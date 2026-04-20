import asyncio
import json
import os
import re
import weakref
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit
from datetime import datetime, timezone
from typing import Iterable

import feedparser
from gnews import GNews

from ..services.google_news_decoder import decode_google_news_urls


CNBC_MACRO_RSS_URL = "https://www.cnbc.com/id/100003114/device/rss/rss.html"

DEFAULT_CNBC_SECTOR_RSS_URLS: dict[str, list[str]] = {
    "technology": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"
    ],
    "financials": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"
    ],
    "energy": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19836768"
    ],
    "healthcare": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000108"
    ],
    "realestate": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000115"
    ],
    "consumerretail": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000116"
    ],
    "industrialsautos": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000101"
    ],
    "media": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000110"
    ],
}

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "technology": [
        "tech",
        "technology",
        "software",
        "semiconductor",
        "chip",
        "ai",
        "cloud",
    ],
    "financials": [
        "bank",
        "financial",
        "finance",
        "lender",
        "insurer",
        "broker",
        "credit",
    ],
    "energy": ["energy", "oil", "gas", "crude", "opec", "refiner", "lng"],
    "healthcare": ["health", "healthcare", "pharma", "biotech", "medical", "drug"],
    "realestate": [
        "real estate",
        "reit",
        "housing",
        "property",
        "mortgage",
        "homebuilder",
    ],
    "consumerretail": [
        "retail",
        "consumer",
        "store",
        "shopping",
        "e-commerce",
        "commerce",
    ],
    "industrialsautos": [
        "industrial",
        "aerospace",
        "auto",
        "automotive",
        "manufacturing",
        "trucking",
    ],
    "media": [
        "media",
        "streaming",
        "entertainment",
        "advertising",
        "broadcast",
        "content",
    ],
}


def _load_google_rss_delay_seconds() -> float:
    raw_value = str(os.getenv("GOOGLE_NEWS_RSS_DELAY_SECONDS", "0")).strip()
    if not raw_value:
        return 0.0
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        return 0.0


GOOGLE_RSS_DELAY_SECONDS = _load_google_rss_delay_seconds()
_google_rss_locks: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, asyncio.Lock
] = weakref.WeakKeyDictionary()
_google_rss_next_request_at = 0.0


def _get_google_rss_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _google_rss_locks.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _google_rss_locks[loop] = lock
    return lock


def _normalize_sector_name(sector: str | None) -> str:
    if not sector:
        return ""

    value = re.sub(r"[^a-z0-9]+", "", sector.lower())
    if "tech" in value:
        return "technology"
    if "financial" in value or "bank" in value:
        return "financials"
    if "energy" in value or "oil" in value or "gas" in value:
        return "energy"
    if "health" in value or "pharma" in value or "biotech" in value:
        return "healthcare"
    if "realestate" in value or "reit" in value or "housing" in value:
        return "realestate"
    if "consumer" in value or "retail" in value:
        return "consumerretail"
    if "industrial" in value or "auto" in value or "manufact" in value:
        return "industrialsautos"
    if "media" in value or "stream" in value or "entertain" in value:
        return "media"
    return value


def _load_sector_feed_urls() -> dict[str, list[str]]:
    result = {sector: urls[:] for sector, urls in DEFAULT_CNBC_SECTOR_RSS_URLS.items()}
    raw = os.getenv("CNBC_SECTOR_RSS_URLS", "").strip()
    if not raw:
        return result

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    result: dict[str, list[str]] = {}
    for key, value in parsed.items():
        sector = _normalize_sector_name(str(key))
        if not sector:
            continue
        if isinstance(value, str):
            urls = [value]
        elif isinstance(value, list):
            urls = [str(url) for url in value if str(url).strip()]
        else:
            urls = []
        if urls:
            result[sector] = urls
    return result


def _entry_timestamp(entry: dict) -> str:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                continue

    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            return str(value)

    return datetime.now(timezone.utc).isoformat()


def _entry_text(entry: dict) -> str:
    return f"{entry.get('title', '')} {entry.get('summary', '')}".lower()


def _should_include_sector_article(entry: dict, sector: str) -> bool:
    keywords = SECTOR_KEYWORDS.get(sector, [])
    if not keywords:
        return True
    text = _entry_text(entry)
    return any(keyword in text for keyword in keywords)


def _normalize_feed_entry(
    entry: dict, feed: dict, source_type: str, sector: str | None = None
) -> dict:
    raw_title = entry.get("title", "")
    title = raw_title
    raw_source = entry.get("source")
    source_url = ""
    if isinstance(raw_source, dict):
        source = raw_source.get("title", "") or feed.feed.get("title", "CNBC RSS")
        source_url = str(raw_source.get("href") or "").strip()
    elif isinstance(raw_source, str):
        source = raw_source or feed.feed.get("title", "CNBC RSS")
    else:
        source = feed.feed.get("title", "CNBC RSS")

    if (
        source_type == "company_news"
        and isinstance(raw_title, str)
        and " - " in raw_title
    ):
        headline, publisher = raw_title.rsplit(" - ", 1)
        if headline.strip() and publisher.strip():
            title = headline.strip()
            source = publisher.strip()

    return {
        "id": str(entry.get("id") or entry.get("guid") or entry.get("link") or ""),
        "title": title,
        "source": source,
        "source_url": source_url,
        "publisher_homepage_url": source_url,
        "url": entry.get("link", ""),
        "published_at": _entry_timestamp(entry),
        "summary": entry.get("summary", ""),
        "sector": sector,
        "source_type": source_type,
    }


