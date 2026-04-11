from typing import Optional
from collections import Counter


def calculate_concentration_risk(positions: list[dict]) -> tuple[float, list[dict]]:
    if not positions:
        return 0.0, []
    total_value = sum(
        float(p.get("shares", 0))
        * float(p.get("current_price", 0) or p.get("purchase_price", 0))
        for p in positions
    )
    if total_value == 0:
        return 50.0, []
    position_values = []
    for p in positions:
        value = float(p.get("shares", 0)) * float(
            p.get("current_price", 0) or p.get("purchase_price", 0)
        )
        weight = (value / total_value) * 100
        position_values.append(
            {
                "ticker": p.get("ticker"),
                "value": value,
                "weight": weight,
            }
        )
    position_values.sort(key=lambda x: x["weight"], reverse=True)
    herfindahl_index = sum(p["weight"] ** 2 for p in position_values)
    concentration_score = min(100, herfindahl_index / 50)
    danger_tickers = [p["ticker"] for p in position_values if p["weight"] > 25]
    return round(concentration_score, 1), danger_tickers


def calculate_cluster_risk(
    positions: list[dict], sector_map: Optional[dict] = None
) -> tuple[float, list[dict]]:
    if sector_map is None:
        sector_map = {}
    if not positions:
        return 0.0, []
    sector_counts = Counter()
    sector_values = {}
    total_value = 0
    for p in positions:
        ticker = p.get("ticker")
        sector = sector_map.get(ticker, "unknown")
        value = float(p.get("shares", 0)) * float(
            p.get("current_price", 0) or p.get("purchase_price", 0)
        )
        total_value += value
        sector_counts[sector] += 1
        if sector not in sector_values:
            sector_values[sector] = 0
        sector_values[sector] += value
    if total_value == 0:
        return 0.0, []
    sector_weights = {s: (v / total_value) * 100 for s, v in sector_values.items()}
    max_sector_weight = max(sector_weights.values()) if sector_weights else 0
    cluster_score = 0.0
    if max_sector_weight > 50:
        cluster_score = min(100, (max_sector_weight - 50) * 2)
    elif len(sector_counts) > 0:
        if max(sector_counts.values()) >= len(positions) * 0.6:
            cluster_score = min(100, max(sector_counts.values()) * 30)
    top_clusters = [s for s, w in sector_weights.items() if w > 30]
    return round(cluster_score, 1), top_clusters


def calculate_correlation_risk(
    positions: list[dict],
    ticker_correlation_matrix: Optional[dict] = None,
) -> tuple[float, list[dict]]:
    if not positions or len(positions) < 2:
        return 0.0, []
    if ticker_correlation_matrix is None:
        tickers = [p.get("ticker") for p in positions]
        return 0.0, []
    tickers = [p.get("ticker") for p in positions]
    pair_correlations = []
    for i, t1 in enumerate(tickers):
        for t2 in tickers[i + 1 :]:
            corr = ticker_correlation_matrix.get(t1, {}).get(t2, 0)
            if corr > 0.5:
                pair_correlations.append(
                    {"ticker1": t1, "ticker2": t2, "correlation": corr}
                )
    if not pair_correlations:
        return 0.0, []
    avg_correlation = sum(pc["correlation"] for pc in pair_correlations) / len(
        pair_correlations
    )
    correlation_score = min(100, avg_correlation * 100)
    high_corr_pairs = [pc for pc in pair_correlations if pc["correlation"] > 0.7]
    return round(correlation_score, 1), high_corr_pairs


def calculate_liquidity_mismatch(
    positions: list[dict], ticker_metadata: Optional[dict] = None
) -> tuple[float, list[dict]]:
    if not positions or ticker_metadata is None:
        return 0.0, []
    total_value = sum(
        float(p.get("shares", 0))
        * float(p.get("current_price", 0) or p.get("purchase_price", 0))
        for p in positions
    )
    if total_value == 0:
        return 0.0, []
    liquidity_issues = []
    for p in positions:
        ticker = p.get("ticker")
        metadata = ticker_metadata.get(ticker, {})
        avg_volume = metadata.get("avg_daily_dollar_volume", 0)
        if avg_volume is None or avg_volume == 0:
            continue
        shares = float(p.get("shares", 0))
        value = shares * float(p.get("current_price", 0) or p.get("purchase_price", 0))
        days_to_liquidate = value / avg_volume if avg_volume > 0 else 999
        if days_to_liquidate > 5:
            liquidity_issues.append(
                {
                    "ticker": ticker,
                    "value": value,
                    "days_to_liquidate": round(days_to_liquidate, 1),
                }
            )
    if not liquidity_issues:
        return 0.0, []
    illiquid_value = sum(i["value"] for i in liquidity_issues)
    illiquid_pct = (illiquid_value / total_value) * 100
    liquidity_score = min(100, illiquid_pct * 1.5)
    return round(liquidity_score, 1), liquidity_issues


