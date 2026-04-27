from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, Query, Request
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
    create_admin_session_cookie,
    require_admin_session,
)
from ..services.supabase import get_supabase
from .analysis_runs import _enrich_run

router = APIRouter()


class AdminTargetRequest(BaseModel):
    user_id: str | None = None


class AdminLoginRequest(BaseModel):
    password: str


def _cache_headers() -> dict[str, str]:
    return {"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"}


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
                "email": email,
                "created_at": created_at,
            }
        )
    return users


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

    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "admin_user_id": admin_user_id,
        "counts": {
            "users": len(preferences),
            "positions": _count_rows(supabase, "positions"),
            "alerts": _count_rows(supabase, "alerts"),
            "digests": _count_rows(supabase, "digests"),
            "analysis_runs": _count_rows(supabase, "analysis_runs"),
            "ticker_refresh_jobs": _count_rows(supabase, "ticker_refresh_jobs"),
        },
        "tier_counts": dict(sorted(tier_counts.items())),
        "sp500_cache": get_sp500_cache_status(limit=8),
        "recent_analysis_runs": _serialize_rows(_recent_analysis_runs(supabase)),
        "recent_users": _serialize_rows(_recent_users(supabase)),
    }
    return _serialize_overview(overview)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_shell(request: Request):
    return HTMLResponse(ADMIN_HTML, headers=_cache_headers())


@router.post("/login")
async def admin_login(payload: AdminLoginRequest):
    settings = get_settings()
    if not settings.admin_password:
        return JSONResponse(
            {"detail": "Admin password is not configured"}, status_code=503
        )
    if payload.password != settings.admin_password:
        return JSONResponse({"detail": "Invalid password"}, status_code=401)

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


@router.get("/api/runs")
async def api_runs(user_id: str = Depends(require_admin_session)):
    supabase = get_supabase()
    return JSONResponse(
        {"runs": _serialize_rows(_recent_analysis_runs(supabase, limit=50))},
        headers=_cache_headers(),
    )


@router.post("/api/actions/sp500/seed")
async def api_seed_sp500(user_id: str = Depends(require_admin_session)):
    return JSONResponse(await trigger_seed_sp500())


async def trigger_seed_sp500() -> dict:
    from ..pipeline.scheduler import seed_sp500_universe

    return await seed_sp500_universe()


@router.post("/api/actions/sp500/backfill")
async def api_backfill_sp500(
    limit: int | None = Query(default=None, ge=1, le=500),
    batch_size: int = Query(default=10, ge=1, le=25),
    user_id: str = Depends(require_admin_session),
):
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
    payload: AdminTargetRequest | None = Body(default=None),
    user_id: str = Depends(require_admin_session),
):
    payload = payload or AdminTargetRequest()
    target_user_id = payload.user_id or SYSTEM_SP500_USER_ID
    return JSONResponse(await trigger_structural_refresh(target_user_id))


@router.post("/api/actions/metadata-refresh")
async def api_metadata_refresh(
    payload: AdminTargetRequest | None = Body(default=None),
    user_id: str = Depends(require_admin_session),
):
    payload = payload or AdminTargetRequest()
    target_user_id = payload.user_id or SYSTEM_SP500_USER_ID
    updated = refresh_all_positions_metadata(target_user_id)
    return JSONResponse({"status": "ok", "user_id": target_user_id, "updated": updated})


