from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Request

from ..services.route_freshness import latest_job_freshness
from ..services.supabase import get_supabase


router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


SECTOR_ETF_MAP = {
    "technology": "XLK",
    "information technology": "XLK",
    "semiconductors": "XLK",
    "semiconductor": "XLK",
    "semis": "XLK",
    "health care": "XLV",
    "healthcare": "XLV",
    "financials": "XLF",
    "financial services": "XLF",
    "energy": "XLE",
    "consumer discretionary": "XLY",
    "consumer staples": "XLP",
    "industrials": "XLI",
    "utilities": "XLU",
    "materials": "XLB",
    "real estate": "XLRE",
    "communication services": "XLC",
}


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sector_snapshot_map(supabase) -> dict[str, dict[str, Any]]:
    rows = (
        supabase.table("sector_regime_snapshots")
        .select("source_etf,sector,etf_day_change_pct,day_change_pct,snapshot_date,data_status")
        .order("snapshot_date", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    snapshots: dict[str, dict[str, Any]] = {}
    for row in rows:
        etf = str(row.get("source_etf") or "").upper()
        if etf and etf not in snapshots:
            # Normalise: pipeline historically wrote day_change_pct; new rows write etf_day_change_pct
            if row.get("etf_day_change_pct") is None and row.get("day_change_pct") is not None:
                row["etf_day_change_pct"] = row["day_change_pct"]
            snapshots[etf] = row
    return snapshots


def _load_metadata_map(supabase, tickers: list[str]) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    rows = (
        supabase.table("ticker_metadata")
        .select("ticker,sector,price,previous_close")
        .in_("ticker", tickers)
        .execute()
        .data
        or []
    )
    return {str(row.get("ticker") or "").upper(): row for row in rows}


def build_sector_exposure(supabase, user_id: str) -> list[dict[str, Any]]:
    positions = (
        supabase.table("positions")
        .select("ticker,shares,current_price,purchase_price")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    tickers = sorted({str(row.get("ticker") or "").upper() for row in positions if row.get("ticker")})
    metadata = _load_metadata_map(supabase, tickers)
    snapshots = _sector_snapshot_map(supabase)

    sector_values: dict[str, float] = defaultdict(float)
    sector_positions: dict[str, int] = defaultdict(int)
    total_value = 0.0
    for position in positions:
        ticker = str(position.get("ticker") or "").upper()
        meta = metadata.get(ticker) or {}
        shares = _float(position.get("shares")) or 0.0
        price = (
            _float(position.get("current_price"))
            or _float(meta.get("price"))
            or _float(position.get("purchase_price"))
            or 0.0
        )
        market_value = max(0.0, shares * price)
        if market_value <= 0:
            continue
        sector = str(meta.get("sector") or "Unclassified")
        sector_values[sector] += market_value
        sector_positions[sector] += 1
        total_value += market_value

    exposures = []
    for sector, value in sorted(sector_values.items(), key=lambda item: item[1], reverse=True):
        etf = SECTOR_ETF_MAP.get(sector.lower())
        snapshot = snapshots.get(etf or "")
        weight = value / total_value if total_value > 0 else 0.0
        exposures.append(
            {
                "sector": sector,
                "etf": etf,
                "market_value": round(value, 2),
                "portfolio_weight": round(weight, 6),
                "portfolio_weight_pct": round(weight * 100.0, 2),
                "position_count": sector_positions[sector],
                "etf_day_change_pct": _float((snapshot or {}).get("etf_day_change_pct")),
                "snapshot_date": (snapshot or {}).get("snapshot_date"),
                "data_status": (snapshot or {}).get("data_status"),
            }
        )
    return exposures


@router.get("/sector-exposure")
async def get_sector_exposure(user_id: str = Depends(get_user_id)) -> dict[str, Any]:
    supabase = get_supabase()
    exposures = build_sector_exposure(supabase, user_id)
    return {
        "sector_exposure": exposures,
        "freshness": latest_job_freshness(
            supabase,
            ["daily_portfolio_rollup_per_user", "daily_sector_snapshot"],
        ),
    }
