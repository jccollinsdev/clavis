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

    assert result["source"] == "shared"
    assert result["coverage_state"] == "substantive"
    assert result["analysis_state"]["status"] == "ready"
    assert result["analysis_state"]["latest_refresh_status"] == "completed"
    assert result["latest_analysis_run"]["id"] == "run-1"
    assert result["latest_refresh_job"]["id"] == "job-1"
    assert result["current_score"]["score_source"] == "shared"
    assert result["current_score"]["score_as_of"] == "2026-04-24T01:00:00+00:00"
    assert result["current_score"]["score_version"] is None
    assert result["position"]["score_source"] == "shared"
    assert result["current_analysis"]["driver_cards_state"] == "pending"
    assert result["current_analysis"]["driver_cards"] == []
    assert result["current_analysis"].get("driver_cards_source") == "generated"
    assert result["shared_analysis"]["summary"]["ticker"] == "HOOD"
    assert result["portfolio_overlay"]["position_id"] == "pos-1"
    assert result["freshness"]["news_as_of"] == "2026-04-24T02:00:00+00:00"
    assert result["freshness"]["last_news_refresh_at"] == "2026-04-24T02:05:00+00:00"
    assert result["freshness"]["news_refresh_status"] == "completed"


def test_get_default_watchlist_detail_uses_recent_news_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
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
                    "id": f"news-{idx}",
                    "ticker": "HOOD",
                    "headline": f"HOOD news {idx}",
                    "summary": f"Summary {idx}",
                    "source": "Reuters",
                    "url": f"https://example.com/{idx}",
                    "sentiment": "neutral",
                    "published_at": f"2026-04-24T0{idx}:00:00+00:00",
                    "processed_at": f"2026-04-24T0{idx}:05:00+00:00",
                }
                for idx in range(5)
            ],
            "positions": [],
            "event_analyses": [],
        }
    )

    result = ticker_cache_service.get_default_watchlist_detail(supabase, "user-1")

    items = result["items"]
    assert len(items) == 1
    assert len(items[0]["latest_event_analyses"]) == 5
    assert items[0]["latest_event_analyses"][0]["title"] == "HOOD news 0"


def test_get_ticker_detail_bundle_normalizes_explicit_event_analysis_fields(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "industry": "Semiconductors",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "price": 155.0,
                    "price_as_of": "2026-04-24T00:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "AMD",
                    "grade": "C",
                    "safety_score": 55,
                    "analysis_as_of": "2026-04-24T01:00:00+00:00",
                    "coverage_state": "substantive",
                    "news_summary": "Coverage is substantive.",
                    "reasoning": "Coverage is substantive.",
                    "dimension_rationale": {},
                }
            ],
            "ticker_news_cache": [
                {
                    "ticker": "AMD",
                    "headline": "AMD supply deal offsets shortage risk",
                    "summary": "AMD signed a new supply agreement that expands access to wafers.",
                    "source": "Reuters",
                    "url": "https://example.com/article",
                    "tldr": "Supply access improves execution visibility.",
                    "what_it_means": "The deal reduces near-term supply constraints and supports manufacturing continuity.",
                    "key_implications": [
                        "Supply risk eases",
                        "Execution visibility improves",
                    ],
                    "follow_up_notes": ["Watch for margin impact in the next update"],
                    "source_article_link": "https://example.com/article",
                    "tags": ["supply", "manufacturing"],
                    "sentiment": "positive",
                    "published_at": "2026-04-24T02:00:00+00:00",
                    "processed_at": "2026-04-24T00:05:00+00:00",
                }
            ],
            "positions": [],
            "risk_scores": [],
            "position_analyses": [],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "alerts": [],
            "watchlists": [
                {
                    "id": "watchlist-1",
                    "user_id": "user-1",
                    "name": "Watchlist",
                    "is_default": True,
                }
            ],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMD")

    event = result["latest_event_analyses"][0]
    assert event["title"] == "AMD supply deal offsets shortage risk"
    assert event["source"] == "Reuters"
    assert event["published_at"] == "2026-04-24T02:00:00+00:00"
    assert event["tldr"] is None
    assert event["what_it_means"] is None
    assert event["key_implications"] == []
    assert event["follow_up_notes"] == []
    assert event["tags"] == []


