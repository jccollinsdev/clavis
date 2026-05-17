"""Candidate ranking and source access policy for the news pipeline.

Scores article candidates before extraction budget is spent. Deprioritizes
known-blocked/paywalled/low-value domains so we don't waste extraction
attempts and Google decode quota on unextractable articles.

Domain policy is evidence-based from observed extraction success rates:
- reuters.com:    0% success (24 attempts)
- msn.com:        0% success (14 attempts)
- bloomberg.com:  0% success + paywalled
- marketbeat.com: 10% success (19 attempts)
- chartmill.com:   7% success (15 attempts)
- stocktitan.net:  9% success (11 attempts)
- benzinga.com:   90% success
- fool.com:       78% success
- cnbc.com:       75% success
- finnhub.io:     69% success
"""
from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

# --- Domain access policy ---

DomainPolicy = Literal["open", "sometimes", "blocked", "paywalled", "low_value", "spam"]

_DOMAIN_POLICY: dict[str, DomainPolicy] = {
    # Open/high-success sources (prefer these)
    "benzinga.com": "open",
    "prnewswire.com": "open",
    "businesswire.com": "open",
    "globenewswire.com": "open",
    "accesswire.com": "open",
    "fool.com": "open",
    "cnbc.com": "open",
    "cnn.com": "sometimes",
    "trefis.com": "open",
    "247wallst.com": "open",
    "apple.com": "open",
    "nasdaq.com": "open",
    "ir.com": "open",

    # Finance/news sources with moderate success
    "finance.yahoo.com": "sometimes",
    "yahoo.com": "sometimes",
    "apnews.com": "sometimes",
    "wpr.org": "sometimes",
    "pymnts.com": "open",
    "foreignpolicyjournal.com": "sometimes",

    # Paywalled — will not extract body (but keep headline)
    "wsj.com": "paywalled",
    "bloomberg.com": "paywalled",
    "ft.com": "paywalled",
    "barrons.com": "paywalled",
    "marketwatch.com": "paywalled",
    "thetimes.com": "paywalled",
    "nytimes.com": "paywalled",
    "morningstar.com": "paywalled",
    "global.morningstar.com": "paywalled",
    "news.microsoft.com": "paywalled",

    # Blocked/anti-bot — 0% success, waste extraction budget
    "reuters.com": "blocked",
    "msn.com": "blocked",
    "news.bloomberglaw.com": "blocked",
    "thestreet.com": "blocked",
    "investing.com": "blocked",
    "financialpost.com": "blocked",

    # Low-value — chart/technical/ratings sites with near-0% extraction
    "marketbeat.com": "low_value",
    "chartmill.com": "low_value",
    "stocktitan.net": "low_value",
    "macroaxis.com": "low_value",
    "tipranks.com": "low_value",
    "barchart.com": "low_value",
    "simplywall.st": "low_value",
    "wisesheets.io": "low_value",
    "stockanalysis.com": "low_value",

    # Spam/irrelevant — government, encyclopedia, unrelated sites
    "news.santaclaracounty.gov": "spam",
    "sec.gov": "spam",
    "britannica.com": "spam",
}

# Domains where title clearly indicates spam/irrelevant article
_SPAM_TITLE_PATTERNS = re.compile(
    r"\b(13[fg]|13 [fg]|ownership|sec filing|form 4|proxy statement"
    r"|etf holdings|mutual fund|index constituent"
    r"|price prediction|technical analysis|target price raised|analyst rating"
    r"|buy or sell\?|should you buy|is it a buy"
    r"|\$\d+[kKmMbB] in \d+)",
    re.IGNORECASE,
)

# Source URLs that are clearly not article bodies
_NON_ARTICLE_PATH_PATTERNS = re.compile(
    r"/(quote|chart|charts|screener|portfolio|login|signup|subscribe"
    r"|account|profile|search|tag|category|author|about|contact)/",
    re.IGNORECASE,
)


def _normalize_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host.removeprefix("www.")
    except Exception:
        return ""


def get_domain_policy(url: str) -> DomainPolicy:
    """Return the access policy for a URL's domain."""
    domain = _normalize_domain(url)
    if not domain:
        return "sometimes"
    # Exact match first
    if domain in _DOMAIN_POLICY:
        return _DOMAIN_POLICY[domain]
    # Suffix match (e.g. "news.cnbc.com" → "cnbc.com")
    for key, policy in _DOMAIN_POLICY.items():
        if domain.endswith(f".{key}"):
            return policy
    return "sometimes"  # unknown — allow with budget cap


