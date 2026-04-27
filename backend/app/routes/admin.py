from __future__ import annotations

import logging
import secrets as _secrets
import time
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from ..config import get_settings
from ..pipeline.scheduler import (
    SYSTEM_SP500_USER_ID,
    enqueue_sp500_backfill_run,
    get_sp500_cache_status,
    trigger_structural_refresh,
    trigger_user_digest,
)
from ..services.admin_auth import (
    COOKIE_NAME,
    _mask_email,
    check_login_rate_limit,
    create_admin_session_cookie,
    record_login_attempt,
    require_admin_session,
    verify_admin_password,
)
from ..services.supabase import get_supabase
from ..services.ticker_metadata import refresh_all_positions_metadata

logger = logging.getLogger(__name__)
router = APIRouter()


class AdminTargetRequest(BaseModel):
    user_id: str | None = None


class AdminLoginRequest(BaseModel):
    password: str


def _cache_headers() -> dict[str, str]:
    return {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _log_admin_action(request: Request, action: str, target: str = "", result: str = ""):
    ip = _client_ip(request)
    logger.info("admin_action ip=%s action=%s target=%s result=%s", ip, action, target, result)


def _count_rows(supabase, table: str) -> int:
    response = supabase.table(table).select("id", count="exact").limit(1).execute()
    return int(response.count or 0)


def _serialize_rows(rows: list[dict]) -> list[dict]:
    def _encode(v):
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, list):
            return [_encode(i) for i in v]
        if isinstance(v, dict):
            return {k: _encode(val) for k, val in v.items()}
        return v

    return [{k: _encode(v) for k, v in row.items()} for row in rows]


def _serialize_value(v):
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [_serialize_value(i) for i in v]
    if isinstance(v, dict):
        return {k: _serialize_value(val) for k, val in v.items()}
    return v


def _serialize_overview(overview: dict) -> dict:
    result = {}
    for k, v in overview.items():
        if k == "sp500_cache":
            cache = {}
            for ck, cv in v.items():
                if isinstance(cv, list):
                    cache[ck] = _serialize_rows(cv)
                else:
                    cache[ck] = _serialize_value(cv)
            result[k] = cache
        else:
            result[k] = _serialize_value(v)
    return result


def _mask_user_email(email: str | None) -> str | None:
    return _mask_email(email)


