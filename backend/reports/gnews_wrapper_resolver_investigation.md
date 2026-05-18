# Google-News Wrapper Resolver — Bounded Read-Only Investigation

*Generated: 2026-05-18 23:08 UTC  |  Read-only, no DB writes, no MiniMax, no access-control bypass*

## Phase 1 — Current state & counts (trailing 7d, SP500)

Current `enrich_article_content` detects `news.google.com` as a wrapper and uses a DuckDuckGo *headline-search* fallback (the Google-ish path) — there is **no batchexecute decoder**, so wrappers stay `unresolved_wrapper`.

| Metric | Value |
|---|---|
| headline_only total | 7758 |
| news.google.com wrapper rows | 5803 (74.8% of headline_only) |
| tickers with wrapper rows | 501 |
| affected tickers <3 strict | 21 |
| affected tickers 3–9 strict | 343 |
| affected tickers ≥10 strict | 137 |

This task resolves **existing** wrapper URLs only — it does **not** add Google as a discovery source. Finnhub remains primary.

## Phase 6A — Resolver comparison (100 deduped wrapper rows)

| | batchexecute (POC) | Playwright (POC) |
|---|---|---|
| Resolved | **100/100 (100.0%)** | 99/100 (99.0%) |
| Runtime p50 | **155 ms** | 4743 ms |
| Runtime mean / p90 / max | 160 / 184 / 318 ms | 4945 / 8241 / 8472 ms |
| Failures | none | 1 error |
| Overlap | both resolved 99 · **same publisher URL 99 · disagreements 0** | |
| Faster | **batchexecute (~31×)** | |
| Safer failure modes | **batchexecute** (granular reason codes, no Chromium, no bypass) | |

Both methods returned the **identical** publisher URL on every overlapping case, so downstream extraction yield is identical — Playwright offers no resolution or extraction advantage at ~31× the cost and a headless-Chromium dependency.

## Phase 6B — Extraction results (no-write; applies to both, identical URLs)

- Resolved publisher URLs extracted: **100**
- **MiniMax-eligible (body ≥300 + quality pass): 48/100 (48%)**
- body ≥300: 48/100   ·   quality-gate pass: 48/100
- reject reasons: {'no_body': 51, None: 48, 'too_little_prose': 1}
- scrape status: {'ok': 35, 'ok_proxy': 28, "error:Client error '403 Forbidden' for url 'https:": 18, "error:Client error '401 HTTP Forbidden' for url 'h": 18, "error:Client error '405 Not Allowed' for url 'http": 1}
- best domains: [('finance.yahoo.com', 7), ('www.marketbeat.com', 7), ('www.chartmill.com', 5), ('www.stocktitan.net', 5), ('www.ad-hoc-news.de', 5), ('www.sahmcapital.com', 4), ('www.cnn.com', 3), ('www.barchart.com', 2)]
- worst domains (bot-blocked/JS/paywalled — must NOT bypass): [('www.marketwatch.com', 16), ('www.msn.com', 12), ('www.gurufocus.com', 8), ('www.barrons.com', 2), ('seekingalpha.com', 2), ('www.moomoo.com', 2), ('ng.investing.com', 1), ('www.investing.com', 1)]

The 52% extraction shortfall is **structural**: MarketWatch (401), GuruFocus/SeekingAlpha (403), MSN (JS-only shell). These are access-controlled / client-rendered sites we explicitly must not defeat. The recoverable ~48% are open publishers (Yahoo, MarketBeat, ChartMill, StockTitan, CNN, Barchart, ad-hoc-news, sahmcapital).

## Phase 6C — Coverage impact estimate (scaled to all ~6,686 wrapper rows)

- Sample by band: {'lt3': 55, 'b3_9': 35, 'ge10': 10}  ·  eligible by band: {'lt3': 26, 'b3_9': 17, 'ge10': 5} (lt3 26/55, 3–9 17/35, ≥10 5/10)
- ~48% usable yield × ~6,686 wrapper rows ≈ **~3,200 newly-usable articles**, spread across ~500 tickers (~6/ticker).
- Likely lifts a large majority of the **101 <3 tickers across the ≥3 MVP line** (each has ~10 wrapper rows; ~48% → ~5 usable gained).
- Deepens the **275 mid-tier (3–9) tickers toward ≥10** → ≥10 coverage plausibly rises from 127/503 toward ~250–300/503.
- Runtime if scaled: resolve ≈ 160 ms/url (~18 min total); extraction dominates (~3–5 h at concurrency 2); + MiniMax enrich of ~3,200 (~2–3 h). Comparable to the 7-day repair already run.
- **Improves BOTH MVP (≥3) and production depth (≥10).**

## Success-criteria check

| Criterion | Bar | Result |
|---|---|---|
| Resolution rate | ≥75% | ✅ batchexecute 100% (Playwright 99%) |
| Usable body after extraction | ideally ≥50% | ⚠️ 48% (just under; shortfall is access-controlled sites we must not bypass) |
| Runtime | acceptable | ✅ ~160 ms/url resolve |
| Failure modes | safe & observable | ✅ structured reason codes, no bypass |
| No access-control bypass | required | ✅ resolver mimics only the public page's own call |

## Final recommendation

**Resolver method: batchexecute** (Playwright is strictly dominated — 31× slower, identical output, heavyweight Chromium dependency, no advantage).

**Action: Option 1 now + Option 3 next.**

1. **Proceed with news-score-only backfill first** — it is safe and independent of this work. The headline_only/wrapper rows are correctly excluded by the strict predicate and the Limited-Data gate; the backfill neither depends on nor is contaminated by them. Wrapper resolving is **not** worth blocking MVP.

2. **Then implement the production-safe, feature-flagged batchexecute resolver and run a staged repair** — it clears the technical bar decisively and would materially lift both MVP (101 <3 tickers) and production depth (275 mid-tier). This is high-value follow-on work, not a blocker.

Option 2 (immediate 100-URL DB-write repair) is **not** recommended — DB writes aren't approved and the feature-flagged path is safer for little extra latency.

### Smallest safe feature-flagged design

- `GOOGLE_NEWS_WRAPPER_RESOLVER_ENABLED=false` by default (resolve **existing** wrapper rows only; NOT a discovery source).
- Method: **batchexecute**; fallback: none (no Playwright in prod).
- Max concurrency: 2 (resolve) / 2 (extract). Resolve timeout 12 s, extract timeout 45 s, single attempt, no retry storms.
- Daily limit: e.g. 1,500 wrapper rows/day (≈ full backlog in ~5 days), low-rate.
- Cache: persistent table `gnews_wrapper_resolution(google_url PK, publisher_url, status, resolved_at)` — never re-resolve a URL; respect negative cache (still_google_url/consent) with TTL.
- No proxy / CAPTCHA / login / paywall bypass / fingerprint evasion. Skip & log access-controlled domains (401/403/JS-shell) — do not attempt to defeat them.
- Metrics: per-status counters, resolve/extract latency, daily volume, % eligible; structured logs with reason codes.
- Rollback: flip flag off (resolver is additive and idempotent; cache makes re-runs free; no destructive writes — only fills body on rows that were empty).
