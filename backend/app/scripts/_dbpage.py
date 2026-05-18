"""Deterministic, fail-loud Supabase pagination helper.

Range pagination WITHOUT a stable ORDER BY returns inconsistent pages,
and treating a transient page error as end-of-data silently truncates
results. Both produce non-reproducible counts. fetch_all fixes this:
explicit order, bounded retry, and a hard raise if a page cannot be
fetched (never a silent short read).
"""
from __future__ import annotations

import time
from typing import Any

PAGE = 1000


def fetch_all(
    sb,
    table: str,
    columns: str,
    *,
    order_col: str = "id",
    in_col: str | None = None,
    in_values: list[str] | None = None,
    gte: tuple[str, str] | None = None,
    eq: tuple[str, Any] | None = None,
    page: int = PAGE,
    max_retries: int = 4,
) -> list[dict]:
    """Fetch every matching row with deterministic ordering.

    Raises RuntimeError if any page fails after retries — callers must
    never silently under-count.
    """
    out: list[dict] = []
    offset = 0
    while True:
        last_err: Exception | None = None
        rows = None
        for attempt in range(max_retries):
            try:
                q = sb.table(table).select(columns).order(order_col)
                if in_col and in_values is not None:
                    q = q.in_(in_col, in_values)
                if gte is not None:
                    q = q.gte(gte[0], gte[1])
                if eq is not None:
                    q = q.eq(eq[0], eq[1])
                resp = q.range(offset, offset + page - 1).execute()
                rows = resp.data
                if rows is None:
                    raise RuntimeError("null .data from PostgREST")
                break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(1.5 * (attempt + 1))
        if rows is None:
            raise RuntimeError(
                f"fetch_all({table}) failed at offset {offset}: {last_err}"
            )
        out.extend(rows)
        if len(rows) < page:
            break
        offset += page
    return out
