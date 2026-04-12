# Clavis Backend Overview

This document explains the backend in `backend/` end to end: how requests enter the API, how the news pipeline works, how the AI prompts are used, what gets stored in Supabase, and how scheduled digests and alerts are produced.

---

## 1. What The Backend Does

The backend is a FastAPI application that turns a user's portfolio into a daily risk-intelligence feed.

In practice, it:

1. Authenticates the user with a Supabase JWT.
2. Loads their holdings from Supabase.
3. Pulls news from RSS and Finnhub.
4. Normalizes and deduplicates the news.
5. Filters the news to what matters for the user's holdings.
6. Classifies relevant events as major or minor.
7. Writes detailed event analyses, position analyses, risk scores, digests, and alerts back to Supabase.
8. Sends APNs push notifications when configured.

The backend is intentionally opinionated: it is not a general finance API. It is a pipeline for answering one question well: "Has anything changed that affects the safety of what I own?"

---

## 2. Main Runtime Pieces

### FastAPI app

The app is defined in `backend/app/main.py`.

Key responsibilities:

- Sets up FastAPI and CORS.
- Validates APNs configuration at startup.
- Starts the APScheduler instance on launch.
- Enforces JWT auth for all portfolio-facing routes.
- Registers all routers.

### Authentication

Authentication is based on the `Authorization: Bearer <jwt>` header.

Important detail:

- The middleware in `backend/app/main.py` does not fully re-verify the JWT signature itself.
- It base64-decodes the payload, checks that `sub` exists, and uses that as `request.state.user_id`.
- The code assumes Supabase has already minted a valid token.

### Services

The backend talks to three major service layers:

- `backend/app/services/supabase.py` for database access
- `backend/app/services/minimax.py` for LLM calls
- `backend/app/services/polygon.py` and `backend/app/services/apns.py` for market data and push notifications

---

## 3. API Surface

The backend exposes these routes:

- `GET /health`
- `GET /holdings`
- `POST /holdings`
- `GET /holdings/{id}`
- `PATCH /holdings/{id}`
- `DELETE /holdings/{id}`
- `GET /positions/{id}`
- `GET /digest`
- `GET /digest/history`
- `GET /alerts`
- `GET /preferences`
- `PATCH /preferences`
- `POST /preferences/device-token`
- `POST /trigger-analysis`
- `GET /analysis-runs/{id}`
- `GET /prices/{ticker}`
- `GET /scheduler/status`
- `POST /test-push`

### Route responsibilities

#### `/holdings`

Implemented in `backend/app/routes/holdings.py`.

- Lists a user's positions.
- Adds a position.
- Deletes a position.
- On read, it attaches the latest risk score and previous grade when available.
- If `current_price` is missing, it schedules a background price refresh.

#### `/positions/{id}`

Implemented in `backend/app/routes/positions.py`.

Returns a deep detail view:

- Position metadata
- Latest risk score
- Latest position analysis
- Risk dimension breakdown
- Recent event analyses
- Recent news items
- Recent alerts

#### `/digest`

Implemented in `backend/app/routes/digest.py`.

- Returns the latest digest generated today.
- Also supports `GET /digest/history`.

#### `/alerts`

Implemented in `backend/app/routes/alerts.py`.

- Returns the user's latest alerts, newest first.

#### `/preferences`

Implemented in `backend/app/routes/preferences.py`.

- Reads and updates `digest_time` and `notifications_enabled`.
- Stores APNs device tokens.
- Reschedules the user's digest job after changes.

#### `/trigger-analysis`

Implemented in `backend/app/routes/trigger.py`.

- Manually starts the analysis pipeline.
- Optionally targets one holding only.

#### `/analysis-runs/{id}`

Implemented in `backend/app/routes/analysis_runs.py`.

- Returns the analysis run record.
- Also resolves the linked digest, if one exists.

#### `/prices/{ticker}`

Implemented in `backend/app/routes/prices.py`.

- Returns historical prices from Supabase if available.
- Falls back to Polygon aggregations and stores them.

