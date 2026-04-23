from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from snaptrade_client import SnapTrade

from ..config import get_settings
from .supabase import get_supabase
from .ticker_cache_service import ensure_ticker_in_universe


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_prefs_row(supabase, user_id: str) -> dict[str, Any]:
    existing = (
        supabase.table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return existing[0]
    supabase.table("user_preferences").insert({"user_id": user_id}).execute()
    return {"user_id": user_id}


def _upsert_prefs(supabase, user_id: str, data: dict[str, Any]) -> None:
    existing = (
        supabase.table("user_preferences")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        supabase.table("user_preferences").update(data).eq("user_id", user_id).execute()
    else:
        supabase.table("user_preferences").insert(
            {"user_id": user_id, **data}
        ).execute()


def snaptrade_is_configured() -> bool:
    settings = get_settings()
    return bool(settings.snaptrade_client_id and settings.snaptrade_consumer_key)


def _require_snaptrade_client() -> SnapTrade:
    settings = get_settings()
    if not snaptrade_is_configured():
        raise HTTPException(503, "SnapTrade is not configured on this backend")
    return SnapTrade(
        consumer_key=settings.snaptrade_consumer_key,
        client_id=settings.snaptrade_client_id,
    )


def _snaptrade_user_id(user_id: str) -> str:
    return f"clavis-{user_id}"


def _get_registered_credentials(
    user_id: str, *, create_if_missing: bool = False
) -> tuple[str, str] | None:
    supabase = get_supabase()
    prefs = _get_prefs_row(supabase, user_id)
    snaptrade_user_id = prefs.get("snaptrade_user_id")
    snaptrade_user_secret = prefs.get("snaptrade_user_secret")

    if snaptrade_user_id and snaptrade_user_secret:
        return str(snaptrade_user_id), str(snaptrade_user_secret)

    if not create_if_missing:
        return None

    snaptrade_user_id = _snaptrade_user_id(user_id)
    client = _require_snaptrade_client()
    try:
        response = client.authentication.register_snap_trade_user(
            body={"userId": snaptrade_user_id}
        )
    except Exception as exc:
        raise HTTPException(502, f"Failed to register SnapTrade user: {exc}") from exc

    body = response.body or {}
    snaptrade_user_secret = body.get("userSecret")
    if not snaptrade_user_secret:
        raise HTTPException(502, "SnapTrade did not return a user secret")

    _upsert_prefs(
        supabase,
        user_id,
        {
            "snaptrade_user_id": snaptrade_user_id,
            "snaptrade_user_secret": snaptrade_user_secret,
        },
    )
    return snaptrade_user_id, snaptrade_user_secret


def _list_connections(user_id: str) -> list[dict[str, Any]]:
    credentials = _get_registered_credentials(user_id)
    if not credentials:
        return []

    snaptrade_user_id, snaptrade_user_secret = credentials
    client = _require_snaptrade_client()
    try:
        response = client.connections.list_brokerage_authorizations(
            user_id=snaptrade_user_id,
            user_secret=snaptrade_user_secret,
        )
    except Exception as exc:
        raise HTTPException(
            502, f"Failed to load SnapTrade connections: {exc}"
        ) from exc
    return response.body or []


def _list_accounts(user_id: str) -> list[dict[str, Any]]:
    credentials = _get_registered_credentials(user_id)
    if not credentials:
        return []

    snaptrade_user_id, snaptrade_user_secret = credentials
    client = _require_snaptrade_client()
    try:
        response = client.account_information.list_user_accounts(
            user_id=snaptrade_user_id,
            user_secret=snaptrade_user_secret,
        )
    except Exception as exc:
        raise HTTPException(502, f"Failed to load SnapTrade accounts: {exc}") from exc
    return response.body or []


def _is_connection_disabled(connection: dict[str, Any]) -> bool:
    return bool(connection.get("disabled_date") or connection.get("disabledDate"))


def _mask_account_number(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= 4:
        return text
    return f"••••{text[-4:]}"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _extract_symbol(raw_position: dict[str, Any]) -> str | None:
    symbol = raw_position.get("symbol")
    if isinstance(symbol, dict):
        for key in ("symbol", "ticker", "raw_symbol"):
            value = symbol.get(key)
            if value:
                return str(value).strip().upper()
        return None
    if symbol is None:
        return None
    return str(symbol).strip().upper() or None


def _extract_purchase_price(
    raw_position: dict[str, Any], current_price: float | None
) -> float:
    purchase_price = _to_float(
        raw_position.get("average_purchase_price")
        or raw_position.get("averagePurchasePrice")
        or raw_position.get("average_purchase_price_per_share")
    )
    if purchase_price is not None and purchase_price > 0:
        return purchase_price
    return current_price or 0.0


def _normalize_position(
    supabase,
    raw_position: dict[str, Any],
    *,
    account: dict[str, Any],
) -> dict[str, Any] | None:
    symbol = _extract_symbol(raw_position)
    if not symbol:
        return None

    supported = ensure_ticker_in_universe(supabase, symbol)
    if not supported:
        return None

    shares = _to_float(raw_position.get("units") or raw_position.get("quantity"))
    if shares is None or shares <= 0:
        return None

    current_price = _to_float(
        raw_position.get("price")
        or raw_position.get("current_price")
        or raw_position.get("last_price")
    )
    purchase_price = _extract_purchase_price(raw_position, current_price)

    return {
        "ticker": supported["ticker"],
        "shares": shares,
        "purchase_price": purchase_price,
        "current_price": current_price,
        "archetype": "growth",
        "synced_from_brokerage": True,
        "brokerage_authorization_id": account.get("brokerage_authorization")
        or account.get("brokerageAuthorization"),
        "brokerage_account_id": account.get("id"),
        "brokerage_last_synced_at": _utcnow_iso(),
    }


def _delete_position_related_rows(supabase, user_id: str, position_id: str) -> None:
    supabase.table("analysis_runs").update({"target_position_id": None}).eq(
        "target_position_id", position_id
    ).eq("user_id", user_id).execute()
    supabase.table("event_analyses").delete().eq("position_id", position_id).execute()
    supabase.table("position_analyses").delete().eq(
        "position_id", position_id
    ).execute()
    supabase.table("risk_scores").delete().eq("position_id", position_id).execute()
    supabase.table("positions").delete().eq("id", position_id).eq(
        "user_id", user_id
    ).execute()


def get_brokerage_status(user_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    prefs = _get_prefs_row(supabase, user_id)
    auto_sync_enabled = prefs.get("brokerage_auto_sync_enabled", False)
    payload = {
        "configured": snaptrade_is_configured(),
        "registered": bool(
            prefs.get("snaptrade_user_id") and prefs.get("snaptrade_user_secret")
        ),
        "connected": False,
        "auto_sync_enabled": auto_sync_enabled,
        "sync_mode": "automatic" if auto_sync_enabled else "manual",
        "last_sync_at": prefs.get("snaptrade_last_sync_at"),
        "connections": [],
        "accounts": [],
    }
    if not payload["configured"] or not payload["registered"]:
        return payload

    connections = _list_connections(user_id)
    accounts = _list_accounts(user_id)
    payload["connected"] = any(
        not _is_connection_disabled(item) for item in connections
    )
    payload["connections"] = [
        {
            "id": item.get("id"),
            "institution_name": item.get("institution_name")
            or item.get("institutionName")
            or item.get("brokerage"),
            "broker": item.get("broker"),
            "disabled": _is_connection_disabled(item),
            "disabled_date": item.get("disabled_date") or item.get("disabledDate"),
        }
        for item in connections
    ]
    payload["accounts"] = [
        {
            "id": item.get("id"),
            "brokerage_authorization_id": item.get("brokerage_authorization")
            or item.get("brokerageAuthorization"),
            "institution_name": item.get("institution_name")
            or item.get("institutionName")
            or item.get("brokerage"),
            "name": item.get("name"),
            "number_masked": _mask_account_number(item.get("number")),
            "last_holdings_sync_at": (
                ((item.get("sync_status") or {}).get("holdings") or {}).get(
                    "last_successful_sync"
                )
            ),
            "is_paper": bool(item.get("is_paper") or item.get("isPaper")),
        }
        for item in accounts
    ]
    return payload


def generate_connection_portal_link(
    user_id: str, broker: str | None = None, reconnect: str | None = None
) -> dict[str, Any]:
    snaptrade_user_id, snaptrade_user_secret = _get_registered_credentials(
        user_id, create_if_missing=True
    )
    client = _require_snaptrade_client()
    settings = get_settings()

    kwargs: dict[str, Any] = {
        "user_id": snaptrade_user_id,
        "user_secret": snaptrade_user_secret,
        "custom_redirect": settings.snaptrade_redirect_uri,
        "immediate_redirect": True,
        "connection_type": "read",
        "show_close_button": False,
        "dark_mode": True,
        "connection_portal_version": "v4",
    }
    if broker:
        kwargs["broker"] = broker
    if reconnect:
        kwargs["reconnect"] = reconnect

    try:
        response = client.authentication.login_snap_trade_user(**kwargs)
    except Exception as exc:
        raise HTTPException(502, f"Failed to create SnapTrade link: {exc}") from exc

    body = response.body or {}
    redirect_uri = body.get("redirectURI")
    if not redirect_uri:
        raise HTTPException(502, "SnapTrade did not return a redirect URI")
    return {
        "redirect_uri": redirect_uri,
        "session_id": body.get("sessionId"),
    }


def update_brokerage_settings(user_id: str, auto_sync_enabled: bool) -> dict[str, Any]:
    supabase = get_supabase()
    _upsert_prefs(
        supabase,
        user_id,
        {"brokerage_auto_sync_enabled": auto_sync_enabled},
    )
    return {
        "auto_sync_enabled": auto_sync_enabled,
        "sync_mode": "automatic" if auto_sync_enabled else "manual",
    }


def sync_brokerage_holdings(
    user_id: str, *, refresh_remote: bool = False
) -> dict[str, Any]:
    credentials = _get_registered_credentials(user_id)
    if not credentials:
        raise HTTPException(400, "No SnapTrade user is registered for this account yet")

    snaptrade_user_id, snaptrade_user_secret = credentials
    client = _require_snaptrade_client()
    supabase = get_supabase()
    connections = _list_connections(user_id)
    active_connections = [
        item for item in connections if not _is_connection_disabled(item)
    ]
    if not active_connections:
        raise HTTPException(400, "No active brokerage connection is available to sync")

    if refresh_remote:
        for item in active_connections:
            authorization_id = item.get("id")
            if not authorization_id:
                continue
            try:
                client.connections.refresh_brokerage_authorization(
                    authorization_id=authorization_id,
                    user_id=snaptrade_user_id,
                    user_secret=snaptrade_user_secret,
                )
            except Exception as exc:
                raise HTTPException(
                    502,
                    f"Failed to refresh brokerage connection {authorization_id}: {exc}",
                ) from exc

    accounts = _list_accounts(user_id)
    now_iso = _utcnow_iso()
    normalized_positions: list[dict[str, Any]] = []
    skipped_positions = 0

    for account in accounts:
        account_id = account.get("id")
        if not account_id:
            continue
        try:
            response = client.account_information.get_user_account_positions(
                account_id=account_id,
                user_id=snaptrade_user_id,
                user_secret=snaptrade_user_secret,
            )
        except Exception as exc:
            raise HTTPException(
                502,
                f"Failed to fetch positions for brokerage account {account_id}: {exc}",
            ) from exc

        for raw_position in response.body or []:
            normalized = _normalize_position(supabase, raw_position, account=account)
            if not normalized:
                skipped_positions += 1
                continue
            normalized["brokerage_last_synced_at"] = now_iso
            normalized_positions.append(normalized)

    existing_rows = (
        supabase.table("positions")
        .select("id, ticker, brokerage_account_id")
        .eq("user_id", user_id)
        .eq("synced_from_brokerage", True)
        .execute()
        .data
        or []
    )
    existing_by_key = {
        (str(row.get("brokerage_account_id") or ""), str(row.get("ticker") or "")): row
        for row in existing_rows
    }

    created_count = 0
    updated_count = 0
    seen_keys: set[tuple[str, str]] = set()
    tickers_to_refresh: set[str] = set()

    for item in normalized_positions:
        key = (
            str(item.get("brokerage_account_id") or ""),
            str(item.get("ticker") or ""),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        tickers_to_refresh.add(item["ticker"])
        existing = existing_by_key.get(key)
        if existing:
            supabase.table("positions").update(item).eq("id", existing["id"]).eq(
                "user_id", user_id
            ).execute()
            updated_count += 1
        else:
            supabase.table("positions").insert({"user_id": user_id, **item}).execute()
            created_count += 1

    deleted_count = 0
    for row in existing_rows:
        key = (
            str(row.get("brokerage_account_id") or ""),
            str(row.get("ticker") or ""),
        )
        if key in seen_keys:
            continue
        if not row.get("id"):
            continue
        _delete_position_related_rows(supabase, user_id, row["id"])
        deleted_count += 1

    _upsert_prefs(supabase, user_id, {"snaptrade_last_sync_at": now_iso})

    return {
        "connected_accounts": len(accounts),
        "created_positions": created_count,
        "updated_positions": updated_count,
        "deleted_positions": deleted_count,
        "skipped_positions": skipped_positions,
        "last_sync_at": now_iso,
        "tickers_to_refresh": sorted(tickers_to_refresh),
    }


def disconnect_brokerage(user_id: str) -> dict[str, Any]:
    credentials = _get_registered_credentials(user_id)
    connections_removed = 0

    if credentials:
        snaptrade_user_id, snaptrade_user_secret = credentials
        client = _require_snaptrade_client()
        for item in _list_connections(user_id):
            authorization_id = item.get("id")
            if not authorization_id:
                continue
            try:
                client.connections.remove_brokerage_authorization(
                    authorization_id=authorization_id,
                    user_id=snaptrade_user_id,
                    user_secret=snaptrade_user_secret,
                )
                connections_removed += 1
            except Exception as exc:
                raise HTTPException(
                    502,
                    f"Failed to disconnect brokerage authorization {authorization_id}: {exc}",
                ) from exc

    supabase = get_supabase()
    synced_positions = (
        supabase.table("positions")
        .select("id")
        .eq("user_id", user_id)
        .eq("synced_from_brokerage", True)
        .execute()
        .data
        or []
    )
    deleted_positions = 0
    for row in synced_positions:
        if not row.get("id"):
            continue
        _delete_position_related_rows(supabase, user_id, row["id"])
        deleted_positions += 1

    _upsert_prefs(
        supabase,
        user_id,
        {
            "snaptrade_last_sync_at": None,
            "brokerage_auto_sync_enabled": False,
        },
    )
    return {
        "connections_removed": connections_removed,
        "deleted_positions": deleted_positions,
    }
