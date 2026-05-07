# Clavix data pipeline audit & build plan

Date: 2026-05-03
Scope: ticker detail end-to-end (news → analysis → API → iOS) for AMD, HOOD, GOOG, SMCI.
Status: audit only. No code or DB changes proposed for execution yet.

---

## 0. TL;DR

- The risk‑dimension `or 0` truthiness bug was real and is fixed in `1bf7e70`. **But the user‑visible HOOD zeros are a different bug**: `risk_scores` for HOOD literally stores `0` for `macro_exposure`, `volatility_trend`, and `position_sizing` (the deterministic fallback wrote zeros, not nulls).
- Driver card titles for AMD/HOOD are raw RSS headlines because `_build_driver_cards()` falls back to `_truncate(group[0]["title"], 80)` whenever `_THEME_DRIVER_TITLES.get((theme, direction))` misses. Commit `1bf7e70` only patched the **summary** fallback; the **title** fallback is still wide open.
- GOOG looks "better" partly by accident: GOOG's latest `position_analyses` row has `driver_cards = null` / `driver_count = 0`, so the iOS view is rendering from a different source (probably `top_risks` / cached prior cards). It's not a working path; it's a quieter failure.
- Event detail "What happened / TL;DR / What it means" duplication is a **field‑mapping bug, not a content bug**. iOS maps `event.summary → What happened`, `event.longAnalysis → TL;DR`, `event.scenarioSummary → What it means`. None of these source fields are a one‑sentence TL;DR. The DB has `summary, scenario_summary, long_analysis` — there is no `tldr` and no `what_happened` column. The "TL;DR" label is therefore mounted on a paragraph (`long_analysis`) by design.
- `event_analyses` rows are inserted byte‑identically multiple times per analysis run (no dedupe key on `(position_id, source_url, content_hash)`). AMD had 5 latest rows that were 2 articles ×~2.5 inserts each.
- `ticker_news_cache.summary` still contains raw HTML/JS for some sources (Investing.com, blog.google, TradingView page chrome) — the `d301e50` sanitizer doesn't cover the contaminating ingest path, and pre‑sanitizer rows were never backfilled.
- `ticker_risk_snapshots` writes `factor_breakdown.ai_dimensions` only on `backfill` snapshots. The newer `sp500-shared-cache-v1` daily writer omits the block entirely. So today's "latest snapshot" for HOOD/AMD/GOOG/SMCI has no ai_dimensions at all.
- "Full Analysis" string is **not present anywhere in the current iOS source**. Either the user is on a stale build, or it's a section header inside the LLM‑generated `long_report` markdown bleeding through.

---

## 1. Current architecture map

```
backend/app/
├── pipeline/
│   ├── rss_ingest.py            # RSS pull + initial article rows
│   ├── finnhub_news.py          # alt news ingest
│   ├── news_normalizer.py       # text sanitization (NO LLM)
│   ├── classifier.py            # event classifier (writes classification.why_it_matters)
│   ├── major_event_analyzer.py  # LLM event analysis (event_analyses rows)
│   ├── relevance.py             # filters which articles become events
│   ├── risk_scorer.py           # risk_scores + ai_dimensions writer
│   ├── structural_scorer.py     # leverage/liquidity/volatility/profitability
│   ├── macro_classifier.py      # macro_adjustment (currently 0)
│   ├── macro_regime.py
│   ├── position_classifier.py
│   ├── position_report_builder.py # build_position_report() + _build_driver_cards()
│   ├── portfolio_compiler.py
│   ├── compiler.py
│   ├── scheduler.py             # writes ticker_risk_snapshots daily
│   └── notifier.py
├── routes/
│   └── tickers.py               # GET /tickers/{ticker} (entry point)
└── services/
    ├── ticker_cache_service.py  # get_ticker_detail_bundle() + build_risk_score_response()
    ├── news_feed_service.py
    └── ticker_metadata.py

ios/Clavis/
├── Models/
│   ├── DriverCard.swift         # title/summary required, default ""
│   ├── PositionAnalysis.swift   # EventAnalysis: title, summary?, longAnalysis?, scenarioSummary?
│   ├── RiskScore.swift          # nil-safe, no nil→0 anywhere
│   └── DecodingHelpers.swift
├── Services/APIService.swift    # single fetchTickerDetail(ticker, positionId?)
└── Views/Tickers/
    ├── TickerDetailView.swift   # exec summary sheet + event detail sheet + risk dims
    └── TickerDriverCardsSection.swift
```

