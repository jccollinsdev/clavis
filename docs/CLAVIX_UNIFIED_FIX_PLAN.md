# Clavix Unified Fix Plan

**Created:** 2026-05-30  
**Source audits:** CLAVIX_PRODUCTION_AUDIT.md (2026-05-29) + CLAVIX_DATA_TRUTH_AUDIT.md (2026-05-30)  
**Goal:** Get Clavix launch-ready for free TestFlight beta (Day 21) and paid App Store (Day 28).  
**Autonomy:** Fix everything fixable in code/DB/config. Block only on Apple Dev enrollment, APNs key, App Store Connect StoreKit products, SMTP credentials, DNS records.

---

## Combined Score Before Fixes
- Production Audit: **58/100** (backend degraded, StoreKit absent)
- Data Truth Audit: **42/100** (3/5 dims heuristic, digests stopped, grades compressed)

---

## Root Cause Summary

Three defects explain most of the damage:

1. **Polygon index ticker auth-failure poisons global call gate.**  
   `I:TNX` and `I:VIX` return 403 Not Authorized. `_block_polygon_auth()` sets a 300s process-wide cooldown. All subsequent `fetch_aggs()` calls return synthetic 403 instantly. This kills bar-fetch for all 504 tickers → macro regression limited_data 100%, volatility real inputs 0/504, sector_beta 0/504.

2. **APScheduler `intraday` tier removes per-user digest jobs without re-registering them.**  
   `start_scheduler()` unconditionally removes all `user_*` APScheduler jobs at line 5602-5606, then returns early at line 5608 if tier=intraday, never re-adding them. Both real users' digests stopped; `next_run_at` is frozen in the past.

3. **Sector and volatility scorers ignore real computed inputs.**  
   `_build_sector_exposure_inputs()` and `_build_volatility_inputs()` compute real sector_beta, realized_vol_30d, beta_to_spy — but these are stored only in `dimension_inputs` JSONB and never passed into the scorer. `_score_sector_exposure()` uses a hardcoded 5-value heuristic. `_score_volatility()` uses a metadata `volatility_proxy` field. Result: sector σ=2.02, 5 distinct values; volatility σ=7.74 but from proxy only. Both are silently degraded (not flagged as limited_data). Composite σ=4.18 → 98.8% BBB/BB.

---

## Execution Plan

### P0 — Fix now (code changes, no external deps)

| # | Fix | File(s) | Done-when |
|---|---|---|---|
| P0-A | Replace unentitled Polygon index tickers I:TNX→TLT, I:VIX→VIXY; use daily returns for all factors | `macro_regression.py` | All 5 FACTOR_TICKERS return 200 from Polygon |
| P0-B | Make Polygon auth-block ticker-scoped for index tickers (I:*); skip global block on index auth fail | `polygon.py` | One I:* 403 no longer blocks equity fetch_aggs |
| P0-C | Fix scheduler intraday tier: register per-user digest jobs before early-return | `scheduler.py` | `scheduler_jobs.next_run_at` in future after restart |
| P0-D | Add limited_data flag to sector/volatility input builders when real inputs absent | `ticker_cache_service.py` | `limited_data_dimensions` includes sector+vol when bars missing |
| P0-E | Wire real sector_beta/momentum/breadth into `_score_sector_exposure`; wire realized_vol/beta_to_spy into `_score_volatility` | `risk_scorer.py` + `ticker_cache_service.py` | Sector σ > 5, vol uses real inputs when present |
| P0-F | Pass sector_inputs + volatility_inputs into scoring_metadata so scorer receives real inputs | `ticker_cache_service.py` | Scorer sees `sector_inputs` and `volatility_inputs` keys |

### P1 — Fix after P0 (data truth + serving)

| # | Fix | File(s) | Done-when |
|---|---|---|---|
| P1-A | Re-run universe recompute (throttled canary: 10 tickers first, then full batch off-peak) | job trigger + verify | >480/504 real beta_to_spy and sector_beta |
| P1-B | Populate fcf_margin / interest_coverage or retire those FH rules | `ticker_cache_service.py` or fundamentals job | Input non-null >480, or rules removed |
| P1-C | Close Supabase RLS: enable RLS on `gnews_wrapper_resolution` | Supabase migration | No anon read on that table |
| P1-D | Revoke anon EXECUTE on two SECURITY DEFINER RPCs | Supabase migration | Supabase advisor shows 0 remaining |
| P1-E | Enable leaked-password protection in Supabase Auth | Supabase dashboard | Supabase advisor: enabled |
| P1-F | Drop or wire dead snapshot columns (generated_at, data_status, verification_status, is_product_visible, stale_after) | Migration | No dead columns in prod use |
| P1-G | Composite re-weighting: after dims are real, verify grade distribution spans ≥4 grades | `analysis_utils.py` if needed | σ > 8, ≥4 grades represented |

