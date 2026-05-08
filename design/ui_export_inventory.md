# UI Export Inventory

Read-only inspection deliverable. No production Swift, backend, or doc files were edited.

---

## 1. Current UI Export

- **Path:** [design/current-app-ui-export.html](current-app-ui-export.html)
- **Format:** Self-contained HTML with inline CSS. No React, Tailwind, external CSS, or external assets. Uses iPhone-shaped frames + annotation cards. Mock data is realistic (AAPL, MSFT, NVDA, JPM, SPY, ASML, TSLA, META, $214.32, AAA…F bond grades, score deltas, sample article TLDRs).

### Screens included (14 sections)

| # | Screen | Recreated from |
|---|---|---|
| 01 | Auth / Login | `Views/Auth/LoginView.swift`, `ViewModels/AuthViewModel.swift`, `Services/SupabaseAuthService.swift` |
| 02 | Onboarding (5 steps: Welcome → DOB → Risk ack → Notification prefs → Brokerage) | `Views/Onboarding/OnboardingContainerView.swift`, `ViewModels/OnboardingViewModel.swift`, `ViewModels/BrokerageViewModel.swift` |
| 03 | Dashboard / Home tab | `Views/Dashboard/DashboardView.swift`, `ViewModels/DashboardViewModel.swift`, `Models/Dashboard.swift` |
| 04 | Daily Digest ("Rating" tab) | `Views/Digest/DigestView.swift`, `ViewModels/DigestViewModel.swift`, `Models/Digest.swift` |
| 05 | Holdings + Watchlist + Search (combined) | `Views/Holdings/HoldingsListView.swift`, `ViewModels/HoldingsViewModel.swift` |
| 06 | Ticker Detail | `Views/Tickers/TickerDetailView.swift`, `Models/SharedTickerAnalysis.swift` |
| 07 | Methodology Drawer (5-dimension accordion) | `Views/Tickers/MethodologyDrawerSheet.swift`, `Models/Methodology.swift` |
| 08 | Article Detail sheet | `Views/Tickers/ArticleDetailSheet.swift` |
| 09 | Alerts | `Views/Alerts/AlertsView.swift`, `ViewModels/AlertsViewModel.swift` |
| 10 | Settings | `Views/Settings/SettingsView.swift`, `ViewModels/SettingsViewModel.swift`, `Models/UserPreferences.swift` |
| 11 | Settings → Methodology Overview + Score Explanation | `Views/Settings/SettingsView.swift` (`MethodologyView`, `ScoreExplanationView`, `ScoreBandRow`) |
| 12 | Paywall (NOT BUILT) | — no Swift file exists — |
| 13 | Dead / orphan UI inventory | `Views/Tickers/TickerDriverCardsSection.swift`, `Views/Tickers/ScoreHistoryChart.swift`, `Views/PositionDetail/PriceChartView.swift`, etc. |
| 14 | Add Position sheet + Add Position progress | `Views/Holdings/HoldingsListView.swift` (`AddPositionSheet`, `AddPositionProgressView`) |

### SwiftUI files inspected

App shell + design system:
- `ios/Clavis/App/ClavisApp.swift`
- `ios/Clavis/App/ContentView.swift`
- `ios/Clavis/App/MainTabView.swift`
- `ios/Clavis/App/ClavisDesignSystem.swift`
- `ios/Clavis/App/ClavisCopy.swift`
- `ios/Clavis/App/DisplayText.swift`

Views:
- `ios/Clavis/Views/Auth/LoginView.swift`
- `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift`
- `ios/Clavis/Views/Dashboard/DashboardView.swift`
- `ios/Clavis/Views/Digest/DigestView.swift`
- `ios/Clavis/Views/Holdings/HoldingsListView.swift`
- `ios/Clavis/Views/Tickers/TickerDetailView.swift`
- `ios/Clavis/Views/Tickers/TickerDriverCardsSection.swift`
- `ios/Clavis/Views/Tickers/MethodologyDrawerSheet.swift`
- `ios/Clavis/Views/Tickers/ArticleDetailSheet.swift`
- `ios/Clavis/Views/Tickers/ScoreHistoryChart.swift`
- `ios/Clavis/Views/PositionDetail/PositionDetailView.swift`
- `ios/Clavis/Views/PositionDetail/PriceChartView.swift`
- `ios/Clavis/Views/Alerts/AlertsView.swift`
- `ios/Clavis/Views/Settings/SettingsView.swift`
- `ios/Clavis/Views/Shared/Components/ClavisCardComponents.swift`

