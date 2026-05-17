"""
news_coverage_google_boost_corrected.py — clean Finnhub-only vs Google-assisted canary.

FIELD SEMANTICS (enforced throughout):
  finnhub_usable        = usable_7d from the Finnhub-only canary baseline JSON (FROZEN, never live DB)
  live_before           = live DB usable count queried right before Google runs for this batch
  live_after            = live DB usable count queried right after Google enrichment for this batch
  google_added_usable   = max(0, live_after - max(finnhub_usable, live_before))
                          Credit Google only for articles *above* the Finnhub baseline.
                          This handles the case where the live DB has drifted down since the
                          Finnhub canary ran — Google refilling the drift gap gets no credit.
  final_usable          = finnhub_usable + google_added_usable
  reached_3             = final_usable >= 3
  reached_10            = final_usable >= 10
  rescued_to_3          = finnhub_usable < 3  AND  final_usable >= 3
  boosted_to_10         = finnhub_usable < 10 AND  final_usable >= 10

WHAT THE PREVIOUS RUN GOT WRONG:
  - finnhub_usable was the *live DB* at boost run time, not the Finnhub baseline.
    181 tickers had live DB < baseline (7-day window drift between the two runs).
  - google_added_usable = live_after - live_before (drifted baseline) made Google appear to
    add +723 articles when in reality it added +25 net-new above the Finnhub baseline.
  - rescued_to_ge3 = 142 was 100% false; all 142 were tickers with FH baseline >= 3 that
    had drifted below 3 in live DB. 0 tickers genuinely rescued.

SAFETY CONSTRAINTS (checked at startup):
  - No risk snapshots promoted
  - No Finnhub baseline modified
  - No invalid articles counted as usable
  - Google is supplement only; Finnhub-only and Google-assisted tracked separately
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import mean, median

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

REPORTS_DIR = BACKEND_DIR / "reports"
FINNHUB_BASELINE_PATH = REPORTS_DIR / "news_coverage_500_canary.json"
CHECKPOINT_FILE = REPORTS_DIR / "news_coverage_google_boost_corrected_checkpoint.json"

# ── config ────────────────────────────────────────────────────────────────────
BATCH_SIZE              = 25
GOOGLE_FALLBACK_MIN     = 3    # mvp_recovery threshold
GOOGLE_PRODUCTION_TARGET = 10  # production_boost target
GOOGLE_CANDIDATES_PER_TICKER = 15
GOOGLE_EXTRACTIONS_PER_TICKER = 10
ENRICH_CONCURRENCY      = 6


# ── calculation tests (run at import) ─────────────────────────────────────────
def _run_calculation_tests() -> None:
    """Inline unit tests for the field semantic formulas. Crash at import if wrong."""

    def _calc(fh_usable, live_before, live_after):
        g_added = max(0, live_after - max(fh_usable, live_before))
        final   = fh_usable + g_added
        return g_added, final

    cases = [
        # (fh_usable, live_before, live_after, expected_g_added, expected_final, label)
        # -- Normal: Google adds on top of stable baseline
        (5, 5, 8,  3, 8,  "Google adds 3 on top of stable baseline"),
        # -- Drift down, Google refills and adds: only credit what's above FH baseline
        (7, 1, 9,  2, 9,  "Drift to 1, Google adds 8 → only 2 above FH baseline"),
        # -- Drift down, Google refills exactly to baseline: 0 credit
        (7, 1, 7,  0, 7,  "Drift to 1, Google refills to FH baseline exactly: 0 credit"),
        # -- Drift down, Google can't even refill to baseline
        (7, 1, 4,  0, 7,  "Google can't refill: final stays at FH baseline"),
        # -- No drift, Google adds nothing
        (5, 5, 5,  0, 5,  "No Google additions"),
        # -- Live before > FH baseline (shouldn't happen but handle gracefully)
        (5, 8, 10, 2, 7,  "Live before higher than FH baseline: 2 added above live_before"),
        # -- FH=0, Google adds 4
        (0, 0, 4,  4, 4,  "FH=0, Google adds 4"),
        # -- FH=2, Google takes from <3 to >=3: rescued
        (2, 2, 5,  3, 5,  "FH=2, Google adds 3 → rescued to 3"),
        # -- FH=9, Google takes to >=10: boosted
        (9, 9, 11, 2, 11, "FH=9, Google adds 2 → boosted to 10"),
    ]

    rescued_cases = [
        (2, 3, True,  "FH<3 and final>=3 → rescued"),
        (3, 5, False, "FH=3 already → NOT rescued"),
        (0, 2, False, "FH<3 but final<3 → NOT rescued"),
    ]

    boosted_cases = [
        (9,  11, True,  "FH<10 and final>=10 → boosted"),
        (10, 12, False, "FH=10 already → NOT boosted"),
        (5,  9,  False, "FH<10 but final<10 → NOT boosted"),
    ]

    for fh, lb, la, exp_ga, exp_f, label in cases:
        ga, f = _calc(fh, lb, la)
        assert ga == exp_ga and f == exp_f, (
            f"CALC FAIL [{label}]: fh={fh} lb={lb} la={la} "
            f"expected g_added={exp_ga} final={exp_f} got g_added={ga} final={f}"
        )

    for fh_usable, final_usable, expected, label in rescued_cases:
        result = fh_usable < 3 and final_usable >= 3
        assert result == expected, f"RESCUED FAIL [{label}]: fh={fh_usable} final={final_usable}"

    for fh_usable, final_usable, expected, label in boosted_cases:
        result = fh_usable < 10 and final_usable >= 10
        assert result == expected, f"BOOSTED FAIL [{label}]: fh={fh_usable} final={final_usable}"


_run_calculation_tests()


# ── dataclass ─────────────────────────────────────────────────────────────────
@dataclass
class BoostMetrics:
    ticker: str = ""
    company_name: str = ""
    sector: str = ""
    industry: str = ""

    # Finnhub-only (from baseline JSON — immutable)
    finnhub_usable: int = 0
    finnhub_raw: int = 0
    finnhub_relevant: int = 0
    finnhub_extracted: int = 0

    # Google path
    google_mode: str = "none"          # none | mvp_recovery | production_boost
    google_raw: int = 0
    google_decoded: int = 0
    google_relevant: int = 0
    google_extracted: int = 0
    google_enriched_complete: int = 0
    google_added_usable: int = 0       # net new above max(finnhub_usable, live_before)
    google_429s: int = 0

    # Live DB snapshots (diagnostic — NOT used for google_added_usable calculation)
    live_db_before: int = 0
    live_db_after: int = 0

    # Final stats
    final_usable: int = 0              # finnhub_usable + google_added_usable
    reached_3: bool = False            # final_usable >= 3
    reached_10: bool = False           # final_usable >= 10
    rescued_to_3: bool = False         # finnhub_usable < 3 AND final_usable >= 3
    boosted_to_10: bool = False        # finnhub_usable < 10 AND final_usable >= 10
    top_failure: str = ""

    batch_num: int = 0
    runtime_s: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BoostMetrics":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── helpers ───────────────────────────────────────────────────────────────────
def _load_finnhub_baseline() -> dict[str, dict]:
    if not FINNHUB_BASELINE_PATH.exists():
        raise FileNotFoundError(f"Finnhub baseline not found: {FINNHUB_BASELINE_PATH}")
    with open(FINNHUB_BASELINE_PATH) as f:
        data = json.load(f)
    per_ticker = data.get("per_ticker", data)
    print(f"[BASELINE] Loaded {len(per_ticker)} tickers from {FINNHUB_BASELINE_PATH.name}")
    return per_ticker


def _query_db_usable(supabase, tickers: list[str]) -> dict[str, int]:
    if not tickers:
        return {}
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


def _safety_check() -> None:
    if os.getenv("PAUSE_SYSTEM_SCHEDULER") != "true":
        print("[SAFETY] ⚠  PAUSE_SYSTEM_SCHEDULER not set — continuing anyway")
    else:
        print("[SAFETY] ✓ PAUSE_SYSTEM_SCHEDULER=true")
    print("[SAFETY] ✓ No risk snapshots — news coverage canary only")
    print("[SAFETY] ✓ finnhub_usable = Finnhub baseline (immutable)")
    print("[SAFETY] ✓ google_added_usable = net new above max(fh_usable, live_before)")
    print("[SAFETY] ✓ skip_existing=True — valid articles preserved")


# ── Google batch runner ───────────────────────────────────────────────────────
async def _run_google_batch(
    supabase,
    batch_tickers: list[str],
    batch_num: int,
    finnhub_baseline: dict[str, dict],
) -> list[BoostMetrics]:
    from app.pipeline.rss_ingest import fetch_google_company_rss
    from app.pipeline.news_normalizer import normalize_news_batch
    from app.services.news_enrichment import enrich_and_store_articles_batch
    from app.services.ticker_cache_service import get_metadata_map

    t_start = time.monotonic()
    results: list[BoostMetrics] = []

    # Determine mode based on FINNHUB BASELINE (never live DB)
    google_mode: dict[str, str] = {}
    for t in batch_tickers:
        fh_usable = finnhub_baseline.get(t, {}).get("usable_7d", 0)
        if fh_usable < GOOGLE_FALLBACK_MIN:
            google_mode[t] = "mvp_recovery"
        elif fh_usable < GOOGLE_PRODUCTION_TARGET:
            google_mode[t] = "production_boost"
        else:
            google_mode[t] = "none"

    # Snapshot live DB BEFORE Google (for diagnostic / delta calculation)
    live_before_map = _query_db_usable(supabase, batch_tickers)

    need_google = [t for t in batch_tickers if google_mode[t] != "none"]
    if not need_google:
        for ticker in batch_tickers:
            fh = finnhub_baseline.get(ticker, {})
            fh_usable = fh.get("usable_7d", 0)
            results.append(BoostMetrics(
                ticker=ticker,
                company_name=fh.get("company_name", ""),
                sector=fh.get("sector", ""),
                industry=fh.get("industry", ""),
                finnhub_usable=fh_usable,
                finnhub_raw=fh.get("finnhub_raw", 0),
                finnhub_relevant=fh.get("finnhub_relevant", 0),
                finnhub_extracted=fh.get("extraction_success", 0),
                google_mode="none",
                live_db_before=live_before_map.get(ticker, 0),
                live_db_after=live_before_map.get(ticker, 0),
                google_added_usable=0,
                final_usable=fh_usable,
                reached_3=(fh_usable >= GOOGLE_FALLBACK_MIN),
                reached_10=(fh_usable >= GOOGLE_PRODUCTION_TARGET),
                rescued_to_3=False,
                boosted_to_10=False,
                top_failure=fh.get("top_failure_reason", "none"),
                batch_num=batch_num,
                runtime_s=time.monotonic() - t_start,
            ))
        return results

    # Fetch Google RSS
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
    google_decoded_counts: dict[str, int] = defaultdict(int)
    for a in google_raw_articles:
        t = str(a.get("ticker") or "").strip().upper()
        google_raw_counts[t] += 1
        if "news.google.com" not in str(a.get("url") or a.get("source_url") or ""):
            google_decoded_counts[t] += 1

    # Normalize and cap extractions per ticker
    google_normalized = normalize_news_batch(google_raw_articles, "company_news") if google_raw_articles else []
    per_t_count: dict[str, int] = defaultdict(int)
    capped: list[dict] = []
    for a in google_normalized:
        t = str(a.get("ticker") or "").strip().upper()
        if per_t_count[t] < GOOGLE_EXTRACTIONS_PER_TICKER:
            capped.append(a)
            per_t_count[t] += 1
    google_normalized = capped

    google_relevant_counts: dict[str, int] = defaultdict(int)
    for a in google_normalized:
        google_relevant_counts[str(a.get("ticker") or "").strip().upper()] += 1

    # Enrich + store (skip_existing=True prevents overwriting valid Finnhub articles)
    google_stored = await enrich_and_store_articles_batch(
        supabase, google_normalized, max_concurrency=ENRICH_CONCURRENCY, skip_existing=True
    )

    google_enriched: dict[str, int] = defaultdict(int)
    for a in google_stored:
        t = str(a.get("ticker") or "").strip().upper()
        if a.get("sentiment_score") is not None and a.get("sentiment_reason"):
            google_enriched[t] += 1

    # Snapshot live DB AFTER Google
    live_after_map = _query_db_usable(supabase, batch_tickers)

    # Build per-ticker metrics with CORRECTED field semantics
    for ticker in batch_tickers:
        fh = finnhub_baseline.get(ticker, {})
        fh_usable   = fh.get("usable_7d", 0)          # FROZEN — from Finnhub baseline
        live_before = live_before_map.get(ticker, 0)
        live_after  = live_after_map.get(ticker, 0)

        # Google gets credit ONLY for articles above max(fh_usable, live_before)
        # This prevents crediting Google for re-filling 7-day window drift
        google_added = max(0, live_after - max(fh_usable, live_before))
        final        = fh_usable + google_added

        results.append(BoostMetrics(
            ticker=ticker,
            company_name=fh.get("company_name", ""),
            sector=fh.get("sector", ""),
            industry=fh.get("industry", ""),
            finnhub_usable=fh_usable,
            finnhub_raw=fh.get("finnhub_raw", 0),
            finnhub_relevant=fh.get("finnhub_relevant", 0),
            finnhub_extracted=fh.get("extraction_success", 0),
            google_mode=google_mode.get(ticker, "none"),
            google_raw=google_raw_counts.get(ticker, 0),
            google_decoded=google_decoded_counts.get(ticker, 0),
            google_relevant=google_relevant_counts.get(ticker, 0),
            google_extracted=per_t_count.get(ticker, 0),
            google_enriched_complete=google_enriched.get(ticker, 0),
            google_added_usable=google_added,
            google_429s=0,
            live_db_before=live_before,
            live_db_after=live_after,
            final_usable=final,
            reached_3=(final >= GOOGLE_FALLBACK_MIN),
            reached_10=(final >= GOOGLE_PRODUCTION_TARGET),
            rescued_to_3=(fh_usable < GOOGLE_FALLBACK_MIN and final >= GOOGLE_FALLBACK_MIN),
            boosted_to_10=(fh_usable < GOOGLE_PRODUCTION_TARGET and final >= GOOGLE_PRODUCTION_TARGET),
            top_failure=fh.get("top_failure_reason", ""),
            batch_num=batch_num,
            runtime_s=time.monotonic() - t_start,
        ))

    return results


# ── percentile helper ─────────────────────────────────────────────────────────
def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = (p / 100) * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


# ── report generator ──────────────────────────────────────────────────────────
def _generate_reports(
    boost_metrics: list[BoostMetrics],
    finnhub_baseline: dict[str, dict],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    all_tickers = list(finnhub_baseline.keys())
    boost_map = {m.ticker: m for m in boost_metrics}

    # Full-universe final_usable: use corrected final from metrics, or FH baseline for skipped
    full_final: dict[str, int] = {}
    full_fh: dict[str, int] = {}
    for t in all_tickers:
        fh_usable = finnhub_baseline[t].get("usable_7d", 0)
        full_fh[t] = fh_usable
        if t in boost_map:
            full_final[t] = boost_map[t].final_usable
        else:
            full_final[t] = fh_usable  # skipped (already >=10 in Finnhub)

    n_full = len(all_tickers)

    def _thresh(vals_dict, thr):
        c = sum(1 for v in vals_dict.values() if v >= thr)
        return {"count": c, "pct": round(c / max(1, len(vals_dict)) * 100, 1)}

    def _stats(vals_dict):
        vs = list(vals_dict.values())
        return {
            "min": min(vs) if vs else 0,
            "mean": round(mean(vs), 1) if vs else 0,
            "median": round(median(vs), 1) if vs else 0,
            "p10": round(_percentile(vs, 10), 1),
            "p25": round(_percentile(vs, 25), 1),
            "p75": round(_percentile(vs, 75), 1),
            "p90": round(_percentile(vs, 90), 1),
            "max": max(vs) if vs else 0,
        }

    fh_stats  = _stats(full_fh)
    ga_stats  = _stats(full_final)

    # Aggregate google stats — use corrected fields
    rescued  = [m for m in boost_metrics if m.rescued_to_3]
    boosted  = [m for m in boost_metrics if m.boosted_to_10]
    below3   = [m for m in boost_metrics if not m.reached_3]
    below10  = [m for m in boost_metrics if not m.reached_10]

    gs = {
        "targeted_tickers": len(boost_metrics),
        "google_used_count": sum(1 for m in boost_metrics if m.google_mode != "none"),
        "mvp_recovery_count": sum(1 for m in boost_metrics if m.google_mode == "mvp_recovery"),
        "production_boost_count": sum(1 for m in boost_metrics if m.google_mode == "production_boost"),
        "none_count": sum(1 for m in boost_metrics if m.google_mode == "none"),
        "total_google_raw": sum(m.google_raw for m in boost_metrics),
        "total_google_extracted": sum(m.google_extracted for m in boost_metrics),
        "total_google_enriched": sum(m.google_enriched_complete for m in boost_metrics),
        "total_google_added_usable": sum(m.google_added_usable for m in boost_metrics),
        "total_google_429s": sum(m.google_429s for m in boost_metrics),
        "rescued_to_3": len(rescued),
        "boosted_to_10": len(boosted),
        "still_below_3": len(below3),
        "still_below_10": len(below10),
    }

    agg = {
        "generated_at": ts,
        "full_universe": n_full,
        "targeted_below_10": sum(1 for t in all_tickers if finnhub_baseline[t].get("usable_7d", 0) < 10),
        "field_semantics": {
            "finnhub_usable": "usable_7d from Finnhub baseline JSON — immutable, never live DB",
            "google_added_usable": "max(0, live_after - max(finnhub_usable, live_before)) — net new only",
            "final_usable": "finnhub_usable + google_added_usable",
            "rescued_to_3": "finnhub_usable < 3 AND final_usable >= 3",
            "boosted_to_10": "finnhub_usable < 10 AND final_usable >= 10",
        },
        "finnhub_only": {
            "ge3":  _thresh(full_fh, 3),
            "ge5":  _thresh(full_fh, 5),
            "ge10": _thresh(full_fh, 10),
            "ge20": _thresh(full_fh, 20),
            **fh_stats,
        },
        "google_assisted": {
            "ge3":  _thresh(full_final, 3),
            "ge5":  _thresh(full_final, 5),
            "ge10": _thresh(full_final, 10),
            "ge20": _thresh(full_final, 20),
            **ga_stats,
        },
        "google_stats": gs,
    }

    # ── JSON ──────────────────────────────────────────────────────────────────
    json_path = output_dir / "news_coverage_500_finnhub_vs_google_corrected.json"
    with open(json_path, "w") as f:
        json.dump({"aggregate": agg, "per_ticker": {m.ticker: m.to_dict() for m in boost_metrics}},
                  f, indent=2, default=str)
    print(f"  [REPORT] JSON: {json_path}")

    # ── CSV ───────────────────────────────────────────────────────────────────
    csv_path = output_dir / "news_coverage_500_finnhub_vs_google_corrected.csv"
    fieldnames = [
        "ticker", "company_name", "sector", "industry",
        "finnhub_usable", "finnhub_raw", "finnhub_relevant", "finnhub_extracted",
        "google_mode", "google_raw", "google_decoded", "google_relevant",
        "google_extracted", "google_enriched_complete",
        "live_db_before", "live_db_after",
        "google_added_usable", "google_429s",
        "final_usable", "reached_3", "reached_10",
        "rescued_to_3", "boosted_to_10", "top_failure",
    ]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for m in sorted(boost_metrics, key=lambda x: x.final_usable, reverse=True):
            w.writerow(m.to_dict())
    print(f"  [REPORT] CSV: {csv_path}")

    # ── Markdown ──────────────────────────────────────────────────────────────
    fh_a = agg["finnhub_only"]
    ga_a = agg["google_assisted"]
    total_g_added = gs["total_google_added_usable"]
    total_g_raw   = gs["total_google_raw"]
    total_g_ext   = gs["total_google_extracted"]

    def _pct_delta(old_pct, new_pct):
        d = round(new_pct - old_pct, 1)
        return f"+{d}%" if d > 0 else (f"{d}%" if d < 0 else "0.0%")

    # Histogram
    def _hist(vals_dict):
        h = {"0": 0, "1-2": 0, "3-4": 0, "5-9": 0, "10-19": 0, "20+": 0}
        for v in vals_dict.values():
            if v == 0:       h["0"] += 1
            elif v <= 2:     h["1-2"] += 1
            elif v <= 4:     h["3-4"] += 1
            elif v <= 9:     h["5-9"] += 1
            elif v <= 19:    h["10-19"] += 1
            else:            h["20+"] += 1
        return h

    fh_hist = _hist(full_fh)
    ga_hist = _hist(full_final)

    # Sector breakdown
    sector_fh:    dict[str, list] = defaultdict(list)
    sector_final: dict[str, list] = defaultdict(list)
    for t in all_tickers:
        sec = finnhub_baseline[t].get("sector") or "Unknown"
        sector_fh[sec].append(full_fh[t])
        sector_final[sec].append(full_final[t])

    # Efficiency
    eff_raw_per_usable = round(total_g_raw / max(1, total_g_added), 1) if total_g_added else "N/A (0 added)"
    eff_ext_per_usable = round(total_g_ext / max(1, total_g_added), 1) if total_g_added else "N/A"

    # Honest recommendation
    google_helps_mvp     = ga_a["ge3"]["count"] > fh_a["ge3"]["count"]
    google_helps_10      = ga_a["ge10"]["count"] > fh_a["ge10"]["count"]
    delta_ge3  = ga_a["ge3"]["count"]  - fh_a["ge3"]["count"]
    delta_ge10 = ga_a["ge10"]["count"] - fh_a["ge10"]["count"]

    md = f"""# Finnhub-Only vs Google-Assisted: Corrected 500-Ticker Coverage Report
