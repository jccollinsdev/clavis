# Backend Data Generation Plan - VisualQA Target

Generated: 2026-05-23  
Basis: `ios/Clavis/App/ClavixVisualQA.swift`, `docs/CLAVIX_TRUTH.md`, `docs/REFACTOR_PLAN.md`, live schema/row-count spot checks.

This is not an implementation plan for this session. It lists the backend/data work required to make the VisualQA mock honest in production.

## 1. Portfolio Hero

| VisualQA field | Current DB/API support | Backend generation plan | Required storage/API | Honest fallback |
|---|---|---|---|---|
| portfolio value | Partially exists client-side from `GET /holdings`: `shares * current_price`. DB has `positions.shares`, `ticker_metadata.price`, `positions.current_price`. | Compute server-side per user from latest price for each held position. Exclude tracked tickers. Return as canonical portfolio summary to avoid Today/Holdings disagreement. | Add `portfolio.value`, `portfolio.value_as_of`, `position.market_value` to `/today` or `/holdings` envelope. | `-` until at least one priced holding exists. |
| daily dollar change | Missing exact field. DB has `ticker_metadata.price` and `previous_close` for 506/508 tickers. | Per position: `shares * (price - previous_close)`. Portfolio: sum positions. | Add `position.day_change_amount`, `position.day_change_pct`, `portfolio.day_change_amount`, `portfolio.day_change_pct`. No new DB required. | `Today -` if previous close missing. |
| grade | Partial. `digests.overall_grade` exists, `ticker_risk_snapshots.grade` exists. Current digest fallback can equal-average and defaults legacy `C`. | Compute value-weighted portfolio score from latest ticker snapshots and position market values. Apply v2 grade mapping. Persist daily. | Add v2 `portfolio_risk_snapshots.composite_score`, `grade`, five dimension rollups, `methodology_version` or store in digest JSON with snapshot reference. | `-` if no scored holdings. |
| composite score | Partial. `digests.overall_score`; no guaranteed value-weighted source. | Same as grade; compute from value-weighted dimension rollups or value-weighted ticker composite. | Add `portfolio.composite_score`. | `-`. |
| score/grade delta | Partial data in snapshots, but no portfolio delta contract. | Compare to prior portfolio snapshot from previous trading day only. Never synthesize. | Add `portfolio.previous_score`, `previous_grade`, `score_delta`, `grade_delta`, `history_count`. | `New` or `-` if fewer than 2 portfolio snapshots. |
| generated timestamp | Exists for digest as `digests.generated_at`. | Return timezone-aware display metadata for Today and report. | Add `generated_at`, `display_time`, `timezone`. | `Not generated yet`. |

## 2. Five-Axis Snapshot

| Dimension | Current support | Portfolio aggregation rule | DB/source requirements | Endpoint requirements |
|---|---|---|---|---|
| Financial Health | Ticker field exists; fundamentals sparse (`debt_to_equity` 10/508, `fcf_margin` 0/508, `interest_coverage` 0/508). | Value-weighted average of available held ticker financial scores; ETFs use weighted top holdings or `Limited`. | Backfill Finnhub/Polygon fundamentals and ETF holdings inputs; store in `ticker_risk_snapshots.dimension_inputs`. | `portfolio.dimensions.financial_health`: score, delta, limited flag, coverage count. |
| News Signal | Ticker field exists; article enrichment is substantially populated in `shared_ticker_events`. | Value-weighted average of ticker news scores, excluding limited-data tickers; include article count coverage. | Continue Google News/Jina/MiniMax enrichment and source/recency weighting. | score, delta, article count, limited flag. |
| Macro Exposure | Ticker field exists in many snapshots, but shared macro table has 0 rows. | Value-weighted average of ticker macro scores; add portfolio macro factor sensitivity summary. | Run 252-day regressions and daily macro factor refresh. Populate `macro_regime_snapshots`. | score, delta, top macro factors, limited flag. |
| Sector Exposure | Ticker field exists for 9210/14907 snapshots; sector shared table has 0 rows. | Value-weighted average of ticker sector exposure; also return sector card grid. | Populate `sector_regime_snapshots` and sector ETF bars. | score, delta, sector drivers, limited flag. |
| Volatility | Ticker field exists; prices table has data. | Value-weighted average of ticker volatility scores. | Compute from `prices`: 30d/90d realized vol, ratio, max drawdown, beta. | score, delta, limited flag. |

Composite rule: equal 20% weighting for ticker scores. For portfolio five-axis, weight each ticker contribution by current position market value. If a ticker dimension is limited, exclude that ticker's dimension contribution from that dimension rollup and expose coverage. If an entire portfolio dimension has insufficient coverage, show `Limited` instead of a score.

## 3. Sector Exposure / Sector Heat

