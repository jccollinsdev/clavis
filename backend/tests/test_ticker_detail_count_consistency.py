"""
Tests for the ticker detail count/rationale consistency fixes:
  1. Displayed event list matches snapshot window (not the full live cache)
  2. Fallback rationale contains no dimension-math or raw numeric factor prose
  3. Stale snapshot detection triggers a background refresh
  4. AMD/NVDA-style ticker detail does not crash
"""
import re
import sys
import types

_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

_fake_openai_module = types.ModuleType("openai")


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


_fake_openai_module.OpenAI = _FakeOpenAI
sys.modules.setdefault("openai", _fake_openai_module)

from app.services import ticker_cache_service
from app.services.ticker_cache_service import (
    _investor_coverage_note,
    _investor_fallback_reasoning,
    _is_legacy_dimension_math,
    _normalize_headline,
    _dedup_event_analyses,
    _build_article_aware_reasoning,
    build_risk_score_response,
)
from app.routes.tickers import _snapshot_is_stale


# ---------------------------------------------------------------------------
# Shared fake Supabase harness (mirrors test_ticker_detail_state.py)
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.in_filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, values):
        self.in_filters[key] = set(values)
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def ilike(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = list(self.supabase.rows.get(self.table_name, []))
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        for key, values in self.in_filters.items():
            rows = [row for row in rows if row.get(key) in values]
        return _FakeResult(rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, table_name):
        return _FakeQuery(self, table_name)


# ---------------------------------------------------------------------------
# Minimal ticker fixture factory
# ---------------------------------------------------------------------------

def _base_rows(
    ticker="AMD",
    snapshot_analysis_as_of="2026-04-25T01:00:00+00:00",
    snapshot_source_count=2,
    news_rows=None,
):
    """Return a rows dict for _FakeSupabase with configurable news cache."""
    if news_rows is None:
        news_rows = []
    return {
        "ticker_universe": [
            {
                "ticker": ticker,
                "company_name": "Advanced Micro Devices",
                "exchange": "NASDAQ",
                "sector": "Technology",
                "industry": "Semiconductors",
                "is_active": True,
            }
        ],
        "ticker_metadata": [
            {
                "ticker": ticker,
                "company_name": "Advanced Micro Devices",
                "price": 155.0,
                "price_as_of": "2026-04-25T00:00:00+00:00",
                "last_price_source": "finnhub",
            }
        ],
        "ticker_risk_snapshots": [
            {
                "id": "snap-amd-1",
                "ticker": ticker,
                "grade": "C",
                "safety_score": 44,
                "analysis_as_of": snapshot_analysis_as_of,
                "source_count": snapshot_source_count,
                "reasoning": None,
                "news_summary": None,
                "dimension_rationale": {},
            }
        ],
        "ticker_news_cache": news_rows,
        "positions": [],
        "risk_scores": [],
        "position_analyses": [],
        "analysis_runs": [],
        "ticker_refresh_jobs": [],
        "alerts": [],
        "watchlists": [],
        "watchlist_items": [],
    }


# ---------------------------------------------------------------------------
# 1. Count contradiction: snapshot.source_count=2, cache has 10 rows
# ---------------------------------------------------------------------------

def test_event_analyses_capped_to_snapshot_window(monkeypatch):
    """
    When snapshot was scored with 2 articles (analysis_as_of = T0) but the
    cache now has 10 rows (8 added after T0), the displayed event list should
    only contain the rows processed before T0.
    """
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )

    old_ts = "2026-04-25T00:30:00+00:00"  # before snapshot analysis_as_of
    new_ts = "2026-04-25T06:00:00+00:00"  # after snapshot analysis_as_of

    news_rows = [
        {
            "id": f"n{i}",
            "ticker": "AMD",
            "headline": f"AMD news {i}",
            "summary": f"Summary {i}",
            "source": "Reuters",
            "url": f"https://example.com/{i}",
            "sentiment": "neutral",
            "published_at": old_ts if i < 2 else new_ts,
            "processed_at": old_ts if i < 2 else new_ts,
        }
        for i in range(10)
    ]

    rows = _base_rows(
        snapshot_analysis_as_of="2026-04-25T01:00:00+00:00",
        snapshot_source_count=2,
        news_rows=news_rows,
    )
    supabase = _FakeSupabase(rows)

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMD")

    event_count = len(result["latest_event_analyses"])
    assert event_count == 2, (
        f"Expected 2 events (matching snapshot window), got {event_count}"
    )


