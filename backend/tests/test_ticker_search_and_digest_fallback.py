import asyncio
import sys
import types
from unittest.mock import patch


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

from app.pipeline.portfolio_compiler import compile_portfolio_digest
from app.services.ticker_cache_service import search_supported_tickers


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.table_name == "ticker_universe":
            return _FakeResult(self.supabase.universe_rows)
        return _FakeResult([])


class _FakeSupabase:
    def __init__(self, universe_rows):
        self.universe_rows = universe_rows

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_search_supported_tickers_keeps_exact_match_first(monkeypatch):
    supabase = _FakeSupabase(
        [
            {
                "ticker": "HOOD",
                "company_name": "Robinhood Markets",
                "exchange": "NASDAQ",
                "sector": "Financials",
                "industry": "Capital Markets",
                "priority_rank": 2,
            },
            {
                "ticker": "HOODX",
                "company_name": "Hood Extended",
                "exchange": "NASDAQ",
                "sector": "Financials",
                "industry": "Capital Markets",
                "priority_rank": 3,
            },
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "exchange": "NASDAQ",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "priority_rank": 1,
            },
        ]
    )

    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    monkeypatch.setattr(
        "app.services.ticker_cache_service.get_metadata_map",
        lambda _supabase, _tickers: {},
    )
    monkeypatch.setattr(
        "app.services.ticker_cache_service.get_latest_risk_snapshot_map",
        lambda _supabase, _tickers: {},
    )

    results = search_supported_tickers(supabase, "hood", limit=10)

    assert results[0]["ticker"] == "HOOD"


def test_compile_portfolio_digest_falls_back_to_structured_sector_and_position_fields():
    positions = [
        {
            "ticker": "HOOD",
            "sector": "Financials",
            "grade": "D",
            "previous_grade": "B",
            "total_score": 42,
            "summary": "Risk remains elevated after a volatile earnings print.",
            "watch_items": ["Margin pressure", "Funding mix"],
            "top_risks": ["Funding stress", "Higher volatility"],
            "dimension_breakdown": {
                "news_sentiment": "Weak",
                "volatility_trend": "High",
            },
            "shares": 10,
            "confidence": 0.8,
            "structural_base_score": 45,
        }
    ]

    with patch(
        "app.pipeline.portfolio_compiler.chatcompletion_text",
        side_effect=RuntimeError("boom"),
    ):
        digest = asyncio.run(compile_portfolio_digest(positions, "D"))

    assert digest["sections"]["sector_overview"]
    impact = digest["sections"]["position_impacts"][0]
    assert impact["watch_items"] == ["Margin pressure", "Funding mix"]
    assert impact["top_risks"] == ["Funding stress", "Higher volatility"]
    assert impact["dimension_breakdown"] == {
        "news_sentiment": "Weak",
        "volatility_trend": "High",
    }
    assert digest["sections"]["what_matters_today"]
    assert digest["sections"]["what_matters_today"][0]["urgency"] == "low"
    assert "No immediate portfolio-level risk driver found today" in digest["content"]


def test_compile_portfolio_digest_preserves_real_urgent_items():
    positions = [
        {
            "ticker": "HOOD",
            "sector": "Financials",
            "grade": "B",
            "previous_grade": "B",
            "total_score": 71,
            "summary": "No material change.",
            "watch_items": ["Rates watch"],
            "top_risks": ["Macro watch"],
            "dimension_breakdown": {"macro_exposure": "Sensitive"},
            "shares": 10,
            "confidence": 0.8,
            "structural_base_score": 45,
        }
    ]

    with patch(
        "app.pipeline.portfolio_compiler.chatcompletion_text",
        return_value='{"content": "digest content", "overall_summary": "digest summary", "sections": {"overnight_macro": {"headlines": ["headline"], "themes": ["theme"], "brief": "Macro brief."}, "sector_overview": [{"sector": "Financials", "brief": "Sector brief."}], "position_impacts": [{"ticker": "HOOD", "impact_summary": "Impact"}], "portfolio_impact": ["Concentration risk elevated."], "what_matters_today": [{"catalyst": "Earnings release could move HOOD after hours.", "impacted_positions": ["HOOD"], "urgency": "high"}], "watchlist_alerts": ["HOOD alert"], "major_events": ["HOOD event"], "watch_list": ["HOOD watch"], "monitoring_notes": ["Note"], "portfolio_advice": ["Note"]}}',
    ):
        digest = asyncio.run(compile_portfolio_digest(positions, "B"))

    assert digest["sections"]["what_matters_today"][0]["urgency"] == "high"
    assert digest["sections"]["what_matters_today"][0]["impacted_positions"] == ["HOOD"]
