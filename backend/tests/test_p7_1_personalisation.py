import asyncio
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.com")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "dummy")
os.environ.setdefault("SUPABASE_JWT_SECRET", "dummy")
os.environ.setdefault("MINIMAX_API_KEY", "dummy")

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

from app.pipeline import portfolio_compiler
from app.services import personalisation


class _Query:
    def __init__(self, db, table_name: str):
        self.db = db
        self.table_name = table_name
        self.rows = list(db.tables.get(table_name, []))
        self._limit = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.rows = [row for row in self.rows if row.get(field) == value]
        return self

    def in_(self, field, values):
        allowed = set(values)
        self.rows = [row for row in self.rows if row.get(field) in allowed]
        return self

    def order(self, field, desc=False, **_kwargs):
        self.rows = sorted(self.rows, key=lambda row: row.get(field) or "", reverse=desc)
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        rows = self.rows[: self._limit] if self._limit is not None else self.rows
        return SimpleNamespace(data=rows)


class _DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, table_name: str):
        return _Query(self, table_name)


def _sample_db():
    return _DB(
        {
            "positions": [
                {
                    "user_id": "user-1",
                    "ticker": "NVDA",
                    "shares": 42,
                    "current_price": 900.0,
                }
            ],
            "ticker_metadata": [{"ticker": "NVDA", "price": 900.0}],
            "portfolio_risk_snapshots": [
                {
                    "user_id": "user-1",
                    "as_of_date": "2026-05-25",
                    "composite_score": 81,
                },
                {
                    "user_id": "user-1",
                    "as_of_date": "2026-05-24",
                    "composite_score": 78,
                },
            ],
            "shared_ticker_events": [
                {
                    "id": "evt-1",
                    "ticker": "NVDA",
                    "title": "NVDA update",
                    "summary": "A material data-center development.",
                    "tldr": "Demand stayed firm.",
                    "what_it_means": "Risk stayed centered on valuation and concentration.",
                    "key_implications": ["Data center demand held up"],
                    "published_at": "2026-05-25T08:00:00+00:00",
                }
            ],
            "digests": [],
        }
    )


def setup_function():
    personalisation._NARRATIVE_CACHE.clear()
    personalisation._DAILY_BUDGET_SPEND.clear()


def test_structural_template_renders_from_positions_and_snapshot_state(monkeypatch):
    monkeypatch.setenv("MINIMAX_PERSONALISATION_ENABLED", "false")
    monkeypatch.setenv("MINIMAX_DAILY_BUDGET", "0")

    result = personalisation.personalise_articles_for_user(
        "user-1",
        ["evt-1"],
        supabase=_sample_db(),
    )

    assert result["evt-1"]["structural"] == (
        "You hold 42 sh of NVDA (100.0% of book). "
        "This change moves your portfolio composite from 78 → 81."
    )


def test_llm_disabled_returns_structural_only(monkeypatch):
    monkeypatch.setenv("MINIMAX_PERSONALISATION_ENABLED", "false")
    monkeypatch.setenv("MINIMAX_DAILY_BUDGET", "5")

    result = personalisation.personalise_articles_for_user(
        "user-1",
        ["evt-1"],
        supabase=_sample_db(),
    )

    assert result["evt-1"]["narrative"] is None


def test_banned_vocabulary_rejects_llm_output_and_falls_back(monkeypatch):
    monkeypatch.setenv("MINIMAX_PERSONALISATION_ENABLED", "true")
    monkeypatch.setenv("MINIMAX_DAILY_BUDGET", "5")

    with patch.object(
        personalisation,
        "chatcompletion_text",
        return_value="Research suggests momentum is building.",
    ):
        result = personalisation.personalise_articles_for_user(
            "user-1",
            ["evt-1"],
            supabase=_sample_db(),
        )

    assert result["evt-1"]["narrative"] is None
    assert "You hold 42 sh of NVDA" in result["evt-1"]["structural"]


