# Terms of Service Audit — V1

**Created:** 2026-06-01
**Audit of:** `https://getclavix.com/terms` (live as of April 12, 2026)
**Status:** Needs parent/lawyer review

---

## A. What the Current Terms Get Right

1. **Operator identification:** Andover Digital LLC named correctly in §1, §19.
2. **No investment advice (§4):** Strong, clear language that Clavix is informational only.
3. **No broker-dealer/adviser claim (§3):** Disclaims those relationships.
4. **User responsibility:** "You are solely responsible for all investment decisions" (§4).
5. **Eligibility (§2):** 18+, US-only, legal capacity.
6. **Account security (§5):** Standard, acceptable.
7. **Acceptable use (§6):** Standard, reasonable restrictions.
8. **Intellectual property (§9):** Properly claims ownership.
9. **Disclaimer of warranties (§11):** Strong "as is" language.
10. **Limitation of liability (§12):** Standard for apps of this type.
11. **Indemnification (§13):** Standard.
12. **Dispute resolution / arbitration (§14):** Standard (AAA, Massachusetts).
13. **Governing law (§15):** Massachusetts.
14. **Termination (§16):** Standard — covers both company and user termination.
15. **Force majeure (§17):** Standard.
16. **Privacy Policy incorporation (§10):** Correct.

---

## B. What Is Overbroad / Future-Only

| Claim | Section | Problem |
|---|---|---|
| "The Service allows you to connect third-party brokerage accounts" | §7 | **FALSE for V1.** Brokerage is disabled. |
| "By connecting a brokerage account, you authorize us to access your account data on a read-only basis" | §7 | FALSE for V1. |
| "Your brokerage credentials are handled via OAuth or read-only API and are never stored by Andover Digital LLC" | §7 | PARTIALLY FALSE — SnapTrade user IDs/secrets ARE stored. Also, brokerage is disabled. |
| "You may revoke brokerage access at any time through the Service" | §7 | FALSE — no brokerage connection UI is available. |
| References to payments/amounts paid (§12) | §12 | **NO payment system exists.** No StoreKit, no IAP, no purchase flow. The liability cap "amount you paid in 12 months" assumes payments exist. |

---

## C. What Is Missing

| Missing Item | Severity | Details |
|---|---|---|
| **App Store distributor disclosure** | **HIGH** | No mention that the App Store seller/developer name may be an individual, not Andover Digital LLC. |
| **Apple App Store terms** | **HIGH** | No reference to Apple's standard EULA / App Store Terms. For apps distributed through the App Store, Apple requires compliance with its standard terms. |
| **AI-generated content disclaimer** | **HIGH** | No disclaimer about AI-generated risk scores, digests, or analysis being potentially inaccurate. |
| **Third-party data provider disclaimer specifics** | **MEDIUM** | §8 is generic. Should specifically name Polygon, Finnhub, and mention that delays/inaccuracies in market data are possible. |
| **Push notification / alert disclaimer** | **MEDIUM** | No disclaimer that alerts/notifications may be delayed, missed, or inaccurate. |
| **No-email communication** | **MEDIUM** | §5 says "notify us immediately at [email]" and §19 provides support email but no email infrastructure exists. |
| **Free/Pro tier description** | **MEDIUM** | No mention of Free vs Pro tiers, limits, or feature differences. |
| **Trial terms** | **MEDIUM** | No mention of 14-day trial, no-credit-card, auto-downgrade. Trial_started_at/ends_at fields exist. |
| **Subscription / IAP terms** | **MEDIUM** | No refund, cancellation, auto-renewal, or billing terms. (But no payment system exists either.) |
| **Data accuracy disclaimer for market data** | **MEDIUM** | §8 is adequate but could be strengthened to mention real-time vs delayed data. |
| **Methodology change notice** | **LOW** | No mechanism to notify users if the risk methodology changes significantly. |

---

## D. What Is Inaccurate / Contradictory

| Issue | Severity | Details |
|---|---|---|
| **Brokerage described as working feature** | **HIGH** | §7 describes a working brokerage connection flow. Brokerage is disabled. |
| **Payment references with no payment system** | **MEDIUM** | §12 references "amount you paid" but no StoreKit/IAP code exists. |
| **Email addresses in contact** | **MEDIUM** | The `[email protected]` in the Terms exists (Cloudflare email protection) but no backend processes emails sent to it. Support is presumably manual. |
| **Termination says "by emailing [email]"** | **MEDIUM** | §16 says terminate by emailing. The app also supports in-app account deletion (DELETE /account). This is actually better but not mentioned. |

---

## E. What Needs Revised Wording

| Section | Change |
|---|---|
| §1 (Acceptance) | Add App Store distributor disclosure sentence. |
| §2 (Eligibility) | Consider adding "no service for on-exchange trading activity." |
| §3 (Description) | Add AI-generated content caveat. Add "manual position entry only" for V1. |
| §4 (No Advice) | Add "AI-generated scores are informational observations." |
| §7 (Brokerage) | **Remove or mark as "Coming in a future update."** |
| §8 (Data Accuracy) | Name specific third-party data sources (Polygon, Finnhub). |
| §12 (Liability) | Add note that no payment system exists yet. Consider adjusting the liability cap for free vs paid users. |
| §16 (Termination) | Add in-app account deletion as a termination method. |
| §19 (Contact) | Add Andover Digital LLC physical address if available. |

---

## F. What Needs Lawyer / Account-Holder Review

| Item | Why |
|---|---|
| **App Store distributor clause** | Must confirm legal validity and whether the individual account holder needs to be a party. |
| **Binding arbitration in Massachusetts** | Confirm appropriateness given users may be outside MA. |
| **Class action waiver** | Legal validity varies by state. |
| **Liability cap ($100 or fees paid)** | Confirm adequate for a free app without payment system. |
| **Individual account holder's liability exposure** | Does the individual need to be named as a party to the Terms? |
| **Tax/accounting implications of Apple IAP** | If/when StoreKit is added. |

---

## G. Launch Blocker vs Post-Launch Cleanup

| Item | Blocker? | Priority |
|---|---|---|
| Brokerage claims in §7 (false for V1) | **BLOCKER** — App Review could flag false feature claims | HIGH |
| Missing AI/LLM disclaimer | **BLOCKER** — Risk of user confusion/litigation | HIGH |
| Missing payment/subscription terms | **NOT A BLOCKER** — no payment system exists | MEDIUM (fix before adding payments) |
| Missing App Store distributor disclosure | **MODERATE** — may not block review but creates legal gap | MEDIUM |
| Individual account holder role not mentioned | **NOT A BLOCKER** for TestFlight, needs resolution for public launch | MEDIUM |
| Missing push notification terms | **NOT A BLOCKER** per se | LOW |
| Website footer missing "Andover Digital LLC" | **NOT A BLOCKER** but recommended | LOW |
