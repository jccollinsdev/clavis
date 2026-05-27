import asyncio
import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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

from app.pipeline import scheduler
from app.services.digest_selection import current_trading_date


class _FakeScheduler:
    def __init__(self, existing_job_ids=None):
        self.jobs = {
            job_id: SimpleNamespace(id=job_id, next_run_time=None)
            for job_id in (existing_job_ids or [])
        }
        self.added = []
        self.removed = []
        self.running = False
        self.started = False
        self.shutdown_called = False

    def start(self):
        self.running = True
        self.started = True

    def shutdown(self, wait=True):
        self.running = False
        self.shutdown_called = True

    def get_jobs(self):
        return list(self.jobs.values())

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def remove_job(self, job_id):
        self.removed.append(job_id)
        self.jobs.pop(job_id, None)

    def add_job(self, func, trigger, id, **kwargs):
        job = SimpleNamespace(
            id=id, func=func, trigger=trigger, kwargs=kwargs, next_run_time=None
        )
        self.jobs[id] = job
        self.added.append(job)
        return job


def test_schedule_holdings_daily_ai_refresh_registers_coroutine_job():
    fake_scheduler = _FakeScheduler()

    with patch.object(scheduler, "scheduler", fake_scheduler):
        scheduler._schedule_holdings_daily_ai_refresh()

    job = fake_scheduler.jobs[scheduler.HOLDINGS_DAILY_AI_JOB_ID]
    assert job.func is scheduler.run_user_holdings_daily_ai_refresh
    assert job.kwargs["misfire_grace_time"] == 3600


def test_schedule_sp500_daily_refresh_registers_coroutine_job_with_kwargs():
    fake_scheduler = _FakeScheduler()

    with patch.object(scheduler, "scheduler", fake_scheduler):
        scheduler._schedule_sp500_daily_refresh()

    job = fake_scheduler.jobs[scheduler.SP500_DAILY_JOB_ID]
    assert job.func is scheduler.refresh_sp500_cache
    assert job.kwargs["kwargs"] == {"job_type": "daily"}


def test_schedule_news_cleanup_registers_cron_job():
    fake_scheduler = _FakeScheduler()

    with patch.object(scheduler, "scheduler", fake_scheduler):
        scheduler._schedule_news_cleanup()

    job = fake_scheduler.jobs[scheduler.NEWS_CLEANUP_JOB_ID]
    assert job.func is scheduler._cleanup_old_articles


def test_start_scheduler_intraday_registers_only_tier_zero_jobs(monkeypatch):
    monkeypatch.setenv("SCHEDULER_TIER", "intraday")
    fake_scheduler = _FakeScheduler()

    with (
        patch.object(scheduler, "scheduler", fake_scheduler),
        patch.object(scheduler, "_fail_stale_runs"),
        patch.object(scheduler, "_fail_orphaned_runs"),
        patch("app.services.supabase.get_supabase", return_value=object()),
    ):
        scheduler.start_scheduler()

    assert fake_scheduler.started is True
    assert scheduler.ACTIVE_TICKER_NEWS_REFRESH_JOB_ID in fake_scheduler.jobs
    assert scheduler.BULK_SENTIMENT_ENRICHMENT_JOB_ID in fake_scheduler.jobs
    assert scheduler.SP500_DAILY_JOB_ID not in fake_scheduler.jobs
    assert scheduler.DAILY_MACRO_SNAPSHOT_JOB_ID not in fake_scheduler.jobs
    assert scheduler.DAILY_SECTOR_SNAPSHOT_JOB_ID not in fake_scheduler.jobs