def test_event_analyses_all_shown_when_no_snapshot_as_of(monkeypatch):
    """When the snapshot has no analysis_as_of timestamp, all cache rows are shown."""
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )

    news_rows = [
        {
            "id": f"n{i}",
            "ticker": "AMD",
            "headline": f"AMD news {i}",
            "summary": f"Summary {i}",
            "source": "Reuters",
            "url": f"https://example.com/{i}",
            "sentiment": "neutral",
            "published_at": "2026-04-25T06:00:00+00:00",
            "processed_at": "2026-04-25T06:00:00+00:00",
        }
        for i in range(5)
    ]

    rows = _base_rows(news_rows=news_rows)
    # Snapshot exists but analysis_as_of is unset → no window filtering
    rows["ticker_risk_snapshots"][0]["analysis_as_of"] = None
    supabase = _FakeSupabase(rows)

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMD")

    assert len(result["latest_event_analyses"]) == 5


# ---------------------------------------------------------------------------
# 2. Fallback rationale must not contain dimension-math or raw score numbers
# ---------------------------------------------------------------------------

_DIMENSION_MATH_PATTERN = re.compile(
    r"(\(\d+\))"  # "(32)" style raw dimension score
    r"|adds risk at \d+"  # old _band text
    r"|supports a safer read at \d+"
    r"|is broadly neutral at \d+"
    r"|land the score at \d+"
    r"|Company-specific news \("
    r"|Macro/sector exposure \("
    r"|Portfolio construction \("
    r"|Near-term volatility \(",
)


def test_investor_coverage_note_no_internal_terms():
    for state in ("provisional", "thin", "substantive"):
        note = _investor_coverage_note(state, 3)
        assert "analyzed event" not in note, f"Internal term in {state!r}: {note!r}"
        assert "Low-confidence coverage" not in note
        assert not _DIMENSION_MATH_PATTERN.search(note), f"Dimension math in {state!r}: {note!r}"


def test_investor_fallback_reasoning_no_internal_terms():
    for state, count in [("provisional", 0), ("thin", 2), ("substantive", 5)]:
        text = _investor_fallback_reasoning(state, count)
        assert not _DIMENSION_MATH_PATTERN.search(text), (
            f"Dimension math in {state!r} reasoning: {text!r}"
        )
        assert "substantive" not in text
        assert "thin" not in text
        assert "provisional" not in text
        assert "source_count" not in text


def test_build_risk_score_response_no_dimension_math_when_no_reasoning():
    """build_risk_score_response must not produce dimension-math when snapshot has no reasoning."""
    snapshot = {
        "id": "snap-1",
        "safety_score": 44,
        "grade": "C",
        "analysis_as_of": "2026-04-25T01:00:00+00:00",
        "source_count": 2,
        "reasoning": None,
        "factor_breakdown": {
            "ai_dimensions": {
                "news_sentiment": 32,
                "macro_exposure": 28,
                "position_sizing": 18,
                "volatility_trend": 26,
            }
        },
    }
    result = build_risk_score_response(snapshot, position_id="pos-1", include_position_sizing=False)
    reasoning = result["reasoning"] or ""
    assert not _DIMENSION_MATH_PATTERN.search(reasoning), (
        f"Dimension math leaked into reasoning: {reasoning!r}"
    )
    assert "Company-specific news (" not in reasoning
    assert "adds risk at" not in reasoning


def test_legacy_dimension_math_is_detected():
    old_text = (
        "AMD: Company-specific news (78) supports a safer read; "
        "Macro/sector exposure (32) adds risk; Near-term volatility (42) is broadly neutral. "
        "This is more of a monitor-only risk. "
        "Low-confidence coverage: only 2 analyzed event(s) were available. "
        "This summary was assembled from the final dimension scores."
    )
    assert _is_legacy_dimension_math(old_text) is True


