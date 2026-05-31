# CLAUDE.md — Clavix Project

**Read this before every session.**  
This file is the operational ground truth for Claude sessions on this codebase. It supersedes any conflicting instructions that appear elsewhere.

---

## VPS SSH Access — Clavix Backend

The production DigitalOcean VPS is accessed through a non-root SSH user.

- **Host alias:** `clavix-vps`
- **IP:** `134.122.114.241`
- **User:** `sansar`
- **Local SSH key:** `~/.ssh/id_ed25519`
- **Do NOT use `root@134.122.114.241`** — root SSH login is disabled. Any session that tries `root@...` will always fail.
- Use `sudo -n` for root-level commands (non-interactive, no password prompt).

### Recommended local SSH config (`~/.ssh/config`)

```sshconfig
Host clavix-vps
  HostName 134.122.114.241
  User sansar
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
```

### Verify connection

```bash
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes sansar@134.122.114.241 'sudo -n whoami'
# Expected: root
```

Or once SSH config is written:

```bash
ssh clavix-vps 'sudo -n whoami'
# Expected: root
```

### Production app structure on VPS

```
/opt/clavis/          # app root (git repo clone)
docker compose        # backend container management
```

Key commands:

```bash
ssh clavix-vps 'cd /opt/clavis && sudo -n git pull origin main && sudo -n docker compose restart clavis-backend'
ssh clavix-vps 'sudo -n docker logs clavis-backend-1 --tail 50'
ssh clavix-vps 'sudo -n docker exec clavis-backend-1 python -m app.scripts.verify_data_truth'
```

### SSH troubleshooting

If SSH fails unexpectedly:

```bash
ssh clavix-vps 'systemctl status ssh --no-pager -l'
ssh clavix-vps 'ss -tlnp | grep :22'
ssh clavix-vps 'sudo -n fail2ban-client status sshd'
```

**Never rebuild/destroy the Droplet as part of normal debugging.**

---

## Backend Deployment

- Backend runs on the DigitalOcean VPS via **Docker Compose** — NOT Render.
- The repo has a `render.yaml` kept only for the static `clavis-web` email-confirm page. The `clavis-backend` block was removed. Never push expecting Render to deploy the backend.
- Deploy:

  ```bash
  ssh clavix-vps 'cd /opt/clavis && sudo -n git pull origin main && sudo -n docker compose restart clavis-backend'
  ```

- Post-deploy verify:

  ```bash
  curl -s https://clavis.andoverdigital.com/health
  ssh clavix-vps 'sudo -n docker exec clavis-backend-1 python -m app.scripts.verify_data_truth'
  ```

---

## Product Source of Truth

`docs/CLAVIX_TRUTH.md` (v2.1) — read it before making any product/copy/scoring decisions.  
`docs/CLAVIX_LAUNCH_SCOPE_v1.md` — v1 brokerage deferral + revised Free/Pro split.

Key rules:
- User-visible name: **Clavix** everywhere. Internal type names (`ClavisApp`, `ClavisDesignSystem`) are fine.
- Brokerage/SnapTrade is **deferred to post-v1**. `FeatureFlags.brokerageEnabled = false` in `ios/Clavis/App/ClavisCopy.swift`. Do not expose any brokerage CTA.
- Five risk dimensions exactly: **Financial Health, News Sentiment, Macro Exposure, Sector Exposure, Volatility**.
- Grade scale: AAA/AA/A/BBB/BB/B/CCC/CC/C/F (bond-rating, not A–F school grades).
- No buy/sell recommendations, price predictions, or investment advice — anywhere.

---

## Project Layout

```
ios/Clavis/              iOS SwiftUI app (Xcode scheme: Clavis, iPhone 17 sim)
backend/app/             FastAPI backend
  routes/                API route handlers
  services/              Business logic, data fetch
  pipeline/              News ingestion, scoring, digest generation
  jobs/                  Scheduled job runners
  scripts/               Verify/health scripts
docs/                    Audit reports, truth docs, plans
  CLAVIX_TRUTH.md        Source of truth (v2.1)
  CLAVIX_LAUNCH_SCOPE_v1.md  v1 scope decisions
  audits/                Full audit reports
supabase/migrations/     DB migrations
web/                     Landing page (getclavix.com)
```

---

## Simulator / iOS Build

