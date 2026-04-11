from fastapi import APIRouter, Depends, Request

from ..pipeline.scheduler import get_scheduler_status_for_user

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("/status")
async def get_scheduler_status(user_id: str = Depends(get_user_id)):
    return get_scheduler_status_for_user(user_id)
