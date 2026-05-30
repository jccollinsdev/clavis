#!/usr/bin/env python3
"""
verify_data_truth.py — Run after P0/P1 fixes to confirm data is trustworthy.

Usage (from repo root):
  docker exec clavis-backend-1 python -m app.scripts.verify_data_truth
  # or locally:
  cd backend && python -m app.scripts.verify_data_truth
"""
from __future__ import annotations
import os
import sys

def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    from supabase import create_client
    sb = create_client(url, key)

    print("=" * 60)
    print("CLAVIX DATA TRUTH VERIFICATION")
    print("=" * 60)
    failures = []

    # 1. Snapshot completeness
    rows = sb.table("ticker_risk_snapshots").select(
        "ticker,composite_score,grade,limited_data_dimensions,analysis_as_of"
    ).order("analysis_as_of", desc=True).limit(600).execute().data or []

    # deduplicate to latest per ticker
    seen: dict[str, dict] = {}
    for r in rows:
        t = r["ticker"]
        if t not in seen:
            seen[t] = r
    latest = list(seen.values())

    total = len(latest)
    with_grade = sum(1 for r in latest if r.get("grade"))
    with_score = sum(1 for r in latest if r.get("composite_score") is not None)
    print(f"\n[1] Snapshot completeness: {total} tickers, {with_grade} with grade, {with_score} with score")
    if total < 490:
        failures.append(f"Too few tickers with snapshots: {total}")

    # 2. Grade distribution
    from collections import Counter
    grade_dist = Counter(r.get("grade") for r in latest if r.get("grade"))
    print(f"\n[2] Grade distribution:")
    for grade in ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "F"]:
        count = grade_dist.get(grade, 0)
        bar = "█" * min(count // 5, 40)
        print(f"    {grade:4s}: {count:4d}  {bar}")
    grades_present = len([g for g, c in grade_dist.items() if c > 0])
    pct_bbb_bb = (grade_dist.get("BBB", 0) + grade_dist.get("BB", 0)) / max(total, 1) * 100
    print(f"    Grades present: {grades_present}, BBB+BB: {pct_bbb_bb:.1f}%")
    if grades_present < 4:
        failures.append(f"Grade distribution too compressed: only {grades_present} grades represented")
    if pct_bbb_bb > 90:
        failures.append(f"BBB+BB dominance too high: {pct_bbb_bb:.1f}% (target <75%)")

    # 3. Dimension realness
    rows2 = sb.table("ticker_risk_snapshots").select(
        "ticker,dimension_inputs,factor_breakdown,limited_data_dimensions"
    ).order("analysis_as_of", desc=True).limit(600).execute().data or []

    seen2: dict[str, dict] = {}
    for r in rows2:
        t = r["ticker"]
        if t not in seen2:
            seen2[t] = r
    latest2 = list(seen2.values())

    total2 = len(latest2)
    vol_beta_real = sum(
        1 for r in latest2
        if isinstance(r.get("dimension_inputs"), dict)
        and r["dimension_inputs"].get("volatility", {}).get("beta_to_spy") is not None
    )
    sec_beta_real = sum(
        1 for r in latest2
        if isinstance(r.get("dimension_inputs"), dict)
        and r["dimension_inputs"].get("sector_exposure", {}).get("sector_beta") is not None
    )
    macro_real = sum(
        1 for r in latest2
        if isinstance(r.get("factor_breakdown"), dict)
        and r["factor_breakdown"].get("macro_regression", {}).get("limited_data") is False
    )
    vol_limited_disclosed = sum(
        1 for r in latest2
        if isinstance(r.get("limited_data_dimensions"), list)
        and "volatility" in r["limited_data_dimensions"]
    )
    sec_limited_disclosed = sum(
        1 for r in latest2
        if isinstance(r.get("limited_data_dimensions"), list)
        and "sector_exposure" in r["limited_data_dimensions"]
    )

    print(f"\n[3] Dimension realness (out of {total2} latest snapshots):")
    print(f"    beta_to_spy real:      {vol_beta_real:4d} / {total2}")
    print(f"    sector_beta real:      {sec_beta_real:4d} / {total2}")
    print(f"    macro real:            {macro_real:4d} / {total2}")
    print(f"    vol limited disclosed: {vol_limited_disclosed:4d} / {total2}  (should equal tickers without beta_to_spy)")
    print(f"    sec limited disclosed: {sec_limited_disclosed:4d} / {total2}  (should equal tickers without sector_beta)")

    # 4. Scheduler / digest jobs
    sched_rows = sb.table("scheduler_jobs").select(
        "user_id,digest_time,last_run_at,next_run_at,notifications_enabled,last_run_status"
    ).execute().data or []
    print(f"\n[4] Scheduler jobs ({len(sched_rows)} rows):")
    import datetime
    now_iso = datetime.datetime.utcnow().isoformat()
    for r in sched_rows:
        enabled = r.get("notifications_enabled")
        next_run = r.get("next_run_at") or "NULL"
        future = next_run > now_iso if next_run != "NULL" else False
        status = "✅ future" if (future and enabled) else ("⏸️  disabled" if not enabled else "❌ PAST")
        print(f"    user {r['user_id'][:8]}: next={next_run[:19]}  enabled={enabled}  {status}")
        if enabled and not future:
            failures.append(f"User {r['user_id'][:8]}: next_run_at is in the past — digest not firing")

    # 5. News enrichment (7-day window)
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    news_rows = sb.table("shared_ticker_events").select(
        "id,sentiment_score,published_at"
    ).gte("published_at", cutoff).execute().data or []
    total_news = len(news_rows)
    null_sentiment = sum(1 for r in news_rows if r.get("sentiment_score") is None)
    null_pct = null_sentiment / max(total_news, 1) * 100
    print(f"\n[5] News enrichment (7-day): {total_news} articles, {null_sentiment} null sentiment ({null_pct:.1f}%)")
    if null_pct > 10:
        failures.append(f"High null sentiment rate in 7d: {null_pct:.1f}%")

    # Summary
    print("\n" + "=" * 60)
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  ❌ {f}")
        sys.exit(1)
    else:
        print("RESULT: ALL CHECKS PASSED ✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
