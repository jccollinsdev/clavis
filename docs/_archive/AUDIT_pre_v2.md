# Clavix — Product, Design, UX, Architecture Audit

**Date:** April 22, 2026  
**Scope:** Complete codebase inspection (iOS, backend, DB, infra, docs) — execution-ready findings  
**Note:** This is a critical pre-launch audit. All findings are based on actual code inspection, not opinions.

---

## 1. Product understanding

**What Clavix is.** An iOS-first portfolio risk intelligence app for self-directed investors. Core promise: a 30-second morning read that answers three questions — *how risky is my portfolio, what changed overnight, what do I look at first.* Output is a letter grade (A–F) per position and portfolio with short natural-language explanations sourced from a multi-stage news/event pipeline.

**What it is not.** Not a trading app. Not advice. The app repeatedly enforces this in copy (onboarding risk ack, settings disclaimer, methodology screen). No buy/sell/hold language.

**Who it is for.** Retail investors who already self-direct, already read headlines, and want structured risk context they don't have time to synthesize themselves. The onboarding requires 18+ and a DOB. It assumes portfolio fluency (archetype picker, sector exposure, "needs review" framing).

**How it makes money.** Free (capped at 5 holdings) vs Pro (unlimited + brokerage sync + depth + advanced alerts). **Pricing is currently unresolved — see §3 gap #2.**

**How it's built (verified).** 
- **iOS:** SwiftUI, iOS 17+, MVVM, single `APIService` singleton, Supabase auth client for JWT. Backend URL and Supabase anon key injected via `Secrets.xcconfig` → Info.plist.
- **Backend:** FastAPI. JWT middleware validates via Supabase `auth.get_user` on every non-public request (fail-closed). 17-stage analysis pipeline. MiniMax for LLM. Finnhub + Polygon + Google News RSS + GNews + newspaper4k for data.
- **DB:** Supabase Postgres, RLS on every user table. Shared ticker intelligence cache (`ticker_universe`, `ticker_risk_snapshots`, `ticker_news_cache`) is populated server-side with service role.
- **Infra:** Single Docker service behind Cloudflare Tunnel on a DigitalOcean VPS (`clavis.andoverdigital.com`). UptimeRobot on `/health`. Sentry scaffolded. APScheduler runs digest/cleanup jobs in-process.
- **Brokerage:** SnapTrade (read-only OAuth via web portal, `clavis://snaptrade/callback` deep link).
- **Push:** APNs wired in code, keys not deployed.
- **Payments:** None. No Stripe, no StoreKit, no RevenueCat.

---

## 2. App inventory

### iOS screens (actually present in code)

