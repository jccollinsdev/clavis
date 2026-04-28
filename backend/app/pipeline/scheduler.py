import asyncio
import time
import logging
import httpx
from collections import Counter
from itertools import zip_longest
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .analysis_utils import utcnow_iso, clamp_score
from .news_normalizer import normalize_news_batch, _evidence_quality
from ..services.backfill_artifacts import record_stage, get_run_artifact_dir, begin_artifact_session, write_named_json, end_artifact_session, record_position_artifact
from ..services.ticker_cache_service import ensure_sp500_universe_seeded, list_active_sp500_tickers

ET = ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=ET)
active_runs: dict[str, asyncio.Task] = {}
active_sp500_backfills: dict[str, asyncio.Task] = {}
PROCESS_STARTED_AT = datetime.now(timezone.utc)
RUN_TIMEOUT_SECONDS = 25 * 60
STALE_RUN_HOURS = 1
POSITION_CONCURRENCY = 2
MAX_ARTICLES_PER_POSITION = 3
SCHEDULER_TABLE = "scheduler_jobs"
CACHE_TABLE = "analysis_cache"
COMPANY_ARTICLE_ENRICHMENT_CACHE_KIND = "company_article_enrichment_v1"
COMPANY_ARTICLE_ENRICHMENT_CACHE_TTL_HOURS = 24 * 365
DEFAULT_DIGEST_TIME = "07:00"
JOB_PREFIX = "user_"
SP500_DAILY_JOB_ID = "system_sp500_daily_refresh"
HOLDINGS_DAILY_AI_JOB_ID = "system_holdings_daily_ai_refresh"
SP500_BACKFILL_JOB_ID = "system_sp500_backfill"
NEWS_CLEANUP_JOB_ID = "system_news_cleanup"
SYSTEM_SP500_USER_ID = "00000000-0000-0000-0000-000000000001"
SP500_BACKFILL_TRIGGER = "sp500_backfill"
MAJOR_PRIORITY_KEYWORDS = (
    "earnings",
    "guidance",
    "ceo",
    "cfo",
    "sec",
    "doj",
    "regulator",
    "lawsuit",
    "bankruptcy",
    "merger",
    "acquisition",
    "opec",
    "fed",
    "tariff",
)


def _is_junk_article(article: dict) -> tuple[bool, str]:
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    low_value_markers = (
        "stock price",
        "quote & chart",
        "price, quote & chart",
        "stock underperforms",
        "underperforms friday when compared to competitors",
    )
    for marker in low_value_markers:
        if marker in text:
            return True, f"low_value_marker: {marker}"
    relevance = article.get("relevance") or {}
    event_type = str(relevance.get("event_type") or "").lower()
    if event_type in ("noise", "spam", "ad"):
        return True, f"irrelevant_event_type: {event_type}"
    return False, ""


def _dedupe_articles(articles: list[dict]) -> list[dict]:
    deduped = {}
    for article in articles:
        deduped[article["event_hash"]] = article
    return list(deduped.values())


def _article_targets_ticker(article: dict, ticker: str) -> bool:
    ticker_upper = str(ticker or "").strip().upper()
    if not ticker_upper:
        return False

    candidates = set()
    for value in article.get("ticker_hints", []) or []:
        normalized = str(value).strip().upper()
        if normalized:
            candidates.add(normalized)
    relevance = article.get("relevance") or {}
    for value in relevance.get("affected_tickers", []) or []:
        normalized = str(value).strip().upper()
        if normalized:
            candidates.add(normalized)
    article_ticker = str(article.get("ticker") or "").strip().upper()
    if article_ticker:
        candidates.add(article_ticker)
    return ticker_upper in candidates


def _refresh_company_article_evidence_quality(article: dict) -> dict:
    body = str(article.get("body") or "").strip()
    summary = str(article.get("summary") or "").strip()
    title = str(article.get("title") or "").strip()
    refreshed_quality = _evidence_quality(
        title, body, summary, raw_body=article.get("body")
    )
    relevance = dict(article.get("relevance") or {})
    if relevance:
        relevance["evidence_quality"] = refreshed_quality
    return {
        **article,
        "evidence_quality": refreshed_quality,
        "relevance": relevance or article.get("relevance") or {},
    }


def _company_article_resolution_report(
    company_articles: list[dict], company_articles_enriched: list[dict]
) -> dict:
    report = {
        "input_count": len(company_articles),
        "enriched_count": len(company_articles_enriched),
        "resolved_with_body": 0,
        "wrapper_only": 0,
        "error_count": 0,
        "resolved_search_count": 0,
        "by_ticker": {},
        "status_counts": {},
        "failure_reason_counts": {},
        "top_failure_reasons": [],
        "sample_resolved_titles": [],
        "sample_wrapper_titles": [],
        "coverage_rate": 0.0,
        "coverage_ok": False,
    }

    status_counts: Counter[str] = Counter()
    failure_reasons: Counter[str] = Counter()
    by_ticker: dict[str, dict[str, object]] = {}

    for raw_article, enriched_article in zip_longest(
        company_articles, company_articles_enriched, fillvalue={}
    ):
        ticker = (
            str(raw_article.get("ticker") or enriched_article.get("ticker") or "")
            .strip()
            .upper()
        )
        ticker_bucket = by_ticker.setdefault(
            ticker or "UNKNOWN",
            {
                "input_count": 0,
                "resolved_with_body": 0,
                "wrapper_only": 0,
                "error_count": 0,
                "resolved_search_count": 0,
                "status_counts": {},
            },
        )
        ticker_bucket["input_count"] = int(ticker_bucket["input_count"]) + 1

        status = (
            str(enriched_article.get("scrape_status") or "unknown").strip() or "unknown"
        )
        status_counts[status] += 1
        ticker_status_counts = Counter(ticker_bucket["status_counts"])
        ticker_status_counts[status] += 1
        ticker_bucket["status_counts"] = dict(ticker_status_counts)

        body = str(enriched_article.get("body") or "").strip()
        title = str(
            enriched_article.get("title") or raw_article.get("title") or ""
        ).strip()

        if body:
            report["resolved_with_body"] += 1
            ticker_bucket["resolved_with_body"] = (
                int(ticker_bucket["resolved_with_body"]) + 1
            )
            if status == "resolved_search":
                report["resolved_search_count"] += 1
                ticker_bucket["resolved_search_count"] = (
                    int(ticker_bucket["resolved_search_count"]) + 1
                )
            if len(report["sample_resolved_titles"]) < 5 and title:
                report["sample_resolved_titles"].append(
                    {"ticker": ticker or "UNKNOWN", "title": title, "status": status}
                )
        else:
            report["wrapper_only"] += 1
            ticker_bucket["wrapper_only"] = int(ticker_bucket["wrapper_only"]) + 1
            failure_reason = str(
                enriched_article.get("resolution_failure_reason") or status or "unknown"
            ).strip()
            if status.startswith("error"):
                report["error_count"] += 1
                ticker_bucket["error_count"] = int(ticker_bucket["error_count"]) + 1
            failure_reasons[failure_reason or "unknown"] += 1
            if len(report["sample_wrapper_titles"]) < 5 and title:
                report["sample_wrapper_titles"].append(
                    {"ticker": ticker or "UNKNOWN", "title": title, "status": status}
                )

    report["by_ticker"] = by_ticker
    report["status_counts"] = dict(status_counts)
    report["failure_reason_counts"] = dict(failure_reasons)
    report["top_failure_reasons"] = [
        {"reason": reason, "count": count}
        for reason, count in failure_reasons.most_common(10)
    ]
    report["coverage_rate"] = (
        round(report["resolved_with_body"] / report["input_count"], 3)
        if report["input_count"]
        else 0.0
    )
    report["coverage_ok"] = report["coverage_rate"] >= 0.35
    return report


def _project_shared_event_analysis(
    base_analysis: dict,
    article: dict,
    position: dict,
    inferred_labels: list[str] | None = None,
) -> dict:
    ticker = str(position.get("ticker") or "").strip().upper()
    direct_company = _article_targets_ticker(article, ticker)
    event_type = str((article.get("relevance") or {}).get("event_type") or "other")
    projection_note = (
        f"This is direct company coverage for {ticker}."
        if direct_company
        else f"This event is applied to {ticker} through a broader {event_type} read-through."
    )

    confidence = float(base_analysis.get("confidence") or 0.5)
    if direct_company:
        confidence = min(0.98, confidence + 0.08)
    else:
        confidence = max(0.3, confidence - 0.05)

    key_implications = list(base_analysis.get("key_implications") or [])
    recommended_followups = list(base_analysis.get("recommended_followups") or [])
    labels = ", ".join(inferred_labels or [])
    if labels:
        recommended_followups.append(
            f"Review the read-through against {ticker}'s current labels: {labels}."
        )

    return {
        **base_analysis,
        "analysis_text": f"{base_analysis.get('analysis_text', '').strip()} {projection_note}".strip(),
        "scenario_summary": (
            f"{base_analysis.get('scenario_summary', '').strip()} {projection_note}"
        ).strip(),
        "confidence": confidence,
        "key_implications": key_implications[:3],
        "recommended_followups": recommended_followups[:3],
    }


def _position_weight(position: dict) -> float:
    current_price = float(
        position.get("current_price")
        or position.get("latest_price")
        or position.get("purchase_price")
        or 0
    )
    shares = float(position.get("shares") or 0)
    return max(current_price * shares, 0.0)


def _compute_portfolio_grade(position_payloads: list[dict]) -> tuple[float, str]:
    if not position_payloads:
        return 0.0, "C"

    total_weight = sum(_position_weight(position) for position in position_payloads)
    if total_weight <= 0:
        average = sum(
            float(position.get("total_score") or 0) for position in position_payloads
        ) / len(position_payloads)
        return round(average, 1), score_to_grade(average)

    weighted_total = 0.0
    for position in position_payloads:
        weighted_total += float(position.get("total_score") or 0) * (
            _position_weight(position) / total_weight
        )

    return round(weighted_total, 1), score_to_grade(weighted_total)


def _parse_article_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _article_priority(article: dict, ticker: str) -> tuple[float, float]:
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    ticker_token = ticker.lower()
    score = 0.0

    is_junk, _ = _is_junk_article(article)
    if is_junk:
        score -= 12

    if ticker_token in text:
        score += 5

    ticker_hints = {str(hint).lower() for hint in (article.get("ticker_hints") or [])}
    if ticker_token in ticker_hints:
        score += 4

    if article.get("source_type") == "company_news":
        score += 3
    elif article.get("source_type") == "rss":
        score += 1

    if article.get("scrape_status") == "google_wrapper":
        score -= 4

    if not str(article.get("body") or "").strip():
        score -= 2

    low_value_markers = (
        "stock price",
        "quote & chart",
        "price, quote & chart",
        "stock underperforms",
        "underperforms friday when compared to competitors",
    )
    if any(marker in text for marker in low_value_markers):
        score -= 8

    score += sum(2 for keyword in MAJOR_PRIORITY_KEYWORDS if keyword in text)
    published_at = _parse_article_timestamp(article.get("published_at"))
    age_hours = (datetime.now(timezone.utc) - published_at).total_seconds() / 3600.0
    if age_hours > 24 * 7:
        score -= 6
    if age_hours > 24 * 14:
        score -= 10
    recency_bonus = max(0.0, 72.0 - age_hours)
    return score, recency_bonus


def _top_articles_for_position(articles: list[dict], ticker: str) -> list[dict]:
    filtered_articles = []
    for article in articles:
        is_junk, _ = _is_junk_article(article)
        if not is_junk:
            filtered_articles.append(article)

    if not filtered_articles:
        return []

    ranked = sorted(
        filtered_articles,
        key=lambda article: _article_priority(article, ticker),
        reverse=True,
    )
    return ranked[:MAX_ARTICLES_PER_POSITION]


def _parse_time_window_hours(hours: int) -> str:
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    return threshold.isoformat()


def _parse_hhmm(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = str(value).split(":")
    if len(parts) < 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except (TypeError, ValueError):
        return None
    if hour not in range(24) or minute not in range(60):
        return None
    return hour, minute


def _quiet_hours_active(
    now_utc: datetime,
    *,
    enabled: bool,
    start: str | None,
    end: str | None,
) -> bool:
    if not enabled:
        return False

    parsed_start = _parse_hhmm(start)
    parsed_end = _parse_hhmm(end)
    if not parsed_start or not parsed_end:
        return False

    current_minutes = now_utc.astimezone(timezone.utc).hour * 60 + now_utc.astimezone(
        timezone.utc
    ).minute
    start_minutes = parsed_start[0] * 60 + parsed_start[1]
    end_minutes = parsed_end[0] * 60 + parsed_end[1]

    if start_minutes <= end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def _is_retryable_supabase_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            httpx.WriteError,
            httpx.WriteTimeout,
        ),
    ):
        return True
    return "Server disconnected" in str(exc)


def _execute_supabase_with_retry(
    operation,
    *,
    context: str,
    attempts: int = 3,
    base_delay: float = 1.0,
):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable_supabase_error(exc) or attempt >= attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Retrying Supabase operation for %s after transient error (attempt %s/%s): %s",
                context,
                attempt,
                attempts,
                exc,
            )
            time.sleep(delay)
    raise last_exc


def _update_analysis_run(supabase, analysis_run_id: str, **fields):
    _execute_supabase_with_retry(
        lambda: (
            supabase.table("analysis_runs")
            .update(fields)
            .eq("id", analysis_run_id)
            .execute()
        ),
        context=f"analysis_runs update {analysis_run_id}",
    )


def _set_analysis_stage(
    supabase,
    analysis_run_id: str,
    stage: str,
    message: str,
    **extra_fields,
):
    _update_analysis_run(
        supabase,
        analysis_run_id,
        current_stage=stage,
        current_stage_message=message[:300],
        **extra_fields,
    )
    record_stage(
        stage,
        {
            "analysis_run_id": analysis_run_id,
            "message": message[:300],
            **extra_fields,
        },
    )


def _job_id_for_user(user_id: str) -> str:
    return f"{JOB_PREFIX}{user_id}"