def test_legacy_text_is_replaced_in_build_risk_score_response():
    """When a stored position score has old dimension-math reasoning, it must be replaced."""
    old_reasoning = (
        "AMD: Company-specific news (78) supports a safer read at 78; "
        "Macro/sector exposure (32) adds risk at 32. "
        "This summary was assembled from the final dimension scores."
    )
    result = build_risk_score_response(
        {"id": "snap-1", "safety_score": 60, "grade": "C",
         "analysis_as_of": "2026-04-25T01:00:00+00:00", "source_count": 2},
        position_id="pos-1",
        latest_position_score={"reasoning": old_reasoning, "safety_score": 60, "source_count": 2},
        include_position_sizing=False,
    )
    reasoning = result["reasoning"] or ""
    assert not _DIMENSION_MATH_PATTERN.search(reasoning), (
        f"Old dimension-math not replaced: {reasoning!r}"
    )
    assert "Company-specific news (" not in reasoning
    assert "adds risk at" not in reasoning


# ---------------------------------------------------------------------------
# 3. Stale snapshot detection
# ---------------------------------------------------------------------------

def test_snapshot_is_stale_when_news_much_newer():
    result = {
        "freshness": {
            "analysis_as_of": "2026-04-25T00:00:00+00:00",
            "last_news_refresh_at": "2026-04-25T08:00:00+00:00",  # 8h newer
        }
    }
    assert _snapshot_is_stale(result) is True


def test_snapshot_not_stale_when_news_slightly_newer():
    result = {
        "freshness": {
            "analysis_as_of": "2026-04-25T00:00:00+00:00",
            "last_news_refresh_at": "2026-04-25T03:00:00+00:00",  # 3h newer — below threshold
        }
    }
    assert _snapshot_is_stale(result) is False


def test_snapshot_not_stale_when_timestamps_missing():
    assert _snapshot_is_stale({}) is False
    assert _snapshot_is_stale({"freshness": {}}) is False
    assert _snapshot_is_stale({"freshness": {"analysis_as_of": None, "last_news_refresh_at": None}}) is False


# ---------------------------------------------------------------------------
# 4. AMD/NVDA ticker detail does not crash (smoke test)
# ---------------------------------------------------------------------------

def test_amd_ticker_detail_no_crash(monkeypatch):
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )
    rows = _base_rows(
        ticker="AMD",
        snapshot_analysis_as_of="2026-04-25T01:00:00+00:00",
        snapshot_source_count=2,
        news_rows=[
            {
                "id": "n1",
                "ticker": "AMD",
                "headline": "AMD launches new chip",
                "summary": "AMD details new architecture.",
                "source": "TechCrunch",
                "url": "https://example.com/amd-chip",
                "sentiment": "positive",
                "published_at": "2026-04-25T00:30:00+00:00",
                "processed_at": "2026-04-25T00:30:00+00:00",
            },
            {
                "id": "n2",
                "ticker": "AMD",
                "headline": "AMD misses revenue estimate",
                "summary": "Q1 revenue came in below expectations.",
                "source": "Reuters",
                "url": "https://example.com/amd-q1",
                "sentiment": "negative",
                "published_at": "2026-04-24T20:00:00+00:00",
                "processed_at": "2026-04-24T20:00:00+00:00",
            },
        ],
    )
    supabase = _FakeSupabase(rows)

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-amd", "AMD")

    assert result["ticker"] == "AMD"
    assert result["current_score"] is not None
    reasoning = (result["current_score"] or {}).get("reasoning") or ""
    assert not _DIMENSION_MATH_PATTERN.search(reasoning), (
        f"Dimension math leaked for AMD: {reasoning!r}"
    )


# ---------------------------------------------------------------------------
# 5. Headline normalization and event deduplication
# ---------------------------------------------------------------------------

def test_normalize_headline_strips_source_suffix():
    assert _normalize_headline("AMD launches new chip - Reuters") == "amd launches new chip"
    assert _normalize_headline("AMD Finally Found Its Edge | Seeking Alpha") == "amd finally found its edge"


def test_normalize_headline_collapses_whitespace_and_punctuation():
    result = _normalize_headline("  AMD's  Q1 Earnings: Mixed Results  ")
    assert "  " not in result
    assert "'" not in result


def test_dedup_event_analyses_removes_same_hash():
    events = [
        {"id": "a", "event_hash": "hash1", "title": "AMD up", "confidence": 0.7, "created_at": "2026-04-25T01:00:00"},
        {"id": "b", "event_hash": "hash1", "title": "AMD up", "confidence": 0.5, "created_at": "2026-04-25T00:00:00"},
        {"id": "c", "event_hash": "hash2", "title": "AMD down", "confidence": 0.6, "created_at": "2026-04-25T00:30:00"},
    ]
    result = _dedup_event_analyses(events)
    assert len(result) == 2
    ids = {e["id"] for e in result}
    # Should keep highest-confidence row for hash1
    assert "a" in ids
    assert "b" not in ids
    assert "c" in ids


