import asyncio
import time
from unittest.mock import patch

from app.pipeline.news_normalizer import normalize_news_item
from app.pipeline.relevance import _is_low_value_article
from app.pipeline.rss_ingest import (
    _attach_decoded_google_news_urls,
    _company_query_text,
)
from app.pipeline.scheduler import _refresh_company_article_evidence_quality
from app.pipeline import scheduler
from app.services.article_scraper import (
    _evaluate_candidate_body,
    _direct_publisher_candidates,
    _extract_ddg_urls,
    _strip_article_boilerplate,
    _search_queries,
    enrich_article_content,
)


def test_normalize_news_item_preserves_source_url():
    normalized = normalize_news_item(
        {
            "title": "Example headline",
            "url": "https://news.google.com/rss/articles/example",
            "source_url": "https://www.example.com",
            "source": "Example News",
        },
        "company_news",
    )

    assert normalized["source_url"] == "https://www.example.com"


def test_attach_decoded_google_news_urls_rewrites_wrapper_urls():
    articles = [
        {
            "title": "Example headline",
            "url": "https://news.google.com/rss/articles/example",
            "source_url": "https://news.google.com/rss/articles/example",
        }
    ]

    async def _run():
        with patch(
            "app.pipeline.rss_ingest.decode_google_news_urls",
            return_value={
                "https://news.google.com/rss/articles/example": "https://www.example.com/story"
            },
        ):
            return await _attach_decoded_google_news_urls(articles)

    enriched = asyncio.run(_run())

    assert enriched[0]["url"] == "https://www.example.com/story"
    assert enriched[0]["source_url"] == "https://www.example.com/story"


def test_company_query_text_uses_company_name_without_stock_suffix():
    assert _company_query_text("AAPL", "Apple Inc.") == "Apple Inc."
    assert _company_query_text("AAPL") == "AAPL"


def test_refresh_position_prices_runs_concurrently():
    class _FakeResult:
        def __init__(self, data=None):
            self.data = data or []

    class _FakeTable:
        def __init__(self, table_name: str, recorder: list):
            self.table_name = table_name
            self.recorder = recorder

        def update(self, payload):
            self.recorder.append((self.table_name, "update", payload))
            return self

        def insert(self, payload):
            self.recorder.append((self.table_name, "insert", payload))
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            return _FakeResult()

    class _FakeSupabase:
        def __init__(self, recorder: list):
            self.recorder = recorder

        def table(self, table_name: str):
            return _FakeTable(table_name, self.recorder)

    positions = [
        {"id": f"position-{i}", "ticker": ticker}
        for i, ticker in enumerate(["AAPL", "MSFT", "NVDA", "AMZN"])
    ]
    recorder: list = []

    def _fake_fetch_current_price(ticker: str):
        time.sleep(0.2)
        return float(len(ticker))

    with (
        patch(
            "app.services.supabase.get_supabase", return_value=_FakeSupabase(recorder)
        ),
        patch(
            "app.services.finnhub_prices.fetch_current_price_from_finnhub",
            side_effect=_fake_fetch_current_price,
        ),
    ):
        started = time.perf_counter()
        asyncio.run(scheduler._refresh_position_prices_from_finnhub(positions))
        elapsed = time.perf_counter() - started

    assert elapsed < 0.7
    assert (
        sum(1 for table, op, _ in recorder if table == "positions" and op == "update")
        == 4
    )
    assert (
        sum(1 for table, op, _ in recorder if table == "prices" and op == "insert") == 4
    )


def test_refresh_company_article_evidence_quality_promotes_real_body():
    article = {
        "title": "Example headline",
        "summary": "Example summary",
        "body": " ".join(["This is substantive article content."] * 30),
        "relevance": {"evidence_quality": "title_only", "relevant": True},
    }

    refreshed = _refresh_company_article_evidence_quality(article)

    assert refreshed["evidence_quality"] == "full_body"
    assert refreshed["relevance"]["evidence_quality"] == "full_body"


def test_normalize_news_item_marks_google_wrapper_as_title_only():
    normalized = normalize_news_item(
        {
            "title": "Example headline",
            "summary": '<a href="https://news.google.com/rss/articles/example">Example headline</a><font color="#6f6f6f">Example News</font>',
            "body": '<a href="https://news.google.com/rss/articles/example">Example headline</a><font color="#6f6f6f">Example News</font>',
            "source": "Example News",
        },
        "company_news",
    )

    assert normalized["evidence_quality"] == "title_only"
    assert "<a href" not in normalized["body"]


def test_normalize_news_item_marks_substantive_body_as_full_body():
    normalized = normalize_news_item(
        {
            "title": "Example headline",
            "body": " ".join(["This is substantive article content."] * 30),
            "source": "Example News",
        },
        "company_news",
    )

    assert normalized["evidence_quality"] == "full_body"


def test_search_queries_include_source_domain_and_title():
    article = {
        "title": "AbbVie strikes up to $745M pain-drug deal with China's Haisco",
        "source": "Stock Titan",
        "source_url": "https://www.stocktitan.net",
    }

    queries = _search_queries(article)

    assert queries[0].startswith("site:stocktitan.net")
    assert "AbbVie strikes up to $745M" in queries[0]


