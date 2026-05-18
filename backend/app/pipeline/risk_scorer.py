from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from ..services.minimax import chatcompletion_text
from .analysis_utils import (
    clamp_score,
    extract_json_object,
    score_to_grade,
    grade_direction,
    format_rationale,
    evidence_strength,
    calculate_weighted_score,
    V2_DIMENSION_KEYS,
)
from .structural_scorer import (
    smooth_score_change,
)

SYSTEM_PROMPT = """You are a risk rating system. Given the position context and event evidence below, score this position across 5 risk dimensions and write a concise risk rationale.

Scale: 0 = penny-stock-like / very risky. 100 = treasury-like / very safe. Higher = lower risk.

Position:
- Ticker: {ticker}
- Shares: {shares} @ ${purchase_price}
- Approximate position value: ${position_value}
- Inferred labels: {labels}
- Position report summary: {summary}

Long-form position report: {long_report}

Scoring criteria:
1. financial_health (0-100): Strong balance sheet, cash flow, coverage ratios → high. Weak fundamentals, high leverage → low.
2. news_sentiment (0-100): Positive/supportive news → high. Negative/dangerous news → low. 50 only when truly balanced.
3. macro_exposure (0-100): Less macro-sensitive / more treasury-like → high. More macro-sensitive / more speculative → low.
4. sector_exposure (0-100): Strong sector with broad participation → high. Weak, concentrated, or volatile sector → low.
5. volatility (0-100): Low, stable, or falling volatility → high. High, rising, or extreme drawdown → low.

How to write "reasoning" — the investor-facing rationale:
FORMAT: Header line + max 2 driver lines. No paragraphs. No hedging.
Example:
BBB — Stable, Watch Points (↑ worsening)
Earnings miss on revenue weakness
Sector rotation into defensives

Rules:
1. First line: [GRADE] — [Risk Level] ([arrow direction])
   - Risk Level per the bond-rating scale: AAA=Treasury-Grade, AA=Investment-Grade Safe, A=Solid, BBB=Stable Watch Points, BB=Mixed Signals, B=Elevated Risk, CCC=High Risk, CC=Severe Risk, C=Distressed, F=Failure Mode
   - Arrow: ↓ improving if score improved >2pts, ↑ worsening if score dropped >2pts, → stable otherwise
2. Next 1-2 lines: specific, causal risk drivers. Each driver ≤60 chars.
3. Each driver MUST name a concrete event, metric change, or sector theme:
   ✅ "Earnings miss on revenue weakness"
   ✅ "High rate sensitivity"
   ✅ "Valuation stretched vs earnings"
   ✅ "Weak revenue trend"
   ❌ "Mixed signals across sectors"
   ❌ "Market uncertainty"
   ❌ "Could impact performance"
4. If evidence is thin (<3 events), write: "Limited data — risk based on fundamentals" as the only driver.
5. Total output ≤140 chars preferred.

Banned words — DO NOT USE: may, could, would, suggests, indicates, sentiment, momentum, thesis, coverage, provisional, research, analyst, monitor, watch.
Write like a credit rating bulletin — direct, specific, concrete. Not a research note, not a process description.

How to write "dimension_rationale" — one short phrase per dimension:
- financial_health: what the fundamentals show about structural strength
- news_sentiment: what the news means for risk
- macro_exposure: how macro conditions affect risk
- sector_exposure: how the sector state affects risk
- volatility: what is driving volatility behavior

Forbidden language: dimension scores, "the model", "the score reflects", "based on the dimension", "data across N sources", internal evidence labels, implementation jargon. Avoid returning 50 for every dimension unless the evidence is genuinely neutral.

Respond in this exact JSON format (no markdown, no explanation):
{{"financial_health": 0-100, "news_sentiment": 0-100, "macro_exposure": 0-100, "sector_exposure": 0-100, "volatility": 0-100, "grade": "AAA|AA|A|BBB|BB|B|CCC|CC|C|F", "reasoning": "concise risk rationale per rules above", "dimension_rationale": {{"financial_health": "...", "news_sentiment": "...", "macro_exposure": "...", "sector_exposure": "...", "volatility": "..."}}}}"""

