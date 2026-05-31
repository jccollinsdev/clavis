# Hi-Fi Live Parity Gap — 2026-05-27

Per-screen audit of the 45 `ClavixVisualQA*` screens in
`ios/Clavis/App/ClavixVisualQA.swift` (the canonical Hi-Fi v2 design ported to
SwiftUI with hand-rolled fixture data) against the live tabs under
`ios/Clavis/Views/` and the wire shapes exposed by
`ios/Clavis/Services/APIService.swift`.

## Summary

Classification counts across the 45 routes:

- **PORTABLE — 13.** Live view can adopt the VQA layout with the existing
  `Clavix*` atoms and existing view-model state. Cosmetic or wiring work only.
- **PARTIAL — 21.** The frame is portable, but at least one VQA element
  requires a backend field that does not exist yet. The honest path is to ship
  the structure with explicit "Unavailable" / `—` placeholders for the missing
  rows and keep the backend follow-up on a backlog row.
- **STRUCTURAL — 11.** A whole VQA route either has no live counterpart
  (subscription, paywall, alert detail, article paywalled/failed states,
  bare-state "limited data" screens) or the data the VQA depends on is a
  multi-week backend build (alert detail composite hysteresis proof, full
  methodology audit formula+inputs, watchlist/tracked enrichment with prices &
  deltas).

External dependencies that gate full parity for paid surfaces (StoreKit,
SnapTrade, Apple Developer Program → APNs) are unchanged since the
2026-05-25 backlog. Those screens are listed in the "Out of scope for this
pass" section at the bottom rather than spread across the audit rows.

## How to execute this plan

1. **See the target.** Boot the sim with
   `CLAVIX_USE_VQA_MOCK=1 CLAVIX_DEBUG_OPEN=<route>` to render any
   `case "..."` from `ClavixVisualQARoot` (the literal route keys are in the
   header table per section below). The screen renders with the static fixture
   data so the rebuild target is the same fixture every time.
2. **See the live counterpart.** Boot normally with
   `--clavix-debug-auth-bypass --clavix-debug-jwt $(cat /tmp/clavix_debug_jwt_7ff)
   --clavix-debug-user-id 7ff5a6c5-8e49-4c2f-be1c-bdc869926699` to sign in as
   the seeded test user. If the JWT file is missing, mint one (see
   `docs/CODEX_PROMPT_HIFI_PARITY.md` §"Local debug JWT").
3. **Atom rename rules.** Anything in the VQA file starts with `VQA*`
   (`VQACard`, `VQAGrade`, `VQASection`, `VQAEyebrow`, `VQAScreen`,
   `VQALargeHeader`, `VQAPill`, `VQAColumnHeader`, `VQAMiniSpark`,
   `VQATabBar`, `VQAScoreBar`). The production atoms in
   `ios/Clavis/Views/Shared/Components/ClavixVQAComponents.swift` use the
   `Clavix*` prefix and are 1:1 replacements. Three atoms still live private
   in `ClavixVisualQA.swift` (`VQARadar`, `VQALineChart`, `VQACodeCard`) and
   either need a one-time extract into `ClavixVQAComponents.swift` (radar —
   already done inline inside `TickerDetailView`) or accept a deliberate
   "no chart in production" stance for now (`VQALineChart` placeholder, used
   for hero sparklines).
4. **Build & run.**
   ```
   xcodebuild \
     -workspace ios/Clavis.xcodeproj/project.xcworkspace \
     -scheme Clavis \
     -destination 'platform=iOS Simulator,name=iPhone 17' build
   ```
   then `mcp__xcode__install_app_sim` + `mcp__xcode__launch_app_sim`.
5. **Screenshot loop.** `mcp__xcode__screenshot(returnFormat="path")` on both
   the live tab and the VQA mock at the same route; diff visually; iterate
   until the live screen matches at default Dynamic Type.

## Out of scope for this pass

These routes either have no honest live data path today, or depend on a
prerequisite called out in `backlog.md` "Prerequisites we do not own yet".
Tracking them here keeps them out of the per-route table so the work-loop
doesn't stall on them.

- `paywall`, `subscription-trial`, `subscription-active` — StoreKit not built.
  Marketing comparison and trial countdown copy fine to render as a static
  shell; do NOT wire prices or entitlement state. Blocked by Apple Developer +
  StoreKit setup.
- `brokerage-sync` — Brokerage routes return `not_configured` until SnapTrade
  developer credentials are provisioned on the VPS. Live view is functional
  ("Connect brokerage" → 503-friendly empty state) but does not pass through a
  real connection. Treat the VQA "Live" status copy as a future state.
- `delete-account` — Live `SettingsView` has its own destructive confirmation
  alert that already wires `viewModel.deleteAccount()`. The VQA "Type DELETE
  to confirm" interaction can be modelled later; the alert is not pretty but
  it is correct.
- `export` — Live `SettingsView` "Export account data" button hits
  `/account/export` and surfaces a count of top-level items. Building a
  separate VQA-styled screen for it is a polish pass; the existing button
  works.
- `auth-loading`, `splash`, `today-empty`, `today-error`, `offline`,
  `limited-data`, `insufficient-history`, `refresh-limit`, `auth-error`,
  `search-none` — these are state screens, not routes. They should be folded
  into the existing live view bodies as conditional render branches when the
  triggering condition is met, not built as standalone navigation
  destinations. The existing `stateCard(...)` pattern in
  `Views/Digest/DigestView.swift` is the template.

---

## Auth

### `splash` — `ClavixVisualQASplash`

- **Live counterpart:** `ios/Clavis/App/ClavixApp.swift` (boot path, no
  dedicated splash view today)
- **View model / data source:** none — the SwiftUI launch surface is the
  `LoginView` once `AuthViewModel.checkSession()` resolves
- **VQA fixture data shape:** waveform icon · "Clavix" wordmark · "Portfolio
  risk, measured." tagline
- **API shape today:** n/a
- **Classification:** `PORTABLE`
- **Port plan:** Add a `ClavixSplashView` rendered while
  `AuthViewModel.checkSession()` is in flight. The icon, wordmark, and tagline
  are all static strings — no view-model wiring beyond
  `@EnvironmentObject var authViewModel` and an `if !authViewModel.checkedSession`
  flag. Atom mapping: just `Color.clavixPage` background + serif/mono typography
  helpers; no `Clavix*` atom required.
- **Backend gap:** none.

### `auth` — `ClavixVisualQAAuthWelcome`

- **Live counterpart:** `ios/Clavis/Views/Auth/LoginView.swift` (combined
  welcome + form view today)
- **View model / data source:** `AuthViewModel`
- **VQA fixture data shape:** brand row · "Morning Report" eyebrow card with
  the one-line value pitch · "Portfolio risk, measured." hero · descriptive
  paragraph · Create account / Sign in buttons · "Clavix is informational
  only." disclaimer footer