#### `/scheduler/status`

Implemented in `backend/app/routes/scheduler.py`.

- Returns the user's scheduler state, next run time, and persisted scheduling metadata.

#### `/test-push`

Implemented in `backend/app/routes/test_push.py`.

- Sends a real APNs test notification to the registered device token.

---

## 4. Data Model

The backend writes to Supabase tables that roughly map to the product's core objects.

### Core tables

- `positions`
  - The user's holdings
  - Fields include `ticker`, `shares`, `purchase_price`, `archetype`, and `current_price`

- `risk_scores`
  - One score record per position per analysis run
  - Stores the A-F grade plus the five scoring dimensions

- `news_items`
  - Relevant news items after filtering
  - Stores the event hash, relevance metadata, and affected ticker(s)

- `event_analyses`
  - Per-article analysis outputs
  - Stores significance, analysis text, direction of risk, follow-ups, and provenance

- `position_analyses`
  - The synthesized report for a position during an analysis run
  - Stores summary, long report, methodology, top risks, and watch items

- `digests`
  - The morning portfolio digest
  - Stores overall grade, structured sections, and summary content

- `alerts`
  - Grade changes, major events, portfolio grade changes, and digest-ready notifications

- `user_preferences`
  - Digest time, notification settings, APNs token

- `analysis_runs`
  - Tracks each pipeline run and stage progress

- `analysis_cache`
  - Caches expensive AI outputs like relevance and significance classifications

- `scheduler_jobs`
  - Persisted scheduler state per user

- `prices`
  - Historical price series for charting and lookup

### Model classes

The Pydantic models live in `backend/app/models/` and mirror the main data objects:

- `Position`
- `RiskScore`
- `Digest`
- `Alert`

---

## 5. News Ingestion

The ingestion layer has three sources.

### RSS feeds

Implemented in `backend/app/pipeline/rss_ingest.py`.

Sources:

- Bloomberg markets RSS
- New York Times markets RSS
- Financial Times markets RSS

Behavior:

- Pulls the latest items from each feed.
- Limits each feed to the first 20 entries.
- If tickers are not provided, it returns the articles as general market items.
- If tickers are provided, it only keeps items whose titles contain one of the tickers.

Important limitation:

- RSS matching is title-based only in the current code.
- It does not do a full article crawl or body extraction from the feed sources.

### Finnhub company news

Implemented in `backend/app/pipeline/finnhub_news.py`.

Behavior:

- For each holding ticker, fetches company news for the last two days.
- Keeps up to 10 items per ticker.
- Also fetches up to 15 general market items.
- Returns empty results if the Finnhub key is not configured.

### News normalization

Implemented in `backend/app/pipeline/news_normalizer.py`.

Each article is normalized into a common shape:

- `external_id`
- `event_hash`
- `source_type`
- `source`
- `title`
- `summary`
- `body`
- `url`
- `published_at`
- `ticker_hints`
- `raw`

Important details:

- Timestamps are normalized to UTC when possible.
- `event_hash` is a SHA-256 hash built from id, URL, title, summary snippet, and timestamp.
- Ticker hints are uppercased and deduplicated.

### Deduplication

The scheduler deduplicates articles by `event_hash`.

That means the same event coming from multiple feeds is collapsed before classification.

---

## 6. Filtering And Relevance

The backend uses a layered relevance system in `backend/app/pipeline/relevance.py`.

### Company-specific relevance

For direct ticker matching, the code uses a curated alias map:

- `AAPL` -> `apple`, `aapl`
- `MSFT` -> `microsoft`, `msft`
- `GOOGL` -> `google`, `alphabet`, `googl`
- `NVDA` -> `nvidia`, `gpu`
- and similar entries for a set of major names

If the title or summary contains the ticker or one of its aliases, the item is considered relevant.

### Noise filtering

The code explicitly suppresses some low-value content patterns such as:

- ETF chatter
- Seeking Alpha-style promotional content
- Motley Fool content
- "convincing buy opportunity" language

