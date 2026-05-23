# UI Data Contract Matrix - VisualQA Target

Generated: 2026-05-23  
Status: VisualQA-based target contracts. Current shapes are summarized from existing Swift models/routes and may be incomplete.

## Conventions

| Term | Meaning |
|---|---|
| yes | route exists and can support the visible element with minimal shaping |
| partial | route exists but misses exact fields, history proof, freshness, or storage/generation coverage |
| no | route/contract missing |
| P0 | required to make VisualQA honestly live |
| P1 | strong production experience |
| P2 | platform/payments/import polish |

## Contracts

### VisualQA Today / Portfolio Summary

| Field | Value |
|---|---|
| endpoint path/name | Proposed `GET /today`; alternative: extend `GET /digest` plus `GET /holdings` envelope |
| exists today? | no as a single endpoint; partial across `/digest`, `/holdings`, `/alerts` |
| current response shape | `/digest` returns digest and structured sections; `/holdings` returns array of positions; `/alerts` returns alert array. |
| desired response shape for VisualQA | See sample JSON below. |
| fields used by VisualQA | portfolio value, day change, grade, score, score delta, generated timestamp, report preview, five-axis portfolio dimensions, sector cards, attention preview, top movers, calendar. |
| missing fields | server-side portfolio value envelope, portfolio day change, portfolio dimensions, sector ETF cards, alert summary count, top movers with true deltas, calendar rows. |
| DB source | `positions`, `ticker_metadata`, `ticker_risk_snapshots`, `digests`, `alerts`, `prices`, `portfolio_risk_snapshots`, `sector_regime_snapshots`. |
| generation source | portfolio rollup job, digest compiler, alert service, sector heat job. |
| frontend model/viewmodel | new `TodayViewModel`, `TodayResponse`, or compose in `DigestViewModel` only after endpoint stabilized. |
| priority | P0 |

```json
{
  "portfolio": {
    "value": 1284715.42,
    "day_change_amount": -5438.0,
    "day_change_pct": -0.42,
    "grade": "AA",
    "composite_score": 81,
    "previous_score": 82,
    "score_delta": -1,
    "generated_at": "2026-05-09T11:02:00Z",
    "history_count": 12,
    "dimensions": [
      {"code":"FIN","name":"Financial Health","score":86,"delta":0,"limited_data":false},
      {"code":"NEWS","name":"News Signal","score":62,"delta":-3,"limited_data":false}
    ]
  },
  "report": {"status":"ready","preview":"Rates moved higher overnight...","digest_id":"uuid"},
  "sector_exposure": [{"sector":"Technology","etf":"XLK","day_change_pct":0.42,"portfolio_weight_pct":42}],
  "attention": {"overnight_count":2,"unread_count":2,"alerts":[{"id":"uuid","category":"GRADE","title":"NVDA changed A -> BBB","destination":{"type":"alert_detail","id":"uuid"}}]},
  "top_movers": [{"ticker":"NVDA","grade":"BBB","score_delta":-3,"day_change_pct":-2.1,"reason":"News signal fell on export-control evidence."}],
  "calendar": [{"time":"08:30","type":"DATA","title":"April core CPI m/m","source":"macro_calendar"}]
}
```

### Morning Report

| Field | Value |
|---|---|
| endpoint | `GET /digest` |
| exists today? | partial |
| current response shape | `digest.content`, `overall_grade`, `overall_score`, `structured_sections.header`, `overnight_macro`, `sector_heat`, `positions`, `watchlist_updates`, `what_to_watch_today`, `generated_at`. |
| desired shape | Six Clavix Truth sections plus source/freshness footer and real score deltas. |
| used by VisualQA | report header, generated timestamp, portfolio grade/composite, macro prose, sector ledger, position ledger, tracked tickers, calendar, methodology footer. |
| missing fields | exact `portfolio.previous_score`, sector ETF moves/weights, position grade/delta/reason, tracked ticker structured rows, structured calendar events, source timestamps. |
| DB source | `digests`, `positions`, `ticker_risk_snapshots`, `shared_ticker_events`, `macro_regime_snapshots`, `sector_regime_snapshots`. |
| generation source | `portfolio_compiler.py`, macro/sector jobs, scheduler. |
| frontend model | extend `DigestSections` or create v2 `MorningReportResponse`. |
| priority | P0 |

