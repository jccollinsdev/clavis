# AGENTS.md

**Read this first. Every session.**

## Session Memory

Read these files in this order at the start of every session:

1. `AGENTS.md`
2. `docs/CLAVIX_TRUTH.md`
3. `docs/REFACTOR_PLAN.md`

This is the master instruction file for AI agents (Claude, Cursor, Copilot, anything) working on Clavix. If you only read one file, read this one — and follow the links.

---

## STOP — Read These First

Before writing a single line of code, you must read:

1. **This file (AGENTS.md)** — context, operational commands, rules
2. **`docs/CLAVIX_TRUTH.md`** — the canonical source of truth for what Clavix is, who it's for, and how it works. **If anything anywhere else contradicts CLAVIX_TRUTH.md, CLAVIX_TRUTH.md is correct.**
3. **`docs/REFACTOR_PLAN.md`** — the active refactor plan (current phase, what's in scope right now, what's deferred)

You do NOT need to read:
- Anything in `docs/_archive/` — these are historical, kept for reference only
- Anything that contradicts `CLAVIX_TRUTH.md` — it's wrong
- Status docs older than 7 days — assume superseded unless cited from `REFACTOR_PLAN.md`

---

## What Is Clavix

**Clavix is a portfolio risk intelligence app for self-directed investors managing $500K-$5M+.**

It tells users what changed in their portfolio overnight (macro → sector → individual positions), assigns a bond-rating-style risk grade (AAA to F) to every tracked stock, and shows the full methodology behind every score.

**Tone:** credit-rating agency, not a research analyst. Calm, precise, observational.

**Mental model:** Bloomberg Terminal compressed into a daily morning briefing.

**Banned strings in user-visible UI:** "Clavis" (use "Clavix"), "SnapTrade" (say "your brokerage"), "shared ticker cache" (say "ticker data"), backend status strings via `.capitalized`.

For the full product spec, ICP, methodology, tier split, and roadmap → **`docs/CLAVIX_TRUTH.md`**.

---

## Identity & Naming

| Surface | Name |
|---|---|
| User-visible everywhere | **Clavix** |
| Legal entity | Andover Digital LLC |
| Internal Swift types | `Clavis*` (no rename) |
| Backend API domain | `clavis.andoverdigital.com` |
| Marketing site | `getclavix.com` |
| iOS bundle ID | `com.clavisdev.portfolioassistant` |
| iOS display name | `Clavix` |
| Container | `clavis-backend-1` |
| URL scheme | `clavix://` (canonical) + `clavis://` (legacy compat) |

**The rule:** anything user-visible says "Clavix". Anything internal-only can stay "Clavis*".

---

## Architecture at a Glance

```
[iOS App (SwiftUI)]
       |
       | HTTPS + JWT (Supabase auth)
       v
[Cloudflare Tunnel: clavis.andoverdigital.com]
       |
       v
[VPS: DigitalOcean Ubuntu 24.04]
       |
       +-- [Docker: clavis-backend-1 (FastAPI on :8000)]
       |       |
       |       +-- APScheduler (in-process cron)
       |       +-- MiniMax LLM (sk-cp- key)
       |       +-- Polygon + Finnhub (market data)
       |       +-- Google News RSS + Jina Reader (news)
       |       +-- SnapTrade (brokerage sync)
       |       +-- APNs (push)
       |
       +-- [cloudflared (systemd service)]
       |
[Supabase Postgres 17.6 (us-west-1)]
       |
       +-- 25 tables
       +-- RLS policies
       +-- One Edge Function (register-device, currently bypassed)
```

**Tech stack:**
- Backend: FastAPI 0.109.2 on Python 3.11
- iOS: SwiftUI, deployment target iOS 17, Swift 5.9, XcodeGen
- DB: Supabase Postgres 17
- Auth: Supabase Auth (email/password; no SSO yet)
- Hosting: DigitalOcean Droplet (Ubuntu 24.04) at `134.122.114.241`
- Reverse proxy: Cloudflare Tunnel (`cloudflared`), no nginx
- CI: GitHub Actions (`backend-ci.yml`, `deploy-prod.yml`)
- Background jobs: APScheduler (in-process, NOT Celery/Redis)

---

## Repository Layout

