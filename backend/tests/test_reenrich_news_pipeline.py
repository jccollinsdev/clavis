"""Tests for the re-enrichment repair pipeline.

Covers:
  1. Candidate selection filters (_select_candidates logic)
  2. skip_existing semantics — enriched rows skipped, unenriched re-processed
  3. Enrichment output validation (_validate_enrichment)
  4. enrich_and_store_articles_batch new skip_existing behavior
  5. Pipeline: extraction-success + missing sentiment = eligible for re-enrich
  6. Pipeline: fully enriched article is not re-enriched
"""
from __future__ import annotations

import asyncio
import types
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Fake supabase so imports don't fail without credentials ───────────────────
_fake_supa = types.ModuleType("supabase")
_fake_supa.create_client = lambda *a, **k: None
_fake_supa.Client = object
sys.modules.setdefault("supabase", _fake_supa)

# ── Inline the validation helper so tests work without the full import tree ────
# (mirrors _validate_enrichment from reenrich_news.py)
_FORBIDDEN_PHRASES = {
    "buy", "sell", "advise", "suggest", "predict", "forecast",
    "recommendation", "bullish outlook", "bearish call", "upside potential",
}

def _validate_enrichment(result: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []
    score = result.get("sentiment_score")
    if score is None:
        issues.append("missing_sentiment_score")
    elif not isinstance(score, (int, float)) or not (0 <= float(score) <= 100):
        issues.append(f"invalid_sentiment_score:{score}")
    reason = str(result.get("sentiment_reason") or "").strip()
    if not reason:
        issues.append("missing_sentiment_reason")
    tldr = str(result.get("tldr") or "").strip()
    if not tldr:
        issues.append("missing_tldr")
    what = str(result.get("what_it_means") or "").strip()
    if not what:
        issues.append("missing_what_it_means")
    combined = " ".join(part.lower() for part in (reason, tldr, what) if part)
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in combined:
            issues.append(f"forbidden_phrase:{phrase}")
    return len(issues) == 0, issues


# ── Candidate selection filter logic (mirrors _select_candidates) ─────────────

def _passes_client_filter(row: dict) -> bool:
    """Local copy of the client-side filter from reenrich_news._select_candidates."""
    if row.get("paywalled") or row.get("paywall_detected"):
        return False
    if row.get("headline_only"):
        return False
    body = str(row.get("body") or "").strip()
    if body.startswith("[No body extracted]") or body.startswith("[Paywalled]") or body.startswith("[Blocked]"):
        return False
    body_lower = body.lower()
    login_hits = sum(
        marker in body_lower
        for marker in ("sign in", "login", "create free account", "join pro", "join ic", "subscribe")
    )
    nav_hits = sum(
        marker in body_lower
        for marker in (
            "search quotes, news & videos",
            "livestream menu",
            "markets markets",
            "stock screener",
            "data & apis",
            "financial news financial news",
            "options etfs commodities",
            "premarket advertise contribute",
        )
    )
    sentence_like = sum(
        1
        for paragraph in body.split("\n\n")
        if len(paragraph.split()) >= 12 and any(punct in paragraph for punct in ".!?")
    )

    if "get benzinga pro" in body_lower or "benzinga edge" in body_lower:
        return False
    if login_hits >= 2 and sentence_like < 3:
        return False
    if nav_hits >= 4 and sentence_like < 3:
        return False
    if len(body.split()) < 40:
        return False
    if body.startswith("# ") and "stock price, quote" in body_lower:
        return False
    return sentence_like >= 1


GOOD_BODY = (
    "The company reported stronger quarterly revenue and margin expansion than analysts expected. "
    "Management also reaffirmed full-year guidance and cited steady demand across its largest product lines.\n\n"
    "Executives said order trends improved through the quarter, operating cash flow remained healthy, "
    "and customer retention stayed above internal targets."
)


# ══════════════════════════════════════════════════════════════════════════════
# 1 — Candidate selection
# ══════════════════════════════════════════════════════════════════════════════

class TestCandidateSelection:
    def test_valid_candidate_accepted(self):
        row = {"body": GOOD_BODY, "paywalled": False, "headline_only": False}
        assert _passes_client_filter(row) is True

    def test_paywalled_excluded(self):
        row = {"body": GOOD_BODY, "paywalled": True, "headline_only": False}
        assert _passes_client_filter(row) is False

    def test_paywall_detected_excluded(self):
        row = {"body": GOOD_BODY, "paywall_detected": True, "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_headline_only_excluded(self):
        row = {"body": GOOD_BODY, "headline_only": True, "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_body_too_short_excluded(self):
        row = {"body": "only five words here", "paywalled": False, "headline_only": False}
        assert _passes_client_filter(row) is False

    def test_body_exactly_40_words_accepted(self):
        body = (
            "The company raised guidance after posting better-than-expected first-quarter revenue and margin performance.\n\n"
            "Management said enterprise demand improved, renewal rates stayed solid, and operating cash flow remained strong throughout the quarter while backlog and customer spending both increased versus last quarter."
        )
        row = {"body": body, "paywalled": False, "headline_only": False}
        assert _passes_client_filter(row) is True

    def test_body_39_words_excluded(self):
        body = " ".join(["word"] * 39)
        row = {"body": body, "paywalled": False, "headline_only": False}
        assert _passes_client_filter(row) is False

    def test_no_body_extracted_placeholder_excluded(self):
        row = {"body": "[No body extracted] Some Headline", "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_paywalled_placeholder_excluded(self):
        row = {"body": "[Paywalled] Article Title Here", "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_blocked_placeholder_excluded(self):
        row = {"body": "[Blocked] Reuters Article", "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_null_paywalled_treated_as_false(self):
        row = {"body": GOOD_BODY, "paywalled": None, "headline_only": None}
        assert _passes_client_filter(row) is True

    # ── garbage body detection ────────────────────────────────────────────────

    def _garbage_body(self, phrase: str) -> str:
        """Build a body that has >= 40 words but embeds a garbage signal."""
        return phrase + " " + " ".join(["word"] * 45)

    def test_benzinga_navigation_get_pro_excluded(self):
        row = {"body": self._garbage_body("Get Benzinga Pro today for free"), "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_benzinga_navigation_edge_excluded(self):
        row = {"body": self._garbage_body("Benzinga Edge is the premium subscription"), "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_cnbc_login_wall_excluded(self):
        row = {"body": self._garbage_body("Create Free Account to view article"), "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_create_free_account_case_insensitive(self):
        row = {"body": self._garbage_body("CREATE FREE ACCOUNT — premium access"), "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_stock_price_page_excluded(self):
        body = "# ACME Corp (ACME) Stock Price, Quote, News & History | Benzinga " + " ".join(["word"] * 45)
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_stock_price_heading_without_stock_price_quote_accepted(self):
        # A genuine article that happens to start with # but is not a ticker page
        body = (
            "# Q3 Earnings Beat Expectations\n\n"
            "Analysts said the company posted stronger revenue growth than expected. "
            + " ".join(["word"] * 45)
            + "."
        )
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is True

    def test_good_article_with_benzinga_name_in_text_accepted(self):
        # An article quoting Benzinga as a source (not a navigation page)
        body = (
            "According to Benzinga analysts, the company reported strong earnings. "
            + " ".join(["word"] * 45)
            + "."
        )
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is True

    def test_generic_navigation_page_excluded(self):
        body = (
            "Markets Markets Livestream Menu Search quotes, news & videos Stock Screener Data & APIs "
            "Premarket Advertise Contribute Financial News Financial News Options ETFs Commodities "
            + " ".join(["word"] * 50)
        )
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_paywall_login_body_excluded(self):
        body = (
            "Sign in Subscribe Create free account Join Pro Search quotes, news & videos "
            + " ".join(["word"] * 45)
        )
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is False

    def test_real_article_body_accepted(self):
        body = (
            "The company raised full-year guidance after reporting stronger subscription revenue.\n\n"
            "Management said demand improved across enterprise and public-sector customers, and operating margins expanded versus last year.\n\n"
            "Shares moved higher after the release as investors focused on bookings growth and lower churn."
        )
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is True

    def test_body_length_alone_is_not_enough(self):
        body = "Create free account Join Pro Search quotes, news & videos " * 20
        assert len(body) >= 300
        row = {"body": body, "paywalled": False, "headline_only": False}
        assert _passes_client_filter(row) is False

    def test_garbage_body_not_selected_by_reenrichment(self):
        row = {
            "body": "Benzinga Edge Get Benzinga Pro Login Register Stock Screener Data & APIs " * 12,
            "paywalled": False,
            "headline_only": False,
        }
        assert _passes_client_filter(row) is False


# ══════════════════════════════════════════════════════════════════════════════
# 2 — skip_existing semantics
# ══════════════════════════════════════════════════════════════════════════════

class TestSkipExistingSemantics:
    """Validate that skip_existing=True now skips only ENRICHED rows."""

    def _make_batch_existing_hashes(self, existing_rows: list[dict]) -> set[str]:
        """Reproduce the new batch pre-check logic from enrich_and_store_articles_batch."""
        return {
            r["event_hash"] for r in existing_rows
            if r.get("sentiment_score") is not None
        }

    def test_enriched_row_in_existing_hashes_is_skipped(self):
        existing = [{"event_hash": "abc123", "sentiment_score": 65}]
        skippable = self._make_batch_existing_hashes(existing)
        assert "abc123" in skippable

    def test_unenriched_row_not_in_existing_hashes(self):
        existing = [{"event_hash": "def456", "sentiment_score": None}]
        skippable = self._make_batch_existing_hashes(existing)
        assert "def456" not in skippable, "Unenriched existing row must NOT be skipped"

    def test_mixed_set_only_enriched_skipped(self):
        existing = [
            {"event_hash": "enriched_hash", "sentiment_score": 72},
            {"event_hash": "unenriched_hash", "sentiment_score": None},
            {"event_hash": "also_enriched",  "sentiment_score": 50},
        ]
        skippable = self._make_batch_existing_hashes(existing)
        assert "enriched_hash"  in skippable
        assert "also_enriched"  in skippable
        assert "unenriched_hash" not in skippable

    def test_zero_sentiment_is_treated_as_enriched(self):
        # score=0 is a valid enrichment (extremely negative article)
        existing = [{"event_hash": "zero_score", "sentiment_score": 0}]
        skippable = self._make_batch_existing_hashes(existing)
        assert "zero_score" in skippable

    def test_empty_existing_rows_nothing_skipped(self):
        skippable = self._make_batch_existing_hashes([])
        assert skippable == set()

    def test_per_article_skip_only_if_sentiment_not_null(self):
        # Simulate the per-article check: only return early if sentiment_score is not None
        def _should_skip(row: dict | None) -> bool:
            if row is None:
                return False
            return row.get("sentiment_score") is not None

        assert _should_skip({"id": "x", "sentiment_score": 55}) is True
        assert _should_skip({"id": "y", "sentiment_score": None}) is False
        assert _should_skip(None) is False


# ══════════════════════════════════════════════════════════════════════════════
# 3 — Enrichment output validation
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateEnrichment:
    def _good(self) -> dict:
        return {
            "sentiment_score": 65,
            "sentiment_reason": "Company reported strong quarterly earnings.",
            "tldr": "ACME beat Q1 estimates by 12%.",
            "what_it_means": "Positive signal for near-term stock performance.",
        }

    def test_complete_enrichment_passes(self):
        ok, issues = _validate_enrichment(self._good())
        assert ok is True
        assert issues == []

    def test_missing_sentiment_score_fails(self):
        d = self._good()
        d["sentiment_score"] = None
        ok, issues = _validate_enrichment(d)
        assert ok is False
        assert "missing_sentiment_score" in issues

    def test_out_of_range_score_fails(self):
        d = self._good()
        d["sentiment_score"] = 150
        ok, issues = _validate_enrichment(d)
        assert ok is False
        assert any("invalid_sentiment_score" in i for i in issues)

    def test_negative_score_fails(self):
        d = self._good()
        d["sentiment_score"] = -1
        ok, issues = _validate_enrichment(d)
        assert ok is False

    def test_score_zero_passes(self):
        d = self._good()
        d["sentiment_score"] = 0
        ok, issues = _validate_enrichment(d)
        assert ok is True

    def test_score_100_passes(self):
        d = self._good()
        d["sentiment_score"] = 100
        ok, issues = _validate_enrichment(d)
        assert ok is True

    def test_missing_sentiment_reason_fails(self):
        d = self._good()
        d["sentiment_reason"] = ""
        ok, issues = _validate_enrichment(d)
        assert ok is False
        assert "missing_sentiment_reason" in issues

    def test_missing_tldr_fails(self):
        d = self._good()
        d["tldr"] = ""
        ok, issues = _validate_enrichment(d)
        assert ok is False
        assert "missing_tldr" in issues

    def test_missing_what_it_means_fails(self):
        d = self._good()
        d["what_it_means"] = None
        ok, issues = _validate_enrichment(d)
        assert ok is False
        assert "missing_what_it_means" in issues

    def test_forbidden_buy_in_reason_fails(self):
        d = self._good()
        d["sentiment_reason"] = "Investors should buy this stock now."
        ok, issues = _validate_enrichment(d)
        assert ok is False
        assert any("forbidden_phrase:buy" in i for i in issues)

    def test_forbidden_sell_in_reason_fails(self):
        d = self._good()
        d["sentiment_reason"] = "This is a clear sell signal for the stock."
        ok, issues = _validate_enrichment(d)
        assert ok is False
        assert any("forbidden_phrase:sell" in i for i in issues)

    def test_forbidden_forecast_in_reason_fails(self):
        d = self._good()
        d["sentiment_reason"] = "Analysts forecast 20% upside over next year."
        ok, issues = _validate_enrichment(d)
        assert ok is False

    def test_forbidden_recommendation_fails(self):
        d = self._good()
        d["sentiment_reason"] = "The recommendation is to hold the position."
        ok, issues = _validate_enrichment(d)
        assert ok is False

    def test_forbidden_phrase_is_case_insensitive(self):
        d = self._good()
        d["sentiment_reason"] = "Strong BUY signal from management commentary."
        ok, issues = _validate_enrichment(d)
        assert ok is False


# ══════════════════════════════════════════════════════════════════════════════
# 4 — Pipeline integration: extraction_success + no sentiment = eligible
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineEligibility:
    """Describe which DB rows should/should not reach LLM enrichment."""

    def _is_eligible(self, row: dict) -> bool:
        """Reproduce the eligibility rule from Phase 0 query + client filter."""
        if row.get("extraction_status") != "success":
            return False
        if (row.get("body_length") or 0) < 300:
            return False
        if row.get("sentiment_score") is not None:
            return False
        if row.get("rejection_reason"):
            return False
        if row.get("paywalled") or row.get("paywall_detected"):
            return False
        if row.get("headline_only"):
            return False
        body = str(row.get("body") or "")
        if len(body.split()) < 40:
            return False
        return True

    def _good_row(self) -> dict:
        return {
            "extraction_status": "success",
            "body_length": 600,
            "body": GOOD_BODY,
            "sentiment_score": None,
            "rejection_reason": None,
            "paywalled": False,
            "paywall_detected": None,
            "headline_only": False,
        }

    def test_extracted_body_no_sentiment_is_eligible(self):
        assert self._is_eligible(self._good_row()) is True

    def test_already_enriched_is_not_eligible(self):
        row = self._good_row()
        row["sentiment_score"] = 72
        assert self._is_eligible(row) is False

    def test_failed_extraction_not_eligible(self):
        row = self._good_row()
        row["extraction_status"] = "failed"
        assert self._is_eligible(row) is False

    def test_paywalled_not_eligible(self):
        row = self._good_row()
        row["paywalled"] = True
        assert self._is_eligible(row) is False

    def test_headline_only_not_eligible(self):
        row = self._good_row()
        row["headline_only"] = True
        assert self._is_eligible(row) is False

    def test_short_body_not_eligible(self):
        row = self._good_row()
        row["body"] = "short text"
        row["body_length"] = 50
        assert self._is_eligible(row) is False

    def test_rejected_article_not_eligible(self):
        row = self._good_row()
        row["rejection_reason"] = "low_quality"
        assert self._is_eligible(row) is False

    def test_body_length_below_300_not_eligible(self):
        row = self._good_row()
        row["body_length"] = 299
        assert self._is_eligible(row) is False

    def test_body_length_exactly_300_eligible(self):
        row = self._good_row()
        row["body_length"] = 300
        assert self._is_eligible(row) is True


# ══════════════════════════════════════════════════════════════════════════════
# 5 — News Sentiment stays Limited Data below 3, scores above 3
# ══════════════════════════════════════════════════════════════════════════════

class TestNewsStatusThresholds:
    """Verifier behaviour — usability thresholds must be honoured."""

    def _usable(self, articles: list[dict]) -> list[dict]:
        return [
            a for a in articles
            if a.get("extraction_status") == "success"
            and not a.get("paywalled")
            and a.get("sentiment_score") is not None
        ]

    def test_zero_usable_is_limited_data(self):
        arts = [{"extraction_status": "failed", "paywalled": False, "sentiment_score": None}]
        assert len(self._usable(arts)) == 0

    def test_two_usable_still_limited(self):
        arts = [
            {"extraction_status": "success", "paywalled": False, "sentiment_score": 60},
            {"extraction_status": "success", "paywalled": False, "sentiment_score": 40},
        ]
        assert len(self._usable(arts)) == 2  # < 3 → Limited Data

    def test_three_usable_reaches_mvp(self):
        arts = [
            {"extraction_status": "success", "paywalled": False, "sentiment_score": 55},
            {"extraction_status": "success", "paywalled": False, "sentiment_score": 70},
            {"extraction_status": "success", "paywalled": False, "sentiment_score": 45},
        ]
        assert len(self._usable(arts)) >= 3

    def test_extraction_complete_but_unenriched_does_not_count(self):
        arts = [
            # Body extracted but LLM never ran — not usable
            {"extraction_status": "success", "paywalled": False, "sentiment_score": None},
            {"extraction_status": "success", "paywalled": False, "sentiment_score": None},
            {"extraction_status": "success", "paywalled": False, "sentiment_score": None},
        ]
        assert len(self._usable(arts)) == 0, \
            "Articles with body but NULL sentiment must not count as usable"

    def test_paywalled_article_with_score_does_not_count(self):
        arts = [
            {"extraction_status": "success", "paywalled": True, "sentiment_score": 60},
        ]
        assert len(self._usable(arts)) == 0

    def test_after_reenrich_three_become_usable(self):
        # Simulate: articles had body, now have sentiment after repair
        before = [
            {"extraction_status": "success", "paywalled": False, "sentiment_score": None},
            {"extraction_status": "success", "paywalled": False, "sentiment_score": None},
            {"extraction_status": "success", "paywalled": False, "sentiment_score": None},
        ]
        assert len(self._usable(before)) == 0
        # After repair job runs
        after = [dict(a, sentiment_score=55) for a in before]
        assert len(self._usable(after)) == 3


class TestActualBodyQualityFilter:
    def test_yahoo_promo_body_rejected(self):
        from app.services.news_enrichment import assess_article_body_quality

        article = {
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "source_url": "https://finance.yahoo.com/news/example",
            "body": (
                "AI Investor Podcast Investing Personal Finance Technology Economy and Geopolitics\n\n"
                "The analyst who called NVIDIA in 2010 just named his top 10 stocks and Coinbase wasn't one of them. Get them here FREE.\n\n"
                "This post may contain links from our sponsors and affiliates, and Flywheel Publishing may receive compensation."
            ),
            "title": "Howard Lindzon on Seed Investing",
        }

        usable, reason, _ = assess_article_body_quality(article)
        assert usable is False
        assert reason in {"promo_menu_page", "ticker_mismatch", "no_usable_content"}

    def test_motley_fool_promo_body_rejected(self):
        from app.services.news_enrichment import assess_article_body_quality

        article = {
            "ticker": "INTC",
            "company_name": "Intel Corporation",
            "source_url": "https://www.fool.com/example",
            "body": (
                "Accessibility ... Help Our Services All Services Stock Advisor Epic Epic Plus Fool Portfolios.\n\n"
                "Best ETFs to Buy Best AI Stocks Best Growth Stocks Dividend Kings Best Index Funds.\n\n"
                "How to Invest How to Invest Money What to Invest In How to Invest in Stocks."
            ),
            "title": "Snapchat: Don't Rush to Buy This Social Media Stock",
        }

        usable, reason, _ = assess_article_body_quality(article)
        assert usable is False
        assert reason in {"promo_menu_page", "ticker_mismatch", "no_usable_content"}

    def test_off_topic_body_rejected(self):
        from app.services.news_enrichment import assess_article_body_quality

        article = {
            "ticker": "PCG",
            "company_name": "PG&E Corporation",
            "source_url": "https://clutchpoints.com/example",
            "body": (
                "NBA Eastern Atlantic Boston Celtics Brooklyn Nets New York Knicks Philadelphia 76ers Toronto Raptors\n\n"
                "Western Pacific Golden State Warriors Los Angeles Lakers Phoenix Suns Sacramento Kings\n\n"
                "Thunder's SGA gets top 3 PG take from Brandon Jennings after MVP win."
            ),
            "title": "Thunder’s SGA gets top 3 PG take from Brandon Jennings after MVP win",
        }

        usable, reason, _ = assess_article_body_quality(article)
        assert usable is False
        assert reason == "off_topic"

    def test_real_article_body_accepted(self):
        from app.services.news_enrichment import assess_article_body_quality

        article = {
            "ticker": "GOOG",
            "company_name": "Alphabet Inc.",
            "source_url": "https://finance.yahoo.com/news/example",
            "body": (
                "Berkshire Hathaway recorded its first quarter of portfolio decisions under new CEO Greg Abel.\n\n"
                "The company exited positions in Amazon, Visa, Mastercard, and UnitedHealth while adding exposure to Alphabet and Delta Air Lines.\n\n"
                "For shareholders, the shift toward Alphabet provides another signal about how Berkshire may be positioning its equity portfolio under new leadership."
            ),
            "title": "Berkshire Hathaway Portfolio Under Greg Abel Shifts Toward Alphabet And Delta",
        }

        usable, reason, cleaned = assess_article_body_quality(article)
        assert usable is True
        assert reason is None
        assert "Alphabet" in cleaned


class TestEnrichmentRetryPath:
    @pytest.mark.asyncio
    async def test_partial_json_retries_and_succeeds(self):
        from app.services.news_enrichment import enrich_article_with_retry

        responses = [
            {"raw_text": '{"sentiment_score": 50, "sentiment_reason": "The', "parsed": {}, "error": None},
            {"raw_text": '{"sentiment_score": 55, "sentiment_reason": "Balanced update.", "tldr": "Summary.", "what_it_means": "Implication.", "key_implications": ["One", "Two"], "impact_tag": "other"}', "parsed": {"sentiment_score": 55, "sentiment_reason": "Balanced update.", "tldr": "Summary.", "what_it_means": "Implication.", "key_implications": ["One", "Two"], "impact_tag": "other"}, "error": None},
        ]

        with patch("app.services.news_enrichment._request_llm_json_diagnostic", side_effect=responses):
            payload, diagnostics = await enrich_article_with_retry(ticker="MSFT", headline="Headline", body="Body text", company_name="Microsoft")

        assert payload is not None
        assert payload["sentiment_score"] == 55
        assert diagnostics["llm_calls"] == 2

    @pytest.mark.asyncio
    async def test_malformed_json_retries_and_succeeds(self):
        from app.services.news_enrichment import enrich_article_with_retry

        responses = [
            {"raw_text": '{sentiment_score: 60', "parsed": {}, "error": None},
            {"raw_text": '{"sentiment_score": 60, "sentiment_reason": "Solid quarter.", "tldr": "Summary.", "what_it_means": "Implication.", "key_implications": ["One"], "impact_tag": "financial-impact"}', "parsed": {"sentiment_score": 60, "sentiment_reason": "Solid quarter.", "tldr": "Summary.", "what_it_means": "Implication.", "key_implications": ["One"], "impact_tag": "financial-impact"}, "error": None},
        ]

        with patch("app.services.news_enrichment._request_llm_json_diagnostic", side_effect=responses):
            payload, diagnostics = await enrich_article_with_retry(ticker="AAPL", headline="Headline", body="Body text", company_name="Apple")

        assert payload is not None
        assert diagnostics["llm_calls"] == 2

    @pytest.mark.asyncio
    async def test_empty_json_retries_and_succeeds(self):
        from app.services.news_enrichment import enrich_article_with_retry

        responses = [
            {"raw_text": "", "parsed": {}, "error": None},
            {"raw_text": '{"sentiment_score": 48, "sentiment_reason": "Mixed outlook.", "tldr": "Summary.", "what_it_means": "Implication.", "key_implications": ["One"], "impact_tag": "macro"}', "parsed": {"sentiment_score": 48, "sentiment_reason": "Mixed outlook.", "tldr": "Summary.", "what_it_means": "Implication.", "key_implications": ["One"], "impact_tag": "macro"}, "error": None},
        ]

        with patch("app.services.news_enrichment._request_llm_json_diagnostic", side_effect=responses):
            payload, diagnostics = await enrich_article_with_retry(ticker="TSLA", headline="Headline", body="Body text", company_name="Tesla")

        assert payload is not None
        assert diagnostics["llm_calls"] == 2

    @pytest.mark.asyncio
    async def test_forbidden_phrase_retries_and_succeeds(self):
        from app.services.news_enrichment import enrich_article_with_retry

        responses = [
            {"raw_text": '{"sentiment_score": 70, "sentiment_reason": "Investors should buy the stock.", "tldr": "Buy this company.", "what_it_means": "Upside potential is strong.", "key_implications": ["Bullish outlook"], "impact_tag": "other"}', "parsed": {"sentiment_score": 70, "sentiment_reason": "Investors should buy the stock.", "tldr": "Buy this company.", "what_it_means": "Upside potential is strong.", "key_implications": ["Bullish outlook"], "impact_tag": "other"}, "error": None},
            {"raw_text": '{"sentiment_score": 70, "sentiment_reason": "The article points to stronger demand and improved margins.", "tldr": "Demand and margins improved.", "what_it_means": "The company may benefit from stronger near-term operating results.", "key_implications": ["Demand improved", "Margins expanded"], "impact_tag": "financial-impact"}', "parsed": {"sentiment_score": 70, "sentiment_reason": "The article points to stronger demand and improved margins.", "tldr": "Demand and margins improved.", "what_it_means": "The company may benefit from stronger near-term operating results.", "key_implications": ["Demand improved", "Margins expanded"], "impact_tag": "financial-impact"}, "error": None},
        ]

        with patch("app.services.news_enrichment._request_llm_json_diagnostic", side_effect=responses):
            payload, diagnostics = await enrich_article_with_retry(ticker="META", headline="Headline", body="Body text", company_name="Meta")

        assert payload is not None
        assert diagnostics["llm_calls"] == 2

    @pytest.mark.asyncio
    async def test_failed_retry_marks_clear_rejection_reason(self):
        from app.scripts.reenrich_news import _enrich_one

        class _FakeQuery:
            def __init__(self):
                self.payload = None
                self.row_id = None

            def update(self, payload):
                self.payload = payload
                return self

            def eq(self, _, row_id):
                self.row_id = row_id
                return self

            def execute(self):
                return types.SimpleNamespace(data=[])

        class _FakeSupabase:
            def __init__(self):
                self.query = _FakeQuery()

            def table(self, _):
                return self.query

        fake_supabase = _FakeSupabase()
        row = {
            "id": "row-1",
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "title": "Headline",
            "source": "Yahoo",
            "body": "The company reported revenue growth and margin expansion.\n\nInvestors focused on stronger data-center demand and improving cash flow across the quarter.",
        }

        with (
            patch("app.services.news_enrichment.assess_article_body_quality", return_value=(True, None, row["body"])),
            patch("app.services.news_enrichment.enrich_article_with_retry", new=AsyncMock(return_value=(None, {"failure_reason": "partial_json", "llm_calls": 2, "llm_429s": 0, "raw_llm_preview": '{"sentiment_score": 50'}))),
        ):
            result = await _enrich_one(fake_supabase, row, dry_run=False)

        assert result["status"] == "validation_failed"
        assert result["issues"] == ["partial_json"]
        assert fake_supabase.query.payload["rejection_reason"] == "partial_json"
        assert fake_supabase.query.payload["analysis_status"] == "enrichment_failed"

    @pytest.mark.asyncio
    async def test_successful_retry_stores_complete_enrichment(self):
        from app.scripts.reenrich_news import _enrich_one

        class _FakeQuery:
            def __init__(self):
                self.payload = None

            def update(self, payload):
                self.payload = payload
                return self

            def eq(self, *_):
                return self

            def execute(self):
                return types.SimpleNamespace(data=[])

        class _FakeSupabase:
            def __init__(self):
                self.query = _FakeQuery()

            def table(self, _):
                return self.query

        fake_supabase = _FakeSupabase()
        row = {
            "id": "row-2",
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "title": "Headline",
            "source": "Yahoo",
            "body": "Microsoft reported higher cloud revenue and operating margins.\n\nManagement also reiterated guidance and highlighted stable enterprise demand through the quarter.",
        }
        payload = {
            "sentiment_score": 64,
            "sentiment_reason": "The article shows stronger cloud demand and steady margins.",
            "tldr": "Microsoft posted higher cloud revenue and reiterated guidance.",
            "what_it_means": "The results support stable near-term operating performance for Microsoft.",
            "key_implications": ["Cloud growth improved", "Margins held steady"],
            "impact_tag": "financial-impact",
        }

        with (
            patch("app.services.news_enrichment.assess_article_body_quality", return_value=(True, None, row["body"])),
            patch("app.services.news_enrichment.enrich_article_with_retry", new=AsyncMock(return_value=(payload, {"failure_reason": None, "llm_calls": 2, "llm_429s": 0, "raw_llm_preview": '{...}'}))),
        ):
            result = await _enrich_one(fake_supabase, row, dry_run=False)

        assert result["status"] == "enriched"
        assert fake_supabase.query.payload["sentiment_score"] == 64
        assert fake_supabase.query.payload["tldr"]
        assert fake_supabase.query.payload["what_it_means"]
        assert fake_supabase.query.payload["analysis_status"] == "complete"


# ── Phase 2: strengthened truncated-JSON recovery ──────────────────────────────
class TestPartialJsonRecovery:
    """The reasoning model emits a correct object whose tail (usually inside
    key_implications) is cut off by the token limit. Recovery must salvage the
    complete leading scalar fields without fabricating content."""

    def _recover(self, raw: str):
        from app.services.news_enrichment import _recover_partial_json_object
        return _recover_partial_json_object(raw)

    def test_full_json_parses_normally(self):
        raw = ('{"sentiment_score": 55, "sentiment_reason": "Balanced report.", '
               '"tldr": "A summary.", "what_it_means": "An implication.", '
               '"key_implications": ["One", "Two"], "impact_tag": "other"}')
        obj = self._recover(raw)
        assert obj.get("sentiment_score") == 55
        assert obj.get("key_implications") == ["One", "Two"]

    def test_truncated_inside_key_implications_keeps_scalars(self):
        # Real ITW-style payload cut off mid-string inside key_implications.
        raw = ('{"sentiment_score": 55, "sentiment_reason": "Positive 4.40% CAGR '
               'growth projection but broad industry focus, not ITW-specific.", '
               '"tldr": "A research report forecasts automotive fastener market '
               'growth through 2031.", "what_it_means": "ITW participates in this '
               'market but the article gives no company-specific detail.", '
               '"key_implications": ["ITW operates in the automotive fastener '
               'market", "EV trends shift fastening demand toward battery and '
               'electronic assemblies", "Rising standards for safety, corrosion '
               'protection, and')
        obj = self._recover(raw)
        assert obj.get("sentiment_score") == 55
        assert obj.get("sentiment_reason", "").startswith("Positive 4.40% CAGR")
        assert obj.get("tldr", "").startswith("A research report")
        assert obj.get("what_it_means", "").startswith("ITW participates")

    def test_truncated_with_complete_array_items_recovers_array(self):
        raw = ('{"sentiment_score": 60, "sentiment_reason": "Solid quarter.", '
               '"tldr": "Summary.", "what_it_means": "Implication.", '
               '"key_implications": ["First complete bullet", "Second complete bullet"')
        obj = self._recover(raw)
        assert obj.get("sentiment_score") == 60
        assert obj.get("what_it_means") == "Implication."
        # the two completed array items survive when only the closer was lost
        assert obj.get("key_implications") == ["First complete bullet", "Second complete bullet"]

    def test_truncated_mid_scalar_value_keeps_earlier_pairs(self):
        raw = '{"sentiment_score": 42, "sentiment_reason": "Margins compressed because'
        obj = self._recover(raw)
        assert obj.get("sentiment_score") == 42

    def test_malformed_unrecoverable_json_fails_cleanly(self):
        assert self._recover("not json at all, just prose about the company") == {}
        assert self._recover("") == {}
        assert self._recover("```\nI cannot answer this question.\n```") == {}

    def test_recovery_never_fabricates_missing_fields(self):
        raw = '{"sentiment_score": 70, "sentiment_reason": "Strong demand growth reported'
        obj = self._recover(raw)
        # tldr / what_it_means were never present — must NOT be invented
        assert "tldr" not in obj
        assert "what_it_means" not in obj

    def test_diagnostic_recovers_truncated_first_attempt_no_retry(self):
        """A truncated-but-recoverable first response should yield a usable
        payload via recovery, without burning a retry call."""
        from app.services import news_enrichment as ne

        truncated = ('{"sentiment_score": 58, "sentiment_reason": "Demand and '
                     'margins improved this quarter.", "tldr": "The company '
                     'posted higher revenue.", "what_it_means": "Near-term '
                     'operating results look stable.", "key_implications": '
                     '["Revenue rose", "Margins held steady'  # cut off here
                     )

        def fake_chat(*args, **kwargs):
            return truncated

        with patch.object(ne, "chatcompletion_text", side_effect=fake_chat):
            out = ne._request_llm_json_diagnostic("prompt", max_tokens=2000)

        assert out["error"] is None
        assert out["parsed"].get("sentiment_score") == 58
        assert out["parsed"].get("what_it_means", "").startswith("Near-term")


class TestRetryUsesHigherMaxTokens:
    @pytest.mark.asyncio
    async def test_enrich_retry_requests_2000_max_tokens(self):
        from app.services.news_enrichment import enrich_article_with_retry

        seen_kwargs = []

        def fake_diag(prompt, *, max_tokens=700, system_prompt=None):
            seen_kwargs.append(max_tokens)
            # first call fails so a retry happens, exercising both attempts
            if len(seen_kwargs) == 1:
                return {"raw_text": "garbage", "parsed": {}, "error": None}
            return {
                "raw_text": "{}",
                "parsed": {
                    "sentiment_score": 50,
                    "sentiment_reason": "Balanced.",
                    "tldr": "Summary.",
                    "what_it_means": "Implication.",
                    "key_implications": ["One"],
                    "impact_tag": "other",
                },
                "error": None,
            }

        with patch("app.services.news_enrichment._request_llm_json_diagnostic", side_effect=fake_diag):
            payload, diagnostics = await enrich_article_with_retry(
                ticker="MSFT", headline="Headline", body="Body text", company_name="Microsoft"
            )

        assert payload is not None
        assert diagnostics["llm_calls"] == 2
        # both the first attempt and the retry must request the raised limit
        assert seen_kwargs == [2000, 2000]


# ── Phase 4: safety breakers + 429 retryability ────────────────────────────────
class _ChainSupabase:
    """Chainable no-op supabase fake (every builder method returns self)."""
    def __getattr__(self, _name):
        def _f(*a, **k):
            return self
        return _f

    def execute(self):
        return types.SimpleNamespace(data=[])


class TestLlm429StaysRetryable:
    @pytest.mark.asyncio
    async def test_429_row_not_marked_rejected_and_is_retryable(self):
        from app.scripts.reenrich_news import _enrich_one

        class _FakeQuery:
            def __init__(self):
                self.payload = None
            def update(self, payload):
                self.payload = payload
                return self
            def eq(self, *_):
                return self
            def execute(self):
                return types.SimpleNamespace(data=[])

        class _FakeSupabase:
            def __init__(self):
                self.query = _FakeQuery()
            def table(self, _):
                return self.query

        fake = _FakeSupabase()
        row = {
            "id": "row-429", "ticker": "NVDA", "company_name": "NVIDIA",
            "title": "Headline",
            "body": "Real article body with enough words to pass the usable body length and word-count gate for enrichment processing here.",
        }
        with (
            patch("app.services.news_enrichment.assess_article_body_quality", return_value=(True, None, row["body"])),
            patch("app.services.news_enrichment.enrich_article_with_retry",
                  new=AsyncMock(return_value=(None, {"failure_reason": "llm_429", "llm_calls": 2, "llm_429s": 2, "raw_llm_preview": ""}))),
        ):
            result = await _enrich_one(fake, row, dry_run=False)

        assert result["status"] == "llm_429_transient"
        assert result.get("retryable") is True
        # CRITICAL: no rejection_reason persisted → row stays selectable next run
        assert fake.query.payload is None


class TestSafetyBreakers:
    def _candidates(self, n):
        return [{"ticker": f"T{i}", "id": str(i)} for i in range(n)]

    def _result(self, status, **over):
        r = {
            "id": "x", "ticker": "T0", "source": "s", "body_length": 500,
            "status": status, "issues": [], "raw_llm_preview": "",
            "body_quality_reason": None, "llm_calls": 1, "llm_429s": 0,
            "sent_to_llm": True,
        }
        r.update(over)
        return r

    @pytest.mark.asyncio
    async def test_failure_rate_breaker_aborts_safely(self):
        from app.scripts import reenrich_news

        async def fake_enrich_one(supabase, row, dry_run=False):
            return {
                "id": row["id"], "ticker": row["ticker"], "source": "s",
                "body_length": 500, "status": "validation_failed",
                "issues": ["missing_required_field"], "raw_llm_preview": "",
                "body_quality_reason": None, "llm_calls": 1, "llm_429s": 0,
                "sent_to_llm": True,
            }

        with (
            patch.object(reenrich_news, "_select_candidates", return_value=(self._candidates(100), [])),
            patch.object(reenrich_news, "_enrich_one", side_effect=fake_enrich_one),
            patch("app.services.supabase.get_supabase", return_value=_ChainSupabase()),
        ):
            stats = await reenrich_news.run_reenrichment(
                window_days=7, batch_size=25, max_concurrency=1,
                max_failure_rate=0.6, max_429=5,
            )

        assert stats["aborted"] is True
        assert stats["abort_reason"] == "failure_rate_exceeded"
        assert stats["valid_measurement"] is True
        assert stats["batches"] == 1            # stopped after first batch
        assert stats["enriched"] == 0

    @pytest.mark.asyncio
    async def test_429_storm_breaker_aborts_and_marks_not_measured(self):
        from app.scripts import reenrich_news

        async def fake_enrich_one(supabase, row, dry_run=False):
            r = {
                "id": "x", "ticker": "T0", "source": "s", "body_length": 500,
                "status": "llm_429_transient", "issues": ["llm_429"],
                "raw_llm_preview": "", "body_quality_reason": None,
                "llm_calls": 2, "llm_429s": 2, "sent_to_llm": True,
                "retryable": True,
            }
            return r

        with (
            patch.object(reenrich_news, "_select_candidates", return_value=(self._candidates(100), [])),
            patch.object(reenrich_news, "_enrich_one", side_effect=fake_enrich_one),
            patch("app.services.supabase.get_supabase", return_value=_ChainSupabase()),
        ):
            stats = await reenrich_news.run_reenrichment(
                window_days=7, batch_size=25, max_concurrency=1,
                max_failure_rate=0.6, max_429=5,
            )

        assert stats["aborted"] is True
        assert stats["abort_reason"] == "quota_exhausted_429_storm"
        assert stats["valid_measurement"] is False
        assert stats["batches"] == 1
        # transient 429s are NOT counted as article failures
        assert stats["failed"] == 0
        assert stats["llm_429_transient"] == 25

    @pytest.mark.asyncio
    async def test_no_failed_or_transient_rows_count_as_enriched(self):
        from app.scripts import reenrich_news

        async def fake_enrich_one(supabase, row, dry_run=False):
            # alternate failed / transient — none should ever count as enriched
            idx = int(row["id"])
            status = "validation_failed" if idx % 2 == 0 else "llm_429_transient"
            return {
                "id": row["id"], "ticker": row["ticker"], "source": "s",
                "body_length": 500, "status": status,
                "issues": ["x"], "raw_llm_preview": "", "body_quality_reason": None,
                "llm_calls": 1, "llm_429s": 1 if status == "llm_429_transient" else 0,
                "sent_to_llm": True,
            }

        with (
            patch.object(reenrich_news, "_select_candidates", return_value=(self._candidates(8), [])),
            patch.object(reenrich_news, "_enrich_one", side_effect=fake_enrich_one),
            patch("app.services.supabase.get_supabase", return_value=_ChainSupabase()),
        ):
            stats = await reenrich_news.run_reenrichment(
                window_days=7, batch_size=25, max_concurrency=1,
                max_failure_rate=1.1, max_429=9999,   # disable breakers for this test
            )

        assert stats["enriched"] == 0
        assert stats["tickers_enriched"] == []


class TestSafeRewriteForbidden:
    """Deterministic, meaning-preserving rewrite of low-risk advisory wording."""

    def test_low_risk_terms_are_rewritten_and_cleared(self):
        from app.services.news_enrichment import (
            _find_forbidden_phrase,
            _safe_rewrite_forbidden,
        )

        payload = {
            "sentiment_score": 60,
            "sentiment_reason": "The data suggests improving margins.",
            "tldr": "Analyst recommendation cited a strong forecast.",
            "what_it_means": "The bullish outlook reflects demand strength.",
            "key_implications": ["A bearish call was withdrawn"],
            "impact_tag": "financial-impact",
        }
        assert _find_forbidden_phrase(payload) is not None

        rewritten, cleared = _safe_rewrite_forbidden(payload)

        assert cleared is True
        assert _find_forbidden_phrase(rewritten) is None
        # meaning preserved, wording neutralised
        assert "indicates" in rewritten["sentiment_reason"].lower()
        assert "rating observation" in rewritten["tldr"].lower()
        assert "forward-looking estimate" in rewritten["tldr"].lower()
        assert "positive outlook" in rewritten["what_it_means"].lower()
        assert "negative assessment" in rewritten["key_implications"][0].lower()
        # score and structure untouched
        assert rewritten["sentiment_score"] == 60
        assert rewritten["impact_tag"] == "financial-impact"

    def test_sentence_start_capitalization_preserved(self):
        from app.services.news_enrichment import _safe_rewrite_forbidden

        payload = {
            "sentiment_score": 50,
            "sentiment_reason": "Suggests caution on guidance.",
            "tldr": "Summary.",
            "what_it_means": "Implication.",
            "key_implications": ["One"],
            "impact_tag": "other",
        }
        rewritten, cleared = _safe_rewrite_forbidden(payload)
        assert cleared is True
        assert rewritten["sentiment_reason"].startswith("Indicates ")

    def test_buy_sell_advise_predict_are_never_rewritten(self):
        from app.services.news_enrichment import (
            _find_forbidden_phrase,
            _safe_rewrite_forbidden,
        )

        for bad in (
            "Investors should buy the stock now.",
            "Time to sell this position.",
            "We advise reducing exposure.",
            "We predict the price will double.",
            "Upside potential remains very large.",
        ):
            payload = {
                "sentiment_score": 70,
                "sentiment_reason": bad,
                "tldr": "Summary.",
                "what_it_means": "Implication.",
                "key_implications": ["One"],
                "impact_tag": "other",
            }
            rewritten, cleared = _safe_rewrite_forbidden(payload)
            assert cleared is False, f"must not auto-clear: {bad!r}"
            # original advisory wording is left intact (not silently mangled)
            assert _find_forbidden_phrase(rewritten) is not None

    def test_replacement_text_introduces_no_forbidden_substring(self):
        from app.services.news_enrichment import (
            _FORBIDDEN_PHRASES,
            _SAFE_PHRASE_REWRITES,
        )

        for _pattern, replacement in _SAFE_PHRASE_REWRITES:
            low = replacement.lower()
            for phrase in _FORBIDDEN_PHRASES:
                assert phrase not in low, (
                    f"replacement {replacement!r} reintroduces {phrase!r}"
                )


class TestForbiddenPhraseHandling:
    @pytest.mark.asyncio
    async def test_low_risk_forbidden_cleared_without_extra_llm_call(self):
        """suggests/recommendation/forecast etc. are fixed deterministically."""
        from app.services.news_enrichment import enrich_article_with_retry

        responses = [
            {
                "raw_text": "{...}",
                "parsed": {
                    "sentiment_score": 62,
                    "sentiment_reason": "The report suggests margin pressure.",
                    "tldr": "Costs rose during the quarter.",
                    "what_it_means": "The company faces near-term cost risk.",
                    "key_implications": ["Input costs increased"],
                    "impact_tag": "financial-impact",
                },
                "error": None,
            },
        ]
        with patch(
            "app.services.news_enrichment._request_llm_json_diagnostic",
            side_effect=responses,
        ):
            payload, diagnostics = await enrich_article_with_retry(
                ticker="KO", headline="H", body="Body text", company_name="Coca-Cola"
            )

        assert payload is not None
        assert diagnostics["llm_calls"] == 1  # no second call needed
        assert diagnostics["forbidden_rewritten"] is True
        assert diagnostics["failure_reason"] is None
        assert "suggest" not in payload["sentiment_reason"].lower()
        assert "indicates" in payload["sentiment_reason"].lower()

    @pytest.mark.asyncio
    async def test_hard_advice_triggers_targeted_retry_with_phrase_and_prior_json(self):
        from app.services.news_enrichment import enrich_article_with_retry

        seen_prompts: list[str] = []

        def fake_diag(prompt, *args, **kwargs):
            seen_prompts.append(prompt)
            if len(seen_prompts) == 1:
                return {
                    "raw_text": "{...}",
                    "parsed": {
                        "sentiment_score": 75,
                        "sentiment_reason": "Investors should buy this stock.",
                        "tldr": "Strong quarter reported.",
                        "what_it_means": "Results beat expectations.",
                        "key_implications": ["Revenue grew"],
                        "impact_tag": "financial-impact",
                    },
                    "error": None,
                }
            return {
                "raw_text": "{...}",
                "parsed": {
                    "sentiment_score": 75,
                    "sentiment_reason": "Results point to stronger demand.",
                    "tldr": "Strong quarter reported.",
                    "what_it_means": "Results beat expectations and lower execution risk.",
                    "key_implications": ["Revenue grew"],
                    "impact_tag": "financial-impact",
                },
                "error": None,
            }

        with patch(
            "app.services.news_enrichment._request_llm_json_diagnostic",
            side_effect=fake_diag,
        ):
            payload, diagnostics = await enrich_article_with_retry(
                ticker="NKE", headline="H", body="Body text", company_name="Nike"
            )

        assert payload is not None
        assert diagnostics["llm_calls"] == 2
        assert diagnostics["failure_reason"] is None
        # the correction prompt named the exact phrase + carried prior JSON
        assert "buy" in seen_prompts[1]
        assert "Previous JSON to fix" in seen_prompts[1]
        assert '"sentiment_score": 75' in seen_prompts[1]
        # nothing advisory survived into the stored payload
        from app.services.news_enrichment import _find_forbidden_phrase

        assert _find_forbidden_phrase(payload) is None

    @pytest.mark.asyncio
    async def test_forbidden_still_rejected_if_retry_also_forbidden(self):
        from app.services.news_enrichment import enrich_article_with_retry

        bad = {
            "sentiment_score": 80,
            "sentiment_reason": "Investors should buy now.",
            "tldr": "Sell pressure eased.",
            "what_it_means": "Time to buy the dip.",
            "key_implications": ["Sell signal cleared"],
            "impact_tag": "other",
        }
        responses = [
            {"raw_text": "{...}", "parsed": dict(bad), "error": None},
            {"raw_text": "{...}", "parsed": dict(bad), "error": None},
        ]
        with patch(
            "app.services.news_enrichment._request_llm_json_diagnostic",
            side_effect=responses,
        ):
            payload, diagnostics = await enrich_article_with_retry(
                ticker="F", headline="H", body="Body text", company_name="Ford"
            )

        assert payload is None  # nothing advisory is ever stored
        assert str(diagnostics["failure_reason"]).startswith("forbidden_phrase")
        assert diagnostics["forbidden_rewritten"] is False

    @pytest.mark.asyncio
    async def test_forbidden_validator_rule_not_weakened(self):
        """The ban itself is unchanged — buy/sell/advise/predict still caught."""
        from app.services.news_enrichment import _find_forbidden_phrase

        for word in ("buy", "sell", "advise", "predict"):
            payload = {
                "sentiment_reason": f"We {word} action here.",
                "tldr": "x",
                "what_it_means": "y",
                "key_implications": [],
            }
            assert _find_forbidden_phrase(payload) == word
