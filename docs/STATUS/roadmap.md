# Clavis — Current Delivery Roadmap

**Last updated:** 2026-04-16

**Goal:** Take Clavis from a feature-rich prototype and shared-ticker intelligence build into a secure, trustworthy, launch-ready v1.

**Positioning:** Clavis is a portfolio risk data platform for self-directed investors. It describes portfolio risk, change, and evidence. It does not provide personalized investment advice.

---

## 0. Product Rules

These rules apply across every phase.

- No buy/sell/hold style recommendations
- No sections framed as prescriptive advice
- Scores and grades are informational model outputs only
- Every score surface needs disclaimer and freshness context
- Weak evidence should be shown as limited-confidence output, not false certainty
- Public legal copy, App Store copy, backend output, and in-app UX must describe the product the same way

---

## 1. External Gate

These are still hard blockers outside the codebase.

### Apple / Revenue

- Paid Apple Developer account active
- App Store Connect app created
- Bundle ID finalized and reserved
- Tax and banking completed
- RevenueCat account created and configured

### Business / Legal

- Business entity and banking in place
- Fintech / securities counsel review completed or scheduled
- Decision documented: Clavis remains in the informational/data lane

### SnapTrade

- Developer application submitted
- Approval process started
- Terms and privacy requirements reviewed

---

## 2. Phase 1 — Security And Production Hardening

**Status:** In progress

This is the highest-risk open area and must finish before launch.

### What is already done

- Supabase-backed JWT validation via `auth.get_user` is wired in backend middleware
- Broad RLS audit work has been performed and supporting migrations/docs exist
- HTTPS production URL is in use for the app backend
- Health endpoint exists

### What still needs to be done

1. Remove repo-tracked secrets and rotate exposed credentials
2. Remove or strictly gate debug/test/internal production surfaces
3. Replace fail-open route-prefix auth enforcement with safer route protection
4. Lock CORS to explicit origins
5. Reduce overuse of service-role DB access for normal user flows where possible
6. Add monitoring, structured logging, and backend error alerting
7. Confirm database backup and restore procedures
8. Add account deletion and export APIs

### Exit criteria

- No live secrets in repo-tracked files or docs
- No public internal/debug surfaces
- Basic monitoring and recovery posture in place
- Tenant isolation and auth behavior tested with adversarial scenarios

---

## 3. Phase 2 — Shared Ticker Intelligence And Evidence Quality

**Status:** In progress

This is the core product migration currently underway.

### What is already done

- Shared ticker schema foundation exists
- S&P universe seeding exists
- Shared ticker search/detail/refresh routes exist
- Default watchlist routes exist
- Holdings and position views can read from shared ticker intelligence
- S&P backfill and snapshot sync paths exist
- Google News RSS decoding, article resolution, body extraction, and artifact capture have been added
- Google RSS throttling is now configurable with `GOOGLE_NEWS_RSS_DELAY_SECONDS`

### What still needs to be done

1. Finish validating the full shared-cache S&P AI backfill path end to end
2. Keep improving evidence quality so wrapper, recap, and broken pages do not contaminate scoring
3. Tighten article resolver retries, telemetry, and failure reporting
4. Verify ticker detail parity with position detail on real shared-cache runs
5. Finish alert fanout behavior based on shared ticker snapshot changes
6. Confirm digest synthesis is correct when driven by shared ticker intelligence
7. Decide what legacy tables remain operational versus historical-only

### Exit criteria

- Shared ticker intelligence is the reliable canonical source for ticker-level analysis
- Full S&P backfill completes consistently with acceptable evidence quality
- Shared cache outputs are stable enough for daily production use

---

## 4. Phase 3 — Legal Documents And Public Trust Surface

**Status:** In progress

### What is already done

- Onboarding risk framing exists in the app
- Score disclaimers and freshness text exist in score-oriented views
- Methodology content exists in docs and app-facing surfaces

### What still needs to be done

1. Publish real public URLs for:
   - `/privacy`
   - `/terms`
   - `/refund`
   - `/methodology`
2. Ensure privacy policy matches real data collection and processors
3. Ensure terms match subscription and trial behavior
4. Add versioned risk-acknowledgment persistence, not just timestamp logging
5. Unify branding, domain, and support/contact references across docs, backend, app, and launch assets

### Exit criteria

