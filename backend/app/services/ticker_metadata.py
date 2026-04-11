import os
import requests
from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import Optional
from ..config import get_settings

POLYGON_BASE_URL = "https://api.polygon.io/v1"
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def get_polygon_client() -> str:
    return get_settings().polygon_api_key


def get_finnhub_client() -> str:
    return get_settings().finnhub_api_key


def get_supabase_admin() -> Client:
    return create_client(
        os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )


def fetch_ticker_details_from_polygon(ticker: str) -> dict | None:
    api_key = get_polygon_client()
    if not api_key:
        return None

    try:
        url = f"{POLYGON_BASE_URL}/meta/symbols/{ticker.upper()}"
        params = {"apiKey": api_key}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name"),
                "symbol": data.get("symbol"),
                "exchange": data.get("exchange"),
                "asset_class": _map_polygon_type_to_asset_class(data.get("type")),
            }
        return None
    except Exception as e:
        print(f"Error fetching Polygon ticker details for {ticker}: {e}")
        return None


def fetch_ticker_details_from_finnhub(ticker: str) -> dict | None:
    api_key = get_finnhub_client()
    if not api_key:
        return None

    try:
        profile_url = f"{FINNHUB_BASE_URL}/stock/profile2"
        profile_resp = requests.get(
            profile_url,
            params={"symbol": ticker.upper(), "token": api_key},
            timeout=10,
        )
        metrics_url = f"{FINNHUB_BASE_URL}/stock/metric"
        metrics_resp = requests.get(
            metrics_url,
            params={"symbol": ticker.upper(), "token": api_key, "metric": "all"},
            timeout=10,
        )
        profile_data = profile_resp.json() if profile_resp.status_code == 200 else {}
        metrics_data = metrics_resp.json() if metrics_resp.status_code == 200 else {}

        market_cap = profile_data.get("marketCapitalization")
        if market_cap:
            market_cap = float(market_cap) * 1e6

        avg_volume = None
        if "volAvg" in metrics_data.get("metric", {}):
            avg_volume = metrics_data["metric"]["volAvg"]

        ten_day_avg = None
        if "10DayAverageTradingVolume" in metrics_data.get("metric", {}):
            ten_day_avg = metrics_data["metric"]["10DayAverageTradingVolume"]

        if ten_day_avg and profile_data.get("price"):
            avg_daily_dollar_volume = float(ten_day_avg) * float(profile_data["price"])
        elif avg_volume and profile_data.get("price"):
            avg_daily_dollar_volume = float(avg_volume) * float(profile_data["price"])
        else:
            avg_daily_dollar_volume = None

        beta = metrics_data.get("metric", {}).get("beta")

        return {
            "company_name": profile_data.get("name"),
            "ticker": ticker.upper(),
            "exchange": profile_data.get("exchange"),
            "sector": profile_data.get("finnhubIndustry") or profile_data.get("sector"),
            "industry": profile_data.get("industry"),
            "market_cap": market_cap,
            "avg_daily_dollar_volume": avg_daily_dollar_volume,
            "beta": beta,
        }
    except Exception as e:
        print(f"Error fetching Finnhub ticker details for {ticker}: {e}")
        return None


def fetch_market_cap_from_polygon(ticker: str) -> float | None:
    api_key = get_polygon_client()
    if not api_key:
        return None

    try:
        url = f"{POLYGON_BASE_URL}/meta/symbols/{ticker.upper()}"
        params = {"apiKey": api_key}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            mc = data.get("market_cap")
            if mc:
                return float(mc)
        return None
    except Exception as e:
        print(f"Error fetching market cap for {ticker}: {e}")
        return None


def fetch_volatility_proxy(ticker: str, days: int = 30) -> float | None:
    from .polygon import fetch_aggs

    aggs = fetch_aggs(ticker, days)
    if not aggs or len(aggs) < 5:
        return None

    returns = []
    for i in range(1, len(aggs)):
        prev_close = aggs[i - 1].get("c", 0)
        curr_close = aggs[i].get("c", 0)
        if prev_close > 0:
            ret = (curr_close - prev_close) / prev_close
            returns.append(ret)

    if not returns:
        return None

    import statistics

    std_dev = statistics.stdev(returns) if len(returns) > 1 else 0
    return std_dev


