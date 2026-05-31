# Clavix V1 Production-Readiness Audit

**Date:** 2026-05-29
**Auditor:** Claude (Opus) — evidence-based, read-only investigation
**App:** Clavix (internal target name "Clavis") — iOS portfolio risk intelligence, manual-entry, informational/non-advisory
**Scope:** Full-stack: iOS app, FastAPI backend, Supabase, VPS/scheduler, website, email, App Store readiness, security
**Method:** Code reads, live HTTP probes, DNS queries, DB completeness audit (from prior recovery), scheduler source trace. Every material claim below is tagged **[CONFIRMED]** (I directly observed the evidence) or **[SUSPECTED]** (inferred, needs one more check).

> Evidence convention: file references use `path:line`. Live probes show the exact command and output. Where a finding rests on the previous session's DB audit, it is cited to `docs/BACKEND_FRESHNESS_AUDIT.md`.

---

## 1. Executive Summary

Clavix is **closer to launchable than it feels**, but it has **one live production defect that makes the whole app feel broken** and a short list of true launch blockers that are mostly *account/legal/StoreKit* paperwork, not engineering.

The single most important finding: **the public API is degraded right now**, not because data is missing, but because an in-process background enrichment loop blocks the web server's event loop. I measured `/health` taking **10.6 seconds** at audit time. This one defect is the root cause of (a) the 5–20s hangs, (b) the "macro/sector/volatility unavailable" UI, and (c) the perceived auth/JWT instability. The data in the database is **complete** (504/504 dimension-complete snapshots per the 2026-05-27 recovery). The app shows "unavailable" because requests *time out*, not because fields are null.

The good news: this defect has a **zero-code mitigation** (an environment flag) and a clean structural fix (move enrichment off the web process). Everything else is the normal pre-launch checklist.

**Bottom line:** With one weekend of focused work — fix the event-loop defect, wire StoreKit, finish the Apple/legal paperwork — Clavix can ship a credible, honest, non-advisory V1 that justifies $20/mo. Do **not** add scope. The product is already over-built for V1; the risk is operational, not featural.

---

## 2. Launch Readiness Score

**Overall: 58 / 100** (weighted; "ready to submit to App Store with paid tier working").

| Domain | Weight | Score | Notes |
|---|---|---|---|
| Core data correctness | 20 | 18/20 | DB is complete & honest; limited-data handling exists. [CONFIRMED] |
| Backend stability/perf | 20 | 6/20 | Event-loop starvation live now. Single biggest gap. [CONFIRMED] |
| iOS app functionality | 15 | 11/15 | Works; depends on backend being responsive. |
| Auth/session | 10 | 8/10 | Robust; perceived instability is backend availability. [CONFIRMED] |
| Monetization (StoreKit) | 10 | 1/10 | StoreKit 2 absent. Cannot charge today. [CONFIRMED prior] |
| App Store/TestFlight readiness | 10 | 4/10 | Blocked on Apple enrollment + paperwork. |
| Website / legal | 5 | 4/5 | Live, honest, non-advisory; source-control drift. [CONFIRMED] |
| Email/deliverability | 5 | 2/5 | DMARC missing; transactional email = Supabase default (risky). [CONFIRMED] |
| Security/RLS | 5 | 3/5 | 3 advisor findings to close. [CONFIRMED prior] |

A score of 58 means: **the engineering is mostly done, but you cannot collect money and the app is currently degraded.** Both are fixable this weekend.

---

## 3. Recommended V1 Scope (Freeze This)

**V1 = "Manual-entry daily portfolio risk briefing, informational only."**

A user manually enters holdings and watchlist tickers. Each day Clavix tells them what changed, what got riskier, why, and shows the evidence (five dimensions + composite grade + methodology drill-down + daily digest).

**IN (already built, keep):**
- Manual ticker entry (holdings + watchlist)
- 5 risk dimensions + equal-weight composite + bond-style grade
- Methodology drill-down (formula, inputs, sources, refresh time)
- Daily digest / morning briefing
- Score history chart
- Free tier (3 holdings / 5 watchlist) + Pro ($20/mo) gating
- Auth (email/password, reset, confirm)

