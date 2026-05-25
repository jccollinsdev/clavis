# Clavix — Scheduling & Data Freshness Implementation Plan

**Version:** 1.0
**Date:** 2026-05-25
**Status:** Plan. Authored after parallel audits of: backend pipeline + scheduler, Supabase schema, and the 69-screen Hi-Fi v2 design handoff.

> **Authority chain.** `docs/CLAVIX_TRUTH.md` → `AGENTS.md` → `docs/REFACTOR_PLAN.md` → this file. This plan **extends** `docs/P0_P1_P2_IMPLEMENTATION_PLAN.md` and `docs/BACKEND_DATA_GENERATION_PLAN.md` with the scheduling layer that was missing from both, plus the data gaps newly visible from the design_handoff_clavix 69-screen spec that landed 2026-05-25.

---

## 0. Why this plan exists

Two concrete problems in the user's words:

1. *"News refresh is daily and working (503/503 S&P backfill passed). I need to schedule the **structural data** — volatility, macro, sector, fundamentals, earnings — so everything stays fresh **without redundant calls**."*
2. *"The new UI requires many different API calls / datapoints, and many of them simply do not exist because we don't generate them. Audit the pipeline so all 69-screen datapoints are actually produced."*

This plan answers both. It does **not** re-do the per-screen data inventory already in `docs/MOCK_TO_LIVE_AUDIT.md` and `docs/UI_DATA_CONTRACT_MATRIX.md` — those still stand for everything they covered. It **adds**:

- A cadence design for every data domain (so nothing is over- or under-refreshed)
- A scheduler execution model that works with Render's current prod constraints
- The data-coverage delta introduced by the new design_handoff_clavix bundle (69 screens) versus what the previous audits captured
- A phased implementation order with explicit acceptance criteria and rollback

---

## 1. Current state, in one page

### 1.1 What runs today (the news pipeline that works)

| Job | Cadence | Trigger | Status |
|---|---|---|---|
| `system_sp500_daily_refresh` | 08:00 ET daily | APScheduler cron | Wired (cache reseed) |
| `system_sp500_backfill` | 07:30 ET daily | APScheduler cron | Wired (news + LLM risk scoring, 503/503 ✓) |
| `system_holdings_daily_ai_refresh` | 07:00 ET daily | APScheduler cron | Wired (per-user holding analysis) |
| `system_active_ticker_news_refresh` | every 4h | APScheduler interval | Wired (Finnhub news) |
| `system_bulk_sentiment_enrichment` | every 2h | APScheduler interval | Wired (LLM rescoring) |
| `system_news_cleanup` | 08:30 ET daily | APScheduler cron | Wired (30-day TTL) |
| per-user digest (`user_{uuid}`) | per-user `digest_time` | APScheduler cron | Wired |
| per-user structural (`user_{uuid}_structural`) | 06:30 ET daily | APScheduler cron | Wired (calls `upsert_ticker_metadata`) |

**Critical constraint:** `PAUSE_SYSTEM_SCHEDULER=true` in [render.yaml](render.yaml). In prod, **none of the system jobs run.** The per-user jobs only run if a user request boots the worker that calls `start_scheduler()`. The 503/503 backfill the user just finished was triggered manually via [backend/scripts/sp500_precompute.py](backend/scripts/sp500_precompute.py).

### 1.2 What's missing (the structural gap)

| Domain | Pipeline module | DB sink | Scheduler wiring | Status |
|---|---|---|---|---|
| Macro regime snapshot | [`pipeline/macro_snapshot.py`](backend/app/pipeline/macro_snapshot.py) | `macro_regime_snapshots` (upsert helper exists: `save_daily_macro_regime()`) | **None — dead code** | 🔴 Orphaned |
| Sector regime snapshot | [`pipeline/sector_snapshot.py`](backend/app/pipeline/sector_snapshot.py) | `sector_regime_snapshots` | **None — dead code** | 🔴 Orphaned |
| Sector ETF day-change (XLK, XLV, XLF, …) | none | none (would belong in `sector_regime_snapshots`) | none | 🔴 Missing |
| Daily composite recompute for **all** S&P 500 (not just news) | `pipeline/risk_scorer.py` + `structural_scorer.py` | `ticker_risk_snapshots` | Runs *inside* S&P backfill; structural metadata refresh is *per-user only* | 🟡 Partial |
| Score history persistence (so 90d sparklines exist) | implicit in daily snapshot writes | `ticker_risk_snapshots` (unique `ticker,snapshot_date`) | Depends on daily composite running | 🟡 Partial |
| Volatility recompute (30d/90d/ratio/drawdown/beta) | done inline in `structural_scorer.py:_build_volatility_inputs(ticker_bars, spy_bars)` | `ticker_risk_snapshots.dimension_inputs.volatility` | On-demand during snapshot only | 🟡 Partial |
| Macro regression (252-day β, R²) | `services/macro_regression.py` | `ticker_risk_snapshots.dimension_inputs.macro_exposure` | On-demand only | 🟡 Partial |
| Fundamentals (earnings, FCF, leverage, sector medians) | `services/ticker_metadata.py` (`upsert_ticker_metadata`) | `ticker_metadata` | Per-user 06:30 ET + 7-day TTL only; **no S&P-wide schedule** | 🟡 Partial |
| Earnings calendar (Today catalysts) | none real (currently LLM-synthesised in digest) | none | none | 🔴 Missing |
| Sector medians / peer benchmarks (for FIN audit z-scores) | none | none | none | 🔴 Missing |
| Daily VIX/SPY/factor capture | none discrete (folded into macro_snapshot, which is orphaned) | `macro_regime_snapshots` columns | none | 🔴 Missing |

