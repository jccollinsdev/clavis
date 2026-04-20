import asyncio
import json
import re
from typing import Optional
from urllib.parse import quote, urlparse

import httpx


_DATA_ATTR_RE = re.compile(
    r'data-n-a-sg=["\']([^"\']+)["\'][^>]*data-n-a-ts=["\']([^"\']+)["\']'
)
_DATA_ATTR_RE_REVERSED = re.compile(
    r'data-n-a-ts=["\']([^"\']+)["\'][^>]*data-n-a-sg=["\']([^"\']+)["\']'
)


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
    base64_str = _extract_base64_str(source_url)
    if not base64_str:
        return {"status": False, "message": "Invalid Google News URL format."}

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
        response.raise_for_status()
        parsed = json.loads(response.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed[0][2])[1]
        if interval:
            await asyncio.sleep(interval)
        if not decoded_url:
            return {"status": False, "message": "Decoded URL was empty."}
        return {"status": True, "decoded_url": decoded_url}
    except Exception as exc:
        return {"status": False, "message": str(exc)}
    finally:
        if owns_client:
            await client.aclose()


async def decode_google_news_urls(
    source_urls: list[str], *, max_concurrency: int = 4
) -> dict[str, str]:
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
