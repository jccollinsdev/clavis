# Clavix 21+7 Day Road to Launch Plan

## Revised Continuation Plan

**Date:** 2026-05-25  
**Owner:** Sansar + Codex  
**This section supersedes conflicting guidance below.**

### Launch Definition

The launch target is:

- **Closed TestFlight beta**
- **Real app functionality**, not mock flows
- **StoreKit sandbox payments if feasible**
- **Legal pages and disclaimers present**
- **Data pipeline, backfill, and scheduler verified with evidence**
- **No public App Store launch unless separately approved**

Human approval gates are mandatory before:

- any production deploy
- any secrets or env changes
- any payment setup that changes real commercial behavior
- any public launch announcement
- any external tester rollout beyond your explicitly approved cohort

### Recommendation

#### Plan A

Closed TestFlight beta in 21 days **with** StoreKit sandbox payments.

This is feasible only if:

- Apple Developer enrollment starts immediately
- EIN recovery happens immediately
- Mercury or equivalent banking setup starts immediately
- App Store Connect agreements do not stall
- “working payments” means sandbox purchase/restore/manage for TestFlight, not public-launch-grade billing infrastructure

#### Plan B

Closed TestFlight beta in 21 days **without** payments, then payments on days 22–28.

This is safer because the repo still lacks:

- any real StoreKit code
- any entitlement backend
- any job-health proof from production
- any backfill proof from production

#### Recommendation

**Recommend Plan B.**

If you force Plan A, keep the scope narrow:

- sandbox-only
- closed testers only
- explicit approval before public launch
- no pretending the backend entitlement model is public-launch complete

### 21-Day Timeline

The schedule assumes intense work, but not reckless work. Keep one light or buffer block every 6-7 days.

#### Day 1

- Start Apple Developer Program enrollment as an **Organization** for Andover Digital LLC.
- Search for EIN paperwork for one focused hour. If not found, prepare IRS call for Day 2 morning.
- Decide Plan A vs Plan B now. Everything else branches from that.
- Start Mercury signup the moment EIN is recovered.

#### Day 2

- Verify the current production scheduler state from VPS and Supabase, not from repo assumptions.
- Check whether `/etc/cron.d/clavix` is installed and whether `job_runs` has recent successful rows.
- If `backfill_14d` has never run, schedule the first safe run window and capture exact commands/logging steps.
- IRS call if EIN is still missing.

#### Day 3

- Run the news canary against a safe representative ticker set using `backend/scripts/canary_10_tickers.py`.
- Capture success/failure counts, blocked domains, and enrichment completeness.
- Freeze the acceptance thresholds for “news system is good enough for TestFlight.”

#### Day 4

- Run or dry-run the 14-day backfill plan in the target environment.
- Capture runtime, batch size, failure behavior, and validation queries.
- Do not call the system “fresh” until the validation SQL is saved and reviewed.

#### Day 5

- Fix P0 trust bugs in the app:
  - add `clavix://`
  - keep `clavis://`
  - remove `armv7`
  - fix APNs `Clavynx Update`
- Rebuild iOS and re-check deep-link and push assumptions.

#### Day 6

- Lock the beta legal/trust surface:
  - Privacy
  - Terms
  - Refund
  - Methodology / disclaimer
- Make sure the website, app settings, and launch copy all point to live pages.
- Add an in-app disclaimer surface if it does not already exist.

#### Day 7

- Decide whether legal pages live in this repo or in a separate site repo.
- If separate, document the real source of truth and stop pretending this repo owns website deployment.
- Align waitlist copy with actual beta/payment status.

#### Day 8

- Build or expose an admin job-health endpoint/dashboard for:
  - last success
  - expected cadence
  - stale/missed status
  - recent failures
- This must show scheduler truth without SSH.

#### Day 9

- Resolve the scheduler snapshot-date test failure and review date-boundary behavior.
- If the failure is only a test bug, prove it.
- If it is a real runtime bug, treat it as a P0 trust issue because freshness history is core product truth.

#### Day 10

- Validate APNs end-to-end once Apple Developer access exists.
- Confirm backend `/health` reports APNs configured.
- Send a test push from the push-test route and verify device delivery.

#### Day 11

- Freeze the beta auth/account model.
- Confirm whether TestFlight users must sign up/login.
- Verify signup, auth callback, onboarding, and add-holding flow end-to-end.

#### Day 12

- If Plan B: keep payment UI hidden or clearly labeled as not live in beta.
- If Plan A: start App Store Connect subscription setup and product IDs.
- Either way, stop the website from promising more than the beta can actually do.

#### Day 13

- Implement or finish StoreKit 2 client scaffolding if Plan A.
- Minimum acceptable scope:
  - products load
  - purchase works
  - restore works
  - manage-subscription link works

#### Day 14

- Define the beta entitlement model.
- Decide whether backend Pro access in closed beta will be:
  - fully entitlement-backed, or
  - sandbox-local in app plus approved backend tester allowlist
- Document that this is a beta-only compromise if you choose the second option.

#### Day 15

- Run first internal device QA pass:
  - signup
  - onboarding
  - add holding
  - digest
  - holdings
  - ticker detail
  - alerts
  - settings/legal links
  - push
  - refresh

#### Day 16

- Fix all trust-breaking bugs found in internal QA.
- Do not spend this day polishing typography while freshness or legal trust is still soft.

#### Day 17

- App Store Connect metadata pass:
  - app description
  - subtitle
  - keywords
  - support URL
  - privacy policy URL
  - screenshots list
- If Plan A, verify sandbox product metadata is accepted.

#### Day 18

- Build the first TestFlight candidate.
- Install and test on real devices.
- Capture crashes, empty states, misleading copy, and stale-data edge cases.

#### Day 19

- Closed beta readiness review.
- Check exact gates:
  - iOS build
  - backend tests
  - data freshness audit
  - backfill evidence
  - scheduler evidence
  - legal links
  - disclaimer presence
  - payment scope truthfulness

#### Day 20

- Final fixes only.
- No new features.
- No scope creep.
- No “while I’m here” refactors.

#### Day 21

- Human approval gate.
- If approved:
  - release closed TestFlight build to trusted testers
  - publish accurate waitlist/tester instructions
  - monitor job health, auth failures, crashes, and support feedback
- If not approved:
  - slip the release instead of shipping a trust-damaging beta

### Payment Scope

#### Exact StoreKit tasks

1. App Store Connect app exists under the correct Apple Developer org.
2. Paid Apps / banking / tax prerequisites are completed enough to create subscription products.
3. Product identifiers are chosen and frozen.
   - Example: `clavix_pro_monthly`
   - Example: `clavix_pro_annual`
4. iOS StoreKit 2 client loads products.
5. Purchase flow works in sandbox.
6. Restore flow works in sandbox.
7. Manage-subscription deep link is available.
8. Entitlement storage model is defined.
9. Backend entitlement verification approach is defined.
10. Sandbox testing matrix is executed on real devices.

#### Acceptable TestFlight scope vs public-launch scope

For **TestFlight**, acceptable if needed:

- sandbox-only
- purchase / restore / manage work
- backend uses a documented beta entitlement compromise

For **public launch**, not acceptable:

- trusting client-only unlock state
- manual entitlement flips as the primary system
- no receipt / transaction verification plan
- no support path for restore failures

#### Fallback if server-side verification is too much for 21 days

- Ship Plan B.
- Or ship Plan A with:
  - sandbox purchase UI working
  - backend Pro access limited to approved closed-beta testers
  - explicit note in the launch docs that public-launch billing is not done yet

### Data Pipeline Scope

#### Safe local / operator commands

- News canary:
  - `cd backend && python3 scripts/canary_10_tickers.py`
