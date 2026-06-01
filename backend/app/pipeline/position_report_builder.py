from __future__ import annotations
import re
from datetime import datetime
from typing import Any

from ..services.minimax import chatcompletion_text
from .analysis_utils import (
    extract_json_list,
    extract_json_object,
    sanitize_public_analysis_text,
    sanitize_text_field,
)


SYSTEM_PROMPT = """You are a downside risk rater writing a concise rating for a self-directed investor. Your job is to synthesize what the evidence means, not catalog what articles exist.

Return strict JSON with this shape:
{{
  "summary": "1-2 sentence summary: state the dominant risk force, acknowledge counter-evidence briefly, and identify what would change the rating",
  "long_report": "3-6 sentence detailed report that develops the rating with specific evidence, resolves contradictions rather than listing them, and closes with what could materially shift the rating",
  "methodology": "brief explanation of the evidence used",
  "top_risks": ["risk 1", "risk 2", "risk 3"],
  "watch_items": ["risk driver 1", "risk driver 2"],
  "risk_context": [
    {{
      "macro_event": "description of macro development",
      "rating_impact": "supports|contradicts|neutral",
      "reasoning": "one sentence explaining why"
    }}
  ]
}}

Writing rules:
1. Lead with the dominant narrative — what is the most important force acting on this position? Do not start by describing what articles exist or what the data says.
2. If positive and negative evidence compete, resolve the tension: explain which force matters more and why. Do not just list both sides and leave it to the reader.
3. If strong headlines coexist with structural risk (e.g., earnings beat but valuation is stretched, revenue growth but macro pressure), explain why the structural factor can outweigh the headline.
4. Close with what would change the rating — a specific catalyst, resolution, or development, not a generic "watch for developments."
5. Write concise risk assessment language — direct, specific, grounded. Not a news summary, not a process description.

Forbidden: internal evidence labels (full_body, title_only, headline_summary), scoring methodology references, "the model", "recent event flow is [stance]", "N relevant items in this cycle", implementation jargon, "thesis", "positive momentum", "macro headwinds", "provisional", "current read", "sentiment", "confirms", "coverage", "monitor/recheck", "research", "analyst", "confidence" (as model uncertainty), "watch" (use "risk driver" instead).

CRITICAL - Macro as Risk Context:
- For risk_context, assess whether any macro context supports, contradicts, or is neutral to this position's risk profile
- If the position has no clear setup, use "neutral" for rating_impact
- Only include risk_context entries for macro events that actually relate to this position's sector/theme
- If no relevant macro context exists, omit risk_context array entirely (do not include empty array)
"""


_DRIVER_THEME_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("regulatory_risk", ("sec", "ftc", "doj", "antitrust", "lawsuit", "litigation", "subpoena", "probe", "regulation", "regulatory", "fine", "settlement", "patent")),
    ("earnings_risk", ("earnings", "eps", "quarter", "q1", "q2", "q3", "q4", "results", "beat", "miss", "guidance", "outlook")),
    ("guidance_risk", ("guide", "guidance", "outlook", "forecast", "cut guidance", "raise guidance")),
    ("margin_risk", ("margin", "gross margin", "operating margin", "pricing pressure", "pricing power", "compression")),
    ("competition_risk", ("competition", "competitor", "market share", "share loss", "rivalry", "undercut", "pricing war")),
    ("demand_risk", ("demand", "slowdown", "orders", "backlog", "bookings", "inventory", "channel checks", "weak demand")),
    ("macro_risk", ("rates", "inflation", "fed", "treasury", "yields", "recession", "dollar", "tariffs", "china", "geopolitic", "credit", "macro")),
    ("leverage_risk", ("debt", "leverage", "refinancing", "covenant", "liquidity", "cash burn", "maturity", "distress", "bankruptcy")),
    ("liquidity_risk", ("liquidity", "cash", "funding", "runway", "dilution", "financing")),
    ("volatility_risk", ("volatility", "gap", "breakout", "breakdown", "momentum")),
    ("technical_risk", ("resistance", "support", "chart", "technical", "overbought", "oversold")),
    ("execution_risk", ("execution", "delay", "ramp", "rollout", "integration", "production", "supply chain")),
    ("concentration_risk", ("concentration", "single customer", "customer concentration", "dependency")),
    ("product_risk", ("launch", "defect", "recall", "quality", "bug", "adoption", "security issue")),
    ("valuation_risk", ("valuation", "multiple", "stretched", "expensive", "rerate", "overvalued", "premium")),
]

_DRIVER_THEME_PRIORITY = {theme: idx for idx, (theme, _keywords) in enumerate(_DRIVER_THEME_RULES)}

