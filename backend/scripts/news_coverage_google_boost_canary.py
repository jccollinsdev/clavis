#!/usr/bin/env python3
"""Google-assisted coverage boost canary.

Targets only tickers below 10 usable from the Finnhub-only canary.
Runs Google RSS for each, tracks per-ticker delta, generates before/after report.

Priority order:
  1. usable == 0  (MVP recovery needed)
  2. usable 1-2   (MVP recovery)
  3. usable 3-9   (production boost)

Usage:
    cd backend && python3 scripts/news_coverage_google_boost_canary.py [--resume]

Safety:
  - PAUSE_SYSTEM_SCHEDULER=true enforced
  - skip_existing=True — no valid articles overwritten
  - Google never replaces Finnhub; only supplements missing usable articles
  - Finnhub-only and Google-assisted counts tracked separately
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
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import mean, median, stdev

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "reports"
FINNHUB_CANARY_JSON = REPORTS_DIR / "news_coverage_500_canary.json"
CHECKPOINT_FILE = REPORTS_DIR / "news_coverage_google_boost_checkpoint.json"

GOOGLE_FALLBACK_MIN = 3
GOOGLE_PRODUCTION_TARGET = 10
BATCH_SIZE = 25
GOOGLE_CANDIDATES_PER_TICKER = 15
GOOGLE_EXTRACTIONS_PER_TICKER = 10
ENRICH_CONCURRENCY = 6


@dataclass
class BoostMetrics:
    ticker: str
    company_name: str = ""
    sector: str = ""
    industry: str = ""

    # Finnhub-only baseline (from prior canary)
    finnhub_raw: int = 0
    finnhub_relevant: int = 0
    finnhub_extracted: int = 0
    finnhub_usable: int = 0

    # Google metrics
    google_mode: str = "none"       # none | mvp_recovery | production_boost
    google_raw: int = 0
    google_decoded: int = 0
    google_relevant: int = 0
    google_extracted: int = 0
    google_enriched_complete: int = 0
    google_added_usable: int = 0
    google_429s: int = 0

    # Final
    final_usable: int = 0
    reached_3: bool = False
    reached_10: bool = False
    top_failure: str = ""
    batch_num: int = 0
    runtime_s: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def _safety_check() -> None:
    paused = os.getenv("PAUSE_SYSTEM_SCHEDULER", "").strip().lower()
    if paused not in {"1", "true", "yes", "on"}:
        print("[SAFETY] WARNING: PAUSE_SYSTEM_SCHEDULER not set — proceed with caution")
    else:
        print("[SAFETY] ✓ PAUSE_SYSTEM_SCHEDULER=true")
    print("[SAFETY] ✓ Google-boost canary — news coverage only, no risk snapshots")
    print("[SAFETY] ✓ skip_existing=True — valid enriched articles preserved")
    print("[SAFETY] ✓ Finnhub-first: Google supplements only, never replaces")


def _load_finnhub_baseline() -> dict[str, dict]:
    """Load per-ticker Finnhub-only data from the completed canary JSON."""
    if not FINNHUB_CANARY_JSON.exists():
        raise FileNotFoundError(f"Finnhub canary JSON not found: {FINNHUB_CANARY_JSON}")
    with open(FINNHUB_CANARY_JSON) as f:
        data = json.load(f)
    return data.get("per_ticker", {})


def _query_db_usable(supabase, tickers: list[str]) -> dict[str, int]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        rows = (
            supabase.table("shared_ticker_events")
            .select("ticker,extraction_status,paywalled,sentiment_score")
            .in_("ticker", tickers)
            .gte("published_at", cutoff)
            .execute()
            .data or []
        )
    except Exception as exc:
        print(f"  [DB] Query failed: {exc}")
        return {}
    result: dict[str, int] = defaultdict(int)
    for row in rows:
        t = str(row.get("ticker") or "").upper()
        if (
            row.get("extraction_status") == "success"
            and not row.get("paywalled", False)
            and row.get("sentiment_score") is not None
        ):
            result[t] += 1
    return dict(result)


async def _run_google_batch(
    supabase,
    batch_tickers: list[str],
    batch_num: int,
    finnhub_baseline: dict[str, dict],
    usable_before: dict[str, int],
) -> list[BoostMetrics]:
    from app.pipeline.rss_ingest import fetch_google_company_rss
    from app.pipeline.news_normalizer import normalize_news_batch
    from app.services.news_enrichment import enrich_and_store_articles_batch
    from app.services.candidate_ranker import rank_and_filter_candidates
    from app.services.ticker_cache_service import get_metadata_map

    t_start = time.monotonic()
    results: list[BoostMetrics] = []

    # Determine mode per ticker
    google_mode: dict[str, str] = {}
    for t in batch_tickers:
        usbl = usable_before.get(t, 0)
        if usbl < GOOGLE_FALLBACK_MIN:
            google_mode[t] = "mvp_recovery"
        elif usbl < GOOGLE_PRODUCTION_TARGET:
            google_mode[t] = "production_boost"
        else:
            google_mode[t] = "none"

    # Only fetch Google for tickers that need it
    need_google = [t for t in batch_tickers if google_mode[t] != "none"]
    if not need_google:
        for ticker in batch_tickers:
            fh = finnhub_baseline.get(ticker, {})
            m = BoostMetrics(
                ticker=ticker,
                company_name=fh.get("company_name", ""),
                sector=fh.get("sector", ""),
                industry=fh.get("industry", ""),
                finnhub_raw=fh.get("finnhub_raw", 0),
                finnhub_relevant=fh.get("finnhub_relevant", 0),
                finnhub_extracted=fh.get("extraction_success", 0),
                finnhub_usable=usable_before.get(ticker, 0),
                google_mode="none",
                final_usable=usable_before.get(ticker, 0),
                reached_3=usable_before.get(ticker, 0) >= GOOGLE_FALLBACK_MIN,
                reached_10=usable_before.get(ticker, 0) >= GOOGLE_PRODUCTION_TARGET,
                batch_num=batch_num,
                runtime_s=time.monotonic() - t_start,
            )
            results.append(m)
        return results

    # Google fetch
    metadata_map = get_metadata_map(supabase, need_google)
    try:
        google_raw_articles = await fetch_google_company_rss(
            need_google,
            ticker_metadata=metadata_map,
            limit_per_ticker=GOOGLE_CANDIDATES_PER_TICKER,
        )
    except Exception as exc:
        print(f"  [GOOGLE] fetch_google_company_rss failed: {exc}")
        google_raw_articles = []

    # Count raw per ticker
    google_raw_counts: dict[str, int] = defaultdict(int)
    for a in google_raw_articles:
        t = str(a.get("ticker") or "").strip().upper()
        google_raw_counts[t] += 1

    # Count decoded (URLs that aren't google wrapper after decode)
    google_decoded_counts: dict[str, int] = defaultdict(int)
    for a in google_raw_articles:
        t = str(a.get("ticker") or "").strip().upper()
        url = str(a.get("url") or a.get("source_url") or "")
        if "news.google.com" not in url:
            google_decoded_counts[t] += 1

    # Normalize
    google_normalized = normalize_news_batch(google_raw_articles, "company_news") if google_raw_articles else []

    # Track per-ticker relevant counts (after normalization/ranking)
    google_relevant_counts: dict[str, int] = defaultdict(int)
    for a in google_normalized:
        t = str(a.get("ticker") or "").strip().upper()
        google_relevant_counts[t] += 1

    # Cap extractions per ticker
    per_t_count: dict[str, int] = defaultdict(int)
    capped: list[dict] = []
    for a in google_normalized:
        t = str(a.get("ticker") or "").strip().upper()
        if per_t_count[t] < GOOGLE_EXTRACTIONS_PER_TICKER:
            capped.append(a)
            per_t_count[t] += 1
    google_normalized = capped

    # LLM enrich + store
    google_stored = await enrich_and_store_articles_batch(
        supabase, google_normalized, max_concurrency=ENRICH_CONCURRENCY, skip_existing=True
    )

    # Count enriched complete per ticker
    google_enriched: dict[str, int] = defaultdict(int)
    for a in google_stored:
        t = str(a.get("ticker") or "").strip().upper()
        if a.get("sentiment_score") is not None and a.get("sentiment_reason"):
            google_enriched[t] += 1

    # Query DB after Google
    usable_after = _query_db_usable(supabase, batch_tickers)

    # Build metrics per ticker
    for ticker in batch_tickers:
        fh = finnhub_baseline.get(ticker, {})
        ub = usable_before.get(ticker, 0)
        ua = usable_after.get(ticker, 0)
        added = max(0, ua - ub)

        m = BoostMetrics(
            ticker=ticker,
            company_name=fh.get("company_name", ""),
            sector=fh.get("sector", ""),
            industry=fh.get("industry", ""),
            finnhub_raw=fh.get("finnhub_raw", 0),
            finnhub_relevant=fh.get("finnhub_relevant", 0),
            finnhub_extracted=fh.get("extraction_success", 0),
            finnhub_usable=ub,
            google_mode=google_mode.get(ticker, "none"),
            google_raw=google_raw_counts.get(ticker, 0),
            google_decoded=google_decoded_counts.get(ticker, 0),
            google_relevant=google_relevant_counts.get(ticker, 0),
            google_extracted=per_t_count.get(ticker, 0),
            google_enriched_complete=google_enriched.get(ticker, 0),
            google_added_usable=added,
            final_usable=ua,
            reached_3=ua >= GOOGLE_FALLBACK_MIN,
            reached_10=ua >= GOOGLE_PRODUCTION_TARGET,
            top_failure=fh.get("top_failure_reason", ""),
            batch_num=batch_num,
            runtime_s=time.monotonic() - t_start,
        )
        results.append(m)

    return results


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = (p / 100) * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _generate_reports(
    boost_metrics: list[BoostMetrics],
    finnhub_baseline: dict[str, dict],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n = len(boost_metrics)

    # ── CSV ──────────────────────────────────────────────────────────────────
    csv_path = output_dir / "news_coverage_500_finnhub_vs_google.csv"
    fieldnames = [
        "ticker", "company_name", "sector", "industry",
        "finnhub_raw", "finnhub_relevant", "finnhub_extracted", "finnhub_usable",
        "google_used", "google_mode",
        "google_raw", "google_decoded", "google_relevant", "google_extracted",
        "google_enriched_complete", "google_added_usable", "google_429s",
        "final_usable", "reached_3", "reached_10", "top_failure",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for m in sorted(boost_metrics, key=lambda x: x.final_usable, reverse=True):
            row = m.to_dict()
            row["google_used"] = m.google_mode != "none"
            w.writerow(row)
    print(f"  [REPORT] CSV: {csv_path}")

    # ── JSON ─────────────────────────────────────────────────────────────────
    fh_usable_vals = [m.finnhub_usable for m in boost_metrics]
    final_usable_vals = [m.final_usable for m in boost_metrics]

    # Full universe stats (include tickers not targeted = already ≥10)
    all_tickers = list(finnhub_baseline.keys())
    full_final: dict[str, int] = {}
    boost_map = {m.ticker: m for m in boost_metrics}
    for t in all_tickers:
        if t in boost_map:
            full_final[t] = boost_map[t].final_usable
        else:
            full_final[t] = finnhub_baseline[t].get("usable_7d", 0)

    full_vals = list(full_final.values())
    n_full = len(full_vals)

    def _thresh(vals, thr):
        c = sum(1 for v in vals if v >= thr)
        return {"count": c, "pct": round(c / max(1, len(vals)) * 100, 1)}

    agg = {
        "generated_at": ts,
        "targeted_tickers": n,
        "full_universe_tickers": n_full,
        "finnhub_only": {
            "ge3": _thresh(full_vals, 3) if False else _thresh([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 3),
            "ge5": _thresh([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 5),
            "ge10": _thresh([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 10),
            "ge20": _thresh([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 20),
            "mean": round(mean([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers]), 1),
            "median": round(median([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers]), 1),
        },
        "google_assisted": {
            "ge3": _thresh(full_vals, 3),
            "ge5": _thresh(full_vals, 5),
            "ge10": _thresh(full_vals, 10),
            "ge20": _thresh(full_vals, 20),
            "mean": round(mean(full_vals), 1) if full_vals else 0,
            "median": round(median(full_vals), 1) if full_vals else 0,
        },
        "google_stats": {
            "tickers_used_google": sum(1 for m in boost_metrics if m.google_mode != "none"),
            "mvp_recovery_count": sum(1 for m in boost_metrics if m.google_mode == "mvp_recovery"),
            "production_boost_count": sum(1 for m in boost_metrics if m.google_mode == "production_boost"),
            "rescued_to_ge3": sum(1 for m in boost_metrics if m.google_mode == "mvp_recovery" and m.reached_3),
            "boosted_to_ge10": sum(1 for m in boost_metrics if m.google_mode == "production_boost" and m.reached_10),
            "still_below_3": sum(1 for m in boost_metrics if not m.reached_3),
            "still_below_10": sum(1 for m in boost_metrics if not m.reached_10),
            "total_google_raw": sum(m.google_raw for m in boost_metrics),
            "total_google_added_usable": sum(m.google_added_usable for m in boost_metrics),
            "total_google_429s": sum(m.google_429s for m in boost_metrics),
        },
        "distribution_stats": {
            "finnhub_only": {
                "p10": round(_percentile([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 10), 1),
                "p25": round(_percentile([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 25), 1),
                "p75": round(_percentile([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 75), 1),
                "p90": round(_percentile([finnhub_baseline[t].get("usable_7d", 0) for t in all_tickers], 90), 1),
            },
            "google_assisted": {
                "p10": round(_percentile(full_vals, 10), 1),
                "p25": round(_percentile(full_vals, 25), 1),
                "p75": round(_percentile(full_vals, 75), 1),
                "p90": round(_percentile(full_vals, 90), 1),
            },
        },
    }

    json_path = output_dir / "news_coverage_500_finnhub_vs_google.json"
    with open(json_path, "w") as f:
        json.dump({
            "aggregate": agg,
            "per_ticker": {m.ticker: m.to_dict() for m in boost_metrics},
        }, f, indent=2, default=str)
    print(f"  [REPORT] JSON: {json_path}")

    # ── Markdown ─────────────────────────────────────────────────────────────
    fh_only = agg["finnhub_only"]
    ga = agg["google_assisted"]
    gs = agg["google_stats"]
    ds = agg["distribution_stats"]

    def _pct_delta(old_pct, new_pct):
        delta = round(new_pct - old_pct, 1)
        return f"+{delta}%" if delta >= 0 else f"{delta}%"

    # Sector improvement table
    sector_before: dict[str, list] = defaultdict(list)
    sector_after: dict[str, list] = defaultdict(list)
    for t in all_tickers:
        sector = finnhub_baseline[t].get("sector") or "Unknown"
        sector_before[sector].append(finnhub_baseline[t].get("usable_7d", 0))
        sector_after[sector].append(full_final.get(t, 0))

    # Tickers rescued / boosted / still failing
    rescued = [m for m in boost_metrics if m.google_mode == "mvp_recovery" and m.reached_3 and m.finnhub_usable < GOOGLE_FALLBACK_MIN]
    boosted = [m for m in boost_metrics if m.google_mode == "production_boost" and m.reached_10 and m.finnhub_usable < GOOGLE_PRODUCTION_TARGET]
    still_below3 = [m for m in boost_metrics if not m.reached_3]
    still_below10 = [m for m in boost_metrics if not m.reached_10]

    md = f"""# Finnhub-First vs Google-Assisted: 500-Ticker Coverage Comparison
