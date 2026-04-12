# Clavis

**Portfolio risk intelligence for self-directed investors.**

Clavis monitors your holdings, filters relevant news, and scores downside risk using letter grades (A–F). The app describes what's happening in your portfolio — it does not tell you what to do.

> Clavis is a portfolio risk data platform. It provides informational model outputs only, not investment advice.

---

## Status

**Currently working on:** Shared Ticker Intelligence Platform Migration

**Phase 1–2 roadmap items:** Security, legal, onboarding — mostly complete

**Gate 0 blockers remaining before launch can proceed:**
- Paid Apple Developer account
- App Store Connect setup
- RevenueCat setup
- Business entity and banking
- SnapTrade developer application and approval

---

## Architecture Migration: Shared Ticker Intelligence Platform

**Goal:** Move Clavis from a user-scoped, on-demand analysis model to a shared ticker intelligence platform.

- Free users read the latest cached daily ticker analysis
- Pro users can force-refresh a ticker intra-day
- A refresh updates the shared ticker cache for everyone
- Holdings, watchlists, search, and digest all read from the same canonical ticker snapshot
- This reduces analysis cost, makes watchlists natural, improves consistency, and turns Clavis into a true risk data platform

### Migration Progress

#### Stage 1: Schema Foundation ✅ Complete

| Table | Purpose | Status |
|-------|---------|--------|
| `ticker_universe` | Supported tickers (S&P 500 seeded), priority ranking | ✅ |
| `ticker_risk_snapshots` | Canonical shared risk output (grade, score, reasoning) | ✅ |
| `ticker_news_cache` | Shared relevant news per ticker | ✅ |
| `ticker_refresh_jobs` | Job audit, deduplication, and refresh gating | ✅ |
| `watchlists` | User-defined collections | ✅ |
| `watchlist_items` | Ticker membership in watchlists | ✅ |
| `ticker_metadata` extended | PE ratio, 52-week high/low, avg volume, price snapshot | ✅ |

#### Stage 2: Backend API Layer 🔄 In Progress

| Route | Description | Status |
|-------|-------------|--------|
| `GET /tickers/search` | Search supported tickers | ✅ |
| `GET /tickers/{ticker}` | Ticker detail bundle | ✅ |
| `POST /tickers/{ticker}/refresh` | Pro-only manual refresh | ✅ |
| `GET /tickers/{ticker}/refresh-status` | Refresh job status | ✅ |
| `GET /watchlists` | List user's watchlists | ✅ |
| `POST /watchlists` | Create watchlist | ✅ |
| `POST /watchlists/{id}/items` | Add ticker to watchlist | ✅ |
| `DELETE /watchlists/{id}/items/{ticker}` | Remove ticker | ✅ |

| Backend Service | Description | Status |
|----------------|-------------|--------|
| `ticker_cache_service` | Shared ticker cache read/write, S&P 500 seed, search | ✅ |
| Daily batch refresh scheduler | 3AM ET refresh of S&P 500 universe | ✅ |
| Pro manual refresh path | `refresh_ticker_snapshot()` reusable function | ✅ |

#### Stage 3: iOS Integration 🔄 In Progress

| Screen / Feature | Description | Status |
|-----------------|-------------|--------|
| `TickerDetailView` | Canonical ticker intelligence screen | ✅ |
| `TickerSearchSheet` | Search-first add position flow | ✅ |
| Holdings enriched from ticker cache | Positions read canonical snapshots | ✅ |
| Watchlist UI | User watchlist management | 🔄 Pending |
| Add-position flow flip | Instant add (no blocking analysis) | 🔄 Pending |
| Digest cutover | Source canonical snapshots instead of position analysis | 🔄 Pending |

#### Stage 4: Digest & Alerts Migration ⏳ Pending

- Digest pipeline refactored to read canonical ticker snapshots
- Alerts fan out from canonical snapshot changes

#### Stage 5: Legacy Cleanup ⏳ Pending

- Retire or archive old `risk_scores` / `position_analyses` writes
- Keep as historical audit only

### What's Been Built So Far

**Backend:**
- S&P 500 universe seeded (505 tickers, priority-ranked)
- Shared `ticker_risk_snapshots` table — canonical risk output per ticker
- Shared `ticker_news_cache` table — relevant news per ticker
- `ticker_refresh_jobs` for job deduplication and audit
- `GET /tickers/search` — searches `ticker_universe`, returns ticker + latest grade + freshness
- `GET /tickers/{ticker}` — full ticker detail bundle (profile, price, risk snapshot, news, user context)
- `POST /tickers/{ticker}/refresh` — pro-only, enqueues shared refresh job, writes canonical snapshot
- `GET /tickers/{ticker}/refresh-status` — job status polling
- Full watchlist CRUD endpoints
- Daily 3AM ET batch refresh job in scheduler
- Holdings and dashboard routes now prefer canonical ticker snapshots

**iOS:**
- `TickerDetailView` — canonical ticker intelligence screen
- `TickerSearchSheet` — search-first add position flow
- Holdings enriched with cached ticker snapshots
- `OnboardingViewModel` and 4-screen onboarding flow complete

### What's Left

- iOS watchlist management UI (add/remove tickers, view watchlist)
- iOS holdings add flow flip — instant add without blocking analysis
- Digest pipeline cutover to canonical ticker snapshots
- Alert fan-out from snapshot changes
- Legacy analysis table cleanup

---

## Roadmap Progress

### Phase 1 — Security, Legal Reframing, and Critical Bug Fixes ✅ Complete

