"""Phase 5 — Google-News wrapper repair (resolve -> extract -> write body).

For EXISTING shared_ticker_events rows whose URL is a news.google.com
wrapper and which are strict-non-usable (headline_only / extraction
failed / no body), this:

  1. resolves the wrapper to its real publisher URL (cache-first),
  2. runs the existing extraction stack on the publisher URL,
  3. if body >= 300 chars AND the body-quality gate passes, UPDATES the
     existing row in place (publisher canonical_url, body, body_length,
     extraction_status=success, headline_only=False, analysis_status
     cleared) so the proven reenrich_news enricher picks it up next,
  4. never INSERTs (no duplicate publisher rows), never bypasses an
     access control (401/403/login/paywall/JS-shell -> recorded failure,
     row left non-usable and retryable).

Enrichment itself is delegated to the already-proven, already-tested
reenrich_news job (run after this) — this script does not call MiniMax.

Idempotent (cache + selection skip already-bodied rows), checkpointed
(per-batch JSON), abortable (resolver-failure breaker).

Requires GOOGLE_NEWS_WRAPPER_RESOLVER_ENABLED=true. Does NOT enable or
use Google News discovery.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("wrapper_repair")

MIN_BODY = 300


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _select_candidates(sb, window_days: int, limit: int) -> list[dict]:
    from app.scripts._dbpage import fetch_all

    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    uni = fetch_all(
        sb, "ticker_universe", "ticker,index_membership,is_active",
        order_col="ticker",
    )
    sp = sorted({
        (u["ticker"] or "").upper()
        for u in uni
        if u.get("index_membership") == "SP500" and u.get("is_active") and u.get("ticker")
    })
    cols = (
        "id,ticker,title,source,source_url,canonical_url,published_at,body,"
        "body_length,extraction_status,analysis_status,headline_only,paywalled,"
        "paywall_detected,rejection_reason,sentiment_score"
    )
    rows: list[dict] = []
    for i in range(0, len(sp), 150):
        rows.extend(fetch_all(
            sb, "shared_ticker_events", cols, order_col="id",
            in_col="ticker", in_values=sp[i:i + 150],
            gte=("published_at", cutoff),
        ))
    out = []
    for r in rows:
        # rejection_reason rows stay out of scope (handled elsewhere, kept
        # retryable). NOTE: sentiment_score is intentionally NOT a filter —
        # ~99% of these rows carry a STALE headline-only sentiment that is
        # never counted usable (headline_only=True). Repair resolves the
        # wrapper, extracts the real body, and resets those stale LLM
        # fields so the proven enricher re-derives from the real article.
        if str(r.get("rejection_reason") or "").strip():
            continue
        url = str(r.get("canonical_url") or r.get("source_url") or "")
        if "news.google.com" not in url:
            continue
        body = str(r.get("body") or "")
        non_usable = (
            r.get("headline_only")
            or str(r.get("analysis_status") or "").lower() == "headline_only"
            or str(r.get("extraction_status") or "").lower() in {"failed", ""}
            or len(body.strip()) < MIN_BODY
            or body.startswith("[No body extracted]")
        )
        # already a real, usable, non-wrapper-flagged row -> skip (idempotent)
        already_good = (
            str(r.get("extraction_status") or "").lower() == "success"
            and not r.get("headline_only")
            and str(r.get("analysis_status") or "").lower() != "headline_only"
            and len(body.strip()) >= MIN_BODY
            and not body.startswith("[No body extracted]")
            and r.get("sentiment_score") is not None
        )
        if non_usable and not already_good:
            out.append(r)
    out.sort(key=lambda x: str(x.get("id")))
    return out[:limit] if limit else out


async def _process_row(sb, row, client, *, timeout, dry_run):
    from app.services.article_scraper import enrich_article_content
    from app.services.gnews_resolver import resolve_with_cache
    from app.services.news_enrichment import assess_article_body_quality
    from app.config import get_settings

    s = get_settings()
    gurl = str(row.get("canonical_url") or row.get("source_url") or "")
    out = {"id": row["id"], "ticker": (row.get("ticker") or "").upper()}
    rr = await resolve_with_cache(
        sb, gurl, client, timeout=timeout,
        write_cache=s.google_news_wrapper_resolver_write_cache,
    )
    out["resolve_status"] = rr["status"]
    out["cached"] = rr.get("cached", False)
    if rr["status"] != "resolved" or not rr.get("resolved_url"):
        out["stage"] = "resolve_failed"
        return out
    pub = rr["resolved_url"]
    out["publisher"] = pub
    out["final_domain"] = rr.get("final_domain")
    try:
        art = {"url": pub, "title": row.get("title") or "",
                "ticker": out["ticker"], "company_name": out["ticker"],
                "source": rr.get("final_domain") or ""}
        res = await asyncio.wait_for(enrich_article_content(art), timeout=45)
    except Exception as exc:  # noqa: BLE001
        out["stage"] = "extract_error"
        out["error"] = str(exc)[:120]
        return out
    raw = str(res.get("body") or "")
    usable, reason, cleaned = assess_article_body_quality({**art, "body": raw})
    body = cleaned if usable else ""
    out["extract_scrape"] = str(res.get("scrape_status"))[:50]
    out["body_len"] = len(body)
    out["quality_pass"] = bool(usable)
    out["reject_reason"] = reason
    if not usable or len(body) < MIN_BODY:
        out["stage"] = "extract_unusable"  # blocked/paywall/js-shell — not bypassed
        return out
    out["stage"] = "eligible"
    out["stale_sentiment_reset"] = row.get("sentiment_score") is not None
    if not dry_run:
        # Replace the explicitly-non-usable headline_only state with the
        # real publisher body, and RESET the stale headline-derived LLM
        # fields so the proven reenrich_news enricher re-derives them from
        # the real article (it selects sentiment_score IS NULL). The old
        # values were never counted usable (headline_only=True), so this is
        # a correctness improvement, not loss of usable data. Provenance of
        # original google url -> publisher is preserved in
        # gnews_wrapper_resolution + this run's report.
        sb.table("shared_ticker_events").update({
            "canonical_url": pub,
            "body": body,
            "body_length": len(body),
            "extraction_status": "success",
            "headline_only": False,
            "analysis_status": None,
            "rejection_reason": None,
            "sentiment_score": None,
            "sentiment_reason": None,
            "tldr": None,
            "what_it_means": None,
            "key_implications": None,
            "impact_tag": None,
            "extraction_provider_used": "gnews_wrapper_resolved",
            "updated_at": _now(),
        }).eq("id", row["id"]).execute()
        out["written"] = True
    return out


async def run(window_days, batch_size, concurrency, timeout, limit,
              min_resolve_rate, dry_run, out_path):
    from app.services.supabase import get_supabase

    sb = get_supabase()
    cands = _select_candidates(sb, window_days, limit)
    total = len(cands)
    log.info("=== Wrapper Repair === window=%dd candidates=%d batch=%d "
             "concurrency=%d dry_run=%s", window_days, total, batch_size,
             concurrency, dry_run)
    stats = Counter()
    by_resolve = Counter()
    by_stage = Counter()
    dom_ok = Counter()
    dom_bad = Counter()
    sem = asyncio.Semaphore(concurrency)
    t_start = time.monotonic()
    n_batches = (total + batch_size - 1) // batch_size or 1
    aborted = None

    async with httpx.AsyncClient(follow_redirects=True) as client:
        async def worker(r):
            async with sem:
                return await _process_row(
                    sb, r, client, timeout=timeout, dry_run=dry_run)

        for b in range(n_batches):
            chunk = cands[b * batch_size:(b + 1) * batch_size]
            if not chunk:
                break
            t_b = time.monotonic()
            results = await asyncio.gather(*[worker(r) for r in chunk])
            for o in results:
                stats["attempted"] += 1
                by_resolve[o.get("resolve_status", "n/a")] += 1
                by_stage[o.get("stage", "n/a")] += 1
                if o.get("resolve_status") == "resolved":
                    stats["resolved"] += 1
                if o.get("stage") == "eligible":
                    stats["eligible"] += 1
                    dom_ok[o.get("final_domain") or "?"] += 1
                    if o.get("written"):
                        stats["written"] += 1
                        if o.get("stale_sentiment_reset"):
                            stats["stale_sentiment_reset"] += 1
                elif o.get("stage") in ("extract_unusable", "extract_error"):
                    dom_bad[o.get("final_domain") or "?"] += 1
            done = stats["attempted"]
            el = time.monotonic() - t_start
            rate = done / el if el else 0
            eta = (total - done) / rate if rate else 0
            res_rate = stats["resolved"] / max(1, done)
            log.info(
                "[BATCH %d/%d] %.1fs done=%d resolved=%d (%.0f%%) eligible=%d "
                "written=%d | elapsed=%.0fs eta=%.0fs",
                b + 1, n_batches, time.monotonic() - t_b, done,
                stats["resolved"], 100 * res_rate, stats["eligible"],
                stats["written"], el, eta,
            )
            # checkpoint
            with open(out_path, "w") as f:
                json.dump({
                    "generated_at": _now(), "window_days": window_days,
                    "total_candidates": total, "batches_done": b + 1,
                    "n_batches": n_batches, "stats": dict(stats),
                    "by_resolve_status": dict(by_resolve),
                    "by_stage": dict(by_stage),
                    "top_domains_recovered": dom_ok.most_common(20),
                    "top_domains_failed": dom_bad.most_common(20),
                    "aborted": aborted, "dry_run": dry_run,
                }, f, default=str)
            # breaker: a full batch resolving almost nothing => Google
            # changed format / blocking — stop, do not thrash.
            if done >= batch_size and res_rate < min_resolve_rate:
                aborted = f"resolver_below_floor({res_rate:.2f}<{min_resolve_rate})"
                log.error("ABORT: %s", aborted)
                break

    el = time.monotonic() - t_start
    summary = {
        "generated_at": _now(), "window_days": window_days,
        "total_candidates": total, "runtime_s": round(el, 1),
        "stats": dict(stats), "by_resolve_status": dict(by_resolve),
        "by_stage": dict(by_stage),
        "top_domains_recovered": dom_ok.most_common(25),
        "top_domains_failed": dom_bad.most_common(25),
        "resolved_pct": round(100 * stats["resolved"] / max(1, stats["attempted"]), 1),
        "eligible_pct": round(100 * stats["eligible"] / max(1, stats["attempted"]), 1),
        "aborted": aborted, "dry_run": dry_run,
        "result": "ABORTED" if aborted else "COMPLETE",
    }
    with open(out_path, "w") as f:
        json.dump(summary, f, default=str)
    log.info("=== Wrapper Repair %s === attempted=%d resolved=%d (%.1f%%) "
             "eligible=%d written=%d runtime=%.0fs",
             summary["result"], stats["attempted"], stats["resolved"],
             summary["resolved_pct"], stats["eligible"], stats["written"], el)
    print(json.dumps(summary, default=str))
    return summary


def main() -> None:
    from app.config import get_settings

    ap = argparse.ArgumentParser()
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--batch-size", type=int, default=0)
    ap.add_argument("--max-concurrency", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=0.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-resolve-rate", type=float, default=0.20)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="/tmp/wrapper_repair.json")
    a = ap.parse_args()
    s = get_settings()
    if not s.google_news_wrapper_resolver_enabled:
        print(json.dumps({
            "result": "REFUSED",
            "reason": "GOOGLE_NEWS_WRAPPER_RESOLVER_ENABLED is false",
        }))
        sys.exit(2)
    asyncio.run(run(
        window_days=a.window_days,
        batch_size=a.batch_size or s.google_news_wrapper_repair_batch_size,
        concurrency=a.max_concurrency or s.google_news_wrapper_resolver_max_concurrency,
        timeout=a.timeout or s.google_news_wrapper_resolver_timeout_seconds,
        limit=a.limit, min_resolve_rate=a.min_resolve_rate,
        dry_run=a.dry_run, out_path=a.out,
    ))


if __name__ == "__main__":
    main()