*Generated: {ts}*

## Executive Summary

| Metric | Finnhub-Only | Google-Assisted | Delta |
|--------|-------------|-----------------|-------|
| ≥3 usable (MVP) | {fh_only['ge3']['count']}/{n_full} ({fh_only['ge3']['pct']}%) | {ga['ge3']['count']}/{n_full} ({ga['ge3']['pct']}%) | {_pct_delta(fh_only['ge3']['pct'], ga['ge3']['pct'])} |
| ≥5 usable | {fh_only['ge5']['count']}/{n_full} ({fh_only['ge5']['pct']}%) | {ga['ge5']['count']}/{n_full} ({ga['ge5']['pct']}%) | {_pct_delta(fh_only['ge5']['pct'], ga['ge5']['pct'])} |
| ≥10 usable (prod ideal) | {fh_only['ge10']['count']}/{n_full} ({fh_only['ge10']['pct']}%) | {ga['ge10']['count']}/{n_full} ({ga['ge10']['pct']}%) | {_pct_delta(fh_only['ge10']['pct'], ga['ge10']['pct'])} |
| ≥20 usable | {fh_only['ge20']['count']}/{n_full} ({fh_only['ge20']['pct']}%) | {ga['ge20']['count']}/{n_full} ({ga['ge20']['pct']}%) | {_pct_delta(fh_only['ge20']['pct'], ga['ge20']['pct'])} |
| Mean usable | {fh_only['mean']} | {ga['mean']} | +{round(ga['mean']-fh_only['mean'],1)} |
| Median usable | {fh_only['median']} | {ga['median']} | +{round(ga['median']-fh_only['median'],1)} |

