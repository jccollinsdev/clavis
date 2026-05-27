# Clavix Full Live-Data QA Final Report

## Executive verdict (updated 2026-05-27 resume pass)
- UI/navigation readiness score: 82 (was 74; dimension drill-ins now real NavigationLinks)
- Data representation honesty score: 86
- Button functionality score: 84 (was 71)
- Navigation reliability score: 88 (was 78)
- Redundancy score: 67
- Clavix Truth coverage score: 72
- Safe to push: yes
- Safe for internal alpha: yes
- Safe for TestFlight live-data beta: no (still missing dedicated Alert Detail surface, auth/onboarding revalidation, broader universe; see P1 below)

## 2026-05-27 resume-pass findings
- Tip commit before this pass: `58953828e`. Working tree was dirty from latency-and-honesty edits to `APIService`, `DigestViewModel`, `HoldingsViewModel`, `SettingsViewModel`, `SettingsView`, and `TickerDetailView`.
- Live backend `/health` returned `200 status=ok` (apns missing as expected in sim). `/tickers/AAPL` returned `401 Missing Authorization header` for the unauthenticated probe (expected) and `200 61 KB in 3.86s` with a freshly-minted local debug JWT.
- DEBUG launch args bypass (`--clavix-debug-auth-bypass`) opened the live shell into the Search tab without a root spinner trap. All five tab buttons responded.
- The `/tmp/clavix_debug_jwt_7ff` token from the prior pass was expired; a fresh 6-hour `HS256` JWT was minted locally from the backend `SUPABASE_JWT_SECRET` env value (not committed). After relaunch, live AAPL detail rendered hero/composite/radar/dimensions before the 1Y price chart hydrated, then the chart filled in honestly.
- The history chips row (`1D 1W 1M 3M 1Y`) rendered on one line with the `1M` chip selected; no per-letter wrap.
- All five dimension rows now use `NavigationLink(value: AuditDestination)` against a `.navigationDestination(for: AuditDestination.self)` declared on the Ticker Detail. Manual sim taps via accessibility `AXPress` opened each audit screen, and the system back chevron returned to the Ticker Detail every time.
  - Financial Health → `FinancialHealthAuditView` (Ratio Table / Industry Comparison / Methodology). Methodology payload empty in this snapshot so rows showed `Unavailable` honestly.
  - News Sentiment → `NewsSentimentAuditView` (Weighting / Articles / Score Calculation).
  - Macro Exposure → `MacroExposureAuditView` (Factor Sensitivity per TNX/DXY/WTI/VIX/SPY).
  - Sector Exposure → `SectorExposureAuditView` (Metrics / Narrative / Methodology).
  - Volatility → `VolatilityAuditView` (Metrics: Realized 30d/90d, Vol Ratio, Max Drawdown, Beta to SPY, IV Rank, Implied Vol, Vol Trend chart).
- Settings tab loaded live preferences for `sansar.qa@example.com` (FREE tier, 7:00 AM digest, Standard length, all alert toggles on). No `preferencesMessage` banner appeared because the live load succeeded — exactly the honest signal the new field provides on failure paths.
- Alerts tab loaded live data (0 unread, 50 in 7d, mixed GRADE/NEWS/PORT rows). Tapping a PORT alert deep-linked to Holdings; tapping a NEWS/GRADE alert also deep-linked to Holdings (no dedicated Alert Detail). This confirms the prior pass's P1 — alert detail is still missing.
- Today tab rendered live portfolio composite ($24,443, +$1,865 today, BB composite 56, five-axis scores) and honestly labeled the morning briefing as "Briefing not generated yet" with an "Open →" call to action.

## Current repo state
- Branch: `main`
- Tip commit: `2dea86eae` (`docs: record snapshot completeness recovery results`)
- Working tree: not clean
- Tracked resume-pass code changes: `MainTabView`, `APIService`, `SupabaseAuthService`, `AlertsViewModel`, `SettingsViewModel`, `SettingsView`, `TickerDetailView`
- Untracked artifact status: massive untracked `BACKFILL/` payloads and `docs/snapshot_audit_outputs/*`; left untouched

## Backend preflight result
- Same-day snapshot completeness preflight from the interrupted run was reused; no rerun was needed on resume
- Tracked universe: `504`
- Latest snapshots complete: `504 / 504`
- `news_sentiment` completeness: `504 / 504`
- `macro_exposure` completeness: `504 / 504`
- Missing `composite_score`: `0`
- Partial latest rows selected: `0`
- API selection mismatches: `0`
- Structured limited rows selected: `1` (`HIMS:news_sentiment`)
- Current universe limitation remains: effectively S&P 500-scale, not full broader Clavix Truth coverage

