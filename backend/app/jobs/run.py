from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable

from app.services.job_lock import PostgresAdvisoryLock
from app.services.job_runs import finish_job_run, start_job_run
from app.services.supabase import get_supabase


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    tier: str
    handler: Callable[[], Any]


def _macro_snapshot() -> dict:
    from app.jobs.macro_snapshot import run

    return run()


def _sector_snapshot() -> dict:
    from app.jobs.sector_snapshot import run

    return run()


def _composite_recompute() -> dict:
    from app.jobs.composite_recompute import run_from_env

    return run_from_env()


def _portfolio_rollup() -> dict:
    from app.jobs.portfolio_rollup import run

    return run()


def _earnings_calendar() -> dict:
    from app.jobs.earnings_calendar import run_from_env

    return run_from_env()


def _peer_groups() -> dict:
    from app.jobs.peer_groups import run_from_env

    return run_from_env()


def _sector_medians() -> dict:
    from app.jobs.sector_medians import run_from_env

    return run_from_env()


def _event_fundamentals() -> dict:
    from app.jobs.event_fundamentals import run_from_env

    return run_from_env()


def _etf_holdings() -> dict:
    from app.jobs.etf_holdings import run_from_env

    return run_from_env()


def _macro_regression() -> dict:
    from app.jobs.macro_regression import run_from_env

    return run_from_env()


def _universe_audit() -> dict:
    from app.jobs.universe_audit import run_from_env

    return run_from_env()


def _backfill_14d() -> dict:
    from app.jobs.backfill_14d import run_from_env

    return run_from_env()


JOB_REGISTRY: dict[str, JobSpec] = {
    "daily_macro_snapshot": JobSpec("daily_macro_snapshot", "daily", _macro_snapshot),
    "daily_sector_snapshot": JobSpec("daily_sector_snapshot", "daily", _sector_snapshot),
    "daily_composite_recompute_universe": JobSpec(
        "daily_composite_recompute_universe", "daily", _composite_recompute
    ),
    "daily_portfolio_rollup_per_user": JobSpec(
        "daily_portfolio_rollup_per_user", "daily", _portfolio_rollup
    ),
    "daily_portfolio_rollup": JobSpec(
        "daily_portfolio_rollup", "daily", _portfolio_rollup
    ),
    "daily_earnings_calendar_refresh": JobSpec(
        "daily_earnings_calendar_refresh", "daily", _earnings_calendar
    ),
    "weekly_peer_groups_recompute": JobSpec(
        "weekly_peer_groups_recompute", "weekly", _peer_groups
    ),
    "weekly_sector_medians_recompute": JobSpec(
        "weekly_sector_medians_recompute", "weekly", _sector_medians
    ),
    "event_fundamentals_pull": JobSpec(
        "event_fundamentals_pull", "daily", _event_fundamentals
    ),
    "monthly_etf_holdings_refresh": JobSpec(
        "monthly_etf_holdings_refresh", "monthly", _etf_holdings
    ),
    "monthly_macro_regression_refresh": JobSpec(
        "monthly_macro_regression_refresh", "monthly", _macro_regression
    ),
    "weekly_universe_audit": JobSpec(
        "weekly_universe_audit", "weekly", _universe_audit
    ),
    "backfill_14d": JobSpec("backfill_14d", "manual", _backfill_14d),
}


def _system_scheduler_paused() -> bool:
    return str(os.getenv("PAUSE_SYSTEM_SCHEDULER") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def run_job(job_id: str, *, dry_run: bool = False) -> dict[str, Any]:
    spec = JOB_REGISTRY.get(job_id)
    if not spec:
        return {
            "status": "unknown_job",
            "job_id": job_id,
            "known_jobs": sorted(JOB_REGISTRY),
        }
    if dry_run:
        return {"status": "dry_run", "job_id": job_id, "tier": spec.tier}

    supabase = get_supabase()
    run_row = start_job_run(supabase, job_id=spec.job_id, tier=spec.tier)
    run_id = run_row.get("id")

    if spec.tier != "manual" and _system_scheduler_paused():
        return finish_job_run(
            supabase,
            run_id,
            status="skipped",
            items_skipped=1,
            metadata={"reason": "system_scheduler_paused"},
        )

    lock = PostgresAdvisoryLock(supabase, f"clavix_job:{spec.job_id}")

    try:
        if not lock.acquire():
            return finish_job_run(
                supabase,
                run_id,
                status="skipped_lock",
                items_skipped=1,
                metadata={"reason": "advisory_lock_held"},
            )

        raw_result = spec.handler()
        if inspect.isawaitable(raw_result):
            raw_result = await raw_result
        result = raw_result or {}
        status = str(result.get("status") or "completed")
        if status not in {"completed", "failed", "skipped"}:
            status = "completed" if status in {"ok", "success"} else "failed"

        return finish_job_run(
            supabase,
            run_id,
            status=status,
            items_processed=int(result.get("items_processed") or result.get("processed") or 0),
            items_skipped=int(result.get("items_skipped") or result.get("skipped") or 0),
            items_failed=int(result.get("items_failed") or result.get("failed") or 0),
            metadata=result.get("metadata"),
        )
    except Exception as exc:
        logger.exception("Job %s failed", spec.job_id)
        return finish_job_run(
            supabase,
            run_id,
            status="failed",
            items_failed=1,
            error_json={"message": str(exc), "type": exc.__class__.__name__},
        )
    finally:
        try:
            lock.release()
        except Exception:
            logger.exception("Failed to release advisory lock for %s", spec.job_id)


def run_job_sync(job_id: str) -> dict[str, Any]:
    return asyncio.run(run_job(job_id))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Clavix scheduled job once.")
    parser.add_argument("job_id", help="Registered job id to execute.")
    parser.add_argument("--dry-run", action="store_true", help="Validate job registration without doing work.")
    args = parser.parse_args(argv)

    result = asyncio.run(run_job(args.job_id, dry_run=args.dry_run))
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") not in {"failed", "unknown_job"} else 1


if __name__ == "__main__":
    sys.exit(main())
