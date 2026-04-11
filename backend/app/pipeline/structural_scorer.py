from datetime import datetime
from typing import Optional
from .analysis_utils import clamp_score

MARKET_CAP_BUCKETS = {
    "very_high": {"min": 500e9, "max": None, "base_score": 95, "confidence_boost": 0.1},
    "high": {"min": 50e9, "max": 500e9, "base_score": 85, "confidence_boost": 0.05},
    "moderate_high": {
        "min": 10e9,
        "max": 50e9,
        "base_score": 75,
        "confidence_boost": 0.0,
    },
    "moderate": {"min": 2e9, "max": 10e9, "base_score": 65, "confidence_boost": -0.05},
    "low_moderate": {
        "min": 500e6,
        "max": 2e9,
        "base_score": 50,
        "confidence_boost": -0.1,
    },
    "low": {"min": 100e6, "max": 500e6, "base_score": 35, "confidence_boost": -0.15},
    "very_low": {"min": None, "max": 100e6, "base_score": 20, "confidence_boost": -0.2},
}

LIQUIDITY_SCORE_BUCKETS = {
    "excellent": {"min_volume": 100e6, "penalty": 0, "confidence_boost": 0.05},
    "good": {"min_volume": 10e6, "penalty": -2, "confidence_boost": 0.0},
    "moderate": {"min_volume": 1e6, "penalty": -5, "confidence_boost": -0.05},
    "low": {"min_volume": 100e3, "penalty": -10, "confidence_boost": -0.1},
    "very_low": {"min_volume": 0, "penalty": -20, "confidence_boost": -0.15},
}

VOLATILITY_REGIME_SCORES = {
    "very_low": {"max_vol": 0.10, "penalty": 0, "confidence_boost": 0.05},
    "low": {"max_vol": 0.20, "penalty": -2, "confidence_boost": 0.0},
    "moderate": {"max_vol": 0.35, "penalty": -5, "confidence_boost": -0.05},
    "high": {"max_vol": 0.50, "penalty": -10, "confidence_boost": -0.1},
    "very_high": {"max_vol": None, "penalty": -20, "confidence_boost": -0.15},
}

LEVERAGE_SCORES = {
    "very_low": {"max_debt_equity": 0.3, "bonus": 5, "confidence_boost": 0.05},
    "low": {"max_debt_equity": 0.7, "bonus": 2, "confidence_boost": 0.02},
    "moderate": {"max_debt_equity": 1.5, "bonus": 0, "confidence_boost": 0.0},
    "high": {"max_debt_equity": 3.0, "bonus": -5, "confidence_boost": -0.05},
    "very_high": {"max_debt_equity": None, "bonus": -15, "confidence_boost": -0.1},
}

PROFITABILITY_SCORES = {
    "profitable": {"bonus": 5, "confidence_boost": 0.05},
    "mixed": {"bonus": 0, "confidence_boost": -0.05},
    "unprofitable": {"bonus": -10, "confidence_boost": -0.1},
}

ASSET_CLASS_BASE_SCORES = {
    "treasury": {"base": 98, "confidence_boost": 0.1},
    "large_cap_equity": {"base": 80, "confidence_boost": 0.05},
    "mid_cap_equity": {"base": 65, "confidence_boost": 0.0},
    "small_cap_equity": {"base": 45, "confidence_boost": -0.1},
    "adr": {"base": 55, "confidence_boost": -0.1},
    "biotech": {"base": 35, "confidence_boost": -0.15},
    "penny_stock": {"base": 15, "confidence_boost": -0.2},
    "etf": {"base": 75, "confidence_boost": 0.0},
    "other": {"base": 50, "confidence_boost": 0.0},
}

DAILY_MOVE_CAPS = {
    "large_cap": 6,
    "mid_cap": 10,
    "small_cap": 15,
    "microcap": 20,
}

CONFIDENCE_BUCKETS = {
    "high": {"min": 0.80, "score_floor": 0},
    "medium": {"min": 0.55, "score_floor": 10},
    "low": {"min": 0.0, "score_floor": 20},
}


def get_market_cap_bucket(market_cap: Optional[float]) -> tuple[str, float]:
    if market_cap is None:
        return "very_low", 20
    for bucket_name, bucket_data in MARKET_CAP_BUCKETS.items():
        if bucket_data["min"] is not None and market_cap >= bucket_data["min"]:
            if bucket_data["max"] is None or market_cap < bucket_data["max"]:
                return bucket_name, bucket_data["base_score"]
    return "very_low", 20


def get_market_cap_score(market_cap: Optional[float]) -> float:
    _, base_score = get_market_cap_bucket(market_cap)
    return base_score