### Sector Exposure

| Field | Value |
|---|---|
| endpoint | Proposed `GET /portfolio/sector-exposure` or embedded in `GET /today` and `GET /holdings` |
| exists today? | no exact |
| current shape | sector prose in digest; client may infer sector weights from holdings. |
| desired shape | `[{sector, etf, etf_day_change_pct, portfolio_weight_pct, sector_grade, held_tickers, as_of}]` |
| used by | Today sector grid, Morning Report sector ledger, Holdings sector composition. |
| missing | ETF day bars, sector snapshot rows, sector grades, canonical sector names. |
| DB source | `positions`, `ticker_metadata.sector`, `ticker_risk_snapshots`, `sector_regime_snapshots`, `prices` or factor prices. |
| generation | sector ETF refresh and portfolio aggregation. |
| sample JSON | `{"sector":"Technology","etf":"XLK","etf_day_change_pct":0.42,"portfolio_weight_pct":42,"sector_grade":"AA","held_tickers":["AAPL","MSFT","NVDA"]}` |
| frontend model | `SectorExposureCard`, `SectorCompositionRow`. |
| priority | P0 |

### Holdings

| Field | Value |
|---|---|
| endpoint | `GET /holdings` |
| exists today? | partial |
| current shape | array of `Position` objects. |
| desired shape | `{portfolio, positions, tracked_tickers, limits, sync}` |
| used by | Holdings summary, ledger, tracked tickers, sector composition, free/edit/delete states. |
| missing | portfolio envelope, day changes, weight, market value, P&L, mini sparkline, limits, enriched tracked tickers. |
| DB source | `positions`, `ticker_metadata`, `ticker_risk_snapshots`, `watchlists`, `watchlist_items`, `prices`, `user_preferences`. |
| generation | server-side enrichment in `enrich_positions_with_ticker_cache`. |
| sample JSON | `{"portfolio":{"value":1284715.42,"position_count":9},"positions":[{"id":"uuid","ticker":"NVDA","shares":420,"market_value":200852,"weight_pct":15.6,"last_price":478.22,"day_change_pct":-2.1,"unrealized_pl":69737,"grade":"BBB","score":64,"score_delta":-3}],"tracked_tickers":[{"ticker":"META","grade":"A","price":612.4}],"limits":{"positions_used":9,"positions_limit":null,"tier":"pro"}}` |
| frontend model | Replace array-only `fetchHoldings()` or add new method while preserving old route until migrated. |
| priority | P0 |

### Tracked Tickers

| Field | Value |
|---|---|
| endpoint | `GET /watchlists` today; desired `GET /tracked-tickers` or enriched watchlist payload |
| exists today? | partial |
| current shape | watchlist objects/items, not fully enriched for VisualQA ledger. |
| desired shape | ticker, company, grade, score, delta, price, day change, latest reason, limit state. |
| DB source | `watchlists`, `watchlist_items`, `ticker_metadata`, `ticker_risk_snapshots`, `alerts`. |
| sample JSON | `{"ticker":"TSLA","company_name":"Tesla","grade":"B","score":43,"score_delta":-4,"price":184.6,"day_change_pct":-2.9}` |
| priority | P1 |

### Ticker Detail

