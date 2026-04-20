import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from ..pipeline.scheduler import (
    SP500_BACKFILL_TRIGGER,
    SYSTEM_SP500_USER_ID,
    create_sp500_backfill_run,
    run_sp500_backfill_worker,
)
from ..services.supabase import get_supabase


def _backend_root() -> str:
    return str(Path(__file__).resolve().parents[2])


def _get_active_run() -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("analysis_runs")
        .select(
            "id, status, current_stage, current_stage_message, error_message, "
            "started_at, completed_at, positions_processed"
        )
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .eq("triggered_by", SP500_BACKFILL_TRIGGER)
        .in_("status", ["queued", "running"])
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _get_run(run_id: str) -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("analysis_runs")
        .select(
            "id, status, current_stage, current_stage_message, error_message, "
            "started_at, completed_at, positions_processed, events_processed, "
            "overall_portfolio_grade, triggered_by"
        )
        .eq("id", run_id)
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .eq("triggered_by", SP500_BACKFILL_TRIGGER)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _start(args: argparse.Namespace) -> int:
    existing = _get_active_run()
    if existing:
        print(
            json.dumps(
                {
                    "status": "already_running",
                    "analysis_run_id": existing["id"],
                    "current_stage": existing.get("current_stage"),
                    "current_stage_message": existing.get("current_stage_message"),
                }
            )
        )
        return 0

    run = create_sp500_backfill_run(
        requested_by_user_id=SYSTEM_SP500_USER_ID,
        job_type=args.job_type,
        limit=args.limit,
        batch_size=args.batch_size,
    )
    run_id = run["id"]
    log_path = args.log_path or f"/tmp/clavis_sp500_backfill_{run_id}.log"
    command = [
        sys.executable,
        "-m",
        "app.scripts.sp500_backfill",
        "worker",
        "--run-id",
        run_id,
        "--job-type",
        args.job_type,
        "--batch-size",
        str(args.batch_size),
    ]
    if args.limit is not None:
        command.extend(["--limit", str(args.limit)])
    if args.skip_structural:
        command.append("--skip-structural")

    worker_env = os.environ.copy()
    worker_env["PYTHONUNBUFFERED"] = "1"
    with open(log_path, "ab") as log_file:
        process = subprocess.Popen(
            command,
            cwd=_backend_root(),
            env=worker_env,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    print(
        json.dumps(
            {
                "status": "queued",
                "analysis_run_id": run_id,
                "pid": process.pid,
                "log_path": log_path,
            }
        )
    )
    return 0


def _worker(args: argparse.Namespace) -> int:
    run_sp500_backfill_worker(
        args.run_id,
        requested_by_user_id=SYSTEM_SP500_USER_ID,
        limit=args.limit,
        job_type=args.job_type,
        batch_size=args.batch_size,
        skip_structural=args.skip_structural,
    )
    return 0


def _status(args: argparse.Namespace) -> int:
    run = _get_run(args.run_id)
    if not run:
        print(json.dumps({"status": "not_found", "analysis_run_id": args.run_id}))
        return 1
    print(json.dumps(run))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage S&P 500 backfill runs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--limit", type=int, default=None)
    start_parser.add_argument("--job-type", default="backfill")
    start_parser.add_argument("--batch-size", type=int, default=4)
    start_parser.add_argument("--log-path", default=None)
    start_parser.add_argument("--skip-structural", action="store_true", default=False)
    start_parser.set_defaults(func=_start)

    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument("--run-id", required=True)
    worker_parser.add_argument("--limit", type=int, default=None)
    worker_parser.add_argument("--job-type", default="backfill")
    worker_parser.add_argument("--batch-size", type=int, default=4)
    worker_parser.add_argument("--skip-structural", action="store_true", default=False)
    worker_parser.set_defaults(func=_worker)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--run-id", required=True)
    status_parser.set_defaults(func=_status)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