def get_liquidity_score(
    avg_daily_dollar_volume: Optional[float] = None,
    spread_proxy: Optional[float] = None,
    listing_exchange: Optional[str] = None,
) -> tuple[float, float]:
    if avg_daily_dollar_volume is None:
        return 0, -0.15
    if avg_daily_dollar_volume >= 100e6:
        tier = "excellent"
    elif avg_daily_dollar_volume >= 10e6:
        tier = "good"
    elif avg_daily_dollar_volume >= 1e6:
        tier = "moderate"
    elif avg_daily_dollar_volume >= 100e3:
        tier = "low"
    else:
        tier = "very_low"
    bucket = LIQUIDITY_SCORE_BUCKETS[tier]
    penalty = bucket["penalty"]
    if spread_proxy is not None and spread_proxy > 0.01:
        penalty -= min(5, spread_proxy * 100)
    if listing_exchange in ["OTCM", "OTCBB", "pink"]:
        penalty -= 15
    return 50 + penalty, bucket["confidence_boost"]


def get_volatility_score(
    volatility_proxy: Optional[float] = None,
) -> tuple[float, float]:
    if volatility_proxy is None:
        return 50, -0.05
    if volatility_proxy <= 0.10:
        tier = "very_low"
    elif volatility_proxy <= 0.20:
        tier = "low"
    elif volatility_proxy <= 0.35:
        tier = "moderate"
    elif volatility_proxy <= 0.50:
        tier = "high"
    else:
        tier = "very_high"
    bucket = VOLATILITY_REGIME_SCORES[tier]
    return 50 + bucket["penalty"], bucket["confidence_boost"]


def get_leverage_score(leverage_profile: str = "moderate") -> tuple[float, float]:
    bucket = LEVERAGE_SCORES.get(leverage_profile, LEVERAGE_SCORES["moderate"])
    return 50 + bucket["bonus"], bucket["confidence_boost"]


def get_profitability_score(
    profitability_profile: str = "mixed",
) -> tuple[float, float]:
    bucket = PROFITABILITY_SCORES.get(
        profitability_profile, PROFITABILITY_SCORES["mixed"]
    )
    return 50 + bucket["bonus"], bucket["confidence_boost"]


def get_asset_class_score(asset_class: Optional[str] = None) -> tuple[float, float]:
    if asset_class is None:
        return 50, 0.0
    bucket = ASSET_CLASS_BASE_SCORES.get(asset_class, ASSET_CLASS_BASE_SCORES["other"])
    return bucket["base"], bucket["confidence_boost"]


def calculate_structural_base_score(
    market_cap: Optional[float] = None,
    avg_daily_dollar_volume: Optional[float] = None,
    volatility_proxy: Optional[float] = None,
    leverage_profile: str = "moderate",
    profitability_profile: str = "mixed",
    asset_class: Optional[str] = None,
) -> dict:
    market_cap_bucket, market_cap_base = get_market_cap_bucket(market_cap)
    liquidity_score, liquidity_conf = get_liquidity_score(avg_daily_dollar_volume)
    volatility_score, volatility_conf = get_volatility_score(volatility_proxy)
    leverage_score, leverage_conf = get_leverage_score(leverage_profile)
    profitability_score, profitability_conf = get_profitability_score(
        profitability_profile
    )
    asset_class_score, asset_class_conf = get_asset_class_score(asset_class)

    base_from_market_cap = market_cap_base * 0.30
    base_from_asset_class = asset_class_score * 0.20
    base_from_liquidity = liquidity_score * 0.20
    base_from_volatility = volatility_score * 0.15
    base_from_leverage = leverage_score * 0.10
    base_from_profitability = profitability_score * 0.05

    structural_base = (
        base_from_market_cap
        + base_from_asset_class
        + base_from_liquidity
        + base_from_volatility
        + base_from_leverage
        + base_from_profitability
    )
    structural_base = clamp_score(structural_base, 50)

    confidence_delta = (
        liquidity_conf
        + volatility_conf
        + leverage_conf
        + profitability_conf
        + asset_class_conf
    )

    if market_cap is not None:
        if market_cap >= 10e9:
            confidence_delta += 0.1
        elif market_cap < 100e6:
            confidence_delta -= 0.1

    base_confidence = 0.70 + confidence_delta
    base_confidence = max(0.3, min(0.95, base_confidence))

    factor_breakdown = {
        "market_cap_bucket": market_cap_bucket,
        "market_cap_contribution": round(base_from_market_cap, 1),
        "asset_class_contribution": round(base_from_asset_class, 1),
        "liquidity_score": round(liquidity_score, 1),
        "volatility_score": round(volatility_score, 1),
        "leverage_score": round(leverage_score, 1),
        "profitability_score": round(profitability_score, 1),
    }

    return {
        "structural_base_score": round(structural_base, 1),
        "confidence": round(base_confidence, 2),
        "factor_breakdown": factor_breakdown,
        "market_cap_bucket": market_cap_bucket,
    }


def get_daily_move_cap(
    asset_class: Optional[str] = None, market_cap: Optional[float] = None
) -> float:
    if market_cap is not None and market_cap >= 50e9:
        return DAILY_MOVE_CAPS["large_cap"]
    elif market_cap is not None and market_cap >= 2e9:
        return DAILY_MOVE_CAPS["mid_cap"]
    elif market_cap is not None and market_cap >= 100e6:
        return DAILY_MOVE_CAPS["small_cap"]
    else:
        return DAILY_MOVE_CAPS["microcap"]


