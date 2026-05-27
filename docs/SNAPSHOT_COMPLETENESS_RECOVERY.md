# Snapshot Completeness Recovery

## Scope

- Date: `2026-05-27`
- Starting branch: `main`
- Starting tip: `ab40a270c`
- Repo note: a large pre-existing untracked `BACKFILL/` tree was already present and was left intact.
- Missing prompt-referenced files at session start:
  - `docs/BACKEND_FRESHNESS_AUDIT.md`
  - `whatimdoing.md`
  - `docs/screenshots/post-uiparity/PARITY_DIFF.md`

## Root Cause

Snapshot completeness was failing for two distinct reasons.

1. Canonical persistence mismatch in the AI snapshot sync path.
   - `backend/app/pipeline/scheduler.py::_sync_ai_scores_to_ticker_snapshots_sync(...)` was still treating legacy/top-level `news_sentiment` and `macro_exposure` as authoritative fallback keys.
   - The live canonical snapshot schema uses `news_sentiment_dim` and `macro_exposure_dim`.
   - Result: newer `backfill` rows for `CFG`, `CINF`, `NVR`, `NWSA`, `WBD`, and `ZBRA` were written without canonical news/macro/composite fields even though older same-day complete rows existed.

2. Latest-row selection did not prefer schema-complete rows.
   - `backend/app/services/ticker_cache_service.py` selected latest rows timestamp-first.
   - Result: those newer partial rows became the authoritative “latest” snapshot and flowed into ticker detail and methodology reads.

3. Honest limited-data metadata was missing for sparse-news cases.
   - `backend/app/services/ticker_cache_service.py::refresh_ticker_snapshot(...)` could leave `news_sentiment_dim = null` without structured limited-data metadata.
   - Result: `HIMS` was a real sparse-data case, but it looked like a missing field instead of an explicitly limited dimension.

## Code Changes Made

### Diagnostics and recovery scripts

- Added `backend/app/scripts/audit_snapshot_completeness.py`
  - Read-only audit for universe breadth, latest snapshot integrity, dimension gaps, stale rows, duplicate-latest conflicts, older-complete-vs-newer-partial cases, and API selection mismatches.
- Added `backend/app/scripts/backfill_snapshot_completeness.py`
  - Resumable completeness repair runner with `--tickers`, `--dry-run`, `--limit`, `--resume`, `--force`, per-ticker logging, and markdown/JSON output.

### Snapshot selection and completeness guards

- Updated `backend/app/services/ticker_cache_service.py`
  - Added schema-completeness helpers and canonical dimension validation.
  - Latest snapshot history/map selection now prefers schema-complete rows over newer partial rows.
  - Added graceful fallback for lightweight test doubles that do not implement PostgREST `.in_(...)`.
  - Added structured limited-data reasons for sparse `news_sentiment` and limited `macro_exposure`.
  - `refresh_ticker_snapshot(...)` now persists `limited_data_dimensions` when a dimension is honestly limited.

### Canonical sync persistence fix

- Updated `backend/app/pipeline/scheduler.py`
  - `_sync_ai_scores_to_ticker_snapshots_sync(...)` now reads canonical source snapshots and writes canonical fields:
    - `news_sentiment_dim`
    - `macro_exposure_dim`
    - `composite_score`
    - `dimension_inputs`
    - `dimension_last_refreshed`
    - `limited_data_dimensions`
  - If no schema-complete source snapshot exists, the sync now refuses to treat the row as a valid publish source.

### Methodology endpoint truthfulness

- Updated `backend/app/routes/methodology.py`
  - Methodology now uses the same completeness-aware latest snapshot selector.
  - Methodology responses now surface `limited_data` and `limited_reason` for dimensions such as sparse-news `news_sentiment`.

### Tests

- Added and updated coverage in:
  - `backend/tests/test_scheduler_jobs.py`
  - `backend/tests/test_ticker_detail_state.py`
  - `backend/tests/test_p6_methodology_depth.py`
  - `backend/tests/test_news_cache_freshness.py`

