from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..services.supabase import get_supabase
from ..services.ticker_cache_service import (
    get_latest_refresh_job,
    get_ticker_detail_bundle,
    refresh_ticker_snapshot,
    search_supported_tickers,
)

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
    results = search_supported_tickers(supabase, q, limit=limit)
    return {"results": results, "message": "ok"}


@router.get("/{ticker}")
async def get_ticker_detail(ticker: str, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    try:
        return get_ticker_detail_bundle(supabase, user_id, ticker)
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