- **API shape today:** n/a
- **Classification:** `PARTIAL`
- **Port plan:** Split `LoginView` into a welcome surface (when `email.isEmpty &&
  password.isEmpty` and no error) and the form surface. Welcome reuses
  `ClavixCard` for the value pitch and the same `ClavisPrimaryButton` pair.
  Disclaimer text is static. Welcome does not need a view-model change; the
  existing `LoginView` state can hold a `@State private var mode:
  AuthMode = .welcome`.
- **Backend gap:** none. The card copy is the only place a backend value
  ("Andover Digital") is implied; render that static string.

### `auth-signup` / `auth-signin` — `ClavixVisualQAAuthForm`

- **Live counterpart:** `ios/Clavis/Views/Auth/LoginView.swift`
- **View model / data source:** `AuthViewModel.signIn` / `signUp`
- **VQA fixture data shape:** `ClavixScreen` with eyebrow=Account · title=Create
  account / Sign in · card with two `VQAInputRow`s + a single dark button ·
  "Your first report appears after your portfolio is added." caption
- **API shape today:** n/a (Supabase auth, not our backend)
- **Classification:** `PORTABLE`
- **Port plan:** Wrap the existing email/password form in a `ClavixScreen`
  with `ClavixCard`, use `ClavixGradeBadge`-free `ClavisPrimaryButton` for the
  submit, drop the welcome row + bullet list when `isSignUp` is true (those
  belong to the new welcome split above). Existing `AuthViewModel` bindings
  unchanged.
- **Backend gap:** none.

### `auth-forgot` — `ClavixVisualQAForgotPassword`

- **Live counterpart:** none — `LoginView` has an inline "Forgot password?"
  link that calls `AuthViewModel.resetPassword(email:)` directly with the
  email already typed in the sign-in form
- **View model / data source:** `AuthViewModel.resetPassword(email:)`
- **VQA fixture data shape:** `ClavixScreen` · email input · "Send reset
  link" button
- **API shape today:** Supabase auth `resetPassword` (no Clavix backend
  call)
- **Classification:** `PORTABLE`
- **Port plan:** Add a `ForgotPasswordView` reachable from the sign-in form's
  "Forgot password?" button instead of the silent inline call. Single email
  input, single dark submit, success surfaces `authViewModel.statusMessage`.
- **Backend gap:** none.

### `auth-error` — `ClavixVisualQAAuthError`

- **Live counterpart:** rendered inline in `LoginView.statusMessage`
- **View model / data source:** `AuthViewModel.errorMessage`
- **VQA fixture data shape:** `ClavixScreen` with a tinted bad-soft
  `ClavixCard` containing the failure copy
- **API shape today:** Supabase error strings
- **Classification:** `PORTABLE`
- **Port plan:** Render the error in a `ClavixCard(fill: .clavixBadSoft)`
  inside the existing `LoginView` rather than as a standalone screen. The
  current `Text(error)…foregroundColor(.riskF)` line is functional but doesn't
  match the cream/paper card treatment.
- **Backend gap:** none.

### `auth-loading` — `ClavixVisualQALoading`

- **Live counterpart:** spinner inside `ClavisPrimaryButton(isLoading:)`
- **View model / data source:** `AuthViewModel.isLoading`,
  `AuthViewModel.isLoadingPreferences`
- **VQA fixture data shape:** centered `ProgressView` + serif title +
  caption detail
- **Classification:** `PORTABLE` — already covered by the inline button
  spinner; promote to a full-screen overlay only if a future deep-link cold
  start needs it
- **Port plan:** Optional. Match the VQA layout if a long preference load
  needs a dedicated screen.
- **Backend gap:** none.

---

## Onboarding

### `onboarding` — `ClavixVisualQAOnboarding`

- **Live counterpart:**
  `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift`
  (`OnboardingAddPortfolioView` page)
- **View model / data source:** `OnboardingViewModel`,
  `BrokerageViewModel.startConnect`, plus the eventual add-holding flow via
  `HoldingsViewModel`
- **VQA fixture data shape:** `ClavixScreen` with eyebrow="Step 1 of 2" ·
  title="Add portfolio" · serif lead-in · three `VQAMethodCard`s (Connect
  brokerage / Enter manually / Upload CSV) · Continue manually dark button
- **API shape today:** `/brokerage/connect` for SnapTrade flow,
  `POST /holdings` for manual; CSV import has no backend route
- **Classification:** `PARTIAL`
- **Port plan:** Replace `OnboardingAddPortfolioView.pathCard` with a
  `VQAMethodCard`-equivalent (`ClavixCard` + leading SF Symbol + serif title +
  caption + optional pill badge). Reuse existing brokerage/CSV/manual
  handlers. Keep the "Pro" badge on Connect brokerage and CSV per
  `subscriptionTier`. The "Continue manually" CTA already maps to
  `completeAndOpenHoldings()`.
- **Backend gap:** CSV import is mock-only (no backend endpoint). Render CSV
  card as "Coming soon" until the route exists — do not navigate to the
  fake `CSVImportSheet`.

### `onb-intro` — `ClavixVisualQAOnboardingIntro`

- **Live counterpart:** `OnboardingWelcomeView` inside
  `OnboardingContainerView.swift`
- **View model / data source:** `OnboardingViewModel.currentPage`
- **VQA fixture data shape:** brand · eyebrow="Welcome to Clavix" · centered
  serif hero · centered body · "1 of 7" pill · "Get started" dark button
- **API shape today:** n/a
- **Classification:** `PARTIAL`
- **Port plan:** The live `OnboardingWelcomeView` already has the welcome
  copy, but it uses a vertical bullet list (3 bullets) rather than the
  centered "1 of 7" pagination dot the VQA fixture shows. Simplify to the
  centered hero layout when porting; the bullet list is fine to keep below
  the hero, since it carries product-truth copy the VQA fixture summarises
  in a single sentence. Pagination pill is decorative.
- **Backend gap:** none. The "1 of 7" pill copy implies a longer onboarding
  flow than the live two-page version; render only the pages that actually
  exist.

### `onb-digest-prefs` — `ClavixVisualQAOnboardingDigestPrefs`

- **Live counterpart:** none — preferences are collected on
  `Views/Settings/SettingsView.swift` after onboarding completes, not during
  it
- **View model / data source:** `SettingsViewModel` (`digestTime`,
  `summaryLength`, `weekdayOnly`), `APIService.updatePreferences`
- **VQA fixture data shape:** `ClavixScreen` · "Step 5 of 7" eyebrow ·
  settings group with Time / Length / Weekends rows · Continue button
