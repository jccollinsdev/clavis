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

# MVP threshold: Google used if usable < this (previously GOOGLE_FALLBACK_MIN_USABLE_ARTICLES)
GOOGLE_FALLBACK_MVP_THRESHOLD: int = int(os.getenv("GOOGLE_FALLBACK_MVP_THRESHOLD", "3"))
# Production ideal: Google used to boost if usable < this (when mode allows)
GOOGLE_FALLBACK_PRODUCTION_TARGET: int = int(os.getenv("GOOGLE_FALLBACK_PRODUCTION_TARGET", "10"))
# mvp_only: Google only for usable < MVP_THRESHOLD
# below_10: Google for usable < PRODUCTION_TARGET (mvp_recovery + production_boost)
# disabled: no Google at all
GOOGLE_FALLBACK_MODE: str = os.getenv("GOOGLE_FALLBACK_MODE", "below_10")
# Per-ticker Google fetch limits
GOOGLE_FALLBACK_MAX_CANDIDATES_PER_TICKER: int = int(os.getenv("GOOGLE_FALLBACK_MAX_CANDIDATES_PER_TICKER", "15"))
GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER: int = int(os.getenv("GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER", "10"))

# Backward-compat alias
GOOGLE_FALLBACK_MIN_USABLE_ARTICLES: int = GOOGLE_FALLBACK_MVP_THRESHOLD

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

_LOGIN_WALL_MARKERS: tuple[str, ...] = (
    "sign in",
    "log in",
    "login",
    "subscribe",
    "create free account",
    "join pro",
    "join ic",
    "watchlist",
)

_NAVIGATION_MARKERS: tuple[str, ...] = (
    "search quotes, news & videos",
    "livestream menu",
    "markets markets",
    "stock screener",
    "data & apis",
    "financial news financial news",
    "options etfs commodities",
    "premarket advertise contribute",
    "privacy policy",
    "terms of service",
)

_COOKIE_MARKERS: tuple[str, ...] = (
    "accept all",
    "deny optional",
    "cookie policy",
    "consent preferences",
)

_BLOCKED_PAGE_MARKERS: tuple[str, ...] = (
    "access denied",
    "verify you are human",
    "captcha",
    "unusual traffic",
    "checking if the site connection is secure",
    "press and hold",
)

_TITLE_STOPWORDS: set[str] = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
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


def _sentence_like_paragraphs(text: str) -> int:
    count = 0
    for raw in re.split(r"\n{2,}", text or ""):
        paragraph = raw.strip()
        if len(paragraph.split()) < 12:
            continue
        if re.search(r"[.!?]", paragraph):
            count += 1
    return count


def _title_signal_tokens(title: str) -> list[str]:
    tokens: list[str] = []
    for token in re.split(r"[^A-Za-z0-9]+", title or ""):
        normalized = token.strip().lower()
        if len(normalized) < 4 or normalized in _TITLE_STOPWORDS:
            continue
        tokens.append(normalized)
    return tokens[:6]


def assess_article_body_quality(article: dict[str, Any]) -> tuple[bool, str | None, str]:
    """Decide whether an extracted body is usable for LLM enrichment."""
    body = str(article.get("body") or "").strip()
    if not body:
        return False, "no_body", ""

    if body.startswith("[Paywalled]"):
        return False, "paywall_content", body
    if body.startswith("[Blocked]"):
        return False, "blocked_content", body
    if body.startswith("[No body extracted]"):
        return False, "no_body", body

    source_host = _article_source_host(article)
    if not source_host:
        source_host = _normalize_host(
            str(
                article.get("resolved_url")
                or article.get("canonical_url")
                or article.get("source_url")
                or article.get("url")
                or ""
            )
        )

    cleaned_body = _strip_article_boilerplate(body, source_host) or body
    lowered = cleaned_body.lower()
    raw_lowered = body.lower()

    if any(marker in raw_lowered for marker in _BLOCKED_PAGE_MARKERS):
        return False, "blocked_content", cleaned_body

    login_hits = sum(marker in raw_lowered for marker in _LOGIN_WALL_MARKERS)
    nav_hits = sum(marker in raw_lowered for marker in _NAVIGATION_MARKERS)
    cookie_hits = sum(marker in raw_lowered for marker in _COOKIE_MARKERS)
    sentence_paragraphs = _sentence_like_paragraphs(cleaned_body)
    cleaned_words = len(cleaned_body.split())
    original_words = max(1, len(body.split()))
    retained_ratio = cleaned_words / original_words

    if "benzinga" in source_host and (
        "get benzinga pro" in raw_lowered
        or "benzinga edge" in raw_lowered
        or "benzinga premium services" in raw_lowered
    ):
        return False, "no_usable_content", cleaned_body

    if login_hits >= 2 and sentence_paragraphs < 3:
        return False, "login_wall", cleaned_body

    if cookie_hits >= 2 and sentence_paragraphs < 2:
        return False, "cookie_wall", cleaned_body

    if nav_hits >= 4 and (sentence_paragraphs < 3 or retained_ratio < 0.45):
        return False, "no_usable_content", cleaned_body

    if cleaned_words < 40:
        return False, "no_usable_content", cleaned_body

    title_tokens = _title_signal_tokens(str(article.get("title") or article.get("headline") or ""))
    title_signal_hits = sum(token in lowered for token in title_tokens)
    if title_tokens and title_signal_hits == 0 and sentence_paragraphs < 3 and nav_hits >= 2:
        return False, "no_usable_content", cleaned_body

    return True, None, cleaned_body


