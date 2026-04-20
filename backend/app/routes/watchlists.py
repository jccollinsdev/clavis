from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..services.supabase import get_supabase
from ..services.ticker_cache_service import (
    get_default_watchlist_detail,
    get_or_create_default_watchlist,
    require_supported_ticker,
)

router = APIRouter()


class WatchlistItemCreate(BaseModel):
    ticker: str


def get_user_id(request: Request) -> str:
    return request.state.user_id


@router.get("")
async def get_watchlists(user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    watchlist = get_default_watchlist_detail(supabase, user_id)
    return {"watchlists": [watchlist], "message": "ok"}


@router.post("/default/items")
async def add_to_default_watchlist(
    payload: WatchlistItemCreate, user_id: str = Depends(get_user_id)
):
    supabase = get_supabase()
    supported = require_supported_ticker(supabase, payload.ticker)
    watchlist = get_or_create_default_watchlist(supabase, user_id)

    existing = (
        supabase.table("watchlist_items")
        .select("id")
        .eq("watchlist_id", watchlist["id"])
        .eq("ticker", supported["ticker"])
        .limit(1)
        .execute()
        .data
    )
    if not existing:
        (
            supabase.table("watchlist_items")
            .insert({"watchlist_id": watchlist["id"], "ticker": supported["ticker"]})
            .execute()
        )

    return get_default_watchlist_detail(supabase, user_id)


@router.delete("/default/items/{ticker}")
async def remove_from_default_watchlist(
    ticker: str, user_id: str = Depends(get_user_id)
):
    supabase = get_supabase()
    watchlist = get_or_create_default_watchlist(supabase, user_id)
    result = (
        supabase.table("watchlist_items")
        .delete()
        .eq("watchlist_id", watchlist["id"])
        .eq("ticker", ticker.upper())
        .execute()
    )
    if result.data is None:
        raise HTTPException(404, "Watchlist item not found")
    return get_default_watchlist_detail(supabase, user_id)
