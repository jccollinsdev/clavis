# Phase 0 — MVP Data Baseline (pre-implementation, CORRECTED)

*Generated: 2026-05-18 23:48 UTC · trailing 7d · deterministic pagination (_dbpage.fetch_all)*

> **Data-integrity correction:** the earlier strict 500/504 report (≥3 402/503) and headline_only audit (8,686) were produced by range pagination without a stable ORDER BY and silent error-as-EOF, which under-counted usable rows on transient page errors. Fixed in `_dbpage.fetch_all` (explicit order, bounded retry, hard raise). All numbers below are reproducible across repeated runs (verified 3×).

## Runtime / deploy
- Local & VPS branch `backend/news-pipeline-candidate-ranking`; VPS `/opt/clavis` bind-mount `backend/app -> /app/app (rw)`
- Pre-existing uncommitted local WIP in routes/models/ios (NOT mine, NOT deployed, NOT bundled)
- VPS stray untracked `Users/` dir + safety stash `vps-pre-news-recovery-20260517T2225Z` (left intact); separate unhealthy `crawl4ai-audit` container (unrelated, untouched)
- No pipeline-writer processes running. Env: scheduler paused, news-enrichment disabled, Finnhub primary, Google discovery off, no `GOOGLE_NEWS_WRAPPER_*` yet.

## DB baseline (deterministic)
| Universe | |
|---|---|
| ticker_universe total | 504 |
| SP500 active | 503 |

| Articles 7d | |
|---|---|
| total rows | 15368 |
| strict usable total | 4023 |
| headline_only | 7731 |
| google-wrapper | 5779 |
| ≥3 | 482/503 (95.8%) |
| ≥5 | 414 |
| ≥10 | 139 (27.6%) |
| ≥20 | 10 |
| zero usable | 1 |

| Snapshots | |
|---|---|
| latest snapshot_date | 2026-05-16 |
| rows at latest | 250 |
| distinct tickers at latest | 244/503 |
| product_visible | 10 |
| methodology_versions | {'v2': 247, 'sp500-ai-analysis-v2': 3} |
| data_status | {'None': 217, 'complete': 33} |
| freshness | {'<=72h': 250} |
| dimension scored | {'financial_health': 249, 'news_sentiment': 235, 'macro_exposure': 249, 'sector_exposure': 249, 'volatility': 249} |
| news_sentiment null | 15 |

**Gaps to close:** 244/503 tickers have a recent snapshot (2026-05-16, ~2d stale); 5779 wrapper rows recoverable; 1 tickers zero usable; ≥10 depth 139.
