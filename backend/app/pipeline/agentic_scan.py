from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_list, extract_json_object

SYSTEM_PROMPT = """You are an investment analyst AI. Given a news item and a stock position, analyze the potential impact on the position.

Position context:
- Ticker: {ticker}
- Inferred labels: {labels}
- Purchase price: ${purchase_price}
- News: {title} - {summary}

Analysis should consider:
1. How does this news affect the company's fundamentals?
2. How does it interact with the holding's style/theme exposure?
3. What is the likely short-term and long-term impact?

Return strict JSON:
{{
  "analysis_text": "2-4 sentence analysis",
  "impact_horizon": "immediate|near_term|long_term",
  "risk_direction": "improving|neutral|worsening",
  "confidence": 0.0-1.0,
  "scenario_summary": "one sentence",
  "key_implications": ["...", "..."],
  "recommended_followups": ["...", "..."]
}}"""


def _fallback_minor_event_analysis(news_item: dict, position: dict) -> dict:
    title = news_item.get("title", "Recent news")
    summary = news_item.get("summary", "")
    ticker = position.get("ticker", "this holding")
    combined = " ".join(part for part in [title, summary] if part).strip()
    trimmed = (
        combined[:280]
        if combined
        else "Recent coverage did not include enough detail for a richer AI summary."
    )
    return {
        "analysis_text": f"{trimmed} For {ticker}, this appears to be a monitorable but not thesis-breaking development absent stronger confirming evidence.",
        "impact_horizon": "near_term",
        "risk_direction": "neutral",
        "confidence": 0.45,
        "scenario_summary": f"{ticker} faces a moderate watch-item rather than a confirmed major catalyst from this event.",
        "key_implications": [
            f"Track whether follow-on reporting changes the significance of '{title}'."
        ],
        "recommended_followups": [
            "Watch for earnings, guidance, regulatory, or management updates that materially change the thesis."
        ],
    }


async def analyze_minor_event(
    news_item: dict, position: dict, inferred_labels: list[str] | None = None
) -> dict:
    prompt = SYSTEM_PROMPT.format(
        ticker=position.get("ticker", ""),
        labels=", ".join(inferred_labels or [position.get("archetype", "growth")]),
        purchase_price=position.get("purchase_price", 0),
        title=news_item.get("title", ""),
        summary=news_item.get("summary", ""),
    )

    result = chatcompletion_text(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800,
    )
    parsed = extract_json_object(result, {})
    fallback = _fallback_minor_event_analysis(news_item, position)
    return {
        "analysis_text": parsed.get("analysis_text") or fallback["analysis_text"],
        "impact_horizon": parsed.get("impact_horizon") or fallback["impact_horizon"],
        "risk_direction": parsed.get("risk_direction") or fallback["risk_direction"],
        "confidence": float(parsed.get("confidence") or fallback["confidence"]),
        "scenario_summary": parsed.get("scenario_summary")
        or fallback["scenario_summary"],
        "key_implications": parsed.get("key_implications")
        or fallback["key_implications"],
        "recommended_followups": parsed.get("recommended_followups")
        or fallback["recommended_followups"],
    }


MINOR_EVENTS_BATCH_PROMPT = """You are an investment analyst AI. Given multiple news items and a stock position, analyze the potential impact of each news item on the position.

Position context:
- Ticker: {ticker}
- Inferred labels: {labels}
- Purchase price: ${purchase_price}

News items to analyze:
{news_items}

For each news item above, return a JSON object with:
- "analysis_text": "2-4 sentence analysis"
- "impact_horizon": "immediate|near_term|long_term"
- "risk_direction": "improving|neutral|worsening"
- "confidence": 0.0-1.0
- "scenario_summary": "one sentence"
- "key_implications": ["...", "..."]
- "recommended_followups": ["...", "..."]

Return a JSON array with one object per news item in order."""


async def analyze_minor_events_batch(
    news_items: list[dict],
    position: dict,
    inferred_labels: list[str] | None = None,
) -> list[dict]:
    if not news_items:
        return []

    labels = ", ".join(inferred_labels or [position.get("archetype", "growth")])
    purchase_price = position.get("purchase_price", 0)

    news_texts = []
    for i, item in enumerate(news_items):
        title = item.get("title", "")[:200]
        summary = item.get("summary", "")[:300]
        news_texts.append(f"[{i}] Title: {title}\n    Summary: {summary}")

    prompt = MINOR_EVENTS_BATCH_PROMPT.format(
        ticker=position.get("ticker", ""),
        labels=labels,
        purchase_price=purchase_price,
        news_items="\n\n".join(news_texts),
    )

    result = chatcompletion_text(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=4000,
    )

    from .analysis_utils import extract_json_value

    parsed = extract_json_list(result, None)

    results = []
    if isinstance(parsed, list) and len(parsed) == len(news_items):
        for i, p in enumerate(parsed):
            fallback = _fallback_minor_event_analysis(news_items[i], position)
            results.append(
                {
                    "analysis_text": p.get("analysis_text")
                    or fallback["analysis_text"],
                    "impact_horizon": p.get("impact_horizon")
                    or fallback["impact_horizon"],
                    "risk_direction": p.get("risk_direction")
                    or fallback["risk_direction"],
                    "confidence": float(p.get("confidence") or fallback["confidence"]),
                    "scenario_summary": p.get("scenario_summary")
                    or fallback["scenario_summary"],
                    "key_implications": p.get("key_implications")
                    or fallback["key_implications"],
                    "recommended_followups": p.get("recommended_followups")
                    or fallback["recommended_followups"],
                }
            )
    else:
        for item in news_items:
            fallback = _fallback_minor_event_analysis(item, position)
            results.append(fallback)

    return results
