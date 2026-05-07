# Clavis — Remaining Work

Last updated: 2026-04-06

---

## Status Summary

The core MVP loop works: add holdings → AI analysis → risk grades → daily digest → iOS display.
UI polish was completed April 6 (markdown rendering, animations, dark mode colors, tappable news links, timeframe picker, consistent grade colors).

What remains are backend reliability issues that break core PRD promises, plus secondary features for a more complete product.

---

## Priority 1 — Breaks Core PRD Promises

These must be fixed before showing the app to anyone outside your household.

### 1. Push Notifications Are Unreliable
**What the PRD promises:** Alert user when any position changes grade or a major event triggers. Daily 7am push when digest is ready.

**What's broken:** `backend/app/notifier.py` — `send_push()` silently times out with no retry logic. Device tokens are stored correctly but notifications never reliably fire.

**What to build:**
- Add retry logic (3 attempts, exponential backoff) to `send_push()`
- Add error logging when APNs rejects a token
- Add a test endpoint `POST /test-push` that sends a real push to verify the full stack
- Verify APNs certificate/key is configured in `.env`

**Files:** `backend/app/notifier.py`, `backend/app/main.py`

---

### 2. Scheduled Digest Dies on Container Restart
**What the PRD promises:** Digest runs automatically every morning at the user's configured time.

**What's broken:** APScheduler runs in-memory inside Docker. Every container restart wipes all scheduled jobs. Users silently stop getting digests.

**What to build:**
- Switch APScheduler to a persistent job store backed by Supabase or SQLite
- On app startup, re-register any missing user schedules from `user_preferences` table
- Add a `/scheduler/status` endpoint to inspect which jobs are active

**Files:** `backend/app/scheduler.py`, `backend/app/main.py`

---

### 3. Backend URL Breaks Every Restart
**What the PRD promises:** iOS app connects to backend reliably.

**What's broken:** Cloudflare quick tunnel generates a new random URL on every restart. The hardcoded URL in `APIService.swift` goes stale, silently breaking all API calls.

**What to build:**
- Set up a named Cloudflare tunnel (`cloudflared login` + `cloudflared tunnel create clavis`) with a fixed subdomain
- OR deploy backend to Railway/Render with a stable URL
- Update `APIService.swift` base URL constant once stable URL is set

**Files:** `backend/` (deployment), `ios/Clavis/Services/APIService.swift`

---

## Priority 2 — Gaps vs. PRD Features

These are explicitly mentioned in the PRD/knowledge base but not yet implemented.

### 4. News Items Not Surfaced Reliably in Position Detail
**What the PRD promises:** Position detail shows "today's relevant news" for that holding.

**What's incomplete:** `news_items` table exists and pipeline stores items, but the `/positions/{id}` endpoint hydration of `recentNews` is inconsistent — quiet market days return empty arrays with no fallback messaging.

**What to build:**
- Verify pipeline reliably writes to `news_items` for every run
- Add a "No news today for this position" empty state in `RecentNewsCard`
- Consider expanding news lookback from 2 days to 5 days for quieter stocks

**Files:** `backend/app/pipeline/`, `ios/Clavis/Views/PositionDetail/PositionDetailView.swift`

---

### 5. Analysis Timeout Has No Recovery
**What the PRD promises:** Users get a complete analysis every morning.

**What's broken:** The pipeline has a 12-minute hard timeout. If it fails mid-run, positions processed before the failure get scores but later positions get nothing. The user sees a partial or stale digest with no explanation.

**What to build:**
- Save partial results as the pipeline progresses (checkpoint after each position)
- On timeout/failure, mark run as `partial` not `failed`, and generate a digest from whatever completed
- Surface "last analyzed X hours ago" per position in the iOS app

**Files:** `backend/app/pipeline/runner.py`, `ios/Clavis/Views/PositionDetail/PositionDetailView.swift`

---

## Priority 3 — Polish & Secondary Features

Not blocking, but improve the daily experience.

### 6. Holdings List: Sort & Filter
Add sort options (by grade, by P&L, by archetype) and a search bar to the Holdings tab.

**Files:** `ios/Clavis/Views/Holdings/HoldingsListView.swift`, `ios/Clavis/ViewModels/HoldingsViewModel.swift`

---

### 7. Grade History Sparkline per Position
Show a small line graph of grade changes over the past 30 days on each position card. The `risk_scores` table already stores historical grades — just need a query and a chart.

**Backend:** Add `GET /positions/{id}/grade-history` endpoint
**iOS:** Add a small `Chart` sparkline to `PositionCard` and `PositionDetailView`

---

### 8. First-Time User Onboarding
New users land on an empty dashboard with no guidance. Add a simple 2-step onboarding sheet:
1. "Add your first position" (ticker + shares + price)
2. "Run your first analysis"

**Files:** `ios/Clavis/Views/`, new `OnboardingView.swift`

---

### 9. Portfolio Composition Chart
A donut chart breaking down holdings by archetype (Growth/Value/Cyclical/Defensive/Small Cap). One SwiftUI `Chart` component on the Holdings tab or Dashboard.

**Files:** `ios/Clavis/Views/Holdings/HoldingsListView.swift` or `DashboardView.swift`

---

### 10. Analysis Pipeline Parallelization
Currently positions are processed sequentially. With 5–10 holdings and multiple MiniMax calls per position, a run takes 5–10 minutes. Parallelizing with `asyncio.gather()` would cut this to ~1–2 minutes.

**Files:** `backend/app/pipeline/runner.py`

---

### 11. AI Response Caching
The same news article analyzed for multiple users re-runs the full MiniMax stack every time. Caching `event_analyses` by `event_hash` (which already exists in the schema) would reduce cost and latency at scale.

**Files:** `backend/app/pipeline/agentic_scan.py`, `backend/app/pipeline/classifier.py`

---

## Done (April 6, 2026)

- ✅ Markdown rendering for all AI-generated text (bold, bullets render properly)
- ✅ Time-of-day greeting (morning/afternoon/evening)
- ✅ Tappable news URLs (Safari sheet)
- ✅ Timeframe picker wired to price chart (7D/30D/90D)
- ✅ Fade-in animations on data load (Dashboard, Digest)
- ✅ Grade badge spring animation on Position Detail
- ✅ Smooth disclosure group animations
- ✅ Grade color consistency across all screens
- ✅ Dark mode adaptive alert colors
- ✅ Removed duplicate DigestChip/AnalysisTag components
- ✅ Normalized corner radii to design system constants
- ✅ `SafariView` wrapper for in-app article browsing
