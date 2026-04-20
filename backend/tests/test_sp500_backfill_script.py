from types import SimpleNamespace
from unittest.mock import patch

from app.scripts import sp500_backfill


def test_start_launches_worker_from_backend_root():
    args = SimpleNamespace(job_type="backfill", limit=25, batch_size=4, log_path=None)

    with (
        patch.object(sp500_backfill, "_get_active_run", return_value=None),
        patch.object(
            sp500_backfill, "create_sp500_backfill_run", return_value={"id": "run-123"}
        ),
        patch.object(sp500_backfill.subprocess, "Popen") as popen_mock,
        patch.object(sp500_backfill, "_backend_root", return_value="/repo/backend"),
    ):
        popen_mock.return_value.pid = 4242

        exit_code = sp500_backfill._start(args)

    assert exit_code == 0
    popen_mock.assert_called_once()
    assert popen_mock.call_args.kwargs["cwd"] == "/repo/backend"
    assert popen_mock.call_args.args[0][:4] == [
        sp500_backfill.sys.executable,
        "-m",
        "app.scripts.sp500_backfill",
        "worker",
    ]
