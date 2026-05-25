from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.pipeline.scheduler import grade_boundary_alert_allowed
from app.routes import digest, tickers


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table_name: str):
        self.db = db
        self.table_name = table_name
        self.rows = list(db.tables.get(table_name, []))
        self._insert_payload = None
        self._limit = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.rows = [row for row in self.rows if row.get(field) == value]
        return self

    def gte(self, field, value):
        self.rows = [row for row in self.rows if str(row.get(field)) >= str(value)]
        return self

    def lt(self, field, value):
        self.rows = [row for row in self.rows if str(row.get(field)) < str(value)]
        return self

    def order(self, field, desc=False):
        self.rows = sorted(self.rows, key=lambda row: row.get(field) or 0, reverse=desc)
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def execute(self):
        if self._insert_payload is not None:
            payload = dict(self._insert_payload)
            payload.setdefault("id", f"{self.table_name}-{len(self.db.tables.get(self.table_name, [])) + 1}")
            self.db.tables.setdefault(self.table_name, []).append(payload)
            return _Result([payload])
        rows = self.rows[: self._limit] if self._limit is not None else self.rows
        return _Result(rows)


class _DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Query(self, name)


@pytest.mark.asyncio
async def test_free_refresh_allows_three_attempts_then_429(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    db = _DB(
        {
            "user_preferences": [{"user_id": "u1", "subscription_tier": "free"}],
            "refresh_attempts": [
                {"user_id": "u1", "ticker": "AAPL", "attempted_at": now},
                {"user_id": "u1", "ticker": "MSFT", "attempted_at": now},
                {"user_id": "u1", "ticker": "NVDA", "attempted_at": now},
            ],
        }
    )
    monkeypatch.setattr(tickers, "get_supabase", lambda: db)
    monkeypatch.setattr(tickers, "refresh_ticker_snapshot", lambda *_args, **_kwargs: {"id": "job-1", "status": "completed"})

    with pytest.raises(HTTPException) as exc:
        await tickers.refresh_ticker("TSLA", "u1")

    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "86400"


@pytest.mark.asyncio
async def test_free_refresh_records_allowed_attempt(monkeypatch):
    db = _DB({"user_preferences": [{"user_id": "u1", "subscription_tier": "free"}], "refresh_attempts": []})
    monkeypatch.setattr(tickers, "get_supabase", lambda: db)
    monkeypatch.setattr(tickers, "refresh_ticker_snapshot", lambda *_args, **_kwargs: {"id": "job-1", "status": "completed"})

    result = await tickers.refresh_ticker("TSLA", "u1")

    assert result["job_id"] == "job-1"
    assert db.tables["refresh_attempts"][0]["ticker"] == "TSLA"


def test_outside_universe_detail_returns_limited_payload():
    db = _DB(
        {
            "positions": [
                {
                    "id": "pos-1",
                    "user_id": "u1",
                    "ticker": "BBAI",
                    "outside_universe": True,
                    "shares": 1,
                    "purchase_price": 5,
                }
            ]
        }
    )

    result = tickers._outside_universe_detail(db, "u1", "BBAI")

    assert result["outside_universe"] is True
    assert result["limited_data"] is True
    assert result["coverage_state"] == "limited"


def test_digest_issue_number_is_monotonic():
    db = _DB({"digests": [{"user_id": "u1", "issue_number": 2}]})

    assert digest._next_issue_number(db, "u1") == 3


def test_hysteresis_requires_two_consecutive_boundary_days():
    one_day_cross = [
        {"grade": "A", "composite_score": 72},
        {"grade": "BBB", "composite_score": 68},
    ]
    two_day_cross = [
        {"grade": "A", "composite_score": 72},
        {"grade": "BBB", "composite_score": 68},
        {"grade": "BBB", "composite_score": 67},
    ]

    assert grade_boundary_alert_allowed(one_day_cross) is False
    assert grade_boundary_alert_allowed(two_day_cross) is True
