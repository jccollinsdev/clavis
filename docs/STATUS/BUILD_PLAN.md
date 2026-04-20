# Clavis — Full Build Plan
**Updated:** April 2026  
**Status:** Post-MVP, working core. Planning V2 + launch readiness.

---

## What Was Just Completed (this session)

| Change | File(s) |
|---|---|
| Removed MiroFish entirely — all major event analysis now runs on MiniMax permanently | `pipeline/major_event_analyzer.py` (new), `pipeline/mirofish_analyze.py` (deleted), `docker-compose.yml`, `config.py` |
| `summary_length` preference now applied to digest token budget (brief/standard/detailed) | `pipeline/portfolio_compiler.py`, `pipeline/scheduler.py` |
| `weekday_only` preference now honored — scheduler skips weekend runs if set | `pipeline/scheduler.py` |
| Removed mirofish Docker service from compose; backend no longer depends_on it | `docker-compose.yml` |
| Debug routes confirmed gated — require `subscription_tier = 'admin'` in DB | Already correct, no change needed |
| Onboarding flow confirmed complete — 4 steps (name, DOB, risk ack, preferences), saves to backend | Already correct |

---

## Current Working State

| Feature | Status |
|---|---|
| Auth (Supabase email/password) | ✅ |
| Holdings CRUD | ✅ |
| 17-stage analysis pipeline | ✅ |
| Major event analysis (MiniMax) | ✅ |
| Minor event analysis (MiniMax agentic scan) | ✅ |
| Risk scoring (4 dimensions + structural) | ✅ |
| Portfolio risk rollup | ✅ |
| Morning digest (MiniMax, respects summary_length) | ✅ |
| Price charts (Polygon, 7D/30D/90D) | ✅ |
| Dashboard, Digest, Alerts, Settings views | ✅ |
| Onboarding flow (4-step, name/DOB/risk/prefs) | ✅ |
| `weekday_only` digest scheduling | ✅ |
| Debug routes (admin-only) | ✅ |
| Push Notifications (APNs) | ❌ Waiting on Apple Dev account |

---

## Phase 1 — SnapTrade Integration (PRIORITY #1)

The docs explicitly call out brokerage connection as a V2 feature. SnapTrade provides OAuth-based read-only brokerage connections (Fidelity, Schwab, Robinhood, IBKR, etc.). This replaces manual position entry and is the biggest UX unlock before launch.

### What SnapTrade gives you
- OAuth connection to 30+ brokerages
- Real-time holdings sync (ticker, shares, cost basis)
- No manual entry after first connect

### Backend changes needed

**New route:** `POST /brokerage/connect` — returns a SnapTrade OAuth link  
**New route:** `GET /brokerage/status` — connection status + last sync time  
**New route:** `POST /brokerage/sync` — pull latest holdings from SnapTrade → upsert positions  
**New route:** `DELETE /brokerage/disconnect` — revoke SnapTrade access  
**New service:** `backend/app/services/snaptrade.py`
- SnapTrade user registration (one-time per Clavis user)
- Generate OAuth redirect link
- Exchange code for access token
- Fetch holdings → normalize to Clavis `positions` format

**Schema changes needed:**
- Add `brokerage_account_id`, `synced_from_brokerage`, `last_brokerage_sync` columns to `positions`
- Add `snaptrade_user_id`, `snaptrade_user_secret` to `user_preferences`

### iOS changes needed

**New onboarding step:** Between "preferences" and completion — offer "Connect your brokerage" or "I'll add manually". 
**New Settings section:** "Brokerage" — connected account info, sync now button, disconnect option.
**Holdings list:** Show sync badge on positions imported from brokerage. Show "synced X min ago" at top of list.

### Build order
1. Backend SnapTrade service + routes
2. Store credentials in `user_preferences`
3. Sync endpoint that upserts positions (archetype gets auto-inferred or defaults to "unknown")
4. iOS Settings → Brokerage section
5. Onboarding optional step
6. Background sync on app foreground (pull if > 4 hours since last sync)

---

## Phase 2 — APNs Push Notifications

Blocked on Apple Developer account ($99/year). Do this immediately after account is active.

### What's already built
- `services/apns.py` — APNs client with JWT auth
- `PushNotificationManager.swift` — permission request, token registration
- `POST /preferences/device-token` — token storage
- Alert generation in scheduler triggers push dispatch

### What's missing
- Valid `.p8` key from Apple Developer portal
- `APNS_KEY_ID`, `APNS_TEAM_ID` env vars
- Key file at `backend/apns/apns.p8`

