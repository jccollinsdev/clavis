from fastapi import APIRouter, Depends
from fastapi import Request
from ..services.alert_payloads import enrich_alert_rows
from ..services.supabase import get_supabase

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("")
async def get_alerts(user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    result = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return enrich_alert_rows(result.data)
