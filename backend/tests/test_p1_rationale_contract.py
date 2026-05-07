from app.pipeline.analysis_utils import (
    score_to_grade,
    grade_direction,
    grade_to_risk_level,
    sanitize_rationale,
    format_rationale,
    evidence_strength,
    clamp_score,
)


def test_score_to_grade():
    assert score_to_grade(95) == "AAA"
    assert score_to_grade(90) == "AAA"
    assert score_to_grade(89.9) == "AA"
    assert score_to_grade(80) == "AA"
    assert score_to_grade(79.9) == "A"
    assert score_to_grade(70) == "A"
    assert score_to_grade(69.9) == "BBB"
    assert score_to_grade(60) == "BBB"
    assert score_to_grade(59.9) == "BB"
    assert score_to_grade(50) == "BB"
    assert score_to_grade(49.9) == "B"
    assert score_to_grade(40) == "B"
    assert score_to_grade(39.9) == "CCC"
    assert score_to_grade(30) == "CCC"
    assert score_to_grade(29.9) == "CC"
    assert score_to_grade(20) == "CC"
    assert score_to_grade(19.9) == "C"
    assert score_to_grade(10) == "C"
    assert score_to_grade(9.9) == "F"
    assert score_to_grade(0) == "F"
    assert score_to_grade(-5) == "F"


def test_grade_direction():
    assert grade_direction(70, 60) == "up"
    assert grade_direction(60, 70) == "down"
    assert grade_direction(60, 60) == "flat"
    assert grade_direction(60, 58) == "flat"
    assert grade_direction(60, 62) == "flat"
    assert grade_direction(None, 50) == "flat"
    assert grade_direction(50, None) == "flat"
    assert grade_direction(None, None) == "flat"


def test_clamp_score_no_floor():
    assert clamp_score(90, 0) == 90
    assert clamp_score(50, 0) == 50
    assert clamp_score(20, 0) == 20
    assert clamp_score(0, 0) == 0
    assert clamp_score(-5, 0) == 0
    assert clamp_score(105, 0) == 100
    assert clamp_score(None, 0) == 0


def test_clamp_score_default_on_invalid():
    assert clamp_score(None, 50) == 50
    assert clamp_score("abc", 0) == 0


def test_sanitize_rationale_banned_phrases():
    assert "thesis" not in sanitize_rationale("The thesis is clear.")
    assert "positive momentum" not in sanitize_rationale("Positive momentum drives gains.")
    assert "macro headwinds" not in sanitize_rationale("Macro headwinds ahead.")
    assert "provisional" not in sanitize_rationale("This is provisional data.")
    assert "current read" not in sanitize_rationale("The current read is elevated.")
    assert "coverage" not in sanitize_rationale("Limited coverage available.")
    assert "monitor" not in sanitize_rationale("Monitor this position.")


def test_sanitize_rationale_length_limit():
    long_text = " ".join(["word"] * 100)
    result = sanitize_rationale(long_text)
    assert len(result) <= 280
    assert result.endswith(".")


def test_sanitize_rationale_empty():
    assert sanitize_rationale("") == ""
    assert sanitize_rationale("   ") == ""


def test_stale_grade_regression():
    assert score_to_grade(32.5) == "CCC", "score 32.5 must map to CCC"
    assert score_to_grade(33.8) == "CCC", "score 33.8 must map to CCC"
    assert score_to_grade(34.9) == "CCC", "score 34.9 must map to CCC"
    assert score_to_grade(35) == "CCC", "score 35 is the CCC boundary"
    assert score_to_grade(39.9) == "CCC", "score 39.9 must map to CCC"
    assert score_to_grade(40) == "B", "score 40 is the B boundary"
    assert score_to_grade(49.9) == "B", "score 49.9 must map to B"


def test_grade_to_risk_level():
    assert grade_to_risk_level("AAA") == "Treasury-Grade"
    assert grade_to_risk_level("AA") == "Investment-Grade Safe"
    assert grade_to_risk_level("A") == "Solid"
    assert grade_to_risk_level("BBB") == "Stable, Watch Points"
    assert grade_to_risk_level("BB") == "Mixed Signals"
    assert grade_to_risk_level("B") == "Elevated Risk"
    assert grade_to_risk_level("CCC") == "High Risk"
    assert grade_to_risk_level("CC") == "Severe Risk"
    assert grade_to_risk_level("C") == "Distressed"
    assert grade_to_risk_level("F") == "Failure Mode"
    assert grade_to_risk_level("unknown") == "Elevated Risk"


def test_evidence_strength():
    assert evidence_strength(0) == "thin"
    assert evidence_strength(1) == "thin"
    assert evidence_strength(2) == "thin"
    assert evidence_strength(3) == "moderate"
    assert evidence_strength(5) == "moderate"
    assert evidence_strength(6) == "strong"
    assert evidence_strength(10) == "strong"