If those patterns appear without any ticker hint, the article is marked irrelevant.

### Macro/thematic prefilter

If no company-specific match exists, the pipeline checks whether the article contains macro keywords such as:

- Fed
- interest rate
- yield
- inflation
- oil
- tariff
- antitrust
- SEC
- DOJ

Only if the article looks macro-relevant does it move to the LLM relevance step.

### LLM relevance classification

When needed, `classify_relevance()` sends the article and the portfolio context to MiniMax and asks for strict JSON.

The prompt asks for:

- `relevant`
- `affected_tickers`
- `event_type`
- `why_it_matters`

The code then enforces that:

- the response must mark at least one affected ticker
- otherwise the item is treated as irrelevant

### Relevance caching

Relevance results are cached in `analysis_cache` for 12 hours using the article's event hash.

That reduces repeated calls when the same article reappears in later runs.

---

## 7. Significance Classification

Implemented in `backend/app/pipeline/classifier.py`.

This step answers:

- Is this a major event or a minor one?
- What kind of event is it?
- Why does it matter?

### Prompt behavior

The prompt defines:

- `MAJOR` events like earnings surprises, Fed decisions, M&A, regulatory actions, management exits, bankruptcy, and major recalls
- `MINOR` events like analyst rating changes, routine economic data, price target updates, and general market commentary

The model must return strict JSON:

```json
{
  "significance": "major|minor",
  "event_type": "earnings|macro|management|mna|regulatory|product|financing|sector|other",
  "why_it_matters": "one sentence",
  "confidence": 0.0-1.0
}
```

### Caching

Significance is cached in `analysis_cache` for 24 hours by event hash.

---

## 8. Minor Event Analysis

Implemented in `backend/app/pipeline/agentic_scan.py`.

If an event is minor, the backend performs a shorter structured analysis.

### Prompt goal

The model analyzes the event relative to the position and returns:

- `analysis_text`
- `impact_horizon`
- `risk_direction`
- `confidence`
- `scenario_summary`
- `key_implications`
- `recommended_followups`

### Fallback behavior

If the model output is malformed or thin, the backend falls back to a deterministic summary that:

- labels the event as monitorable
- defaults the horizon to `near_term`
- defaults the risk direction to `neutral`

### Cache

Minor event analyses are cached in `analysis_cache` for 18 hours using a composite key of event hash and ticker.

---

## 9. Major Event Analysis

Major events are routed through `backend/app/pipeline/mirofish_analyze.py`.

### Primary path

If `MIROFISH_URL` is configured:

- the backend tries to POST `{ news, position }` to the MiroFish service
- if that succeeds, the response is normalized and used directly

### Fallback path

If MiroFish is unavailable or returns an unusable response, the backend falls back to MiniMax using a strict JSON prompt.

The fallback prompt asks for:

- `analysis_text`
- `impact_horizon`
- `risk_direction`
- `confidence`
- `scenario_summary`
- `key_implications`
- `recommended_followups`

This makes the major-event path resilient even if the swarm service is down.

---

## 10. Position Classification

Implemented in `backend/app/pipeline/position_classifier.py`.

This step infers a few concise labels that help the later prompts understand the holding's style and theme exposure.

### Prompt output

It returns strict JSON like:

```json
{
  "labels": ["growth", "ai_theme"],
  "summary": "one sentence"
}
```

### Label rules

- Return 1 to 4 short snake_case labels
- Labels can describe style, factor, theme, or sensitivity
- If no event context exists, fall back to the position's manual archetype or `core`

These labels are later injected into the report and risk scoring prompts.

---

## 11. Position Report Generation

Implemented in `backend/app/pipeline/position_report_builder.py`.

This stage takes the position context and the collected event analyses and turns them into a position-level narrative.

### Prompt output

The model returns strict JSON:

```json
{
  "summary": "2-3 sentence executive summary",
  "long_report": "4-8 sentence detailed report",
  "methodology": "brief explanation of the evidence and framework used",
  "top_risks": ["risk 1", "risk 2", "risk 3"],
  "watch_items": ["watch item 1", "watch item 2"]
}
```

