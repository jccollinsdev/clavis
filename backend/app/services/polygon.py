import os
import requests
import time
from threading import Lock
from supabase import create_client, Client
from datetime import datetime, timedelta
from ..config import get_settings

POLYGON_BASE_URL = "https://api.polygon.io/v2"
FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"

MAX_RETRIES = 5
RETRY_BASE_DELAY = 5.0
_MIN_CALL_SPACING = 20.0

_last_polygon_call = 0.0
_polygon_rate_limit_lock = Lock()
_polygon_request_lock = Lock()


def _rate_limit_polygon():
    global _last_polygon_call
    with _polygon_rate_limit_lock:
        now = time.monotonic()
        elapsed = now - _last_polygon_call
        if elapsed < _MIN_CALL_SPACING:
            time.sleep(_MIN_CALL_SPACING - elapsed)
        _last_polygon_call = time.monotonic()


def _retry_request(fn, *args, **kwargs):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            result = fn(*args, **kwargs)
            if hasattr(result, "status_code"):
                if result.status_code == 429:
                    delay = RETRY_BASE_DELAY * (2**attempt)
                    print(
                        f"Polygon 429 rate limit, attempt {attempt + 1}, sleeping {delay:.1f}s"
                    )
                    time.sleep(delay)
                    last_exc = Exception(f"429 rate limit on attempt {attempt + 1}")
                    continue
                if result.status_code == 500 or result.status_code == 503:
                    delay = RETRY_BASE_DELAY * (2**attempt)
                    time.sleep(delay)
                    last_exc = Exception(
                        f"{result.status_code} server error on attempt {attempt + 1}"
                    )
                    continue
                if result.status_code == 401 or result.status_code == 403:
                    print(
                        f"Polygon auth error {result.status_code} for {kwargs.get('url', 'unknown')}"
                    )
                    return result
            return result
        except Exception as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                time.sleep(delay)
    if last_exc:
        raise last_exc
    return None


def polygon_get(url: str, *, params: dict | None = None, timeout: int = 15):
    """Perform a Polygon request under a strict 20s global gate."""
    with _polygon_request_lock:
        _rate_limit_polygon()
        return _retry_request(requests.get, url, params=params, timeout=timeout)


def get_polygon_client() -> str:
    return get_settings().polygon_api_key


def get_finnhub_client() -> str:
    return get_settings().finnhub_api_key


def fetch_current_price_from_finnhub(ticker: str) -> float | None:
    api_key = get_finnhub_client()
    if not api_key:
        return None

    try:
        resp = requests.get(
            FINNHUB_QUOTE_URL,
            params={"symbol": ticker.upper(), "token": api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        current = data.get("c")
        previous_close = data.get("pc")
        if isinstance(current, (int, float)) and current > 0:
            return float(current)
        if isinstance(previous_close, (int, float)) and previous_close > 0:
            return float(previous_close)
        return None
    except Exception as e:
        print(f"Error fetching Finnhub price for {ticker}: {e}")
        return None


def fetch_current_price(ticker: str) -> float | None:
    api_key = get_polygon_client()
    if not api_key:
        print("No Polygon API key configured, falling back to Finnhub")
        return fetch_current_price_from_finnhub(ticker)

    try:
        url = f"{POLYGON_BASE_URL}/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}"
        params = {"apiKey": api_key}
        resp = polygon_get(url, params=params, timeout=10)
        if resp is None:
            return fetch_current_price_from_finnhub(ticker)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK" and "ticker" in data:
                price = data["ticker"].get("lastTrade", {}).get("p")
                if price:
                    return price
        elif resp.status_code == 403:
            print(
                f"Polygon snapshot not authorized for {ticker}, falling back to Finnhub"
            )
        return fetch_current_price_from_finnhub(ticker)
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return fetch_current_price_from_finnhub(ticker)


def fetch_aggs(ticker: str, days: int = 30) -> list[dict]:
    api_key = get_polygon_client()
    if not api_key:
        print(f"No Polygon API key configured")
        return []

    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=days)

    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker.upper()}/range/1/day/{from_date}/{to_date}"
        params = {
            "apiKey": api_key,
            "adjusted": "true",
            "sort": "asc",
            "limit": 500,
        }
        resp = polygon_get(url, params=params, timeout=15)
        if resp is None:
            print(f"All retries exhausted for Polygon aggs for {ticker}")
            return []
        if resp.status_code == 200:
            data = resp.json()
            if data.get("results"):
                return data["results"]
        return []
    except Exception as e:
        print(f"Error fetching aggs for {ticker}: {e}")
        return []


def update_position_prices(positions: list[dict]) -> None:
    supabase: Client = create_client(
        os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )

    for position in positions:
        ticker = position.get("ticker")
        position_id = position.get("id")
        if not ticker or not position_id:
            continue

        price = fetch_current_price(ticker)
        if price:
            supabase.table("positions").update({"current_price": price}).eq(
                "id", position_id
            ).execute()
            print(f"Updated {ticker} price to ${price}")

            supabase.table("prices").insert(
                {
                    "ticker": ticker.upper(),
                    "price": price,
                }
            ).execute()


def store_prices(ticker: str, prices: list[dict]) -> None:
    supabase: Client = create_client(
        os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )

    for bar in prices:
        recorded_at = (
            datetime.fromtimestamp(bar["t"] / 1000)
            if isinstance(bar["t"], int)
            else bar["t"]
        )
        supabase.table("prices").insert(
            {
                "ticker": ticker.upper(),
                "price": bar["c"],
                "recorded_at": recorded_at.isoformat(),
            }
        ).execute()


def normalize_price_history(history: list[dict]) -> list[dict]:
    daily_prices: dict[str, dict] = {}

    for entry in history:
        recorded_at = entry.get("recorded_at")
        if not recorded_at:
            continue

        try:
            timestamp = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        except ValueError:
            continue

        day_key = timestamp.date().isoformat()
        previous = daily_prices.get(day_key)
        if previous is None or recorded_at > previous["recorded_at"]:
            daily_prices[day_key] = {
                "ticker": entry.get("ticker", "").upper(),
                "price": entry.get("price"),
                "recorded_at": timestamp.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).isoformat(),
            }

    return [daily_prices[key] for key in sorted(daily_prices.keys())]


def history_covers_days(history: list[dict], days: int) -> bool:
    if not history:
        return False

    try:
        first = datetime.fromisoformat(history[0]["recorded_at"].replace("Z", "+00:00"))
        last = datetime.fromisoformat(history[-1]["recorded_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return False

    # Allow a few missing calendar days for weekends/market holidays.
    required_span = max(days - 4, 1)
    return (last.date() - first.date()).days >= required_span


def fetch_price_history(ticker: str, days: int = 30) -> list[dict]:
    supabase: Client = create_client(
        os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    result = (
        supabase.table("prices")
        .select("*")
        .eq("ticker", ticker.upper())
        .gte("recorded_at", cutoff)
        .order("recorded_at", desc=False)
        .execute()
    )
    return normalize_price_history(result.data or [])
