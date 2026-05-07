# Clavix Refactor Plan

This refactor moves Clavix from the legacy position-scoped A-F safety model to the v2 product defined in `CLAVIX_TRUTH.md`: one ticker-scoped rating system, one news store, a bond-rating grade scale, five auditable risk dimensions, and iOS screens that match the v2 wireframes.

## Current Phase

Phase 0 is complete after the foundation session that created this document, installed the new source of truth, archived superseded docs, and added the v2 wireframe artifact.

## Wireframe Analysis

### Screen Inventory

| Screen | Tab | Purpose | Key UI components |
|---|---|---|---|
| Welcome | modal/onboarding | Explain the Clavix promise before account setup. | Brand masthead, tagline, three value propositions, Continue and Sign in actions. |
| Add portfolio | modal/onboarding | Let the user choose brokerage sync, CSV import, or manual entry. | Progress bar, add-path cards, Pro/Free tags, read-only brokerage callout. |
| Daily Digest A - Prose-led | Today | Present the morning briefing as a written memo. | Portfolio grade hero, macro prose, sector heat table, position blocks, collapsed quiet holdings. |
| Daily Digest B - Card stack | Today | Present the same briefing as scannable cards. | Portfolio card, macro metric chips, sector card, position cards. |
| Daily Digest C - Hybrid | Today | Mix editorial summary with compact data cards. | Summary headline, portfolio rating card, macro/sector prose, mover list. |
| Daily Digest D1 - Sectioned memo | Today | Rating-agency style daily memo. | Ruled sections, macro prose, sector rows, position delta rows, article CTA. |
| Daily Digest D2 - Stacked cards | Today | Dense card-first briefing. | Bordered macro/sector cards, high-impact position card, score delta callout. |
| Daily Digest D3 - Tight ledger | Today | Most terminal-like digest layout. | Masthead, roman numeral sections, ruled ledger table, grade and delta columns. |
| Holdings | Holdings | Show positions and watchlist in one portfolio screen. | Portfolio composite hero, sorting tabs, holdings table, watchlist section, alert-tinted row. |
| Ticker Detail A - Bars | Search | Exploratory ticker detail with bar dimensions. | Grade hero, price row, dimension bars, driving-grade prose, recent news list, add CTAs. |
| Ticker Detail B - Pills | Search | Exploratory ticker detail with pill rows. | Price hero, grade pill, price chart, dimension rows, recent news. |
| Ticker Detail C - Radar | Search | Chosen ticker detail direction. | Radar chart, grade/score hero, price chart, dimension audit table, news list, executive summary drawer. |
| Ticker Detail D - Terminal | Search | Dense terminal-style ticker view. | Dark stats slab, five dimension rows, sentiment-scored news ledger. |
| Methodology Drawer | modal/sheet/overlay | Quick audit from score tap. | Dimmed backing view, grade header, accordion dimension rows, distribution chart, full audit link. |
| News Sentiment Audit | modal/detail | Show article-level contribution to news score. | Score hero, distribution chart, article table with score and weights, volume signal callout. |
| Financial Health Audit | modal/detail | Show fundamental inputs behind financial health score. | Score hero, input distribution, signal/value/score/weight table, filing cadence callout. |
| Macro Exposure Audit | modal/detail | Show macro sensitivity inputs. | Score hero, distribution chart, macro signal table, current macro risk callout. |
| Sector Exposure Audit | modal/detail | Show sector inputs. | Score hero, distribution chart, sector signal table, sector concentration callout. |
| Volatility Audit | modal/detail | Show volatility inputs. | Score hero, distribution chart, volatility signal table, inverted-score callout. |
| Article Detail | modal/detail | Explain one scored article. | Source metadata, headline, sentiment score bar, TLDR, personalized implication box, key implications, collapsed Why this score. |
| Universal Search | Search | Search tracked and outside-universe tickers. | Search field, top result rows, in-portfolio chip, outside-universe section, recent ticker pills. |
| Alerts | Alerts | Show in-app alert history with destinations. | Filter tabs, alert rows, destination badges, new alert indicator, quiet-hours callout. |
| Settings | Settings | Manage account, digest, alerts, privacy, brokerage, and methodology. | Account card, settings groups, toggles, quiet hours, methodology row, export, connected brokerage. |
| Paywall | modal/sheet | Convert Free to Pro. | Pro badge, $20/mo price, 14-day trial callout, Free/Pro comparison table, restore/terms/privacy links. |

### Comparison To Current iOS App

