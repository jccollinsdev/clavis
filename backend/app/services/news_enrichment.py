from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

# Finnhub-first pipeline settings
NEWS_PRIMARY_PROVIDER: str = "finnhub"
GOOGLE_NEWS_FALLBACK_ENABLED: bool = os.getenv("GOOGLE_NEWS_FALLBACK_ENABLED", "true").lower() not in {"0", "false", "no", "off"}

# MVP threshold: Google used if usable < this (previously GOOGLE_FALLBACK_MIN_USABLE_ARTICLES)
GOOGLE_FALLBACK_MVP_THRESHOLD: int = int(os.getenv("GOOGLE_FALLBACK_MVP_THRESHOLD", "3"))
# Production ideal: Google used to boost if usable < this (when mode allows)
GOOGLE_FALLBACK_PRODUCTION_TARGET: int = int(os.getenv("GOOGLE_FALLBACK_PRODUCTION_TARGET", "10"))
# mvp_only: Google only for usable < MVP_THRESHOLD
# below_10: Google for usable < PRODUCTION_TARGET (mvp_recovery + production_boost)
# disabled: no Google at all
GOOGLE_FALLBACK_MODE: str = os.getenv("GOOGLE_FALLBACK_MODE", "below_10")
# Per-ticker Google fetch limits
GOOGLE_FALLBACK_MAX_CANDIDATES_PER_TICKER: int = int(os.getenv("GOOGLE_FALLBACK_MAX_CANDIDATES_PER_TICKER", "15"))
GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER: int = int(os.getenv("GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER", "10"))

# Backward-compat alias
GOOGLE_FALLBACK_MIN_USABLE_ARTICLES: int = GOOGLE_FALLBACK_MVP_THRESHOLD

from .article_scraper import (
    _extract_with_trafilatura,
    _extract_with_newspaper4k,
    _strip_article_boilerplate,
    _normalize_host,
    _article_source_host,
)
from .minimax import chatcompletion_text
from ..pipeline.analysis_utils import extract_json_object, sanitize_text_field, _strip_model_wrappers

logger = logging.getLogger(__name__)

SOURCE_TIER_MAP: dict[str, int] = {
    "reuters": 1, "reuters.com": 1,
    "wsj": 1, "wsj.com": 1, "wall street journal": 1,
    "bloomberg": 1, "bloomberg.com": 1,
    "ft": 1, "ft.com": 1, "financial times": 1,
    "ap": 1, "apnews.com": 1, "associated press": 1,

    "marketwatch": 2, "marketwatch.com": 2,
    "yahoo finance": 2, "finance.yahoo.com": 2,
    "investing.com": 2,
    "seeking alpha": 2, "seekingalpha.com": 2,
    "cnbc": 2, "cnbc.com": 2,
    "business insider": 2, "businessinsider.com": 2,
    "barrons": 2, "barrons.com": 2,
    "morningstar": 2, "morningstar.com": 2,
    "fool.com": 2, "motley fool": 2,
    "zacks": 2, "zacks.com": 2,
    "investors.com": 2,
    "benzinga": 2, "benzinga.com": 2,
}

_PAYWALL_DOMAINS: set[str] = {
    "wsj.com", "bloomberg.com", "ft.com",
    "barrons.com", "marketwatch.com",
    "nytimes.com", "morningstar.com", "global.morningstar.com",
    "thetimes.com", "news.microsoft.com",
}

# Domains that are technically not paywalled but are blocked / anti-bot / 0% extraction
# These will be stored but marked extraction_status="blocked" rather than "failed"
_BLOCKED_DOMAINS: set[str] = {
    "reuters.com", "msn.com", "news.bloomberglaw.com",
    "thestreet.com", "britannica.com",
}

# Low-value domains (chart sites, analytics, not real news) — deprioritized upstream
# but if they do arrive, extract minimally
_LOW_VALUE_DOMAINS: set[str] = {
    "marketbeat.com", "chartmill.com", "stocktitan.net",
    "macroaxis.com", "tipranks.com", "barchart.com",
}

_LOGIN_WALL_MARKERS: tuple[str, ...] = (
    "sign in",
    "log in",
    "login",
    "subscribe",
    "create free account",
    "join pro",
    "join ic",
    "watchlist",
)

_NAVIGATION_MARKERS: tuple[str, ...] = (
    "search quotes, news & videos",
    "livestream menu",
    "markets markets",
    "stock screener",
    "data & apis",
    "financial news financial news",
    "options etfs commodities",
    "premarket advertise contribute",
    "privacy policy",
    "terms of service",
)

_COOKIE_MARKERS: tuple[str, ...] = (
    "accept all",
    "deny optional",
    "cookie policy",
    "consent preferences",
)

_BLOCKED_PAGE_MARKERS: tuple[str, ...] = (
    "access denied",
    "verify you are human",
    "captcha",
    "unusual traffic",
    "checking if the site connection is secure",
    "press and hold",
)

_TITLE_STOPWORDS: set[str] = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
}

_COMPANY_STOPWORDS: set[str] = {
    "class",
    "co",
    "company",
    "corp",
    "corporation",
    "group",
    "holdings",
    "inc",
    "incorporated",
    "limited",
    "ltd",
    "plc",
    "sa",
}

_PROMO_PARAGRAPH_MARKERS: tuple[str, ...] = (
    "get them here free",
    "find your next quality investment",
    "never miss an important update on your stock portfolio",
    "trusted by over",
    "this post may contain links from our sponsors and affiliates",
    "flywheel publishing may receive compensation",
    "how to add us to google news",
    "help our services",
    "stock advisor",
    "all podcasts",
    "best etfs to buy",
    "best ai stocks",
    "top stocks to buy now",
    "best brokerage accounts",
    "free tool can match you with a financial advisor",
    "don't waste another minute",
    "breakfast news",
    "print subscriptions",
    "download the app",
    "back to home",
    "skip to navigation",
)

