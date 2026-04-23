from datetime import datetime, timezone, timedelta
import sys
import types
from unittest.mock import patch

from fastapi import HTTPException


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

from app.routes import digest as digest_route
from app.routes import trigger as trigger_route


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, table_name, table_data):
        self.table_name = table_name
        self.table_data = table_data
        self.filters = {}
        self.selected = None

    def select(self, columns):
        self.selected = columns
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def gte(self, key, value):
        self.filters[f"gte:{key}"] = value
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, payload):
        return self

    def update(self, payload):
        return self

    def delete(self):
        return self

    def execute(self):
        return _FakeResult(self.table_data.get(self.table_name, []))


class _FakeSupabase:
    def __init__(self, table_data):
        self.table_data = table_data

    def table(self, table_name):
        return _FakeQuery(table_name, self.table_data)


def test_digest_force_refresh_is_rate_limited():
    now = datetime.now(timezone.utc)
    fake_supabase = _FakeSupabase(
        {
            "analysis_runs": [],
            "digests": [],
            "positions": [{"id": "pos-1", "ticker": "HOOD"}],
            "user_preferences": [
                {"last_manual_refresh_at": (now - timedelta(minutes=30)).isoformat()}
            ],
        }
    )

    with patch.object(digest_route, "get_supabase", return_value=fake_supabase):
        try:
            import asyncio

            asyncio.run(digest_route.get_digest(force_refresh=True, user_id="user-1"))
            assert False, "expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 429


def test_manual_analysis_is_capped_at_three_per_day():
    fake_supabase = _FakeSupabase(
        {
            "analysis_runs": [
                {"id": "run-1"},
                {"id": "run-2"},
                {"id": "run-3"},
            ]
        }
    )

    with (
        patch.object(trigger_route, "get_supabase", return_value=fake_supabase),
        patch.object(trigger_route, "enqueue_analysis_run") as enqueue_mock,
    ):
        try:
            import asyncio

            asyncio.run(trigger_route.trigger_analysis(user_id="user-1"))
            assert False, "expected HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 429

    enqueue_mock.assert_not_called()
