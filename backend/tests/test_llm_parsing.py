from app.pipeline.analysis_utils import (
    extract_json_list,
    extract_json_object,
    extract_json_value,
)
from app.pipeline.classifier import classify_significance_keyword
from app.pipeline.relevance import _parse_batch_relevance
from app.pipeline.risk_scorer import _parse_batch_scores


def test_extract_json_value_strips_think_and_fences_for_arrays():
    raw = """
    <think>hidden reasoning</think>
    ```json
    [{"article_index": 0, "relevant": true, "affected_tickers": ["AAPL"]}]
    ```
    """

    parsed = extract_json_value(raw, [])

    assert parsed == [
        {"article_index": 0, "relevant": True, "affected_tickers": ["AAPL"]}
    ]


def test_extract_json_object_ignores_wrappers():
    raw = '<think>reasoning</think>{"summary": "ok", "top_risks": ["risk"]}'

    parsed = extract_json_object(raw, {})

    assert parsed == {"summary": "ok", "top_risks": ["risk"]}


def test_extract_json_value_handles_single_quotes_and_trailing_commas():
    raw = """
    Here is the payload:
    ```json
    {'news_sentiment': 72, 'dimension_rationale': {'news_sentiment': 'ok',},}
    ```
    """

    parsed = extract_json_value(raw, {})

    assert parsed == {
        "news_sentiment": 72,
        "dimension_rationale": {"news_sentiment": "ok"},
    }


def test_extract_json_value_finds_balanced_json_inside_prose():
    raw = 'prefix text {"outer": {"inner": [1, 2, 3]}, "results": [{"id": 1}]} suffix'

    parsed = extract_json_value(raw, {})

    assert parsed == {"outer": {"inner": [1, 2, 3]}, "results": [{"id": 1}]}


def test_extract_json_list_accepts_common_wrapper_keys():
    raw = '{"data": [{"article_index": 0, "relevant": true}], "extra": "ignored"}'

    parsed = extract_json_list(raw, [])

    assert parsed == [{"article_index": 0, "relevant": True}]


def test_parse_batch_relevance_accepts_results_wrapper():
    raw = '{"results": [{"article_index": 0, "relevant": true, "affected_tickers": ["GDX"], "event_type": "sector", "why_it_matters": "Gold demand matters."}]}'

    parsed = _parse_batch_relevance(raw, 1)

    assert parsed[0]["relevant"] is True
    assert parsed[0]["affected_tickers"] == ["GDX"]


def test_parse_batch_scores_accepts_list_payload():
    raw = """{"scores": [{"ticker": "AAPL", "news_sentiment": 80, "macro_exposure": 55, "position_sizing": 60, "volatility_trend": 65, "grade": "B"}, {"ticker": "MSFT", "news_sentiment": 70, "macro_exposure": 75, "position_sizing": 85, "volatility_trend": 90, "grade": "A"}]}"""

    parsed = _parse_batch_scores(raw, ["AAPL", "MSFT"])

    assert parsed["AAPL"]["news_sentiment"] == 80
    assert parsed["MSFT"]["volatility_trend"] == 90


def test_classify_significance_keyword_marks_product_launch_major():
    result = classify_significance_keyword(
        "Robinhood launches new product", "New product launch"
    )

    assert result is not None
    assert result["significance"] == "major"


def test_classify_significance_keyword_keeps_analyst_updates_minor():
    result = classify_significance_keyword(
        "Analyst raises price target on HOOD", "rating update and price target change"
    )

    assert result is not None
    assert result["significance"] == "minor"
