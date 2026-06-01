# Privacy Policy — Revised Draft for V1

**Created:** 2026-06-01
**Status:** DRAFT — NEEDS PARENT/LAWYER REVIEW
**Based on:** Actual V1 code audit
**Changes from current:** Marked with `[REVISED]`

> **IMPORTANT:** This is a draft for comparison. Do not publish or use as final. Parent, account holder, and lawyer must review before use. Placeholders marked with `[PLACEHOLDER: ...]` must be replaced or approved.

---

# Privacy Policy

**Last Updated:** [Date]

**TODO: PARENT/ACCOUNT HOLDER/LAWYER REVIEW THE FOLLOWING SENTENCE:**

> Clavix is operated by Andover Digital LLC ("we," "us," "our"). The Clavix iOS app is distributed on the Apple App Store through an Individual Apple Developer account held by [Individual Apple Developer Account Holder], who acts as the App Store distributor/seller for Apple distribution purposes. [Individual Apple Developer Account Holder] does not receive or access user personal data through their role as App Store distributor. Andover Digital LLC is responsible for operating the Clavix service, handling personal information, providing support, and managing the product experience described in this Privacy Policy.

This policy explains how we collect, use, disclose, and safeguard your information when you use the Clavix application ("the App") and related services.

**Our pledge:** We do not sell your data. We do not advertise with your portfolio data. Your portfolio information is yours.

---

## 1. Scope

This Policy applies to all users of the Clavix service in the United States. Clavix is intended for individuals who are 18 years of age or older. We do not knowingly collect personal information from anyone under 18.

The Clavix iOS app is available through the Apple App Store. Apple, as the App Store operator, may collect certain information as described in Apple's own privacy policy. [PLACEHOLDER: INSERT LINK TO APPLE PRIVACY POLICY]

---

## 2. Information We Collect

### 2.1 Information You Provide to Create and Manage Your Account

| Data | Purpose | Optional? |
|---|---|---|
| Email address | Account creation, authentication, account-related communication | Required |
| Display name | To personalize your experience | Optional |
| Birth year | To personalize your experience | Optional |

### 2.2 Information You Provide to Use the Service

**Portfolio holdings.** When you add positions to your portfolio, you provide:
- Ticker symbol (e.g., AAPL, SPY)
- Number of shares
- Average purchase price
- Purchase date (optional)

**Watchlist items.** When you add tickers to your watchlist, we store the ticker symbols you select.

**Alert and notification preferences.** You can configure which alerts you receive, quiet hours, delivery time, and digest length. These preferences are stored with your account.

### 2.3 Information Provided for Push Notifications

If you enable push notifications, we collect a device token provided by Apple's Push Notification service (APNs). This token is used solely to deliver notifications you have requested. You can disable push notifications at any time in your iOS Settings.

### 2.4 Information Collected Automatically

We collect limited technical information to operate and secure the service:
- **IP address** — collected temporarily for rate limiting, security, and operational monitoring. This is not stored long-term.
- **Request metadata** — the type of request, endpoint accessed, and timestamp are logged temporarily for debugging and performance monitoring.

**We do not collect** usage analytics, session recordings, mouse movements, page interactions, or any behavioral tracking data.

### 2.5 Information from Third-Party Integrations

**Brokerage connections are not available in the current version of the app.** [REVISED — removed false claim that brokerage is live]

If brokerage connection becomes available in a future update, we will update this policy. When available, connections use OAuth or read-only API access through a regulated intermediary. Your brokerage login credentials are handled by your brokerage and are never stored by us.

---

## 3. How We Use Your Information

We use your information for the following purposes:

- **To provide the Clavix service.** This includes generating personalized risk scores, daily briefings, news filtering, and alerts based on your portfolio and preferences.
- **To communicate with you.** We may send you account-related communications (e.g., password reset emails via Supabase Auth). We do not send marketing emails.
- **To improve the service.** We may analyze aggregated, de-identified data to improve the product.
- **To secure the service.** We monitor for unauthorized access, abuse, and technical issues.
- **To comply with legal obligations.**

---

## 4. AI and Model Processing [NEW]

Clavix uses artificial intelligence (AI) and large language models (LLMs) to generate risk scores, portfolio briefings, news sentiment analysis, and explanatory content.

**What data is sent to the AI provider:** When we generate analysis for your portfolio, we may send the following context to our AI provider (MiniMax):
- Your portfolio positions (ticker symbols, share counts, cost basis)
- Your portfolio value context
- Recent news articles and market data related to your positions

**What is NOT sent:** Your name, email address, user ID, or direct identifiers are not sent to the AI provider.

**Purpose:** The AI generates structured risk analysis, digests, and scoring based on your portfolio context. This is what makes the service personalized.

**AI provider:** We use MiniMax, an AI model provider, to process this data. MiniMax is contractually prohibited from using your data to train or improve their models, and from using it for any purpose other than providing the service to us.

**Opt-out:** The AI processing is integral to the core service. If you do not want your portfolio data processed by AI, you should not use the service.

---

## 5. How We Share Your Information

We do not sell, rent, or trade your personal information. We share your information only in the following limited circumstances:

### 5.1 Service Providers (Subprocessors)

We use trusted third-party service providers who process data on our behalf:

| Provider | Service | Data Shared | Location |
|---|---|---|---|
| **Supabase** | Database hosting, authentication | All app data (encrypted at rest) | United States |
| **MiniMax** | AI/LLM processing | Portfolio context, article text | [TODO: CONFIRM MINIMAX DATA LOCATION] |
| **Apple (APNs)** | Push notification delivery | Device token, notification payload | United States / Apple infrastructure |
| **Polygon.io** | Market data | Ticker symbols (no personal data) | United States |
| **Finnhub** | Financial data, news discovery | Ticker symbols (no personal data) | United States |
| **Cloudflare** | CDN, DNS, DDoS protection | All HTTP request data (transient) | Global (edge network) |
| **DigitalOcean** | Server hosting | All app data processed on servers | United States |

**TODO: PARENT/LAWYER REVIEW:** Confirm MiniMax data location and contractual protections.

### 5.2 Legal Requirements

We may disclose your information if required by law, court order, or government authority, or to protect our rights, property, or safety, our users, or the public.

### 5.3 Business Transfers

In the event of a merger, acquisition, or sale of assets, your information may be transferred. We will notify you before your information becomes subject to a different privacy policy.

---

## 6. Apple App Store Role [NEW]

The Clavix iOS app is distributed through the Apple App Store. Apple is not a party to this Privacy Policy and is not responsible for the Clavix service or its data handling.

**Apple as payment processor:** If and when subscription purchases are implemented, Apple will process payments through the App Store. Apple does not share your payment card details with us. Apple may share your transaction ID and purchase status with us to manage your subscription.

**Apple Push Notification service:** If you enable push notifications, your device token is handled by Apple's APNs infrastructure to deliver notifications.

**TODO: UPDATE WHEN STOREKIT/IAP IS IMPLEMENTED**

---

## 7. Data Storage and Security

- All data is stored on Supabase infrastructure hosted in the United States.
- Encryption in transit: TLS 1.2+
- Encryption at rest: AES-256
- Access to personal data is restricted to authorized personnel on a need-to-know basis
- Brokerage login credentials are never stored (brokerage feature not yet available)
- We implement commercially reasonable security measures but cannot guarantee absolute security

---

## 8. Data Retention

We retain your personal information for as long as your account is active.

**Shared/public data:** Some data we generate (ticker risk scores, news articles) is stored in shared tables that are accessible to all users. This data is not personally identifying and is retained as long as it remains useful for the service.

**News data:** News articles and events are automatically deleted after 30 days.

**Upon account deletion:** When you delete your account through in-app settings or by contacting us, we delete or anonymize your personal data. Some shared data (such as ticker risk snapshots and news events) may remain in shared tables, but it will no longer be linked to your identity.

---

## 9. Your Rights and Choices

Regardless of your state of residence, we honor the following rights:

- **Access and portability.** You can download your account data through the in-app "Export Data" feature.
- **Correction.** You can update your profile information and preferences in Settings.
- **Deletion.** You can permanently delete your account and associated data through the in-app "Delete Account" feature.
- **Push notification control.** You can enable or disable push notifications in your iOS Settings or in-app.
- **Communication preferences.** You can configure your digest timing, alert types, and quiet hours in Settings.

To exercise any rights not available in-app, email us at support@getclavix.com. We will respond within 30 days.

### California Residents (CCPA/CPRA)

If you are a California resident, you have additional rights under the CCPA. We do not sell or share your personal information as those terms are defined under the CCPA. To exercise your rights, contact us at support@getclavix.com.

---

## 10. Children's Privacy

The service is not directed to individuals under 18. We do not knowingly collect personal information from children under 18. If you believe a child has provided us with personal information, please contact us.

---

## 11. Cookies and Tracking Technologies

We use only essential session cookies to keep you logged in. We do not use advertising cookies, cross-site tracking, or third-party analytics scripts.

---

## 12. Changes to This Policy

We may update this Privacy Policy. When we make material changes, we will notify you through the app and update the "Last Updated" date. Your continued use after the effective date constitutes acceptance of the updated policy.

---

## 13. Contact

**Andover Digital LLC**
Operator of Clavix
Email: support@getclavix.com

**App Store Distributor:** [Individual Apple Developer Account Holder]
The Clavix iOS app is distributed through an Individual Apple Developer account. See the beginning of this policy for details.

---

## Document Control

- **Revised:** 2026-06-01
- **Previous version:** April 12, 2026
- **Status:** Draft — requires parent/account-holder/lawyer review before publication

### Key Changes from Previous Version

| Change | Reason |
|---|---|
| Added App Store distributor disclosure | Individual Apple account holder vs Andover Digital LLC structure |
| Added AI/LLM processing section | Portfolio data sent to MiniMax — was completely missing |
| Removed false "usage data" claim | No analytics SDK exists |
| Removed false brokerage claims | Brokerage is disabled in V1 |
| Removed false email marketing claims | No email infrastructure exists |
| Added APNs/device token disclosure | Push notification data was missing |
| Added specific subprocessor list | Many were missing or incorrect |
| Added public/shared data retention note | `shared_ticker_events` and `prices` are public-readable |
| Added in-app deletion/export options | These exist in code but weren't in policy |
| Removed Plaid/Alpaca references | Neither is used; SnapTrade is the actual provider (and disabled) |
