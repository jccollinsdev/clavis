"""Read-only root-cause audit of the strict-report `headline_only` bucket.

Mirrors news_coverage_strict's strict-usable predicate and failure
categorisation so the audited population is exactly the same rows that the
strict 500/504 report counted as the `headline_only` non-usable bucket
(trailing 7d, SP500 universe).

Emits one JSON document to stdout. Read-only EXCEPT an optional no-write
fresh-extraction probe of 10 sampled rows (outbound HTTP only; nothing is
written back to the DB).

Run (in container):
    python3 -m app.scripts.audit_headline_only           # audit only
    python3 -m app.scripts.audit_headline_only --probe    # + 10-row extraction probe
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

WINDOW_DAYS = 7
_NON_USABLE_STATUSES = {
    "partial", "enrichment_failed", "rejected", "headline_only", "failed",
}
_PLACEHOLDERS = ("[No body extracted]", "[Paywalled]", "[Blocked]")


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
    if str(r.get("rejection_reason") or "").strip():
        return "rejection:" + str(r.get("rejection_reason")).strip()
    if r.get("headline_only"):
        return "headline_only"
    if r.get("paywalled") or r.get("paywall_detected"):
        return "paywalled"
    st = str(r.get("analysis_status") or "").strip().lower()
    if st in _NON_USABLE_STATUSES:
        return "analysis_status:" + st
    es = str(r.get("extraction_status") or "").strip().lower()
    if es not in {"", "success"}:
        return "extraction_status:" + (es or "empty")
    if r.get("sentiment_score") is None:
        return "missing_sentiment_score"
    for f in ("sentiment_reason", "tldr", "what_it_means"):
        if not str(r.get(f) or "").strip():
            return "missing_" + f
    if not (r.get("key_implications") or []):
        return "missing_key_implications"
    return "other_non_usable"


def _domain(url: str) -> str:
    try:
        h = urlparse(url or "").netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def _real_body(r: dict) -> str:
    b = str(r.get("body") or "").strip()
    if not b or any(b.startswith(p) for p in _PLACEHOLDERS):
        return ""
    return b


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


async def _probe(samples: list[dict]) -> list[dict]:
    from app.services.article_scraper import enrich_article_content
    from app.services.news_enrichment import assess_article_body_quality

    out = []
    for s in samples:
        url = s["url"]
        rec = {
            "ticker": s["ticker"], "domain": s["domain"], "url": url[:160],
            "old_body_words": s["body_words"],
        }
        try:
            art = {
                "url": url,
                "title": s.get("title") or "",
                "ticker": s.get("ticker") or "",
                "source": s.get("source") or "",
                "company_name": s.get("company_name") or s.get("ticker") or "",
            }
            res = await asyncio.wait_for(
                enrich_article_content(art), timeout=45
            )
            body = str(res.get("body") or "")
            words = len((_real_body({"body": body})).split())
            usable, reason, cleaned = assess_article_body_quality(
                {**art, "body": body}
            )
            rec.update(
                scrape_status=str(res.get("scrape_status"))[:60],
                resolution_status=str(res.get("resolution_status"))[:40],
                recovered_words=words,
                recovered_usable=bool(usable),
                reject_reason=reason,
                recovered=words >= 50 and bool(usable),
            )
        except Exception as exc:  # noqa: BLE001
            rec.update(error=str(exc)[:140], recovered=False)
        out.append(rec)
    return out


def main() -> None:
    do_probe = "--probe" in sys.argv
    from app.services.supabase import get_supabase

    sb = get_supabase()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=WINDOW_DAYS)).isoformat()

    universe = (
        sb.table("ticker_universe")
        .select("ticker,company_name,sector")
        .eq("index_membership", "SP500")
        .eq("is_active", True)
        .execute()
        .data
        or []
    )
    meta = {
        (u["ticker"] or "").upper(): {
            "company_name": u.get("company_name") or "",
            "sector": u.get("sector") or "Unknown",
        }
        for u in universe
        if u.get("ticker")
    }
    tickers = sorted(meta)
    n_univ = len(tickers)

    cols = (
        "ticker,source,canonical_url,source_url,published_at,title,body,"
        "body_markdown,body_length,extraction_status,extraction_provider_used,"
        "headline_only,paywalled,paywall_detected,rejection_reason,"
        "analysis_status,sentiment_score,sentiment_reason,tldr,what_it_means,"
        "key_implications"
    )
    rows: list[dict] = []
    CH, PG = 150, 1000
    for i in range(0, n_univ, CH):
        sub = tickers[i : i + CH]
        off = 0
        while True:
            pg = (
                sb.table("shared_ticker_events")
                .select(cols)
                .in_("ticker", sub)
                .gte("published_at", cutoff)
                .range(off, off + PG - 1)
                .execute()
                .data
                or []
            )
            if not pg:
                break
            rows.extend(pg)
            if len(pg) < PG:
                break
            off += PG

    # strict-usable per ticker -> which tickers are still < 3
    usable_ct = {t: 0 for t in tickers}
    for r in rows:
        t = (r.get("ticker") or "").upper()
        if t in usable_ct and _row_is_strict_usable(r):
            usable_ct[t] += 1
    below3 = {t for t in tickers if usable_ct[t] < 3}
    zero_t = {t for t in tickers if usable_ct[t] == 0}

    # the exact headline_only bucket
    ho = [
        r
        for r in rows
        if (r.get("ticker") or "").upper() in meta
        and not _row_is_strict_usable(r)
        and _failure_category(r) == "headline_only"
    ]
    total = len(ho)

    url_present = url_missing = 0
    body_present = body_ge300_len = body_ge300_real = 0
    es_ctr, prov_ctr, rej_ctr, astatus_ctr = Counter(), Counter(), Counter(), Counter()
    src_ctr, dom_ctr = Counter(), Counter()
    yahoo_dom = Counter()
    by_ticker_below3 = Counter()
    by_sector_below3 = Counter()
    samples_by_dom: dict[str, list] = defaultdict(list)

    for r in ho:
        url = str(r.get("canonical_url") or r.get("source_url") or "").strip()
        if url:
            url_present += 1
        else:
            url_missing += 1
        rb = _real_body(r)
        if rb:
            body_present += 1
        bl = r.get("body_length")
        try:
            bl = int(bl) if bl is not None else len(str(r.get("body") or ""))
        except Exception:
            bl = len(str(r.get("body") or ""))
        if bl >= 300:
            body_ge300_len += 1
        if len(rb) >= 300:
            body_ge300_real += 1
        es_ctr[str(r.get("extraction_status") or "(null)")] += 1
        prov_ctr[str(r.get("extraction_provider_used") or "(null)")] += 1
        rej_ctr[str(r.get("rejection_reason") or "(null)")] += 1
        astatus_ctr[str(r.get("analysis_status") or "(null)")] += 1
        src = (str(r.get("source") or "unknown").strip() or "unknown")
        src_ctr[src] += 1
        dom = _domain(url) or "(no-url)"
        dom_ctr[dom] += 1
        if "yahoo" in dom or "yahoo" in src.lower():
            yahoo_dom[dom or src] += 1
        t = (r.get("ticker") or "").upper()
        if t in below3:
            by_ticker_below3[t] += 1
            by_sector_below3[meta[t]["sector"]] += 1
        if len(samples_by_dom[dom]) < 3:
            samples_by_dom[dom].append(
                {
                    "ticker": t,
                    "domain": dom,
                    "has_url": bool(url),
                    "body_words": len(rb.split()),
                    "body_length_col": r.get("body_length"),
                    "extraction_status": r.get("extraction_status"),
                    "title": str(r.get("title") or "")[:90],
                }
            )

    sample20 = []
    for dom, _c in dom_ctr.most_common():
        for s in samples_by_dom.get(dom, []):
            sample20.append(s)
            if len(sample20) >= 20:
                break
        if len(sample20) >= 20:
            break

    probe_results = []
    if do_probe:
        picks, seen_dom = [], Counter()
        for dom, _c in dom_ctr.most_common():
            if dom == "(no-url)":
                continue
            for r in ho:
                url = str(r.get("canonical_url") or r.get("source_url") or "").strip()
                if not url or _domain(url) != dom:
                    continue
                if seen_dom[dom] >= 2:
                    break
                picks.append(
                    {
                        "url": url,
                        "ticker": (r.get("ticker") or "").upper(),
                        "title": r.get("title") or "",
                        "source": r.get("source") or "",
                        "company_name": meta.get(
                            (r.get("ticker") or "").upper(), {}
                        ).get("company_name", ""),
                        "domain": dom,
                        "body_words": len(_real_body(r).split()),
                    }
                )
                seen_dom[dom] += 1
                if len(picks) >= 10:
                    break
            if len(picks) >= 10:
                break
        probe_results = asyncio.run(_probe(picks))

    summary = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "window_days": WINDOW_DAYS,
        "universe_tickers": n_univ,
        "events_rows_7d": len(rows),
        "headline_only_total": total,
        "url_present": url_present,
        "url_missing": url_missing,
        "body_present_nonplaceholder": body_present,
        "body_length_col_ge300": body_ge300_len,
        "real_body_ge300_chars": body_ge300_real,
        "extraction_status_counts": dict(es_ctr.most_common()),
        "extraction_provider_used_counts": dict(prov_ctr.most_common()),
        "rejection_reason_counts": dict(rej_ctr.most_common()),
        "analysis_status_counts": dict(astatus_ctr.most_common()),
        "source_counts_top20": dict(src_ctr.most_common(20)),
        "domain_counts_top20": dict(dom_ctr.most_common(20)),
        "yahoo_breakdown": dict(yahoo_dom.most_common()),
        "below3_tickers_total": len(below3),
        "zero_usable_tickers_total": len(zero_t),
        "headline_only_rows_for_below3_tickers": sum(by_ticker_below3.values()),
        "below3_tickers_by_sector_headline_only": dict(
            by_sector_below3.most_common()
        ),
        "top25_below3_tickers_by_headline_only": [
            {
                "ticker": t,
                "sector": meta[t]["sector"],
                "strict_usable": usable_ct[t],
                "headline_only_rows": c,
            }
            for t, c in by_ticker_below3.most_common(25)
        ],
        "sample_20": sample20,
        "probe_results": probe_results,
    }
    json.dump(summary, sys.stdout, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
