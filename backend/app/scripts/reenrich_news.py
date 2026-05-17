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
from collections import Counter
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


def _select_candidates(
    supabase, *, window_days: int, limit: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch raw candidates and split them into valid vs garbage bodies."""
    from ..services.news_enrichment import assess_article_body_quality

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

    ticker_rows = [str(row.get("ticker") or "").strip().upper() for row in all_rows if str(row.get("ticker") or "").strip()]
    metadata_map: dict[str, dict[str, Any]] = {}
    unique_tickers = sorted(set(ticker_rows))
    if unique_tickers:
        metadata_rows = (
            supabase.table("ticker_metadata")
            .select("ticker,company_name")
            .in_("ticker", unique_tickers)
            .execute()
            .data
            or []
        )
        metadata_map = {
            str(row.get("ticker") or "").upper(): row
            for row in metadata_rows
            if row.get("ticker")
        }

    # Client-side filters that Supabase .is_() can't express cleanly
    candidates = []
    rejected: list[dict[str, Any]] = []
    for row in all_rows:
        if row.get("paywalled") or row.get("paywall_detected"):
            continue
        if row.get("headline_only"):
            continue
        body = str(row.get("body") or "").strip()
        if len(body) < MIN_BODY_LENGTH:
            continue
        row = dict(row)
        row["company_name"] = (
            metadata_map.get(str(row.get("ticker") or "").upper(), {}).get("company_name")
        )
        usable, rejection_reason, cleaned_body = assess_article_body_quality(row)
        if not usable:
            rejected.append({
                "id": row.get("id"),
                "ticker": row.get("ticker"),
                "reason": rejection_reason or "no_usable_content",
            })
            continue
        row["body"] = cleaned_body
        row["body_length"] = len(cleaned_body)
        candidates.append(row)

    return candidates, rejected


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

    tldr = str(result.get("tldr") or "").strip()
    if not tldr:
        issues.append("missing_tldr")

    what = str(result.get("what_it_means") or "").strip()
    if not what:
        issues.append("missing_what_it_means")

    combined = " ".join(
        part.lower()
        for part in (reason, tldr, what)
        if part
    )
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in combined:
            issues.append(f"forbidden_phrase:{phrase}")

    return len(issues) == 0, issues


def _primary_issue(issues: list[str]) -> str:
    if not issues:
        return "unknown_failure"
    return str(issues[0]).split(":", 1)[0]


async def _enrich_one(
    supabase,
    row: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Enrich a single article and update the DB. Returns result dict."""
    from ..services.news_enrichment import (
        assess_article_body_quality,
        enrich_article_with_retry,
        sanitize_text_field,
    )

    ticker   = str(row.get("ticker") or "").strip().upper()
    headline = str(row.get("title")  or "").strip()
    body     = str(row.get("body")   or "").strip()
    row_id   = row.get("id")

    result: dict[str, Any] = {
        "id": row_id,
        "ticker": ticker,
        "source": str(row.get("source") or ""),
        "body_length": len(body),
        "status": "pending",
        "issues": [],
        "raw_llm_preview": "",
        "body_quality_reason": None,
        "llm_calls": 0,
        "llm_429s": 0,
        "sent_to_llm": False,
    }

    if not ticker or not headline or not body:
        result["status"] = "skipped_missing_fields"
        return result

    usable, rejection_reason, cleaned_body = assess_article_body_quality(row)
    if not usable:
        result["status"] = "rejected_garbage"
        result["issues"] = [rejection_reason or "no_usable_content"]
        result["body_quality_reason"] = rejection_reason or "no_usable_content"
        if dry_run:
            return result
        try:
            patch = {
                "body": cleaned_body,
                "body_length": len(cleaned_body),
                "extraction_status": "failed",
                "analysis_status": "rejected",
                "rejection_reason": rejection_reason or "no_usable_content",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await asyncio.to_thread(
                lambda: (
                    supabase.table("shared_ticker_events")
                    .update(patch)
                    .eq("id", str(row_id))
                    .execute()
                )
            )
        except Exception as exc:
            result["status"] = "db_write_failed"
            result["issues"].append(str(exc)[:120])
        return result

    body = cleaned_body
    result["body_length"] = len(body)

    existing_tldr = str(row.get("tldr") or "").strip() or None
    existing_what = str(row.get("what_it_means") or "").strip() or None
    existing_implications = row.get("key_implications") if isinstance(row.get("key_implications"), list) else []
    result["sent_to_llm"] = True
    enrichment, diagnostics = await enrich_article_with_retry(
        ticker=ticker,
        headline=headline,
        body=body,
        company_name=str(row.get("company_name") or "").strip() or None,
    )
    result["llm_calls"] = int(diagnostics.get("llm_calls") or 0)
    result["llm_429s"] = int(diagnostics.get("llm_429s") or 0)
    result["raw_llm_preview"] = str(diagnostics.get("raw_llm_preview") or "")

    if enrichment is None:
        failure_reason = str(diagnostics.get("failure_reason") or "true_llm_failure")
        result["status"] = "validation_failed"
        result["issues"] = [failure_reason]
        if dry_run:
            return result
        try:
            await asyncio.to_thread(
                lambda: (
                    supabase.table("shared_ticker_events")
                    .update(
                        {
                            "analysis_status": "enrichment_failed",
                            "rejection_reason": failure_reason,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    .eq("id", str(row_id))
                    .execute()
                )
            )
        except Exception as exc:
            result["status"] = "db_write_failed"
            result["issues"].append(str(exc)[:120])
        return result

    sentiment_score: Any = enrichment.get("sentiment_score")
    sentiment_reason = sanitize_text_field(enrichment.get("sentiment_reason"), fallback="")
    impact_tag = (enrichment.get("impact_tag") or "").strip().lower()
    valid_tags = {"financial-impact", "regulatory", "leadership", "product", "macro", "sector", "other"}
    impact_tag = impact_tag if impact_tag in valid_tags else None

    tldr = sanitize_text_field(enrichment.get("tldr"), fallback="") or existing_tldr
    what_it_means = sanitize_text_field(enrichment.get("what_it_means"), fallback="") or existing_what
    key_implications = [sanitize_text_field(i, fallback="") for i in (enrichment.get("key_implications") or []) if sanitize_text_field(i, fallback="")]
    if not key_implications:
        key_implications = existing_implications

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
        if dry_run:
            return result
        try:
            await asyncio.to_thread(
                lambda: (
                    supabase.table("shared_ticker_events")
                    .update(
                        {
                            "analysis_status": "enrichment_failed",
                            "rejection_reason": _primary_issue(issues),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    .eq("id", str(row_id))
                    .execute()
                )
            )
        except Exception as exc:
            result["status"] = "db_write_failed"
            result["issues"].append(str(exc)[:120])
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
            "body": body,
            "body_length": len(body),
            "tldr": tldr or None,
            "what_it_means": what_it_means or None,
            "key_implications": key_implications,
            "analysis_status": "complete",
            "rejection_reason": None,
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
    candidates, rejected = _select_candidates(supabase, window_days=window_days, limit=fetch_limit)
    rejection_counts = Counter(r["reason"] for r in rejected)
    logger.info(
        "[SELECT] Raw=%d valid=%d rejected_garbage=%d across %d tickers",
        len(candidates) + len(rejected),
        len(candidates),
        len(rejected),
        len({c["ticker"] for c in candidates}),
    )
    if rejection_counts:
        logger.info("[SELECT] Top rejection reasons: %s", rejection_counts.most_common(10))

    if not candidates:
        logger.info("[SELECT] Nothing to do.")
        return {
            "raw_candidates": len(rejected),
            "total_candidates": 0,
            "rejected_garbage": len(rejected),
            "rejections_by_reason": dict(rejection_counts),
            "sent_to_llm": 0,
            "llm_calls": 0,
            "llm_429s": 0,
            "enriched": 0,
            "failed": 0,
            "skipped": 0,
        }

    if dry_run:
        ticker_counts: dict[str, int] = {}
        for c in candidates:
            ticker_counts[c["ticker"]] = ticker_counts.get(c["ticker"], 0) + 1
        top10 = sorted(ticker_counts.items(), key=lambda x: -x[1])[:10]
        logger.info("[DRY-RUN] Would enrich %d articles", len(candidates))
        logger.info("[DRY-RUN] Top tickers: %s", top10)
        return {
            "raw_candidates": len(candidates) + len(rejected),
            "total_candidates": len(candidates),
            "rejected_garbage": len(rejected),
            "rejections_by_reason": dict(rejection_counts),
            "tickers_affected": len(ticker_counts),
            "sent_to_llm": 0,
            "llm_calls": 0,
            "llm_429s": 0,
            "dry_run": True,
        }

    # ── Batch processing ──────────────────────────────────────────────────────
    t_start   = time.monotonic()
    stats: dict[str, Any] = {
        "raw_candidates": len(candidates) + len(rejected),
        "total_candidates": len(candidates),
        "rejected_garbage": len(rejected),
        "rejections_by_reason": dict(rejection_counts),
        "sent_to_llm": 0,
        "llm_calls": 0,
        "llm_429s": 0,
        "enriched": 0,
        "failed": 0,
        "skipped": 0,
        "validation_failed": 0,
        "llm_exception": 0,
        "db_write_failed": 0,
        "batches": 0,
        "tickers_enriched": set(),
        "failures_by_issue": {},
        "failure_rows": [],
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
        failed_n   = sum(
            1
            for r in batch_results
            if r["status"] not in ("enriched", "skipped_missing_fields", "rejected_garbage")
        )
        skipped_n  = sum(1 for r in batch_results if r["status"] == "skipped_missing_fields")
        rejected_n = sum(1 for r in batch_results if r["status"] == "rejected_garbage")

        stats["batches"] += 1
        stats["enriched"] += enriched_n
        stats["failed"]   += failed_n
        stats["skipped"]  += skipped_n
        stats["rejected_garbage"] += rejected_n
        stats["sent_to_llm"] += sum(1 for r in batch_results if r.get("sent_to_llm"))
        stats["llm_calls"] += sum(int(r.get("llm_calls") or 0) for r in batch_results)
        stats["llm_429s"] += sum(int(r.get("llm_429s") or 0) for r in batch_results)

        for r in batch_results:
            if r["status"] == "enriched":
                stats["tickers_enriched"].add(r["ticker"])
            if r["status"] == "validation_failed":
                stats["validation_failed"] += 1
            if r["status"] == "llm_exception":
                stats["llm_exception"] += 1
            if r["status"] == "db_write_failed":
                stats["db_write_failed"] += 1
            if r["status"] == "rejected_garbage":
                for issue in r.get("issues", []):
                    stats["rejections_by_reason"][issue] = stats["rejections_by_reason"].get(issue, 0) + 1
            for issue in r.get("issues", []):
                key = issue.split(":")[0]
                stats["failures_by_issue"][key] = stats["failures_by_issue"].get(key, 0) + 1
            if r["status"] not in ("enriched", "skipped_missing_fields"):
                stats["failure_rows"].append(
                    {
                        "article_id": r.get("id"),
                        "ticker": r.get("ticker"),
                        "source": r.get("source"),
                        "body_length": r.get("body_length"),
                        "failure_reason": _primary_issue(r.get("issues", [])),
                        "raw_llm_preview": r.get("raw_llm_preview", ""),
                        "body_quality_reason": r.get("body_quality_reason"),
                    }
                )

        # Build per-batch failure breakdown for diagnostics
        batch_issue_counts: dict[str, int] = {}
        for r in batch_results:
            for issue in r.get("issues", []):
                key = issue.split(":")[0]
                batch_issue_counts[key] = batch_issue_counts.get(key, 0) + 1

        logger.info(
            "[BATCH %d/%d] Done in %.1fs — enriched=%d failed=%d skipped=%d rejected=%d "
            "(total so far: enriched=%d failed=%d rejected=%d) issues=%s",
            batch_num, total_batches, elapsed,
            enriched_n, failed_n, skipped_n, rejected_n,
            stats["enriched"], stats["failed"], stats["rejected_garbage"],
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
    logger.info("  Raw        : %d", stats["raw_candidates"])
    logger.info("  Candidates : %d", stats["total_candidates"])
    logger.info("  Rejected   : %d", stats["rejected_garbage"])
    logger.info("  Sent to LLM: %d", stats["sent_to_llm"])
    logger.info("  Enriched   : %d (%.1f%%)",
                stats["enriched"],
                100 * stats["enriched"] / max(1, stats["total_candidates"]))
    logger.info("  Failed     : %d", stats["failed"])
    logger.info("  MiniMax calls : %d", stats["llm_calls"])
    logger.info("  MiniMax 429s  : %d", stats["llm_429s"])
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
