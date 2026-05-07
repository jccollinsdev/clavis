# Clavix — Production Incompletion Audit

**Date:** 2026-04-22
**Scope:** Full local repo (`backend/`, `ios/`, `supabase/`, `docs/`, infra), marketing site repo `jccollinsdev/clavix-dashboard`, product and methodology docs.
**Lens:** Why this still feels like an MVP, not a finished product. Gap-finding only.
**Method:** Verified against actual code at audit time. The previous `AUDIT.md` was consumed as prior art and re-verified — items already fixed are noted as such and not double-counted.

---

## Phase 1 — What Clavix Claims To Be

From `README.md`, `docs/PRODUCT/methodology.md`, `docs/PRODUCT/pricing.md`, `docs/STATE/project_state.md`, marketing site `getclavix.com`:

- **The promise.** "Know where your portfolio stands before the market tells you." A 30-second morning risk read: A–F grade per holding + portfolio, what changed overnight, what to look at first, with cited rationale.
- **The positioning.** Portfolio risk intelligence, not investment advice. Aimed at self-directed retail investors with portfolio fluency (archetypes, sector exposure).
- **The pricing.** $20/mo or $99/yr Pro tier (`docs/PRODUCT/pricing.md`). Free = 5 holdings, daily digest, A–F grades. Pro = unlimited holdings, brokerage sync, full methodology, advanced alerts.
- **The promised features.** Brokerage sync (SnapTrade), APNs push, morning digest, grade-change alerts, methodology transparency, account deletion + export, multi-surface news reading, ticker search, watchlist.

## Phase 2 — What Clavix Actually Is Today

Verified by code inspection:

- **iOS app** — SwiftUI, iOS 17+. Real UI across 5 tabs + onboarding + ticker detail + news + settings. Typography and design system are genuinely opinionated, not stock UIKit.
- **Backend** — FastAPI on DO VPS via Cloudflare Tunnel. JWT middleware uses local HS256 verify with `auth.get_user` fallback (good). `/account` delete + export routes live and wired to Settings. Manual-analysis rate limit = 3/24h. Digest `force_refresh` cooldown = 1h.
- **Pipeline** — 17-stage news→relevance→classifier→analysis→scoring→compile path, MiniMax-only LLM. Shared-cache S&P 500 ticker intelligence layer is populated.
- **DB** — Supabase Postgres, RLS on user tables. `prices` RLS tightened to SELECT-only for auth users per recent completions.
- **Infra** — Single Docker backend, no Redis, APScheduler in-process. Sentry scaffolded. UptimeRobot on `/health`. Admin UI with cookie password.
- **What's wired but not live** — APNs (no `apns.p8` on VPS), SnapTrade production env vars (missing on VPS), payments (zero StoreKit/RevenueCat code), marketing CTAs (site is waitlist-only with "1 investor" counter).

## Phase 3 — Product Reality Gap

| Claim | Reality | Mismatch |
|---|---|---|
| "Pro at $20/mo, 5-holding free cap" | No payment code. No entitlement checks. `POST /holdings` has no cap. | Pro is uncollectable; free tier is unbounded. |
| "Grade-change alerts, morning digest push" | APNs unconfigured. Settings toggles fire nothing. | Alert UX is theater. |
| "Connect your brokerage for automatic sync" (marketing site) | SnapTrade wired in code, not provisioned on VPS. | Onboarding step 5 will break for every real user. |
| "Delete account / export data" (compliance requirement) | Routes present (`/account`), Settings has buttons. | Functional. ✅ |
| "Informational only, algorithmically generated" | Mostly honest. Still synthesizes prior-score deltas? — recently fixed per `project_state.md`; verify on device. | Needs a visual QA pass. |
| "Portfolio intelligence for self-directed investors" (marketing) | No App Store link, 1-person waitlist, no testimonials, no pricing on site. | Zero social proof. |

---

## Top 10 Reasons It Still Feels Like An MVP

