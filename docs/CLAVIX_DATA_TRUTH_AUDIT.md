# Clavix Backend / Database Data-Truth Audit

**Date:** 2026-05-30 (Sat)
**Auditor scope:** Backend, database, and data-truth only (NOT iOS UI).
**Question answered:** *Is the Clavix backend/database actually generating, enriching, refreshing, storing, and serving correct production-quality data for every ticker and every user-facing data surface?*
**Method:** Direct SQL against Supabase prod (`uwvwulhkxtzabykelvam`), source-code reading, filesystem LLM-artifact analysis (`BACKFILL/`), live production HTTP probes (`https://clavis.andoverdigital.com`). Every claim below carries evidence.

---

## 1. Executive Summary

Clavix is **surface-complete but hollow underneath.** Every one of the 504 S&P tickers has a non-null composite score and a bond-style grade, refreshed daily on weekdays, and the API serves those values correctly and fast. That is the good half.

The bad half: **three of the five scoring dimensions are effectively heuristic constants, not measurements**, and the price-data layer that is supposed to feed them is non-functional during the universe recompute. The result is a risk grade that **cannot discriminate between stocks** — 98.8% of the entire S&P 500 universe is graded either BBB or BB. On top of that, **daily digests have silently stopped firing for both real users**, and **APNs is not configured in production**, so even a generated digest cannot be delivered.

The news pipeline is the genuine bright spot: for the ~122 actively-followed tickers it is fresh, deduplicated, and 97% LLM-enriched within the trailing 7 days, with a reliable idempotent re-enrichment loop and a measured LLM error rate of 0.5%.

**Data readiness score: 42 / 100.** The infrastructure is real and the news layer is production-grade; the core differentiator (the multi-dimension risk grade) is not yet trustworthy, and two user-facing delivery surfaces (digests, push) are broken.

**Go / No-Go: NO-GO for presenting the composite grade as a differentiated, real-data risk signal.** Conditional GO for news/sentiment surfaces on actively-followed tickers once digest delivery + APNs are fixed.

---

## 2. Data Readiness Score — breakdown

| Area | Weight | Score | Notes |
|---|---:|---:|---|
| Snapshot completeness & freshness | 15 | 14 | 504/504 present, ≤2d old, no nulls in composite/grade |
| Composite math correctness | 15 | 9 | Math is correct; **inputs** are mostly fallback → near-constant output |
| Dimension realness (5 dims) | 25 | 6 | Only financial-health (partial) + news (35% of universe) carry real signal |
| News enrichment quality | 15 | 13 | Excellent for active tickers; idempotent; 97% scored in 7d |
| LLM/MiniMax reliability | 10 | 9 | 0.5% error rate over 5,021 calls; retries; idempotent |
| Job cadence / scheduler | 10 | 5 | Cron daily jobs healthy; **in-process digest scheduler broken** |
| Delivery surfaces (digest + push) | 10 | 1 | Digests stopped for all users; APNs missing in prod |
| Price-history surface | 5 | 2 | `prices` table maintained for only ~10 tickers |
| Serving correctness | 5 | 5 | Reads live columns, fast, auth-gated |
| **Total** | **100** | **42** | |

---

## 3. 504-Ticker Completeness Report (Part B)

**Surface completeness: PASS.** Latest snapshot per ticker:

```sql
WITH latest AS (SELECT DISTINCT ON (ticker) ticker, composite_score, grade,
  limited_data_dimensions FROM ticker_risk_snapshots
  ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
SELECT count(*) ... ;
-- 504 tickers, composite_score non-null 504/504, grade non-null 504/504,
-- 0 rows with empty limited_data_dimensions, avg 1.65 dims flagged limited.
```

- **504 / 504** have a non-null `composite_score` and `grade`.
- Freshness: `max(analysis_as_of) = 2026-05-29 10:19 UTC`; **503/504 tickers refreshed within 2 days**. (Today is Sat 05-30; weekday-only recompute correctly has not run.)
- **No price/snapshot nulls** in the served columns.

