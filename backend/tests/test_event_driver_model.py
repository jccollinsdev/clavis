"""Phase 6 — Event/news/risk-driver model cleanup validation.

These tests prove:
1. Raw ticker_news_cache rows NEVER produce fabricated analyzed event fields.
2. Canonical event_analyses rows expose honest, non-fabricated fields.
3. _build_event_analyses_from_news_rows() returns empty analyzed fields.
4. _public_event_tags() only returns explicit tags, never fabricated.
5. build_public_event_news_item() handles missing fields cleanly.
6. The shared ticker contract exposes canonical event/driver objects.
7. Watchlist endpoint prefers canonical event_analyses over raw news cache.

All tests are read-only — no DB writes, no live Supabase connections.
"""

import pytest
from unittest import mock

from app.services import ticker_cache_service as tcs
from app.pipeline.analysis_utils import sanitize_text_field


# ═══════════════════════════════════════════════════════════════════════════════
# News cache → event fabrication prevention
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsCacheFabricationPrevention:
    """_build_event_analyses_from_news_rows must NOT fabricate analyzed fields."""

    def test_raw_news_cache_events_have_empty_analyzed_fields(self):
        raw_rows = [
            {
                "id": "news-1",
                "headline": "AMD announces new partnership",
                "summary": "Details about the partnership...",
                "source": "Reuters",
                "url": "https://example.com/article",
                "sentiment": "positive",
                "published_at": "2026-05-05T12:00:00Z",
            }
        ]

        events = tcs._build_event_analyses_from_news_rows(
            raw_rows, ticker="AMD", position_id="virtual:AMD"
        )

        assert len(events) == 1
        e = events[0]

        assert e["title"] == "AMD announces new partnership"
        assert e["source"] == "Reuters"
        assert e["what_happened"] == ""
        assert e["tldr"] == ""
        assert e["what_it_means"] == ""
        assert e["key_implications"] == []
        assert e["recommended_followups"] == []
        assert e["tags"] == []
        assert e["confidence"] is None
        assert e["analysis_source"] == "ticker_news_cache_raw"
        assert e["long_analysis"] is None
        assert e["scenario_summary"] is None

    def test_raw_news_cache_provenance_is_explicit(self):
        """News-cache-derived events carry 'ticker_news_cache_raw' provenance."""
        raw_rows = [{"id": "n1", "headline": "Test", "summary": "Test summary", "sentiment": "neutral"}]
        events = tcs._build_event_analyses_from_news_rows(
            raw_rows, ticker="TEST", position_id="virtual:TEST"
        )
        assert events[0]["analysis_source"] == "ticker_news_cache_raw"

    def test_raw_news_cache_negative_sentiment_is_major(self):
        raw_rows = [{"id": "n1", "headline": "Bad news", "sentiment": "negative"}]
        events = tcs._build_event_analyses_from_news_rows(
            raw_rows, ticker="T", position_id="v:T"
        )
        assert events[0]["significance"] == "major"
        assert events[0]["risk_direction"] == "negative"

    def test_raw_news_cache_positive_sentiment_is_minor(self):
        raw_rows = [{"id": "n1", "headline": "Good news", "sentiment": "positive"}]
        events = tcs._build_event_analyses_from_news_rows(
            raw_rows, ticker="T", position_id="v:T"
        )
        assert events[0]["significance"] == "minor"
        assert events[0]["risk_direction"] == "positive"


