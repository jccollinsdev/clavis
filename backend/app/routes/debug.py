import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from ..services.access_control import require_admin_user_id
from ..services.debug_service import (
    get_debug_service,
    track_request,
    finish_request,
    TrackingSession,
    patch_minimax_service,
)
from starlette.datastructures import URL
import json
import asyncio
from ..services.supabase import get_supabase
from ..pipeline.scheduler import trigger_user_digest

router = APIRouter(tags=["debug"])

PATCHED = False


def ensure_patched():
    global PATCHED
    if not PATCHED:
        patch_minimax_service()
        PATCHED = True


@router.get("/dashboard")
async def dashboard(user_id: str = Depends(require_admin_user_id)):
    ensure_patched()
    return HTMLResponse(DASHBOARD_HTML)


@router.get("/requests")
async def get_requests(user_id: str = Depends(require_admin_user_id)):
    ensure_patched()
    service = get_debug_service()
    return JSONResponse(service.get_requests())


@router.get("/ai-calls")
async def get_ai_calls(user_id: str = Depends(require_admin_user_id)):
    ensure_patched()
    service = get_debug_service()
    return JSONResponse(service.get_ai_calls())


@router.get("/stats")
async def get_stats(user_id: str = Depends(require_admin_user_id)):
    ensure_patched()
    service = get_debug_service()
    return JSONResponse(service.get_stats())


@router.post("/clear")
async def clear_debug(user_id: str = Depends(require_admin_user_id)):
    service = get_debug_service()
    service.clear_all()
    return JSONResponse({"status": "cleared"})


@router.post("/run-analysis")
async def run_analysis(user_id: str = Depends(require_admin_user_id)):
    supabase = get_supabase()

    run = await trigger_user_digest(user_id)
    return JSONResponse({"status": "queued", "user_id": user_id, "run": run})


