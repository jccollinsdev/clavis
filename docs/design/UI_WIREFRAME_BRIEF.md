# Clavis UI Wireframe Brief

## Purpose

This document is the wireframe brief for Clavis. It captures:

- the pages and features that already exist
- the pages and features we want next
- the content hierarchy for each screen
- the key states a wireframe should account for

Clavis is a portfolio risk intelligence app, not an adviser. Every screen should feel informative, calm, and precise.

---

## Product Summary

Clavis helps a self-directed investor answer three questions:

1. What is my portfolio risk right now?
2. What changed since the last review?
3. What should I look at first?

The UI should emphasize:

- portfolio-grade risk summaries
- ticker-level evidence and news
- fast review of holdings, digest, and alerts
- clear freshness and confidence context

---

## Current Feature Inventory

### Already in the app

- auth gate and onboarding flow
- Home / Dashboard
- Holdings list
- Digest page
- Alerts page
- Settings page
- ticker search and add-position flows
- ticker detail page
- watchlist actions
- refresh and analysis trigger actions
- digest, alert, and ticker freshness labels
- score disclaimers and risk-grade copy

### Already supported in data

- shared ticker cache and search
- holdings, positions, and watchlist data
- portfolio digest generation
- alert generation from score changes and major events
- news ingestion and article resolution
- risk grades, rationale, and factor breakdowns
- daily refresh / analysis pipeline

### Wanted next

- a stronger Home page focused on triage
- a Holdings page with a clear search bar and faster add flow
- a dedicated News page or feed surface
- better empty, loading, and error states
- more native iOS navigation patterns
- stronger filter/sort/search patterns
- cleaner notification and deep-link behavior
- legal/public trust pages aligned across app and web

---

## Global Wireframe Rules

- dark, precise, professional visual language
- use one strong accent color sparingly
- show grade, score, and freshness anywhere a score appears
- keep primary actions visible near the top
- avoid clutter; show a few high-signal items first
- every list row should have a clear reason to exist
- show empty states that explain what to do next

---

## App Navigation

### Primary tabs

1. Home
2. Holdings
3. Digest
4. Alerts
5. Settings

### Secondary surfaces

- ticker detail
- ticker search
- add position flow
- onboarding flow
- future News surface

---

## Page 1: Home

### Goal

Make Home the fastest triage surface. It should answer: how risky is the portfolio, what changed, and what needs attention now.

### Current content

- top action bar
- refresh
- run analysis
- tab shortcuts
- hero portfolio summary
- snapshot card
- needs attention list
- since-last-review summary
- digest preview card

### Wireframe should include

- portfolio grade and score block
- short one-line portfolio summary
- freshness timestamp
- current analysis status if a run is active
- ranked attention queue
- key change summary since last review
- morning digest teaser
- quick actions

### Suggested sections

1. Portfolio overview
2. Priority queue
3. What changed since last review
4. Morning focus
5. Quick actions

### Key actions

- refresh data
- run fresh analysis
- open holdings
- open digest
- open alerts

### Empty state

- if there are no holdings, show a simple getting-started panel
- primary CTA should be add first position

### Loading state

- show a single strong loading card before the content stack

---

## Page 2: Holdings

### Goal

Let the user review positions, search tickers, add holdings, and move into ticker detail quickly.

### Current content

- holdings overview card
- watchlist section
- needs review section
- ranked holdings list
- add position sheet
- ticker search sheet
- delete position actions
- long-press / context-menu delete

### Wireframe should include

- a visible search bar at the top of the page
- add position button
- refresh button
- a summary card for total positions and risk status
- watchlist preview
- holdings sorted by risk or concern
- a clear needs-review grouping for risky names

### Search bar behavior

- search ticker symbol or company name
- show matching supported tickers
- allow quick navigation to ticker detail
- allow add-to-watchlist or add-to-holdings actions from search results

### Suggested sections

1. Search / add bar
2. Holdings summary
3. Watchlist
4. Needs review
5. All holdings list

### Row content

Each holding row should show:

- ticker
- company name
- grade
- score
- trend indicator
- short reason for concern or confidence
- current price context if useful

### Interactions

- tap row opens position detail
- long press or context menu shows delete / manage actions
- search result can add to holdings or watchlist

### Empty state

- explain that no positions exist yet
- offer add-position and search actions

### Desired improvements

- make destructive actions safer and clearer
- reduce friction for add position
- keep watchlist and holdings visually distinct

---

## Page 3: Digest

### Goal

Present the daily portfolio narrative in a readable, scannable format.

### Current content

- digest status / run state
- score summary
- lead summary
- macro section
- sector overview
- position impacts
- what to do section
- holdings section
- full narrative

### Wireframe should include

- digest headline
- generated time / freshness
- grade and score summary
- 1-sentence risk note
- main market or portfolio driver
- section-by-section breakdown
- clear “what changed” and “what matters today” framing

### Suggested sections

1. Summary header
2. Score overview
3. Key drivers
4. Macro context
5. Sector context
6. Position impacts
7. Important actions / notes
8. Full narrative