| Wireframe screen | Current equivalent | Status | Differences |
|---|---|---|---|
| Welcome | `Views/Auth/LoginView.swift` plus onboarding container | MODIFIED | Current auth is credential-first; wireframe needs product-first onboarding with tagline, trial framing, and value propositions. |
| Add portfolio | `Views/Onboarding/OnboardingContainerView.swift`, `HoldingsListView` add sheet | MODIFIED | Current manual add asks ticker/shares/purchase price/archetype; wireframe adds brokerage, CSV, and manual path cards with Pro/Free tags. |
| Daily Digest A-D | `Views/Digest/DigestView.swift` | MODIFIED | Current digest has score summary, lead card, What Changed, What Matters Today, Monitoring Notes, Positions, Full Narrative. Wireframe requires macro -> sector -> positions, portfolio grade hero, position deltas, quiet holdings collapse, and no backend status strings. |
| Holdings | `Views/Holdings/HoldingsListView.swift` | MODIFIED | Current holdings list is filter/sort oriented and position-detail linked; wireframe combines portfolio composite, weighted holdings table, alert row tint, and inline watchlist. |
| Ticker Detail A-D | `Views/Tickers/TickerDetailView.swift`, `Views/PositionDetail/PositionDetailView.swift` | MODIFIED | Current app has separate position detail and ticker detail compatibility payloads; chosen wireframe uses ticker-first radar hero, price chart below hero, audit table, no fundamentals section, and executive summary drawer. |
| Methodology Drawer | none | NEW | Current methodology is static settings/help text, not a score-tap sheet with dimension accordions. |
| Methodology Audit pages | none | NEW | Current API/view does not expose per-dimension audit pages with input rows, weights, score distributions, and refresh timestamps. |
| Article Detail | event detail inside `PositionDetailView.swift` | MODIFIED | Current event detail shows event summary, market interpretation, position impact, action signal. Wireframe requires source tier, sentiment score, TLDR, What It Means for your position, key implications, and collapsed Why this score. |
| Universal Search | likely `Views/Tickers/TickerDetailView.swift` search flow via API | MODIFIED | Current search exists at route/API level, but wireframe needs recent ticker pills, in-portfolio flag, outside-universe section, current grade, and price. |
| Alerts | `Views/Alerts/AlertsView.swift` | MODIFIED | Current alerts group rows; wireframe requires filters All/Grade/News/Macro/Digest and explicit destination badges for tap-through. |
| Settings | `Views/Settings/SettingsView.swift` | MODIFIED | Current settings has account, digest, alerts, about. Wireframe adds trial day, verbose mode, digest alerts, watchlist/macro alert Pro states, severity threshold, connected brokerage row, and removes score history. |
| Paywall | none | NEW | No production StoreKit/RevenueCat paywall exists in the current app. |

Current screens not represented directly in the wireframes:

| Current screen | Status | Notes |
|---|---|---|
| Dashboard tab | REMOVED | Wireframes replace Dashboard with Today as the first tab. Any dashboard-only data should move into Today or Holdings. |
| Position Detail | REMOVED/MERGED | The ticker detail screen becomes the canonical per-name page; portfolio-specific context appears as overlays and Article Detail personalization. |
| Score Explanation | REMOVED/MERGED | Replaced by methodology drawer and full audit pages. |
| Full Score History screen | REMOVED | Wireframe README says score history screen is out of v1 scope; keep limited charts inside ticker detail only if required by truth. |

### New UI Components Required

| Proposed component | What it does | Screens |
|---|---|---|
| `BondGradeBadge` | Displays AAA-F bond grades with fixed-width sharp boxes and optional delta. | Digest, Holdings, Ticker Detail, Alerts, Search. |
| `RatingLedgerRow` | Dense ruled row with ticker, score, grade, delta, and short explanation. | Digest D3, Holdings, Alerts. |
| `PortfolioCompositeHeader` | Shows weighted portfolio grade, score, delta, and driver. | Today, Holdings. |
| `RiskRadarChart` | Displays five dimension scores as a radar chart. | Ticker Detail C, Executive Summary. |
| `DimensionAuditTable` | Rows for dimension, score, 7-day delta, updated timestamp, and navigation affordance. | Ticker Detail, Methodology Drawer. |
| `MethodologyDrawerSheet` | Score-tap sheet with accordion dimension summaries and links to full audit. | Ticker Detail, any grade/score surface. |
| `ScoreDistributionChart` | Mini histogram of article/signal score buckets. | Methodology Drawer, all audit pages. |
| `AuditInputTable` | Signal/value/score/weight table for non-news dimensions. | Financial, Macro, Sector, Volatility audits. |
| `ArticleScoreTable` | Article/source/headline/score/recency-weight/source-tier-weight table. | News Sentiment Audit. |
| `WhyThisScoreDisclosure` | Collapsed-by-default explanation for article score reasoning. | Ticker Detail, Article Detail. |
| `PersonalizedImplicationBox` | Orange-tinted user-specific context using holdings, cost basis, P&L, and weight. | Article Detail, Digest. |
| `DestinationBadge` | Compact row badge that previews alert tap-through destination. | Alerts. |
| `ProFeatureBadge` | Sharp Pro tag for gates and comparison rows. | Add Portfolio, Settings, Paywall. |
| `FreeProComparisonTable` | Paywall comparison grid. | Paywall. |

Current `ClavisDesignSystem.swift` has general colors, typography, `GradeBadge`, `RiskBar`, `ClavixGauge`, `CX2NavBar`, buttons, cards, and toggles, but it is still a rounded dark-system implementation with A-F grade styling. The wireframes require a lighter paper system, sharp boxes, burnt-orange accent, mono numeric ledgers, radar/distribution charts, and AAA-F grade support.

### New Data Requirements

