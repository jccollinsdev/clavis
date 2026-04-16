---
project: Clavis
version: 1
last_updated: 2026-04-16
roadmap: docs/STATUS/roadmap.md
status: active
current_phase: "Phase 2 - Shared ticker intelligence and evidence-quality hardening"
current_focus:
  - Introduce evidence-quality modeling and sufficiency gates so wrapper-only articles no longer flow through relevance, event analysis, and report generation as if they were real article evidence
  - Make the search collector resilient to per-query failures so one bad DuckDuckGo request does not zero out company-article enrichment coverage
  - Fix the resolver fallback regression so Google wrapper articles no longer fail with unbound diagnostics variables during backfill runs
  - Make company-news resolver retries smarter and emit per-article failure reasons so wrapper-only runs are diagnosable instead of opaque
  - Add resolver telemetry and evidence gates for company-news article enrichment so the backfill run can distinguish true article coverage from wrapper-only failure states
  - Refactor the shared-cache backfill path into a ticker-intelligence pipeline for the position view: enrich article evidence with scraped content, reduce cache contamination, preserve valid macro output, and remove position-sizing logic from synthetic backfill snapshots
  - Resolve Google RSS wrapper pages into real publisher article bodies using source-domain hints, search-result discovery, and proxy text extraction so backfill analysis can cite substantive evidence instead of wrapper summaries
  - Fix the source_url resolver path so Google RSS company articles are resolved through the actual publisher URL instead of reconstructed slugs; source_url path is now probed first in resolution, with newspaper4k extraction and HTML fallback applied to the source_url directly before search candidates are tried
  - Decode Google News RSS article URLs into canonical publisher article URLs during company-news ingest so enrichment starts from the real article page rather than the publisher homepage stored in RSS source metadata
  - Ensure company-news article resolution happens before relevance classification so stale wrapper-era cache rows cannot bypass the improved evidence path
  - Tighten the remaining junk-article filters so broken MarketWatch recaps, generic price-move stories, and malformed proxy pages do not survive relevance/significance and dilute final backfill scores
  - Validate the repaired shared-cache S&P AI backfill path after fixing subset scoping, failed-run snapshot sync, misleading CLI dimension output, and restoring AI-led scoring preference for backfill runs
  - Validate the expanded ticker detail parity view, dynamic shared ticker onboarding, shared ticker cache freshness, digest synthesis, and alert fanout behavior in production-like runs
  - Validate the optimized shared-cache AI backfill path after reducing Finnhub, RSS, and MiniMax call volume across metadata refresh, relevance, event analysis, and scoring
  - Optional iOS refinement pass for richer ticker detail actions and more complete watchlist management UX
blockers:
  gate_0:
    - Paid Apple Developer account
    - App Store Connect setup
    - RevenueCat setup
    - Business entity and banking
    - SnapTrade developer application and approval
  technical:
    - Shared-cache scoring dispersion may still be narrower than the old fully AI-led flow because metadata inputs still default leverage/profitability to neutral placeholders and shared event projection is less ticker-specific than the legacy path
    - Batch AI scoring still needs live validation after reducing backfill scoring chunk size; empty MiniMax scoring responses should now fall back less often, but the new behavior needs rerun confirmation
    - The position-view backfill output still needs a fuller ticker-intelligence refactor: real article-body extraction is now wired for selected company articles and bad relevance cache payloads are rejected, but the final UI shape still needs simplification around what happened / what to watch / risk dimensions / relevant news
    - End-to-end ABBV backfill now completes with real event analyses and non-fallback risk dimensions, but one more cleanup pass is still needed to reject low-value recap / broken-page articles that currently survive as minor events
