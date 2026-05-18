"""Production-safe Google-News wrapper-URL resolver.

Resolves an existing ``news.google.com`` wrapper URL to its real publisher
URL by mimicking ONLY the public wrapper page's own URL-resolution call
(GET the public page, read the tokens it already serves, POST them to the
same public batchexecute endpoint the page itself uses). It does not, and
must not, defeat any access control: no proxy, no CAPTCHA/consent/login/
paywall/bot-wall bypass, no fingerprint or stealth evasion. It is NOT a
news-discovery source — it only re-resolves wrapper URLs already stored.

Validated POC: 100/100 resolution, ~160ms mean, identical output to a
Playwright browser on every overlap.

Status codes: resolved | not_google_wrapper | token_parse_failed |
resolution_request_failed | still_google_url | consent_or_captcha |
timeout | invalid_url | error
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

RESOLVER_VERSION = "batchexecute-1"
_BATCH_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
_UA = "Mozilla/5.0 (compatible; ClavisBot/1.0; +https://clavis.andoverdigital.com)"
_CACHE_TABLE = "gnews_wrapper_resolution"

STATUS_RESOLVED = "resolved"
STATUS_NOT_WRAPPER = "not_google_wrapper"
STATUS_TOKEN_FAIL = "token_parse_failed"
STATUS_REQ_FAIL = "resolution_request_failed"
STATUS_STILL_GOOGLE = "still_google_url"
STATUS_CONSENT = "consent_or_captcha"
STATUS_TIMEOUT = "timeout"
STATUS_INVALID = "invalid_url"
STATUS_ERROR = "error"

_TERMINAL_OK = {STATUS_RESOLVED}
# Negative results we should not hammer again (cache hit short-circuits).
_TERMINAL_NEG = {STATUS_STILL_GOOGLE, STATUS_CONSENT, STATUS_NOT_WRAPPER, STATUS_INVALID}


def _domain(u: str) -> str:
    try:
        h = urlparse(u or "").netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def is_google_wrapper(url: str) -> bool:
    return "news.google.com" in _domain(url)


def _is_google(url: str) -> bool:
    d = _domain(url)
    return "google.com" in d or "gstatic.com" in d


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_tokens(html: str) -> tuple[str, str, str] | None:
    """(gn_art_id, signature, timestamp) from the public wrapper page markup."""
    m_id = re.search(r'data-n-a-id="([^"]+)"', html)
    m_sg = re.search(r'data-n-a-sg="([^"]+)"', html)
    m_ts = re.search(r'data-n-a-ts="([^"]+)"', html)
    if m_id and m_sg and m_ts:
        return m_id.group(1), m_sg.group(1), m_ts.group(1)
    return None


def parse_batch_url(text: str) -> str | None:
    body = text
    if body.startswith(")]}'"):
        body = body.split("\n", 1)[1] if "\n" in body else body[4:]
    try:
        for chunk in re.findall(r'\[\\?"garturlres\\?".*?\]', body):
            for u in re.findall(r'https?:\\?/\\?/[^\\"\]]+', chunk):
                clean = u.replace("\\/", "/").replace("\\u003d", "=")
                if not _is_google(clean):
                    return clean
    except Exception:
        pass
    for u in re.findall(r'https?://[^\\"\]\s]+', body.replace("\\/", "/")):
        if not _is_google(u) and "gstatic" not in u and "schema.org" not in u:
            return u
    return None


def _result(url: str, status: str, t0: float, resolved: str | None = None) -> dict:
    return {
        "original_url": url,
        "status": status,
        "resolved_url": resolved,
        "failure_reason": None if status == STATUS_RESOLVED else status,
        "runtime_ms": int((time.monotonic() - t0) * 1000),
        "resolver_version": RESOLVER_VERSION,
        "source_domain": _domain(url),
        "final_domain": _domain(resolved) if resolved else None,
        "cached": False,
    }


async def resolve_wrapper(
    url: str,
    client: httpx.AsyncClient,
    *,
    timeout: float = 12.0,
) -> dict:
    """Resolve one wrapper URL. Single attempt, no retry storms."""
    t0 = time.monotonic()
    if not url or not url.startswith(("http://", "https://")):
        return _result(url, STATUS_INVALID, t0)
    if not is_google_wrapper(url):
        return _result(url, STATUS_NOT_WRAPPER, t0)

    try:
        page = await client.get(
            url, headers={"User-Agent": _UA}, timeout=timeout,
            follow_redirects=True,
        )
    except (httpx.TimeoutException, asyncio.TimeoutError):
        return _result(url, STATUS_TIMEOUT, t0)
    except Exception:
        return _result(url, STATUS_REQ_FAIL, t0)

    final = str(page.url)
    if not _is_google(final) and final.startswith("http"):
        return _result(url, STATUS_RESOLVED, t0, final)

    html = page.text or ""
    low = html[:3000].lower()
    if (
        "consent.google.com" in final
        or "/sorry/" in final
        or "recaptcha" in low
        or ("consent" in low and "captcha" in low)
    ):
        return _result(url, STATUS_CONSENT, t0)

    toks = extract_tokens(html)
    if not toks:
        return _result(url, STATUS_TOKEN_FAIL, t0)
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
            timeout=timeout,
        )
    except (httpx.TimeoutException, asyncio.TimeoutError):
        return _result(url, STATUS_TIMEOUT, t0)
    except Exception:
        return _result(url, STATUS_REQ_FAIL, t0)

    if resp.status_code != 200:
        return _result(url, STATUS_REQ_FAIL, t0)
    pub = parse_batch_url(resp.text)
    if not pub or _is_google(pub):
        return _result(url, STATUS_STILL_GOOGLE, t0)
    return _result(url, STATUS_RESOLVED, t0, pub)


# ───────────────────────────── cache layer ─────────────────────────────────
def cache_lookup(sb, url: str) -> dict | None:
    try:
        r = (
            sb.table(_CACHE_TABLE).select("*")
            .eq("original_url", url).limit(1).execute()
        )
        return r.data[0] if r.data else None
    except Exception as exc:  # table may not exist yet
        logger.debug("gnews cache lookup skipped: %s", exc)
        return None


def cache_store(sb, res: dict) -> None:
    try:
        existing = cache_lookup(sb, res["original_url"])
        attempts = (existing.get("attempts") or 0) + 1 if existing else 1
        first_seen = (
            existing.get("first_seen_at")
            if existing and existing.get("first_seen_at")
            else _now()
        )
        row = {
            "original_url": res["original_url"],
            "resolved_url": res.get("resolved_url"),
            "status": res["status"],
            "failure_reason": res.get("failure_reason"),
            "first_seen_at": first_seen,
            "last_attempted_at": _now(),
            "resolved_at": _now() if res["status"] == STATUS_RESOLVED else (
                existing.get("resolved_at") if existing else None
            ),
            "attempts": attempts,
            "runtime_ms": res.get("runtime_ms"),
            "resolver_version": res.get("resolver_version", RESOLVER_VERSION),
            "source_domain": res.get("source_domain"),
            "final_domain": res.get("final_domain"),
        }
        sb.table(_CACHE_TABLE).upsert(row, on_conflict="original_url").execute()
    except Exception as exc:
        logger.warning("gnews cache store skipped: %s", exc)


async def resolve_with_cache(
    sb,
    url: str,
    client: httpx.AsyncClient,
    *,
    timeout: float = 12.0,
    write_cache: bool = True,
    reuse_negative: bool = True,
) -> dict:
    """Cache-first resolve. Positive results always reused; negative
    terminal results (still_google/consent/not_wrapper/invalid) reused so
    we never hammer the same dead URL."""
    hit = cache_lookup(sb, url)
    if hit:
        st = hit.get("status")
        if st in _TERMINAL_OK and hit.get("resolved_url"):
            return {**hit, "cached": True}
        if reuse_negative and st in _TERMINAL_NEG:
            return {**hit, "cached": True}
    res = await resolve_wrapper(url, client, timeout=timeout)
    if write_cache:
        cache_store(sb, res)
    return res
