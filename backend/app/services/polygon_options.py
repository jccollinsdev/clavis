from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from .polygon import polygon_get
from ..config import get_settings


POLYGON_OPTIONS_SNAPSHOT_URL = "https://api.polygon.io/v3/snapshot/options"
DEFAULT_PAGE_LIMIT = 250
MAX_PAGES = 3


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _underlying_price(contract: dict[str, Any]) -> float | None:
    underlying = contract.get("underlying_asset") or {}
    for field in ("price", "value"):
        price = _float(underlying.get(field))
        if price is not None and price > 0:
            return price
    quote = underlying.get("last_quote") or {}
    bid = _float(quote.get("bid"))
    ask = _float(quote.get("ask"))
    if bid is not None and ask is not None and bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    return _float(quote.get("midpoint"))


def _candidate_key(
    contract: dict[str, Any],
    *,
    target_expiration: date,
) -> tuple[float, float, float]:
    details = contract.get("details") or {}
    expiration = _parse_date(details.get("expiration_date"))
    underlying_price = _underlying_price(contract)
    strike = _float(details.get("strike_price"))
    if expiration is None or underlying_price is None or strike is None or underlying_price <= 0:
        return (float("inf"), float("inf"), float("inf"))
    distance_days = abs((expiration - target_expiration).days)
    moneyness_gap = abs(strike - underlying_price) / underlying_price
    open_interest = -(_float(contract.get("open_interest")) or 0.0)
    return (distance_days, moneyness_gap, open_interest)


def fetch_near_term_implied_vol_30d(
    ticker: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    api_key = get_settings().polygon_api_key
    if not api_key:
        return None

    upper = ticker.upper()
    as_of = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    target_expiration = as_of.date() + timedelta(days=30)
    url = f"{POLYGON_OPTIONS_SNAPSHOT_URL}/{upper}"
    params = {
        "apiKey": api_key,
        "limit": DEFAULT_PAGE_LIMIT,
        "sort": "expiration_date",
        "order": "asc",
    }

    best_contract: dict[str, Any] | None = None
    page_count = 0
    next_url: str | None = url
    next_params: dict[str, Any] | None = params

    while next_url and page_count < MAX_PAGES:
        response = polygon_get(next_url, params=next_params, timeout=15)
        if response is None or response.status_code != 200:
            return None
        payload = response.json() or {}
        results = payload.get("results") or []
        for contract in results:
            implied_vol = _float(contract.get("implied_volatility"))
            if implied_vol is None or implied_vol <= 0:
                continue
            if best_contract is None or _candidate_key(
                contract,
                target_expiration=target_expiration,
            ) < _candidate_key(best_contract, target_expiration=target_expiration):
                best_contract = contract

        next_url = payload.get("next_url")
        next_params = {"apiKey": api_key} if next_url else None
        page_count += 1

    if best_contract is None:
        return None

    details = best_contract.get("details") or {}
    return {
        "implied_vol_30d": round(_float(best_contract.get("implied_volatility")) or 0.0, 4),
        "expiration_date": details.get("expiration_date"),
        "strike_price": _float(details.get("strike_price")),
        "contract_type": details.get("contract_type"),
        "underlying_price": _underlying_price(best_contract),
    }
