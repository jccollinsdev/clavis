# Completeness Backfill Summary — repair-stuck-2026-05-28

- Started at: `2026-05-28T19:29:10.845840+00:00`
- Finished at: `2026-05-28T19:34:00.198806+00:00`
- Requested tickers: `6`
- Attempted tickers: `6`
- Completed tickers: `6`
- Failed tickers: `0`

## Before Audit

# Snapshot Completeness Audit

- Generated at: `2026-05-28T19:29:11.544175+00:00`
- Universe count: `6`
- Latest snapshot count: `6`
- Complete latest snapshot count: `6`
- Completeness-aware preferred latest count: `6`

## Core Counts

| Metric | Value |
| --- | --- |
| Universe count | 6 |
| Latest snapshot count | 6 |
| Complete 5D latest count | 6 |
| Missing composite_score | 0 |
| Missing valid grade | 0 |
| Methodology missing count | 6 |

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
| Min analysis_as_of | 2026-05-27T15:55:59.908020+00:00 |
| Median analysis_as_of | 2026-05-27T16:03:13.834733+00:00 |
| Max analysis_as_of | 2026-05-27T16:23:57.805646+00:00 |
| Stale >24h | 6 |
| Stale >48h | 0 |
| Stale >7d | 0 |

## Selection Integrity

| Finding | Count | Examples |
| --- | --- | --- |
| Duplicate same-day conflicts | 6 | CFG, CINF, NVR, NWSA, WBD, ZBRA |
| Partial latest selected | 0 | — |
| Older complete row exists | 0 | — |
| API selection mismatches | 0 | — |
| Structured limited rows selected | 0 | — |

## Snapshot Types

| Snapshot type | Latest row count |
| --- | --- |
| backfill | 6 |

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

## After Audit

# Snapshot Completeness Audit

- Generated at: `2026-05-28T19:33:59.437051+00:00`
- Universe count: `6`
- Latest snapshot count: `6`
- Complete latest snapshot count: `6`
- Completeness-aware preferred latest count: `6`

## Core Counts

| Metric | Value |
| --- | --- |
| Universe count | 6 |
| Latest snapshot count | 6 |
| Complete 5D latest count | 6 |
| Missing composite_score | 0 |
| Missing valid grade | 0 |
| Methodology missing count | 6 |

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
| Min analysis_as_of | 2026-05-28T19:31:40.089126+00:00 |
| Median analysis_as_of | 2026-05-28T19:33:54.360821+00:00 |
| Max analysis_as_of | 2026-05-28T19:33:55.937349+00:00 |
| Stale >24h | 0 |
| Stale >48h | 0 |
| Stale >7d | 0 |

## Selection Integrity

| Finding | Count | Examples |
| --- | --- | --- |
| Duplicate same-day conflicts | 6 | CFG, CINF, NVR, NWSA, WBD, ZBRA |
| Partial latest selected | 0 | — |
| Older complete row exists | 0 | — |
| API selection mismatches | 0 | — |
| Structured limited rows selected | 0 | — |

## Snapshot Types

| Snapshot type | Latest row count |
| --- | --- |
| backfill | 6 |

## Recent Runs

- `2026-05-28T19:29:27.19309+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=1` `id=ae538531-1d42-41cd-b6b9-e8f047cd4fe4`
- `2026-05-28T19:29:27.191491+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=52a29401-08e2-4bbb-bf2e-e435bce44fd8`
- `2026-05-27T16:21:23.525755+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=2` `id=171b6437-e764-4d34-b326-ad304cc309d5`
- `2026-05-27T15:51:23.727424+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=1` `id=9ac29bb1-41cc-46e7-94b1-90c1bf9286f9`
- `2026-05-27T15:51:23.706031+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=ce93ad73-6bbe-475a-b554-da1ee9872058`
- `2026-05-24T17:26:05.421859+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=3` `id=e293893e-f37c-485e-b288-da0e5330774e`
- `2026-05-24T17:19:15.797642+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=d0dcf6f9-caa8-4f16-8c1a-c6d954cc0d52`
- `2026-05-24T17:19:15.781002+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=032d192d-065d-4ac2-95b8-1eb12b6072b2`
- `2026-05-24T17:11:03.150083+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=852d9bee-d74f-4b96-b96c-459f144df86d`
- `2026-05-24T17:11:03.134344+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=40f12294-1954-4e08-8ee4-c49e7512b20c`

## Run Summary

{
  "after": {
    "complete_5d_count": 6,
    "latest_snapshot_count": 6,
    "rows_marked_partial_selected_as_latest": []
  },
  "attempted_tickers": [
    "CFG",
    "CINF",
    "NVR",
    "NWSA",
    "WBD",
    "ZBRA"
  ],
  "before": {
    "complete_5d_count": 6,
    "latest_snapshot_count": 6,
    "rows_marked_partial_selected_as_latest": []
  },
  "completed_tickers": [
    "CFG",
    "CINF",
    "NVR",
    "NWSA",
    "WBD",
    "ZBRA"
  ],
  "failed_tickers": [],
  "finished_at": "2026-05-28T19:34:00.198806+00:00",
  "label": "repair-stuck-2026-05-28",
  "other_results": [],
  "requested_tickers": [
    "CFG",
    "CINF",
    "NVR",
    "NWSA",
    "WBD",
    "ZBRA"
  ],
  "skipped_complete_tickers": [],
  "sp500_result": {
    "artifact_dir": "/Users/sansarkarki/Documents/Clavis/BACKFILL/ae538531-1d42-41cd-b6b9-e8f047cd4fe4",
    "artifact_dirs": [
      "/Users/sansarkarki/Documents/Clavis/BACKFILL/52a29401-08e2-4bbb-bf2e-e435bce44fd8",
      "/Users/sansarkarki/Documents/Clavis/BACKFILL/ae538531-1d42-41cd-b6b9-e8f047cd4fe4"
    ],
    "failed": [],
    "job_type": "backfill",
    "refreshed": 6,
    "requested": 6,
    "status": "ok"
  },
  "started_at": "2026-05-28T19:29:10.845840+00:00"
}
