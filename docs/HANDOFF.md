# Clavix — Agent Handoff

**Last updated:** 2026-05-25
**Authored by:** prior agent session (UI design-system foundation + backend/data audit)
**For:** any agent (Claude Code / Cursor / human) picking up this work cold

> Read this end-to-end before touching code. It is intentionally self-contained: if you've never seen this repo, this file plus `docs/CLAVIX_TRUTH.md` plus `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md` is sufficient to resume work.

---

## 1. What this repo is

**Clavix** is a SwiftUI iOS app (deployment target iOS 16) that issues bond-style letter grades (AAA → C) for portfolios, sectors, and individual tickers. It is **informational, not advisory** — never says buy/sell/hold/recommend (see `docs/CLAVIX_TRUTH.md` and `design_handoff/system/00-rules.md`).

Stack:
- **iOS app**: SwiftUI, `~/Documents/Clavis/ios/Clavis/` — generated via XcodeGen (`project.yml`)
- **Backend**: FastAPI, `~/Documents/Clavis/backend/app/` — deployed to Render (`render.yaml`)
- **DB**: Supabase Postgres — schema in `supabase_schema.sql`, migrations in `supabase/migrations/`
- **External APIs**: Polygon (prices, fundamentals), Finnhub (news + quotes), Minimax (LLM), APNs (push)
- **Marketing site**: static, `~/Documents/Clavis/web/`

The prod backend is `https://clavis.andoverdigital.com` behind a Cloudflare Tunnel. iOS calls Supabase directly for auth and the backend for everything else.

---

## 2. What was just completed (state as of this handoff)

### 2.1 iOS design-system foundation (committed)

Commit `4d15901d5` — *ios: Hi-Fi v2 design-system foundation from handoff bundle*.

Added [ios/Clavis/DesignSystem/](../ios/Clavis/DesignSystem/) with 15 files implementing the canonical token + primitive layer from `~/Downloads/UI_extracted/design_handoff_clavix/` (the design handoff bundle that landed today):

- `Tokens.swift` — `Color.cx*`, `CXFont/CXType`, `CXSpace/CXRadius/CXLine/CXMotion`, `Theme` (ObservableObject for iOS 16 compat), `ClavixDark`, `ClavixAccent` (4 swappable accents)
- `ClavixMark.swift` — Canvas-rendered logo per `design_handoff/system/03-logo.md` (squared "C" + ECG pulse exiting right; animated splash, dim ghost, small variant for <16pt; `ClavixBrand` wordmark lockup)
- `Grade.swift`, `ScoreBar.swift`, `Eyebrow.swift`, `Cards.swift` (`CXCard` + `AccentCard`), `Hairline.swift`, `Buttons.swift` (Primary/Secondary/Ghost 48pt), `AppBar.swift` (`LargeAppBar`), `TabBar.swift` (`CXTabBar`), `ChipBadge.swift`, `Sparkline.swift`, `PeriodChips.swift`, `DimsRow.swift`, `EmptyState.swift` (`CXEmptyState`)

Each primitive has a `#Preview`. Verified clean build on iPhone 17 sim. **No symbol collisions** with the existing `clavix*`/`Clavix*`/`VQA*` layers — the new layer is unprefixed (`Eyebrow`, `ScoreBar`, `GradePill`, `Sparkline`) plus `CX*` enums and a `Theme` class.

### 2.2 Backend audit + scheduling plan (this commit)

Authored two new docs:
1. **[docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md](SCHEDULING_AND_DATA_FRESHNESS_PLAN.md)** — the authoritative plan for getting all data fresh (volatility, macro, sector, fundamentals, earnings, prices, score history) without redundant work, plus the data-coverage delta introduced by the 69-screen design handoff. 6 phases (P3–P8), ~20 working days.
2. **This file (HANDOFF.md).**

The new plan **extends** (does not replace):
- `docs/P0_P1_P2_IMPLEMENTATION_PLAN.md` (2026-05-22) — UI mock-to-live priorities
- `docs/BACKEND_DATA_GENERATION_PLAN.md` (2026-05-23) — per-dimension data generation
- `docs/UI_DATA_CONTRACT_MATRIX.md` (2026-05-23) — endpoint shape design
- `docs/MOCK_TO_LIVE_AUDIT.md` (2026-05-22) — screen-by-screen LIVE/PARTIAL/MOCK state

All four are still valid for everything they cover; the new plan adds the missing scheduling layer and the 69-screen delta.

