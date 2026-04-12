# Portfolio Intelligence App — Knowledge Base
**Author:** Sansar Karki
**Created:** April 2026
**Status:** MVP Planning

---

# Table of Contents
1. [Ideal Customer Profile](#ideal-customer-profile)
2. [Problem Statement](#problem-statement)
3. [Value Proposition](#value-proposition)
4. [Market Map](#market-map)
5. [Product Requirements Document](#product-requirements-document)
6. [MVP Scope](#mvp-scope)
7. [Go-To-Market Strategy](#go-to-market-strategy)
8. [Pricing and Monetization](#pricing-and-monetization)

---

# Ideal Customer Profile

**Who they are**
Self-directed investors who pick individual stocks and hold them for 1–3 years. They have a real portfolio ($50k–$2M), a real thesis for each position, and a day job that limits how much time they can spend monitoring it.

**Demographics**
- Age 28–55
- Works in tech, finance, medicine, or engineering
- US-based, English-speaking
- Manages their own money — no advisor

**How they invest**
- Buys individual stocks, holds 3 quarters minimum
- Has a written or mental thesis for every position
- Tracks macro trends, reads earnings, follows sector news
- Not a day trader. Not a passive index investor.

**Their daily routine**
Every morning they open their brokerage, read the news, figure out what it means for their holdings, check their sizing, and mentally model their risk. It takes 45–60 minutes. Most days nothing changed.

**The core problem**
They spend an hour just to answer "am I still okay?" — and they have no system to tell them when the answer becomes no.

**What they're not**
- Day traders
- Beginners without a thesis
- Passive index investors
- Institutional funds

**Where to find them**
Reddit (r/stocks, r/investing, r/SecurityAnalysis), Seeking Alpha, finance Twitter/X, Substack newsletters, and investor Discord communities.

**The one sentence that captures them**
> "I don't want to be told what to buy. I want to know if what I already own is still safe to hold."

---

# Problem Statement

Self-directed investors who pick individual stocks have no reliable way to know when their risk profile changes.

They built a process to handle this — open the brokerage, read the news, connect it to their holdings, check position sizing, model the risk. It works. But it takes an hour every morning, requires full concentration, and falls apart the moment life gets busy. Miss a few days and you're flying blind.

The tools that exist don't solve this. Brokerage platforms show you what happened, not what it means for your specific book. Financial news apps are written for everyone, so they're useful to no one in particular. Portfolio trackers show allocation and performance but have no concept of risk changing in real time. General AI tools like ChatGPT can help you think through a position, but you have to do all the legwork yourself — pull the news, frame the question, interpret the output.

The result is that a serious investor with a $200k portfolio and a clear thesis for every position has roughly the same risk visibility as someone who checks their account once a month.

Three specific gaps drive this:

**News isn't filtered to their portfolio.** They read the same macro headlines as everyone else and have to manually figure out which ones actually affect them. A Fed rate decision might matter a lot or not at all depending on what they hold. Right now that translation is entirely on them.

**Risk isn't relative.** A growth stock with high volatility in a rate hike cycle is a different situation than a value stock with the same volatility. No existing tool understands the difference. They all treat risk as a single number regardless of what the position is or why you own it.

**There's no alert layer.** Nothing tells them when a position they haven't looked at in two weeks just became a problem. They find out when the damage is already done.

The investor who feels this most is not someone who's careless. It's the opposite — someone careful enough to have built a manual process, frustrated that it breaks down the moment they don't have an hour to spare.

---

# Value Proposition

Your portfolio's daily risk briefing — built around what you own, not the market at large.

---

**The core promise**

You built a thesis for every position you hold. We protect it. Every morning you get a clear picture of where your portfolio stands, what changed overnight, and whether anything needs your attention — without spending an hour figuring it out yourself.

---

**What makes it different**

Most tools tell you what the market did. This tells you what the market did *to you*.

News gets filtered down to the positions you actually own. Risk gets scored relative to what each position is — a growth stock in a rising rate environment gets judged differently than a value stock in the same environment. And when something shifts enough to matter, you hear about it before it becomes a problem.

---

**The three things it replaces**

| What you do today | What the app does instead |
|---|---|
| Read broad market news and manually connect it to your holdings | Filters news to only what affects your positions |
| Eyeball your allocation and mentally model your risk | Scores each position's downside risk in real time |
| Find out a position deteriorated when it's already too late | Alerts you the moment a position changes risk grade |

---

**What it is not**

It doesn't tell you what to buy. It doesn't predict stock prices. It doesn't manage your money. It's a risk monitoring layer that sits on top of the decisions you already make — and makes sure nothing slips through while you're living your life.

---

**One line**

> Know if what you own is still safe to hold. Without the hour.

---

# Market Map

## The landscape

The tools serious investors use today fall into four categories. None of them do what this product does.

---

**1. Brokerage platforms**
Fidelity, Schwab, Robinhood, IBKR

Show you performance, allocation, and order history. Built for execution, not analysis. They tell you what happened to your portfolio — not what it means or what to watch.

**2. Financial news and research**
Bloomberg, Seeking Alpha, Motley Fool, Benzinga

Written for a general audience. Covers the market, not your book. You still have to read it all and figure out what applies to you.

**3. Portfolio trackers and analytics**
Sharesight, Stock Events, Morningstar Portfolio, Yahoo Finance Portfolio

Track performance over time. Some show allocation and basic diversification. None assess risk dynamically or tie news events to your specific positions in real time.

**4. General AI tools**
ChatGPT, Claude, Perplexity

Can reason about a position if you frame the question well and bring your own context. Powerful but manual — no persistent knowledge of your portfolio, no proactive alerts, no daily cadence.

---

## Where this product sits

Every category above is reactive. You go to them. They don't come to you with something relevant.

This product is the only one that:
- Knows your specific holdings
- Monitors news continuously
- Filters it to what actually affects you
- Scores risk relative to what each position is
- Comes to you when something changes

That's a gap none of the four categories above fill — not because it's technically impossible, but because none of them were built with that as the core job.

---

## Competitive positioning

| | Knows your holdings | Filters news to you | Dynamic risk scoring | Proactive alerts | Thesis-aware |
|---|---|---|---|---|---|
| Brokerage | Yes | No | No | Price only | No |
| News/Research | No | No | No | No | No |
| Portfolio trackers | Yes | No | No | No | No |
| General AI | No | No | No | No | No |
| **This product** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

---

## The real competition

The honest answer is that the real competition right now is the investor's own morning routine. They've built a manual process that works well enough. The bar isn't beating another app — it's being better than 45 minutes of careful reading every morning.

That's a high bar. It's also a very winnable one.

---

# Product Requirements Document

**Product:** Portfolio intelligence app
**Version:** 1.0 MVP
**Author:** Sansar Karki
**Status:** Draft

---

## Purpose

A daily risk intelligence layer for self-directed long-term investors. The product monitors their holdings, filters market news to what's relevant, scores downside risk per position, and alerts them when something changes — so they don't have to spend an hour every morning figuring it out themselves.

---

## Users

Single user type at launch: the self-directed long-term investor. Defined in ICP document.

---

## Core user stories

**Portfolio setup**
- As a user I can connect my brokerage account or manually enter my holdings
- As a user I can see all my positions in one place with current price and allocation
- As a user I can tag each position with its archetype (growth, value, cyclical, defensive, small cap)

**Daily digest**
- As a user I receive a morning digest by push notification summarizing overnight changes
- As a user the digest only covers news that affects my actual holdings
- As a user the digest tells me which positions changed grade and why

**Risk dashboard**
- As a user I can see every position with its current risk grade (A through F)
- As a user I can see what's driving the grade for each position
- As a user I see an overall portfolio risk grade weighted by position size
- As a user I can tap any position to see its full detail view

**Position detail**
- As a user I can see a price chart for each holding
- As a user I can see the current risk score broken down by dimension
- As a user I can see the news that affected this position today
- As a user I can see the full AI analysis in plain English
- As a user I can see the methodology — why it got this score

**Alerts**
- As a user I get a push notification when any position changes risk grade
- As a user I get a push notification when my overall portfolio grade changes
- As a user I get a push notification when a major news event triggers deep analysis on one of my holdings

---

## System requirements

### News ingestion
- Pull from RSS feeds covering macro news and company-specific news
- Run continuously in the background
- Two parallel tracks: macro events and company-specific events
- Flag each news item with affected tickers where identifiable

### News classification

**Step 1 — Relevance filter**
- Check each news item against user's holdings
- Macro news: determine if it affects any held position by sector, rate sensitivity, geography, or theme
- Company news: match directly to ticker
- Discard if no holdings are affected

**Step 2 — Significance classification**
- Classify relevant news as major or minor
- Major triggers: earnings surprises, Fed decisions, geopolitical events with direct sector impact, regulatory actions, CEO changes, M&A
- Minor triggers: analyst rating changes, routine macro data, secondary news mentions

**Step 3 — Routing**
- Major events → MiroFish swarm analysis
- Minor events → lightweight agentic AI scan

### Risk scoring

Each position is scored 0–100 across five dimensions:

| Dimension | What it measures |
|---|---|
| News sentiment | Tone and severity of recent news affecting this position |
| Macro exposure | How sensitive this stock is to current macro conditions |
| Position sizing | Whether allocation is appropriate given current risk |
| Volatility trend | Whether volatility is rising, stable, or falling |
| Thesis integrity | Whether the original reason to own this is still intact |

Scoring is archetype-relative. The system classifies each position before scoring:

| Archetype | Baseline expectation | What moves the score |
|---|---|---|
| High growth | High volatility is normal, not penalized | Rate sensitivity, multiple compression, narrative breaks |
| Value | Low volatility expected | Earnings deterioration, sector rotation |
| Cyclical | Risk tied to macro cycle | GDP signals, commodity prices, consumer data |
| Small cap | Wide swings expected | Credit conditions, risk-off sentiment |
| Defensive | Minimal movement expected | Dividend cuts, defensive rotation breaking down |

**Grade thresholds**
- A = 80–100 (hold, thesis intact)
- B = 65–79 (watching, no action needed)
- C = 50–64 (caution, review position)
- D = 35–49 (deteriorating, consider trimming)
- F = 0–34 (alert, thesis may be broken)

Grades are time-sensitive. A position can move from B to D in one morning if the right event hits.

### Analysis pipeline

```
NEWS FEED (RSS + financial API)
        ↓
[Relevance filter] → discard if no holdings affected
        ↓
[Significance classifier] → major or minor
        ↓
    major               minor
      ↓                   ↓
[MiroFish swarm]    [Agentic AI scan]
        ↓                   ↓
         [Compiler AI]
    synthesizes all reports
        ↓               ↓
  Morning digest    Dashboard update
```

### MiroFish integration
- Self-hosted, not exposed as a service (AGPL compliance)
- Triggered only for major events
- Input: seed data = news item + affected position context + portfolio weighting
- Output: swarm prediction report on likely impact
- Output feeds into compiler AI alongside agentic scans

### Compiler AI
- Receives all swarm reports and agentic scans from the current cycle
- Produces one morning digest in plain English
- Updates risk scores for all affected positions
- Flags grade changes for alert system

---

## Dashboard screens

**Home**
- Overall portfolio grade, large and front and center
- Position cards: ticker, current price, grade, grade change indicator
- Top news strip filtered to holdings

**Position detail**
- Price chart
- Risk grade and score
- Score breakdown by dimension
- Today's relevant news
- Full AI analysis
- Methodology in plain English

**Alerts / notification center**
- Grade change history
- Major event log

---

## Non-requirements (MVP)

| Feature | Why it's cut |
|---|---|
| Brokerage API connection | Auth complexity delays launch |
| Web app | Mobile only at launch |
| MiroFish full deployment | Added in v2 once pipeline is proven |
| Multi-user accounts | One user type at launch |
| Price move alerts | Exists everywhere already |
| Thesis tracking over time | Post-MVP |
| Social features | No |
| International markets | US stocks only |
| Options or derivatives | Out of scope |

---

## Success metrics
- User opens digest 5 out of 7 mornings per week
- User reports digest replaced their manual morning routine
- Alert triggers rated as relevant, not noise
- Time to "am I okay" drops from 45 minutes to under 5

---

# MVP Scope

## The single question MVP answers

> "Did anything happen overnight that changes my risk on any position I hold?"

If a user opens the app every morning because the answer is reliably useful — the MVP worked.

---

## What's in

**Portfolio setup**
- Manual entry of holdings (ticker, shares, purchase price)
- Archetype tagging per position
- No brokerage connection at MVP

**News pipeline**
- RSS ingestion for macro and company news
- Relevance filter against holdings
- Significance classifier (major vs minor)
- Routing to MiroFish or agentic AI

**Risk scoring**
- All five dimensions scored per position
- Archetype-relative scoring logic
- A–F grade per position
- Overall portfolio grade weighted by position size

**Morning digest**
- Push notification at user-set time
- Plain English summary of overnight changes
- Flags which positions moved grade and why

**Dashboard**
- Overall portfolio grade front and center
- Position cards with ticker, grade, grade change arrow
- Top news strip for holdings

**Position detail**
- Price chart (Yahoo Finance API or similar)
- Current grade and score breakdown
- Today's relevant news
- AI analysis in plain English
- Methodology explanation

**Alerts**
- Push when any position changes grade
- Push when major event triggers analysis on a holding

---

## MiroFish in MVP

Cut for now. Replace with stronger agentic AI prompt for major events. Add MiroFish in v2 once the pipeline is proven and users are opening the app daily.

---

## Build order

| Week | Focus |
|---|---|
| 1–2 | Holdings input, archetype tagging, RSS ingestion, relevance filter |
| 3–4 | Significance classifier, agentic AI scan, risk scoring, grade calculation |
| 5–6 | Compiler AI, morning digest, push notifications, basic dashboard |
| 7–8 | Position detail, price chart, grade change alerts, internal testing |
| 9–10 | Polish, fix issues, onboard 3–5 people from personal circle |

---

## Definition of done

- You open it every morning and it replaces your manual routine
- At least 3 people outside your household use it daily for 2 weeks
- At least one of them says the digest caught something they would have missed

---

# Go-To-Market Strategy

## The core GTM principle

You don't need a marketing strategy yet. You need 10 people who can't imagine going back to their morning routine without it. Everything before that is distribution. Everything after that is growth.

---

## Phase 1 — Validation (Month 1–2)

**Who:** 5–10 people from your personal circle

Friends, family, anyone you know personally who invests in individual stocks. The bar isn't finding perfect ICP matches — it's finding people honest enough to tell you when something doesn't work.

Don't pitch them a product. Tell them you're building something for yourself and want to see if it solves a problem they have too. Ask if they'll use it daily for two weeks and give you real feedback.

**What you're measuring:**
- Do they open the digest daily?
- Do they find the grades useful or confusing?
- Did it catch anything they would have missed?
- What's the first thing they say when they describe it to someone else?

**What you're not doing:**
- No landing page yet
- No social content yet
- No pricing yet
- No outreach outside your circle

---

## Phase 2 — Warm expansion (Month 3–4)

**Who:** Reddit communities and finance Twitter/X

**Reddit**
- r/stocks, r/investing, r/SecurityAnalysis
- Post honest stories, not ads
- Engage in threads where people describe the exact problem you solve

**Finance Twitter/X**
- Document the build in public
- Share anonymized digest examples
- Chase replies from people who say "I need this"

**What you're measuring:**
- Waitlist signups
- Quality of inbound
- Questions people ask before signing up

---

## Phase 3 — Controlled launch (Month 5–6)

**Who:** Waitlist from Phase 2, opened in batches

**Positioning:**
Don't say: "AI-powered portfolio risk intelligence using swarm simulation"
Say: "Know if what you own is still safe to hold. Without the hour."

**Channels:**
- Reddit organic
- Finance Twitter/X
- Direct outreach to finance Substack writers

**What you're not doing:**
- No paid ads
- No Product Hunt yet
- No cold email

---

## Phase 4 — Growth (Month 7+)

- Product Hunt launch timed to a real milestone
- Simple referral loop for existing users
- Anonymized digest examples as content

---

## GTM summary

| Phase | Who | Goal |
|---|---|---|
| 1 — Validation | Personal circle | Prove daily habit |
| 2 — Warm expansion | Reddit + Finance Twitter | Build waitlist |
| 3 — Controlled launch | Waitlist batches | Find retention ceiling |
| 4 — Growth | Referral + content + Product Hunt | Scale what works |

---

# Pricing and Monetization

## When to start charging

After Phase 2. Specifically when:
- At least 20 users have used it daily for 4 consecutive weeks
- At least half say they'd miss it if it disappeared
- You have enough real language to write a pricing page

---

## Model: Freemium with a hard cap

**Free tier**
- Up to 5 holdings
- Daily digest
- A–F grade per position
- Top news per holding
- Grade change alerts

**Pro — $12/month or $99/year**
- Unlimited holdings
- Full score breakdown by dimension
- Position detail with methodology
- MiroFish deep analysis on major events
- Alert history and event log
- Priority analysis during high-volume news days

---

## Why this model

The free tier is genuinely useful for someone with a small portfolio. It proves the product works before asking for money. The people most likely to pay are those with more than 5 positions — exactly the ICP with $100k–$2M portfolios.

$12/month doesn't require budget approval. $99/year locks in annual commitment and reduces churn.

---

## What not to do

- Don't charge per alert or per analysis — usage-based pricing creates anxiety
- Don't build a team or enterprise tier at MVP
- Don't discount early — lifetime deals attract users who never use the product

---

## Revenue projection (conservative)

| Month | Free users | Pro users (20% conversion) | MRR |
|---|---|---|---|
| 6 | 200 | 40 | $480 |
| 9 | 500 | 100 | $1,200 |
| 12 | 1,500 | 300 | $3,600 |

---

## Long term

**Data partnerships** — Anonymized, aggregated signals about how retail investors respond to macro events is valuable to research firms. A v3 conversation.

**Institutional lite** — A $49/month tier for investors with larger portfolios who want more frequent analysis cycles and longer event history.

---

*End of knowledge base — Tech Architecture and Roadmap docs to be added.*