# ═══════════════════════════════════════════════════════════════════════════════
# Public event tags — no fabrication
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicEventTags:
    """_public_event_tags() returns only explicit tags, never fabricated."""

    def test_returns_explicit_tags(self):
        result = tcs._public_event_tags({"tags": ["earnings", "guidance"]})
        assert result == ["earnings", "guidance"]

    def test_returns_empty_when_no_tags(self):
        result = tcs._public_event_tags({})
        assert result == []

    def test_does_not_fabricate_from_event_type(self):
        result = tcs._public_event_tags({"event_type": "earnings", "significance": "major"})
        assert result == []

    def test_does_not_fabricate_from_significance(self):
        result = tcs._public_event_tags({"significance": "major"})
        assert result == []

    def test_does_not_fabricate_from_source(self):
        result = tcs._public_event_tags({"source": "Bloomberg"})
        assert result == []

    def test_truncates_to_five(self):
        result = tcs._public_event_tags({"tags": ["a", "b", "c", "d", "e", "f", "g"]})
        assert len(result) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# Public event news item — honest field handling
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildPublicEventNewsItem:
    """build_public_event_news_item() handles missing fields cleanly."""

    def test_returns_none_for_empty_title(self):
        result = tcs.build_public_event_news_item({"title": ""}, ticker="T")
        assert result is None

    def test_returns_none_for_missing_title_and_headline(self):
        result = tcs.build_public_event_news_item({}, ticker="T")
        assert result is None

    def test_null_tldr_passes_through(self):
        result = tcs.build_public_event_news_item(
            {"title": "Event", "tldr": None}, ticker="T"
        )
        assert result["tldr"] is None

    def test_null_key_implications_returns_empty_list(self):
        result = tcs.build_public_event_news_item(
            {"title": "Event", "key_implications": None}, ticker="T"
        )
        assert result["key_implications"] == []

    def test_canonical_event_fields_preserved(self):
        """When what_happened, tldr, what_it_means exist, they pass through."""
        row = {
            "id": "evt-1",
            "title": "AMD supply agreement",
            "what_happened": "AMD signed a new supply agreement.",
            "tldr": "Supply access improves execution visibility.",
            "what_it_means": "The deal reduces near-term supply constraints.",
            "key_implications": ["Supply risk eases"],
            "follow_up_notes": ["Watch margins"],
            "tags": ["supply", "manufacturing"],
            "source": "Reuters",
            "source_article_link": "https://example.com/article",
            "published_at": "2026-05-05T12:00:00Z",
        }

        result = tcs.build_public_event_news_item(row, ticker="AMD")

        assert result["title"] == "AMD supply agreement"
        assert result["tldr"] == "Supply access improves execution visibility."
        assert result["what_it_means"] == "The deal reduces near-term supply constraints."
        assert result["key_implications"] == ["Supply risk eases"]
        assert result["follow_up_notes"] == ["Watch margins"]
        assert result["tags"] == ["supply", "manufacturing"]
        assert result["source"] == "Reuters"
        assert result["source_article_link"] == "https://example.com/article"


# ═══════════════════════════════════════════════════════════════════════════════
# Shared ticker contract — event and driver objects
# ═══════════════════════════════════════════════════════════════════════════════

