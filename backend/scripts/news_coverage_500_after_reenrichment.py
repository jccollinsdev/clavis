#!/usr/bin/env python3
"""Phase 5: Post-re-enrichment coverage report.

Reads the pre-repair baseline from reports/news_coverage_500_finnhub_vs_google_corrected.csv,
queries the live DB for current usable-article counts, and produces a before/after delta report.

Usage:
    cd backend
    python3 scripts/news_coverage_500_after_reenrichment.py

Outputs (in reports/):
    news_coverage_500_after_reenrichment.csv
    news_coverage_500_after_reenrichment.json
    news_coverage_500_after_reenrichment.md
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

SCRIPT_DIR  = Path(__file__).parent
REPO_ROOT   = SCRIPT_DIR.parent
REPORTS_DIR = REPO_ROOT / "reports"
BASELINE_CSV = REPORTS_DIR / "news_coverage_500_finnhub_vs_google_corrected.csv"
WINDOW_DAYS  = 7


def main() -> None:
    from app.services.supabase import get_supabase

    supabase = get_supabase()
    now_utc  = datetime.now(timezone.utc)
    cutoff   = (now_utc - timedelta(days=WINDOW_DAYS)).isoformat()

    # ── Load baseline ─────────────────────────────────────────────────────────
    print(f"Loading baseline from {BASELINE_CSV}…")
    baseline: dict[str, dict] = {}
    with open(BASELINE_CSV, newline="") as f:
        for row in csv.DictReader(f):
            baseline[row["ticker"]] = row

    tickers = sorted(baseline.keys())
    print(f"  {len(tickers)} tickers loaded from baseline")

    # ── Query live DB for current usable counts ───────────────────────────────
    print(f"Querying live DB (window={WINDOW_DAYS}d)…")
    PAGE_SIZE = 1000
    all_rows: list[dict] = []
    offset    = 0
    while True:
        rows = (
            supabase.table("shared_ticker_events")
            .select("ticker,extraction_status,paywalled,sentiment_score")
            .in_("ticker", tickers)
            .gte("published_at", cutoff)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data or []
        )
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  {len(all_rows)} rows fetched")

    # Group by ticker
    usable_now: dict[str, int] = {}
    total_now: dict[str, int]  = {}
    for row in all_rows:
        t = (row.get("ticker") or "").upper()
        if not t:
            continue
        total_now[t] = total_now.get(t, 0) + 1
        if (
            row.get("extraction_status") == "success"
            and not row.get("paywalled", False)
            and row.get("sentiment_score") is not None
        ):
            usable_now[t] = usable_now.get(t, 0) + 1

    # ── Build comparison rows ─────────────────────────────────────────────────
    results = []
    for ticker in tickers:
        b          = baseline[ticker]
        before     = int(b.get("final_usable") or b.get("finnhub_usable") or 0)
        after      = usable_now.get(ticker, before)
        delta      = after - before
        company    = b.get("company_name", "")
        sector     = b.get("sector", "")
        results.append({
            "ticker":          ticker,
            "company_name":    company,
            "sector":          sector,
            "usable_before":   before,
            "usable_after":    after,
            "delta":           delta,
            "reached_3_after": after >= 3,
            "reached_10_after": after >= 10,
            "newly_rescued":   before < 3 and after >= 3,
            "newly_boosted":   before < 10 and after >= 10,
        })

    # Sort: newly rescued first, then largest delta
    results.sort(key=lambda r: (-int(r["newly_rescued"]), -r["delta"], r["ticker"]))

    # ── Aggregate stats ───────────────────────────────────────────────────────
    n = len(results)
    before_ge3  = sum(1 for r in results if r["usable_before"] >= 3)
    after_ge3   = sum(1 for r in results if r["usable_after"]  >= 3)
    before_ge5  = sum(1 for r in results if r["usable_before"] >= 5)
    after_ge5   = sum(1 for r in results if r["usable_after"]  >= 5)
    before_ge10 = sum(1 for r in results if r["usable_before"] >= 10)
    after_ge10  = sum(1 for r in results if r["usable_after"]  >= 10)
    newly_rescued = sum(1 for r in results if r["newly_rescued"])
    newly_boosted = sum(1 for r in results if r["newly_boosted"])
    total_delta   = sum(r["delta"] for r in results)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    csv_path = REPORTS_DIR / "news_coverage_500_after_reenrichment.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"  CSV written → {csv_path}")

    # ── Write JSON ────────────────────────────────────────────────────────────
    summary = {
        "generated_at":  now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "window_days":   WINDOW_DAYS,
        "tickers_total": n,
        "before": {
            "ge3":  before_ge3,  "ge3_pct":  round(100 * before_ge3  / n, 1),
            "ge5":  before_ge5,  "ge5_pct":  round(100 * before_ge5  / n, 1),
            "ge10": before_ge10, "ge10_pct": round(100 * before_ge10 / n, 1),
        },
        "after": {
            "ge3":  after_ge3,  "ge3_pct":  round(100 * after_ge3  / n, 1),
            "ge5":  after_ge5,  "ge5_pct":  round(100 * after_ge5  / n, 1),
            "ge10": after_ge10, "ge10_pct": round(100 * after_ge10 / n, 1),
        },
        "newly_rescued_to_3":  newly_rescued,
        "newly_boosted_to_10": newly_boosted,
        "total_articles_enriched": total_delta,
        "tickers": results,
    }
    json_path = REPORTS_DIR / "news_coverage_500_after_reenrichment.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  JSON written → {json_path}")

    # ── Write Markdown ────────────────────────────────────────────────────────
    md_lines = [
        "# Post-Re-Enrichment Coverage Report",
        f"*Generated: {now_utc.strftime('%Y-%m-%d %H:%M UTC')}*",
        f"*Trailing window: {WINDOW_DAYS} days  |  Baseline: news_coverage_500_finnhub_vs_google_corrected.csv*",
        "",
        "## A. Executive Summary",
        "",
        "| Metric | Before Re-Enrich | After Re-Enrich | Delta |",
        "|--------|-----------------|-----------------|-------|",
        f"| ≥3 usable (MVP) | {before_ge3}/{n} ({100*before_ge3/n:.1f}%) | {after_ge3}/{n} ({100*after_ge3/n:.1f}%) | {after_ge3 - before_ge3:+d} |",
        f"| ≥5 usable | {before_ge5}/{n} ({100*before_ge5/n:.1f}%) | {after_ge5}/{n} ({100*after_ge5/n:.1f}%) | {after_ge5 - before_ge5:+d} |",
        f"| ≥10 usable (prod ideal) | {before_ge10}/{n} ({100*before_ge10/n:.1f}%) | {after_ge10}/{n} ({100*after_ge10/n:.1f}%) | {after_ge10 - before_ge10:+d} |",
        f"| Tickers rescued <3 → ≥3 | — | {newly_rescued} | — |",
        f"| Tickers boosted <10 → ≥10 | — | {newly_boosted} | — |",
        f"| Total articles newly enriched | — | +{total_delta} | — |",
        "",
        "## B. Tickers Rescued (<3 → ≥3)",
        "",
    ]

    rescued_rows = [r for r in results if r["newly_rescued"]]
    if rescued_rows:
        md_lines += [
            "| Ticker | Company | Before | After | Delta |",
            "|--------|---------|--------|-------|-------|",
        ]
        for r in rescued_rows[:30]:
            md_lines.append(f"| {r['ticker']} | {r['company_name']} | {r['usable_before']} | {r['usable_after']} | +{r['delta']} |")
        if len(rescued_rows) > 30:
            md_lines.append(f"*…and {len(rescued_rows)-30} more — see CSV for full list*")
    else:
        md_lines.append("*No tickers moved from <3 to ≥3 in this window.*")

    md_lines += [
        "",
        "## C. Largest Gains (top 20)",
        "",
        "| Ticker | Company | Before | After | Delta |",
        "|--------|---------|--------|-------|-------|",
    ]
    top_gains = sorted([r for r in results if r["delta"] > 0], key=lambda r: -r["delta"])[:20]
    for r in top_gains:
        md_lines.append(f"| {r['ticker']} | {r['company_name']} | {r['usable_before']} | {r['usable_after']} | +{r['delta']} |")

    if not top_gains:
        md_lines.append("*No gains recorded yet — repair job still running.*")

    md_lines += [
        "",
        "## D. Still Below 3 After Re-Enrichment",
        "",
        "| Ticker | Company | Sector | After |",
        "|--------|---------|--------|-------|",
    ]
    still_zero = [r for r in results if r["usable_after"] < 3]
    still_zero.sort(key=lambda r: r["usable_after"])
    for r in still_zero[:30]:
        md_lines.append(f"| {r['ticker']} | {r['company_name']} | {r['sector']} | {r['usable_after']} |")
    if len(still_zero) > 30:
        md_lines.append(f"*…and {len(still_zero)-30} more — see CSV*")
    if not still_zero:
        md_lines.append("*All tickers have ≥3 usable articles.*")

    md_path = REPORTS_DIR / "news_coverage_500_after_reenrichment.md"
    md_path.write_text("\n".join(md_lines) + "\n")
    print(f"  MD written  → {md_path}")

    # ── Console summary ───────────────────────────────────────────────────────
    print()
    print("=== Post-Re-Enrichment Coverage ===")
    print(f"  Tickers checked : {n}")
    print(f"  ≥3 usable  : {before_ge3} → {after_ge3} ({after_ge3-before_ge3:+d})")
    print(f"  ≥5 usable  : {before_ge5} → {after_ge5} ({after_ge5-before_ge5:+d})")
    print(f"  ≥10 usable : {before_ge10} → {after_ge10} ({after_ge10-before_ge10:+d})")
    print(f"  Newly rescued (<3→≥3)  : {newly_rescued}")
    print(f"  Newly boosted (<10→≥10): {newly_boosted}")
    print(f"  Total new enriched     : +{total_delta} articles")


if __name__ == "__main__":
    main()
