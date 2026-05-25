from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


JOB_RUNS_TABLE = "job_runs"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_job_run(
    supabase,
    *,
    job_id: str,
    tier: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "job_id": job_id,
        "tier": tier,
        "status": "running",
        "started_at": utcnow_iso(),
        "metadata": metadata or {},
    }
    result = supabase.table(JOB_RUNS_TABLE).insert(payload).execute()
    rows = result.data or []
    if rows:
        return rows[0]
    return payload


def finish_job_run(
    supabase,
    run_id: str | None,
    *,
    status: str,
    items_processed: int = 0,
    items_skipped: int = 0,
    items_failed: int = 0,
    error_json: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "completed_at": utcnow_iso(),
        "items_processed": items_processed,
        "items_skipped": items_skipped,
        "items_failed": items_failed,
        "error_json": error_json,
    }
    if metadata is not None:
        payload["metadata"] = metadata
    if not run_id:
        return payload
    result = (
        supabase.table(JOB_RUNS_TABLE)
        .update(payload)
        .eq("id", run_id)
        .execute()
    )
    rows = result.data or []
    if rows:
        return rows[0]
    return {**payload, "id": run_id}
