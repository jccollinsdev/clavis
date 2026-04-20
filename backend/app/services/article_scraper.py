import asyncio
import re
import time
import warnings
from urllib.parse import parse_qs, quote_plus, unquote, urlparse, urlsplit

import httpx

_NEWSPAPER4K_LOADED = True
try:
    import newspaper
    from newspaper import Article as _NPArticle
except ImportError:
    _NEWSPAPER4K_LOADED = False
    _NPArticle = None

_BLOCK_TAG_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)


def _extract_with_newspaper4k(
    url: str,
) -> tuple[str, str, str, str] | tuple[None, None, None, None]:
    if not _NEWSPAPER4K_LOADED:
        return None, None, None, None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            article = _NPArticle(url)
            article.download()
            article.parse()
            text = article.text or ""
            title = article.title or ""
            authors = ", ".join(article.authors) if article.authors else ""
            publish_date = ""
            if article.publish_date:
                publish_date = article.publish_date.isoformat()
            return text, title, authors, publish_date
    except Exception:
        return None, None, None, None


_PARAGRAPH_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)

_GENERIC_BOILERPLATE_PHRASES = (
    "cookie",
    "accept all",
    "deny optional",
    "privacy policy",
    "terms of service",
    "subscribe to read",
    "sign in to continue",
    "continue reading",
    "related articles",
    "recommended stories",
    "advertisement",
    "powered by",
    "all rights reserved",
)

_SOURCE_BOILERPLATE_PHRASES = {
    "zacks.com": (
        "we use cookies",
        "this article originally appeared on zacks",
        "premium research",
    ),
    "finance.yahoo.com": (
        "yahoo finance",
        "sign in",
        "privacy dashboard",
    ),
    "marketwatch.com": (
        "marketwatch",
        "need to know",
        "stock picks",
    ),
    "reuters.com": (
        "our standards",
        "privacy policy",
        "thomson reuters",
    ),
    "stocktitan.net": (
        "stock titan",
        "free email alerts",
    ),
}

