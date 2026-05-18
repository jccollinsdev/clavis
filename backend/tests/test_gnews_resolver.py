"""Tests for the production Google-News wrapper resolver + cache."""
import asyncio
import inspect

import pytest

from app.services import gnews_resolver as gr


# ───────────────────────── token / payload parsing ─────────────────────────
def test_extract_tokens_ok():
    html = '<c-wiz data-n-a-id="ABC123" data-n-a-sg="SIG99" data-n-a-ts="1700000000"></c-wiz>'
    assert gr.extract_tokens(html) == ("ABC123", "SIG99", "1700000000")


def test_extract_tokens_missing_returns_none():
    assert gr.extract_tokens("<html>no tokens</html>") is None
    assert gr.extract_tokens('<div data-n-a-id="x"></div>') is None


def test_parse_batch_url_extracts_publisher():
    body = (
        ")]}'\n\n[[\"wrb.fr\",\"Fbv4je\",\"[\\\"garturlres\\\","
        "[\\\"https://www.reuters.com/markets/abc-123\\\"]]\"]]"
    )
    assert gr.parse_batch_url(body) == "https://www.reuters.com/markets/abc-123"


def test_parse_batch_url_rejects_google_and_empty():
    assert gr.parse_batch_url(")]}'\n[[\"x\"]]") is None
    body = ")]}'\n[\"garturlres\",[\"https://news.google.com/foo\"]]"
    assert gr.parse_batch_url(body) is None


def test_is_google_wrapper_only_news_google():
    assert gr.is_google_wrapper("https://news.google.com/rss/articles/CBMiX")
    assert not gr.is_google_wrapper("https://www.reuters.com/x")
    # plain google.com is NOT a wrapper (resolver is not a discovery source)
    assert not gr.is_google_wrapper("https://www.google.com/search?q=x")


# ───────────────────────────── fake httpx ──────────────────────────────────
class _Resp:
    def __init__(self, url, text="", status=200):
        self.url = url
        self.text = text
        self.status_code = status


class _FakeClient:
    def __init__(self, get=None, post=None, get_exc=None, post_exc=None):
        self._get, self._post = get, post
        self._ge, self._pe = get_exc, post_exc

    async def get(self, url, **kw):
        if self._ge:
            raise self._ge
        return self._get

    async def post(self, url, **kw):
        if self._pe:
            raise self._pe
        return self._post


def _run(c):
    return asyncio.get_event_loop().run_until_complete(c)


GOOGLE = "https://news.google.com/rss/articles/CBMiABC?oc=5"


def test_resolve_invalid_url():
    r = _run(gr.resolve_wrapper("", _FakeClient(), timeout=1))
    assert r["status"] == gr.STATUS_INVALID


def test_resolve_not_wrapper():
    r = _run(gr.resolve_wrapper("https://reuters.com/x", _FakeClient(), timeout=1))
    assert r["status"] == gr.STATUS_NOT_WRAPPER


def test_resolve_direct_redirect():
    cl = _FakeClient(get=_Resp("https://www.cnbc.com/story", "<html/>"))
    r = _run(gr.resolve_wrapper(GOOGLE, cl, timeout=1))
    assert r["status"] == gr.STATUS_RESOLVED
    assert r["resolved_url"] == "https://www.cnbc.com/story"
    assert r["final_domain"] == "cnbc.com"


def test_resolve_via_batchexecute():
    html = '<c-wiz data-n-a-id="ID1" data-n-a-sg="SG1" data-n-a-ts="123"></c-wiz>'
    batch = ")]}'\n[\"garturlres\",[\"https://www.barrons.com/articles/xyz\"]]"
    cl = _FakeClient(get=_Resp(GOOGLE, html), post=_Resp(_B(), batch))
    r = _run(gr.resolve_wrapper(GOOGLE, cl, timeout=1))
    assert r["status"] == gr.STATUS_RESOLVED
    assert r["resolved_url"] == "https://www.barrons.com/articles/xyz"


def _B():
    return gr._BATCH_URL


def test_resolve_token_parse_failed():
    cl = _FakeClient(get=_Resp(GOOGLE, "<html>no tokens here</html>"))
    r = _run(gr.resolve_wrapper(GOOGLE, cl, timeout=1))
    assert r["status"] == gr.STATUS_TOKEN_FAIL


def test_resolve_consent_or_captcha():
    cl = _FakeClient(get=_Resp("https://consent.google.com/m?continue=x", "x"))
    r = _run(gr.resolve_wrapper(GOOGLE, cl, timeout=1))
    assert r["status"] == gr.STATUS_CONSENT