### P2 — App Store / iOS readiness

| # | Fix | File(s) | Done-when |
|---|---|---|---|
| P2-A | Remove stale `trycloudflare.com` ATS exception from Info.plist | `Info.plist` | ATS exception removed |
| P2-B | Audit ClavixVQAComponents.swift for mock values that must not ship in release | `ClavixVQAComponents.swift` | No static mock $ or grade values in non-debug paths |
| P2-C | Commit live legal/homepage sources into web/ | `web/` | getclavix.com pages match repo |
| P2-D | Soften "connect your brokerage" homepage copy (cut feature) | `web/index.html` | No broken promise of brokerage sync for V1 |
| P2-E | Add DMARC DNS record instructions (no credential needed) | `docs/` | Doc ready for when DNS access available |
| P2-F | Prepare custom SMTP config instructions for Supabase Auth | `docs/` | Step-by-step ready for when SMTP creds available |

### P3 — Blocked on external dependencies (prepare code/docs only)

| # | Fix | External dep | Action |
|---|---|---|---|
| P3-A | APNs push delivery | Apple Developer account + APNs key | Code ready; `APNS_ENABLED=false` env var; doc remaining steps |
| P3-B | StoreKit paywall | App Store Connect product creation | Create StoreKit config placeholder; mock paywall sheet is live |
| P3-C | TestFlight submission | Apple Developer enrollment | Doc checklist |
| P3-D | Custom SMTP for transactional email | SMTP provider credentials | Code path ready; doc provider options |
| P3-E | DMARC record | DNS access to getclavix.com | Write the exact TXT record to add |
| P3-F | GitHub Actions PROD_SSH_KEY secret | Repo settings access | Set `~/.ssh/clavix_vps_ed25519` as secret |

---

## What Must Wait for Me (External Setup)

1. **Apple Developer Program enrollment** → APNs key, TestFlight, App Store Connect, StoreKit products
2. **App Store Connect** → create `clavix_pro_monthly` and `clavix_pro_annual` subscription products
3. **APNs p8 key** → upload to VPS as `APNS_KEY_PATH`, set `APNS_ENABLED=true`
4. **SMTP provider** (Resend/Postmark/SES) → credentials → configure in Supabase Auth
5. **DNS access** → add `_dmarc.getclavix.com TXT "v=DMARC1; p=none; rua=mailto:support@getclavix.com"` + DKIM for SMTP provider
6. **GitHub repo settings** → set `PROD_SSH_KEY` secret for auto-deploy

---

## Post-Fix Verification Queries

```sql
-- Grade distribution should span ≥4 grades after recompute
WITH l AS (SELECT DISTINCT ON (ticker) ticker, composite_score, grade
  FROM ticker_risk_snapshots ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
SELECT grade, count(*), round(stddev_pop(composite_score),2) sigma
FROM l GROUP BY grade ORDER BY 1;

-- Dimension realness: target >480/504 for each
WITH l AS (SELECT DISTINCT ON (ticker) ticker, dimension_inputs, factor_breakdown
  FROM ticker_risk_snapshots ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
SELECT
  count(*) FILTER (WHERE (dimension_inputs->'volatility'->>'beta_to_spy') IS NOT NULL) vol_beta,
  count(*) FILTER (WHERE (dimension_inputs->'sector_exposure'->>'sector_beta') IS NOT NULL) sec_beta,
  count(*) FILTER (WHERE (factor_breakdown->'macro_regression'->>'limited_data')='false') macro_real
FROM l;

-- Digests must advance
SELECT user_id, last_run_at, next_run_at, last_run_status FROM scheduler_jobs WHERE notifications_enabled;
```

```bash
# Health check: expect apns:missing (until Apple Dev setup), all else configured, <200ms
curl -s -w "\n%{http_code} %{time_total}s\n" https://clavis.andoverdigital.com/health
```
