import asyncio
import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace
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

from app.pipeline import scheduler


class _FakeScheduler:
    def __init__(self, existing_job_ids=None):
        self.jobs = {
            job_id: SimpleNamespace(id=job_id, next_run_time=None)
            for job_id in (existing_job_ids or [])
        }
        self.added = []
        self.removed = []

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
    assert job.func is scheduler._cleanup_old_news_items


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

    assert result == {"status": "structural_refresh_complete", "user_id": "user-123"}
    assert len(fake_supabase.upserts) == 1
    assert fake_supabase.upserts[0]["table"] == "asset_safety_profiles"
    assert fake_supabase.upserts[0]["payload"]["ticker"] == "HOOD"
    assert fake_supabase.upserts[0]["on_conflict"] == "ticker,as_of_date"


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
