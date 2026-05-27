from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from app.services.supabase import get_supabase


DIMENSION_SPECS = (
    ("financial_health", "financial_health"),
    ("news_sentiment", "news_sentiment_dim"),
    ("macro_exposure", "macro_exposure_dim"),
    ("sector_exposure", "sector_exposure"),
    ("volatility", "volatility"),
)
VALID_GRADES = {"AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "F"}


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _snapshot_methodology_priority(version: Any) -> int:
    value = str(version or "").lower()
    if value == "v2":
        return 5
    if "sp500-ai" in value:
        return 4
    if "deterministic" in value:
        return 3
    if value:
        return 2
    return 0


def _current_sort_key(row: dict[str, Any]) -> tuple:
    analysis_as_of = _parse_datetime(row.get("analysis_as_of"))
    updated_at = _parse_datetime(row.get("updated_at"))
    created_at = _parse_datetime(row.get("created_at"))
    return (
        analysis_as_of.timestamp() if analysis_as_of else float("-inf"),
        updated_at.timestamp() if updated_at else float("-inf"),
        created_at.timestamp() if created_at else float("-inf"),
        _snapshot_methodology_priority(row.get("methodology_version")),
        str(row.get("id") or ""),
    )


def _dimension_detail(snapshot: dict[str, Any], dimension: str, column: str) -> dict[str, Any]:
    dimension_inputs = _json_object(snapshot.get("dimension_inputs"))
    dimension_input = _json_object(dimension_inputs.get(dimension))
    limited_dimensions = {str(item) for item in _json_list(snapshot.get("limited_data_dimensions"))}
    value = snapshot.get(column)
    factor_breakdown = _json_object(snapshot.get("factor_breakdown"))
    ai_dimensions = _json_object(factor_breakdown.get("ai_dimensions"))
    legacy_value = ai_dimensions.get(dimension)
    if legacy_value is None and dimension == "financial_health":
        legacy_value = ai_dimensions.get("position_sizing")
    if legacy_value is None and dimension == "volatility":
        legacy_value = ai_dimensions.get("volatility_trend")

    limited_flag = bool(
        dimension_input.get("limited_data")
        or dimension_input.get("limited")
        or dimension in limited_dimensions
    )
    limited_reason = (
        dimension_input.get("limited_reason")
        or dimension_input.get("limited_data_reason")
        or dimension_input.get("reason")
    )
    has_structured_limited_reason = limited_flag and bool(str(limited_reason or "").strip())

    upstream_inputs_present = bool(dimension_input)
    if dimension == "news_sentiment":
        upstream_inputs_present = upstream_inputs_present or bool(
            dimension_input.get("weighted_score") is not None
            or dimension_input.get("article_count_7d")
            or dimension_input.get("volume_signal")
        )
    elif dimension == "macro_exposure":
        macro_regression = _json_object(factor_breakdown.get("macro_regression"))
        upstream_inputs_present = upstream_inputs_present or bool(
            macro_regression or ai_dimensions.get("macro_exposure") is not None
        )

    return {
        "value": value,
        "legacy_value": legacy_value,
        "limited_flag": limited_flag,
        "limited_reason": limited_reason,
        "complete": value is not None or has_structured_limited_reason,
        "missing_without_reason": value is None and not has_structured_limited_reason,
        "upstream_inputs_present": upstream_inputs_present,
    }


def _snapshot_schema_complete(snapshot: dict[str, Any] | None) -> bool:
    if not snapshot:
        return False
    if snapshot.get("composite_score") is None:
        return False
    if str(snapshot.get("grade") or "") not in VALID_GRADES:
        return False
    if not _parse_datetime(snapshot.get("analysis_as_of")):
        return False
    for dimension, column in DIMENSION_SPECS:
        if not _dimension_detail(snapshot, dimension, column)["complete"]:
            return False
    return True


def _preferred_sort_key(row: dict[str, Any]) -> tuple:
    return (
        1 if _snapshot_schema_complete(row) else 0,
        *_current_sort_key(row),
    )


def _load_all_rows(query_factory, *, page_size: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        page = query_factory(start, start + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def _chunked(items: list[str], size: int = 200) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def run_audit(*, tickers: list[str] | None = None, page_size: int = 1000) -> dict[str, Any]:
    supabase = get_supabase()
    snapshot_batch_size = 100
    news_batch_size = 50
    universe_query = (
        supabase.table("ticker_universe")
        .select("ticker,index_membership,is_active", count="exact")
        .eq("is_active", True)
        .order("ticker")
    )
    universe_rows = universe_query.execute().data or []
    active_universe = sorted(
        {
            str(row.get("ticker") or "").upper()
            for row in universe_rows
            if str(row.get("ticker") or "").strip()
        }
    )
    if tickers:
        requested = {ticker.strip().upper() for ticker in tickers if ticker.strip()}
        active_universe = [ticker for ticker in active_universe if ticker in requested]

    snapshot_columns = (
        "id,ticker,snapshot_type,snapshot_date,analysis_as_of,updated_at,created_at,"
        "financial_health,news_sentiment_dim,macro_exposure_dim,sector_exposure,volatility,"
        "composite_score,grade,methodology_version,dimension_inputs,dimension_last_refreshed,"
        "limited_data_dimensions,factor_breakdown,reasoning"
    )
    snapshots: list[dict[str, Any]] = []
    for batch in _chunked(active_universe, size=snapshot_batch_size):
        snapshots.extend(
            _load_all_rows(
                lambda start, end, batch=batch: (
                    supabase.table("ticker_risk_snapshots")
                    .select(snapshot_columns)
                    .in_("ticker", batch)
                    .order("analysis_as_of", desc=True)
                    .order("updated_at", desc=True)
                    .order("created_at", desc=True)
                    .range(start, end)
                ),
                page_size=page_size,
            )
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in snapshots:
        ticker = str(row.get("ticker") or "").upper()
        if ticker:
            grouped[ticker].append(row)
    for ticker in grouped:
        grouped[ticker] = sorted(grouped[ticker], key=_current_sort_key, reverse=True)

    news_rows: list[dict[str, Any]] = []
    for batch in _chunked(active_universe, size=news_batch_size):
        news_rows.extend(
            _load_all_rows(
                lambda start, end, batch=batch: (
                    supabase.table("shared_ticker_events")
                    .select(
                        "ticker,published_at,sentiment_score,source_tier,recency_weight,"
                        "source_weight,impact_tag,canonical_url,title"
                    )
                    .in_("ticker", batch)
                    .order("published_at", desc=True)
                    .range(start, end)
                ),
                page_size=page_size,
            )
        )
    news_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in news_rows:
        ticker = str(row.get("ticker") or "").upper()
        if ticker:
            news_by_ticker[ticker].append(row)

    now = datetime.now(timezone.utc)
    latest_selected: dict[str, dict[str, Any]] = {}
    preferred_selected: dict[str, dict[str, Any]] = {}
    duplicate_same_day_conflicts: list[str] = []
    newer_partial_over_complete: list[str] = []
    older_complete_exists: list[str] = []
    api_selection_mismatches: list[str] = []
    dimension_missing_samples: dict[str, list[str]] = defaultdict(list)
    dimension_missing_counts: Counter[str] = Counter()
    persistence_gap_counts: Counter[str] = Counter()
    generation_gap_counts: Counter[str] = Counter()
    legacy_only_counts: Counter[str] = Counter()
    selected_partial_without_reason: list[str] = []
    selected_rows_with_structured_limits: list[str] = []
    stale_counts = Counter({"over_24h": 0, "over_48h": 0, "over_7d": 0})
    methodology_missing_count = 0
    latest_timestamps: list[datetime] = []
    snapshot_type_counter: Counter[str] = Counter()

    for ticker in active_universe:
        rows = grouped.get(ticker, [])
        if not rows:
            continue
        current_latest = rows[0]
        preferred_latest = max(rows, key=_preferred_sort_key)
        latest_selected[ticker] = current_latest
        preferred_selected[ticker] = preferred_latest
        snapshot_type_counter[str(current_latest.get("snapshot_type") or "unknown")] += 1

        if current_latest.get("snapshot_date"):
            same_day = [
                row for row in rows if row.get("snapshot_date") == current_latest.get("snapshot_date")
            ]
            if len(same_day) > 1:
                duplicate_same_day_conflicts.append(ticker)

        if current_latest.get("id") != preferred_latest.get("id"):
            api_selection_mismatches.append(ticker)

        if not _snapshot_schema_complete(current_latest):
            selected_partial_without_reason.append(ticker)
            if any(_snapshot_schema_complete(row) for row in rows[1:]):
                older_complete_exists.append(ticker)
                newer_partial_over_complete.append(ticker)

        for dimension, column in DIMENSION_SPECS:
            detail = _dimension_detail(current_latest, dimension, column)
            if detail["complete"] and detail["value"] is None:
                selected_rows_with_structured_limits.append(f"{ticker}:{dimension}")
            if not detail["missing_without_reason"]:
                continue
            dimension_missing_counts[dimension] += 1
            if len(dimension_missing_samples[dimension]) < 15:
                dimension_missing_samples[dimension].append(ticker)
            if detail["legacy_value"] is not None:
                legacy_only_counts[dimension] += 1
            if detail["upstream_inputs_present"]:
                persistence_gap_counts[dimension] += 1
            else:
                if dimension == "news_sentiment":
                    recent_enriched = [
                        row
                        for row in news_by_ticker.get(ticker, [])
                        if (
                            _parse_datetime(row.get("published_at"))
                            and now - _parse_datetime(row.get("published_at")) <= timedelta(days=7)
                            and row.get("sentiment_score") is not None
                        )
                    ]
                    if recent_enriched:
                        persistence_gap_counts[dimension] += 1
                    else:
                        generation_gap_counts[dimension] += 1
                else:
                    generation_gap_counts[dimension] += 1

        if not _json_object(current_latest.get("dimension_inputs")):
            methodology_missing_count += 1

        latest_ts = _parse_datetime(current_latest.get("analysis_as_of"))
        if latest_ts:
            latest_timestamps.append(latest_ts)
            age = now - latest_ts
            if age.total_seconds() > 24 * 3600:
                stale_counts["over_24h"] += 1
            if age.total_seconds() > 48 * 3600:
                stale_counts["over_48h"] += 1
            if age.total_seconds() > 7 * 24 * 3600:
                stale_counts["over_7d"] += 1

    complete_latest_count = sum(
        1 for ticker in active_universe if _snapshot_schema_complete(latest_selected.get(ticker))
    )
    preferred_complete_count = sum(
        1 for ticker in active_universe if _snapshot_schema_complete(preferred_selected.get(ticker))
    )

    analysis_runs = (
        supabase.table("analysis_runs")
        .select(
            "id,user_id,status,triggered_by,current_stage,current_stage_message,error_message,"
            "started_at,completed_at,positions_processed,target_tickers",
            count="exact",
        )
        .eq("user_id", "00000000-0000-0000-0000-000000000001")
        .order("started_at", desc=True)
        .limit(25)
        .execute()
        .data
        or []
    )
    refresh_jobs = (
        supabase.table("ticker_refresh_jobs")
        .select("ticker,status,job_type,started_at,completed_at,error_message", count="exact")
        .order("started_at", desc=True)
        .limit(200)
        .execute()
        .data
        or []
    )

    return {
        "generated_at": now.isoformat(),
        "universe_count": len(active_universe),
        "universe_membership_counts": {
            "active_total": len(active_universe),
            "sp500_active": sum(1 for row in universe_rows if row.get("index_membership") == "SP500"),
        },
        "snapshot_row_count": len(snapshots),
        "latest_snapshot_count": len(latest_selected),
        "latest_snapshot_by_ticker": sorted(latest_selected),
        "complete_5d_count": complete_latest_count,
        "preferred_complete_5d_count": preferred_complete_count,
        "missing_dimension_counts": dict(dimension_missing_counts),
        "missing_dimension_samples": dict(dimension_missing_samples),
        "missing_composite_score_count": sum(
            1 for row in latest_selected.values() if row.get("composite_score") is None
        ),
        "missing_grade_count": sum(
            1 for row in latest_selected.values() if str(row.get("grade") or "") not in VALID_GRADES
        ),
        "latest_generated_at_summary": {
            "min": min(latest_timestamps).isoformat() if latest_timestamps else None,
            "median": median([ts.timestamp() for ts in latest_timestamps]) if latest_timestamps else None,
            "max": max(latest_timestamps).isoformat() if latest_timestamps else None,
        },
        "stale_counts": dict(stale_counts),
        "duplicate_same_day_conflicts": duplicate_same_day_conflicts,
        "rows_marked_partial_selected_as_latest": selected_partial_without_reason,
        "older_complete_rows_exist_for_partial_latest": older_complete_exists,
        "legacy_value_available_when_canonical_missing": dict(legacy_only_counts),
        "persistence_gap_counts": dict(persistence_gap_counts),
        "generation_gap_counts": dict(generation_gap_counts),
        "newer_partial_over_complete": newer_partial_over_complete,
        "api_selection_mismatches": api_selection_mismatches,
        "selected_rows_with_structured_limits": selected_rows_with_structured_limits,
        "methodology_missing_count": methodology_missing_count,
        "latest_snapshot_types": dict(snapshot_type_counter),
        "recent_analysis_runs": analysis_runs,
        "recent_refresh_jobs": refresh_jobs,
    }


def render_markdown(report: dict[str, Any]) -> str:
    latest_summary = report["latest_generated_at_summary"]
    median_ts = latest_summary["median"]
    median_iso = (
        datetime.fromtimestamp(median_ts, tz=timezone.utc).isoformat()
        if median_ts is not None
        else None
    )
    lines = [
        "# Snapshot Completeness Audit",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Universe count: `{report['universe_count']}`",
        f"- Latest snapshot count: `{report['latest_snapshot_count']}`",
        f"- Complete latest snapshot count: `{report['complete_5d_count']}`",
        f"- Completeness-aware preferred latest count: `{report['preferred_complete_5d_count']}`",
        "",
        "## Core Counts",
        "",
    ]
    lines.extend(
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Universe count", report["universe_count"]],
                ["Latest snapshot count", report["latest_snapshot_count"]],
                ["Complete 5D latest count", report["complete_5d_count"]],
                ["Missing composite_score", report["missing_composite_score_count"]],
                ["Missing valid grade", report["missing_grade_count"]],
                ["Methodology missing count", report["methodology_missing_count"]],
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Dimension Gaps",
            "",
        ]
    )
    dimension_rows = []
    for dimension, _column in DIMENSION_SPECS:
        dimension_rows.append(
            [
                dimension,
                report["missing_dimension_counts"].get(dimension, 0),
                ", ".join(report["missing_dimension_samples"].get(dimension, [])) or "—",
                report["legacy_value_available_when_canonical_missing"].get(dimension, 0),
                report["persistence_gap_counts"].get(dimension, 0),
                report["generation_gap_counts"].get(dimension, 0),
            ]
        )
    lines.extend(
        _markdown_table(
            [
                "Dimension",
                "Missing latest",
                "Sample tickers",
                "Legacy-only source",
                "Likely persistence gap",
                "Likely generation gap",
            ],
            dimension_rows,
        )
    )
    lines.extend(
        [
            "",
            "## Latest Timestamp Summary",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Metric", "Value"],
            [
                ["Min analysis_as_of", latest_summary["min"] or "—"],
                ["Median analysis_as_of", median_iso or "—"],
                ["Max analysis_as_of", latest_summary["max"] or "—"],
                ["Stale >24h", report["stale_counts"].get("over_24h", 0)],
                ["Stale >48h", report["stale_counts"].get("over_48h", 0)],
                ["Stale >7d", report["stale_counts"].get("over_7d", 0)],
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Selection Integrity",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Finding", "Count", "Examples"],
            [
                [
                    "Duplicate same-day conflicts",
                    len(report["duplicate_same_day_conflicts"]),
                    ", ".join(report["duplicate_same_day_conflicts"][:15]) or "—",
                ],
                [
                    "Partial latest selected",
                    len(report["rows_marked_partial_selected_as_latest"]),
                    ", ".join(report["rows_marked_partial_selected_as_latest"][:15]) or "—",
                ],
                [
                    "Older complete row exists",
                    len(report["older_complete_rows_exist_for_partial_latest"]),
                    ", ".join(report["older_complete_rows_exist_for_partial_latest"][:15]) or "—",
                ],
                [
                    "API selection mismatches",
                    len(report["api_selection_mismatches"]),
                    ", ".join(report["api_selection_mismatches"][:15]) or "—",
                ],
                [
                    "Structured limited rows selected",
                    len(report["selected_rows_with_structured_limits"]),
                    ", ".join(report["selected_rows_with_structured_limits"][:10]) or "—",
                ],
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Snapshot Types",
            "",
        ]
    )
    snapshot_type_rows = [
        [key, value] for key, value in sorted(report["latest_snapshot_types"].items())
    ]
    lines.extend(_markdown_table(["Snapshot type", "Latest row count"], snapshot_type_rows))
    lines.extend(["", "## Recent Runs", ""])
    for row in report["recent_analysis_runs"][:10]:
        lines.append(
            "- "
            + f"`{row.get('started_at')}` `status={row.get('status')}` "
            + f"`triggered_by={row.get('triggered_by')}` "
            + f"`positions_processed={row.get('positions_processed')}` "
            + f"`id={row.get('id')}`"
        )
        if row.get("error_message"):
            lines.append(f"  error: `{row.get('error_message')}`")
    if not report["recent_analysis_runs"]:
        lines.append("- No recent analysis runs found for the SP500 system user.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit latest ticker snapshot completeness.")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--output", default=None, help="Write markdown report to this path.")
    parser.add_argument("--json-output", default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    report = run_audit(tickers=args.tickers, page_size=max(10, args.page_size))
    markdown = render_markdown(report)
    print(markdown)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
