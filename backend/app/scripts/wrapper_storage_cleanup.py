from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from app.pipeline.analysis_utils import utcnow_iso
from app.services.supabase import get_supabase


def _is_google_news_wrapper_url(value: str | None) -> bool:
    parsed = urlparse(str(value or "").strip())
    host = (parsed.hostname or "").lower()
    if host != "news.google.com":
        return False
    return parsed.path.startswith(("/rss/articles/", "/articles/", "/read/"))


def _non_wrapper_url(*values: str | None) -> str | None:
    for value in values:
        normalized = str(value or "").strip()
        if normalized and not _is_google_news_wrapper_url(normalized):
            return normalized
    return None


def _fetch_wrapper_rows(
    supabase,
    *,
    since_iso: str,
    tickers: list[str] | None,
    page_size: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        query = (
            supabase.table("shared_ticker_events")
            .select(
                "id,ticker,source_url,canonical_url,resolved_url,original_url,"
                "published_at,created_at,url_resolution_status,url_resolution_error"
            )
            .gte("created_at", since_iso)
            .like("source_url", "https://news.google.com%")
            .order("created_at", desc=True)
            .order("id")
        )
        if tickers:
            query = query.in_("ticker", tickers)
        response = query.range(start, start + page_size - 1).execute()
        page = response.data or []
        rows.extend(
            row for row in page if _is_google_news_wrapper_url(row.get("source_url"))
        )
        if len(page) < page_size:
            return rows
        start += page_size


async def run_cleanup(
    *,
    apply: bool = False,
    days: int = 30,
    tickers: list[str] | None = None,
    concurrency: int = 20,
    timeout: float = 8.0,
    batch_size: int = 50,
) -> dict[str, Any]:
    del concurrency, timeout
    supabase = get_supabase()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    normalized_tickers = sorted({t.strip().upper() for t in tickers or [] if t.strip()})
    rows = await asyncio.to_thread(
        _fetch_wrapper_rows,
        supabase,
        since_iso=since.isoformat(),
        tickers=normalized_tickers or None,
        page_size=batch_size,
    )

    quarantined = 0
    if apply:
        for row in rows:
            replacement_url = _non_wrapper_url(
                row.get("resolved_url"),
                row.get("canonical_url"),
            )
            update = {
                "original_url": row.get("original_url") or row.get("source_url"),
                "source_url": replacement_url,
                "canonical_url": replacement_url,
                "resolved_url": replacement_url,
                "url_resolution_status": "unresolved_wrapper_quarantined",
                "url_resolution_error": "post_run_wrapper_cleanup_unresolved_google_wrapper",
                "data_status": "quarantined",
                "analysis_status": "excluded",
                "factored_into_score": False,
                "headline_only": True,
                "limited_reason": "unresolved_google_news_wrapper",
                "rejection_reason": "unresolved_google_news_wrapper",
                "updated_at": utcnow_iso(),
            }
            await asyncio.to_thread(
                lambda row_id=row["id"], payload=update: supabase.table(
                    "shared_ticker_events"
                )
                .update(payload)
                .eq("id", row_id)
                .execute()
            )
            quarantined += 1

    remaining = await asyncio.to_thread(
        _fetch_wrapper_rows,
        supabase,
        since_iso=since.isoformat(),
        tickers=normalized_tickers or None,
        page_size=batch_size,
    )
    report = {
        "status": "ok" if not remaining else "leaks_remaining",
        "apply": apply,
        "days": days,
        "tickers": normalized_tickers,
        "found": len(rows),
        "quarantined": quarantined,
        "remaining_leaks": len(remaining),
        "sample_remaining": remaining[:10],
    }
    if apply and remaining:
        raise RuntimeError(f"Wrapper cleanup left {len(remaining)} source_url leaks")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--tickers", default="")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    report = asyncio.run(
        run_cleanup(
            apply=args.apply,
            days=args.days,
            tickers=tickers or None,
            concurrency=args.concurrency,
            timeout=args.timeout,
            batch_size=args.batch_size,
        )
    )
    print(report)


if __name__ == "__main__":
    main()