| Screen | Endpoint | Missing data |
|---|---|---|
| Today digest | `GET /digest` or `GET /dashboard` | Six-section digest shape: header, overnight macro, sector heat, positions ranked by risk change, watchlist updates, what to watch today. Current structured sections do not reliably match this exact contract. |
| Today digest | `GET /digest` | Portfolio composite grade weighted by position value, real previous grade/score, position-level score deltas, quiet-position grouping, sector overnight performance for held sectors. |
| Holdings | `GET /holdings` | Portfolio composite header fields, position weight, P&L percentage, alert highlight flag, watchlist inline section, Free limit state. |
| Ticker Detail | `GET /tickers/{ticker}` | Five dimension scores with names matching truth, 7-day deltas, per-dimension updated timestamps, price chart period data, executive summary sections, current holding/watchlist state, article-level sentiment reason. |
| Methodology Drawer | `GET /tickers/{ticker}` or new `/tickers/{ticker}/methodology` | Dimension source labels, article count, distribution buckets, weighted means, full-audit links. |
| News Sentiment Audit | new `/tickers/{ticker}/methodology/news` or expanded ticker detail | Article rows with `sentiment_score`, `sentiment_reason`, `source_tier`, `recency_weight`, `source_weight`, `impact_tag`, score distribution, 4-week article volume average. |
| Financial Health Audit | new `/tickers/{ticker}/methodology/financial-health` | D/E, FCF margin, interest coverage, current ratio, revenue growth trend, profitability trend, sector medians, filing date, weights, score distribution. |
| Macro Exposure Audit | new `/tickers/{ticker}/methodology/macro` | Regression coefficients for rates, DXY, WTI, VIX, SPY beta, R², current factor levels, macro narrative, refresh timestamp. |
| Sector Exposure Audit | new `/tickers/{ticker}/methodology/sector` | Sector ETF mapping, sector beta, 30-day relative momentum, breadth, sector narrative, signal weights, refresh timestamp. |
| Volatility Audit | new `/tickers/{ticker}/methodology/volatility` | 30d realized vol, 90d realized vol, 30d/90d ratio, max drawdown, 252d beta, signal weights, sparklines. |
| Article Detail | new `/articles/{id}` or expanded ticker detail event payload | Full body or paywall flag, TLDR, What It Means, Key Implications, Why this score, original URL, user-specific holding overlay. |
| Search | `GET /tickers/search` | Current grade, current price, in-portfolio flag, outside-universe reason, recent searched tickers. |
| Alerts | `GET /alerts` | Destination type and ID, digest-ready subtype, score delta details, dimension driver, quiet-hours queued/delivered metadata. |
| Settings | `GET /preferences` | Digest alert toggle, watchlist alerts toggle, macro shock toggle, severity threshold, trial day/entitlement state, connected brokerage display name. |
| Paywall | local + entitlement endpoint | RevenueCat/StoreKit products, trial eligibility, current tier, feature limit usage. |

### Grade/Score System Delta

The v2 grade scale is `AAA`, `AA`, `A`, `BBB`, `BB`, `B`, `CCC`, `CC`, `C`, `F` with 10-point score bands. Current old-grade references include:

| Area | Current references to update |
|---|---|
| Backend scoring | `backend/app/pipeline/analysis_utils.py` has `_RISK_LEVELS`, `score_to_grade`, `_extract_drivers`, `_pick_generic_drivers`, and rationale defaults hardcoded to A/B/C/D/F. |
| Backend risk scorer | `backend/app/pipeline/risk_scorer.py` computes four dimensions, calls `score_to_grade`, returns `position_sizing`, `volatility_trend`, and `mirofish_used`. |
| Backend structural scorer | `backend/app/pipeline/structural_scorer.py` still computes structural base from market cap/liquidity/volatility/leverage/profitability, not the v2 five dimensions. |
| Backend scheduler | `backend/app/pipeline/scheduler.py` reads/writes `risk_scores`, stores `position_sizing`, syncs to `ticker_risk_snapshots`, and dual-writes news stores. |
| Backend routes | `routes/dashboard.py`, `routes/digest.py`, `routes/holdings.py`, `routes/analysis_runs.py`, `routes/account.py`, `routes/tickers.py`, and `routes/alerts.py` expose or persist grade fields. |
| Backend prompts | `backend/app/pipeline/portfolio_compiler.py`, `risk_scorer.py`, and event-analysis prompt paths mention old dimensions, risk labels, or grade assumptions. |
| iOS models | `ios/Clavis/Models/RiskEnums.swift` defines `Grade` as A/B/C/D/F and `RiskDrivers` as news/macro/position_sizing/volatility/market_integrity. |
| iOS design system | `ios/Clavis/App/ClavisDesignSystem.swift` has A-F colors, grade band labels, `GradeBadge`, `RiskBar`, `ClavixGauge`, and grade risk mapping. |
| iOS copy | `ios/Clavis/App/ClavisCopy.swift` maps statuses but also has `.capitalized` fallback; copy must avoid backend raw statuses in visible UI. |
| iOS views | `DashboardView.swift`, `HoldingsListView.swift`, `DigestView.swift`, `TickerDetailView.swift`, `PositionDetailView.swift`, `AlertsView.swift`, `SettingsView.swift`, and shared components render grades, risk colors, filters, or grade deltas. |
| DB | `supabase_schema.sql` has `risk_scores.grade CHECK (grade IN ('A','B','C','D','F'))`; `ticker_risk_snapshots.grade` is unconstrained in repo schema but must get the new constraint; `alerts.previous_grade` and `alerts.new_grade` are unconstrained but must get the new constraint. |