async def _score_article_llm(
    ticker: str, headline: str, body: str
) -> dict[str, Any]:
    prompt = SENTIMENT_PROMPT.format(
        ticker=ticker,
        headline=headline[:300],
        body_excerpt=_truncate_text(body or "", 1200),
    )
    _, parsed = await asyncio.to_thread(_request_llm_json, prompt, 400)
    return parsed if isinstance(parsed, dict) else {}


async def _generate_tldr_llm(
    ticker: str, headline: str, body: str
) -> dict[str, Any]:
    prompt = TLDR_PROMPT.format(
        ticker=ticker,
        headline=headline[:300],
        body=_truncate_text(body or "", 2000),
    )
    _, parsed = await asyncio.to_thread(_request_llm_json, prompt, 600)
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

    # When skip_existing=True: skip the row only if it is FULLY ENRICHED
    # (sentiment_score IS NOT NULL). Rows that exist but have no sentiment are
    # extraction-complete but LLM-incomplete — they must be re-enriched, not skipped.
    # When skip_existing=False: fetch existing row to seed LLM fields so we never
    # overwrite non-null sentiment_score / tldr / what_it_means with a weaker pass.
    existing_llm: dict[str, Any] = {}
    if skip_existing:
        try:
            existing = (
                supabase.table("shared_ticker_events")
                .select("id,sentiment_score,sentiment_reason,impact_tag,tldr,what_it_means,key_implications")
                .eq("ticker", ticker)
                .eq("event_hash", event_hash)
                .limit(1)
                .execute()
            )
            if existing.data:
                row = existing.data[0]
                if row.get("sentiment_score") is not None:
                    # Fully enriched — skip
                    return row
                # Exists but unenriched — fall through to re-enrich, seeding existing LLM fields
                existing_llm = row
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

    rejection_reason: str | None = None
    if extraction_status == "success":
        body_is_usable, rejection_reason, cleaned_body = assess_article_body_quality(
            {
                **article,
                "title": headline,
                "headline": headline,
                "body": body,
                "resolved_url": resolved_url,
                "canonical_url": canonical_url,
                "source_url": canonical_url,
            }
        )
        body = cleaned_body
        if not body_is_usable:
            extraction_status = "failed"

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
    need_tldr = tldr is None or what_it_means is None

    body_has_content = (
        extraction_status == "success"
        and rejection_reason is None
        and bool(body)
        and not is_paywalled
        and len(body.split()) >= 40
    )
    scoring_text = body if body_has_content else ""

    if scoring_text and not is_paywalled and body_has_content:
        # Run sentiment + TLDR concurrently — each is now truly async via asyncio.to_thread
        _coro_keys: list[str] = []
        _coros = []
        if need_sentiment:
            _coro_keys.append("sentiment")
            _coros.append(_score_article_llm(ticker, headline, scoring_text))
        if body_has_content and need_tldr:
            _coro_keys.append("tldr")
            _coros.append(_generate_tldr_llm(ticker, headline, scoring_text))

        if _coros:
            _llm_results = await asyncio.gather(*_coros, return_exceptions=True)
            for _key, _result in zip(_coro_keys, _llm_results):
                if isinstance(_result, Exception):
                    logger.warning("LLM %s failed for %s: %s", _key, ticker, _result)
                    continue
                if _key == "sentiment":
                    sentiment_score = _result.get("sentiment_score")
                    sentiment_reason = sanitize_text_field(_result.get("sentiment_reason"), fallback="")
                    impact_tag_val = (_result.get("impact_tag") or "").strip().lower()
                    valid_tags = {"financial-impact", "regulatory", "leadership", "product", "macro", "sector", "other"}
                    impact_tag = impact_tag_val if impact_tag_val in valid_tags else None
                elif _key == "tldr":
                    new_tldr = sanitize_text_field(_result.get("tldr"), fallback="")
                    new_what = sanitize_text_field(_result.get("what_it_means"), fallback="")
                    # Only overwrite a field when the new value is non-empty — preserves
                    # any partially-enriched data if the LLM returns empty for that field.
                    tldr = new_tldr if new_tldr else tldr
                    what_it_means = new_what if new_what else what_it_means
                    raw_imp = _result.get("key_implications")
                    if isinstance(raw_imp, list):
                        new_imp = [sanitize_text_field(item, fallback="") for item in raw_imp[:4]]
                        new_imp = [imp for imp in new_imp if imp]
                        key_implications = new_imp if new_imp else key_implications
                    elif key_implications is None:
                        key_implications = []

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
        "body_length": len(body),
        "extraction_status": extraction_status,
        "paywalled": is_paywalled,
        "headline_only": False,
        "rejection_reason": rejection_reason,
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
        def _do_upsert():
            return (
                supabase.table("shared_ticker_events")
                .upsert(payload, on_conflict="ticker,event_hash")
                .execute()
            )
        result = await asyncio.to_thread(_do_upsert)
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

    articles_to_process = articles
    if skip_existing:
        # Batch pre-check: one query instead of N individual per-article SELECTs
        hash_map: dict[str, dict[str, Any]] = {}
        for a in articles:
            _ticker = str(a.get("ticker") or "").strip().upper()
            _url = str(a.get("url") or a.get("source_url") or "").strip()
            _resolved = str(a.get("resolved_url") or _url).strip()
            _headline = str(a.get("title") or a.get("headline") or "").strip()
            _h = _compute_event_hash(_ticker, _resolved or _url, _headline)
            hash_map[_h] = a

        def _batch_lookup():
            return (
                supabase.table("shared_ticker_events")
                .select("event_hash,sentiment_score")
                .in_("event_hash", list(hash_map.keys()))
                .execute()
                .data or []
            )
        try:
            existing_rows = await asyncio.to_thread(_batch_lookup)
            # Only skip rows that are FULLY enriched (sentiment_score is set).
            # Rows that exist but have sentiment_score=NULL were extracted without LLM
            # enrichment and must be re-processed — not skipped.
            existing_hashes = {
                r["event_hash"] for r in existing_rows
                if r.get("sentiment_score") is not None
            }
        except Exception:
            existing_hashes = set()

        articles_to_process = [a for h, a in hash_map.items() if h not in existing_hashes]

    if not articles_to_process:
        return []

    sem = asyncio.Semaphore(max_concurrency)

    async def _process(article):
        async with sem:
            return await enrich_and_store_article(
                supabase, article, analysis_run_id=analysis_run_id,
                skip_existing=False,  # already filtered by batch pre-check above
            )

    results = await asyncio.gather(*(_process(a) for a in articles_to_process))
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

    # ── 2. Google tiered fallback ─────────────────────────────────────────────
    if not GOOGLE_NEWS_FALLBACK_ENABLED or GOOGLE_FALLBACK_MODE == "disabled":
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

    # Tiered fallback: determine which tickers need Google and why
    need_mvp_recovery = [
        t for t in tickers if usable_by_ticker.get(t, 0) < GOOGLE_FALLBACK_MVP_THRESHOLD
    ]
    need_production_boost = (
        []
        if GOOGLE_FALLBACK_MODE == "mvp_only"
        else [
            t for t in tickers
            if GOOGLE_FALLBACK_MVP_THRESHOLD <= usable_by_ticker.get(t, 0) < GOOGLE_FALLBACK_PRODUCTION_TARGET
            and t not in need_mvp_recovery
        ]
    )
    fallback_tickers = need_mvp_recovery + need_production_boost
    google_mode_map: dict[str, str] = {
        **{t: "mvp_recovery" for t in need_mvp_recovery},
        **{t: "production_boost" for t in need_production_boost},
    }

    if not fallback_tickers:
        return results

    logger.info(
        "[NEWS] Google fallback — mvp_recovery: %d, production_boost: %d tickers",
        len(need_mvp_recovery), len(need_production_boost),
    )

    from ..pipeline.rss_ingest import fetch_google_company_rss

    metadata_map = get_metadata_map(supabase, fallback_tickers)
    google_limit = max(
        limit_per_ticker,
        GOOGLE_FALLBACK_MAX_CANDIDATES_PER_TICKER,
    )
    google_raw = await fetch_google_company_rss(
        fallback_tickers,
        ticker_metadata=metadata_map,
        limit_per_ticker=google_limit,
    )
    google_normalized = normalize_news_batch(google_raw, "company_news") if google_raw else []

    # Cap per-ticker extraction to avoid runaway cost on production_boost tickers
    if GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER > 0:
        per_t: dict[str, int] = {}
        capped: list[dict] = []
        for a in google_normalized:
            t = str(a.get("ticker") or "").strip().upper()
            if per_t.get(t, 0) < GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER:
                capped.append(a)
                per_t[t] = per_t.get(t, 0) + 1
        google_normalized = capped

    google_stored = await enrich_and_store_articles_batch(
        supabase, google_normalized, max_concurrency=max_concurrency, skip_existing=True
    )
    for article in google_stored:
        t = str(article.get("ticker") or "").strip().upper()
        if t in tickers:
            results[t] = results.get(t, 0) + 1

    return results
