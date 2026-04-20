import requests

from ..config import get_settings

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"


def fetch_current_price_from_finnhub(ticker: str) -> float | None:
    api_key = get_settings().finnhub_api_key
    if not api_key:
        return None

    try:
        resp = requests.get(
            FINNHUB_QUOTE_URL,
            params={"symbol": ticker.upper(), "token": api_key},
            timeout=5,
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
