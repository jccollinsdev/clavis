import sys
import types
from types import SimpleNamespace

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

from app.routes import preferences


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self._update_payload = None
        self._insert_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def update(self, payload):
        self._update_payload = payload
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def execute(self):
        rows = list(self.supabase.rows.get(self.table_name, []))
        filtered_rows = [row for row in rows if all(row.get(k) == v for k, v in self.filters.items())]

        if self._update_payload is not None:
            for row in rows:
                if all(row.get(k) == v for k, v in self.filters.items()):
                    row.update(self._update_payload)
            self.supabase.rows[self.table_name] = rows
            return _FakeResult(filtered_rows)

        if self._insert_payload is not None:
            created = {"id": f"{self.table_name}-new", **self._insert_payload}
            rows.append(created)
            self.supabase.rows[self.table_name] = rows
            return _FakeResult([created])

        return _FakeResult(filtered_rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_update_preferences_reschedules_when_notifications_toggle_changes(monkeypatch):
    supabase = _FakeSupabase(
        {
            "user_preferences": [
                {
                    "id": "pref-1",
                    "user_id": "user-1",
                    "digest_time": "07:00",
                    "notifications_enabled": True,
                    "summary_length": "standard",
                    "weekday_only": False,
                }
            ]
        }
    )
    rescheduled = []

    monkeypatch.setattr(preferences, "get_supabase", lambda: supabase)

    async def fake_reschedule_user_digest(user_id: str):
        rescheduled.append(user_id)

    monkeypatch.setattr(
        "app.pipeline.scheduler.reschedule_user_digest", fake_reschedule_user_digest
    )

    request = SimpleNamespace(state=SimpleNamespace(user_id="user-1"))

    import asyncio

    result = asyncio.run(
        preferences.update_preferences(
            preferences.PreferencesUpdate(notifications_enabled=False),
            request,
        )
    )

    assert result == {"status": "ok"}
    assert rescheduled == ["user-1"]
    assert supabase.rows["user_preferences"][0]["notifications_enabled"] is False
