import asyncio
import logging
import json
import urllib.request
import httpx
from ..config import get_settings
from ..services.minimax import chatcompletion_text
from .analysis_utils import safe_json_loads

logger = logging.getLogger(__name__)


FALLBACK_PROMPT = """You are a major-event investment risk analyst.

Return strict JSON:
{
  "analysis_text": "3-6 sentence analysis",
  "impact_horizon": "immediate|near_term|long_term",
  "risk_direction": "improving|neutral|worsening",
  "confidence": 0.0-1.0,
  "scenario_summary": "one sentence",
  "key_implications": ["...", "..."],
  "recommended_followups": ["...", "..."]
}
"""


def _normalize_mirofish_payload(payload: dict | None) -> dict | None:
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
        "scenario_summary": payload.get("scenario_summary")
        or "Major event analysis completed.",
        "key_implications": payload.get("key_implications") or [],
        "recommended_followups": payload.get("recommended_followups") or [],
        "provider": payload.get("provider") or "mirofish",
    }


def _urllib_mirofish_request(
    mirofish_url: str, news_item: dict, position_context: dict
) -> dict | None:
    request = urllib.request.Request(
        f"{mirofish_url}/analyze",
        data=json.dumps({"news": news_item, "position": position_context}).encode(
            "utf-8"
        ),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _normalize_mirofish_payload(payload)


async def mirofish_analyze(news_item: dict, position_context: dict) -> dict:
    settings = get_settings()
    mirofish_url = settings.mirofish_url

    if mirofish_url:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{mirofish_url}/analyze",
                    json={
                        "news": news_item,
                        "position": position_context,
                    },
                )
                if response.status_code == 200:
                    normalized = _normalize_mirofish_payload(response.json())
                    if normalized:
                        return normalized
                else:
                    logger.warning(f"MiroFish returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"MiroFish analysis failed via httpx: {e!r}")

        try:
            normalized = await asyncio.to_thread(
                _urllib_mirofish_request,
                mirofish_url,
                news_item,
                position_context,
            )
            if normalized:
                return normalized
        except Exception as e:
            logger.warning(f"MiroFish analysis failed via urllib: {e!r}")

    fallback_prompt = f"""Event:
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
    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": FALLBACK_PROMPT},
            {"role": "user", "content": fallback_prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    parsed = safe_json_loads(result, {})
    normalized = _normalize_mirofish_payload(parsed) or {
        "analysis_text": "Major event fallback analysis was unavailable.",
        "impact_horizon": "near_term",
        "risk_direction": "neutral",
        "confidence": 0.4,
        "scenario_summary": "Major event fallback analysis unavailable.",
        "key_implications": [],
        "recommended_followups": [],
        "provider": "minimax_fallback",
    }
    normalized["provider"] = "minimax_fallback"
    return normalized


MAJOR_EVENTS_BATCH_PROMPT = """You are a major-event investment risk analyst.

For each event below, analyze the potential impact on the position.

Position context:
- Ticker: {ticker}
- Shares: {shares}
- Purchase price: {purchase_price}
- Archetype: {archetype}
- Inferred labels: {labels}

Events:
{events}

Return a JSON array with one object per event in order.
Each object has:
- "analysis_text": "3-6 sentence analysis"
- "impact_horizon": "immediate|near_term|long_term"
- "risk_direction": "improving|neutral|worsening"
- "confidence": 0.0-1.0
- "scenario_summary": "one sentence"
- "key_implications": ["...", "..."]
- "recommended_followups": ["...", "..."]"""


async def mirofish_analyze_batch(
    news_items: list[dict],
    position_context: dict,
) -> list[dict]:
    if not news_items:
        return []

    events_text = []
    for i, item in enumerate(news_items):
        title = item.get("title", "")[:300]
        summary = item.get("summary", "")[:500]
        body = item.get("body", "")[:800]
        events_text.append(
            f"[{i}] Title: {title}\n    Summary: {summary}\n    Body: {body}"
        )

    ticker = position_context.get("ticker", "")
    shares = position_context.get("shares", 0)
    purchase_price = position_context.get("purchase_price", 0)
    archetype = position_context.get("archetype", "unknown")
    labels = ", ".join(position_context.get("inferred_labels", []))

    prompt = MAJOR_EVENTS_BATCH_PROMPT.format(
        ticker=ticker,
        shares=shares,
        purchase_price=purchase_price,
        archetype=archetype,
        labels=labels,
        events="\n\n".join(events_text),
    )

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": FALLBACK_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    from .analysis_utils import extract_json_list

    parsed = extract_json_list(result, None)

    results = []
    if isinstance(parsed, list) and len(parsed) == len(news_items):
        for p in parsed:
            normalized = _normalize_mirofish_payload(p)
            if normalized:
                normalized["provider"] = "minimax_fallback"
                results.append(normalized)
            else:
                results.append(
                    {
                        "analysis_text": "Major event batch analysis unavailable.",
                        "impact_horizon": "near_term",
                        "risk_direction": "neutral",
                        "confidence": 0.4,
                        "scenario_summary": "Batch analysis fallback.",
                        "key_implications": [],
                        "recommended_followups": [],
                        "provider": "minimax_fallback",
                    }
                )
    else:
        for _ in news_items:
            results.append(
                {
                    "analysis_text": "Major event batch analysis unavailable.",
                    "impact_horizon": "near_term",
                    "risk_direction": "neutral",
                    "confidence": 0.4,
                    "scenario_summary": "Batch analysis fallback.",
                    "key_implications": [],
                    "recommended_followups": [],
                    "provider": "minimax_fallback",
                }
            )

    return results
