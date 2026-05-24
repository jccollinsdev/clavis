# CLAVIX TRUTH

**The single source of truth for what Clavix is, who it's for, and how it works.**

**Version:** 2.0
**Last updated:** May 6, 2026
**Status:** Authoritative. Supersedes all prior product, methodology, pricing, and roadmap documents.

> **Read this first.** If anything in this codebase contradicts this document — code comments, other docs, README files, in-app copy, anything — this document is correct and the other thing is wrong. Fix the other thing.

---

## Table of Contents

1. [What Clavix Is](#1-what-clavix-is)
2. [Identity & Branding](#2-identity--branding)
3. [Ideal Customer Profile](#3-ideal-customer-profile)
4. [Value Proposition](#4-value-proposition)
5. [The Ticker Universe](#5-the-ticker-universe)
6. [The Five Risk Dimensions](#6-the-five-risk-dimensions)
7. [The Composite Score & Grade](#7-the-composite-score--grade)
8. [The Methodology Drill-Down](#8-the-methodology-drill-down)
9. [The Daily Digest](#9-the-daily-digest)
10. [News Pipeline](#10-news-pipeline)
11. [Portfolio Mechanics](#11-portfolio-mechanics)
12. [Search & Ticker Detail](#12-search--ticker-detail)
13. [Watchlist](#13-watchlist)
14. [Score History](#14-score-history)
15. [Alerts & Notifications](#15-alerts--notifications)
16. [Tier Split: Free vs Pro](#16-tier-split-free-vs-pro)
17. [Refresh Cadence](#17-refresh-cadence)
18. [Out of Scope for v1](#18-out-of-scope-for-v1)
19. [v1.5 Roadmap](#19-v15-roadmap)
20. [Glossary](#20-glossary)

---

## 1. What Clavix Is

**Clavix is a portfolio risk intelligence app for self-directed investors managing significant assets.**

It tells the user:
- What changed overnight at three levels (macro, sector, individual position)
- What that means specifically for their portfolio
- How risky any stock is, with full transparency into why

It does NOT:
- Recommend buys or sells
- Predict prices
- Manage money
- Provide personalized investment advice

The product is **informational**, not advisory. Every output is a description of risk based on observable data, not a recommendation.

The mental model: **Bloomberg Terminal compressed into a daily morning briefing tailored to one user's portfolio, with full transparency into how every score is derived.**

### The one-sentence pitch

> "Clavix tells you what happened to your portfolio overnight, what it means, and how risky every position you own actually is — with the math shown."

### The job-to-be-done

When someone uses Clavix, this disappears from their life: **the 30-60 minutes every morning spent reading Bloomberg, Seeking Alpha, Yahoo Finance, and CNBC trying to figure out what news from the last 12 hours actually matters to their book, and whether anything in their portfolio has gotten more dangerous.**

---

## 2. Identity & Branding

### Names — the rule

| Surface | Name | Why |
|---|---|---|
| User-visible everywhere (app UI, marketing, App Store, support email, copy) | **Clavix** | This is the product brand. |
| Legal entity | **Andover Digital LLC** | Parent company. Owns Clavix. Used for ToS, Privacy Policy, App Store seller, banking. |
| Internal Swift types, directories, Xcode project | **Clavis*** (e.g. `ClavisApp`, `ClavisDesignSystem`, `ios/Clavis/`) | No rename. Refactor risk too high. Internal-only. |
| Backend API domain | `clavis.andoverdigital.com` | Existing, working, behind Cloudflare Tunnel. Do not change. |
| Marketing site | `getclavix.com` | Public-facing. ToS, Privacy, Methodology, Pricing, App Store badge live here. |
| iOS bundle ID | `com.clavisdev.portfolioassistant` | Already provisioned. Do not change. |
| iOS CFBundleDisplayName | `Clavix` | What users see on their home screen. |
| FastAPI title | `Clavix API` | Currently correct. |
| URL scheme | `clavix://` AND `clavis://` (dual) | New scheme is canonical. Old scheme retained because SnapTrade is configured with it. Both must work. |
| Container name | `clavis-backend-1` | Existing, working. Do not rename. |
| Repo / file paths | `/Users/sansarkarki/Documents/Clavis/`, `/opt/clavis/` | No rename. |

### What this means in practice

**Anywhere a user can see it, the word is "Clavix".** Anywhere only an engineer or a log file can see it, "Clavis" is fine.

**Banned strings in user-visible UI/copy:**
- "Clavis" (the old brand — ALL user-visible references must be "Clavix")
- "Clavynx" (a typo from an earlier era)
- "SnapTrade" (the user connects "their brokerage", not a third-party service)
- "Shared ticker cache" (internal term — say "ticker data" or just don't mention it)
- Any backend status string like "queued / running / failed / completed" shown via `.capitalized`

**Banned strings in code comments and internal docs:** none. Use whatever's clearest.

### Tagline

**"Portfolio risk, measured."**

This is the App Store subtitle (under 30 chars), the onboarding hero line, and the marketing site headline. Use it everywhere a tagline is needed. Do not invent new ones.

### Tone of voice

Clavix sounds like **a credit-rating agency, not a research analyst**. Calm, precise, observational. Letter grades. Numbers. Evidence.

It does NOT sound like:
- A trading newsletter ("This stock is RIPE for a breakout!")
- A research analyst ("Our coverage suggests...")
- A wellness app ("Your portfolio is feeling stressed today")
- A general AI assistant ("Sure! I'd be happy to analyze your portfolio!")

Banned vocabulary in user-visible copy: *coverage, monitor, watch, momentum, analyst, research, sentiment, thesis, provisional, current read, recommendation, suggest, advise, predict, forecast.*

Use instead: *rating, track, trend, data, evidence, signal, change, observation.*

---

## 3. Ideal Customer Profile

### The one-line ICP

**A 45-65 year old self-directed investor managing $500K-$5M+ in personal assets, who currently spends 30-60 minutes every morning manually piecing together what overnight news means for their portfolio across Bloomberg, Seeking Alpha, Yahoo Finance, and CNBC.**

### Demographics

- **Age:** 45-65 (skews older than the typical fintech app user)
- **Net worth:** $500K-$5M+ in liquid investable assets
- **Location:** US-based, English-speaking (initially)
- **Profession:** Often retired, semi-retired, or in a senior professional role (medicine, law, finance, engineering, executive). Not tied to a 9-5.
- **Tech comfort:** High enough to use Bloomberg-like tools and read 10-Ks. Not afraid of complex UIs.

### How they invest

- Holds individual stocks AND ETFs AND occasionally bonds/treasuries
- Portfolio is a mix of large-cap blue chips, dividend stocks, broad-market ETFs, and a smaller satellite of conviction picks
- Holding period is months to years, not days
- Cares more about **wealth preservation** than wealth multiplication
- Does NOT day-trade
- Does NOT chase memes
- Reads 10-Ks, earnings transcripts, Fed minutes
- Has a financial advisor relationship for some assets but actively manages a sleeve themselves

### Their daily routine (today, before Clavix)

- Wakes between 6-7am
- Opens phone or laptop, checks futures, then opens 4-6 apps in sequence
- Spends 30-60 minutes piecing together: macro overnight → sector moves → news on each holding → mental update on portfolio risk
- Most mornings, nothing has materially changed — but they don't know that until they've done the work
- The cost is the time AND the mental tax of "did I miss something"

### Their tools today

- **Bloomberg Terminal** if they're really serious (rare — most aren't)
- **Yahoo Finance / Google Finance** for quotes and basic charts
- **Seeking Alpha** for opinion / analyst commentary
- **CNBC, WSJ, FT** for news
- **Their brokerage** (Fidelity, Schwab, Vanguard, IBKR, Merrill, sometimes E\*TRADE) for actual positions
- **A spreadsheet** they keep for cost basis, sometimes
- **Robinhood** is NOT in this list. They are not Robinhood users.

### What they're NOT

- Not day traders
- Not options gamblers
- Not "FIRE movement" 25-year-olds
- Not crypto-native
- Not beginners — they have a real risk framework, they just don't have a tool that respects it
- Not institutional — no compliance team, no Bloomberg access, no team of analysts

### The one sentence that captures them

> "I'm not trying to find the next 10-bagger. I just want to know if anything in my book got materially worse overnight, before the day gets away from me."

### Where to find them

- Reddit: r/investing, r/SecurityAnalysis, r/dividends (NOT r/wallstreetbets)
- Seeking Alpha author comments (paying SA Premium subscribers)
- Substack: Stratechery, The Diff, Doomberg, Net Interest, Pragmatic Capitalism
- Bogleheads forum (some, but they're more passive)
- Investor Discord communities for the more sophisticated end
- Twitter/X finance scene (FinTwit), but the older mature accounts, not the trader hype crowd

---

## 4. Value Proposition

### The promise

**You spend 30-60 minutes every morning trying to figure out if your portfolio just got more dangerous. Clavix answers that in 60 seconds — and shows the math.**

### What replaces what

| What you do today | What Clavix does instead |
|---|---|
| Read 4-6 apps to piece together overnight news | One morning briefing, tailored to your holdings |
| Manually translate macro news into "what does this mean for me" | Pre-translated: macro → sector → your positions, in order |
| Eyeball position sizing and mentally model risk | A letter grade per position, with the full math shown |
| Find out a position deteriorated only when it's too late | Alerts the moment a grade or risk dimension shifts |
| Trust an opaque "AI risk score" from a fintech app | See every article, every formula, every input that produced every score |

### The differentiator

**Transparency is the moat.** Other apps give you a black-box risk number. Clavix shows you:

- Every news article that was considered for sentiment scoring
- The score assigned to each article and why
- The exact formula for each of the five risk dimensions
- The inputs used (debt-to-equity = X, free cash flow margin = Y, etc.)
- How the dimensions combined into the composite score
- The rolling 90-day history of every score

If a sophisticated investor can't explain why a position is rated B-, they don't trust the rating. Clavix is the rating they can trust because they can audit it.

---

## 5. The Ticker Universe

### Definition

The Clavix universe is the set of tickers that have pre-computed risk data, news, and methodology in the database.

**Universe = S&P 500 ∪ {non-S&P US-listed stocks where market cap ≥ $2B AND 30-day average daily dollar volume ≥ $20M} ∪ {top 50 ETFs by AUM}**

Approximate size: **~700-1,000 tickers.** Fluctuates as market caps and volumes change.

### What's IN the universe

- All S&P 500 constituents (always, regardless of cap/volume drift)
- Mid- and large-cap US stocks above the dual cap+volume threshold
- The top 50 ETFs by AUM (broad market, sector, fixed-income, commodity, international — but NOT leveraged or single-stock ETFs)

### What's NOT in the universe

- Penny stocks
- OTC-only stocks
- Stocks below $2B market cap
- Illiquid stocks (under $20M average daily dollar volume)
- Leveraged ETFs (TQQQ, SQQQ, etc.)
- Single-stock ETFs
- Cryptocurrency / crypto ETFs (defer to v1.5)
- International stocks (defer to v1.5; ADRs of major foreign companies *are* included if they meet thresholds)
- Options, futures, derivatives

### What happens if a user wants a ticker outside the universe

Two paths:

1. **They can still ADD it to their portfolio manually.** The system flags it as `outside_universe = true`. Risk scoring runs in degraded mode (limited fundamentals, basic news). They see a banner: *"This ticker isn't in the Clavix tracked universe. Risk data may be limited."*
2. **Pro users can request a ticker be added to the universe.** Backend admin reviews and adds if warranted. Currently manual; v1.5 will automate via the same cap+volume filter.

### Universe refresh

The universe membership list is **recomputed weekly** (Sunday night ET):
- New stocks crossing the threshold get added
- Stocks falling below get **flagged but NOT removed** (we don't want to lose history)
- ETF top-50 list refreshed weekly

### Universe data backfill

Every ticker in the universe has:
- Latest fundamentals (Finnhub)
- Latest price data (Polygon)
- Recent news (last 30 days, refreshed per cadence in §17)
- Risk score for today (refreshed per cadence in §17)
- Score history going forward from the day it entered the universe

---

## 6. The Five Risk Dimensions

Every ticker in the universe is scored across **exactly five dimensions**. Not four. Not six.

The legacy schema has a fourth dimension `position_sizing` and a fifth `thesis_integrity`. **Both are deprecated.** The new five dimensions replace them entirely.

### Dimension 1: Financial Health (0-100)

**What it measures:** The structural balance-sheet and cash-flow strength of the company.

**Inputs:**
- Debt-to-equity ratio (lower = healthier)
- Free cash flow margin (higher = healthier)
- Interest coverage ratio (higher = healthier)
- Current ratio (higher = healthier, up to a point)
- Revenue growth trend, trailing 4 quarters (positive = healthier)
- Profitability trend (consistent positive net income = healthier)

**Update cadence:** Quarterly, on earnings filings. Slow-moving by design.

**Source:** Finnhub `stock/metric` endpoint + `stock/profile2`.

**Special handling:** ETFs don't have these metrics. ETF financial health is computed as the weighted-average financial health of the ETF's top 25 holdings (where those holdings are themselves in the universe). If too few holdings are in the universe, financial health is shown as "N/A — diversified holding".

### Dimension 2: News Sentiment (0-100)

**What it measures:** The tone and severity of news coverage about this ticker over the trailing 7 days.

**Inputs:**
- Every article ingested for this ticker in the last 7 days
- Each article gets a sentiment score (0-100) by the LLM
- Articles are weighted by recency (last 24h = 3x weight, 24-72h = 2x weight, 72h-7d = 1x weight)
- Articles are weighted by source quality (Tier 1 sources = Reuters, WSJ, Bloomberg, FT, AP = 1.5x; Tier 2 = MarketWatch, Yahoo Finance, Investing.com, Seeking Alpha free = 1x; Tier 3 = aggregators, blogs = 0.5x)
- Volume signal: if article count this week is >2x the trailing 4-week average, it's a "high-volume coverage" event regardless of sentiment polarity (unusual attention is itself a risk signal)

**Update cadence:** Every 4 hours for tickers in any user's portfolio or watchlist. Every 24 hours for dormant tickers.

**Source:** Google News RSS for discovery → Jina AI Reader (or trafilatura/newspaper4k as fallback) for article body extraction → MiniMax LLM for sentiment scoring.

**Special handling:** If fewer than 3 articles in 7 days, news sentiment shows "Limited Data" instead of a score, and is excluded from composite calculation (composite is rescaled to the four remaining dimensions).

### Dimension 3: Macro Exposure (0-100)

**What it measures:** How vulnerable the stock's price is to macro factors based on its historical correlations.

**This is a math problem, not an LLM problem.** Run a regression of the stock's daily returns over trailing 252 trading days (1 year) against:
- 10-year Treasury yield changes
- Dollar Index (DXY) changes
- Crude oil (WTI) changes
- VIX level
- S&P 500 returns (beta)

The **macro vulnerability score** is the weighted absolute sensitivity (sum of squared correlations, normalized to 0-100). High score = highly macro-sensitive = lower safety = lower dimension score.

The narrative layer: an LLM looks at the current macro regime (rates rising? VIX spiking?) and writes a one-paragraph "what this means right now" given the stock's sensitivities.

**Update cadence:** Weekly recalculation of correlations. Daily refresh of the narrative layer based on current macro state.

**Source:** Polygon for stock daily bars and macro factor levels.

### Dimension 4: Sector Exposure (0-100)

**What it measures:** How vulnerable the stock is to its sector's current state.

**Two-layer approach:**

**Quantitative layer:**
- Compute sector beta (rolling 90-day correlation of stock returns to sector ETF returns, e.g. AAPL vs XLK)
- Compute sector momentum (sector ETF performance vs S&P 500 over trailing 30 days)
- Compute sector breadth (% of sector ETF constituents above 200-day MA)
- Combine into a sector vulnerability score

**Narrative layer:**
- LLM reads sector-specific RSS feeds and recent sector news
- Generates a one-paragraph "current sector state" assessment
- Notes specific sector risks (regulatory, supply chain, demand cycle)

The dimension score combines both. A stock in a high-beta sector that's currently in drawdown scores low. A stock in a defensive sector with strong breadth scores high.

**Update cadence:** Daily quantitative refresh. Every 12 hours narrative refresh.

**Source:** Polygon for sector ETF data + CNBC sector RSS + Google News sector queries.

### Dimension 5: Volatility (0-100)

**What it measures:** How much price action is happening, and whether it's trending up or down.

**Inputs:**
- Realized volatility, 30-day annualized
- Realized volatility, 90-day annualized
- The ratio: 30d / 90d (>1 means vol is rising, <1 means vol is falling)
- Maximum drawdown from trailing 252-day high
- Beta to S&P 500 over trailing 252 days

The score is constructed so that:
- Low absolute vol + falling vol trend = high score (safe)
- High absolute vol + rising vol trend = low score (risky)
- Extreme drawdown + high beta = lowest scores

**Update cadence:** Daily, after market close.

**Source:** Polygon daily bars.

### Equal weighting in the composite

All five dimensions are weighted **20% each** in the composite score.

Earlier versions of the methodology debated structural weighting (financial health 30%, etc.). **Equal weighting is final.** Reason: it's simpler to explain, and any time-scale imbalance (news moves fast, fundamentals move slow) is acceptable because the user can drill into each dimension individually if they want a slower or faster lens.

---

## 7. The Composite Score & Grade

### Composite formula

```
composite_score = (financial_health + news_sentiment + macro_exposure +
                   sector_exposure + volatility) / 5

(Where each input is 0-100. Composite is also 0-100.)
```

If a dimension is "Limited Data" (e.g. news sentiment with <3 articles), it's excluded and the composite is the average of the remaining dimensions, with a flag shown to the user.

### Grade scale

| Grade | Score | Meaning |
|---|---|---|
| **AAA** | 90-100 | Treasury-grade. Major defensive blue chips, broad-market ETFs, ultra-stable names. |
| **AA** | 80-89 | Investment-grade safe. Strong large caps, defensive sectors, well-capitalized. |
| **A** | 70-79 | Solid. Healthy balance sheet, reasonable risk profile. |
| **BBB** | 60-69 | Stable but watch points. Some pressure but no immediate concerns. |
| **BB** | 50-59 | Mixed signals. Real risks present, weighing them is required. |
| **B** | 40-49 | Elevated risk. Material concerns across multiple dimensions. |
| **CCC** | 30-39 | High risk. Pressure compounding. |
| **CC** | 20-29 | Severe risk. Multiple dimensions in deterioration. |
| **C** | 10-19 | Distressed. Near-failure signals in fundamentals or news. |
| **F** | 0-9 | Failure mode. Illiquid, broken, near-zero. |

### Why bond-rating analog instead of letter grades A-F

The legacy app used A/B/C/D/F. We replaced it because:
1. School grades imply judgment ("you got a D — bad student"). Bond ratings imply observation ("rated BBB — stable but watch").
2. Sophisticated investors already understand bond ratings intuitively. AAA = treasury. F = junk.
3. It positions Clavix as a *rating service*, not a *report card*.

### Hysteresis (anti-flicker)

A position cannot change grade on a single day's data unless the move is significant.

**Rule:** A grade change requires the new score to be **at least 3 points across the boundary** AND **maintained for at least 2 days**.

Example: AAPL is rated AA at 80.5. A day where the score drops to 79.8 does NOT downgrade to A. The score must drop to ≤77 AND remain ≤77 for 2 consecutive days before AAPL is rated A.

This prevents grade flicker from noise and makes alerts trustworthy.

### What the composite does NOT include

- Position sizing (how much of the user's portfolio is in this name) — this is portfolio-level metadata, not a property of the ticker
- Cost basis (what the user paid) — this is portfolio-level metadata
- Personal "thesis" tracking — out of scope
- Unrealized P&L — that's a brokerage feature

The ticker score is **about the ticker**, not about any user's relationship to it. Personalization happens at the digest and "what it means for you" layer (§9, §11), not at the score layer.

---

## 8. The Methodology Drill-Down

This is the core feature of the v2 product. **It's what was missing in v1 and what the entire pivot is about.**

### The principle

**Every score must be auditable.** A user must be able to tap any number and see:
1. The formula
2. The inputs
3. The data sources
4. When each input was last updated

### Implementation: progressive depth

The drill-down is a **progressive disclosure pattern**, not a separate page.

**Surface (default view):** the score number and grade.

**Tap once:** a "methodology drawer" slides up showing the formula and the dimension scores.

**Tap any dimension:** that dimension expands to show:
- Its formula
- Each input value with the date it was last refreshed
- A link to view the underlying data (e.g. for news sentiment, the list of articles)

**Tap an article in news sentiment:** see the full TLDR, the LLM's reasoning for its sentiment score, and a link to the original article.

### What this looks like for each dimension

**Financial Health:** show each ratio with its current value, the comparison to industry median, and the date of the latest filing. Click each ratio to see its 4-quarter history.

**News Sentiment:** show the full list of articles considered (last 7 days), each with its individual sentiment score, source tier, and recency weight. Click any article for TLDR + LLM reasoning. Show the volume-of-coverage indicator separately.

**Macro Exposure:** show the regression coefficients to each macro factor, the R² of the model, the current level of each factor, and the resulting sensitivity score. Show the LLM-generated narrative paragraph.

**Sector Exposure:** show sector beta, sector momentum, sector breadth — each with its current value and a sparkline of the last 90 days. Show the LLM-generated sector state paragraph.

**Volatility:** show realized vol numbers (30d, 90d), the ratio, the max drawdown, and beta — all with sparklines.

### The methodology page (public + in-app)

The same methodology lives in two surfaces:

**Public methodology page at `getclavix.com/methodology`** — for SEO, trust, and pre-purchase research. Anyone can read it.

**In-app methodology view** — accessible from Settings → Methodology AND from the drill-down on any score. Same content. Native rendering, not a webview.

Both surfaces stay in sync because they're generated from the same Markdown source: `docs/PUBLIC/methodology.md`. CI rebuilds both on changes.

### Critical: no fabricated previous scores

The legacy app showed "was X" deltas where X was synthesized (e.g., `current - 8`). **This is banned.**

If a position has fewer than 2 days of score history, **show no delta**. Show "—" or "New". The user must trust that any number Clavix shows is real.

---

## 9. The Daily Digest

### Format

A **personalized written briefing**, sent every morning, that reads like a portfolio manager's pre-market memo to themselves.

Not a card-stack. Not a feed. A briefing.

Structure: prose-with-cards-interleaved. Cards anchor data points. Prose connects them.

### Sections, in order

1. **Header**
   - Date, time of generation
   - Portfolio composite grade (rolled up across all holdings, weighted by position size)
   - One-line summary: "Your portfolio is rated **AA** today, unchanged from yesterday."

2. **Overnight Macro**
   - 1-2 paragraphs on what happened in macro overnight (futures, Asian session, European open, Fed/Treasury news, key data prints)
   - Sourced from CNBC RSS + Google News macro queries + LLM synthesis
   - Generic — every user gets the same macro section (cost optimization)

3. **Sector Heat**
   - Sector-by-sector overnight performance for sectors the user has exposure to
   - "Tech is up 0.4% pre-market on cooler-than-expected CPI. You hold AAPL, MSFT, GOOGL."
   - Personalized to user's sectors

4. **Your Positions**
   - One block per holding, ranked by absolute risk change overnight (biggest mover first)
   - Each block: ticker, current grade, change indicator, 1-2 sentences on what news drove the change (or "no material news" if quiet)
   - Tap any block → navigate to ticker detail
   - Personalized — this is the heart of the digest

5. **Watchlist Updates** (Pro)
   - Same format as positions, but for watchlist tickers
   - Free users: up to 5 watchlist tickers shown
   - Pro users: unlimited

6. **What to Watch Today**
   - Calendar items: earnings reports today from any holding/watchlist, Fed events, economic data prints, major scheduled events
   - Sourced from Finnhub earnings calendar + macro calendar
   - Personalized to user's holdings

### Length tiers (per user preference)

- **Brief** (~300 words): just the header + grades + 2-3 line summary
- **Standard** (~800 words, default): full structure above, concise
- **Verbose** (Pro only, ~1500 words): full structure with deeper "what it means for you" prose on each position, more detail on news, options-flow signals if available

Cost optimization: macro section is generated once per day and shared across all users. Sector section is generated once per sector per day. Only the "Your Positions" personalization is per-user.

### Generation timing

- 5:00 AM ET: macro and sector sections generated (one-time, shared)
- 5:30 AM ET - 7:00 AM ET: per-user digest generation (parallelized, prioritized by user's preferred delivery time)
- Default delivery time: 7:00 AM in the user's local time zone
- User can configure between 5:00 AM and 9:00 AM in 15-minute increments

### LLM provider for digest

**MiniMax-M2.7** via OpenAI-compatible client. ~$20/mo flat fee gives 45K requests/week. At ~10 requests per user per day (digest generation + news sentiment + dimension narratives), this supports up to ~600 active users on the current plan. Scales linearly from there.

---

## 10. News Pipeline

### Discovery

**Source (current, 2026-05-24 override):** **Finnhub `company_news`** per ticker. Google News RSS exists in code (`rss_ingest.py`) and is used in some auxiliary paths, but Finnhub is the canonical discovery source for v1. Do not silently switch back to Google News RSS without an explicit product decision.

For each ticker in the universe:
- Call Finnhub `company_news` with a 48h trailing window
- Pull headlines + URLs
- Deduplicate by canonical URL (strip tracking params)
- Filter: drop articles with low ticker relevance (the article must mention the ticker or company prominently, not as a passing mention)

**Cadence:** Every 4 hours for active tickers (in any user's portfolio/watchlist). Every 24 hours for dormant tickers.

### Article body extraction

**Primary:** Jina AI Reader (`r.jina.ai/<url>`). Free tier covers reasonable volume. Returns clean Markdown.

**Fallback:** trafilatura (Python lib, free, open-source). Used if Jina fails or rate-limits.

**Last resort:** newspaper4k. Used if both above fail.

**Paywalled content:** if the article is from a paywalled source (WSJ, FT, Bloomberg), Clavix saves the headline and a "[Paywalled]" body. The headline alone is still scored for sentiment but with a low-confidence flag.

### Sentiment scoring

Each article gets:
- A 0-100 sentiment score from the LLM
- A one-sentence reason for the score
- An "impact tag" (financial-impact / regulatory / leadership / product / macro / sector / other)

Stored in the database. Visible in the methodology drill-down.

### TLDR + "What It Means" generation

For each article, the LLM also generates:
- **TLDR:** 1-2 sentences summarizing the article
- **What It Means:** 1-2 sentences on the implication for the ticker (or the user's holding, if personalization is in scope — see §11)
- **Key Implications:** 2-4 bullet points of specific consequences (financial, operational, regulatory, etc.)

Generated once per article. Cached. Shown in the article view inside ticker detail.

### Sector & macro RSS

Separate RSS pipelines for sector-level and macro-level news:
- CNBC macro RSS: economic data, Fed, macro narratives
- CNBC sector RSS feeds: one per sector (Technology, Energy, Healthcare, Financials, etc.)
- Google News sector queries

These feed the digest's macro and sector sections, NOT individual ticker scores.

### Storage: ONE news store

The current code has three overlapping news stores (`news_items`, `ticker_news_cache`, `shared_ticker_events`). **The new architecture has exactly one: `shared_ticker_events`.**

`news_items` and `ticker_news_cache` will be retired in the refactor (see §17 of `REFACTOR_PLAN.md`).

`shared_ticker_events` schema:
- One row per article
- Linked to a ticker (or multiple tickers if the article is about multiple)
- Contains: headline, URL, source, published_at, body, sentiment_score, sentiment_reason, impact_tag, tldr, what_it_means, key_implications
- Indexed on (ticker, published_at desc) for fast retrieval

---

## 11. Portfolio Mechanics

### Adding a holding

Three paths:

**1. SnapTrade brokerage connection (Pro)**
- User clicks "Connect Brokerage" in onboarding or Settings
- Redirected to SnapTrade hosted connect URL
- Returns to Clavix via `clavix://snaptrade/callback` (with `clavis://` fallback for compatibility)
- Holdings auto-sync nightly + on user-triggered refresh
- Each synced position has `synced_from_brokerage = true` flag

**2. Manual entry (Free + Pro)**
- User enters: ticker, share count, average cost basis, purchase date (optional)
- Ticker validated against universe; if outside universe, user is warned but can proceed
- System fetches current price, calculates current value
- Each position has `synced_from_brokerage = false` flag

**3. CSV import (Pro)**
- Pro users can upload a CSV from their brokerage (Fidelity, Schwab, Vanguard, IBKR all support CSV exports)
- System parses ticker / shares / cost basis / purchase date columns (with column mapping UI)
- Bulk-imports as manual positions

### What's stored per holding

| Field | Required | Notes |
|---|---|---|
| ticker | yes | uppercased, validated |
| shares | yes | decimal (allows fractional) |
| cost_basis | yes (manual), auto (brokerage) | per-share average cost |
| purchase_date | optional | for manual entries; brokerage sync provides actual lot dates |
| current_price | computed | from price feed, refreshed daily |
| synced_from_brokerage | yes | boolean flag |
| brokerage_account_id | optional | for synced positions |
| created_at | auto | |
| updated_at | auto | |

### Per-user holdings limits

- **Free:** 3 holdings maximum. The 4th add attempt shows an upgrade prompt.
- **Pro:** unlimited.

### Personalization depth in "What It Means"

When an article is shown in the user's digest or ticker detail, the "What It Means" line considers:

1. **Whether they hold it** (everyone gets a generic version if they don't, a personalized version if they do)
2. **Position weight in their portfolio** (a 15% position triggers stronger language than a 0.5% position)
3. **Their cost basis and current P&L** (mentioned only when relevant — e.g., a stock down 30% from cost basis with bad news warrants different language than the same stock up 50% from cost basis with the same news)
4. **Correlated holdings** (if they hold AAPL + MSFT + GOOGL, an article about big tech regulation gets framed as portfolio-concentrated risk, not single-stock risk)

This is generated by the LLM at digest time (cached). Not regenerated on every page load.

---

## 12. Search & Ticker Detail

### Search

Universal ticker search, available from any screen via a search button or pull-down gesture.

- Searches the universe by ticker symbol or company name
- Returns ranked results with: ticker, name, current grade, current price
- Tapping any result → ticker detail screen
- A search result for a ticker outside the universe shows: "Not in tracked universe" with an "Add manually" CTA

### Ticker detail screen

Sections, top to bottom:

1. **Hero**
   - Ticker + company name
   - Current price + day change
   - Current grade (large)
   - Composite score (0-100)
   - Sparkline of last 30 days price (NOT score — score history is shown separately)

2. **Risk Dimensions**
   - 5 dimension scores in a row, each tappable
   - Tap a dimension → expands the methodology drill-down for that dimension

3. **What's Driving It**
   - 2-3 LLM-generated sentences explaining the current grade
   - Sourced from the most-impactful recent articles + dimension scores

4. **Recent News**
   - Articles from the last 14 days, most recent first
   - Each article: headline, source, published date, sentiment score (small), TLDR
   - Tap any article → article detail with full TLDR, What It Means, Key Implications, and link to source

5. **Score History**
   - Chart of composite score over time (since universe entry, capped at 90 days for v1)
   - Mini chart of grade over time below the score chart
   - "New" or "—" if <2 days of history

6. **Add to Portfolio / Watchlist**
   - Two CTAs: "Add to Holdings" and "Add to Watchlist"
   - If already held: "In your portfolio (X shares)" with link to portfolio
   - If on watchlist: "On your watchlist" with link

### Refresh on ticker detail

Free users see whatever cached data exists.
Pro users see a refresh button that:
- Triggers an immediate news pull for this ticker
- Triggers an immediate dimension recalculation (where possible without full pipeline)
- Returns updated data within ~30-60 seconds
- Rate-limited: 5 manual refreshes per ticker per day per user

---

## 13. Watchlist

### Behavior

A watchlist is a list of tickers the user wants to track without owning.

- Max 5 tickers (Free)
- Unlimited (Pro)
- Each watchlist ticker gets the same daily digest treatment as a holding (personalized "What It Means" if news happens)
- Watchlist tickers do NOT count toward portfolio risk metrics
- Adding a watchlist ticker does NOT require any cost basis or share entry

### UI

- Watchlist is a section on the Holdings screen, below the holdings list
- Same card style as holdings, but with a "watching" indicator instead of P&L
- Tap any watchlist ticker → ticker detail
- Long-press → "Remove from watchlist" / "Convert to holding"

---

## 14. Score History

### Storage

Every composite score and every dimension score is stored daily in `ticker_risk_snapshots`. One row per ticker per day. Includes:
- All five dimension scores
- Composite score
- Grade
- Snapshot type (`daily`, `manual_refresh`, `backfill`)
- Snapshot date
- Methodology version (so we can recompute if the methodology changes)

### Display in v1

- 30-day sparkline on ticker detail hero (composite score only)
- Full 90-day chart in the Score History section of ticker detail (composite + each dimension togglable)
- "New" indicator if <2 days of history

### v1.5 adds

- Trend analysis ("AAPL has trended down 8 points over 30 days, driven primarily by news sentiment")
- Comparison view (compare a stock's history to its sector or to the S&P)
- Custom date ranges
- Export to CSV (Pro)

---

## 15. Alerts & Notifications

### Alert types

1. **Grade Change Alert** — fires when any holding's grade changes (with hysteresis applied per §7)
2. **Major News Alert** — fires when an article tagged "high-impact" (earnings surprise, M&A, regulatory action, leadership change) is published for any holding
3. **Portfolio Grade Change Alert** — fires when the user's overall portfolio composite grade changes
4. **Watchlist Alert** (Pro) — same as Grade Change but for watchlist tickers
5. **Macro Shock Alert** — fires on big macro events (Fed surprise, major selloff, etc.) that affect the user's holdings

### Delivery channels

- **Push notification (APNs)** — primary channel
- **In-app alert center** — historical record of all alerts
- **Email** (Pro, opt-in) — daily digest of alerts (separate from the morning briefing)

Currently APNs is configured but `/health` reports `apns: missing` because the `.p8` key isn't deployed to the VPS. **Fixing this is a refactor priority.**

### Quiet hours

User-configurable in Settings:
- Start time (default 10:00 PM)
- End time (default 7:00 AM)
- Alerts during quiet hours are queued and delivered at the end-of-quiet-hours time

### Alert-tier configuration

Per user, configurable in Settings:
- Grade Change Alerts: on/off
- Major News Alerts: on/off
- Portfolio Grade Change: on/off
- Macro Shock: on/off
- Pro-only: severity threshold ("only alert me on AA→BBB or worse")

---

## 16. Tier Split: Free vs Pro

| Feature | Free | Pro |
|---|---|---|
| Sign up / sign in | ✓ | ✓ |
| Onboarding | ✓ | ✓ |
| Manual portfolio entry | ✓ (max 3 holdings) | ✓ (unlimited) |
| SnapTrade brokerage sync | — | ✓ |
| CSV import | — | ✓ |
| Watchlist | ✓ (max 5) | ✓ (unlimited) |
| Daily digest — Brief tier | ✓ | ✓ |
| Daily digest — Standard tier | ✓ | ✓ |
| Daily digest — Verbose tier | — | ✓ |
| Universal ticker search | ✓ | ✓ |
| Ticker detail screen | ✓ | ✓ |
| Methodology drill-down | ✓ | ✓ |
| Recent news per ticker | ✓ (last 7 days) | ✓ (last 30 days) |
| Score history | ✓ (30 days) | ✓ (full available) |
| Manual ticker refresh | — | ✓ (5/day/ticker) |
| Grade change alerts | ✓ | ✓ |
| Major news alerts | ✓ | ✓ |
| Watchlist alerts | — | ✓ |
| Macro shock alerts | — | ✓ |
| Email digest of alerts | — | ✓ |
| Severity threshold for alerts | — | ✓ |
| Export portfolio data | ✓ | ✓ |
| Delete account | ✓ | ✓ |

**Pricing:**
- **Free:** $0
- **Pro:** **$20/month** (post Apple cut). No annual plan at launch — revisit at v1.1 once retention data exists.
- **Trial:** 14 days of Pro free on signup, no credit card required, downgrades to Free automatically on day 15.

---

## 17. Refresh Cadence

| Data | Active tickers | Dormant tickers | Trigger |
|---|---|---|---|
| Price (daily bar) | Daily after market close | Daily after market close | Cron |
| News articles | Every 4 hours | Every 24 hours | Cron |
| News sentiment scoring | On article ingestion | On article ingestion | Pipeline |
| Financial Health | On earnings filing | On earnings filing | Cron checks daily |
| Macro Exposure (regression) | Weekly (Sunday) | Weekly (Sunday) | Cron |
| Macro Exposure (narrative) | Daily | Daily | Cron |
| Sector Exposure (quantitative) | Daily | Daily | Cron |
| Sector Exposure (narrative) | Every 12 hours | Every 24 hours | Cron |
| Volatility | Daily after market close | Daily after market close | Cron |
| Composite score | Daily | Every 2 days | Cron |
| Daily digest | Every weekday morning | — | Cron |
| Universe membership | Weekly (Sunday) | Weekly (Sunday) | Cron |

**"Active" = ticker is in any user's portfolio or watchlist. "Dormant" = no user is tracking it.**

When a user adds a holding/watchlist for a previously-dormant ticker, it's promoted to active and refreshed within 30 minutes.

---

## 18. Out of Scope for v1

These are explicitly NOT in v1. Do not let scope creep pull them in.

- Looming storylines / ongoing narrative tracking (v1.5)
- Score trend analysis ("X has trended down 8 points over 30 days") (v1.5)
- Verbose digest tier — wait, scratch that, **Verbose IS in v1 for Pro** (see §16)
- ETFs in the universe — scratch that, **ETFs ARE in v1** (see §5)
- Annual subscription plans (revisit v1.1)
- International stocks (excluding US-listed ADRs) (v1.5)
- Crypto / crypto ETFs (v2)
- Options / derivatives (never in scope)
- Web app (mobile only at launch)
- Android app (v2)
- Multi-portfolio support (v2 — one user = one portfolio)
- Tax-lot tracking / wash-sale tracking (v2)
- Dividend tracking (v2)
- Cost-basis adjustments (corporate actions) (v1.5)
- Currency conversion / multi-currency (v2)
- Sharing / social features (never in scope)
- Forum / community (never in scope)
- Investment recommendations (NEVER in scope — this is a regulatory line)
- Clavix-managed model portfolios (NEVER in scope)
- Trading execution (NEVER in scope — read-only forever)

---

## 19. v1.5 Roadmap

After v1 ships and stabilizes (target: ~30 days post-launch), v1.5 adds:

1. **Looming storylines** — clustering articles into ongoing narratives, surfacing when they heat up
2. **Score trend analysis** — natural-language explanations of multi-day score changes
3. **Score history charts** — comparison views, custom date ranges, CSV export
4. **Annual subscription plans** — once retention data justifies pricing
5. **Cost-basis adjustments for corporate actions** — splits, spinoffs, mergers
6. **Custom alerts** — user-defined alert rules (e.g., "alert me if AAPL's news sentiment drops below 40")
7. **Universe expansion** — more stocks above a lower cap+volume threshold, ADRs, select international
8. **Methodology versioning UX** — show users when methodology changed and how it affected their scores

---

## 20. Glossary

- **Active ticker** — a ticker in any user's portfolio or watchlist; refreshed at higher cadence
- **Composite score** — the 0-100 weighted average of the five dimensions
- **Dimension** — one of the five risk axes: Financial Health, News Sentiment, Macro Exposure, Sector Exposure, Volatility
- **Dormant ticker** — a ticker in the universe but tracked by no users; refreshed at lower cadence
- **Grade** — the bond-rating-style label for a composite score (AAA, AA, A, BBB, BB, B, CCC, CC, C, F)
- **Hysteresis** — the anti-flicker rule that prevents grade changes from minor score fluctuations
- **ICP** — Ideal Customer Profile (see §3)
- **Methodology drill-down** — the progressive-disclosure feature that lets users audit any score
- **Position** — a holding in the user's portfolio (with shares + cost basis)
- **Universe** — the ~700-1,000 tickers Clavix tracks with full data
- **Watchlist** — a list of up to 5 (Free) or unlimited (Pro) tickers the user is tracking but doesn't own

---

## Document control

This document is the **source of truth**. When it conflicts with anything else:
- Code → fix the code
- Other docs → archive/delete the other doc
- In-app copy → fix the copy
- Marketing copy → fix the marketing copy

Changes to this document require an explicit decision. Don't change it casually. When you do change it, update the version number and date at the top, and note the change in a `CHANGELOG.md` at the same level.
