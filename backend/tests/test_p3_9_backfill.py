import sys
import types
from datetime import date
from unittest.mock import patch

_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

from app.jobs import backfill_14d
from app.jobs import run as job_runner


def test_backfill_job_dry_run_reports_manual_tier():
    response = job_runner.main(["backfill_14d", "--dry-run"])

    assert response == 0
    assert job_runner.JOB_REGISTRY["backfill_14d"].tier == "manual"


def test_backfill_dispatches_one_composite_recompute_per_day():
    requested_days = [
        date(2026, 5, 11),
        date(2026, 5, 12),
        date(2026, 5, 13),
    ]
    dispatched: list[date] = []

    def fake_run_for_date(target_date):
        dispatched.append(target_date)
        return {
            "status": "completed",
            "items_processed": 1,
            "items_skipped": 0,
            "items_failed": 0,
            "metadata": {"target_date": target_date.isoformat()},
        }

    with (
        patch.object(backfill_14d, "_backfill_dates", return_value=requested_days),
        patch.object(backfill_14d, "run_for_date", side_effect=fake_run_for_date),
    ):
        result = backfill_14d.run()

    assert dispatched == requested_days
    assert result["status"] == "completed"
    assert result["items_processed"] == len(requested_days)
    assert result["metadata"]["days_requested"] == [
        day.isoformat() for day in requested_days
    ]