def test_start_scheduler_cron_registers_daily_and_intraday_jobs(monkeypatch):
    monkeypatch.setenv("SCHEDULER_TIER", "cron")
    fake_scheduler = _FakeScheduler()

    with (
        patch.object(scheduler, "scheduler", fake_scheduler),
        patch.object(scheduler, "_fail_stale_runs"),
        patch.object(scheduler, "_fail_orphaned_runs"),
        patch.object(scheduler, "_sync_user_job"),
        patch("app.services.supabase.get_supabase") as get_supabase_mock,
    ):
        fake_query = SimpleNamespace(
            select=lambda *_args, **_kwargs: SimpleNamespace(
                execute=lambda: SimpleNamespace(data=[])
            )
        )
        get_supabase_mock.return_value = SimpleNamespace(table=lambda *_args: fake_query)
        scheduler.start_scheduler()

    assert scheduler.SP500_DAILY_JOB_ID in fake_scheduler.jobs
    assert scheduler.HOLDINGS_DAILY_AI_JOB_ID in fake_scheduler.jobs
    assert scheduler.NEWS_CLEANUP_JOB_ID in fake_scheduler.jobs
    assert scheduler.DAILY_MACRO_SNAPSHOT_JOB_ID in fake_scheduler.jobs
    assert scheduler.DAILY_SECTOR_SNAPSHOT_JOB_ID in fake_scheduler.jobs
    assert scheduler.ACTIVE_TICKER_NEWS_REFRESH_JOB_ID in fake_scheduler.jobs


def test_start_scheduler_none_does_not_start_scheduler(monkeypatch):
    monkeypatch.setenv("SCHEDULER_TIER", "none")
    fake_scheduler = _FakeScheduler()

    with (
        patch.object(scheduler, "scheduler", fake_scheduler),
        patch("app.services.supabase.get_supabase") as get_supabase_mock,
    ):
        scheduler.start_scheduler()

    assert fake_scheduler.started is False
    get_supabase_mock.assert_not_called()


class _AnalysisCacheStoreResult:
    data = []


class _AnalysisCacheStoreQuery:
    def __init__(self):
        self.upsert_calls = []

    def upsert(self, row, on_conflict=None):
        self.upsert_calls.append({"row": row, "on_conflict": on_conflict})
        return self

    def execute(self):
        return _AnalysisCacheStoreResult()


class _AnalysisCacheStoreSupabase:
    def __init__(self):
        self.query = _AnalysisCacheStoreQuery()

    def table(self, table_name):
        assert table_name == scheduler.CACHE_TABLE
        return self.query


def test_store_analysis_cache_uses_conflict_safe_upsert():
    supabase = _AnalysisCacheStoreSupabase()

    scheduler._store_analysis_cache(
        supabase,
        kind="relevance",
        cache_key="race-key",
        payload={"relevant": True},
    )

    assert len(supabase.query.upsert_calls) == 1
    call = supabase.query.upsert_calls[0]
    assert call["on_conflict"] == "kind,cache_key"
    assert call["row"]["kind"] == "relevance"
    assert call["row"]["cache_key"] == "race-key"
    assert call["row"]["payload"] == {"relevant": True}


class _TickerSnapshotUpsertResult:
    def __init__(self, data):
        self.data = data


class _TickerSnapshotUpsertQuery:
    def __init__(self):
        self.upsert_calls = []

    def upsert(self, row, on_conflict=None):
        self.upsert_calls.append({"row": row, "on_conflict": on_conflict})
        return self

    def execute(self):
        return _TickerSnapshotUpsertResult([{"id": "snapshot-1"}])


class _TickerSnapshotUpsertSupabase:
    def __init__(self):
        self.query = _TickerSnapshotUpsertQuery()

    def table(self, table_name):
        assert table_name == "ticker_risk_snapshots"
        return self.query


