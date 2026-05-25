from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.jobs import composite_recompute, portfolio_rollup


def test_snapshot_dimensions_fresh_requires_all_dimension_timestamps():
    now = datetime(2026, 5, 25, 12, tzinfo=timezone.utc)
    fresh_time = (now - timedelta(hours=1)).isoformat()
    snapshot = {
        "dimension_last_refreshed": {
            key: fresh_time for key in composite_recompute.DIMENSION_KEYS
        }
    }

    assert composite_recompute.snapshot_dimensions_fresh(snapshot, now=now)

    snapshot["dimension_last_refreshed"]["volatility"] = (
        now - timedelta(hours=30)
    ).isoformat()
    assert not composite_recompute.snapshot_dimensions_fresh(snapshot, now=now)


class _Query:
    def __init__(self, table_name, db):
        self.table_name = table_name
        self.db = db
        self.filters = {}
        self.payload = None
        self.limit_count = None
        self.mode = "select"

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = ("eq", value)
        return self

    def lt(self, key, value):
        self.filters[key] = ("lt", value)
        return self

    def in_(self, key, values):
        self.filters[key] = ("in", set(values))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def upsert(self, payload, on_conflict=None):
        self.mode = "upsert"
        self.payload = payload
        self.on_conflict = on_conflict
        return self

    def execute(self):
        if self.mode == "upsert":
            self.db.upserts.append((self.table_name, self.payload, self.on_conflict))
            return SimpleNamespace(data=[self.payload])
        rows = list(self.db.tables.get(self.table_name, []))
        for key, (operator, expected) in self.filters.items():
            if operator == "eq":
                rows = [row for row in rows if row.get(key) == expected]
            elif operator == "lt":
                rows = [row for row in rows if row.get(key) < expected]
            elif operator == "in":
                rows = [row for row in rows if row.get(key) in expected]
        if self.limit_count is not None:
            rows = rows[: self.limit_count]
        return SimpleNamespace(data=rows)


class _Supabase:
    def __init__(self, tables):
        self.tables = tables
        self.upserts = []

    def table(self, table_name):
        return _Query(table_name, self)


def test_portfolio_rollup_persists_two_day_delta():
    supabase = _Supabase(
        {
            "ticker_metadata": [
                {"ticker": "AAPL", "price": 100, "sector": "Technology"},
                {"ticker": "MSFT", "price": 200, "sector": "Technology"},
            ],
            "portfolio_risk_snapshots": [
                {
                    "user_id": "user-1",
                    "as_of_date": "2026-05-24",
                    "composite_score": 80,
                }
            ],
        }
    )
    positions = [
        {"ticker": "AAPL", "shares": 1, "current_price": 100},
        {"ticker": "MSFT", "shares": 1, "current_price": 200},
    ]
    snapshots = {
        "AAPL": {
            "composite_score": 70,
            "financial_health": 80,
            "news_sentiment_dim": 70,
            "macro_exposure_dim": 60,
            "sector_exposure": 65,
            "volatility": 75,
        },
        "MSFT": {
            "composite_score": 85,
            "financial_health": 90,
            "news_sentiment_dim": 80,
            "macro_exposure_dim": 75,
            "sector_exposure": 70,
            "volatility": 95,
        },
    }

    with patch.object(portfolio_rollup, "get_latest_risk_snapshot_map", return_value=snapshots):
        row = portfolio_rollup.rollup_user(supabase, "user-1", positions)

    assert row["composite_score"] == 80.0
    assert row["previous_score"] == 80.0
    assert row["score_delta"] == 0.0
    assert row["grade"] == "AA"
    assert row["dimensions"][0]["score"] == 86.7
    assert supabase.upserts[0][2] == "user_id,as_of_date"