recent_completions:
  - Added env-configurable Google News RSS throttling in `backend/app/pipeline/rss_ingest.py` so one-off backfill runs can serialize Google feed requests with a fixed inter-request delay (for example `GOOGLE_NEWS_RSS_DELAY_SECONDS=60`) without slowing normal runs unless explicitly enabled
  - Began the structural evidence-quality fix: normalization now strips HTML and tags articles as title_only/headline_summary/partial_body/full_body, company-news force-promotion is now gated on usable evidence, event-analysis prompts now include body/evidence depth, and empty-event reports now state low evidence rather than claiming no material catalysts
  - Fixed two evidence-quality bugs in the backfill pipeline: (1) `company_articles_enriched` was inside `if artifact_enabled:` so SP500 backfill runs always passed empty enrichment to normalization — moved enrichment, coverage gate, and market_articles outside the artifact gate; (2) `normalize_news_item` used `raw_body = article.get("body") or raw_summary` which discarded enriched body key when body was absent from RSS items — fixed to distinguish absent key from empty string, giving `full_body: 3, headline_summary: 2, title_only: 35` vs prior `title_only: 40`
  - Integrated newspaper4k as primary extractor in `_probe_source_url_path`: source_url from RSS items is now tried directly with newspaper4k before any search candidate probing; includes HTML fallback and recursive newspaper4k retry if HTML body is weak
  - Fixed `_direct_publisher_candidates` to preserve and probe the actual source_url path from RSS items (not just reconstruct slug paths), adding exact source_url and parent directory as candidates alongside slug-based probing
  - Integrated Google News URL decoding into `fetch_google_company_rss`: company-news ingest now decodes `news.google.com/rss/articles/...` links into canonical publisher article URLs before enrichment, preserves the original publisher homepage as `publisher_homepage_url`, and a live ABBV spot check now resolves Yahoo Finance, MarketWatch, Seeking Alpha, and TIKR article URLs instead of homepage/tool pages
  - Fixed relevance wrapper detection so normalized articles with Google top-level URLs but enriched `raw.resolved_url`/`raw.source_url` are no longer auto-rejected as wrapper pages when they contain `full_body` evidence
  - Removed stale `evidence_quality` writes from `event_analyses` inserts so the repaired backfill path matches the live Supabase schema and no longer crashes during event persistence
  - Confirmed the repaired backfill pipeline works end-to-end on live ABBV runs: Google RSS URLs decode to canonical publisher pages, enrichment coverage reached 7/10, three company-news events persisted to `event_analyses`, final reports used substantive article-driven summaries instead of low-evidence fallback text, and risk dimensions/grade were generated successfully from the analyzed event set
  - Fixed the wrapper fallback regression introduced by the resolver diagnostics pass: `proxy_failure_reason` is now initialized before the wrapper branch so unresolved company-news items return structured fallback metadata instead of crashing
  - Began the smarter resolver pass: article enrichment now records structured failure reasons, candidate-level attempt diagnostics, and resolution status fields so unresolved company-news items can be debugged per article
  - Began the article-resolution hardening pass: company-news enrichment now records per-run resolution coverage telemetry, and the search resolver now tries broader headline/domain/ticker query variants before giving up
  - Started the ticker-intelligence backfill refactor: selected company-news articles are now scraped before downstream analysis, bad relevance cache payloads with failed LLM explanations are no longer reused, Google sector RSS queries are now added alongside CNBC sector feeds, macro persistence now prefers normalized raw model output, backfill scoring now omits live position sizing in favor of thesis-risk semantics, and system backfill digest assembly no longer overwrites fresh current-run payloads with stale snapshot history
  - Hardened ticker-intelligence evidence gating: low-information quote/chart, recap, holdings-history, and Google wrapper articles are now excluded from final per-ticker selection and from reused relevance cache payloads
  - Added a publisher-resolution path for Google RSS company articles: source_url is now preserved through normalization, search queries are derived from the headline and source domain, and resolved article pages are fetched through the `r.jina.ai` text proxy so article bodies are much richer than raw wrapper HTML
  - Moved company article enrichment ahead of relevance classification and version-gated legacy relevance cache rows so new body-based evidence cannot be bypassed by older wrapper-era cached decisions
  - Persistent backfill artifact capture added under `BACKFILL/<analysis_run_id>/`: each instrumented S&P backfill run now saves raw feed inputs, normalized articles, stage outputs, per-position analysis payloads, risk payloads, and every MiniMax prompt/response pair for end-to-end debugging
  - Root cause of the latest long-running backfill failure identified and fixed: cross-process orphan cleanup inside `enqueue_analysis_run()` was incorrectly marking live CLI backfill runs as "server restarted" failures; orphan cleanup now only runs during scheduler startup, and backfill AI scoring now uses smaller chunks to avoid empty batch-score responses
  - Shared-cache S&P backfill runner repaired: batch AI runs now scope to the requested ticker subset, failed runs no longer sync stale snapshots, CLI output now reads the current run's numeric AI dimensions from `risk_scores`, and backfill scoring now prefers the richer AI path with deterministic fallback only when model output is missing or suspiciously neutral
  - Shared-cache AI backfill pipeline optimized for API efficiency: ticker metadata now reuses fresh snapshots and avoids duplicate Finnhub metric calls, Google company RSS only falls back to symbol search when name search is thin, relevance/significance now chunk prompts, shared event analyses are cached once per article instead of once per ticker, and final risk dimensions default to deterministic scoring from cached evidence with LLM fallback only for sparse cases
  - Shared ticker cache expanded beyond seeded S&P names: Pro-added tickers can now be onboarded into `ticker_universe`, background-refreshed into the shared cache, and shown in search/detail for all users; ticker detail now returns position-style analysis, events, and alerts payloads
  - Ticker detail screen expanded to mirror position detail more closely: shared price chart, risk summary, factor breakdown, and richer news cards now render for searched tickers
  - Supabase migration applied, S&P universe seeded, and all 503 S&P tickers backfilled into `ticker_risk_snapshots`; digest fallback now synthesizes from shared cache and alerts compare snapshot deltas instead of position-scoped scores
  - iOS shared-cache integration completed for first pass: ticker search sheet, ticker detail screen, watchlist section navigation, cached add-position flow, and position-detail refresh now uses shared ticker refresh; simulator build and launch verified successfully
  - Backend scheduler now includes S&P 500 seed/backfill/status endpoints and a daily 3:00 shared cache refresh job; iOS holdings flow now loads cached ticker snapshots on add, exposes watchlist data, and uses ticker search in the add-position sheet
  - Backend S&P 500 shared ticker cache foundation added: migration scaffold, static S&P universe seed, ticker search/detail/refresh routes, watchlist routes, and holdings/dashboard/position detail reads now prefer canonical ticker snapshots
  - Notification permission onboarding step made status-aware; simulator/device decisions now surface a message instead of failing silently
  - iOS simulator build verified after notification flow update: BUILD SUCCEEDED
  - JWT verification hardened in backend middleware (Supabase auth.get_user)
  - Backend container restart issue diagnosed and resolved (double restart cleared .pyc cache)
  - Advisory/action copy rewritten across backend AI pipeline (portfolio_compiler, position_report_builder, agentic_scan, macro_classifier, risk_scorer, mirofish_analyze)
  - "What To Do" → "Monitoring Notes", "Action Signal" → "Risk Read" across iOS UI
  - /preferences/alerts PATCH endpoint added
  - All 10 preference fields persisted to Supabase (summary_length, weekday_only, alerts_grade_changes, alerts_major_events, alerts_portfolio_risk, quiet_hours_enabled, quiet_hours_start, quiet_hours_end)
  - iOS APIService/SettingsViewModel updated for all 10 preference fields
  - Score disclaimers added to DigestView, DashboardView, PositionDetailView, SettingsView
  - Freshness timestamps added to all score-displaying views
  - HoldingsViewModel and DigestViewModel CancellationError handling verified
  - Supabase RLS audit completed: prices table fixed (was SELECT-all-ops, now SELECT-only), all other policies verified correct — user data scoped via auth.uid() or EXISTS JOIN through positions table
  - Environment audit completed: no secrets in Swift files, all secrets in backend .env
  - Empty digest handling verified: already correctly handled (returns nil digest → shows idle state)
  - iOS build fixed: DigestView generatedAt conditional binding corrected
  - Phase 2 onboarding flow built: 4-screen flow (Welcome, Name/DOB, Risk Ack, Notification Permission)
  - Backend POST /preferences/acknowledge endpoint for onboarding completion
  - OnboardingViewModel with page state management and notification permission handling
  - ContentView updated with auth gate: authenticated → onboarding check → MainTabView vs OnboardingContainerView
  - hasCompletedOnboarding added to PreferencesResponse and GET /preferences response
  - AuthViewModel updated with hasCompletedOnboarding, checkOnboardingStatus(), markOnboardingComplete()
working_rules:
  - Load this file before coding
  - Load the roadmap before planning
  - Prefer the smallest correct change
  - Keep Clavis framed as a portfolio risk data platform, not an adviser
  - Update this file when the active phase or blockers change
next_review:
  trigger: "At the start and end of every meaningful work session"
---

# Project State

Clavis is currently focused on shared ticker intelligence hardening and evidence-quality improvements, while security and launch-surface work remain active pre-launch blockers.

The roadmap is the source of truth for sequencing. This file is the quick session memory that should be read first.

## Suggested Session Start

1. Read `AGENTS.md`.
2. Read `docs/STATE/project_state.md`.
3. Read `docs/STATUS/roadmap.md`.
4. Work from `current_phase` and `current_focus`.

## Suggested Session End

1. Update `recent_completions`.
2. Update `current_focus` and `blockers`.
3. Bump `last_updated`.
