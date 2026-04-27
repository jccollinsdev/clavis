from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from ..config import get_settings

logger = logging.getLogger(__name__)

COOKIE_NAME = "clavis_admin_session"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 12

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60

_login_attempts: dict[str, list[float]] = defaultdict(list)


def _session_secret() -> str:
    settings = get_settings()
    secret = settings.admin_session_secret.strip()
    if not secret:
        raise ValueError(
            "ADMIN_SESSION_SECRET must be set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret


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


def check_login_rate_limit(ip: str) -> None:
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    _login_attempts[ip] = attempts
    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        logger.warning("admin_login_locked_out ip=%s attempts=%d", ip, len(attempts))
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Try again in {int(LOCKOUT_SECONDS / 60)} minutes.",
        )


def record_login_attempt(ip: str) -> None:
    _login_attempts[ip].append(time.time())


def verify_admin_password(password: str) -> bool:
    settings = get_settings()
    if not settings.admin_password:
        raise HTTPException(status_code=503, detail="Admin password is not configured")
    return secrets.compare_digest(password, settings.admin_password)


def _mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return email
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        masked_local = "**"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


def require_admin_session(request: Request) -> str:
    if not verify_admin_session_cookie(request.cookies.get(COOKIE_NAME)):
        raise HTTPException(401, "Admin password required")
    return "admin"