import sys
import types
import importlib
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

from app.pipeline import scheduler
from app.services.ticker_cache_service import sync_ticker_news_cache


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.lt_filters = {}
        self.in_filters = {}
        self._delete = False
        self._insert_payload = None
        self._update_payload = None
        self._upsert_payload = None
        self._on_conflict = None

    def select(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        self._delete = True
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._upsert_payload = payload
        self._on_conflict = on_conflict
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, values):
        self.in_filters[key] = set(values)
        return self

    def lt(self, key, value):
        self.lt_filters[key] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def ilike(self, *_args, **_kwargs):
        return self

    def execute(self):
        table_rows = self.supabase.rows.setdefault(self.table_name, [])
        rows = table_rows
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self.in_filters.items():
            rows = [row for row in rows if row.get(key) in values]
        for key, value in self.lt_filters.items():
            rows = [row for row in rows if (row.get(key) or "") >= value]

        if self._delete:
            self.supabase.rows[self.table_name] = rows
            return _FakeResult([])

        if self._update_payload is not None:
            with self.supabase.lock:
                for row in table_rows:
                    if all(row.get(key) == value for key, value in self.filters.items()):
                        row.update(self._update_payload)
            return _FakeResult(rows)

        if self._insert_payload is not None:
            with self.supabase.lock:
                payload = self._insert_payload
                if isinstance(payload, list):
                    normalized = []
                    for item in payload:
                        row = dict(item)
                        row.setdefault("id", str(uuid.uuid4()))
                        normalized.append(row)
                    table_rows.extend(normalized)
                    payload = normalized
                else:
                    payload = dict(payload)
                    payload.setdefault("id", str(uuid.uuid4()))
                    table_rows.append(payload)
                self.supabase.rows[self.table_name] = table_rows
            return _FakeResult(payload if isinstance(payload, list) else [payload])

        if self._upsert_payload is not None:
            with self.supabase.lock:
                payloads = (
                    self._upsert_payload
                    if isinstance(self._upsert_payload, list)
                    else [self._upsert_payload]
                )
                conflict_keys = tuple((self._on_conflict or "").split(",")) if self._on_conflict else ()
                updated_rows = list(table_rows)
                for payload in payloads:
                    matched = False
                    for existing in updated_rows:
                        if conflict_keys and all(
                            existing.get(key) == payload.get(key) for key in conflict_keys
                        ):
                            existing.update(payload)
                            matched = True
                            break
                    if not matched:
                        updated_rows.append(dict(payload))
                self.supabase.rows[self.table_name] = updated_rows
            return _FakeResult(payloads)

        return _FakeResult(rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows
        self.lock = threading.Lock()

    def table(self, table_name):
        return _FakeQuery(self, table_name)


# Legacy ticker_news_cache test — retired tables in v2
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — ticker_news_cache and news_items tables dropped")
def test_sync_ticker_news_cache_replaces_rows_and_dedupes():
    supabase = _FakeSupabase(
        {
            "ticker_news_cache": [
                {
                    "ticker": "HOOD",
                    "headline": "old",
                    "url": "https://example.com/1",
                    "processed_at": "2026-04-24T00:05:00+00:00",
                }
            ]
        }
    )

    result = sync_ticker_news_cache(
        supabase,
        ticker="hood",
        news_rows=[
            {
                "event_hash": "hash-1",
                "title": "First headline",
                "summary": "First summary",
                "source": "Reuters",
                "url": "https://example.com/1",
                "sentiment": "positive",
                "published_at": "2026-04-24T02:00:00+00:00",
                "processed_at": "2026-04-24T02:05:00+00:00",
            },
            {
                "event_hash": "hash-1",
                "title": "Duplicate headline",
                "summary": "Duplicate summary",
                "source": "Reuters",
                "url": "https://example.com/1",
                "sentiment": "positive",
                "published_at": "2026-04-24T02:00:00+00:00",
                "processed_at": "2026-04-24T02:05:00+00:00",
            },
            {
                "event_hash": "hash-2",
                "title": "Second headline",
                "summary": "Second summary",
                "source": "AP",
                "url": "https://example.com/2",
                "sentiment": "neutral",
                "published_at": "2026-04-24T01:00:00+00:00",
                "processed_at": "2026-04-24T01:05:00+00:00",
            },
        ],
    )

    rows = supabase.rows["ticker_news_cache"]
    assert result["status"] == "completed"
    assert result["count"] == 2
    assert [row["headline"] for row in rows] == ["First headline", "Second headline"]
    assert rows[0]["ticker"] == "HOOD"


# Legacy ticker_news_cache test — retired tables in v2
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — ticker_news_cache and news_items tables dropped")
def test_sync_ticker_news_cache_is_idempotent_on_repeat_runs():
    supabase = _FakeSupabase({"ticker_news_cache": []})

    news_rows = [
        {
            "event_hash": "hash-1",
            "title": "First headline",
            "summary": "First summary",
            "source": "Reuters",
            "url": "https://example.com/1",
            "sentiment": "positive",
            "published_at": "2026-04-24T02:00:00+00:00",
            "processed_at": "2026-04-24T02:05:00+00:00",
        }
    ]

    first = sync_ticker_news_cache(supabase, ticker="hood", news_rows=news_rows)
    second = sync_ticker_news_cache(supabase, ticker="hood", news_rows=news_rows)

    assert first["status"] == "completed"
    assert second["status"] == "completed"
    assert len(supabase.rows["ticker_news_cache"]) == 1
    assert supabase.rows["ticker_news_cache"][0]["url"] == "https://example.com/1"


# Legacy ticker_news_cache test — retired tables in v2
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — ticker_news_cache and news_items tables dropped")
def test_sync_ticker_news_cache_is_idempotent_under_concurrent_calls():
    supabase = _FakeSupabase({"ticker_news_cache": []})

    news_rows = [
        {
            "event_hash": "hash-1",
            "title": "First headline",
            "summary": "First summary",
            "source": "Reuters",
            "url": "https://example.com/1",
            "sentiment": "positive",
            "published_at": "2026-04-24T02:00:00+00:00",
            "processed_at": "2026-04-24T02:05:00+00:00",
        },
        {
            "event_hash": "hash-2",
            "title": "Second headline",
            "summary": "Second summary",
            "source": "AP",
            "url": "https://example.com/2",
            "sentiment": "neutral",
            "published_at": "2026-04-24T01:00:00+00:00",
            "processed_at": "2026-04-24T01:05:00+00:00",
        },
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(sync_ticker_news_cache, supabase, ticker="hood", news_rows=news_rows)
            for _ in range(2)
        ]
        results = [future.result() for future in futures]

    assert all(result["status"] == "completed" for result in results)
    assert len(supabase.rows["ticker_news_cache"]) == 2
    assert {row["url"] for row in supabase.rows["ticker_news_cache"]} == {
        "https://example.com/1",
        "https://example.com/2",
    }


# Legacy cleanup test — _cleanup_old_news_items and retired tables
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — _cleanup_old_news_items, news_items, and ticker_news_cache dropped")
def test_cleanup_old_news_items_clears_ticker_news_cache():
    supabase = _FakeSupabase(
        {
            "news_items": [
                {"processed_at": "2026-03-01T00:00:00+00:00"},
                {"processed_at": "2026-04-23T00:00:00+00:00"},
            ],
            "ticker_news_cache": [
                {"processed_at": "2026-03-01T00:00:00+00:00"},
                {"processed_at": "2026-04-23T00:00:00+00:00"},
            ],
        }
    )

    supabase_service = importlib.import_module("app.services.supabase")

    original = supabase_service.get_supabase
    try:
        supabase_service.get_supabase = lambda: supabase
        scheduler._cleanup_old_news_items()
    finally:
        supabase_service.get_supabase = original

    assert supabase.rows["news_items"] == [
        {"processed_at": "2026-04-23T00:00:00+00:00"}
    ]
    assert supabase.rows["ticker_news_cache"] == [
        {"processed_at": "2026-04-23T00:00:00+00:00"}
    ]


# Legacy test — verifies refresh_ticker_snapshot queries news_items (retired table)
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — news_items table dropped")
def test_refresh_ticker_snapshot_omits_missing_news_summary_column(monkeypatch):
    ticker_cache_service = importlib.import_module("app.services.ticker_cache_service")

    class _StopAfterNewsSelect(Exception):
        pass

    class _SnapshotFakeResult:
        def __init__(self, data):
            self.data = data

    class _SnapshotFakeQuery:
        def __init__(self, table_name):
            self.table_name = table_name
            self.select_args = None
            self.insert_payload = None
            self.update_payload = None

        def select(self, *args, **kwargs):
            self.select_args = args
            if self.table_name == "news_items":
                raise _StopAfterNewsSelect()
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def in_(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def ilike(self, *_args, **_kwargs):
            return self

        def insert(self, *_args, **_kwargs):
            if _args:
                self.insert_payload = _args[0]
            return self

        def update(self, payload):
            self.update_payload = payload
            return self

        def delete(self, *_args, **_kwargs):
            return self

        def execute(self):
            if self.insert_payload is not None:
                payload = dict(self.insert_payload)
                payload.setdefault("id", "job-1")
                return _SnapshotFakeResult([payload])
            if self.update_payload is not None:
                return _SnapshotFakeResult([self.update_payload])
            return _SnapshotFakeResult([])

    class _SnapshotFakeSupabase:
        def __init__(self):
            self.queries = []

        def table(self, table_name):
            self.queries.append(table_name)
            return _SnapshotFakeQuery(table_name)

    supabase = _SnapshotFakeSupabase()

    monkeypatch.setattr(
        ticker_cache_service,
        "get_supported_ticker",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "ensure_ticker_in_universe",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )

    with pytest.raises(_StopAfterNewsSelect):
        ticker_cache_service.refresh_ticker_snapshot(
            supabase,
            ticker="HOOD",
            job_type="manual",
            requested_by_user_id=None,
        )

    assert "news_items" in supabase.queries


# Legacy test — depends on sync_ticker_news_cache (retired function) and news_items fixture
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — sync_ticker_news_cache and news_items dropped")
def test_refresh_ticker_snapshot_records_failed_job_before_news_sync(monkeypatch):
    ticker_cache_service = importlib.import_module("app.services.ticker_cache_service")

    supabase = _FakeSupabase(
        {
            "ticker_refresh_jobs": [],
            "news_items": [],
            "ticker_risk_snapshots": [],
        }
    )

    monkeypatch.setattr(
        ticker_cache_service,
        "get_supported_ticker",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "ensure_ticker_in_universe",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "sync_ticker_news_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("dup-key")),
    )

    with pytest.raises(RuntimeError, match="dup-key"):
        ticker_cache_service.refresh_ticker_snapshot(
            supabase,
            ticker="HOOD",
            job_type="daily",
            requested_by_user_id=None,
        )

    jobs = supabase.rows["ticker_refresh_jobs"]
    assert len(jobs) == 1
    assert jobs[0]["ticker"] == "HOOD"
    assert jobs[0]["status"] == "failed"
    assert jobs[0]["error_message"] == "dup-key"
    assert jobs[0].get("completed_at") is not None


# Legacy test — depends on sync_ticker_news_cache (retired) and news_items fixture
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — sync_ticker_news_cache and news_items dropped")
def test_refresh_ticker_snapshot_skips_existing_ai_snapshot_without_metadata_refresh(
    monkeypatch,
):
    ticker_cache_service = importlib.import_module("app.services.ticker_cache_service")

    supabase = _FakeSupabase(
        {
            "ticker_refresh_jobs": [],
            "news_items": [],
            "ticker_risk_snapshots": [
                {
                    "id": "snap-1",
                    "ticker": "HOOD",
                    "snapshot_date": ticker_cache_service.date.today().isoformat(),
                    "snapshot_type": "daily",
                    "methodology_version": "sp500-ai-backfill-v2",
                    "grade": "B",
                    "safety_score": 71,
                }
            ],
        }
    )

    monkeypatch.setattr(
        ticker_cache_service,
        "get_supported_ticker",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "ensure_ticker_in_universe",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "sync_ticker_news_cache",
        lambda *_args, **_kwargs: {"status": "completed", "count": 0},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "upsert_ticker_metadata",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("metadata refresh should not run")),
    )

    result = ticker_cache_service.refresh_ticker_snapshot(
        supabase,
        ticker="HOOD",
        job_type="daily",
        requested_by_user_id=None,
    )

    assert result["status"] == "skipped_ai_scored"
    assert result["methodology_version"] == "sp500-ai-backfill-v2"


# Legacy test — reads from risk_scores (retired) and position_analyses (partially retired)
@pytest.mark.xfail(reason="Legacy tables retired in v2 — risk_scores and position_analyses columns dropped")
def test_sync_ai_scores_to_ticker_snapshots_uses_run_scoped_ai_score(monkeypatch):
    ticker_cache_service = importlib.import_module("app.services.ticker_cache_service")

    supabase = _FakeSupabase(
        {
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": scheduler.SYSTEM_SP500_USER_ID,
                    "ticker": "HOOD",
                }
            ],
            "risk_scores": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-newer",
                    "grade": "D",
                    "total_score": 42.0,
                    "safety_score": 60.0,
                    "calculated_at": "2026-05-01T01:00:00+00:00",
                    "factor_breakdown": {
                        "ai_dimensions": {
                            "news_sentiment": 35,
                            "macro_exposure": 50,
                            "position_sizing": 40,
                            "volatility_trend": 43,
                        },
                        "llm_scoring_used": False,
                    },
                    "reasoning": "newer score",
                },
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-target",
                    "grade": "B",
                    "total_score": 68.4,
                    "safety_score": 60.0,
                    "calculated_at": "2026-05-01T00:30:00+00:00",
                    "factor_breakdown": {
                        "ai_dimensions": {
                            "news_sentiment": 61,
                            "macro_exposure": 64,
                            "position_sizing": 70,
                            "volatility_trend": 72,
                        },
                        "llm_scoring_used": True,
                    },
                    "reasoning": "target score",
                },
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-newer",
                    "summary": "newer summary",
                    "updated_at": "2026-05-01T01:00:00+00:00",
                },
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-target",
                    "summary": "target summary",
                    "updated_at": "2026-05-01T00:30:00+00:00",
                },
            ],
            "ticker_risk_snapshots": [],
        }
    )
    captured = {}

    def _capture_upsert(_supabase, *, ticker, snapshot_type, payload):
        captured["ticker"] = ticker
        captured["snapshot_type"] = snapshot_type
        captured["payload"] = payload
        return payload

    monkeypatch.setattr(ticker_cache_service, "_upsert_ticker_snapshot", _capture_upsert)

    scheduler._sync_ai_scores_to_ticker_snapshots_sync(
        supabase,
        "HOOD",
        "backfill",
        analysis_run_id="run-target",
    )

    assert captured["ticker"] == "HOOD"
    assert captured["snapshot_type"] == "backfill"
    assert captured["payload"]["grade"] == "B"
    assert captured["payload"]["safety_score"] == 68.4
    assert captured["payload"]["methodology_version"] == "sp500-ai-backfill-v2"
    assert captured["payload"]["reasoning"].startswith("B — Moderate Risk (")
    assert "Target score" in captured["payload"]["reasoning"]
    assert captured["payload"]["news_summary"] == "target summary"