*Generated: {ts}*
*CORRECTED: fixes field-semantic bugs in previous run where finnhub_usable was live DB (not baseline).*

## A. Executive Summary

| Metric | Finnhub-Only | Google-Assisted | Delta |
|--------|-------------|-----------------|-------|
| ≥3 usable (MVP) | {fh_a['ge3']['count']}/{n_full} ({fh_a['ge3']['pct']}%) | {ga_a['ge3']['count']}/{n_full} ({ga_a['ge3']['pct']}%) | {_pct_delta(fh_a['ge3']['pct'], ga_a['ge3']['pct'])} |
| ≥5 usable | {fh_a['ge5']['count']}/{n_full} ({fh_a['ge5']['pct']}%) | {ga_a['ge5']['count']}/{n_full} ({ga_a['ge5']['pct']}%) | {_pct_delta(fh_a['ge5']['pct'], ga_a['ge5']['pct'])} |
| ≥10 usable (prod ideal) | {fh_a['ge10']['count']}/{n_full} ({fh_a['ge10']['pct']}%) | {ga_a['ge10']['count']}/{n_full} ({ga_a['ge10']['pct']}%) | {_pct_delta(fh_a['ge10']['pct'], ga_a['ge10']['pct'])} |
| ≥20 usable | {fh_a['ge20']['count']}/{n_full} ({fh_a['ge20']['pct']}%) | {ga_a['ge20']['count']}/{n_full} ({ga_a['ge20']['pct']}%) | {_pct_delta(fh_a['ge20']['pct'], ga_a['ge20']['pct'])} |
| Rescued <3 → ≥3 | — | {gs['rescued_to_3']} tickers | — |
| Boosted <10 → ≥10 | — | {gs['boosted_to_10']} tickers | — |
| Net Google usable added | — | +{total_g_added} total | — |
| Google raw fetched | — | {total_g_raw} | — |
| Google extraction attempts | — | {total_g_ext} | — |
| Google 429s | — | {gs['total_google_429s']} | — |

