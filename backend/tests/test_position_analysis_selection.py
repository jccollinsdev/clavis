from app.routes.positions import _select_current_analysis


def test_select_current_analysis_prefers_latest_substantive_ready_row():
    analyses = [
        {
            "status": "ready",
            "source_count": 0,
            "top_news": [],
            "top_risks": ["No new material risk catalysts identified."],
        },
        {
            "status": "ready",
            "source_count": 3,
            "top_news": ["JPMorgan Joins Project Glasswing"],
            "top_risks": ["Meaningful risk"],
        },
    ]

    selected = _select_current_analysis(analyses)

    assert selected == analyses[1]


def test_select_current_analysis_falls_back_to_latest_ready_when_none_substantive():
    analyses = [
        {
            "status": "ready",
            "source_count": 0,
            "top_news": [],
            "top_risks": ["No new material risk catalysts identified."],
        },
        {
            "status": "ready",
            "source_count": 0,
            "top_news": [],
            "top_risks": [],
        },
    ]

    selected = _select_current_analysis(analyses)

    assert selected == analyses[0]