---

## 3. Where to pick up next

### 3.1 If you're continuing the iOS UI parity work

Continue from the AGENT_PROMPT in `~/Downloads/UI_extracted/design_handoff_clavix/AGENT_PROMPT.md`. The build order is:

1. ✅ Tokens + Typography (`DesignSystem/Tokens.swift`)
2. ✅ Logo mark (`DesignSystem/ClavixMark.swift`)
3. ✅ Primitives (the rest of `DesignSystem/`)
4. ⏭️ **Screen shells** — skipped intentionally because most screens already exist; *migrate existing views to the new primitives instead*.
5. ⏭️ **Section-by-section migration**, in this order per the AGENT_PROMPT:
   - `00 brand` → `01 auth` → `02 onboarding` → `03 today` → `04 holdings` → `05 watchlist` → `06 search` → `07 ticker` → `08 methodology` → `09 news` → `10 alerts` → `11 settings` → `12 pro`
   - For each screen, open `design_handoff_clavix/screens/<id>.md` + `screenshots/1x/<id>.png` and rewrite the existing view against `DesignSystem/` primitives + `cx*` tokens.
   - One commit per section. Keep PRs reviewable.

The legacy `clavix*` palette in `App/ClavixDesignTokens.swift` and `App/ClavisDesignSystem.swift` stays around until every view is migrated; both layers coexist cleanly.

### 3.2 If you're continuing the backend work (most likely)

**Open `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md` and start at Phase P3.**

Critical-path order: **P3-1 → P3-4 → P3-5 → P4-1 → P4-2 → P5-2**. This 6-step chain is what unblocks `today-a` / `today-b` from showing real numbers instead of `—`.

The two **highest-leverage** first changes:
1. **Wire `pipeline/macro_snapshot.py` to the scheduler (P3-4)** — the file works, it just isn't called. Same for `pipeline/sector_snapshot.py` (P3-5). Both are "dead code we already wrote."
2. **Add `SCHEDULER_TIER` env + flip `PAUSE_SYSTEM_SCHEDULER=false` carefully (P3-1, P3-7)** — currently no system jobs run in prod at all. This is the single biggest unlock.

### 3.3 If you're triaging an incident

- **iOS app shows `—` everywhere on Today/Holdings** → backend likely returning empty `dimensions[]`. Check `ticker_risk_snapshots.snapshot_date = CURRENT_DATE` count. If 0, the `daily_composite_recompute_universe` job didn't run. See `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md` §1.1 — `PAUSE_SYSTEM_SCHEDULER=true` is the most likely cause until P3 lands.
- **News articles missing** → check `system_active_ticker_news_refresh` (every 4h) and `DISABLE_NEWS_ENRICHMENT` env (must be `false`).
- **Build fails after `DesignSystem/` edits** → most likely cause is collision between the new unprefixed primitives (`Eyebrow`, `ScoreBar`) and existing `ClavixEyebrow`, `ClavixScoreBar`. Grep both layers before adding new primitive names.

---

## 4. Working agreements (don't violate without explicit instruction)

From `~/.claude/projects/-Users-sansarkarki-Documents-Clavis/memory/`:

- **Tokens, never literals.** Use `Color.cxInk`, `CXSpace.lg`, `CXType.sectionTitle.font` — never hex literals or magic numbers in new views.
- **No advisory language ever.** Banned: buy, sell, hold, recommend, advise, predict, forecast, thesis, research, analyst, monitor, momentum, Clavis, SnapTrade. See `design_handoff_clavix/system/00-rules.md`.
- **Faithful, not "improved".** Pixel parity with the design handoff is the goal. When the spec and your intuition disagree, the spec wins.
- **Every score must be auditable.** Tapping any letter grade or score bar opens its methodology drawer. Drill-downs are not optional.
- **Limited data is mandatory.** If a dimension has <3 articles or <2 days of history, render `—` and the limited-data card. Never fabricate.
- **Don't commit unless asked.** This handoff was written *because* the user explicitly asked for committed progress; default is to ask first.
- **Don't add features the task doesn't require.** No backwards-compat shims, no premature abstractions, no helper methods for hypothetical future use.

---

## 5. Project geography (where to find things)

