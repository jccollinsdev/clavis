# Codex Run Audit — 2026-05-25 v2

## Status
- ✅ P3-9 shipped
- ✅ P7-1 shipped
- ✅ P6-5 shipped
- ✅ P6-4 shipped
- ✅ P8-2 shipped

## Per-item Summary

### P3-9 — deploy-time 14-day score-history backfill
- Added one-shot manual backfill job in [backend/app/jobs/backfill_14d.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/backfill_14d.py).
- Threaded `target_date` through [backend/app/jobs/composite_recompute.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/composite_recompute.py) and the snapshot refresh path in [backend/app/services/ticker_cache_service.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/ticker_cache_service.py) so backfilled rows use real as-of data instead of fabricated history.
- Registered `backfill_14d` as a manual job in [backend/app/jobs/run.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/run.py).
- Added coverage in [backend/tests/test_p3_9_backfill.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p3_9_backfill.py).

### P7-1 — two-layer per-user article personalisation
- Added structural + optional LLM narrative generation in [backend/app/services/personalisation.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/personalisation.py).
- Persisted `sections.personalised_articles` during digest compilation in [backend/app/pipeline/portfolio_compiler.py](/Users/sansarkarki/Documents/Clavis/backend/app/pipeline/portfolio_compiler.py) and threaded it through digest/scheduler callers in [backend/app/routes/digest.py](/Users/sansarkarki/Documents/Clavis/backend/app/routes/digest.py) and [backend/app/pipeline/scheduler.py](/Users/sansarkarki/Documents/Clavis/backend/app/pipeline/scheduler.py).
- Reattached latest personalisation to article payloads in [backend/app/routes/methodology.py](/Users/sansarkarki/Documents/Clavis/backend/app/routes/methodology.py) and [backend/app/services/ticker_cache_service.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/ticker_cache_service.py).
- Extended iOS decoding/rendering in [ios/Clavis/Models/Methodology.swift](/Users/sansarkarki/Documents/Clavis/ios/Clavis/Models/Methodology.swift) and [ios/Clavis/Views/Tickers/ArticleDetailSheet.swift](/Users/sansarkarki/Documents/Clavis/ios/Clavis/Views/Tickers/ArticleDetailSheet.swift).
- Added tests in [backend/tests/test_p7_1_personalisation.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p7_1_personalisation.py).

### P6-5 — monthly macro regression refresh + factor exposures
- Added monthly regression job in [backend/app/jobs/macro_regression.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/macro_regression.py).
- Registered the job in [backend/app/jobs/run.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/run.py) and scheduled it in [scripts/cron/clavix.crontab](/Users/sansarkarki/Documents/Clavis/scripts/cron/clavix.crontab).
- Exposed `factor_exposures` from [backend/app/routes/methodology.py](/Users/sansarkarki/Documents/Clavis/backend/app/routes/methodology.py).
- Added synthetic regression coverage in [backend/tests/test_p6_5_macro_regression.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p6_5_macro_regression.py).
- Added `numpy` to [backend/requirements.txt](/Users/sansarkarki/Documents/Clavis/backend/requirements.txt) because `numpy.linalg.lstsq` was required and not previously installed in the repo’s Python 3.11 environment.

### P6-4 — IV-rank + implied vol fallback
- Added Polygon options snapshot adapter in [backend/app/services/polygon_options.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/polygon_options.py).
- Extended volatility input generation in [backend/app/services/ticker_cache_service.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/ticker_cache_service.py) to store `implied_vol_30d`, `iv_rank`, and `iv_source`, with `estimated` fallback when options data is unavailable.
- Added percentile helper in [backend/app/pipeline/structural_scorer.py](/Users/sansarkarki/Documents/Clavis/backend/app/pipeline/structural_scorer.py).
- Updated methodology response mapping in [backend/app/routes/methodology.py](/Users/sansarkarki/Documents/Clavis/backend/app/routes/methodology.py).
- Added tests in [backend/tests/test_p6_4_polygon_options.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p6_4_polygon_options.py) and adjusted [backend/tests/test_p6_methodology_depth.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p6_methodology_depth.py) to the new `iv_source` contract.

### P8-2 — real issuer-API ETF holdings ingestion
- Replaced static-only writes in [backend/app/jobs/etf_holdings.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/etf_holdings.py) with issuer-backed fetchers:
  - SPY via official SSGA holdings workbook
  - QQQ via official Invesco holdings JSON, stored as `source="invictus"` per requested source label
  - VTI via official Vanguard holdings API
- Preserved explicit static-seed fallback with warning logging.
- Added tests in [backend/tests/test_p8_2_etf_holdings.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p8_2_etf_holdings.py).

