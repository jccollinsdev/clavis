# Clavis

**Portfolio risk intelligence for self-directed investors.**

Clavis monitors your holdings, filters relevant news, and scores downside risk using letter grades (A–F). The app describes what's happening in your portfolio — it does not tell you what to do.

> Clavis is a portfolio risk data platform. It provides informational model outputs only, not investment advice.

---

## Status

**Currently in:** Phase 2 — Legal Documents, Onboarding, and Public Trust Surface

**Gate 0 blockers remaining before launch can proceed:**
- Paid Apple Developer account
- App Store Connect setup
- RevenueCat setup
- Business entity and banking
- SnapTrade developer application and approval

---

## Progress

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
| Methodology page | 🔄 Pending |
| Onboarding UX refinement | 🔄 In Progress |

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

---

## Project Structure

```
Clavis/
├── backend/            # FastAPI backend (Docker)
├── ios/                # SwiftUI iOS app
├── docs/
│   ├── STATE/          # Project state
│   └── STATUS/         # Roadmap
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
