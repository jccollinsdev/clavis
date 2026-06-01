# App Store Privacy Labels — V1 Draft

**Created:** 2026-06-01
**Status:** DRAFT — must be confirmed against App Store Connect configuration
**Important:** These are inferred from code. Actual App Store privacy labels are configured in App Store Connect and cannot be verified without access.

---

## Draft Label Answers

### 1. Contact Info

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| Email Address | YES | YES | NO | Account authentication, account identification | `auth.signUp()` / `auth.signIn()` in iOS | Core auth data |
| Name | YES | YES | NO | Personalization | `user_preferences.name` via PATCH /preferences/profile | Optional field |
| Phone Number | NO | — | — | — | Not collected | NOT collected |
| Physical Address | NO | — | — | — | Not collected | NOT collected |
| Other Contact Info | NO | — | — | — | Not collected | NOT collected |

### 2. Financial Info

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| Payment Info | NO | — | — | — | No StoreKit/IAP code | **NOT collected in V1** |
| Credit/Debit Card | NO | — | — | — | No payment UI | NOT collected |
| Bank Info | NO | — | — | — | No payment UI | NOT collected |
| **Portfolio Holdings** | **YES** | YES | NO | Core app functionality | `positions` table: ticker, shares, purchase_price | Sent to MiniMax AI for scoring |
| **Ticker Symbols** | **YES** | YES | NO | Risk analysis, market data queries | `positions.ticker`, `watchlist_items.ticker` | Also used to query Polygon/Finnhub |

**Important:** Apple's definition of "Financial Info" may not include portfolio holdings. If Apple asks, portfolio holdings are "User Content" or "Other Data." However, they should be disclosed honestly.

### 3. User Content

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| **Generated Content (Digests, Scores, Analysis)** | **YES** | YES | NO | Core product output | `digests`, `ticker_risk_snapshots`, `position_analyses` tables | AI-generated content stored per user |
| **Alert Preferences** | YES | YES | NO | Feature configuration | `user_preferences.alerts_*` fields | |
| Support Content | NO | — | — | — | No in-app support chat | Support via email only |

### 4. Identifiers

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| User ID (UUID) | YES | YES | NO | Account identification | `auth.users.id` — linked to all user data | |
| Device ID | NO | — | — | — | Not collected | **NOT collected** |
| **APNs Device Token** | **YES** | YES | NO | Push notifications | `user_preferences.apns_token` via POST /preferences/device-token | Required by APNs. This is technically an identifier. |
| Advertising ID (IDFA) | NO | — | — | — | Not collected | NOT collected |

### 5. Purchases

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| Purchase History | NO | — | — | — | No StoreKit/IAP | NOT collected in V1 |
| **Subscription Tier** | **YES** | YES | NO | Feature gating | `user_preferences.subscription_tier` | Stored server-side, no Apple receipt |
| Trial Status | YES | YES | NO | Trial management | `user_preferences.trial_started_at`, `trial_ends_at` | |

### 6. Usage Data

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| Product Interaction | **NO** | — | — | — | No analytics SDK | **NOT collected** — Privacy Policy is WRONG about this |
| Advertising Data | NO | — | — | — | Not collected | |
| Other Usage Data | NO | — | — | — | Not collected | |

### 7. Diagnostics

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| Crash Data | **NO** (disabled) | — | — | — | Sentry SDK in backend but DSN empty | **NOT actively collected** |
| Performance Data | **NO** (disabled) | — | — | — | Sentry tracing disabled (rate 0.0) | NOT actively collected |
| Other Diagnostics | NO | — | — | — | | |

### 8. Search History

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| Search History | **NO** (local only) | NO | NO | UX convenience | iOS in-memory cache only | NOT persisted to server |

### 9. Other Data

| Data Type | Collected? | Linked to User? | Used for Tracking? | Purpose | Evidence | Notes |
|---|---|---|---|---|---|---|
| Birth Year | YES | YES | NO | Personalization | `user_preferences.birth_year` | Optional |
| Timezone | YES | YES | NO | Digest/alert scheduling | `user_preferences.timezone` | |
| Digest Time Preference | YES | YES | NO | Feature configuration | `user_preferences.digest_time` | |
| Alert Preferences | YES | YES | NO | Feature configuration | `user_preferences.alerts_*` | |
| Quiet Hours Settings | YES | YES | NO | Feature configuration | `user_preferences.quiet_hours_*` | |
| Onboarding Status | YES | YES | NO | UX state | `user_preferences.onboarding_acknowledged_at` | |
| Watchlist Items | YES | YES | NO | Core feature | `watchlist_items` | |
| Waitlist Email | YES | NOT typically | NO | Marketing waitlist | `waitlist_signups` table | Separate from app auth |

---

## Summary for App Store Connect

Based on actual V1 code, the privacy labels should indicate:

| Category | Data Type | Collected | Notes |
|---|---|---|---|
| Contact Info | Email Address | YES | Auth |
| Contact Info | Name | YES | Optional profile |
| Financial Info | Portfolio Holdings | YES | Core feature (ticker, shares, cost basis) |
| Identifiers | User ID | YES | Auth |
| Identifiers | Device Token | YES | Push notifications |
| Other Data | Birth Year | YES | Optional |
| Other Data | Preferences | YES | Multiple fields |
| Other Data | Watchlist Tickers | YES | Core feature |
| Usage Data | Product Interaction | **NO** | **DO NOT check this** — correct the Privacy Policy |
| Diagnostics | Crash Data | **NO** | Disabled |
| Purchases | Purchase History | **NO** | Not implemented in V1 |
| Search History | Search History | **NO** | Local only |

**TODO:** Cross-reference this with the actual App Store Connect configuration. These labels must match what is entered in App Store Connect exactly.

**TODO:** Apple's label for "Financial Info" may need careful wording — portfolio holdings are not traditional financial info. Consider marking as "Other Data" with a clear purpose description.

**TODO:** APNs device token should be listed under "Identifiers" with purpose "App Functionality — Push Notifications."
