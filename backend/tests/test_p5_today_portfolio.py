from __future__ import annotations

from datetime import date, timezone, datetime

import pytest

from app.jobs import earnings_calendar
from app.routes import portfolio, today


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table_name: str):
        self.db = db
        self.table_name = table_name
        self.rows = list(db.tables.get(table_name, []))
        self._limit: int | None = None
        self._upsert_rows = None
        self._on_conflict = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.rows = [row for row in self.rows if row.get(field) == value]
        return self

    def in_(self, field, values):
        allowed = set(values)
        self.rows = [row for row in self.rows if row.get(field) in allowed]
        return self

    def gte(self, field, value):
        self.rows = [row for row in self.rows if str(row.get(field)) >= str(value)]
        return self

    def lte(self, field, value):
        self.rows = [row for row in self.rows if str(row.get(field)) <= str(value)]
        return self

    def order(self, field, desc=False):
        self.rows = sorted(
            self.rows,
            key=lambda row: row.get(field) or "",
            reverse=desc,
        )
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def upsert(self, rows, on_conflict=None):
        self._upsert_rows = rows if isinstance(rows, list) else [rows]
        self._on_conflict = on_conflict
        return self

    def execute(self):
        if self._upsert_rows is not None:
            target = self.db.tables.setdefault(self.table_name, [])
            if self._on_conflict:
                keys = [key.strip() for key in self._on_conflict.split(",")]
                for row in self._upsert_rows:
                    target[:] = [
                        existing
                        for existing in target
                        if any(existing.get(key) != row.get(key) for key in keys)
                    ]
                    target.append(row)
            else:
                target.extend(self._upsert_rows)
            return _Result(self._upsert_rows)
        rows = self.rows[: self._limit] if self._limit is not None else self.rows
        return _Result(rows)


class _DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Query(self, name)


def _fresh_job(job_id: str = "daily_sector_snapshot") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "job_id": job_id,
        "status": "completed",
        "started_at": now,
        "completed_at": now,
    }


def test_sector_exposure_weights_sum_to_one():
    db = _DB(
        {
            "positions": [
                {"user_id": "u1", "ticker": "AAPL", "shares": 2, "current_price": 100},
                {"user_id": "u1", "ticker": "JPM", "shares": 1, "current_price": 200},
            ],
            "ticker_metadata": [
                {"ticker": "AAPL", "sector": "Technology", "price": 100},
                {"ticker": "JPM", "sector": "Financials", "price": 200},
            ],
            "sector_regime_snapshots": [
                {
                    "source_etf": "XLK",
                    "sector": "Technology",
                    "etf_day_change_pct": 1.2,
                    "snapshot_date": "2026-05-25",
                    "data_status": "fresh",
                },
                {
                    "source_etf": "XLF",
                    "sector": "Financials",
                    "etf_day_change_pct": -0.4,
                    "snapshot_date": "2026-05-25",
                    "data_status": "fresh",
                },
            ],
        }
    )

    rows = portfolio.build_sector_exposure(db, "u1")

    assert round(sum(row["portfolio_weight"] for row in rows), 6) == 1.0
    assert {row["etf"] for row in rows} == {"XLK", "XLF"}
    assert rows[0]["etf_day_change_pct"] is not None


def test_earnings_calendar_upserts_by_ticker_and_report_date(monkeypatch):
    db = _DB(
        {
            "positions": [{"ticker": "AAPL"}],
            "watchlist_items": [{"ticker": "MSFT"}],
            "ticker_universe": [{"ticker": "AAPL"}, {"ticker": "MSFT"}],
            "earnings_calendar": [
                {
                    "ticker": "AAPL",
                    "report_date": date.today().isoformat(),
                    "est_eps": 1.0,
                }
            ],
        }
    )
    monkeypatch.setattr(earnings_calendar, "get_supabase", lambda: db)
    monkeypatch.setattr(earnings_calendar, "list_active_sp500_tickers", lambda _db: ["AAPL", "MSFT"])
    monkeypatch.setattr(
        earnings_calendar,
        "_request_earnings",
        lambda _from, _to: [
            {
                "symbol": "AAPL",
                "date": date.today().isoformat(),
                "epsEstimate": 2.34,
                "revenueEstimate": 90000000000,
                "hour": "amc",
                "quarter": "Q2",
            },
            {
                "symbol": "ZZZZ",
                "date": date.today().isoformat(),
                "epsEstimate": 9.99,
            },
        ],
    )

    result = earnings_calendar.run()

    assert result["items_processed"] == 1
    assert len(db.tables["earnings_calendar"]) == 1
    assert db.tables["earnings_calendar"][0]["est_eps"] == 2.34


@pytest.mark.asyncio
async def test_today_envelope_includes_sector_calendar_and_freshness(monkeypatch):
    report_date = date.today().isoformat()
    db = _DB(
        {
            "positions": [
                {"user_id": "u1", "ticker": "AAPL", "shares": 2, "current_price": 100},
                {"user_id": "u1", "ticker": "JPM", "shares": 1, "current_price": 200},
            ],
            "ticker_metadata": [
                {"ticker": "AAPL", "sector": "Technology", "price": 100},
                {"ticker": "JPM", "sector": "Financials", "price": 200},
            ],
            "sector_regime_snapshots": [
                {
                    "source_etf": "XLK",
                    "sector": "Technology",
                    "etf_day_change_pct": 0.8,
                    "snapshot_date": report_date,
                },
                {
                    "source_etf": "XLF",
                    "sector": "Financials",
                    "etf_day_change_pct": -0.2,
                    "snapshot_date": report_date,
                },
            ],
            "alerts": [],
            "digests": [],
            "portfolio_risk_snapshots": [],
            "earnings_calendar": [
                {
                    "ticker": "AAPL",
                    "report_date": report_date,
                    "est_eps": 2.34,
                    "est_revenue": 90000000000,
                    "time_of_day": "amc",
                    "source": "finnhub",
                }
            ],
            "job_runs": [_fresh_job("daily_earnings_calendar_refresh")],
        }
    )
    monkeypatch.setattr(today, "get_supabase", lambda: db)
    monkeypatch.setattr(
        today,
        "enrich_positions_with_ticker_cache",
        lambda rows, _db: [
            {
                **row,
                "shared_analysis": {
                    "latest_price": row["current_price"],
                    "current_score": 80,
                    "current_grade": "AA",
                    "risk_dimensions": {
                        "financial_health": 80,
                        "news_sentiment": 75,
                        "macro_exposure": 70,
                        "sector_exposure": 65,
                        "volatility": 60,
                    },
                },
            }
            for row in rows
        ],
    )

    envelope = await today.get_today("u1")

    assert set(envelope) >= {"portfolio", "dimensions", "sector_exposure", "calendar", "freshness"}
    assert round(sum(row["portfolio_weight"] for row in envelope["sector_exposure"]), 6) == 1.0
    assert envelope["calendar"][0]["ticker"] == "AAPL"
    assert envelope["freshness"]["job_id"] == "daily_earnings_calendar_refresh"