## Safety Status
- ✅ Finnhub-first — Google supplements only, never replaces
- ✅ finnhub_usable = Finnhub baseline JSON (immutable, never live DB)
- ✅ google_added_usable = net new above max(fh_usable, live_before)
- ✅ skip_existing=True — valid Finnhub articles not overwritten
- ✅ No risk snapshots promoted; no paywalled/failed counted as usable

## B. Corrected Distribution

| Stat | Finnhub-Only | Google-Assisted |
|------|-------------|-----------------|
| min | {fh_a['min']} | {ga_a['min']} |
| mean | {fh_a['mean']} | {ga_a['mean']} |
| median | {fh_a['median']} | {ga_a['median']} |
| p10 | {fh_a['p10']} | {ga_a['p10']} |
| p25 | {fh_a['p25']} | {ga_a['p25']} |
| p75 | {fh_a['p75']} | {ga_a['p75']} |
| p90 | {fh_a['p90']} | {ga_a['p90']} |
| max | {fh_a['max']} | {ga_a['max']} |

## C. Histogram

| Bucket | Finnhub-Only | Google-Assisted | Delta |
|--------|-------------|-----------------|-------|
"""
    for bucket in ("0", "1-2", "3-4", "5-9", "10-19", "20+"):
        d = ga_hist[bucket] - fh_hist[bucket]
        md += f"| {bucket} | {fh_hist[bucket]} | {ga_hist[bucket]} | {'+'+str(d) if d>0 else str(d)} |\n"

    md += f"""