### 1.3 The 69-screen UI bundle adds these net-new asks

Cross-checking the screen audit against the existing `BACKEND_DATA_GENERATION_PLAN.md`, the design_handoff that landed today introduces or sharpens these requirements:

- **`★ PERSONALISED` "What it means for YOU" overlay** on every News article and grade-change Alert detail (`news-main`, `alerts-detail`) — backend must do per-user article personalisation tied to the user's actual holdings.
- **Peer group rendering** in `meth-sec` (sector audit shows peers with relative grades) and `meth-fin` (sector median comparison) — needs a `peer_groups` table or computed view, doesn't exist.
- **14-day article histogram + per-article z-scored sentiment distribution** in `meth-news` — needs aggregation query on `shared_ticker_events`.
- **Macro factor exposures bar (rates / USD / oil / SPY β) + 10 most recent macro events** in `meth-mac` — `macro_regression` produces coefs but the "10 recent events" list isn't a stored view.
- **Volatility regime label (low / mid / high) + IV-rank + earnings-period overlay** in `meth-vol` — IV-rank and implied vol are NOT currently sourced (only realized vol is computed).
- **Score history sparkline + "was AA 5 days ago"** on every grade pill across ticker/today/alerts screens — confirmed `/tickers/{ticker}/score-history` exists (per agent 2 audit) but is sparse until daily snapshots accumulate.
- **Refresh limit state** (`3/day` free, unlimited Pro) on `ticker-refresh` — needs `refresh_attempts_today` per user, not currently tracked.
- **Outside-universe degraded add path** with honest limited-data card — `positions.outside_universe` column not yet added.
- **Sector heat grid with `etf_day_change_pct` + `portfolio_weight_pct` per sector** on `today-a/b` — requires `sector_regime_snapshots` populated AND a portfolio-aggregation endpoint.
- **Morning Report issue number (monotonically increasing)** — needs a counter on `digests`.

The good news: every other 69-screen datapoint maps onto an existing table column or one already planned in `BACKEND_DATA_GENERATION_PLAN.md`.

---

## 2. The scheduling design

### 2.1 Principles

1. **One source of truth for "is X fresh?"** — Every refreshable domain has a single `*_refreshed_at` timestamp (column or a row in `scheduler_jobs`). Every job checks freshness before doing work. No redundant calls.
2. **Refresh at the slowest cadence that still makes the UI honest.** Earnings filings change quarterly, so don't refresh fundamentals daily. Macro regime changes daily, so don't refresh it weekly.
3. **Heavy work runs off-hours.** Anything S&P 500-wide or > 5 minutes of LLM compute runs between 02:00–05:00 ET so it finishes before the 07:00 ET morning report.
4. **Skip on freshness, not on schedule.** Jobs ALWAYS attempt at their cadence; they self-skip per-ticker when the data is still inside its TTL. This makes recovery from prod outages automatic.
5. **All jobs are idempotent.** Upserts on `(ticker, as_of_date)` or `(user_id, as_of_date)` — re-running a job for the same day overwrites cleanly.
6. **Every job writes an audit row.** New `job_runs` table records `job_id, started_at, completed_at, status, items_processed, items_skipped, items_failed, error`. Visible in admin UI and feeds the "Refreshed 03:17 ET" timestamps the design specs want.

### 2.2 Cadence design — one table

Times in ET. "Held" = a ticker present in any user's `positions` or `watchlist_items`. "Universe" = `ticker_universe.is_active = true` (S&P 500 + extensions).