def test_strip_article_boilerplate_removes_cookie_and_nav_text():
    text = """
    We use cookies to understand how you use our site.

    Accept All

    AbbVie stock pulls ahead after strong earnings.
    Related articles
    """

    cleaned = _strip_article_boilerplate(text, "zacks.com")

    assert "cookies" not in cleaned.lower()
    assert "related articles" not in cleaned.lower()
    assert "AbbVie stock pulls ahead" in cleaned


def test_direct_publisher_candidates_probe_source_host():
    article = {
        "title": "AbbVie strikes up to $745M pain-drug deal with China's Haisco",
        "source_url": "https://www.stocktitan.net/news/abc-123-def-ghi",
        "source": "Stock Titan",
    }

    candidates = _direct_publisher_candidates(article)

    assert candidates
    exact_match = next(
        (c for c in candidates if c["query"] == "source_url_exact"), None
    )
    assert exact_match is not None
    assert exact_match["url"] == "https://www.stocktitan.net/news/abc-123-def-ghi"
    assert all(
        candidate["url"].startswith("https://stocktitan.net/")
        for candidate in candidates
    )


def test_direct_publisher_candidates_falls_back_to_host_probe_when_no_source_url():
    article = {
        "title": "AbbVie strikes up to $745M pain-drug deal",
        "source": "stocktitan.net",
        "source_url": "",
    }

    candidates = _direct_publisher_candidates(article)

    assert candidates
    assert any("/news/" in c["url"] for c in candidates)


def test_extract_ddg_urls_decodes_result_links():
    markdown = "## [Result](http://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fstory%3Fa%3D1)"

    urls = _extract_ddg_urls(markdown)

    assert urls == ["https://example.com/story?a=1"]


def test_evaluate_candidate_body_reports_failure_reason():
    article = {
        "title": "AbbVie strikes up to $745M pain-drug deal with China's Haisco",
        "source_url": "https://www.stocktitan.net",
        "source": "Stock Titan",
    }

    evaluation = _evaluate_candidate_body(
        article, "Subscribe to read more", "https://example.com/story", method="html"
    )

    assert evaluation["accepted"] is False
    assert evaluation["failure_reason"] == "insufficient_article_signal"


def test_relevance_does_not_treat_full_body_decoded_article_as_google_wrapper():
    article = {
        "title": "Battle of Big Pharma: Is AbbVie Stock Pulling Ahead of Pfizer?",
        "summary": "Yahoo Finance analysis of AbbVie and Pfizer.",
        "body": " ".join(
            ["AbbVie and Pfizer are compared across pipeline strength and valuation."]
            * 20
        ),
        "evidence_quality": "full_body",
        "url": "https://news.google.com/rss/articles/example?oc=5",
        "raw": {
            "scrape_status": "resolved_source_url_html",
            "resolved_url": "https://finance.yahoo.com/sectors/healthcare/articles/battle-big-pharma-abbvie-stock-133200889.html",
            "source_url": "https://finance.yahoo.com/sectors/healthcare/articles/battle-big-pharma-abbvie-stock-133200889.html",
            "content_source": "finance.yahoo.com",
        },
    }

    is_low_value, reason = _is_low_value_article(article)

    assert is_low_value is False
    assert reason == ""


class _FakeResponse:
    def __init__(self, text: str, url: str):
        self.text = text
        self.url = url

    def raise_for_status(self):
        return None


class _FakeClient:
    async def get(self, url):
        return _FakeResponse(
            "<html><body>Comprehensive up-to-date news coverage, aggregated from sources all over the world by Google News.</body></html>",
            url,
        )

    async def aclose(self):
        return None


class _FlakySearchClient:
    def __init__(self):
        self.calls = 0

    async def get(self, url):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary search failure")
        markdown = "## [Result](http://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fstory%3Fa%3D1)"
        return _FakeResponse(markdown, url)

    async def aclose(self):
        return None


def test_article_scraper_wrapper_fallback_has_no_unbound_error():
    article = {
        "title": "Example wrapper headline",
        "url": "https://news.google.com/rss/articles/example",
        "source": "Example News",
        "source_url": "https://www.example.com",
    }

    async def _run():
        with patch(
            "app.services.article_scraper._resolve_publisher_article",
            return_value=(None, {"failure_reason": "no_candidate_attempts"}),
        ):
            return await enrich_article_content(article, client=_FakeClient())

    enriched = asyncio.run(_run())

    assert enriched["scrape_status"] == "google_wrapper"
    assert enriched["resolution_status"] == "unresolved_wrapper"
    assert enriched["resolution_failure_reason"] == "no_candidate_attempts"


def test_search_candidate_collection_survives_one_failed_query():
    from app.services.article_scraper import _search_resolved_candidates

    article = {
        "title": "AbbVie strikes up to $745M pain-drug deal with China's Haisco",
        "source_url": "https://www.stocktitan.net",
        "source": "Stock Titan",
    }

    async def _run():
        client = _FlakySearchClient()
        candidates, debug = await _search_resolved_candidates(article, client)
        return candidates, debug

    candidates, debug = asyncio.run(_run())

    assert candidates
    assert debug["query_errors"]
    assert debug["query_errors"][0]["error"] == "temporary search failure"
