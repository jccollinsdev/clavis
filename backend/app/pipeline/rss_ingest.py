import asyncio
import json
import os
import re
from urllib.parse import quote_plus
from datetime import datetime, timezone
from typing import Iterable

import feedparser


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
    if isinstance(raw_source, dict):
        source = raw_source.get("title", "") or feed.feed.get("title", "CNBC RSS")
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
        "url": entry.get("link", ""),
        "published_at": _entry_timestamp(entry),
        "summary": entry.get("summary", ""),
        "sector": sector,
        "source_type": source_type,
    }


def _company_query_text(ticker: str, company_name: str | None = None) -> str:
    base = (company_name or ticker).strip() or ticker.strip()
    return f"{base} stock"


def _google_news_company_url(ticker: str, company_name: str | None = None) -> str:
    query = quote_plus(_company_query_text(ticker, company_name))
    return f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


async def _parse_feed(url: str):
    return await asyncio.to_thread(feedparser.parse, url)


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

    deduped: list[dict] = []
    seen: set[str] = set()
    for article in articles:
        key = article.get("url") or article.get("id") or article.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(article)

    return deduped


async def fetch_google_company_rss(
    tickers: list[str],
    ticker_metadata: dict[str, dict] | None = None,
    limit_per_ticker: int = 10,
) -> list[dict]:
    if not tickers:
        return []

    ticker_metadata = ticker_metadata or {}
    requests = []
    ticker_lookup: list[tuple[str, str]] = []

    for ticker in tickers:
        normalized_ticker = str(ticker).strip().upper()
        if not normalized_ticker:
            continue
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
        query_sources = [
            _google_news_company_url(normalized_ticker, company_name),
            _google_news_company_url(normalized_ticker, normalized_ticker),
        ]
        for url in dict.fromkeys(query_sources):
            requests.append(_parse_feed(url))
            ticker_lookup.append((normalized_ticker, company_name))

    feeds = await asyncio.gather(*requests) if requests else []
    articles: list[dict] = []

    for (ticker, company_name), feed in zip(ticker_lookup, feeds):
        for entry in feed.entries[:limit_per_ticker]:
            articles.append(
                {
                    **_normalize_feed_entry(entry, feed, "company_news"),
                    "ticker": ticker,
                    "company_name": company_name,
                    "query": _company_query_text(ticker, company_name),
                }
            )

    deduped: list[dict] = []
    seen: set[str] = set()
    for article in articles:
        key = article.get("url") or article.get("id") or article.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(article)

    return deduped


async def fetch_rss_feeds(tickers: list[str] | None = None) -> list[dict]:
    # Backwards-compatible wrapper for callers that still expect the RSS helper.
    if not tickers:
        return await fetch_cnbc_macro_rss()
    return await fetch_cnbc_sector_rss(tickers)