def calculate_macro_stack_risk(
    positions: list[dict],
    ticker_metadata: Optional[dict] = None,
    regime_state: str = "neutral",
) -> tuple[float, list[str]]:
    if not positions:
        return 0.0, []
    if ticker_metadata is None:
        return 0.0, []
    sensitive_tickers = []
    for p in positions:
        ticker = p.get("ticker")
        metadata = ticker_metadata.get(ticker, {})
        sensitivity = metadata.get("macro_sensitivity", "moderate")
        if sensitivity in ["high", "very_high"]:
            sensitive_tickers.append(ticker)
    if not sensitive_tickers:
        return 0.0, []
    regime_risk_multiplier = {
        "neutral": 0.5,
        "risk_on": 0.7,
        "risk_off": 1.5,
        "rates_up": 2.0,
        "rates_down": 0.8,
        "credit_tightening": 2.0,
        "credit_easing": 0.5,
        "inflation_shock": 1.8,
        "commodity_shock": 1.5,
        "recession_pressure": 2.0,
        "expansion_supportive": 0.5,
    }
    base_score = len(sensitive_tickers) * 15
    multiplier = regime_risk_multiplier.get(regime_state, 1.0)
    macro_score = min(100, base_score * multiplier)
    return round(macro_score, 1), sensitive_tickers


def calculate_portfolio_risk_score(
    positions: list[dict],
    sector_map: Optional[dict] = None,
    ticker_metadata: Optional[dict] = None,
    ticker_correlation_matrix: Optional[dict] = None,
    regime_state: str = "neutral",
) -> dict:
    concentration_risk, concentration_tickers = calculate_concentration_risk(positions)
    cluster_risk, danger_clusters = calculate_cluster_risk(positions, sector_map)
    correlation_risk, high_corr_pairs = calculate_correlation_risk(
        positions, ticker_correlation_matrix
    )
    liquidity_mismatch, liquidity_issues = calculate_liquidity_mismatch(
        positions, ticker_metadata
    )
    macro_stack_risk, macro_sensitive_tickers = calculate_macro_stack_risk(
        positions, ticker_metadata, regime_state
    )
    weights = {
        "concentration": 0.30,
        "cluster": 0.20,
        "correlation": 0.20,
        "liquidity": 0.15,
        "macro_stack": 0.15,
    }
    portfolio_score = (
        concentration_risk * weights["concentration"]
        + cluster_risk * weights["cluster"]
        + correlation_risk * weights["correlation"]
        + liquidity_mismatch * weights["liquidity"]
        + macro_stack_risk * weights["macro_stack"]
    )
    portfolio_score = min(100, max(0, portfolio_score))
    confidence = 0.70
    if ticker_metadata is not None:
        coverage = len([p for p in positions if p.get("ticker") in ticker_metadata])
        confidence = 0.50 + (coverage / len(positions)) * 0.30 if positions else 0.50
    factor_breakdown = {
        "concentration_risk": round(concentration_risk, 1),
        "cluster_risk": round(cluster_risk, 1),
        "correlation_risk": round(correlation_risk, 1),
        "liquidity_mismatch": round(liquidity_mismatch, 1),
        "macro_stack_risk": round(macro_stack_risk, 1),
    }
    top_risk_drivers = []
    if concentration_risk > 30:
        top_risk_drivers.append(
            {"type": "concentration", "tickers": concentration_tickers}
        )
    if cluster_risk > 25:
        top_risk_drivers.append({"type": "cluster", "clusters": danger_clusters})
    if liquidity_mismatch > 20:
        top_risk_drivers.append({"type": "liquidity", "issues": liquidity_issues})
    if macro_stack_risk > 30:
        top_risk_drivers.append({"type": "macro", "tickers": macro_sensitive_tickers})
    return {
        "portfolio_allocation_risk_score": round(portfolio_score, 1),
        "confidence": round(confidence, 2),
        "concentration_risk": round(concentration_risk, 1),
        "cluster_risk": round(cluster_risk, 1),
        "correlation_risk": round(correlation_risk, 1),
        "liquidity_mismatch": round(liquidity_mismatch, 1),
        "macro_stack_risk": round(macro_stack_risk, 1),
        "factor_breakdown": factor_breakdown,
        "top_risk_drivers": top_risk_drivers,
        "danger_clusters": danger_clusters,
    }