| VisualQA sector card | ETF mapping | Current DB support | Required generation |
|---|---|---|---|
| Technology / XLK | XLK | `ticker_cache_service.SECTOR_ETF_MAP` maps technology/information technology to XLK. `sector_regime_snapshots` has 0 rows. | Fetch XLK daily/intraday bars; compute daily change, 30d relative performance, breadth, narrative. |
| Health Care / XLV | XLV | Map currently uses `healthcare`, not explicit `health care`. | Normalize GICS sector names; map Health Care to XLV. |
| Financials / XLF | XLF | mapping exists | same as above. |
| Energy / XLE | XLE | mapping exists | same as above. |
| Consumer Discretionary / XLY | XLY | mapping exists | same as above. |
| Consumer Staples / XLP | XLP | mapping exists | same as above. |
| Industrials / XLI | XLI | mapping exists | same as above. |
| Utilities / XLU | XLU | mapping exists | same as above. |
| Materials / XLB | XLB | mapping exists | same as above. |
| Real Estate / XLRE | XLRE | mapping exists | same as above. |
| Communication Services / XLC | XLC | mapping exists | same as above. |

Required market data source: Polygon daily aggregates for sector ETFs. If pre-market sector movement is displayed, add a clear source and timestamp; otherwise label as latest close.

ETF daily bars in DB: not proven as a dedicated factor table. `prices` may hold ticker prices but no confirmed VisualQA sector heat contract. Prefer a `market_factor_prices` table or reuse `prices` if sector ETFs are populated consistently.

Portfolio sector exposure calculation:

1. Map each held ticker to canonical sector from `ticker_metadata.sector`.
2. Compute position market value from shares and latest price.
3. Sector weight = sector market value / total portfolio value.
4. Sector grade = value-weighted composite grade of tickers in that sector, not ETF grade unless explicitly labeled.
5. Sector day change = sector ETF daily change, not portfolio sector P&L, unless field is renamed.

## 4. Holdings / Position Ledger

| Field | Current support | Required backend work |
|---|---|---|
| position value | Client can compute; server should return canonical. | Add `market_value` to enriched holdings. |
| weight | Client can compute, but server envelope missing. | Add portfolio total and per-position `weight_pct`. |
| day change | Missing exact field. | Compute from `ticker_metadata.price` and `previous_close`. |
| grade/composite | Partial via shared analysis/snapshots. | Ensure v2 grade scale and latest ticker snapshot are the source. |
| dimension deltas | Missing exact field. | Compare latest snapshot to prior valid snapshot per dimension. |
| mini sparklines | Prices exist. | Return compact price series or let frontend call `/prices/{ticker}` lazily. |
| tracked ticker data | Watchlist exists, but detail enrichment incomplete. | Return watchlist items enriched with latest price, grade, score, deltas. |
| edit/delete | API exists. | Extend update/create models for purchase date/account if shown. |
| free limit | UI copy exists; server enforcement incomplete. | Enforce limits in `POST /holdings` and `POST /watchlists/default/items`. |
| outside universe | DB has `positions.outside_universe`; route currently rejects unsupported tickers. | Allow degraded manual create and return limited-data state. |

## 5. Ticker Detail

| Area | Current support | Required generation/storage/API |
|---|---|---|
| hero price/grade/composite | Partial via `/tickers/{ticker}` and metadata/snapshots. | Return exact v2 grade, score, previous score/grade, score delta, hysteresis state, latest price/day change. |
| sparkline/chart | `/prices/{ticker}` exists. | Add period support and ensure enough adjusted daily closes. |
| dimensions | `/methodology` and ticker detail partial. | Return five dimensions with deltas, limited-data flags, last refreshed, and audit route IDs. |
| radar/chart | Needs same five dimensions. | No extra backend if dimension array complete. |
| position context | `portfolio_overlay` exists partial. | Ensure held/watchlist state, shares, cost basis, market value, weight, P&L are returned for current user. |
| drivers | Risk driver cards exist partial. | Drivers must reference source event IDs and score impact. |
| recent news | `shared_ticker_events` enriched. | Return article IDs, source tier, score, weight, extraction/paywall status. |
| score history | DB has snapshots; no exact endpoint. | Add `/tickers/{ticker}/score-history` or embed history arrays. |
| refresh/limit states | Refresh route exists; status is latest job only. | Add per-user allowance, remaining count, reset time, Pro/admin gate metadata. |
| already-held state | Position overlay can support. | Return `is_held`, `holding_ids`, and edit route metadata. |

## 6. Methodology Audit

Every score shown by VisualQA must expose formula, inputs, source, and timestamp.

