"""Re-enrichment repair job for articles with extracted bodies but missing LLM enrichment.

Selects articles from shared_ticker_events where:
  - extraction_status = 'success'
  - body_length >= 300
  - sentiment_score IS NULL
  - headline_only IS FALSE or NULL
  - paywalled IS FALSE or NULL
  - rejection_reason IS NULL
  - published_at within trailing --window-days

Calls LLM enrichment on them in batches, updates the DB, and reports results.
Does NOT promote risk snapshots. Does NOT re-extract bodies. Does NOT touch articles
with sentiment_score already set. Safe to re-run — idempotent.

Usage:
    cd backend
    python -m app.scripts.reenrich_news --dry-run
    python -m app.scripts.reenrich_news --window-days 7 --batch-size 25
    python -m app.scripts.reenrich_news --window-days 14 --batch-size 50 --max-articles 500
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("reenrich_news")

# ── Safety constants ───────────────────────────────────────────────────────────
MIN_BODY_LENGTH = 300       # chars; must have real extracted body
MIN_BODY_WORDS  = 40        # words; matches current branch body_has_content threshold
BATCH_SIZE_DEFAULT = 25
MAX_CONCURRENCY_DEFAULT = 4
WINDOW_DAYS_DEFAULT = 7

# Recommendation language rejected by verifier — should never appear in LLM output.
_FORBIDDEN_PHRASES = {
    "buy", "sell", "advise", "suggest", "predict", "forecast",
    "recommendation", "bullish outlook", "bearish call", "upside potential",
}

_REJECTION_REASONS = {
    "paywall_content", "blocked_content", "no_body", "duplicate",
    "low_quality", "spam", "off_topic",
}


def _select_candidates(supabase, *, window_days: int, limit: int) -> list[dict[str, Any]]:
    """Fetch articles eligible for re-enrichment, paginating past the 1000-row API cap."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    PAGE_SIZE = 1000

    all_rows: list[dict[str, Any]] = []
    offset = 0
    while len(all_rows) < limit:
        fetch = min(PAGE_SIZE, limit - len(all_rows))
        rows = (
            supabase.table("shared_ticker_events")
            .select(
                "id,ticker,title,source,source_url,canonical_url,published_at,"
                "body,body_markdown,body_length,extraction_status,"
                "sentiment_score,tldr,what_it_means,key_implications,"
                "paywalled,paywall_detected,headline_only,rejection_reason,"
                "extraction_provider_used,event_hash"
            )
            .eq("extraction_status", "success")
            .gte("body_length", MIN_BODY_LENGTH)
            .is_("sentiment_score", "null")
            .is_("rejection_reason", "null")
            .gte("published_at", cutoff)
            .order("published_at", desc=True)
            .range(offset, offset + fetch - 1)
            .execute()
            .data
            or []
        )
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < fetch:
            break
        offset += fetch

    # Client-side filters that Supabase .is_() can't express cleanly
    candidates = []
    for row in all_rows:
        if row.get("paywalled") or row.get("paywall_detected"):
            continue
        if row.get("headline_only"):
            continue
        body = str(row.get("body") or "").strip()
        if len(body.split()) < MIN_BODY_WORDS:
            continue
        # Sanity: body must not be a placeholder
        if body.startswith("[No body extracted]") or body.startswith("[Paywalled]") or body.startswith("[Blocked]"):
            continue
        # Skip known extraction-failure patterns (navigation menus / login walls
        # that passed body_length >= 300 but contain no article content)
        body_lower = body.lower()
        if "get benzinga pro" in body_lower or "benzinga edge" in body_lower:
            continue
        if "create free account" in body_lower:
            continue
        if body.startswith("# ") and "stock price, quote" in body_lower:
            continue
        candidates.append(row)

    return candidates


