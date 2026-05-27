# QA Interaction Log

| Screen | Element tapped | Expected result | Actual result | Pass/Fail | Screenshot | Severity if failed |
| --- | --- | --- | --- | --- | --- | --- |
| Main shell | `Today` tab | Show Today screen | Today loaded with live digest data | Pass | `docs/screenshots/qa/qa-020-today-live.jpg` | — |
| Today | Morning Report card | Open full Morning Report | Full Morning Report opened | Pass | `docs/screenshots/qa/qa-021-morning-report-live.jpg` | — |
| Morning Report | close/back | Dismiss full report | Returned to Today | Pass | `docs/screenshots/qa/qa-020-today-live.jpg` | — |
| Main shell | `Holdings` tab | Show holdings ledger | Holdings loaded with AMD / HOOD live data | Pass | `docs/screenshots/qa/qa-030-holdings-live.jpg` | — |
| Main shell | `Search` tab | Show search shell | Search loaded | Pass | `docs/screenshots/qa/qa-040-search-empty.jpg` | — |
| Search | supported result (`AAPL`) | Open ticker detail | Ticker detail opened after fix | Pass | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | — |
| Search | unsupported query (`SPY`) | Honest unsupported state | Unsupported state shown; no fake data | Pass | `docs/screenshots/qa/qa-042-search-outside-universe.jpg` | — |
| Ticker Detail | back button | Return to Search | Returned to Search | Pass | `docs/screenshots/qa/qa-041-search-supported.jpg` | — |
| Main shell | `Alerts` tab | Show alert center | Alert center now loads populated list | Pass | `docs/screenshots/qa/qa-060-alert-center-live.jpg` | — |
| Alerts | first alert row | Open useful destination | Deep-linked to destination tab; no dedicated detail view verified | Fail | `docs/screenshots/qa/qa-060-alert-center-live.jpg` | `P1` |
| Main shell | `Settings` tab | Show settings | Settings loaded with live account + prefs | Pass | `docs/screenshots/qa/qa-070-settings-live.jpg` | — |
| Settings | passive launch / hydration | Load current preferences without mutating them | Live `user_preferences` values stayed unchanged until a deliberate toggle action | Pass | `docs/screenshots/qa/qa-070-settings-live.jpg` | — |
| Settings | `Major news` toggle off | Save user-initiated alert preference change | Backend preference changed from `true` to `false` | Pass | `docs/screenshots/qa/qa-070-settings-live.jpg` | — |
| Settings | `Major news` toggle on | Restore original alert preference | Backend preference changed from `false` back to `true` | Pass | `docs/screenshots/qa/qa-070-settings-live.jpg` | — |
| Settings | `Data sources & methodology` | Open methodology screen | Methodology screen opened | Pass | `docs/screenshots/qa/qa-071-settings-methodology.jpg` | — |
| Settings | methodology back | Return to Settings | Returned to Settings | Pass | `docs/screenshots/qa/qa-070-settings-live.jpg` | — |
| Settings | `Delete account` | Show confirmation only | Confirmation sheet shown; destructive action not executed | Pass | none | — |
| Settings | `Sign out` | Sign out flow | Not executed in this pass | Not tested | none | `P2` |
| Holdings / Search / Alerts / Settings | tab switches | Reliable tab navigation | Reliable after active-tab shell fix | Pass | mixed | — |
| Ticker Detail | add to holdings | Open add flow | Visible but not executed | Not tested | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | `P2` |
| Ticker Detail | add to watchlist | Add or open watchlist path | Visible but not executed | Not tested | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | `P2` |
| Settings | `Connect brokerage` | Open connect/setup-required path | Visible but not exercised | Not tested | `docs/screenshots/qa/qa-070-settings-live.jpg` | `P2` |
| Holdings | add button | Open add-holding sheet | Not rerun after fixes | Not tested | none | `P2` |

## Notes
- The largest live interaction failures were on Alerts and Ticker Detail. Both were retested after fresh install of the rebuilt app.
- Alert center now loads. Ticker Detail now renders without waiting on the slow price-history endpoint.
- A dedicated Alert Detail surface is still missing from the exercised live path; current alert rows behave as deep links.

## 2026-05-27 resume pass — live taps verified
- Search tab → recent `AAPL` row tap → Ticker Detail rendered hero/composite/radar/dimensions in under a second; price chart hydrated ~1s later. History chip strip `1D 1W 1M 3M 1Y` renders on one line with `1M` selected.
- Ticker Detail → Financial Health row tap → opened `FinancialHealthAuditView` (title "Financial Health", AAPL header). Back chevron returned to Ticker Detail.
- Ticker Detail → News Sentiment row tap → opened `NewsSentimentAuditView`. Back returned.
- Ticker Detail → Macro Exposure row tap → opened `MacroExposureAuditView` (TNX/DXY/WTI/VIX/SPY factor table). Back returned.
- Ticker Detail → Sector Exposure row tap → opened `SectorExposureAuditView` (Sector Beta / Momentum / Breadth). Back returned.
- Ticker Detail → Volatility row tap → opened `VolatilityAuditView` (Realized 30d/90d, Vol Ratio, Max Drawdown, Beta to SPY, IV Rank, Implied Vol, Vol Trend chart). Back returned.
- Settings tab → live preferences loaded without showing the new `preferencesMessage` banner, confirming the failure-only banner stays hidden when the live call succeeds.
- Alerts tab → PORT, NEWS, and GRADE row taps each deep-linked to the Holdings tab. No dedicated Alert Detail surface opened in any case (P1 still open).
- Today tab → live portfolio `$24,443 (+$1,865, +7.09%)`, BB composite `56`, five-axis snapshot all rendered. Morning Report briefing was honestly labeled "not generated yet" with an "Open →" CTA.
