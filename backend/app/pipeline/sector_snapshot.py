"""Daily sector ETF snapshot job.

Writes one `sector_regime_snapshots` row per sector ETF per trading day:
- close, previous_close, day_change_pct, day_change_amount

Per CLAVIX_TRUTH §6, this is the data backbone for the Today sector heat grid
and the Sector Exposure audit. The full quant layer (sector beta / momentum /
breadth / narrative) is still TODO — this job only handles price snapshots so
the iOS Today screen can render ETF day-change today.

Usage:
    from app.pipeline.sector_snapshot import refresh_sector_snapshots
    refresh_sector_snapshots()
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable

from ..services.polygon import fetch_aggs
from ..services.supabase import get_supabase

logger = logging.getLogger(__name__)

# CLAVIX_TRUTH §6 / §6 sector mapping. Keep in sync with the iOS sector
# normalization in `ClavixTodayView`.
SECTOR_ETFS: list[tuple[str, str]] = [
    ("Technology",             "XLK"),
    ("Health Care",            "XLV"),
    ("Financials",             "XLF"),
    ("Energy",                 "XLE"),
    ("Consumer Discretionary", "XLY"),
    ("Consumer Staples",       "XLP"),
    ("Industrials",            "XLI"),
    ("Utilities",              "XLU"),
    ("Materials",              "XLB"),
    ("Real Estate",            "XLRE"),
    ("Communication Services", "XLC"),
    # VTI is the broad-market reference shown in the Today sector grid.
    ("US Total Market",        "VTI"),
]


def _latest_two_bars(ticker: str) -> tuple[dict, dict] | None:
    """Return (most_recent_close_bar, prior_close_bar) using Polygon aggs.

    Falls back to the available history when there are fewer than two bars
    in the look-back window.
    """
    # 7-day window covers weekends + holidays for daily resolution.
    bars = fetch_aggs(ticker, days=7) or []
    if not bars:
        return None
    if len(bars) < 2:
        return (bars[-1], bars[-1])
    return (bars[-1], bars[-2])


def _snapshot_row(sector: str, etf: str, latest: dict, prior: dict) -> dict:
    close = latest.get("c")
    prev_close = prior.get("c")
    try:
        day_change_amount = float(close) - float(prev_close)
        day_change_pct = (day_change_amount / float(prev_close)) * 100.0 if prev_close else None
    except (TypeError, ValueError):
        day_change_amount = None
        day_change_pct = None

    snapshot_ts = latest.get("t")
    snapshot_date = None
    if isinstance(snapshot_ts, int):
        snapshot_date = datetime.fromtimestamp(snapshot_ts / 1000, tz=timezone.utc).date().isoformat()
    else:
        snapshot_date = datetime.now(timezone.utc).date().isoformat()

    return {
        "sector":             sector,
        "snapshot_date":      snapshot_date,
        "etf":                etf,
        "source_etf":         etf,
        "etf_close":          close,
        "etf_previous_close": prev_close,
        "etf_day_change_pct": day_change_pct,
        "day_change_pct":     day_change_pct,
        "day_change_amount":  day_change_amount,
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "data_status":        "price_only",
    }


def refresh_sector_snapshots(sectors: Iterable[tuple[str, str]] = SECTOR_ETFS) -> int:
    """Pull daily ETF bars from Polygon and upsert sector_regime_snapshots rows.

    Returns the number of rows successfully written. Skips ETFs that Polygon
    couldn't return data for (e.g. weekend before market open) — those become
    missing rows that the next day's run will fill.
    """
    supabase = get_supabase()
    written = 0
    for sector, etf in sectors:
        try:
            bars = _latest_two_bars(etf)
        except Exception:
            logger.exception("Failed to pull aggs for %s (%s)", sector, etf)
            continue
        if not bars:
            logger.info("No bars returned for %s (%s); skipping", sector, etf)
            continue
        latest, prior = bars
        row = _snapshot_row(sector, etf, latest, prior)
        try:
            # Upsert by (sector, snapshot_date) — newer runs overwrite the same day.
            existing = (
                supabase.table("sector_regime_snapshots")
                .select("id")
                .eq("sector", sector)
                .eq("snapshot_date", row["snapshot_date"])
                .limit(1)
                .execute()
                .data
            )
            if existing:
                supabase.table("sector_regime_snapshots") \
                    .update(row) \
                    .eq("id", existing[0]["id"]) \
                    .execute()
            else:
                supabase.table("sector_regime_snapshots").insert(row).execute()
            written += 1
        except Exception:
            logger.exception("Failed to write sector snapshot for %s", sector)
    logger.info("refresh_sector_snapshots wrote %d rows", written)
    return written