| Dimension | Required generation |
|---|---|
| Financial Health | Pull Finnhub `stock/metric`/profile metrics or alternate fundamentals source. Compute debt/equity, FCF margin, interest coverage, current ratio, 4Q revenue trend, profitability trend. Store raw values, normalized scores, weights, filing date, sector median. ETF handling requires top holdings. |
| News Signal | For trailing 7 days, score each article with MiniMax, store sentiment reason, source tier, recency/source weights, extraction status, paywall flag, volume signal. Exclude score and show limited data if fewer than 3 articles. |
| Macro Exposure | Run 252-trading-day regression against 10Y, DXY, WTI, VIX, SPY. Store coefficients, R2, trading days, current factor levels, limited flag, narrative. |
| Sector Exposure | Map ticker sector to ETF, compute 90d sector beta, 30d sector momentum vs SPY, breadth, narrative adjustment. Store source ETF and narrative timestamp. |
| Volatility | Compute 30d/90d realized vol, 30/90 ratio, max drawdown, beta to SPY from daily bars. Store values and timestamp. |

Required endpoint shape: `GET /tickers/{ticker}/methodology` should either return all full audit rows or provide dimension detail endpoints. Current route returns many fields, but lacks deltas, source rows, input weights, full raw input rows, sector medians, and complete limited-data semantics.

## 7. Morning Report

Required stored/generated sections:

1. Header: date/time, value-weighted portfolio grade/score, real previous score if available.
2. Macro: shared generated prose, factor moves, source list, generated timestamp.
3. Sector: user-specific sector exposure rows with ETF moves and held tickers.
4. Positions: held tickers ranked by real risk-score change, grade, delta, reason, destination ticker ID.
5. Tracked tickers: same format for watchlist/tracked names with tier limits.
6. Calendar: macro data, Fed events, and earnings events relevant to holdings/tracked tickers.
7. Sources/methodology footer: methodology version and latest data timestamps.

Storage: keep final report in `digests` with structured JSON. Shared macro/sector building blocks should live in `macro_regime_snapshots` and `sector_regime_snapshots` to avoid regenerating per user.

Endpoint: keep `GET /digest`, but make VisualQA Today consume a stable envelope or add `GET /today` as an aggregator over digest, holdings summary, alert summary, and sector heat.

## 8. Alerts

Required fields:

| Field | Current support | Required work |
|---|---|---|
| severity | partial/implicit | Add normalized severity. |
| category | type exists but legacy | Map to VisualQA categories: grade, news, macro, portfolio, tracked. |
| read/unread | missing | Add `read_at`; return unread counts. |
| destination metadata | missing/partial | Add `destination_type`, `destination_id`, ticker, article_id, methodology dimension. |
| grade change metadata | partial | Store previous/new grade/score, delta, hysteresis proof. |
| article/news metadata | partial | Link to `shared_ticker_events.id`. |
| portfolio impact metadata | missing | Store affected positions and portfolio score impact. |
| notification preferences | partial | Add digest, tracked ticker, macro shock, severity threshold prefs. |

## 9. Search

| Area | Required work |
|---|---|
| universe lookup | Existing `/tickers/search` should return grade, price, in-portfolio, tracked state, outside-universe eligibility. |
| outside-universe detection | If ticker absent from universe, return reason and whether manual degraded add is allowed. |
| result rows | Need price, day change, grade, score, company, sector, held/tracked state. |
| recent/trending/browse | Recent can be client-local or server-side; trending needs a real source or should be hidden. Browse chips require backend filters. |
| add-position eligibility | Add endpoint/contract that returns free limit, Pro gates, duplicate held state, outside-universe status. |

## 10. Article Detail

Required endpoint: `GET /articles/{id}` or `GET /tickers/{ticker}/articles/{id}` over `shared_ticker_events`.

Required fields: ticker, title, source, source URL, canonical URL, published timestamp, source tier, TLDR, what-it-means, key implications, sentiment score, sentiment reason, source/recency weights, extraction status, paywall flag, confidence, included-in-score flag, and user portfolio context if held.

Fallbacks: if body extraction fails, show extraction state and exclude from score if appropriate. If paywalled, show headline-based low-confidence flag only if backend truly scored it that way.

## 11. Settings / Account

| Area | Current support | Required work |
|---|---|---|
| user preferences | `GET/PATCH /preferences` exists. | Add timezone, next report time, missing alert prefs. |
| report preferences | digest time/summary length exists. | Enforce Pro-only verbose/expanded length server-side. |
| alert settings | partial. | Add tracked ticker, macro shock, digest-ready, severity threshold. |
| brokerage sync status | routes exist. | Return user-facing status, last sync, accounts, positions, auto-sync. |
| subscription status | only `subscription_tier`. | StoreKit/entitlement backlog; do not implement now. |
| export/delete | routes exist. | Ensure v2 shared/user-owned data included/deleted correctly. |
| support/legal | mostly static links. | Provide canonical support email/legal URLs. |

## 12. Paywall / StoreKit

Backlog only. No StoreKit or payment implementation in this audit.

Required later: StoreKit 2 or RevenueCat decision, App Store product IDs, server-side entitlement verification, trial eligibility, entitlement event table, subscription endpoint, and server-side gates for Pro-only VisualQA elements.
