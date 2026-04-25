import os
import sys
import types
from datetime import datetime, timezone

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

from app.routes import digest


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.in_filters = {}
        self._insert_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, values):
        self.in_filters[key] = set(values)
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self._insert_payload is not None:
            created = {"id": f"{self.table_name}-new", **self._insert_payload}
            self.supabase.inserted.setdefault(self.table_name, []).append(created)
            return _FakeResult([created])

        rows = list(self.supabase.rows.get(self.table_name, []))
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self.in_filters.items():
            rows = [row for row in rows if row.get(key) in values]
        return _FakeResult(rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows
        self.inserted = {}

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_force_refresh_digest_uses_shared_pipeline_inputs(monkeypatch):
    supabase = _FakeSupabase(
        {
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "summary": "Analysis summary",
                    "methodology": "method",
                    "watch_items": ["watch item"],
                    "top_risks": ["risk item"],
                    "source_count": 4,
                    "major_event_count": 1,
                    "minor_event_count": 2,
                    "updated_at": "2026-04-24T01:00:00+00:00",
                }
            ],
            "user_preferences": [{"user_id": "user-1", "summary_length": "brief"}],
            "alerts": [
                {
                    "user_id": "user-1",
                    "position_ticker": "HOOD",
                    "type": "major_event",
                    "message": "HOOD moved on earnings",
                    "created_at": "2026-04-24T02:00:00+00:00",
                }
            ],
            "digests": [],
        }
    )

    positions = [
        {
            "id": "pos-1",
            "ticker": "HOOD",
            "sector": "Financials",
            "shares": 10,
            "total_score": 71,
            "risk_grade": "B",
            "current_price": 42.1,
        }
    ]

    compiled_calls = {}
    alerts_created = []

    monkeypatch.setattr(
        digest, "enrich_positions_with_ticker_cache", lambda data, _supabase: data
    )
    monkeypatch.setattr(
        digest,
        "get_metadata_map",
        lambda _supabase, tickers: {"HOOD": {"sector": "Financials"}},
    )
    monkeypatch.setattr(
        digest,
        "calculate_portfolio_risk_score",
        lambda **kwargs: {
            "portfolio_allocation_risk_score": 44,
            "confidence": 0.8,
            "concentration_risk": 55,
            "cluster_risk": 22,
            "correlation_risk": 11,
            "liquidity_mismatch": 5,
            "macro_stack_risk": 17,
            "factor_breakdown": {},
            "top_risk_drivers": [{"type": "concentration", "tickers": ["HOOD"]}],
            "danger_clusters": ["Fintech"],
        },
    )

    async def fake_fetch_cnbc_macro_rss(limit=12):
        return ["macro"]

    async def fake_classify_overnight_macro(macro_articles, current_positions):
        return {
            "overnight_macro": {
                "headlines": ["headline"],
                "themes": ["theme"],
                "brief": "Macro brief.",
            },
            "position_impacts": [],
            "what_matters_today": ["Fed speakers"],
        }

    async def fake_fetch_cnbc_sector_rss(sector_names, limit_per_sector=8):
        return ["sector"]

    async def fake_summarize_sector_overview(sector_articles_by_name):
        return {"tech": {"brief": "Sector brief."}}

    async def fake_create_analysis_run(user_id, triggered_by):
        return {"id": "run-new", "status": "queued"}

    async def fake_maybe_create_alert(
        _supabase, payload, dedupe_event_hash=None, dedupe_hours=24
    ):
        alerts_created.append(payload)
        return True

    monkeypatch.setattr(digest, "fetch_cnbc_macro_rss", fake_fetch_cnbc_macro_rss)
    monkeypatch.setattr(
        digest, "classify_overnight_macro", fake_classify_overnight_macro
    )
    monkeypatch.setattr(digest, "fetch_cnbc_sector_rss", fake_fetch_cnbc_sector_rss)
    monkeypatch.setattr(
        digest, "summarize_sector_overview", fake_summarize_sector_overview
    )
    monkeypatch.setattr(
        digest,
        "get_default_watchlist_detail",
        lambda _supabase, _user_id: {"items": [{"ticker": "HOOD"}]},
    )
    monkeypatch.setattr(
        digest,
        "_build_watchlist_alerts",
        lambda _alerts, _tickers: ["HOOD — Major Event: HOOD moved on earnings"],
    )
    monkeypatch.setattr(
        digest, "_compute_portfolio_grade", lambda current_positions: (68.4, "B")
    )

    async def fake_compile_portfolio_digest(*args, **kwargs):
        compiled_calls.update(kwargs)
        return {
            "content": "digest content",
            "overall_summary": "digest summary",
            "sections": {
                "overnight_macro": {
                    "headlines": ["headline"],
                    "themes": ["theme"],
                    "brief": "Macro brief.",
                },
                "sector_overview": [{"sector": "Financials", "brief": "Sector brief."}],
                "position_impacts": [{"ticker": "HOOD", "impact_summary": "Impact"}],
                "portfolio_impact": ["Concentration risk elevated."],
                "what_matters_today": ["Fed speakers"],
                "watchlist_alerts": ["HOOD alert"],
                "major_events": ["HOOD event"],
                "watch_list": ["HOOD watch"],
                "monitoring_notes": ["Note"],
                "portfolio_advice": ["Note"],
            },
        }

    monkeypatch.setattr(
        digest, "compile_portfolio_digest", fake_compile_portfolio_digest
    )
    monkeypatch.setattr(
        digest,
        "create_analysis_run",
        fake_create_analysis_run,
    )
    monkeypatch.setattr(digest, "_set_analysis_stage", lambda *args, **kwargs: None)
    monkeypatch.setattr(digest, "_maybe_create_alert", fake_maybe_create_alert)

    result = digest._build_force_refresh_digest(
        supabase,
        user_id="user-1",
        positions=positions,
        latest_saved_digest={"overall_grade": "C"},
        latest_run=None,
        now=datetime(2026, 4, 24, 15, 0, tzinfo=timezone.utc),
    )

    import asyncio

    response = asyncio.run(result)

    assert compiled_calls["portfolio_risk"]["concentration_risk"] == 55
    assert compiled_calls["summary_length"] == "brief"
    assert compiled_calls["macro_context"]["overnight_macro"]["brief"] == "Macro brief."
    assert compiled_calls["sector_context"]["tech"]["brief"] == "Sector brief."
    assert compiled_calls["watchlist_alerts"] == [
        "HOOD — Major Event: HOOD moved on earnings"
    ]
    assert response["analysis_run"]["id"] == "run-new"
    assert response["overall_grade"] == "B"
    assert response["overall_score"] == 68.4
    assert response["score_source"] == "digest"
    assert response["score_version"] == "run-new"
    assert response["digest"]["structured_sections"]["digest_version"] == 2
    assert any(alert["type"] == "digest_ready" for alert in alerts_created)


