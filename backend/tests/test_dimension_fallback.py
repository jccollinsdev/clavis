import sys
import types

_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

_fake_openai_module = types.ModuleType("openai")


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


_fake_openai_module.OpenAI = _FakeOpenAI
sys.modules.setdefault("openai", _fake_openai_module)

from app.services.ticker_cache_service import _shared_risk_dimensions, _first_non_none


class TestFirstNonNone:
    def test_returns_first_non_none(self):
        assert _first_non_none(None, None, 42) == 42

    def test_returns_none_if_all_none(self):
        assert _first_non_none(None, None, None) is None

    def test_preserves_zero(self):
        assert _first_non_none(None, 0, 99) == 0

    def test_preserves_zero_first(self):
        assert _first_non_none(0, 99, None) == 0


class TestSharedRiskDimensions:
    def test_v2_columns_take_priority(self):
        snapshot = {
            "financial_health": 80,
            "news_sentiment_dim": 70,
            "macro_exposure_dim": 60,
            "sector_exposure": 55,
            "volatility": 65,
            "factor_breakdown": {"ai_dimensions": {
                "financial_health": 10,
                "news_sentiment": 10,
                "macro_exposure": 10,
                "sector_exposure": 10,
                "volatility": 10,
            }},
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["financial_health"] == 80
        assert result["news_sentiment"] == 70
        assert result["macro_exposure"] == 60
        assert result["sector_exposure"] == 55
        assert result["volatility"] == 65

    def test_falls_back_to_ai_dimensions_new_names(self):
        snapshot = {
            "factor_breakdown": {"ai_dimensions": {
                "financial_health": 62,
                "news_sentiment": 50,
                "macro_exposure": 67,
                "sector_exposure": 68,
                "volatility": 67,
            }},
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["financial_health"] == 62
        assert result["news_sentiment"] == 50
        assert result["macro_exposure"] == 67
        assert result["sector_exposure"] == 68
        assert result["volatility"] == 67

    def test_falls_back_to_old_dimension_names(self):
        snapshot = {
            "factor_breakdown": {"ai_dimensions": {
                "position_sizing": 82,
                "news_sentiment": 50,
                "macro_exposure": 62,
                "volatility_trend": 72,
            }},
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["financial_health"] == 82, "position_sizing should map to financial_health"
        assert result["news_sentiment"] == 50
        assert result["macro_exposure"] == 62
        assert result["sector_exposure"] is None, "sector_exposure has no old name fallback"
        assert result["volatility"] == 72, "volatility_trend should map to volatility"

    def test_new_names_take_priority_over_old_names(self):
        snapshot = {
            "factor_breakdown": {"ai_dimensions": {
                "financial_health": 40,
                "position_sizing": 82,
                "volatility": 67,
                "volatility_trend": 72,
            }},
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["financial_health"] == 40, "new name financial_health takes priority"
        assert result["volatility"] == 67, "new name volatility takes priority"

    def test_v2_column_zero_is_preserved(self):
        snapshot = {
            "news_sentiment_dim": 0,
            "factor_breakdown": {"ai_dimensions": {
                "news_sentiment": 50,
            }},
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["news_sentiment"] == 0, "zero score should not be overwritten by fallback"

    def test_empty_snapshot_returns_nones(self):
        result = _shared_risk_dimensions(None)
        assert result["financial_health"] is None
        assert result["news_sentiment"] is None
        assert result["macro_exposure"] is None
        assert result["sector_exposure"] is None
        assert result["volatility"] is None

    def test_deterministic_fallback_snapshot(self):
        snapshot = {
            "factor_breakdown": {
                "ai_dimensions": {
                    "position_sizing": 50,
                    "news_sentiment": 50,
                    "macro_exposure": 50,
                    "volatility_trend": 50,
                },
            },
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["financial_health"] == 50
        assert result["news_sentiment"] == 50
        assert result["macro_exposure"] == 50
        assert result["sector_exposure"] is None
        assert result["volatility"] == 50

    def test_mixed_old_and_new_names_in_ai_dimensions(self):
        snapshot = {
            "factor_breakdown": {"ai_dimensions": {
                "position_sizing": 70,
                "news_sentiment": 55,
                "macro_exposure": 45,
                "sector_exposure": 60,
                "volatility_trend": 40,
            }},
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["financial_health"] == 70
        assert result["news_sentiment"] == 55
        assert result["macro_exposure"] == 45
        assert result["sector_exposure"] == 60
        assert result["volatility"] == 40

    def test_shared_cache_v1_snapshot_no_ai_dimensions(self):
        snapshot = {
            "safety_score": 63,
            "factor_breakdown": {
                "event_count": 2,
                "volatility_score": 45,
                "market_cap_contribution": 25,
            },
        }
        result = _shared_risk_dimensions(snapshot)
        assert result["financial_health"] is None
        assert result["news_sentiment"] is None
        assert result["macro_exposure"] is None
        assert result["sector_exposure"] is None
        assert result["volatility"] is None