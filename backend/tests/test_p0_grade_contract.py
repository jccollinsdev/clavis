from app.pipeline.analysis_utils import score_to_grade, grade_direction, sanitize_rationale, clamp_score


def test_score_to_grade():
    assert score_to_grade(95) == "AAA"
    assert score_to_grade(90) == "AAA"
    assert score_to_grade(89.9) == "AA"
    assert score_to_grade(85) == "AA"
    assert score_to_grade(80) == "AA"
    assert score_to_grade(79.9) == "A"
    assert score_to_grade(75) == "A"
    assert score_to_grade(70) == "A"
    assert score_to_grade(69.9) == "BBB"
    assert score_to_grade(65) == "BBB"
    assert score_to_grade(60) == "BBB"
    assert score_to_grade(59.9) == "BB"
    assert score_to_grade(55) == "BB"
    assert score_to_grade(50) == "BB"
    assert score_to_grade(49.9) == "B"
    assert score_to_grade(40) == "B"
    assert score_to_grade(39.9) == "CCC"
    assert score_to_grade(35) == "CCC"
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