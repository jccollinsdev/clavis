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

from app.services import ticker_cache_service


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.in_filters = {}

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

    def execute(self):
        rows = list(self.supabase.rows.get(self.table_name, []))
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self.in_filters.items():
            rows = [row for row in rows if row.get(key) in values]
        return _FakeResult(rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_get_ticker_detail_bundle_exposes_analysis_state(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "HOOD",
                    "company_name": "Robinhood Markets",
                    "exchange": "NASDAQ",
                    "sector": "Financials",
                    "industry": "Capital Markets",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "HOOD",
                    "company_name": "Robinhood Markets",
                    "price": 42.1,
                    "price_as_of": "2026-04-24T00:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "HOOD",
                    "grade": "B",
                    "safety_score": 71,
                    "analysis_as_of": "2026-04-24T01:00:00+00:00",
                    "coverage_state": "substantive",
                    "news_summary": "Coverage is substantive.",
                    "reasoning": "Coverage is substantive.",
                    "dimension_rationale": {},
                }
            ],
            "ticker_news_cache": [
                {
                    "ticker": "HOOD",
                    "headline": "Robinhood expands product line",
                    "summary": "New product coverage.",
                    "source": "Reuters",
                    "url": "https://example.com/article",
                    "sentiment": "positive",
                    "published_at": "2026-04-24T02:00:00+00:00",
                    "processed_at": "2026-04-24T02:05:00+00:00",
                }
            ],
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": "user-1",
                    "ticker": "HOOD",
                    "current_price": 42.1,
                    "risk_grade": "B",
                    "total_score": 71,
                    "previous_grade": "C",
                }
            ],
            "risk_scores": [
                {
                    "position_id": "pos-1",
                    "safety_score": 71,
                    "coverage_state": "substantive",
                    "calculated_at": "2026-04-24T01:05:00+00:00",
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-1",
                    "status": "ready",
                    "coverage_state": "substantive",
                    "updated_at": "2026-04-24T01:04:00+00:00",
                }
            ],
            "analysis_runs": [
                {
                    "id": "run-1",
                    "user_id": "user-1",
                    "target_position_id": "pos-1",
                    "status": "completed",
                    "started_at": "2026-04-24T01:00:00+00:00",
                    "completed_at": "2026-04-24T01:10:00+00:00",
                }
            ],
            "ticker_refresh_jobs": [
                {
                    "id": "job-1",
                    "ticker": "HOOD",
                    "job_type": "manual_refresh",
                    "status": "completed",
                    "started_at": "2026-04-24T01:20:00+00:00",
                    "completed_at": "2026-04-24T01:22:00+00:00",
                    "error_message": None,
                }
            ],
            "alerts": [],
            "watchlists": [
                {
                    "id": "watchlist-1",
                    "user_id": "user-1",
                    "name": "Watchlist",
                    "is_default": True,
                }
            ],
            "watchlist_items": [
                {"id": "item-1", "watchlist_id": "watchlist-1", "ticker": "HOOD"}
            ],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "HOOD")

    assert result["source"] == "user"
    assert result["coverage_state"] == "substantive"
    assert result["analysis_state"]["status"] == "fresh"
    assert result["analysis_state"]["latest_refresh_status"] == "completed"
    assert result["latest_analysis_run"]["id"] == "run-1"
    assert result["latest_refresh_job"]["id"] == "job-1"
    assert result["current_score"]["score_source"] == "user"
    assert result["current_score"]["score_as_of"] == "2026-04-24T01:05:00+00:00"
    assert result["current_score"]["score_version"] is None
    assert result["position"]["score_source"] == "user"
    assert result["freshness"]["news_as_of"] == "2026-04-24T02:00:00+00:00"
    assert result["freshness"]["last_news_refresh_at"] == "2026-04-24T02:05:00+00:00"
    assert result["freshness"]["news_refresh_status"] == "completed"


def test_get_ticker_detail_bundle_prefers_active_analysis_run(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "HOOD",
                    "company_name": "Robinhood Markets",
                    "exchange": "NASDAQ",
                    "sector": "Financials",
                    "industry": "Capital Markets",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "HOOD",
                    "company_name": "Robinhood Markets",
                    "price": 42.1,
                    "price_as_of": "2026-04-24T00:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "HOOD",
                    "grade": "B",
                    "safety_score": 71,
                    "analysis_as_of": "2026-04-24T01:00:00+00:00",
                    "coverage_state": "substantive",
                    "news_summary": "Coverage is substantive.",
                    "reasoning": "Coverage is substantive.",
                    "dimension_rationale": {},
                }
            ],
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": "user-1",
                    "ticker": "HOOD",
                    "current_price": 42.1,
                    "risk_grade": "B",
                    "total_score": 71,
                    "previous_grade": "C",
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-old",
                    "status": "ready",
                    "coverage_state": "substantive",
                    "updated_at": "2026-04-24T01:04:00+00:00",
                }
            ],
            "analysis_runs": [
                {
                    "id": "run-old",
                    "user_id": "user-1",
                    "target_position_id": "pos-1",
                    "status": "completed",
                    "created_at": "2026-04-24T01:00:00+00:00",
                    "started_at": "2026-04-24T01:00:00+00:00",
                    "completed_at": "2026-04-24T01:10:00+00:00",
                },
                {
                    "id": "run-new",
                    "user_id": "user-1",
                    "target_position_id": "pos-1",
                    "status": "queued",
                    "created_at": "2026-04-24T02:00:00+00:00",
                    "started_at": None,
                    "completed_at": None,
                },
            ],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
            "risk_scores": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "HOOD")

    assert result["latest_analysis_run"]["id"] == "run-new"
    assert result["analysis_state"]["status"] == "running"
