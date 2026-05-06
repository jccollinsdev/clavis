import logging
from datetime import datetime, timezone

from ..services.minimax import chatcompletion_text
from .analysis_utils import clamp_score, extract_json_object, score_to_grade, grade_direction, sanitize_rationale, format_rationale, evidence_strength
from .structural_scorer import (
    calculate_structural_base_score,
    calculate_macro_adjustment,
    calculate_event_adjustment,
    calculate_final_safety_score,
    smooth_score_change,
    get_daily_move_cap,
)

SYSTEM_PROMPT = """You are a risk rating system. Given the position context and event evidence below, score this position across 4 risk dimensions and write a concise risk rationale.

Scale: 0 = penny-stock-like / very risky. 100 = treasury-like / very safe. Higher = lower risk.

Position:
- Ticker: {ticker}
- Shares: {shares} @ ${purchase_price}
- Approximate position value: ${position_value}
- Inferred labels: {labels}
- Position report summary: {summary}

Long-form position report: {long_report}

Scoring criteria:
1. news_sentiment (0-100): Positive/supportive news → high. Negative/dangerous news → low. 50 only when truly balanced.
2. macro_exposure (0-100): Less macro-sensitive / more treasury-like → high. More macro-sensitive / more speculative → low.
3. position_sizing (0-100): Appropriately sized, prudent exposure → high. Oversized or speculative → low.
4. volatility_trend (0-100): Falling volatility / stable trend → high. Rising volatility / unstable → low.

How to write "reasoning" — the investor-facing rationale:
FORMAT: Header line + max 2 driver lines. No paragraphs. No hedging.
Example:
C — Elevated Risk (↑ worsening)
Earnings miss on revenue weakness
Sector rotation into defensives

Rules:
1. First line: [GRADE] — [Risk Level] ([arrow direction])
   - Risk Level: A=Low Risk, B=Moderate Risk, C=Elevated Risk, D=High Risk, F=Severe Risk
   - Arrow: ↓ improving if score improved >2pts, ↑ worsening if score dropped >2pts, → stable otherwise
2. Next 1-2 lines: specific, causal risk drivers. Each driver ≤60 chars.
3. Each driver MUST name a concrete event, metric change, or sector theme:
   ✅ "Earnings miss on revenue weakness"
   ✅ "High rate sensitivity"
   ✅ "Valuation stretched vs earnings"
   ✅ "Weak revenue momentum"
   ❌ "Mixed signals across sectors"
   ❌ "Market uncertainty"
   ❌ "Positive momentum"
   ❌ "Could impact performance"
4. If evidence is thin (<3 events), write: "Limited data — risk based on fundamentals" as the only driver.
5. Total output ≤140 chars preferred.

Banned words — DO NOT USE: may, could, would, suggests, indicates, sentiment, momentum, thesis, coverage, provisional, research, analyst, monitor, watch.
Write like a credit rating bulletin — direct, specific, concrete. Not a research note, not a process description.

How to write "dimension_rationale" — one short phrase per dimension:
- news_sentiment: what the news means for risk (not "the score is 60")
- macro_exposure: how macro conditions affect risk
- position_sizing: whether the position size amplifies risk
- volatility_trend: what is driving volatility behavior

Forbidden language: dimension scores, "the model", "the score reflects", "based on the dimension", "data across N sources", internal evidence labels (full_body, title_only, headline_summary), implementation jargon. Avoid returning 50 for every dimension unless the evidence is genuinely neutral.

Respond in this exact JSON format (no markdown, no explanation):
{{"news_sentiment": 0-100, "macro_exposure": 0-100, "position_sizing": 0-100, "volatility_trend": 0-100, "grade": "A|B|C|D|F", "reasoning": "concise risk rationale per rules above", "dimension_rationale": {{"news_sentiment": "...", "macro_exposure": "...", "position_sizing": "...", "volatility_trend": "..."}}}}"""

DIMENSION_KEYS = [
    "news_sentiment",
    "macro_exposure",
    "position_sizing",
    "volatility_trend",
]

def _neutral_dimension_count(scores: dict | None) -> int:
    if not isinstance(scores, dict):
        return len(DIMENSION_KEYS)
    return sum(clamp_score(scores.get(key), 0) == 50 for key in DIMENSION_KEYS)


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


