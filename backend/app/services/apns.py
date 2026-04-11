import asyncio
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from aioapns import APNs, NotificationRequest, PushType

from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

NON_RETRYABLE_REASONS = {
    "BadDeviceToken",
    "DeviceTokenNotForTopic",
    "Unregistered",
    "TopicDisallowed",
    "BadTopic",
    "MissingDeviceToken",
}
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass
class PushDeliveryResult:
    success: bool
    reason: str | None = None
    status_code: int | None = None
    retryable: bool = False
    attempt_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _token_fingerprint(token: str) -> str:
    if len(token) <= 10:
        return token
    return f"{token[:6]}...{token[-4:]}"


def validate_apns_configuration() -> dict:
    issues = []

    if not settings.apns_key_id:
        issues.append("APNS_KEY_ID is missing")
    if not settings.apns_team_id:
        issues.append("APNS_TEAM_ID is missing")
    if not settings.apns_bundle_id:
        issues.append("APNS_BUNDLE_ID is missing")
    if not settings.apns_key_path:
        issues.append("APNS_KEY_PATH is missing")
    elif not Path(settings.apns_key_path).exists():
        issues.append(f"APNS key file not found at {settings.apns_key_path}")

    return {"configured": not issues, "issues": issues}


def _build_client() -> APNs:
    return APNs(
        key_path=settings.apns_key_path,
        key_id=settings.apns_key_id,
        team_id=settings.apns_team_id,
        topic=settings.apns_bundle_id,
    )


def _build_notification(token: str, payload: dict) -> NotificationRequest:
    return NotificationRequest(
        device_token=token,
        message={
            "aps": {
                "alert": {
                    "title": payload.get("title", "Clavynx Update"),
                    "body": payload.get("body", ""),
                },
                "sound": "default",
            },
            "type": payload.get("type", "digest"),
            "data": payload.get("data", {}),
        },
        push_type=PushType.ALERT,
    )


def _extract_result_details(result) -> tuple[int | None, str | None]:
    status_code = (
        getattr(result, "status", None)
        or getattr(result, "status_code", None)
        or getattr(result, "code", None)
    )
    reason = (
        getattr(result, "description", None)
        or getattr(result, "reason", None)
        or getattr(result, "error", None)
    )
    if reason is not None:
        reason = str(reason)
    return status_code, reason


def _is_retryable_result(status_code: int | None, reason: str | None) -> bool:
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    if reason in NON_RETRYABLE_REASONS:
        return False
    return False


def _is_retryable_exception(exc: Exception) -> bool:
    return isinstance(exc, (asyncio.TimeoutError, ConnectionError, OSError))


async def send_push(
    token: str,
    payload: dict,
    *,
    user_id: str | None = None,
    max_attempts: int = 3,
) -> PushDeliveryResult:
    config_state = validate_apns_configuration()
    if not config_state["configured"]:
        logger.warning(
            "Push skipped because APNs is not configured",
            extra={"user_id": user_id, "issues": config_state["issues"]},
        )
        return PushDeliveryResult(
            success=False,
            reason="APNs is not configured",
            retryable=False,
            attempt_count=0,
        )

    client = _build_client()
    notification = _build_notification(token, payload)
    fingerprint = _token_fingerprint(token)

    for attempt in range(1, max_attempts + 1):
        try:
            result = await asyncio.wait_for(
                client.send_notification(notification), timeout=10.0
            )
            if getattr(result, "is_success", False):
                return PushDeliveryResult(success=True, attempt_count=attempt)

            status_code, reason = _extract_result_details(result)
            retryable = _is_retryable_result(status_code, reason)
            logger.warning(
                "Push delivery rejected by APNs",
                extra={
                    "user_id": user_id,
                    "token": fingerprint,
                    "attempt": attempt,
                    "status_code": status_code,
                    "reason": reason,
                    "retryable": retryable,
                },
            )
            if not retryable or attempt == max_attempts:
                return PushDeliveryResult(
                    success=False,
                    reason=reason or "APNs rejected the notification",
                    status_code=status_code,
                    retryable=retryable,
                    attempt_count=attempt,
                )
        except Exception as exc:
            retryable = _is_retryable_exception(exc)
            logger.warning(
                "Push delivery failed before APNs success response",
                extra={
                    "user_id": user_id,
                    "token": fingerprint,
                    "attempt": attempt,
                    "error": str(exc),
                    "retryable": retryable,
                },
            )
            if not retryable or attempt == max_attempts:
                return PushDeliveryResult(
                    success=False,
                    reason=str(exc),
                    retryable=retryable,
                    attempt_count=attempt,
                )

        await asyncio.sleep(2 ** (attempt - 1))

    return PushDeliveryResult(
        success=False,
        reason="Push delivery failed after retries",
        retryable=False,
        attempt_count=max_attempts,
    )
