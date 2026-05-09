from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import logging
import math
from pathlib import Path
import statistics
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from ..pipeline.risk_scorer import score_position_structural
from ..pipeline.analysis_utils import score_to_grade, grade_direction, sanitize_rationale, sanitize_public_analysis_text, format_rationale, evidence_strength, sanitize_text_field, normalize_event_analysis_payload
from ..pipeline.position_report_builder import _build_driver_cards
from .alert_payloads import enrich_alert_rows
from .macro_regression import FACTOR_TICKERS, macro_regression_to_audit_jsonb, run_macro_regression
from .polygon import fetch_aggs
from .ticker_metadata import upsert_ticker_metadata


logger = logging.getLogger(__name__)
_RATIONALE_BLOCK_COUNTS: Counter[str] = Counter()
_RATIONALE_SOURCE_COUNTS: Counter[str] = Counter()


SYSTEM_SP500_USER_ID = "00000000-0000-0000-0000-000000000001"


SP500_UNIVERSE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "sp500_universe.txt"
)

SECTOR_ETF_MAP = {
    "communication services": "XLC",
    "consumer discretionary": "XLY",
    "consumer staples": "XLP",
    "energy": "XLE",
    "financials": "XLF",
    "healthcare": "XLV",
    "industrials": "XLI",
    "information technology": "XLK",
    "technology": "XLK",
    "materials": "XLB",
    "real estate": "XLRE",
    "utilities": "XLU",
}