## Backend Gap Analysis

### New Dimensions Vs Old Dimensions

| New dimension | Current scorer exists? | Correct per truth? | Missing or wrong inputs | Data sources needed | Effort |
|---|---|---|---|---|---|
| Financial Health | Partial. `structural_scorer.py` has leverage/profitability proxies; `ticker_metadata.py` fetches some Finnhub metrics. | No. It does not compute D/E, FCF margin, interest coverage, current ratio, 4Q revenue trend, and profitability trend as an explicit dimension. | Exact Finnhub metric mapping, quarterly refresh, sector medians, ETF top-holding weighted average, dimension score persistence. | Finnhub `stock/metric`, `stock/profile2`, ETF holdings source or manual top-50 ETF holdings feed. | Large |
| News Sentiment | Partial. `risk_scorer.py` derives news score from event analyses; scheduler enriches article analysis; `shared_ticker_events` exists. | No. It is event-direction based, not every article in trailing 7 days with recency/source weights and volume signal. | Article body extraction, per-article sentiment score/reason, source tier, recency weight, 4-week average volume, limited-data exclusion. | Google News RSS, Jina Reader, trafilatura/newspaper fallback, MiniMax. | Large |
| Macro Exposure | Partial. `risk_scorer.py` has `_macro_adjustment_from_context`; `structural_scorer.py` has regime adjustments. | No. Truth requires 252-trading-day regression against 10Y, DXY, WTI, VIX, and SPY beta. | Daily factor series, regression implementation, coefficients/R² storage, current macro state, narrative generation. | Polygon daily bars and macro factor series; FRED only if Polygon cannot provide a factor. | Large |
| Sector Exposure | Minimal. `rss_ingest.py` has sector RSS and metadata has sector. | No. No sector beta, sector ETF momentum, sector breadth, or sector narrative scoring exists. | Sector ETF mapping, constituent breadth, 90-day stock/sector correlation, 30-day sector vs SPY momentum, sector narrative cache. | Polygon sector ETF bars, sector constituent lists, CNBC sector RSS, Google News sector queries. | Large |
| Volatility | Partial. `ticker_metadata.py` computes a beta-derived `volatility_proxy`; `structural_scorer.py` scores volatility proxy. | No. Truth requires realized 30d/90d annualized vol, 30d/90d ratio, max drawdown from 252-day high, 252-day beta. | Daily bars, realized vol math, drawdown calculation, beta regression, dimension audit rows. | Polygon aggregate bars. | Medium |

Legacy dimensions to remove:

| Legacy dimension | Remove from |
|---|---|
| `position_sizing` | `risk_scores`, `risk_scorer.py`, scheduler writes, ticker cache compatibility, iOS `RiskDrivers`, views, prompts. Keep position weight as portfolio metadata only. |
| `thesis_integrity` / `market_integrity` | DB schema, iOS `RiskDrivers`, docs, copy, prompts. Do not replace it with another user-thesis feature. |
| `volatility_trend` | Rename to `volatility` everywhere user/API-visible. Underlying calculations can still include trend ratio. |

### Database Changes Required

Tables to create:

| Table | Purpose | Notes |
|---|---|---|
| `macro_regime_snapshots` | Shared daily macro state and narrative for digest and macro exposure audit. | If live DB already has this empty table, reconcile repo schema and migrations instead of recreating. |
| `sector_regime_snapshots` | Shared per-sector quantitative and narrative state. | Needed for sector heat, sector audit, and digest cost sharing. |
| `ticker_universe_requests` | Pro ticker-add requests for outside-universe symbols. | Can be deferred until after search/manual-add works. |
| `entitlement_events` or RevenueCat webhook table | Payment entitlement audit trail. | Phase 8 only; do not block scoring phases. |

Tables to drop, after migration checkpoints:

| Table | Data migration note | Drop prerequisite |
|---|---|---|
| `event_analyses_backup_20260504` | No production use, no PK, RLS disabled. | Verify no code references and export row count. |
| `position_analyses_backup_20260504` | No production use, no PK, RLS disabled. | Verify no code references and export row count. |
| `news_items` | Migrate article rows into `shared_ticker_events`; preserve URL, title, source, body, affected tickers, significance. | All reads/writes moved to `shared_ticker_events`. |
| `ticker_news_cache` | Migrate cached rows into `shared_ticker_events`; preserve ticker, URL, headline, source, published date, summary. | `get_ticker_detail_bundle`, scheduler cleanup, and refresh jobs no longer read it. |
| `risk_scores` | Migrate latest historical scores into `ticker_risk_snapshots` where legitimate; user-position data remains in `positions`. | `GET /holdings`, deletes, export/delete account, scheduler, and analysis routes no longer read/write it. |
| `asset_safety_profiles` | Drop unused structural snapshot table. | Confirm no `save_daily_asset_safety_profile` path remains. |

Columns to drop:

| Column | Note |
|---|---|
| `risk_scores.thesis_integrity` | Drop with `risk_scores` or earlier if table is retained temporarily. |
| `risk_scores.grade_reason` | Redundant with rationale fields and retiring table. |
| `risk_scores.mirofish_used` | Legacy sidecar field. |
| `position_analyses.top_news` | Superseded by `shared_ticker_events`. |
| `event_analyses.recommended_followups` | Replace with neutral `key_implications`/`follow_up_notes` only if event table remains. |

