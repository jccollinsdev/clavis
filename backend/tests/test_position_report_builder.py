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


def test_build_driver_cards_prefers_richer_goog_evidence_over_blog_landing_page():
    cards, state, source = _build_driver_cards(
        {"ticker": "GOOG", "status": "ready"},
        event_analyses=[
            {
                "id": "ev-1",
                "title": "Q1 2026 earnings call: Remarks from our CEO - blog.google",
                "summary": "Q1 2026 earnings call: Remarks from our CEO blog.google",
                "scenario_summary": "The earnings call landing page contains no substantive remarks, so the key risk signal remains opaque.",
                "long_analysis": "The earnings call landing page contains no substantive remarks, so the key risk signal remains opaque.",
                "source": "blog.google",
                "published_at": "2026-05-03T12:00:00+00:00",
                "confidence": 0.9,
                "significance": "major",
                "risk_direction": "neutral",
            },
            {
                "id": "ev-2",
                "title": "Google shares hit all-time high on blowout earnings, market cap doubles to $4.4 trillion in just a year - Fortune",
                "summary": "Google shares hit all-time high on blowout earnings, market cap doubles to $4.4 trillion in just a year Fortune",
                "scenario_summary": "All-time highs and doubling market cap in one year reflect exceptional recent performance, but the pace of appreciation creates elevated downside risk if AI monetization expectations disappoint or competitive positioning shifts.",
                "long_analysis": "All-time highs and doubling market cap in one year reflect exceptional recent performance, but the pace of appreciation creates elevated downside risk if AI monetization expectations disappoint or competitive positioning shifts.",
                "source": "Fortune",
                "published_at": "2026-05-03T13:00:00+00:00",
                "confidence": 0.95,
                "significance": "major",
                "risk_direction": "neutral",
            },
        ],
    )

    assert state == "ready"
    assert source == "generated"
    assert len(cards) == 1
    assert "all-time highs" in cards[0]["summary"].lower()
    assert "elevated downside risk" in cards[0]["summary"].lower()
    assert "blog.google" not in cards[0]["summary"].lower()


def test_build_driver_cards_prefers_crypto_revenue_summary_over_headline():
    cards, state, source = _build_driver_cards(
        {"ticker": "HOOD", "status": "ready"},
        event_analyses=[
            {
                "id": "ev-1",
                "title": "Robinhood Stock Sinks as Earnings Hit by Plunge in Crypto Revenue - Investopedia",
                "summary": "Robinhood Stock Sinks as Earnings Hit by Plunge in Crypto Revenue Investopedia",
                "scenario_summary": "A crypto-driven revenue collapse is the primary culprit behind Robinhood's earnings miss, confirming the stock's sensitivity to crypto market conditions and raising near-term earnings risk.",
                "long_analysis": "A crypto-driven revenue collapse is the primary culprit behind Robinhood's earnings miss, confirming the stock's sensitivity to crypto market conditions and raising near-term earnings risk.",
                "source": "Investopedia",
                "published_at": "2026-05-03T12:00:00+00:00",
                "confidence": 0.9,
                "significance": "major",
                "risk_direction": "negative",
            }
        ],
    )

    assert state == "ready"
    assert source == "generated"
    assert len(cards) == 1
    assert "crypto-driven revenue collapse" in cards[0]["summary"].lower()
    assert "investopedia" not in cards[0]["summary"].lower()


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
