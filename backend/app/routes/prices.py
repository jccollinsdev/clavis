from fastapi import APIRouter, Request, HTTPException, Depends, Query
from datetime import datetime
from ..services.polygon import (
    fetch_price_history,
    fetch_aggs,
    history_covers_days,
    normalize_price_history,
    store_prices,
)

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("/{ticker}")
async def get_price_history(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = Depends(get_user_id),
):
    history = fetch_price_history(ticker.upper(), days)
    if history and history_covers_days(history, days):
        return {"ticker": ticker.upper(), "prices": history}

    aggs = fetch_aggs(ticker.upper(), days)
    if not aggs:
        return {"ticker": ticker.upper(), "prices": history}

    formatted_prices = [
        {
            "ticker": ticker.upper(),
            "price": agg["c"],
            "recorded_at": datetime.fromtimestamp(agg["t"] / 1000).isoformat(),
        }
        for agg in aggs
    ]
    store_prices(ticker.upper(), aggs)
    return {
        "ticker": ticker.upper(),
        "prices": normalize_price_history(formatted_prices),
    }