| Tier | Cadence | Job | Scope | What it produces | Skip condition |
|---|---|---|---|---|---|
| **0 — Intraday** | every 5 min, 09:30–16:00 ET, weekdays | `intraday_price_refresh_held` | Held tickers | `ticker_metadata.price`, `previous_close` | ticker not held by any user; outside market hours |
| | every 15 min, 09:30–16:00 ET, weekdays | `intraday_price_refresh_watchlist` | Watchlist-only (not held) | same | already refreshed in last 15 min |
| | every 4h (existing) | `system_active_ticker_news_refresh` | Held + watchlist | Finnhub news → `shared_ticker_events` | unchanged |
| | every 2h (existing) | `system_bulk_sentiment_enrichment` | Recent unenriched articles | LLM enrichment fields on `shared_ticker_events` | already enriched |
| **1 — Daily (pre-market)** | 04:00 ET | `daily_earnings_calendar_refresh` | Held + watchlist + S&P 500 | new `earnings_calendar` table (date, ticker, est_eps, est_revenue, time) | already refreshed today |
| | 04:30 ET | `daily_factor_bars_refresh` | TLT, UUP, USO, VIXY, SPY, XLK…XLC, VTI | `prices` rows for factor ETFs | already today |
| | 05:00 ET | `daily_macro_snapshot` ✨NEW WIRING | one row | `macro_regime_snapshots` (vix, ust10y, dxy, wti, spy, regime_state) | row exists for today |
| | 05:15 ET | `daily_sector_snapshot` ✨NEW WIRING | 11 sector ETFs | `sector_regime_snapshots` (sector, etf, day_change_pct, breadth, momentum, narrative) | row exists for today |
| | 05:30 ET | `daily_news_full_refresh` | Held + watchlist | Finnhub news, full window | per-ticker fresh < 4h |
| | 06:00 ET | `daily_composite_recompute_universe` ✨EXPANDED | Universe (~503 tickers) | `ticker_risk_snapshots` (composite, 5 dims, dimension_inputs, dimension_last_refreshed) | snapshot < 24h |
| | 06:30 ET | `daily_composite_recompute_outside_universe` ✨NEW | Held tickers NOT in universe (P1-7 degraded) | degraded `ticker_risk_snapshots` row + `limited_data` flag | universe ticker (handled above) |
| | 06:45 ET | `daily_portfolio_rollup_per_user` ✨EXPANDED | Every user | `portfolio_risk_snapshots` (value-weighted composite, 5 dims, prev-day delta, sector breakdown) | already rolled up for today |
| | 07:00 ET (existing per-user) | `user_{uuid}` digest | Per-user (default 07:00, configurable 06:00–08:00 Pro) | `digests` (Morning Report w/ all 6 sections) | per-user already today |
| | 07:30 ET | `system_sp500_backfill` (existing) | Universe | news + sentiment refresh, redundant safety pass | within-budget batch |
| | 08:30 ET (existing) | `system_news_cleanup` | All | drops articles > 30 days | unchanged |
| **1 — Daily (post-close)** | 16:15 ET | `daily_eod_price_capture` | Universe | OHLC into `prices` | row exists for today |
| | 16:30 ET | `daily_score_history_seal` ✨NEW | Universe | finalises `ticker_risk_snapshots` for today (locks against further intraday changes; provides clean 90d history) | already sealed |
| | 17:00 ET | `daily_alert_evaluation` ✨EXPANDED | Per-user | hysteresis-aware grade-change alerts, macro-shock alerts, news-spike alerts | per-user already today |
| **2 — Weekly** | Sat 02:00 ET | `weekly_volatility_recompute` ✨NEW | Universe | full 30d/90d/ratio/drawdown/SPY-β refresh into `dimension_inputs.volatility`; required for `meth-vol` IV-rank fields | snapshot < 7d |
| | Sat 03:00 ET | `weekly_peer_groups_recompute` ✨NEW | Universe | `peer_groups` table (per ticker → 5–10 peers with similarity score) | snapshot < 7d |
| | Sat 04:00 ET | `weekly_sector_medians_recompute` ✨NEW | Per sector | `sector_medians` table (debt/equity, FCF margin, interest coverage medians per sector) | < 7d |
| | Sun 03:00 ET | `weekly_universe_audit` | S&P CSV | reconcile `ticker_universe.is_active` vs. live S&P list; mark adds/removes | unchanged in 7d |
| **3 — Monthly** | 1st of month, 03:00 ET | `monthly_macro_regression_refresh` ✨NEW | Universe | 252-trading-day regression: β to 10Y, DXY, WTI, VIX, SPY → `dimension_inputs.macro_exposure` | < 30d |
| | 1st of month, 04:00 ET | `monthly_etf_holdings_refresh` ✨NEW | Held + watchlist ETFs | top holdings for portfolio-look-through scoring | < 30d |
| **4 — Quarterly / Event-driven** | T-1 day before earnings | `event_fundamentals_pull` | Ticker reporting tomorrow | `ticker_metadata` refresh (PE, FCF, revenue, leverage); set `next_earnings_date` | already refreshed in last 7d |
| | T+1 day after earnings | `event_fundamentals_postclose` | Ticker that reported yesterday | re-pull post-release fundamentals + force composite recompute | T-1 ran successfully |
| | else: every 90 days | `quarterly_fundamentals_safety_net` | Any ticker whose `next_earnings_date` lookup failed | force-refresh | refreshed in last 90d |
| **5 — On-demand** | user tap | `ticker_refresh_manual` | One ticker | full re-pull (news + composite) | rate-limit: 3/day Free, unlimited Pro |
| | user onboarding | `onboarding_seed_user` | New user's positions/watchlist | full first-pass refresh + degraded-mode for outside-universe adds | n/a |