### Screens that could not be confidently recreated

- **Per-dimension full audit pages** (News Sentiment / Financial Health / Macro / Sector / Volatility) — they don't exist in the iOS source; only the in-drawer accordion is shipped. Nothing to recreate.
- **Digest variants A/B/C/D1/D2/D3** — only the single shipped digest layout exists. The wireframe variants are in the V2 wireframe file, not in the iOS app.
- **Some loading and error skeleton states** were shown only in concept (one card per family) rather than every variant.

---

## 2. Intended Wireframe Location

| File | Exists? | Notes |
|---|---|---|
| `design/clavix-wireframes-v2.html` | ✅ Yes | Main entrypoint — loads the JSX wireframe modules via Babel-standalone in browser |
| `design/clavix-figma-export.html` | ❌ No | File not present in the repo |
| `design/design-canvas.jsx` | ✅ Yes | DesignCanvas / DCSection / DCArtboard primitives (~48 KB) |
| `design/tweaks-panel.jsx` | ✅ Yes | Live tweaks / state controls |
| `design/wf-primitives.jsx` | ✅ Yes | Shared design tokens, typography, color, GradeBadge, SharpBox, etc. |
| `design/wf-digest.jsx` | ✅ Yes | Digest variants A, B, C, D1, D2, D3 |
| `design/wf-ticker.jsx` | ✅ Yes | Ticker detail variants A (Bars), B (Pills), C★ (Radar — chosen), D (Terminal); Methodology drawer + audits |
| `design/wf-screens.jsx` | ✅ Yes | Onboarding A/B, Holdings, Article Detail, Search, Alerts, Settings, Paywall |

### Current intended V2 source

**[design/clavix-wireframes-v2.html](clavix-wireframes-v2.html)** is the canonical entrypoint. It bootstraps React 18 + Babel-standalone in the browser and loads the JSX modules listed above. The V2 README inside it states the chosen directions:

- **Daily Digest:** A–C kept as variations; D split into D1 / D2 / D3 — all enforce macro → sector → positions order.
- **Ticker Detail:** **C (Radar) is the chosen direction** — radar chart hero, no composite sparkline, stock chart below hero, executive-summary drawer, "Why this score?" toggle, no fundamentals section.
- **Methodology:** quick drawer + four full audit pages (News Sentiment / Financial Health / Macro / Sector / Volatility — yes, four "audit pages" implementing the five dimensions).
- **Settings:** digest-alert toggle added, score-history row removed.
- **Paywall:** part of v2 scope.
- **Removed from v2:** Score History screen, 18d composite sparkline on ticker hero, Fundamentals & last filing section, formula display on audit pages, "LLM reasoning" label.

There is no `clavix-figma-export.html` — the only intended-wireframe surface is the React/JSX bundle above.

---

## 3. High-Level Difference Summary

### Screens mostly unchanged from the old MVP
- **Auth / Login** — credential-first, no product-first welcome. V2 wants a hero + value props + trial framing.
- **Onboarding (5 steps)** — still the legacy 5-step modal sequence with brokerage as step 5. V2 collapses to 2 screens (Welcome + Add Portfolio with three paths).
- **Dashboard / Home** — entire tab is legacy. V2 deletes Dashboard as a top-level tab.
- **Add Position sheet** — SwiftUI default light Form on a dark app — visually broken; not in V2 at all (V2 has a dedicated Add Portfolio screen with brokerage / CSV / manual cards).
- **Settings → Methodology Overview** — static "four dimensions" copy, stale vs. CLAVIX_TRUTH §6.

### Screens that already partially match V2
- **Holdings + Watchlist** — watchlist-as-inline-section, search bar at top of Holdings, sort/filter pills are correct in spirit. Mismatch: gold accents (`#F0C76C`, `#F3D58C`, `#FFE8A8 → #EABF57`) instead of burnt orange; alert-row tint for active grade-change alert isn't present.
- **Daily Digest** — sections include hero / macro / sector / position impacts / watchlist / what matters today. Close-ish but section names + ordering don't match the spec contract.
- **Methodology Drawer** — already a 5-dimension accordion with composite hero, source labels, refresh dates, per-article expansion. Inputs (D/E, FCF margin, etc.) match. Missing: distribution charts and "Full audit ↗" links.
- **Article Detail** — TLDR / What it means / Key implications / collapsed Why this score — already implemented. Missing: personalised holding-overlay box.
- **Alerts** — summary grid + filter chips + timeline rows are present. Missing: destination badges, quiet-hours callout, digest-ready alert type, finer event filter split.
- **Score Explanation** — bond-rating bands AAA…F — fully migrated.

