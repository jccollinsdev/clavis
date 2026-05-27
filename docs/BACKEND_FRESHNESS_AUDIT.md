# Backend Freshness Audit

This repo snapshot did not contain the original `docs/BACKEND_FRESHNESS_AUDIT.md` file referenced in the May 27, 2026 recovery prompt. This document reconstructs the relevant baseline findings from that prompt and records the recovery addendum below.

## Reconstructed Baseline Findings

- Latest snapshot completeness was materially broken.
- Latest tracked-universe completeness was reported as `6 / 504` in the external audit summary that triggered this recovery.
- The repo-connected live audit at the start of this recovery measured `497 / 504` latest snapshots as schema-complete and proved the remaining breakage was concentrated in newer partial latest rows.
- The critical remaining gaps at recovery start were:
  - missing `news_sentiment` on `7` latest rows
  - missing `macro_exposure` on `7` latest rows
  - missing `composite_score` on `7` latest rows
  - `6` cases where an older same-day complete row existed but a newer partial row was being selected as latest
- APNs health was not part of the blocking path for snapshot completeness.

## Addendum — 2026-05-27 Snapshot Completeness Recovery

### What changed since `f808c7180`

- Added a read-only snapshot completeness auditor:
  - `backend/app/scripts/audit_snapshot_completeness.py`
- Added a resumable snapshot completeness repair runner:
  - `backend/app/scripts/backfill_snapshot_completeness.py`
- Fixed canonical snapshot sync persistence in:
  - `backend/app/pipeline/scheduler.py`
- Fixed latest snapshot selection to prefer schema-complete rows in:
  - `backend/app/services/ticker_cache_service.py`
- Added honest structured limited-data handling for sparse news cases in:
  - `backend/app/services/ticker_cache_service.py`
- Updated methodology reads to use completeness-aware latest selection and expose limited-data reasons in:
  - `backend/app/routes/methodology.py`
- Added regression coverage for canonical sync, completeness-aware latest selection, and limited-data methodology surfacing.

### Root cause resolved

Two bugs were driving the latest-snapshot truth failure.

1. `scheduler.py::_sync_ai_scores_to_ticker_snapshots_sync(...)` was still relying on legacy field names instead of the canonical `news_sentiment_dim` and `macro_exposure_dim` columns used by live snapshots.
2. Latest-row selection was timestamp-first and allowed a newer partial row to outrank an older schema-complete row.

Additionally, sparse-news cases like `HIMS` were missing structured limited-data metadata, which made an honest null dimension look like a silent data hole.

### Latest completeness after recovery

- Tracked universe count: `504`
- Latest snapshot count: `504`
- Schema-complete latest snapshots: `504 / 504`
- Missing `news_sentiment` without structured limited reason: `0`
- Missing `macro_exposure` without structured limited reason: `0`
- Missing `composite_score`: `0`
- Missing valid grade: `0`
- Partial latest rows selected as authoritative: `0`

### Current limited rows

- `HIMS`
  - limited dimension: `news_sentiment`
  - reason: fewer than 3 recent shared ticker events in the 7-day scoring window

### Previous blockers resolved?

- Latest snapshot completeness blocker: resolved
- News persistence blocker: resolved
- Macro persistence blocker: resolved
- Partial-latest selection blocker: resolved
- Honest limited-data representation blocker: resolved

### Remaining blockers

- Snapshot completeness blocker: none
- Broader product-truth blocker still outstanding:
  - active tracked universe remains effectively S&P 500 breadth rather than the broader Clavix Truth universe target

### Supporting artifacts

- `docs/snapshot_audit_outputs/latest_snapshot_completeness_before.md`
- `docs/snapshot_audit_outputs/canary_after.md`
- `docs/snapshot_audit_outputs/full_after.md`
- `docs/snapshot_audit_outputs/full_backfill_summary.md`
- `docs/snapshot_audit_outputs/endpoint_after.md`
- `docs/SNAPSHOT_COMPLETENESS_RECOVERY.md`
