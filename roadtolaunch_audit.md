# Clavix Road to Launch Audit

## Updated Continuation Audit

**Date:** 2026-05-25  
**Auditor:** Codex GPT-5  
**Scope:** repo state, git history, local build/test signals, selected live endpoint checks, and prior launch docs in this repo.  
**This section supersedes conflicting conclusions below.**

### New launch target

Closed TestFlight beta in 21 days with:

- the iOS app working end-to-end
- real backend data and visible freshness
- scheduler/backfill verified with evidence, not hope
- legal pages and disclaimers present
- StoreKit sandbox payments working **if feasible without blowing up the 21-day target**
- no public App Store launch unless separately approved

### Verified current state

#### Repo / git

- `main` is ahead of `origin/main` by 18 commits and the worktree is dirty.
- There is a very large untracked `BACKFILL/` tree plus untracked launch docs. Treat local state as active, not clean-room.
- Recent commit history does verify the claimed scheduler/news work:
  - `10c587ff0` added scheduler foundation, job runner, cron file, job locks, job-runs audit, and scheduler tests.
  - `aa31c7a2e` added event-fundamentals, ETF-holdings, and universe-audit jobs.
  - `f277ea442` and `2c0d47fef` materially hardened the news pipeline.
  - `b55b02168` is the current HEAD and includes post-audit corrections.

#### Backend / scheduler / backfill

- The repo now contains a real cron file at `scripts/cron/clavix.crontab:1-22`, not just a plan.
- The production deploy workflow does install that file to `/etc/cron.d/clavix` and reload cron at deploy time: `.github/workflows/deploy-prod.yml:45-55`.
- The job runner exists and registers daily/weekly/monthly/manual jobs in `backend/app/jobs/run.py:80-113`.
- `backfill_14d` exists and loops a 14-day window through `composite_recompute.run(...)`: `backend/app/jobs/backfill_14d.py:8-45`.
- The scheduler tiering logic exists and defaults to `"cron"` unless `SCHEDULER_TIER` or legacy pause flags say otherwise: `backend/app/pipeline/scheduler.py:94-101`.
- APScheduler startup exists and conditionally registers cron-tier jobs plus intraday jobs: `backend/app/pipeline/scheduler.py:5525-5574`.
- What is **not** verified from repo alone:
  - whether VPS cron is actually firing in production
  - whether `job_runs` has recent successful rows
  - whether `backfill_14d` has ever been run against prod
  - whether the VPS is on the same code as local `main`

#### News pipeline

- There is a real canary script for news-system validation: `backend/scripts/canary_10_tickers.py:1-240`.
- The canary is additive and explicitly intended as a safe pipeline probe.
- Repo evidence strongly supports that the news pipeline exists and has been iterated on heavily.
- What is **not** verified from repo alone:
  - current real-world enrichment hit rate
  - current Google wrapper resolution success rate
  - current MiniMax failure rate under sustained load
  - current freshness of `shared_ticker_events` in production

#### iOS app

- The app still builds locally: `xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build` returned `BUILD SUCCEEDED`.
- The build still emits a project warning about malformed Xcode group membership, which is not a launch blocker by itself.
- The app still only registers `clavis` as a URL scheme in `ios/Clavis/Resources/Info.plist:15-23`.
- The app still declares `armv7` in `ios/Clavis/Resources/Info.plist:50-53`.
- The app delegate still only accepts `clavis://...` callbacks in `ios/Clavis/App/ClavisApp.swift:50-79`.
- Push registration is wired in-app, but backend APNs must exist for delivery: `ios/Clavis/App/ClavisApp.swift:19-40`, `ios/Clavis/Services/PushNotificationManager.swift:5-102`.

#### Payments / subscriptions

- There is still **no real StoreKit implementation** in app code. `rg` over `ios/Clavis` and `backend/app` found no `StoreKit` import and no purchase/restore code paths.
- `ios/project.yml:40-46` still only declares the Supabase package.
- Upgrade flows are still stubs:
  - `ios/Clavis/Views/Settings/SettingsView.swift:355-388` renders `Pro is coming soon`.
  - `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:355-380` renders `Pro is coming soon`.
- There is still no backend entitlement route or webhook surface. Repo search found no real `subscription` / `entitlement` API implementation under `backend/app/routes`.
- `subscription_tier` is still used as the entitlement source for server gates like ticker refresh: `backend/app/routes/tickers.py:26-67`.

#### Legal / website / trust copy

- The repo website source still contains only `web/index.html` and `web/confirm.html`. There are no versioned `web/privacy.html`, `web/terms.html`, `web/refund.html`, or `web/methodology.html` files in this repo.
- The website source still advertises a 14-day Pro trial and paid plan:
  - `web/index.html:560`
  - `web/index.html:688`
  - `web/index.html:694-697`
- The website source does include a meaningful informational-risk disclaimer in `web/index.html:704-705`.
- The iOS settings screen links to live Privacy and Terms pages: `ios/Clavis/Views/Settings/SettingsView.swift:209-213`.
- Live site check on 2026-05-25:
  - `https://getclavix.com/privacy` -> `200`
  - `https://getclavix.com/terms` -> `200`
  - `https://getclavix.com/refund` -> `200`
  - `https://getclavix.com/methodology` -> `200`
- Conclusion: the old “legal pages 404” audit finding is stale for the live site, but the repo still does not contain the source for those live pages. That is a process and trust problem, not a resolved repo problem.

#### APNs / backend live health

- Live backend check on 2026-05-25 returned:
  - `{"status":"ok","apns":"missing","snaptrade":"configured","minimax":"configured","supabase":"configured"}`
- The APNs typo is still real in code: `backend/app/services/apns.py:69-76` defaults to `"Clavynx Update"`.
- Health route still reports APNs status based on file/env validation: `backend/app/main.py:320-331`.

#### Tests / CI

- Backend CI uses Python 3.11 and runs the full test suite: `.github/workflows/backend-ci.yml:13-46`.
- Local backend collection now reports **490 tests collected**, not 391.
- Targeted scheduler/news/data tests under CI-style env produced:
  - `33 passed`
  - `1 failed`
- The failing test is `tests/test_scheduler_jobs.py::test_upsert_ticker_snapshot_from_scores_serializes_snapshot_date`.
- The current implementation uses `date.today()` in `_upsert_ticker_snapshot_from_scores`: `backend/app/pipeline/scheduler.py:5326-5341`.
- The failing assertion expects UTC date alignment and got an off-by-one boundary mismatch: `backend/tests/test_scheduler_jobs.py:230-259`.

### What the previous audit got right and still appears true

- Backend is up. Verified live `/health`.
- APNs is not deployed. Verified live `/health` plus repo code.
- StoreKit/payment infra is still absent in repo.
- Scheduler/backfill/news work really did land in git history.
- iOS still builds.
- Legal/commercial/trust scaffolding is still the main launch bottleneck.

### What the previous audit got wrong or stale

- **Tests count:** stale. It is now 490 collected locally, not 391.
- **Legal pages 404:** stale for the live site. They now return `200`.
- **`subscription_tier` self-edit via `/preferences`:** stale as written. The public `/preferences` PATCH model only accepts digest and notification fields in `backend/app/routes/preferences.py:7-12` and `:75-118`.  
  What remains true is worse in a different way: there is still **no real entitlement model**. Server-side access control still trusts `user_preferences.subscription_tier`, but the consumer purchase path does not exist.
- **Scheduler “may exist”:** stale. It does exist in repo now. What remains unverified is production firing.

### What still cannot be verified from repo alone

- Whether the production VPS is actually on the local `main` tip.
- Whether `/etc/cron.d/clavix` is installed on prod right now.
- Whether `job_runs` shows recent successful daily/weekly/monthly jobs.
- Whether `backfill_14d` has been run in prod.
- Whether the live legal pages match repo/source-of-truth docs.
- Whether Apple Developer enrollment, Paid Apps agreement, App Store Connect, or banking are far enough along to support sandbox subscriptions.

### Payment / TestFlight feasibility

#### Plan A — 21 days with TestFlight + StoreKit sandbox payments

Feasible **only if** all of the following are true within the first week:

- Apple Developer Program enrollment starts immediately and clears quickly.
- Paid Apps / banking / tax setup in App Store Connect does not stall.
- You recover the EIN or get it from the IRS fast enough to start Mercury immediately.
- We define “payments working” as:
  - sandbox subscription products configured in App Store Connect
  - purchase / restore / manage flows working in TestFlight
  - beta-grade entitlement handling acceptable for a **closed** tester cohort

This is **not** the same thing as public-launch-grade billing infrastructure. If you insist on Plan A, the clean trade is:

- closed TestFlight beta only
- sandbox-only purchases
- no promise that the server-side entitlement model is public-launch complete
- explicit approval gate before any public App Store release

#### Plan B — 21 days TestFlight, payments days 22–28

This is the safer launch path.

- Day 21 target becomes a fully working closed TestFlight beta with real data, scheduler proof, backfill proof, legal pages, disclaimers, and APNs if Apple enrollment cleared.
- Days 22–28 finish StoreKit sandbox, entitlement model, Paid Apps setup, and beta validation without putting the 21-day target at risk.

#### Recommendation

**Recommend Plan B.**