def test_budget_exhaustion_returns_structural_only_without_error(monkeypatch):
    monkeypatch.setenv("MINIMAX_PERSONALISATION_ENABLED", "true")
    monkeypatch.setenv("MINIMAX_DAILY_BUDGET", "1")
    personalisation._DAILY_BUDGET_SPEND[personalisation._today_key()] = 1

    with patch.object(
        personalisation,
        "chatcompletion_text",
        side_effect=AssertionError("LLM should not be called when budget is exhausted"),
    ):
        result = personalisation.personalise_articles_for_user(
            "user-1",
            ["evt-1"],
            supabase=_sample_db(),
        )

    assert result["evt-1"]["narrative"] is None


def test_cache_hit_reuses_identical_user_event_composite_triplet(monkeypatch):
    monkeypatch.setenv("MINIMAX_PERSONALISATION_ENABLED", "true")
    monkeypatch.setenv("MINIMAX_DAILY_BUDGET", "5")

    with patch.object(
        personalisation,
        "chatcompletion_text",
        return_value="The article kept the main risk signal focused on valuation pressure.",
    ) as mocked_llm:
        first = personalisation.personalise_articles_for_user(
            "user-1",
            ["evt-1"],
            supabase=_sample_db(),
        )
        second = personalisation.personalise_articles_for_user(
            "user-1",
            ["evt-1"],
            supabase=_sample_db(),
        )

    assert mocked_llm.call_count == 1
    assert first == second


def test_personalisation_filters_none_key_implications(monkeypatch):
    monkeypatch.setenv("MINIMAX_PERSONALISATION_ENABLED", "true")
    monkeypatch.setenv("MINIMAX_DAILY_BUDGET", "5")

    sample_db = _sample_db()
    sample_db.tables["shared_ticker_events"][0]["key_implications"] = [
        None,
        "Data center demand held up",
        "",
    ]
    captured = {}

    def fake_chatcompletion_text(**kwargs):
        captured["prompt"] = kwargs["messages"][1]["content"]
        return "Direct, portfolio-specific note."

    with patch.object(
        personalisation,
        "chatcompletion_text",
        side_effect=fake_chatcompletion_text,
    ):
        result = personalisation.personalise_articles_for_user(
            "user-1",
            ["evt-1"],
            supabase=sample_db,
        )

    assert "None" not in captured["prompt"]
    assert "Data center demand held up" in captured["prompt"]
    assert result["evt-1"]["narrative"] == "Direct, portfolio-specific note."


def test_compile_portfolio_digest_stores_personalised_articles_section(monkeypatch):
    monkeypatch.setattr(
        portfolio_compiler,
        "chatcompletion_text",
        lambda **_kwargs: '{"content":"digest","overall_summary":"summary","sections":{"overnight_macro":{"headlines":[],"themes":[],"brief":""},"sector_overview":[],"position_impacts":[],"portfolio_impact":[],"what_matters_today":[],"watchlist_alerts":[],"major_events":[],"watch_list":[],"monitoring_notes":[],"portfolio_advice":[]}}',
    )
    monkeypatch.setattr(
        "app.services.personalisation.personalise_articles_for_user",
        lambda user_id, event_ids, supabase: {
            "evt-1": {
                "structural": "You hold 42 sh of NVDA (100.0% of book). This change moves your portfolio composite from 78 → 81.",
                "narrative": None,
                "generated_at": "2026-05-25T09:00:00+00:00",
            }
        },
    )

    digest = asyncio.run(
        portfolio_compiler.compile_portfolio_digest(
            [{"ticker": "NVDA", "grade": "A", "total_score": 81}],
            "A",
            supabase=object(),
            user_id="user-1",
            event_ids=["evt-1"],
        )
    )

    assert digest["sections"]["personalised_articles"]["evt-1"]["generated_at"] == "2026-05-25T09:00:00+00:00"
