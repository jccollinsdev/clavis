"""Tests for candidate_ranker: domain policy, candidate scoring, selection logic."""
import pytest
from app.services.candidate_ranker import (
    get_domain_policy,
    score_candidate,
    rank_and_filter_candidates,
    should_decode_google_wrapper,
)


# --- Domain policy tests ---

def test_open_domain_policy():
    assert get_domain_policy("https://www.benzinga.com/article/123") == "open"
    assert get_domain_policy("https://fool.com/investing/abc") == "open"
    assert get_domain_policy("https://cnbc.com/2026/05/abc") == "open"


def test_paywalled_domain_policy():
    assert get_domain_policy("https://www.wsj.com/articles/abc") == "paywalled"
    assert get_domain_policy("https://bloomberg.com/news/abc") == "paywalled"
    assert get_domain_policy("https://ft.com/content/abc") == "paywalled"
    assert get_domain_policy("https://nytimes.com/2026/abc") == "paywalled"


def test_blocked_domain_policy():
    assert get_domain_policy("https://reuters.com/business/abc") == "blocked"
    assert get_domain_policy("https://msn.com/en-us/money/abc") == "blocked"
    assert get_domain_policy("https://britannica.com/topic/abc") == "spam"  # encyclopedia = spam


def test_low_value_domain_policy():
    assert get_domain_policy("https://marketbeat.com/stocks/NASDAQ/AMD/") == "low_value"
    assert get_domain_policy("https://chartmill.com/stock/quote/AMD") == "low_value"
    assert get_domain_policy("https://stocktitan.net/news/AMD/") == "low_value"


def test_subdomain_inherits_policy():
    # news.cnbc.com should inherit cnbc.com = open
    assert get_domain_policy("https://news.cnbc.com/article") == "open"


def test_unknown_domain_returns_sometimes():
    assert get_domain_policy("https://randomblogsite.com/article") == "sometimes"


# --- Candidate scoring tests ---

def test_open_domain_ranks_higher_than_blocked():
    open_article = {
        "url": "https://benzinga.com/article/123",
        "source_url": "https://benzinga.com",
        "title": "AMD earnings beat expectations",
    }
    blocked_article = {
        "url": "https://reuters.com/article/abc",
        "source_url": "https://reuters.com",
        "title": "AMD earnings beat expectations",
    }
    open_score, _ = score_candidate(open_article)
    blocked_score, _ = score_candidate(blocked_article)
    assert open_score > blocked_score, f"Expected open ({open_score}) > blocked ({blocked_score})"


def test_spam_title_ranks_low():
    spam_article = {
        "url": "https://example.com/article",
        "source_url": "https://example.com",
        "title": "Hedge Fund 13F Filing Shows Ownership in NVDA",
    }
    score, reason = score_candidate(spam_article)
    assert score < 20.0, f"Spam title should score low, got {score}"
    assert "spam" in reason


def test_etf_holdings_spam_ranks_low():
    article = {
        "url": "https://example.com/article",
        "source_url": "https://example.com",
        "title": "ETF Holdings Update: SPY now holds AAPL",
    }
    score, _ = score_candidate(article)
    assert score < 20.0


def test_ownership_filing_spam_ranks_low():
    article = {
        "url": "https://sec.gov/cgi-bin/browse-edgar?action=getcompany",
        "source_url": "https://sec.gov",
        "title": "Form 4: Insider Ownership Transaction",
    }
    score, _ = score_candidate(article)
    assert score < 15.0  # spam domain or spam title


def test_direct_url_ranks_above_google_wrapper():
    direct_article = {
        "url": "https://cnbc.com/2026/05/16/amd-earnings.html",
        "source_url": "https://cnbc.com",
        "title": "AMD beats earnings",
    }
    wrapper_article = {
        "url": "https://news.google.com/articles/CBMiZmh0dHBzOi8vd3d3LmNuYmMuY29t",
        "source_url": "https://cnbc.com",
        "title": "AMD beats earnings",
    }
    direct_score, _ = score_candidate(direct_article)
    wrapper_score, _ = score_candidate(wrapper_article)
    assert direct_score > wrapper_score, f"Direct ({direct_score}) should beat wrapper ({wrapper_score})"


def test_paywalled_article_not_counted_usable():
    paywalled = {
        "url": "https://wsj.com/articles/apple-ai-strategy-abc123",
        "source_url": "https://wsj.com",
        "title": "Apple AI Strategy",
    }
    score, reason = score_candidate(paywalled)
    # Paywalled should still score but significantly penalized
    assert score < 35.0, f"Paywalled should score below 35, got {score}"


