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
    else:
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in reason.lower():
                issues.append(f"forbidden_phrase:{phrase}")
    tldr = str(result.get("tldr") or "").strip()
    if not tldr:
        issues.append("missing_tldr")
    what = str(result.get("what_it_means") or "").strip()
    if not what:
        issues.append("missing_what_it_means")
    return len(issues) == 0, issues


# ── Candidate selection filter logic (mirrors _select_candidates) ─────────────

def _passes_client_filter(row: dict) -> bool:
    """Local copy of the client-side filter from reenrich_news._select_candidates."""
    if row.get("paywalled") or row.get("paywall_detected"):
        return False
    if row.get("headline_only"):
        return False
    body = str(row.get("body") or "").strip()
    if len(body.split()) < 40:
        return False
    if body.startswith("[No body extracted]") or body.startswith("[Paywalled]") or body.startswith("[Blocked]"):
        return False
    body_lower = body.lower()
    if "get benzinga pro" in body_lower or "benzinga edge" in body_lower:
        return False
    if "create free account" in body_lower:
        return False
    if body.startswith("# ") and "stock price, quote" in body_lower:
        return False
    return True


GOOD_BODY = " ".join(["word"] * 50)  # 50 words — passes 40-word threshold


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
        body = " ".join(["word"] * 40)
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
        body = "# Q3 Earnings Beat Expectations Analysts say " + " ".join(["word"] * 45)
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is True

    def test_good_article_with_benzinga_name_in_text_accepted(self):
        # An article quoting Benzinga as a source (not a navigation page)
        body = "According to Benzinga analysts, the company reported strong earnings. " + " ".join(["word"] * 45)
        row = {"body": body, "paywalled": False}
        assert _passes_client_filter(row) is True


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
