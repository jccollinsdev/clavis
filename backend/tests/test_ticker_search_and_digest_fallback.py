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


# ---------------------------------------------------------------------------
# Ticker search correctness tests (regression for AMD/NVDA autocomplete bug)
# ---------------------------------------------------------------------------

def _make_universe():
    """Minimal S&P 500 subset covering the regression cases."""
    return [
        {
            "ticker": "AMD",
            "company_name": "Advanced Micro Devices",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Semiconductors",
            "index_membership": "SP500",
            "is_active": True,
            "priority_rank": 7,
        },
        {
            "ticker": "NVDA",
            "company_name": "Nvidia",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Semiconductors",
            "index_membership": "SP500",
            "is_active": True,
            "priority_rank": 345,
        },
        {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "index_membership": "SP500",
            "is_active": True,
            "priority_rank": 39,
        },
        {
            "ticker": "AMZN",
            "company_name": "Amazon.com Inc.",
            "exchange": "NASDAQ",
            "sector": "Consumer Discretionary",
            "industry": "Internet Retail",
            "index_membership": "SP500",
            "is_active": True,
            "priority_rank": 50,
        },
    ]


def _patched_search(monkeypatch, universe):
    supabase = _FakeSupabase(universe)
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _: None,
    )
    monkeypatch.setattr(
        "app.services.ticker_cache_service.get_metadata_map",
        lambda _sb, _tickers: {},
    )
    monkeypatch.setattr(
        "app.services.ticker_cache_service.get_latest_risk_snapshot_map",
        lambda _sb, _tickers: {},
    )
    return supabase


def test_search_amd_returns_amd(monkeypatch):
    """AMD must appear when searching 'AMD'."""
    supabase = _patched_search(monkeypatch, _make_universe())
    results = search_supported_tickers(supabase, "AMD", limit=10)
    tickers = [r["ticker"] for r in results]
    assert "AMD" in tickers
    assert results[0]["ticker"] == "AMD"  # exact match is first
    assert results[0]["is_supported"] is True


def test_search_nvda_returns_nvda(monkeypatch):
    """NVDA must appear when searching 'NVDA'."""
    supabase = _patched_search(monkeypatch, _make_universe())
    results = search_supported_tickers(supabase, "NVDA", limit=10)
    tickers = [r["ticker"] for r in results]
    assert "NVDA" in tickers
    assert results[0]["ticker"] == "NVDA"
    assert results[0]["is_supported"] is True


def test_search_is_case_insensitive(monkeypatch):
    """Lowercase query 'amd' must find AMD."""
    supabase = _patched_search(monkeypatch, _make_universe())
    results = search_supported_tickers(supabase, "amd", limit=10)
    assert any(r["ticker"] == "AMD" for r in results)


def test_search_by_company_name(monkeypatch):
    """Searching by company name fragment must find the ticker."""
    supabase = _patched_search(monkeypatch, _make_universe())
    results = search_supported_tickers(supabase, "advanced micro", limit=10)
    assert any(r["ticker"] == "AMD" for r in results)

    results2 = search_supported_tickers(supabase, "nvidia", limit=10)
    assert any(r["ticker"] == "NVDA" for r in results2)


def test_search_all_results_have_is_supported_true(monkeypatch):
    """Every result from search must carry is_supported=True."""
    supabase = _patched_search(monkeypatch, _make_universe())
    results = search_supported_tickers(supabase, "a", limit=20)
    assert results  # non-empty
    for r in results:
        assert r["is_supported"] is True


def test_search_empty_query_returns_all(monkeypatch):
    """Empty query returns all active tickers (up to limit)."""
    supabase = _patched_search(monkeypatch, _make_universe())
    results = search_supported_tickers(supabase, "", limit=20)
    assert len(results) == len(_make_universe())


def test_search_exact_match_ranks_first_over_prefix(monkeypatch):
    """Exact ticker match must outrank prefix match in results."""
    universe = _make_universe() + [
        {
            "ticker": "AMDA",
            "company_name": "Amedra Corp",
            "exchange": "NASDAQ",
            "sector": "Healthcare",
            "industry": "Biotechnology",
            "index_membership": "SP500",
            "is_active": True,
            "priority_rank": 1,  # higher priority_rank than AMD
        }
    ]
    supabase = _patched_search(monkeypatch, universe)
    results = search_supported_tickers(supabase, "AMD", limit=10)
    assert results[0]["ticker"] == "AMD"