Constraints to update or add:

| Constraint | Required state |
|---|---|
| `risk_scores.grade` | If retained during migration, change from A/B/C/D/F to `AAA`,`AA`,`A`,`BBB`,`BB`,`B`,`CCC`,`CC`,`C`,`F`. |
| `ticker_risk_snapshots.grade` | Add the same v2 check constraint. Repo schema currently lacks a check. |
| `alerts.previous_grade` / `alerts.new_grade` | Add v2 grade check allowing null. Repo schema currently lacks a check. |
| `analysis_runs.overall_portfolio_grade`, `digests.overall_grade` | Add v2 grade check allowing null. |
| `user_preferences.summary_length` | Add check `summary_length IN ('brief','standard','verbose')`; enforce Pro-only verbose in API. |

Columns to add or alter:

| Table | Columns |
|---|---|
| `ticker_risk_snapshots` | `financial_health`, `news_sentiment`, `macro_exposure`, `sector_exposure`, `volatility`, `composite_score`, `dimension_inputs`, `dimension_last_refreshed`, `methodology_version`. Keep `safety_score` only as temporary alias. |
| `shared_ticker_events` | `body`, `canonical_url`, `sentiment_score`, `sentiment_reason`, `source_tier`, `recency_weight`, `source_weight`, `impact_tag`, `article_window`, `volume_signal`, `extraction_status`, `paywalled`. |
| `ticker_universe` | `outside_universe_reason`, `market_cap`, `avg_daily_dollar_volume`, `is_supported`, `universe_entered_at`, `universe_flagged_at`. |
| `user_preferences` | `alerts_watchlist`, `alerts_macro_shock`, `alerts_digest_ready`, `alert_severity_threshold`, `trial_started_at`, `trial_ends_at`, `subscription_status`. |

Indexes to add:

| Index | Reason |
|---|---|
| `shared_ticker_events(ticker, published_at DESC)` | Recent news and audit pages. Already exists in migration; keep. |
| `shared_ticker_events(ticker, sentiment_score, published_at DESC)` | News audit distribution and negative article lookup. |
| `shared_ticker_events(canonical_url)` unique where not null | Cross-ticker dedupe. |
| `ticker_risk_snapshots(ticker, snapshot_date DESC)` | Ticker detail, history, latest snapshot. Current index exists on `analysis_as_of`; add date-specific if needed. |
| `ticker_risk_snapshots(ticker, methodology_version, snapshot_date DESC)` | Methodology version audits. |
| `sector_regime_snapshots(sector, snapshot_date DESC)` | Digest sector heat and sector audit. |
| `macro_regime_snapshots(snapshot_date DESC)` | Daily digest macro section. |
| `watchlist_items(watchlist_id, ticker)` | Already unique; keep. |
| `positions(user_id, ticker)` | Holdings overlays and duplicate checks. |

New migration files in safe order:

| Order | Migration | Purpose |
|---|---|---|
| 001 | `reconcile_live_schema_snapshot.sql` | Bring repo migrations/schema in sync with live DB before destructive work. |
| 002 | `add_v2_grade_constraints.sql` | Add v2 grade checks to grade-bearing tables, allowing old grades during an explicit transition only if needed. |
| 003 | `add_v2_snapshot_dimension_columns.sql` | Add five dimension columns and audit JSONB to `ticker_risk_snapshots`. |
| 004 | `add_shared_event_sentiment_fields.sql` | Add article body, sentiment, weight, tier, impact, and extraction fields to `shared_ticker_events`. |
| 005 | `create_macro_sector_snapshot_tables.sql` | Add macro and sector shared snapshot tables if absent. |
| 006 | `backfill_shared_ticker_events_from_legacy_news.sql` | Copy `news_items` and `ticker_news_cache` into `shared_ticker_events`, preserving legacy IDs. |
| 007 | `backfill_ticker_risk_snapshots_from_risk_scores.sql` | Copy real historical grade/score data to ticker snapshots where ticker mapping is unambiguous. |
| 008 | `switch_summary_length_constraint.sql` | Enforce brief/standard/verbose values and normalize existing rows. |
| 009 | `drop_legacy_backup_tables.sql` | Drop the two backup tables after verification. |
| 010 | `drop_legacy_news_and_score_tables.sql` | Drop `news_items`, `ticker_news_cache`, `risk_scores`, and `asset_safety_profiles` only after code no longer uses them. |

### API Endpoint Changes Required

