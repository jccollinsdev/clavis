import logging
from datetime import datetime, timezone

from ..services.minimax import chatcompletion_text
from .analysis_utils import clamp_score, extract_json_object
from .structural_scorer import (
    calculate_structural_base_score,
    calculate_macro_adjustment,
    calculate_event_adjustment,
    calculate_final_safety_score,
    smooth_score_change,
    get_daily_move_cap,
)

SYSTEM_PROMPT = """You are a risk scoring AI for individual stock positions. Given the position context, recent news analysis, and optional MiroFish swarm report, score this position across 4 dimensions (0-100) and determine a grade.

Position:
- Ticker: {ticker}
- Shares: {shares} @ ${purchase_price}
- Inferred labels: {labels}
- Position report summary: {summary}

Long-form position report: {long_report}

Scoring criteria:
1. news_sentiment (0-100): Is recent news positive, negative, or neutral? 50 is neutral.
2. macro_exposure (0-100): How exposed is this to macro headwinds? Lower = more exposed.
3. position_sizing (0-100): Is the position size appropriate for the risk? Larger positions with high risk = lower score.
4. volatility_trend (0-100): Is volatility increasing or decreasing? Decreasing = higher score.

Use plain English only. Do not mention internal evidence labels, body-depth terms, or implementation jargon such as full_body, title_only, or headline_summary.

Respond in this exact JSON format (no markdown, no explanation):
{{"news_sentiment": 0-100, "macro_exposure": 0-100, "position_sizing": 0-100, "volatility_trend": 0-100, "grade": "A|B|C|D|F", "reasoning": "plain English explanation of the scores and grade", "dimension_rationale": {{"news_sentiment": "...", "macro_exposure": "...", "position_sizing": "...", "volatility_trend": "..."}}}}"""

DIMENSION_KEYS = [
    "news_sentiment",
    "macro_exposure",
    "position_sizing",
    "volatility_trend",
]

GRADE_ORDER = ("A", "B", "C", "D", "F")
GRADE_THRESHOLDS = {
    "A": 80,
    "B": 65,
    "C": 50,
    "D": 35,
    "F": 0,
}
GRADE_HYSTERESIS = 3.0


def _neutral_dimension_count(scores: dict | None) -> int:
    if not isinstance(scores, dict):
        return len(DIMENSION_KEYS)
    return sum(clamp_score(scores.get(key), 50) == 50 for key in DIMENSION_KEYS)


def has_suspicious_neutral_scores(scores: dict | None, threshold: int = 3) -> bool:
    return _neutral_dimension_count(scores) >= threshold


def _is_batch_response_suspicious(
    parsed_scores: dict[str, dict], tickers: list[str], threshold: int = 3
) -> bool:
    expected = [str(t).strip().upper() for t in tickers if str(t).strip()]
    if not expected:
        return False
    suspicious = 0
    for ticker in expected:
        score = parsed_scores.get(ticker, {})
        if has_suspicious_neutral_scores(score, threshold=threshold):
            suspicious += 1
    return suspicious > 0


def _parse_batch_scores(raw_text: str, tickers: list[str]) -> dict[str, dict]:
    parsed = extract_json_object(raw_text, None)
    if isinstance(parsed, dict):
        for key in ("scores", "results"):
            candidate = parsed.get(key)
            if candidate is not None:
                parsed = candidate
                break

    expected = {str(t).strip().upper() for t in tickers if str(t).strip()}
    scores: dict[str, dict] = {}

    if isinstance(parsed, dict):
        for key, value in parsed.items():
            ticker = str(key).strip().upper()
            if expected and ticker not in expected:
                continue
            if isinstance(value, dict):
                scores[ticker] = value

        if scores:
            return scores

        ticker = parsed.get("ticker") or parsed.get("symbol")
        if ticker:
            ticker_key = str(ticker).strip().upper()
            if not expected or ticker_key in expected:
                return {ticker_key: parsed}

    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue

            ticker = item.get("ticker") or item.get("symbol")
            if ticker:
                ticker_key = str(ticker).strip().upper()
                if not expected or ticker_key in expected:
                    scores[ticker_key] = item
                continue

            if len(item) == 1:
                key, value = next(iter(item.items()))
                ticker_key = str(key).strip().upper()
                if isinstance(value, dict) and (not expected or ticker_key in expected):
                    scores[ticker_key] = value

        if scores:
            return scores

    return {}