_SPORTS_MARKERS: tuple[str, ...] = (
    "nba",
    "nfl",
    "mlb",
    "nhl",
    "wnba",
    "soccer",
    "world cup",
    "touchdown",
    "quarterback",
    "playoffs",
    "lakers",
    "warriors",
    "thunder",
    "eagles",
    "celtics",
)

_FINANCE_MARKERS: tuple[str, ...] = (
    "analyst",
    "business",
    "ceo",
    "company",
    "dividend",
    "earnings",
    "equity",
    "guidance",
    "investor",
    "lawsuit",
    "management",
    "market",
    "merger",
    "profit",
    "quarter",
    "regulator",
    "revenue",
    "sales",
    "shares",
    "stock",
)

_GENERAL_NEWS_DOMAINS: set[str] = {
    "clutchpoints.com",
    "espn.com",
    "imdb.com",
    "theguardian.com",
    "burncitysports.com",
    "hotelsmag.com",
}

_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "buy",
    "sell",
    "advise",
    "suggest",
    "predict",
    "forecast",
    "recommendation",
    "bullish outlook",
    "bearish call",
    "upside potential",
)

ENRICHMENT_PROMPT = """You are a risk-rating agency, not an investment analyst.
You are rating one news article for a stock-risk system.

Return exactly one JSON object and nothing else.
Do not include markdown, prefaces, apologies, analysis outside JSON, or trailing text.

Write only as a risk-rating agency:
- Describe observed risk signals only.
- Do not imply or recommend any action.
- Do not mention investment decisions or what an investor should do.
- Never use these words anywhere in any field: buy, sell, advise, suggest, recommendation, recommend, predict, forecast, bullish outlook, bearish call, upside potential.
- Use neutral risk language instead: indicates, reflects, signals, points to, raises, lowers, pressure, risk, evidence, uncertainty, exposure.

Required JSON schema:
{{
  "sentiment_score": <number 0-100>,
  "sentiment_reason": "<one sentence>",
  "tldr": "<1-2 sentence factual summary>",
  "what_it_means": "<1-2 sentence implication for the company/stock>",
  "key_implications": ["<short bullet>", "<short bullet>", "<short bullet>"],
  "impact_tag": "<financial-impact|regulatory|leadership|product|macro|sector|other>"
}}

Rules:
- sentiment_score must be a number from 0 to 100.
- sentiment_reason must explain the score using article evidence only.
- tldr must describe what happened, factually.
- what_it_means must explain the likely implication for the company/stock as a risk signal, not advice for an investor.
- key_implications must contain 2-3 short bullets, each at most 18 words; use [] only if the article truly lacks enough evidence. Keep total output compact so the JSON is never truncated.
- If the article is descriptive and balanced, use sentiment_score 50.

Ticker: {ticker}
Company: {company_name}
Headline: {headline}
Article excerpt:
{body_excerpt}
"""

ENRICHMENT_RETRY_PROMPT = """Return one strict JSON object only.

The previous response was unusable because it was empty, malformed, incomplete, or used forbidden language.
Do not output any prose outside JSON.
Do not omit any required key.

Write only as a risk-rating agency, not an analyst. Describe observed risk signals only.
Never use these words anywhere: buy, sell, advise, suggest, recommendation, recommend, predict, forecast, bullish outlook, bearish call, upside potential.
Prefer: indicates, reflects, signals, points to, raises, lowers, pressure, risk, evidence, uncertainty, exposure.

Required keys: sentiment_score, sentiment_reason, tldr, what_it_means, key_implications, impact_tag.
key_implications: 2-3 short bullets, each at most 18 words. Keep the whole object compact so it is never truncated.

Ticker: {ticker}
Company: {company_name}
Headline: {headline}
Shorter article excerpt:
{body_excerpt}
"""

ENRICHMENT_FORBIDDEN_RETRY_PROMPT = """Return one strict JSON object only. No markdown, no prose outside JSON.

Your previous JSON was rejected because it used investment-advice / action language.
Forbidden wording detected: "{forbidden_phrase}".

Rewrite the SAME analysis as a risk-rating agency, not an analyst:
- Keep every factual claim and the exact same sentiment_score.
- Describe observed risk signals only. Do not imply any action or investment decision.
- Do NOT use any of these words anywhere: buy, sell, advise, suggest, recommendation, recommend, predict, forecast, bullish outlook, bearish call, upside potential.
- Prefer: indicates, reflects, signals, points to, raises, lowers, pressure, risk, evidence, uncertainty, exposure.
- Keep the JSON schema identical. key_implications: 2-3 short bullets, each at most 18 words. Keep it compact so it is never truncated.

Required keys: sentiment_score, sentiment_reason, tldr, what_it_means, key_implications, impact_tag.

Previous JSON to fix (rewrite the wording, keep the meaning):
{prior_json}
"""

SENTIMENT_PROMPT = """Analyze the following news article about {ticker} and return a JSON object.

Article headline: {headline}
Article body excerpt: {body_excerpt}

Return ONLY this JSON (no markdown, no explanation):
{{"sentiment_score": <0-100>, "sentiment_reason": "<one sentence>", "impact_tag": "<category>"}}

- sentiment_score: 0 = extremely negative for the company/stock, 100 = extremely positive. 50 = neutral/balanced.
- sentiment_reason: One sentence explaining WHY this score was assigned. No hedging. Be specific.
- impact_tag: Choose ONE from: financial-impact, regulatory, leadership, product, macro, sector, other

Use the article evidence. Do not guess. If the article is purely descriptive with no clear implication, score 50."""

TLDR_PROMPT = """Summarize the following news article about {ticker} and return a JSON object.

Article headline: {headline}
Article body: {body}

Return ONLY this JSON (no markdown, no explanation):
{{"tldr": "<1-2 sentence summary>", "what_it_means": "<1-2 sentence implication for the stock>", "key_implications": ["<bullet 1>", "<bullet 2>", "<bullet 3>", "<bullet 4>"]}}

- tldr: Pure factual summary. No opinion. What happened.
- what_it_means: Implication for the company/stock. Specific, not generic.
- key_implications: 2-4 concrete, specific bullet points. Financial, operational, regulatory, competitive implications.

If the body text is very short or insufficient to derive implications, set key_implications to an empty array and note that in tldr."""


