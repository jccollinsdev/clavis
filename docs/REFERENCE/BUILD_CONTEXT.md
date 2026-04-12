# Clavis — Build Context

## What Was Built

### Backend (`/backend/`)
- **Framework:** FastAPI (Python) running in Docker
- **Location:** Desktop/Clavis/backend/ (volume-mounted to container at /app/app/)

### Infrastructure
- **Database:** Supabase PostgreSQL — project `uwvwulhkxtzabykelvam`
- **Auth:** Supabase Auth (email/password) — JWT tokens with `sub` claim as user_id
- **AI:** MiniMax M2.7 via `app/services/minimax.py` — uses thinking-tag stripping (MiniMax puts reasoning in `<think>...</think>` tags, content ends up empty when `reasoning_split=True`; we strip the tags and use content directly)
- **Container:** Docker container named `clavis-backend-1`

### API Endpoints
All require `Authorization: Bearer <jwt>` header except `/health`.

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/holdings` | GET | List positions with current risk_grade + total_score |
| `/holdings` | POST | Add position |
| `/holdings/:id` | DELETE | Delete position |
| `/positions/:id` | GET | Position detail with score breakdown, recent news, alerts |
| `/digest` | GET | Today's compiled digest |
| `/alerts` | GET | Recent grade-change and major-event alerts |
| `/preferences` | GET | User preferences (digest_time, notifications_enabled) |
| `/preferences` | PATCH | Update preferences (reschedules user's cron job) |
| `/trigger-analysis` | POST | Manually trigger full pipeline run |

### News Pipeline (`/app/pipeline/`)
Runs in sequence: RSS → Finnhub → relevance → classifier → agentic scan → risk scorer → compiler → Supabase

1. **RSS** (`rss_ingest.py`) — Bloomberg, NYTimes, FT markets feeds
2. **Finnhub** (`finnhub_news.py`) — company news + market news
3. **Relevance** (`relevance.py`) — filters to tickers in user's portfolio
4. **Classifier** (`classifier.py`) — MAJOR vs MINOR classification via MiniMax
5. **Agentic Scan** (`agentic_scan.py`) — position-aware analysis of minor events
6. **Risk Scorer** (`risk_scorer.py`) — 5-dimension scoring, A-F grade
7. **Compiler** (`compiler.py`) — digest generation in plain English
8. **Scheduler** (`scheduler.py`) — per-user cron jobs via APScheduler

MiroFish (`mirofish_analyze.py`) is bypassed — returns null, pipeline handles gracefully.

### iOS App (`/ios/`)
- **Framework:** SwiftUI
- **Project:** `Clavis.xcodeproj` (generated via XcodeGen from `project.yml`)
- **Bundle ID:** `com.clavisdev.portfolioassistant`
- **Screens:** Dashboard, Holdings (list + add/delete), Digest, Alerts, Settings
- **Auth:** Supabase email/password via `SupabaseAuthService`
- **Config:** `APIService.swift` — `backendBaseUrl` must match cloudflare tunnel URL

## Known Issues

### Critical
- **Cloudflare tunnel URL changes on restart** — quick tunnels are ephemeral. For production, need a named tunnel via `cloudflared login`.

### V2 Deferred

1. **Price charts** — Polygon.io key is configured but `current_price` is never fetched. Need:
   - A `prices` table (ticker, price, fetched_at)
   - A price-fetching step in the pipeline
   - `Position.currentPrice` populated from latest price

2. **News items persistence** — `news_items` table exists but pipeline never writes to it. Position detail's "Recent News" section stays empty.

3. **Push notifications** — `notifier.py` is a stub. Need:
   - APNs certificate setup
   - iOS: `PushNotificationManager.swift` to request + store token
   - Backend: send via APNs when digest generated

4. **Named Cloudflare tunnel** — quick tunnel at `https://requested-tagged-sue-residential.trycloudflare.com` (valid as of last run). To persist:
   ```
   cloudflared tunnel --url http://localhost:8000
   ```
   Or use named tunnel with `cloudflared login`.

5. **MiroFish integration** — `mirofish_analyze.py` is a bypass stub. Pipeline already handles null return.

6. **MiniMax prompt tuning** — M2.7 is verbose; classifier ~80-100% accurate. Prompts in `classifier.py`, `agentic_scan.py`, `risk_scorer.py`, `compiler.py` may need Day 7-style refinement for more concise outputs.

7. **In-app polling** — digest refreshes on pull but no background fetch. Silent push needed for real-time.

## Day 7 Dogfood Results

**Positions (real user `90b7281c-0015-49de-a657-587bb25fbc6c`):**
| Ticker | Shares | Purchase | Archetype | Grade | Score |
|---|---|---|---|---|---|
| PG | 18 | $168 | defensive | A | 82.5 |
| AAPL | 25 | $188.50 | value | B | 71.0 |
| JPM | 20 | $195 | cyclical | C | 54.8 |
| MSFT | 15 | $415 | growth | C | 50.0 |

**Digest quality:** Plain English, actionable advice, grade changes flagged correctly.

## Files Modified During Build

### Backend Key Files
- `app/services/minimax.py` — thinking-tag stripping, default max_tokens=1000
- `app/pipeline/classifier.py` — max_tokens 100→1000
- `app/pipeline/agentic_scan.py` — max_tokens 300→1500
- `app/pipeline/risk_scorer.py` — max_tokens 500→1500, grade always from `score_to_grade()`
- `app/pipeline/compiler.py` — max_tokens 600→1500
- `app/pipeline/scheduler.py` — per-user cron scheduling
- `app/routes/holdings.py` — joins risk_scores for grade/score
- `app/routes/alerts.py` — new endpoint
- `app/routes/preferences.py` — new endpoint
- `app/routes/trigger.py` — fixed FastAPI dependency injection
- `app/main.py` — registered new routers

### iOS Key Files
- `Services/APIService.swift` — backend URL, preferences API
- `ViewModels/SettingsViewModel.swift` — new
- `Views/Settings/SettingsView.swift` — wired to ViewModel
- `Views/Dashboard/DashboardView.swift` — grade change arrows
- `Models/Position.swift` — added previousGrade field

## To Restart Backend
```bash
docker restart clavis-backend-1
```

## To Restart Cloudflare Tunnel
```bash
cloudflared tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
# Check URL:
grep trycloudflare /tmp/cloudflared.log
```

## To Rebuild iOS
```bash
cd ~/Documents/Clavis/ios
xcodegen generate
xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build
```