| Endpoint | Change |
|---|---|
| `GET /digest` | Return exact v2 sections: `header`, `overnight_macro`, `sector_heat`, `positions`, `watchlist_updates`, `what_to_watch_today`, plus `summary_length`, `portfolio_grade`, `portfolio_score`, and real deltas only. |
| `GET /dashboard` | Either retire for iOS or make it a thin alias of `/digest` plus holdings if still needed. Do not keep a divergent dashboard contract. |
| `GET /holdings` | Add portfolio composite, weights, P&L, alert highlight, watchlist items, holdings limit, and bond grades. Remove old risk labels and raw backend statuses. |
| `POST /holdings` | Enforce Free 3-holding limit and Pro unlimited limit. Allow outside-universe manual add with degraded-mode flag instead of hard failing. |
| `GET /tickers/search` | Add current grade, current price, in-portfolio flag, outside-universe reason, add-manually CTA metadata. |
| `GET /tickers/{ticker}` | Return five dimensions, score/grade, price chart, recent articles from `shared_ticker_events`, audit summaries, executive summary, and user overlay. Stop reading `ticker_news_cache`. |
| `POST /tickers/{ticker}/refresh` | Enforce Pro/admin gate and 5/day/ticker/user limit. Refresh shared ticker events and dimension snapshots. |
| New methodology endpoints | Add `/tickers/{ticker}/methodology`, `/tickers/{ticker}/methodology/{dimension}`, or equivalent nested data in ticker detail. Must expose audit tables and article sentiment reason. |
| New article endpoint | Add `/articles/{shared_event_id}` or `/tickers/{ticker}/articles/{id}` for Article Detail. Include personalized holding overlay when the user holds the ticker. |
| `GET /alerts` | Add destination metadata, score delta details, dimension driver, digest-ready alert type, quiet-hours delivery state. |
| `GET/PATCH /preferences` | Add digest alert, watchlist alert, macro shock, severity threshold, verbose tier gating, trial/subscription state. |
| `GET /account/export` and `DELETE /account` | Remove `risk_scores`/`news_items` legacy assumptions and export new shared/user-owned data appropriately. |

Methodology drill-down gap: no current endpoint fully returns per-article sentiment scores with source tier, recency/source weights, and LLM reasoning. Some event rows have TLDR/What It Means/Key Implications in `shared_ticker_events`, but the table lacks sentiment-specific fields and current `GET /tickers/{ticker}` still reads `ticker_news_cache` for latest news.

Digest structure gap: current digest generation can produce macro/sector/watchlist text, but the route and compiler still use legacy sections and do not guarantee the CLAVIX_TRUTH §9 six-section contract.

### Pipeline Changes Required

| File | Required changes |
|---|---|
| `backend/app/pipeline/risk_scorer.py` | Replace four-dimension scoring with five equal-weight dimensions. Remove `position_sizing`, `thesis_integrity`, `mirofish_used`, legacy A-F assumptions, and LLM-first dimension scoring where math is specified. Add limited-data handling and v2 score-to-grade mapping. |
| `backend/app/pipeline/structural_scorer.py` | Reframe as deterministic dimension helpers: financial health, macro regression, sector exposure, volatility. Remove market-cap-as-safety shortcut. Keep useful utility functions only if they feed a truth dimension. |
| `backend/app/pipeline/rss_ingest.py` | Make Google News RSS + canonical URL dedupe the ticker article discovery path; add Jina/trafilatura/newspaper extraction status; keep CNBC macro/sector feeds for digest/narratives. |
| `backend/app/services/ticker_metadata.py` | Persist exact Finnhub fundamental metrics needed for financial health. Add ETF handling inputs, sector ETF mapping, and 252-day/90-day price data dependencies. |
| `backend/app/services/ticker_cache_service.py` | Stop reading `ticker_news_cache` and old `risk_scores`. Project from `ticker_risk_snapshots` and `shared_ticker_events` only. Replace `_shared_risk_dimensions` with five dimensions and audit payloads. |
| `backend/app/pipeline/scheduler.py` | Remove dual writes to legacy news/scoring tables after migration. Schedule active/dormant refresh cadences, macro/sector shared generation, article sentiment scoring, dimension recomputation, hysteresis, and alert creation. |
| `backend/app/pipeline/portfolio_compiler.py` | Compile the exact six-section digest and remove old monitoring/advice language. Enforce brief/standard/verbose lengths and Pro-only verbose. |

## Phase 0 — Foundation (Before Any Code)

What's in scope:

- Install new `AGENTS.md` and `docs/CLAVIX_TRUTH.md` from Downloads.
- Add `design/clavix-wireframes-v2.html` from the v2 handoff package.
- Archive superseded docs into `docs/_archive/`.
- Create this `docs/REFACTOR_PLAN.md`.
- Update public-facing methodology and pricing docs.

What's explicitly deferred:

- Application code changes.
- Database migrations.
- Production deploys.

Prerequisites:

- None.

Exit criteria:

- Repo reads `AGENTS.md`, `docs/CLAVIX_TRUTH.md`, then `docs/REFACTOR_PLAN.md` on session start.
- No active planning doc contradicts `CLAVIX_TRUTH.md`.
- Phase 1 work has a safe execution sequence.

Estimated effort: 0.5-1 day.

## Phase 1 — DB Cleanup & Grade Migration

What's in scope:

- Reconcile live schema drift with repo migrations.
- Add v2 grade constraints to `ticker_risk_snapshots`, `alerts`, `digests`, and `analysis_runs`.
- Add v2 dimension columns and audit JSONB to `ticker_risk_snapshots`.
- Add sentiment/audit fields to `shared_ticker_events`.
- Add or reconcile `macro_regime_snapshots` and `sector_regime_snapshots`.
- Backfill `shared_ticker_events` from `news_items` and `ticker_news_cache`.
- Backfill `ticker_risk_snapshots` from legitimate `risk_scores` history.
- Drop backup tables after row-count and code-reference checks.

What's explicitly deferred:

- Dropping `news_items`, `ticker_news_cache`, or `risk_scores` until code no longer reads/writes them.
- iOS changes.
- Payment tables except entitlement planning.

