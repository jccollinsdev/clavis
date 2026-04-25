import asyncio
import sys
import types
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException

from app.models.position import PositionCreate

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

from app.routes import holdings


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self._insert_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def update(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self._insert_payload is not None:
            created = {
                "id": "pos-123",
                "created_at": "2026-04-18T00:00:00Z",
                "updated_at": "2026-04-18T00:00:00Z",
                "current_price": None,
                "analysis_started_at": self._insert_payload.get("analysis_started_at"),
                **self._insert_payload,
            }
            self.supabase.positions.append(created)
            return _FakeResult([created])

        if self.table_name == "positions":
            rows = list(self.supabase.positions)
            for key, value in self.filters.items():
                rows = [row for row in rows if row.get(key) == value]
            return _FakeResult(rows)

        if self.table_name == "analysis_runs":
            rows = list(self.supabase.analysis_runs)
            for key, value in self.filters.items():
                rows = [row for row in rows if row.get(key) == value]
            return _FakeResult(rows)

        return _FakeResult([])


class _FakeSupabase:
    def __init__(self, positions=None, analysis_runs=None):
        self.positions = positions or []
        self.analysis_runs = analysis_runs or []

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_create_holding_returns_backend_workflow_status():
    position = PositionCreate(
        ticker="hood",
        shares=2,
        purchase_price=37.5,
        archetype="growth",
    )
    supabase = _FakeSupabase()
    workflow = {
        "holding_id": "pos-123",
        "ticker": "HOOD",
        "analysis_state": "queued",
        "analysis_run_id": "run-1",
        "latest_refresh_job": {"id": "job-1", "status": "completed"},
        "coverage_state": "substantive",
        "coverage_note": "Coverage is substantive.",
        "analysis_as_of": "2026-04-18T00:00:00Z",
        "news_as_of": "2026-04-17T00:00:00Z",
        "price_as_of": "2026-04-18T00:00:00Z",
        "position": {"id": "pos-123", "ticker": "HOOD"},
        "source": "user",
    }

    with (
        patch.object(holdings, "get_supabase", return_value=supabase),
        patch.object(
            holdings,
            "ensure_ticker_in_universe",
            return_value={"ticker": "HOOD", "company_name": "Robinhood Markets"},
        ) as ensure_mock,
        patch.object(
            holdings.asyncio,
            "to_thread",
            side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs),
        ) as to_thread_mock,
        patch.object(
            holdings,
            "refresh_ticker_snapshot",
            return_value={"id": "job-1", "status": "completed"},
        ) as refresh_snapshot_mock,
        patch.object(
            holdings,
            "enqueue_analysis_run",
            return_value={"status": "queued", "analysis_run_id": "run-1"},
        ) as enqueue_mock,
        patch.object(
            holdings, "build_holding_workflow_response", return_value=workflow
        ) as workflow_mock,
        patch.object(holdings, "refresh_position_price") as refresh_price_mock,
    ):
        created = asyncio.run(
            holdings.create_holding(position, BackgroundTasks(), user_id="user-1")
        )

    assert created == workflow
    assert supabase.positions[0]["ticker"] == "HOOD"
    ensure_mock.assert_called_once_with(supabase, "hood")
    refresh_snapshot_mock.assert_called_once()
    enqueue_mock.assert_awaited_once()
    workflow_mock.assert_called_once()
    refresh_price_mock.assert_not_called()
    to_thread_mock.assert_called_once()


def test_create_holding_reuses_existing_holding_without_new_jobs():
    position = PositionCreate(
        ticker="hood",
        shares=2,
        purchase_price=37.5,
        archetype="growth",
    )
    supabase = _FakeSupabase(
        positions=[
            {
                "id": "pos-123",
                "user_id": "user-1",
                "ticker": "HOOD",
                "shares": 2,
                "purchase_price": 37.5,
                "archetype": "growth",
                "created_at": "2026-04-18T00:00:00Z",
                "updated_at": "2026-04-18T00:00:00Z",
            }
        ]
    )

    with (
        patch.object(holdings, "get_supabase", return_value=supabase),
        patch.object(
            holdings, "ensure_ticker_in_universe", return_value={"ticker": "HOOD"}
        ),
        patch.object(
            holdings,
            "build_holding_workflow_response",
            return_value={
                "holding_id": "pos-123",
                "ticker": "HOOD",
                "analysis_state": "ready",
            },
        ) as workflow_mock,
        patch.object(holdings, "refresh_ticker_snapshot") as refresh_snapshot_mock,
        patch.object(holdings, "enqueue_analysis_run") as enqueue_mock,
    ):
        created = asyncio.run(
            holdings.create_holding(position, BackgroundTasks(), user_id="user-1")
        )

    assert created["analysis_state"] == "ready"
    workflow_mock.assert_called_once()
    refresh_snapshot_mock.assert_not_called()
    enqueue_mock.assert_not_called()


def test_create_holding_rejects_unsupported_ticker():
    position = PositionCreate(
        ticker="zzzz",
        shares=1,
        purchase_price=1,
        archetype="growth",
    )
    supabase = _FakeSupabase()

    with (
        patch.object(holdings, "get_supabase", return_value=supabase),
        patch.object(holdings, "ensure_ticker_in_universe", return_value=None),
    ):
        try:
            asyncio.run(
                holdings.create_holding(position, BackgroundTasks(), user_id="user-1")
            )
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "shared ticker cache" in exc.detail
        else:
            raise AssertionError("expected HTTPException")