- One-shot job dry run:
  - `cd backend && python3 -m app.jobs.run daily_macro_snapshot --dry-run`
- Full backfill job:
  - `cd backend && python3 -m app.jobs.run backfill_14d`
- iOS build:
  - `cd ios && xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build`

#### Scheduler / backfill / freshness tasks

1. Verify cron installed on VPS.
2. Verify `job_runs` has recent successful rows.
3. Verify `daily_macro_snapshot`, `daily_sector_snapshot`, `daily_composite_recompute_universe`, and `daily_portfolio_rollup_per_user` all complete on schedule.
4. Run the news canary and save the report.
5. Run the 14-day backfill and save the results.
6. Save validation SQL for freshness review.

#### Validation SQL

Use queries like:

```sql
select job_id, status, started_at, completed_at
from job_runs
where started_at > now() - interval '7 days'
order by started_at desc;
```

```sql
select ticker, snapshot_date, composite_score, grade
from ticker_risk_snapshots
where ticker = 'AAPL'
order by snapshot_date desc
limit 20;
```

```sql
select ticker, extraction_status, sentiment_score, published_at
from shared_ticker_events
where ticker in ('AAPL','NVDA','MSFT')
order by published_at desc;
```

#### Runtime / failure guidance

- `backfill_14d` is repo-documented as roughly an hour-scale operation, but treat that as an estimate until you measure it in your environment.
- Do not trust “completed” alone. Validate row counts and sample outputs.
- Capture failures by ticker/day and save them into the audit trail.

### Legal / Security Scope

- This plan is **not legal advice**.
- Closed TestFlight still needs privacy basics, terms access, and plain-English disclaimers.
- A real lawyer should review the public-facing methodology/disclaimer/ratings framing before any public launch.
- The repo evidence does **not** currently prove a production-grade payment entitlement system.
- The old “self-editable `subscription_tier` via `/preferences`” finding appears stale, but the broader security issue remains:
  - real entitlements do not exist yet
  - server gates still rely on `user_preferences.subscription_tier`

### Definition of Done

The closed TestFlight beta is done only when all of the following are true:

- iOS build passes.
- Backend tests pass at an acceptable threshold and known failures are explicitly triaged.
- Critical data audit passes.
- Scheduler firing is verified with evidence.
- Backfill is verified with evidence.
- Legal pages are live.
- In-app disclaimers are present.
- No fake or misleading app-visible data remains on core surfaces.
- Live backend health is green enough for beta.
- APNs is either working or explicitly deferred as non-blocking.
- StoreKit sandbox purchase/restore works **or** payments are explicitly deferred under Plan B.
- TestFlight metadata is ready.
- Human approval is given before external testers are invited.

---

**Historical plan content follows below. Keep it as context only.**

**Date authored:** 2026-05-25 (revised after user round-2 decisions)
**Day 21 target:** 2026-06-15 — closed TestFlight beta, **FREE only** (no Pro / no payments), ~100 invites from waitlist
**Day 28 target:** 2026-06-22 — App Store public launch with StoreKit 2 Pro subscriptions live ($20/mo + 14-day trial)
**Authority:** Pairs with `roadtolaunch_audit.md`. The audit identifies what's wrong; this file says when each fix lands.

> Assumes 10+ focused hours/day. Hours per day flagged so you can compress if you work 14 hours or stretch if you work 8.

## Decisions baked in (from user round-2)

1. **Day 21 = Closed TestFlight beta, FREE only.** StoreKit work happens in parallel through week 3 and ships at Day 28 with the App Store public launch.
2. **EIN retrieval = search first.** Spend ~1h on Day 0 looking through email, IRS confirmation letter PDFs, prior tax docs, formation paperwork. Fallback: call IRS Business & Specialty Line (800-829-4933, 7am-7pm local) and request a 147C letter (same-day fax if you can prove identity).
3. **Business bank = Mercury** (online, 24-48h approval for LLCs with EIN).
4. **Andover Digital LLC is formed**, EIN exists but document is lost. No business bank yet.
5. **`backfill_14d` has never run.** Day 1 task.
6. **News pipeline just finished hardening** (commits `f277ea442` → `b55b02168`). Untested at sustained load. Day 2 task.
7. **Scheduler code shipped** (commits `10c587ff0` P3 → `aa31c7a2e` P8). User will SSH into VPS to verify cron is actually firing as Day 0 task.

---

## Launch Definition

Two-stage launch decided:

| Stage | Day | What it means | Payments? | What it gates |
|---|---|---|---|---|
| **Stage 1: Closed TestFlight beta** | Day 21 (Mon Jun 15) | Invite-only ~100 testers from waitlist | **No** — all Pro features either off or unlocked-for-everyone | Apple Dev + ToS/Privacy + APNs + first-run disclaimer + minimum data trust + Mercury account |
| **Stage 2: App Store public launch w/ payments** | Day 28 (Mon Jun 22) | App Store live; StoreKit 2 Pro $20/mo with 14-day trial; press launch | **Yes** | All of Stage 1 + StoreKit 2 end-to-end + entitlement webhook + App Store review approval |

StoreKit work happens **in parallel** through Days 14–21 instead of sequential after the beta. This means closing the 21-day target as planned, and the App Store submission window is Day 22–25 (with reviewer wait 1–5 days for finance apps).

**Pro-feature gating during the Stage 1 beta.** Decision needed (see questions below): either (a) unlock all Pro features to all beta testers (simpler; helps you collect Pro-feature feedback for free), or (b) only ship Free-tier surfaces and disable Pro features entirely during beta. Recommendation: **(a)** — you'll get more signal on the methodology drill-down + watchlist + verbose digest from sophisticated testers if they can use them.

---

## Strategy

The fastest *safe* path is:

**Day 0 (today/tonight).** Three independent, can't-be-parallelised long poles open in one evening: (1) SSH to VPS, confirm cron is firing, kick off `backfill_14d` as a tmux job; (2) search for EIN paperwork (1h cap, else call IRS tomorrow 7am ET); (3) open the Apple Developer Program enrolment page and start the 24-48h verification clock. Each is <1 hour of your time; Apple's verification then runs while you sleep.

