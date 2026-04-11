from fastapi import APIRouter, Request, Depends
from datetime import datetime, timedelta
from ..services.supabase import get_supabase
from .analysis_runs import _enrich_run

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("")
async def get_digest(user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
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
        return {
            "digest": None,
            "analysis_run": _enrich_run(latest_run, latest_run_digest)
            if latest_run
            else None,
            "message": "No digest generated yet",
        }

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

    return {
        "digest": digest,
        "analysis_run": _enrich_run(digest_run, digest_run_digest)
        if digest_run
        else _enrich_run(latest_run, latest_run_digest)
        if latest_run
        else None,
        "overall_grade": digest.get("overall_grade"),
        "structured_sections": digest.get("structured_sections"),
        "generated_at": digest.get("generated_at"),
        "grade_summary": digest.get("grade_summary"),
        "message": "ok",
    }


@router.get("/history")
async def get_digest_history(limit: int = 7, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    result = (
        supabase.table("digests")
        .select("*")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
