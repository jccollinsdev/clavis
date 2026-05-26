# Clavix Backlog - VisualQA Data Gaps

Updated: 2026-05-25 (added "Prerequisites we do not own yet")
Source: `ios/Clavis/App/ClavixVisualQA.swift`, `docs/UI_ELEMENT_DATA_AUDIT.md`, `docs/BACKEND_DATA_GENERATION_PLAN.md`, `docs/UI_DATA_CONTRACT_MATRIX.md`, `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md`

This backlog is tied only to visible VisualQA gaps. It is not a generic refactor task list.

## 2026-05-26 - Hi-Fi Cycle 3 follow-ups

1. `/tickers/{ticker}` does not yet expose `shared_analysis.executive_summary_breakdown` with `bull_case`, `risk_case`, and `what_to_watch`. The Cycle 3 iOS card is wired to render those fields when present and omit them entirely when absent; the backend now needs to ship the real envelope.
2. `/tickers/{ticker}/methodology` still returns the older per-dimension payload and does not expose the Hi-Fi audit contract of `formula`, `inputs[]`, and `sector_medians[]` rows for each dimension. This blocks a true 1:1 rebuild of the five audit drill-down screens without fabricating rows client-side.
3. `sector_medians` is currently empty in production, so the drill-down medians table has no honest data source today even if the route shape is expanded.
4. `sector_regime_snapshots` currently stores `sector`, `snapshot_date`, `generated_at`, `data_status`, and ETF pricing fields, but not the `regime_state` column assumed by the parity checklist SQL. Update either the table/route or the verification query so the sector audit has a stable, documented contract.
5. Production route verification from this workspace is currently blocked by network timeouts to `https://clavis.andoverdigital.com` even though Supabase REST is reachable. Re-run the `/today`, `/holdings`, `/tickers/{ticker}`, `/tickers/{ticker}/score-history`, `/tickers/{ticker}/methodology`, `/alerts`, and `/preferences` curls once the tunnel/backend is responsive again.

## ⚠️ Prerequisites we do not own yet (decided 2026-05-25)

These three external dependencies are NOT in place and gate parts of the implementation. The current cycle builds everything that does NOT require them; once obtained, each unlock is a small bounded follow-up.

| Prerequisite | Cost / steps | What it unlocks | Stub behavior in the meantime |
|---|---|---|---|
| **Apple Developer Program** ($99/yr) | Apple ID → enrol → 24-48h verification → TestFlight + APNs key generation | Push notifications (APNs); TestFlight distribution; App Store submission; StoreKit | `services/apns.py` is a no-op logger. `/health` reports `apns: missing` honestly. `AlertsView` renders from the `alerts` DB table; alerts fire and store but never push to a device. |
| **StoreKit 2 setup** (depends on Apple Dev) | App Store Connect → create products (`clavix_pro_monthly`, `clavix_pro_annual`) → server-side webhook for entitlement verification → integrate StoreKit 2 client in iOS | Real paywall purchase flow; real Pro entitlement | "Mock paywall" — paywall screen renders Free/Pro comparison + price + 14-day trial CTA; CTA shows a "Subscriptions are coming soon" sheet. Admin route can flip `user_preferences.subscription_tier` manually to test Pro gates. |
| **SnapTrade developer account** (free dev tier) | snaptrade.com → create app → get client_id + secret → set env vars on VPS | Real brokerage sync (Robinhood, Schwab, Fidelity, etc.) | `/brokerage/*` routes return `{"status":"not_configured"}`. Holdings "Sync brokerage" CTA shows a "Brokerage sync is coming soon" sheet. `positions.synced_from_brokerage` column stays in schema; no code populates it. |

**Implementation impact:**
- Alert hysteresis engine + DB writes + in-app surface (`AlertsView`) all ship.
- Real APNs delivery sits behind `APNS_ENABLED=false`; flipping to `true` once the Apple Dev account is set up is a one-env-var change.
- Real paywall + StoreKit + SnapTrade ship as a single bundled follow-up cycle once all 3 prerequisites are in hand.

