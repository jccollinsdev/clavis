# Clavis - Project Status

## Overview
Clavis is a portfolio risk intelligence app that analyzes your stock holdings using AI to provide daily digests, risk scores, and alerts when positions change grade.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (iOS - SwiftUI)              │
│                                                               │
│  • Holdings input + archetype tagging                         │
│  • Dashboard (portfolio grade, position cards, news strip)     │
│  • Position detail (price chart, grade breakdown, news)        │
│  • Morning digest view                                        │
│  • Alerts view                                                │
│  • Settings (digest time, notifications)                       │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS / JWT Auth
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│           BACKEND (Python - FastAPI / Docker)                │
│                                                               │
│  • RSS Feed Ingestion (scheduled)                             │
│  • Relevance Filter (matches news to holdings)                │
│  • Significance Classifier (MiniMax AI)                      │
│  • MiroFish Swarm (major events - placeholder)                 │
│  • Agentic AI Scan (minor events - MiniMax)                  │
│  • Risk Scorer (5 dimensions, MiniMax AI)                    │
│  • Compiler AI (Morning digest synthesis)                      │
│  • Push Notification Dispatcher (APNs)                       │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                       SUPABASE                               │
│                                                               │
│  Tables: positions, risk_scores, news_items, digests, alerts,  │
│  user_preferences, analysis_runs, position_analyses,          │
│  event_analyses, prices                                       │
│                                                               │
│  Auth: Supabase Auth (email/password) + RLS enabled          │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                         │
│                                                               │
│  • MiniMax API - all AI layers (classifier, scanner, scorer,    │
│    compiler)                                                 │
│  • MiroFish - self-hosted swarm (placeholder, not installed)  │
│  • Finnhub - news + earnings data                             │
│  • Polygon.io - price chart data                             │
│  • APNs - push notifications                                 │
│  • RSS Feeds - macro financial news                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
Clavis/
├── backend/                    # Python/FastAPI (Docker)
│   ├── app/
│   │   ├── main.py           # FastAPI app + JWT middleware + scheduler
│   │   ├── config.py          # Environment settings
│   │   ├── routes/
│   │   │   ├── holdings.py    # /holdings CRUD
│   │   │   ├── digest.py      # /digest GET + /digest/history
│   │   │   ├── positions.py   # /positions/:id (detail + score)
│   │   │   ├── alerts.py      # /alerts GET
│   │   │   ├── preferences.py # /preferences GET/PATCH
│   │   │   ├── trigger.py     # /trigger-analysis POST
│   │   │   ├── scheduler.py   # /scheduler/status GET
│   │   │   ├── analysis_runs.py # /analysis-runs/*
│   │   │   ├── prices.py      # /prices/:ticker GET
│   │   │   ├── test_push.py   # /test-push POST
│   │   │   └── debug.py       # /debug/* routes
│   │   ├── pipeline/
│   │   │   ├── scheduler.py        # APScheduler (2,123 lines)
│   │   │   ├── rss_ingest.py      # RSS feed fetching
│   │   │   ├── finnhub_news.py    # Finnhub news + earnings
│   │   │   ├── news_normalizer.py # Article format normalization
│   │   │   ├── relevance.py       # News/holdings matching
│   │   │   ├── classifier.py      # Major/minor classification
│   │   │   ├── position_classifier.py # Position-aware classification
│   │   │   ├── agentic_scan.py     # Minor event analysis (MiniMax)
│   │   │   ├── mirofish_analyze.py # MiroFish swarm call (placeholder)
│   │   │   ├── risk_scorer.py      # 5-dim risk scoring
│   │   │   ├── structural_scorer.py # Deterministic structural scoring
│   │   │   ├── portfolio_risk.py   # Portfolio-level rollup
│   │   │   ├── portfolio_compiler.py # Digest synthesis (MiniMax)
│   │   │   ├── position_report_builder.py # Long-form position reports
│   │   │   ├── macro_classifier.py # Macro event classification
│   │   │   └── macro_regime.py     # Macro regime detection
│   │   ├── services/
│   │   │   ├── supabase.py    # Supabase client (service role)
│   │   │   ├── minimax.py     # MiniMax API client (OpenAI-compatible)
│   │   │   ├── apns.py        # APNs push client
│   │   │   ├── polygon.py     # Polygon.io price data
│   │   │   ├── ticker_metadata.py # Metadata refresh for scoring
│   │   │   └── debug_service.py # Request tracking
│   │   └── models/
│   │       ├── position.py, risk_score.py, digest.py, alert.py
│   │       ├── position_analysis.py, event_analysis.py
│   │       └── price_point.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env                   # Contains real keys (gitignored)
│
├── mirofish/                  # Self-hosted swarm (placeholder)
│   ├── Dockerfile
│   └── config/
│
├── supabase/
│   ├── supabase_schema.sql    # Full schema + RLS policies
│   └── functions/
│       └── register-device/   # Edge function for APNs token
│
├── ios/                       # SwiftUI iOS app
│   ├── project.yml            # XcodeGen config
│   └── Clavis/
│       ├── App/
│       │   ├── ClavisApp.swift      # @main, APNs delegate
│       │   ├── ContentView.swift    # Auth gate
│       │   ├── MainTabView.swift    # 5-tab navigation
│       │   └── ClavisDesignSystem.swift # 557-line design system
│       ├── Views/
│       │   ├── Auth/LoginView.swift
│       │   ├── Dashboard/DashboardView.swift
│       │   ├── Holdings/HoldingsListView.swift
│       │   ├── Digest/DigestView.swift
│       │   ├── Alerts/AlertsView.swift
│       │   ├── Settings/SettingsView.swift
│       │   ├── PositionDetail/PositionDetailView.swift
│       │   └── Shared/ (components)
│       ├── ViewModels/
│       │   ├── DashboardViewModel.swift
│       │   ├── HoldingsViewModel.swift
│       │   ├── DigestViewModel.swift  (analysis polling)
│       │   ├── AlertsViewModel.swift
│       │   ├── SettingsViewModel.swift
│       │   └── AuthViewModel.swift
│       ├── Models/ (11 models)
│       │   ├── Position, RiskScore, Digest, Alert, AnalysisRun
│       │   ├── PositionAnalysis, EventAnalysis, NewsItem, PricePoint
│       │   ├── UserPreferences, RiskEnums
│       ├── Services/
│       │   ├── APIService.swift       # 12KB main API client
│       │   ├── SupabaseAuthService.swift
│       │   └── PushNotificationManager.swift
│       └── Resources/
│
├── docker-compose.yml         # Backend + MiroFish services
├── scripts/
│   ├── setup-tunnel.sh
│   └── start.sh
└── .tunnel_url               # Cloudflare quick tunnel URL
```

---

## Supabase Project

- **Project ID:** `uwvwulhkxtzabykelvam`
- **Region:** us-west-1
- **URL:** `https://uwvwulhkxtzabykelvam.supabase.co`
- **Dashboard:** `https://supabase.com/dashboard`

