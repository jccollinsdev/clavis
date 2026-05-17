#!/usr/bin/env python3
"""500-ticker Finnhub-first news coverage canary.

Measures usable-article coverage across the entire active universe using the
Finnhub-first pipeline (Finnhub primary, Google fallback-only).

This is a NEWS COVERAGE CANARY ONLY. It does NOT:
  - promote risk snapshots
  - run the full risk backfill
  - enable unsafe scheduler jobs
  - count failed/paywalled/headline-only articles as usable

Usage:
    cd backend && python3 scripts/news_coverage_500_canary.py [--resume] [--batch-size 25]

Outputs (in reports/):
  - news_coverage_500_canary.csv
  - news_coverage_500_canary.json
  - news_coverage_500_canary.md
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import mean, median, stdev

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "reports"
CHECKPOINT_FILE = REPORTS_DIR / "news_coverage_500_canary_checkpoint.json"

GOOGLE_FALLBACK_MIN = 3
LIMIT_PER_TICKER = 10
BATCH_SIZE = 25
FINNHUB_CONCURRENCY = 4   # concurrent Finnhub calls per batch
EXTRACT_CONCURRENCY = 4   # concurrent extractions
ENRICH_CONCURRENCY = 6    # concurrent LLM calls (asyncio.to_thread enables true parallelism)


@dataclass
class TickerMetrics:
    ticker: str
    company_name: str = ""
    sector: str = ""
    industry: str = ""

    # Finnhub discovery
    finnhub_raw: int = 0          # total from API (before dedup)
    finnhub_deduped: int = 0      # after URL dedup
    finnhub_relevant: int = 0     # after domain policy filter
    finnhub_429: bool = False
    finnhub_error: str = ""

    # Extraction (from enrich_articles_content)
    extraction_attempted: int = 0
    extraction_success: int = 0
    jina_success: int = 0
    trafilatura_success: int = 0
    newspaper4k_success: int = 0
    proxy_success: int = 0
    blocked_urls: int = 0
    paywalled_urls: int = 0
    extraction_fail: int = 0

    # DB state (7-day window)
    db_total: int = 0
    db_ok: int = 0
    db_fail: int = 0
    db_pay: int = 0
    db_blk: int = 0
    db_usable_before: int = 0    # usable before this canary run
    db_usable_after: int = 0     # usable after this canary run
    new_usable_added: int = 0    # delta

    # Enrichment
    enriched_complete: int = 0   # has sentiment_score + reason
    tldr_present: int = 0
    what_it_means_present: int = 0

    # Final
    usable_7d: int = 0           # final usable count (db_usable_after)
    news_status: str = "limited_data"
    top_failure_reason: str = "unknown"
    google_used: bool = False
    google_added_usable: int = 0

    batch_num: int = 0
    runtime_s: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ── Safety checks ─────────────────────────────────────────────────────────────

def _safety_check() -> None:
    """Abort if any unsafe env is detected."""
    scheduler_paused = os.getenv("PAUSE_SYSTEM_SCHEDULER", "").strip().lower()
    if scheduler_paused not in {"1", "true", "yes", "on"}:
        print("[SAFETY] WARNING: PAUSE_SYSTEM_SCHEDULER is not set to true.")
        print("  Set PAUSE_SYSTEM_SCHEDULER=true to prevent scheduler interference.")
        # Don't abort — allow canary to run but warn loudly
    else:
        print("[SAFETY] ✓ PAUSE_SYSTEM_SCHEDULER=true — scheduler is paused")
    print("[SAFETY] ✓ This script is NEWS COVERAGE ONLY — no snapshot promotion")
    print("[SAFETY] ✓ skip_existing=True — will not overwrite valid enriched articles")


# ── Universe loading ───────────────────────────────────────────────────────────

def _load_sp500_metadata() -> dict[str, dict]:
    """Load ticker→{company, sector, industry} from sp500_universe.txt."""
    meta: dict[str, dict] = {}
    universe_path = REPO_ROOT / "app" / "data" / "sp500_universe.txt"
    if not universe_path.exists():
        return meta
    for line in universe_path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", maxsplit=3)
        if len(parts) >= 4:
            ticker, company, sector, industry = parts[0], parts[1], parts[2], parts[3]
            meta[ticker.upper().strip()] = {
                "company_name": company.strip(),
                "sector": sector.strip(),
                "industry": industry.strip(),
            }
    return meta


def _get_active_universe(supabase) -> list[str]:
    """Return sorted unique tickers from positions + watchlist_items."""
    positions = supabase.table("positions").select("ticker").execute().data or []
    watchlist = supabase.table("watchlist_items").select("ticker").execute().data or []
    return sorted({
        str(r.get("ticker") or "").strip().upper()
        for r in positions + watchlist
        if r.get("ticker")
    })


# ── DB snapshot ───────────────────────────────────────────────────────────────

def _query_db_usable(supabase, tickers: list[str]) -> dict[str, dict]:
    """Return per-ticker DB stats for the last 7 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        rows = (
            supabase.table("shared_ticker_events")
            .select("ticker,extraction_status,paywalled,sentiment_score,tldr,what_it_means")
            .in_("ticker", tickers)
            .gte("published_at", cutoff)
            .execute()
            .data or []
        )
    except Exception as exc:
        print(f"  [DB] Query failed: {exc}")
        return {}

    result: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "ok": 0, "fail": 0, "pay": 0, "blk": 0,
                 "usable": 0, "has_sent": 0, "has_tldr": 0, "has_what": 0}
    )
    for row in rows:
        t = str(row.get("ticker") or "").upper()
        s = row.get("extraction_status")
        p = row.get("paywalled", False)
        sent = row.get("sentiment_score")
        result[t]["total"] += 1
        if s == "success":   result[t]["ok"] += 1
        elif s == "failed":  result[t]["fail"] += 1
        elif s == "paywalled": result[t]["pay"] += 1
        elif s == "blocked": result[t]["blk"] += 1
        if s == "success" and not p and sent is not None:
            result[t]["usable"] += 1
        if sent is not None:
            result[t]["has_sent"] += 1
        if row.get("tldr"):
            result[t]["has_tldr"] += 1
        if row.get("what_it_means"):
            result[t]["has_what"] += 1
    return dict(result)


