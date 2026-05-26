# Agent Handoff — Clavix iOS Hi-Fi v2 Parity Build

**You are the next agent on this build.** This is a deep, autonomous, multi-cycle visual-parity job: drive the iOS simulator, screenshot every screen, diff against the canonical Hi-Fi v2 mockup, patch the SwiftUI, rebuild, re-screenshot, loop. Keep going until each screen matches the mockup pixel-for-pixel (or as close as SwiftUI allows). You have ~7 hours of context. Spend it.

This document is **load-bearing**. Read it top to bottom before touching anything. Re-read the *Critical rules* section before every commit.

---

## 0. Critical rules — break any of these and the build degrades

1. **The Hi-Fi v2 HTML is the only design source of truth.** It lives at `docs/design/clavix-hifi-v2.html` and is bundled inside the iOS app at `ios/Clavis/Resources/Design/clavix-hifi-v2.html`. Boot the sim with `CLAVIX_USE_HIFI_REFERENCE=1` to see it. Do **not** consult `ClavixVisualQA.swift` for visual decisions — it's a stale earlier copy of the same design intent. Use it only to crib *atom layouts* (VQACard, VQAGrade, etc.) which were already extracted into `ClavixVQAComponents.swift`.

2. **`docs/CLAVIX_TRUTH.md` is the product source of truth.** When the HTML mockup and CLAVIX_TRUTH disagree, CLAVIX_TRUTH wins. The HTML drives *visuals*; CLAVIX_TRUTH drives *what the product is and isn't*. Banned vocabulary, the five-dimension methodology, the bond-rating grade scale, the "informational not advisory" stance — all come from CLAVIX_TRUTH §2, §6, §7, §10.

3. **The five dimensions are fixed: Financial Health, News Sentiment, Macro Exposure, Sector Exposure, Volatility.** Equal-weight composite. Never four. Never six. Never invent a sixth like "thesis integrity" — those are deprecated legacy fields.

4. **Never fabricate previous scores or deltas.** If `score_delta == nil`, render `—` or `New`. Never display `current − 8` or any synthetic value. CLAVIX_TRUTH §8 is explicit.

5. **User-visible brand is Clavix.** Internal types/dirs (`ClavisDesignSystem`, `ClavisTypography`, `ClavisCopy`, `ios/Clavis/`, etc.) stay as `Clavis*` — too risky to rename. But every user-facing string says "Clavix". Banned UI strings: `Clavis`, `Clavynx`, `SnapTrade`, `MiroFish`, raw backend statuses via `.capitalized`. Banned vocabulary: coverage, monitor, momentum, analyst, research, thesis, provisional, current read, recommendation, suggest, advise, predict, forecast.

6. **Never commit unless the task is in a known-good state (build passes, no obvious crashes).** Commit messages must use the Claude Code conventional footer. Push to `main` triggers GitHub Actions deploy — but the deploy job needs `PROD_SSH_KEY` secret which is currently missing, so the action fails. Use the manual rsync path (§7) to deploy.

7. **Backend is live on a DigitalOcean VPS at `clavix-backend@134.122.114.241`**, behind Cloudflare Tunnel `clavix-prod` at `https://clavis.andoverdigital.com`. SSH key is `~/.ssh/clavix_vps_ed25519`. The `/opt/clavis` directory there mirrors the repo. **You can deploy backend changes manually.**

8. **Do not break the live run if one is in progress.** Always check `analysis_runs` in Supabase before applying migrations or restarting the backend container. The user runs ~daily backfills of the full S&P 500.

---

## 1. The autonomous parity loop — exactly how to run it

This is the loop. Repeat until the user says stop.

```
LOOP:
  1. Launch the live app:
       mcp__xcode__stop_app_sim()
       mcp__xcode__install_app_sim(appPath="/Users/sansarkarki/Library/Developer/Xcode/DerivedData/Clavis-gwrxdzeojwrjhbglmivjzniaqokb/Build/Products/Debug-iphonesimulator/Clavis.app")
       mcp__xcode__launch_app_sim()
       Bash: sleep 8

  2. Tap the next tab to inspect (Today, Holdings, Search, Alerts, Settings):
       mcp__xcode__tap(label="Today")
       Bash: sleep 4

  3. Snapshot the live screen:
       mcp__xcode__screenshot(returnFormat="path")
       Read(<path>)  # multimodal — actually look at the pixels

  4. Launch the HiFi reference:
       mcp__xcode__stop_app_sim()
       mcp__xcode__launch_app_sim(env={"CLAVIX_USE_HIFI_REFERENCE":"1"})
       Bash: sleep 4
     Scroll to the matching section using:
       mcp__xcode__swipe(x1=200, y1=600, x2=200, y2=100, duration=0.3)   # scroll up
     Repeat until you find the section that maps to the tab you're inspecting.

  5. Snapshot the HiFi reference:
       mcp__xcode__screenshot(returnFormat="path")
       Read(<path>)

  6. Diff the two images mentally. List every divergence:
       - colors (often legacy .textPrimary leak)
       - font (mono vs serif vs Inter)
       - spacing/padding/line-height
       - corner radius (cards 10, controls 6/7, badges 3/4)
       - badge sizing / typography
       - missing or extra elements

  7. Open the SwiftUI file for that tab and patch each divergence. Use the
     clavix* tokens from ClavixDesignTokens.swift. Use the atoms from
     ClavixVQAComponents.swift (ClavixCard, ClavixGradeBadge, ClavixPill,
     ClavixSection, ClavixLargeHeader, ClavixEyebrow, ClavixColumnHeader,
     ClavixMiniSpark, ClavixScoreBar, ClavixTabBar).

  8. Build:
       mcp__xcode__build_sim()
     If error, fix and rebuild.

  9. Goto step 1. Verify the live screen now matches.

 10. Every 3-5 successful screens, commit + push:
       Bash: git add -A && git commit -m "..."  && git push origin main
     Push to main does NOT deploy backend currently — only commit ios/* and
     docs/* unless you have backend changes. Manual deploy if needed (§7).
```

