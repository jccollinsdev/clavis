"""
Tests for DELETE /account endpoint.

Covers:
  1. Full data deletion (positions, analyses, alerts, scheduler_jobs, etc.)
  2. No portfolio / no holdings
  3. Partial onboarding data (no preferences row)
  4. SnapTrade unavailable (best-effort — must not block deletion)
  5. Unauthorized request (no user_id on request state)
"""

import asyncio
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

# ── Stub out heavy optional imports before any app code is imported ──────────
_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

_fake_openai = types.ModuleType("openai")


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


_fake_openai.OpenAI = _FakeOpenAI
sys.modules.setdefault("openai", _fake_openai)

from app.routes import account  # noqa: E402  (must come after stubs)


# ── Fake Supabase client ──────────────────────────────────────────────────────

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Minimal supabase query builder that supports select/delete/eq/in_."""

    def __init__(self, db: "_FakeSupabase", table_name: str):
        self._db = db
        self._table = table_name
        self._filters: dict = {}
        self._in_filters: dict = {}
        self._is_delete = False

    def select(self, *_args, **_kwargs):
        return self

    def delete(self):
        self._is_delete = True
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def in_(self, key, values):
        self._in_filters[key] = set(values)
        return self

    def execute(self) -> _FakeResult:
        rows = list(self._db.rows.get(self._table, []))

        def matches(row):
            for k, v in self._filters.items():
                if row.get(k) != v:
                    return False
            for k, vs in self._in_filters.items():
                if row.get(k) not in vs:
                    return False
            return True

        matched = [r for r in rows if matches(r)]

        if self._is_delete:
            remaining = [r for r in rows if not matches(r)]
            self._db.rows[self._table] = remaining
            return _FakeResult(matched)

        return _FakeResult(matched)


class _FakeAuthAdmin:
    def __init__(self):
        self.deleted_user_ids: list[str] = []
        self.should_raise: Exception | None = None

    def delete_user(self, user_id: str) -> None:
        if self.should_raise:
            raise self.should_raise
        self.deleted_user_ids.append(user_id)


class _FakeAuth:
    def __init__(self):
        self.admin = _FakeAuthAdmin()


class _FakeSupabase:
    def __init__(self, rows: dict):
        self.rows = {k: list(v) for k, v in rows.items()}
        self.auth = _FakeAuth()

    def table(self, table_name: str) -> _FakeQuery:
        if table_name not in self.rows:
            self.rows[table_name] = []
        return _FakeQuery(self, table_name)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_request(user_id: str = "user-abc"):
    return SimpleNamespace(state=SimpleNamespace(user_id=user_id))


def _run(coro):
    return asyncio.run(coro)


# ── Test 1: Full data deletion ────────────────────────────────────────────────

def test_delete_account_full_data(monkeypatch):
    """All tables cleaned up; auth user deleted; returns 'deleted' status."""
    position_id = "pos-1"
    watchlist_id = "wl-1"

    db = _FakeSupabase({
        "positions": [{"id": position_id, "user_id": "user-abc"}],
        "analysis_runs": [{"id": "run-1", "user_id": "user-abc"}],
        "position_analyses": [{"id": "pa-1", "position_id": position_id}],
        "event_analyses": [{"id": "ea-1", "position_id": position_id}],
        "risk_scores": [{"id": "rs-1", "position_id": position_id}],
        "alerts": [{"id": "al-1", "user_id": "user-abc"}],
        "digests": [{"id": "dg-1", "user_id": "user-abc"}],
        "news_items": [{"id": "ni-1", "user_id": "user-abc"}],
        "portfolio_risk_snapshots": [{"id": "prs-1", "user_id": "user-abc"}],
        "scheduler_jobs": [{"id": "sj-1", "user_id": "user-abc"}],
        "user_preferences": [{"id": "up-1", "user_id": "user-abc"}],
        "watchlists": [{"id": watchlist_id, "user_id": "user-abc"}],
        "watchlist_items": [{"id": "wi-1", "watchlist_id": watchlist_id}],
    })

    monkeypatch.setattr(account, "get_supabase", lambda: db)
    monkeypatch.setattr(account, "snaptrade_is_configured", lambda: False)

    result = _run(account.delete_account(user_id="user-abc"))

    assert result["status"] == "deleted"
    assert result["user_id"] == "user-abc"
    assert db.auth.admin.deleted_user_ids == ["user-abc"]

    # All user-owned rows must be gone
    for table in [
        "positions", "analysis_runs", "position_analyses", "event_analyses",
        "risk_scores", "alerts", "digests", "news_items",
        "portfolio_risk_snapshots", "scheduler_jobs",
        "user_preferences", "watchlists", "watchlist_items",
    ]:
        assert db.rows[table] == [], f"Expected {table} to be empty after deletion"


# ── Test 2: No portfolio / no holdings ───────────────────────────────────────

def test_delete_account_no_portfolio(monkeypatch):
    """User with zero positions and watchlists — deletion succeeds idempotently."""
    db = _FakeSupabase({
        "user_preferences": [{"id": "up-1", "user_id": "user-abc"}],
        "scheduler_jobs": [{"id": "sj-1", "user_id": "user-abc"}],
    })

    monkeypatch.setattr(account, "get_supabase", lambda: db)
    monkeypatch.setattr(account, "snaptrade_is_configured", lambda: False)

    result = _run(account.delete_account(user_id="user-abc"))

    assert result["status"] == "deleted"
    assert db.auth.admin.deleted_user_ids == ["user-abc"]
    assert db.rows["user_preferences"] == []
    assert db.rows["scheduler_jobs"] == []
    # position-related counts should be 0 (skipped entirely)
    assert "position_analyses" not in result["deleted_counts"]
    assert "risk_scores" not in result["deleted_counts"]


# ── Test 3: Partial onboarding data ─────────────────────────────────────────

def test_delete_account_partial_onboarding(monkeypatch):
    """User who never completed onboarding has no preferences row — still succeeds."""
    db = _FakeSupabase({})  # completely empty — no rows anywhere

    monkeypatch.setattr(account, "get_supabase", lambda: db)
    monkeypatch.setattr(account, "snaptrade_is_configured", lambda: False)

    result = _run(account.delete_account(user_id="user-abc"))

    assert result["status"] == "deleted"
    assert db.auth.admin.deleted_user_ids == ["user-abc"]


# ── Test 4: SnapTrade unavailable ─────────────────────────────────────────────

def test_delete_account_snaptrade_unavailable(monkeypatch):
    """SnapTrade configured but remote call raises — deletion still succeeds."""
    db = _FakeSupabase({
        "scheduler_jobs": [{"id": "sj-1", "user_id": "user-abc"}],
        "user_preferences": [{"id": "up-1", "user_id": "user-abc"}],
    })

    monkeypatch.setattr(account, "get_supabase", lambda: db)
    monkeypatch.setattr(account, "snaptrade_is_configured", lambda: True)

    def _failing_snaptrade_delete(_user_id):
        raise RuntimeError("SnapTrade API unreachable")

    monkeypatch.setattr(account, "delete_snaptrade_user", _failing_snaptrade_delete)

    result = _run(account.delete_account(user_id="user-abc"))

    assert result["status"] == "deleted"
    assert result["snaptrade_deleted"] is False
    assert db.auth.admin.deleted_user_ids == ["user-abc"]


def test_delete_account_snaptrade_not_configured(monkeypatch):
    """SnapTrade not configured — deletion succeeds and snaptrade_deleted is False."""
    db = _FakeSupabase({})

    monkeypatch.setattr(account, "get_supabase", lambda: db)
    monkeypatch.setattr(account, "snaptrade_is_configured", lambda: False)

    result = _run(account.delete_account(user_id="user-abc"))

    assert result["status"] == "deleted"
    assert result["snaptrade_deleted"] is False


# ── Test 5: Auth deletion failure ─────────────────────────────────────────────

def test_delete_account_auth_deletion_fails(monkeypatch):
    """If Supabase auth.admin.delete_user raises, endpoint returns 500."""
    db = _FakeSupabase({})
    db.auth.admin.should_raise = RuntimeError("auth service unavailable")

    monkeypatch.setattr(account, "get_supabase", lambda: db)
    monkeypatch.setattr(account, "snaptrade_is_configured", lambda: False)

    with pytest.raises(HTTPException) as exc_info:
        _run(account.delete_account(user_id="user-abc"))

    assert exc_info.value.status_code == 500
    assert "auth record" in exc_info.value.detail.lower() or "support" in exc_info.value.detail.lower()


# ── Test 6: Missing user_id → 401 ─────────────────────────────────────────────

def test_delete_account_unauthorized():
    """Request with no user_id on state raises 401, not 500."""
    request = SimpleNamespace(state=SimpleNamespace(user_id=None))

    with pytest.raises(HTTPException) as exc_info:
        account.get_user_id(request)

    assert exc_info.value.status_code == 401


# ── Test 7: scheduler_jobs and portfolio_risk_snapshots are deleted ──────────

def test_delete_account_clears_scheduler_jobs_and_risk_snapshots(monkeypatch):
    """Regression: these two tables were previously skipped, causing a FK 500."""
    db = _FakeSupabase({
        "scheduler_jobs": [{"id": "sj-1", "user_id": "user-abc"}],
        "portfolio_risk_snapshots": [{"id": "prs-1", "user_id": "user-abc"}],
    })

    monkeypatch.setattr(account, "get_supabase", lambda: db)
    monkeypatch.setattr(account, "snaptrade_is_configured", lambda: False)

    result = _run(account.delete_account(user_id="user-abc"))

    assert result["status"] == "deleted"
    assert db.rows["scheduler_jobs"] == []
    assert db.rows["portfolio_risk_snapshots"] == []
    assert result["deleted_counts"]["scheduler_jobs"] == 1
    assert result["deleted_counts"]["portfolio_risk_snapshots"] == 1
    assert db.auth.admin.deleted_user_ids == ["user-abc"]
