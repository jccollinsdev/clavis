---
project: Clavis
version: 1
last_updated: 2026-04-25
roadmap: docs/STATUS/roadmap.md
status: active
current_phase: "Phase 5 - Digest Parity and Architecture Cleanup"
current_focus:
  - Verify and preserve the preference lifecycle so digest timing, summary length, weekday-only behavior, and notification toggles stay aligned across iOS, API, scheduler state, and digest generation
  - Keep `ticker_news_cache` fresh on snapshot refresh skips and surface `analysis_state`, `news_refresh_status`, and `last_news_refresh_at` consistently
  - Keep quiet-hours notification timing enforced in the scheduler without changing digest generation or scoring behavior
blockers:
  gate_0:
    - Paid Apple Developer account
    - App Store Connect setup
    - RevenueCat setup
    - Business entity and banking
    - SnapTrade developer application and approval
    - SnapTrade sandbox + brokerage sync setup once launch timing justifies it
  technical:
    - APNs is still not configured on the VPS because the production `apns.p8` key is not present yet
    - SnapTrade is wired locally and the simulator now works against `http://127.0.0.1:8000`, but the VPS backend still needs the SnapTrade client ID / consumer key configured before the production brokerage flow can work
    - App shell/UI migration is functionally complete, but final spacing polish and screenshot-level parity checks are still needed before release polish is considered done
