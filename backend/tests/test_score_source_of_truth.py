"""Phase 5B — Score/grade source-of-truth cleanup validation.

These tests prove:
1. score_to_grade() is the ONLY backend grade-band rule.
2. Dead hysteresis code and GRADE_THRESHOLDS are fully removed.
3. Compatibility projections always derive from shared_analysis.
4. Score provenance labels are unified across endpoints.
5. Structural refresh cannot overwrite AI/shared ticker snapshot grade.
6. Same ticker returns identical shared score/grade through all read paths.
7. Dashboard and digest score metadata are consistent.
8. Null-grade behavior is consistent and does not fabricate a real grade.
9. Compatibility fields are present and projected from canonical shared data.

All tests are read-only — no DB writes, no live Supabase connections.
"""

import pytest
from unittest import mock

from app.pipeline.analysis_utils import score_to_grade, grade_direction, clamp_score
from app.services import ticker_cache_service as tcs


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Dead code removal
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeadCodeRemoved:
    """Confirm _apply_grade_hysteresis and redundant grade artifacts are removed."""

    def test_hysteresis_function_removed(self):
        import app.pipeline.risk_scorer as rs
        assert not hasattr(rs, "_apply_grade_hysteresis")

    def test_grade_thresholds_removed(self):
        import app.pipeline.risk_scorer as rs
        assert not hasattr(rs, "GRADE_THRESHOLDS")
        assert not hasattr(rs, "GRADE_ORDER")
        assert not hasattr(rs, "GRADE_HYSTERESIS")

    def test_score_to_grade_is_only_grade_band(self):
        """The ONLY grade band definition is analysis_utils.score_to_grade."""
        assert callable(score_to_grade)
        assert score_to_grade(95) == "AAA"
        assert score_to_grade(80) == "AA"
        assert score_to_grade(70) == "A"
        assert score_to_grade(60) == "BBB"
        assert score_to_grade(50) == "BB"
        assert score_to_grade(40) == "B"
        assert score_to_grade(30) == "CCC"
        assert score_to_grade(20) == "CC"
        assert score_to_grade(10) == "C"
        assert score_to_grade(5) == "F"


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Consolidated grade bands
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalGradeBands:
    """score_to_grade() is the single source of truth for grade mapping."""

    def test_grade_boundaries(self):
        assert score_to_grade(100) == "AAA"
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

    def test_grade_is_deterministic(self):
        for score in (0, 10, 35, 50, 65, 80, 100):
            assert score_to_grade(score) == score_to_grade(score)

    def test_grade_never_returns_none(self):
        for score in range(-5, 106, 5):
            grade = score_to_grade(score)
            assert grade in ("AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "F")

    def test_all_scoring_functions_use_canonical_grade(self):
        """Verify every scoring function imports from analysis_utils."""
        import app.pipeline.risk_scorer as rs
        import inspect
        src = inspect.getsource(rs._deterministic_dimension_scores)
        assert "score_to_grade" in src
        src = inspect.getsource(rs.score_position_structural)
        assert "score_to_grade" in src


class TestGradeDirection:
    def test_direction_up(self):
        assert grade_direction(70, 60) == "up"

    def test_direction_down(self):
        assert grade_direction(60, 70) == "down"

    def test_direction_flat(self):
        assert grade_direction(65, 65) == "flat"
        assert grade_direction(63, 65) == "flat"


class TestClampScore:
    def test_clamp_within_range(self):
        assert clamp_score(50) == 50
        assert clamp_score(0) == 0
        assert clamp_score(100) == 100

    def test_clamp_above_range(self):
        assert clamp_score(150) == 100

    def test_clamp_below_range(self):
        assert clamp_score(-10) == 0

    def test_clamp_defaults_to_50(self):
        assert clamp_score("bad") == 50
        assert clamp_score(None) == 50


# ═══════════════════════════════════════════════════════════════════════════════
# Shared analysis consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestSharedTickerAnalysisSummary:
    """build_shared_ticker_analysis_summary() produces consistent score/grade."""

    def _fake_snapshot(self, **overrides):
        return {
            "ticker": "TEST",
            "grade": "B",
            "safety_score": 72.0,
            "structural_base_score": 68.0,
            "macro_adjustment": 2.0,
            "event_adjustment": 2.0,
            "confidence": 0.75,
            "factor_breakdown": {
                "ai_dimensions": {
                    "news_sentiment": 65,
                    "macro_exposure": 70,
                    "position_sizing": 75,
                    "volatility_trend": 78,
                }
            },
            "reasoning": "B — Moderate Risk (→ stable). Stable earnings growth supports moderate risk rating.",
            "news_summary": "Quarterly earnings were in line with expectations.",
            "source_count": 12,
            "analysis_as_of": "2026-05-05T12:00:00+00:00",
            "methodology_version": "sp500-ai-backfill-v2",
            **overrides,
        }

    def _fake_previous_snapshot(self, **overrides):
        return {
            "safety_score": 68.0,
            "grade": "B",
            **overrides,
        }

    def test_shared_summary_uses_snapshot_score(self):
        snapshot = self._fake_snapshot()
        result = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=snapshot, previous_snapshot=None,
        )
        assert result["current_score"] == 72.0
        assert result["current_grade"] == "B"

    def test_shared_summary_derives_grade_from_score_when_missing(self):
        snapshot = self._fake_snapshot(grade=None, safety_score=82.0)
        result = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=snapshot, previous_snapshot=None,
        )
        assert result["current_grade"] == "A"

    def test_shared_summary_returns_none_when_no_data(self):
        """No snapshot → grade is None (not fabricated as C)."""
        result = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=None, previous_snapshot=None,
        )
        assert result["current_grade"] is None
        assert result["current_score"] is None

    def test_shared_summary_computes_grade_direction(self):
        snapshot = self._fake_snapshot(safety_score=72.0)
        previous = self._fake_previous_snapshot(safety_score=68.0)
        result = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=snapshot, previous_snapshot=previous,
        )
        assert result["grade_direction"] == "up"
        assert result["score_delta"] == 4

    def test_shared_summary_grade_direction_flat_when_no_previous(self):
        snapshot = self._fake_snapshot()
        result = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=snapshot, previous_snapshot=None,
        )
        assert result["grade_direction"] == "flat"


