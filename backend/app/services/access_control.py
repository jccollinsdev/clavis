from fastapi import HTTPException, Request

from .supabase import get_supabase


def require_admin_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Missing Authorization header")

    supabase = get_supabase()
    result = (
        supabase.table("user_preferences")
        .select("subscription_tier")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    tier = (
        (result.data[0].get("subscription_tier") if result.data else None) or "free"
    ).lower()
    if tier != "admin":
        raise HTTPException(403, "Admin tier is required")
    return str(user_id)
