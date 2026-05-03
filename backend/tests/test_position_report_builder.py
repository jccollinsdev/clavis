import asyncio

from app.pipeline.position_report_builder import (
    _build_driver_cards,
    _generate_driver_summary,
    build_position_report,
)


def test_build_position_report_generates_driver_cards(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.position_report_builder.chatcompletion_text",
        lambda **_kwargs: (
            '{"summary":"Major downside pressure is building.",'
            '"long_report":"Major downside pressure is building.",'
            '"methodology":"Uses event evidence.",'
            '"top_risks":["Margin pressure is rising."],'
            '"watch_items":["Watch for guidance cuts."],'
            '"risk_context":[]}'
        ),
    )

    report = asyncio.run(
        build_position_report(
            {"ticker": "ABBV", "sector": "Healthcare"},
            ["core"],
            [
                {
                    "id": "ev-1",
                    "title": "Earnings beat but guidance cut",
                    "summary": "Revenue beat, but management cut guidance after margin pressure.",
                    "long_analysis": "earnings guidance margin pressure",
                    "source": "Reuters",
                    "source_url": "https://example.com/1",
                    "published_at": "2026-04-24T01:00:00+00:00",
                    "confidence": 0.9,
                    "significance": "major",
                    "risk_direction": "worsening",
                }
            ],
        )
    )

    assert report["driver_cards_state"] == "ready"
    assert report["driver_cards_source"] == "generated"
    assert len(report["driver_cards"]) == 1
    assert report["driver_cards"][0]["theme"] == "earnings_risk"
    assert report["driver_cards"][0]["direction"] == "negative"
    assert report["driver_cards"][0]["source_chips"] == ["Reuters"]
    assert report["driver_cards"][0]["supporting_evidence"][0]["id"] == "ev-1"
    assert report["driver_cards"][0]["title"] == "Earnings risk is elevated"
    assert report["driver_cards"][0]["summary"] == "Revenue beat, but management cut guidance after margin pressure."


def test_build_position_report_uses_insufficient_evidence_fallback():
    report = __import__("asyncio").run(
        build_position_report(
            {"ticker": "ABBV", "sector": "Healthcare"},
            ["core"],
            [],
        )
    )

    assert "not enough recent news" in report["summary"]
    assert "limited-data" in report["long_report"]
    assert report["driver_cards"] == []
    assert report["driver_cards_state"] == "limited"


def test_build_driver_cards_never_uses_rss_headline_or_snippet_for_unknown_theme_mapping(monkeypatch):
    monkeypatch.delitem(
        __import__("app.pipeline.position_report_builder", fromlist=["_THEME_DRIVER_TITLES"])._THEME_DRIVER_TITLES,
        ("margin_risk", "negative"),
        raising=False,
    )
    monkeypatch.delitem(
        __import__("app.pipeline.position_report_builder", fromlist=["_THEME_DRIVER_DESCRIPTIONS"])._THEME_DRIVER_DESCRIPTIONS,
        ("margin_risk", "negative"),
        raising=False,
    )

    cards, state, source = _build_driver_cards(
        {"ticker": "AMD", "status": "ready"},
        event_analyses=[
            {
                "id": "ev-1",
                "title": "Chipmaker warns of margin pressure after pricing reset - Reuters",
                "summary": "Chipmaker warns of margin pressure after pricing reset - Reuters",
                "long_analysis": "Margin pressure is building as pricing discipline weakens across the segment.",
                "source": "Yahoo Finance",
                "source_url": "https://example.com/article",
                "published_at": "2026-05-03T12:00:00+00:00",
                "confidence": 0.88,
                "significance": "major",
                "risk_direction": "worsening",
            }
        ],
    )

    assert state == "ready"
    assert source == "generated"
    assert len(cards) == 1
    assert cards[0]["title"] == "Margins are compressing"
    assert cards[0]["title"] != "Chipmaker warns of margin pressure after pricing reset - Reuters"
    assert cards[0]["summary"] == "Margin trajectory is stable but offers no near-term catalyst to drive meaningful earnings upside."


def test_build_driver_cards_prefers_specific_summary_over_generic_primary_note():
    summary = _generate_driver_summary(
        "margin_risk",
        "negative",
        [
            {
                "title": "Margins under pressure",
                "summary": "Analyst watch remains cautious as the company continues to face margin pressure from pricing resets and higher labor costs.",
            },
            {
                "title": "Freight and labor costs rise",
                "summary": "Higher freight and labor costs are compressing gross margin in the quarter.",
            },
        ],
    )

    assert summary == "Higher freight and labor costs are compressing gross margin in the quarter."


def test_build_driver_cards_classifies_stretched_valuation_as_negative():
    cards, state, source = _build_driver_cards(
        {"ticker": "AMD", "status": "ready"},
        news_items=[
            {
                "headline": "AMD: Strong AI Tailwinds, But Valuation Is Getting Ahead Of Reality (NASDAQ:AMD) - Seeking Alpha",
                "summary": "AMD: Strong AI Tailwinds, But Valuation Is Getting Ahead Of Reality (NASDAQ:AMD) Seeking Alpha",
                "source": "Seeking Alpha",
                "sentiment": "positive",
            }
        ],
    )

    assert state == "ready"
    assert source == "generated"
    assert len(cards) == 1
    assert cards[0]["title"] == "Valuation is stretched relative to fundamentals"
    assert "Seeking Alpha" not in cards[0]["summary"]
    assert cards[0]["summary"] == "The current multiple prices in near-perfect execution; any earnings miss or guidance cut would cause outsized multiple compression."


def test_build_driver_cards_handles_missing_timestamps():
    cards, state, _source = _build_driver_cards(
        {"ticker": "HOOD", "status": "ready"},
        news_items=[
            {
                "headline": "Robinhood revenue outlook weakens after crypto slowdown - Reuters",
                "summary": "Robinhood revenue outlook weakens after crypto slowdown Reuters",
                "source": "Reuters",
                "sentiment": "negative",
            }
        ],
    )

    assert state == "ready"
    assert len(cards) == 1
    assert cards[0]["title"] == "Earnings risk is elevated"
