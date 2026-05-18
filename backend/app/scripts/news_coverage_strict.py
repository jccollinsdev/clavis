"""Strict 500/504 news-coverage report (post re-enrichment).

Emits a single JSON document to stdout describing per-ticker STRICT-usable
article counts over the trailing 7-day window for the full S&P 500 universe
(ticker_universe where index_membership='SP500' and is_active=True).

The strict-usable predicate is an exact mirror of
ticker_cache_service._build_event_analyses_from_news_rows._row_is_strict_usable
— a row counts only if it has sentiment_score + sentiment_reason + tldr +
what_it_means + non-empty key_implications, is not headline_only / paywalled /
paywall_detected, has no rejection_reason, and its analysis_status /
extraction_status are not in a non-usable state. Nothing failed/partial/
rejected/headline-only is ever counted as usable.

Run (in the container):
    python3 -m app.scripts.news_coverage_strict
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

WINDOW_DAYS = 7

# Strict baseline (pre-repair), supplied as the agreed reference point.
BASELINE_GE3 = 307
BASELINE_GE10 = 18
BASELINE_TOTAL = 504

_NON_USABLE_STATUSES = {
    "partial", "enrichment_failed", "rejected", "headline_only", "failed",
}


def _row_is_strict_usable(r: dict) -> bool:
    if r.get("sentiment_score") is None:
        return False
    if not str(r.get("sentiment_reason") or "").strip():
        return False
    if not str(r.get("tldr") or "").strip():
        return False
    if not str(r.get("what_it_means") or "").strip():
        return False
    if not (r.get("key_implications") or []):
        return False
    if r.get("headline_only"):
        return False
    if r.get("paywalled") or r.get("paywall_detected"):
        return False
    if str(r.get("rejection_reason") or "").strip():
        return False
    if str(r.get("analysis_status") or "").strip().lower() in _NON_USABLE_STATUSES:
        return False
    if str(r.get("extraction_status") or "").strip().lower() not in {"", "success"}:
        return False
    return True


def _failure_category(r: dict) -> str:
    rej = str(r.get("rejection_reason") or "").strip()
    if rej:
        return f"rejection:{rej}"
    if r.get("headline_only"):
        return "headline_only"
    if r.get("paywalled") or r.get("paywall_detected"):
        return "paywalled"
    st = str(r.get("analysis_status") or "").strip().lower()
    if st in _NON_USABLE_STATUSES:
        return f"analysis_status:{st}"
    es = str(r.get("extraction_status") or "").strip().lower()
    if es not in {"", "success"}:
        return f"extraction_status:{es or 'empty'}"
    if r.get("sentiment_score") is None:
        return "missing_sentiment_score"
    for f in ("sentiment_reason", "tldr", "what_it_means"):
        if not str(r.get(f) or "").strip():
            return f"missing_{f}"
    if not (r.get("key_implications") or []):
        return "missing_key_implications"
    return "other_non_usable"


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    rank = q / 100.0 * (len(s) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(s) - 1)
    frac = rank - lo
    return round(s[lo] + (s[hi] - s[lo]) * frac, 2)


def _domain(url: str) -> str:
    try:
        host = urlparse(url or "").netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def main() -> None:
    from app.services.supabase import get_supabase

    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=WINDOW_DAYS)).isoformat()

    universe = (
        supabase.table("ticker_universe")
        .select("ticker,company_name,sector")
        .eq("index_membership", "SP500")
        .eq("is_active", True)
        .order("priority_rank")
        .execute()
        .data
        or []
    )
    meta = {
        (u.get("ticker") or "").upper(): {
            "company_name": u.get("company_name") or "",
            "sector": u.get("sector") or "Unknown",
        }
        for u in universe
        if u.get("ticker")
    }
    tickers = sorted(meta.keys())
    n = len(tickers)

    cols = (
        "ticker,source,canonical_url,source_url,published_at,sentiment_score,"
        "sentiment_reason,tldr,what_it_means,key_implications,headline_only,"
        "paywalled,paywall_detected,rejection_reason,analysis_status,extraction_status"
    )
    rows: list[dict] = []
    CHUNK = 150
    PAGE = 1000
    for i in range(0, n, CHUNK):
        sub = tickers[i : i + CHUNK]
        offset = 0
        while True:
            page = (
                supabase.table("shared_ticker_events")
                .select(cols)
                .in_("ticker", sub)
                .gte("published_at", cutoff)
                .range(offset, offset + PAGE - 1)
                .execute()
                .data
                or []
            )
            if not page:
                break
            rows.extend(page)
            if len(page) < PAGE:
                break
            offset += PAGE

    usable_by_ticker: dict[str, int] = {t: 0 for t in tickers}
    total_by_ticker: dict[str, int] = {t: 0 for t in tickers}
    source_usable = Counter()
    domain_usable = Counter()
    failure_counts = Counter()
    candidate_nonusable = 0

    for r in rows:
        t = (r.get("ticker") or "").upper()
        if t not in usable_by_ticker:
            continue
        total_by_ticker[t] += 1
        if _row_is_strict_usable(r):
            usable_by_ticker[t] += 1
            src = (r.get("source") or "unknown").strip() or "unknown"
            source_usable[src] += 1
            dom = _domain(r.get("canonical_url") or r.get("source_url") or "")
            domain_usable[dom or "unknown"] += 1
        else:
            candidate_nonusable += 1
            failure_counts[_failure_category(r)] += 1

    counts = [usable_by_ticker[t] for t in tickers]
    ge3 = sum(1 for c in counts if c >= 3)
    ge5 = sum(1 for c in counts if c >= 5)
    ge10 = sum(1 for c in counts if c >= 10)
    ge20 = sum(1 for c in counts if c >= 20)

    def bucket(c: int) -> str:
        if c == 0:
            return "0"
        if c <= 2:
            return "1-2"
        if c <= 4:
            return "3-4"
        if c <= 9:
            return "5-9"
        if c <= 19:
            return "10-19"
        return "20+"

    hist = Counter(bucket(c) for c in counts)

    sector_agg: dict[str, list[int]] = defaultdict(list)
    for t in tickers:
        sector_agg[meta[t]["sector"]].append(usable_by_ticker[t])
    sector_rows = []
    for sec, vals in sorted(sector_agg.items(), key=lambda kv: -statistics.mean(kv[1] or [0])):
        sector_rows.append(
            {
                "sector": sec,
                "tickers": len(vals),
                "mean_usable": round(statistics.mean(vals), 2) if vals else 0.0,
                "median_usable": round(statistics.median(vals), 1) if vals else 0.0,
                "pct_ge3": _pct(sum(1 for v in vals if v >= 3), len(vals)),
                "pct_ge10": _pct(sum(1 for v in vals if v >= 10), len(vals)),
            }
        )

    per_ticker = [
        {
            "ticker": t,
            "company_name": meta[t]["company_name"],
            "sector": meta[t]["sector"],
            "usable_strict": usable_by_ticker[t],
            "total_rows_7d": total_by_ticker[t],
            "bucket": bucket(usable_by_ticker[t]),
            "reached_3": usable_by_ticker[t] >= 3,
            "reached_5": usable_by_ticker[t] >= 5,
            "reached_10": usable_by_ticker[t] >= 10,
            "reached_20": usable_by_ticker[t] >= 20,
        }
        for t in tickers
    ]
    bottom50 = sorted(per_ticker, key=lambda r: (r["usable_strict"], r["ticker"]))[:50]
    top50 = sorted(per_ticker, key=lambda r: (-r["usable_strict"], r["ticker"]))[:50]

    summary = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "window_days": WINDOW_DAYS,
        "definition": "strict (mirrors ticker_cache_service._row_is_strict_usable)",
        "universe_source": "ticker_universe[index_membership=SP500,is_active=True]",
        "tickers_total": n,
        "events_rows_7d": len(rows),
        "candidate_nonusable_rows": candidate_nonusable,
        "thresholds": {
            "ge3": ge3, "ge3_pct": _pct(ge3, n),
            "ge5": ge5, "ge5_pct": _pct(ge5, n),
            "ge10": ge10, "ge10_pct": _pct(ge10, n),
            "ge20": ge20, "ge20_pct": _pct(ge20, n),
        },
        "distribution": {
            "min": min(counts) if counts else 0,
            "p10": _percentile(counts, 10),
            "p25": _percentile(counts, 25),
            "median": _percentile(counts, 50),
            "mean": round(statistics.mean(counts), 2) if counts else 0.0,
            "p75": _percentile(counts, 75),
            "p90": _percentile(counts, 90),
            "max": max(counts) if counts else 0,
        },
        "histogram": {
            k: hist.get(k, 0)
            for k in ("0", "1-2", "3-4", "5-9", "10-19", "20+")
        },
        "baseline_strict": {
            "ge3": BASELINE_GE3, "ge3_total": BASELINE_TOTAL,
            "ge10": BASELINE_GE10, "ge10_total": BASELINE_TOTAL,
        },
        "vs_baseline": {
            "ge3_before": f"{BASELINE_GE3}/{BASELINE_TOTAL}",
            "ge3_after": f"{ge3}/{n}",
            "ge3_delta": ge3 - BASELINE_GE3,
            "ge10_before": f"{BASELINE_GE10}/{BASELINE_TOTAL}",
            "ge10_after": f"{ge10}/{n}",
            "ge10_delta": ge10 - BASELINE_GE10,
        },
        "sector_breakdown": sector_rows,
        "source_breakdown_top30": [
            {"source": s, "usable_articles": c}
            for s, c in source_usable.most_common(30)
        ],
        "domain_breakdown_top30": [
            {"domain": d, "usable_articles": c}
            for d, c in domain_usable.most_common(30)
        ],
        "failure_breakdown": [
            {
                "category": cat,
                "count": cnt,
                "pct_of_nonusable": _pct(cnt, candidate_nonusable),
            }
            for cat, cnt in failure_counts.most_common()
        ],
        "bottom_50": bottom50,
        "top_50": top50,
        "tickers": per_ticker,
    }
    json.dump(summary, sys.stdout, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
