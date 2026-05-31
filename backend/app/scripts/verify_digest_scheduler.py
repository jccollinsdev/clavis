#!/usr/bin/env python3
"""
verify_digest_scheduler.py — Verify that per-user digest jobs are scheduled
and next_run_at is advancing after the scheduler fix.

Usage:
  docker exec clavis-backend-1 python -m app.scripts.verify_digest_scheduler
  # or locally:
  cd backend && python -m app.scripts.verify_digest_scheduler
"""
from __future__ import annotations
import os
import sys
import datetime


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    from supabase import create_client
    sb = create_client(url, key)
    now_iso = datetime.datetime.utcnow().isoformat()
    failures = []

    print("=" * 60)
    print("CLAVIX DIGEST SCHEDULER VERIFICATION")
    print(f"Current UTC time: {now_iso[:19]}")
    print("=" * 60)

    rows = sb.table("scheduler_jobs").select("*").execute().data or []
    print(f"\nTotal scheduler_jobs rows: {len(rows)}")

    for r in rows:
        uid = r.get("user_id", "?")[:8]
        enabled = r.get("notifications_enabled", False)
        last_run = (r.get("last_run_at") or "never")[:19]
        next_run = r.get("next_run_at") or "NULL"
        status = r.get("last_run_status") or "?"
        digest_time = r.get("digest_time") or "?"

        is_future = (next_run != "NULL") and (next_run > now_iso)
        future_str = "✅ future" if is_future else ("⏸  disabled" if not enabled else "❌ PAST/NULL")

        print(f"\n  user_{uid}:")
        print(f"    notifications_enabled: {enabled}")
        print(f"    digest_time: {digest_time}")
        print(f"    last_run_at: {last_run}")
        print(f"    next_run_at: {next_run[:19] if next_run != 'NULL' else 'NULL'}  {future_str}")
        print(f"    last_run_status: {status}")

        if enabled and not is_future:
            failures.append(
                f"user_{uid}: next_run_at is {'NULL' if next_run == 'NULL' else 'in the past'} "
                f"({next_run[:19]}) — digest CronTrigger is not registered"
            )

    # Check recent digest deliveries (last 7 days)
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
    recent = (
        sb.table("digests")
        .select("user_id,generated_at,overall_grade")
        .gte("generated_at", cutoff)
        .order("generated_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    print(f"\nRecent digest deliveries (last 7d): {len(recent)}")
    for d in recent[:10]:
        uid = (d.get("user_id") or "?")[:8]
        gen = (d.get("generated_at") or "?")[:19]
        grade = d.get("overall_grade") or "?"
        print(f"  user_{uid}  generated={gen}  grade={grade}")

    print("\n" + "=" * 60)
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  ❌ {f}")
        print("\nFix: restart the backend container — the scheduler fix will re-register digest jobs.")
        sys.exit(1)
    else:
        print("RESULT: Digest scheduler looks healthy ✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
