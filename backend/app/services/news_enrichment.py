from __future__ import annotations

import hashlib
import re
import logging
from datetime import datetime, timezone
from typing import Any

from .article_scraper import (
    _extract_with_trafilatura,
    _extract_with_newspaper4k,
    _strip_article_boilerplate,
    _normalize_host,
    _article_source_host,
)
from .minimax import chatcompletion_text
from ..pipeline.analysis_utils import extract_json_object, sanitize_text_field

logger = logging.getLogger(__name__)

SOURCE_TIER_MAP: dict[str, int] = {
    "reuters": 1, "reuters.com": 1,
    "wsj": 1, "wsj.com": 1, "wall street journal": 1,
    "bloomberg": 1, "bloomberg.com": 1,
    "ft": 1, "ft.com": 1, "financial times": 1,
    "ap": 1, "apnews.com": 1, "associated press": 1,

    "marketwatch": 2, "marketwatch.com": 2,
    "yahoo finance": 2, "finance.yahoo.com": 2,
    "investing.com": 2,
    "seeking alpha": 2, "seekingalpha.com": 2,
    "cnbc": 2, "cnbc.com": 2,
    "business insider": 2, "businessinsider.com": 2,
    "barrons": 2, "barrons.com": 2,
    "morningstar": 2, "morningstar.com": 2,
    "fool.com": 2, "motley fool": 2,
    "zacks": 2, "zacks.com": 2,
    "investors.com": 2,
    "benzinga": 2, "benzinga.com": 2,
}

_PAYWALL_DOMAINS: set[str] = {
    "wsj.com", "bloomberg.com", "ft.com",
    "barrons.com", "marketwatch.com",
}

SENTIMENT_PROMPT = """Analyze the following news article about {ticker} and return a JSON object.

Article headline: {headline}
Article body excerpt: {body_excerpt}

Return ONLY this JSON (no markdown, no explanation):
{{"sentiment_score": <0-100>, "sentiment_reason": "<one sentence>", "impact_tag": "<category>"}}

- sentiment_score: 0 = extremely negative for the company/stock, 100 = extremely positive. 50 = neutral/balanced.
- sentiment_reason: One sentence explaining WHY this score was assigned. No hedging. Be specific.
- impact_tag: Choose ONE from: financial-impact, regulatory, leadership, product, macro, sector, other

Use the article evidence. Do not guess. If the article is purely descriptive with no clear implication, score 50."""

TLDR_PROMPT = """Summarize the following news article about {ticker} and return a JSON object.

Article headline: {headline}
Article body: {body}

Return ONLY this JSON (no markdown, no explanation):
{{"tldr": "<1-2 sentence summary>", "what_it_means": "<1-2 sentence implication for the stock>", "key_implications": ["<bullet 1>", "<bullet 2>", "<bullet 3>", "<bullet 4>"]}}

- tldr: Pure factual summary. No opinion. What happened.
- what_it_means: Implication for the company/stock. Specific, not generic.
- key_implications: 2-4 concrete, specific bullet points. Financial, operational, regulatory, competitive implications.

If the body text is very short or insufficient to derive implications, set key_implications to an empty array and note that in tldr."""


def classify_source_tier(source: str) -> int:
    if not source:
        return 3
    normalized = source.strip().lower()
    for key, tier in SOURCE_TIER_MAP.items():
        if key in normalized:
            return tier
    return 3


def classify_recency_weight(published_at: str | None) -> tuple[float, str]:
    if not published_at:
        return 1.0, "72h_7d"
    try:
        dt = _parse_iso(published_at)
        if dt is None:
            return 1.0, "72h_7d"
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if age_hours <= 24:
            return 3.0, "last_24h"
        if age_hours <= 72:
            return 2.0, "24_72h"
        return 1.0, "72h_7d"
    except Exception:
        return 1.0, "72h_7d"


def source_weight_for_tier(tier: int) -> float:
    return {1: 1.5, 2: 1.0, 3: 0.5}.get(tier, 1.0)


