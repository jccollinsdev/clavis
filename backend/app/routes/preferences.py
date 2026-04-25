from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ..services.supabase import get_supabase


class PreferencesUpdate(BaseModel):
    digest_time: str | None = None
    notifications_enabled: bool | None = None
    summary_length: str | None = None
    weekday_only: bool | None = None


class AlertPreferencesUpdate(BaseModel):
    alerts_grade_changes: bool | None = None
    alerts_major_events: bool | None = None
    alerts_portfolio_risk: bool | None = None
    alerts_large_price_moves: bool | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None


class DeviceTokenUpdate(BaseModel):
    apns_token: str


class ProfileUpdate(BaseModel):
    name: str | None = None
    birth_year: int | None = None


router = APIRouter()


def _get_or_create_prefs(supabase, user_id: str) -> dict:
    existing = (
        supabase.table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    if existing:
        return existing[0]
    supabase.table("user_preferences").insert({"user_id": user_id}).execute()
    return {"id": None, "user_id": user_id}


@router.get("")
async def get_preferences(request: Request):
    user_id = request.state.user_id
    supabase = get_supabase()
    prefs = _get_or_create_prefs(supabase, user_id)
    safe = {
        "digest_time": prefs.get("digest_time") or "07:00",
        "notifications_enabled": prefs.get("notifications_enabled", False),
        "summary_length": prefs.get("summary_length") or "standard",
        "weekday_only": prefs.get("weekday_only", False),
        "alerts_grade_changes": prefs.get("alerts_grade_changes", True),
        "alerts_major_events": prefs.get("alerts_major_events", True),
        "alerts_portfolio_risk": prefs.get("alerts_portfolio_risk", True),
        "alerts_large_price_moves": prefs.get("alerts_large_price_moves", False),
        "quiet_hours_enabled": prefs.get("quiet_hours_enabled", False),
        "quiet_hours_start": prefs.get("quiet_hours_start") or "22:00",
        "quiet_hours_end": prefs.get("quiet_hours_end") or "07:00",
        "has_completed_onboarding": prefs.get("has_completed_onboarding", False),
        "name": prefs.get("name"),
        "birth_year": prefs.get("birth_year"),
        "subscription_tier": prefs.get("subscription_tier") or "free",
    }
    return safe


@router.patch("")
async def update_preferences(preferences: PreferencesUpdate, request: Request):
    user_id = request.state.user_id
    supabase = get_supabase()

    data = {}
    if preferences.digest_time is not None:
        data["digest_time"] = preferences.digest_time
    if preferences.notifications_enabled is not None:
        data["notifications_enabled"] = preferences.notifications_enabled
    if preferences.summary_length is not None:
        data["summary_length"] = preferences.summary_length
    if preferences.weekday_only is not None:
        data["weekday_only"] = preferences.weekday_only

    existing = (
        supabase.table("user_preferences")
        .select("id")
        .eq("user_id", user_id)
        .execute()
        .data
    )

    if existing:
        if data:
            supabase.table("user_preferences").update(data).eq(
                "user_id", user_id
            ).execute()
    else:
        if data:
            supabase.table("user_preferences").insert(
                {"user_id": user_id, **data}
            ).execute()

    if (
        preferences.digest_time is not None
        or preferences.weekday_only is not None
        or preferences.notifications_enabled is not None
    ):
        from ..pipeline.scheduler import reschedule_user_digest

        await reschedule_user_digest(user_id)

    return {"status": "ok"}


@router.patch("/alerts")
async def update_alert_preferences(
    prefs_update: AlertPreferencesUpdate, request: Request
):
    user_id = request.state.user_id
    supabase = get_supabase()

    data = {}
    if prefs_update.alerts_grade_changes is not None:
        data["alerts_grade_changes"] = prefs_update.alerts_grade_changes
    if prefs_update.alerts_major_events is not None:
        data["alerts_major_events"] = prefs_update.alerts_major_events
    if prefs_update.alerts_portfolio_risk is not None:
        data["alerts_portfolio_risk"] = prefs_update.alerts_portfolio_risk
    if prefs_update.alerts_large_price_moves is not None:
        data["alerts_large_price_moves"] = prefs_update.alerts_large_price_moves
    if prefs_update.quiet_hours_enabled is not None:
        data["quiet_hours_enabled"] = prefs_update.quiet_hours_enabled
    if prefs_update.quiet_hours_start is not None:
        data["quiet_hours_start"] = prefs_update.quiet_hours_start
    if prefs_update.quiet_hours_end is not None:
        data["quiet_hours_end"] = prefs_update.quiet_hours_end

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

    return {"status": "ok"}


@router.post("/acknowledge")
async def acknowledge_onboarding(request: Request):
    user_id = request.state.user_id
    supabase = get_supabase()

    from datetime import datetime, timezone

    data = {
        "has_completed_onboarding": True,
        "onboarding_acknowledged_at": datetime.now(timezone.utc).isoformat(),
    }

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


@router.post("/profile")
async def update_profile(profile: ProfileUpdate, request: Request):
    user_id = request.state.user_id
    supabase = get_supabase()

    data = {}
    if profile.name is not None:
        data["name"] = profile.name
    if profile.birth_year is not None:
        data["birth_year"] = profile.birth_year

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

    return {"status": "ok"}
