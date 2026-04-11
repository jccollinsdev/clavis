from datetime import datetime, timezone
from typing import Any

from .analysis_utils import make_event_hash


def _normalize_timestamp(value: Any) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()

    raw = str(value).strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()

    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(raw).astimezone(timezone.utc).isoformat()
    except ValueError:
        return raw


def normalize_news_item(article: dict, source_type: str) -> dict:
    title = article.get("title") or article.get("headline") or ""
    summary = article.get("summary") or article.get("body") or ""
    body = article.get("body") or summary
    source = article.get("source") or source_type
    url = article.get("url") or ""
    published_at = _normalize_timestamp(
        article.get("published_at") or article.get("datetime")
    )
    ticker_hints = []
    sector_hint = article.get("sector") or article.get("sector_hint")

    if article.get("ticker"):
        ticker_hints.append(article["ticker"])
    ticker_hints.extend(article.get("affected_tickers") or [])

    normalized = {
        "external_id": str(article.get("id") or article.get("external_id") or ""),
        "event_hash": make_event_hash(
            article.get("id"),
            url,
            title,
            summary[:200],
            published_at,
        ),
        "source_type": source_type,
        "source": source,
        "title": title,
        "summary": summary,
        "body": body,
        "url": url,
        "published_at": published_at,
        "ticker_hints": sorted({ticker.upper() for ticker in ticker_hints if ticker}),
        "sector_hint": sector_hint,
        "raw": article,
    }

    return normalized


def normalize_news_batch(articles: list[dict], source_type: str) -> list[dict]:
    return [normalize_news_item(article, source_type) for article in articles]