_THEME_DRIVER_TITLES: dict[tuple[str, str], str] = {
    ("regulatory_risk", "negative"): "Regulatory and legal exposure is rising",
    ("regulatory_risk", "positive"): "Regulatory overhang is clearing",
    ("regulatory_risk", "neutral"): "Regulatory situation remains uncertain",
    ("earnings_risk", "negative"): "Earnings risk is elevated",
    ("earnings_risk", "positive"): "Earnings trajectory is improving",
    ("earnings_risk", "neutral"): "Earnings trajectory is uncertain",
    ("margin_risk", "negative"): "Margin pressure is increasing",
    ("margin_risk", "positive"): "Margin recovery is under way",
    ("margin_risk", "neutral"): "Margin outlook remains uncertain",
    ("growth_risk", "negative"): "Growth momentum is slowing",
    ("growth_risk", "positive"): "Growth momentum is accelerating",
    ("growth_risk", "neutral"): "Growth trajectory is uncertain",
    ("macro_risk", "negative"): "Macro headwinds are weighing on the outlook",
    ("macro_risk", "positive"): "Macro tailwinds are supporting the near-term outlook",
    ("macro_risk", "neutral"): "Macro environment remains in flux",
    ("leverage_risk", "negative"): "Debt load and leverage risk are concerns",
    ("leverage_risk", "positive"): "Balance sheet is improving",
    ("leverage_risk", "neutral"): "Leverage position is stable",
    ("liquidity_risk", "negative"): "Liquidity runway is tightening",
    ("liquidity_risk", "positive"): "Cash position is strengthening",
    ("liquidity_risk", "neutral"): "Liquidity position is adequate",
    ("technical_risk", "negative"): "Technical structure is breaking down",
    ("technical_risk", "positive"): "Technical setup is constructive",
    ("technical_risk", "neutral"): "Technical picture is neutral",
    ("execution_risk", "negative"): "Execution risk is elevated",
    ("execution_risk", "positive"): "Execution momentum is improving",
    ("execution_risk", "neutral"): "Execution results are inconsistent",
    ("valuation_risk", "negative"): "Valuation is stretched relative to fundamentals",
    ("valuation_risk", "positive"): "Valuation has de-risked materially",
    ("valuation_risk", "neutral"): "Valuation is in line with peers",
    ("competitive_risk", "negative"): "Competitive pressure is intensifying",
    ("competitive_risk", "positive"): "Competitive position is strengthening",
    ("competitive_risk", "neutral"): "Competitive dynamics are stable",
    ("revenue_risk", "negative"): "Revenue growth is decelerating",
    ("revenue_risk", "positive"): "Revenue growth is accelerating",
    ("revenue_risk", "neutral"): "Revenue trajectory is uncertain",
    # Additional themes present in _DRIVER_THEME_RULES
    ("guidance_risk", "negative"): "Guidance has been cut, raising near-term earnings risk",
    ("guidance_risk", "positive"): "Guidance raised above consensus expectations",
    ("guidance_risk", "neutral"): "Forward guidance is in line with street expectations",
    ("competition_risk", "negative"): "Competitive pressure is intensifying",
    ("competition_risk", "positive"): "Competitive position is strengthening",
    ("competition_risk", "neutral"): "Competitive dynamics are stable",
    ("demand_risk", "negative"): "Demand signals are weakening",
    ("demand_risk", "positive"): "Demand signals are strengthening",
    ("demand_risk", "neutral"): "Demand trajectory is uncertain",
    ("volatility_risk", "negative"): "Price volatility is elevated",
    ("volatility_risk", "positive"): "Price action is stabilizing",
    ("volatility_risk", "neutral"): "Volatility is in line with sector norms",
}

_THEME_DRIVER_DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("regulatory_risk", "negative"): "Active investigations, fines, or policy changes are creating legal cost exposure that could compress margins and delay strategic plans.",
    ("regulatory_risk", "positive"): "Regulatory clarity or approvals are removing a key overhang, directly reducing the risk premium embedded in the stock.",
    ("regulatory_risk", "neutral"): "Pending regulatory outcomes could shift materially in either direction, keeping uncertainty elevated in the risk premium.",
    ("earnings_risk", "negative"): "Guidance cuts or consensus estimate reductions signal near-term earnings pressure that typically precedes multiple contraction.",
    ("earnings_risk", "positive"): "Earnings beats or upward guidance revisions are reducing near-term uncertainty and supporting multiple expansion.",
    ("earnings_risk", "neutral"): "Earnings are roughly in line with expectations, providing little catalyst in either direction.",
    ("margin_risk", "negative"): "Rising input costs, pricing pressure, or mix shift are squeezing gross margins, directly reducing near-term earnings power.",
    ("margin_risk", "positive"): "Cost discipline or improved pricing is expanding operating margins, lifting earnings power ahead of street expectations.",
    ("margin_risk", "neutral"): "Margin trajectory is stable but offers no near-term catalyst to drive meaningful earnings upside.",
    ("growth_risk", "negative"): "Decelerating revenue or unit growth is reducing the premium multiple investors assign to future cash flows.",
    ("growth_risk", "positive"): "Accelerating growth is expanding the addressable market story and supporting a higher forward earnings multiple.",
    ("growth_risk", "neutral"): "Growth is steady and in line with expectations, leaving the risk-reward roughly unchanged.",
    ("macro_risk", "negative"): "Rate sensitivity, currency exposure, or economic softness are creating top-line headwinds that pressure earnings estimates.",
    ("macro_risk", "positive"): "Favorable macro conditions — rate cuts, stronger consumer spending, or favorable currency — are providing a direct tailwind to earnings.",
    ("macro_risk", "neutral"): "Macro crosscurrents are partially offsetting each other, leaving near-term sector direction unclear.",
    ("leverage_risk", "negative"): "Elevated debt levels raise refinancing risk and limit financial flexibility, increasing the cost of capital for the business.",
    ("leverage_risk", "positive"): "Debt paydown or improved interest service ratios are lowering financial risk and expanding the investor base who can own the stock.",
    ("leverage_risk", "neutral"): "Current leverage is manageable but leaves limited room to absorb a revenue shortfall without covenant risk.",
    ("liquidity_risk", "negative"): "Tightening cash runway or widening credit spreads are raising the probability of a dilutive equity raise.",
    ("liquidity_risk", "positive"): "A strengthened cash position or renewed credit facility reduces funding risk and supports sustained reinvestment.",
    ("liquidity_risk", "neutral"): "Liquidity is sufficient for near-term operations but provides no meaningful buffer beyond 12 months.",
    ("technical_risk", "negative"): "Price action is showing distribution with volume — a technical signal that institutional sellers are actively reducing exposure.",
    ("technical_risk", "positive"): "Price structure and relative strength suggest accumulation, which often precedes fundamental re-rating catalysts.",
    ("technical_risk", "neutral"): "The chart is range-bound with no clear directional signal from price action or relative momentum.",
    ("execution_risk", "negative"): "Product launches, integrations, or ramp timelines are slipping, creating downside risk to consensus earnings estimates.",
    ("execution_risk", "positive"): "On-time delivery and improving operational metrics are reducing execution uncertainty embedded in the discount rate.",
    ("execution_risk", "neutral"): "Some initiatives are on track while others face delays, leaving the near-term earnings picture uncertain.",
    ("valuation_risk", "negative"): "The current multiple prices in near-perfect execution; any earnings miss or guidance cut would cause outsized multiple compression.",
    ("valuation_risk", "positive"): "After a material pullback the stock now trades at a discount to intrinsic value, improving the asymmetric risk-reward.",
    ("valuation_risk", "neutral"): "Valuation is in line with peers and growth expectations, leaving the stock a hold until a re-rating catalyst emerges.",
    ("competitive_risk", "negative"): "New entrants or feature parity from incumbents are eroding pricing power and threatening market share.",
    ("competitive_risk", "positive"): "Widening product advantages are enabling pricing power and share gains that should flow into operating leverage.",
    ("competitive_risk", "neutral"): "The competitive landscape is stable with no near-term threat to share, but also no clear path to significant share gain.",
    ("revenue_risk", "negative"): "Revenue growth is decelerating faster than the market expects, putting consensus estimates at downside risk.",
    ("revenue_risk", "positive"): "Accelerating revenue driven by new products or geographies is providing an upward estimate revision catalyst.",
    ("revenue_risk", "neutral"): "Revenue is growing within the range of expectations, offering no near-term earnings surprise potential.",
    # Additional themes present in _DRIVER_THEME_RULES
    ("guidance_risk", "negative"): "A guidance cut signals management sees near-term headwinds, which typically triggers consensus estimate reductions and multiple contraction.",
    ("guidance_risk", "positive"): "Raised guidance reduces near-term uncertainty and is often a leading indicator of further upward estimate revisions.",
    ("guidance_risk", "neutral"): "In-line guidance removes a near-term catalyst in either direction, leaving the rating dependent on longer-term execution.",
    ("competition_risk", "negative"): "New entrants or feature parity from incumbents are eroding pricing power and threatening market share.",
    ("competition_risk", "positive"): "Widening product advantages are enabling pricing power and share gains that should flow into operating leverage.",
    ("competition_risk", "neutral"): "The competitive landscape is stable with no near-term threat to share, but also no clear path to significant share gain.",
    ("demand_risk", "negative"): "Softening order flow or inventory build-up is creating near-term revenue pressure and raising the risk of an earnings miss.",
    ("demand_risk", "positive"): "Strengthening demand signals point to revenue upside and could support upward estimate revisions.",
    ("demand_risk", "neutral"): "Demand signals are steady but not strong enough to drive a material change in the near-term revenue outlook.",
    ("volatility_risk", "negative"): "Elevated price volatility is increasing short-term risk and may signal uncertainty about near-term fundamentals.",
    ("volatility_risk", "positive"): "Declining volatility suggests the market is becoming more confident in the near-term outlook.",
    ("volatility_risk", "neutral"): "Price action is choppy but within normal bounds, offering no clear directional signal.",
}