def classify_source_tier(source: str) -> int:
    if not source:
        return 3
    normalized = source.strip().lower()
    for key, tier in SOURCE_TIER_MAP.items():
        if key in normalized:
            return tier
    return 3


def classify_recency_weight(published_at: str | None) -> tuple[float, str]:
    if not published_at:
        return 1.0, "72h_7d"
    try:
        dt = _parse_iso(published_at)
        if dt is None:
            return 1.0, "72h_7d"
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if age_hours <= 24:
            return 3.0, "last_24h"
        if age_hours <= 72:
            return 2.0, "24_72h"
        return 1.0, "72h_7d"
    except Exception:
        return 1.0, "72h_7d"


def source_weight_for_tier(tier: int) -> float:
    return {1: 1.5, 2: 1.0, 3: 0.5}.get(tier, 1.0)


def _normalize_url_host(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def is_paywalled_domain(url: str) -> bool:
    host = _normalize_url_host(url)
    return any(pd in host for pd in _PAYWALL_DOMAINS) if host else False


def is_blocked_domain(url: str) -> bool:
    """Anti-bot/blocked domains: 0% extraction success, not paywalled."""
    host = _normalize_url_host(url)
    return any(bd in host for bd in _BLOCKED_DOMAINS) if host else False


def validate_enrichment_completeness(article: dict) -> tuple[bool, list[str]]:
    """Check whether an article has all required enrichment fields.

    Returns (is_complete, missing_fields).
    An article is complete when it has:
    - sentiment_score (numeric 0-100)
    - sentiment_reason (non-empty string)
    - tldr (non-empty, only required if body_has_content)

    key_implications are required only for body-extracted articles.
    """
    missing: list[str] = []
    if article.get("sentiment_score") is None:
        missing.append("missing_sentiment_score")
    if not str(article.get("sentiment_reason") or "").strip():
        missing.append("missing_sentiment_reason")
    body = str(article.get("body") or "")
    body_has_content = (
        body
        and not body.startswith("[No body extracted]")
        and not body.startswith("[Paywalled]")
        and len(body.split()) >= 40
    )
    if body_has_content:
        if not str(article.get("tldr") or "").strip():
            missing.append("missing_tldr")
        if not str(article.get("what_it_means") or "").strip():
            missing.append("missing_what_it_means")
    return len(missing) == 0, missing


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _compute_event_hash(ticker: str, url: str, headline: str) -> str:
    raw = f"{ticker.strip().upper()}|{url.strip()}|{headline.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _truncate_text(text: str, limit: int = 1500) -> str:
    if not text:
        return ""
    return text[:limit]


def _sentence_like_paragraphs(text: str) -> int:
    count = 0
    for raw in re.split(r"\n{2,}", text or ""):
        paragraph = raw.strip()
        if len(paragraph.split()) < 12:
            continue
        if re.search(r"[.!?]", paragraph):
            count += 1
    return count


def _title_signal_tokens(title: str) -> list[str]:
    tokens: list[str] = []
    for token in re.split(r"[^A-Za-z0-9]+", title or ""):
        normalized = token.strip().lower()
        if len(normalized) < 4 or normalized in _TITLE_STOPWORDS:
            continue
        tokens.append(normalized)
    return tokens[:6]


def _company_signal_tokens(company_name: str | None, ticker: str) -> list[str]:
    tokens: list[str] = []
    for token in re.split(r"[^A-Za-z0-9&]+", company_name or ""):
        normalized = token.strip().lower()
        if len(normalized) < 3 or normalized in _COMPANY_STOPWORDS:
            continue
        tokens.append(normalized)
    ticker_token = str(ticker or "").strip().lower()
    if len(ticker_token) >= 2:
        tokens.append(ticker_token)
    return list(dict.fromkeys(tokens))[:8]


def _contains_ticker_symbol(text: str, ticker: str) -> bool:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        return False
    return re.search(rf"\b{re.escape(symbol)}\b", text or "", flags=re.IGNORECASE) is not None


def _strip_low_value_paragraphs(text: str, source_host: str = "") -> tuple[str, int]:
    kept: list[str] = []
    removed = 0
    for raw in re.split(r"\n{2,}", text or ""):
        paragraph = raw.strip()
        if not paragraph:
            continue
        lowered = paragraph.lower()
        if any(marker in lowered for marker in _PROMO_PARAGRAPH_MARKERS):
            removed += 1
            continue
        if paragraph.count("|") >= 5 or lowered.count("http") >= 2:
            removed += 1
            continue
        if "yahoo" in source_host and lowered.startswith("ai investor podcast investing personal finance"):
            removed += 1
            continue
        if "fool.com" in source_host and lowered.startswith("accessibility"):
            removed += 1
            continue
        kept.append(paragraph)
    return "\n\n".join(kept).strip(), removed


def _find_forbidden_phrase(payload: dict[str, Any]) -> str | None:
    text_parts: list[str] = []
    for key in ("sentiment_reason", "tldr", "what_it_means"):
        value = str(payload.get(key) or "").strip().lower()
        if value:
            text_parts.append(value)
    for item in payload.get("key_implications") or []:
        value = str(item or "").strip().lower()
        if value:
            text_parts.append(value)
    combined = " ".join(text_parts)
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in combined:
            return phrase
    return None


# Conservative, meaning-preserving substitutions for advisory wording that does
# NOT change the factual claim. Ordered longest-stem-first so inflections are
# replaced before their shorter roots. buy / sell / advise / predict / "upside
# potential" are intentionally absent — rewriting those could alter meaning, so
# they keep tripping the validator and must go to retry or be rejected.
# Replacement text is verified below to contain no forbidden substring.
_SAFE_PHRASE_REWRITES: tuple[tuple["re.Pattern[str]", str], ...] = (
    (re.compile(r"\bsuggesting\b", re.I), "indicating"),
    (re.compile(r"\bsuggested\b", re.I), "indicated"),
    (re.compile(r"\bsuggestions\b", re.I), "indications"),
    (re.compile(r"\bsuggestion\b", re.I), "indication"),
    (re.compile(r"\bsuggests\b", re.I), "indicates"),
    (re.compile(r"\bsuggest\b", re.I), "indicate"),
    (re.compile(r"\brecommendations\b", re.I), "rating observations"),
    (re.compile(r"\brecommendation\b", re.I), "rating observation"),
    (re.compile(r"\bforecasted\b", re.I), "projected"),
    (re.compile(r"\bforecasting\b", re.I), "projecting"),
    (re.compile(r"\bforecasts\b", re.I), "forward-looking estimates"),
    (re.compile(r"\bforecast\b", re.I), "forward-looking estimate"),
    (re.compile(r"\bbullish outlook\b", re.I), "positive outlook"),
    (re.compile(r"\bbearish call\b", re.I), "negative assessment"),
)


def _case_like(matched: str, replacement: str) -> str:
    if matched[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _rewrite_safe_text(text: str) -> str:
    out = text
    for pattern, replacement in _SAFE_PHRASE_REWRITES:
        out = pattern.sub(
            lambda m, r=replacement: _case_like(m.group(0), r), out
        )
    return out


def _safe_rewrite_forbidden(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Conservatively rewrite low-risk advisory wording in user-visible fields.

    Returns ``(possibly_rewritten_payload, cleared)``. ``cleared`` is True only
    if NO forbidden phrase remains after rewrite. Never rewrites
    buy/sell/advise/predict/"upside potential" — if those are present the
    payload stays forbidden and the caller must retry or reject it. Assumes the
    required fields are already complete (caller checks this first).
    """
    rewritten: dict[str, Any] = dict(payload)
    for key in ("sentiment_reason", "tldr", "what_it_means"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            rewritten[key] = _rewrite_safe_text(value)
    implications = payload.get("key_implications")
    if isinstance(implications, list):
        rewritten["key_implications"] = [
            _rewrite_safe_text(item) if isinstance(item, str) else item
            for item in implications
        ]
    cleared = _find_forbidden_phrase(rewritten) is None
    return rewritten, cleared


def _coerce_enrichment_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    score = payload.get("sentiment_score")
    if isinstance(score, str):
        try:
            score = float(score)
        except ValueError:
            score = score.strip()

    implications = payload.get("key_implications")
    if not isinstance(implications, list):
        implications = []

    return {
        "sentiment_score": score,
        "sentiment_reason": sanitize_text_field(payload.get("sentiment_reason"), fallback=""),
        "tldr": sanitize_text_field(payload.get("tldr"), fallback=""),
        "what_it_means": sanitize_text_field(payload.get("what_it_means"), fallback=""),
        "key_implications": [
            sanitize_text_field(item, fallback="")
            for item in implications[:4]
            if sanitize_text_field(item, fallback="")
        ],
        "impact_tag": str(payload.get("impact_tag") or "").strip().lower(),
    }


def _classify_json_failure(raw_text: str, parsed: dict[str, Any], error: str | None) -> str:
    if error:
        if "429" in error:
            return "llm_429"
        return "true_llm_failure"
    cleaned = raw_text.strip()
    if not cleaned:
        return "empty_llm_response"
    if parsed:
        return "missing_required_field"
    if "{" in cleaned and "}" not in cleaned:
        return "partial_json"
    if "{" in cleaned or "}" in cleaned:
        return "malformed_json"
    return "true_llm_failure"


def _recover_partial_json_object(raw_text: str) -> dict[str, Any]:
    """Salvage a truncated-but-mostly-valid JSON object.

    The reasoning model frequently emits a correct object whose tail (usually
    inside ``key_implications``) is cut off by the token limit, leaving
    unbalanced quotes/brackets. We recover by closing the structure, and if
    that fails, by falling back to the last fully-completed top-level pair —
    so the complete leading scalar fields (sentiment_score, sentiment_reason,
    tldr, what_it_means) survive even when key_implications is truncated.

    Only fields actually present in the raw output are recovered; nothing is
    fabricated. Returns {} when nothing valid can be salvaged.
    """
    cleaned = _strip_model_wrappers(raw_text).strip()
    if not cleaned.startswith("{"):
        return {}

    # Scan once, tracking string/escape state and the container stack, and
    # record the index just before the last depth-1 comma — the boundary at
    # which every preceding key:value pair is complete.
    stack: list[str] = []
    in_str = False
    esc = False
    last_pair_end: int | None = None
    for i, ch in enumerate(cleaned):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
        elif ch == "," and len(stack) == 1 and stack[0] == "{":
            last_pair_end = i

    def _closers(container_stack: list[str]) -> str:
        return "".join("}" if c == "{" else "]" for c in reversed(container_stack))

    candidates: list[str] = []

    # 1. Structure intact, not inside a string: drop a dangling trailing
    #    comma / colon / whitespace, then close open containers.
    if not in_str:
        trimmed = cleaned.rstrip()
        while trimmed and trimmed[-1] in ",:":
            trimmed = trimmed[:-1].rstrip()
        candidates.append(trimmed + _closers(stack))

    # 2. Truncated inside a string value: close the string, then containers.
    if in_str and not esc:
        candidates.append(cleaned + '"' + _closers(stack))

    # 3. Graceful degradation: keep only fully-completed leading pairs.
    if last_pair_end is not None:
        candidates.append(cleaned[:last_pair_end] + "}")

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except Exception:
            obj = extract_json_object(cand, {})
        if isinstance(obj, dict) and obj:
            return obj
    return {}


def assess_article_body_quality(article: dict[str, Any]) -> tuple[bool, str | None, str]:
    """Decide whether an extracted body is usable for LLM enrichment."""
    body = str(article.get("body") or "").strip()
    if not body:
        return False, "no_body", ""

    if body.startswith("[Paywalled]"):
        return False, "paywall_content", body
    if body.startswith("[Blocked]"):
        return False, "blocked_content", body
    if body.startswith("[No body extracted]"):
        return False, "no_body", body

    source_host = _article_source_host(article)
    if not source_host:
        source_host = _normalize_host(
            str(
                article.get("resolved_url")
                or article.get("canonical_url")
                or article.get("source_url")
                or article.get("url")
                or ""
            )
        )

    cleaned_body = _strip_article_boilerplate(body, source_host) or body
    cleaned_body, promo_removed = _strip_low_value_paragraphs(cleaned_body, source_host)
    lowered = cleaned_body.lower()
    raw_lowered = body.lower()

    if any(marker in raw_lowered for marker in _BLOCKED_PAGE_MARKERS):
        return False, "blocked_content", cleaned_body

    login_hits = sum(marker in raw_lowered for marker in _LOGIN_WALL_MARKERS)
    nav_hits = sum(marker in raw_lowered for marker in _NAVIGATION_MARKERS)
    cookie_hits = sum(marker in raw_lowered for marker in _COOKIE_MARKERS)
    sentence_paragraphs = _sentence_like_paragraphs(cleaned_body)
    cleaned_words = len(cleaned_body.split())
    original_words = max(1, len(body.split()))
    retained_ratio = cleaned_words / original_words
    company_tokens = _company_signal_tokens(article.get("company_name"), article.get("ticker") or "")
    company_signal_hits = sum(token in lowered for token in company_tokens)
    ticker_symbol_hit = _contains_ticker_symbol(
        f"{article.get('title') or ''} {cleaned_body}",
        str(article.get("ticker") or ""),
    )
    sports_hits = sum(marker in lowered for marker in _SPORTS_MARKERS)
    finance_hits = sum(marker in lowered for marker in _FINANCE_MARKERS)

    if promo_removed >= 1 and cleaned_words < 60:
        return False, "promo_menu_page", cleaned_body

    if "benzinga" in source_host and (
        "get benzinga pro" in raw_lowered
        or "benzinga edge" in raw_lowered
        or "benzinga premium services" in raw_lowered
    ):
        return False, "no_usable_content", cleaned_body

    if login_hits >= 2 and sentence_paragraphs < 3:
        return False, "login_wall", cleaned_body

    if cookie_hits >= 2 and sentence_paragraphs < 2:
        return False, "cookie_wall", cleaned_body

    if nav_hits >= 4 and (sentence_paragraphs < 3 or retained_ratio < 0.45):
        return False, "promo_menu_page", cleaned_body

    if sports_hits >= 4 and finance_hits < 2 and not ticker_symbol_hit:
        return False, "off_topic", cleaned_body

    if source_host in _GENERAL_NEWS_DOMAINS and finance_hits == 0 and not ticker_symbol_hit and company_signal_hits == 0:
        return False, "off_topic", cleaned_body

    if cleaned_words < 40:
        return False, "too_little_prose", cleaned_body

    title_tokens = _title_signal_tokens(str(article.get("title") or article.get("headline") or ""))
    title_signal_hits = sum(token in lowered for token in title_tokens)
    if title_tokens and title_signal_hits == 0 and sentence_paragraphs < 3 and nav_hits >= 2:
        return False, "ticker_mismatch", cleaned_body

    if company_tokens and company_signal_hits == 0 and not ticker_symbol_hit and promo_removed >= 1:
        return False, "ticker_mismatch", cleaned_body

    return True, None, cleaned_body


def _request_llm_json_diagnostic(
    prompt: str,
    *,
    max_tokens: int = 700,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    try:
        result_text = chatcompletion_text(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt or "You MUST respond with valid JSON only. No markdown. No explanation. Start with { and end with }.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            max_tokens=max_tokens,
        )
        parsed = extract_json_object(result_text, {})
        if not parsed:
            parsed = _recover_partial_json_object(result_text)
        return {
            "raw_text": result_text,
            "parsed": parsed if isinstance(parsed, dict) else {},
            "error": None,
        }
    except Exception as exc:
        logger.warning("LLM request failed: %s", exc)
        return {
            "raw_text": "",
            "parsed": {},
            "error": str(exc),
        }


async def _score_article_llm(
    ticker: str, headline: str, body: str
) -> dict[str, Any]:
    prompt = SENTIMENT_PROMPT.format(
        ticker=ticker,
        headline=headline[:300],
        body_excerpt=_truncate_text(body or "", 1200),
    )
    _, parsed = await asyncio.to_thread(_request_llm_json, prompt, 400)
    return parsed if isinstance(parsed, dict) else {}


async def _generate_tldr_llm(
    ticker: str, headline: str, body: str
) -> dict[str, Any]:
    prompt = TLDR_PROMPT.format(
        ticker=ticker,
        headline=headline[:300],
        body=_truncate_text(body or "", 2000),
    )
    _, parsed = await asyncio.to_thread(_request_llm_json, prompt, 600)
    return parsed if isinstance(parsed, dict) else {}


def _request_llm_json(prompt: str, max_tokens: int = 600) -> tuple[str, dict]:
    result = _request_llm_json_diagnostic(prompt, max_tokens=max_tokens)
    return str(result.get("raw_text") or ""), result.get("parsed") or {}


async def enrich_article_with_retry(
    *,
    ticker: str,
    headline: str,
    body: str,
    company_name: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    diagnostics: dict[str, Any] = {
        "attempts": 0,
        "llm_calls": 0,
        "llm_429s": 0,
        "failure_reason": None,
        "raw_llm_preview": "",
        "forbidden_rewritten": False,
    }
    excerpts = [1600, 900]
    last_forbidden: str | None = None
    last_parsed: dict[str, Any] | None = None

    for index, excerpt_limit in enumerate(excerpts):
        diagnostics["attempts"] += 1
        diagnostics["llm_calls"] += 1
        if index > 0 and last_forbidden and last_parsed:
            # Targeted correction: tell the model exactly which advisory phrase
            # tripped the validator and ask it to rewrite the SAME analysis
            # without changing the facts or the score.
            prior_json = json.dumps(
                {
                    k: last_parsed.get(k)
                    for k in (
                        "sentiment_score",
                        "sentiment_reason",
                        "tldr",
                        "what_it_means",
                        "key_implications",
                        "impact_tag",
                    )
                },
                ensure_ascii=False,
            )[:1400]
            prompt = ENRICHMENT_FORBIDDEN_RETRY_PROMPT.format(
                forbidden_phrase=last_forbidden,
                prior_json=prior_json,
            )
        elif index > 0:
            prompt = ENRICHMENT_RETRY_PROMPT.format(
                ticker=ticker,
                company_name=company_name or ticker,
                headline=headline[:300],
                body_excerpt=_truncate_text(body or "", excerpt_limit),
            )
        else:
            prompt = ENRICHMENT_PROMPT.format(
                ticker=ticker,
                company_name=company_name or ticker,
                headline=headline[:300],
                body_excerpt=_truncate_text(body or "", excerpt_limit),
            )
        response = await asyncio.to_thread(
            _request_llm_json_diagnostic,
            prompt,
            # 2000 (was 750): the reasoning model's verbose key_implications
            # overran 750 and truncated otherwise-valid JSON mid-string,
            # which dominated enrichment failures (missing_required_field).
            # Applies to both the first attempt and the retry.
            max_tokens=2000,
            system_prompt="Return one strict JSON object only. No markdown. No extra text. No commentary.",
        )
        raw_text = str(response.get("raw_text") or "")
        parsed = _coerce_enrichment_payload(response.get("parsed") or {})
        error = response.get("error")
        if error and "429" in str(error):
            diagnostics["llm_429s"] += 1
        diagnostics["raw_llm_preview"] = raw_text[:240]

        failure_reason = _classify_json_failure(raw_text, parsed, str(error) if error else None)
        if parsed and not error:
            required_fields = (
                parsed.get("sentiment_score") is not None
                and bool(parsed.get("sentiment_reason"))
                and bool(parsed.get("tldr"))
                and bool(parsed.get("what_it_means"))
            )
            if not required_fields:
                failure_reason = "missing_required_field"
            else:
                forbidden = _find_forbidden_phrase(parsed)
                if not forbidden:
                    diagnostics["failure_reason"] = None
                    return parsed, diagnostics
                # Deterministic safe rewrite of low-risk advisory wording
                # (suggests->indicates, recommendation->rating observation,
                # forecast->forward-looking estimate, bullish/bearish->...).
                # buy/sell/advise/predict are never rewritten — those still
                # fall through to the targeted retry / rejection.
                rewritten, cleared = _safe_rewrite_forbidden(parsed)
                if cleared:
                    diagnostics["failure_reason"] = None
                    diagnostics["forbidden_rewritten"] = True
                    return rewritten, diagnostics
                last_forbidden = forbidden
                last_parsed = parsed
                diagnostics["failure_reason"] = f"forbidden_phrase:{forbidden}"
                continue

        diagnostics["failure_reason"] = failure_reason

    return None, diagnostics


async def enrich_and_store_article(
    supabase,
    article: dict[str, Any],
    *,
    analysis_run_id: str | None = None,
    skip_existing: bool = True,
) -> dict[str, Any] | None:
    ticker = str(article.get("ticker") or "").strip().upper()
    headline = str(article.get("title") or article.get("headline") or "").strip()
    url = str(article.get("url") or article.get("source_url") or "").strip()
    source = str(article.get("source") or "").strip()
    published_at = str(article.get("published_at") or "")
    resolved_url = str(article.get("resolved_url") or url or "").strip()
    body = str(article.get("body") or "").strip()

    if not ticker or not headline:
        logger.debug("Skipping article — missing ticker or headline")
        return None

    event_hash = _compute_event_hash(ticker, resolved_url or url, headline)
    canonical_url = resolved_url or url

    # When skip_existing=True: skip the row only if it is FULLY ENRICHED
    # (sentiment_score IS NOT NULL). Rows that exist but have no sentiment are
    # extraction-complete but LLM-incomplete — they must be re-enriched, not skipped.
    # When skip_existing=False: fetch existing row to seed LLM fields so we never
    # overwrite non-null sentiment_score / tldr / what_it_means with a weaker pass.
    existing_llm: dict[str, Any] = {}
    if skip_existing:
        try:
            existing = (
                supabase.table("shared_ticker_events")
                .select("id,sentiment_score,sentiment_reason,impact_tag,tldr,what_it_means,key_implications")
                .eq("ticker", ticker)
                .eq("event_hash", event_hash)
                .limit(1)
                .execute()
            )
            if existing.data:
                row = existing.data[0]
                if row.get("sentiment_score") is not None:
                    # Fully enriched — skip
                    return row
                # Exists but unenriched — fall through to re-enrich, seeding existing LLM fields
                existing_llm = row
        except Exception:
            pass
    else:
        try:
            existing_row = (
                supabase.table("shared_ticker_events")
                .select("sentiment_score,sentiment_reason,impact_tag,tldr,what_it_means,key_implications")
                .eq("ticker", ticker)
                .eq("event_hash", event_hash)
                .limit(1)
                .execute()
            )
            if existing_row.data:
                existing_llm = existing_row.data[0]
        except Exception:
            pass

    is_paywalled = is_paywalled_domain(canonical_url)
    is_blocked = is_blocked_domain(canonical_url)

    if is_paywalled or (body and body.startswith("[Paywalled]")):
        body = "[Paywalled] " + headline
        extraction_status = "paywalled"
        is_paywalled = True
    elif is_blocked and (not body or len(body.split()) < 30):
        body = "[Blocked] " + headline
        extraction_status = "blocked"
    elif not body or len(body.split()) < 30:
        body = "[No body extracted] " + headline
        extraction_status = "failed"
    elif body:
        extraction_status = "success"
    else:
        body = headline
        extraction_status = "empty"

    rejection_reason: str | None = None
    if extraction_status == "success":
        body_is_usable, rejection_reason, cleaned_body = assess_article_body_quality(
            {
                **article,
                "title": headline,
                "headline": headline,
                "body": body,
                "resolved_url": resolved_url,
                "canonical_url": canonical_url,
                "source_url": canonical_url,
            }
        )
        body = cleaned_body
        if not body_is_usable:
            extraction_status = "failed"

    source_tier = classify_source_tier(source)
    recency_w, article_window = classify_recency_weight(published_at)
    source_w = source_weight_for_tier(source_tier)

    # Seed LLM fields from existing row. A non-null DB value is preserved;
    # a null DB value (or no existing row) triggers a fresh LLM call below.
    sentiment_score: Any = existing_llm.get("sentiment_score")
    sentiment_reason: str | None = existing_llm.get("sentiment_reason")
    impact_tag: str | None = existing_llm.get("impact_tag")
    tldr: str | None = existing_llm.get("tldr")
    what_it_means: str | None = existing_llm.get("what_it_means")
    key_implications: list | None = existing_llm.get("key_implications")

    body_has_content = (
        extraction_status == "success"
        and rejection_reason is None
        and bool(body)
        and not is_paywalled
        and len(body.split()) >= 40
    )
    scoring_text = body if body_has_content else ""

    if scoring_text and not is_paywalled and body_has_content and (
        sentiment_score is None or tldr is None or what_it_means is None
    ):
        enrichment, diagnostics = await enrich_article_with_retry(
            ticker=ticker,
            headline=headline,
            body=scoring_text,
            company_name=str(article.get("company_name") or "").strip() or None,
        )
        if enrichment is None:
            rejection_reason = str(diagnostics.get("failure_reason") or "true_llm_failure")
        else:
            if sentiment_score is None:
                sentiment_score = enrichment.get("sentiment_score")
                sentiment_reason = sanitize_text_field(enrichment.get("sentiment_reason"), fallback="")
                impact_tag_val = (enrichment.get("impact_tag") or "").strip().lower()
                valid_tags = {"financial-impact", "regulatory", "leadership", "product", "macro", "sector", "other"}
                impact_tag = impact_tag_val if impact_tag_val in valid_tags else None
            if tldr is None or what_it_means is None:
                new_tldr = sanitize_text_field(enrichment.get("tldr"), fallback="")
                new_what = sanitize_text_field(enrichment.get("what_it_means"), fallback="")
                tldr = new_tldr if new_tldr else tldr
                what_it_means = new_what if new_what else what_it_means
                raw_imp = enrichment.get("key_implications")
                if isinstance(raw_imp, list):
                    new_imp = [sanitize_text_field(item, fallback="") for item in raw_imp[:4]]
                    new_imp = [imp for imp in new_imp if imp]
                    key_implications = new_imp if new_imp else key_implications
                elif key_implications is None:
                    key_implications = []

    payload = {
        "ticker": ticker,
        "event_hash": event_hash,
        "title": sanitize_text_field(headline, fallback=""),
        "summary": sanitize_text_field(article.get("summary") or "", fallback=""),
        "source": sanitize_text_field(source, fallback=""),
        "source_url": canonical_url,
        "canonical_url": canonical_url,
        "published_at": published_at or None,
        "event_type": str(article.get("event_type") or "").strip() or None,
        "significance": "minor",
        "body": body,
        "body_length": len(body),
        "extraction_status": extraction_status,
        "paywalled": is_paywalled,
        "headline_only": False,
        "rejection_reason": rejection_reason,
        "sentiment_score": sentiment_score,
        "sentiment_reason": sentiment_reason,
        "source_tier": source_tier,
        "recency_weight": recency_w,
        "source_weight": source_w,
        "impact_tag": impact_tag,
        "article_window": article_window,
        "tldr": tldr,
        "what_it_means": what_it_means,
        "key_implications": key_implications or [],
        "tags": article.get("tags") or [],
        "analysis_run_id": analysis_run_id,
        "analysis_status": "complete" if rejection_reason is None and sentiment_score is not None else "enrichment_failed" if rejection_reason else None,
        "factored_into_score": False,
        "provenance": "news_pipeline_v2",
        "methodology_version": "v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        def _do_upsert():
            return (
                supabase.table("shared_ticker_events")
                .upsert(payload, on_conflict="ticker,event_hash")
                .execute()
            )
        result = await asyncio.to_thread(_do_upsert)
        if result.data:
            return result.data[0]
    except Exception as exc:
        logger.error("Failed to store article for %s: %s", ticker, exc)

    return None


async def enrich_and_store_articles_batch(
    supabase,
    articles: list[dict[str, Any]],
    *,
    analysis_run_id: str | None = None,
    max_concurrency: int = 5,
    skip_existing: bool = True,
) -> list[dict[str, Any]]:
    if not articles:
        return []

    articles_to_process = articles
    if skip_existing:
        # Batch pre-check: one query instead of N individual per-article SELECTs
        hash_map: dict[str, dict[str, Any]] = {}
        for a in articles:
            _ticker = str(a.get("ticker") or "").strip().upper()
            _url = str(a.get("url") or a.get("source_url") or "").strip()
            _resolved = str(a.get("resolved_url") or _url).strip()
            _headline = str(a.get("title") or a.get("headline") or "").strip()
            _h = _compute_event_hash(_ticker, _resolved or _url, _headline)
            hash_map[_h] = a

        def _batch_lookup():
            return (
                supabase.table("shared_ticker_events")
                .select("event_hash,sentiment_score")
                .in_("event_hash", list(hash_map.keys()))
                .execute()
                .data or []
            )
        try:
            existing_rows = await asyncio.to_thread(_batch_lookup)
            # Only skip rows that are FULLY enriched (sentiment_score is set).
            # Rows that exist but have sentiment_score=NULL were extracted without LLM
            # enrichment and must be re-processed — not skipped.
            existing_hashes = {
                r["event_hash"] for r in existing_rows
                if r.get("sentiment_score") is not None
            }
        except Exception:
            existing_hashes = set()

        articles_to_process = [a for h, a in hash_map.items() if h not in existing_hashes]

    if not articles_to_process:
        return []

    sem = asyncio.Semaphore(max_concurrency)

    async def _process(article):
        async with sem:
            return await enrich_and_store_article(
                supabase, article, analysis_run_id=analysis_run_id,
                skip_existing=False,  # already filtered by batch pre-check above
            )

    results = await asyncio.gather(*(_process(a) for a in articles_to_process))
    return [r for r in results if r is not None]


async def ingest_and_enrich_ticker_news(
    supabase,
    tickers: list[str],
    *,
    limit_per_ticker: int = 10,
    max_concurrency: int = 3,
) -> dict[str, int]:
    """Finnhub-first news ingestion: fetch → filter → extract → score → store.

    Primary: Finnhub company-news (7-day window) with inline body extraction.
    Fallback: Google News RSS, only for tickers with < GOOGLE_FALLBACK_MIN_USABLE_ARTICLES
    usable 7-day articles after Finnhub enrichment.

    Returns: dict of {ticker: articles_stored}.
    """
    from ..pipeline.finnhub_news import fetch_finnhub_ticker_news
    from ..pipeline.news_normalizer import normalize_news_batch
    from .article_scraper import enrich_articles_content
    from .candidate_ranker import rank_and_filter_candidates
    from .ticker_cache_service import get_metadata_map

    if not tickers:
        return {}

    results: dict[str, int] = {}

    # ── 1. Finnhub primary ────────────────────────────────────────────────────
    per_ticker_raw, _ = await fetch_finnhub_ticker_news(
        tickers, days=7, limit_per_ticker=limit_per_ticker
    )
    all_finnhub = [a for arts in per_ticker_raw.values() for a in arts]

    # Filter by domain policy before spending extraction budget
    filtered_finnhub = rank_and_filter_candidates(all_finnhub, skip_score_below=15.0)

    # Extract article bodies from Finnhub URLs
    if filtered_finnhub:
        extracted_finnhub = await enrich_articles_content(
            filtered_finnhub, max_concurrency=max_concurrency
        )
    else:
        extracted_finnhub = []

    # Store + LLM score
    finnhub_stored = await enrich_and_store_articles_batch(
        supabase, extracted_finnhub, max_concurrency=max_concurrency, skip_existing=True
    )
    for article in finnhub_stored:
        t = str(article.get("ticker") or "").strip().upper()
        if t in tickers:
            results[t] = results.get(t, 0) + 1

    # ── 2. Google tiered fallback ─────────────────────────────────────────────
    if not GOOGLE_NEWS_FALLBACK_ENABLED or GOOGLE_FALLBACK_MODE == "disabled":
        return results

    # Query DB for usable 7-day counts per ticker
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        rows = (
            supabase.table("shared_ticker_events")
            .select("ticker,extraction_status,paywalled,sentiment_score")
            .in_("ticker", list(tickers))
            .gte("published_at", cutoff)
            .execute()
            .data or []
        )
    except Exception:
        rows = []

    usable_by_ticker: dict[str, int] = {}
    for row in rows:
        t = str(row.get("ticker") or "").upper()
        if (
            row.get("extraction_status") == "success"
            and not row.get("paywalled", False)
            and row.get("sentiment_score") is not None
        ):
            usable_by_ticker[t] = usable_by_ticker.get(t, 0) + 1

    # Tiered fallback: determine which tickers need Google and why
    need_mvp_recovery = [
        t for t in tickers if usable_by_ticker.get(t, 0) < GOOGLE_FALLBACK_MVP_THRESHOLD
    ]
    need_production_boost = (
        []
        if GOOGLE_FALLBACK_MODE == "mvp_only"
        else [
            t for t in tickers
            if GOOGLE_FALLBACK_MVP_THRESHOLD <= usable_by_ticker.get(t, 0) < GOOGLE_FALLBACK_PRODUCTION_TARGET
            and t not in need_mvp_recovery
        ]
    )
    fallback_tickers = need_mvp_recovery + need_production_boost
    google_mode_map: dict[str, str] = {
        **{t: "mvp_recovery" for t in need_mvp_recovery},
        **{t: "production_boost" for t in need_production_boost},
    }

    if not fallback_tickers:
        return results

    logger.info(
        "[NEWS] Google fallback — mvp_recovery: %d, production_boost: %d tickers",
        len(need_mvp_recovery), len(need_production_boost),
    )

    from ..pipeline.rss_ingest import fetch_google_company_rss

    metadata_map = get_metadata_map(supabase, fallback_tickers)
    google_limit = max(
        limit_per_ticker,
        GOOGLE_FALLBACK_MAX_CANDIDATES_PER_TICKER,
    )
    google_raw = await fetch_google_company_rss(
        fallback_tickers,
        ticker_metadata=metadata_map,
        limit_per_ticker=google_limit,
    )
    google_normalized = normalize_news_batch(google_raw, "company_news") if google_raw else []

    # Cap per-ticker extraction to avoid runaway cost on production_boost tickers
    if GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER > 0:
        per_t: dict[str, int] = {}
        capped: list[dict] = []
        for a in google_normalized:
            t = str(a.get("ticker") or "").strip().upper()
            if per_t.get(t, 0) < GOOGLE_FALLBACK_MAX_EXTRACTIONS_PER_TICKER:
                capped.append(a)
                per_t[t] = per_t.get(t, 0) + 1
        google_normalized = capped

    google_stored = await enrich_and_store_articles_batch(
        supabase, google_normalized, max_concurrency=max_concurrency, skip_existing=True
    )
    for article in google_stored:
        t = str(article.get("ticker") or "").strip().upper()
        if t in tickers:
            results[t] = results.get(t, 0) + 1

    return results
