from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_supabase
from app.services.ticker_cache_service import (
    list_active_sp500_tickers,
    refresh_ticker_snapshot,
)


DIMENSION_KEYS = (
    "financial_health",
    "news_sentiment",
    "macro_exposure",
    "sector_exposure",
    "volatility",
)
FRESHNESS_HOURS = 24
DEFAULT_BATCH_SIZE = 15
DEFAULT_INTER_BATCH_DELAY_SECONDS = 5


def _coerce_target_date(value: date | str | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def snapshot_dimensions_fresh(
    snapshot: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    freshness_hours: int = FRESHNESS_HOURS,
) -> bool:
    if not snapshot:
        return False
    refreshed = snapshot.get("dimension_last_refreshed") or {}
    if not isinstance(refreshed, dict):
        return False
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=freshness_hours)
    for key in DIMENSION_KEYS:
        refreshed_at = _parse_timestamp(refreshed.get(key))
        if refreshed_at is None or refreshed_at < cutoff:
            return False
    return True


def _latest_snapshots_for_date(
    supabase,
    tickers: list[str],
    *,
    snapshot_date: date,
) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    rows = (
        supabase.table("ticker_risk_snapshots")
        .select("ticker,dimension_last_refreshed,analysis_as_of,methodology_version")
        .eq("snapshot_date", snapshot_date.isoformat())
        .in_("ticker", tickers)
        .execute()
        .data
        or []
    )
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").upper()
        if ticker and ticker not in latest:
            latest[ticker] = row
    return latest


def run(
    *,
    limit: int | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    inter_batch_delay_seconds: int = DEFAULT_INTER_BATCH_DELAY_SECONDS,
    target_date: date | str | None = None,
    force_refresh: bool = False,
) -> dict:
    snapshot_date = _coerce_target_date(target_date)
    supabase = get_supabase()
    tickers = list_active_sp500_tickers(supabase, limit=limit)
    date_snapshots = _latest_snapshots_for_date(
        supabase,
        tickers,
        snapshot_date=snapshot_date,
    )

    # force_refresh bypasses both the dimension freshness check and the
    # existing-AI-snapshot early-return in refresh_ticker_snapshot, so Polygon
    # bar data and real sector_beta / beta_to_spy are always recomputed.
    effective_job_type = "manual_refresh" if force_refresh else "daily"

    processed = 0
    skipped = 0
    failed: list[dict[str, str]] = []
    batch_size = max(1, int(batch_size))

    for index, ticker in enumerate(tickers):
        if not force_refresh and snapshot_dimensions_fresh(date_snapshots.get(ticker)):
            skipped += 1
            continue
        try:
            refresh_ticker_snapshot(
                supabase,
                ticker=ticker,
                job_type=effective_job_type,
                snapshot_date=snapshot_date,
            )
            processed += 1
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})

        if (
            inter_batch_delay_seconds > 0
            and (index + 1) % batch_size == 0
            and index + 1 < len(tickers)
        ):
            time.sleep(inter_batch_delay_seconds)

    return {
        "status": "completed" if not failed else "failed",
        "items_processed": processed,
        "items_skipped": skipped,
        "items_failed": len(failed),
        "metadata": {
            "requested": len(tickers),
            "target_date": snapshot_date.isoformat(),
            "force_refresh": force_refresh,
            "failed": failed[:25],
        },
    }


def run_from_env() -> dict:
    limit = os.getenv("COMPOSITE_RECOMPUTE_LIMIT")
    target_date = os.getenv("COMPOSITE_RECOMPUTE_TARGET_DATE")
    force_refresh = os.getenv("COMPOSITE_RECOMPUTE_FORCE_REFRESH", "").lower() in (
        "1", "true", "yes",
    )
    return run(
        limit=int(limit) if limit else None,
        target_date=target_date or None,
        force_refresh=force_refresh,
    )