def _serialize_datetime(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _fmt_both_tz(value) -> dict | None:
    """Format a datetime as both ET and UTC ISO strings."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return {"et": value, "utc": value}
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return {
            "et": value.astimezone(ET).isoformat(),
            "utc": value.astimezone(timezone.utc).isoformat(),
        }
    return {"et": str(value), "utc": str(value)}


def _parse_digest_time(digest_time: str | None) -> tuple[str, int, int]:
    normalized = digest_time or DEFAULT_DIGEST_TIME
    try:
        parts = normalized.split(":")
        if len(parts) < 2:
            raise ValueError("Digest time must include hours and minutes")
        hour_str, minute_str = parts[0], parts[1]
        hour = int(hour_str)
        minute = int(minute_str)
        if hour not in range(24) or minute not in range(60):
            raise ValueError("Digest time must be a valid HH:MM value")
        return f"{hour:02d}:{minute:02d}", hour, minute
    except Exception:
        logger.warning(
            "Invalid digest time found, falling back to default",
            extra={"digest_time": digest_time},
        )
        return DEFAULT_DIGEST_TIME, 7, 0


def _load_scheduler_state(supabase, user_id: str) -> dict | None:
    result = (
        supabase.table(SCHEDULER_TABLE)
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _persist_scheduler_state(supabase, user_id: str, **fields) -> dict:
    existing = _load_scheduler_state(supabase, user_id)
    payload = {"user_id": user_id, **fields}
    if existing:
        (
            supabase.table(SCHEDULER_TABLE)
            .update(payload)
            .eq("user_id", user_id)
            .execute()
        )
        existing.update(payload)
        return existing

    created = supabase.table(SCHEDULER_TABLE).insert(payload).execute().data
    return created[0] if created else payload


def _mark_scheduler_inactive(
    supabase,
    user_id: str,
    *,
    digest_time: str | None = None,
    notifications_enabled: bool = False,
    last_run_status: str | None = None,
    last_error: str | None = None,
):
    return _persist_scheduler_state(
        supabase,
        user_id,
        job_id=_job_id_for_user(user_id),
        digest_time=digest_time or DEFAULT_DIGEST_TIME,
        notifications_enabled=notifications_enabled,
        active=False,
        next_run_at=None,
        last_scheduled_at=utcnow_iso(),
        last_run_status=last_run_status,
        last_error=last_error,
    )


def _load_analysis_cache(
    supabase,
    *,
    kind: str,
    cache_key: str,
    max_age_hours: int = 24,
    article: dict | None = None,
) -> dict | None:
    threshold = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    result = (
        supabase.table(CACHE_TABLE)
        .select("payload")
        .eq("kind", kind)
        .eq("cache_key", cache_key)
        .gte("updated_at", threshold.isoformat())
        .limit(1)
        .execute()
    )
    payload = result.data[0]["payload"] if result.data else None
    if not isinstance(payload, dict):
        return None

    why = str(payload.get("why_it_matters") or "").strip().lower()
    if why == "llm call failed":
        return None

    if kind == "relevance":
        if article is not None:
            is_junk, _ = _is_junk_article(article)
            if is_junk:
                return None
            if (
                str(article.get("source_type") or "") == "company_news"
                and str(article.get("body") or "").strip()
                and int(payload.get("cache_version") or 0) < 2
            ):
                return None
        event_type = str(payload.get("event_type") or "").strip().lower()
        affected = payload.get("affected_tickers") or []
        if payload.get("relevant") and not affected:
            return None
        if not event_type:
            return None

    return payload


def _store_analysis_cache(
    supabase,
    *,
    kind: str,
    cache_key: str,
    payload: dict,
):
    existing = (
        supabase.table(CACHE_TABLE)
        .select("cache_key")
        .eq("kind", kind)
        .eq("cache_key", cache_key)
        .limit(1)
        .execute()
        .data
    )
    row = {
        "kind": kind,
        "cache_key": cache_key,
        "payload": payload,
        "updated_at": utcnow_iso(),
    }
    if existing:
        (
            supabase.table(CACHE_TABLE)
            .update(row)
            .eq("kind", kind)
            .eq("cache_key", cache_key)
            .execute()
        )
    else:
        supabase.table(CACHE_TABLE).insert(row).execute()


def _should_enrich_company_article(article: dict) -> bool:
    if str(article.get("source_type") or "") != "company_news":
        return False

    evidence_quality = str(article.get("evidence_quality") or "").strip().lower()
    if evidence_quality == "full_body":
        return False

    body_text = str(article.get("body") or "").strip()
    if not body_text:
        return True

    return evidence_quality in {"title_only", "partial_body"}


async def _enrich_company_articles_with_cache(
    supabase,
    articles: list[dict],
) -> list[dict]:
    from ..services.article_scraper import enrich_articles_content
    if not articles:
        return []

    unique_articles: list[dict] = []
    seen_hashes: set[str] = set()
    for article in articles:
        event_hash = str(article.get("event_hash") or "").strip()
        if not event_hash or event_hash in seen_hashes:
            continue
        seen_hashes.add(event_hash)
        unique_articles.append(article)

    if not unique_articles:
        return []

    cache_keys = [
        str(article.get("event_hash") or "").strip() for article in unique_articles
    ]
    threshold = datetime.now(timezone.utc) - timedelta(
        hours=COMPANY_ARTICLE_ENRICHMENT_CACHE_TTL_HOURS
    )
    cached_rows = (
        supabase.table(CACHE_TABLE)
        .select("cache_key, payload")
        .eq("kind", COMPANY_ARTICLE_ENRICHMENT_CACHE_KIND)
        .in_("cache_key", cache_keys)
        .gte("updated_at", threshold.isoformat())
        .execute()
        .data
    )
    cached_by_hash = {
        str(row.get("cache_key") or "").strip(): row.get("payload")
        for row in cached_rows
        if isinstance(row.get("payload"), dict)
    }

    enriched_by_hash: dict[str, dict] = {}
    pending_articles: list[dict] = []
    for article in unique_articles:
        event_hash = str(article.get("event_hash") or "").strip()
        cached = cached_by_hash.get(event_hash)
        if cached:
            enriched_by_hash[event_hash] = cached
            continue
        pending_articles.append(article)

    if pending_articles:
        pending_started_at = time.monotonic()
        pending_enriched = await enrich_articles_content(pending_articles)
        print(
            f"[ARTICLE_ENRICH] Cache miss enriched {len(pending_enriched)}/{len(pending_articles)} "
            f"company articles in {time.monotonic() - pending_started_at:.1f}s"
        )
        for article in pending_enriched:
            event_hash = str(article.get("event_hash") or "").strip()
            if not event_hash:
                continue
            enriched_by_hash[event_hash] = article
            _store_analysis_cache(
                supabase,
                kind=COMPANY_ARTICLE_ENRICHMENT_CACHE_KIND,
                cache_key=event_hash,
                payload=article,
            )

    ordered: list[dict] = []
    cache_hits = 0
    cache_misses = 0
    for article in unique_articles:
        event_hash = str(article.get("event_hash") or "").strip()
        enriched = enriched_by_hash.get(event_hash)
        if enriched:
            ordered.append(enriched)
            if event_hash in cached_by_hash:
                cache_hits += 1
            else:
                cache_misses += 1
        else:
            ordered.append(article)

    print(
        f"[ARTICLE_ENRICH] Company cache hits={cache_hits} misses={cache_misses} total={len(unique_articles)}"
    )
    return ordered


def _sync_user_job(
    supabase,
    user_id: str,
    digest_time: str | None,
    notifications_enabled: bool,
) -> dict:
    normalized_time, hour, minute = _parse_digest_time(digest_time)
    job_id = _job_id_for_user(user_id)
    structural_job_id = f"{JOB_PREFIX}{user_id}_structural_refresh"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    if scheduler.get_job(structural_job_id):
        scheduler.remove_job(structural_job_id)

    scheduler.add_job(
        trigger_structural_refresh,
        CronTrigger(hour=6, minute=30, timezone=ET),
        id=structural_job_id,
        args=[user_id],
        misfire_grace_time=7200,
        replace_existing=True,
    )

    if not notifications_enabled:
        return _mark_scheduler_inactive(
            supabase,
            user_id,
            digest_time=normalized_time,
            notifications_enabled=False,
            last_run_status="disabled",
            last_error=None,
        )

    scheduler.add_job(
        trigger_scheduled_digest,
        CronTrigger(hour=hour, minute=minute, timezone=ET),
        id=job_id,
        args=[user_id],
        misfire_grace_time=3600,
        replace_existing=True,
    )

    job = scheduler.get_job(job_id)
    return _persist_scheduler_state(
        supabase,
        user_id,
        job_id=job_id,
        digest_time=normalized_time,
        notifications_enabled=True,
        active=True,
        next_run_at=_serialize_datetime(job.next_run_time if job else None),
        last_scheduled_at=utcnow_iso(),
    )


def _record_scheduled_run_start(supabase, user_id: str):
    state = _load_scheduler_state(supabase, user_id) or {}
    _persist_scheduler_state(
        supabase,
        user_id,
        job_id=_job_id_for_user(user_id),
        digest_time=state.get("digest_time", DEFAULT_DIGEST_TIME),
        notifications_enabled=state.get("notifications_enabled", True),
        active=state.get("active", True),
        next_run_at=state.get("next_run_at"),
        last_scheduled_at=state.get("last_scheduled_at"),
        last_run_at=utcnow_iso(),
        last_run_status="running",
        last_error=None,
    )


def _record_scheduled_run_result(
    supabase,
    user_id: str,
    *,
    status: str,
    error: str | None = None,
):
    state = _load_scheduler_state(supabase, user_id) or {}
    job = scheduler.get_job(_job_id_for_user(user_id))
    _persist_scheduler_state(
        supabase,
        user_id,
        job_id=_job_id_for_user(user_id),
        digest_time=state.get("digest_time", DEFAULT_DIGEST_TIME),
        notifications_enabled=state.get("notifications_enabled", True),
        active=state.get("active", True),
        next_run_at=_serialize_datetime(job.next_run_time if job else None),
        last_scheduled_at=state.get("last_scheduled_at", utcnow_iso()),
        last_run_at=state.get("last_run_at", utcnow_iso()),
        last_run_status=status,
        last_error=error[:500] if error else None,
    )


async def _maybe_create_alert(
    supabase,
    payload: dict,
    dedupe_event_hash: str | None = None,
    dedupe_hours: int = 24,
) -> bool:
    query = (
        supabase.table("alerts")
        .select("id")
        .eq("user_id", payload["user_id"])
        .eq("type", payload["type"])
        .gte("created_at", _parse_time_window_hours(dedupe_hours))
    )
    if dedupe_event_hash:
        query = query.eq("event_hash", dedupe_event_hash)

    existing = query.limit(1).execute().data
    if existing:
        return False

    supabase.table("alerts").insert(payload).execute()
    return True


def _upsert_position_analysis(
    supabase,
    *,
    analysis_run_id: str,
    position: dict,
    ticker: str,
    inferred_labels: list[str] | None = None,
    summary: str | None = None,
    long_report: str | None = None,
    methodology: str | None = None,
    top_risks: list[str] | None = None,
    watch_items: list[str] | None = None,
    top_news: list[str] | None = None,
    major_event_count: int | None = None,
    minor_event_count: int | None = None,
    status: str | None = None,
    progress_message: str | None = None,
    source_count: int | None = None,
):
    payload = {
        "analysis_run_id": analysis_run_id,
        "position_id": position["id"],
        "ticker": ticker,
        "updated_at": utcnow_iso(),
    }
    optional_fields = {
        "inferred_labels": inferred_labels,
        "summary": summary,
        "long_report": long_report,
        "methodology": methodology,
        "top_risks": top_risks,
        "watch_items": watch_items,
        "top_news": top_news,
        "major_event_count": major_event_count,
        "minor_event_count": minor_event_count,
        "status": status,
        "progress_message": progress_message,
        "source_count": source_count,
    }
    payload.update(
        {key: value for key, value in optional_fields.items() if value is not None}
    )

    existing = (
        supabase.table("position_analyses")
        .select("id")
        .eq("analysis_run_id", analysis_run_id)
        .eq("position_id", position["id"])
        .limit(1)
        .execute()
        .data
    )
    if existing:
        (
            supabase.table("position_analyses")
            .update(payload)
            .eq("id", existing[0]["id"])
            .execute()
        )
    else:
        supabase.table("position_analyses").insert(payload).execute()


def _store_relevant_news_items(
    supabase,
    *,
    user_id: str,
    analysis_run_id: str,
    relevant_articles: list[dict],
):
    for article in relevant_articles:
        affected_tickers = article.get("relevance", {}).get("affected_tickers", []) or [
            None
        ]
        for affected_ticker in affected_tickers:
            existing = (
                supabase.table("news_items")
                .select("id")
                .eq("analysis_run_id", analysis_run_id)
                .eq("event_hash", article.get("event_hash"))
                .eq("ticker", affected_ticker)
                .limit(1)
                .execute()
                .data
            )
            if existing:
                continue

            try:
                supabase.table("news_items").insert(
                    {
                        "user_id": user_id,
                        "ticker": affected_ticker,
                        "title": article.get("title", ""),
                        "source": article.get("source", ""),
                        "url": article.get("url", ""),
                        "significance": None,
                        "event_hash": article.get("event_hash"),
                        "published_at": article.get("published_at"),
                        "body": article.get("body", ""),
                        "affected_tickers": article.get("relevance", {}).get(
                            "affected_tickers", []
                        ),
                        "relevance": article.get("relevance", {}),
                        "analysis_run_id": analysis_run_id,
                    }
                ).execute()
            except Exception:
                continue

    from ..services.ticker_cache_service import sync_ticker_news_cache

    for ticker in sorted(
        {
            str(ticker or "").strip().upper()
            for article in relevant_articles
            for ticker in (
                article.get("relevance", {}).get("affected_tickers", [])
                or [article.get("ticker")]
            )
            if str(ticker or "").strip()
        }
    ):
        cache_articles = []
        for article in relevant_articles:
            affected_tickers = article.get("relevance", {}).get(
                "affected_tickers", []
            ) or [article.get("ticker")]
            normalized = {
                str(item or "").strip().upper()
                for item in affected_tickers
                if str(item or "").strip()
            }
            if ticker in normalized:
                cache_articles.append(article)
        sync_ticker_news_cache(supabase, ticker=ticker, news_rows=cache_articles)


async def _load_ticker_metadata_map(
    supabase,
    tickers: list[str],
) -> dict[str, dict]:
    normalized_tickers = sorted(
        {str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}
    )
    if not normalized_tickers:
        return {}

    result = (
        supabase.table("ticker_metadata")
        .select("*")
        .in_("ticker", normalized_tickers)
        .execute()
        .data
    )
    return {row["ticker"]: row for row in (result or []) if row.get("ticker")}


async def _build_shared_news_payload(
    tickers: list[str],
    ticker_metadata_map: dict[str, dict],
) -> dict:
    started_at = time.monotonic()
    timings: dict[str, float] = {}

    async def _time_fetch(name: str, awaitable):
        fetch_started_at = time.monotonic()
        result = await awaitable
        timings[name] = time.monotonic() - fetch_started_at
        return result

    from .finnhub_news import fetch_market_news
    from .macro_classifier import summarize_sector_overview
    from .rss_ingest import (
        fetch_cnbc_macro_rss,
        fetch_cnbc_sector_rss,
        fetch_google_company_rss,
        fetch_google_sector_rss,
    )

    sector_names = sorted(
        {
            str(metadata.get("sector", "")).strip()
            for metadata in ticker_metadata_map.values()
            if str(metadata.get("sector", "")).strip()
        }
    )

    macro_task = asyncio.create_task(
        _time_fetch("macro", fetch_cnbc_macro_rss(limit=12))
    )
    cnbc_sector_task = asyncio.create_task(
        _time_fetch(
            "cnbc_sector", fetch_cnbc_sector_rss(sector_names, limit_per_sector=10)
        )
    )
    google_sector_task = asyncio.create_task(
        _time_fetch(
            "google_sector", fetch_google_sector_rss(sector_names, limit_per_sector=6)
        )
    )
    company_task = asyncio.create_task(
        _time_fetch(
            "company",
            fetch_google_company_rss(tickers, ticker_metadata_map, limit_per_ticker=4),
        )
    )
    market_task = asyncio.create_task(_time_fetch("market", fetch_market_news()))

    macro_articles = await macro_task
    cnbc_sector_articles = await cnbc_sector_task
    google_sector_articles = await google_sector_task
    company_articles = await company_task
    market_articles = await market_task

    sector_articles = cnbc_sector_articles + google_sector_articles
    sector_articles_by_name: dict[str, list[dict]] = {}
    for article in sector_articles:
        sector_name = (
            str(article.get("sector_hint") or article.get("sector") or "")
            .strip()
            .lower()
        )
        if sector_name and sector_name not in {"unknown", "none", "null", "n/a"}:
            sector_articles_by_name.setdefault(sector_name, []).append(article)

    sector_context_started_at = time.monotonic()
    sector_context = await summarize_sector_overview(sector_articles_by_name)
    timings["sector_context"] = time.monotonic() - sector_context_started_at

    normalize_started_at = time.monotonic()
    raw_articles = []
    raw_articles.extend(normalize_news_batch(company_articles, "company_news"))
    raw_articles.extend(normalize_news_batch(macro_articles, "cnbc_macro_rss"))
    raw_articles.extend(normalize_news_batch(sector_articles, "cnbc_sector_rss"))
    raw_articles.extend(normalize_news_batch(market_articles, "market_news"))
    timings["normalize"] = time.monotonic() - normalize_started_at

    dedupe_started_at = time.monotonic()
    normalized_articles = _dedupe_articles(raw_articles)
    timings["dedupe"] = time.monotonic() - dedupe_started_at

    elapsed = time.monotonic() - started_at
    print(
        f"[SHARED_NEWS] Built shared news payload for {len(tickers)} tickers in {elapsed:.1f}s: "
        f"macro={len(macro_articles)} sector={len(sector_articles)} company={len(company_articles)} market={len(market_articles)} "
        f"timings=macro:{timings.get('macro', 0.0):.1f}s cnbc_sector:{timings.get('cnbc_sector', 0.0):.1f}s "
        f"google_sector:{timings.get('google_sector', 0.0):.1f}s company:{timings.get('company', 0.0):.1f}s "
        f"market:{timings.get('market', 0.0):.1f}s sector_context:{timings.get('sector_context', 0.0):.1f}s "
        f"normalize:{timings.get('normalize', 0.0):.1f}s dedupe:{timings.get('dedupe', 0.0):.1f}s"
    )

    return {
        "macro_articles": macro_articles,
        "cnbc_sector_articles": cnbc_sector_articles,
        "google_sector_articles": google_sector_articles,
        "sector_articles": sector_articles,
        "company_articles": company_articles,
        "market_articles": market_articles,
        "sector_names": sector_names,
        "sector_context": sector_context,
        "raw_articles": raw_articles,
        "normalized_articles": normalized_articles,
    }


async def _refresh_position_prices_from_finnhub(positions: list[dict]) -> None:
    from ..services.finnhub_prices import fetch_current_price_from_finnhub
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    semaphore = asyncio.Semaphore(6)

    def _persist_price(position_id: str, ticker: str, price: float) -> None:
        supabase.table("positions").update({"current_price": price}).eq(
            "id", position_id
        ).execute()
        supabase.table("prices").insert({"ticker": ticker, "price": price}).execute()

    async def _refresh_one(position: dict) -> None:
        ticker = str(position.get("ticker") or "").strip().upper()
        position_id = str(position.get("id") or "").strip()
        if not ticker or not position_id:
            return

        async with semaphore:
            try:
                price = await asyncio.wait_for(
                    asyncio.to_thread(fetch_current_price_from_finnhub, ticker),
                    timeout=6,
                )
            except Exception as exc:
                print(f"Error fetching Finnhub price for {ticker}: {exc}")
                return

            if not price:
                return

            try:
                await asyncio.to_thread(_persist_price, position_id, ticker, price)
                print(f"Updated {ticker} price to ${price}")
            except Exception as exc:
                print(f"Error saving Finnhub price for {ticker}: {exc}")

    await asyncio.gather(*(_refresh_one(position) for position in positions))


def _upsert_draft_position_snapshot(
    supabase,
    *,
    analysis_run_id: str,
    position: dict,
    ticker: str,
    top_headlines: list[str],
    progress_message: str,
    source_count: int,
    inferred_labels: list[str] | None = None,
):
    _upsert_position_analysis(
        supabase,
        analysis_run_id=analysis_run_id,
        position=position,
        ticker=ticker,
        inferred_labels=inferred_labels or [position.get("archetype", "watchlist")],
        summary=(
            f"Quick brief ready for {ticker}. Found {source_count} relevant headlines and started the deeper analysis."
            if source_count > 0
            else f"No strong news signal surfaced for {ticker} yet."
        ),
        long_report=(
            "Clavynx already found the initial signal for this holding and is still generating the in-depth report. "
            "You can review the first matched headlines now and come back shortly for the final scoring."
            if source_count > 0
            else "Clavynx is still scanning for stronger holding-specific signal. Price data is available while the deeper run continues."
        ),
        methodology=(
            "Initial draft based on the earliest matched headlines while the deeper event analysis is still running."
            if source_count > 0
            else "Initial placeholder generated before a strong set of matched headlines was available."
        ),
        top_risks=[] if source_count > 0 else ["No strong article matches yet."],
        watch_items=(
            ["Deep analysis is still running on the current news set."]
            if source_count > 0
            else ["Watch for new company-specific headlines."]
        ),
        top_news=top_headlines,
        major_event_count=0,
        minor_event_count=0,
        status="draft",
        progress_message=progress_message,
        source_count=source_count,
    )


def _build_position_analysis_payload(
    analysis_run_id: str,
    position: dict,
    ticker: str,
    inferred_labels: list[str],
    position_report: dict,
    related_articles: list[dict],
    event_analyses: list[dict],
) -> dict:
    return {
        "analysis_run_id": analysis_run_id,
        "position_id": position["id"],
        "ticker": ticker,
        "inferred_labels": inferred_labels,
        "summary": position_report["summary"],
        "long_report": position_report["long_report"],
        "methodology": position_report["methodology"],
        "top_risks": position_report["top_risks"],
        "watch_items": position_report["watch_items"],
        "top_news": [article.get("title", "") for article in related_articles[:5]],
        "major_event_count": len(
            [event for event in event_analyses if event["significance"] == "major"]
        ),
        "minor_event_count": len(
            [event for event in event_analyses if event["significance"] == "minor"]
        ),
        "status": "ready",
        "progress_message": "Full position analysis is ready.",
        "source_count": len(related_articles),
        "updated_at": utcnow_iso(),
    }


def _load_completed_position_payloads(
    supabase, user_id: str, analysis_run_id: str
) -> list[dict]:
    positions = _execute_supabase_with_retry(
        lambda: (
            supabase.table("positions")
            .select("*")
            .eq("user_id", user_id)
            .execute()
            .data
        ),
        context=f"positions load for partial run {analysis_run_id}",
    )
    payloads = []
    for position in positions:
        score_rows = _execute_supabase_with_retry(
            lambda: (
                supabase.table("risk_scores")
                .select("*")
                .eq("analysis_run_id", analysis_run_id)
                .eq("position_id", position["id"])
                .limit(1)
                .execute()
                .data
            ),
            context=(
                f"risk_scores load for partial run {analysis_run_id} "
                f"position {position['id']}"
            ),
        )
        analysis_rows = _execute_supabase_with_retry(
            lambda: (
                supabase.table("position_analyses")
                .select("*")
                .eq("analysis_run_id", analysis_run_id)
                .eq("position_id", position["id"])
                .limit(1)
                .execute()
                .data
            ),
            context=(
                f"position_analyses load for partial run {analysis_run_id} "
                f"position {position['id']}"
            ),
        )
        if not score_rows or not analysis_rows:
            continue

        history_rows = _execute_supabase_with_retry(
            lambda: (
                supabase.table("risk_scores")
                .select("analysis_run_id, grade")
                .eq("position_id", position["id"])
                .order("calculated_at", desc=True)
                .limit(2)
                .execute()
                .data
            ),
            context=f"risk_scores history load for position {position['id']}",
        )
        previous_grade = None
        if len(history_rows) >= 2:
            previous_grade = history_rows[1].get("grade")

        score = score_rows[0]
        analysis = analysis_rows[0]
        payloads.append(
            {
                **position,
                **score,
                "previous_grade": previous_grade,
                "summary": analysis.get("summary"),
                "long_report": analysis.get("long_report"),
                "top_risks": analysis.get("top_risks") or [],
                "top_news": analysis.get("top_news") or [],
                "inferred_labels": analysis.get("inferred_labels") or [],
                "methodology": analysis.get("methodology"),
                "mirofish_used": score.get("mirofish_used", False),
                "thesis_verifier": [],
            }
        )
    return payloads


async def _finalize_partial_run(
    supabase,
    user_id: str,
    analysis_run_id: str,
    error_message: str,
) -> bool:
    from .portfolio_compiler import compile_portfolio_digest
    position_payloads = _load_completed_position_payloads(
        supabase, user_id, analysis_run_id
    )
    if not position_payloads:
        return False

    events_processed = (
        _execute_supabase_with_retry(
            lambda: (
                supabase.table("event_analyses")
                .select("id", count="exact")
                .eq("analysis_run_id", analysis_run_id)
                .execute()
                .count
            ),
            context=f"event_analyses count for partial run {analysis_run_id}",
        )
        or 0
    )
    portfolio_score, overall_grade = _compute_portfolio_grade(position_payloads)
    digest = await compile_portfolio_digest(position_payloads, overall_grade)

    existing_digest = _execute_supabase_with_retry(
        lambda: (
            supabase.table("digests")
            .select("id")
            .eq("analysis_run_id", analysis_run_id)
            .limit(1)
            .execute()
            .data
        ),
        context=f"digest lookup for partial run {analysis_run_id}",
    )
    if not existing_digest:
        _execute_supabase_with_retry(
            lambda: (
                supabase.table("digests")
                .insert(
                    {
                        "user_id": user_id,
                        "analysis_run_id": analysis_run_id,
                        "content": digest["content"],
                        "grade_summary": {
                            payload["ticker"]: payload["grade"]
                            for payload in position_payloads
                        },
                        "overall_grade": overall_grade,
                        "overall_score": portfolio_score,
                        "structured_sections": digest["sections"],
                        "summary": digest["overall_summary"],
                    }
                )
                .execute()
            ),
            context=f"digest insert for partial run {analysis_run_id}",
        )

    _set_analysis_stage(
        supabase,
        analysis_run_id,
        "partial",
        f"Completed {len(position_payloads)} positions before timing out.",
        status="partial",
        completed_at=utcnow_iso(),
        error_message=error_message[:500],
        overall_portfolio_grade=overall_grade,
        positions_processed=len(position_payloads),
        events_processed=events_processed,
    )
    return True


async def create_analysis_run(
    user_id: str,
    triggered_by: str,
    target_position_id: str | None = None,
    target_tickers: list[str] | None = None,
) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    target_ticker = None
    if target_position_id:
        position = (
            supabase.table("positions")
            .select("ticker")
            .eq("id", target_position_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        )
        if position:
            target_ticker = position[0].get("ticker")
    normalized_target_tickers = None
    if target_tickers:
        normalized_target_tickers = list(
            dict.fromkeys(
                [
                    str(ticker).strip().upper()
                    for ticker in target_tickers
                    if str(ticker).strip()
                ]
            )
        )
    run_result = (
        supabase.table("analysis_runs")
        .insert(
            {
                "user_id": user_id,
                "status": "queued",
                "triggered_by": triggered_by,
                "current_stage": "queued",
                "current_stage_message": "Queued for analysis.",
                "target_position_id": target_position_id,
                "target_ticker": target_ticker,
                "target_tickers": normalized_target_tickers,
            }
        )
        .execute()
    )
    return run_result.data[0]


def _fail_stale_runs(supabase):
    stale_cutoff = _parse_time_window_hours(STALE_RUN_HOURS)
    stale_runs = (
        supabase.table("analysis_runs")
        .select("id")
        .in_("status", ["queued", "running"])
        .neq("triggered_by", SP500_BACKFILL_TRIGGER)
        .lt("started_at", stale_cutoff)
        .execute()
        .data
    )
    for run in stale_runs:
        supabase.table("analysis_runs").update(
            {
                "status": "failed",
                "completed_at": utcnow_iso(),
                "error_message": "Marked failed by cleanup after exceeding stale-run threshold.",
            }
        ).eq("id", run["id"]).execute()


def _fail_orphaned_runs(supabase):
    orphaned_runs = (
        supabase.table("analysis_runs")
        .select("id, started_at")
        .in_("status", ["queued", "running"])
        .lt("started_at", PROCESS_STARTED_AT.isoformat())
        .execute()
        .data
    )
    for run in orphaned_runs:
        _update_analysis_run(
            supabase,
            run["id"],
            status="failed",
            current_stage="failed",
            current_stage_message="Analysis stopped when the server restarted.",
            completed_at=utcnow_iso(),
            error_message="Analysis was interrupted by a server restart. Please run it again.",
        )


async def _execute_with_timeout(
    user_id: str,
    analysis_run_id: str,
    triggered_by: str,
    target_position_id: str | None = None,
    skip_metadata_refresh: bool = False,
    target_tickers: list[str] | None = None,
    artifact_label: str | None = None,
    shared_news_payload: dict | None = None,
):
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    try:
        return await asyncio.wait_for(
            execute_analysis_run(
                user_id,
                analysis_run_id,
                triggered_by,
                target_position_id,
                skip_metadata_refresh=skip_metadata_refresh,
                target_tickers=target_tickers,
                artifact_label=artifact_label,
                shared_news_payload=shared_news_payload,
            ),
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        run = _execute_supabase_with_retry(
            lambda: (
                supabase.table("analysis_runs")
                .select("current_stage, current_stage_message")
                .eq("id", analysis_run_id)
                .limit(1)
                .execute()
                .data
            ),
            context=f"analysis_runs timeout lookup {analysis_run_id}",
        )
        current_stage = run[0].get("current_stage") if run else None
        current_message = run[0].get("current_stage_message") if run else None
        timeout_message = "Analysis ran longer than expected and timed out."
        if current_message:
            timeout_message += f" Last stage: {current_message}"
        finalized_partial = await _finalize_partial_run(
            supabase,
            user_id,
            analysis_run_id,
            timeout_message,
        )
        if not finalized_partial:
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "failed",
                current_message or "Analysis timed out.",
                status="failed",
                completed_at=utcnow_iso(),
                error_message=timeout_message[:500],
            )
        if triggered_by == "scheduled":
            _record_scheduled_run_result(
                supabase,
                user_id,
                status="partial" if finalized_partial else "failed",
                error=timeout_message,
            )
        active_runs.pop(analysis_run_id, None)
        return None


def _run_analysis_in_thread(
    user_id: str,
    analysis_run_id: str,
    triggered_by: str,
    target_position_id: str | None = None,
    skip_metadata_refresh: bool = False,
    target_tickers: list[str] | None = None,
    artifact_label: str | None = None,
    shared_news_payload: dict | None = None,
):
    asyncio.run(
        _execute_with_timeout(
            user_id,
            analysis_run_id,
            triggered_by,
            target_position_id,
            skip_metadata_refresh=skip_metadata_refresh,
            target_tickers=target_tickers,
            artifact_label=artifact_label,
            shared_news_payload=shared_news_payload,
        )
    )


def _log_analysis_task_result(analysis_run_id: str, task: asyncio.Task) -> None:
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        logger.warning(
            "Background analysis task was cancelled for run %s", analysis_run_id
        )
        return

    if exc is not None:
        logger.error(
            "Background analysis task failed for run %s",
            analysis_run_id,
            exc_info=(type(exc), exc, exc.__traceback__),
        )


async def execute_analysis_run(
    user_id: str,
    analysis_run_id: str,
    triggered_by: str,
    target_position_id: str | None = None,
    skip_metadata_refresh: bool = False,
    target_tickers: list[str] | None = None,
    artifact_label: str | None = None,
    shared_news_payload: dict | None = None,
):
    from ..services.article_scraper import enrich_articles_content
    from .portfolio_risk import calculate_portfolio_risk_score
    from .portfolio_compiler import compile_portfolio_digest
    from .risk_scorer import score_position_structural
    from ..services.ticker_cache_service import get_latest_risk_snapshot_history_map
    from ..services.supabase import get_supabase
    from .finnhub_news import fetch_market_news
    from .notifier import (
        notify_digest,
        notify_grade_change,
        notify_major_event,
        notify_portfolio_grade_change,
    )
    from .rss_ingest import (
        fetch_cnbc_macro_rss,
        fetch_cnbc_sector_rss,
        fetch_google_company_rss,
        fetch_google_sector_rss,
    )

    supabase = get_supabase()
    artifact_enabled = bool(artifact_label)
    coverage_gate: dict = {}

    if triggered_by == "scheduled":
        _record_scheduled_run_start(supabase, user_id)

    if artifact_enabled:
        begin_artifact_session(
            analysis_run_id,
            {
                "label": artifact_label,
                "user_id": user_id,
                "triggered_by": triggered_by,
                "target_position_id": target_position_id,
                "target_tickers": target_tickers or [],
            },
        )

    _set_analysis_stage(
        supabase,
        analysis_run_id,
        "starting",
        "Starting analysis run.",
        status="running",
        started_at=utcnow_iso(),
    )

    try:
        positions_query = supabase.table("positions").select("*").eq("user_id", user_id)
        normalized_target_tickers = sorted(
            {
                str(ticker).strip().upper()
                for ticker in (target_tickers or [])
                if str(ticker).strip()
            }
        )
        is_internal_sp500_batch_run = (
            user_id == SYSTEM_SP500_USER_ID
            and triggered_by == "scheduled"
            and not target_position_id
            and bool(normalized_target_tickers)
        )
        if target_position_id:
            positions_query = positions_query.eq("id", target_position_id)
        elif normalized_target_tickers:
            positions_query = positions_query.in_("ticker", normalized_target_tickers)
        positions = positions_query.execute().data
        if artifact_enabled:
            write_named_json(
                "positions.json",
                {
                    "positions": positions,
                    "target_position_id": target_position_id,
                    "target_tickers": normalized_target_tickers,
                },
            )
        if not positions:
            empty_message = (
                "Target position not found."
                if target_position_id
                else "No positions to analyze."
            )
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "completed",
                empty_message,
                status="completed",
                completed_at=utcnow_iso(),
                positions_processed=0,
                events_processed=0,
            )
            if triggered_by == "scheduled":
                _record_scheduled_run_result(supabase, user_id, status="completed")
            return

        tickers = [p["ticker"] for p in positions]

        if not skip_metadata_refresh:
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "refreshing_metadata",
                f"Refreshing ticker metadata for {len(tickers)} holdings.",
            )
            for ticker in tickers:
                await asyncio.to_thread(upsert_ticker_metadata, supabase, ticker)

        ticker_metadata_map = {}
        for ticker in tickers:
            meta_result = (
                supabase.table("ticker_metadata")
                .select("*")
                .eq("ticker", ticker.upper())
                .limit(1)
                .execute()
            )
            if meta_result.data:
                ticker_metadata_map[ticker] = meta_result.data[0]
        if artifact_enabled:
            write_named_json("ticker_metadata.json", ticker_metadata_map)

        sector_names = sorted(
            {
                str(metadata.get("sector", "")).strip()
                for metadata in ticker_metadata_map.values()
                if str(metadata.get("sector", "")).strip()
            }
        )

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "fetching_news" if not shared_news_payload else "loading_shared_news",
            (
                f"Loading shared news cache for {len(tickers)} holdings."
                if shared_news_payload
                else (
                    f"Fetching CNBC macro and sector news for {tickers[0]}."
                    if len(tickers) == 1
                    else f"Fetching CNBC macro and sector news for {len(tickers)} holdings."
                )
            ),
        )
        if shared_news_payload:
            macro_articles = list(shared_news_payload.get("macro_articles") or [])
            cnbc_sector_articles = list(
                shared_news_payload.get("cnbc_sector_articles") or []
            )
            google_sector_articles = list(
                shared_news_payload.get("google_sector_articles") or []
            )
            sector_articles = list(shared_news_payload.get("sector_articles") or [])
            market_articles = list(shared_news_payload.get("market_articles") or [])
            sector_context = shared_news_payload.get("sector_context") or {}
            shared_company_articles = list(
                shared_news_payload.get("company_articles") or []
            )
            ticker_set = {ticker.upper() for ticker in tickers}
            company_articles = [
                article
                for article in shared_company_articles
                if str(article.get("ticker") or "").strip().upper() in ticker_set
            ]
            print(
                f"[SHARED_NEWS] Reusing shared payload for {len(tickers)} tickers: "
                f"company_scoped={len(company_articles)}/{len(shared_company_articles)} "
                f"macro={len(macro_articles)} sector={len(sector_articles)} market={len(market_articles)}"
            )
        else:
            macro_articles = await fetch_cnbc_macro_rss()
            cnbc_sector_articles = await fetch_cnbc_sector_rss(sector_names)
            google_sector_articles = await fetch_google_sector_rss(sector_names)
            sector_articles = cnbc_sector_articles + google_sector_articles
            company_articles = await fetch_google_company_rss(
                tickers, ticker_metadata_map
            )
            market_articles_task = asyncio.create_task(fetch_market_news())
            sector_articles_by_name: dict[str, list[dict]] = {}
            for article in sector_articles:
                sector_name = (
                    str(article.get("sector_hint") or article.get("sector") or "")
                    .strip()
                    .lower()
                )
                if sector_name and sector_name not in {
                    "unknown",
                    "none",
                    "null",
                    "n/a",
                }:
                    sector_articles_by_name.setdefault(sector_name, []).append(article)

            from .macro_classifier import summarize_sector_overview

            sector_context = await summarize_sector_overview(sector_articles_by_name)
            market_articles = await market_articles_task
        raw_articles = []
        raw_articles.extend(normalize_news_batch(company_articles, "company_news"))
        raw_articles.extend(normalize_news_batch(macro_articles, "cnbc_macro_rss"))
        raw_articles.extend(normalize_news_batch(sector_articles, "cnbc_sector_rss"))
        raw_articles.extend(normalize_news_batch(market_articles, "market_news"))
        normalized_articles = _dedupe_articles(raw_articles)

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "classifying_relevance",
            (
                f"Filtering {len(normalized_articles)} news items for {tickers[0]}."
                if len(tickers) == 1
                else f"Filtering {len(normalized_articles)} news items for portfolio relevance."
            ),
        )
        from .relevance import classify_relevance_batch

        normalized_copy = normalized_articles[:]

        relevance_cache: dict[str, dict] = {}
        articles_to_classify: list[dict] = []
        for article in normalized_copy:
            event_hash = article.get("event_hash", "")
            if event_hash:
                cached = _load_analysis_cache(
                    supabase,
                    kind="relevance",
                    cache_key=event_hash,
                    max_age_hours=72,
                    article=article,
                )
                if cached:
                    relevance_cache[event_hash] = cached

        for article in normalized_copy:
            event_hash = article.get("event_hash", "")
            if event_hash and event_hash in relevance_cache:
                relevance_cache[event_hash]["article"] = article
            else:
                articles_to_classify.append(article)

        uncached_count = len(articles_to_classify)
        stage_msg = (
            f"Filtering {uncached_count} new articles."
            if relevance_cache
            else f"Filtering {uncached_count} articles."
        )
        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "classifying_relevance",
            stage_msg,
        )

        all_batch_results: list[dict] = []
        if articles_to_classify:
            article_count = len(articles_to_classify)
            relevance_batch_size = (
                5 if article_count < 200 else (20 if article_count < 2000 else 30)
            )
            fresh_results = await classify_relevance_batch(
                articles_to_classify, positions, batch_size=relevance_batch_size
            )
            for r in fresh_results:
                article = r.get("article") or {}
                event_hash = article.get("event_hash", "")
                if event_hash:
                    cache_payload = {k: v for k, v in r.items() if k != "article"}
                    cache_payload["cache_version"] = 2
                    _store_analysis_cache(
                        supabase,
                        kind="relevance",
                        cache_key=event_hash,
                        payload=cache_payload,
                    )
                all_batch_results.append(r)
        if artifact_enabled:
            write_named_json(
                "stages/relevance_outputs.json",
                {
                    "cached_count": len(relevance_cache),
                    "uncached_count": len(articles_to_classify),
                    "results": all_batch_results,
                },
            )

        for event_hash, cached in relevance_cache.items():
            article = cached.pop("article", {})
            all_batch_results.append(
                {
                    "article_index": next(
                        (
                            idx
                            for idx, a in enumerate(normalized_copy)
                            if a.get("event_hash") == event_hash
                        ),
                        -1,
                    ),
                    "relevant": cached.get("relevant", False),
                    "affected_tickers": cached.get("affected_tickers", []),
                    "event_type": cached.get("event_type") or "irrelevant",
                    "why_it_matters": cached.get("why_it_matters") or "",
                    "article": article,
                }
            )

        all_batch_results.sort(key=lambda r: r["article_index"])

        relevant_articles = []
        articles_by_ticker: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
        positions_by_ticker = {position["ticker"]: position for position in positions}

        held_tickers = {ticker.upper() for ticker in tickers}

        for result in all_batch_results:
            article = result.get("article") or normalized_copy[result["article_index"]]
            is_junk, junk_reason = _is_junk_article(article)
            if is_junk:
                article["relevance"] = {
                    "relevant": False,
                    "affected_tickers": [],
                    "event_type": "irrelevant",
                    "why_it_matters": junk_reason,
                }
                continue
            affected_tickers = [
                str(t).upper()
                for t in result.get("affected_tickers", [])
                if str(t).strip()
            ]

            # Company-news fetches are already scoped by ticker. Preserve that signal
            # when the relevance classifier under-matches or returns an empty ticker list.
            ticker_hints = [
                str(t).upper()
                for t in article.get("ticker_hints", [])
                if str(t).strip().upper() in held_tickers
            ]
            article_evidence_quality = str(
                article.get("evidence_quality") or "title_only"
            )
            can_force_promote = article_evidence_quality in {
                "headline_summary",
                "partial_body",
                "full_body",
            }
            if (
                article.get("source_type") == "company_news"
                and ticker_hints
                and can_force_promote
            ):
                if not affected_tickers:
                    affected_tickers = ticker_hints
                if not result.get("relevant"):
                    result["relevant"] = True
                    result["event_type"] = "company_specific"
                    if not result.get("why_it_matters"):
                        result["why_it_matters"] = (
                            f"Direct company coverage matched to {', '.join(ticker_hints)}."
                        )

            if result.get("relevant") and affected_tickers:
                article["relevance"] = {
                    "relevant": True,
                    "affected_tickers": affected_tickers,
                    "event_type": result.get("event_type", "company_specific"),
                    "why_it_matters": result.get("why_it_matters", ""),
                    "evidence_quality": article_evidence_quality,
                }
                relevant_articles.append(article)
                for ticker in affected_tickers:
                    if ticker in articles_by_ticker:
                        articles_by_ticker[ticker].append(article)
                        articles_by_ticker[ticker] = _top_articles_for_position(
                            articles_by_ticker[ticker],
                            ticker,
                        )
                        if articles_by_ticker[ticker]:
                            top_headlines = [
                                matched_article.get("title", "")
                                for matched_article in articles_by_ticker[ticker][
                                    :MAX_ARTICLES_PER_POSITION
                                ]
                                if matched_article.get("title")
                            ]
                            _upsert_draft_position_snapshot(
                                supabase,
                                analysis_run_id=analysis_run_id,
                                position=positions_by_ticker[ticker],
                                ticker=ticker,
                                top_headlines=top_headlines,
                                progress_message=(
                                    f"Quick brief ready. Matched {len(articles_by_ticker[ticker])} headlines so far and queued the deep analysis."
                                ),
                                source_count=len(articles_by_ticker[ticker]),
                            )
            else:
                article["relevance"] = {
                    "relevant": False,
                    "affected_tickers": [],
                    "event_type": "irrelevant",
                    "why_it_matters": "",
                    "evidence_quality": article_evidence_quality,
                }

        for ticker in tickers:
            articles_by_ticker[ticker] = _top_articles_for_position(
                articles_by_ticker.get(ticker, []),
                ticker,
            )

        selected_articles_by_hash: dict[str, dict] = {}
        for articles in articles_by_ticker.values():
            for article in articles:
                event_hash = str(article.get("event_hash") or "").strip()
                if event_hash:
                    selected_articles_by_hash[event_hash] = article

        articles_to_enrich = [
            article
            for article in selected_articles_by_hash.values()
            if _should_enrich_company_article(article)
        ]
        enriched_articles_by_hash: dict[str, dict] = {}
        if articles_to_enrich:
            enriched_articles = await _enrich_company_articles_with_cache(
                supabase,
                articles_to_enrich,
            )
            enriched_articles_by_hash = {
                str(article.get("event_hash") or "").strip(): article
                for article in enriched_articles
                if str(article.get("event_hash") or "").strip()
            }

        if enriched_articles_by_hash:
            for ticker in tickers:
                articles_by_ticker[ticker] = [
                    _refresh_company_article_evidence_quality(
                        enriched_articles_by_hash.get(
                            article.get("event_hash"), article
                        )
                    )
                    for article in articles_by_ticker.get(ticker, [])
                ]
            relevant_articles = [
                _refresh_company_article_evidence_quality(
                    enriched_articles_by_hash.get(article.get("event_hash"), article)
                )
                for article in relevant_articles
            ]

        if relevant_articles:
            _store_relevant_news_items(
                supabase,
                user_id=user_id,
                analysis_run_id=analysis_run_id,
                relevant_articles=relevant_articles,
            )

        company_articles_enriched = list(enriched_articles_by_hash.values())
        coverage_report = _company_article_resolution_report(
            company_articles, company_articles_enriched
        )
        coverage_gate = {
            "limited_evidence": not coverage_report.get("coverage_ok", False),
            "coverage_ok": coverage_report.get("coverage_ok", False),
            "coverage_rate": coverage_report.get("coverage_rate", 0.0),
            "threshold": 0.35,
            "resolved_with_body": coverage_report.get("resolved_with_body", 0),
            "input_count": coverage_report.get("input_count", 0),
        }
        if artifact_enabled:
            write_named_json(
                "stages/relevant_articles_by_ticker.json",
                {
                    "relevant_articles": relevant_articles,
                    "articles_by_ticker": articles_by_ticker,
                    "scraped_event_hashes": sorted(enriched_articles_by_hash.keys()),
                },
            )
            write_named_json(
                "feeds/raw_feeds.json",
                {
                    "macro_articles": macro_articles,
                    "cnbc_sector_articles": cnbc_sector_articles,
                    "google_sector_articles": google_sector_articles,
                    "sector_articles": sector_articles,
                    "company_articles": company_articles,
                    "company_articles_enriched": company_articles_enriched,
                    "market_articles": market_articles,
                    "sector_names": sector_names,
                },
            )
            write_named_json(
                "feeds/company_article_resolution_report.json",
                coverage_report,
            )
            write_named_json("feeds/coverage_gate.json", coverage_gate)
            record_stage("coverage_gate", coverage_gate)
            write_named_json(
                "feeds/normalized_articles.json",
                {
                    "sector_context": sector_context,
                    "raw_articles": raw_articles,
                    "normalized_articles": normalized_articles,
                    "company_articles_enriched": company_articles_enriched,
                },
            )

        prefs = (
            supabase.table("user_preferences")
            .select(
                "apns_token, notifications_enabled, summary_length, weekday_only, quiet_hours_enabled, quiet_hours_start, quiet_hours_end"
            )
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        )
        notifications_enabled = bool(prefs and prefs[0].get("notifications_enabled"))
        apns_token = prefs[0].get("apns_token") if prefs else None
        summary_length = (
            (prefs[0].get("summary_length") or "standard") if prefs else "standard"
        )
        weekday_only = bool(prefs and prefs[0].get("weekday_only"))
        quiet_hours_enabled = bool(prefs and prefs[0].get("quiet_hours_enabled"))
        quiet_hours_start = prefs[0].get("quiet_hours_start") if prefs else None
        quiet_hours_end = prefs[0].get("quiet_hours_end") if prefs else None

        def _can_send_push_notifications() -> bool:
            return bool(
                notifications_enabled
                and apns_token
                and not _quiet_hours_active(
                    datetime.now(timezone.utc),
                    enabled=quiet_hours_enabled,
                    start=quiet_hours_start,
                    end=quiet_hours_end,
                )
            )

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "classifying_macro",
            "Classifying overnight macro developments.",
            positions_processed=0,
            events_processed=0,
        )
        macro_context = {
            "overnight_macro": {
                "headlines": [],
                "themes": [],
                "brief": "Macro analysis unavailable.",
            },
            "position_impacts": [],
            "what_matters_today": [],
        }
        if macro_articles:
            from .macro_classifier import classify_overnight_macro

            macro_context = await classify_overnight_macro(
                macro_articles[-20:], positions
            )
        if artifact_enabled:
            write_named_json("stages/macro_context.json", macro_context)

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "classifying_positions",
            "Batch classifying all position archetypes.",
            positions_processed=0,
            events_processed=0,
        )
        from .position_classifier import classify_position_batch

        all_events_by_ticker = {
            ticker: articles_by_ticker.get(ticker, []) for ticker in tickers
        }
        position_labels = await classify_position_batch(positions, all_events_by_ticker)
        if artifact_enabled:
            write_named_json("stages/position_labels.json", position_labels)
        inferred_map: dict[str, list[str]] = {}
        for p in positions:
            ticker = p["ticker"]
            inferred_map[ticker] = position_labels.get(
                ticker, [p.get("archetype", "core")]
            )

        position_payloads = []
        total_event_count = 0
        significance_cache: dict[str, dict] = {}
        all_events_by_ticker_for_analysis: dict[str, list[dict]] = {
            ticker: articles_by_ticker.get(ticker, []) for ticker in tickers
        }

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "classifying_significance",
            f"Batch classifying significance for all {sum(len(v) for v in all_events_by_ticker_for_analysis.values())} relevant articles.",
            positions_processed=0,
            events_processed=0,
        )

        from .classifier import classify_significance_batch

        all_articles_to_classify = []
        article_to_ticker_idx: dict[int, tuple[str, int]] = {}

        for ticker in tickers:
            articles = all_events_by_ticker_for_analysis.get(ticker, [])
            for article_idx, article in enumerate(articles):
                event_hash = article.get("event_hash", "")
                cached = _load_analysis_cache(
                    supabase,
                    kind="significance",
                    cache_key=event_hash,
                    max_age_hours=72,
                )
                if cached:
                    significance_cache[event_hash] = cached
                else:
                    all_articles_to_classify.append(article)
                    article_to_ticker_idx[len(all_articles_to_classify) - 1] = (
                        ticker,
                        article_idx,
                    )

        if all_articles_to_classify:
            sig_batch_results = await classify_significance_batch(
                all_articles_to_classify
            )
            for idx, significance in enumerate(sig_batch_results):
                article = all_articles_to_classify[idx]
                event_hash = article.get("event_hash", "")
                significance_cache[event_hash] = significance
                _store_analysis_cache(
                    supabase,
                    kind="significance",
                    cache_key=event_hash,
                    payload=significance,
                )
        if artifact_enabled:
            write_named_json(
                "stages/significance_outputs.json",
                {
                    "articles_classified": all_articles_to_classify,
                    "significance_cache": significance_cache,
                },
            )

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "analyzing_events",
            f"Analyzing events for {len(positions)} positions.",
            positions_processed=0,
            events_processed=0,
        )

        previous_grades_by_ticker = {}
        previous_total_scores_by_ticker = {}
        for position in positions:
            previous_scores = (
                supabase.table("risk_scores")
                .select("grade, total_score")
                .eq("position_id", position["id"])
                .order("calculated_at", desc=True)
                .limit(1)
                .execute()
                .data
            )
            previous_grades_by_ticker[position["ticker"]] = (
                previous_scores[0]["grade"] if previous_scores else None
            )
            previous_total_scores_by_ticker[position["ticker"]] = (
                previous_scores[0].get("total_score") if previous_scores else None
            )

        async def _process_position(
            position: dict, position_index: int
        ) -> tuple[int, dict, list[dict]]:
            ticker = position["ticker"]
            related_articles = all_events_by_ticker_for_analysis.get(ticker, [])
            inferred_labels = inferred_map.get(ticker, ["core"])
            analyzable_related_articles = [
                article
                for article in related_articles
                if str(article.get("evidence_quality") or "title_only")
                in {"headline_summary", "partial_body", "full_body"}
            ]

            top_headlines = [
                article.get("title", "")
                for article in related_articles[:3]
                if article.get("title")
            ]

            if related_articles:
                _upsert_draft_position_snapshot(
                    supabase,
                    analysis_run_id=analysis_run_id,
                    position=position,
                    ticker=ticker,
                    top_headlines=top_headlines,
                    progress_message=f"Quick brief ready. Deep analysis is still running on {len(related_articles)} headlines.",
                    source_count=len(related_articles),
                    inferred_labels=inferred_labels,
                )
            else:
                _upsert_draft_position_snapshot(
                    supabase,
                    analysis_run_id=analysis_run_id,
                    position=position,
                    ticker=ticker,
                    top_headlines=[],
                    progress_message="No strong headline matches yet. The broader run is still in progress.",
                    source_count=0,
                    inferred_labels=inferred_labels,
                )

            minor_articles = []
            major_articles = []
            significance_by_hash = {}

            for article in analyzable_related_articles:
                event_hash = article.get("event_hash", "")
                significance = significance_cache.get(event_hash)
                if significance:
                    significance_by_hash[event_hash] = significance
                    if significance["significance"] == "major":
                        major_articles.append(article)
                    else:
                        minor_articles.append(article)

            minor_uncached_articles = []
            minor_article_analysis_results: list[dict] = []

            for article in minor_articles:
                event_hash = article.get("event_hash", "")
                cached = _load_analysis_cache(
                    supabase,
                    kind="minor_event_analysis_shared",
                    cache_key=event_hash,
                    max_age_hours=72,
                )
                if cached:
                    minor_article_analysis_results.append(
                        {"article": article, "analysis": cached, "cached": True}
                    )
                else:
                    minor_uncached_articles.append(article)
                    minor_article_analysis_results.append(
                        {"article": article, "analysis": None, "cached": False}
                    )

            if minor_uncached_articles:
                from .agentic_scan import analyze_minor_events_shared_batch

                batch_results = await analyze_minor_events_shared_batch(
                    minor_uncached_articles
                )
                result_idx = 0
                for item in minor_article_analysis_results:
                    if not item["cached"]:
                        item["analysis"] = batch_results[result_idx]
                        result_idx += 1
                        event_hash = item["article"].get("event_hash", "")
                        _store_analysis_cache(
                            supabase,
                            kind="minor_event_analysis_shared",
                            cache_key=event_hash,
                            payload=item["analysis"],
                        )

            mirofish_used = False
            major_uncached_articles = []
            major_article_analysis_results: list[dict] = []

            for article in major_articles:
                event_hash = article.get("event_hash", "")
                cached = _load_analysis_cache(
                    supabase,
                    kind="major_event_analysis_shared",
                    cache_key=event_hash,
                    max_age_hours=120,
                )
                if cached:
                    major_article_analysis_results.append(
                        {"article": article, "analysis": cached, "cached": True}
                    )
                else:
                    major_uncached_articles.append(article)
                    major_article_analysis_results.append(
                        {"article": article, "analysis": None, "cached": False}
                    )

            if major_uncached_articles:
                from .major_event_analyzer import analyze_major_events_shared_batch

                batch_results = await analyze_major_events_shared_batch(
                    major_uncached_articles
                )
                result_idx = 0
                for item in major_article_analysis_results:
                    if not item["cached"]:
                        item["analysis"] = batch_results[result_idx]
                        result_idx += 1
                        event_hash = item["article"].get("event_hash", "")
                        _store_analysis_cache(
                            supabase,
                            kind="major_event_analysis_shared",
                            cache_key=event_hash,
                            payload=item["analysis"],
                        )

            event_analyses = []
            for item in minor_article_analysis_results:
                article = item["article"]
                result = _project_shared_event_analysis(
                    item["analysis"] or {}, article, position, inferred_labels
                )
                event_hash = article.get("event_hash", "")
                significance = significance_by_hash.get(event_hash, {})
                event_record = {
                    "analysis_run_id": analysis_run_id,
                    "position_id": position["id"],
                    "event_hash": event_hash,
                    "external_event_id": article.get("external_id"),
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "source": article.get("source", ""),
                    "source_url": article.get("url", ""),
                    "published_at": article.get("published_at"),
                    "event_type": significance.get("event_type", "other"),
                    "significance": significance.get("significance", "minor"),
                    "classification": significance,
                    "classification_evidence": {
                        "relevance": article.get("relevance", {}),
                        "significance": significance,
                    },
                    "analysis_source": "minimax",
                    "long_analysis": result.get("analysis_text", "") if result else "",
                    "confidence": result.get("confidence", 0.5) if result else 0.5,
                    "impact_horizon": result.get("impact_horizon", "near_term")
                    if result
                    else "near_term",
                    "risk_direction": result.get("risk_direction", "neutral")
                    if result
                    else "neutral",
                    "scenario_summary": result.get("scenario_summary", "")
                    if result
                    else "",
                    "key_implications": result.get("key_implications", [])
                    if result
                    else [],
                    "recommended_followups": result.get("recommended_followups", [])
                    if result
                    else [],
                }
                event_analyses.append(event_record)
                supabase.table("event_analyses").insert(event_record).execute()

            for item in major_article_analysis_results:
                article = item["article"]
                result = _project_shared_event_analysis(
                    item["analysis"] or {}, article, position, inferred_labels
                )
                event_hash = article.get("event_hash", "")
                significance = significance_by_hash.get(event_hash, {})
                analysis_source = (
                    result.get("provider", "minimax") if result else "minimax"
                )
                mirofish_used = False
                event_record = {
                    "analysis_run_id": analysis_run_id,
                    "position_id": position["id"],
                    "event_hash": event_hash,
                    "external_event_id": article.get("external_id"),
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "source": article.get("source", ""),
                    "source_url": article.get("url", ""),
                    "published_at": article.get("published_at"),
                    "event_type": significance.get("event_type", "other"),
                    "significance": significance.get("significance", "major"),
                    "classification": significance,
                    "classification_evidence": {
                        "relevance": article.get("relevance", {}),
                        "significance": significance,
                    },
                    "analysis_source": analysis_source,
                    "long_analysis": result.get("analysis_text", "") if result else "",
                    "confidence": result.get("confidence", 0.5) if result else 0.5,
                    "impact_horizon": result.get("impact_horizon", "near_term")
                    if result
                    else "near_term",
                    "risk_direction": result.get("risk_direction", "neutral")
                    if result
                    else "neutral",
                    "scenario_summary": result.get("scenario_summary", "")
                    if result
                    else "",
                    "key_implications": result.get("key_implications", [])
                    if result
                    else [],
                    "recommended_followups": result.get("recommended_followups", [])
                    if result
                    else [],
                }
                event_analyses.append(event_record)
                supabase.table("event_analyses").insert(event_record).execute()

                created = await _maybe_create_alert(
                    supabase,
                    {
                        "user_id": user_id,
                        "position_ticker": ticker,
                        "type": "major_event",
                        "message": f"Major event detected for {ticker}: {article.get('title', '')}",
                        "event_hash": event_hash,
                        "analysis_run_id": analysis_run_id,
                        "change_reason": article.get("summary")
                        or article.get("title", "Major event detected."),
                        "change_details": {
                            "event_type": significance.get("event_type", "other"),
                            "significance": significance.get("significance", "major"),
                            "title": article.get("title", ""),
                            "source": article.get("source", ""),
                        },
                    },
                    dedupe_event_hash=event_hash,
                )
                if created and _can_send_push_notifications():
                    await notify_major_event(
                        user_id, apns_token, ticker, article.get("title", "")
                    )
            _upsert_position_analysis(
                supabase,
                analysis_run_id=analysis_run_id,
                position=position,
                ticker=ticker,
                inferred_labels=inferred_labels,
                summary=f"Quick brief ready for {ticker}. Processed {len(event_analyses)} events.",
                long_report="Event analysis complete. Generating position report.",
                methodology="Batch event analysis with significance classification.",
                top_news=top_headlines,
                major_event_count=len(
                    [e for e in event_analyses if e.get("significance") == "major"]
                ),
                minor_event_count=len(
                    [e for e in event_analyses if e.get("significance") == "minor"]
                ),
                status="draft",
                progress_message=f"Processed {len(event_analyses)} events for {ticker}.",
                source_count=len(related_articles),
            )

            ticker_meta_result = (
                supabase.table("ticker_metadata")
                .select("*")
                .eq("ticker", ticker.upper())
                .limit(1)
                .execute()
            )
            ticker_metadata = (
                ticker_meta_result.data[0] if ticker_meta_result.data else None
            )

            from .position_report_builder import build_position_report

            position_report = await build_position_report(
                {
                    **position,
                    "sector": (ticker_metadata or {}).get("sector"),
                    "analysis_mode": (
                        "sp500_backfill"
                        if user_id == SYSTEM_SP500_USER_ID
                        else "default"
                    ),
                },
                inferred_labels,
                event_analyses,
                macro_context=macro_context,
            )

            macro_impact = next(
                (
                    impact
                    for impact in macro_context.get("position_impacts", [])
                    if str(impact.get("ticker") or "").strip().upper() == ticker.upper()
                ),
                None,
            )

            mirofish_used = mirofish_used or any(
                e.get("analysis_source") == "mirofish" for e in event_analyses
            )

            position_payload = {
                **position,
                "analysis_mode": (
                    "sp500_backfill" if user_id == SYSTEM_SP500_USER_ID else "default"
                ),
                "previous_grade": previous_grades_by_ticker.get(ticker),
                "previous_total_score": previous_total_scores_by_ticker.get(ticker),
                "summary": position_report["summary"],
                "long_report": position_report["long_report"],
                "top_risks": position_report["top_risks"],
                "watch_items": position_report["watch_items"],
                "top_news": top_headlines,
                "inferred_labels": inferred_labels,
                "methodology": position_report["methodology"],
                "mirofish_used": mirofish_used,
                "thesis_verifier": position_report.get("thesis_verifier", []),
                "event_analyses": event_analyses,
                "ticker_metadata": ticker_metadata or {},
                "macro_impact": macro_impact or {},
                "current_price": (ticker_metadata or {}).get("price")
                or position.get("current_price")
                or position.get("purchase_price"),
            }
            if artifact_enabled:
                record_position_artifact(
                    ticker,
                    "analysis",
                    {
                        "position": position,
                        "inferred_labels": inferred_labels,
                        "related_articles": related_articles,
                        "event_analyses": event_analyses,
                        "position_report": position_report,
                        "position_payload": position_payload,
                    },
                )
            return position_index, position_payload, event_analyses

        position_concurrency = max(1, min(4, len(positions)))
        position_semaphore = asyncio.Semaphore(position_concurrency)

        async def _run_position(
            position: dict, position_index: int
        ) -> tuple[int, dict, list[dict]]:
            async with position_semaphore:
                return await _process_position(position, position_index)

        position_results = await asyncio.gather(
            *(
                _run_position(position, index)
                for index, position in enumerate(positions)
            )
        )
        position_results.sort(key=lambda item: item[0])
        position_payloads = [payload for _, payload, _ in position_results]
        total_event_count = sum(len(events) for _, _, events in position_results)

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "building_position_reports",
            f"Building all position reports in batch.",
            positions_processed=len(positions),
            events_processed=total_event_count,
        )

        if not position_payloads:
            for ticker in tickers:
                _upsert_draft_position_snapshot(
                    supabase,
                    analysis_run_id=analysis_run_id,
                    position=positions_by_ticker[ticker],
                    ticker=ticker,
                    top_headlines=[],
                    progress_message="No relevant events found for this position.",
                    source_count=0,
                    inferred_labels=inferred_map.get(ticker, ["core"]),
                )

        if position_payloads:
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "scoring_position",
                f"Batch scoring all {len(position_payloads)} positions.",
                positions_processed=len(position_payloads),
                events_processed=total_event_count,
            )
            from .risk_scorer import (
                has_suspicious_neutral_scores,
                score_position,
                score_positions_batch,
            )

            batch_risk_scores = await score_positions_batch(position_payloads)
            for i, scores in enumerate(batch_risk_scores):
                if i < len(position_payloads):
                    position_payloads[i].update(scores)
            if artifact_enabled:
                write_named_json("stages/batch_risk_scores.json", batch_risk_scores)

            suspicious_score_count = 0
            for i, position in enumerate(positions):
                if i >= len(position_payloads):
                    continue
                ai_scores = position_payloads[i]
                if not has_suspicious_neutral_scores(ai_scores):
                    continue
                suspicious_score_count += 1
                _set_analysis_stage(
                    supabase,
                    analysis_run_id,
                    "scoring_position",
                    f"Re-scoring {position['ticker']} because the batch result looked neutral or incomplete.",
                    positions_processed=i,
                    events_processed=total_event_count,
                )
                rescored = await score_position(
                    position,
                    position_payloads[i],
                    inferred_labels=position_payloads[i].get("inferred_labels", []),
                    mirofish_used=position_payloads[i].get("mirofish_used", False),
                )
                if not has_suspicious_neutral_scores(rescored):
                    position_payloads[i].update(rescored)

            if suspicious_score_count:
                logger.warning(
                    "Re-scored %s position(s) after suspicious neutral batch scoring.",
                    suspicious_score_count,
                )

            for i, position in enumerate(positions):
                ticker = position["ticker"]
                related_articles = articles_by_ticker.get(ticker, [])
                event_analyses_result = (
                    supabase.table("event_analyses")
                    .select("significance, risk_direction, confidence, published_at")
                    .eq("position_id", position["id"])
                    .eq("analysis_run_id", analysis_run_id)
                    .execute()
                )
                event_analyses = event_analyses_result.data or []

                ticker_meta_result = (
                    supabase.table("ticker_metadata")
                    .select("*")
                    .eq("ticker", ticker.upper())
                    .limit(1)
                    .execute()
                )
                ticker_metadata = (
                    ticker_meta_result.data[0] if ticker_meta_result.data else None
                )

                previous_score_result = (
                    supabase.table("risk_scores")
                    .select("safety_score")
                    .eq("position_id", position["id"])
                    .order("calculated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                previous_safety = (
                    previous_score_result.data[0].get("safety_score")
                    if previous_score_result.data
                    else None
                )

                events_for_structural = [
                    {
                        "significance": ea.get("significance", "minor"),
                        "risk_direction": ea.get("risk_direction", "neutral"),
                        "confidence": ea.get("confidence", 0.5),
                        "event_age_days": (
                            (
                                datetime.now(timezone.utc)
                                - isoparse(ea["published_at"])
                            ).days
                            if ea.get("published_at")
                            else 0
                        ),
                    }
                    for ea in event_analyses
                ]

                structural_scores = score_position_structural(
                    position=position,
                    ticker_metadata=ticker_metadata,
                    regime_state="neutral",
                    recent_events=events_for_structural,
                    previous_safety_score=previous_safety,
                )

                ai_scores = position_payloads[i] if i < len(position_payloads) else {}
                total_score = (
                    ai_scores.get("total_score")
                    or structural_scores.get("safety_score")
                    or 50
                )
                grade = ai_scores.get("grade") or structural_scores.get("grade") or "C"

                risk_payload = {
                    "position_id": position["id"],
                    "analysis_run_id": analysis_run_id,
                    "news_sentiment": ai_scores.get("news_sentiment"),
                    "macro_exposure": ai_scores.get("macro_exposure"),
                    "position_sizing": ai_scores.get("position_sizing"),
                    "volatility_trend": ai_scores.get("volatility_trend"),
                    "total_score": round(total_score, 1),
                    "safety_score": structural_scores.get("safety_score"),
                    "confidence": structural_scores.get("confidence"),
                    "structural_base_score": structural_scores.get(
                        "structural_base_score"
                    ),
                    "macro_adjustment": structural_scores.get("macro_adjustment"),
                    "event_adjustment": structural_scores.get("event_adjustment"),
                    "factor_breakdown": {
                        **(
                            structural_scores.get("factor_breakdown")
                            if isinstance(
                                structural_scores.get("factor_breakdown"), dict
                            )
                            else {}
                        ),
                        "ai_dimensions": {
                            "news_sentiment": ai_scores.get("news_sentiment"),
                            "macro_exposure": ai_scores.get("macro_exposure"),
                            "position_sizing": ai_scores.get("position_sizing"),
                            "volatility_trend": ai_scores.get("volatility_trend"),
                        },
                    },
                    "grade": grade,
                    "reasoning": ai_scores.get("reasoning"),
                    "grade_reason": ai_scores.get("grade_reason"),
                    "evidence_summary": ai_scores.get("evidence_summary"),
                    "dimension_rationale": ai_scores.get("dimension_rationale"),
                    "mirofish_used": ai_scores.get(
                        "mirofish_used", structural_scores.get("mirofish_used", False)
                    ),
                }
                if artifact_enabled:
                    record_position_artifact(
                        ticker,
                        "risk_payload",
                        {
                            "structural_scores": structural_scores,
                            "ai_scores": ai_scores,
                            "risk_payload": risk_payload,
                        },
                    )
                supabase.table("risk_scores").insert(risk_payload).execute()

                _upsert_position_analysis(
                    supabase,
                    analysis_run_id=analysis_run_id,
                    position=position,
                    ticker=ticker,
                    inferred_labels=position_payloads[i].get("inferred_labels", [])
                    if i < len(position_payloads)
                    else [],
                    summary=position_payloads[i].get("summary", "")
                    if i < len(position_payloads)
                    else "",
                    long_report=position_payloads[i].get("long_report", "")
                    if i < len(position_payloads)
                    else "",
                    methodology=position_payloads[i].get("methodology", "")
                    if i < len(position_payloads)
                    else "",
                    top_risks=position_payloads[i].get("top_risks", [])
                    if i < len(position_payloads)
                    else [],
                    watch_items=position_payloads[i].get("watch_items", [])
                    if i < len(position_payloads)
                    else [],
                    top_news=position_payloads[i].get("top_news", [])
                    if i < len(position_payloads)
                    else [],
                    major_event_count=len(
                        [e for e in event_analyses if e.get("significance") == "major"]
                    ),
                    minor_event_count=len(
                        [e for e in event_analyses if e.get("significance") == "minor"]
                    ),
                    status="ready",
                    progress_message="Full position analysis is ready.",
                    source_count=len(related_articles),
                )

                previous_grade = (
                    position_payloads[i].get("previous_grade")
                    if i < len(position_payloads)
                    else None
                )
                if previous_grade and grade and previous_grade != grade:
                    top_risks = (
                        position_payloads[i].get("top_risks", [])
                        if i < len(position_payloads)
                        else []
                    )
                    watch_items = (
                        position_payloads[i].get("watch_items", [])
                        if i < len(position_payloads)
                        else []
                    )
                    change_reason = (
                        "; ".join(
                            str(item)
                            for item in (watch_items[:2] or top_risks[:2])
                            if str(item).strip()
                        )
                        or position_payloads[i].get("summary", "")
                        or f"Latest analysis changed the risk read for {ticker}."
                    )
                    alert_payload = {
                        "user_id": user_id,
                        "position_ticker": ticker,
                        "type": "grade_change",
                        "previous_grade": previous_grade,
                        "new_grade": grade,
                        "message": f"{ticker} grade changed from {previous_grade} to {grade}",
                        "analysis_run_id": analysis_run_id,
                        "change_reason": change_reason,
                        "change_details": {
                            "previous_grade": previous_grade,
                            "new_grade": grade,
                            "watch_items": ", ".join(
                                str(item) for item in watch_items[:3]
                            ),
                            "top_risks": ", ".join(str(item) for item in top_risks[:3]),
                            "summary": position_payloads[i].get("summary", "")
                            if i < len(position_payloads)
                            else "",
                        },
                    }
                    supabase.table("alerts").insert(alert_payload).execute()
                    if _can_send_push_notifications():
                        await notify_grade_change(
                            user_id,
                            apns_token,
                            ticker,
                            previous_grade,
                            grade,
                        )

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "refreshing_prices",
            (
                f"Refreshing price history for {tickers[0]}."
                if len(tickers) == 1
                else "Refreshing price snapshots for analyzed holdings."
            ),
            positions_processed=len(position_payloads),
            events_processed=total_event_count,
        )
        await _refresh_position_prices_from_finnhub(positions)

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "computing_portfolio_risk",
            "Computing portfolio risk metrics.",
            positions_processed=len(position_payloads),
            events_processed=total_event_count,
        )

        sector_map = {}
        for ticker, metadata in ticker_metadata_map.items():
            sector_map[ticker] = metadata.get("sector", "unknown")

        portfolio_risk = calculate_portfolio_risk_score(
            positions=positions,
            sector_map=sector_map,
            ticker_metadata=ticker_metadata_map,
            ticker_correlation_matrix=None,
            regime_state="neutral",
        )

        today = datetime.utcnow().date()
        existing_snapshot = (
            supabase.table("portfolio_risk_snapshots")
            .select("id")
            .eq("user_id", user_id)
            .eq("as_of_date", today.isoformat())
            .limit(1)
            .execute()
            .data
        )
        snapshot_payload = {
            "user_id": user_id,
            "as_of_date": today.isoformat(),
            "portfolio_allocation_risk_score": portfolio_risk.get(
                "portfolio_allocation_risk_score"
            ),
            "confidence": portfolio_risk.get("confidence"),
            "concentration_risk": portfolio_risk.get("concentration_risk"),
            "cluster_risk": portfolio_risk.get("cluster_risk"),
            "correlation_risk": portfolio_risk.get("correlation_risk"),
            "liquidity_mismatch": portfolio_risk.get("liquidity_mismatch"),
            "macro_stack_risk": portfolio_risk.get("macro_stack_risk"),
            "factor_breakdown": portfolio_risk.get("factor_breakdown"),
            "top_risk_drivers": portfolio_risk.get("top_risk_drivers"),
            "danger_clusters": portfolio_risk.get("danger_clusters"),
        }
        if existing_snapshot:
            supabase.table("portfolio_risk_snapshots").update(snapshot_payload).eq(
                "id", existing_snapshot[0]["id"]
            ).execute()
        else:
            supabase.table("portfolio_risk_snapshots").insert(
                snapshot_payload
            ).execute()

        digest_alert_created = False
        overall_grade = None
        if not target_position_id and not is_internal_sp500_batch_run:
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "building_digest",
                "Building your morning digest.",
                positions_processed=len(position_payloads),
                events_processed=total_event_count,
            )
            snapshot_history_map = get_latest_risk_snapshot_history_map(
                supabase,
                [p["ticker"] for p in position_payloads],
                per_ticker=2,
            )
            if user_id != SYSTEM_SP500_USER_ID:
                for payload in position_payloads:
                    ticker = payload.get("ticker")
                    if not ticker:
                        continue
                    snapshots = snapshot_history_map.get(ticker, [])
                    latest_snapshot = snapshots[0] if snapshots else None
                    previous_snapshot = snapshots[1] if len(snapshots) > 1 else None
                    if latest_snapshot:
                        payload["grade"] = latest_snapshot.get("grade") or payload.get(
                            "grade"
                        )
                        payload["safety_score"] = latest_snapshot.get(
                            "safety_score"
                        ) or payload.get("safety_score")
                        payload["total_score"] = latest_snapshot.get(
                            "safety_score"
                        ) or payload.get("total_score")
                        payload["confidence"] = latest_snapshot.get(
                            "confidence"
                        ) or payload.get("confidence")
                        payload["structural_base_score"] = latest_snapshot.get(
                            "structural_base_score"
                        ) or payload.get("structural_base_score")
                        payload["summary"] = (
                            latest_snapshot.get("news_summary")
                            or latest_snapshot.get("reasoning")
                            or payload.get("summary")
                        )
                        payload["previous_grade"] = (
                            previous_snapshot.get("grade")
                            if previous_snapshot
                            else payload.get("previous_grade")
                        )
            portfolio_score, overall_grade = _compute_portfolio_grade(position_payloads)
            digest = await compile_portfolio_digest(
                position_payloads,
                overall_grade,
                portfolio_risk,
                macro_context=macro_context,
                sector_context=sector_context,
                summary_length=summary_length,
            )
            previous_digest = (
                supabase.table("digests")
                .select("overall_grade")
                .eq("user_id", user_id)
                .order("generated_at", desc=True)
                .limit(1)
                .execute()
                .data
            )
            previous_portfolio_grade = (
                previous_digest[0].get("overall_grade") if previous_digest else None
            )

            digest_payload = {
                "user_id": user_id,
                "analysis_run_id": analysis_run_id,
                "content": digest["content"],
                "grade_summary": {p["ticker"]: p["grade"] for p in position_payloads},
                "overall_grade": overall_grade,
                "overall_score": portfolio_score,
                "structured_sections": digest["sections"],
                "summary": digest["overall_summary"],
            }
            supabase.table("digests").insert(digest_payload).execute()

            if previous_portfolio_grade and previous_portfolio_grade != overall_grade:
                created = await _maybe_create_alert(
                    supabase,
                    {
                        "user_id": user_id,
                        "type": "portfolio_grade_change",
                        "previous_grade": previous_portfolio_grade,
                        "new_grade": overall_grade,
                        "message": f"Overall portfolio grade changed from {previous_portfolio_grade} to {overall_grade}",
                        "analysis_run_id": analysis_run_id,
                        "change_reason": "Portfolio-wide score moved after the latest full analysis run.",
                        "change_details": {
                            "previous_grade": previous_portfolio_grade,
                            "new_grade": overall_grade,
                            "overall_score": f"{portfolio_score:.1f}",
                        },
                    },
                )
                if created and _can_send_push_notifications():
                    await notify_portfolio_grade_change(
                        user_id,
                        apns_token,
                        previous_portfolio_grade,
                        overall_grade,
                    )

            previous_scores_for_alerts = {}
            for p in positions:
                snapshots = snapshot_history_map.get(p["ticker"], [])
                if len(snapshots) >= 2:
                    previous_scores_for_alerts[p["id"]] = snapshots[1].get(
                        "safety_score"
                    )

            for p in positions:
                ticker = p["ticker"]
                position_id = p["id"]
                current_score = p.get("safety_score") or p.get("total_score")
                if not current_score:
                    continue
                previous_score = previous_scores_for_alerts.get(position_id)
                if previous_score is not None and current_score < previous_score - 10:
                    top_risks = p.get("top_risks", []) or []
                    watch_items = p.get("watch_items", []) or []
                    created = await _maybe_create_alert(
                        supabase,
                        {
                            "user_id": user_id,
                            "position_ticker": ticker,
                            "type": "safety_deterioration",
                            "previous_grade": score_to_grade(previous_score),
                            "new_grade": p.get("grade"),
                            "message": f"{ticker} safety score dropped from {previous_score:.1f} to {current_score:.1f}",
                            "analysis_run_id": analysis_run_id,
                            "change_reason": (
                                "; ".join(
                                    str(item)
                                    for item in (watch_items[:2] or top_risks[:2])
                                    if str(item).strip()
                                )
                                or f"Safety score fell by {previous_score - current_score:.1f} points."
                            ),
                            "change_details": {
                                "previous_score": f"{previous_score:.1f}",
                                "new_score": f"{current_score:.1f}",
                                "top_risks": ", ".join(
                                    str(item) for item in top_risks[:3]
                                ),
                                "watch_items": ", ".join(
                                    str(item) for item in watch_items[:3]
                                ),
                            },
                        },
                        dedupe_hours=12,
                    )

            if portfolio_risk:
                risk_score = portfolio_risk.get("portfolio_allocation_risk_score", 0)
                concentration = portfolio_risk.get("concentration_risk", 0)
                if concentration > 50:
                    top_drivers = portfolio_risk.get("top_risk_drivers", []) or []
                    created = await _maybe_create_alert(
                        supabase,
                        {
                            "user_id": user_id,
                            "type": "concentration_danger",
                            "message": f"Portfolio concentration risk elevated at {concentration}/100",
                            "analysis_run_id": analysis_run_id,
                            "change_reason": "Concentration risk is above the review threshold for the latest portfolio snapshot.",
                            "change_details": {
                                "concentration_risk": f"{concentration}",
                                "top_drivers": ", ".join(
                                    str(driver.get("type") or "driver")
                                    for driver in top_drivers[:3]
                                    if isinstance(driver, dict)
                                ),
                            },
                        },
                        dedupe_hours=24,
                    )
                danger_clusters = [
                    cluster
                    for cluster in (portfolio_risk.get("danger_clusters") or [])
                    if cluster
                ]
                if danger_clusters:
                    created = await _maybe_create_alert(
                        supabase,
                        {
                            "user_id": user_id,
                            "type": "cluster_risk",
                            "message": f"Portfolio has exposure to risky clusters: {', '.join(danger_clusters[:3])}",
                            "analysis_run_id": analysis_run_id,
                            "change_reason": "Multiple holdings now share the same risk cluster.",
                            "change_details": {
                                "danger_clusters": ", ".join(danger_clusters[:3]),
                            },
                        },
                        dedupe_hours=24,
                    )

            digest_alert_created = await _maybe_create_alert(
                supabase,
                {
                    "user_id": user_id,
                    "type": "digest_ready",
                    "message": "Your latest Clavynx digest is ready.",
                    "analysis_run_id": analysis_run_id,
                },
                dedupe_hours=4,
            )

            if _can_send_push_notifications():
                await notify_digest(user_id, apns_token, digest["content"])

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "completed",
            (
                f"{tickers[0]} analysis complete."
                if len(tickers) == 1
                else "Analysis complete."
            ),
            status="completed",
            completed_at=utcnow_iso(),
            overall_portfolio_grade=overall_grade,
            positions_processed=len(position_payloads),
            events_processed=total_event_count,
        )
        if target_position_id:
            supabase.table("positions").update({"analysis_started_at": None}).eq(
                "id", target_position_id
            ).execute()
        if target_position_id and _can_send_push_notifications():
            position_ticker = tickers[0] if tickers else None
            position_grade = (
                position_payloads[0].get("grade") if position_payloads else None
            )
            if position_ticker:
                from .notifier import notify_position_analysis_complete

                await notify_position_analysis_complete(
                    user_id,
                    apns_token,
                    ticker=position_ticker,
                    position_id=target_position_id,
                    grade=position_grade,
                )
        if triggered_by == "scheduled":
            _record_scheduled_run_result(supabase, user_id, status="completed")
        if artifact_enabled:
            write_named_json(
                "final_outputs.json",
                {
                    "position_payloads": position_payloads,
                    "portfolio_risk": portfolio_risk,
                    "overall_grade": overall_grade,
                    "digest_alert_created": digest_alert_created,
                    "coverage_gate": coverage_gate,
                },
            )
        return digest_alert_created
    except Exception as exc:
        if artifact_enabled:
            record_stage(
                "error",
                {
                    "analysis_run_id": analysis_run_id,
                    "error": str(exc),
                },
            )
        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "failed",
            "Analysis failed.",
            status="failed",
            completed_at=utcnow_iso(),
            error_message=str(exc)[:500],
        )
        if triggered_by == "scheduled":
            _record_scheduled_run_result(
                supabase, user_id, status="failed", error=str(exc)
            )
        if target_position_id:
            supabase.table("positions").update({"analysis_started_at": None}).eq(
                "id", target_position_id
            ).execute()
        raise
    finally:
        active_runs.pop(analysis_run_id, None)
        if artifact_enabled:
            end_artifact_session(
                {
                    "analysis_run_id": analysis_run_id,
                    "completed_at": utcnow_iso(),
                }
            )


async def enqueue_analysis_run(
    user_id: str,
    triggered_by: str = "manual",
    target_position_id: str | None = None,
    skip_metadata_refresh: bool = False,
    target_tickers: list[str] | None = None,
    artifact_label: str | None = None,
    allow_parallel_runs: bool = False,
    shared_news_payload: dict | None = None,
) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    _fail_stale_runs(supabase)

    existing = []
    if not allow_parallel_runs:
        existing = (
            supabase.table("analysis_runs")
            .select("id, status, started_at, target_position_id, triggered_by")
            .eq("user_id", user_id)
            .in_("status", ["queued", "running"])
            .order("started_at", desc=True)
            .execute()
            .data
        )
        existing = [
            run for run in existing if run.get("triggered_by") != SP500_BACKFILL_TRIGGER
        ]
    if existing:
        blocking_run = None
        if target_position_id:
            blocking_run = next(
                (
                    run
                    for run in existing
                    if run.get("target_position_id") is None
                    or run.get("target_position_id") == target_position_id
                ),
                None,
            )
        else:
            blocking_run = existing[0]

        if blocking_run and blocking_run["id"] not in active_runs:
            _update_analysis_run(
                supabase,
                blocking_run["id"],
                status="failed",
                current_stage="failed",
                current_stage_message="Previous analysis was interrupted.",
                completed_at=utcnow_iso(),
                error_message="Previous analysis was interrupted before completion. Please run it again.",
            )
        elif blocking_run:
            if triggered_by == "scheduled":
                _record_scheduled_run_result(
                    supabase,
                    user_id,
                    status="skipped",
                    error=f"Skipped because analysis run {blocking_run['id']} is already {blocking_run['status']}.",
                )
            return {
                "status": blocking_run["status"],
                "user_id": user_id,
                "analysis_run_id": blocking_run["id"],
                "positions_processed": 0,
                "events_processed": 0,
                "overall_grade": None,
            }

    run = await create_analysis_run(
        user_id,
        triggered_by,
        target_position_id,
        target_tickers=target_tickers,
    )
    task = asyncio.create_task(
        asyncio.to_thread(
            _run_analysis_in_thread,
            user_id,
            run["id"],
            triggered_by,
            target_position_id,
            skip_metadata_refresh,
            target_tickers,
            artifact_label,
            shared_news_payload,
        )
    )
    task.add_done_callback(
        lambda completed_task, run_id=run["id"]: _log_analysis_task_result(
            run_id, completed_task
        )
    )
    active_runs[run["id"]] = task
    return {
        "status": "queued",
        "user_id": user_id,
        "analysis_run_id": run["id"],
        "positions_processed": 0,
        "events_processed": 0,
        "overall_grade": None,
    }


async def trigger_user_digest(user_id: str):
    return await enqueue_analysis_run(user_id, "manual")


async def trigger_scheduled_digest(user_id: str):
    from datetime import datetime, timezone
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    prefs_row = (
        supabase.table("user_preferences")
        .select("weekday_only")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    weekday_only = bool(prefs_row and prefs_row[0].get("weekday_only"))
    if weekday_only and datetime.now(timezone.utc).weekday() >= 5:
        logger.info(
            f"Skipping scheduled digest for {user_id}: weekday_only=True and today is weekend"
        )
        return None

    return await enqueue_analysis_run(user_id, "scheduled")


def _create_sp500_backfill_run(
    supabase,
    *,
    requested_by_user_id: str,
    job_type: str,
    limit: int | None,
    batch_size: int,
) -> dict:
    payload = {
        "user_id": SYSTEM_SP500_USER_ID,
        "status": "queued",
        "triggered_by": SP500_BACKFILL_TRIGGER,
        "current_stage": "queued",
        "current_stage_message": (
            f"Queued S&P 500 {job_type} run"
            + (f" for limit {limit}" if limit else "")
            + f" with batch size {batch_size}."
        )[:300],
        "error_message": None,
    }
    result = supabase.table("analysis_runs").insert(payload).execute()
    return result.data[0]


def create_sp500_backfill_run(
    *,
    requested_by_user_id: str,
    job_type: str = "backfill",
    limit: int | None = None,
    batch_size: int = 10,
) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    return _create_sp500_backfill_run(
        supabase,
        requested_by_user_id=requested_by_user_id,
        job_type=job_type,
        limit=limit,
        batch_size=batch_size,
    )


async def _execute_sp500_backfill_run(
    analysis_run_id: str,
    *,
    requested_by_user_id: str,
    limit: int | None,
    job_type: str,
    batch_size: int,
    skip_structural: bool = False,
) -> None:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    logger.info(
        "SP500 backfill starting run_id=%s job_type=%s batch_size=%s skip_structural=%s limit=%s",
        analysis_run_id, job_type, batch_size, skip_structural, limit,
    )
    try:
        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "starting",
            "Starting S&P 500 backfill controller.",
            status="running",
            started_at=utcnow_iso(),
        )
        result = await run_sp500_full_ai_analysis_fast(
            limit=limit,
            job_type=job_type,
            batch_size=batch_size,
            backfill_run_id=analysis_run_id,
            skip_structural=skip_structural,
        )
        refreshed = int(result.get("refreshed") or 0)
        failed = result.get("failed") or []
        if result.get("status") == "ok":
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "completed",
                f"Completed S&P 500 {job_type} run. Synced {refreshed} tickers.",
                status="completed",
                completed_at=utcnow_iso(),
                error_message=None,
                positions_processed=refreshed,
            )
            return

        if result.get("status") == "partial":
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "completed",
                f"Completed S&P 500 {job_type} run with {len(failed)} failures. Synced {refreshed} tickers.",
                status="partial",
                completed_at=utcnow_iso(),
                error_message=(str(failed[:3])[:500] if failed else None),
                positions_processed=refreshed,
            )
            return

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "failed",
            f"S&P 500 {job_type} run failed.",
            status="failed",
            completed_at=utcnow_iso(),
            error_message=(str(failed[:3])[:500] if failed else "Backfill failed."),
            positions_processed=refreshed,
        )
    except Exception as exc:
        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "failed",
            "S&P 500 backfill controller failed.",
            status="failed",
            completed_at=utcnow_iso(),
            error_message=str(exc)[:500],
        )
        raise
    finally:
        active_sp500_backfills.pop(analysis_run_id, None)


def run_sp500_backfill_worker(
    analysis_run_id: str,
    *,
    requested_by_user_id: str,
    limit: int | None = None,
    job_type: str = "backfill",
    batch_size: int = 10,
    skip_structural: bool = False,
) -> None:
    asyncio.run(
        _execute_sp500_backfill_run(
            analysis_run_id,
            requested_by_user_id=requested_by_user_id,
            limit=limit,
            job_type=job_type,
            batch_size=batch_size,
            skip_structural=skip_structural,
        )
    )


async def enqueue_sp500_backfill_run(
    *,
    requested_by_user_id: str,
    limit: int | None = None,
    job_type: str = "backfill",
    batch_size: int = 10,
    skip_structural: bool = False,
) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    existing = (
        supabase.table("analysis_runs")
        .select("id, status, started_at")
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .eq("triggered_by", SP500_BACKFILL_TRIGGER)
        .in_("status", ["queued", "running"])
        .order("started_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        blocking_run = existing[0]
        if blocking_run["id"] not in active_sp500_backfills:
            _update_analysis_run(
                supabase,
                blocking_run["id"],
                status="failed",
                current_stage="failed",
                current_stage_message="Previous S&P 500 backfill was interrupted.",
                completed_at=utcnow_iso(),
                error_message="Previous S&P 500 backfill was interrupted before completion. Please run it again.",
            )
        else:
            return {
                "status": blocking_run["status"],
                "analysis_run_id": blocking_run["id"],
                "user_id": SYSTEM_SP500_USER_ID,
                "positions_processed": 0,
                "events_processed": 0,
                "overall_grade": None,
            }

    run = _create_sp500_backfill_run(
        supabase,
        requested_by_user_id=requested_by_user_id,
        job_type=job_type,
        limit=limit,
        batch_size=batch_size,
    )
    task = asyncio.create_task(
        _execute_sp500_backfill_run(
            run["id"],
            requested_by_user_id=requested_by_user_id,
            limit=limit,
            job_type=job_type,
            batch_size=batch_size,
            skip_structural=skip_structural,
        )
    )
    task.add_done_callback(
        lambda completed_task, run_id=run["id"]: _log_analysis_task_result(
            run_id, completed_task
        )
    )
    active_sp500_backfills[run["id"]] = task
    logger.info("SP500 backfill task created: run_id=%s task_id=%s", run["id"], task.get_name())
    print(f"[SP500] Backfill task created: run_id={run['id']} task_name={task.get_name()}")
    return {
        "status": "queued",
        "user_id": SYSTEM_SP500_USER_ID,
        "analysis_run_id": run["id"],
        "positions_processed": 0,
        "events_processed": 0,
        "overall_grade": None,
    }


async def trigger_structural_refresh(user_id: str):
    from ..services.supabase import get_supabase
    from ..services.ticker_metadata import upsert_ticker_metadata
    from .structural_scorer import calculate_structural_base_score

    supabase = get_supabase()

    positions = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("user_id", user_id)
        .execute()
        .data
    )

    today = datetime.utcnow().date()
    today_iso = today.isoformat()
    tickers = sorted(
        {str(position.get("ticker") or "").strip().upper() for position in positions}
    )

    for ticker in tickers:
        if not ticker:
            continue

        upsert_ticker_metadata(supabase, ticker)

        meta_result = (
            supabase.table("ticker_metadata")
            .select("*")
            .eq("ticker", ticker)
            .limit(1)
            .execute()
        )

        if not meta_result.data:
            continue

        metadata = meta_result.data[0]

        previous_score_result = (
            supabase.table("asset_safety_profiles")
            .select("safety_score")
            .eq("ticker", ticker)
            .order("as_of_date", desc=True)
            .limit(1)
            .execute()
        )
        previous_safety = (
            previous_score_result.data[0].get("safety_score")
            if previous_score_result.data
            else None
        )

        structural_result = calculate_structural_base_score(
            market_cap=metadata.get("market_cap"),
            avg_daily_dollar_volume=metadata.get("avg_daily_dollar_volume"),
            volatility_proxy=metadata.get("volatility_proxy"),
            leverage_profile=metadata.get("leverage_profile", "moderate"),
            profitability_profile=metadata.get("profitability_profile", "mixed"),
            asset_class=metadata.get("asset_class"),
        )

        safety_score = structural_result["structural_base_score"]
        if previous_safety is not None:
            from .structural_scorer import get_daily_move_cap

            market_cap = metadata.get("market_cap")
            asset_class = metadata.get("asset_class")
            cap = get_daily_move_cap(asset_class, market_cap)
            delta = safety_score - previous_safety
            if abs(delta) > cap:
                safety_score = previous_safety + (cap if delta > 0 else -cap)
            safety_score = clamp_score(safety_score, 50)

        factor_breakdown = structural_result.get("factor_breakdown", {})

        profile_payload = {
            "ticker": ticker,
            "as_of_date": today_iso,
            "structural_base_score": structural_result["structural_base_score"],
            "macro_adjustment": 0.0,
            "event_adjustment": 0.0,
            "safety_score": safety_score,
            "confidence": structural_result["confidence"],
            "asset_class": metadata.get("asset_class"),
            "regime_state": "neutral",
            "market_cap_bucket": structural_result.get("market_cap_bucket"),
            "liquidity_score": factor_breakdown.get("liquidity_score"),
            "volatility_score": factor_breakdown.get("volatility_score"),
            "leverage_score": factor_breakdown.get("leverage_score"),
            "profitability_score": factor_breakdown.get("profitability_score"),
            "factor_breakdown": factor_breakdown,
        }

        supabase.table("asset_safety_profiles").upsert(
            profile_payload,
            on_conflict="ticker,as_of_date",
        ).execute()

    return {"status": "structural_refresh_complete", "user_id": user_id}


async def reschedule_user_digest(user_id: str):
    from ..services.supabase import get_supabase

    supabase = get_supabase()

    prefs = (
        supabase.table("user_preferences")
        .select("digest_time, notifications_enabled")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )

    if not prefs:
        _mark_scheduler_inactive(
            supabase,
            user_id,
            digest_time=DEFAULT_DIGEST_TIME,
            notifications_enabled=False,
            last_run_status="missing_preferences",
            last_error="User preferences row not found during reschedule.",
        )
        return

    pref = prefs[0]
    _sync_user_job(
        supabase,
        user_id,
        pref.get("digest_time", DEFAULT_DIGEST_TIME),
        bool(pref.get("notifications_enabled", False)),
    )


def get_scheduler_status_for_user(user_id: str) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    prefs = (
        supabase.table("user_preferences")
        .select("digest_time, notifications_enabled")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    state = _load_scheduler_state(supabase, user_id)
    job = scheduler.get_job(_job_id_for_user(user_id))

    pref = prefs[0] if prefs else {}
    last_run_status = state.get("last_run_status") if state else None
    last_run_at = state.get("last_run_at") if state else None
    last_success_at = (
        last_run_at if last_run_status in {"completed", "success"} else None
    )
    last_failure_at = (
        last_run_at
        if last_run_status
        and last_run_status not in {"completed", "success", "running"}
        else None
    )
    next_run_at = _serialize_datetime(
        job.next_run_time if job else state.get("next_run_at") if state else None
    )
    next_run_at_raw = (
        job.next_run_time if job else state.get("next_run_at") if state else None
    )
    return {
        "user_id": user_id,
        "digest_time": pref.get(
            "digest_time", state.get("digest_time") if state else DEFAULT_DIGEST_TIME
        ),
        "notifications_enabled": pref.get(
            "notifications_enabled",
            state.get("notifications_enabled") if state else False,
        ),
        "runtime_job_present": job is not None,
        "runtime_next_run_at": next_run_at,
        "runtime_next_run_at_et": _fmt_both_tz(next_run_at_raw),
        "last_success_at": last_success_at,
        "last_failure_at": last_failure_at,
        "last_run_status": last_run_status,
        "persisted_state": state,
    }


def get_sp500_cache_status(limit: int = 10) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    ensure_sp500_universe_seeded(supabase)
    universe = list_active_sp500_tickers(supabase)
    latest_jobs = (
        supabase.table("ticker_refresh_jobs")
        .select("ticker, status, job_type, created_at, completed_at, error_message")
        .order("created_at", desc=True)
        .limit(max(limit, 25))
        .execute()
        .data
        or []
    )
    latest_snapshots = (
        supabase.table("ticker_risk_snapshots")
        .select("ticker, analysis_as_of, snapshot_type")
        .order("analysis_as_of", desc=True)
        .limit(max(limit, 25))
        .execute()
        .data
        or []
    )
    snapshot_tickers = {row["ticker"] for row in latest_snapshots}
    completed_jobs = [row for row in latest_jobs if row.get("status") == "completed"]
    job_state = {
        "daily": {
            "present": scheduler.get_job(SP500_DAILY_JOB_ID) is not None,
            "next_run_at": _fmt_both_tz(
                scheduler.get_job(SP500_DAILY_JOB_ID).next_run_time
                if scheduler.get_job(SP500_DAILY_JOB_ID)
                else None
            ),
            "last_success_at": next(
                (
                    row.get("completed_at")
                    for row in latest_jobs
                    if row.get("job_type") == "daily_refresh"
                    and row.get("status") == "completed"
                ),
                None,
            ),
            "last_failure_at": next(
                (
                    row.get("completed_at")
                    for row in latest_jobs
                    if row.get("job_type") == "daily_refresh"
                    and row.get("status") == "failed"
                ),
                None,
            ),
        },
        "backfill": {
            "present": scheduler.get_job(SP500_BACKFILL_JOB_ID) is not None,
            "next_run_at": _fmt_both_tz(
                scheduler.get_job(SP500_BACKFILL_JOB_ID).next_run_time
                if scheduler.get_job(SP500_BACKFILL_JOB_ID)
                else None
            ),
            "last_success_at": next(
                (
                    row.get("completed_at")
                    for row in latest_jobs
                    if row.get("job_type") == "backfill"
                    and row.get("status") == "completed"
                ),
                None,
            ),
            "last_failure_at": next(
                (
                    row.get("completed_at")
                    for row in latest_jobs
                    if row.get("job_type") == "backfill"
                    and row.get("status") == "failed"
                ),
                None,
            ),
        },
    }

    return {
        "universe_size": len(universe),
        "coverage_count": len(snapshot_tickers),
        "daily_job_present": scheduler.get_job(SP500_DAILY_JOB_ID) is not None,
        "daily_next_run_at": _fmt_both_tz(
            scheduler.get_job(SP500_DAILY_JOB_ID).next_run_time
            if scheduler.get_job(SP500_DAILY_JOB_ID)
            else None
        ),
        "backfill_job_present": scheduler.get_job(SP500_BACKFILL_JOB_ID) is not None,
        "backfill_next_run_at": _fmt_both_tz(
            scheduler.get_job(SP500_BACKFILL_JOB_ID).next_run_time
            if scheduler.get_job(SP500_BACKFILL_JOB_ID)
            else None
        ),
        "recent_jobs": latest_jobs[:limit],
        "recent_snapshots": latest_snapshots[:limit],
        "completed_job_count_sample": len(completed_jobs),
        "job_state": job_state,
    }


async def _get_or_create_sp500_system_user(supabase) -> str:
    existing = (
        supabase.table("user_preferences")
        .select("user_id")
        .eq("user_id", SYSTEM_SP500_USER_ID)
        .limit(1)
        .execute()
    )
    if not existing.data:
        supabase.table("user_preferences").insert(
            {
                "user_id": SYSTEM_SP500_USER_ID,
                "notifications_enabled": False,
            }
        ).execute()
    return SYSTEM_SP500_USER_ID


async def _ensure_sp500_system_positions(supabase, tickers: list[str]) -> None:
    user_id = await _get_or_create_sp500_system_user(supabase)
    existing = (
        supabase.table("positions").select("ticker").eq("user_id", user_id).execute()
    )
    existing_tickers = {row["ticker"] for row in (existing.data or [])}
    missing_tickers = [t for t in tickers if t not in existing_tickers]
    if not missing_tickers:
        return
    rows = [
        {
            "user_id": user_id,
            "ticker": t.upper(),
            "shares": 0.0,
            "purchase_price": 0.0,
            "archetype": "growth",
        }
        for t in missing_tickers
    ]
    for chunk_start in range(0, len(rows), 100):
        chunk = rows[chunk_start : chunk_start + 100]
        supabase.table("positions").insert(chunk).execute()


async def _sync_ai_scores_to_ticker_snapshots(
    supabase, ticker: str, job_type: str
) -> None:
    await asyncio.to_thread(
        _sync_ai_scores_to_ticker_snapshots_sync, supabase, ticker, job_type
    )


def _sync_ai_scores_to_ticker_snapshots_sync(
    supabase, ticker: str, job_type: str
) -> None:
    from .risk_scorer import score_to_grade
    from ..services.ticker_cache_service import _upsert_ticker_snapshot

    user_id = SYSTEM_SP500_USER_ID
    position_rows = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("user_id", user_id)
        .eq("ticker", ticker.upper())
        .limit(1)
        .execute()
        .data
    )
    if not position_rows:
        return
    position_id = position_rows[0]["id"]
    latest_score_rows = (
        supabase.table("risk_scores")
        .select("*")
        .eq("position_id", position_id)
        .order("calculated_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if not latest_score_rows:
        return
    ai_score = latest_score_rows[0]
    latest_analysis_rows = (
        supabase.table("position_analyses")
        .select("*")
        .eq("position_id", position_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    analysis = latest_analysis_rows[0] if latest_analysis_rows else {}
    now_iso = utcnow_iso()
    safety_score = ai_score.get("safety_score") or ai_score.get("total_score") or 50
    grade = ai_score.get("grade") or score_to_grade(safety_score)
    factor_breakdown = ai_score.get("factor_breakdown") or {}
    if isinstance(factor_breakdown, str):
        import json

        try:
            factor_breakdown = json.loads(factor_breakdown)
        except Exception:
            factor_breakdown = {}
    stored_ai_dims = factor_breakdown.get("ai_dimensions") or {}
    factor_breakdown = {
        **factor_breakdown,
        "ai_dimensions": {
            "news_sentiment": stored_ai_dims.get("news_sentiment")
            or ai_score.get("news_sentiment"),
            "macro_exposure": stored_ai_dims.get("macro_exposure")
            or ai_score.get("macro_exposure"),
            "position_sizing": stored_ai_dims.get("position_sizing")
            or ai_score.get("position_sizing"),
            "volatility_trend": stored_ai_dims.get("volatility_trend")
            or ai_score.get("volatility_trend"),
        },
    }
    payload = {
        "ticker": ticker.upper(),
        "snapshot_date": datetime.utcnow().date().isoformat(),
        "snapshot_type": job_type,
        "grade": grade,
        "safety_score": round(float(safety_score), 1),
        "structural_base_score": ai_score.get("structural_base_score"),
        "macro_adjustment": ai_score.get("macro_adjustment") or 0.0,
        "event_adjustment": ai_score.get("event_adjustment") or 0.0,
        "confidence": ai_score.get("confidence"),
        "factor_breakdown": factor_breakdown,
        "dimension_rationale": ai_score.get("dimension_rationale") or {},
        "reasoning": ai_score.get("reasoning") or analysis.get("summary") or "",
        "news_summary": analysis.get("summary") or "",
        "source_count": ai_score.get("source_count", 0),
        "methodology_version": (
            (
                "sp500-ai-backfill-v2"
                if job_type == "backfill"
                else "sp500-ai-analysis-v2"
            )
            if ai_score.get("llm_scoring_used")
            else (
                "sp500-backfill-deterministic-fallback-v1"
                if job_type == "backfill"
                else "sp500-analysis-deterministic-fallback-v1"
            )
        ),
        "analysis_as_of": ai_score.get("calculated_at") or now_iso,
        "refresh_triggered_by_user_id": None,
        "updated_at": now_iso,
    }
    _upsert_ticker_snapshot(
        supabase,
        ticker=ticker.upper(),
        snapshot_type=job_type,
        payload=payload,
    )


async def refresh_sp500_cache(
    limit: int | None = None, job_type: str = "daily"
) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    ensure_sp500_universe_seeded(supabase)
    tickers = list_active_sp500_tickers(supabase, limit=limit)

    await _ensure_sp500_system_positions(supabase, tickers)

    user_id = SYSTEM_SP500_USER_ID
    system_positions = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("user_id", user_id)
        .in_("ticker", [t.upper() for t in tickers])
        .execute()
        .data
    )
    if not system_positions:
        return {
            "status": "error",
            "job_type": job_type,
            "requested": len(tickers),
            "refreshed": 0,
            "failed": [{"error": "No system positions found for SP500 tickers"}],
        }

    refreshed = 0
    failed: list[dict] = []

    for pos in system_positions:
        ticker = pos["ticker"]
        try:
            await asyncio.to_thread(
                refresh_ticker_snapshot,
                supabase,
                ticker=ticker,
                job_type=job_type,
                requested_by_user_id=None,
            )
            refreshed += 1
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})

    return {
        "status": "ok" if not failed else "partial",
        "job_type": job_type,
        "requested": len(tickers),
        "refreshed": refreshed,
        "failed": failed,
    }


async def run_sp500_full_ai_analysis(
    limit: int | None = None, job_type: str = "daily"
) -> dict:
    """Run full AI analysis for S&P 500 tickers and sync results to ticker_risk_snapshots.

    This replaces the formula-only structural scoring with actual AI-powered analysis:
    - Creates system SP500 positions if they don't exist
    - Runs the full analysis pipeline (news, relevance, significance, events, AI scoring)
    - Syncs AI scores to ticker_risk_snapshots so the position page shows real AI analysis
    """
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    ensure_sp500_universe_seeded(supabase)
    tickers = list_active_sp500_tickers(supabase, limit=limit)

    await _ensure_sp500_system_positions(supabase, tickers)

    user_id = SYSTEM_SP500_USER_ID
    system_positions = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("user_id", user_id)
        .in_("ticker", [t.upper() for t in tickers])
        .execute()
        .data
    )
    if not system_positions:
        return {
            "status": "error",
            "job_type": job_type,
            "requested": len(tickers),
            "refreshed": 0,
            "failed": [{"error": "No system positions found for SP500 tickers"}],
        }

    refreshed = 0
    failed: list[dict] = []

    for pos in system_positions:
        ticker = pos["ticker"]
        position_id = pos["id"]
        try:
            result = await enqueue_analysis_run(
                user_id=user_id,
                triggered_by="scheduled",
                target_position_id=position_id,
                skip_metadata_refresh=True,
            )
            if result.get("status") in ("queued", "running"):
                import time

                run_id = result.get("analysis_run_id")
                for _ in range(300):
                    await asyncio.sleep(2)
                    run_check = (
                        supabase.table("analysis_runs")
                        .select("status")
                        .eq("id", run_id)
                        .limit(1)
                        .execute()
                        .data
                    )
                    if run_check and run_check[0]["status"] in ("completed", "failed"):
                        break
            await _sync_ai_scores_to_ticker_snapshots(supabase, ticker, job_type)
            refreshed += 1
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})
            print(f"Error running AI analysis for {ticker}: {exc}")

    return {
        "status": "ok" if not failed else "partial",
        "job_type": job_type,
        "requested": len(tickers),
        "refreshed": refreshed,
        "failed": failed,
    }


async def run_sp500_full_ai_analysis_fast(
    limit: int | None = None,
    job_type: str = "daily",
    batch_size: int = 10,
    backfill_run_id: str | None = None,
    skip_structural: bool = False,
    tickers_override: list[str] | None = None,
) -> dict:
    """Efficient batch AI analysis for S&P 500 tickers.

    Optimizations:
    1. Optional structural refresh (can be skipped when metadata is fresh)
    2. Parallel structural refreshes (4 concurrent) scoped to limited tickers
    3. Chunked AI analysis runs with capped concurrency
    4. Batch sync of AI scores to ticker_risk_snapshots
    """
    import logging

    for _logger_name in (
        "requests",
        "urllib3",
        "http.client",
        "requests.packages.urllib3",
    ):
        _l = logging.getLogger(_logger_name)
        _l.setLevel(logging.WARNING)
        _l.disabled = True

    from ..services.supabase import get_supabase

    supabase = get_supabase()
    logger.info(
        "SP500 fast analysis starting: tickers_override=%s limit=%s skip_structural=%s batch_size=%s backfill_run_id=%s",
        tickers_override is not None, limit, skip_structural, batch_size, backfill_run_id,
    )
    print(f"[SP500] run_sp500_full_ai_analysis_fast starting, skip_structural={skip_structural}, batch_size={batch_size}, backfill_run_id={backfill_run_id}")

    def _update_backfill_progress(message: str, **extra_fields) -> None:
        if not backfill_run_id:
            return
        _set_analysis_stage(
            supabase,
            backfill_run_id,
            "sp500_running_batches",
            message,
            status="running",
            **extra_fields,
        )

    if tickers_override is not None:
        tickers = sorted({t.strip().upper() for t in tickers_override if t.strip()})
    else:
        ensure_sp500_universe_seeded(supabase)
        tickers = list_active_sp500_tickers(supabase, limit=limit)

    await _ensure_sp500_system_positions(supabase, tickers)

    user_id = SYSTEM_SP500_USER_ID
    system_positions = (
        supabase.table("positions")
        .select("id, ticker")
        .eq("user_id", user_id)
        .in_("ticker", [t.upper() for t in tickers])
        .execute()
        .data
    )
    if not system_positions:
        return {
            "status": "error",
            "job_type": job_type,
            "requested": len(tickers),
            "refreshed": 0,
            "failed": [{"error": "No system positions found for SP500 tickers"}],
        }

    REFRESH_CONCURRENCY = 2

    def _print_ticker_analysis(ticker: str, meta: dict) -> None:
        pe = meta.get("pe_ratio") or "N/A"
        high52 = meta.get("week_52_high") or "N/A"
        low52 = meta.get("week_52_low") or "N/A"
        price = meta.get("price") or "N/A"
        vol = meta.get("volatility_proxy")
        vol_str = f"{vol:.3f}" if vol is not None else "N/A"
        liq = meta.get("avg_daily_dollar_volume")
        liq_str = f"${liq / 1e6:.1f}M" if liq is not None else "N/A"
        beta = meta.get("beta") or "N/A"
        market_cap = meta.get("market_cap")
        mc_str = f"${market_cap / 1e9:.1f}B" if market_cap is not None else "N/A"
        sector = meta.get("sector") or "N/A"

        snap = (
            supabase.table("ticker_risk_snapshots")
            .select("grade, safety_score, factor_breakdown")
            .eq("ticker", ticker.upper())
            .eq("snapshot_type", job_type)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        grade = "N/A"
        score = "N/A"
        if snap:
            grade = snap[0].get("grade") or "N/A"
            score = snap[0].get("safety_score") or "N/A"
            fb = snap[0].get("factor_breakdown") or {}
            if isinstance(fb, str):
                import json

                try:
                    fb = json.loads(fb)
                except Exception:
                    fb = {}
            liq_score = fb.get("liquidity_score", "N/A")
            vol_score = fb.get("volatility_score", "N/A")
            lev_score = fb.get("leverage_score", "N/A")
            prof_score = fb.get("profitability_score", "N/A")
            print(
                f"[{ticker}] Structural: Price=${price} | PE={pe} | 52W: ${low52}-${high52} | "
                f"Grade={grade} Score={score} | Liquidity={liq_score} | Volatility={vol_score} | "
                f"Leverage={lev_score} | Profitability={prof_score} | Beta={beta} | "
                f"MC={mc_str} | Sector={sector}"
            )
            return

        print(
            f"[{ticker}] Structural: Price=${price} | PE={pe} | 52W: ${low52}-${high52} | "
            f"Grade={grade} Score={score} | Liquidity={liq_str} Vol={vol_str} | "
            f"Beta={beta} | MC={mc_str} | Sector={sector}"
        )

    failed_refresh: list[dict] = []
    successful = [p["ticker"] for p in system_positions]
    print(f"[SP500] Building shared news payload for {len(successful)} tickers...")
    _update_backfill_progress(
        f"Building shared news payload for {len(successful)} tickers...",
        positions_processed=0,
    )
    try:
        shared_news_payload = await asyncio.wait_for(
            _build_shared_news_payload(
                successful,
                await _load_ticker_metadata_map(supabase, successful),
            ),
            timeout=600,
        )
    except asyncio.TimeoutError:
        logger.error("SP500 _build_shared_news_payload timed out after 600s")
        print("[SP500] _build_shared_news_payload timed out after 600s")
        shared_news_payload = {
            "macro_articles": [],
            "cnbc_sector_articles": [],
            "google_sector_articles": [],
            "sector_articles": [],
            "company_articles": [],
            "market_articles": [],
            "sector_names": [],
            "sector_context": {},
            "raw_articles": [],
            "normalized_articles": [],
        }
    print(f"[SP500] Shared news payload built: macro={len(shared_news_payload.get('macro_articles', []))} company={len(shared_news_payload.get('company_articles', []))} market={len(shared_news_payload.get('market_articles', []))} sector={len(shared_news_payload.get('sector_articles', []))}")
    _update_backfill_progress(
        f"Shared news cache built for {len(successful)} tickers.",
        positions_processed=0,
    )

    if skip_structural:
        print(
            f"[SP500] Skipping structural refresh (using cached metadata for {len(successful)} tickers)..."
        )
        _update_backfill_progress(
            f"Skipping structural refresh. Starting AI analysis for {len(successful)} tickers.",
            positions_processed=0,
        )
    else:
        print(
            f"[SP500] Starting structural refresh for {len(system_positions)} tickers (scoped to limit={limit})..."
        )
        _update_backfill_progress(
            f"Refreshing structural data for {len(system_positions)} S&P tickers.",
            positions_processed=0,
        )
        semaphore = asyncio.Semaphore(REFRESH_CONCURRENCY)

        async def _refresh_one(pos: dict) -> str:
            ticker = pos["ticker"]
            async with semaphore:
                try:
                    await asyncio.to_thread(
                        refresh_ticker_snapshot,
                        supabase,
                        ticker=ticker,
                        job_type=job_type,
                        requested_by_user_id=None,
                    )
                    meta = (
                        supabase.table("ticker_metadata")
                        .select(
                            "pe_ratio, week_52_high, week_52_low, price, volatility_proxy, "
                            "avg_daily_dollar_volume, beta, market_cap, sector"
                        )
                        .eq("ticker", ticker.upper())
                        .limit(1)
                        .execute()
                        .data
                    )
                    if meta:
                        _print_ticker_analysis(ticker, meta[0])
                    return ticker
                except Exception as exc:
                    failed_refresh.append({"ticker": ticker, "error": str(exc)})
                    print(f"[SP500] Refresh error for {ticker}: {exc}")
                    return None

        # `asyncio.gather()` already schedules the refresh coroutines; wrapping it
        # in `create_task()` is invalid because it returns a Future, not a coroutine.
        refresh_task = asyncio.gather(
            *(_refresh_one(p) for p in system_positions), return_exceptions=True
        )

    batch_size = max(1, int(batch_size))
    total_batches = (len(successful) + batch_size - 1) // batch_size
    print(
        f"[SP500] Starting batch AI analysis for {len(successful)} tickers in {total_batches} batches of {batch_size}..."
    )
    _update_backfill_progress(
        f"Starting {total_batches} AI batches for {len(successful)} tickers.",
        positions_processed=0,
    )

    synced = 0
    artifact_dirs: list[str] = []
    failed_batches: list[dict] = []
    failed_sync: list[dict] = []
    progress_lock = asyncio.Lock()

    def _print_ai_scores(ticker: str, meta: dict, analysis_run_id: str) -> None:
        position_rows = (
            supabase.table("positions")
            .select("id")
            .eq("user_id", user_id)
            .eq("ticker", ticker.upper())
            .limit(1)
            .execute()
            .data
        )
        latest_score = None
        if position_rows:
            latest_score_rows = (
                supabase.table("risk_scores")
                .select(
                    "news_sentiment, macro_exposure, position_sizing, volatility_trend, total_score, reasoning, analysis_run_id"
                )
                .eq("position_id", position_rows[0]["id"])
                .eq("analysis_run_id", analysis_run_id)
                .order("calculated_at", desc=True)
                .limit(1)
                .execute()
                .data
            )
            latest_score = latest_score_rows[0] if latest_score_rows else None

        snap = (
            supabase.table("ticker_risk_snapshots")
            .select("grade, safety_score, reasoning, methodology_version")
            .eq("ticker", ticker.upper())
            .eq("snapshot_type", job_type)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if not snap:
            print(f"[{ticker}] AI: no snapshot found")
            return
        s = snap[0]
        grade = s.get("grade") or "N/A"
        score = s.get("safety_score") or "N/A"
        method = s.get("methodology_version") or ""
        news_sent = latest_score.get("news_sentiment") if latest_score else "N/A"
        macro_exp = latest_score.get("macro_exposure") if latest_score else "N/A"
        pos_size = latest_score.get("position_sizing") if latest_score else "N/A"
        vol_trend = latest_score.get("volatility_trend") if latest_score else "N/A"
        reasoning = (latest_score or {}).get("reasoning") or s.get("reasoning") or ""
        short_reasoning = reasoning[:80] + "..." if len(reasoning) > 80 else reasoning
        ai_tag = " [AI]" if "sp500-ai" in method else ""
        print(
            f"[{ticker}] AI{ai_tag}: Grade={grade} Score={score} | "
            f"NewsSentiment={news_sent} | MacroExposure={macro_exp} | "
            f"PositionSizing={pos_size} | VolatilityTrend={vol_trend} | "
            f"Reasoning: {short_reasoning}"
        )

    async def _run_batch(batch_number: int, batch_tickers: list[str]) -> dict:
        nonlocal synced

        print(
            f"[SP500] Running batch {batch_number}/{total_batches} with {len(batch_tickers)} tickers..."
        )
        _update_backfill_progress(
            f"Running batch {batch_number}/{total_batches} with {len(batch_tickers)} tickers.",
            positions_processed=synced,
        )
        result = await enqueue_analysis_run(
            user_id=user_id,
            triggered_by="scheduled",
            target_position_id=None,
            skip_metadata_refresh=True,
            target_tickers=batch_tickers,
            artifact_label=f"sp500_{job_type}_batch_{batch_number}",
            allow_parallel_runs=True,
            shared_news_payload=shared_news_payload,
        )
        run_id = result.get("analysis_run_id")
        if not run_id:
            failure = {
                "batch": batch_number,
                "tickers": batch_tickers,
                "error": "Failed to enqueue analysis run",
            }
            print(f"[SP500] Failed to enqueue batch {batch_number}/{total_batches}")
            return {
                "batch": batch_number,
                "synced": 0,
                "artifact_dir": None,
                "failed_batch": failure,
                "failed_sync": [],
            }

        artifact_dir = str(get_run_artifact_dir(run_id))
        print(
            f"[SP500] Saving debug artifacts for batch {batch_number} to {artifact_dir}"
        )
        print(
            f"[SP500] Waiting for batch {batch_number}/{total_batches} run {run_id} to complete..."
        )
        _update_backfill_progress(
            f"Waiting for batch {batch_number}/{total_batches} run {run_id} to finish.",
            positions_processed=synced,
        )

        run_state = None
        for i in range(600):
            await asyncio.sleep(5)
            try:
                run_check = _execute_supabase_with_retry(
                    lambda: (
                        supabase.table("analysis_runs")
                        .select(
                            "status, current_stage, current_stage_message, error_message"
                        )
                        .eq("id", run_id)
                        .limit(1)
                        .execute()
                        .data
                    ),
                    context=f"analysis_runs batch status poll {run_id}",
                )
            except Exception as exc:
                print(
                    f"[SP500] Batch {batch_number}/{total_batches} status read failed: {exc}"
                )
                continue
            if run_check:
                run_state = run_check[0]
            if run_state and run_state["status"] in ("completed", "failed"):
                print(
                    f"[SP500] Batch {batch_number}/{total_batches} analysis run {run_state['status']}"
                    + (
                        f": {run_state.get('error_message') or run_state.get('current_stage_message') or ''}"
                        if run_state["status"] != "completed"
                        else ""
                    )
                )
                break
            if i % 12 == 0:
                print(
                    f"[SP500] Batch {batch_number}/{total_batches} still running... ({i * 5}s elapsed)"
                )

        if not run_state:
            failure = {
                "batch": batch_number,
                "tickers": batch_tickers,
                "run_id": run_id,
                "error": f"Unable to read analysis run status for {run_id}",
            }
            return {
                "batch": batch_number,
                "synced": 0,
                "artifact_dir": artifact_dir,
                "failed_batch": failure,
                "failed_sync": [],
            }

        if run_state.get("status") != "completed":
            failure = {
                "batch": batch_number,
                "tickers": batch_tickers,
                "run_id": run_id,
                "stage": run_state.get("current_stage"),
                "error": run_state.get("error_message")
                or run_state.get("current_stage_message")
                or "Analysis did not complete successfully",
            }
            return {
                "batch": batch_number,
                "synced": 0,
                "artifact_dir": artifact_dir,
                "failed_batch": failure,
                "failed_sync": [],
            }

        print(
            f"[SP500] Syncing AI scores for batch {batch_number}/{total_batches} ({len(batch_tickers)} tickers)..."
        )
        _update_backfill_progress(
            f"Syncing AI scores for batch {batch_number}/{total_batches}.",
            positions_processed=synced,
        )
        sync_semaphore = asyncio.Semaphore(2)

        async def _sync_one_ticker(ticker: str):
            async with sync_semaphore:
                await _sync_ai_scores_to_ticker_snapshots(supabase, ticker, job_type)
                return ticker

        sync_results = await asyncio.gather(
            *(_sync_one_ticker(ticker) for ticker in batch_tickers),
            return_exceptions=True,
        )
        batch_failed_sync: list[dict] = []
        batch_synced = 0
        for ticker, sync_result in zip(batch_tickers, sync_results):
            if isinstance(sync_result, Exception):
                batch_failed_sync.append({"ticker": ticker, "error": str(sync_result)})
                print(f"[{ticker}] Sync error: {sync_result}")
                continue

            meta = (
                supabase.table("ticker_metadata")
                .select("pe_ratio, price, sector")
                .eq("ticker", ticker.upper())
                .limit(1)
                .execute()
                .data
            )
            if meta:
                m = meta[0]
                print(
                    f"[{ticker}] Final: Price=${m.get('price') or 'N/A'} | PE=${m.get('pe_ratio') or 'N/A'} | Sector={m.get('sector') or 'N/A'} | Methodology={job_type}"
                )
            _print_ai_scores(ticker, meta[0] if meta else {}, run_id)
            batch_synced += 1

        async with progress_lock:
            synced += batch_synced
            current_synced = synced

        _update_backfill_progress(
            f"Finished batch {batch_number}/{total_batches}. Synced {current_synced}/{len(successful)} tickers so far.",
            positions_processed=current_synced,
        )
        return {
            "batch": batch_number,
            "synced": batch_synced,
            "artifact_dir": artifact_dir,
            "failed_batch": None,
            "failed_sync": batch_failed_sync,
        }

    batch_jobs: list[tuple[int, list[str]]] = [
        (
            (batch_index // batch_size) + 1,
            successful[batch_index : batch_index + batch_size],
        )
        for batch_index in range(0, len(successful), batch_size)
    ]
    batch_concurrency = max(1, min(2, len(batch_jobs)))
    print(
        f"[SP500] Running {len(batch_jobs)} analysis batches with concurrency {batch_concurrency}..."
    )
    batch_results: list[dict] = []
    for chunk_start in range(0, len(batch_jobs), batch_concurrency):
        chunk = batch_jobs[chunk_start : chunk_start + batch_concurrency]
        chunk_results = await asyncio.gather(
            *(
                _run_batch(batch_number, batch_tickers)
                for batch_number, batch_tickers in chunk
            ),
            return_exceptions=True,
        )
        for result in chunk_results:
            if isinstance(result, Exception):
                failed_batches.append({"error": str(result)})
                print(f"[SP500] Batch worker error: {result}")
                continue
            batch_results.append(result)

    if not skip_structural:
        refresh_results = await refresh_task
        refresh_successful = [
            r for r in refresh_results if r and not isinstance(r, Exception)
        ]
        refresh_failed = [r for r in refresh_results if isinstance(r, Exception)]
        if refresh_failed:
            failed_refresh.extend(
                [{"ticker": str(r), "error": str(r)} for r in refresh_failed]
            )
        print(
            f"[SP500] Structural refresh complete: {len(refresh_successful)}/{len(system_positions)} succeeded"
        )

    for result in sorted(batch_results, key=lambda item: item.get("batch", 0)):
        if result.get("artifact_dir"):
            artifact_dirs.append(result["artifact_dir"])
        if result.get("failed_batch"):
            failed_batches.append(result["failed_batch"])
        if result.get("failed_sync"):
            failed_sync.extend(result["failed_sync"])

    all_failed = failed_refresh + failed_batches + failed_sync
    print(
        f"[SP500] Done. Synced {synced}/{len(successful)} snapshots across {len(artifact_dirs)} batches. Failed: {len(all_failed)}"
    )
    return {
        "status": "ok" if not all_failed else "partial",
        "job_type": job_type,
        "requested": len(tickers),
        "refreshed": synced,
        "artifact_dir": artifact_dirs[-1] if artifact_dirs else None,
        "artifact_dirs": artifact_dirs,
        "failed": all_failed,
    }


async def seed_sp500_universe() -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    before = len(list_active_sp500_tickers(supabase))
    ensure_sp500_universe_seeded(supabase)
    after = len(list_active_sp500_tickers(supabase))
    return {"status": "ok", "tracked_tickers": after, "added": max(after - before, 0)}


def _get_all_user_held_tickers(supabase) -> list[str]:
    rows = (
        supabase.table("positions")
        .select("ticker")
        .neq("user_id", SYSTEM_SP500_USER_ID)
        .execute()
        .data
    )
    return sorted(
        {str(r["ticker"]).strip().upper() for r in (rows or []) if r.get("ticker")}
    )


async def run_user_holdings_daily_ai_refresh(
    backfill_run_id: str | None = None,
) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    tickers = _get_all_user_held_tickers(supabase)
    if not tickers:
        logger.info(
            "[HOLDINGS_AI] No user-held tickers found — skipping daily AI refresh."
        )
        return {"status": "skipped", "reason": "no_user_tickers", "refreshed": 0}

    logger.info(
        "[HOLDINGS_AI] Starting daily AI refresh for %d user-held tickers: %s",
        len(tickers),
        tickers,
    )
    try:
        result = await run_sp500_full_ai_analysis_fast(
            job_type="daily",
            batch_size=25,
            backfill_run_id=backfill_run_id,
            skip_structural=False,
            tickers_override=tickers,
        )
        logger.info("[HOLDINGS_AI] Daily AI refresh complete: %s", result)
        return result
    except Exception as exc:
        logger.error("[HOLDINGS_AI] Daily AI refresh failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc), "refreshed": 0}


def _schedule_holdings_daily_ai_refresh() -> None:
    if scheduler.get_job(HOLDINGS_DAILY_AI_JOB_ID):
        scheduler.remove_job(HOLDINGS_DAILY_AI_JOB_ID)
    scheduler.add_job(
        run_user_holdings_daily_ai_refresh,
        trigger=CronTrigger(hour=7, minute=0, timezone=ET),
        id=HOLDINGS_DAILY_AI_JOB_ID,
        replace_existing=True,
        misfire_grace_time=3600,
    )


def _next_et_backfill_time(reference: datetime | None = None) -> datetime:
    current_time = reference or datetime.now(ET)
    run_time = current_time.replace(hour=7, minute=30, second=0, microsecond=0)
    if run_time <= current_time:
        run_time += timedelta(days=1)
    return run_time


async def _run_scheduled_sp500_backfill() -> None:
    try:
        await enqueue_sp500_backfill_run(
            requested_by_user_id=SYSTEM_SP500_USER_ID,
            job_type="backfill",
            batch_size=10,
        )
    except Exception as exc:
        logger.error(
            "[SP500_BACKFILL] Scheduled S&P 500 backfill failed: %s",
            exc,
            exc_info=True,
        )


def _schedule_sp500_backfill() -> None:
    if scheduler.get_job(SP500_BACKFILL_JOB_ID):
        scheduler.remove_job(SP500_BACKFILL_JOB_ID)
    scheduler.add_job(
        _run_scheduled_sp500_backfill,
        trigger=CronTrigger(hour=7, minute=30, timezone=ET),
        id=SP500_BACKFILL_JOB_ID,
        replace_existing=True,
        misfire_grace_time=6 * 3600,
    )


def _schedule_sp500_daily_refresh() -> None:
    if scheduler.get_job(SP500_DAILY_JOB_ID):
        scheduler.remove_job(SP500_DAILY_JOB_ID)
    scheduler.add_job(
        refresh_sp500_cache,
        trigger=CronTrigger(hour=8, minute=0, timezone=ET),
        id=SP500_DAILY_JOB_ID,
        replace_existing=True,
        kwargs={"job_type": "daily"},
    )


def _cleanup_old_news_items() -> None:
    from ..services.supabase import get_supabase

    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    supabase = get_supabase()
    supabase.table("news_items").delete().lt("processed_at", cutoff).execute()
    supabase.table("ticker_news_cache").delete().lt("processed_at", cutoff).execute()


def _schedule_news_cleanup() -> None:
    if scheduler.get_job(NEWS_CLEANUP_JOB_ID):
        scheduler.remove_job(NEWS_CLEANUP_JOB_ID)
    scheduler.add_job(
        _cleanup_old_news_items,
        trigger=CronTrigger(hour=8, minute=30, timezone=ET),
        id=NEWS_CLEANUP_JOB_ID,
        replace_existing=True,
    )


def start_scheduler():
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    _fail_stale_runs(supabase)
    _fail_orphaned_runs(supabase)

    if not scheduler.running:
        scheduler.start()

    _schedule_sp500_backfill()
    _schedule_sp500_daily_refresh()
    _schedule_holdings_daily_ai_refresh()
    _schedule_news_cleanup()

    current_jobs = [
        job.id for job in scheduler.get_jobs() if job.id.startswith(JOB_PREFIX)
    ]
    for job_id in current_jobs:
        scheduler.remove_job(job_id)

    users = (
        supabase.table("user_preferences")
        .select("user_id, digest_time, notifications_enabled")
        .execute()
        .data
    )
    seen_user_ids = set()

    for user in users:
        seen_user_ids.add(user["user_id"])
        _sync_user_job(
            supabase,
            user["user_id"],
            user.get("digest_time", DEFAULT_DIGEST_TIME),
            bool(user.get("notifications_enabled", False)),
        )

    existing_states = (
        supabase.table(SCHEDULER_TABLE).select("user_id, digest_time").execute().data
    )
    for state in existing_states:
        if state["user_id"] in seen_user_ids:
            continue
        _mark_scheduler_inactive(
            supabase,
            state["user_id"],
            digest_time=state.get("digest_time", DEFAULT_DIGEST_TIME),
            notifications_enabled=False,
            last_run_status="orphaned",
            last_error="Scheduler entry no longer has matching user_preferences row.",
        )
