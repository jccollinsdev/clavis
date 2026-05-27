from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.jobs.peer_groups import compute_peer_groups
from app.jobs.sector_medians import compute_sector_medians
from app.pipeline.structural_scorer import estimate_iv_rank_from_realized_vol
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

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        self.rows = [row for row in self.rows if row.get(field) == value]
        return self

    def in_(self, field, values):
        allowed = set(values)
        self.rows = [row for row in self.rows if row.get(field) in allowed]
        return self

    def order(self, field, desc=False):
        self.rows = sorted(self.rows, key=lambda row: row.get(field) or "", reverse=desc)
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def execute(self):
        rows = self.rows[: self._limit] if self._limit is not None else self.rows
        return _Result(rows)


class _DB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Query(self, name)


def test_peer_groups_prevent_self_links():
    peers = compute_peer_groups(
        [
            {"ticker": "AAPL", "sector": "Technology", "market_cap": 3_000_000_000_000, "market_cap_bucket": "very_high"},
            {"ticker": "MSFT", "sector": "Technology", "market_cap": 2_800_000_000_000, "market_cap_bucket": "very_high"},
            {"ticker": "JPM", "sector": "Financials", "market_cap": 600_000_000_000, "market_cap_bucket": "very_high"},
        ]
    )

    assert peers
    assert all(row["ticker"] != row["peer_ticker"] for row in peers)
    assert any(row["ticker"] == "AAPL" and row["peer_ticker"] == "MSFT" for row in peers)


def test_sector_medians_emit_per_metric_coverage():
    medians = compute_sector_medians(
        [
            {"ticker": "A", "sector": "Technology", "debt_to_equity": 0.2, "fcf_margin": 0.3},
            {"ticker": "B", "sector": "Technology", "debt_to_equity": 0.6, "fcf_margin": 0.5},
            {"ticker": "C", "sector": "Financials", "debt_to_equity": 1.0},
        ]
    )

    tech_debt = next(row for row in medians if row["sector"] == "Technology" and row["metric"] == "debt_to_equity")
    tech_fcf = next(row for row in medians if row["sector"] == "Technology" and row["metric"] == "fcf_margin")
    assert tech_debt["median"] == 0.4
    assert tech_debt["n_tickers"] == 2
    assert tech_fcf["n_tickers"] == 2


def test_realized_vol_iv_rank_fallback_is_bounded():
    assert estimate_iv_rank_from_realized_vol(0.30, 0.20) == 100.0
    assert estimate_iv_rank_from_realized_vol(0.10, 0.20) == 0.0
    assert estimate_iv_rank_from_realized_vol(None, 0.20) is None


@pytest.mark.asyncio
async def test_methodology_response_includes_audit_depth(monkeypatch):
    now = datetime.now(timezone.utc)
    db = _DB(
        {
            "ticker_metadata": [
                {
                    "ticker": "AAPL",
                    "sector": "Technology",
                    "updated_at": now.isoformat(),
                }
            ],
            "ticker_risk_snapshots": [
                {
                    "ticker": "AAPL",
                    "grade": "AA",
                    "composite_score": 84,
                    "financial_health": 80,
                    "news_sentiment_dim": 70,
                    "macro_exposure_dim": 65,
                    "sector_exposure": 75,
                    "volatility": 60,
                    "analysis_as_of": now.isoformat(),
                    "dimension_inputs": {
                        "financial_health": {"debt_to_equity": 0.2},
                        "volatility": {
                            "realized_vol_30d": 0.24,
                            "realized_vol_90d": 0.20,
                        },
                    },
                }
            ],
            "shared_ticker_events": [
                {
                    "ticker": "AAPL",
                    "title": "AAPL event",
                    "published_at": (now - timedelta(days=1)).isoformat(),
                    "sentiment_score": 65,
                    "source": "Reuters",
                }
            ],
            "sector_medians": [
                {
                    "sector": "Technology",
                    "metric": "debt_to_equity",
                    "median": 0.4,
                    "p25": 0.2,
                    "p75": 0.6,
                    "n_tickers": 2,
                    "as_of": now.date().isoformat(),
                }
            ],
            "peer_groups": [
                {
                    "ticker": "AAPL",
                    "peer_ticker": "MSFT",
                    "similarity": 0.9,
                    "computed_at": now.isoformat(),
                }
            ],
        }
    )
    monkeypatch.setattr(methodology, "get_supabase", lambda: db)

    result = await methodology.get_ticker_methodology("aapl", "u1")

    fin = result["dimensions"]["financial_health"]
    news = result["dimensions"]["news_sentiment"]
    vol = result["dimensions"]["volatility"]
    assert fin["peer_comparisons"][0]["ticker"] == "MSFT"
    assert fin["sector_median_comparison"]["debt_to_equity"]["median"] == 0.4
    assert sum(row["count"] for row in news["article_histogram_14d"]) == 1
    assert news["sentiment_distribution"][0]["bucket"] == "positive"
    assert vol["iv_rank"] is not None
    assert vol["iv_source"] == "estimated"