### 2.3 Anti-redundancy mechanisms

1. **`dimension_last_refreshed` JSONB** on `ticker_risk_snapshots` already exists but is write-only. **Read it.** Per-dimension cadences check this before recomputing. Example: weekly volatility job skips a ticker whose `dimension_last_refreshed.volatility > now() - 7d`.
2. **`scheduler_jobs.next_run_at`** already exists. Use it as the canonical "when will this run next" for both system and per-user jobs. UI can render "Next refresh: 06:30 ET" from this.
3. **New `job_runs` table** (one row per job invocation) — see §4.1 — gives `items_skipped` so we can measure how much work was avoided.
4. **HTTP caching at the route layer** — `GET /tickers/{ticker}` already has freshness; extend the same pattern to `/today`, `/holdings`, `/portfolio/sector-exposure` so iOS gets `Cache-Control: max-age` headers tied to the underlying job cadence.
5. **External API rate limits respected by gates** — already in `services/polygon.py` (20s spacing) and Finnhub (0.12s). Don't add parallelism without bumping these.

### 2.4 Scheduler execution model — three options, recommendation

**Current prod state:** `PAUSE_SYSTEM_SCHEDULER=true` (in-process APScheduler disabled). All daily/structural data must be triggered manually right now.

| Option | Pros | Cons |
|---|---|---|
| **A. Re-enable in-process APScheduler** (`PAUSE_SYSTEM_SCHEDULER=false`) | Zero new infra. Code already exists. Per-user dynamic cron already implemented. | Render starter plan = 1 dyno; if it sleeps/restarts, jobs can be missed. No retry guarantee. Single-worker concurrency = stampedes if a job takes long. |
| **B. Render Cron Jobs** (separate `cron` services in `render.yaml`) | Independent infra. Retry on failure. Observable in Render dashboard. | Each cron is a new Render service ($). Need a tiny CLI entrypoint per job (`python -m app.jobs.run job_id`). |
| **C. Supabase `pg_cron` + Edge Functions** | Cron lives next to DB. Existing functions: `save_daily_macro_regime()`, `save_daily_asset_safety_profile()`. | Heavy LLM work doesn't run in Edge. Most jobs would still call back into the Render API, doubling round-trips. |

**Recommendation:** **Hybrid A + B.**
- **In-process APScheduler (option A)** for intraday Tier-0 jobs (price polls, news, sentiment enrichment) where short cadence + at-most-best-effort is fine.
- **Render Cron Jobs (option B)** for Tier-1+ jobs (anything daily/weekly/monthly that the morning report depends on). Each cron service runs a single command `python -m app.jobs.run <job_id>` against the same Docker image, then exits.
- Set `PAUSE_SYSTEM_SCHEDULER=false` (now safe because intraday jobs are the only ones in-process) BUT add a `SCHEDULER_TIER` env that filters which jobs APScheduler boots — Render dynos boot only Tier-0; cron services boot only their named job.

This gives:
- Tier-0 jobs survive a Render restart (next 5-min tick picks them up)
- Tier-1+ jobs get explicit cron-job retry semantics + visible run history
- No double-execution: every job is keyed by `SCHEDULER_TIER` env

---

## 3. Data-coverage roadmap (the 69-screen gap)

Each row below = one concrete deliverable. Cross-references the existing `MOCK_TO_LIVE_AUDIT.md` priorities so this slots into the existing P0/P1/P2 sequence.

