from __future__ import annotations

from datetime import date, timedelta

from app.jobs import composite_recompute


WINDOW_DAYS = 14


def _coerce_target_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _backfill_dates(today: date | None = None) -> list[date]:
    anchor = today or date.today()
    start = anchor - timedelta(days=WINDOW_DAYS)
    return [start + timedelta(days=offset) for offset in range(WINDOW_DAYS)]


def run_for_date(target_date: date | str) -> dict[str, object]:
    resolved = _coerce_target_date(target_date)
    return composite_recompute.run(target_date=resolved)


def run(*, target_date: date | str | None = None) -> dict[str, object]:
    if target_date is not None:
        return run_for_date(target_date)

    daily_results: list[dict[str, object]] = []
    requested_days = _backfill_dates()
    for day in requested_days:
        daily_results.append(run_for_date(day))

    failed_days = [
        str((result.get("metadata") or {}).get("target_date") or "")
        for result in daily_results
        if result.get("status") == "failed"
    ]
    return {
        "status": "failed" if failed_days else "completed",
        "items_processed": sum(int(result.get("items_processed") or 0) for result in daily_results),
        "items_skipped": sum(int(result.get("items_skipped") or 0) for result in daily_results),
        "items_failed": sum(int(result.get("items_failed") or 0) for result in daily_results),
        "metadata": {
            "days_requested": [day.isoformat() for day in requested_days],
            "failed_days": [day for day in failed_days if day],
        },
    }


def run_from_env() -> dict[str, object]:
    return run()
