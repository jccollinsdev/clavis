"""Wrapper-repair candidate selection: only existing strict-non-usable
news.google.com wrapper rows, never already-usable ones."""
from app.scripts import wrapper_repair as wr


class _Q:
    def __init__(self, data):
        self._d = data

    def select(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def in_(self, *_a, **_k):
        return self

    def gte(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def range(self, *_a, **_k):
        return self

    def execute(self):
        return type("R", (), {"data": self._d})


class _SB:
    def __init__(self, uni, events):
        self._uni, self._ev = uni, events

    def table(self, name):
        return _Q(self._uni if name == "ticker_universe" else self._ev)


def test_selection_filters_to_unusable_google_wrappers():
    uni = [{"ticker": "AAA", "index_membership": "SP500", "is_active": True},
           {"ticker": "BBB", "index_membership": "SP500", "is_active": True}]
    events = [
        # google wrapper, headline_only -> SELECTED
        {"id": "1", "ticker": "AAA", "canonical_url": "https://news.google.com/x1",
         "headline_only": True, "extraction_status": "failed", "body": "",
         "sentiment_score": None, "rejection_reason": None, "analysis_status": "headline_only"},
        # google wrapper, real body, already usable -> EXCLUDED (idempotent)
        {"id": "2", "ticker": "AAA", "canonical_url": "https://news.google.com/x2",
         "headline_only": False, "extraction_status": "success", "body": "x" * 500,
         "sentiment_score": 55, "rejection_reason": None, "analysis_status": None},
        # google wrapper, headline_only WITH stale headline-derived
        # sentiment -> SELECTED (the ~99% real-world case)
        {"id": "6", "ticker": "AAA", "canonical_url": "https://news.google.com/x6",
         "headline_only": True, "extraction_status": "failed", "body": "",
         "sentiment_score": 50, "rejection_reason": None,
         "analysis_status": "headline_only"},
        # google wrapper but rejected -> EXCLUDED (stays retryable elsewhere)
        {"id": "3", "ticker": "AAA", "canonical_url": "https://news.google.com/x3",
         "headline_only": True, "extraction_status": "failed", "body": "",
         "sentiment_score": None, "rejection_reason": "blocked", "analysis_status": "headline_only"},
        # NOT a google wrapper -> EXCLUDED
        {"id": "4", "ticker": "BBB", "canonical_url": "https://reuters.com/y",
         "headline_only": True, "extraction_status": "failed", "body": "",
         "sentiment_score": None, "rejection_reason": None, "analysis_status": "headline_only"},
        # google wrapper, extraction failed, no body -> SELECTED
        {"id": "5", "ticker": "BBB", "source_url": "https://news.google.com/x5",
         "canonical_url": None, "headline_only": False, "extraction_status": "failed",
         "body": "[No body extracted] Headline", "sentiment_score": None,
         "rejection_reason": None, "analysis_status": None},
    ]
    sb = _SB(uni, events)
    got = {r["id"] for r in wr._select_candidates(sb, window_days=7, limit=0)}
    assert got == {"1", "5", "6"}


def test_min_body_constant_is_strict():
    assert wr.MIN_BODY == 300