_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "after",
    "ahead",
    "as",
    "by",
    "for",
    "from",
    "in",
    "is",
    "last",
    "new",
    "of",
    "on",
    "outperform",
    "pulling",
    "rises",
    "stock",
    "the",
    "to",
    "with",
    "when",
}


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = _BLOCK_TAG_RE.sub(" ", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"&amp;", "&", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_article_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = _strip_html(raw_line)
        if line:
            lines.append(line)
    return lines


def _is_boilerplate_line(line: str, source_host: str = "") -> bool:
    normalized = str(line or "").lower()
    if not normalized:
        return True
    if normalized.startswith(("title:", "url source:", "published time:")):
        return True
    if len(normalized) < 18 and not any(ch in normalized for ch in (".", ":", ",")):
        return True
    if any(phrase in normalized for phrase in _GENERIC_BOILERPLATE_PHRASES):
        return True
    for host_key, phrases in _SOURCE_BOILERPLATE_PHRASES.items():
        if host_key in source_host and any(phrase in normalized for phrase in phrases):
            return True
    return False


def _strip_article_boilerplate(text: str, source_host: str = "") -> str:
    cleaned: list[str] = []
    for line in _normalize_article_lines(text):
        if _is_boilerplate_line(line, source_host):
            continue
        cleaned.append(line)

    deduped: list[str] = []
    for line in cleaned:
        if not deduped or deduped[-1] != line:
            deduped.append(line)

    return "\n\n".join(deduped).strip()


def _slugify_article_title(article: dict) -> str:
    title = str(article.get("title") or "").strip()
    parts = [
        token.lower()
        for token in re.split(r"[^A-Za-z0-9]+", title)
        if len(token) >= 3 and token.lower() not in _QUERY_STOPWORDS
    ]
    return "-".join(parts[:12])


def _direct_publisher_candidates(article: dict) -> list[dict]:
    candidates: list[dict] = []
    source_url = str(article.get("source_url") or "").strip()
    source_host = _article_source_host(article)
    slug = _slugify_article_title(article)

    if source_url:
        try:
            parsed = urlsplit(source_url)
            path = parsed.path.rstrip("/")
            if path and len(path) > 1:
                candidates.append(
                    {
                        "url": source_url,
                        "query": "source_url_exact",
                        "query_index": -2,
                        "search_rank": 0,
                    }
                )
                base_path = path.rsplit("/", 1)[0]
                if base_path and len(base_path) > 1:
                    candidates.append(
                        {
                            "url": f"{parsed.scheme}://{parsed.netloc}{base_path}/",
                            "query": "source_url_directory",
                            "query_index": -2,
                            "search_rank": 1,
                        }
                    )
        except Exception:
            pass

    if not source_host or not slug:
        return candidates

    candidate_paths = [
        f"/{slug}",
        f"/news/{slug}",
        f"/article/{slug}",
        f"/articles/{slug}",
        f"/markets/{slug}",
        f"/stock/{slug}",
    ]
    for index, path in enumerate(candidate_paths):
        candidates.append(
            {
                "url": f"https://{source_host}{path}",
                "query": "direct_host_probe",
                "query_index": -1,
                "search_rank": index + 2,
            }
        )
    return candidates


def _maybe_extract_source_specific_body(html: str, article: dict) -> str:
    source_host = _article_source_host(article)
    body = _extract_body_text(html)
    body = _strip_article_boilerplate(body, source_host)
    if body:
        return body

    raw_body = _strip_html(html or "")
    return _strip_article_boilerplate(raw_body, source_host)[:5000]


def _extract_body_text(html: str) -> str:
    paragraphs = [_strip_html(match) for match in _PARAGRAPH_RE.findall(html or "")]
    paragraphs = [paragraph for paragraph in paragraphs if len(paragraph) >= 60]
    if paragraphs:
        return _strip_article_boilerplate("\n\n".join(paragraphs[:8])[:5000])

    meta_match = _META_RE.search(html or "")
    if meta_match:
        return _strip_article_boilerplate(_strip_html(meta_match.group(1))[:1200])

    return _strip_article_boilerplate(_strip_html(html or "")[:2000])


def _extract_title(html: str) -> str:
    match = _TITLE_RE.search(html or "")
    if not match:
        return ""
    return _strip_html(match.group(1))[:300]


def _extract_proxy_body(text: str, source_host: str = "") -> str:
    if not text:
        return ""

    lines = str(text).splitlines()
    content_start = 0
    for idx, line in enumerate(lines):
        if line.strip().lower() == "markdown content:":
            content_start = idx + 1
            break

    body = "\n".join(lines[content_start:]).strip()
    body = re.sub(r"^Title:.*$", "", body, flags=re.MULTILINE)
    body = re.sub(r"^URL Source:.*$", "", body, flags=re.MULTILINE)
    body = re.sub(r"^Published Time:.*$", "", body, flags=re.MULTILINE)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return _strip_article_boilerplate(body.strip(), source_host)


def _looks_like_security_or_chrome_page(text: str) -> bool:
    normalized = str(text or "").lower()
    return any(
        phrase in normalized
        for phrase in (
            "security verification",
            "performing security verification",
            "verify you are not a bot",
            "are you a human",
            "access denied",
            "choose your location",
            "see all locations",
            "customize your news",
            "partner with us",
            "about us",
            "sign in",
            "help center",
            "local news",
        )
    )


async def _fetch_proxy_text(url: str, client: httpx.AsyncClient) -> str:
    stripped = str(url or "").strip()
    if not stripped:
        return ""

    if stripped.startswith("https://r.jina.ai/"):
        proxy_url = stripped
    else:
        normalized = stripped.removeprefix("https://").removeprefix("http://")
        proxy_url = f"https://r.jina.ai/http://{normalized}"

    response = await _get_with_backoff(client, proxy_url)
    return response.text or ""


def _is_google_wrapper(resolved_url: str, html: str) -> bool:
    host = urlparse(resolved_url).netloc.lower()
    if host.endswith("news.google.com"):
        return True
    return "news.google.com/rss/articles" in (html or "")[:500]


async def _get_with_backoff(
    client: httpx.AsyncClient,
    url: str,
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
) -> httpx.Response:
    last_error: Exception | None = None
    retry_statuses = {429, 500, 502, 503, 504}
    for attempt in range(max(1, attempts)):
        try:
            response = await client.get(url)
            if response.status_code in retry_statuses and attempt < attempts - 1:
                await asyncio.sleep(base_delay * (2**attempt))
                continue
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in retry_statuses and attempt < attempts - 1:
                await asyncio.sleep(base_delay * (2**attempt))
                continue
            raise
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                await asyncio.sleep(base_delay * (2**attempt))
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("request failed")


def _normalize_host(value: str | None) -> str:
    host = urlparse(str(value or "").strip()).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _article_source_host(article: dict) -> str:
    source_url = str(article.get("source_url") or "").strip()
    if source_url:
        return _normalize_host(source_url)
    source = str(article.get("source") or "").strip().lower()
    return source.replace(" ", "")


def _search_queries(article: dict) -> list[str]:
    title = str(article.get("title") or "").strip()
    source_host = _article_source_host(article)
    source = str(article.get("source") or "").strip()
    ticker = str(article.get("ticker") or "").strip().upper()
    company_name = str(article.get("company_name") or "").strip()
    queries: list[str] = []
    if not title:
        return queries

    title_tokens = [
        token.lower()
        for token in re.split(r"[^A-Za-z0-9]+", title)
        if len(token) >= 3 and token.lower() not in _QUERY_STOPWORDS
    ]
    keyword_phrase = " ".join(dict.fromkeys(title_tokens) or [title.lower()]).strip()

    if source_host:
        if ticker:
            queries.append(f"site:{source_host} {keyword_phrase} {ticker}")
        queries.append(f"site:{source_host} {keyword_phrase}")
    if source:
        queries.append(f"{keyword_phrase} {source}")
    if company_name:
        queries.append(f"{keyword_phrase} {company_name}")
        if ticker:
            queries.append(f"{keyword_phrase} {company_name} {ticker}")
    if ticker:
        queries.append(f"{keyword_phrase} {ticker}")
    queries.append(keyword_phrase)
    queries.append(title)
    return list(dict.fromkeys(queries))


def _headline_tokens(article: dict) -> list[str]:
    title = str(article.get("title") or "").strip()
    return [
        token.lower()
        for token in re.split(r"[^A-Za-z0-9]+", title)
        if len(token) >= 3 and token.lower() not in _QUERY_STOPWORDS
    ]


def _extract_ddg_urls(markdown: str) -> list[str]:
    urls: list[str] = []
    pattern = re.compile(r"\]\((https?://duckduckgo\.com/l/\?uddg=[^)]+)\)")
    for match in pattern.finditer(markdown or ""):
        parsed = urlparse(match.group(1))
        query = parse_qs(parsed.query)
        candidate = query.get("uddg", [""])[0]
        if candidate:
            urls.append(unquote(candidate))
    return urls


async def _search_resolved_urls(article: dict, client: httpx.AsyncClient) -> list[str]:
    queries = _search_queries(article)
    if not queries:
        return []

    results: list[str] = []
    for query in queries[:5]:
        search_url = "https://r.jina.ai/http://duckduckgo.com/html/?q=" + quote_plus(
            query
        )
        response = await client.get(search_url)
        response.raise_for_status()
        results.extend(_extract_ddg_urls(response.text))
    seen: set[str] = set()
    deduped: list[str] = []
    for url in results:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _candidate_host_score(candidate_url: str, article: dict) -> tuple[int, int]:
    candidate_host = _normalize_host(candidate_url)
    source_host = _article_source_host(article)
    source = str(article.get("source") or "").strip().lower()
    path = urlparse(candidate_url).path.lower()
    headline_tokens = _headline_tokens(article)

    match = 0
    if source_host and (
        candidate_host == source_host
        or candidate_host.endswith(f".{source_host}")
        or source_host.endswith(f".{candidate_host}")
    ):
        match += 4
    if source and source.replace(" ", "") in candidate_host:
        match += 2
    if candidate_host.endswith("google.com") or candidate_host.endswith(
        "duckduckgo.com"
    ):
        match -= 10

    if path.count("/") <= 3 and path.endswith("/"):
        match -= 8
    token_hits = sum(1 for token in headline_tokens[:6] if token in path)
    match += min(6, token_hits * 2)

    path_score = 2 if len(path) > 20 else 0
    if token_hits:
        path_score += 2
    return match, path_score


def _evaluate_candidate_body(
    article: dict, body: str, resolved_url: str, *, method: str
) -> dict:
    normalized_body = str(body or "").strip()
    body_lower = normalized_body.lower()
    resolved_host = _normalize_host(resolved_url)
    source_host = _article_source_host(article)
    title_tokens = _headline_tokens(article)
    title_hits = sum(1 for token in title_tokens[:8] if token in body_lower)
    word_count = len(normalized_body.split())

    if not normalized_body:
        return {
            "accepted": False,
            "failure_reason": "empty_body",
            "word_count": 0,
            "title_hits": 0,
            "resolved_host": resolved_host,
            "method": method,
        }

    if _looks_like_security_or_chrome_page(normalized_body):
        return {
            "accepted": False,
            "failure_reason": "security_or_portal_page",
            "word_count": word_count,
            "title_hits": title_hits,
            "resolved_host": resolved_host,
            "method": method,
        }

    if "news.google.com" in resolved_host:
        return {
            "accepted": False,
            "failure_reason": "google_wrapper",
            "word_count": word_count,
            "title_hits": title_hits,
            "resolved_host": resolved_host,
            "method": method,
        }

    source_match = bool(
        source_host
        and (
            resolved_host == source_host
            or resolved_host.endswith(f".{source_host}")
            or source_host.endswith(f".{resolved_host}")
        )
    )

    acceptance_score = 0
    if word_count >= 120:
        acceptance_score += 3
    elif word_count >= 80:
        acceptance_score += 2
    elif word_count >= 60:
        acceptance_score += 1

    if title_hits >= 3:
        acceptance_score += 2
    elif title_hits >= 2:
        acceptance_score += 1

    if source_match:
        acceptance_score += 1

    if (
        any(
            phrase in body_lower
            for phrase in (
                "subscribe to read",
                "sign in to continue",
                "continue reading",
                "related articles",
            )
        )
        and word_count < 160
    ):
        acceptance_score -= 2

    accepted = acceptance_score >= 3 or (word_count >= 140 and title_hits >= 1)
    failure_reason = "" if accepted else "insufficient_article_signal"
    return {
        "accepted": accepted,
        "failure_reason": failure_reason,
        "word_count": word_count,
        "title_hits": title_hits,
        "resolved_host": resolved_host,
        "source_match": source_match,
        "acceptance_score": acceptance_score,
        "method": method,
    }


async def _search_resolved_candidates(
    article: dict, client: httpx.AsyncClient
) -> tuple[list[dict], dict]:
    queries = _search_queries(article)
    if not queries:
        return [], {"query_errors": [], "query_count": 0}

    candidates: list[dict] = []
    seen: set[str] = set()
    debug = {"query_errors": [], "query_count": min(len(queries), 5)}
    for query_index, query in enumerate(queries[:5]):
        search_url = "https://r.jina.ai/http://duckduckgo.com/html/?q=" + quote_plus(
            query
        )
        try:
            response = await _get_with_backoff(client, search_url, attempts=3)
        except Exception as exc:
            debug["query_errors"].append(
                {
                    "query": query,
                    "query_index": query_index,
                    "search_url": search_url,
                    "error": str(exc),
                }
            )
            continue

        urls = _extract_ddg_urls(response.text)
        if not urls:
            debug["query_errors"].append(
                {
                    "query": query,
                    "query_index": query_index,
                    "search_url": search_url,
                    "error": "no_urls_extracted",
                }
            )
            continue

        for rank, url in enumerate(urls):
            if url in seen:
                continue
            seen.add(url)
            candidates.append(
                {
                    "url": url,
                    "query": query,
                    "query_index": query_index,
                    "search_rank": rank,
                }
            )
    return candidates, debug


async def _probe_source_url_path(
    article: dict, client: httpx.AsyncClient
) -> tuple[dict | None, dict]:
    source_url = str(article.get("source_url") or "").strip()
    if not source_url:
        return None, {}

    attempt_log: dict = {"method": "source_url_probe", "url": source_url}
    try:
        np_text, np_title, np_authors, np_date = _extract_with_newspaper4k(source_url)
        if np_text and len(np_text.split()) >= 60:
            np_body = _strip_article_boilerplate(np_text, _normalize_host(source_url))
            np_eval = _evaluate_candidate_body(
                article, np_body, source_url, method="newspaper4k"
            )
            word_count = np_eval.get("word_count", 0)
            if np_eval["accepted"] or word_count >= 80:
                resolved_host = _normalize_host(source_url)
                source_host = _article_source_host(article)
                source_match = bool(
                    source_host
                    and (
                        resolved_host == source_host
                        or resolved_host.endswith(f".{source_host}")
                        or source_host.endswith(f".{resolved_host}")
                    )
                )
                return {
                    **article,
                    "title": np_title or article.get("title") or "",
                    "body": np_body,
                    "resolved_url": source_url,
                    "content_source": resolved_host or article.get("source") or "",
                    "scrape_status": "resolved_source_url_newspaper4k",
                    "resolution_status": "resolved_source_url",
                    "resolution_failure_reason": "",
                    "resolution_debug": {
                        "method": "newspaper4k",
                        "evaluation": np_eval,
                        "source_match": source_match,
                    },
                }, attempt_log

        response = await _get_with_backoff(client, source_url, attempts=2)
        html = response.text or ""
        resolved_url = str(response.url)
        if _is_google_wrapper(resolved_url, html):
            attempt_log["result"] = "google_wrapper"
            return None, attempt_log

        body = _maybe_extract_source_specific_body(html, article)
        evaluation = _evaluate_candidate_body(
            article, body, resolved_url, method="html"
        )
        attempt_log["evaluation"] = evaluation

        if evaluation["accepted"] or evaluation.get("word_count", 0) >= 80:
            title = article.get("title") or _extract_title(html)
            resolved_host = _normalize_host(resolved_url)
            return {
                **article,
                "title": title,
                "body": body or article.get("body") or "",
                "resolved_url": resolved_url,
                "content_source": resolved_host or article.get("source") or "",
                "scrape_status": "resolved_source_url_html",
                "resolution_status": "resolved_source_url",
                "resolution_failure_reason": "",
                "resolution_debug": {"method": "html", "evaluation": evaluation},
            }, attempt_log

        if not evaluation["accepted"]:
            np_text2, np_title2, _, _ = _extract_with_newspaper4k(resolved_url)
            if np_text2 and len(np_text2.split()) >= 60:
                np_body2 = _strip_article_boilerplate(
                    np_text2, _normalize_host(resolved_url)
                )
                np_eval2 = _evaluate_candidate_body(
                    article, np_body2, resolved_url, method="newspaper4k"
                )
                if np_eval2["accepted"] or np_eval2.get("word_count", 0) >= 80:
                    return {
                        **article,
                        "title": np_title2 or article.get("title") or "",
                        "body": np_body2,
                        "resolved_url": resolved_url,
                        "content_source": _normalize_host(resolved_url)
                        or article.get("source")
                        or "",
                        "scrape_status": "resolved_source_url_newspaper4k",
                        "resolution_status": "resolved_source_url",
                        "resolution_failure_reason": "",
                        "resolution_debug": {
                            "method": "newspaper4k",
                            "evaluation": np_eval2,
                            "html_evaluation": evaluation,
                        },
                    }, attempt_log

        attempt_log["result"] = "weak_body"
        return None, attempt_log

    except Exception as exc:
        attempt_log["result"] = f"error:{exc}"
        return None, attempt_log


async def _resolve_publisher_article(
    article: dict, client: httpx.AsyncClient
) -> tuple[dict | None, dict]:
    debug: dict = {
        "failure_reason": "no_search_results",
        "attempts": [],
        "candidate_count": 0,
        "query_count": len(_search_queries(article)),
        "query_errors": [],
        "direct_candidate_count": 0,
        "source_url_probe_count": 0,
    }
    source_url_resolved, probe_debug = await _probe_source_url_path(article, client)
    debug["source_url_probe_count"] = 1
    if probe_debug:
        debug["attempts"].append(probe_debug)
    if source_url_resolved:
        source_url_resolved.setdefault("resolution_debug", debug)
        return source_url_resolved, debug

    direct_candidates = _direct_publisher_candidates(article)
    if direct_candidates:
        debug["direct_candidate_count"] = len(direct_candidates)
    try:
        search_candidates, search_debug = await _search_resolved_candidates(
            article, client
        )
    except Exception:
        debug["failure_reason"] = "search_lookup_failed"
        return None, debug

    debug["query_errors"] = search_debug.get("query_errors", [])
    candidates = direct_candidates + search_candidates
    if search_debug.get("query_errors") and not candidates:
        debug["failure_reason"] = "search_queries_failed"
    if not candidates:
        return None, debug

    debug["candidate_count"] = len(candidates)

    scored_candidates = sorted(
        candidates,
        key=lambda candidate: (
            _candidate_host_score(candidate["url"], article),
            max(0, 6 - int(candidate.get("search_rank") or 0)),
            max(0, 5 - int(candidate.get("query_index") or 0)),
        ),
        reverse=True,
    )

    for candidate in scored_candidates[:8]:
        candidate_url = candidate["url"]
        attempt = {
            "candidate_url": candidate_url,
            "query": candidate.get("query"),
            "query_index": candidate.get("query_index"),
            "search_rank": candidate.get("search_rank"),
            "candidate_host_score": _candidate_host_score(candidate_url, article),
            "attempts": [],
        }
        try:
            proxy_text = await _fetch_proxy_text(candidate_url, client)
            attempt["attempts"].append({"method": "proxy", "result": "fetched"})
            resolved_url = candidate_url
            body = _extract_proxy_body(proxy_text, _article_source_host(article))
            evaluation = _evaluate_candidate_body(
                article, body, resolved_url, method="proxy"
            )
            attempt["proxy_evaluation"] = evaluation
            if evaluation["accepted"]:
                title = article.get("title") or ""
                resolved = {
                    **article,
                    "title": title,
                    "body": body,
                    "resolved_url": resolved_url,
                    "content_source": _normalize_host(resolved_url)
                    or article.get("source")
                    or "",
                    "scrape_status": "resolved_search",
                    "resolution_status": "resolved_search",
                    "resolution_failure_reason": "",
                    "resolution_debug": {
                        **debug,
                        "attempts": debug["attempts"] + [attempt],
                    },
                }
                return resolved, {**debug, "attempts": debug["attempts"] + [attempt]}

            response = await _get_with_backoff(client, candidate_url, attempts=2)
            html = response.text or ""
            resolved_url = str(response.url)
            attempt["attempts"].append({"method": "html", "result": "fetched"})
            if _is_google_wrapper(resolved_url, html):
                attempt["html_evaluation"] = {
                    "accepted": False,
                    "failure_reason": "google_wrapper",
                }
                debug["attempts"].append(attempt)
                continue
            body = _maybe_extract_source_specific_body(html, article)
            evaluation = _evaluate_candidate_body(
                article, body, resolved_url, method="html"
            )
            attempt["html_evaluation"] = evaluation
            if not evaluation["accepted"]:
                np_text, np_title, _, _ = _extract_with_newspaper4k(resolved_url)
                if np_text and len(np_text.split()) >= 60:
                    np_body = _strip_article_boilerplate(
                        np_text, _normalize_host(resolved_url)
                    )
                    np_eval = _evaluate_candidate_body(
                        article, np_body, resolved_url, method="newspaper4k"
                    )
                    if np_eval["accepted"] or np_eval["word_count"] >= 80:
                        title = np_title or article.get("title") or ""
                        resolved = {
                            **article,
                            "title": title,
                            "body": np_body,
                            "resolved_url": resolved_url,
                            "content_source": _normalize_host(resolved_url)
                            or article.get("source")
                            or "",
                            "scrape_status": "resolved_search_newspaper4k",
                            "resolution_status": "resolved_search_newspaper4k",
                            "resolution_failure_reason": "",
                            "resolution_debug": {
                                **debug,
                                "attempts": debug["attempts"] + [attempt],
                            },
                        }
                        return resolved, {
                            **debug,
                            "attempts": debug["attempts"] + [attempt],
                        }
                debug["attempts"].append(attempt)
                continue
            title = article.get("title") or _extract_title(html)
            resolved = {
                **article,
                "title": title,
                "body": body or article.get("body") or article.get("summary") or "",
                "resolved_url": resolved_url,
                "content_source": _normalize_host(resolved_url)
                or article.get("source")
                or "",
                "scrape_status": "resolved_search",
                "resolution_status": "resolved_search",
                "resolution_failure_reason": "",
                "resolution_debug": {
                    **debug,
                    "attempts": debug["attempts"] + [attempt],
                },
            }
            return resolved, {**debug, "attempts": debug["attempts"] + [attempt]}
        except Exception:
            attempt["attempts"].append({"method": "fetch", "result": "error"})
            attempt["failure_reason"] = "candidate_fetch_failed"
            debug["attempts"].append(attempt)
            continue

    if debug["attempts"]:
        final_reason = "all_candidates_rejected"
        last_attempt = debug["attempts"][-1]
        for key in ("html_evaluation", "proxy_evaluation"):
            evaluation = last_attempt.get(key) or {}
            if evaluation.get("failure_reason"):
                final_reason = str(evaluation.get("failure_reason"))
                break
        debug["failure_reason"] = final_reason
    else:
        debug["failure_reason"] = "no_candidate_attempts"

    return None, debug


async def enrich_article_content(
    article: dict, client: httpx.AsyncClient | None = None
) -> dict:
    url = str(article.get("url") or "").strip()
    if not url:
        return article

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ClavisBot/1.0; +https://clavis.andoverdigital.com)",
            },
        )

    try:
        proxy_failure_reason = ""
        if not _is_google_wrapper(url, ""):
            try:
                proxy_text = await _fetch_proxy_text(url, client)
                proxy_body = _extract_proxy_body(
                    proxy_text, _article_source_host(article)
                )
                proxy_evaluation = _evaluate_candidate_body(
                    article, proxy_body, url, method="proxy"
                )
                if proxy_evaluation["accepted"]:
                    return {
                        **article,
                        "title": article.get("title") or _extract_title(proxy_text),
                        "body": proxy_body,
                        "resolved_url": url,
                        "content_source": _normalize_host(url)
                        or article.get("source")
                        or "",
                        "scrape_status": "ok_proxy",
                        "resolution_status": "resolved_proxy",
                        "resolution_failure_reason": "",
                        "resolution_debug": {
                            "method": "proxy",
                            "evaluation": proxy_evaluation,
                        },
                    }
                proxy_failure_reason = proxy_evaluation["failure_reason"]
            except Exception:
                proxy_failure_reason = "proxy_fetch_failed"

        response = await _get_with_backoff(client, url, attempts=2)
        html = response.text or ""
        resolved_url = str(response.url)
        if _is_google_wrapper(resolved_url, html):
            resolved_article, resolution_debug = await _resolve_publisher_article(
                article, client
            )
            if resolved_article is not None:
                resolved_article.setdefault("resolution_debug", resolution_debug)
                return resolved_article
            source_url = str(article.get("source_url") or "").strip()
            source_host = urlparse(source_url).netloc or article.get("source") or ""
            return {
                **article,
                "resolved_url": resolved_url,
                "content_source": source_host,
                "body": "",
                "scrape_status": "google_wrapper",
                "resolution_status": "unresolved_wrapper",
                "resolution_failure_reason": resolution_debug.get(
                    "failure_reason", proxy_failure_reason or "google_wrapper"
                ),
                "resolution_debug": resolution_debug,
            }
        body = _maybe_extract_source_specific_body(html, article)
        title = article.get("title") or _extract_title(html)
        html_evaluation = _evaluate_candidate_body(
            article, body, resolved_url, method="html"
        )

        if not html_evaluation["accepted"]:
            np_text, np_title, np_authors, np_date = _extract_with_newspaper4k(
                resolved_url
            )
            if np_text and len(np_text.split()) >= 60:
                np_body = _strip_article_boilerplate(
                    np_text, _normalize_host(resolved_url)
                )
                np_evaluation = _evaluate_candidate_body(
                    article, np_body, resolved_url, method="newspaper4k"
                )
                if np_evaluation["accepted"]:
                    return {
                        **article,
                        "title": np_title or title or article.get("title") or "",
                        "body": np_body,
                        "resolved_url": resolved_url,
                        "content_source": _normalize_host(resolved_url)
                        or article.get("source")
                        or "",
                        "scrape_status": "ok_newspaper4k",
                        "resolution_status": "resolved_newspaper4k",
                        "resolution_failure_reason": "",
                        "resolution_debug": {
                            "method": "newspaper4k",
                            "evaluation": np_evaluation,
                            "proxy_evaluation": proxy_evaluation
                            if proxy_failure_reason
                            else None,
                            "html_evaluation": html_evaluation,
                        },
                    }
                if np_evaluation["word_count"] >= 80:
                    return {
                        **article,
                        "title": np_title or title or article.get("title") or "",
                        "body": np_body,
                        "resolved_url": resolved_url,
                        "content_source": _normalize_host(resolved_url)
                        or article.get("source")
                        or "",
                        "scrape_status": "ok_newspaper4k",
                        "resolution_status": "resolved_newspaper4k",
                        "resolution_failure_reason": "",
                        "resolution_debug": {
                            "method": "newspaper4k",
                            "evaluation": np_evaluation,
                            "proxy_evaluation": proxy_evaluation
                            if proxy_failure_reason
                            else None,
                            "html_evaluation": html_evaluation,
                        },
                    }

        enriched = {
            **article,
            "title": title,
            "body": body or article.get("body") or article.get("summary") or "",
            "resolved_url": resolved_url,
            "content_source": urlparse(resolved_url).netloc
            or article.get("source")
            or "",
            "scrape_status": "ok",
            "resolution_status": (
                "resolved_html" if html_evaluation["accepted"] else "weak_html"
            ),
            "resolution_failure_reason": ""
            if html_evaluation["accepted"]
            else html_evaluation["failure_reason"],
            "resolution_debug": {"method": "html", "evaluation": html_evaluation},
        }
        return enriched
    except Exception as exc:
        return {
            **article,
            "scrape_status": f"error:{exc}",
            "resolution_status": "error",
            "resolution_failure_reason": str(exc),
            "resolution_debug": {"error": str(exc)},
        }
    finally:
        if owns_client:
            await client.aclose()


async def enrich_articles_content(
    articles: list[dict], max_concurrency: int = 10
) -> list[dict]:
    if not articles:
        return []

    started_at = time.monotonic()
    semaphore = httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ClavisBot/1.0; +https://clavis.andoverdigital.com)",
        },
    )
    gate = asyncio.Semaphore(max(1, max_concurrency))

    async def _run(article: dict) -> dict:
        async with gate:
            return await enrich_article_content(article, client=semaphore)

    try:
        enriched_articles = await asyncio.gather(
            *(_run(article) for article in articles)
        )
        print(
            f"[ARTICLE_ENRICH] Enriched {len(enriched_articles)}/{len(articles)} articles "
            f"in {time.monotonic() - started_at:.1f}s"
        )
        return enriched_articles
    finally:
        await semaphore.aclose()
