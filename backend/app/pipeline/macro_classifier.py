import re
from typing import Optional
from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_object


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_ticker(value: str | None) -> str:
    return str(value or "").strip().upper()


def _is_valid_sector_name(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized and normalized not in {"unknown", "none", "null", "n/a"})


MACRO_THEMES = [
    "rate_policy",
    "inflation",
    "growth_recession",
    "geopolitics",
    "sector_specific",
    "credit_market",
    "currency",
    "commodities",
]

THEME_KEYWORDS = {
    "rate_policy": [
        "fed",
        "interest rate",
        "yield",
        "bond",
        "rate",
        "central bank",
        "monetary",
        "fomc",
        "basis points",
    ],
    "inflation": [
        "inflation",
        "cpi",
        "pce",
        "price",
        "cost",
        "pricing",
        "hot",
        "moderate",
        "tame",
    ],
    "growth_recession": [
        "gdp",
        "growth",
        "recession",
        "contraction",
        "expansion",
        "slowdown",
        "economy",
        "jobs",
        "unemployment",
    ],
    "geopolitics": [
        "china",
        "trade war",
        "tariff",
        "opec",
        "russia",
        "ukraine",
        "middle east",
        "sanctions",
        "export",
    ],
    "sector_specific": [
        "bank",
        "energy",
        "tech",
        "healthcare",
        "retail",
        "housing",
        "auto",
    ],
    "credit_market": [
        "credit",
        "spread",
        "high yield",
        "junk",
        "default",
        "leveraged",
        "debt",
    ],
    "currency": ["dollar", "yuan", "euro", "currency", "fx", "foreign exchange"],
    "commodities": [
        "oil",
        "gas",
        "crude",
        "gold",
        "silver",
        "copper",
        "commodity",
        "wheat",
    ],
}


def _detect_macro_themes(articles: list[dict]) -> list[dict]:
    detected = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        matched_themes = []
        for theme, keywords in THEME_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                matched_themes.append(theme)

        if matched_themes:
            detected.append(
                {
                    "title": article.get("title", ""),
                    "summary": article.get("summary", "")[:300],
                    "source": article.get("source"),
                    "published_at": article.get("published_at"),
                    "themes": matched_themes,
                }
            )
    return detected


SYSTEM_PROMPT = """You are a macro analyst writing a brief morning macro brief.

Given a list of overnight macro developments (news articles classified as macro-relevant), synthesize them into a clear structured brief.

Return strict JSON with this shape:
{{
  "overnight_macro": {{
    "headlines": ["list of 2-4 key headlines"],
    "themes": ["rate_policy", "growth_recession", "geopolitics"],  // up to 3 themes driving markets
    "brief": "2-3 sentence synthesis of what happened overnight and what it means for markets"
  }},
  "position_impacts": [
    {{
      "ticker": "NVDA",
      "macro_relevance": "confirms|challenges|neutral",
      "impact_summary": "one sentence on how macro affects this position"
    }}
  ],
  "what_matters_today": [
    {{
      "catalyst": "what is happening today (earnings, data release, Fed speaker, etc.)",
      "impacted_positions": ["NVDA", "AAPL"],
      "urgency": "high|medium|low"
    }}
  ]
}}

Rules:
- For themes, use exactly: rate_policy, inflation, growth_recession, geopolitics, sector_specific, credit_market, currency, commodities
- For position_impacts, include every holding provided exactly once
- For what_matters_today, focus on forward-looking catalysts: scheduled events, data releases, known earnings, policy decisions
- If no meaningful macro happened overnight, return empty headlines and brief: "No significant macro developments overnight."
- Be specific and factual. Do not speculate beyond what the headlines say.
- position_impacts should reference actual holdings provided, not generic tickers
- If macro read-through is weak for a holding, mark it neutral and say there is no clear overnight macro change
"""


SECTOR_SUMMARY_PROMPT = """You summarize overnight sector news for a morning portfolio digest.

Return strict JSON with this shape:
{
  "sector_overview": [
    {
      "sector": "technology",
      "brief": "1-2 sentence summary of what actually happened across the sector overnight",
      "headlines": []
    }
  ]
}

Rules:
- Only include the sectors provided by the user prompt
- Exclude empty, unknown, null, or none sectors
- The brief must synthesize the articles, not repeat or list titles
- Keep the tone calm, concise, and risk-focused
- headlines should be an empty array unless the prompt explicitly asks for them
"""


def _fallback_sector_brief(sector: str, articles: list[dict]) -> dict:
    article_count = len(articles)
    if not article_count:
        brief = f"No material overnight update was identified for {sector}."
    else:
        brief = f"Overnight {sector} coverage was active across {article_count} CNBC item(s), with the main developments concentrated in the sector rather than isolated to a single company headline."
    return {"sector": sector, "brief": brief, "headlines": []}