logger = logging.getLogger(__name__)


def _is_backfill_mode(position_data: dict) -> bool:
    return (
        str(position_data.get("analysis_mode") or "").strip().lower()
        == "sp500_backfill"
    )


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _event_age_days(event: dict) -> float:
    published_at = _parse_timestamp(event.get("published_at"))
    if published_at is None:
        return 7.0
    delta = datetime.now(timezone.utc) - published_at
    return max(0.0, delta.total_seconds() / 86400.0)


def _risk_direction_value(direction: str | None) -> int:
    normalized = str(direction or "neutral").strip().lower()
    if normalized == "worsening":
        return -1
    if normalized == "improving":
        return 1
    return 0


def _macro_adjustment_from_context(position_data: dict) -> tuple[float, str]:
    macro_impact = position_data.get("macro_impact") or {}
    labels = {
        str(label).strip().lower() for label in position_data.get("inferred_labels", [])
    }
    ticker_metadata = position_data.get("ticker_metadata") or {}

    score = 62.0
    rationale_parts = []
    macro_relevance = (
        str(macro_impact.get("macro_relevance") or "neutral").strip().lower()
    )
    if macro_relevance == "challenges":
        score -= 18
        rationale_parts.append("overnight macro backdrop challenges the holding")
    elif macro_relevance == "confirms":
        score += 10
        rationale_parts.append("overnight macro backdrop is supportive")
    else:
        rationale_parts.append("no clear overnight macro change was detected")

    if "rate_sensitive" in labels:
        score -= 6
        rationale_parts.append("labels show rate sensitivity")
    if "defensive" in labels:
        score += 5
        rationale_parts.append("defensive labeling offsets some macro risk")

    sector = str(ticker_metadata.get("sector") or "").strip().lower()
    if sector in {"financials", "energy", "real estate", "realestate"}:
        score -= 3
    elif sector in {"healthcare", "consumer staples", "utilities"}:
        score += 2

    return clamp_score(round(score), 50), "; ".join(rationale_parts)


def _deterministic_dimension_scores(
    position_data: dict,
    portfolio_total_value: float,
) -> dict:
    event_analyses = list(position_data.get("event_analyses") or [])
    ticker_metadata = position_data.get("ticker_metadata") or {}
    current_price = _safe_float(
        position_data.get("current_price")
        or ticker_metadata.get("price")
        or position_data.get("purchase_price")
    )
    shares = _safe_float(position_data.get("shares"))
    position_value = max(current_price * shares, 0.0)
    portfolio_weight = (
        position_value / portfolio_total_value if portfolio_total_value > 0 else 0.0
    )

    news_delta = 0.0
    worsening_major = 0
    improving_major = 0
    for event in event_analyses:
        direction = _risk_direction_value(event.get("risk_direction"))
        significance = str(event.get("significance") or "minor").strip().lower()
        confidence = min(max(_safe_float(event.get("confidence"), 0.5), 0.2), 1.0)
        age_days = _event_age_days(event)
        recency = max(0.35, 1.0 - min(age_days, 14.0) / 20.0)
        magnitude = 15 if significance == "major" else 7
        news_delta += direction * magnitude * confidence * recency
        if significance == "major" and direction < 0:
            worsening_major += 1
        if significance == "major" and direction > 0:
            improving_major += 1

    news_sentiment = clamp_score(round(50 + news_delta), 50)
    news_rationale = (
        f"Derived from {len(event_analyses)} analyzed event(s) with {worsening_major} major worsening and {improving_major} major improving catalyst(s)."
        if event_analyses
        else "No strong event evidence was available, so the score stays near neutral."
    )

    macro_exposure, macro_rationale = _macro_adjustment_from_context(position_data)

    volatility_proxy = _safe_float(ticker_metadata.get("volatility_proxy"), 0.0)
    beta = abs(_safe_float(ticker_metadata.get("beta"), 0.0))
    volatility_trend = 78 - (volatility_proxy * 40)
    if beta:
        volatility_trend -= min(18, max(0.0, (beta - 1.0) * 10))
    volatility_trend -= worsening_major * 5
    volatility_trend += improving_major * 3
    volatility_trend = clamp_score(round(volatility_trend), 50)
    volatility_rationale = f"Uses beta {ticker_metadata.get('beta') or 'n/a'} and volatility proxy {ticker_metadata.get('volatility_proxy') or 'n/a'} with recent event pressure layered in."

    sizing_score = 82.0
    if portfolio_weight >= 0.2:
        sizing_score -= 22
    elif portfolio_weight >= 0.1:
        sizing_score -= 12
    elif portfolio_weight >= 0.05:
        sizing_score -= 6
    if news_sentiment < 45:
        sizing_score -= 8
    if volatility_trend < 45:
        sizing_score -= 8
    if portfolio_weight <= 0.01 and shares > 0:
        sizing_score += 2
    position_sizing = clamp_score(round(sizing_score), 50)
    sizing_rationale = f"Estimated portfolio weight is {portfolio_weight:.1%}; higher weights and weaker risk signals reduce the sizing score."

    normalized_scores = {
        "news_sentiment": news_sentiment,
        "macro_exposure": macro_exposure,
        "position_sizing": position_sizing,
        "volatility_trend": volatility_trend,
    }
    weighted = calculate_weighted_score(normalized_scores)
    total = round(
        smooth_score_change(
            new_score=weighted,
            previous_score=position_data.get("previous_total_score"),
        ),
        1,
    )
    grade = _apply_grade_hysteresis(total, position_data.get("previous_grade"))

    reasoning = (
        f"Deterministic score built from cached event analysis, macro context, and ticker metadata. "
        + f"News={news_sentiment}, Macro={macro_exposure}, Size={position_sizing}, Volatility={volatility_trend}."
    )
    if position_data.get("previous_grade") and grade != score_to_grade(weighted):
        reasoning = (
            f"{reasoning} Grade held at {grade} to stay consistent near the threshold."
        )

    return {
        **normalized_scores,
        "total_score": total,
        "grade": grade,
        "reasoning": reasoning,
        "grade_reason": reasoning,
        "evidence_summary": position_data.get("summary", ""),
        "dimension_rationale": {
            "news_sentiment": news_rationale,
            "macro_exposure": macro_rationale,
            "position_sizing": sizing_rationale,
            "volatility_trend": volatility_rationale,
        },
        "mirofish_used": position_data.get("mirofish_used", False),
    }


