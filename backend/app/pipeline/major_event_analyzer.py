import logging
from ..services.minimax import chatcompletion_text
from .analysis_utils import safe_json_loads, extract_json_list

logger = logging.getLogger(__name__)


MAJOR_EVENT_SYSTEM_PROMPT = """You are a major-event portfolio risk analyst.

Return strict JSON:
{
  "analysis_text": "3-6 sentence analysis",
  "impact_horizon": "immediate|near_term|long_term",
  "risk_direction": "improving|neutral|worsening",
  "confidence": 0.0-1.0,
  "scenario_summary": "one sentence",
  "key_implications": ["...", "..."],
  "followup_notes": ["...", "..."]
}
"""


def _normalize_result(payload: dict | None) -> dict | None:
    if not payload:
        return None
    analysis_text = payload.get("analysis_text") or payload.get("analysis") or ""
    if not analysis_text:
        return None
    return {
        "analysis_text": analysis_text,
        "impact_horizon": payload.get("impact_horizon") or "near_term",
        "risk_direction": payload.get("risk_direction") or "neutral",
        "confidence": float(payload.get("confidence") or 0.6),
        "scenario_summary": payload.get("scenario_summary") or "Major event analysis completed.",
        "key_implications": payload.get("key_implications") or [],
        "recommended_followups": payload.get("followup_notes") or payload.get("recommended_followups") or [],
        "provider": "minimax",
    }


def _provisional_result(news_item: dict) -> dict:
    title = news_item.get("title", "Major event")
    evidence_quality = news_item.get("evidence_quality", "title_only")
    return {
        "analysis_text": f"{title} looks material enough to monitor closely, but the impact is still provisional until follow-up details confirm the scale.",
        "impact_horizon": "near_term",
        "risk_direction": "neutral",
        "confidence": 0.3 if evidence_quality in {"title_only", "headline_summary"} else 0.45,
        "scenario_summary": "Material headline detected — durable impact depends on follow-through.",
        "key_implications": [
            "Watch for management detail, filing support, or market reaction that confirms the event's importance."
        ],
        "recommended_followups": [
            "Check subsequent company commentary, regulatory disclosures, and earnings implications."
        ],
        "provider": "minimax",
    }


async def analyze_major_event(news_item: dict, position_context: dict) -> dict:
    """Analyze a single major event for a specific position."""
    user_prompt = f"""Event:
Title: {news_item.get("title", "")}
Summary: {news_item.get("summary", "")}
Body: {news_item.get("body", "")[:1600]}

Position context:
- Ticker: {position_context.get("ticker", "")}
- Shares: {position_context.get("shares", 0)}
- Purchase price: {position_context.get("purchase_price", 0)}
- Archetype: {position_context.get("archetype", "unknown")}
- Inferred labels: {", ".join(position_context.get("inferred_labels", []))}
"""
    try:
        result = chatcompletion_text(
            messages=[
                {"role": "system", "content": MAJOR_EVENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=900,
        )
    except Exception:
        return _provisional_result(news_item)

    parsed = safe_json_loads(result, {})
    return _normalize_result(parsed) or {
        "analysis_text": "Major event analysis was unavailable.",
        "impact_horizon": "near_term",
        "risk_direction": "neutral",
        "confidence": 0.4,
        "scenario_summary": "Analysis unavailable.",
        "key_implications": [],
        "recommended_followups": [],
        "provider": "minimax",
    }


async def analyze_major_events_batch(news_items: list[dict], position_context: dict) -> list[dict]:
    """Analyze multiple major events for a specific position in one call."""
    if not news_items:
        return []

    events_text = []
    for i, item in enumerate(news_items):
        title = item.get("title", "")[:300]
        summary = item.get("summary", "")[:500]
        body = item.get("body", "")[:800]
        events_text.append(f"[{i}] Title: {title}\n    Summary: {summary}\n    Body: {body}")

    ticker = position_context.get("ticker", "")
    shares = position_context.get("shares", 0)
    purchase_price = position_context.get("purchase_price", 0)
    archetype = position_context.get("archetype", "unknown")
    labels = ", ".join(position_context.get("inferred_labels", []))

    prompt = f"""Position context:
- Ticker: {ticker}
- Shares: {shares}
- Purchase price: {purchase_price}
- Archetype: {archetype}
- Inferred labels: {labels}

For each event below, analyze the potential impact on this position.

Events:
{chr(10).join(events_text)}

Return a JSON array with one object per event in order.
Each object has: analysis_text, impact_horizon, risk_direction, confidence, scenario_summary, key_implications, followup_notes."""

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": MAJOR_EVENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    parsed = extract_json_list(result, None)
    results = []
    if isinstance(parsed, list) and len(parsed) == len(news_items):
        for p in parsed:
            normalized = _normalize_result(p)
            results.append(normalized if normalized else _provisional_result(news_items[len(results)]))
    else:
        results = [_provisional_result(item) for item in news_items]

    return results


async def analyze_major_events_shared_batch(news_items: list[dict]) -> list[dict]:
    """Analyze major events without a specific position context (shared/macro events)."""
    if not news_items:
        return []

    events_text = []
    for i, item in enumerate(news_items):
        title = item.get("title", "")[:320]
        summary = item.get("summary", "")[:520]
        body = item.get("body", "")[:900]
        evidence_quality = item.get("evidence_quality", "title_only")
        events_text.append(
            f"[{i}] Evidence quality: {evidence_quality}\n    Title: {title}\n    Summary: {summary}\n    Body: {body}"
        )

    prompt = f"""For each event below, analyze the potential fundamental and valuation impact without assuming a specific holder.

If evidence quality is title_only or headline_summary, do not act as if you read a full article. Lower confidence and describe the read as provisional.

Events:
{chr(10).join(events_text)}

Return a JSON array with one object per event in order.
Each object has: analysis_text, impact_horizon, risk_direction, confidence, scenario_summary, key_implications, followup_notes."""

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": MAJOR_EVENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=2600,
    )

    parsed = extract_json_list(result, None)
    results = []
    if isinstance(parsed, list) and len(parsed) == len(news_items):
        for i, payload in enumerate(parsed):
            normalized = _normalize_result(payload)
            results.append(normalized if normalized else _provisional_result(news_items[i]))
        return results

    return [_provisional_result(item) for item in news_items]
