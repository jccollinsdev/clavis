# Methodology
How Clavis analyzes your portfolio risk and translates market events into clear, observable signals.

**Last updated:** April 12, 2026

---

## The Three Analysis Layers

Clavis evaluates your portfolio across three interconnected layers. Every score reflects all three working together — not a single number pulled in isolation.

### Macro Layer

Broad market conditions that set the overall risk tone: interest rates, Federal Reserve policy, inflation trends, GDP growth, geopolitical events, and cross-sector volatility regimes. These factors affect nearly every position indirectly. When the macro picture shifts, it changes the baseline risk for all holdings — even solid companies can see their risk scores rise simply because the environment became more hostile.

### Sector Layer

Industry and sector-level dynamics: earnings surprises within a sector, regulatory changes, supply chain shifts, commodity price moves, and sector rotation patterns. These factors affect groups of related positions. A rate-sensitive sector like real estate can underperform even when individual REITs have strong operating metrics. Sector signals help the model understand *why* a position is moving before the company-specific news arrives.

### Position Layer

Company-specific signals: earnings results versus expectations, leadership changes, product recalls, legal developments, unusual options activity, and news sentiment specific to that ticker. These are the most direct inputs to a position's score — and the fastest to change. A single earnings miss can move a position from B to D in hours.

---

## Risk Scoring Dimensions

Each position receives a score (0–100) across four dimensions. The dimension scores are averaged into a single total score, which maps to a letter grade (A–F). Scores are archetype-aware: a small-cap speculative holding is judged against different baselines than a defensive utility.

### News Sentiment (0–100)

The tone and severity of recent news coverage for this specific ticker. Positive coverage moves the score up; negative coverage — especially coverage describing operational problems, leadership instability, or legal issues — moves it down. Neutral news scores 50. This dimension captures the market's attention and whether that attention is favorable or hostile.

### Macro Exposure (0–100)

How sensitive this position is to current macro conditions. High macro sensitivity (e.g., rate-sensitive equities, high-beta growth names) scores lower when macro conditions are hostile. Low macro sensitivity (e.g., defensive names, companies with pricing power, non-cyclical businesses) scores higher. This dimension prevents the model from treating all positions the same when the Fed is moving.

### Position Sizing (0–100)

Whether your allocation to this position is appropriate given its current risk profile. A large position in a high-risk name is penalized. A small position in the same name is treated more indulgently. This dimension is personal — it reflects your portfolio, not the market. Two investors holding the same ticker can receive different scores on this dimension if their position sizes differ.

### Volatility Trend (0–100)

Whether recent price volatility is increasing, stable, or decreasing. Increasing volatility — especially when it coincides with negative news — signals elevated risk. Decreasing volatility in a flat or positive price context signals stability. This dimension uses recent price behavior, not long-term averages, to stay current.

---

## Grade Scale

Grades translate the total score into a severity signal. The scale is fixed and applies uniformly across all positions.

| Grade | Score Range | What It Means |
|---|---|---|
| **A** | 80–100 | Risk is low. Market conditions and company fundamentals are cooperating with your position's current setup. |
| **B** | 65–79 | No immediate concerns. Conditions are net positive but worth watching. |
| **C** | 50–64 | Mixed signals. The position is neither clearly safe nor clearly at risk. Watch for developments. |
| **D** | 35–49 | Risk is elevated. Things have deteriorated enough that the downside is material. |
| **F** | 0–34 | High risk. Fundamentals or market conditions have moved against the position. |

**Grade stability.** Clavis applies a hysteresis buffer when a position is near a grade boundary. A position won't flip from B to C simply because its score dipped one point below the threshold — it needs to stay there. This prevents noise from creating false signals. When a grade does change, the new grade is stable before it propagates to alerts.

**Grade history.** Every score is stored over time. You can see whether a position has been holding steady at A or slowly drifting from B toward C over the past month. A position that has been B for six weeks is different from one that dropped from A to B in two days.

---

## Signal Labels

Every position carries an observational signal label — a plain-language description of what the evidence currently shows. These are not instructions. They describe what the model is observing, not what you should do.

| Label | What It Means |
|---|---|
| **Thesis Intact** | The case for owning this position is holding. No concerning signals detected. |
| **Watching** | Something has changed. Not yet a problem, but the trajectory warrants attention. |
| **Pressure Building** | Negative signals are accumulating. The position is showing stress. |
| **Risk Elevated** | The downside has become material. The evidence is no longer ambiguous. |
| **Under Stress** | Fundamentals or market conditions have moved clearly against the position. |

---

## The Daily Digest

Each morning, Clavis delivers a briefing organized in three parts:

**Market Context** — Key macro events from the prior 24 hours and what they mean for markets broadly. This is the layer that sets the tone before your positions are even considered.

**Where You're Exposed** — How macro and sector moves connect to your specific holdings, ranked by risk severity. The positions driving the most portfolio risk appear first. Each entry shows the current grade and what's driving it.

**Notable Changes** — A plain-language summary of what changed overnight for your positions. New negative signals, grade movements, and emerging concerns are flagged here. The goal is to answer "did anything happen overnight that changes my risk?" in under a minute.

---

## Data Sources

Clavis aggregates from multiple provider types:

- **Brokerage connections** (via SnapTrade) — read-only access to your holdings data
- **Licensed financial news and data feeds** — real-time news ingestion filtered to your holdings
- **Public market data providers** (Polygon, Finnhub) — price, volume, fundamentals, and options data
- **Alternative data** — options flow patterns and sentiment indices used for early signal detection

---

## Model Limitations

No model is omniscient. Clavis has explicit, known boundaries:

**Lag.** News events take time to propagate into scores. A sudden market move — a flash crash, an unexpected Fed statement — may not be reflected in scores immediately. The model works on the prior 24–48 hours of evidence, not real-time ticks.

**Black swan events.** Sudden, unpredictable shocks (natural disasters, geopolitical crises, surprise regulatory actions) can overwhelm the patterns the model relies on. These events are by definition outside the training distribution.

**Archetype assumptions.** Scoring is relative to the position's archetype, but archetypes are inferred from data, not declared. A position tagged incorrectly by archetype will be judged against the wrong baseline.

**Sentiment analysis.** Text-based news analysis can miss sarcasm, spin, delayed reporting, or information that is well-known to institutional investors but underreported in mainstream financial news.

**Score disclaimer.** All Clavis outputs are algorithmically generated informational signals. They are not investment advice, not a substitute for professional analysis, and not a prediction of future performance. Treat them as one input among many in your own decision-making process. Past signal behavior does not guarantee future results. The methodology may evolve as the model is refined over time.
