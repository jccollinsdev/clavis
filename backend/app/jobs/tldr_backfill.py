"""TLDR backfill job — re-enriches articles that have sentiment but are missing
TLDR, what_it_means, or key_implications.

632 articles failed body extraction (can't be fixed), but ~300 have a body
and got sentiment-scored before TLDR generation was added. This job clears
that backlog in one shot and can be re-run monthly via cron.

Run manually: python -m app.jobs.run tldr_backfill
Auto: added to cron monthly_tldr_backfill on the 1st of each month.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Only enrich articles that have body content but missing at least one field.
# Don't touch failed extractions (body IS NULL or length < 50).
MIN_BODY_LENGTH = 50
BATCH_SIZE = 200


def run(days_back: int = 30) -> dict[str, Any]:
    from app.services.supabase import get_supabase
    from app.services.news_enrichment import enrich_and_store_articles_batch

    supabase = get_supabase()

    # Find articles with body but incomplete enrichment
    rows = (
        supabase.table("shared_ticker_events")
        .select("id, ticker, title, body, sentiment_score, tldr, what_it_means, key_implications, source, published_at, source_url, url")
        .gte("published_at", f"NOW() - INTERVAL '{days_back} days'")
        .not_.is_("body", "null")
        .or_("tldr.is.null,what_it_means.is.null,key_implications.is.null")
        .order("published_at", desc=True)
        .limit(2000)
        .execute()
        .data
        or []
    )

    # Filter to articles with meaningful body
    candidates = [
        r for r in rows
        if r.get("body") and len(str(r.get("body") or "")) >= MIN_BODY_LENGTH
    ]
    total = len(candidates)
    logger.info("[TLDR_BACKFILL] Found %d articles needing TLDR/implications enrichment.", total)

    if not candidates:
        return {"status": "completed", "items_processed": 0, "items_skipped": 0, "items_failed": 0,
                "metadata": {"message": "No articles needed enrichment."}}

    stored = 0
    failed = 0
    for i in range(0, total, BATCH_SIZE):
        batch = candidates[i : i + BATCH_SIZE]
        try:
            result = enrich_and_store_articles_batch(
                supabase,
                batch,
                skip_existing=False,  # preserves existing non-null fields, only fills nulls
                max_concurrency=5,
            )
            stored += len(result)
        except Exception as exc:
            failed += len(batch)
            logger.error("[TLDR_BACKFILL] Batch %d failed: %s", i // BATCH_SIZE, exc)

    logger.info("[TLDR_BACKFILL] Done. stored=%d failed=%d", stored, failed)
    return {
        "status": "completed" if failed == 0 else "failed",
        "items_processed": stored,
        "items_skipped": total - stored - failed,
        "items_failed": failed,
        "metadata": {"candidates": total, "days_back": days_back},
    }


def run_from_env() -> dict[str, Any]:
    import os
    days = int(os.getenv("TLDR_BACKFILL_DAYS", "30"))
    return run(days_back=days)
