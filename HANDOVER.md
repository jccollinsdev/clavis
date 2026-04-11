# Clavis Handover

## What The App Does
Clavis is a portfolio risk intelligence app for self-directed investors. It tracks holdings, ingests financial news, scores downside risk, and turns overnight changes into a daily digest and alerts.

The core promise is simple: tell the user what changed in their portfolio, what it means, and what needs attention.

## System Overview

| Layer | Tech | Job |
|---|---|---|
| iOS app | SwiftUI | Auth, holdings, digest, alerts, settings, position detail |
| Backend API | FastAPI | Auth gate, portfolio API, analysis triggers, digests, prices, alerts |
| Scheduler | APScheduler | Runs daily digest jobs per user |
| Database | Supabase Postgres | Stores positions, scores, news, digests, alerts, preferences, prices |
| AI | MiniMax | Relevance, event analysis, scoring, digest generation |
| News/Market data | RSS, Finnhub, Polygon | Feeds the analysis pipeline |
| Push | APNs | Optional device notifications |
| Dev infra | Docker, Cloudflare tunnel, Render | Local and hosted runtime |

## Product Flow
1. User signs in with Supabase Auth.
2. User adds holdings and tags each one with an archetype.
3. Backend pulls news and market data.
4. News is normalized and filtered to portfolio-relevant items.
5. Relevant items are classified as major or minor.
6. Minor items get position-aware analysis.
7. Risk is scored per position and rolled up to a portfolio view.
8. A digest is compiled and stored in Supabase.
9. Alerts and optional APNs pushes are emitted when conditions warrant.

## Backend

### Entry Point
`backend/app/main.py`

Responsibilities:
- Creates the FastAPI app.
- Enables CORS.
- Validates APNs configuration at startup.
- Starts the scheduler on launch.
- Registers all routers.
- Extracts `request.state.user_id` from the Supabase JWT payload.

### Auth Notes
- Requests to portfolio routes require `Authorization: Bearer <jwt>`.
- The middleware decodes the JWT payload and trusts the `sub` claim as the user id.
- Signature verification is not fully enforced in this app layer.

### API Routes

| Route | Purpose |
|---|---|
| `GET /health` | Health check |
| `GET /holdings` | List holdings with latest grade, score, prior grade, summary |
| `POST /holdings` | Add a holding |
| `GET /holdings/{id}` | Fetch a holding |
| `PATCH /holdings/{id}` | Update a holding |
| `DELETE /holdings/{id}` | Delete a holding and detach linked analysis history |
| `GET /positions/{id}` | Deep position detail: score, analysis, events, news, alerts |
| `GET /digest` | Latest digest for today |
| `GET /digest/history` | Recent digest history |
| `GET /alerts` | Recent alerts |
| `GET /preferences` | User preferences |
| `PATCH /preferences` | Update digest time / notification toggle |
| `POST /preferences/device-token` | Register APNs token |
| `POST /trigger-analysis` | Start a manual analysis run |
| `GET /analysis-runs/latest` | Latest analysis run |
| `GET /analysis-runs/{id}` | Specific run |
| `GET /prices/{ticker}` | Historical price series |
| `GET /scheduler/status` | Per-user scheduler state |
| `POST /test-push` | Send a test APNs notification |
| `GET /debug/*` | Debug dashboard and request/AI traces |

### Key Backend Files
- `backend/app/routes/holdings.py` - holdings CRUD and live price refresh.
- `backend/app/routes/positions.py` - deep detail response for the position screen.
- `backend/app/routes/digest.py` - digest lookup and history.
- `backend/app/routes/alerts.py` - alert feed.
- `backend/app/routes/preferences.py` - digest time, notifications, APNs token.
- `backend/app/routes/trigger.py` - manual analysis trigger.
- `backend/app/routes/analysis_runs.py` - run status and progress mapping.
- `backend/app/routes/prices.py` - price history lookup and persistence.
- `backend/app/routes/scheduler.py` - scheduler status.
- `backend/app/routes/test_push.py` - APNs verification.
- `backend/app/routes/debug.py` - internal debug dashboard.

### Analysis Pipeline
The main pipeline lives under `backend/app/pipeline/`.

Current flow:
RSS + Finnhub -> relevance -> classifier -> minor-event analysis or MiroFish fallback -> risk scoring -> portfolio digest -> Supabase

Important modules:
- `rss_ingest.py` - macro news ingestion.
- `finnhub_news.py` - company and market news.
- `news_normalizer.py` - normalizes article shape.
- `relevance.py` - matches news to portfolio holdings and macro themes.
- `classifier.py` - major vs minor significance classification.
- `agentic_scan.py` - position-aware analysis for minor events.
- `mirofish_analyze.py` - tries MiroFish first, falls back to MiniMax.
- `risk_scorer.py` - per-position scoring and A-F grade.
- `portfolio_risk.py` - portfolio-level rollup.
- `portfolio_compiler.py` - digest synthesis.
- `scheduler.py` - scheduled daily runs and run-state persistence.
- `ticker_metadata.py` - metadata refresh for structural scoring.

### Scoring Model
Each position gets a score and grade based on a mix of:
- News sentiment.
- Macro exposure.
- Position sizing.
- Volatility trend.
- Structural and event adjustments.

Grades are normalized to A, B, C, D, F and surfaced in both the dashboard and detail screens.

