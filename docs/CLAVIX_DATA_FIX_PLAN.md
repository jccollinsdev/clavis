# Clavix Data Fix Plan

Concise execution plan derived from `CLAVIX_DATA_TRUTH_AUDIT.md` (2026-05-30).
**Readiness 42/100. Go/No-Go: NO-GO** for the risk-grade as a real-data signal until P0+P1 land.

One-line problem statement: *the system is surface-complete but the grade can't discriminate (98.8% BBB/BB), 3 of 5 dimensions are heuristic constants, the Polygon price layer is dead during recompute, digests have stopped, and APNs is unconfigured.*

---

## The next 10 backend/data tasks (in order)

| # | Pri | Task | File(s) | Done-when |
|---|---|---|---|---|
| 1 | P0 | Confirm `SCHEDULER_TIER` on VPS; set uvicorn to `cron` **or** re-register per-user digests in the intraday branch | `app/pipeline/scheduler.py:5586–5639` | `scheduler_jobs.next_run_at` is in the future for both enabled users after restart |
| 2 | P0 | Configure APNs in prod (load key/cert env) | deploy env / `app/main.py:150–160` | `/health` returns `"apns":"configured"` |
| 3 | P0 | Make Polygon auth-block **ticker-scoped**, not global | `app/services/polygon.py:33–104` | one unentitled symbol no longer forces synthetic-403 on all calls |
| 4 | P0 | Remove/replace unentitled factors `I:TNX`, `I:VIX` with entitled symbols | `app/services/macro_regression.py:10–16` | direct probe of all `FACTOR_TICKERS` returns 200 |
| 5 | P1 | Flag `sector_exposure` & `volatility` as `limited_data` when real inputs absent | `app/pipeline/risk_scorer.py` (`_score_sector_exposure`, `_score_volatility`) | disclosure matches reality (no silent degradation) |
| 6 | P1 | Use computed sector beta/momentum/breadth in the sector scorer | `risk_scorer.py:_score_sector_exposure` (~597) | `sector_exposure` σ rises materially above 2.0 |
| 7 | P1 | Verify realized-vol/beta populate after #3–#4; re-run universe recompute (throttled) | `composite_recompute.py` | `beta_to_spy`/`realized_vol_30d` non-null > 480/504 |
| 8 | P1 | Populate `fcf_margin`/`interest_coverage` or retire those FH rules | `ticker_cache_service.py:_build_financial_health_inputs`; `event_fundamentals_pull` | inputs non-null > 480/504, **or** rules removed + methodology updated |
| 9 | P2 | Re-weight/re-scale composite so grades span ≥4 buckets | `analysis_utils.py:calculate_weighted_score` (~512) | grade distribution spans ≥4 grades; composite σ > ~8 |
| 10 | P2 | Decide + implement news coverage policy for the 64% zero-coverage tickers | `scheduler.py:_run_active_ticker_news_refresh` (5411) | either universe sweep added, or unfollowed-ticker news labeled honestly |

---

## Safety notes for execution

- **Do NOT run an unthrottled full-universe LLM backfill.** At p50 ≈ 11 s/call it is latency-bound (~3h for the universe) and there is a hard MiniMax usage cap (`429 usage limit exceeded (2056)` was hit once). Keep the 200-rows / 2h bulk-enrich shape.
- **Throttle universe Polygon recompute.** Once auth is fixed, the real 20 s/call gate means a full bar-fetch run is ~2.8h — run off-peak, batched, and watch `job_runs.duration`.
- News pipeline and LLM layer are healthy — **do not refactor them.** Idempotency (event-hash + upsert) and the re-enrich loop work; leave them alone.
- All P0 tasks are config/scoping fixes, not data rewrites — low blast radius. P1–P2 change scoring output, so snapshot a backup of `ticker_risk_snapshots` before re-running the universe recompute.

---

## Verification (re-run after fixes)

```sql
-- (a) grade now discriminates
WITH l AS (SELECT DISTINCT ON (ticker) ticker, composite_score, grade
  FROM ticker_risk_snapshots ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
SELECT grade, count(*), round(stddev_pop(composite_score),2) FROM l GROUP BY grade ORDER BY 1;

-- (b) dimensions are real
WITH l AS (SELECT DISTINCT ON (ticker) ticker, dimension_inputs, factor_breakdown
  FROM ticker_risk_snapshots ORDER BY ticker, snapshot_date DESC, analysis_as_of DESC)
SELECT
  count(*) FILTER (WHERE (dimension_inputs->'volatility'->>'beta_to_spy') IS NOT NULL) vol_beta,
  count(*) FILTER (WHERE (dimension_inputs->'sector_exposure'->>'sector_beta') IS NOT NULL) sec_beta,
  count(*) FILTER (WHERE (factor_breakdown->'macro_regression'->>'limited_data')='false') macro_real
FROM l;

-- (c) digests advancing
SELECT user_id, last_run_at, next_run_at, last_run_status FROM scheduler_jobs WHERE notifications_enabled;
```

```bash
curl -s https://clavis.andoverdigital.com/health     # expect apns:configured
# VPS (read-only): docker compose exec <svc> printenv SCHEDULER_TIER
```

**Ship gate:** (a) shows ≥4 grades with σ>8, (b) shows >480/504 real for each dim, (c) shows future `next_run_at`, and `/health` shows `apns:configured`.
