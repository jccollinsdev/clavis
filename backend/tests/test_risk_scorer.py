import sys
import types
import asyncio
import re


_fake_openai_module = types.ModuleType("openai")


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


_fake_openai_module.OpenAI = _FakeOpenAI
sys.modules.setdefault("openai", _fake_openai_module)

from app.pipeline import risk_scorer
from app.services.ticker_cache_service import build_risk_score_response


def _assert_strict_rationale(text: str, grade: str):
    assert text
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assert lines
    assert re.match(
        rf"{grade} — (Treasury-Grade|Investment-Grade Safe|Solid|Stable, Watch Points|Mixed Signals|Elevated Risk|High Risk|Severe Risk|Distressed|Failure Mode) \([↑↓→] (improving|worsening|stable)\)",
        lines[0],
    )
    assert len(lines) <= 3


def test_prefer_llm_scoring_for_backfill_when_analysis_exists():
    payload = {
        "analysis_mode": "sp500_backfill",
        "summary": "Recent company-specific catalysts are available.",
        "long_report": "Longer report body.",
        "event_analyses": [{"risk_direction": "worsening", "significance": "major"}],
    }

    assert risk_scorer._prefer_llm_scoring(payload) is True


def test_deterministic_scores_mark_llm_usage_false():
    result = risk_scorer._deterministic_dimension_scores(
        {
            "ticker": "AMD",
            "ticker_metadata": {"beta": 1.8, "volatility_proxy": 0.6},
            "event_analyses": [],
        },
        portfolio_total_value=1.0,
    )

    assert result["llm_scoring_used"] is False


def test_neutral_gate_requires_all_dimensions():
    assert (
        risk_scorer.has_suspicious_neutral_scores(
            {
                "financial_health": 50,
                "news_sentiment": 50,
                "macro_exposure": 50,
                "sector_exposure": 50,
                "volatility": 50,
            }
        )
        is True
    )
    assert (
        risk_scorer.has_suspicious_neutral_scores(
            {
                "financial_health": 50,
                "news_sentiment": 50,
                "macro_exposure": 50,
                "sector_exposure": 50,
                "volatility": 42,
            }
        )
        is False
    )


def test_llm_prompt_uses_treasury_scale_and_position_value():
    prompt = risk_scorer._llm_score_prompt(
        {
            "ticker": "AMD",
            "shares": 10,
            "purchase_price": 100,
            "position_value": 1000,
            "inferred_labels": ["growth"],
            "summary": "Company-specific catalyst",
            "long_report": "Detailed report",
        }
    )

    assert "treasury-like" in prompt
    assert "penny-stock-like" in prompt
    assert "Approximate position value: $1000.0" in prompt


def test_score_position_synthesizes_reasoning_when_llm_returns_blank(monkeypatch):
    monkeypatch.setattr(
        risk_scorer,
        "chatcompletion_text",
        lambda **kwargs: (
            '{"financial_health": 84, "news_sentiment": 52, "macro_exposure": 68, "sector_exposure": 71, "volatility": 89, "grade": "BBB", "reasoning": "", "dimension_rationale": {}}'
        ),
    )

    result = asyncio.run(
        risk_scorer.score_position(
            {
                "ticker": "AMD",
                "shares": 10,
                "purchase_price": 100,
                "current_price": 110,
                "analysis_mode": "sp500_backfill",
                "event_analyses": [],
                "summary": "Insufficient evidence was available for this cycle.",
                "long_report": "Long-form report.",
                "previous_total_score": 50,
            },
            {
                "summary": "Insufficient evidence was available for this cycle.",
                "long_report": "Long-form report.",
                "previous_grade": None,
            },
        )
    )

    assert result["reasoning"]
    assert "Company-specific news (" not in result["reasoning"]
    assert "adds risk at" not in result["reasoning"]
    assert result["coverage_state"] == "provisional"
    assert result["is_provisional"] is True