DB tables that matter for ticker detail:

- `ticker_news_cache` — raw normalized news; columns include `headline, summary, source, published_at`.
- `event_analyses` — `title, summary, scenario_summary, long_analysis, key_implications, recommended_followups, classification, impact_horizon, risk_direction, confidence, analysis_source, significance`. **No** `tldr`, `what_happened`, `what_it_means`.
- `ticker_risk_snapshots` — structural scores in columns; `ai_dimensions` lives inside `factor_breakdown` jsonb (only on backfill rows).
- `risk_scores` — per‑position score with explicit `macro_exposure`, `volatility_trend`, `news_sentiment`, `position_sizing`, `thesis_integrity` columns.
- `position_analyses` — `summary, long_report, methodology, top_risks, top_news, watch_items, driver_cards (jsonb), driver_cards_state, driver_cards_source, driver_count, status`.
- `positions`, `watchlist_items`.

---

## 2. Data flow

```
RSS / Finnhub / Polygon
   │
   ▼
rss_ingest.py / finnhub_news.py
   │   raw article {headline, summary?, body?}
   ▼
news_normalizer.normalize_news_item()
   │   text-sanitize only (no LLM); summary falls back to title if empty
   ▼
ticker_news_cache  (rows; duplicates not blocked; HTML/JS leaks for some sources)
   │
   ├─► relevance.filter() ─► classifier ─► event_analyses (+ classification jsonb)
   │                                          ▲
   │                                major_event_analyzer.analyze_major_event()
   │                                LLM returns: analysis_text, scenario_summary,
   │                                  key_implications, followup_notes, impact_horizon,
   │                                  risk_direction, confidence
   │                                (NO tldr / what_happened / what_it_means returned)
   │
   ├─► structural_scorer ─► ticker_risk_snapshots (daily, NO ai_dimensions)
   │   risk_scorer        ─► ticker_risk_snapshots (backfill, WITH ai_dimensions)
   │                     ─► risk_scores (per-position; deterministic fallback can write 0)
   │
   └─► position_report_builder.build_position_report()
           │  LLM returns: summary, long_report, methodology, top_risks,
           │              watch_items, risk_context
           ▼
       _build_driver_cards()
           │  picks group[0]; titles via _THEME_DRIVER_TITLES lookup;
           │  on miss → _truncate(group[0]["title"], 80) ← RAW HEADLINE
           ▼
       position_analyses row (status=draft → ready when promoted)

GET /tickers/{ticker}?position_id=…
   │  routes/tickers.py:87
   ▼
ticker_cache_service.get_ticker_detail_bundle()
   │  pulls latest position_analyses (held: by position_id; watchlist: synthetic)
   │  pulls risk_scores or ticker_risk_snapshots → build_risk_score_response()
   │  pulls event_analyses (held: by position_id; watchlist: built from ticker_news_cache)
   ▼
JSON {current_score, current_analysis, latest_event_analyses, profile, watchlist_status}
   │
   ▼
iOS APIService.fetchTickerDetail() → TickerDetailResponse
   │
   ├─ TickerDriverCardsSection: card.title / card.summary (faithful render)
   ├─ Risk dimensions chart: RiskScore.macroExposure etc. (nil → "—")
   └─ Event detail sheet (TickerDetailView.swift:1271-1279):
        "What happened" ← event.summary           ◄── raw article body / RSS snippet
        "TL;DR"         ← event.longAnalysis      ◄── 3-6 sentence paragraph
        "What it means" ← event.scenarioSummary   ◄── one-line implication
```