### Screens missing entirely
- **Paywall** — no Swift file; no StoreKit/RevenueCat surface; no trial countdown anywhere.
- **Per-dimension Full Audit pages (5)** — V2 has News Sentiment / Financial Health / Macro / Sector / Volatility audit pages. Only the in-drawer accordion is shipped.
- **Standalone Universal Search** — embedded in Holdings only.
- **Article Detail personalised-implication box** (orange-tinted holding overlay).

### Screens that exist but are visually wrong
- **Ticker Detail** — has a square grade tile + score column instead of a radar; Fundamentals section is still rendered though V2 explicitly removes it; risk-dimension bars use `cornerRadius: 999` (pill ends) violating "sharp boxes / no pill ends"; trend arrows inverted vs. shared `RiskDirectionLabel` (↓ for improving here, ↑ for improving elsewhere); inline gold/cream color literals instead of design tokens.
- **Add Position sheet** — light SwiftUI default Form on dark app.
- **Holdings refresh button** — gold pill button breaks the design language.

### Screens that are functionally broken
- **Add Position progress bar** — `progressGrade` returns the literal string `"Analyzing…"`, which falls through `riskColor(for:)` to `textSecondary`; the bar is always grey.
- **Alerts header missing** — `AlertsTopHeader` defined but never inserted via `safeAreaInset`; the tab has no top header bar.
- **Methodology Overview copy** — says "four dimensions"; system is on five.
- **DashboardStatStrip Watchlist cell** — value is `morningFocusItems.count`, label says "Watchlist" — semantically mismatched.
- **Two parallel Key Drivers UIs** — the `TickerDriverCardsSection` v2-styled component is dead; the visible inline version uses ad-hoc hex colors.

### Backend / data gaps visible from the UI
- Ticker detail shows Fundamentals (P/E, Mkt cap, Volatility, Beta) — should disappear under V2; backend still emits these.
- Methodology drawer needs distribution-chart inputs, weighted-mean rows, and per-dimension-audit endpoints — not yet exposed.
- No `/articles/{id}` endpoint surfaces personalised holding overlay (cost basis, weight, P&L).
- Digest VM still hits `/dashboard` per AGENTS.md pitfall #1, not `/digest` — the six-section contract is unenforced.
- Alerts payloads lack destination metadata, score deltas, dimension drivers, and quiet-hours queue state.
- Free 3-holdings cap and watchlist 5-item cap are not enforced server-side in a way the UI surfaces.
- Subscription tier/trial-day/entitlement state isn't returned in `/preferences`.
- Custom URL scheme is still `clavis://` (`ClavisApp.swift`) — the iOS deep-link side hasn't switched to canonical `clavix://`.

---

## 4. Implementation Readiness

### Is the V2 wireframe clear enough to implement?

**Yes — for the visible screens.** Wireframe v2 ships every screen with annotations, design tokens, and copy. The chosen direction is explicit (Ticker C / Radar, plus 6 digest variants to pick from). The clearest gaps are:

- The **digest variant choice (D1 vs. D2 vs. D3)** is not yet locked. CLAVIX_TRUTH §9 prefers a "rating-agency memo" tone — that points to D3 (Tight ledger), but a product call is needed before building.
- The **per-dimension audit pages** show layout but assume backend audit data exists; backend Phase 2/Phase 4 must land first.
- The **paywall** is wireframed but the StoreKit/RevenueCat product setup is a separate Phase 8 dependency.

### Which SwiftUI screens need a full rewrite?

| Screen | Reason |
|---|---|
| `LoginView` | Add product-first welcome with three value props + trial framing before login fields. |
| `OnboardingContainerView` | Collapse from 5 steps to V2's 2-screen flow (Welcome + Add Portfolio with three paths). |
| `DashboardView` | Delete the tab. Move any unique data (Risk Contributors, What Changed) into Today/Digest. |
| `TickerDetailView` | Replace square-tile hero with radar chart hero; remove Fundamentals section; switch to flat sharp-box bars; consolidate the two Key Drivers implementations onto `TickerDriverCardsSection`; align trend arrow convention. |
| `AddPositionSheet` + `AddPositionProgressView` | Rebuild as the V2 Add Portfolio screen with brokerage/CSV/manual paths and dark design tokens. |
| Methodology full-audit pages (×5) | Build new — News Sentiment / Financial Health / Macro Exposure / Sector Exposure / Volatility. |
| Paywall | Build new — no surface exists today. |
| Universal Search | Build new — currently only an embedded search bar. |

