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

Use a single scale where 0 means penny-stock-like / very risky and 100 means treasury-like / very safe. Higher scores always mean lower risk.

Position:
- Ticker: {ticker}
- Shares: {shares} @ ${purchase_price}
- Approximate position value: ${position_value}
- Inferred labels: {labels}
- Position report summary: {summary}

Long-form position report: {long_report}

Scoring criteria:
1. news_sentiment (0-100): Positive / supportive news moves toward 100, negative / dangerous news moves toward 0. Use 50 only when the news is truly balanced.
2. macro_exposure (0-100): Less macro-sensitive / more treasury-like moves toward 100. More macro-sensitive / more speculative moves toward 0.
3. position_sizing (0-100): Appropriately sized, prudent risk for the holding moves toward 100. Oversized or speculative exposure moves toward 0.
4. volatility_trend (0-100): Falling volatility / stable trend moves toward 100. Rising volatility / unstable behavior moves toward 0.

Use plain English only. Do not mention internal evidence labels, body-depth terms, or implementation jargon such as full_body, title_only, or headline_summary. Avoid returning 50 for every dimension unless the evidence is genuinely neutral.

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


def has_suspicious_neutral_scores(
    scores: dict | None, threshold: int = len(DIMENSION_KEYS)
) -> bool:
    return _neutral_dimension_count(scores) >= threshold


