# Clavis — Portfolio Intelligence App

## Overview
Daily risk intelligence for self-directed investors. Monitors holdings, filters news, scores downside risk (A-F grades), alerts on changes.

**Backend:** FastAPI (Python) in Docker container `clavis-backend-1`
**iOS:** SwiftUI app (`~/Documents/Clavis/ios/`)
**Database:** Supabase PostgreSQL with RLS

## Quick Start

### Backend
```bash
cd ~/Documents/Clavis
docker-compose up -d          # Start
docker logs clavis-backend-1  # View logs
docker restart clavis-backend-1 # Restart
```

### iOS
```bash
cd ~/Documents/Clavis/ios
xcodegen generate
xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build
```

## Cloudflare Tunnel (PERSISTENT)
```bash
cloudflared tunnel run clavis-prod
```
**URL:** https://clavis.andoverdigital.com

## API Keys (in backend/.env)
- **Polygon:** `ZhzOMxq5CHtYnTM6PHpmSvgSJydDlox9`
- **Finnhub:** `d794qehr01qp0fl76degd794qehr01qp0fl76df0`
- **MiniMax:** AI analysis
- **Supabase:** Project credentials

## API Endpoints
All require `Authorization: Bearer <jwt>` header.

| Endpoint | Method | Description |
|---|---|---|
| `/holdings` | GET/POST | List/add positions |
| `/holdings/{id}` | DELETE | Delete position |
| `/positions/{id}` | GET | Position detail + score |
| `/digest` | GET | Today's digest |
| `/alerts` | GET | Grade change alerts |
| `/preferences` | GET/PATCH | User settings |
| `/trigger-analysis` | POST | Run analysis |

## Database Tables
- `positions` — user holdings (ticker, shares, price, archetype)
- `risk_scores` — historical scores per position
- `news_items` — filtered relevant news
- `digests` — compiled morning digests
- `alerts` — grade change notifications
- `user_preferences` — digest time, notifications

## News Pipeline
RSS → Finnhub → relevance filter → classifier → agentic scan → risk scorer → compiler → Supabase

## V2 Deferred
- Price charts visualization
- Push notifications (APNs)
- MiroFish swarm analysis
- Background polling