DIMENSION_KEYS = V2_DIMENSION_KEYS


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
    vol_v = clamp_score(scores.get("volatility"), 0)
    sector_v = clamp_score(scores.get("sector_exposure"), 0)
    fin_v = clamp_score(scores.get("financial_health"), 0)

    drivers: list[str] = []

    if news_v <= 35:
        drivers.append("Negative company-specific news")
    elif news_v >= 65:
        drivers.append("Positive news support")

    if macro_v <= 35:
        drivers.append("Macro pressure on the sector")
    elif macro_v <= 45:
        drivers.append("Rate sensitivity adds risk")

    if sector_v <= 40:
        drivers.append("Sector concentration risk")

    if vol_v <= 40:
        drivers.append("Elevated volatility")

    if fin_v <= 45:
        drivers.append("Weak financial health")

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


# Truth-spec "usable" article: fully enriched and complete. Headline-only,
# paywalled/blocked, rejected, partial, or failed rows must NOT count toward
# the news dimension or its evidence — otherwise a ticker with zero usable
# articles can present a confident (false) news_sentiment.
_NON_USABLE_STATUSES = {"partial", "enrichment_failed", "rejected", "headline_only", "failed"}

# Required for News Sentiment to be scored at all (MVP threshold). Below this
# the dimension is Limited Data (None) and excluded from the composite.
MIN_USABLE_ARTICLES_FOR_NEWS = 3


def _is_strict_usable_event(event: dict | None) -> bool:
    if not isinstance(event, dict):
        return False
    if event.get("sentiment_score") is None:
        return False
    if not str(event.get("tldr") or "").strip():
        return False
    if not str(event.get("what_it_means") or "").strip():
        return False
    if not (event.get("key_implications") or []):
        return False
    if event.get("headline_only"):
        return False
    if event.get("paywalled") or event.get("paywall_detected"):
        return False
    if str(event.get("rejection_reason") or "").strip():
        return False
    if str(event.get("analysis_status") or "").strip().lower() in _NON_USABLE_STATUSES:
        return False
    return True