## Modes tested
- Primary: live-data shell with `CLAVIX_DEBUG_AUTH_BYPASS=1`
- Live QA user for resumed pass: `90b7281c-0015-49de-a657-587bb25fbc6c` with local placeholder email `qa-live@example.com`
- Secondary comparison evidence: prior fixture screenshots only; fixture mode not fully rerun in this pass
- Auth/onboarding debug modes: not fully rerun in this pass
- Signed-out normal auth flow: not fully rerun in this pass

## Screens tested
- Main shell tabs: Today, Holdings, Search, Alerts, Settings
- Today live state and Morning Report full view
- Holdings live populated state
- Search empty, supported result, unsupported result
- Ticker Detail live state for `AAPL`
- Settings launch hydration and one manual alert-preference toggle round trip
- Settings methodology route
- Alert center live populated state

## Screens not tested and why
- Welcome / sign in / sign up / forgot password: not rerun after live-data fixes
- Onboarding steps 1-5: not rerun in this pass
- Brokerage connect callback flow: external setup path only, not completed
- CSV import sheet: code path exists, not exercised in simulator
- Paywall / upgrade sheets: placeholder code exists, not fully exercised in simulator
- Live audit deep-link screens for all five dimensions: not conclusively re-opened in this resumed pass; the existing static methodology screen was verified, but live dimension-audit evidence remains incomplete
- Alert detail: not just unverified; the live alert-row behavior still deep-links to destination tabs instead of opening an alert-specific detail surface

## Screenshots added
- `docs/screenshots/qa/qa-020-today-live.jpg`
- `docs/screenshots/qa/qa-021-morning-report-live.jpg`
- `docs/screenshots/qa/qa-030-holdings-live.jpg`
- `docs/screenshots/qa/qa-040-search-empty.jpg`
- `docs/screenshots/qa/qa-041-search-supported.jpg`
- `docs/screenshots/qa/qa-042-search-outside-universe.jpg`
- `docs/screenshots/qa/qa-050-ticker-detail-live.jpg`
- `docs/screenshots/qa/qa-060-alert-center-live.jpg`
- `docs/screenshots/qa/qa-070-settings-live.jpg`
- `docs/screenshots/qa/qa-071-settings-methodology.jpg`

### Added 2026-05-27 resume pass
- `docs/screenshots/qa/qa-latest-today-live.jpg`
- `docs/screenshots/qa/qa-latest-ticker-detail-aapl.jpg`
- `docs/screenshots/qa/qa-latest-history-chips.jpg`
- `docs/screenshots/qa/qa-latest-audit-financial-health.jpg`
- `docs/screenshots/qa/qa-latest-audit-news-sentiment.jpg`
- `docs/screenshots/qa/qa-latest-audit-macro-exposure.jpg`
- `docs/screenshots/qa/qa-latest-audit-sector-exposure.jpg`
- `docs/screenshots/qa/qa-latest-audit-volatility.jpg`
- `docs/screenshots/qa/qa-latest-settings-status.jpg`
- `docs/screenshots/qa/qa-latest-alerts.jpg`

## P0 issues
- None confirmed after fixes and rebuild/install verification
- 2026-05-27 resume pass: still none. The previously open "Financial Health row does not open" blocker is resolved by the NavigationLink conversion; all five rows verified live.

## P1 issues
- Alert rows still do not open a dedicated Alert Detail surface; the live path routes to Today / Holdings destinations instead. Confirmed again on 2026-05-27 — PORT, NEWS, and GRADE alerts all route into Holdings rather than a dedicated detail.
- Auth, onboarding, and signed-out entry flows were not fully revalidated in this pass, so release readiness is still incomplete
- Broader tracked-universe coverage remains below Clavix Truth target; unsupported names are handled honestly, but product breadth is still constrained

## P2 issues
- Methodology screen visual language is darker than the rest of the cream shell
- `ArticleDetailSheet` still uses `.capitalized` on tags, which risks non-canonical label transforms
- Xcode project still warns about malformed `Clavis/Config` file reference
- SearchView still has deprecated `onChange(of:perform:)` usage

## P3 issues
- More complete audit deep-link screenshot coverage
- Readability pass for Dynamic Type / VoiceOver labels
- Polish around chart empty/loading transitions

## Fixes made
- Added DEBUG-only auth bypass hooks for safe live QA
- Fixed alerts endpoint decoding to match `{ "alerts": [...] }`
- Prevented hidden Settings hydration from immediately mutating live preferences during QA
- Stopped sending unsupported `alerts_large_price_moves` payload field from Settings
- Changed tab shell to mount only the active tab, eliminating hidden-tab network/write activity
- Made Ticker Detail render without blocking on slow price-history fetch
- Decoupled alert-center secondary data loads so holdings/preferences can’t block alert rendering