def test_dedup_event_analyses_removes_same_normalized_title():
    events = [
        {"id": "a", "event_hash": "h1", "title": "AMD Q1 Earnings Beat - CNBC", "confidence": 0.8, "created_at": "2026-04-25T01:00:00"},
        {"id": "b", "event_hash": "h2", "title": "AMD Q1 Earnings Beat | Bloomberg", "confidence": 0.4, "created_at": "2026-04-25T00:00:00"},
    ]
    result = _dedup_event_analyses(events)
    # Both normalize to "amd q1 earnings beat" — only the higher-confidence one kept
    assert len(result) == 1
    assert result[0]["id"] == "a"


def test_dedup_event_analyses_preserves_distinct_events():
    events = [
        {"id": "a", "event_hash": "h1", "title": "AMD chip launch", "confidence": 0.7, "created_at": "2026-04-25T01:00:00"},
        {"id": "b", "event_hash": "h2", "title": "AMD revenue miss", "confidence": 0.6, "created_at": "2026-04-25T00:00:00"},
        {"id": "c", "event_hash": "h3", "title": "AMD partnership announced", "confidence": 0.5, "created_at": "2026-04-24T23:00:00"},
    ]
    result = _dedup_event_analyses(events)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# 6. Article-aware reasoning quality
# ---------------------------------------------------------------------------

_MOCK_EVENTS_MIXED = [
    {
        "id": "e1",
        "title": "Trefis: Why AMD Stock May Drop Soon",
        "risk_direction": "worsening",
        "significance": "major",
        "scenario_summary": "Historical volatility patterns suggest a pullback is likely.",
        "key_implications": [
            "Short-term sentiment is stretched relative to fundamentals.",
            "Watch for confirmation from updated guidance before adding exposure.",
        ],
        "confidence": 0.75,
    },
    {
        "id": "e2",
        "title": "AMD Deepens AI Collaboration with France",
        "risk_direction": "improving",
        "significance": "minor",
        "scenario_summary": "European data-center expansion signals long-term demand tailwind.",
        "key_implications": [
            "New government AI partnerships expand AMD's enterprise pipeline.",
            "Revenue impact likely 2–3 quarters out.",
        ],
        "confidence": 0.65,
    },
    {
        "id": "e3",
        "title": "Yahoo Finance: AMD Among Top AI Stocks to Watch",
        "risk_direction": "improving",
        "significance": "minor",
        "scenario_summary": "Analyst coverage supports continued AI hardware demand.",
        "key_implications": [
            "Strong AI semiconductor demand underpins near-term revenue visibility.",
        ],
        "confidence": 0.60,
    },
]

_MOCK_SCORE_AMD = {
    "source_count": 3,
    "macro_exposure": 32,
    "news_sentiment": 78,
    "volatility_trend": 42,
    "coverage_state": "substantive",
}


def test_article_aware_reasoning_contains_no_generic_fallback():
    text = _build_article_aware_reasoning(_MOCK_EVENTS_MIXED, _MOCK_SCORE_AMD, "AMD")
    assert text is not None
    assert "We're still building a full picture" not in text
    assert "Risk reflects recent news coverage and sector conditions" not in text


def test_article_aware_reasoning_references_source_count():
    text = _build_article_aware_reasoning(_MOCK_EVENTS_MIXED, _MOCK_SCORE_AMD, "AMD")
    assert "3 sources" in text


def test_article_aware_reasoning_contains_downside_and_upside():
    text = _build_article_aware_reasoning(_MOCK_EVENTS_MIXED, _MOCK_SCORE_AMD, "AMD")
    assert "Downside" in text or "downside" in text
    assert "positive" in text.lower() or "supportive" in text.lower()


def test_article_aware_reasoning_macro_elevated_when_low_score():
    text = _build_article_aware_reasoning(_MOCK_EVENTS_MIXED, _MOCK_SCORE_AMD, "AMD")
    # macro_exposure=32 → should mention elevated risk
    assert "elevated risk" in text