recent_completions:
  - Added backend enforcement for quiet-hours notification timing in the scheduler, so digest/analysis APNs pushes now honor the stored quiet-hours window while leaving digest content and scoring untouched, and covered the overnight-window helper with regression tests
  - Audited the digest and notification preference lifecycle end to end, fixed the scheduler resync so `notifications_enabled` now re-registers digest jobs correctly, removed the cross-user `summary_length` fallback in force-refresh digest generation, and added regression tests for rescheduling, weekend skipping, user-scoped summary length, and digest token budgeting
  - Hardened the new digest and ticker-cache read paths so summary-length lookup falls back cleanly, sector-context synthesis tolerates sparse placeholder inputs, and ticker detail no longer throws when a default watchlist has to be synthesized on a read-only fake backend
  - Re-ran the touched backend slice after those fixes and confirmed all 27 relevant tests pass in the local `uv` environment with dummy Supabase/MiniMax settings
  - Added score-selection fallbacks on iOS so Home now prefers any valid digest score, logs a sanitized score payload in DEBUG, and shows "Pending" plus an explicit reason instead of a silent dash when no score is available
  - Reworked the backend risk-score synthesis and digest compiler so low-coverage reads stay factual, confidence is separated from the main rationale, and the digest now emits a useful low-urgency "no immediate portfolio-level risk driver" item when nothing urgent exists
  - Added backend tests covering thin-coverage rationale output, urgent-item behavior, and digest/dashboard score provenance, then verified the backend suite passes in the container and the iOS simulator build still succeeds
  - Unified manual digest force-refresh with the scheduled digest compiler inputs so portfolio risk, macro context, sector context, summary length, and analysis-run linkage now flow through the same backend path
  - Verified the updated digest payload still builds cleanly in the iPhone 17 Simulator after the score/provenance contract changes
  - Moved portfolio grade generation fully into the backend dashboard response, removed the last iOS `scoreToGrade` fallback, and taught the dashboard hero/change feed to show an honest unknown state when the backend does not provide a portfolio score
  - Tightened the display-score contract so ticker detail now prefers `position.total_score` and `position.risk_grade` ahead of shared snapshot fallbacks, and dashboard portfolio grade now derives from backend numeric scores instead of local grade averaging when the digest is absent
  - Fixed the ticker-detail bundle freshness contract by defining the missing `last_news_refresh_at` value before it is serialized, so the new analysis-state payload and freshness fields return cleanly instead of crashing on read
  - Added a shared-news cache writer and freshness tracking so analysis runs and shared refresh can populate `ticker_news_cache`, ticker detail/holdings can surface `news_as_of`, `last_news_refresh_at`, and refresh status, and old cache rows are cleaned up with retention
  - Completed the backend-owned add-holding workflow so `POST /holdings` now ensures ticker support, refreshes shared ticker data, enqueues the user analysis run, and returns a workflow/status object, then aligned ticker-detail state labels with holdings so both surfaces speak the same queued/running/ready/failed/thin vocabulary
  - Exposed explicit provenance and job-state fields through ticker detail and scheduler status responses, including analysis_state, latest_analysis_run, latest_refresh_job, coverage_state, and freshness timestamps, then wired the iOS ticker detail and dashboard to consume the new state cleanly
  - Connected the add-position flow to trigger backend analysis runs, surfaced top-3 supported ticker suggestions and unsupported ticker messaging in the search/add flows, routed alerts through the existing tab/deep-link structure, and hid position-sizing metrics on search-only ticker detail views
  - Applied the missing production Supabase migrations for `analysis_runs.target_tickers`, `user_preferences.last_manual_refresh_at`, `user_preferences.last_analysis_request_at`, `alerts.change_reason`, and `alerts.change_details`, and confirmed the live schema now matches the local migration set for those fields
  - Reconfirmed the iOS app is configured to use `https://clavis.andoverdigital.com` as its backend and rebuilt/relaunched the app successfully in the iPhone 17 Simulator
  - Switched the iOS backend target in the shared Xcode config from the local dev URL to the production VPS hostname so the simulator and app builds now point at `https://clavis.andoverdigital.com` instead of `http://127.0.0.1:8000`
  - Verified the latest iOS UI polish pass against the working tree, caught two compile regressions introduced during the cleanup (duplicate `NetworkStatusMonitor` / `OfflineStatusBanner` definitions and a duplicate `ClavisCopy` type), consolidated the shared definitions, then rebuilt and relaunched the app successfully in the iPhone 17 Simulator
  - Reworked the iOS presentation layer around the provided Clavix HTML handoff: updated the shared dark tokens, restyled login/onboarding plus the Home, Holdings, Digest, Alerts, Settings, News, Article, and ticker-detail shells to match the new layout direction, preserved the existing data/view-model flows underneath, and rebuilt the app successfully for the iPhone 17 Simulator
  - Restored the typography to the actual pre-change git baseline instead of the earlier approximation: reverted `ClavisTypography` label/row/body/card/footnote/metric/grade sizes, restored the gauge caption size, and returned the tab-bar labels to the original 10pt sizing before relaunching the iOS Simulator
  - Restored the original text sizing baseline after the smaller-font experiment, including the shared header/body styles and the bottom tab-bar labels, and relaunched the iOS Simulator to apply it
  - Trimmed the main app typography further after the screenshot review: reduced top header wordmarks, lowered body/card/footnote sizes, and shrank the bottom tab-bar labels to stop the Home and Holdings screens from feeling oversized
  - Trimmed the oversized app top-bar branding so the nav/header text stays readable without looking bulged: reduced the shared brand wordmark size, lowered the top-bar title size, and removed some of the extra scaling
  - Fixed the stock-detail risk-dimension regression by letting `build_risk_score_response()` fall back to the latest held-position `risk_scores` row when the shared ticker snapshot is absent, which restores the card on tickers like HOOD that have user-level scoring before shared-cache coverage lands
  - Began the structural pass by adding digest and manual-analysis cooldowns, wiring account export/delete actions into Settings, and switching backend auth middleware to local JWT verification with auth API fallback
  - Completed the easy audit fix pass: renamed the backend API title to Clavix, reconciled score bands and methodology copy, removed fabricated previous-score and empty-portfolio defaults, added forgot-password and DOB picker flows, scheduled news cleanup, tightened the prices RLS policy, and exposed core service status in `/health`
  - Reworked the iOS top-of-screen branding to use the App Logo asset and a large cream CLAVIX wordmark across the main tabs, settings, login, and ticker detail
  - Removed the user-facing reload DB chrome from digest and replaced the risk-score internal metric tiles/risk-dimension card with a simpler rationale-only presentation
  - Synced the backend tree to the prod VPS, rebuilt the backend service, and verified `https://clavis.andoverdigital.com/health` returns `{"status":"ok"}`
  - Verified the digest/alert/ticker-search changes with targeted backend tests in the backend container and confirmed the new digest helpers and fallback logic pass
  - Rebuilt and relaunched the Clavis iOS app in the iPhone 17 Simulator after the digest/dashboard/alerts pass; BUILD SUCCEEDED
  - Throttled Minimax calls globally, reduced S&P backfill fan-out concurrency, and persisted batch ticker lists on `analysis_runs` so failed batches are easier to reconstruct and rate-limit failures are less likely
  - Reworked the iOS Home, Holdings, Digest, and Alerts surfaces to remove the non-essential News entry point, drop the Home settings shortcut, add visible Clavix branding, clarify refresh actions, and improve digest/alert timestamps and section behavior
  - Saved the onboarding upgrade plan into `docs/STATUS/BUILD_PLAN.md` so the next session can resume from the exact production polish sequence
  - Reconciled the local schema snapshot in `supabase_schema.sql` with the current production extensions for preferences, analysis runs, ticker cache, scheduler jobs, watchlists, and analysis cache so the repo documents the live database shape more accurately
  - Saved the current free-vs-Pro pricing plan locally in `docs/PRODUCT/pricing.md` and updated it to reflect the launch split, feature matrix, and cost assumptions
  - Gated production debug/test surfaces behind a new backend feature flag and removed the stale `8001` deploy healthcheck mismatch so prod deploy verification now matches the actual compose stack
  - Completed a full-stack launch audit across backend, iOS, Supabase, migrations, docs, and deploy config; confirmed the core app is feature-rich and usable, but identified the top launch blockers as missing subscriptions/entitlements, incomplete notification UX, missing in-app account management/recovery flows, legal/public trust gaps, repo-to-production schema drift, and production exposure from debug/test surfaces
  - Surfaced coverage quality in the ticker detail flow by carrying source/event counts and coverage state through the backend score response, synthesizing non-blank rationales for blank AI outputs, tightening confidence levels on provisional rows, and updating the iOS rationale card to show methodology plus an explicit coverage warning
  - Stopped the active S&P backfill run `12b54f23-f0e7-4eaa-937f-c53c3c20128c`, verified the worker process exited, and confirmed the run is now marked failed because the server restarted
  - Improved the risk-scoring prompts to explicitly use a 0=penny-stock / 100=treasury scale, added notional and portfolio-weight context, and relaxed the neutral fallback gate so only fully neutral outputs are rejected
  - Probed the live backend on a real held HOOD position and a synthetic BXP backfill row; both now return `llm_scoring_used: true` with non-neutral dimensions instead of collapsing to the deterministic fallback path
  - Audited the shared ticker backfill scoring path and confirmed the current `sp500_backfill` mode was forcing deterministic risk scoring despite AI-generated analysis reports; patched the scorer to allow LLM scoring for backfill runs, labeled deterministic fallbacks honestly in snapshot methodology metadata, removed the stale iOS-only thesis dimension, renamed the UI card to Risk dimensions, and hid position sizing on non-held ticker detail surfaces
  - Updated the held-position detail path to use the same AI dimension card as ticker detail, then rebuilt and relaunched the iOS app successfully in the Simulator
  - Swapped the ticker detail risk-dimension card to show the AI dimension set from `currentScore.factorBreakdown.aiDimensions` instead of the structural liquidity/volatility/leverage/profitability panel, keeping the same bar-card presentation
  - Fixed the VPS overnight scheduler regressions: the 2AM holdings AI refresh and 3AM S&P refresh now register coroutine jobs correctly, structural refresh no longer depends on notification settings, and daily structural profile writes now upsert per ticker/date instead of crashing on duplicate-key races
  - Added a one-time 2AM UTC S&P backfill scheduler job on backend startup, exposed its next-run status in the cache monitor payload, and kept the existing daily refresh jobs intact
  - Repointed the iOS Settings legal links to getclavix.com, added public methodology/refund-policy links, and removed the force-unwrapped external URL so invalid URLs fail safely instead of crashing
  - Fixed the iOS local-dev backend URL packaging bug by inlining the simulator backend URL in Info.plist, then reinstalling the app in Xcode Simulator so brokerage connect now targets the correct local backend instead of a broken `http:` host
  - Updated the iOS onboarding brokerage step so `I’ll add manually for now` stays available as an exit path while the brokerage portal flow uses the shared SnapTrade view model
  - Added the first SnapTrade integration slice end to end: additive Supabase fields, backend `/brokerage` routes plus SnapTrade service, iOS onboarding/settings/holdings brokerage UI, deep-link callback handling, and a successful simulator build/run after wiring the new flow
  - Added a root README plus repository-layout, backend-organization, dev/prod workflow, and backfill-artifacts references so the codebase has a clearer contributor map without changing app logic
  - Synced the new admin-password setup to the live VPS, rebuilt the backend there, and verified the public `/admin` page now serves the protected login UI instead of the old 404
  - Switched the admin browser console to password-based cookie auth so you can log in directly from the web UI without needing to understand Supabase admin roles
  - Hardened the backend auth surface by switching to fail-closed middleware, tightening CORS to explicit production origins, and keeping the admin browser UI and debug surfaces behind authenticated access
  - Added a protected browser admin surface with overview, user visibility, scheduler/cache status, and manual refresh controls for S&P backfill, structural refresh, metadata refresh, and digest triggering
  - Moved the backend onto the DigitalOcean VPS, installed Docker/Compose and cloudflared, verified the public `/health` endpoint, and then stopped the Mac-side backend and tunnel so the public hostname only serves the VPS
  - Verified the live protected API surface with a real Supabase bearer token, found and fixed the `/news` schema mismatch, and re-verified the core read endpoints after the VPS cutover
  - Rebuilt and relaunched the Clavis iOS app in the iPhone 17 Simulator again after the digest/cache and ticker-detail work, confirming the current UI build still succeeds end to end
  - Reworked digest loading to prefer a fresh cached dashboard/digest row before generating, passed real overnight CNBC macro context into digest compilation, silenced transient MiniMax overload errors in the dashboard/digest pollers, and relaunched the iOS app in Simulator after a successful rebuild
  - Verified the iOS simulator build still succeeds after the digest and ticker-detail fixes, and traced the backend analysis pipeline enough to confirm digest freshness is cache-backed while position/ticker detail still falls back cleanly when no live analysis exists
  - Simplified the digest risk score card by removing the sparkline, prior-digest delta, and thesis card, moved the score to the top of the page, added a visible What Matters Today section, and cleaned underscored macro/sector labels plus noisy watch-item phrasing
  - Fixed the digest refresh path by caching synthesized fallback digests server-side and extending the iOS digest request timeout so the first slow load can complete instead of surfacing the generic error message
  - Reverified the iOS simulator build/run state for the current routing and lazy-load gating pass; the app still launches successfully and Digest remains the initial tab due to persisted tab selection
  - Routed dashboard, digest, and alerts position links to the shared ticker-detail screen so search, watchlist, holdings, dashboard, and alerts all land on the same improved detail UI
  - Gated digest and alerts tab loading behind actual tab selection to reduce eager fetch pressure and restore the dashboard fetch path during app launch
  - Replaced the old holdings-only position detail path with a thin bridge into the new ticker-detail UI so holdings, watchlist, and search all land on the same improved screen
  - Replaced the custom bottom dot tab bar with a simpler native tab bar styled to the Clavix dark palette, per the latest iOS UI direction
  - Replaced the Home digest teaser's leftover "sector overview" placeholder with a real sector-preview module backed by digest data
  - Fixed Digest score overview parity by deriving the sparkline from real digest history and aligning the delta label with the actual prior-digest score change
  - Restyled Holdings rows back toward the mockup by removing nested row cards, restoring flatter list rows with dividers, and simplifying the score/trend presentation
  - Rebuilt and relaunched the iOS app in the iPhone 17 Simulator after the regression-repair pass: BUILD SUCCEEDED
  - Restyled News to the prototype feed layout with a custom top bar, filter chips that include counts, a hero story card, and compact follow-on story rows
  - Restyled ticker detail to the prototype long-scroll layout with a custom inline nav bar, score hero, price card with sparkline and range chips, fundamentals grid, dimension bars, watch list, and compact recent news and alert sections
  - Updated article detail to use the same inline-back navigation pattern so the News-to-article-to-ticker flow stays visually consistent with the migrated design language
  - Rebuilt and launched the fully migrated app in the iPhone 17 Simulator after the News and ticker-detail pass
  - Restyled Holdings toward the prototype with a custom top header, persistent search bar, compact holdings summary card, prototype-style watchlist and needs-review sections, and an all-holdings section with inline sort control
  - Restyled Digest toward the prototype with a custom top header, score overview card, reordered breakdown sections, and a dedicated What to Watch section
  - Restyled Alerts toward the prototype with a compact summary grid, filter chips, and a timeline-style alert feed that deep-links into held positions or ticker detail when possible
  - Verified the full iOS app still builds successfully after the Holdings, Digest, and Alerts parity pass: BUILD SUCCEEDED
  - Refactored onboarding to the prototype-style 4-step flow with a real date-of-birth entry step, a top progress bar, updated Clavix branding, and the existing profile save path preserving backend compatibility by deriving the stored birth year from the entered DOB
  - Restyled Home toward the prototype with a gauge-based hero, tighter top header actions, a prototype-style bottom tab bar, a compact 3-card stat strip, a change feed card, and an always-visible next scheduled run label
  - Rebuilt Settings into grouped row cards closer to the prototype, including a conditional plan row that only appears when backed by real subscription-tier data from preferences
  - Restyled the core iOS tab surfaces toward the design handoff: Home now has a triage hero, Holdings has a search/add control strip and filter chips, Digest has a summary hero, Alerts has a severity-first hero, and Settings now opens with a cleaner trust/preferences card
  - Swapped the custom tab-shell action bars on Holdings, Digest, Alerts, and Settings for more native navigation bars and top-level toolbar actions
  - Cleaned up the main iOS shell by removing duplicate top-bar tab shortcuts, keeping the bottom bar as the primary navigation pattern, and simplifying the settings actions menu
  - Improved holdings row interactions by moving delete into native swipe actions while preserving the delete context menu for power users
  - Rebuilt the iOS simulator target successfully and relaunched the Clavis app for hands-on UI testing
  - Reduced onboarding to the four-step handoff flow, removed the first-position and notification-permission prompts, and added a preference step that persists the default alert choices
  - Added the matching large price move alert toggle to Settings and regenerated the iOS Xcode project so the new news models are included in the app target
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
  - Started the ticker-intelligence backfill refactor: selected company-news articles are now scraped before downstream analysis, bad relevance cache payloads with failed LLM explanations are no longer reused, Google sector RSS queries are now added alongside CNBC sector feeds, macro persistence now prefers normalized raw model output, backfill scoring now omits live position sizing in favor of risk-profile semantics, and system backfill digest assembly no longer overwrites fresh current-run payloads with stale snapshot history
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
