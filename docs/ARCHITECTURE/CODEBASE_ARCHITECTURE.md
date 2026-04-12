# Clavis Codebase Architecture

## What Clavis Is

Clavis is an iOS-first portfolio risk intelligence app for self-directed investors. The product is built around one core question: "Is what I own still safe to hold?"

The app tracks a user's holdings, analyzes relevant news and macro signals, assigns each holding a safety score and letter grade, compiles a morning digest, and surfaces alerts when something material changes.

At a high level:

- Frontend: native iOS app built in SwiftUI
- Auth: Supabase Auth used directly from iOS
- Backend API: FastAPI
- Data store: Supabase Postgres
- Analysis engine: Python pipeline with LLM-assisted classification and report generation
- Market/news data: Finnhub, Polygon, RSS feeds
- Push notifications: APNs via `aioapns`
- Scheduling: APScheduler running inside the backend process

## Repository Layout

- `ios/Clavis/`: SwiftUI app
- `backend/app/`: FastAPI app, pipeline, services, routes
- `backend/app/routes/`: API endpoints the iOS app calls
- `backend/app/pipeline/`: analysis, scoring, digest generation, scheduling
- `backend/app/services/`: external integrations and shared service clients

## Full Stack

### Frontend

- Language: Swift
- UI framework: SwiftUI
- Charting: Apple `Charts`
- Browser embedding: `SFSafariViewController`
- Auth client: Supabase Swift client

### Backend

- Language: Python
- Web framework: FastAPI
- Scheduler: APScheduler
- HTTP clients: `requests`, vendor SDKs
- Push delivery: `aioapns`
- AI provider: MiniMax via OpenAI-compatible client

### Data + Infra

- Database and auth: Supabase
- Backend host URL used by iOS: `https://clavis.andoverdigital.com`
- Backend container used locally: `clavis-backend-1`

## Runtime Architecture

## iOS app startup

1. `ClavisApp` starts.
2. `AppDelegate` registers for remote notifications immediately.
3. `AuthViewModel` is injected into the environment.
4. `ContentView` checks for an existing Supabase session once on first appearance.
5. If authenticated, the app shows `MainTabView`.
6. If not authenticated, the app shows `LoginView`.

## Backend startup

1. FastAPI starts through `backend/app/main.py`.
2. In the app lifespan hook, APNs configuration is validated.
3. `start_scheduler()` runs.
4. Existing scheduled jobs are rebuilt from `user_preferences` and persisted scheduler state.
5. Stale or orphaned `analysis_runs` are marked failed during startup cleanup.

## Authentication Model

### Frontend auth flow

- iOS uses `SupabaseAuthService` directly for sign-in, sign-up, sign-out, session checks, and access token retrieval.
- `AuthViewModel` is a thin wrapper around that service.
- All backend calls go through `APIService`.
- `APIService` attaches the current Supabase access token as `Authorization: Bearer <token>`.

### Backend auth flow

- FastAPI middleware in `main.py` intercepts protected routes.
- It manually decodes the JWT payload, extracts the `sub` claim, and stores it on `request.state.user_id`.
- Route handlers use that `user_id` to scope all queries to the current user.

Protected route families:

- `/holdings`
- `/digest`
- `/positions`
- `/trigger-analysis`
- `/analysis-runs`
- `/alerts`
- `/preferences`
- `/prices`
- `/scheduler`
- `/test-push`

## Frontend Architecture

## App shell

### `ContentView`

- Root auth gate.
- Decides between `LoginView` and `MainTabView`.

### `MainTabView`

Five tabs:

1. Dashboard
2. Holdings
3. Digest
4. Alerts
5. Settings

## Shared frontend layers

### Design system

`ios/Clavis/App/ClavisDesignSystem.swift` defines:

- spacing constants
- color palette
- typography tokens
- card styling helpers
- reusable loading cards, section headers, stat pills, ring gauges

The visual system is intentionally restrained, high-signal, and light-themed.

