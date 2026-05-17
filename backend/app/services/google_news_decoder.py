"""Google News URL decoder with circuit breaker, cache, and decode budget.

Decodes Google News wrapper URLs (news.google.com/articles/...) into
real publisher URLs. Includes:
- In-process decode cache (url → decoded_url) to avoid re-decoding
- Circuit breaker: after _CIRCUIT_OPEN_THRESHOLD 429s, stops all decodes
  until _CIRCUIT_RESET_SECONDS have elapsed
- Per-run budget: stops decoding after _DEFAULT_DECODE_BUDGET per call to
  decode_google_news_urls_budgeted
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Optional
from urllib.parse import quote, urlparse

import httpx

_DATA_ATTR_RE = re.compile(
    r'data-n-a-sg=["\']([^"\']+)["\'][^>]*data-n-a-ts=["\']([^"\']+)["\']'
)
_DATA_ATTR_RE_REVERSED = re.compile(
    r'data-n-a-ts=["\']([^"\']+)["\'][^>]*data-n-a-sg=["\']([^"\']+)["\']'
)

# --- Circuit breaker state (module-level, process-scoped) ---
_circuit_open_until: float = 0.0        # epoch seconds; 0 = closed
_circuit_429_count: int = 0             # 429s since last reset
_CIRCUIT_OPEN_THRESHOLD = 3             # open circuit after this many 429s
_CIRCUIT_RESET_SECONDS = 300            # 5 minutes before allowing retries

# --- Decode cache (module-level, process-scoped) ---
_decode_cache: dict[str, str] = {}      # google_url → decoded_url
_failure_cache: dict[str, float] = {}   # google_url → timestamp of failure
_FAILURE_CACHE_TTL = 600.0              # don't retry failed decode for 10 min

# --- Metrics (reset per process lifetime) ---
_metrics: dict[str, int] = {
    "discovered": 0,
    "cache_hits": 0,
    "skipped_circuit_open": 0,
    "skipped_failure_cache": 0,
    "attempted": 0,
    "success": 0,
    "rate_limited_429": 0,
    "other_failure": 0,
}


def get_decode_metrics() -> dict[str, int]:
    return dict(_metrics)


def reset_decode_metrics() -> None:
    for k in _metrics:
        _metrics[k] = 0


def _circuit_is_open() -> bool:
    return time.monotonic() < _circuit_open_until


def _record_429() -> None:
    global _circuit_open_until, _circuit_429_count
    _circuit_429_count += 1
    _metrics["rate_limited_429"] += 1
    if _circuit_429_count >= _CIRCUIT_OPEN_THRESHOLD:
        _circuit_open_until = time.monotonic() + _CIRCUIT_RESET_SECONDS
        _circuit_429_count = 0


def _record_success(google_url: str, decoded_url: str) -> None:
    global _circuit_429_count
    _circuit_429_count = max(0, _circuit_429_count - 1)  # decay on success
    _decode_cache[google_url] = decoded_url
    _metrics["success"] += 1


def _extract_base64_str(source_url: str) -> str | None:
    parsed = urlparse(str(source_url or "").strip())
    parts = parsed.path.split("/")
    if (
        parsed.hostname == "news.google.com"
        and len(parts) > 1
        and parts[-2] in {"articles", "read"}
    ):
        return parts[-1]
    return None


def _extract_decoding_params(html: str) -> tuple[str, str] | tuple[None, None]:
    match = _DATA_ATTR_RE.search(html or "")
    if match:
        return match.group(1), match.group(2)

    reversed_match = _DATA_ATTR_RE_REVERSED.search(html or "")
    if reversed_match:
        return reversed_match.group(2), reversed_match.group(1)

    return None, None


async def _get_decoding_params(
    base64_str: str, client: httpx.AsyncClient
) -> tuple[str, str]:
    errors: list[str] = []
    for url in (
        f"https://news.google.com/articles/{base64_str}",
        f"https://news.google.com/rss/articles/{base64_str}",
    ):
        try:
            response = await client.get(url)
            response.raise_for_status()
            signature, timestamp = _extract_decoding_params(response.text)
            if signature and timestamp:
                return signature, timestamp
            errors.append(f"missing decoding attrs from {url}")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("; ".join(errors) or "failed to fetch decoding params")


async def decode_google_news_url(
    source_url: str,
    *,
    client: httpx.AsyncClient | None = None,
    interval: Optional[float] = None,
) -> dict:
    """Decode a single Google News wrapper URL into a real publisher URL.

    Uses circuit breaker and failure cache. Returns dict with:
      {"status": True, "decoded_url": "..."}  on success
      {"status": False, "message": "..."}      on failure
      {"status": False, "message": "circuit_open"}  when circuit is open
    """
    _metrics["discovered"] += 1

    base64_str = _extract_base64_str(source_url)
    if not base64_str:
        return {"status": False, "message": "Invalid Google News URL format."}

    # Cache hit
    if source_url in _decode_cache:
        _metrics["cache_hits"] += 1
        return {"status": True, "decoded_url": _decode_cache[source_url], "cache_hit": True}

    # Failure cache
    failure_ts = _failure_cache.get(source_url, 0.0)
    if failure_ts and time.monotonic() - failure_ts < _FAILURE_CACHE_TTL:
        _metrics["skipped_failure_cache"] += 1
        return {"status": False, "message": "recent_failure_cached"}

    # Circuit breaker
    if _circuit_is_open():
        _metrics["skipped_circuit_open"] += 1
        return {"status": False, "message": "circuit_open"}

    _metrics["attempted"] += 1
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(follow_redirects=True, timeout=20.0)

    assert client is not None

    try:
        signature, timestamp = await _get_decoding_params(base64_str, client)
        payload = [
            "Fbv4je",
            f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{base64_str}",{timestamp},"{signature}"]',
        ]
        response = await client.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/129.0.0.0 Safari/537.36"
                ),
            },
            data=f"f.req={quote(json.dumps([[payload]]))}",
        )
        if response.status_code == 429:
            _record_429()
            _failure_cache[source_url] = time.monotonic()
            return {"status": False, "message": "rate_limited_429"}

        response.raise_for_status()
        parsed = json.loads(response.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed[0][2])[1]
        if interval:
            await asyncio.sleep(interval)
        if not decoded_url:
            _failure_cache[source_url] = time.monotonic()
            _metrics["other_failure"] += 1
            return {"status": False, "message": "Decoded URL was empty."}

        _record_success(source_url, decoded_url)
        return {"status": True, "decoded_url": decoded_url}

    except Exception as exc:
        _failure_cache[source_url] = time.monotonic()
        _metrics["other_failure"] += 1
        return {"status": False, "message": str(exc)}
    finally:
        if owns_client:
            await client.aclose()


async def decode_google_news_urls(
    source_urls: list[str], *, max_concurrency: int = 4
) -> dict[str, str]:
    """Decode a batch of Google News URLs. Returns {google_url: decoded_url}."""
    unique_urls = [
        url for url in dict.fromkeys(source_urls) if _extract_base64_str(url)
    ]
    if not unique_urls:
        return {}

    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    results: dict[str, str] = {}

    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:

        async def _decode(url: str) -> None:
            async with semaphore:
                decoded = await decode_google_news_url(url, client=client)
                if decoded.get("status") and decoded.get("decoded_url"):
                    results[url] = str(decoded["decoded_url"])

        await asyncio.gather(*(_decode(url) for url in unique_urls))

    return results


async def decode_google_news_urls_budgeted(
    source_urls: list[str],
    *,
    max_concurrency: int = 4,
    budget: int = 20,
    should_decode_fn=None,
) -> dict[str, str]:
    """Decode Google News URLs with a per-call decode budget.

    Args:
        source_urls: Google News wrapper URLs to decode.
        max_concurrency: Max concurrent decode requests.
        budget: Max number of live decode requests to attempt (cache hits don't count).
        should_decode_fn: Optional callable(url) → bool to skip URLs before decode.
            Useful for candidate_ranker.should_decode_google_wrapper filtering.

    Returns:
        {google_url: decoded_url} for successfully decoded URLs.
    """
    unique_urls = list(dict.fromkeys(source_urls))
    if not unique_urls:
        return {}

    results: dict[str, str] = {}
    budget_used = 0
    semaphore = asyncio.Semaphore(max(1, max_concurrency))

    # First pass: serve from cache (no budget consumed)
    remaining: list[str] = []
    for url in unique_urls:
        if not _extract_base64_str(url):
            continue
        if url in _decode_cache:
            results[url] = _decode_cache[url]
            _metrics["cache_hits"] += 1
        else:
            remaining.append(url)

    if not remaining or budget <= 0:
        return results

    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:

        async def _decode(url: str) -> None:
            nonlocal budget_used
            async with semaphore:
                # Skip if budget exhausted
                if budget_used >= budget:
                    return
                # Skip if circuit is open
                if _circuit_is_open():
                    _metrics["skipped_circuit_open"] += 1
                    return
                # Apply optional pre-filter
                if should_decode_fn is not None and not should_decode_fn(url):
                    return
                budget_used += 1
                decoded = await decode_google_news_url(url, client=client)
                if decoded.get("status") and decoded.get("decoded_url"):
                    results[url] = str(decoded["decoded_url"])

        await asyncio.gather(*(_decode(url) for url in remaining))

    return results