def test_get_ticker_detail_bundle_backfills_legacy_driver_cards(monkeypatch):
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
            "event_analyses": [
                {
                    "id": "ev-1",
                    "analysis_run_id": "run-1",
                    "position_id": "pos-1",
                    "event_hash": "hash-1",
                    "title": "Robinhood expands crypto trading to new markets",
                    "summary": "The rollout may increase engagement among active traders.",
                    "long_analysis": "Robinhood expands crypto trading access to additional markets, which could broaden engagement.",
                    "source": "Reuters",
                    "source_url": "https://example.com/article",
                    "published_at": "2026-04-24T02:00:00+00:00",
                    "significance": "major",
                    "confidence": 0.9,
                    "risk_direction": "improving",
                    "created_at": "2026-04-24T02:05:00+00:00",
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

    assert result["current_analysis"]["driver_cards_state"] == "ready"
    assert result["current_analysis"]["driver_cards_source"] == "legacy_fallback"
    assert len(result["current_analysis"]["driver_cards"]) == 1
    assert result["current_analysis"]["driver_cards"][0]["source_chips"] == ["Reuters"]
    assert result["current_analysis"]["driver_cards"][0]["supporting_evidence"][0]["id"] == "ev-1"


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
    assert result["analysis_state"]["status"] == "queued"


def test_get_ticker_detail_bundle_uses_canonical_public_reasoning(monkeypatch):
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
                    "reasoning": "Risk factors for HOOD are relatively balanced and no single force dominates.",
                    "dimension_rationale": {},
                }
            ],
            "ticker_news_cache": [],
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
                    "reasoning": "Synthesized one bullish event analysis.",
                }
            ],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "HOOD")

    reasoning = result["current_score"]["reasoning"]
    assert reasoning.startswith("B — Moderate Risk (")
    assert "Data is substantive" in reasoning
    assert "Synthesized" not in reasoning
    assert "Risk factors for" not in reasoning
    assert "methodology" not in reasoning.lower()


def test_get_latest_position_analysis_for_ids_ignores_drafts(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-draft",
                    "status": "draft",
                    "summary": "Quick brief ready for AMD. Found 3 relevant headlines and started the deeper analysis.",
                    "updated_at": "2026-04-29T07:00:00+00:00",
                },
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-ready",
                    "status": "ready",
                    "summary": "AMD faces macro pressure but the AI thesis remains intact.",
                    "updated_at": "2026-04-29T08:00:00+00:00",
                },
            ]
        }
    )

    row = ticker_cache_service._get_latest_position_analysis_for_ids(supabase, ["pos-1"])

    assert row is not None
    assert row["status"] == "ready"
    assert "Quick brief ready" not in row["summary"]


def test_get_latest_position_analysis_for_ids_prefers_substantive_ready_row(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-fallback",
                    "status": "ready",
                    "summary": "Known facts are limited for AMD, so the current read leans on existing position context and whatever confirmed signals are available.",
                    "source_count": 0,
                    "major_event_count": 0,
                    "minor_event_count": 0,
                    "updated_at": "2026-04-29T08:00:00+00:00",
                },
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-substantive",
                    "status": "ready",
                    "summary": "AMD faces macro pressure but the AI thesis remains intact.",
                    "source_count": 2,
                    "major_event_count": 1,
                    "minor_event_count": 0,
                    "updated_at": "2026-04-29T07:00:00+00:00",
                },
            ]
        }
    )

    row = ticker_cache_service._get_latest_position_analysis_for_ids(supabase, ["pos-1"])

    assert row is not None
    assert row["analysis_run_id"] == "run-substantive"