### Display text sanitization

`DisplayText.swift` removes invalid characters and strips basic markdown markers for some UI contexts.

### Network layer

`APIService` is the single backend client.

It handles:

- request building
- bearer token attachment
- JSON decoding
- no-cache request headers
- endpoint-specific typed decoding

### Push layer

`PushNotificationManager`:

- requests notification permission
- registers with APNs
- stores the APNs token in `UserDefaults`
- forwards the token to the backend
- posts internal notifications when a push should open Digest or a Position Detail screen

## Screen-by-screen frontend behavior

## 1. Login screen

File: `ios/Clavis/Views/Auth/LoginView.swift`

Purpose:

- authenticate the user via Supabase

UI:

- email field
- password field
- sign in / sign up mode toggle
- loading indicator while auth request is in flight
- inline auth error label

Data flow:

- user submits credentials
- `AuthViewModel.signIn` or `AuthViewModel.signUp` calls `SupabaseAuthService`
- success flips `isAuthenticated = true`
- `ContentView` automatically transitions to `MainTabView`

## 2. Dashboard screen

Files:

- `ios/Clavis/Views/Dashboard/DashboardView.swift`
- `ios/Clavis/ViewModels/DashboardViewModel.swift`

Purpose:

- give the user a top-level portfolio risk snapshot

Primary data sources:

- `GET /holdings`
- `GET /digest`

Derived portfolio metrics computed in the view model:

- portfolio grade
- portfolio score
- portfolio risk state
- portfolio risk trend
- action pressure
- improving count
- deteriorating count
- major event count
- top risk driver
- last updated time

UI sections:

- loading card
- error card
- `PortfolioStatusHero`
- `NeedsAttentionSection`
- `SinceLastReviewRow`
- `DigestPreviewCard`

How the data gets there:

1. `DashboardView.onAppear` triggers `loadData()` on first appearance.
2. View model fetches holdings and today's digest concurrently.
3. Holdings are enriched on the backend with latest grade, score, previous grade, labels, and summary.
4. Digest provides portfolio summary text and overall grade/score when available.
5. If digest is missing, the dashboard still derives a portfolio grade from holdings.

Manual actions:

- pull-to-refresh runs `loadData()` again
- dashboard can trigger a full analysis via `triggerFreshAnalysis()`

Analysis refresh behavior:

- `POST /trigger-analysis`
- then poll `GET /analysis-runs/{id}` every 2 seconds
- if completed, reload holdings + digest
- if failed, show error
- if it runs too long, show "Analysis taking longer than expected. You can leave this screen."

## 3. Holdings screen

Files:

- `ios/Clavis/Views/Holdings/HoldingsListView.swift`
- `ios/Clavis/ViewModels/HoldingsViewModel.swift`

Purpose:

- show all tracked positions
- add and delete positions
- inspect holdings by risk grade and trend

Primary data source:

- `GET /holdings`

Main UI states:

- loading state
- empty state
- populated list state
- add-position sheet
- full-screen add-progress flow
- alert for errors

Holdings list behavior:

- holdings are filterable by `HoldingFilter`
- sortable by `HoldingSort`
- rows are `NavigationLink`s to `PositionDetailView`
- delete uses native `.swipeActions`

Holding row contents:

- risk grade badge
- ticker
- one-line position summary
- numeric score
- trend icon

### Add position flow

Files within same view:

- `AddPositionSheet`
- `AddPositionProgressView`

Data flow when adding:

1. User opens add sheet.
2. User enters ticker, shares, purchase price, archetype.
3. `HoldingsViewModel.addHolding` calls `POST /holdings`.
4. Created position is inserted locally immediately.
5. App then triggers analysis with `POST /trigger-analysis` targeting that `position_id`.
6. App polls `GET /analysis-runs/{id}`.
7. Full-screen progress view renders stage-specific copy.
8. When analysis completes, the user can open the new position directly.