def _needs_llm_scoring(position_data: dict) -> bool:
    return not any(
        [
            position_data.get("event_analyses"),
            position_data.get("macro_impact"),
            position_data.get("ticker_metadata"),
        ]
    )


def _prefer_llm_scoring(position_data: dict) -> bool:
    analysis_mode = str(position_data.get("analysis_mode") or "").strip().lower()
    if analysis_mode == "sp500_backfill":
        return False

    if position_data.get("event_analyses"):
        return True

    summary = str(position_data.get("summary") or "").strip()
    long_report = str(position_data.get("long_report") or "").strip()
    return bool(summary or long_report)


def _llm_score_prompt(position_data: dict) -> str:
    return SYSTEM_PROMPT.format(
        ticker=position_data.get("ticker", ""),
        shares=position_data.get("shares", 0),
        purchase_price=position_data.get("purchase_price", 0),
        labels=", ".join(position_data.get("inferred_labels", []) or []),
        summary=position_data.get("summary", ""),
        long_report=position_data.get("long_report", ""),
    )


def calculate_weighted_score(scores: dict) -> float:
    values = [clamp_score(scores.get(key), 50) for key in DIMENSION_KEYS]
    return sum(values) / len(values)


def score_to_grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _apply_grade_hysteresis(score: float, previous_grade: str | None) -> str:
    current_grade = score_to_grade(score)
    previous_grade = (previous_grade or "").strip().upper()

    if previous_grade not in GRADE_THRESHOLDS:
        return current_grade

    if current_grade == previous_grade:
        return current_grade

    previous_index = GRADE_ORDER.index(previous_grade)
    current_index = GRADE_ORDER.index(current_grade)

    if current_index < previous_index:
        if score >= GRADE_THRESHOLDS[current_grade] + GRADE_HYSTERESIS:
            return current_grade
        return previous_grade

    if score < GRADE_THRESHOLDS[previous_grade] - GRADE_HYSTERESIS:
        return current_grade
    return previous_grade