| # | Deliverable | Tables touched | Routes touched | iOS surfaces | Aligns with |
|---|---|---|---|---|---|
| D1 | Wire `macro_snapshot.py` to scheduler + write to `macro_regime_snapshots` | `macro_regime_snapshots` | none | `today-a`, `today-digest`, `meth-mac` | P1 (precondition to P1-4) |
| D2 | Wire `sector_snapshot.py` to scheduler + add `etf_day_change_pct`, `breadth`, `momentum` columns | `sector_regime_snapshots` (+migration) | none | `today-a/b` sector grid, `meth-sec` | P1-4 |
| D3 | Add `GET /portfolio/sector-exposure` | reads `positions`, `ticker_metadata.sector`, `sector_regime_snapshots` | new route | `today-a/b`, `hold-main` sector composition | P1-4 |
| D4 | Add `GET /today` aggregator (composes digest header + sector heat + alert summary + top-movers + calendar) | reads many | new route | `today-a`, `today-b` | P1-1 + P1-4 |
| D5 | Add `earnings_calendar` table + `daily_earnings_calendar_refresh` job | new table | extend `/today` | `today-a/b` calendar; `meth-vol` earnings overlay | P1-4 |
| D6 | Add `peer_groups` + `sector_medians` tables + weekly recompute jobs | 2 new tables | extend `/methodology` | `meth-fin` z-scores, `meth-sec` peers | P2-1 |
| D7 | Add `daily_composite_recompute_universe` system job (not just S&P backfill, all dimensions) | writes `ticker_risk_snapshots` | none | every score on every screen | P1-3 / P2-2 |
| D8 | Add `daily_portfolio_rollup_per_user` job → `portfolio_risk_snapshots` with prev-day delta | writes `portfolio_risk_snapshots` | extend `/today`, `/holdings` portfolio envelope | `today-a/b` portfolio score + delta, `hold-main` header | P1-1 |
| D9 | Score history endpoint already exists per audit (`/tickers/{ticker}/score-history`); ensure D7 runs daily so 90d history accrues | `ticker_risk_snapshots` daily rows | existing | `ticker-main` history sparkline, "was AA 5 days ago" deltas | P1-3 |
| D10 | Add `refresh_attempts` table + per-user 3/day Free rate-limit on `POST /tickers/{ticker}/refresh` | new table | `tickers.py` | `ticker-refresh` limit card | P1-7 / P2-4 |
| D11 | Add `positions.outside_universe` column + degraded-mode `POST /holdings?allow_outside_universe=true` | `positions` migration | `holdings.py`, `tickers.py` | `hold-outside`, `ticker-limited` | P1-7 |
| D12 | Add per-user article personalisation at digest-compile time (writes `digest_articles_personalised` JSONB into `digests`) | `digests.structured_sections` | `digest.py` | `news-main` "What it means for YOU", `alerts-detail` | P2-5 |
| D13 | Add `digests.issue_number` (sequential per user) | `digests` migration | `digest.py` | `today-digest` "Issue 142" | P1 |
| D14 | Add IV-rank + implied vol pull (Polygon options or fallback) into `dimension_inputs.volatility` | extend `volatility` JSONB | `methodology.py` | `meth-vol` IV-rank line + regime label | P2-2 |
| D15 | Add monthly `macro_regression_refresh` writing β to 10Y/DXY/WTI/VIX/SPY into `dimension_inputs.macro_exposure` with `r2`, `trading_days` | `ticker_risk_snapshots` | `methodology.py` | `meth-mac` factor exposures bar | P2-1 |
| D16 | Add `event_fundamentals_pull` cron triggered by earnings calendar T-1/T+1 | writes `ticker_metadata` | none | quarterly-fresh fundamentals | P2-2 |
| D17 | Expose `freshness` block on `/today`, `/holdings`, `/portfolio/sector-exposure` (mirroring the existing `/tickers/{ticker}.freshness`) | none | extend each route | "Refreshed 03:17 ET" labels in every spec | P1 polish |
| D18 | Add `job_runs` table + admin route to query | new table | new admin route | not user-visible; powers (D17) timestamps | P1 |

Items D1, D2, D7, D8, D17 are the **critical path** for getting the design's Today/Holdings/Ticker screens to show real numbers instead of `—`. Everything else is a follow-on.

---

## 4. Implementation phases

Each phase is sequenced so the **previous phase's data exists** before the next phase needs it. Phase numbers continue from the existing P0/P1/P2 plan (this plan starts at **P3** to avoid confusion — "structural scheduling").

### Phase P3 — Scheduler foundation (3–4 days)

Goal: every system job has a place to run in prod, every job writes an audit row, and the orphaned macro/sector snapshots come alive.