# Legacy test — reads from risk_scores and analysis_runs (retired/legacy tables)
@pytest.mark.xfail(reason="Legacy tables retired in v2 — risk_scores dropped")
def test_sync_ai_scores_to_ticker_snapshots_recovers_ai_methodology_from_run_context(
    monkeypatch,
):
    ticker_cache_service = importlib.import_module("app.services.ticker_cache_service")

    supabase = _FakeSupabase(
        {
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": scheduler.SYSTEM_SP500_USER_ID,
                    "ticker": "HOOD",
                }
            ],
            "analysis_runs": [
                {
                    "id": "run-target",
                    "user_id": scheduler.SYSTEM_SP500_USER_ID,
                    "triggered_by": "scheduled",
                    "target_tickers": ["HOOD"],
                }
            ],
            "risk_scores": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-target",
                    "grade": "B",
                    "total_score": 68.4,
                    "safety_score": 60.0,
                    "calculated_at": "2026-05-01T00:30:00+00:00",
                    "factor_breakdown": {
                        "ai_dimensions": {
                            "news_sentiment": 61,
                            "macro_exposure": 64,
                            "position_sizing": 70,
                            "volatility_trend": 72,
                        }
                    },
                    "reasoning": "target score",
                }
            ],
            "position_analyses": [
                {
                    "position_id": "pos-1",
                    "analysis_run_id": "run-target",
                    "summary": "target summary",
                    "updated_at": "2026-05-01T00:30:00+00:00",
                }
            ],
            "ticker_risk_snapshots": [],
        }
    )
    captured = {}

    def _capture_upsert(_supabase, *, ticker, snapshot_type, payload):
        captured["payload"] = payload
        return payload

    monkeypatch.setattr(ticker_cache_service, "_upsert_ticker_snapshot", _capture_upsert)

    scheduler._sync_ai_scores_to_ticker_snapshots_sync(
        supabase,
        "HOOD",
        "backfill",
        analysis_run_id="run-target",
    )

    assert captured["payload"]["methodology_version"] == "sp500-ai-backfill-v2"


