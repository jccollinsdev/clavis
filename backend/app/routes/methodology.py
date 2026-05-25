from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from ..pipeline.structural_scorer import estimate_iv_rank_from_realized_vol
from ..services.personalisation import attach_latest_personalisation
from ..services.supabase import get_supabase
from ..services.ticker_cache_service import _shared_risk_dimensions

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _isoformat_or_none(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if value in {None, ""}:
        return None
    return str(value)


def _latest_sector_medians(supabase, sector: str | None) -> dict[str, dict[str, Any]]:
    if not sector:
        return {}
    rows = (
        supabase.table("sector_medians")
        .select("sector,metric,median,p25,p75,n_tickers,as_of")
        .eq("sector", sector)
        .order("as_of", desc=True)
        .limit(100)
        .execute()
        .data
        or []
    )
    medians: dict[str, dict[str, Any]] = {}
    for row in rows:
        metric = row.get("metric")
        if metric and metric not in medians:
            medians[metric] = row
    return medians


def _peer_comparisons(supabase, ticker: str) -> list[dict[str, Any]]:
    rows = (
        supabase.table("peer_groups")
        .select("peer_ticker,similarity,computed_at")
        .eq("ticker", ticker)
        .order("similarity", desc=True)
        .limit(10)
        .execute()
        .data
        or []
    )
    return [
        {
            "ticker": row.get("peer_ticker"),
            "similarity": row.get("similarity"),
            "computed_at": row.get("computed_at"),
        }
        for row in rows
        if row.get("peer_ticker") != ticker
    ]


def _article_histogram(articles: list[dict[str, Any]], days: int = 14) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    counts = {
        (now - timedelta(days=offset)).date().isoformat(): 0
        for offset in range(days - 1, -1, -1)
    }
    for article in articles:
        published = _parse_iso_datetime(article.get("published_at"))
        if not published:
            continue
        key = published.date().isoformat()
        if key in counts:
            counts[key] += 1
    return [{"date": key, "count": value} for key, value in counts.items()]


def _sentiment_distribution(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for article in articles:
        score = article.get("sentiment_score")
        if score is None:
            continue
        try:
            numeric = float(score)
        except (TypeError, ValueError):
            continue
        if numeric >= 60:
            counts["positive"] += 1
        elif numeric <= 40:
            counts["negative"] += 1
        else:
            counts["neutral"] += 1
    return [{"bucket": key, "count": value} for key, value in counts.items()]


@router.get("/{ticker}/methodology")
async def get_ticker_methodology(
    ticker: str,
    user_id: str = Depends(get_user_id),
):
    """Return cached methodology data for a ticker.

    Returns only what is already stored in ticker_risk_snapshots and
    shared_ticker_events — no live Polygon API calls are made. If a
    dimension's cached inputs are absent the field is returned as null
    rather than blocking on a slow computation.
    """
    supabase = get_supabase()
    upper = ticker.upper()

    metadata_result = (
        supabase.table("ticker_metadata")
        .select("*")
        .eq("ticker", upper)
        .limit(1)
        .execute()
    )
    metadata = metadata_result.data[0] if metadata_result.data else {}
    sector = metadata.get("sector")
    sector_medians = _latest_sector_medians(supabase, sector)
    peers = _peer_comparisons(supabase, upper)

    snapshot_result = (
        supabase.table("ticker_risk_snapshots")
        .select("*")
        .eq("ticker", upper)
        .order("analysis_as_of", desc=True)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    snapshot = snapshot_result.data[0] if snapshot_result.data else {}

    factor_breakdown = snapshot.get("factor_breakdown") or {}
    if isinstance(factor_breakdown, str):
        import json
        try:
            factor_breakdown = json.loads(factor_breakdown)
        except Exception:
            factor_breakdown = {}

    dimension_inputs = snapshot.get("dimension_inputs") or {}
    if isinstance(dimension_inputs, str):
        import json
        try:
            dimension_inputs = json.loads(dimension_inputs)
        except Exception:
            dimension_inputs = {}

    risk_dims = _shared_risk_dimensions(snapshot)

    articles_result = (
        supabase.table("shared_ticker_events")
        .select("*")
        .eq("ticker", upper)
        .order("published_at", desc=True)
        .limit(50)
        .execute()
    )
    articles = articles_result.data or []

    now = datetime.now(timezone.utc)
    seven_day_articles = [
        a for a in articles
        if (pub := _parse_iso_datetime(a.get("published_at"))) and now - pub <= timedelta(days=7)
    ]
    fourteen_day_articles = [
        a for a in articles
        if (pub := _parse_iso_datetime(a.get("published_at"))) and now - pub <= timedelta(days=14)
    ]

    # Build display article list — enriched articles first, fall back to all 7-day articles.
    enriched_articles = [
        a for a in seven_day_articles
        if a.get("sentiment_score") is not None
        or a.get("source_tier") is not None
        or a.get("recency_weight") is not None
        or a.get("tldr")
        or a.get("what_it_means")
    ]
    display_articles = enriched_articles or seven_day_articles

    # Pull cached dimension inputs — no live Polygon calls.
    news_inputs = dimension_inputs.get("news_sentiment") or {}
    macro_inputs = dimension_inputs.get("macro_exposure") or {}
    sector_inputs = dimension_inputs.get("sector_exposure") or {}
    volatility_inputs = dimension_inputs.get("volatility") or {}
    financial_inputs = dimension_inputs.get("financial_health") or {}
    macro_regression = factor_breakdown.get("macro_regression") or {}
    iv_rank = volatility_inputs.get("iv_rank")
    iv_source = volatility_inputs.get("iv_source")
    if iv_rank is None:
        iv_rank = estimate_iv_rank_from_realized_vol(
            volatility_inputs.get("realized_vol_30d"),
            volatility_inputs.get("realized_vol_90d"),
        )
        if iv_rank is not None:
            iv_source = "realized_vol_fallback"

    # Compute weighted news score on-the-fly from available articles when
    # the cached value is absent — this is a cheap in-memory calculation.
    if news_inputs.get("weighted_score") is None:
        weighted_total = 0.0
        total_weight = 0.0
        for article in display_articles:
            sentiment_score = article.get("sentiment_score")
            if sentiment_score is None:
                continue
            recency_weight = float(article.get("recency_weight") or 1.0)
            source_weight = float(article.get("source_weight") or 1.0)
            weight = recency_weight * source_weight
            weighted_total += float(sentiment_score) * weight
            total_weight += weight
        if total_weight > 0:
            news_inputs["weighted_score"] = round(weighted_total / total_weight, 1)

    # Sector fallback: use cached metadata when dimension_inputs lacks sector data.
    if not sector_inputs.get("sector_etf") and metadata.get("sector"):
        sector_inputs = {
            "sector": metadata.get("sector"),
            "sector_etf": None,
            "sector_beta": None,
            "sector_momentum_30d": None,
            "sector_breadth": None,
            "narrative": None,
        }

    article_payloads = [
        {
            "id": article.get("id"),
            "title": article.get("title"),
            "source": article.get("source"),
            "published_at": article.get("published_at"),
            "source_tier": article.get("source_tier"),
            "recency_weight": article.get("recency_weight"),
            "sentiment_score": article.get("sentiment_score"),
            "sentiment_reason": article.get("sentiment_reason"),
            "impact_tag": article.get("impact_tag"),
            "tldr": article.get("tldr"),
            "what_it_means": article.get("what_it_means"),
            "key_implications": article.get("key_implications") or [],
            "source_url": (
                article.get("canonical_url")
                or article.get("source_url")
                or article.get("url")
            ),
        }
        for article in display_articles[:15]
    ]
    article_payloads = attach_latest_personalisation(
        supabase,
        user_id=user_id,
        articles=article_payloads,
    )

    return {
        "ticker": upper,
        "dimensions": {
            "financial_health": {
                "score": risk_dims.get("financial_health"),
                "debt_to_equity": financial_inputs.get("debt_to_equity"),
                "fcf_margin": financial_inputs.get("fcf_margin"),
                "interest_coverage": financial_inputs.get("interest_coverage"),
                "current_ratio": financial_inputs.get("current_ratio"),
                "revenue_growth_trend": financial_inputs.get("revenue_growth_trend"),
                "profitability_trend": financial_inputs.get("profitability_trend"),
                "as_of_date": financial_inputs.get("as_of_date") or _isoformat_or_none(metadata.get("updated_at")),
                "data_source": financial_inputs.get("data_source") or "finnhub",
                "peer_comparisons": peers,
                "sector_median_comparison": {
                    metric: sector_medians.get(metric)
                    for metric in (
                        "debt_to_equity",
                        "fcf_margin",
                        "interest_coverage",
                        "current_ratio",
                    )
                    if sector_medians.get(metric)
                },
            },
            "news_sentiment": {
                "score": risk_dims.get("news_sentiment"),
                "article_count_7d": (
                    news_inputs.get("article_count_7d")
                    if news_inputs.get("article_count_7d") is not None
                    else len(seven_day_articles)
                ),
                "volume_signal": bool(news_inputs.get("volume_signal")),
                "weighted_score": news_inputs.get("weighted_score"),
                "articles": article_payloads,
                "article_histogram_14d": _article_histogram(fourteen_day_articles),
                "sentiment_distribution": _sentiment_distribution(fourteen_day_articles),
            },
            "macro_exposure": {
                "score": risk_dims.get("macro_exposure"),
                "r_squared": (
                    macro_inputs.get("r_squared")
                    if macro_inputs.get("r_squared") is not None
                    else macro_regression.get("r_squared")
                ),
                "trading_days_used": (
                    macro_inputs.get("trading_days_used")
                    if macro_inputs.get("trading_days_used") is not None
                    else macro_regression.get("trading_days_used")
                ),
                "limited_data": bool(
                    macro_inputs.get("limited_data")
                    if macro_inputs.get("limited_data") is not None
                    else macro_regression.get("limited_data")
                ),
                "as_of_date": macro_inputs.get("as_of_date") or macro_regression.get("as_of_date"),
                "coefficients": macro_inputs.get("coefficients") or macro_regression.get("coefficients") or {},
                "current_factor_levels": macro_inputs.get("current_factor_levels") or {},
                "factor_levels": macro_inputs.get("current_factor_levels") or {},
                "narrative": macro_inputs.get("narrative"),
            },
            "sector_exposure": {
                "score": risk_dims.get("sector_exposure"),
                "sector": sector_inputs.get("sector") or metadata.get("sector"),
                "sector_etf": sector_inputs.get("sector_etf"),
                "sector_beta": sector_inputs.get("sector_beta"),
                "sector_momentum_30d": sector_inputs.get("sector_momentum_30d"),
                "sector_breadth": sector_inputs.get("sector_breadth"),
                "narrative": sector_inputs.get("narrative"),
                "peer_comparisons": peers,
                "sector_median_comparison": {
                    metric: sector_medians.get(metric)
                    for metric in ("pe_ratio", "beta", "volatility_proxy")
                    if sector_medians.get(metric)
                },
            },
            "volatility": {
                "score": risk_dims.get("volatility"),
                "realized_vol_30d": volatility_inputs.get("realized_vol_30d"),
                "realized_vol_90d": volatility_inputs.get("realized_vol_90d"),
                "vol_ratio": volatility_inputs.get("vol_ratio"),
                "max_drawdown_252d": volatility_inputs.get("max_drawdown_252d"),
                "beta_to_spy": volatility_inputs.get("beta_to_spy"),
                "iv_rank": iv_rank,
                "implied_volatility": volatility_inputs.get("implied_volatility"),
                "iv_source": iv_source,
                "factor_levels": {
                    "realized_vol_30d": volatility_inputs.get("realized_vol_30d"),
                    "realized_vol_90d": volatility_inputs.get("realized_vol_90d"),
                    "iv_rank": iv_rank,
                },
                "as_of_date": volatility_inputs.get("as_of_date"),
            },
        },
        "composite": {
            "score": snapshot.get("composite_score") or snapshot.get("safety_score"),
            "grade": snapshot.get("grade"),
            "methodology_version": snapshot.get("methodology_version"),
        },
    }
