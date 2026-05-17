#!/usr/bin/env python3
"""Finnhub-first 10-ticker canary.

Runs the full pipeline step-by-step and reports granular metrics per ticker:
  finnhub_raw | finnhub_deduped | finnhub_relevant | finnhub_extracted
  finnhub_usable_7d | google_used | google_added_usable | final_status | top_failure

Usage:
    cd backend && python3 scripts/canary_10_tickers.py

PAUSE_SYSTEM_SCHEDULER=true is enforced by env (set in .env).
This script is additive — it only adds/updates rows in shared_ticker_events.
"""
import asyncio
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

CANARY_TICKERS = [
    "AMD", "AAPL", "NVDA", "MSFT", "HOOD",
    "SMCI", "JPM", "XOM", "GOOGL", "META",
]

LIMIT_PER_TICKER = 10
GOOGLE_FALLBACK_MIN = 3


async def run_canary() -> None:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    from app.services.supabase import get_supabase
    from app.pipeline.finnhub_news import fetch_finnhub_ticker_news
    from app.services.candidate_ranker import rank_and_filter_candidates, get_domain_policy
    from app.services.article_scraper import enrich_articles_content
    from app.services.news_enrichment import enrich_and_store_articles_batch, GOOGLE_FALLBACK_MIN_USABLE_ARTICLES
    from app.pipeline.rss_ingest import fetch_google_company_rss
    from app.pipeline.news_normalizer import normalize_news_batch
    from app.services.ticker_cache_service import get_metadata_map

    supabase = get_supabase()

    print("=" * 80)
    print(f"FINNHUB-FIRST 10-TICKER CANARY  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    # ── Step 1: Finnhub discovery ────────────────────────────────────────────
    print(f"\n[1/6] Fetching Finnhub company-news (7-day window) …")
    per_ticker, fh_metrics = await fetch_finnhub_ticker_news(
        CANARY_TICKERS, days=7, limit_per_ticker=LIMIT_PER_TICKER
    )

    print(f"  Finnhub calls: {fh_metrics['calls']}  |  429s: {fh_metrics['rate_limited']}  |  raw articles: {fh_metrics['articles_raw']}")
    if fh_metrics["errors"]:
        print(f"  Errors: {fh_metrics['errors']}")

    # Per-ticker raw/deduped counts
    raw_counts: dict[str, int] = fh_metrics["per_ticker_raw"]
    deduped_counts: dict[str, int] = {t: len(arts) for t, arts in per_ticker.items()}

    # ── Step 2: Domain policy filter ────────────────────────────────────────
    print(f"\n[2/6] Applying domain policy filter …")
    all_finnhub = [a for arts in per_ticker.values() for a in arts]
    filtered = rank_and_filter_candidates(all_finnhub, skip_score_below=15.0)

    relevant_counts: dict[str, int] = defaultdict(int)
    rejected_counts: dict[str, int] = defaultdict(int)
    rejection_reasons: dict[str, list[str]] = defaultdict(list)
    domain_tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for a in all_finnhub:
        t = str(a.get("ticker") or "").upper()
        url = str(a.get("url") or "")
        policy = get_domain_policy(url)
        domain = url.split("/")[2].replace("www.", "") if "//" in url else url[:40]
        domain_tally[t][f"{domain}({policy})"] += 1

    for a in filtered:
        t = str(a.get("ticker") or "").upper()
        relevant_counts[t] += 1

    rejected = [a for a in all_finnhub if a not in filtered]
    for a in all_finnhub:
        score_a = next(
            (f.get("candidate_score", 0) for f in filtered if f.get("url") == a.get("url")),
            None,
        )
        if score_a is None:
            t = str(a.get("ticker") or "").upper()
            rejected_counts[t] += 1
            reason = a.get("candidate_rejection_reason") or get_domain_policy(str(a.get("url") or ""))
            rejection_reasons[t].append(str(reason))

    print(f"  Passed filter: {len(filtered)}  |  Rejected: {len(all_finnhub) - len(filtered)}")

    # ── Step 3: Body extraction ──────────────────────────────────────────────
    print(f"\n[3/6] Extracting article bodies from Finnhub URLs ({len(filtered)} articles) …")
    t0 = datetime.now(timezone.utc)
    if filtered:
        extracted = await enrich_articles_content(filtered, max_concurrency=4)
    else:
        extracted = []
    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    print(f"  Extraction done in {elapsed:.1f}s")

    # Count extraction results per ticker and per method
    extracted_ok: dict[str, int] = defaultdict(int)
    extracted_fail: dict[str, int] = defaultdict(int)
    method_counts: dict[str, int] = defaultdict(int)
    failure_reasons: dict[str, list[str]] = defaultdict(list)

    for a in extracted:
        t = str(a.get("ticker") or "").upper()
        status = str(a.get("scrape_status") or "")
        if status.startswith("ok"):
            extracted_ok[t] += 1
            method = status.replace("ok_", "").replace("ok", "jina/html")
            method_counts[method] += 1
        else:
            extracted_fail[t] += 1
            failure_reasons[t].append(status or "unknown")

    print(f"  Extraction success: {sum(extracted_ok.values())}  |  Fail: {sum(extracted_fail.values())}")
    print(f"  Method breakdown: {dict(method_counts)}")

    # ── Step 4: LLM enrichment + store ───────────────────────────────────────
    print(f"\n[4/6] LLM enrichment + DB store …")
    stored = await enrich_and_store_articles_batch(
        supabase, extracted, max_concurrency=3, skip_existing=True
    )

    enriched_complete: dict[str, int] = defaultdict(int)
    for a in stored:
        t = str(a.get("ticker") or "").upper()
        has_sent = a.get("sentiment_score") is not None
        has_reason = bool(a.get("sentiment_reason"))
        if has_sent and has_reason:
            enriched_complete[t] += 1

    print(f"  Stored: {len(stored)}  |  With sentiment: {sum(enriched_complete.values())}")

    # ── Step 5: DB usable count after Finnhub ────────────────────────────────
    print(f"\n[5/6] Querying DB for usable_7d counts …")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    rows = (
        supabase.table("shared_ticker_events")
        .select("ticker,extraction_status,paywalled,sentiment_score,tldr,what_it_means,key_implications")
        .in_("ticker", CANARY_TICKERS)
        .gte("published_at", cutoff)
        .execute()
        .data or []
    )

    db_stats: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "ok": 0, "fail": 0, "pay": 0, "blk": 0, "usable": 0,
                 "has_tldr": 0, "has_what": 0, "miss_sent": 0}
    )
    for row in rows:
        t = str(row.get("ticker") or "").upper()
        s = row.get("extraction_status")
        p = row.get("paywalled", False)
        sent = row.get("sentiment_score")
        db_stats[t]["total"] += 1
        if s == "success": db_stats[t]["ok"] += 1
        elif s == "failed": db_stats[t]["fail"] += 1
        elif s == "paywalled": db_stats[t]["pay"] += 1
        elif s == "blocked": db_stats[t]["blk"] += 1
        if s == "success" and not p and sent is not None:
            db_stats[t]["usable"] += 1
        if sent is None:
            db_stats[t]["miss_sent"] += 1
        if row.get("tldr"):
            db_stats[t]["has_tldr"] += 1
        if row.get("what_it_means"):
            db_stats[t]["has_what"] += 1

    finnhub_usable: dict[str, int] = {t: db_stats[t]["usable"] for t in CANARY_TICKERS}

    # ── Step 6: Google fallback for < 3 usable ───────────────────────────────
    fallback_tickers = [t for t in CANARY_TICKERS if finnhub_usable.get(t, 0) < GOOGLE_FALLBACK_MIN]
    google_added_usable: dict[str, int] = {}
    google_used: dict[str, bool] = {t: False for t in CANARY_TICKERS}
    google_429s = 0

    if fallback_tickers:
        print(f"\n[6/6] Google fallback for {len(fallback_tickers)} tickers: {fallback_tickers}")
        metadata_map = get_metadata_map(supabase, fallback_tickers)
        google_raw = await fetch_google_company_rss(
            fallback_tickers, ticker_metadata=metadata_map, limit_per_ticker=LIMIT_PER_TICKER
        )
        google_norm = normalize_news_batch(google_raw, "company_news") if google_raw else []
        google_stored = await enrich_and_store_articles_batch(
            supabase, google_norm, max_concurrency=3, skip_existing=True
        )
        for t in fallback_tickers:
            google_used[t] = True

        # Re-query DB for these tickers to see improvement
        if fallback_tickers:
            rows2 = (
                supabase.table("shared_ticker_events")
                .select("ticker,extraction_status,paywalled,sentiment_score")
                .in_("ticker", fallback_tickers)
                .gte("published_at", cutoff)
                .execute()
                .data or []
            )
            usable2: dict[str, int] = defaultdict(int)
            for row in rows2:
                t = str(row.get("ticker") or "").upper()
                if (row.get("extraction_status") == "success"
                        and not row.get("paywalled", False)
                        and row.get("sentiment_score") is not None):
                    usable2[t] += 1
            for t in fallback_tickers:
                google_added_usable[t] = max(0, usable2.get(t, 0) - finnhub_usable.get(t, 0))
                finnhub_usable[t] = usable2.get(t, 0)
    else:
        print(f"\n[6/6] Google fallback: NOT NEEDED — all tickers have ≥{GOOGLE_FALLBACK_MIN} usable articles")

    # ── Report ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("CANARY RESULTS")
    print("=" * 80)

    # Summary metrics
    print(f"\nFinnhub calls: {fh_metrics['calls']}  |  429s: {fh_metrics['rate_limited']}  |  raw: {fh_metrics['articles_raw']}")
    print(f"Google calls used: {len(fallback_tickers)}  |  Google 429s: {google_429s}")
    print(f"Extraction method breakdown: {dict(method_counts)}")

    # Per-ticker table
    hdr = (
        f"  {'ticker':<6} {'fh_raw':>6} {'fh_ded':>6} {'fh_rel':>6} "
        f"{'fh_ext':>6} {'fh_usbl':>7} {'g_used':>6} {'g_add':>5} "
        f"{'final_st':<10} {'top_fail'}"
    )
    print(f"\n{hdr}")
    print("  " + "-" * (len(hdr) - 2))

    for ticker in CANARY_TICKERS:
        fh_raw = raw_counts.get(ticker, 0)
        fh_ded = deduped_counts.get(ticker, 0)
        fh_rel = relevant_counts.get(ticker, 0)
        fh_ext = extracted_ok.get(ticker, 0)
        fh_usbl = db_stats[ticker]["usable"]
        g_used = "YES" if google_used.get(ticker) else "no"
        g_add = google_added_usable.get(ticker, 0) if google_used.get(ticker) else "-"
        final_usable = finnhub_usable.get(ticker, 0)
        final_status = "SCORED" if final_usable >= GOOGLE_FALLBACK_MIN else "limited"

        # Top failure reason
        all_failures = rejection_reasons.get(ticker, []) + failure_reasons.get(ticker, [])
        if not all_failures:
            top_fail = "none" if fh_raw > 0 else "no_finnhub_articles"
        else:
            from collections import Counter
            top_fail = Counter(all_failures).most_common(1)[0][0][:30]

        print(
            f"  {ticker:<6} {fh_raw:>6} {fh_ded:>6} {fh_rel:>6} "
            f"{fh_ext:>6} {fh_usbl:>7} {g_used:>6} {str(g_add):>5} "
            f"{final_status:<10} {top_fail}"
        )

    # DB detail table
    print(f"\n  {'ticker':<6} {'7d':>4} {'ok':>4} {'fail':>4} {'pay':>4} {'blk':>4} {'usable':>7} {'tldr':>5} {'what':>5}")
    print("  " + "-" * 54)
    for ticker in CANARY_TICKERS:
        s = db_stats[ticker]
        print(
            f"  {ticker:<6} {s['total']:>4} {s['ok']:>4} {s['fail']:>4} "
            f"{s['pay']:>4} {s['blk']:>4} {s['usable']:>7} {s['has_tldr']:>5} {s['has_what']:>5}"
        )

    # Domain breakdown (top sources per ticker)
    print("\nFinnhub source domains per ticker:")
    for ticker in CANARY_TICKERS:
        domains = domain_tally.get(ticker, {})
        if domains:
            top = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:4]
            top_str = ", ".join(f"{d}×{c}" for d, c in top)
            print(f"  {ticker}: {top_str}")
        else:
            print(f"  {ticker}: (no articles)")

    # Final verdict
    scored = [t for t in CANARY_TICKERS if finnhub_usable.get(t, 0) >= GOOGLE_FALLBACK_MIN]
    limited = [t for t in CANARY_TICKERS if finnhub_usable.get(t, 0) < GOOGLE_FALLBACK_MIN]
    finnhub_only_scored = [t for t in CANARY_TICKERS if finnhub_usable.get(t, 0) >= GOOGLE_FALLBACK_MIN and not google_used.get(t)]

    print(f"\n{'=' * 80}")
    print(f"VERDICT")
    print(f"{'=' * 80}")
    print(f"  SCORED (≥{GOOGLE_FALLBACK_MIN} usable):  {len(scored)}/10  →  {scored}")
    print(f"  Finnhub-only SCORED:  {len(finnhub_only_scored)}/10  →  {finnhub_only_scored}")
    print(f"  still limited:  {len(limited)}/10  →  {limited}")

    if len(finnhub_only_scored) >= 8:
        print(f"\n  ✓ Finnhub can support News Sentiment for major tickers without Google.")
    elif len(finnhub_only_scored) >= 5:
        print(f"\n  ~ Finnhub supports most tickers; Google fallback needed for {limited}.")
    else:
        print(f"\n  ✗ Finnhub alone is insufficient — investigate top_failure per ticker above.")

    print("\n[DONE]")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    asyncio.run(run_canary())