### Fallback

If the model output is missing or malformed, the backend synthesizes a deterministic report from:

- event significance counts
- risk direction counts
- inferred labels
- recent event titles

If no events exist, the report says there were no material new risk events in the cycle.

---

## 12. Risk Scoring

Implemented in `backend/app/pipeline/risk_scorer.py`.

This is the core grading step.

### Inputs

The scoring prompt receives:

- ticker
- shares
- purchase price
- inferred labels
- position report summary
- long-form position report

### The five dimensions

Each dimension is scored from 0 to 100:

1. `news_sentiment`
2. `macro_exposure`
3. `position_sizing`
4. `volatility_trend`
5. `thesis_integrity`

### Grade mapping

The weighted average of those five scores becomes the total score, then maps to a grade:

- `A` >= 80
- `B` >= 65
- `C` >= 50
- `D` >= 35
- `F` otherwise

### Prompt output

The model must return exact JSON with:

- the five dimension scores
- `grade`
- `reasoning`
- `dimension_rationale`

### Guardrails

- Scores are clamped to `0..100`
- Invalid grades are normalized back to `C`
- The model's reasoning is preserved for downstream UI and storage

---

## 13. Digest Compilation

Implemented in `backend/app/pipeline/portfolio_compiler.py`.

This is the final portfolio-level synthesis step.

### What it does

It takes all completed position payloads, sorts them by urgency, and asks MiniMax to write a compact morning briefing.

### Prompt rules

The prompt explicitly tells the model:

- this is a morning portfolio digest, not a market essay
- focus on what changed and what matters today
- only discuss the user's real holdings
- lead with the single most important takeaway
- keep it concise and decisive

### Required format

The model must return strict JSON with:

- `content`
- `overall_summary`
- `sections`
  - `major_events`
  - `watch_list`
  - `portfolio_advice`

### Fallback behavior

If the model output is missing, the backend generates a deterministic digest that:

- highlights the riskiest holding first
- lists a short watch item per position
- keeps the output plain and short

---

## 14. Analysis Scheduler And Run Lifecycle

The orchestration layer lives in `backend/app/pipeline/scheduler.py`.

This is the biggest backend file and it manages the full analysis lifecycle.

### Run flow

1. Create an `analysis_runs` row.
2. Fetch the user's positions.
3. Pull news from RSS, Finnhub company news, and Finnhub market news.
4. Normalize and dedupe all articles.
5. Classify article relevance against the portfolio.
6. For each relevant article:
   - classify significance
   - route major events to MiroFish or the MiniMax fallback
   - route minor events to the minor-event analyzer
   - write `event_analyses`
7. For each position:
   - classify position labels
   - build a draft position snapshot while analysis is still in progress
   - generate the full position report
   - score the position
   - write `risk_scores` and `position_analyses`
8. Refresh current prices and historical prices.
9. Build the digest if the run is portfolio-wide.
10. Create alerts when grades change or a major event is detected.
11. Send push notifications if APNs is enabled.
12. Mark the analysis run completed, partial, or failed.

### Concurrency and timeout behavior

Important constants:

- `RUN_TIMEOUT_SECONDS = 25 * 60`
- `POSITION_CONCURRENCY = 2`
- `MAX_ARTICLES_PER_POSITION = 3`

The run is wrapped in a timeout. If it exceeds the limit, the backend tries to finalize a partial digest from the completed positions rather than throwing away all progress.

### Caching

The scheduler caches:

- relevance decisions
- significance decisions
- minor-event analyses

That keeps repeated runs cheaper and faster.

### Partial progress

The scheduler writes "draft" position analyses while the deeper event analysis is still running.

That means the UI can show progress before the final score lands.

### Run stages

The `analysis_runs.current_stage` field is updated throughout the process with messages such as:

- queued
- starting
- fetching_news
- classifying_relevance
- analyzing_events
- scoring_position
- refreshing_prices
- building_digest
- completed
- failed

