# Launch Execution Log — 2026-05-25

This file captures execution evidence gathered after the continuation audit moved into implementation.

## Local code/test fixes completed

- Commit: `5f079af55` — `fix: restore launch trust paths and green suite`
- Backend test result:
  - Command: `python3.11 -m pytest -q`
  - Result: `480 passed, 10 xfailed`
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
  - Early signal:
    - many `r.jina.ai` requests returned `451`
    - direct publisher fallback continued successfully for many URLs
    - MiniMax enrichment and Supabase upserts are executing
- 14-day backfill:
  - validator prepared: `backend/scripts/validate_backfill_14d.py`
  - baseline evidence saved to `docs/backfill_validation_before_2026-05-25.json`
  - baseline result is **incomplete history**, not healthy history
    - sample tickers only show 10-12 of the expected 14 dates
    - universe daily coverage ranges from `0` to `136` rows instead of ~full-universe daily coverage
    - `2026-05-17` and `2026-05-18` currently have `0` rows
  - the actual 14-day backfill run has not started yet in this execution window
  - sequencing choice: finish canary first, then run the backfill in isolation so evidence remains interpretable