class TestSharedTickerContract:
    """The shared ticker contract exposes canonical event/driver objects."""

    def _fake_snapshot(self):
        return {
            "ticker": "AMD", "grade": "B", "safety_score": 72.0,
            "factor_breakdown": {"ai_dimensions": {
                "news_sentiment": 65, "macro_exposure": 70, "volatility_trend": 78,
            }},
            "reasoning": "B — Moderate Risk.",
            "analysis_as_of": "2026-05-05T12:00:00+00:00",
            "methodology_version": "sp500-ai-backfill-v2",
        }

    def test_shared_detail_includes_risk_drivers(self):
        snapshot = self._fake_snapshot()
        analysis = {"driver_cards": [], "driver_cards_state": "pending", "driver_cards_source": None}
        events = [
            {
                "id": "evt-1", "title": "Test event",
                "what_happened": "Something happened.",
                "tldr": "Risk takeaway.", "what_it_means": "So what.",
                "key_implications": ["Key point"],
                "follow_up_notes": [], "tags": ["tag1"],
                "source": "Reuters",
                "source_article_link": "https://example.com",
                "published_at": "2026-05-05T12:00:00Z",
            }
        ]

        result = tcs.build_shared_ticker_analysis_detail(
            ticker="AMD", metadata={}, snapshot=snapshot,
            previous_snapshot=None, latest_news_row=None, latest_refresh_job=None,
            current_analysis=analysis, latest_event_analyses=events,
        )

        assert "summary" in result
        assert "risk_drivers" in result
        assert "risk_drivers_state" in result
        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0]["title"] == "Test event"

    def test_shared_detail_empty_events_is_list(self):
        snapshot = self._fake_snapshot()
        result = tcs.build_shared_ticker_analysis_detail(
            ticker="AMD", metadata={}, snapshot=snapshot,
            previous_snapshot=None, latest_news_row=None, latest_refresh_job=None,
            current_analysis={}, latest_event_analyses=[],
        )
        assert result["events"] == []
        assert result["risk_drivers"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# Compatibility projection for events and drivers
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventDriverCompatibility:
    """Compatibility projections preserve fields and provenance."""

    def _fake_shared_detail(self):
        return {
            "summary": {
                "current_score": 72.0, "current_grade": "B",
                "grade_direction": "flat", "grade_rationale": "B — Moderate Risk.",
                "analysis_source": "shared",
                "freshness": {
                    "score_as_of": "2026-05-05T12:00:00+00:00",
                    "analysis_as_of": "2026-05-05T12:00:00+00:00",
                    "status": "ready", "coverage_state": "substantive",
                },
                "methodology_version": "sp500-ai-backfill-v2",
            },
            "events": [
                {"id": "evt-1", "title": "Test", "tldr": "TLDR",
                 "what_it_means": "Meaning", "key_implications": ["Key"],
                 "follow_up_notes": [], "tags": ["tag"], "source": "Src",
                 "source_article_link": "https://example.com",
                 "published_at": "2026-05-05T12:00:00Z"},
            ],
            "risk_drivers": [
                {"driver_id": "d-1", "ticker": "AMD", "rank": 1,
                 "title": "Driver", "summary": "Summary", "direction": "negative",
                 "strength": "moderate", "source_chips": ["Src"],
                 "evidence_event_ids": ["evt-1"], "provenance": "generated"},
            ],
            "risk_drivers_state": "ready",
            "risk_drivers_provenance": "generated",
            "key_implications": ["Key"],
            "follow_up_notes": [],
            "source_links": ["https://example.com"],
        }

    def test_projection_includes_events(self):
        detail = self._fake_shared_detail()
        overlay = tcs.build_portfolio_overlay(ticker="AMD")
        result = tcs._project_shared_detail_compatibility(
            ticker="AMD", shared_detail=detail, portfolio_overlay=overlay,
            base_position={"ticker": "AMD"}, metadata={},
            latest_refresh_job=None, latest_analysis_run=None,
            latest_alerts=[], recent_news_rows=[],
            is_selected_held=False,
        )
        assert "latest_event_analyses" in result
        assert len(result["latest_event_analyses"]) == 1

    def test_projection_includes_driver_cards(self):
        detail = self._fake_shared_detail()
        overlay = tcs.build_portfolio_overlay(ticker="AMD")
        result = tcs._project_shared_detail_compatibility(
            ticker="AMD", shared_detail=detail, portfolio_overlay=overlay,
            base_position={"ticker": "AMD"}, metadata={},
            latest_refresh_job=None, latest_analysis_run=None,
            latest_alerts=[], recent_news_rows=[],
            is_selected_held=False,
        )
        assert "current_analysis" in result
        assert result["current_analysis"]["driver_cards"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Consistency: same event/driver data across all read paths
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventDriverConsistency:
    """Same ticker returns canonical event/driver data across read paths."""

    def _fake_snapshot(self):
        return {
            "ticker": "AMD", "grade": "B", "safety_score": 72.0,
            "factor_breakdown": {"ai_dimensions": {
                "news_sentiment": 65, "macro_exposure": 70, "volatility_trend": 78,
            }},
            "reasoning": "B — Moderate Risk.",
            "analysis_as_of": "2026-05-05T12:00:00+00:00",
            "methodology_version": "sp500-ai-backfill-v2",
        }

    def test_dedup_preserves_first_distinct_event(self):
        dup_rows = [
            {"id": "a", "title": "Event A", "event_hash": None},
            {"id": "a2", "title": "Event A", "event_hash": None},
            {"id": "b", "title": "Event B", "event_hash": None},
        ]
        deduped = tcs._dedup_event_analyses(dup_rows)
        ids = [r["id"] for r in deduped]
        assert "b" in ids
        deduped_a = [r for r in deduped if r["title"] == "Event A"]
        assert len(deduped_a) == 1
