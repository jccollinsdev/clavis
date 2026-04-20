from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from ..models.position import Position, PositionCreate, PositionUpdate
from ..services.supabase import get_supabase
from ..services.polygon import fetch_current_price
from ..services.ticker_cache_service import (
    ensure_ticker_in_universe,
    enrich_positions_with_ticker_cache,
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


@router.post("", response_model=Position)
async def create_holding(
    position: PositionCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()
    from datetime import datetime, timezone

    supported = ensure_ticker_in_universe(supabase, position.ticker)
    if not supported:
        raise HTTPException(
            400, "Ticker could not be validated from market data providers"
        )

    data = {
        **position.model_dump(),
        "ticker": supported["ticker"],
        "user_id": user_id,
        "current_price": None,
        "analysis_started_at": datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("positions").insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create position")
    created = result.data[0]
    background_tasks.add_task(refresh_position_price, created["id"], created["ticker"])
    background_tasks.add_task(
        refresh_ticker_snapshot,
        supabase,
        ticker=created["ticker"],
        job_type="manual_refresh",
        requested_by_user_id=user_id,
    )
    return created


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
    return result.data[0]


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
