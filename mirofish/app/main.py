import os

from fastapi import FastAPI
from pydantic import BaseModel
import openai


app = FastAPI(title="Clavis MiroFish Adapter", version="1.0.0")

client = openai.OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY", ""),
    base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1"),
)


class AnalyzeRequest(BaseModel):
    news: dict
    position: dict


def _chatcompletion_text(messages: list, model: str = "MiniMax-M2.7", **kwargs) -> str:
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 1200
    response = client.chat.completions.create(model=model, messages=messages, **kwargs)
    content = response.choices[0].message.content or ""
    return content.strip()


SYSTEM_PROMPT = """You are the MiroFish major-event analysis engine for Clavis.

Return strict JSON:
{
  "analysis_text": "3-6 sentence major event analysis",
  "impact_horizon": "immediate|near_term|long_term",
  "risk_direction": "improving|neutral|worsening",
  "confidence": 0.0-1.0,
  "scenario_summary": "one sentence",
  "key_implications": ["...", "..."],
  "recommended_followups": ["...", "..."],
  "provider": "mirofish"
}

Focus on event severity, downside risk, and position-specific implications.
"""


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    news = request.news
    position = request.position
    prompt = f"""Major event:
Title: {news.get("title", "")}
Summary: {news.get("summary", "")}
Body: {news.get("body", "")[:2000]}
Source: {news.get("source", "")}

Position:
- Ticker: {position.get("ticker", "")}
- Shares: {position.get("shares", 0)}
- Purchase price: {position.get("purchase_price", 0)}
- Archetype: {position.get("archetype", "unknown")}
- Inferred labels: {", ".join(position.get("inferred_labels", []))}
"""

    try:
        result = _chatcompletion_text(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except Exception:
        result = ""

    import json
    import re

    parsed = None
    try:
        parsed = json.loads(result)
    except Exception:
        match = re.search(r"\{.*\}", result, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = None

    if not isinstance(parsed, dict):
        parsed = {
            "analysis_text": f"{news.get('title', 'Major event')} introduces meaningful uncertainty for {position.get('ticker', 'this holding')}. The event should be treated as a material risk catalyst until management response and follow-on reporting provide more clarity.",
            "impact_horizon": "near_term",
            "risk_direction": "worsening",
            "confidence": 0.55,
            "scenario_summary": "Major event fallback from local MiroFish adapter.",
            "key_implications": ["Validate the durability of the core thesis against this event."],
            "recommended_followups": ["Review management commentary, filings, and follow-on reporting."],
            "provider": "mirofish",
        }

    parsed["provider"] = "mirofish"
    return parsed
