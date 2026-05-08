from __future__ import annotations
from fastapi import (
    APIRouter,
    Request,
    HTTPException,
    Depends,
    BackgroundTasks,
    Response,
)
from ..services.supabase import get_supabase
from ..services.alert_payloads import enrich_alert_rows
from ..services.ticker_cache_service import get_ticker_detail_bundle
from .holdings import refresh_position_price

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


def _has_substantive_analysis(analysis: dict) -> bool:
    source_count = analysis.get("source_count") or 0
    if source_count > 0:
        return True

    top_news = analysis.get("top_news") or []
    if top_news:
        return True

    top_risks = analysis.get("top_risks") or []
    return any(
        isinstance(item, str)
        and item.strip()
        and item.strip() != "No new material risk catalysts identified."
        for item in top_risks
    )


def _select_current_analysis(analyses: list[dict]) -> dict | None:
    ready_analyses = [
        analysis
        for analysis in analyses
        if analysis.get("status") == "ready"
    ]
    if not ready_analyses:
        return None

    for analysis in ready_analyses:
        if _has_substantive_analysis(analysis):
            return analysis

    return ready_analyses[0]


@router.get("/{position_id}")
async def get_position_detail(
    position_id: str,
    response: Response,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"

    supabase = get_supabase()

    position_result = (
        supabase.table("positions")
        .select("*")
        .eq("id", position_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not position_result.data:
        raise HTTPException(404, "Position not found")

    position = position_result.data[0]
    if position.get("current_price") is None:
        background_tasks.add_task(
            refresh_position_price, position_id, position["ticker"]
        )
    return get_ticker_detail_bundle(
        supabase,
        user_id,
        position["ticker"],
        position_id=position_id,
    )