async def score_position(
    position: dict,
    position_report: dict,
    inferred_labels: list[str] | None = None,
    mirofish_used: bool = False,
) -> dict:
    position_data = {
        **position,
        **position_report,
        "inferred_labels": inferred_labels
        or position_report.get("inferred_labels", []),
        "mirofish_used": mirofish_used,
    }
    deterministic = _deterministic_dimension_scores(
        position_data,
        portfolio_total_value=max(
            _safe_float(position_data.get("purchase_price"))
            * _safe_float(position_data.get("shares")),
            1.0,
        ),
    )
    if not _prefer_llm_scoring(position_data) and not _needs_llm_scoring(position_data):
        return deterministic

    prompt = _llm_score_prompt(position_data)
    required_dimensions = [
        "news_sentiment",
        "macro_exposure",
        "position_sizing",
        "volatility_trend",
    ]

    def _request_scores() -> tuple[str, dict]:
        result_text = chatcompletion_text(
            messages=[
                {
                    "role": "system",
                    "content": "You MUST respond with valid JSON only. No markdown. No explanation. No thinking. Start with { and end with }.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            max_tokens=1500,
        )
        return result_text, extract_json_object(result_text, {})

    result_text, scores = _request_scores()
    missing_dimensions = [key for key in required_dimensions if scores.get(key) is None]
    if missing_dimensions:
        logger.warning(
            "score_position parse failure for %s; missing=%s; raw=%r",
            position.get("ticker", ""),
            missing_dimensions,
            (result_text or "")[:800],
        )
        retry_text, retry_scores = _request_scores()
        retry_missing = [
            key for key in required_dimensions if retry_scores.get(key) is None
        ]
        if len(retry_missing) < len(missing_dimensions):
            result_text, scores = retry_text, retry_scores
            missing_dimensions = retry_missing

    if missing_dimensions:
        logger.error(
            "score_position falling back to defaults for %s; missing=%s; raw=%r",
            position.get("ticker", ""),
            missing_dimensions,
            (result_text or "")[:800],
        )
        return deterministic

    normalized_scores = {
        "news_sentiment": clamp_score(scores.get("news_sentiment"), 50),
        "macro_exposure": clamp_score(scores.get("macro_exposure"), 50),
        "position_sizing": clamp_score(scores.get("position_sizing"), 50),
        "volatility_trend": clamp_score(scores.get("volatility_trend"), 50),
    }

    weighted = calculate_weighted_score(normalized_scores)
    total = round(
        smooth_score_change(
            new_score=weighted,
            previous_score=position_report.get("previous_total_score"),
        ),
        1,
    )
    grade = _apply_grade_hysteresis(total, position_report.get("previous_grade"))
    dimension_rationale = scores.get("dimension_rationale") or {}

    if position_report.get("previous_grade") and grade != score_to_grade(weighted):
        reasoning = scores.get("reasoning", "")
        if reasoning:
            reasoning = f"{reasoning} Grade held at {grade} to stay consistent near the threshold."
        else:
            reasoning = f"Grade held at {grade} to stay consistent near the threshold."
    else:
        reasoning = scores.get("reasoning", "")

    return {
        "news_sentiment": normalized_scores["news_sentiment"],
        "macro_exposure": normalized_scores["macro_exposure"],
        "position_sizing": normalized_scores["position_sizing"],
        "volatility_trend": normalized_scores["volatility_trend"],
        "total_score": total,
        "grade": grade,
        "reasoning": reasoning,
        "grade_reason": reasoning,
        "evidence_summary": position_data.get("summary", ""),
        "dimension_rationale": dimension_rationale,
        "mirofish_used": mirofish_used,
    }


def score_position_structural(
    position: dict,
    ticker_metadata: dict | None = None,
    regime_state: str = "neutral",
    recent_events: list[dict] | None = None,
    previous_safety_score: float | None = None,
) -> dict:
    if ticker_metadata is None:
        ticker_metadata = {}
    if recent_events is None:
        recent_events = []

    market_cap = ticker_metadata.get("market_cap")
    avg_daily_dollar_volume = ticker_metadata.get("avg_daily_dollar_volume")
    volatility_proxy = ticker_metadata.get("volatility_proxy")
    leverage_profile = ticker_metadata.get("leverage_profile", "moderate")
    profitability_profile = ticker_metadata.get("profitability_profile", "mixed")
    asset_class = ticker_metadata.get("asset_class")
    macro_sensitivity = ticker_metadata.get("macro_sensitivity", "moderate")

    structural_result = calculate_structural_base_score(
        market_cap=market_cap,
        avg_daily_dollar_volume=avg_daily_dollar_volume,
        volatility_proxy=volatility_proxy,
        leverage_profile=leverage_profile,
        profitability_profile=profitability_profile,
        asset_class=asset_class,
    )

    macro_adj = calculate_macro_adjustment(
        regime_state=regime_state,
        asset_sensitivity=macro_sensitivity,
    )

    total_event_adjustment = 0.0
    for event in recent_events:
        event_significance = event.get("significance", "minor")
        event_direction = event.get("risk_direction", "neutral")
        event_confidence = event.get("confidence", 0.5)
        event_age_days = event.get("event_age_days", 0)
        event_adj = calculate_event_adjustment(
            event_significance=event_significance,
            event_direction=event_direction,
            event_confidence=event_confidence,
            event_age_days=event_age_days,
        )
        total_event_adjustment += event_adj

    total_event_adjustment = max(-20, min(5, total_event_adjustment))

    final_safety = calculate_final_safety_score(
        structural_base_score=structural_result["structural_base_score"],
        macro_adjustment=macro_adj,
        event_adjustment=total_event_adjustment,
    )

    if previous_safety_score is not None:
        final_safety = smooth_score_change(
            new_score=final_safety,
            previous_score=previous_safety_score,
            asset_class=asset_class,
            market_cap=market_cap,
        )

    safety_grade = score_to_grade(final_safety)

    factor_breakdown = structural_result.get("factor_breakdown", {})
    factor_breakdown.update(
        {
            "macro_adjustment": macro_adj,
            "event_adjustment": total_event_adjustment,
            "event_count": len(recent_events),
        }
    )

    return {
        "safety_score": final_safety,
        "confidence": structural_result["confidence"],
        "structural_base_score": structural_result["structural_base_score"],
        "macro_adjustment": macro_adj,
        "event_adjustment": total_event_adjustment,
        "total_score": final_safety,
        "grade": safety_grade,
        "factor_breakdown": factor_breakdown,
        "market_cap_bucket": structural_result.get("market_cap_bucket"),
        "reasoning": f"Structural: {structural_result['structural_base_score']}, Macro: {macro_adj}, Event: {total_event_adjustment}",
        "grade_reason": f"Safety score {final_safety} based on structural factors and adjustments",
        "dimension_rationale": {
            "structural_base_score": f"Deterministic scoring from market cap, liquidity, volatility, leverage, profitability",
            "macro_adjustment": f"Regime {regime_state} with {macro_sensitivity} sensitivity",
            "event_adjustment": f"{len(recent_events)} recent events contributing {total_event_adjustment}",
        },
        "mirofish_used": False,
    }


async def score_positions_batch(
    positions_data: list[dict],
) -> list[dict]:
    if not positions_data:
        return []

    portfolio_total_value = (
        sum(
            max(
                _safe_float(
                    p.get("current_price")
                    or (p.get("ticker_metadata") or {}).get("price")
                    or p.get("purchase_price")
                )
                * _safe_float(p.get("shares")),
                0.0,
            )
            for p in positions_data
        )
        or 1.0
    )

    results = [
        _deterministic_dimension_scores(position, portfolio_total_value)
        for position in positions_data
    ]

    sparse_positions = [
        (index, position)
        for index, position in enumerate(positions_data)
        if _prefer_llm_scoring(position) or _needs_llm_scoring(position)
    ]
    if not sparse_positions:
        return results

    import re

    llm_chunk_size = (
        3
        if any(_prefer_llm_scoring(position) for _, position in sparse_positions)
        else 8
    )

    for chunk_start in range(0, len(sparse_positions), llm_chunk_size):
        chunk = sparse_positions[chunk_start : chunk_start + llm_chunk_size]
        tickers = [position.get("ticker", "") for _, position in chunk]
        positions_text = "\n".join(
            f"""Position {i + 1}:
- Ticker: {position.get("ticker", "")}
- Shares: {position.get("shares", 0)} @ ${position.get("purchase_price", 0)}
- Inferred labels: {", ".join(position.get("inferred_labels", [])) or position.get("archetype", "core")}
- Position report summary: {position.get("summary", "no summary")[:200]}
- Long report excerpt: {position.get("long_report", "")[:300]}"""
            for i, (_, position) in enumerate(chunk)
        )
        score_example = ", ".join(
            (
                f'"{ticker}": {{"news_sentiment": 50, "macro_exposure": 50, "position_sizing": 50, "volatility_trend": 50, "grade": "C"}}'
            )
            for ticker in tickers
        )
        prompt = f"""Score each position across 4 dimensions (0-100) and assign a grade.

{positions_text}

Return EXACTLY this JSON format (no markdown, no explanation, no thinking):
{{"scores": {{{score_example}}}}}

        Scoring criteria:
        - news_sentiment: positive news=high (70-90), negative=low (20-40), neutral=50
        - macro_exposure: low macro sensitivity=high (60-80), high sensitivity=low (20-40)
        - position_sizing: appropriate size=high (70-90), oversized=low (20-40)
        - volatility_trend: decreasing vol=high (60-80), increasing vol=low (20-40)
        - Grade A=80+, B=65-79, C=50-64, D=35-49, F=<35

Respond with ONLY the JSON object. Start with {{ and end with }}."""

        def _request_chunk_scores() -> tuple[str, dict[str, dict]]:
            result_text = chatcompletion_text(
                messages=[
                    {
                        "role": "system",
                        "content": "You MUST respond with valid JSON only. No markdown. No explanation. No thinking. Start your response with { and end with }.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                max_tokens=800,
            )
            return result_text, _parse_batch_scores(result_text, tickers)

        result_text, all_scores = _request_chunk_scores()
        if _is_batch_response_suspicious(all_scores, tickers):
            logger.warning(
                "score_positions_batch sparse fallback retry; raw=%r",
                (result_text or "")[:800],
            )
            retry_text, retry_scores = _request_chunk_scores()
            if not _is_batch_response_suspicious(retry_scores, tickers):
                result_text, all_scores = retry_text, retry_scores

        required_dimensions = [
            "news_sentiment",
            "macro_exposure",
            "position_sizing",
            "volatility_trend",
        ]

        if not all_scores:
            for ticker in tickers:
                ticker_upper = ticker.upper()
                ticker_scores = {}
                for dim in required_dimensions:
                    pattern = rf"{ticker_upper}.*?{dim}.*?(\d+)"
                    match = re.search(pattern, result_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        ticker_scores[dim] = int(match.group(1))
                if ticker_scores:
                    all_scores[ticker_upper] = ticker_scores

        for result_index, position in chunk:
            ticker = str(position.get("ticker") or "").strip().upper()
            raw_scores = all_scores.get(ticker, {})
            if not raw_scores:
                continue
            if _prefer_llm_scoring(position) and has_suspicious_neutral_scores(
                raw_scores
            ):
                logger.warning(
                    "score_positions_batch keeping deterministic fallback for %s due to neutral AI output",
                    ticker,
                )
                continue
            normalized = {
                "news_sentiment": clamp_score(raw_scores.get("news_sentiment"), 50),
                "macro_exposure": clamp_score(raw_scores.get("macro_exposure"), 50),
                "position_sizing": clamp_score(raw_scores.get("position_sizing"), 50),
                "volatility_trend": clamp_score(raw_scores.get("volatility_trend"), 50),
            }
            weighted = calculate_weighted_score(normalized)
            total = round(
                smooth_score_change(
                    new_score=weighted,
                    previous_score=position.get("previous_total_score"),
                ),
                1,
            )
            grade = _apply_grade_hysteresis(total, position.get("previous_grade"))
            reasoning = raw_scores.get("reasoning", "")
            if position.get("previous_grade") and grade != score_to_grade(weighted):
                reasoning = (
                    f"{reasoning} Grade held at {grade} to stay consistent near the threshold."
                    if reasoning
                    else f"Grade held at {grade} to stay consistent near the threshold."
                )
            results[result_index] = {
                "news_sentiment": normalized["news_sentiment"],
                "macro_exposure": normalized["macro_exposure"],
                "position_sizing": normalized["position_sizing"],
                "volatility_trend": normalized["volatility_trend"],
                "total_score": total,
                "grade": grade,
                "reasoning": reasoning,
                "grade_reason": reasoning,
                "evidence_summary": position.get("summary", ""),
                "dimension_rationale": raw_scores.get("dimension_rationale") or {},
                "mirofish_used": position.get("mirofish_used", False),
                "factor_breakdown": {
                    "ai_dimensions": {
                        "news_sentiment": normalized["news_sentiment"],
                        "macro_exposure": normalized["macro_exposure"],
                        "position_sizing": normalized["position_sizing"],
                        "volatility_trend": normalized["volatility_trend"],
                    },
                },
            }

    return results
