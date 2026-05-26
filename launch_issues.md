# Launch Issues

Execution-ready issue list for the 21-day TestFlight push. Priorities are about launch sequencing, not code elegance.

## 1. Enroll Andover Digital LLC in Apple Developer Program

- **Priority:** P0
- **Area:** Apple / Operations
- **Why it matters:** Blocks TestFlight, APNs key generation, App Store Connect, and StoreKit setup.
- **Files likely involved:** none in repo; later `ios/project.yml`, signing settings, App Store Connect metadata
- **Acceptance criteria:** Organization enrollment submitted; D-U-N-S issue resolved if required; account approved; App Store Connect accessible.
- **Test plan:** Confirm organization account can create the `Clavix` app record and generate APNs credentials.
- **Dependencies:** LLC standing, Apple ID, D-U-N-S if Apple requires it
- **Estimated effort:** 2-8 hours active; 1-5 days wall-clock
- **Can Codex implement?:** no
- **Needs Sansar action?:** yes

## 2. Recover EIN and open Mercury business account

- **Priority:** P0
- **Area:** Finance / Operations
- **Why it matters:** Needed for Mercury, and likely needed for paid agreements/tax/banking setup around App Store payments.
- **Files likely involved:** none in repo
- **Acceptance criteria:** EIN recovered or IRS fallback completed; Mercury application submitted; account status tracked.
- **Test plan:** Mercury application accepted or pending with no missing-information blocker.
- **Dependencies:** LLC info, EIN, identity docs
- **Estimated effort:** 1-4 hours active; 1-3 days wall-clock
- **Can Codex implement?:** no
- **Needs Sansar action?:** yes

## 3. Document the real website source of truth for legal pages

- **Priority:** P0
- **Area:** Website / Trust
- **Why it matters:** Live legal pages now return `200`, but this repo does not contain their source. That is a change-control risk.
- **Files likely involved:** `web/index.html`, separate website repo or deployment docs if one exists
- **Acceptance criteria:** Either the legal page source is added to version control here, or this repo clearly documents the external website repo/deployment path.
- **Test plan:** Verify repo path or documented external repo is enough to reproduce `/privacy`, `/terms`, `/refund`, and `/methodology`.
- **Dependencies:** Access to the actual website source/deployment
- **Estimated effort:** 1-3 hours
- **Can Codex implement?:** yes, if the source lives here or you point me to the real site repo
- **Needs Sansar action?:** yes

## 4. Align website waitlist/payment copy with actual beta scope

- **Priority:** P0
- **Area:** Website / Product honesty
- **Why it matters:** `web/index.html` still promises a 14-day Pro trial and paid plan even though no StoreKit flow exists in repo.
- **Files likely involved:** `web/index.html`
- **Acceptance criteria:** Closed-beta site copy matches reality for Plan A or Plan B; no beta user is misled about what works today.
- **Test plan:** Manually review hero, FAQ, footer, and waitlist sections against chosen plan.
- **Dependencies:** Plan A vs Plan B decision
- **Estimated effort:** 1-2 hours
- **Can Codex implement?:** yes
- **Needs Sansar action?:** yes

## 5. Add live legal/disclaimer coverage to the app beta surface

- **Priority:** P0
- **Area:** iOS / Legal / Trust
- **Why it matters:** Closed TestFlight still needs privacy basics and clear “informational, not investment advice” framing.
- **Files likely involved:** `ios/Clavis/Views/Settings/SettingsView.swift`, auth/onboarding views, possibly new disclaimer view
- **Acceptance criteria:** Privacy/Terms/Refund/Methodology links work from the app; beta users see a clear disclaimer before relying on portfolio outputs.
- **Test plan:** Fresh install -> login/onboarding -> disclaimer visible -> links open correctly.
- **Dependencies:** Live legal URLs
- **Estimated effort:** 2-6 hours
- **Can Codex implement?:** yes
- **Needs Sansar action?:** yes

## 6. Fix Info.plist URL scheme and device capability issues

- **Priority:** P0
- **Area:** iOS / App Store readiness
- **Why it matters:** The app still only registers `clavis://` and still declares `armv7`.
- **Files likely involved:** `ios/Clavis/Resources/Info.plist`, `ios/Clavis/App/ClavisApp.swift`
- **Acceptance criteria:** `clavix://` and `clavis://` both work; `armv7` removed; app still builds.
- **Test plan:** Build app; open both deep-link schemes in simulator; verify auth/brokerage callback routing.
- **Dependencies:** none
- **Estimated effort:** 1-2 hours
- **Can Codex implement?:** yes
- **Needs Sansar action?:** no