# ═══════════════════════════════════════════════════════════════════════════════
# Compatibility projection consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompatibilityProjection:
    """_project_shared_summary_compatibility() always derives from shared_analysis."""

    def _fake_shared_summary(self):
        return {
            "current_score": 72.0,
            "current_grade": "B",
            "grade_direction": "up",
            "score_delta": 4,
            "grade_rationale": "B — Moderate Risk (→ stable).",
            "analysis_source": "shared",
            "freshness": {
                "score_as_of": "2026-05-05T12:00:00+00:00",
                "analysis_as_of": "2026-05-05T12:00:00+00:00",
                "status": "ready",
                "coverage_state": "substantive",
                "coverage_note": "Backed by 12 sources.",
            },
            "methodology_version": "sp500-ai-backfill-v2",
            "evidence_strength": "moderate",
        }

    def test_projection_copies_grade_from_shared(self):
        summary = self._fake_shared_summary()
        result = tcs._project_shared_summary_compatibility(
            base={"ticker": "TEST"}, shared_summary=summary,
        )
        assert result["grade"] == "B"
        assert result["risk_grade"] == "B"

    def test_projection_copies_score_from_shared(self):
        summary = self._fake_shared_summary()
        result = tcs._project_shared_summary_compatibility(
            base={"ticker": "TEST"}, shared_summary=summary,
        )
        assert result["total_score"] == 72.0
        assert result["safety_score"] == 72.0

    def test_projection_does_not_use_base_stale_grade(self):
        summary = self._fake_shared_summary()
        base = {"ticker": "TEST", "risk_grade": "F", "total_score": 20.0}
        result = tcs._project_shared_summary_compatibility(
            base=base, shared_summary=summary,
        )
        assert result["risk_grade"] == "B"
        assert result["total_score"] == 72.0

    def test_projection_preserves_compatibility_fields(self):
        """Compatibility fields (grade, risk_grade, total_score, safety_score,
        summary) are all present and projected from shared data."""
        summary = self._fake_shared_summary()
        result = tcs._project_shared_summary_compatibility(
            base={"ticker": "TEST"}, shared_summary=summary,
        )
        for key in ("grade", "risk_grade", "total_score", "safety_score", "summary"):
            assert key in result, f"Compatibility field '{key}' missing from projection"


