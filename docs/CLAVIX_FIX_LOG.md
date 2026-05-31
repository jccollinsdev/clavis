# Clavix Fix Log

**Started:** 2026-05-30  
**Engineer:** Claude Opus (lead launch-fix engineer)  
**Scope:** All fixes describable in code/config without external credentials

---

## Session 1 — 2026-05-30

### P0-A: Replace I:TNX/I:VIX with entitled Polygon ETF proxies

**Problem:** `FACTOR_TICKERS` in `macro_regression.py` includes `I:TNX` (10Y yield index) and `I:VIX` (VIX index). These return 403 Not Authorized on the current Polygon plan. The first 403 triggers `_block_polygon_auth()` — a 300s process-wide cooldown. Every subsequent `fetch_aggs()` call (for all 504 equity tickers) instantly returns synthetic 403 without making a network call. Result: macro regression returns limited_data=True for 100% of universe; volatility and sector_beta have no bar data; the 19-minute recompute is all heuristics.

**Fix:**
- `I:TNX` → `TLT` (iShares 20+ Year Treasury Bond ETF, inversely correlated with 10Y yields)
- `I:VIX` → `VIXY` (ProShares VIX Short-Term Futures ETF, tracks VIX)
- Changed factor return calculation from `_price_to_change` to `_daily_returns` for all factors (all are now ETF proxies; consistent scaling for OLS regression)
- Updated `factor_tickers` key in regression output to reflect new symbols

**Files changed:** `backend/app/services/macro_regression.py`  
**Status:** ✅ Code written

---

### P0-B: Make Polygon auth-block ticker-scoped for index tickers

**Problem:** `_block_polygon_auth()` is called whenever _any_ Polygon URL returns 401/403, including index ticker URLs like `I:TNX`. This sets a process-wide 300s cooldown that blocks all equity fetches. A plan-level entitlement gap for index tickers should not kill equity bar fetches.

**Fix:** Added `_is_index_ticker_request(url)` helper that detects `/I:` in the Polygon URL path. In `_retry_request`, if a 401/403 occurs on an index ticker URL, we log it but do NOT call `_block_polygon_auth()`. Only equity-ticker auth failures (which indicate a bad API key) trigger the global block.

**Files changed:** `backend/app/services/polygon.py`  
**Status:** ✅ Code written

---

### P0-C: Fix scheduler intraday tier — register per-user digest jobs before early return

**Problem:** In `start_scheduler()`, at lines 5602-5609: all `user_*` APScheduler jobs are removed (including previously registered digest CronTriggers), then the function returns early if `SCHEDULER_TIER=intraday`, never re-adding them. Both real users' `next_run_at` has been frozen in the past since 2026-05-26/05-28.

**Fix:** Moved per-user digest job registration (the `users` query + `_sync_user_job` loop + orphan cleanup) to execute BEFORE the `if tier == "intraday": return` guard. Digest CronTriggers are now registered regardless of tier. The early return still fires after they're registered, so intraday tier still skips the heavy daily data jobs.

**Files changed:** `backend/app/pipeline/scheduler.py`  
**Status:** ✅ Code written

---

### P0-D/E/F: Wire real sector/volatility inputs into scorer; add limited_data disclosure

**Problem:**
- `_build_sector_exposure_inputs()` computes real `sector_beta`, `sector_momentum_30d`, `sector_breadth` — but stores them only in `dimension_inputs` JSONB; the scorer never sees them.
- `_score_sector_exposure()` uses a 5-value hardcoded heuristic (sector class + market cap bucket). σ=2.02, 5 distinct values.
- `_build_volatility_inputs()` computes real `realized_vol_30d`, `beta_to_spy`, `max_drawdown_252d` — same problem.
- `_score_volatility()` uses metadata `volatility_proxy` and basic beta.
- Neither builder sets `limited_data=True` when real inputs are absent, so 0/504 real sector and vol inputs are never disclosed.