### Tap-targeting tips
- Use `mcp__xcode__snapshot_ui()` first if the UI tree is unclear. It returns AXLabel/AXUniqueId/coordinates for every element. Tap with `label="Holdings"` instead of raw coords when possible — labels survive layout changes.
- The five tabs in MainTabView are at y=800 (iPhone 17): Today ≈ x=40, Holdings ≈ x=120, Search ≈ x=200, Alerts ≈ x=283, Settings ≈ x=362. But always use `label="<tab>"` — it's more robust.
- The HiFi reference is a single long-scrolling document. Use repeated swipes (delta=400, duration=0.3) to navigate. There's no internal nav.

### Build/install dance
- `mcp__xcode__build_sim()` compiles to `~/Library/Developer/Xcode/DerivedData/Clavis-gwrxdzeojwrjhbglmivjzniaqokb/Build/Products/Debug-iphonesimulator/Clavis.app`.
- After every build, you **must** `install_app_sim(appPath=…)` then `launch_app_sim()` for the simulator to see new code. `launch_app_sim()` alone re-runs the *installed* binary, which is stale.
- After bundling new resources (e.g. fonts, HTML) or changing `project.yml`, run `cd ios && xcodegen generate` first.

---

## 2. The codebase — where things live

### iOS (`ios/Clavis/`)

| Path | What it does |
|---|---|
| `App/ClavixApp.swift` | App entry, deep-link handling |
| `App/ContentView.swift` | Auth gate + debug toggles (`CLAVIX_USE_HIFI_REFERENCE`, `CLAVIX_USE_VQA_MOCK`) |
| `App/MainTabView.swift` | Live tab shell; UITabBar.appearance configured to cream/paper |
| `App/ClavisDesignSystem.swift` | Legacy dark-theme tokens + shared atoms (DashboardErrorCard, ClavisLoadingCard live here, both rebuilt with clavix tokens). **Do NOT add new dark-theme color references.** |
| `App/ClavixDesignTokens.swift` | **Hi-Fi v2 cream/paper palette + typography** — single source of color truth. Derived from `cx` object in HTML. |
| `App/ClavisCopy.swift` | User-facing copy strings + status translation. titleCase fallback returns "Updating" — never raw status. |
| `App/ClavixVisualQA.swift` | Static design canon, `#if DEBUG`. Useful for atom shapes; do NOT use for visual decisions. |
| `Views/Shared/Components/ClavixVQAComponents.swift` | Production atoms (ClavixCard, ClavixSection, ClavixGradeBadge, ClavixPill, ClavixColumnHeader, ClavixMiniSpark, ClavixScoreBar, ClavixTabBar). |
| `Views/Shared/ClavixHiFiReferenceView.swift` | WKWebView that loads bundled HiFi HTML. Triggered by env var. |
| `Views/Digest/DigestView.swift` | Today tab (cream summary). Hero, MorningReport card, five-axis, sector heat, attention, top movers, calendar. |
| `Views/Digest/MorningReportView.swift` | Full prose digest pushed from Today's Morning Report card. |
| `Views/Holdings/HoldingsListView.swift` | Holdings tab. 4-column ledger (Sym·w% / Last·day / P&L / Grade·Δ), toolbar pills, ledger header bar. |
| `Views/Search/SearchView.swift` | Search tab. VQASearchHeader-style sticky header, Recent / Trending / Browse sections, live results. |
| `Views/Alerts/AlertsView.swift` | Alerts tab. Day groups, filter chips with counts, VQAAlertCenterRow with unread accent strip. |
| `Views/Settings/SettingsView.swift` | Settings tab. settingsGroup helper + ClavixCard sections. |
| `Views/Tickers/TickerDetailView.swift` | Ticker detail (hero, 5 dimensions, drivers, news, score history, outside-universe banner). |
| `Views/Tickers/MethodologyDrawerSheet.swift` + `*AuditView.swift` | Methodology drill-down. All five (Financial Health, News, Macro, Sector, Volatility). |
| `Views/Tickers/ArticleDetailSheet.swift` | Per-article reader. |
| `Views/Tickers/ScoreHistoryChart.swift` | Score history line chart + HeroPriceSparkline + HeroScoreSparkline. |
| `Views/Tickers/TickerDriverCardsSection.swift` | Driver cards for Ticker Detail. |
| `Views/Auth/LoginView.swift` | Sign in / sign up. |
| `Views/Onboarding/OnboardingContainerView.swift` | Onboarding flow. |
| `Models/Position.swift` | Position payload from /holdings. Has `sharedAnalysis` (SharedTickerAnalysisSummary). |
| `Models/SharedTickerAnalysis.swift` | Position summary with v2 fields: latestPrice, previousClose, dayChangeAmount, dayChangePct, riskDimensions, isSupported, outsideUniverse. Custom decoder, nil-safe. |
| `Models/Alert.swift` | Alert payload with v2 fields: severity, destination_type, destination_id, read_at (when backend sends). |
| `Models/Digest.swift` | Digest with structuredSections (header, overnightMacro, sectorHeat, positions, watchlistUpdates, whatToWatchToday). |
| `Models/PortfolioMath.swift` | Value-weighted composite/grade helper used by Today + Holdings. |
| `Models/ScoreHistory.swift` | ScoreHistoryPoint + ScoreHistoryResponse + TodayResponse envelope + ScoreHistoryConversion. |
| `Services/APIService.swift` | All backend HTTP. Default timeout 30s. Per-call overrides for digest (75s), score-history (30s), etc. |
| `Services/SupabaseAuthService.swift` | Session, JWT refresh, deep-link callback. |
| `ViewModels/*ViewModel.swift` | One per major view. Load data, expose published state. |