```
/Users/sansarkarki/Documents/Clavis/   (local dev)
/opt/clavis/                            (VPS production)

├── backend/                            FastAPI service
│   ├── app/
│   │   ├── main.py                     entry point, lifespan, JWT middleware
│   │   ├── config.py                   BaseSettings env reader
│   │   ├── routes/                     all FastAPI route modules
│   │   ├── services/                   external integrations + helpers
│   │   ├── pipeline/                   analysis/scoring/digest pipeline
│   │   └── models/                     pydantic DTOs
│   ├── apns/                           APNs key (.p8) — VPS only, gitignored
│   ├── tests/                          pytest suite
│   ├── scripts/                        one-off scripts (sp500_precompute, etc.)
│   ├── Dockerfile
│   ├── requirements.txt                (no lock file currently)
│   └── .env                            local secrets (gitignored)
│
├── ios/                                SwiftUI iOS app
│   ├── Clavis/                         (internal name — do NOT rename)
│   │   ├── App/                        app shell, design system
│   │   ├── Config/                     xcconfig (CONTAINS REAL ANON KEY — to fix)
│   │   ├── Models/                     DTO layer
│   │   ├── Services/                   API client, auth, push
│   │   ├── ViewModels/                 MVVM state
│   │   ├── Views/                      screens
│   │   └── Resources/                  Info.plist, fonts, assets
│   ├── Clavis.xcodeproj/               generated by xcodegen
│   └── project.yml                     XcodeGen spec
│
├── supabase/
│   ├── migrations/                     SQL migrations (32 applied)
│   └── functions/register-device/      Edge Function (deployed but bypassed)
│
├── docs/
│   ├── CLAVIX_TRUTH.md                 ★ THE source of truth
│   ├── REFACTOR_PLAN.md                ★ active refactor sequence
│   ├── PUBLIC/methodology.md           public methodology (mirrored to web)
│   └── _archive/                       old docs, do not read
│
├── scripts/                            local dev helpers
├── docker-compose.yml                  local stack
└── .github/workflows/                  CI/CD
```

---

## VPS Operations

### SSH Access

```bash
# SSH to production VPS
ssh -i ~/.ssh/clavix_vps_ed25519 clavix-backend@134.122.114.241

# If you don't have the key yet, ask Bipul. It's not in the repo.
# The key is the only auth method — password auth is disabled.
```

### Inside the VPS

```bash
# Working directory for the deployed app
cd /opt/clavis

# View running containers
docker ps

# Backend container name: clavis-backend-1
docker logs clavis-backend-1 --tail 100
docker logs clavis-backend-1 --tail 100 -f       # follow

# Restart backend
docker restart clavis-backend-1

# Rebuild + restart (after code change)
cd /opt/clavis && docker compose up -d --build --remove-orphans

# View backend env (do NOT cat — it has secrets)
sudo nano /opt/clavis/backend/.env

# Health check from VPS
curl http://127.0.0.1:8000/health

# Health check from outside (through Cloudflare)
curl https://clavis.andoverdigital.com/health
```

### Cloudflare Tunnel

The tunnel is a systemd service. It routes `clavis.andoverdigital.com` → `localhost:8000`.

```bash
# Status
sudo systemctl status cloudflared

# Restart
sudo systemctl restart cloudflared

# Logs
sudo journalctl -u cloudflared -f

# Config location
cat /etc/cloudflared/config.yml
```

The tunnel name is `clavis-prod`. Do NOT rename it. SnapTrade and DNS are all keyed to it.

### Crontab / scheduled jobs

There are NO OS-level crontab entries for `clavix-backend`. All scheduling is **APScheduler in-process** inside the FastAPI container. Job state persists in the `scheduler_jobs` Postgres table.

If the container restarts, APScheduler reloads jobs from the DB on lifespan startup.

---

## Local Development

### Backend (Mac/Linux)

```bash
cd ~/Documents/Clavis

# Start the local stack
docker-compose up -d

# Logs
docker logs clavis-backend-1 -f

# Restart
docker restart clavis-backend-1

# The local backend listens on http://127.0.0.1:8000
# It uses backend/.env for secrets (gitignored, ask Bipul)
```

### Local backend env vars

The full list is in `docs/CLAVIX_TRUTH.md` and `backend/.env.example`. Critical ones:

```
SUPABASE_URL=https://uwvwulhkxtzabykelvam.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<get from Bipul>
SUPABASE_JWT_SECRET=<get from Bipul>
MINIMAX_API_KEY=sk-cp-<rest>
MINIMAX_BASE_URL=https://api.minimax.io/v1
POLYGON_API_KEY=<get from Bipul>
FINNHUB_API_KEY=<get from Bipul>
SNAPTRADE_CLIENT_ID=<get from Bipul>
SNAPTRADE_CONSUMER_KEY=<get from Bipul>
SNAPTRADE_REDIRECT_URI=clavix://snaptrade/callback
APNS_KEY_ID=<get from Bipul, prod only>
APNS_TEAM_ID=<get from Bipul, prod only>
APNS_KEY_PATH=apns/apns.p8
APNS_BUNDLE_ID=com.clavisdev.portfolioassistant
ADMIN_PASSWORD=<get from Bipul>
ADMIN_SESSION_SECRET=<get from Bipul>
SENTRY_DSN=<get from Bipul, prod only>
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://getclavix.com
ENABLE_PUBLIC_DOCS=false
ENABLE_DEBUG_SURFACES=false
PAUSE_SYSTEM_SCHEDULER=false
```

### iOS (Mac only)

```bash
cd ~/Documents/Clavis/ios

# Regenerate Xcode project from project.yml
xcodegen generate

# Build for simulator
xcodebuild -scheme Clavis -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17' build

# Open in Xcode for hands-on testing
open Clavis.xcodeproj
```

The iOS scheme is `Clavis` (internal name). The display name on a phone is `Clavix`. Both are correct.

### Local DB (none)

There is no local Postgres. Local backend hits the same Supabase project that production hits. **Be careful when testing destructive operations locally — they hit prod data.** The current 4 auth users / 3 preference rows are test accounts and are disposable per the user's directive.

---

## Branch & Deploy Workflow

### Branches

- **`main`** = production. Pushes deploy to VPS via GitHub Actions.
- **`develop`** = day-to-day integration. Merge to `main` to deploy.
- Feature branches off `develop`. PR back to `develop`.

### Deploy to production

```bash
# From local
git checkout develop
# ... do work, commit ...
git checkout main
git merge develop
git push origin main

# Watch the deploy
# https://github.com/<your-org>/clavis/actions
```

The deploy workflow (`.github/workflows/deploy-prod.yml`):
1. SSHs to VPS as `clavix-backend@134.122.114.241`
2. rsyncs the repo to `/opt/clavis/`
3. Runs `docker compose up -d --build --remove-orphans`
4. Verifies `curl http://127.0.0.1:8000/health` returns ok

### Required GitHub secrets

- `PROD_SSH_KEY` (private key for the deploy SSH user)
- `PROD_SSH_HOST` (134.122.114.241)
- `PROD_SSH_USER` (clavix-backend)
- Plus all the API keys for CI tests (see `.github/workflows/backend-ci.yml`)

### What does NOT auto-deploy

- The `ios/` directory (iOS app deploys via TestFlight / App Store, not via this pipeline)
- The marketing site at getclavix.com (separate repo / hosting)
- Supabase migrations (run manually via Supabase CLI or dashboard)
- Cloudflare tunnel config (managed via Cloudflare dashboard)
- VPS-only files: `backend/.env`, `backend/apns/apns.p8`

---

## Database & Migrations

### Connection

- **Provider:** Supabase
- **Project ref:** `uwvwulhkxtzabykelvam`
- **Region:** us-west-1
- **Postgres version:** 17.6.1.104

### Migrations

- Live in `supabase/migrations/`
- Applied via Supabase CLI or dashboard
- 32 currently applied

**Important:** the live DB schema has drifted ahead of the repo migrations. The repo has 20 migration files but the live DB has 32 applied records. Treat the live DB schema as authoritative until the refactor reconciles them.

### Critical schema notes

- **Three overlapping news stores exist:** `news_items`, `ticker_news_cache`, `shared_ticker_events`. The refactor consolidates to **only `shared_ticker_events`** (see `REFACTOR_PLAN.md`).
- **Two parallel scoring stores exist:** `risk_scores` (user-scoped) and `ticker_risk_snapshots` (ticker-scoped). The refactor keeps **only `ticker_risk_snapshots`**.
- **Backup tables `event_analyses_backup_20260504` and `position_analyses_backup_20260504`** are in the public schema with RLS disabled. They will be dropped in the refactor.
- **Legacy columns** to drop (in refactor): `risk_scores.thesis_integrity`, `risk_scores.grade_reason`, `risk_scores.mirofish_used`, `position_analyses.top_news`, `asset_safety_profiles` (entire table), `recommended_followups` columns.