Relevant backend behavior:

- backend inserts the position
- starts a background price refresh if needed
- targeted analysis only refreshes that holding; it does not necessarily rebuild the full digest

### Delete position flow

1. User swipes delete.
2. The row is removed optimistically on the client.
3. `DELETE /holdings/{id}` runs.
4. If delete fails, the row is restored.

Backend delete behavior:

- detaches related `analysis_runs.target_position_id`
- deletes that position's `event_analyses`
- deletes that position's `position_analyses`
- deletes that position's `risk_scores`
- deletes the `positions` row

## 4. Position Detail screen

Files:

- `ios/Clavis/Views/PositionDetail/PositionDetailView.swift`
- `ios/Clavis/Views/PositionDetail/PriceChartView.swift`

Purpose:

- give a complete per-holding view of risk, price, developments, and event analysis

Primary data sources:

- `GET /positions/{id}`
- `GET /prices/{ticker}?days=...`

Screen sections:

- `PositionSummaryHero`
- `PositionSnapshotCard`
- `PriceAndTrendSection`
- optional `AnalysisProgressCard`
- `RiskDriversCard`
- `RecentDevelopmentsCard`
- `WhatToWatchCard`
- `EventAnalysesCard`
- or `NoAnalysisCard` if no analysis exists yet

### Position detail response contents

The backend assembles one combined payload with:

- raw position row
- latest risk score
- latest position analysis report
- methodology text
- dimension breakdown
- latest event analyses
- recent news items
- recent alerts for that ticker

### Price chart flow

`PriceChartView`:

- normalizes to latest point per day
- renders a line chart with color depending on up/down performance
- supports 7D / 30D / 90D windows

### Manual refresh on position detail

- toolbar button labeled `Refresh`
- pull-to-refresh also exists here
- both call a targeted `POST /trigger-analysis` with `position_id`
- then poll `GET /analysis-runs/{id}`
- while running, `AnalysisProgressCard` shows current stage message

## 5. Event Analysis detail screen

Contained inside `PositionDetailView.swift`

Purpose:

- turn an individual event into a structured risk brief for one holding

Navigation:

- user taps an event row under `Event Analyses`

Data source:

- event analysis data is already included in `GET /positions/{id}`
- no second fetch is needed for event detail

Current structure:

- title + subtle significance pill
- ticker, source, published date
- Event Summary
- Market Interpretation
- Position Impact
- Action Signal
- optional Confidence

Logic notes:

- summary prefers full `longAnalysis`
- market interpretation prefers `scenarioSummary`
- position impact prefers `keyImplications` then `recommendedFollowups`
- action signal is inferred from `riskDirection`, confidence, and significance

## 6. Morning Digest screen

Files:

- `ios/Clavis/Views/Digest/DigestView.swift`
- `ios/Clavis/ViewModels/DigestViewModel.swift`

Purpose:

- present the daily portfolio briefing
- show whether a new analysis run is in progress
- keep older digest visible while a new report is generating

Primary data sources:

- `GET /digest`
- `GET /digest/history`
- `GET /holdings`
- `GET /alerts`
- `POST /trigger-analysis`
- `GET /analysis-runs/{id}`

Render precedence in the current code:

1. running analysis banner if there is an active queued/running run
2. error card if digest fetch failed or run failed
3. timeout card if a run is overdue
4. digest content if a digest exists
5. idle empty state only if there is no digest, no running run, no error, and no loading state
6. loading card only if nothing else should win

Important current UX choice:

- pull-to-refresh was removed from this screen
- refresh now happens through the toolbar button / on-appear loading / analysis completion flow
- if a fetch fails, the screen tries to preserve the previously loaded digest instead of blanking the UI

Digest sections:

- score summary card
- lead card with generated timestamp
- What Changed
- What Matters Today
- What To Do
- Positions
- expandable Full Narrative markdown section

### Digest generation flow from frontend perspective

