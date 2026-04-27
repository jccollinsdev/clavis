import sys
import types
import asyncio


_fake_openai_module = types.ModuleType("openai")


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


_fake_openai_module.OpenAI = _FakeOpenAI
sys.modules.setdefault("openai", _fake_openai_module)

from app.pipeline import risk_scorer
from app.services.ticker_cache_service import build_risk_score_response


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
                "news_sentiment": 50,
                "macro_exposure": 50,
                "position_sizing": 50,
                "volatility_trend": 50,
            }
        )
        is True
    )
    assert (
        risk_scorer.has_suspicious_neutral_scores(
            {
                "news_sentiment": 50,
                "macro_exposure": 50,
                "position_sizing": 50,
                "volatility_trend": 42,
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
            '{"news_sentiment": 52, "macro_exposure": 49, "position_sizing": 61, "volatility_trend": 46, "grade": "C", "reasoning": "", "dimension_rationale": {}}'
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
    # Rationale must be investor-facing, not dimension-math
    assert "Company-specific news (" not in result["reasoning"]
    assert "adds risk at" not in result["reasoning"]
    assert result["coverage_state"] == "provisional"
    assert result["is_provisional"] is True


def test_build_risk_score_response_surfaces_coverage_context():
    response = build_risk_score_response(
        {
            "id": "snapshot-1",
            "safety_score": 58,
            "grade": "C",
            "source_count": 0,
            "analysis_as_of": "2026-04-21T18:00:00+00:00",
        },
        position_id="position-1",
        latest_position_score={"reasoning": "", "total_score": 58, "grade": "C"},
        coverage_context={
            "source_count": 0,
            "coverage_state": "provisional",
            "coverage_note": "Confidence is low because the score leans mostly on ticker metadata and cached context.",
            "is_provisional": True,
        },
    )

    assert response["coverage_state"] == "provisional"
    assert response["is_provisional"] is True
    assert response["source_count"] == 0
    assert response["reasoning"]
    # Rationale must be investor-facing, not dimension-math
    assert "Macro/sector exposure (" not in response["reasoning"]
    assert "adds risk at" not in response["reasoning"]


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
