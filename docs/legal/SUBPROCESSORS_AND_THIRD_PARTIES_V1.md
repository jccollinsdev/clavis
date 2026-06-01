# Subprocessors & Third Parties — V1 Audit

**Created:** 2026-06-01
**Status:** Needs parent/lawyer review

---

## Provider Directory

### 1. Supabase

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | Database (Postgres), Authentication, Hosting |
| **What data is sent to it** | All app data: user profiles, positions, preferences, analysis runs, digests, alerts, watchlists, job runs, waitlist entries. Backend uses `service_role_key` for full admin access. |
| **User-linked?** | YES — all user-scoped tables by user_id |
| **Required for app functionality?** | YES — core database and auth |
| **Required for payments/distribution?** | NO (but stores subscription_tier) |
| **Disclosed in current Privacy Policy?** | YES (§4.1 — "Supabase - cloud database and authentication") |
| **Covered in current Terms?** | Indirectly (via Privacy Policy) |
| **Needs to be added to revised docs?** | Already present, but should clarify it hosts the database |
| **Notes** | Supabase's `shared_ticker_events` and `prices` tables are publicly readable (RLS = true). This should be mentioned. |

### 2. Apple (App Store / iOS)

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | App distribution, APNs push notifications |
| **What data is sent to it** | iOS app binary, app metadata; APNs device token and push payloads |
| **User-linked?** | YES (device token identifies device) |
| **Required for app functionality?** | YES (distribution) |
| **Required for payments/distribution?** | YES (App Store distribution) |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | YES — especially APNs device token handling |
| **Notes** | No StoreKit/IAP code exists. If added later, Apple will also handle payments. |

### 3. Apple Push Notification Service (APNs)

| Property | Value |
|---|---|
| **Actually used in V1?** | YES (code exists, backend configured, may not be fully tested) |
| **Service** | Push notification delivery |
| **What data is sent to it** | Device token, notification payload (title, body, type, ticker symbol) |
| **User-linked?** | YES |
| **Required for app functionality?** | NO (alerts are a feature, not core) |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | YES |
| **Notes** | Backend `/health` reports APNs as "missing" — the .p8 key may not be deployed. Alerts code runs but push delivery may not work in production yet. |

### 4. MiniMax (LLM / AI Provider)

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | AI/LLM for risk scoring, digest generation, news sentiment, personalization, event analysis |
| **What data is sent to it** | **Risk scoring:** ticker, shares, purchase_price, position_value, labels, report summaries. **Digest:** full portfolio context (all positions, macro regime, sector data, events). **News enrichment:** full article text. **Personalization:** ticker context + recent events. |
| **User-linked?** | INDIRECTLY — portfolio/ticker data is sent but not user name/email/ID |
| **Required for app functionality?** | YES — core AI analysis pipeline |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | **CRITICAL — YES** |
| **Notes** | OpenAI-compatible SDK (`openai` pip package) used to call MiniMax API. The API key format is `sk-cp-...` (MiniMax). This is the single most important missing disclosure — portfolio financial data is sent to a third-party AI provider for processing. |

### 5. Polygon.io

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | Market data (daily bars, OHLC, prices, macro factors) |
| **What data is sent to it** | Ticker symbols only. API key in request headers. |
| **User-linked?** | NO — ticker symbols only |
| **Required for app functionality?** | YES — price data and market data |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | §8 (generic third-party data reference) |
| **Needs to be added to revised docs?** | YES — should note ticker symbols from user portfolios may be used to query market data |
| **Notes** | Ticker symbols from user portfolios/watchlists are used to query Polygon. While not personally identifying, ticker selection reveals financial interest. Rate-limited ~5 req/min. |

### 6. Finnhub

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | Financial fundamentals, news discovery, earnings calendar, company profiles |
| **What data is sent to it** | Ticker symbols only. API key in headers. |
| **User-linked?** | NO — ticker symbols only |
| **Required for app functionality?** | YES — fundamental data, news, earnings |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | §8 (generic third-party data reference) |
| **Needs to be added to revised docs?** | YES — same reasoning as Polygon |
| **Notes** | Ticker symbols from user portfolios used to query company-specific data. |

### 7. SnapTrade

| Property | Value |
|---|---|
| **Actually used in V1?** | CODE EXISTS — **FEATURE IS DISABLED** (`FeatureFlags.brokerageEnabled = false`) |
| **Service** | Brokerage connection middleware (OAuth, holdings sync) |
| **What data is sent to it** | User SnapTrade ID, broker authorization, connection ID, holdings (when enabled) |
| **User-linked?** | YES (via SnapTrade user IDs) |
| **Required for app functionality?** | NO (deferred to post-v1) |
| **Disclosed in current Privacy Policy?** | YES (indirectly as "Brokerage API provider (e.g., Plaid or Alpaca)" — **incorrectly named**) |
| **Covered in current Terms?** | YES (§7 — as generic "brokerage connections") |
| **Needs to be added to revised docs?** | YES — but should state it's NOT YET ACTIVE in V1 |
| **Notes** | **Current Privacy Policy names Plaid and Alpaca as brokerage providers. Neither is used. SnapTrade is the actual provider.** This is a factual error. The entire brokerage section of both legal docs describes a feature that is disabled in V1. |

### 8. Google News RSS