### Steps (once Apple Dev account is active)
1. Create Push Notification key in Apple Developer portal
2. Download `.p8`, place at `backend/apns/apns.p8`
3. Set `APNS_KEY_ID` and `APNS_TEAM_ID` in `.env`
4. Run `POST /test-push` with a real device token to verify
5. Test alert → push flow end-to-end

---

## Phase 3 — Freemium / Subscription Gate

The product doc specifies a freemium model. This is the monetization layer.

### Tiers
| Tier | Holdings limit | Features |
|---|---|---|
| Free | 5 positions | Daily digest, A-F grade, top news, grade change alerts |
| Pro ($12/mo or $99/yr) | Unlimited | Full score breakdown, position detail, methodology, alert history |

### Backend changes
- `subscription_tier` column already exists in `user_preferences`
- Add enforcement middleware: check tier before returning full `position_analyses`, `event_analyses`, score breakdown
- New route: `POST /billing/portal` — Stripe customer portal redirect
- New route: `POST /billing/webhook` — Stripe webhook handler (subscription created/updated/cancelled)
- New service: `backend/app/services/stripe.py`

### iOS changes
- Paywall sheet — shown when free user tries to access Pro feature
- Settings → Subscription section (current tier, upgrade button, manage subscription)
- `StoreKit 2` for in-app purchase (or Stripe web checkout redirect)

### Build order
1. Stripe account setup + product/price creation
2. Backend billing service + webhook
3. Tier enforcement in `/positions/{id}` and `/digest` routes
4. iOS paywall UI
5. Settings subscription section

---

## Phase 4 — Launch Readiness

### App Store preparation
- [ ] App Store Connect account (requires Apple Dev account)
- [ ] App icon (1024×1024 required)
- [ ] Screenshots for 6.7" and 6.1" iPhone (required for submission)
- [ ] Privacy policy URL (required)
- [ ] App description + keywords
- [ ] TestFlight internal testing (5-10 people from personal circle)
- [ ] Bundle ID confirmed: `com.clavisdev.portfolioassistant`

### Backend hardening
- [ ] Remove `mirofish_analyze.py` pycache artifacts (handled by Docker rebuild)
- [ ] Add Sentry DSN for production error tracking (field exists in config)
- [ ] Rate limiting on `/trigger-analysis` (prevent spam runs)
- [ ] Add `PATCH /preferences` to update `summary_length` from iOS Settings (already works — confirm iOS is sending it)

### iOS polish
- [ ] Empty state for Digest view (first-time user with no analysis run yet)
- [ ] Better loading/error states across all views (network failures, timeout)
- [ ] Pull-to-refresh on Dashboard
- [ ] Haptic feedback on grade change alert tap
- [ ] App icon

---

## Phase 5 — Growth Features (Post-Launch)

These are explicitly V3+ in the product docs. Do not start until 20+ active daily users.

| Feature | Description | Complexity |
|---|---|---|
| **Watchlist UI** | Backend routes exist, just needs iOS screen + model | Low |
| **Portfolio risk drilldown** | Dedicated view for `portfolio_risk_snapshots` data | Medium |
| **Grade history chart** | Show how a position's grade drifted over time | Medium |
| **Background app refresh** | iOS BGProcessingTask to pre-load digest | Medium |
| **Web app** | Browser dashboard alongside iOS | High |
| **Multi-user / advisor sharing** | Share portfolios read-only | High |

---

## Build Order Summary

```
NOW (immediate):
  ✅ MiroFish → MiniMax (done)
  ✅ summary_length + weekday_only wired (done)
  ✅ docker-compose cleaned (done)

NEXT (1-2 weeks):
  → SnapTrade brokerage integration (backend + iOS)
  → iOS polish: empty states, error handling, loading states

THEN (once Apple Dev account active):
  → APNs end-to-end test

THEN (before public launch):
  → Stripe freemium gate
  → App Store assets + TestFlight
  → App icon

AFTER LAUNCH:
  → Watchlist UI
  → Portfolio risk drilldown
  → Grade history chart
```

---

## Key Decisions Locked

| Decision | Rationale |
|---|---|
| MiniMax for all AI (no MiroFish) | MiroFish was never implemented; MiniMax handles major events well enough at MVP |
| Supabase for auth + DB | RLS + Edge Functions reduce backend surface; no self-hosted auth needed |
| SnapTrade for brokerage | AGPL-clean, supports 30+ US brokerages, read-only OAuth |
| Stripe for billing | Industry standard, Stripe Tax handles compliance |
| No web app at launch | Mobile-only MVP; iOS is the core habit surface |
| Freemium with 5-position free tier | Gets real users in without asking for money upfront |
