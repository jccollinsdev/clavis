from fastapi import APIRouter, Depends, Request, HTTPException
import traceback
from pydantic import BaseModel
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
    try:
        result = await enqueue_analysis_run(
            user_id,
            "manual",
            target_position_id=payload.position_id if payload else None,
        )
        result["progress"] = 0
        result["digest_ready"] = False
        result["events_analyzed"] = 0
        result["error"] = None
        return result
    except Exception as e:
        print(f"Trigger analysis error: {e}")
        traceback.print_exc()
        raise HTTPException(500, "Analysis failed")
