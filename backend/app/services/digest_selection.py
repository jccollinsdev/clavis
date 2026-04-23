from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


_DIGEST_TIMEZONE = ZoneInfo("America/New_York")


def _parse_digest_timestamp(value: object) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=ZoneInfo("UTC"))

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def current_trading_date(now: datetime | None = None) -> date:
    current = now or datetime.now(_DIGEST_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=_DIGEST_TIMEZONE)
    current = current.astimezone(_DIGEST_TIMEZONE)

    if current.weekday() >= 5:
        offset = current.weekday() - 4
        return (current - timedelta(days=offset)).date()

    return current.date()


def digest_trading_date(digest: dict | None) -> date | None:
    timestamp = _parse_digest_timestamp((digest or {}).get("generated_at"))
    if not timestamp:
        return None
    return timestamp.astimezone(_DIGEST_TIMEZONE).date()


def select_latest_trading_day_digest(
    digests: list[dict] | None,
    now: datetime | None = None,
) -> dict | None:
    """Pick the newest digest for the active trading date.

    Keep this helper isolated so the old 24-hour freshness shortcut can be
    restored in one place if we ever need to revert this behavior.
    """

    if not digests:
        return None

    target_date = current_trading_date(now)
    parsed: list[tuple[datetime, dict]] = []

    for digest in digests:
        timestamp = _parse_digest_timestamp(digest.get("generated_at"))
        if timestamp is None:
            continue
        parsed.append((timestamp.astimezone(_DIGEST_TIMEZONE), digest))

    if not parsed:
        return digests[0]

    parsed.sort(key=lambda item: item[0], reverse=True)

    for timestamp, digest in parsed:
        if timestamp.date() <= target_date:
            return digest

    return parsed[0][1]
