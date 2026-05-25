from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

import pytest

from app.jobs import macro_regression
from app.routes import methodology


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table_name: str):
        self.db = db
        self.table_name = table_name
        self.rows = list(db.tables.get(table_name, []))
        self._limit: int | None = None
        self._updates: dict | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.rows = [row for row in self.rows if row.get(field) == value]
        return self

    def gte(self, field, value):
        self.rows = [row for row in self.rows if (row.get(field) or "") >= value]
        return self

    def order(self, field, desc=False, **_kwargs):
        self.rows = sorted(self.rows, key=lambda row: row.get(field) or "", reverse=desc)
        return self

    def limit(self, value):
        self._limit = value
        return self

    def update(self, payload):
        self._updates = payload
        return self

    def execute(self):
        if self._updates is not None:
            for row in self.rows:
                row.update(self._updates)
            self.db.updates.append((self.table_name, self._updates))
            return _Result(self.rows)
        rows = self.rows[: self._limit] if self._limit is not None else self.rows
        return _Result(rows)


class _DB:
    def __init__(self, tables):
        self.tables = tables
        self.updates: list[tuple[str, dict]] = []

    def table(self, name: str):
        return _Query(self, name)


def _price_rows(
    ticker: str,
    returns: list[float],
    *,
    start: datetime,
    base_price: float = 100.0,
) -> list[dict]:
    rows: list[dict] = []
    price = base_price
    current = start
    rows.append({"ticker": ticker, "price": round(price, 6), "recorded_at": current.isoformat()})
    for daily_return in returns:
        current += timedelta(days=1)
        price *= 1.0 + daily_return
        rows.append({"ticker": ticker, "price": round(price, 6), "recorded_at": current.isoformat()})
    return rows


def _synthetic_db(now: datetime) -> _DB:
    start = now - timedelta(days=320)
    observations = 260
    spy = [0.001 * math.sin(index / 9.0) + 0.0008 for index in range(observations)]
    ten_y = [0.0007 * math.cos(index / 13.0) for index in range(observations)]
    dxy = [0.0006 * math.sin(index / 7.0) - 0.0002 for index in range(observations)]
    wti = [0.0009 * math.cos(index / 11.0) + 0.0001 for index in range(observations)]
    vix = [0.0008 * math.sin(index / 5.0) for index in range(observations)]
    asset = [
        (
            1.4 * spy[index]
            - 0.5 * ten_y[index]
            + 0.25 * dxy[index]
            + 0.15 * wti[index]
            - 0.2 * vix[index]
            + 0.0001
        )
        for index in range(observations)
    ]
    return _DB(
        {
            "prices": (
                _price_rows("AAPL", asset, start=start)
                + _price_rows("SPY", spy, start=start)
                + _price_rows("TLT", ten_y, start=start)
                + _price_rows("UUP", dxy, start=start)
                + _price_rows("USO", wti, start=start)
                + _price_rows("VIXY", vix, start=start)
            ),
            "ticker_risk_snapshots": [
                {
                    "id": "snapshot-aapl",
                    "ticker": "AAPL",
                    "analysis_as_of": (now - timedelta(days=31)).isoformat(),
                    "updated_at": (now - timedelta(days=31)).isoformat(),
                    "dimension_inputs": {"macro_exposure": {"legacy": True}},
                    "dimension_last_refreshed": {
                        "macro_exposure": (now - timedelta(days=31)).isoformat()
                    },
                    "grade": "A",
                    "composite_score": 82,
                }
            ],
            "ticker_metadata": [{"ticker": "AAPL", "sector": "Technology", "updated_at": now.isoformat()}],
            "shared_ticker_events": [],
            "sector_medians": [],
            "peer_groups": [],
        }
    )


def test_monthly_macro_regression_refresh_updates_factor_exposures(monkeypatch):
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    db = _synthetic_db(now)
    monkeypatch.setattr(macro_regression, "get_supabase", lambda: db)
    monkeypatch.setattr(macro_regression, "list_active_sp500_tickers", lambda _supabase, limit=None: ["AAPL"])

    result = macro_regression.run(now=now)

    assert result["items_processed"] == 1
    snapshot = db.tables["ticker_risk_snapshots"][0]
    macro_inputs = snapshot["dimension_inputs"]["macro_exposure"]
    factor_exposures = macro_inputs["factor_exposures"]
    assert factor_exposures["beta_spy"] == pytest.approx(1.4, abs=0.02)
    assert factor_exposures["beta_10y"] == pytest.approx(-0.5, abs=0.02)
    assert factor_exposures["beta_dxy"] == pytest.approx(0.25, abs=0.02)
    assert factor_exposures["beta_wti"] == pytest.approx(0.15, abs=0.02)
    assert factor_exposures["beta_vix"] == pytest.approx(-0.2, abs=0.02)
    assert macro_inputs["trading_days_used"] == 252
    assert macro_inputs["r_squared"] > 0.99
    assert snapshot["dimension_last_refreshed"]["macro_exposure"] == now.isoformat()


def test_monthly_macro_regression_refresh_skips_fresh_snapshots(monkeypatch):
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    db = _synthetic_db(now)
    db.tables["ticker_risk_snapshots"][0]["dimension_last_refreshed"]["macro_exposure"] = (
        now - timedelta(days=7)
    ).isoformat()
    monkeypatch.setattr(macro_regression, "get_supabase", lambda: db)
    monkeypatch.setattr(macro_regression, "list_active_sp500_tickers", lambda _supabase, limit=None: ["AAPL"])

    result = macro_regression.run(now=now)

    assert result["items_processed"] == 0
    assert result["items_skipped"] == 1
    assert db.updates == []


@pytest.mark.asyncio
async def test_methodology_includes_factor_exposures(monkeypatch):
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    db = _synthetic_db(now)
    db.tables["ticker_risk_snapshots"][0]["dimension_inputs"]["macro_exposure"] = {
        "factor_exposures": {
            "beta_10y": -0.42,
            "beta_dxy": 0.12,
            "beta_wti": 0.08,
            "beta_vix": -0.21,
            "beta_spy": 1.31,
        },
        "r_squared": 0.88,
        "trading_days_used": 252,
        "computed_at": now.isoformat(),
    }
    monkeypatch.setattr(methodology, "get_supabase", lambda: db)

    result = await methodology.get_ticker_methodology("AAPL", "user-1")

    macro = result["dimensions"]["macro_exposure"]
    assert macro["factor_exposures"]["beta_spy"] == 1.31
    assert macro["factor_exposures"]["beta_10y"] == -0.42
