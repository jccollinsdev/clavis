# Phase 0 — MVP Data Baseline (pre-implementation)

*Generated: 2026-05-18 23:45 UTC · trailing 7d*

## Local / VPS / Runtime
- Local branch `backend/news-pipeline-candidate-ranking` @ `c8596cb` (pre-existing uncommitted WIP in routes/models/ios — NOT mine, NOT deployed; will not be bundled)
- VPS `/opt/clavis` @ `c8596cb`, bind-mount `/opt/clavis/backend/app -> /app/app (rw)`; container `clavis-backend-1` Up; separate `crawl4ai-audit` container (unrelated, unhealthy — noted, untouched)
- VPS stray untracked `Users/` dir + safety stash `vps-pre-news-recovery-20260517T2225Z` (left intact)
- No pipeline-writer processes running (no reenrich/risk/backfill/scheduler/news_score). Clean.
- Env: `PAUSE_SYSTEM_SCHEDULER=true`, `DISABLE_NEWS_ENRICHMENT=true`, `NEWS_PRIMARY_PROVIDER=finnhub`, `GOOGLE_NEWS_FALLBACK_ENABLED=false`, `GOOGLE_FALLBACK_MIN_USABLE_ARTICLES=3`, MiniMax min-interval 1.0s. No `GOOGLE_NEWS_WRAPPER_*` yet.

## DB baseline
| Universe | |
|---|---|
| ticker_universe total | 504 |
| SP500 active | 503 |

| Articles (7d) | |
|---|---|
| total rows | 15378 |
| strict usable total | 4023 |
| headline_only | 7740 |
| news.google.com wrapper | 5787 |
| coverage ≥3 | 482/503 (95.8%) |
| coverage ≥5 | 414 |
| coverage ≥10 | 139 (27.6%) |
| coverage ≥20 | 10 |
| tickers zero usable | 1 |

| Snapshots | |
|---|---|
| latest snapshot_date | 2026-05-16 |
| rows at latest date | 250 |
| distinct tickers at latest | 244 / 503 |
| product_visible | 10 |
| methodology_versions | {'v2': 247, 'sp500-ai-analysis-v2': 3} |
| snapshot_types | {'daily': 217, 'manual_refresh': 33} |
| data_status | {'None': 217, 'complete': 33} |
| freshness (created_at) | {'<=72h': 250} |
| dimension scored counts | {'financial_health': 249, 'news_sentiment': 235, 'macro_exposure': 249, 'sector_exposure': 249, 'volatility': 249} |
| news_sentiment null | 15 |

**Key gaps:** only 244/503 tickers have a snapshot at the latest date (2026-05-16, ~2d stale); 5787 Google-wrapper rows recoverable; 1 tickers at zero usable; ≥10 depth only 139.