1. **You can't pay for it.** Zero StoreKit, zero RevenueCat, zero Stripe. The entire "Pro" concept is a label in `SettingsView.swift` and rows in a pricing doc. Until this ships, every "Pro feature" gate is cosmetic.
2. **Free tier has no enforcement.** `backend/app/routes/holdings.py:45` `create_holding` takes any holding count. A free user can add 500 positions and fully exhaust your MiniMax budget. The cornerstone of the $20 pricing model is not wired.
3. **Push notifications don't exist yet.** `backend/app/config.py` expects `apns.p8` at `/app/apns.p8`; `docker-compose.yml` mounts the dir; `main.py:116-123` logs `startup_apns_incomplete` as a WARNING and keeps running. Every alert/digest toggle in the app is a lie until this key is deployed.
4. **Brokerage connect is pre-wired but not live.** `SNAPTRADE_CLIENT_ID` and `SNAPTRADE_CONSUMER_KEY` are missing from VPS `.env` per `project_state.md` blockers. Onboarding step 5 — the emotional peak of the flow — will surface a generic error for every new account.
5. **The marketing site is a waitlist, not a product site.** `getclavix.com/index.html:822` says "Join 1+ investor on the waitlist". No App Store badge, no TestFlight link, no published pricing, no founder, no screenshots of the *risk science*. A prospect can't convert; they can only hope.
6. **Three product identities still shipping.** CFBundleDisplayName = "Clavix" ✓, API title = "Clavix API" ✓, but the URL scheme is still `clavis://` (`ios/Clavis/Resources/Info.plist:20`), the Xcode project/dir/Swift types are all `Clavis*`, and the production domain is `clavis.andoverdigital.com`. Debug logs, crash reports, oauth callbacks, and file paths will all confuse you and anyone who inspects them.
7. **Info.plist has pre-launch debt that blocks App Review.** No `PrivacyInfo.xcprivacy`. ATS still whitelists `trycloudflare.com` (`Info.plist:64-74`) even though prod is on a named tunnel. `UIRequiredDeviceCapabilities` claims `armv7` (`Info.plist:52`) which is 32-bit ARM — iOS 17 is arm64-only, so this entry is either ignored or will get the binary rejected on validation.
8. **Supabase schema drift vs production.** `project_state.md` explicitly lists "Reconcile repo-to-production drift in Supabase schema/migrations" as an active focus item. `supabase_schema.sql` is tracked but does not match the live DB; `supabase/migrations/` and `supabase/functions/` are partial. A fresh environment cannot be reproduced from the repo. That is an "MVP project", not a "product".
9. **Cost/abuse safety is half-built.** `/trigger-analysis` has a 3/24h guard (good). `/digest?force_refresh=true` has a 1-hour cooldown (good). But `/brokerage/sync` runs synchronously in-request, `POST /holdings` fires a background `refresh_ticker_snapshot` on every create with no dedupe/debounce, and there is no global daily MiniMax dollar ceiling — only a 1.25s per-request throttle. One unbounded background loop burns your budget overnight.
10. **The app is a single-worker single-VPS setup with no DR story.** `docker-compose.yml` bind-mounts `./backend/app` into the container (dev pattern, not prod). APScheduler is in-process — if you ever run 2 workers every job fires twice. There's no automated DB backup runbook documented. No Redis, no message queue, no secondary region. UptimeRobot will tell you it's down, nothing tells you how to bring it back.

---

## Incompletion Map — Verified Findings

Severity: **P0** launch blocker, **P1** credibility/compliance, **P2** polish, **P3** cleanup. "Claude fixable" = resolvable in this repo without external provisioning.

