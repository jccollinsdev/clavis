import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks

from ..models.position import (
    HoldingWorkflowResponse,
    Position,
    PositionCreate,
    PositionUpdate,
)
from ..pipeline.scheduler import enqueue_analysis_run
from ..services.supabase import get_supabase
from ..services.polygon import fetch_current_price
from ..services.ticker_cache_service import (
    ensure_ticker_in_universe,
    enrich_positions_with_ticker_cache,
    build_holding_workflow_response,
    refresh_ticker_snapshot,
)

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


def refresh_position_price(position_id: str, ticker: str):
    current_price = fetch_current_price(ticker)
    if current_price is None:
        return
    supabase = get_supabase()
    supabase.table("positions").update({"current_price": current_price}).eq(
        "id", position_id
    ).execute()


@router.get("", response_model=list[Position])
async def list_holdings(
    background_tasks: BackgroundTasks, user_id: str = Depends(get_user_id)
):
    supabase = get_supabase()
    positions = (
        supabase.table("positions").select("*").eq("user_id", user_id).execute().data
        or []
    )

    for pos in positions:
        if pos.get("current_price") is None:
            background_tasks.add_task(refresh_position_price, pos["id"], pos["ticker"])

    return enrich_positions_with_ticker_cache(positions, supabase)


@router.post("", response_model=HoldingWorkflowResponse)
async def create_holding(
    position: PositionCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()

    supported = ensure_ticker_in_universe(supabase, position.ticker)
    if not supported:
        raise HTTPException(
            400, "Ticker is not available in the shared ticker cache yet"
        )

    normalized_ticker = supported["ticker"]
    existing_position = (
        supabase.table("positions")
        .select("*")
        .eq("user_id", user_id)
        .eq("ticker", normalized_ticker)
        .limit(1)
        .execute()
        .data
    )
    if existing_position:
        existing = enrich_positions_with_ticker_cache(existing_position, supabase)[0]
        return build_holding_workflow_response(
            supabase,
            user_id=user_id,
            ticker=normalized_ticker,
            position_id=existing["id"],
            position=existing,
        )

    data = {
        **position.model_dump(),
        "ticker": normalized_ticker,
        "user_id": user_id,
        "current_price": None,
        "analysis_started_at": datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("positions").insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create position")
    created = result.data[0]
    background_tasks.add_task(refresh_position_price, created["id"], created["ticker"])

    try:
        refresh_job = await asyncio.to_thread(
            refresh_ticker_snapshot,
            supabase,
            ticker=created["ticker"],
            job_type="manual_refresh",
            requested_by_user_id=user_id,
        )
    except Exception as exc:
        supabase.table("positions").update({"analysis_started_at": None}).eq(
            "id", created["id"]
        ).execute()
        created["analysis_started_at"] = None
        return build_holding_workflow_response(
            supabase,
            user_id=user_id,
            ticker=created["ticker"],
            position_id=created["id"],
            position=enrich_positions_with_ticker_cache([created], supabase)[0],
            latest_refresh_job={
                "ticker": created["ticker"],
                "status": "failed",
                "error_message": str(exc),
            },
        )

    analysis_run = None
    try:
        analysis_run = await enqueue_analysis_run(
            user_id,
            "manual",
            target_position_id=created["id"],
            target_tickers=[created["ticker"]],
        )
    except Exception as exc:
        supabase.table("positions").update({"analysis_started_at": None}).eq(
            "id", created["id"]
        ).execute()
        created["analysis_started_at"] = None
        return build_holding_workflow_response(
            supabase,
            user_id=user_id,
            ticker=created["ticker"],
            position_id=created["id"],
            position=enrich_positions_with_ticker_cache([created], supabase)[0],
            latest_refresh_job=refresh_job,
            latest_analysis_run={
                "id": None,
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(exc),
            },
        )

    latest_analysis_run = None
    if analysis_run.get("analysis_run_id"):
        latest_analysis_run_result = (
            supabase.table("analysis_runs")
            .select("*")
            .eq("id", analysis_run["analysis_run_id"])
            .limit(1)
            .execute()
            .data
        )
        if latest_analysis_run_result:
            latest_analysis_run = latest_analysis_run_result[0]

    return build_holding_workflow_response(
        supabase,
        user_id=user_id,
        ticker=created["ticker"],
        position_id=created["id"],
        position=enrich_positions_with_ticker_cache([created], supabase)[0],
        latest_analysis_run=latest_analysis_run,
        latest_refresh_job=refresh_job,
    )


@router.get("/{position_id}", response_model=Position)
async def get_holding(position_id: str, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    result = (
        supabase.table("positions")
        .select("*")
        .eq("id", position_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Position not found")
    return enrich_positions_with_ticker_cache(result.data, supabase)[0]


@router.patch("/{position_id}", response_model=Position)
async def update_holding(
    position_id: str, position: PositionUpdate, user_id: str = Depends(get_user_id)
):
    supabase = get_supabase()
    data = {k: v for k, v in position.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, "No fields to update")
    data["updated_at"] = "now()"
    result = (
        supabase.table("positions")
        .update(data)
        .eq("id", position_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Position not found")
    return result.data[0]


@router.delete("/{position_id}")
async def delete_holding(position_id: str, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()

    existing_position = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("id", position_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing_position.data:
        raise HTTPException(404, "Position not found")

    # Preserve analysis run history while detaching it from the position being removed.
    supabase.table("analysis_runs").update({"target_position_id": None}).eq(
        "target_position_id", position_id
    ).eq("user_id", user_id).execute()

    supabase.table("event_analyses").delete().eq("position_id", position_id).execute()
    supabase.table("position_analyses").delete().eq(
        "position_id", position_id
    ).execute()
    supabase.table("risk_scores").delete().eq("position_id", position_id).execute()

    result = (
        supabase.table("positions")
        .delete()
        .eq("id", position_id)
        .eq("user_id", user_id)
        .execute()
    )
    return {"deleted": True}
