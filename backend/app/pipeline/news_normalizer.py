from datetime import datetime, timezone
from typing import Any
import re

from .analysis_utils import make_event_hash


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"&amp;", "&", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _body_html_like(value: Any) -> bool:
    text = str(value or "")
    return bool(text and ("<a " in text or _HTML_TAG_RE.search(text)))


def _evidence_quality(title: str, body: str, summary: str, *, raw_body: Any) -> str:
    clean_title = _strip_html(title)
    clean_body = _strip_html(body)
    clean_summary = _strip_html(summary)
    body_words = len(clean_body.split())

    if not clean_body:
        return "title_only"
    if _body_html_like(raw_body):
        return "title_only"
    if clean_body == clean_title or clean_body == clean_summary:
        return "title_only"
    if body_words >= 120:
        return "full_body"
    if body_words >= 60:
        return "partial_body"
    if body_words >= 12:
        return "headline_summary"
    if clean_summary and len(clean_summary.split()) >= 12:
        return "headline_summary"
    return "title_only"


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
    raw_title = article.get("title") or article.get("headline") or ""
    raw_summary = article.get("summary") or article.get("body") or ""
    incoming_body = article.get("body") or ""
    raw_body = incoming_body or raw_summary
    title = _strip_html(raw_title)
    summary = _strip_html(raw_summary)
    body = _strip_html(raw_body)
    source = article.get("source") or source_type
    url = article.get("url") or ""
    source_url = article.get("source_url") or (article.get("raw") or {}).get(
        "source_url"
    )
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
        "source_url": source_url or "",
        "title": title,
        "summary": summary,
        "body": body,
        "evidence_quality": _evidence_quality(title, body, summary, raw_body=raw_body),
        "url": url,
        "published_at": published_at,
        "ticker_hints": sorted({ticker.upper() for ticker in ticker_hints if ticker}),
        "sector_hint": sector_hint,
        "raw": article,
    }

    return normalized


def normalize_news_batch(articles: list[dict], source_type: str) -> list[dict]:
    return [normalize_news_item(article, source_type) for article in articles]
