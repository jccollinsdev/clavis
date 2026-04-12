# Clavis — Ultimate Final Build Plan

**Last updated:** 2026-04-12

**Goal:** Take Clavis from working MVP to a marketable, defensible, App Store-ready v1.

**Core positioning:** Clavis is a **portfolio risk data platform**, not an investment adviser, broker, or trading app. The product must describe what is happening in a portfolio, not tell the user what to do.

---

## 0. Launch Principles

### Bloomberg Terminal Defense

Before any copy, feature, or screen ships, apply this test:

> Is this telling the user something that is true right now, or is it telling them what to do?

If it tells the user what to do, rewrite it.

### Product Rules

- No `Buy`, `Sell`, `Exit`, `Reduce`, `Add`, `Hold`, or equivalent action signals.
- No `What To Do` sections.
- Scores and grades are presented as informational model outputs only.
- Every score view must include a short disclaimer.
- Onboarding must require an explicit risk acknowledgment before the first score is shown.
- Legal docs, App Store metadata, and in-app disclosures must all say the same thing.

---

## 1. Gate 0 — Business, Accounts, and External Approvals

These happen before or immediately at the start of the build. Several later phases are blocked on them.

### Apple / Revenue

- Paid Apple Developer account active (`$99/year`)
- App Store Connect app created
- Bundle ID reserved and locked
- Apple tax forms completed
- Apple banking info completed
- RevenueCat account created
- RevenueCat tax and payout forms completed

### Company / Finance

- Business entity formed (`LLC` or equivalent)
- Business bank account opened
- EIN obtained if applicable
- Basic accounting system chosen (`Wave`, spreadsheet, or equivalent)

### Domain / Email

- `support@getclavix.com` mailbox exists and is monitored
- Transactional email provider chosen (`Resend`, `Postmark`, or `SendGrid`)
- SPF configured
- DKIM configured
- DMARC configured

### SnapTrade

- SnapTrade developer account application submitted on Day 1
- SnapTrade approval process started early
- SnapTrade terms reviewed
- SnapTrade privacy policy requirements reviewed

### Legal

- Fintech / securities attorney consultation scheduled or completed
- Decision documented: Clavis stays in the information/data lane, not advice
- Third-party processor agreements reviewed or tracked:
  - Supabase
  - SnapTrade
  - MiniMax
  - Polygon

---

## 2. Phase 1 — Security, Legal Reframing, and Critical Product Bugs

This is the true first build phase. Nothing user-facing that increases exposure should ship before this is done.

### Security Foundation

1. **JWT verification**
   - Replace current shared-secret style verification with proper Supabase JWT verification
   - Verify signatures cryptographically via JWKS / correct signing config
   - Fail closed on invalid tokens

2. **Supabase RLS audit and hardening**
   - Verify RLS on every table
   - Confirm `prices` table intentionally uses a broad read policy
   - Test with an adversarial second user token
   - Confirm no cross-user reads are possible

3. **Environment audit**
   - Remove placeholders and dev-only values from production config
   - Verify no secrets are hardcoded in app binaries or repo-tracked files
   - Separate production vs staging environment config

4. **HTTPS-only posture**
   - No HTTP fallback anywhere
   - Verify production backend, callbacks, and support URLs are HTTPS

### Legal/Product Reframing

1. Remove all advisory/action language from iOS and backend output
2. Replace action-oriented labels with observational labels
3. Replace `portfolio advice` style digest sections with `what changed` or `risk summary`
4. Add score disclaimer text anywhere a grade/score is displayed
5. Add visible data freshness timestamps to scores and digest content
6. Add limited-data state when evidence is weak or missing

### Critical Bug Fixes

1. Holdings pull-to-refresh `Cancelled` error
2. Digest refresh false failure state
3. Position chart reliability and chart data correctness
4. Missing `/preferences/alerts` endpoint
5. Persist missing preferences fields (`summary_length`, `weekday_only`, and alert prefs if applicable)
6. Offline and no-network handling for core screens

### Notification Reliability Foundation

1. Confirm production APNs configuration, not just sandbox
2. Add token refresh handling
3. Respect notification opt-out / invalid token cleanup

---

## 3. Phase 2 — Legal Documents, Onboarding, and Public Trust Surface

### Legal Documents

Publish real public URLs, accessible without login:

- `/privacy`
- `/terms`
- `/refund`
- `/methodology`

### Privacy Policy Must Cover

