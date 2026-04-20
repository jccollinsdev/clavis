import inspect
import json
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_CURRENT_RUN_ID: ContextVar[str | None] = ContextVar("backfill_run_id", default=None)
_LOCK = threading.Lock()
_SEQUENCES: dict[str, int] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_artifact_root() -> Path:
    return _repo_root() / "BACKFILL"


def get_run_artifact_dir(run_id: str) -> Path:
    return get_artifact_root() / str(run_id)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _json_default(value: Any):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    return str(value)


def _write_json(path: Path, payload: Any) -> None:
    _ensure_dir(path.parent)
    path.write_text(
        json.dumps(payload, indent=2, default=_json_default), encoding="utf-8"
    )


def _append_jsonl(path: Path, payload: Any) -> None:
    _ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=_json_default))
        handle.write("\n")


def _next_sequence(run_id: str, key: str) -> int:
    with _LOCK:
        seq_key = f"{run_id}:{key}"
        next_value = _SEQUENCES.get(seq_key, 0) + 1
        _SEQUENCES[seq_key] = next_value
        return next_value


def _sanitize_name(value: str) -> str:
    cleaned = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value)
    )
    return cleaned.strip("_") or "artifact"


def begin_artifact_session(run_id: str, metadata: dict | None = None) -> str:
    run_id = str(run_id)
    artifact_dir = get_run_artifact_dir(run_id)
    _ensure_dir(artifact_dir)
    _ensure_dir(artifact_dir / "feeds")
    _ensure_dir(artifact_dir / "llm_calls")
    _ensure_dir(artifact_dir / "stages")
    _ensure_dir(artifact_dir / "positions")
    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }
    _write_json(artifact_dir / "manifest.json", manifest)
    _CURRENT_RUN_ID.set(run_id)
    return str(artifact_dir)


def end_artifact_session(summary: dict | None = None) -> None:
    run_id = _CURRENT_RUN_ID.get()
    if not run_id:
        return
    if summary is not None:
        write_named_json("summary.json", summary)
    _CURRENT_RUN_ID.set(None)


def get_current_run_id() -> str | None:
    return _CURRENT_RUN_ID.get()


def write_named_json(relative_path: str, payload: Any) -> None:
    run_id = get_current_run_id()
    if not run_id:
        return
    _write_json(get_run_artifact_dir(run_id) / relative_path, payload)


def append_named_jsonl(relative_path: str, payload: Any) -> None:
    run_id = get_current_run_id()
    if not run_id:
        return
    _append_jsonl(get_run_artifact_dir(run_id) / relative_path, payload)


def record_stage(stage_name: str, payload: Any) -> None:
    run_id = get_current_run_id()
    if not run_id:
        return
    seq = _next_sequence(run_id, "stage")
    file_name = f"{seq:03d}_{_sanitize_name(stage_name)}.json"
    _write_json(get_run_artifact_dir(run_id) / "stages" / file_name, payload)


def record_position_artifact(ticker: str, name: str, payload: Any) -> None:
    run_id = get_current_run_id()
    if not run_id:
        return
    file_name = f"{_sanitize_name(name)}.json"
    _write_json(
        get_run_artifact_dir(run_id)
        / "positions"
        / _sanitize_name(ticker.upper())
        / file_name,
        payload,
    )


def record_llm_call(
    function_name: str,
    model: str,
    messages: list,
    kwargs: dict,
    response: str,
    error: str | None,
    duration_ms: float,
) -> None:
    run_id = get_current_run_id()
    if not run_id:
        return

    caller = None
    for frame in inspect.stack()[2:12]:
        file_name = str(frame.filename)
        if file_name.endswith("minimax.py") or file_name.endswith(
            "backfill_artifacts.py"
        ):
            continue
        caller = {
            "file": file_name,
            "function": frame.function,
            "line": frame.lineno,
        }
        break

    seq = _next_sequence(run_id, "llm")
    payload = {
        "sequence": seq,
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "function_name": function_name,
        "caller": caller,
        "messages": messages,
        "kwargs": kwargs,
        "response": response,
        "error": error,
        "duration_ms": round(duration_ms, 2),
    }
    file_name = f"{seq:03d}_{_sanitize_name(caller['function'] if caller else function_name)}.json"
    _write_json(get_run_artifact_dir(run_id) / "llm_calls" / file_name, payload)
    _append_jsonl(get_run_artifact_dir(run_id) / "llm_calls" / "index.jsonl", payload)
