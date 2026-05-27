from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.pipeline.scheduler import run_sp500_full_ai_analysis_fast
from app.scripts.audit_snapshot_completeness import render_markdown, run_audit
from app.services.supabase import get_supabase
from app.services.ticker_cache_service import refresh_ticker_snapshot, snapshot_is_schema_complete


def _load_active_universe(supabase) -> dict[str, dict[str, Any]]:
    rows = (
        supabase.table("ticker_universe")
        .select("ticker,index_membership,is_active")
        .eq("is_active", True)
        .order("ticker")
        .execute()
        .data
        or []
    )
    return {
        str(row.get("ticker") or "").upper(): row
        for row in rows
        if str(row.get("ticker") or "").strip()
    }


def _build_output_summary(
    *,
    label: str,
    requested_tickers: list[str],
    attempted_tickers: list[str],
    skipped_complete: list[str],
    sp500_result: dict[str, Any] | None,
    other_results: list[dict[str, Any]],
    before_report: dict[str, Any],
    after_report: dict[str, Any],
    started_at: datetime,
) -> dict[str, Any]:
    after_latest = set(after_report["latest_snapshot_by_ticker"])
    after_incomplete = set(after_report["rows_marked_partial_selected_as_latest"])
    completed_tickers = sorted(
        [
            ticker
            for ticker in requested_tickers
            if ticker in after_latest and ticker not in after_incomplete
        ]
    )
    failed_tickers = sorted(set(attempted_tickers) - set(completed_tickers))
    return {
        "label": label,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "requested_tickers": requested_tickers,
        "attempted_tickers": attempted_tickers,
        "skipped_complete_tickers": skipped_complete,
        "completed_tickers": completed_tickers,
        "failed_tickers": failed_tickers,
        "sp500_result": sp500_result,
        "other_results": other_results,
        "before": {
            "complete_5d_count": before_report["complete_5d_count"],
            "latest_snapshot_count": before_report["latest_snapshot_count"],
            "rows_marked_partial_selected_as_latest": before_report[
                "rows_marked_partial_selected_as_latest"
            ],
        },
        "after": {
            "complete_5d_count": after_report["complete_5d_count"],
            "latest_snapshot_count": after_report["latest_snapshot_count"],
            "rows_marked_partial_selected_as_latest": after_report[
                "rows_marked_partial_selected_as_latest"
            ],
        },
    }


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a resumable completeness recovery backfill."
    )
    parser.add_argument("--tickers", default=None, help="Comma-separated ticker list.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--job-type", default="backfill")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--label", default="snapshot-completeness")
    parser.add_argument("--resume", action="store_true", default=False)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--force", action="store_true", default=False)
    parser.add_argument("--skip-structural", action="store_true", default=False)
    parser.add_argument("--state-file", default=None)
    parser.add_argument("--output", default=None, help="Markdown summary output path.")
    parser.add_argument("--json-output", default=None, help="JSON summary output path.")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    supabase = get_supabase()
    universe_map = _load_active_universe(supabase)
    requested_tickers = sorted(universe_map)
    if args.tickers:
        requested = {
            ticker.strip().upper()
            for ticker in args.tickers.split(",")
            if ticker.strip()
        }
        requested_tickers = [ticker for ticker in requested_tickers if ticker in requested]
    if args.limit is not None:
        requested_tickers = requested_tickers[: max(0, args.limit)]

    before_report = run_audit(tickers=requested_tickers)
    latest_present = set(before_report["latest_snapshot_by_ticker"])
    incomplete_tickers = sorted(
        (set(requested_tickers) - latest_present)
        | set(before_report["rows_marked_partial_selected_as_latest"])
    )
    target_tickers = requested_tickers if args.force else incomplete_tickers

    state_path = Path(
        args.state_file
        or f"/Users/sansarkarki/Documents/Clavis/docs/snapshot_audit_outputs/{args.label}_state.json"
    )
    completed_from_state: set[str] = set()
    if args.resume and state_path.exists():
        try:
            completed_from_state = {
                str(ticker).upper()
                for ticker in json.loads(state_path.read_text(encoding="utf-8")).get(
                    "completed_tickers", []
                )
            }
        except Exception:
            completed_from_state = set()
    if completed_from_state:
        target_tickers = [ticker for ticker in target_tickers if ticker not in completed_from_state]

    skipped_complete = [ticker for ticker in requested_tickers if ticker not in target_tickers]
    sp500_tickers = [
        ticker
        for ticker in target_tickers
        if universe_map.get(ticker, {}).get("index_membership") == "SP500"
    ]
    other_tickers = [
        ticker
        for ticker in target_tickers
        if universe_map.get(ticker, {}).get("index_membership") != "SP500"
    ]

    if args.dry_run:
        payload = {
            "label": args.label,
            "requested_tickers": requested_tickers,
            "target_tickers": target_tickers,
            "sp500_tickers": sp500_tickers,
            "other_tickers": other_tickers,
            "before_complete_5d_count": before_report["complete_5d_count"],
            "before_partial_latest": before_report["rows_marked_partial_selected_as_latest"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    attempted_tickers: list[str] = []
    sp500_result: dict[str, Any] | None = None
    other_results: list[dict[str, Any]] = []

    if sp500_tickers:
        attempted_tickers.extend(sp500_tickers)
        sp500_result = asyncio.run(
            run_sp500_full_ai_analysis_fast(
                job_type=args.job_type,
                batch_size=max(1, args.batch_size),
                tickers_override=sp500_tickers,
                skip_structural=args.skip_structural,
            )
        )

    for ticker in other_tickers:
        attempted_tickers.append(ticker)
        try:
            result = refresh_ticker_snapshot(
                supabase,
                ticker=ticker,
                job_type=args.job_type,
                requested_by_user_id=None,
            )
            other_results.append(
                {
                    "ticker": ticker,
                    "status": result.get("status"),
                    "snapshot_complete": snapshot_is_schema_complete(result.get("snapshot") or {}),
                }
            )
        except Exception as exc:
            other_results.append({"ticker": ticker, "status": "failed", "error": str(exc)})

    after_report = run_audit(tickers=requested_tickers)
    summary = _build_output_summary(
        label=args.label,
        requested_tickers=requested_tickers,
        attempted_tickers=attempted_tickers,
        skipped_complete=skipped_complete,
        sp500_result=sp500_result,
        other_results=other_results,
        before_report=before_report,
        after_report=after_report,
        started_at=started_at,
    )
    _write_state(state_path, summary)

    markdown_lines = [
        f"# Completeness Backfill Summary — {args.label}",
        "",
        f"- Started at: `{summary['started_at']}`",
        f"- Finished at: `{summary['finished_at']}`",
        f"- Requested tickers: `{len(requested_tickers)}`",
        f"- Attempted tickers: `{len(attempted_tickers)}`",
        f"- Completed tickers: `{len(summary['completed_tickers'])}`",
        f"- Failed tickers: `{len(summary['failed_tickers'])}`",
        "",
        "## Before Audit",
        "",
        render_markdown(before_report).rstrip(),
        "",
        "## After Audit",
        "",
        render_markdown(after_report).rstrip(),
        "",
        "## Run Summary",
        "",
        json.dumps(summary, indent=2, sort_keys=True),
        "",
    ]
    markdown = "\n".join(markdown_lines)
    print(markdown)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
