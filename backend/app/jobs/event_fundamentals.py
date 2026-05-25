from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.services.supabase import get_supabase
from app.services.ticker_metadata import upsert_ticker_metadata


def _calendar_tickers(supabase, target_date: str) -> list[str]:
    rows = (
        supabase.table("earnings_calendar")
        .select("ticker")
        .eq("report_date", target_date)
        .execute()
        .data
        or []
    )
    return sorted({str(row.get("ticker") or "").upper() for row in rows if row.get("ticker")})


def run(dry_run: bool = False) -> dict[str, Any]:
    supabase = get_supabase()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tickers = sorted(set(_calendar_tickers(supabase, tomorrow)) | set(_calendar_tickers(supabase, yesterday)))
    if dry_run:
        return {"status": "completed", "items_processed": 0, "metadata": {"tickers": tickers, "dry_run": True}}

    processed = 0
    failed: list[dict[str, str]] = []
    for ticker in tickers:
        try:
            if upsert_ticker_metadata(supabase, ticker):
                processed += 1
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})
    return {
        "status": "completed" if not failed else "failed",
        "items_processed": processed,
        "items_failed": len(failed),
        "metadata": {"tickers": tickers, "failed": failed[:25]},
    }


def run_from_env() -> dict[str, Any]:
    return run()
