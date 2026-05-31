# Clavix UI Vision

## Product Promise
Clavix should feel like a premium morning risk brief for serious self-directed investors: fast to scan, calm under pressure, and rigorous enough to trust. The app should answer what changed overnight in seconds, then let the user audit the reasoning without the interface collapsing into clutter.

## Intended User Experience
- The first open of the day should feel concise and authoritative, not busy.
- The user should understand the portfolio situation before drilling into any single name.
- Every important number should feel sourced, recent, and inspectable.
- The app should respect mobile attention: strong hierarchy first, depth on demand second.
- When data is incomplete, the interface should become more candid, not more vague.

## Visual Design Principles
- Institutional calm over fintech theater
  - Sharp geometry, disciplined spacing, restrained color, and minimal decorative motion.
- Evidence-led hierarchy
  - Grades, deltas, timestamps, and source cues should anchor the layout before prose does.
- Warm precision
  - Keep the cream/paper and burnt-orange direction only if it remains crisp, high-contrast, and rating-agency serious rather than lifestyle-soft.
- Mono where it earns trust
  - Use monospaced typography for grades, figures, deltas, and timestamps to reinforce auditability.
- One system, everywhere
  - The same rules for cards, rows, labels, state messaging, and empty/loading/error surfaces across all tabs.

## Information Hierarchy Principles
- Start broad, then narrow:
  - Portfolio
  - Sector
  - Position
  - Article / methodology evidence
- Use summary blocks to answer the immediate question, then route to denser evidence surfaces.
- Keep user actions obvious and rare. Most screens are for understanding, not fiddling.
- Separate “current state” from “supporting explanation” visually so the user never has to parse both at once.

## Screen-By-Screen Goals
- Welcome / Login
  - Explain the product before asking for work. Reduce auth anxiety and make the first action obvious.
- Onboarding / Add portfolio
  - Clarify what is available now versus later, especially around manual entry and limited coverage.
- Today
  - Become the cleanest, most valuable morning surface in the app. It should stand on its own in under 30 seconds.
- Holdings
  - Present the portfolio as a risk-weighted book, not just a list of positions.
- Search
  - Make discovery feel precise and fast, with confidence about tracked versus outside-universe coverage.
- Ticker detail
  - Serve as the trust center: current rating, recent change, main drivers, news evidence, methodology drill-down.
- Alerts
  - Help the user decide whether something deserves attention now, later, or not at all.
- Settings
  - Feel operational and trustworthy, with clean control groupings and no visual noise.

## What Should Feel Premium
- Typography rhythm and spacing discipline
- Clear, stable component vocabulary
- Crisp state transitions and skeleton loading
- Numerically literate presentation of ratings, deltas, and timestamps
- Methodology and evidence surfaces that feel like part of the product, not bolted-on help pages

## What Should Feel Trustworthy
- Honest limited-data states
- Explicit freshness/timestamp cues
- Consistent use of source labels, methodology language, and grade logic
- No overclaiming language, fake history, or vague AI flourish
- Strong contrast and readable density, especially for older investors on phones

## What Should Feel Fast
- Immediate top-of-screen summary on every primary tab
- Progressive disclosure instead of long default walls of content
- Lightweight motion used only for state change and navigation feedback
- Loading placeholders that preserve layout and reduce uncertainty

## Data That Must Never Be Faked
- Previous scores or deltas when true history is missing
- Confidence implied where data is thin or outside-universe
- Methodology precision that the backend does not actually provide
- Brokerage-related expectations that are out of current launch scope

## Handling Missing Or Limited Data
- Use a consistent limited-data component with plain-language explanation, scope, and consequence.
- Distinguish clearly between:
  - no holdings yet
  - no digest generated yet
  - tracked but thin coverage
  - outside-universe ticker
  - backend/network failure
- When a score or chart is absent, preserve structure and explain why instead of collapsing the UI into blanks.
- In evidence screens, prefer fewer real signals over fuller but speculative summaries.
- Cold-launch or timeout states should still land in a composed, usable shell that tells the user what is loading, what failed, and what remains trustworthy right now.