_NEGATIVE_DIRECTION_MARKERS = (
    "downgrade",
    "miss",
    "cut",
    "pressure",
    "probe",
    "lawsuit",
    "delay",
    "slowdown",
    "resistance",
    "risk",
    "weak",
    "compression",
    "competition",
    "worsen",
    "decline",
    "getting ahead of reality",
    "stretched",
    "overvalued",
    "expensive",
    "too rich",
    "premium to peers",
    "pricing in",
    "multiple compression",
)

_POSITIVE_DIRECTION_MARKERS = (
    "upgrade",
    "beat",
    "raise",
    "resolved",
    "approved",
    "launch",
    "expansion",
    "improve",
    "strength",
    "support",
    "tailwind",
)

_GENERIC_DRIVER_MARKERS = (
    "balanced",
    "mixed",
    "watch",
    "monitor",
    "research",
    "analyst",
    "coverage",
    "current read",
    "thesis",
    "model",
    "fallback",
    "limited data",
    "no single force",
    "nothing urgent",
)

_RSS_HEADLINE_SUFFIX_RE = re.compile(r"\s+-\s+[A-Z][A-Za-z .&]+$")

_THEME_DRIVER_SUBJECTS: dict[str, str] = {
    "regulatory_risk": "Regulatory pressure",
    "earnings_risk": "Earnings risk",
    "guidance_risk": "Guidance",
    "margin_risk": "Margins",
    "growth_risk": "Growth",
    "macro_risk": "Macro pressure",
    "leverage_risk": "Leverage",
    "liquidity_risk": "Liquidity",
    "technical_risk": "Technical setup",
    "execution_risk": "Execution risk",
    "valuation_risk": "Valuation",
    "competitive_risk": "Competitive pressure",
    "revenue_risk": "Revenue trend",
    "competition_risk": "Competitive pressure",
    "demand_risk": "Demand",
    "volatility_risk": "Volatility",
    "concentration_risk": "Customer concentration",
    "product_risk": "Product risk",
}

