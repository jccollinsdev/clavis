#!/usr/bin/env python3
"""10-ticker news pipeline canary.

Runs ingest_and_enrich_ticker_news for the 10 canary tickers and
reports extraction/enrichment metrics. Does NOT touch snapshots.

Usage:
    cd backend && python3 scripts/canary_10_tickers.py

Set PAUSE_SYSTEM_SCHEDULER=true before running to ensure no scheduler
interference. This script is purely additive — it only adds/updates
rows in shared_ticker_events.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

CANARY_TICKERS = [
    "AMD", "AAPL", "NVDA", "MSFT", "HOOD",
    "SMCI", "JPM", "XOM", "GOOGL", "META",
]


async def run_canary() -> None:
    from app.services.supabase import get_supabase
    from app.services.news_enrichment import ingest_and_enrich_ticker_news
    from app.services.google_news_decoder import get_decode_metrics, reset_decode_metrics
    from datetime import datetime, timezone

    supabase = get_supabase()
    reset_decode_metrics()

    print("=" * 70)
    print(f"10-TICKER CANARY  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    print("\n[PRE-CANARY] DB snapshot:")
    _print_db_baseline(supabase, CANARY_TICKERS)

    print("\n[CANARY] Running ingest_and_enrich_ticker_news …")
    counts = await ingest_and_enrich_ticker_news(
        supabase,
        CANARY_TICKERS,
        limit_per_ticker=10,
        max_concurrency=3,
    )

    decode_metrics = get_decode_metrics()
    print(f"\n[GOOGLE DECODE] metrics: {decode_metrics}")

    print("\n[POST-CANARY] DB snapshot:")
    _print_db_baseline(supabase, CANARY_TICKERS)

    print("\n[CANARY] Newly stored articles:", counts)
    print("\n[DONE]")


def _print_db_baseline(supabase, tickers: list[str]) -> None:
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    try:
        rows = (
            supabase.table("shared_ticker_events")
            .select("ticker,extraction_status,paywalled,sentiment_score")
            .in_("ticker", tickers)
            .gte("published_at", cutoff)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"  DB query failed: {e}")
        return

    from collections import defaultdict
    stats: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "success": 0, "failed": 0, "paywalled": 0,
                 "blocked": 0, "usable": 0, "missing_sentiment": 0}
    )
    for row in rows:
        t = row.get("ticker", "?")
        s = row.get("extraction_status")
        p = row.get("paywalled", False)
        sent = row.get("sentiment_score")
        stats[t]["total"] += 1
        if s == "success":
            stats[t]["success"] += 1
        elif s == "failed":
            stats[t]["failed"] += 1
        elif s in ("paywalled",):
            stats[t]["paywalled"] += 1
        elif s == "blocked":
            stats[t]["blocked"] += 1
        if s == "success" and not p and sent is not None:
            stats[t]["usable"] += 1
        if sent is None:
            stats[t]["missing_sentiment"] += 1

    header = f"  {'ticker':<6} {'7d':>4} {'ok':>4} {'fail':>4} {'pay':>4} {'blk':>4} {'usable':>7} {'miss_sent':>10} {'status':<12}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for ticker in tickers:
        s = stats[ticker]
        status = "SCORED" if s["usable"] >= 3 else "limited"
        print(
            f"  {ticker:<6} {s['total']:>4} {s['success']:>4} {s['failed']:>4} "
            f"{s['paywalled']:>4} {s['blocked']:>4} {s['usable']:>7} "
            f"{s['missing_sentiment']:>10} {status:<12}"
        )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    asyncio.run(run_canary())