**OUT (cut, do not touch this weekend):** SnapTrade/brokerage sync, trading/execution, buy/sell/hold, advice, price targets/predictions, options/crypto/international, multi-portfolio, social, CSV import (unless already shipped & safe).

**DEFERRED (not cut, but post-Apple-enrollment):** Push notifications (APNs is wired but no-op until the Apple Developer account + APNs key exist).

---

## 4. Cut List (Explicit)

| Feature | Decision | Reason |
|---|---|---|
| SnapTrade / brokerage sync | **CUT** | Regulatory + scope; V1 is manual-entry |
| Buy/sell/hold, advice, price targets | **CUT (hard)** | Non-advisory positioning is the legal moat |
| Options / crypto / international | **CUT** | Not modeled; out of universe |
| Multi-portfolio / social | **CUT** | Scope |
| CSV import | **CUT unless already safe** | Verify it isn't half-wired; if half-wired, hide it |
| Push notifications | **DEFER** | Wired but no-op; needs Apple Dev + APNs key |
| Data verification gate (`is_product_visible`/`data_status`) | **REMOVE or WIRE** | Dead columns; currently misleading. See §13. |

---

## 5. Feature Readiness Matrix

Columns: Area | Required for V1 | Status | Evidence | Blocker | Priority | Exact fix | Owner | Complexity | Deps

| Area | Req V1 | Status | Evidence | Blocker | Pri | Exact fix | Owner | Cx | Deps |
|---|---|---|---|---|---|---|---|---|---|
| Event-loop starvation (enrichment blocks web) | Yes | **BROKEN (live)** | `/health` = 10.6s; `scheduler.py:5429-5430,5470-5478` sync supabase in async job | API hangs/timeouts | **P0** | Set `DISABLE_NEWS_ENRICHMENT=true` + restart NOW; then move enrichment to separate worker/process | Backend | M | VPS access |
| 5 dimensions data completeness | Yes | **DONE** | `BACKEND_FRESHNESS_AUDIT.md`: 504/504 | none | P3 | — | — | — | — |
| "Unavailable" UI | Yes | **ROOT-CAUSED** | Data complete; failure = timeouts | tied to P0 | P0 | Fix P0; verify cards repopulate | Backend | S | P0 |
| StoreKit 2 paywall | Yes | **ABSENT** | No StoreKit code (prior) | Cannot charge | **P0** | Implement StoreKit 2 product + purchase + entitlement gate | iOS | L | App Store Connect product |
| Apple Developer enrollment | Yes | **BLOCKED** | `launch_issues.md` #1 | Cannot submit | **P0** | Enroll (mom's personal acct interim) | Founder | M | — |
| Macro/sector "Today" snapshots narrative | Yes | **PARTIAL** | `price_only`, ~30h stale (prior) | Thin briefing | **P1** | Run daily macro/sector snapshot jobs; verify narrative populates | Backend | S | P0 fixed |
| Legal pages (Privacy/Terms/Refund/Methodology) | Yes | **LIVE** | All 200 + distinct content (§14) | Source not in repo | **P1** | Commit live page sources into `web/` | Founder/Web | S | — |
| Email deliverability (transactional) | Yes | **RISKY** | Supabase default SMTP; no custom; no DMARC | Reset/confirm to spam | **P1** | Configure custom SMTP in Supabase + add DMARC | Founder | M | — |
| Auth/session | Yes | **ROBUST** | `SupabaseAuthService.swift`, `APIService.swift` retry/refresh | none material | P2 | — | — | — | — |
| Push notifications (APNs) | No (defer) | **NO-OP** | `apns.py` present; no key | Deferred | P2 | Add APNs key post-enrollment | Backend | M | Apple Dev |
| RLS: `gnews_wrapper_resolution` | Yes | **RLS OFF** | Supabase advisor ERROR (prior) | Anon-readable | **P1** | Enable RLS + policy | Backend | S | — |
| SECURITY DEFINER RPCs anon-executable (×2) | Yes | **OPEN** | Supabase advisor (prior) | Fake-data injection risk | **P1** | Revoke anon EXECUTE / add auth check | Backend | S | — |
| Leaked-password protection | Yes | **OFF** | Supabase advisor (prior) | Weak-pw signups | **P2** | Toggle on in Supabase Auth | Founder | S | — |
| Holdings price staleness vs detail | Nice | **BUG #32** | `backlog.md` #32 | Inconsistent UX | **P2** | Unify price source | iOS/Backend | S | — |
| Double XLK sector rows | Nice | **BUG #35** | `backlog.md` #35 | Cosmetic data dup | **P3** | Dedup sector rows | Backend | S | — |
| GitHub Actions deploy secret | Nice | **BUG #34** | `backlog.md` #34 (PROD_SSH_KEY unset) | Manual deploy only | **P3** | Set secret or accept manual deploy | Founder | S | — |
| Stale `trycloudflare.com` ATS exception | No | **CRUFT** | `Info.plist:63` | App Store reviewer optics | **P2** | Remove exception domain | iOS | S | — |
| LLM capacity for SP500 backfill | Yes | **RISK** | 4,500 req/5h plan vs backfill volume (§19) | Throttle needed | **P1** | Chunk/throttle backfill | Backend | M | — |