Prerequisites:

- Export live schema and applied migration list.
- Verify current live row counts for legacy tables.
- Run code search for every table/column scheduled for drop.

Exit criteria:

- Backup tables are gone.
- Grade constraints accept only the v2 grade scale wherever grade checks exist.
- `shared_ticker_events` contains migrated legacy article data.
- `ticker_risk_snapshots` can store all five dimension scores and audit inputs.
- `user_preferences.summary_length` allows only `brief`, `standard`, `verbose`.

Estimated effort: 1-2 days.

## Phase 2 — Backend Pipeline: Five Dimensions

What's in scope:

- Implement score-to-grade mapping per `CLAVIX_TRUTH.md` §7.
- Implement equal-weight composite scoring with limited-data rescaling.
- Implement Financial Health from Finnhub metrics.
- Implement Volatility from Polygon bars.
- Implement Macro Exposure regression.
- Implement Sector Exposure quantitative score.
- Remove `position_sizing`, `thesis_integrity`, `market_integrity`, `volatility_trend` API naming, and old A-F assumptions.
- Add backend tests for every grade boundary and each dimension's missing-data behavior.

What's explicitly deferred:

- Full methodology UI.
- Payments.
- APNs production validation.

Prerequisites:

- Phase 1 additive schema is applied.
- A test fixture set exists for at least one stock and one ETF.

Exit criteria:

- All five dimensions compute correctly and persist in `ticker_risk_snapshots`.
- Composite score uses equal weighting and limited-data rescaling.
- Old dimensions are not emitted in new API contracts.
- Backend tests pass.

Estimated effort: 3-5 days.

## Phase 3 — News Pipeline Consolidation

What's in scope:

- Make `shared_ticker_events` the only article/event store.
- Move ticker article discovery to Google News RSS with canonical URL dedupe.
- Add Jina Reader primary extraction and trafilatura/newspaper fallback.
- Score every article with MiniMax for `sentiment_score`, `sentiment_reason`, `impact_tag`, TLDR, What It Means, and Key Implications.
- Implement recency/source weighting and article-volume signal.
- Retire `news_items` and `ticker_news_cache` after all reads/writes are gone.

What's explicitly deferred:

- Looming storyline clustering.
- International/crypto news expansion.

Prerequisites:

- Phase 1 backfill complete.
- Scheduler code no longer requires old tables.

Exit criteria:

- All news reads and writes use `shared_ticker_events`.
- Article audit data is available for News Sentiment pages.
- `news_items` and `ticker_news_cache` are dropped or marked fully unused pending drop.
- Backend tests cover dedupe, paywall fallback, and limited-data scoring.

Estimated effort: 3-4 days.

## Phase 4 — API Surface Updates

What's in scope:

- Update `/digest`, `/holdings`, `/tickers/search`, `/tickers/{ticker}`, `/alerts`, `/preferences`, and account export/delete contracts.
- Add methodology and article detail endpoints if not embedded in ticker detail.
- Remove raw backend statuses and legacy grade strings from user-visible response fields.
- Enforce Free/Pro limits server-side where required.

What's explicitly deferred:

- iOS implementation.
- Payment processor integration; use `subscription_tier` until Phase 8.

Prerequisites:

- Phase 2 and Phase 3 data is available.

Exit criteria:

- Every wireframe screen has backend data available.
- No new response emits `position_sizing`, `thesis_integrity`, `mirofish_used`, or fabricated previous scores.
- API tests document the v2 contracts.

Estimated effort: 2-3 days.

## Phase 5 — iOS: Grade System & Design Token Update

What's in scope:

- Replace A-F model with AAA-F grade enum and ordinal mapping.
- Update `ClavisDesignSystem.swift` for sharp paper-based v2 tokens, burnt-orange accent, mono ledgers, and bond-grade badges.
- Remove old grade labels and color mappings.
- Replace `.capitalized` backend-status display with explicit copy mapping.

What's explicitly deferred:

- Full screen rebuilds except fixes needed to compile.

Prerequisites:

- API contracts for v2 grade fields are stable.

Exit criteria:

- All grade displays can render `AAA`, `AA`, `A`, `BBB`, `BB`, `B`, `CCC`, `CC`, `C`, and `F`.
- No iOS model fabricates previous score or grade history.
- iOS build passes.

Estimated effort: 1-2 days.

## Phase 6 — iOS: Screen-by-Screen Rebuild

What's in scope:

- Rebuild in dependency order: app shell tabs, onboarding, Today digest, Holdings+Watchlist, Ticker Detail, Search, Alerts, Settings, Paywall shell.
- Use wireframe C as ticker detail direction and D3 or final product choice for digest style.
- Remove Dashboard as a top-level tab unless the product owner explicitly reverses the wireframe decision.
- Replace Position Detail with ticker-first detail plus portfolio overlay.

What's explicitly deferred:

- StoreKit purchase flow logic beyond paywall shell until Phase 8.
- Push delivery validation until Phase 9.

Prerequisites:

- Phase 5 complete.
- Phase 4 contracts available in `APIService` models.

Exit criteria:

- All screens match v2 wireframes closely enough for manual review.
- No MVP placeholder copy remains.
- No banned user-visible strings appear.
- iOS simulator build passes and manual smoke test completes.