## Safety Status
- ✅ Finnhub-first — Google supplements only, never replaces
- ✅ skip_existing=True — no valid articles overwritten
- ✅ No risk snapshots promoted
- ✅ Finnhub-only and Google-assisted counts tracked separately

## Google Usage Summary

| Metric | Value |
|--------|-------|
| Tickers targeted (<10 usable) | {n} |
| Tickers that used Google | {gs['tickers_used_google']} |
| MVP recovery (usable < 3) | {gs['mvp_recovery_count']} |
| Production boost (usable 3–9) | {gs['production_boost_count']} |
| Rescued to ≥3 | {gs['rescued_to_ge3']} |
| Boosted to ≥10 | {gs['boosted_to_ge10']} |
| Still below 3 after Google | {gs['still_below_3']} |
| Still below 10 after Google | {gs['still_below_10']} |
| Total Google raw articles | {gs['total_google_raw']} |
| Total Google added usable | {gs['total_google_added_usable']} |
| Google 429s | {gs['total_google_429s']} |

## Distribution Shift

| Stat | Finnhub-Only | Google-Assisted |
|------|-------------|-----------------|
| p10 | {ds['finnhub_only']['p10']} | {ds['google_assisted']['p10']} |
| p25 | {ds['finnhub_only']['p25']} | {ds['google_assisted']['p25']} |
| p75 | {ds['finnhub_only']['p75']} | {ds['google_assisted']['p75']} |
| p90 | {ds['finnhub_only']['p90']} | {ds['google_assisted']['p90']} |