## 7. Fix APNs title typo and deploy APNs credentials

- **Priority:** P0
- **Area:** Backend / Apple
- **Why it matters:** Current fallback push title says `Clavynx Update`, and live `/health` still reports APNs missing.
- **Files likely involved:** `backend/app/services/apns.py`, VPS env/key path, Apple Developer portal
- **Acceptance criteria:** Default title says `Clavix`; backend `/health` reports APNs configured; test push reaches device.
- **Test plan:** Hit health endpoint; register device token; trigger push-test route; confirm notification text on device.
- **Dependencies:** Apple Developer enrollment, APNs key
- **Estimated effort:** 2-4 hours plus Apple access
- **Can Codex implement?:** yes for code; no for portal/VPS secret deployment
- **Needs Sansar action?:** yes

## 8. Verify production scheduler firing with evidence

- **Priority:** P0
- **Area:** Backend / Operations / Trust
- **Why it matters:** Repo wiring exists, but launch trust depends on proof that cron jobs actually run in production.
- **Files likely involved:** `scripts/cron/clavix.crontab`, `.github/workflows/deploy-prod.yml`, `backend/app/jobs/run.py`, `backend/app/services/job_runs.py`
- **Acceptance criteria:** Recent successful `job_runs` rows exist for daily macro, sector, composite, and portfolio-rollup jobs; cron install on VPS confirmed.
- **Test plan:** Query `job_runs`; inspect VPS cron file and logs; save screenshots or SQL output to audit docs.
- **Dependencies:** VPS access, Supabase access
- **Estimated effort:** 2-4 hours
- **Can Codex implement?:** partially; verification needs external access
- **Needs Sansar action?:** yes

## 9. Build an admin job-health endpoint/dashboard

- **Priority:** P1
- **Area:** Backend / Ops tooling
- **Why it matters:** `/admin/api/health` is too shallow. You need scheduler truth without SSH.
- **Files likely involved:** `backend/app/routes/admin.py`, `backend/app/services/job_runs.py`, maybe new helper/service module
- **Acceptance criteria:** Admin API returns per-job last success, last failure, expected cadence, stale state, and recent error summary.
- **Test plan:** Seed fake/stale job rows in tests; verify API marks stale jobs correctly.
- **Dependencies:** `job_runs` table
- **Estimated effort:** 4-8 hours
- **Can Codex implement?:** yes
- **Needs Sansar action?:** no

## 10. Run the 10-ticker news canary and publish the results

- **Priority:** P0
- **Area:** Data pipeline
- **Why it matters:** The news system is one of the freshest/highest-risk parts of the stack and still lacks a published live-fire result.
- **Files likely involved:** `backend/scripts/canary_10_tickers.py`, audit docs
- **Acceptance criteria:** Canary run completed; success metrics, failure reasons, and follow-up actions documented.
- **Test plan:** Run the script in the target environment and compare DB output to its reported counts.
- **Dependencies:** API keys, Supabase, internet access
- **Estimated effort:** 2-4 hours including analysis
- **Can Codex implement?:** yes
- **Needs Sansar action?:** no

## 11. Run and validate the 14-day score-history backfill

- **Priority:** P0
- **Area:** Data pipeline / Trust
- **Why it matters:** Score history and “was X days ago” trust depends on real historical rows, not placeholder deltas.
- **Files likely involved:** `backend/app/jobs/backfill_14d.py`, `backend/app/jobs/composite_recompute.py`, audit docs
- **Acceptance criteria:** `backfill_14d` completes in target environment; representative tickers show populated daily snapshot history.
- **Test plan:** Run the job; query `ticker_risk_snapshots` for AAPL/NVDA/MSFT; compare row counts and dates.
- **Dependencies:** Scheduler/prod access, API keys, snapshot tables
- **Estimated effort:** 1-3 hours active plus runtime
- **Can Codex implement?:** yes
- **Needs Sansar action?:** yes if prod execution is required

## 12. Triage and fix scheduler snapshot-date boundary behavior

- **Priority:** P1
- **Area:** Backend / Testing / Trust
- **Why it matters:** Targeted tests still show a snapshot-date mismatch around `_upsert_ticker_snapshot_from_scores`.
- **Files likely involved:** `backend/app/pipeline/scheduler.py`, `backend/tests/test_scheduler_jobs.py`
- **Acceptance criteria:** Date behavior is explicitly correct and the failing scheduler test is green.
- **Test plan:** Re-run targeted scheduler tests under CI-style env; add a regression test for timezone/date expectations if needed.
- **Dependencies:** none
- **Estimated effort:** 1-4 hours
- **Can Codex implement?:** yes
- **Needs Sansar action?:** no

