# Snapshot Completeness Audit

- Generated at: `2026-05-27T15:28:59.965683+00:00`
- Universe count: `504`
- Latest snapshot count: `504`
- Complete latest snapshot count: `497`
- Completeness-aware preferred latest count: `503`

## Core Counts

| Metric | Value |
| --- | --- |
| Universe count | 504 |
| Latest snapshot count | 504 |
| Complete 5D latest count | 497 |
| Missing composite_score | 7 |
| Missing valid grade | 0 |
| Methodology missing count | 8 |

## Dimension Gaps

| Dimension | Missing latest | Sample tickers | Legacy-only source | Likely persistence gap | Likely generation gap |
| --- | --- | --- | --- | --- | --- |
| financial_health | 1 | HIMS | 0 | 0 | 1 |
| news_sentiment | 7 | CFG, CINF, HIMS, NVR, NWSA, WBD, ZBRA | 6 | 4 | 3 |
| macro_exposure | 7 | CFG, CINF, HIMS, NVR, NWSA, WBD, ZBRA | 6 | 6 | 1 |
| sector_exposure | 1 | HIMS | 0 | 0 | 1 |
| volatility | 1 | HIMS | 0 | 0 | 1 |

## Latest Timestamp Summary

| Metric | Value |
| --- | --- |
| Min analysis_as_of | 2026-04-18T12:40:24.063675+00:00 |
| Median analysis_as_of | 2026-05-27T10:10:23.259756+00:00 |
| Max analysis_as_of | 2026-05-27T10:21:10.728073+00:00 |
| Stale >24h | 70 |
| Stale >48h | 7 |
| Stale >7d | 1 |

## Selection Integrity

| Finding | Count | Examples |
| --- | --- | --- |
| Duplicate same-day conflicts | 11 | AES, CFG, CINF, EQT, ETR, NVR, NWSA, SOLV, VLTO, WBD, ZBRA |
| Partial latest selected | 7 | CFG, CINF, HIMS, NVR, NWSA, WBD, ZBRA |
| Older complete row exists | 6 | CFG, CINF, NVR, NWSA, WBD, ZBRA |
| API selection mismatches | 6 | CFG, CINF, NVR, NWSA, WBD, ZBRA |
| Structured limited rows selected | 0 | — |

## Snapshot Types

| Snapshot type | Latest row count |
| --- | --- |
| backfill | 6 |
| daily | 497 |
| manual_refresh | 1 |

## Recent Runs

- `2026-05-24T17:26:05.421859+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=3` `id=e293893e-f37c-485e-b288-da0e5330774e`
- `2026-05-24T17:19:15.797642+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=d0dcf6f9-caa8-4f16-8c1a-c6d954cc0d52`
- `2026-05-24T17:19:15.781002+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=032d192d-065d-4ac2-95b8-1eb12b6072b2`
- `2026-05-24T17:11:03.150083+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=852d9bee-d74f-4b96-b96c-459f144df86d`
- `2026-05-24T17:11:03.134344+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=40f12294-1954-4e08-8ee4-c49e7512b20c`
- `2026-05-24T17:04:39.11702+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=a8559793-7235-4433-abb6-adc49eecf860`
- `2026-05-24T17:04:39.11395+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=f3ae6a5c-0d7d-4e5a-beed-5c9d3756728c`
- `2026-05-24T16:57:59.74884+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=0af15813-7b36-4249-a785-0139a9ac587f`
- `2026-05-24T16:57:59.736862+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=1e3697eb-3ab3-419b-8b75-5776ba3f414c`
- `2026-05-24T16:52:42.057331+00:00` `status=completed` `triggered_by=scheduled` `positions_processed=5` `id=8d74cf15-86f8-4ea4-978a-2425e81726ee`