- **API shape today:** `PATCH /preferences` with `digest_time`,
  `summary_length`, `weekday_only`
- **Classification:** `STRUCTURAL`
- **Port plan:** Only build this if we want onboarding to capture preferences
  before the first run. Otherwise omit — the same screen lives in Settings.
  If kept, factor `SettingsViewModel.digestSection` into a reusable view
  and host it inside an `OnboardingPage.digestPrefs` case.
- **Backend gap:** none.

### `onb-final` — `ClavixVisualQAOnboardingFinal`

- **Live counterpart:** none — onboarding currently dismisses to Holdings
  directly via `completeAndOpenHoldings()`
- **View model / data source:** `OnboardingViewModel.completeOnboarding`
- **VQA fixture data shape:** `ClavixScreen` · good-soft `ClavixCard`
  confirmation · "Open Clavix" dark button
- **API shape today:** `POST /preferences/acknowledge`
- **Classification:** `PORTABLE`
- **Port plan:** Optional. If kept, insert as a final page between
  `addPortfolio` and the tab shell. Single static success card + button that
  posts `.openAddHoldingFromOnboarding` (already done by
  `completeAndOpenHoldings`).
- **Backend gap:** none.

---

## Today / Digest

### `today` (tab default) — `ClavixVisualQAToday`

- **Live counterpart:** `ios/Clavis/Views/Digest/DigestView.swift`
- **View model / data source:** `DigestViewModel` (`today`, `todayDigest`,
  `holdings`, `alerts`); `/today`, `/holdings`, `/digest`, `/alerts`,
  `/preferences`
- **VQA fixture data shape:**
  - Portfolio hero: date · "Updated" · portfolio value · "-$5,438 today" ·
    grade badge (`AA`) · "Composite 81 · -1"
  - Morning Report card: eyebrow · serif title · 3-line preview · `Open →`
  - Five-axis snapshot: 5 columns `FIN/NEWS/MAC/SEC/VOL` with score
  - Sector exposure: 3×2 grid of `VQASectorCell` (symbol · name ·
    change% · weight%)
  - Attention: alerts preview with "See all →"
  - Top movers: 5 `VQABookRow`s with grade + delta + today%
  - Calendar: 3 `VQACalendarLine`s (time · type · title)
- **API shape today:** `TodayResponse` exposes everything except the headline
  on the Morning Report card; `Position.sharedAnalysis.dayChangeAmount/Pct`
  and `previousClose` drive the per-row today%. `TodayResponse.attention`
  exists; `attention.alerts[].ticker/title/created_at` populate the preview.
  `TodayResponse.calendar` exists with type/time/title/ticker.
- **Classification:** `PORTABLE` (this is the most-finished live screen, but
  there are still gaps below)
- **Port plan:** The structure is already in `DigestView`. Remaining
  divergences to close:
  1. Five-axis snapshot reads from `viewModel.today?.dimensions`; when that
     array is empty, fall back to the per-position weighted average using
     `dimensionTuples` — current code already does this honestly. Verify each
     code maps to the canonical five (`FIN/NEWS/MAC/SEC/VOL`) and that
     missing cells render `—`.
  2. Top movers shows `position.sharedAnalysis?.displaySummary` as the
     2-line note. The VQA shows a per-position editorial sentence; map this
     to `sharedAnalysis?.gradeRationale` (already routed via `displaySummary`)
     and render `"No note yet."` for nil.
  3. Calendar items: prefer `TodayResponse.calendar` when present (already
     wired); fall back to `DigestWhatMattersItem` parsing. No fabrication.
- **Backend gap:** Score delta on the composite line still depends on a real
  `portfolio.previousScore` / `portfolio.scoreDelta` from `/today` — backend
  ships the field shape but values are sometimes null; render `—` for delta
  when null (already does).

### `digest` / `report` — `ClavixVisualQADigest`

- **Live counterpart:** `ios/Clavis/Views/Digest/MorningReportView.swift`
- **View model / data source:** `DigestViewModel.todayDigest` (the
  `Digest.structuredSections`)
- **VQA fixture data shape:** Newspaper-style header (CLAVIX · MORNING
  REPORT eyebrow + date) · portfolio rating + composite + mini line chart ·
  six numbered `VQARomanSection`s (I Macro overnight, II Sector exposure,
  III Position changes, IV Tracked tickers, V What to track today,
  VI Sources & Methodology)
- **API shape today:** `Digest.structuredSections` has `header`,
  `overnightMacro` (headlines + themes + brief), `sectorHeat` (per-sector
  brief + headlines), `positions` (per-ticker macroRelevance, impactSummary,
  watchItems, topRisks, dimensionBreakdown), `watchlistUpdates`,
  `whatToWatchToday`. No "VI Sources & Methodology" field.
- **Classification:** `PARTIAL`
- **Port plan:** Replace the existing `MorningReportView` body with six
  `ClavixSection`-or-`VQARomanSection`-style blocks bound to the structured
  sections. Map:
  - I Macro overnight → `structuredSections.overnightMacro.brief` (serif body
    paragraph) + tinted `ClavixCard` with the first theme as READ-THROUGH if
    available.
  - II Sector exposure → `structuredSections.sectorHeat` ledger (one row per
    sector with brief + first headline).
  - III Position changes → `structuredSections.positions` ledger; map
    `urgency` to grade tone.
  - IV Tracked tickers → `structuredSections.watchlistUpdates.watchList`
    (already an array of strings).
  - V What to track today → `structuredSections.whatToWatchToday.catalysts`
    (same parsed time/type/title as Today calendar).
  - VI Sources & Methodology → static "Generated at …" line + open
    methodology link. The "Sources" lineage list does not exist on
    `Digest`; render the methodology-version footer only.
- **Backend gap:** `Digest` does not expose per-section source/freshness
  lineage rows. Render the section without that table for now; backlog row
  added.

---

## Holdings

### `holdings` (tab) — `ClavixVisualQAHoldings`

- **Live counterpart:** `ios/Clavis/Views/Holdings/HoldingsListView.swift`
- **View model / data source:** `HoldingsViewModel` (`holdings`,
  `watchlistItems`, `subscriptionTier`); `/holdings`, `/watchlists`
- **VQA fixture data shape:** sync summary line · `VQAHoldingsToolbar`
  (Weight/Grade/Δ Today/P&L pills + "9 / 9") · ledger header bar · ledger
  rows (Sym·w% / Last·day(spark+pct) / P&L / Grade·Δ) · tracked tickers
  section · sector composition bars
- **API shape today:** Position has `sharedAnalysis.dayChangePct`, `weight`
  derivable from `currentValue / Σ currentValue`, `scoreDelta`, `currentPrice`,
  `purchasePrice`. Watchlists have ticker + price + grade. No real per-position
  daily price history → no real sparkline (`ClavixMiniSpark` uses a
  deterministic zigzag placeholder, which is the honest current state).
