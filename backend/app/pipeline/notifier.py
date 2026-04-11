import logging

from ..services.apns import PushDeliveryResult, send_push

GRADE_RANK = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
logger = logging.getLogger(__name__)


def _log_push_failure(
    notification_type: str, user_id: str, apns_token: str, result: PushDeliveryResult
):
    if result.success:
        return

    fingerprint = (
        apns_token if len(apns_token) <= 10 else f"{apns_token[:6]}...{apns_token[-4:]}"
    )
    logger.warning(
        "Notification delivery failed",
        extra={
            "notification_type": notification_type,
            "user_id": user_id,
            "token": fingerprint,
            "reason": result.reason,
            "status_code": result.status_code,
            "attempt_count": result.attempt_count,
            "retryable": result.retryable,
        },
    )


async def notify_digest(user_id: str, apns_token: str, digest_content: str):
    payload = {
        "type": "digest",
        "title": "Your Morning Digest is Ready",
        "body": digest_content[:200] + "..."
        if len(digest_content) > 200
        else digest_content,
        "data": {"user_id": user_id},
    }
    result = await send_push(apns_token, payload, user_id=user_id)
    _log_push_failure("digest", user_id, apns_token, result)
    return result


async def notify_grade_change(
    user_id: str, apns_token: str, ticker: str, old_grade: str, new_grade: str
):
    arrow = "⬆️" if GRADE_RANK.get(new_grade, 0) > GRADE_RANK.get(old_grade, 0) else "⬇️"
    payload = {
        "type": "grade_change",
        "title": f"{ticker} Grade Changed {arrow}",
        "body": f"{ticker} moved from {old_grade} to {new_grade}",
        "data": {
            "user_id": user_id,
            "ticker": ticker,
            "old_grade": old_grade,
            "new_grade": new_grade,
        },
    }
    result = await send_push(apns_token, payload, user_id=user_id)
    _log_push_failure("grade_change", user_id, apns_token, result)
    return result


async def notify_major_event(
    user_id: str, apns_token: str, ticker: str, event_title: str
):
    payload = {
        "type": "major_event",
        "title": f"Major Event: {ticker}",
        "body": event_title[:200],
        "data": {"user_id": user_id, "ticker": ticker},
    }
    result = await send_push(apns_token, payload, user_id=user_id)
    _log_push_failure("major_event", user_id, apns_token, result)
    return result


async def notify_portfolio_grade_change(
    user_id: str, apns_token: str, old_grade: str, new_grade: str
):
    payload = {
        "type": "portfolio_grade_change",
        "title": "Portfolio Grade Changed",
        "body": f"Your overall portfolio grade moved from {old_grade} to {new_grade}",
        "data": {
            "user_id": user_id,
            "old_grade": old_grade,
            "new_grade": new_grade,
        },
    }
    result = await send_push(apns_token, payload, user_id=user_id)
    _log_push_failure("portfolio_grade_change", user_id, apns_token, result)
    return result


async def notify_position_analysis_complete(
    user_id: str,
    apns_token: str,
    ticker: str,
    position_id: str,
    grade: str | None = None,
):
    if grade:
        body = f"{ticker} graded {grade} — now ready in your portfolio."
    else:
        body = f"{ticker} analysis complete — now ready in your portfolio."
    payload = {
        "type": "position_analysis",
        "title": f"{ticker} Analysis Complete",
        "body": body,
        "data": {
            "user_id": user_id,
            "ticker": ticker,
            "position_id": position_id,
            "grade": grade,
        },
    }
    result = await send_push(apns_token, payload, user_id=user_id)
    _log_push_failure("position_analysis", user_id, apns_token, result)
    return result