**Week 1 (Days 1–7) — Trust + legal + Mercury.** Privacy/Terms/Refund/Methodology pages; in-app first-run disclaimer; `subscription_tier` lockdown; Digest vs Holdings grade reconciliation; APNs key deployed; Mercury bank account opened (parallel: 24-48h); news pipeline live-fire test (since it's the freshest, least-tested system). End of week: internal alpha on your own iPhone.

**Week 2 (Days 8–14) — Polish + StoreKit kickoff.** Bug-fix off internal alpha; lawyer call + implement feedback; remaining iOS screens migrated to Hi-Fi v2; App Store Connect app record + StoreKit subscription products configured; iOS StoreKit 2 client started (Day 14); 5 sim screenshots; press kit assembled.

**Week 3 (Days 15–21) — StoreKit complete + closed beta launch.** StoreKit server webhook + entitlement table + sandbox testing (Days 15–18). Internal beta on 5–10 trusted testers Day 16. Day 19–21: drip-invite the waitlist (20 → 50 → 200) in batches; closed TestFlight beta is live **without payments active**.

**Week 4 (Days 22–28) — StoreKit live in TestFlight + App Store submission.** Days 22–24: turn on StoreKit in TestFlight sandbox, verify entitlement flow end-to-end with 2–3 real testers; Day 25: submit to App Store (allow 1–5 days for finance review); Day 28: App Store goes live with $20/mo Pro + 14-day trial.

Optimise for **trust** > polish throughout. A sophisticated investor noticing one fabricated number is worse than 10 ugly screens.

---

## Non-Negotiable Launch Gates

What must be true before the first non-Sansar tester taps Install.

### Legal
- [ ] Andover Digital LLC formed, in good standing, EIN issued
- [ ] Privacy Policy live at `getclavix.com/privacy`
- [ ] Terms of Service live at `getclavix.com/terms`
- [ ] Refund Policy live at `getclavix.com/refund`
- [ ] Methodology page live at `getclavix.com/methodology`
- [ ] In-app first-run disclaimer with accept-checkbox; audit row in `user_legal_acks`
- [ ] Securities lawyer has read the marketing copy + in-app rating language at least once

### Trust
- [ ] Portfolio composite grade is identical across Digest and Holdings (value-weighted everywhere)
- [ ] `backfill_14d` has been run; score-history sparklines render real points
- [ ] `/admin/job_health` shows all tier-1 jobs `status=completed` for the last 7 consecutive days
- [ ] `freshness.as_of` is visible on Today/Holdings/Ticker screens
- [ ] First push notification says "Clavix" not "Clavynx"

### Security
- [ ] `subscription_tier` is not writable via `/preferences`
- [ ] APNs `.p8` deployed; `/health` says `"apns":"configured"`
- [ ] Supabase RLS verified on every user-data table (manual SQL audit)
- [ ] No localhost in prod CORS allowlist
- [ ] Admin password rotated; admin session secret regenerated

### iOS
- [ ] Build succeeds against deployment target iOS 17.0
- [ ] `clavix://` URL scheme registered (alongside `clavis://`)
- [ ] `arm64` in `UIRequiredDeviceCapabilities` (not `armv7`)
- [ ] Sentry-Cocoa initialised
- [ ] First-run disclaimer ships
- [ ] Outside-universe degraded-mode add path works
- [ ] Alerts unread badge honest (uses `read_at`)
- [ ] App Store icon at all sizes including 1024×1024 marketing

### Infrastructure
- [ ] Apple Developer Program account live
- [ ] TestFlight build uploaded and processing
- [ ] Production cron has produced 7+ days of completed `job_runs`
- [ ] Sentry DSN set in prod env; events flowing
- [ ] Post-deploy smoke tests added to `deploy-prod.yml`
- [ ] 30-min job-health cron alerts to a real channel
- [ ] Backups of Supabase confirmed (PITR enabled)

### Marketing
- [ ] App Store description (4,000 chars) drafted
- [ ] 5 App Store screenshots
- [ ] Promotional text (170 chars)
- [ ] Keywords (100 chars)
- [ ] Demo video (30s) recorded
- [ ] Press kit assembled
- [ ] Waitlist confirmation email sequence drafted (3 emails minimum)
- [ ] Analytics (Plausible or PostHog) live on website
- [ ] Privacy nutrition labels filled out in App Store Connect

---

## 21+7 Day Timeline

ET timezone throughout. "Sansar" = items only you can do (account creation, financial decisions, lawyer calls, SSH). "claude-code" = items Claude Code can carry end-to-end with you reviewing PRs. "designer" = items needing visual work — record where you'll source this (you, contractor, AI-assisted).

### Day 0 (tonight) — Open the three long poles before bed

| Lane | Task | Owner | Hours | Output |
|---|---|---|---|---|
| 🔴 Critical | **SSH into VPS, verify cron is firing.** `ssh root@<vps-ip>`; `tail -100 /var/log/clavix/cron.log`; in Supabase SQL editor or via `docker exec`: `SELECT job_id, status, started_at, completed_at FROM job_runs WHERE started_at > now() - interval '7 days' ORDER BY started_at DESC LIMIT 50;`. If empty or any tier-1 job missing, document the gap. If `clavix.crontab` was deployed but cron service was reloaded incorrectly, run `sudo systemctl reload cron`. | Sansar | 0.5 | log + screenshot of last 50 job_runs rows |
| 🔴 Critical | **Kick off `backfill_14d` against prod** if cron is verified working. `tmux new -s backfill 'docker exec clavis-backend-1 python -m app.jobs.run backfill_14d'`. Runs ~1h. Don't wait for it; come back in the morning. | Sansar | 0.2 active + 1h passive | tmux session running |
| 🔴 Critical | **Search for EIN paperwork** — search Gmail/Outlook for "EIN", "147C", "Andover Digital", "Internal Revenue Service"; check `~/Documents` for LLC formation PDF; check Stripe Atlas (if used) which stores EIN in the dashboard. **1h cap.** If not found, schedule a call to IRS 800-829-4933 for tomorrow 7am ET. | Sansar | 1 | EIN written down OR IRS call scheduled |
| 🔴 Critical | **Open Apple Developer Program enrolment.** `developer.apple.com/programs/enroll`. Use your Apple ID. Choose **Organization** (not Individual). Enter Andover Digital LLC. Apple verifies the legal name match — they will check D-U-N-S Number; if no D-U-N-S exists they'll prompt to create one (free via Dun & Bradstreet). Pay $99. | Sansar | 0.5–1 | tracking number; D-U-N-S pending if first-time |
| 🟢 Trust | While the above ticks, run pytest 3.11 on `backend/`: `cd backend && python3.11 -m pytest -q`. Confirm only the 1 known failure remains. | Sansar | 0.5 | clean log |

**Day 0 main goal.** Three long-pole clocks running before you sleep. Backfill writing rows while you're not at the keyboard.
**DoD.** `job_runs` returns ≥1 row for `daily_macro_snapshot`, `daily_sector_snapshot`, `daily_composite_recompute_universe`. EIN known or IRS call booked. Apple Dev enrolment submitted.
**Risks.** Apple may flag the org name; D-U-N-S takes 1-3 days. If so, the wait costs a launch day. EIN not found and IRS line opens 7am tomorrow → you call first thing.

### Day 1 (Tue) — Mercury + legal pages + quick-win blockers

| Lane | Task | Owner | Hours | Output |
|---|---|---|---|---|
| 🔴 Critical | **Open Mercury account** at mercury.com — apply with Andover Digital LLC + EIN (call IRS first if not retrieved Day 0). Submit. Mercury verifies in 24–48h. | Sansar | 1 | Application submitted |
| 🔴 Critical | **IRS call if EIN still missing.** 800-829-4933, 7am ET. Ask for 147C letter; provide LLC formation details; they fax (or email PDF) same-day. | Sansar | 0.5 | EIN in hand |
| 🔴 Critical | **Verify `backfill_14d` overnight run completed.** Query `job_runs` for `backfill_14d` status. Sample a ticker's score history (e.g., AAPL) — confirm ~14 rows accrued. | Sansar | 0.3 | screenshot of populated history |
| 🟢 Legal | Draft Privacy Policy + Terms of Service + Refund Policy + Methodology page; publish to `/web/privacy.html`, `/web/terms.html`, `/web/refund.html`, `/web/methodology.html`; re-route footer links | claude-code | 3 | 4 new HTML files; PR |
| 🟢 Legal | Email a securities lawyer (Cooley fintech group, Wilson Sonsini, or a fintech-focused solo on Lawtrades/Upwork — budget $500-1500 for 1h review) requesting review of marketing copy + in-app letter-grade framing; book for Day 5–7 | Sansar | 0.5 | Booked call |
| 🟢 Trust | Fix `subscription_tier` self-elevation (`routes/preferences.py`); add a server-side guard that ignores client writes to the field | claude-code | 1 | PR |
| 🟢 Trust | Fix `apns.py:75` banned brand (`Clavynx Update` → `Clavix`) | claude-code | 5 min | PR |
| 🟢 Polish | Fix `Info.plist`: `armv7` → `arm64`; add `clavix://` to `CFBundleURLSchemes` | claude-code | 30 min | PR |
| 🟢 Analytics | Add Plausible to `web/index.html` (single `<script>` tag) | claude-code | 30 min | PR |
| 🟢 Backend | Build `/admin/job_health` route (queries `job_runs` last 14 days; returns per-job `last_success`, `expected_cadence`, `status`, `consecutive_failures`) — replaces needing to SSH for daily checks | claude-code | 3 | PR + tests |
| Verify | Run full backend test suite locally on Python 3.11; verify all green except the 1 pre-existing failure | Sansar | 0.5 | clean log |
| End-of-day | Push the day's PRs to `main`; verify `/health`, `/privacy`, `/admin/job_health` work in prod | Sansar | 0.5 | green deploy |

**Day 1 main goal.** Mercury submitted (clock running); EIN in hand; legal landing pages live; three quick-win launch blockers closed; `/admin/job_health` shipped so future days don't need SSH.
**Definition of done.** Mercury application submitted. EIN in hand. `getclavix.com/privacy`, `/terms`, `/refund`, `/methodology` return 200. iOS PR open with `armv7→arm64` + `clavix://`. `subscription_tier` write blocked. Score history sparklines now render for AAPL.
**Hours:** ~11.
**Risks.** Lawyer doesn't respond same day → email 2-3 in parallel; cost $500/hr is fine for a 1h call. Mercury rejects → fallback Relay (similar online flow).

### Day 2 (Wed) — News pipeline live-fire test + trust foundations

The news pipeline is the freshest, least-tested system (commits `f277ea442` → `b55b02168` landed it; never run with 503 tickers under real load with sentiment enrichment, on-ingestion sentiment, and the wrapper-decoder circuit). Today verifies it works end-to-end.

| Lane | Task | Owner | Hours | Output |
|---|---|---|---|---|
| 🔴 Critical | **News pipeline live-fire test.** Pick 30 tickers across all 11 sectors (3 each). Wipe `shared_ticker_events` rows for those tickers. Trigger `system_active_ticker_news_refresh` manually. Wait 4h. Verify: (a) every ticker has ≥3 articles, (b) every article has `sentiment_score` non-null, (c) `tldr` + `what_it_means` populated, (d) no `forbidden_phrase` violations, (e) Google-News wrapper URLs resolved to real publishers. | Sansar + claude-code | 4 (mostly waiting) | test report at `docs/AUDITS/news_pipeline_livefire_2026-05-27.md` |
| 🟢 Trust | Add a daily 8:00 ET cron that posts `/admin/job_health` summary to a webhook (Discord/Slack via Resend or n8n) | claude-code | 2 | PR |
| 🟢 iOS | Render `freshness.as_of` next to scores on Today, Holdings, Ticker Detail (data exists in response; rarely shown) | claude-code | 4 | PR |
| 🟢 iOS | Add Sentry-Cocoa pod; init in `ClavisApp` | claude-code | 2 | PR |
| Verify | Open the app in sim; verify the freshness labels render and the timestamps are within 24h | Sansar | 0.5 | screenshot |

**Goal.** News pipeline proves it can sustain real load; visible freshness on user-facing screens; crash reporting live.
**DoD.** All 30 test tickers have ≥3 fully-enriched articles. Today screen shows "Refreshed 06:01 ET" or equivalent. Sentry-Cocoa receives a test crash.
**Hours:** ~12.
**Risks.** Live-fire reveals a Minimax rate-limit issue under load → may push other Day 3 items; budget 2h slack on Day 4. If wrapper-decoder fails on >2% of articles, escalate to a debug session — that's a launch blocker.

### Day 3 (Thu) — Trust day 2 + iOS first-run disclaimer

| Lane | Task | Owner | Hours | Output |
|---|---|---|---|---|
| 🟢 Trust | Reconcile portfolio composite grade — make `routes/digest.py` read from `portfolio_risk_snapshots` instead of computing equal-average; remove the legacy compute; update tests | claude-code | 4 | PR + tests |
| 🟢 Legal | Build iOS first-run disclaimer screen: full-screen modal, "Clavix is informational, not investment advice", checkbox + accept button; on accept, POST `/account/legal-ack` writing to new `user_legal_acks(user_id, version, accepted_at, ip, ua)` | claude-code | 5 | PR (backend table + route + iOS screen) |
| 🟢 Legal | Replace Settings legal links to land on real pages (already fixed by Day 1, verify) | Sansar | 5 min | screenshot |
| 🟢 Email | Wire Resend (or SendGrid); update Supabase Auth email templates to branded Clavix; add a 2-email waitlist confirmation sequence | claude-code | 4 | PR + Resend account |
| Verify | Send a test email; check rendering on Gmail + Apple Mail + Outlook | Sansar | 0.5 | screenshots |

**Goal.** Grade-consistency closed; first-run legal acceptance shipped; transactional email working.
**DoD.** Same portfolio shows same grade on Digest and Holdings. New install → first-run disclaimer → accept → home. `user_legal_acks` has the row. A signup gets a branded confirmation email.
**Hours:** ~13.
**Risks.** Email deliverability; if Resend has DNS issues, use SendGrid as fallback. Pre-warm domain via Resend's domain auth UI.

### Day 4 (Fri) — APNs + outside-universe iOS + Mercury approval

| Lane | Task | Owner | Hours | Output |
|---|---|---|---|---|
| 🔴 Critical | **Verify Mercury approval landed** (24–48h after Day 1 submit). Activate account, order debit card (won't need it for launch but needed for Apple Pay payout setup later). | Sansar | 0.5 | Account active |
| 🔴 Critical | **Generate APNs `.p8` key in Apple Developer portal** (assumes Apple Dev cleared Day 2–3). Save securely; never commit. | Sansar | 1 | `.p8` file |
| 🔴 Critical | **Deploy `.p8` to VPS** at `/etc/secrets/apns.p8`; restart container; verify `/health` says `"apns":"configured"`; trigger a manual push via `/push-test` route | Sansar | 1 | screenshot |
| 🟢 iOS | Plumb outside-universe degraded-mode add path: when search returns "not in universe", show "Add anyway" CTA → POST `/holdings?allow_outside_universe=true` → render `limited_data` banner on the new holding row | claude-code | 5 | PR |
| 🟢 iOS | Update `Alert.swift` model to include `read_at`, `severity`, `destination_*`; mark-read endpoint plumbed; AlertsView shows unread badge using `read_at` | claude-code | 4 | PR |
| Verify | Full end-to-end test on iPhone 17 sim: login → onboarding → disclaimer → add AAPL → add a non-universe ticker → view limited-data banner → receive a test push | Sansar | 1 | log + screenshots |

**Goal.** Mercury account active; APNs live; two user-visible iOS gaps closed.
**DoD.** Mercury account active. Push notification arrives on sim. Adding `BABA` shows a banner not an error. Alerts unread count is honest.
**Hours:** ~12.
**Risks.** Apple Dev enrolment hasn't cleared yet (D-U-N-S delay) — slip APNs to Day 5–6 and pull other work forward. Mercury rejected (rare for clean LLC + EIN) — apply to Relay same day.

### Day 5 (Sat) — Production smoke + cron health alarm + bug-fix

| Lane | Task | Owner | Hours | Output |
|---|---|---|---|---|
| 🟢 Backend | Fix the pre-existing `test_attach_decoded_google_news_urls_rewrites_wrapper_urls` failure | claude-code | 2 | PR; CI fully green |
| 🟢 Pipeline | Add post-deploy smoke tests to `deploy-prod.yml`: curl `/today` (authed), `/holdings`, `/tickers/AAPL`, `/tickers/AAPL/methodology`; fail the deploy if any return non-200 or empty body | claude-code | 3 | PR |
| 🟢 Pipeline | Build the 30-min job-health-alert cron: queries `job_runs` for any tier-1 job whose `last_completed_at` is older than expected; if any, POST to webhook (Discord/Slack/email) | claude-code | 3 | PR + cron entry |
| 🟢 Trust | Manual SQL audit of RLS policies on `positions`, `portfolio_risk_snapshots`, `watchlist_items`, `digests`, `alerts`, `user_preferences`, `user_legal_acks`, `refresh_attempts` — confirm all enforce `auth.uid() = user_id` | Sansar | 2 | audit doc in `docs/AUDITS/rls_audit_2026-05-30.md` |
| 🟢 Marketing | Capture 5 sim screenshots for App Store: Today/Holdings/TickerDetail/Methodology/Alerts (1290×2796 for iPhone 17 Pro Max) | Sansar | 2 | 5 PNGs in `marketing/appstore/` |

**Goal.** Pipeline observability hardened. CI fully green. App Store screenshot draft.
**DoD.** Trigger a fake stale job-run; alarm fires within 30 min. Smoke tests run on next deploy. 5 screenshots saved.
**Hours:** ~12.
**Risks.** RLS audit reveals a missing policy → could be a half-day of repair. Worth doing now.

### Day 6 (Sun) — Slack/wind-down/buffer

Reserve as catch-up day. If Days 1–5 are on track, use today to:
- Tighten CORS allowlist (remove `localhost` from prod)
- Migrate `SettingsView.swift` to `DesignSystem/` primitives
- Migrate `OnboardingContainerView.swift` to `DesignSystem/` primitives
- Verify Sentry DSN actually fires events
- Spin up PostHog for in-app event tracking (5–10 critical events: signup, onboarding-complete, add-holding, view-methodology, alert-tap)

**Hours:** 6–10 depending on slip. Treat as a real day off if everything is green.

### Day 7 (Mon) — Internal alpha: install on your own iPhone

| Lane | Task | Owner | Hours | Output |
|---|---|---|---|---|
| 🔴 Critical | Open App Store Connect; create the `Clavix` app record; set bundle ID `com.clavisdev.portfolioassistant`; primary language English; set up the `Clavix Pro` in-app purchase placeholder (you'll wire StoreKit later) | Sansar | 1 | app record |
| 🔴 Critical | Create distribution certificate + provisioning profile; archive a TestFlight build; upload via Transporter or `fastlane pilot upload` | Sansar | 3 | build in App Store Connect |
| 🔴 Critical | Wait for processing; install on your iPhone via TestFlight; walk the entire app cold | Sansar | 2 | bug list |
| 🟢 Backend | If bugs found during walkthrough, file as GH issues + start fixing | claude-code | rest of day | PRs |

**Goal.** Internal alpha on a real device. Walk every screen with a critical eye. Note everything that's wrong.
**DoD.** TestFlight install works. You've gone through every tab. Bug list filed.
**Hours.** ~10.
**Risks.** TestFlight upload pain (codesigning issues) often eats half a day. Budget tolerantly.

### Day 8 (Tue) — Bug-fix marathon, day 1

Triage the Day 7 bug list. Priority: trust > polish.

| Lane | Task | Owner | Hours |
|---|---|---|---|
| iOS bug-fix | All trust-impacting bugs from walkthrough | claude-code | 4–6 |
| iOS bug-fix | All UX-confusing bugs | claude-code | 2–4 |
| Visual | Polish-only bugs queued for Day 17–18 | — | 0 |
| Verify | Re-walk after each fix batch | Sansar | 2 |

**Hours.** ~12.

### Day 9 (Wed) — Bug-fix day 2 + Lawyer call

| Lane | Task | Owner | Hours |
|---|---|---|---|
| Legal | Lawyer call: review marketing language, in-app letter grades, "not investment advice" framing, registration risk assessment | Sansar | 1.5 |
| Legal | Implement lawyer's changes in ToS/Privacy/disclaimer copy | claude-code | 2–4 |
| iOS bug-fix | Continue Day 7 list | claude-code | 4–6 |
| Verify | Re-walk | Sansar | 1 |

**Hours.** ~12.

### Day 10 (Thu) — Mid-point review + buffer day 1

Stop. Take 2 hours. Open `roadtolaunch_audit.md`. For every P0 and P1 item, check it off or move it. Identify slippage. Decide whether to compress Days 11–14 or drop polish items.

| Lane | Task | Hours |
|---|---|---|
| Review | Audit checklist review | 2 |
| Replan | Update Day 11–21 if needed | 1 |
| Slip fix | Whatever's slipped most | 6–8 |

**Hours.** ~10.

### Day 11 (Fri) — Onboarding polish + Today migration to Hi-Fi v2

| Lane | Task | Owner | Hours |
|---|---|---|---|
| iOS | Migrate `OnboardingContainerView` to `DesignSystem/` primitives (if not already done in Day 6) | claude-code | 4 |
| iOS | Migrate `DigestView` / Today tab to use Hi-Fi v2 primitives for the header + portfolio-grade card | claude-code | 4 |
| Verify | Walk the new onboarding cold | Sansar | 1 |
| Marketing | Record 30-second app demo on sim (screen recording) | Sansar | 2 |

**Hours.** ~11.

### Day 12 (Sat) — Holdings + Search migration

| Lane | Task | Owner | Hours |
|---|---|---|---|
| iOS | Migrate `HoldingsListView` to Hi-Fi v2 primitives | claude-code | 5 |
| iOS | Migrate `SearchView` to Hi-Fi v2 primitives | claude-code | 3 |
| iOS | Verify outside-universe search row UX still works after migration | Sansar | 1 |

**Hours.** ~9.

### Day 13 (Sun) — Ticker Detail + Methodology migration

| Lane | Task | Owner | Hours |
|---|---|---|---|
| iOS | Migrate `TickerDetailView` hero + dimension row to Hi-Fi v2 primitives | claude-code | 5 |
| iOS | Migrate `MethodologyDrawerSheet` and the 5 audit screens (`FinancialHealthAuditView`, `NewsSentimentAuditView`, `MacroExposureAuditView`, `SectorExposureAuditView`, `VolatilityAuditView`) | claude-code | 4 |
| Verify | Walk every methodology drill-down | Sansar | 1 |

**Hours.** ~10.

### Day 14 (Mon) — App Store metadata + press kit + StoreKit kickoff

| Lane | Task | Owner | Hours |
|---|---|---|---|
| 🔴 StoreKit | **App Store Connect: create In-App Purchase products.** Auto-renewable subscription group "Clavix Pro"; product `clavix_pro_monthly` ($19.99 → net $20 after Apple's 30%/15% take). Configure 14-day Introductory Offer (free trial). Localized title/description/promotional image. | Sansar | 2 |
| Marketing | Draft App Store metadata: title (`Clavix`), subtitle (`Portfolio risk, measured.` 30 char), promotional text (170 char), description (4000 char — adapt from getclavix.com), keywords (100 char), category (Finance), age rating (17+) | Sansar | 2 |
| Marketing | Process 5 App Store screenshots; design overlay text using brand tokens | Sansar/designer | 3 |
| Marketing | Assemble press kit: icon at 1024×1024, 5 screenshots, 30-s demo video, 200-word about, founder photo, 3-line product summary | Sansar | 3 |
| Marketing | Draft 3-email waitlist drip: (1) "Beta access is coming", (2) "Here's what's behind the rating", (3) "Your invite is live"; queue in Resend | claude-code | 3 |
| Backend | Build `POST /admin/invite` endpoint that creates a TestFlight-ready invite token for a waitlist email and sends the drip | claude-code | 2 |

**Hours.** ~15. Long day.

### Day 15 (Tue) — StoreKit iOS client + server webhook scaffolding

| Lane | Task | Owner | Hours |
|---|---|---|---|
| 🔴 StoreKit | **iOS StoreKit 2 client.** New `Services/StoreKitService.swift`: load products via `Product.products(for: ["clavix_pro_monthly"])`, present `StoreKit.SubscriptionStoreView` or custom `PaywallView` (replace the current "coming soon" stub), observe `Transaction.updates` for refunds/expirations, call backend `POST /webhooks/apple/verify` with signed JWS on purchase | claude-code | 6 |
| 🔴 StoreKit | **Backend webhook scaffold.** New `routes/webhooks/apple.py`. Verify Apple's JWS signature (apple's public key). Parse `transactionInfo`. Write to new `subscription_events(user_id, product_id, transaction_id, event_type, expires_at, raw)` table. Update `user_preferences.subscription_tier` based on event type. Migration for `subscription_events`. | claude-code | 4 |
| Automation | AI UGC v1 cron: `daily_market_summary_post` reads macro/sector snapshots, drafts a 2-tweet thread, writes to `marketing_draft_posts`, posts to Discord/Slack for 1-click approval | claude-code | 3 |
| Marketing | 2 launch blog posts to `/web/blog/`: "Why we built Clavix", "How portfolio risk is rated" | Sansar | 2 |

**Hours.** ~15.

### Day 16 (Wed) — Internal beta on real people

| Lane | Task | Owner | Hours |
|---|---|---|---|
| Beta | Invite 5–10 trusted ICP-matched testers (family/friends only) via TestFlight; ask them to use the app for 24h and report bugs to a single email/Form | Sansar | 1 + async |
| Bug-fix | Triage their bugs; fix trust-impacting bugs same-day | claude-code | 6–8 |
| Verify | Re-walk after each fix | Sansar | 1 |

**Hours.** ~10.

### Day 17 (Thu) — Bug-fix day + final design polish

| Lane | Task | Owner | Hours |
|---|---|---|---|
| iOS | Address Day 16 feedback | claude-code | 6 |
| Polish | Settings + Alerts visual polish | claude-code | 2 |
| Polish | Replace placeholder copy ("Your portfolio briefing is ready.") with copy that's truthful when the backend returns nulls | claude-code | 2 |

**Hours.** ~10.

### Day 18 (Fri) — Pre-launch QA day

| Lane | Task | Owner | Hours |
|---|---|---|---|
| QA | Full pre-launch checklist (see below) | Sansar | 4 |
| QA | Verify Apple Dev account fully provisioned; certificates valid; bundle ID matches; entitlements set (`aps-environment=production`) | Sansar | 1 |
| QA | Upload final TestFlight build; verify processing; install on 2 real devices | Sansar | 3 |
| QA | Confirm: Privacy nutrition label filled out in App Store Connect | Sansar | 1 |
| QA | Confirm: in-app purchases (Pro) shows the right placeholder for closed beta (no money charged) | Sansar | 1 |

**Hours.** ~10.

### Day 19 (Sat) — Invite the waitlist

| Lane | Task | Owner | Hours |
|---|---|---|---|
| Marketing | Send waitlist drip email 3 to a first batch of 20–30 testers; monitor signups | Sansar | 1 + async |
| Bug-fix | Live triage of any P0 bugs surfaced | claude-code | 6–8 |
| Analytics | Watch PostHog for crash rate, onboarding-completion rate, methodology-drill-down rate | Sansar | 2 |

**Hours.** ~10.

### Day 20 (Sun) — Slack day / expand invites

| Lane | Task | Owner | Hours |
|---|---|---|---|
| Marketing | If Day 19 is green, send drip 3 to next 50 testers | Sansar | 1 |
| Bug-fix | Continue | claude-code | 4–6 |
| Marketing | Draft Product Hunt launch post (queued for post-21-day public launch) | Sansar | 2 |

**Hours.** ~8.

### Day 21 (Mon) — Closed TestFlight beta launch day (FREE)

| Lane | Task | Owner | Hours |
|---|---|---|---|
| Launch | Send drip 3 to remaining waitlist (cap at 200 total testers; protect Minimax + Polygon budget). Pro features either fully unlocked for all testers OR gated to test the gating logic — your call (see Day 0 questions). | Sansar | 1 |
| Comms | Post a brief "we're in closed beta" tweet/X thread; **NOT** Product Hunt yet — that's Day 28 launch day | Sansar | 1 |
| Monitor | All-day: PostHog, Sentry, `/admin/job_health`, App Store Connect crash reports, support@ inbox | Sansar | 6–8 |
| Prep | Confirm Days 22–28 (StoreKit live + App Store submission) | Sansar | 1 |

**Hours.** ~10.

### Day 22 (Tue) — StoreKit sandbox end-to-end

| Lane | Task | Owner | Hours |
|---|---|---|---|
| 🔴 StoreKit | **Sandbox purchase test.** Use App Store Connect Sandbox tester accounts. Walk: open app → tap "Upgrade" → buy `clavix_pro_monthly` → verify `subscription_events` row created → verify `subscription_tier` flipped to `pro` → verify Pro features unlock → verify expiry triggers downgrade after sandbox renewal cycle (5 minutes in sandbox = 1 month). | Sansar + claude-code | 5 |
| 🔴 StoreKit | **Refund/cancel test.** Cancel in sandbox; verify `subscription_events` records `DID_CHANGE_RENEWAL_STATUS`; verify tier stays `pro` until expiry then flips to `free`. | claude-code + Sansar | 2 |
| 🔴 StoreKit | **Restore purchases.** "Restore Purchases" button in Settings; calls Apple to refresh entitlement; webhook re-syncs. | claude-code | 2 |
| Monitor | Triage Day 21 beta feedback | Sansar | 3 |

**Hours.** ~12.

### Day 23 (Wed) — StoreKit polish + paywall final design

| Lane | Task | Owner | Hours |
|---|---|---|---|
| 🔴 StoreKit | Final `PaywallView` design: Hi-Fi v2 primitives; clear "$19.99/month after 14-day free trial"; restore button; ToS/Privacy links; subscription terms in fine print (required by Apple guidelines) | claude-code | 5 |
| 🔴 StoreKit | Implement subscription management deeplink (`UIApplication.shared.open(URL(string: "https://apps.apple.com/account/subscriptions")!)`) in Settings | claude-code | 1 |
| 🔴 StoreKit | Beta testers get a "founders" code that grants Pro for 1 year free (manual `subscription_tier` flip via admin route) — for the ~10 most-engaged testers from week 3 | claude-code | 2 |
| Monitor | Continued bug-fix from beta feedback | claude-code | 4 |

**Hours.** ~12.

### Day 24 (Thu) — App Store submission day

| Lane | Task | Owner | Hours |
|---|---|---|---|
| 🔴 Apple | **Final submission build.** Archive → upload to App Store Connect → submit for review. Reviewer notes (paste in the submission notes): "Sandbox test credentials below. Subscription is Auto-Renewable. We do not provide investment advice — see Terms at getclavix.com/terms and in-app first-run disclaimer." Provide a sandbox tester account in reviewer notes. | Sansar | 3 |
| 🔴 Apple | Privacy nutrition labels (App Store Connect → App Privacy): declare Email, Payment Info (handled by Apple), Crash Data (Sentry), Product Interaction (PostHog). No tracking. | Sansar | 1 |
| Monitor | Beta feedback triage | Sansar | 3 |
| Buffer | Any leftover Day 22–23 polish | claude-code | 3 |

**Hours.** ~10.
**Risks.** Finance app reviewers can take 1–5 days. If rejected on Day 26–27, fix and resubmit (each resub = ~24h review).

### Day 25–27 (Fri–Sun) — Review wait + final polish + press warm-up

| Day | Focus |
|---|---|
| 25 (Fri) | Monitor review status; if approved (24h is best case), schedule release for Day 28 AM. Press kit final polish. Product Hunt launch post drafted + scheduled. Hacker News "Show HN: Clavix" post drafted. Twitter/X launch thread drafted. |
| 26 (Sat) | If still in review, continued bug-fix from beta. Outreach: email 5 finance Substack writers with press kit + early access offer. |
| 27 (Sun) | Final pre-launch sanity walkthrough. Press scheduling: Product Hunt goes live 00:01 PT Day 28; Hacker News post manually at 8am ET. |

**Hours each day.** 4–8 depending on approval status.

### Day 28 (Mon) — App Store public launch with payments live

| Lane | Task | Owner | Hours |
|---|---|---|---|
| 🚀 Launch | App goes live on App Store with `clavix_pro_monthly` $19.99 + 14-day trial enabled | Sansar | 1 |
| 🚀 Launch | Product Hunt post live; Hacker News post live; Twitter/X thread posted | Sansar | 2 |
| Comms | Re-engage closed-beta cohort with "We're live" email; thank-you note | claude-code | 1 |
| Monitor | All-day: Sentry, PostHog, App Store reviews, support inbox, StoreKit purchases | Sansar | 6–8 |

**Hours.** ~12. Launch day.

---

## Workstreams (parallelisable)

Compressed view of the 8 lanes. Lets you reassign load if any lane stalls.

### Data / Backend
- Day 1: `subscription_tier` lockdown.
- Day 2: `/admin/job_health` + backfill_14d.
- Day 3: Digest grade reconciliation.
- Day 5: Pre-existing test fix; smoke tests; cron health alarm.
- Day 6: CORS tightening; PostHog event taxonomy.
- Day 14: `/admin/invite` endpoint.
- Day 15: AI UGC cron scaffold.

### iOS / Frontend
- Day 1: Info.plist fixes.
- Day 2: Sentry-Cocoa, freshness labels.
- Day 3: First-run disclaimer.
- Day 4: Outside-universe path, Alerts v2 model.
- Day 6: Settings + Onboarding to Hi-Fi v2.
- Days 11–13: Today/Holdings/Search/Ticker/Methodology to Hi-Fi v2.
- Days 8–9, 16–17: bug-fix.

### Website / Waitlist
- Day 1: Legal pages + Plausible.
- Day 14: Press kit + screenshots + email drip.
- Day 15: 2 blog posts.

### Legal / Security
- Day 1: Apple Dev + Andover entity + Privacy/Terms draft + lawyer outreach.
- Day 3: First-run disclaimer + `user_legal_acks` table.
- Day 9: Lawyer call + implement feedback.
- Day 18: Final legal review.

### Integrations
- Day 1: Plausible.
- Day 2: Sentry-Cocoa.
- Day 3: Resend email.
- Day 4: APNs key deployment.
- Day 6: PostHog.

### Testing / QA
- Day 5: Smoke tests; pre-existing test fix; RLS audit.
- Day 7: Internal alpha walkthrough.
- Day 16: Internal beta walkthrough.
- Day 18: Pre-launch QA day.

### Brand / Marketing
- Day 5: Sim screenshots draft.
- Day 11: Demo video.
- Day 14: App Store metadata + press kit + email drip.
- Day 15: Blog posts.
- Day 20–21: Launch posts.

### AI UGC / Company OS
- Day 15: AI UGC v1 cron scaffold.
- Days 22+: Daily report cron + bug-intake email→GH issues + autonomous engineering loop (post-launch).

---

## Parallelization Plan

What Claude Code can do without your hands-on involvement (you review the PR, you decide whether to merge):

**Days 1–7 (Apple Dev wait):**
- Privacy/Terms/Refund/Methodology pages.
- Job-health admin route + tests.
- Grade reconciliation between Digest and Holdings.
- First-run disclaimer screen + `user_legal_acks` migration + route + iOS view.
- Resend transactional email integration.
- Smoke tests in deploy workflow.
- Sentry-Cocoa integration.
- PostHog integration.
- `subscription_tier` lockdown.
- All `armv7→arm64` + `clavix://` Info.plist fixes.
- 30-min job-health alarm cron.
- Outside-universe iOS UI path.
- Alert model v2 update.

**Days 7–14:**
- Sim screenshots; press kit assembly.
- App Store metadata draft.
- Hi-Fi v2 design system migrations (one screen per session — Onboarding, Settings, Today, Holdings, Search, TickerDetail, Methodology).
- AI UGC scaffold.

**Days 14–21:**
- Bug-fix triage from internal alpha/beta.
- Polish copy.
- Final docs (CHANGELOG, RUNBOOK).

**What only you can do:**
- Apple Dev enrolment and signing.
- Lawyer call.
- Andover entity verification.
- TestFlight upload.
- Beta invites.
- All financial/billing decisions.
- Final merges to `main`.

---

## Automation Roadmap

Phased plan to make Clavix more autonomous over the next 6–12 weeks.

### Phase 1 (Days 1–21) — Manual command center

You're the orchestrator. Daily routine: open audit checklist, review Sentry, review PostHog, review `/admin/job_health`, queue 1–3 tasks for Claude Code.

### Phase 2 (Weeks 4–6, post-launch) — GitHub issue/PR automation

- Bug reports from users → email forwarder → Claude Code drafts a GH issue with labels.
- Sentry errors above threshold → auto-create GH issues.
- Claude Code picks up `priority:P1` unassigned issues, opens PRs.
- PRs run CI + smoke tests; auto-tagged ready-for-review on green.
- Manual merge approval.

### Phase 3 (Weeks 6–8) — Monitoring + daily report

- `daily_orchestrator_report` cron at 8:00 ET runs every morning: queries `job_runs`, Sentry, PostHog, App Store Connect, Stripe; produces a 250-word "yesterday at Clavix" report; emails you.
- Cost reporter weekly: API spend rollup.
- KPI reporter weekly: signups, activation, retention, drill-down rate.

### Phase 4 (Weeks 8–12) — AI UGC / content engine

- AI UGC daily tweet thread on macro/sector moves; queued for 1-click approval.
- Blog post drafter: every 2 weeks, drafts a post from the week's interesting risk events.
- Email engagement automation: re-engage churned users with personalised insights drawn from their old portfolio.

### Phase 5 (Months 4–6) — Semi-autonomous product/engineering loop

- Backlog scanner: ingests `backlog.md` + user feedback + Sentry priorities; suggests next sprint.
- Spec drafter: writes implementation specs for issues, reviewed by you.
- Engineer agent: implements specs into PRs.
- Reviewer agent: catches obvious quality issues before you review.

### Phase 6 (Months 6–12) — Autonomous company system

- Daily standup report assembling status from every department.
- Cost-watch agent: triggers spend reviews if any line item exceeds budget.
- Security-watch agent: scans for new dependency CVEs, leaked tokens, RLS regressions.
- Growth experiment scheduler: drafts and queues A/B tests on the marketing site.

**Hard safety rule (reinforced).** Across all phases: AI can detect, draft, test, and open PRs. AI **does not** merge to main, deploy to prod, modify secrets, change billing/auth/security, auto-post marketing without approval, or alter financial scoring formulas without approval.

---

## Daily Operating Routine

**Morning (08:00 ET, 15 minutes).**
- Open `/admin/job_health`. Confirm all tier-1 jobs `status=completed` for yesterday.
- Open Sentry. Look at top 5 errors in the last 24h.
- Open PostHog. Look at yesterday's signups + onboarding completion rate.
- Open the daily orchestrator email (Phase 3+).
- Queue 1–3 tasks for Claude Code.

**Midday (13:00 ET, 10 minutes).**
- Verify intraday price polls are running (`job_runs` for `intraday_price_refresh_held`).
- Review any new GH issues filed by users/support.
- Check `/health` from outside the network.

**Night (21:00 ET, 15 minutes).**
- Review what shipped today (commits, deploys).
- Check tomorrow's planned work (the next day of this plan).
- Sentry one more time.
- Spot-check 1 random user's data integrity in Supabase (if there are real users).

---

## Final Pre-Launch Checklist

Run through this **the morning of Day 21**.

**Legal**
- [ ] Privacy live at https://getclavix.com/privacy
- [ ] Terms live at https://getclavix.com/terms
- [ ] Refund live at https://getclavix.com/refund
- [ ] Methodology live at https://getclavix.com/methodology
- [ ] In-app first-run disclaimer ships
- [ ] `user_legal_acks` table populates on accept
- [ ] Lawyer call done; lawyer feedback implemented

**Apple / iOS**
- [ ] Apple Developer Program active
- [ ] App Store Connect record created
- [ ] Bundle ID `com.clavisdev.portfolioassistant` registered
- [ ] APNs `.p8` deployed; `/health` says `"apns":"configured"`
- [ ] Distribution cert + prov profile valid
- [ ] Latest TestFlight build processed
- [ ] App icon at 1024×1024 reviewed
- [ ] 5 App Store screenshots saved
- [ ] App Store metadata drafted and entered

**Backend / Data**
- [ ] All tier-1 jobs `status=completed` for the last 7 days
- [ ] `backfill_14d` evidence in `job_runs`
- [ ] Sentry DSN set and firing
- [ ] CORS allowlist no longer includes `localhost`
- [ ] Admin password rotated; admin session secret regenerated
- [ ] Smoke tests in `deploy-prod.yml`
- [ ] 30-min job-health alarm functional
- [ ] Backups confirmed (Supabase PITR)

**Trust**
- [ ] Digest and Holdings show identical composite grade for the same portfolio
- [ ] Freshness labels visible on Today/Holdings/Ticker
- [ ] First push notification says "Clavix" (not "Clavynx")
- [ ] Score history sparkline shows real points

**Security**
- [ ] `subscription_tier` not writable via `/preferences`
- [ ] RLS verified on every user-data table
- [ ] No secrets in repo
- [ ] APNs `.p8` excluded from rsync

**iOS UX**
- [ ] `armv7` removed, `arm64` present
- [ ] `clavix://` URL scheme registered
- [ ] Outside-universe degraded-mode path works
- [ ] Alerts unread badge honest

**Marketing**
- [ ] Press kit assembled
- [ ] Demo video recorded
- [ ] 2 launch blog posts published
- [ ] Email drip queued in Resend
- [ ] Plausible (or PostHog) firing on website

**Pipeline**
- [ ] One real test push delivered to your phone via APNs
- [ ] One real digest delivered for a real user (you) on the morning of Day 21

---

## Post-Launch Week 1 Plan (Days 29–35)

After Day 28 App Store public launch with payments. Goal: **don't break trust**; **convert beta cohort to paying**; **start growth flywheel**.

| Day | Focus | Tasks |
|---|---|---|
| 29 (Tue) | Triage | Read every Sentry error; review every App Store review; review every PostHog onboarding-to-trial-start funnel |
| 30 (Wed) | Conversion analysis | Of the 100+ beta testers, who converted to trial? Why didn't the others? Email the non-converters with a personalised "what would make Clavix valuable to you?" survey |
| 31 (Thu) | Bug-fix + content | All P0/P1 production bugs surfaced in first 72h. Publish a 3rd blog post on a sector/macro insight pulled from this week's snapshots |
| 32 (Fri) | First-week retention | Cohort analysis: Day-1 / Day-3 / Day-7 morning-report-open rate. If <50% D3, the digest isn't compelling — that's a major signal |
| 33 (Sat) | Annual plan? | If conversion rate is healthy (>5% of installs to trial-start), consider shipping annual ($199/yr) earlier than v1.5 planned |
| 34 (Sun) | Slack | Real rest day if possible |
| 35 (Mon) | Week-2 plan | Plan Week 5+ priorities based on actual usage data, not assumptions |

**Monitoring during week 1.**
- Hourly: Sentry top errors.
- 4×/day: `/admin/job_health`.
- Daily: PostHog onboarding-completion rate; methodology-drill-down rate; alert-tap rate.
- Daily: API spend (Minimax, Polygon, Finnhub).
- Weekly: cohort retention; D1, D3, D7.

**Trip-wires (auto-pause invites if any triggers).**
- Sentry error rate > 5% of sessions.
- Onboarding completion rate < 60%.
- Any tier-1 job failure 2 days in a row.
- Minimax daily spend > 2× budget.
- A user-reported security issue.

---

## Top 10 First Actions

These are the exact first 10 things to do, in order, starting now (tonight Day 0 → tomorrow Day 1 morning).

1. **SSH into the VPS RIGHT NOW.** `tail -200 /var/log/clavix/cron.log` + query `job_runs`. Confirm `daily_macro_snapshot`, `daily_sector_snapshot`, `daily_composite_recompute_universe` are all firing. If any aren't, debug now — every day they aren't firing is a day of stale data shipping to beta testers. (15 min.)
2. **In the same SSH session, kick off `backfill_14d` in tmux.** `tmux new -s backfill 'docker exec clavis-backend-1 python -m app.jobs.run backfill_14d > /tmp/backfill_14d.log 2>&1'`. Walk away; comes back tomorrow with score history populated. (5 min active.)
3. **Search for EIN.** Gmail/Outlook for "EIN", "147C", "Andover Digital", "Internal Revenue Service"; `~/Documents` for LLC formation PDF; Stripe Atlas dashboard if used. **1h cap.** If not found by then, schedule IRS call tomorrow morning. (1h.)
4. **Start Apple Developer Program enrolment.** `developer.apple.com/programs/enroll` → Organization → Andover Digital LLC → pay $99. If D-U-N-S Number is missing, the form will offer to start the free Dun & Bradstreet lookup — do it. (45 min + 24-48h passive wait.)
5. **Apply to Mercury.** mercury.com → LLC application → EIN (Day 1 if not retrieved Day 0) → submit. (30 min + 24-48h wait.)
6. **Email 3 securities lawyers** asking for a 1h call this week. Targets: Cooley fintech, Wilson Sonsini, a fintech-focused solo on Lawtrades or Upwork (search "securities lawyer SEC fintech disclaimer"). Budget $500-1500 for the call. Goal: review marketing claims + in-app letter-grade language + registration-risk assessment. (30 min.)
7. **Open a Claude Code session and queue these 4 PRs to land Day 1:** (a) draft Privacy/Terms/Refund/Methodology HTML pages under `/web/` from Stripe Atlas + Termly templates and re-route footer; (b) lock `subscription_tier` writes server-side in `routes/preferences.py`; (c) fix `apns.py:75` `"Clavynx Update"` → `"Clavix"`; (d) Info.plist `armv7` → `arm64` and add `clavix://` to `CFBundleURLSchemes`. Add Plausible to `web/index.html`.
8. **Build `/admin/job_health` endpoint.** Replaces needing to SSH for daily cron health checks. Queue this as a Claude Code task; review the PR.
9. **Archive `backlog.md`** as `backlog_visualqa_2026-05-25.md`. Create a new `backlog.md` framed as "Road to Launch — open P0/P1 items" populated from `roadtolaunch_audit.md §P0/P1`.
10. **Set a calendar alarm for 7:00am ET tomorrow** — IRS Business & Specialty line opens then if you need the 147C call. Also set a follow-up alarm for 48h to check Apple Dev + Mercury approval status.

Done — by end of Day 0 you've started three 24-48h async clocks (Apple Dev, Mercury, EIN), kicked off the never-run `backfill_14d`, verified the scheduler is actually firing in prod, and queued 5 same-day PRs to land Day 1.
