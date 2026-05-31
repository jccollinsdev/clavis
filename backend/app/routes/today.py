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

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from ..services.digest_selection import current_trading_date
from ..services.route_freshness import latest_job_freshness
from ..services.supabase import get_supabase
from ..services.ticker_cache_service import enrich_positions_with_ticker_cache
from .portfolio import build_sector_exposure

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
    sector_cards = build_sector_exposure(supabase, user_id)[:8]

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
    trading_date = current_trading_date()
    today = trading_date.isoformat()
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

    held_tickers = sorted(
        {
            str(position.get("ticker") or "").upper()
            for position in raw_positions
            if position.get("ticker")
        }
    )
    horizon = (trading_date + timedelta(days=14)).isoformat()
    earnings_rows = []
    if held_tickers:
        earnings_rows = (
            supabase.table("earnings_calendar")
            .select("ticker,report_date,est_eps,est_revenue,time_of_day,fiscal_period,source,fetched_at")
            .in_("ticker", held_tickers)
            .gte("report_date", today)
            .lte("report_date", horizon)
            .order("report_date")
            .limit(12)
            .execute()
            .data
            or []
        )

    calendar_items = [
        {
            "type": "EARN",
            "time": row.get("time_of_day") or "—",
            "title": f"{row.get('ticker')} earnings",
            "ticker": row.get("ticker"),
            "report_date": row.get("report_date"),
            "est_eps": row.get("est_eps"),
            "est_revenue": row.get("est_revenue"),
            "source": row.get("source"),
        }
        for row in earnings_rows
    ]
    for item in catalysts[:6]:
        if isinstance(item, dict):
            calendar_items.append(
                {
                    "type": "DATA",
                    "time": "—",
                    "title": item.get("catalyst") or item.get("title"),
                    "tickers": item.get("impacted_positions") or [],
                    "source": "digest",
                }
            )
        else:
            calendar_items.append(
                {
                    "type": "DATA",
                    "time": "—",
                    "title": str(item),
                    "tickers": [],
                    "source": "digest",
                }
            )

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

    # Use live-computed portfolio_score/grade/five_axis as the primary source.
    # The snapshot can have stale or zero-inflated dimensions (e.g. after a
    # limited-data exclusion change stores 0 for excluded dims). We only read
    # previous_score and score_delta from the snapshot for trend display.
    # If the live computation has no coverage (no holdings with scores), fall
    # back to the snapshot's composite_score as a last resort.
    if portfolio_score is None and portfolio_snapshot:
        snapshot_score = portfolio_snapshot.get("composite_score")
        if snapshot_score is not None:
            try:
                snapshot_score = float(snapshot_score)
                if snapshot_score > 0:
                    portfolio_score = round(snapshot_score, 1)
                    portfolio_grade = _grade_for_score(portfolio_score)
            except (TypeError, ValueError):
                pass

    # Similarly, only use snapshot dimensions if the live five_axis has no
    # coverage at all (all scores None) and the snapshot dimensions look valid
    # (all scores > 0 and on the expected 0-100 scale).
    live_has_dims = any(d.get("score") is not None for d in five_axis)
    if not live_has_dims and portfolio_snapshot:
        snap_dims = portfolio_snapshot.get("dimensions") or []
        if isinstance(snap_dims, list) and all(
            isinstance(d, dict) and (d.get("score") or 0) > 0
            for d in snap_dims
            if d.get("score") is not None
        ):
            five_axis = snap_dims

    # Compute score_delta live from portfolio_score vs the snapshot's previous_score.
    # The snapshot's score_delta was computed against the snapshot's composite_score
    # (which may be wrong due to zero-inflation). The live portfolio_score is correct,
    # so the live delta against the correct previous_score gives an honest trend line.
    previous_score: float | None = None
    score_delta: float | None = None
    if portfolio_snapshot:
        try:
            prev = portfolio_snapshot.get("previous_score")
            if prev is not None:
                previous_score = round(float(prev), 1)
        except (TypeError, ValueError):
            pass
    if portfolio_score is not None and previous_score is not None:
        score_delta = round(portfolio_score - previous_score, 1)

    return {
        "portfolio": {
            "value": round(total_value, 2) if total_value > 0 else (
                portfolio_snapshot.get("portfolio_value") if portfolio_snapshot else None
            ),
            "day_change_amount": round(total_day_change, 2) if total_value > 0 else None,
            "day_change_pct": day_change_pct,
            "composite_score": portfolio_score,
            "grade": portfolio_grade,
            "previous_score": previous_score,
            "score_delta": score_delta,
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
        "calendar": calendar_items,
        "report": {
            "digest_id": digest_id,
            "preview": digest_preview,
            "status": "ready" if digest_id else "unavailable",
        },
        "freshness": latest_job_freshness(
            supabase,
            [
                "daily_portfolio_rollup_per_user",
                "daily_sector_snapshot",
                "daily_earnings_calendar_refresh",
            ],
        ),
    }
