from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Request

from ..config import get_settings

COOKIE_NAME = "clavis_admin_session"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 12


def _session_secret() -> str:
    settings = get_settings()
    return settings.admin_session_secret.strip() or settings.supabase_jwt_secret


def _sign(value: str) -> str:
    return hmac.new(
        _session_secret().encode("utf-8"), value.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def create_admin_session_cookie() -> str:
    issued_at = str(int(time.time()))
    nonce = secrets.token_hex(8)
    payload = f"{issued_at}:{nonce}"
    return f"{payload}.{_sign(payload)}"


def verify_admin_session_cookie(cookie_value: str | None) -> bool:
    if not cookie_value or "." not in cookie_value:
        return False

    payload, signature = cookie_value.rsplit(".", 1)
    if not hmac.compare_digest(_sign(payload), signature):
        return False

    try:
        issued_at = int(payload.split(":", 1)[0])
    except (ValueError, IndexError):
        return False

    return (time.time() - issued_at) <= COOKIE_MAX_AGE_SECONDS


def require_admin_session(request: Request) -> str:
    if not verify_admin_session_cookie(request.cookies.get(COOKIE_NAME)):
        raise HTTPException(401, "Admin password required")
    return "admin"