---

## 6. P0 Blockers (Launch-Stopping)

1. **Event-loop starvation / API degradation [CONFIRMED, LIVE].** `/health` = 10.6s now. Root cause: `AsyncIOScheduler` (scheduler.py:31) runs `async def` enrichment jobs (scheduler.py:5453 `_run_bulk_sentiment_enrichment`, 5411 `_run_active_ticker_news_refresh`) that call the **synchronous** Supabase client `.execute()` directly on the event loop (scheduler.py:5429-5430, 5470-5478). Every call blocks all HTTP request handling. Jobs run every 2h/4h **and on startup** (+10min/+5min), registered unconditionally (scheduler.py:5599-5600). This is backlog #33 at production scale.
   - **Immediate mitigation (no code):** `DISABLE_NEWS_ENRICHMENT=true` env var kills both jobs (scheduler.py:5419, 5460) → restart container. *Tradeoff:* news dimension stops refreshing until the real fix.
   - **Real fix:** move enrichment to a separate process/container (or a second uvicorn-less worker), OR wrap every blocking Supabase call in `await asyncio.to_thread(...)`. The separate-process route is cleaner and matches the existing `/etc/cron.d/clavix` `docker exec ... python -m app.jobs.run <job>` pattern.

2. **StoreKit 2 absent [CONFIRMED prior].** No purchase flow → cannot collect the $20/mo. Must implement product config + purchase + entitlement gating before any paid submission.

3. **Apple Developer enrollment not complete [CONFIRMED].** `launch_issues.md` #1. Cannot submit to TestFlight/App Store. Interim path: mom's personal account, branded Clavix.

---

## 7. P1 Blockers (Must Fix Before Public Launch)

1. **Macro/sector "Today" snapshots are `price_only` and ~30h stale [CONFIRMED prior].** Briefing looks thin. Run the daily macro/sector snapshot jobs (scheduler.py:5534/5547, ET 05:00/05:15) and verify narrative populates after P0 is fixed.
2. **Legal page source not version-controlled [CONFIRMED].** Pages are live (§14) but `web/` only has `index.html` + `confirm.html`; live homepage bytes (31,154) ≠ repo (50,623). Production is ahead of repo. Commit the real sources.
3. **Transactional email deliverability [CONFIRMED].** Password reset / signup confirmation are sent by Supabase (`SupabaseAuthService.swift:104,131` redirect to getclavix.com/confirm). Supabase's default SMTP is rate-limited (~a few/hour) and lands in spam. Configure custom SMTP. Also **no DMARC record** (§15).
4. **Security: `gnews_wrapper_resolution` RLS off; two anon-executable SECURITY DEFINER RPCs [CONFIRMED prior].** Close before public exposure.
5. **LLM backfill capacity [SUSPECTED, math in §19].** A full SP500 (504-ticker) backfill can exceed 4,500 req/5h if run unthrottled. Chunk it.