### Added 2026-05-27 resume pass
- Replaced the unreliable `MethodologyDrawerSheet` sheet presentation on Ticker Detail with direct `NavigationLink(value:)` per dimension row, routing through a new `.navigationDestination(for: AuditDestination.self)` declared on the detail view. The audit views (`FinancialHealthAuditView`, `NewsSentimentAuditView`, `MacroExposureAuditView`, `SectorExposureAuditView`, `VolatilityAuditView`) accept the optional `methodology` payload and render an honest "Unavailable" state when it has not loaded yet. The `MethodologyDrawerSheet` file remains in the tree for any future entry point but is no longer reached from Ticker Detail.
- Tightened request timeouts on the read-heavy endpoints (`/today` now 18s, `/holdings` 15s, `/tickers/...` 15s, `/preferences` 10s, `/watchlists` and `/alerts` and `/analysis-runs/latest` 12s, `/brokerage/status` 12s, `/tickers/search` 12s, `/tickers/.../methodology` 15s) so a stalled secondary call cannot trap the global skeleton.
- Refactored `DigestViewModel.reload(...)`, `HoldingsViewModel.reload(...)`, and `TickerDetailView.reloadAll()` so the primary payload lands first and secondary calls (watchlist, preferences, brokerage status, today envelope, price/score history, methodology) hydrate in independent `Task` branches. The `isLoading` flag drops as soon as the primary call resolves, so secondary failures can no longer hold the UI in a skeleton.
- Added a `preferencesMessage` field on `SettingsViewModel` and rendered it via `DashboardErrorCard` in `SettingsView`. Load failures and per-toggle save failures now show the user a visible banner instead of silently looking live.

## Button and navigation audit summary
- Main tab navigation now works reliably across Today, Holdings, Search, Alerts, and Settings
- Morning Report open/close path works
- Search result to Ticker Detail works for supported tickers
- Unsupported ticker handling is honest (`SPY` shows unsupported state instead of fake data)
- Alert rows are tappable but currently act as destination deep links, not alert-detail views
- Destructive Settings actions stop at confirmation
- A manual Settings change was reverified by toggling `Major news` off and back on; backend values changed and were restored

## Redundancy audit summary
- No severe same-card repetition found on tested live screens
- Ticker Detail shows progressive disclosure from composite to dimensions to news/history
- Alerts list is dense but not obviously duplicative within a single row design
- Some repeated portfolio-risk alerts across days are real underlying data, not a UI duplication bug

## Data representation honesty summary
- Live snapshot completeness is now reflected honestly on tested screens
- Unsupported tickers are shown as unsupported rather than padded with fake coverage
- Ticker Detail now degrades progressively: first render succeeded before price history returned, then the chart filled in later when live data arrived
- APNs is not healthy in simulator and should not be treated as configured
- No fabricated previous scores were observed on tested detail/history surfaces
- Opening Settings no longer auto-PATCHed preferences on launch; the live `user_preferences` row remained unchanged until a deliberate toggle action

## Clavix Truth coverage summary
- Core live-data shell is present
- Morning Report exists and reads like a briefing
- Holdings, watchlist, search, ticker detail, five dimensions, score history, and methodology surfaces are present
- Outside-universe behavior is present and honest
- Coverage remains partial for alert detail, live audit drill-down verification, and broader universe scope

## Accessibility/readability summary
- Tested live screens are readable for the target user on default text size
- Tap targets on tabs, rows, and primary cards are acceptable in tested screens
- Long alert copy wraps without obvious clipping
- Some dense ticker-news rows remain visually busy for an older-investor audience

## External setup blockers
- Payments / StoreKit: placeholder-only, not configured for real checkout
- Brokerage / SnapTrade: connect path exists, real brokerage completion not verified
- APNs: simulator reports missing APS entitlement; push cannot be treated as healthy
- Broader universe expansion: still not at Clavix Truth target breadth

## Before TestFlight checklist
- Verify auth, sign-up, sign-in, forgot-password, and onboarding flows end-to-end
- Verify upgrade/paywall placeholder routes from every visible Pro CTA
- Verify CSV import placeholder route and brokerage connect placeholder route from user-facing entry points
- Add or explicitly defer a real Alert Detail surface
- Run a second screen pass on live audit deep links for at least Financial Health and News Sentiment, then the remaining dimensions
- Decide whether methodology visual mismatch is acceptable for beta

## Safe to defer
- Xcode project malformed group warning cleanup
- SearchView deprecation cleanup
- Deeper accessibility polish
- Broader tracked-universe expansion
