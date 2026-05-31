from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.pipeline.analysis_utils import score_to_grade
from app.services.supabase import get_supabase
from app.services.ticker_cache_service import get_latest_risk_snapshot_map


DIMENSIONS = (
    ("financial_health", "FIN", "Financial Health"),
    ("news_sentiment_dim", "NEWS", "News Sentiment"),
    ("macro_exposure_dim", "MAC", "Macro Exposure"),
    ("sector_exposure", "SEC", "Sector Exposure"),
    ("volatility", "VOL", "Volatility"),
)


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _weighted_average(rows: list[tuple[float, float]]) -> float | None:
    if not rows:
        return None
    denominator = sum(weight for _score, weight in rows)
    if denominator <= 0:
        return None
    return round(sum(score * weight for score, weight in rows) / denominator, 1)


def _load_positions_by_user(supabase) -> dict[str, list[dict[str, Any]]]:
    rows = (
        supabase.table("positions")
        .select("user_id,ticker,shares,current_price,purchase_price")
        .execute()
        .data
        or []
    )
    by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        user_id = str(row.get("user_id") or "")
        ticker = str(row.get("ticker") or "").upper()
        if user_id and ticker:
            by_user[user_id].append({**row, "ticker": ticker})
    return by_user


def _load_metadata_map(supabase, tickers: list[str]) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    rows = (
        supabase.table("ticker_metadata")
        .select("ticker,price,previous_close,sector")
        .in_("ticker", tickers)
        .execute()
        .data
        or []
    )
    return {str(row.get("ticker") or "").upper(): row for row in rows}


def _previous_portfolio_snapshot(supabase, user_id: str, as_of_date: str) -> dict | None:
    rows = (
        supabase.table("portfolio_risk_snapshots")
        .select("composite_score,portfolio_allocation_risk_score")
        .eq("user_id", user_id)
        .lt("as_of_date", as_of_date)
        .order("as_of_date", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def rollup_user(supabase, user_id: str, positions: list[dict[str, Any]]) -> dict[str, Any]:
    as_of_date = date.today().isoformat()
    tickers = sorted({position["ticker"] for position in positions})
    snapshots = get_latest_risk_snapshot_map(supabase, tickers)
    metadata = _load_metadata_map(supabase, tickers)

    portfolio_value = 0.0
    composite_rows: list[tuple[float, float]] = []
    dimension_rows: dict[str, list[tuple[float, float]]] = {
        column: [] for column, _code, _name in DIMENSIONS
    }
    sector_values: dict[str, float] = defaultdict(float)

    for position in positions:
        ticker = position["ticker"]
        shares = _float(position.get("shares")) or 0.0
        meta = metadata.get(ticker) or {}
        price = (
            _float(position.get("current_price"))
            or _float(meta.get("price"))
            or _float(position.get("purchase_price"))
            or 0.0
        )
        market_value = max(0.0, shares * price)
        if market_value <= 0:
            continue
        portfolio_value += market_value

        snapshot = snapshots.get(ticker) or {}
        # Prefer safety_score: it is the user-facing grade score and correctly
        # excludes limited-data dimensions. composite_score may be 0-inflated
        # when the scorer stores 0 for excluded dimensions.
        composite = _float(snapshot.get("safety_score")) or _float(snapshot.get("composite_score"))
        if composite is not None and composite > 0:
            composite_rows.append((composite, market_value))
        for column, _code, _name in DIMENSIONS:
            score = _float(snapshot.get(column))
            # Skip zero scores: a stored 0 means the dimension was excluded
            # from the composite (limited-data flag), not that it actually
            # scored zero. Treating it as missing is more accurate.
            if score is not None and score > 0:
                dimension_rows[column].append((score, market_value))

        sector = str(meta.get("sector") or "Unclassified")
        sector_values[sector] += market_value

    composite_score = _weighted_average(composite_rows)
    previous = _previous_portfolio_snapshot(supabase, user_id, as_of_date)
    previous_score = None
    if previous:
        previous_score = _float(previous.get("composite_score")) or _float(
            previous.get("portfolio_allocation_risk_score")
        )
    score_delta = (
        round(composite_score - previous_score, 1)
        if composite_score is not None and previous_score is not None
        else None
    )
    dimensions = [
        {
            "code": code,
            "name": name,
            "score": _weighted_average(dimension_rows[column]),
            "coverage": len(dimension_rows[column]),
        }
        for column, code, name in DIMENSIONS
    ]
    sector_breakdown = [
        {
            "sector": sector,
            "market_value": round(value, 2),
            "portfolio_weight_pct": (
                round((value / portfolio_value) * 100.0, 2)
                if portfolio_value > 0
                else 0.0
            ),
        }
        for sector, value in sorted(
            sector_values.items(), key=lambda item: item[1], reverse=True
        )
    ]

    payload = {
        "user_id": user_id,
        "as_of_date": as_of_date,
        "portfolio_value": round(portfolio_value, 2),
        "portfolio_allocation_risk_score": composite_score,
        "composite_score": composite_score,
        "grade": score_to_grade(composite_score) if composite_score is not None else None,
        "previous_score": previous_score,
        "score_delta": score_delta,
        "dimensions": dimensions,
        "sector_breakdown": sector_breakdown,
        "factor_breakdown": {
            "source": "ticker_risk_snapshots",
            "tickers": tickers,
        },
    }
    result = (
        supabase.table("portfolio_risk_snapshots")
        .upsert(payload, on_conflict="user_id,as_of_date")
        .execute()
    )
    return (result.data or [payload])[0]


def run() -> dict:
    supabase = get_supabase()
    positions_by_user = _load_positions_by_user(supabase)
    processed = 0
    failed: list[dict[str, str]] = []
    for user_id, positions in positions_by_user.items():
        try:
            rollup_user(supabase, user_id, positions)
            processed += 1
        except Exception as exc:
            failed.append({"user_id": user_id, "error": str(exc)})
    return {
        "status": "completed" if not failed else "failed",
        "items_processed": processed,
        "items_failed": len(failed),
        "metadata": {"failed": failed[:25]},
    }
