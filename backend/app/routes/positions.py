from fastapi import (
    APIRouter,
    Request,
    HTTPException,
    Depends,
    BackgroundTasks,
    Response,
)
from ..services.supabase import get_supabase
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
        if analysis.get("status") not in {"draft", "queued"}
    ]
    if not ready_analyses:
        return analyses[0] if analyses else None

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

    scores_result = (
        supabase.table("risk_scores")
        .select("*")
        .eq("position_id", position_id)
        .order("calculated_at", desc=True)
        .limit(1)
        .execute()
    )
    analyses_result = (
        supabase.table("position_analyses")
        .select("*")
        .eq("position_id", position_id)
        .order("updated_at", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    analyses = analyses_result.data or []
    current_analysis = _select_current_analysis(analyses)

    news_result = (
        supabase.table("news_items")
        .select("*")
        .eq("user_id", user_id)
        .eq("ticker", position["ticker"])
        .order("processed_at", desc=True)
        .limit(10)
        .execute()
    )
    event_result = (
        supabase.table("event_analyses")
        .select("*")
        .eq("position_id", position_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    alerts_result = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .eq("position_ticker", position["ticker"])
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    current_score = scores_result.data[0] if scores_result.data else None

    if current_score:
        score_response = {
            "id": current_score.get("id"),
            "position_id": current_score.get("position_id"),
            "safety_score": current_score.get(
                "safety_score", current_score.get("total_score")
            ),
            "confidence": current_score.get("confidence"),
            "structural_base_score": current_score.get("structural_base_score"),
            "macro_adjustment": current_score.get("macro_adjustment"),
            "event_adjustment": current_score.get("event_adjustment"),
            "grade": current_score.get("grade"),
            "reasoning": current_score.get("reasoning"),
            "factor_breakdown": current_score.get("factor_breakdown"),
            "mirofish_used": current_score.get("mirofish_used"),
            "calculated_at": current_score.get("calculated_at"),
            "total_score": current_score.get("total_score"),
            "news_sentiment": current_score.get("news_sentiment"),
            "macro_exposure": current_score.get("macro_exposure"),
            "position_sizing": current_score.get("position_sizing"),
            "volatility_trend": current_score.get("volatility_trend"),
        }
    else:
        score_response = None

    return {
        "position": position,
        "current_score": score_response,
        "current_analysis": current_analysis,
        "methodology": current_analysis.get("methodology")
        if current_analysis
        else None,
        "dimension_breakdown": current_score.get("dimension_rationale")
        if current_score
        else None,
        "latest_event_analyses": event_result.data,
        "mirofish_used_this_cycle": current_score.get("mirofish_used")
        if current_score
        else False,
        "recent_news": news_result.data,
        "recent_alerts": alerts_result.data,
    }