1. Screen appears.
2. `DigestViewModel.loadDigest()` runs.
3. It fetches digest, digest history, holdings, and alerts concurrently.
4. The `/digest` response also includes the latest `analysis_run` so the UI can restore running/failed/completed state from one payload.
5. If a run is active, `AnalysisRunStatusCard` is shown.
6. If a digest exists, it remains visible even while a new run is generating.

### Manual digest refresh / new review flow

- Toolbar refresh button triggers `triggerAnalysis()`.
- That calls `POST /trigger-analysis` without a target position.
- App polls the run until terminal or timeout.
- On completion it waits briefly for the digest row to exist, then reloads the digest screen data.

## 7. Alerts screen

Files:

- `ios/Clavis/Views/Alerts/AlertsView.swift`
- `ios/Clavis/ViewModels/AlertsViewModel.swift`

Purpose:

- show recent alerts and group repeated similar alerts

Primary data source:

- `GET /alerts`

Behavior:

- alerts are grouped if they share type, ticker, and happen within one hour
- empty state is shown if there are no alerts
- pull-to-refresh reloads the alert list

Alert types currently modeled in the app:

- grade change
- major event
- portfolio grade change
- digest ready
- safety deterioration
- concentration danger
- cluster risk
- macro shock
- structural fragility
- portfolio safety threshold breach

## 8. Settings screen

Files:

- `ios/Clavis/Views/Settings/SettingsView.swift`
- `ios/Clavis/ViewModels/SettingsViewModel.swift`

Purpose:

- account management
- digest scheduling settings
- alert preferences
- methodology/help pages

Primary data sources:

- `GET /preferences`
- `PATCH /preferences`
- `PATCH /preferences/alerts` from the iOS client contract, though backend currently only implements core preference patching and device-token registration in the route file that was inspected
- Supabase auth user for email display

Main sections:

- Account
- Digest
- Alerts
- About

Capabilities:

- show current user email
- sign out
- set digest delivery time
- set summary length locally and send it through preferences payload
- toggle weekday-only digests locally and send it through preferences payload
- toggle alert preferences and quiet hours from the iOS side
- open `ScoreExplanationView`
- open `MethodologyView`
- open privacy policy and terms links

### Settings sub-screens

#### Score Explanation

- explains 0-100 scores
- explains A-F mapping
- explains the five dimensions shown in the UI copy

#### Methodology

- explains the conceptual scoring dimensions
- explains that scores recalculate on new events, manual refreshes, digest compilation, and scheduled sweeps

## 9. Shared browser screen

File: `ios/Clavis/Views/Shared/SafariView.swift`

Purpose:

- open external URLs inside the app when needed using `SFSafariViewController`

## Frontend model layer

Important iOS models:

- `Position`: base holding plus latest enriched risk fields
- `RiskScore`: current safety and factor breakdown for a position
- `PositionAnalysis`: long-form position report and watch/risk lists
- `EventAnalysis`: structured event-level analysis for a single news item
- `Digest`: daily portfolio digest row
- `AnalysisRun`: persisted job state used by Dashboard, Holdings, Digest, and Position Detail
- `Alert`: user-facing alert rows
- `UserPreferences`: digest time, notifications, APNs token

## Backend Route Layer

## `GET /holdings`

What it does:

- fetches all user positions
- backfills missing current prices asynchronously
- attaches latest and previous risk grades from `risk_scores`
- attaches latest position analysis labels and summary from `position_analyses`

Used by:

- Dashboard
- Holdings
- Digest

## `POST /holdings`

What it does:

- inserts a new position row
- sets `current_price` to `None` initially
- triggers background price refresh

Used by:

- Add Position sheet

## `DELETE /holdings/{id}`

What it does:

- deletes a position and its directly-owned analytical artifacts
- preserves analysis run history by nulling `target_position_id` first

Used by:

- Holdings swipe-to-delete

## `GET /positions/{id}`

What it does:

- returns a full position detail payload
- fetches latest risk score
- fetches latest position analysis
- fetches recent relevant news
- fetches latest event analyses
- fetches recent alerts for that ticker

Used by:

- Position Detail screen

## `GET /digest`

What it does:

- fetches today's digest for the user
- also fetches the latest analysis run and enriches it with digest linkage/status
- returns `digest: null` with job state if digest has not yet been generated

Used by:

- Digest screen
- Dashboard

## `GET /digest/history`

- returns recent digest rows
- currently used by the Digest screen view model

## `GET /alerts`

- returns most recent alerts for the user

## `GET /prices/{ticker}`

What it does:

- first tries cached `prices` table history
- if insufficient, fetches Polygon aggregates
- stores them into the `prices` table
- returns normalized daily price points

Used by:

- Position Detail chart

## `POST /trigger-analysis`

What it does:

- starts an analysis run for the whole portfolio or a single position
- returns the created or reused analysis run ID

Used by:

- Dashboard refresh
- Digest refresh / fresh review
- Position Detail refresh
- Add Position flow

## `GET /analysis-runs/latest`

- returns most recent persisted analysis run for the user
- used as a job-state restoration endpoint

## `GET /analysis-runs/{id}`

- returns a single analysis run with enriched fields:
  - normalized status
  - progress
  - digest ID
  - overall grade
  - generated time
  - `digest_ready`
  - `events_analyzed`

Used by:

- all polling-based analysis UI

## `GET /preferences`

- returns current user preferences
- defaults to `07:00` and notifications off if no row exists

## `PATCH /preferences`

- updates digest time and/or notifications enabled
- reschedules the user's APScheduler job

## `POST /preferences/device-token`

- stores APNs token
- enables notifications
- reschedules scheduler state

## `GET /scheduler/status`

- returns runtime and persisted scheduler state for the current user

## `POST /test-push`

- sends a real APNs test notification using stored device token

## Backend Pipeline: End-to-End Analysis Flow

The scheduler pipeline in `backend/app/pipeline/scheduler.py` is the core of the app.

## Analysis run lifecycle

### Step 1: enqueue

`enqueue_analysis_run(...)`

- marks stale or orphaned runs failed
- checks for any currently queued/running runs for the user
- if one exists and is still active, returns the existing run
- otherwise creates a new `analysis_runs` row and spawns the worker task

### Step 2: create run row

`create_analysis_run(...)`

The new row starts with:

- `status = queued`
- `current_stage = queued`
- `current_stage_message = Queued for analysis.`
- optional `target_position_id`

### Step 3: execute analysis

`execute_analysis_run(...)` stages:

1. `starting`
2. `refreshing_metadata`
3. `fetching_news`
4. `classifying_relevance`
5. `analyzing_events`
6. `running_mirofish` for major events only
7. `scoring_position`
8. `refreshing_prices`
9. `computing_portfolio_risk`
10. `building_digest` for portfolio-wide runs
11. `completed` or `failed`

### Step 4: refresh ticker metadata

For each ticker:

- `upsert_ticker_metadata(...)` runs
- metadata later feeds deterministic structural scoring and portfolio-risk logic

### Step 5: collect news

News sources:

- Finnhub company news
- Finnhub market news
- RSS feeds from Bloomberg, NYT Markets, FT Markets

News is normalized and deduplicated by `event_hash`.

### Step 6: relevance classification

`classify_relevance(...)` decides whether an article matters to this user's holdings.

Logic:

- drop obvious noise/promotional content
- accept direct ticker or alias matches immediately
- otherwise, if it looks macro/thematic, ask MiniMax whether it matters to the current portfolio

Outputs:

- `relevant`
- `affected_tickers`
- `event_type`
- `why_it_matters`

Relevant news is also stored into `news_items`.

### Step 7: classify each holding

For each position:

- `classify_position(...)` assigns 1-4 inferred labels
- example categories include styles, sectors, themes, and sensitivities