def test_get_ticker_detail_bundle_prefers_article_reasoning_over_weak_fallback(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "industry": "Semiconductors",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "price": 155.0,
                    "price_as_of": "2026-04-29T08:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "AMD",
                    "grade": "C",
                    "safety_score": 58,
                    "analysis_as_of": "2026-04-29T08:00:00+00:00",
                    "coverage_state": "substantive",
                    "source_count": 2,
                    "news_summary": "AMD occupies a strong AI infrastructure position with real competitive pressure from Nvidia.",
                    "reasoning": "Company news is supportive for AMD. Coverage is thin; one new development could shift the picture.",
                    "dimension_rationale": {},
                }
            ],
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": "user-1",
                    "ticker": "AMD",
                    "current_price": 155.0,
                    "risk_grade": "C",
                    "total_score": 58,
                    "previous_grade": "D",
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-ready",
                    "status": "ready",
                    "summary": "Known facts are limited for AMD, so the current read leans on existing position context and whatever confirmed signals are available.",
                    "source_count": 0,
                    "updated_at": "2026-04-29T08:00:00+00:00",
                }
            ],
            "risk_scores": [
                {
                    "position_id": "pos-1",
                    "safety_score": 58,
                    "grade": "C",
                    "calculated_at": "2026-04-29T08:05:00+00:00",
                    "reasoning": "Known facts are limited for AMD, so the current read leans on existing position context and whatever confirmed signals are available.",
                    "source_count": 0,
                }
            ],
            "event_analyses": [
                {
                    "position_id": "pos-1",
                    "title": "AMD Stock Tests Resistance As Intel Beat Sparks Sector Rally - Benzinga",
                    "summary": "AMD rides sector momentum.",
                    "key_implications": [
                        "Sector rotation into semiconductors appears active, potentially benefiting AMD alongside Intel"
                    ],
                    "risk_direction": "improving",
                    "confidence": 0.63,
                    "created_at": "2026-04-29T08:04:00+00:00",
                }
            ],
            "analysis_runs": [
                {
                    "id": "run-ready",
                    "user_id": "user-1",
                    "target_position_id": "pos-1",
                    "status": "completed",
                    "started_at": "2026-04-29T08:00:00+00:00",
                    "completed_at": "2026-04-29T08:10:00+00:00",
                }
            ],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMD")

    reasoning = result["current_score"]["reasoning"]
    assert "Known facts are limited" not in reasoning
    assert "existing position context" not in reasoning
    assert "Sector rotation into se" in reasoning


def test_clean_public_rationale_text_preserves_valid_rationale():
    text = (
        "AMD's AI server demand supports near-term revenue growth, but Nvidia competition still threatens share capture if hyperscaler wins stall."
    )

    cleaned = ticker_cache_service._clean_public_rationale_text(text)

    assert cleaned == text


def test_clean_public_rationale_text_rejects_internal_score_breakdown():
    text = "Structural: 60, Macro: 0.0, Event: 0.0"

    cleaned = ticker_cache_service._clean_public_rationale_text(text)

    assert cleaned is None


def test_get_ticker_detail_bundle_uses_news_summary_when_no_events_exist(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "industry": "Semiconductors",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "NVDA",
                    "company_name": "NVIDIA",
                    "price": 900.0,
                    "price_as_of": "2026-04-29T08:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "NVDA",
                    "grade": "B",
                    "safety_score": 71,
                    "analysis_as_of": "2026-04-29T08:00:00+00:00",
                    "coverage_state": "substantive",
                    "source_count": 2,
                    "news_summary": "NVIDIA's AI demand remains strong, but valuation sensitivity and hyperscaler spending concentration still shape downside risk.",
                    "reasoning": "Risk factors for NVDA are relatively balanced and no single force dominates.",
                    "dimension_rationale": {},
                }
            ],
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": "user-1",
                    "ticker": "NVDA",
                    "current_price": 900.0,
                    "risk_grade": "B",
                    "total_score": 71,
                    "previous_grade": "C",
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-ready",
                    "status": "ready",
                    "summary": "Known facts are limited for NVDA, so the current read leans on existing position context and whatever confirmed signals are available.",
                    "source_count": 0,
                    "updated_at": "2026-04-29T08:00:00+00:00",
                }
            ],
            "risk_scores": [
                {
                    "position_id": "pos-1",
                    "safety_score": 71,
                    "grade": "B",
                    "calculated_at": "2026-04-29T08:05:00+00:00",
                    "reasoning": "Coverage is thin; one new development could shift the picture.",
                    "source_count": 0,
                }
            ],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "event_analyses": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "NVDA")

    reasoning = result["current_score"]["reasoning"]
    assert reasoning.startswith("B — Moderate Risk (")
    assert "NVIDIA's AI demand remains strong" in reasoning
    assert "valuation sensitivit" in reasoning