def test_article_aware_reasoning_no_dimension_math():
    text = _build_article_aware_reasoning(_MOCK_EVENTS_MIXED, _MOCK_SCORE_AMD, "AMD")
    assert not _DIMENSION_MATH_PATTERN.search(text), f"Dimension math in reasoning: {text!r}"


def test_article_aware_reasoning_returns_none_for_empty_events():
    result = _build_article_aware_reasoning([], _MOCK_SCORE_AMD, "AMD")
    assert result is None


def test_held_user_event_count_matches_source_count(monkeypatch):
    """
    Held user: 10 event_analyses rows (6 dupes, 4 unique) with source_count=3.
    After dedup + cap, displayed list should be 3.
    """
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )

    # Build rows with 4 unique hashes (one appears 4×, others 2× each)
    event_rows = []
    for i, (h, title, direction) in enumerate([
        ("hash-a", "AMD Chip Launch", "improving"),
        ("hash-b", "AMD Revenue Miss", "worsening"),
        ("hash-c", "AMD AI Deal Announced", "improving"),
        ("hash-d", "AMD Analyst Downgrade", "worsening"),
    ]):
        for j in range(2 if i > 0 else 4):
            event_rows.append({
                "id": f"{h}-{j}",
                "position_id": "pos-amd-1",
                "event_hash": h,
                "title": title,
                "risk_direction": direction,
                "significance": "major",
                "scenario_summary": f"Summary for {title}",
                "key_implications": [f"Implication 1 for {title}", f"Implication 2 for {title}"],
                "confidence": 0.7,
                "created_at": f"2026-04-25T0{j}:00:00+00:00",
            })

    base = _base_rows(ticker="AMD", snapshot_source_count=3)
    base["positions"] = [
        {
            "id": "pos-amd-1",
            "user_id": "user-held",
            "ticker": "AMD",
            "shares": 10,
            "purchase_price": 120.0,
            "current_price": 155.0,
        }
    ]
    base["risk_scores"] = [
        {
            "id": "rs-1",
            "position_id": "pos-amd-1",
            "safety_score": 58,
            "total_score": 58,
            "grade": "C",
            "source_count": 3,
            "calculated_at": "2026-04-25T01:00:00+00:00",
            "reasoning": None,
            "factor_breakdown": {
                "ai_dimensions": {
                    "news_sentiment": 78,
                    "macro_exposure": 32,
                    "volatility_trend": 42,
                    "position_sizing": 50,
                }
            },
        }
    ]
    base["event_analyses"] = event_rows

    supabase = _FakeSupabase(base)

    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-held", "AMD")

    event_count = len(result["latest_event_analyses"])
    assert event_count == 3, (
        f"Expected 3 events (matching source_count), got {event_count}"
    )


def test_reasoning_is_article_specific_after_bundle(monkeypatch):
    """
    After get_ticker_detail_bundle, the reasoning should contain article-specific text,
    not just generic fallback prose, when event_analyses are present.
    """
    monkeypatch.setattr(
        "app.services.ticker_cache_service.ensure_sp500_universe_seeded",
        lambda _supabase: None,
    )

    base = _base_rows(
        ticker="AMD",
        snapshot_source_count=2,
        news_rows=[
            {
                "id": "n1",
                "ticker": "AMD",
                "headline": "AMD chip gains traction in AI market",
                "summary": "Strong AI adoption boosts AMD outlook.",
                "source": "Reuters",
                "url": "https://example.com/n1",
                "sentiment": "positive",
                "published_at": "2026-04-24T22:00:00+00:00",
                "processed_at": "2026-04-24T22:00:00+00:00",
            },
            {
                "id": "n2",
                "ticker": "AMD",
                "headline": "AMD valuation concerns raised by analysts",
                "summary": "Stock may be overvalued at current levels.",
                "source": "Barron's",
                "url": "https://example.com/n2",
                "sentiment": "negative",
                "published_at": "2026-04-24T20:00:00+00:00",
                "processed_at": "2026-04-24T20:00:00+00:00",
            },
        ],
    )
    supabase = _FakeSupabase(base)
    result = ticker_cache_service.get_ticker_detail_bundle(supabase, "user-1", "AMD")

    reasoning = (result["current_score"] or {}).get("reasoning") or ""
    # Should reference article-specific text, not generic template
    assert "We're still building a full picture" not in reasoning
    assert "Risk reflects recent news coverage and sector conditions" not in reasoning
    # Should have content (not empty)
    assert len(reasoning) > 20