---

## 15. Alerting And Notifications

### Alert creation

The scheduler creates alerts for:

- major events
- grade changes
- portfolio grade changes
- digest readiness

Alerts are deduplicated by type and time window, and major-event alerts can also be deduped by event hash.

### APNs push notifications

Implemented in `backend/app/services/apns.py` and used through `backend/app/pipeline/notifier.py`.

The backend can send:

- digest notifications
- grade change notifications
- major event notifications
- portfolio grade change notifications

If APNs is not configured, the backend logs the issue and skips delivery safely.

### Device registration

The user's APNs token is stored in `user_preferences` through `POST /preferences/device-token`.

---

## 16. Price Data

Implemented in `backend/app/services/polygon.py` and exposed through `backend/app/routes/prices.py`.

### Current price lookup

- Tries Polygon first.
- Falls back to Finnhub if Polygon is missing or rejected.
- Updates `positions.current_price` in the background when possible.

### Historical prices

- Uses Polygon daily aggregates.
- Stores them in the `prices` table.
- Returns stored history when it exists.

This layer supports charting and portfolio valuation.

---

## 17. Caching, Deduping, And Fallback Philosophy

A lot of the backend design is about graceful degradation.

### If the AI returns malformed output

The code uses safe JSON parsing helpers in `backend/app/pipeline/analysis_utils.py`.

If parsing fails, the backend falls back to deterministic summaries instead of crashing the whole run.

### If a news source is missing

- Missing Finnhub key -> company and market news return empty lists
- Missing RSS article body -> the pipeline still works on title and summary
- Missing MiroFish -> MiniMax fallback handles major events

### If a run times out

The scheduler tries to finalize a partial digest if enough position work was completed.

### If a duplicate run is queued

The scheduler blocks overlapping runs for the same user and returns the active run instead of starting a duplicate.

---

## 18. Environment Settings

Configuration is read from `.env` via `backend/app/config.py`.

Important settings:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `MINIMAX_API_KEY`
- `MINIMAX_BASE_URL`
- `MIROFISH_URL`
- `FINNHUB_API_KEY`
- `APNS_KEY_ID`
- `APNS_TEAM_ID`
- `APNS_KEY_PATH`
- `APNS_BUNDLE_ID`
- `POLYGON_API_KEY`

The backend uses a service role Supabase client, so access control is enforced in application logic and in the database's RLS layer.

---

## 19. What The Prompts Actually Ask For

This is a condensed catalog of the AI prompts embedded in the backend.

### Relevance prompt

Asks whether a macro or thematic article matters to the user's portfolio, and if so, which tickers it affects.

### Significance prompt

Asks whether a relevant article is major or minor, and classifies the event type.

### Minor event analysis prompt

Asks for a short, position-aware analysis of the event's impact horizon and risk direction.

### Major event prompt

Asks for a deeper, scenario-oriented analysis of a major catalyst.

### Position classifier prompt

Asks for compact style/theme labels that help the rest of the pipeline reason about the holding.

### Position report prompt

Asks for a long-form, evidence-based report for one position.

### Risk scorer prompt

Asks for five numerical dimension scores, a grade, and written reasoning.

### Portfolio digest prompt

Asks for a concise morning briefing with a clear action focus and a per-position breakdown.

---

## 20. Practical Mental Model

If you want to understand the backend in one sentence:

**The backend is a staged news-to-risk pipeline that turns raw financial news into position-level analysis, risk grades, portfolio digests, and alerts, with caching and fallback paths at every step.**

If you want to debug it, the most useful progression is:

1. `analysis_runs` for stage status
2. `news_items` and `event_analyses` for article flow
3. `position_analyses` for the synthesized report
4. `risk_scores` for the final grade
5. `digests` and `alerts` for the user-facing output

---

## 21. Notes

- The backend is intentionally optimized for self-directed investors, not for broad market research.
- The code currently prefers resilience over strict completeness.
- Many stages have deterministic fallbacks so a partial AI outage does not break the whole user experience.