def test_score_position_uses_canonical_grade_band_over_previous_grade(monkeypatch):
    monkeypatch.setattr(
        risk_scorer,
        "chatcompletion_text",
        lambda **kwargs: (
            '{"financial_health": 84, "news_sentiment": 65, "macro_exposure": 65, '
            '"sector_exposure": 65, "volatility": 65, "grade": "CCC", "reasoning": "Balanced risk read.", '
            '"dimension_rationale": {}}'
        ),
    )

    result = asyncio.run(
        risk_scorer.score_position(
            {
                "ticker": "ABT",
                "shares": 10,
                "purchase_price": 100,
                "current_price": 110,
                "analysis_mode": "sp500_backfill",
                "event_analyses": [],
                "summary": "Company-specific catalyst",
                "long_report": "Long-form report.",
                "previous_total_score": 42,
            },
            {
                "summary": "Company-specific catalyst",
                "long_report": "Long-form report.",
                "previous_grade": "CCC",
            },
        )
    )

    assert result["total_score"] == 68.8
    assert result["grade"] == "BBB"


def test_build_risk_score_response_surfaces_coverage_context():
    response = build_risk_score_response(
        {
            "id": "snapshot-1",
            "safety_score": 58,
            "grade": "BB",
            "source_count": 0,
            "analysis_as_of": "2026-04-21T18:00:00+00:00",
        },
        position_id="position-1",
        latest_position_score={"reasoning": "", "total_score": 58, "grade": "BB"},
        coverage_context={
            "source_count": 0,
            "coverage_state": "provisional",
            "coverage_note": "Confidence is low because the score leans mostly on ticker metadata and cached context.",
            "is_provisional": True,
        },
    )

    assert response["coverage_state"] == "limited data"
    assert response["is_provisional"] is True
    assert response["source_count"] == 0
    _assert_strict_rationale(response["reasoning"], "BB")
    assert "Macro/sector exposure (" not in response["reasoning"]
    assert "adds risk at" not in response["reasoning"]
    assert "provisional" not in response["reasoning"].lower()


def test_build_risk_score_response_uses_latest_position_score_without_snapshot():
    response = build_risk_score_response(
        None,
        position_id="position-1",
        latest_position_score={
            "id": "risk-1",
            "calculated_at": "2026-04-22T18:00:00+00:00",
            "safety_score": 61,
            "grade": "B",
            "factor_breakdown": {
                "ai_dimensions": {
                    "news_sentiment": 72,
                    "macro_exposure": 48,
                    "position_sizing": 55,
                    "volatility_trend": 39,
                }
            },
        },
        coverage_context={"source_count": 3},
    )

    assert response is not None
    assert response["safety_score"] == 61
    assert response["factor_breakdown"]["ai_dimensions"]["news_sentiment"] == 72
    assert response["source_count"] == 3


def test_build_risk_score_response_ignores_draft_position_analysis_summary():
    response = build_risk_score_response(
        {"id": "snapshot-1", "safety_score": 58, "grade": "BB", "analysis_as_of": "2026-04-21T18:00:00+00:00"},
        position_id="position-1",
        latest_position_score={"reasoning": "", "total_score": 58, "grade": "BB"},
        coverage_context={
            "status": "draft",
            "summary": "Quick brief ready for AMD. Found 3 relevant headlines and started the deeper analysis.",
            "long_report": "Draft status text.",
            "source_count": 3,
        },
    )

    assert response is not None
    _assert_strict_rationale(response["reasoning"], "BB")
    assert "Quick brief ready" not in response["reasoning"]
    assert "started the deeper analysis" not in response["reasoning"]


# ── Phase 3: Limited Data truth — News Sentiment must not be fabricated ────────
def _usable_event(score=60, direction="improving", **over):
    e = {
        "sentiment_score": score,
        "sentiment_reason": "Real enriched reason.",
        "tldr": "A real factual summary of what happened.",
        "what_it_means": "A real implication for the company.",
        "key_implications": ["Implication one", "Implication two"],
        "headline_only": False,
        "paywalled": False,
        "rejection_reason": None,
        "analysis_status": "enriched",
        "significance": "minor",
        "risk_direction": direction,
        "recency_weight": 1.0,
        "source_weight": 1.0,
        "confidence": score,
    }
    e.update(over)
    return e


def _non_usable_event(**over):
    # headline-only / unenriched: no tldr/what_it_means/key_implications, sentiment None
    e = {
        "sentiment_score": None,
        "tldr": "",
        "what_it_means": "",
        "key_implications": [],
        "headline_only": True,
        "analysis_status": "headline_only",
        "significance": "minor",
        "risk_direction": "neutral",
        "confidence": None,
    }
    e.update(over)
    return e