def _validate_enrichment(result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate LLM enrichment output. Returns (ok, missing_or_invalid)."""
    issues: list[str] = []
    score = result.get("sentiment_score")
    if score is None:
        issues.append("missing_sentiment_score")
    elif not isinstance(score, (int, float)) or not (0 <= float(score) <= 100):
        issues.append(f"invalid_sentiment_score:{score}")

    reason = str(result.get("sentiment_reason") or "").strip()
    if not reason:
        issues.append("missing_sentiment_reason")
    else:
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in reason.lower():
                issues.append(f"forbidden_phrase:{phrase}")

    tldr = str(result.get("tldr") or "").strip()
    if not tldr:
        issues.append("missing_tldr")

    what = str(result.get("what_it_means") or "").strip()
    if not what:
        issues.append("missing_what_it_means")

    return len(issues) == 0, issues


async def _enrich_one(
    supabase,
    row: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Enrich a single article and update the DB. Returns result dict."""
    from ..services.news_enrichment import (
        _score_article_llm,
        _generate_tldr_llm,
        sanitize_text_field,
    )
    from ..pipeline.analysis_utils import sanitize_text_field as _sani

    ticker   = str(row.get("ticker") or "").strip().upper()
    headline = str(row.get("title")  or "").strip()
    body     = str(row.get("body")   or "").strip()
    row_id   = row.get("id")

    result: dict[str, Any] = {
        "id": row_id,
        "ticker": ticker,
        "status": "pending",
        "issues": [],
    }

    if not ticker or not headline or not body:
        result["status"] = "skipped_missing_fields"
        return result

    try:
        # Run sentiment + TLDR concurrently
        sentiment_res, tldr_res = await asyncio.gather(
            _score_article_llm(ticker, headline, body),
            _generate_tldr_llm(ticker, headline, body),
            return_exceptions=True,
        )
    except Exception as exc:
        result["status"] = "llm_exception"
        result["issues"] = [str(exc)[:120]]
        return result

    # Unpack sentiment
    sentiment_score: Any = None
    sentiment_reason: str | None = None
    impact_tag: str | None = None

    if isinstance(sentiment_res, Exception):
        result["issues"].append(f"sentiment_failed:{sentiment_res!s:.80}")
    elif isinstance(sentiment_res, dict):
        sentiment_score = sentiment_res.get("sentiment_score")
        sentiment_reason = _sani(sentiment_res.get("sentiment_reason"), fallback="")
        tag_val = (sentiment_res.get("impact_tag") or "").strip().lower()
        valid_tags = {"financial-impact", "regulatory", "leadership", "product", "macro", "sector", "other"}
        impact_tag = tag_val if tag_val in valid_tags else None

    # Unpack TLDR
    tldr: str | None = None
    what_it_means: str | None = None
    key_implications: list = []

    if isinstance(tldr_res, Exception):
        result["issues"].append(f"tldr_failed:{tldr_res!s:.80}")
    elif isinstance(tldr_res, dict):
        tldr = _sani(tldr_res.get("tldr"), fallback="")
        what_it_means = _sani(tldr_res.get("what_it_means"), fallback="")
        raw_imp = tldr_res.get("key_implications")
        if isinstance(raw_imp, list):
            key_implications = [_sani(i, fallback="") for i in raw_imp[:4] if i]

    # Validate
    enrichment_out = {
        "sentiment_score": sentiment_score,
        "sentiment_reason": sentiment_reason,
        "tldr": tldr,
        "what_it_means": what_it_means,
    }
    ok, issues = _validate_enrichment(enrichment_out)
    if not ok:
        result["status"] = "validation_failed"
        result["issues"].extend(issues)
        # Retry once if only missing tldr/what_it_means (partial)
        if any(i.startswith("forbidden_phrase") or i == "missing_sentiment_score" for i in issues):
            return result

    if dry_run:
        result["status"] = "dry_run_would_enrich"
        result["sentiment_score"] = sentiment_score
        return result

    # Persist
    try:
        patch: dict[str, Any] = {
            "sentiment_score": sentiment_score,
            "sentiment_reason": sentiment_reason,
            "impact_tag": impact_tag,
            "tldr": tldr or None,
            "what_it_means": what_it_means or None,
            "key_implications": key_implications,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        # Remove None values so we don't overwrite existing data with NULL
        patch = {k: v for k, v in patch.items() if v is not None}
        await asyncio.to_thread(
            lambda: (
                supabase.table("shared_ticker_events")
                .update(patch)
                .eq("id", str(row_id))
                .execute()
            )
        )
        result["status"] = "enriched"
        result["sentiment_score"] = sentiment_score
    except Exception as exc:
        result["status"] = "db_write_failed"
        result["issues"].append(str(exc)[:120])

    return result


async def run_reenrichment(
    *,
    window_days: int = WINDOW_DAYS_DEFAULT,
    batch_size: int = BATCH_SIZE_DEFAULT,
    max_articles: int | None = None,
    max_concurrency: int = MAX_CONCURRENCY_DEFAULT,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Main entry point. Returns aggregate stats dict."""
    from ..services.supabase import get_supabase

    logger.info("=== Re-Enrichment Repair Job ===")
    logger.info("  window_days=%d  batch_size=%d  max_articles=%s  dry_run=%s",
                window_days, batch_size, max_articles or "unlimited", dry_run)

    supabase = get_supabase()

    fetch_limit = max_articles or 5000
    logger.info("[SELECT] Querying candidates (limit=%d)…", fetch_limit)
    candidates = _select_candidates(supabase, window_days=window_days, limit=fetch_limit)
    logger.info("[SELECT] Found %d eligible articles across %d tickers",
                len(candidates), len({c["ticker"] for c in candidates}))

    if not candidates:
        logger.info("[SELECT] Nothing to do.")
        return {"total_candidates": 0, "enriched": 0, "failed": 0, "skipped": 0}

    if dry_run:
        ticker_counts: dict[str, int] = {}
        for c in candidates:
            ticker_counts[c["ticker"]] = ticker_counts.get(c["ticker"], 0) + 1
        top10 = sorted(ticker_counts.items(), key=lambda x: -x[1])[:10]
        logger.info("[DRY-RUN] Would enrich %d articles", len(candidates))
        logger.info("[DRY-RUN] Top tickers: %s", top10)
        return {
            "total_candidates": len(candidates),
            "tickers_affected": len(ticker_counts),
            "dry_run": True,
        }

    # ── Batch processing ──────────────────────────────────────────────────────
    t_start   = time.monotonic()
    stats: dict[str, Any] = {
        "total_candidates": len(candidates),
        "enriched": 0,
        "failed": 0,
        "skipped": 0,
        "validation_failed": 0,
        "llm_exception": 0,
        "db_write_failed": 0,
        "batches": 0,
        "tickers_enriched": set(),
        "failures_by_issue": {},
    }

    sem = asyncio.Semaphore(max_concurrency)

    async def _bounded(row: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await _enrich_one(supabase, row, dry_run=False)

    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start : batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(candidates) + batch_size - 1) // batch_size
        logger.info("[BATCH %d/%d] Processing %d articles…", batch_num, total_batches, len(batch))

        t_batch = time.monotonic()
        batch_results = await asyncio.gather(*(_bounded(row) for row in batch))
        elapsed = time.monotonic() - t_batch

        enriched_n = sum(1 for r in batch_results if r["status"] == "enriched")
        failed_n   = sum(1 for r in batch_results if r["status"] not in ("enriched", "skipped_missing_fields"))
        skipped_n  = sum(1 for r in batch_results if r["status"] == "skipped_missing_fields")

        stats["batches"] += 1
        stats["enriched"] += enriched_n
        stats["failed"]   += failed_n
        stats["skipped"]  += skipped_n

        for r in batch_results:
            if r["status"] == "enriched":
                stats["tickers_enriched"].add(r["ticker"])
            if r["status"] == "validation_failed":
                stats["validation_failed"] += 1
            if r["status"] == "llm_exception":
                stats["llm_exception"] += 1
            if r["status"] == "db_write_failed":
                stats["db_write_failed"] += 1
            for issue in r.get("issues", []):
                key = issue.split(":")[0]
                stats["failures_by_issue"][key] = stats["failures_by_issue"].get(key, 0) + 1

        # Build per-batch failure breakdown for diagnostics
        batch_issue_counts: dict[str, int] = {}
        for r in batch_results:
            for issue in r.get("issues", []):
                key = issue.split(":")[0]
                batch_issue_counts[key] = batch_issue_counts.get(key, 0) + 1

        logger.info(
            "[BATCH %d/%d] Done in %.1fs — enriched=%d failed=%d skipped=%d "
            "(total so far: enriched=%d failed=%d) issues=%s",
            batch_num, total_batches, elapsed,
            enriched_n, failed_n, skipped_n,
            stats["enriched"], stats["failed"],
            batch_issue_counts or "none",
        )

    total_elapsed = time.monotonic() - t_start
    stats["runtime_s"] = round(total_elapsed, 1)
    stats["tickers_enriched"] = sorted(stats["tickers_enriched"])

    # ── Post-run coverage check ───────────────────────────────────────────────
    logger.info("[COVERAGE] Recomputing usability for affected tickers…")
    affected_tickers = list({c["ticker"] for c in candidates})
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    try:
        rows = (
            supabase.table("shared_ticker_events")
            .select("ticker,extraction_status,paywalled,sentiment_score")
            .in_("ticker", affected_tickers)
            .gte("published_at", cutoff)
            .execute()
            .data or []
        )
        usable_by_ticker: dict[str, int] = {}
        for row in rows:
            t = str(row.get("ticker") or "").upper()
            if (
                row.get("extraction_status") == "success"
                and not row.get("paywalled", False)
                and row.get("sentiment_score") is not None
            ):
                usable_by_ticker[t] = usable_by_ticker.get(t, 0) + 1

        tickers_ge3  = sum(1 for v in usable_by_ticker.values() if v >= 3)
        tickers_ge10 = sum(1 for v in usable_by_ticker.values() if v >= 10)
        tickers_zero = sum(1 for t in affected_tickers if usable_by_ticker.get(t, 0) == 0)

        stats["post_run"] = {
            "tickers_checked": len(affected_tickers),
            "tickers_ge3":  tickers_ge3,
            "tickers_ge10": tickers_ge10,
            "tickers_zero_usable": tickers_zero,
        }
        logger.info("[COVERAGE] %d tickers checked: ≥3=%d  ≥10=%d  still_zero=%d",
                    len(affected_tickers), tickers_ge3, tickers_ge10, tickers_zero)
    except Exception as exc:
        logger.warning("[COVERAGE] Post-run check failed: %s", exc)

    # ── Final summary ─────────────────────────────────────────────────────────
    logger.info("=== Re-Enrichment Complete ===")
    logger.info("  Candidates : %d", stats["total_candidates"])
    logger.info("  Enriched   : %d (%.1f%%)",
                stats["enriched"],
                100 * stats["enriched"] / max(1, stats["total_candidates"]))
    logger.info("  Failed     : %d", stats["failed"])
    logger.info("  Skipped    : %d", stats["skipped"])
    logger.info("  Runtime    : %.1fs", stats["runtime_s"])
    if stats["failures_by_issue"]:
        logger.info("  Top failure reasons: %s",
                    sorted(stats["failures_by_issue"].items(), key=lambda x: -x[1])[:5])

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-enrich news articles with extracted bodies but missing LLM enrichment."
    )
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS_DEFAULT,
                        help="Trailing window in days (default: 7)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT,
                        help="Articles per batch (default: 25)")
    parser.add_argument("--max-articles", type=int, default=None,
                        help="Cap total articles processed (default: unlimited)")
    parser.add_argument("--max-concurrency", type=int, default=MAX_CONCURRENCY_DEFAULT,
                        help="Concurrent LLM calls per batch (default: 4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be enriched without writing to DB")
    args = parser.parse_args()

    stats = asyncio.run(
        run_reenrichment(
            window_days=args.window_days,
            batch_size=args.batch_size,
            max_articles=args.max_articles,
            max_concurrency=args.max_concurrency,
            dry_run=args.dry_run,
        )
    )

    if not args.dry_run:
        enriched = stats.get("enriched", 0)
        total    = stats.get("total_candidates", 0)
        sys.exit(0 if enriched > 0 or total == 0 else 1)


if __name__ == "__main__":
    main()