### Content rules

- show only the most important items above the fold
- keep long narrative collapsed until expanded
- make the digest usable even when no new digest exists

### Empty state

- explain that the digest has not been generated yet
- offer a run-digest action

### Loading and error states

- loading should mention that the latest morning summary is being fetched
- errors should allow retry
- timeouts should explain that generation is still in progress

---

## Page 4: Alerts

### Goal

Show what changed in the portfolio and what requires attention, grouped clearly by severity.

### Current content

- alert refresh
- severity summary
- grouped alert cards
- empty state

### Wireframe should include

- a severity summary at the top
- grouped alerts by type
- timestamp for each alert
- short message explaining why it matters

### Suggested sections

1. Severity summary
2. Recent alerts grouped by type
3. Empty state / no recent alerts

### Alert row content

Each alert card should show:

- alert type
- grade change or event label
- affected ticker or portfolio item
- short explanation
- time received

### Desired improvements

- better visual differentiation between grade changes and major events
- easier scanning for the most urgent alerts
- future deep links into ticker detail or digest context

---

## Page 5: News

### Goal

Create a dedicated place to review relevant news without forcing the user to hunt inside ticker detail.

### Current state

- news already exists inside ticker detail and the backend pipeline
- digest and alerts already consume news-derived analysis
- there is no dedicated news-first page yet

### Wireframe should include

- a top-level news feed
- filters for portfolio, watchlist, market, and major events
- grouped stories by ticker and theme
- relevance labels
- source and freshness metadata

### Suggested sections

1. News headline summary
2. Filter bar
3. Top relevant stories
4. Market / sector stories
5. Ticker-specific stories

### Story card content

- headline
- source
- ticker or theme
- short summary
- evidence quality or confidence label
- timestamp

### Desired behavior

- allow opening story detail
- allow jumping from story to ticker detail
- show why the story matters to the portfolio

### Empty state

- explain that there are no relevant stories yet
- suggest checking watchlist or adding holdings

---

## Page 6: Ticker Detail

### Goal

Give a full view of one ticker: price, risk, rationale, evidence, news, and alerts.

### Current content

- risk hero
- price and trend section
- snapshot grid for held names
- fundamentals card
- AI score rationale
- what to watch section
- risk dimensions
- relevant news section
- recent alerts section
- recent news section
- watchlist toggle
- refresh action for paid users

### Wireframe should include

- ticker title and watchlist control
- grade and score hero
- price chart or trend area
- snapshot / fundamentals block
- risk rationale block
- key factors / dimensions
- recent news and alerts

### Suggested sections

1. Hero summary
2. Price / trend
3. Snapshot and fundamentals
4. Risk rationale
5. What to watch
6. News
7. Alerts

### Desired improvements

- make evidence quality more obvious
- make the difference between structural and AI-driven analysis clear
- support quick jump back to holdings or news

---

## Page 7: Settings

### Goal

Let the user control preferences, notifications, and trust-related app settings.

### Current content

- digest settings
- alerts settings
- brand section
- app state / preference controls

### Wireframe should include

- digest preferences
- alert preferences
- notification controls
- account / session actions
- app info and brand info

### Desired improvements

- clearer section grouping
- simpler language for each preference
- visible explanation of what each toggle changes

---

## Page 8: Onboarding

### Goal

Help a new user understand the product, give basic setup, and complete required acknowledgement steps.

### Current flow

- welcome
- name and DOB
- risk acknowledgement
- notification permission

### Wireframe should include

- short intro per step
- progress indicator
- one primary action per screen
- ability to continue later where appropriate

### Desired improvements

- reduce accidental bypass behavior
- make permission prompts status-aware
- keep the risk framing clear and non-advisory

---

## Key Cross-Page Features

### Search

- search should exist in holdings and ticker-related flows
- search should support symbol and company name
- results should lead to detail, add, or watchlist actions

### Refresh / analysis

- Home, Holdings, Digest, and Alerts should have refresh behavior
- users should see when a run is active

### Freshness

- every score surface needs freshness context
- timestamps should be visible wherever grades or scores appear

### Disclaimers

- keep informational language consistent
- avoid advice-style phrasing
- make limited-confidence results look limited, not certain

### Empty states

- no holdings
- no alerts
- no digest
- no news

Each empty state should explain what the user can do next.

---

## Wireframe Priority Order

1. Home
2. Holdings
3. Digest
4. Alerts
5. News
6. Ticker Detail
7. Settings
8. Onboarding

---

## Notes For Visual Design

- keep the app dark and premium
- use cards, not dense tables, for most mobile content
- reserve color for grades, alerts, and CTA states
- make the Home page the most editorial and the Holdings page the most operational
- make News feel like a feed, not a second digest

---

## Open Items

- decide whether News becomes a full tab or a section inside ticker detail and digest
- decide whether holdings search should be a visible page search bar or a dedicated modal plus page action
- decide how much of the digest should be collapsed by default
- decide whether settings should include trust / legal links directly