### Database Schema

Tables with RLS enabled:
- `user_preferences` - digest time, notification prefs, APNs token
- `positions` - holdings with ticker, shares, purchase price, archetype
- `risk_scores` - 5-dim scores, grade, reasoning, mirofish_used flag
- `news_items` - filtered news per user (auto-cleanup at 30 days)
- `digests` - compiled morning digests with grade summary
- `alerts` - grade change and major event history
- `analysis_runs` - run tracking with status
- `position_analyses` - long-form AI analysis artifacts
- `event_analyses` - per-event AI analysis artifacts
- `prices` - price history for charts (no RLS, public)

### Edge Functions
- `register-device` - stores APNs token for push notifications

---

## Backend Configuration

**Local URL:** `http://localhost:8000` (Docker container: `clavis-backend-1`)  
**Public URL:** `https://clavis.andoverdigital.com` (Cloudflare named tunnel)

### Environment Variables (backend/.env)

```bash
SUPABASE_URL=https://uwvwulhkxtzabykelvam.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

MINIMAX_API_KEY=your-minimax-api-key
MINIMAX_BASE_URL=https://api.minimax.io/v1

FINNHUB_API_KEY=your-finnhub-api-key
POLYGON_API_KEY=your-polygon-api-key
APNS_KEY_ID=YOUR_APNS_KEY_ID
APNS_TEAM_ID=YOUR_APNS_TEAM_ID
APNS_KEY_PATH=/app/apns/apns.p8
MIROFISH_URL=http://mirofish:8001
```

