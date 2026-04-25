import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel

from ..services.snaptrade import (
    disconnect_brokerage,
    generate_connection_portal_link,
    get_brokerage_status,
    sync_brokerage_holdings,
    update_brokerage_settings,
)
from ..services.supabase import get_supabase
from ..services.ticker_cache_service import refresh_ticker_snapshot

logger = logging.getLogger(__name__)
router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


class BrokerageConnectRequest(BaseModel):
    broker: str | None = None
    reconnect_connection_id: str | None = None


class BrokerageSyncRequest(BaseModel):
    refresh_remote: bool = False


class BrokerageSettingsUpdate(BaseModel):
    auto_sync_enabled: bool


@router.get("/status")
async def brokerage_status(user_id: str = Depends(get_user_id)):
    return get_brokerage_status(user_id)


@router.post("/connect")
async def brokerage_connect(
    payload: BrokerageConnectRequest, user_id: str = Depends(get_user_id)
):
    logger.info("brokerage_connect user_id=%s broker=%s reconnect=%s", user_id, payload.broker, payload.reconnect_connection_id)
    try:
        result = generate_connection_portal_link(
            user_id,
            broker=payload.broker,
            reconnect=payload.reconnect_connection_id,
        )
        logger.info("brokerage_connect success user_id=%s", user_id)
        return result
    except Exception as exc:
        logger.warning("brokerage_connect failed user_id=%s error=%s", user_id, exc)
        raise


@router.patch("/settings")
async def brokerage_settings(
    payload: BrokerageSettingsUpdate, user_id: str = Depends(get_user_id)
):
    return update_brokerage_settings(user_id, payload.auto_sync_enabled)


@router.post("/sync")
async def brokerage_sync(
    payload: BrokerageSyncRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    result = sync_brokerage_holdings(user_id, refresh_remote=payload.refresh_remote)
    supabase = get_supabase()
    for ticker in result.get("tickers_to_refresh", []):
        background_tasks.add_task(
            refresh_ticker_snapshot,
            supabase,
            ticker=ticker,
            job_type="manual_refresh",
            requested_by_user_id=user_id,
        )
    return result


@router.delete("/disconnect")
async def brokerage_disconnect(user_id: str = Depends(get_user_id)):
    return disconnect_brokerage(user_id)
