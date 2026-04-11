import openai
import re
from ..config import get_settings

settings = get_settings()

client = openai.OpenAI(
    api_key=settings.minimax_api_key, base_url=settings.minimax_base_url
)


def chatcompletion(messages: list, model: str = "MiniMax-M2.7", **kwargs):
    return client.chat.completions.create(model=model, messages=messages, **kwargs)


def chatcompletion_text(messages: list, model: str = "MiniMax-M2.7", **kwargs) -> str:
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 1000

    response = chatcompletion(messages, model, **kwargs)
    msg = response.choices[0].message

    content = msg.content or ""

    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)

    return content.strip()
