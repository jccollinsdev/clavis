#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


DEFAULT_TICKERS = ["AAPL", "NVDA", "MSFT", "AMD", "JPM", "XOM"]


def _date_window(anchor: date, days: int) -> list[date]:
    start = anchor - timedelta(days=days)
    return [start + timedelta(days=offset) for offset in range(days)]


def _report(payload: dict, output_path: str | None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate 14-day ticker snapshot backfill coverage")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--tickers", nargs="*", default=DEFAULT_TICKERS)
    parser.add_argument("--anchor-date", default=None, help="YYYY-MM-DD; defaults to today")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(backend_root / ".env")

    from app.services.supabase import get_supabase

    anchor = date.fromisoformat(args.anchor_date) if args.anchor_date else date.today()
    window = _date_window(anchor, args.days)
    expected_dates = [day.isoformat() for day in window]
    start_date = expected_dates[0]
    end_date = expected_dates[-1]
    tickers = sorted({ticker.strip().upper() for ticker in args.tickers if ticker.strip()})

    supabase = get_supabase()

    sample_rows = (
        supabase.table("ticker_risk_snapshots")
        .select("ticker,snapshot_date,grade,composite_score,methodology_version,analysis_as_of")
        .in_("ticker", tickers)
        .gte("snapshot_date", start_date)
        .lte("snapshot_date", end_date)
        .order("snapshot_date")
        .execute()
        .data
        or []
    )

    universe_rows = (
        supabase.table("ticker_risk_snapshots")
        .select("ticker,snapshot_date")
        .gte("snapshot_date", start_date)
        .lte("snapshot_date", end_date)
        .execute()
        .data
        or []
    )

    sample_dates_by_ticker: dict[str, set[str]] = defaultdict(set)
    latest_sample_by_ticker: dict[str, dict] = {}
    for row in sample_rows:
        ticker = str(row.get("ticker") or "").upper()
        snapshot_date = str(row.get("snapshot_date") or "")
        if not ticker or not snapshot_date:
            continue
        sample_dates_by_ticker[ticker].add(snapshot_date)
        latest_sample_by_ticker[ticker] = row

    universe_counts: dict[str, int] = defaultdict(int)
    unique_tickers_by_day: dict[str, set[str]] = defaultdict(set)
    for row in universe_rows:
        ticker = str(row.get("ticker") or "").upper()
        snapshot_date = str(row.get("snapshot_date") or "")
        if not ticker or not snapshot_date:
            continue
        universe_counts[snapshot_date] += 1
        unique_tickers_by_day[snapshot_date].add(ticker)

    payload = {
        "anchor_date": anchor.isoformat(),
        "days": args.days,
        "window_start": start_date,
        "window_end": end_date,
        "sample_tickers": {
            ticker: {
                "dates_present": sorted(sample_dates_by_ticker.get(ticker, set())),
                "missing_dates": [
                    snapshot_date
                    for snapshot_date in expected_dates
                    if snapshot_date not in sample_dates_by_ticker.get(ticker, set())
                ],
                "coverage_count": len(sample_dates_by_ticker.get(ticker, set())),
                "latest_row": latest_sample_by_ticker.get(ticker),
            }
            for ticker in tickers
        },
        "universe_daily_counts": {
            snapshot_date: {
                "rows": universe_counts.get(snapshot_date, 0),
                "unique_tickers": len(unique_tickers_by_day.get(snapshot_date, set())),
            }
            for snapshot_date in expected_dates
        },
    }

    _report(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