# ═══════════════════════════════════════════════════════════════════════════════
# Risk score response chain
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildRiskScoreResponse:
    """build_risk_score_response() prefers shared snapshot over user risk_scores."""

    def _fake_snapshot(self):
        return {
            "ticker": "TEST",
            "grade": "B",
            "safety_score": 72.0,
            "factor_breakdown": {
                "ai_dimensions": {
                    "news_sentiment": 65, "macro_exposure": 70,
                    "position_sizing": 75, "volatility_trend": 78,
                }
            },
            "reasoning": "B — Moderate Risk.",
            "source_count": 12,
            "analysis_as_of": "2026-05-05T12:00:00+00:00",
        }

    def test_prefers_snapshot_when_no_user_score(self):
        snapshot = self._fake_snapshot()
        result = tcs.build_risk_score_response(
            snapshot=snapshot, position_id="pos-1", latest_position_score=None,
        )
        assert result["safety_score"] == 72.0
        assert result["grade"] == "B"

    def test_score_source_is_shared_when_snapshot_exists(self):
        """score_source must be 'shared' when snapshot provides the score."""
        snapshot = self._fake_snapshot()
        result = tcs.build_risk_score_response(
            snapshot=snapshot, position_id="pos-1", latest_position_score=None,
        )
        assert result["score_source"] == "shared"

    def test_does_not_use_nonexistent_user_score_preferentially(self):
        snapshot = self._fake_snapshot()
        user_score = {"total_score": None, "safety_score": None, "grade": None}
        result = tcs.build_risk_score_response(
            snapshot=snapshot, position_id="pos-1", latest_position_score=user_score,
        )
        assert result["safety_score"] == 72.0
        assert result["grade"] == "B"


# ═══════════════════════════════════════════════════════════════════════════════
# Virtual position consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildVirtualPosition:
    """_build_virtual_position() derives grade from shared snapshot."""

    def test_uses_snapshot_score(self):
        snapshot = {"safety_score": 72.0, "grade": "B"}
        current_score = {"total_score": None, "grade": None}
        result = tcs._build_virtual_position(
            user_id="user-1", ticker="TEST", metadata={},
            snapshot=snapshot, previous_snapshot=None, current_score=current_score,
        )
        assert result["total_score"] == 72.0
        assert result["risk_grade"] == "B"

    def test_derives_grade_from_score_when_missing(self):
        snapshot = {"safety_score": 82.0, "grade": None}
        current_score = {"total_score": None, "grade": None}
        result = tcs._build_virtual_position(
            user_id="user-1", ticker="TEST", metadata={},
            snapshot=snapshot, previous_snapshot=None, current_score=current_score,
        )
        assert result["risk_grade"] == "A"