**But "complete" ≠ "real."** Disclosed limited-data flags per latest snapshot:

| Dimension | Tickers flagged `limited_data` | % |
|---|---:|---:|
| macro_exposure | **504** | 100% |
| news_sentiment | **328** | 65% |
| sector_exposure | 0 | 0% |
| volatility | 0 | 0% |
| financial_health | 0 | 0% |

The "0%" rows are **silent degradation** (see Part D): the underlying inputs are hardcoded or absent, but the snapshot does not flag it.

### Worst-25 by data realness
All cap at **2 disclosed** limited dims (the ceiling, because sector/vol/fin are never flagged) and **0 usable 7-day news articles**:

```
SNDK(B 45.8) CCL(B 46.4) COIN(B 47.0) CVNA(B 47.8) SATS(B 48.8)
RCL(BB 50.0) KKR(BB 50.2) URI(BB 50.4) HIMS(BB 51.0) GM(BB 51.4)
INTC(BB 51.8) DASH(BB 52.0) IT(BB 52.6) MSCI(BB 52.8) VRT(BB 53.2)
LRCX(BB 54.0) MS(BB 54.2) EL(BB 54.4) BX(BB 54.8) IVZ(BB 55.0)
EXPE(BB 55.0) HON(BB 55.0) F(BB 55.2) IBKR(BB 55.2) IRM(BB 55.4)
```

These tickers' composite is driven almost entirely by metadata heuristics (sector class, market cap, beta bucket, D/E) — no real news, no real macro regression, no realized volatility.

---

## 4. Composite Math Correctness (Part C)

**The arithmetic is correct; the output is not informative.**

- `calculate_weighted_score` (analysis_utils.py:512) takes an equal-weight mean of the 5 V2 dimension scores; `None` dims are excluded and the remainder rescaled. Verified correct.
- `score_to_grade` (analysis_utils.py:486) thresholds are standard (≥90 AAA … <10 F). Verified correct.

**The problem is dispersion.** Across all 504 latest snapshots:

| Dimension | min | max | mean | **σ** | distinct values |
|---|---:|---:|---:|---:|---:|
| composite | 45.8 | 71.2 | 61.2 | **4.18** | 97 |
| financial_health | 23 | 76 | 61.7 | 8.94 | 33 |
| news_sentiment | 19 | 76 | 46.4 | 9.58 | 53 |
| macro_exposure | 41 | 78 | 66.2 | 10.48 | **5** |
| sector_exposure | 61 | 70 | 65.2 | **2.02** | **5** |
| volatility | 26 | 76 | 66.7 | 7.74 | 41 |

- `sector_exposure` and `macro_exposure` each take **only 5 distinct values** — they are categorical constants, not measurements. Together they are **40% of the equal-weight composite**, mechanically dragging every ticker toward ~65.
- Net composite σ is **4.18 over a 25-point range**. The grade collapses:

| Grade | Count | % | composite range |
|---|---:|---:|---|
| A | 1 | 0.2% | 71.2 |
| BBB | 324 | 64.3% | 60.0–69.6 |
| BB | 174 | 34.5% | 50.0–59.8 |
| B | 5 | 1.0% | 45.8–48.8 |

**98.8% of the S&P 500 universe is BBB or BB.** No AAA, AA, A (×1), CCC, CC, C, D, or F. A 10-grade scale collapsed to effectively two. The grade carries almost no discriminating information for the user.

---

## 5. Dimension-Level Correctness (Part D)

Direct inspection of `dimension_inputs` / `factor_breakdown` across all 504 latest snapshots:

| Dimension | Real input present | Verdict |
|---|---|---|
| **financial_health** | `debt_to_equity` 503/504; **`fcf_margin` 0/504; `interest_coverage` 0/504** | Partial. D/E rules fire; two documented rule inputs are null for the entire universe, yet **never flagged limited**. σ=8.9 → some real signal. |
| **news_sentiment** | Real for ~35% (the actively-followed set); fallback for 65% | Honest (flagged when limited). σ=9.6 from the real 35%. |
| **macro_exposure** | **0/504 real regression** (`limited_data=true` everywhere; `trading_days_used=0`; empty `coefficients`) | Dead. 100% fallback (`base 65 ± beta-bucket`). At least correctly flagged. |
| **sector_exposure** | **`sector_beta` 0/504** | Hardcoded heuristic (`base 65 ± defensive/cyclical ± market_cap`). Real sector beta/momentum/breadth are *computed by the input builder but ignored by the scorer*. Never flagged. |
| **volatility** | **`beta_to_spy` 0/504; `realized_vol_30d` 5/504** | Runs on a metadata `volatility_proxy` only. No realized vol, no SPY beta for 99% of names. Never flagged. σ=7.7 from the proxy. |

The only 5 tickers with real realized volatility are **CTVA, HIMS, JPM, MMM, SNA** — a near-random handful that happened to fetch Polygon bars before the auth cooldown kicked in (HIMS rv30 = 0.98, plausibly high for a volatile name).

**Conclusion:** 3 of 5 dimensions (macro, sector, volatility) are heuristic constants for ~99–100% of the universe. Of those, only macro is honestly disclosed as limited. Sector and volatility are **silently degraded** — the product presents full confidence on dimensions that are running on hardcoded labels.

---

## 6. Root Cause — the Polygon price layer is dead during recompute

This single defect explains macro=100%-limited, sector_beta=0/504, and realized_vol=5/504 simultaneously.

**Evidence — the recompute is impossibly fast for a job that fetches bars:**

```sql
-- daily_composite_recompute_universe
-- 2026-05-29: 503 items in 19.5 min  (~2.3 s/ticker)
-- 2026-05-28: 503 items in 18.8 min
-- 2026-05-27: 503 items in 21.1 min
```

Each ticker is supposed to call `fetch_aggs(ticker, days=400)` + 5 factor series + `run_macro_regression`. With Polygon's global gate `_MIN_CALL_SPACING = 20.0 s` (polygon.py:15), 503 tickers × 20 s ≈ **2.8 hours minimum** — yet the job finishes in **~19 minutes**.

**Mechanism** (polygon.py:96–104, 33–44):
1. `run_macro_regression` requests factor series including `I:TNX` and `I:VIX`.
2. Direct API probe (this audit): **`I:TNX` and `I:VIX` return `NOT_AUTHORIZED`** ("not entitled to this data") on the current Polygon plan. `SPY`, `UUP`, `USO`, and equities return data.
3. The first 401/403 calls `_block_polygon_auth()`, setting a **300-second cooldown** (`_AUTH_FAILURE_COOLDOWN`).
4. During cooldown, `polygon_get()` checks `_polygon_auth_temporarily_blocked()` **before** `_rate_limit_polygon()` and returns a synthetic 403 **instantly** — skipping both the network call and the 20 s sleep.
5. So every subsequent `fetch_aggs` returns `[]` in microseconds → empty bars → regression returns `limited_data` immediately, volatility has no series, sector beta cannot compute. The 19-minute runtime is just DB reads + heuristic scoring.

**Corroborating:** the standalone `daily_macro_snapshot` job (1 row, current *levels* via single snapshot calls) succeeds — but stores **mislabeled proxy prices**: `ust10y_level=85.74` (a 10Y yield should be ~4–5%; this is a bond/proxy price), `dxy_level=27.7` (DXY ≈ 100; this is the UUP ETF price), `wti_level≈130–140` (USO proxy). All macro/sector regime rows are `data_status='price_only'` with null `sector_beta`/`narrative`.

---

## 7. News Enrichment Report (Part E)

**This is the strongest part of the system.**