| Item | Files | DB | Tests |
|---|---|---|---|
| P3-1 | Add `SCHEDULER_TIER` env (`intraday`/`cron`/`none`); gate APScheduler job registration on it. Document in `render.yaml`. | `backend/app/pipeline/scheduler.py`, `backend/app/main.py`, `render.yaml` | none | Boot with each tier and assert correct jobs registered |
| P3-2 | Add `job_runs` table (D18) | new migration | `job_runs(id, job_id, tier, started_at, completed_at, status, items_processed, items_skipped, items_failed, error_json)` | insert/query round-trip |
| P3-3 | New `app/jobs/run.py` CLI entrypoint: `python -m app.jobs.run <job_id>`; writes a `job_runs` row around execution. | new file | reads `job_runs` for skip-if-recent | dry-run + exit-code check |
| P3-4 | Wire `pipeline/macro_snapshot.py` to a new `daily_macro_snapshot` job (D1) | `scheduler.py`, `app/jobs/macro_snapshot.py` | writes `macro_regime_snapshots` via existing `save_daily_macro_regime()` | upsert idempotency test |
| P3-5 | Wire `pipeline/sector_snapshot.py` to a new `daily_sector_snapshot` job (D2). Add migration for `sector_regime_snapshots.etf_day_change_pct`, `breadth`, `momentum`, `narrative_last_refreshed` if missing. | `scheduler.py`, `app/jobs/sector_snapshot.py`, new migration | `sector_regime_snapshots` | upsert + 11-sector coverage test |
| P3-6 | Add 6 Render cron services for: macro_snapshot (05:00), sector_snapshot (05:15), composite_recompute (06:00), portfolio_rollup (06:45), eod_price_capture (16:15), alert_evaluation (17:00). | `render.yaml` | none | manual: trigger one in staging |
| P3-7 | Flip `PAUSE_SYSTEM_SCHEDULER=false` with `SCHEDULER_TIER=intraday` so only Tier-0 jobs boot in the web dyno. | `render.yaml` | none | watch logs for 24h |

**Acceptance:** in staging, `select count(*) from macro_regime_snapshots where as_of_date=current_date` returns 1 after 05:00 ET. Same for `sector_regime_snapshots` (11 rows). `job_runs` table has corresponding entries.

**Rollback:** flip `PAUSE_SYSTEM_SCHEDULER=true` and disable Render cron services. No schema changes are destructive.

### Phase P4 — Daily composite + portfolio rollup (3 days)

Goal: every S&P ticker has a fresh `ticker_risk_snapshots` row each morning before the 07:00 ET digest; every user has a fresh `portfolio_risk_snapshots` row.

| Item | Files | DB | Tests |
|---|---|---|---|
| P4-1 | New `daily_composite_recompute_universe` job (D7) — runs `refresh_ticker_snapshot` for every `ticker_universe.is_active` ticker, batched with the same 15-per-batch backoff as `sp500_precompute.py`. Uses `dimension_last_refreshed` to skip dimensions already fresh-enough. | new `app/jobs/composite_recompute.py`, reuse `pipeline/risk_scorer.py`, `structural_scorer.py` | reads/writes `ticker_risk_snapshots`, `dimension_last_refreshed` | per-dim freshness skip test |
| P4-2 | New `daily_portfolio_rollup_per_user` job (D8) — for each user, compute value-weighted composite + 5 dims from latest `ticker_risk_snapshots` × position market values; write to `portfolio_risk_snapshots` with prev-day delta. | new `app/jobs/portfolio_rollup.py`, reuse `pipeline/portfolio_compiler.py` math | `portfolio_risk_snapshots` row per user per day | 2-day delta test |
| P4-3 | Extend `GET /holdings` envelope per `UI_DATA_CONTRACT_MATRIX.md` to include `portfolio{value, composite_score, score_delta, previous_score, dimensions[]}` from P4-2's snapshot. | `routes/holdings.py`, `Models/Position.swift` (iOS) | reads `portfolio_risk_snapshots` | snapshot envelope test |
| P4-4 | Extend `GET /today` (or `/digest` if not yet promoted) similarly. | `routes/today.py` or `routes/digest.py` | same | same |
| P4-5 | Daily score-history accrues — verify `/tickers/{ticker}/score-history` returns growing series after P4-1 runs for 2+ days. | none (read-only validation) | none | integration test |

**Acceptance:** after 2 ET trading days post-deploy, every user with positions has 2 `portfolio_risk_snapshots` rows; iOS Today header shows `score_delta` instead of `—`.

### Phase P5 — Sector heat + earnings + Today aggregator (4 days)

Goal: iOS Today + Holdings render real sector heat and a real catalyst calendar.

| Item | Files | DB | Tests |
|---|---|---|---|
| P5-1 | New `GET /portfolio/sector-exposure` (D3) | new `routes/portfolio.py` | reads `positions`, `ticker_metadata.sector`, `sector_regime_snapshots` | weight sum = 1.0 |
| P5-2 | New `GET /today` aggregator (D4) — composes digest header + sector heat + alert summary + top-movers + calendar | new `routes/today.py` (already exists per audit — extend) | reads multiple | snapshot test of envelope shape |
| P5-3 | New `earnings_calendar` table (D5) + `daily_earnings_calendar_refresh` job from Finnhub `calendar/earnings` endpoint. | new migration, new `app/jobs/earnings_calendar.py` | `earnings_calendar(ticker, report_date, est_eps, est_revenue, time_of_day, fiscal_period, source, fetched_at)` | dedupe on `(ticker, report_date)` |
| P5-4 | Render sector heat from `sector_regime_snapshots` in `DigestView` / new `TodayView` (iOS) — replace prose-only with grid. | `ios/Clavis/Views/Digest/`, new TodayView | none | preview-driven |
| P5-5 | Add `freshness` block (D17) on each of the new routes returning `{as_of, job_id, age_seconds}`. | routes above | reads `job_runs` | freshness propagation test |