def _normalize_position_impacts(
    raw_impacts: list[dict], positions: list[dict]
) -> list[dict]:
    impact_map: dict[str, dict] = {}
    for item in raw_impacts or []:
        if not isinstance(item, dict):
            continue
        ticker = _normalize_ticker(item.get("ticker"))
        if not ticker:
            continue
        impact_map[ticker] = {
            "ticker": ticker,
            "macro_relevance": str(item.get("macro_relevance") or "neutral")
            .strip()
            .lower()
            or "neutral",
            "impact_summary": str(item.get("impact_summary") or "").strip(),
        }

    normalized = []
    for position in positions:
        ticker = _normalize_ticker(position.get("ticker"))
        if not ticker:
            continue
        impact = impact_map.get(ticker)
        if impact and impact.get("impact_summary"):
            normalized.append(impact)
            continue
        normalized.append(
            {
                "ticker": ticker,
                "macro_relevance": "neutral",
                "impact_summary": "No clear overnight macro read-through for this holding; keep the focus on company-specific developments unless new sector news broadens out.",
            }
        )
    return normalized


def _fallback_macro_brief(
    overnight_articles: list[dict], positions: list[dict]
) -> dict:
    themes_found = set()
    for article in overnight_articles:
        for theme in article.get("themes", []):
            themes_found.add(theme)

    headlines = [
        a.get("title", "")[:100] for a in overnight_articles[:4] if a.get("title")
    ]

    fallback_brief = "Overnight macro developments were limited. Markets appear calm with no significant policy shifts or economic surprises."
    if themes_found:
        fallback_brief = f"Overnight macro themes: {', '.join(sorted(themes_found))}. No major surprises."

    return {
        "overnight_macro": {
            "headlines": headlines or [],
            "themes": list(themes_found) if themes_found else [],
            "brief": fallback_brief,
        },
        "position_impacts": _normalize_position_impacts([], positions),
        "what_matters_today": [],
    }


async def summarize_sector_overview(
    sector_articles_by_name: dict[str, list[dict]],
) -> dict:
    valid_sectors = {
        str(sector).strip().lower(): articles
        for sector, articles in (sector_articles_by_name or {}).items()
        if _is_valid_sector_name(sector) and articles
    }
    if not valid_sectors:
        return {"sector_overview": []}

    sector_blocks = []
    for sector, articles in sorted(valid_sectors.items()):
        lines = [f"Sector: {sector}"]
        for article in articles[:6]:
            title = str(article.get("title") or "").strip()
            summary = _strip_html(str(article.get("summary") or "").strip())
            if title:
                lines.append(f"- {title}: {summary[:180]}")
        sector_blocks.append("\n".join(lines))

    try:
        result = chatcompletion_text(
            messages=[
                {"role": "system", "content": SECTOR_SUMMARY_PROMPT},
                {"role": "user", "content": "\n\n".join(sector_blocks)},
            ],
            temperature=0.1,
            max_tokens=900,
        )
        parsed = extract_json_object(result, {})
    except Exception:
        parsed = {}
    raw_overview = parsed.get("sector_overview") or []
    if isinstance(raw_overview, list):
        normalized = []
        seen = set()
        for item in raw_overview:
            if not isinstance(item, dict):
                continue
            sector = str(item.get("sector") or "").strip().lower()
            if (
                sector in seen
                or sector not in valid_sectors
                or not _is_valid_sector_name(sector)
            ):
                continue
            seen.add(sector)
            normalized.append(
                {
                    "sector": sector,
                    "brief": str(item.get("brief") or "").strip()
                    or _fallback_sector_brief(sector, valid_sectors[sector])["brief"],
                    "headlines": [],
                }
            )
        if normalized:
            return {"sector_overview": normalized}

    return {
        "sector_overview": [
            _fallback_sector_brief(sector, articles)
            for sector, articles in sorted(valid_sectors.items())
        ]
    }


async def classify_overnight_macro(
    overnight_articles: list[dict],
    positions: list[dict],
) -> dict:
    if not overnight_articles:
        return {
            "overnight_macro": {
                "headlines": [],
                "themes": [],
                "brief": "No overnight macro developments to report.",
            },
            "position_impacts": _normalize_position_impacts([], positions),
            "what_matters_today": [],
        }

    position_context = "\n".join(
        f"- {p.get('ticker', '')}: {p.get('archetype', 'unknown')} archetype"
        for p in positions
    )

    articles_text = "\n".join(
        f"- [{a.get('source', 'news')}] {a.get('title', '')}: {_strip_html(a.get('summary', ''))[:200]}"
        for a in overnight_articles[:10]
    )

    prompt = f"""Positions:
{position_context}

Overnight macro articles:
{articles_text}
"""

    try:
        result = chatcompletion_text(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            max_tokens=1000,
        )
        parsed = extract_json_object(result, {})
    except Exception:
        parsed = {}
    fallback = _fallback_macro_brief(overnight_articles, positions)

    parsed_impacts = parsed.get("position_impacts")
    if not isinstance(parsed_impacts, list):
        parsed_impacts = fallback["position_impacts"]

    return {
        "overnight_macro": parsed.get("overnight_macro") or fallback["overnight_macro"],
        "position_impacts": _normalize_position_impacts(parsed_impacts, positions),
        "what_matters_today": parsed.get("what_matters_today")
        or fallback["what_matters_today"],
    }


def filter_macro_articles(articles: list[dict]) -> list[dict]:
    return [
        a
        for a in articles
        if a.get("relevance", {}).get("event_type") in ["macro", "sector", "theme"]
    ]
