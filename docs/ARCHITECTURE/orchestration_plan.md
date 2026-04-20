# Clavis — Backend Job Orchestration Plan

**Last updated:** 2026-04-19

## Overview

The backend uses APScheduler (AsyncIO mode) embedded directly in the FastAPI process.
All scheduled work is registered at startup and persisted through server restarts via Supabase.
There is no separate queue service — jobs run as asyncio tasks inside the single backend container.

---

## How The Scheduler Boots

`start_scheduler()` is called from the FastAPI `lifespan` hook on every container start.

On boot it:
1. Marks any stale runs (`queued`/`running` older than 1 hour) as `failed`
2. Marks any runs that started before this process as `failed` (orphan cleanup)
3. Starts APScheduler if not already running
4. Registers the S&P 500 daily refresh system job (3:00 AM UTC)
5. Re-reads `user_preferences` from Supabase and re-registers all per-user digest and structural refresh jobs

**Result:** Jobs survive server restarts — they are re-seeded from the DB every time the container starts.

---

## Job Types And Schedule

### 1. S&P 500 Shared Cache Daily Refresh
**Job ID:** `system_sp500_daily_refresh`
**Trigger:** Every day at 3:00 AM UTC
**Function:** `refresh_sp500_cache(job_type="daily")`
**What it does:**
- Pulls fresh price/structural data for all ~503 tracked S&P tickers from Finnhub
- Recomputes structural base scores (no full AI pipeline, no news)
- Upserts `ticker_risk_snapshots` in Supabase (the shared cache)
- All users reading ticker detail or adding holdings see fresh data without individual analysis runs

**Cost:** Finnhub API calls only, no MiniMax. Fast (~minutes for full S&P).

---

### 2. Per-User Structural Refresh
**Job ID:** `user_{user_id}_structural_refresh`
**Trigger:** Every day at 6:30 AM UTC (hardcoded)
**Function:** `trigger_structural_refresh(user_id)`
**What it does:**
- For each of the user's positions, fetches the latest price and recomputes the structural score
- Uses `score_position_structural()` — deterministic, no AI
- Updates `risk_scores` with the fresh structural score
- Does NOT produce a digest or send notifications

**Purpose:** Ensures positions have a fresh score even on days when the full AI digest doesn't run
(e.g. user has digest disabled, or as a pre-digest price refresh before 7:00 AM).

**Gap to address:** Structural refresh is hardcoded at 6:30 AM regardless of the user's digest time.
If a user sets their digest to 5:00 AM, structural data is 1.5 hours stale when the digest runs.
**Fix:** Schedule structural refresh at `digest_time - 30 minutes` instead of hardcoded 6:30.

---

### 3. Per-User Daily Digest (Full AI Pipeline)
**Job ID:** `user_{user_id}`
**Trigger:** Daily at the user's `digest_time` preference (default: 7:00 AM UTC)
**Function:** `trigger_scheduled_digest(user_id)`
**Only runs if:** `notifications_enabled = true` in `user_preferences`

**What it does (full pipeline):**
```
RSS + Finnhub + GNews
        ↓
  normalize_news_batch()         [dedupe, evidence quality tagging]
        ↓
  enrich company articles        [scrape publisher pages via jina.ai proxy]
        ↓
  classify_relevance()           [LLM: is this relevant to the user's tickers?]
        ↓
  agentic_scan / event analysis  [LLM: what happened, significance, implications]
        ↓
  score_position()               [LLM + structural: final risk score + grade]
        ↓
  compile_portfolio_digest()     [LLM: morning summary for the user]
        ↓
  notify_digest()                [APNs push notification]
        ↓
  alert fanout                   [grade changes → alerts table → push]
```

**Timeout:** 25 minutes (`RUN_TIMEOUT_SECONDS`). If exceeded, partial results are saved and status set to `partial`.
**Concurrency:** `POSITION_CONCURRENCY = 2` (two positions analyzed in parallel per run).

---

### 4. S&P 500 Full AI Backfill
**Trigger:** Manual only (no automatic cron)
**Entry points:**
- Admin API: `POST /scheduler/sp500-backfill/enqueue` → returns `run_id`, runs as background task
- CLI: `python -m app.scripts.sp500_backfill start` inside container → detached subprocess

**What it does:**
- Full AI pipeline for all ~503 S&P tickers (or a subset)
- Chunked into batches of 10 tickers to avoid the 25-min scheduler timeout
- Each batch creates its own `analysis_run` row; a master controller row tracks overall progress
- Writes to `ticker_risk_snapshots` — the shared cache that all users read

**When to run:**
- On first deployment (seed all tickers)
- After significant pipeline changes (re-score everything with new logic)
- Weekly cadence is reasonable once the pipeline is stable

**Planned improvement:** Add a weekly cron for the full backfill (Sunday 2:00 AM UTC) so the shared cache
stays fresh with AI scoring even without manual intervention.

---

## Current Gaps And Planned Fixes

| Gap | Impact | Fix |
|---|---|---|
| Structural refresh hardcoded at 6:30 AM | Stale data for users with early digest times | Schedule at `digest_time - 30min` |
| No weekly S&P full AI backfill cron | Shared cache degrades without manual runs | Add `CronTrigger(day_of_week='sun', hour=2)` |
| `refresh_sp500_cache` at 3 AM is fire-and-forget `create_task` | Errors are silently swallowed | Wrap in proper error capture, log to Sentry |
| No per-user backfill for non-S&P tickers | User-added tickers (e.g. crypto, small caps) miss shared cache | Auto-onboard on `POST /holdings` via `refresh_ticker_snapshot` (partially done) |
| Failed scheduled jobs have no external alert | Silent failures until user notices missing digest | Sentry alert on `last_run_status = failed` or UptimeRobot webhook |

---

## Job Registration Flow (When User Changes Preferences)

```
PATCH /preferences  →  _sync_user_job(supabase, user_id, digest_time, notifications_enabled)
                              ↓
                    Remove existing user job from APScheduler
                              ↓
                    if notifications_enabled:
                      Add digest cron job at user's time
                      Add structural refresh job at 6:30 AM
                    else:
                      Mark scheduler_jobs row inactive
```

---

## Monitoring And Observability

- **UptimeRobot** pings `/health` every 5 minutes — alerts if backend goes down
- **Sentry** captures unhandled exceptions from the FastAPI process
- **`scheduler_jobs` table** — per-user last run status, last error, next run time (queryable from iOS settings)
- **`analysis_runs` table** — full audit trail for every run, with stage-level progress messages
- **BACKFILL_IMPORT/** — local artifact captures for every instrumented backfill run (debug only)

---

## VPS Deployment Notes

On the DigitalOcean droplet, the scheduler runs inside the `clavis-backend-1` container.
APScheduler uses asyncio event loop — it runs in the same process as FastAPI.
No external task queue (Celery, Redis) is needed at this scale.

The recommended sequence after `docker compose up -d` on a fresh VPS:
1. Verify `/health` returns `{"status": "ok"}`
2. Check `docker logs clavis-backend-1` for `start_scheduler` log lines
3. Confirm S&P daily job is registered: `GET /scheduler/status` (admin endpoint)
4. Manually trigger a small S&P backfill to seed the shared cache: `python -m app.scripts.sp500_backfill start --limit 10`
5. Confirm UptimeRobot is pointing to the VPS IP (not the old local tunnel)
