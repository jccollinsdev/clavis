# P1 — Rating Language & Presentation Alignment

**Goal:** Make Clavis read like a credit-rating agency (Moody's / S&P tone), not a research analyst. Align every surface around A/B/C/D/F risk grades. Remove all remaining analyst/research language.

**Constraint:** No scoring logic, weight, or data-source changes.

---

## P1-A: Shorter, Rating-Style Rationale Output

**Problem:** Rationales still read like analyst notes — multi-sentence paragraphs with hedged language.

**Target:** Every rationale follows the contract already enforced by `sanitize_rationale()`:
```
B — Moderate Risk (→)
• Revenue beat on margin compression
• Sector rotation into defensives
```

### Tasks

1. **Tighten scorer SYSTEM_PROMPT constraints** (`risk_scorer.py`)
   - Enforce 1-line header + max 2 driver bullets in the prompt
   - Ban paragraph prose, conjunction chains ("and also additionally"), and hedge phrases
   - Add explicit instruction: "Write like a credit rating bulletin, not a research note"

2. **Tighten position_report_builder SYSTEM_PROMPT** (`position_report_builder.py`)
   - Same contract: header line + max 2 drivers
   - Ban "we believe", "we note", "our analysis suggests"
   - Replace any remaining "thesis" / "investment" / "outlook" phrasing

3. **Tighten portfolio_compiler SYSTEM_PROMPT** (`portfolio_compiler.py`)
   - Digest rationale: same header + bullets format
   - Ban "monitoring notes" variants (already partially done, audit for stragglers)
   - Ban "provisional" and "current read" (already in sanitizer, confirm prompt-side)

4. **Add rationale length audit to sanitize_rationale()** (`analysis_utils.py`)
   - After sanitization, if output > 200 chars, strip to first 2 newlines + "…more"
   - Log a warning when truncation fires (for prompt tuning visibility)

5. **Regression tests** (`test_p0_grade_contract.py` — add P1 tests)
   - Test that `sanitize_rationale` strips paragraphs → header + bullets
   - Test that over-length output is truncated
   - Test banned phrases are replaced in live prompt outputs

---

## P1-B: Risk Driver Quality

**Problem:** AI sometimes returns vague drivers ("mixed signals", "ongoing volatility") or fills bullet slots with restated headers.

**Target:** Each driver bullet names a *specific factual catalyst* (earnings miss, FDA ruling, sector rotation) or honestly signals limited evidence.

### Tasks

1. **Add driver-specificity constraints to all scorer prompts**
   - "Each driver must name a concrete event, metric change, or sector theme — not a generic observation"
   - "If evidence is thin, write: 'Limited coverage — fewer than 3 material events identified' as the only bullet"
   - Add negative examples: "❌ 'Mixed signals across sectors'" and positive examples: "✅ 'CPI miss → bond sell-off'"

2. **Add evidence-count gating in risk_scorer**
   - If `relevant_events < 3`, force the "limited coverage" single-bullet rationale instead of fabricated diversification
   - Pass event count context into the prompt so the model knows its evidence budget

3. **Ban generic filler phrases in sanitize_rationale**
   - Add to `_BANNED_PHRASES_PATTERNS`: "mixed signals", "ongoing volatility", "various factors", "overall trends", "broad market", "general uncertainty"
   - Replace with "[specific catalyst]" placeholder that triggers a re-prompt flag

4. **Add thin-evidence label to risk_scores output** (`build_risk_score_response`)
   - New field: `evidence_strength: "strong" | "moderate" | "thin"` derived from event count
   - iOS surfaces this as a confidence tag next to the grade

5. **Regression tests**
   - Test that event count < 3 produces thin-evidence label
   - Test that banned generic phrases are caught by sanitizer

---

## P1-C: A/B/C/D/F Alignment Across All Surfaces

**Problem:** Home, Holdings, Detail, Digest, and Alerts sometimes show numeric scores, sometimes vague labels, sometimes old grade mappings. The grade should be the primary signal everywhere.

**Target:** Every score surface shows the letter grade prominently (A/B/C/D/F), with numeric score as secondary context. Risk direction (↑↓→) is always visible.

### Tasks — Backend

1. **Ensure all API responses include `grade` + `gradeDirection` + `scoreDelta`**
   - `GET /positions/{id}` — already has these (P0)
   - `GET /holdings` — already has these (P0)
   - `GET /digest` — verify digest response includes `portfolio_grade` + `grade_direction`
   - `GET /alerts` — verify alerts include `grade` + `grade_direction`

2. **Add `evidence_strength` field to position and digest responses**
   - Positions: derive from event count in risk_scores
   - Digest: derive from digest-level event coverage

3. **Strip numeric-only score surfaces from API**
   - Any response field that only shows a score number should also include the grade
   - Do NOT remove the numeric score — just never show it alone without the grade

### Tasks — iOS

4. **Home / DashboardView**
   - Portfolio hero: show letter grade in large type, numeric score as subtitle
   - Change feed: show `gradeDirection` arrow (↑↓→) next to grade
   - Replace any raw-score-only displays with grade + score

5. **HoldingsListView**
   - PositionCardRow: grade letter is primary, score is secondary/muted
   - WatchlistCardRow: show grade for watched tickers, not just score
   - "Needs review" → "Downgraded" (already done in P0, verify)

6. **TickerDetailView**
   - Score hero section: grade letter large, score smaller below
   - Risk dimensions card: each factor label aligned with overall grade tone
   - Evidence strength badge: "Strong evidence" / "Moderate" / "Thin coverage"

7. **DigestView**
   - Portfolio grade hero: large letter grade with direction arrow
   - Each position item: show grade letter, not just name/score
   - "Morning Rating" (already done in P0, verify)
   - What Matters section: each item tagged with grade context if available

8. **AlertsView**
   - Alert items: show `gradeDirection` arrow and grade letter
   - Severity indicators: derive from grade (A/B = low, C = medium, D/F = high) not raw score
   - `ratingReady` alerts (already done in P0, verify)

9. **SettingsView**
   - ScoreExplanationView: already updated to canonical 80/65/50/35/0 bands (P0)
   - Verify methodology copy says "risk rating" not "risk score" everywhere
   - Add evidence_strength methodology note

10. **Shared grade display components**
    - Extract a reusable `GradeBadge` view: letter + direction arrow + optional evidence tag
    - Use this component everywhere grades appear (Home, Holdings, Detail, Digest, Alerts)

---

## P1-D: Remove Remaining Analyst / Research Language

**Problem:** Scattered references to "analysis", "research note", "thesis", "investment thesis", "advisory", "recommendation" remain in prompts, comments, and UI strings.

**Target:** Clavis is a risk-rating platform. All language is rating-oriented.

### Tasks

1. **Audit all backend SYSTEM_PROMPT strings**
   - Grep for: "analysis", "research", "thesis", "investment", "advisory", "recommendation", "outlook", "monitoring", "conviction", "view", "stance", "opinion"
   - Replace with: "rating", "assessment", "risk driver", "downgrade", "upgrade", "stable"

2. **Audit all iOS user-facing strings**
   - Grep for: "analysis", "research", "thesis", "investment", "advisory", "recommendation"
   - Replace with rating-oriented language
   - Exception: "analysis_status" / "analysis_run" are internal field names — leave those alone

3. **Audit comments and docstrings**
   - Same grep across backend and iOS
   - Clean up only user-facing or prompt-adjacent comments; internal naming is fine

4. **Add banned-word test**
   - Unit test that fails if any SYSTEM_PROMPT contains banned analyst phrases
   - Add to `test_p0_grade_contract.py` or a new `test_p1_language_contract.py`

---

## P1 Execution Order

| Order | Item | Depends On |
|-------|------|------------|
| 1 | P1-A (rationale format) | P0 complete |
| 2 | P1-B (driver quality) | P1-A prompts |
| 3 | P1-D (language audit) | P1-A + P1-B (do alongside) |
| 4 | P1-C (iOS alignment) | P1-A backend changes deployed |

## P1 Exit Criteria

- [ ] Every rationale follows: `[GRADE] — [Risk Level] ([↑↓→])` + max 2 driver bullets
- [ ] No rationale exceeds 200 characters after sanitization
- [ ] Thin-evidence positions are labeled, not disguised as high-confidence
- [ ] All 5 surfaces (Home, Holdings, Detail, Digest, Alerts) show grade as primary signal
- [ ] No analyst/research/thesis language in prompts or user-facing strings
- [ ] Zero scoring logic changes