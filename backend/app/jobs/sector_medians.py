from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any

from app.services.supabase import get_supabase


METRICS = (
    "debt_to_equity",
    "fcf_margin",
    "interest_coverage",
    "current_ratio",
    "pe_ratio",
    "beta",
    "volatility_proxy",
)


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    fraction = index - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def compute_sector_medians(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        sector = str(row.get("sector") or "").strip()
        if not sector:
            continue
        bucket = grouped.setdefault(sector, {metric: [] for metric in METRICS})
        for metric in METRICS:
            value = _float(row.get(metric))
            if value is not None:
                bucket[metric].append(value)

    as_of = date.today().isoformat()
    output: list[dict[str, Any]] = []
    for sector, metrics in grouped.items():
        for metric, values in metrics.items():
            if not values:
                continue
            output.append(
                {
                    "sector": sector,
                    "metric": metric,
                    "median": round(median(values), 6),
                    "p25": round(_percentile(values, 0.25) or 0.0, 6),
                    "p75": round(_percentile(values, 0.75) or 0.0, 6),
                    "n_tickers": len(values),
                    "as_of": as_of,
                }
            )
    return output


def run() -> dict[str, Any]:
    supabase = get_supabase()
    rows = (
        supabase.table("ticker_metadata")
        .select(",".join(("ticker", "sector", *METRICS)))
        .execute()
        .data
        or []
    )
    medians = compute_sector_medians(rows)
    if medians:
        supabase.table("sector_medians").upsert(
            medians,
            on_conflict="sector,metric,as_of",
        ).execute()
    return {
        "status": "completed",
        "items_processed": len(medians),
        "metadata": {"sectors": len({row["sector"] for row in medians}) if medians else 0},
    }


def run_from_env() -> dict[str, Any]:
    return run()
