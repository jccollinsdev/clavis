# Clavix V1 Final Roadmap

**Last updated:** 2026-04-19

## V1 Decisions Locked

- Brand name: `Clavix`
- UI source of truth: `design_handoff/`
- V1 includes brokerage sync via SnapTrade
- V1 includes paid Pro at `$25/mo`
- Email summaries are V2
- Advanced plan management is V2
- Institutional/data products are V2
- Shared ticker analysis is trusted enough to keep as the product foundation

## Phase 0 - Scope Lock

Goal: remove ambiguity before coding.

1. Freeze the v1 product contract and terminology.
2. Map every design-handoff screen to a real iOS screen or route.
3. Define the backend payloads needed for Home, Holdings, Digest, Alerts, News, Article, Ticker, and Settings.
4. Write the News feed endpoint plan before implementation because there is no existing route to extend.

Exit criteria:
- one product name
- one UI source of truth
- one list of V1 features
- one backend surface plan for news/articles

## Phase 1 - Trust And Release Safety

1. Keep security hardening active.
2. Keep legal/trust pages aligned with the product language.
3. Ensure launch copy never drifts into advice language.
4. Keep monitoring, backup, and recovery requirements in view.

Exit criteria:
- public trust surface is consistent
- no hidden/internal surfaces are exposed

## Phase 2 - Shared Intelligence Foundation

1. Keep shared ticker analysis as the canonical source.
2. Confirm the ticker cache and digest pipeline remain stable enough for daily use.
3. Make sure alert fanout and digest synthesis stay aligned with shared ticker data.
4. Decide which legacy surfaces remain active only for compatibility.

Exit criteria:
- shared ticker data is stable enough to power the redesigned UI

## Phase 3 - iOS V1 UI Rebuild

Build the app to match the handoff, not the current MVP shell.

1. Replace the top-level shell with the handoff navigation model.
2. Implement the custom tab bar and per-tab stacks.
3. Rebuild onboarding to the handoff flow.
4. Rebuild Home, Holdings, Digest, Alerts, Settings.
5. Add News and Article Detail screens.
6. Rework Ticker Detail to the handoff spec.
7. Add loading, empty, error, accessibility, and persistence behavior.

Exit criteria:
- the iPhone app feels like the design handoff in real use

## Phase 4 - Backend/API Surface For The New UI

1. Define and add the News feed endpoint.
2. Define and add Article Detail support.
3. Expand Home/Dashboard payloads for counts, state, and next-run context.
4. Expand Ticker Detail payloads for the handoff fields.
5. Expand Preferences for the new settings and onboarding contract.
6. Add any missing model fields needed for the new UI states.

### News Feed Plan

Because the route does not exist yet, the plan is:

1. Add a dedicated `GET /news` route.
2. Source it from the existing news caches and ticker intelligence tables.
3. Return a grouped portfolio news feed suitable for the News tab.
4. Include enough metadata for the hero card, story cards, and filters.
5. Add a companion article detail route, likely `GET /news/{id}` or `GET /articles/{id}`.
6. Make article payloads include body, impact, factored state, grade context, source, timestamps, and ticker links.

Exit criteria:
- every V1 UI screen has a stable backend contract

## V1 Launch Gates After Phase 4

1. SnapTrade brokerage sync implemented and verified.
2. Pro plan purchase flow implemented and verified at `$25/mo`.
3. App Store metadata, screenshots, and reviewer notes ready.
4. Production deployment path verified on the Mac mini until VPS cutover is enabled.
5. Final QA pass across fresh install, no network, notifications, and account isolation.

## Deferred To V2

- Email summaries
- Advanced plan management
- Institutional/data features
- Any non-essential analytics expansions beyond the V1 handoff