---

## 3. Ticker-by-ticker comparison

### AMD

| Layer | Observed |
|---|---|
| `ticker_news_cache` | TradingView/Seeking Alpha rows have page chrome in `summary`; duplicate rows for same `(headline, published_at)`. |
| `event_analyses` | 5 latest = 2 articles, repeated 2-3× each, byte-identical. `classification.why_it_matters = "Classification parse failed."` on every row. |
| `risk_scores` | `macro_exposure=38, volatility_trend=40, news_sentiment=50, position_sizing=95` (95 is deterministic-fallback artifact for 0% position weight). |
| `position_analyses` (ready) | `driver_count=1`, title is raw `"Semiconductor stocks rise on Big Tech earnings, Qualcomm beat - Yahoo Finance"`. Summary text is good. |
| Pending draft | Created ~3h ago, never promoted. |
| iOS render | Driver card title = raw headline. Event detail fields populated from `summary/longAnalysis/scenarioSummary`. |

### HOOD

| Layer | Observed |
|---|---|
| `ticker_news_cache` | Investing.com row contains raw JavaScript (`{const a=e.bidRequestsCount...`) as `summary`. One row has empty summary. Duplicate rows. |
| `event_analyses` | 2 of 5 latest are byte-identical. Investing.com row's own `recommended_followups` self-flags: "Body content was unreadable (malformed JavaScript)". |
| `risk_scores` | **`macro_exposure=0, volatility_trend=0, position_sizing=0`** (literal zeros in DB). Grade F, total 32.2. |
| `ticker_risk_snapshots` | Latest is `daily` (sp500-shared-cache-v1) — **no `ai_dimensions` block**. Yesterday's backfill row had `{macro_exposure:62, news_sentiment:44, position_sizing:66, volatility_trend:37}`. |
| `position_analyses` (ready) | 2 driver cards: `"Earnings call transcript: Robinhood Q1 2026 misses forecasts, stock dips - Inve…"` (truncated) and `"Robinhood Shares Tumble After Trading Results Disappoint - WSJ"`. Both are raw headlines. |
| Pending draft | Created ~3h ago, never promoted. |
| iOS render | Risk dimensions show 0 (faithful render of DB 0). Driver card titles = raw headlines. Some events render only title + scenarioSummary because `summary`/`longAnalysis` are empty. |

### GOOG

| Layer | Observed |
|---|---|
| `ticker_news_cache` | `blog.google` row has page navigation chrome in `summary`. |
| `event_analyses` | 2 of 5 are the `blog.google` "no content" article at confidence 0.23; analysis text self-acknowledges it found only nav chrome. |
| `risk_scores` | `macro_exposure=28, volatility_trend=38, news_sentiment=65, position_sizing=50`. Deterministic fallback values. |
| `position_analyses` (ready) | **`driver_cards=null, driver_count=0`** despite `status=ready`. `summary` is one 70-word run-on sentence. |
| iOS render | "Earnings trajectory is uncertain" the user saw is **not** coming from `driver_cards` (there are none). It's likely `top_risks[0]` rendered as a synthesized card, or a stale cached payload. The "GOOG works" appearance is a misread — this path is just failing more quietly. |

### SMCI

| Layer | Observed |
|---|---|
| `ticker_news_cache` | GlobeNewswire shareholder-alert row: summary == headline. |
| `event_analyses` | 4 rows = 2 distinct events ×2. Lawsuit row's own `long_analysis` says: "actual content contains only PR Newswire boilerplate rather than substantive article text". |
| `risk_scores` | `macro_exposure=32, volatility_trend=30, news_sentiment=28, position_sizing=85`. |
| `position_analyses` (ready) | Same as GOOG: `driver_cards=null, driver_count=0`, despite status=ready. 22h old. |
| Pending draft | ~30 min old. |

### Summary

