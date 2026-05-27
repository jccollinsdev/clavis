# Snapshot Completeness Audit

- Generated at: `2026-05-27T16:31:55.832635+00:00`
- Universe count: `504`
- Latest snapshot count: `504`
- Complete latest snapshot count: `504`
- Completeness-aware preferred latest count: `504`

## Core Counts

| Metric | Value |
| --- | --- |
| Universe count | 504 |
| Latest snapshot count | 504 |
| Complete 5D latest count | 504 |
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
| Min analysis_as_of | 2026-05-27T10:00:30.244519+00:00 |
| Median analysis_as_of | 2026-05-27T10:12:13.397733+00:00 |
| Max analysis_as_of | 2026-05-27T16:24:20.873523+00:00 |
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
| Structured limited rows selected | 1 | HIMS:news_sentiment |

## Snapshot Types

| Snapshot type | Latest row count |
| --- | --- |
| backfill | 7 |
| daily | 497 |

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
