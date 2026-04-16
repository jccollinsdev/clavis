# Clavis

Portfolio risk intelligence for self-directed investors.

Clavis monitors holdings, ingests market and company news, scores downside risk on an `A-F` scale, and surfaces digest and alert changes. The product is being built as a portfolio risk data platform, not an investment adviser, broker, or trading app.

> Informational model outputs only. Not financial advice.

---

## Current Status

Clavis is in an active transition from position-scoped analysis to a shared ticker intelligence platform.

What is already live in the codebase:

- FastAPI backend with holdings, dashboard, digest, alerts, preferences, ticker search/detail, watchlists, scheduler, and analysis-run endpoints
- SwiftUI iPhone app with auth, onboarding, holdings, digest, alerts, settings, ticker search, and ticker detail flows
- Shared S&P ticker cache foundation backed by Supabase tables and scheduled refresh jobs
- News pipeline that combines CNBC macro and sector feeds, Google News RSS, article resolution, relevance filtering, event analysis, and AI-assisted scoring
- Instrumented S&P backfill tooling with artifact capture for debugging long runs

Major launch blockers still open:

- Security and production hardening work is not finished
- Legal/public trust documents are not fully published
- Subscription and RevenueCat flows are not implemented
- SnapTrade integration is not implemented
- Notification lifecycle and deep-link quality are incomplete

---

## Product Direction

Clavis is moving toward a shared ticker intelligence model:

- Shared ticker snapshots become the canonical source for search, ticker detail, watchlists, holdings enrichment, digest fallback, and alert comparisons
- Free users consume the latest cached ticker intelligence
- Pro users can request manual ticker refreshes
- Backfill and scheduled refresh infrastructure update shared ticker state for all users

This lowers analysis cost, improves consistency across the app, and makes watchlists and search first-class features instead of bolt-ons.

---

## Implemented Features

### Backend

- JWT-backed request authentication via Supabase `auth.get_user`
- Holdings CRUD and position detail routes
- Dashboard, digest, alerts, and preferences routes
- Preferences persistence for digest timing, summary length, onboarding completion, and alert settings
- Shared ticker routes:
  - `GET /tickers/search`
  - `GET /tickers/{ticker}`
  - `POST /tickers/{ticker}/refresh`
  - `GET /tickers/{ticker}/refresh-status`
- Default watchlist routes:
  - `GET /watchlists`
  - `POST /watchlists/default/items`
  - `DELETE /watchlists/default/items/{ticker}`
- Scheduler endpoints for per-user status plus S&P seed/backfill/status helpers
- Shared ticker services for universe seeding, search, detail assembly, watchlists, and snapshot refresh jobs
- S&P universe seeding and ticker snapshot refresh pipeline
- Full AI backfill path for S&P/shared ticker analysis with artifact capture under `BACKFILL_IMPORT/`
- Google News company/sector RSS ingest with canonical URL decoding
- Article enrichment and resolver hardening for Google wrapper links
- Env-configurable Google RSS throttling via `GOOGLE_NEWS_RSS_DELAY_SECONDS`

### iOS

- Supabase auth flow
- Onboarding flow with welcome, name/birth year, risk acknowledgment, notification step, and first-position flow
- Auth gate that routes authenticated users to onboarding or main app
- Tab-based app shell with Dashboard, Holdings, Digest, Alerts, and Settings
- Holdings list with cached ticker snapshot enrichment
- Position detail screen with score, chart, risk dimensions, and news/event surfaces
- Ticker search sheet and shared ticker detail screen
- Settings support for digest preferences and alert preferences
- Score disclaimer and freshness copy on score-oriented screens

### Data / Supabase

- Shared ticker cache migration scaffold
- S&P universe seed data and snapshot-related migrations
- Analysis artifact and cache-related migrations
- Device registration edge function under `supabase/functions/register-device`

---

## Current Gaps

The codebase still needs meaningful work before public launch:

- Public privacy, terms, refund, and methodology pages must be finalized and aligned with the app
- Security hardening remains incomplete around debug/internal surfaces, CORS, secrets handling, and route protection model
- RevenueCat / StoreKit subscription flows are still pending
- SnapTrade account connection and sync are still pending
- Account export and deletion flows are still pending
- Notification token lifecycle, quiet-hours enforcement, and deep links need completion
- App Store trust surfaces, metadata, and review-prep assets are still pending
- Reliability, monitoring, and end-to-end testing need expansion

