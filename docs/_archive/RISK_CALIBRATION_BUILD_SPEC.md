# Clavis Risk Calibration Build Spec

## Goal

Turn Clavis from an event-reactive portfolio analyzer into a calibrated safety engine.

The backend should answer two separate questions:

1. How safe is this asset on its own?
2. How much portfolio risk is the user taking by holding it this way?

The system must produce a stable safety score even on quiet days, and it must not let one headline dominate a structurally unsafe or structurally safe name without explicit evidence.

---

## Core Product Terms

Use these terms consistently across backend code, database fields, prompts, and API responses:

- `safety_score`
- `confidence`
- `structural_base_score`
- `macro_adjustment`
- `event_adjustment`
- `portfolio_allocation_risk`
- `structural_fragility`
- `liquidity_risk`
- `macro_sensitivity`
- `safety_deterioration`

Retire or minimize these older terms:

- `thesis_integrity`
- `position_sizing` as an asset score dimension
- `risk grade` when it implies the old event-analysis framing
- `event analysis`
- `methodology`
- `major/minor analysis` except where needed for internal event handling

---

## Score Hierarchy

The final asset safety score must be a weighted composition with explicit dominance rules.

### Recommended hierarchy

- `structural_base_score`: 70 to 90 percent weight
- `macro_adjustment`: 10 to 25 percent weight
- `event_adjustment`: 0 to 20 percent weight

### Hard rules

- Structural score dominates by default.
- Macro can move the score meaningfully, but not usually more than a structural band.
- Event impact is capped unless the event is clearly severe and durable.
- Quiet days must still produce a score from the structural base alone.

### Suggested formula

```text
raw_safety =
  structural_base_score
  + macro_adjustment
  + event_adjustment

final_safety_score = clamp(0, 100, normalized(raw_safety))
```

Recommended default caps:

- structural score: 0 to 100
- macro adjustment: -15 to +15
- event adjustment: -20 to +5

These are starting values, not final truth. They should be tuned after backtesting.

---

## Asset Safety Model

This is the score for the asset itself, independent of how much the user owns.

### Structural factors

Use deterministic logic for the base score. The LLM may explain, but it must not be the primary decision-maker.

#### 1. Market cap

Use bucket-based safety bands.

Example starting bands:

- `>$500B`: very high safety contribution
- `$50B-$500B`: high
- `$10B-$50B`: moderate-high
- `$2B-$10B`: moderate
- `$500M-$2B`: low-moderate
- `$100M-$500M`: low
- `<$100M`: very low

Market cap should mainly influence:

- base safety
- confidence
- maximum possible score ceiling for very small names

#### 2. Liquidity / market structure

Use at least:

- average daily dollar volume
- float if available
- spread proxy
- listing tier / exchange quality

Suggested liquidity penalties:

- extremely low dollar volume: strong penalty
- wide spread proxy: penalty
- low float: penalty
- OTC / poor listing quality: strong penalty

#### 3. Volatility regime

Use realized volatility or another robust proxy.

Suggested penalty logic:

- low volatility: small or no penalty
- moderate volatility: mild penalty
- high volatility: moderate penalty
- extreme volatility: strong penalty

#### 4. Leverage / balance-sheet fragility

Use explicit leverage and solvency signals when available.

Suggested penalties:

- low leverage, good coverage: positive or neutral
- moderate leverage: mild penalty
- high leverage / weak coverage: strong penalty

#### 5. Profitability quality

Use profitability and cash-generation as structural supports.

Suggested boosts:

- consistently profitable: score support
- mixed profitability: neutral to mild penalty
- persistent losses / weak cash generation: penalty

#### 6. Sector / cyclicality

Sector should affect both base score and macro sensitivity.

Suggested mapping:

- defensive sectors: safer baseline
- cyclicals: more macro-sensitive
- biotech / speculative software / tiny caps: lower baseline and lower confidence

#### 7. Asset class awareness

The system should know when a security behaves like:

- Treasury / Treasury ETF
- large-cap equity
- mid-cap equity
- small-cap equity
- ADR / cross-listed name
- biotech / binary catalyst name
- penny stock / microcap

This is necessary if `100` is truly meant to be Treasury-like safety.

### Structural score implementation

Do this in code using explicit rules:

- map each factor to a numeric contribution
- sum the contributions
- clamp to a valid range
- store the factor breakdown

Do not rely on the LLM to infer the base score from prose.

---

## Macro Regime Model

Macro is a separate medium-moving adjustment layer.

### Regime computation

Use deterministic rules first. LLM may assist with labeling, but should not decide the regime alone.

Recommended regime states:

- `risk_on`
- `risk_off`
- `rates_up`
- `rates_down`
- `credit_tightening`
- `credit_easing`
- `inflation_shock`
- `commodity_shock`
- `recession_pressure`
- `expansion_supportive`

### Regime inputs

Use a rule-based signal set built from available macro data and heuristics.

Possible inputs:

- rates trend
- credit spread trend
- broad market volatility
- commodity shock flags
- inflation pressure
- recession indicators

### Asset sensitivity map

Each asset should carry sensitivity tags such as:

