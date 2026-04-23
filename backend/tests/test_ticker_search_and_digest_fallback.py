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
