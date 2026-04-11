from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_list

SYSTEM_PROMPT = """You are a relevance classifier for a portfolio risk app.

For each article below, determine if it's relevant to any of the given positions.

Positions:
{positions}

Articles:
{articles}

Return JSON array where each entry has:
- "article_index": 0-based index
- "relevant": true/false
- "affected_tickers": ["NVDA", "AAPL"] (if relevant)
- "event_type": "company_specific|macro|sector|theme|irrelevant"
- "why_it_matters": one sentence

Rules:
- If article mentions a held ticker by name or alias → relevant (company_specific)
- If macro/financial news matches position themes → relevant (macro/sector)
- Analyst downgrades/upgrades with price targets → minor, still relevant
- General market commentary with no specific tickers → irrelevant unless macro theme matches
- Only flag articles as relevant if there's a clear connection to held positions
"""


def _positions_text(positions: list[dict]) -> str:
    return "\n".join(
        f"- {p.get('ticker', '')}: {p.get('archetype', 'growth')} archetype"
        for p in positions
    )


def _articles_text(articles: list[dict]) -> str:
    result = []
    for i, article in enumerate(articles):
        title = article.get("title", "")
        summary = article.get("summary", "")[:300]
        result.append(f"[{i}] Title: {title}\n    Summary: {summary}")
    return "\n\n".join(result)


def _parse_batch_relevance(response_text: str, count: int) -> list[dict]:
    parsed = extract_json_list(response_text, None)
    if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
        return parsed
    if (
        isinstance(parsed, dict)
        and isinstance(parsed.get("results"), list)
        and all(isinstance(item, dict) for item in parsed["results"])
    ):
        return parsed["results"]

    print(
        f"[WARN] _parse_batch_relevance fallback triggered. Type: {type(parsed)}, Value preview: {str(parsed)[:200]}"
    )
    return [
        {
            "article_index": i,
            "relevant": False,
            "affected_tickers": [],
            "event_type": "irrelevant",
            "why_it_matters": "parse failed",
        }
        for i in range(count)
    ]


async def classify_relevance_batch(
    articles: list[dict], positions: list[dict], batch_size: int = 15
) -> list[dict]:
    if not articles or not positions:
        return []

    positions_text = _positions_text(positions)
    articles_text = _articles_text(articles)
    prompt = f"""Positions:
{positions_text}

Articles:
{articles_text}
"""
    try:
        result = await asyncio.to_thread(
            chatcompletion_text,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=8000,
        )
    except Exception as e:
        print(f"[ERROR] chatcompletion_text failed: {e}")
        return [
            {
                "article_index": i,
                "relevant": False,
                "affected_tickers": [],
                "event_type": "irrelevant",
                "why_it_matters": "LLM call failed",
                "article": articles[i],
            }
            for i in range(len(articles))
        ]

    parsed_results = _parse_batch_relevance(result, len(articles))
    output = []
    for idx, parsed in enumerate(parsed_results):
        output.append(
            {
                "article_index": idx,
                "relevant": parsed.get("relevant", False),
                "affected_tickers": [
                    str(t).upper()
                    for t in parsed.get("affected_tickers", [])
                    if str(t).strip()
                ],
                "event_type": parsed.get("event_type") or "irrelevant",
                "why_it_matters": parsed.get("why_it_matters") or "",
                "article": articles[idx],
            }
        )
    return output


async def classify_relevance(article: dict, positions: list[dict]) -> dict:
    results = await classify_relevance_batch([article], positions, batch_size=1)
    if results:
        r = results[0]
        return {
            "relevant": r["relevant"],
            "affected_tickers": r["affected_tickers"],
            "event_type": r["event_type"],
            "why_it_matters": r["why_it_matters"],
        }

    return {
        "relevant": False,
        "affected_tickers": [],
        "event_type": "irrelevant",
        "why_it_matters": "No classification result.",
    }
