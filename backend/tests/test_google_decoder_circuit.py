"""Tests for google_news_decoder circuit breaker, cache, and budget."""
import asyncio
import time
import unittest.mock as mock
import pytest

import app.services.google_news_decoder as gnd


def _reset_state():
    gnd._decode_cache.clear()
    gnd._failure_cache.clear()
    gnd._circuit_open_until = 0.0
    gnd._circuit_429_count = 0
    gnd.reset_decode_metrics()


# --- Circuit breaker tests ---

def test_circuit_opens_after_threshold_429s():
    _reset_state()
    for _ in range(gnd._CIRCUIT_OPEN_THRESHOLD):
        gnd._record_429()
    assert gnd._circuit_is_open(), "Circuit should be open after threshold 429s"


def test_circuit_closed_before_threshold():
    _reset_state()
    gnd._record_429()
    gnd._record_429()
    assert not gnd._circuit_is_open(), "Circuit should stay closed below threshold"


def test_circuit_opens_until_reset_seconds():
    _reset_state()
    for _ in range(gnd._CIRCUIT_OPEN_THRESHOLD):
        gnd._record_429()
    assert gnd._circuit_is_open()
    # Simulate time passing beyond reset
    gnd._circuit_open_until = time.monotonic() - 1
    assert not gnd._circuit_is_open(), "Circuit should close after reset period"


def test_success_decays_circuit_count():
    _reset_state()
    gnd._record_429()
    gnd._record_429()
    assert gnd._circuit_429_count == 2
    gnd._record_success("https://news.google.com/articles/test", "https://example.com/article")
    assert gnd._circuit_429_count == 1


@pytest.mark.asyncio
async def test_decode_returns_circuit_open_when_tripped():
    _reset_state()
    gnd._circuit_open_until = time.monotonic() + 9999.0

    result = await gnd.decode_google_news_url(
        "https://news.google.com/articles/CBMiZGh0dHBzOi8vd3d3LmV4YW1wbGUuY29tL2FydGljbGU"
    )
    assert result["status"] is False
    assert "circuit_open" in result["message"]


# --- Cache tests ---

@pytest.mark.asyncio
async def test_decode_uses_cache_on_second_call():
    _reset_state()
    google_url = "https://news.google.com/articles/CBMiZGh0dHBzOi8vd3d3LmV4YW1wbGUuY29tL2FydGljbGU"
    decoded = "https://www.example.com/article"
    gnd._decode_cache[google_url] = decoded

    result = await gnd.decode_google_news_url(google_url)
    assert result["status"] is True
    assert result["decoded_url"] == decoded
    assert result.get("cache_hit") is True
    assert gnd._metrics["cache_hits"] == 1


@pytest.mark.asyncio
async def test_decode_skips_recently_failed_url():
    _reset_state()
    google_url = "https://news.google.com/articles/CBMiZGh0dHBzOi8vd3d3LmV4YW1wbGUuY29tL2FydGljbGU"
    gnd._failure_cache[google_url] = time.monotonic()  # just failed

    result = await gnd.decode_google_news_url(google_url)
    assert result["status"] is False
    assert "recent_failure" in result["message"]


# --- Budget tests ---

@pytest.mark.asyncio
async def test_budgeted_decode_respects_budget():
    _reset_state()
    # Pre-fill some cache entries so decode is instantaneous for some
    urls = [f"https://news.google.com/articles/CBMi{i:04d}xxxx" for i in range(10)]

    # Mock the actual decode to count calls
    call_count = 0

    async def mock_decode(url, *, client=None, interval=None):
        nonlocal call_count
        call_count += 1
        return {"status": True, "decoded_url": f"https://example.com/{call_count}"}

    with mock.patch.object(gnd, "decode_google_news_url", side_effect=mock_decode):
        # Mock _extract_base64_str to return non-None for all urls
        with mock.patch.object(gnd, "_extract_base64_str", return_value="fakebase64"):
            result = await gnd.decode_google_news_urls_budgeted(urls, budget=3)

    # Budget of 3 means at most 3 live decode attempts
    assert call_count <= 3, f"Expected ≤3 decode attempts, got {call_count}"


@pytest.mark.asyncio
async def test_budgeted_decode_cache_hits_dont_count_toward_budget():
    _reset_state()
    # Pre-cache 5 URLs
    cached_urls = [
        f"https://news.google.com/articles/CBMi{i:04d}cache" for i in range(5)
    ]
    for url in cached_urls:
        gnd._decode_cache[url] = f"https://example.com/cached/{url[-5:]}"

    fresh_urls = [
        f"https://news.google.com/articles/CBMi{i:04d}fresh" for i in range(3)
    ]
    all_urls = cached_urls + fresh_urls

    call_count = 0

    async def mock_decode(url, *, client=None, interval=None):
        nonlocal call_count
        call_count += 1
        return {"status": True, "decoded_url": f"https://example.com/fresh/{call_count}"}

    with mock.patch.object(gnd, "decode_google_news_url", side_effect=mock_decode):
        with mock.patch.object(gnd, "_extract_base64_str", return_value="fakebase64"):
            result = await gnd.decode_google_news_urls_budgeted(all_urls, budget=2)

    # 5 should come from cache, at most 2 fresh attempts
    assert call_count <= 2
    assert len(result) >= 5  # all cached ones should be in result


@pytest.mark.asyncio
async def test_budgeted_decode_skips_when_circuit_open():
    _reset_state()
    gnd._circuit_open_until = time.monotonic() + 9999.0

    urls = [f"https://news.google.com/articles/CBMi{i:04d}xxxx" for i in range(5)]

    with mock.patch.object(gnd, "_extract_base64_str", return_value="fakebase64"):
        result = await gnd.decode_google_news_urls_budgeted(urls, budget=10)

    assert len(result) == 0, "No decodes should succeed when circuit is open"
    assert gnd._metrics["skipped_circuit_open"] > 0


# --- Metrics tests ---

def test_metrics_track_429s():
    _reset_state()
    gnd._record_429()
    gnd._record_429()
    assert gnd.get_decode_metrics()["rate_limited_429"] == 2


def test_metrics_track_cache_hits():
    _reset_state()
    gnd._decode_cache["https://news.google.com/articles/test"] = "https://example.com"
    gnd._metrics["cache_hits"] += 1  # simulate
    assert gnd.get_decode_metrics()["cache_hits"] == 1


def test_reset_metrics():
    _reset_state()
    gnd._record_429()
    gnd.reset_decode_metrics()
    assert gnd.get_decode_metrics()["rate_limited_429"] == 0