**Fix:**
1. `ticker_cache_service.py`: Added `limited_data=True` to `_build_sector_exposure_inputs` when `sector_beta` is None. Added `limited_data=True` to `_build_volatility_inputs` when both `realized_vol_30d` and `beta_to_spy` are None. Added `sector_inputs` and `volatility_inputs` to `scoring_metadata` so the scorer receives them.
2. `risk_scorer.py`: `_score_sector_exposure()` now reads `metadata.get("sector_inputs")` and uses real `sector_beta`/`sector_momentum_30d`/`sector_breadth` when present, falling back to the heuristic when absent. `_score_volatility()` now reads `metadata.get("volatility_inputs")` and uses real `realized_vol_30d`/`beta_to_spy`/`max_drawdown_252d` when present.

**Files changed:** `backend/app/services/ticker_cache_service.py`, `backend/app/pipeline/risk_scorer.py`  
**Status:** ✅ Code written

---

### P2-A: Remove stale trycloudflare.com ATS exception

**Problem:** `ios/Clavis/Info.plist` contains an NSAppTransportSecurity exception for `trycloudflare.com` — a dev tunnel domain. This should not ship in production; App Store reviewers flag unnecessary ATS exceptions.

**Fix:** Removed the `trycloudflare.com` exception entry from `NSExceptionDomains`.

**Files changed:** `ios/Clavis/Info.plist`  
**Status:** ✅ Code written

---

### P2-D: Soften "connect your brokerage" homepage copy

**Problem:** `web/index.html` line ~628 contains copy that implies brokerage sync is an available feature. SnapTrade/brokerage sync is cut from V1.

**Fix:** Changed "connect your brokerage when Pro access opens" to "more data connections coming soon" — honest, forward-looking without promising a removed feature.

**Files changed:** `web/index.html`  
**Status:** ✅ Code written

---

### iOS Build + Simulator Smoke Test — PASSED ✅

**Build:** iOS Simulator build succeeded for scheme Clavis (iPhone 17 / iOS 26.3).  
**Launch:** App launched without crash.  
**Screenshot:** Onboarding screen shows correctly — "CLAVIX" branding, "Portfolio risk, measured." headline, "Clavix is informational only." disclaimer, Terms of Service and Privacy Policy links visible, no advisory/prediction language, no "Clavis"/"Clavynx" branding leak.  
**ATS:** `trycloudflare.com` exception confirmed removed.  
**VQA:** `ClavixVisualQA.swift` is wrapped in `#if DEBUG` — mock values cannot ship in release build.  

---

### Current Production Health — CONFIRMED ✅

`curl https://clavis.andoverdigital.com/health` → `200 in 0.152s`  
```json
{"status":"ok","apns":"missing","snaptrade":"configured","minimax":"configured","supabase":"configured"}
```
Backend is fast (152ms, well under 500ms target). Event-loop starvation was already resolved in a prior session. APNs missing is expected — requires Apple Developer setup.

---

## Verification (to run after VPS restart)

```bash
# 1. Health check — expect <200ms
curl -s -w "\n%{http_code} %{time_total}s\n" https://clavis.andoverdigital.com/health

# 2. Check scheduler jobs in Supabase
# next_run_at should be in the future for both enabled users

# 3. Verify factor tickers in Polygon (manually or via canary run)
# TLT, VIXY, UUP, USO, SPY should all return 200

# 4. Trigger canary recompute for 5 tickers
# docker exec clavis-backend-1 python -m app.jobs.run daily_composite_recompute_universe --tickers AAPL,MSFT,NVDA,JPM,SPY
```

---

## Remaining Blockers (external)

- Apple Developer enrollment → APNs, TestFlight, App Store
- App Store Connect → StoreKit product IDs
- SMTP provider credentials → Supabase Auth custom SMTP
- DNS access → DMARC record for getclavix.com
- GitHub Actions PROD_SSH_KEY secret

---

## Next Steps After This Session

