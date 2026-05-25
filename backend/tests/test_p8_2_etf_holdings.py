from __future__ import annotations

from app.jobs import etf_holdings


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table_name: str):
        self.db = db
        self.table_name = table_name
        self.rows = list(db.tables.get(table_name, []))
        self._upsert_rows = None

    def select(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self._upsert_rows is not None:
            self.db.upsert_calls.append((self.table_name, self._upsert_rows))
        return _Result(self.rows)

    def upsert(self, rows, on_conflict=None):
        self._upsert_rows = rows
        self.db.upsert_conflicts.append(on_conflict)
        return self


class _DB:
    def __init__(self, tables):
        self.tables = tables
        self.upsert_calls: list[tuple[str, list[dict]]] = []
        self.upsert_conflicts: list[str | None] = []

    def table(self, name):
        return _Query(self, name)


def test_monthly_etf_holdings_refresh_uses_live_issuer_rows(monkeypatch):
    db = _DB(
        {
            "positions": [{"ticker": "SPY"}, {"ticker": "QQQ"}],
            "watchlist_items": [{"ticker": "VTI"}],
            "etf_holdings": [],
        }
    )
    monkeypatch.setattr(etf_holdings, "get_supabase", lambda: db)
    monkeypatch.setattr(
        etf_holdings,
        "_fetch_ssga_holdings",
        lambda ticker: [
            {
                "etf_ticker": "SPY",
                "holding_ticker": "AAPL",
                "weight_pct": 7.0,
                "rank": 1,
                "source": "ssga",
                "as_of": "2026-05-21",
            }
        ],
    )
    monkeypatch.setattr(
        etf_holdings,
        "_fetch_invictus_holdings",
        lambda ticker: [
            {
                "etf_ticker": "QQQ",
                "holding_ticker": "NVDA",
                "weight_pct": 8.5,
                "rank": 1,
                "source": "invictus",
                "as_of": "2026-05-25",
            }
        ],
    )
    monkeypatch.setattr(
        etf_holdings,
        "_fetch_vanguard_holdings",
        lambda ticker: [
            {
                "etf_ticker": "VTI",
                "holding_ticker": "MSFT",
                "weight_pct": 5.2,
                "rank": 1,
                "source": "vanguard",
                "as_of": "2026-04-30",
            }
        ],
    )

    result = etf_holdings.run()

    assert result["items_processed"] == 3
    table_name, rows = db.upsert_calls[0]
    assert table_name == "etf_holdings"
    assert {row["source"] for row in rows} == {"ssga", "invictus", "vanguard"}
    assert db.upsert_conflicts == ["etf_ticker,holding_ticker,as_of"]


def test_monthly_etf_holdings_refresh_falls_back_to_static_seed(monkeypatch):
    db = _DB(
        {
            "positions": [{"ticker": "SPY"}],
            "watchlist_items": [],
            "etf_holdings": [],
        }
    )
    monkeypatch.setattr(etf_holdings, "get_supabase", lambda: db)
    monkeypatch.setattr(etf_holdings, "_fetch_ssga_holdings", lambda ticker: [])

    result = etf_holdings.run()

    assert result["items_processed"] == len(etf_holdings.ETF_STATIC_SEEDS["SPY"])
    _, rows = db.upsert_calls[0]
    assert rows[0]["source"] == "static_seed"
    assert rows[0]["etf_ticker"] == "SPY"
