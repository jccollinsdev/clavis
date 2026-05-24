from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from ..services.supabase import get_supabase
from ..services.ticker_cache_service import (
    get_latest_refresh_job,
    get_ticker_detail_bundle,
    refresh_ticker_snapshot,
    search_supported_tickers,
)

logger = logging.getLogger(__name__)

_STALE_SNAPSHOT_THRESHOLD_HOURS = 6

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


def _user_subscription_tier(supabase, user_id: str) -> str:
    result = (
        supabase.table("user_preferences")
        .select("subscription_tier")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return "free"
    return (result.data[0].get("subscription_tier") or "free").lower()


def _require_pro_or_admin(supabase, user_id: str) -> str:
    tier = _user_subscription_tier(supabase, user_id)
    if tier not in {"pro", "admin"}:
        raise HTTPException(403, "Manual refresh is available to Pro users only")
    return tier


@router.get("/search")
async def search_tickers(
    q: str | None = Query(default=None, min_length=0, max_length=50),
    limit: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()
    results = search_supported_tickers(supabase, q, limit=limit, user_id=user_id)
    return {"results": results, "message": "ok"}


def _snapshot_is_stale(result: dict) -> bool:
    """Return True when the news cache has grown meaningfully since the snapshot was scored."""
    freshness = result.get("freshness") or {}
    analysis_as_of_str = freshness.get("analysis_as_of")
    last_news_at_str = freshness.get("last_news_refresh_at")
    if not analysis_as_of_str or not last_news_at_str:
        return False
    try:
        analysis_dt = datetime.fromisoformat(
            str(analysis_as_of_str).replace("Z", "+00:00")
        )
        news_dt = datetime.fromisoformat(
            str(last_news_at_str).replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return False
    return news_dt - analysis_dt > timedelta(hours=_STALE_SNAPSHOT_THRESHOLD_HOURS)


def _safe_refresh_snapshot(supabase, ticker: str) -> None:
    try:
        refresh_ticker_snapshot(
            supabase,
            ticker=ticker,
            job_type="daily",
        )
        logger.info("Background snapshot refresh queued for %s", ticker)
    except Exception:
        logger.warning("Background snapshot refresh failed for %s", ticker, exc_info=True)


@router.get("/{ticker}")
async def get_ticker_detail(
    ticker: str,
    background_tasks: BackgroundTasks,
    position_id: str | None = Query(default=None),
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()
    try:
        result = get_ticker_detail_bundle(
            supabase,
            user_id,
            ticker,
            position_id=position_id,
        )
        if _snapshot_is_stale(result):
            logger.info(
                "Ticker %s snapshot is stale (news newer than analysis_as_of by >%dh) — scheduling refresh",
                ticker,
                _STALE_SNAPSHOT_THRESHOLD_HOURS,
            )
            background_tasks.add_task(_safe_refresh_snapshot, supabase, ticker)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Failed to load ticker detail: {exc}")


@router.post("/{ticker}/refresh")
async def refresh_ticker(ticker: str, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    _require_pro_or_admin(supabase, user_id)

    try:
        job = refresh_ticker_snapshot(
            supabase,
            ticker=ticker,
            job_type="manual_refresh",
            requested_by_user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Failed to refresh ticker: {exc}")

    return {
        "job_id": job.get("id"),
        "ticker": ticker.upper(),
        "status": job.get("status"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "error_message": job.get("error_message"),
    }


@router.get("/{ticker}/refresh-status")
async def get_refresh_status(ticker: str, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    job = get_latest_refresh_job(supabase, ticker)
    return {
        "ticker": ticker.upper(),
        "status": job.get("status") if job else "idle",
        "started_at": job.get("started_at") if job else None,
        "completed_at": job.get("completed_at") if job else None,
        "error_message": job.get("error_message") if job else None,
    }


@router.get("/{ticker}/score-history")
async def get_score_history(
    ticker: str,
    days: int = Query(default=90, ge=2, le=365),
    user_id: str = Depends(get_user_id),
):
    """Ordered composite + per-dimension score history from ticker_risk_snapshots.

    Returns points sorted ascending by date. When <2 points exist, the iOS
    `ScoreHistoryChart` renders the "New" indicator per CLAVIX_TRUTH §8.
    """
    supabase = get_supabase()
    normalized = ticker.upper()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()

    rows = (
        supabase.table("ticker_risk_snapshots")
        .select(
            "snapshot_date,composite_score,safety_score,grade,"
            "financial_health,news_sentiment_dim,macro_exposure_dim,"
            "sector_exposure,volatility,methodology_version"
        )
        .eq("ticker", normalized)
        .gte("snapshot_date", cutoff)
        .order("snapshot_date", desc=False)
        .execute()
        .data
        or []
    )

    points = []
    for row in rows:
        composite = row.get("composite_score")
        if composite is None:
            composite = row.get("safety_score")
        if composite is None:
            continue
        points.append({
            "date": row.get("snapshot_date"),
            "composite": composite,
            "grade": row.get("grade"),
            "financial_health": row.get("financial_health"),
            "news_sentiment": row.get("news_sentiment_dim"),
            "macro_exposure": row.get("macro_exposure_dim"),
            "sector_exposure": row.get("sector_exposure"),
            "volatility": row.get("volatility"),
            "methodology_version": row.get("methodology_version"),
        })

    return {
        "ticker": normalized,
        "points": points,
        "history_count": len(points),
        "days_requested": days,
    }
