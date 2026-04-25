import asyncio
import os
import sys
import types
from datetime import datetime, timezone

os.environ.setdefault("SUPABASE_URL", "https://example.com")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "dummy")
os.environ.setdefault("SUPABASE_JWT_SECRET", "dummy")
os.environ.setdefault("MINIMAX_API_KEY", "dummy")

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

from app.routes import dashboard, digest as digest_route


def test_portfolio_score_fields_use_digest_contract():
    digest = {
        "overall_score": 61.2,
        "overall_grade": "B",
        "generated_at": "2026-04-24T14:00:00Z",
        "analysis_run_id": "run-123",
    }

    fields = dashboard._portfolio_score_fields(digest)

    assert fields == {
        "overall_score": 61.2,
        "overall_grade": "B",
        "score_source": "digest",
        "score_as_of": "2026-04-24T14:00:00Z",
        "score_version": "run-123",
    }


def test_portfolio_score_fields_return_unknown_state_without_digest():
    assert dashboard._portfolio_score_fields(None) == {
        "overall_score": None,
        "overall_grade": None,
        "score_source": None,
        "score_as_of": None,
        "score_version": None,
    }


class _DigestFakeResult:
    def __init__(self, data):
        self.data = data


class _DigestFakeQuery:
    def __init__(self, table_name, data_map):
        self.table_name = table_name
        self.data_map = data_map

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return _DigestFakeResult(self.data_map.get(self.table_name, []))


class _DigestFakeSupabase:
    def __init__(self, data_map):
        self.data_map = data_map

    def table(self, table_name):
        return _DigestFakeQuery(table_name, self.data_map)


def test_get_digest_returns_portfolio_score_fields_for_saved_digest(monkeypatch):
    fake_supabase = _DigestFakeSupabase(
        {
            "analysis_runs": [
                {
                    "id": "run-123",
                    "user_id": "user-1",
                    "status": "completed",
                    "started_at": "2026-04-24T10:00:00Z",
                }
            ],
            "digests": [
                {
                    "id": "digest-1",
                    "user_id": "user-1",
                    "analysis_run_id": "run-123",
                    "overall_score": 61.2,
                    "overall_grade": "B",
                    "generated_at": "2026-04-24T14:00:00Z",
                    "content": "digest content",
                }
            ],
            "positions": [],
        }
    )

    monkeypatch.setattr(digest_route, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(
        digest_route,
        "select_latest_trading_day_digest",
        lambda rows, _now: rows[0] if rows else None,
    )

    response = asyncio.run(digest_route.get_digest(user_id="user-1"))

    assert response["overall_score"] == 61.2
    assert response["overall_grade"] == "B"
    assert response["score_source"] == "digest"
    assert response["score_as_of"] == "2026-04-24T14:00:00Z"
    assert response["score_version"] == "run-123"