### Backend (`backend/app/`)

| Path | What it does |
|---|---|
| `main.py` | FastAPI app, middleware, route registration. |
| `config.py` | Settings via env. `.env` at `backend/.env` (gitignored). |
| `routes/today.py` | `GET /today` — composite envelope. Read-only. |
| `routes/tickers.py` | `/search`, `/{ticker}`, `/{ticker}/refresh`, `/{ticker}/score-history`. |
| `routes/methodology.py` | `/{ticker}/methodology` — drill-down payload. |
| `routes/holdings.py` | `GET/POST /holdings`. POST accepts `allow_outside_universe`. |
| `routes/alerts.py` | `GET /alerts` envelope, `POST /{id}/read`, `POST /read-all`. |
| `routes/digest.py` | `GET /digest` + history. |
| `routes/preferences.py` | User preferences + alert subtype prefs. |
| `routes/watchlists.py` | Default watchlist + items. |
| `routes/brokerage.py` | SnapTrade connect, status, sync, disconnect. |
| `routes/account.py` | Export, delete. |
| `routes/prices.py` | `GET /prices/{ticker}?days=N`. |
| `services/ticker_cache_service.py` | The big one. `enrich_positions_with_ticker_cache` embeds v2 fields (latest_price, previous_close, day_change_amount, day_change_pct, risk_dimensions, is_supported, outside_universe) on every Position. |
| `services/news_enrichment.py` | LLM article enrichment (TLDR, what_it_means, sentiment_score, etc.). |
| `services/finnhub_prices.py` + `polygon.py` | Price providers. |
| `services/supabase.py` | Service-role client. |
| `pipeline/scheduler.py` | Long-running scheduler, S&P 500 backfill orchestration. |
| `pipeline/sector_snapshot.py` | New: daily sector ETF bars → sector_regime_snapshots. |
| `pipeline/macro_snapshot.py` | New: daily macro factor levels → macro_regime_snapshots. |
| `pipeline/finnhub_news.py` | Per-CLAVIX_TRUTH override, this is the canonical news discovery source. |
| `pipeline/rss_ingest.py` | Google News RSS (auxiliary; not the canonical path). |
| `pipeline/risk_scorer.py` + `structural_scorer.py` | Scoring. Two paths exist; converging to one is a P2 item. |

### Database (Supabase, project `uwvwulhkxtzabykelvam`)

Service-role key in `backend/.env`. Use the `mcp__supabase__*` tools to query. Tables that matter most:

| Table | Notes |
|---|---|
| `positions` | User holdings. Has `outside_universe` column. |
| `ticker_universe` | ~508 supported tickers (S&P 500). |
| `ticker_metadata` | Per-ticker profile. `price` and `previous_close` populated for 506/508. Fundamentals (debt_to_equity, fcf_margin, interest_coverage, current_ratio) very sparse. |
| `ticker_risk_snapshots` | One row per ticker per day. Composite + five dimensions + dimension_inputs JSON. Latest day post-backfill: 503 rows w/ composite. |
| `shared_ticker_events` | Articles (canonical v2 store). 26,647+ rows; sentiment + TLDR + what_it_means populated for ~70%. |
| `alerts` | v2 schema (post 2026-05-24 migration): `read_at`, `delivered_at`, `severity`, `destination_type`, `destination_id`. Backfilled. |
| `user_preferences` | v2 schema: `alerts_watchlist`, `alerts_macro_shock`, `alerts_digest_ready`, `alert_severity_threshold`, trial_started_at, trial_ends_at, timezone. |
| `sector_regime_snapshots` | Has `etf`, `etf_close`, `etf_previous_close`, `day_change_pct`, `day_change_amount` after recent migration. Populated only when sector_snapshot job runs. |
| `macro_regime_snapshots` | Has ust10y_level, dxy_level, wti_level, spy_close, per-factor day-change. Populated only when macro_snapshot job runs. |
| `digests` | Stored Morning Reports per user. |
| `portfolio_risk_snapshots` | Currently sparse (~76 rows). Future P1 work to populate. |
| `watchlists`, `watchlist_items` | Tracked tickers. |
| `analysis_runs` | Run controller + per-batch children. Check this before any destructive ops. |
| `ticker_refresh_jobs` | Manual refresh queue. |

---

## 3. Hi-Fi v2 design tokens — what they are and how to use them

All in `ios/Clavis/App/ClavixDesignTokens.swift`. Derived from the `cx` object in the HTML. **Do not invent new colors.** If the HTML uses a color you can't find a token for, add a new token in this file with a comment pointing to where you found it in the HTML.

### Color palette

