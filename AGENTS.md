# Clavis — Portfolio Intelligence App

## Overview
Daily risk intelligence for self-directed investors. Monitors holdings, filters news, scores downside risk (A-F grades), alerts on changes.

## Session Memory — Read First

**At the start of every session, read these three files in order:**

1. `AGENTS.md` — this file (context, routes, credentials)
2. `docs/STATE/project_state.md` — current phase, blockers, active work, recent completions
3. `docs/STATUS/roadmap.md` — full 11-phase plan and launch principles

**For a manual bootstrap**, run: `bash scripts/session-start.sh`

Keep `docs/STATE/project_state.md` current. Whenever the active phase, blockers, or current focus changes, update that file in the same change set. Use the `project-memory` skill to enforce this workflow.

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

## Deployment Workflow
- `develop` is the day-to-day integration branch for backend work.
- `main` is production; merging or pushing to `main` deploys the DigitalOcean droplet.
- The droplet is prod-only. Do not edit code there by hand unless you are debugging an outage.
- Production deploys sync the repo into `/opt/clavis`, then run `docker compose up -d --build`.
- Keep secrets only on the VPS: `backend/.env`, `backend/apns/apns.p8`, and Cloudflare tunnel credentials.
- Production ports should stay localhost-only; Cloudflare Tunnel is the public entrypoint.
- For fast iteration, develop locally with the same compose stack and promote changes from `develop` to `main`.

## API Keys (in backend/.env)
- **Polygon:** keep in local secret storage / `backend/.env`
- **Finnhub:** keep in local secret storage / `backend/.env`
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
