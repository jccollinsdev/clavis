import asyncio
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


def _fetch_price_history_sync(ticker: str, days: int) -> dict:
    """All blocking Polygon work for the price history endpoint.

    Runs in a thread via asyncio.to_thread so the rate-limit sleep in
    _rate_limit_polygon() does not block the uvicorn event loop.
    """
    history = fetch_price_history(ticker, days)
    if history and history_covers_days(history, days):
        return {"ticker": ticker, "prices": history}

    aggs = fetch_aggs(ticker, days)
    if not aggs:
        return {"ticker": ticker, "prices": history}

    formatted_prices = [
        {
            "ticker": ticker,
            "price": agg["c"],
            "recorded_at": datetime.fromtimestamp(agg["t"] / 1000).isoformat(),
        }
        for agg in aggs
    ]
    store_prices(ticker, aggs)
    return {"ticker": ticker, "prices": normalize_price_history(formatted_prices)}


@router.get("/{ticker}")
async def get_price_history(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365),
    user_id: str = Depends(get_user_id),
):
    return await asyncio.to_thread(_fetch_price_history_sync, ticker.upper(), days)