| Token | Hex | Purpose |
|---|---|---|
| `clavixInk` | `#1A1814` | Primary text, primary fills |
| `clavixInk2` | `#3A342B` | Secondary text |
| `clavixInk3` | `#777777` | Tertiary/muted body, meta, eyebrow |
| `clavixInk4` | `#999999` | Ghost text, disabled icons |
| `clavixInk5` | `#C8C0B0` | Rare deep-muted |
| `clavixCanvas` | `#F0EADB` | Canvas (≡ Page in v2) |
| `clavixPage` | `#F0EADB` | Main page background |
| `clavixPaper` | `#F3ECE0` | Card surface (warmer) |
| `clavixPaper2` | `#E8E0CC` | Ledger header inset, secondary card |
| `clavixRule` | `#D6CEBD` | Card stroke, divider |
| `clavixRule2` | `#E6DFCF` | Subtle divider |
| `clavixAccent` | `#1D3A6E` | Ink Blue. Primary link, focused state |
| `clavixAccentSoft` | `#E3E9F3` | Accent-tinted card fill |
| `clavixAccentInk` | `#11264A` | Text on accent fill |
| `clavixGood` | `#1F5B3A` | Forest. Up/positive/healthy |
| `clavixGoodSoft` | `#DDE9D8` | Good-tinted card |
| `clavixGoodInk` | `#0D3A22` | Text on good fill |
| `clavixWarn` | `#B34A14` | Burnt orange. Pressure/Pro accent |
| `clavixWarnSoft` | `#F4DCC4` | Warn-tinted card |
| `clavixWarnInk` | `#6E2C09` | Text on warn fill |
| `clavixBad` | `#7A1E2C` | Bordeaux. Bad/danger |
| `clavixBadSoft` | `#F0D8D4` | Bad-tinted card (error states) |
| `clavixBadInk` | `#5C2B2E` | Text on bad fill |

### Typography helpers (extension on `ClavisTypography`)

| Helper | Use |
|---|---|
| `clavixMono(size, weight)` | JetBrainsMono. Mono numerics, eyebrows, ticker symbols, ledger values, timestamps. |
| `clavixSerif(size, weight)` | System serif. Headlines, prose, card titles. |
| `clavixCaption` | Inter 12pt. Body caption, meta text. |
| `inter(size, weight)` | Inter family. Default body. |

### Layout constants (`ClavixLayout`)
- `pad: 20` — outer horizontal pad
- `bottomPad: 28`
- `cardRadius: 10`
- `controlRadius: 7`

### Atom inventory (`ClavixVQAComponents.swift`)
- `ClavixScreen<Content>` — eyebrow + title + scrolling content
- `ClavixLargeHeader` — sticky top header (eyebrow + serif title + trailing)
- `ClavixEyebrow(text)` — ALL CAPS mono 10pt eyebrow
- `ClavixCard<Content>(padding, fill)` — paper card with rule stroke + 10pt radius
- `ClavixSection<Content>(eyebrow, title)` — eyebrow + serif title + content
- `ClavixGradeBadge(grade, size)` — bond rating colored badge (AAA forest, AA forest, A ink, BBB warn, BB warn, BBB+ warn, default bad)
- `ClavixScoreBar(score)` — horizontal score 0-100 with tone fill
- `ClavixPill(label, active)` — mono chip for toolbars/filters
- `ClavixColumnHeader(text, align)` — ledger column header
- `ClavixMiniSpark(tone, seed)` — tiny inline sparkline (deterministic placeholder until real per-position history)
- `ClavixTabBar` — built but not currently in MainTabView (which uses TabView with UITabBar.appearance). Can swap later.

### Atom usage examples
```swift
// Today header
ClavixLargeHeader(
    eyebrow: "Morning Report",
    title: "Today",
    trailing: AnyView(HStack(spacing: 18) {
        Image(systemName: "magnifyingglass").foregroundColor(.clavixInk)
        Image(systemName: "bell").foregroundColor(.clavixInk)
    })
)

// Section
ClavixSection(eyebrow: "Portfolio sectors", title: "Sector exposure") {
    LazyVGrid(...) { ... }
}

// Card
ClavixCard(fill: .clavixPaper) {
    VStack(alignment: .leading, spacing: 12) {
        ClavixEyebrow("Morning Report")
        Text("Your daily risk brief is ready")
            .font(ClavisTypography.clavixSerif(18, weight: .medium))
            .foregroundColor(.clavixInk)
    }
}

// Grade badge
ClavixGradeBadge("BBB", size: 28)

// Score bar
ClavixScoreBar(score: 64)
```

---

## 4. The HiFi reference — how to use it as a build target

The HTML is bundled into the app and rendered in a WKWebView. **It is the spec.** When in doubt, screenshot it and copy what you see.

### Activate
```
mcp__xcode__stop_app_sim()
mcp__xcode__launch_app_sim(env={"CLAVIX_USE_HIFI_REFERENCE": "1"})
```

### Navigate
The HTML is one long scrolling document with 13 sections totalling 68 screens. Sections in order:
0. Read me (cover, contents)
1. Authentication (welcome, sign up, sign in, forgot, error)
2. Onboarding (positioning, brokerage connect, prefs, watchlist, notifications, final)
3. Today / Daily Digest (2 home variants, full digest, empty, offline)
4. Holdings / Portfolio (list, add, manual, outside-universe, edit, delete confirm, free limit, brokerage states)
5. Watchlist (add, manage)
6. Search (idle, recents, results, no-results, outside-universe)
7. Ticker Detail (composite + five dim, drivers, news, score history, exec summary)
8. Methodology drill-down (per-dimension audit: Financial, News, Macro, Sector, Volatility)
9. Alerts (centre, day groups, filter chips, alert detail)
10. Settings (account, prefs, brokerage, methodology, account actions)
11. Subscription (trial active, Pro)
12. Empty / Error states (offline, limited data, insufficient history, refresh limit)
13. Edge cases (article paywalled / failed / outside-universe ticker / etc.)

Scroll with `mcp__xcode__swipe(x1=200, y1=600, x2=200, y2=100)` to advance. Each swipe moves ~500px.

