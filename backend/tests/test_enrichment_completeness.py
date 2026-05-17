"""Tests for enrichment completeness validation and domain classification."""
import pytest
from app.services.news_enrichment import (
    is_paywalled_domain,
    is_blocked_domain,
    validate_enrichment_completeness,
)


# --- Paywall domain tests ---

def test_wsj_is_paywalled():
    assert is_paywalled_domain("https://www.wsj.com/articles/abc") is True


def test_bloomberg_is_paywalled():
    assert is_paywalled_domain("https://bloomberg.com/news/abc") is True


def test_nytimes_is_paywalled():
    assert is_paywalled_domain("https://nytimes.com/2026/abc") is True


def test_ft_is_paywalled():
    assert is_paywalled_domain("https://ft.com/content/abc") is True


def test_benzinga_is_not_paywalled():
    assert is_paywalled_domain("https://benzinga.com/article") is False


def test_cnbc_is_not_paywalled():
    assert is_paywalled_domain("https://cnbc.com/article") is False


# --- Blocked domain tests ---

def test_reuters_is_blocked():
    assert is_blocked_domain("https://reuters.com/business/abc") is True


def test_msn_is_blocked():
    assert is_blocked_domain("https://msn.com/en-us/money/abc") is True


def test_britannica_is_blocked():
    assert is_blocked_domain("https://britannica.com/topic/apple-company") is True


def test_benzinga_not_blocked():
    assert is_blocked_domain("https://benzinga.com/article") is False


def test_cnbc_not_blocked():
    assert is_blocked_domain("https://cnbc.com/article") is False


# --- Enrichment completeness ---

def test_complete_article_passes():
    article = {
        "sentiment_score": 65,
        "sentiment_reason": "Positive earnings beat expectations.",
        "body": "AMD reported strong quarterly earnings that exceeded analyst expectations. " * 5,
        "tldr": "AMD posted Q1 2026 results above consensus.",
        "what_it_means": "Positive for AMD stock near-term on strong demand signals.",
        "key_implications": ["Beat revenue by 8%", "GPU margins expanded", "Guidance raised"],
    }
    ok, missing = validate_enrichment_completeness(article)
    assert ok, f"Expected complete, missing: {missing}"
    assert len(missing) == 0


def test_missing_sentiment_score_fails():
    article = {
        "sentiment_score": None,
        "sentiment_reason": "Positive.",
        "body": "Short body.",
    }
    ok, missing = validate_enrichment_completeness(article)
    assert not ok
    assert "missing_sentiment_score" in missing


def test_missing_sentiment_reason_fails():
    article = {
        "sentiment_score": 60,
        "sentiment_reason": "",
        "body": "Short body.",
    }
    ok, missing = validate_enrichment_completeness(article)
    assert not ok
    assert "missing_sentiment_reason" in missing


def test_short_body_article_does_not_require_tldr():
    # Short body → headline-only scoring path → tldr not required
    article = {
        "sentiment_score": 55,
        "sentiment_reason": "Neutral balance of positive and negative factors.",
        "body": "[No body extracted] AMD quarterly results headline",
        "tldr": None,
        "what_it_means": None,
    }
    ok, missing = validate_enrichment_completeness(article)
    assert ok, f"Short body should not require tldr, missing: {missing}"


def test_long_body_article_requires_tldr():
    long_body = "AMD reported strong quarterly earnings. " * 10
    article = {
        "sentiment_score": 70,
        "sentiment_reason": "Beat earnings expectations.",
        "body": long_body,
        "tldr": None,
        "what_it_means": None,
    }
    ok, missing = validate_enrichment_completeness(article)
    assert not ok
    assert "missing_tldr" in missing or "missing_what_it_means" in missing


def test_paywalled_body_does_not_require_tldr():
    article = {
        "sentiment_score": 50,
        "sentiment_reason": "Paywalled content, limited signal.",
        "body": "[Paywalled] Apple AI strategy article headline",
        "tldr": None,
    }
    ok, missing = validate_enrichment_completeness(article)
    assert ok, f"Paywalled article should not require tldr, missing: {missing}"


def test_article_with_full_enrichment_is_usable():
    long_body = "Nvidia reported record datacenter revenue for Q1 2026. " * 8
    article = {
        "sentiment_score": 80,
        "sentiment_reason": "Record datacenter revenue is highly positive for NVDA.",
        "body": long_body,
        "tldr": "Nvidia beat Q1 expectations on datacenter strength.",
        "what_it_means": "Strong demand signals support continued growth.",
        "key_implications": [
            "Datacenter revenue up 427% YoY",
            "Blackwell architecture seeing strong adoption",
        ],
    }
    ok, missing = validate_enrichment_completeness(article)
    assert ok
    assert len(missing) == 0


def test_blocked_body_does_not_require_tldr():
    article = {
        "sentiment_score": 45,
        "sentiment_reason": "Headline suggests modest concern about JPM loan losses.",
        "body": "[Blocked] JPM reports mixed Q1 results",
        "tldr": None,
    }
    ok, missing = validate_enrichment_completeness(article)
    assert ok, f"Blocked article should not require tldr, missing: {missing}"