| Property | Value |
|---|---|
| **Actually used in V1?** | YES (secondary/fallback — Finnhub is primary) |
| **Service** | News article discovery via RSS |
| **What data is sent to it** | HTTP GET for RSS XML feeds. No user data. |
| **User-linked?** | NO |
| **Required for app functionality?** | NO (fallback only) |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | NO (no user data sent) |
| **Notes** | Automated RSS requests for ticker news. Standard web crawling. |

### 9. CNBC RSS

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | Macro and sector news RSS feeds |
| **What data is sent to it** | HTTP GET for RSS XML. No user data. |
| **User-linked?** | NO |
| **Required for app functionality?** | PARTIALLY (macro/sector digest content) |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | NO (no user data sent) |

### 10. Jina AI Reader

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | Article body extraction (URL → clean markdown) |
| **What data is sent to it** | Article URL only. No user data. |
| **User-linked?** | NO |
| **Required for app functionality?** | YES (primary article extraction path) |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | NO (no user data, but could be noted) |

### 11. Trafilatura / newspaper4k

| Property | Value |
|---|---|
| **Actually used in V1?** | YES (fallback article extraction) |
| **Service** | Python libs for article extraction |
| **What data is sent to it** | Article URL. Local processing, no external API. |
| **User-linked?** | NO |
| **Required for app functionality?** | NO (fallback only) |
| **Disclosed in current Privacy Policy?** | NO |
| **Notes** | Local libraries, no external data transmission. |

### 12. Sentry

| Property | Value |
|---|---|
| **Actually used in V1?** | CODE EXISTS — **DISABLED BY DEFAULT** (DSN env var empty, sample rates 0.0) |
| **Service** | Error monitoring and performance tracing |
| **What data is sent to it** | Would include stack traces, request context, user_id (if configured) |
| **User-linked?** | WOULD BE (if enabled) |
| **Required for app functionality?** | NO |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | YES — if/when Sentry is enabled in production |
| **Notes** | Currently harmless (disabled), but code is live. If DSN is configured in production .env, Sentry will capture error data including request context. |

### 13. Cloudflare

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | CDN, DNS, Tunnel (clavis.andoverdigital.com), DDoS protection |
| **What data is sent to it** | All API traffic passes through Cloudflare Tunnel. HTTP request data including IP addresses, user-agents, request bodies. |
| **User-linked?** | YES (IP, headers) |
| **Required for app functionality?** | YES (reverse proxy to backend) |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | YES — Cloudflare Tunnel is an infrastructure provider handling all request data |
| **Notes** | Cloudflare operates as a network/infrastructure layer between iOS app and backend server. All HTTPS traffic passes through it. |

### 14. DigitalOcean

| Property | Value |
|---|---|
| **Actually used in V1?** | YES |
| **Service** | VPS hosting (Droplet at 134.122.114.241) |
| **What data is sent to it** | All backend processing, database queries, application logic. Hosts the entire backend including .env with all API keys. |
| **User-linked?** | YES (all user data processed on VPS) |
| **Required for app functionality?** | YES (server hosting) |
| **Disclosed in current Privacy Policy?** | NO |
| **Covered in current Terms?** | NO |
| **Needs to be added to revised docs?** | YES — as hosting infrastructure provider |
| **Notes** | Listed as subprocessor / hosting provider. |

### 15. Plaid / Alpaca

| Property | Value |
|---|---|
| **Actually used in V1?** | **NO** — neither Plaid nor Alpaca is used. Current Privacy Policy incorrectly names them. |
| **Service** | None |
| **Correct provider** | SnapTrade (but brokerage is disabled) |
| **Status** | **ERROR IN CURRENT DOCS** — must be corrected |

---

## Summary

### Critical Missing Disclosures

| Provider | Missing from Privacy Policy | Missing from Terms | Risk |
|---|---|---|---|
| MiniMax (LLM/AI) | YES | YES | **HIGH** — portfolio financial data sent to third-party AI |
| Apple APNs | YES | YES | HIGH — device token shared for push |
| Cloudflare | YES | YES | MEDIUM — all traffic passes through |
| DigitalOcean | YES | YES | MEDIUM — hosting provider |

### Errors in Current Documents

1. **Privacy Policy §4.1** names "Plaid or Alpaca" as brokerage providers. Neither is used. SnapTrade is the actual provider (and brokerage is disabled).
2. **Privacy Policy** lists "Email delivery provider (e.g., Resend)" — no email sending code exists.
3. **Privacy Policy §2.2** claims "usage data" collection — no analytics SDK exists.

### Accurate Third-Party List for V1 Revised Docs

| Provider | Role | Data Received | User Data? |
|---|---|---|---|
| Supabase | Database, Auth | All app data | YES |
| Apple (App Store + APNs) | Distribution, Push | App binary, device token, push payloads | YES (device token) |
| MiniMax | AI/LLM Processing | Portfolio context, article text | INDIRECT (portfolio data) |
| Polygon.io | Market data | Ticker symbols | NO (tickers only) |
| Finnhub | Fundamentals, news | Ticker symbols | NO (tickers only) |
| Google News RSS | News discovery | Nothing (RSS crawl) | NO |
| CNBC RSS | News discovery | Nothing (RSS crawl) | NO |
| Jina AI Reader | Article extraction | Article URLs | NO |
| Cloudflare | CDN/Tunnel | All request data | YES (transient) |
| DigitalOcean | Hosting | All app data | YES |
| SnapTrade | Brokerage (DISABLED) | None currently | N/A |
| Sentry | Error monitoring (DISABLED) | None currently | N/A |
