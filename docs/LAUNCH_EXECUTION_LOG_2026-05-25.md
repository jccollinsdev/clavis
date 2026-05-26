# Launch Execution Log — 2026-05-25

This file captures execution evidence gathered after the continuation audit moved into implementation.

## Local code/test fixes completed

- Commit: `5f079af55` — `fix: restore launch trust paths and green suite`
- Commit: `fa551273d` — `fix: honor scheduler pause in cron job runner`
- Commit: pending during execution window — Polygon auth short-circuit runtime fix
- Backend test result:
  - Command: `python3.11 -m pytest -q`
  - Result: `482 passed, 10 xfailed`
- Targeted scheduler/backfill runner tests:
  - Command: `python3.11 -m pytest tests/test_jobs_runner.py tests/test_p3_9_backfill.py tests/test_p8_jobs.py -q`
  - Result: `16 passed`
- Targeted Polygon runtime tests:
  - Command: `python3.11 -m pytest tests/test_polygon_service.py tests/test_p6_4_polygon_options.py tests/test_p6_5_macro_regression.py -q`
  - Result: `8 passed`
- iOS build result:
  - Command: `xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build`
  - Result: `BUILD SUCCEEDED`

## Trust-path fixes completed

- Canonical deep link support added alongside legacy compat:
  - `ios/Clavis/Resources/Info.plist`
  - `ios/Clavis/App/ClavisApp.swift`
  - `web/confirm.html`
  - `backend/app/config.py`
- APNs fallback title typo fixed:
  - `backend/app/services/apns.py`
- Daily/trading-date consistency corrected for:
  - `backend/app/routes/today.py`
  - `backend/app/pipeline/scheduler.py`

## Production scheduler verification evidence

- VPS reachable via SSH key `~/.ssh/clavix_vps_ed25519`
- Production host:
  - `hostname` -> `Clavix-Backend`
  - deployed repo commit -> `2c6a24d`
  - deployed git branch -> `backend/news-pipeline-candidate-ranking`
  - deployed worktree is dirty with many tracked modifications and deletions
- Cron install status:
  - `/etc/cron.d/clavix` was **absent**
  - `/etc/cron.d` contained only `.placeholder`, `e2scrub_all`, and `sysstat`
- Host timezone:
  - `timedatectl` -> `Etc/UTC`
- Production env flags inside container:
  - `SCHEDULER_TIER=None`
  - `PAUSE_SYSTEM_SCHEDULER=true`
  - `DISABLE_NEWS_ENRICHMENT=true`
- Job audit status:
  - `job_runs` query returned `0` rows
- Container logs still showed interval APScheduler activity from the currently deployed older build, including:
  - `_run_active_ticker_news_refresh`
  - `_run_bulk_sentiment_enrichment`
  - both skipping because `DISABLE_NEWS_ENRICHMENT` is set

## Immediate operational conclusions

- Production is **behind local main**.
- Production is **not a clean checkout of local main** and should not be overwritten casually.
- Production is **not** on the cron-enabled deployment path yet.
- Production scheduler freshness is **not proven**.
- The repo cron file had an ET/UTC assumption bug; it has now been corrected locally to UTC times matching the current VPS timezone.

## Live data tasks

- 10-ticker canary:
  - Started from local backend environment on 2026-05-25
  - Writes are hitting `shared_ticker_events` in Supabase
  - Mid-run evidence before stopping it to avoid overlap with backfill:
    - many `r.jina.ai` requests returned `451`
    - direct publisher fallback continued successfully for many URLs
    - MiniMax enrichment and Supabase upserts are executing
  - Last captured 7-day DB snapshot before stopping the run:
    - `AMD`: `13 total / 10 success / 4 usable`
    - `AAPL`: `9 total / 7 success / 1 usable`
    - `NVDA`: `12 total / 8 success / 3 usable`
    - `MSFT`: `12 total / 8 success / 3 usable`
    - `HOOD`: `14 total / 7 success / 1 usable`
    - `SMCI`: `13 total / 9 success / 2 usable`
    - `JPM`: `9 total / 8 success / 3 usable`
    - `XOM`: `11 total / 9 success / 1 usable`
    - `GOOGL`: `6 total / 4 success / 1 usable`
    - `META`: `3 total / 0 success / 0 usable`
  - Operational conclusion:
    - the news pipeline is real and writing live rows
    - the canary did **not** prove broad consistent 3-usable-articles coverage across all 10 names
- 14-day backfill:
  - validator prepared: `backend/scripts/validate_backfill_14d.py`
  - baseline evidence saved to `docs/backfill_validation_before_2026-05-25.json`
  - baseline result is **incomplete history**, not healthy history
    - sample tickers only show 10-12 of the expected 14 dates
    - universe daily coverage ranges from `0` to `136` rows instead of ~full-universe daily coverage
    - `2026-05-17` and `2026-05-18` currently have `0` rows
  - actual run started locally:
    - Command: `python3.11 -m app.jobs.run backfill_14d`
    - `job_runs.id`: `cdb6d5db-225f-4304-9f89-81b2d99cae8b`
    - observed status during this log update: `running`
  - observed runtime behavior:
    - repeated `Polygon auth error 403 for unknown`
    - local `POLYGON_API_KEY` is present, so this does **not** look like a missing-secret mistake
    - `unknown` in the log comes from `backend/app/services/polygon.py` logging a positional URL argument poorly; the `403` itself is still real
    - fresh writes were confirmed in `ticker_risk_snapshots` while the job ran, so this is a real long-running backfill, not a no-op
  - operational conclusion:
    - the backfill is **not** a quick verification step
    - provider readiness and runtime characteristics still need proof before launch

## Backfill rerun after runtime fix

- Root cause found during execution:
  - `backend/app/services/polygon.py` enforced a strict global 20s Polygon gate even after repeated `401/403` auth failures.
  - That made unauthorized Polygon access pathologically slow during `backfill_14d`.
- Runtime fix added locally:
  - after the first Polygon `401/403`, the process now temporarily short-circuits further Polygon calls instead of paying the 20s gate over and over
  - the auth log now prints the real URL instead of `unknown`
- Old run was stopped and closed out explicitly:
  - `job_runs.id`: `cdb6d5db-225f-4304-9f89-81b2d99cae8b`
  - final status: `failed`
  - reason: `aborted_after_polygon_auth_runtime_fix`
- Rerun started under the new client:
  - Command: `python3.11 -m app.jobs.run backfill_14d`
  - new `job_runs.id`: `8c8b50ee-c831-4e00-b153-295e3fa7e993`
  - first observed Polygon auth failure:
    - `Polygon auth error 403 for https://api.polygon.io/v2/aggs/ticker/I:TNX/range/1/day/2025-04-20/2026-05-25`
  - first observed improvement:
    - rerun stopped spamming repeated Polygon auth lines immediately after the first 403
    - rerun wrote roughly 10 fresh `ticker_risk_snapshots` rows for `2026-05-11` within a few minutes, materially faster than the earlier run
- Current state at last check:
  - rerun still `running`
  - later dates (`2026-05-17`, `2026-05-18`) still not repaired yet
