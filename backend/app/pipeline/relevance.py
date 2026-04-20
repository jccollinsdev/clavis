import asyncio
import re
from datetime import datetime, timezone

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
- Quote pages, chart pages, generic price pages, and low-information stock recaps are irrelevant even if they mention the ticker
"""


LOW_VALUE_TITLE_PATTERNS = [
    r"stock\s+price",
    r"quote\s*&\s*chart",
    r"price,\s*quote\s*&\s*chart",
    r"stock\s+underperforms",
    r"underperforms\s+.*competitors",
    r"stock\s+quote",
    r"holdings?\s+history",
    r"historical\s+holdings",
    r"stock\s+recap",
    r"market\s+recap",
    r"daily\s+stock\s+movers",
    r"top\s+stock\s+movers",
]


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _article_age_days(article: dict) -> float | None:
    parsed = _parse_timestamp(article.get("published_at"))
    if parsed is None:
        return None
    delta = datetime.now(timezone.utc) - parsed
    return max(0.0, delta.total_seconds() / 86400.0)


def _is_low_value_article(article: dict) -> tuple[bool, str]:
    raw = article.get("raw") or {}
    title = str(article.get("title") or "").strip().lower()
    summary = str(article.get("summary") or "").strip().lower()
    body = str(article.get("body") or "").strip().lower()
    scrape_status = (
        str(article.get("scrape_status") or raw.get("scrape_status") or "")
        .strip()
        .lower()
    )
    evidence_quality = str(article.get("evidence_quality") or "").strip().lower()
    resolved_url = (
        str(
            article.get("resolved_url")
            or raw.get("resolved_url")
            or article.get("source_url")
            or raw.get("source_url")
            or article.get("url")
            or raw.get("url")
            or ""
        )
        .strip()
        .lower()
    )
    content_source = (
        str(article.get("content_source") or raw.get("content_source") or "")
        .strip()
        .lower()
    )

    if (
        scrape_status == "google_wrapper"
        or "news.google.com" in resolved_url
        or "news.google.com" in content_source
    ) and evidence_quality in {"", "title_only", "headline_summary"}:
        return True, "Google wrapper page without article content"

    for pattern in LOW_VALUE_TITLE_PATTERNS:
        if re.search(pattern, title):
            return True, "Low-information quote or chart page"

    if (
        body
        == "comprehensive up-to-date news coverage, aggregated from sources all over the world by google news."
    ):
        return True, "Google wrapper page without article content"

    if (
        "no actual news, analysis, or actionable information" in summary
        or "no actual news, analysis, or actionable information" in body
    ):
        return True, "Low-information market data page"

    if (
        title
        and not body
        and any(
            marker in title
            for marker in (
                "quote",
                "chart",
                "recap",
                "holdings",
                "movers",
            )
        )
    ):
        return True, "Low-information market data page"

    age_days = _article_age_days(article)
    if age_days is not None and age_days > 10:
        return True, "Article is outside the recent evidence window"

    return False, ""


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


def _normalized_article_tickers(article: dict) -> set[str]:
    tickers: set[str] = set()
    for key in ("ticker_hints", "affected_tickers"):
        for ticker in article.get(key, []) or []:
            normalized = str(ticker).strip().upper()
            if normalized:
                tickers.add(normalized)
    ticker = str(article.get("ticker") or "").strip().upper()
    if ticker:
        tickers.add(ticker)
    return tickers


def _positions_for_articles(articles: list[dict], positions: list[dict]) -> list[dict]:
    article_tickers: set[str] = set()
    for article in articles:
        article_tickers.update(_normalized_article_tickers(article))

    if article_tickers:
        scoped = [
            position
            for position in positions
            if str(position.get("ticker", "")).strip().upper() in article_tickers
        ]
        if scoped:
            return scoped

    return positions[:20]


async def _classify_relevance_chunk(
    articles: list[dict], positions: list[dict]
) -> list[dict]:
    if not articles:
        return []

    deterministic_results = []
    llm_articles = []
    llm_index_map = []
    for index, article in enumerate(articles):
        is_low_value, reason = _is_low_value_article(article)
        if is_low_value:
            deterministic_results.append(
                {
                    "article_index": index,
                    "relevant": False,
                    "affected_tickers": [],
                    "event_type": "irrelevant",
                    "why_it_matters": reason,
                    "article": article,
                }
            )
            continue
        llm_index_map.append(index)
        llm_articles.append(article)

    if not llm_articles:
        return deterministic_results

    positions_text = _positions_text(_positions_for_articles(llm_articles, positions))
    articles_text = _articles_text(llm_articles)
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
            max_tokens=2500,
        )
    except Exception as e:
        print(f"[ERROR] chatcompletion_text failed: {e}")
        return [
            {
                "article_index": llm_index_map[i],
                "relevant": False,
                "affected_tickers": [],
                "event_type": "irrelevant",
                "why_it_matters": "LLM call failed",
                "article": llm_articles[i],
            }
            for i in range(len(llm_articles))
        ]

    parsed_results = _parse_batch_relevance(result, len(llm_articles))
    output = list(deterministic_results)
    for idx, parsed in enumerate(parsed_results):
        article = llm_articles[idx]
        is_low_value, reason = _is_low_value_article(article)
        output.append(
            {
                "article_index": llm_index_map[idx],
                "relevant": False if is_low_value else parsed.get("relevant", False),
                "affected_tickers": [
                    str(t).upper()
                    for t in parsed.get("affected_tickers", [])
                    if str(t).strip()
                ]
                if not is_low_value
                else [],
                "event_type": (parsed.get("event_type") or "irrelevant")
                if not is_low_value
                else "irrelevant",
                "why_it_matters": reason
                if is_low_value
                else (parsed.get("why_it_matters") or ""),
                "article": article,
            }
        )
    return sorted(output, key=lambda item: item.get("article_index", 0))


async def classify_relevance_batch(
    articles: list[dict], positions: list[dict], batch_size: int = 15
) -> list[dict]:
    if not articles or not positions:
        return []

    normalized_batch_size = max(1, batch_size)
    output: list[dict] = []
    for start in range(0, len(articles), normalized_batch_size):
        chunk = articles[start : start + normalized_batch_size]
        chunk_results = await _classify_relevance_chunk(chunk, positions)
        for idx, item in enumerate(chunk_results):
            item["article_index"] = start + idx
            item["article"] = articles[start + idx]
            output.append(item)

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
