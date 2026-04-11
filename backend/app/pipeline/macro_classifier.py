from typing import Optional
from ..services.minimax import chatcompletion_text
from .analysis_utils import extract_json_object

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
- For position_impacts, only include positions that have meaningful macro sensitivity
- For what_matters_today, focus on forward-looking catalysts: scheduled events, data releases, known earnings, policy decisions
- If no meaningful macro happened overnight, return empty headlines and brief: "No significant macro developments overnight."
- Be specific and factual. Do not speculate beyond what the headlines say.
- position_impacts should reference actual holdings provided, not generic tickers
"""


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
        "position_impacts": [],
        "what_matters_today": [],
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
            "position_impacts": [],
            "what_matters_today": [],
        }

    position_context = "\n".join(
        f"- {p.get('ticker', '')}: {p.get('archetype', 'unknown')} archetype"
        for p in positions
    )

    articles_text = "\n".join(
        f"- [{a.get('source', 'news')}] {a.get('title', '')}: {a.get('summary', '')[:200]}"
        for a in overnight_articles[:10]
    )

    prompt = f"""Positions:
{position_context}

Overnight macro articles:
{articles_text}
"""

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,
        max_tokens=1000,
    )

    parsed = extract_json_object(result, {})
    fallback = _fallback_macro_brief(overnight_articles, positions)

    return {
        "overnight_macro": parsed.get("overnight_macro") or fallback["overnight_macro"],
        "position_impacts": parsed.get("position_impacts")
        or fallback["position_impacts"],
        "what_matters_today": parsed.get("what_matters_today")
        or fallback["what_matters_today"],
    }


def filter_macro_articles(articles: list[dict]) -> list[dict]:
    return [
        a
        for a in articles
        if a.get("relevance", {}).get("event_type") in ["macro", "sector", "theme"]
    ]