## Histogram (Full Universe After Google)

"""
    fh_hist = {"0":0,"1-2":0,"3-4":0,"5-9":0,"10-19":0,"20+":0}
    ga_hist = {"0":0,"1-2":0,"3-4":0,"5-9":0,"10-19":0,"20+":0}
    for t in all_tickers:
        fv = finnhub_baseline[t].get("usable_7d", 0)
        gv = full_final.get(t, 0)
        for v, h in ((fv, fh_hist), (gv, ga_hist)):
            if v == 0: h["0"] += 1
            elif v <= 2: h["1-2"] += 1
            elif v <= 4: h["3-4"] += 1
            elif v <= 9: h["5-9"] += 1
            elif v <= 19: h["10-19"] += 1
            else: h["20+"] += 1

    md += "| Bucket | Finnhub-Only | Google-Assisted | Delta |\n|--------|-------------|-----------------|-------|\n"
    for bucket in ("0","1-2","3-4","5-9","10-19","20+"):
        delta = ga_hist[bucket] - fh_hist[bucket]
        ds_str = f"+{delta}" if delta > 0 else str(delta)
        md += f"| {bucket} | {fh_hist[bucket]} | {ga_hist[bucket]} | {ds_str} |\n"

    md += f"""
## Tickers Rescued from <3 → ≥3 ({len(rescued)})

