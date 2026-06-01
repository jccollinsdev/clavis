# Privacy Policy Audit — V1

**Created:** 2026-06-01
**Audit of:** `https://getclavix.com/privacy` (live as of April 12, 2026)
**Status:** Needs parent/lawyer review

---

## A. What the Current Privacy Policy Gets Right

1. **Operator identification:** Correctly identifies Andover Digital LLC as the operator.
2. **No data selling:** Correctly states "We don't sell your data."
3. **No advertising with data:** Correctly states "We don't advertise with your data."
4. **Account information collected:** Generally describes email collection.
5. **Portfolio holdings disclosure:** Mentions holding entry.
6. **Scope limitation:** Says intended for US, 18+ only.
7. **Children's privacy:** States service not for under-18.
8. **Supabase as subprocessor:** Named correctly.
9. **Data retention tied to account:** Generally correct.
10. **User rights section:** Access, correction, deletion, portability. Export and deletion endpoints exist in code.
11. **CCPA section:** Attempts California compliance.
12. **Security practices:** TLS, AES-256 at rest generally correct.

---

## B. What Is Overbroad or Describes Features Not Live in V1

| Claim | Location | Problem |
|---|---|---|
| "Usage data — features accessed, session duration, and interaction patterns, used solely to improve the Service" | §2.2 | **FALSE.** No analytics SDK, telemetry, or event tracking exists anywhere in the iOS app or backend code. |
| "When you connect a brokerage account, we receive account holdings and transaction data" | §2.3 | **FALSE for V1.** Brokerage connection is DISABLED (`FeatureFlags.brokerageEnabled = false`). No brokerage account can currently be connected. |
| "Brokerage API provider (e.g., Plaid or Alpaca)" | §4.1 | **FALSE.** Neither Plaid nor Alpaca is used. The actual provider is SnapTrade. And brokerage is disabled. |
| "Email delivery provider (e.g., Resend)" | §4.1 | **FALSE.** No email sending code exists in the codebase. No Resend, SendGrid, SES, SMTP, or any email library is used. |
| "We send transactional and product communications to your registered email address" | §3 | **FALSE.** No email sending capability is implemented. |
| "Brokerage credentials are never stored. We store only encrypted OAuth access tokens" | §5 | **PARTIALLY FALSE.** SnapTrade user IDs and secrets ARE stored in `user_preferences.snaptrade_user_id` and `.snaptrade_user_secret`. However, brokerage login credentials (username/password) are never stored. Also, brokerage is disabled. |
| "To sync with brokerage accounts you have authorized" | §3 | **FALSE for V1.** Brokerage is disabled. |
| "We will notify you via email" (for business transfers) | §4.3 | **FALSE.** No email capability. |
| "We will notify you by email" (for policy changes) | §11 | **FALSE.** No email capability. |
| "You may unsubscribe from non-essential emails" | §8 | **FALSE.** No email capability. |

---

## C. What Is Missing

| Missing Item | Severity | Details |
|---|---|---|
| **AI/LLM data processing disclosure** | **CRITICAL** | Portfolio position data (tickers, shares, cost basis) is sent to MiniMax AI for risk scoring and digest generation. No mention of this anywhere in the policy. |
| **MiniMax as subprocessor** | **CRITICAL** | MiniMax is the AI provider that receives portfolio context. Not named. |
| **APNs / push notification token** | **HIGH** | Device tokens are collected and sent to Apple APNs. Not mentioned. |
| **Apple's role (App Store, APNs)** | **HIGH** | App Store distribution, APNs as a data processor. |
| **Cloudflare (CDN/Tunnel)** | **MEDIUM** | All traffic passes through Cloudflare Tunnel. |
| **DigitalOcean (VPS hosting)** | **MEDIUM** | Server hosting provider. |
| **Polygon.io** | **MEDIUM** | Market data provider receiving ticker symbols. |
| **Finnhub** | **MEDIUM** | News and fundamentals provider receiving ticker symbols. |
| **Individual Apple Developer Account / App Store seller disclosure** | **MEDIUM** | No mention that App Store seller name may differ from Andover Digital LLC. |
| **Publicly readable data** | **MEDIUM** | `shared_ticker_events` and `prices` tables are publicly readable. Not disclosed. |
| **Data retention specifics** | **MEDIUM** | Claims "as long as account is active" but doesn't mention 30-day news cleanup, shared data (retained indefinitely), cached/processed data. |
| **Account deletion specifics** | **MEDIUM** | Policy says "within 30 days" but code deletes immediately. This is actually better than stated, but still a discrepancy. |
| **User choices beyond deletion** | **LOW** | No mention of alert preferences, digest frequency, quiet hours, etc. being stored. |
| **In-app account deletion availability** | **LOW** | The app has account deletion (Settings > Delete Account). Should be mentioned. |
| **Debug data (in-memory request logging)** | **LOW** | DebugService records up to 500 requests and 1000 AI calls in memory. Not disclosed. |