```
~/Documents/Clavis/
├── ios/
│   └── Clavis/
│       ├── App/                       # entry, MainTabView, design tokens (legacy clavix*)
│       ├── DesignSystem/              # ← NEW (this handoff): canonical cx*/CX* + primitives
│       ├── Models/                    # Codable view-state structs
│       ├── ViewModels/                # @ObservableObject view models (iOS 16 compat)
│       ├── Views/                     # screen-by-screen views (Auth, Digest, Holdings, Tickers, …)
│       ├── Services/                  # APIService.swift, SupabaseAuthService, APNs manager
│       ├── Resources/                 # Fonts (Source Serif 4, Inter, JetBrainsMono), Design HTML
│       └── Config/                    # Secrets.xcconfig
│   ├── project.yml                    # XcodeGen spec
│   └── Clavis.xcodeproj
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry, starts APScheduler
│   │   ├── auth.py                    # Supabase JWT verification
│   │   ├── config.py                  # env loader
│   │   ├── pipeline/                  # the heart — scheduler.py + every analysis module
│   │   ├── routes/                    # FastAPI routes (one per surface)
│   │   ├── services/                  # external API clients, supabase helpers, news enrichment
│   │   ├── models/                    # Pydantic models
│   │   └── data/                      # sp500_universe.txt
│   ├── scripts/                       # sp500_precompute.py (manual backfill), canary_10_tickers.py
│   ├── apns/                          # APNs key & helpers
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── supabase/
│   ├── migrations/                    # 33 migrations, chronologically named
│   ├── functions/                     # edge functions (mostly empty / scaffolding)
│   └── sql/
├── supabase_schema.sql                # consolidated current schema (single source of truth for shape)
│
├── docs/
│   ├── CLAVIX_TRUTH.md                # ← AUTHORITY (944 lines) — read before anything else
│   ├── SCHEDULING_AND_DATA_FRESHNESS_PLAN.md  # ← NEW (this handoff): scheduling + data plan
│   ├── HANDOFF.md                     # ← you are here
│   ├── P0_P1_P2_IMPLEMENTATION_PLAN.md  # UI mock-to-live priorities
│   ├── MOCK_TO_LIVE_AUDIT.md          # screen-by-screen LIVE/PARTIAL/MOCK
│   ├── BACKEND_DATA_GENERATION_PLAN.md # per-dimension data generation
│   ├── UI_DATA_CONTRACT_MATRIX.md     # endpoint shape design
│   ├── UI_ELEMENT_DATA_AUDIT.md       # element-level UI data audit
│   ├── REFACTOR_PLAN.md               # large refactor sequencing
│   ├── TARGET_DESIGN_SOURCE_OF_TRUTH.md
│   ├── AGENT_HANDOFF_HIFI_PARITY.md   # prior handoff specific to UI parity
│   ├── ARCHITECTURE/, GUIDES/, PRODUCT/, REFERENCE/, PUBLIC/, legal/, design/
│   └── _archive/
│
├── web/                               # marketing site (static)
├── mirofish/                          # removed product surface — do not extend
├── render.yaml                        # ← prod deploy config; PAUSE_SYSTEM_SCHEDULER lives here
├── docker-compose.yml
├── scripts/                           # session-start, tunnel setup, sim-tap helpers
├── BACKFILL/                          # 357 backfill artifact dirs from the recent news pipeline
├── BACKFILL_IMPORT/
├── AGENTS.md                          # 665-line agent operating manual
├── opencode.json                      # opencode config
└── backlog.md
```

