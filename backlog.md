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

## 2026-05-27 — Hi-Fi live-parity port (backend follow-ups)

Numbering continues from the highest existing item in the document
(P0 ends at 20, P1 ends at 15, P2 ends at 10; the Cycle 3 list ends at 5).
The items below are numbered fresh from 21 across the parity sweep so they
do not collide with any prior list.

21. **`POST /holdings` `allow_outside_universe` opt-in via iOS encoder.**
    Screen: `holding-outside` (Add position, outside universe).
    Backend already supports `positions.outside_universe = true`, but the
    iOS `APIService.CreateHoldingRequest` does not carry the field, so the
    Search→Add flow silently rejects unsupported tickers despite the live
    sheet's outside-universe banner being present elsewhere.
    Smallest backend change: none — purely an iOS wire-model addition.
    Cross-reference: existing P0#16 ("Allow outside-universe manual position
    add"). This item tracks the iOS side.
    iOS can ship a placeholder first: render the search row tag (OUTSIDE)
    and route to `TickerDetailView` (which already renders the banner)
    without enabling the actual add path. Once shipped, replace the
    placeholder with a real "Save as outside-universe" button.

22. **`PATCH /holdings/{id}` for edit-position.**
    Screen: `edit-holding` (Edit position) and the related
    "Edit shares / cost basis / account" affordance referenced in
    `ticker-held`.
    Smallest backend change: a single `PATCH /holdings/{id}` route accepting
    `{shares?, purchase_price?, account?}` and returning the updated Position.
    iOS placeholder: hide the "Edit position" CTA until the route ships;
    the swipe-to-delete flow already works.

23. **`POST /holdings` accept `purchase_date`.**
    Screen: `holding-manual` (manual add). The live `HoldingsAddSheet`
    already collects a `DatePicker` value but a TODO line tells the user
    "Purchase date will be sent once the backend route supports it."
    Smallest backend change: add `purchase_date` to the create-holding
    payload and persist it on `positions.purchase_date`.
    iOS can ship a placeholder first: today's TODO message is the
    placeholder.

24. **Per-dimension `score_delta` on `MethodologyResponse` and on
    `TickerDetailResponse.dimensionBreakdown`.**
    Screens: `ticker` (five-dimensions ledger) and all five
    `methodology-{financial,news,macro,sector,volatility}` audits.
    The composite `scoreDelta` exists, but the five-row ledger shows `—`
    for every per-dimension delta because the field is not on the wire.
    Smallest backend change: persist yesterday's per-dimension scores when
    `ticker_risk_snapshots` rolls and compute today−yesterday for each
    dimension; expose as `dimension_breakdown.{dim}_score_delta`.
    iOS can ship a placeholder first: current `—` rendering is honest;
    swap to real delta once the field lands.

25. **`Alert.read_at` on the iOS decoder + alerts list pagination.**
    Screen: `alerts`. Backend migration already added `alerts.read_at`,
    `delivered_at`, `severity`, `destination_type`, `destination_id`. The
    iOS `Alert` decoder still tracks unread via `UserDefaults.lastSeenAt`.
    Smallest backend change: include `read_at` (and the rest of the v2
    fields) on the `/alerts` envelope response.
    iOS placeholder: current UserDefaults `lastSeenAt` is functional but
    not cross-device; safe to keep until backend exposes `read_at`.
    Pagination (`/alerts?before=…&limit=…`) is a separate backend change
    needed to make the "Load earlier alerts" button work.

26. **`GET /alerts/{id}` for the `alert-detail` screen.**
    Screen: `alert-detail` (grade-change detail). The VQA screen needs
    before/after grade, hysteresis proof (composite ≤ X for 2 days), the
    driving dimension's before/after score, and the 3 articles that drove
    the change.
    Cross-reference: this is the existing P0#13.
    iOS placeholder: tapping an alert today routes to digest / holdings /
    ticker — keep that behaviour until the detail endpoint exists.

27. **Article extraction status on `MethodologyArticle`.**
    Screens: `article-paywalled` and `article-failed`. Both states are
    referenced from the `methodology-news` and `ticker` recent-news ledgers
    but the iOS `MethodologyArticle` decoder has no
    `extraction_status` / `paywall_state` / `included_in_score` field.
    Smallest backend change: surface `shared_ticker_events.extraction_status`
    and a `paywalled: bool` on the article objects in
    `/tickers/{ticker}` `recent_news` and `/tickers/{ticker}/methodology`
    `news_sentiment.articles[]`.
    iOS placeholder: never branch — render the full body and trust the
    backend to omit unscored articles. Add the warn-soft/bad-soft state
    cards once the field exists.

28. **`Digest.structuredSections.sources` (lineage rows) for the Morning
    Report VI section.**
    Screen: `digest`. The VQA "VI Sources & Methodology" block expects a
    short list of feeds + the methodology version + a "generated at X using
    data refreshed within the last N hours" line. Today the iOS view falls
    back to a static "Generated at <time>" caption.
    Smallest backend change: include a `sources_freshness` block on
    `Digest.structured_sections` with `{generated_at, data_age_minutes,
    methodology_version, sources: [string]}`.
    iOS placeholder: render only the timestamp + methodology version
    caption today.

