from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..pipeline.scheduler import (
    SP500_BACKFILL_TRIGGER,
    SYSTEM_SP500_USER_ID,
    enqueue_sp500_backfill_run,
    get_scheduler_status_for_user,
    get_sp500_cache_status,
    seed_sp500_universe,
)
from ..services.access_control import require_admin_user_id
from ..services.supabase import get_supabase
from .analysis_runs import _enrich_run

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("/status")
async def get_scheduler_status(user_id: str = Depends(get_user_id)):
    return get_scheduler_status_for_user(user_id)


@router.get("/sp500/status")
async def get_sp500_status(user_id: str = Depends(get_user_id)):
    return get_sp500_cache_status()


@router.post("/sp500/seed")
async def seed_sp500(user_id: str = Depends(require_admin_user_id)):
    return await seed_sp500_universe()


@router.post("/sp500/backfill")
async def backfill_sp500(
    limit: int | None = Query(default=None, ge=1, le=500),
    batch_size: int = Query(default=10, ge=1, le=25),
    user_id: str = Depends(require_admin_user_id),
):
    result = await enqueue_sp500_backfill_run(
        requested_by_user_id=user_id,
        limit=limit,
        job_type="backfill",
        batch_size=batch_size,
    )
    result["progress"] = 0
    result["digest_ready"] = False
    result["events_analyzed"] = 0
    result["error"] = None
    return result


@router.get("/sp500/backfill/{analysis_run_id}")
async def get_sp500_backfill_run(
    analysis_run_id: str, user_id: str = Depends(require_admin_user_id)
):
    supabase = get_supabase()
    result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("id", analysis_run_id)
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .eq("triggered_by", SP500_BACKFILL_TRIGGER)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "S&P backfill run not found")

    return _enrich_run(result.data[0], [])
