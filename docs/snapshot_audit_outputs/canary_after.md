# Completeness Backfill Summary — canary-2026-05-27-rerun

- Started at: `2026-05-27T16:20:58.525608+00:00`
- Finished at: `2026-05-27T16:24:22.127556+00:00`
- Requested tickers: `3`
- Attempted tickers: `3`
- Completed tickers: `3`
- Failed tickers: `0`

## Before Audit

# Snapshot Completeness Audit

- Generated at: `2026-05-27T16:20:59.420059+00:00`
- Universe count: `3`
- Latest snapshot count: `3`
- Complete latest snapshot count: `0`
- Completeness-aware preferred latest count: `2`

## Core Counts

| Metric | Value |
| --- | --- |
| Universe count | 3 |
| Latest snapshot count | 3 |
| Complete 5D latest count | 0 |
| Missing composite_score | 0 |
| Missing valid grade | 0 |
| Methodology missing count | 2 |

## Dimension Gaps

| Dimension | Missing latest | Sample tickers | Legacy-only source | Likely persistence gap | Likely generation gap |
| --- | --- | --- | --- | --- | --- |
| financial_health | 0 | — | 0 | 0 | 0 |
| news_sentiment | 3 | HIMS, NVR, WBD | 0 | 3 | 0 |
| macro_exposure | 2 | NVR, WBD | 0 | 0 | 2 |
| sector_exposure | 0 | — | 0 | 0 | 0 |
| volatility | 0 | — | 0 | 0 | 0 |

## Latest Timestamp Summary

| Metric | Value |
| --- | --- |
| Min analysis_as_of | 2026-05-27T16:03:14.389898+00:00 |
| Median analysis_as_of | 2026-05-27T16:03:15.431551+00:00 |
| Max analysis_as_of | 2026-05-27T16:03:39.905087+00:00 |
| Stale >24h | 0 |
| Stale >48h | 0 |
| Stale >7d | 0 |

## Selection Integrity

| Finding | Count | Examples |
| --- | --- | --- |
| Duplicate same-day conflicts | 2 | NVR, WBD |
| Partial latest selected | 3 | HIMS, NVR, WBD |
| Older complete row exists | 2 | NVR, WBD |
| API selection mismatches | 2 | NVR, WBD |
| Structured limited rows selected | 0 | — |

## Snapshot Types

| Snapshot type | Latest row count |
| --- | --- |
| backfill | 3 |

## Recent Runs

- `2026-05-27T15:51:23.727424+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=1` `id=9ac29bb1-41cc-46e7-94b1-90c1bf9286f9`
- `2026-05-27T15:51:23.706031+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=ce93ad73-6bbe-475a-b554-da1ee9872058`
- `2026-05-24T17:26:05.421859+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=3` `id=e293893e-f37c-485e-b288-da0e5330774e`
- `2026-05-24T17:19:15.797642+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=d0dcf6f9-caa8-4f16-8c1a-c6d954cc0d52`
- `2026-05-24T17:19:15.781002+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=032d192d-065d-4ac2-95b8-1eb12b6072b2`
- `2026-05-24T17:11:03.150083+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=852d9bee-d74f-4b96-b96c-459f144df86d`
- `2026-05-24T17:11:03.134344+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=40f12294-1954-4e08-8ee4-c49e7512b20c`
- `2026-05-24T17:04:39.11702+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=a8559793-7235-4433-abb6-adc49eecf860`
- `2026-05-24T17:04:39.11395+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=f3ae6a5c-0d7d-4e5a-beed-5c9d3756728c`
- `2026-05-24T16:57:59.74884+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=0af15813-7b36-4249-a785-0139a9ac587f`

## After Audit

# Snapshot Completeness Audit

- Generated at: `2026-05-27T16:24:21.568109+00:00`
- Universe count: `3`
- Latest snapshot count: `3`
- Complete latest snapshot count: `3`
- Completeness-aware preferred latest count: `3`

## Core Counts

| Metric | Value |
| --- | --- |
| Universe count | 3 |
| Latest snapshot count | 3 |
| Complete 5D latest count | 3 |
| Missing composite_score | 0 |
| Missing valid grade | 0 |
| Methodology missing count | 2 |