29. **Watchlist enrichment: `day_change_pct` + `score_delta` on
    `WatchlistItem`.**
    Screen: `holdings` (tracked tickers section) and `tracked-tickers`.
    Cross-reference: existing P1#1 already requests this; this row tracks
    the specific fields the VQA ledger row needs (price already exists; day
    change % and grade delta do not).
    iOS placeholder: render `—` for both columns until the fields ship.

30. **Settings → dedicated `NotificationPrefs` view requires
    `alerts_macro_shock`, `alerts_watchlist`, `alerts_digest_ready`,
    `alert_severity_threshold` columns.**
    Screen: `notification-prefs`. The VQA layout has rows for "Macro
    shock" and "Tracked ticker alerts" that map directly to those columns.
    Cross-reference: existing P1#7. The schema migration already added
    these columns server-side; the missing piece is the iOS PATCH wiring
    and exposing them on `PreferencesResponse`.
    iOS placeholder: render the unimplemented rows as disabled with
    "Coming soon" until the response includes the values.


## 2026-05-28 — Alpha QA pass findings

Verified in iOS Simulator (iPhone 17, iOS 26.3) with real backend + real user data.
Fixed: 1 bug. Documented: 3 new backend bugs.

31. **[FIXED] Alerts deep-link → wrong Ticker Detail.**
    Screen: `alerts` → tap GRADE or NEWS alert with `positionTicker`.
    Bug: `HoldingsListView.onChange(of: deepLinkTicker)` was clearing the
    binding but never pushing the ticker onto `navigationPath`, so the nav
    stack didn't move.
    Fix applied in `ios/Clavis/Views/Holdings/HoldingsListView.swift`:
    - Added `@State private var navigationPath: [String] = []`
    - Bound it to `NavigationStack(path: $navigationPath)`
    - Changed handler to `navigationPath.append(ticker)` before clearing.
    Verified: SMCI grade alert now opens SMCI Ticker Detail (was AMD).
    Verified: SMCI news alert also routes to SMCI Ticker Detail correctly.

32. **[BUG] Holdings position row price stale vs Ticker Detail price.**
    Screen: `holdings` (positions), `ticker`.
    Observed: AMD position row shows $467.51 but Ticker Detail shows
    $495.54. SMCI: $35.58 vs $38.19. Same `price_as_of` timestamp on both
    endpoints yet different prices.
    Root cause: `/holdings` returns `positions.current_price` which is
    written at analysis time. `/tickers/{ticker}` returns
    `latest_price.price` from the current price snapshot. The positions
    table is not updated between analysis runs, so `current_price` can lag
    by hours or days.
    Fix: `/holdings` enrichment should JOIN with the latest price snapshot
    row for each ticker rather than using the stale `positions.current_price`.
    This affects displayed P&L, portfolio value accuracy, and day-change %.
    Cross-reference: P0#4 ("holdings envelope… market value, day change,
    P&L").

33. **[BUG] Backend event loop blocked by synchronous Supabase calls.**
    Observed: `/tickers/{ticker}` occasionally takes 10-15 seconds to
    respond, briefly freezing all endpoints including `/health`.
    Root cause: `async def get_ticker_detail` calls synchronous
    `get_ticker_detail_bundle()` directly, blocking the asyncio event loop.
    Fix: wrap in `asyncio.get_event_loop().run_in_executor(None, ...)` or
    migrate Supabase queries to the async client.
    File: `backend/app/routes/tickers.py`

34. **[BUG] GitHub Actions `PROD_SSH_KEY` secret not configured.**
    Deploy workflow at `.github/workflows/deploy-prod.yml` requires
    `secrets.PROD_SSH_KEY` to SSH to `134.122.114.241`. The secret is not
    set in GitHub repo settings, so `git push` auto-deploy is broken.
    Manual SSH deploy (`ssh clavix-backend@134.122.114.241` with local key
    `~/.ssh/clavix_vps_ed25519`) still works as a fallback.
    Fix: add the contents of `~/.ssh/clavix_vps_ed25519` as the
    `PROD_SSH_KEY` secret in GitHub → Settings → Secrets and variables →
    Actions.

35. **[COSMETIC] Sector exposure shows two XLK rows on Today and Holdings.**
    Screen: `today` (sector exposure card), `holdings` (composition section).
    Observed: Two rows both labeled "XLK / Tech", one at 94% weight (AMD)
    and one at 6% (AAPL + SMCI). Should show distinct sector names:
    "Semiconductors" (AMD) and "Technology" (AAPL + SMCI).
    Root cause: sector normalization collapses both into "Technology/XLK".
    Cross-reference: P0#20 ("normalize VisualQA sector taxonomy").