def _strict_usable_events(events: list[dict] | None) -> list[dict]:
    return [e for e in (events or []) if _is_strict_usable_event(e)]


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

    worsening_major = 0
    improving_major = 0
    for event in event_analyses:
        direction = _risk_direction_value(event.get("risk_direction"))
        significance = str(event.get("significance") or "minor").strip().lower()
        if significance == "major" and direction < 0:
            worsening_major += 1
        if significance == "major" and direction > 0:
            improving_major += 1

    # --- Dimension 1: Financial Health (0-100) ---
    fin = _score_financial_health(ticker_metadata)
    fin_rationale = _fin_rationale(ticker_metadata, fin)

    # --- Dimension 2: News Sentiment (0-100) ---
    # Only fully-usable articles drive this dimension. Below the MVP threshold
    # it is Limited Data (None) so calculate_weighted_score excludes it from
    # the composite rather than diluting toward a false neutral 50.
    usable_events = _strict_usable_events(event_analyses)
    if len(usable_events) < MIN_USABLE_ARTICLES_FOR_NEWS:
        news_sentiment = None
        news_rationale = (
            f"Limited data: only {len(usable_events)} fully-usable recent article(s) "
            f"(need {MIN_USABLE_ARTICLES_FOR_NEWS}). News Sentiment is excluded from the composite."
        )
    else:
        news_delta = 0.0
        for event in usable_events:
            direction = _risk_direction_value(event.get("risk_direction"))
            significance = str(event.get("significance") or "minor").strip().lower()
            confidence = min(max(_safe_float(event.get("confidence"), 0.5), 0.2), 1.0)
            age_days = _event_age_days(event)
            recency = max(0.35, 1.0 - min(age_days, 14.0) / 20.0)
            magnitude = 15 if significance == "major" else 7
            news_delta += direction * magnitude * confidence * recency
        news_sentiment = clamp_score(round(50 + news_delta), 0)
        news_rationale = (
            f"News risk is driven by {worsening_major} major negative development(s) "
            f"and improved by {improving_major} positive one(s)."
        )

    # --- Dimension 3: Macro Exposure (0-100) ---
    macro_exposure = _score_macro_exposure(ticker_metadata)
    macro_rationale = _macro_rationale(ticker_metadata, macro_exposure)

    # --- Dimension 4: Sector Exposure (0-100) ---
    sector_exposure = _score_sector_exposure(ticker_metadata)
    sector_rationale = _sector_rationale(ticker_metadata, sector_exposure)

    # --- Dimension 5: Volatility (0-100) ---
    volatility = _score_volatility(ticker_metadata, worsening_major, improving_major)
    vol_rationale = _vol_rationale(ticker_metadata, volatility, worsening_major)

    normalized_scores = {
        "financial_health": fin,
        "news_sentiment": news_sentiment,
        "macro_exposure": macro_exposure,
        "sector_exposure": sector_exposure,
        "volatility": volatility,
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
        str(position_data.get("ticker") or "this ticker"),
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

    return {
        **normalized_scores,
        "total_score": total,
        "grade": grade,
        "grade_direction": grade_direction(total, position_data.get("previous_total_score")),
        "score_delta": int(round(total - position_data.get("previous_total_score", total))),
        "reasoning": formatted_reasoning,
        "evidence_summary": position_data.get("summary", ""),
        "dimension_rationale": {
            "financial_health": fin_rationale,
            "news_sentiment": news_rationale,
            "macro_exposure": macro_rationale,
            "sector_exposure": sector_rationale,
            "volatility": vol_rationale,
        },
        "source_count": source_count,
        "major_event_count": major_event_count,
        "minor_event_count": minor_event_count,
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "is_provisional": coverage_state != "substantive",
        "evidence_strength": evidence_strength(source_count),
        "llm_scoring_used": False,
    }


# ════════════════════════════════════════════════════════════════════════════
# V2 Dimension Scorers
# ════════════════════════════════════════════════════════════════════════════

def _score_financial_health(metadata: dict) -> int:
    d_e = _safe_float(metadata.get("debt_to_equity"))
    fcf_margin = _safe_float(metadata.get("fcf_margin"))
    interest_cov = _safe_float(metadata.get("interest_coverage"))
    current_ratio = _safe_float(metadata.get("current_ratio"))
    rev_growth = _safe_float(metadata.get("revenue_growth_trend"))

    score = 50.0

    if d_e > 0:
        if d_e <= 0.3:
            score += 8
        elif d_e <= 0.7:
            score += 4
        elif d_e <= 1.5:
            score += 0
        elif d_e <= 3.0:
            score -= 6
        else:
            score -= 12

    if fcf_margin > 0:
        if fcf_margin >= 0.20:
            score += 10
        elif fcf_margin >= 0.10:
            score += 6
        elif fcf_margin >= 0.05:
            score += 2
        else:
            score -= 4

    if interest_cov > 0:
        if interest_cov >= 20:
            score += 8
        elif interest_cov >= 5:
            score += 4
        elif interest_cov >= 2:
            score += 0
        else:
            score -= 6

    if current_ratio > 0:
        if current_ratio >= 2.0:
            score += 6
        elif current_ratio >= 1.0:
            score += 2
        elif current_ratio < 0.5:
            score -= 5

    if rev_growth:
        if rev_growth >= 0.30:
            score += 8
        elif rev_growth >= 0.10:
            score += 4
        elif rev_growth >= 0.0:
            score += 1
        else:
            score -= 5

    if metadata.get("profitability_profile") == "profitable":
        score += 4
    elif metadata.get("profitability_profile") == "unprofitable":
        score -= 5

    return clamp_score(round(score), 0)


def _fin_rationale(metadata: dict, score: int) -> str:
    parts = []
    d_e = _safe_float(metadata.get("debt_to_equity"))
    fcf_margin = _safe_float(metadata.get("fcf_margin"))
    if d_e > 0:
        parts.append(f"D/E {d_e:.2f}")
    if fcf_margin > 0:
        parts.append(f"FCF margin {fcf_margin:.0%}")
    if parts:
        return f"Financials reflect {', '.join(parts)}."
    return "Fundamentals based on available data."


def _score_macro_exposure(metadata: dict) -> int:
    factor_breakdown = metadata.get("factor_breakdown") or {}
    if isinstance(factor_breakdown, str):
        import json

        try:
            factor_breakdown = json.loads(factor_breakdown)
        except Exception:
            factor_breakdown = {}
    reg = factor_breakdown.get("macro_regression") or {}
    if isinstance(reg, dict) and not reg.get("limited_data"):
        sensitivity_score = reg.get("sensitivity_score")
        if sensitivity_score is None:
            coefficients = reg.get("coefficients") or {}
            sensitivity = math.sqrt(
                sum(float(value) ** 2 for value in coefficients.values())
            )
            sensitivity_score = 100.0 * (1.0 - min(1.0, sensitivity / 5.0))
        if sensitivity_score is not None:
            return clamp_score(round(sensitivity_score), 0)

    beta = abs(_safe_float(metadata.get("beta"), 0.0))
    macro_sens = str(metadata.get("macro_sensitivity") or "moderate").lower()

    score = 65.0

    if beta > 0:
        if beta <= 0.8:
            score += 8
        elif beta <= 1.2:
            score += 2
        elif beta <= 1.8:
            score -= 6
        else:
            score -= 14

    if macro_sens == "low":
        score += 5
    elif macro_sens == "very_high":
        score -= 10
    elif macro_sens == "high":
        score -= 5

    return clamp_score(round(score), 0)


def _macro_rationale(metadata: dict, score: int) -> str:
    factor_breakdown = metadata.get("factor_breakdown") or {}
    if isinstance(factor_breakdown, str):
        import json

        try:
            factor_breakdown = json.loads(factor_breakdown)
        except Exception:
            factor_breakdown = {}
    reg = factor_breakdown.get("macro_regression") or {}
    if isinstance(reg, dict) and reg.get("r_squared") is not None and not reg.get("limited_data"):
        coef = reg.get("coefficients", {})
        top_factor = max(coef.items(), key=lambda x: abs(x[1])) if coef else ("market", 0.0)
        return (
            f"Regression R\xb2={reg['r_squared']:.2f}, "
            f"top driver: {top_factor[0].upper()} ({top_factor[1]:.3f})."
        )

    beta = _safe_float(metadata.get("beta"))
    if beta:
        return f"Beta of {beta:.2f} drives macro sensitivity."
    return "Macro sensitivity based on sector profile."


def _score_sector_exposure(metadata: dict) -> int:
    sector = str(metadata.get("sector") or "").strip().lower()
    market_cap = _safe_float(metadata.get("market_cap"))

    score = 65.0

    defensive = {"healthcare", "consumer staples", "utilities"}
    cyclical = {"financials", "energy", "real estate", "realestate", "materials", "industrials"}

    if sector in defensive:
        score += 5
    elif sector in cyclical:
        score -= 4

    if market_cap and market_cap >= 200e9:
        score += 3
    elif market_cap and market_cap < 2e9:
        score -= 4

    return clamp_score(round(score), 0)


def _sector_rationale(metadata: dict, score: int) -> str:
    sector = str(metadata.get("sector") or "").title()
    if sector:
        return f"Sector exposure shaped by {sector} profile."
    return "Sector exposure based on industry classification."


def _score_volatility(metadata: dict, worsening_major: int, improving_major: int) -> int:
    volatility_proxy = _safe_float(metadata.get("volatility_proxy"), 0.0)
    beta = abs(_safe_float(metadata.get("beta"), 0.0))

    score = 78.0 - (volatility_proxy * 40)
    if beta:
        score -= min(18, max(0.0, (beta - 1.0) * 10))
    score -= worsening_major * 5
    score += improving_major * 3
    return clamp_score(round(score), 0)


def _vol_rationale(metadata: dict, score: int, worsening_major: int) -> str:
    beta = _safe_float(metadata.get("beta"))
    if beta and beta > 1.2:
        return f"Beta of {beta:.2f} amplifies volatility exposure."
    if worsening_major:
        return "Recent negative events add upward pressure to volatility."
    return "Volatility is within normal range for this profile."


# ════════════════════════════════════════════════════════════════════════════
# LLM path
# ════════════════════════════════════════════════════════════════════════════

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


async def score_position(
    position: dict,
    position_report: dict,
    inferred_labels: list[str] | None = None,
) -> dict:
    position_data = {
        **position,
        **position_report,
        "inferred_labels": inferred_labels
        or position_report.get("inferred_labels", []),
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
    missing_dimensions = [key for key in DIMENSION_KEYS if scores.get(key) is None]
    if missing_dimensions:
        logger.warning(
            "score_position parse failure for %s; missing=%s; raw=%r",
            position.get("ticker", ""),
            missing_dimensions,
            (result_text or "")[:800],
        )
        retry_text, retry_scores = _request_scores()
        retry_missing = [
            key for key in DIMENSION_KEYS if retry_scores.get(key) is None
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
        key: clamp_score(scores.get(key), 0)
        for key in DIMENSION_KEYS
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
            str(position_data.get("ticker") or "this ticker"),
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
        **normalized_scores,
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

    worsening_major = 0
    improving_major = 0
    for event in recent_events:
        direction = _risk_direction_value(event.get("risk_direction"))
        significance = str(event.get("significance") or "minor").strip().lower()
        if significance == "major" and direction < 0:
            worsening_major += 1
        if significance == "major" and direction > 0:
            improving_major += 1

    fin = _score_financial_health(ticker_metadata)
    macro = _score_macro_exposure(ticker_metadata)
    sector = _score_sector_exposure(ticker_metadata)
    vol = _score_volatility(ticker_metadata, worsening_major, improving_major)

    # Only fully-usable articles drive News Sentiment. Do not fall back to
    # `confidence` for unenriched rows — that previously let headline-only /
    # partial rows produce a confident (false) score (the MRK case).
    usable_events = _strict_usable_events(recent_events)
    weighted_news = 0.0
    total_weight = 0.0
    article_count = len(usable_events)
    for e in usable_events:
        recency_w = _safe_float(e.get("recency_weight"), 1.0)
        source_w = _safe_float(e.get("source_weight"), 1.0)
        sent = _safe_float(e.get("sentiment_score"))
        w = recency_w * source_w
        weighted_news += sent * w
        total_weight += w
    if article_count >= MIN_USABLE_ARTICLES_FOR_NEWS and total_weight > 0:
        news = clamp_score(round(weighted_news / total_weight), 0)
    elif article_count >= MIN_USABLE_ARTICLES_FOR_NEWS:
        news = clamp_score(round(50 + sum(
            _risk_direction_value(e.get("risk_direction")) * 7
            for e in usable_events
        )), 0)
    else:
        news = None

    normalized = {
        "financial_health": fin,
        "news_sentiment": news,
        "macro_exposure": macro,
        "sector_exposure": sector,
        "volatility": vol,
    }
    weighted = calculate_weighted_score(normalized)
    total = round(
        smooth_score_change(
            new_score=weighted,
            previous_score=previous_safety_score,
        ),
        1,
    )
    grade = score_to_grade(total)

    source_count = len(recent_events)
    major_event_count = sum(
        1 for e in recent_events
        if str(e.get("significance") or "minor").strip().lower() == "major"
    )
    minor_event_count = max(source_count - major_event_count, 0)

    if source_count == 0:
        coverage_state = "provisional"
        coverage_note = "No recent event data was available."
    elif source_count <= 2:
        coverage_state = "thin"
        coverage_note = f"Limited data: {source_count} recent event(s)."
    else:
        coverage_state = "substantive"
        coverage_note = f"{source_count} recent event(s) supported this score."

    structural_reasoning = format_rationale(
        grade=grade,
        direction=grade_direction(total, previous_safety_score),
        raw_text="Structural profile dominant",
        scores=normalized,
        source_count=source_count,
    )

    existing_factor_breakdown = ticker_metadata.get("factor_breakdown") or {}
    if isinstance(existing_factor_breakdown, str):
        import json

        try:
            existing_factor_breakdown = json.loads(existing_factor_breakdown)
        except Exception:
            existing_factor_breakdown = {}

    return {
        "safety_score": total,
        "total_score": total,
        "composite_score": total,
        "structural_base_score": total,
        "macro_adjustment": 0.0,
        "event_adjustment": 0.0,
        "confidence": 0.75,
        "grade": grade,
        "grade_direction": grade_direction(total, previous_safety_score),
        "score_delta": int(round(total - previous_safety_score)) if previous_safety_score is not None else None,
        "reasoning": structural_reasoning,
        "dimension_rationale": {
            "financial_health": _fin_rationale(ticker_metadata, fin),
            "news_sentiment": "Event-driven sentiment from available articles.",
            "macro_exposure": _macro_rationale(ticker_metadata, macro),
            "sector_exposure": _sector_rationale(ticker_metadata, sector),
            "volatility": _vol_rationale(ticker_metadata, vol, worsening_major),
        },
        "factor_breakdown": {
            **existing_factor_breakdown,
            "ai_dimensions": normalized,
        },
        **normalized,
        "source_count": source_count,
        "major_event_count": major_event_count,
        "minor_event_count": minor_event_count,
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "is_provisional": coverage_state != "substantive",
        "evidence_strength": evidence_strength(source_count),
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
            f'"{ticker}": {{"financial_health": 50, "news_sentiment": 50, "macro_exposure": 50, "sector_exposure": 50, "volatility": 50, "grade": "BBB", "reasoning": "...", "dimension_rationale": {{"financial_health": "...", "news_sentiment": "...", "macro_exposure": "...", "sector_exposure": "...", "volatility": "..."}}, "evidence_summary": "..."}}'
            for ticker in tickers
        )
        prompt = f"""Score each position across 5 dimensions (0-100) and assign a grade.

Scale: 0 = penny-stock-like / very risky, 100 = treasury-like / very safe. Higher = lower risk.

{positions_text}

{evidence_block if evidence_block else ""}

Return EXACTLY this JSON format (no markdown, no explanation, no thinking):
{{"scores": {{{score_example}}}}}

        Scoring criteria:
        - financial_health: strong balance sheet, cash flow, coverage=high (70-100), weak fundamentals=low (0-40)
        - news_sentiment: positive/supportive news=high (70-100), negative/dangerous news=low (0-40), neutral=50 only when truly balanced
        - macro_exposure: less macro-sensitive=high (70-100), more macro-sensitive=low (0-40)
        - sector_exposure: strong sector with broad participation=high (70-100), weak/concentrated sector=low (0-40)
        - volatility: low/stable/falling volatility=high (70-100), high/rising volatility=low (0-40)
        - Grade bands: AAA (90-100), AA (80-89), A (70-79), BBB (60-69), BB (50-59), B (40-49), CCC (30-39), CC (20-29), C (10-19), F (0-9)

        How to write "reasoning" — strict credit-rating format:
        FORMAT: [GRADE] — [Risk Level] ([arrow]) + max 2 driver lines. Each driver ≤60 chars.
        Arrows: ↓ improving if score improved, ↑ worsening if score dropped, → stable
        Example:
        BBB — Stable, Watch Points (↑ worsening)
        Earnings miss on revenue weakness
        Sector rotation into defensives

        Rules:
        1. Each driver MUST name a concrete event, metric change, or sector theme.
        2. If evidence is thin (<3 events), write: "Limited data — risk based on fundamentals"
        3. No paragraphs. No hedging. No "may", "could", "would", "suggests", "indicates"

        Important:
        - Do not return 50 across all five dimensions unless the evidence is genuinely absent.
        - If the evidence is directional, move the relevant dimensions away from 50.

        Forbidden: dimension scores in rationale, "the model", "the score reflects", internal evidence labels, "thesis", "positive momentum", "macro headwinds", "provisional", "sentiment", "confirms", "coverage", "monitor", "research", "analyst", "watch", "portfolio weighting".

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

        if not all_scores:
            for ticker in tickers:
                ticker_upper = ticker.upper()
                ticker_scores = {}
                for dim in DIMENSION_KEYS:
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
                key: clamp_score(raw_scores.get(key), 0)
                for key in DIMENSION_KEYS
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
            formatted_reasoning = format_rationale(
                grade=grade,
                direction=grade_direction(total, position.get("previous_total_score")),
                raw_text=reasoning,
                scores=normalized,
                source_count=source_count,
            )
            results[result_index] = {
                **normalized,
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
                "factor_breakdown": {
                    "ai_dimensions": normalized,
                },
            }

    return results
