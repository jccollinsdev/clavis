# Clavix Launch Readiness Audit — 2026-05-30

**Auditor:** Claude Opus (Phase 0 — audit/report only, no product code changed)
**Scope:** End-to-end: product truth, iOS, backend, production DB, deployment, data freshness, App Store, StoreKit, legal, website, brand, observability, security, QA.
**Evidence basis:** Live production API, production Supabase DB (`uwvwulhkxtzabykelvam`), iOS app built + run in iPhone 17 simulator with real authenticated data, repo code, live website, security advisors.
**Verdict in one line:** The core app is real, polished, and largely functional with live data — but it is **not** launch-ready: there is **zero StoreKit/IAP code**, the **digest+alert pipeline has been stalled since 2026-05-28**, **ETFs are entirely missing** from the universe (contradicting Truth §5), **per-ticker news relevance is broken** (Apple's feed shows QQQ/SCHX/unrelated articles), the **rating scale is mis-calibrated** (no ticker scores above grade A), and Apple enrollment is still pending.

> This report supersedes the optimistic "GO for free TestFlight" conclusions in `docs/CLAVIX_FINAL_VERIFICATION.md` and `docs/CLAVIX_UI_DATA_QA_REPORT.md` (both authored the same day by a prior session). Those used same-session verification scripts; this audit verified independently against live prod + simulator and found material gaps those scripts did not test for (news relevance, ETF coverage, grade calibration, digest/alert staleness, StoreKit absence).

---

## A. Executive Summary

| Dimension | Readiness | Notes |
|---|---|---|
| **Overall public-paid launch** | **~40%** | StoreKit missing entirely; data-quality + pipeline reliability gaps |
| **Free TestFlight (closed beta)** | **~60%** | Code/app largely ready; gated on Apple enrollment (external) + 2-day-stale digests/alerts |
| **App Store submission** | **~40%** | Needs screenshots, metadata, age rating, demo account, news-relevance fix |
| **Paid launch (charging money)** | **~20%** | **No IAP/StoreKit code exists at all** — multi-day build + App Review |
| **Public launch** | **~30%** | Depends on paid launch + data-truth fixes + observability |

**Biggest blockers (top 5):**
1. **No StoreKit / In-App Purchase implementation anywhere in iOS** (`import StoreKit` = 0 hits; no `.storekit` file; no product IDs). Upgrade sheets say "Pro is coming soon" and dismiss. → Cannot charge money. Cannot test Pro via App Review.
2. **Apple Developer enrollment pending** (external, applied under user's mother). Gates TestFlight, App Store, APNs, StoreKit products. `/health` confirms `apns:missing`.
3. **Per-ticker news relevance is broken.** AAPL's "Recent news" in the live app is dominated by articles about *other* securities (QQQ, SCHX, SCHG, Porch Group, "Josh Brown Porterhouse strategy") — one article's own TLDR reads *"no substantive content… or any AAPL-related news."* This corrupts the News dimension and destroys the "audit every article" trust promise.
4. **ETFs are entirely absent from the universe** (Truth §5 requires top-50 ETFs). DB: `ticker_metadata` ETFs = 0, `etf_holdings` = 0 rows, SPY/VOO have no snapshots. The Search "ETFs" quick-filter returns **"No supported ticker matched 'VTI'."** Dead-end feature + product-scope contradiction.
5. **Digest + alert pipeline stalled since 2026-05-28.** Latest digest `generated_at` = 2026-05-28; alerts in last 2 days = 0. A prior-session scheduler fix is deployed (next_run in future) but **no fresh digest/alert has actually been produced** — unverified until the 2026-05-31 morning run. Compounded by a **rating mis-calibration**: max grade across all 504 tickers is **A**; 64% are BBB; blue chips (KO=BBB, JNJ/PG/WMT/MSFT all A) never reach AA/AAA.

**Risk call-outs:**
- **Biggest code risk:** StoreKit built from scratch is the long pole for paid launch; and the async-route event-loop pattern (two P0s already found+fixed this week) likely lurks in `portfolio.py`/`today.py`/`dashboard.py` (unaudited).
- **Biggest data risk:** News relevance + ETF absence + grade ceiling + limited-news-still-averaged-into-composite (Truth §7 exclusion not applied) — together they make the rating look miscalibrated to the exact sophisticated ICP it targets.
- **Biggest Apple/admin risk:** Everything Apple is gated on an enrollment under a parent's identity (seller-name / banking / tax / age implications) that has not completed.
- **Biggest legal/compliance risk:** Privacy Policy names "Plaid or Alpaca" as the brokerage processor while the real integration is SnapTrade — an inaccurate sub-processor disclosure.
- **Biggest user-facing trust risk:** Showing irrelevant news as a ticker's news, and showing blue chips like Coca-Cola as BBB, to a credit-rating-literate audience.

**Is each stage realistic soon?**
- **TestFlight (free closed beta): YES, realistic within days of Apple approval.** The app builds, launches crash-free, and core flows work on real data. Recommend fixing news relevance + confirming the 05-31 digest fired before inviting testers.
- **App Store submission: realistic in ~1–2 weeks** (metadata/screenshots/age-rating/demo account + news-relevance fix).
- **Paid launch: NOT soon — ~2+ weeks minimum** (StoreKit from zero + sandbox + IAP review). Matches the Day-28 plan only if StoreKit starts now.
- **Public launch: after paid launch + data-truth + observability.**

---

## B. Evidence Index

| # | Command / Check | Environment | Result | Verified |
|---|---|---|---|---|
| 1 | Read `docs/CLAVIX_TRUTH.md` v2.0 | repo | Source of truth; internal §6/§10 provider conflict found | ✅ |
| 2 | `curl https://clavis.andoverdigital.com/health` | prod API | `200` in 141ms; `apns:missing`, `snaptrade:configured`, `minimax:configured`, `supabase:configured` | ✅ |
| 3 | `curl …/tickers/AAPL` (no auth) | prod API | `401 Missing Authorization header` (auth gate works) | ✅ |
| 4 | Mint HS256 JWT (test user) → `curl …/tickers/AAPL` | prod API | `200` full payload (real position 1 sh @ $100, price $312.08) | ✅ |
| 5 | `curl …/prices/AAPL?days=365` (auth) | prod API | `200` real bars (201.7, 203.27…) — price endpoint works server-side | ✅ |
| 6 | `list_tables` (Supabase) | prod DB | 31 tables; legacy `news_items`/`ticker_news_cache` **absent** (retired ✓) | ✅ |
| 7 | Universe composition SQL | prod DB | `ticker_universe`=504 (SP500∪USER_SHARED); **ETFs=0**; `etf_holdings`=0 | ✅ |
| 8 | Latest-snapshot SQL (2026-05-30) | prod DB | 503 tickers; 1005 rows (daily+manual_refresh dup); `is_product_visible`/`verification_status`/`data_status`/`writer_source` **all NULL** | ✅ |
| 9 | Deduped latest-per-ticker (504) | prod DB | All 5 dims populated; **generated_at & stale_after NULL for all 504**; 360/504 have limited_data flag | ✅ |
| 10 | Limited-dims breakdown | prod DB | 357/504 = **news_sentiment limited** | ✅ |
| 11 | Sample tickers SQL (AAPL/MSFT/NVDA/SPY/VOO/JNJ/PG/KO/BRK.B/WMT) | prod DB | **SPY/VOO absent**; max grade **A**; KO/BRK.B/JNJ show limited-news still averaged into composite | ✅ |
| 12 | `shared_ticker_events` stats (7d) | prod DB | 2287 articles, 2227 enriched; **only 196/504 tickers have any news, 144 have ≥3**; TLDR on 60% | ✅ |
| 13 | AAPL snapshot history | prod DB | **+5 delta is real**; same-day daily 65.6/BBB vs manual 71.0/A; single-day BB flicker (hysteresis off) | ✅ |
| 14 | `data_generation_runs` / `job_runs` / `alerts` health | prod DB | gen controller dead since 05-16 (35 failed, **13 stuck running**); alerts last 2d = **0**; latest digest 05-28 | ✅ |
| 15 | `get_advisors(security)` | Supabase | RLS-no-policy ×4; **anon can EXEC `save_daily_asset_safety_profile`/`save_daily_macro_regime` SECURITY DEFINER**; leaked-pw off | ✅ |
| 16 | iOS build + run (`build_run_sim`) | sim iPhone 17 | **Build + launch succeeded, no crash**; persisted session → real data | ✅ |
| 17 | Simulator tap-through (Today→Ticker→Methodology→Article→Search→Settings→Legal) | sim | See §F. Flows work; found news-relevance, ETF dead-end, "Version unavailable", price-chart transient | ✅ |
| 18 | `rg` banned strings in iOS user-visible | repo | No user-visible "Clavis"/"SnapTrade"; `DisplayText.swift` sanitizes banned vocab; "watch"/"coverage" leak in a few static strings | ✅ |
| 19 | `ContentView.swift` VQA gating | repo | Mock `ClavixVisualQA` is `#if DEBUG` + `CLAVIX_USE_VQA_MOCK=1` only — **not reachable in release** | ✅ |
| 20 | StoreKit grep | repo | `import StoreKit`=0; no `.storekit`; no product IDs; upgrade sheets = "Pro is coming soon" → dismiss | ✅ |
| 21 | `curl getclavix.com /,/terms,/privacy,/methodology` | website | All `200`; `/support` 404 | ✅ |
| 22 | Live Privacy/Terms content | website | "Clavix"/"Andover Digital LLC"; 18+; No-Investment-Advice; **names "Plaid or Alpaca" not SnapTrade** | ✅ |
| 23 | `rg` web/index.html | repo | No Clavis/SnapTrade; buy/sell only as disclaimers; pricing $20/mo + 14-day trial (matches Truth) | ✅ |
| 24 | Provider source (`finnhub_news.py`) | repo | Finnhub = "Primary news source… 7-day window per-ticker"; Google RSS auxiliary/fallback | ✅ |
| 25 | iOS API base URL | repo | `Secrets.xcconfig` → `https://clavis.andoverdigital.com` (prod) | ✅ |

**Could NOT be verified (UNVERIFIED):** 05-31 morning digest/alert generation (future event); APNs push delivery (needs Apple p8); StoreKit (does not exist); Onboarding & Sign-up/Sign-in flows in sim (session was already persisted — see §F); CSV import (no UI found); small-device/Dynamic-Type/dark-mode layout (not exercised).

---

## C. Master Blocker Table

| ID | Pri | Area | Issue | Evidence | Fix | Verify | Owner | Cx | TF | AS | Paid | Pub |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | P0 | StoreKit | No IAP code at all; "Pro coming soon" dismiss | grep #20; `SettingsView.swift:992`, `HoldingsListView.swift:1291` | Build StoreKit 2 (`clavix_pro_monthly` $19.99 + 14-day intro), entitlement sync, Restore button | Sandbox purchase + restore on device | code+user | L | – | – | **YES** | YES |
| B2 | P0 | Apple | Developer enrollment pending (under parent) | `/health apns:missing`; user note | Complete enrollment, accept agreements, banking/tax | App Store Connect record exists | user/Apple | M | **YES** | **YES** | **YES** | YES |
| B3 | P0 | Data | Per-ticker news relevance broken | §F sim: AAPL feed = QQQ/SCHX/SCHG/Porch/Josh-Brown; one TLDR "no AAPL-related news" | Enforce ticker-relevance filter (Truth §10) at ingestion/display; re-score | Open AAPL/MSFT/NVDA — all news on-ticker | code | M | soft | soft | – | YES |
| B4 | P0 | Data | ETFs entirely missing from universe | DB #7,#11; sim "No supported ticker matched VTI" | Ingest top-50 ETFs + ETF FH (top-25 holdings); populate `etf_holdings`; OR hide "ETFs" filter & label scope | SPY/VOO/QQQ return a rating | code | L | soft | soft | – | YES |
| B5 | P0 | Prod/Data | Digest + alert pipeline stalled since 05-28 | DB #14 (alerts 2d=0; digest 05-28) | Confirm scheduler fix produces 05-31 digest+alerts; add failure alerting | `digests`/`alerts` rows dated 05-31 | code | M | **YES** | YES | YES | YES |
| B6 | P0 | Data | Rating mis-calibration: max grade A; 64% BBB | DB #11 (WMT 75/A top; KO BBB) | Apply Truth §7 limited-data exclusion; fix Financial Health missing inputs; recalibrate | Blue chips reach AA/AAA; ≥6 grade bands | code | L | soft | soft | – | YES |
| B7 | P1 | Methodology | Limited-data dim still averaged into composite | DB: KO news=37 limited, comp 68.2=avg of 5 | Exclude limited dims; rescale to remaining (Truth §7) | KO composite rises ~8pts | code | S | – | soft | – | YES |
| B8 | P1 | Methodology | Hysteresis (anti-flicker) not implemented | DB #13 AAPL BB(57) single-day flip; same-day BBB→A | Implement 3-pt/2-day rule (Truth §7) | No single-day grade flips | code | M | – | – | soft | YES |
| B9 | P1 | Data integrity | Duplicate same-day snapshots disagree on grade | DB #13: 05-30 daily 65.6/BBB vs manual 71.0/A | One canonical snapshot per ticker/day; define "prior session" | 1 visible snapshot/ticker/day | code | M | soft | YES | YES | YES |
| B10 | P1 | Security | anon can EXEC SECURITY DEFINER write fns | advisor #15; migration `20260530_security_fixes.sql` unapplied | Apply migration (revoke anon EXEC + auth guard + RLS on gnews) | advisor clean | user/code | S | – | YES | YES | YES |
| B11 | P1 | iOS | Settings shows "Version unavailable" | §F sim | Wire CFBundleShortVersionString/build | Real version shows | code | S | soft | YES | – | – |
| B12 | P1 | Data freshness | `generated_at`/`stale_after` NULL on all snapshots | DB #9 | Populate at write; drive UI freshness labels | non-null; labels show | code | S | – | YES | – | YES |
| B13 | P2 | iOS/Truth | Search "outside universe" lacks "Add manually" CTA | §F sim (VTI) | Add manual-add CTA on no-match (Truth §12) | CTA appears | code | S | – | soft | – | YES |
| B14 | P2 | Legal | Privacy names Plaid/Alpaca, real processor is SnapTrade | website #22 | Correct sub-processor disclosure (generic "brokerage aggregator") | policy accurate | user/legal | S | – | YES | YES | YES |
| B15 | P2 | Copy | Banned vocab leaks ("watch", "coverage") in static strings | `TickerDetailView.swift:212`; FIN audit "Watch"; Today "on watch" | Route static copy through sanitizer / reword | grep clean | code | S | – | soft | – | – |
| B16 | P2 | Observability | Canonical `data_generation_runs` dead since 05-16; 13 stuck "running" | DB #14 | Decommission or revive; clear stuck rows; add monitoring | no stuck runs | code | M | – | – | – | YES |
| B17 | P2 | Repo hygiene | 413 untracked entries (BACKFILL/ 360+ UUID dirs) | `git status` | `.gitignore` BACKFILL/ scratch/ | clean status | code | S | – | – | – | – |

(TF=TestFlight, AS=App Store, Paid, Pub=Public. "soft"=quality blocker not hard gate.)

---

## D. Product-Truth Contradiction Table

| ID | Surface | Current behavior | Clavix Truth requirement | Evidence | Fix | Pri |
|---|---|---|---|---|---|---|
| T1 | Universe/Search | ETFs absent; "No supported ticker matched VTI"; SPY/VOO unscored | §5 "top 50 ETFs by AUM" are IN v1 | DB #7/#11; sim VTI | Ingest ETFs or scope-limit + hide ETF filter | P0 |
| T2 | Ticker news | AAPL feed shows QQQ/SCHX/SCHG/unrelated; one "no AAPL-related news" | §10 "drop low-relevance articles… not a passing mention" | §F | Relevance filter | P0 |
| T3 | Grade scale | Max grade A; no AA/AAA; KO=BBB | §7 AAA–F; AAA="Treasury-grade… broad-market ETFs, blue chips" | DB #11 | Recalibrate + §7 exclusion | P0 |
| T4 | Composite | Limited news still averaged in | §7 "excluded… composite rescaled to remaining" | DB KO 68.2 | Exclusion logic | P1 |
| T5 | Grades | Single-day grade flips | §7 hysteresis 3-pt/2-day | DB #13 | Implement hysteresis | P1 |
| T6 | Truth doc itself | §6 dim-2 says "Google News RSS for discovery"; §10 says Finnhub override | Internal doc inconsistency | code #24 | Update §6 to Finnhub | P2 |
| T7 | Privacy policy | Names "Plaid or Alpaca"; real = SnapTrade | §11 connect "their brokerage"; accuracy | website #22 | Correct disclosure | P2 |
| T8 | Methodology page | Truth §10 storage says "ONE store `shared_ticker_events`" — implemented ✓ | §10 | DB #6 | none (compliant) | — |
| T9 | Copy | "watch"/"coverage" appear user-visible | §2 banned vocab | B15 | Reword | P2 |
| T10 | Article detail | No "Key Implications" bullets shown | §8/§12 TLDR+What It Means+Key Implications | §F | Render key_implications | P2 |

**Compliant with Truth (verified, no action):** user-visible name is "Clavix" (header wordmark, all copy); tagline usage; brokerage copy says "brokerage" not "SnapTrade"; informational/no-advice disclaimers (app `ClavisCopy.swift`, web footer, Terms §4); five dimensions exactly FIN/NEWS/MAC/SEC/VOL; bond-rating grade labels; one canonical news store; legacy `position_sizing`/`thesis_integrity` not user-visible; manual-add + watchlist mechanics; methodology drill-down is core and works.

---

## E. iOS Screen-by-Screen Audit

| Screen | Source | Data source | DB? | API? | UI shows? | Missing/stale handling | Nav/buttons | Copy/truth | CU-verified? | Blocker |
|---|---|---|---|---|---|---|---|---|---|---|
| Today / Digest | `DigestView.swift`, `DigestViewModel` | `/today`, `digests` | ✅ | ✅ | ✅ $24,754, BB, 5-axis, positions, alerts | digest 2d stale (unlabeled) | all CTAs live | "on watch" banned word | ✅ | B5,B15 |
| Ticker Detail | `TickerDetailView.swift` | `/tickers/{t}`, `/prices`, `/methodology`, `/score-history` | ✅ | ✅ | ✅ grade/5 dims/radar/price/news | price chart transient-empty on 1st load; "1M" shows ~1Y | back works | analyst price-target in brief (news) | ✅ | B3 |
| Methodology drawer | `FinancialHealthAuditView` etc. | `/methodology` | ✅ | ✅ | ✅ ratios, peers, source ts | FCF/Interest "Unavailable" honest | back works | raw ISO ts; "Watch" label | ✅ | B6,B15 |
| Article detail | `ArticleDetailSheet.swift` | bundled in ticker | ✅ | ✅ | ✅ TLDR + What It Means | "—" for missing sentiment (honest) | close works | no Key Implications | ✅ | B3,T10 |
| Search | `SearchView.swift` | `/search` | ✅ | ✅ | ✅ filters, empty states | ETF filter → no match; no Add-manually CTA | tab works | "supported ticker" | ✅ | B4,B13 |
| Settings | `SettingsView.swift` | `/preferences` | ✅ | ✅ | ✅ plan, brokerage, legal | "Version unavailable"; delivery time renders 9:16 PM vs AX 7:00 AM | rows work | — | ✅ | B11 |
| Support & legal | `SettingsView.swift` | static + web | n/a | n/a | ✅ Terms/Privacy/Methodology → Safari | opens web (200) | links work | — | ✅ | — |
| Holdings | `HoldingsListView.swift` | `/positions` | ✅ | ✅ | (positions seen on Today) | — | — | — | partial | — |
| Add holding | `HoldingsListView.swift` | `/positions` POST | ✅ | ✅ | NOT tapped (user at 3/3 Free limit) | upgrade sheet "Pro coming soon" | — | — | ⚠️ UNVERIFIED | — |
| Watchlist | `HoldingsListView.swift` | `/watchlist` | ✅ (7 items, **dup AMD**) | ✅ | NOT tapped | — | — | dup AMD row likely | ⚠️ UNVERIFIED | — |
| Alerts | `AlertsView.swift` | `/alerts` | ✅ (16782, **0 in 2d**) | ✅ | (preview on Today) | stale, unlabeled | — | real grade/news alerts | partial | B5 |
| Paywall / Pro | upgrade sheets | none | n/a | n/a | "Pro is coming soon" → dismiss; no Restore | honest placeholder | dead "View Pro" (dismiss) | — | code-verified | B1 |
| Onboarding | `OnboardingContainerView.swift` | `/preferences` | ✅ | ✅ | NOT shown (session persisted) | — | brokerage step present | "Connect your brokerage" | ⚠️ UNVERIFIED | — |
| Sign in/up | `LoginView`, `AuthViewModel` | Supabase Auth | ✅ | ✅ | NOT shown (session persisted) | — | — | — | ⚠️ UNVERIFIED | — |

---

## F. Computer-Use / Simulator UI Test Results

**Available:** YES — Xcode build/run + Computer-Use (Simulator). **Device:** iPhone 17, iOS 26.3 (`22AE0AD5…`). **Build:** `build_run_sim` succeeded, app launched crash-free. **Auth:** a persisted Supabase session resolved to real user `7ff5a6c5…` (holdings AMD/AAPL/SMCI) — so authenticated flows ran on **live production data**. (A short-lived HS256 token was minted from the local JWT secret and confirmed prod data independently.)

**Tested tap paths & results:**
1. **Launch → Today.** Real: Portfolio **$24,754**, +$45.07, grade **BB**, Composite 58; five-axis FIN76/NEWS65/MAC41/SEC68/VOL39; sectors SOXX/XLK; real alerts (SMCI Pomerantz, AMD Taiwan); positions SMCI B−16 / AMD BB−14 / AAPL A+5; "What to Watch" prose. ✅ "CLAVIX" wordmark. ⚠️ Narrative says "keep the rest of the book **on watch**" (banned vocab).
2. **Today → tap AAPL → Ticker Detail.** ✅ Good loading-state copy → loaded: grade A/71, radar, "YOU HOLD 1 sh +212.1%", LAST $312.08, key-drivers narrative, dims FIN62/NEWS45/MAC84/SEC82/VOL82 (exact DB match). ⚠️ Price chart first showed **"Price history unavailable"** then rendered after return (transient first-load). ⚠️ "1M" selector shows ~1-year range / +54.71% (window mislabel). ❌ **Recent news polluted with off-ticker articles** (QQQ, SCHX, SCHG, Porch Group, Josh Brown); one TLDR: *"no substantive content… or any AAPL-related news."* Several sentiment scores "—".
3. **Ticker → tap FIN dimension → Methodology audit.** ✅ Score 62/BBB, Finnhub timestamp, ratio table (D/E 1.35, Current 0.89, Rev Growth "Positive 3Q", Profitability "Improving"), peers MSFT/ORCL/PLTR/IBM/SNDK. ❌ **FCF Margin & Interest Coverage = "Unavailable"** (2/6 inputs missing → depresses Apple's FIN). ⚠️ Raw ISO timestamp; "Watch" status label (banned).
4. **Back → tap article → Article brief sheet.** ✅ Title, BRIEF (TLDR), RISK SIGNAL (What It Means) with "—" for missing sentiment, "Read full article at Yahoo →". ⚠️ No "Key Implications". Back/close ✅.
5. **Search tab.** ✅ Empty states honest ("Tickers you open will appear here", "Trending… once enough activity captured"). Quick filters incl. **ETFs**.
6. **Search → ETFs filter (auto "VTI").** ❌ **"No supported ticker matched 'VTI'. Try a different ticker symbol or company name."** No Add-manually CTA.
7. **Settings.** ✅ Plan **Free**, Brokerage "Not connected", Methodology "Open", Export data, **Delete account**, Sign out. ❌ **"Version unavailable."** ⚠️ Delivery time renders "9:16 PM" (AX value "7:00 AM"). ❌ No Restore Purchases; no dedicated upgrade entry.
8. **Settings → Support & legal.** ✅ Email (support), Status "Online", Terms/Privacy/Methodology. **Terms → opens Safari web view** (legal pages live, 200).

**Broken/misleading found:** off-ticker news (B3); ETF dead-end (B4); "Version unavailable" (B11); transient empty price chart + window mislabel; banned "watch"/"coverage" copy; raw timestamp.
**Broken CTAs:** "View Pro" (HoldingsUpgradeSheet) only dismisses (acceptable pre-monetization).
**Could not test (UNVERIFIED):** Onboarding, Sign-in/up, Add-holding, Watchlist add/remove, CSV import, offline/airplane, small device, Dynamic Type, dark mode, force-quit relaunch.

---

## G. Backend / API Endpoint Audit

| Endpoint | Source | Auth | iOS consumer | Tables | Sample | Risk | Latency | Issue/Fix | Verify |
|---|---|---|---|---|---|---|---|---|---|
| `/health` | `main.py` | none | — | — | 200 ok | low | 141ms | apns missing (B2) | curl |
| `/tickers/{t}` | `routes/tickers.py` | JWT | TickerDetail | ticker_metadata, snapshots, events | 200 full | event-loop pattern unaudited | ~fast | confirm `to_thread` | curl+token |
| `/prices/{t}` | `routes/prices.py` | JWT | chart | prices | 200 real bars | fixed this week (to_thread) | <1s | none | curl ✅ |
| `/tickers/{t}/methodology` | `routes/methodology.py` | JWT | drill-down | snapshots | 200 | fixed this week (to_thread) | 1-2s | none | sim ✅ |
| `/tickers/{t}/score-history` | route | JWT | chart | snapshots | 200 | dup snapshots/day | <1s | dedupe (B9) | sim ✅ |
| `/today` | `routes/today.py` | JWT | Today | digests, positions, snapshots | populated | **stale digest (05-28)**; event-loop unaudited | — | B5; audit to_thread | sim ✅ |
| `/search` | route | JWT | Search | ticker_universe | works; no ETFs | B4 | — | relevance/ETF | sim ✅ |
| `/positions` `/watchlist` | routes | JWT | Holdings | positions, watchlist_items | dup AMD in watchlist | data dedupe | — | clean dup | DB |
| `/alerts` | route | JWT | Alerts | alerts | stale (0/2d) | B5 | — | regen | DB |
| `/brokerage/*` | routes | JWT | Brokerage | positions | snaptrade configured | hidden-at-launch ok | — | gate to Pro | health |
| StoreKit/receipt validation | **none** | — | — | — | — | **MISSING** | — | B1 | — |
| APNs register | present | JWT | — | — | `apns:missing` | B2 | — | deploy p8 | health |

**Pattern risk:** memory + this audit flag that `portfolio.py`, `today.py`, `dashboard.py`, `analysis_runs.py` were not audited for the `asyncio.to_thread` event-loop fix that already produced two P0s this week. Audit before TestFlight.

---

## H. Database / Data-Freshness Audit

**Canonical tables (in use):** `ticker_universe`(504), `ticker_metadata`(508), `ticker_risk_snapshots`(22,772), `shared_ticker_events`(29,438 — the ONE news store ✓), `positions`(509: 504 belong to system user `0000…0001` scoring-anchor + 3+2 real), `watchlists`/`watchlist_items`(7, **dup AMD**), `digests`(179), `alerts`(16,782), `prices`(40,738), `user_preferences`(3), `scheduler_jobs`(3), `peer_groups`, `sector_medians`, `macro/sector_regime_snapshots`.

**Legacy/abandoned:** `news_items`/`ticker_news_cache` — **gone (retired ✓)**. `data_generation_runs`(143; **dead since 2026-05-16**, 35 failed, **13 stuck "running"**) + `data_generation_run_items`(4,093) — the "canonical controller" is abandoned; the active scoring path is `analysis_runs`/`job_runs`/scheduler. `etf_holdings`(**0 rows**), `refresh_attempts`(0).

**Freshness:** ticker snapshots **fresh** (latest 2026-05-30, 503/504 tickers). News **fresh** (newest article 2026-05-30 21:18). **Digests stale (05-28).** **Alerts stale (0 in 2d).**

**Governance columns unused:** `is_product_visible`, `verification_status`, `data_status`, `writer_source`, `generated_at`, `stale_after` are **NULL across all latest snapshots** (the dead canonical controller was meant to set them). The API ignores them, so UI still works — but there is **no verified/published gate** and **no freshness fields** backing any "fresh"/"stale" label.

**Sample-ticker evidence (latest snapshot per ticker, 2026-05-30):**

| Ticker | Price | Fund. | News 7d | ≥3 art | TLDR | FIN | NEWS | MAC | SEC | VOL | Comp | Grade | Hist | gen_at | stale_after | Limited | Blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AAPL | ✅ $312 | partial (FCF/IntCov missing) | 10 | yes | yes | 62 | 45 | 84 | 82 | 82 | 71.0 | **A** | 8+ days | NULL | NULL | [] | B3 news off-ticker |
| MSFT | ✅ | partial | yes | yes | yes | 72 | 61 | 77 | 81 | 82 | 74.6 | **A** | yes | NULL | NULL | [] | grade ceiling |
| NVDA | ✅ | ok | yes | yes | yes | 76 | 50 | 54 | 78 | 65 | 64.6 | BBB | yes | NULL | NULL | [] | — |
| WMT | ✅ | partial | yes | yes | yes | 66 | 61 | 99 | 74 | 76 | 75.2 | **A** | yes | NULL | NULL | [] | best name still only A |
| JNJ | ✅ | partial | <3 | no | — | 68 | 49 | 93 | 68 | 81 | 71.8 | **A** | yes | NULL | NULL | news_sentiment | B7 |
| KO | ✅ | partial | <3 | no | — | 64 | 37 | 91 | 67 | 82 | 68.2 | **BBB** | yes | NULL | NULL | news_sentiment | B6/B7 (should be A) |
| BRK.B | ✅ | partial | <3 | no | — | 72 | 48 | 94 | 69 | 85 | 73.6 | **A** | yes | NULL | NULL | news_sentiment | B7 |
| **SPY** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | **ABSENT (B4)** |
| **VOO** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | **ABSENT (B4)** |

**Pipeline reliability:** active ticker-scoring cron works (fresh daily snapshots, `job_runs` 21 completed/3d but **7 failed**). User-facing digest+alert cron stalled 05-28→present (fix deployed, unverified). Duplicate snapshots/day (daily + forced manual_refresh) disagree on grade → ambiguity (B9). Production==the only DB checked (no separate local prod mismatch found).

**Fake/fallback risk:** Score deltas verified **real** (AAPL +5 from real prior snapshot). No fabricated "was X". No headline-only flagged-as-full (headline_only=0 but ~30% lack body — extraction gap, not fakery). Real alerts (grade/news), not demo. **The mock `ClavixVisualQA` data (fake scores, "Google News RSS" string) is DEBUG-only and unreachable in release.**

---

## I. News / Provider Audit

| Provider | Role | Status | Evidence |
|---|---|---|---|
| **Finnhub** | **Primary ticker news discovery (7-day, per-ticker)** | ✅ Active, canonical | `backend/app/pipeline/finnhub_news.py` "Primary news source… main entry point" |
| Google News RSS | Auxiliary/fallback (URL decode, fallback ingest) | present, not primary | `google_news_decoder.py`, `rss_ingest.py`, `GOOGLE_FALLBACK_ENABLED` flag |
| Jina/trafilatura/newspaper | Body extraction | present (extraction path) | `news_enrichment.py` |
| **Polygon** | Prices, bars, options snapshot, macro factor ETFs | ✅ Active | `polygon.py`, `polygon_options.py`; macro now uses TLT/VIXY ETFs |
| **MiniMax** | LLM (sentiment, TLDR, narratives, digest) | ✅ Active (`minimax:configured`) | `news_enrichment.py`, `personalisation.py`, `/health` |

**Findings:**
- **Doc-truth conflict:** Truth **§6 dimension-2 still says "Google News RSS for discovery → Jina"** while **§10 has the 2026-05-24 Finnhub override**. Code proves **Finnhub is primary**. → Update Truth §6 to match §10 (B/T6).
- **Relevance filter NOT working** (B3): Finnhub `company_news` returns articles that mention a ticker in passing (e.g., AAPL as a top holding in QQQ/SCHX) and they are stored + displayed as that ticker's news. Truth §10 requires dropping low-relevance.
- **Coverage shallow:** only 196/504 tickers have any news in 7d; 144 have ≥3 → 71% of universe shows News "Limited Data".
- **TLDR/What-It-Means missing on ~40%** of articles; `headline_only` flag never set despite ~30% lacking body.
- Rate-limit/failure handling: index-ticker 403 cooldown bug already fixed this week (TLT/VIXY). No new provider-failure cascade observed; `/health` shows providers configured.
- No provider name leaks to users except the mock VQA (debug-only) string "Google News RSS → Jina → MiniMax" — not shipped.

---

## J. App Store / Admin Checklist

**Apple (needed before TestFlight unless noted):**
- [ ] Complete Apple Developer enrollment (pending, under parent) — **gates everything**
- [ ] Accept Paid Apps + Free Apps agreements (paid: before charging)
- [ ] Create App Store Connect app record (bundle `com.clavisdev.portfolioassistant`)
- [ ] App name "Clavix", subtitle "Portfolio risk, measured." (≤30), category Finance
- [ ] Age rating questionnaire (likely 17+ финance; app self-declares 18+)
- [ ] Privacy nutrition labels (data: email/auth, holdings, usage; no tracking/ATT — session cookies only per policy)
- [ ] Export compliance (uses HTTPS only → standard exemption answer)
- [ ] Signing: distribution cert + provisioning profile (auto-managed ok)
- [ ] Screenshots 6.9"/6.5" (+ iPad if "iPhone only" not set) — **none exist yet**
- [ ] App icon 1024 (verify `clavix_logo`/AppIcon asset present — `ClavynxMark` falls back to bars if missing)
- [ ] App Review demo account (test user + seeded holdings) + Review Notes (informational, not advisory; brokerage hidden)
- [ ] StoreKit products `clavix_pro_monthly` ($19.99) + 14-day intro offer; subscription group (before charging)

**User/adult/legal:** parent owns dev account + accepts agreements + banking/tax (W-9/W-8) + seller name (mismatch with "Clavix"/"Andover Digital LLC" — decide acceptable); who receives payouts/legal/support email.

**Needed for:** Simulator=none Apple; TestFlight=enrollment+record+build+demo acct; App Store=+screenshots+metadata+age+privacy labels+review notes; Charging=+StoreKit products+Paid Apps agreement+banking/tax.

---

## K. StoreKit / Monetization Checklist

**Current state: NOT IMPLEMENTED.** No `import StoreKit`, no `.storekit` config, no product IDs; tier is read-only from backend `subscription_tier` (always "free" for test users); upgrade sheets = "Pro is coming soon" → dismiss; **no Restore Purchases button** (Apple-required for paid).

| Item | Status | Needed for |
|---|---|---|
| Product IDs `clavix_pro_monthly` ($19.99) [+ optional annual] | ❌ | charging |
| Subscription group | ❌ | charging |
| 14-day intro/free trial | ❌ (Truth §16) | charging |
| Purchase flow (StoreKit 2 `Product.purchase`) | ❌ | charging |
| Transaction listener / entitlement → backend sync | ❌ | charging |
| Restore Purchases | ❌ | App Store **required** |
| Expired/grace handling | ❌ | charging |
| Server receipt validation / `subscription_tier` write | ❌ (backend gates on tier but nothing sets it via Apple) | charging |
| Free/Pro gates | ⚠️ UI-only (3-holding limit, verbose digest) — not backend-enforced | charging |
| App Review can test Pro | ❌ (no purchase + no comp path) | App Store |
| Local `.storekit` matches ASC product IDs | ❌ | sandbox |

**Free vs Pro behavior today:** App fully usable Free (3 holdings, 5 watchlist intent, standard digest). Pro features (verbose digest, brokerage, CSV) are gated to "coming soon". **Acceptable for free TestFlight; full StoreKit is the paid-launch long pole.**

---

## L. Website / Brand / Legal Checklist

**Website (`getclavix.com`):** `/`, `/terms`, `/privacy`, `/methodology` all **200** ✅; `/support` 404 (support is email). Landing copy: no Clavis/SnapTrade; buy/sell only as disclaimers; pricing "$20/month after trial" + "14-day Pro trial, no card" ✅ matches Truth. Repo `web/` holds only `index.html`+`confirm.html` (legal pages deployed outside repo — source not auditable here).

**Legal (live):** Privacy + Terms professionally drafted; "Clavix"/"Andover Digital LLC"; 18+; "No Investment Advice" (Terms §4); AS-IS, liability cap, indemnity, arbitration; account/data deletion implemented in-app ✅.
- ⚠️ **Privacy names "Plaid or Alpaca" as brokerage processor — real integration is SnapTrade** (B14). Correct before any brokerage feature ships.
- ⚠️ Website advertises a **paid Pro tier + trial the app can't yet deliver** (no StoreKit) — fine pre-launch, misaligned at public launch.

**Brand:** "CLAVIX" wordmark in-app ✅; credit-rating aesthetic (cream/serif) ✅; `clavix_logo` asset referenced (verify present, else fallback bars). Internal type names `ClavisDesignSystem`, `ClavynxMark`, `ClavisApp` — **allowed (internal-only, render the logo, not text)**.

| Asset | Before TestFlight | Before App Store | Before public |
|---|---|---|---|
| Legal pages live | ✅ done | ✅ | ✅ |
| App Store screenshots | — | **required** | required |
| App preview video | — | optional | nice |
| Brand kit / press | — | — | nice |
| Support email working | verify `support@getclavix.com` | required | required |

---

## M. Observability / Security / Reliability Checklist

**Observability — mostly MISSING:**
- No crash reporting (no Sentry/Crashlytics found), no analytics, no error monitoring in iOS.
- Backend: `job_runs`(45) + `analysis_runs` give some history; **no alerting on failed jobs** (7 failed/3d unnoticed; digest/alert stall went 2 days unnoticed).
- No data-freshness dashboard; "canonical" `data_generation_runs` controller dead (13 stuck "running") — misleading if used for monitoring.
- **How you'd know tomorrow if overnight worked:** only by manual SQL (see §T). Add automated checks.

**Security:**
- ✅ RLS enabled on all user tables; ✅ service-role key backend-only; iOS ships only the **anon** key (verify it's the intended publishable key, `APIService.swift:4-15`).
- ❌ **anon role can EXECUTE `save_daily_asset_safety_profile` + `save_daily_macro_regime` (SECURITY DEFINER)** via REST RPC — an attacker with the shipped anon key could overwrite risk scores / macro regime. Migration `supabase/migrations/20260530_security_fixes.sql` exists but **is NOT applied** (advisor confirms). **Apply before App Store/paid (B10).**
- ⚠️ `gnews_wrapper_resolution`, `waitlist_signups`, `data_generation_run(_items)` RLS-enabled-no-policy (deny-all is safe for internal, but gnews intended to have a policy per migration).
- ⚠️ Leaked-password protection OFF; ⚠️ 2 functions mutable search_path; ⚠️ citext in public schema.
- ✅ HTTPS only (ATS `trycloudflare` exception removed this week). ✅ JWT validated (sig+exp) server-side.

**Reliability:** single VPS + Cloudflare Tunnel (no documented failover); no backup/restore runbook found beyond Supabase defaults; no rollback plan; `PROD_SSH_KEY` GitHub Actions secret not set (push-to-deploy broken — manual SSH only).

---

## N. Before TestFlight (hard blockers only)

- [ ] **B2** Apple Developer enrollment complete + App Store Connect record (external)
- [ ] **B5** Confirm 2026-05-31 morning digest **and** alerts actually generate (pipeline was stalled since 05-28) — or testers see a 3-day-old "Today"
- [ ] Archive build signed with distribution profile; confirm prod backend URL baked in (✅ `Secrets.xcconfig`)
- [ ] Seed/confirm the demo/test account has fresh holdings + digest
- [ ] (Strongly recommended, soft) **B3** news relevance + **B4** ETF dead-end — beta testers WILL search SPY and open AAPL news

Everything else (StoreKit, screenshots, security migration) is NOT a hard TestFlight gate for a free closed beta.

## O. Before App Store Submission

- [ ] All of §N
- [ ] **B3** news relevance fixed (quality; review-visible)
- [ ] **B4** ETF coverage OR explicit scope-limit (hide ETF filter, label universe)
- [ ] **B10** apply security migration (anon RPC write)
- [ ] **B11** fix "Version unavailable"; **B12** populate generated_at/stale_after
- [ ] Screenshots, subtitle, age rating, privacy nutrition labels, export compliance, review notes + demo account
- [ ] **B6/B7** grade calibration (Apple won't reject, but blue-chips-as-BBB undermines the pitch)

## P. Before Charging Money (Paid Launch)

- [ ] **B1** Full StoreKit 2: products, purchase, restore, entitlement→backend sync, expired/grace
- [ ] Backend enforces Pro gates server-side (not UI-only)
- [ ] `clavix_pro_monthly` $19.99 + 14-day intro in ASC; `.storekit` matches; sandbox tested
- [ ] Paid Apps agreement + banking + tax forms (parent)
- [ ] App Review can exercise Pro (comp account or testable trial)
- [ ] Website pricing matches StoreKit reality

## Q. Before Public Launch

- [ ] All paid-launch items + **B8** hysteresis + **B9** snapshot dedupe + **B16** controller cleanup
- [ ] Crash reporting + failed-job alerting + freshness dashboard (§M)
- [ ] **B14** privacy sub-processor accuracy; DMARC/SMTP for transactional email
- [ ] News coverage depth (so most holdings have real News dimension, not "Limited Data")

---

## R. User / Admin Tasks (cannot be solved in code)

- [ ] Apple Developer enrollment under parent; accept Free + Paid Apps agreements
- [ ] Decide seller name / brand mismatch acceptability (Andover Digital LLC vs Clavix)
- [ ] Banking (Mercury) + EIN doc (147C if lost) + Apple tax/banking forms
- [ ] Business/support email (`support@getclavix.com`) deliverability; DMARC/SMTP DNS
- [ ] App Store screenshots/metadata/age-rating/privacy-label answers (you provide content/decisions)
- [ ] Confirm who owns prod secrets, receives payouts, handles support
- [ ] Apply Supabase security migration (dashboard) + toggle leaked-password protection
- [ ] Set GitHub `PROD_SSH_KEY` (or accept manual deploy)

## S. Claude / Code Tasks

- [ ] B1 StoreKit; B3 news relevance filter; B4 ETF ingestion/scope; B5 verify+harden digest/alert scheduler; B6/B7 grade calibration + limited-data exclusion; B8 hysteresis; B9 snapshot dedupe; B11 version string; B12 generated_at/stale_after; B13 Add-manually CTA; B15 copy sanitizer; B16 controller cleanup; B17 .gitignore
- [ ] Audit `portfolio.py`/`today.py`/`dashboard.py`/`analysis_runs.py` for `asyncio.to_thread` (event-loop P0 pattern)
- [ ] Add crash reporting + failed-job alerting + freshness dashboard
- [ ] Update Truth §6 (Finnhub, not Google RSS); correct privacy sub-processor copy

---

## T. Tomorrow-Morning Manual QA Checklist (copy/paste)

**A. Overnight pipeline health (run first — SQL in Supabase or via API):**
- [ ] `SELECT max(generated_at) FROM digests;` → **must be 2026-05-31** (else digests still stalled = blocker)
- [ ] `SELECT count(*) FROM alerts WHERE created_at >= now() - interval '1 day';` → **> 0** expected
- [ ] `SELECT max(snapshot_date) FROM ticker_risk_snapshots;` → **2026-05-31**
- [ ] `SELECT status,count(*) FROM job_runs WHERE started_at>=now()-interval '1 day' GROUP BY status;` → mostly completed, note failures
- [ ] `curl -s https://clavis.andoverdigital.com/health` → `200`, providers configured
- [ ] **Overnight succeeded =** fresh digest + fresh snapshots + alerts firing. **Partial =** snapshots fresh but digest/alerts stale. **Blocker =** digest still 05-28.

**B. iOS spot-check (force-quit first):**
- [ ] Open app — does NOT crash; lands on Today
- [ ] Today: screenshot; check date/time is today; portfolio value + grade present; **is the digest dated today?**
- [ ] Tap every position card → ticker detail opens → back works
- [ ] Tap a dimension row → methodology drawer → back
- [ ] Open a news article → TLDR + What It Means show → close. **Are the articles actually about THIS ticker?** (flag off-ticker)
- [ ] Search "AAPL", "MSFT", "NVDA" → results → open one
- [ ] Search "SPY" / "VOO" → note "no supported ticker" (expected ETF gap)
- [ ] Holdings tab → tap "Add" → note Free-limit "Pro coming soon"
- [ ] Watchlist → is **AMD duplicated**? remove/add works?
- [ ] Alerts tab → are alerts dated today or 2+ days old?
- [ ] Settings → Plan, Methodology opens, **does it still say "Version unavailable"?**, Support&Legal → Terms/Privacy open
- [ ] Settings → Morning Report → Length → Verbose → paywall sheet appears; "Pro coming soon" dismisses
- [ ] Note: dead buttons / missing data / stale data / fake data / bad copy ("watch", "coverage")

**What counts as:** *Broken* = crash, dead CTA, blank where data expected. *Missing data* = "—"/empty with no honest label. *Stale* = digest/alerts older than this morning. *Fake* = a number with no DB backing (none found so far). *Ignore* = pure visual taste (spacing/font).

---

## U. Recommended Next Prompt (after reading this report)

> "Phase 1: Start fixing the P0 launch blockers in dependency order, one at a time, verifying each against production/simulator before moving on. Do NOT touch polish until P0s are verified. Order:
> 1. **B5** — confirm the 05-31 digest+alerts actually generated; if not, fix the scheduler and re-trigger; show me fresh `digests`/`alerts` rows dated today.
> 2. **B3** — implement the Truth §10 ticker-relevance filter so AAPL/MSFT/NVDA news contains only on-ticker articles; re-score affected News dimensions; show me AAPL's news list before/after.
> 3. **B6/B7** — apply the Truth §7 limited-data exclusion + rescale, and fix Financial Health missing-input handling; show the new grade distribution and prove KO/JNJ/blue-chips can reach AA/AAA.
> 4. **B4** — decide ETF scope with me: either ingest top-50 ETFs (+`etf_holdings`) or hide the ETF filter and relabel the universe; whichever, no dead-end.
> 5. **B10** — apply the security migration and re-run `get_advisors`.
> After each, run the relevant verify_*.py + a live API/DB check and report evidence. Then re-assess TestFlight go/no-go. Leave StoreKit (B1) for a dedicated paid-launch workstream once the data-truth P0s are clean."

---

*End of audit. No product code, migrations, web, iOS, backend, config, or non-report docs were modified in Phase 0.*
