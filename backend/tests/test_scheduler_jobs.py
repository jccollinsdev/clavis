import asyncio
import sys
import types
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
