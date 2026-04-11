import logging

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

Respond in this exact JSON format (no markdown, no explanation):
{{"news_sentiment": 0-100, "macro_exposure": 0-100, "position_sizing": 0-100, "volatility_trend": 0-100, "grade": "A|B|C|D|F", "reasoning": "plain English explanation of the scores and grade", "dimension_rationale": {{"news_sentiment": "...", "macro_exposure": "...", "position_sizing": "...", "volatility_trend": "..."}}}}"""

DIMENSION_KEYS = [
    "news_sentiment",
    "macro_exposure",
    "position_sizing",
    "volatility_trend",
]


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


def calculate_weighted_score(scores: dict) -> float:
    return sum(scores[key] for key in DIMENSION_KEYS) / len(DIMENSION_KEYS)


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


async def score_position(
    position: dict,
    position_report: dict,
    inferred_labels: list[str] | None = None,
    mirofish_used: bool = False,
) -> dict:
    prompt = SYSTEM_PROMPT.format(
        ticker=position.get("ticker", ""),
        shares=position.get("shares", 0),
        purchase_price=position.get("purchase_price", 0),
        labels=", ".join(inferred_labels or []),
        summary=position_report.get("summary", ""),
        long_report=position_report.get("long_report", ""),
    )

    def _request_scores() -> tuple[str, dict]:
        result_text = chatcompletion_text(
            messages=[
                {
                    "role": "system",
                    "content": "You MUST respond with valid JSON only. No markdown. No explanation. No thinking. Start with { and end with }.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        return result_text, extract_json_object(result_text, {})

    result_text, scores = _request_scores()
    missing_dimensions = [key for key in DIMENSION_KEYS if scores.get(key) is None]
    if missing_dimensions:
        logger.warning(
            "score_position parse failure for %s; missing=%s; raw=%r",
            position.get("ticker", ""),
            missing_dimensions,
            (result_text or "")[:800],
        )
        retry_text, retry_scores = _request_scores()
        retry_missing = [key for key in DIMENSION_KEYS if retry_scores.get(key) is None]
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

    normalized_scores = {
        key: clamp_score(scores.get(key), 50) for key in DIMENSION_KEYS
    }

    weighted = calculate_weighted_score(normalized_scores)
    grade = score_to_grade(weighted)
    valid_grades = {"A", "B", "C", "D", "F"}
    if grade not in valid_grades:
        grade = "C"
    total = round(weighted, 1)
    dimension_rationale = scores.get("dimension_rationale") or {}

    return {
        "news_sentiment": normalized_scores["news_sentiment"],
        "macro_exposure": normalized_scores["macro_exposure"],
        "position_sizing": normalized_scores["position_sizing"],
        "volatility_trend": normalized_scores["volatility_trend"],
        "total_score": total,
        "grade": grade,
        "reasoning": scores.get("reasoning", ""),
        "grade_reason": scores.get("reasoning", ""),
        "evidence_summary": position_report.get("summary", ""),
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

    tickers = [p.get("ticker", "") for p in positions_data]
    positions_text = "\n".join(
        f"""Position {i + 1}:
- Ticker: {p.get("ticker", "")}
- Shares: {p.get("shares", 0)} @ ${p.get("purchase_price", 0)}
- Inferred labels: {", ".join(p.get("inferred_labels", [])) or p.get("archetype", "core")}
- Position report summary: {p.get("summary", "no summary")[:200]}
- Long report excerpt: {p.get("long_report", "")[:300]}"""
        for i, p in enumerate(positions_data)
    )

    score_example = ", ".join(
        f'"{t}": {{"news_sentiment": 50, "macro_exposure": 50, "position_sizing": 50, "volatility_trend": 50, "grade": "C"}}'
        for t in tickers
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

    def _request_batch_scores() -> tuple[str, dict[str, dict]]:
        result_text = chatcompletion_text(
            messages=[
                {
                    "role": "system",
                    "content": "You MUST respond with valid JSON only. No markdown. No explanation. No thinking. Start your response with { and end with }.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        return result_text, _parse_batch_scores(result_text, tickers)

    result_text, all_scores = _request_batch_scores()

    import re

    if _is_batch_response_suspicious(all_scores, tickers):
        logger.warning(
            "score_positions_batch suspicious neutral batch detected; retrying once; raw=%r",
            (result_text or "")[:800],
        )
        retry_text, retry_scores = _request_batch_scores()
        if not _is_batch_response_suspicious(retry_scores, tickers):
            result_text, all_scores = retry_text, retry_scores

    if not all_scores:
        for ticker in tickers:
            ticker_upper = ticker.upper()
            ticker_scores = {}
            for dim in [
                "news_sentiment",
                "macro_exposure",
                "position_sizing",
                "volatility_trend",
            ]:
                pattern = rf"{ticker_upper}.*?{dim}.*?(\d+)"
                match = re.search(pattern, result_text, re.IGNORECASE | re.DOTALL)
                if match:
                    ticker_scores[dim] = int(match.group(1))
            if ticker_scores:
                all_scores[ticker_upper] = ticker_scores

    results = []
    for p in positions_data:
        ticker = p.get("ticker", "")
        raw_scores = all_scores.get(str(ticker).strip().upper(), {})
        normalized = {
            key: clamp_score(raw_scores.get(key, 50), 50) for key in DIMENSION_KEYS
        }
        weighted = calculate_weighted_score(normalized)
        grade = score_to_grade(weighted)
        total = round(weighted, 1)
        results.append(
            {
                "news_sentiment": normalized["news_sentiment"],
                "macro_exposure": normalized["macro_exposure"],
                "position_sizing": normalized["position_sizing"],
                "volatility_trend": normalized["volatility_trend"],
                "total_score": total,
                "grade": raw_scores.get("grade") or grade,
                "reasoning": raw_scores.get("reasoning", ""),
                "grade_reason": raw_scores.get("reasoning", ""),
                "evidence_summary": p.get("summary", ""),
                "dimension_rationale": raw_scores.get("dimension_rationale") or {},
                "mirofish_used": p.get("mirofish_used", False),
            }
        )
    return results