## P0 - Required To Make VisualQA Honestly Live

1. Add a VisualQA Today data envelope (`GET /today` or extended `/digest`) with portfolio value, day change, grade, composite score, generated timestamp, report preview, five-axis portfolio dimensions, sector cards, attention preview, top movers, and calendar.
2. Compute server-side portfolio value and portfolio day change from positions, latest price, and previous close.
3. Compute and persist value-weighted portfolio composite grade/score and five portfolio dimension rollups with real previous-day deltas only.
4. Add holdings envelope: portfolio summary, market value, weight, day change, P&L, score delta, highlight reason, limits, sync status, and enriched tracked tickers.
5. Add score-history endpoint or embedded score history array from `ticker_risk_snapshots`; show `-`/`New` when fewer than two real points exist.
6. Extend ticker detail contract with dimension deltas, last-refreshed timestamps, limited-data flags, hysteresis state, refresh allowance, article IDs, and action eligibility.
7. Complete methodology contract for all five dimensions: formula, raw inputs, weights, source rows, timestamps, limited-data flags, and score deltas.
8. Backfill Financial Health fundamentals needed by VisualQA audit pages: debt/equity, FCF margin, interest coverage, current ratio, revenue trend, profitability trend, and sector medians.
9. Populate `macro_regime_snapshots` and generate macro factor rows used by Today, Morning Report, and Macro Exposure audit.
10. Populate `sector_regime_snapshots` and sector ETF heat for Technology/XLK, Health Care/XLV, Financials/XLF, Energy/XLE, Consumer Discretionary/XLY, Consumer Staples/XLP, Industrials/XLI, Utilities/XLU, Materials/XLB, Real Estate/XLRE, Communication Services/XLC.
11. Extend `/digest` to guarantee the VisualQA six-section Morning Report contract with real portfolio deltas, sector ETF ledger rows, position grade/delta rows, tracked ticker rows, calendar events, and source/freshness footer.
12. Add alert read/unread support (`alerts.read_at`) and return unread counts, category counts, severity, destination metadata, grade-change metadata, and article/news metadata.
13. Add `GET /alerts/{id}` for VisualQA alert detail: before/after grade and score, hysteresis proof, driving dimension, source article rows, and portfolio context.
14. Add shared-event article detail endpoint over `shared_ticker_events` with TLDR, what-it-means, key implications, source tier, extraction status, paywall state, score/reason, and portfolio context.
15. Extend search results with price, day change, grade, score, held/tracked state, and outside-universe status.
16. Allow outside-universe manual position add in degraded mode per product truth; current backend hard-fails unsupported tickers despite `positions.outside_universe` existing.
17. Add add-position validation contract for duplicate held state, free limit, outside-universe eligibility, and degraded-mode warnings.
18. Enforce Free limits server-side for visible position/tracked ticker limits.
19. Define exact backend triggers for `limited-data`, `insufficient-history`, `offline`, `refresh-limit`, and `today-empty/error` states.
20. Normalize VisualQA sector taxonomy: use canonical sector names; avoid treating `Conglomerate` as a sector.

## P1 - Strong Production Experience

1. Add enriched tracked ticker endpoint or enriched watchlist payload with price, grade, score, delta, reason, and Pro/free limits.
2. Add market calendar cache/source for CPI/Fed/earnings rows and personalized holding/tracked ticker relevance.
3. Add source/freshness lineage arrays for Today and Morning Report.
4. Add search recent tickers, either local-only or server-backed, and enrich them before display.
5. Add browse filter support for S&P 500, ETFs, mega caps, high-grade only, and recently downgraded.
6. Hide or source trending search rows; do not claim `What others are looking at` without search/event telemetry.
7. Add notification preference columns: `alerts_watchlist`, `alerts_macro_shock`, `alerts_digest_ready`, `alert_severity_threshold`.
8. Extend brokerage status with last sync, connected state, account count, position count, and auto-sync without exposing vendor naming.
9. Add profile/account envelope with display name, email source, birth year, region if needed, and current tier.
10. Update export/delete account contracts to include v2 snapshots, digests, alerts, preferences, positions, tracked tickers, and user-owned data only.
11. Render full methodology page from the canonical public methodology source or a versioned native copy.
12. Add alert mark-read/mark-all-read endpoints and quiet-hours delivery state.
13. Add refresh allowance counters and reset timestamps for manual ticker recompute.
14. Add article source confidence and included-in-score flags for paywalled/failed extraction states.
15. Adjust production copy during implementation where VisualQA uses research-like framing such as `Bull case`; prefer rating/audit language.