def test_get_ticker_detail_bundle_uses_safe_fallback_when_only_weak_rows_exist(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "AMZN",
                    "company_name": "Amazon",
                    "exchange": "NASDAQ",
                    "sector": "Consumer Discretionary",
                    "industry": "Internet Retail",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "AMZN",
                    "company_name": "Amazon",
                    "price": 180.0,
                    "price_as_of": "2026-04-29T08:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "AMZN",
                    "grade": "C",
                    "safety_score": 62,
                    "analysis_as_of": "2026-04-29T08:00:00+00:00",
                    "coverage_state": "provisional",
                    "source_count": 0,
                    "news_summary": "Insufficient evidence was available to produce a substantive event-driven analysis for AMZN in this cycle.",
                    "reasoning": "Coverage is thin; one new development could shift the picture.",
                    "dimension_rationale": {},
                }
            ],
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": "user-1",
                    "ticker": "AMZN",
                    "current_price": 180.0,
                    "risk_grade": "C",
                    "total_score": 62,
                    "previous_grade": "C",
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-ready",
                    "status": "ready",
                    "summary": "Known facts are limited for AMZN, so the current read leans on existing position context and whatever confirmed signals are available.",
                    "source_count": 0,
                    "updated_at": "2026-04-29T08:00:00+00:00",
                }
            ],
            "risk_scores": [
                {
                    "position_id": "pos-1",
                    "safety_score": 62,
                    "grade": "C",
                    "calculated_at": "2026-04-29T08:05:00+00:00",
                    "reasoning": "Coverage is thin; one new development could shift the picture.",
                    "source_count": 0,
                }
            ],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "event_analyses": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMZN")

    reasoning = result["current_score"]["reasoning"]
    assert reasoning.startswith("C — Elevated Risk (")
    assert "Rating pending" in reasoning or "Limited data" in reasoning


def test_get_ticker_detail_bundle_hides_weak_snapshot_reasoning(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "LDOS",
                    "company_name": "Leidos",
                    "exchange": "NYSE",
                    "sector": "Industrials",
                    "industry": "Aerospace & Defense",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "LDOS",
                    "company_name": "Leidos",
                    "price": 150.0,
                    "price_as_of": "2026-04-30T15:23:24+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "LDOS",
                    "grade": "F",
                    "safety_score": 26.5,
                    "analysis_as_of": "2026-04-30T15:23:24+00:00",
                    "source_count": 1,
                    "reasoning": "Position size amplifies downside risk for LDOS regardless of mixed signals. Concentration risk amplifies the downside. Volatility is elevated. Near-term risk is the primary focus. this rating is limited data — fuller data will sharpen it.",
                    "dimension_rationale": {},
                }
            ],
            "positions": [],
            "position_analyses": [],
            "risk_scores": [],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "event_analyses": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "LDOS")

    assert result["latest_risk_snapshot"]["reasoning"] is None


