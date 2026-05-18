"""Local Playwright resolver POC (comparison arm) — read-only, no DB.

Opens each news.google.com wrapper URL in a reused headless Chromium
context, waits briefly for the redirect to a publisher URL, and records
the final non-Google URL. Does NOT interact with consent / CAPTCHA /
login / paywall walls. Low concurrency, short per-URL timeout.

Usage:
    python3 backend/scripts/gnews_playwright_poc.py <sample.json> <out.json>

<sample.json>: list of {"original_google_url","ticker","current_strict_usable"}
Emits the same list with playwright_status / playwright_resolved_url /
playwright_runtime_ms added.

Reason codes: resolved | still_google_url | consent_or_captcha | timeout |
blocked | invalid_url | error
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from urllib.parse import urlparse

CONCURRENCY = 3
PER_URL_TIMEOUT_MS = 20000


def _is_google(u: str) -> bool:
    try:
        h = urlparse(u or "").netloc.lower()
    except Exception:
        return False
    return "google.com" in h or "gstatic.com" in h


async def _resolve(context, url: str) -> dict:
    t0 = time.monotonic()
    out = {"playwright_status": "error", "playwright_resolved_url": None}
    if not url or "news.google.com" not in url:
        out["playwright_status"] = "invalid_url"
        out["playwright_runtime_ms"] = int((time.monotonic() - t0) * 1000)
        return out
    page = await context.new_page()
    try:
        try:
            await page.goto(url, wait_until="commit", timeout=PER_URL_TIMEOUT_MS)
        except Exception:
            pass
        # allow the client-side redirect to settle without interacting
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        for _ in range(6):
            final = page.url
            if final and not _is_google(final) and final.startswith("http"):
                out["playwright_status"] = "resolved"
                out["playwright_resolved_url"] = final
                break
            if "consent.google.com" in final or "/sorry/" in final:
                out["playwright_status"] = "consent_or_captcha"
                break
            await asyncio.sleep(1.0)
        else:
            final = page.url
            if _is_google(final):
                out["playwright_status"] = "still_google_url"
        if out["playwright_status"] == "error":
            body = (await page.content())[:3000].lower()
            if "captcha" in body or "unusual traffic" in body:
                out["playwright_status"] = "consent_or_captcha"
            elif "403" in body or "access denied" in body:
                out["playwright_status"] = "blocked"
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "timeout" in msg:
            out["playwright_status"] = "timeout"
        else:
            out["playwright_status"] = "error"
            out["error"] = str(exc)[:140]
    finally:
        await page.close()
    out["playwright_runtime_ms"] = int((time.monotonic() - t0) * 1000)
    return out


async def main() -> None:
    sample = json.load(open(sys.argv[1]))
    from playwright.async_api import async_playwright

    sem = asyncio.Semaphore(CONCURRENCY)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        )

        async def one(it):
            async with sem:
                r = await _resolve(context, it["original_google_url"])
            it.update(r)
            return it

        sample = await asyncio.gather(*[one(i) for i in sample])
        await context.close()
        await browser.close()

    json.dump(sample, open(sys.argv[2], "w"), default=str)
    print(f"wrote {len(sample)} -> {sys.argv[2]}")


if __name__ == "__main__":
    asyncio.run(main())