### Disable
Remove the env var and `launch_app_sim()` again.

---

## 5. Backend — keep it healthy

### Health check
```
curl -fsS https://clavis.andoverdigital.com/health
```
Should return `{"status":"ok", "apns":"missing", "snaptrade":"configured", "minimax":"configured", "supabase":"configured"}` in <100ms.

### Routes you can curl-test without auth (all return 401 fast)
```
curl -sS -o /dev/null -w "%{http_code} %{time_total}s\n" https://clavis.andoverdigital.com/<path>
# /holdings /preferences /digest /alerts /today
# /tickers/NVDA/score-history?days=90
```

If any return slower than ~150ms, suspect backend issue.

### Live SSH
```
ssh -i ~/.ssh/clavix_vps_ed25519 clavix-backend@134.122.114.241
# /opt/clavis is the mirrored repo
# docker compose ps   — container should be clavis-backend-1
# docker compose logs --tail 200 backend   — tail recent logs
```

### Manual deploy
GitHub Actions deploy (`.github/workflows/deploy-prod.yml`) requires `PROD_SSH_KEY` secret which is missing. **Use this manual flow instead:**
```bash
rsync -az --delete \
  --exclude '.git/' --exclude '.github/' --exclude '.xcodebuildmcp/' \
  --exclude '.claude/' --exclude '.cursor/' \
  --exclude 'BACKFILL/' --exclude 'BACKFILL_IMPORT/' --exclude 'ios/' \
  --exclude 'backend/.env' --exclude 'backend/apns/apns.p8' \
  --exclude '__pycache__/' --exclude '*.pyc' \
  -e "ssh -i ~/.ssh/clavix_vps_ed25519" \
  /Users/sansarkarki/Documents/Clavis/ \
  clavix-backend@134.122.114.241:/opt/clavis/

ssh -i ~/.ssh/clavix_vps_ed25519 clavix-backend@134.122.114.241 \
  "cd /opt/clavis && docker compose up -d --build --remove-orphans"

# Then verify:
curl -fsS https://clavis.andoverdigital.com/health
```

Build takes ~30-90s. Health check should return 200 immediately after.

### Migrations
Use `mcp__supabase__apply_migration` with the project ID `uwvwulhkxtzabykelvam`. Write the migration file to `supabase/migrations/<date>_<name>.sql` first so it's in git. **Always wrap in BEGIN/COMMIT and use `IF NOT EXISTS`/`IF EXISTS`.** Always check `information_schema` for column existence before writing — there have been previous schema-drift bugs where the audit doc was stale.

```python
mcp__supabase__apply_migration(
    project_id="uwvwulhkxtzabykelvam",
    name="my_migration_name",
    query="""BEGIN;
ALTER TABLE foo ADD COLUMN IF NOT EXISTS bar text;
COMMIT;"""
)
```

### Don't migrate during a live run
```python
result = mcp__supabase__execute_sql(
    project_id="uwvwulhkxtzabykelvam",
    query="SELECT id, current_stage, current_stage_message FROM analysis_runs WHERE status IN ('queued','running') ORDER BY started_at DESC LIMIT 5;"
)
```
If any rows: wait. The user runs S&P 500 backfills periodically.

---

## 6. Known issues + things in flight

### Already fixed in current session
- ✅ iOS default API timeout raised 12s → 30s (Today no longer immediately errors on parallel burst)
- ✅ Cream/paper palette derived from HTML applied across all live tab views
- ✅ All legacy `.textPrimary`/`.textSecondary`/`.accentBurnt`/`.surfaceElevated`/etc replaced with `clavix*` tokens in live views
- ✅ `DashboardErrorCard`, `ClavisLoadingCard`, `HoldingsEmptyState` rebuilt on cream/paper
- ✅ `ClavixTabBar` UITabBar appearance set to cream/paper
- ✅ HiFi HTML bundled and reachable via `CLAVIX_USE_HIFI_REFERENCE=1`
- ✅ Backend deployed with `/today`, `/tickers/{ticker}/score-history`, `/alerts/{id}/read`, `/holdings` outside-universe degraded mode, `enrich_positions_with_ticker_cache` v2 fields
- ✅ Schema migrations applied: alerts v2, user_prefs v2, sector_regime price columns, macro_regime factor levels

### Pending parity work (in priority order)
1. **Ticker Detail (Hi-Fi section 7)** — full rebuild: hero with composite + 5-dim radar, position context line, key drivers as 3 cards (HEADWIND/PRESSURE/TAILWIND), executive summary (Bull/Risk/What to watch), recent news with VQANewsLedgerCard-style cards, score history chart with toggles. The current ports are basic skins.
2. **Methodology drill-down (Hi-Fi section 8)** — five audit views need to match the HTML drill-downs: formula at top, input rows with raw value + source + last refreshed + weight + benchmark, sector medians, etc.
3. **Add-holding sheet** — currently functional but doesn't match the HTML's editorial styling
4. **CSV import sheet** — fully mock; backend route doesn't exist yet
5. **Sector heat ETF day changes** — Today shows `—` until iOS consumes `/today` envelope (not just `/holdings`). The data is there; it's a wiring change in DigestView.
6. **Macro narrative regeneration** — `macro_snapshot.refresh_macro_snapshot` job needs scheduling in `pipeline/scheduler.py`. Currently writes a snapshot row but no LLM narrative.
7. **Two scoring systems convergence** — `risk_scorer.py` LLM-first vs `structural_scorer.py` deterministic. Stick with structural; remove LLM path. CLAVIX_TRUTH §6 requires deterministic.
8. **Paywall** — not yet built. StoreKit/RevenueCat. P2.