def smooth_score_change(
    new_score: float,
    previous_score: Optional[float],
    asset_class: Optional[str] = None,
    market_cap: Optional[float] = None,
) -> float:
    if previous_score is None:
        return new_score
    cap = get_daily_move_cap(asset_class, market_cap)
    delta = new_score - previous_score
    if abs(delta) <= cap:
        return new_score
    if delta > 0:
        return previous_score + cap
    else:
        return previous_score - cap


def calculate_macro_adjustment(
    regime_state: str = "neutral",
    asset_sensitivity: str = "moderate",
    rates_signal: Optional[str] = None,
    credit_signal: Optional[str] = None,
) -> float:
    base_adjustment = 0.0
    if regime_state == "risk_off":
        base_adjustment = -5
    elif regime_state == "risk_on":
        base_adjustment = 3
    elif regime_state == "recession_pressure":
        base_adjustment = -8
    elif regime_state == "expansion_supportive":
        base_adjustment = 5
    elif regime_state == "rates_up":
        base_adjustment = -5
    elif regime_state == "rates_down":
        base_adjustment = 3

    if rates_signal == "rising":
        base_adjustment -= 3
    elif rates_signal == "falling":
        base_adjustment += 3

    if credit_signal == "tightening":
        base_adjustment -= 5
    elif credit_signal == "easing":
        base_adjustment += 3

    sensitivity_multiplier = {
        "low": 0.5,
        "moderate": 1.0,
        "high": 1.5,
        "very_high": 2.0,
    }.get(asset_sensitivity, 1.0)

    final_adjustment = base_adjustment * sensitivity_multiplier
    final_adjustment = max(-15, min(15, final_adjustment))
    return round(final_adjustment, 1)


def calculate_event_adjustment(
    event_significance: str = "minor",
    event_direction: str = "negative",
    event_confidence: float = 0.5,
    event_age_days: int = 0,
) -> float:
    base_adjustments = {
        "minor": {"negative": -2, "neutral": 0, "positive": 1},
        "moderate": {"negative": -5, "neutral": 0, "positive": 2},
        "major": {"negative": -12, "neutral": 0, "positive": 3},
    }
    if event_significance not in base_adjustments:
        return 0.0
    base = base_adjustments[event_significance].get(event_direction, 0)

    confidence_factor = max(0.3, min(1.0, event_confidence))
    adjustment = base * confidence_factor

    if event_age_days <= 1:
        decay = 1.0
    elif event_age_days <= 5:
        decay = 0.7
    elif event_age_days <= 14:
        decay = 0.3
    else:
        decay = 0.1

    adjustment = adjustment * decay
    adjustment = max(-20, min(5, adjustment))
    return round(adjustment, 1)


def calculate_final_safety_score(
    structural_base_score: float,
    macro_adjustment: float = 0.0,
    event_adjustment: float = 0.0,
) -> float:
    raw_score = structural_base_score + macro_adjustment + event_adjustment
    final = clamp_score(raw_score, 50)
    return round(final, 1)


def build_ticker_metadata(
    ticker: str,
    company_name: Optional[str] = None,
    asset_class: Optional[str] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    exchange: Optional[str] = None,
    market_cap: Optional[float] = None,
    float_shares: Optional[float] = None,
    avg_daily_dollar_volume: Optional[float] = None,
    spread_proxy: Optional[float] = None,
    beta: Optional[float] = None,
    volatility_proxy: Optional[float] = None,
    profitability_profile: str = "mixed",
    leverage_profile: str = "moderate",
    macro_sensitivity: str = "moderate",
) -> dict:
    structural_result = calculate_structural_base_score(
        market_cap=market_cap,
        avg_daily_dollar_volume=avg_daily_dollar_volume,
        volatility_proxy=volatility_proxy,
        leverage_profile=leverage_profile,
        profitability_profile=profitability_profile,
        asset_class=asset_class,
    )

    market_cap_bucket, _ = get_market_cap_bucket(market_cap)

    structural_fragility = 100 - structural_result["structural_base_score"]
    liquidity_risk = 100 - structural_result["factor_breakdown"].get(
        "liquidity_score", 50
    )

    return {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "asset_class": asset_class,
        "sector": sector,
        "industry": industry,
        "exchange": exchange,
        "market_cap": market_cap,
        "market_cap_bucket": market_cap_bucket,
        "float_shares": float_shares,
        "avg_daily_dollar_volume": avg_daily_dollar_volume,
        "spread_proxy": spread_proxy,
        "beta": beta,
        "volatility_proxy": volatility_proxy,
        "profitability_profile": profitability_profile,
        "leverage_profile": leverage_profile,
        "macro_sensitivity": macro_sensitivity,
        "structural_fragility": round(structural_fragility, 1),
        "liquidity_risk": round(liquidity_risk, 1),
        "updated_at": datetime.utcnow().isoformat(),
    }
