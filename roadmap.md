# Clavis — 7 Day Build Plan

**Goal:** Working app on your phone by Day 7. Real holdings, real news, real grades, real digest.

**APNs:** Deferred to v2. In-app polling only.

---

## Day 1 — Environment & API Keys

Get every external dependency unblocked before writing a single line of pipeline logic.

### Backend .env — get all four keys

- **MiniMax API key** — everything AI depends on this, do it first
- **Finnhub API key** — free tier, instant signup
- **Polygon.io API key** — free tier, instant signup
- **Supabase URL + service role key + JWT secret** — already in your Supabase project settings

### Verify each one works in isolation

- Hit Finnhub's `/news` endpoint manually with curl, confirm real news comes back
- Hit Polygon.io's `/v2/aggs` endpoint manually, confirm real price data comes back
- Send one test completion to MiniMax API, confirm response comes back correctly

### Supabase

- Run the corrected SQL schema (with the three bug fixes: `auth.users` typo, unique RLS policy names, `risk_scores` RLS join through `positions`)
- Confirm all six tables exist and RLS is enabled
- Add `reasoning TEXT` and `mirofish_used BOOLEAN` to `risk_scores`

### MiroFish bypass

- Open `pipeline/mirofish_analyze.py`
- Replace the implementation with a pass-through that logs a warning and returns `None`
- All major events will route to `agentic_scan` instead — confirm this in `classifier.py`

### End of Day 1 check

All four API keys return real data. Schema is deployed. MiroFish is bypassed. Nothing is blocked.

---

## Day 2 — News Pipeline

Build and verify the first half of the pipeline — from raw news to classified events.

### RSS + Finnhub ingestion

- Confirm `rss_ingest.py` pulls from at least 3 macro RSS feeds (Reuters, Bloomberg, WSJ)
- Confirm `finnhub_news.py` pulls company-specific news by ticker
- Both should return a normalized news item format — same shape regardless of source

### Relevance filter

- Feed 10 real news items through `relevance.py` with 3-5 test tickers
- Confirm it correctly discards items with no holdings match
- Confirm it correctly flags which ticker is affected for items that match
- Check edge cases — Fed rate decision should match rate-sensitive holdings, not just exact ticker mentions

### Significance classifier

- Send 5 relevant news items through `classifier.py` (MiniMax)
- Confirm it returns `major` or `minor` correctly
- Confirm it returns structured JSON — if MiniMax returns free text instead, fix the prompt now
- Test with one obvious major event (earnings miss) and one obvious minor one (analyst upgrade)
- **Validate this before end of day — classifier errors propagate to every stage downstream**

### End of Day 2 check

Real news flows from ingestion → relevance filter → classifier and comes out the other end with the right shape. Log every step so you can see exactly what's happening.

---

## Day 3 — Analysis & Scoring

Build and verify the second half of the pipeline — from classified events to grades.

### Agentic scan

- Send one minor event through `agentic_scan.py` with a real position context
- Confirm it returns a useful impact assessment in plain English
- If output is vague or generic, tighten the system prompt — give it the archetype, the ticker, the allocation size

### Risk scorer

- Send one agentic scan output through `risk_scorer.py`
- Confirm it returns all five dimension scores plus a final A–F grade
- Confirm it returns plain English reasoning for the methodology screen
- Test across two archetypes — a growth stock and a value stock with the same news item should produce different scores
- If grades feel wrong, tune the system prompt now before connecting everything

### Compiler AI

- Send two or three risk score outputs through `compiler.py`
- Confirm it produces one coherent morning digest in plain English
- Digest should mention which positions changed and why — not just list grades

### End of Day 3 check

A news item goes in one end. A grade and a plain English analysis come out the other. Each stage logs its output so you can trace failures.

---

## Day 4 — Full Pipeline End to End

Connect every stage and fire the whole thing with real data.

### Wire /trigger-analysis endpoint

Calling this should kick off the full pipeline for a given user:

```
RSS + Finnhub → relevance → classifier → agentic scan → risk scorer → compiler → writes to Supabase
```

### Run with 5 real holdings

- Add 5 positions across different archetypes in Supabase directly (no iOS yet)
- Hit `/trigger-analysis` manually
- Watch the logs — confirm every stage fires in sequence
- Check Supabase after — `risk_scores`, `news_items`, `digests` tables should all have new rows