def is_paywalled_domain(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        for pd in _PAYWALL_DOMAINS:
            if pd in host:
                return True
    except Exception:
        pass
    return False


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _compute_event_hash(ticker: str, url: str, headline: str) -> str:
    raw = f"{ticker.strip().upper()}|{url.strip()}|{headline.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _truncate_text(text: str, limit: int = 1500) -> str:
    if not text:
        return ""
    return text[:limit]


async def _score_article_llm(
    ticker: str, headline: str, body: str
) -> dict[str, Any]:
    prompt = SENTIMENT_PROMPT.format(
        ticker=ticker,
        headline=headline[:300],
        body_excerpt=_truncate_text(body or "", 1200),
    )
    result_text, parsed = _request_llm_json(prompt, max_tokens=400)
    return parsed if isinstance(parsed, dict) else {}


async def _generate_tldr_llm(
    ticker: str, headline: str, body: str
) -> dict[str, Any]:
    prompt = TLDR_PROMPT.format(
        ticker=ticker,
        headline=headline[:300],
        body=_truncate_text(body or "", 2000),
    )
    result_text, parsed = _request_llm_json(prompt, max_tokens=600)
    return parsed if isinstance(parsed, dict) else {}


def _request_llm_json(prompt: str, max_tokens: int = 600) -> tuple[str, dict]:
    try:
        result_text = chatcompletion_text(
            messages=[
                {
                    "role": "system",
                    "content": "You MUST respond with valid JSON only. No markdown. No explanation. Start with { and end with }.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            max_tokens=max_tokens,
        )
        return result_text, extract_json_object(result_text, {})
    except Exception as exc:
        logger.warning("LLM request failed: %s", exc)
        return "", {}


async def enrich_and_store_article(
    supabase,
    article: dict[str, Any],
    *,
    analysis_run_id: str | None = None,
    skip_existing: bool = True,
) -> dict[str, Any] | None:
    ticker = str(article.get("ticker") or "").strip().upper()
    headline = str(article.get("title") or article.get("headline") or "").strip()
    url = str(article.get("url") or article.get("source_url") or "").strip()
    source = str(article.get("source") or "").strip()
    published_at = str(article.get("published_at") or "")
    resolved_url = str(article.get("resolved_url") or url or "").strip()
    body = str(article.get("body") or "").strip()

    if not ticker or not headline:
        logger.debug("Skipping article — missing ticker or headline")
        return None

    event_hash = _compute_event_hash(ticker, resolved_url or url, headline)
    canonical_url = resolved_url or url

    if skip_existing:
        try:
            existing = (
                supabase.table("shared_ticker_events")
                .select("id")
                .eq("ticker", ticker)
                .eq("event_hash", event_hash)
                .limit(1)
                .execute()
            )
            if existing.data:
                return existing.data[0]
        except Exception:
            pass

    is_paywalled = is_paywalled_domain(canonical_url)

    if is_paywalled or (body and body.startswith("[Paywalled]")):
        body = "[Paywalled] " + headline
        extraction_status = "paywalled"
        is_paywalled = True
    elif not body or len(body.split()) < 30:
        body = "[No body extracted] " + headline
        extraction_status = "failed"
    elif body:
        extraction_status = "success"
    else:
        body = headline
        extraction_status = "empty"

    source_tier = classify_source_tier(source)
    recency_w, article_window = classify_recency_weight(published_at)
    source_w = source_weight_for_tier(source_tier)

    sentiment_score = None
    sentiment_reason = None
    impact_tag = None
    tldr = None
    what_it_means = None
    key_implications = None

    if body and not is_paywalled and len(body.split()) >= 40:
        try:
            sent = await _score_article_llm(ticker, headline, body)
            sentiment_score = sent.get("sentiment_score")
            sentiment_reason = sanitize_text_field(sent.get("sentiment_reason"), fallback="")
            impact_tag_val = (sent.get("impact_tag") or "").strip().lower()
            valid_tags = {"financial-impact", "regulatory", "leadership", "product", "macro", "sector", "other"}
            impact_tag = impact_tag_val if impact_tag_val in valid_tags else None
        except Exception as exc:
            logger.warning("Sentiment scoring failed for %s: %s", ticker, exc)

        try:
            tldr_result = await _generate_tldr_llm(ticker, headline, body)
            tldr = sanitize_text_field(tldr_result.get("tldr"), fallback="")
            what_it_means = sanitize_text_field(tldr_result.get("what_it_means"), fallback="")
            raw_imp = tldr_result.get("key_implications")
            if isinstance(raw_imp, list):
                key_implications = [sanitize_text_field(item, fallback="") for item in raw_imp[:4]]
                key_implications = [imp for imp in key_implications if imp]
            else:
                key_implications = []
        except Exception as exc:
            logger.warning("TLDR generation failed for %s: %s", ticker, exc)

    payload = {
        "ticker": ticker,
        "event_hash": event_hash,
        "title": sanitize_text_field(headline, fallback=""),
        "summary": sanitize_text_field(article.get("summary") or "", fallback=""),
        "source": sanitize_text_field(source, fallback=""),
        "source_url": canonical_url,
        "canonical_url": canonical_url,
        "published_at": published_at or None,
        "event_type": str(article.get("event_type") or "").strip() or None,
        "significance": "minor",
        "body": body,
        "extraction_status": extraction_status,
        "paywalled": is_paywalled,
        "sentiment_score": sentiment_score,
        "sentiment_reason": sentiment_reason,
        "source_tier": source_tier,
        "recency_weight": recency_w,
        "source_weight": source_w,
        "impact_tag": impact_tag,
        "article_window": article_window,
        "tldr": tldr,
        "what_it_means": what_it_means,
        "key_implications": key_implications or [],
        "tags": article.get("tags") or [],
        "analysis_run_id": analysis_run_id,
        "factored_into_score": False,
        "provenance": "news_pipeline_v2",
        "methodology_version": "v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = (
            supabase.table("shared_ticker_events")
            .upsert(payload, on_conflict="ticker,event_hash")
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception as exc:
        logger.error("Failed to store article for %s: %s", ticker, exc)

    return None


async def enrich_and_store_articles_batch(
    supabase,
    articles: list[dict[str, Any]],
    *,
    analysis_run_id: str | None = None,
    max_concurrency: int = 5,
    skip_existing: bool = True,
) -> list[dict[str, Any]]:
    if not articles:
        return []

    import asyncio
    sem = asyncio.Semaphore(max_concurrency)

    async def _process(article):
        async with sem:
            return await enrich_and_store_article(
                supabase, article, analysis_run_id=analysis_run_id,
                skip_existing=skip_existing,
            )

    results = await asyncio.gather(*(_process(a) for a in articles))
    return [r for r in results if r is not None]