class TestLimitedDataNewsSentiment:
    def test_zero_usable_articles_news_is_limited_data(self):
        r = risk_scorer.score_position_structural({"id": "p1"}, ticker_metadata={}, recent_events=[])
        assert r["news_sentiment"] is None

    def test_one_or_two_usable_articles_news_is_limited_data(self):
        for n in (1, 2):
            r = risk_scorer.score_position_structural(
                {"id": "p1"}, ticker_metadata={}, recent_events=[_usable_event() for _ in range(n)]
            )
            assert r["news_sentiment"] is None, f"{n} usable should be Limited Data"

    def test_three_usable_articles_get_real_news_sentiment(self):
        r = risk_scorer.score_position_structural(
            {"id": "p1"}, ticker_metadata={},
            recent_events=[_usable_event(score=80) for _ in range(3)],
        )
        assert r["news_sentiment"] is not None
        assert r["news_sentiment"] == 80

    def test_composite_excludes_limited_data_news_dimension(self):
        # news None -> composite is the mean of the other 4 dims only
        r = risk_scorer.score_position_structural({"id": "p1"}, ticker_metadata={}, recent_events=[])
        from app.pipeline.analysis_utils import calculate_weighted_score
        expected = calculate_weighted_score({
            "financial_health": r["financial_health"],
            "news_sentiment": None,
            "macro_exposure": r["macro_exposure"],
            "sector_exposure": r["sector_exposure"],
            "volatility": r["volatility"],
        })
        assert abs(r["total_score"] - round(expected, 1)) < 0.05
        assert r["news_sentiment"] is None

    def test_mrk_like_case_cannot_show_confident_news_from_non_usable_rows(self):
        # 15 non-usable rows (the MRK pattern) must NOT yield a confident score
        r = risk_scorer.score_position_structural(
            {"id": "p1"}, ticker_metadata={},
            recent_events=[_non_usable_event() for _ in range(15)],
        )
        assert r["news_sentiment"] is None

    def test_mixed_usable_and_non_usable_counts_only_usable(self):
        events = [_usable_event(score=70) for _ in range(2)] + [_non_usable_event() for _ in range(20)]
        r = risk_scorer.score_position_structural({"id": "p1"}, ticker_metadata={}, recent_events=events)
        assert r["news_sentiment"] is None  # only 2 usable < 3

    def test_deterministic_scores_news_none_below_threshold(self):
        result = risk_scorer._deterministic_dimension_scores(
            {"ticker": "MRK", "ticker_metadata": {}, "event_analyses": [_non_usable_event() for _ in range(15)]},
            portfolio_total_value=1.0,
        )
        assert result["news_sentiment"] is None

    def test_deterministic_scores_news_real_at_threshold(self):
        result = risk_scorer._deterministic_dimension_scores(
            {"ticker": "AMD", "ticker_metadata": {},
             "event_analyses": [_usable_event(direction="worsening", significance="major") for _ in range(3)]},
            portfolio_total_value=1.0,
        )
        assert result["news_sentiment"] is not None

    def test_build_event_analyses_filters_non_usable_rows(self):
        from app.services.ticker_cache_service import _build_event_analyses_from_news_rows
        rows = [
            {  # usable
                "id": "1", "sentiment_score": 65, "sentiment_reason": "Reason.",
                "tldr": "Summary.", "what_it_means": "Implication.",
                "key_implications": ["A", "B"], "analysis_status": "enriched",
                "extraction_status": "success", "title": "T", "published_at": "2026-05-17T00:00:00Z",
            },
            {  # headline-only -> excluded
                "id": "2", "sentiment_score": None, "tldr": "", "what_it_means": "",
                "key_implications": [], "headline_only": True, "analysis_status": "headline_only",
                "title": "T2",
            },
            {  # partial (missing what_it_means) -> excluded
                "id": "3", "sentiment_score": 50, "sentiment_reason": "R", "tldr": "S",
                "what_it_means": "", "key_implications": ["x"], "analysis_status": "partial",
                "title": "T3",
            },
        ]
        events = _build_event_analyses_from_news_rows(rows, ticker="TST", position_id="p1")
        assert len(events) == 1
        assert events[0]["sentiment_score"] == 65
        assert events[0]["sentiment_reason"] == "Reason."