## Before / After

### Full tracked universe

| Metric | Before | After |
| --- | --- | --- |
| Universe count | 504 | 504 |
| Latest snapshot count | 504 | 504 |
| Complete latest snapshot count | 497 | 504 |
| Completeness-aware preferred latest count | 503 | 504 |
| Missing `news_sentiment` without reason | 7 | 0 |
| Missing `macro_exposure` without reason | 7 | 0 |
| Missing `composite_score` | 7 | 0 |
| Missing valid `grade` | 0 | 0 |
| Partial latest selected | 7 | 0 |
| API selection mismatches | 6 | 0 |
| Structured limited rows selected | 0 | 1 (`HIMS:news_sentiment`) |

### Canary repair set

Initial broad canary work confirmed most large-cap names were already fine after the selector/persistence fix. The final targeted repair canary focused on the remaining broken latest rows:

- `HIMS`
- `NVR`
- `WBD`

Targeted rerun result:

| Metric | Before | After |
| --- | --- | --- |
| Requested tickers | 3 | 3 |
| Complete latest snapshot count | 0 | 3 |
| Missing `news_sentiment` without reason | 3 | 0 |
| Missing `macro_exposure` without reason | 2 | 0 |
| Partial latest selected | 3 | 0 |
| API selection mismatches | 2 | 0 |
| Failed tickers | — | 0 |

## Backfill Commands Run

### Before audit

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.audit_snapshot_completeness \
  --output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/latest_snapshot_completeness_before.md \
  --json-output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/latest_snapshot_completeness_before.json
```

### Canary dry run

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.backfill_snapshot_completeness \
  --tickers AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,JNJ,UNH,SPY,CFG,CINF,HIMS,NVR,NWSA,WBD,ZBRA \
  --dry-run \
  --label canary-2026-05-27
```

### Final targeted canary repair

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.backfill_snapshot_completeness \
  --tickers NVR,WBD,HIMS \
  --label canary-2026-05-27-rerun \
  --output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/canary_after.md \
  --json-output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/canary_after.json
```

### Full post-fix audit

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.audit_snapshot_completeness \
  --page-size 100 \
  --output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_after.md \
  --json-output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_after.json
```

### Full universe no-op completeness backfill verification

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.backfill_snapshot_completeness \
  --label full-2026-05-27 \
  --output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_backfill_summary.md \
  --json-output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_backfill_summary.json
```

## Audit Artifacts

- `docs/snapshot_audit_outputs/latest_snapshot_completeness_before.md`
- `docs/snapshot_audit_outputs/latest_snapshot_completeness_before.json`
- `docs/snapshot_audit_outputs/canary_after.md`
- `docs/snapshot_audit_outputs/canary_after.json`
- `docs/snapshot_audit_outputs/full_after.md`
- `docs/snapshot_audit_outputs/full_after.json`
- `docs/snapshot_audit_outputs/full_backfill_summary.md`
- `docs/snapshot_audit_outputs/full_backfill_summary.json`
- `docs/snapshot_audit_outputs/endpoint_after.md`

## Endpoint Verification

Verified via app code against the configured live Supabase environment using a signed test JWT and `fastapi.testclient.TestClient`.

General endpoints:

- `/tickers/search?q=AAPL&limit=3` -> `200`
- `/holdings` -> `200`
- `/digest` -> `200`
- `/alerts` -> `200`

Representative tickers verified:

- `AAPL`
- `MSFT`
- `NVDA`
- `JPM`
- `XOM`
- `JNJ`
- `HIMS`

Results:

- All verified supported tickers returned five-dimension methodology payloads with consistent dimension scores.
- For `AAPL`, `MSFT`, `NVDA`, `JPM`, `XOM`, and `JNJ`, detail composite score matched the equal-weight average of the five live dimensions.
- `HIMS` now reports an honest sparse-data case:
  - detail endpoint returns `news_sentiment = null`
  - methodology endpoint returns a structured limited reason:
    - `Only 0 shared ticker event(s) were available in the last 7 days; at least 3 are required for a scored news sentiment dimension.`
  - composite score remains honest and is computed from the available dimensions only.
- `SPY` remains unsupported by `/tickers/SPY` and returns `400`; this did not block tracked-universe completeness because it is not part of the active supported universe for ticker detail.

## Test Results

Focused changed coverage:

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m pytest -q \
  tests/test_p6_5_macro_regression.py \
  tests/test_p6_methodology_depth.py \
  tests/test_ticker_detail_state.py \
  tests/test_scheduler_jobs.py \
  tests/test_news_cache_freshness.py
```

