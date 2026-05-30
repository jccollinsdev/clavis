#!/usr/bin/env python3
"""
verify_api_serving.py — Probe the live production API for correctness and latency.

Usage:
  python -m app.scripts.verify_api_serving [--base-url https://clavis.andoverdigital.com]

Note: /tickers/{ticker} requires a valid JWT. Without one, only /health is checked
for authenticated endpoints. Pass --token <jwt> to probe protected routes.
"""
from __future__ import annotations
import sys
import time
import argparse
import urllib.request
import urllib.error
import json

DEFAULT_BASE = "https://clavis.andoverdigital.com"
DEMO_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "XOM", "SPY"]


def get(url: str, token: str | None = None, timeout: int = 20) -> tuple[int, float, dict | None]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.monotonic() - t0
            try:
                body = json.loads(resp.read())
            except Exception:
                body = None
            return resp.status, elapsed, body
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - t0
        return e.code, elapsed, None
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"  ERROR: {e}")
        return 0, elapsed, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--token", default=None, help="Supabase JWT for authenticated routes")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print("=" * 60)
    print(f"CLAVIX API SERVING VERIFICATION — {base}")
    print("=" * 60)
    failures = []

    # 1. /health
    code, elapsed, body = get(f"{base}/health")
    apns = (body or {}).get("apns", "unknown")
    supabase = (body or {}).get("supabase", "unknown")
    status_ok = (body or {}).get("status") == "ok"
    print(f"\n[1] GET /health  → {code}  {elapsed:.3f}s")
    print(f"    status={status_ok}  apns={apns}  supabase={supabase}")
    if code != 200:
        failures.append(f"/health returned {code}")
    if elapsed > 2.0:
        failures.append(f"/health latency too high: {elapsed:.2f}s (target <2s)")
    if apns == "configured":
        print("    ✅ APNs configured")
    else:
        print("    ⚠️  APNs missing — push delivery blocked (needs Apple Dev setup)")

    # 2. Auth gate on /tickers
    code2, elapsed2, _ = get(f"{base}/tickers/AAPL")
    print(f"\n[2] GET /tickers/AAPL (no auth)  → {code2}  {elapsed2:.3f}s")
    if code2 != 401:
        failures.append(f"/tickers/AAPL without auth returned {code2} (expected 401)")
    else:
        print("    ✅ Auth gate works")

    # 3. Authenticated ticker probes (if token provided)
    if args.token:
        print(f"\n[3] Authenticated ticker probes:")
        for ticker in DEMO_TICKERS:
            code3, elapsed3, body3 = get(f"{base}/tickers/{ticker}", token=args.token)
            if code3 == 200 and body3:
                grade = body3.get("grade", "?")
                score = body3.get("composite_score") or body3.get("safety_score", "?")
                limited = body3.get("limited_data_dimensions") or []
                print(f"    {ticker:6s}: {code3}  {elapsed3:.2f}s  grade={grade}  score={score}  limited={limited}")
                if elapsed3 > 5.0:
                    failures.append(f"/tickers/{ticker} latency: {elapsed3:.2f}s (target <5s)")
            else:
                print(f"    {ticker:6s}: {code3}  {elapsed3:.2f}s  ❌")
                failures.append(f"/tickers/{ticker} returned {code3}")
    else:
        print(f"\n[3] Skipping authenticated ticker probes (pass --token <jwt> to test)")

    # Summary
    print("\n" + "=" * 60)
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S)")
        for f in failures:
            print(f"  ❌ {f}")
        sys.exit(1)
    else:
        print("RESULT: ALL CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
