import asyncio
import sys
import types
from unittest.mock import patch

from fastapi import BackgroundTasks

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


class _FakeInsertQuery:
    def __init__(self, table_name: str, recorder: dict):
        self._table_name = table_name
        self._recorder = recorder

    def execute(self):
        if self._table_name != "positions":
            return _FakeResult([])
        created = {
            "id": "pos-123",
            "ticker": self._recorder["inserted"]["ticker"],
            "user_id": self._recorder["inserted"]["user_id"],
            "shares": self._recorder["inserted"]["shares"],
            "purchase_price": self._recorder["inserted"]["purchase_price"],
            "archetype": self._recorder["inserted"]["archetype"],
            "current_price": None,
            "analysis_started_at": self._recorder["inserted"]["analysis_started_at"],
            "created_at": "2026-04-18T00:00:00Z",
            "updated_at": "2026-04-18T00:00:00Z",
        }
        return _FakeResult([created])


class _FakeTable:
    def __init__(self, table_name: str, recorder: dict):
        self._table_name = table_name
        self._recorder = recorder

    def insert(self, payload):
        self._recorder["inserted"] = payload
        return _FakeInsertQuery(self._table_name, self._recorder)


class _FakeSupabase:
    def __init__(self):
        self.recorder = {}

    def table(self, table_name):
        return _FakeTable(table_name, self.recorder)


def test_create_holding_auto_adds_new_ticker_to_shared_universe():
    position = PositionCreate(
        ticker="hood",
        shares=2,
        purchase_price=37.5,
        archetype="growth",
    )
    supabase = _FakeSupabase()

    with (
        patch.object(holdings, "get_supabase", return_value=supabase),
        patch.object(
            holdings,
            "ensure_ticker_in_universe",
            return_value={"ticker": "HOOD", "company_name": "Robinhood Markets"},
        ) as ensure_mock,
        patch.object(holdings, "refresh_position_price") as refresh_price_mock,
        patch.object(holdings, "refresh_ticker_snapshot") as refresh_snapshot_mock,
    ):
        created = asyncio.run(
            holdings.create_holding(position, BackgroundTasks(), user_id="user-1")
        )

    assert created["ticker"] == "HOOD"
    assert supabase.recorder["inserted"]["ticker"] == "HOOD"
    assert supabase.recorder["inserted"]["user_id"] == "user-1"
    ensure_mock.assert_called_once_with(supabase, "hood")
    refresh_price_mock.assert_not_called()
    refresh_snapshot_mock.assert_not_called()