@pytest.mark.asyncio
async def test_methodology_prefers_complete_snapshot_over_newer_partial(monkeypatch):
    now = datetime.now(timezone.utc)
    db = _DB(
        {
            "ticker_metadata": [{"ticker": "CFG", "sector": "Financials", "updated_at": now.isoformat()}],
            "ticker_risk_snapshots": [
                {
                    "id": "partial",
                    "ticker": "CFG",
                    "snapshot_type": "backfill",
                    "grade": "BBB",
                    "composite_score": None,
                    "financial_health": 54,
                    "news_sentiment_dim": None,
                    "macro_exposure_dim": None,
                    "sector_exposure": 65,
                    "volatility": 67,
                    "analysis_as_of": (now + timedelta(seconds=5)).isoformat(),
                    "methodology_version": "sp500-ai-backfill-v2",
                    "factor_breakdown": {
                        "ai_dimensions": {
                            "financial_health": 54,
                            "news_sentiment": 55,
                            "macro_exposure": 100,
                            "sector_exposure": 65,
                            "volatility": 67,
                        }
                    },
                },
                {
                    "id": "complete",
                    "ticker": "CFG",
                    "snapshot_type": "daily",
                    "grade": "B",
                    "composite_score": 48.2,
                    "financial_health": 45,
                    "news_sentiment_dim": 40,
                    "macro_exposure_dim": 35,
                    "sector_exposure": 50,
                    "volatility": 45,
                    "analysis_as_of": now.isoformat(),
                    "methodology_version": "v2",
                },
            ],
            "shared_ticker_events": [],
            "sector_medians": [],
            "peer_groups": [],
        }
    )
    monkeypatch.setattr(methodology, "get_supabase", lambda: db)

    result = await methodology.get_ticker_methodology("cfg", "u1")

    assert result["composite"]["score"] == 48.2
    assert result["dimensions"]["news_sentiment"]["score"] == 40
    assert result["dimensions"]["macro_exposure"]["score"] == 35


@pytest.mark.asyncio
async def test_methodology_surfaces_limited_reason_for_missing_dimension(monkeypatch):
    now = datetime.now(timezone.utc)
    db = _DB(
        {
            "ticker_metadata": [{"ticker": "HIMS", "sector": "Health Care", "updated_at": now.isoformat()}],
            "ticker_risk_snapshots": [
                {
                    "id": "limited",
                    "ticker": "HIMS",
                    "snapshot_type": "backfill",
                    "grade": "BB",
                    "composite_score": 51.0,
                    "financial_health": 58,
                    "news_sentiment_dim": None,
                    "macro_exposure_dim": 41,
                    "sector_exposure": 65,
                    "volatility": 40,
                    "analysis_as_of": now.isoformat(),
                    "methodology_version": "v2",
                    "dimension_inputs": {
                        "news_sentiment": {
                            "article_count_7d": 0,
                            "weighted_score": None,
                            "limited_data": True,
                            "limited_reason": "Only 0 shared ticker event(s) were available in the last 7 days; at least 3 are required for a scored news sentiment dimension.",
                        },
                        "macro_exposure": {
                            "limited_data": True,
                            "limited_reason": "Macro regression only had 0 usable trading day(s) of factor history.",
                        },
                    },
                }
            ],
            "shared_ticker_events": [],
            "sector_medians": [],
            "peer_groups": [],
        }
    )
    monkeypatch.setattr(methodology, "get_supabase", lambda: db)

    result = await methodology.get_ticker_methodology("hims", "u1")

    news = result["dimensions"]["news_sentiment"]
    macro = result["dimensions"]["macro_exposure"]
    assert news["score"] is None
    assert news["limited_data"] is True
    assert "at least 3 are required" in news["limited_reason"]
    assert macro["limited_data"] is True
    assert "usable trading day" in macro["limited_reason"]