def _is_batch_response_suspicious(
    parsed_scores: dict[str, dict],
    tickers: list[str],
    threshold: int = len(DIMENSION_KEYS),
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


def _coverage_state_for_position(position_data: dict) -> tuple[str, int, int, int, str]:
    event_analyses = list(position_data.get("event_analyses") or [])
    source_count = len(event_analyses)
    major_event_count = sum(
        1
        for event in event_analyses
        if str(event.get("significance") or "minor").strip().lower() == "major"
    )
    minor_event_count = max(source_count - major_event_count, 0)
    summary = str(position_data.get("summary") or "").strip().lower()

    if source_count == 0 or summary.startswith("insufficient evidence"):
        coverage_state = "provisional"
        coverage_note = "Confidence is low because the score leans mostly on ticker metadata and cached context."
    elif source_count <= 2:
        coverage_state = "thin"
        coverage_note = f"Low-confidence coverage: only {source_count} analyzed event(s) were available."
    else:
        coverage_state = "substantive"
        coverage_note = f"{source_count} analyzed event(s) supported this score."

    return (
        coverage_state,
        source_count,
        major_event_count,
        minor_event_count,
        coverage_note,
    )


def _synthesized_reasoning(
    ticker: str,
    scores: dict,
    coverage_state: str,
    source_count: int,
    coverage_note: str,
    llm_used: bool,
    total_score: float | None = None,
) -> str:
    def _dimension_phrase(key: str, label: str) -> str:
        value = clamp_score(scores.get(key), 50)
        if value >= 65:
            effect = "supports a safer read"
        elif value <= 35:
            effect = "adds risk"
        else:
            effect = "is broadly neutral"
        return f"{label} ({value}) {effect}"

    def _primary_horizon() -> str:
        volatility = clamp_score(scores.get("volatility_trend"), 50)
        news = clamp_score(scores.get("news_sentiment"), 50)
        macro = clamp_score(scores.get("macro_exposure"), 50)
        sizing = clamp_score(scores.get("position_sizing"), 50)
        if volatility <= 40 or news <= 40:
            return "The immediate risk is the main concern."
        if macro <= 45 or sizing <= 45:
            return "This is more of a monitor-only risk than an immediate shock."
        return "The risk is mostly background unless new evidence changes the setup."

    parts = [
        f"{ticker}: "
        + "; ".join(
            [
                _dimension_phrase("news_sentiment", "Company-specific news"),
                _dimension_phrase("macro_exposure", "Macro/sector exposure"),
                _dimension_phrase("position_sizing", "Portfolio construction"),
                _dimension_phrase("volatility_trend", "Near-term volatility"),
            ]
        )
        + "."
    ]
    parts.append(_primary_horizon())

    if total_score is not None:
        parts.append(
            f"Those inputs land the score at {int(round(total_score))}/100, which matches the final grade."
        )

    if coverage_note:
        parts.append(coverage_note)

    if llm_used:
        parts.append(
            "This summary was assembled from the final dimension scores."
        )

    return " ".join(part for part in parts if part).strip()


def _article_evidence_brief(position_data: dict, limit: int = 4) -> str:
    evidence_rows = list(position_data.get("article_evidence") or [])
    if not evidence_rows:
        evidence_rows = []
        for event in list(position_data.get("event_analyses") or []):
            evidence_rows.append(
                {
                    "title": event.get("title"),
                    "source": event.get("source"),
                    "published_at": event.get("published_at"),
                    "evidence_quality": event.get("evidence_quality"),
                    "excerpt": event.get("article_excerpt") or event.get("summary") or "",
                }
            )

    lines: list[str] = []
    for row in evidence_rows[:limit]:
        title = str(row.get("title") or "").strip()
        source = str(row.get("source") or "").strip()
        published_at = str(row.get("published_at") or "").strip()[:19]
        evidence_quality = str(row.get("evidence_quality") or "").strip()
        excerpt = str(row.get("excerpt") or row.get("summary") or "").strip()
        if excerpt:
            excerpt = excerpt[:180]
        parts = [part for part in [title, source, published_at, evidence_quality] if part]
        if excerpt:
            parts.append(excerpt)
        if parts:
            lines.append(" | ".join(parts))

    return "\n".join(lines)


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
    (
        coverage_state,
        source_count,
        major_event_count,
        minor_event_count,
        coverage_note,
    ) = _coverage_state_for_position(position_data)
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

    reasoning = _synthesized_reasoning(
        str(position_data.get("ticker") or "this position"),
        normalized_scores,
        coverage_state,
        source_count,
        coverage_note,
        llm_used=False,
        total_score=total,
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
        "source_count": source_count,
        "major_event_count": major_event_count,
        "minor_event_count": minor_event_count,
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "is_provisional": coverage_state != "substantive",
        "llm_scoring_used": False,
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
    if position_data.get("event_analyses"):
        return True

    summary = str(position_data.get("summary") or "").strip()
    long_report = str(position_data.get("long_report") or "").strip()
    return bool(summary or long_report)


def _llm_score_prompt(position_data: dict) -> str:
    article_evidence = _article_evidence_brief(position_data)
    evidence_block = (
        f"\n\nSelected article evidence:\n{article_evidence}" if article_evidence else ""
    )
    return SYSTEM_PROMPT.format(
        ticker=position_data.get("ticker", ""),
        shares=position_data.get("shares", 0),
        purchase_price=position_data.get("purchase_price", 0),
        position_value=round(_safe_float(position_data.get("position_value"), 0.0), 2),
        labels=", ".join(position_data.get("inferred_labels", []) or []),
        summary=position_data.get("summary", ""),
        long_report=(position_data.get("long_report", "") or "") + evidence_block,
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
    position_data["position_value"] = max(
        _safe_float(
            position_data.get("current_price") or position_data.get("purchase_price")
        )
        * _safe_float(position_data.get("shares")),
        0.0,
    )
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
    (
        coverage_state,
        source_count,
        major_event_count,
        minor_event_count,
        coverage_note,
    ) = _coverage_state_for_position(position_data)

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
    reasoning = (scores.get("reasoning") or "").strip()
    if not reasoning:
        reasoning = _synthesized_reasoning(
            str(position_data.get("ticker") or "this position"),
            normalized_scores,
            coverage_state,
            source_count,
            coverage_note,
            llm_used=True,
            total_score=total,
        )

    if position_report.get("previous_grade") and grade != score_to_grade(weighted):
        if reasoning:
            reasoning = f"{reasoning} Grade held at {grade} to stay consistent near the threshold."
        else:
            reasoning = f"Grade held at {grade} to stay consistent near the threshold."

    return {
        "news_sentiment": normalized_scores["news_sentiment"],
        "macro_exposure": normalized_scores["macro_exposure"],
        "position_sizing": normalized_scores["position_sizing"],
        "volatility_trend": normalized_scores["volatility_trend"],
        "total_score": total,
        "grade": grade,
        "reasoning": reasoning,
        "grade_reason": reasoning,
        "evidence_summary": scores.get("evidence_summary") or position_data.get("summary", ""),
        "dimension_rationale": dimension_rationale,
        "source_count": source_count,
        "major_event_count": major_event_count,
        "minor_event_count": minor_event_count,
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "is_provisional": coverage_state != "substantive",
        "llm_scoring_used": True,
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
    source_count = len(recent_events)
    major_event_count = sum(
        1
        for event in recent_events
        if str(event.get("significance") or "minor").strip().lower() == "major"
    )
    minor_event_count = max(source_count - major_event_count, 0)
    if source_count == 0:
        coverage_state = "provisional"
        coverage_note = "No recent event coverage was available, so this structural score is provisional."
    elif source_count <= 2:
        coverage_state = "thin"
        coverage_note = f"Low-confidence coverage: only {source_count} recent event(s) were available."
    else:
        coverage_state = "substantive"
        coverage_note = (
            f"{source_count} recent event(s) supported this structural score."
        )

    confidence = structural_result["confidence"]
    if source_count == 0:
        confidence = max(0.35, confidence - 0.2)
    elif source_count == 1:
        confidence = max(0.45, confidence - 0.12)
    elif source_count == 2:
        confidence = max(0.5, confidence - 0.08)

    factor_breakdown = structural_result.get("factor_breakdown", {})
    factor_breakdown.update(
        {
            "macro_adjustment": macro_adj,
            "event_adjustment": total_event_adjustment,
            "event_count": source_count,
        }
    )

    return {
        "safety_score": final_safety,
        "confidence": confidence,
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
        "source_count": source_count,
        "major_event_count": major_event_count,
        "minor_event_count": minor_event_count,
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "is_provisional": coverage_state != "substantive",
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
        evidence_texts = []
        for i, (_, position) in enumerate(chunk):
            evidence = _article_evidence_brief(position, limit=3)
            if evidence:
                evidence_texts.append(f"Position {i + 1} article evidence:\n{evidence}")
        positions_text = "\n".join(
            f"""Position {i + 1}:
- Ticker: {position.get("ticker", "")}
- Shares: {position.get("shares", 0)} @ ${position.get("purchase_price", 0)}
- Approximate current price: ${position.get("current_price") or position.get("purchase_price", 0)}
- Estimated position value: ${round(_safe_float(position.get("current_price") or position.get("purchase_price")) * _safe_float(position.get("shares")), 2)}
- Portfolio weight: {round(((_safe_float(position.get("current_price") or position.get("purchase_price")) * _safe_float(position.get("shares"))) / portfolio_total_value) * 100, 2)}%
- Inferred labels: {", ".join(position.get("inferred_labels", [])) or position.get("archetype", "core")}
- Position report summary: {position.get("summary", "no summary")[:200]}
- Long report excerpt: {position.get("long_report", "")[:300]}"""
            for i, (_, position) in enumerate(chunk)
        )
        evidence_block = "\n\n".join(evidence_texts)
        score_example = ", ".join(
            (
                f'"{ticker}": {{"news_sentiment": 50, "macro_exposure": 50, "position_sizing": 50, "volatility_trend": 50, "grade": "C", "reasoning": "...", "dimension_rationale": {{"news_sentiment": "...", "macro_exposure": "...", "position_sizing": "...", "volatility_trend": "..."}}, "evidence_summary": "..."}}'
            )
            for ticker in tickers
        )
        prompt = f"""Score each position across 4 dimensions (0-100) and assign a grade.

Use a single scale where 0 means penny-stock-like / very risky and 100 means treasury-like / very safe. Higher scores always mean lower risk.

{positions_text}

{evidence_block if evidence_block else ""}

Return EXACTLY this JSON format (no markdown, no explanation, no thinking):
{{"scores": {{{score_example}}}}}

        Scoring criteria:
        - news_sentiment: positive/supportive news=high (70-100), negative/dangerous news=low (0-40), neutral=50 only when truly balanced
        - macro_exposure: less macro-sensitive / more treasury-like=high (70-100), more macro-sensitive / more speculative=low (0-40)
        - position_sizing: prudent, appropriately sized exposure=high (70-100), oversized or speculative exposure=low (0-40)
        - volatility_trend: falling volatility / stable trend=high (70-100), rising volatility / unstable behavior=low (0-40)
        - Grade A=80+, B=65-79, C=50-64, D=35-49, F=<35

        Important:
        - Do not return 50 across all four dimensions unless the evidence is genuinely absent.
        - If the evidence is directional, move the relevant dimensions away from 50.
        - Use the position value and portfolio weight context in the prompt when estimating position sizing.
        - Include a short reasoning string, per-dimension rationale, and a one-line evidence summary for each ticker when possible.

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
            (
                coverage_state,
                source_count,
                major_event_count,
                minor_event_count,
                coverage_note,
            ) = _coverage_state_for_position(position)
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
            reasoning = (raw_scores.get("reasoning") or "").strip()
            if not reasoning:
                reasoning = _synthesized_reasoning(
                    ticker,
                    normalized,
                    coverage_state,
                    source_count,
                    coverage_note,
                    llm_used=True,
                )
            weighted = calculate_weighted_score(normalized)
            total = round(
                smooth_score_change(
                    new_score=weighted,
                    previous_score=position.get("previous_total_score"),
                ),
                1,
            )
            grade = _apply_grade_hysteresis(total, position.get("previous_grade"))
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
                "evidence_summary": raw_scores.get("evidence_summary") or position.get("summary", ""),
                "dimension_rationale": raw_scores.get("dimension_rationale") or {},
                "source_count": source_count,
                "major_event_count": major_event_count,
                "minor_event_count": minor_event_count,
                "coverage_state": coverage_state,
                "coverage_note": coverage_note,
                "is_provisional": coverage_state != "substantive",
                "llm_scoring_used": True,
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