| ID | Area | Type | Sev | Issue | Evidence | Why it feels incomplete | Fix | Claude fixable? |
|---|---|---|---|---|---|---|---|---|
| I01 | Monetization | Missing | P0 | No payment system at all | no StoreKit code in `ios/Clavis/`; no `/subscription` route in `backend/app/routes/`; pricing.md says $20/mo Pro | You cannot sell the product | Implement StoreKit 2 + RevenueCat, add `/subscription/receipt`, write `subscription_tier` to `user_preferences` | Code yes, App Store config no |
| I02 | Monetization | Missing | P0 | Free 5-holding cap not enforced | `backend/app/routes/holdings.py:45-79` `create_holding` has no tier/count check | Pricing model is a slideware claim | Add `tier = _user_subscription_tier(supabase, user_id); if tier=='free' and count(positions)>=5: 402` | Yes |
| I03 | Push | Partial | P0 | APNs never deployed | `backend/app/main.py:116-124` logs warning and starts; `config.py:22-25` expects missing `apns.p8`; `project_state.md` blockers list it explicitly | Alert toggles fire nothing | Deploy Apple `.p8` key; set `APNS_KEY_ID`/`TEAM_ID` on VPS; verify via existing `/test-push` | Partial — key is Apple-gated |
| I04 | Brokerage | Partial | P0 | SnapTrade prod env vars missing | `backend/app/config.py:27-29`; `project_state.md` technical blockers | Onboarding step 5 errors for every new user | Provision env vars; make onboarding gracefully skip when service is `not_configured` | Partial — provisioning is Apple/SnapTrade-gated |
| I05 | Compliance | Missing | P0 | No `PrivacyInfo.xcprivacy` in iOS bundle | `ios/Clavis/Resources/` contains only `Assets.xcassets`, `Fonts`, `Info.plist` | iOS 17 App Review requirement for SDKs + data categories | Generate PrivacyInfo.xcprivacy covering SnapTrade, Supabase, Sentry, Finnhub, Polygon, MiniMax | Yes |
| I06 | Compliance | Weak | P1 | ATS still whitelists `trycloudflare.com` | `ios/Clavis/Resources/Info.plist:64-74` | Stale dev config ships to prod; small but reviewable | Delete the `NSExceptionDomains` block entirely | Yes |
| I07 | iOS build config | Weak | P1 | `UIRequiredDeviceCapabilities` = `armv7` | `ios/Clavis/Resources/Info.plist:50-53` | iOS 17 is arm64 only — this is factually wrong and can flag App Store validation | Replace with `arm64` | Yes |
| I08 | Branding | Partial | P1 | URL scheme still `clavis://`; internal type/dir names still `Clavis` | `Info.plist:20`; `ios/Clavis/*`; `backend/app/config.py` SnapTrade redirect | Product is Clavix; paths aren't. Trust + support friction | Add dual-scheme `clavix://` alongside `clavis://`; plan rename post-v1 | Yes (dual-scheme now) |
| I09 | Marketing | Weak | P1 | Site is a waitlist with "1 investor" counter; no pricing, no screenshots of the risk engine, no App Store link | `/tmp/clavix-dashboard/index.html:822,1001` | Product site looks abandoned/unvalidated — a prospective user lands and bounces | Publish pricing page, founder note, methodology excerpts, App Store badge, replace live counter with "Early access" copy | Yes |
| I10 | Marketing | Missing | P1 | Marketing site has no published pricing page | no `pricing.html` in `clavix-dashboard/`; only `privacy/terms/refund/methodology` | "How much?" is unanswered on first visit | Add `pricing.html` reflecting `docs/PRODUCT/pricing.md`, link from nav | Yes |
| I11 | DB hygiene | Weak | P0 | Repo schema drifts from prod Supabase | `project_state.md` `current_focus` line 15; migrations directory partial | Cannot reproduce env; migration history is lost | Dump current prod schema, reconcile `supabase_schema.sql`, commit ordered migrations under `supabase/migrations/` | Partial — needs DB access |
| I12 | Cost | Weak | P1 | No daily MiniMax cost ceiling | `backend/app/services/minimax.py` has `minimax_min_interval_seconds=1.25` only | One runaway background loop = uncapped bill | Add per-day token/cost counter in DB, refuse calls over ceiling, expose in admin | Yes |
| I13 | Cost | Weak | P1 | `/brokerage/sync` runs sync in-request | `backend/app/routes/brokerage.py` (sync path to SnapTrade, 10–30s) | Bad onboarding UX; blocks worker | Convert to background job with `analysis_runs`-style polling | Yes |
| I14 | Holdings UX | Weak | P2 | `POST /holdings` stalls on provider calls | `holdings.py:54` `ensure_ticker_in_universe` may call Finnhub/Polygon with no timeout contract | First "Add position" can hang 10–20s | Wrap in `asyncio.wait_for`, fall back to minimal-metadata row + background enrichment | Yes |
| I15 | Scheduler | Weak | P1 | APScheduler in-process, single Uvicorn worker assumed | `backend/app/main.py:125` `start_scheduler()` | Multi-worker deploy would double-fire jobs; restarts lose state until recomputed | Document `--workers 1` invariant; plan Postgres-backed scheduler before horizontal scale | Yes (doc), no (full switch) |
| I16 | Infra | Weak | P1 | `docker-compose.yml` bind-mounts source in prod pattern | `docker-compose.yml` volumes | Source drift between repo and container possible | Build & tag image, pull by tag on VPS; stop bind-mount in prod compose | Yes |
| I17 | Infra | Missing | P1 | No automated DB backup runbook in `docs/GUIDES/` | no backup/restore guide checked in | Data loss story is "call Supabase support" | Document Supabase PITR verification + monthly export script + restore drill | Yes |
| I18 | Admin surface | Weak | P2 | `/admin` is password-only, no lockout, no audit log | `backend/app/routes/admin.py` cookie auth | Brute-forceable if URL leaks | Add failed-attempt lockout, IP allowlist, admin action log | Yes |
| I19 | Debug middleware | Weak | P2 | Still captures full request bodies when enabled | `backend/app/main.py:186-224` | Works because `enable_debug_surfaces` refuses prod env (`main.py:107-111` ✓); still leaky in staging | Redact password-like fields; cap body length | Yes |
| I20 | Empty states | Weak | P2 | Dashboard/Digest copy for "no positions" vs "generating" vs "failed" not fully distinct | `backend/app/routes/digest.py` return shape doesn't surface `status` variants cleanly | User can't tell whether to add a holding or wait | Return `status: no_positions/awaiting/generating/ready/failed` and switch iOS copy | Yes |
| I21 | Error handling | Weak | P2 | Generic errors on iOS for backend failures | `ios/Clavis/Services/APIService.swift` decodes minimal error | User has no recovery path | Decode FastAPI `detail`; distinguish cold start, network, auth | Yes |
| I22 | Onboarding | Weak | P2 | Brokerage step failure path not clearly tested when SnapTrade is `not_configured` | onboarding flow assumes working SnapTrade; project_state admits VPS is missing creds | First-run broken on prod today | Add a `/brokerage/health` probe and skip step cleanly with "We'll enable this soon" | Yes |
| I23 | Auth | Missing | P1 | No Sign in with Apple | `ios/Clavis/Views/Auth/LoginView.swift` — email/password only | Apple requires SIWA if other SSO is added, and it reduces friction | Add SIWA via Supabase (auth provider + iOS entitlement) | Partial — needs entitlement |
| I24 | Auth | Weak | P2 | Terms/Privacy footer on LoginView not verified | need visual audit | Trust signal missing | Add small footer with tappable links to getclavix.com pages | Yes |
| I25 | Trust | Weak | P1 | No visible "last updated" + source attribution on scores in UI flows we haven't re-verified | reference `recent_completions`: freshness timestamps added — need visual QA | Retail users need to see "as of 9:12 AM ET, based on 14 sources" | Visual QA pass; anywhere a grade appears it must have a timestamp + source count | Yes |
| I26 | Methodology | Weak | P2 | Methodology page is on marketing site only; in-app link exits to Safari | `ios/Clavis/Views/Settings/SettingsView.swift` Methodology link; `/tmp/clavix-dashboard/methodology.html` | Users who tap "Why this grade?" lose session | Mirror key methodology in-app as native view; keep web page as canonical reference | Yes |
| I27 | Observability | Weak | P2 | `/health` now has service flags, but no user-facing status page | `backend/app/main.py` health JSON | When push breaks, users see silent no-op | Publish status.getclavix.com (or use a free hosted page) reading `/health` | Yes |
| I28 | Observability | Missing | P2 | No MiniMax per-request cost logging | `backend/app/services/minimax.py` | Can't budget-forecast or catch drift | Log `tokens_in`, `tokens_out`, `est_cost_usd`; daily roll-up on admin | Yes |
| I29 | Dead code | Weak | P3 | MiroFish references may linger in docs/schema (`mirofish_used` column, etc.) | `supabase_schema.sql`, iOS decode path | Signals abandonment; confuses new contributors | Migration to drop column; grep pass to remove residue from docs & models | Yes |
| I30 | Content depth | Weak | P1 | Core scoring rationale is AI-generated; depth + consistency not audited at scale | `backend/app/pipeline/risk_scorer.py`, `portfolio_compiler.py`; prior backfill QC in `project_state.md` notes "synthetic zero-share backfill rows sometimes produced false 'no position / wait-and-see / entry catalyst' language" | Retail trust depends on rationale feeling written, not auto-filled | Add golden-set eval: 20 hand-graded tickers, nightly diff LLM output vs. golden; reject + retry when rationale pattern-matches known failure modes | Yes |
| I31 | Content depth | Weak | P2 | Digest / positions repetition risk at scale with single LLM + same prompts | `portfolio_compiler.py`, `position_report_builder.py` — no templating variance | Users on day 5 will see the same phrasing | Add style rotation / few-shot diversity set, post-generation similarity check | Yes |
| I32 | Data | Weak | P2 | `positions` lacks `currency`, `cost_basis_method`, `tax_lot` | `supabase_schema.sql:25` | Multi-lot / non-USD investors can't trust numbers | v1: copy labels it "Average cost (USD)"; v2: schema migration | Yes (copy) |
| I33 | Onboarding | Weak | P2 | DOB + risk ack collected but no enforcement story for the age gate beyond client check | onboarding stores DOB | If client is bypassed, no server check | Enforce `is_adult` server-side from DOB when storing; log rejections | Yes |
| I34 | Alerts | Weak | P2 | No user-facing alert history export or "mute this ticker" | `ios/Clavis/Views/Alerts/AlertsView.swift` timeline, no per-ticker mute | Noisy users abandon alerts silently | Add mute-ticker toggle; write to `user_preferences.alert_mutes[]` | Yes |
| I35 | Settings | Weak | P2 | Terms/Privacy/Refund/Methodology links jump to web, not mirrored in-app | `SettingsView.swift` external links | Users who bounce to Safari may not return | Render inline sheets for legal pages | Yes |