- What data is collected
  - name
  - email
  - DOB
  - holdings
  - brokerage connection tokens / metadata
  - device info and notification token
- How data is used
  - risk analysis
  - digest generation
  - notifications
  - subscription management
- Third parties
  - Supabase
  - SnapTrade
  - MiniMax
  - Polygon
  - Apple
- Data retention
- Deletion rights
- Export rights
- Contact information
- Last updated date

### Terms Must Cover

- Service description as a data product
- Prominent not-financial-advice disclaimer
- Subscription terms
- Trial terms
- Cancellation policy
- Refund policy link or language
- Limitation of liability
- Governing law
- Last updated date

### Refund Policy

- Explicit policy published publicly
- Matches App Store and support responses

### Methodology Page

- Data sources
- Five risk dimensions
- What the model measures
- What the model does not measure
- Explicit note that outputs are informational model results, not recommendations

### Onboarding

Build a full onboarding flow with:

1. Welcome / value proposition
2. Account creation / sign in
3. Name and DOB collection
4. Risk acknowledgment screen
5. Notification permission request
6. First position flow

### Risk Acknowledgment Requirement

Before the user sees any score:

- Show full acknowledgment copy
- Require explicit acceptance
- Log version + timestamp in database

---

## 4. Phase 3 — Website, Email Infrastructure, and App Store Trust Prep

### Website Fixes

The marketing site must be cleaned up before submission.

1. Mobile optimization
2. Real privacy and terms links, not `#`
3. Risk disclaimer visible in footer at minimum
4. Support/contact page or support email visible
5. Fix or remove `Join 2+ investors`
6. OG tags and social preview image
7. Favicon across required sizes
8. Basic SEO
   - title tag
   - meta description
9. Cookie consent banner if analytics are installed

### Email Infrastructure

Required transactional flows:

1. Waitlist confirmation
2. Welcome email on signup
3. Trial ending reminder
4. Payment failed notification
5. Account deletion confirmation

Required setup:

- transactional provider configured
- SPF / DKIM / DMARC valid
- email templates created
- support inbox monitored

### App Store Connect Baseline Setup

This must be ready before subscription product setup.

1. App name finalized
2. Subtitle finalized
3. Keywords drafted
4. Description drafted
5. Copyright entered: `© 2026 Clavix`
6. Primary category: `Finance`
7. Secondary category decided if needed
8. Age rating questionnaire completed
9. iPad support decision made
10. Minimum iOS version decided

---

## 5. Phase 4 — Payments, RevenueCat, and Subscription Enforcement

**Prerequisite:** Apple Developer account, App Store Connect app, bundle ID, tax/banking, and products must already be set up.

### App Store / RevenueCat Setup

1. Create subscription product(s) in App Store Connect
2. Configure RevenueCat entitlements
3. Integrate StoreKit 2 + RevenueCat SDK in iOS app
4. Add backend webhook endpoint for subscription state updates
5. Add restore purchases flow

### Commercial Model

#### Free

- 3 positions max
- Simulated positions count toward the 3-position limit
- No live brokerage sync after trial ends

#### Plus

- `$15/month`
- Real-time brokerage syncing via SnapTrade
- Higher-value premium features as finalized

### Trial

- 1 month free for all new users
- Trial countdown visible in app
- Trial ending emails sent
- Downgrade behavior after expiry is explicit and tested

### Enforcement

- Backend hard-enforces position limits
- UI reflects plan limits
- Subscription restore supported
- Subscription management link present in app

---

## 6. Phase 5 — SnapTrade and Portfolio Connection

### Start Early

SnapTrade account application starts in Phase 1, even though implementation lands here.

### Implementation

1. Backend endpoints for user registration and connection flow
2. OAuth / redirect or hosted connect flow support
3. Callback handling and URL scheme registration
4. Brokerage account sync into holdings model
5. Disconnect and resync flows

### Constraints

- Review SnapTrade terms and privacy requirements before shipping
- Do not depend on App Review creating their own brokerage connection
- Provide demo/testing instructions for Apple reviewers using a seeded account instead

---

## 7. Phase 6 — App UX, Simulated Risk, and Profile Experience

### Navigation / Information Architecture

1. Remove Settings from bottom nav if desired
2. Replace hamburger content with account/profile oriented surface
3. Add profile screen
   - name
   - DOB
   - plan status
   - brokerages
   - manage subscription
   - support / feedback

### Holdings Improvements

1. Search bar on holdings
2. Stock lookup before adding
3. `Simulate Risk` flow before entering a real position
4. Simulated positions displayed clearly as simulated
5. Search + sort + filter improvements