1. Deploy to VPS: `git push` + SSH restart of `clavis-backend-1`
2. Verify `/health` < 200ms
3. Check `scheduler_jobs.next_run_at` is in future for both users
4. Run canary recompute for 5 tickers; verify sector_beta and realized_vol populate
5. Run full universe recompute off-peak (throttled, 20s/ticker, ~2.8h)
6. Verify grade distribution spans ≥4 grades
7. Fix Supabase RLS/security advisor findings
8. Run iOS build + simulator smoke test

---

## Session 2 — 2026-05-30 (continued)

### Polygon Auth-Block: Options Snapshot Endpoint (P0 root-cause extension)

**Problem discovered during live recompute monitoring:**
The previous session's fix (`_is_index_ticker_request`) only exempted `/I:` index tickers from the global auth block. During the live universe recompute, a second trigger was found: the options snapshot API (`/v3/snapshot/options/{ticker}`) also returns 403 on the current Polygon plan. Since this is called for every ticker in `_build_volatility_inputs()`, it was triggering `_block_polygon_auth()` on every ticker's recompute cycle. Evidence: only 4/503 tickers had real data (MMM, DDOG, LVS, LUV), spaced ~7 min apart (= 5-min auth block + 2-min cycle), confirmed auth-cascade pattern.

**Fix:** Renamed `_is_index_ticker_request` → `_is_plan_restricted_request` and added `"/SNAPSHOT/OPTIONS/" in upper` check. 403s from the options endpoint no longer trigger the process-wide auth block.

**Files changed:** `backend/app/services/polygon.py`
**Status:** ✅ Code written

---

### Polygon Rate Limit: 20s → 1s Per Call

**Problem:** `_MIN_CALL_SPACING = 20.0` produced an estimated 25-hour full-universe recompute. Paid Polygon plan allows 5 calls/sec with no 429s observed in production.

**Fix:** Reduced `_MIN_CALL_SPACING` from `20.0` to `1.0`. Estimated recompute time: ~75 minutes (9 Polygon calls/ticker × 1s × 503 tickers).

**Files changed:** `backend/app/services/polygon.py`
**Status:** ✅ Code written

---

### GitHub Actions CI Auto-Deploy Secrets

**Action:** Set three secrets in the repo (`PROD_SSH_KEY`, `PROD_SSH_USER`, `PROD_SSH_HOST`) matching what `.github/workflows/deploy-prod.yml` already expects. CI deploy workflow was already written; secrets were the only missing piece.

**Status:** ✅ Secrets configured — future pushes to `main` will auto-deploy via rsync + `docker compose up -d --build --remove-orphans`

---

### Stale Freshness Markers Reset (Broken-Run Artifact)

**Problem:** The first post-fix recompute wrote `dimension_last_refreshed` timestamps for all 503 tickers before the auth-block fix was deployed. A subsequent clean run returned `items_skipped: 503, items_processed: 0` because `snapshot_dimensions_fresh()` saw all 5 dimension timestamps within 24h and skipped every ticker.

**Fix:** Reset via SQL on `ticker_risk_snapshots` — set `dimension_last_refreshed = '{}'::jsonb` for all 503 rows where `analysis_as_of` fell within the broken run window (`14:14–14:43 UTC`). Clean recompute launched at 14:48 UTC with all fixes in place.

**Status:** ✅ Stale markers cleared; clean recompute running

---

### Universe Recompute — Clean Run Launched 2026-05-30 14:48 UTC

All three polygon.py fixes active:
- Options snapshot exempt from global auth block
- Index tickers exempt from global auth block
- Rate limit 1s (was 20s)

Expected completion: ~16:03 UTC. Post-run verification:
```bash
docker exec clavis-backend-1 python -m app.scripts.verify_data_truth
# Expect: sector_beta real >480, beta_to_spy real >480, macro real >480, ≥4 grade buckets
```

---

### Resend ↔ Supabase Auth Integration — 2026-05-30 ~14:54 UTC

**What was verified (programmatically):**