---

## iOS App Configuration

- **Bundle ID:** `com.clavisdev.portfolioassistant`
- **Target:** iOS 17.0+
- **Backend URL:** `https://clavis.andoverdigital.com`

### Features Working ✅
- [x] Supabase Auth (email/password sign up, sign in, sign out)
- [x] Holdings CRUD (create, read, delete positions)
- [x] Dashboard with portfolio grade display
- [x] Position detail view with score breakdown, analysis, events, news
- [x] Morning digest view (What Changed / What Matters / Monitoring Notes)
- [x] Alerts view with grouped alerts, pull-to-refresh
- [x] Settings view (digest time, notification preferences)
- [x] Analysis progress polling during runs
- [x] Price chart display (SwiftUI Charts framework)
- [x] Custom design system (ClavisTheme, ClavisTypography, ClavisGradeStyle)

### Features Partially Working ⚠️
- [ ] `summary_length` and `weekday_only` sent by iOS but not fully persisted
- [ ] `/preferences/alerts` endpoint called by iOS but no matching route
- [ ] Debug routes present (should be internal tooling only)

### Features Not Working 🔴
- [ ] **MiroFish integration** - Container scaffolded but contains placeholder, no actual package
- [ ] **APNs push** - Requires valid Apple credentials, key file, real device token
- [ ] **Real news from Finnhub** - API key may be placeholder
- [ ] **Real price data from Polygon** - API key may be placeholder

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/holdings` | GET/POST | JWT | List/add positions |
| `/holdings/{id}` | DELETE | JWT | Delete position |
| `/positions/{id}` | GET | JWT | Position detail + score + analysis |
| `/digest` | GET | JWT | Today's compiled digest |
| `/digest/history` | GET | JWT | Recent digests |
| `/alerts` | GET | JWT | Grade change + major event alerts |
| `/preferences` | GET/PATCH | JWT | User settings |
| `/preferences/device-token` | POST | JWT | APNs token registration |
| `/trigger-analysis` | POST | JWT | Run manual analysis |
| `/analysis-runs/latest` | GET | JWT | Latest run status |
| `/analysis-runs/{id}` | GET | JWT | Specific run details |
| `/prices/{ticker}` | GET | JWT | Price history from Polygon |
| `/scheduler/status` | GET | JWT | Per-user scheduler state |
| `/test-push` | POST | JWT | APNs verification |
| `/debug/*` | GET | No | Debug dashboard (internal) |

---

## News Pipeline

```
RSS + Finnhub
    ↓
Normalizer (news_normalizer.py)
    ↓
Relevance Filter (matches to holdings / macro themes)
    ↓
Classifier (MiniMax major vs minor)
    │
    ├── Major Event → MiroFish Swarm (placeholder)
    │
    └── Minor Event → Agentic Scan (MiniMax)
    │
    ↓
Risk Scorer (5 dimensions → A-F grade)
    │
    ↓
Portfolio Risk Rollup + Portfolio Compiler (MiniMax digest)
    │
    ↓
Digest → Supabase + Alerts → APNs
```

### Risk Scoring Dimensions
1. **news_sentiment** - Recent news tone
2. **macro_exposure** - Sensitivity to macro events
3. **position_sizing** - Concentration risk
4. **volatility_trend** - Recent price volatility
5. **earnings_risk** - Upcoming earnings risk

---

## Running Locally

### Start Backend
```bash
cd ~/Documents/Clavis
docker-compose up -d
docker logs clavis-backend-1
docker restart clavis-backend-1
```

### Start Cloudflare Tunnel (PERSISTENT)
```bash
cloudflared tunnel run clavis-prod
```
URL: https://clavis.andoverdigital.com

### iOS Build
```bash
cd ~/Documents/Clavis/ios
xcodegen generate
xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build
```

---

## Known Issues

| Issue | Severity | Fix |
|-------|----------|-----|
| **JWT signature not verified** | High | Token trusted based on payload; add RS256 verification |
| `/preferences/alerts` route missing | Medium | Add backend route matching iOS call |
| `summary_length` / `weekday_only` not persisted | Medium | Complete preference persistence |
| Debug routes exposed | Low | Gate behind env flag |
| Cloudflare quick tunnel URL changes on restart | Medium | Use named tunnel (already done in prod) |
| MiroFish not installed | Medium | Container scaffolded, needs actual swarm package |
| APNs not configured | Medium | Requires Apple Developer account + key file |

---

## What's Been Built

This project was built from scratch. Key decisions made:

1. **SwiftUI frontend** - Native iOS 17+, uses XcodeBuildMCP
2. **Supabase for auth + database** - Handles user management, RLS, Edge Functions
3. **Python/FastAPI backend** - Docker container, validates JWT from Supabase
4. **MiniMax for all AI** - OpenAI-compatible API, used for classification, analysis, scoring, compilation
5. **Cloudflare named tunnel** - Stable production URL
6. **Local Docker** - Backend runs locally in Docker

---

## Roadmap

### V2 - Next Phase

| Feature | Priority | Description |
|---------|----------|-------------|
| **Price Charts** | High | Interactive charts in Position Detail (SwiftUI Charts ready, data flow needed) |
| **Push Notifications (APNs)** | High | Real device push when grades change; needs Apple Developer account + key file |
| **MiroFish Swarm** | Medium | Self-hosted swarm for major event analysis (placeholder → real integration) |
| **Background Polling** | Medium | iOS background app refresh for digest updates |

### Future - V3+

| Feature | Description |
|---------|-------------|
| **Brokerage API** | Auto-import positions from brokerage accounts |
| **Web App** | Browser-based dashboard alongside iOS |
| **Multi-user Sharing** | Share portfolios with family/advisors |
| **Onboarding Flow** | First-run tutorial + sample portfolio |

---

## Key Files

### Critical Backend Files
- `backend/app/main.py` - Entry point + middleware
- `backend/app/pipeline/scheduler.py` - 2,123 lines, orchestration hub
- `backend/app/pipeline/risk_scorer.py` - Scoring logic
- `backend/app/pipeline/portfolio_compiler.py` - Digest generation
- `backend/app/routes/positions.py` - Position detail endpoint
- `backend/app/routes/preferences.py` - User preferences

### Critical iOS Files
- `ios/Clavis/App/ClavisApp.swift` - App entry + APNs delegate
- `ios/Clavis/Services/APIService.swift` - Main API client (12KB)
- `ios/Clavis/ViewModels/DigestViewModel.swift` - Digest loading + analysis polling
- `ios/Clavis/Views/PositionDetail/PositionDetailView.swift` - Position detail screen
- `ios/Clavis/App/ClavisDesignSystem.swift` - Design system (557 lines)

### Configuration Files
- `docker-compose.yml` - Backend + MiroFish services
- `backend/.env` - API keys (Polygon, Finnhub, MiniMax, Supabase)
- `supabase_schema.sql` - Full database schema with RLS
- `ios/project.yml` - XcodeGen configuration
