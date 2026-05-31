#!/usr/bin/env python3
"""
verify_launch_readiness.py — Go/No-Go checklist for Clavix V1 beta launch.

Checks everything that can be verified from code/DB/API.
Items that require external credentials (Apple Dev, APNs, SMTP) are listed but
not failed — they are documented as pending external setup.

Usage:
  cd backend && python -m app.scripts.verify_launch_readiness [--base-url URL]
"""
from __future__ import annotations
import os
import sys
import time
import json
import urllib.request
import urllib.error
import argparse

DEFAULT_BASE = "https://clavis.andoverdigital.com"


def get(url, timeout=20):
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.monotonic() - t0
            try:
                body = json.loads(resp.read())
            except Exception:
                body = {}
            return resp.status, elapsed, body
    except urllib.error.HTTPError as e:
        return e.code, time.monotonic() - t0, {}
    except Exception as e:
        return 0, time.monotonic() - t0, {"error": str(e)}


def check_db():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None, "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — skipping DB checks"
    try:
        from supabase import create_client
        return create_client(url, key), None
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    passes = []
    warnings = []
    failures = []
    external_pending = []

    print("=" * 65)
    print("CLAVIX V1 LAUNCH READINESS CHECK")
    print("=" * 65)

    # ── API Layer ──────────────────────────────────────────────────
    print("\n── API Layer ──")
    code, elapsed, body = get(f"{base}/health")
    if code == 200 and elapsed < 2.0:
        passes.append(f"/health OK in {elapsed:.2f}s")
        print(f"  ✅ /health {elapsed:.2f}s")
    elif code == 200:
        warnings.append(f"/health slow: {elapsed:.2f}s (target <2s)")
        print(f"  ⚠️  /health slow: {elapsed:.2f}s")
    else:
        failures.append(f"/health returned {code}")
        print(f"  ❌ /health returned {code}")

    apns = body.get("apns", "unknown")
    if apns == "configured":
        passes.append("APNs configured")
        print("  ✅ APNs configured")
    else:
        external_pending.append("APNs not configured — needs Apple Developer account + p8 key upload")
        print("  ⏳ APNs missing (external: Apple Dev enrollment required)")

    # auth gate
    code2, _, _ = get(f"{base}/tickers/AAPL")
    if code2 == 401:
        passes.append("Auth gate works on /tickers")
        print("  ✅ Auth gate: 401 on unauthenticated /tickers/AAPL")
    else:
        failures.append(f"Auth gate broken: /tickers/AAPL returned {code2}")
        print(f"  ❌ Auth gate broken: {code2}")

    # ── Database ───────────────────────────────────────────────────
    print("\n── Database / Data ──")
    sb, err = check_db()
    if sb is None:
        print(f"  ⚠️  DB checks skipped: {err}")
        warnings.append(f"DB checks skipped: {err}")
    else:
        # snapshot completeness
        rows = sb.table("ticker_risk_snapshots").select(
            "ticker,grade,composite_score,limited_data_dimensions"
        ).order("analysis_as_of", desc=True).limit(600).execute().data or []
        seen: dict[str, dict] = {}
        for r in rows:
            if r["ticker"] not in seen:
                seen[r["ticker"]] = r
        latest = list(seen.values())
        n = len(latest)
        n_grade = sum(1 for r in latest if r.get("grade"))
        if n >= 490 and n_grade >= 490:
            passes.append(f"Snapshot completeness: {n} tickers, {n_grade} graded")
            print(f"  ✅ Snapshots: {n} tickers, {n_grade} graded")
        else:
            failures.append(f"Snapshot completeness low: {n} tickers, {n_grade} graded")
            print(f"  ❌ Snapshots: {n} tickers, {n_grade} graded")

        # grade distribution
        from collections import Counter
        grade_dist = Counter(r.get("grade") for r in latest if r.get("grade"))
        n_grades = len([g for g, c in grade_dist.items() if c > 0])
        pct_bb = (grade_dist.get("BBB", 0) + grade_dist.get("BB", 0)) / max(n, 1) * 100
        if n_grades >= 4:
            passes.append(f"Grade distribution: {n_grades} grades, BBB+BB={pct_bb:.0f}%")
            print(f"  ✅ Grade distribution: {n_grades} distinct grades, {pct_bb:.0f}% BBB+BB")
        else:
            failures.append(f"Grade distribution too compressed: {n_grades} grades ({pct_bb:.0f}% BBB+BB)")
            print(f"  ❌ Grade distribution compressed: {n_grades} grades, {pct_bb:.0f}% BBB+BB")

        # scheduler
        sched = sb.table("scheduler_jobs").select(
            "user_id,next_run_at,notifications_enabled"
        ).execute().data or []
        import datetime
        now_iso = datetime.datetime.utcnow().isoformat()
        enabled_users = [r for r in sched if r.get("notifications_enabled")]
        future_next = [r for r in enabled_users if (r.get("next_run_at") or "") > now_iso]
        if len(future_next) == len(enabled_users) and enabled_users:
            passes.append(f"Digest scheduler: {len(future_next)}/{len(enabled_users)} users have future next_run_at")
            print(f"  ✅ Digest scheduler: {len(future_next)}/{len(enabled_users)} enabled users scheduled")
        elif not enabled_users:
            warnings.append("No users have notifications enabled")
            print(f"  ⚠️  No users have notifications enabled")
        else:
            failures.append(f"Digest scheduler broken: only {len(future_next)}/{len(enabled_users)} users have future next_run_at")
            print(f"  ❌ Digest scheduler: {len(future_next)}/{len(enabled_users)} users have future next_run_at")

        # dimension realness
        rows2 = sb.table("ticker_risk_snapshots").select(
            "ticker,dimension_inputs,factor_breakdown"
        ).order("analysis_as_of", desc=True).limit(600).execute().data or []
        seen2: dict[str, dict] = {}
        for r in rows2:
            if r["ticker"] not in seen2:
                seen2[r["ticker"]] = r
        latest2 = list(seen2.values())
        vol_real = sum(
            1 for r in latest2
            if isinstance(r.get("dimension_inputs"), dict)
            and r["dimension_inputs"].get("volatility", {}).get("beta_to_spy") is not None
        )
        sec_real = sum(
            1 for r in latest2
            if isinstance(r.get("dimension_inputs"), dict)
            and r["dimension_inputs"].get("sector_exposure", {}).get("sector_beta") is not None
        )
        pct_vol = vol_real / max(len(latest2), 1) * 100
        pct_sec = sec_real / max(len(latest2), 1) * 100
        if pct_vol >= 90:
            passes.append(f"Volatility real: {vol_real}/{len(latest2)} ({pct_vol:.0f}%)")
            print(f"  ✅ Volatility real: {vol_real}/{len(latest2)} tickers ({pct_vol:.0f}%)")
        else:
            warnings.append(f"Volatility real: only {vol_real}/{len(latest2)} ({pct_vol:.0f}%) — run recompute")
            print(f"  ⚠️  Volatility real: {vol_real}/{len(latest2)} ({pct_vol:.0f}%) — run recompute after fix")
        if pct_sec >= 90:
            passes.append(f"Sector real: {sec_real}/{len(latest2)} ({pct_sec:.0f}%)")
            print(f"  ✅ Sector real: {sec_real}/{len(latest2)} tickers ({pct_sec:.0f}%)")
        else:
            warnings.append(f"Sector real: only {sec_real}/{len(latest2)} ({pct_sec:.0f}%) — run recompute")
            print(f"  ⚠️  Sector real: {sec_real}/{len(latest2)} ({pct_sec:.0f}%) — run recompute after fix")

    # ── External Pending ───────────────────────────────────────────
    external_pending += [
        "Apple Developer enrollment → TestFlight / App Store / APNs key",
        "App Store Connect → create clavix_pro_monthly + clavix_pro_annual subscription products",
        "SMTP provider (Resend/Postmark/SES) → configure in Supabase Auth for transactional email",
        "DNS access → add _dmarc.getclavix.com TXT 'v=DMARC1; p=none; rua=mailto:support@getclavix.com'",
        "GitHub Actions → set PROD_SSH_KEY secret for auto-deploy",
    ]

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"PASSES:   {len(passes)}")
    print(f"WARNINGS: {len(warnings)}")
    print(f"FAILURES: {len(failures)}")
    print(f"EXTERNAL: {len(external_pending)} items blocked on external setup")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  ⚠️  {w}")

    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  ❌ {f}")

    print("\nExternal dependencies (cannot unblock without credentials/accounts):")
    for e in external_pending:
        print(f"  ⏳ {e}")

    print()
    if not failures:
        print("GO/NO-GO: ✅ GO for free TestFlight beta (pending external items above)")
    else:
        print("GO/NO-GO: ❌ NO-GO — fix failures above before launch")

    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