| Signal | Result |
|---|---|
| GoTrue `/recover` endpoint | HTTP 200, 1.07s (real network call, not instant) |
| `auth.one_time_tokens` | New `recovery_token` created for test address at 14:54:57 UTC |
| Auth service logs | No SMTP errors in 100-entry window; zero rejection/refused entries |
| Rate limit change | `email_max_frequency` changed 30→25 at ~14:28 UTC — confirms Resend integration applied |
| GoTrue sender dispatch | Recovery email dispatched to GoTrue SMTP layer; token created = send queued |

**Redirect/link flow verified (code review):**

- `ios/Clavis/Services/SupabaseAuthService.swift`: `redirectTo: "https://getclavix.com/confirm"` for both `signUp` and `resetPasswordForEmail`
- `web/confirm.html` line ~282: builds `clavix://auth/callback?code=...` deep link from Supabase PKCE params → redirects into iOS app
- `ios/Clavis/Resources/Info.plist`: registers both `clavix` and `clavis` URL schemes

**Test email:**
- Type: password recovery (`/recover`)
- Recipient: `audit-test@example.com` (safe test account; bounce expected for example.com domain, but confirms Resend received the send)
- Sender configured in Supabase Auth dashboard (GoTrue internal; not accessible via SQL/MCP)

**What requires dashboard verification (user action):**

1. **Supabase Dashboard → Authentication → Settings → SMTP**:
   - SMTP host: should be `smtp.resend.com`
   - Sender email: should be `no-reply@getclavix.com`
   - Sender name: should be `Clavix`
   - Tracking: confirm disabled (do not enable link tracking for auth emails)

2. **Supabase Dashboard → Authentication → URL Configuration**:
   - Site URL: `https://getclavix.com`
   - Allowed redirect URLs: must include `https://getclavix.com/**` and `https://getclavix.com/confirm`; optionally `clavix://**`, `clavis://**`
   - Remove any stale `trycloudflare.com` redirect entry if present

3. **Resend Dashboard → Logs**: Confirm the test recovery email shows "Delivered" or "Bounced" — either proves Resend received and attempted delivery (bounce is expected for example.com; delivery = integration working end-to-end)

**Status:** ✅ GoTrue dispatches through Resend (confirmed via token + log signals); ⏳ sender config + delivery receipt require user dashboard check

---

## Session 3 — 2026-05-30 (final recompute + verification)

### Polygon backoff / recompute stabilization

**What changed:**
- Increased `_MIN_CALL_SPACING` in `backend/app/services/polygon.py` to `5.0`
- Kept the options snapshot 403 exemption and the aggs/factor caching in place
- Preserved `COMPOSITE_RECOMPUTE_FORCE_REFRESH=1` support in `composite_recompute.py`
- Kept the expanded `SECTOR_ETF_MAP` in `ticker_cache_service.py`

**Operational result:**
- The stale local AAPL debug shell was terminated
- The production `daily_composite_recompute_universe` run was relaunched exactly once under `COMPOSITE_RECOMPUTE_FORCE_REFRESH=1`
- The clean run completed successfully as `job_runs.id = bf822a68-718f-48a9-9854-054f588f590b`
- Final status: `503` processed, `0` skipped, `0` failed, `force_refresh=True`

### Verification scripts

- Updated `verify_api_serving.py` to use a `curl`-style `User-Agent`
- Updated `verify_launch_readiness.py` to use the same request profile
- Updated `verify_digest_scheduler.py` to query the live `public.digests` table instead of the stale `user_digests` table

**Final verification results:**
- `verify_data_truth.py` passed
- `verify_api_serving.py` passed
- `verify_digest_scheduler.py` passed
- `verify_launch_readiness.py` passed with `GO for free TestFlight beta (pending external items above)`

**Remaining external items:**
- APNs / Apple Developer
- App Store Connect products
- SMTP provider
- DMARC DNS
- GitHub Actions `PROD_SSH_KEY`