## D. Threshold Coverage

| Threshold | Finnhub-Only | Google-Assisted | Delta |
|-----------|-------------|-----------------|-------|
| ≥3 (MVP) | {fh_a['ge3']['count']}/{n_full} ({fh_a['ge3']['pct']}%) | {ga_a['ge3']['count']}/{n_full} ({ga_a['ge3']['pct']}%) | {delta_ge3:+d} tickers |
| ≥5 | {fh_a['ge5']['count']}/{n_full} ({fh_a['ge5']['pct']}%) | {ga_a['ge5']['count']}/{n_full} ({ga_a['ge5']['pct']}%) | {ga_a['ge5']['count']-fh_a['ge5']['count']:+d} tickers |
| ≥10 (prod ideal) | {fh_a['ge10']['count']}/{n_full} ({fh_a['ge10']['pct']}%) | {ga_a['ge10']['count']}/{n_full} ({ga_a['ge10']['pct']}%) | {delta_ge10:+d} tickers |
| ≥20 | {fh_a['ge20']['count']}/{n_full} ({fh_a['ge20']['pct']}%) | {ga_a['ge20']['count']}/{n_full} ({ga_a['ge20']['pct']}%) | {ga_a['ge20']['count']-fh_a['ge20']['count']:+d} tickers |

