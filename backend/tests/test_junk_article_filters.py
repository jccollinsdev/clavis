from app.pipeline.relevance import _is_low_value_article
from app.pipeline.scheduler import (
    _company_article_resolution_report,
    _load_analysis_cache,
    _top_articles_for_position,
)


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def gte(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        return _FakeResult(self._data)


class _FakeSupabase:
    def __init__(self, data):
        self._data = data

    def table(self, _name):
        return _FakeQuery(self._data)


def test_low_value_article_rejects_google_wrapper_and_recap_pages():
    wrapper = {
        "title": "AAPL Stock Quote & Chart",
        "scrape_status": "google_wrapper",
        "body": "",
    }
    recap = {
        "title": "Apple stock recap after today's move",
        "summary": "Market recap with no real catalyst.",
    }

    assert _is_low_value_article(wrapper)[0] is True
    assert _is_low_value_article(recap)[0] is True


def test_top_articles_for_position_drops_junk_articles():
    articles = [
        {
            "title": "AAPL Stock Quote & Chart",
            "scrape_status": "google_wrapper",
            "summary": "",
            "event_hash": "junk",
        },
        {
            "title": "Apple expands AI supply chain",
            "summary": "The company announced a new supplier agreement.",
            "event_hash": "real",
        },
    ]

    selected = _top_articles_for_position(articles, "AAPL")

    assert [article["event_hash"] for article in selected] == ["real"]


def test_load_analysis_cache_rejects_low_value_article_payload():
    supabase = _FakeSupabase(
        [
            {
                "payload": {
                    "relevant": True,
                    "affected_tickers": ["AAPL"],
                    "event_type": "company_specific",
                    "why_it_matters": "Important catalyst.",
                }
            }
        ]
    )
    article = {
        "title": "AAPL Stock Quote & Chart",
        "scrape_status": "google_wrapper",
        "body": "",
    }

    cached = _load_analysis_cache(
        supabase,
        kind="relevance",
        cache_key="abc123",
        max_age_hours=72,
        article=article,
    )

    assert cached is None


def test_load_analysis_cache_rejects_legacy_company_news_cache_for_enriched_body():
    supabase = _FakeSupabase(
        [
            {
                "payload": {
                    "relevant": False,
                    "affected_tickers": [],
                    "event_type": "irrelevant",
                    "why_it_matters": "Old wrapper-era decision.",
                }
            }
        ]
    )
    article = {
        "title": "AbbVie strikes up to $745M pain-drug deal with China's Haisco",
        "source_type": "company_news",
        "body": "AbbVie and IGI announced an exclusive licensing agreement for ISB 2001.",
        "scrape_status": "ok_proxy",
    }

    cached = _load_analysis_cache(
        supabase,
        kind="relevance",
        cache_key="abc123",
        max_age_hours=72,
        article=article,
    )

    assert cached is None


def test_company_article_resolution_report_summarizes_coverage():
    company_articles = [
        {"ticker": "ABBV", "title": "AbbVie one"},
        {"ticker": "ABBV", "title": "AbbVie two"},
        {"ticker": "ABT", "title": "Abbott three"},
    ]
    enriched_articles = [
        {
            "ticker": "ABBV",
            "title": "AbbVie one",
            "body": "Real article body",
            "scrape_status": "resolved_search",
        },
        {
            "ticker": "ABBV",
            "title": "AbbVie two",
            "body": "",
            "scrape_status": "google_wrapper",
        },
        {
            "ticker": "ABT",
            "title": "Abbott three",
            "body": "",
            "scrape_status": "error:timeout",
        },
    ]

    report = _company_article_resolution_report(company_articles, enriched_articles)

    assert report["input_count"] == 3
    assert report["resolved_with_body"] == 1
    assert report["wrapper_only"] == 2
    assert report["error_count"] == 1
    assert report["status_counts"]["resolved_search"] == 1
    assert report["by_ticker"]["ABBV"]["resolved_with_body"] == 1
    assert report["by_ticker"]["ABT"]["error_count"] == 1
