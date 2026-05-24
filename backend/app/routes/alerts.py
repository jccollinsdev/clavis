"""Alerts API.

GET /alerts          → envelope { summary, alerts }
POST /alerts/{id}/read       → mark a single alert read
POST /alerts/read-all        → mark every alert read for the user
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from ..services.alert_payloads import enrich_alert_rows
from ..services.supabase import get_supabase

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("")
async def get_alerts(
    user_id: str = Depends(get_user_id),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return an envelope with summary counts plus enriched alert rows.

    Backwards-compatibility note: the original /alerts route returned a bare
    array. iOS continues to accept either an array or this envelope by reading
    `alerts` if present.
    """
    supabase = get_supabase()
    rows: list[dict[str, Any]] = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    enriched = enrich_alert_rows(rows)
    unread = sum(1 for row in rows if row.get("read_at") is None)

    # Per-category counts so filter chips can show "Grade 5" etc.
    category_counts: dict[str, int] = {}
    for row in rows:
        key = row.get("type") or "other"
        category_counts[key] = category_counts.get(key, 0) + 1

    return {
        "summary": {
            "unread_count": unread,
            "total_count": len(rows),
            "category_counts": category_counts,
        },
        "alerts": enriched,
    }


@router.post("/{alert_id}/read")
async def mark_alert_read(
    alert_id: str = Path(..., min_length=1),
    user_id: str = Depends(get_user_id),
):
    supabase = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("alerts")
        .update({"read_at": now_iso})
        .eq("id", alert_id)
        .eq("user_id", user_id)
        .is_("read_at", None)
        .execute()
    )
    if not result.data:
        # Either the alert doesn't belong to this user, doesn't exist, or was
        # already read. Idempotent — return the current state without erroring.
        existing = (
            supabase.table("alerts")
            .select("id,read_at")
            .eq("id", alert_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        )
        if not existing:
            raise HTTPException(404, "Alert not found")
        return {"id": alert_id, "read_at": existing[0].get("read_at")}
    return {"id": alert_id, "read_at": now_iso}


@router.post("/read-all")
async def mark_all_alerts_read(user_id: str = Depends(get_user_id)):
    """Mark every unread alert as read for the current user. Idempotent."""
    supabase = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("alerts")
        .update({"read_at": now_iso})
        .eq("user_id", user_id)
        .is_("read_at", None)
        .execute()
    )
    return {"updated": len(result.data or [])}
