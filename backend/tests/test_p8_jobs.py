"""P8 — operational polish: event_fundamentals_pull, monthly_etf_holdings_refresh,
weekly_universe_audit.

Codex authored the P8 job modules but ran out of credits before wiring them into
the runner registry, the cron file, and tests. These tests verify the wiring +
exercise the pure-function helpers each job exposes."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import patch


# Match the fake-supabase pattern used in test_jobs_runner.py — keeps the test
# isolated from the real supabase client at import time.
_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

from app.jobs import run as job_runner
from app.jobs import etf_holdings, event_fundamentals, universe_audit


# ---------------------------------------------------------------------------
# Runner registration
# ---------------------------------------------------------------------------


def test_p8_jobs_registered_with_expected_tiers():
    registry = job_runner.JOB_REGISTRY
    assert "event_fundamentals_pull" in registry
    assert "monthly_etf_holdings_refresh" in registry
    assert "weekly_universe_audit" in registry
    assert registry["event_fundamentals_pull"].tier == "daily"
    assert registry["monthly_etf_holdings_refresh"].tier == "monthly"
    assert registry["weekly_universe_audit"].tier == "weekly"


def test_p8_jobs_dry_run_via_cli():
    for job_id in (
        "event_fundamentals_pull",
        "monthly_etf_holdings_refresh",
        "weekly_universe_audit",
    ):
        assert job_runner.main([job_id, "--dry-run"]) == 0


# ---------------------------------------------------------------------------
# universe_audit.diff_universe — pure helper, easy to assert on
# ---------------------------------------------------------------------------


def test_diff_universe_finds_adds_and_removes():
    existing = [
        {"ticker": "AAPL", "is_active": True},
        {"ticker": "MSFT", "is_active": True},
        {"ticker": "OLD", "is_active": True},
    ]
    authoritative = [
        {"ticker": "AAPL"},
        {"ticker": "MSFT"},
        {"ticker": "NEW"},
    ]
    diff = universe_audit.diff_universe(existing, authoritative)
    assert diff["adds"] == ["NEW"]
    assert diff["removes"] == ["OLD"]


def test_diff_universe_ignores_inactive_existing_rows():
    existing = [
        {"ticker": "AAPL", "is_active": True},
        {"ticker": "RETIRED", "is_active": False},
    ]
    authoritative = [{"ticker": "AAPL"}]
    diff = universe_audit.diff_universe(existing, authoritative)
    # RETIRED is already inactive — must not show up under removes
    assert diff["removes"] == []
    assert diff["adds"] == []


def test_diff_universe_normalises_case():
    existing = [{"ticker": "aapl", "is_active": True}]
    authoritative = [{"ticker": "AAPL"}]
    diff = universe_audit.diff_universe(existing, authoritative)
    assert diff["adds"] == []
    assert diff["removes"] == []


# ---------------------------------------------------------------------------
# etf_holdings.rows_for_etf — pure helper
# ---------------------------------------------------------------------------


def test_rows_for_etf_returns_ranked_top_holdings():
    rows = etf_holdings.rows_for_etf("SPY", as_of="2026-05-25")
    assert rows, "SPY seed must produce rows"
    assert rows[0]["etf_ticker"] == "SPY"
    assert rows[0]["rank"] == 1
    assert rows[0]["holding_ticker"] == "AAPL"
    assert all(row["as_of"] == "2026-05-25" for row in rows)
    assert all(row["source"] == "static_seed" for row in rows)
    # ranks are monotonic + dense
    assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))


def test_rows_for_etf_unknown_ticker_yields_empty():
    assert etf_holdings.rows_for_etf("ZZZZ", as_of="2026-05-25") == []


def test_rows_for_etf_normalises_ticker_case():
    rows = etf_holdings.rows_for_etf("spy", as_of="2026-05-25")
    assert rows and rows[0]["etf_ticker"] == "SPY"


# ---------------------------------------------------------------------------
# event_fundamentals — exercise the supabase-touching helper with a stub
# ---------------------------------------------------------------------------


class _FakeQuery:
    def __init__(self, table_name, rows):
        self.table_name = table_name
        self._rows = rows
        self._filters: dict[str, object] = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def execute(self):
        matched = [
            row
            for row in self._rows
            if all(row.get(k) == v for k, v in self._filters.items())
        ]
        return SimpleNamespace(data=matched)


class _FakeSupabase:
    def __init__(self, earnings_rows):
        self._earnings_rows = earnings_rows

    def table(self, name):
        if name == "earnings_calendar":
            return _FakeQuery(name, self._earnings_rows)
        return _FakeQuery(name, [])


def test_event_fundamentals_dry_run_lists_calendar_tickers():
    fake = _FakeSupabase(
        earnings_rows=[
            {"ticker": "nvda", "report_date": "2026-05-26"},
            {"ticker": "AAPL", "report_date": "2026-05-26"},
            {"ticker": "MSFT", "report_date": "2026-05-24"},
            {"ticker": "META", "report_date": "2026-05-30"},  # outside T-1/T+1 window
        ]
    )
    with patch.object(event_fundamentals, "get_supabase", return_value=fake), patch(
        "app.jobs.event_fundamentals.date"
    ) as fake_date:
        import datetime as _dt

        fake_date.today.return_value = _dt.date(2026, 5, 25)

        result = event_fundamentals.run(dry_run=True)

    assert result["status"] == "completed"
    assert result["items_processed"] == 0
    tickers = result["metadata"]["tickers"]
    # union of T-1 (2026-05-24) + T+1 (2026-05-26), case-normalised, sorted
    assert tickers == ["AAPL", "MSFT", "NVDA"]
    assert "META" not in tickers
