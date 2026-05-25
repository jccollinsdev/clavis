from __future__ import annotations

from typing import Any

from app.pipeline.scheduler import enqueue_analysis_run
from app.services.ticker_cache_service import refresh_ticker_snapshot


async def run_for_user(supabase, user_id: str) -> dict[str, Any]:
    positions = (
        supabase.table("positions")
        .select("id,ticker,outside_universe")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    tickers = [
        str(position.get("ticker") or "").upper()
        for position in positions
        if position.get("ticker") and not position.get("outside_universe")
    ]
    refreshed = 0
    failed: list[dict[str, str]] = []
    for ticker in sorted(set(tickers)):
        try:
            refresh_ticker_snapshot(
                supabase,
                ticker=ticker,
                job_type="manual_refresh",
                requested_by_user_id=user_id,
            )
            refreshed += 1
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})

    analysis_run = None
    if positions:
        analysis_run = await enqueue_analysis_run(
            user_id,
            "onboarding",
            target_position_id=None,
            target_tickers=tickers or None,
            allow_parallel_runs=True,
        )

    return {
        "status": "completed" if not failed else "failed",
        "items_processed": refreshed,
        "items_failed": len(failed),
        "analysis_run": analysis_run,
        "failed": failed,
    }