---

## Architecture

### Backend

- FastAPI in Docker
- Supabase for Postgres, auth, and RLS-backed data model
- Polygon for market data
- Finnhub for metadata and market/company news inputs
- MiniMax for analysis/scoring prompts
- `mirofish` sidecar service for major-event analysis

### iOS

- SwiftUI app targeting iPhone
- Supabase Swift client for auth
- Custom API client for backend integration

### Shared Ticker Intelligence

Core shared-cache backend pieces now exist:

- `ticker_universe`
- `ticker_risk_snapshots`
- `ticker_news_cache`
- `ticker_refresh_jobs`
- `watchlists`
- `watchlist_items`
- expanded `ticker_metadata`

---

## API Surface

All app endpoints are intended to require `Authorization: Bearer <jwt>` unless explicitly public.

### Core user routes

- `GET /holdings`
- `POST /holdings`
- `DELETE /holdings/{id}`
- `GET /dashboard`
- `GET /digest`
- `GET /digest/history`
- `GET /positions/{id}`
- `GET /alerts`
- `GET /preferences`
- `PATCH /preferences`
- `PATCH /preferences/alerts`
- `POST /preferences/acknowledge`
- `POST /preferences/profile`
- `POST /preferences/device-token`
- `POST /trigger-analysis`
- `GET /analysis-runs/latest`
- `GET /analysis-runs/{id}`

### Shared ticker routes

- `GET /tickers/search`
- `GET /tickers/{ticker}`
- `POST /tickers/{ticker}/refresh`
- `GET /tickers/{ticker}/refresh-status`
- `GET /watchlists`
- `POST /watchlists/default/items`
- `DELETE /watchlists/default/items/{ticker}`

### Scheduler / infra helpers

- `GET /scheduler/status`
- `GET /scheduler/sp500/status`
- `POST /scheduler/sp500/seed`
- `POST /scheduler/sp500/backfill`
- `GET /health`

---

## Project Structure

```text
Clavis/
├── backend/                 FastAPI backend
│   ├── app/
│   │   ├── pipeline/        News, scoring, digest, scheduler pipelines
│   │   ├── routes/          API routes
│   │   ├── services/        Supabase, market data, cache, APNs, scraping
│   │   └── data/            Seed data such as the S&P universe
│   └── tests/
├── ios/                     SwiftUI iPhone app
├── mirofish/                Sidecar analysis service
├── supabase/
│   ├── migrations/
│   └── functions/
├── docs/
│   ├── STATE/
│   └── STATUS/
├── scripts/
└── BACKFILL_IMPORT/         Saved backfill artifacts and run output
```

---

## Development

### Backend

```bash
docker-compose up -d
docker logs clavis-backend-1
docker restart clavis-backend-1
```

### iOS

```bash
cd ios
xcodegen generate
xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build
```

### Session bootstrap

```bash
bash scripts/session-start.sh
```

---

## S&P Backfill Notes

The repo now supports throttling Google News RSS fetches during one-off backfill runs.

Environment variable:

- `GOOGLE_NEWS_RSS_DELAY_SECONDS`

Example:

```bash
docker exec -e GOOGLE_NEWS_RSS_DELAY_SECONDS=60 "clavis-backend-1" python -c '
import asyncio
from app.pipeline.scheduler import run_sp500_full_ai_analysis_fast
print(asyncio.run(run_sp500_full_ai_analysis_fast(job_type="backfill")))
'
```

That delay is opt-in. Normal runs remain unthrottled unless the variable is set.

---

## Launch Criteria

Clavis is launch-ready only when all of the following are true:

- Security basics are correct and verified
- User isolation is tested
- Legal docs are public and accurate
- The app copy stays in the informational/data lane
- Subscription flows work end to end
- Notifications work in production
- Monitoring and crash/error alerting are live
- The app handles no-data, no-network, fresh-install, and multi-account flows well

Until those are true, this is still an active pre-launch build.
