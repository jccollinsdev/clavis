# Clavix UI Backlog

## Backend Data Needed
- Search trending needs a real activity feed or aggregate signal so the section can do more than explain its own absence.
- Search query reliability needs work: live `/tickers/search` could stall long enough to leave the user on a loading card without results.
- Ticker detail needs stronger resilience across `/tickers/{ticker}`, price history, score history, and methodology fetches so the screen does not sit on loading skeletons when only one downstream request is slow.
- Preferences loading needs reliability work: cold launches showed `/preferences` timing out, which can strand settings or other dependent surfaces in degraded/local-default states.

## Product Decisions Needed
- Decide whether Search should surface unsupported/outside-universe names directly in results or remain a tracked-universe-only lookup with explanatory copy.
- Decide how much alert triage should live in Alerts versus Today. Right now the alert tape is useful, but the canonical "what matters now" surface is still split between tabs.
- Decide whether version/build information should always be visible in Settings or hidden when bundle metadata is missing.

## UI Polish Later
- Today still needs a dedicated second pass once the existing user-owned `DigestView` work stabilizes; it remains the most important product surface.
- Settings file structure is still oversized. Splitting detail screens into separate files would make future polish safer and more maintainable.
- Add richer motion/state transitions once data-state contracts are more stable; right now the main UX win is clarity, not animation.

## Launch Blockers
- Fresh-install QA needs a stable demo/test account path so signed-in regression checks survive app reinstalls in Simulator.
- Timeout behavior on preferences/search/ticker detail is visible enough to undermine trust during launch-style QA if left unaddressed.

## Nice-To-Have Improvements
- Add a proper "coverage status" module on ticker detail that explains freshness, source depth, and thin-data conditions in one place.
- Promote a reusable trust/freshness strip into Today and Holdings so timestamps, coverage limits, and source scope are always easy to scan.
