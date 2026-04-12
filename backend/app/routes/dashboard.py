from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from ..services.supabase import get_supabase
from .analysis_runs import _enrich_run
from .holdings import refresh_position_price

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


def _enrich_positions(
    positions: list[dict], supabase, background_tasks: BackgroundTasks
):
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


def _latest_digest_and_run(supabase, user_id: str):
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)

    latest_run_result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    latest_run = latest_run_result.data[0] if latest_run_result.data else None
    latest_run_digest = None
    if latest_run:
        latest_run_digest = (
            supabase.table("digests")
            .select("id, overall_grade, generated_at")
            .eq("analysis_run_id", latest_run["id"])
            .limit(1)
            .execute()
            .data
        )

    result = (
        supabase.table("digests")
        .select("*")
        .eq("user_id", user_id)
        .gte("generated_at", today.isoformat())
        .lt("generated_at", tomorrow.isoformat())
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None, _enrich_run(latest_run, latest_run_digest) if latest_run else None

    digest = result.data[0]
    digest_run = None
    digest_run_digest = None
    if digest.get("analysis_run_id"):
        digest_run_result = (
            supabase.table("analysis_runs")
            .select("*")
            .eq("id", digest["analysis_run_id"])
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        digest_run = digest_run_result.data[0] if digest_run_result.data else None
        if digest_run:
            digest_run_digest = (
                supabase.table("digests")
                .select("id, overall_grade, generated_at")
                .eq("analysis_run_id", digest_run["id"])
                .limit(1)
                .execute()
                .data
            )

    analysis_run = (
        _enrich_run(digest_run, digest_run_digest)
        if digest_run
        else _enrich_run(latest_run, latest_run_digest)
        if latest_run
        else None
    )
    return digest, analysis_run


def _clean_string_list(values):
    return [
        value for value in (values or []) if isinstance(value, str) and value.strip()
    ]


def _clean_risk_driver(driver: dict) -> dict:
    return {
        **driver,
        "tickers": _clean_string_list(driver.get("tickers")),
        "clusters": _clean_string_list(driver.get("clusters")),
        "issues": _clean_string_list(driver.get("issues")),
    }


@router.get("")
async def get_dashboard(
    response: Response,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"

    supabase = get_supabase()
    positions = (
        supabase.table("positions").select("*").eq("user_id", user_id).execute().data
        or []
    )
    positions = _enrich_positions(positions, supabase, background_tasks)

    alerts = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )

    portfolio_risk_snapshot = (
        supabase.table("portfolio_risk_snapshots")
        .select("*")
        .eq("user_id", user_id)
        .order("as_of_date", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if portfolio_risk_snapshot:
        snapshot = dict(portfolio_risk_snapshot[0])
        snapshot["danger_clusters"] = _clean_string_list(
            snapshot.get("danger_clusters")
        )
        snapshot["top_risk_drivers"] = [
            _clean_risk_driver(driver)
            for driver in (snapshot.get("top_risk_drivers") or [])
            if isinstance(driver, dict)
        ]
    else:
        snapshot = None

    digest, analysis_run = _latest_digest_and_run(supabase, user_id)

    return {
        "digest": digest,
        "analysis_run": analysis_run,
        "positions": positions,
        "alerts": alerts,
        "portfolio_risk_snapshot": snapshot,
        "message": "ok",
    }
