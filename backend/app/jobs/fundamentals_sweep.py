"""Weekly fundamentals sweep — refreshes Finnhub stock/metric for ALL universe tickers.

Unlike event_fundamentals_pull (which only runs for earnings-calendar tickers),
this job pulls D/E, FCF margin, interest coverage, current ratio, and revenue growth
for every active ticker in ticker_universe once a week (Sunday 08:00 UTC).

This is what keeps Financial Health scores accurate for the full 504-ticker
universe, not just the 6-ish tickers that have upcoming earnings each day.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

BATCH_SIZE = 20          # tickers per batch
INTER_BATCH_DELAY = 2.0  # seconds between batches (Finnhub free: 60 req/min)


def run() -> dict[str, Any]:
    from app.services.supabase import get_supabase
    from app.services.ticker_metadata import (
        fetch_ticker_details_from_finnhub,
        upsert_ticker_metadata,
    )

    supabase = get_supabase()

    # Fetch full universe
    rows = (
        supabase.table("ticker_universe")
        .select("ticker")
        .eq("is_active", True)
        .execute()
        .data
        or []
    )
    tickers = [r["ticker"] for r in rows if r.get("ticker")]
    total = len(tickers)
    logger.info("[FUNDAMENTALS_SWEEP] Starting sweep for %d tickers.", total)

    processed = 0
    failed: list[str] = []
    skipped = 0  # Finnhub returned no data (common for some international ADRs)

    for i in range(0, total, BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        for ticker in batch:
            try:
                data = fetch_ticker_details_from_finnhub(ticker)
                if data:
                    upsert_ticker_metadata(supabase, ticker, data)
                    processed += 1
                else:
                    skipped += 1
                    logger.debug("[FUNDAMENTALS_SWEEP] No Finnhub data for %s (skipped).", ticker)
            except Exception as exc:
                failed.append(ticker)
                logger.warning(
                    "[FUNDAMENTALS_SWEEP] Failed to update %s: %s", ticker, exc
                )

        # Rate-limit between batches
        if i + BATCH_SIZE < total:
            time.sleep(INTER_BATCH_DELAY)

    status = "completed" if not failed else "failed"
    logger.info(
        "[FUNDAMENTALS_SWEEP] Done. processed=%d skipped=%d failed=%d",
        processed, skipped, len(failed),
    )
    return {
        "status": status,
        "items_processed": processed,
        "items_skipped": skipped,
        "items_failed": len(failed),
        "metadata": {
            "total_tickers": total,
            "failed": failed[:25],
        },
    }


def run_from_env() -> dict[str, Any]:
    return run()