- **Classification:** `PARTIAL`
- **Port plan:** The structure is mostly in place. Remaining gaps:
  1. Toolbar pills are decorative today — sort order is fixed. Wire each pill
     to a `@State private var sortKey` and re-sort `viewModel.holdings`.
  2. Sector composition bars (`VQASectorBar`) — render from the same
     `sectorRows` derivation used in `DigestView.sectorExposure`; do not
     hard-code "Conglomerate".
  3. `WatchlistRow` currently uses the legacy `GradeBadge` and the old
     metric layout. Rewrite to `VQATrackedTickerLedgerRow` (ticker + name +
     mini spark + price + day change + grade + delta).
- **Backend gap:** `WatchlistItem` exposes price but not `day_change_pct` or
  `score_delta` — backfill those when the watchlist enrichment endpoint
  lands (existing P1 backlog item 1). Until then, render `—` for those
  columns.

### `add-holding` — `ClavixVisualQAAddPositionMethod`

- **Live counterpart:** none — `HoldingsAddSheet` in `HoldingsListView.swift`
  jumps straight to the manual ticker/shares/cost form
- **View model / data source:** `HoldingsViewModel.addHolding`,
  `BrokerageViewModel.startConnect`, CSV import (mock)
- **VQA fixture data shape:** four `VQAMethodCard`s (Search universe /
  Refresh from brokerage / Enter manually / Upload CSV)
- **API shape today:** `/tickers/search`, `/brokerage/connect`, `/holdings`
- **Classification:** `PORTABLE` (after a small refactor)
- **Port plan:** Wrap the existing manual form in a method picker. Add a
  `HoldingsAddMethodSheet` with four `ClavixCard`-method-cards; "Enter
  manually" navigates to the current `HoldingsAddSheet`; "Search universe"
  pushes the user to the Search tab; "Refresh from brokerage" calls
  `brokerageViewModel.syncNow()` if connected, else triggers the connect
  flow; CSV stays a "coming soon" sheet.
- **Backend gap:** none (CSV is structural; see Onboarding).

### `holding-manual` — `ClavixVisualQAAddPositionManual(outside: false)`

- **Live counterpart:** `HoldingsAddSheet` inside `HoldingsListView.swift`
- **View model / data source:** `HoldingsViewModel.addHolding`,
  `searchTickers`
- **VQA fixture data shape:** `ClavixScreen` · card with Ticker / Shares /
  Cost basis rows · Save position dark button
- **API shape today:** `POST /holdings` with `{ticker, shares, purchase_price}`
- **Classification:** `PORTABLE`
- **Port plan:** Restyle existing fields with `VQAInputRow`-equivalent: 48pt
  height, paper2 fill, mono caption. Wrap in `ClavixScreen(eyebrow: "Manual
  entry", title: "Add position")`. Keep ticker suggestions list rendered as a
  `ClavixCard(padding: 0)` ledger of `SearchResultRow`s. Keep purchase-date
  TODO line as a `ClavixEyebrow` caption.
- **Backend gap:** `POST /holdings` does not accept `purchase_date` — the
  TODO already calls this out; do not lie about it.

### `holding-outside` — `ClavixVisualQAAddPositionManual(outside: true)`

- **Live counterpart:** none — the live sheet rejects unsupported tickers
  outright (`isTickerSupported` gate)
- **View model / data source:** `HoldingsViewModel.addHolding` (needs
  `allow_outside_universe=true` support on the wire model)
- **VQA fixture data shape:** same as `holding-manual` plus an additional
  warn-soft `ClavixCard` explaining limited data
