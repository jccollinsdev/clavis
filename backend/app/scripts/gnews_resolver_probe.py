"""Bounded, read-only Google-News wrapper-URL resolution investigation.

Phase 1 (counts) + Phase 4 sample (100 deduped news.google.com wrapper rows
from the trailing-7d SP500 headline_only bucket) + a from-scratch
batchexecute-style resolver POC + Phase 5 no-write extraction test on
resolved publisher URLs.

NO DB writes. NO MiniMax. Low concurrency, short timeouts, single attempt
(no retry storms), in-memory cache. Mimics only the public Google News
page's own URL-resolution call — no proxy / CAPTCHA / login / paywall
bypass / fingerprint evasion.

Modes:
    python3 -m app.scripts.gnews_resolver_probe counts
        -> Phase 1 counts only (fast).
    python3 -m app.scripts.gnews_resolver_probe sample
        -> emit the 100-row stratified sample (no resolving), JSON.
    python3 -m app.scripts.gnews_resolver_probe run
        -> counts + sample + batchexecute resolve + extraction, JSON.
    python3 -m app.scripts.gnews_resolver_probe extract <urls.json>
        -> no-write extraction over an explicit list of publisher URLs
           (used to score Playwright-resolved URLs), JSON.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

WINDOW_DAYS = 7
SAMPLE_SIZE = 100
RESOLVE_CONCURRENCY = 2
RESOLVE_TIMEOUT = 12.0
EXTRACT_CONCURRENCY = 2
EXTRACT_TIMEOUT = 45.0

_NON_USABLE = {"partial", "enrichment_failed", "rejected", "headline_only", "failed"}
_PLACEHOLDERS = ("[No body extracted]", "[Paywalled]", "[Blocked]")
_UA = "Mozilla/5.0 (compatible; ClavisBot/1.0; +https://clavis.andoverdigital.com)"


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


def _is_headline_only_bucket(r: dict) -> bool:
    if _strict_usable(r):
        return False
    if str(r.get("rejection_reason") or "").strip():
        return False
    return bool(r.get("headline_only"))


def _domain(u: str) -> str:
    try:
        h = urlparse(u or "").netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def _is_google(u: str) -> bool:
    return "news.google.com" in _domain(u) or _domain(u).endswith("google.com")


# ───────────────────────── batchexecute-style resolver ──────────────────────
_BATCH_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"


def _extract_tokens(html: str) -> tuple[str, str, str] | None:
    """Pull (gn_art_id, signature, timestamp) from the public wrapper page.

    These are the same values the public page itself feeds to its
    URL-resolution call. Not an access-control bypass — just reading the
    markup the page already serves.
    """
    m_id = re.search(r'data-n-a-id="([^"]+)"', html)
    m_sg = re.search(r'data-n-a-sg="([^"]+)"', html)
    m_ts = re.search(r'data-n-a-ts="([^"]+)"', html)
    if m_id and m_sg and m_ts:
        return m_id.group(1), m_sg.group(1), m_ts.group(1)
    # alternate markup: c-wiz with jslog / AF_initDataCallback containing the id
    m_id2 = re.search(r'\["(garturlreq[^"]*)"', html)
    return None if not (m_id2) else None


def _parse_batch_url(text: str) -> str | None:
    # response is XSSI-guarded: )]}'\n<len>\n[...]
    body = text
    if body.startswith(")]}'"):
        body = body.split("\n", 1)[1] if "\n" in body else body[4:]
    # find a https URL inside the garturlres payload
    try:
        for chunk in re.findall(r'\[\\?"garturlres\\?".*?\]', body):
            urls = re.findall(r'https?:\\?/\\?/[^\\"\]]+', chunk)
            for u in urls:
                clean = u.replace("\\/", "/").replace("\\u003d", "=")
                if not _is_google(clean):
                    return clean
    except Exception:
        pass
    urls = re.findall(r'https?://[^\\"\\]\s]+', body.replace("\\/", "/"))
    for u in urls:
        if not _is_google(u) and "gstatic" not in u and "schema.org" not in u:
            return u
    return None


async def resolve_batchexecute(
    url: str, client: httpx.AsyncClient, cache: dict
) -> dict:
    if url in cache:
        return {**cache[url], "cached": True}
    t0 = time.monotonic()

    def done(status, resolved=None):
        r = {
            "status": status,
            "resolved_url": resolved,
            "runtime_ms": int((time.monotonic() - t0) * 1000),
            "cached": False,
        }
        cache[url] = r
        return r

    if not url or "news.google.com" not in url:
        return done("invalid_url")
    try:
        page = await client.get(
            url, headers={"User-Agent": _UA}, timeout=RESOLVE_TIMEOUT,
            follow_redirects=True,
        )
    except (httpx.TimeoutException, asyncio.TimeoutError):
        return done("timeout")
    except Exception:
        return done("resolution_request_failed")

    final = str(page.url)
    if not _is_google(final) and final.startswith("http"):
        return done("resolved", final)  # plain redirect already left Google

    html = page.text or ""
    low = html.lower()
    if "consent.google.com" in final or "consent" in low[:2000] and "captcha" in low:
        return done("consent_or_captcha")
    if "recaptcha" in low or "/sorry/" in final:
        return done("consent_or_captcha")

    toks = _extract_tokens(html)
    if not toks:
        return done("token_parse_failed")
    art_id, sig, ts = toks
    f_req = (
        '[[["Fbv4je","[\\"garturlreq\\",[[\\"X\\",\\"X\\",[\\"X\\",\\"X\\"],'
        "null,null,1,1,\\\"US:en\\\",null,1,null,null,null,null,null,0,1],"
        "\\\"X\\\",\\\"X\\\",1,[1,1,1],1,1,null,0,0,null,0],\\\""
        + art_id + "\\\"," + ts + ",\\\"" + sig + '\\"]",null,"generic"]]]'
    )
    try:
        resp = await client.post(
            _BATCH_URL,
            params={"rpcids": "Fbv4je", "source-path": "/", "hl": "en-US"},
            data={"f.req": f_req},
            headers={
                "User-Agent": _UA,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            timeout=RESOLVE_TIMEOUT,
        )
    except (httpx.TimeoutException, asyncio.TimeoutError):
        return done("timeout")
    except Exception:
        return done("resolution_request_failed")

    if resp.status_code != 200:
        return done("resolution_request_failed")
    pub = _parse_batch_url(resp.text)
    if not pub:
        return done("still_google_url")
    if _is_google(pub):
        return done("still_google_url")
    return done("resolved", pub)


# ───────────────────────── extraction (no-write) ────────────────────────────
def _real_body(b: str) -> str:
    b = (b or "").strip()
    return "" if (not b or any(b.startswith(p) for p in _PLACEHOLDERS)) else b


async def extract_no_write(url: str, ticker: str, title: str, sem) -> dict:
    from app.services.article_scraper import enrich_article_content
    from app.services.news_enrichment import assess_article_body_quality

    rec = {"url": url[:200], "ticker": ticker, "domain": _domain(url)}
    async with sem:
        try:
            art = {"url": url, "title": title or "", "ticker": ticker,
                    "company_name": ticker, "source": _domain(url)}
            res = await asyncio.wait_for(
                enrich_article_content(art), timeout=EXTRACT_TIMEOUT
            )
            raw = str(res.get("body") or "")
            body = _real_body(raw)
            usable, reason, cleaned = assess_article_body_quality(
                {**art, "body": raw}
            )
            blen = len(body)
            rec.update(
                scrape_status=str(res.get("scrape_status"))[:50],
                body_length=blen,
                body_ge_300=blen >= 300,
                quality_pass=bool(usable),
                reject_reason=reason,
                paywall_block=bool(
                    raw.startswith("[Paywalled]") or raw.startswith("[Blocked]")
                ),
                eligible_for_minimax=blen >= 300 and bool(usable),
            )
        except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
            rec.update(error=str(exc)[:140], eligible_for_minimax=False,
                       quality_pass=False, body_ge_300=False)
    return rec


# ───────────────────────────── data access ─────────────────────────────────
def _fetch_universe_and_rows(sb):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=WINDOW_DAYS)).isoformat()
    uni = (
        sb.table("ticker_universe").select("ticker,sector")
        .eq("index_membership", "SP500").eq("is_active", True)
        .execute().data or []
    )
    meta = {(u["ticker"] or "").upper(): (u.get("sector") or "Unknown")
            for u in uni if u.get("ticker")}
    tickers = sorted(meta)
    cols = (
        "ticker,source,canonical_url,source_url,published_at,title,"
        "headline_only,paywalled,paywall_detected,rejection_reason,"
        "analysis_status,extraction_status,sentiment_score,sentiment_reason,"
        "tldr,what_it_means,key_implications"
    )
    rows: list[dict] = []
    CH, PG = 150, 1000
    for i in range(0, len(tickers), CH):
        sub = tickers[i:i + CH]
        off = 0
        while True:
            pg = (sb.table("shared_ticker_events").select(cols)
                  .in_("ticker", sub).gte("published_at", cutoff)
                  .range(off, off + PG - 1).execute().data or [])
            if not pg:
                break
            rows.extend(pg)
            if len(pg) < PG:
                break
            off += PG
    return meta, tickers, rows, now


def _counts(meta, tickers, rows):
    usable = {t: 0 for t in tickers}
    for r in rows:
        t = (r.get("ticker") or "").upper()
        if t in usable and _strict_usable(r):
            usable[t] += 1
    ho = [r for r in rows
          if (r.get("ticker") or "").upper() in meta and _is_headline_only_bucket(r)]
    gw = [r for r in ho
          if "news.google.com" in _domain(
              r.get("canonical_url") or r.get("source_url") or "")]

    def band(t):
        c = usable.get(t, 0)
        return "lt3" if c < 3 else ("b3_9" if c < 10 else "ge10")

    gw_tickers = {(r.get("ticker") or "").upper() for r in gw}
    band_ct = Counter(band(t) for t in gw_tickers)
    return {
        "headline_only_total": len(ho),
        "google_wrapper_total": len(gw),
        "google_wrapper_pct_of_headline_only": round(
            100 * len(gw) / max(1, len(ho)), 1),
        "tickers_with_google_wrapper_rows": len(gw_tickers),
        "affected_tickers_lt3_strict": band_ct.get("lt3", 0),
        "affected_tickers_3to9_strict": band_ct.get("b3_9", 0),
        "affected_tickers_ge10_strict": band_ct.get("ge10", 0),
    }, usable, gw


def _stratified_sample(gw, usable):
    seen, lt3, b39, ge10 = set(), [], [], []
    for r in gw:
        u = r.get("canonical_url") or r.get("source_url") or ""
        if u in seen:
            continue
        seen.add(u)
        t = (r.get("ticker") or "").upper()
        c = usable.get(t, 0)
        item = {"original_google_url": u, "ticker": t,
                "current_strict_usable": c, "title": r.get("title") or ""}
        (lt3 if c < 3 else (b39 if c < 10 else ge10)).append(item)
    out = lt3[:55] + b39[:35] + ge10[:10]
    if len(out) < SAMPLE_SIZE:
        for pool in (lt3[55:], b39[35:], ge10[10:]):
            for it in pool:
                if len(out) >= SAMPLE_SIZE:
                    break
                out.append(it)
    return out[:SAMPLE_SIZE]


async def _run(sample):
    cache: dict = {}
    sem_r = asyncio.Semaphore(RESOLVE_CONCURRENCY)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async def one(it):
            async with sem_r:
                res = await resolve_batchexecute(
                    it["original_google_url"], client, cache)
            it["batchexecute_status"] = res["status"]
            it["batchexecute_resolved_url"] = res["resolved_url"]
            it["batchexecute_runtime_ms"] = res["runtime_ms"]
            return it
        sample = await asyncio.gather(*[one(i) for i in sample])
    sem_e = asyncio.Semaphore(EXTRACT_CONCURRENCY)
    tasks = []
    for it in sample:
        if it.get("batchexecute_status") == "resolved" and it.get(
                "batchexecute_resolved_url"):
            tasks.append((it, extract_no_write(
                it["batchexecute_resolved_url"], it["ticker"],
                it.get("title", ""), sem_e)))
    ex = await asyncio.gather(*[t for _, t in tasks]) if tasks else []
    for (it, _), e in zip(tasks, ex):
        it["batchexecute_extraction"] = e
    return sample


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"

    if mode == "extract":
        payload = json.load(open(sys.argv[2]))

        async def go():
            sem = asyncio.Semaphore(EXTRACT_CONCURRENCY)
            res = await asyncio.gather(*[
                extract_no_write(p["url"], p.get("ticker", ""),
                                 p.get("title", ""), sem) for p in payload
            ])
            return res
        json.dump({"extractions": asyncio.run(go())}, sys.stdout, default=str)
        sys.stdout.write("\n")
        return

    from app.services.supabase import get_supabase
    sb = get_supabase()
    meta, tickers, rows, now = _fetch_universe_and_rows(sb)
    counts, usable, gw = _counts(meta, tickers, rows)
    out = {"generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
           "window_days": WINDOW_DAYS, "phase1_counts": counts}

    if mode == "counts":
        json.dump(out, sys.stdout, default=str)
        sys.stdout.write("\n")
        return

    sample = _stratified_sample(gw, usable)
    out["sample_size"] = len(sample)
    if mode == "sample":
        out["sample"] = sample
        json.dump(out, sys.stdout, default=str)
        sys.stdout.write("\n")
        return

    out["sample"] = asyncio.run(_run(sample))
    json.dump(out, sys.stdout, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
