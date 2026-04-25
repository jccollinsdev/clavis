import sys
import types
import importlib

_fake_supabase_module = types.ModuleType("supabase")
_fake_supabase_module.create_client = lambda *args, **kwargs: None
_fake_supabase_module.Client = object
sys.modules.setdefault("supabase", _fake_supabase_module)

from app.pipeline import scheduler
from app.services.ticker_cache_service import sync_ticker_news_cache


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = {}
        self.lt_filters = {}
        self._delete = False
        self._insert_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def delete(self, *_args, **_kwargs):
        self._delete = True
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def lt(self, key, value):
        self.lt_filters[key] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = self.supabase.rows.setdefault(self.table_name, [])
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        for key, value in self.lt_filters.items():
            rows = [row for row in rows if (row.get(key) or "") >= value]

        if self._delete:
            self.supabase.rows[self.table_name] = rows
            return _FakeResult([])

        if self._insert_payload is not None:
            payload = self._insert_payload
            if isinstance(payload, list):
                rows.extend(payload)
            else:
                rows.append(payload)
            self.supabase.rows[self.table_name] = rows
            return _FakeResult(payload if isinstance(payload, list) else [payload])

        return _FakeResult(rows)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_sync_ticker_news_cache_replaces_rows_and_dedupes():
    supabase = _FakeSupabase(
        {"ticker_news_cache": [{"ticker": "HOOD", "headline": "old"}]}
    )

    result = sync_ticker_news_cache(
        supabase,
        ticker="hood",
        news_rows=[
            {
                "event_hash": "hash-1",
                "title": "First headline",
                "summary": "First summary",
                "source": "Reuters",
                "url": "https://example.com/1",
                "sentiment": "positive",
                "published_at": "2026-04-24T02:00:00+00:00",
                "processed_at": "2026-04-24T02:05:00+00:00",
            },
            {
                "event_hash": "hash-1",
                "title": "Duplicate headline",
                "summary": "Duplicate summary",
                "source": "Reuters",
                "url": "https://example.com/1",
                "sentiment": "positive",
                "published_at": "2026-04-24T02:00:00+00:00",
                "processed_at": "2026-04-24T02:05:00+00:00",
            },
            {
                "event_hash": "hash-2",
                "title": "Second headline",
                "summary": "Second summary",
                "source": "AP",
                "url": "https://example.com/2",
                "sentiment": "neutral",
                "published_at": "2026-04-24T01:00:00+00:00",
                "processed_at": "2026-04-24T01:05:00+00:00",
            },
        ],
    )

    rows = supabase.rows["ticker_news_cache"]
    assert result["status"] == "completed"
    assert result["count"] == 2
    assert [row["headline"] for row in rows] == ["First headline", "Second headline"]
    assert rows[0]["ticker"] == "HOOD"


def test_cleanup_old_news_items_clears_ticker_news_cache():
    supabase = _FakeSupabase(
        {
            "news_items": [
                {"processed_at": "2026-03-01T00:00:00+00:00"},
                {"processed_at": "2026-04-23T00:00:00+00:00"},
            ],
            "ticker_news_cache": [
                {"processed_at": "2026-03-01T00:00:00+00:00"},
                {"processed_at": "2026-04-23T00:00:00+00:00"},
            ],
        }
    )

    supabase_service = importlib.import_module("app.services.supabase")

    original = supabase_service.get_supabase
    try:
        supabase_service.get_supabase = lambda: supabase
        scheduler._cleanup_old_news_items()
    finally:
        supabase_service.get_supabase = original

    assert supabase.rows["news_items"] == [
        {"processed_at": "2026-04-23T00:00:00+00:00"}
    ]
    assert supabase.rows["ticker_news_cache"] == [
        {"processed_at": "2026-04-23T00:00:00+00:00"}
    ]
