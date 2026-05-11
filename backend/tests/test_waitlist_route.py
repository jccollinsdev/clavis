import asyncio
import sys
import types
from types import SimpleNamespace

from pydantic import ValidationError
import pytest

_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

from app.routes import waitlist


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

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def execute(self):
        rows = list(self.supabase.rows.get(self.table_name, []))
        filtered_rows = [
            row for row in rows if all(row.get(key) == value for key, value in self.filters.items())
        ]

        if self._insert_payload is not None:
            if self.supabase.raise_on_insert:
                raise RuntimeError("duplicate key value violates unique constraint")

            created = {"id": f"{self.table_name}-new", **self._insert_payload}
            rows.append(created)
            self.supabase.rows[self.table_name] = rows
            return _FakeResult([created])

        return _FakeResult(filtered_rows)


class _FakeSupabase:
    def __init__(self, rows=None, raise_on_insert=False):
        self.rows = rows or {}
        self.raise_on_insert = raise_on_insert

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_waitlist_signup_normalizes_email():
    signup = waitlist.WaitlistSignup(email="  CLAVIX@Example.COM  ")

    assert signup.email == "clavix@example.com"


def test_waitlist_signup_rejects_invalid_email():
    with pytest.raises(ValidationError):
        waitlist.WaitlistSignup(email="not-an-email")


def test_waitlist_signup_rejects_empty_email():
    with pytest.raises(ValidationError):
        waitlist.WaitlistSignup(email="   ")


def test_join_waitlist_creates_row(monkeypatch):
    supabase = _FakeSupabase({"waitlist_signups": []})
    monkeypatch.setattr(waitlist, "get_supabase", lambda: supabase)

    request = SimpleNamespace(
        headers={
            "referer": "https://getclavix.com/",
            "user-agent": "Mozilla/5.0",
        }
    )

    result = asyncio.run(
        waitlist.join_waitlist(waitlist.WaitlistSignup(email="  New@Example.com  "), request)
    )

    assert result == {"status": "success", "message": "You are on the waitlist."}
    rows = supabase.rows["waitlist_signups"]
    assert len(rows) == 1
    assert rows[0]["email"] == "new@example.com"
    assert rows[0]["source"] == "website"
    assert rows[0]["referrer"] == "https://getclavix.com/"
    assert rows[0]["user_agent"] == "Mozilla/5.0"


def test_join_waitlist_returns_duplicate_for_existing_email(monkeypatch):
    supabase = _FakeSupabase(
        {
            "waitlist_signups": [
                {
                    "id": "waitlist-1",
                    "email": "existing@example.com",
                    "source": "website",
                }
            ]
        }
    )
    monkeypatch.setattr(waitlist, "get_supabase", lambda: supabase)

    request = SimpleNamespace(headers={})

    result = asyncio.run(
        waitlist.join_waitlist(waitlist.WaitlistSignup(email="existing@example.com"), request)
    )

    assert result == {
        "status": "duplicate",
        "message": "That email is already on the waitlist.",
    }
