from __future__ import annotations

from typing import Any

from app.services.supabase import get_supabase
from app.services.ticker_cache_service import load_sp500_seed_rows


def diff_universe(existing: list[dict[str, Any]], authoritative: list[dict[str, Any]]) -> dict[str, list[str]]:
    current = {str(row.get("ticker") or "").upper() for row in existing if row.get("is_active", True)}
    desired = {str(row.get("ticker") or "").upper() for row in authoritative}
    return {
        "adds": sorted(desired - current),
        "removes": sorted(current - desired),
    }


def run(dry_run: bool = False) -> dict[str, Any]:
    supabase = get_supabase()
    existing = (
        supabase.table("ticker_universe")
        .select("ticker,is_active")
        .eq("index_membership", "SP500")
        .execute()
        .data
        or []
    )
    authoritative = load_sp500_seed_rows()
    diff = diff_universe(existing, authoritative)
    if not dry_run:
        for ticker in diff["adds"]:
            seed = next((row for row in authoritative if row["ticker"] == ticker), None)
            if seed:
                supabase.table("ticker_universe").upsert(seed, on_conflict="ticker").execute()
        for ticker in diff["removes"]:
            supabase.table("ticker_universe").update({"is_active": False}).eq("ticker", ticker).execute()
    return {
        "status": "completed",
        "items_processed": len(diff["adds"]) + len(diff["removes"]),
        "metadata": diff | {"dry_run": dry_run},
    }


def run_from_env() -> dict[str, Any]:
    return run()
