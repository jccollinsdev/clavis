# Clavix UI Data Fix Log

**Date:** 2026-05-30  
**Session:** End-to-end UI data QA  
**Engineer:** Claude Sonnet 4.6  

---

## Fix 1 — P1: RiskScore null-id and null-calculatedAt silently drop currentScore

**Symptom:** `TickerDetailView` always shows dimension scores from `shared?.financialHealth` fallback rather than `current?.financialHealth`. The `currentScore` object decoded as nil for every ticker. `factorBreakdown.aiDimensions` also nil.

**Root cause:** In `RiskScore.init(from:)`, two non-optional fields were decoded with `try container.decode(...)`:
- `id`: API always returns `"id": null` for shared/virtual scores
- `calculatedAt`: API always returns `null` for this field

When either throw, the parent `try? JSONDecoder().decode(RiskScore.self, from:)` returns nil.

**File changed:** `ios/Clavis/Models/RiskScore.swift`

```swift
// BEFORE (throws on null → parent returns nil):
id = try container.decode(String.self, forKey: .id)
calculatedAt = try container.decode(Date.self, forKey: .calculatedAt)

// AFTER:
let rawPositionId = (try? container.decodeIfPresent(String.self, forKey: .positionId)) ?? ""
positionId = rawPositionId
id = (try? container.decodeIfPresent(String.self, forKey: .id)) ?? "score:\(rawPositionId)"
calculatedAt = (try? container.decodeIfPresent(Date.self, forKey: .calculatedAt)) ?? Date()
```

**Status:** ✅ Fixed

---

## Fix 2 — P2: TickerRiskSnapshot null-id and null-analysisAsOf

**Symptom:** `latest_risk_snapshot` always returns `"id": null` and `analysis_as_of` is sometimes null. Non-optional Swift fields crash the decode.

**Root cause:** Both `id: String` and `analysisAsOf: Date` were non-optional in `TickerRiskSnapshot`.

**File changed:** `ios/Clavis/Services/APIService.swift`

```swift
// BEFORE:
let id: String
let analysisAsOf: Date

// AFTER:
let id: String?
let analysisAsOf: Date?
```

**Status:** ✅ Fixed

---

## Fix 3 — P0: Methodology endpoint all DB calls blocking event loop

**Symptom:** `GET /tickers/{ticker}/methodology` timed out (>15s) on every request. All five audit views (FIN, NEWS, MAC, SEC, VOL) showed "—" for all inputs.

**Root cause:** The `get_ticker_methodology` async FastAPI route made 5 sequential synchronous Supabase calls directly on the uvicorn event loop with no `asyncio.to_thread` wrapping:
1. `ticker_metadata` select
2. `sector_medians` select (up to 100 rows)
3. `peer_groups` select (up to 10 rows)
4. `get_latest_risk_snapshot_history_map` — full ticker snapshot history
5. `shared_ticker_events` select (up to 50 rows)
6. `digests` select in `attach_latest_personalisation`

**File changed:** `backend/app/routes/methodology.py`

**Fix:** Extracted entire synchronous body into `_build_methodology_response(supabase, upper, user_id)` and dispatched via `asyncio.to_thread`. Added `import asyncio`. Route handler is now 3 lines:

```python
async def get_ticker_methodology(ticker, user_id):
    supabase = get_supabase()
    upper = ticker.upper()
    return await asyncio.to_thread(_build_methodology_response, supabase, upper, user_id)
```

**Status:** ✅ Fixed, deployed via CI (run 26692306188), verified no timeouts

---

## Fix 4 — P0: Prices route `time.sleep(5.0)` blocks entire event loop

**Symptom:** Even after Fix 3, methodology and score-history still timed out. Root cause traced to the `/prices/{ticker}` endpoint which fires concurrently with methodology on every ticker detail open.

**Root cause:** `fetch_aggs()` calls `_rate_limit_polygon()` which contains `time.sleep(_MIN_CALL_SPACING - elapsed)` with `_MIN_CALL_SPACING = 5.0`. This `time.sleep(5.0)` ran directly on the uvicorn async event loop (no `asyncio.to_thread`), freezing ALL concurrent requests for 5 seconds. With the iOS methodology timeout at 15s, two such blocks = timeout.

Timeline of a single AAPL detail open (4 concurrent requests):
1. `/tickers/AAPL` → fast (ticker bundle cache)
2. `/prices/AAPL?days=365` → triggers Polygon → `time.sleep(5.0)` on event loop → all queued
3. `/tickers/AAPL/methodology` → queued, eventually times out at 15s
4. `/tickers/AAPL/score-history` → queued, eventually times out at 30s

**File changed:** `backend/app/routes/prices.py`

**Fix:** Extracted blocking work into `_fetch_price_history_sync(ticker, days)` and dispatched via `asyncio.to_thread`:

```python
def _fetch_price_history_sync(ticker: str, days: int) -> dict:
    history = fetch_price_history(ticker, days)
    if history and history_covers_days(history, days):
        return {"ticker": ticker, "prices": history}
    aggs = fetch_aggs(ticker, days)
    ...

async def get_price_history(ticker, days, user_id):
    return await asyncio.to_thread(_fetch_price_history_sync, ticker.upper(), days)
```

**Status:** ✅ Fixed, deployed via CI (run 26692529452), verified zero timeouts in post-fix logs

---

## Other Routes with the Same Blocking Pattern

The following routes already used `asyncio.to_thread` correctly (no changes needed):
- `tickers.py`: search, ticker detail, score-history, refresh endpoints
- `holdings.py`: position refresh

The following routes were NOT audited but may have similar patterns if they make synchronous Supabase or external API calls:
- `portfolio.py`, `today.py`, `dashboard.py`, `analysis_runs.py`

These should be audited before launch if they have user-facing latency concerns.

---

## Commits

| SHA | Message |
|---|---|
| `963f84d` | fix: methodology endpoint timeout — wrap sync Supabase calls in asyncio.to_thread |
| `65ea23c` | fix: prices route blocks event loop — wrap Polygon fetch in asyncio.to_thread |

Both deployed via GitHub Actions CI (deploy-prod.yml) with health check passing.
