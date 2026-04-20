from app.pipeline.analysis_utils import sanitize_public_analysis_text


def test_sanitize_public_analysis_text_removes_internal_evidence_terms():
    payload = {
        "summary": "This is a full_body read rather than a fully grounded article analysis.",
        "long_report": "The title_only summary should not leak.",
        "watch_items": ["headline_summary is not user-facing"],
        "thesis_verifier": [
            {"reasoning": "Based on evidence quality and full_body coverage."}
        ],
    }

    sanitized = sanitize_public_analysis_text(payload)

    assert "full_body" not in str(sanitized)
    assert "title_only" not in str(sanitized)
    assert "headline_summary" not in str(sanitized)
    assert "fully grounded" not in str(sanitized)
    assert "provisional article read" in sanitized["summary"]
