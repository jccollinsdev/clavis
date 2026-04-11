from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from ..services.supabase import get_supabase

router = APIRouter()


class PreferencesUpdate(BaseModel):
    digest_time: str = None
    notifications_enabled: bool = None


class DeviceTokenUpdate(BaseModel):
    apns_token: str


@router.get("")
async def get_preferences(request: Request):
    user_id = request.state.user_id
    supabase = get_supabase()
    result = (
        supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
    )
    if not result.data:
        return {"digest_time": "07:00", "notifications_enabled": False}
    return result.data[0]


@router.patch("")
async def update_preferences(preferences: PreferencesUpdate, request: Request):
    user_id = request.state.user_id
    supabase = get_supabase()

    data = {}
    if preferences.digest_time is not None:
        data["digest_time"] = preferences.digest_time
    if preferences.notifications_enabled is not None:
        data["notifications_enabled"] = preferences.notifications_enabled

    if not data:
        raise HTTPException(400, "No fields to update")

    existing = (
        supabase.table("user_preferences")
        .select("id")
        .eq("user_id", user_id)
        .execute()
        .data
    )

    if existing:
        supabase.table("user_preferences").update(data).eq("user_id", user_id).execute()
    else:
        supabase.table("user_preferences").insert(
            {"user_id": user_id, **data}
        ).execute()

    from ..pipeline.scheduler import reschedule_user_digest

    await reschedule_user_digest(user_id)

    return {"status": "ok"}


@router.post("/device-token")
async def register_device_token(token_update: DeviceTokenUpdate, request: Request):
    user_id = request.state.user_id
    supabase = get_supabase()

    apns_token = token_update.apns_token
    if not apns_token:
        raise HTTPException(400, "apns_token is required")

    existing = (
        supabase.table("user_preferences")
        .select("id")
        .eq("user_id", user_id)
        .execute()
        .data
    )

    if existing:
        supabase.table("user_preferences").update(
            {"apns_token": apns_token, "notifications_enabled": True}
        ).eq("user_id", user_id).execute()
    else:
        supabase.table("user_preferences").insert(
            {
                "user_id": user_id,
                "apns_token": apns_token,
                "notifications_enabled": True,
            }
        ).execute()

    from ..pipeline.scheduler import reschedule_user_digest

    await reschedule_user_digest(user_id)

    return {"status": "registered"}
