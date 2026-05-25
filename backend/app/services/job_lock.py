import logging


logger = logging.getLogger(__name__)


class PostgresAdvisoryLock:
    """Small wrapper around Postgres advisory locks exposed through Supabase RPC."""

    def __init__(self, supabase, lock_name: str):
        self.supabase = supabase
        self.lock_name = lock_name
        self.acquired = False

    def acquire(self) -> bool:
        result = (
            self.supabase.rpc(
                "clavix_try_advisory_lock",
                {"lock_name": self.lock_name},
            )
            .execute()
            .data
        )
        self.acquired = _rpc_bool(result)
        return self.acquired

    def release(self) -> bool:
        if not self.acquired:
            return False
        try:
            result = (
                self.supabase.rpc(
                    "clavix_advisory_unlock",
                    {"lock_name": self.lock_name},
                )
                .execute()
                .data
            )
            return _rpc_bool(result)
        finally:
            self.acquired = False


def _rpc_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, bool):
            return first
        if isinstance(first, dict):
            return bool(next(iter(first.values()), False))
    if isinstance(value, dict):
        return bool(next(iter(value.values()), False))
    return bool(value)
