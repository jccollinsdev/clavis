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
6. **iOS deployment target is iOS 16**, but the AGENT_PROMPT in the bundle assumes iOS 17 (`@Observable`). The DesignSystem/Theme class was adapted to `ObservableObject` to compile. If/when target bumps to 17, can swap back.
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

## 9. Open questions for the user (when next available)

1. **Render scheduling choice (P3-6)**: 6+ Render cron services (extra $/mo) OR upgrade to `standard` and run cron in-process via `SCHEDULER_TIER=cron`. The plan recommends hybrid; needs sign-off because it changes the bill.
2. **LLM personalisation budget (P7-1)**: estimated $50/day at 1k users for per-user article personalisation. Cap? Pro-only?
3. **Outside-universe scope (P7-4)**: all US-listed tickers, or whitelist? Polygon supports US-listed.
4. **Earnings calendar source (P5-3)**: Finnhub free tier vs. paid. Need to confirm the free tier's coverage.
5. **iOS deployment target bump to 17**: would simplify `Theme` (back to `@Observable`) and a few other things. Worth doing as a side task, or hold for the next OS-major boundary?

---

## 10. Memory pointers

The auto-memory system at `~/.claude/projects/-Users-sansarkarki-Documents-Clavis/memory/` has been written to during prior sessions. Notable entry: `project_clavis_state.md` (working app, MiroFish removed, SnapTrade + APNs + Stripe are next priorities). Read on session start; update as state changes.

---

## Session log

### 2026-05-25 (this handoff)
- Landed: iOS design-system foundation (15 files, commit `4d15901d5`).
- Landed: this handoff + `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md`.
- Blocked: nothing.
- Resume at: Phase P3 of `docs/SCHEDULING_AND_DATA_FRESHNESS_PLAN.md`. Critical-path P3-1 → P3-4 → P3-5 → P4-1 → P4-2 → P5-2 unblocks `today-a` rendering real numbers.