## File-by-file Diff Summary
- [backend/app/jobs/backfill_14d.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/backfill_14d.py): new one-shot 14-day backfill loop.
- [backend/app/jobs/composite_recompute.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/composite_recompute.py): `target_date` support for day-specific recomputes.
- [backend/app/jobs/macro_regression.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/macro_regression.py): new monthly factor-beta refresh job.
- [backend/app/jobs/etf_holdings.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/etf_holdings.py): issuer-backed ETF holdings fetchers plus fallback path.
- [backend/app/jobs/run.py](/Users/sansarkarki/Documents/Clavis/backend/app/jobs/run.py): registered `backfill_14d` and `monthly_macro_regression_refresh`.
- [backend/app/pipeline/portfolio_compiler.py](/Users/sansarkarki/Documents/Clavis/backend/app/pipeline/portfolio_compiler.py): digest-time `personalised_articles` persistence.
- [backend/app/pipeline/scheduler.py](/Users/sansarkarki/Documents/Clavis/backend/app/pipeline/scheduler.py): passed event/user context into digest personalisation.
- [backend/app/pipeline/structural_scorer.py](/Users/sansarkarki/Documents/Clavis/backend/app/pipeline/structural_scorer.py): percentile-rank helper for IV ranking.
- [backend/app/routes/digest.py](/Users/sansarkarki/Documents/Clavis/backend/app/routes/digest.py): selected top event ids for digest personalisation.
- [backend/app/routes/methodology.py](/Users/sansarkarki/Documents/Clavis/backend/app/routes/methodology.py): article personalisation reattachment, `factor_exposures`, and updated volatility output.
- [backend/app/services/personalisation.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/personalisation.py): new structural + optional LLM personalisation service.
- [backend/app/services/polygon_options.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/polygon_options.py): new Polygon options snapshot parser.
- [backend/app/services/ticker_cache_service.py](/Users/sansarkarki/Documents/Clavis/backend/app/services/ticker_cache_service.py): as-of filtering for backfill dates, personalisation reattachment, implied vol + IV-rank capture.
- [backend/app/config.py](/Users/sansarkarki/Documents/Clavis/backend/app/config.py): personalisation env flags.
- [backend/requirements.txt](/Users/sansarkarki/Documents/Clavis/backend/requirements.txt): added `numpy`.
- [scripts/cron/clavix.crontab](/Users/sansarkarki/Documents/Clavis/scripts/cron/clavix.crontab): added monthly macro-regression cron entry.
- [ios/Clavis/Models/Methodology.swift](/Users/sansarkarki/Documents/Clavis/ios/Clavis/Models/Methodology.swift): decode personalised article fields.
- [ios/Clavis/Views/Tickers/ArticleDetailSheet.swift](/Users/sansarkarki/Documents/Clavis/ios/Clavis/Views/Tickers/ArticleDetailSheet.swift): render `★ PERSONALISED` structural line first, narrative second.
- New backend tests:
  - [backend/tests/test_p3_9_backfill.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p3_9_backfill.py)
  - [backend/tests/test_p7_1_personalisation.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p7_1_personalisation.py)
  - [backend/tests/test_p6_5_macro_regression.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p6_5_macro_regression.py)
  - [backend/tests/test_p6_4_polygon_options.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p6_4_polygon_options.py)
  - [backend/tests/test_p8_2_etf_holdings.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_p8_2_etf_holdings.py)

## Test Results
- Backend targeted verification:
  - P3-9: `7 passed` via `tests/test_p3_9_backfill.py tests/test_p4_jobs.py tests/test_jobs_runner.py`
  - P7-1: `9 passed` via `tests/test_p7_1_personalisation.py tests/test_portfolio_compiler_summary_length.py tests/test_digest_force_refresh.py`
  - P6-5: `10 passed` via `tests/test_p6_5_macro_regression.py tests/test_p6_methodology_depth.py tests/test_jobs_runner.py`
  - P6-4: `7 passed` via `tests/test_p6_4_polygon_options.py tests/test_p6_methodology_depth.py`
  - P8-2: `5 passed` via `tests/test_p8_2_etf_holdings.py tests/test_jobs_runner.py`
  - Total targeted tests passed during this run: `38`
- Backend full-suite spot check:
  - `pytest tests/ -x -q` still stops on the same pre-existing failure:
    - `tests/test_article_scraper_resolution.py::test_attach_decoded_google_news_urls_rewrites_wrapper_urls`
  - No new first-failure regression was introduced ahead of that point.
- iOS verification:
  - `cd ios && xcodegen && xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build`
  - Result: `BUILD SUCCEEDED`

## Manual Verification Checklist
- Search tab → type `AAPL` or `NVDA` → open ticker detail.
  - The score-history area should now show prior daily points once `python -m app.jobs.run backfill_14d` has been executed against the environment you are testing. It should no longer behave like a single-day-only history.
- Ticker Detail → open `Methodology` → go to the `Macro` tab.
  - The macro section should now include `factor_exposures` with non-zero values such as `beta_spy` instead of a placeholder-only macro card.
- Ticker Detail → open `Methodology` → go to the `Volatility` tab.
  - `IV Rank` should be populated.
  - The source should resolve cleanly through the payload:
    - `polygon` when an options snapshot was found
    - `estimated` when the fallback path was used
  - `implied_volatility` should prefer the live `implied_vol_30d` value when present.
- Ticker Detail → in recent news, open an article detail sheet.
  - Inside the existing `★ PERSONALISED` card, the first line should always be the structural sentence:
    - `You hold ... This change moves your portfolio composite from ...`
  - A second paragraph only appears if `MINIMAX_PERSONALISATION_ENABLED=true` and `MINIMAX_DAILY_BUDGET > 0`; with defaults, expect structural-only and no collapse.
- Search tab → open an ETF ticker with current support (`SPY`, `QQQ`, `VTI`) and then pull backend data or inspect the associated holdings-driven surfaces if you already have one wired locally.
  - There is no dedicated new iOS-only ETF holdings screen in this run; the main verification for P8-2 is the live issuer fetch succeeding and writing rows with `source` set to `ssga`, `invictus`, or `vanguard` instead of only `static_seed`.

## Open Questions / Next Steps
- No planned deferred items remain from the prior Codex run.
- The only outstanding repo-level verifier issue observed in this run is the pre-existing Google News URL rewrite test failure in [backend/tests/test_article_scraper_resolution.py](/Users/sansarkarki/Documents/Clavis/backend/tests/test_article_scraper_resolution.py).
