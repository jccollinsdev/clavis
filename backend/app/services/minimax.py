import openai
import re
from ..config import get_settings
from .backfill_artifacts import record_llm_call

settings = get_settings()
DEFAULT_CHAT_TIMEOUT_SECONDS = 120

client = openai.OpenAI(
    api_key=settings.minimax_api_key, base_url=settings.minimax_base_url
)


def chatcompletion(messages: list, model: str = "MiniMax-M2.7", **kwargs):
    return client.chat.completions.create(model=model, messages=messages, **kwargs)


def chatcompletion_text(messages: list, model: str = "MiniMax-M2.7", **kwargs) -> str:
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 1000
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_CHAT_TIMEOUT_SECONDS

    import time

    start = time.perf_counter()
    response = None
    cleaned = ""
    error = None
    retryable_markers = (
        "high traffic",
        "rate limit",
        "too many requests",
        "overloaded",
        "temporarily unavailable",
        "503",
        "529",
    )
    try:
        delay = 0.8
        for attempt in range(3):
            try:
                response = chatcompletion(messages, model, **kwargs)
                msg = response.choices[0].message
                content = msg.content or ""
                cleaned = re.sub(
                    r"<think>.*?</think>", "", content, flags=re.DOTALL
                ).strip()
                return cleaned
            except Exception as exc:
                error = str(exc)
                if attempt < 2 and any(
                    marker in error.lower() for marker in retryable_markers
                ):
                    time.sleep(delay)
                    delay *= 2
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