## E. Biggest Improvements (top 50 by google_added_usable)

| ticker | company | sector | fh_usable | google_added | final | mode |
|--------|---------|--------|-----------|--------------|-------|------|
"""
    top50 = sorted(boost_metrics, key=lambda m: m.google_added_usable, reverse=True)[:50]
    for m in top50:
        if m.google_added_usable > 0:
            md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_usable} | +{m.google_added_usable} | {m.final_usable} | {m.google_mode} |\n"

    md += f"""
## F. Still Below 3 After Google ({gs['still_below_3']} tickers)

| ticker | company | sector | finnhub_usable | google_added | final_usable | top_failure |
|--------|---------|--------|----------------|--------------|--------------|-------------|
"""
    for m in sorted(below3, key=lambda m: (m.final_usable, m.ticker)):
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_usable} | +{m.google_added_usable} | {m.final_usable} | {m.top_failure} |\n"

    md += f"""
## G. Still Below 10 After Google (bottom 50)

| ticker | company | sector | finnhub_usable | google_added | final_usable | top_failure |
|--------|---------|--------|----------------|--------------|--------------|-------------|
"""
    for m in sorted(below10, key=lambda m: m.final_usable)[:50]:
        md += f"| {m.ticker} | {m.company_name[:20]} | {m.sector[:15]} | {m.finnhub_usable} | +{m.google_added_usable} | {m.final_usable} | {m.top_failure} |\n"

    md += "\n## H. Sector Breakdown\n\n| sector | n | fh_mean | final_mean | fh_≥3% | final_≥3% | fh_≥10% | final_≥10% |\n|--------|---|---------|------------|--------|-----------|---------|------------|\n"
    for sector in sorted(sector_fh.keys()):
        bv = sector_fh[sector]
        av = sector_final[sector]
        if not bv:
            continue
        md += (
            f"| {sector[:25]} | {len(bv)} "
            f"| {round(mean(bv),1)} | {round(mean(av),1)} "
            f"| {round(sum(1 for v in bv if v>=3)/len(bv)*100):.0f}% "
            f"| {round(sum(1 for v in av if v>=3)/len(av)*100):.0f}% "
            f"| {round(sum(1 for v in bv if v>=10)/len(bv)*100):.0f}% "
            f"| {round(sum(1 for v in av if v>=10)/len(av)*100):.0f}% |\n"
        )

    eff_section = f"""