Estimated effort: 5-8 days.

## Phase 7 — Methodology Drill-Down

What's in scope:

- Implement score-tap methodology drawer.
- Implement five full audit pages.
- Implement article detail with collapsed Why this score.
- Show formulas where `CLAVIX_TRUTH.md` requires formulas and show input/weight tables where wireframes require audit readability. If wireframes and truth conflict, truth wins.
- Ensure every visible number maps to stored real data.

What's explicitly deferred:

- v1.5 storyline clustering and custom date ranges.

Prerequisites:

- Phase 2 audit data and Phase 3 article data are persisted.
- Phase 6 ticker navigation exists.

Exit criteria:

- Every score is auditable per `CLAVIX_TRUTH.md` §8.
- Per-article sentiment score and reason are visible behind user-friendly labels.
- No fabricated deltas appear when history is missing.

Estimated effort: 3-5 days.

## Phase 8 — Payments & Paywall

What's in scope:

- Implement StoreKit 2 + RevenueCat or choose one processor with explicit decision.
- Add Pro entitlement write path to `subscription_tier` or entitlement table.
- Enforce Pro gates: unlimited holdings, brokerage sync, CSV import, verbose digest, manual refresh, watchlist alerts, macro shock alerts, severity thresholds.
- Implement 14-day trial, no credit card, auto-downgrade behavior.

What's explicitly deferred:

- Annual plan.
- Institutional tiers.

Prerequisites:

- Paywall UI shell exists.
- App Store product IDs are created.

Exit criteria:

- A real user can start trial and upgrade to Pro.
- Server-side tier checks cannot be bypassed by client UI changes.
- Paywall copy matches `CLAVIX_TRUTH.md` §16.

Estimated effort: 3-5 days.

## Phase 9 — APNs & Alerts

What's in scope:

- Deploy APNs `.p8` key to VPS only.
- Ensure `/health` reports APNs as OK.
- Implement grade-change hysteresis and alert generation using v2 grades.
- Implement digest-ready, major news, portfolio grade, watchlist, and macro shock alerts.
- Implement quiet-hours queue behavior.

What's explicitly deferred:

- Email alerts unless Pro email digest is explicitly prioritized after push works.

Prerequisites:

- Phase 4 alert API and Phase 8 tier checks are in place.

Exit criteria:

- A grade change alert fires on a real device.
- Alert center tap-through destinations work.
- Quiet-hours behavior is manually verified.

Estimated effort: 2-3 days.

## Phase 10 — SnapTrade & Brokerage Sync

What's in scope:

- End-to-end brokerage connect and callback test using `clavix://` canonical scheme plus `clavis://` compatibility.
- Nightly and manual sync of holdings.
- Connected brokerage display in Settings without showing the string `SnapTrade`.
- CSV import for Pro users.

What's explicitly deferred:

- Multi-portfolio support.
- Corporate-action cost-basis adjustments.

Prerequisites:

- Phase 8 Pro entitlement enforcement.
- URL schemes tested in iOS.

Exit criteria:

- A real brokerage can connect and sync holdings.
- User can see synced holdings and manual holdings together.
- Disconnect removes brokerage credentials safely.

Estimated effort: 3-4 days.

## Phase 11 — Branding & Copy Sweep

What's in scope:

- Sweep all user-visible iOS copy for Clavix naming and banned strings.
- Sweep backend response messages that reach iOS.
- Update methodology page source and marketing copy references.
- Ensure dual URL scheme handling.
- Remove fabricated previous score patterns everywhere.

What's explicitly deferred:

- Non-user-visible internal Swift type renames; keep `Clavis*` internal names.

Prerequisites:

- Major UI/API changes are complete.

Exit criteria:

- Zero user-visible `Clavis`, `SnapTrade`, `shared ticker cache`, raw backend status capitalization, or fabricated previous scores.
- App Store subtitle/tagline is `Portfolio risk, measured.`

Estimated effort: 1-2 days.

## Phase 12 — Security & Launch Hardening

What's in scope:

- Put `/admin` behind Cloudflare Access.
- Fix `SECURITY DEFINER` functions executable by `anon`/`authenticated`.
- Audit RLS after schema changes.
- Remove tracked iOS anon key by templating xcconfig and injecting safely.
- Drop legacy tables/columns only after code-reference verification.
- Run Supabase security and performance advisors.
- Run backend test suite and iOS build.

What's explicitly deferred:

- Any feature not in v1 scope.

Prerequisites:

- Phases 1-11 complete.

Exit criteria:

- Audit checklist complete.
- No P0 security findings open.
- Production deploy health check passes.

Estimated effort: 2-3 days.

## Pre-Launch Checklist

- App display name is Clavix.
- Bundle ID remains `com.clavisdev.portfolioassistant`.
- App Store subtitle is `Portfolio risk, measured.`
- Legal pages are live on `getclavix.com`.
- Public methodology page matches `docs/PRODUCT/methodology.md` or the chosen public markdown source.
- APNs key is present on VPS and absent from git.
- StoreKit products are approved or ready for review.
- Supabase advisors show no unresolved launch-blocking security issues.
- Backend CI passes.
- iOS simulator build passes.
- A real device can sign up, complete onboarding, add holdings, receive digest-ready push, open ticker detail, inspect methodology, and delete account.