def test_resolve_still_google_url():
    html = '<c-wiz data-n-a-id="ID1" data-n-a-sg="SG1" data-n-a-ts="123"></c-wiz>'
    batch = ")]}'\n[\"garturlres\",[\"https://news.google.com/articles/again\"]]"
    cl = _FakeClient(get=_Resp(GOOGLE, html), post=_Resp(_B(), batch))
    r = _run(gr.resolve_wrapper(GOOGLE, cl, timeout=1))
    assert r["status"] == gr.STATUS_STILL_GOOGLE


def test_resolve_timeout():
    import httpx

    cl = _FakeClient(get_exc=httpx.TimeoutException("slow"))
    r = _run(gr.resolve_wrapper(GOOGLE, cl, timeout=1))
    assert r["status"] == gr.STATUS_TIMEOUT


def test_resolve_request_failed_non_200():
    html = '<c-wiz data-n-a-id="ID1" data-n-a-sg="SG1" data-n-a-ts="123"></c-wiz>'
    cl = _FakeClient(get=_Resp(GOOGLE, html), post=_Resp(_B(), "err", status=500))
    r = _run(gr.resolve_wrapper(GOOGLE, cl, timeout=1))
    assert r["status"] == gr.STATUS_REQ_FAIL


# ───────────────────────────── cache idempotency ───────────────────────────
class _FakeTable:
    def __init__(self, store):
        self.store = store
        self._op = None
        self._row = None
        self._eqval = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def eq(self, _c, v):
        self._eqval = v
        return self

    def limit(self, _n):
        return self

    def upsert(self, row, **_k):
        self._op, self._row = "upsert", row
        return self

    def execute(self):
        if self._op == "select":
            row = self.store.get(self._eqval)
            return type("R", (), {"data": [row] if row else []})
        if self._op == "upsert":
            self.store[self._row["original_url"]] = self._row
            return type("R", (), {"data": [self._row]})
        return type("R", (), {"data": []})


class _FakeSB:
    def __init__(self):
        self._store = {}

    def table(self, _n):
        return _FakeTable(self._store)


def test_cache_roundtrip_and_idempotency():
    sb = _FakeSB()
    res = gr._result(GOOGLE, gr.STATUS_RESOLVED, __import__("time").monotonic(),
                     "https://www.wsj.com/articles/a")
    gr.cache_store(sb, res)
    hit = gr.cache_lookup(sb, GOOGLE)
    assert hit and hit["status"] == gr.STATUS_RESOLVED
    assert hit["resolved_url"] == "https://www.wsj.com/articles/a"
    assert hit["attempts"] == 1
    gr.cache_store(sb, res)
    assert gr.cache_lookup(sb, GOOGLE)["attempts"] == 2  # idempotent, counts attempts


def test_resolve_with_cache_reuses_positive(monkeypatch):
    sb = _FakeSB()
    gr.cache_store(sb, gr._result(GOOGLE, gr.STATUS_RESOLVED, 0.0,
                                  "https://www.cnbc.com/x"))

    async def _boom(*a, **k):
        raise AssertionError("network must not be hit on positive cache hit")

    monkeypatch.setattr(gr, "resolve_wrapper", _boom)
    r = _run(gr.resolve_with_cache(sb, GOOGLE, _FakeClient(), timeout=1))
    assert r["cached"] and r["resolved_url"] == "https://www.cnbc.com/x"


def test_resolve_with_cache_reuses_negative(monkeypatch):
    sb = _FakeSB()
    gr.cache_store(sb, gr._result(GOOGLE, gr.STATUS_STILL_GOOGLE, 0.0))

    async def _boom(*a, **k):
        raise AssertionError("network must not be hit on negative terminal cache")

    monkeypatch.setattr(gr, "resolve_wrapper", _boom)
    r = _run(gr.resolve_with_cache(sb, GOOGLE, _FakeClient(), timeout=1,
                                   reuse_negative=True))
    assert r["cached"] and r["status"] == gr.STATUS_STILL_GOOGLE


# ───────────────────────────── safety guards ───────────────────────────────
def test_resolver_uses_no_proxy_browser_or_evasion():
    # scan executable code only — strip the module docstring (which
    # legitimately references the Playwright POC comparison)
    src = inspect.getsource(gr)
    code = src.split('"""', 2)[-1].lower()
    for bad in ("import playwright", "import selenium", "proxies=", "proxy=",
                "stealth", "undetected", "fingerprint", "2captcha",
                "anticaptcha", "consent.google.com/save"):
        assert bad not in code, f"resolver must not use {bad}"


def test_resolver_is_not_a_discovery_source():
    # only resolves an explicit existing wrapper URL; no search/discovery API
    src = inspect.getsource(gr).lower()
    assert "search?q=" not in src
    assert "def resolve_wrapper" in inspect.getsource(gr)