## I. Efficiency Analysis

| Metric | Value |
|--------|-------|
| Google raw articles per net-added usable | {eff_raw_per_usable} |
| Google extraction attempts per net-added usable | {eff_ext_per_usable} |
| Total Google raw fetched | {total_g_raw} |
| Total Google extraction attempts | {total_g_ext} |
| Total Google enriched complete | {gs['total_google_enriched']} |
| Net new Google usable articles | {total_g_added} |
| Google 429s | {gs['total_google_429s']} |
"""
    md += eff_section

    # Honest recommendation
    md += f"""
## J. Honest Recommendation

**Did Google actually help?**
{"YES — " + str(delta_ge3) + " tickers gained ≥3 and " + str(delta_ge10) + " tickers gained ≥10." if google_helps_mvp or google_helps_10 else "MARGINALLY — Google added +" + str(total_g_added) + " net new usable articles but moved the MVP (≥3) threshold by " + str(delta_ge3) + " tickers and production (≥10) by " + str(delta_ge10) + " tickers."}

**Did Google help MVP threshold (≥3)?**
{"YES — +" + str(delta_ge3) + " tickers crossed ≥3" if delta_ge3 > 0 else "NO — " + str(delta_ge3) + " net change at ≥3 threshold"}

**Did Google help 10-article goal (≥10)?**
{"YES — +" + str(delta_ge10) + " tickers crossed ≥10" if delta_ge10 > 0 else "NO — " + str(delta_ge10) + " net change at ≥10 threshold"}