def _canonical_url(url: str | None) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""

    try:
        parts = urlsplit(raw)
        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in {"ocid", "cmpid", "source", "guccounter"}
        ]
        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                urlencode(filtered_query),
                "",
            )
        )
    except Exception:
        return raw


def _normalize_title(title: str | None) -> str:
    return re.sub(r"\s+", " ", str(title or "").strip().lower())


def _article_dedupe_key(article: dict) -> str:
    canonical_url = _canonical_url(article.get("url"))
    if canonical_url:
        return canonical_url

    published = str(article.get("published_at") or "")[:10]
    title = _normalize_title(article.get("title"))
    source = str(article.get("source") or "").strip().lower()
    return "|".join(part for part in (title, source, published) if part)


def _dedupe_articles(articles: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for article in articles:
        key = _article_dedupe_key(article)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(article)
    return deduped


async def _attach_decoded_google_news_urls(articles: list[dict]) -> list[dict]:
    if not articles:
        return articles

    decoded_urls = await decode_google_news_urls(
        [str(article.get("url") or "") for article in articles]
    )
    if not decoded_urls:
        return articles

    enriched: list[dict] = []
    for article in articles:
        google_url = str(article.get("url") or "")
        decoded_url = decoded_urls.get(google_url)
        if decoded_url:
            enriched.append(
                {
                    **article,
                    "url": decoded_url,
                    "source_url": decoded_url,
                    "decoded_google_url": decoded_url,
                }
            )
        else:
            enriched.append(article)
    return enriched


def _build_gnews_client(max_results: int) -> GNews:
    return GNews(language="en", country="US", period="7d", max_results=max_results)


async def _fetch_gnews_articles(query: str, max_results: int) -> list[dict]:
    if not query.strip():
        return []

    def _run() -> list[dict]:
        try:
            return _build_gnews_client(max_results).get_news(query)
        except Exception:
            return []

    return await asyncio.to_thread(_run)


def _normalize_gnews_entry(
    entry: dict,
    query: str,
    ticker: str,
    company_name: str,
) -> dict:
    publisher = entry.get("publisher")
    if not isinstance(publisher, dict):
        publisher = {}

    source = (
        publisher.get("title")
        or entry.get("source")
        or entry.get("publisher")
        or company_name
        or ticker
    )
    source_url = str(publisher.get("href") or "").strip()
    title = str(entry.get("title") or "").strip()
    description = str(entry.get("description") or entry.get("summary") or "").strip()
    published_at = str(entry.get("published date") or entry.get("published_at") or "")
    url = str(entry.get("url") or "").strip()

    return {
        "id": url or f"{ticker}:{title}:{published_at}",
        "title": title,
        "source": source,
        "source_url": source_url,
        "publisher_homepage_url": source_url,
        "url": url,
        "published_at": published_at,
        "summary": description,
        "ticker": ticker,
        "company_name": company_name,
        "query": query,
        "source_type": "company_news",
    }


def _company_query_text(ticker: str, company_name: str | None = None) -> str:
    base = (company_name or ticker).strip() or ticker.strip()
    return base


def _sector_query_text(sector: str) -> str:
    normalized = _normalize_sector_name(sector)
    if normalized == "consumerretail":
        label = "consumer retail"
    elif normalized == "industrialsautos":
        label = "industrials autos"
    elif normalized == "realestate":
        label = "real estate"
    else:
        label = normalized.replace("_", " ")
    return f"{label} stock market news"


def _google_news_company_url(ticker: str, company_name: str | None = None) -> str:
    query = quote_plus(_company_query_text(ticker, company_name))
    return f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def _google_news_sector_url(sector: str) -> str:
    query = quote_plus(_sector_query_text(sector))
    return f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


async def _parse_feed(url: str, semaphore: asyncio.Semaphore | None = None):
    async def _parse():
        return await asyncio.to_thread(feedparser.parse, url)

    if semaphore:
        async with semaphore:
            return await _parse()
    return await _parse()


async def _parse_google_feed(url: str):
    global _google_rss_next_request_at

    if GOOGLE_RSS_DELAY_SECONDS <= 0:
        return await asyncio.to_thread(feedparser.parse, url)

    loop = asyncio.get_running_loop()
    async with _get_google_rss_lock():
        delay = _google_rss_next_request_at - loop.time()
        if delay > 0:
            await asyncio.sleep(delay)
        feed = await asyncio.to_thread(feedparser.parse, url)
        _google_rss_next_request_at = loop.time() + GOOGLE_RSS_DELAY_SECONDS
        return feed


async def fetch_cnbc_macro_rss(limit: int = 20) -> list[dict]:
    feed = await _parse_feed(CNBC_MACRO_RSS_URL)
    return [
        _normalize_feed_entry(entry, feed, "cnbc_macro_rss")
        for entry in feed.entries[:limit]
    ]


async def fetch_cnbc_sector_rss(
    sectors: Iterable[str], limit_per_sector: int = 20
) -> list[dict]:
    normalized_sectors = [
        sector
        for sector in {
            _normalize_sector_name(sector) for sector in sectors if str(sector).strip()
        }
        if sector
    ]
    if not normalized_sectors:
        return []

    configured_urls = _load_sector_feed_urls()
    macro_feed = None
    articles: list[dict] = []

    for sector in normalized_sectors:
        urls = configured_urls.get(sector, [])
        if urls:
            feeds = await asyncio.gather(*(_parse_feed(url) for url in urls))
            for feed in feeds:
                for entry in feed.entries[:limit_per_sector]:
                    articles.append(
                        _normalize_feed_entry(entry, feed, "cnbc_sector_rss", sector)
                    )
            continue

        if macro_feed is None:
            macro_feed = await _parse_feed(CNBC_MACRO_RSS_URL)
        for entry in macro_feed.entries[:limit_per_sector]:
            if _should_include_sector_article(entry, sector):
                articles.append(
                    _normalize_feed_entry(entry, macro_feed, "cnbc_sector_rss", sector)
                )

    return _dedupe_articles(articles)


async def fetch_google_company_rss(
    tickers: list[str],
    ticker_metadata: dict[str, dict] | None = None,
    limit_per_ticker: int = 10,
) -> list[dict]:
    if not tickers:
        return []

    ticker_metadata = ticker_metadata or {}
    gnews_semaphore = asyncio.Semaphore(4)
    fallback_threshold = max(2, min(4, limit_per_ticker // 2 or 1))

    async def _fetch_ticker_articles(ticker: str) -> list[dict]:
        normalized_ticker = str(ticker).strip().upper()
        if not normalized_ticker:
            return []

        metadata = (
            ticker_metadata.get(normalized_ticker)
            or ticker_metadata.get(normalized_ticker.lower())
            or {}
        )
        company_name = (
            metadata.get("company_name")
            or metadata.get("name")
            or metadata.get("company")
            or normalized_ticker
        )

        first_query = _company_query_text(normalized_ticker, company_name)
        async with gnews_semaphore:
            first_results = await _fetch_gnews_articles(
                first_query, max(10, limit_per_ticker * 2)
            )
        ticker_articles = [
            _normalize_gnews_entry(entry, first_query, normalized_ticker, company_name)
            for entry in first_results[:limit_per_ticker]
        ]
        deduped_primary = _dedupe_articles(ticker_articles)
        deduped_primary = await _attach_decoded_google_news_urls(deduped_primary)
        if (
            len(deduped_primary) >= fallback_threshold
            or company_name == normalized_ticker
        ):
            return deduped_primary[:limit_per_ticker]

        fallback_query = _company_query_text(normalized_ticker, normalized_ticker)
        async with gnews_semaphore:
            fallback_results = await _fetch_gnews_articles(
                fallback_query, max(10, limit_per_ticker * 2)
            )
        fallback_articles = [
            _normalize_gnews_entry(
                entry, fallback_query, normalized_ticker, company_name
            )
            for entry in fallback_results[:limit_per_ticker]
        ]
        fallback_articles = await _attach_decoded_google_news_urls(fallback_articles)
        return _dedupe_articles(deduped_primary + fallback_articles)[:limit_per_ticker]

    ticker_articles = await asyncio.gather(
        *(_fetch_ticker_articles(ticker) for ticker in tickers)
    )
    flattened = [article for articles in ticker_articles for article in articles]
    return _dedupe_articles(flattened)


async def fetch_google_sector_rss(
    sectors: Iterable[str], limit_per_sector: int = 8
) -> list[dict]:
    normalized_sectors = [
        sector
        for sector in {
            _normalize_sector_name(sector) for sector in sectors if str(sector).strip()
        }
        if sector
    ]
    if not normalized_sectors:
        return []

    rss_semaphore = asyncio.Semaphore(4)

    async def _fetch_sector_articles(sector: str) -> list[dict]:
        async with rss_semaphore:
            feed = await _parse_google_feed(_google_news_sector_url(sector))
        return [
            {
                **_normalize_feed_entry(entry, feed, "google_sector_rss", sector),
                "sector": sector,
                "query": _sector_query_text(sector),
            }
            for entry in feed.entries[:limit_per_sector]
            if _should_include_sector_article(entry, sector)
        ]

    batches = await asyncio.gather(
        *(_fetch_sector_articles(sector) for sector in normalized_sectors)
    )
    flattened = [article for articles in batches for article in articles]
    return _dedupe_articles(flattened)


async def fetch_rss_feeds(tickers: list[str] | None = None) -> list[dict]:
    # Backwards-compatible wrapper for callers that still expect the RSS helper.
    if not tickers:
        return await fetch_cnbc_macro_rss()
    return await fetch_cnbc_sector_rss(tickers)