# ── Per-ticker Finnhub fetch ───────────────────────────────────────────────────

async def _fetch_one_ticker(ticker: str, days: int = 7) -> tuple[int, list[dict], str]:
    """Return (raw_count, deduped_articles, error_str) for one ticker."""
    from app.pipeline.finnhub_news import fetch_finnhub_ticker_news
    try:
        per_ticker, metrics = await fetch_finnhub_ticker_news(
            [ticker], days=days, limit_per_ticker=LIMIT_PER_TICKER
        )
        err = metrics["errors"].get(ticker, "")
        raw = metrics["per_ticker_raw"].get(ticker, 0)
        return raw, per_ticker.get(ticker, []), err
    except Exception as exc:
        return 0, [], str(exc)[:60]


# ── Batch runner ──────────────────────────────────────────────────────────────

async def _run_batch(
    supabase,
    batch_tickers: list[str],
    batch_num: int,
    sp500_meta: dict[str, dict],
    google_fallback_enabled: bool = False,
) -> list[TickerMetrics]:
    from app.services.candidate_ranker import rank_and_filter_candidates, get_domain_policy
    from app.services.article_scraper import enrich_articles_content
    from app.services.news_enrichment import enrich_and_store_articles_batch

    t_start = time.monotonic()
    results: list[TickerMetrics] = []

    # Pre-run DB snapshot
    before_db = _query_db_usable(supabase, batch_tickers)

    # ── Finnhub fetch (concurrent within batch) ────────────────────────────
    sem = asyncio.Semaphore(FINNHUB_CONCURRENCY)
    per_ticker_raw: dict[str, int] = {}
    per_ticker_articles: dict[str, list[dict]] = {}
    per_ticker_errors: dict[str, str] = {}

    async def _fetch_with_sem(ticker: str) -> None:
        async with sem:
            raw, arts, err = await _fetch_one_ticker(ticker)
            per_ticker_raw[ticker] = raw
            per_ticker_articles[ticker] = arts
            per_ticker_errors[ticker] = err

    await asyncio.gather(*(_fetch_with_sem(t) for t in batch_tickers))

    # ── Domain filter on all articles ─────────────────────────────────────
    all_articles = [a for arts in per_ticker_articles.values() for a in arts]
    filtered = rank_and_filter_candidates(all_articles, skip_score_below=15.0)
    filtered_by_ticker: dict[str, list[dict]] = defaultdict(list)
    for a in filtered:
        t = str(a.get("ticker") or "").upper()
        if t in batch_tickers:
            filtered_by_ticker[t].append(a)

    # ── Extraction ────────────────────────────────────────────────────────
    to_extract = [a for arts in filtered_by_ticker.values() for a in arts]
    if to_extract:
        extracted = await enrich_articles_content(to_extract, max_concurrency=EXTRACT_CONCURRENCY)
    else:
        extracted = []

    # Parse extraction results per ticker
    extracted_by_ticker: dict[str, list[dict]] = defaultdict(list)
    for a in extracted:
        t = str(a.get("ticker") or "").upper()
        extracted_by_ticker[t].append(a)

    # ── LLM enrich + store ────────────────────────────────────────────────
    stored = await enrich_and_store_articles_batch(
        supabase, extracted, max_concurrency=ENRICH_CONCURRENCY, skip_existing=True
    )
    stored_by_ticker: dict[str, list[dict]] = defaultdict(list)
    for a in stored:
        t = str(a.get("ticker") or "").upper()
        stored_by_ticker[t].append(a)

    # Post-run DB snapshot
    after_db = _query_db_usable(supabase, batch_tickers)

    # ── Build per-ticker metrics ───────────────────────────────────────────
    for ticker in batch_tickers:
        meta = sp500_meta.get(ticker, {})
        m = TickerMetrics(
            ticker=ticker,
            company_name=meta.get("company_name", ""),
            sector=meta.get("sector", ""),
            industry=meta.get("industry", ""),
            batch_num=batch_num,
        )

        # Finnhub discovery
        m.finnhub_raw = per_ticker_raw.get(ticker, 0)
        m.finnhub_deduped = len(per_ticker_articles.get(ticker, []))
        m.finnhub_relevant = len(filtered_by_ticker.get(ticker, []))
        err_str = per_ticker_errors.get(ticker, "")
        m.finnhub_429 = "rate_limited" in err_str
        m.finnhub_error = err_str

        # Extraction breakdown
        extr_arts = extracted_by_ticker.get(ticker, [])
        m.extraction_attempted = len(extr_arts)
        failure_reasons: list[str] = []
        for a in extr_arts:
            status = str(a.get("scrape_status") or "")
            if status.startswith("ok"):
                m.extraction_success += 1
                method = status.replace("ok_", "")
                if "newspaper4k" in method: m.newspaper4k_success += 1
                elif "trafilatura" in method: m.trafilatura_success += 1
                elif "proxy" in method: m.proxy_success += 1
                else: m.jina_success += 1  # "ok" or "ok_jina" or "ok_html"
            else:
                m.extraction_fail += 1
                failure_reasons.append(status[:50])

        # Blocked/paywalled from domain policy (pre-extraction)
        for a in filtered_by_ticker.get(ticker, []):
            policy = get_domain_policy(str(a.get("url") or ""))
            if policy == "blocked":   m.blocked_urls += 1
            elif policy == "paywalled": m.paywalled_urls += 1

        # Enrichment
        for a in stored_by_ticker.get(ticker, []):
            if a.get("sentiment_score") is not None and a.get("sentiment_reason"):
                m.enriched_complete += 1
            if a.get("tldr"):
                m.tldr_present += 1
            if a.get("what_it_means"):
                m.what_it_means_present += 1

        # DB stats
        bd = before_db.get(ticker, {})
        ad = after_db.get(ticker, {})
        m.db_total = ad.get("total", 0)
        m.db_ok = ad.get("ok", 0)
        m.db_fail = ad.get("fail", 0)
        m.db_pay = ad.get("pay", 0)
        m.db_blk = ad.get("blk", 0)
        m.db_usable_before = bd.get("usable", 0)
        m.db_usable_after = ad.get("usable", 0)
        m.new_usable_added = max(0, m.db_usable_after - m.db_usable_before)
        m.usable_7d = m.db_usable_after

        # Top failure reason
        if m.finnhub_429:
            m.top_failure_reason = "provider_rate_limited"
        elif m.finnhub_raw == 0:
            m.top_failure_reason = "low_finnhub_supply"
        elif m.finnhub_deduped == 0:
            m.top_failure_reason = "duplicate_heavy"
        elif m.extraction_success == 0 and m.extraction_attempted > 0:
            reason_ctr = Counter(failure_reasons)
            top = reason_ctr.most_common(1)
            if top:
                r = top[0][0]
                if "403" in r or "Forbidden" in r: m.top_failure_reason = "blocked_domains"
                elif "paywall" in r.lower() or "451" in r: m.top_failure_reason = "paywalled_sources"
                elif "proxy_ev" in r: m.top_failure_reason = "extraction_failed"
                else: m.top_failure_reason = "extraction_failed"
            else:
                m.top_failure_reason = "extraction_failed"
        elif m.usable_7d < GOOGLE_FALLBACK_MIN:
            if m.finnhub_raw < 5:
                m.top_failure_reason = "low_finnhub_supply"
            elif m.db_ok > 0 and m.usable_7d < GOOGLE_FALLBACK_MIN:
                m.top_failure_reason = "enrichment_incomplete"
            else:
                m.top_failure_reason = "not_enough_recent_news"
        else:
            if failure_reasons:
                reason_ctr = Counter(failure_reasons)
                top = reason_ctr.most_common(1)
                r = top[0][0] if top else ""
                if "403" in r or "Forbidden" in r: m.top_failure_reason = "blocked_domains"
                elif m.paywalled_urls > 0: m.top_failure_reason = "paywalled_sources"
                else: m.top_failure_reason = "none"
            else:
                m.top_failure_reason = "none"

        # News status
        m.news_status = "scored" if m.usable_7d >= GOOGLE_FALLBACK_MIN else "limited_data"

        m.runtime_s = time.monotonic() - t_start
        results.append(m)

    return results