- duration sensitivity
- consumer sensitivity
- commodity sensitivity
- credit sensitivity
- regulatory sensitivity
- growth sensitivity
- cyclicality

### Macro impact limits

Macro should generally:

- move large-cap stable names less
- move cyclicals and levered names more
- change slowly unless regime itself changes

Recommended cap:

- most names: `-10` to `+10`
- highly sensitive names: `-15` to `+15`

Macro should never be a vague catch-all. It must be explainable and bounded.

---

## Event Adjustment Model

Events should modify the score only when they meaningfully change safety.

### Event significance definition

An event is significant if it changes one of these:

- durability of the business
- structural fragility
- liquidity / financing access
- macro exposure
- regulatory survivability

### Event scoring rules

Each event should receive:

- `event_significance`
- `event_direction`
- `event_duration`
- `event_confidence`
- `event_adjustment`

### Event caps

Default event impact should be small.

Suggested cap:

- minor event: `0` to `-3`
- moderate event: `-3` to `-8`
- major event: `-8` to `-20`

The cap can be broken only when:

- the event is clearly company-specific
- the effect is durable
- there is strong supporting evidence

### Event decay

Event impact should decay over time unless reinforced by new evidence.

Suggested behavior:

- same-day or fresh event: full effect
- 2 to 5 days old: partial decay
- 1 to 2 weeks old: mostly decayed unless repeated

---

## Confidence Model

Confidence must be first-class.

### Confidence inputs

Confidence should increase with:

- richer structured data
- high liquidity / stable coverage
- multiple corroborating signals
- consistent regime and event inputs

Confidence should decrease with:

- thin data
- microcaps
- sparse news
- conflicting signals
- sparse financials

### Required outputs

Every asset score should store:

- `safety_score`
- `confidence`

Suggested confidence scale:

- `0.80-1.00`: high confidence
- `0.55-0.79`: medium confidence
- `<0.55`: low confidence

Low confidence should not block scoring, but it should be visible in the API and UI.

---

## Stability Constraints

Trust depends on score stability.

### Required rules

- max daily move cap unless a major event occurs
- smoothing window for short-term noise
- reject implausible jumps without supporting evidence
- enforce consistency bands by asset class

### Suggested starting rules

- large-cap stable names: daily move cap of `5-8` points
- mid-cap names: `8-12` points
- small-cap / microcap names: `12-20` points

If the event layer is weak, the score should not whip around.

### Noise rejection

If the new signal set only slightly differs from the prior state:

- preserve most of the previous structural score
- apply only a small delta

---

## Portfolio Risk Model

Portfolio risk is not an average of asset safety scores.

### Required dimensions

- concentration risk
- clustering risk
- correlation risk
- liquidity mismatch
- regime stacking

### What it should answer

- Is the portfolio too concentrated in a few names?
- Are multiple positions exposed to the same macro regime?
- Are the holdings clustered in the same sector or factor group?
- Would liquidity become a problem in a selloff?

### Output

This model should produce a distinct object:

- `portfolio_allocation_risk_score`
- `portfolio_confidence`
- `top_risk_drivers`
- `danger_clusters`

### What not to do

Do not do:

```text
portfolio_score = average(asset_scores)
```

That loses the actual portfolio risk picture.

---

## Database Changes

Add new tables or materialized records in Supabase.

### 1. `ticker_metadata`

One row per ticker, slowly changing metadata.

Suggested fields:

- `ticker`
- `company_name`
- `asset_class`
- `sector`
- `industry`
- `exchange`
- `market_cap`
- `float_shares`
- `avg_daily_dollar_volume`
- `spread_proxy`
- `beta`
- `volatility_proxy`
- `profitability_profile`
- `leverage_profile`
- `updated_at`

### 2. `asset_safety_profiles`

Current structural safety snapshot per ticker.

Suggested fields:

- `ticker`
- `as_of_date`
- `structural_base_score`
- `macro_adjustment`
- `event_adjustment`
- `safety_score`
- `confidence`
- `asset_class`
- `regime_state`
- `updated_at`

### 3. `safety_factor_snapshots`

Debuggable factor history.

Suggested fields:

- `ticker`
- `as_of_date`
- `market_cap_bucket`
- `liquidity_score`
- `volatility_score`
- `leverage_score`
- `profitability_score`
- `macro_sensitivity_score`
- `event_risk_score`
- `composite_safety_score`
- `confidence`
- `factor_breakdown`

### 4. `macro_regime_snapshots`

Slow-moving regime records.

Suggested fields:

- `as_of_date`
- `regime_state`
- `rates_signal`
- `credit_signal`
- `inflation_signal`
- `growth_signal`
- `risk_on_off_signal`
- `notes`

### 5. `portfolio_risk_snapshots`

Portfolio-level risk history.

Suggested fields:

- `user_id`
- `as_of_date`
- `portfolio_allocation_risk_score`
- `confidence`
- `concentration_risk`
- `cluster_risk`
- `correlation_risk`
- `liquidity_mismatch`
- `macro_stack_risk`
- `factor_breakdown`

### 6. Optional compatibility fields

Keep legacy fields temporarily where needed:

- `total_score`
- `grade`
- `dimension_rationale`

But these should become backward-compatibility fields, not the core architecture.

---

## Backend File Changes

### Scoring and calibration

Primary files:

- `backend/app/pipeline/risk_scorer.py`
- `backend/app/pipeline/scheduler.py`
- `backend/app/pipeline/portfolio_compiler.py`
- `backend/app/pipeline/relevance.py`
- `backend/app/pipeline/classifier.py`
- `backend/app/pipeline/position_report_builder.py`

### Models

- `backend/app/models/risk_score.py`
- `backend/app/models/alert.py`
- `backend/app/models/digest.py`

### Routes

- `backend/app/routes/positions.py`
- `backend/app/routes/digest.py`
- `backend/app/routes/alerts.py`
- `backend/app/routes/preferences.py`
- `backend/app/routes/analysis_runs.py`

### Schema and migrations

- `supabase_schema.sql`
- `supabase/migrations/*`

### Supporting services

- `backend/app/services/polygon.py`
- `backend/app/services/supabase.py`
- `backend/app/services/minimax.py` if the prompt contract changes

---

## Prompt and AI Role

The LLM should not own the system.

### Allowed LLM responsibilities

- explain factor rationale
- classify ambiguous event impact
- summarize edge cases
- help label macro or event significance when evidence is thin

### Disallowed LLM responsibilities

- deciding the full structural base score
- overriding deterministic factor rules
- generating unbounded daily moves
- inventing confidence without data

### New scorer prompt should ask

- where this asset belongs on the safety ladder today
- which factors are structural
- which factors are temporary
- what would cause a one-band move
- what would cause a collapse

The output should be structured JSON only.

---

## API Changes

### `/positions/{id}`

Add or rename fields to return:

- current asset safety score
- confidence
- structural base score
- macro adjustment
- event adjustment
- factor breakdown
- historical safety trend
- recent safety drivers

### `/digest`

Digest should prioritize:

1. portfolio safety right now
2. what changed safety
3. least safe positions
4. main exposures
5. whether the portfolio is improving or worsening

### `/alerts`

Add alert types:

- `safety_deterioration`
- `portfolio_safety_threshold_breach`
- `concentration_danger`
- `macro_shock`
- `structural_fragility`

### `/preferences`

Extend user guardrails:

- minimum acceptable safety score
- target portfolio safety band
- max low-safety positions
- max concentration in risky names
- alert threshold for score drops

---

## Scheduler Changes

The scheduler must do two different jobs:

1. news-triggered event updates
2. periodic structural refresh

### Required scheduler modes

- daily structural refresh
- event-driven scoring update
- digest generation
- threshold alert evaluation

### Quiet-day behavior

Even if no news arrives:

- refresh structural profiles
- refresh macro regime
- recompute asset safety
- update portfolio risk

No news must not imply safe.

---

## Migration Order

### Phase 1: Vocabulary and schema

- remove `thesis_integrity`
- add confidence fields
- add safety tables
- preserve legacy fields temporarily

### Phase 2: Structural scoring

- build deterministic factor scoring
- write `ticker_metadata`
- write `asset_safety_profiles`

### Phase 3: Macro and event layers

- add regime snapshot logic
- rework event significance
- add bounded event and macro adjustments

### Phase 4: Portfolio risk

- create portfolio model
- persist portfolio snapshots
- add threshold evaluation

### Phase 5: API and UI updates

- update route contracts
- update iOS models and views
- expose confidence and trends

### Phase 6: Backfill and stabilization

- backfill metadata
- backfill initial profiles
- compare new scores to old ones
- tune caps and bands

---

## Testing Plan

### Unit tests

Cover:

- market cap bucket scoring
- liquidity penalties
- leverage penalties
- volatility penalties
- confidence calculation
- score caps and smoothing
- macro regime mapping
- event cap behavior

### Integration tests

Cover:

- quiet-day score generation
- major event score movement
- portfolio concentration warnings
- threshold alerts
- digest generation with no news

### Regression tests

Must verify:

- a Treasury-like asset scores near the top
- a microcap can score low without any news
- one bad article does not tank a structurally strong name unless evidence justifies it
- score movement stays bounded on ordinary days

---

## Acceptance Criteria

The refactor is complete when:

- every asset has a standing safety score even on quiet days
- the score has confidence
- structural score dominates event noise
- macro is bounded and explainable
- portfolio risk is separate from asset safety
- the old thesis-integrity dimension is gone
- alerts are safety-driven, not drama-driven
- digest output is short, structured, and safety-first

---

## Suggested First Implementation Slice

If you want the smallest high-value first step, do this:

1. Add `confidence`, `structural_base_score`, `macro_adjustment`, and `event_adjustment` to the score model.
2. Add `ticker_metadata` and `asset_safety_profiles`.
3. Replace `thesis_integrity` in `backend/app/pipeline/risk_scorer.py`.
4. Add deterministic structural scoring for market cap, liquidity, volatility, leverage, and profitability.
5. Add score caps and smoothing.
6. Expose the new fields in `/positions/{id}`.

That gets the product onto the new safety architecture before the broader portfolio work lands.
