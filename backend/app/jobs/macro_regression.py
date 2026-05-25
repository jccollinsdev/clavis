from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from app.services.supabase import get_supabase
from app.services.ticker_cache_service import list_active_sp500_tickers


FACTOR_TICKERS = {
    "beta_10y": "TLT",
    "beta_dxy": "UUP",
    "beta_wti": "USO",
    "beta_vix": "VIXY",
    "beta_spy": "SPY",
}
FACTOR_ORDER = tuple(FACTOR_TICKERS)
FRESHNESS_DAYS = 30
RETURN_WINDOW = 252
LOOKBACK_DAYS = 430
MIN_TRADING_DAYS = 60


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _latest_snapshot_for_ticker(supabase, ticker: str) -> dict[str, Any] | None:
    rows = (
        supabase.table("ticker_risk_snapshots")
        .select("id,ticker,dimension_inputs,dimension_last_refreshed,analysis_as_of,updated_at")
        .eq("ticker", ticker)
        .order("analysis_as_of", desc=True)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _macro_refresh_is_fresh(
    snapshot: dict[str, Any] | None,
    *,
    now: datetime,
) -> bool:
    if not snapshot:
        return False
    refreshed = _json_object(snapshot.get("dimension_last_refreshed"))
    refreshed_at = _parse_timestamp(refreshed.get("macro_exposure"))
    if refreshed_at is None:
        return False
    return refreshed_at >= now - timedelta(days=FRESHNESS_DAYS)


def _price_rows_for_ticker(
    supabase,
    ticker: str,
    *,
    cutoff: datetime,
) -> list[dict[str, Any]]:
    return (
        supabase.table("prices")
        .select("ticker,price,recorded_at")
        .eq("ticker", ticker)
        .gte("recorded_at", cutoff.isoformat())
        .order("recorded_at", desc=False)
        .execute()
        .data
        or []
    )


def _daily_close_series(rows: list[dict[str, Any]]) -> list[tuple[str, float]]:
    latest_by_day: dict[str, tuple[datetime, float]] = {}
    for row in rows:
        timestamp = _parse_timestamp(row.get("recorded_at"))
        try:
            price = float(row.get("price"))
        except (TypeError, ValueError):
            continue
        if timestamp is None:
            continue
        day = timestamp.date().isoformat()
        existing = latest_by_day.get(day)
        if existing is None or timestamp > existing[0]:
            latest_by_day[day] = (timestamp, price)
    ordered_days = sorted(latest_by_day)
    return [(day, latest_by_day[day][1]) for day in ordered_days]


def _daily_returns(series: list[tuple[str, float]]) -> list[tuple[str, float]]:
    returns: list[tuple[str, float]] = []
    for index in range(1, len(series)):
        previous = series[index - 1][1]
        current = series[index][1]
        if previous <= 0:
            continue
        returns.append((series[index][0], (current - previous) / previous))
    return returns


def _build_regression_payload(
    ticker_returns: list[tuple[str, float]],
    factor_returns: dict[str, list[tuple[str, float]]],
    *,
    computed_at: datetime,
) -> dict[str, Any] | None:
    asset_map = {day: value for day, value in ticker_returns}
    factor_maps = {
        key: {day: value for day, value in values}
        for key, values in factor_returns.items()
    }
    common_days = sorted(
        set(asset_map).intersection(*(set(factor_maps[key]) for key in FACTOR_ORDER))
    )
    if len(common_days) < MIN_TRADING_DAYS:
        return None
    window_days = common_days[-RETURN_WINDOW:]
    X = np.array(
        [[factor_maps[key][day] for key in FACTOR_ORDER] for day in window_days],
        dtype=float,
    )
    y = np.array([asset_map[day] for day in window_days], dtype=float)
    design = np.column_stack([np.ones(len(window_days)), X])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coefficients
    residual = y - fitted
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 0.0 if ss_tot <= 0 else max(0.0, min(1.0, 1.0 - (ss_res / ss_tot)))
    betas = {
        key: round(float(coefficients[index + 1]), 6)
        for index, key in enumerate(FACTOR_ORDER)
    }
    return {
        **betas,
        "factor_exposures": betas,
        "r_squared": round(r_squared, 4),
        "trading_days_used": len(window_days),
        "computed_at": computed_at.isoformat(),
    }


def _merge_macro_inputs(
    snapshot: dict[str, Any],
    *,
    macro_payload: dict[str, Any],
    computed_at: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dimension_inputs = dict(_json_object(snapshot.get("dimension_inputs")))
    macro_inputs = dict(_json_object(dimension_inputs.get("macro_exposure")))
    macro_inputs.update(macro_payload)
    macro_inputs.setdefault("as_of_date", computed_at.date().isoformat())
    dimension_inputs["macro_exposure"] = macro_inputs

    dimension_last_refreshed = dict(_json_object(snapshot.get("dimension_last_refreshed")))
    dimension_last_refreshed["macro_exposure"] = computed_at.isoformat()
    return dimension_inputs, dimension_last_refreshed


def run(
    *,
    limit: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    supabase = get_supabase()
    computed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = computed_at - timedelta(days=LOOKBACK_DAYS)
    tickers = list_active_sp500_tickers(supabase, limit=limit)

    factor_price_rows = {
        key: _price_rows_for_ticker(supabase, factor_ticker, cutoff=cutoff)
        for key, factor_ticker in FACTOR_TICKERS.items()
    }
    factor_returns = {
        key: _daily_returns(_daily_close_series(rows))
        for key, rows in factor_price_rows.items()
    }

    processed = 0
    skipped = 0
    failed: list[dict[str, str]] = []

    for ticker in tickers:
        snapshot = _latest_snapshot_for_ticker(supabase, ticker)
        if snapshot is None:
            skipped += 1
            continue
        if _macro_refresh_is_fresh(snapshot, now=computed_at):
            skipped += 1
            continue

        ticker_returns = _daily_returns(
            _daily_close_series(
                _price_rows_for_ticker(supabase, ticker, cutoff=cutoff)
            )
        )
        macro_payload = _build_regression_payload(
            ticker_returns,
            factor_returns,
            computed_at=computed_at,
        )
        if macro_payload is None:
            skipped += 1
            continue

        try:
            dimension_inputs, dimension_last_refreshed = _merge_macro_inputs(
                snapshot,
                macro_payload=macro_payload,
                computed_at=computed_at,
            )
            (
                supabase.table("ticker_risk_snapshots")
                .update(
                    {
                        "dimension_inputs": dimension_inputs,
                        "dimension_last_refreshed": dimension_last_refreshed,
                        "updated_at": computed_at.isoformat(),
                    }
                )
                .eq("id", snapshot["id"])
                .execute()
            )
            processed += 1
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})

    return {
        "status": "completed" if not failed else "failed",
        "items_processed": processed,
        "items_skipped": skipped,
        "items_failed": len(failed),
        "metadata": {
            "requested": len(tickers),
            "failed": failed[:25],
        },
    }


def run_from_env() -> dict[str, Any]:
    return run()