def test_upsert_ticker_snapshot_from_scores_serializes_snapshot_date():
    supabase = _TickerSnapshotUpsertSupabase()
    today = current_trading_date().isoformat()

    scheduler._upsert_ticker_snapshot_from_scores(
        supabase,
        ticker="EXPD",
        ai_scores={
            "grade": "A",
            "total_score": 88.5,
            "financial_health": 82,
            "news_sentiment": 79,
            "macro_exposure": 77,
            "sector_exposure": 80,
            "volatility": 84,
            "structural_base_score": 71.0,
            "macro_adjustment": 1.2,
            "event_adjustment": 2.3,
            "confidence": 0.91,
            "factor_breakdown": {"ai_dimensions": {"news_sentiment": 79}},
            "dimension_rationale": {},
            "reasoning": "Reasoning",
            "calculated_at": "2026-05-23T00:00:00+00:00",
        },
        structural_scores={"safety_score": 71.0, "grade": "B", "confidence": 0.72},
        analysis_run_id="run-1",
    )

    assert len(supabase.query.upsert_calls) == 1
    call = supabase.query.upsert_calls[0]
    assert call["on_conflict"] == "ticker,snapshot_date,snapshot_type"
    assert call["row"]["snapshot_date"] == today
    assert call["row"]["ticker"] == "EXPD"


def test_enqueue_analysis_run_pauses_autonomous_system_child_when_scheduler_paused(monkeypatch):
    monkeypatch.setenv("PAUSE_SYSTEM_SCHEDULER", "true")

    with patch.object(scheduler, "create_analysis_run", new_callable=AsyncMock) as create_mock:
        result = asyncio.run(
            scheduler.enqueue_analysis_run(
                scheduler.SYSTEM_SP500_USER_ID,
                triggered_by="scheduled",
                target_tickers=["AAPL"],
            )
        )

    assert result["status"] == "paused"
    assert result["analysis_run_id"] is None
    create_mock.assert_not_called()


def test_enqueue_analysis_run_allows_supervised_backfill_child_when_scheduler_paused(monkeypatch):
    monkeypatch.setenv("PAUSE_SYSTEM_SCHEDULER", "true")

    async def fake_create_analysis_run(*_args, **_kwargs):
        return {"id": "supervised-child-run"}

    with (
        patch.object(scheduler, "create_analysis_run", side_effect=fake_create_analysis_run) as create_mock,
        patch.object(scheduler, "_fail_stale_runs") as fail_stale_mock,
        patch.object(scheduler, "_run_analysis_in_thread", return_value=True),
        patch("app.services.supabase.get_supabase", return_value=object()),
    ):
        result = asyncio.run(
            scheduler.enqueue_analysis_run(
                scheduler.SYSTEM_SP500_USER_ID,
                triggered_by="scheduled",
                target_tickers=["AAPL", "MSFT"],
                allow_parallel_runs=True,
            )
        )

    task = scheduler.active_runs.pop("supervised-child-run", None)
    if task is not None and not task.done():
        task.cancel()

    assert result["status"] == "queued"
    assert result["analysis_run_id"] == "supervised-child-run"
    create_mock.assert_called_once()
    fail_stale_mock.assert_called_once()


def test_sync_user_job_keeps_structural_refresh_when_notifications_disabled():
    user_id = "user-123"
    digest_job_id = scheduler._job_id_for_user(user_id)
    structural_job_id = f"{scheduler.JOB_PREFIX}{user_id}_structural_refresh"
    fake_scheduler = _FakeScheduler([digest_job_id, structural_job_id])

    with (
        patch.object(scheduler, "scheduler", fake_scheduler),
        patch.object(
            scheduler, "_mark_scheduler_inactive", return_value={"status": "inactive"}
        ) as inactive_mock,
    ):
        result = scheduler._sync_user_job(
            supabase=object(),
            user_id=user_id,
            digest_time="07:00",
            notifications_enabled=False,
        )

    assert result == {"status": "inactive"}
    assert digest_job_id in fake_scheduler.removed
    assert structural_job_id in fake_scheduler.removed
    assert structural_job_id in fake_scheduler.jobs
    assert (
        fake_scheduler.jobs[structural_job_id].func
        is scheduler.trigger_structural_refresh
    )
    inactive_mock.assert_called_once()