---

## Critical Missing Systems

These are systems a real product has; Clavix doesn't yet.

1. **Payments + entitlement.** No StoreKit, no RevenueCat, no receipt validation, no `subscription_tier` write path, no paywall screen. Blocks revenue, blocks free-cap enforcement, blocks every "Pro" gate.
2. **Push notification delivery.** Code path exists (`apns.py`, device token persistence), key + setup do not. Every notification toggle is theater.
3. **Privacy manifest + App Review assets.** `PrivacyInfo.xcprivacy`, accurate `UIRequiredDeviceCapabilities`, ATS cleanup, App Tracking Transparency declaration. Without these the app cannot be submitted.
4. **A real marketing funnel.** `getclavix.com` is a waitlist with no pricing, no App Store badge, no screenshots that sell the *insight*, and a public "1 investor" counter that actively works against conversion.
5. **DB migration + disaster recovery.** No canonical migration chain in `supabase/migrations/`, schema drifts from prod, no documented backup/restore runbook.
6. **Cost ceiling + observability.** No MiniMax per-request cost log, no daily spend cap, no admin cost surface. One regression = a bad bill.
7. **Status page / health surface.** `/health` is structured but not exposed to users. When push or brokerage silently fail, users think the product is broken.
8. **Eval harness for LLM outputs.** No golden-set regression testing for rationale quality, digest variance, or failure-mode pattern detection.
9. **In-app legal + methodology.** Legal and methodology live only on the web; in-app CTAs bounce users out.

