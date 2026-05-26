from __future__ import annotations

from app.services import polygon


class _Response:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def json(self):
        return {}


def test_polygon_get_short_circuits_after_auth_error(monkeypatch):
    current_time = {"value": 100.0}
    request_calls: list[str] = []
    rate_limit_calls: list[str] = []

    def fake_monotonic():
        return current_time["value"]

    def fake_rate_limit():
        rate_limit_calls.append("rate")

    def fake_get(url, *_, **__):
        request_calls.append(url)
        return _Response(403)

    monkeypatch.setattr(polygon.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(polygon, "_rate_limit_polygon", fake_rate_limit)
    monkeypatch.setattr(polygon.requests, "get", fake_get)
    monkeypatch.setattr(polygon, "_polygon_auth_failed_until", 0.0)

    first = polygon.polygon_get("https://example.com/first", params={"apiKey": "x"})

    assert first.status_code == 403
    assert request_calls == ["https://example.com/first"]
    assert rate_limit_calls == ["rate"]

    second = polygon.polygon_get("https://example.com/second", params={"apiKey": "x"})

    assert second.status_code == 403
    assert request_calls == ["https://example.com/first"]
    assert rate_limit_calls == ["rate"]


def test_polygon_get_retries_requests_after_auth_cooldown(monkeypatch):
    current_time = {"value": 100.0}
    request_calls: list[str] = []
    rate_limit_calls: list[str] = []

    def fake_monotonic():
        return current_time["value"]

    def fake_rate_limit():
        rate_limit_calls.append("rate")

    def fake_get(url, *_, **__):
        request_calls.append(url)
        return _Response(403 if len(request_calls) == 1 else 200)

    monkeypatch.setattr(polygon.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(polygon, "_rate_limit_polygon", fake_rate_limit)
    monkeypatch.setattr(polygon.requests, "get", fake_get)
    monkeypatch.setattr(polygon, "_polygon_auth_failed_until", 0.0)

    first = polygon.polygon_get("https://example.com/first", params={"apiKey": "x"})
    assert first.status_code == 403

    current_time["value"] += polygon._AUTH_FAILURE_COOLDOWN + 1.0

    second = polygon.polygon_get("https://example.com/second", params={"apiKey": "x"})

    assert second.status_code == 200
    assert request_calls == [
        "https://example.com/first",
        "https://example.com/second",
    ]
    assert rate_limit_calls == ["rate", "rate"]
