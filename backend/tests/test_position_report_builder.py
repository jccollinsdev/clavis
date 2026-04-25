from app.pipeline.position_report_builder import build_position_report


def test_build_position_report_uses_insufficient_evidence_fallback():
    report = __import__("asyncio").run(
        build_position_report(
            {"ticker": "ABBV", "sector": "Healthcare"},
            ["core"],
            [],
        )
    )

    assert "Known facts are limited" in report["summary"]
    assert "low-confidence" in report["long_report"]