---

## Partial Features

Features that exist in code but are not complete products.

1. **Brokerage sync** — Wired end-to-end in code (`backend/app/services/snaptrade.py`, onboarding step 5, Settings). Not provisioned on VPS. Blocking.
2. **Morning digest push** — Scheduler exists, notifier exists, APNs key does not.
3. **Pro tier** — Exists as a label, flag, and a single gated refresh in `TickerDetailView`. No payment, no cap, no real gating anywhere else.
4. **Ticker shared cache / S&P backfill** — Backfill works locally, but "backfill QC" in `project_state.md` flags real content-quality misses (spillover claims, synthetic-position phrasing). Needs eval harness before it's trustworthy.
5. **Alerts** — Alerts render, are clickable, carry severity. No per-ticker mute, no alert settings granularity beyond broad toggles, no "why this alert" explanation per item.
6. **Account deletion** — Routes + UI live. Needs re-auth step on iOS and a visible success→sign-out flow. Verify cascade on all tables (backend loop looks correct).
7. **Onboarding** — 4 steps, DOB picker present, preferences step writes defaults, brokerage step fails on prod today (see I04). Notification permission request is "status-aware" — needs device QA.
8. **Dashboard** — Hero gauge, stat strip, change feed; relies on digest freshness. Empty-state handling depends on distinct `status` values that backend doesn't consistently return (see I20).
9. **News surface** — Built, but `project_state.md` lists "remove the non-essential News surface" as a day-1 focus — it's a feature the team is about to subtract. That's a signal it isn't finished enough to retain.

