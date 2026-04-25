from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from ..services.snaptrade import delete_snaptrade_user, snaptrade_is_configured
from ..services.supabase import get_supabase

logger = logging.getLogger(__name__)
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
    """
    Permanently delete the calling user's account and all associated data.

    Deletion order matters: child rows with FK constraints referencing
    auth.users must be removed before the auth user is deleted, otherwise
    Postgres raises a FK violation and the whole request fails with 500.

    Tables with FK → auth.users (NO ACTION):
      alerts, analysis_runs, digests, news_items,
      portfolio_risk_snapshots, positions, scheduler_jobs, user_preferences

    Tables without FK (safe to delete in any order):
      watchlists, watchlist_items

    SnapTrade cleanup is best-effort: if the SnapTrade service is not
    configured or the remote call fails we log a warning but continue so
    that a missing integration never blocks account deletion.
    """
    supabase = get_supabase()
    logger.info("account_delete_start user_id=%s", user_id)

    # ── Collect child IDs needed for in-clause deletes ──────────────────────
    positions = _table_rows(supabase, "positions", user_id)
    position_ids = [row["id"] for row in positions if row.get("id")]
    watchlists = _table_rows(supabase, "watchlists", user_id)
    watchlist_ids = [row["id"] for row in watchlists if row.get("id")]

    deleted_counts: dict[str, int] = {}

    def delete_rows(table: str, *, column: str = "user_id", value: str = user_id) -> int:
        result = supabase.table(table).delete().eq(column, value).execute()
        count = len(result.data or [])
        logger.info("account_delete_table table=%s deleted=%d user_id=%s", table, count, user_id)
        return count

    def delete_rows_in(table: str, column: str, values: list[str]) -> int:
        if not values:
            return 0
        result = supabase.table(table).delete().in_(column, values).execute()
        count = len(result.data or [])
        logger.info("account_delete_table table=%s deleted=%d user_id=%s", table, count, user_id)
        return count

    # ── Step 1: Best-effort SnapTrade cleanup ────────────────────────────────
    snaptrade_deleted = False
    if snaptrade_is_configured():
        try:
            result = delete_snaptrade_user(user_id)
            snaptrade_deleted = result.get("deleted", False)
            logger.info("account_delete_snaptrade user_id=%s result=%s", user_id, result)
        except Exception as exc:
            logger.warning(
                "account_delete_snaptrade_skipped user_id=%s reason=%s", user_id, exc
            )
    else:
        logger.info("account_delete_snaptrade_skipped user_id=%s reason=not_configured", user_id)

    # ── Step 2: Children of positions (FK → positions.id) ───────────────────
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

    # ── Step 3: Children of watchlists ──────────────────────────────────────
    if watchlist_ids:
        deleted_counts["watchlist_items"] = delete_rows_in(
            "watchlist_items", "watchlist_id", watchlist_ids
        )

    # ── Step 4: All tables with FK → auth.users (must clear before auth delete)
    deleted_counts["alerts"] = delete_rows("alerts")
    deleted_counts["digests"] = delete_rows("digests")
    deleted_counts["news_items"] = delete_rows("news_items")
    deleted_counts["portfolio_risk_snapshots"] = delete_rows("portfolio_risk_snapshots")
    deleted_counts["analysis_runs"] = delete_rows("analysis_runs")
    deleted_counts["positions"] = delete_rows("positions")
    deleted_counts["scheduler_jobs"] = delete_rows("scheduler_jobs")
    deleted_counts["user_preferences"] = delete_rows("user_preferences")

    # ── Step 5: Tables without FK constraints ────────────────────────────────
    deleted_counts["watchlists"] = delete_rows("watchlists")

    # ── Step 6: Delete Supabase auth user (must be last) ────────────────────
    try:
        supabase.auth.admin.delete_user(user_id)
        logger.info("account_delete_auth_user_ok user_id=%s", user_id)
    except Exception as exc:
        logger.error(
            "account_delete_auth_user_failed user_id=%s error=%s", user_id, exc
        )
        raise HTTPException(
            500,
            "Account data was removed but the auth record could not be deleted. "
            "Please contact support.",
        ) from exc

    logger.info(
        "account_delete_complete user_id=%s counts=%s snaptrade_deleted=%s",
        user_id,
        deleted_counts,
        snaptrade_deleted,
    )

    return {
        "status": "deleted",
        "user_id": user_id,
        "snaptrade_deleted": snaptrade_deleted,
        "deleted_counts": deleted_counts,
    }