def _data_state_for_position(position_data: dict) -> tuple[str, int, int, int, str]:
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
        coverage_note = "Score based on fundamentals — limited recent news available."
    elif source_count <= 2:
        coverage_state = "thin"
        word = "source" if source_count == 1 else "sources"
        coverage_note = f"Limited data: {source_count} recent {word} reviewed."
    else:
        coverage_state = "substantive"
        word = "source" if source_count == 1 else "sources"
        coverage_note = f"{source_count} recent {word} reviewed."

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
    news_v = clamp_score(scores.get("news_sentiment"), 0)
    macro_v = clamp_score(scores.get("macro_exposure"), 0)
    vol_v = clamp_score(scores.get("volatility_trend"), 0)
    sizing_v = clamp_score(scores.get("position_sizing"), 0)

    drivers: list[str] = []

    if news_v <= 35:
        drivers.append("Negative company-specific news")
    elif news_v >= 65:
        drivers.append("Positive news support")

    if macro_v <= 35:
        drivers.append("Macro pressure on the sector")
    elif macro_v <= 45:
        drivers.append("Rate sensitivity adds risk")

    if sizing_v <= 40:
        drivers.append("Concentration amplifies downside")

    if vol_v <= 40:
        drivers.append("Elevated volatility")

    if not drivers:
        if news_v <= 45:
            drivers.append("Negative news pressure")
        elif news_v >= 55:
            drivers.append("Positive news support")
        elif macro_v <= 45:
            drivers.append("Macro sensitivity")
        elif vol_v <= 45:
            drivers.append("Moderate volatility")
        else:
            drivers.append("Structural profile dominant")

    if coverage_state in ("provisional", "thin"):
        drivers = drivers[:1] + ["Limited data — fundamentals dominate"]

    return "\n".join(drivers[:2])


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
    if macro_relevance == "challenges" or macro_relevance == "contradicts":
        score -= 18
        rationale_parts.append("overnight macro conditions raise risk for this position")
    elif macro_relevance == "confirms" or macro_relevance == "supports":
        score += 10
        rationale_parts.append("overnight macro backdrop lowers risk for this position")
    else:
        rationale_parts.append("no clear overnight macro shift detected")

    if "rate_sensitive" in labels:
        score -= 6
        rationale_parts.append("rate sensitivity adds cyclical exposure")
    if "defensive" in labels:
        score += 5
        rationale_parts.append("defensive characteristics cushion macro risk")

    sector = str(ticker_metadata.get("sector") or "").strip().lower()
    if sector in {"financials", "energy", "real estate", "realestate"}:
        score -= 3
    elif sector in {"healthcare", "consumer staples", "utilities"}:
        score += 2

    return clamp_score(round(score), 0), "; ".join(rationale_parts)


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
    ) = _data_state_for_position(position_data)
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

    news_sentiment = clamp_score(round(50 + news_delta), 0)
    news_rationale = (
        f"News risk is driven by {worsening_major} major negative development(s) and improved by {improving_major} positive one(s)."
        if event_analyses
        else "No recent news with a clear directional signal — rating defaults to neutral pending new data."
    )

    macro_exposure, macro_rationale = _macro_adjustment_from_context(position_data)

    volatility_proxy = _safe_float(ticker_metadata.get("volatility_proxy"), 0.0)
    beta = abs(_safe_float(ticker_metadata.get("beta"), 0.0))
    volatility_trend = 78 - (volatility_proxy * 40)
    if beta:
        volatility_trend -= min(18, max(0.0, (beta - 1.0) * 10))
    volatility_trend -= worsening_major * 5
    volatility_trend += improving_major * 3
    volatility_trend = clamp_score(round(volatility_trend), 0)
    if beta and volatility_proxy:
        volatility_rationale = f"Beta of {ticker_metadata.get('beta')} and elevated volatility proxy drive near-term price instability, compounded by {worsening_major} negative event(s)."
    elif worsening_major:
        volatility_rationale = f"Recent negative developments add upward pressure to near-term volatility."
    else:
        volatility_rationale = "Volatility is within normal range for this profile — no major event-driven instability detected."

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
    position_sizing = clamp_score(round(sizing_score), 0)
    if portfolio_weight >= 0.2:
        sizing_rationale = f"Concentration risk is elevated — this position represents {portfolio_weight:.0%} of portfolio value, amplifying downside from any adverse development."
    elif portfolio_weight >= 0.1:
        sizing_rationale = f"This position is a meaningful allocation at {portfolio_weight:.0%} of portfolio value, leaving moderate exposure to company-specific risk."
    else:
        sizing_rationale = f"Position sizing is manageable at {portfolio_weight:.0%} of portfolio — company-specific risk is not amplified by concentration."

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
    grade = score_to_grade(total)

    reasoning = _synthesized_reasoning(
        str(position_data.get("ticker") or "this position"),
        normalized_scores,
        coverage_state,
        source_count,
        coverage_note,
        llm_used=False,
        total_score=total,
    )
    formatted_reasoning = format_rationale(
        grade=grade,
        direction=grade_direction(total, position_data.get("previous_total_score")),
        raw_text=reasoning,
        scores=normalized_scores,
        source_count=source_count,
    )
    if position_data.get("previous_grade") and grade != score_to_grade(weighted):
        pass

    return {
        **normalized_scores,
        "total_score": total,
        "grade": grade,
        "grade_direction": grade_direction(total, position_data.get("previous_total_score")),
        "score_delta": int(round(total - position_data.get("previous_total_score", total))),
        "reasoning": formatted_reasoning,
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
        "evidence_strength": evidence_strength(source_count),
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
    values = [clamp_score(scores.get(key), 0) for key in DIMENSION_KEYS]
    return sum(values) / len(values)


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
        "news_sentiment": clamp_score(scores.get("news_sentiment"), 0),
        "macro_exposure": clamp_score(scores.get("macro_exposure"), 0),
        "position_sizing": clamp_score(scores.get("position_sizing"), 0),
        "volatility_trend": clamp_score(scores.get("volatility_trend"), 0),
    }
    (
        coverage_state,
        source_count,
        major_event_count,
        minor_event_count,
        coverage_note,
    ) = _data_state_for_position(position_data)

    weighted = calculate_weighted_score(normalized_scores)
    total = round(
        smooth_score_change(
            new_score=weighted,
            previous_score=position_report.get("previous_total_score"),
        ),
        1,
    )
    grade = score_to_grade(total)
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
    formatted_reasoning = format_rationale(
        grade=grade,
        direction=grade_direction(total, position_report.get("previous_total_score")),
        raw_text=reasoning,
        scores=normalized_scores,
        source_count=source_count,
    )

    return {
        "news_sentiment": normalized_scores["news_sentiment"],
        "macro_exposure": normalized_scores["macro_exposure"],
        "position_sizing": normalized_scores["position_sizing"],
        "volatility_trend": normalized_scores["volatility_trend"],
        "total_score": total,
        "grade": grade,
        "grade_direction": grade_direction(total, position_report.get("previous_total_score")),
        "score_delta": int(round(total - position_report.get("previous_total_score", total))),
        "reasoning": formatted_reasoning,
        "evidence_summary": scores.get("evidence_summary") or position_data.get("summary", ""),
        "dimension_rationale": dimension_rationale,
        "source_count": source_count,
        "major_event_count": major_event_count,
        "minor_event_count": minor_event_count,
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "is_provisional": coverage_state != "substantive",
        "evidence_strength": evidence_strength(source_count),
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
    direction = grade_direction(final_safety, previous_safety_score)
    source_count_struct = len(recent_events)
    structural_drivers = []
    if abs(macro_adj) > 3:
        structural_drivers.append(f"Macro adjustment: {'+' if macro_adj > 0 else ''}{macro_adj}")
    if abs(total_event_adjustment) > 1:
        structural_drivers.append(f"Event adjustment: {'+' if total_event_adjustment > 0 else ''}{total_event_adjustment:.0f}")
    if not structural_drivers:
        structural_drivers.append("Structural profile dominant")
    structural_reasoning = format_rationale(
        grade=safety_grade,
        direction=direction,
        raw_text="\n".join(structural_drivers[:2]),
        scores={"news_sentiment": 50, "macro_exposure": structural_result["structural_base_score"], "position_sizing": 50, "volatility_trend": 50},
        source_count=source_count_struct,
    )
    source_count = len(recent_events)
    major_event_count = sum(
        1
        for event in recent_events
        if str(event.get("significance") or "minor").strip().lower() == "major"
    )
    minor_event_count = max(source_count - major_event_count, 0)
    if source_count == 0:
        coverage_state = "provisional"
        coverage_note = "No recent event data was available, so this structural score uses limited data."
    elif source_count <= 2:
        coverage_state = "thin"
        coverage_note = f"Limited data: only {source_count} recent event(s) were available."
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
        "grade_direction": grade_direction(final_safety, previous_safety_score),
        "score_delta": int(round(final_safety - previous_safety_score)) if previous_safety_score is not None else None,
        "factor_breakdown": factor_breakdown,
        "market_cap_bucket": structural_result.get("market_cap_bucket"),
        "reasoning": structural_reasoning,
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
        "evidence_strength": evidence_strength(source_count),
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

Scale: 0 = penny-stock-like / very risky, 100 = treasury-like / very safe. Higher = lower risk.

{positions_text}

{evidence_block if evidence_block else ""}

Return EXACTLY this JSON format (no markdown, no explanation, no thinking):
{{"scores": {{{score_example}}}}}

        Scoring criteria:
        - news_sentiment: positive/supportive news=high (70-100), negative/dangerous news=low (0-40), neutral=50 only when truly balanced
        - macro_exposure: less macro-sensitive / more treasury-like=high (70-100), more macro-sensitive / more speculative=low (0-40)
        - position_sizing: prudent, appropriately sized exposure=high (70-100), oversized or speculative exposure=low (0-40)
        - volatility_trend: falling volatility / stable trend=high (70-100), rising volatility / unstable behavior=low (0-40)
        - Grade bands: A (80-100), B (65-79), C (50-64), D (35-49), F (0-34)

        How to write "reasoning" — strict credit-rating format:
        FORMAT: [GRADE] — [Risk Level] ([arrow]) + max 2 driver lines. Each driver ≤60 chars.
        Risk Levels: A=Low Risk, B=Moderate Risk, C=Elevated Risk, D=High Risk, F=Severe Risk
        Arrows: ↓ improving if score improved, ↑ worsening if score dropped, → stable
        Example:
        C — Elevated Risk (↑ worsening)
        Earnings miss on revenue weakness
        Sector rotation into defensives

        Rules:
        1. Each driver MUST name a concrete event, metric change, or sector theme:
           ✅ "Earnings miss on revenue weakness"
           ✅ "High rate sensitivity"
           ✅ "Valuation stretched vs earnings"
           ❌ "Mixed signals across sectors"
           ❌ "Market uncertainty"
           ❌ "Could impact performance"
        2. If evidence is thin (<3 events), write: "Limited data — risk based on fundamentals"
        3. No paragraphs. No hedging. No "may", "could", "would", "suggests", "indicates"

        How to write "dimension_rationale" — one sentence per dimension about what is happening, not what the score number is:
        - news_sentiment: what the news means (not "the score is 60")
        - macro_exposure: how macro conditions interact with the position's profile
        - position_sizing: whether the size is appropriate and why
        - volatility_trend: what is driving volatility behavior

        Important:
        - Do not return 50 across all four dimensions unless the evidence is genuinely absent.
        - If the evidence is directional, move the relevant dimensions away from 50.
        - Use the position value and portfolio weight context when estimating position sizing.

        Forbidden: dimension scores in rationale, "the model", "the score reflects", "based on the dimension", "data across N sources", internal evidence labels (full_body, title_only, headline_summary), "thesis", "positive momentum", "macro headwinds", "provisional", "sentiment", "confirms", "coverage", "monitor", "research", "analyst", "watch".

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
            ) = _data_state_for_position(position)
            if _prefer_llm_scoring(position) and has_suspicious_neutral_scores(
                raw_scores
            ):
                logger.warning(
                    "score_positions_batch keeping deterministic fallback for %s due to neutral AI output",
                    ticker,
                )
                continue
            normalized = {
                "news_sentiment": clamp_score(raw_scores.get("news_sentiment"), 0),
                "macro_exposure": clamp_score(raw_scores.get("macro_exposure"), 0),
                "position_sizing": clamp_score(raw_scores.get("position_sizing"), 0),
                "volatility_trend": clamp_score(raw_scores.get("volatility_trend"), 0),
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
            grade = score_to_grade(total)
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
            formatted_reasoning = format_rationale(
                grade=grade,
                direction=grade_direction(total, position.get("previous_total_score")),
                raw_text=reasoning,
                scores=normalized,
                source_count=source_count,
            )
            results[result_index] = {
                "news_sentiment": normalized["news_sentiment"],
                "macro_exposure": normalized["macro_exposure"],
                "position_sizing": normalized["position_sizing"],
                "volatility_trend": normalized["volatility_trend"],
                "total_score": total,
                "grade": grade,
                "grade_direction": grade_direction(total, position.get("previous_total_score")),
                "score_delta": int(round(total - position.get("previous_total_score", total))),
                "reasoning": formatted_reasoning,
                "evidence_summary": raw_scores.get("evidence_summary") or position.get("summary", ""),
                "dimension_rationale": raw_scores.get("dimension_rationale") or {},
                "source_count": source_count,
                "major_event_count": major_event_count,
                "minor_event_count": minor_event_count,
                "coverage_state": coverage_state,
                "coverage_note": coverage_note,
                "is_provisional": coverage_state != "substantive",
                "evidence_strength": evidence_strength(source_count),
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