def test_format_rationale_header_structure():
    result = format_rationale("BB", "down", "Earnings miss on revenue weakness")
    lines = result.strip().split("\n")
    assert len(lines) >= 1

    header = lines[0]
    assert header.startswith("BB —")
    assert "Mixed Signals" in header
    assert "↑ worsening" in header


def test_format_rationale_direction_arrows():
    improving = format_rationale("B", "up", "Strong earnings")
    worsening = format_rationale("CCC", "down", "Weak revenue trend")
    stable = format_rationale("AAA", "flat", "Stable profile")

    assert "↓ improving" in improving
    assert "↑ worsening" in worsening
    assert "→ stable" in stable


def test_format_rationale_max_two_drivers():
    long_text = "Driver one is about earnings.\nDriver two is about macro.\nDriver three is about volatility."
    result = format_rationale("BB", "flat", long_text)
    lines = [l for l in result.strip().split("\n") if l.strip()]
    assert len(lines) <= 3, f"Expected max 3 lines (1 header + 2 drivers), got {len(lines)}: {lines}"


def test_format_rationale_driver_max_60_chars():
    very_long_driver = "A" * 100
    result = format_rationale("BB", "flat", very_long_driver)
    for line in result.strip().split("\n")[1:]:
        assert len(line) <= 60, f"Driver line exceeds 60 chars: '{line}'"


def test_format_rationale_total_max_length():
    text = "\n".join(["This is driver " + str(i) for i in range(5)])
    result = format_rationale("CCC", "down", text)
    assert len(result) <= 200, f"Total rationale exceeds 200 chars: {len(result)}"


def test_format_rationale_no_banned_words():
    banned = ["may", "could", "would", "suggests", "indicates", "sentiment",
              "momentum", "thesis", "coverage", "provisional"]
    result = format_rationale(
        "BB", "flat",
        "Negative company-specific news\nMacro pressure on the sector"
    )
    result_lower = result.lower()
    for word in banned:
        assert word not in result_lower, f"Banned word '{word}' found in: {result}"


def test_format_rationale_grade_matches_header():
    for grade, expected in [("AAA", "Treasury-Grade"), ("AA", "Investment-Grade Safe"),
                             ("A", "Solid"), ("BBB", "Stable, Watch Points"),
                             ("BB", "Mixed Signals"), ("B", "Elevated Risk"),
                             ("CCC", "High Risk"), ("CC", "Severe Risk"),
                             ("C", "Distressed"), ("F", "Failure Mode")]:
        result = format_rationale(grade, "flat", "Some driver")
        assert f"{grade} — {expected}" in result, f"Expected '{grade} — {expected}' in: {result}"


def test_format_rationale_fallback_when_no_drivers():
    result = format_rationale("BB", "flat", None, source_count=1)
    assert "BB — Mixed Signals" in result
    assert "→ stable" in result
    lines = [l for l in result.strip().split("\n") if l.strip()]
    assert len(lines) >= 2


def test_format_rationale_thin_evidence_fallback():
    result = format_rationale("CCC", "flat", "", source_count=0)
    assert "Limited data" in result
    assert "fundamentals" in result.lower()


def test_format_rationale_extracts_drivers_from_newlines():
    text = "Some header line\nFirst driver\nSecond driver\nThird driver (should be dropped)"
    result = format_rationale("BB", "flat", text)
    lines = result.strip().split("\n")
    assert len(lines) <= 3


def test_format_rationale_extracts_drivers_from_sentences():
    text = "Negative news is the primary risk. Macro pressure adds downside."
    result = format_rationale("CCC", "down", text)
    assert "CCC — High Risk" in result
    assert "↑ worsening" in result


def test_format_rationale_generic_drivers_by_grade():
    result_f = format_rationale("F", "down", None, scores={"financial_health": 60, "news_sentiment": 20, "macro_exposure": 30, "sector_exposure": 40, "volatility": 30})
    assert "F — Failure Mode" in result_f
    assert "↑ worsening" in result_f

    result_aaa = format_rationale("AAA", "up", None, scores={"financial_health": 95, "news_sentiment": 90, "macro_exposure": 85, "sector_exposure": 85, "volatility": 85})
    assert "AAA — Treasury-Grade" in result_aaa
    assert "↓ improving" in result_aaa


def test_format_rationale_direction_none_defaults_stable():
    result = format_rationale("A", None, "Strong fundamentals")
    assert "→ stable" in result


def test_sanitize_p1_banned_words():
    assert "may" not in sanitize_rationale("This may change things.")
    assert "could" not in sanitize_rationale("Risk could increase.")
    assert "would" not in sanitize_rationale("This would affect the rating.")
    assert "suggests" not in sanitize_rationale("This suggests growth.")
    assert "indicates" not in sanitize_rationale("Data indicates a shift.")


def test_format_rationale_sanitizes_banned_words_in_drivers():
    result = format_rationale(
        "CCC", "down",
        "The thesis suggests this momentum could shift. The coverage may be provisional."
    )
    result_lower = result.lower()
    assert "thesis" not in result_lower
    assert "momentum" not in result_lower
    assert "coverage" not in result_lower
    assert "provisional" not in result_lower