```
Xcode project: ios/Clavis.xcodeproj
Scheme: Clavis
Simulator: iPhone 17 (22AE0AD5-B089-46A3-8393-2F947D55D0FB)
Bundle ID: com.clavisdev.portfolioassistant
API base URL: https://clavis.andoverdigital.com (both Secrets.xcconfig + Secrets.local.xcconfig)
```

Build + run: `mcp__xcode__build_run_sim` (session defaults already set).

Debug auth bypass (simulator only, DEBUG build):

```
SIMCTL_CHILD_CLAVIX_DEBUG_AUTH_BYPASS=1
SIMCTL_CHILD_CLAVIX_DEBUG_JWT=<token>
SIMCTL_CHILD_CLAVIX_DEBUG_USER_ID=7ff5a6c5-8e49-4c2f-be1c-bdc869926699
```

Real test user: `7ff5a6c5-8e49-4c2f-be1c-bdc869926699` (sansarbikramkarki@gmail.com), holds AMD/AAPL/SMCI.

---

## Production Supabase

- Project ID: `uwvwulhkxtzabykelvam` (region: us-west-1, ACTIVE_HEALTHY)
- Safe read-only SQL checks via `mcp__supabase__execute_sql` — never run DDL through execute_sql; use `mcp__supabase__apply_migration` for schema changes.
- Security migrations applied 2026-05-31: anon cannot call `save_daily_asset_safety_profile` / `save_daily_macro_regime` via REST RPC.
- **User task pending:** toggle leaked-password protection in Supabase Dashboard → Auth → Providers → Email.

---

## Safety Rules (hard)

- **Never** commit `backend/.env`, `.env`, or any secrets file.
- **Never** use `root@134.122.114.241` — always `sansar@` with `sudo -n`.
- **Never** run destructive DB commands without explicit user approval.
- **Never** auto-merge to main or auto-deploy without user approval.
- **Never** modify scoring formulas without verifying the output distribution on prod data.
- **Never** add v1.5/v2 scope to current sprint. Scope is locked in `docs/CLAVIX_LAUNCH_SCOPE_v1.md`.
- iOS VQA mock (`ClavixVisualQA.swift`) is DEBUG+env-gated — never expose in release.

---

## Phase 1 Status (2026-05-31 — all items resolved)

| # | Item | Status | Commit |
|---|---|---|---|
| B1 | Digest + alerts freshness | ✅ LIVE — digest 11:09 UTC, 9 alerts | 395feba4d |
| B2 | News relevance filter (ingestion) | ✅ DONE — `_ticker_relevance_penalty()` in candidate_ranker.py | 5c8218fe0 |
| B2b | News relevance filter (scoring time) | ✅ DONE — `_filter_news_rows_by_relevance()` in ticker_cache_service.py | 992bc2460 |
| B3 | Limited-data exclusion + calibration | ✅ DONE — composite excludes limited dims; BRK.B=AA, KO=A, JNJ=A | 5c8218fe0 |
| B3b | API response consistency | ✅ DONE — `_shared_risk_dimensions` respects `limited_data_dimensions` | 41ce8f6d5 |
| B4 | ETF filter dead-end | ✅ DONE — chips removed | 395feba4d |
| B5 | Supabase security migration | ✅ DONE — applied via MCP | 395feba4d |
| B6 | Security advisor rerun | ✅ DONE — all SECURITY DEFINER findings cleared | 395feba4d |

## Verified grade distribution (2026-05-31)
- AA: 1 (BRK.B 80.0) — first AA ticker since launch
- A: 131
- BBB: 321
- BB: 43
- B: 8 + CCC/CC: 2
- `verify_data_truth.py`: ALL CHECKS PASSED ✅, 7 grade bands

## Remaining P1 blockers (no longer code-solvable without Apple account)
- **StoreKit** — no IAP code exists; needed for paid launch; requires App Store Connect products
- **APNs** — `/health` returns `apns:missing`; needs Apple Developer enrollment + p8 key
- **Leaked-password protection** — toggle in Supabase Dashboard → Auth → Providers → Email (user task)

## Daily recompute note
The full-universe daily recompute runs at ~10:00 UTC weekdays. On the next run,
all 321 BBB tickers will be re-scored with the limited-data exclusion fix applied.
Many will shift from BBB to A as their limited news_sentiment is correctly excluded.
After that run, the grade distribution will look materially more realistic.
