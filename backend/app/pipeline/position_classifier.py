from ..services.minimax import chatcompletion_text
from .analysis_utils import safe_json_loads


DEFAULT_LABELS = ["core"]

SYSTEM_PROMPT = """You classify public equity holdings into investment style and theme labels.

Return strict JSON with this shape:
{"labels":["growth","ai_theme"],"summary":"one sentence"}

Rules:
- Include 1 to 4 concise snake_case labels.
- Labels may include styles, factor traits, themes, or sensitivities such as growth, value, cyclical, defensive, small_cap, quality, rate_sensitive, ai_theme, consumer_discretionary, healthcare, financials, industrials.
- Use the company/news context when helpful.
- If uncertain, still choose the best available labels.
"""


async def classify_position_batch(
    positions: list[dict], all_events: dict[str, list[dict]]
) -> dict[str, list[str]]:
    if not positions:
        return {}

    positions_text = "\n".join(
        f"- {p.get('ticker', '')}: {p.get('archetype', 'unknown')} archetype, {p.get('shares', 0)} shares @ ${p.get('purchase_price', 0)}"
        for p in positions
    )

    events_text_parts = []
    for p in positions:
        ticker = p.get("ticker", "")
        events = all_events.get(ticker, [])[:5]
        if not events:
            events_text_parts.append(f"- {ticker}: no recent events")
        else:
            ev_summary = "\n".join(
                f"  • {e.get('title', '')[:80]}: {e.get('summary', '')[:120]}"
                for e in events
            )
            events_text_parts.append(f"- {ticker}:\n{ev_summary}")

    events_text = "\n".join(events_text_parts)

    prompt = f"""Classify each position into investment style/theme labels.

Positions:
{positions_text}

Recent relevant events per position:
{events_text}

Return JSON with one entry per ticker:
{{
  "classifications": {{
    "AAPL": ["growth", "large_cap", "tech"],
    "NVDA": ["ai_theme", "growth", "semicap"]
  }}
}}

Rules:
- Include 1-4 snake_case labels per ticker: styles (growth/value/cyclical/defensive), themes (ai_theme/consumer_discretionary/healthcare/rate_sensitive), sizes (large_cap/small_cap)
- Use archetype as fallback if no events
- If uncertain, pick best available labels"""

    result_text = chatcompletion_text(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=600,
    )

    import json

    try:
        parsed = json.loads(result_text)
        return parsed.get("classifications", {})
    except:
        return {p.get("ticker"): [p.get("archetype", "core")] for p in positions}


async def classify_position(position: dict, related_events: list[dict]) -> dict:
    if not related_events:
        fallback = position.get("archetype") or DEFAULT_LABELS[0]
        return {
            "labels": [fallback],
            "summary": f"{position.get('ticker', 'This holding')} is currently tracked as {fallback}.",
        }

    event_summary = "\n".join(
        f"- {event.get('title', '')}: {event.get('summary', '')[:180]}"
        for event in related_events[:5]
    )
    prompt = f"""Position:
- Ticker: {position.get("ticker", "")}
- Shares: {position.get("shares", 0)}
- Purchase price: {position.get("purchase_price", 0)}
- Existing manual archetype: {position.get("archetype", "unknown")}

Recent relevant events:
{event_summary}
"""

    result_text = chatcompletion_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=400,
    )

    parsed = safe_json_loads(result_text, {})
    labels = parsed.get("labels") or [position.get("archetype") or DEFAULT_LABELS[0]]
    labels = [str(label).strip() for label in labels if str(label).strip()]

    return {
        "labels": labels[:4] or DEFAULT_LABELS,
        "summary": parsed.get("summary")
        or f"{position.get('ticker', 'This holding')} is best understood through labels: {', '.join(labels[:4] or DEFAULT_LABELS)}.",
    }