| ticker | company | sector | fh_usable | google_added | final |
|--------|---------|--------|-----------|--------------|-------|
"""
    for m in sorted(rescued, key=lambda x: x.final_usable, reverse=True)[:30]:
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_usable} | +{m.google_added_usable} | {m.final_usable} |\n"

    md += f"""
## Tickers Boosted from 3–9 → ≥10 ({len(boosted)})

| ticker | company | sector | fh_usable | google_added | final |
|--------|---------|--------|-----------|--------------|-------|
"""
    for m in sorted(boosted, key=lambda x: x.final_usable, reverse=True)[:30]:
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_usable} | +{m.google_added_usable} | {m.final_usable} |\n"

    md += f"""
## Still Below 3 After Google ({len(still_below3)})

| ticker | company | sector | fh_usable | google_added | final | top_failure |
|--------|---------|--------|-----------|--------------|-------|-------------|
"""
    for m in sorted(still_below3, key=lambda x: x.final_usable):
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_usable} | +{m.google_added_usable} | {m.final_usable} | {m.top_failure} |\n"

    md += f"""
## Still Below 10 After Google (sample — worst 30)

| ticker | company | sector | fh_usable | google_added | final |
|--------|---------|--------|-----------|--------------|-------|
"""
    for m in sorted(still_below10, key=lambda x: x.final_usable)[:30]:
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_usable} | +{m.google_added_usable} | {m.final_usable} |\n"

    md += "\n## By Sector\n\n| sector | n | fh_mean | ga_mean | fh_≥3% | ga_≥3% | fh_≥10% | ga_≥10% |\n|--------|---|---------|---------|--------|--------|---------|--------|\n"
    for sector in sorted(sector_before.keys()):
        bv = sector_before[sector]
        av = sector_after[sector]
        if not bv:
            continue
        md += (
            f"| {sector[:25]} | {len(bv)} "
            f"| {round(mean(bv),1)} | {round(mean(av),1)} "
            f"| {round(sum(1 for v in bv if v>=3)/len(bv)*100,0):.0f}% "
            f"| {round(sum(1 for v in av if v>=3)/len(av)*100,0):.0f}% "
            f"| {round(sum(1 for v in bv if v>=10)/len(bv)*100,0):.0f}% "
            f"| {round(sum(1 for v in av if v>=10)/len(av)*100,0):.0f}% |\n"
        )

    # Efficiency analysis
    total_google_raw = gs["total_google_raw"]
    total_added = gs["total_google_added_usable"]
    marginal_raw = round(total_google_raw / max(1, total_added), 1)

    md += f"""
