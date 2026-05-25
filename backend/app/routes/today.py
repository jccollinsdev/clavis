"""GET /today — single envelope the iOS Today tab consumes.

Composes existing data sources rather than introducing a new generator:
- portfolio summary (value-weighted from positions + ticker_metadata)
- five-axis dimensions (value-weighted from latest per-ticker snapshots)
- sector exposure (weights from positions + ticker_metadata.sector;
  ETF day-change attached when sector_regime_snapshots is populated)
- attention (unread alert summary)
- top movers (positions sorted by abs(score_delta))
- calendar (digest.structured_sections.what_to_watch_today)

This route is intentionally read-only and idempotent. No background work.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from ..services.supabase import get_supabase
from ..services.ticker_cache_service import enrich_positions_with_ticker_cache

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


# Sector ETF map used to attach day-change to portfolio sectors when
# sector_regime_snapshots are populated. Mirrors CLAVIX_TRUTH §6.
SECTOR_ETF_MAP = {
    "technology": "XLK",
    "information technology": "XLK",
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


def _grade_for_score(score: float | None) -> str:
    if score is None:
        return "—"
    if score >= 90: return "AAA"
    if score >= 80: return "AA"
    if score >= 70: return "A"
    if score >= 60: return "BBB"
    if score >= 50: return "BB"
    if score >= 40: return "B"
    if score >= 30: return "CCC"
    if score >= 20: return "CC"
    if score >= 10: return "C"
    return "F"


@router.get("")
async def get_today(user_id: str = Depends(get_user_id)) -> dict[str, Any]:
    supabase = get_supabase()

    # ---- Holdings (enriched with v2 summary including dimensions) -------
    raw_positions = (
        supabase.table("positions")
        .select("*")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    holdings = enrich_positions_with_ticker_cache(raw_positions, supabase)

    # ---- Portfolio totals --------------------------------------------------
    total_value = 0.0
    total_day_change = 0.0
    weighted_score_num = 0.0
    weight_denom = 0.0
    dim_weighted: dict[str, list[tuple[float, float]]] = {
        "financial_health": [],
        "news_sentiment": [],
        "macro_exposure": [],
        "sector_exposure": [],
        "volatility": [],
    }
    sector_value: dict[str, float] = {}

    for position in holdings:
        shared = position.get("shared_analysis") or {}
        price = shared.get("latest_price") or position.get("current_price")
        shares = position.get("shares") or 0
        try:
            value = float(price) * float(shares) if price is not None else 0.0
        except (TypeError, ValueError):
            value = 0.0
        if value <= 0:
            continue
        total_value += value

        day_change_amount = shared.get("day_change_amount")
        if day_change_amount is not None and shares is not None:
            try:
                total_day_change += float(day_change_amount) * float(shares)
            except (TypeError, ValueError):
                pass

        score = shared.get("current_score")
        if score is not None:
            try:
                weighted_score_num += float(score) * value
                weight_denom += value
            except (TypeError, ValueError):
                pass

        dims = shared.get("risk_dimensions") or {}
        for key in dim_weighted:
            dim_score = dims.get(key)
            if dim_score is not None:
                try:
                    dim_weighted[key].append((float(dim_score), value))
                except (TypeError, ValueError):
                    pass

        sector = (shared.get("sector") or "Unclassified")
        sector_value[sector] = sector_value.get(sector, 0.0) + value

    portfolio_score = (
        round(weighted_score_num / weight_denom, 1) if weight_denom > 0 else None
    )
    portfolio_grade = _grade_for_score(portfolio_score)
    day_change_pct = (
        round((total_day_change / total_value) * 100.0, 2)
        if total_value > 0 and total_day_change != 0
        else None
    )

    # ---- Five-axis ---------------------------------------------------------
    def _weighted_avg(rows: list[tuple[float, float]]) -> float | None:
        if not rows:
            return None
        num = sum(score * weight for score, weight in rows)
        denom = sum(weight for _, weight in rows)
        return round(num / denom, 1) if denom > 0 else None

    five_axis = [
        {"code": "FIN", "name": "Financial Health",
         "score": _weighted_avg(dim_weighted["financial_health"]),
         "coverage": len(dim_weighted["financial_health"])},
        {"code": "NEWS", "name": "News Sentiment",
         "score": _weighted_avg(dim_weighted["news_sentiment"]),
         "coverage": len(dim_weighted["news_sentiment"])},
        {"code": "MAC", "name": "Macro Exposure",
         "score": _weighted_avg(dim_weighted["macro_exposure"]),
         "coverage": len(dim_weighted["macro_exposure"])},
        {"code": "SEC", "name": "Sector Exposure",
         "score": _weighted_avg(dim_weighted["sector_exposure"]),
         "coverage": len(dim_weighted["sector_exposure"])},
        {"code": "VOL", "name": "Volatility",
         "score": _weighted_avg(dim_weighted["volatility"]),
         "coverage": len(dim_weighted["volatility"])},
    ]

    # ---- Sector heat (with optional ETF day change) -----------------------
    sector_snapshots = (
        supabase.table("sector_regime_snapshots")
        .select("source_etf,etf_day_change_pct,sector,snapshot_date")
        .order("snapshot_date", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    # Take the most recent row per ETF.
    etf_day_change: dict[str, float] = {}
    seen_etfs: set[str] = set()
    for row in sector_snapshots:
        etf = (row.get("source_etf") or "").upper()
        if etf and etf not in seen_etfs:
            seen_etfs.add(etf)
            change = row.get("etf_day_change_pct")
            if change is not None:
                try:
                    etf_day_change[etf] = float(change)
                except (TypeError, ValueError):
                    pass

    sector_cards = []
    for sector, value in sorted(sector_value.items(), key=lambda kv: -kv[1])[:8]:
        etf = SECTOR_ETF_MAP.get(sector.lower())
        sector_cards.append({
            "sector": sector,
            "etf": etf,
            "portfolio_weight_pct": round((value / total_value) * 100.0, 1) if total_value > 0 else 0,
            "etf_day_change_pct": etf_day_change.get(etf) if etf else None,
        })

    # ---- Attention (alerts) -----------------------------------------------
    alerts_rows = (
        supabase.table("alerts")
        .select("id,type,position_ticker,message,created_at,severity,read_at,destination_type,destination_id,previous_grade,new_grade")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    unread_count = sum(1 for row in alerts_rows if row.get("read_at") is None)

    # ---- Top movers --------------------------------------------------------
    def _abs_delta(p: dict[str, Any]) -> int:
        shared = p.get("shared_analysis") or {}
        delta = shared.get("score_delta") or p.get("score_delta") or 0
        try:
            return abs(int(delta))
        except (TypeError, ValueError):
            return 0

    movers = sorted(holdings, key=_abs_delta, reverse=True)[:5]
    top_movers = []
    for p in movers:
        shared = p.get("shared_analysis") or {}
        top_movers.append({
            "ticker": p.get("ticker"),
            "grade": shared.get("current_grade") or p.get("risk_grade") or "—",
            "score_delta": shared.get("score_delta") or p.get("score_delta"),
            "day_change_pct": shared.get("day_change_pct"),
            "reason": (shared.get("grade_rationale") or "")[:160] or None,
        })

    # ---- Today's digest + calendar ----------------------------------------
    today = datetime.now(timezone.utc).date().isoformat()
    digest_row = (
        supabase.table("digests")
        .select("id,summary,structured_sections,generated_at,overall_grade,overall_score")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    digest = digest_row[0] if digest_row else None
    catalysts = []
    digest_preview = None
    digest_id = None
    if digest:
        digest_id = digest.get("id")
        sections = digest.get("structured_sections") or {}
        header = (sections.get("header") or {}) if isinstance(sections, dict) else {}
        digest_preview = header.get("summary_line") or digest.get("summary")
        wtw = (sections.get("what_to_watch_today") or {}) if isinstance(sections, dict) else {}
        catalysts = wtw.get("catalysts") or []

    portfolio_snapshot_rows = (
        supabase.table("portfolio_risk_snapshots")
        .select("portfolio_value,composite_score,grade,score_delta,previous_score,dimensions,sector_breakdown,as_of_date")
        .eq("user_id", user_id)
        .order("as_of_date", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    portfolio_snapshot = portfolio_snapshot_rows[0] if portfolio_snapshot_rows else None
    if portfolio_snapshot:
        portfolio_score = portfolio_snapshot.get("composite_score") or portfolio_score
        portfolio_grade = portfolio_snapshot.get("grade") or portfolio_grade
        five_axis = portfolio_snapshot.get("dimensions") or five_axis

    return {
        "portfolio": {
            "value": portfolio_snapshot.get("portfolio_value") if portfolio_snapshot else (round(total_value, 2) if total_value > 0 else None),
            "day_change_amount": round(total_day_change, 2) if total_value > 0 else None,
            "day_change_pct": day_change_pct,
            "composite_score": portfolio_score,
            "grade": portfolio_grade,
            "previous_score": portfolio_snapshot.get("previous_score") if portfolio_snapshot else None,
            "score_delta": portfolio_snapshot.get("score_delta") if portfolio_snapshot else None,
            "position_count": len(holdings),
            "generated_at": portfolio_snapshot.get("as_of_date") if portfolio_snapshot else datetime.now(timezone.utc).isoformat(),
        },
        "dimensions": five_axis,
        "sector_exposure": sector_cards,
        "attention": {
            "unread_count": unread_count,
            "total_count": len(alerts_rows),
            "alerts": [
                {
                    "id": a.get("id"),
                    "category": a.get("type"),
                    "severity": a.get("severity"),
                    "ticker": a.get("position_ticker"),
                    "title": a.get("message"),
                    "created_at": a.get("created_at"),
                    "destination": {
                        "type": a.get("destination_type") or "alert_detail",
                        "id": a.get("destination_id"),
                    },
                }
                for a in alerts_rows[:5]
            ],
        },
        "top_movers": top_movers,
        "calendar": catalysts,
        "report": {
            "digest_id": digest_id,
            "preview": digest_preview,
            "status": "ready" if digest_id else "unavailable",
        },
    }
