from __future__ import annotations

import asyncio
import hashlib
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

# Finnhub-first pipeline settings
NEWS_PRIMARY_PROVIDER: str = "finnhub"
GOOGLE_NEWS_FALLBACK_ENABLED: bool = os.getenv("GOOGLE_NEWS_FALLBACK_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
GOOGLE_FALLBACK_MIN_USABLE_ARTICLES: int = int(os.getenv("GOOGLE_FALLBACK_MIN_USABLE_ARTICLES", "3"))

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
    "nytimes.com", "morningstar.com", "global.morningstar.com",
    "thetimes.com", "news.microsoft.com",
}

# Domains that are technically not paywalled but are blocked / anti-bot / 0% extraction
# These will be stored but marked extraction_status="blocked" rather than "failed"
_BLOCKED_DOMAINS: set[str] = {
    "reuters.com", "msn.com", "news.bloomberglaw.com",
    "thestreet.com", "britannica.com",
}

# Low-value domains (chart sites, analytics, not real news) — deprioritized upstream
# but if they do arrive, extract minimally
_LOW_VALUE_DOMAINS: set[str] = {
    "marketbeat.com", "chartmill.com", "stocktitan.net",
    "macroaxis.com", "tipranks.com", "barchart.com",
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


def _normalize_url_host(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def is_paywalled_domain(url: str) -> bool:
    host = _normalize_url_host(url)
    return any(pd in host for pd in _PAYWALL_DOMAINS) if host else False


def is_blocked_domain(url: str) -> bool:
    """Anti-bot/blocked domains: 0% extraction success, not paywalled."""
    host = _normalize_url_host(url)
    return any(bd in host for bd in _BLOCKED_DOMAINS) if host else False


def validate_enrichment_completeness(article: dict) -> tuple[bool, list[str]]:
    """Check whether an article has all required enrichment fields.

    Returns (is_complete, missing_fields).
    An article is complete when it has:
    - sentiment_score (numeric 0-100)
    - sentiment_reason (non-empty string)
    - tldr (non-empty, only required if body_has_content)

    key_implications are required only for body-extracted articles.
    """
    missing: list[str] = []
    if article.get("sentiment_score") is None:
        missing.append("missing_sentiment_score")
    if not str(article.get("sentiment_reason") or "").strip():
        missing.append("missing_sentiment_reason")
    body = str(article.get("body") or "")
    body_has_content = (
        body
        and not body.startswith("[No body extracted]")
        and not body.startswith("[Paywalled]")
        and len(body.split()) >= 40
    )
    if body_has_content:
        if not str(article.get("tldr") or "").strip():
            missing.append("missing_tldr")
        if not str(article.get("what_it_means") or "").strip():
            missing.append("missing_what_it_means")
    return len(missing) == 0, missing


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

    # When skip_existing=True: skip the whole row if it exists.
    # When skip_existing=False: fetch existing row to seed LLM fields so we never
    # overwrite non-null sentiment_score / tldr / what_it_means with a weaker pass.
    existing_llm: dict[str, Any] = {}
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
    else:
        try:
            existing_row = (
                supabase.table("shared_ticker_events")
                .select("sentiment_score,sentiment_reason,impact_tag,tldr,what_it_means,key_implications")
                .eq("ticker", ticker)
                .eq("event_hash", event_hash)
                .limit(1)
                .execute()
            )
            if existing_row.data:
                existing_llm = existing_row.data[0]
        except Exception:
            pass

    is_paywalled = is_paywalled_domain(canonical_url)
    is_blocked = is_blocked_domain(canonical_url)

    if is_paywalled or (body and body.startswith("[Paywalled]")):
        body = "[Paywalled] " + headline
        extraction_status = "paywalled"
        is_paywalled = True
    elif is_blocked and (not body or len(body.split()) < 30):
        body = "[Blocked] " + headline
        extraction_status = "blocked"
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

    # Seed LLM fields from existing row. A non-null DB value is preserved;
    # a null DB value (or no existing row) triggers a fresh LLM call below.
    sentiment_score: Any = existing_llm.get("sentiment_score")
    sentiment_reason: str | None = existing_llm.get("sentiment_reason")
    impact_tag: str | None = existing_llm.get("impact_tag")
    tldr: str | None = existing_llm.get("tldr")
    what_it_means: str | None = existing_llm.get("what_it_means")
    key_implications: list | None = existing_llm.get("key_implications")

    need_sentiment = sentiment_score is None
    # BUG FIX: key_implications was not included in the need_tldr check.
    # Articles enriched before key_implications was added to TLDR_PROMPT had
    # tldr + what_it_means set (so need_tldr was False) but key_implications=null,
    # meaning they were permanently skipped by the enrichment loop.
    # Fix: also trigger a TLDR_PROMPT call when key_implications is null or empty.
    _ki = key_implications
    _ki_missing = _ki is None or (isinstance(_ki, list) and len(_ki) == 0)
    need_tldr = (tldr is None or not str(tldr or "").strip()
                 or what_it_means is None or not str(what_it_means or "").strip()
                 or _ki_missing)

    # Score from full body when available; fall back to headline-only scoring per §10.
    # Headline-only path: score sentiment from headline alone when body extraction failed.
    body_has_content = (
        body
        and not is_paywalled
        and not body.startswith("[No body extracted]")
        and len(body.split()) >= 40
    )
    headline_only = not body_has_content and bool(headline)
    scoring_text = body if body_has_content else headline

    if scoring_text and not is_paywalled and (body_has_content or headline_only):
        if need_sentiment:
            try:
                sent = await _score_article_llm(ticker, headline, scoring_text)
                sentiment_score = sent.get("sentiment_score")
                sentiment_reason = sanitize_text_field(sent.get("sentiment_reason"), fallback="")
                impact_tag_val = (sent.get("impact_tag") or "").strip().lower()
                valid_tags = {"financial-impact", "regulatory", "leadership", "product", "macro", "sector", "other"}
                impact_tag = impact_tag_val if impact_tag_val in valid_tags else None
            except Exception as exc:
                logger.warning("Sentiment scoring failed for %s: %s", ticker, exc)

        if body_has_content and need_tldr:
            try:
                tldr_result = await _generate_tldr_llm(ticker, headline, scoring_text)
                new_tldr = sanitize_text_field(tldr_result.get("tldr"), fallback="")
                new_what = sanitize_text_field(tldr_result.get("what_it_means"), fallback="")
                # Only overwrite a field when the new value is non-empty — preserves
                # any partially-enriched data if the LLM returns empty for that field.
                tldr = new_tldr if new_tldr else tldr
                what_it_means = new_what if new_what else what_it_means
                raw_imp = tldr_result.get("key_implications")
                if isinstance(raw_imp, list):
                    new_imp = [sanitize_text_field(item, fallback="") for item in raw_imp[:4]]
                    new_imp = [imp for imp in new_imp if imp]
                    key_implications = new_imp if new_imp else key_implications
                elif key_implications is None:
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

    sem = asyncio.Semaphore(max_concurrency)

    async def _process(article):
        async with sem:
            return await enrich_and_store_article(
                supabase, article, analysis_run_id=analysis_run_id,
                skip_existing=skip_existing,
            )

    results = await asyncio.gather(*(_process(a) for a in articles))
    return [r for r in results if r is not None]


async def ingest_and_enrich_ticker_news(
    supabase,
    tickers: list[str],
    *,
    limit_per_ticker: int = 10,
    max_concurrency: int = 3,
) -> dict[str, int]:
    """Finnhub-first news ingestion: fetch → filter → extract → score → store.

    Primary: Finnhub company-news (7-day window) with inline body extraction.
    Fallback: Google News RSS, only for tickers with < GOOGLE_FALLBACK_MIN_USABLE_ARTICLES
    usable 7-day articles after Finnhub enrichment.

    Returns: dict of {ticker: articles_stored}.
    """
    from ..pipeline.finnhub_news import fetch_finnhub_ticker_news
    from ..pipeline.news_normalizer import normalize_news_batch
    from .article_scraper import enrich_articles_content
    from .candidate_ranker import rank_and_filter_candidates
    from .ticker_cache_service import get_metadata_map

    if not tickers:
        return {}

    results: dict[str, int] = {}

    # ── 1. Finnhub primary ────────────────────────────────────────────────────
    per_ticker_raw, _ = await fetch_finnhub_ticker_news(
        tickers, days=7, limit_per_ticker=limit_per_ticker
    )
    all_finnhub = [a for arts in per_ticker_raw.values() for a in arts]

    # Filter by domain policy before spending extraction budget
    filtered_finnhub = rank_and_filter_candidates(all_finnhub, skip_score_below=15.0)

    # Extract article bodies from Finnhub URLs
    if filtered_finnhub:
        extracted_finnhub = await enrich_articles_content(
            filtered_finnhub, max_concurrency=max_concurrency
        )
    else:
        extracted_finnhub = []

    # Store + LLM score
    finnhub_stored = await enrich_and_store_articles_batch(
        supabase, extracted_finnhub, max_concurrency=max_concurrency, skip_existing=True
    )
    for article in finnhub_stored:
        t = str(article.get("ticker") or "").strip().upper()
        if t in tickers:
            results[t] = results.get(t, 0) + 1

    # ── 2. Google fallback ────────────────────────────────────────────────────
    if not GOOGLE_NEWS_FALLBACK_ENABLED:
        return results

    # Query DB for usable 7-day counts per ticker
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        rows = (
            supabase.table("shared_ticker_events")
            .select("ticker,extraction_status,paywalled,sentiment_score")
            .in_("ticker", list(tickers))
            .gte("published_at", cutoff)
            .execute()
            .data or []
        )
    except Exception:
        rows = []

    usable_by_ticker: dict[str, int] = {}
    for row in rows:
        t = str(row.get("ticker") or "").upper()
        if (
            row.get("extraction_status") == "success"
            and not row.get("paywalled", False)
            and row.get("sentiment_score") is not None
        ):
            usable_by_ticker[t] = usable_by_ticker.get(t, 0) + 1

    fallback_tickers = [
        t for t in tickers
        if usable_by_ticker.get(t, 0) < GOOGLE_FALLBACK_MIN_USABLE_ARTICLES
    ]

    if not fallback_tickers:
        return results

    logger.info(
        "[NEWS] Google fallback for %d tickers (need more usable): %s",
        len(fallback_tickers), fallback_tickers,
    )

    from ..pipeline.rss_ingest import fetch_google_company_rss

    metadata_map = get_metadata_map(supabase, fallback_tickers)
    google_raw = await fetch_google_company_rss(
        fallback_tickers,
        ticker_metadata=metadata_map,
        limit_per_ticker=limit_per_ticker,
    )
    google_normalized = normalize_news_batch(google_raw, "company_news") if google_raw else []
    google_stored = await enrich_and_store_articles_batch(
        supabase, google_normalized, max_concurrency=max_concurrency, skip_existing=True
    )
    for article in google_stored:
        t = str(article.get("ticker") or "").strip().upper()
        if t in tickers:
            results[t] = results.get(t, 0) + 1

    return results