### Data Written By Backend
Core tables and artifacts:
- `positions`
- `risk_scores`
- `news_items`
- `event_analyses`
- `position_analyses`
- `digests`
- `alerts`
- `user_preferences`
- `analysis_runs`
- `analysis_cache`
- `scheduler_jobs`
- `prices`

## iOS App

### App Entry
- `ios/Clavis/App/ClavisApp.swift` bootstraps the app.
- `ContentView.swift` gates access on auth state.
- `MainTabView.swift` holds the main app navigation.

### Navigation Tabs
1. Home - dashboard summary.
2. Holdings - list, add, delete positions.
3. Digest - morning digest and analysis run status.
4. Alerts - grouped alert feed.
5. Settings - digest, alert, account controls.

### Screen Behavior

#### Login
`Views/Auth/LoginView.swift`
- Email/password login and sign up.
- Toggled mode for new account creation.

#### Dashboard
`Views/Dashboard/DashboardView.swift`
- Shows portfolio risk grade and score.
- Highlights positions that need attention.
- Shows counts for worsening, improving, and major events.
- Opens the current digest.

#### Holdings
`Views/Holdings/HoldingsListView.swift`
- Lists holdings ordered by risk score.
- Supports pull-to-refresh.
- Supports add and delete.
- New holding creation opens a progress sheet while analysis runs.

#### Digest
`Views/Digest/DigestView.swift`
- Displays the current digest, portfolio summary, what changed, what matters today, what to do, and the full narrative.
- Shows analysis run progress when a run is active.
- Can trigger a new analysis manually.

#### Alerts
`Views/Alerts/AlertsView.swift`
- Loads alerts and groups similar alerts by type and ticker within a 60 minute window.

#### Position Detail
`Views/PositionDetail/PositionDetailView.swift`
- Shows score hero, price snapshot, price chart, risk drivers, recent developments, watch items, event analyses, and recent alerts.
- Can trigger a fresh analysis for that holding.
- Polls analysis run status until completion.

#### Settings
`Views/Settings/SettingsView.swift`
- Shows signed-in user email.
- Lets the user set digest time.
- Includes summary length and weekday-only controls.
- Includes alert toggles and quiet hours.
- Links to score explanation and methodology screens.

### UI System
- The app uses a custom SwiftUI design system in `App/ClavisDesignSystem.swift`.
- Cards, gradients, typography, and color tokens are consistent across the app.
- The price chart uses the native Charts framework.

### View Models
- `DashboardViewModel` loads holdings and the digest together and derives portfolio health.
- `HoldingsViewModel` handles add/delete flows and analysis polling.
- `DigestViewModel` loads digest, history, holdings, alerts, and run state.
- `AlertsViewModel` handles alert grouping.
- `SettingsViewModel` loads and saves preferences.
- `AuthViewModel` manages Supabase session state.

## Infrastructure

### Local Runtime
- Backend runs in Docker.
- `docker-compose.yml` starts the backend and the MiroFish service.
- Backend code is volume-mounted into the container.

### Hosted Runtime
- `render.yaml` deploys the backend as a Docker service.
- Cloudflare tunnel is used for local device testing against the backend.

### Environment Variables
Set in `backend/.env` and Render secrets as needed.

Required keys:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `MINIMAX_API_KEY`
- `MINIMAX_BASE_URL`
- `FINNHUB_API_KEY`
- `POLYGON_API_KEY`
- `APNS_KEY_ID`
- `APNS_TEAM_ID`
- `APNS_KEY_PATH`
- `APNS_BUNDLE_ID`
- `MIROFISH_URL`

### iOS Config
- Bundle id: `com.clavisdev.portfolioassistant`
- Minimum OS: iOS 17
- Backend base URL is hardcoded in `ios/Clavis/Services/APIService.swift`

## How To Run

### Backend
```bash
docker-compose up -d
docker logs clavis-backend-1
```

### iOS
```bash
cd ios
xcodegen generate
xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build
```

### Tunnel
```bash
cloudflared tunnel run clavis-prod
```

## Current Gaps And Risks
- JWT payload decoding is used instead of full signature verification in the backend middleware.
- `SettingsView` exposes controls that are only partially supported by the backend.
- `summary_length` and `weekday_only` are sent by the iOS app but are not fully persisted by the current `/preferences` API.
- `SettingsView` calls `PATCH /preferences/alerts`, but there is no matching backend route in the current codebase.
- APNs requires valid Apple credentials and a real device token to work end to end.
- Price data depends on Polygon or Finnhub availability.
- Debug routes are present and should be treated as internal tooling.

## Important Files For Future Work
- `backend/app/main.py`
- `backend/app/pipeline/scheduler.py`
- `backend/app/pipeline/risk_scorer.py`
- `backend/app/pipeline/mirofish_analyze.py`
- `backend/app/routes/positions.py`
- `backend/app/routes/preferences.py`
- `ios/Clavis/Services/APIService.swift`
- `ios/Clavis/ViewModels/DigestViewModel.swift`
- `ios/Clavis/Views/PositionDetail/PositionDetailView.swift`

## One-Line Summary
Clavis turns a portfolio into a daily risk briefing: authenticate, analyze holdings, score downside risk, surface changes in a native iOS UI, and optionally push alerts when something matters.