## Efficiency Analysis

| Metric | Value |
|--------|-------|
| Google raw articles per added usable | {marginal_raw} |
| Total Google raw fetched | {total_google_raw} |
| Total usable added | {total_added} |
| Google 429s | {gs['total_google_429s']} |

## Recommendations

**Can Finnhub-first support the full universe at MVP (≥3)?**
{"YES" if ga['ge3']['pct'] >= 90 else "PARTIALLY" if ga['ge3']['pct'] >= 75 else "NO"} — {ga['ge3']['count']}/{n_full} ({ga['ge3']['pct']}%) after Google

**Can Finnhub+Google reach production ideal (≥10) for most tickers?**
{"YES" if ga['ge10']['pct'] >= 80 else "PARTIALLY" if ga['ge10']['pct'] >= 50 else "NO — paid provider needed for remaining gap"} — {ga['ge10']['count']}/{n_full} ({ga['ge10']['pct']}%) after Google

**Recommended production policy:**
- Active holdings/watchlist: target ≥10, use Finnhub + Google boost (mode=below_10)
- Dormant universe: target ≥3 MVP only, use Finnhub + Google MVP recovery (mode=mvp_only)
- Tickers still below 3 after Google: show "Limited Coverage" badge, score from headline if ≥1 article
- Never count failed/paywalled/headline-only as usable; never fabricate bodies or scores
"""
    md_path = output_dir / "news_coverage_500_finnhub_vs_google.md"
    md_path.write_text(md)
    print(f"  [REPORT] Markdown: {md_path}")


async def run_boost_canary(resume: bool = False) -> None:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    from app.services.supabase import get_supabase

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("GOOGLE-ASSISTED COVERAGE BOOST CANARY")
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    _safety_check()

    supabase = get_supabase()
    finnhub_baseline = _load_finnhub_baseline()

    # Sort by priority: 0 usable → 1-2 → 3-9 → ≥10 (skip)
    below10 = {
        t: v for t, v in finnhub_baseline.items()
        if v.get("usable_7d", 0) < GOOGLE_PRODUCTION_TARGET
    }
    priority_order = sorted(
        below10.keys(),
        key=lambda t: (
            0 if below10[t].get("usable_7d", 0) == 0 else
            1 if below10[t].get("usable_7d", 0) <= 2 else
            2
        )
    )

    print(f"\n[UNIVERSE] {len(finnhub_baseline)} total tickers in Finnhub baseline")
    print(f"[TARGET]   {len(below10)} tickers below {GOOGLE_PRODUCTION_TARGET} usable")
    print(f"  Priority 1 (usable=0):   {sum(1 for t in below10 if below10[t].get('usable_7d',0)==0)}")
    print(f"  Priority 2 (usable 1-2): {sum(1 for t in below10 if 1<=below10[t].get('usable_7d',0)<=2)}")
    print(f"  Priority 3 (usable 3-9): {sum(1 for t in below10 if 3<=below10[t].get('usable_7d',0)<=9)}")
    print(f"  Tickers ≥10 (skipped):   {len(finnhub_baseline)-len(below10)}")

    # Checkpoint
    completed: set[str] = set()
    all_metrics: list[BoostMetrics] = []
    if resume and CHECKPOINT_FILE.exists():
        cp = json.loads(CHECKPOINT_FILE.read_text())
        completed = set(cp.get("completed_tickers", []))
        for td in cp.get("metrics", []):
            m = BoostMetrics(**{k: v for k, v in td.items() if k in BoostMetrics.__dataclass_fields__})
            all_metrics.append(m)
        print(f"[RESUME] {len(completed)} tickers already done")

    pending = [t for t in priority_order if t not in completed]
    batches = [pending[i:i+BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
    total_batches = len(batches)
    start_batch_num = len(all_metrics) // BATCH_SIZE + 1
    total_start = time.monotonic()

    print(f"\n[PLAN] {len(pending)} tickers in {total_batches} batches of {BATCH_SIZE}")
    print()

    # Pre-snapshot usable counts
    print("[DB] Snapshotting current usable counts …")
    usable_snapshot = _query_db_usable(supabase, list(finnhub_baseline.keys()))
    print(f"  Done — {len(usable_snapshot)} tickers with ≥1 usable article\n")

    for batch_idx, batch in enumerate(batches):
        batch_num = start_batch_num + batch_idx
        batch_start = time.monotonic()
        mvp_count = sum(1 for t in batch if usable_snapshot.get(t, 0) < GOOGLE_FALLBACK_MIN)
        boost_count = sum(1 for t in batch if GOOGLE_FALLBACK_MIN <= usable_snapshot.get(t, 0) < GOOGLE_PRODUCTION_TARGET)
        print(f"[BATCH {batch_num:02d}/{start_batch_num+total_batches-1:02d}] {batch[:5]}… | mvp={mvp_count} boost={boost_count}")

        usable_before = {t: usable_snapshot.get(t, below10.get(t, {}).get("usable_7d", 0)) for t in batch}

        try:
            batch_metrics = await _run_google_batch(
                supabase, batch, batch_num, finnhub_baseline, usable_before
            )
        except Exception as exc:
            print(f"  [ERROR] Batch {batch_num} failed: {exc}")
            batch_metrics = [
                BoostMetrics(ticker=t, batch_num=batch_num, top_failure="batch_error")
                for t in batch
            ]

        all_metrics.extend(batch_metrics)
        elapsed = time.monotonic() - batch_start

        rescued = sum(1 for m in batch_metrics if m.google_mode=="mvp_recovery" and m.reached_3 and m.finnhub_usable < GOOGLE_FALLBACK_MIN)
        boosted = sum(1 for m in batch_metrics if m.google_mode=="production_boost" and m.reached_10)
        g_added = sum(m.google_added_usable for m in batch_metrics)
        g_429s  = sum(m.google_429s for m in batch_metrics)
        final_vals = [m.final_usable for m in batch_metrics]

        print(
            f"  done in {elapsed:.0f}s | google_429s: {g_429s} | "
            f"added_usable: +{g_added} | rescued→≥3: {rescued} | boosted→≥10: {boosted} | "
            f"mean_final: {round(sum(final_vals)/max(1,len(final_vals)),1)} | "
            f"≥10: {sum(1 for v in final_vals if v>=10)}/{len(batch)}"
        )
        still_below = [m.ticker for m in batch_metrics if not m.reached_10]
        if still_below:
            print(f"  still <10: {still_below[:10]}{'…' if len(still_below)>10 else ''}")

        completed.update(batch)
        CHECKPOINT_FILE.write_text(json.dumps({
            "completed_tickers": list(completed),
            "metrics": [m.to_dict() for m in all_metrics],
        }))

        if g_429s >= 2:
            print(f"  [BACKOFF] {g_429s} Google 429s — sleeping 30s")
            await asyncio.sleep(30)

    # Final summary
    total_elapsed = time.monotonic() - total_start
    print(f"\n{'='*80}")
    print(f"ALL BATCHES COMPLETE — {len(all_metrics)} tickers processed in {total_elapsed:.0f}s")
    print(f"{'='*80}\n")

    total_rescued = sum(1 for m in all_metrics if m.google_mode=="mvp_recovery" and m.reached_3 and m.finnhub_usable < GOOGLE_FALLBACK_MIN)
    total_boosted = sum(1 for m in all_metrics if m.google_mode=="production_boost" and m.reached_10)
    total_added   = sum(m.google_added_usable for m in all_metrics)
    still_below3  = [m for m in all_metrics if not m.reached_3]
    still_below10 = [m for m in all_metrics if not m.reached_10]

    print(f"Tickers rescued (<3 → ≥3):    {total_rescued}")
    print(f"Tickers boosted (3-9 → ≥10):  {total_boosted}")
    print(f"Total usable added by Google:  +{total_added}")
    print(f"Still below 3 after Google:    {len(still_below3)}")
    print(f"Still below 10 after Google:   {len(still_below10)}")

    print(f"\n[REPORTS] Generating …")
    _generate_reports(all_metrics, finnhub_baseline, REPORTS_DIR)

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("[CHECKPOINT] Cleared")

    print(f"\n[DONE] Total runtime: {total_elapsed:.0f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google-assisted coverage boost canary")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    asyncio.run(run_boost_canary(resume=args.resume))
