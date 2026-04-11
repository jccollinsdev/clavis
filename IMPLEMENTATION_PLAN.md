# Morning Digest Rework Plan

## Goal
Rebuild the morning digest pipeline so it refreshes all holdings in parallel, pulls overnight macro news from CNBC RSS, pulls sector news from CNBC sector RSS feeds, classifies holdings into sectors automatically, and then sends one combined payload to the LLM to generate the final digest.

## Current State
- Holdings are analyzed inside one sequential analysis run.
- News ingestion currently uses Finnhub company news plus generic RSS feeds.
- Macro summarization already exists, but it is fed from the current article pool, not dedicated CNBC macro RSS.
- Sector awareness exists indirectly through ticker metadata and macro sensitivity helpers, but there is no dedicated sector-news pipeline.

## Target Flow
1. Refresh all user positions in parallel.
2. In parallel, fetch overnight macro news from CNBC RSS and generate a macro overview.
3. In parallel, classify each holding’s sector and fetch the matching CNBC sector RSS feeds.
4. Analyze all article sets with the existing relevance/significance/event-analysis pipeline.
5. Build one combined digest prompt with:
   - macro overview
   - sector overview
   - individual holding analysis
   - portfolio impact
   - what matters today
   - what to do

## Planned Changes

### 1. Parallel portfolio refresh
- Split the current per-position refresh loop into concurrent tasks.
- Keep the existing analysis steps per position, but run them with bounded concurrency.
- Ensure progress and partial results still persist while the run is active.

### 2. CNBC macro RSS ingestion
- Add a dedicated CNBC macro RSS source:
  - `https://www.cnbc.com/id/100003114/device/rss/rss.html`
- Normalize these articles into the same article shape used by the rest of the pipeline.
- Feed them into a dedicated macro summarizer that produces a short overnight macro brief.

### 3. CNBC sector RSS ingestion
- Add a sector feed map for:
  - Technology
  - Financials
  - Energy
  - Healthcare
  - RealEstate
  - ConsumerRetail
  - IndustrialsAutos
  - Media
- Use the sector associated with each holding to select the right feed(s).
- Fetch these feeds in parallel with the macro and holding refresh work.

### 4. Sector classification for holdings
- Make sector a first-class attribute on holdings or ticker metadata.
- On add/refresh, infer sector from company metadata and persist it.
- Use this persisted sector to route sector RSS lookups.

### 5. Reuse article-analysis pipeline
- Keep the current relevance, significance, and event-analysis stages.
- Replace only the article source layer for holdings where needed.
- Preserve caching and fallback behavior.

### 6. Digest compilation update
- Update digest compilation so the LLM receives one structured payload containing:
  - macro overview
  - sector summaries
  - per-position summaries and event analyses
  - portfolio risk
  - forward-looking items
- Change the digest order to lead with macro, then sector, then positions, then portfolio impact, then action items.

## Risks / Notes
- Google News RSS and CNBC RSS are noisier than Finnhub and will need dedupe/filtering.
- Sector mapping needs a clear source of truth to avoid inconsistent feed selection.
- Parallel refresh needs concurrency limits so the run does not overload external services.
- Digest output format may need a prompt/JSON shape update to keep sections stable.

## Open Questions
- Should CNBC fully replace Finnhub company news, or should it be a fallback/source blend?
- Should sector live on `positions`, `ticker_metadata`, or both?
- Should sector summaries be one per sector or one combined sector section in the digest?

## Next Step
Implement the new ingestion and orchestration flow, then update digest compilation to consume the combined context.
