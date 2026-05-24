import sys
import types
import asyncio


_fake_openai_module = types.ModuleType("openai")


class _FakeOpenAI:
    def __init__(self, *args, **kwargs):
        pass


_fake_openai_module.OpenAI = _FakeOpenAI
sys.modules.setdefault("openai", _fake_openai_module)

from app.pipeline import agentic_scan, major_event_analyzer


def test_analyze_minor_events_shared_batch_falls_back_on_retryable_error(
    monkeypatch,
):
    monkeypatch.setattr(
        agentic_scan,
        "chatcompletion_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError(
                "Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'The server cluster is currently under high load.'}}"
            )
        ),
    )

    result = asyncio.run(
        agentic_scan.analyze_minor_events_shared_batch(
        [
            {
                "title": "Portal page",
                "summary": "A low-information page.",
                "body": "This is a low-information page body.",
                "evidence_quality": "partial_body",
            }
        ]
    ))

    assert len(result) == 1
    assert result[0]["risk_direction"] == "neutral"
    assert "Portal page" in result[0]["analysis_text"]


def test_analyze_major_events_shared_batch_falls_back_on_retryable_error(
    monkeypatch,
):
    monkeypatch.setattr(
        major_event_analyzer,
        "chatcompletion_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError(
                "Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'The server cluster is currently under high load.'}}"
            )
        ),
    )

    result = asyncio.run(
        major_event_analyzer.analyze_major_events_shared_batch(
        [
            {
                "title": "Major event",
                "summary": "Something happened.",
                "body": "Additional context.",
                "evidence_quality": "partial_body",
            }
        ]
    ))

    assert len(result) == 1
    assert result[0]["risk_direction"] == "neutral"
    assert "Major event" in result[0]["analysis_text"]


def test_analyze_minor_events_shared_batch_falls_back_on_scalar_payload_item(
    monkeypatch,
):
    monkeypatch.setattr(
        agentic_scan,
        "chatcompletion_text",
        lambda *args, **kwargs: (
            '[{"analysis_text": "First result", "impact_horizon": "near_term", '
            '"risk_direction": "neutral", "confidence": 0.9, "scenario_summary": "ok", '
            '"key_implications": ["one"], "followup_notes": ["two"]}, '
            '"oops"]'
        ),
    )

    result = asyncio.run(
        agentic_scan.analyze_minor_events_shared_batch(
            [
                {
                    "title": "First event",
                    "summary": "Useful detail.",
                    "body": "Useful detail body.",
                    "evidence_quality": "full_body",
                },
                {
                    "title": "Second event",
                    "summary": "Scalar payload.",
                    "body": "Scalar payload body.",
                    "evidence_quality": "full_body",
                },
            ]
        )
    )

    assert len(result) == 2
    assert result[0]["analysis_text"] == "First result"
    assert result[1]["risk_direction"] == "neutral"
    assert "Second event" in result[1]["analysis_text"]


def test_analyze_major_events_shared_batch_falls_back_on_scalar_payload_item(
    monkeypatch,
):
    monkeypatch.setattr(
        major_event_analyzer,
        "chatcompletion_text",
        lambda *args, **kwargs: (
            '[{"analysis_text": "Major result", "impact_horizon": "long_term", '
            '"risk_direction": "improving", "confidence": 0.8, '
            '"scenario_summary": "major ok", "key_implications": ["a"], '
            '"followup_notes": ["b"]}, ...]'
        ),
    )

    result = asyncio.run(
        major_event_analyzer.analyze_major_events_shared_batch(
            [
                {
                    "title": "Major event",
                    "summary": "Useful detail.",
                    "body": "Useful detail body.",
                    "evidence_quality": "full_body",
                },
                {
                    "title": "Second major",
                    "summary": "Ellipsis payload.",
                    "body": "Ellipsis payload body.",
                    "evidence_quality": "full_body",
                },
            ]
        )
    )

    assert len(result) == 2
    assert result[0]["risk_direction"] == "improving"
    assert result[1]["risk_direction"] == "neutral"
    assert "Second major" in result[1]["analysis_text"]