def test_get_ticker_detail_bundle_prefers_shared_path_when_system_position_exists(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "industry": "Semiconductors",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "price": 155.0,
                    "price_as_of": "2026-04-29T08:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "AMD",
                    "grade": "C",
                    "safety_score": 58,
                    "analysis_as_of": "2026-04-29T08:00:00+00:00",
                    "coverage_state": "substantive",
                    "source_count": 2,
                    "news_summary": "Shared AMD summary.",
                    "reasoning": "Shared AMD reasoning.",
                    "dimension_rationale": {},
                }
            ],
            "positions": [
                {
                    "id": "pos-user",
                    "user_id": "user-1",
                    "ticker": "AMD",
                    "current_price": 155.0,
                    "risk_grade": "C",
                    "total_score": 58,
                    "previous_grade": "D",
                },
                {
                    "id": "pos-system",
                    "user_id": ticker_cache_service.SYSTEM_SP500_USER_ID,
                    "ticker": "AMD",
                    "current_price": 155.0,
                    "risk_grade": "B",
                    "total_score": 71,
                    "previous_grade": "C",
                },
            ],
            "position_analyses": [
                {
                    "position_id": "pos-user",
                    "analysis_run_id": "run-user",
                    "status": "ready",
                    "summary": "User-specific AMD thesis remains intact.",
                    "source_count": 2,
                    "updated_at": "2026-04-29T08:00:00+00:00",
                },
                {
                    "position_id": "pos-system",
                    "analysis_run_id": "run-system",
                    "status": "ready",
                    "summary": "System-level AMD thesis should not override the held user path.",
                    "source_count": 3,
                    "updated_at": "2026-04-29T09:00:00+00:00",
                },
            ],
            "risk_scores": [
                {
                    "position_id": "pos-user",
                    "safety_score": 58,
                    "grade": "C",
                    "calculated_at": "2026-04-29T08:05:00+00:00",
                    "reasoning": "User-specific AMD thesis remains intact.",
                    "source_count": 2,
                },
                {
                    "position_id": "pos-system",
                    "safety_score": 71,
                    "grade": "B",
                    "calculated_at": "2026-04-29T09:05:00+00:00",
                    "reasoning": "System-level AMD thesis should not override the held user path.",
                    "source_count": 3,
                },
            ],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "event_analyses": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMD")

    assert result["analysis_state"]["source"] == "shared"
    assert result["portfolio_overlay"]["position_id"] == "pos-user"
    assert result["shared_analysis"]["summary"]["analysis_source"] == "shared"
    assert result["current_analysis"]["summary"] == "System-level AMD risk assessment should not override the held user path."
    assert result["current_score"]["reasoning"].startswith("C — Elevated Risk (")
    assert "Shared AMD summary" in result["current_score"]["reasoning"]


def test_get_latest_risk_snapshot_history_map_prefers_ai_snapshot_on_ties(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_risk_snapshots": [
                {
                    "id": "snap-fallback",
                    "ticker": "ABT",
                    "snapshot_type": "backfill",
                    "snapshot_date": "2026-04-30",
                    "grade": "D",
                    "safety_score": 60,
                    "methodology_version": "sp500-backfill-deterministic-fallback-v1",
                    "analysis_as_of": "2026-04-30T22:34:50+00:00",
                    "created_at": "2026-04-30T22:34:46+00:00",
                    "updated_at": "2026-04-30T22:35:05+00:00",
                },
                {
                    "id": "snap-ai",
                    "ticker": "ABT",
                    "snapshot_type": "backfill",
                    "snapshot_date": "2026-05-01",
                    "grade": "B",
                    "safety_score": 65,
                    "methodology_version": "sp500-ai-backfill-v2",
                    "analysis_as_of": "2026-04-30T22:34:50+00:00",
                    "created_at": "2026-05-01T11:00:56+00:00",
                    "updated_at": "2026-05-01T11:00:55+00:00",
                },
            ]
        }
    )

    history = ticker_cache_service.get_latest_risk_snapshot_history_map(
        supabase, ["ABT"], per_ticker=2
    )

    assert history["ABT"][0]["id"] == "snap-ai"
    assert history["ABT"][1]["id"] == "snap-fallback"