def fetch_float_shares_from_finnhub(ticker: str) -> float | None:
    api_key = get_finnhub_client()
    if not api_key:
        return None

    try:
        url = f"{FINNHUB_BASE_URL}/stock/metric"
        resp = requests.get(
            url,
            params={"symbol": ticker.upper(), "token": api_key, "metric": "all"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            shares_float = data.get("metric", {}).get("sharesFloat")
            if shares_float:
                return float(shares_float)
        return None
    except Exception as e:
        print(f"Error fetching float shares for {ticker}: {e}")
        return None


def _map_polygon_type_to_asset_class(type_str: str | None) -> str:
    if not type_str:
        return "other"
    type_lower = type_str.lower()
    if "etf" in type_lower:
        return "etf"
    if "common" in type_lower:
        return "large_cap_equity"
    if "adr" in type_lower or "gdr" in type_lower:
        return "adr"
    return "other"


def _get_market_cap_bucket(market_cap: float | None) -> str | None:
    if market_cap is None:
        return None
    if market_cap >= 500e9:
        return "very_high"
    if market_cap >= 50e9:
        return "high"
    if market_cap >= 10e9:
        return "moderate_high"
    if market_cap >= 2e9:
        return "moderate"
    if market_cap >= 500e6:
        return "low_moderate"
    if market_cap >= 100e6:
        return "low"
    return "very_low"


def _get_profitability_profile(
    profit_margin: float | None,
    roe: float | None,
) -> str:
    if profit_margin is None and roe is None:
        return "mixed"
    if profit_margin is not None and profit_margin > 0.1:
        return "profitable"
    if roe is not None and roe > 0.15:
        return "profitable"
    if profit_margin is not None and profit_margin < 0:
        return "unprofitable"
    return "mixed"


def _get_leverage_profile(debt_to_equity: float | None) -> str:
    if debt_to_equity is None:
        return "moderate"
    if debt_to_equity <= 0.3:
        return "very_low"
    if debt_to_equity <= 0.7:
        return "low"
    if debt_to_equity <= 1.5:
        return "moderate"
    if debt_to_equity <= 3.0:
        return "high"
    return "very_high"


def build_ticker_metadata(ticker: str) -> dict | None:
    finnhub_data = fetch_ticker_details_from_finnhub(ticker)
    if not finnhub_data:
        finnhub_data = fetch_ticker_details_from_polygon(ticker)
        if not finnhub_data:
            return None

    market_cap = finnhub_data.get("market_cap")
    volatility = fetch_volatility_proxy(ticker, 30)
    float_shares = fetch_float_shares_from_finnhub(ticker)

    market_cap_bucket = _get_market_cap_bucket(market_cap)
    profitability_profile = "mixed"
    leverage_profile = "moderate"

    spread_proxy = None
    if finnhub_data.get("avg_daily_dollar_volume"):
        spread_proxy = 0.001

    return {
        "ticker": ticker.upper(),
        "company_name": finnhub_data.get("company_name"),
        "exchange": finnhub_data.get("exchange"),
        "sector": finnhub_data.get("sector"),
        "industry": finnhub_data.get("industry"),
        "market_cap": market_cap,
        "market_cap_bucket": market_cap_bucket,
        "float_shares": float_shares,
        "avg_daily_dollar_volume": finnhub_data.get("avg_daily_dollar_volume"),
        "beta": finnhub_data.get("beta"),
        "volatility_proxy": volatility,
        "profitability_profile": profitability_profile,
        "leverage_profile": leverage_profile,
        "spread_proxy": spread_proxy,
        "updated_at": datetime.utcnow().isoformat(),
    }


def upsert_ticker_metadata(supabase: Client, ticker: str) -> dict | None:
    metadata = build_ticker_metadata(ticker)
    if not metadata:
        return None

    existing = (
        supabase.table("ticker_metadata")
        .select("id, ticker")
        .eq("ticker", ticker.upper())
        .limit(1)
        .execute()
        .data
    )

    if existing:
        supabase.table("ticker_metadata").update(metadata).eq(
            "ticker", ticker.upper()
        ).execute()
        return metadata

    supabase.table("ticker_metadata").insert(metadata).execute()
    return metadata


def refresh_all_positions_metadata(user_id: str) -> int:
    supabase = get_supabase_admin()

    positions = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("user_id", user_id)
        .execute()
        .data
    )

    updated = 0
    for position in positions:
        ticker = position.get("ticker")
        if ticker:
            result = upsert_ticker_metadata(supabase, ticker)
            if result:
                updated += 1

    return updated