---

## UX & Flow Breakpoints

Where the user loses trust or gets confused.

- **First run, SnapTrade step** (I04). Clicks "Connect brokerage", hits error, questions whether the app is real.
- **First run, notification toggles** (I03). Turns on "morning digest", never receives one. Churns by day 3 without feedback.
- **Add holding #6 on free** (I02). No paywall, no resistance, no Pro offer. User with 30 holdings is consuming Pro-tier compute for free.
- **Tap "Why this grade?"** (I26). Exits to Safari. Mobile user loses context, doesn't return.
- **Tap any legal link** (I35). Same exit pattern.
- **Quiet market day on a position** (partial — recent fixes). User sees empty news and doesn't know if the system failed or the market is quiet.
- **Cold start / pipeline failure** (I20, I21). Generic error; no retry affordance, no ETA, no "last good" fallback copy.
- **Marketing site visit** (I09, I10). Prospect looks for pricing, social proof, App Store link. Finds "1 investor on waitlist". Closes tab.

---

## Trust Killers

Direct signals that make the product feel unreliable.

1. **No social proof anywhere.** 1-investor counter, no testimonials, no public methodology authorship, no "as covered in", no screenshots that demonstrate insight depth.
2. **Three identities in the stack** (I08). Support email replies referencing "Clavis API", URL scheme `clavis://`, brand "Clavix" — fragments confidence on the first technical interaction.
3. **"Waitlist" language on product site** (I09) for a product that is functionally complete. Says "not ready for me yet" to visitors who could actually convert.
4. **Unenforced limits** (I02). Users sense unserious products when the stated rules don't match observed behavior.
5. **Legal links bouncing out to web** (I35). Feels hobbyist; real fintech products mirror terms inline.
6. **AI-generated content with known failure modes** (I30). Without an eval harness, content quality is load-bearing and unverified — a single bad rationale on a loved ticker permanently damages the account.
7. **`armv7` + `trycloudflare.com` in shipped Info.plist** (I06, I07). Anyone technical who inspects the binary will notice.

---

## Backend / Production Gaps

Concrete, code-backed.

- **Single-worker assumption, in-process scheduler** — `backend/app/main.py:125`. Safe today, silent bug when you scale.
- **Bind-mounted source in compose** (I16) — production should run a built image, not host-mounted code.
- **No Redis / queue** — acceptable for v1, document it; don't discover it during Black-Friday-sized load.
- **`enable_debug_surfaces` body capture** (I19) — prod-safe via startup assertion (`main.py:107-111` ✓), but still leaks in staging.
- **No daily MiniMax spend ceiling** (I12). Only a 1.25s per-request throttle.
- **`POST /holdings` synchronous provider calls** (I14). 10–20s stalls on a cold Finnhub/Polygon.
- **`POST /brokerage/sync` synchronous** (I13). 10–30s request; blocks a worker.
- **No per-user background-task dedupe**. `holdings.py:71-78` fires `refresh_ticker_snapshot` on every create, no in-flight check. A user spam-adding holdings spawns N background snapshots.
- **Schema drift** (I11) — canonical source unclear between `supabase_schema.sql` and live DB; `supabase/migrations/` isn't a durable timeline.
- **Admin hardening** (I18) — password cookie, no lockout, no audit log.
- **No DR runbook** (I17).

---

## Branding Incompletion

Where Clavix still reads as generic.