_THEME_DRIVER_PHRASES: dict[str, dict[str, str]] = {
    "negative": {
        "regulatory_risk": "is intensifying",
        "earnings_risk": "is deteriorating",
        "guidance_risk": "is moving lower",
        "margin_risk": "are compressing",
        "growth_risk": "is slowing",
        "macro_risk": "is building",
        "leverage_risk": "is elevated",
        "liquidity_risk": "is tightening",
        "technical_risk": "is weakening",
        "execution_risk": "is rising",
        "valuation_risk": "is stretched",
        "competitive_risk": "is intensifying",
        "revenue_risk": "is decelerating",
        "competition_risk": "is intensifying",
        "demand_risk": "is weakening",
        "volatility_risk": "is elevated",
        "concentration_risk": "is elevated",
        "product_risk": "is increasing",
    },
    "positive": {
        "regulatory_risk": "is easing",
        "earnings_risk": "is improving",
        "guidance_risk": "is strengthening",
        "margin_risk": "are recovering",
        "growth_risk": "is accelerating",
        "macro_risk": "is easing",
        "leverage_risk": "is improving",
        "liquidity_risk": "is improving",
        "technical_risk": "is improving",
        "execution_risk": "is improving",
        "valuation_risk": "has de-risked",
        "competitive_risk": "is improving",
        "revenue_risk": "is accelerating",
        "competition_risk": "is improving",
        "demand_risk": "is strengthening",
        "volatility_risk": "is normalizing",
        "concentration_risk": "is easing",
        "product_risk": "is easing",
    },
    "neutral": {
        "regulatory_risk": "remains uncertain",
        "earnings_risk": "remains uncertain",
        "guidance_risk": "remains mixed",
        "margin_risk": "remain in focus",
        "growth_risk": "remains uncertain",
        "macro_risk": "remains mixed",
        "leverage_risk": "remains stable",
        "liquidity_risk": "remains adequate",
        "technical_risk": "remains mixed",
        "execution_risk": "remains mixed",
        "valuation_risk": "remains balanced",
        "competitive_risk": "remains stable",
        "revenue_risk": "remains uncertain",
        "competition_risk": "remains stable",
        "demand_risk": "remains mixed",
        "volatility_risk": "remains contained",
        "concentration_risk": "remains elevated",
        "product_risk": "remains mixed",
    },
}


def _clean_text(value: Any) -> str:
    cleaned = sanitize_text_field(value)
    return cleaned


def _join_text_items(values: list[Any] | None) -> str:
    return ", ".join(_clean_text(value) for value in (values or []) if _clean_text(value))


def _truncate(text: str, limit: int) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = _clean_text(value)
        if text:
            return text
    return ""


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value)
    for candidate in (
        raw,
        raw.replace("Z", "+00:00"),
    ):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _theme_for_text(text: str) -> str | None:
    lowered = _clean_text(text).lower()
    for theme, keywords in _DRIVER_THEME_RULES:
        if any(keyword in lowered for keyword in keywords):
            return theme
    return None


def _direction_for_text(text: str, risk_direction: str | None = None) -> str:
    if risk_direction:
        normalized = _clean_text(risk_direction).lower()
        if normalized in {"worsening", "negative", "down"}:
            return "negative"
        if normalized in {"improving", "positive", "up"}:
            return "positive"
        if normalized in {"neutral", "flat", "stable"}:
            return "neutral"

    lowered = _clean_text(text).lower()
    if any(marker in lowered for marker in _NEGATIVE_DIRECTION_MARKERS):
        return "negative"
    if any(marker in lowered for marker in _POSITIVE_DIRECTION_MARKERS):
        return "positive"
    return "neutral"


def _is_generic_driver_text(text: str) -> bool:
    lowered = _clean_text(text).lower()
    return any(marker in lowered for marker in _GENERIC_DRIVER_MARKERS)


def _looks_like_rss_headline(text: str) -> bool:
    return bool(_RSS_HEADLINE_SUFFIX_RE.search(_clean_text(text)))


def _is_specific_driver_summary(summary: str, title: str | None = None) -> bool:
    cleaned_summary = _clean_text(summary)
    if not cleaned_summary or len(cleaned_summary) < 30:
        return False
    if title and cleaned_summary == _clean_text(title):
        return False
    if _looks_like_rss_headline(cleaned_summary):
        return False
    lowered = cleaned_summary.lower()
    if re.search(r"\((?:nasdaq|nyse|amex):[a-z0-9.-]+\)", lowered):
        return False
    if any(marker in lowered for marker in ("reuters", "seeking alpha", "yahoo finance", "yahoo! finance", "yahoo! finance canada", "barron's", "investing.com", "marketwatch", "stock titan", "quiver quantitative", "investopedia", "cnbc", "fortune", "blog.google", "benzinga", "msn", "tradingview", "u.s. bank")):
        return False
    if _is_generic_driver_text(cleaned_summary):
        return False
    return True


def _generate_driver_title(theme: str, direction: str | None) -> str:
    normalized_direction = direction if direction in {"negative", "positive", "neutral"} else "neutral"
    mapped_title = _THEME_DRIVER_TITLES.get((theme, normalized_direction))
    if mapped_title and not _looks_like_rss_headline(mapped_title):
        return mapped_title

    subject = _THEME_DRIVER_SUBJECTS.get(theme) or _clean_text(theme).replace("_", " ").strip().title() or "Risk outlook"
    phrase = (_THEME_DRIVER_PHRASES.get(normalized_direction) or {}).get(theme)
    if not phrase:
        fallback_phrases = {
            "negative": "is worsening",
            "positive": "is improving",
            "neutral": "remains uncertain",
        }
        phrase = fallback_phrases[normalized_direction]
    return f"{subject} {phrase}".strip()


def _generate_driver_summary(theme: str, direction: str | None, group: list[dict[str, Any]]) -> str:
    if not group:
        return ""

    primary = group[0]
    primary_summary = _clean_text(primary.get("summary"))
    primary_title = _clean_text(primary.get("title"))
    if _is_specific_driver_summary(primary_summary, primary_title):
        return _truncate(primary_summary, 180)

    for item in group[1:]:
        candidate_summary = _clean_text(item.get("summary"))
        if _is_specific_driver_summary(candidate_summary, _clean_text(item.get("title"))):
            return _truncate(candidate_summary, 180)

    normalized_direction = direction if direction in {"negative", "positive", "neutral"} else "neutral"
    static_desc = _THEME_DRIVER_DESCRIPTIONS.get((theme, normalized_direction)) or _THEME_DRIVER_DESCRIPTIONS.get((theme, "neutral"), "")
    return _truncate(static_desc, 220) if static_desc else ""


def _normalize_source(source: Any) -> str:
    return _clean_text(source)