- **API shape today:** `POST /holdings` does NOT yet accept
  `allow_outside_universe` from the iOS encoder (`CreateHoldingRequest`
  doesn't include it), even though backend supports it.
- **Classification:** `PARTIAL`
- **Port plan:** Add `allow_outside_universe: Bool?` to
  `APIService.CreateHoldingRequest`. Surface a "Save anyway as outside-universe"
  affordance when `searchTickers` returns `isSupported == false`. Add the
  warn-soft explanatory card.
- **Backend gap:** Backend already supports
  `positions.outside_universe = true`; iOS wire model needs to opt in.

### `edit-holding` — `ClavixVisualQAEditPosition`

- **Live counterpart:** none — holdings can only be deleted today (via swipe
  action in `HoldingsListView`); shares / cost basis / account cannot be
  edited
- **View model / data source:** `HoldingsViewModel.deleteHolding` exists; no
  edit method
- **VQA fixture data shape:** `ClavixScreen` · card with Shares / Cost basis
  / Account rows · Save changes dark button
- **API shape today:** No `PATCH /holdings/{id}` route exists.
- **Classification:** `STRUCTURAL`
- **Port plan:** Defer until backend ships an edit endpoint.
- **Backend gap:** Add `PATCH /holdings/{id}` to update shares /
  purchase_price / account. New backlog item.

### `delete-confirm` — `ClavixVisualQADeleteConfirm`

- **Live counterpart:** `.alert("Delete holding?", …)` in `HoldingsListView`
- **View model / data source:** `HoldingsViewModel.deleteHolding`
- **VQA fixture data shape:** `ClavixScreen` · bad-soft `ClavixCard` warning
  · Remove (bad fill) + Keep (paper outline) buttons
- **API shape today:** `DELETE /holdings/{id}`
- **Classification:** `PORTABLE`
- **Port plan:** Replace the system `.alert` with a half-sheet that renders
  the VQA layout. Reuse `viewModel.deleteHolding(_:)`.
- **Backend gap:** none.

### `free-limit` — `ClavixVisualQAFreeLimitReached`

- **Live counterpart:** `HoldingsUpgradeSheet` inside `HoldingsListView.swift`
- **View model / data source:** `HoldingsViewModel.subscriptionTier`,
  `holdings.count >= 3`
- **VQA fixture data shape:** `ClavixScreen` · accent-soft `ClavixCard`
  upsell · View Pro (accent) + Manage positions (outline) buttons
- **API shape today:** `/preferences.subscription_tier`
- **Classification:** `PARTIAL` (visual port portable; "View Pro" CTA is the
  StoreKit-blocked path)
- **Port plan:** Restyle the existing `HoldingsUpgradeSheet` using
  `ClavixCard(fill: .clavixAccentSoft)` and accent button. CTA shows the
  existing "Pro is coming soon" message until StoreKit lands.
- **Backend gap:** StoreKit (out-of-scope).

### `brokerage-sync` — `ClavixVisualQABrokerageSync`

- **Live counterpart:** brokerage section of `Views/Settings/SettingsView.swift`
- **View model / data source:** `BrokerageViewModel.status` from
  `/brokerage/status`
- **VQA fixture data shape:** `ClavixScreen` · "Connected" card · settings
  group (Positions count, Accounts count, Auto-sync) · "Sync now" dark
  button
- **API shape today:** `BrokerageStatusResponse` exposes `connected`,
  `autoSyncEnabled`, `lastSyncAt`, `connections[]`, `accounts[]`. The
  Positions count is `viewModel.holdings.filter { $0.isBrokerageSynced }.count`
  — derived client-side from the existing Position payload.
- **Classification:** `PARTIAL`
- **Port plan:** Promote the inline Brokerage section in `SettingsView` to a
  navigation destination (or sheet) styled like the VQA reference. Wire the
  Positions count via a small helper on `HoldingsViewModel`. Status copy
  "Live" maps to `BrokerageViewModel.isConnected`.
- **Backend gap:** SnapTrade credentials (out-of-scope).

---

## Search

### `search` (tab) — `ClavixVisualQASearch`

- **Live counterpart:** `ios/Clavis/Views/Search/SearchView.swift`
- **View model / data source:** `APIService.searchTickers`, local
  `UserDefaults` for recents
- **VQA fixture data shape:** sticky search header · "Last viewed" recents
  ledger · "Trending" ledger · "Browse" quick-filter pills · debug links to
  the no-results / outside-universe states
- **API shape today:** `/tickers/search?q=…&limit=…` returns
  `TickerSearchResponse` (ticker, companyName, price, grade, safetyScore,
  sector, industry, isSupported, sharedAnalysis). No trending endpoint, no
  browse-filter endpoint.
- **Classification:** `PARTIAL`
- **Port plan:** Already mostly built. Remaining work:
  1. "Trending" section currently renders a placeholder card — leave that
     copy honest until search telemetry exists (existing backlog item P1#6).
  2. Browse pills currently mutate the query to seed a search — keep that
     behaviour but rename pills to match VQA copy: "S&P 500", "ETFs", "Mega
     caps", "Dividend aristocrats", "High-grade only", "Recently downgraded".
- **Backend gap:** trending source; browse filter params (both already
  backlog'd at P1#5 and P1#6).

### `search-none` — `ClavixVisualQASearchNoResults`

- **Live counterpart:** inline state in `SearchView.queryResultsSection`
- **View model / data source:** `SearchView.results.isEmpty`
- **VQA fixture data shape:** `ClavixScreen` · single `ClavixCard` with "No
  match" copy
- **Classification:** `PORTABLE` — already covered inline; no separate
  screen needed.

### `search-outside` — `ClavixVisualQASearchOutsideUniverse`

- **Live counterpart:** inline outside-universe row in
  `SearchView.SearchResultRow` (shows `· OUTSIDE` tag)
- **View model / data source:** `TickerSearchResult.isSupported`
- **VQA fixture data shape:** `ClavixScreen` · warn-soft `ClavixCard`
  explaining limited dimension coverage
- **Classification:** `PARTIAL`
- **Port plan:** The inline `· OUTSIDE` tag is already correct. To match the
  full VQA screen, gate the explanatory card behind tapping the outside row
  → routes to `TickerDetailView` which already renders an
  `outsideUniverseBanner`. No new screen needed.
- **Backend gap:** none.

---

## Ticker Detail + Audits

### `ticker` — `ClavixVisualQATickerDetail`

- **Live counterpart:** `ios/Clavis/Views/Tickers/TickerDetailView.swift`
- **View model / data source:** `APIService.fetchTickerDetail`,
  `fetchTickerMethodology`, `fetchPriceHistory`, `fetchScoreHistory`
- **VQA fixture data shape:** Hero card (composite grade + score + delta + 5-axis
  radar + position line + last price) · Price 1M card · Five dimensions
  ledger (FIN/NEWS/MAC/SEC/VOL with score bar + delta + chevron) · Key
  drivers (HEADWIND / PRESSURE / TAILWIND tone-tinted `VQADriverCard`s) ·
  Executive summary (Bull/Risk/What to watch tinted accent card) · Recent
  news ledger (T1/T2/T3 badge + source + tldr) · Score history with toggles
  (Composite/News/Macro) · Refresh data + Tracked ticker action bar
- **API shape today:** `TickerDetailResponse` provides all of this:
  `currentScore`, `dimensionBreakdown`, `sharedAnalysis.summary` (grade,
  scoreDelta, riskDimensions), `sharedAnalysis.executiveSummaryBreakdown`
  (bullCase/riskCase/whatToWatch — backend may omit), `riskDrivers[]`,
  `recentNews[]`, `freshness`. `fetchScoreHistory` gives the 90-day chart.
- **Classification:** `PARTIAL` (Cycle 3 already landed most of this)
- **Port plan:** Cycle 3 already covers hero radar, executive summary,
  driver cards, news cards, score history with period chips. Open items:
  1. SUMMARY chip in the trailing nav bar (scrolls to executive-summary) —
     currently a debug-route harness only; promote to a real nav-bar button.
  2. Per-dimension delta values: render `—` when `scoreDelta` is unavailable
     per dimension (the API does not expose per-dimension deltas today, only
     composite — keep "—" honest).
  3. Drivers tone tag (HEADWIND / PRESSURE / TAILWIND) is in `Cycle 1`;
     verify mapping covers `direction == "watch"` → PRESSURE.
- **Backend gap:**
  `shared_analysis.executive_summary_breakdown.{bull_case,risk_case,what_to_watch}`
  must be populated server-side — existing backlog item Hi-Fi Cycle 3 #1.
  Per-dimension `score_delta` does not exist; backend follow-up.

### `ticker-live` / `ticker-live-summary` — debug harness routes

- **Live counterpart:** `TickerDetailDebugHarness` (DEBUG-only)
- Used for screenshot diffing without depending on production data. Not a
  separate screen to port.

### `ticker-held` — `ClavixVisualQATickerHeldState`

- **Live counterpart:** rendered inline as `TickerDetailView` when
  `userContext.isHeld == true` (no dedicated "already held" gate)
- **View model / data source:** `TickerDetailResponse.userContext.isHeld`
- **VQA fixture data shape:** `ClavixScreen` · `ClavixCard` with grade +
  "NVDA is already in your book" + shares/weight · View risk profile / Edit
  position buttons
- **Classification:** `PARTIAL`
- **Port plan:** This is the "Add holding" path when the user tries to add a
  ticker they already hold. Add a guard in the add-holding submit handler:
  if `viewModel.holdings.contains(where: { $0.ticker == ticker })`, surface
  a `ClavixCard` with the existing row data + "View risk profile" (→
  `TickerDetailView`) and "Edit position" (→ structural, see `edit-holding`).
- **Backend gap:** none (held check is client-side).

### `methodology` — `ClavixVisualQAMethodology`

- **Live counterpart:** `ios/Clavis/Views/Tickers/MethodologyDrawerSheet.swift`
  (presented as a sheet from `TickerDetailView` — the live UX is "drawer of
  five expandable rows", not "single page with formula + grade bands")
- **View model / data source:** `APIService.fetchTickerMethodology`
- **VQA fixture data shape:** Composite hero (grade + score + delta) ·
  Formula card (`VQACodeCard` showing equal-weighted formula calculation) ·
  Five-dimension input ledger (`VQAMethodologyInputRow`s with source line
  + refresh timestamp + score + chevron) · Grade-bands reference table
  (AAA→F)
- **API shape today:** `MethodologyResponse` exposes per-dimension
  inputs (`debt_to_equity`, `fcf_margin`, `articles[]`, `coefficients{}`,
  `sector_beta`, `realized_vol_30d`, …). No `formula` string field, no
  precomputed `source_line` or `refreshed_at_human` field — these are
  rendered client-side today.
- **Classification:** `PARTIAL`
- **Port plan:** Build a dedicated full-screen
  `MethodologyView(ticker:methodology:)` that renders:
  1. Composite hero from `methodology.composite.{grade,score}`. Delta is not
     exposed → render `—`.
  2. Static `ClavixCard` with the equal-weighted formula derived from the
     five `MethodologyResponse.dimensions.*.score` values — this is honest
     arithmetic, not a fabricated source string.
  3. Five-row input ledger; each row's source/refresh line is a static
     mapping based on dimension key (see `VQAMethodologyInputRow.sourceLine`
     in the VQA file) — fine to inline these strings, they describe the
     pipeline, not user-specific data.
  4. Grade-bands reference table — static data (`VQAGradeBand.bands`).
  Replace the existing `MethodologyDrawerSheet` flow with this navigation
  destination; the per-dimension audit views (`FinancialHealthAuditView`
  etc.) become the destinations of each row tap.
- **Backend gap:** per-dimension `delta` and `dimension_inputs_score_delta`
  are not exposed; render `—`. Existing backlog item Hi-Fi Cycle 3 #2.

### `methodology-page` — `ClavixVisualQAMethodologyPage`

- **Live counterpart:** `MethodologyView` inside
  `Views/Settings/SettingsView.swift` (a custom step list, very different
  from the VQA "Contents + Audit pages + Excerpt" reference page)
- **View model / data source:** none (static)
- **VQA fixture data shape:** `ClavixScreen` · serif hero ·
  "CONTENTS" + "AUDIT PAGES" settings groups · numbered excerpt block
- **Classification:** `PORTABLE`
- **Port plan:** Rebuild `Views/Settings/SettingsView.swift > MethodologyView`
  as a `ClavixScreen(eyebrow: "Reference · v2.0", title: "Methodology")` with
  the two settings groups linking to the same audit views the ticker
  drill-down uses (Financial/News/Macro/Sector/Volatility).
- **Backend gap:** none.

### `methodology-financial` / `-news` / `-macro` / `-sector` / `-volatility` — `ClavixVisualQAAuditDetail`

- **Live counterparts:** `Views/Tickers/FinancialHealthAuditView.swift`,
  `NewsSentimentAuditView.swift`, `MacroExposureAuditView.swift`,
  `SectorExposureAuditView.swift`, `VolatilityAuditView.swift`
- **View model / data source:** `MethodologyResponse.dimensions.*`
- **VQA fixture data shape (per dimension):** Score hero (eyebrow ·
  large mono score · delta + weight · score bar with 0/50/100 axis) ·
  Formula card · Raw inputs ledger (label + value + benchmark) · Optional
  Narrative card · Data lineage (source · last refreshed · cadence ·
  distance to next band) · Dimension-specific extras (News articles ledger
  for NEWS; Macro factor levels for MAC) · "Recompute now" button
- **API shape today:**
  - **Financial Health:** `debt_to_equity`, `fcf_margin`, `interest_coverage`,
    `current_ratio`, `revenue_growth_trend`, `profitability_trend`,
    `peer_comparisons[]`, `sector_median_comparison{}`. `as_of_date`,
    `data_source` are exposed. No `formula` string and no benchmark column;
    sector medians are mostly empty in prod (existing backlog item Hi-Fi
    Cycle 3 #3).
  - **News Sentiment:** `score`, `article_count_7d`, `volume_signal`,
    `weighted_score`, `articles[]` (full `MethodologyArticle`),
    `article_histogram_14d[]`, `sentiment_distribution[]`. Source/tier mix
    (`T1/T2/T3 count`) is not pre-aggregated; derive client-side from
    `articles[i].sourceTier`.
  - **Macro Exposure:** `r_squared`, `trading_days_used`, `limited_data`,
    `coefficients{tnx,dxy,wti,vix,spy}`, `current_factor_levels{}`,
    `narrative`. Per-factor `β` and current value drive the ledger directly.
  - **Sector Exposure:** `sector`, `sector_etf`, `sector_beta`,
    `sector_momentum_30d`, `sector_breadth`, `narrative`,
    `peer_comparisons[]`, `sector_median_comparison{}`. No `narrative_adjustment`
    or `breakdown_into_quant_vs_narrative` field.
  - **Volatility:** `realized_vol_30d`, `realized_vol_90d`, `vol_ratio`,
    `max_drawdown_252d`, `beta_to_spy`, `iv_rank`, `implied_volatility`,
    `iv_source`, `as_of_date`.
- **Classification:** `PARTIAL` for all five.
- **Port plan:** Rebuild each `*AuditView` to the VQA shape:
  - Score hero card with `ClavixScoreBar`, mono delta (`—` when not exposed
    per dimension), "weighted 20% in composite" caption.
  - Formula card: render an honest formula card with the same static text
    used in `VQAAuditModel.{financial,news,macro,sector,volatility}.formula`
    in the VQA file — these are descriptive, not fabricated numbers.
  - Raw inputs ledger: one row per real backend field. `benchmark` column
    populates from `sector_median_comparison[metric].median` when present,
    else omit.
  - Narrative card: render only when `narrative`/`sentiment_reason` is
    populated; never fabricate.
  - Data lineage: source string from
    `VQAMethodologyInputRow.sourceLine` static mapping + `as_of_date`. "Distance
    to next band" is derivable from `score` and the static `VQAGradeBand`
    table.
  - News-specific extras: articles ledger reuses
    `Views/Tickers/NewsSentimentAuditView`'s article cards but restyled to
    `VQANewsLedgerCard` (T1/T2/T3 badge + source + relative time + sentiment
    dot + headline + "Why this score? · weight N" tap → `ArticleDetailSheet`).
  - Macro-specific extras: factor levels card with the 10Y / DXY / VIX live
    values from `currentFactorLevels`.
- **Backend gap:** sector medians sparse; per-dimension deltas missing; no
  pre-aggregated T1/T2/T3 source mix counts (derivable client-side, so not
  a true gap). These are the same items already on the backlog under Cycle
  3 #2 and #3.

---

## Methodology / Article

### `article` — `ClavixVisualQAArticle`

- **Live counterpart:** `ios/Clavis/Views/Tickers/ArticleDetailSheet.swift`
  (sheet, not a navigation destination)
- **View model / data source:** `MethodologyArticle` (a value type passed
  through the sheet, no fetch)
- **VQA fixture data shape:** Impact pill ("HIGH IMPACT") + tier + relative
  time · headline · "Brief" body paragraph · accent-soft portfolio-context
  `ClavixCard` · risk-signal card with sentiment score · "Read full article
  at Reuters →" outline button
- **API shape today:** `MethodologyArticle` includes `title`, `source`,
  `publishedAt`, `sourceTier`, `sentimentScore`, `sentimentReason`,
  `impactTag`, `tldr`, `whatItMeans`, `keyImplications[]`, `sourceUrl`,
  `personalisedStructural`, `personalisedNarrative`. Portfolio context
  ("NVDA is 15.6% of your book…") is not on the article payload; it would
  need to be derived from `viewModel.holdings`.
- **Classification:** `PARTIAL`
- **Port plan:** Restyle `ArticleDetailSheet` with `ClavixCard`s and VQA
  typography. Map:
  - Impact pill ← `article.impactTag` (already shown but in legacy style).
  - Brief ← `article.tldr` or first paragraph of `whatItMeans`.
  - Portfolio context ← derive at present time from the held position's
    `portfolioWeight × 100` rounded to one decimal; render only when the
    article's `ticker` matches a held position.
  - Risk signal ← `article.sentimentScore` with `sentimentReason`.
  - Read full article ← `article.sourceUrl` (already wired).
- **Backend gap:** none — derivations are client-side.

### `article-paywalled` / `article-failed` — `ClavixVisualQAArticleState`

- **Live counterpart:** none — `ArticleDetailSheet` shows the article body
  unconditionally; there is no paywalled/failed branch
- **View model / data source:** would need `MethodologyArticle.extraction_status`
  / `paywall_state` (NOT currently exposed)
- **VQA fixture data shape:** `ClavixScreen` · single warn-soft (paywalled)
  or bad-soft (failed) `ClavixCard` with explanatory copy
- **Classification:** `STRUCTURAL`
- **Port plan:** Defer until article extraction state is exposed.
- **Backend gap:** `shared_ticker_events.extraction_status` exists in the
  DB but is not surfaced on `MethodologyArticle`. Backlog item.

---

## Alerts

### `alerts` (tab) — `ClavixVisualQAAlerts`

- **Live counterpart:** `ios/Clavis/Views/Alerts/AlertsView.swift`
- **View model / data source:** `AlertsViewModel`, `/alerts`
- **VQA fixture data shape:** filter chips with counts · day separators ·
  unread accent-strip rows with category pill (GRADE/MACRO/NEWS/TRACK/PORT)
  + time + headline + body + grade/delta · "Load earlier" outline button
- **API shape today:** `Alert` has `type`, `previous_grade`, `new_grade`,
  `change_details{score_delta}`, `message`, `created_at`. v2 fields
  (`severity`, `destination_type`, `destination_id`, `read_at`) defined in
  schema but not yet on `Alert` decoder (handoff doc notes "when backend
  sends"). Unread state is tracked via `UserDefaults.lastSeenAt` until
  `read_at` ships.
- **Classification:** `PARTIAL`
- **Port plan:** The structure is already in place. Remaining gaps:
  1. Add `read_at` to `Alert` decoder so unread state is server-truth instead
     of UserDefaults-derived.
  2. "Load earlier alerts" button is a no-op today; wire to a paginated
     `/alerts?before=…&limit=…` query (no backend route yet → keep as TODO).
- **Backend gap:** `read_at` on Alert payload; pagination endpoint.

### `alerts-empty` — `ClavixVisualQAAlertsEmpty`

- **Live counterpart:** `AlertsView.emptyState`
- **View model / data source:** `AlertsViewModel.alerts.isEmpty`
- **Classification:** `PORTABLE` — already covered inline; matches the VQA
  layout (bell.slash icon + "All quiet." + caption).

### `alert-detail` — `ClavixVisualQAAlertDetail`

- **Live counterpart:** none — tapping an alert routes to either the digest
  tab, the holdings tab, or a ticker detail (see `AlertsView.handleAlertTap`).
  There is no per-alert detail screen.
- **View model / data source:** would need `GET /alerts/{id}` (does not
  exist)
- **VQA fixture data shape:** Category pill + time · headline ·
  hysteresis-cleared explanation · Before/Now grade comparison card · driving
  dimension score bar · accent-soft portfolio-context card · driving-articles
  ledger (3 `VQANewsLedgerCard`s) · Open NVDA detail / Adjust threshold
  buttons
- **API shape today:** `Alert` has `previous_grade`, `new_grade`,
  `change_details{score_delta}`. No hysteresis proof, no per-dimension
  before/after, no driving-articles array.
- **Classification:** `STRUCTURAL`
- **Port plan:** Defer until `GET /alerts/{id}` lands. Existing backlog
  P0#13.

### `notification-prefs` — `ClavixVisualQANotificationPrefs`

- **Live counterpart:** `alertsSection` + `quietHoursSection` in
  `Views/Settings/SettingsView.swift`
- **View model / data source:** `SettingsViewModel` (`alertsGradeChanges`,
  `alertsMajorEvents`, `alertsPortfolioRisk`, `quietHoursEnabled`,
  `quietHoursStart/End`), `APIService.updateAlertPreferences`
- **VQA fixture data shape:** `ClavixScreen` · DELIVERY group (Morning
  Report on/off, Quiet hours range) · RULES group (Grade changes, Major
  news, Macro shock, Tracked ticker alerts — last marked "Pro")
- **API shape today:** `PreferencesResponse` covers grade changes, major
  events, portfolio risk, large price moves, quiet hours. There is no
  separate "macro shock" or "tracked ticker alerts" preference column —
  P1#7 covers this.
- **Classification:** `PARTIAL`
- **Port plan:** Promote alerts + quiet hours into a dedicated
  `NotificationPrefsView` reachable from Settings ("Notifications"). Render
  the unimplemented prefs (`Macro shock`, `Tracked ticker alerts`) as
  disabled rows with "Coming soon" caption until P1#7 lands.
- **Backend gap:** `alerts_macro_shock`, `alerts_watchlist`,
  `alerts_digest_ready`, `alert_severity_threshold` columns (existing P1#7).

---

## Settings / Profile

### `settings` (tab) — `ClavixVisualQASettings`

- **Live counterpart:** `ios/Clavis/Views/Settings/SettingsView.swift`
- **View model / data source:** `SettingsViewModel`, `BrokerageViewModel`
- **VQA fixture data shape:** Five settings groups (Profile, Morning Report,
  Brokerage, Reference, Account) where each row is a `VQASettingRow` (title
  + value + optional detail). All rows tap-through to a sub-screen.
- **API shape today:** `/preferences` (digest_time, summary_length,
  weekday_only, name, birth_year, subscription_tier, quiet hours, alert
  prefs); `/brokerage/status`; `/account/export`; `/account` (DELETE).
- **Classification:** `PARTIAL`
- **Port plan:** The existing Settings is fully functional but uses an
  in-page accordion-style layout for everything. Rebuild as 5 navigation
  destinations matching VQA: Profile, Morning Report (delivery time +
  length), Brokerage (sync status), Reference (methodology), Account
  (Export / Support & legal / Delete). The detail string on the Profile row
  ("Pro trial · 10 days remaining") depends on StoreKit and stays "Free" /
  "Pro" only until then.
- **Backend gap:** trial days remaining requires entitlement contract
  (out-of-scope).

### `profile` — `ClavixVisualQAProfile`

- **Live counterpart:** `accountHeader` row inside `SettingsView`
- **View model / data source:** `SettingsViewModel.userName`, `userEmail`,
  `subscriptionTier`; `APIService.updateProfile`
- **VQA fixture data shape:** `ClavixScreen` · profile card with name +
  email + PRO badge · DETAILS group with Display name / Birth year / Region
- **API shape today:** `PreferencesResponse` exposes `name`, `birth_year`,
  `subscription_tier`. No `region` field.
- **Classification:** `PARTIAL`
- **Port plan:** Promote `accountHeader` to a navigation destination with
  editable Name / Birth year fields wired to `APIService.updateProfile`.
  Omit Region row until backend supports it.
- **Backend gap:** no `region` column; not critical for v1.

### `support-legal` — `ClavixVisualQASupportLegal`

- **Live counterpart:** `legalSection` rows in `SettingsView`
- **View model / data source:** static URLs
- **VQA fixture data shape:** `ClavixScreen` · SUPPORT group (Email,
  Status) · LEGAL group (Terms, Privacy, Methodology)
- **Classification:** `PORTABLE`
- **Port plan:** Add a `SupportLegalView` destination; wire Email to
  `mailto:support@getclavix.com`, Status to a static "Online" string (no
  status endpoint), Terms/Privacy/Methodology to existing public URLs.
- **Backend gap:** none.

---

## Tracked tickers

### `watchlist` / `tracked-tickers` — `ClavixVisualQATrackedTickers`

- **Live counterpart:** `watchlistSection` inside `HoldingsListView`
- **View model / data source:** `HoldingsViewModel.watchlistItems`,
  `/watchlists`
- **VQA fixture data shape:** `ClavixScreen` · ledger of three
  `VQAHoldingRow`s (ticker + name + tracked-ticker line · grade + value +
  today%) · Add tracked ticker dark button
- **API shape today:** `WatchlistItem` exposes ticker + companyName +
  price + grade + safetyScore + sharedAnalysis. No `today%` or
  `score_delta`.
- **Classification:** `PARTIAL`
- **Port plan:** Replace the inline `watchlistSection` in
  `HoldingsListView` with a navigation destination. Render each row as
  `VQATrackedTickerLedgerRow` (ticker + name + mini spark + price + day%
  + grade + delta) — render `—` for day% and delta until backend ships
  them.
- **Backend gap:** `day_change_pct` and `score_delta` on `WatchlistItem`
  (existing P1#1).

### `watchlist-add` / `tracked-add` — `ClavixVisualQATrackedTickerAdd`

- **Live counterpart:** none — adding to watchlist happens silently via
  `HoldingsViewModel.addTickerToWatchlist(_:)` when the user taps a search
  result. There's no dedicated "search + COMMON NAMES suggestions" sheet.
- **View model / data source:** `HoldingsViewModel.addTickerToWatchlist`,
  `APIService.searchTickers`
- **VQA fixture data shape:** `ClavixScreen` · search card · COMMON NAMES
  settings group with AMD/META/TSLA + their grades
- **API shape today:** `/tickers/search`, `/watchlists/default/items`
- **Classification:** `PARTIAL`
- **Port plan:** Build a `WatchlistAddSheet` reachable from the watchlist
  ledger trailing "+" button. Wire search + a static "common names"
  shortlist (top-5 mega caps). Honest grades come from a one-shot batch
  call to `/tickers/search?q=AMD,META,TSLA…`.
- **Backend gap:** none.

### `watchlist-convert` / `tracked-convert` — `ClavixVisualQATrackedTickerConvert`

- **Live counterpart:** none — there is no "convert tracked → position"
  flow today; users must add manually via Holdings
- **View model / data source:** `HoldingsViewModel.addHolding` +
  `removeTickerFromWatchlist`
- **VQA fixture data shape:** `ClavixScreen` · `ClavixCard` explanation ·
  Shares / Cost basis inputs · "Add as position" dark button
- **API shape today:** `POST /holdings`, `DELETE /watchlists/default/items/{ticker}`
- **Classification:** `PORTABLE`
- **Port plan:** Reuse the manual-add form, pre-fill ticker from the
  watchlist row, on success call `removeTickerFromWatchlist(ticker)`.
- **Backend gap:** none.

---

## State / utility screens

The following routes are state branches, not stand-alone navigation
destinations. They are not separately portable; they should be rendered as
conditional cards inside the host view (which already has the data needed
to detect the state). They are listed for completeness; the work is to fold
them into the host view's body.

- `today-empty`, `today-error`, `offline`, `limited-data`,
  `insufficient-history`, `refresh-limit` — `ClavixVisualQAStateScreen`
  variants. Host views: `DigestView`, `TickerDetailView`, `ScoreHistoryChart`.
  The host views already have placeholder states; restyle them to the
  `ClavixCard` + glyph + serif body + CTA layout used by
  `ClavixVisualQAStateScreen`. **Classification: PORTABLE** as a single
  shared helper `ClavixStateCard(title:eyebrow:glyph:body:cta:tone:)`.

- `paywall`, `subscription-trial`, `subscription-active` — **Classification:
  STRUCTURAL.** Out of scope for this pass (StoreKit blocked).

- `export`, `delete-account` — **Classification: PARTIAL.** Live equivalents
  exist in `SettingsView` but as inline buttons + alerts. Promotable to
  dedicated screens that render the VQA layout when the user taps the
  relevant Settings row.
