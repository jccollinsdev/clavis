# Clavix UI System Map

## Purpose
This document is the working map for the iOS redesign pass. It captures the current live app structure, its screen-to-data relationships, and the biggest UX/system risks discovered before editing.

## App Entry And Navigation
- App entry: `ios/Clavis/App/ClavisApp.swift`
- Root gate: `ios/Clavis/App/ContentView.swift`
- Root flow:
  - Unauthenticated: `LoginView`
  - Authenticated but incomplete onboarding: `OnboardingContainerView`
  - Authenticated and onboarded: `MainTabView`
- Primary navigation shell: `ios/Clavis/App/MainTabView.swift`
- Tabs in production shell:
  - Today: `DigestView`
  - Holdings: `HoldingsListView`
  - Search: `SearchView`
  - Alerts: `AlertsView`
  - Settings: `SettingsView`
- Secondary drill-down surfaces:
  - Ticker detail: `TickerDetailView`
  - Article/detail narratives inside ticker detail
  - Methodology drawer: `MethodologyDrawerSheet`
  - Audit pages: `NewsSentimentAuditView`, `FinancialHealthAuditView`, `MacroExposureAuditView`, `SectorExposureAuditView`, `VolatilityAuditView`

## Current Screen Inventory
- Auth
  - `ios/Clavis/Views/Auth/LoginView.swift`
  - Mixed welcome, sign-in, sign-up, and reset states in one screen
- Onboarding
  - `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift`
  - Includes welcome step and add-portfolio path selection
- Today
  - `ios/Clavis/Views/Digest/DigestView.swift`
  - `ios/Clavis/Views/Digest/MorningReportView.swift`
- Holdings
  - `ios/Clavis/Views/Holdings/HoldingsListView.swift`
  - Includes add-holding flow, progress sheet, CSV-coming-soon sheet
- Search
  - `ios/Clavis/Views/Search/SearchView.swift`
- Alerts
  - `ios/Clavis/Views/Alerts/AlertsView.swift`
- Settings
  - `ios/Clavis/Views/Settings/SettingsView.swift`
  - Also contains profile, digest prefs, quiet hours, support/legal, export/delete, methodology explainer, upgrade sheet
- Ticker and methodology
  - `ios/Clavis/Views/Tickers/TickerDetailView.swift`
  - `ios/Clavis/Views/Tickers/MethodologyDrawerSheet.swift`
  - Per-dimension audit views in `ios/Clavis/Views/Tickers/`

## Data Sources And Endpoint Usage
- Shared network layer: `ios/Clavis/Services/APIService.swift`
- Auth/session: `ios/Clavis/Services/SupabaseAuthService.swift`
- Today tab data composition:
  - `/holdings`
  - `/preferences`
  - digest response path via `fetchTodayDigest(...)`
  - digest history via `fetchDigestHistory(...)`
  - `/alerts`
  - `/today`
- Holdings tab data composition:
  - `/holdings`
  - `/watchlists`
  - `/preferences`
  - brokerage status + sync endpoints
- Search:
  - `/tickers/search?q=...`
- Ticker detail:
  - `/tickers/{ticker}`
  - `/tickers/{ticker}/refresh`
  - `/tickers/{ticker}/refresh-status`
- Alerts:
  - `/alerts`
  - `/holdings`
  - `/preferences`
- Settings:
  - `/preferences`
  - `/account/export`
  - `/account`
  - profile and notification update endpoints

## Key Reusable UI Components
- Theme/tokens: `ios/Clavis/App/ClavisDesignSystem.swift`
- Shared card and shell vocabulary:
  - `ClavixCard`
  - `ClavixScreen`
  - `ClavixTabBar`
  - `ClavixAtmosphereBackground`
  - badge and gauge helpers inside the design system
- New/parallel visual QA components already present:
  - `ios/Clavis/App/ClavixVisualQA.swift`
  - `ios/Clavis/Views/Shared/ClavixHiFiReferenceView.swift`
  - `ios/Clavis/Views/Shared/Components/SectorHeatmapView.swift`

## Current Visual System
- Typography:
  - Inter for interface text
  - JetBrains Mono for data and numeric emphasis
- Color direction in tokens:
  - Mixed signals between dark-surface tokens and newer cream/paper references
  - Burnt orange accent used as primary brand/action color
  - Risk colors already expanded to the AAA-F bond-grade system
- Shape language:
  - Sharp-corner bias in `ClavisTheme`
  - Light-surface comments and dark-surface token aliases both exist
- Navigation:
  - Custom bottom tab bar instead of native `TabView`
- Motion:
  - Limited and inconsistent; more state-based than system-wide

## Major Pain Points
- Data-contract sprawl: several screens fetch multiple independent payloads and assemble state locally, which makes loading, error handling, and honesty about freshness inconsistent.
- Visual system split-brain: the codebase contains both older dark-system tokens and newer cream/paper VQA language, so the app risks looking half-migrated.
- Settings is overloaded: one file contains many detail screens and mixed concerns, which slows redesign and weakens information architecture.
- Today is not yet a single decisive morning briefing surface; it still behaves like a stitched composite of adjacent backend concepts.
- Trust cues are inconsistent: timestamps, freshness, limited-data messaging, and refresh states are not yet standardized across tabs.
- Some legacy product assumptions remain visible in comments and state names, especially around brokerage flows and backend-driven refresh states.
- Live backend latency can leak straight into UX: `/preferences`, `/tickers/search`, and ticker-detail dependencies can stall long enough to leave users staring at placeholders without enough context.
- Search and Alerts already have strong structural shells, but their empty/default states are too sparse to carry product trust on their own.
- Ticker detail is structurally credible but still brittle under partial-load conditions, which makes the trust center of the app feel less dependable than it should.

## Likely Dead, Duplicated, Or Transitional UI Surfaces
- `ios/Clavis/Views/PositionDetail/PositionDetailView.swift`
  - Likely transitional because ticker detail is the product’s canonical drill-down direction.
- `ios/Clavis/App/ClavixVisualQA.swift`
  - Useful as a reference harness, not a user-facing production surface.
- `ios/Clavis/Views/Shared/ClavixHiFiReferenceView.swift`
  - Debug-only parity aid, not production UI.
- `fetchDashboard()` still exists in `APIService`, while the product direction centers on Today/Digest-specific surfaces.

## Screens Most In Need Of Polish
- `LoginView`
  - Needs cleaner framing, lighter cognitive load, and a stronger product-first welcome state.
- `DigestView`
  - Most important screen, but still compositionally noisy and overly dependent on stitched backend fetches.
- `HoldingsListView`
  - Needs clearer separation between portfolio, watchlist, and sync/progress states.
- `TickerDetailView`
  - Core credibility screen; must feel premium, auditable, and honest about data quality.
- `SettingsView`
  - Needs simplification and stronger trust/utility hierarchy.

## Immediate Design Implications
- Standardize a single live production visual language before polishing individual screens.
- Tighten each primary tab around one dominant question:
  - Today: what changed and what matters now?
  - Holdings: what do I own and where is risk concentrated?
  - Search: what do we know about this ticker?
  - Alerts: what needs attention?
  - Settings: how does Clavix behave for me?
- Promote evidence, freshness, and limited-data disclosures into reusable components rather than per-screen ad hoc copy.
