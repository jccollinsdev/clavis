"""Read-only MVP data baseline (Phase 0). Emits JSON to stdout. No writes."""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

WINDOW_DAYS = 7
_NON_USABLE = {"partial", "enrichment_failed", "rejected", "headline_only", "failed"}


def _strict_usable(r: dict) -> bool:
    if r.get("sentiment_score") is None:
        return False
    for f in ("sentiment_reason", "tldr", "what_it_means"):
        if not str(r.get(f) or "").strip():
            return False
    if not (r.get("key_implications") or []):
        return False
    if r.get("headline_only") or r.get("paywalled") or r.get("paywall_detected"):
        return False
    if str(r.get("rejection_reason") or "").strip():
        return False
    if str(r.get("analysis_status") or "").strip().lower() in _NON_USABLE:
        return False
    if str(r.get("extraction_status") or "").strip().lower() not in {"", "success"}:
        return False
    return True


def _is_ho(r: dict) -> bool:
    if _strict_usable(r):
        return False
    if str(r.get("rejection_reason") or "").strip():
        return False
    return bool(r.get("headline_only"))


def _dom(u: str) -> str:
    try:
        h = urlparse(u or "").netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def main() -> None:
    from app.services.supabase import get_supabase

    from app.scripts._dbpage import fetch_all

    sb = get_supabase()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=WINDOW_DAYS)).isoformat()

    uni = fetch_all(
        sb, "ticker_universe", "ticker,sector,index_membership,is_active",
        order_col="ticker",
    )
    sp = [u for u in uni if u.get("index_membership") == "SP500" and u.get("is_active")]
    sp_tickers = sorted({(u["ticker"] or "").upper() for u in sp if u.get("ticker")})

    cols = (
        "id,ticker,canonical_url,source_url,published_at,headline_only,paywalled,"
        "paywall_detected,rejection_reason,analysis_status,extraction_status,"
        "sentiment_score,sentiment_reason,tldr,what_it_means,key_implications"
    )
    rows: list[dict] = []
    CH = 150
    for i in range(0, len(sp_tickers), CH):
        sub = sp_tickers[i:i + CH]
        rows.extend(fetch_all(
            sb, "shared_ticker_events", cols,
            order_col="id", in_col="ticker", in_values=sub,
            gte=("published_at", cutoff),
        ))

    usable = Counter()
    ho = gw = 0
    for r in rows:
        t = (r.get("ticker") or "").upper()
        if _strict_usable(r):
            usable[t] += 1
        elif _is_ho(r):
            ho += 1
            if "news.google.com" in _dom(r.get("canonical_url") or r.get("source_url") or ""):
                gw += 1
    counts = [usable.get(t, 0) for t in sp_tickers]
    nuniv = len(sp_tickers)

    # snapshots
    snap_sample = (
        sb.table("ticker_risk_snapshots")
        .select("ticker,snapshot_date,created_at,methodology_version,"
                "news_sentiment,financial_health,macro_exposure,sector_exposure,"
                "volatility,composite_score,grade,data_status,is_product_visible,"
                "limited_data_dimensions,snapshot_type")
        .order("snapshot_date", desc=True).limit(1).execute().data or []
    )
    latest_date = snap_sample[0]["snapshot_date"] if snap_sample else None
    snaps = []
    if latest_date:
        snaps = fetch_all(
            sb, "ticker_risk_snapshots",
            "id,ticker,snapshot_date,created_at,methodology_version,"
            "news_sentiment,financial_health,macro_exposure,sector_exposure,"
            "volatility,composite_score,grade,data_status,is_product_visible,"
            "limited_data_dimensions,snapshot_type",
            order_col="id", eq=("snapshot_date", latest_date),
        )

    def _age_days(ts):
        try:
            d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return (now - d).total_seconds() / 86400
        except Exception:
            return None

    fresh = Counter()
    for s in snaps:
        a = _age_days(s.get("created_at"))
        if a is None:
            fresh["unknown"] += 1
        elif a <= 1:
            fresh["<=24h"] += 1
        elif a <= 3:
            fresh["<=72h"] += 1
        elif a <= 7:
            fresh["<=7d"] += 1
        else:
            fresh[">7d"] += 1

    def dim_state(s, key):
        v = s.get(key)
        return "scored" if v is not None else "limited_or_null"

    dim_scored = {
        k: sum(1 for s in snaps if s.get(k) is not None)
        for k in ("financial_health", "news_sentiment", "macro_exposure",
                  "sector_exposure", "volatility")
    }

    out = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "window_days": WINDOW_DAYS,
        "universe": {
            "ticker_universe_total": len(uni),
            "sp500_active": nuniv,
        },
        "articles_7d": {
            "total_rows": len(rows),
            "strict_usable_total": sum(counts),
            "headline_only": ho,
            "google_wrapper": gw,
            "coverage_ge3": sum(1 for c in counts if c >= 3),
            "coverage_ge5": sum(1 for c in counts if c >= 5),
            "coverage_ge10": sum(1 for c in counts if c >= 10),
            "coverage_ge20": sum(1 for c in counts if c >= 20),
            "coverage_ge3_pct": round(100 * sum(1 for c in counts if c >= 3) / nuniv, 1),
            "coverage_ge10_pct": round(100 * sum(1 for c in counts if c >= 10) / nuniv, 1),
            "tickers_zero": sum(1 for c in counts if c == 0),
        },
        "snapshots": {
            "latest_snapshot_date": latest_date,
            "rows_at_latest_date": len(snaps),
            "distinct_tickers_at_latest": len({s["ticker"] for s in snaps}),
            "product_visible": sum(1 for s in snaps if s.get("is_product_visible")),
            "methodology_versions": dict(
                Counter(str(s.get("methodology_version")) for s in snaps).most_common()
            ),
            "snapshot_types": dict(
                Counter(str(s.get("snapshot_type")) for s in snaps).most_common()
            ),
            "data_status": dict(
                Counter(str(s.get("data_status")) for s in snaps).most_common()
            ),
            "freshness_by_created_at": dict(fresh.most_common()),
            "dimension_scored_counts": dim_scored,
            "news_sentiment_null": sum(1 for s in snaps if s.get("news_sentiment") is None),
        },
    }
    json.dump(out, sys.stdout, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
