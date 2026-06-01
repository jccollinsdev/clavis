import asyncio
from datetime import datetime, timezone
from typing import Any

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
from ..services.route_freshness import latest_job_freshness

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


async def run_onboarding_seed_user(user_id: str):
    from ..jobs.onboarding_seed_user import run_for_user

    supabase = get_supabase()
    await run_for_user(supabase, user_id)


def _list_holdings_sync(
    supabase,
    *,
    user_id: str,
    envelope: bool,
) -> tuple[Any, list[dict[str, str]]]:
    positions = (
        supabase.table("positions").select("*").eq("user_id", user_id).execute().data
        or []
    )
    missing_price_positions = [
        {"id": pos["id"], "ticker": pos["ticker"]}
        for pos in positions
        if pos.get("current_price") is None
    ]
    enriched = enrich_positions_with_ticker_cache(positions, supabase)
    if not envelope:
        return enriched, missing_price_positions

    portfolio_rows = (
        supabase.table("portfolio_risk_snapshots")
        .select(
            "portfolio_value,composite_score,grade,score_delta,previous_score,dimensions,sector_breakdown,as_of_date"
        )
        .eq("user_id", user_id)
        .order("as_of_date", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return (
        {
            "portfolio": portfolio_rows[0] if portfolio_rows else None,
            "positions": enriched,
            "freshness": latest_job_freshness(
                supabase,
                ["daily_portfolio_rollup_per_user", "daily_composite_recompute_universe"],
            ),
        },
        missing_price_positions,
    )


def _create_holding_sync(
    supabase,
    *,
    user_id: str,
    position: PositionCreate,
) -> dict[str, Any]:
    supported = ensure_ticker_in_universe(supabase, position.ticker)
    is_outside_universe = False
    if not supported:
        if not getattr(position, "allow_outside_universe", False):
            raise HTTPException(
                400,
                f"{position.ticker.upper()} isn't in the Clavix tracked universe yet. "
                "Re-submit with allow_outside_universe=true to add it in degraded mode.",
            )
        is_outside_universe = True
        normalized_ticker = position.ticker.strip().upper()
    else:
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
        response = build_holding_workflow_response(
            supabase,
            user_id=user_id,
            ticker=normalized_ticker,
            position_id=existing["id"],
            position=existing,
        )
        return {"kind": "existing", "response": response}

    payload = position.model_dump(exclude_none=True)
    payload.pop("allow_outside_universe", None)
    data = {
        **payload,
        "ticker": normalized_ticker,
        "user_id": user_id,
        "current_price": None,
        "analysis_started_at": datetime.now(timezone.utc).isoformat(),
        "outside_universe": is_outside_universe,
    }
    result = supabase.table("positions").insert(data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create position")
    return {
        "kind": "created",
        "created": result.data[0],
        "is_outside_universe": is_outside_universe,
    }


def _enrich_single_position_sync(supabase, position: dict[str, Any]) -> dict[str, Any]:
    enriched = enrich_positions_with_ticker_cache([position], supabase)
    return enriched[0] if enriched else position


def _clear_analysis_started_at_sync(supabase, position_id: str) -> None:
    supabase.table("positions").update({"analysis_started_at": None}).eq(
        "id", position_id
    ).execute()


def _get_latest_analysis_run_sync(
    supabase,
    analysis_run_id: str | None,
) -> dict[str, Any] | None:
    if not analysis_run_id:
        return None
    latest_analysis_run_result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("id", analysis_run_id)
        .limit(1)
        .execute()
        .data
    )
    if latest_analysis_run_result:
        return latest_analysis_run_result[0]
    return None


@router.get("")
async def list_holdings(
    background_tasks: BackgroundTasks,
    envelope: bool = False,
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()
    response, missing_price_positions = await asyncio.to_thread(
        _list_holdings_sync,
        supabase,
        user_id=user_id,
        envelope=envelope,
    )
    for pos in missing_price_positions:
        if pos.get("current_price") is None:
            background_tasks.add_task(refresh_position_price, pos["id"], pos["ticker"])
    return response


@router.post("", response_model=HoldingWorkflowResponse)
async def create_holding(
    position: PositionCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()
    creation_result = await asyncio.to_thread(
        _create_holding_sync,
        supabase,
        user_id=user_id,
        position=position,
    )
    if creation_result["kind"] == "existing":
        return creation_result["response"]

    created = creation_result["created"]
    is_outside_universe = creation_result["is_outside_universe"]
    background_tasks.add_task(refresh_position_price, created["id"], created["ticker"])
    background_tasks.add_task(run_onboarding_seed_user, user_id)

    # Outside-universe positions skip the structural refresh (we have neither
    # metadata nor a snapshot row to enrich from). Return immediately with
    # honest limited-data state.
    if is_outside_universe:
        enriched_position = await asyncio.to_thread(
            _enrich_single_position_sync,
            supabase,
            created,
        )
        return await asyncio.to_thread(
            build_holding_workflow_response,
            supabase,
            user_id=user_id,
            ticker=created["ticker"],
            position_id=created["id"],
            position=enriched_position,
            latest_refresh_job=None,
        )

    try:
        refresh_job = await asyncio.to_thread(
            refresh_ticker_snapshot,
            supabase,
            ticker=created["ticker"],
            job_type="manual_refresh",
            requested_by_user_id=user_id,
        )
    except Exception as exc:
        await asyncio.to_thread(_clear_analysis_started_at_sync, supabase, created["id"])
        created["analysis_started_at"] = None
        enriched_position = await asyncio.to_thread(
            _enrich_single_position_sync,
            supabase,
            created,
        )
        return await asyncio.to_thread(
            build_holding_workflow_response,
            supabase,
            user_id=user_id,
            ticker=created["ticker"],
            position_id=created["id"],
            position=enriched_position,
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
        await asyncio.to_thread(_clear_analysis_started_at_sync, supabase, created["id"])
        created["analysis_started_at"] = None
        enriched_position = await asyncio.to_thread(
            _enrich_single_position_sync,
            supabase,
            created,
        )
        return await asyncio.to_thread(
            build_holding_workflow_response,
            supabase,
            user_id=user_id,
            ticker=created["ticker"],
            position_id=created["id"],
            position=enriched_position,
            latest_refresh_job=refresh_job,
            latest_analysis_run={
                "id": None,
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(exc),
            },
        )

    latest_analysis_run = await asyncio.to_thread(
        _get_latest_analysis_run_sync,
        supabase,
        analysis_run.get("analysis_run_id"),
    )
    enriched_position = await asyncio.to_thread(
        _enrich_single_position_sync,
        supabase,
        created,
    )
    return await asyncio.to_thread(
        build_holding_workflow_response,
        supabase,
        user_id=user_id,
        ticker=created["ticker"],
        position_id=created["id"],
        position=enriched_position,
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

    result = (
        supabase.table("positions")
        .delete()
        .eq("id", position_id)
        .eq("user_id", user_id)
        .execute()
    )
    return {"deleted": True}