`shared_ticker_events`: **29,357 rows, 506 distinct tickers.** Fresh: `max(published_at)=2026-05-30 07:50 UTC`, `max(created_at)=2026-05-30 11:48 UTC` — **ingesting today.** 229 events in last 24h.

**Last-7-day window (what is actually served + re-enriched):**

| Metric | Value |
|---|---|
| Events (7d) | 2,275 |
| Null sentiment (7d) | 69 (**3.0%**) |
| Extraction success | 1,629 (71.6%) |
| Extraction failed | 617 (27.1%) |
| Has TLDR | 1,376 (84% of extracted-ok) |

- **No duplicate `(ticker, event_hash)` pairs** anywhere — idempotency via MD5 event-hash + upsert `on_conflict="ticker,event_hash"` works.
- Transient-failure recovery is real: `_run_bulk_sentiment_enrichment` (scheduler.py:5453) selects up to 200 null-sentiment rows from the last 7d every 2h with `skip_existing=False`, re-running the LLM on null fields while preserving non-null ones.

**The one structural gap:** news is fetched only for **active** tickers (any user's positions or watchlist — `_run_active_ticker_news_refresh`, scheduler.py:5411). Per-ticker usable-news coverage over the full 504-universe:

```
universe=504  zero_usable=323 (64%)  1–2=59  ≥3=122 (24%)  avg=3.13
```

So **64% of the universe has zero usable news in 7 days** (by design), which is exactly why `news_sentiment` is `limited_data` on 328/504 tickers. This is acceptable for a V1 that only deeply analyzes followed names — but the composite for unfollowed tickers is correspondingly thin.

The 25.1% all-time null-sentiment figure is a red herring: it is dominated by old events outside the 7d re-enrich window (headline-only / failed-extraction rows that will never be retried). Served data uses the 7d window where null rate is 3%.

---

## 8. MiniMax / LLM Reliability (Part F)

Analyzed **5,021 logged LLM calls** across 362 `BACKFILL/*/llm_calls/index.jsonl` artifacts (2026-05-08 → 2026-05-28):

| Metric | Value |
|---|---|
| Total calls | 5,021 |
| Errors | 24 (**0.5%**) |
| → 529 overloaded | 9 (retried) |
| → 429 "usage limit exceeded (2056)" | 15 (one clustered burst, consecutive request IDs) |
| Empty responses | 16 (0.3%) |
| Duration p50 / p90 / p99 / max | **11.4 s / 26.1 s / 40.2 s / 114.7 s** |
| Model | `MiniMax-M2.7` (100%) |

**Reliability mechanics (minimax.py):**
- 5 attempts, exponential backoff 0.8→8.0 s, but **only** on retryable markers (`high traffic`, `rate limit`, `502/503/529`, `server disconnected`).
- Auth failures raise immediately (`MiniMaxAuthError`).
- Global process-wide throttle floor of **1.05 s** between calls (`_wait_for_minimax_slot`).
- Timeout 120 s, default `max_tokens` 1000.

**Two findings:**
1. **Quota cap is real and was hit.** The 15 `429 usage limit exceeded (2056)` errors are a hard account-usage cap, clustered in one run. The retry filter checks for `"rate limit"` (space) but the payload says `rate_limit_error` (underscore) + `usage limit exceeded`, so these are **not** retried (correct — retrying a quota cap won't help, but capacity planning must respect this ceiling).
2. **Latency, not error rate, is the capacity constraint.** At p50 ≈ 11 s/call and a 1 s throttle floor, a full-universe LLM backfill is latency-bound. A 504-ticker × 2-call enrichment ≈ 1,008 calls × ~11 s ≈ **3+ hours single-threaded**. The 2h bulk-enrich cap of 200 rows/run is the right shape to stay under quota.

**Verdict:** LLM layer is reliable and idempotent. Do not run an unthrottled full-universe LLM backfill — it will hit the 2056 usage cap.

---

## 9. Cadence Truth Table (Part G)

Verified against `job_runs` (actual executions, not just schedules). Server time at audit: **2026-05-30 12:34 UTC (Sat)**.

| Job | Mechanism | Intended cadence | Actually ran | Status | Notes |
|---|---|---|---|---|---|
| `daily_composite_recompute_universe` | external cron (`app.jobs.run`) | weekday daily ~10:00 UTC | 05-27, 05-28, 05-29 | completed, 503/run, 0 fail | Healthy *since 05-27*; nothing earlier in 21d window |
| `daily_macro_snapshot` | cron | weekday ~09:00 UTC | 05-26→05-29 | completed | stores mislabeled proxy levels (§6) |
| `daily_sector_snapshot` | cron | weekday ~09:15 UTC | 05-26→05-29 | completed, 12/run | `sector_beta` null |
| `daily_earnings_calendar_refresh` | cron | weekday | 05-27→05-29 | completed | |
| `event_fundamentals_pull` | cron | weekday | 05-27→05-29 | completed, 17 proc | fundamentals still sparse (fcf/icov null) |
| `daily_portfolio_rollup_per_user` | cron | weekday | 05-27→05-29 (1 fail 05-28) | mostly completed | |
| `weekly_peer_groups_recompute` | cron | weekly Sat | **05-30** ✓ | completed, 5050 | ran today |
| `weekly_sector_medians_recompute` | cron | weekly Sat | **05-30** ✓ | completed, 266 | ran today |
| `active_ticker_news_refresh` | **in-process APScheduler** (IntervalTrigger 4h) | every 4h | live (news created 05-30 11:48) | — | proves APScheduler is running |
| `bulk_sentiment_enrichment` | in-process APScheduler (2h) | every 2h | live (3% null in 7d) | — | |
| **per-user digest** | **in-process APScheduler CronTrigger (ET)** | per-user daily | **STOPPED** | frozen | see Part H |

**Reads:** The daily data jobs are **external cron** (UTC `:02`-second offsets are the cron signature; `app.jobs.run` is the entrypoint). They are healthy on weekdays and correctly idle on weekend. The in-process APScheduler is running (news refreshed today) **but** is in a tier that drops per-user digests.

---

## 10. Daily Digest Reliability (Part H) — **P0**

**Both real users' digests have silently stopped, and `next_run_at` is frozen in the past.**

```sql
SELECT user_id, digest_time, last_run_at, next_run_at, last_run_status FROM scheduler_jobs;
-- 90b7281c (07:05 ET): last_run 05-28 11:05, next_run 2026-05-29 11:05 (PAST), completed
-- 7ff5a6c5 (07:00 ET): last_run 05-26 11:00, next_run 2026-05-27 11:00 (PAST, 3d stale), completed
-- 00000000-1   : notifications disabled (test user)
```

Actual digest deliveries (ET):
```
90b7281c: 05-25 Mon, 05-26 Tue, 05-27 Wed, 05-28 Thu — then NOTHING (missing 05-29 Fri)
7ff5a6c5: 05-25 Mon, 05-26 Tue — then NOTHING
```

**Root cause (scheduler.py:5560–5639):** `start_scheduler()` registers the interval news jobs (5599–5600) **before** branching on `_scheduler_tier()`. In the `intraday` tier it then **removes every per-user digest job (5605–5606) and returns early (5608–5609) without re-adding them.** Only the `cron` tier re-registers per-user digests.

This reconciles all evidence: **the uvicorn/APScheduler process is running in `SCHEDULER_TIER=intraday`** → interval news jobs keep firing (fresh news today) → per-user digest CronTriggers were purged on the last restart → `next_run_at` is frozen at the last value persisted to `scheduler_jobs` and never advances. The daily data jobs are unaffected because they run via external cron.

**Digest content itself is fine** when it runs: per-user, timezone-aware ET CronTrigger from each user's `digest_time` pref, `weekday_only` + `quiet_hours` honored, `misfire_grace_time=3600`, run state persisted. 86/97 historical digests have `structured_sections`. The defect is purely that the jobs are no longer scheduled.

**Compounding P0 — push delivery is impossible:** `/health` reports **`"apns":"missing"`** in production. Even a generated digest cannot be pushed to a device. APNs is unconfigured.

---

## 11. API Serving Correctness (Part I)

Live probes against `https://clavis.andoverdigital.com`:

```
/health        → HTTP 200 in 73–119 ms   {"status":"ok","apns":"missing",
                                            "snaptrade":"configured","minimax":"configured",
                                            "supabase":"configured"}
/tickers/AAPL  → HTTP 401 in 52 ms        (auth gate works; only /health is public)
```

- Production is **up and fast** (sub-130 ms health, sub-60 ms auth rejection).
- The ticker detail endpoint (`tickers.py:165` `get_ticker_detail`) is JWT-gated via middleware (`request.state.user_id`); could not be probed end-to-end without a user token.
- **Serving reads live columns, not dead ones.** `get_ticker_detail_bundle` (ticker_cache_service.py:3469) selects the latest snapshot via `_canonical_snapshot_sort_key`, which orders by `analysis_as_of, updated_at, created_at, method_priority` + schema-completeness. It does **not** reference `generated_at`, `data_status`, `verification_status`, or `is_product_visible` (the dead columns). So the API faithfully serves the same composite/grade/dimension values audited above — there is no divergent live-compute path that could mask the §4/§5 problems. The API correctly serves a compressed, heuristic grade.

**Dead columns confirmed (all 504 latest rows):** `generated_at`, `stale_after`, `data_status`, `verification_status`, `is_product_visible` are NULL/false. The real timestamp is `analysis_as_of` (504/504 set). These columns are inert and safe (not used for gating), but should be dropped or wired up.

---

## 12. Price-history surface (Part A addendum)

```sql
SELECT max(recorded_at), count(DISTINCT ticker) FILTER (WHERE recorded_at > now()-'3 days') FROM prices;
-- max=2026-05-28 19:33 UTC ; only 10 distinct tickers priced in last 3 days
```

The `prices` table is maintained for **only ~10 tickers** (the held positions, via `update_position_prices`). There is no universe-wide daily price ingestion. The composite does not depend on this table (it uses Polygon `fetch_aggs` directly — which is itself broken, §6), but any price-history/sparkline surface in the app has data for only ~10 names.

`etf_holdings` and `refresh_attempts` tables are empty; `asset_safety_profiles` is 100% stale (≤2026-05-08, 22 days). `gnews_wrapper_resolution` has RLS disabled.

---

## 13. Prioritized Fix List

### P0 — fix before any launch / re-enable of digests
1. **Digest scheduler dropped.** Confirm `SCHEDULER_TIER` on the VPS. If `intraday`, switch the uvicorn process to `cron` (or add per-user digest re-registration to the intraday branch). Verify `scheduler_jobs.next_run_at` advances to a future time after restart.
2. **APNs unconfigured in prod** (`/health → apns:missing`). Load the APNs key/cert so digests can actually be delivered.
3. **Polygon price layer dead during recompute** (§6). Either (a) remove `I:TNX`/`I:VIX` from `FACTOR_TICKERS` (or replace with entitled proxies, e.g. `TLT`/`^VIX` alternatives the plan allows), and/or (b) make `_block_polygon_auth` ticker-scoped instead of global so one unentitled symbol does not poison all 503 equity fetches.

### P1 — core data truth (the grade must mean something)
4. **Stop silent degradation.** Flag `sector_exposure` and `volatility` as `limited_data` whenever `sector_beta`/`beta_to_spy`/`realized_vol_30d` are absent — so disclosure matches reality.
5. **Wire the real sector inputs into the scorer.** `_build_sector_exposure_inputs` already computes sector beta/momentum/breadth; `_score_sector_exposure` ignores them in favor of hardcoded constants. Use the computed values.
6. **Fix realized-volatility coverage.** Once §3 is fixed, `realized_vol_30d`/`beta_to_spy` should populate for the universe; re-verify >480/504 non-null.
7. **Populate `fcf_margin` / `interest_coverage`** (0/504 today) from the fundamentals source, or remove those rules and re-document the financial-health methodology.

### P2 — discrimination & coverage
8. **Re-scale / re-weight the composite** so it disperses across the grade band. With sector/macro near-constant, equal weighting guarantees BBB/BB clustering. Down-weight non-informative dims or widen the informative ones until grade distribution spans ≥4 grades.
9. **Decide news coverage policy.** Either accept "active tickers only" (and label unfollowed tickers' news dimension honestly in the UI), or add a low-frequency universe-wide news sweep.

### P3 — hygiene
10. Drop or wire up the dead columns (`generated_at`, `data_status`, `verification_status`, `is_product_visible`, `stale_after`). Enable RLS on `gnews_wrapper_resolution`. Backfill or retire `asset_safety_profiles` (22d stale), `etf_holdings` (empty).

---

## 14. Direct Answers — Go / No-Go

1. **Is every ticker's data real?** No. 504/504 are *present*, but 3/5 dimensions are heuristic constants for ~99% of tickers.
2. **Is the composite math correct?** Yes — the arithmetic is correct; the inputs are not informative.
3. **Does the grade discriminate?** No. 98.8% of the universe is BBB or BB.
4. **Is macro real?** No. 0/504 real regressions; 100% fallback (correctly disclosed).
5. **Is sector/volatility real?** No, and **not disclosed** — silent degradation (sector_beta 0/504, beta_to_spy 0/504, realized_vol 5/504).
6. **Is news enrichment real?** Yes, for the ~24% actively-followed universe — fresh, deduped, 97% scored in 7d, idempotent. No for the 64% with zero usable news (by design).
7. **Is the LLM layer reliable?** Yes. 0.5% error over 5,021 calls; idempotent; respects quota. Latency (p50 11 s) is the capacity limit.
8. **Do daily jobs run on cadence?** Yes for external-cron data jobs (weekday daily, healthy since 05-27). No for in-process digests.
9. **Are digests reliable?** No — **stopped for both users** (P0), and undeliverable anyway (APNs missing).
10. **Does the API serve correctly?** Yes — fast, auth-gated, reads live columns. It correctly serves data that is itself not yet trustworthy.

**Overall: NO-GO** for the risk-grade as a real-data differentiator until P0+P1 land. The news/sentiment surface for followed tickers is launch-quality once digest delivery + APNs are fixed.

---

## 15. Re-run commands (verify after fixes)

```sql
-- grade discrimination should span ≥4 grades, composite σ should rise > ~8
WITH l AS (SELECT DISTINCT ON (ticker) ticker, composite_score, grade
  FROM ticker_risk_snapshots ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
SELECT grade, count(*) FROM l GROUP BY grade ORDER BY 1;

-- dimension realness should approach 504 for sector/vol/macro
WITH l AS (SELECT DISTINCT ON (ticker) ticker, dimension_inputs, factor_breakdown
  FROM ticker_risk_snapshots ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
SELECT
  count(*) FILTER (WHERE (dimension_inputs->'volatility'->>'beta_to_spy') IS NOT NULL)  vol_beta,
  count(*) FILTER (WHERE (dimension_inputs->'sector_exposure'->>'sector_beta') IS NOT NULL) sec_beta,
  count(*) FILTER (WHERE (factor_breakdown->'macro_regression'->>'limited_data')='false') macro_real
FROM l;

-- digests must advance
SELECT user_id, last_run_at, next_run_at FROM scheduler_jobs WHERE notifications_enabled;
```

```bash
# prod should report apns:configured after P0-2
curl -s https://clavis.andoverdigital.com/health

# confirm scheduler tier on VPS (read-only)
#   docker compose exec <svc> printenv SCHEDULER_TIER PAUSE_SYSTEM_SCHEDULER
```
