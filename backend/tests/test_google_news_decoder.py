from unittest.mock import AsyncMock, patch

from app.pipeline.rss_ingest import _attach_decoded_google_news_urls
from app.services.google_news_decoder import _extract_base64_str


def test_extract_base64_str_from_google_news_url():
    url = (
        "https://news.google.com/rss/articles/"
        "CBMiiAFBVV95cUxQOXZLdC1hSzFqQVVLWGJVZzlPaDYyNjdWTURScV9BbVp0SWhF"
        "?hl=en-US&gl=US&ceid=US:en"
    )

    assert (
        _extract_base64_str(url)
        == "CBMiiAFBVV95cUxQOXZLdC1hSzFqQVVLWGJVZzlPaDYyNjdWTURScV9BbVp0SWhF"
    )


def test_extract_base64_str_rejects_non_google_url():
    assert _extract_base64_str("https://example.com/story") is None


def test_attach_decoded_google_news_urls_rewrites_source_url():
    import asyncio

    article = {
        "url": "https://news.google.com/rss/articles/example123?oc=5",
        "source_url": "https://finance.yahoo.com",
        "publisher_homepage_url": "https://finance.yahoo.com",
        "title": "Example headline",
    }

    async def _run():
        with patch(
            "app.pipeline.rss_ingest.decode_google_news_urls",
            new=AsyncMock(
                return_value={
                    "https://news.google.com/rss/articles/example123?oc=5": (
                        "https://finance.yahoo.com/news/example-story-123.html"
                    )
                }
            ),
        ):
            return await _attach_decoded_google_news_urls([article])

    rewritten = asyncio.run(_run())

    assert (
        rewritten[0]["source_url"]
        == "https://finance.yahoo.com/news/example-story-123.html"
    )
    assert rewritten[0]["publisher_homepage_url"] == "https://finance.yahoo.com"
    assert (
        rewritten[0]["decoded_google_url"]
        == "https://finance.yahoo.com/news/example-story-123.html"
    )
