from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request, HTTPException
import traceback
from pydantic import BaseModel
from ..services.supabase import get_supabase
from ..pipeline.scheduler import enqueue_analysis_run

router = APIRouter()


def require_user_id(request: Request) -> str:
    return request.state.user_id


class TriggerAnalysisRequest(BaseModel):
    position_id: str | None = None


@router.post("")
async def trigger_analysis(
    payload: TriggerAnalysisRequest | None = None,
    user_id: str = Depends(require_user_id),
):
    supabase = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_manual_runs = (
        supabase.table("analysis_runs")
        .select("id, started_at")
        .eq("user_id", user_id)
        .eq("triggered_by", "manual")
        .gte("started_at", cutoff)
        .order("started_at", desc=True)
        .limit(3)
        .execute()
        .data
        or []
    )
    if len(recent_manual_runs) >= 3:
        raise HTTPException(
            429,
            "Manual analysis is limited to 3 requests per 24 hours.",
        )

    try:
        result = await enqueue_analysis_run(
            user_id,
            "manual",
            target_position_id=payload.position_id if payload else None,
        )
        prefs_payload = {
            "user_id": user_id,
            "last_analysis_request_at": datetime.now(timezone.utc).isoformat(),
        }
        existing = (
            supabase.table("user_preferences")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        )
        if existing:
            supabase.table("user_preferences").update(prefs_payload).eq(
                "user_id", user_id
            ).execute()
        else:
            supabase.table("user_preferences").insert(prefs_payload).execute()
        result["progress"] = 0
        result["digest_ready"] = False
        result["events_analyzed"] = 0
        result["error"] = None
        return result
    except Exception as e:
        print(f"Trigger analysis error: {e}")
        traceback.print_exc()
        raise HTTPException(500, "Analysis failed")