| Item | Status |
|------|--------|
| JWT verification hardened (Supabase `get_user`) | ✅ |
| Supabase RLS audit and hardening | ✅ |
| Environment audit (no secrets in code) | ✅ |
| Advisory/action copy removed from AI pipeline | ✅ |
| `"What To Do"` → `"Monitoring Notes"`, `"Action Signal"` → `"Risk Read"` | ✅ |
| `/preferences/alerts` PATCH endpoint | ✅ |
| All 10 preference fields persisted to Supabase | ✅ |
| Score disclaimers added to all score views | ✅ |
| Freshness timestamps on all data views | ✅ |
| `CancellationError` handling verified | ✅ |
| Phase 2 onboarding flow (4 screens) | ✅ |
| `POST /preferences/acknowledge` endpoint | ✅ |
| `hasCompletedOnboarding` flag implemented | ✅ |
| Notification permission step status-aware | ✅ |

### Phase 2 — Legal Documents, Onboarding, and Public Trust Surface 🔄 In Progress

| Item | Status |
|------|--------|
| Privacy Policy page | 🔄 Pending |
| Terms of Service page | 🔄 Pending |
| Refund Policy page | 🔄 Pending |
| Methodology page | ✅ Complete |
| Onboarding UX | ✅ Complete |

### Phase 3 — Website, Email Infrastructure, and App Store Trust Prep ⏳ Pending

- Marketing site cleanup (mobile, SEO, OG tags)
- Transactional email setup (Resend/Postmark/SendGrid)
- App Store Connect baseline metadata

### Phase 4 — Payments, RevenueCat, and Subscription Enforcement ⏳ Pending

- StoreKit 2 + RevenueCat integration
- Free tier (3 positions) vs Plus tier ($15/mo)
- Backend subscription enforcement
- Trial flow and expiry handling

### Phase 5 — SnapTrade and Portfolio Connection ⏳ Pending

- OAuth brokerage connection flow
- Real-time portfolio sync
- Disconnect/resync UX

### Phase 6 — App UX, Simulated Risk, and Profile Experience ⏳ Pending

- Profile screen (name, DOB, plan, brokers, subscription)
- Simulate Risk flow before adding real positions
- Search, sort, filter on holdings
- Dark mode, Dynamic Type, accessibility audits

### Phase 7 — Backend Production Readiness ⏳ Pending

- Health check endpoint
- Graceful shutdown
- Structured logging and error alerting
- `DELETE /account` and `GET /account/export`
- Database backups

### Phase 8 — Notifications and Alert Quality ⏳ Pending

- Production APNs configuration
- Alert preference granularity
- Silent hours, rate limits
- Deep links from push

### Phase 9 — App Store Submission ⏳ Pending

- Full metadata and screenshots
- Finance-specific review prep
- Demo account for Apple reviewers

### Phase 10 — Testing Matrix ⏳ Pending

- Full functional testing
- iOS 16/17, SE, dark mode, accessibility
- Offline/airplane mode
- TestFlight external beta

### Phase 11 — Launch Operations ⏳ Pending

- Support inbox and ops runbook
- Press kit and launch announcement

---

## Tech Stack

**Backend:** Python/FastAPI in Docker
- Supabase (PostgreSQL + RLS)
- Polygon (market data)
- Finnhub (news)
- MiniMax (AI analysis)

**iOS:** SwiftUI
- StoreKit 2 + RevenueCat (planned)
- SnapTrade (planned)

**Infrastructure:** Cloudflare Tunnel
- Production URL: https://clavis.andoverdigital.com

---

## API Endpoints

All endpoints require `Authorization: Bearer <jwt>` header.

| Endpoint | Method | Description |
|---|---|---|
| `/holdings` | GET/POST | List/add positions |
| `/holdings/{id}` | DELETE | Delete position |
| `/positions/{id}` | GET | Position detail + score |
| `/digest` | GET | Today's digest |
| `/alerts` | GET | Grade change alerts |
| `/preferences` | GET/PATCH | User settings |
| `/preferences/acknowledge` | POST | Onboarding completion |
| `/trigger-analysis` | POST | Run analysis |
| `/tickers/search` | GET | Search supported tickers |
| `/tickers/{ticker}` | GET | Ticker detail + snapshot |
| `/tickers/{ticker}/refresh` | POST | Pro-only manual refresh |
| `/tickers/{ticker}/refresh-status` | GET | Refresh job status |
| `/watchlists` | GET/POST | List/create watchlists |
| `/watchlists/{id}/items` | POST/DELETE | Add/remove watchlist items |

---

## Project Structure

```
Clavis/
├── backend/            # FastAPI backend (Docker)
├── ios/                # SwiftUI iOS app
├── docs/
│   ├── STATE/          # Project state
│   └── STATUS/         # Roadmap
├── supabase/migrations/ # Database migrations
└── scripts/            # Dev helper scripts
```

---

## Development

### Backend
```bash
docker-compose up -d          # Start
docker logs clavis-backend-1  # View logs
docker restart clavis-backend-1 # Restart
```

### iOS
```bash
cd ios
xcodegen generate
xcodebuild -scheme Clavis -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

---

## Launch Criteria

Clavis is launch-ready when all of the following are true:

- Security basics are correct
- User isolation is verified
- Legal docs are public and accurate
- In-app copy does not cross into advice language
- Apple reviewer can test the app with a seeded demo account
- Subscription flows work
- Notifications work in production
- Crash and error monitoring are live
- Website and support surfaces look legitimate
- The app behaves well with no data, no network, expired trial, multiple accounts, and fresh install
