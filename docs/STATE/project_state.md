---
project: Clavis
version: 1
last_updated: 2026-04-19
roadmap: docs/STATUS/roadmap.md
status: active
current_phase: "Phase 0 - V1 scope lock and final roadmap"
current_focus:
  - Lock the V1 product scope: Clavix branding, handoff UI as source of truth, brokerage sync in V1, and Pro purchase at $25/month
  - Define the missing News feed endpoint contract before implementation so the new Home/News/Article flow has a stable backend shape
  - Build the final execution plan for phases 0-4, including the exact dependency order for iOS UI, backend API, and release readiness work
  - Treat email summaries, advanced plan management, and institutional/data features as V2-only work
  - Keep the shared ticker analysis assumptions stable while the UI/API plan is finalized
blockers:
  gate_0:
    - Paid Apple Developer account
    - App Store Connect setup
    - RevenueCat setup
    - Business entity and banking
    - SnapTrade developer application and approval
    - SnapTrade sandbox + brokerage sync setup once launch timing justifies it
  technical:
    - News feed endpoint has no dedicated implementation yet and needs an explicit route/data contract before the handoff UI can be built
    - App shell/UI migration for the handoff has not started yet
    - Phase 3 and Phase 4 implementation order still needs to be broken into concrete file-level tasks
  recent_completions:
  - Created a branding guide documenting fonts, colors, spacing, tone, and UI presentation rules
  - Created a comprehensive UI wireframe brief covering Home, Holdings, Digest, Alerts, News, ticker detail, onboarding, and settings
  - Added the DigitalOcean VPS setup guide with droplet bootstrap steps, secret-copy steps, Cloudflare Tunnel systemd service, and verification commands
  - Documented the `develop` / `main` branch workflow and the production deploy path to the droplet in AGENTS.md
  - Confirmed the backfill artifact set contains descriptive, article-specific risk analyses rather than generic fallback summaries
  - Fixed structural refresh overwriting AI scores: refresh_ticker_snapshot now skips tickers with existing AI-scored same-day snapshot (methodology_version ILIKE '%ai%')
  - Implemented run_user_holdings_daily_ai_refresh() job at 2 AM UTC: queries all user-held tickers (excluding system SP500 user) and runs full AI pipeline via tickers_override passthrough to run_sp500_full_ai_analysis_fast
  - Moved the iOS Supabase anon key into an xcconfig-backed build setting, regenerated XcodeGen, and verified the simulator still launches with the real key
  - Updated the shared ticker snapshot refresh to consume recent news-derived events instead of hardcoding macro/event adjustments to zero
  - Updated the iOS ticker detail model and UI so backfill search results now show AI score rationale and AI dimensions instead of the structural-only snapshot card
  - Simplified the add-position ticker field so it no longer pops live search results while typing, and clarified the watchlist star action with accessibility labels
  - Reframed the shared ticker detail fallback as a structural snapshot with explicit copy that macro and event adjustments are neutral until a live analysis run exists
  - Fixed the stale evidence label bug so enriched company articles now refresh both top-level and nested relevance evidence quality, preventing bodyful articles from still being persisted as `title_only`
  - Parallelized the S&P backfill price-refresh stage and shortened Finnhub quote timeouts so 25-ticker batches stop spending their tail in a serial price loop
  - Simplified company-news discovery queries to use the company name directly instead of appending "stock", so the backfill can pull broader news coverage for each holding
  - Widened the shared ticker analysis gate so headline-summary company articles can now be forced into event analysis after enrichment, not just partial/full-body articles
  - Swapped company-news discovery to GNews, added decoded URL rewriting so wrapper links are replaced with publisher URLs, and validated AAPL/MSFT/TSLA live results in the backend container
  - Moved company article enrichment out of the shared payload and into a cache-backed post-relevance step so only needed company articles get scraped, and added a reusable event-hash cache for enriched articles across backfill runs
  - Disabled forced LLM scoring for S&P backfill positions and raised backfill batch concurrency to 4 so the remaining runtime is driven more by actual work than by neutral fallback retries or serialized batch waits
  - Removed Polygon from the backfill refresh path so price updates now use Finnhub-only snapshots, and collapsed company article enrichment into the shared payload so batches reuse cached enriched articles instead of re-scraping them
  - Reduced the backfill-only shared ingest load by capping the shared company RSS feed at 4 articles per ticker, trimming sector/macroeconomic fetch volume, and adding timing logs for shared payload build, article enrichment, and cache reuse so the next canary can pinpoint the remaining bottleneck
  - Split the backfill news path into a shared raw ingest plus batch-specific analysis consumption: the controller now fetches one shared news payload for all selected tickers, batch analyses reuse that cache, and the 8-ticker canary still completed successfully in 8.7 minutes with 8/8 synced and 0 failures
  - Implemented the next backfill throughput pass: article enrichment now runs with higher concurrency, scheduled S&P batch analyses create independent run IDs, and company-news enrichment overlaps with relevance classification before the enriched bodies are merged back for downstream analysis; an 8-ticker canary completed successfully in 8.8 minutes with 8/8 synced and no failures
  - Inspected the stalled detached S&P backfill through batch artifacts and live DB state, confirmed the worker had progressed through event analysis/report/scoring, then safely terminated the live worker and marked the active master plus batch runs failed after investigation
  - Patched the detached S&P backfill hang path by adding default MiniMax chat timeouts, skipping digest generation for internal scheduled S&P batch runs, and excluding the long-lived `sp500_backfill` controller row from stale-run cleanup so the controller is no longer marked failed mid-run
  - Ran a grounding QC pass across one sampled stock from every other batch in the interrupted run; later completed batches were usually tied to real event titles, but several summaries still overreached with macro spillover claims and synthetic zero-share backfill rows sometimes produced false "no position / wait-and-see / entry catalyst" language
  - Fixed the S&P backfill launcher so the detached worker now starts from the backend root instead of a hard-coded `/app` cwd, and added a focused launcher regression test
  - Added a local `python -m app.scripts.sp500_backfill` launcher/status workflow so the backend container can start an S&P backfill in a detached process, return a run ID without JWT, and report progress from `analysis_runs`
  - Added a persistent server-side S&P backfill trigger/status flow backed by `analysis_runs`, so admin requests can enqueue a backfill, get a run ID immediately, and poll progress even after the calling terminal closes
  - Hardened the batched S&P backfill against transient Supabase/PostgREST disconnects by retrying timeout-finalization and status-poll queries, and by consuming background task exceptions so failures no longer surface only as "Task exception was never retrieved"
  - Chose UptimeRobot as the free-tier uptime monitor and documented the exact `/health` check settings in the repo
  - Fixed the Google RSS throttling lock so it is scoped per event loop, preventing batched backfill runs from failing with "bound to a different event loop" errors
  - Added an uptime-monitoring runbook for the backend `/health` endpoint so the app can be watched on a free tier without extra infrastructure
  - Added backend Sentry scaffolding and a GitHub Actions CI workflow for compile/test coverage
  - Chunked the S&P shared-cache AI backfill into sequential batches of 10 tickers so large runs avoid the 25-minute scheduler timeout and can continue even if one batch fails
  - Added a dedicated `/account` backend surface for user data export and account deletion, including Supabase auth-user removal and cleanup across user-owned tables
  - Added structured JSON-style backend event logging for auth failures, request failures, startup status, and successful request completions
  - Redacted repo-tracked secret values from `AGENTS.md`, `backend/.env`, `docs/STATUS/PROJECT_STATUS.md`, and the iOS Supabase config so only placeholder/local-secret references remain in tracked files
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