Also note: `~/Downloads/UI_extracted/design_handoff_clavix/` — the 69-screen design handoff. **Not committed** to the repo (it lives in the user's Downloads). If you need the spec for a screen, read it from there.

---

## 6. How to run things

### iOS
- Open `ios/Clavis.xcodeproj`. Scheme is `Clavis`. Default sim is iPhone 17. Build/Run normally.
- After editing `project.yml`, regenerate with `cd ios && xcodegen` (or use the XcodeBuildMCP tool).
- Previews work for every `DesignSystem/` primitive.

### Backend (local)
- `cd backend && pip install -r requirements.txt`
- Env vars required: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `MINIMAX_API_KEY`, `MINIMAX_BASE_URL`, `FINNHUB_API_KEY`, `POLYGON_API_KEY`, `PORT=8000`.
- `uvicorn app.main:app --reload --port 8000`
- Set `PAUSE_SYSTEM_SCHEDULER=false` locally to see jobs fire.

### Backfill (manual)
- `cd backend && python -m scripts.sp500_precompute` — the script the user ran to get 503/503 ✓
- `cd backend && python -m scripts.canary_10_tickers` — quick smoke check

### Render prod
- `render.yaml` defines the services. Push to `main` → autodeploy.
- Secrets live in Render dashboard (not in the file). Adding a new env var = edit `render.yaml` AND set in dashboard.

---

## 7. Important context the audits surfaced

These are non-obvious findings worth carrying forward:

1. **`PAUSE_SYSTEM_SCHEDULER=true` in prod** ([render.yaml](../render.yaml)). The 503/503 backfill the user just finished was triggered manually. System scheduled jobs are off until P3-1 changes this.
2. **Two pipeline modules are dead code in prod**: `pipeline/macro_snapshot.py` and `pipeline/sector_snapshot.py`. Both are fully written, both have working DB upsert helpers (`save_daily_macro_regime()`, `save_daily_asset_safety_profile()` in migration `20260408_daily_structural_refresh.sql`), but nothing in `pipeline/scheduler.py` calls them. P3-4 / P3-5 wires them up.
3. **`ticker_risk_snapshots.dimension_last_refreshed`** is a JSONB column already populated but **write-only** — no code reads it. P4-1 uses it as the per-dimension freshness gate.
4. **Staleness threshold is hardcoded** at `_STALE_SNAPSHOT_THRESHOLD_HOURS = 6` in `backend/app/routes/tickers.py:57`. New cadence design wants this configurable per-domain.
5. **Score history endpoint exists** (`GET /tickers/{ticker}/score-history`) but is sparse because the daily composite job that would fill it doesn't run universe-wide.
6. **iOS deployment target = 17.0** (bumped 2026-05-25 from 16.0). `Theme` uses `@Observable`. Pre-existing VMs that still use `ObservableObject` (`DigestViewModel`, `SettingsViewModel`, etc.) keep working — no need to refactor them; just new code can use `@Observable` freely. After the bump, 8 deprecation warnings appeared on `onChange(of:perform:)` in existing views — non-blocking, address opportunistically.
7. **Two field-name evolutions** silently impact API parsing:
   - `Alert` v2 (migration `20260524_alerts_v2_read_state.sql`) added `read_at`, `delivered_at`, `severity`, `destination_*` columns but iOS `Alert.swift` model wasn't updated. Decoding works because fields are optional, but unread badge can't be honest until iOS picks them up.
   - `dimension_scores` was renamed and backfilled in `20260508_backfill_dimension_scores_from_old_names.sql`. Code reads both names defensively.
8. **No `job_runs` audit table yet** — P3-2 adds one. Until then, "Refreshed at" timestamps in the UI have nothing to read.
9. **Personalisation is the biggest LLM-cost risk** (§5.1 of the plan). Budget gate required before P7-1 ships.

---

## 8. The "if rate-limited" playbook

If you hit a rate limit / context limit mid-task:

1. **Commit what's done** if it compiles. Partial PRs are fine as long as the build is green.
2. **Add a short note** to the bottom of this file under a `## Session log` heading: date, what landed, what's blocked, where to resume.
3. **Update `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md`** if your work changed the plan (struck-through items, added items, scope changes).
4. **Don't delete in-progress branches** without checking with the user. Push the WIP branch with a `wip/` prefix.

---

## 9. Resolved decisions (user, 2026-05-25)

1. **Scheduling host = VPS cron**, not Render. The DigitalOcean VPS running `clavis-backend-1` is prod truth. `render.yaml` is fallback/staging. Cron entries in `scripts/cron/clavix.crontab` get copied to `/etc/cron.d/clavix` on the VPS and shell `docker exec clavis-backend-1 python -m app.jobs.run <job_id>`. See `SCHEDULING_AND_DATA_FRESHNESS_PLAN.md` §2.4.
2. **LLM personalisation (P7-1) = two-layer: structural template + LLM narrative.** Structural template always renders (zero LLM): *"You hold 420 sh of NVDA (15.6% of book). This change moves your portfolio composite from 81 → 78."* LLM-generated narrative is APPENDED (fails open if budget runs out). Cached per `(user_id, event_id, portfolio_composite_at_compose)`. Hard caps: top-5 articles/user/day, 240 chars per article. **Prerequisite: upgrade Minimax plan to $50/mo (150k req/week) before P7-1 ships** — done as part of P7-1 acceptance. Watchlist personalisation = structural only in v1. See plan §5.1 for full guardrails.
3. **Outside-universe (P7-4) = all US-listed via Polygon `/v3/reference/tickers?market=stocks&active=true&locale=us`.** No whitelist. ADRs/OTC/pink-sheets rejected until the degraded-mode scoring path proves stable on US-listed equities.
4. **Earnings calendar (P5-3) = Finnhub free tier.** Coverage is sufficient; one batch call per day for the whole universe sits comfortably inside the 60 req/min limit.
5. **iOS deployment target = 17.0** (was 16). `ios/project.yml` updated, `Theme` reverted to `@Observable`, Xcode project regenerated, build verified. Existing iOS-16-compat ObservableObject VMs left alone — no need to refactor everything; just unblocks new code from using `@Observable` directly.
6. **Apple Developer / StoreKit / SnapTrade = NOT YET OWNED.** This cycle builds everything that does NOT require them. APNs becomes a no-op behind `APNS_ENABLED=false`; paywall is a mock that says "Subscriptions are coming soon"; brokerage routes return `not_configured`. All three deferrals are loud in `backlog.md` under "Prerequisites we do not own yet" with the small bounded follow-up cycle each unlock requires. See plan §5.7.
7. **Universe scope = S&P 500 only (~503 tickers)**, no expansion to S&P 1500 or Russell 1000. Everything else lives in the outside-universe degraded path from P7-4. Keeps API costs flat and matches the 80% market-cap coverage product threshold.
8. **First-time onboarding UX = hybrid.** iOS renders Today immediately using the latest universe-wide snapshot; the Morning Report card shows a `generating your first report` state until the per-user sync run finishes; on completion the card swaps in. New job: `onboarding_seed_user` (P4-6). Backend exposes `GET /digest/status?user_id=...` polled at 1.5s during `.generating` state.
9. **Score history backfill = 14 days at deploy** (compromise between full 90d and forward-only). Powers "was BBB 5 days ago" week-over-week deltas on day 1. Full 90d accrues forward over the next ~75 days. Run as a one-shot post-deploy job: `python -m app.jobs.run backfill_14d` (P3-9). Estimated ~1h with existing rate gates.

---

## 10. Memory pointers

The auto-memory system at `~/.claude/projects/-Users-sansarkarki-Documents-Clavis/memory/` has been written to during prior sessions. Notable entry: `project_clavis_state.md` (working app, MiroFish removed, SnapTrade + APNs + Stripe are next priorities). Read on session start; update as state changes.

---

## Session log

### 2026-05-25 (planning + handoff)
- Landed: iOS design-system foundation (15 files, commit `4d15901d5`).
- Landed: scheduling plan + handoff (commit `f1249d94d`).
- Landed: round-1 user decisions — VPS cron / templated personalisation / outside-universe = US-listed / earnings = Finnhub free / iOS 17 bump (commit `2eb474d14`).
- Landed: round-2 user decisions — personalisation reverted to LLM-driven with Minimax upgrade; universe stays S&P 500; hybrid onboarding (P4-6 added); 14-day deploy-time history backfill (P3-9 added); explicit deferral of Apple Dev + StoreKit + SnapTrade with stub-behaviour spec (commit `dd219d7fd`).

### 2026-05-25 (Codex execution run, P3 → P8)
Codex ran the handoff prompt and shipped phases P3–P7 cleanly + started P8 before hitting a ChatGPT usage limit mid-phase.

**Codex commits (in order):**
- `10c587ff0` — **feat(p3): scheduler foundation + macro/sector snapshots wired.** Added `SCHEDULER_TIER` gate, advisory-lock RPC wrappers (`clavix_try_advisory_lock` / `clavix_advisory_unlock`), `job_runs` audit table + writers, `python -m app.jobs.run` CLI, macro/sector job wrappers, `scripts/cron/clavix.crontab`, deploy copy step. **P3-9 deliberately deferred** (rejected: don't fake 14d of history without the real composite recompute path; deferred until P4 exists — sound call).
- `f2c2516b4` — **feat(p4): daily composite + portfolio rollup + onboarding.** Added `daily_composite_recompute_universe`, `daily_portfolio_rollup_per_user`, hybrid-onboarding `onboarding_seed_user`, `/digest/status` polling endpoint. iOS gained a minimal `MorningReportState = .placeholder | .generating | .ready` state machine + 1.5s polling hook in `DigestViewModel`, no visual redesign.
- `ccc190205` — **feat(p5): today sector heat + earnings calendar.** Added `/portfolio/sector-exposure` (value-weighted composition + ETF day-change), extended `/today` aggregator with portfolio + sector + calendar + report + freshness blocks, `earnings_calendar` table + `daily_earnings_calendar_refresh` Finnhub-backed job, freshness blocks on `/today`, `/portfolio/sector-exposure`, holdings envelope mode. Today tab now consumes the real envelope.
- `fbb1fba75` — **feat(p6): methodology peer medians + audit depth.** Persisted `peer_groups` + `sector_medians` weekly jobs + tables, extended `/methodology` with `peer_comparisons[]`, `sector_median_comparison{}`, `article_histogram_14d[]`. **P6-4 (IV-rank/options) + P6-5 (monthly macro regression) deferred** (Polygon options scope larger than this run could safely take — flagged for follow-up).
- `9597c2a15` — **feat(p7): refresh limits + outside-universe guardrails.** Added `refresh_attempts` table + 3/day Free rate-limit on `POST /tickers/{ticker}/refresh` (429 + retry-after), `positions.outside_universe` column + degraded `POST /holdings?allow_outside_universe=true` path, `digests.issue_number` monotonic sequence, alert-hysteresis helper + test (Δ ≥ 3 + 2 consecutive days, per `system/00-rules.md`). **P7-1 LLM personalisation explicitly deferred** until Minimax plan upgrade — correct call, that prerequisite was an open env-var change, not a Codex action.

**Codex P8 work (in-flight, finished in this session):**
Codex authored three P8 job modules and the etf_holdings migration but ran out of credits before wiring them. I picked up the trailing work:
- `aa31c7a2e` — **feat(p8): wire event-fundamentals + etf-holdings + universe-audit jobs.** Added job_id registry entries (`event_fundamentals_pull`/daily, `monthly_etf_holdings_refresh`/monthly, `weekly_universe_audit`/weekly), cron entries under a new "P8 — operational polish" section, 9 new tests in `test_p8_jobs.py` covering registry + dry-run + pure helpers (`diff_universe`, `rows_for_etf`, `event_fundamentals._calendar_tickers`). ETF holdings ship with STATIC seeds for SPY/QQQ/VTI only — real issuer-API ingestion is a follow-up.

**Verification (this session, post-P8):**
- `pytest tests/test_p8_jobs.py tests/test_jobs_runner.py tests/test_p4_jobs.py tests/test_p5_today_portfolio.py tests/test_p6_methodology_depth.py tests/test_p7_limits_outside_digest.py tests/test_scheduler_jobs.py` → **53 passed** on Python 3.11 (matches prod `python:3.11-slim` Dockerfile). Local Python 3.9 will fail collection because Codex's code uses PEP 604 union syntax (`X | None`); not a real issue — prod is 3.11.
- `xcodebuild build_sim` Clavis / iPhone 17 → **green.**

**What's deferred (re-stated for the next agent):**
| Deferred | Why | When to revisit |
|---|---|---|
| P3-9 14-day score-history backfill | Codex correctly chose not to fake history before real composite recompute existed | Now safe: P4-1 daily_composite_recompute_universe shipped. Run `python -m app.jobs.run backfill_14d` once that job module is added (new follow-up). |
| P6-4 IV-rank + implied vol | Polygon options API scope too large for the Codex run | Add `app/jobs/iv_rank.py` + extend `dimension_inputs.volatility`. Standalone follow-up. |
| P6-5 monthly macro regression refresh | Same reason as P6-4 | Add `app/jobs/macro_regression.py` running 252-day β to 10Y/DXY/WTI/VIX/SPY. |
| P7-1 LLM personalisation | Needs Minimax plan upgraded to $50/mo (150k req/week) first | Upgrade Minimax plan → then add `app/services/personalisation.py` with the two-layer template+LLM design per plan §5.1. |
| P8-2 real ETF holdings ingestion | Static seeds work for SPY/QQQ/VTI; real-issuer ingestion is a separate API surface | Replace `etf_holdings.ETF_HOLDING_SEEDS` dict with a fetcher; keep job_id + cron entry as-is. |
| Real APNs delivery | No Apple Dev account yet | Flip `APNS_ENABLED=true` env once Apple Dev account is set up; no code change required (per plan §5.7). |
| Real StoreKit + SnapTrade | No accounts yet | Bundled follow-up cycle once Apple Dev + StoreKit + SnapTrade prerequisites in hand. |

**Resume at:** any of the deferred items above. Critical-path is empty — every Today / Holdings / Ticker / Methodology screen has its backend data path live (assuming the cron has run at least once). Next-most-valuable single ticket is probably **P7-1 personalisation** (visible user value, blocked only by a $30 Minimax plan upgrade) followed by **P3-9 backfill** (one-shot at deploy → unlocks "was BBB 5 days ago" deltas immediately instead of waiting 5 trading days).

**Verification next time you sit at the sim:**
1. Pull latest main: `git pull`. Confirm at commit `aa31c7a2e` or later.
2. iOS: `cd ios && xcodegen && xcodebuild build_sim`. Boot the sim. **Today tab** should now show a populated sector-heat grid (after the macro/sector cron has run at least once in prod) and a non-`—` portfolio composite delta. **Ticker Detail → Methodology drawer** should show peer comparisons + sector medians where data exists.
3. Backend: `cd backend && /opt/homebrew/bin/python3.11 -m pytest tests/ -q` should return 53+ passed.
4. Cron sanity (on the VPS): `crontab -l -u root | grep clavix` should show 13 entries (was 10 pre-P8).

### 2026-05-25 (Codex deferred-items completion run)
- Landed: `8fce49d4f` — **feat(p3-9): one-shot 14d ticker-risk-snapshot backfill.** Added `backend/app/jobs/backfill_14d.py`, threaded `target_date` through `daily_composite_recompute_universe`, registered `backfill_14d` as a manual job, and added tests for dry-run + per-day dispatch.
- Landed: `0ada303e9` — **feat(p7-1): two-layer per-user article personalisation.** Added `backend/app/services/personalisation.py`, digest-time persistence in `digests.structured_sections.personalised_articles`, methodology/ticker-news reattachment, and iOS `ArticleDetailSheet` rendering inside the existing `★ PERSONALISED` card.
- Landed: `70c9bc18c` — **feat(p6-5): monthly macro regression refresh + factor exposures.** Added `backend/app/jobs/macro_regression.py`, monthly job registry wiring + cron entry, methodology `factor_exposures`, and synthetic regression tests. Added `numpy` to `backend/requirements.txt` because the repo’s Python 3.11 environment did not previously have it installed.
- Landed: `7d4fb5a56` — **feat(p6-4): IV-rank + implied vol fallback for volatility audit.** Added `backend/app/services/polygon_options.py`, threaded `implied_vol_30d` + `iv_rank` into volatility inputs, and kept an explicit `iv_source="estimated"` fallback when options data is unavailable.
- Landed: `d8d7adf49` — **feat(p8-2): real issuer-API ETF holdings ingestion.** Replaced static-only writes with issuer-backed fetchers for SPY (SSGA workbook), QQQ (Invesco JSON, stored as `source="invictus"` per plan wording), and VTI (Vanguard holdings API), with static-seed fallback + warning logging preserved.

**Verification (this session):**
- Targeted backend tests passed for each item:
  - P3-9: `tests/test_p3_9_backfill.py tests/test_p4_jobs.py tests/test_jobs_runner.py`
  - P7-1: `tests/test_p7_1_personalisation.py tests/test_portfolio_compiler_summary_length.py tests/test_digest_force_refresh.py`
  - P6-5: `tests/test_p6_5_macro_regression.py tests/test_p6_methodology_depth.py tests/test_jobs_runner.py`
  - P6-4: `tests/test_p6_4_polygon_options.py tests/test_p6_methodology_depth.py`
  - P8-2: `tests/test_p8_2_etf_holdings.py tests/test_jobs_runner.py`
- iOS regeneration + build passed for the P7-1 UI surface: `cd ios && xcodegen && xcodebuild -scheme Clavis -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17' build`
- Full backend suite still stops on the same pre-existing first failure as earlier in the day: `tests/test_article_scraper_resolution.py::test_attach_decoded_google_news_urls_rewrites_wrapper_urls`

**Blocked / remaining work:**
- No planned deferred items remain from the 2026-05-25 Codex run.
- One unrelated repo-level test failure remains pre-existing in `tests/test_article_scraper_resolution.py`; it was not part of this deferred-items scope.

**Resume point for the next agent:**
- Start with the pre-existing Google News URL rewrite test if you want the full backend suite green.
- Otherwise, the product-facing deferred backlog from the prior run is complete; next work can come from new user priorities rather than this handoff chain.