### Additional UX Work

1. Empty states on every screen
2. Better chart presentation and reliability
3. Dark mode audit
4. Dynamic Type audit
5. Accessibility audit

---

## 8. Phase 7 — Backend Production Readiness

### Operational Readiness

1. Add `/v1` route prefixing strategy or document versioning plan
2. Health check endpoint verified (`GET /health`)
3. Graceful shutdown handling
4. Scheduled job monitoring
5. Structured logging in production
6. Error alerting for backend 500s
7. Crash reporting / backend monitoring
8. Cold-start mitigation if hosting sleeps

### Database / Infra

1. Connection pooling strategy documented
2. Scheduled digest persistence and restart resilience
3. Database backups confirmed
4. Backup restore tested
5. Data retention jobs implemented in code

### Privacy Operations

1. `DELETE /account` endpoint
2. `GET /account/export` endpoint
3. Data deletion flow tested
4. Export format defined and tested

---

## 9. Phase 8 — Notifications and Alert Quality

### Infrastructure

1. Production APNs entitlement enabled
2. Push entitlement verified in release build
3. Backend only sends to valid, current tokens
4. Token updates handled correctly

### Product Quality

1. Alert preference granularity
2. Silent hours respected by default
3. Notification rate limits per position / day
4. Alert history available in app
5. Deep links from push land on the correct screen

---

## 10. Phase 9 — App Store Submission Assets and Metadata

### Required App Store Metadata

- App name
- Subtitle
- Description
- Keywords
- Support URL
- Marketing URL
- Privacy Policy URL
- Copyright
- Age rating
- Export compliance
- Privacy nutrition label
- `What's New` text

### Finance-Specific Review Prep

Provide strong review notes explaining:

- Data sources used
- That the app does not execute trades
- That Clavis is not an RIA and does not provide individualized investment advice
- That outputs are informational model results only
- How demo credentials work

### Review Information

- Demo account provided
- Preloaded holdings in demo account
- Reviewer instructions for key flows
- If SnapTrade is not required for review, say so clearly

### Screenshots / Assets

1. Required screenshot sizes
2. Disclaimer visible in screenshot set
3. App icon complete in all required sizes
4. No placeholder assets or TODO content
5. Launch screen verified
6. App size audited

---

## 11. Phase 10 — Testing Matrix

### Core Functional Testing

1. Fresh install flow
2. Sign up flow
3. Trial flow
4. Trial expiry flow
5. Subscription restore
6. Multiple account sign-in / sign-out test
7. Account deletion flow
8. Account export flow

### Device / OS Testing

1. iOS 16
2. iOS 17
3. Smaller devices / SE class
4. Dark mode
5. Large accessibility font sizes
6. iPhone-only behavior verified if iPad unsupported

### Reliability Testing

1. Airplane mode / offline states
2. Background / low battery behavior
3. Push notification end-to-end
4. SnapTrade connection test with a real account
5. Multiple user isolation test against RLS
6. Crash-response drill

### Beta

- TestFlight external beta with real users before submission

---

## 12. Phase 11 — Launch Operations

### Support / Ops

1. Support inbox monitored daily
2. Auto-responder enabled
3. App Store review response account decided
4. Crash response plan documented
5. Internal escalation path documented

### Growth / Launch

1. Press kit prepared
2. Review prompt strategy implemented
3. Referral / sharing considered
4. Launch announcement plan drafted
   - Product Hunt
   - X / Twitter
   - relevant subreddits
   - Hacker News if appropriate

---

## 13. Immediate Next Actions

Do these first, in this order:

1. Activate paid Apple Developer account
2. Confirm business entity / banking / tax setup path
3. Submit SnapTrade developer application
4. Fix JWT verification properly
5. Audit and test Supabase RLS with adversarial user access
6. Rewrite advisory/action copy in app and backend
7. Fix the four known product bugs
8. Publish legal docs and methodology page

---

## 14. Definition of Launch-Ready

Clavis is launch-ready when all of the following are true:

- Security basics are correct
- User isolation is verified
- Legal docs are public and accurate
- In-app copy does not cross into advice language
- Apple reviewer can test the app with a seeded demo account
- Subscription flows work
- Notifications work in production
- Crash and error monitoring are live
- Website and support surfaces look legitimate
- The app behaves well with no data, no network, expired trial, multiple accounts, and fresh install

If any of those are false, the app is not ready for public launch.