## 13. Define the beta entitlement model

- **Priority:** P0
- **Area:** Product / Payments / Security
- **Why it matters:** Server-side gates still trust `subscription_tier`, but there is no real purchase path. Beta needs a deliberate entitlement story.
- **Files likely involved:** `backend/app/routes/tickers.py`, `backend/app/services/access_control.py`, future subscription endpoint docs
- **Acceptance criteria:** Written decision on whether closed-beta Pro access is sandbox-verified, tester-allowlisted, or deferred under Plan B.
- **Test plan:** Walk through each Pro-gated feature and confirm how it unlocks in beta.
- **Dependencies:** Plan A vs Plan B decision
- **Estimated effort:** 1-2 hours
- **Can Codex implement?:** partially
- **Needs Sansar action?:** yes

## 14. Implement StoreKit 2 sandbox payments

- **Priority:** P0 for Plan A, P1 for Plan B
- **Area:** iOS / Payments
- **Why it matters:** There is currently no real purchase/restore/manage flow in the app.
- **Files likely involved:** new StoreKit client/service, upgrade sheet replacements in `ios/Clavis/Views/*`, maybe auth/settings models
- **Acceptance criteria:** Products load; purchase works in sandbox; restore works; manage-subscription path works; UI no longer says `Pro is coming soon`.
- **Test plan:** TestFlight sandbox on real devices with at least two tester accounts.
- **Dependencies:** Apple Developer, App Store Connect products, plan decision
- **Estimated effort:** 2-5 days
- **Can Codex implement?:** yes
- **Needs Sansar action?:** yes

## 15. Set up App Store Connect subscription products and paid agreements

- **Priority:** P0 for Plan A, P1 for Plan B
- **Area:** Apple / Payments / Operations
- **Why it matters:** StoreKit code is useless without actual products, agreements, and the right org/account setup.
- **Files likely involved:** none in repo; product IDs should be documented back into launch docs
- **Acceptance criteria:** Subscription products exist; pricing/trial config matches launch plan; tax/banking agreements are not blocking sandbox testing.
- **Test plan:** Products appear in sandbox product fetch and can be purchased in TestFlight.
- **Dependencies:** Apple Developer enrollment, EIN, banking/tax
- **Estimated effort:** 2-8 hours active; 1-5 days wall-clock depending on Apple
- **Can Codex implement?:** no
- **Needs Sansar action?:** yes

## 16. Build a TestFlight-ready signing and release path

- **Priority:** P0
- **Area:** iOS / Release
- **Why it matters:** A locally building app is not the same as a distributable TestFlight build.
- **Files likely involved:** `ios/project.yml`, Xcode signing settings, App Store Connect metadata
- **Acceptance criteria:** Archive succeeds; build uploads to TestFlight; internal testers can install it.
- **Test plan:** Upload a build, wait for processing, install via TestFlight, complete core user flow.
- **Dependencies:** Apple Developer enrollment, app record
- **Estimated effort:** 1-2 days including signing friction
- **Can Codex implement?:** partially
- **Needs Sansar action?:** yes

## 17. Prepare App Store metadata, screenshots, and privacy disclosures

- **Priority:** P1
- **Area:** Launch packaging
- **Why it matters:** Even for closed beta prep, these assets become the bottleneck late if you ignore them.
- **Files likely involved:** screenshot exports, marketing assets, support/legal URLs, maybe docs
- **Acceptance criteria:** Description, subtitle, keywords, screenshots, support URL, privacy URL, and privacy disclosure answers are drafted.
- **Test plan:** Review in App Store Connect and cross-check copy against actual beta functionality.
- **Dependencies:** live legal pages, stable app flows
- **Estimated effort:** 1-2 days
- **Can Codex implement?:** partially
- **Needs Sansar action?:** yes

## 18. Final closed-beta launch QA and approval gate

- **Priority:** P0
- **Area:** QA / Release management
- **Why it matters:** The app should not reach trusted testers until data freshness, legal truth, and critical flows are explicitly approved.
- **Files likely involved:** `roadtolaunch.md`, `roadtolaunch_audit.md`, QA notes, possibly bugfix files
- **Acceptance criteria:** Written go/no-go review completed; all P0 gates either pass or are explicitly deferred and approved.
- **Test plan:** Full walkthrough on real device plus backend/live checks; signed-off checklist stored in repo docs.
- **Dependencies:** All prior P0 items
- **Estimated effort:** 4-8 hours
- **Can Codex implement?:** yes, for the checklist and many fixes
- **Needs Sansar action?:** yes
