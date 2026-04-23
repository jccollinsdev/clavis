from datetime import datetime, timezone

from app.services.alert_payloads import enrich_alert_row
from app.services.digest_selection import (
    current_trading_date,
    select_latest_trading_day_digest,
)


def test_current_trading_date_rolls_weekends_back_to_friday():
    saturday = datetime(2026, 4, 25, 15, 0, tzinfo=timezone.utc)

    assert current_trading_date(saturday).isoformat() == "2026-04-24"


def test_select_latest_trading_day_digest_prefers_same_trading_day():
    now = datetime(2026, 4, 22, 15, 0, tzinfo=timezone.utc)
    digests = [
        {"id": "tue", "generated_at": "2026-04-21T14:00:00Z"},
        {"id": "wed", "generated_at": "2026-04-22T14:00:00Z"},
    ]

    selected = select_latest_trading_day_digest(digests, now)

    assert selected["id"] == "wed"


def test_enrich_alert_row_adds_reason_and_stringifies_details():
    alert = {
        "type": "grade_change",
        "position_ticker": "hood",
        "previous_grade": "B",
        "new_grade": "D",
        "message": "HOOD grade changed from B to D",
        "change_details": {"previous_score": 72.5, "new_score": 41.2},
    }

    enriched = enrich_alert_row(alert)

    assert (
        enriched["change_reason"] == "HOOD moved from B to D after the latest analysis."
    )
    assert enriched["change_details"] == {
        "previous_score": "72.5",
        "new_score": "41.2",
    }