### Verify /digest endpoint

- Call it and confirm it returns today's compiled digest from Supabase
- Confirm it returns current grade per position

### Verify /positions/:id endpoint

- Call it and confirm it returns score breakdown, news items, and reasoning for a specific position

### Debug systematically

If something breaks, don't debug the whole pipeline at once. Comment out everything after the failing stage and fix it in isolation. Then reconnect.

### End of Day 4 check

Full pipeline fires on demand. Supabase has real data in every table. All three endpoints return correct data.

---

## Day 5 — iOS Integration & Price Charts

Connect the iOS app to the real backend.

### Price charts

- Wire Polygon.io into `PositionDetailView.swift` — replace mock chart with real data
- Dashboard position cards — show real current price from Polygon.io
- Keep it simple — daily close prices are fine for MVP, no need for real-time tick data

### Backend integration

- `APIService.swift` — confirm it attaches JWT correctly to every request
- `DigestViewModel.swift` — calls `/digest`, renders real content
- `DashboardViewModel.swift` — calls `/positions`, renders real grades and prices
- `PositionDetailView.swift` — calls `/positions/:id`, renders score breakdown and news

### In-app polling (replaces APNs)

- On app open, check if today's digest exists in Supabase
- If yes, show it immediately
- If no, show "Your digest is being prepared" and poll every 60 seconds
- Also check `user_preferences.last_digest_at` on app open — if a digest was already written before the user opened the app, show it without waiting for a poll cycle

### End of Day 5 check

Open the iOS app. See real prices. See real grades. Tap a position and see real analysis. The app is talking to the real backend.

---

## Day 6 — Scheduler & Polish

Make the pipeline run automatically every morning.

### Scheduler

- `scheduler.py` — APScheduler fires the pipeline once per day per user at their set digest time
- Default to 7am if no preference is set
- Test by temporarily setting your digest time to 2 minutes from now and confirming the pipeline fires automatically

### Settings screen

- Digest time picker works and persists to Supabase `user_preferences`
- Notifications toggle exists but does nothing for now — label it "coming soon" or hide it entirely

### Polish

- Grade change arrows on dashboard position cards (up/down/same vs yesterday's grade)
- Archetype selection in `AddPositionSheet` — confirm dropdown matches PRD exactly: growth, value, cyclical, defensive, small cap
- Empty states — what does the app show if no holdings are added yet?
- Error states — what does the app show if the backend is down?

### End of Day 6 check

Scheduler fires automatically. Settings persist. App handles empty and error states gracefully.

---

## Day 7 — Dogfood

Load your real portfolio and live with it for a day.

### Morning

- Add your actual holdings — real tickers, real shares, real purchase prices, correct archetypes
- Trigger analysis manually once to generate your first real digest
- Read it. Does it make sense? Does it reflect what actually happened in the market?

### Grade sanity check

- Do the grades feel right given what you know about each position?
- If AAPL gets an F on a green day, the scoring prompt needs tuning
- If everything comes back a B regardless of news, the classifier isn't routing correctly
- Tune prompts until grades feel honest

### Digest quality check

- Is it written in plain English a non-technical investor would understand?
- Does it tell you something you didn't already know?
- Would you read it every morning?

### Fix what breaks

Day 7 is debugging and tuning, not building. Something will be wrong. That's what today is for. Budget 2-3 hours specifically for prompt tuning.

### End of Day 7 check — the only one that matters

You open the app. The digest tells you what changed overnight for your real holdings. Each position has a grade that makes sense. You didn't need to open anything else to know your portfolio status.

**If that's true, the MVP worked.**

---

## What's Not in This Plan

### Deferred — APNs push notifications
### Deferred — Onboarding first testers
### v2 — MiroFish swarm analysis
### v2 — Brokerage API connection
### v2 — Web app
### v2 — Multi-user

---

## Risk Table

| Risk | Mitigation |
|------|------------|
| MiniMax returns malformed JSON | Fix classifier and scorer prompts on Day 3 before connecting pipeline |
| Pipeline too slow to run on demand | Add async throughout Day 4 — each stage should not block the next |
| Grades feel wrong | Budget 2-3 hours on Day 7 just for prompt tuning |
| Polygon.io free tier rate limits | Cache price data per ticker — one fetch per day is enough for MVP |
