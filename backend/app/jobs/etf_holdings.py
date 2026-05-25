from __future__ import annotations

from datetime import date
from typing import Any

from app.services.supabase import get_supabase


ETF_HOLDING_SEEDS: dict[str, list[tuple[str, float]]] = {
    "SPY": [("AAPL", 7.1), ("MSFT", 6.8), ("NVDA", 6.2), ("AMZN", 3.8), ("META", 2.9), ("AVGO", 2.2), ("GOOGL", 2.1), ("GOOG", 1.8), ("BRK.B", 1.7), ("TSLA", 1.6)],
    "QQQ": [("NVDA", 9.2), ("MSFT", 8.1), ("AAPL", 7.9), ("AMZN", 5.2), ("AVGO", 4.6), ("META", 4.2), ("NFLX", 2.7), ("COST", 2.6), ("GOOGL", 2.5), ("GOOG", 2.4)],
    "VTI": [("AAPL", 6.2), ("MSFT", 5.8), ("NVDA", 5.4), ("AMZN", 3.2), ("META", 2.5), ("AVGO", 1.9), ("GOOGL", 1.8), ("GOOG", 1.6), ("BRK.B", 1.5), ("TSLA", 1.4)],
}


def _active_etfs(supabase) -> list[str]:
    tickers: set[str] = set()
    for table in ("positions", "watchlist_items"):
        for row in supabase.table(table).select("ticker").execute().data or []:
            ticker = str(row.get("ticker") or "").upper()
            if ticker in ETF_HOLDING_SEEDS:
                tickers.add(ticker)
    return sorted(tickers)


def rows_for_etf(ticker: str, as_of: str | None = None) -> list[dict[str, Any]]:
    as_of = as_of or date.today().isoformat()
    return [
        {
            "etf_ticker": ticker.upper(),
            "holding_ticker": holding,
            "weight_pct": weight,
            "rank": index + 1,
            "source": "static_seed",
            "as_of": as_of,
        }
        for index, (holding, weight) in enumerate(ETF_HOLDING_SEEDS.get(ticker.upper(), []))
    ]


def run() -> dict[str, Any]:
    supabase = get_supabase()
    rows = [row for ticker in _active_etfs(supabase) for row in rows_for_etf(ticker)]
    if rows:
        supabase.table("etf_holdings").upsert(
            rows,
            on_conflict="etf_ticker,holding_ticker,as_of",
        ).execute()
    return {"status": "completed", "items_processed": len(rows), "metadata": {"etfs": sorted({row["etf_ticker"] for row in rows})}}


def run_from_env() -> dict[str, Any]:
    return run()