def test_get_ticker_detail_bundle_uses_canonical_ai_score_for_virtual_position(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "ABT",
                    "company_name": "Abbott Laboratories",
                    "exchange": "NYSE",
                    "sector": "Health Care",
                    "industry": "Medical Devices",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "ABT",
                    "company_name": "Abbott Laboratories",
                    "price": 90.79,
                    "price_as_of": "2026-05-01T10:30:06+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-fallback",
                    "ticker": "ABT",
                    "snapshot_type": "backfill",
                    "snapshot_date": "2026-04-30",
                    "grade": "D",
                    "safety_score": 60,
                    "methodology_version": "sp500-backfill-deterministic-fallback-v1",
                    "analysis_as_of": "2026-04-30T22:34:50+00:00",
                    "created_at": "2026-04-30T22:34:46+00:00",
                    "updated_at": "2026-04-30T22:35:05+00:00",
                    "reasoning": "D — High Risk (↓ improving)\nStructural profile dominant",
                    "news_summary": "Older summary.",
                    "source_count": 0,
                },
                {
                    "id": "snap-ai",
                    "ticker": "ABT",
                    "snapshot_type": "backfill",
                    "snapshot_date": "2026-05-01",
                    "grade": "B",
                    "safety_score": 65,
                    "methodology_version": "sp500-ai-backfill-v2",
                    "analysis_as_of": "2026-04-30T22:34:50+00:00",
                    "created_at": "2026-05-01T11:00:56+00:00",
                    "updated_at": "2026-05-01T11:00:55+00:00",
                    "reasoning": "D — High Risk (↓ improving)\nStructural profile dominant",
                    "news_summary": "Newer summary.",
                    "source_count": 3,
                },
            ],
            "positions": [
                {
                    "id": "pos-system",
                    "user_id": ticker_cache_service.SYSTEM_SP500_USER_ID,
                    "ticker": "ABT",
                    "current_price": 90.79,
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-system",
                    "analysis_run_id": "run-system",
                    "status": "ready",
                    "summary": "Abbott solid quarter offsets downgrade pressure.",
                    "source_count": 3,
                    "updated_at": "2026-05-01T00:30:00+00:00",
                }
            ],
            "risk_scores": [
                {
                    "position_id": "pos-system",
                    "analysis_run_id": "run-system",
                    "total_score": 65,
                    "safety_score": 60,
                    "grade": "D",
                    "reasoning": "D — High Risk (↓ improving)\nStructural profile dominant",
                    "source_count": 3,
                    "calculated_at": "2026-04-30T22:34:50+00:00",
                    "news_sentiment": 46,
                    "macro_exposure": 62,
                    "position_sizing": 82,
                    "volatility_trend": 71,
                    "factor_breakdown": {
                        "ai_dimensions": {
                            "news_sentiment": 46,
                            "macro_exposure": 62,
                            "position_sizing": 82,
                            "volatility_trend": 71,
                        }
                    },
                }
            ],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "event_analyses": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "ABT")

    assert result["current_score"]["grade"] == "B"
    assert result["current_score"]["total_score"] == 65
    assert result["current_score"]["safety_score"] == 65
    assert result["current_score"]["reasoning"].startswith("B — Moderate Risk (")
    assert result["current_score"]["evidence_strength"] == "moderate"
    assert result["position"]["risk_grade"] == "B"
    assert result["position"]["total_score"] == 65
    assert result["position"]["summary"].startswith("B — Moderate Risk (")
    assert result["position"]["evidence_strength"] == "moderate"


def test_get_ticker_detail_bundle_prefers_ai_snapshot_over_newer_shared_cache(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "ORLY",
                    "company_name": "O'Reilly Automotive",
                    "exchange": "NASDAQ",
                    "sector": "Consumer Discretionary",
                    "industry": "Specialty Retail",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "ORLY",
                    "company_name": "O'Reilly Automotive",
                    "price": 150.0,
                    "price_as_of": "2026-05-01T10:30:06+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-shared",
                    "ticker": "ORLY",
                    "snapshot_type": "daily",
                    "snapshot_date": "2026-05-01",
                    "grade": "C",
                    "safety_score": 60,
                    "methodology_version": "sp500-shared-cache-v1",
                    "analysis_as_of": "2026-05-01T10:18:43+00:00",
                    "created_at": "2026-05-01T10:18:44+00:00",
                    "updated_at": "2026-05-01T10:18:43+00:00",
                    "reasoning": "C — Elevated Risk (→ stable)\nStructural profile dominant",
                    "news_summary": "Shared summary.",
                    "source_count": 0,
                },
                {
                    "id": "snap-ai",
                    "ticker": "ORLY",
                    "snapshot_type": "backfill",
                    "snapshot_date": "2026-05-01",
                    "grade": "B",
                    "safety_score": 66.8,
                    "methodology_version": "sp500-ai-backfill-v2",
                    "analysis_as_of": "2026-05-01T02:47:37+00:00",
                    "created_at": "2026-05-01T11:00:57+00:00",
                    "updated_at": "2026-05-01T11:23:07+00:00",
                    "reasoning": "B — Moderate Risk (↓ improving)\nStructural profile dominant",
                    "news_summary": "AI summary.",
                    "source_count": 0,
                },
            ],
            "positions": [],
            "position_analyses": [],
            "risk_scores": [],
            "analysis_runs": [],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "event_analyses": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "ORLY")

    assert result["latest_risk_snapshot"]["methodology_version"] == "sp500-ai-backfill-v2"
    assert result["latest_risk_snapshot"]["grade"] == "B"
    assert result["latest_risk_snapshot"]["safety_score"] == 66.8


