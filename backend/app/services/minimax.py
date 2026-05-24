from __future__ import annotations
import openai
import re
import threading
import time
from ..config import get_settings
from .backfill_artifacts import record_llm_call

settings = get_settings()
DEFAULT_CHAT_TIMEOUT_SECONDS = 120
_MINIMAX_THROTTLE_LOCK = threading.Lock()
_MINIMAX_NEXT_ALLOWED_AT = 0.0

client = openai.OpenAI(
    api_key=settings.minimax_api_key, base_url=settings.minimax_base_url
)


class MiniMaxAuthError(RuntimeError):
    pass


def chatcompletion(messages: list, model: str = "MiniMax-M2.7", **kwargs):
    return client.chat.completions.create(model=model, messages=messages, **kwargs)


def _is_minimax_auth_failure(exc: Exception) -> bool:
    error_text = str(exc).lower()
    return (
        "invalid api key" in error_text
        or "authorized_error" in error_text
        or "authenticationerror" in exc.__class__.__name__.lower()
    )


def _is_retryable_minimax_failure(exc: Exception) -> bool:
    error_text = str(exc).lower()
    return any(
        marker in error_text
        for marker in (
            "high traffic",
            "rate limit",
            "too many requests",
            "overloaded",
            "temporarily unavailable",
            "bad gateway",
            "502",
            "503",
            "529",
            "server disconnected",
        )
    )


def _wait_for_minimax_slot() -> None:
    global _MINIMAX_NEXT_ALLOWED_AT

    # Enforce a floor above 1s so concurrent workers never back-to-back MiniMax
    # requests within the same second, even if env config is lowered.
    min_interval_seconds = max(float(settings.minimax_min_interval_seconds), 1.05)
    if min_interval_seconds == 0:
        return

    while True:
        with _MINIMAX_THROTTLE_LOCK:
            now = time.monotonic()
            wait_seconds = _MINIMAX_NEXT_ALLOWED_AT - now
            if wait_seconds <= 0:
                _MINIMAX_NEXT_ALLOWED_AT = now + min_interval_seconds
                return
        time.sleep(wait_seconds)


def chatcompletion_text(messages: list, model: str = "MiniMax-M2.7", **kwargs) -> str:
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 1000
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_CHAT_TIMEOUT_SECONDS

    start = time.perf_counter()
    response = None
    cleaned = ""
    error = None
    try:
        delay = 0.8
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                _wait_for_minimax_slot()
                response = chatcompletion(messages, model, **kwargs)
                msg = response.choices[0].message
                content = msg.content or ""
                cleaned = re.sub(
                    r"<think>.*?</think>", "", content, flags=re.DOTALL
                ).strip()
                return cleaned
            except Exception as exc:
                error = str(exc)
                if _is_minimax_auth_failure(exc):
                    error = f"MiniMax auth failure: {error}"
                    raise MiniMaxAuthError(error) from exc
                if attempt < max_attempts - 1 and _is_retryable_minimax_failure(exc):
                    time.sleep(delay)
                    delay = min(delay * 2, 8.0)
                    continue
                raise
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        raw_response = ""
        if response is not None and getattr(response, "choices", None):
            raw_response = response.choices[0].message.content or ""
        record_llm_call(
            function_name="chatcompletion_text",
            model=model,
            messages=messages,
            kwargs=kwargs,
            response=cleaned or raw_response,
            error=error,
            duration_ms=duration_ms,
        )
