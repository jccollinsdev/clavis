# Clavis Dashboard Implementation Spec

## Goal

Make the dashboard the app's primary triage surface: fast to scan, focused on risk changes, and opinionated about what needs attention now.

The dashboard should answer three questions immediately:

1. How risky is the portfolio right now?
2. What changed since the last review?
3. What should I look at first?

## Current State

The current dashboard in `ios/Clavis/Views/Dashboard/DashboardView.swift` shows:

- portfolio grade and score
- a short portfolio summary
- a top-3 "Needs Attention" list
- a simple "Since Last Review" count row
- a digest preview card

The app already has richer data than the dashboard uses:

- `Position.riskTrend`, `previousGrade`, `totalScore`, and summaries
- `Digest.structuredSections` with major events, watch list, and portfolio advice
- `Alert` types for grade changes, major events, portfolio-grade changes, concentration danger, cluster risk, macro shock, and structural fragility
- backend portfolio risk output with concentration, cluster, correlation, liquidity, and macro-stack risk

## Product Principles

- Lead with urgency, not completeness.
- Show portfolio-level risk before individual names.
- Show concrete changes, not just counts.
- Keep the dashboard useful when there is no fresh digest.
- Every card should support a next action.

## Proposed Dashboard Structure

### 1. Portfolio Overview

Replace the current single status card with a stronger overview block:

- portfolio grade
- portfolio score
- risk state label
- freshness timestamp
- current analysis status

Display copy should make the state actionable, for example:

- `Stable, but 2 names are deteriorating`
- `Analysis is still running`
- `Updated 7:42 AM`

### 2. Priority Queue

Add a ranked list of holdings that deserve attention now.

Each row should show:

- ticker
- grade and trend
- short reason for surfacing
- action pressure label

Suggested ordering:

- grade deterioration
- F or D grades
- major event coverage
- concentration or macro exposure

### 3. Portfolio Construction Risk

Add a dedicated card for portfolio-level fragility.

Surface:

- allocation risk score
- concentration risk
- cluster risk
- correlation risk
- liquidity mismatch
- macro-stack risk

Show top 1 to 3 drivers only.

This is the highest-value missing dashboard element because the backend already computes it in `backend/app/pipeline/portfolio_risk.py`.

### 4. What Changed

Replace the current count-only row with a change feed.

Show items like:

- `AAPL: B -> C`
- `TSLA: major event detected`
- `Portfolio grade changed from B to C`

Use alert types and digest sections together so the dashboard reports actual changes, not abstract totals.

### 5. Morning Focus

Add a digest-derived briefing card with:

- one-line portfolio summary
- 2 to 3 items that matter today
- 1 to 3 action items

This should be a compressed version of `Digest.structuredSections`.

### 6. Quick Actions

Expose primary actions directly from the dashboard:

- Run fresh analysis
- Open digest
- View alerts
- Add position

## Data Contract Changes

### Backend

Extend `/digest` or add a dedicated dashboard endpoint so the app can fetch a dashboard-ready payload.

Recommended payload additions:

- `portfolio_risk_summary`
- `top_risk_drivers`
- `danger_clusters`
- `freshness`
- `change_summary`
- `priority_holdings`
- `analysis_run`

The current digest route returns digest content and analysis-run context, but not the portfolio-risk breakdown.

### iOS models

Add lightweight models for:

- dashboard risk summary
- dashboard change item
- dashboard action item

Keep them separate from the existing digest and alert models unless the API shape stays unchanged.

## UI Behavior

### Loading

- Show the overview card first.
- Skeleton-load the priority queue and risk cards.
- Do not leave the screen empty while digest data is missing.

### Empty state

If there are no holdings:

- explain the app value in one sentence
- show `Add Position`

### Error handling

- show partial results when only one data source fails
- keep old digest data visible when refresh fails
- make retry available from the error state

## Acceptance Criteria

- Dashboard shows portfolio grade, score, freshness, and analysis status.
- Dashboard shows a ranked attention list with reasons, not just positions.
- Dashboard surfaces portfolio allocation risk and at least 1 top driver.
- Dashboard includes a change feed for actual grade/event changes.
- Dashboard includes a digest-derived morning focus section.
- Dashboard offers quick actions without requiring tab changes.
- Dashboard remains useful even when the latest digest is unavailable.

## Rollout Plan

### Phase 1

- Rework the overview card.
- Add quick actions.
- Upgrade the change row to a change feed.

### Phase 2

- Add portfolio-risk summary to the backend response.
- Surface concentration, cluster, and macro drivers.

### Phase 3

- Add the morning focus card.
- Refine ranking logic for the priority queue.
- Add better empty and partial-data states.

## Non-Goals

- Rebuilding the holdings tab.
- Replacing the digest screen.
- Adding charts before the decision surface is improved.

## Open Questions

- Should the dashboard fetch a new dedicated endpoint, or should `/digest` be expanded?
- Should the priority queue be driven by alert types, score deltas, or both?
- Should portfolio-risk details be summary-only or expandable inline?

## Next Step

Implement the dashboard payload shape first, then update the SwiftUI view to render the new sections.
