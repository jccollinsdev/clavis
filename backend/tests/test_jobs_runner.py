import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

from app.jobs import run as job_runner


class _FakeQuery:
    def __init__(self, table_name: str, db: "FakeSupabase"):
        self.table_name = table_name
        self.db = db
        self.payload = None
        self.filters = {}
        self.mode = None

    def insert(self, payload):
        self.mode = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.mode = "update"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def execute(self):
        if self.mode == "insert":
            row = {"id": f"run-{len(self.db.rows) + 1}", **self.payload}
            self.db.rows.append(row)
            return SimpleNamespace(data=[row])
        if self.mode == "update":
            row_id = self.filters.get("id")
            for row in self.db.rows:
                if row.get("id") == row_id:
                    row.update(self.payload)
                    return SimpleNamespace(data=[row])
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=[])


class _FakeRpc:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return SimpleNamespace(data=self.value)


class FakeSupabase:
    def __init__(self, lock_value=True):
        self.lock_value = lock_value
        self.rows = []
        self.rpc_calls = []

    def table(self, table_name):
        assert table_name == "job_runs"
        return _FakeQuery(table_name, self)

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        if name == "clavix_try_advisory_lock":
            return _FakeRpc(self.lock_value)
        return _FakeRpc(True)


def test_job_runner_dry_run_does_not_touch_db():
    result = job_runner.main(["daily_macro_snapshot", "--dry-run"])

    assert result == 0


def test_run_job_records_skipped_lock():
    fake_supabase = FakeSupabase(lock_value=False)

    with patch.object(job_runner, "get_supabase", return_value=fake_supabase):
        result = job_runner.run_job_sync("daily_macro_snapshot")

    assert result["status"] == "skipped_lock"
    assert fake_supabase.rows[0]["status"] == "skipped_lock"
    assert fake_supabase.rows[0]["items_skipped"] == 1


def test_run_job_records_success_and_releases_lock():
    fake_supabase = FakeSupabase(lock_value=True)

    def fake_handler():
        return {"status": "completed", "items_processed": 11}

    spec = job_runner.JobSpec("fake_job", "daily", fake_handler)
    with (
        patch.object(job_runner, "get_supabase", return_value=fake_supabase),
        patch.dict(job_runner.JOB_REGISTRY, {"fake_job": spec}),
    ):
        result = job_runner.run_job_sync("fake_job")

    assert result["status"] == "completed"
    assert result["items_processed"] == 11
    rpc_names = [name for name, _params in fake_supabase.rpc_calls]
    assert rpc_names == ["clavix_try_advisory_lock", "clavix_advisory_unlock"]