### Step 8: classify event significance

For each relevant article:

- `classify_significance(...)` returns `major` or `minor`
- also returns event type and a short explanation

### Step 9: event-level analysis

If event is major:

- run `mirofish_analyze(...)`
- used for deeper major-event analysis

If event is minor:

- run `analyze_minor_event(...)`
- uses MiniMax with a lighter structured event-analysis prompt

Each event analysis stores:

- title
- summary
- source URL
- published time
- significance
- event type
- long analysis
- confidence
- impact horizon
- risk direction
- scenario summary
- key implications
- recommended follow-ups

These rows are written into `event_analyses`.

### Step 10: progressive draft snapshots

While analysis is still running, the pipeline continuously writes draft `position_analyses` rows with:

- inferred labels
- early headline list
- progress message
- source count

This is why some UI can show partial analysis context before the full report is done.

### Step 11: build long-form position report

`build_position_report(...)` synthesizes all event analyses into:

- summary
- long report
- methodology
- top risks
- watch items

This gets written into `position_analyses` with status `ready`.

### Step 12: score the position

Two scoring tracks exist.

#### A. LLM-assisted dimension scoring

`score_position(...)` asks MiniMax to score:

- news sentiment
- macro exposure
- position sizing
- volatility trend

It returns:

- per-dimension scores
- total score
- grade
- reasoning
- dimension rationale

#### B. Deterministic structural scoring

`score_position_structural(...)` uses ticker metadata and event adjustments to compute:

- structural base score
- macro adjustment
- event adjustment
- final safety score
- confidence
- factor breakdown

The current backend stores both the LLM-derived fields and structural fields into `risk_scores`, with `safety_score` coming from the structural track.

### Step 13: create alerts

The pipeline can write alerts for:

- grade changes
- major events
- portfolio grade changes
- safety deterioration
- concentration danger
- cluster risk
- digest ready

When notifications are enabled and an APNs token exists, push notifications are sent too.

### Step 14: refresh prices and chart data

- current prices are refreshed for positions
- recent aggregate bars are stored in `prices`

### Step 15: compute portfolio risk

`calculate_portfolio_risk_score(...)` combines:

- concentration risk
- cluster risk
- correlation risk
- liquidity mismatch
- macro stack risk

This writes daily rows into `portfolio_risk_snapshots`.

### Step 16: compile morning digest

For full-portfolio runs only:

- portfolio score/grade is computed using weighted holdings
- `compile_portfolio_digest(...)` produces:
  - markdown narrative content
  - overall summary
  - `major_events`
  - `watch_list`
  - `portfolio_advice`

The result is inserted into `digests`.

### Step 17: finalize run

The run row is updated with:

- `status = completed` or `failed`
- `completed_at`
- `overall_portfolio_grade`
- `positions_processed`
- `events_processed`

If any exception escapes the pipeline, the run is marked failed and `error_message` is set to the exception text.

## Scheduler behavior

Clavis runs a per-user daily digest scheduler inside the FastAPI process.

Sources of scheduler truth:

- `user_preferences`
- runtime APScheduler jobs
- persisted `scheduler_jobs` table

Main scheduler functions:

- `reschedule_user_digest(user_id)` updates the user's scheduled digest job
- `get_scheduler_status_for_user(user_id)` returns runtime + persisted scheduling state
- `start_scheduler()` rebuilds all jobs on backend startup

Scheduled jobs are only active when notifications are enabled in the persisted preferences path that the scheduler reads.

## External integrations

### Supabase

Used for:

- auth on iOS
- all application tables on backend
- service-role database access in Python

### Finnhub

Used for:

- company news
- market news
- quote fallback when Polygon snapshot is unavailable
- ticker metadata like market cap, volume proxies, float, beta

### Polygon

Used for:

- current price snapshot when authorized
- aggregate bars for chart history

### RSS feeds

Used for:

- broad financial news supplementation

### MiniMax

