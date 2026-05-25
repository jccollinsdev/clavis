from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def latest_job_freshness(supabase, job_ids: list[str]) -> dict[str, Any]:
    if not job_ids:
        return {"as_of": None, "job_id": None, "age_seconds": None}

    query = (
        supabase.table("job_runs")
        .select("job_id,started_at,completed_at,status")
        .eq("status", "completed")
        .order("completed_at", desc=True)
        .limit(1)
    )
    if len(job_ids) == 1:
        query = query.eq("job_id", job_ids[0])
    else:
        query = query.in_("job_id", job_ids)
    rows = query.execute().data or []
    if not rows:
        return {"as_of": None, "job_id": job_ids[0], "age_seconds": None}

    row = rows[0]
    as_of = row.get("completed_at") or row.get("started_at")
    parsed = _parse_timestamp(as_of)
    age_seconds = (
        int((datetime.now(timezone.utc) - parsed).total_seconds())
        if parsed
        else None
    )
    return {
        "as_of": as_of,
        "job_id": row.get("job_id") or job_ids[0],
        "age_seconds": max(0, age_seconds) if age_seconds is not None else None,
    }
