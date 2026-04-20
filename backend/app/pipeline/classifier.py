from app.services.minimax import chatcompletion_text
from .analysis_utils import extract_json_list, extract_json_object


SYSTEM_PROMPT = """You are a financial event classifier for a portfolio risk app.

Classify each news item conservatively.

MAJOR = earnings results or surprises, guidance raises/cuts, material corporate announcements, new product launches, strategy shifts, M&A, CEO/CFO resignations or appointments tied to change, regulatory actions, SEC/DOJ investigations, bankruptcy, financing crises, major recalls, and other events that can materially change fundamentals or valuation.

MINOR = analyst upgrades/downgrades, price target changes, routine economic data, conference appearances, commentary, secondary mentions, and general market chatter without a material new catalyst.

Rules:
- If the company itself is announcing a material action, prefer MAJOR.
- If it is only analysis, commentary, or a rating change, prefer MINOR.
- When uncertain, choose MINOR.

Return exact JSON with:
{{
  "significance": "major|minor",
  "event_type": "earnings|macro|management|mna|regulatory|product|financing|sector|other",
  "why_it_matters": "one sentence",
  "confidence": 0.0-1.0
}}"""


MINOR_KEYWORDS = [
    "analyst",
    "rating",
    "price target",
    "upgrade",
    "downgrade",
    "maintain",
    "pt ",
    "price target",
    "raised price target",
    "lowered price target",
    "quarterly",
    "earnings preview",
    "watching",
    "market perform",
    "sector perform",
    "equal weight",
    "neutral rating",
    "buy rating",
    "hold rating",
    "outperform",
    "underperform",
    "market perform",
    "conference",
    "upcoming",
    "event preview",
    "data preview",
]
MAJOR_KEYWORDS = [
    "earnings",
    "missed",
    "beat",
    "guidance",
    "raised guidance",
    "lowered guidance",
    "fed",
    "federal reserve",
    "fomc",
    "ceo",
    "cfo",
    "resign",
    "departure",
    "appointed",
    "acquisition",
    "merger",
    "acquire",
    "buyout",
    "takeover",
    "regulatory",
    "sec",
    "doj",
    "investigation",
    "lawsuit",
    "settlement",
    "bankruptcy",
    "chapter 11",
    "reorganization",
    "recall",
    "safety recall",
    "product recall",
    "geopolitical",
    "sanctions",
    "tariff",
    "trade war",
    "financing",
    "new product",
    "product launch",
    "launches new",
    "introduces new",
    "unveils new",
]


def classify_significance_keyword(title: str, summary: str) -> dict | None:
    text = f"{title} {summary}".lower()
    for kw in MAJOR_KEYWORDS:
        if kw.lower() in text:
            return {
                "significance": "major",
                "event_type": "other",
                "why_it_matters": "Keyword detected major event",
                "confidence": 0.95,
                "rule": "keyword",
            }
    for kw in MINOR_KEYWORDS:
        if kw.lower() in text:
            return {
                "significance": "minor",
                "event_type": "other",
                "why_it_matters": "Keyword detected routine minor event",
                "confidence": 0.85,
                "rule": "keyword",
            }
    return None


async def classify_significance(title: str, summary: str, body: str = "") -> dict:
    keyword_result = classify_significance_keyword(title, summary)
    if keyword_result:
        return keyword_result

    prompt = f"News: {title}. {summary[:500]}\n\nBody: {body[:1000]}"

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=400,
    )

    parsed = extract_json_object(result, {})
    significance = parsed.get("significance", "minor")
    if significance not in {"major", "minor"}:
        significance = "minor"

    return {
        "significance": significance,
        "event_type": parsed.get("event_type") or "other",
        "why_it_matters": parsed.get("why_it_matters")
        or "Classification evidence unavailable.",
        "confidence": float(parsed.get("confidence") or 0.5),
    }


async def classify_significance_batch(
    articles: list[dict],
) -> list[dict]:
    if not articles:
        return []

    results = []
    for article in articles:
        title = article.get("title", "")
        summary = article.get("summary", "")
        body = article.get("body", "")
        keyword_result = classify_significance_keyword(title, summary)
        if keyword_result:
            results.append(keyword_result)
        else:
            results.append(None)

    uncached_indices = [i for i, r in enumerate(results) if r is None]

    if not uncached_indices:
        return results

    chunk_size = 8
    for chunk_start in range(0, len(uncached_indices), chunk_size):
        chunk_indices = uncached_indices[chunk_start : chunk_start + chunk_size]
        articles_text = []
        for local_idx, article_idx in enumerate(chunk_indices):
            article = articles[article_idx]
            title = article.get("title", "")[:500]
            summary = article.get("summary", "")[:500]
            body = article.get("body", "")[:1000]
            articles_text.append(
                f"[{local_idx}] Title: {title}\nSummary: {summary}\nBody: {body}"
            )

        prompt = "\n\n".join(articles_text)

        response = chatcompletion_text(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1200,
        )

        parsed = extract_json_list(response, None)
        if isinstance(parsed, list):
            for local_idx, article_idx in enumerate(chunk_indices):
                if local_idx < len(parsed):
                    p = parsed[local_idx]
                    significance = p.get("significance", "minor")
                    if significance not in {"major", "minor"}:
                        significance = "minor"
                    results[article_idx] = {
                        "significance": significance,
                        "event_type": p.get("event_type") or "other",
                        "why_it_matters": p.get("why_it_matters")
                        or "Classification evidence unavailable.",
                        "confidence": float(p.get("confidence") or 0.5),
                    }
                else:
                    results[article_idx] = {
                        "significance": "minor",
                        "event_type": "other",
                        "why_it_matters": "Classification unavailable.",
                        "confidence": 0.3,
                    }
            continue

        for article_idx in chunk_indices:
            results[article_idx] = {
                "significance": "minor",
                "event_type": "other",
                "why_it_matters": "Classification parse failed.",
                "confidence": 0.3,
            }

    return results
