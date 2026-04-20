from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_list, extract_json_object

SYSTEM_PROMPT = """You are a portfolio risk analysis AI. Given a news item and a stock position, describe the potential impact on the position.

Position context:
- Ticker: {ticker}
- Inferred labels: {labels}
- Purchase price: ${purchase_price}
- Evidence quality: {evidence_quality}
- News title: {title}
- News summary: {summary}
- News body: {body}

Analysis should consider:
1. How does this news affect the company's fundamentals?
2. How does it interact with the holding's style/theme exposure?
3. What is the likely short-term and long-term impact?

If evidence_quality is title_only or headline_summary, do not pretend you read a full article. Lower confidence and state that the read is provisional.

Return strict JSON:
{{
  "analysis_text": "2-4 sentence analysis",
  "impact_horizon": "immediate|near_term|long_term",
  "risk_direction": "improving|neutral|worsening",
  "confidence": 0.0-1.0,
  "scenario_summary": "one sentence",
  "key_implications": ["...", "..."],
  "followup_notes": ["...", "..."]
}}"""


def _fallback_minor_event_analysis(news_item: dict, position: dict) -> dict:
    title = news_item.get("title", "Recent news")
    summary = news_item.get("summary", "")
    body = news_item.get("body", "")
    evidence_quality = news_item.get("evidence_quality", "title_only")
    ticker = position.get("ticker", "this holding")
    combined = " ".join(part for part in [title, summary, body[:220]] if part).strip()
    trimmed = (
        combined[:280]
        if combined
        else "Recent coverage did not include enough detail for a richer AI summary."
    )
    evidence_note = (
        "This read is provisional because it is based on limited headline-level evidence."
        if evidence_quality in {"title_only", "headline_summary"}
        else "This read uses the extracted article body and should still be validated against follow-on reporting."
    )
    return {
        "analysis_text": f"{trimmed} {evidence_note} For {ticker}, this appears to be a monitorable development rather than a clear risk break absent stronger confirming evidence.",
        "impact_horizon": "near_term",
        "risk_direction": "neutral",
        "confidence": 0.3
        if evidence_quality in {"title_only", "headline_summary"}
        else 0.45,
        "scenario_summary": f"{ticker} faces a moderate change in context rather than a confirmed major catalyst from this {evidence_quality} event.",
        "key_implications": [
            f"Track whether follow-on reporting changes the significance of '{title}'."
        ],
        "followup_notes": [
            "Track whether earnings, guidance, regulatory, or management updates materially change the risk profile."
        ],
    }


def _fallback_shared_minor_event_analysis(news_item: dict) -> dict:
    title = news_item.get("title", "Recent news")
    summary = news_item.get("summary", "")
    body = news_item.get("body", "")
    evidence_quality = news_item.get("evidence_quality", "title_only")
    combined = " ".join(part for part in [title, summary, body[:220]] if part).strip()
    trimmed = (
        combined[:280]
        if combined
        else "Recent coverage did not include enough detail for a richer AI summary."
    )
    evidence_note = (
        "This is a low-confidence title-led inference because the underlying article evidence is thin."
        if evidence_quality in {"title_only", "headline_summary"}
        else "This read uses the extracted article body and remains subject to follow-on confirmation."
    )
    return {
        "analysis_text": f"{trimmed} {evidence_note} This looks like a monitorable development rather than a confirmed risk-changing catalyst without stronger follow-through.",
        "impact_horizon": "near_term",
        "risk_direction": "neutral",
        "confidence": 0.3
        if evidence_quality in {"title_only", "headline_summary"}
        else 0.45,
        "scenario_summary": f"The event changes context more than it changes fundamentals at this {evidence_quality} stage.",
        "key_implications": [
            f"Track whether follow-on reporting changes the significance of '{title}'."
        ],
        "recommended_followups": [
            "Watch for management commentary, earnings, regulatory filings, or additional reporting that changes the fundamental read-through."
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
        body=news_item.get("body", "")[:900],
        evidence_quality=news_item.get("evidence_quality", "title_only"),
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
        "recommended_followups": parsed.get("followup_notes")
        or parsed.get("recommended_followups")
        or fallback["recommended_followups"],
    }


MINOR_EVENTS_BATCH_PROMPT = """You are a portfolio risk analysis AI. Given multiple news items and a stock position, describe the potential impact of each news item on the position.

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
- "followup_notes": ["...", "..."]

Return a JSON array with one object per news item in order."""


GENERIC_MINOR_EVENTS_BATCH_PROMPT = """You are a portfolio risk analyst.

Given multiple news items, produce a reusable base analysis for each event without assuming a specific holder.

News items to analyze:
{news_items}

For each news item above, return a JSON object with:
- "analysis_text": "2-4 sentence analysis"
- "impact_horizon": "immediate|near_term|long_term"
- "risk_direction": "improving|neutral|worsening"
- "confidence": 0.0-1.0
- "scenario_summary": "one sentence"
- "key_implications": ["...", "..."]
- "followup_notes": ["...", "..."]

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
        body = item.get("body", "")[:700]
        evidence_quality = item.get("evidence_quality", "title_only")
        news_texts.append(
            f"[{i}] Evidence quality: {evidence_quality}\n    Title: {title}\n    Summary: {summary}\n    Body: {body}"
        )

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


async def analyze_minor_events_shared_batch(news_items: list[dict]) -> list[dict]:
    if not news_items:
        return []

    news_texts = []
    for i, item in enumerate(news_items):
        title = item.get("title", "")[:220]
        summary = item.get("summary", "")[:320]
        body = item.get("body", "")[:700]
        evidence_quality = item.get("evidence_quality", "title_only")
        news_texts.append(
            f"[{i}] Evidence quality: {evidence_quality}\n    Title: {title}\n    Summary: {summary}\n    Body: {body}"
        )

    prompt = GENERIC_MINOR_EVENTS_BATCH_PROMPT.format(
        news_items="\n\n".join(news_texts),
    )

    result = chatcompletion_text(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2400,
    )

    parsed = extract_json_list(result, None)
    results = []
    if isinstance(parsed, list) and len(parsed) == len(news_items):
        for i, payload in enumerate(parsed):
            fallback = _fallback_shared_minor_event_analysis(news_items[i])
            results.append(
                {
                    "analysis_text": payload.get("analysis_text")
                    or fallback["analysis_text"],
                    "impact_horizon": payload.get("impact_horizon")
                    or fallback["impact_horizon"],
                    "risk_direction": payload.get("risk_direction")
                    or fallback["risk_direction"],
                    "confidence": float(
                        payload.get("confidence") or fallback["confidence"]
                    ),
                    "scenario_summary": payload.get("scenario_summary")
                    or fallback["scenario_summary"],
                    "key_implications": payload.get("key_implications")
                    or fallback["key_implications"],
                    "recommended_followups": payload.get("followup_notes")
                    or payload.get("recommended_followups")
                    or fallback["recommended_followups"],
                }
            )
        return results

    return [_fallback_shared_minor_event_analysis(item) for item in news_items]
