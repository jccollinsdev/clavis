from datetime import date, datetime
from typing import Optional
from .structural_scorer import clamp_score

REGIME_STATES = [
    "risk_on",
    "risk_off",
    "rates_up",
    "rates_down",
    "credit_tightening",
    "credit_easing",
    "inflation_shock",
    "commodity_shock",
    "recession_pressure",
    "expansion_supportive",
    "neutral",
]

RATES_SIGNALS = ["rising", "falling", "stable"]
CREDIT_SIGNALS = ["tightening", "easing", "stable"]
INFLATION_SIGNALS = ["spiking", "moderating", "stable"]
GROWTH_SIGNALS = ["expanding", "contracting", "stable"]
RISK_ON_OFF_SIGNALS = ["risk_on", "risk_off", "neutral"]


def compute_macro_regime(
    vix_level: Optional[float] = None,
    credit_spread_level: Optional[float] = None,
    rates_trend: str = "stable",
    inflation_trend: str = "stable",
    growth_trend: str = "stable",
    market_breadth_trend: Optional[str] = None,
    high_yield_趋势: Optional[str] = None,
) -> dict:
    risk_on_off = "neutral"
    regime_state = "neutral"
    rates_signal = "stable"
    credit_signal = "stable"
    inflation_signal = "stable"
    growth_signal = "stable"

    if vix_level is not None:
        if vix_level > 30:
            risk_on_off = "risk_off"
            regime_state = "risk_off"
        elif vix_level < 15:
            risk_on_off = "risk_on"
            regime_state = "risk_on"

    if credit_spread_level is not None:
        if credit_spread_level > 150:
            credit_signal = "tightening"
            if regime_state == "neutral":
                regime_state = "credit_tightening"
        elif credit_spread_level < 80:
            credit_signal = "easing"
            if regime_state == "neutral":
                regime_state = "credit_easing"

    if rates_trend == "rising":
        rates_signal = "rising"
        if regime_state in ["neutral", "risk_on"]:
            regime_state = "rates_up"
    elif rates_trend == "falling":
        rates_signal = "falling"
        if regime_state in ["neutral", "risk_off"]:
            regime_state = "rates_down"

    if inflation_trend == "spiking":
        inflation_signal = "spiking"
        if regime_state == "neutral":
            regime_state = "inflation_shock"
    elif inflation_trend == "moderating":
        inflation_signal = "moderating"

    if growth_trend == "contracting":
        growth_signal = "contracting"
        if regime_state in ["neutral", "risk_off"]:
            regime_state = "recession_pressure"
    elif growth_trend == "expanding":
        growth_signal = "expanding"
        if regime_state == "neutral":
            regime_state = "expansion_supportive"

    if high_yield_趋势 == "widening" and risk_on_off == "neutral":
        risk_on_off = "risk_off"
        if regime_state == "neutral":
            regime_state = "credit_tightening"
    elif high_yield_趋势 == "narrowing" and risk_on_off == "neutral":
        risk_on_off = "risk_on"
        if regime_state == "neutral":
            regime_state = "credit_easing"

    if market_breadth_trend == "narrowing" and risk_on_off == "risk_on":
        if regime_state in ["risk_on", "neutral"]:
            regime_state = "expansion_supportive"

    return {
        "regime_state": regime_state,
        "rates_signal": rates_signal,
        "credit_signal": credit_signal,
        "inflation_signal": inflation_signal,
        "growth_signal": growth_signal,
        "risk_on_off_signal": risk_on_off,
        "vix_level": vix_level,
        "credit_spread_level": credit_spread_level,
    }


def get_regime_from_market_data(
    spx_level: Optional[float] = None,
    spx_早先_level: Optional[float] = None,
    vix_level: Optional[float] = None,
    credit_spread_bps: Optional[float] = None,
    ten_yield_change: Optional[float] = None,
    high_yield_spread_change: Optional[float] = None,
) -> dict:
    vix_tier = None
    if vix_level is not None:
        if vix_level < 12:
            vix_tier = "very_low"
        elif vix_level < 18:
            vix_tier = "low"
        elif vix_level < 25:
            vix_tier = "moderate"
        elif vix_level < 35:
            vix_tier = "high"
        else:
            vix_tier = "very_high"

    rates_trend = "stable"
    if ten_yield_change is not None:
        if ten_yield_change > 0.10:
            rates_trend = "rising"
        elif ten_yield_change < -0.10:
            rates_trend = "falling"

    inflation_trend = "stable"
    growth_trend = "stable"
    high_yield_趋势 = None

    if spx_level is not None and spx_早先_level is not None:
        if spx_level < spx_早先_level * 0.95:
            growth_trend = "contracting"
        elif spx_level > spx_早先_level * 1.05:
            growth_trend = "expanding"

    if high_yield_spread_change is not None:
        if high_yield_spread_change > 30:
            high_yield_趋势 = "widening"
        elif high_yield_spread_change < -30:
            high_yield_趋势 = "narrowing"

    return compute_macro_regime(
        vix_level=vix_level,
        credit_spread_level=credit_spread_bps,
        rates_trend=rates_trend,
        inflation_trend=inflation_trend,
        growth_trend=growth_trend,
        high_yield_趋势=high_yield_趋势,
    )


def get_macro_sensitivity_for_sector(sector: Optional[str] = None) -> str:
    if sector is None:
        return "moderate"
    sector_lower = sector.lower()
    high_sensitivity_sectors = [
        "real estate",
        "utilities",
        "materials",
        "energy",
        "financials",
        "banks",
    ]
    low_sensitivity_sectors = [
        "healthcare",
        "consumer staples",
        "industrials",
        "technology",
    ]
    for hs in high_sensitivity_sectors:
        if hs in sector_lower:
            return "high"
    for ls in low_sensitivity_sectors:
        if ls in sector_lower:
            return "low"
    return "moderate"


def get_macro_sensitivity_for_asset_class(asset_class: Optional[str] = None) -> str:
    if asset_class is None:
        return "moderate"
    asset_class_lower = asset_class.lower()
    if "treasury" in asset_class_lower or "bond" in asset_class_lower:
        return "very_high"
    if "large_cap" in asset_class_lower:
        return "low"
    if "small_cap" in asset_class_lower or "penny" in asset_class_lower:
        return "very_high"
    if "biotech" in asset_class_lower:
        return "very_high"
    if "adr" in asset_class_lower:
        return "high"
    return "moderate"


def get_macro_sensitivity(
    sector: Optional[str] = None,
    asset_class: Optional[str] = None,
) -> str:
    sector_sensitivity = get_macro_sensitivity_for_sector(sector)
    asset_sensitivity = get_macro_sensitivity_for_asset_class(asset_class)
    sensitivity_map = {
        ("high", "high"): "very_high",
        ("high", "moderate"): "high",
        ("high", "low"): "high",
        ("moderate", "high"): "high",
        ("moderate", "moderate"): "moderate",
        ("moderate", "low"): "moderate",
        ("low", "high"): "high",
        ("low", "moderate"): "moderate",
        ("low", "low"): "low",
    }
    return sensitivity_map.get((sector_sensitivity, asset_sensitivity), "moderate")