@router.get("/")
async def debug_index(user_id: str = Depends(require_admin_user_id)):
    ensure_patched()
    service = get_debug_service()
    stats = service.get_stats()
    return JSONResponse(
        {
            "message": "Clavis Debug Dashboard",
            "dashboard_url": "/debug/dashboard",
            "stats": stats,
            "endpoints": {
                "GET /debug/dashboard": "HTML dashboard",
                "GET /debug/requests": "List all tracked HTTP requests",
                "GET /debug/ai-calls": "List all AI calls with messages & responses",
                "GET /debug/stats": "Aggregate statistics",
                "POST /debug/clear": "Clear all debug data",
            },
        }
    )


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clavis Debug Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; background: #0d1117; color: #e6edf3; font-size: 13px; }
        .header { background: #161b22; border-bottom: 1px solid #30363d; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 16px; font-weight: 600; color: #58a6ff; }
        .header .stats { display: flex; gap: 20px; font-size: 12px; }
        .stat { display: flex; flex-direction: column; }
        .stat .label { color: #8b949e; font-size: 11px; }
        .stat .value { color: #58a6ff; font-size: 16px; font-weight: 600; }
        .btn { background: #238636; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .btn:hover { background: #2ea043; }
        .btn.refresh { background: #1f6feb; }
        .btn.refresh:hover { background: #388bfd; }
        .tabs { background: #161b22; border-bottom: 1px solid #30363d; padding: 0 20px; display: flex; gap: 4px; }
        .tab { padding: 10px 16px; cursor: pointer; color: #8b949e; border-bottom: 2px solid transparent; font-size: 13px; }
        .tab:hover { color: #e6edf3; }
        .tab.active { color: #58a6ff; border-bottom-color: #58a6ff; }
        .content { padding: 20px; }
        .section { display: none; }
        .section.active { display: block; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 8px 12px; background: #161b22; border-bottom: 1px solid #30363d; color: #8b949e; font-weight: 500; font-size: 11px; text-transform: uppercase; }
        td { padding: 10px 12px; border-bottom: 1px solid #21262d; }
        tr:hover { background: #161b22; }
        .method { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }
        .method.GET { background: #238636; color: white; }
        .method.POST { background: #1f6feb; color: white; }
        .method.PATCH { background: #d29922; color: black; }
        .method.DELETE { background: #da3633; color: white; }
        .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
        .status.green { background: rgba(35, 134, 54, 0.4); color: #3fb950; }
        .status.red { background: rgba(218, 54, 51, 0.4); color: #f85149; }
        .status.yellow { background: rgba(210, 153, 34, 0.4); color: #d29922; }
        .mono { font-family: 'SF Mono', Monaco, monospace; font-size: 12px; }
        .duration { color: #8b949e; }
        .duration.fast { color: #3fb950; }
        .duration.slow { color: #f85149; }
        .timestamp { color: #8b949e; font-size: 11px; }
        .message-content { max-width: 400px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .full-message { display: none; }
        .row.expanded .full-message { display: block; white-space: pre-wrap; background: #0d1117; border: 1px solid #30363d; padding: 10px; margin-top: 8px; border-radius: 6px; font-size: 11px; max-height: 300px; overflow-y: auto; }
        .row.expanded .short-message { display: none; }
        .ai-call { background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 12px; overflow: hidden; }
        .ai-header { padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .ai-header:hover { background: #1c2128; }
        .ai-id { color: #58a6ff; font-size: 11px; }
        .ai-model { color: #8b949e; font-size: 12px; }
        .ai-duration { font-size: 12px; }
        .ai-duration.fast { color: #3fb950; }
        .ai-duration.medium { color: #d29922; }
        .ai-duration.slow { color: #f85149; }
        .ai-body { display: none; border-top: 1px solid #30363d; }
        .ai-body.open { display: block; }
        .ai-section { border-bottom: 1px solid #21262d; }
        .ai-section:last-child { border-bottom: none; }
        .ai-section-title { padding: 8px 16px; background: #0d1117; color: #8b949e; font-size: 10px; text-transform: uppercase; font-weight: 600; }
        .ai-section-content { padding: 12px 16px; font-size: 12px; }
        .msg-role { color: #58a6ff; font-weight: 500; margin-right: 8px; }
        .msg-content { white-space: pre-wrap; color: #e6edf3; }
        .error { color: #f85149; background: rgba(248, 81, 73, 0.1); padding: 8px 12px; border-radius: 4px; }
        .empty { text-align: center; padding: 40px; color: #8b949e; }
        .filter-bar { margin-bottom: 16px; display: flex; gap: 12px; align-items: center; }
        .filter-bar input { background: #0d1117; border: 1px solid #30363d; color: #e6edf3; padding: 6px 10px; border-radius: 6px; font-size: 12px; width: 200px; }
        .filter-bar input::placeholder { color: #8b949e; }
        .count-badge { background: #30363d; padding: 2px 8px; border-radius: 10px; font-size: 11px; color: #8b949e; }
        .user-id { color: #8b949e; font-size: 11px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Clavis Debug Dashboard</h1>
        <div class="stats" id="stats"></div>
        <div style="display: flex; gap: 8px;">
            <button class="btn refresh" onclick="refreshAll()">Refresh</button>
            <button class="btn" onclick="clearAll()">Clear</button>
        </div>
    </div>

    <div class="tabs">
        <div class="tab active" onclick="showTab('requests')">HTTP Requests <span class="count-badge" id="req-count">0</span></div>
        <div class="tab" onclick="showTab('ai')">AI Calls <span class="count-badge" id="ai-count">0</span></div>
        <div class="tab" onclick="showTab('stats')">Stats</div>
    </div>

    <div class="content">
        <div id="requests" class="section active">
            <div class="filter-bar">
                <input type="text" id="req-filter" placeholder="Filter by path..." oninput="filterRequests()">
            </div>
            <div id="requests-list">Loading...</div>
        </div>

        <div id="ai" class="section">
            <div class="filter-bar">
                <input type="text" id="ai-filter" placeholder="Filter by function or model..." oninput="filterAI()">
            </div>
            <div id="ai-list">Loading...</div>
        </div>

        <div id="stats" class="section">
            <div id="stats-content"></div>
        </div>
    </div>

    <script>
        let requests = [];
        let aiCalls = [];

        async function refreshAll() {
            await Promise.all([loadRequests(), loadAICalls(), loadStats()]);
        }

        async function loadRequests() {
            try {
                const res = await fetch('/debug/requests');
                requests = await res.json();
                renderRequests(requests);
            } catch(e) { console.error(e); }
        }

        async function loadAICalls() {
            try {
                const res = await fetch('/debug/ai-calls');
                aiCalls = await res.json();
                renderAICalls(aiCalls);
            } catch(e) { console.error(e); }
        }

        async function loadStats() {
            try {
                const res = await fetch('/debug/stats');
                const stats = await res.json();
                document.getElementById('stats').innerHTML = `
                    <div class="stat"><div class="label">Total Requests</div><div class="value">${stats.total_requests}</div></div>
                    <div class="stat"><div class="label">Avg Duration</div><div class="value">${stats.avg_request_duration_ms}ms</div></div>
                    <div class="stat"><div class="label">AI Calls</div><div class="value">${stats.total_ai_calls}</div></div>
                    <div class="stat"><div class="label">Avg AI Duration</div><div class="value">${stats.avg_ai_duration_ms}ms</div></div>
                `;
                document.getElementById('stats-content').innerHTML = `
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
                        <tr><td>Total Requests</td><td>${stats.total_requests}</td></tr>
                        <tr><td>Avg Request Duration</td><td>${stats.avg_request_duration_ms}ms</td></tr>
                        <tr><td>Total AI Calls</td><td>${stats.total_ai_calls}</td></tr>
                        <tr><td>Avg AI Duration</td><td>${stats.avg_ai_duration_ms}ms</td></tr>
                        <tr><td>Requests/min</td><td>${stats.requests_per_minute}</td></tr>
                    </table>
                `;
            } catch(e) { console.error(e); }
        }

        function renderRequests(reqs) {
            document.getElementById('req-count').textContent = reqs.length;
            if (!reqs.length) {
                document.getElementById('requests-list').innerHTML = '<div class="empty">No requests tracked yet</div>';
                return;
            }
            let html = `<table><tr><th>Method</th><th>Path</th><th>User</th><th>Status</th><th>Duration</th><th>Time</th></tr>`;
            reqs.forEach(r => {
                const durClass = r.duration_ms < 200 ? 'fast' : r.duration_ms > 1000 ? 'slow' : '';
                const statusClass = r.status_code < 300 ? 'green' : r.status_code < 400 ? 'yellow' : 'red';
                const shortBody = r.request_body ? r.request_body.substring(0, 100) : '';
                const shortResp = r.response_body ? r.response_body.substring(0, 100) : '';
                html += `<tr class="row" onclick="toggleRow(this)">
                    <td><span class="method ${r.method}">${r.method}</span></td>
                    <td class="mono">${r.path}</td>
                    <td class="user-id">${r.user_id || 'anonymous'}</td>
                    <td><span class="status ${statusClass}">${r.status_code}</span></td>
                    <td class="duration ${durClass}">${Math.round(r.duration_ms)}ms</td>
                    <td class="timestamp">${r.started_at.split('T')[1].slice(0,8)}</td>
                </tr>
                <tr class="full-message-row" style="display:none"><td colspan="6">
                    <div class="full-message">
                        <strong>Request Body:</strong>\\n${escapeHtml(r.request_body || '(none)')}
                        \\n\\n<strong>Response Body:</strong>\\n${escapeHtml(r.response_body || '(none)')}
                    </div>
                </td></tr>`;
            });
            html += '</table>';
            document.getElementById('requests-list').innerHTML = html;
        }

        function renderAICalls(calls) {
            document.getElementById('ai-count').textContent = calls.length;
            if (!calls.length) {
                document.getElementById('ai-list').innerHTML = '<div class="empty">No AI calls tracked yet</div>';
                return;
            }
            let html = '';
            calls.forEach(c => {
                const durClass = c.duration_ms < 1000 ? 'fast' : c.duration_ms > 3000 ? 'slow' : 'medium';
                const errorHtml = c.error ? `<div class="error">Error: ${escapeHtml(c.error)}</div>` : '';
                let messagesHtml = '';
                c.messages.forEach(m => {
                    const content = typeof m.content === 'string' ? m.content : JSON.stringify(m.content);
                    messagesHtml += `<div style="margin-bottom:8px"><span class="msg-role">${m.role}</span><span class="msg-content">${escapeHtml(content.substring(0, 500))}${content.length > 500 ? '...' : ''}</span></div>`;
                });
                const responsePreview = c.response ? c.response.substring(0, 200) : '';
                html += `<div class="ai-call">
                    <div class="ai-header" onclick="toggleAI(this)">
                        <div>
                            <span class="ai-id">${c.id}</span>
                            <span class="ai-model">${c.function_name} (${c.model})</span>
                        </div>
                        <div>
                            <span class="ai-duration ${durClass}">${Math.round(c.duration_ms)}ms</span>
                        </div>
                    </div>
                    <div class="ai-body">
                        ${errorHtml}
                        <div class="ai-section">
                            <div class="ai-section-title">Messages (${c.messages.length})</div>
                            <div class="ai-section-content">${messagesHtml}</div>
                        </div>
                        <div class="ai-section">
                            <div class="ai-section-title">Response Preview</div>
                            <div class="ai-section-content mono">${escapeHtml(responsePreview)}${c.response && c.response.length > 200 ? '...' : ''}</div>
                        </div>
                    </div>
                </div>`;
            });
            document.getElementById('ai-list').innerHTML = html;
        }

        function showTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(name).classList.add('active');
        }

        function toggleRow(row) {
            const nextRow = row.nextElementSibling;
            if (nextRow && nextRow.classList.contains('full-message-row')) {
                nextRow.style.display = nextRow.style.display === 'none' ? 'table-row' : 'none';
            }
        }

        function toggleAI(header) {
            header.nextElementSibling.classList.toggle('open');
        }

        function filterRequests() {
            const q = document.getElementById('req-filter').value.toLowerCase();
            const filtered = requests.filter(r => r.path.toLowerCase().includes(q));
            renderRequests(filtered);
        }

        function filterAI() {
            const q = document.getElementById('ai-filter').value.toLowerCase();
            const filtered = aiCalls.filter(c => c.function_name.toLowerCase().includes(q) || c.model.toLowerCase().includes(q));
            renderAICalls(filtered);
        }

        async function clearAll() {
            await fetch('/debug/clear', { method: 'POST' });
            refreshAll();
        }

        function escapeHtml(s) {
            if (!s) return '';
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        refreshAll();
        setInterval(refreshAll, 5000);
    </script>
</body>
</html>
"""
