from __future__ import annotations

from datetime import date, timedelta
import time
from typing import Any

import requests

from app.config import get_settings
from app.services.supabase import get_supabase
from app.services.ticker_cache_service import list_active_sp500_tickers


FINNHUB_EARNINGS_URL = "https://finnhub.io/api/v1/calendar/earnings"


def _request_earnings(from_date: str, to_date: str) -> list[dict[str, Any]]:
    api_key = get_settings().finnhub_api_key
    if not api_key:
        return []

    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(
                FINNHUB_EARNINGS_URL,
                params={"from": from_date, "to": to_date, "token": api_key},
                timeout=20,
            )
            if response.status_code == 429:
                time.sleep(min(8.0, 1.0 * (2**attempt)))
                continue
            response.raise_for_status()
            payload = response.json() or {}
            return payload.get("earningsCalendar") or []
        except Exception as exc:
            last_error = exc
            time.sleep(min(8.0, 1.0 * (2**attempt)))
    if last_error:
        raise last_error
    return []


def _active_portfolio_tickers(supabase) -> set[str]:
    tickers: set[str] = set()
    for row in (
        supabase.table("positions")
        .select("ticker")
        .execute()
        .data
        or []
    ):
        ticker = str(row.get("ticker") or "").upper()
        if ticker:
            tickers.add(ticker)
    for row in (
        supabase.table("watchlist_items")
        .select("ticker")
        .execute()
        .data
        or []
    ):
        ticker = str(row.get("ticker") or "").upper()
        if ticker:
            tickers.add(ticker)
    return tickers


def _row_from_finnhub(item: dict[str, Any], tracked_tickers: set[str]) -> dict[str, Any] | None:
    ticker = str(item.get("symbol") or "").upper()
    report_date = item.get("date")
    if not ticker or not report_date or ticker not in tracked_tickers:
        return None
    return {
        "ticker": ticker,
        "report_date": report_date,
        "est_eps": item.get("epsEstimate"),
        "est_revenue": item.get("revenueEstimate"),
        "time_of_day": item.get("hour"),
        "fiscal_period": item.get("quarter"),
        "source": "finnhub",
    }


def run(days_ahead: int = 14) -> dict[str, Any]:
    supabase = get_supabase()
    today = date.today()
    from_date = today.isoformat()
    to_date = (today + timedelta(days=days_ahead)).isoformat()
    tracked_tickers = set(list_active_sp500_tickers(supabase)) | _active_portfolio_tickers(supabase)
    raw_items = _request_earnings(from_date, to_date)
    rows = [
        row
        for item in raw_items
        if (row := _row_from_finnhub(item, tracked_tickers)) is not None
    ]
    if not rows:
        return {
            "status": "completed",
            "items_processed": 0,
            "metadata": {"window": [from_date, to_date], "fetched": len(raw_items)},
        }
    result = (
        supabase.table("earnings_calendar")
        .upsert(rows, on_conflict="ticker,report_date")
        .execute()
    )
    return {
        "status": "completed",
        "items_processed": len(result.data or rows),
        "metadata": {"window": [from_date, to_date], "fetched": len(raw_items)},
    }


def run_from_env() -> dict[str, Any]:
    return run()