- Public legal pages exist and are accurate
- Risk acknowledgment is properly versioned
- Trust surface is consistent everywhere users or reviewers see it

---

## 5. Phase 4 — iOS UX And Core Product Quality

**Status:** In progress

### What is already done

- Auth gate and onboarding routing exist
- Dashboard, holdings, digest, alerts, settings, ticker search, and ticker detail screens exist
- Cached ticker snapshot data is surfaced in holdings and ticker flows

### What still needs to be done

1. Remove duplicated hamburger-style top-level navigation in favor of more native iOS navigation patterns
2. Improve destructive actions and row-level interaction patterns in holdings
3. Complete watchlist UX on iOS
4. Improve onboarding flow control and prevent accidental bypass behavior
5. Improve offline/no-network states and degraded read-only behavior
6. Improve notification deep-link handling
7. Run accessibility, Dynamic Type, and appearance audits
8. Add stronger search/sort/filter UX where still missing

### Exit criteria

- Core app flows feel coherent on iPhone
- Failure states are understandable to users
- The app is usable and credible under normal daily conditions

---

## 6. Phase 5 — Notifications And User Preference Enforcement

**Status:** In progress

### What is already done

- Device token registration path exists
- Alert preference fields exist in backend and iOS settings models
- Scheduler and alert generation flows exist

### What still needs to be done

1. Finish token lifecycle handling across login, logout, refresh, and invalid token cleanup
2. Enforce quiet hours and alert preference granularity in real send paths
3. Ensure disabling notifications shuts down related scheduled work correctly
4. Complete deep-link routing from push notifications
5. Validate production APNs configuration in release conditions

### Exit criteria

- Notifications are reliable
- User notification preferences are fully respected
- Push taps land in the correct place in the app

---

## 7. Phase 6 — Payments, Entitlements, And Access Control

**Status:** Not started

### Scope

1. RevenueCat and StoreKit 2 integration
2. Free vs paid entitlement model
3. Restore purchases flow
4. Trial state and expiry handling
5. Backend enforcement for gated features and limits
6. Subscription management surface in the app

### Exit criteria

- Users can buy, restore, and manage subscription access
- Free vs paid product rules are enforced consistently in backend and UI

---

## 8. Phase 7 — SnapTrade And Live Portfolio Connections

**Status:** Not started

### Scope

1. User registration and connection endpoints
2. Hosted connect / OAuth flow
3. Callback handling and app deep linking
4. Brokerage sync into holdings
5. Disconnect and resync support

### Exit criteria

- A user can connect, sync, disconnect, and resync a brokerage account safely

---

## 9. Phase 8 — App Store, Operations, And Release Readiness

**Status:** Not started

### App Store / Review Prep

- Metadata, screenshots, icon set, launch assets
- Reviewer notes and seeded/demo-account story
- Support URL, marketing URL, privacy URL, and trust surfaces aligned

### Testing Matrix

- Fresh install and sign-up flows
- Multiple-account isolation testing
- No-network / airplane mode testing
- Notification end-to-end testing
- Trial / subscription / restore testing
- Smaller-device and accessibility testing

### Operations

- Support inbox and response workflow
- Crash-response and escalation plan
- TestFlight / beta feedback cycle

### Exit criteria

- Reviewer can evaluate the app cleanly
- Core user journeys are tested on target devices
- Operational response path exists for launch issues

---

## 10. Immediate Next Actions

Do these next, in order.

1. Finish security hardening around secrets, debug exposure, and route protection
2. Publish real legal/public trust pages and align branding/domain references
3. Validate the shared-cache S&P AI backfill path and remaining evidence-quality gaps
4. Complete iOS watchlist and core navigation/UX cleanup
5. Finish notification lifecycle and preference enforcement
6. Integrate RevenueCat / StoreKit and entitlement enforcement

---

## 11. Definition Of Launch-Ready

Clavis is launch-ready when all of the following are true:

- Security basics are correct and verified
- Shared ticker intelligence is stable and trustworthy enough for daily use
- Legal docs are public and accurate
- In-app copy stays in the informational/data lane
- Notifications work in production and respect user preferences
- Subscription flows work end to end
- Apple review can be completed with a clear demo path
- Monitoring, backup, and operational response are live
- The app behaves well with no data, no network, multiple accounts, and fresh install

If any of those are false, Clavis is not ready for public launch.