---

## 8. P2 / P3 (Post-Launch / Polish)

- **P2:** Remove stale `trycloudflare.com` ATS exception (`Info.plist:63`); enable leaked-password protection; fix holdings price staleness (#32); APNs key after enrollment.
- **P3:** Dedup double XLK rows (#35); set `PROD_SSH_KEY` GitHub secret (#34); HIMS-style limited-data is already honest — leave it.

---

## 9. The "Unavailable" Mystery — End-to-End Trace (7 Layers)

The user demanded: *do not stop at "field is nil"; find why it's nil and how to fix it.* Result: **the field is not nil. The request times out.**

1. **API source (Finnhub/Polygon/Jina):** Live, not the cause.
2. **Backend job (scheduler):** Dimension data is computed and persisted; `BACKEND_FRESHNESS_AUDIT.md` confirms 504/504 schema-complete.
3. **DB (Supabase):** `news_sentiment_dim`, `macro_exposure_dim`, `sector_exposure`, `volatility`, `financial_health`, `composite_score` all populated for latest rows. **No null gap.** [CONFIRMED prior]
4. **Endpoint (`routes/tickers.py:258-283`):** Selects `_dim` columns, maps to response keys `news_sentiment`/`macro_exposure`. Correct after the 2026-05-27 fix.
5. **iOS decode:** Decodes those keys; when the HTTP call **times out** (30s request / per-call 15–75s), the ViewModel receives an error, not data.
6. **ViewModel:** On error/timeout, dimensions render as "unavailable."
7. **UI:** Shows "unavailable" — **not** because data is missing but because step 5 failed under event-loop starvation (§6 P0).

**Fix:** resolve the P0. The cards repopulate because the data is already there. Secondary: the macro/sector *regime* "Today" cards are genuinely thin (`price_only`, P1 §7).

**Confirmed vs suspected:** The completeness (DB has data) is CONFIRMED from the prior recovery audit. The causal link "unavailable = timeout from event-loop starvation" is CONFIRMED by the live 10.6s `/health` + the synchronous-supabase-in-async-job code path. The only SUSPECTED piece is the exact ViewModel error-to-"unavailable" mapping line (not re-read this session); the behavior is consistent with the trace.

---

## 10. Performance (5–20s Hangs)

**Root cause is §6 P0.** When an enrichment batch runs (200 articles, `max_concurrency=3`, every 2h; or active-ticker refresh, 8 articles/ticker × active universe, every 4h), the synchronous Supabase `.execute()` calls block the single event loop, so *every* concurrent HTTP request — including `/health` — stalls until the blocking call returns. The 5–20s window matches batch duration.

**Evidence:**
- `curl -w` `/health` = **10.6s** (live, this audit).
- Scheduler is `AsyncIOScheduler` on the uvicorn loop (scheduler.py:31).
- Jobs are `async def` but call blocking sync client inline (scheduler.py:5429-5430, 5470-5478).

**Secondary (iOS side, SUSPECTED):** ViewModel may load dimensions serially rather than concurrently, amplifying perceived latency. Worth converting to a `TaskGroup`/`async let` fan-out — but this is a multiplier, not the cause. The cause is server-side.

---

## 11. Auth / JWT Stability

**Verdict: robust. Perceived instability is backend availability + an already-patched sign-out bug.** [CONFIRMED]

- `SupabaseAuthService.getAccessToken()` checks `session.isExpired`, force-refreshes, returns fresh token (SupabaseAuthService.swift:181-206).
- `checkSession()` pre-warms a refresh on launch (146-168) so the first API calls have a fresh token.
- `APIService` on 401: if not already a retry → `refreshSession()` + retry once; second 401 posts `.clavixSessionExpired` (unless suppressed). Sound retry ladder.
- Recent commit `2e03287f0` already fixed `fetchPreferences` wrongly triggering session-expired sign-out.

The only auth-adjacent risk is **deliverability** of reset/confirm emails (§7.3), not token logic.

---

## 12. Data Cadence Recommendations

Current cron (`/etc/cron.d/clavix`, all UTC) + in-process intervals. Recommended V1 cadence:

| Data | Current | Recommended V1 | Why |
|---|---|---|---|
| EOD prices | 20:15 UTC daily | Keep | Sufficient for daily briefing |
| Macro snapshot | 09:00 UTC (ET 05:00) | Keep, but ensure narrative (not `price_only`) | Briefing needs the narrative |
| Sector snapshot | 09:15 UTC | Keep + dedup XLK | #35 |
| Composite/rollup | 10:00 / 10:45 | Keep | Aligns with briefing build |
| Daily alerts/digest | 21:00 UTC | Align to user `digest_time` | Per-user already wired |
| News (active tickers) | every 4h in-process | **Move to cron / separate worker** | Event-loop fix (P0) |
| Bulk sentiment enrich | every 2h in-process | **Move off web process** | Event-loop fix (P0) |

**Principle:** nothing that does heavy LLM/DB work should run inside the web container's event loop. The `docker exec ... python -m app.jobs.run` cron pattern already exists — route enrichment through it.

---

## 13. The Dead Verification Gate

`is_product_visible` / `data_status` / `verification_status` columns were migrated but are **unwired** — they do not gate anything. [CONFIRMED prior]
**Recommendation:** either (a) delete them to avoid the illusion of a safety gate, or (b) wire them as the actual product-visibility filter. Do **not** ship with a dead gate that future-you assumes is protecting users. For V1, deletion is simpler; the honest limited-data handling in `ticker_cache_service.py` already covers the real need.

---

## 14. Website (getclavix.com)

**Verdict: live, honest, non-advisory, well-built. Two issues: source drift + DMARC.** [CONFIRMED]

Live probes (this audit):
```
/           -> 200
/privacy    -> 200  <title>Privacy Policy - Clavix</title>   (17,100 bytes)
/terms      -> 200  <title>Terms of Service - Clavix</title> (20,329 bytes)
/refund     -> 200  <title>Refund Policy - Clavix</title>    (14,409 bytes)
/methodology-> 200  <title>Methodology - Clavix</title>      (13,048 bytes)
/confirm    -> 200
```
- **All four legal pages exist with distinct real content.** Good for App Store review.
- **Advisory language audit (index.html):** Clean. Hero, FAQ, and footer explicitly state informational-only, "does not recommend buys, sells, position changes, trading actions, or price predictions" (index.html:687, 705), "Not for trading calls" (661), "No predictions. No recommendations." (647). Footer risk disclaimer present (705). This is exactly the non-advisory posture V1 needs.
- **Branding:** "CLAVIX" throughout; no "Clavis"/"Clavynx"/"SnapTrade" leakage in user copy. (One forward-looking line mentions "connect your brokerage when Pro access opens," index.html:628 — **flag:** this implies a feature that's CUT for V1. Soften to avoid promising brokerage sync.)
- **Pricing:** "Pro $20/month after trial," "14-day Pro trial," "No credit card required," "Free tier available" (index.html:560, 697). Matches CLAVIX_TRUTH. The trial promise must be honored by StoreKit config.

**Issues:**
1. **Source drift [CONFIRMED]:** live legal pages + live homepage are **not** in this repo (`web/` has only `index.html` + `confirm.html`; `render.yaml` publishes `./web`). Live homepage is 31,154 bytes vs repo's 50,623. Production is being served from something other than this repo's `web/` (or a divergent deploy). **Risk:** legal page edits aren't version-controlled here. Commit the real sources.
2. **"Connect your brokerage" copy** promises a cut feature — adjust.

---

## 15. Email / DNS (Zoho / Cloudflare)

DNS probes (this audit):
```
MX:    route1/2/3.mx.cloudflare.net   (Cloudflare Email Routing — forwarding)
SPF:   v=spf1 include:_spf.mx.cloudflare.net ~all          [present, OK]
TXT:   zoho-verification=zb07698488... ; google-site-verification=...
DMARC: (empty)                                              [MISSING]
DKIM:  zoho._domainkey -> (empty)
A:     172.67.163.1 / 104.21.49.126   (Cloudflare)
```
**Findings [CONFIRMED]:**
- **Inbound mail = Cloudflare Email Routing (forwarding), not full Zoho mailboxes.** A leftover `zoho-verification` TXT exists but MX points to Cloudflare → Zoho is not actually receiving. `support@getclavix.com` (index.html:704) is a forward — fine for receiving contact mail.
- **DMARC absent** → weaker anti-spoofing and deliverability. Add `_dmarc.getclavix.com TXT "v=DMARC1; p=none; rua=mailto:..."` (start with `p=none`, monitor, then tighten).
- **The real launch email risk is transactional, not contact mail.** Password reset / signup confirmation are sent by **Supabase**, not Zoho/Cloudflare. Supabase default SMTP is heavily rate-limited and spam-prone. **Configure a custom SMTP provider in Supabase Auth** (e.g., Resend/Postmark/SES) before inviting beta users, or confirmations will silently fail.

---

## 16. iOS App / Config

- **Display name** `Clavix`, bundle `com.clavisdev.portfolioassistant`, URL schemes `clavix` + `clavis` both present (Info.plist:9-10, 18-24). launch_issues #6 (URL scheme) **FIXED**. [CONFIRMED]
- **Backend base URL** `https://clavis.andoverdigital.com` (Info.plist:14). Timeouts: request 30s / resource 90s; per-call 15–75s (APIService).
- **`UIBackgroundModes: remote-notification`** present (Info.plist:74-77) — ready for push once APNs key exists.
- **Stale `trycloudflare.com` ATS exception** (Info.plist:62-72) — dev cruft; remove for App Store optics. [CONFIRMED]
- **Secrets.xcconfig** is git-tracked but contains only the **anon** Supabase JWT (role:anon, public/safe) + base URL — **not** a service-role leak. [CONFIRMED prior]
- **APNs default title** is "Clavix Update" (apns.py:75) — the "Clavynx" typo is **FIXED**. [CONFIRMED prior]
- **Mock-only VisualQA values** (`backlog.md` table) must not ship — verify `ClavixVQAComponents.swift` (modified in working tree) doesn't surface mock numbers in release.

---

## 17. Security / RLS

[CONFIRMED prior — Supabase advisors]
1. **ERROR: `gnews_wrapper_resolution` RLS disabled** → anon-readable. Enable RLS + restrict.
2. **Two SECURITY DEFINER RPCs anon-executable** → potential fake-data injection. Revoke anon `EXECUTE` or add an auth check inside.
3. **Leaked-password protection OFF** → enable in Supabase Auth.

None are catastrophic for a small closed beta, but #1 and #2 should close before public launch. The app's own auth/RLS posture (anon key client-side, per-user RLS on `positions`/`watchlist_items`) is sound.

---

## 18. VPS / Scheduler / Freshness

- **Deploy:** DigitalOcean `134.122.114.241`, Docker Compose (`clavis-backend-1`), Cloudflare Tunnel `clavis-prod` → `clavis.andoverdigital.com`. `render.yaml` deploys **only** the static `web/` site (not the backend). [CONFIRMED prior]
- **Scheduler:** in-process `AsyncIOScheduler` started in `main.py` lifespan; `SCHEDULER_TIER` gates daily-vs-intraday jobs (scheduler.py:5560-5609). **Enrichment jobs run regardless of tier** (5599-5600) — this is the P0 vector.
- **Cron:** `/etc/cron.d/clavix` runs 14 jobs via `docker exec clavis-backend-1 python -m app.jobs.run <job>` — a **good** out-of-process pattern that enrichment should join.
- **Freshness:** snapshots 504/504 complete; prices ~30h stale on macro/sector "Today" regime cards (P1).

---

## 19. LLM Capacity / Backfill Math

Plan: **4,500 requests / 5 hours = 900/hr = 15/min sustained.** [estimates — SUSPECTED, label accordingly]

- **Bulk enrichment run:** ≤200 articles, 1 LLM call each, `max_concurrency=3`, every 2h → ≤200 calls/run. **Well under budget.**
- **Active-ticker news refresh:** `limit_per_ticker=8`, `max_concurrency=4`, every 4h. For a small beta (≤100 users × ≤8 tickers) the active union is ~100–300 tickers → up to ~800–2,400 calls/run if all articles are new. **Approaches but stays under** 4,500/5h. Watch it.
- **Full SP500 backfill (504 tickers):** if each ticker costs ~5–10 LLM calls (per-article sentiment + dimension synthesis) → **~2,500–5,000 calls**. Run all at once and you can **exceed** 4,500/5h. **Action:** chunk the backfill (e.g., 100 tickers/window) and throttle to ≤15/min. Never trigger a full backfill and a refresh simultaneously.

**Net:** steady-state V1 traffic is comfortably within plan; **the only capacity risk is an unthrottled full backfill.**

---

## 20. Monetization — Can It Charge $20/mo?

**Not today.** [CONFIRMED prior]
- StoreKit 2 is absent — no product, no purchase, no entitlement gate. This is a P0 for a *paid* launch.
- The free/Pro split (3 holdings/5 watchlist vs unlimited) and $20/mo + 14-day trial are specified (CLAVIX_TRUTH, website) but not enforced via a real purchase.
- **To charge:** (1) create the auto-renewing subscription + 14-day intro offer in App Store Connect; (2) implement StoreKit 2 purchase + `Transaction.currentEntitlements` gate; (3) map entitlement → server-side Pro flag (or client-trust for V1); (4) test in sandbox.
- **Alternative for a free closed beta (Day-21 TestFlight):** ship **without** StoreKit, everyone on Pro-equivalent, defer paid to the Day-28 App Store stage. This matches the two-stage launch plan in memory and de-risks the weekend. **Recommended.**

---

## 21. App Store / TestFlight Readiness

- **Blocked on Apple enrollment** (P0, §6.3). Interim: mom's personal account, branded Clavix.
- **Need:** signing/provisioning, app record, screenshots, privacy nutrition labels (declare: account email, portfolio tickers; "data not sold" already claimed on site), support URL (`support@getclavix.com`), marketing URL (getclavix.com), and the live legal pages (✓).
- **Reviewer risk:** non-advisory positioning is strong; ensure in-app copy matches the website's disclaimers. Remove the `trycloudflare.com` ATS exception. Ensure no mock VQA numbers ship.
- **Two-stage plan (from memory):** Day 21 free closed TestFlight (no StoreKit) → Day 28 App Store + StoreKit. Keep it.

---

## 22. Weekend Execution Plan (Ordered)

**Saturday AM — Stop the bleeding (P0 #1):**
1. SSH VPS, set `DISABLE_NEWS_ENRICHMENT=true`, restart `clavis-backend-1`. Re-probe `/health` (expect <500ms). **[needs your go-ahead — production action]**
2. Verify ticker detail cards repopulate (data was never missing).
3. Begin the real fix: move enrichment to the existing `python -m app.jobs.run` cron path (out-of-process), then it's safe to re-enable.

**Saturday PM — Backend hardening:**
4. Close RLS/RPC advisor findings (§17).
5. Run daily macro/sector snapshot jobs; confirm narrative (not `price_only`).
6. Add DMARC; configure Supabase custom SMTP.

**Sunday AM — App Store track:**
7. Apple enrollment paperwork (interim account).
8. Commit live legal-page sources into `web/`; soften "connect your brokerage" copy.
9. Remove `trycloudflare.com` ATS exception; verify no mock VQA values in release build.

**Sunday PM — Decide monetization track:**
10. If Day-21 free beta: skip StoreKit, ship TestFlight. If paid now: implement StoreKit 2 (L effort — likely slips past weekend).

---

## 23. Command Checklists

**Re-verify production health:**
```
curl -s -o /dev/null -w "health=%{http_code} %{time_total}s\n" --max-time 20 https://clavis.andoverdigital.com/health
```
**Apply P0 mitigation (after approval):**
```
ssh root@134.122.114.241
# add DISABLE_NEWS_ENRICHMENT=true to the backend env / compose env file
docker compose -f /opt/clavis/docker-compose.yml restart   # or the project's restart path
docker exec clavis-backend-1 env | grep DISABLE_NEWS_ENRICHMENT
```
**Verify scheduler jobs gone quiet:**
```
docker logs --since 15m clavis-backend-1 | grep -E "BULK_ENRICH|NEWS_REFRESH"
```
**DNS/email:**
```
dig +short TXT _dmarc.getclavix.com   # currently empty — add record
```

---

## 24. Do NOT Touch This Weekend

- SnapTrade / brokerage / trading code (CUT)
- Any advisory/recommendation features (CUT, legal)
- The scoring methodology / weights (working, complete)
- The auth token logic (robust; don't destabilize)
- Multi-portfolio, social, options/crypto (CUT)
- A from-scratch enrichment rewrite — just move it out-of-process; don't redesign it

---

## 25. Final Go/No-Go

**GO — conditional, in two stages.**

- **Today: NO-GO for a paid public launch.** Two hard stops: API is degraded (P0 #1) and there's no StoreKit (P0 #2).
- **This weekend → Day 21: GO for a free closed TestFlight beta**, *provided* you fix the event-loop defect (which makes the app feel broken), finish Apple enrollment, and ship without StoreKit (everyone Pro-equivalent). The product is honest, non-advisory, and the data is complete — it's a credible beta.
- **Day 28 → paid App Store: GO once** StoreKit 2 + entitlement gate is implemented and the P1 list (legal source, email SMTP/DMARC, RLS findings, macro/sector narrative) is closed.

**Can it charge $20/mo?** Yes, the value (transparent daily multi-dimension risk briefing with full methodology) justifies it — but **only after StoreKit exists.** Until then, charging is impossible, not merely unwise.

**Biggest hidden risk:** the **source-control drift on the live website/legal pages** (§14). The pages App Store review will read are not in this repo. If someone redeploys `web/` from this repo, the legal pages could vanish — an App Store rejection and a compliance gap in one move. Commit the real sources before any web redeploy.

**Next 10 tasks, in order:**
1. (Approval) Apply `DISABLE_NEWS_ENRICHMENT=true` + restart; verify `/health` <500ms.
2. Move enrichment to out-of-process cron; re-enable safely.
3. Run macro/sector snapshot jobs; confirm narrative populates.
4. Close `gnews_wrapper_resolution` RLS + the two anon RPCs.
5. Configure Supabase custom SMTP; add DMARC `p=none`.
6. Commit live legal-page + homepage sources into `web/`.
7. Apple Developer enrollment (interim account).
8. Remove `trycloudflare.com` ATS exception; audit release build for mock VQA values.
9. Soften "connect your brokerage" website copy (cut feature).
10. Decide StoreKit-now vs free-beta; if free beta, ship TestFlight.

---

### Confirmed vs Suspected — Quick Index
- **CONFIRMED (directly observed this session or prior recovery):** event-loop starvation mechanism + live 10.6s health; DB completeness 504/504; website live/legal/non-advisory; source drift; email = Cloudflare routing + missing DMARC; iOS config (Info.plist, URL schemes, ATS cruft); auth robustness; scheduler structure + kill switch.
- **SUSPECTED (needs one more check):** exact ViewModel error→"unavailable" mapping line; iOS serial-vs-concurrent dimension loading; precise LLM-calls-per-ticker for backfill math; whether `DISABLE_NEWS_ENRICHMENT` is already set on the VPS (the live 10.6s implies it is **not**).