### Active divergences observed in sim today
- Today's "Today —" line — no day change. Blocked on Holdings `previous_close` field reaching iOS via /holdings response (backend writes it, but iOS Position decoder may not be reading it correctly — verify).
- Sector exposure shows "SEM" instead of "Tech" — that's because the user has a Semiconductors-industry-as-sector position. Sector normalization needed.
- Top Movers / Calendar sections empty because user has no holdings with score deltas yet.

---

## 7. The user's preferences / instructions

These come from `CLAVIX_TRUTH.md` and prior conversations:

1. **News pipeline = Finnhub** (override of CLAVIX_TRUTH §10 which says Google News RSS). Don't switch silently.
2. **HTML mockup wins over Swift VisualQA** for design decisions.
3. **No fake deltas, no fake "was X" values.** Honest `—` always.
4. **Production user-visible brand is "Clavix"**, internal directories stay `Clavis*`.
5. **Free tier = 3 holdings, 5 watchlist tickers.** Server-enforced (mostly).
6. **Pro tier = $20/mo, 14-day trial, no card needed.** Paywall not built yet.
7. **iOS only at launch.** Android = v2.
8. **Five dimensions only.** Equal-weight composite.
9. **AAA→F grade scale.** Hysteresis: 3-point boundary cross + 2 days.
10. **Commit only when explicitly asked, OR after the user has reviewed and the build is clean.** Push to main is allowed and triggers GitHub Actions (which currently no-ops because of missing secret).

---

## 8. Useful one-liners

### Smoke-test the whole API contract
```bash
for endpoint in health holdings preferences digest alerts watchlists today; do
  printf "%-15s " "$endpoint"
  curl -sS -o /dev/null -w "code=%{http_code} time=%{time_total}s\n" --max-time 10 https://clavis.andoverdigital.com/$endpoint
done
```

### Check today's snapshot health
```python
mcp__supabase__execute_sql(
    project_id="uwvwulhkxtzabykelvam",
    query="""SELECT
      (SELECT COUNT(*) FROM ticker_risk_snapshots WHERE snapshot_date = CURRENT_DATE) AS today_total,
      (SELECT COUNT(*) FROM ticker_risk_snapshots WHERE snapshot_date = CURRENT_DATE AND composite_score IS NOT NULL) AS today_composite,
      (SELECT COUNT(*) FROM positions WHERE outside_universe = true) AS outside_universe_positions,
      (SELECT COUNT(*) FROM alerts WHERE read_at IS NULL) AS unread_alerts,
      (SELECT COUNT(*) FROM sector_regime_snapshots WHERE snapshot_date = CURRENT_DATE) AS today_sector_snapshots,
      (SELECT COUNT(*) FROM macro_regime_snapshots WHERE as_of_date = CURRENT_DATE) AS today_macro_snapshots;"""
)
```

### Regenerate iOS project after adding new files
```bash
cd /Users/sansarkarki/Documents/Clavis/ios && xcodegen generate
```

### Find legacy color references (none should remain in Views/)
```bash
grep -rnE "textPrimary|textSecondary|accentBurnt|accentSoft|accentInk|surfaceElevated|Color\.surface\b|Color\.bad\b|Color\.good\b|Color\.warn\b|Color\.border\b" ios/Clavis/Views/ | head -20
```

### Force a fresh user-defaults-clear if recents/last-seen sticks
The sim app stores recents and alert last-seen in UserDefaults. Reset with:
```bash
xcrun simctl uninstall booted com.clavisdev.portfolioassistant
```
Then re-install + launch.

---

## 9. Conventions

