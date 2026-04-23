from fastapi import APIRouter, Depends, HTTPException, Request

from ..services.apns import send_push
from ..services.supabase import get_supabase

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.post("")
async def test_push(user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    prefs = (
        supabase.table("user_preferences")
        .select("apns_token")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    apns_token = prefs[0].get("apns_token") if prefs else None
    if not apns_token:
        raise HTTPException(400, "No APNs device token is registered for this user")

    payload = {
        "type": "test_push",
        "title": "Clavis Push Test",
        "body": "This is a real APNs test notification from Clavis.",
        "data": {"user_id": user_id},
    }
    result = await send_push(apns_token, payload, user_id=user_id)
    return {
        "status": "sent" if result.success else "failed",
        "result": result.to_dict(),
    }