| | Driver cards present | Driver titles clean | Risk dims populated | Event fields complete |
|---|---|---|---|---|
| AMD | yes (1) | **no** (raw headline) | yes (deterministic) | partial |
| HOOD | yes (2) | **no** (raw, truncated) | **no** (literal 0s) | partial |
| GOOG | **no** (null) | n/a | yes (deterministic) | partial |
| SMCI | **no** (null) | n/a | yes (deterministic) | partial |

GOOG isn't "the working one" — it's the one whose worst defects are hidden behind a different fallback.

---

## 4. Root causes, grouped

### A. Stale / corrupt DB rows
1. `ticker_news_cache.summary` contains raw HTML/JS for Investing.com, blog.google, TradingView, Seeking Alpha rows ingested before `d301e50`, AND a fresh HOOD row from 2026-05-01 still has JS — meaning at least one ingest path bypasses the centralized sanitizer.
2. `event_analyses` is duplicated per analysis run with no `(position_id, source_url, content_hash)` uniqueness constraint.
3. `position_analyses` `draft` rows pending 3+ hours; the promotion gate from `draft → ready` is stuck for AMD, GOOG, HOOD, SMCI right now.
4. `position_analyses.driver_cards = null` on GOOG and SMCI even though `status=ready` — the readiness gate isn't checking the cards generator.
5. `risk_scores` for HOOD has hard zeros (not nulls) — written by the deterministic fallback path.

### B. Backend prompt / generation
1. `MAJOR_EVENT_SYSTEM_PROMPT` (`major_event_analyzer.py:8-24`) returns `analysis_text + scenario_summary + key_implications + followup_notes`. It does not return a one-sentence TL;DR or a factual "what happened" recap. Whatever iOS labels "TL;DR" was never generated as such.
2. `_build_driver_cards()` (`position_report_builder.py:487-624`) title fallback at line 527: `_truncate(group[0]["title"], 80)` whenever `_THEME_DRIVER_TITLES.get((theme, direction))` misses. Commit `1bf7e70` patched only the summary fallback (lines 553-559).
3. `news_normalizer.normalize_news_item()` does no LLM rewriting — `summary` either survives as the source's RSS snippet or falls back to `title`.
4. Macro/event adjusters (`macro_adjustment`, `event_adjustment`) emit `0.0` on every snapshot for every ticker — dead pipeline stage.
5. Classifier silently produces `"Classification parse failed."` for AMD events; rows are persisted anyway with confidence 0.3.