**Acceptance:** `today-a` and `today-b` mockups render with non-`—` numbers for sector heat and calendar after P5-3 cron has run once.

### Phase P6 — Methodology depth (5 days)

Goal: the 7 methodology screens (`meth-comp`, `meth-fin`, `meth-news`, `meth-mac`, `meth-sec`, `meth-vol`, `meth-page`) show real audit data.

| Item | Files | DB | Tests |
|---|---|---|---|
| P6-1 | Add `peer_groups` table + `weekly_peer_groups_recompute` job (D6) — kNN by sector + market-cap bucket; 5–10 peers per ticker. | new migration, new `app/jobs/peer_groups.py` | `peer_groups(ticker, peer_ticker, similarity, computed_at)` | self-link prevention |
| P6-2 | Add `sector_medians` table + `weekly_sector_medians_recompute` job. | new migration, new `app/jobs/sector_medians.py` | `sector_medians(sector, metric, median, p25, p75, n_tickers, as_of)` | per-metric coverage |
| P6-3 | Extend `/methodology` route to include per-dimension `peer_comparisons[]`, `sector_median_comparison{}`, `article_histogram_14d[]`, `sentiment_distribution[]`, `factor_levels{}` (D6, D15). | `routes/methodology.py` | reads new tables + `shared_ticker_events` | shape test |
| P6-4 | Add IV-rank + implied vol pull (D14). Polygon options API; fallback to estimated IV-rank from realised vol if unavailable. Persist into `ticker_risk_snapshots.dimension_inputs.volatility`. | `services/polygon.py`, `structural_scorer.py` | extends existing JSONB | unit test with sample chain |
| P6-5 | Monthly `macro_regression_refresh` (D15) — 252-trading-day β to 10Y/DXY/WTI/VIX/SPY, R², trading_days. | new `app/jobs/macro_regression.py` | extends `dimension_inputs.macro_exposure` | regression-vs-numpy fixture |
| P6-6 | Wire 5 audit views (`meth-fin/news/mac/sec/vol`) to render the new fields. iOS Models extend. | `ios/Clavis/Views/Tickers/*AuditView.swift`, `Models/Methodology.swift` | none | per-view previews |

**Acceptance:** every audit view passes the "no `—` where data exists" smoke test on AAPL, NVDA, F (low-priority outside-S&P), and one limited-data ticker.

### Phase P7 — Personalisation + alerts + outside-universe (3 days)

Goal: `★ PERSONALISED` overlays render, refresh limits enforced, outside-universe tickers addable.

| Item | Files | DB | Tests |
|---|---|---|---|
| P7-1 | Per-user article personalisation at digest-compile time (D12) — generate per-user "What it means for YOU" copy referencing the user's actual holdings; store in `digests.structured_sections.personalised_articles` JSONB keyed by `event_id`. | `pipeline/portfolio_compiler.py`, `routes/digest.py` | extends `digests` JSONB | LLM-output cap + cost gate |
| P7-2 | Surface personalised copy in iOS `ArticleDetailSheet`. | `ios/Clavis/Views/Tickers/ArticleDetailSheet.swift` | none | a11y label preview |
| P7-3 | Add `refresh_attempts` table + 3/day Free rate-limit on `POST /tickers/{ticker}/refresh` (D10). 429 with retry-after header on exceed. | new migration, `routes/tickers.py` | `refresh_attempts(user_id, attempted_at, ticker, result)` | rate-limit test |
| P7-4 | Add `positions.outside_universe` column + degraded path (D11). `POST /holdings?allow_outside_universe=true` creates with limited-data flag; `GET /tickers/{ticker}` surfaces the flag. | new migration, `routes/holdings.py`, `routes/tickers.py` | extends `positions` | round-trip test |
| P7-5 | Add `digests.issue_number` sequence per user (D13). | new migration, `routes/digest.py` | extends `digests` | sequence monotonicity test |
| P7-6 | Hysteresis-aware alert evaluation (Δ ≥ 3 + 2 consecutive days per `system/00-rules.md`) in `daily_alert_evaluation` job; populates the v2 alert columns added in 20260524 migration. | `pipeline/scheduler.py` alert section | writes `alerts` | hysteresis fixture |