Used for:

- relevance classification for macro/thematic articles
- significance classification support
- minor-event analysis
- position classification
- position report generation
- dimension scoring
- portfolio digest generation

### MiroFish

Used for:

- deeper analysis of major events only

### APNs

Used for:

- digest-ready pushes
- grade-change pushes
- major-event pushes
- portfolio-grade-change pushes
- test push route

## Current core tables implied by the code

- `positions`
- `risk_scores`
- `position_analyses`
- `event_analyses`
- `news_items`
- `digests`
- `alerts`
- `user_preferences`
- `analysis_runs`
- `prices`
- `ticker_metadata`
- `portfolio_risk_snapshots`
- `asset_safety_profiles`
- `scheduler_jobs`
- `analysis_cache`

## How data reaches each major screen

## Dashboard

- `DashboardView` -> `DashboardViewModel.loadData()`
- `APIService.fetchHoldings()` -> `GET /holdings`
- `APIService.fetchTodayDigest()` -> `GET /digest`
- view model derives aggregate stats locally

## Holdings

- `HoldingsListView` -> `HoldingsViewModel.loadHoldings()`
- `GET /holdings`
- local filter/sort only after fetch

## Add Position progress

- `POST /holdings`
- `POST /trigger-analysis` with `position_id`
- poll `GET /analysis-runs/{id}`
- optional final navigation to `PositionDetailView`

## Position Detail

- `GET /positions/{id}`
- `GET /prices/{ticker}?days=7|30|90`
- optional `POST /trigger-analysis` with `position_id`
- poll `GET /analysis-runs/{id}` during refresh

## Event Analysis detail

- no extra fetch
- uses `detail.latestEventAnalyses` already returned from `/positions/{id}`

## Digest

- `GET /digest`
- `GET /digest/history`
- `GET /holdings`
- `GET /alerts`
- `POST /trigger-analysis`
- poll `GET /analysis-runs/{id}`

## Alerts

- `GET /alerts`
- grouped client-side by type/ticker/time window

## Settings

- `GET /preferences`
- `PATCH /preferences`
- `POST /preferences/device-token`
- Supabase user email comes from auth session, not backend

## How the app currently behaves in practice

### Strengths in the current design

- Every main screen has a dedicated view model or local state owner.
- The backend keeps long-running analysis state in `analysis_runs`, which allows the UI to restore in-progress jobs.
- The app stores structured event analyses and long-form position reports separately.
- The digest is not just text; it also exposes machine-friendly sections used by the UI.
- The pipeline uses progressive drafts, so users can sometimes see early context before final scoring completes.
- Portfolio risk is not just an average of position grades; it also includes concentration and cluster logic.

### Important current implementation realities

- The backend JWT validation is a lightweight payload decode, not a full cryptographic verification layer inside FastAPI.
- The digest screen currently avoids pull-to-refresh because that UX was destabilizing trust.
- Position Detail still supports pull-to-refresh.
- Holdings and Alerts still support pull-to-refresh.
- Settings iOS code sends some preference fields like summary length, weekday only, and alert settings, but the backend route file inspected only clearly implements core digest time / notifications patching and device token registration. That suggests a contract mismatch or incomplete backend coverage for some settings UI.
- Analysis failures are persisted on the run row and can be surfaced later unless a new successful run replaces the visible state.

## Mental model of the whole product

The cleanest way to think about Clavis is:

1. The user authenticates with Supabase.
2. The user adds positions.
3. A backend analysis run is queued.
4. The backend fetches news, filters relevance, classifies significance, runs event analysis, writes event rows, writes position analysis rows, scores positions, computes portfolio risk, and compiles a digest.
5. The iOS app reads different slices of that same underlying data:
   - holdings list for compact portfolio scan
   - position detail for per-name deep dive
   - digest for daily cross-portfolio narrative
   - alerts for change detection
   - settings for timing and notification control

That is the current system as implemented in the codebase right now.