### Commit messages
```
<scope>: <imperative one-line>

<body explaining why, not what>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Scopes:
- `ios:` — Swift/iOS
- `backend:` — Python/FastAPI
- `db:` — Migrations
- `docs:` — Markdown
- `infra:` — Docker, GitHub Actions, deploy scripts

### File naming
- iOS views: `<Feature>View.swift` or `<Feature>Section.swift` or `<Feature>Sheet.swift`
- iOS view models: `<Feature>ViewModel.swift`
- iOS models: `<Domain>.swift` (singular noun)
- Backend routes: `<resource>.py` (plural)
- Backend services: `<noun>_service.py` or `<noun>.py`
- Backend pipeline: `<job_name>.py`
- Migrations: `<YYYYMMDD>_<snake_case_name>.sql`

### When to ask vs decide
Decide:
- Visual nits (padding, spacing, color tone within the cream palette)
- Backend honest fallbacks (empty array vs null)
- File organization, refactoring within a screen

Ask:
- Breaking API contract changes
- Schema changes that touch existing populated columns
- Adding paid third-party dependencies
- Anything that touches `CLAVIX_TRUTH.md` content

---

## 10. Your first 60 minutes

1. Read this doc top to bottom (10 min).
2. Read `docs/CLAVIX_TRUTH.md` (15 min).
3. Run the smoke-test one-liner from §8 to verify backend health (1 min).
4. Boot the sim, launch live tabs, screenshot each (5 min).
5. Boot the sim with `CLAVIX_USE_HIFI_REFERENCE=1`, scroll through every section, screenshot (10 min).
6. Pick the next pending parity task from §6, run one autonomous loop cycle (10 min).
7. Commit, push, report what you did and what's next (5 min).
8. Loop.

Have fun. The user is patient with quality, impatient with cosmetic regressions. They'll notice if you break a previously-good screen. Keep a clean working tree.

---

*Last updated by Claude Opus 4.7 at the conclusion of session `c5c31ccb-cf7d-4812-bd5b-d52007525954` on 2026-05-24. Next agent: keep this doc current. Add a "Session log" section at the bottom and append after every significant push.*

---

## Session log

### 2026-05-24 · Cycle 1 — Ticker Detail middle-third rebuild

**Pushed:** `ios: Hi-Fi parity — Ticker Detail dimensions, drivers, news rewrite`

Landed:
- **Five dimensions** rebuilt as a HiFi tabular card: `FIN / NEWS / MAC / SEC / VOL` mono abbrev + name on the left, `ClavixScoreBar` middle, mono score + chevron right. Tap-through to methodology preserved. Dropped the legacy "Limited Data" inline badge + "Full audit ↗" link in favor of a chevron — the row IS the tap target.
- **Key drivers** (`TickerDriverCardsSection`) fully rebuilt. Maps `DriverDirection` → `HEADWIND / WATCH / TAILWIND` tone tag, tone-tinted background (`clavixBadSoft / clavixWarnSoft / clavixGoodSoft`), tone border + serif title + `via {theme}` chip + strength label. Killed every `Color.surface / Color.border / .riskA / .riskD / .informational` legacy reference and removed the dark "SupportingEvidenceRow" subcards entirely — those aren't in the HiFi spec.
- **Recent news** cards: T1/T2/T3 source-tier badge, mono source, mono relative date (`2d ago` / `May 19` via new `formatArticleTimestamp` helper that handles ISO8601 with/without fractional seconds), serif headline, 2-line TLDR, sentiment dot+score on the right. Killed the ISO-timestamp leak and the "Limited Data" impact pill.
- **Section headers** for Key drivers / Recent news / Score history switched to HiFi pattern: `ClavixEyebrow` + serif title + optional trailing action (See all → / Show less). New `hifiSectionHeader(eyebrow:title:action:onAction:)` helper.

Still TODO on Ticker Detail (next cycle):
- Hero: split `You hold ··· Last $X · Δ%` bottom row; add radar (or keep sparkline placeholder)
- Executive summary card (Bull / Risk / What to watch — accent-tinted)
- Score history: toggle pills (Composite · News · Macro)
- Honest delta line under composite (currently no delta surfaced)
- Period chips above price/score chart

Reference workflow:
- Avoid spending compute on side-by-side WebView screenshotting — the HTML is at `docs/design/clavix-hifi-v2.html`. The React component source for each artboard lives gzipped+b64 in `<script type="__bundler/manifest">` of that file. Extract with:
  ```python
  m = re.search(r'<script type="__bundler/manifest">\s*(.*?)\s*</script>', raw, re.DOTALL)
  manifest = json.loads(m.group(1))
  for uuid, entry in manifest.items():
      data = base64.b64decode(entry['data'])
      if entry.get('compressed'): data = gzip.decompress(data)
      text = data.decode('utf-8', errors='replace')
      if 'ScreenTicker' in text: open(f'/tmp/{uuid}.js','w').write(text)
  ```
  Section 7 components (`ScreenTicker`, `DimRow`, `DriverCard`, `NewsRow`) live in asset `e743adf2-56cd-41fe-b381-bcec1a598a88`. `ScreenTickerHeld`, `ScreenRefreshLimit`, etc. live in `dcfc5c59-f42a-4d9d-be08-7ec9253c440e`. Reading the JSX directly is 10× faster than scrolling the WKWebView through 25+ artboards.

### 2026-05-24 · Cycle 2 — Full-app parity sweep (all 5 tabs + Ticker Detail Pass 2)

**Pushed:** `ios: Hi-Fi parity Cycle 2 — full tab sweep + Ticker Detail hero rebuild`

Landed across all 5 tab screens + Ticker Detail in one cycle, after extracting and reading every React component out of the gzipped bundle assets in `docs/design/clavix-hifi-v2.html`:

**Ticker Detail (Pass 2):**
- **Hero rebuild** matching `ScreenTicker` JSX in asset `e743adf2`: `Composite` eyebrow + grade badge + 30pt mono score on the left, honest score-delta line ("▲/▼ N vs prior session" when `sharedAnalysis.summary.scoreDelta` is present, else "— · no prior session score" — never fabricated). Bottom split row below a `clavixRule2` divider: `You hold` (shares + portfolioWeight × 100 → "X% of book" + "+$Y · +Z% from cost" coloured by P&L sign) ··· `Last` (price + day change % coloured by sign). Drops the pricing-only sparkline below the score block.
- **Score history toggle pills** (Composite / News / Macro / Vol) above the chart, wired through `ScoreHistoryChart`'s existing `toggledDimensions` binding. `Composite` is the no-toggle baseline.

**Today (DigestView):**
- Replaced the stub `Today —` line with a real portfolio day-change computed from `sharedAnalysis.dayChangeAmount × shares` summed across positions. Renders "Today +$604 (+3.66%)" (green) / "−$X (−Y%)" (red) when ≥1 position reports `previous_close`, else `—`.
- Cleaned the trailing `· —` dot off the composite line under the grade badge.
- Calendar empty-state copy already routes through `sanitizedDisplayText`, so the new vocab guard (below) cleans backend leaks automatically.

**Holdings:**
- Eyebrow `X tracked` → `X watched` per HiFi spec.

**Search:** already matches HiFi spec; no edits this cycle.

**Alerts:** already matches HiFi spec (`X unread · Y in 7D` eyebrow, mono filter pills with counts, mono day separators, category badge + time + headline + body + grade/delta meta + unread accent strip).

**Settings:** already matches HiFi spec (`ACCOUNT` eyebrow + serif `Settings`, grouped cards with toggles, version footer). Note: live toggles render green (system tint) where HiFi spec uses `clavixAccent` blue — left for a styling pass.

**Vocab guard (cross-cutting):**
- New `String.clavixVocabSafe` extension on top of `sanitizedDisplayText` in `App/DisplayText.swift`. Whole-word, case-preserving replacement of every CLAVIX_TRUTH §2 banned term that could leak from backend LLM output: Monitor→Track, Coverage→Tracking, Momentum→Trend, Recommend(ation)→Note/Observation, Suggest→Note, Forecast→Projection, Predict→Indicate, Analyst→Data. Caught a live "Monitor HOO…" leak in the Calendar card on Today.

Build verified after each batch; live screenshots taken on each tab and the AMD ticker detail hero/middle/bottom. Holdings ledger, Today five-axis snapshot, Alerts filter pills, Settings preference toggles, and the Ticker Detail HEADWIND/WATCH/TAILWIND driver cards all match the v2 HTML pixel structure.

Still pending (not on critical path; pull next cycle):
- Radar chart in the Ticker Detail hero (current placeholder is the price sparkline)
- Executive summary card (Bull / Risk / What to watch) between drivers and news
- Period chips above the price/score charts (1D / 1W / 1M / 3M / 1Y)
- Methodology drill-down per-dimension audits (HiFi §8) — these still use the older drawer
- Add-holding & CSV-import sheets — current functional UI, not yet HiFi-styled
- Settings toggle tint: swap UISwitch tint to `clavixAccent`

### 2026-05-26 · Cycle 3 — Radar + executive summary + honest backend verification

**Not committed yet:** branch `ios/hifi-parity-cycle-3` is live locally; no commit/PR created because this cycle is waiting on review.

Completed the remaining high-priority Ticker Detail parity work against the extracted JSX in `docs/design/clavix-hifi-v2.html`:

**Ticker Detail (Cycle 3):**
- Replaced the hero sparkline placeholder with a true 5-axis radar (`FIN / NEWS / MAC / SEC / VOL`) driven from `sharedAnalysis.riskDimensions`, with `clavixAccentSoft` fill and `clavixAccent` stroke. Missing dimension values now stay honest: the label hides and the polygon skips that vertex instead of inventing a score.
- Added the `Executive summary` block between Key drivers and Recent news, with separate `Bull case`, `Risk case`, and `What to watch` cards. Each card only renders if the backend supplies that specific field; null fields disappear entirely.
- Added shared period chips (`1D / 1W / 1M / 3M / 1Y`) above both the price chart and the score-history chart. Selection now filters the underlying `PricePoint` and `ScoreHistoryPoint` arrays rather than changing labels only.
- Preserved the honest composite delta line: still renders `— · no prior session score` when no real prior-session delta exists.

**Small remaining live parity fixes:**
- Settings toggles now use `clavixAccent` instead of the default green tint via `CX2Toggle`.
- Today sector normalization now maps `SEM` / semiconductor variants to `Tech` in the sector-exposure renderer.
- Added `ios/ClavisTests/PositionDecoderTests.swift` and a test target in `ios/project.yml` to lock the nested `shared_analysis.previous_close` decode path used by day-change calculations.
- Cleared the remaining legacy color-token matches under `ios/Clavis/Views/`; the grep at the handoff doc's token-check step now returns no matches.

**Screenshot artifacts:**
- `docs/AUDITS/hifi_parity_cycle3_ticker_2026-05-26.png` captures the live Swift ticker hero + radar + hold row + price chart state.
- `docs/AUDITS/hifi_parity_cycle3_summary_2026-05-26.png` captures the live Swift executive-summary cards and recent-news ledger.
- To make these captures meaningful without depending on the production API, added a DEBUG-only `ticker-live` / `ticker-live-summary` route in the Visual QA shell that renders the real `TickerDetailView` with a local fixture instead of the static mock component.

**Backend verification findings (production data):**
- Supabase REST is reachable; `clavis.andoverdigital.com` is not currently reachable from this workspace. `curl` and direct web fetches to `/health` time out with 0 bytes returned, so route-level verification is blocked by the tunnel/backend path rather than by auth.
- `backfill_14d` is complete in `job_runs` (`items_processed = 4054`, `items_failed = 0`, started `2026-05-26T12:06:47Z`).
- `ticker_risk_snapshots` has real 30-day depth for AAPL (`37` rows since `2026-04-26`), and current v2 rows exist for AAPL / NVDA / MSFT / GOOGL / META, but their latest populated `snapshot_date` is `2026-05-25`, not the table-wide max of `2026-05-26`.
- `macro_regime_snapshots` is now populated, but the latest row is still `data_status = price_only` with `rates_signal`, `credit_signal`, and `inflation_signal` null.
- `sector_regime_snapshots` is populated for today's run, but the schema currently exposes ETF/day-change fields and `data_status`, not the `regime_state` column assumed by the original SQL checklist.
- `sector_medians` is still empty in production, which blocks the Hi-Fi medians table in the methodology drill-down.

**Methodology drill-down status:**
- Deferred honestly to the next cycle. The current backend route `backend/app/routes/methodology.py` still returns the older per-dimension envelope and does not expose the Hi-Fi audit contract of `formula`, `inputs[]`, and `sector_medians[]` rows. Shipping the full §8 drill-down UI now would require fabricating rows client-side, which this cycle explicitly avoided.
- Follow-up entries were added to `backlog.md` for the missing methodology payload shape, missing `executive_summary_breakdown` contract, empty `sector_medians`, and the production route timeout blocker.