def test_get_ticker_detail_bundle_rejects_quick_brief_placeholder(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    supabase = _FakeSupabase(
        {
            "ticker_universe": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "exchange": "NASDAQ",
                    "sector": "Technology",
                    "industry": "Semiconductors",
                    "is_active": True,
                }
            ],
            "ticker_metadata": [
                {
                    "ticker": "AMD",
                    "company_name": "Advanced Micro Devices",
                    "price": 155.0,
                    "price_as_of": "2026-04-29T08:00:00+00:00",
                    "last_price_source": "finnhub",
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "AMD",
                    "grade": "C",
                    "safety_score": 58,
                    "analysis_as_of": "2026-04-29T08:00:00+00:00",
                    "coverage_state": "substantive",
                    "source_count": 2,
                    "news_summary": "Company news is supportive for AMD.",
                    "reasoning": "Company news is supportive for AMD. Risks are manageable near-term but worth monitoring.",
                    "dimension_rationale": {},
                }
            ],
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": "user-1",
                    "ticker": "AMD",
                    "current_price": 155.0,
                    "risk_grade": "C",
                    "total_score": 58,
                    "previous_grade": "D",
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-draft",
                    "status": "draft",
                    "summary": "Quick brief ready for AMD. Found 3 relevant headlines and started the deeper analysis.",
                    "long_report": "Draft status text.",
                    "methodology": "Initial draft based on the earliest matched headlines while the deeper event analysis is still running.",
                    "top_news": ["Draft headline"],
                    "top_risks": ["Draft risk"],
                    "watch_items": ["Draft watch item"],
                    "source_count": 3,
                    "updated_at": "2026-04-29T07:00:00+00:00",
                },
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-ready",
                    "status": "ready",
                    "summary": "AMD faces macro pressure but the AI thesis remains intact.",
                    "long_report": "Final report body.",
                    "methodology": "Final investor-facing analysis.",
                    "top_news": ["AMD gains traction"],
                    "top_risks": ["Macro pressure"],
                    "watch_items": ["Watch earnings"],
                    "source_count": 2,
                    "updated_at": "2026-04-29T08:00:00+00:00",
                },
            ],
            "risk_scores": [
                {
                    "position_id": "pos-1",
                    "safety_score": 58,
                    "grade": "C",
                    "calculated_at": "2026-04-29T08:05:00+00:00",
                    "reasoning": "",
                    "source_count": 2,
                }
            ],
            "analysis_runs": [
                {
                    "id": "run-ready",
                    "user_id": "user-1",
                    "target_position_id": "pos-1",
                    "status": "completed",
                    "started_at": "2026-04-29T08:00:00+00:00",
                    "completed_at": "2026-04-29T08:10:00+00:00",
                }
            ],
            "ticker_refresh_jobs": [],
            "ticker_news_cache": [],
            "alerts": [],
            "watchlists": [],
            "watchlist_items": [],
        }
    )

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMD")

    current_analysis = result["current_analysis"] or {}
    current_score = result["current_score"] or {}

    assert current_analysis.get("status") == "ready"
    assert "Quick brief ready" not in str(current_analysis.get("summary"))
    assert "started the deeper analysis" not in str(current_analysis.get("summary"))
    assert "Quick brief ready" not in str(current_score.get("reasoning"))
    assert "started the deeper analysis" not in str(current_score.get("reasoning"))
