from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from ..services.alert_payloads import enrich_alert_rows
from ..services.digest_selection import select_latest_trading_day_digest
from ..services.supabase import get_supabase
from ..services.ticker_cache_service import enrich_positions_with_ticker_cache
from .analysis_runs import _enrich_run
from .holdings import refresh_position_price

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


def _enrich_positions(
    positions: list[dict], supabase, background_tasks: BackgroundTasks
):
    for pos in positions:
        if pos.get("current_price") is None:
            background_tasks.add_task(refresh_position_price, pos["id"], pos["ticker"])
    return enrich_positions_with_ticker_cache(positions, supabase)


def _latest_digest_and_run(supabase, user_id: str):
    now = datetime.utcnow()

    latest_run_result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    latest_run = latest_run_result.data[0] if latest_run_result.data else None
    latest_run_digest = None
    if latest_run:
        latest_run_digest = (
            supabase.table("digests")
            .select("id, overall_grade, generated_at")
            .eq("analysis_run_id", latest_run["id"])
            .limit(1)
            .execute()
            .data
        )

    result = (
        supabase.table("digests")
        .select("*")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(12)
        .execute()
    )

    if not result.data:
        return None, _enrich_run(latest_run, latest_run_digest) if latest_run else None

    saved_digest = result.data[0]
    digest = select_latest_trading_day_digest(result.data, now)
    digest_run = None
    digest_run_digest = None
    if digest.get("analysis_run_id"):
        digest_run_result = (
            supabase.table("analysis_runs")
            .select("*")
            .eq("id", digest["analysis_run_id"])
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        digest_run = digest_run_result.data[0] if digest_run_result.data else None
        if digest_run:
            digest_run_digest = (
                supabase.table("digests")
                .select("id, overall_grade, generated_at")
                .eq("analysis_run_id", digest_run["id"])
                .limit(1)
                .execute()
                .data
            )

    analysis_run = (
        _enrich_run(digest_run, digest_run_digest)
        if digest_run
        else _enrich_run(latest_run, latest_run_digest)
        if latest_run
        else None
    )
    if digest is None:
        digest = saved_digest
    digest = {
        **digest,
        "saved_digest": saved_digest,
        "generated_digest": None,
    }
    return digest, analysis_run


def _clean_string_list(values):
    return [
        value for value in (values or []) if isinstance(value, str) and value.strip()
    ]


def _clean_risk_driver(driver: dict) -> dict:
    return {
        **driver,
        "tickers": _clean_string_list(driver.get("tickers")),
        "clusters": _clean_string_list(driver.get("clusters")),
        "issues": _clean_string_list(driver.get("issues")),
    }


def _portfolio_score_fields(digest: dict | None) -> dict[str, object | None]:
    if not digest:
        return {
            "overall_score": None,
            "overall_grade": None,
            "score_source": None,
            "score_as_of": None,
            "score_version": None,
        }

    return {
        "overall_score": digest.get("overall_score"),
        "overall_grade": digest.get("overall_grade"),
        "score_source": "digest",
        "score_as_of": digest.get("generated_at"),
        "score_version": digest.get("analysis_run_id"),
    }


@router.get("")
async def get_dashboard(
    response: Response,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"

    supabase = get_supabase()
    positions = (
        supabase.table("positions").select("*").eq("user_id", user_id).execute().data
        or []
    )
    positions = _enrich_positions(positions, supabase, background_tasks)

    alerts = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    alerts = enrich_alert_rows(alerts)

    portfolio_risk_snapshot = (
        supabase.table("portfolio_risk_snapshots")
        .select("*")
        .eq("user_id", user_id)
        .order("as_of_date", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if portfolio_risk_snapshot:
        snapshot = dict(portfolio_risk_snapshot[0])
        snapshot["danger_clusters"] = _clean_string_list(
            snapshot.get("danger_clusters")
        )
        snapshot["top_risk_drivers"] = [
            _clean_risk_driver(driver)
            for driver in (snapshot.get("top_risk_drivers") or [])
            if isinstance(driver, dict)
        ]
    else:
        snapshot = None

    digest, analysis_run = _latest_digest_and_run(supabase, user_id)
    portfolio_score_fields = _portfolio_score_fields(digest)

    return {
        "digest": digest,
        "saved_digest": digest.get("saved_digest") if digest else None,
        "generated_digest": digest.get("generated_digest") if digest else None,
        "analysis_run": analysis_run,
        "positions": positions,
        "alerts": alerts,
        "portfolio_risk_snapshot": snapshot,
        **portfolio_score_fields,
        "message": "ok",
    }
