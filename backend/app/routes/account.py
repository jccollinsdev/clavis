from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from ..services.supabase import get_supabase

router = APIRouter(tags=["account"])


def get_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Missing Authorization header")
    return user_id


def _table_rows(
    supabase, table: str, user_id: str, *, column: str = "user_id"
) -> list[dict]:
    response = supabase.table(table).select("*").eq(column, user_id).execute()
    return response.data or []


@router.get("/export")
async def export_account(user_id: str = Depends(get_user_id)):
    supabase = get_supabase()

    positions = _table_rows(supabase, "positions", user_id)
    position_ids = [row["id"] for row in positions if row.get("id")]
    watchlists = _table_rows(supabase, "watchlists", user_id)
    watchlist_ids = [row["id"] for row in watchlists if row.get("id")]

    risk_scores = []
    if position_ids:
        risk_scores = (
            supabase.table("risk_scores")
            .select("*")
            .in_("position_id", position_ids)
            .execute()
            .data
            or []
        )

    watchlist_items = []
    if watchlist_ids:
        watchlist_items = (
            supabase.table("watchlist_items")
            .select("*")
            .in_("watchlist_id", watchlist_ids)
            .execute()
            .data
            or []
        )

    auth_user = None
    auth_response = supabase.auth.admin.get_user_by_id(user_id)
    user = getattr(auth_response, "user", None)
    if user:
        auth_user = {
            "id": str(getattr(user, "id", "")),
            "email": getattr(user, "email", None),
            "created_at": getattr(user, "created_at", None),
            "updated_at": getattr(user, "updated_at", None),
            "app_metadata": getattr(user, "app_metadata", None),
            "user_metadata": getattr(user, "user_metadata", None),
            "identities": getattr(user, "identities", None),
        }

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "auth_user": auth_user,
        "user_preferences": _table_rows(supabase, "user_preferences", user_id),
        "positions": positions,
        "analysis_runs": _table_rows(supabase, "analysis_runs", user_id),
        "risk_scores": risk_scores,
        "news_items": _table_rows(supabase, "news_items", user_id),
        "digests": _table_rows(supabase, "digests", user_id),
        "alerts": _table_rows(supabase, "alerts", user_id),
        "position_analyses": (
            supabase.table("position_analyses")
            .select("*")
            .in_("position_id", position_ids)
            .execute()
            .data
            or []
            if position_ids
            else []
        ),
        "event_analyses": (
            supabase.table("event_analyses")
            .select("*")
            .in_("position_id", position_ids)
            .execute()
            .data
            or []
            if position_ids
            else []
        ),
        "watchlists": watchlists,
        "watchlist_items": watchlist_items,
    }


@router.delete("")
async def delete_account(user_id: str = Depends(get_user_id)):
    supabase = get_supabase()

    positions = _table_rows(supabase, "positions", user_id)
    position_ids = [row["id"] for row in positions if row.get("id")]
    watchlists = _table_rows(supabase, "watchlists", user_id)
    watchlist_ids = [row["id"] for row in watchlists if row.get("id")]

    deleted_counts: dict[str, int] = {}

    def delete_rows(
        table: str, *, column: str = "user_id", value: str = user_id
    ) -> int:
        result = supabase.table(table).delete().eq(column, value).execute()
        return len(result.data or [])

    def delete_rows_in(table: str, column: str, values: list[str]) -> int:
        if not values:
            return 0
        result = supabase.table(table).delete().in_(column, values).execute()
        return len(result.data or [])

    if position_ids:
        deleted_counts["event_analyses"] = delete_rows_in(
            "event_analyses", "position_id", position_ids
        )
        deleted_counts["position_analyses"] = delete_rows_in(
            "position_analyses", "position_id", position_ids
        )
        deleted_counts["risk_scores"] = delete_rows_in(
            "risk_scores", "position_id", position_ids
        )

    if watchlist_ids:
        deleted_counts["watchlist_items"] = delete_rows_in(
            "watchlist_items", "watchlist_id", watchlist_ids
        )

    deleted_counts["alerts"] = delete_rows("alerts")
    deleted_counts["digests"] = delete_rows("digests")
    deleted_counts["news_items"] = delete_rows("news_items")
    deleted_counts["analysis_runs"] = delete_rows("analysis_runs")
    deleted_counts["positions"] = delete_rows("positions")
    deleted_counts["user_preferences"] = delete_rows("user_preferences")
    deleted_counts["watchlists"] = delete_rows("watchlists")

    auth_deleted = False
    try:
        supabase.auth.admin.delete_user(user_id)
        auth_deleted = True
    except Exception as exc:
        raise HTTPException(
            500, f"User data deleted but auth deletion failed: {exc}"
        ) from exc

    return {
        "status": "deleted",
        "user_id": user_id,
        "auth_deleted": auth_deleted,
        "deleted_counts": deleted_counts,
    }
