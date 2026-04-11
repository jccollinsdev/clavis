from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from ..models.position import Position, PositionCreate, PositionUpdate
from ..services.supabase import get_supabase
from ..services.polygon import fetch_current_price

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
    )

    for pos in positions:
        if pos.get("current_price") is None:
            background_tasks.add_task(refresh_position_price, pos["id"], pos["ticker"])
        scores = (
            supabase.table("risk_scores")
            .select("grade, total_score, calculated_at")
            .eq("position_id", pos["id"])
            .order("calculated_at", desc=True)
            .limit(2)
            .execute()
            .data
        )
        analyses = (
            supabase.table("position_analyses")
            .select(
                "inferred_labels, summary, status, progress_message, source_count, updated_at, created_at"
            )
            .eq("position_id", pos["id"])
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if len(scores) >= 1:
            pos["risk_grade"] = scores[0].get("grade")
            pos["total_score"] = scores[0].get("total_score")
            pos["last_analyzed_at"] = scores[0].get("calculated_at")
        else:
            pos["risk_grade"] = None
            pos["total_score"] = None
            pos["last_analyzed_at"] = None
        pos["previous_grade"] = scores[1].get("grade") if len(scores) >= 2 else None
        pos["inferred_labels"] = (
            analyses[0].get("inferred_labels") if analyses else None
        )
        pos["summary"] = analyses[0].get("summary") if analyses else None

    return positions


@router.post("", response_model=Position)
async def create_holding(
    position: PositionCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()
    from datetime import datetime, timezone

    data = {
        **position.model_dump(),
        "user_id": user_id,
        "current_price": None,
        "analysis_started_at": datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("positions").insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create position")
    created = result.data[0]
    background_tasks.add_task(refresh_position_price, created["id"], created["ticker"])
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