- **URL scheme, project paths, Swift types** all say `Clavis` (I08). Easy to fix at scheme level, harder at type level.
- **Website copy is generic fintech-lite.** "Know where your portfolio stands before the market tells you" is strong; everything under it reads like a template. Missing: authored methodology, founder voice, risk philosophy, a distinctive visual example of a grade explanation.
- **No native methodology / rationale explainer** (I26) — the thing most differentiating about Clavix is accessed only by exiting the app.
- **No distinctive "Clavix grade" visual identity** on marketing pages — the site has a generic dark dashboard look that could be any portfolio tracker.
- **Tagline varies by surface.** "Portfolio intelligence for self-directed investors" (login) vs. "Know where your portfolio stands..." (site) vs. onboarding copy. Pick one, propagate.
- **Marketing site waitlist counter is a negative trust signal** (I09). Replace with "Early access — limited beta" framing if you don't yet have testimonials.

---

## Fastest Way To Fix The "MVP Feel"

In order of ROI.

**Phase A — Trust & credibility (1–2 days, Claude-executable)**
1. Fix `UIRequiredDeviceCapabilities` = arm64 (I07).
2. Remove `trycloudflare.com` ATS exception (I06).
3. Add `PrivacyInfo.xcprivacy` (I05) — research SDKs once, generate.
4. Enforce free-tier cap in `POST /holdings` (I02).
5. Add daily MiniMax cost ceiling + log per-request cost (I12, I28).
6. Add dual URL scheme `clavix://` (I08, keep `clavis://` for SnapTrade).
7. Distinct empty/status states in digest response (I20) + nicer iOS errors (I21).
8. Pass: in-app legal + methodology as sheets (I26, I35).

**Phase B — Ship-the-already-built (external-dependent)**
9. Deploy APNs `.p8` to VPS; flip the existing code live (I03).
10. Provision SnapTrade prod env vars (I04); add `/brokerage/health` for graceful onboarding skip.
11. Fix Supabase schema drift (I11); commit canonical migration chain.

**Phase C — Unlock revenue (3–5 days, external-gated)**
12. Apple Developer account → App Store Connect → StoreKit 2 subscription product.
13. Implement `/subscription/receipt`, wire `subscription_tier` cascade through tier-gated endpoints.
14. Paywall on 6th holding.

**Phase D — Marketing credibility**
15. Ship a real pricing page on `getclavix.com` (I10).
16. Replace "1 investor" counter with private/early-access framing (I09) until real users exist.
17. Add App Store + TestFlight badges when those exist.
18. Publish 2 methodology long-reads with your name on them.

**Phase E — Content quality moat**
19. Build golden-set eval harness for LLM rationale (I30).
20. Add digest phrasing variance + post-gen similarity check (I31).

Do Phase A + Phase B and the product stops feeling like an MVP. Phases C–E are how it stops looking like one.

---

## What I Could Not Verify

- **Visual parity** of recently-landed fixes (synthetic previous score removed, grade bands reconciled, dashboard empty state) — these require device/simulator QA, not static analysis. The claim is in `project_state.md recent_completions`; the UI behavior needs a button-by-button QA pass before launch.
- **Current Supabase prod schema** vs. `supabase_schema.sql` — no live DB access in this audit. The drift is acknowledged in `project_state.md` and treated as fact.
- **Real SnapTrade OAuth flow** — can only be validated against a live sandbox + real brokerage.
- **APNs delivery** — requires the undeployed key.
- **RLS policy exhaustiveness** on shared tables (`ticker_universe`, `ticker_risk_snapshots`, etc.) — not re-enumerated this pass; prior audit flagged this and recent completions note a RLS audit was done; re-verify with a direct anon-JWT query before launch.
- **Website conversion analytics** — no GA/Plausible config visible in `clavix-dashboard/`; can't say what traffic does.

---

## Bottom Line

The code is further along than the product feels. The pipeline is real, the UI is opinionated, the compliance scaffolding is mostly in place, the rate limits and cooldowns landed. What's still missing is the stuff that converts *engineering* into *product*: a working payment loop, the pushed-down-already-built blockers (APNs, SnapTrade prod env, migration hygiene), a non-waitlist marketing page, privacy manifest, and a content-quality moat. Phase A + B above is ~1 week of work and moves Clavix from "working prototype we're nervous to show family" to "I'd let a stranger download this". Phase C–E is what makes it a business.
