from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import polygon_options, ticker_cache_service


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table_name: str):
        self.db = db
        self.table_name = table_name
        self.rows = list(db.tables.get(table_name, []))
        self._limit: int | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.rows = [row for row in self.rows if row.get(field) == value]
        return self

    def order(self, field, desc=False, **_kwargs):
        self.rows = sorted(self.rows, key=lambda row: row.get(field) or "", reverse=desc)
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        rows = self.rows[: self._limit] if self._limit is not None else self.rows
        return _Result(rows)


class _DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Query(self, name)


def _bars(start: datetime, closes: list[float]) -> list[dict]:
    bars = []
    current = start
    for close in closes:
        bars.append({"t": int(current.timestamp() * 1000), "c": close})
        current += timedelta(days=1)
    return bars


def test_fetch_near_term_implied_vol_30d_picks_near_money_contract(monkeypatch):
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)

    class _Response:
        status_code = 200

        def json(self):
            return {
                "results": [
                    {
                        "implied_volatility": 0.41,
                        "details": {
                            "expiration_date": "2026-06-24",
                            "strike_price": 150,
                            "contract_type": "call",
                        },
                        "underlying_asset": {"price": 149.5},
                    },
                    {
                        "implied_volatility": 0.55,
                        "details": {
                            "expiration_date": "2026-06-03",
                            "strike_price": 180,
                            "contract_type": "call",
                        },
                        "underlying_asset": {"price": 149.5},
                    },
                ]
            }

    monkeypatch.setattr(polygon_options, "polygon_get", lambda *_args, **_kwargs: _Response())
    monkeypatch.setattr(
        polygon_options,
        "get_settings",
        lambda: type("Settings", (), {"polygon_api_key": "test-key"})(),
    )

    result = polygon_options.fetch_near_term_implied_vol_30d("AAPL", now=now)

    assert result["implied_vol_30d"] == 0.41
    assert result["strike_price"] == 150.0


def test_build_volatility_inputs_uses_polygon_iv_rank_when_available(monkeypatch):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    closes = [100 + index * 0.4 for index in range(320)]
    spy_closes = [90 + index * 0.25 for index in range(320)]
    db = _DB(
        {
            "ticker_risk_snapshots": [
                {
                    "ticker": "AAPL",
                    "snapshot_date": f"2026-01-{day:02d}",
                    "dimension_inputs": {"volatility": {"implied_vol_30d": 0.20 + day * 0.001}},
                }
                for day in range(1, 40)
            ]
        }
    )
    monkeypatch.setattr(
        ticker_cache_service,
        "fetch_near_term_implied_vol_30d",
        lambda ticker: {"implied_vol_30d": 0.31},
    )

    result = ticker_cache_service._build_volatility_inputs(
        db,
        "AAPL",
        _bars(start, closes),
        _bars(start, spy_closes),
        as_of_date="2026-05-25",
    )

    assert result["implied_vol_30d"] == 0.31
    assert 0.0 <= result["iv_rank"] <= 100.0
    assert result["iv_source"] == "polygon"


def test_build_volatility_inputs_falls_back_when_options_snapshot_missing(monkeypatch):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    closes = [100 + ((index % 9) - 4) * 0.8 + index * 0.15 for index in range(320)]
    spy_closes = [95 + ((index % 7) - 3) * 0.5 + index * 0.1 for index in range(320)]
    db = _DB({"ticker_risk_snapshots": []})
    monkeypatch.setattr(ticker_cache_service, "fetch_near_term_implied_vol_30d", lambda ticker: None)

    result = ticker_cache_service._build_volatility_inputs(
        db,
        "AAPL",
        _bars(start, closes),
        _bars(start, spy_closes),
        as_of_date="2026-05-25",
    )

    assert result["implied_vol_30d"] is None
    assert 0.0 <= result["iv_rank"] <= 100.0
    assert result["iv_source"] == "estimated"