| Area | Screens | Files |
|---|---|---|
| Gate | `ContentView` (auth + onboarding router), `LoadingView` | `ios/Clavis/App/ContentView.swift`, `ios/Clavis/App/ClavisApp.swift` |
| Auth | `LoginView` (sign in + sign up toggle) | `ios/Clavis/Views/Auth/LoginView.swift` |
| Onboarding | 5 steps: welcome+name, DOB, risk ack, preferences, brokerage | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift` |
| Main shell | `MainTabView` — 5 tabs: Home / Holdings / Digest / Alerts / Settings | `ios/Clavis/App/MainTabView.swift` |
| Dashboard | Hero gauge, stat strip, what-changed, digest teaser, needs-attention | `ios/Clavis/Views/Dashboard/DashboardView.swift` |
| Holdings | List + search, watchlist, "needs review", add-position sheet, progress view | `ios/Clavis/Views/Holdings/HoldingsListView.swift` |
| Ticker detail | Hero + score + sparkline + metrics + rationale + events + news + alerts | `ios/Clavis/Views/Tickers/TickerDetailView.swift` |
| Digest | Hero, macro, sector, position impacts, what matters, watchlist, watch-for, full narrative | `ios/Clavis/Views/Digest/DigestView.swift` |
| Alerts | Top header, severity summary grid, filter chips, timeline | `ios/Clavis/Views/Alerts/AlertsView.swift` |
| Settings | Digest, brokerage, alerts, notifications, account, about, disclaimer, sign out | `ios/Clavis/Views/Settings/SettingsView.swift` |
| Secondary | Score explanation, Methodology, News feed + article detail, Position detail | `ios/Clavis/Views/Settings/SettingsView.swift:604`, `ios/Clavis/Views/News/*` |

### Backend routers (mounted in `backend/app/main.py:285`)

`/holdings`, `/digest`, `/dashboard`, `/positions`, `/trigger-analysis`, `/analysis-runs`, `/alerts`, `/news`, `/preferences`, `/tickers`, `/watchlists`, `/brokerage`, `/prices`, `/account`, `/scheduler`, `/admin`, plus `/test-push` + `/debug` when `enable_debug_surfaces=True`.

### DB tables (from `supabase_schema.sql`)

User-scoped: `user_preferences`, `positions`, `analysis_runs`, `risk_scores`, `news_items`, `digests`, `alerts`, `prices`, `position_analyses`, `event_analyses`, `scheduler_jobs`. Shared: `ticker_universe`, `ticker_risk_snapshots`, `ticker_news_cache`, `ticker_refresh_jobs`, `watchlists`, `watchlist_items`, `analysis_cache`.

### External services

Supabase (auth + DB), MiniMax (LLM), Finnhub (prices + news), Polygon (prices), Google News RSS + GNews + r.jina.ai (news), SnapTrade (brokerage), APNs (push, unconfigured), Sentry (optional), UptimeRobot (health), Cloudflare Tunnel (ingress).

---

## 3. Executive summary — top 10 gaps

Ranked by launch risk, not effort.

1. **Three different product names shipping simultaneously.** iOS wordmark says **Clavix**, every Swift type / dir is **Clavis**, and the FastAPI app title in `backend/app/main.py:106` literally says **"Clavynx API"**. The domain is `clavis.andoverdigital.com`. This will burn you on App Review, brand trust, and support tickets.

2. **Pricing is documented three ways, and payments aren't implemented at all.** `docs/PRODUCT/pricing.md` says **$20/mo**, `BUILD_PLAN` says **$12/mo or $99/yr**, the v1 roadmap says **$25/mo**. No Stripe, no StoreKit, no RevenueCat, no entitlement checks outside one gated refresh button in `TickerDetailView`. You cannot ship Pro. You cannot ship the 5-holding free cap either — it isn't enforced anywhere.

3. **Grade bands disagree with themselves.** Methodology docs and backend `digest.py:30-41` use A=80+, B=65+, C=50+, D=35+, F<35. The in-app Score Explanation screen `SettingsView.swift:619-623` tells users A=75–100, B=55–74, C=35–54, D=15–34, F=0–14. Users see numbers that don't match their grades.

4. **The app fabricates data and shows it as real.** `TickerDetailView` synthesizes a "was [previousScore]" delta as `displayScore - 8` when no real prior snapshot exists. `DashboardView` renders grade `"C"` as a hardcoded default when the portfolio grade is actually `N/A`. This is a direct trust and compliance problem for an "informational only" product.

5. **Account deletion and data export do not exist in-app.** Only a link to `getclavix.com/privacy` in `SettingsView.swift:302`. App Store §5.1.1(v) requires in-app account deletion. No `/account/delete` or `/account/export` visible in the router set. This is a hard App Review rejection.

6. **SnapTrade is wired but VPS is not provisioned** and the whole brokerage flow is at the center of Pro. `backend/.env.example:21` and `config.py:27-29` read `SNAPTRADE_CLIENT_ID` + `SNAPTRADE_CONSUMER_KEY`; production `.env` on VPS is missing them per `project_state.md`. Users will hit "configure brokerage" errors from `brokerage.py` in onboarding step 5.

7. **APNs is scaffolded but not deployed.** `config.py:22-25` expects `apns.p8` at `/app/apns.p8`; `docker-compose.yml:10` mounts the dir read-only; lifespan logs `startup_apns_incomplete` as a WARNING and keeps running. Notifications silently no-op. All the digest/alert preferences toggles are meaningless until this lands.

8. **No rate limiting or cost control on expensive endpoints.** `GET /digest?force_refresh=true` in `digest.py:144-292` runs macro + sector + portfolio compilation synchronously and calls MiniMax on every hit. `POST /trigger-analysis` has no guard. A user (or bug loop) can run your AI bill up in an hour. No auth middleware throttling, no per-user cooldown visible.

9. **Onboarding asks permission for notifications via a toggle but never actually requests the iOS permission.** `OnboardingContainerView.swift:316-386` flips `morningDigestEnabled`, `alertsGradeChangesEnabled`, etc., but the iOS permission prompt (`UNUserNotificationCenter.requestAuthorization`) is never shown during onboarding. After the 7 "Apple Dev" items land, users will toggle things on and get nothing.

10. **News cleanup cron isn't actually running.** `supabase_schema.sql:202-205` ships the function `delete_old_news_items()` but the `cron.schedule` line is commented out. `news_items` grows unbounded. For a user who runs the pipeline daily this adds thousands of rows/month and degrades `ticker` / `published_at` queries.

---

## 4. Detailed gap sheet

Severity: **P0** = launch blocker, **P1** = credibility/compliance, **P2** = polish, **P3** = cleanup.

| ID | Area | Sev | Issue | Evidence | Why it matters | Recommended fix | Files / systems | Claude fixable now? |
|---|---|---|---|---|---|---|---|---|
| G01 | Branding | P0 | Three active product names: "Clavix" (wordmark), "Clavis" (code), "Clavynx" (API title) | `backend/app/main.py:106`, `ios/Clavis/App/ClavisApp.swift`, `ios/Clavis/Views/Auth/LoginView.swift:23` | App Review, support, trust, SEO | Decide: brand=Clavix, legal entity=Clavis, internal module names stay Clavis. Rename API title to "Clavix API". Add a naming README row. | `backend/app/main.py`, marketing copy | Yes — API title + doc rows |
| G02 | Monetization | P0 | No payment implementation; price undecided | `ios/Clavis/Views/Settings/SettingsView.swift:68-76` only labels a tier; no StoreKit/Stripe code; pricing.md vs BUILD_PLAN vs v1 roadmap disagree | You cannot earn revenue or enforce the 5-holding cap | Lock price in one doc. Implement StoreKit 2 subscription (App Store requires for digital). Wire `subscription_tier` to free/pro/admin. Enforce holdings cap in `POST /holdings`. | New: iOS StoreKit, `backend/app/routes/subscription.py`, `backend/app/routes/holdings.py:45` | Partial — can scaffold backend + cap, cannot sign App Store paid agreements |
| G03 | Trust | P0 | Grade bands in UI disagree with backend | `ios/Clavis/Views/Settings/SettingsView.swift:619-623` vs `backend/app/routes/digest.py:31-40` vs `docs/PRODUCT/methodology.md` | Users will see "85 → grade B" and lose faith | Pick one band set (recommend backend's 80/65/50/35). Update ScoreExplanationView + methodology.md in lockstep. | `ios/Clavis/Views/Settings/SettingsView.swift:619`, `docs/PRODUCT/methodology.md` | Yes |
| G04 | Trust | P0 | Synthetic "was X" previous score | `ios/Clavis/Views/Tickers/TickerDetailView.swift` `estimatedPreviousScore` returns `displayScore - 8`; `previousScore(for:)` maps A=83, B=65, C=45, D=25, F=8 | "Informational only" claim is broken if you fabricate history | Return `nil` when prior snapshot missing. Hide the delta pill. Only show delta when `risk_scores` has ≥2 rows for the position. | `ios/Clavis/Views/Tickers/TickerDetailView.swift` | Yes |
| G05 | Trust | P0 | Dashboard shows grade "C" when portfolio grade is N/A | `ios/Clavis/Views/Dashboard/DashboardView.swift` `grade: "C"` fallback; `backend/app/routes/digest.py:26-29` returns `(50.0, "C")` for empty positions | Same fabrication problem | Show an "—" state with "Add a position to see your grade" CTA. Backend returns `null` grade when zero positions. | `ios/Clavis/Views/Dashboard/DashboardView.swift`, `backend/app/routes/digest.py:26` | Yes |
| G06 | Compliance | P0 | No in-app account deletion or data export | Only `SettingsLinkRow("Data & privacy")` pointing to a web page; no `/account/delete` or `/account/export` router exists in `backend/app/main.py:285-305` | App Store §5.1.1(v) rejection | Add Settings → Delete Account flow (confirmation + re-auth). Backend `DELETE /account` cascades from `auth.users` down. Add `GET /account/export` returning JSON. | iOS Settings, `backend/app/routes/account.py` | Yes |
| G07 | Brokerage | P0 | SnapTrade env vars missing in prod | `backend/app/config.py:27-29` defaults to empty string; project_state blockers list "SnapTrade VPS env vars" | Onboarding step 5 will error out for every user | Provision `SNAPTRADE_CLIENT_ID` / `_CONSUMER_KEY` on VPS. Add a startup warning in lifespan like APNs has. Onboarding should detect "not configured" and skip gracefully instead of erroring. | VPS `.env`, `backend/app/main.py:91-100`, `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:388` | Partial — code + onboarding yes, VPS provisioning no |
| G08 | Push | P0 | APNs key not deployed; notifications silently noop | `backend/app/config.py:22-25`, `backend/app/main.py:92-100` logs warning but starts server | All alert/digest toggles are theater until fixed | Deploy `apns.p8` to VPS, set `APNS_KEY_ID` + `APNS_TEAM_ID`. Once deployed, have onboarding trigger iOS permission prompt on preferences step. | VPS `/app/apns/apns.p8`, `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:316` | Partial — iOS prompt yes, Apple key no |
| G09 | Cost/Abuse | P0 | Expensive endpoints have no rate limit or per-user cooldown | `backend/app/routes/digest.py:144` `force_refresh` runs macro+sector+compile synchronously; `/trigger-analysis` unbounded | One user or a retry loop can multiply MiniMax cost arbitrarily | Add per-user cooldown (e.g., 1 force_refresh per hour, 3 trigger-analysis per day). Move `force_refresh` logic to background task. Store cooldown in `user_preferences.last_manual_refresh_at`. | `backend/app/routes/digest.py`, `backend/app/routes/trigger.py`, `supabase_schema.sql` | Yes |
| G10 | Onboarding | P0 | iOS notification permission never actually requested | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:316-386` only toggles state | Toggles are lies; user expects alerts, nothing fires | Add a `UNUserNotificationCenter.current().requestAuthorization` step after preferences, tied to "morning digest" or "major events" being on. Register APNs token only after grant. | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift`, `ios/Clavis/App/ClavisApp.swift` | Yes |
| G11 | DB hygiene | P1 | News cleanup cron commented out | `supabase_schema.sql:202-205` | `news_items` grows forever, degrades queries | Enable `pg_cron` on Supabase and run the commented `SELECT cron.schedule(...)`. Or move cleanup into APScheduler. | Supabase, `backend/app/pipeline/scheduler.py` | Yes — schedule job in APScheduler |
| G12 | Security | P1 | `users_own_prices` RLS policy is `USING (true)` FOR ALL | `supabase_schema.sql:189` | Any authenticated user can INSERT/UPDATE/DELETE into `prices`. Price data is public, but writes shouldn't be | Split into `FOR SELECT USING (true)`, writes restricted to `service_role`. Same pattern for `ticker_universe`, `ticker_news_cache`, `ticker_risk_snapshots` which appear to have RLS enabled but no explicit USING policy shown. | `supabase_schema.sql:177` | Yes |
| G13 | Security | P1 | `enable_debug_surfaces=True` logs full request bodies | `backend/app/main.py:185-224` captures body incl. JSON, headers | If ever flipped on in prod it leaks PII + auth payloads | Strip request bodies by default. Redact known fields. Hard-refuse the flag when `sentry_environment == "production"`. | `backend/app/main.py:185`, `backend/app/config.py:17` | Yes |
| G14 | Login UX | P1 | No forgot password, no SSO, no Terms/Privacy link, no trust signals | `ios/Clavis/Views/Auth/LoginView.swift` | Standard password recovery + legal links are table-stakes | Add "Forgot password" that calls Supabase `resetPasswordForEmail`. Add Terms + Privacy footnote links. Optional: "Sign in with Apple" (required by Apple if you add other SSO). | `ios/Clavis/Views/Auth/LoginView.swift` | Yes |
| G15 | Onboarding UX | P2 | DOB entered as free-form "DD / MM / YYYY" text with digit pad | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:154-233` | Slow, error-prone, locale-confusing (DD/MM vs MM/DD) | Use `DatePicker(displayedComponents: .date)` with a max date = today − 18y. | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:154` | Yes |
| G16 | Onboarding UX | P2 | Add-Position has no live search dropdown | `ios/Clavis/Views/Holdings/HoldingsListView.swift` AddPositionSheet is manual entry only; search is elsewhere | Friction during first-run for manual users | Merge the existing `/tickers/search` debounce into AddPositionSheet with ticker chip selection. | `ios/Clavis/Views/Holdings/HoldingsListView.swift` | Yes |
| G17 | Copy | P1 | Methodology screen says "five dimensions" but methodology.md + backend use four | `ios/Clavis/Views/Settings/SettingsView.swift:680` says "five dimensions" `docs/PRODUCT/methodology.md` says four (news_sentiment, macro_exposure, position_sizing, volatility_trend); schema has 5th `thesis_integrity` but it isn't exposed in the digest grade path | Contradicts product docs | Pick 4 (current active) and align both. Or ship `thesis_integrity` and document it. | `ios/Clavis/Views/Settings/SettingsView.swift:680`, `docs/PRODUCT/methodology.md` | Yes |
| G18 | Copy | P2 | "MiroFish" still referenced in pricing.md after removal | `docs/PRODUCT/pricing.md:60` lists "MiroFish deep analysis" as Pro feature | Stale claim, contradicts `9003c60` commit | Delete the row or replace with "In-depth event analysis on major catalysts". | `docs/PRODUCT/pricing.md` | Yes |
| G19 | Dead code | P3 | Many deprecated view structs still compile | `ios/Clavis/Views/Dashboard/DashboardView.swift`: DashboardMastheadCard, DashboardHeroCard, DashboardSnapshotCard, DashboardPlaybookCard, SinceLastReviewCard; AlertsHeroCard, AlertsSeveritySummaryCard, legacy AlertCard; ClavisDesignSystem capsule/ring deprecated components | Build bloat, confusion | Delete unreferenced structs. Build will flag any residual use. | iOS `ios/Clavis/Views/*` | Yes |
| G20 | Dead code | P3 | `mirofish_used_this_cycle` still returned by API and decoded by iOS | `backend/app/routes/positions.py:181`, `ios/Clavis/Services/APIService.swift:569` | Dead field, dead keys, stale risk_scores column | Remove field from response, remove iOS CodingKey, drop `mirofish_used` column in a migration. | `backend/app/routes/positions.py`, `ios/Clavis/Services/APIService.swift:569`, `supabase_schema.sql:66` | Yes |
| G21 | Settings | P2 | No multi-currency, no cost-basis precision beyond single purchase_price | `supabase_schema.sql:25` has only `shares` + `purchase_price` | Misleading for users with partial fills or multi-lot positions | Acknowledge scope in copy ("single cost basis only"), defer multi-lot to v2. Short-term: rename `purchase_price` label to "Average cost". | `ios/Clavis/Views/Holdings/HoldingsListView.swift` AddPositionSheet copy | Yes |
| G22 | Digest | P2 | `GET /digest?force_refresh=true` runs sync in request handler | `backend/app/routes/digest.py:157-292` | Blocks a web worker for 30–75s, contends with other users | Convert to background job: return 202 + poll via `analysis_runs`. Already have the infra (`analysis_runs_router`). | `backend/app/routes/digest.py` | Yes |
| G23 | Observability | P2 | `startup_apns_incomplete` logged as WARNING but server starts | `backend/app/main.py:96-100` | Silent prod drift | Make APNs status visible in `/health` JSON: `{"status":"ok","apns":"configured","snaptrade":"configured"}`. | `backend/app/main.py:280` | Yes |
| G24 | Observability | P2 | No structured log of MiniMax cost per request | searched: no cost/token fields in `backend/app/services/minimax.py` log_event | Can't forecast burn, can't detect runaway | Log tokens in / tokens out / $ estimate per call; aggregate daily to admin surface. | `backend/app/services/minimax.py` | Yes |
| G25 | Empty states | P2 | Several core surfaces show the same "No digest yet" message regardless of cause | `backend/app/routes/digest.py:147-154` returns same shape for "no positions" and "no digest generated" | User can't tell if they need to add a holding or wait | Return distinct states: `no_positions`, `awaiting_first_run`, `generating`, `failed`. iOS switches on `status`. | `backend/app/routes/digest.py`, `ios/Clavis/Views/Digest/DigestView.swift` | Yes |
| G26 | Error handling | P2 | Generic "Server error: 500" on iOS | `ios/Clavis/Services/APIService.swift:114` | User has no recovery path | Decode FastAPI `detail` field and show it. Distinguish cold-start/timeouts with friendlier copy. | `ios/Clavis/Services/APIService.swift:100` | Yes |
| G27 | Auth | P2 | Backend re-validates every JWT against Supabase auth API (network call per request) | `backend/app/main.py:147` `get_user(token)` | Adds 50–300ms per request, burns Supabase quota | Verify JWT signature locally with `SUPABASE_JWT_SECRET` (already in config) and only hit `auth.get_user` on signature failure or once per session. | `backend/app/main.py:147` | Yes |
| G28 | Auth/UX | P3 | Old `clavis://` deep link scheme while brand is Clavix | `ios/Clavis/App/ClavisApp.swift`, `backend/app/config.py:29` | Harmless but yet another brand split | Keep for v1 (SnapTrade is already configured with it), plan rename in v2 with dual-scheme support. | `ios/Clavis/Resources/Info.plist`, `backend/app/config.py:29` | Defer |

---

## 5. Launch readiness gaps

What must be resolved before you can submit to App Review.

| # | Item | Status | Blocker type |
|---|---|---|---|
| L1 | Apple Developer Program enrolled, bundle id `com.clavisdev.portfolioassistant` provisioned | Not done | Apple, cannot fix |
| L2 | APNs `.p8` key generated, uploaded to VPS | Not done | Apple, cannot fix |
| L3 | StoreKit 2 IAP products configured in App Store Connect | Not done | Apple + code |
| L4 | In-app account deletion & export | Not done | Code (**G06**) |
| L5 | Privacy manifest (PrivacyInfo.xcprivacy) for iOS 17+ | Not verified — no `PrivacyInfo.xcprivacy` seen in `ios/Clavis/Resources/` | Code |
| L6 | App Tracking Transparency check (we don't track, but must declare) | Not verified | Code |
| L7 | Support URL, marketing URL, privacy URL, ToS URL live | Privacy/ToS/Refund on `getclavix.com` per `ios/Clavis/Views/Settings/SettingsView.swift:508` — **verify these pages actually exist** | Infra |
| L8 | `Clavix` vs `Clavis` reconciled in App Store listing, Info.plist `CFBundleDisplayName`, and API title | Not done | **G01** |
| L9 | SnapTrade production credentials on VPS | Not done | **G07** |
| L10 | Grade-band copy reconciled across app + methodology + docs | Not done | **G03** |
| L11 | Synthetic previous-score removed | Not done | **G04** |
| L12 | Rate limits on `/trigger-analysis` and `/digest?force_refresh` | Not done | **G09** |
| L13 | Pricing locked across docs; Pro entitlement enforced; free-tier 5-holding cap enforced | Not done | **G02** |
| L14 | `/account/delete` + `/account/export` endpoints + Settings flows | Not done | **G06** |
| L15 | Notification permission actually requested during onboarding | Not done | **G10** |
| L16 | Supabase `pg_cron` enabled and `delete_old_news_items` scheduled | Not done | **G11** |
| L17 | `PrivacyInfo.xcprivacy` + NSUserTrackingUsage (if any) keys | Not verified | Code |
| L18 | App icon variants @1x/@2x/@3x + 1024 marketing, with "Clavix" wordmark consistency | Not verified — `AppLogo` referenced at `ios/Clavis/Views/Auth/LoginView.swift:17` | Asset |
| L19 | TestFlight build + at least 2 external testers | Apple, cannot fix |
| L20 | Incident response runbook (VPS down, SnapTrade expired token, APNs key rotated) | Not verified in `docs/GUIDES/` | Docs |

**Flagged as Apple-blocked (outside my scope per the brief):** L1, L2, L3, L19.

---

## 6. Branding gaps

| ID | Issue | Evidence | Fix |
|---|---|---|---|
| B1 | Three brand names live at once | "Clavix" wordmark (`ios/Clavis/Views/Auth/LoginView.swift:23`); "Clavis" dirs, types, domain, deep link; "Clavynx API" FastAPI title `backend/app/main.py:106` | Commit: brand = **Clavix**. Keep Swift types as `Clavis*` internally (avoid refactor risk) but: change API title to "Clavix API", set `CFBundleDisplayName=Clavix`, write a one-line README at repo root explaining the name split |
| B2 | Wordmark uses `brandCream` cream on dark; AppLogo is referenced but asset integrity unverified | `ios/Clavis/Views/Auth/LoginView.swift:17`, `ios/Clavis/App/ClavisDesignSystem.swift` `ClavixWordmarkHeader` | Audit `Assets.xcassets`: confirm AppLogo @1x/@2x/@3x, confirm dark-mode variant exists |
| B3 | "Portfolio risk, measured." (onboarding) vs "Portfolio intelligence for self-directed investors" (login) vs roadmap positioning | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:119`, `ios/Clavis/Views/Auth/LoginView.swift:28` | Pick one tagline. Onboarding's is stronger. Propagate to login, marketing site, App Store subtitle (max 30 chars): "Portfolio risk, measured." |
| B4 | Deprecated capsule/ring components + `slate900`-`slate100`, `semanticRed`, `decisionReduce` aliases in design system | `ios/Clavis/App/ClavisDesignSystem.swift` | Delete the alias layer before v1 lock. It's adding maintenance tax without value |
| B5 | Grade color treatment is consistent (`.riskA`-`.riskF`) but the meaning shifts because bands conflict | See G03 | Fix G03 first; visual system is fine |
| B6 | "Informational only" disclaimer text varies by surface | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:258` vs `ios/Clavis/Views/Settings/SettingsView.swift:576` vs `ios/Clavis/Views/Settings/SettingsView.swift:684` — different sentences each place | Centralize as `ClavisStrings.informationalDisclosure` and reference |
| B7 | Inter + JetBrains Mono families loaded; verify licensing in shipped bundle | `ios/Clavis/App/ClavisDesignSystem.swift` | Confirm SIL OFL in `docs/legal` and bundled with Info.plist font declarations |
| B8 | Welcome screen shows "C" monogram inside a rounded box — visual conflict with the letter-grade C which appears in the app as the neutral grade | `ios/Clavis/Views/Onboarding/OnboardingContainerView.swift:113` | Use the X monogram or full wordmark — "C" signals "grade C" inside this product |

---

## 7. Backend / DB / VPS gaps

**API layer**
- `backend/app/main.py:147` calls `supabase.auth.get_user(token)` on **every authenticated request**. That's a network hop per request. Switch to local JWT signature verification with `SUPABASE_JWT_SECRET` (already loaded in `backend/app/config.py:8`); fall back to `get_user` only on failure. Saves 50–300ms per call and a lot of Supabase quota.
- `enable_public_docs` and `enable_debug_surfaces` are separate booleans with no safety coupling — both default to `False` but there's nothing stopping a prod deploy from having `enable_debug_surfaces=True` with `sentry_environment=production`. Add a startup assertion that refuses to start in that combination. `backend/app/main.py:87`, `backend/app/config.py:16-17`.
- Debug middleware (`backend/app/main.py:185`) reads and stores full request bodies including POST payloads. Redact Authorization/Cookie (it does) but it does **not** redact password fields or PII. Minor now; major if the flag flips in prod.
- `/health` returns only `{"status":"ok"}`. Add `apns`, `snaptrade`, `minimax`, `supabase` reachability. `backend/app/main.py:280`.
- No rate limit middleware. At minimum add `slowapi` on `/trigger-analysis`, `/digest?force_refresh=true`, `/brokerage/sync`, `/tickers/{ticker}/refresh`.
- Admin surface (`/admin`) is cookie-auth with a single password. Adequate for one-user admin, but add (a) IP allowlist, (b) failed-attempt lockout, (c) audit log.

**Routes — specific issues**
- `backend/app/routes/positions.py:181` still returns `"mirofish_used_this_cycle": False` — dead field.
- `backend/app/routes/positions.py:84-90` fires a background price refresh when `current_price is None`, but there's no circuit breaker if Polygon is down. You'll spawn a background task per request forever.
- `backend/app/routes/digest.py` does synchronous MiniMax calls for macro + sector + portfolio compile when `force_refresh=true`. Per G09 / G22.
- `backend/app/routes/holdings.py:54` validates the ticker via `ensure_ticker_in_universe` which may call out to Finnhub/Polygon. No timeout on the create path; if both providers stall the user's "Add position" button hangs 12s + 12s before failing.
- `backend/app/routes/brokerage.py:58` runs `sync_brokerage_holdings` synchronously in the request. SnapTrade can take 10–30s; move to background with polling. This is especially rough for onboarding step 5.
- **Free-tier cap not enforced.** `backend/app/routes/holdings.py:45` does not check `subscription_tier` + count. Add: `if tier=='free' and count>=5: 402 Payment Required`.
- **Account deletion endpoint missing.** `/account` router is mounted but no `DELETE` visible in overview; verify. If absent, add.

**Scheduler**
- APScheduler runs in-process (`backend/app/main.py:101` `start_scheduler()`). If you ever run multiple Uvicorn workers the scheduler will fire N times. Lock down to `--workers 1` or switch to Postgres-backed scheduler with leader election.

**DB / Supabase**
- `supabase_schema.sql:189` `users_own_prices FOR ALL USING (true)` — allows writes by any auth'd user. Split to `FOR SELECT USING (true)`, deny writes except service role. **P1.**
- Shared tables `ticker_universe`, `ticker_risk_snapshots`, `ticker_news_cache`, `ticker_refresh_jobs`, `watchlists`, `watchlist_items`, `analysis_cache` have RLS enabled but the shown schema has no `CREATE POLICY` for most of them (only `service_role_analysis_cache`). With RLS on and no policy, `anon`/`authenticated` reads return zero rows. Your backend uses service role so it works — but confirm by running a direct client-side query from an anon JWT; if you ever move any call off the backend it'll silently fail.
- `delete_old_news_items()` exists but the cron schedule is commented. **G11.** Easier fix: schedule in APScheduler alongside the digest job.
- No index on `alerts(user_id, created_at DESC)` composite; queries sort+filter on both. Current separate indexes work but composite helps list pagination.
- `positions` lacks `cost_basis_method`, `currency`, or `tax_lot` fields. For v1 that's fine; surface as a known limitation in copy.
- `risk_scores` table still carries the `mirofish_used` column — migration needed to drop.

**Infra / VPS**
- `docker-compose.yml` runs a single backend container, code-mounted as a read-write volume from host (`./backend/app:/app/app`). **In production you should not bind-mount source**; the CI deploy flow should rebuild the image or pull a tagged image, not rsync source.
- Cloudflare Tunnel is fine but not declared in docker-compose — runs outside, undocumented in this file. Document the tunnel config in `docs/GUIDES/digitalocean-vps-setup.md`.
- No `nginx`/Caddy reverse proxy in compose; relying on Cloudflare TLS termination and direct `:8000`. Add an internal reverse proxy or lock down the port with UFW so only Cloudflare tunnel can reach it.
- No log rotation configured; `docker logs` grows unbounded by default. Set `logging.driver: json-file` with `max-size: 10m`, `max-file: 5`.
- Environment files committed? `backend/.env` shows up in `git status` as modified — verify `.env` is in `.gitignore`. `backend/.env` should **never** be tracked.
- No Redis in compose — APScheduler in-memory means a restart loses next-run scheduling until recomputed. Acceptable at your scale; call it out.
- No automated DB backups documented. Supabase handles PITR on paid plans; confirm the tier.

**External integrations**
- MiniMax: no retry/backoff visible in the route handlers; `minimax_min_interval_seconds=1.25` is a global throttle but offers no per-call budget. Add a daily cost ceiling.
- Polygon: no key in `.env.example` default; positions create path relies on it.
- Finnhub: free tier rate-limited; no visible 429 handling.
- Google News RSS + r.jina.ai: brittle upstream, no fallback documented.

---

## 8. Quick wins

Under ~30 min each, high signal.

1. **Rename API title** in `backend/app/main.py:106` from `Clavynx API` → `Clavix API`. (G01)
2. **Delete the `mirofish_used_this_cycle` field** from `backend/app/routes/positions.py:181` and the iOS decode at `ios/Clavis/Services/APIService.swift:569,582`. (G20)
3. **Drop the synthetic previous-score**: return `nil` when no prior snapshot; hide the delta pill. `ios/Clavis/Views/Tickers/TickerDetailView.swift`. (G04)
4. **Fix empty-portfolio grade**: backend returns `null` grade when positions list is empty; iOS renders "—". `backend/app/routes/digest.py:29`, `ios/Clavis/Views/Dashboard/DashboardView.swift`. (G05)
5. **Reconcile grade bands**: update `ios/Clavis/Views/Settings/SettingsView.swift:619-623` to A=80+, B=65+, C=50+, D=35+, F<35, matching backend. (G03)
6. **Delete "MiroFish deep analysis"** row from `docs/PRODUCT/pricing.md:60`. (G18)
7. **Fix "five dimensions" copy** in `ios/Clavis/Views/Settings/SettingsView.swift:680` → "four dimensions". (G17)
8. **Tighten `users_own_prices` RLS** to `FOR SELECT USING (true)` + service-role writes only. (G12)
9. **Schedule news cleanup** in APScheduler (1 line, avoids the pg_cron dependency). (G11)
10. **Add DatePicker to DOB onboarding step** with max date = today-18y. (G15)
11. **Add "Forgot password"** to LoginView (Supabase `resetPasswordForEmail`). (G14)
12. **Add startup assertion** refusing `enable_debug_surfaces=True` when `sentry_environment='production'`. (G13)
13. **Expose APNs/SnapTrade/MiniMax status in `/health`.** (G23)
14. **Add Inter/JetBrains Mono license files** to `docs/legal/` and confirm bundle inclusion. (B7)
15. **Add `logging: { driver: json-file, options: { max-size: 10m, max-file: 5 } }`** to `docker-compose.yml`. (infra)

All 15 are Claude-fixable in this repo with no external dependencies.

---

## 9. What to do next — implementation order

### Phase 0 — credibility bug-fix sprint (1–2 days)

Kill the fabrications, reconcile the brand, ship the low-effort high-trust fixes. Nothing here depends on Apple Dev or payments.

- Quick wins 1–15 above.
- G03 grade bands, G04 synthetic previous score, G05 empty portfolio, G17 dimensions copy, G18 MiroFish copy, G20 dead fields, G19 dead view structs.
- Cleanup pass: delete deprecated view structs + design-system aliases to stop bitrot.

Outcome: app is internally consistent, no fabricated numbers, one brand name everywhere.

### Phase 1 — compliance + cost control (2–3 days)

Make the app App-Review-acceptable and financially safe.

- **G06** in-app account deletion + export (new `/account` routes + Settings flows).
- **G09 / G22** rate-limit + background `/digest?force_refresh` and `/trigger-analysis`.
- **G12** RLS tightening.
- **G13** `enable_debug_surfaces` hardening.
- **G27** local JWT verification (quota + latency win).
- Add `PrivacyInfo.xcprivacy` and verify App Store metadata (L5).
- Free-tier 5-holding cap enforcement in `POST /holdings` (G02, backend half).

Outcome: the app can be submitted pending Apple-side tasks without review blockers, and won't bankrupt you on MiniMax.

### Phase 2 — wire the already-built blockers (1–2 days + Apple-side)

These are ready in code; they need keys/provisioning.

- **G07** Put SnapTrade credentials on VPS. Confirm the portal + callback end-to-end from TestFlight build.
- **G08** Deploy `apns.p8`; set `APNS_KEY_ID` + `APNS_TEAM_ID`. Test via `/test-push`.
- **G10** Trigger iOS notification permission during onboarding preferences step. Register token after grant.
- Harden onboarding step 5 to gracefully skip when SnapTrade isn't configured.

Outcome: notifications, brokerage, and onboarding actually work end-to-end.

### Phase 3 — pricing + StoreKit (3–5 days)

- Lock price in one place (recommend **$20/mo** from `docs/PRODUCT/pricing.md` — already the most thought-through doc with unit economics; $25 is aspirational, $12 was rejected per pricing.md:117).
- Implement StoreKit 2 subscription + restore purchases.
- Backend: `/subscription/receipt` endpoint verifies with Apple and updates `user_preferences.subscription_tier`.
- iOS: gate Pro features (brokerage sync, full rationale, unlimited holdings, advanced alerts) via `subscriptionTier` — pattern already exists at `ios/Clavis/Views/Tickers/TickerDetailView.swift` refresh button.
- Paywall screen on hitting 5-holding cap.
- Sync pricing copy across pricing.md, BUILD_PLAN.md, roadmap docs, marketing site.

Outcome: Pro is sellable and enforceable.

### Phase 4 — polish + launch prep (2–3 days)

- G14 login (forgot password, Apple SSO if desired).
- G15 DOB DatePicker, G16 ticker search inside AddPosition.
- G23 `/health` surface + G24 MiniMax cost logging.
- G25 distinct empty states, G26 friendlier error copy.
- Copy pass: centralize disclaimer strings (B6), one tagline (B3).
- Document incident runbooks (L20): VPS down, SnapTrade token expired, APNs key rotation, Supabase outage.
- Docker compose hardening: no source bind mount in prod, log rotation, reverse proxy or UFW lockdown.

### Phase 5 — App Review submission (Apple-gated)

- TestFlight build with all of the above.
- 2+ external testers through TestFlight.
- Submit.

### Deferred (v1.1+)

- G21 multi-currency / multi-lot cost basis.
- G28 deep link scheme rename `clavis://` → `clavix://` with dual-scheme support.
- Backup + PITR verification.
- Move scheduler out of in-process APScheduler when you add a second worker.
- Institutional / data-partnership tier from `docs/PRODUCT/pricing.md:124`.

---

## Bottom line

The pipeline, DB, and UI are more mature than they look on the surface. What's blocking a real launch is a cluster of credibility bugs (fabricated scores, inconsistent grade bands, three product names), compliance gaps (account deletion, privacy manifest), missing cost guards (no rate limits on MiniMax-hitting endpoints), and unwired-but-ready integrations (APNs, SnapTrade prod, payments). Phase 0 alone will move the app from "looks professional but feels dishonest in spots" to "consistent and trustworthy." Phases 1–3 close the launch checklist everything else depends on.
