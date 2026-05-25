from __future__ import annotations

from datetime import datetime, timezone
from math import log10
from typing import Any

from app.services.supabase import get_supabase


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _similarity(ticker_row: dict[str, Any], peer_row: dict[str, Any]) -> float:
    score = 0.0
    if ticker_row.get("sector") and ticker_row.get("sector") == peer_row.get("sector"):
        score += 0.65
    if ticker_row.get("market_cap_bucket") and ticker_row.get("market_cap_bucket") == peer_row.get("market_cap_bucket"):
        score += 0.2
    lhs_cap = _float(ticker_row.get("market_cap"))
    rhs_cap = _float(peer_row.get("market_cap"))
    if lhs_cap and rhs_cap and lhs_cap > 0 and rhs_cap > 0:
        distance = abs(log10(lhs_cap) - log10(rhs_cap))
        score += max(0.0, 0.15 * (1.0 - min(distance, 2.0) / 2.0))
    return round(min(score, 1.0), 4)


def compute_peer_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    computed_at = datetime.now(timezone.utc).isoformat()
    output: list[dict[str, Any]] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").upper()
        if not ticker:
            continue
        peers = []
        for candidate in rows:
            peer = str(candidate.get("ticker") or "").upper()
            if not peer or peer == ticker:
                continue
            similarity = _similarity(row, candidate)
            if similarity > 0:
                peers.append((similarity, peer))
        for similarity, peer in sorted(peers, reverse=True)[:10]:
            output.append(
                {
                    "ticker": ticker,
                    "peer_ticker": peer,
                    "similarity": similarity,
                    "computed_at": computed_at,
                }
            )
    return output


def run(limit: int | None = None) -> dict[str, Any]:
    supabase = get_supabase()
    query = (
        supabase.table("ticker_metadata")
        .select("ticker,sector,market_cap,market_cap_bucket")
    )
    if limit:
        query = query.limit(limit)
    rows = query.execute().data or []
    peers = compute_peer_groups(rows)
    if peers:
        supabase.table("peer_groups").upsert(
            peers,
            on_conflict="ticker,peer_ticker",
        ).execute()
    return {
        "status": "completed",
        "items_processed": len(peers),
        "metadata": {"tickers": len({row["ticker"] for row in peers}) if peers else 0},
    }


def run_from_env() -> dict[str, Any]:
    return run()