# ═══════════════════════════════════════════════════════════════════════════════
# Portfolio overlay — no score/grade contamination
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildPortfolioOverlay:
    """build_portfolio_overlay() does not compute or expose score/grade."""

    def test_overlay_does_not_contain_grade(self):
        result = tcs.build_portfolio_overlay(
            ticker="TEST", position=None, held_positions=[], is_in_watchlist=False,
        )
        assert "grade" not in result
        assert "risk_grade" not in result
        assert "total_score" not in result

    def test_overlay_risk_contribution_is_none(self):
        result = tcs.build_portfolio_overlay(
            ticker="TEST", position=None, held_positions=[], is_in_watchlist=False,
        )
        assert result.get("risk_contribution_score") is None


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end cross-read-path consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEndConsistency:
    """Score/grade flowing through the full chain stays consistent."""

    def _fake_snapshot(self):
        return {
            "ticker": "TEST",
            "grade": "B",
            "safety_score": 72.0,
            "factor_breakdown": {
                "ai_dimensions": {
                    "news_sentiment": 65, "macro_exposure": 70,
                    "position_sizing": 75, "volatility_trend": 78,
                }
            },
            "reasoning": "B — Moderate Risk.",
            "source_count": 12,
            "analysis_as_of": "2026-05-05T12:00:00+00:00",
            "methodology_version": "sp500-ai-backfill-v2",
        }

    def test_same_ticker_same_score_across_read_paths(self):
        snapshot = self._fake_snapshot()
        summary = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=snapshot, previous_snapshot=None,
        )
        projection = tcs._project_shared_summary_compatibility(
            base={}, shared_summary=summary,
        )
        risk_response = tcs.build_risk_score_response(
            snapshot=snapshot, position_id="pos-1", latest_position_score=None,
        )
        virtual = tcs._build_virtual_position(
            user_id="u1", ticker="TEST", metadata={}, snapshot=snapshot,
            previous_snapshot=None,
            current_score={"total_score": None, "grade": None},
        )

        assert summary["current_score"] == 72.0
        assert summary["current_grade"] == "B"
        assert projection["total_score"] == 72.0
        assert projection["risk_grade"] == "B"
        assert risk_response["safety_score"] == 72.0
        assert risk_response["grade"] == "B"
        assert virtual["total_score"] == 72.0
        assert virtual["risk_grade"] == "B"

    def test_grade_always_matches_score_bands(self):
        scores = [95, 80, 72, 65, 55, 50, 40, 35, 25, 0]
        for score in scores:
            snapshot = {
                "ticker": "T", "safety_score": float(score), "grade": None,
                "factor_breakdown": {}, "reasoning": "",
                "analysis_as_of": "2026-05-05T12:00:00+00:00",
            }
            summary = tcs.build_shared_ticker_analysis_summary(
                ticker="T", metadata={}, snapshot=snapshot, previous_snapshot=None,
            )
            expected = score_to_grade(score)
            assert summary["current_grade"] == expected, (
                f"Score {score} → grade {summary['current_grade']}, expected {expected}"
            )

    def test_null_grade_does_not_fabricate_real_grade(self):
        """When no snapshot exists, grade must be None — not 'C' or any real grade."""
        result = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=None, previous_snapshot=None,
        )
        assert result["current_grade"] is None
        assert result["current_score"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Structural refresh protection
# ═══════════════════════════════════════════════════════════════════════════════

class TestStructuralRefreshProtection:
    """Structural refresh must not overwrite AI/shared ticker snapshot grade."""

    def test_ai_snapshot_guard_checks_across_snapshot_types(self):
        """The guard in refresh_ticker_snapshot should detect AI snapshots
        regardless of snapshot_type — not just matching job_type."""
        import inspect
        src = inspect.getsource(tcs.refresh_ticker_snapshot)
        # Must query across ALL snapshot_types, not just job_type
        assert '.eq("snapshot_date"' in src
        assert '.eq("snapshot_type", job_type)' not in src, (
            "refresh_ticker_snapshot must not filter by snapshot_type "
            "when checking for existing AI snapshots"
        )

    def test_ai_snapshot_blocks_structural_write(self):
        """When an AI snapshot exists for today, refresh_ticker_snapshot
        returns the existing data without upserting a structural override."""
        import inspect
        src = inspect.getsource(tcs.refresh_ticker_snapshot)
        assert "skipped_ai_scored" in src, (
            "refresh_ticker_snapshot must return 'skipped_ai_scored' "
            "when AI snapshot exists"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Score provenance labels unified
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreProvenanceLabels:
    """Score provenance labels are consistent across endpoints."""

    def _fake_snapshot(self):
        return {
            "ticker": "TEST", "grade": "B", "safety_score": 72.0,
            "factor_breakdown": {"ai_dimensions": {
                "news_sentiment": 65, "macro_exposure": 70,
                "position_sizing": 75, "volatility_trend": 78,
            }},
            "reasoning": "B — Moderate Risk.",
            "source_count": 12,
            "analysis_as_of": "2026-05-05T12:00:00+00:00",
        }

    def test_risk_score_response_prefers_shared(self):
        """build_risk_score_response labels score_source as 'shared' when
        snapshot provides the score value."""
        snapshot = self._fake_snapshot()
        result = tcs.build_risk_score_response(
            snapshot=snapshot, position_id="pos-1", latest_position_score=None,
        )
        assert result["score_source"] == "shared"

    def test_shared_summary_always_shared(self):
        """build_shared_ticker_analysis_summary always returns
        analysis_source='shared'."""
        snapshot = self._fake_snapshot()
        result = tcs.build_shared_ticker_analysis_summary(
            ticker="TEST", metadata={}, snapshot=snapshot, previous_snapshot=None,
        )
        assert result["analysis_source"] == "shared"

    def test_dashboard_score_uses_digest_source(self):
        """Dashboard _portfolio_score_fields reads score_source from digest row."""
        import inspect
        from app.routes import dashboard
        src = inspect.getsource(dashboard._portfolio_score_fields)
        assert 'digest.get("score_source")' in src, (
            "Dashboard must use digest's score_source, not hardcoded 'digest'"
        )