**Acceptance:** a Free user can't refresh more than 3 tickers/day; an outside-universe ticker (e.g. `BBAI`) shows the limited-data card; a grade boundary cross with only 1-day Δ=4 does **not** fire an alert.

### Phase P8 — Quarterly + monthly polish (2 days)

| Item | Files | DB | Tests |
|---|---|---|---|
| P8-1 | Event-driven `event_fundamentals_pull` (D16) — Render cron at 04:30 ET reads `earnings_calendar` for tomorrow's reporters, refreshes their `ticker_metadata`. T+1 follow-up pulls revised fundamentals. | new `app/jobs/event_fundamentals.py` | writes `ticker_metadata` | dry-run on next-week sample |
| P8-2 | Monthly `etf_holdings_refresh` for ETFs held/watched (D6 from BACKEND_DATA_GENERATION_PLAN.md) | new `app/jobs/etf_holdings.py` | new `etf_holdings` table | top-10 holdings coverage |
| P8-3 | `weekly_universe_audit` — reconcile `ticker_universe.is_active` against authoritative S&P 500 CSV; mark adds/removes and emit admin notification. | `app/jobs/universe_audit.py` | updates `ticker_universe` | diff fixture |

---

## 5. Cost & risk

### 5.1 LLM cost ceiling

The biggest unknown is per-user article personalisation (P7-1). The existing news pipeline LLM cost is bounded by ticker count × articles/ticker × enrichment-cost-per-article. Personalisation multiplies that by ~user count. **Mitigation:** only personalise articles for tickers the user *actually holds* (`positions` join) and cap per-user to top-N articles per day. Estimate: ~50 articles/day/user × $0.001/article = $0.05/user/day; at 1k users = $50/day = $1.5k/mo. Budget gate required.

### 5.2 Render plan

Current backend is `plan: starter` (1 dyno). The cron-job approach adds 6+ separate Render cron services — each is billed. **Mitigation:** consolidate into a single cron service that takes a `job_id` argument and Render cron schedules them; OR upgrade to `standard` and run all jobs in-process with `SCHEDULER_TIER=cron` enabled.

### 5.3 Polygon / Finnhub rate limits

P5-3 (earnings calendar) and P6-4 (IV-rank) add new API endpoints. **Mitigation:** existing global gates (Polygon 20s, Finnhub 0.12s) already serialize; new jobs inherit them. Add `429` retries with exponential backoff identical to news pipeline.

### 5.4 Data correctness during transition

Until P4 lands, `portfolio_risk_snapshots` will be empty for most users; iOS must keep rendering its existing client-side composite as a fallback. **Mitigation:** every new field in the route envelope is **optional**; iOS treats missing/`null` as "fall back to legacy path", not "error".

### 5.5 Scheduler stampede

If multiple cron services boot the same image and call `start_scheduler()`, jobs could double-fire. **Mitigation:** `SCHEDULER_TIER=none` on every non-web service; cron services run a single `python -m app.jobs.run` and exit without calling `start_scheduler()`.

---

## 6. What this plan deliberately does NOT do

- It does not redo the per-screen mock-to-live audit (already in `docs/MOCK_TO_LIVE_AUDIT.md`, valid).
- It does not redo the endpoint contract design (already in `docs/UI_DATA_CONTRACT_MATRIX.md`, valid for endpoints it covered).
- It does not implement payments / StoreKit — that's P2-4 in the existing plan, untouched here.
- It does not migrate iOS views off `clavix*` tokens onto the new `cx*` `DesignSystem/` primitives — that's a separate Hi-Fi parity cycle.
- It does not retire legacy tables (`news_items`, `ticker_news_cache`, `risk_scores`) — that's P2-7 in the existing plan.

---

## 7. Sequencing summary

```
P3 (3–4d)  ── scheduler foundation, macro+sector come alive, job_runs table
P4 (3d)    ── daily composite for universe + per-user portfolio rollup
P5 (4d)    ── /today aggregator + sector heat + earnings calendar
P6 (5d)    ── methodology depth: peers, medians, IV-rank, monthly regressions
P7 (3d)    ── personalisation, refresh limits, outside-universe, alert hysteresis
P8 (2d)    ── earnings-event fundamentals, ETF holdings, universe audit
──────────────────
Total: ~20 working days, single full-time engineer, sequential
```

P3 and P4 can overlap (different files). P6 depends on P4 (needs daily snapshots to compute deltas). P7's personalisation can begin in parallel with P6.

Critical-path items: **P3-1 → P3-4 → P3-5 → P4-1 → P4-2 → P5-2** (this 6-step chain gets `today-a` to render real numbers).

---

*End of plan. Implementation tracker lives in commits + `docs/HANDOFF.md`.*