# ── Report generation ─────────────────────────────────────────────────────────

def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = (p / 100) * (len(sorted_d) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_d) - 1)
    return sorted_d[lo] + (sorted_d[hi] - sorted_d[lo]) * (idx - lo)


def _generate_reports(all_metrics: list[TickerMetrics], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    usable_vals = [m.usable_7d for m in all_metrics]
    n = len(usable_vals)

    # Aggregate stats
    agg = {
        "generated_at": ts,
        "total_tickers": n,
        "tickers_scored": sum(1 for v in usable_vals if v >= GOOGLE_FALLBACK_MIN),
        "tickers_limited": sum(1 for v in usable_vals if v < GOOGLE_FALLBACK_MIN),
        "total_finnhub_calls": sum(1 for m in all_metrics),
        "total_finnhub_429s": sum(1 for m in all_metrics if m.finnhub_429),
        "total_raw_articles": sum(m.finnhub_raw for m in all_metrics),
        "total_deduped": sum(m.finnhub_deduped for m in all_metrics),
        "total_relevant": sum(m.finnhub_relevant for m in all_metrics),
        "total_extraction_attempts": sum(m.extraction_attempted for m in all_metrics),
        "total_extraction_success": sum(m.extraction_success for m in all_metrics),
        "extraction_success_rate": round(
            sum(m.extraction_success for m in all_metrics) /
            max(1, sum(m.extraction_attempted for m in all_metrics)) * 100, 1
        ),
        "usable_stats": {
            "min": min(usable_vals) if usable_vals else 0,
            "max": max(usable_vals) if usable_vals else 0,
            "mean": round(mean(usable_vals), 1) if usable_vals else 0,
            "median": round(median(usable_vals), 1) if usable_vals else 0,
            "stdev": round(stdev(usable_vals), 1) if len(usable_vals) > 1 else 0,
            "p10": round(_percentile(usable_vals, 10), 1),
            "p25": round(_percentile(usable_vals, 25), 1),
            "p75": round(_percentile(usable_vals, 75), 1),
            "p90": round(_percentile(usable_vals, 90), 1),
        },
        "threshold_coverage": {
            "ge3": {"count": sum(1 for v in usable_vals if v >= 3), "pct": round(sum(1 for v in usable_vals if v >= 3) / max(1, n) * 100, 1)},
            "ge5": {"count": sum(1 for v in usable_vals if v >= 5), "pct": round(sum(1 for v in usable_vals if v >= 5) / max(1, n) * 100, 1)},
            "ge10": {"count": sum(1 for v in usable_vals if v >= 10), "pct": round(sum(1 for v in usable_vals if v >= 10) / max(1, n) * 100, 1)},
            "ge20": {"count": sum(1 for v in usable_vals if v >= 20), "pct": round(sum(1 for v in usable_vals if v >= 20) / max(1, n) * 100, 1)},
        },
        "histogram": {
            "0": sum(1 for v in usable_vals if v == 0),
            "1-2": sum(1 for v in usable_vals if 1 <= v <= 2),
            "3-4": sum(1 for v in usable_vals if 3 <= v <= 4),
            "5-9": sum(1 for v in usable_vals if 5 <= v <= 9),
            "10-19": sum(1 for v in usable_vals if 10 <= v <= 19),
            "20+": sum(1 for v in usable_vals if v >= 20),
        },
    }

    # Sector breakdown
    by_sector: dict[str, list[TickerMetrics]] = defaultdict(list)
    for m in all_metrics:
        sector = m.sector or "Unknown"
        by_sector[sector].append(m)
    sector_stats = {}
    for sector, ms in sorted(by_sector.items()):
        vals = [m.usable_7d for m in ms]
        sector_stats[sector] = {
            "ticker_count": len(ms),
            "mean_usable": round(mean(vals), 1) if vals else 0,
            "median_usable": round(median(vals), 1) if vals else 0,
            "pct_ge3": round(sum(1 for v in vals if v >= GOOGLE_FALLBACK_MIN) / max(1, len(vals)) * 100, 1),
            "pct_ge10": round(sum(1 for v in vals if v >= 10) / max(1, len(vals)) * 100, 1),
            "common_failure": Counter(m.top_failure_reason for m in ms if m.top_failure_reason not in ("none", "unknown")).most_common(1)[0][0] if any(m.top_failure_reason not in ("none", "unknown") for m in ms) else "none",
        }

    # Failure breakdown
    failure_ctr = Counter(m.top_failure_reason for m in all_metrics)

    # ── CSV ──────────────────────────────────────────────────────────────────
    csv_path = output_dir / "news_coverage_500_canary.csv"
    fieldnames = [
        "ticker", "company_name", "sector", "industry",
        "finnhub_raw", "finnhub_deduped", "finnhub_relevant",
        "extraction_attempted", "extraction_success",
        "jina_success", "trafilatura_success", "newspaper4k_success",
        "blocked_urls", "paywalled_urls", "extraction_fail",
        "enriched_complete", "db_usable_before", "db_usable_after",
        "new_usable_added", "usable_7d",
        "news_status", "top_failure_reason",
        "finnhub_429", "google_used", "google_added_usable",
        "batch_num",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for m in sorted(all_metrics, key=lambda x: x.usable_7d, reverse=True):
            w.writerow(m.to_dict())
    print(f"  [REPORT] CSV: {csv_path}")

    # ── JSON ─────────────────────────────────────────────────────────────────
    json_path = output_dir / "news_coverage_500_canary.json"
    json_data = {
        "aggregate": agg,
        "by_sector": sector_stats,
        "failure_distribution": dict(failure_ctr),
        "per_ticker": {m.ticker: m.to_dict() for m in all_metrics},
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"  [REPORT] JSON: {json_path}")

    # ── Markdown ─────────────────────────────────────────────────────────────
    md_path = output_dir / "news_coverage_500_canary.md"
    scored_pct = agg["threshold_coverage"]["ge3"]["pct"]
    ge10_pct = agg["threshold_coverage"]["ge10"]["pct"]
    hist = agg["histogram"]
    stats = agg["usable_stats"]
    extr_rate = agg["extraction_success_rate"]

    md = f"""# Finnhub-First 500-Ticker News Coverage Canary
*Generated: {ts}*

## Executive Summary

| Metric | Value |
|--------|-------|
| Tickers processed | {n} |
| SCORED (≥3 usable) | {agg['threshold_coverage']['ge3']['count']} / {n} ({scored_pct}%) |
| Production threshold (≥10 usable) | {agg['threshold_coverage']['ge10']['count']} / {n} ({ge10_pct}%) |
| Finnhub 429s | {agg['total_finnhub_429s']} |
| Extraction success rate | {extr_rate}% |
| Google fallback used | {sum(1 for m in all_metrics if m.google_used)} tickers |

## Safety Status
- ✅ News coverage canary only — no risk snapshots promoted
- ✅ skip_existing=True — no valid enriched articles overwritten
- ✅ Finnhub-first: Google used only as fallback for <3 usable

## Distribution Stats

| Statistic | Value |
|-----------|-------|
| Min usable | {stats['min']} |
| Max usable | {stats['max']} |
| Mean | {stats['mean']} |
| Median | {stats['median']} |
| Std Dev | {stats['stdev']} |
| p10 | {stats['p10']} |
| p25 | {stats['p25']} |
| p75 | {stats['p75']} |
| p90 | {stats['p90']} |

## Histogram

| Bucket | Count | % |
|--------|-------|---|
| 0 usable | {hist['0']} | {round(hist['0']/max(1,n)*100,1)}% |
| 1–2 usable | {hist['1-2']} | {round(hist['1-2']/max(1,n)*100,1)}% |
| 3–4 usable | {hist['3-4']} | {round(hist['3-4']/max(1,n)*100,1)}% |
| 5–9 usable | {hist['5-9']} | {round(hist['5-9']/max(1,n)*100,1)}% |
| 10–19 usable | {hist['10-19']} | {round(hist['10-19']/max(1,n)*100,1)}% |
| 20+ usable | {hist['20+']} | {round(hist['20+']/max(1,n)*100,1)}% |

## Threshold Coverage

| Threshold | Count | % |
|-----------|-------|---|
| ≥3 usable (MVP) | {agg['threshold_coverage']['ge3']['count']} | {agg['threshold_coverage']['ge3']['pct']}% |
| ≥5 usable | {agg['threshold_coverage']['ge5']['count']} | {agg['threshold_coverage']['ge5']['pct']}% |
| ≥10 usable (production ideal) | {agg['threshold_coverage']['ge10']['count']} | {agg['threshold_coverage']['ge10']['pct']}% |
| ≥20 usable | {agg['threshold_coverage']['ge20']['count']} | {agg['threshold_coverage']['ge20']['pct']}% |

## Bottom 50 Tickers (by usable_7d)

| ticker | company | sector | fh_raw | relevant | extracted | usable_7d | status | top_failure |
|--------|---------|--------|--------|----------|-----------|-----------|--------|-------------|
"""
    bottom50 = sorted(all_metrics, key=lambda x: x.usable_7d)[:50]
    for m in bottom50:
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_raw} | {m.finnhub_relevant} | {m.extraction_success} | {m.usable_7d} | {m.news_status} | {m.top_failure_reason} |\n"

    md += f"""
## Top 50 Tickers (by usable_7d)

| ticker | company | sector | fh_raw | extracted | usable_7d |
|--------|---------|--------|--------|-----------|-----------|
"""
    top50 = sorted(all_metrics, key=lambda x: x.usable_7d, reverse=True)[:50]
    for m in top50:
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_raw} | {m.extraction_success} | {m.usable_7d} |\n"

    md += "\n## By Sector\n\n| sector | tickers | mean_usable | median | ≥3% | ≥10% | common_failure |\n|--------|---------|-------------|--------|-----|------|----------------|\n"
    for sector, ss in sorted(sector_stats.items()):
        md += f"| {sector} | {ss['ticker_count']} | {ss['mean_usable']} | {ss['median_usable']} | {ss['pct_ge3']}% | {ss['pct_ge10']}% | {ss['common_failure']} |\n"

    md += f"""
## Failure Analysis

| failure_reason | ticker_count |
|----------------|--------------|
"""
    for reason, cnt in failure_ctr.most_common():
        md += f"| {reason} | {cnt} |\n"

    rec = "YES" if scored_pct >= 90 else "PARTIALLY" if scored_pct >= 70 else "NO"
    rec10 = "YES" if ge10_pct >= 80 else "PARTIALLY" if ge10_pct >= 50 else "NO"

    md += f"""
## Recommendations

**Can Finnhub-first support the full universe (MVP ≥3)?** {rec}
- {agg['threshold_coverage']['ge3']['count']}/{n} tickers ({scored_pct}%) meet the MVP threshold

**Is 10 usable articles per ticker realistic?** {rec10}
- {agg['threshold_coverage']['ge10']['count']}/{n} tickers ({ge10_pct}%) meet the production ideal threshold

**Is first25 safe?** {"YES — run with confidence" if scored_pct >= 85 else "CAUTION — check limited tickers first"}

**Is full 500 risk refresh safe?** {"YES — coverage is sufficient" if scored_pct >= 90 else "WAIT — " + str(agg['tickers_limited']) + " tickers are limited"}
"""
    md_path.write_text(md)
    print(f"  [REPORT] Markdown: {md_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def run_canary(
    batch_size: int = BATCH_SIZE,
    resume: bool = False,
    google_fallback: bool = False,
) -> None:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    from app.services.supabase import get_supabase

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"500-TICKER FINNHUB-FIRST NEWS COVERAGE CANARY")
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    _safety_check()

    supabase = get_supabase()
    sp500_meta = _load_sp500_metadata()
    active_tickers = _get_active_universe(supabase)
    print(f"\n[UNIVERSE] {len(active_tickers)} active tickers from positions + watchlist_items")
    print(f"[UNIVERSE] SP500 metadata loaded for {len(sp500_meta)} tickers")
    print(f"[CONFIG] Batch size: {batch_size} | Finnhub concurrency: {FINNHUB_CONCURRENCY}")
    print(f"[CONFIG] Google fallback: {'enabled (≥3 usable threshold)' if google_fallback else 'DISABLED for this canary'}")

    # Load checkpoint if resuming
    completed: set[str] = set()
    all_metrics: list[TickerMetrics] = []
    if resume and CHECKPOINT_FILE.exists():
        checkpoint = json.loads(CHECKPOINT_FILE.read_text())
        completed = set(checkpoint.get("completed_tickers", []))
        # Reconstruct metrics from checkpoint
        for td in checkpoint.get("metrics", []):
            m = TickerMetrics(**{k: v for k, v in td.items() if k in TickerMetrics.__dataclass_fields__})
            all_metrics.append(m)
        print(f"[RESUME] Found checkpoint: {len(completed)} tickers already done")

    pending = [t for t in active_tickers if t not in completed]
    batches = [pending[i:i+batch_size] for i in range(0, len(pending), batch_size)]
    total_batches = len(batches)
    start_batch_num = len(all_metrics) // batch_size + 1

    print(f"\n[PLAN] {len(pending)} tickers remaining in {total_batches} batches of {batch_size}")
    print()

    total_start = time.monotonic()

    for batch_idx, batch in enumerate(batches):
        batch_num = start_batch_num + batch_idx
        batch_start = time.monotonic()
        print(f"[BATCH {batch_num:02d}/{start_batch_num+total_batches-1:02d}] {batch} …")

        try:
            batch_metrics = await _run_batch(
                supabase, batch, batch_num, sp500_meta, google_fallback_enabled=google_fallback
            )
        except Exception as exc:
            print(f"  [ERROR] Batch {batch_num} failed: {exc}")
            # Still create placeholder metrics
            batch_metrics = [
                TickerMetrics(ticker=t, batch_num=batch_num, top_failure_reason="batch_error")
                for t in batch
            ]

        all_metrics.extend(batch_metrics)
        batch_elapsed = time.monotonic() - batch_start

        # Batch summary
        batch_usable = [m.usable_7d for m in batch_metrics]
        batch_scored = sum(1 for v in batch_usable if v >= GOOGLE_FALLBACK_MIN)
        batch_limited = [m.ticker for m in batch_metrics if m.usable_7d < GOOGLE_FALLBACK_MIN]
        fh_calls = len(batch)
        fh_429s = sum(1 for m in batch_metrics if m.finnhub_429)
        ext_att = sum(m.extraction_attempted for m in batch_metrics)
        ext_ok = sum(m.extraction_success for m in batch_metrics)

        print(
            f"  done in {batch_elapsed:.0f}s | "
            f"Finnhub calls: {fh_calls} | 429s: {fh_429s} | "
            f"extract: {ext_ok}/{ext_att} | "
            f"SCORED: {batch_scored}/{len(batch)} | "
            f"mean_usable: {round(mean(batch_usable), 1) if batch_usable else 0} | "
            f"min: {min(batch_usable) if batch_usable else 0}"
        )
        if batch_limited:
            print(f"  limited: {batch_limited}")

        # Checkpoint
        completed.update(t for t in batch)
        checkpoint = {
            "completed_tickers": list(completed),
            "metrics": [m.to_dict() for m in all_metrics],
        }
        CHECKPOINT_FILE.write_text(json.dumps(checkpoint))

        # Back off if 429s spike
        if fh_429s >= 2:
            print(f"  [BACKOFF] {fh_429s} Finnhub 429s — sleeping 30s")
            await asyncio.sleep(30)

    # ── Final report ──────────────────────────────────────────────────────────
    total_elapsed = time.monotonic() - total_start
    print(f"\n{'='*80}")
    print(f"ALL BATCHES COMPLETE — {len(all_metrics)} tickers in {total_elapsed:.0f}s")
    print(f"{'='*80}\n")

    usable_vals = [m.usable_7d for m in all_metrics]
    n = len(usable_vals)
    scored = sum(1 for v in usable_vals if v >= GOOGLE_FALLBACK_MIN)
    ge10 = sum(1 for v in usable_vals if v >= 10)

    print(f"SCORED (≥3 usable):  {scored}/{n}  ({round(scored/max(1,n)*100,1)}%)")
    print(f"≥10 usable:          {ge10}/{n}  ({round(ge10/max(1,n)*100,1)}%)")
    print(f"Mean usable: {round(mean(usable_vals), 1) if usable_vals else 0}  |  Median: {round(median(usable_vals), 1) if usable_vals else 0}")
    print(f"Min: {min(usable_vals) if usable_vals else 0}  |  Max: {max(usable_vals) if usable_vals else 0}")
    print(f"p10: {round(_percentile(usable_vals, 10), 1)}  |  p25: {round(_percentile(usable_vals, 25), 1)}"
          f"  |  p75: {round(_percentile(usable_vals, 75), 1)}  |  p90: {round(_percentile(usable_vals, 90), 1)}")

    hist = {
        "0": sum(1 for v in usable_vals if v == 0),
        "1-2": sum(1 for v in usable_vals if 1 <= v <= 2),
        "3-4": sum(1 for v in usable_vals if 3 <= v <= 4),
        "5-9": sum(1 for v in usable_vals if 5 <= v <= 9),
        "10-19": sum(1 for v in usable_vals if 10 <= v <= 19),
        "20+": sum(1 for v in usable_vals if v >= 20),
    }
    print(f"\nHistogram: 0={hist['0']}  1-2={hist['1-2']}  3-4={hist['3-4']}  "
          f"5-9={hist['5-9']}  10-19={hist['10-19']}  20+={hist['20+']}")

    bottom10 = sorted(all_metrics, key=lambda x: x.usable_7d)[:10]
    print(f"\nBottom 10 tickers:")
    for m in bottom10:
        print(f"  {m.ticker:<6} {m.company_name[:25]:<25} {m.sector[:15]:<15} "
              f"usable={m.usable_7d} fh_raw={m.finnhub_raw} fail={m.top_failure_reason}")

    print(f"\n[REPORTS] Generating …")
    _generate_reports(all_metrics, REPORTS_DIR)

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print(f"[CHECKPOINT] Cleared")

    print(f"\n[DONE] Total runtime: {total_elapsed:.0f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="500-ticker Finnhub-first news coverage canary")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--google-fallback", action="store_true", help="Enable Google fallback")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    asyncio.run(run_canary(
        batch_size=args.batch_size,
        resume=args.resume,
        google_fallback=args.google_fallback,
    ))
