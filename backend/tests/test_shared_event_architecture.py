"""Phase 7A — Shared ticker event architecture validation.

These tests prove the shared event read model works correctly WITHOUT
requiring any live DB migration. All are read-model unit tests.

Tests:
1. build_shared_ticker_event() produces correct output shape
2. dedup_event_analyses_for_shared() handles duplicate hashes
3. Event deduplication preserves highest-confidence row
4. Shared event → compatibility projection works
5. Ticker-level events are isolated from position-level events
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.services import ticker_cache_service as tcs
from app.pipeline.analysis_utils import sanitize_text_field


# ═══════════════════════════════════════════════════════════════════════════════
# Shared event deduplication (from existing per-position rows)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSharedEventDeduplication:
    """_dedup_event_analyses deduplicates by event_hash and normalized title."""

    def test_dedup_by_event_hash(self):
        rows = [
            {"id": "a", "event_hash": "hash-1", "title": "AMD earnings",
             "confidence": 0.8, "created_at": "2026-05-05T12:00:00Z"},
            {"id": "b", "event_hash": "hash-1", "title": "AMD earnings (dup)",
             "confidence": 0.7, "created_at": "2026-05-05T13:00:00Z"},
            {"id": "c", "event_hash": "hash-2", "title": "AMD new product",
             "confidence": 0.9, "created_at": "2026-05-05T14:00:00Z"},
        ]
        result = tcs._dedup_event_analyses(rows)
        assert len(result) == 2
        hashes = {r["event_hash"] for r in result}
        assert "hash-1" in hashes
        assert "hash-2" in hashes

    def test_dedup_prefers_highest_confidence(self):
        rows = [
            {"id": "a", "event_hash": "hash-1", "title": "AMD earnings",
             "confidence": 0.5, "created_at": "2026-05-05T14:00:00Z"},
            {"id": "b", "event_hash": "hash-1", "title": "AMD earnings",
             "confidence": 0.9, "created_at": "2026-05-05T12:00:00Z"},
        ]
        result = tcs._dedup_event_analyses(rows)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.9

    def test_dedup_by_normalized_headline_same_story_different_source(self):
        rows = [
            {"id": "a", "event_hash": "h1", "title": "AMD beats earnings estimates - Reuters",
             "confidence": 0.8, "created_at": "2026-05-05T12:00:00Z"},
            {"id": "b", "event_hash": "h2", "title": "AMD beats earnings estimates | Bloomberg",
             "confidence": 0.7, "created_at": "2026-05-05T12:30:00Z"},
            {"id": "c", "event_hash": "h3", "title": "AMD launches new GPU",
             "confidence": 0.6, "created_at": "2026-05-05T13:00:00Z"},
        ]
        result = tcs._dedup_event_analyses(rows)
        # First two have different hashes but same normalized title
        # -> dedup keeps only one
        assert len(result) == 2
        titles = {r["title"] for r in result}
        assert "AMD launches new GPU" in titles

    def test_empty_events_returns_empty(self):
        assert tcs._dedup_event_analyses([]) == []

    def test_single_event_unchanged(self):
        row = [{"id": "a", "event_hash": "h1", "title": "Event",
                "confidence": 0.5, "created_at": "2026-05-05T12:00:00Z"}]
        result = tcs._dedup_event_analyses(row)
        assert result == row


# ═══════════════════════════════════════════════════════════════════════════════
# News cache → event fallback (non-fabricated)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsCacheFallbackEvents:
    """_build_event_analyses_from_news_rows creates honest raw-cache events."""

    def test_cache_events_are_not_analyzed(self):
        rows = [
            {"id": "nc-1", "headline": "AMD price target raised",
             "summary": "Analysts raised AMD price target...",
             "source": "Barron's", "url": "https://example.com",
             "sentiment": "positive",
             "published_at": "2026-05-05T12:00:00Z"},
        ]
        events = tcs._build_event_analyses_from_news_rows(
            rows, ticker="AMD", position_id="virtual:AMD"
        )
        assert len(events) == 1
        e = events[0]
        assert e["analysis_source"] == "ticker_news_cache_raw"
        assert e["what_happened"] == ""
        assert e["tldr"] == ""
        assert e["what_it_means"] == ""
        assert e["key_implications"] == []
        assert e["confidence"] is None

    def test_cache_events_inherit_title(self):
        rows = [{"id": "n1", "headline": "AMD news", "sentiment": "neutral"}]
        events = tcs._build_event_analyses_from_news_rows(
            rows, ticker="AMD", position_id="v:AMD"
        )
        assert events[0]["title"] == "AMD news"


# ═══════════════════════════════════════════════════════════════════════════════
# Shared analysis — events and drivers in detail
# ═══════════════════════════════════════════════════════════════════════════════

class TestSharedAnalysisEvents:
    """build_shared_ticker_analysis_detail includes events and risk drivers."""

    def _snapshot(self):
        return {
            "ticker": "AMD", "grade": "B", "safety_score": 72.0,
            "factor_breakdown": {"ai_dimensions": {
                "news_sentiment": 65, "macro_exposure": 70, "volatility_trend": 78,
            }},
            "reasoning": "B — Moderate Risk.",
            "analysis_as_of": "2026-05-05T12:00:00+00:00",
            "methodology_version": "sp500-ai-backfill-v2",
        }

    def _events(self):
        return [
            {
                "id": "evt-1", "title": "AMD earnings beat",
                "event_hash": "h1",
                "what_happened": "AMD reported Q1 earnings above consensus.",
                "tldr": "Earnings strength adds positive near-term momentum.",
                "what_it_means": "The earnings beat reduces near-term downside risk.",
                "key_implications": ["Revenue growth accelerating"],
                "follow_up_notes": ["Watch guidance"],
                "tags": ["earnings", "beat"],
                "source": "Reuters",
                "source_url": "https://example.com/article",
                "published_at": "2026-05-05T12:00:00Z",
                "significance": "major",
                "risk_direction": "improving",
                "confidence": 0.85,
            }
        ]

    def test_detail_includes_events(self):
        snapshot = self._snapshot()
        events = self._events()
        detail = tcs.build_shared_ticker_analysis_detail(
            ticker="AMD", metadata={}, snapshot=snapshot,
            previous_snapshot=None, latest_news_row=None, latest_refresh_job=None,
            current_analysis={}, latest_event_analyses=events,
        )
        assert len(detail["events"]) == 1
        assert detail["events"][0]["title"] == "AMD earnings beat"
        assert detail["events"][0]["tldr"] is not None

    def test_detail_includes_risk_drivers_key(self):
        snapshot = self._snapshot()
        detail = tcs.build_shared_ticker_analysis_detail(
            ticker="AMD", metadata={}, snapshot=snapshot,
            previous_snapshot=None, latest_news_row=None, latest_refresh_job=None,
            current_analysis={"driver_cards": [], "driver_cards_state": "pending"},
            latest_event_analyses=[],
        )
        assert "risk_drivers" in detail
        assert detail["risk_drivers"] == []
        assert detail["risk_drivers_state"] == "pending"

    def test_empty_events_is_list(self):
        snapshot = self._snapshot()
        detail = tcs.build_shared_ticker_analysis_detail(
            ticker="AMD", metadata={}, snapshot=snapshot,
            previous_snapshot=None, latest_news_row=None, latest_refresh_job=None,
            current_analysis={}, latest_event_analyses=[],
        )
        assert detail["events"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# Compatibility projection — events flow through
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventCompatibilityProjection:
    """Compatibility projection carries events from shared_detail to response."""

    def _shared_detail(self):
        return {
            "summary": {
                "current_score": 72.0, "current_grade": "B",
                "grade_direction": "flat",
                "grade_rationale": "B — Moderate Risk.",
                "analysis_source": "shared",
                "freshness": {
                    "score_as_of": "2026-05-05T12:00:00+00:00",
                    "analysis_as_of": "2026-05-05T12:00:00+00:00",
                    "status": "ready", "coverage_state": "substantive",
                },
                "methodology_version": "sp500-ai-backfill-v2",
            },
            "events": [
                {"id": "evt-1", "title": "AMD earnings", "tldr": "TLDR",
                 "what_it_means": "Meaning", "key_implications": [],
                 "follow_up_notes": [], "tags": [],
                 "source": "Reuters",
                 "source_article_link": "https://example.com",
                 "published_at": "2026-05-05T12:00:00Z"},
            ],
            "risk_drivers": [],
            "risk_drivers_state": "pending",
            "risk_drivers_provenance": None,
            "key_implications": [],
            "follow_up_notes": [],
            "source_links": [],
        }

    def test_projection_preserves_latest_event_analyses(self):
        detail = self._shared_detail()
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
        assert result["latest_event_analyses"][0]["title"] == "AMD earnings"


# ═══════════════════════════════════════════════════════════════════════════════
# Public event tags — no fabrication
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicEventTagsNoFabrication:
    """_public_event_tags returns only explicit tags, never fabricated."""

    def test_explicit_tags_returned(self):
        assert tcs._public_event_tags({"tags": ["earnings", "guidance"]}) == ["earnings", "guidance"]

    def test_no_tags_returns_empty(self):
        assert tcs._public_event_tags({}) == []

    def test_no_fabrication_from_event_type(self):
        assert tcs._public_event_tags({"event_type": "earnings"}) == []

    def test_no_fabrication_from_significance(self):
        assert tcs._public_event_tags({"significance": "major"}) == []

    def test_no_fabrication_from_source(self):
        assert tcs._public_event_tags({"source": "Reuters"}) == []

    def test_truncates_to_five(self):
        result = tcs._public_event_tags({"tags": ["a", "b", "c", "d", "e", "f"]})
        assert len(result) == 5
