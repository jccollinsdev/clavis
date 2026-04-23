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


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.payload = None

    def select(self, columns):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        self.supabase.inserts.append({"table": self.table_name, "payload": payload})
        return self

    def execute(self):
        if self.table_name == "analysis_runs":
            return _FakeResult([{**(self.payload or {}), "id": "run-1"}])
        return _FakeResult([])


class _FakeSupabase:
    def __init__(self):
        self.inserts = []

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_create_analysis_run_persists_target_tickers(monkeypatch):
    fake_supabase = _FakeSupabase()
    monkeypatch.setattr("app.services.supabase.get_supabase", lambda: fake_supabase)

    run = asyncio.run(
        scheduler.create_analysis_run(
            "user-1",
            "scheduled",
            target_tickers=["hood", "HOOD", "AAPL"],
        )
    )

    assert run["target_tickers"] == ["HOOD", "AAPL"]
    assert fake_supabase.inserts[0]["payload"]["target_tickers"] == ["HOOD", "AAPL"]


def test_enqueue_analysis_run_forwards_target_tickers(monkeypatch):
    fake_task = SimpleNamespace(add_done_callback=lambda callback: None)
    fake_supabase = _FakeSupabase()

    with (
        patch.object(
            scheduler, "create_analysis_run", return_value={"id": "run-1"}
        ) as create_run_mock,
        patch.object(scheduler.asyncio, "create_task", return_value=fake_task),
        patch.object(scheduler, "_fail_stale_runs"),
        patch("app.services.supabase.get_supabase", return_value=fake_supabase),
    ):
        asyncio.run(
            scheduler.enqueue_analysis_run(
                user_id="user-1",
                triggered_by="scheduled",
                target_tickers=["hood", "aapl"],
                allow_parallel_runs=True,
            )
        )

    create_run_mock.assert_awaited_once()
    assert create_run_mock.await_args.kwargs["target_tickers"] == ["hood", "aapl"]
