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
from ..services.ticker_cache_service import (
    _build_article_aware_reasoning,
    _dedup_event_analyses,
    _is_generic_fallback_reasoning,
    _get_latest_position_score_for_ids,
    build_position_analysis_from_snapshot,
    build_risk_score_response,
    get_latest_risk_snapshot_map,
    get_metadata_map,
    sanitize_public_analysis_text,
)
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

    analyses_result = (
        supabase.table("position_analyses")
        .select("*")
        .eq("position_id", position_id)
        .order("updated_at", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    analyses = analyses_result.data or []

    metadata = get_metadata_map(supabase, [position["ticker"]]).get(
        position["ticker"], {}
    )
    snapshot = get_latest_risk_snapshot_map(supabase, [position["ticker"]]).get(
        position["ticker"]
    )
    if position.get("current_price") is None:
        position["current_price"] = metadata.get("price")

    news_result = (
        supabase.table("ticker_news_cache")
        .select("*")
        .eq("ticker", position["ticker"])
        .order("published_at", desc=True)
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

    current_analysis = sanitize_public_analysis_text(
        _select_current_analysis(analyses)
        or build_position_analysis_from_snapshot(
            snapshot, position_id=position_id, ticker=position["ticker"]
        )
    )
    latest_position_score = _get_latest_position_score_for_ids(supabase, [position_id])
    score_response = sanitize_public_analysis_text(
        build_risk_score_response(
            snapshot,
            position_id=position_id,
            latest_position_score=latest_position_score,
            coverage_context=current_analysis,
        )
    )

    # Replace generic/fallback reasoning with article-specific text when we have events
    deduped_events = _dedup_event_analyses(event_result.data or [])
    # Cap displayed events to source_count so the count matches the risk rationale
    sc = int((score_response or {}).get("source_count") or 0)
    if sc and len(deduped_events) > sc:
        deduped_events = deduped_events[:sc]
    if deduped_events and score_response:
        existing = score_response.get("reasoning") or ""
        if not existing or _is_generic_fallback_reasoning(existing):
            article = _build_article_aware_reasoning(
                deduped_events, score_response, position["ticker"]
            )
            if article:
                score_response["reasoning"] = article
    recent_news = []
    for row in news_result.data or []:
        recent_news.append(
            {
                "id": row.get("id"),
                "user_id": user_id,
                "ticker": position["ticker"],
                "title": row.get("headline"),
                "summary": row.get("summary"),
                "source": row.get("source"),
                "url": row.get("url"),
                "significance": row.get("sentiment"),
                "published_at": row.get("published_at"),
                "affected_tickers": [position["ticker"]],
                "processed_at": row.get("processed_at"),
            }
        )

    return sanitize_public_analysis_text(
        {
            "position": position,
            "current_score": score_response,
            "current_analysis": current_analysis,
            "methodology": current_analysis.get("methodology")
            if current_analysis
            else None,
            "dimension_breakdown": snapshot.get("dimension_rationale")
            if snapshot
            else None,
            "latest_event_analyses": deduped_events,
            "recent_news": recent_news,
            "recent_alerts": enrich_alert_rows(alerts_result.data),
        }
    )