| Field | Value |
|---|---|
| endpoint | `GET /tickers/{ticker}` |
| exists today? | partial |
| current response shape | bundle from `get_ticker_detail_bundle`: summary, metadata prices, risk dimensions, drivers, events, overlay. |
| desired shape | hero, price chart metadata, dimensions with deltas, drivers with source IDs, recent news IDs, score history, actions. |
| missing | real score history array, dimension deltas/last-refreshed/limited flags, action eligibility, exact article IDs in recent news, hysteresis metadata. |
| DB source | `ticker_metadata`, `ticker_risk_snapshots`, `shared_ticker_events`, `prices`, `positions`, `watchlist_items`, `ticker_refresh_jobs`. |
| sample JSON | `{"ticker":"NVDA","company_name":"NVIDIA","sector":"Technology","industry":"Semiconductors","grade":"BBB","score":64,"previous_score":67,"score_delta":-3,"hysteresis":{"days_across_boundary":2},"price":{"last":478.22,"day_change_pct":-2.1},"dimensions":[{"code":"NEWS","score":38,"delta":-7,"last_refreshed":"2026-05-09T10:50:00Z"}],"drivers":[{"title":"Chip-export curbs widened","dimension":"News Signal","score_impact":-7,"source_event_ids":["uuid"]}],"actions":{"refresh":{"allowed":true,"remaining_today":4},"tracked_state":"not_tracked"}}` |
| frontend model | Extend `TickerDetailResponse`. |
| priority | P0 |

### Ticker Score History

| Field | Value |
|---|---|
| endpoint | Proposed `GET /tickers/{ticker}/score-history?dimension=composite&period=90d` |
| exists today? | no exact; DB exists |
| current shape | none exposed as stable array. |
| desired shape | ordered points with composite and optional dimension scores. |
| DB source | `ticker_risk_snapshots`. |
| sample JSON | `{"ticker":"NVDA","points":[{"date":"2026-05-07","score":70,"grade":"A"},{"date":"2026-05-09","score":64,"grade":"BBB"}],"history_count":2}` |
| frontend model | `ScoreHistoryPoint`; used by ticker chart and deltas. |
| priority | P0 |

### Ticker Search

| Field | Value |
|---|---|
| endpoint | `GET /tickers/search` |
| exists today? | partial |
| current shape | `{results, message}` from supported ticker search. |
| desired shape | results with current price, day change, grade, score, held/tracked flags, outside-universe result type. |
| DB source | `ticker_universe`, `ticker_metadata`, `ticker_risk_snapshots`, `positions`, `watchlist_items`. |
| sample JSON | `{"results":[{"ticker":"NVDA","company_name":"NVIDIA","grade":"BBB","score":64,"price":478.22,"day_change_pct":-2.1,"is_held":true,"is_tracked":false,"universe_status":"supported"}],"outside_universe":null}` |
| frontend model | Extend `TickerSearchResult`. |
| priority | P0 |

### Article Detail

| Field | Value |
|---|---|
| endpoint | Proposed `GET /articles/{id}` |
| exists today? | no exact; old `/news/{article_id}` exists but current VisualQA should use `shared_ticker_events`. |
| desired shape | source metadata, title, TLDR, what-it-means, key implications, score/reason, extraction/paywall state, source URL, portfolio context. |
| DB source | `shared_ticker_events`, `positions`, `ticker_metadata`. |
| sample JSON | `{"id":"uuid","ticker":"NVDA","title":"Export controls keep semiconductor risk elevated","source":"Reuters","source_tier":1,"published_at":"2026-05-09T09:00:00Z","tldr":"...","what_it_means":"...","key_implications":["..."],"sentiment_score":61,"sentiment_reason":"...","extraction_status":"success","paywalled":false,"portfolio_context":{"is_held":true,"weight_pct":15.6}}` |
| frontend model | `ArticleDetail`. |
| priority | P0 |

### Alerts

| Field | Value |
|---|---|
| endpoint | `GET /alerts` |
| exists today? | partial |
| current shape | array of enriched alerts. |
| desired shape | envelope with summary, filters, alerts. |
| missing | read/unread, category counts, destination metadata, severity, score deltas, article IDs. |
| DB source | `alerts`, `shared_ticker_events`, snapshots. |
| sample JSON | `{"summary":{"unread_count":2,"last_7d_count":14},"filters":[{"id":"grade","label":"Grade","count":5}],"alerts":[{"id":"uuid","category":"GRADE","severity":"high","read_at":null,"created_at":"2026-05-09T08:12:00Z","ticker":"NVDA","title":"NVDA changed A -> BBB","body":"News signal fell 7 pts...","grade":"BBB","score_delta":-3,"destination":{"type":"alert_detail","id":"uuid"}}]}` |
| frontend model | Replace array-only `fetchAlerts()` or add v2 method. |
| priority | P0 |