Result:

- `58 passed, 10 xfailed`

Full backend suite:

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m pytest -q
```

Result:

- `489 passed, 10 xfailed`

Note on environment-sensitive noise:

- Running the full suite with `backend/.env` sourced causes `tests/test_jobs_runner.py` to fail because `backend/.env` currently sets `PAUSE_SYSTEM_SCHEDULER=true`.
- The clean suite run without sourcing `.env` passed.

## iOS Verification

Build command:

```bash
xcodebuild -project /Users/sansarkarki/Documents/Clavis/ios/Clavis.xcodeproj \
  -scheme Clavis \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  build
```

Result:

- `BUILD SUCCEEDED`

Additional grep checks:

```bash
rg 'Color\.clavix' /Users/sansarkarki/Documents/Clavis/ios/Clavis/ || true
rg '\.capitalized' /Users/sansarkarki/Documents/Clavis/ios/Clavis/Views/ | grep -v '^.*//.*' || true
```

Findings:

- `Color.clavix` usage exists broadly across the current iOS UI, as expected.
- One live `.capitalized` use remains in `ios/Clavis/Views/Tickers/ArticleDetailSheet.swift` for article-tag display text; it was not part of this backend completeness recovery.

## Current State

- Latest tracked-universe snapshot completeness: `504 / 504`
- Latest tracked-universe `news_sentiment` completeness without silent gaps: `504 / 504`
- Latest tracked-universe `macro_exposure` completeness without silent gaps: `504 / 504`
- Latest tracked-universe `composite_score` completeness: `504 / 504`
- Latest tracked-universe valid grade completeness: `504 / 504`

Tickers still using structured limited data:

- `HIMS`
  - limited dimension: `news_sentiment`
  - reason: insufficient recent shared ticker events

## Remaining Blockers

Snapshot completeness is no longer blocked.

Separate from this recovery, one Truth-level gap still remains:

- The active tracked universe is still effectively S&P 500 breadth (`504` active, `503` tagged `SP500`) and does not yet satisfy the broader Clavix Truth target for universe breadth.

## Rerun Commands

### Re-run the full audit

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.audit_snapshot_completeness \
  --page-size 100 \
  --output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_after.md \
  --json-output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_after.json
```

### Re-run a targeted repair

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.backfill_snapshot_completeness \
  --tickers HIMS,NVR,WBD \
  --resume \
  --label rerun-2026-05-27 \
  --output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/rerun.md \
  --json-output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/rerun.json
```

### Re-run the full-universe completeness pass

```bash
cd /Users/sansarkarki/Documents/Clavis/backend
python3.11 -m app.scripts.backfill_snapshot_completeness \
  --resume \
  --label full-rerun-2026-05-27 \
  --output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_rerun.md \
  --json-output /Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/full_rerun.json
```

## Release Assessment

- Snapshot-completeness gate: passed.
- Live-data honesty for the tracked universe: passed.
- TestFlight safe from the specific snapshot-completeness blocker: yes.
- TestFlight fully aligned with the broader Clavix Truth universe-breadth promise: not yet, because breadth is still effectively S&P 500 only.
