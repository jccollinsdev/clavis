# QA Clavix Truth Coverage

| Truth requirement | Screen/path | Status | Evidence screenshot | Notes | Priority |
| --- | --- | --- | --- | --- | --- |
| User-visible brand says Clavix | tested shell | present | multiple | No user-visible `Clavis` branding observed on tested screens | `P1` |
| No advisory buy/sell/recommend language | tested shell | present | multiple | No advisory copy found in tested live UI | `P1` |
| Daily digest exists | Today | present | `docs/screenshots/qa/qa-020-today-live.jpg` | Live digest rendered | `P1` |
| Morning Report exists | Today -> full view | present | `docs/screenshots/qa/qa-021-morning-report-live.jpg` | Reads like a briefing | `P1` |
| Portfolio holdings exist | Holdings | present | `docs/screenshots/qa/qa-030-holdings-live.jpg` | Live AMD / HOOD positions | `P1` |
| Manual holding entry exists | Holdings add flow | partial | none | Code path exists; not rerun in this pass | `P2` |
| Brokerage connection path exists | Settings / Onboarding | partial | `docs/screenshots/qa/qa-070-settings-live.jpg` | Connect button visible; not fully exercised | `P1` |
| CSV import path exists or honest placeholder exists | Onboarding / Holdings upgrade sheet | partial | none | Placeholder path exists in code; not rerun | `P1` |
| Watchlist exists | Holdings | present | `docs/screenshots/qa/qa-030-holdings-live.jpg` | Live watchlist rendered | `P2` |
| Ticker search exists | Search | present | `docs/screenshots/qa/qa-040-search-empty.jpg` | Search shell and results verified | `P1` |
| Outside-universe behavior exists | Search `SPY` | present | `docs/screenshots/qa/qa-042-search-outside-universe.jpg` | Honest unsupported state | `P1` |
| Ticker detail hero exists | AAPL detail | present | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Live after fix | `P1` |
| Price/day change visible | AAPL detail | partial | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Price + selected-window change visible; not separately reverified on `1D` | `P2` |
| Grade/composite visible | AAPL detail | present | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Visible in hero | `P1` |
| Five risk dimensions visible | AAPL detail | present | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Visible list | `P1` |
| Each dimension tappable | AAPL detail | partial | none | Intended path exists; full drill-down not conclusively verified in this pass | `P1` |
| Methodology drill-down exists | Settings / Ticker detail path | present | `docs/screenshots/qa/qa-071-settings-methodology.jpg` | Settings methodology screen verified | `P1` |
| Formulas visible where data exists | audit screens | partial | none | Underlying methodology endpoint verified; full UI drill-down not completed | `P2` |
| Inputs visible where data exists | audit screens | partial | none | Same as above | `P2` |
| Sources/freshness visible where data exists | detail / methodology | partial | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Source/news rows visible; full freshness audit incomplete | `P2` |
| Recent news exists | AAPL detail | present | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Live rows render | `P1` |
| Article detail exists | article row tap | partial | none | Sheet exists in code; not fully rerun in this pass | `P2` |
| Score history exists | AAPL detail | present | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Live history graph rendered | `P1` |
| Alerts center exists | Alerts | present | `docs/screenshots/qa/qa-060-alert-center-live.jpg` | Live rows render after fix | `P1` |
| Alert detail exists | alert row tap | missing / partial | none | Rows still deep-link to Today / Holdings destinations; a dedicated alert-detail surface is not exposed in the live path | `P1` |
| Grade-change / major-news alert surface exists | Alerts | present | `docs/screenshots/qa/qa-060-alert-center-live.jpg` | Both types visible | `P1` |
| Settings methodology exists | Settings | present | `docs/screenshots/qa/qa-071-settings-methodology.jpg` | Verified | `P2` |
| Free/Pro limits appear honestly | Settings / Holdings / Onboarding code | partial | `docs/screenshots/qa/qa-070-settings-live.jpg` | Free badge visible; placeholder upgrade paths exist in code but not fully exercised | `P1` |
| Upgrade path exists | Settings / Holdings / Onboarding code | partial | none | Placeholder sheets exist, not rerun in device QA | `P1` |
| Legal/privacy/terms links exist | Settings | present | `docs/screenshots/qa/qa-070-settings-live.jpg` | Visible | `P2` |
| No fabricated previous scores | Ticker detail | present | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Observed honest history usage | `P1` |
| Limited-data behavior exists | unsupported / chart unavailable | present | `docs/screenshots/qa/qa-042-search-outside-universe.jpg` | Honest limited/unsupported states observed | `P1` |
| Source transparency exists | recent news | present | `docs/screenshots/qa/qa-050-ticker-detail-live.jpg` | Source and recency shown | `P2` |
| Refresh/freshness timestamps exist | backend payload / some UI surfaces | partial | none | Backend carries freshness; not fully audited across UI | `P2` |