Reason:

- The repo still has zero real StoreKit code.
- There is still no entitlement backend.
- Apple Developer enrollment has not started.
- business banking is not ready
- scheduler/backfill still lack production proof
- there is still one scheduler/date failure in the targeted backend suite

Plan A is possible, but it is a tightrope. Plan B gives you a truthful, usable fintech beta in 21 days and leaves payments to a contained week-two extension instead of betting the whole launch on Apple + billing + entitlement timing.

### Apple Developer / LLC / EIN / Mercury implications

- **Apple Developer Program** is now the single highest external blocker for TestFlight, APNs key generation, and StoreKit setup.
- **Lost EIN** is not a paperwork nuisance. It blocks Mercury and can delay App Store paid-agreement/banking setup.
- **Mercury** is the right banking choice for speed, but it should be started immediately after EIN recovery, not later in the plan.
- **Andover Digital LLC exists**, which helps, but repo evidence cannot confirm standing, D-U-N-S readiness, tax forms, or Paid Apps agreement readiness.

### News analysis / backfill readiness

- The system is code-ready for a canary and a backfill.
- It is **not** launch-ready until you have documented evidence for:
  - canary success rate
  - real enrichment completeness
  - real ticker snapshot history
  - real freshness windows
- The giant local `BACKFILL/` directory suggests substantial manual execution happened, but that is not the same thing as reproducible, verified production readiness.

### Scheduler verification status

**Repo verdict:** scheduler implementation exists.  
**Launch verdict:** scheduler trust is still unproven.

Why:

- Cron file exists.
- Deploy copies cron file.
- Job runner exists.
- `job_runs` service exists.
- There is no dedicated admin job-health endpoint yet. `/admin/api/health` only reports basic scheduler runtime state and generic checks: `backend/app/routes/admin.py:272-292` and `:479-481`.
- The targeted suite still has a scheduler-related date-boundary failure.

### Remaining launch issues

#### P0

- Apple Developer Program enrollment
- EIN recovery and Mercury application
- Plan A vs Plan B payment decision
- StoreKit scope definition
- APNs deployment
- `clavix://` URL scheme support
- `armv7` capability fix
- scheduler proof in production
- `backfill_14d` proof in production
- news pipeline canary report
- website payment/trial copy aligned with reality

#### P1

- version-controlled legal page source or documented separate site source of truth
- admin job-health endpoint/dashboard
- sandbox entitlement model for TestFlight
- App Store Connect product/config checklist
- iOS crash/logging instrumentation
- scheduler snapshot-date failure triage

#### P2

- public-launch-grade entitlement verification
- App Store Server Notifications / receipt strategy
- tester communications / support flow
- App Store metadata / screenshots / privacy nutrition labels

#### P3

- analytics
- synthetic monitoring
- repo cleanup for `BACKFILL/`

### Clear questions for Sansar

1. Do you want **Plan A** or **Plan B**?
2. Which Apple ID / entity will be used for Apple Developer enrollment?
3. Did you find the EIN, or do you need to call the IRS?
4. Has Mercury signup started?
5. Is the target **closed TestFlight only**, or closed TestFlight plus a public waitlist beta narrative on the website?
6. For TestFlight, must every tester create a Clavix account and log in, or do you want a no-account demo mode?
7. What is the minimum payment behavior that counts as “working” for you:
   - purchase only
   - purchase + restore
   - purchase + restore + manage subscription
   - full backend entitlement verification
8. Are sandbox-only payments acceptable for TestFlight?

---

**Historical audit content follows below. Keep it only as context.**

**Date:** 2026-05-25
**Auditor:** Claude Opus 4.7 (read-only inspection of repo + docs + live endpoints)
**Audit scope:** entire `/Users/sansarkarki/Documents/Clavis` repo, all `docs/`, the live backend (`clavis.andoverdigital.com/health`), the live marketing site (`getclavix.com`), the live Supabase schema as snapshotted in `supabase_schema.sql`, the iOS XcodeGen project, all GitHub Actions workflows, the VPS cron file, and the 39 Supabase migrations.

> **Authority:** `docs/CLAVIX_TRUTH.md` (v2.0, 944 lines) is treated as the source-of-truth product spec. Where the live code disagrees with it, the code is wrong.

---

## Executive Summary

**Overall launch readiness score: 64/100.**

You are much further along than most pre-launch fintech projects. The hard, expensive, slow work is done: a 17-stage news pipeline is shipping live data, 39 migrations have already evolved a coherent Supabase schema, the iOS app builds clean against the new Hi-Fi v2 design system, the backend has 391 tests and a working CI lane, 14 cron-driven jobs are defined and scheduled on the VPS, and a real production deploy pipeline (GitHub Actions → SSH → docker compose) exists. Cloudflare Tunnel + Supabase Auth + Sentry hooks are wired. The marketing site is live and capturing waitlist signups.

What you are *not* ready for is **a real customer paying $20/month with a real brokerage connected via Stripe under a real legal entity that has been reviewed for SEC/SIPC/FINRA exposure.** The gap between "the app is built" and "the company can take money for it" is bigger than the gap between "an idea exists" and "the app is built." That second gap is where the next 21 days have to land.

### Biggest launch blockers (in order)

1. **No Apple Developer Program enrolment yet** — gates TestFlight, App Store submission, APNs, StoreKit. 24–48h delay once you start.
2. **Privacy / Terms / Refund / Methodology pages do not exist on the website** — the footer links to them but they 404. Both the live site and the iOS Settings screen point at these URLs. App Store will reject without them. This is a same-day fix.
3. **No payment infrastructure** — no Stripe code, no StoreKit code, no entitlement table, no `subscription_events`. The "14-day free trial" promised on the website cannot be honoured.
4. **APNs key is not deployed to the VPS** — `/health` reports `apns: missing`. Push notifications silently fail. The whole "wakes you when something material happens" value prop depends on this.
5. **Critical UI surfaces silently disagree with the source-of-truth grade definition** — Digest computes portfolio grade as *equal-average* of position scores while `CLAVIX_TRUTH §9` says *value-weighted*. Holdings tab uses the correct value-weighted compute. Two screens will show different grades for the same portfolio. Trust-breaking the moment a user notices.
6. **iOS URL scheme is `clavis://` only** — `CLAVIX_TRUTH §2` requires both `clavix://` (canonical) and `clavis://` (SnapTrade compat). Brokerage OAuth callbacks land in `clavis://`; deeplinks from email/marketing land in `clavix://` and currently don't open the app.
7. **Cold-pipeline truth is unverified** — the cron is defined, but no one has produced evidence in the audit trail that `daily_macro_snapshot`, `daily_sector_snapshot`, `daily_composite_recompute_universe`, and `daily_portfolio_rollup_per_user` actually wrote rows yesterday in prod. Until you can show 14 consecutive days of `job_runs` rows with `status='completed'` for each, the "freshness" UI claims are aspirational.
8. **The `armv7` `UIRequiredDeviceCapabilities`** in [Info.plist:48–50](ios/Clavis/Resources/Info.plist) — wrong (modern iOS-only apps should declare `arm64`). App Store may flag.
9. **Banned brand string `Clavynx` in APNs default title** at [backend/app/services/apns.py:75](backend/app/services/apns.py) — first push the user ever receives will say "Clavynx Update".
10. **No legal entity / not-investment-advice disclaimer surface in the app** beyond a footer line on the website. App Store reviewers and Apple's financial-app guidelines want this in-app, on first run, and in Settings.

### Biggest hidden risks

