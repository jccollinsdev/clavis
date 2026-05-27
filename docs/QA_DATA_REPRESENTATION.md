# QA Data Representation

## Backend spot check summary
- Preflight snapshot audit passed on `2026-05-27`
- Representative live device/user QA used read-only debug auth against real backend data
- Direct endpoint checks previously confirmed:
  - `/preferences` returns live user prefs
  - `/holdings` returns live holdings
  - `/watchlists` returns live watchlist
  - `/today` returns populated digest payload
  - `/alerts` returns populated alert payload
  - `/brokerage/status` returns setup state
  - `/tickers/AAPL` and `/tickers/AAPL/methodology` return live structured detail

## Honesty audit

| Screen | Data condition | Current UI behavior | Honest enough? | Severity | Fix recommendation |
| --- | --- | --- | --- | --- | --- |
| Search | unsupported ticker (`SPY`) | shows unsupported state instead of fake detail | yes | `P3` | keep |
| Ticker Detail | slow or missing price history | now renders detail and shows `Price history unavailable for the selected window.` when needed | yes | `P3` | keep |
| Ticker Detail | incomplete live chart early in load | page no longer blocks on chart | yes | `P3` | keep |
| Alert center | live alerts present | now renders live counts and rows | yes | `P3` | keep |
| Settings / notifications | APNs unavailable in simulator | simulator logs show missing APS entitlement; QA does not treat push as healthy | yes | `P3` | keep explicit external blocker |
| Search / outside universe | broader universe still limited | unsupported names remain unsupported | yes | `P3` | keep until universe expansion lands |
| Ticker Detail | previous score/history gaps | chart/history uses real data; no fabricated previous score observed | yes | `P3` | keep |
| Settings | launch hydration | opening Settings no longer mutates live preferences by itself | yes | `P3` | keep |
| Settings | manual alert-preference change | deliberate toggle saves through to backend and can be restored | yes | `P3` | keep |
| Alert interaction | row lacks detail screen | user can reach destination, but alert-specific context is not represented in a dedicated surface | no | `P1` | add or explicitly defer Alert Detail |

## Live representation notes
- `AAPL` now loads real composite, grade, dimensions, history, and recent news.
- Alert center shows real unread counts and category counts from live backend data.
- Price history is still backend-latency sensitive; the UI fix prevents the entire detail screen from looking broken and allows the chart to fill in later.
- One methodology caveat remains from backend preflight: structured limited-data row existed for `HIMS:news_sentiment`. This pass did not fully rerun the HIMS UI drill-down.