### C. Response builder
1. `get_ticker_detail_bundle()` for watchlist tickers calls `_build_event_analyses_from_news_rows()` which synthesizes events from `ticker_news_cache` (so they inherit any junk in `summary`).
2. `build_risk_score_response()` truthiness bug fix in `1bf7e70` is correct but applies to the `or` operator only; the literal-0 in DB still propagates to the user (it isn't a bug for HOOD because the DB is genuinely 0, but the UI has no way to distinguish "0 because deterministic fallback" from "0 because real").
3. `ticker_risk_snapshots` daily methodology (`sp500-shared-cache-v1`) does not write `factor_breakdown.ai_dimensions`. The response builder reads "latest snapshot" and so misses ai_dimensions on most days.
4. No suppression of stale `position_analyses` ready rows when newer drafts have been pending too long.

### D. iOS mapping / defaulting
1. **Event detail field mapping is wrong** (`TickerDetailView.swift:1271-1279`):
   - "What happened" ← `event.summary` (raw RSS body)
   - "TL;DR" ← `event.longAnalysis` (3-6 sentence paragraph)
   - "What it means" ← `event.scenarioSummary` (one-liner)
   The user expectation (what_happened = factual recap, tldr = ≤18-word takeaway, what_it_means = implication) does not match these source fields. The label "TL;DR" on a `long_analysis` paragraph is the duplication symptom.
2. `DriverCard.title` and `DriverCard.summary` default to `""` if missing. Not a bug per se, but it masks "is there really a card here?" decisions.
3. No nil→0 defaulting in `RiskScore.swift` — HOOD zeros are real.
4. "Full Analysis" — string does not exist in the current iOS source. Likely either: (a) older app build still on the simulator, (b) an `# Full Analysis` markdown header inside the LLM-generated `long_report` rendering through the executive summary sheet.

---

## 5. Proposed correct data contracts

These are **target** shapes, not yet present in code/DB.

### `DriverCard`
```jsonc
{
  "id": "uuid",
  "theme": "earnings_risk | valuation | macro | competitive | regulatory | ...",
  "direction": "positive | negative | neutral",
  "strength": "strong | limited | weak",
  "title": "≤80 char synthesized title (NEVER a raw RSS headline)",
  "summary": "2-3 sentence rationale, ≥30 chars, distinct from title",
  "supporting_evidence": [
    { "title": "string", "summary": "string", "url": "string", "published_at": "iso" }
  ],
  "generated_by": "llm | template",
  "generated_at": "iso"
}
```
Invariant: `title != supporting_evidence[*].title` and `title` does not match `^[A-Z0-9 .,'’]+ - [A-Z][A-Za-z .]+$` (the dash-source-suffix pattern of RSS headlines).

### `EventAnalysis` (DB + API + iOS, aligned)
Add three first-class columns to `event_analyses`:
```jsonc
{
  "id": "uuid",
  "ticker": "AMD",
  "title": "≤120 char neutral event title",
  "what_happened": "2-3 sentence factual recap, no opinion",
  "tldr": "ONE sentence, ≤18 words, present-tense, no markdown",
  "what_it_means": "1-2 sentence implication for the stock/risk rating",
  "long_analysis": "current scenario_summary + analysis_text (kept for power-users)",
  "key_implications": ["..."],
  "impact_horizon": "immediate | near_term | long_term",
  "risk_direction": "improving | neutral | worsening",
  "confidence": 0.0,
  "source_url": "string",
  "content_hash": "sha1",
  "generated_at": "iso"
}
```
Unique key: `(position_id, source_url, content_hash)`.
LLM prompt must populate all of `what_happened`, `tldr`, `what_it_means` and validate length: tldr ≤ 18 words, what_happened ≥ 30 chars, distinct strings.

### `ExecutiveSummary`
```jsonc
{
  "tldr": "ONE sentence, ≤25 words",
  "bullish_tailwinds": ["≤3 bullets, ≤20 words each"],
  "bearish_headwinds": ["≤3 bullets, ≤20 words each"],
  "what_could_change_rating": ["≤3 bullets, ≤20 words each"]
}
```
No `full_analysis`, no `long_report`, no markdown headers. Stored as a structured jsonb column on `position_analyses` (e.g. `executive_summary`), not embedded in `summary`/`long_report`.

### `RiskDimensions`
```jsonc
{
  "macro_exposure":        { "value": 0-100 | null, "rationale": "string" },
  "volatility_trend":      { "value": 0-100 | null, "rationale": "string" },
  "news_sentiment":        { "value": 0-100 | null, "rationale": "string" },
  "position_sizing":       { "value": 0-100 | null, "rationale": "string" },
  "thesis_integrity":      { "value": 0-100 | null, "rationale": "string" },
  "_meta": {
    "source": "live | backfill | deterministic_fallback",
    "as_of": "iso"
  }
}
```
Distinguish `null` (we don't know) from `0` (we know it's zero). Today's pipeline collapses both into `0`. iOS already renders `null → "—"`; backend just needs to send null instead of synthetic 0 from the deterministic fallback.

---

## 6. Backfill / restocking plan

Order matters. Backup before each write step.

1. **Snapshot DB.** `pg_dump --schema-only` plus targeted `pg_dump --data-only -t ticker_news_cache -t event_analyses -t position_analyses -t risk_scores -t ticker_risk_snapshots` to `backups/2026-05-03/`.
2. **Sanitize `ticker_news_cache.summary` in place.** Run the centralized sanitizer over every row where `summary` matches an HTML/JS tell (`<`, `function`, `const `, `var `, `{const`). Re-null any summary that is byte-equal to `headline + " " + source`. Add a `sanitized_at` timestamp column.
3. **Dedupe `ticker_news_cache`.** Identify `(headline, published_at, source)` duplicates; keep the earliest, delete the rest. Add a partial unique index after.
4. **Dedupe `event_analyses`.** Backfill `content_hash`, then collapse to one row per `(position_id, source_url, content_hash)`. Drop rows where `classification.why_it_matters = "Classification parse failed."` AND no useful `long_analysis`.
5. **Re-null `risk_scores` zeros that came from deterministic fallback.** Identify rows whose `dimension_rationale` text matches the deterministic fallback signature ("Position sizing is manageable at 0% of portfolio…") and set those dimensions to NULL. HOOD's `risk_scores` row qualifies.
6. **Force re-run of `position_analyses` for AMD, HOOD, GOOG, SMCI.** Mark stuck `draft` rows as failed; trigger a fresh build. Validate driver_cards populates and titles pass the "no raw headline" invariant.
7. **Backfill `ticker_risk_snapshots.factor_breakdown.ai_dimensions`** for the latest daily row whenever it is missing — copy from the most recent backfill row OR re-run `risk_scorer.compute_ai_dimensions()` for that snapshot date.
8. **Smoke test** all four tickers via the live API with a known JWT and diff against the audit table in §3.

---

## 7. Phased implementation plan

Each phase is independently shippable and reversible. Do not skip ordering — phase N relies on the contracts from phase N-1.

### Phase 0 — Safety net (½ day)
- DB snapshot to `backups/2026-05-03/`.
- Add a feature flag `STRICT_DRIVER_TITLES` and `STRUCTURED_EVENT_FIELDS` (default off) to gate the schema/prompt changes.
- Add a small admin debug route that returns the raw `position_analyses` and `risk_scores` row alongside the rendered ticker detail JSON so we can diff cause vs effect quickly.

### Phase 1 — Driver-card title invariant (1 day)
- In `_build_driver_cards()`, replace the `_truncate(group[0]["title"], 80)` fallback with: (a) call LLM with a small "synthesize a 6-10 word driver title from these supporting items" prompt, OR (b) reject the card entirely if the theme/direction title can't be produced.
- Add a regex guard that rejects any candidate title matching the RSS-source-suffix pattern (`/ - [A-Z][A-Za-z .]+$/`).
- Add a unit test fixture per ticker (AMD, HOOD, GOOG, SMCI) using a frozen news bundle.
- Re-run `position_analyses` for the four test tickers.

### Phase 2 — Event analysis schema + prompt (2 days)
- Migration: add `what_happened text`, `tldr text`, `what_it_means text`, `content_hash text`, `source_url text` to `event_analyses`. Add unique index on `(position_id, source_url, content_hash)` (nullable-safe).
- Update `MAJOR_EVENT_SYSTEM_PROMPT` to require those three fields with explicit length constraints; validate tldr word count server-side and re-prompt if violated.
- `get_ticker_detail_bundle()` returns the new fields directly.
- iOS `EventAnalysis` model + `TickerDetailView.swift:1271-1279` re-mapped: "What happened" ← `event.what_happened`, "TL;DR" ← `event.tldr`, "What it means" ← `event.what_it_means`. Hide section if field is nil/empty (already does).
- Backfill: re-analyze last 30d of events with the new prompt, write to new columns. Old `summary`/`long_analysis` left intact.

### Phase 3 — Executive summary structured object (1 day)
- Migration: add `executive_summary jsonb` to `position_analyses`.
- Extend `build_position_report()` LLM call to return the four-field object (tldr ≤25 words, three bullet arrays).
- Response builder: surface `current_analysis.executive_summary`.
- iOS executive summary sheet: render strictly the four sections from `executive_summary`. If absent, fall back to today's `summary` field with a "(legacy)" note. Verify no markdown header `# Full Analysis` is rendered as a section title.

### Phase 4 — Risk dimensions provenance (1 day)
- `risk_scorer` and `scheduler.py` daily writer must always emit `ai_dimensions` (even if it's a re-use of yesterday's), AND must write NULL — not 0 — when a dimension is genuinely unknown.
- Add `_meta.source` to the dimensions response so iOS can dim a "deterministic fallback" indicator.
- Migration: backfill `ai_dimensions` on every `daily` snapshot for the last 7 days (copy from the closest preceding backfill row).
- Re-score HOOD with real inputs; verify `risk_scores` row has non-zero values where appropriate, and NULL elsewhere.

### Phase 5 — Sanitizer & dedupe hardening (1 day)
- Make `news_normalizer.sanitize_text_field` the only entry point — refactor the alternate ingest paths (Finnhub, Polygon, RSS direct) to flow through it.
- Add a startup self-test: feed known-bad fixtures (the Investing.com JS blob, the blog.google nav chrome) and assert sanitizer strips them.
- Add a unique partial index on `ticker_news_cache(headline, published_at, source)`.
- Add the same dedupe key on `event_analyses` (`position_id, source_url, content_hash`).
- Re-run the sanitizer over historical rows.

### Phase 6 — Promotion gate (½ day)
- `position_analyses` cannot reach `status=ready` while `driver_cards_state in ('pending', null)` and `driver_count=0`. Either generate cards inline before promoting, or downgrade to `partial` state and surface that to iOS.
- Alert on any draft row pending > 30 minutes.

---

## 8. Validation checklist

For each of AMD, HOOD, GOOG, SMCI, after each phase:

- [ ] `GET /tickers/{ticker}` returns `current_analysis.driver_cards` with ≥1 card whose `title` does not match the RSS-source-suffix regex and is not equal to any `supporting_evidence[*].title`.
- [ ] Each event in `latest_event_analyses` has all three of `what_happened`, `tldr`, `what_it_means` populated; `tldr` is ≤18 words; the three strings are pairwise distinct.
- [ ] `executive_summary` is a structured object with `tldr ≤25 words`, three bullet arrays, no `full_analysis` key.
- [ ] `current_score` reports either a non-zero value or `null` for each AI dimension; never `0` from the deterministic fallback unless `_meta.source = "deterministic_fallback"`.
- [ ] HOOD specifically: `current_score.macro_exposure` and `volatility_trend` are non-null real values OR explicitly `null` with a rationale.
- [ ] No row in `ticker_news_cache` for these four tickers has `<` or `function ` or `const ` in `summary`.
- [ ] No duplicate `event_analyses` rows for the same `(position_id, source_url, content_hash)`.
- [ ] iOS event detail sheet shows three distinct text blocks for events that have all three populated; collapses sections cleanly when fields are missing.
- [ ] iOS executive summary sheet shows exactly four sections; "Full Analysis" string does not appear in rendered output (search transcript / UI snapshot).
- [ ] iOS risk dimensions chart shows "—" for nil and a real number for non-nil; no `0` displayed for HOOD when DB has been re-scored.

Capture screenshots from the simulator for AMD, HOOD, GOOG, SMCI before/after each phase and attach to the relevant PR.

---

## 9. What NOT to change

- Do **not** add iOS-side hardcoded text constraints (truncating `event.longAnalysis` to fake a TL;DR). The TL;DR has to be generated, not synthesized client-side.
- Do **not** add per-ticker special-case code paths for AMD/HOOD/GOOG/SMCI. Every fix must apply uniformly.
- Do **not** change `RiskScore.swift` decoders to default nil → 0. iOS is correct; the backend is wrong.
- Do **not** drop the `long_analysis` / `scenario_summary` columns. Power users (and the methodology view) still need them. Add the new fields alongside.
- Do **not** widen the `or` → `is not None` fix from `1bf7e70` further; it's the right pattern, not the cause of HOOD's zeros.
- Do **not** clear or rewrite historical `position_analyses` rows directly. Re-run the generator and let the `draft → ready` flow overwrite naturally.
- Do **not** ship the new `event_analyses` schema migration without first running the sanitizer backfill — otherwise the new fields will get populated from contaminated `ticker_news_cache.summary` again.
- Do **not** trust simulator screenshots from before today as evidence; the "Full Analysis" section the user reported isn't in current source — confirm the simulator is on the latest build before chasing it.

---

## 10. Answers to the 10 audit questions

1. **Why does GOOG produce better Key Drivers than AMD/HOOD?** It doesn't. GOOG's `position_analyses.driver_cards = null`. What the user is seeing is a different fallback (likely synthesized from `top_risks`) that happens to read cleanly. AMD/HOOD have actual driver_cards rows whose titles fell through to the raw RSS headline branch.
2. **Why are AMD/HOOD driver cards still article headlines?** `_build_driver_cards()` line 527 fallback: `_truncate(group[0]["title"], 80)` when `_THEME_DRIVER_TITLES.get((theme, direction))` misses. Commit `1bf7e70` patched the summary fallback only.
3. **Are AMD/HOOD serving stale stored driver_cards?** No — the `ready` rows are from today. They're fresh, just generated wrong. (The pending `draft` rows are also stuck, but the UI is reading the prior `ready` row.)
4. **Are watchlist tickers using a weaker fallback path?** Yes. `get_ticker_detail_bundle()` for watchlist-only tickers calls `_build_event_analyses_from_news_rows()` which synthesizes events from `ticker_news_cache` rather than `event_analyses`, inheriting whatever junk is in `summary`.
5. **Why do event detail fields duplicate each other?** iOS maps `summary → "What happened"`, `longAnalysis → "TL;DR"`, `scenarioSummary → "What it means"`. None of these source fields are designed to be a TL;DR. When the LLM repeats itself across `analysis_text` and `scenario_summary`, all three labels show similar text. The DB schema literally has no `tldr` or `what_happened` column.
6. **Why is TL;DR not short?** Because the field iOS labels "TL;DR" is `long_analysis`, which the LLM is prompted to produce as 3-6 sentences.
7. **Why does HOOD show 0 macro exposure / volatility trend?** Because `risk_scores` for HOOD literally has `0` in those columns — written by the deterministic fallback when ai_dimensions weren't computed. Plus the latest `daily` snapshot for HOOD has no `ai_dimensions` block at all.
8. **Are zeros real values, nil defaults, stale snapshots, or serialization bugs?** All of the above for different tickers, but for HOOD specifically: real DB zeros from a deterministic fallback that should have written NULL.
9. **Which exact files/prompts generate each field?**
   - `driver_cards.title` — `backend/app/pipeline/position_report_builder.py:487-624`, `_THEME_DRIVER_TITLES` dict + line 527 fallback.
   - `driver_cards.summary` — same file, lines 553-559.
   - `event.what_happened` — does not exist; iOS reads `event.summary` (raw RSS body) from `event_analyses.summary`.
   - `event.tldr` — does not exist; iOS reads `event.longAnalysis` from `event_analyses.long_analysis`, populated by `MAJOR_EVENT_SYSTEM_PROMPT` in `backend/app/pipeline/major_event_analyzer.py:8-24`.
   - `event.what_it_means` — does not exist as labeled; iOS reads `event.scenarioSummary` from `event_analyses.scenario_summary`.
   - Executive summary sections — `backend/app/pipeline/position_report_builder.py:14` (`SYSTEM_PROMPT`); fields are `summary, long_report, methodology, top_risks, watch_items, risk_context`. No structured `executive_summary` exists.
10. **What schema/API changes are actually needed?** See §5 contracts and §7 phases. In short: new columns on `event_analyses` (what_happened/tldr/what_it_means/content_hash/source_url + unique index), new `executive_summary jsonb` on `position_analyses`, dedupe constraints on `ticker_news_cache` and `event_analyses`, NULL discipline on `risk_scores` and `ticker_risk_snapshots.ai_dimensions`, and a `_meta.source` field on the dimensions API response.