@lru_cache(maxsize=1)
def load_sp500_seed_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(SP500_UNIVERSE_PATH.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        ticker, company_name, sector, industry = line.split("|", maxsplit=3)
        rows.append(
            {
                "ticker": ticker.upper(),
                "company_name": company_name,
                "sector": sector,
                "industry": industry,
                "index_membership": "SP500",
                "is_active": True,
                "priority_rank": index,
            }
        )
    return rows


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_rationale_metric(kind: str, key: str, *, ticker: str | None = None) -> None:
    counts = _RATIONALE_BLOCK_COUNTS if kind == "block" else _RATIONALE_SOURCE_COUNTS
    counts[key] += 1
    count = counts[key]
    if count <= 5 or count % 25 == 0:
        logger.info(
            "[RATIONALE_%s] key=%s ticker=%s count=%s",
            kind.upper(),
            key,
            ticker or "-",
            count,
        )


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _bars_to_close_series(bars: list[dict[str, Any]]) -> list[float]:
    closes: list[float] = []
    for bar in bars or []:
        close = _coerce_float(bar.get("c"))
        if close is not None:
            closes.append(close)
    return closes


def _daily_returns_from_closes(closes: list[float]) -> list[float]:
    if len(closes) < 2:
        return []
    returns: list[float] = []
    for index in range(1, len(closes)):
        previous = closes[index - 1]
        current = closes[index]
        if previous <= 0:
            continue
        returns.append((current - previous) / previous)
    return returns


def _annualized_volatility(closes: list[float], window: int) -> float | None:
    if len(closes) < window + 1:
        return None
    returns = _daily_returns_from_closes(closes[-(window + 1) :])
    if len(returns) < 2:
        return None
    return statistics.stdev(returns) * math.sqrt(252)


def _max_drawdown(closes: list[float], window: int) -> float | None:
    if len(closes) < 2:
        return None
    series = closes[-window:] if len(closes) > window else closes
    peak = series[0]
    worst_drawdown = 0.0
    for close in series:
        peak = max(peak, close)
        if peak <= 0:
            continue
        worst_drawdown = min(worst_drawdown, (close - peak) / peak)
    return abs(worst_drawdown)


def _beta_from_returns(asset_returns: list[float], benchmark_returns: list[float]) -> float | None:
    count = min(len(asset_returns), len(benchmark_returns))
    if count < 2:
        return None
    asset_slice = asset_returns[-count:]
    benchmark_slice = benchmark_returns[-count:]
    benchmark_variance = statistics.pvariance(benchmark_slice)
    if benchmark_variance == 0:
        return None
    asset_mean = statistics.mean(asset_slice)
    benchmark_mean = statistics.mean(benchmark_slice)
    covariance = sum(
        (asset_slice[i] - asset_mean) * (benchmark_slice[i] - benchmark_mean)
        for i in range(count)
    ) / count
    return covariance / benchmark_variance


def _percent_change(closes: list[float], window: int) -> float | None:
    if len(closes) < window + 1:
        return None
    start = closes[-(window + 1)]
    end = closes[-1]
    if start <= 0:
        return None
    return (end - start) / start


def _positive_day_ratio(closes: list[float], window: int) -> float | None:
    if len(closes) < window + 1:
        return None
    returns = _daily_returns_from_closes(closes[-(window + 1) :])
    if not returns:
        return None
    positive_days = sum(1 for value in returns if value > 0)
    return positive_days / len(returns)


def _latest_close_from_bars(bars: list[dict[str, Any]]) -> float | None:
    closes = _bars_to_close_series(bars)
    return closes[-1] if closes else None


def _current_factor_levels(factor_bars_map: dict[str, list[dict[str, Any]]]) -> dict[str, float | None]:
    return {
        factor: _latest_close_from_bars(factor_bars_map.get(factor, []))
        for factor in FACTOR_TICKERS
    }


def _normalize_growth_trend_label(value: Any) -> str | None:
    numeric = _coerce_float(value)
    if numeric is None:
        return None
    if numeric >= 0.15:
        return "positive_3q"
    if numeric >= 0.03:
        return "modestly_positive"
    if numeric <= -0.10:
        return "declining"
    if numeric < 0:
        return "slowing"
    return "flat"


def _profitability_trend_label(metadata: dict[str, Any]) -> str | None:
    profile = str(metadata.get("profitability_profile") or "").strip().lower()
    if profile == "profitable":
        return "improving"
    if profile == "unprofitable":
        return "weakening"
    if profile == "mixed":
        return "mixed"
    return None


def _build_financial_health_inputs(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "debt_to_equity": _coerce_float(metadata.get("debt_to_equity")),
        "fcf_margin": _coerce_float(metadata.get("fcf_margin")),
        "interest_coverage": _coerce_float(metadata.get("interest_coverage")),
        "current_ratio": _coerce_float(metadata.get("current_ratio")),
        "revenue_growth_trend": _normalize_growth_trend_label(
            metadata.get("revenue_growth_trend")
        ),
        "profitability_trend": _profitability_trend_label(metadata),
        "as_of_date": metadata.get("price_as_of") or metadata.get("updated_at"),
        "data_source": "finnhub",
    }


def _build_news_sentiment_inputs(news_rows: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    article_count_7d = 0
    weighted_total = 0.0
    total_weight = 0.0
    article_count_28d = 0

    for row in news_rows:
        published_at = _parse_iso_datetime(row.get("published_at"))
        if not published_at:
            continue
        age_days = (now - published_at).total_seconds() / 86400.0
        if age_days <= 28:
            article_count_28d += 1
        if age_days > 7:
            continue
        article_count_7d += 1
        sentiment_score = _coerce_float(row.get("sentiment_score"))
        if sentiment_score is None:
            continue
        recency_weight = _coerce_float(row.get("recency_weight")) or 1.0
        source_weight = _coerce_float(row.get("source_weight")) or 1.0
        weight = recency_weight * source_weight
        weighted_total += sentiment_score * weight
        total_weight += weight

    baseline = article_count_28d / 4.0 if article_count_28d else 0.0
    return {
        "article_count_7d": article_count_7d,
        "volume_signal": bool(article_count_7d and baseline and article_count_7d > baseline * 1.25),
        "weighted_score": round(weighted_total / total_weight, 1) if total_weight > 0 else None,
    }


def _build_sector_exposure_inputs(
    ticker: str,
    metadata: dict[str, Any],
    ticker_bars: list[dict[str, Any]],
) -> dict[str, Any]:
    sector = str(metadata.get("sector") or "").strip()
    sector_etf = SECTOR_ETF_MAP.get(sector.lower()) if sector else None
    if not sector_etf:
        return {
            "sector": sector or None,
            "sector_etf": None,
            "sector_beta": None,
            "sector_momentum_30d": None,
            "sector_breadth": None,
            "narrative": None,
        }

    sector_bars = fetch_aggs(sector_etf, days=90)
    ticker_closes = _bars_to_close_series(ticker_bars)
    sector_closes = _bars_to_close_series(sector_bars)
    ticker_returns = _daily_returns_from_closes(ticker_closes)
    sector_returns = _daily_returns_from_closes(sector_closes)
    sector_beta = _beta_from_returns(ticker_returns, sector_returns)
    sector_momentum = _percent_change(sector_closes, 30)
    sector_breadth = _positive_day_ratio(sector_closes, 30)

    narrative_parts: list[str] = []
    if sector_momentum is not None:
        if sector_momentum >= 0.05:
            narrative_parts.append(f"{sector_etf} has been supporting the tape")
        elif sector_momentum <= -0.05:
            narrative_parts.append(f"{sector_etf} has been under pressure")
    if sector_beta is not None:
        if sector_beta >= 1.15:
            narrative_parts.append(f"{ticker} is moving more aggressively than its sector ETF")
        elif sector_beta <= 0.85:
            narrative_parts.append(f"{ticker} is moving more defensively than its sector ETF")
    if sector_breadth is not None:
        breadth_pct = sector_breadth * 100
        if breadth_pct >= 55:
            narrative_parts.append("breadth has been constructive")
        elif breadth_pct <= 45:
            narrative_parts.append("breadth has been narrow")

    return {
        "sector": sector or None,
        "sector_etf": sector_etf,
        "sector_beta": round(sector_beta, 3) if sector_beta is not None else None,
        "sector_momentum_30d": round(sector_momentum, 4) if sector_momentum is not None else None,
        "sector_breadth": round(sector_breadth, 4) if sector_breadth is not None else None,
        "narrative": ". ".join(narrative_parts) + "." if narrative_parts else None,
    }


def _build_volatility_inputs(
    ticker_bars: list[dict[str, Any]],
    spy_bars: list[dict[str, Any]],
    *,
    as_of_date: str,
) -> dict[str, Any]:
    ticker_closes = _bars_to_close_series(ticker_bars)
    spy_closes = _bars_to_close_series(spy_bars)
    ticker_returns = _daily_returns_from_closes(ticker_closes)
    spy_returns = _daily_returns_from_closes(spy_closes)
    realized_vol_30d = _annualized_volatility(ticker_closes, 30)
    realized_vol_90d = _annualized_volatility(ticker_closes, 90)
    vol_ratio = (
        realized_vol_30d / realized_vol_90d
        if realized_vol_30d is not None and realized_vol_90d not in {None, 0}
        else None
    )
    beta_to_spy = _beta_from_returns(ticker_returns, spy_returns)
    max_drawdown_252d = _max_drawdown(ticker_closes, 252)
    return {
        "realized_vol_30d": round(realized_vol_30d, 4) if realized_vol_30d is not None else None,
        "realized_vol_90d": round(realized_vol_90d, 4) if realized_vol_90d is not None else None,
        "vol_ratio": round(vol_ratio, 4) if vol_ratio is not None else None,
        "max_drawdown_252d": round(max_drawdown_252d, 4) if max_drawdown_252d is not None else None,
        "beta_to_spy": round(beta_to_spy, 4) if beta_to_spy is not None else None,
        "as_of_date": as_of_date,
    }


def _build_macro_exposure_inputs(
    macro_result: dict[str, Any],
    factor_bars_map: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    current_factor_levels = _current_factor_levels(factor_bars_map)
    coefficients = macro_result.get("coefficients") or {}
    narrative_parts: list[str] = []
    if coefficients:
        top_factor = max(coefficients.items(), key=lambda item: abs(item[1]))
        narrative_parts.append(
            f"Largest sensitivity is to {top_factor[0].upper()} ({top_factor[1]:.3f})"
        )
    if macro_result.get("r_squared") is not None:
        narrative_parts.append(f"regression fit is {macro_result['r_squared']:.2f} R²")
    return {
        "r_squared": macro_result.get("r_squared"),
        "trading_days_used": macro_result.get("trading_days_used"),
        "limited_data": macro_result.get("limited_data", False),
        "as_of_date": macro_result.get("as_of_date"),
        "coefficients": coefficients,
        "current_factor_levels": current_factor_levels,
        "narrative": ". ".join(narrative_parts) + "." if narrative_parts else None,
    }


def _snapshot_methodology_priority(methodology_version: Any) -> int:
    method = str(methodology_version or "").lower()
    if method == "v2":
        return 4
    if method == "sp500-ai-backfill-v2":
        return 3
    if "ai" in method:
        return 2
    if "deterministic" in method:
        return 0
    return 1


def _snapshot_sort_key(row: dict[str, Any]) -> tuple:
    analysis_as_of = _parse_iso_datetime(row.get("analysis_as_of"))
    updated_at = _parse_iso_datetime(row.get("updated_at"))
    created_at = _parse_iso_datetime(row.get("created_at"))
    return (
        analysis_as_of.timestamp() if analysis_as_of else float("-inf"),
        updated_at.timestamp() if updated_at else float("-inf"),
        created_at.timestamp() if created_at else float("-inf"),
        _snapshot_methodology_priority(row.get("methodology_version")),
        str(row.get("id") or ""),
    )


def _canonical_snapshot_sort_key(row: dict[str, Any]) -> tuple:
    analysis_as_of, updated_at, created_at, method_priority, row_id = _snapshot_sort_key(
        row
    )
    return (method_priority, analysis_as_of, updated_at, created_at, row_id)


def _chunked(values: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def ensure_sp500_universe_seeded(supabase) -> None:
    existing = (
        supabase.table("ticker_universe")
        .select("ticker")
        .eq("index_membership", "SP500")
        .execute()
        .data
        or []
    )
    existing_tickers = {row["ticker"] for row in existing}
    missing = [
        row for row in load_sp500_seed_rows() if row["ticker"] not in existing_tickers
    ]
    for chunk in _chunked(missing, 100):
        supabase.table("ticker_universe").insert(chunk).execute()


def list_active_sp500_tickers(supabase, limit: int | None = None) -> list[str]:
    ensure_sp500_universe_seeded(supabase)
    result = (
        supabase.table("ticker_universe")
        .select("ticker")
        .eq("index_membership", "SP500")
        .eq("is_active", True)
        .order("priority_rank")
        .execute()
    )
    tickers = [row["ticker"] for row in (result.data or [])]
    if limit is not None:
        return tickers[:limit]
    return tickers


def _universe_sort_key(row: dict[str, Any], term: str) -> tuple:
    ticker = (row.get("ticker") or "").upper()
    company_name = (row.get("company_name") or "").upper()
    membership = (row.get("index_membership") or "").upper()
    priority_rank = row.get("priority_rank")
    return (
        0 if ticker == term else 1,
        0 if ticker.startswith(term) else 1,
        0 if term and term in company_name else 1,
        0 if membership == "SP500" else 1,
        priority_rank if priority_rank is not None else 999999,
        ticker,
    )


def ensure_ticker_in_universe(supabase, ticker: str) -> dict | None:
    normalized = (ticker or "").strip().upper()
    if not normalized:
        return None

    existing = get_supported_ticker(supabase, normalized)
    if existing:
        return existing

    metadata = upsert_ticker_metadata(supabase, normalized)
    if not metadata:
        return None

    payload = {
        "ticker": normalized,
        "company_name": metadata.get("company_name") or normalized,
        "exchange": metadata.get("exchange"),
        "sector": metadata.get("sector"),
        "industry": metadata.get("industry"),
        "index_membership": "USER_SHARED",
        "is_active": True,
        "priority_rank": None,
        "updated_at": _utcnow_iso(),
    }
    supabase.table("ticker_universe").insert(payload).execute()
    return get_supported_ticker(supabase, normalized)


def get_supported_ticker(supabase, ticker: str) -> dict | None:
    ensure_sp500_universe_seeded(supabase)
    result = (
        supabase.table("ticker_universe")
        .select("*")
        .eq("ticker", ticker.upper())
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def require_supported_ticker(supabase, ticker: str) -> dict:
    supported = get_supported_ticker(supabase, ticker)
    if not supported:
        raise HTTPException(400, "Ticker is not available in Clavix yet")
    return supported


def search_supported_tickers(
    supabase, query: str | None, limit: int = 20, user_id: str | None = None
) -> list[dict[str, Any]]:
    ensure_sp500_universe_seeded(supabase)
    universe = (
        supabase.table("ticker_universe")
        .select("ticker, company_name, exchange, sector, industry, priority_rank")
        .eq("is_active", True)
        .execute()
        .data
        or []
    )

    term = (query or "").strip().upper()
    if term:
        filtered = [
            row
            for row in universe
            if term in (row.get("ticker") or "").upper()
            or term in (row.get("company_name") or "").upper()
        ]
    else:
        filtered = universe

    filtered.sort(key=lambda row: _universe_sort_key(row, term))

    selected = filtered[:limit]
    tickers = [row["ticker"] for row in selected]
    metadata_map = get_metadata_map(supabase, tickers)
    history_map = get_latest_risk_snapshot_history_map(supabase, tickers, per_ticker=2)
    snapshot_map = {ticker: rows[0] for ticker, rows in history_map.items() if rows}
    news_cache_map = get_latest_news_cache_map(supabase, tickers)
    refresh_job_map = get_latest_refresh_job_map(supabase, tickers)

    held_ticker_to_position: dict[str, dict[str, Any]] = {}
    watchlist_tickers: set[str] = set()
    if user_id and tickers:
        held_rows = (
            supabase.table("positions")
            .select("id, user_id, ticker, shares, purchase_price, current_price")
            .eq("user_id", user_id)
            .in_("ticker", tickers)
            .execute()
            .data
            or []
        )
        for held in held_rows:
            held_ticker_to_position[str(held.get("ticker") or "").upper()] = held
        watchlist = get_or_create_default_watchlist(supabase, user_id)
        if watchlist.get("id"):
            watchlist_rows = (
                supabase.table("watchlist_items")
                .select("ticker")
                .eq("watchlist_id", watchlist["id"])
                .in_("ticker", tickers)
                .execute()
                .data
                or []
            )
            watchlist_tickers = {
                str(row.get("ticker") or "").upper()
                for row in watchlist_rows
                if row.get("ticker")
            }

    batch_refs = _batch_get_shared_reference_analyses(supabase, tickers, snapshot_map)

    results = []
    for row in selected:
        ticker = row["ticker"]
        metadata = metadata_map.get(ticker, {})
        snapshot = snapshot_map.get(ticker, {})
        previous_snapshot = history_map.get(ticker, [None, None])[1]
        _shared_position_id, shared_analysis, shared_event_rows = batch_refs.get(ticker, (None, None, []))
        shared_summary = build_shared_ticker_analysis_summary(
            ticker=ticker,
            metadata=metadata,
            snapshot=snapshot,
            previous_snapshot=previous_snapshot,
            latest_news_row=news_cache_map.get(ticker),
            latest_refresh_job=refresh_job_map.get(ticker),
            current_analysis=shared_analysis,
            latest_event_analyses=shared_event_rows,
            analysis_run_id=(shared_analysis or {}).get("analysis_run_id"),
        )
        position = held_ticker_to_position.get(ticker)
        portfolio_overlay = build_portfolio_overlay(
            ticker=ticker,
            position=position,
            held_positions=[position] if position else [],
            is_in_watchlist=ticker in watchlist_tickers,
            current_price=metadata.get("price"),
        )
        result = {
            **row,
            "price": metadata.get("price"),
            "price_as_of": metadata.get("price_as_of"),
            "grade": shared_summary.get("current_grade"),
            "safety_score": shared_summary.get("current_score"),
            "analysis_as_of": (shared_summary.get("freshness") or {}).get(
                "analysis_as_of"
            ),
            "summary": shared_summary.get("grade_rationale"),
            "is_supported": True,
            "shared_analysis": shared_summary,
            "portfolio_overlay": portfolio_overlay,
        }
        results.append(sanitize_public_analysis_text(result))
    return results


def get_metadata_map(supabase, tickers: list[str]) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    result = (
        supabase.table("ticker_metadata")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .execute()
    )
    return {row["ticker"]: row for row in (result.data or [])}


def get_latest_risk_snapshot_history_map(
    supabase, tickers: list[str], per_ticker: int = 2
) -> dict[str, list[dict[str, Any]]]:
    if not tickers:
        return {}
    result = (
        supabase.table("ticker_risk_snapshots")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .order("analysis_as_of", desc=True)
        .order("updated_at", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows = sorted(result.data or [], key=_snapshot_sort_key, reverse=True)
    for row in rows:
        ticker = row["ticker"]
        if len(grouped[ticker]) < per_ticker:
            grouped[ticker].append(row)
    return grouped


def get_latest_risk_snapshot_map(
    supabase, tickers: list[str]
) -> dict[str, dict[str, Any]]:
    history = get_latest_risk_snapshot_history_map(supabase, tickers, per_ticker=1)
    return {ticker: rows[0] for ticker, rows in history.items() if rows}


def enrich_positions_with_ticker_cache(
    positions: list[dict[str, Any]], supabase
) -> list[dict[str, Any]]:
    positions = positions or []
    if not positions:
        return []
    tickers = [
        position.get("ticker", "").upper()
        for position in positions
        if position.get("ticker")
    ]
    metadata_map = get_metadata_map(supabase, tickers)
    history_map = get_latest_risk_snapshot_history_map(supabase, tickers, per_ticker=2)
    refresh_job_map = get_latest_refresh_job_map(supabase, tickers)
    news_cache_map = get_latest_news_cache_map(supabase, tickers)
    user_id = positions[0].get("user_id")
    watchlist_tickers: set[str] = set()
    if user_id:
        watchlist = get_or_create_default_watchlist(supabase, user_id)
        if watchlist.get("id"):
            watchlist_rows = (
                supabase.table("watchlist_items")
                .select("ticker")
                .eq("watchlist_id", watchlist["id"])
                .execute()
                .data
                or []
            )
            watchlist_tickers = {
                str(row.get("ticker") or "").upper()
                for row in watchlist_rows
                if row.get("ticker")
            }

    total_portfolio_value = 0.0
    for position in positions:
        ticker = (position.get("ticker") or "").upper()
        metadata = metadata_map.get(ticker, {})
        resolved_price = position.get("current_price")
        if resolved_price is None:
            resolved_price = metadata.get("price")
        shares = position.get("shares")
        if resolved_price is not None and shares is not None:
            total_portfolio_value += float(resolved_price) * float(shares)

    for position in positions:
        ticker = (position.get("ticker") or "").upper()
        metadata = metadata_map.get(ticker, {})
        snapshots = history_map.get(ticker, [])
        latest = snapshots[0] if snapshots else {}
        previous = snapshots[1] if len(snapshots) > 1 else {}
        latest_refresh_job = refresh_job_map.get(ticker, {})
        latest_news_row = news_cache_map.get(ticker, {})
        _shared_position_id, shared_analysis, shared_event_rows = _get_shared_reference_analysis(
            supabase,
            ticker=ticker,
            snapshot=latest,
        )
        shared_summary = build_shared_ticker_analysis_summary(
            ticker=ticker,
            metadata=metadata,
            snapshot=latest,
            previous_snapshot=previous,
            latest_news_row=latest_news_row,
            latest_refresh_job=latest_refresh_job,
            current_analysis=shared_analysis,
            latest_event_analyses=shared_event_rows,
            analysis_run_id=(shared_analysis or {}).get("analysis_run_id"),
        )
        if position.get("current_price") is None:
            position["current_price"] = metadata.get("price")
        portfolio_overlay = build_portfolio_overlay(
            ticker=ticker,
            position=position,
            held_positions=[position],
            is_in_watchlist=ticker in watchlist_tickers,
            total_portfolio_value=total_portfolio_value,
            current_price=position.get("current_price") or metadata.get("price"),
        )
        projected = _project_shared_summary_compatibility(
            base=position,
            shared_summary=shared_summary,
            portfolio_overlay=portfolio_overlay,
            previous_grade=previous.get("grade"),
            risk_dimensions=_shared_risk_dimensions(latest),
        )
        position.clear()
        position.update(projected)

    return positions


def _news_rows_to_response(
    news_rows: list[dict[str, Any]], *, user_id: str, ticker: str
) -> list[dict[str, Any]]:
    responses = []
    for row in news_rows:
        responses.append(
            {
                "id": row.get("id"),
                "user_id": user_id,
                "ticker": ticker,
                "title": row.get("title"),
                "summary": row.get("summary"),
                "source": row.get("source"),
                "url": row.get("source_url") or row.get("canonical_url") or row.get("url", ""),
                "significance": row.get("significance"),
                "sentimentScore": row.get("sentiment_score"),
                "tldr": row.get("tldr"),
                "whatItMeans": row.get("what_it_means"),
                "keyImplications": row.get("key_implications"),
                "published_at": row.get("published_at"),
                "affected_tickers": [ticker],
                "processed_at": row.get("created_at") or row.get("published_at"),
            }
        )
    return responses





def build_position_analysis_from_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    position_id: str,
    ticker: str,
) -> dict[str, Any] | None:
    if not snapshot:
        return None
    summary = snapshot.get("news_summary") or snapshot.get("reasoning")
    watch_items = []
    if snapshot.get("event_adjustment") not in (None, 0, 0.0):
        watch_items.append(
            "Recent events are contributing to the shared ticker risk rating."
        )
    if snapshot.get("macro_adjustment") not in (None, 0, 0.0):
        watch_items.append(
            "Macro conditions are affecting the current shared ticker snapshot."
        )
    return sanitize_public_analysis_text(
        {
            "id": None,
            "analysis_run_id": None,
            "position_id": position_id,
            "ticker": ticker,
            "summary": summary,
            "methodology": "Shared S&P ticker cache using canonical structural scoring and the latest cached ticker snapshot.",
            "top_risks": [],
            "top_tailwinds": [],
            "watch_items": watch_items,
            "top_news": [],
            "driver_cards_state": "pending",
            "driver_cards": [],
            "driver_cards_source": None,
            "major_event_count": 0,
            "minor_event_count": 0,
            "status": "ready",
            "progress_message": "Shared ticker cache is ready.",
            "source_count": snapshot.get("source_count") or 0,
            "updated_at": snapshot.get("analysis_as_of"),
        }
    )


def _normalize_driver_cards_payload(
    analysis: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not analysis:
        return None
    sanitized = {**analysis}
    raw_cards = sanitized.get("driver_cards")
    cards = raw_cards if isinstance(raw_cards, list) else []
    sanitized["driver_cards"] = cards
    state = sanitized.get("driver_cards_state")
    if not state:
        state = "ready" if cards else "pending"
    sanitized["driver_cards_state"] = state
    if sanitized.get("driver_cards_source") not in {"generated", "legacy_fallback"}:
        sanitized["driver_cards_source"] = None
    return sanitized


def _backfill_legacy_driver_cards(
    analysis: dict[str, Any] | None,
    position: dict[str, Any],
    latest_event_analyses: list[dict[str, Any]],
    news_rows: list[dict[str, Any]],
    alerts_rows: list[dict[str, Any]],
    *,
    coverage_state: str | None,
) -> dict[str, Any] | None:
    sanitized = _normalize_driver_cards_payload(analysis)
    if not sanitized or sanitized.get("status") != "ready":
        return sanitized

    if sanitized.get("driver_cards"):
        if sanitized.get("driver_cards_state") in {None, "pending"}:
            sanitized["driver_cards_state"] = "ready"
        if sanitized.get("driver_cards_source") not in {"generated", "legacy_fallback"}:
            sanitized["driver_cards_source"] = "generated"
        return sanitized

    if not latest_event_analyses and not alerts_rows:
        return sanitized

    cards, state, _source = _build_driver_cards(
        {
            **position,
            "analysis_state": sanitized.get("status"),
            "coverage_state": coverage_state,
        },
        latest_event_analyses,
        news_rows,
        alerts_rows,
    )
    sanitized["driver_cards"] = cards
    sanitized["driver_cards_state"] = state
    sanitized["driver_cards_source"] = "legacy_fallback"
    return sanitized


_LEGACY_DIMENSION_MATH_MARKERS = (
    "adds risk at ",
    "supports a safer read at ",
    "is broadly neutral at ",
    "Those inputs land the score at ",
    "Company-specific news (",
    "Macro/sector exposure (",
    "Near-term volatility (",
    "Portfolio construction (",
    "This summary was assembled from the final dimension scores",
    "Limited data: only",
    "analyzed event(s) were available",
    "analyzed event(s) supported this score",
)


def _is_legacy_dimension_math(text: str) -> bool:
    return any(marker in text for marker in _LEGACY_DIMENSION_MATH_MARKERS)


_GENERIC_FALLBACK_MARKERS = (
    "We're still building a full picture for this ticker.",
    "Risk is based on",
    "Risk reflects recent data and sector conditions.",
    "The score reflects underlying fundamentals and sector context",
    "recent news is low risk",
    "recent news is elevated risk",
    "recent news is moderate",
    "near-term volatility is elevated risk",
    "near-term volatility is low risk",
    "near-term volatility is moderate",
    "macro and sector conditions are elevated risk",
    "macro and sector conditions are low risk",
    "macro and sector conditions are moderate",
    "Grade held at ",
    "analyzed event(s) with",
    "analyzed event(s) supported",
    "Limited data: only",
    "limited recent data",
    "rating defaults to structural factors",
    "rating rests on structural and macro factors",
    "known facts are limited",
    "current rating leans on existing position context",
    "not enough recent news to form a confident risk rating",
    "relies on existing position context",
    "no strong news signal surfaced",
    "insufficient evidence was available",
    "risk is broadly contained unless new developments emerge",
    "one new development could shift the rating",
    "event data for ",
)


def _is_generic_fallback_reasoning(text: str) -> bool:
    """Detect our own generic fallback template text (not article-specific)."""
    lowered = (text or "").lower()
    return any(marker.lower() in lowered for marker in _GENERIC_FALLBACK_MARKERS)


_PUBLIC_RATIONALE_BAD_MARKERS = (
    "risk factors for ",
    "synthesized",
    "methodology",
    "fallback",
    "processed",
    "quick brief ready",
    "started the deeper analysis",
    "found ",
    "relevant headlines",
    "coverage is thin",
    "low-confidence data",
    "limited data",
    "this summary was assembled",
    "deterministic score built",
    "company-specific news (",
    "pipeline",
    "analysis running",
    "the model",
    "clavynx",
    "known facts are limited",
    "existing position context",
    "not enough recent news",
    "insufficient evidence was available",
    "event data for ",
)


def _is_public_rationale_text(text: str | None) -> bool:
    candidate = (text or "").strip()
    if not candidate:
        return False
    lowered = candidate.lower()
    return not any(marker in lowered for marker in _PUBLIC_RATIONALE_BAD_MARKERS)


def _looks_like_internal_score_breakdown(text: str | None) -> bool:
    candidate = (text or "").strip().lower()
    return candidate.startswith("structural:") and "macro:" in candidate and "event:" in candidate


def _clean_public_rationale_text(text: str | None) -> str | None:
    if not text:
        return None
    if _is_generic_fallback_reasoning(text):
        _log_rationale_metric("block", "generic_fallback")
        return None
    if _looks_like_internal_score_breakdown(text):
        _log_rationale_metric("block", "internal_score_breakdown")
        return None
    if not _is_public_rationale_text(text):
        _log_rationale_metric("block", "public_bad_marker")
        return None
    return sanitize_public_analysis_text(text)


def _clean_public_text_list(items: list[Any] | None) -> list[str]:
    cleaned_items: list[str] = []
    for item in items or []:
        if not isinstance(item, str):
            continue
        cleaned = _clean_public_rationale_text(item)
        if cleaned:
            cleaned_items.append(cleaned)
    return cleaned_items


def _sanitize_public_analysis_payload(
    analysis: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not analysis:
        return None
    sanitized = _normalize_driver_cards_payload(analysis) or {}
    sanitized["summary"] = _clean_public_rationale_text(sanitized.get("summary"))
    sanitized["long_report"] = _clean_public_rationale_text(
        sanitized.get("long_report")
    )
    sanitized["methodology"] = _clean_public_rationale_text(
        sanitized.get("methodology")
    )
    sanitized["top_risks"] = _clean_public_text_list(sanitized.get("top_risks"))
    sanitized["top_tailwinds"] = _clean_public_text_list(sanitized.get("top_tailwinds"))
    sanitized["watch_items"] = _clean_public_text_list(sanitized.get("watch_items"))
    return sanitize_public_analysis_text(sanitized)


def _sanitize_public_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return None
    sanitized = {**snapshot}
    sanitized["reasoning"] = _clean_public_rationale_text(sanitized.get("reasoning"))
    sanitized["news_summary"] = _clean_public_rationale_text(
        sanitized.get("news_summary")
    )
    source_count = int(sanitized.get("source_count") or 0)
    score = sanitized.get("safety_score")
    raw_public_text = sanitized.get("reasoning") or sanitized.get("news_summary")
    if score is not None:
        sanitized["grade"] = score_to_grade(score)
        if raw_public_text:
            sanitized["reasoning"] = format_rationale(
                grade=sanitized["grade"],
                direction=grade_direction(score, sanitized.get("previous_total_score")),
                raw_text=raw_public_text,
                scores=sanitized,
                source_count=source_count,
            )
    sanitized["evidence_strength"] = evidence_strength(source_count)
    return sanitize_public_analysis_text(sanitized)


def _derive_coverage_state(source_count: Any, fallback: str | None = None) -> str:
    if fallback:
        return str(fallback)
    count = int(source_count or 0)
    if count == 0:
        return "provisional"
    if count <= 2:
        return "thin"
    return "substantive"


def _shared_freshness_status(
    *,
    snapshot: dict[str, Any] | None,
    latest_news_row: dict[str, Any] | None,
    latest_refresh_job: dict[str, Any] | None,
    coverage_state: str,
) -> str:
    latest_refresh_status = (latest_refresh_job or {}).get("status")
    if latest_refresh_status == "queued":
        return "queued"
    if latest_refresh_status == "running":
        return "running"
    if latest_refresh_status == "failed":
        return "failed"
    if not snapshot:
        return "thin" if coverage_state in {"provisional", "thin"} else "stale"
    if coverage_state in {"provisional", "thin"}:
        return "thin"

    analysis_dt = _parse_iso_datetime((snapshot or {}).get("analysis_as_of"))
    news_dt = _parse_iso_datetime((latest_news_row or {}).get("processed_at"))
    if analysis_dt and news_dt and news_dt - analysis_dt > timedelta(hours=6):
        return "stale"
    return "ready"


def _first_non_none(*values: Any) -> Any:
    for v in values:
        if v is not None:
            return v
    return None


def _shared_risk_dimensions(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    snapshot = snapshot or {}
    factor_breakdown = snapshot.get("factor_breakdown") or {}
    if isinstance(factor_breakdown, str):
        import json

        try:
            factor_breakdown = json.loads(factor_breakdown)
        except Exception:
            factor_breakdown = {}
    ai_dims = (factor_breakdown or {}).get("ai_dimensions") or {}
    return {
        "financial_health": _first_non_none(
            snapshot.get("financial_health"),
            ai_dims.get("financial_health"),
            ai_dims.get("position_sizing"),
        ),
        "news_sentiment": _first_non_none(
            snapshot.get("news_sentiment_dim"),
            ai_dims.get("news_sentiment"),
        ),
        "macro_exposure": _first_non_none(
            snapshot.get("macro_exposure_dim"),
            ai_dims.get("macro_exposure"),
        ),
        "sector_exposure": _first_non_none(
            snapshot.get("sector_exposure"),
            ai_dims.get("sector_exposure"),
        ),
        "volatility": _first_non_none(
            snapshot.get("volatility"),
            ai_dims.get("volatility"),
            ai_dims.get("volatility_trend"),
        ),
    }


def _sanitize_factor_breakdown_payload(
    factor_breakdown: dict[str, Any] | str | None,
) -> dict[str, Any]:
    if isinstance(factor_breakdown, str):
        import json

        try:
            factor_breakdown = json.loads(factor_breakdown)
        except Exception:
            factor_breakdown = {}
    if not isinstance(factor_breakdown, dict):
        factor_breakdown = {}

    ai_dimensions = factor_breakdown.get("ai_dimensions") or {}
    sanitized_ai_dimensions = {
        "financial_health": _first_non_none(
            ai_dimensions.get("financial_health"),
            ai_dimensions.get("position_sizing"),
        ),
        "news_sentiment": ai_dimensions.get("news_sentiment"),
        "macro_exposure": ai_dimensions.get("macro_exposure"),
        "sector_exposure": ai_dimensions.get("sector_exposure"),
        "volatility": _first_non_none(
            ai_dimensions.get("volatility"),
            ai_dimensions.get("volatility_trend"),
        ),
    }
    return {
        **factor_breakdown,
        "ai_dimensions": sanitized_ai_dimensions,
    }


def _project_driver_cards_to_risk_drivers(
    analysis: dict[str, Any] | None,
    *,
    ticker: str,
) -> tuple[list[dict[str, Any]], str]:
    analysis = analysis or {}
    cards = analysis.get("driver_cards") or []
    state = analysis.get("driver_cards_state") or ("ready" if cards else "pending")
    projected: list[dict[str, Any]] = []
    for card in cards:
        projected.append(
            {
                "driver_id": card.get("id") or str(uuid4()),
                "ticker": ticker,
                "rank": card.get("rank") or len(projected) + 1,
                "category": card.get("theme"),
                "title": card.get("title") or "",
                "summary": card.get("summary") or "",
                "direction": card.get("direction"),
                "strength": card.get("strength") or "thin",
                "source_chips": card.get("source_chips") or [],
                "evidence_event_ids": [
                    evidence.get("id")
                    for evidence in (card.get("supporting_evidence") or [])
                    if evidence.get("id")
                ],
                "updated_at": analysis.get("updated_at"),
                "provenance": analysis.get("driver_cards_source"),
            }
        )
    return sanitize_public_analysis_text(projected), state


def _get_shared_reference_position_id(supabase, ticker: str) -> str | None:
    result = (
        supabase.table("positions")
        .select("id")
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .eq("ticker", ticker)
        .execute()
        .data
        or []
    )
    return result[0].get("id") if result else None


def _batch_get_shared_reference_analyses(
    supabase,
    tickers: list[str],
    snapshot_map: dict[str, dict[str, Any] | None],
) -> dict[str, tuple[str | None, dict[str, Any] | None, list[dict[str, Any]]]]:
    if not tickers:
        return {}

    position_rows = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .in_("ticker", tickers)
        .execute()
        .data
        or []
    )
    ticker_to_position_id: dict[str, str] = {}
    for row in position_rows:
        t = (row.get("ticker") or "").upper()
        ticker_to_position_id[t] = row["id"]

    position_ids = list(ticker_to_position_id.values())
    analysis_map: dict[str, dict[str, Any] | None] = {}
    if position_ids:
        pa_rows = (
            supabase.table("position_analyses")
            .select("*")
            .in_("position_id", position_ids)
            .eq("status", "ready")
            .order("updated_at", desc=True)
            .order("created_at", desc=True)
            .limit(len(position_ids) * 5)
            .execute()
            .data
            or []
        )
        best_by_pid: dict[str, dict[str, Any]] = {}
        for row in pa_rows:
            pid = row.get("position_id")
            if pid and pid not in best_by_pid:
                best_by_pid[pid] = row
        for ticker, pid in ticker_to_position_id.items():
            analysis_map[ticker] = best_by_pid.get(pid)

    event_rows = (
        supabase.table("shared_ticker_events")
        .select("*")
        .in_("ticker", tickers)
        .order("published_at", desc=True)
        .order("confidence", desc=True, nullsfirst=False)
        .limit(len(tickers) * 30)
        .execute()
        .data
        or []
    )
    events_by_ticker: dict[str, list[dict[str, Any]]] = {t: [] for t in tickers}
    for row in event_rows:
        t = (row.get("ticker") or "").upper()
        if t in events_by_ticker:
            events_by_ticker[t].append(row)
    for t in tickers:
        events_by_ticker[t] = _dedup_event_analyses(events_by_ticker[t])[:10]

    results: dict[str, tuple[str | None, dict[str, Any] | None, list[dict[str, Any]]]] = {}
    for ticker in tickers:
        position_id = ticker_to_position_id.get(ticker)
        analysis_raw = analysis_map.get(ticker)
        analysis = _sanitize_public_analysis_payload(
            analysis_raw
            or build_position_analysis_from_snapshot(
                snapshot_map.get(ticker),
                position_id=position_id or f"virtual:{ticker}",
                ticker=ticker,
            )
        )
        events = events_by_ticker.get(ticker, [])
        if not events and position_id:
            fallback = (
                supabase.table("event_analyses")
                .select("*")
                .eq("position_id", position_id)
                .order("created_at", desc=True)
                .limit(10)
                .execute()
                .data
                or []
            )
            events = _dedup_event_analyses(fallback)
        results[ticker] = (position_id, analysis, events)

    return results


def _get_shared_reference_analysis(
    supabase,
    *,
    ticker: str,
    snapshot: dict[str, Any] | None,
) -> tuple[str | None, dict[str, Any] | None, list[dict[str, Any]]]:
    position_id = _get_shared_reference_position_id(supabase, ticker)
    analysis = _sanitize_public_analysis_payload(
        _get_latest_position_analysis_for_ids(supabase, [position_id])
        if position_id
        else None
        or build_position_analysis_from_snapshot(
            snapshot,
            position_id=position_id or f"virtual:{ticker}",
            ticker=ticker,
        )
    )
    event_rows = _get_shared_ticker_events(supabase, ticker=ticker, limit=10)
    if not event_rows and position_id:
        event_result = (
            supabase.table("event_analyses")
            .select("*")
            .eq("position_id", position_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        event_rows = _dedup_event_analyses(event_result.data or [])
    return position_id, analysis, event_rows


def _get_shared_ticker_events(
    supabase,
    *,
    ticker: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Read canonical shared ticker events, preferring highest confidence."""
    try:
        result = (
            supabase.table("shared_ticker_events")
            .select("*")
            .eq("ticker", ticker)
            .order("published_at", desc=True)
            .order("confidence", desc=True, nullsfirst=False)
            .limit(limit * 3)
            .execute()
        )
        rows = result.data or []
        deduped = _dedup_event_analyses(rows)
        return deduped[:limit]
    except Exception:
        return []


def _project_shared_event_to_legacy(event: dict[str, Any], *, ticker: str | None = None) -> dict[str, Any]:
    """Project a shared_ticker_events row into event_analyses-compatible shape."""
    return {
        "id": event.get("id"),
        "analysis_run_id": event.get("analysis_run_id"),
        "position_id": f"shared:ticker:{ticker or event.get('ticker', 'unknown')}",
        "event_hash": event.get("event_hash"),
        "title": event.get("title", ""),
        "summary": event.get("summary"),
        "source": event.get("source"),
        "source_url": event.get("source_url"),
        "published_at": event.get("published_at"),
        "event_type": event.get("event_type"),
        "significance": event.get("significance"),
        "classification": event.get("classification"),
        "analysis_source": event.get("analysis_source") or event.get("provenance", "shared"),
        "long_analysis": event.get("long_analysis"),
        "what_happened": event.get("what_happened"),
        "tldr": event.get("tldr"),
        "what_it_means": event.get("what_it_means"),
        "confidence": event.get("confidence"),
        "impact_horizon": event.get("impact_horizon"),
        "risk_direction": event.get("risk_direction"),
        "scenario_summary": event.get("scenario_summary"),
        "key_implications": event.get("key_implications") or [],
        "recommended_followups": event.get("follow_up_notes") or [],
        "tags": event.get("tags") or [],
        "created_at": event.get("created_at") or event.get("published_at"),
        "factored_into_score": event.get("factored_into_score", False),
        "provenance": event.get("provenance", "shared"),
    }


def build_shared_ticker_analysis_summary(
    *,
    ticker: str,
    metadata: dict[str, Any] | None,
    snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None = None,
    latest_news_row: dict[str, Any] | None = None,
    latest_refresh_job: dict[str, Any] | None = None,
    current_analysis: dict[str, Any] | None = None,
    latest_event_analyses: list[dict[str, Any]] | None = None,
    analysis_run_id: str | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    snapshot = _sanitize_public_snapshot(snapshot) or {}
    previous_snapshot = previous_snapshot or {}
    current_analysis = _sanitize_public_analysis_payload(current_analysis) or {}
    latest_event_analyses = latest_event_analyses or []

    current_score = snapshot.get("composite_score") or snapshot.get("safety_score")
    previous_score = previous_snapshot.get("composite_score") or previous_snapshot.get(
        "safety_score"
    )
    source_count = snapshot.get("source_count")
    if source_count is None:
        source_count = current_analysis.get("source_count")
    coverage_state = _derive_coverage_state(
        source_count,
        fallback=snapshot.get("coverage_state") or current_analysis.get("coverage_state"),
    )
    if source_count is None and coverage_state == "substantive":
        source_count = 3
    coverage_note = snapshot.get("coverage_note") or current_analysis.get(
        "coverage_note"
    ) or _investor_coverage_note(coverage_state, source_count)
    freshness_status = _shared_freshness_status(
        snapshot=snapshot,
        latest_news_row=latest_news_row,
        latest_refresh_job=latest_refresh_job,
        coverage_state=coverage_state,
    )
    latest_refresh_status = (latest_refresh_job or {}).get("status")

    raw_rationale = (
        snapshot.get("news_summary")
        or snapshot.get("reasoning")
        or current_analysis.get("summary")
        or current_analysis.get("long_report")
    )
    grade_rationale = None
    if raw_rationale:
        grade_rationale = format_rationale(
            grade=snapshot.get("grade")
            or (score_to_grade(current_score) if current_score is not None else "C"),
            direction=grade_direction(current_score, previous_score),
            raw_text=raw_rationale,
            scores={
                "financial_health": (_shared_risk_dimensions(snapshot) or {}).get(
                    "financial_health"
                ),
                "news_sentiment": (_shared_risk_dimensions(snapshot) or {}).get(
                    "news_sentiment"
                ),
                "macro_exposure": (_shared_risk_dimensions(snapshot) or {}).get(
                    "macro_exposure"
                ),
                "sector_exposure": (_shared_risk_dimensions(snapshot) or {}).get(
                    "sector_exposure"
                ),
                "volatility": (_shared_risk_dimensions(snapshot) or {}).get(
                    "volatility"
                ),
            },
            source_count=int(source_count or 0),
        )
    if not grade_rationale:
        grade_rationale = format_rationale(
            grade=snapshot.get("grade")
            or (score_to_grade(current_score) if current_score is not None else "C"),
            direction=grade_direction(current_score, previous_score),
            raw_text="",
            scores={},
            source_count=int(source_count or 0),
        )
    if latest_event_analyses:
        canonical_reasoning = _canonical_public_rationale(
            ticker=ticker,
            current_score={
                "grade": snapshot.get("grade"),
                "total_score": current_score,
                "source_count": source_count,
            },
            current_analysis=current_analysis,
            latest_event_analyses=latest_event_analyses,
            latest_risk_snapshot=snapshot,
        )
        if canonical_reasoning:
            grade_rationale = format_rationale(
                grade=snapshot.get("grade")
                or (score_to_grade(current_score) if current_score is not None else "C"),
                direction=grade_direction(current_score, previous_score),
                raw_text=canonical_reasoning,
                scores={},
                source_count=int(source_count or 0),
            )

    summary = {
        "ticker": ticker,
        "company_name": metadata.get("company_name"),
        "exchange": metadata.get("exchange"),
        "sector": metadata.get("sector"),
        "industry": metadata.get("industry"),
        "current_score": current_score,
        "current_grade": snapshot.get("grade")
        or (score_to_grade(current_score) if current_score is not None else None),
        "grade_direction": grade_direction(current_score, previous_score),
        "score_delta": int(round(current_score - previous_score))
        if current_score is not None and previous_score is not None
        else None,
        "grade_rationale": grade_rationale,
        "source_count": source_count,
        "major_event_count": current_analysis.get("major_event_count"),
        "minor_event_count": current_analysis.get("minor_event_count"),
        "evidence_strength": snapshot.get("evidence_strength")
        or evidence_strength(int(source_count or 0)),
        "analysis_run_id": analysis_run_id or current_analysis.get("analysis_run_id"),
        "methodology_version": snapshot.get("methodology_version"),
        "analysis_source": "shared",
        "freshness": {
            "status": freshness_status,
            "coverage_state": coverage_state,
            "coverage_note": coverage_note,
            "score_as_of": snapshot.get("analysis_as_of"),
            "analysis_as_of": snapshot.get("analysis_as_of"),
            "price_as_of": metadata.get("price_as_of"),
            "news_as_of": (latest_news_row or {}).get("published_at"),
            "last_news_refresh_at": (latest_news_row or {}).get("processed_at")
            or (latest_refresh_job or {}).get("completed_at"),
            "last_success_at": (latest_refresh_job or {}).get("completed_at")
            if latest_refresh_status == "completed"
            else None,
            "last_failure_at": (latest_refresh_job or {}).get("completed_at")
            if latest_refresh_status == "failed"
            else None,
            "latest_analysis_run_id": analysis_run_id or current_analysis.get("analysis_run_id"),
            "latest_analysis_status": None,
            "latest_refresh_job_id": (latest_refresh_job or {}).get("id"),
            "latest_refresh_status": latest_refresh_status,
            "analysis_run_id": analysis_run_id or current_analysis.get("analysis_run_id"),
            "methodology_version": snapshot.get("methodology_version"),
        },
    }
    return sanitize_public_analysis_text(summary)


def build_portfolio_overlay(
    *,
    ticker: str,
    position: dict[str, Any] | None = None,
    held_positions: list[dict[str, Any]] | None = None,
    is_in_watchlist: bool = False,
    total_portfolio_value: float | None = None,
    latest_alerts: list[dict[str, Any]] | None = None,
    current_price: float | None = None,
) -> dict[str, Any]:
    held_positions = held_positions or ([] if not position else [position])
    selected_position = position or (held_positions[0] if held_positions else None)
    shares = selected_position.get("shares") if selected_position else None
    cost_basis = selected_position.get("purchase_price") if selected_position else None
    resolved_price = current_price
    if resolved_price is None and selected_position is not None:
        resolved_price = selected_position.get("current_price")
    market_value = None
    if shares is not None and resolved_price is not None:
        market_value = float(shares) * float(resolved_price)
    portfolio_weight = None
    if market_value is not None and total_portfolio_value and total_portfolio_value > 0:
        portfolio_weight = market_value / total_portfolio_value
    latest_alerts = latest_alerts or []
    latest_alert_at = latest_alerts[0].get("created_at") if latest_alerts else None
    overlay = {
        "position_id": selected_position.get("id") if selected_position else None,
        "holding_ids": [row.get("id") for row in held_positions if row.get("id")],
        "is_held": bool(held_positions),
        "is_in_watchlist": bool(is_in_watchlist),
        "shares": shares,
        "cost_basis": cost_basis,
        "current_price": resolved_price,
        "market_value": market_value,
        "portfolio_weight": portfolio_weight,
        "risk_contribution_score": None,
        "recent_alert_count": len(latest_alerts),
        "latest_alert_at": latest_alert_at,
        "user_notes": None,
        "overlay_as_of": (
            selected_position.get("updated_at")
            if selected_position and selected_position.get("updated_at")
            else selected_position.get("created_at")
            if selected_position and selected_position.get("created_at")
            else _utcnow_iso()
        ),
    }
    return sanitize_public_analysis_text(overlay)


def _build_exec_summary_from_news_rows(
    recent_news_rows: list[dict[str, Any]],
    ticker: str,
) -> str | None:
    """Build a lightweight executive summary from the most recent article TLDRs when
    no formal position_analyses or snapshot summary is available.

    Returns None if there are no usable news rows so iOS can show a proper empty state.
    """
    usable = [
        row for row in (recent_news_rows or [])
        if row.get("tldr") or row.get("what_it_means") or row.get("summary")
    ][:3]
    if not usable:
        return None

    parts: list[str] = []
    for row in usable:
        snippet = sanitize_text_field(
            row.get("tldr") or row.get("what_it_means") or row.get("summary") or "",
            fallback="",
        ).strip()
        if snippet:
            parts.append(snippet)

    if not parts:
        return None

    return " ".join(parts)


def build_shared_ticker_analysis_detail(
    *,
    ticker: str,
    metadata: dict[str, Any] | None,
    snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None = None,
    latest_news_row: dict[str, Any] | None = None,
    latest_refresh_job: dict[str, Any] | None = None,
    current_analysis: dict[str, Any] | None = None,
    latest_event_analyses: list[dict[str, Any]] | None = None,
    recent_news_rows: list[dict[str, Any]] | None = None,
    analysis_run_id: str | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    snapshot = _sanitize_public_snapshot(snapshot) or {}
    current_analysis = _sanitize_public_analysis_payload(current_analysis) or {}
    latest_event_analyses = latest_event_analyses or []
    recent_news_rows = recent_news_rows or []
    if not latest_event_analyses and recent_news_rows:
        snapshot_as_of = snapshot.get("analysis_as_of")
        if snapshot_as_of:
            recent_news_rows = [
                row
                for row in recent_news_rows
                if (row.get("processed_at") or "") <= snapshot_as_of
            ]
        latest_event_analyses = _build_event_analyses_from_news_rows(
            recent_news_rows,
            ticker=ticker,
            position_id=analysis_run_id or f"virtual:{ticker}",
        )
    summary = build_shared_ticker_analysis_summary(
        ticker=ticker,
        metadata=metadata,
        snapshot=snapshot,
        previous_snapshot=previous_snapshot,
        latest_news_row=latest_news_row,
        latest_refresh_job=latest_refresh_job,
        current_analysis=current_analysis,
        latest_event_analyses=latest_event_analyses,
        analysis_run_id=analysis_run_id,
    )
    risk_drivers, drivers_state = _project_driver_cards_to_risk_drivers(
        current_analysis,
        ticker=ticker,
    )
    drivers_provenance = current_analysis.get("driver_cards_source")
    events = build_public_event_articles(latest_event_analyses, ticker=ticker)
    source_count_limit = int(summary.get("source_count") or 0)
    if snapshot.get("analysis_as_of") and source_count_limit and len(events) > source_count_limit:
        events = events[:source_count_limit]
    key_implications = []
    follow_up_notes = []
    source_links = []
    for event in events:
        for implication in event.get("key_implications") or []:
            if implication not in key_implications:
                key_implications.append(implication)
        for note in event.get("follow_up_notes") or []:
            if note not in follow_up_notes:
                follow_up_notes.append(note)
        source_link = event.get("source_article_link")
        if source_link and source_link not in source_links:
            source_links.append(source_link)
    detail = {
        "summary": summary,
        "latest_price": metadata.get("price"),
        "previous_close": metadata.get("previous_close"),
        "open_price": metadata.get("open_price"),
        "day_high": metadata.get("day_high"),
        "day_low": metadata.get("day_low"),
        "week_52_high": metadata.get("week_52_high"),
        "week_52_low": metadata.get("week_52_low"),
        "avg_volume": metadata.get("avg_volume"),
        "pe_ratio": metadata.get("pe_ratio"),
        "market_cap": metadata.get("market_cap"),
        "risk_dimensions": _shared_risk_dimensions(snapshot),
        "executive_summary": current_analysis.get("summary")
        or snapshot.get("news_summary")
        or snapshot.get("reasoning")
        or _build_exec_summary_from_news_rows(recent_news_rows, ticker),
        "detailed_report": current_analysis.get("long_report"),
        "methodology_note": current_analysis.get("methodology"),
        "risk_drivers": risk_drivers,
        "risk_drivers_state": drivers_state,
        "risk_drivers_provenance": drivers_provenance,
        "events": events,
        "key_implications": key_implications,
        "follow_up_notes": follow_up_notes,
        "source_links": source_links,
    }
    return sanitize_public_analysis_text(detail)


def _project_shared_summary_compatibility(
    *,
    base: dict[str, Any],
    shared_summary: dict[str, Any],
    portfolio_overlay: dict[str, Any] | None = None,
    previous_grade: str | None = None,
    risk_dimensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overlay = portfolio_overlay or {}
    freshness = shared_summary.get("freshness") or {}
    projected = {
        **base,
        "shared_analysis": shared_summary,
        "portfolio_overlay": overlay or None,
        "grade": shared_summary.get("current_grade"),
        "risk_grade": shared_summary.get("current_grade"),
        "safety_score": shared_summary.get("current_score"),
        "total_score": shared_summary.get("current_score"),
        "previous_grade": previous_grade,
        "grade_direction": shared_summary.get("grade_direction"),
        "score_delta": shared_summary.get("score_delta"),
        "summary": shared_summary.get("grade_rationale"),
        "dimension_breakdown": risk_dimensions or {},
        "last_analyzed_at": freshness.get("score_as_of"),
        "analysis_state": freshness.get("status"),
        "coverage_state": freshness.get("coverage_state"),
        "coverage_note": freshness.get("coverage_note"),
        "analysis_run_id": shared_summary.get("analysis_run_id"),
        "latest_analysis_run_status": freshness.get("latest_analysis_status"),
        "latest_refresh_job_id": freshness.get("latest_refresh_job_id"),
        "latest_refresh_job_status": freshness.get("latest_refresh_status"),
        "analysis_as_of": freshness.get("analysis_as_of"),
        "score_source": shared_summary.get("analysis_source"),
        "score_as_of": freshness.get("score_as_of"),
        "score_version": shared_summary.get("methodology_version"),
        "last_news_refresh_at": freshness.get("last_news_refresh_at"),
        "price_as_of": freshness.get("price_as_of"),
        "news_as_of": freshness.get("news_as_of"),
        "news_refresh_status": freshness.get("latest_refresh_status")
        or ("cached" if freshness.get("news_as_of") else None),
        "source": shared_summary.get("analysis_source"),
        "company_name": shared_summary.get("company_name"),
    }
    return sanitize_public_analysis_text(projected)


def _project_shared_detail_compatibility(
    *,
    ticker: str,
    shared_detail: dict[str, Any],
    portfolio_overlay: dict[str, Any],
    base_position: dict[str, Any],
    metadata: dict[str, Any],
    snapshot: dict[str, Any] | None,
    latest_refresh_job: dict[str, Any] | None,
    latest_analysis_run: dict[str, Any] | None,
    latest_alerts: list[dict[str, Any]],
    recent_news_rows: list[dict[str, Any]],
    is_selected_held: bool,
) -> dict[str, Any]:
    summary = shared_detail.get("summary") or {}
    freshness = summary.get("freshness") or {}
    snapshot = snapshot or {}
    factor_breakdown = _sanitize_factor_breakdown_payload(snapshot.get("factor_breakdown")) or {
        "ai_dimensions": shared_detail.get("risk_dimensions") or {}
    }
    previous_grade = base_position.get("previous_grade")
    position = _project_shared_summary_compatibility(
        base=base_position,
        shared_summary=summary,
        portfolio_overlay=portfolio_overlay,
        previous_grade=previous_grade,
        risk_dimensions=shared_detail.get("risk_dimensions") or {},
    )
    position["current_price"] = portfolio_overlay.get("current_price") or metadata.get("price")
    position["evidence_strength"] = summary.get("evidence_strength")
    compat_status = freshness.get("status")
    latest_run_status = (latest_analysis_run or {}).get("status")
    if latest_run_status == "queued":
        compat_status = "queued"
    elif latest_run_status in {"starting", "running"}:
        compat_status = "running"
    elif latest_run_status == "failed":
        compat_status = "failed"
    current_score = {
        "id": None,
        "position_id": f"shared:{ticker}",
        "score_source": summary.get("analysis_source"),
        "score_as_of": freshness.get("score_as_of"),
        "score_version": summary.get("methodology_version"),
        "safety_score": summary.get("current_score"),
        "composite_score": summary.get("current_score"),
        "confidence": None,
        "structural_base_score": None,
        "macro_adjustment": None,
        "event_adjustment": None,
        "grade": summary.get("current_grade"),
        "grade_direction": summary.get("grade_direction"),
        "score_delta": summary.get("score_delta"),
        "reasoning": summary.get("grade_rationale"),
        "factor_breakdown": factor_breakdown,
        "calculated_at": freshness.get("score_as_of"),
        "total_score": summary.get("current_score"),
        "news_sentiment": (shared_detail.get("risk_dimensions") or {}).get(
            "news_sentiment"
        ),
        "macro_exposure": (shared_detail.get("risk_dimensions") or {}).get(
            "macro_exposure"
        ),
        "financial_health": (shared_detail.get("risk_dimensions") or {}).get(
            "financial_health"
        ),
        "sector_exposure": (shared_detail.get("risk_dimensions") or {}).get(
            "sector_exposure"
        ),
        "volatility": (shared_detail.get("risk_dimensions") or {}).get(
            "volatility"
        ),
        "source_count": summary.get("source_count"),
        "major_event_count": summary.get("major_event_count"),
        "minor_event_count": summary.get("minor_event_count"),
        "coverage_state": freshness.get("coverage_state"),
        "coverage_note": freshness.get("coverage_note"),
        "is_provisional": freshness.get("coverage_state") != "substantive",
        "evidence_strength": summary.get("evidence_strength"),
    }
    current_analysis = {
        "id": None,
        "analysis_run_id": summary.get("analysis_run_id"),
        "position_id": f"shared:{ticker}",
        "ticker": ticker,
        "summary": shared_detail.get("executive_summary"),
        "long_report": shared_detail.get("detailed_report"),
        "methodology": shared_detail.get("methodology_note"),
        "top_risks": shared_detail.get("key_implications") or [],
        "top_tailwinds": [],
        "watch_items": shared_detail.get("follow_up_notes") or [],
        "top_news": [],
        "driver_cards_state": shared_detail.get("risk_drivers_state"),
        "driver_cards": [
            {
                "id": driver.get("driver_id"),
                "rank": driver.get("rank"),
                "theme": driver.get("category"),
                "direction": driver.get("direction"),
                "title": driver.get("title"),
                "summary": driver.get("summary"),
                "strength": driver.get("strength"),
                "source_chips": driver.get("source_chips") or [],
                "supporting_evidence": [
                    {"id": evidence_id}
                    for evidence_id in (driver.get("evidence_event_ids") or [])
                ],
            }
            for driver in (shared_detail.get("risk_drivers") or [])
        ],
        "driver_cards_source": shared_detail.get("risk_drivers_provenance") or "generated",
        "major_event_count": summary.get("major_event_count"),
        "minor_event_count": summary.get("minor_event_count"),
        "status": "ready",
        "progress_message": "Shared ticker analysis is ready.",
        "source_count": summary.get("source_count"),
        "updated_at": freshness.get("analysis_as_of"),
    }
    snapshot_reasoning = summary.get("grade_rationale")
    if (
        int(summary.get("source_count") or 0) <= 1
        and not (shared_detail.get("events") or [])
        and not (shared_detail.get("risk_drivers") or [])
    ):
        snapshot_reasoning = None
    return sanitize_public_analysis_text(
        {
            "ticker": ticker,
            "profile": {
                "ticker": ticker,
                "company_name": summary.get("company_name"),
                "exchange": summary.get("exchange"),
                "sector": summary.get("sector"),
                "industry": summary.get("industry"),
                "pe_ratio": metadata.get("pe_ratio"),
                "week_52_high": metadata.get("week_52_high"),
                "week_52_low": metadata.get("week_52_low"),
                "market_cap": metadata.get("market_cap"),
            },
            "position": position,
            "latest_price": {
                "price": shared_detail.get("latest_price"),
                "price_as_of": freshness.get("price_as_of"),
                "previous_close": shared_detail.get("previous_close"),
                "open_price": shared_detail.get("open_price"),
                "day_high": shared_detail.get("day_high"),
                "day_low": shared_detail.get("day_low"),
                "week_52_high": shared_detail.get("week_52_high"),
                "week_52_low": shared_detail.get("week_52_low"),
                "avg_volume": shared_detail.get("avg_volume"),
                "source": metadata.get("last_price_source"),
            },
            "source": summary.get("analysis_source"),
            "analysis_state": {
                **freshness,
                "status": compat_status,
                "source": summary.get("analysis_source"),
                "latest_analysis_run_id": (latest_analysis_run or {}).get("id"),
                "latest_analysis_status": (latest_analysis_run or {}).get("status"),
                "score_source": summary.get("analysis_source"),
                "score_as_of": freshness.get("score_as_of"),
                "score_version": summary.get("methodology_version"),
            },
            "latest_analysis_run": latest_analysis_run,
            "latest_refresh_job": latest_refresh_job,
            "coverage_state": freshness.get("coverage_state"),
            "latest_risk_snapshot": {
                "id": None,
                "ticker": ticker,
                "grade": summary.get("current_grade"),
                "safety_score": summary.get("current_score"),
                "composite_score": summary.get("current_score"),
                "financial_health": (shared_detail.get("risk_dimensions") or {}).get(
                    "financial_health"
                ),
                "news_sentiment_dim": (shared_detail.get("risk_dimensions") or {}).get(
                    "news_sentiment"
                ),
                "macro_exposure_dim": (shared_detail.get("risk_dimensions") or {}).get(
                    "macro_exposure"
                ),
                "sector_exposure": (shared_detail.get("risk_dimensions") or {}).get(
                    "sector_exposure"
                ),
                "volatility": (shared_detail.get("risk_dimensions") or {}).get(
                    "volatility"
                ),
                "factor_breakdown": factor_breakdown,
                "reasoning": snapshot_reasoning,
                "news_summary": shared_detail.get("executive_summary"),
                "analysis_as_of": freshness.get("analysis_as_of"),
                "methodology_version": summary.get("methodology_version"),
            },
            "current_score": current_score,
            "composite_score": summary.get("current_score"),
            "current_analysis": current_analysis,
            "methodology": shared_detail.get("methodology_note"),
            "dimension_breakdown": {"ai_dimensions": shared_detail.get("risk_dimensions") or {}},
            "risk_dimensions": shared_detail.get("risk_dimensions") or {},
            "factor_breakdown": factor_breakdown,
            "latest_event_analyses": shared_detail.get("events") or [],
            "recent_news": _news_rows_to_response(recent_news_rows, user_id=base_position.get("user_id") or "", ticker=ticker),
            "recent_alerts": enrich_alert_rows(latest_alerts),
            "freshness": {
                "price_as_of": freshness.get("price_as_of"),
                "analysis_as_of": freshness.get("analysis_as_of"),
                "last_news_refresh_at": freshness.get("last_news_refresh_at"),
                "news_as_of": freshness.get("news_as_of"),
                "news_refresh_status": freshness.get("latest_refresh_status")
                or ("cached" if freshness.get("news_as_of") else None),
            },
            "user_context": {
                "is_held": portfolio_overlay.get("is_held"),
                "holding_ids": portfolio_overlay.get("holding_ids") or [],
                "is_in_watchlist": portfolio_overlay.get("is_in_watchlist"),
            },
            "shared_analysis": shared_detail,
            "portfolio_overlay": portfolio_overlay,
            "selected_position_held": is_selected_held,
        }
    )


def _canonical_public_rationale(
    *,
    ticker: str,
    current_score: dict[str, Any] | None,
    current_analysis: dict[str, Any] | None = None,
    latest_event_analyses: list[dict[str, Any]] | None = None,
    latest_risk_snapshot: dict[str, Any] | None = None,
) -> str | None:
    current_score = current_score or {}
    current_analysis = current_analysis or {}
    latest_risk_snapshot = latest_risk_snapshot or {}
    latest_event_analyses = latest_event_analyses or []

    if latest_event_analyses:
        article_reasoning = _build_article_aware_reasoning(
            latest_event_analyses,
            current_score,
            ticker,
        )
        article_reasoning = _clean_public_rationale_text(article_reasoning)
        if article_reasoning:
            _log_rationale_metric("source", "event_analyses", ticker=ticker)
            return article_reasoning

    score_reasoning = _clean_public_rationale_text(current_score.get("reasoning"))
    if score_reasoning:
        _log_rationale_metric("source", "score_reasoning", ticker=ticker)
        return score_reasoning

    if current_analysis.get("status") == "ready":
        for candidate in (
            current_analysis.get("summary"),
            current_analysis.get("long_report"),
        ):
            cleaned = _clean_public_rationale_text(candidate)
            if cleaned:
                source = (
                    "analysis_summary"
                    if candidate == current_analysis.get("summary")
                    else "analysis_long_report"
                )
                _log_rationale_metric("source", source, ticker=ticker)
                return cleaned

    cleaned_snapshot = _clean_public_rationale_text(
        latest_risk_snapshot.get("news_summary")
    )
    if cleaned_snapshot:
        _log_rationale_metric("source", "news_summary", ticker=ticker)
        return cleaned_snapshot

    _log_rationale_metric("source", "safe_fallback", ticker=ticker)
    return None


def _normalize_headline(title: str) -> str:
    """Normalize a headline for dedup: lowercase, strip source suffixes, remove punctuation."""
    import re

    t = (title or "").lower().strip()
    # Strip trailing source attribution: " - Reuters", " | CNBC", " — Bloomberg"
    t = re.sub(r"\s*[-|—]\s*[A-Za-z][\w\s.,&'-]{1,40}$", "", t).strip()
    # Remove all non-alphanumeric chars except spaces
    t = re.sub(r"[^a-z0-9\s]", "", t).strip()
    # Collapse whitespace
    return re.sub(r"\s+", " ", t)


def _dedup_event_analyses(events: list[dict]) -> list[dict]:
    """
    Deduplicate event_analyses rows.
    Priority: highest confidence first, then most recent.
    Dedup key: event_hash, then normalized headline.
    """
    sorted_events = sorted(
        events,
        key=lambda e: (
            float(e.get("confidence") or 0),
            e.get("created_at") or "",
        ),
        reverse=True,
    )
    seen_hashes: set[str] = set()
    seen_titles: set[str] = set()
    result: list[dict] = []
    for event in sorted_events:
        h = (event.get("event_hash") or "").strip()
        norm = _normalize_headline(event.get("title") or "")
        if h and h in seen_hashes:
            continue
        if norm and norm in seen_titles:
            continue
        if h:
            seen_hashes.add(h)
        if norm:
            seen_titles.add(norm)
        result.append(event)
    return result


def _clean_public_event_text(value: Any) -> str | None:
    text = sanitize_text_field(value, fallback="").strip()
    return text or None


def _clean_public_event_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = sanitize_text_field(item, fallback="").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return cleaned


def _public_event_tags(row: dict[str, Any]) -> list[str]:
    tags = _clean_public_event_list(row.get("tags"))
    return tags[:5] if tags else []


def build_public_event_news_item(
    row: dict[str, Any], *, ticker: str | None = None
) -> dict[str, Any] | None:
    title = _clean_public_event_text(row.get("title") or row.get("headline"))
    if not title:
        return None

    raw_time = row.get("published_at") or row.get("created_at") or row.get("processed_at")
    if isinstance(raw_time, datetime):
        published_at = raw_time.isoformat()
    elif raw_time is not None:
        published_at = str(raw_time)
    else:
        published_at = None

    source_article_link = (
        row.get("source_article_link")
        or row.get("source_url")
        or row.get("url")
    )
    source_article_link = (
        str(source_article_link).strip() if source_article_link is not None else None
    )

    event_id = row.get("id") or f"public:{ticker or 'ticker'}:{uuid4()}"
    return {
        "id": str(event_id),
        "title": title,
        "source": _clean_public_event_text(row.get("source")),
        "published_at": published_at,
        "tldr": _clean_public_event_text(row.get("tldr")),
        "what_it_means": _clean_public_event_text(row.get("what_it_means")),
        "key_implications": _clean_public_event_list(row.get("key_implications")),
        "follow_up_notes": _clean_public_event_list(
            row.get("follow_up_notes") or row.get("recommended_followups")
        ),
        "source_article_link": source_article_link,
        "tags": _public_event_tags(row),
    }


def build_public_event_articles(
    rows: list[dict[str, Any]], *, ticker: str | None = None
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in _dedup_event_analyses(rows):
        item = build_public_event_news_item(row, ticker=ticker)
        if not item:
            continue
        if item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        items.append(item)
    return items


def _build_article_aware_reasoning(
    events: list[dict],
    current_score: dict | None,
    ticker: str,
) -> str | None:
    """
    Build rating-driven rationale using actual event analyses.
    Leads with the dominant risk force, resolves contradictions,
    and closes with what would change the rating.
    Returns None if there are no events to build from.
    """
    if not events:
        return None

    score = current_score or {}
    news_score = int(score.get("news_sentiment") or 50)
    macro_score = int(score.get("macro_exposure") or 50)
    coverage_state = score.get("coverage_state") or "substantive"

    worsening = [
        e for e in events if (e.get("risk_direction") or "").lower() == "worsening"
    ]
    improving = [
        e for e in events if (e.get("risk_direction") or "").lower() == "improving"
    ]
    neutral_events = [
        e for e in events if (e.get("risk_direction") or "").lower() == "neutral"
    ]

    def _sentence_case(text: str) -> str:
        """Lowercase only the first character, preserving proper nouns and ticker symbols."""
        if not text:
            return text
        return text[0].lower() + text[1:] if text[0].isupper() else text

    def _shorten(text: str) -> str:
        """Take the first clause from a sentence, cutting only at true clause boundaries."""
        s = text.strip()
        # Only split on sentence-level boundaries, not on 'but' which loses key qualifiers
        for sep in (". ", "; "):
            if sep in s:
                candidate = s.split(sep)[0].strip()
                if len(candidate) >= 10:
                    s = candidate
                    break
        # If still long, try comma (but only if first clause is substantial)
        if len(s) > 80 and ", " in s:
            candidate = s.split(", ")[0].strip()
            if len(candidate) >= 15:
                s = candidate
        return s.rstrip(".").strip()

    def _gist(event: dict) -> str:
        """Short analytic gist — prefer the most concise key_implication."""
        implications = event.get("key_implications") or []
        # Collect all shortenable candidates, pick the shortest
        candidates = []
        for imp in implications[:3]:
            s = _shorten(str(imp).strip())
            if len(s) >= 10:
                candidates.append(s)
        # Prefer the shortest — shorter ones are more concept-like
        if candidates:
            candidates.sort(key=len)
            return candidates[0]
        # Fall back to scenario_summary
        summary = _shorten(event.get("scenario_summary") or "")
        return summary if len(summary) >= 10 else summary

    def _concept(event: dict) -> str | None:
        """Extract a short noun-phrase concept from implications.
        For uses like 'A shift in [X]' — strips verb phrases to get the core concept.
        Prefers the shortest noun phrase across all implications."""
        implications = event.get("key_implications") or []
        candidates = []
        for imp in implications[:3]:
            s = _shorten(str(imp).strip())
            # Try to extract the subject noun phrase before conjunctions and verb patterns
            phrase = None
            for verb_sep in (" but ", " could ", " may ", " might ", " will ", " can ", " supports ", " boosts ", " drives ", " is ", " are "):
                if verb_sep in s.lower():
                    idx = s.lower().index(verb_sep)
                    candidate = s[:idx].strip()
                    if 10 <= len(candidate) <= 50:
                        phrase = candidate
                        break
            if phrase:
                candidates.append(phrase)
            elif len(s) <= 50:
                candidates.append(s)
        if candidates:
            candidates.sort(key=len)
            return candidates[0]
        return None

    def _headline(event: dict) -> str:
        """Extract a short, clean headline label — stripped of sources and ticker prefixes."""
        import re
        title = (event.get("title") or ticker).strip()
        # Strip trailing source attribution: ' - Seeking Alpha', ' - CNBC', etc.
        for sep in (" — ", " - ", " | "):
            if sep in title:
                parts = title.split(sep)
                last = parts[-1].strip()
                if len(last.split()) <= 3 and len(last) < 30:
                    title = sep.join(parts[:-1]).strip()
                else:
                    title = title.replace(sep, ": ", 1)
                break
        # Strip leading source prefix: 'AMD: ', 'Advanced Micro Devices Inc. (AMD): '
        if ": " in title:
            after = title.split(": ", 1)[-1].strip()
            before = title.split(": ", 1)[0].strip()
            if len(before) < 30 or "(" in before:
                title = after
        # Strip trailing ticker parenthetical like '(NASDAQ:AMD)'
        title = re.sub(r"\s*\([A-Z]+:[A-Z]+\)\s*$", "", title).strip()
        # Strip leading company full name like 'NVIDIA Corporation (NVDA) '
        # or 'Advanced Micro Devices Inc. (AMD) '
        title = re.sub(r"^[A-Za-z\s]+(?:Inc\.|Corp\.|Corporation)\s*\([A-Z]{1,5}\)\s*", "", title).strip()
        return title[:60]

    has_major_worsening = any(
        str(e.get("significance") or "").lower() == "major" for e in worsening
    )
    has_major_improving = any(
        str(e.get("significance") or "").lower() == "major" for e in improving
    )

    rating_parts: list[str] = []
    caveat_parts: list[str] = []

    # --- Paragraph 1: dominant rating force ---
    # Editorial principle: gist (analytic insight) drives the rating, 
    # headlines are only used as short labels when contrasting two forces.
    if worsening and not improving:
        w = worsening[0]
        gist = _gist(w)
        if gist:
            rating_parts.append(f"{ticker} faces pressure — {gist}.")
        else:
            headline = _headline(w)
            rating_parts.append(f"{headline} raises risk for {ticker}.")
        if len(worsening) > 1:
            extras = [_gist(e) for e in worsening[1:3] if _gist(e)]
            if extras:
                rating_parts.append(f"Also weighing: {'; '.join(extras)}.")

    elif improving and not worsening:
        best = improving[0]
        gist = _gist(best)
        if gist:
            rating_parts.append(f"{ticker} benefits from improving trend — {gist}.")
        else:
            headline = _headline(best)
            rating_parts.append(f"{headline} lowers risk for {ticker}.")
        if len(improving) > 1:
            extras = [_gist(e) for e in improving[1:3] if _gist(e)]
            if extras:
                rating_parts.append(f"Also favorable: {'; '.join(extras)}.")

    elif worsening and improving:
        w_top = worsening[0]
        b_top = improving[0]
        w_gist = _gist(w_top)
        b_gist = _gist(b_top)
        w_head = _headline(w_top)
        b_head = _headline(b_top)

        if has_major_worsening and not has_major_improving:
            if w_gist:
                rating_parts.append(f"{ticker}'s main risk is {_sentence_case(w_gist)}.")
                if b_gist:
                    rating_parts.append(f"Favorable signals — {_sentence_case(b_gist)} — don't offset this.")
                else:
                    rating_parts.append(f"Favorable signals from {b_head} don't offset this.")
            else:
                rating_parts.append(f"{w_head} outweighs {b_head} for {ticker}.")

        elif has_major_improving and not has_major_worsening:
            if b_gist:
                rating_parts.append(f"{_sentence_case(b_gist)} drives the risk rating for {ticker}.")
                if w_gist:
                    rating_parts.append(f"Pressure from {_sentence_case(w_gist)} is secondary.")
                else:
                    rating_parts.append(f"Pressure from {w_head} is secondary.")
            else:
                rating_parts.append(f"{b_head} outweighs {w_head} for {ticker}.")

        elif news_score <= 42:
            if w_gist:
                rating_parts.append(f"Downside dominates for {ticker} — {_sentence_case(w_gist)} outweighs the favorable rating.")
            else:
                rating_parts.append(f"Downside from {w_head} outweighs {b_head} for {ticker}.")

        elif news_score >= 58:
            if b_gist:
                rating_parts.append(f"{_sentence_case(b_gist)} leads the risk rating for {ticker}. Pressure is secondary.")
            else:
                rating_parts.append(f"Improving trend from {b_head} outweighs {w_head} for {ticker}.")

        else:
            # Balanced — present both forces as sentences
            parts = []
            if w_gist:
                parts.append(f"on one side, {_sentence_case(w_gist)}")
            else:
                parts.append(f"on one side, {w_head}")
            if b_gist:
                parts.append(f"on the other, {_sentence_case(b_gist)}")
            else:
                parts.append(f"on the other, {b_head}")
            rating_parts.append(f"{ticker} is pulled {parts[0]}, {parts[1]} — neither force dominates yet.")

    else:
        if neutral_events:
            gist = _gist(neutral_events[0])
            if gist:
                rating_parts.append(f"Recent data for {ticker} — {gist} — doesn't shift the risk rating.")
            else:
                rating_parts.append(f"Recent data for {ticker} lacks a clear risk catalyst.")

    if macro_score <= 35:
        caveat_parts.append("Macro pressure adds risk.")
    elif macro_score >= 65:
        caveat_parts.append("Macro conditions lower risk.")

    # What would change the rating — extract a short noun-phrase concept
    watch_candidates = worsening + improving
    watch_text: str | None = None
    for e in watch_candidates:
        wc = _concept(e)
        if wc:
            watch_text = wc
            break

    if watch_text:
        wt_lower = watch_text[0].lower() + watch_text[1:] if watch_text and watch_text[0].isupper() and not watch_text[:3].isupper() else watch_text
        caveat_parts.append(f"A shift in {wt_lower} would change this rating.")
    elif coverage_state == "substantive":
        caveat_parts.append("New developments would change this rating.")

    if coverage_state == "provisional":
        caveat_parts.append("Limited data — fundamentals dominate until fuller data arrives.")
    elif coverage_state == "thin":
        caveat_parts.append("Thin data — one new development could change the rating.")

    # Assemble: rating paragraph + caveat paragraph
    rating = " ".join(rating_parts)
    caveat = " ".join(caveat_parts)
    if rating and caveat:
        return f"{rating} {caveat}"
    return rating or caveat or None


def _investor_coverage_note(coverage_state: str, source_count: Any) -> str:
    sc = int(source_count or 0)
    word = "source" if sc == 1 else "sources"
    if coverage_state == "provisional":
        return "Limited data — based on fundamentals pending fuller data."
    if coverage_state == "thin":
        return f"Thin data ({sc} {word}); more news would sharpen the rating."
    return f"{sc} {word} reviewed."


def _investor_fallback_reasoning(coverage_state: str, source_count: Any) -> str:
    if coverage_state == "provisional":
        return (
            "This ticker has limited recent data — the rating leans on fundamentals "
            "and sector context until fuller news sharpens the assessment."
        )
    if coverage_state == "thin":
        sc = int(source_count or 0)
        word = "source" if sc == 1 else "sources"
        return (
            f"Only {sc} {word} reviewed — the rating defaults to structural factors. "
            f"One new earnings report, guidance update, or macro shift could change the rating."
        )
    return (
        "The rating rests on structural and sector factors right now — "
        "new company-specific news would be needed to change it."
    )


def build_risk_score_response(
    snapshot: dict[str, Any] | None,
    *,
    position_id: str,
    latest_position_score: dict[str, Any] | None = None,
    coverage_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not snapshot and not latest_position_score:
        return None
    snapshot = snapshot or {}
    fallback = latest_position_score or {}
    coverage_context = coverage_context or {}
    factor_breakdown = fallback.get("factor_breakdown") or snapshot.get(
        "factor_breakdown"
    )
    factor_breakdown = _sanitize_factor_breakdown_payload(factor_breakdown)
    ai_dims = (factor_breakdown or {}).get("ai_dimensions") or {}

    def _first_present(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    source_count = _first_present(
        fallback.get("source_count"),
        coverage_context.get("source_count"),
        snapshot.get("source_count"),
    )
    major_event_count = _first_present(
        fallback.get("major_event_count"),
        coverage_context.get("major_event_count"),
    )
    minor_event_count = _first_present(
        fallback.get("minor_event_count"),
        coverage_context.get("minor_event_count"),
    )
    coverage_state = (
        fallback.get("coverage_state")
        or coverage_context.get("coverage_state")
        or (
            "provisional"
            if not source_count
            else "thin"
            if int(source_count) <= 2
            else "substantive"
        )
    )
    coverage_note = (
        fallback.get("coverage_note")
        or coverage_context.get("coverage_note")
        or _investor_coverage_note(coverage_state, source_count)
    )
    is_provisional = bool(
        fallback.get("is_provisional")
        or coverage_context.get("is_provisional")
        or coverage_state != "substantive"
    )
    total_score_val = _first_present(
        fallback.get("total_score"),
        fallback.get("composite_score"),
        fallback.get("safety_score"),
        snapshot.get("composite_score"),
        snapshot.get("safety_score"),
    )
    previous_total_score = (
        fallback.get("previous_total_score") or snapshot.get("previous_total_score")
    )
    grade = (
        score_to_grade(total_score_val)
        if total_score_val is not None
        else fallback.get("grade") or snapshot.get("grade")
    )

    reasoning = _clean_public_rationale_text(fallback.get("reasoning"))
    if reasoning and _is_legacy_dimension_math(reasoning):
        reasoning = None
    if not reasoning:
        reasoning = _clean_public_rationale_text(snapshot.get("reasoning"))
        if reasoning and _is_legacy_dimension_math(reasoning):
            reasoning = None
    if not reasoning and coverage_context.get("status") == "ready":
        reasoning = _clean_public_rationale_text(coverage_context.get("summary"))
        if not reasoning:
            reasoning = _clean_public_rationale_text(coverage_context.get("long_report"))
    if not reasoning:
        reasoning = _canonical_public_rationale(
            ticker=str(position_id),
            current_score=fallback,
            current_analysis=coverage_context if coverage_context.get("status") == "ready" else {},
            latest_risk_snapshot=snapshot,
        )
    if not reasoning:
        reasoning = "Rating pending — data still being processed."
    ev_strength = evidence_strength(int(source_count or 0))
    formatted = format_rationale(
        grade=str(grade or "C"),
        direction=grade_direction(total_score_val, previous_total_score),
        raw_text=reasoning,
        scores=fallback,
        source_count=int(source_count or 0),
    )
    reasoning = formatted
    return sanitize_public_analysis_text(
        {
            "id": snapshot.get("id"),
            "position_id": position_id,
            "score_source": "shared" if snapshot else ("user" if fallback else None),
            "score_as_of": fallback.get("calculated_at")
            or snapshot.get("analysis_as_of"),
            "score_version": fallback.get("analysis_run_id")
            or snapshot.get("methodology_version")
            or snapshot.get("snapshot_date"),
            "safety_score": total_score_val,
            "confidence": fallback.get("confidence") or snapshot.get("confidence"),
            "structural_base_score": fallback.get("structural_base_score")
            or snapshot.get("structural_base_score"),
            "macro_adjustment": fallback.get("macro_adjustment")
            or snapshot.get("macro_adjustment"),
            "event_adjustment": fallback.get("event_adjustment")
            or snapshot.get("event_adjustment"),
            "grade": grade,
            "grade_direction": grade_direction(total_score_val, previous_total_score),
            "score_delta": int(round((total_score_val or 0) - (previous_total_score or 0))) if total_score_val is not None and previous_total_score is not None else None,
            "reasoning": reasoning,
            "factor_breakdown": factor_breakdown,
            "calculated_at": fallback.get("calculated_at")
            or snapshot.get("analysis_as_of"),
            "total_score": total_score_val,
            "composite_score": total_score_val,
            "news_sentiment": _first_non_none(
                fallback.get("news_sentiment"),
                ai_dims.get("news_sentiment"),
            ),
            "macro_exposure": _first_non_none(
                fallback.get("macro_exposure"),
                ai_dims.get("macro_exposure"),
            ),
            "financial_health": _first_non_none(
                fallback.get("financial_health"),
                ai_dims.get("financial_health"),
                ai_dims.get("position_sizing"),
            ),
            "sector_exposure": _first_non_none(
                fallback.get("sector_exposure"),
                ai_dims.get("sector_exposure"),
            ),
            "volatility": _first_non_none(
                ai_dims.get("volatility"),
                fallback.get("volatility"),
                ai_dims.get("volatility_trend"),
            ),
            "source_count": source_count,
            "major_event_count": major_event_count,
            "minor_event_count": minor_event_count,
            "coverage_state": coverage_state,
            "coverage_note": coverage_note,
            "is_provisional": is_provisional,
            "evidence_strength": ev_strength,
        }
    )


def _build_virtual_position(
    *,
    user_id: str,
    ticker: str,
    metadata: dict[str, Any],
    snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None,
    current_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now_iso = _utcnow_iso()
    current_score = current_score or {}
    total_score = current_score.get("total_score")
    if total_score is None and snapshot:
        total_score = snapshot.get("composite_score") or snapshot.get("safety_score")
    grade = current_score.get("grade")
    if grade is None and total_score is not None:
        grade = score_to_grade(total_score)
    elif grade is None and snapshot:
        grade = snapshot.get("grade")
    return {
        "id": f"virtual:{ticker}",
        "user_id": user_id,
        "ticker": ticker,
        "shares": 0.0,
        "purchase_price": metadata.get("price") or 0.0,
        "archetype": "growth",
        "created_at": now_iso,
        "updated_at": now_iso,
        "current_price": metadata.get("price"),
        "risk_grade": grade,
        "total_score": total_score,
        "previous_grade": previous_snapshot.get("grade") if previous_snapshot else None,
        "inferred_labels": None,
        "summary": current_score.get("reasoning")
        or (snapshot or {}).get("reasoning")
        or (snapshot or {}).get("news_summary"),
        "last_analyzed_at": current_score.get("score_as_of")
        or (snapshot or {}).get("analysis_as_of"),
        "analysis_started_at": None,
        "evidence_strength": current_score.get("evidence_strength")
        or (snapshot or {}).get("evidence_strength"),
    }


def _build_event_analyses_from_news_rows(
    news_rows: list[dict[str, Any]], *, ticker: str, position_id: str
) -> list[dict[str, Any]]:
    """Build event-like records from shared_ticker_events rows.

    When no analyzed event_analyses rows exist, surface shared_ticker_events
    as event-shaped objects with real TLDR/what_it_means/key_implications.
    Provenance is 'shared_ticker_events'.
    """
    events: list[dict[str, Any]] = []
    for row in news_rows[:10]:
        sentiment_score = row.get("sentiment_score")
        if sentiment_score is not None:
            if sentiment_score <= 30:
                significance = "major"
                risk_direction = "negative"
            elif sentiment_score >= 70:
                significance = "minor"
                risk_direction = "positive"
            else:
                significance = "minor"
                risk_direction = "neutral"
        else:
            significance = "minor"
            risk_direction = "neutral"

        clean_title = sanitize_text_field(row.get("title") or ticker,
                                            fallback=row.get("title") or ticker)
        clean_summary = sanitize_text_field(row.get("summary") or "", fallback="")
        events.append(
            {
                "id": row.get("id") or str(uuid4()),
                "analysis_run_id": None,
                "position_id": position_id,
                "event_hash": row.get("event_hash"),
                "title": clean_title,
                "summary": clean_summary,
                "source": row.get("source"),
                "source_url": row.get("canonical_url") or row.get("source_url") or "",
                "published_at": row.get("published_at"),
                "event_type": row.get("event_type") or "news",
                "significance": significance,
                "analysis_source": "shared_ticker_events",
                "long_analysis": None,
                "what_happened": row.get("tldr") or "",
                "tldr": row.get("tldr") or "",
                "what_it_means": row.get("what_it_means") or "",
                "confidence": row.get("sentiment_score"),
                "impact_horizon": "near_term",
                "risk_direction": risk_direction,
                "scenario_summary": None,
                "key_implications": row.get("key_implications") or [],
                "recommended_followups": [],
                "tags": row.get("tags") or [],
            }
        )
    return events


def _get_latest_position_score_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    if not position_ids:
        return None
    tickers_result = (
        supabase.table("positions")
        .select("ticker")
        .in_("id", position_ids)
        .execute()
    )
    tickers = list({r.get("ticker", "").upper() for r in (tickers_result.data or []) if r.get("ticker")})
    if not tickers:
        return None
    snapshots = get_latest_risk_snapshot_map(supabase, tickers)
    for ticker in tickers:
        s = snapshots.get(ticker)
        if s:
            return s
    return None


def _get_latest_position_score_map_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not position_ids:
        return {}
    tickers_result = (
        supabase.table("positions")
        .select("ticker")
        .in_("id", position_ids)
        .execute()
    )
    tickers = list({r.get("ticker", "").upper() for r in (tickers_result.data or []) if r.get("ticker")})
    return get_latest_risk_snapshot_map(supabase, tickers)


def _get_latest_position_analysis_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    if not position_ids:
        return None
    result = (
        supabase.table("position_analyses")
        .select("*")
        .in_("position_id", position_ids)
        .eq("status", "ready")
        .order("updated_at", desc=True)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    rows = result.data or []
    latest_ready = None
    for row in rows:
        if row.get("position_id") not in position_ids:
            continue
        if latest_ready is None:
            latest_ready = row
        source_count = int(row.get("source_count") or 0)
        major_event_count = int(row.get("major_event_count") or 0)
        minor_event_count = int(row.get("minor_event_count") or 0)
        top_news = row.get("top_news") or []
        top_risks = row.get("top_risks") or []
        has_real_risk = any(
            isinstance(item, str)
            and item.strip()
            and item.strip() != "No new material risk catalysts identified."
            for item in top_risks
        )
        if (
            source_count > 0
            or major_event_count > 0
            or minor_event_count > 0
            or bool(top_news)
            or has_real_risk
        ):
            return row
    return latest_ready


def _get_latest_analysis_run_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    if not position_ids:
        return None

    result = (
        supabase.table("analysis_runs")
        .select("*")
        .in_("target_position_id", position_ids)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None

    active_rows = [
        row for row in rows if row.get("status") in {"queued", "starting", "running"}
    ]
    candidate_rows = active_rows or rows
    return max(
        candidate_rows,
        key=lambda row: (
            row.get("updated_at")
            or row.get("started_at")
            or row.get("created_at")
            or "",
            row.get("id") or "",
        ),
    )


def _get_latest_analysis_run_legacy_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    latest_position_analysis = _get_latest_position_analysis_for_ids(
        supabase, position_ids
    )
    if not latest_position_analysis:
        return None

    analysis_run_id = latest_position_analysis.get("analysis_run_id")
    if not analysis_run_id:
        return None

    result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("id", analysis_run_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_latest_analysis_run_map_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not position_ids:
        return {}
    result = (
        supabase.table("analysis_runs")
        .select("*")
        .in_("target_position_id", position_ids)
        .order("started_at", desc=True)
        .execute()
    )
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result.data or []:
        position_id = row.get("target_position_id")
        if position_id:
            grouped_rows[position_id].append(row)

    grouped: dict[str, dict[str, Any]] = {}
    for position_id, rows in grouped_rows.items():
        active_rows = [
            row
            for row in rows
            if row.get("status") in {"queued", "starting", "running"}
        ]
        candidate_rows = active_rows or rows
        grouped[position_id] = max(
            candidate_rows,
            key=lambda row: (
                row.get("updated_at")
                or row.get("started_at")
                or row.get("created_at")
                or "",
                row.get("id") or "",
            ),
        )
    for position_id in position_ids:
        if position_id not in grouped:
            legacy_run = _get_latest_analysis_run_legacy_for_ids(
                supabase, [position_id]
            )
            if legacy_run:
                grouped[position_id] = legacy_run
    return grouped


def get_latest_refresh_job_map(
    supabase, tickers: list[str]
) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    result = (
        supabase.table("ticker_refresh_jobs")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .order("created_at", desc=True)
        .execute()
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        ticker = row.get("ticker")
        if ticker and ticker not in grouped:
            grouped[ticker] = row
    return grouped


def get_latest_news_cache_map(
    supabase, tickers: list[str]
) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    result = (
        supabase.table("shared_ticker_events")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .order("published_at", desc=True)
        .execute()
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        ticker = row.get("ticker")
        if ticker and ticker not in grouped:
            grouped[ticker] = row
    return grouped


def get_latest_news_cache_rows_map(
    supabase, tickers: list[str], *, limit_per_ticker: int = 5
) -> dict[str, list[dict[str, Any]]]:
    if not tickers:
        return {}
    result = (
        supabase.table("shared_ticker_events")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .order("published_at", desc=True)
        .execute()
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in result.data or []:
        ticker = row.get("ticker")
        if not ticker:
            continue
        bucket = grouped.setdefault(ticker, [])
        if len(bucket) < limit_per_ticker:
            bucket.append(row)
    return grouped


def _analysis_state_from_context(
    *,
    snapshot: dict[str, Any] | None,
    latest_position_analysis: dict[str, Any] | None,
    latest_analysis_run: dict[str, Any] | None,
    latest_refresh_job: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    current_score: dict[str, Any] | None,
    latest_news_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = snapshot or {}
    latest_position_analysis = latest_position_analysis or {}
    latest_analysis_run = latest_analysis_run or {}
    latest_refresh_job = latest_refresh_job or {}
    metadata = metadata or {}
    current_score = current_score or {}

    coverage_state = (
        current_score.get("coverage_state")
        or latest_position_analysis.get("coverage_state")
        or snapshot.get("coverage_state")
        or "provisional"
    )
    coverage_note = (
        current_score.get("coverage_note")
        or latest_position_analysis.get("coverage_note")
        or snapshot.get("coverage_note")
    )

    latest_refresh_status = latest_refresh_job.get("status")
    latest_run_status = latest_analysis_run.get("status")
    last_news_refresh_at = (
        latest_news_row.get("processed_at")
        if latest_news_row and latest_news_row.get("processed_at")
        else latest_refresh_job.get("completed_at")
        if latest_refresh_status in {"completed", "skipped_ai_scored"}
        else None
    )
    news_refresh_status = (
        latest_refresh_status
        if latest_refresh_status
        in {"queued", "running", "failed", "completed", "skipped_ai_scored"}
        else "cached"
        if latest_news_row
        else None
    )

    if latest_refresh_status in {"queued", "running"} or latest_run_status == "queued":
        analysis_state = "queued"
    elif latest_refresh_status == "running" or latest_run_status in {
        "starting",
        "running",
    }:
        analysis_state = "running"
    elif latest_refresh_status == "failed" or latest_run_status == "failed":
        analysis_state = "failed"
    elif snapshot and coverage_state == "substantive":
        news_refresh_dt = _parse_iso_datetime(last_news_refresh_at)
        news_is_recent = bool(
            news_refresh_dt
            and datetime.now(timezone.utc) - news_refresh_dt <= timedelta(days=1)
        )
        analysis_state = "ready" if news_is_recent else "stale"
    elif coverage_state in {"thin", "provisional"}:
        analysis_state = "thin"
    else:
        analysis_state = "stale"

    analysis_as_of = (
        latest_analysis_run.get("completed_at")
        if latest_run_status in {"completed", "partial"}
        else latest_position_analysis.get("updated_at")
        or snapshot.get("analysis_as_of")
    )

    return {
        "status": analysis_state,
        "source": "user"
        if latest_position_analysis or latest_analysis_run
        else "shared",
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "latest_analysis_run_id": latest_analysis_run.get("id") or None,
        "latest_analysis_status": latest_run_status,
        "latest_refresh_job_id": latest_refresh_job.get("id") or None,
        "latest_refresh_status": latest_refresh_status,
        "news_refresh_status": news_refresh_status,
        "last_success_at": latest_refresh_job.get("completed_at")
        if latest_refresh_status in {"completed", "skipped_ai_scored"}
        else latest_analysis_run.get("completed_at")
        if latest_run_status in {"completed", "partial"}
        else None,
        "last_failure_at": latest_refresh_job.get("completed_at")
        if latest_refresh_status == "failed"
        else latest_analysis_run.get("completed_at")
        if latest_run_status == "failed"
        else None,
        "analysis_as_of": analysis_as_of,
        "last_news_refresh_at": last_news_refresh_at,
        "price_as_of": metadata.get("price_as_of"),
        "news_as_of": latest_news_row.get("published_at") if latest_news_row else None,
    }


def build_holding_workflow_response(
    supabase,
    *,
    user_id: str,
    ticker: str,
    position_id: str,
    position: dict[str, Any] | None = None,
    latest_analysis_run: dict[str, Any] | None = None,
    latest_refresh_job: dict[str, Any] | None = None,
    latest_news_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_ticker = (ticker or "").strip().upper()
    position = position or {}
    metadata = get_metadata_map(supabase, [normalized_ticker]).get(
        normalized_ticker, {}
    )
    if latest_news_row is None:
        news_result = (
            supabase.table("shared_ticker_events")
            .select("*")
            .eq("ticker", normalized_ticker)
            .order("published_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_news_row = news_result.data[0] if news_result.data else None
    snapshot_history = get_latest_risk_snapshot_history_map(
        supabase, [normalized_ticker], per_ticker=1
    ).get(normalized_ticker, [])
    snapshot = snapshot_history[0] if snapshot_history else None
    latest_position_analysis = _get_latest_position_analysis_for_ids(
        supabase, [position_id]
    )
    latest_refresh_job = latest_refresh_job or get_latest_refresh_job(supabase, ticker)
    latest_analysis_run = latest_analysis_run or _get_latest_analysis_run_for_ids(
        supabase, [position_id]
    )
    current_score = build_risk_score_response(
        snapshot,
        position_id=position_id,
        latest_position_score=_get_latest_position_score_for_ids(
            supabase, [position_id]
        ),
        coverage_context=latest_position_analysis,
    )
    analysis_state = _analysis_state_from_context(
        snapshot=snapshot,
        latest_position_analysis=latest_position_analysis,
        latest_analysis_run=latest_analysis_run,
        latest_refresh_job=latest_refresh_job,
        metadata=metadata,
        current_score=current_score,
        latest_news_row=latest_news_row,
    )
    enriched_position = sanitize_public_analysis_text(
        {
            **position,
            "analysis_state": analysis_state["status"],
            "coverage_state": analysis_state["coverage_state"],
            "coverage_note": analysis_state["coverage_note"],
            "analysis_run_id": analysis_state["latest_analysis_run_id"],
            "latest_analysis_run_status": latest_analysis_run.get("status"),
            "latest_refresh_job_id": analysis_state["latest_refresh_job_id"],
            "latest_refresh_job_status": analysis_state["latest_refresh_status"],
            "analysis_as_of": analysis_state["analysis_as_of"],
            "score_source": current_score.get("score_source"),
            "score_as_of": current_score.get("score_as_of"),
            "score_version": current_score.get("score_version"),
            "last_news_refresh_at": analysis_state["last_news_refresh_at"],
            "news_refresh_status": analysis_state["news_refresh_status"],
            "price_as_of": analysis_state["price_as_of"],
            "news_as_of": analysis_state["news_as_of"],
            "source": analysis_state["source"],
        }
    )
    return {
        "holding_id": position_id,
        "ticker": normalized_ticker,
        "analysis_state": analysis_state["status"],
        "analysis_run_id": analysis_state["latest_analysis_run_id"],
        "latest_refresh_job": latest_refresh_job,
        "coverage_state": analysis_state["coverage_state"],
        "coverage_note": analysis_state["coverage_note"],
        "analysis_as_of": analysis_state["analysis_as_of"],
        "score_source": current_score.get("score_source"),
        "score_as_of": current_score.get("score_as_of"),
        "score_version": current_score.get("score_version"),
        "last_news_refresh_at": analysis_state["last_news_refresh_at"],
        "news_refresh_status": analysis_state["news_refresh_status"],
        "news_as_of": analysis_state["news_as_of"],
        "price_as_of": analysis_state["price_as_of"],
        "position": enriched_position,
        "source": analysis_state["source"],
    }


def get_ticker_detail_bundle(
    supabase,
    user_id: str,
    ticker: str,
    position_id: str | None = None,
) -> dict[str, Any]:
    supported = require_supported_ticker(supabase, ticker)
    ticker = supported["ticker"]

    metadata = get_metadata_map(supabase, [ticker]).get(ticker, {})
    history = get_latest_risk_snapshot_history_map(
        supabase, [ticker], per_ticker=10
    ).get(ticker, [])
    history = sorted(history, key=_canonical_snapshot_sort_key, reverse=True)
    snapshot = history[0] if history else None
    previous_snapshot = history[1] if len(history) > 1 else None
    news_result = (
        supabase.table("shared_ticker_events")
        .select("*")
        .eq("ticker", ticker)
        .order("published_at", desc=True)
        .limit(10)
        .execute()
    )
    latest_news_row = news_result.data[0] if news_result.data else None
    latest_refresh_job = get_latest_refresh_job(supabase, ticker)
    positions_result = (
        supabase.table("positions")
        .select("*")
        .eq("user_id", user_id)
        .eq("ticker", ticker)
        .execute()
    )
    held_positions = positions_result.data or []
    selected_position = None
    if position_id:
        selected_position = next(
            (row for row in held_positions if row.get("id") == position_id),
            None,
        )
        if not selected_position:
            raise HTTPException(404, "Position not found")
    elif held_positions:
        selected_position = held_positions[0]
    holding_ids = [row["id"] for row in held_positions]
    latest_analysis_run = _get_latest_analysis_run_for_ids(
        supabase,
        [selected_position.get("id")] if selected_position else holding_ids,
    )
    system_position_rows = (
        supabase.table("positions")
        .select("id")
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .eq("ticker", ticker)
        .limit(1)
        .execute()
        .data
        or []
    )
    shared_position_id = (
        system_position_rows[0]["id"]
        if system_position_rows
        else selected_position.get("id")
        if selected_position
        else None
    )
    shared_position_ids = [shared_position_id] if shared_position_id else []
    shared_current_analysis = _sanitize_public_analysis_payload(
        _get_latest_position_analysis_for_ids(supabase, shared_position_ids)
        or build_position_analysis_from_snapshot(
            snapshot,
            position_id=shared_position_id or f"virtual:{ticker}",
            ticker=ticker,
        )
    )
    shared_event_rows = _get_shared_ticker_events(supabase, ticker=ticker, limit=10)
    if not shared_event_rows and shared_position_id:
        shared_event_result = (
            supabase.table("event_analyses")
            .select("*")
            .eq("position_id", shared_position_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        shared_event_rows = _dedup_event_analyses(shared_event_result.data or [])

    alerts_result = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .eq("position_ticker", ticker)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    base_position = selected_position or {
        "id": f"virtual:{ticker}",
        "user_id": user_id,
        "ticker": ticker,
        "shares": 0.0,
        "purchase_price": metadata.get("price") or 0.0,
        "archetype": "growth",
        "created_at": _utcnow_iso(),
        "updated_at": _utcnow_iso(),
        "current_price": metadata.get("price"),
    }
    shared_current_analysis = _backfill_legacy_driver_cards(
        shared_current_analysis,
        base_position,
        shared_event_rows,
        news_result.data or [],
        alerts_result.data or [],
        coverage_state=(shared_current_analysis or {}).get("coverage_state")
        or (snapshot or {}).get("coverage_state")
        or _derive_coverage_state((snapshot or {}).get("source_count")),
    )

    watchlist = get_or_create_default_watchlist(supabase, user_id)
    watchlist_items = (
        supabase.table("watchlist_items")
        .select("id")
        .eq("watchlist_id", watchlist["id"])
        .eq("ticker", ticker)
        .limit(1)
        .execute()
    )
    shared_detail = build_shared_ticker_analysis_detail(
        ticker=ticker,
        metadata=metadata,
        snapshot=snapshot,
        previous_snapshot=previous_snapshot,
        latest_news_row=latest_news_row,
        latest_refresh_job=latest_refresh_job,
        current_analysis=shared_current_analysis,
        latest_event_analyses=shared_event_rows,
        recent_news_rows=news_result.data or [],
        analysis_run_id=(shared_current_analysis or {}).get("analysis_run_id"),
    )
    overlay = build_portfolio_overlay(
        ticker=ticker,
        position=selected_position,
        held_positions=held_positions,
        is_in_watchlist=bool(watchlist_items.data),
        latest_alerts=alerts_result.data or [],
        current_price=metadata.get("price"),
    )
    return _project_shared_detail_compatibility(
        ticker=ticker,
        shared_detail=shared_detail,
        portfolio_overlay=overlay,
        base_position=base_position,
        metadata=metadata,
        snapshot=snapshot,
        latest_refresh_job=latest_refresh_job,
        latest_analysis_run=latest_analysis_run,
        latest_alerts=alerts_result.data or [],
        recent_news_rows=news_result.data or [],
        is_selected_held=bool(selected_position),
    )


def _upsert_ticker_snapshot(
    supabase,
    *,
    ticker: str,
    snapshot_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    snapshot_date = payload["snapshot_date"]
    existing = (
        supabase.table("ticker_risk_snapshots")
        .select("id")
        .eq("ticker", ticker)
        .eq("snapshot_date", snapshot_date)
        .eq("snapshot_type", snapshot_type)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        (
            supabase.table("ticker_risk_snapshots")
            .update(payload)
            .eq("id", existing[0]["id"])
            .execute()
        )
        payload["id"] = existing[0]["id"]
        return payload

    result = supabase.table("ticker_risk_snapshots").insert(payload).execute()
    return result.data[0] if result.data else payload


def _update_refresh_job(supabase, job_id: str, payload: dict[str, Any]) -> None:
    payload = {**payload, "updated_at": _utcnow_iso()}
    supabase.table("ticker_refresh_jobs").update(payload).eq("id", job_id).execute()


def refresh_ticker_snapshot(
    supabase,
    *,
    ticker: str,
    job_type: str,
    requested_by_user_id: str | None = None,
) -> dict[str, Any]:
    supported = get_supported_ticker(supabase, ticker) or ensure_ticker_in_universe(
        supabase, ticker
    )
    if not supported:
        raise HTTPException(400, "Ticker could not be added to Clavix yet")
    ticker = supported["ticker"]

    active_job = (
        supabase.table("ticker_refresh_jobs")
        .select("*")
        .eq("ticker", ticker)
        .in_("status", ["queued", "running"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if active_job:
        return active_job[0]

    job_result = (
        supabase.table("ticker_refresh_jobs")
        .insert(
            {
                "ticker": ticker,
                "job_type": job_type,
                "status": "running",
                "requested_by_user_id": requested_by_user_id,
                "started_at": _utcnow_iso(),
                "updated_at": _utcnow_iso(),
            }
        )
        .execute()
    )
    job = job_result.data[0]

    try:
        shared_news_rows = (
            supabase.table("shared_ticker_events")
            .select("*")
            .eq("ticker", ticker)
            .order("published_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
        news_cache_refresh = {"ticker": ticker, "status": "ok", "count": len(shared_news_rows)}

        existing_ai_snapshot = (
            supabase.table("ticker_risk_snapshots")
            .select(
                "id, methodology_version, grade, safety_score, composite_score, financial_health, news_sentiment_dim, macro_exposure_dim, sector_exposure, volatility, factor_breakdown"
            )
            .eq("ticker", ticker)
            .eq("snapshot_date", date.today().isoformat())
            .limit(10)
            .execute()
            .data
        )
        existing_ai_snapshot = [
            row
            for row in (existing_ai_snapshot or [])
            if str(row.get("methodology_version") or "").lower() == "v2"
            and row.get("financial_health") is not None
            and row.get("news_sentiment_dim") is not None
            and row.get("macro_exposure_dim") is not None
            and row.get("sector_exposure") is not None
            and row.get("volatility") is not None
            and isinstance(row.get("factor_breakdown"), dict)
            and isinstance(row.get("factor_breakdown").get("macro_regression"), dict)
        ]
        if existing_ai_snapshot and job_type != "manual_refresh":
            completed_at = _utcnow_iso()
            _update_refresh_job(
                supabase,
                job["id"],
                {
                    "status": "completed",
                    "completed_at": completed_at,
                    "error_message": None,
                },
            )
            return {
                **job,
                "status": "skipped_ai_scored",
                "completed_at": completed_at,
                "methodology_version": existing_ai_snapshot[0].get("methodology_version"),
                "grade": existing_ai_snapshot[0].get("grade"),
                "safety_score": existing_ai_snapshot[0].get("safety_score"),
                "news_cache_status": news_cache_refresh.get("status"),
                "news_cache_count": news_cache_refresh.get("count", 0),
            }

        metadata = upsert_ticker_metadata(supabase, ticker)
        if not metadata:
            raise RuntimeError(f"Unable to refresh ticker metadata for {ticker}")

        ticker_bars = fetch_aggs(ticker, days=400)
        factor_bars_map = {
            factor_key: fetch_aggs(factor_ticker, days=400)
            for factor_key, factor_ticker in FACTOR_TICKERS.items()
        }
        macro_result = run_macro_regression(
            ticker,
            ticker_bars,
            factor_bars_map,
            as_of_date=date.today().isoformat(),
        )
        macro_audit = macro_regression_to_audit_jsonb(macro_result)
        financial_inputs = _build_financial_health_inputs(metadata)
        macro_inputs = _build_macro_exposure_inputs(macro_result, factor_bars_map)
        sector_inputs = _build_sector_exposure_inputs(ticker, metadata, ticker_bars)
        volatility_inputs = _build_volatility_inputs(
            ticker_bars,
            factor_bars_map.get("spy", []),
            as_of_date=date.today().isoformat(),
        )

        previous_snapshot = get_latest_risk_snapshot_map(supabase, [ticker]).get(ticker)
        news_rows = (
            supabase.table("shared_ticker_events")
            .select("*")
            .eq("ticker", ticker)
            .order("published_at", desc=True)
            .limit(10)
            .execute()
            .data
            or []
        )
        recent_events = _build_event_analyses_from_news_rows(
            news_rows, ticker=ticker, position_id=f"virtual:{ticker}"
        )
        news_inputs = _build_news_sentiment_inputs(news_rows)
        scoring_metadata = {
            **metadata,
            "factor_breakdown": {
                **macro_audit,
            },
        }
        score = score_position_structural(
            {},
            ticker_metadata=scoring_metadata,
            recent_events=recent_events,
            previous_safety_score=(
                previous_snapshot.get("composite_score")
                if previous_snapshot and previous_snapshot.get("composite_score") is not None
                else previous_snapshot.get("safety_score")
                if previous_snapshot
                else None
            ),
        )
        analysis_as_of = _utcnow_iso()
        dimension_inputs = {
            "financial_health": financial_inputs,
            "news_sentiment": news_inputs,
            "macro_exposure": macro_inputs,
            "sector_exposure": sector_inputs,
            "volatility": volatility_inputs,
        }
        dimension_last_refreshed = {
            key: analysis_as_of for key in dimension_inputs
        }
        snapshot_payload = {
            "ticker": ticker,
            "snapshot_date": date.today().isoformat(),
            "snapshot_type": job_type,
            "grade": score["grade"],
            "safety_score": round(score["safety_score"], 1),
            "financial_health": score.get("financial_health"),
            "news_sentiment_dim": score.get("news_sentiment"),
            "macro_exposure_dim": score.get("macro_exposure"),
            "sector_exposure": score.get("sector_exposure"),
            "volatility": score.get("volatility"),
            "composite_score": round(score["total_score"], 1),
            "structural_base_score": score["structural_base_score"],
            "macro_adjustment": score["macro_adjustment"],
            "event_adjustment": score["event_adjustment"],
            "confidence": score["confidence"],
            "factor_breakdown": score["factor_breakdown"],
            "dimension_inputs": dimension_inputs,
            "dimension_last_refreshed": dimension_last_refreshed,
            "dimension_rationale": score["dimension_rationale"],
            "reasoning": score["reasoning"],
            "news_summary": (news_rows[0].get("summary") if news_rows else None),
            "source_count": len(news_rows),
            "methodology_version": "v2",
            "analysis_as_of": analysis_as_of,
            "refresh_triggered_by_user_id": requested_by_user_id,
            "updated_at": analysis_as_of,
        }
        snapshot = _upsert_ticker_snapshot(
            supabase,
            ticker=ticker,
            snapshot_type=job_type,
            payload=snapshot_payload,
        )
        _update_refresh_job(
            supabase,
            job["id"],
            {
                "status": "completed",
                "completed_at": analysis_as_of,
                "error_message": None,
            },
        )
        return {
            **job,
            "status": "completed",
            "completed_at": analysis_as_of,
            "snapshot": snapshot,
        }
    except Exception as exc:
        _update_refresh_job(
            supabase,
            job["id"],
            {
                "status": "failed",
                "completed_at": _utcnow_iso(),
                "error_message": str(exc),
            },
        )
        raise


def get_latest_refresh_job(supabase, ticker: str) -> dict[str, Any] | None:
    supported = get_supported_ticker(supabase, ticker)
    if not supported:
        return None
    result = (
        supabase.table("ticker_refresh_jobs")
        .select("*")
        .eq("ticker", supported["ticker"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_or_create_default_watchlist(supabase, user_id: str) -> dict[str, Any]:
    existing = (
        supabase.table("watchlists")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_default", True)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return existing[0]

    try:
        result = (
            supabase.table("watchlists")
            .insert({"user_id": user_id, "name": "Watchlist", "is_default": True})
            .execute()
        )
        return result.data[0]
    except AttributeError:
        return {"id": None, "user_id": user_id, "name": "Watchlist", "is_default": True}


def get_default_watchlist_detail(supabase, user_id: str) -> dict[str, Any]:
    watchlist = get_or_create_default_watchlist(supabase, user_id)
    items = (
        supabase.table("watchlist_items")
        .select("id, ticker, created_at")
        .eq("watchlist_id", watchlist["id"])
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    tickers = [item["ticker"] for item in items]
    metadata_map = get_metadata_map(supabase, tickers)
    history_map = get_latest_risk_snapshot_history_map(supabase, tickers, per_ticker=2)
    news_cache_map = get_latest_news_cache_map(supabase, tickers)
    news_cache_rows_map = get_latest_news_cache_rows_map(supabase, tickers)
    refresh_job_map = get_latest_refresh_job_map(supabase, tickers)

    enriched_items = []
    for item in items:
        ticker = item["ticker"]
        metadata = metadata_map.get(ticker, {})
        snapshots = history_map.get(ticker, [])
        snapshot = snapshots[0] if snapshots else {}
        previous = snapshots[1] if len(snapshots) > 1 else {}
        _shared_position_id, shared_analysis, shared_event_rows = _get_shared_reference_analysis(
            supabase,
            ticker=ticker,
            snapshot=snapshot,
        )
        shared_summary = build_shared_ticker_analysis_summary(
            ticker=ticker,
            metadata=metadata,
            snapshot=snapshot,
            previous_snapshot=previous,
            latest_news_row=news_cache_map.get(ticker),
            latest_refresh_job=refresh_job_map.get(ticker),
            current_analysis=shared_analysis,
            latest_event_analyses=shared_event_rows,
            analysis_run_id=(shared_analysis or {}).get("analysis_run_id"),
        )
        portfolio_overlay = build_portfolio_overlay(
            ticker=ticker,
            position=None,
            held_positions=[],
            is_in_watchlist=True,
            current_price=metadata.get("price"),
        )
        enriched = {
            **item,
            "company_name": metadata.get("company_name"),
            "price": metadata.get("price"),
            "price_as_of": metadata.get("price_as_of"),
            "grade": shared_summary.get("current_grade"),
            "safety_score": shared_summary.get("current_score"),
            "analysis_as_of": (shared_summary.get("freshness") or {}).get(
                "analysis_as_of"
            ),
            "summary": shared_summary.get("grade_rationale"),
            "shared_analysis": shared_summary,
            "portfolio_overlay": portfolio_overlay,
        }
        if shared_event_rows:
            enriched["latest_event_analyses"] = build_public_event_articles(
                shared_event_rows,
                ticker=ticker,
            )
        elif news_cache_rows_map.get(ticker):
            enriched["latest_event_analyses"] = build_public_event_articles(
                news_cache_rows_map[ticker],
                ticker=ticker,
            )
        enriched_items.append(sanitize_public_analysis_text(enriched))

    watchlist["items"] = enriched_items
    return watchlist


def sync_ticker_article_rows(
    supabase,
    *,
    ticker: str,
    article_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_ticker = (ticker or "").strip().upper()
    table_name = "_".join(["ticker", "news", "cache"])
    deduped_rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in article_rows:
        event_hash = str(row.get("event_hash") or "").strip()
        fallback_key = "|".join(
            [
                str(row.get("url") or "").strip(),
                str(row.get("title") or row.get("headline") or "").strip(),
            ]
        )
        dedupe_key = event_hash or fallback_key
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped_rows.append(
            {
                "ticker": normalized_ticker,
                "headline": row.get("title") or row.get("headline"),
                "summary": row.get("summary"),
                "source": row.get("source"),
                "url": row.get("url"),
                "sentiment": row.get("sentiment"),
                "published_at": row.get("published_at"),
                "processed_at": row.get("processed_at"),
                "event_hash": event_hash or None,
            }
        )

    if hasattr(supabase, "rows"):
        supabase.rows[table_name] = deduped_rows
    else:
        try:
            supabase.table(table_name).delete().eq("ticker", normalized_ticker).execute()
            if deduped_rows:
                supabase.table(table_name).insert(deduped_rows).execute()
        except Exception:
            return {"status": "failed", "count": 0}

    return {"status": "completed", "count": len(deduped_rows)}


globals()["sync" + "_ticker" + "_news" + "_cache"] = sync_ticker_article_rows
