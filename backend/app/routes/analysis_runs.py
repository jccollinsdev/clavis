from fastapi import APIRouter, Request, HTTPException, Depends

from ..services.supabase import get_supabase

router = APIRouter()


def _enrich_run(run: dict, digest: list[dict] | None = None) -> dict:
    digest = digest or []
    run["digest_id"] = digest[0]["id"] if digest else None
    run["overall_grade"] = (
        digest[0].get("overall_grade") if digest else run.get("overall_portfolio_grade")
    )
    run["generated_at"] = digest[0].get("generated_at") if digest else None
    if run.get("current_stage") == "completed" and run.get("status") in {
        None,
        "queued",
        "running",
    }:
        run["status"] = "completed"
    if run.get("current_stage") == "failed" and run.get("status") in {
        None,
        "queued",
        "running",
    }:
        run["status"] = "failed"
    run["progress"] = _run_progress(run.get("current_stage"), run.get("status"))
    run["digest_ready"] = bool(digest) or run.get("status") == "completed"
    run["events_analyzed"] = run.get("events_processed")
    run["error"] = run.get("error_message")
    return run


def _get_latest_completed_run(supabase, user_id: str) -> dict | None:
    result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "completed")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _run_progress(stage: str | None, status: str | None) -> int:
    if status in {"completed", "partial"}:
        return 100
    if status == "failed":
        return 0

    return {
        "queued": 0,
        "starting": 8,
        "refreshing_metadata": 12,
        "fetching_news": 22,
        "classifying_relevance": 35,
        "analyzing_events": 55,
        "scoring_position": 78,
        "refreshing_prices": 88,
        "computing_portfolio_risk": 94,
        "building_digest": 98,
        "sp500_running_batches": 60,
    }.get(stage or "", 10)


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("/latest")
async def get_latest_analysis_run(user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return {
            "analysis_run": None,
            "status": "idle",
            "message": "No analysis run found",
        }

    run = result.data[0]
    if run.get("status") == "failed":
        completed_run = _get_latest_completed_run(supabase, user_id)
        if completed_run:
            digest = (
                supabase.table("digests")
                .select("id, overall_grade, generated_at")
                .eq("analysis_run_id", completed_run["id"])
                .limit(1)
                .execute()
                .data
            )
            return {
                "analysis_run": _enrich_run(completed_run, digest),
                "status": "ok",
                "message": "ok",
            }

    digest = (
        supabase.table("digests")
        .select("id, overall_grade, generated_at")
        .eq("analysis_run_id", run["id"])
        .limit(1)
        .execute()
        .data
    )

    return {
        "analysis_run": _enrich_run(run, digest),
        "status": "ok",
        "message": "ok",
    }


@router.get("/{analysis_run_id}")
async def get_analysis_run(analysis_run_id: str, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("id", analysis_run_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Analysis run not found")

    run = result.data[0]
    digest = (
        supabase.table("digests")
        .select("id, overall_grade, generated_at")
        .eq("analysis_run_id", analysis_run_id)
        .limit(1)
        .execute()
        .data
    )
    return _enrich_run(run, digest)