@router.post("/api/actions/digest")
async def api_trigger_digest(
    payload: AdminTargetRequest | None = Body(default=None),
    user_id: str = Depends(require_admin_session),
):
    payload = payload or AdminTargetRequest()
    target_user_id = payload.user_id or SYSTEM_SP500_USER_ID
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
        <div class="subtle">The password is checked on the server and the browser gets an HttpOnly session cookie.</div>
      </div>
    </div>

    <div id="app" class="hidden">
      <div class="grid" id="stats"></div>

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
          <button id="structural-refresh">Structural refresh</button>
          <button class="secondary" id="metadata-refresh">Metadata refresh</button>
          <button class="secondary" id="run-digest">Run digest</button>
          <button class="warn" id="seed-sp500">Seed S&P universe</button>
          <button class="warn" id="run-backfill">Run S&P backfill</button>
        </div>
        <div id="action-log" class="log">Ready.</div>
      </div>

      <div class="section panel table">
        <div class="section-head">
          <div class="section-title">Users</div>
          <div class="subtle" id="users-summary"></div>
        </div>
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Tier</th>
              <th>Digest</th>
              <th>Notifications</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody id="users-table"></tbody>
        </table>
      </div>

      <div class="section panel table">
        <div class="section-head">
          <div class="section-title">Recent runs</div>
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
  </div>

  <script>
    let overview = null;

    const app = document.getElementById('app');
    const actionLog = document.getElementById('action-log');
    const passwordInput = document.getElementById('password');

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

    function statusClass(text) {
      const v = String(text || '').toLowerCase();
      if (v.includes('fail') || v.includes('error')) return 'danger';
      if (v.includes('queue') || v.includes('running') || v.includes('partial')) return 'warn';
      return '';
    }

    function renderUsers(users) {
      document.getElementById('users-summary').textContent = `${users.length} loaded`;
      document.getElementById('target-user').innerHTML = users.map((user) => {
        const label = [user.email || user.user_id, user.subscription_tier || 'free'].filter(Boolean).join(' · ');
        return `<option value="${escapeHtml(user.user_id)}">${escapeHtml(label)}</option>`;
      }).join('');
      document.getElementById('users-table').innerHTML = users.map((user) => `
        <tr>
          <td><div>${user.email ? escapeHtml(user.email) : '<span class="subtle">no email</span>'}</div><div class="mono subtle">${escapeHtml(user.user_id || '')}</div></td>
          <td><span class="status">${escapeHtml(user.subscription_tier || 'free')}</span></td>
          <td>${user.digest_time ? escapeHtml(user.digest_time) : '<span class="subtle">unset</span>'}</td>
          <td>${user.notifications_enabled ? 'on' : 'off'}</td>
          <td class="subtle">${escapeHtml(user.updated_at || user.created_at || '')}</td>
        </tr>
      `).join('');
    }

    function renderRuns(runs) {
      document.getElementById('runs-summary').textContent = `${runs.length} latest`;
      document.getElementById('runs-table').innerHTML = runs.map((run) => {
        const stage = run.current_stage || 'idle';
        const progress = run.progress != null ? `${run.progress}%` : 'n/a';
        return `
          <tr>
            <td class="mono">${escapeHtml(run.id || '')}</td>
            <td class="mono">${escapeHtml(run.user_id || '')}</td>
            <td><span class="status ${statusClass(run.status)}">${escapeHtml(run.status || 'unknown')}</span></td>
            <td>${escapeHtml(stage)}</td>
            <td>${escapeHtml(progress)}</td>
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

    async function runAction(message, path, options = {}) {
      setLog(`${message}...`);
      try {
        const data = await api(path, options);
        setLog(`${message} complete.\n${JSON.stringify(data, null, 2)}`);
        await loadOverview();
      } catch (error) {
        setLog(`${message} failed.\n${error.message}`);
      }
    }

    document.getElementById('save-password').addEventListener('click', async () => {
      const password = passwordInput.value.trim();
      try {
        const response = await fetch('/admin/login', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        });
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
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

    document.getElementById('reload').addEventListener('click', loadOverview);
    document.getElementById('logout').addEventListener('click', () => {
      fetch('/admin/logout', { method: 'POST', credentials: 'include' }).finally(() => {
        passwordInput.value = '';
        app.classList.add('hidden');
        setLog('Logged out.');
      });
    });

    document.getElementById('seed-sp500').addEventListener('click', () => {
      runAction('Seeding S&P universe', '/admin/api/actions/sp500/seed', { method: 'POST' });
    });

    document.getElementById('run-backfill').addEventListener('click', () => {
      const limit = document.getElementById('backfill-limit').value || '25';
      runAction('Starting S&P backfill', `/admin/api/actions/sp500/backfill?limit=${encodeURIComponent(limit)}&batch_size=10`, { method: 'POST' });
    });

    document.getElementById('structural-refresh').addEventListener('click', () => {
      const user_id = document.getElementById('target-user').value;
      runAction('Starting structural refresh', '/admin/api/actions/structural-refresh', {
        method: 'POST',
        body: JSON.stringify({ user_id }),
      });
    });

    document.getElementById('metadata-refresh').addEventListener('click', () => {
      const user_id = document.getElementById('target-user').value;
      runAction('Refreshing ticker metadata', '/admin/api/actions/metadata-refresh', {
        method: 'POST',
        body: JSON.stringify({ user_id }),
      });
    });

    document.getElementById('run-digest').addEventListener('click', () => {
      const user_id = document.getElementById('target-user').value;
      runAction('Queuing digest', '/admin/api/actions/digest', {
        method: 'POST',
        body: JSON.stringify({ user_id }),
      });
    });

    loadOverview();
  </script>
</body>
</html>
"""