def test_force_refresh_digest_defaults_summary_length_to_standard_for_current_user(monkeypatch):
    supabase = _FakeSupabase(
        {
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "summary": "Analysis summary",
                    "methodology": "method",
                    "watch_items": ["watch item"],
                    "top_risks": ["risk item"],
                    "source_count": 4,
                    "major_event_count": 1,
                    "minor_event_count": 2,
                    "updated_at": "2026-04-24T01:00:00+00:00",
                }
            ],
            "user_preferences": [
                {"user_id": "other-user", "summary_length": "detailed"}
            ],
            "alerts": [],
            "digests": [],
        }
    )

    positions = [
        {
            "id": "pos-1",
            "ticker": "HOOD",
            "sector": "Financials",
            "shares": 10,
            "total_score": 71,
            "risk_grade": "B",
            "current_price": 42.1,
        }
    ]

    compiled_calls = {}

    monkeypatch.setattr(
        digest, "enrich_positions_with_ticker_cache", lambda data, _supabase: data
    )
    monkeypatch.setattr(
        digest,
        "get_metadata_map",
        lambda _supabase, tickers: {"HOOD": {"sector": "Financials"}},
    )
    monkeypatch.setattr(
        digest,
        "calculate_portfolio_risk_score",
        lambda **kwargs: {
            "portfolio_allocation_risk_score": 44,
            "confidence": 0.8,
            "concentration_risk": 55,
            "cluster_risk": 22,
            "correlation_risk": 11,
            "liquidity_mismatch": 5,
            "macro_stack_risk": 17,
            "factor_breakdown": {},
            "top_risk_drivers": [{"type": "concentration", "tickers": ["HOOD"]}],
            "danger_clusters": ["Fintech"],
        },
    )

    async def fake_fetch_cnbc_macro_rss(limit=12):
        return ["macro"]

    async def fake_classify_overnight_macro(macro_articles, current_positions):
        return {
            "overnight_macro": {
                "headlines": ["headline"],
                "themes": ["theme"],
                "brief": "Macro brief.",
            },
            "position_impacts": [],
            "what_matters_today": ["Fed speakers"],
        }

    async def fake_fetch_cnbc_sector_rss(sector_names, limit_per_sector=8):
        return ["sector"]

    async def fake_summarize_sector_overview(sector_articles_by_name):
        return {"tech": {"brief": "Sector brief."}}

    async def fake_create_analysis_run(user_id, triggered_by):
        return {"id": "run-new", "status": "queued"}

    async def fake_maybe_create_alert(
        _supabase, payload, dedupe_event_hash=None, dedupe_hours=24
    ):
        return True

    monkeypatch.setattr(digest, "fetch_cnbc_macro_rss", fake_fetch_cnbc_macro_rss)
    monkeypatch.setattr(
        digest, "classify_overnight_macro", fake_classify_overnight_macro
    )
    monkeypatch.setattr(digest, "fetch_cnbc_sector_rss", fake_fetch_cnbc_sector_rss)
    monkeypatch.setattr(
        digest, "summarize_sector_overview", fake_summarize_sector_overview
    )
    monkeypatch.setattr(
        digest,
        "get_default_watchlist_detail",
        lambda _supabase, _user_id: {"items": [{"ticker": "HOOD"}]},
    )
    monkeypatch.setattr(
        digest,
        "_build_watchlist_alerts",
        lambda _alerts, _tickers: [],
    )
    monkeypatch.setattr(
        digest, "_compute_portfolio_grade", lambda current_positions: (68.4, "B")
    )

    async def fake_compile_portfolio_digest(*args, **kwargs):
        compiled_calls.update(kwargs)
        return {
            "content": "digest content",
            "overall_summary": "digest summary",
            "sections": {
                "overnight_macro": {
                    "headlines": ["headline"],
                    "themes": ["theme"],
                    "brief": "Macro brief.",
                },
                "sector_overview": [{"sector": "Financials", "brief": "Sector brief."}],
                "position_impacts": [{"ticker": "HOOD", "impact_summary": "Impact"}],
                "portfolio_impact": ["Concentration risk elevated."],
                "what_matters_today": ["Fed speakers"],
                "watchlist_alerts": [],
                "major_events": [],
                "watch_list": [],
                "monitoring_notes": [],
                "portfolio_advice": [],
            },
        }

    monkeypatch.setattr(
        digest, "compile_portfolio_digest", fake_compile_portfolio_digest
    )
    monkeypatch.setattr(
        digest,
        "create_analysis_run",
        fake_create_analysis_run,
    )
    monkeypatch.setattr(digest, "_set_analysis_stage", lambda *args, **kwargs: None)
    monkeypatch.setattr(digest, "_maybe_create_alert", fake_maybe_create_alert)

    result = digest._build_force_refresh_digest(
        supabase,
        user_id="user-1",
        positions=positions,
        latest_saved_digest={"overall_grade": "C"},
        latest_run=None,
        now=datetime(2026, 4, 24, 15, 0, tzinfo=timezone.utc),
    )

    import asyncio

    response = asyncio.run(result)

    assert compiled_calls["summary_length"] == "standard"
    assert response["digest"]["structured_sections"]["digest_version"] == 2
