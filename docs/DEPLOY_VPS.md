# VPS Deployment Guide

**Server:** DigitalOcean `134.122.114.241`  
**Service:** `clavis-backend-1` (Docker Compose)  
**Domain:** `clavis.andoverdigital.com` (via Cloudflare Tunnel)  
**SSH key:** `~/.ssh/clavix_vps_ed25519`

---

## Standard Deploy (after any backend code change)

```bash
# 1. Push changes to GitHub
git add -p   # stage selectively
git commit -m "fix: ..."
git push origin main

# 2. SSH to VPS
ssh -i ~/.ssh/clavix_vps_ed25519 root@134.122.114.241

# 3. Pull latest code
cd /opt/clavis
git pull origin main

# 4. Restart the backend container (graceful)
docker compose restart clavis-backend

# 5. Verify health (expect <500ms, status:ok)
curl -s -w "\n%{http_code} in %{time_total}s\n" https://clavis.andoverdigital.com/health

# 6. Check logs for startup errors
docker logs --tail 50 clavis-backend-1

# 7. Verify digest jobs registered (run this after restart)
docker exec clavis-backend-1 python -m app.scripts.verify_digest_scheduler
```

---

## After the P0 Fixes (2026-05-30 session)

The following fixes need a VPS deploy + restart to take effect:

### 1. Polygon index-ticker auth-fix (polygon.py)
No config change needed. The fix is in code. After restart, index ticker 403s will no longer poison equity fetches.

### 2. Macro factor tickers (macro_regression.py)
No config change needed. `I:TNX` → `TLT`, `I:VIX` → `VIXY`. These ETFs work on the current Polygon plan.

### 3. Digest scheduler fix (scheduler.py)
After restart, per-user digest CronTriggers will be registered immediately.  
**Verify with:**
```bash
docker exec clavis-backend-1 python -m app.scripts.verify_digest_scheduler
```
Expect both enabled users to show `next_run_at` in the future.

### 4. Sector/volatility scorer wiring (ticker_cache_service.py + risk_scorer.py)
No config change needed. The next universe recompute (weekday ~10:00 UTC) will use real inputs.

---

## Run a Canary Recompute (verify data fix works)

After deploy, trigger a canary batch of 5–10 tickers to verify the Polygon fix is working and real bar data flows through:

```bash
# On VPS — check if a canary recompute command exists
docker exec clavis-backend-1 python -m app.jobs.run daily_composite_recompute_universe --help

# Or trigger via the normal job for a small set (if --tickers flag is supported):
docker exec clavis-backend-1 python -m app.jobs.run daily_composite_recompute_universe

# Then verify bar data is flowing:
# In Supabase SQL editor:
# WITH l AS (SELECT DISTINCT ON (ticker) ticker, dimension_inputs, factor_breakdown
#   FROM ticker_risk_snapshots ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
# SELECT ticker,
#   (dimension_inputs->'volatility'->>'beta_to_spy') as beta,
#   (dimension_inputs->'sector_exposure'->>'sector_beta') as sec_beta,
#   (factor_breakdown->'macro_regression'->>'limited_data') as macro_limited
# FROM l WHERE ticker IN ('AAPL','MSFT','NVDA','JPM','SPY','XOM','TSLA')
# ORDER BY ticker;
# Expect: beta_to_spy non-null, sector_beta non-null, macro_limited = 'false'
```

---

## Apply Supabase Security Migration

```bash
# Option A: Supabase CLI
cd /opt/clavis  # or local repo
supabase db push   # pushes pending migrations

# Option B: Manual SQL (Supabase Dashboard → SQL Editor)
# Copy-paste: supabase/migrations/20260530_security_fixes.sql
# Run it. Verify with:
# SELECT relrowsecurity FROM pg_class WHERE relname = 'gnews_wrapper_resolution';
# -- expect: true
```

---

## Scheduler Tier Check

The VPS should be running with `SCHEDULER_TIER=intraday` (news/enrichment only in-process; heavy data jobs via external cron). Verify:

```bash
docker exec clavis-backend-1 printenv SCHEDULER_TIER
# Expected: intraday
# After the fix, intraday tier NOW also registers per-user digest CronTriggers.
```

If `SCHEDULER_TIER` is unset, it defaults to `cron` — this also works now (digest jobs register in both tiers).

---

## Environment Variables (current expected state)

| Var | Expected | Notes |
|---|---|---|
| `SCHEDULER_TIER` | `intraday` | news + digest; heavy jobs via external cron |
| `DISABLE_NEWS_ENRICHMENT` | unset (or `false`) | news enrichment should run |
| `APNS_ENABLED` | `false` or unset | waiting for Apple Dev account |
| `POLYGON_API_KEY` | set | current plan; I:TNX/I:VIX replaced with TLT/VIXY |
| `SUPABASE_URL` | set | production |
| `SUPABASE_SERVICE_ROLE_KEY` | set | backend service-role |
| `MINIMAX_API_KEY` | set | LLM enrichment |

---

## Pending External Setup (cannot unblock without credentials)

| Item | What to do | Unlocks |
|---|---|---|
| Apple Developer enrollment | enroll at developer.apple.com | APNs, TestFlight, App Store |
| APNs p8 key | generate in Apple Dev portal, upload to VPS, set `APNS_KEY_PATH` + `APNS_TEAM_ID` + `APNS_KEY_ID` + `APNS_ENABLED=true` | push delivery |
| App Store Connect products | create `clavix_pro_monthly` + `clavix_pro_annual` | StoreKit paywall |
| SMTP provider | Resend/Postmark/SES → configure in Supabase Auth → Settings → SMTP | reliable transactional email |
| DMARC DNS record | add `_dmarc.getclavix.com TXT "v=DMARC1; p=none; rua=mailto:support@getclavix.com"` | email deliverability |
| Leaked-password protection | Supabase Dashboard → Authentication → Providers → Email → Enable | security hardening |
| GitHub PROD_SSH_KEY | repo Settings → Secrets → Actions → add `~/.ssh/clavix_vps_ed25519` | auto-deploy on push |