### RLS policies

All user-scoped tables use Row-Level Security keyed off `auth.uid()`. The `prices` table was recently fixed (was SELECT-all-ops, now SELECT-only). Always verify RLS when adding new tables.

### `SECURITY DEFINER` functions

`save_daily_asset_safety_profile` and `save_daily_macro_regime` are `SECURITY DEFINER` and currently executable by `anon` and `authenticated`. **This is a security finding to fix in the refactor.** Don't add new SECURITY DEFINER functions without explicit review.

---

## API Authentication

### App API (everything except `/admin/*`)

```
Authorization: Bearer <Supabase JWT>
```

The middleware in `backend/app/main.py` verifies the JWT using `SUPABASE_JWT_SECRET` (local decode), with fallback to `supabase.auth.get_user(token)`.

There is a `backend/app/auth.py` file with duplicate helpers (`validate_jwt`, `optional_jwt`) — **dead code, do not use**. Will be deleted in refactor.

### Admin API (`/admin/*`)

Separate auth — password login at `/admin/login`, sets a signed cookie `clavis_admin_session`. CSRF protection via cookie + header.

The admin HTML shell at `/admin` is currently publicly reachable. **This needs to go behind Cloudflare Access before launch.**

### Admin tier

Some JWT routes additionally require `subscription_tier == 'admin'` via `backend/app/services/access_control.py`. This is for things like S&P seed/backfill triggers and debug surfaces.

---

## API Endpoints (current)

All require `Authorization: Bearer <jwt>` unless noted.

```
GET    /health                              No auth. Returns service status.
GET    /dashboard                           Holdings + digest + alerts bundle
GET    /digest                              Today's digest
GET    /digest/history                      Historical digests
GET    /holdings                            List holdings
POST   /holdings                            Add holding
GET    /holdings/{id}                       Single holding
PATCH  /holdings/{id}                       Update holding
DELETE /holdings/{id}                       Delete holding
GET    /positions/{id}                      Position detail
POST   /trigger-analysis                    Manual analysis (3/day limit)
GET    /analysis-runs/latest                Latest run
GET    /analysis-runs/{id}                  Specific run
GET    /alerts                              Recent alerts
GET    /news                                News feed (UNUSED by current iOS)
GET    /news/{id}                           Article (UNUSED by current iOS)
GET    /preferences                         User preferences
PATCH  /preferences                         Update preferences
PATCH  /preferences/alerts                  Update alert prefs
POST   /preferences/acknowledge             Mark onboarding complete
POST   /preferences/device-token            Register APNs token
POST   /preferences/profile                 Update name/birth year
GET    /tickers/search                      Universe search
GET    /tickers/{ticker}                    Ticker detail
POST   /tickers/{ticker}/refresh            Manual refresh (Pro/admin)
GET    /tickers/{ticker}/refresh-status     Refresh job status
GET    /watchlists                          Default watchlist
POST   /watchlists/default/items            Add to watchlist
DELETE /watchlists/default/items/{ticker}   Remove from watchlist
GET    /brokerage/status                    SnapTrade state
POST   /brokerage/connect                   Hosted connect URL
PATCH  /brokerage/settings                  Update auto-sync
POST   /brokerage/sync                      Sync brokerage holdings
DELETE /brokerage/disconnect                Disconnect brokerage
GET    /prices/{ticker}                     Price history
GET    /account/export                      Export user data
DELETE /account                             Delete account
GET    /scheduler/status                    User scheduler status
GET    /scheduler/sp500/status              S&P cache status
POST   /scheduler/sp500/seed                Admin only
POST   /scheduler/sp500/backfill            Admin only
GET    /scheduler/sp500/backfill/{id}       Admin only
```

Plus admin web routes under `/admin/*` (cookie-auth) and debug routes under `/debug/*` (admin tier + ENABLE_DEBUG_SURFACES env flag).

---

## External Services & API Keys