def test_sync_user_job_replaces_digest_job_for_new_time():
    user_id = "user-456"
    digest_job_id = scheduler._job_id_for_user(user_id)
    structural_job_id = f"{scheduler.JOB_PREFIX}{user_id}_structural_refresh"
    fake_scheduler = _FakeScheduler([digest_job_id, structural_job_id])

    with (
        patch.object(scheduler, "scheduler", fake_scheduler),
        patch.object(scheduler, "_persist_scheduler_state", return_value={}) as persist_mock,
    ):
        result = scheduler._sync_user_job(
            supabase=object(),
            user_id=user_id,
            digest_time="21:30",
            notifications_enabled=True,
        )

    assert digest_job_id in fake_scheduler.removed
    assert structural_job_id in fake_scheduler.removed
    assert fake_scheduler.added[-1].id == digest_job_id
    assert str(fake_scheduler.added[-1].trigger) == "cron[hour='21', minute='30']"
    persist_mock.assert_called_once()
    assert result == {}


def test_upsert_draft_position_snapshot_keeps_publishable_fields_empty():
    captured = {}

    def _capture(*_args, **kwargs):
        captured.update(kwargs)

    with patch.object(scheduler, "_upsert_position_analysis", side_effect=_capture):
        scheduler._upsert_draft_position_snapshot(
            object(),
            analysis_run_id="run-1",
            position={"id": "pos-1", "ticker": "AMD", "archetype": "core"},
            ticker="AMD",
            top_headlines=["Headline"],
            progress_message="Risk review in progress.",
            source_count=2,
        )

    assert captured["summary"] is None
    assert captured["long_report"] is None
    assert captured["methodology"] is None
    assert captured["top_risks"] == []
    assert captured["watch_items"] == []


class _WeekdayDigestFakeResult:
    def __init__(self, data):
        self.data = data


class _WeekdayDigestFakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return _WeekdayDigestFakeResult(self.rows)


class _WeekdayDigestFakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _table_name):
        return _WeekdayDigestFakeQuery(self.rows)