def _is_spam_title(title: str) -> bool:
    return bool(_SPAM_TITLE_PATTERNS.search(title or ""))


def _is_non_article_url(url: str) -> bool:
    try:
        path = urlparse(url).path.lower()
        return bool(_NON_ARTICLE_PATH_PATTERNS.search(path))
    except Exception:
        return False


def _is_google_wrapper_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
        return "news.google.com" in host
    except Exception:
        return False


def score_candidate(article: dict) -> tuple[float, str]:
    """Score an article candidate (0-100). Returns (score, reason).

    Higher score = higher priority for extraction.
    Score below 20 = should be skipped entirely.
    """
    url = str(article.get("url") or article.get("source_url") or "").strip()
    title = str(article.get("title") or "").strip()
    source_url = str(article.get("source_url") or "").strip()
    published_at = str(article.get("published_at") or "").strip()

    # Use source_url (publisher domain) for policy check when url is a Google wrapper
    policy_url = source_url if _is_google_wrapper_url(url) and source_url else url
    policy = get_domain_policy(policy_url)

    # Hard rejections
    if policy == "spam":
        return 0.0, f"spam_domain:{_normalize_domain(policy_url)}"

    if policy == "blocked":
        return 5.0, f"blocked_domain:{_normalize_domain(policy_url)}"

    if _is_spam_title(title):
        return 8.0, "spam_title_pattern"

    if _is_non_article_url(url) and not _is_google_wrapper_url(url):
        return 10.0, "non_article_url"

    score = 50.0

    # Domain quality bonus/penalty
    if policy == "open":
        score += 25.0
    elif policy == "paywalled":
        # Paywalled: can still extract headline; penalize but don't zero-out
        score -= 30.0
    elif policy == "low_value":
        score -= 25.0
    # "sometimes" and "unknown" → no adjustment

    # Direct URL (not a google wrapper) → prefer
    if not _is_google_wrapper_url(url):
        score += 10.0

    # Has Finnhub summary → richer signal available
    if article.get("summary") and len(str(article.get("summary") or "")) > 50:
        score += 5.0

    # Recent publication
    if published_at:
        import re as _re
        # If within 24h → small bonus (recency_weight handles the scoring weight)
        if _re.search(r"2026-05-1[5-6]", published_at):
            score += 5.0

    return min(max(score, 0.0), 100.0), f"policy={policy}"


def rank_and_filter_candidates(
    articles: list[dict],
    *,
    skip_score_below: float = 15.0,
    max_candidates: int | None = None,
) -> list[dict]:
    """Score, annotate, and rank candidates. Filters out those below threshold.

    Adds `candidate_score` and `candidate_rejection_reason` to each article.
    Returns ranked list (highest score first), skipping below threshold.
    """
    scored: list[tuple[float, dict]] = []
    rejected: list[dict] = []

    for article in articles:
        sc, reason = score_candidate(article)
        enriched = {
            **article,
            "candidate_score": round(sc, 1),
            "candidate_rejection_reason": reason if sc < skip_score_below else None,
            "domain_policy": get_domain_policy(
                str(article.get("source_url") or article.get("url") or "")
            ),
        }
        if sc < skip_score_below:
            rejected.append(enriched)
        else:
            scored.append((sc, enriched))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [a for _, a in scored]
    if max_candidates is not None:
        result = result[:max_candidates]
    return result


def should_decode_google_wrapper(article: dict) -> bool:
    """Return True if this Google-wrapped article is worth decoding.

    Skips decoding when:
    - source domain is blocked/spam/paywalled (save decode budget)
    - title is spam
    - already have a decoded/direct URL
    """
    url = str(article.get("url") or "").strip()
    if not _is_google_wrapper_url(url):
        return True  # not a wrapper, no decode needed

    source_url = str(article.get("source_url") or "").strip()
    if source_url:
        policy = get_domain_policy(source_url)
        if policy in ("blocked", "spam", "paywalled"):
            return False

    title = str(article.get("title") or "").strip()
    if _is_spam_title(title):
        return False

    return True
