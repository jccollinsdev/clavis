import sys
import types


_fake_openai_module = types.ModuleType("openai")


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


_fake_openai_module.OpenAI = _FakeOpenAI
sys.modules.setdefault("openai", _fake_openai_module)

from app.services import minimax


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def test_chatcompletion_text_respects_minimum_interval(monkeypatch):
    calls = []
    sleeps = []

    monkeypatch.setattr(minimax.settings, "minimax_min_interval_seconds", 1.0)
    monkeypatch.setattr(minimax, "_MINIMAX_NEXT_ALLOWED_AT", 101.0)
    monotonic_values = iter([100.0, 101.0])
    monkeypatch.setattr(minimax.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(minimax.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(minimax.time, "perf_counter", lambda: 0.0)
    monkeypatch.setattr(
        minimax,
        "chatcompletion",
        lambda *args, **kwargs: calls.append((args, kwargs)) or _FakeResponse("{}"),
    )

    result = minimax.chatcompletion_text([{"role": "user", "content": "hi"}])

    assert result == "{}"
    assert sleeps == [1.0]
    assert len(calls) == 1


def test_chatcompletion_text_retries_502_errors(monkeypatch):
    attempts = []

    monkeypatch.setattr(minimax.settings, "minimax_min_interval_seconds", 0.0)
    monkeypatch.setattr(minimax, "_MINIMAX_NEXT_ALLOWED_AT", 0.0)
    monkeypatch.setattr(minimax.time, "perf_counter", lambda: 0.0)
    monkeypatch.setattr(minimax.time, "sleep", lambda seconds: None)

    def fake_chatcompletion(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("502 Bad Gateway")
        return _FakeResponse("{}")

    monkeypatch.setattr(minimax, "chatcompletion", fake_chatcompletion)

    result = minimax.chatcompletion_text([{"role": "user", "content": "hi"}])

    assert result == "{}"
    assert len(attempts) == 2
