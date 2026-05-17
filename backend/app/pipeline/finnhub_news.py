"""Finnhub news ingestion — company-specific news discovery.

Primary news source for the Finnhub-first pipeline.
fetch_finnhub_ticker_news is the main entry point (7-day window, per-ticker).
fetch_company_news and fetch_market_news are kept for backward compat.
"""
from __future__ import annotations

import asyncio
import finnhub
from datetime import datetime, timedelta, timezone
from typing import List

from ..config import get_settings

settings = get_settings()


def get_finnhub_client() -> finnhub.Client:
    return finnhub.Client(api_key=settings.finnhub_api_key)


def _to_iso(ts) -> str:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    return str(ts or "")


def _normalize_item(item: dict, ticker: str) -> dict:
    return {
        "id": str(item.get("id", "")),
        "title": item.get("headline", ""),
        "source": item.get("source", ""),
        "source_url": item.get("url", ""),
        "url": item.get("url", ""),
        "published_at": _to_iso(item.get("datetime")),
        "summary": item.get("summary", ""),
        "ticker": ticker,
        "category": item.get("category", ""),
        "source_type": "finnhub",
    }


def _dedupe(articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for a in articles:
        key = str(a.get("url") or "").strip().rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


async def fetch_finnhub_ticker_news(
    tickers: list[str],
    *,
    days: int = 7,
    limit_per_ticker: int = 10,
) -> tuple[dict[str, list[dict]], dict]:
    """Fetch Finnhub company news for the trailing `days` window.

    Returns (per_ticker, metrics) where:
    - per_ticker: dict[ticker -> deduped list of normalized articles]
    - metrics: calls, rate_limited, errors, articles_raw, per_ticker_raw
    """
    if not settings.finnhub_api_key:
        return (
            {t: [] for t in tickers},
            {"calls": 0, "rate_limited": 0, "errors": {}, "articles_raw": 0, "per_ticker_raw": {}},
        )

    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    metrics: dict = {
        "calls": 0,
        "rate_limited": 0,
        "errors": {},
        "articles_raw": 0,
        "per_ticker_raw": {},
    }
    per_ticker: dict[str, list[dict]] = {}

    def _sync_fetch(ticker: str) -> list:
        client = get_finnhub_client()
        return client.company_news(ticker, _from=from_date, to=to_date) or []

    for ticker in tickers:
        metrics["calls"] += 1
        try:
            raw = await asyncio.to_thread(_sync_fetch, ticker)
        except Exception as exc:
            msg = str(exc).lower()
            if "429" in msg or "rate" in msg or "too many" in msg:
                metrics["rate_limited"] += 1
                metrics["errors"][ticker] = "rate_limited"
            else:
                metrics["errors"][ticker] = str(exc)[:80]
            per_ticker[ticker] = []
            metrics["per_ticker_raw"][ticker] = 0
            continue

        metrics["articles_raw"] += len(raw)
        metrics["per_ticker_raw"][ticker] = len(raw)
        normalized = [_normalize_item(item, ticker) for item in raw]
        per_ticker[ticker] = _dedupe(normalized)[:limit_per_ticker]

    return per_ticker, metrics


# ── backward-compat ────────────────────────────────────────────────────────────

async def fetch_company_news(tickers: List[str]) -> List[dict]:
    """Legacy 2-day window. Prefer fetch_finnhub_ticker_news."""
    if not settings.finnhub_api_key:
        return []
    per_ticker, _ = await fetch_finnhub_ticker_news(tickers, days=2, limit_per_ticker=10)
    return [a for arts in per_ticker.values() for a in arts]


async def fetch_market_news() -> List[dict]:
    if not settings.finnhub_api_key:
        return []

    def _sync() -> list:
        client = get_finnhub_client()
        return client.general_news("general", min_id=0) or []

    try:
        general = await asyncio.to_thread(_sync)
    except Exception:
        return []

    return [
        {
            "id": str(item.get("id", "")),
            "title": item.get("headline", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "published_at": _to_iso(item.get("datetime")),
            "summary": item.get("summary", ""),
            "category": "market",
        }
        for item in general[:15]
    ]