def test_trigger_scheduled_digest_skips_weekends_when_weekday_only_enabled(monkeypatch):
    class _FakeSaturday(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("datetime.datetime", _FakeSaturday)
    fake_supabase = _WeekdayDigestFakeSupabase([
        {"weekday_only": True}
    ])

    with (
        patch("app.services.supabase.get_supabase", return_value=fake_supabase),
        patch.object(scheduler, "enqueue_analysis_run") as enqueue_mock,
    ):
        result = asyncio.run(scheduler.trigger_scheduled_digest("user-1"))

    assert result is None
    enqueue_mock.assert_not_called()


def test_quiet_hours_active_handles_overnight_window():
    assert (
        scheduler._quiet_hours_active(
            datetime(2026, 4, 24, 23, 30, tzinfo=timezone.utc),
            enabled=True,
            start="22:00",
            end="07:00",
        )
        is True
    )
    assert (
        scheduler._quiet_hours_active(
            datetime(2026, 4, 24, 10, 30, tzinfo=timezone.utc),
            enabled=True,
            start="22:00",
            end="07:00",
        )
        is False
    )


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.selected = None

    def select(self, columns):
        self.selected = columns
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def upsert(self, payload, on_conflict):
        self.supabase.upserts.append(
            {
                "table": self.table_name,
                "payload": payload,
                "on_conflict": on_conflict,
            }
        )
        return self

    def execute(self):
        if self.table_name == "positions":
            return _FakeResult(
                [
                    {"id": "pos-1", "ticker": "hood"},
                    {"id": "pos-2", "ticker": "HOOD"},
                ]
            )
        if self.table_name == "ticker_metadata":
            return _FakeResult(
                [
                    {
                        "ticker": self.filters.get("ticker", "HOOD"),
                        "market_cap": 100,
                        "avg_daily_dollar_volume": 50,
                        "volatility_proxy": 20,
                        "leverage_profile": "moderate",
                        "profitability_profile": "mixed",
                        "asset_class": "equity",
                    }
                ]
            )
        if self.table_name == "asset_safety_profiles":
            return _FakeResult([])
        if self.table_name == "shared_ticker_events":
            return _FakeResult([{"id": "id-1"}])
        return _FakeResult([])


class _FakeSupabase:
    def __init__(self):
        self.upserts = []

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_trigger_structural_refresh_upserts_once_per_unique_ticker():
    fake_supabase = _FakeSupabase()

    with (
        patch("app.services.supabase.get_supabase", return_value=fake_supabase),
        patch("app.services.ticker_metadata.upsert_ticker_metadata"),
        patch(
            "app.pipeline.structural_scorer.calculate_structural_base_score",
            return_value={
                "structural_base_score": 72,
                "confidence": 0.9,
                "market_cap_bucket": "large",
                "factor_breakdown": {
                    "liquidity_score": 1,
                    "volatility_score": 2,
                    "leverage_score": 3,
                    "profitability_score": 4,
                },
            },
        ),
    ):
        result = asyncio.run(scheduler.trigger_structural_refresh("user-123"))

    assert result == {
        "status": "structural_refresh_complete",
        "user_id": "user-123",
        "tickers_refreshed": 1,
    }
    assert len(fake_supabase.upserts) == 0


def test_upsert_shared_ticker_event_skips_unresolved_google_wrapper():
    fake_supabase = _FakeSupabase()

    result = scheduler._upsert_shared_ticker_event(
        fake_supabase,
        ticker="TTD",
        event_record={
            "event_hash": "hash-1",
            "title": "Wrapped article",
            "source": "Seeking Alpha",
            "source_url": "https://news.google.com/rss/articles/CBMi123?oc=5",
            "published_at": "2026-05-20T15:40:06+00:00",
            "risk_direction": "neutral",
        },
    )

    assert result is None
    assert fake_supabase.upserts == []


def test_upsert_shared_ticker_event_skips_missing_canonical_url():
    fake_supabase = _FakeSupabase()

    result = scheduler._upsert_shared_ticker_event(
        fake_supabase,
        ticker="RSG",
        event_record={
            "event_hash": "hash-rsg",
            "title": "Wrapped article",
            "source": "Simply Wall St",
            "source_url": "",
            "published_at": "2026-05-20T15:40:06+00:00",
            "risk_direction": "neutral",
        },
    )

    assert result is None
    assert fake_supabase.upserts == []


def test_upsert_shared_ticker_event_normalizes_invalid_horizon_and_direction():
    fake_supabase = _FakeSupabase()

    result = scheduler._upsert_shared_ticker_event(
        fake_supabase,
        ticker="RSG",
        event_record={
            "event_hash": "hash-rsg-valid",
            "title": "Resolved article",
            "source": "Stock Titan",
            "source_url": "https://www.stocktitan.net/sec-filings/RSG/example",
            "published_at": "2026-05-20T15:40:06+00:00",
            "impact_horizon": "future",
            "risk_direction": "sideways",
        },
    )

    assert result == "id-1"
    assert len(fake_supabase.upserts) == 1
    payload = fake_supabase.upserts[0]["payload"]
    assert payload["impact_horizon"] == "near_term"
    assert payload["risk_direction"] == "neutral"
    assert payload["sentiment_score"] is None


def test_google_news_wrapper_detector_catches_embedded_rss_shape():
    assert scheduler._is_google_news_wrapper_url(
        " https://news.google.com/rss/articles/CBMi3AFBVV95cUxOVllicmFi?oc=5 "
    )


def test_canonical_article_url_for_shared_event_prefers_resolved_publisher_url():
    article = {
        "url": "https://news.google.com/rss/articles/CBMi123?oc=5",
        "source_url": "https://seekingalpha.com",
        "resolved_url": "https://seekingalpha.com/article/123-the-trade-desk",
    }

    assert (
        scheduler._canonical_article_url_for_shared_event(article)
        == "https://seekingalpha.com/article/123-the-trade-desk"
    )


def test_canonical_article_url_for_shared_event_rejects_unresolved_wrapper():
    article = {
        "url": "https://news.google.com/rss/articles/CBMi123?oc=5",
        "source_url": "https://seekingalpha.com",
    }

    assert scheduler._canonical_article_url_for_shared_event(article) == ""


def test_canonical_article_url_for_shared_event_uses_canonical_url_key():
    article = {
        "url": "https://news.google.com/rss/articles/CBMi123?oc=5",
        "source_url": "https://simplywall.st",
        "canonical_url": "https://simplywall.st/stocks/us/commercial-services/nyse-rsg/republic-services/news/pricing-update",
    }

    assert scheduler._canonical_article_url_for_shared_event(article) == (
        "https://simplywall.st/stocks/us/commercial-services/nyse-rsg/republic-services/news/pricing-update"
    )


def test_sp500_post_run_wrapper_cleanup_imports_cleanup_hook(monkeypatch):
    async def _fake_run_cleanup(**kwargs):
        return {"remaining_leaks": 0, "kwargs": kwargs}

    monkeypatch.setattr(
        "app.scripts.wrapper_storage_cleanup.run_cleanup",
        _fake_run_cleanup,
    )

    result = asyncio.run(scheduler._run_sp500_post_run_wrapper_cleanup())

    assert result["remaining_leaks"] == 0
    assert result["kwargs"]["apply"] is True
    assert result["kwargs"]["days"] == 30


class _SyncSnapshotFakeQuery:
    def __init__(self, table_name):
        self.table_name = table_name
        self.selected = ""
        self.filters = {}

    def select(self, columns):
        self.selected = columns
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.table_name == "positions":
            return _FakeResult([{"id": "pos-amd", "ticker": "AMD"}])
        if self.table_name == "position_analyses":
            return _FakeResult([{"summary": "Real analysis summary.", "source_count": 5}])
        if self.table_name == "ticker_risk_snapshots" and self.selected == "safety_score":
            return _FakeResult([{"safety_score": 70.0}])
        if self.table_name == "ticker_risk_snapshots":
            return _FakeResult(
                [
                    {
                        "ticker": "AMD",
                        "snapshot_type": "backfill",
                        "snapshot_date": "2026-05-21",
                        "grade": "BB",
                        "safety_score": 68.0,
                        "composite_score": 68.0,
                        "analysis_as_of": "2026-05-21T12:00:00+00:00",
                        "created_at": "2026-05-21T12:00:00+00:00",
                        "updated_at": "2026-05-21T12:00:00+00:00",
                        "confidence": 0.88,
                        "source_count": 4,
                        "llm_scoring_used": True,
                        "factor_breakdown": {
                            "ai_dimensions": {
                                "financial_health": 72,
                                "news_sentiment": 60,
                                "macro_exposure": 58,
                                "sector_exposure": 61,
                                "volatility": 66,
                            }
                        },
                    },
                    {
                        "ticker": "AMD",
                        "snapshot_type": "daily",
                        "snapshot_date": "2026-05-22",
                        "grade": "A",
                        "safety_score": 82.0,
                        "composite_score": 82.0,
                        "confidence": 0.91,
                        "source_count": 5,
                        "llm_scoring_used": True,
                        "analysis_as_of": "2026-05-22T12:00:00+00:00",
                        "created_at": "2026-05-22T12:00:00+00:00",
                        "updated_at": "2026-05-22T12:00:00+00:00",
                        "financial_health": 80,
                        "news_sentiment_dim": 84,
                        "macro_exposure_dim": 78,
                        "sector_exposure": 79,
                        "volatility": 83,
                        "dimension_inputs": {"macro_exposure": {"r_squared": 0.31}},
                        "dimension_last_refreshed": {"macro_exposure": "2026-05-22T12:00:00+00:00"},
                        "factor_breakdown": {
                            "ai_dimensions": {
                                "financial_health": 80,
                                "news_sentiment": 84,
                                "macro_exposure": 78,
                                "sector_exposure": 79,
                                "volatility": 83,
                            }
                        },
                    }
                ]
            )
        return _FakeResult([])


class _SyncSnapshotFakeSupabase:
    def table(self, table_name):
        return _SyncSnapshotFakeQuery(table_name)


def test_sync_ai_scores_retries_transient_snapshot_upsert_disconnect(monkeypatch):
    calls = {"upsert": 0}

    def _flaky_upsert(_client, **kwargs):
        calls["upsert"] += 1
        if calls["upsert"] == 1:
            raise RuntimeError("Server disconnected")
        calls["payload"] = kwargs["payload"]
        return kwargs["payload"]

    monkeypatch.setattr(
        "app.services.supabase.get_supabase",
        lambda: _SyncSnapshotFakeSupabase(),
    )
    monkeypatch.setattr(
        "app.services.ticker_cache_service._upsert_ticker_snapshot",
        _flaky_upsert,
    )
    monkeypatch.setattr(scheduler.time, "sleep", lambda _seconds: None)

    scheduler._sync_ai_scores_to_ticker_snapshots_sync(
        _SyncSnapshotFakeSupabase(),
        ticker="AMD",
        job_type="backfill",
        analysis_run_id="run-1",
    )

    assert calls["upsert"] == 2
    assert calls["payload"]["ticker"] == "AMD"
    assert calls["payload"]["safety_score"] == 82.0
    assert calls["payload"]["composite_score"] == 82.0
    assert calls["payload"]["news_sentiment_dim"] == 84
    assert calls["payload"]["macro_exposure_dim"] == 78
    assert calls["payload"]["dimension_inputs"] == {"macro_exposure": {"r_squared": 0.31}}


class _CanonicalFallbackSyncSnapshotFakeQuery(_SyncSnapshotFakeQuery):
    def execute(self):
        if self.table_name == "positions":
            return _FakeResult([{"id": "pos-amd", "ticker": "AMD"}])
        if self.table_name == "position_analyses":
            return _FakeResult([{"summary": "Real analysis summary.", "source_count": 5}])
        if self.table_name == "ticker_risk_snapshots" and self.selected == "safety_score":
            return _FakeResult([{"safety_score": 70.0}])
        if self.table_name == "ticker_risk_snapshots":
            return _FakeResult(
                [
                    {
                        "ticker": "AMD",
                        "snapshot_type": "daily",
                        "snapshot_date": "2026-05-22",
                        "grade": "A",
                        "safety_score": 82.0,
                        "composite_score": 82.0,
                        "confidence": 0.91,
                        "source_count": 5,
                        "llm_scoring_used": True,
                        "analysis_as_of": "2026-05-22T12:00:00+00:00",
                        "created_at": "2026-05-22T12:00:00+00:00",
                        "updated_at": "2026-05-22T12:00:00+00:00",
                        "financial_health": 80,
                        "news_sentiment_dim": 84,
                        "macro_exposure_dim": 78,
                        "sector_exposure": 79,
                        "volatility": 83,
                        "dimension_inputs": {"macro_exposure": {"r_squared": 0.31}},
                        "dimension_last_refreshed": {"macro_exposure": "2026-05-22T12:00:00+00:00"},
                        "factor_breakdown": None,
                    }
                ]
            )
        return _FakeResult([])


class _CanonicalFallbackSyncSnapshotFakeSupabase:
    def table(self, table_name):
        return _CanonicalFallbackSyncSnapshotFakeQuery(table_name)


def test_sync_ai_scores_uses_canonical_dimension_columns_when_factor_breakdown_missing(
    monkeypatch,
):
    captured = {}

    def _capture_upsert(_client, **kwargs):
        captured["payload"] = kwargs["payload"]
        return kwargs["payload"]

    monkeypatch.setattr(
        "app.services.supabase.get_supabase",
        lambda: _CanonicalFallbackSyncSnapshotFakeSupabase(),
    )
    monkeypatch.setattr(
        "app.services.ticker_cache_service._upsert_ticker_snapshot",
        _capture_upsert,
    )

    scheduler._sync_ai_scores_to_ticker_snapshots_sync(
        _CanonicalFallbackSyncSnapshotFakeSupabase(),
        ticker="AMD",
        job_type="backfill",
        analysis_run_id="run-1",
    )

    assert captured["payload"]["news_sentiment_dim"] == 84
    assert captured["payload"]["macro_exposure_dim"] == 78
    assert captured["payload"]["factor_breakdown"]["ai_dimensions"]["news_sentiment"] == 84
    assert captured["payload"]["factor_breakdown"]["ai_dimensions"]["macro_exposure"] == 78


class _StatusFakeResult:
    def __init__(self, data):
        self.data = data


class _StatusFakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.table_name == "user_preferences":
            return _StatusFakeResult(
                [
                    {
                        "digest_time": "07:15",
                        "notifications_enabled": True,
                    }
                ]
            )
        if self.table_name == "scheduler_jobs":
            return _StatusFakeResult(
                [
                    {
                        "user_id": "user-123",
                        "last_run_status": "failed",
                        "last_run_at": "2026-04-24T05:00:00+00:00",
                        "next_run_at": "2026-04-24T07:15:00+00:00",
                    }
                ]
            )
        return _StatusFakeResult([])


class _StatusFakeSupabase:
    def table(self, table_name):
        return _StatusFakeQuery(self, table_name)


def test_get_scheduler_status_exposes_last_run_summary():
    fake_scheduler = _FakeScheduler([scheduler._job_id_for_user("user-123")])
    fake_scheduler.jobs[
        scheduler._job_id_for_user("user-123")
    ].next_run_time = datetime(2026, 4, 24, 7, 15, tzinfo=timezone.utc)

    with (
        patch.object(scheduler, "scheduler", fake_scheduler),
        patch("app.services.supabase.get_supabase", return_value=_StatusFakeSupabase()),
    ):
        status = scheduler.get_scheduler_status_for_user("user-123")

    assert status["runtime_next_run_at"] == "2026-04-24T07:15:00+00:00"
    assert status["last_run_status"] == "failed"
    assert status["last_failure_at"] == "2026-04-24T05:00:00+00:00"
    assert status["last_success_at"] is None


class _MetadataRefreshStop(Exception):
    pass


class _ExecuteFakeResult:
    def __init__(self, data):
        self.data = data


class _ExecuteFakeQuery:
    def __init__(self, table_name, rows):
        self.table_name = table_name
        self.rows = rows
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
        if self.table_name == "ticker_metadata":
            raise _MetadataRefreshStop()
        rows = list(self.rows.get(self.table_name, []))
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self.in_filters.items():
            rows = [row for row in rows if row.get(key) in values]
        return _ExecuteFakeResult(rows)


class _ExecuteFakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, table_name):
        return _ExecuteFakeQuery(table_name, self.rows)


def test_execute_analysis_run_reaches_metadata_refresh_without_nameerror():
    fake_supabase = _ExecuteFakeSupabase(
        {
            "positions": [
                {"id": "pos-1", "user_id": "user-1", "ticker": "AMD"}
            ]
        }
    )

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    with (
        patch("app.services.supabase.get_supabase", return_value=fake_supabase),
        patch.object(scheduler, "upsert_ticker_metadata", return_value={"ticker": "AMD"}),
        patch.object(scheduler, "_set_analysis_stage"),
        patch.object(scheduler, "_record_scheduled_run_start"),
        patch.object(scheduler, "_record_scheduled_run_result"),
        patch.object(scheduler.asyncio, "to_thread", side_effect=_fake_to_thread),
    ):
        try:
            asyncio.run(
                scheduler.execute_analysis_run(
                    user_id="user-1",
                    analysis_run_id="run-1",
                    triggered_by="scheduled",
                    skip_metadata_refresh=False,
                )
            )
        except _MetadataRefreshStop:
            pass
        else:
            raise AssertionError("Expected metadata refresh sentinel after import path")