## P2 - Backlog Only

1. StoreKit 2 or RevenueCat paywall implementation.
2. Server-side entitlement event table and subscription webhook validation.
3. `GET /subscription/entitlement` with trial eligibility, renewal source, feature limits, and App Store product IDs.
4. CSV import UI and backend endpoint (`POST /holdings/import` or batch create) with column mapping, validation, and preview.
5. Server-side trending/search telemetry if the Search screen keeps `What others are looking at`.
6. Ticker universe request queue for Pro users (`ticker_universe_requests`) and admin review tooling.
7. ETF top-holdings ingestion for ETF Financial Health scoring.
8. Sector constituent breadth data source if not derivable from current universe.
9. Export job async status and PDF report export.
10. Longer news history / 30-day article access as a Pro entitlement after payments exist.

## Mock-Only VisualQA Values That Must Not Ship As Real

| Visible value | Route | Required source before production |
|---|---|---|
| `$1,284,715.42` | Today/Holdings | server portfolio value from holdings/prices |
| `-$5,438 today` | Today | portfolio day change computation |
| `AA`, `Composite 81 · -1` | Today | value-weighted portfolio snapshot with previous point |
| FIN/NEWS/MAC/SEC/VOL portfolio scores | Today | value-weighted dimension rollups |
| sector ETF moves/weights | Today/Morning Report | sector ETF bars + portfolio weights |
| `2 alerts overnight`, `2 unread · 14 in 7D` | Today/Alerts | alert read/window counts |
| all Today/Morning Report calendar rows | Today/Morning Report | calendar ingestion/cache |
| all holdings row P&L/day-change/sparkline values | Holdings | server-enriched holdings + prices/history |
| tracked ticker prices/grades/deltas | Holdings | enriched watchlist/tracked endpoint |
| search recent/trending rows | Search | recent store/trending source and enriched ticker data |
| ticker score deltas and `was` values | Ticker/Methodology/Alerts | real snapshot history and hysteresis proof |
| methodology raw audit numbers | Methodology pages | persisted dimension input rows |
| article score/context | Article | shared event enrichment + portfolio overlay |
| subscription/trial days/price | Paywall/Settings | StoreKit/entitlement contract, backlog only |

## Known Contradictions

| Contradiction | Resolution |
|---|---|
| VisualQA is untracked but included in Xcode project | Audit it anyway; final implementation should ensure it is intentionally tracked or removed from release paths. |
| Current `/holdings` returns an array, VisualQA needs an envelope | Add v2 envelope or new Today/Holdings endpoint while preserving old app until migration. |
| Current backend rejects unsupported tickers, product truth allows degraded outside-universe manual add | Change backend later to allow `outside_universe=true` positions with limited-data UI. |
| `macro_regime_snapshots` and `sector_regime_snapshots` exist but have 0 rows | Jobs must populate them before VisualQA macro/sector audit pages can be honest. |
| Ticker score history data exists but VisualQA needs a chart contract | Add endpoint or embed ordered history arrays. |
| Paywall UI exists in VisualQA but no StoreKit/entitlement exists | Keep in backlog only; do not implement during P0 data work. |
| CSV import appears in VisualQA but no implementation exists | Keep in backlog only. |