# Legacy test — uses news_items and ticker_news_cache (retired), mocks sync_ticker_news_cache
@pytest.mark.xfail(reason="Legacy news cache retired in v2 — news_items, ticker_news_cache, and sync_ticker_news_cache dropped")
def test_refresh_ticker_snapshot_does_not_write_unsupported_news_cache_columns(
    monkeypatch,
):
    ticker_cache_service = importlib.import_module("app.services.ticker_cache_service")

    supabase = _FakeSupabase(
        {
            "ticker_refresh_jobs": [],
            "news_items": [],
            "ticker_risk_snapshots": [],
            "ticker_news_cache": [],
        }
    )
    captured = {}

    monkeypatch.setattr(
        ticker_cache_service,
        "get_supported_ticker",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "ensure_ticker_in_universe",
        lambda _supabase, _ticker: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "sync_ticker_news_cache",
        lambda *_args, **_kwargs: {"status": "completed", "count": 2},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "upsert_ticker_metadata",
        lambda *_args, **_kwargs: {"ticker": "HOOD"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "get_latest_risk_snapshot_map",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "_build_event_analyses_from_news_rows",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "score_position_structural",
        lambda *_args, **_kwargs: {
            "grade": "B",
            "safety_score": 71,
            "structural_base_score": 71,
            "macro_adjustment": 0.0,
            "event_adjustment": 0.0,
            "confidence": 0.8,
            "factor_breakdown": {},
            "dimension_rationale": {},
            "reasoning": "Valid investor-facing rationale.",
        },
    )

    def _capture_snapshot(*_args, **kwargs):
        captured.update(kwargs["payload"])
        return kwargs["payload"]

    monkeypatch.setattr(
        ticker_cache_service,
        "_upsert_ticker_snapshot",
        _capture_snapshot,
    )

    result = ticker_cache_service.refresh_ticker_snapshot(
        supabase,
        ticker="HOOD",
        job_type="daily",
        requested_by_user_id=None,
    )

    assert result["status"] == "completed"
    assert "news_cache_status" not in captured
    assert "news_cache_count" not in captured


def test_refresh_ticker_snapshot_marks_missing_news_dimension_as_limited(monkeypatch):
    ticker_cache_service = importlib.import_module("app.services.ticker_cache_service")

    supabase = _FakeSupabase(
        {
            "ticker_refresh_jobs": [],
            "shared_ticker_events": [],
            "ticker_risk_snapshots": [],
        }
    )
    captured = {}

    monkeypatch.setattr(
        ticker_cache_service,
        "get_supported_ticker",
        lambda _supabase, _ticker: {"ticker": "HIMS"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "ensure_ticker_in_universe",
        lambda _supabase, _ticker: {"ticker": "HIMS"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "upsert_ticker_metadata",
        lambda *_args, **_kwargs: {
            "ticker": "HIMS",
            "sector": "Health Care",
            "price_as_of": "2026-05-27T16:03:19.292155+00:00",
        },
    )
    monkeypatch.setattr(ticker_cache_service, "fetch_aggs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        ticker_cache_service,
        "run_macro_regression",
        lambda *_args, **_kwargs: {
            "limited_data": True,
            "trading_days_used": 0,
            "coefficients": {},
            "r_squared": None,
            "as_of_date": "2026-05-27",
        },
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "_build_sector_exposure_inputs",
        lambda *_args, **_kwargs: {"sector": "Health Care"},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "_build_volatility_inputs",
        lambda *_args, **_kwargs: {"realized_vol_30d": 0.9848},
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "_build_event_analyses_from_news_rows",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "score_position_structural",
        lambda *_args, **_kwargs: {
            "grade": "BB",
            "safety_score": 51.0,
            "total_score": 51.0,
            "composite_score": 51.0,
            "structural_base_score": 51.0,
            "macro_adjustment": 0.0,
            "event_adjustment": 0.0,
            "confidence": 0.75,
            "financial_health": 58,
            "news_sentiment": None,
            "macro_exposure": 41,
            "sector_exposure": 65,
            "volatility": 40,
            "factor_breakdown": {
                "ai_dimensions": {
                    "financial_health": 58,
                    "news_sentiment": None,
                    "macro_exposure": 41,
                    "sector_exposure": 65,
                    "volatility": 40,
                }
            },
            "dimension_rationale": {
                "news_sentiment": "Event-driven sentiment from available articles.",
            },
            "reasoning": "BB - Mixed Signals",
        },
    )

    def _capture_snapshot(*_args, **kwargs):
        captured.update(kwargs["payload"])
        return kwargs["payload"]

    monkeypatch.setattr(
        ticker_cache_service,
        "_upsert_ticker_snapshot",
        _capture_snapshot,
    )

    result = ticker_cache_service.refresh_ticker_snapshot(
        supabase,
        ticker="HIMS",
        job_type="backfill",
        requested_by_user_id=None,
    )

    assert result["status"] == "completed"
    assert captured["news_sentiment_dim"] is None
    assert "news_sentiment" in captured["limited_data_dimensions"]
    assert captured["dimension_inputs"]["news_sentiment"]["limited_data"] is True
    assert "at least 3 are required" in captured["dimension_inputs"]["news_sentiment"]["limited_reason"]
    assert captured["dimension_inputs"]["macro_exposure"]["limited_data"] is True
    assert "usable trading day" in captured["dimension_inputs"]["macro_exposure"]["limited_reason"]
