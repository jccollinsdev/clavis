import asyncio
import json
import os
import sys
import types

os.environ.setdefault("SUPABASE_URL", "https://example.com")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "dummy")
os.environ.setdefault("SUPABASE_JWT_SECRET", "dummy")
os.environ.setdefault("MINIMAX_API_KEY", "dummy")

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

from app.pipeline import portfolio_compiler


def test_compile_portfolio_digest_uses_summary_length_token_budget(monkeypatch):
    captured = {}

    def fake_chatcompletion_text(**kwargs):
        captured.update(kwargs)
        return json.dumps(
            {
                "overall_summary": "summary",
                "content": "content",
                "sections": {
                    "overnight_macro": {"headlines": [], "themes": [], "brief": ""},
                    "sector_overview": [],
                    "position_impacts": [],
                    "portfolio_impact": [],
                    "what_matters_today": [],
                    "watchlist_alerts": [],
                    "major_events": [],
                    "watch_list": [],
                    "monitoring_notes": [],
                    "portfolio_advice": [],
                },
            }
        )

    monkeypatch.setattr(portfolio_compiler, "chatcompletion_text", fake_chatcompletion_text)

    result = asyncio.run(
        portfolio_compiler.compile_portfolio_digest(
            [{"ticker": "HOOD", "grade": "B", "total_score": 70}],
            "B",
            summary_length="detailed",
        )
    )

    assert captured["max_tokens"] == 2200
    assert result["content"] == "content"