def test_article_with_summary_scores_higher():
    with_summary = {
        "url": "https://benzinga.com/article/1",
        "source_url": "https://benzinga.com",
        "title": "AMD announces new GPU line",
        "summary": "AMD unveiled its new Radeon RX 9000 series graphics cards targeting high-performance gaming markets.",
    }
    without_summary = {
        "url": "https://benzinga.com/article/2",
        "source_url": "https://benzinga.com",
        "title": "AMD announces new GPU line",
    }
    s1, _ = score_candidate(with_summary)
    s2, _ = score_candidate(without_summary)
    assert s1 >= s2


# --- rank_and_filter_candidates tests ---

def test_rank_and_filter_removes_spam_candidates():
    articles = [
        {"url": "https://reuters.com/article", "source_url": "https://reuters.com", "title": "JPM Q1 earnings"},
        {"url": "https://cnbc.com/article", "source_url": "https://cnbc.com", "title": "JPM Q1 earnings"},
        {"url": "https://sec.gov/form4", "source_url": "https://sec.gov", "title": "Form 4 Filing"},
    ]
    result = rank_and_filter_candidates(articles, skip_score_below=15.0)
    urls = [a["url"] for a in result]
    assert "https://cnbc.com/article" in urls
    assert "https://sec.gov/form4" not in urls
    # reuters is blocked (score=5) so should be filtered
    assert "https://reuters.com/article" not in urls


def test_rank_orders_by_score_descending():
    articles = [
        {"url": "https://chartmill.com/stock/AMD", "source_url": "https://chartmill.com", "title": "AMD chart"},
        {"url": "https://benzinga.com/AMD-earnings", "source_url": "https://benzinga.com", "title": "AMD earnings"},
        {"url": "https://fool.com/AMD-analysis", "source_url": "https://fool.com", "title": "AMD analysis"},
    ]
    result = rank_and_filter_candidates(articles)
    # benzinga and fool (open) should rank above chartmill (low_value)
    result_domains = [a.get("domain_policy") for a in result]
    assert result_domains.index("open") < result_domains.index("low_value") or "low_value" not in result_domains


def test_rank_adds_candidate_score_field():
    articles = [
        {"url": "https://cnbc.com/article", "source_url": "https://cnbc.com", "title": "Meta earnings"},
    ]
    result = rank_and_filter_candidates(articles)
    assert len(result) == 1
    assert "candidate_score" in result[0]
    assert isinstance(result[0]["candidate_score"], float)


def test_filtered_articles_get_rejection_reason():
    articles = [
        {"url": "https://britannica.com/topic/apple", "source_url": "https://britannica.com", "title": "Apple Inc."},
    ]
    # Low threshold to see the rejection
    result = rank_and_filter_candidates(articles, skip_score_below=15.0)
    assert len(result) == 0  # britannica is spam, score=0


def test_max_candidates_respected():
    articles = [
        {"url": f"https://cnbc.com/article-{i}", "source_url": "https://cnbc.com", "title": f"News {i}"}
        for i in range(10)
    ]
    result = rank_and_filter_candidates(articles, max_candidates=3)
    assert len(result) <= 3


# --- should_decode_google_wrapper tests ---

def test_should_decode_non_wrapper_url():
    assert should_decode_google_wrapper({"url": "https://cnbc.com/article"}) is True


def test_should_not_decode_wrapper_with_blocked_source():
    # Google wrapper pointing to reuters (blocked)
    assert should_decode_google_wrapper({
        "url": "https://news.google.com/articles/CBMiaHR0cHM",
        "source_url": "https://reuters.com",
    }) is False


def test_should_not_decode_wrapper_with_paywalled_source():
    assert should_decode_google_wrapper({
        "url": "https://news.google.com/articles/CBMi12345",
        "source_url": "https://wsj.com",
    }) is False


def test_should_decode_wrapper_with_open_source():
    assert should_decode_google_wrapper({
        "url": "https://news.google.com/articles/CBMi12345",
        "source_url": "https://benzinga.com",
    }) is True


def test_should_not_decode_wrapper_with_spam_title():
    assert should_decode_google_wrapper({
        "url": "https://news.google.com/articles/CBMi12345",
        "source_url": "https://example.com",
        "title": "13F Filing Shows Ownership in AAPL",
    }) is False