### Alert Detail

| Field | Value |
|---|---|
| endpoint | Proposed `GET /alerts/{id}` |
| exists today? | no |
| desired shape | alert row plus before/after scores, hysteresis proof, driving dimensions, source article rows, portfolio context, actions. |
| DB source | `alerts`, `ticker_risk_snapshots`, `shared_ticker_events`, `positions`. |
| priority | P1 |

### Notification Preferences

| Field | Value |
|---|---|
| endpoint | `GET /preferences`, `PATCH /preferences/alerts` |
| exists today? | partial |
| current shape | notifications, grade changes, major events, portfolio risk, large price moves, quiet hours. |
| desired shape | Morning Report, quiet hours, grade changes, major news, macro shock, tracked ticker alerts, severity threshold. |
| missing | `alerts_watchlist`, `alerts_macro_shock`, `alerts_digest_ready`, `alert_severity_threshold`. |
| DB source | `user_preferences`. |
| priority | P1 |

### Methodology Overview

| Field | Value |
|---|---|
| endpoint | `GET /tickers/{ticker}/methodology` |
| exists today? | partial |
| current shape | ticker, dimensions object, composite object. |
| desired shape | composite with formula metadata, grade bands/static version, dimensions array with score/delta/source/refreshed/limited. |
| missing | deltas, source rows, last refreshed per dimension, limited-data flags, grade movement/hysteresis metadata. |
| DB source | `ticker_risk_snapshots.dimension_inputs`, `dimension_last_refreshed`, snapshots. |
| priority | P0 |

### Methodology Dimension Detail

| Field | Value |
|---|---|
| endpoint | Existing `/tickers/{ticker}/methodology` can carry this; optional `GET /tickers/{ticker}/methodology/{dimension}` |
| exists today? | partial |
| desired shape | formula lines, input rows `{label,value,score,weight,benchmark,source,as_of}`, narrative, lineage, source article rows for news. |
| DB source | `ticker_risk_snapshots.dimension_inputs`, `shared_ticker_events`, `ticker_metadata`, `macro_regime_snapshots`, `sector_regime_snapshots`, `prices`. |
| priority | P0 |

### Settings / Account

| Field | Value |
|---|---|
| endpoint | `GET /preferences`, `POST /preferences/profile`, `/brokerage/status`, `/account/export`, `DELETE /account` |
| exists today? | partial |
| desired shape | profile, plan/entitlement, report prefs, alert prefs, brokerage status, export/delete action state, legal/support links. |
| missing | trial days, entitlement status, support/legal URLs, export job status. |
| priority | P1 |

### Subscription Entitlement

| Field | Value |
|---|---|
| endpoint | Proposed `GET /subscription/entitlement` |
| exists today? | no; only `subscription_tier` in preferences |
| desired shape | tier, status, trial start/end, renewal source, StoreKit product, feature limits. |
| DB source | future entitlement table/events, `user_preferences.subscription_tier` transitional. |
| priority | P2 backlog only |

### Onboarding / Add-Position Validation

| Field | Value |
|---|---|
| endpoint | Proposed `POST /holdings/validate` or included in `POST /holdings` error/success contract |
| exists today? | no exact |
| desired shape | ticker support, duplicate held state, free limit, outside-universe eligibility, required fields, degraded mode. |
| DB source | `ticker_universe`, `positions`, `user_preferences`, entitlement. |
| priority | P0 |

### Outside-Universe Validation

| Field | Value |
|---|---|
| endpoint | Proposed `GET /tickers/validate?q=...` or search result extension |
| exists today? | no; `POST /holdings` rejects unsupported ticker |
| desired shape | `universe_status`, `outside_universe_reason`, `can_add_degraded`, `can_request_universe_add`, `limited_fields`. |
| DB source | `ticker_universe`, `positions.outside_universe`, future `ticker_universe_requests`. |
| sample JSON | `{"ticker":"XYZ","universe_status":"outside","outside_universe_reason":"Below liquidity threshold","can_add_degraded":true,"limited_fields":["composite_score","macro_exposure","sector_exposure"]}` |
| priority | P0 |