def _candidate_identity(candidate: dict[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    event_hash = _clean_text(candidate.get("event_hash"))
    url = _clean_text(candidate.get("url"))
    title = _clean_text(candidate.get("title")).lower()
    source = _clean_text(candidate.get("source")).lower()
    published_at = _clean_text(candidate.get("published_at"))
    if event_hash:
        keys.append(f"hash:{event_hash}")
    if url:
        keys.append(f"url:{url.lower()}")
    if title or source or published_at:
        keys.append(f"title:{title}|source:{source}|published:{published_at}")
    return tuple(keys)


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple:
    priority = int(candidate.get("priority") or 0)
    confidence = float(candidate.get("confidence") or 0)
    published_at = _parse_datetime(candidate.get("published_at")) or _parse_datetime(candidate.get("created_at"))
    return (
        priority,
        confidence,
        published_at.timestamp() if published_at else float("-inf"),
        _clean_text(candidate.get("id")),
    )


def _select_summary_text(candidate: dict[str, Any]) -> str:
    return _first_non_empty(
        candidate.get("scenario_summary"),
        candidate.get("summary"),
        (candidate.get("key_implications") or [None])[0] if isinstance(candidate.get("key_implications"), list) and candidate.get("key_implications") else None,
        candidate.get("long_analysis"),
    )


def _candidate_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    text = " ".join(
        part
        for part in [
            _clean_text(event.get("title")),
            _clean_text(event.get("summary")),
            _clean_text(event.get("scenario_summary")),
            " ".join(_clean_text(item) for item in (event.get("key_implications") or []) if _clean_text(item)),
            _clean_text(event.get("long_analysis")),
        ]
        if part
    )
    theme = _theme_for_text(text)
    if not theme:
        return None
    title = _clean_text(event.get("title"))
    summary = _select_summary_text(event)
    if not title or not summary or _is_generic_driver_text(title):
        return None
    # Only reject AI-generated summaries for boilerplate (short texts); longer summaries
    # may incidentally contain words like "analyst" or "watch" in meaningful context
    if len(summary) < 80 and _is_generic_driver_text(summary):
        return None
    return {
        "id": _clean_text(event.get("id")),
        "kind": "event_analysis",
        "title": title,
        "summary": summary,
        "source": _normalize_source(event.get("source")),
        "url": _clean_text(event.get("source_url")) or None,
        "published_at": _clean_text(event.get("published_at")) or None,
        "confidence": float(event.get("confidence") or 0),
        "event_id": _clean_text(event.get("id")) or None,
        "news_id": None,
        "alert_id": None,
        "event_hash": _clean_text(event.get("event_hash")) or None,
        "theme": theme,
        "direction": _direction_for_text(text, event.get("risk_direction")),
        "priority": 0 if _clean_text(event.get("significance")) == "major" else 1,
        "is_major": _clean_text(event.get("significance")) == "major",
        "created_at": _clean_text(event.get("created_at")) or None,
    }


def _candidate_from_news(article: dict[str, Any]) -> dict[str, Any] | None:
    title = _first_non_empty(article.get("headline"), article.get("title"))
    summary = _first_non_empty(article.get("summary"))
    text = f"{title} {summary or title}"
    theme = _theme_for_text(text)
    if not theme:
        return None
    if not title or _is_generic_driver_text(title) or (summary and _is_generic_driver_text(summary)):
        return None
    sentiment = _clean_text(article.get("sentiment")).lower()
    direction = _direction_for_text(text)
    if sentiment in {"positive", "bullish"} and direction != "negative":
        direction = "positive"
    elif sentiment in {"negative", "bearish"} and direction != "positive":
        direction = "negative"
    return {
        "id": _clean_text(article.get("id")),
        "kind": "news_item",
        "title": title,
        "summary": summary,
        "source": _normalize_source(article.get("source")),
        "url": _clean_text(article.get("url")) or None,
        "published_at": _clean_text(article.get("published_at")) or None,
        "confidence": float(article.get("relevance_score") or 0.5),
        "event_id": None,
        "news_id": _clean_text(article.get("id")) or None,
        "alert_id": None,
        "event_hash": _clean_text(article.get("event_hash")) or None,
        "theme": theme,
        "direction": direction,
        "priority": 2,
        "is_major": False,
        "created_at": _clean_text(article.get("created_at")) or None,
    }


def _candidate_from_alert(alert: dict[str, Any]) -> dict[str, Any] | None:
    title = _first_non_empty(alert.get("message"), alert.get("change_reason"))
    summary = _first_non_empty(alert.get("change_reason"), alert.get("message"))
    text = f"{title} {summary}"
    theme = _theme_for_text(text)
    if not theme:
        return None
    if not title or not summary or _is_generic_driver_text(title) or _is_generic_driver_text(summary):
        return None
    return {
        "id": _clean_text(alert.get("id")),
        "kind": "alert",
        "title": title,
        "summary": summary,
        "source": "Clavix Alert",
        "url": None,
        "published_at": _clean_text(alert.get("created_at")) or None,
        "confidence": 0.6,
        "event_id": None,
        "news_id": None,
        "alert_id": _clean_text(alert.get("id")) or None,
        "event_hash": _clean_text(alert.get("event_hash")) or None,
        "theme": theme,
        "direction": _direction_for_text(text),
        "priority": 3,
        "is_major": _clean_text(alert.get("type")) in {"major_event", "grade_change"},
        "created_at": _clean_text(alert.get("created_at")) or None,
    }


def _evidence_item_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": candidate["id"],
        "kind": candidate["kind"],
        "title": _truncate(candidate["title"], 140),
        "summary": _truncate(candidate["summary"], 220),
        "source": _truncate(candidate["source"], 80),
        "url": candidate.get("url"),
        "published_at": candidate.get("published_at"),
        "confidence": candidate.get("confidence"),
        "event_id": candidate.get("event_id"),
        "news_id": candidate.get("news_id"),
        "alert_id": candidate.get("alert_id"),
    }


def _strength_for_group(group: list[dict[str, Any]]) -> str:
    evidence_count = len(group)
    unique_sources = len({ _normalize_source(item.get("source")) for item in group if _normalize_source(item.get("source")) })
    max_confidence = max((float(item.get("confidence") or 0) for item in group), default=0)
    has_major_event = any(item.get("is_major") for item in group if item.get("kind") == "event_analysis")
    if evidence_count >= 2 and unique_sources >= 2 and (max_confidence >= 0.75 or has_major_event):
        return "strong"
    if evidence_count >= 2 and unique_sources == 1:
        return "moderate"
    if evidence_count == 1 and max_confidence >= 0.55:
        return "moderate"
    return "limited"


def _source_chips_for_group(group: list[dict[str, Any]]) -> list[str]:
    sources: list[str] = []
    for item in group:
        source = _normalize_source(item.get("source"))
        if source and source not in sources:
            sources.append(source)
    if not sources:
        return []
    if len(sources) == 1:
        return [sources[0]]
    if len(sources) == 2:
        return sources[:2]
    return [sources[0], sources[1], f"{len(group)} sources"]


def _build_driver_cards(
    position: dict[str, Any],
    event_analyses: list[dict[str, Any]] | None = None,
    related_articles: list[dict[str, Any]] | None = None,
    alerts: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str, str | None]:
    event_analyses = event_analyses or []
    related_articles = related_articles or []
    alerts = alerts or []

    candidates: list[dict[str, Any]] = []
    for event in event_analyses:
        candidate = _candidate_from_event(event)
        if candidate:
            candidates.append(candidate)
    for article in related_articles:
        candidate = _candidate_from_news(article)
        if candidate:
            candidates.append(candidate)
    for alert in alerts:
        candidate = _candidate_from_alert(alert)
        if candidate:
            candidates.append(candidate)

    candidates.sort(key=_candidate_sort_key, reverse=True)

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        keys = _candidate_identity(candidate)
        if keys and any(key in seen for key in keys):
            continue
        deduped.append(candidate)
        seen.update(keys)

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in deduped:
        theme = candidate.get("theme")
        direction = candidate.get("direction")
        if not theme:
            continue
        key = (theme, direction or "neutral")
        groups.setdefault(key, []).append(candidate)

    cards_with_meta: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for (theme, direction), group in groups.items():
        group.sort(key=_candidate_sort_key, reverse=True)
        title = _generate_driver_title(theme, direction)
        summary = _generate_driver_summary(theme, direction, group)
        timestamps = [
            timestamp
            for timestamp in (
                _parse_datetime(item.get("published_at")) or _parse_datetime(item.get("created_at"))
                for item in group
            )
            if timestamp is not None
        ]
        if not title or not summary:
            continue
        # For AI summaries (>= 80 chars), skip the generic check — real scenario
        # summaries may mention "analyst" or "watch" in meaningful context.
        if (
            _looks_like_rss_headline(title)
            or _is_generic_driver_text(title)
            or summary == title
            or any(summary == _clean_text(item.get("title")) for item in group)
            or (len(summary) < 80 and _is_generic_driver_text(summary))
        ):
            continue
        strength = _strength_for_group(group)
        evidence_items = [_evidence_item_from_candidate(item) for item in group[:3]]
        card = {
            "id": str(group[0]["id"] or group[0].get("event_hash") or f"driver-{len(cards_with_meta)+1}"),
            "rank": 0,
            "title": title,
            "summary": summary,
            "strength": strength,
            "direction": direction,
            "theme": theme,
            "source_chips": _source_chips_for_group(group),
            "supporting_event_ids": [item["event_id"] for item in group if item.get("event_id")][:3],
            "supporting_news_ids": [item["news_id"] for item in group if item.get("news_id")][:3],
            "supporting_evidence": evidence_items,
        }
        meta = {
            "has_major_event": any(item.get("is_major") for item in group if item.get("kind") == "event_analysis"),
            "evidence_count": len(group),
            "unique_sources": len({_normalize_source(item.get("source")) for item in group if _normalize_source(item.get("source"))}),
            "max_confidence": max((float(item.get("confidence") or 0) for item in group), default=0),
            "latest_timestamp": max(timestamps) if timestamps else None,
            "theme_priority": _DRIVER_THEME_PRIORITY.get(theme, 999),
        }
        cards_with_meta.append((card, meta))

    cards_with_meta.sort(
        key=lambda pair: (
            -int(bool(pair[1]["has_major_event"])),
            -pair[1]["evidence_count"],
            -pair[1]["unique_sources"],
            -pair[1]["max_confidence"],
            -(pair[1]["latest_timestamp"].timestamp() if pair[1]["latest_timestamp"] else float("-inf")),
            pair[1]["theme_priority"],
            pair[0]["title"].lower(),
        )
    )

    cards: list[dict[str, Any]] = []
    for index, (card, _meta) in enumerate(cards_with_meta[:3], start=1):
        card["rank"] = index
        cards.append(card)

    raw_evidence_count = len(deduped)
    status = _clean_text(position.get("analysis_state") or position.get("status")).lower()
    coverage_state = _clean_text(position.get("coverage_state")).lower()
    if status and status != "ready":
        driver_cards_state = "pending"
    elif cards:
        driver_cards_state = "ready"
    elif raw_evidence_count <= 2 or coverage_state in {"provisional", "thin"}:
        driver_cards_state = "limited"
    else:
        driver_cards_state = "empty"

    return sanitize_public_analysis_text(cards), driver_cards_state, "generated"


def _empty_driver_cards_state(position: dict[str, Any]) -> str:
    status = _clean_text(position.get("analysis_state") or position.get("status")).lower()
    coverage_state = _clean_text(position.get("coverage_state")).lower()
    source_count = int(position.get("source_count") or 0)
    if status and status != "ready":
        return "pending"
    if coverage_state in {"provisional", "thin"} or source_count <= 2:
        return "limited"
    return "empty"


def _fallback_position_report(
    position: dict,
    inferred_labels: list[str],
    event_analyses: list[dict],
) -> dict:
    ticker = position.get("ticker", "This holding")
    major_events = [
        event for event in event_analyses if event.get("significance") == "major"
    ]
    worsening_count = len(
        [
            event
            for event in event_analyses
            if event.get("risk_direction") == "worsening"
        ]
    )
    improving_count = len(
        [
            event
            for event in event_analyses
            if event.get("risk_direction") == "improving"
        ]
    )
    labels_text = _join_text_items(inferred_labels[:3]) if inferred_labels else "core"
    event_titles = [
        event.get("title", "recent data") for event in event_analyses[:3]
    ]

    stance = "mixed — no single force clearly dominates"
    if worsening_count > improving_count:
        stance = "downside pressure is the primary concern"
    elif improving_count > worsening_count:
        stance = "constructive but still subject to reversal"

    summary = (
        f"{ticker}'s current risk profile leans {labels_text}. "
        f"The dominant read is {stance}, based on {len(event_analyses)} tracked developments."
    )
    long_report = (
        f"{ticker} is classified as {labels_text}. "
        f"The most relevant developments were {', '.join(event_titles)}. "
        f"{worsening_count} item(s) flagged downside pressure and {improving_count} pointed to improvement. "
        f"This rating is limited-data — a single new filing, earnings surprise, or regulatory update could shift the rating materially."
    )
    top_risks = [
        event.get("scenario_summary") or event.get("title", "Recent catalyst risk")
        for event in event_analyses[:3]
    ]
    watch_items = [
        followup
        for event in event_analyses[:3]
        for followup in (event.get("recommended_followups") or [])[:1]
    ]

    return {
        "summary": summary,
        "long_report": long_report,
        "methodology": "Summary assembled from event-level analysis. LLM synthesis was unavailable for this position.",
        "top_risks": top_risks
        or ["A single new article or filing could materially change the risk rating."],
        "watch_items": watch_items
        or [
            "Check for new company-specific news, guidance, or filings that change the setup."
        ],
    }


async def build_position_report(
    position: dict,
    inferred_labels: list[str],
    event_analyses: list[dict],
    macro_context: dict | None = None,
    related_articles: list[dict] | None = None,
    alerts: list[dict] | None = None,
) -> dict:
    related_articles = related_articles or []
    alerts = alerts or []
    driver_cards, driver_cards_state, driver_cards_source = _build_driver_cards(
        position,
        event_analyses=event_analyses,
        related_articles=related_articles,
        alerts=alerts,
    )

    if not event_analyses and not related_articles and not alerts:
        ticker = position.get("ticker", "This holding")
        return sanitize_public_analysis_text(
            {
                "summary": f"There is not enough recent news to form a confident risk rating for {ticker}. The current rating relies on existing position context and structural factors.",
                "long_report": f"Data for {ticker} is thin in this cycle, so the dominant risk rating defaults to structural and sector factors rather than company-specific catalysts. This is a limited-data rating — any new company-specific development (earnings, guidance, regulatory action) could shift the picture meaningfully. Treat this as limited-data until fuller data arrives.",
                "methodology": "Limited-data rating based on position metadata and structural context. No usable event data for this cycle.",
                "top_risks": [
                    "No confirmed company-specific catalyst in this cycle."
                ],
                "watch_items": [
                    "Recheck for resolved company or sector data before treating the current rating as settled."
                ],
                "driver_cards": driver_cards,
                "driver_cards_state": driver_cards_state,
                "driver_cards_source": driver_cards_source,
            }
        )

    event_summary = "\n".join(
        f"- [{event.get('significance', 'minor')}] {event.get('title', '')}: {event.get('long_analysis', '')[:400]}"
        for event in event_analyses[:8]
    )
    is_backfill_mode = (
        str(position.get("analysis_mode") or "").strip().lower() == "sp500_backfill"
    )
    prompt = f"""Position:
    - Ticker: {position.get("ticker", "")}
    - Sector: {position.get("sector", "unknown")}
    - Inferred labels: {_join_text_items(inferred_labels) if inferred_labels else "unknown"}
    """

    if is_backfill_mode:
        prompt += """
Backfill context:
- This is a synthetic ticker-level backfill snapshot, not a live user position.
- Do not infer conviction, entry timing, position sizing, or portfolio intent from placeholder shares or purchase price fields.
"""
    else:
        prompt += f"""
- Shares: {position.get("shares", 0)}
- Purchase price: {position.get("purchase_price", 0)}
"""

    if macro_context and macro_context.get("overnight_macro"):
        macro_brief = macro_context["overnight_macro"].get("brief", "")
        macro_themes = macro_context["overnight_macro"].get("themes", [])
        prompt += f"""
Macro Context (overnight developments):
- Brief: {macro_brief}
- Themes: {_join_text_items(macro_themes) if macro_themes else "none detected"}
"""

        position_impacts = macro_context.get("position_impacts", [])
        ticker_impact = next(
            (
                imp
                for imp in position_impacts
                if imp.get("ticker", "").upper() == position.get("ticker", "").upper()
            ),
            None,
        )
        if ticker_impact:
            prompt += f"- Macro impact on {position.get('ticker')}: {ticker_impact.get('impact_summary', '')}\n"

    prompt += f"""
Event analyses:
{event_summary}
"""

    try:
        result = chatcompletion_text(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1400,
        )
    except Exception:
        fallback = _fallback_position_report(position, inferred_labels, event_analyses)
        return sanitize_public_analysis_text(
            {
                "summary": fallback["summary"],
                "long_report": fallback["long_report"],
                "methodology": fallback["methodology"],
                "top_risks": fallback["top_risks"],
                "watch_items": fallback["watch_items"],
                "risk_context": [],
                "driver_cards": driver_cards,
                "driver_cards_state": driver_cards_state,
                "driver_cards_source": driver_cards_source,
            }
        )

    parsed = extract_json_object(result, {})
    fallback = _fallback_position_report(position, inferred_labels, event_analyses)
    return sanitize_public_analysis_text(
        {
            "summary": parsed.get("summary") or fallback["summary"],
            "long_report": parsed.get("long_report")
            or parsed.get("summary")
            or fallback["long_report"],
            "methodology": parsed.get("methodology") or fallback["methodology"],
            "top_risks": parsed.get("top_risks") or fallback["top_risks"],
            "watch_items": parsed.get("watch_items") or fallback["watch_items"],
            "risk_context": parsed.get("risk_context") or parsed.get("rating_verifier") or [],
            "driver_cards": driver_cards,
            "driver_cards_state": driver_cards_state,
            "driver_cards_source": driver_cards_source,
        }
    )


BATCH_REPORT_PROMPT = """You write concise downside risk ratings for multiple stock positions.

Write like a risk rater briefing a portfolio manager — direct, specific, rating-driven. Do not catalog articles; synthesize what they mean.

Return a JSON array with one object per position in order.
Each object has:
- "summary": "1-2 sentence summary: dominant risk force, counter-evidence acknowledged, what changes the rating"
- "long_report": "3-6 sentence detailed report that develops the rating, resolves contradictions with evidence, and closes with what could shift the rating"
- "methodology": "brief explanation of the evidence used"
- "top_risks": ["risk 1", "risk 2", "risk 3"]
- "watch_items": ["risk driver 1", "risk driver 2"]
- "risk_context": [{{"macro_event": "...", "rating_impact": "supports|contradicts|neutral", "reasoning": "..."}}]

Writing rules:
1. Lead with the dominant narrative, not with what data exists.
2. If positive and negative evidence compete, resolve which matters more and why. Do not list both sides.
3. Close with what would change the rating — specific, not generic.

Forbidden: internal evidence labels (full_body, title_only, headline_summary), scoring methodology references, "recent event flow is [stance]", "N relevant items", implementation jargon, "thesis", "positive momentum", "macro headwinds", "provisional", "current read", "sentiment", "confirms", "coverage", "monitor/recheck", "research", "analyst", "confidence" (as model uncertainty), "watch" (use "risk driver" instead).

CRITICAL - Macro as Risk Context:
- For risk_context, assess whether any macro context supports, contradicts, or is neutral to each position's risk profile
- If a position has no clear setup, use "neutral" for rating_impact
- Only include risk_context entries for macro events that actually relate to each position's sector/theme
- If no relevant macro context exists for a position, omit risk_context array for that position

Positions:
{positions}

Return a JSON array with {count} objects, one per position in order."""


async def build_position_reports_batch(
    positions: list[dict],
    positions_inferred_labels: dict[str, list[str]],
    all_event_analyses: dict[str, list[dict]],
    macro_context: dict | None = None,
) -> list[dict]:
    if not positions:
        return []

    macro_brief = ""
    macro_themes = []
    if macro_context and macro_context.get("overnight_macro"):
        macro_brief = macro_context["overnight_macro"].get("brief", "")
        macro_themes = macro_context["overnight_macro"].get("themes", [])

    position_impacts = (
        macro_context.get("position_impacts", []) if macro_context else []
    )

    positions_text = []
    for i, position in enumerate(positions):
        ticker = position.get("ticker", "")
        inferred_labels = positions_inferred_labels.get(ticker, [])
        event_analyses = all_event_analyses.get(ticker, [])

        event_summary = "\n".join(
            f"- [{event.get('significance', 'minor')}] {event.get('title', '')}: {event.get('long_analysis', '')[:300]}"
            for event in event_analyses[:6]
        )

        pos_text = f"""[{i}] Ticker: {ticker}
- Sector: {position.get("sector", "unknown")}
- Shares: {position.get("shares", 0)}
- Purchase price: {position.get("purchase_price", 0)}
- Inferred labels: {_join_text_items(inferred_labels) if inferred_labels else "unknown"}"""

        if macro_brief:
            pos_text += f"""
- Macro Context: Brief: {macro_brief}, Themes: {_join_text_items(macro_themes) if macro_themes else "none"}"""

        ticker_impact = next(
            (
                imp
                for imp in position_impacts
                if imp.get("ticker", "").upper() == ticker.upper()
            ),
            None,
        )
        if ticker_impact:
            pos_text += f"\n- Macro impact: {ticker_impact.get('impact_summary', '')}"

        if event_summary:
            pos_text += f"\n- Event analyses:\n{event_summary}"
        else:
            pos_text += "\n- Event analyses: None"

        positions_text.append(pos_text)

    prompt = BATCH_REPORT_PROMPT.format(
        positions="\n\n".join(positions_text),
        count=len(positions),
    )

    result = chatcompletion_text(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=5000,
    )

    parsed = extract_json_list(result, None)

    results = []
    if isinstance(parsed, list) and len(parsed) == len(positions):
        for i, position in enumerate(positions):
            ticker = position.get("ticker", "")
            inferred_labels = positions_inferred_labels.get(ticker, [])
            event_analyses = all_event_analyses.get(ticker, [])
            fallback = _fallback_position_report(
                position, inferred_labels, event_analyses
            )
            p = parsed[i]
            results.append(
                sanitize_public_analysis_text(
                    {
                        "summary": p.get("summary") or fallback["summary"],
                        "long_report": p.get("long_report")
                        or p.get("summary")
                        or fallback["long_report"],
                        "methodology": p.get("methodology") or fallback["methodology"],
                        "top_risks": p.get("top_risks") or fallback["top_risks"],
                        "watch_items": p.get("watch_items") or fallback["watch_items"],
                        "risk_context": p.get("risk_context") or p.get("rating_verifier") or [],
                    }
                )
            )
    else:
        for position in positions:
            ticker = position.get("ticker", "")
            inferred_labels = positions_inferred_labels.get(ticker, [])
            event_analyses = all_event_analyses.get(ticker, [])
            results.append(
                _fallback_position_report(position, inferred_labels, event_analyses)
            )

    return results