- **Outside-universe degraded-mode is shipped behind a query flag** (`POST /holdings?allow_outside_universe=true`) but the iOS app doesn't expose the toggle anywhere. The first user who searches `BABA` will see a hard rejection and assume the product is broken.
- **`scheduler_jobs` has the per-user jobs but `PAUSE_SYSTEM_SCHEDULER` semantics changed during the P3 refactor** — `SCHEDULER_TIER` is the new gate. If a developer runs an old branch, system jobs may double-fire or none-fire.
- **No mechanism for "the methodology endpoint took 60 seconds" telemetry** beyond Sentry transactions, which probably aren't sampled at 1.0. The user-facing fallback works (cached `dimension_inputs` only), but you won't know how often it kicks in.
- **`MINIMAX_PERSONALISATION_ENABLED=false` and `MINIMAX_DAILY_BUDGET=0` by default** — the personalisation P7-1 ship was real, but it's gated off in prod until the $50/mo Minimax plan upgrade lands. The structural template still renders, which is fine, but the marketing pitch ("personalised") is half-true.
- **`NSAllowsArbitraryLoads = false` plus an exception for `trycloudflare.com`** — keep this for staging tunnels, but if a release build ever shipped with a public `*.trycloudflare.com` exception in `NSExceptionDomains` the App Store reviewer would flag it. Currently safe but fragile.
- **357 directories under `BACKFILL/`** — generated run artifacts not in `.gitignore`. The repo is gaining weight every backfill. Risk of accidentally committing PII in a future artifact.
- **39 migrations, no rollback / down-migration discipline** — if a deploy goes bad, you're recovering by hand.
- **CORS allowlist includes `localhost` ports** — fine for staging, but `cors_allowed_origins` is read in prod too unless explicitly overridden. Lower-risk than it sounds (CORS is browser-only and you don't have a web app), but worth tightening.
- **`subscription_tier` is freely settable via `/preferences`** — there is no entitlement verification, so any user can self-elevate to Pro by PATCHing the field. Hard blocker once StoreKit ships, but in the current "mock paywall" state it means a curious user with the API spec can use all Pro features for free.

### What is already strong

- **The product spec is unusually clear** (`CLAVIX_TRUTH.md` v2.0 is one of the best product source-of-truths I've seen in a pre-launch repo). Everyone on the team can ship from it.
- **The scoring is auditable end-to-end** — `dimension_inputs` JSONB, `dimension_last_refreshed`, `methodology` endpoint with raw rows, peer/sector medians. This is the moat the spec promises.
- **The job orchestration is real, not paper** — `app/jobs/run.py` + advisory locks + `job_runs` audit table + `/etc/cron.d/clavix` from-repo deploy. Compare to the typical pre-launch indie fintech: this is enterprise-grade.
- **Tests are abundant** — 391 collected. Most pass. CI lane works.
- **Brand voice + visual design is coherent.** Hi-Fi v2 design system + DesignSystem/ primitives + the website's tone all reinforce the rating-agency positioning.
- **Schema discipline.** `shared_ticker_events` is the canonical news store; `ticker_risk_snapshots` is the canonical score store; `portfolio_risk_snapshots` rolls up per-user. No conflicting tables.

### Fastest safe launch path (revised 2026-05-25 per user decisions)

**Two-stage launch.**
- **Day 21 (Mon Jun 15): Closed TestFlight beta, FREE only.** Invite-only ~100 testers from the waitlist; no payments active; Pro features unlocked or gated (TBD). Goal: prove the loop works without trust regressions.
- **Day 28 (Mon Jun 22): App Store public launch with StoreKit 2 payments.** Pro $19.99/mo with 14-day Introductory Offer free trial. StoreKit work happens in parallel through Days 14–21 instead of sequential after the beta. App Store submission Day 24, approval window Day 25–27, public launch Day 28.

This sequence trades a week of "everything in parallel" tension for actually shipping with payments at Day 28 instead of Day 35+. The closed beta gives one full week of trust validation before money enters the picture — if Sentry erupts or the beta cohort hates the digest, you delay Day 28 by 7 days without breaking any external promise.

---

## What I Inspected

### Code

- `backend/app/main.py` (FastAPI entry, Sentry init, JWT auth middleware, public path allowlist)
- `backend/app/config.py` (Settings; env knobs; Sentry; APNs; SnapTrade; Minimax)
- `backend/app/routes/` (24 route modules — every product surface)
- `backend/app/jobs/` (14 job modules + `run.py` CLI + advisory-lock helper)
- `backend/app/pipeline/` (17 pipeline modules — `risk_scorer`, `structural_scorer`, `portfolio_compiler`, `scheduler`, `macro_snapshot`, `sector_snapshot`, `agentic_scan`, etc.)
- `backend/app/services/` (24 service modules — APNs, SnapTrade, Minimax, Polygon, Finnhub, Supabase, news_enrichment, personalisation, polygon_options, peer/sector medians, advisory locks, job_runs audit)
- `backend/tests/` (391 collected tests across 50 files)
- `ios/Clavis/App/` (`ClavisApp`, `ContentView`, `MainTabView`, `ClavixVisualQA`, design tokens)
- `ios/Clavis/Views/` (Auth, Onboarding, Digest, Holdings, Tickers, Alerts, Settings, Search, Shared)
- `ios/Clavis/Services/APIService.swift`, `SupabaseAuthService.swift`, `PushNotificationManager.swift`
- `ios/Clavis/DesignSystem/` (new Hi-Fi v2 foundation, 15 files)
- `ios/Clavis/Resources/Info.plist` (URL schemes, ATS, push capability)
- `ios/project.yml` (XcodeGen spec; deployment target iOS 17.0)
- `web/index.html` (marketing site, 885 lines), `web/confirm.html`
- `scripts/cron/clavix.crontab` (14 cron entries), `scripts/start.sh`, `scripts/setup-tunnel.sh`
- `.github/workflows/backend-ci.yml`, `.github/workflows/deploy-prod.yml`
- `render.yaml`, `docker-compose.yml`

### Docs

- `docs/CLAVIX_TRUTH.md` (944 lines — source of truth)
- `docs/HANDOFF.md` (315 lines — most recent state of play)
- `docs/MOCK_TO_LIVE_AUDIT.md` (370 lines — screen-by-screen LIVE/PARTIAL/MOCK)
- `docs/CODEX_RUN_AUDIT_2026-05-25_v2.md` (109 lines — most recent Codex execution audit)
- `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md` (386 lines — cadence design)
- `docs/UI_DATA_CONTRACT_MATRIX.md`, `docs/BACKEND_DATA_GENERATION_PLAN.md`, `docs/UI_ELEMENT_DATA_AUDIT.md`
- `docs/P0_P1_P2_IMPLEMENTATION_PLAN.md`, `docs/REFACTOR_PLAN.md`, `docs/TARGET_DESIGN_SOURCE_OF_TRUTH.md`
- `docs/PRODUCT/methodology.md`, `docs/PRODUCT/pricing.md`, `docs/PUBLIC/methodology.md`
- `docs/ARCHITECTURE/CODEBASE_ARCHITECTURE.md`, `docs/REFERENCE/BACKEND_OVERVIEW.md`
- `docs/design/BRANDING_GUIDE.md`, `docs/design/clavis-colors.md`, `docs/design/clavix-hifi-v2.html`
- `docs/GUIDES/*` (digitalocean-vps-setup, cloudflare-access-admin, vps-deploy-tutorial, dev_prod_workflow, uptime-monitoring)
- `docs/legal/inter_font_license.md`, `docs/legal/jetbrains_mono_font_license.md` (font licenses only — no privacy/terms docs)
- `AGENTS.md` (665 lines — agent operating manual)
- `README.md`, `backlog.md`

### Live systems

- `https://clavis.andoverdigital.com/health` returned `200 ok` with `apns: missing` at audit time
- `https://getclavix.com` returned the marketing site (`200 ok`)
- `supabase_schema.sql` (615 lines — consolidated current schema)

### Memory

- `/Users/sansarkarki/.claude/projects/-Users-sansarkarki-Documents-Clavis/memory/project_clavis_state.md` — auto-memory project state from prior sessions

### Not inspected (and where to look next)

- Supabase project dashboard (RLS policies live there, partially mirrored in migrations)
- Render dashboard (production env vars)
- DigitalOcean VPS host (cron logs, container restart history)
- Cloudflare Tunnel dashboard
- Apple Developer Program / App Store Connect (you don't have an account yet)
- The 357 directories under `BACKFILL/` (sampled one; assumed all are similar artifacts)

---

## Assumptions

These are stated explicitly so you can correct them. Anything labelled `[ASSUMPTION]` in later sections traces back here.

1. **You have admin/SSH access to the VPS** and can deploy changes via `git push` → `deploy-prod.yml` or manually via SSH. The handoff doc says the SSH key is at `~/.ssh/clavix_vps_ed25519` but earlier attempts hit "permission denied" on two IPs; assuming the access has since been restored because `/health` was responding at audit time.
2. **Sentry is collecting events in prod.** `sentry_dsn` is read from env. I cannot verify whether a real DSN is set in Render/VPS env without dashboard access.
3. **Supabase RLS is enforced.** Migrations show RLS being added to several tables; assuming the live database has RLS enabled on `positions`, `portfolio_risk_snapshots`, `digests`, `alerts`, `user_preferences`, `watchlist_items`.
4. **No real users yet** — beyond yourself and possibly a small dev cohort. The audit is launch-readiness, not user-impact triage.
5. **Apple Developer Program is not yet enrolled** (per `backlog.md`'s "Prerequisites we do not own yet" section).
6. **Stripe / Apple Pay / StoreKit accounts are not yet created.**
7. **SnapTrade is configured in prod env** (`/health` says `snaptrade: configured`), but the iOS app surface for it is the deferred "Subscriptions are coming soon"-style stub — assuming no end-to-end brokerage sync has happened yet for a real user.
8. **The 14-day score-history backfill (`backfill_14d`) has not been run against prod** — there is no audit row in the repo proving it. If it has, score-history sparklines will be populated; if not, every "was BBB N days ago" delta is `—` until ~14 trading days post-deploy.
9. **You can work 10+ focused hours/day for 21 days.** The 21-day plan assumes this.

---

## Questions for Sansar

Highest-impact open questions, ranked. Answering the top five unblocks the 21-day plan.

| # | Question | Why it matters | Impact if wrong |
|---|---|---|---|
| 1 | **Are you committed to closed TestFlight as the 21-day launch target, or do you want App Store public launch in 21 days?** | App Store review averages 24–48h but a financial app can take 1–2 weeks; payment infra alone is ~5 days. Public launch in 21 days means most of those days are non-engineering. | If public launch, 21 days is unrealistic without dropping payments → recommend free public TestFlight beta with a Stripe payment-link fallback for early supporters. |
| 2 | **Have you enrolled in Apple Developer Program yet? If not, can you start the enrolment today?** | 24–48h delay. Blocks APNs key, TestFlight, App Store submission, StoreKit setup. Every day of delay costs a launch day. | If not started, real launch slips by Apple's wait time. |
| 3 | **What is the legal entity name and state of formation for "Andover Digital LLC"?** Is it actually formed and in good standing, with EIN, business bank account, and a registered agent? Is there a Terms-of-Service / Privacy-Policy draft anywhere we missed (the repo only has font licenses)? | The website footer lists Andover Digital LLC. App Store requires the seller entity to match. ToS / Privacy are non-negotiable. The "not investment advice" language has to be reviewed by a securities lawyer at least once. | Without a real entity + reviewed ToS, you can't take money and you may have unintentional SEC exposure ("you describe portfolio risk, but you also rank stocks A→F — is that an unregistered advisor newsletter?"). |
| 4 | **What's the maximum invite list size you're comfortable with for closed beta?** 50? 200? 1,000? | Determines Minimax LLM budget needed before launch ($20/mo plan = ~600 users; $50/mo = ~1,500), determines Polygon/Finnhub plan tier needed, determines support load. | Underestimate → cost surprise. Overestimate → wasted spend. |
| 5 | **Is `subscription_tier` patchable client-side a known issue or a security oversight?** | If it's a known stub, fine (and obvious to fix when StoreKit lands). If you didn't realise, you have a free Pro upgrade available to anyone with the API spec right now. | Either way: lock it before any public/beta exposure. |
| 6 | **Did the `backfill_14d` job actually run against prod?** Output of `python -m app.jobs.run backfill_14d` would have shown 503 × 14 = ~7,000 rows written to `ticker_risk_snapshots`. | If yes, your score-history sparklines are live on day 0. If no, week-1 users see `—` on every "was AA 5 days ago" delta and you need to run it ASAP. | Trust impact: huge. |
| 7 | **Has any of the cron from `scripts/cron/clavix.crontab` produced 7+ consecutive days of `status='completed'` rows in `job_runs`?** | If yes, the data pipeline is genuinely live. If no, the freshness UI ships lying. | Same as above. |
| 8 | **Are you intending to launch with both manual + brokerage paths, or just manual?** Brokerage = SnapTrade = depends on Pro = depends on StoreKit. Manual-only is shippable today. | Affects scope of Day 1–7 in the plan. | Brokerage in 21 days adds risk; manual-only is safer. |
| 9 | **Who is your launch designer/illustrator?** App Store screenshots, social cards, press images, app icon polish — these are 1–2 days of design work that doesn't exist in the repo. | App Store rejects on poor screenshots; press reach depends on cards. | Without a designer (you or contractor), Day 18–20 of the plan stretches. |
| 10 | **What is your Minimax bill cap and Polygon/Finnhub usage today?** | Need to know the cost model before personalisation P7-1 turns on at scale and before you invite 200 testers. | Surprise bill = stress. |

---

## Launch Readiness Scores

Out of 100 each. Brutal honesty.

| Area | Score | One-line why |
|---|---|---|
| **Product** | 75 | Spec is unusually crisp; core loop works; key value (auditable scores) is real. Pricing/payments not built. |
| **UI/UX** | 70 | Hi-Fi v2 design system landed; legacy `clavix*` tokens still co-exist; some screens not yet migrated; navigation good; loading/empty/error states inconsistent. |
| **Backend** | 80 | FastAPI is clean; routes are organised; auth works; pipeline is sophisticated; advisory locks + job_runs audit is enterprise-grade. Sentry maybe not connected. |
| **Database** | 78 | 39 migrations, coherent schema, RLS appears intentional, single news store, single score store. Lacking down-migrations; no documented rollback path. |
| **Data freshness** | 55 | Cron is defined; can't verify rows are landing daily without DB read access; `apns: missing` → push won't fire; until proven, freshness UI is promissory. |
| **Data accuracy** | 65 | Methodology is rigorous; portfolio composite definition disagrees between Digest (equal-avg) and Holdings (value-weighted); peer/sector medians weekly but unverified live. |
| **Pipeline reliability** | 65 | The pipeline runs and writes; 17 stages; tested. But no SLO, no alerting on job failures, no canary outside the `canary_10_tickers.py` script. |
| **Website** | 55 | Marketing site is up, copy is good, waitlist works. **Privacy/Terms/Refund/Methodology pages 404.** No analytics. No sitemap. No OG image asset (only meta tags). |
| **Analytics** | 20 | No analytics at all — no PostHog, no Amplitude, no Mixpanel, no GA4, no app-level event tracking. `waitlist_signups` table is the only conversion signal. |
| **Legal/compliance** | 25 | "Not investment advice" disclaimers in copy; no actual Terms; no Privacy Policy; no legal entity in repo; no SEC review; no GDPR/CCPA posture. |
| **Security** | 60 | Supabase RLS appears configured; JWT verification works; CORS allowlist intentional; admin password set; `apns.p8` properly excluded from rsync. `subscription_tier` is self-elevatable. Secrets management via Render env / `.env` (not via a vault). |
| **Integrations** | 50 | Polygon, Finnhub, Minimax, Supabase, Sentry, Cloudflare Tunnel — all wired. SnapTrade configured but unused. APNs missing. Stripe missing. PostHog missing. |
| **Testing/QA** | 70 | 391 tests; CI lane exists; 1 known pre-existing failure (`test_article_scraper_resolution`). No E2E iOS UI tests; no canary post-deploy; no synthetic monitoring. |
| **App Store readiness** | 15 | App is buildable; no Apple Dev team; no signing cert; no provisioning; no screenshots; no App Store description; `armv7` capability is wrong; `clavix://` scheme missing. |
| **Brand** | 80 | Voice is consistent; design language is distinctive; "Portfolio risk, measured." works as a tagline. Logo mark exists. Press kit doesn't. |
| **Marketing** | 35 | Site captures waitlist. No social, no blog, no SEO content, no methodology page on the site (despite the `#methodology` anchor going to a section, not a page). No press kit. No demo video. |
| **Automation/autonomous company readiness** | 25 | Cron + agent operating manual + Claude Code workflows exist as patterns. No GitHub Actions for issue/PR triage, no monitoring → issue pipeline, no daily report. The bones are good; the system is not assembled. |
| **Overall** | **64** | Solid engineering, weak commercial+legal scaffolding. |

---

## Full Audit

### 1. Product readiness

**Current state.** The product is informational portfolio risk intelligence with bond-style letter grades (AAA→F) on three layers (macro, sector, individual position) plus a personalised morning briefing. The 17-stage news → classify → score → digest pipeline is shipping live data for ~503 S&P 500 tickers. Onboarding is 4 steps, complete. Tabs: Today, Holdings, Search, Alerts, Settings.

**What's working.**
- The auditable-scoring promise is real and architecturally enforced (see §8 of `CLAVIX_TRUTH.md` and `routes/methodology.py`).
- The grade hysteresis rule (Δ ≥ 3 + 2 consecutive days) shipped in P7-1 work.
- `Limited Data` honest fallback exists for <3 articles and <2 days of history.
- Outside-universe degraded path exists in the backend (`positions.outside_universe` column, `allow_outside_universe=true` query flag).

**What's missing or risky.**
- Outside-universe path is invisible in the iOS UI — search a non-universe ticker today and you get a hard error.
- Verbose digest tier is wired but Pro-only; the Pro gate is bypassable because `subscription_tier` is self-PATCHable.
- No CSV import (P2 — out of scope for v1, fine).
- No Pro entitlement event table; no subscription webhook handlers.
- "Limited Data" message wording varies across screens.

**Recommended fixes.**
- Plumb `allow_outside_universe=true` into iOS `APIService.addHolding` with the right banner copy from `CLAVIX_TRUTH §5`.
- Server-side enforce `subscription_tier` — refuse PATCH on the field via `/preferences`; only the entitlement webhook can set it.
- Standardise the limited-data card copy in `DesignSystem/EmptyState.swift` and use it everywhere.

### 2. Data freshness and correctness

**Current state.** The cron file `scripts/cron/clavix.crontab` schedules 14 jobs across daily/weekly/monthly cadences. Macro snapshot, sector snapshot, universe composite recompute, portfolio rollup, EOD price capture, alert evaluation are all daily on weekdays. Peer groups, sector medians, volatility recompute are weekly. Universe audit is weekly. Macro regression and ETF holdings refresh are monthly. Event-driven earnings-T-1 fundamentals refresh exists.

**Evidence from repo.** `scripts/cron/clavix.crontab:8–24`. `app/jobs/run.py` registry. `services/job_runs.py` audit table. The deploy workflow `.github/workflows/deploy-prod.yml` copies the crontab to `/etc/cron.d/clavix` and reloads `cron`.

**What's working.**
- `job_runs` writes a row per invocation; you can query "did `daily_macro_snapshot` run yesterday?" in SQL.
- Idempotent upserts on `(ticker, snapshot_date)`.
- Rate gates on Polygon (20s spacing) and Finnhub (0.12s).

**What's missing or risky.**
- **No live verification.** I cannot confirm from the repo alone that yesterday's macro/sector snapshot wrote rows. The cron is on the VPS; the `job_runs` table is in Supabase; only a SQL query (or admin route) can tell you for sure.
- **`daily_eod_price_capture` runs at 16:15 ET** — US markets close at 16:00 ET but extended-hours moves can still occur. Currently fine, but be aware.
- **No alert on missing job runs.** If the VPS reboots and cron doesn't come back, you find out from a user.
- **iOS doesn't surface "Refreshed at" timestamps prominently.** The `freshness` block is in some endpoints; the UI rarely renders it. Sophisticated users will ask "is this morning's data or yesterday's?"

**Recommended fixes.**
- Add a `/admin/job_health` route that returns `{job_id, last_success, expected_cadence, status}` for every job in the registry. Bake into the daily morning routine.
- Surface `freshness.as_of` next to the score on Today/Holdings/Ticker. The label exists; render it.
- Set up a 30-min healthcheck cron that pings a notification channel if any tier-1 job hasn't completed in the last 30h.

### 3. Backend / DB / API contracts

**Current state.** FastAPI app with 24 route modules, ~17 pipeline modules, ~24 service modules. Pydantic models. Supabase as the only datastore. JWT auth via Supabase. Sentry hooks. CORS allowlist. Per-route public/auth gating.

**What's working.**
- Single news store (`shared_ticker_events`), single score store (`ticker_risk_snapshots`), single portfolio store (`portfolio_risk_snapshots`).
- Models are versioned (`v2_grade_constraints`, `v2_snapshot_dimension_columns`).
- 39 migrations are chronological, named clearly, and look composable.
- Methodology endpoint returns `dimension_inputs` + `peer_comparisons` + `factor_exposures` + `article_histogram_14d`.

**What's missing or risky.**
- **No API versioning.** Routes are unprefixed (`/today`, `/holdings`). If you ever ship a v2 contract, you'll have to deal with `?v=2` query params or a `X-Clavix-Version` header. Not blocking, but plan for it.
- **No OpenAPI spec is committed.** `enable_public_docs` is gated. The iOS app effectively documents the contract by consuming it; no machine-readable contract test exists.
- **Decision-of-record disagreements.** Portfolio grade definition: `MOCK_TO_LIVE_AUDIT` flags that the Digest endpoint computes equal-average grade and the Holdings envelope uses value-weighted. Truth says value-weighted. Two surfaces, two answers.
- **`subscription_tier` writable from `/preferences`** — this is in `routes/preferences.py`. Block it.
- **No `webhooks/stripe` or `webhooks/apple` route.** When StoreKit lands you'll need one.

**Recommended fixes.**
- Promote `routes/today.py` to be the canonical envelope; deprecate the equal-average grade compute in `routes/digest.py` so both surfaces read from `portfolio_risk_snapshots`.
- Server-side block `subscription_tier` PATCH; require an admin token OR the (future) entitlement webhook.
- Commit the generated OpenAPI to `docs/REFERENCE/openapi.json` so the iOS team can diff contract changes per release.

### 4. Frontend / iOS audit

**Current state.** SwiftUI app, deployment target iOS 17.0, Supabase Swift SDK, custom `APIService` for the backend. New `DesignSystem/` foundation (Hi-Fi v2). Legacy `App/ClavixDesignTokens.swift` and `App/ClavisDesignSystem.swift` still coexist. Tabs: Today (`DigestView`), Holdings (`HoldingsListView`), Search (`SearchView`), Alerts (`AlertsView`), Settings (`SettingsView`).

**Screen-by-screen (live vs mock).** Per `docs/MOCK_TO_LIVE_AUDIT.md` and recent commits:

| Screen | Live | Notes |
|---|---|---|
| Auth / Onboarding | mostly LIVE | Real Supabase auth; 4-step onboarding writes real prefs. |
| Today / Digest | PARTIAL | Real backend digest envelope; equal-vs-value-weighted mismatch with Holdings; some prose fallbacks ("Your portfolio briefing is ready.") if backend returns nulls. |
| Holdings | mostly LIVE | Real positions; real prices; value-weighted portfolio composite. Score-history sparkline depends on `backfill_14d` having run. |
| Search | PARTIAL | Real search; "What others are looking at" trending rows still placeholder. |
| Ticker Detail | LIVE | Real `dimension_inputs`, methodology drawer, peer comparisons, factor exposures, IV-rank (where Polygon options data exists). Recent News from `shared_ticker_events`. |
| Methodology audits (FH/News/Mac/Sec/Vol) | LIVE | Real raw inputs, sector medians, peers. |
| Alerts | PARTIAL | Alerts table is live but APNs delivery is no-op; unread counts depend on Alerts v2 columns (added in `20260524`); iOS Alert model decoding works because optional. |
| Settings | LIVE | Real preferences. Legal links 404. |
| Paywall | MOCK | Says "coming soon." No StoreKit. |

**What's working.**
- Build is green on iPhone 17 sim.
- Hi-Fi v2 primitives have previews.
- Loading/empty/error cards are in `DesignSystem/EmptyState.swift`.

**What's missing or risky.**
- `armv7` in `UIRequiredDeviceCapabilities` is wrong — should be `arm64`.
- `clavix://` URL scheme not registered (only `clavis://`). Truth requires both.
- No `Clavynx` strings in iOS, but the typo lives in `backend/app/services/apns.py:75` — the *first* push every user receives says "Clavynx Update".
- No in-app first-run disclaimer.
- No iOS analytics SDK.
- No accessibility audit.
- The TODO at `HoldingsListView.swift:792` ("backend add-holding endpoint does not yet accept purchase_date") is minor but real.

**Recommended fixes.**
- Fix Info.plist: `armv7` → `arm64`, add `clavix` to `CFBundleURLSchemes`.
- Fix `apns.py:75` default title from `"Clavynx Update"` to `"Clavix"`.
- Add a one-time "Clavix is informational, not investment advice" full-screen disclaimer on first launch with an accept-checkbox + audit record.
- Migrate the remaining legacy `clavix*`-token screens to `DesignSystem/` primitives — start with Settings and Onboarding because those are first-impression surfaces.

### 5. Website / waitlist audit

**Current state.** Static site under `/web` deployed via Render's static site service. Single index page (`index.html`, 885 lines). Confirmation page (`confirm.html`, 367 lines). Waitlist signup endpoint at `POST /waitlist` writes to `waitlist_signups`.

**What's working.**
- Visually distinct, on-brand, "rating agency" tone.
- Above-the-fold CTA is the waitlist signup. Conversion path is clean.
- Footer disclaimer correctly says "informational, not investment advice."
- OG tags and canonical URL present.
- Anti-spam: the waitlist endpoint normalises email + rejects garbage.

**What's missing or risky.**
- **`/privacy`, `/terms`, `/refund`, `/methodology` all 404.** Footer links go to dead URLs.
- **No analytics.** No PostHog, GA4, Plausible. You don't know your conversion rate.
- **No demo video or animated mockup** — the "preview" section is static screenshots.
- **No favicon / no apple-touch-icon** (or not visible from the HTML).
- **No sitemap.xml or robots.txt** committed to `/web`.
- **`signup-shell`'s "14-day Pro trial · No credit card required" promise** depends on StoreKit/Stripe existing.
- **The `#methodology` anchor on the home page jumps to a section, but there is no dedicated `/methodology` page** the way `CLAVIX_TRUTH §8` describes.
- **No press kit page** (`/press` or `/about`).

**Recommended fixes.**
- Day 1: ship `/privacy.html`, `/terms.html`, `/refund.html`, `/methodology.html` rendered from `docs/PUBLIC/methodology.md` and the (to-be-written) legal docs. Re-point footer links.
- Day 1: add Plausible or PostHog (single `<script>` tag) for conversion + waitlist completion tracking.
- Day 2: produce a 30-second app demo (Lottie or hand-recorded sim) and embed in the hero.
- Day 7: ship a `/blog` directory with 1–2 launch posts targeting the ICP (Bogleheads, r/SecurityAnalysis).

### 6. Legal / compliance / security audit

**Current state.**
- Website footer says "informational only, no investment advice, no buy/sell recs."
- iOS Settings links to `https://getclavix.com/privacy` and `/terms` (broken URLs).
- No Terms of Service or Privacy Policy committed anywhere in the repo (only font licenses).
- The "Andover Digital LLC" entity is referenced on the site footer.
- Supabase Auth handles user passwords and email; Supabase is SOC 2 Type II.
- Service-role keys are in Render env (`render.yaml: sync: false`). APNs `.p8` is excluded from the rsync.
- CORS allowlist restricts to known origins.

**SEC/SIPC/FINRA risk.** Not a lawyer, but the structural risk pattern:
- Clavix produces letter-grade ratings on individual stocks and surfaces them daily, personalised to a user's holdings.
- It explicitly avoids "buy/sell/hold" language.
- "Investment adviser" under the Advisers Act covers anyone "engaged in the business of advising others ... as to the advisability of investing in ... securities." A *rating* of individual securities, *personalised* to a portfolio, *for a fee* could plausibly cross that line.
- The strongest defenses for staying out of advisor-registration: (1) no personalised recommendations; (2) data and methodology shown to the user; (3) ratings are based on public information and observable measurements, not professional judgment; (4) a clear disclaimer accepted by the user.
- Clavix does (1)–(3) well. (4) is on the website footer but **not in the app first-run flow** and not in a signed/accepted ToS.

**What's missing or risky.**
- **No legal entity verification in the repo** — does Andover Digital LLC actually exist, with EIN, registered agent, business bank account?
- **No Terms of Service.** No Privacy Policy. No Cookie Policy. No DPA. No CCPA opt-out.
- **No GDPR posture.** If you ship globally on App Store, you'll get EU users. Need DPIA + data export + data deletion (`routes/account.py` does delete — good — but no DPA, no privacy contact email beyond `support@`).
- **`subscription_tier` is self-elevatable** (security).
- **No rate-limiting on `/waitlist`** by IP — bots can flood `waitlist_signups`. Currently low-stakes but worth a basic IP-bucket guard.
- **`CORS_ALLOWED_ORIGINS` includes `localhost` in production** (see `backend/app/config.py:14`). Low risk because CORS is browser-only and you don't have a web app, but tighten.
- **APNs `.p8` key location is `/etc/secrets/apns.p8` on Render and `/app/apns.p8` in container default** — if these don't align in deploy, push silently fails.
- **`admin_password` is a settings value** — fine, but rotate before launch and ensure it's a strong secret.
- **No SOC 2 / ISO posture; no penetration test.** Not needed for a closed beta but worth budgeting before public launch.

**Recommended fixes.**
- **This week:** draft Terms of Service + Privacy Policy + No-Investment-Advice disclaimer. Use a template (Termly, iubenda, Stripe Atlas's templates) and have a securities lawyer do a one-hour review. Cost: ~$500–$1,500.
- **This week:** verify Andover Digital LLC is formed and in good standing. If not, form it (Delaware via Stripe Atlas, ~$500).
- **This week:** ship the disclaimer pages on the site + a first-run in-app acceptance with an audit record (`user_legal_acks` table).
- **Day 4:** lock `subscription_tier` and add a simple IP-bucket on `/waitlist`.

### 7. Integrations audit

| Integration | Status | Owner | Risk |
|---|---|---|---|
| Supabase Auth + DB | LIVE | configured | None — but RLS posture not independently verified. |
| Polygon (prices, fundamentals, options) | LIVE | API key in env | Rate-limit gate exists; key may be on free tier. |
| Finnhub (news, earnings calendar, fundamentals) | LIVE | API key in env | Free tier covers daily volume per CLAVIX_TRUTH §5. |
| Minimax (LLM) | LIVE | $20/mo plan | Personalisation gated off; full text generation works. |
| APNs | NOT LIVE | `.p8` not deployed | **Launch blocker.** |
| StoreKit / Stripe | NOT BUILT | — | **Required for paid launch.** |
| SnapTrade | CONFIGURED but unused | Pro-only path | Stub in iOS; brokerage sync won't happen. |
| Sentry | CONFIGURED in code | DSN value unknown | Without DSN you have no error reporting. |
| Cloudflare Tunnel | LIVE | `clavis.andoverdigital.com` | Working at audit time. |
| GitHub Actions CI | LIVE | working | Tests pass on 3.11. |
| Render (static site + standby backend) | LIVE | `getclavix.com` | Fine. |
| Email (transactional) | NOT BUILT | — | No SendGrid/Postmark/Resend. Sign-up emails go through Supabase Auth's defaults. |
| Analytics (PostHog/Plausible/GA4) | NONE | — | Major gap. |
| Crash reporting (iOS) | NONE | — | iOS uses no Crashlytics or Sentry Apple SDK. |

**Recommended fixes.**
- Day 1: SendGrid (free) or Resend ($0–$20) for transactional. Replace Supabase default templates with branded confirmation emails.
- Day 1: PostHog (free up to 1M events) — single web `<script>` + iOS SDK.
- Day 2: Sentry-Cocoa pod added to iOS for crash reporting.
- Day 3: deploy APNs key to VPS (`/etc/secrets/apns.p8`), validate via `validate_apns_configuration()` on next `/health`.
- Day 7–10: StoreKit 2 server-side webhook + entitlement table.

### 8. Testing / QA / release audit

**Current state.**
- 391 tests collected. CI lane runs them on Python 3.11. Most pass.
- 1 known pre-existing failure: `tests/test_article_scraper_resolution.py::test_attach_decoded_google_news_urls_rewrites_wrapper_urls`.
- `compileall` in CI catches syntax errors.
- Deploy workflow: rsync repo to VPS, `docker compose up -d --build`, retry-curl `/health` for 10×3s.
- No iOS test suite (no XCTest target in `project.yml`).
- No synthetic monitoring outside `/health` curl in deploy.
- No staging environment per `render.yaml` (Render is fallback / staging but it's just-another-prod).

**What's missing or risky.**
- **No XCTest target.** Snapshot tests for the design system primitives + a few view-model unit tests would catch regressions cheaply.
- **No E2E flow tests.** "User logs in → adds AAPL → sees a grade → opens methodology → sees inputs" should be automatable.
- **No staging.** All testing happens in prod. The `develop` branch is mentioned in CI triggers but I don't see a `develop` deploy target.
- **No rollback plan documented.** If a deploy lands a broken image, the recovery is `git revert + git push`. There's no SOP for "the schema changed and we need to undo."
- **No load testing.** Today's traffic is zero so this hasn't mattered. With 50 testers hitting `/today` simultaneously at 7am, FastAPI + Supabase will be fine; with 500, you'll start to see queueing on the Minimax personalisation path.

**Recommended fixes.**
- Day 2: add a minimal `ios/ClavisTests/` XCTest target with at least 5 snapshot tests for the design primitives (`GradePill`, `ScoreBar`, `EmptyState`).
- Day 5: fix the pre-existing Google News URL test failure (likely 1–2h).
- Day 8: write a `tests/test_e2e_user_flow.py` integration test that hits the real local backend with a real Supabase test schema.
- Day 12: add a simple post-deploy smoke test in `deploy-prod.yml` that hits `/today`, `/holdings`, `/tickers/AAPL`, `/tickers/AAPL/methodology` and asserts shape.
- Pre-launch: document a 1-page rollback runbook in `docs/GUIDES/incident_response.md`.

### 9. Marketing / brand / AI UGC audit

**Current state.**
- Brand voice and visual identity are coherent and distinctive.
- Marketing site is up but has 4 dead links and no analytics.
- No social presence audited.
- No press kit.
- No demo video.
- No blog or SEO content.

**What's missing or risky.**
- **App Store metadata** — title, subtitle, keywords, description, screenshots, preview video. None of this is in the repo.
- **App icon** — `AppIcon` is in `Assets.xcassets`; I didn't verify quality but it should be checked at all sizes including 1024×1024 marketing.
- **No press kit** — for inbound press (Hacker News post, Product Hunt launch, finance Substack interviews), you need 4-5 high-res images, an app icon, a 200-word About, founder photos.
- **No content calendar** — Twitter/X (FinTwit), 1–2 Substack guest posts, r/SecurityAnalysis presence.
- **AI UGC opportunity**: the methodology drill-downs + the "What changed overnight" briefings are *natively shareable* content. Auto-generated daily market summaries on Twitter using your real macro/sector snapshots could be a sustained acquisition loop. Not blocking, but high upside.

**Recommended fixes.**
- Day 14: package press kit (icon, 5 screenshots, 1 demo video, 200-word about, founder photo).
- Day 14: write App Store metadata. Title: `Clavix`. Subtitle: `Portfolio risk, measured.`. Promotional text: 170 chars. Description: 4,000 chars (use the website's hero + proof + methodology sections, edited down).
- Day 15: AI UGC system v1 — a cron that posts the daily macro+sector summary to X with a `getclavix.com` link. Read-only, no engagement required from you. (P3 of automation roadmap.)
- Day 20: Product Hunt + Hacker News launch posts drafted.

### 10. Autonomous company system audit

You want this to scale toward an AI-operated company. The pieces you have, and the system you should build:

**Existing pieces.**
- `AGENTS.md` (665 lines) — agent operating manual. Strong foundation.
- `scripts/cron/clavix.crontab` — production cron.
- `job_runs` audit table — durable record of what ran.
- Sentry + JSON-structured logging on the backend.
- GitHub Actions for CI + deploy.
- Claude Code as the primary engineering agent.

**Departments (in build order).**

| Dept | Purpose | Inputs | Outputs | Tools | Automatable | Needs human | Priority |
|---|---|---|---|---|---|---|---|
| Orchestrator | Decide what to do next across the system; daily command-center; weekly review | All other dept outputs | Daily report; weekly review; new GH issues | Claude Code + cron | 90% | Strategic decisions; financial decisions | **P0** |
| SRE / monitoring | Catch outages, job failures, data drift | `job_runs`, Sentry, `/health`, `/admin/job_health` | Alerts → orchestrator | Cron healthcheck + Slack/email webhook | 95% | Real incident response | **P0** |
| Data quality | Verify freshness; verify accuracy; verify pipeline outputs | Supabase row counts; reasonableness checks | Daily DQ report | SQL cron + Claude | 90% | Methodology changes | **P1** |
| Code review | Review PRs, flag risk | GH PRs | Approve / comment / request changes | `gh` CLI + Claude Code | 70% | Merges to main | **P0** |
| Engineering | Pick up backlog issues; implement; open PRs | GH issues + backlog.md | PRs | Claude Code | 70% | Final merge approval | **P1** |
| QA | Run test suite + smoke tests + E2E on PRs | GH PRs | Pass/fail | CI + Claude | 95% | — | **P0** |
| Bug intake / user support | Ingest user-reported bugs; triage; ack | Email, Sentry, App Store reviews | GH issues + drafted email replies | Email API + Claude Code | 80% | Sensitive replies | **P1** |
| Growth / AI UGC | Auto-generate market posts; auto-respond to FinTwit; SEO content | Daily macro/sector snapshots; events | Tweets, blog posts | LLM + scheduled poster | 70% | Posting permission per channel | **P2** |
| Analytics | Track KPIs; report deltas | PostHog / event logs | Daily KPI report | DB queries + Claude | 95% | — | **P1** |
| Release / DevOps | Cut releases; tag; deploy | main branch | Deployed image | GH Actions + Claude oversight | 80% | Final production push approval | **P0** |
| Docs / memory | Keep AGENTS.md, CLAVIX_TRUTH.md, REFERENCE current | Code changes | Updated docs | Claude Code + post-merge hook | 90% | Truth doc changes | **P1** |
| Cost / finance | Track API spend, infra spend, projected runway | Render/DO/Stripe/Apple/Polygon/Finnhub/Minimax invoices | Weekly cost report | Email forwarder + Claude | 80% | Plan upgrades | **P2** |
| Security | Watch for token leaks, dependency CVEs, RLS regressions | Dependabot, GitHub secret scanning, `git diff` | Issues + PRs | Claude + tooling | 70% | Any cred rotation | **P1** |

**GitHub workflow design.**
- Every bug or task becomes a GH issue (manually or via the Bug Intake dept).
- Issues are tagged with `area:<dept>` and `priority:<P0..P3>`.
- The Engineering dept loop: pick highest-priority unassigned issue → implement on a `feature/<issue>` branch → open PR → tag for review.
- Code Review dept reviews; QA dept runs tests; if both pass, the PR is *ready* but not merged.
- A human-approval gate merges to `main`.
- Merge to `main` → CI + deploy.

**PR workflow.** Same as above. PRs link to the issue they close, summarise changes, include test results.

**CI/CD gates.**
- ✅ Backend tests pass.
- ✅ Compileall passes.
- ✅ iOS build succeeds on iPhone 17.
- ✅ Smoke tests pass post-deploy.
- ✅ No new Sentry errors in the 1 hour post-deploy (canary monitoring).

**Monitoring workflow.**
- Every 30 min: SRE cron queries `job_runs` for missed tier-1 jobs.
- Every 5 min: `/health` is checked from outside (UptimeRobot, Better Stack).
- Sentry catches exceptions.
- Daily 8am: Orchestrator writes a 200-word "yesterday at Clavix" summary into an internal channel.

**Daily command center report.** Generated at 8am ET. Sections:
1. Pipeline health (job_runs from last 24h).
2. New errors (Sentry top 5).
3. User signups (waitlist + active users).
4. Cost (API spend vs budget).
5. PRs awaiting review.
6. Top 3 things the orchestrator suggests doing today.

**Bug intake workflow.** A `bugs@getclavix.com` mailbox is monitored; each new email becomes a GH issue via a Zapier/n8n forward or a simple Python cron polling IMAP. Sensitive replies are drafted for human review.

**AI UGC workflow.** Daily 6am: cron picks the most-impactful overnight macro/sector event from `macro_regime_snapshots` + `sector_regime_snapshots`, drafts a 2-tweet thread, queues to Typefully or Buffer. Human approves with one click.

**Hard safety rule (reinforced).** AI can detect, draft, test, and open PRs. AI should not merge, deploy, delete data, modify secrets, change billing/auth/security, auto-post marketing without human approval, or change financial scoring formulas without human approval. Every cron that touches user-visible scoring or money has to be runnable in `--dry-run` mode and gated behind a `_DEPLOY_LOCK` env var.

### 11. Backlog audit

`backlog.md` is well-organised but **rooted in the VisualQA-mockup data gap audit**, not in launch-readiness. The P0/P1/P2 items there are tactical iOS data-contract gaps; most have been addressed by P3–P8 Codex runs.

| Backlog item | Still relevant for launch? | Action |
|---|---|---|
| P0 #1 (Today envelope) | ✅ done in P5 | close |
| P0 #2 (portfolio value/day change) | ✅ done in P5 | close |
| P0 #3 (value-weighted composite) | ⚠️ done in P4 but Digest still uses equal-avg | open a new issue |
| P0 #4 (holdings envelope) | ✅ done | close |
| P0 #5 (score history) | ⚠️ depends on backfill_14d being run | open a new issue |
| P0 #6 (ticker detail extensions) | ✅ done in P6/P7 | close |
| P0 #7 (methodology contract) | ✅ done in P6 | close |
| P0 #8–#11 (fundamentals, macro, sector, digest) | ✅ done in P3–P6 | close |
| P0 #12–#14 (alerts v2, alert detail, shared-event detail) | ⚠️ alerts v2 columns added but iOS Alert model not updated for `read_at`/`severity` | open iOS issue |
| P0 #15 (search results enrichment) | partial | open issue |
| P0 #16–#17 (outside-universe path) | backend done, iOS missing | open iOS issue |
| P0 #18 (Free limits enforcement) | partial | verify and close |
| P0 #19 (limited-data/insufficient-history/offline state semantics) | partial | open polish issue |
| P0 #20 (sector taxonomy) | unverified | open audit issue |
| All P1 items | mostly relevant, some done | groom |
| All P2 items | post-launch | defer |

**Recommendation.** Archive the existing `backlog.md` as `backlog_visualqa_2026-05-25.md` and start a new `backlog.md` framed around the 21-day plan in `roadtolaunch.md`. Group by `area:` not by `P0/P1/P2`.

---

## Data and Trust Audit

| Data | Exists? | Source | Refresh cadence | Frontend uses it correctly? | Stale/mock/silent-fail? |
|---|---|---|---|---|---|
| Position prices | yes | Polygon | every 5–15 min during market hours (cron) | yes | none observed |
| Position P&L | yes | derived | with prices | yes | none |
| Portfolio composite grade | yes | `portfolio_risk_snapshots` (value-weighted) | daily 06:45 ET | Holdings: yes. Digest: equal-avg fallback. | **inconsistent across screens** |
| 5-dimension portfolio rollup | yes | `portfolio_risk_snapshots` | daily | partially | newly added; needs verification day-of-launch |
| Per-ticker composite | yes | `ticker_risk_snapshots` | daily 06:00 ET | yes | first-day after deploy needs `backfill_14d` to seed history |
| Per-ticker dimension inputs | yes | `dimension_inputs` JSONB | per dimension cadence per `CLAVIX_TRUTH §17` | yes | depends on per-dim cron health |
| News articles | yes | Finnhub primary + Google News RSS auxiliary | every 4h active, 24h dormant | yes | `Limited Data` honest fallback exists |
| Sentiment scores | yes | Minimax LLM | on ingestion + bulk every 2h | yes | depends on Minimax availability |
| Peer comparisons | yes | `peer_groups` table | weekly | yes | empty until first weekly run |
| Sector medians | yes | `sector_medians` | weekly | yes | same |
| Macro regression coefs | yes | `dimension_inputs.macro_exposure` | monthly + daily narrative | yes | monthly job ran in P6-5; verify |
| Earnings calendar | yes | Finnhub | daily 04:00 ET | yes | new in P5 |
| ETF holdings (SPY/QQQ/VTI) | yes | issuer APIs | monthly | yes | new in P8-2 |
| Score history (90d) | sparse | `ticker_risk_snapshots` daily writes | daily | yes | needs `backfill_14d` + 75 more days |
| Alert delivery | yes (DB) | Alert evaluation job | daily 17:00 + on-event | partial | APNs no-op until `.p8` deployed |
| Portfolio value | yes | derived (positions × current_price) | with prices | yes | none |

---

## P0/P1/P2/P3 Issues

Definitions:
- **P0** — launch blocker; legal/security/data trust failure.
- **P1** — must fix before launch.
- **P2** — can ship shortly after.
- **P3** — polish.

### P0

| ID | Area | Problem | Evidence | Impact | Fix | Effort | Deps | Owner |
|---|---|---|---|---|---|---|---|---|
| P0-1 | Legal | No Privacy Policy, ToS, Refund, Methodology pages on website | 404 on `/privacy`, `/terms`, `/refund`, `/methodology`; footer links to them | App Store rejection; legal exposure | Write + publish 4 static HTML pages; have one lawyer review the SEC-disclaimer language | 1 d + lawyer review | None | Sansar |
| P0-2 | Legal/Org | Apple Developer Program not enrolled | `project.yml` `DEVELOPMENT_TEAM: ""`; backlog.md explicitly notes deferred | No TestFlight, no App Store, no APNs key | Enrol today; wait 24–48h | 1h work + wait | Andover Digital LLC EIN | Sansar |
| P0-3 | Push | APNs key not deployed | `/health` returns `"apns":"missing"` | Push notifications silently fail | Deploy `.p8` to VPS `/etc/secrets/apns.p8` once Apple Dev account exists | 1h | P0-2 | Sansar |
| P0-4 | Brand | Banned brand string in APNs default | `backend/app/services/apns.py:75` says `"Clavynx Update"` | First push every user receives says wrong word | One-line fix | 5 min | None | Sansar |
| P0-5 | Data trust | Portfolio composite grade inconsistent across Digest vs Holdings | `MOCK_TO_LIVE_AUDIT.md` table row | Two screens, two grades, instant trust break | Make Digest read `portfolio_risk_snapshots` instead of computing equal-avg | 2h | P4 cron must be running | claude-code |
| P0-6 | Security | `subscription_tier` is self-PATCHable | `routes/preferences.py` allows field; no server-side gate | Free Pro to anyone with the spec | Server-side block writes on `subscription_tier`; only admin/webhook can set | 1h | None | claude-code |
| P0-7 | iOS | URL scheme missing `clavix://` | `Info.plist:14` registers only `clavis://` | Deep links from email/marketing won't open the app | Add `clavix` to `CFBundleURLSchemes`; route both schemes to same handler | 30 min | None | claude-code |
| P0-8 | iOS | `armv7` capability is wrong | `Info.plist:48-50` | Could fail App Store validation | Change to `arm64` | 5 min | None | claude-code |
| P0-9 | Data trust | Can't prove cron is firing in prod | No `job_runs` query in audit; only the schedule file | Freshness UI may be lying | Build `/admin/job_health` route; query the last 7 days | 3h | None | claude-code |
| P0-10 | Data | `backfill_14d` may not have run | No proof in commits | Day-1 users see `—` on every "was AA 5d ago" delta | Run `python -m app.jobs.run backfill_14d` against prod | 1h compute + verify | None | Sansar |

### P1

| ID | Area | Problem | Fix | Effort |
|---|---|---|---|---|
| P1-1 | iOS | No first-run "informational, not advice" disclaimer | Full-screen accept-checkbox on first launch; write to `user_legal_acks` | 4h |
| P1-2 | Web | No analytics on site | Add Plausible or PostHog | 1h |
| P1-3 | iOS | No crash reporting | Add Sentry-Cocoa | 2h |
| P1-4 | iOS | Outside-universe degraded-mode add path is invisible in UI | Plumb `allow_outside_universe=true` + banner | 4h |
| P1-5 | iOS | Alerts v2 columns not consumed (`read_at`, `severity`, `destination_*`) | Update `Alert.swift` + AlertsView unread badge | 3h |
| P1-6 | Web | No demo video / animated preview | Record sim + embed | 1d (designer-ish) |
| P1-7 | Backend | No staging environment distinct from prod | Spin up `clavix-staging` on Render with own Supabase project | 0.5d |
| P1-8 | Backend | No post-deploy smoke tests | Curl `/today`, `/holdings`, `/tickers/AAPL`, `/tickers/AAPL/methodology` in `deploy-prod.yml` | 1h |
| P1-9 | Backend | Fix pre-existing test failure `test_attach_decoded_google_news_urls_rewrites_wrapper_urls` | Debug + fix | 2h |
| P1-10 | Email | No transactional email | Wire Resend or SendGrid; replace Supabase default templates | 4h |
| P1-11 | Backend | No `/admin/job_health` endpoint | Build it; expose for the daily command center | 3h |
| P1-12 | Brand | App Store metadata + screenshots + icon validation | Author title/subtitle/description/keywords; capture 5 sim screenshots; verify icon at all sizes | 1d |
| P1-13 | iOS | Settings legal links 404 | Re-point after P0-1 | 5 min |
| P1-14 | Legal | First-run disclaimer audit trail | `user_legal_acks(user_id, version, accepted_at, ip, ua)` table | 2h |
| P1-15 | Backend | Self-elevation in `subscription_tier` exists in test fixtures too | Verify tests don't accidentally encode the bug | 1h |
| P1-16 | iOS | Migrate Settings + Onboarding screens to `DesignSystem/` primitives | Replace legacy tokens screen-by-screen | 1d |
| P1-17 | Pipeline | Daily cron health alerting | 30-min cron that pings a webhook if any tier-1 job hasn't completed in expected window | 3h |
| P1-18 | Trust | Render `freshness.as_of` labels in iOS UI on Today/Holdings/Ticker | UI work | 4h |
| P1-19 | Marketing | Press kit | 5 high-res images + icon + about + founder | 1d |
| P1-20 | Marketing | App Store screenshots (5 required) | Sim capture, post-process | 4h |

### P2

| ID | Area | Problem | Fix | Effort |
|---|---|---|---|---|
| P2-1 | Payments | No StoreKit 2 integration | Server webhook + iOS StoreKit client + entitlement table | 5d |
| P2-2 | Payments | No Stripe fallback (for web/non-iOS billing later) | — | defer |
| P2-3 | Brokerage | iOS SnapTrade UI is stub | Wire the existing backend routes; deeplink callback handler | 2d |
| P2-4 | Backend | OpenAPI spec committed | Generate + commit | 2h |
| P2-5 | Backend | API versioning strategy | Add `X-Clavix-API-Version` header | 1d |
| P2-6 | iOS | Migrate remaining screens to `DesignSystem/` | — | 3d |
| P2-7 | Growth | AI UGC daily tweet automation | Cron + Typefully + 1-click approval | 3d |
| P2-8 | Docs | Public methodology page rendered from `docs/PUBLIC/methodology.md` | Build step | 4h |
| P2-9 | Web | Blog directory + 2 launch posts | — | 2d |
| P2-10 | Analytics | KPI dashboard | PostHog dashboard + weekly auto-report | 1d |
| P2-11 | Testing | XCTest target + 5 snapshot tests | — | 1d |
| P2-12 | Testing | E2E user flow integration test | — | 1d |

### P3

- Annual subscription plan (revisit v1.1)
- Web app
- Android app
- Multi-portfolio
- CSV import UI
- Trending search rows
- Cost-basis adjustments for splits/spinoffs
- Custom alerts
- Universe expansion beyond S&P 500

---

## Launch Blockers (true blockers only)

1. **No Apple Developer Program enrolment** (P0-2)
2. **No Privacy / Terms / Refund / Methodology pages on website** (P0-1)
3. **No real legal entity verification + ToS draft + lawyer review** (overlaps with P0-1)
4. **APNs missing in prod** (P0-3)
5. **Portfolio composite grade inconsistent across Digest vs Holdings** (P0-5)
6. **`subscription_tier` self-elevation** (P0-6)
7. **App Store metadata + 5 screenshots + icon** (P1-12, P1-20)
8. **First-run informational-only disclaimer in-app + audit row** (P1-1, P1-14)
9. **No payments → cannot launch the marketed "Pro $20/mo, 14-day trial"** — but a closed beta with no money sidesteps this. If 21-day public+paid is the goal, this is also a blocker.

---

## Unknowns

Updated 2026-05-25 with user round-2 answers.

**Resolved (user confirmed):**
- ✅ Andover Digital LLC is formed. EIN exists but document is lost — search Day 0; call IRS 800-829-4933 for 147C if not found.
- ✅ No business bank account yet — Mercury chosen, Day 1 application.
- ✅ No Apple Developer Program enrolment yet — Day 0 long-pole.
- ✅ `backfill_14d` has never been run — Day 0 task in tmux.
- ✅ Scheduler code shipped per commits `10c587ff0` (P3) → `aa31c7a2e` (P8); user will SSH-verify cron is actually firing as Day 0 task.
- ✅ News pipeline just finished hardening (commits `f277ea442` → `b55b02168`) — Day 2 live-fire test scheduled.

**Still unknown (need user action or external access):**
- Is the Sentry DSN actually set in Render/VPS env? (DSN value not in repo, correctly.)
- What's the current monthly bill for Minimax / Polygon / Finnhub?
- Are RLS policies on every user-data table enforced in the live DB? (Day 5 task is an SQL audit.)
- Is the VPS firewall locked down or wide-open?
- Has a securities lawyer ever reviewed the marketing copy + in-app letter-grade language? (Day 1: email 3 lawyers.)
- How many waitlist signups are currently in `waitlist_signups`? (Determines invite-batch sizing on Days 19–21.)
- D-U-N-S Number exists for Andover Digital LLC? (Apple's Org enrolment requires it; free via Dun & Bradstreet but can take 1–3 days.)

---

## Recommended Next Action

**Tonight, before bed, in this order:** (1) SSH into the VPS, verify `job_runs` for the last 7 days, kick off `backfill_14d` in a tmux session. (2) Search Gmail/Outlook/Documents for the lost EIN (1h cap). (3) Start Apple Developer Program enrolment with Andover Digital LLC. (4) Submit Mercury application. (5) Email 3 securities lawyers requesting a 1h call this week.

That's <3 hours of your time and starts five different 24-48h async clocks (cron sanity check, EIN retrieval if not found, Apple verification, Mercury approval, lawyer scheduling). Tomorrow morning you wake up with the score-history backfill complete, the Apple/Mercury/Lawyer clocks running, and you only need to call IRS at 7am ET if the EIN search came up empty.