| Service | Used for | Key location |
|---|---|---|
| Supabase | Auth, DB | `SUPABASE_*` env vars |
| MiniMax | LLM (digest, news sentiment, narratives) | `MINIMAX_API_KEY` (sk-cp-) |
| Polygon | Market data, prices, OHLC | `POLYGON_API_KEY` |
| Finnhub | Quotes, fundamentals, news | `FINNHUB_API_KEY` |
| SnapTrade | Brokerage sync | `SNAPTRADE_CLIENT_ID`, `SNAPTRADE_CONSUMER_KEY` |
| APNs | Push notifications | `APNS_KEY_ID`, `APNS_TEAM_ID`, `apns.p8` file |
| Sentry | Error monitoring | `SENTRY_DSN` |
| Google News RSS | News discovery | No key (RSS) |
| Jina AI Reader | Article body extraction | No key (free tier) |
| CNBC RSS | Macro/sector news | No key (RSS) |

**Rate limits to know:**
- MiniMax: 4500 requests / 5 hours, 45,000 / week
- Polygon: ~5 requests/minute on current plan
- Finnhub: 60 requests/minute
- Google News RSS: throttle yourself or you'll get blocked

The MiniMax client has a global `MINIMAX_MIN_INTERVAL_SECONDS` (default 1.25s). The Polygon client has 20-second global spacing. Don't bypass these.

---

## Background Jobs (APScheduler)

All scheduled in `backend/app/pipeline/scheduler.py`. Started in FastAPI lifespan.

```
07:00 ET — Holdings daily AI refresh
07:30 ET — S&P 500 backfill
08:00 ET — S&P 500 daily refresh
08:30 ET — News cleanup
Per-user — Digest generation at user's preferred time
```

Job state persists in `scheduler_jobs` table. On container restart, jobs reload from DB.

To pause all system scheduled runs, set env var `PAUSE_SYSTEM_SCHEDULER=true` and restart container.

---

## How to Test

### Backend tests

```bash
cd backend
pytest                      # full suite
pytest tests/test_<file>    # specific file
pytest -k <pattern>         # match test name
pytest -x                   # stop on first failure
pytest -v                   # verbose
```

The test suite has ~30 files. CI runs all of them on every push.

### iOS tests

iOS has no real test suite yet. Build verification only:

```bash
cd ios
xcodebuild -scheme Clavis -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

Manual test on simulator after every meaningful UI change.

### Smoke test against prod

```bash
curl https://clavis.andoverdigital.com/health
# should return {"status":"ok", ...}
```

---

## Coding Rules

### Always

- **Read `CLAVIX_TRUTH.md` first** when making product/feature decisions. If your instinct contradicts it, the doc is right.
- **Prefer the smallest correct change.** Don't refactor adjacent code unless the refactor plan says to.
- **Keep secrets out of source.** All secrets live in `backend/.env`, the VPS `.env`, or GitHub Actions secrets. Never commit a `.p8`, never commit an API key, never commit a JWT secret.
- **Update RLS** when you add a user-scoped table. Default-deny, then add explicit policies.
- **Sanitize text fields.** All user-displayable strings from external sources go through `sanitize_text_field()` in `backend/app/pipeline/analysis_utils.py`. This strips HTML, JSON-LD, code-like content.
- **Use canonical naming.** "Clavix" everywhere user-visible. Banned strings list above.
- **Cite the source of truth in PR descriptions.** "Per CLAVIX_TRUTH §6, the methodology is..."

### Never

- **Don't write to `news_items` or `ticker_news_cache`.** They're being retired. Write only to `shared_ticker_events`.
- **Don't write to `risk_scores`.** It's being retired. Write only to `ticker_risk_snapshots`.
- **Don't fabricate previous scores or grade deltas.** If history is empty, show "—" or "New". The legacy `estimatedPreviousScore` (current - 8) and `previousScore(for:)` (A=83, B=65, ...) patterns are BANNED.
- **Don't use `.capitalized` on backend status strings in the UI.** Map states explicitly via `ClavisCopy.statusLabel(for:)`.
- **Don't show backend implementation terms to users.** No "SnapTrade", "shared ticker cache", "queued/running", "analysis run". Use user-facing copy.
- **Don't expose `/admin` HTML shell publicly.** It's behind Cloudflare Access (or will be). Don't add new routes under `/admin/*` without admin auth.
- **Don't add new `SECURITY DEFINER` functions** without explicit review.
- **Don't rename Swift types from `Clavis*` to `Clavix*`.** That refactor is too risky for the timeline. Internal naming stays.
- **Don't add features not in `CLAVIX_TRUTH.md` §16-19.** If it's "Out of scope" or "v1.5", it doesn't go in v1.

---

## Common Pitfalls (from the audit)

1. **`/dashboard` vs `/digest`** — the iOS DigestView currently calls `/dashboard`, not `/digest`. The refactor will fix this. Until then, both endpoints return overlapping data and you might modify the wrong one.

2. **`mirofish_used_this_cycle`** — dead field still in API response and iOS decode. Drop it; don't propagate it.

3. **`mirofish/` directory** — abandoned sidecar service. Not in `docker-compose.yml`. Not running. Don't add code to it.

4. **`render.yaml`** — defined but unused. Production is DigitalOcean, not Render. Don't update it.

5. **`backend/app/auth.py`** — duplicate of the JWT middleware. Dead. Don't import it.

6. **Real `SUPABASE_ANON_KEY` is in `ios/Clavis/Config/Secrets.xcconfig`** which is tracked. Anon keys are technically public-facing but this still violates the "no secrets in tracked files" rule. The refactor will template this and inject via xcconfig template + CI.

7. **Empty `shared_ticker_events`** — the table exists but currently has 0 rows. The refactor populates it from `ticker_news_cache` + `news_items` and switches all reads/writes.

8. **Empty `macro_regime_snapshots`** — table exists, 0 rows. Will be populated by the new macro narrative pipeline.

---

## When You Get Stuck

In this order:

1. **Re-read `CLAVIX_TRUTH.md`.** Most "what should this do" questions are answered there.
2. **Re-read `REFACTOR_PLAN.md`.** Most "should I do this now or later" questions are answered there.
3. **Check the audit findings** in `docs/_archive/AUDIT.md` for known gotchas.
4. **Search the codebase** before assuming something doesn't exist. Use `rg` (ripgrep) — fast.
5. **Check the live DB** if a schema question — the live schema is ahead of the migration files.
6. **Ask Bipul.** When in doubt about a product decision, the truth doc + Bipul's call beats your instinct.

---

## Session Workflow

1. Read AGENTS.md (this file)
2. Read CLAVIX_TRUTH.md
3. Read REFACTOR_PLAN.md (current phase, blockers, next actions)
4. Pull latest from `develop`
5. Branch: `git checkout -b <type>/<short-description>` where type ∈ {feat, fix, refactor, chore, docs}
6. Code — smallest correct change
7. Run `pytest` for backend changes; `xcodebuild build` for iOS changes
8. Commit with descriptive message; cite `CLAVIX_TRUTH §X` if a product decision
9. Push, open PR to `develop`
10. After merge to `develop`, you can later merge `develop` → `main` to deploy

---

## Quick Reference Cheatsheet

```bash
# === Local dev ===
cd ~/Documents/Clavis
docker-compose up -d
docker logs clavis-backend-1 -f
docker restart clavis-backend-1

# === iOS ===
cd ios && xcodegen generate
xcodebuild -scheme Clavis -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
open Clavis.xcodeproj

# === SSH to prod ===
ssh -i ~/.ssh/clavix_vps_ed25519 clavix-backend@134.122.114.241

# === On VPS ===
cd /opt/clavis
docker logs clavis-backend-1 --tail 100 -f
docker restart clavis-backend-1
docker compose up -d --build --remove-orphans
sudo systemctl status cloudflared
sudo systemctl restart cloudflared

# === Health checks ===
curl http://127.0.0.1:8000/health           # local or on VPS
curl https://clavis.andoverdigital.com/health  # public

# === Tests ===
cd backend && pytest
cd backend && pytest -x -v -k <pattern>

# === Deploy ===
git checkout main && git merge develop && git push origin main
# Then watch GitHub Actions

# === DB ===
# Supabase dashboard: https://supabase.com/dashboard/project/uwvwulhkxtzabykelvam
# Connection details: backend/.env
```

---

## Document Control

This file is the operational entry point for AI agents. Keep it current.

When you make a meaningful change to operations (new env var, new service, new domain, etc.), update this file in the same PR.

When you make a meaningful change to product (new feature, scope change, methodology tweak), update `CLAVIX_TRUTH.md`, NOT this file.

When in conflict between this file and `CLAVIX_TRUTH.md`: **CLAVIX_TRUTH.md wins** for product/methodology, **AGENTS.md wins** for operations.