def _recent_analysis_runs(supabase, limit: int = 12) -> list[dict]:
    result = (
        supabase.table("analysis_runs")
        .select(
            "id, user_id, status, current_stage, current_stage_message, triggered_by, started_at, completed_at, error_message, positions_processed, events_processed, overall_portfolio_grade"
        )
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    from .analysis_runs import _enrich_run
    return [_enrich_run(dict(row), []) for row in (result.data or [])]


def _recent_users(supabase, limit: int = 12) -> list[dict]:
    rows = (
        supabase.table("user_preferences")
        .select(
            "user_id, subscription_tier, digest_time, notifications_enabled, updated_at"
        )
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    users: list[dict] = []
    for row in rows:
        user_id = row.get("user_id")
        email = None
        created_at = None
        if user_id:
            try:
                auth_response = supabase.auth.admin.get_user_by_id(user_id)
                auth_user = getattr(auth_response, "user", None)
                if auth_user:
                    email = getattr(auth_user, "email", None)
                    created_at = getattr(auth_user, "created_at", None)
            except Exception:
                pass

        users.append(
            {
                **row,
                "email": _mask_user_email(email),
                "created_at": created_at,
            }
        )
    return users


def _failed_analysis_runs(supabase, limit: int = 25) -> list[dict]:
    result = (
        supabase.table("analysis_runs")
        .select(
            "id, user_id, status, current_stage, current_stage_message, triggered_by, started_at, completed_at, error_message, positions_processed, events_processed, overall_portfolio_grade"
        )
        .in_("status", ["failed", "partial"])
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    from .analysis_runs import _enrich_run
    return [_enrich_run(dict(row), []) for row in (result.data or [])]


def _user_detail(supabase, user_id: str) -> dict | None:
    prefs = (
        supabase.table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if not prefs:
        return None
    pref = dict(prefs[0])

    email = None
    created_at = None
    try:
        auth_response = supabase.auth.admin.get_user_by_id(user_id)
        auth_user = getattr(auth_response, "user", None)
        if auth_user:
            email = _mask_user_email(getattr(auth_user, "email", None))
            created_at = getattr(auth_user, "created_at", None)
    except Exception:
        pass

    pref["email"] = email
    pref["created_at"] = created_at
    return pref


def _user_positions(supabase, user_id: str) -> list[dict]:
    rows = (
        supabase.table("positions")
        .select("id, ticker, shares, cost_basis, current_price, archetype, created_at, updated_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    safe = []
    for row in rows:
        safe.append({
            "id": row.get("id"),
            "ticker": row.get("ticker"),
            "shares": row.get("shares"),
            "cost_basis": row.get("cost_basis"),
            "current_price": row.get("current_price"),
            "archetype": row.get("archetype"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        })
    return safe


def _user_watchlist(supabase, user_id: str) -> list[dict]:
    try:
        watchlists = (
            supabase.table("watchlists")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not watchlists:
            return []
        wl_id = watchlists[0]["id"]
        items = (
            supabase.table("watchlist_items")
            .select("ticker, created_at")
            .eq("watchlist_id", wl_id)
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
        return [{"ticker": item["ticker"], "created_at": item.get("created_at")} for item in items]
    except Exception:
        return []


def _user_runs(supabase, user_id: str, limit: int = 15) -> list[dict]:
    result = (
        supabase.table("analysis_runs")
        .select(
            "id, status, current_stage, current_stage_message, triggered_by, started_at, completed_at, error_message, positions_processed, events_processed, overall_portfolio_grade"
        )
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    from .analysis_runs import _enrich_run
    return [_enrich_run(dict(row), []) for row in (result.data or [])]


def _health_checks() -> dict:
    checks = {}
    settings = get_settings()
    supabase_ok = False
    supabase_error = None
    try:
        supabase = get_supabase()
        result = supabase.table("user_preferences").select("user_id").limit(1).execute()
        supabase_ok = bool(result.data is not None)
    except Exception as e:
        supabase_error = str(e)[:200]
    checks["supabase"] = {"ok": supabase_ok, "error": supabase_error}

    from ..pipeline.scheduler import scheduler
    checks["scheduler"] = {
        "running": scheduler.running,
        "job_count": len(scheduler.get_jobs()) if scheduler.running else 0,
    }

    checks["admin_password_set"] = bool(settings.admin_password)
    checks["admin_session_secret_set"] = bool(settings.admin_session_secret.strip())

    return checks


def _build_overview(admin_user_id: str) -> dict:
    supabase = get_supabase()
    preferences = (
        supabase.table("user_preferences")
        .select("user_id, subscription_tier")
        .execute()
        .data
        or []
    )
    tier_counts = Counter(
        (row.get("subscription_tier") or "free").lower() for row in preferences
    )

    failed_count = _count_rows(supabase, "analysis_runs")

    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "admin_user_id": admin_user_id,
        "counts": {
            "users": len(preferences),
            "positions": _count_rows(supabase, "positions"),
            "alerts": _count_rows(supabase, "alerts"),
            "digests": _count_rows(supabase, "digests"),
            "analysis_runs": failed_count,
            "ticker_refresh_jobs": _count_rows(supabase, "ticker_refresh_jobs"),
        },
        "tier_counts": dict(sorted(tier_counts.items())),
        "sp500_cache": get_sp500_cache_status(limit=8),
        "recent_analysis_runs": _serialize_rows(_recent_analysis_runs(supabase)),
        "recent_users": _serialize_rows(_recent_users(supabase)),
    }
    return _serialize_overview(overview)


def _generate_csrf_token() -> str:
    return _secrets.token_hex(16)


def _verify_csrf(request: Request) -> None:
    cookie_token = request.cookies.get("clavis_admin_csrf", "")
    header_token = request.headers.get("x-csrf-token", "")
    if not cookie_token or not header_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")
    if not _secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF token invalid")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_shell(request: Request):
    return HTMLResponse(ADMIN_HTML, headers=_cache_headers())


@router.post("/login")
async def admin_login(payload: AdminLoginRequest, request: Request):
    ip = _client_ip(request)
    check_login_rate_limit(ip)

    if not verify_admin_password(payload.password):
        record_login_attempt(ip)
        logger.warning("admin_login_failed ip=%s", ip)
        _log_admin_action(request, "login_failed", result="invalid_password")
        return JSONResponse({"detail": "Invalid password"}, status_code=401)

    _login_attempts = {}
    logger.info("admin_login_success ip=%s", ip)
    _log_admin_action(request, "login_success")

    csrf_token = _generate_csrf_token()
    response = JSONResponse({"status": "ok"}, headers=_cache_headers())
    response.set_cookie(
        COOKIE_NAME,
        create_admin_session_cookie(),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )
    response.set_cookie(
        "clavis_admin_csrf",
        csrf_token,
        httponly=False,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 12,
        path="/admin",
    )
    return response


@router.post("/logout")
async def admin_logout():
    response = JSONResponse({"status": "ok"}, headers=_cache_headers())
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@router.get("/api/overview")
async def api_overview(user_id: str = Depends(require_admin_session)):
    return JSONResponse(_build_overview(user_id), headers=_cache_headers())


@router.get("/api/users")
async def api_users(user_id: str = Depends(require_admin_session)):
    supabase = get_supabase()
    return JSONResponse(
        {"users": _serialize_rows(_recent_users(supabase, limit=50))},
        headers=_cache_headers(),
    )


@router.get("/api/users/{target_user_id}")
async def api_user_detail(
    target_user_id: str,
    user_id: str = Depends(require_admin_session),
):
    supabase = get_supabase()
    detail = _user_detail(supabase, target_user_id)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse({"user": _serialize_rows([detail])[0]}, headers=_cache_headers())


@router.get("/api/users/{target_user_id}/positions")
async def api_user_positions(
    target_user_id: str,
    user_id: str = Depends(require_admin_session),
):
    supabase = get_supabase()
    return JSONResponse(
        {"positions": _serialize_rows(_user_positions(supabase, target_user_id))},
        headers=_cache_headers(),
    )


@router.get("/api/users/{target_user_id}/watchlist")
async def api_user_watchlist(
    target_user_id: str,
    user_id: str = Depends(require_admin_session),
):
    supabase = get_supabase()
    return JSONResponse(
        {"watchlist": _serialize_rows(_user_watchlist(supabase, target_user_id))},
        headers=_cache_headers(),
    )


@router.get("/api/users/{target_user_id}/runs")
async def api_user_runs(
    target_user_id: str,
    limit: int = Query(default=15, ge=1, le=50),
    user_id: str = Depends(require_admin_session),
):
    supabase = get_supabase()
    return JSONResponse(
        {"runs": _serialize_rows(_user_runs(supabase, target_user_id, limit=limit))},
        headers=_cache_headers(),
    )


@router.get("/api/runs")
async def api_runs(user_id: str = Depends(require_admin_session)):
    supabase = get_supabase()
    return JSONResponse(
        {"runs": _serialize_rows(_recent_analysis_runs(supabase, limit=50))},
        headers=_cache_headers(),
    )


@router.get("/api/runs/failed")
async def api_failed_runs(
    limit: int = Query(default=25, ge=1, le=100),
    user_id: str = Depends(require_admin_session),
):
    supabase = get_supabase()
    return JSONResponse(
        {"runs": _serialize_rows(_failed_analysis_runs(supabase, limit=limit))},
        headers=_cache_headers(),
    )


@router.get("/api/health")
async def api_health(user_id: str = Depends(require_admin_session)):
    return JSONResponse(_health_checks(), headers=_cache_headers())


@router.post("/api/actions/sp500/seed")
async def api_seed_sp500(
    request: Request,
    user_id: str = Depends(require_admin_session),
):
    _verify_csrf(request)
    _log_admin_action(request, "sp500_seed")
    return JSONResponse(await trigger_seed_sp500())


async def trigger_seed_sp500() -> dict:
    from ..pipeline.scheduler import seed_sp500_universe

    return await seed_sp500_universe()


@router.post("/api/actions/sp500/backfill")
async def api_backfill_sp500(
    request: Request,
    limit: int | None = Query(default=None, ge=1, le=500),
    batch_size: int = Query(default=10, ge=1, le=25),
    user_id: str = Depends(require_admin_session),
):
    _verify_csrf(request)
    _log_admin_action(request, "sp500_backfill", target=f"limit={limit}")
    return JSONResponse(
        await enqueue_sp500_backfill_run(
            requested_by_user_id=SYSTEM_SP500_USER_ID,
            limit=limit,
            job_type="backfill",
            batch_size=batch_size,
        )
    )


@router.post("/api/actions/structural-refresh")
async def api_structural_refresh(
    request: Request,
    payload: AdminTargetRequest | None = Body(default=None),
    user_id: str = Depends(require_admin_session),
):
    _verify_csrf(request)
    payload = payload or AdminTargetRequest()
    target_user_id = payload.user_id or SYSTEM_SP500_USER_ID
    _log_admin_action(request, "structural_refresh", target=target_user_id)
    return JSONResponse(await trigger_structural_refresh(target_user_id))


@router.post("/api/actions/metadata-refresh")
async def api_metadata_refresh(
    request: Request,
    payload: AdminTargetRequest | None = Body(default=None),
    user_id: str = Depends(require_admin_session),
):
    _verify_csrf(request)
    payload = payload or AdminTargetRequest()
    target_user_id = payload.user_id or SYSTEM_SP500_USER_ID
    _log_admin_action(request, "metadata_refresh", target=target_user_id)
    updated = refresh_all_positions_metadata(target_user_id)
    return JSONResponse({"status": "ok", "user_id": target_user_id, "updated": updated})


@router.post("/api/actions/digest")
async def api_trigger_digest(
    request: Request,
    payload: AdminTargetRequest | None = Body(default=None),
    user_id: str = Depends(require_admin_session),
):
    _verify_csrf(request)
    payload = payload or AdminTargetRequest()
    target_user_id = payload.user_id or SYSTEM_SP500_USER_ID
    _log_admin_action(request, "digest_trigger", target=target_user_id)
    run = await trigger_user_digest(target_user_id)
    return JSONResponse({"status": "queued", "user_id": target_user_id, "run": run})


ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Clavis Admin</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #071016;
      --panel: rgba(8, 18, 25, 0.84);
      --panel-strong: #0d1720;
      --line: rgba(148, 163, 184, 0.18);
      --text: #e5eef7;
      --muted: #8da2b8;
      --accent: #72f1b8;
      --accent-2: #7cc7ff;
      --warn: #ffcc66;
      --danger: #ff7a8a;
      --success: #5ce0a0;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.45);
    }
    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(114, 241, 184, 0.14), transparent 28%),
        radial-gradient(circle at top right, rgba(124, 199, 255, 0.10), transparent 24%),
        linear-gradient(180deg, #04090d 0%, var(--bg) 100%);
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.12), transparent 75%);
    }
    .shell {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.35fr 0.85fr;
      gap: 16px;
      margin-bottom: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }
    .brand, .login, .card, .table, .section { animation: rise 0.55s ease both; }
    @keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .brand {
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 220px;
      background:
        linear-gradient(135deg, rgba(114,241,184,0.10), transparent 38%),
        linear-gradient(220deg, rgba(124,199,255,0.12), transparent 32%),
        var(--panel);
    }
    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 11px;
      color: var(--muted);
    }
    h1 {
      margin: 10px 0 12px;
      font-size: clamp(34px, 5vw, 56px);
      line-height: 0.96;
      letter-spacing: -0.05em;
    }
    .lede {
      max-width: 60ch;
      color: #c8d5e4;
      font-size: 15px;
      line-height: 1.6;
    }
    .meta-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 20px;
    }
    .chip {
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 12px;
      background: rgba(255,255,255,0.02);
    }
    .login {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-height: 220px;
      justify-content: center;
    }
    .login label, .field label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    input, select {
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(4, 10, 15, 0.85);
      color: var(--text);
      outline: none;
    }
    input:focus, select:focus { border-color: rgba(114, 241, 184, 0.5); box-shadow: 0 0 0 3px rgba(114, 241, 184, 0.08); }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .button-row { display: flex; flex-wrap: wrap; gap: 10px; }
    button {
      border: 0;
      border-radius: 14px;
      padding: 12px 14px;
      color: #04110c;
      background: var(--accent);
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary { color: var(--text); background: rgba(255,255,255,0.05); border: 1px solid var(--line); }
    button.warn { background: var(--warn); }
    button:hover { filter: brightness(1.03); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
    }
    .card {
      grid-column: span 3;
      padding: 18px;
      min-height: 112px;
    }
    .metric-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
    .metric-value { margin-top: 10px; font-size: 30px; letter-spacing: -0.04em; }
    .metric-sub { margin-top: 8px; color: #c5d3e2; font-size: 13px; line-height: 1.45; }
    .section { margin-top: 16px; padding: 18px; }
    .section-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; }
    .section-title { font-size: 14px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
    .table { overflow: hidden; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; }
    td { font-size: 13px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; }
    .status { display: inline-flex; align-items: center; gap: 8px; padding: 5px 10px; border-radius: 999px; border: 1px solid var(--line); font-size: 12px; }
    .status::before { content: ""; width: 8px; height: 8px; border-radius: 999px; background: var(--accent); }
    .status.warn::before { background: var(--warn); }
    .status.danger::before { background: var(--danger); }
    .status.success::before { background: var(--success); }
    .subtle { color: var(--muted); }
    .log {
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      color: #cdd9e7;
      white-space: pre-wrap;
      font-size: 12px;
      min-height: 54px;
    }
    .hidden { display: none !important; }
    .toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .spacer { flex: 1; }
    .large { font-size: 16px; color: #dce7f2; }
    .tabs { display: flex; gap: 4px; margin-top: 16px; flex-wrap: wrap; }
    .tab-btn {
      padding: 10px 16px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: transparent;
      color: var(--muted);
      font-size: 13px;
      cursor: pointer;
      font-weight: 600;
    }
    .tab-btn.active { background: rgba(114, 241, 184, 0.12); color: var(--accent); border-color: rgba(114, 241, 184, 0.3); }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    .health-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-top: 12px; }
    .health-card { padding: 14px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); }
    .health-card .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }
    .health-card .value { font-size: 18px; margin-top: 6px; }
    .clickable-row { cursor: pointer; }
    .clickable-row:hover { background: rgba(114, 241, 184, 0.04); }
    .error-text { color: var(--danger); font-size: 12px; margin-top: 4px; max-width: 400px; word-break: break-word; }
    @media (max-width: 1080px) {
      .hero { grid-template-columns: 1fr; }
      .card { grid-column: span 6; }
    }
    @media (max-width: 720px) {
      .shell { padding: 14px; }
      .card { grid-column: span 12; }
      .row { grid-template-columns: 1fr; }
      table, thead, tbody, th, td, tr { display: block; }
      thead { display: none; }
      td { border-bottom: 0; padding-top: 0; }
      tr { border-bottom: 1px solid var(--line); padding: 10px 0; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div class="brand panel">
        <div>
          <div class="eyebrow">Protected operator console</div>
          <h1>Clavis Admin</h1>
          <div class="lede">Operational control for backend health, user visibility, and safe manual refreshes. Sign in with the admin password to unlock the data panels and actions.</div>
        </div>
        <div class="meta-row">
          <div class="chip">VPS-hosted</div>
          <div class="chip">Cloudflare Tunnel</div>
          <div class="chip">Auth required</div>
          <div class="chip">No-store</div>
          <div class="chip">CSRF protected</div>
          <div class="chip">Rate limited</div>
        </div>
      </div>
      <div class="login panel">
        <div class="eyebrow">Access</div>
        <label for="password">Admin password</label>
        <input id="password" type="password" placeholder="Enter password" autocomplete="current-password" spellcheck="false" />
        <div class="button-row">
          <button id="save-password">Unlock dashboard</button>
          <button class="secondary" id="clear-password">Clear password</button>
        </div>
        <div class="subtle" id="login-error"></div>
        <div class="subtle">Session cookie + CSRF token. 5 attempts then 15-min lockout per IP.</div>
      </div>
    </div>

    <div id="app" class="hidden">
      <div class="grid" id="stats"></div>

      <div class="tabs">
        <button class="tab-btn active" data-tab="overview">Overview</button>
        <button class="tab-btn" data-tab="users">Users</button>
        <button class="tab-btn" data-tab="failures">Failures</button>
        <button class="tab-btn" data-tab="health">Health</button>
        <button class="tab-btn" data-tab="actions">Actions</button>
      </div>

      <div id="tab-overview" class="tab-content active">
        <div class="section panel table">
          <div class="section-head">
            <div>
              <div class="section-title">Recent runs</div>
            </div>
            <div class="subtle" id="runs-summary"></div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>User</th>
                <th>Status</th>
                <th>Stage</th>
                <th>Progress</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody id="runs-table"></tbody>
          </table>
        </div>

        <div class="section panel table">
          <div class="section-head">
            <div class="section-title">Scheduler and cache</div>
            <div class="subtle" id="scheduler-summary"></div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Surface</th>
                <th>State</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody id="system-table"></tbody>
          </table>
        </div>
      </div>

      <div id="tab-users" class="tab-content">
        <div class="section panel table">
          <div class="section-head">
            <div class="section-title">Users</div>
            <div class="subtle" id="users-summary"></div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Email</th>
                <th>Tier</th>
                <th>Digest</th>
                <th>Notifications</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody id="users-table"></tbody>
          </table>
        </div>

        <div id="user-detail" class="section panel hidden">
          <div class="section-head">
            <div>
              <div class="section-title">User detail</div>
              <div class="large" id="user-detail-title"></div>
            </div>
            <button class="secondary" id="close-user-detail">Back to list</button>
          </div>
          <div id="user-detail-info" class="row" style="margin-bottom:12px;"></div>
          <div class="section-title" style="margin:12px 0 8px;">Positions</div>
          <table>
            <thead><tr><th>Ticker</th><th>Shares</th><th>Cost basis</th><th>Current</th><th>Archetype</th></tr></thead>
            <tbody id="user-positions-table"></tbody>
          </table>
          <div class="section-title" style="margin:12px 0 8px;">Watchlist</div>
          <div id="user-watchlist" class="subtle">Loading...</div>
          <div class="section-title" style="margin:12px 0 8px;">Runs</div>
          <table>
            <thead><tr><th>Status</th><th>Stage</th><th>Started</th><th>Error</th></tr></thead>
            <tbody id="user-runs-table"></tbody>
          </table>
        </div>
      </div>

      <div id="tab-failures" class="tab-content">
        <div class="section panel table">
          <div class="section-head">
            <div class="section-title">Failed runs</div>
            <div class="subtle" id="failures-summary"></div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>User</th>
                <th>Status</th>
                <th>Stage</th>
                <th>Error</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody id="failures-table"></tbody>
          </table>
        </div>
      </div>

      <div id="tab-health" class="tab-content">
        <div class="section panel">
          <div class="section-head">
            <div class="section-title">Health checks</div>
            <div class="subtle" id="health-summary"></div>
          </div>
          <div id="health-grid" class="health-grid"></div>
        </div>
      </div>

      <div id="tab-actions" class="tab-content">
        <div class="section panel">
          <div class="section-head">
            <div>
              <div class="section-title">Control room</div>
              <div class="large">Manual refreshes and backfill actions</div>
            </div>
            <div class="toolbar">
              <button class="secondary" id="reload">Reload</button>
              <button class="secondary" id="logout">Log out</button>
            </div>
          </div>
          <div class="row">
            <div class="field">
              <label for="target-user">Target user</label>
              <select id="target-user"></select>
            </div>
            <div class="field">
              <label for="backfill-limit">Backfill limit</label>
              <input id="backfill-limit" type="number" min="1" max="500" value="25" />
            </div>
          </div>
          <div class="button-row" style="margin-top:12px;">
            <button class="secondary" id="structural-refresh">Structural refresh</button>
            <button class="secondary" id="metadata-refresh">Metadata refresh</button>
            <button class="secondary" id="run-digest">Run digest</button>
            <button class="warn" id="seed-sp500">Seed S&P universe</button>
            <button class="warn" id="run-backfill">Run S&P backfill</button>
          </div>
          <div id="action-log" class="log">Ready.</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let overview = null;

    const app = document.getElementById('app');
    const actionLog = document.getElementById('action-log');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('login-error');

    function escapeHtml(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function setLog(message) {
      actionLog.textContent = message;
    }

    function statusClass(text) {
      const v = String(text || '').toLowerCase();
      if (v.includes('fail') || v.includes('error')) return 'danger';
      if (v.includes('queue') || v.includes('running') || v.includes('partial')) return 'warn';
      if (v.includes('success') || v.includes('completed')) return 'success';
      return '';
    }

    function getCsrfFromCookie() {
      const match = document.cookie.match(/clavis_admin_csrf=([^;]+)/);
      return match ? match[1] : null;
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      });
      if (response.status === 401 || response.status === 403) {
        throw new Error('Authentication failed or admin access is missing');
      }
      const text = await response.text();
      return text ? JSON.parse(text) : {};
    }

    async function postAction(path, body = {}) {
      const csrf = getCsrfFromCookie();
      return api(path, {
        method: 'POST',
        body: JSON.stringify(body),
        headers: csrf ? { 'x-csrf-token': csrf } : {},
      });
    }

    function renderCards(data) {
      const counts = data.counts || {};
      const tiers = data.tier_counts || {};
      const cards = [
        ['Users', counts.users || 0, 'Tier mix: ' + Object.entries(tiers).map(([k,v]) => `${k} ${v}`).join(', ')],
        ['Positions', counts.positions || 0, 'Tracked holdings across user accounts'],
        ['Analysis runs', counts.analysis_runs || 0, 'Latest system and user run history'],
        ['S&P coverage', data.sp500_cache ? `${data.sp500_cache.coverage_count}/${data.sp500_cache.universe_size}` : '0/0', 'Shared ticker cache coverage'],
      ];
      document.getElementById('stats').innerHTML = cards.map(([label, value, sub]) => `
        <div class="card panel">
          <div class="metric-label">${escapeHtml(label)}</div>
          <div class="metric-value">${escapeHtml(value)}</div>
          <div class="metric-sub">${escapeHtml(sub)}</div>
        </div>
      `).join('');
    }

    function renderUsers(users) {
      document.getElementById('users-summary').textContent = `${users.length} loaded`;
      document.getElementById('target-user').innerHTML = users.map((user) => {
        const label = [user.email || user.user_id, user.subscription_tier || 'free'].filter(Boolean).join(' | ');
        return `<option value="${escapeHtml(user.user_id)}">${escapeHtml(label)}</option>`;
      }).join('');
      document.getElementById('users-table').innerHTML = users.map((user) => `
        <tr class="clickable-row" data-user-id="${escapeHtml(user.user_id)}">
          <td><div>${user.email ? escapeHtml(user.email) : '<span class="subtle">no email</span>'}</div><div class="mono subtle">${escapeHtml(user.user_id ? user.user_id.slice(0, 8) + '...' : '')}</div></td>
          <td><span class="status">${escapeHtml(user.subscription_tier || 'free')}</span></td>
          <td>${user.digest_time ? escapeHtml(user.digest_time) : '<span class="subtle">unset</span>'}</td>
          <td>${user.notifications_enabled ? 'on' : 'off'}</td>
          <td class="subtle">${escapeHtml(user.updated_at || user.created_at || '')}</td>
        </tr>
      `).join('');
      document.querySelectorAll('#users-table .clickable-row').forEach(row => {
        row.addEventListener('click', () => loadUserDetail(row.dataset.userId));
      });
    }

    function renderRuns(runs) {
      document.getElementById('runs-summary').textContent = `${runs.length} latest`;
      document.getElementById('runs-table').innerHTML = runs.map((run) => {
        const stage = run.current_stage || 'idle';
        const progress = run.progress != null ? `${run.progress}%` : 'n/a';
        return `
          <tr>
            <td class="mono">${escapeHtml((run.id || '').slice(0, 8))}...</td>
            <td class="mono">${escapeHtml((run.user_id || '').slice(0, 8))}...</td>
            <td><span class="status ${statusClass(run.status)}">${escapeHtml(run.status || 'unknown')}</span></td>
            <td>${escapeHtml(stage)}</td>
            <td>${escapeHtml(progress)}</td>
            <td class="subtle">${escapeHtml(run.started_at || '')}</td>
          </tr>
        `;
      }).join('');
    }

    function renderFailures(runs) {
      document.getElementById('failures-summary').textContent = `${runs.length} failed`;
      document.getElementById('failures-table').innerHTML = runs.map((run) => {
        const errorSnippet = (run.error_message || run.current_stage_message || '').substring(0, 120);
        return `
          <tr>
            <td class="mono">${escapeHtml((run.id || '').slice(0, 8))}</td>
            <td class="mono">${escapeHtml((run.user_id || '').slice(0, 8))}</td>
            <td><span class="status ${statusClass(run.status)}">${escapeHtml(run.status || 'unknown')}</span></td>
            <td>${escapeHtml(run.current_stage || 'unknown')}</td>
            <td><div class="error-text">${escapeHtml(errorSnippet) || 'No error detail'}</div></td>
            <td class="subtle">${escapeHtml(run.started_at || '')}</td>
          </tr>
        `;
      }).join('');
    }

    function fmtTz(obj) {
      if (!obj) return 'N/A';
      if (typeof obj === 'string') return obj;
      return obj.et ? `${obj.et} (ET) / ${obj.utc} (UTC)` : String(obj);
    }

    function renderSystem(data) {
      const scheduler = data.scheduler_status || {};
      const sp500 = data.sp500_cache || {};
      const rows = [
        ['Scheduler', scheduler.runtime_job_present ? 'running' : 'idle', fmtTz(scheduler.runtime_next_run_at_et || scheduler.runtime_next_run_at)],
        ['Digest time (ET)', scheduler.digest_time || 'unset', scheduler.notifications_enabled ? 'notifications enabled' : 'notifications disabled'],
        ['S&P daily job', sp500.daily_job_present ? 'scheduled' : 'missing', fmtTz(sp500.daily_next_run_at)],
        ['Backfill job', sp500.backfill_job_present ? 'scheduled' : 'missing', fmtTz(sp500.backfill_next_run_at)],
        ['Backfill queue', sp500.recent_jobs && sp500.recent_jobs.length ? sp500.recent_jobs[0].status : 'empty', sp500.recent_jobs && sp500.recent_jobs[0] ? `${sp500.recent_jobs[0].ticker || 'n/a'} · ${sp500.recent_jobs[0].job_type || 'job'}` : 'No recent jobs'],
      ];
      document.getElementById('scheduler-summary').textContent = `Generated ${data.generated_at || ''}`;
      document.getElementById('system-table').innerHTML = rows.map(([surface, state, details]) => `
        <tr>
          <td>${escapeHtml(surface)}</td>
          <td><span class="status ${statusClass(state)}">${escapeHtml(state)}</span></td>
          <td class="subtle">${escapeHtml(details)}</td>
        </tr>
      `).join('');
    }

    function renderHealth(checks) {
      const items = [];
      for (const [key, val] of Object.entries(checks)) {
        if (typeof val === 'object' && val !== null) {
          const ok = val.ok !== undefined ? val.ok : val.running !== undefined ? val.running : null;
          const statusLabel = ok === true ? 'OK' : ok === false ? 'FAIL' : 'N/A';
          const statusCls = ok === true ? 'success' : ok === false ? 'danger' : '';
          let detail = '';
          if (val.error) detail = escapeHtml(val.error);
          if (val.job_count !== undefined) detail = `${val.job_count} jobs`;
          items.push(`<div class="health-card"><div class="label">${escapeHtml(key)}</div><div class="value"><span class="status ${statusCls}">${statusLabel}</span></div>${detail ? '<div class="subtle" style="margin-top:6px;font-size:12px;">' + detail + '</div>' : ''}</div>`);
        } else {
          const ok = val === true;
          items.push(`<div class="health-card"><div class="label">${escapeHtml(key)}</div><div class="value"><span class="status ${ok ? 'success' : 'danger'}">${ok ? 'Set' : 'Missing'}</span></div></div>`);
        }
      }
      document.getElementById('health-grid').innerHTML = items.join('');
      document.getElementById('health-summary').textContent = `${Object.keys(checks).length} checks`;
    }

    async function loadUserDetail(userId) {
      try {
        const [detail, positions, watchlist, runs] = await Promise.all([
          api(`/admin/api/users/${userId}`),
          api(`/admin/api/users/${userId}/positions`),
          api(`/admin/api/users/${userId}/watchlist`),
          api(`/admin/api/users/${userId}/runs`),
        ]);
        const u = detail.user || {};
        document.getElementById('user-detail-title').textContent = u.email || u.user_id || userId;
        document.getElementById('user-detail-info').innerHTML = `
          <div><span class="subtle">ID:</span> <span class="mono">${escapeHtml(u.user_id || '')}</span></div>
          <div><span class="subtle">Tier:</span> ${escapeHtml(u.subscription_tier || 'free')}</div>
          <div><span class="subtle">Digest:</span> ${escapeHtml(u.digest_time || 'unset')}</div>
          <div><span class="subtle">Notifications:</span> ${u.notifications_enabled ? 'on' : 'off'}</div>
        `;
        document.getElementById('user-positions-table').innerHTML = (positions.positions || []).map(p => `
          <tr>
            <td><strong>${escapeHtml(p.ticker || '')}</strong></td>
            <td>${escapeHtml(p.shares ?? '')}</td>
            <td>${escapeHtml(p.cost_basis ?? '')}</td>
            <td>${escapeHtml(p.current_price ?? '')}</td>
            <td><span class="status">${escapeHtml(p.archetype || 'n/a')}</span></td>
          </tr>
        `).join('') || '<tr><td colspan="5" class="subtle">No positions</td></tr>';
        document.getElementById('user-watchlist').textContent = (watchlist.watchlist || []).map(w => w.ticker).join(', ') || 'Empty';
        document.getElementById('user-runs-table').innerHTML = (runs.runs || []).slice(0, 10).map(r => `
          <tr>
            <td><span class="status ${statusClass(r.status)}">${escapeHtml(r.status || 'unknown')}</span></td>
            <td>${escapeHtml(r.current_stage || 'idle')}</td>
            <td class="subtle">${escapeHtml(r.started_at || '')}</td>
            <td><div class="error-text">${escapeHtml((r.error_message || '').substring(0, 100))}</div></td>
          </tr>
        `).join('') || '<tr><td colspan="4" class="subtle">No runs</td></tr>';
        document.getElementById('user-detail').classList.remove('hidden');
      } catch (err) {
        setLog('Failed to load user detail: ' + err.message);
      }
    }

    async function loadOverview() {
      try {
        const data = await api('/admin/api/overview');
        overview = data;
        app.classList.remove('hidden');
        renderCards(data);
        renderUsers(data.recent_users || []);
        renderRuns(data.recent_analysis_runs || []);
        renderSystem(data);
        setLog(`Loaded overview at ${data.generated_at}`);
      } catch (error) {
        app.classList.add('hidden');
        setLog(error.message || 'Unable to load dashboard');
      }
    }

    async function loadFailures() {
      try {
        const data = await api('/admin/api/runs/failed');
        renderFailures(data.runs || []);
      } catch (error) {
        setLog('Failed to load failures: ' + error.message);
      }
    }

    async function loadHealth() {
      try {
        const data = await api('/admin/api/health');
        renderHealth(data);
      } catch (error) {
        setLog('Failed to load health: ' + error.message);
      }
    }

    async function runAction(message, path, body = {}) {
      setLog(`${message}...`);
      try {
        const data = await postAction(path, body);
        setLog(`${message} complete.\n${JSON.stringify(data, null, 2)}`);
        await loadOverview();
      } catch (error) {
        setLog(`${message} failed.\n${error.message}`);
      }
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.getElementById('tab-' + tab).classList.add('active');
        if (tab === 'failures') loadFailures();
        if (tab === 'health') loadHealth();
      });
    });

    document.getElementById('save-password').addEventListener('click', async () => {
      const password = passwordInput.value.trim();
      loginError.textContent = '';
      try {
        const response = await fetch('/admin/login', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        });
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          loginError.textContent = data.detail || 'Login failed';
          throw new Error(data.detail || 'Login failed');
        }
        await loadOverview();
      } catch (error) {
        setLog(error.message || 'Unable to log in');
      }
    });

    document.getElementById('clear-password').addEventListener('click', () => {
      passwordInput.value = '';
      app.classList.add('hidden');
      setLog('Password cleared.');
    });

    document.getElementById('close-user-detail').addEventListener('click', () => {
      document.getElementById('user-detail').classList.add('hidden');
    });

    document.getElementById('reload').addEventListener('click', loadOverview);
    document.getElementById('logout').addEventListener('click', () => {
      fetch('/admin/logout', { method: 'POST', credentials: 'include' }).finally(() => {
        passwordInput.value = '';
        app.classList.add('hidden');
        setLog('Logged out.');
      });
    });

    document.getElementById('seed-sp500').addEventListener('click', () => {
      if (!confirm('Seed the S&P universe? This refreshes the full ticker list.')) return;
      runAction('Seeding S&P universe', '/admin/api/actions/sp500/seed');
    });

    document.getElementById('run-backfill').addEventListener('click', () => {
      const limit = document.getElementById('backfill-limit').value || '25';
      if (!confirm(`Run S&P backfill (limit ${limit})?`)) return;
      runAction('Starting S&P backfill', `/admin/api/actions/sp500/backfill?limit=${encodeURIComponent(limit)}&batch_size=10`);
    });

    document.getElementById('structural-refresh').addEventListener('click', () => {
      const user_id = document.getElementById('target-user').value;
      runAction('Starting structural refresh', '/admin/api/actions/structural-refresh', { user_id });
    });

    document.getElementById('metadata-refresh').addEventListener('click', () => {
      const user_id = document.getElementById('target-user').value;
      runAction('Refreshing ticker metadata', '/admin/api/actions/metadata-refresh', { user_id });
    });

    document.getElementById('run-digest').addEventListener('click', () => {
      const user_id = document.getElementById('target-user').value;
      runAction('Queuing digest', '/admin/api/actions/digest', { user_id });
    });

    loadOverview();
  </script>
</body>
</html>
"""