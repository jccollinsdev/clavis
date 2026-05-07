# Clavix Backend — Full System Audit & Recovery Plan
**Audit Date:** 2026-04-30 ~00:55 UTC
**VPS:** 134.122.114.241
**Scope:** Evidence-only investigation from live VPS logs, Supabase REST queries, deployed code.
**Note on naming:** The project is "Clavix"; the working directory and deployed container are named `clavis`. Treated as the same system throughout.

---

## Table of Contents
1. [Live System State](#1-live-system-state)
2. [Full System Flow — 24h Lifecycle](#2-full-system-flow--24h-lifecycle)
3. [Rationale Pipeline Breakdown](#3-rationale-pipeline-breakdown)
4. [Database Truth Audit](#4-database-truth-audit)
5. [Failure Chains](#5-failure-chains)
6. [Root Causes (Top 5)](#6-root-causes-top-5)
7. [System Design Flaws](#7-system-design-flaws)
8. [Fix Plan](#8-fix-plan)
9. [Canonical Rationale Design](#9-canonical-rationale-design)
10. [Validation Rules](#10-validation-rules)
11. [Test Plan](#11-test-plan)
12. [Final Diagnosis](#12-final-diagnosis)

---

## 1. Live System State

### 1.1 Containers / Processes

| Name | Status | Image |
|---|---|---|
| `clavis-backend-1` | Up 38 minutes | `clavis-backend` |

- Only one container running.
- `cloudflared` and `clavis-mirofish-1` are documented in `vps-access-and-operations.md` but **NOT running** — Mirofish is intentionally removed. Docs are stale.
- Container restarted at 00:11 UTC 2026-04-30. This is why `docker logs --since 24h` only shows 247 lines (recent restart cleared older logs).

### 1.2 Resource Usage

```
CPU:  0.20%
MEM:  113.5 MiB / 1.92 GiB (5.77%)
Host: 1.9 Gi total | 715 Mi free | 856 Mi buff/cache | 593 Mi used | 0 swap
Disk: /dev/vda1 — 48G total, 4.2G used (9%)
```

**Status: Healthy.** No memory or disk pressure.

### 1.3 Registered Scheduler Jobs

All times in ET. Source: `scheduler.py:5044–5047` and `_sync_user_job` at `814–840`.

| Job ID | Trigger (ET) | Function | Source |
|---|---|---|---|
| `system_sp500_backfill` | 07:30 daily | `_run_scheduled_sp500_backfill` | `scheduler.py:4995` |
| SP500 daily refresh | 08:00 daily | `refresh_sp500_cache` | `scheduler.py:5005–5011` |
| Holdings daily AI refresh | 07:00 daily | `run_user_holdings_daily_ai_refresh` | `scheduler.py:4958–4964` |
| News cleanup | 08:30 daily | `_cleanup_old_news_items` | `scheduler.py:5026–5031` |
| Per-user structural | 06:30 daily | `trigger_structural_refresh` | `scheduler.py:814` |
| Per-user digest | user `digest_time` (e.g. 07:05 ET) | `trigger_scheduled_digest` | `scheduler.py:833–840` |

### 1.4 Last 24h Log Errors

Only two distinct error sources in the 247-line live tail (`docker logs --since 24h`):

**Error A — AMD background snapshot refresh, every `/tickers/AMD` hit:**
```
04/30/2026 12:37:44 AM - HTTP Request: POST .../ticker_news_cache?... "HTTP/2 409 Conflict"
04/30/2026 12:37:44 AM - Background snapshot refresh failed for AMD
Traceback:
  File "/app/app/routes/tickers.py", line 77, in _safe_refresh_snapshot
  File "/app/app/services/ticker_cache_service.py", line 1960, in refresh_ticker_snapshot
  File "/app/app/services/ticker_cache_service.py", line 425, in sync_ticker_news_cache
postgrest.exceptions.APIError: {'code': '23505', 'details':
  'Key (ticker, url)=(AMD, https://www.cnbc.com/2026/04/28/fed-meeting-preview-april-2026.html)
   already exists.', 'message':
  'duplicate key value violates unique constraint "idx_ticker_news_cache_ticker_url"'}
```
Repeated at 12:16:05 and 12:37:44 — fires on every iOS open of `/tickers/AMD`.

**Error B — Daily user digest NameError (confirmed in DB `scheduler_jobs.last_error`):**
```json
{"user_id":"90b7281c...","last_run_status":"failed",
 "last_error":"name 'upsert_ticker_metadata' is not defined",
 "last_run_at":"2026-04-29T11:05:00Z","next_run_at":"2026-04-30T11:05:00Z"}

{"user_id":"7ff5a6c5...","last_run_status":"failed",
 "last_error":"name 'upsert_ticker_metadata' is not defined",
 "last_run_at":"2026-04-29T11:00:02Z"}
```

No 429s, no rate-limit warnings, no retries observed in last 24h.

### 1.5 Active Analysis Runs

- Latest 10 `analysis_runs`: all `status=completed`, `triggered_by=scheduled`, `user_id=00000000-0000-0000-0000-000000000001` (system user), all on 2026-04-29 17:56–18:45 UTC.
- Earlier that day:

| Run ID | User | Status | Started | Error |
|---|---|---|---|---|
| `0fa24fe9-a23a-46ec-97a4-d81bf48667bf` | `90b7281c…` (real user) | `failed` | 2026-04-29 07:05:02 UTC | `Error code: 401 - {'type': 'authorized_error', 'message': 'invalid api key (2049)'}` (MiniMax) |

- Both real users have `last_run_status=failed` in `scheduler_jobs` (see Section 6).

---

## 2. Full System Flow — 24h Lifecycle

All times ET. Scheduler is `timezone=ET`.

| Stage | Trigger | Entry Point | Reads | Writes | Failure Mode (live) |
|---|---|---|---|---|---|
| **A. Per-user structural refresh** | 06:30 daily | `trigger_structural_refresh` (3778) | `positions`, `ticker_metadata` | `risk_scores` (structural-only), `ticker_metadata` | Currently passes — `upsert_ticker_metadata` is imported lazily *inside* this function at line 3780. |
| **B. Holdings AI refresh** | 07:00 daily | `run_user_holdings_daily_ai_refresh` (4922) → `run_sp500_full_ai_analysis_fast` | `positions`, `news_items`, `ticker_metadata` | `ticker_risk_snapshots` directly | When MiniMax 401s → falls back to `methodology_version="sp500-backfill-deterministic-fallback-v1"` → writes generic reasoning. Does NOT write `ticker_refresh_jobs` rows. |
| **C. Per-user digest** | User `digest_time` (07:05 ET for both real users) | `trigger_scheduled_digest` (3527) → `enqueue_analysis_run` → `_run_analysis_in_thread` → `execute_analysis_run` (1677) | `positions`, `news_items`, `ticker_metadata`, `ticker_risk_snapshots` | `analysis_runs`, `position_analyses` (draft→ready), `risk_scores`, `event_analyses`, `digests`, `alerts`, news cache | **Crashes** on `NameError: name 'upsert_ticker_metadata' is not defined` at `scheduler.py:1794`. Symbol not imported at module level (only at 3780 inside a different function). Confirmed in `scheduler_jobs.last_error` for both users. |
| **D. SP500 backfill** | 07:30 daily | `_run_scheduled_sp500_backfill` (4975) → `enqueue_sp500_backfill_run` → `_execute_sp500_backfill_run` → `run_sp500_full_ai_analysis_fast` | universe + per-ticker news | `analysis_runs`, `ticker_risk_snapshots` | Falls back to deterministic when AI fails. All 04-29 AMD/HOOD/NVDA/AMZN snapshots are from this path. |
| **E. SP500 daily refresh** | 08:00 daily | `refresh_sp500_cache` (5006) | per-ticker news, snapshots | `ticker_risk_snapshots` | Same code path as D. Does NOT write `ticker_refresh_jobs`. |
| **F. News cleanup** | 08:30 daily | `_cleanup_old_news_items` (5014) | — | DELETE `news_items` and `ticker_news_cache` rows >30 days old | Works, but does not address dup accumulation in `news_items`. |
| **G. Background snapshot refresh** | Every `/tickers/{T}` open if news >6h newer than snapshot | `_safe_refresh_snapshot` (tickers.py:75) → `refresh_ticker_snapshot` (1960) → `sync_ticker_news_cache` (386) | `news_items`, `ticker_news_cache` | `ticker_news_cache` (DELETE+INSERT), `ticker_refresh_jobs`, `ticker_risk_snapshots` | `23505 duplicate key value violates idx_ticker_news_cache_ticker_url` at line 425. Exception swallowed by `_safe_refresh_snapshot` (tickers.py:84). No `ticker_refresh_jobs` row created. Repeats every page open. |
| **H. iOS render** | User opens holding | `PositionDetailView` calls `fetchPositionDetail` → reads `position.ticker` → routes to `TickerDetailView` | `/tickers/{T}` | nothing | Renders `tickerRationale(for:)` (TickerDetailView.swift:186): picks `currentScore.reasoning` first, then `latestRiskSnapshot.reasoning`, then `latestRiskSnapshot.newsSummary`, then hardcoded fallback. |

**Net daily outcome today:** Stages A, D, E succeed. Stage C crashes → leaves `position_analyses status='draft'` + failed `analysis_runs`. Stage G fails silently every visit. The only fresh artifact for an AMD-holding user is a deterministic-fallback snapshot + stranded draft. No `ready` position-level analysis ever produced.

---

## 3. Rationale Pipeline Breakdown

### 3.1 Exact Selection Trace for AMD

```
1. snapshot = latest ticker_risk_snapshots[AMD]
              { reasoning: "...Coverage is thin...",
                news_summary: "AMD occupies a structurally attractive position as hyperscalers...",
                source_count: 0,
                methodology_version: "sp500-backfill-deterministic-fallback-v1" }

2. latest_position_score = risk_scores[91a3ac22]  ORDER BY calculated_at DESC LIMIT 1
              { reasoning: "AMD: Company-specific news (42) is broadly neutral...
                            This summary was assembled from the final dimension scores.",
                calculated_at: 2026-04-27 }   ← 3 days stale

3. latest_position_analysis = position_analyses[91a3ac22]
              WHERE status='ready' ORDER BY updated_at DESC LIMIT 1
              { summary: "Known facts are limited for AMD, so the current read leans
                          on existing position context and whatever confirmed signals are available.",
                source_count: 0, updated_at: 2026-04-27 07:07:52 }
              ← BEATS the substantive 04-26 rows because it is newer.
                No source_count / quality check exists in this selector.

4. current_analysis = (3)  ← passes through sanitize_public_analysis_text unchanged

5. current_score = build_risk_score_response(snapshot, ..., coverage_context=current_analysis)
   (ticker_cache_service.py:1031–1050):
     a. _clean(latest_position_score.reasoning)  → None  (legacy dimension math caught)
     b. _clean(snapshot.reasoning)               → None  ("coverage is thin" caught)
     c. _clean(coverage_context.summary)         → "Known facts are limited..." PASSES
        ← FILTER COVERAGE GAP:
          None of _PUBLIC_RATIONALE_BAD_MARKERS, _GENERIC_FALLBACK_MARKERS,
          _LEGACY_DIMENSION_MATH_MARKERS match:
          "known facts are limited" / "current read leans on existing position context"
     reasoning = "Known facts are limited..."

6. _canonical_public_rationale called at lines 1656 and 1802:
     score_reasoning = _clean(current_score.reasoning) → "Known facts are limited..." PASSES
     → returns early
     → NEVER reaches:
         - _build_article_aware_reasoning(latest_event_analyses)
         - snapshot.news_summary

7. JSON shipped to iOS:
     current_score.reasoning           = "Known facts are limited for AMD..."  ← BAD  (shown)
     latest_risk_snapshot.reasoning    = "...Coverage is thin..."              ← BAD
     latest_risk_snapshot.news_summary = "AMD occupies a structurally..."      ← GOOD (buried as footnote)
     current_analysis.summary          = "Known facts are limited..."          ← BAD
     current_analysis.methodology      = "Shared S&P ticker cache using..."

8. iOS tickerRationale() picks currentScore.reasoning FIRST → renders bad text.
   snapshot.news_summary is rendered only as a small footnote in a separate "Snapshot"
   card (TickerDetailView.swift:302).
```

### 3.2 Per-Ticker Rationale Resolution (Summary)

| Ticker | What resolves | Why |
|---|---|---|
| **AMD** | `"Known facts are limited for AMD..."` (bad) | Fallback ready row (04-27) is newest; passes filters; short-circuits article path |
| **HOOD** | `snapshot.reasoning` ("Elevated volatility is the primary risk for HOOD...") | No substantive `position_analyses` row; snapshot.reasoning passes filters |
| **NVDA** | `snapshot.news_summary` (good) | `snapshot.reasoning` starts with "Risk factors for NVDA" — caught by `_PUBLIC_RATIONALE_BAD_MARKERS`; falls through to `news_summary` |
| **AMZN** | `snapshot.news_summary` (good) | Same as NVDA — "Risk factors for AMZN" caught; falls through |

**AMD is the worst case** because its `position_analyses` contains a stale ready row with fallback text that passes every filter, blocking the good `news_summary`.

### 3.3 Live Snapshot Data (all tickers, 04-29)

| Ticker | `snapshot_date` | `type` | `grade` | `safety` | `source_count` | `methodology_version` |
|---|---|---|---|---|---|---|
| AMD | 2026-04-29 | backfill | C | 60 | 0 | `sp500-backfill-deterministic-fallback-v1` |
| HOOD | 2026-04-29 | backfill | C | 58 | 0 | `sp500-backfill-deterministic-fallback-v1` |
| NVDA | 2026-04-29 | backfill | C | 60 | 0 | `sp500-backfill-deterministic-fallback-v1` |
| AMZN | 2026-04-29 | backfill | C | 62 | 0 | `sp500-backfill-deterministic-fallback-v1` |

All four backed by the deterministic fallback. All `source_count=0`.

### 3.4 AMD `risk_scores` (latest)

```json
{
  "position_id": "91a3ac22...",
  "calculated_at": "2026-04-27T07:07:52Z",
  "grade": "F",
  "safety_score": 60,
  "total_score": 30.0,
  "reasoning": "AMD: Company-specific news (42) is broadly neutral; Macro/sector exposure (32) adds risk; Portfolio construction (8) adds risk; Near-term volatility (38) is broadly neutral. … This summary was assembled from the final dimension scores."
}
```

No `risk_scores` row newer than 2026-04-27 for AMD — 3 days stale.

### 3.5 AMD `position_analyses` (latest 10)

| `updated_at` | `status` | `source_count` | Summary excerpt |
|---|---|---|---|
| 2026-04-29 07:05:47 | **draft** | 3 | "Quick brief ready for AMD. Found 3 relevant headlines and started the deeper analysis." |
| 2026-04-28 07:05:35 | **draft** | 3 | (same) |
| 2026-04-27 07:07:52 | **ready** | 0 | "Known facts are limited for AMD, so the current read leans on existing position context…" |
| 2026-04-27 07:05:32 | **draft** | 3 | "Quick brief ready…" |
| 2026-04-26 07:09:44 | **ready** | 3 | "AMD's position faces near-term technical overextension risk after the recent bull run… geopolitical risk escalation and Fed policy uncertainty…" ← **RICH** |
| 2026-04-26 07:08:57 | **ready** | 3 | rich |
| 2026-04-25 07:10:16 | **ready** | 3 | rich |

### 3.6 `event_analyses` for AMD

Newest: 2026-04-26 07:07:48 ("AMD Stock Tests Resistance As Intel Beat…"). Nothing in the last 3 days. Older 04-26 events are still returned (query is `LIMIT 20 ORDER BY DESC`).

### 3.7 `ticker_refresh_jobs`

Most recent row: **2026-04-18** — 12 days stale. The job-row insert is at `ticker_cache_service.py:1989`, downstream of the failing `sync_ticker_news_cache` call at line 1960. Failures are never journalled.

---

## 4. Database Truth Audit

### 4.1 Per-Table Assessment

| Table | Should be truth for… | Currently used as | Conflict / Corruption |
|---|---|---|---|
| `ticker_risk_snapshots` | Shared per-ticker score + canonical thesis (`news_summary`) | Partial — `snapshot.reasoning` leaks templated text; `news_summary` is the cleanest field but reached last in resolver | One row per ticker per day; mostly clean structurally |
| `position_analyses` | Per-user article-grounded narrative for a holding | Both source-of-truth AND draft-progress journal — same column shapes for "finished brief" and "we just started" | Drafts mix with ready; `ready` rows with `source_count=0` exist alongside `ready` rows with real content |
| `risk_scores` | Per-user numeric score + dimension breakdown | Also leaks deterministic synthesizer text into `reasoning` (legacy dimension math) | `reasoning` is rarely usable for users; should not feed UI |
| `event_analyses` | Per-event article narrative (the raw article-aware ingredient) | Feeds `_build_article_aware_reasoning` — but only when score reasoning is empty/unsafe (it isn't, for AMD) | Clean data exists for AMD as recent as 04-26; sits unused because resolver short-circuits |
| `news_items` | Raw ingested headlines | Also feeds `sync_ticker_news_cache` and structural scorer | **No unique constraint on `(ticker, url)` or `(ticker, event_hash)`** (`supabase_schema.sql:73-87`). 1,451 AMD rows. Same URL appears 3+ times with different `id`, identical `event_hash`, slightly different `processed_at`. |
| `ticker_news_cache` | Last-N normalized news per ticker for display + scoring | Written by `sync_ticker_news_cache` via DELETE-then-INSERT | DELETE is bounded by `lt(processed_at, latest_in_batch)` — leaves orphaned rows that collide on `(ticker, url)` unique index with new batches |
| `analysis_runs` | Execution journal | Works as journal | Failed runs leave `position_analyses` drafts behind — no transactional cleanup |
| `ticker_refresh_jobs` | Journal of background refresh attempts | Empty since 2026-04-18 (12 days) | Jobs row inserted at line 1989, **after** the failing sync at line 1960 — failures are never journalled |

### 4.2 Position Analyses Status Counts (most recent 1,000 rows)

```
ready: 968
draft:  32
```

Drafts cluster on the most recent days for users whose digest run has been failing.

### 4.3 Pipeline-Language Strings in DB (confirmed live)

- `position_analyses` rows with `summary` starting with `"Quick brief ready for"` — at least 2 active (AMD/HOOD), updated 04-29 and 04-28, `status=draft`.
- `position_analyses` rows with `summary="Known facts are limited for AMD…"` — 1 `ready` row, 2026-04-27.
- `position_analyses` rows with `long_report` containing `"Clavynx already found the initial signal for this holding and is still generating the in-depth report."` — present in every draft row.
- `position_analyses` rows with `methodology="Initial draft based on the earliest matched headlines while the deeper event analysis is still running."` — present in every draft row.

### 4.4 API Response Fields and Safety Status

| Field | Safe for users? | Can be draft? | LLM or deterministic? | Contains internal text? |
|---|---|---|---|---|
| `risk_scores.reasoning` | No — legacy "Company-specific news (X) adds risk" math | Only written on completed analysis | Mixed: deterministic synthesizer when LLM rationale missing | Yes — "This summary was assembled from the final dimension scores" |
| `ticker_risk_snapshots.reasoning` | Mostly no — "Coverage is thin", "Risk factors for X are relatively balanced" | No | Deterministic when AI fallback | Yes — templated phrases |
| `ticker_risk_snapshots.news_summary` | Yes — observed AMD/NVDA texts are clean, article-grounded | No | LLM (MiniMax) when pipeline succeeds | No |
| `position_analyses.summary` | Sometimes — drafts contain "Quick brief ready", "started the deeper analysis"; ready-fallback rows contain "Known facts are limited" | Yes — draft is the default initial state | LLM | Yes — pipeline language in summary |
| `position_analyses.long_report` | Rarely — observed "Clavynx already found the initial signal for this holding and is still generating the in-depth report" | Yes | LLM/template | Yes — internal product name "Clavynx", pipeline stage language |
| `position_analyses.methodology` | No — describes internal scoring framework | Yes | Template | Yes — "Initial draft based on the earliest matched headlines while the deeper event analysis is still running." |
| `event_analyses.summary` | Yes when present (single event narrative) | N/A | LLM | Mostly clean |
| `event_analyses.scenario_summary` / `key_implications` | Yes | N/A | LLM | Mostly clean |

---

## 5. Failure Chains

### Chain A — Daily User Digest Broken (dominant chain)

```
07:05 ET cron fires
  → trigger_scheduled_digest
  → enqueue_analysis_run(skip_metadata_refresh=False)
  → _run_analysis_in_thread → execute_analysis_run
  → write position_analyses(status='draft', summary='Quick brief ready...')
    [partial write committed before crash]
  → if not skip_metadata_refresh: upsert_ticker_metadata(...)
       NameError: 'upsert_ticker_metadata' is not defined  ← scheduler.py:1794
  → analysis_runs.status = 'failed'
  → scheduler_jobs.last_run_status = 'failed'
  → no risk_scores written
  → no position_analyses promoted to 'ready'
  → no event_analyses written
  → draft row persists forever with pipeline language
  → next day: new draft row written, same crash, same draft persists
```

**Consequence:** Both real users have had a dead daily pipeline since at least 2026-04-25.

### Chain B — Snapshot Refresh Wedged on AMD

```
iOS opens /tickers/AMD
  → backend computes freshness (news newer than snapshot by >6h)
  → background_tasks.add_task(_safe_refresh_snapshot, AMD)
  → refresh_ticker_snapshot(AMD)
  → sync_ticker_news_cache:
      DELETE WHERE ticker=AMD AND processed_at < latest_in_batch
        ← does NOT delete rows at processed_at >= latest_in_batch
      INSERT cache_rows
        ← collides on (ticker, url) with surviving rows
      raise APIError 23505
  → exception bubbles to _safe_refresh_snapshot
  → ticker_refresh_jobs row NEVER inserted (insert is downstream of failure)
  → ticker_risk_snapshots not refreshed
  → logger.warning("Background snapshot refresh failed for AMD", exc_info=True)
  → user opens AMD again 30s later → IDENTICAL failure
  → self-heal impossible
```

### Chain C — Bad Rationale Wins for AMD

```
iOS opens /tickers/AMD
  → get_ticker_detail_bundle(AMD)
  → _get_latest_position_analysis_for_ids returns 04-27 ready fallback
       (newest ready, source_count=0, "Known facts are limited...")
       ← BEATS 04-26 substantive row — no _has_substantive_analysis check
  → build_risk_score_response:
       legacy math caught → snapshot 'Coverage is thin' caught →
       coverage_context.summary "Known facts are limited..." PASSES FILTER
       ← FILTER COVERAGE GAP:
         _PUBLIC_RATIONALE_BAD_MARKERS / _GENERIC_FALLBACK_MARKERS
         contain no substring of:
           "known facts are limited"
           "current read leans on existing position context"
  → current_score.reasoning = "Known facts are limited..."
  → _canonical_public_rationale short-circuits on this passing text
  → article path NEVER reached
  → snapshot.news_summary NEVER reached
  → JSON ships, iOS picks currentScore.reasoning → user sees bad text
```

### Chain D — `news_items` Accumulation Amplifies Chain B

```
RSS ingest writes news_items (no unique constraint)
  → same URL reinserted on every ingest pass for the same news cycle
  → AMD has 1,451 rows; same fed-meeting URL exists with multiple IDs,
    same event_hash, slightly different processed_at
  → sync_ticker_news_cache pulls top 50, dedupes in memory (works),
    but produces a batch whose latest_processed_at may be OLDER than
    what's already in the cache
    (earlier ingest cycles already persisted those URLs at later processed_at)
  → Chain B fires every time
```

### Chain E — MiniMax 401 Mid-Pipeline

```
Analysis run calls MiniMax
  → 401 'invalid api key (2049)'  (observed 2026-04-29, run 0fa24fe9)
  → exception not specifically handled (MiniMaxAuthError in local uncommitted edits)
  → analysis_runs.status = 'failed'
  → ready position_analyses never written
  → drives Chain C: low-confidence fallback rows become the latest 'ready'
```

---

## 6. Root Causes (Top 5)

### #1 — Filter Coverage Gap

| Attribute | Detail |
|---|---|
| **Where** | `_PUBLIC_RATIONALE_BAD_MARKERS` / `_GENERIC_FALLBACK_MARKERS` in `ticker_cache_service.py:514–561` |
| **Why** | The deterministic fallback writer added new template phrasing; deny-lists weren't updated to match. No substring of `"known facts are limited"` or `"leans on existing position context"` appears in any marker list. |
| **Frequency** | Every render where the latest `ready` `position_analyses` is a low-coverage fallback |
| **User impact** | AMD shows generic text instead of the rich `news_summary`. The single most visible quality bug. |

### #2 — `upsert_ticker_metadata` NameError in `execute_analysis_run`

| Attribute | Detail |
|---|---|
| **Where** | `scheduler.py:1794` — symbol used unconditionally, but only imported inside `trigger_structural_refresh` at line 3780 |
| **Why** | Missing top-level import after refactor; `skip_metadata_refresh=False` is the default for scheduled digests |
| **Frequency** | Every day per user with `notifications_enabled=True` (both real users) since at least 2026-04-25 |
| **User impact** | **Silent total stoppage** of the daily user pipeline. No new `ready` analyses, no new risk scores, no digests. Drafts pile up daily. |

### #3 — Newest-Ready Selection Beats Substantive Selection

| Attribute | Detail |
|---|---|
| **Where** | `_get_latest_position_analysis_for_ids` at `ticker_cache_service.py:1214` |
| **Why** | No `_has_substantive_analysis` check — sorts by `updated_at DESC` only. The equivalent check exists in `routes/positions._select_current_analysis` (different route, dead from iOS) but not here. |
| **Frequency** | Whenever a low-coverage `ready` row is newer than a substantive `ready` row |
| **User impact** | Old rich analyses are masked indefinitely |

### #4 — `sync_ticker_news_cache` Non-Idempotent

| Attribute | Detail |
|---|---|
| **Where** | `ticker_cache_service.py:416–425` |
| **Why** | DELETE is bounded by `processed_at < latest_in_batch`; surviving rows with `processed_at >= latest` collide with INSERT on the `(ticker, url)` unique index |
| **Frequency** | Every background refresh (every page open beyond 6h staleness) for AMD |
| **User impact** | Snapshot refresh permanently wedged. `ticker_refresh_jobs` table empty for 12 days. "Last updated" stays stale. |

### #5 — `news_items` Lacks Uniqueness Constraint

| Attribute | Detail |
|---|---|
| **Where** | `supabase_schema.sql:73–87` |
| **Why** | Schema authored without a dedup constraint; no enforcement at write sites |
| **Frequency** | Continuous — 1,451 AMD rows; same URL with 3+ IDs, same `event_hash` |
| **User impact** | Slows queries, multiplies dedup work, creates input conditions for RC#4 to keep reproducing |

### Honourable Mentions (not in top 5)

- **MiniMax 401** (`analysis_runs.0fa24fe9.error_message`): appeared at least once on 04-29. Local uncommitted edits to `services/minimax.py` introduce `MiniMaxAuthError`, suggesting a known recurring issue not yet shipped.
- **`latest_risk_snapshot.reasoning`** ships legacy math text directly — no sanitizer applied.
- **`/tickers` vs `/positions` route divergence** — two different selection rules. iOS only uses the ticker route; `positions.py` logic is dead code from the iOS perspective.

---

## 7. System Design Flaws

1. **Three rationale fields exposed in the same JSON payload** (`current_score.reasoning`, `latest_risk_snapshot.reasoning`, `latest_risk_snapshot.news_summary`) with selection done partly client-side, partly via ad-hoc cleaner functions. No single canonical column.

2. **Deny-list cleaner, not allow-list validator.** Any new fallback phrasing introduced upstream is invisible until a user complains. Three overlapping constants (`_LEGACY_DIMENSION_MATH_MARKERS`, `_GENERIC_FALLBACK_MARKERS`, `_PUBLIC_RATIONALE_BAD_MARKERS`) with shared responsibilities and gaps.

3. **Backend AND iOS both make rationale-selection decisions.** Backend resolves to `current_score.reasoning`; iOS independently considers `latestRiskSnapshot.reasoning` and `latestRiskSnapshot.newsSummary` as fallbacks (TickerDetailView.swift:186–197). When the backend hands over a passing-but-bad string, iOS fallbacks never fire.

4. **Two routes, two selection rules for the same data.** `/tickers/{T}` uses newest-ready; `/positions/{id}` uses newest-substantive. They must agree.

5. **Drafts and ready rows live in the same table with the same column shapes.** Progress journal and publishable artifact are entangled. Discipline lives only in queries.

6. **No transactional boundary around analysis runs.** Failure mid-run leaves a draft `position_analyses` orphaned with no compensating cleanup.

7. **Failures are silent.** `_safe_refresh_snapshot` swallows exceptions. `ticker_refresh_jobs` doesn't journal early-stage failures. `analysis_runs.error_message` records traces but nothing consumes them.

8. **Pipeline language is written into user-facing columns and filtered downstream.** Producers write "Quick brief ready…", "Clavynx already found…", "Initial draft based on…" into user-facing columns; the cleaner downstream is asked to recognize and strip them. The producer should never write them in the first place.

---

## 8. Fix Plan

### P0 — Immediate: Stop Bad UX (Today)

1. **Patch the deny-list.** Append substrings to `_PUBLIC_RATIONALE_BAD_MARKERS` (or `_GENERIC_FALLBACK_MARKERS`):
   - `"known facts are limited"`
   - `"leans on existing position context"`

   Re-run the cleaner so AMD's `current_score.reasoning` resolves through to `news_summary`.

2. **Patch `_get_latest_position_analysis_for_ids`** to require `source_count > 0` OR `major_event_count + minor_event_count > 0` before accepting a `ready` row, falling back to newest-ready only if no substantive row exists. Mirror `_has_substantive_analysis` from `routes/positions.py`. One predicate, used in both routes.

3. **Stop emitting pipeline language into user-facing columns.** Change the draft writer in `_run_analysis_in_thread` to write `summary=NULL` (and `long_report=NULL`, `methodology=NULL`), or a single neutral string like `"Risk review in progress."` The progress message belongs in a `progress_message` field only. This removes exposure of: `"Quick brief ready…"`, `"Clavynx already found…"`, `"started the deeper analysis"`, `"Initial draft based on…"`.

### P1 — Stability (This Week)

4. **Fix the `NameError`.** Add `from ..services.ticker_metadata import upsert_ticker_metadata` to the top-level imports in `scheduler.py` (lines 1–18). Add a regression test that imports `execute_analysis_run` and runs it with `skip_metadata_refresh=False` against a mocked supabase, asserting no `NameError`.

5. **Handle MiniMax 401s properly.** Wire the existing-but-uncommitted `MiniMaxAuthError` work (`services/minimax.py`) so 401s are caught at the call site and surfaced as a typed exception. At boot, do a lightweight credential probe against MiniMax and refuse to start the digest cron if the key is invalid.

6. **Make `sync_ticker_news_cache` idempotent.** Replace the DELETE-then-INSERT pair with:
   ```python
   supabase.table("ticker_news_cache").upsert(cache_rows, on_conflict="ticker,url")
   ```
   Keep a separate time-bounded retention sweep (older than 30 days) but decouple it from the per-sync write.

7. **Insert `ticker_refresh_jobs` row before the news sync** so failures are journalled. Status flow: `queued → running → completed | failed` (with `error_message`). Currently, the insert is after the failing sync — making failures invisible.

### P2 — Data Layer

8. **Add `UNIQUE (ticker, COALESCE(event_hash, url))` constraint on `news_items`** and `ON CONFLICT DO NOTHING` (or `DO UPDATE SET processed_at=GREATEST`) at write sites. Migrate existing dupes (1,451 → unique).

9. **`UNIQUE (ticker, url)` on `ticker_news_cache`** already exists (`idx_ticker_news_cache_ticker_url`). Keep it. Combined with fix #6 (upsert), it becomes safe.

10. **Split `position_analyses` lifecycle.** Options:
    - Add a `lifecycle` column with values `draft | ready | superseded` and a partial index `WHERE lifecycle='ready'`, OR
    - Move drafts into a sibling table `position_analysis_drafts`.

    Selection queries can never accidentally pick a draft.

11. **Wrap analysis runs in a transactional cleanup pattern.** On `analysis_runs.failed`, compensate by deleting the draft `position_analyses` rows for that `analysis_run_id`. Eliminates strand artifacts.

### P3 — Architecture

12. **Define one canonical rationale field** (see Section 9). All other rationale-shaped fields stop being part of the iOS contract; remove from API responses or mark internal.

13. **Replace deny-list cleaner with allow-list validator** (see Section 10). Validator runs at **write time** in the analysis pipeline, not at read time on the API boundary. If a producer's text doesn't pass, the producer writes nothing — never a poor surrogate.

14. **Move all rationale selection into the backend resolver.** iOS reads exactly one field; no client-side fallback chain.

15. **Add admin observability:**
    - Per-day counts of `position_analyses` by status
    - `analysis_runs.failed` counts with top error text per day
    - Last successful `ticker_refresh_jobs` per ticker
    - A single `rationale_source` field on each ticker showing which path produced the live text

16. **Update `docs/GUIDES/vps-access-and-operations.md`** to remove `clavis-mirofish-1` and `cloudflared` (neither runs).

---

## 9. Canonical Rationale Design

**Goal: one field, written once, consumed once.**

### Field Definition

- **Field:** `ticker_risk_snapshots.public_rationale` (new column)
- **Producer:** The same resolver that `_canonical_public_rationale` already implements, executed at snapshot **write time** in `refresh_ticker_snapshot` and the SP500 backfill writer. Resolved once, stored. API never re-resolves on read.

### Fallback Hierarchy (resolver order, applied at write)

1. `news_summary` from a freshly-written, AI-grounded snapshot (when `methodology_version` does NOT contain `"deterministic-fallback"`).
2. Deterministic article-aware reasoning built from `event_analyses` rows for the position, only when at least one event has `risk_direction != 'neutral'` AND `confidence >= 0.6`.
3. `position_analyses.summary` only when that row passes the validator (Section 10) AND `source_count > 0`.
4. **Safe sentence fallback:** `"Risk review in progress."` — API marks `analysis_state='stale'` so UI shows a refreshing affordance.

No further rules. No deny-list re-entry on read. The field is either a thesis-driven sentence or the safe sentence. No third state.

### API Contract

- `current_score.reasoning` → **removed**
- `latest_risk_snapshot.reasoning` → **removed from public payload** (kept in DB for debugging)
- `latest_risk_snapshot.news_summary` → **removed from public payload** (kept in DB for debugging)
- iOS reads `latest_risk_snapshot.public_rationale` only
- `tickerRationale(for:)` becomes: `detail.latestRiskSnapshot?.publicRationale ?? "Risk review in progress."`

### Rule for Content

One investor-facing sentence (or two short ones). No headers, no bullet markers, no internal product names (`"Clavynx"`), no pipeline language (`"draft"`, `"running"`), no scoring math.

---

## 10. Validation Rules — `is_publishable_rationale(text)`

A rationale string is publishable **iff all of these hold** (evaluated at **write time**, not read time):

| Rule | Constraint |
|---|---|
| **Length** | Between 80 and 600 characters |
| **Sentence count** | Between 1 and 3 sentences (split on `". "` and `"; "`) |
| **References a driver** | Contains ≥ 2 distinct entries from the driver lexicon (see below) |
| **No pipeline vocabulary** | Lower-cased text does not contain: `"draft"`, `"queued"`, `"pipeline"`, `"running"`, `"clavynx"`, `"quick brief"`, `"started the deeper"`, `"found "`, `"relevant headline"`, `"methodology"`, `"synthesized"`, `"fallback"`, `"the model"`, `"this summary was assembled"`, `"company-specific news ("`, `"deterministic"` |
| **No generic-fallback shapes** | Lower-cased text does not contain: `"coverage is thin"`, `"limited recent coverage"`, `"thesis defaults to"`, `"thesis rests on structural"`, `"risk factors for "`, `"known facts are limited"`, `"leans on existing position context"`, `"broadly contained unless new developments"`, `"relatively balanced — no single force"` |
| **Mentions ticker or company name** | At least once — anchors against generic templates |
| **Not a verbatim duplicate** | Not a match to any string in a baked "fallback templates" set committed to source control |
| **Contains an effect verb** | Matches regex: `\b(adds|reduces|drives|supports|threatens|compresses|expands|signals|raises|lowers|opens|closes|shifts|caps|widens|narrows|locks|undermines|reinforces|sharpens|weakens|strengthens)\b` |

**Driver lexicon (conservative, reviewed monthly):**
> `earnings`, `guidance`, `demand`, `margin`, `supply`, `tariff`, `rate`, `Fed`, `valuation`, `competition`, `share`, `policy`, `buyback`, `regulatory`, `approval`, `sanction`, `macro`, `spending`, `capex`, `subscriber`, `customer`, `contract`, `product`, `launch`, `AI`, `infrastructure`, `litigation`

**Producer contract:** Every writer of a rationale-shaped column calls the validator before persisting. If text fails, writer stores the safe sentence instead. The read-time cleaner is deleted — it has no work to do.

---

## 11. Test Plan

| # | Test | Assertion |
|---|---|---|
| 1 | **No draft text exposed** | Unit test: `_clean_public_rationale_text` returns `None` for each of: "Quick brief ready for AMD…", "Clavynx already found the initial signal…", "Initial draft based on the earliest matched headlines…", "Known facts are limited for AMD, so the current read leans on…", "Company-specific news (X) adds risk…" |
| 2 | **No pipeline language in API responses** | Integration test: assert `GET /tickers/{T}` and `GET /positions/{id}` JSON payloads contain none of: `"Quick brief"`, `"started the deeper analysis"`, `"Clavynx"`, `"found N relevant headlines"`, `"Initial draft"`, `"Known facts are limited"`, `"Risk factors for "`, `"Company-specific news ("` |
| 3 | **Canonical rationale selection** | Given a fixture with (a) a stale fallback `ready` row, (b) a substantive older `ready` row, (c) a `draft` row — selector must return (b). |
| 4 | **Failed runs don't corrupt UI** | Fixture: `analysis_runs.failed` + a `draft` `position_analyses` for that run. Assert `_get_latest_position_analysis_for_ids` does NOT return the draft and does NOT raise. |
| 5 | **Article evidence produces article-based rationale** | When `event_analyses` for the position contain ≥1 row with `risk_direction!=null` and `key_implications`, rationale runs through `_build_article_aware_reasoning` and includes at least one of those event titles or implications. |
| 6 | **Sync idempotency** | Re-running `sync_ticker_news_cache` with the same `news_rows` twice does NOT raise `23505`. |
| 7 | **`upsert_ticker_metadata` callable from `execute_analysis_run`** | Test imports `execute_analysis_run` and runs `_run_analysis_in_thread` with mocked supabase, asserting no `NameError`. |
| 8 | **Snapshot freshness signal** | When AMD snapshot is older than 6h relative to `last_news_refresh_at`, the route schedules a refresh AND the refresh succeeds (no dup-key) on a clean DB state. |

---

## 12. Final Diagnosis

The current system produces bad rationale because the daily user pipeline is **silently failing on a missing import** (`upsert_ticker_metadata` is not in scope inside `execute_analysis_run` at `scheduler.py:1794`), so each user's holdings get a `position_analyses` row stranded at `status='draft'` while the only `status='ready'` row is a 3-day-old deterministic fallback containing the literal phrase _"Known facts are limited for AMD, so the current read leans on existing position context"_; the rationale resolver picks **newest-ready (not best-ready)** and the cleaner's deny-list does not include the substrings of that fallback, so it passes the filter as if it were investor-grade text and **short-circuits the canonical resolver** before it ever consults the rich `news_summary` (which contains the actual article-grounded thesis: _"AMD occupies a structurally attractive position as hyperscalers accelerate AI infrastructure buildout…"_); meanwhile the background snapshot refresher is **wedged on every `/tickers/AMD` open** by a non-idempotent `sync_ticker_news_cache` colliding with the `(ticker, url)` unique index, so the stale snapshot cannot self-heal — the system has good data but is selecting the wrong field, validating it with the wrong test, and unable to refresh because of a separate dup-key bug, and these three failures compound rather than mask each other.

---

*Document compiled from live VPS logs, Supabase REST queries, and deployed code audit at commit `90e8ccb`. No code changes implemented — diagnosis and design only.*