### Which screens only need polish?

| Screen | Polish needed |
|---|---|
| `HoldingsListView` | Replace gold accents (`#F0C76C`, `#F3D58C`, `#FFE8A8 → #EABF57`) with burnt-orange tokens. Add alert-row tint for active grade-change alert. Enforce Free/Pro caps client-side. |
| `DigestView` | Reorder sections to match CLAVIX_TRUTH §9 contract; rename "Position impacts" to "Your positions"; remove `.capitalized` on `macroRelevance` and `urgency`; unify "Morning Rating" / "Morning Digest" copy; switch to D3 layout once chosen. |
| `MethodologyDrawerSheet` | Add mini distribution chart per dimension; add "Full audit ↗" link rows pointing to the new audit pages; add 7-day delta to composite header. |
| `ArticleDetailSheet` | Add personalised-implication box (orange-tinted overlay tied to user holding). |
| `AlertsView` | Mount `AlertsTopHeader` via `safeAreaInset`; add destination badges; split Events filter into News / Macro / Digest; add quiet-hours callout. |
| `SettingsView` | Add trial-day countdown, Verbose mode toggle, digest-ready alert toggle, watchlist alerts toggle, macro-shock alerts toggle, severity-threshold picker, friendly brokerage display name. |
| `MethodologyView` | Update step 03 copy from "four dimensions" to "five dimensions". |

### Backend / API gaps blocking the UI implementation

1. **Methodology audit endpoints** — `/tickers/{ticker}/methodology/{dimension}` with input rows, weights, distribution data, refresh timestamps. None exist yet.
2. **Article endpoint** — `/articles/{id}` with personalised holding overlay. Currently only embedded in ticker detail.
3. **Digest contract** — switch iOS calls from `/dashboard` to `/digest` and ensure six-section payload (Header, Overnight Macro, Sector Heat, Your Positions, Watchlist Updates, What to Watch Today).
4. **Holdings response** — needs portfolio composite, weighted grade, P&L, alert-highlight flag, watchlist inline list, holdings limit.
5. **Search response** — needs current grade, current price, in-portfolio flag, outside-universe reason, recent-tickers list.
6. **Alerts response** — destination type/id, score-delta details, dimension driver, digest-ready alert subtype, quiet-hours delivery state.
7. **Preferences response** — alerts_watchlist, alerts_macro_shock, alerts_digest_ready, alert_severity_threshold, trial_started_at/ends_at, subscription_status.
8. **Five-dimension scoring** — Financial Health is a Phase 2 backend deliverable; until it lands, the methodology drawer can render only legacy dimensions.
9. **Entitlements** — RevenueCat/StoreKit webhook table and entitlement state (Phase 8) — blocks Paywall.
10. **APNs** — `.p8` not deployed; `/health` reports `apns: missing` per AGENTS.md. Blocks any push-driven alert UX.

### What should be the next implementation phase?

Per the existing `docs/REFACTOR_PLAN.md`, the unblocked path is:

1. **Lock the Daily Digest variant** (D1 / D2 / D3 — recommendation: D3, the Tight Ledger, given the rating-agency tone in CLAVIX_TRUTH §2).
2. **Phase 5 — iOS Grade System & Design Token Update.** Most of this is done already (AAA…F grade enum, color tokens), but the residual A–F aliases (`riskA…riskF` legacy tokens used in LoginView, OnboardingView, DashboardView, HoldingsListView, AlertsView, PriceChartView) need full retirement. Standardise the trend-arrow convention, remove dead `@available(*, deprecated)` components, and remove the inline gold color literals.
3. **Phase 6 — iOS Screen-by-Screen Rebuild** (after Phase 6 step 0: complete `risk_scores` retirement). Build in dependency order: app shell tabs → onboarding → Today digest (D-variant) → Holdings + Watchlist → Ticker Detail (radar hero, no Fundamentals) → Search → Alerts → Settings → Paywall shell.
4. **Phase 7 — Methodology Drill-Down** (depends on Phase 4 endpoints landing): wire the in-app methodology drawer to the new audit endpoints, then build the five full audit pages.
5. **Phase 8 — Payments & Paywall** (after Phase 6 shell): RevenueCat/StoreKit, entitlements, trial-day countdown, paywall purchase flow.

The single highest-leverage piece to do **next** is locking the digest variant choice, then beginning Phase 6 with onboarding + Today digest, since those are the surfaces a brand-new Free user lands on first.