## Dimension Gaps

| Dimension | Missing latest | Sample tickers | Legacy-only source | Likely persistence gap | Likely generation gap |
| --- | --- | --- | --- | --- | --- |
| financial_health | 0 | — | 0 | 0 | 0 |
| news_sentiment | 0 | — | 0 | 0 | 0 |
| macro_exposure | 0 | — | 0 | 0 | 0 |
| sector_exposure | 0 | — | 0 | 0 | 0 |
| volatility | 0 | — | 0 | 0 | 0 |

## Latest Timestamp Summary

| Metric | Value |
| --- | --- |
| Min analysis_as_of | 2026-05-27T16:23:57.804146+00:00 |
| Median analysis_as_of | 2026-05-27T16:23:57.805646+00:00 |
| Max analysis_as_of | 2026-05-27T16:24:20.873523+00:00 |
| Stale >24h | 0 |
| Stale >48h | 0 |
| Stale >7d | 0 |

## Selection Integrity

| Finding | Count | Examples |
| --- | --- | --- |
| Duplicate same-day conflicts | 2 | NVR, WBD |
| Partial latest selected | 0 | — |
| Older complete row exists | 0 | — |
| API selection mismatches | 0 | — |
| Structured limited rows selected | 1 | HIMS:news_sentiment |

## Snapshot Types

| Snapshot type | Latest row count |
| --- | --- |
| backfill | 3 |

## Recent Runs

- `2026-05-27T16:21:23.525755+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=2` `id=171b6437-e764-4d34-b326-ad304cc309d5`
- `2026-05-27T15:51:23.727424+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=1` `id=9ac29bb1-41cc-46e7-94b1-90c1bf9286f9`
- `2026-05-27T15:51:23.706031+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=ce93ad73-6bbe-475a-b554-da1ee9872058`
- `2026-05-24T17:26:05.421859+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=3` `id=e293893e-f37c-485e-b288-da0e5330774e`
- `2026-05-24T17:19:15.797642+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=d0dcf6f9-caa8-4f16-8c1a-c6d954cc0d52`
- `2026-05-24T17:19:15.781002+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=032d192d-065d-4ac2-95b8-1eb12b6072b2`
- `2026-05-24T17:11:03.150083+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=852d9bee-d74f-4b96-b96c-459f144df86d`
- `2026-05-24T17:11:03.134344+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=40f12294-1954-4e08-8ee4-c49e7512b20c`
- `2026-05-24T17:04:39.11702+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=a8559793-7235-4433-abb6-adc49eecf860`
- `2026-05-24T17:04:39.11395+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=f3ae6a5c-0d7d-4e5a-beed-5c9d3756728c`

## Run Summary

{
  "after": {
    "complete_5d_count": 3,
    "latest_snapshot_count": 3,
    "rows_marked_partial_selected_as_latest": []
  },
  "attempted_tickers": [
    "NVR",
    "WBD",
    "HIMS"
  ],
  "before": {
    "complete_5d_count": 0,
    "latest_snapshot_count": 3,
    "rows_marked_partial_selected_as_latest": [
      "HIMS",
      "NVR",
      "WBD"
    ]
  },
  "completed_tickers": [
    "HIMS",
    "NVR",
    "WBD"
  ],
  "failed_tickers": [],
  "finished_at": "2026-05-27T16:24:22.127556+00:00",
  "label": "canary-2026-05-27-rerun",
  "other_results": [
    {
      "snapshot_complete": true,
      "status": "completed",
      "ticker": "HIMS"
    }
  ],
  "requested_tickers": [
    "HIMS",
    "NVR",
    "WBD"
  ],
  "skipped_complete_tickers": [],
  "sp500_result": {
    "artifact_dir": "/Users/sansarkarki/Documents/Clavis/BACKFILL/171b6437-e764-4d34-b326-ad304cc309d5",
    "artifact_dirs": [
      "/Users/sansarkarki/Documents/Clavis/BACKFILL/171b6437-e764-4d34-b326-ad304cc309d5"
    ],
    "failed": [],
    "job_type": "backfill",
    "refreshed": 2,
    "requested": 2,
    "status": "ok"
  },
  "started_at": "2026-05-27T16:20:58.525608+00:00"
}