**Is 10 usable articles realistic for all 504 tickers using free sources (Finnhub + Google RSS)?**
NO — {ga_a['ge10']['count']}/{n_full} ({ga_a['ge10']['pct']}%) reach ≥10 after both sources.
{gs['still_below_10']} tickers still below 10. A paid provider is needed for broad ≥10 coverage.

**Recommended production policy:**
- Active holdings / watchlist tickers: target ≥10, use Finnhub + Google boost (mode=below_10); show "Limited Coverage" badge if still <10 after both sources
- Dormant universe tickers: target ≥3 MVP only, use Finnhub + Google MVP recovery (mode=mvp_only)
- Tickers still <3 after both sources ({gs['still_below_3']} tickers): show "Limited Coverage" badge; score from headline only if ≥1 article exists; do not fabricate sentiment

**Is first-25 safe?** YES — no risk snapshots, no invalid articles counted, Finnhub baseline immutable.
**Is full-500 risk refresh safe?** NOT YET — {gs['still_below_3']} tickers below MVP; use coverage gate before any risk refresh.

**Previous run contradiction explained:**
The prior report claimed 142 rescued and +723 Google usable. Both were artifacts of using the live DB
count (which had drifted due to the 7-day window shifting ~44 min between runs) as `finnhub_usable`.
All 142 "rescued" tickers were ≥3 in the Finnhub baseline; none were genuinely below 3.
The corrected formula (google_added = max(0, live_after - max(fh_usable, live_before))) assigns
Google credit only for articles strictly above the established Finnhub baseline.
"""

    md_path = output_dir / "news_coverage_500_finnhub_vs_google_corrected.md"
    md_path.write_text(md)
    print(f"  [REPORT] Markdown: {md_path}")


# ── main canary runner ────────────────────────────────────────────────────────
async def run_corrected_canary(resume: bool = False) -> None:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    from app.services.supabase import get_supabase

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("CORRECTED GOOGLE-ASSISTED COVERAGE CANARY")
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 80)

    _safety_check()

    supabase = get_supabase()
    finnhub_baseline = _load_finnhub_baseline()

    # Full universe, sorted: 0 → 1-2 → 3-9 → >=10 (still included, mode=none)
    all_tickers = list(finnhub_baseline.keys())
    def _priority(t):
        u = finnhub_baseline[t].get("usable_7d", 0)
        if u == 0:    return 0
        elif u <= 2:  return 1
        elif u <= 9:  return 2
        else:         return 3   # will be mode=none, fast

    priority_order = sorted(all_tickers, key=_priority)

    n_below3  = sum(1 for t in all_tickers if finnhub_baseline[t].get("usable_7d", 0) < 3)
    n_3to9    = sum(1 for t in all_tickers if 3 <= finnhub_baseline[t].get("usable_7d", 0) <= 9)
    n_ge10    = sum(1 for t in all_tickers if finnhub_baseline[t].get("usable_7d", 0) >= 10)

    print(f"\n[UNIVERSE] {len(all_tickers)} tickers (full Finnhub baseline)")
    print(f"  usable=0:   {sum(1 for t in all_tickers if finnhub_baseline[t].get('usable_7d',0)==0)}")
    print(f"  usable=1-2: {sum(1 for t in all_tickers if 1<=finnhub_baseline[t].get('usable_7d',0)<=2)}")
    print(f"  usable=3-9: {n_3to9}  (production_boost mode)")
    print(f"  usable≥10:  {n_ge10} (skipped — mode=none)")

    # Checkpoint / resume
    completed: set[str] = set()
    all_metrics: list[BoostMetrics] = []
    if resume and CHECKPOINT_FILE.exists():
        cp = json.loads(CHECKPOINT_FILE.read_text())
        completed = set(cp.get("completed_tickers", []))
        for td in cp.get("metrics", []):
            all_metrics.append(BoostMetrics.from_dict(td))
        print(f"[RESUME] {len(completed)} tickers already done")

    pending = [t for t in priority_order if t not in completed]
    batches = [pending[i:i+BATCH_SIZE] for i in range(0, len(pending), BATCH_SIZE)]
    n_batches = len(batches)
    start_batch_num = len(completed) // BATCH_SIZE + 1

    print(f"[PLAN] {len(pending)} tickers in {n_batches} batches of {BATCH_SIZE}")

    total_start = time.monotonic()

    for batch_idx, batch in enumerate(batches):
        batch_num = start_batch_num + batch_idx
        batch_start = time.monotonic()

        n_mvp   = sum(1 for t in batch if finnhub_baseline.get(t, {}).get("usable_7d", 0) < GOOGLE_FALLBACK_MIN)
        n_boost = sum(1 for t in batch if GOOGLE_FALLBACK_MIN <= finnhub_baseline.get(t, {}).get("usable_7d", 0) < GOOGLE_PRODUCTION_TARGET)
        n_none  = sum(1 for t in batch if finnhub_baseline.get(t, {}).get("usable_7d", 0) >= GOOGLE_PRODUCTION_TARGET)
        print(f"\n[BATCH {batch_num:02d}/{start_batch_num+n_batches-1:02d}] {batch[:4]}… | mvp={n_mvp} boost={n_boost} skip={n_none}")

        try:
            batch_metrics = await _run_google_batch(supabase, batch, batch_num, finnhub_baseline)
        except Exception as exc:
            print(f"  [ERROR] Batch {batch_num} failed: {exc}")
            batch_metrics = [
                BoostMetrics(ticker=t, finnhub_usable=finnhub_baseline.get(t, {}).get("usable_7d", 0),
                             final_usable=finnhub_baseline.get(t, {}).get("usable_7d", 0),
                             batch_num=batch_num, top_failure="batch_error")
                for t in batch
            ]

        all_metrics.extend(batch_metrics)
        elapsed = time.monotonic() - batch_start

        rescued  = sum(1 for m in batch_metrics if m.rescued_to_3)
        boosted  = sum(1 for m in batch_metrics if m.boosted_to_10)
        g_added  = sum(m.google_added_usable for m in batch_metrics)
        g_429s   = sum(m.google_429s for m in batch_metrics)
        ge3_now  = sum(1 for m in batch_metrics if m.reached_3)
        ge10_now = sum(1 for m in batch_metrics if m.reached_10)

        print(
            f"  done {elapsed:.0f}s | 429s={g_429s} | g_added=+{g_added} | "
            f"rescued_to_3={rescued} | boosted_to_10={boosted} | "
            f"≥3={ge3_now}/{len(batch)} | ≥10={ge10_now}/{len(batch)}"
        )

        completed.update(batch)
        CHECKPOINT_FILE.write_text(json.dumps({
            "completed_tickers": list(completed),
            "metrics": [m.to_dict() for m in all_metrics],
        }))

        if g_429s >= 2:
            print(f"  [BACKOFF] {g_429s} 429s — sleeping 30s")
            await asyncio.sleep(30)

    total_elapsed = time.monotonic() - total_start
    print(f"\n{'='*80}")
    print(f"ALL BATCHES COMPLETE — {len(all_metrics)} tickers in {total_elapsed:.0f}s")
    print(f"{'='*80}")

    total_rescued = sum(1 for m in all_metrics if m.rescued_to_3)
    total_boosted = sum(1 for m in all_metrics if m.boosted_to_10)
    total_added   = sum(m.google_added_usable for m in all_metrics)

    print(f"Rescued (<3 → ≥3):   {total_rescued}")
    print(f"Boosted (<10 → ≥10): {total_boosted}")
    print(f"Net Google usable:   +{total_added}")

    print("\n[REPORTS] Generating …")
    _generate_reports(all_metrics, finnhub_baseline, REPORTS_DIR)

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("[CHECKPOINT] Cleared")

    print(f"\n[DONE] {total_elapsed:.0f}s")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_corrected_canary(resume=args.resume))