---

## D. What Is Inaccurate or Contradictory

1. **"Usage data" claim is false** — §2.2 claims collection of usage data. No analytics exist. This needs to be removed or caveated.
2. **Brokerage described as live** — §2.3, §3, §4.1, §5, §6 all describe brokerage as a current feature. It is disabled in V1.
3. **Wrong brokerage provider named** — §4.1 lists "Plaid or Alpaca." Neither is used. SnapTrade is the actual provider.
4. **Email provider listed but unsendable** — §4.1 lists "Email delivery provider (e.g., Resend)." No email infrastructure exists.
5. **"Encrypted access token" vs stored credentials** — §5 says "never store brokerage credentials... only encrypted OAuth access tokens." In reality, SnapTrade user IDs and secrets ARE stored in the database.
6. **"Notify by email" claims** — Multiple places promise email notification. No email capability exists.

---

## E. What Should Be Rewritten

| Section | Change Needed |
|---|---|
| §1 (Scope) | Add App Store distributor disclosure |
| §2.1 (Info You Provide) | Add: name, birth_year, APNs device token, all preferences |
| §2.2 (Automatically Collected) | **REMOVE false "usage data" claim.** Replace with actual auto-collected data: IP (transient), request metadata. |
| §2.3 (Third-Party Integrations) | **REMOVE brokerage as active feature.** Add AI/LLM processing disclosure. Add APNs/device token. |
| §3 (How We Use) | Remove email claims. Add AI/LLM processing purpose. |
| §4 (How We Share) | Add MiniMax, APNs, Cloudflare, DigitalOcean. Remove email provider. |
| §5 (Data Security) | Correct the brokerage credentials claim. |
| §6 (Brokerage) | **Either remove or mark as "coming in a future update."** |
| §7 (Retention) | Add shared data retention. Add 30-day news cleanup. |
| §8 (User Rights) | Add in-app deletion availability. Remove "opt out of marketing" (no marketing exists). |
| §11 (Changes) | Remove "notify by email." Replace with in-app notification. |
| §12 (Contact) | Add Andover Digital LLC details. |

---

## F. What Should Be Left Alone

- **Pledge not to sell data** — accurate and important.
- **No advertising with portfolio data** — accurate.
- **Children's privacy (§9)** — accurate.
- **Cookies (§10)** — accurate (session cookies only).
- **California rights (§8.1)** — acceptably accurate.
- **Legal disclosure (§4.2)** — standard, acceptable.
- **Security (§5)** — TLS and AES-256 statements are correct for Supabase.
- **Business transfers (§4.3)** — standard.
- **CCPA/CPRA (§8.1)** — acceptable for the current scope.

---

## G. What Needs Parent/Legal/Account-Holder Review

| Item | Why |
|---|---|
| **Individual Apple Developer Account holder disclosure** | Must decide whether and how to mention the individual's name/role |
| **AI/LLM processing language** | Must ensure no legal exposure from AI-generated analysis |
| **Removal of false brokerage claims** | Must confirm timeline for brokerage |
| **Removal of false email/analytics claims** | Must confirm future plans |
| **Data controller designation** | Confirm Andover Digital LLC is properly designated |
| **Governing law (Massachusetts)** | Confirm appropriateness |

---

## H. App Store Privacy Label Alignment

The current Privacy Policy describes data collection that partially conflicts with what App Store privacy labels would require based on actual V1 data collection. See separate draft at `APP_STORE_PRIVACY_LABELS_DRAFT.md`.

Key conflicts:
- Policy claims "usage data" collected → would require "Usage Data" on label. Actual: NOT collected.
- Policy claims brokerage data collected with identifying info → would require "Financial Info" on label. Actual: NOT collected (disabled).
- Policy doesn't mention push notification token → APNs requires "Identifiers" on label. Actual: token collected.
