import asyncio
import logging
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .analysis_utils import utcnow_iso, clamp_score
from .news_normalizer import normalize_news_batch
from .portfolio_compiler import compile_portfolio_digest
from .position_classifier import classify_position
from .relevance import classify_relevance
from .risk_scorer import score_position, score_to_grade, score_position_structural
from .portfolio_risk import calculate_portfolio_risk_score
from .structural_scorer import calculate_structural_base_score, get_daily_move_cap
from ..services.ticker_metadata import (
    refresh_all_positions_metadata,
    upsert_ticker_metadata,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
active_runs: dict[str, asyncio.Task] = {}
PROCESS_STARTED_AT = datetime.now(timezone.utc)
RUN_TIMEOUT_SECONDS = 25 * 60
STALE_RUN_HOURS = 1
POSITION_CONCURRENCY = 2
MAX_ARTICLES_PER_POSITION = 3
SCHEDULER_TABLE = "scheduler_jobs"
CACHE_TABLE = "analysis_cache"
DEFAULT_DIGEST_TIME = "07:00"
JOB_PREFIX = "user_"
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


def _dedupe_articles(articles: list[dict]) -> list[dict]:
    deduped = {}
    for article in articles:
        deduped[article["event_hash"]] = article
    return list(deduped.values())


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

    if ticker_token in text:
        score += 5

    ticker_hints = {str(hint).lower() for hint in (article.get("ticker_hints") or [])}
    if ticker_token in ticker_hints:
        score += 4

    if article.get("source_type") == "company_news":
        score += 3
    elif article.get("source_type") == "rss":
        score += 1

    score += sum(2 for keyword in MAJOR_PRIORITY_KEYWORDS if keyword in text)
    published_at = _parse_article_timestamp(article.get("published_at"))
    recency_bonus = max(
        0.0, 72.0 - (datetime.now(timezone.utc) - published_at).total_seconds() / 3600.0
    )
    return score, recency_bonus


def _top_articles_for_position(articles: list[dict], ticker: str) -> list[dict]:
    ranked = sorted(
        articles,
        key=lambda article: _article_priority(article, ticker),
        reverse=True,
    )
    return ranked[:MAX_ARTICLES_PER_POSITION]


def _parse_time_window_hours(hours: int) -> str:
    threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
    return threshold.isoformat()


def _update_analysis_run(supabase, analysis_run_id: str, **fields):
    supabase.table("analysis_runs").update(fields).eq("id", analysis_run_id).execute()


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
    return result.data[0]["payload"] if result.data else None


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


def _sync_user_job(
    supabase,
    user_id: str,
    digest_time: str | None,
    notifications_enabled: bool,
) -> dict:
    normalized_time, hour, minute = _parse_digest_time(digest_time)
    job_id = _job_id_for_user(user_id)

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

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
        CronTrigger(hour=hour, minute=minute),
        id=job_id,
        args=[user_id],
        misfire_grace_time=3600,
        replace_existing=True,
    )

    structural_job_id = f"{JOB_PREFIX}{user_id}_structural_refresh"
    scheduler.add_job(
        trigger_structural_refresh,
        CronTrigger(hour=6, minute=30),
        id=structural_job_id,
        args=[user_id],
        misfire_grace_time=7200,
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
    positions = (
        supabase.table("positions").select("*").eq("user_id", user_id).execute().data
    )
    payloads = []
    for position in positions:
        score_rows = (
            supabase.table("risk_scores")
            .select("*")
            .eq("analysis_run_id", analysis_run_id)
            .eq("position_id", position["id"])
            .limit(1)
            .execute()
            .data
        )
        analysis_rows = (
            supabase.table("position_analyses")
            .select("*")
            .eq("analysis_run_id", analysis_run_id)
            .eq("position_id", position["id"])
            .limit(1)
            .execute()
            .data
        )
        if not score_rows or not analysis_rows:
            continue

        history_rows = (
            supabase.table("risk_scores")
            .select("analysis_run_id, grade")
            .eq("position_id", position["id"])
            .order("calculated_at", desc=True)
            .limit(2)
            .execute()
            .data
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
    position_payloads = _load_completed_position_payloads(
        supabase, user_id, analysis_run_id
    )
    if not position_payloads:
        return False

    events_processed = (
        supabase.table("event_analyses")
        .select("id", count="exact")
        .eq("analysis_run_id", analysis_run_id)
        .execute()
        .count
        or 0
    )
    portfolio_score, overall_grade = _compute_portfolio_grade(position_payloads)
    digest = await compile_portfolio_digest(position_payloads, overall_grade)

    existing_digest = (
        supabase.table("digests")
        .select("id")
        .eq("analysis_run_id", analysis_run_id)
        .limit(1)
        .execute()
        .data
    )
    if not existing_digest:
        supabase.table("digests").insert(
            {
                "user_id": user_id,
                "analysis_run_id": analysis_run_id,
                "content": digest["content"],
                "grade_summary": {
                    payload["ticker"]: payload["grade"] for payload in position_payloads
                },
                "overall_grade": overall_grade,
                "overall_score": portfolio_score,
                "structured_sections": digest["sections"],
                "summary": digest["overall_summary"],
            }
        ).execute()

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
):
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    try:
        return await asyncio.wait_for(
            execute_analysis_run(
                user_id, analysis_run_id, triggered_by, target_position_id
            ),
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        run = (
            supabase.table("analysis_runs")
            .select("current_stage, current_stage_message")
            .eq("id", analysis_run_id)
            .limit(1)
            .execute()
            .data
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
):
    asyncio.run(
        _execute_with_timeout(
            user_id, analysis_run_id, triggered_by, target_position_id
        )
    )


async def execute_analysis_run(
    user_id: str,
    analysis_run_id: str,
    triggered_by: str,
    target_position_id: str | None = None,
):
    from ..services.polygon import fetch_aggs, store_prices, update_position_prices
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
    )

    supabase = get_supabase()

    if triggered_by == "scheduled":
        _record_scheduled_run_start(supabase, user_id)

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
        if target_position_id:
            positions_query = positions_query.eq("id", target_position_id)
        positions = positions_query.execute().data
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

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "refreshing_metadata",
            f"Refreshing ticker metadata for {len(tickers)} holdings.",
        )
        metadata_refresh_limit = max(1, min(4, len(tickers)))
        metadata_refresh_semaphore = asyncio.Semaphore(metadata_refresh_limit)

        async def _refresh_metadata(ticker: str) -> None:
            async with metadata_refresh_semaphore:
                await asyncio.to_thread(upsert_ticker_metadata, supabase, ticker)

        await asyncio.gather(*(_refresh_metadata(ticker) for ticker in tickers))

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

        sector_names = sorted(
            {
                str(metadata.get("sector", "")).strip()
                for metadata in ticker_metadata_map.values()
                if str(metadata.get("sector", "")).strip()
            }
        )

        macro_rss_task = asyncio.create_task(fetch_cnbc_macro_rss())
        sector_rss_task = asyncio.create_task(fetch_cnbc_sector_rss(sector_names))
        company_rss_task = asyncio.create_task(
            fetch_google_company_rss(tickers, ticker_metadata_map)
        )

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "fetching_news",
            (
                f"Fetching CNBC macro and sector news for {tickers[0]}."
                if len(tickers) == 1
                else f"Fetching CNBC macro and sector news for {len(tickers)} holdings."
            ),
        )
        macro_articles = await macro_rss_task
        sector_articles = await sector_rss_task
        company_articles = await company_rss_task
        sector_articles_by_name: dict[str, list[dict]] = {}
        for article in sector_articles:
            sector_name = (
                str(article.get("sector") or "unknown").strip().lower() or "unknown"
            )
            sector_articles_by_name.setdefault(sector_name, []).append(article)

        sector_context = {
            "sector_overview": [
                {
                    "sector": sector,
                    "brief": f"{len(articles)} CNBC sector headline(s) overnight.",
                    "headlines": [
                        a.get("title", "") for a in articles[:4] if a.get("title")
                    ],
                }
                for sector, articles in sorted(sector_articles_by_name.items())
            ],
        }
        raw_articles = []
        raw_articles.extend(normalize_news_batch(company_articles, "company_news"))
        raw_articles.extend(normalize_news_batch(macro_articles, "cnbc_macro_rss"))
        raw_articles.extend(normalize_news_batch(sector_articles, "cnbc_sector_rss"))
        raw_articles.extend(
            normalize_news_batch(await fetch_market_news(), "market_news")
        )
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

        BATCH_SIZE = 15
        all_batch_results = []
        normalized_copy = normalized_articles[:]

        for batch_start in range(0, len(normalized_copy), BATCH_SIZE):
            batch = normalized_copy[batch_start : batch_start + BATCH_SIZE]
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "classifying_relevance",
                f"Batch relevance check: articles {batch_start + 1}-{batch_start + len(batch)} of {len(normalized_copy)}.",
            )
            batch_results = await classify_relevance_batch(
                batch, positions, batch_size=BATCH_SIZE
            )
            all_batch_results.extend(batch_results)

        relevant_articles = []
        articles_by_ticker: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
        positions_by_ticker = {position["ticker"]: position for position in positions}

        held_tickers = {ticker.upper() for ticker in tickers}

        for result in all_batch_results:
            article = result.get("article") or normalized_copy[result["article_index"]]
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
            if article.get("source_type") == "company_news" and ticker_hints:
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
                }
                relevant_articles.append(article)
                _store_relevant_news_items(
                    supabase,
                    user_id=user_id,
                    analysis_run_id=analysis_run_id,
                    relevant_articles=[article],
                )
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
                }

        for ticker in tickers:
            articles_by_ticker[ticker] = _top_articles_for_position(
                articles_by_ticker.get(ticker, []),
                ticker,
            )

        prefs = (
            supabase.table("user_preferences")
            .select("apns_token, notifications_enabled")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
        )
        notifications_enabled = bool(prefs and prefs[0].get("notifications_enabled"))
        apns_token = prefs[0].get("apns_token") if prefs else None

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
                    max_age_hours=24,
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

        _set_analysis_stage(
            supabase,
            analysis_run_id,
            "analyzing_events",
            f"Analyzing events for {len(positions)} positions.",
            positions_processed=0,
            events_processed=0,
        )

        previous_grades_by_ticker = {}
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

        async def _process_position(
            position: dict, position_index: int
        ) -> tuple[int, dict, list[dict]]:
            ticker = position["ticker"]
            related_articles = all_events_by_ticker_for_analysis.get(ticker, [])
            inferred_labels = inferred_map.get(ticker, ["core"])

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

            for article in related_articles:
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
                minor_cache_key = f"{event_hash}:{ticker}"
                cached = _load_analysis_cache(
                    supabase,
                    kind="minor_event_analysis",
                    cache_key=minor_cache_key,
                    max_age_hours=18,
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
                from .agentic_scan import analyze_minor_events_batch

                batch_results = await analyze_minor_events_batch(
                    minor_uncached_articles, position, inferred_labels
                )
                result_idx = 0
                for item in minor_article_analysis_results:
                    if not item["cached"]:
                        item["analysis"] = batch_results[result_idx]
                        result_idx += 1
                        event_hash = item["article"].get("event_hash", "")
                        minor_cache_key = f"{event_hash}:{ticker}"
                        _store_analysis_cache(
                            supabase,
                            kind="minor_event_analysis",
                            cache_key=minor_cache_key,
                            payload=item["analysis"],
                        )

            mirofish_used = False
            major_uncached_articles = []
            major_article_analysis_results: list[dict] = []

            for article in major_articles:
                event_hash = article.get("event_hash", "")
                major_cache_key = f"{event_hash}:{ticker}"
                cached = _load_analysis_cache(
                    supabase,
                    kind="major_event_analysis",
                    cache_key=major_cache_key,
                    max_age_hours=24,
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
                from .mirofish_analyze import mirofish_analyze_batch

                batch_results = await mirofish_analyze_batch(
                    major_uncached_articles,
                    {**position, "inferred_labels": inferred_labels},
                )
                result_idx = 0
                for item in major_article_analysis_results:
                    if not item["cached"]:
                        item["analysis"] = batch_results[result_idx]
                        result_idx += 1
                        event_hash = item["article"].get("event_hash", "")
                        major_cache_key = f"{event_hash}:{ticker}"
                        _store_analysis_cache(
                            supabase,
                            kind="major_event_analysis",
                            cache_key=major_cache_key,
                            payload=item["analysis"],
                        )

            event_analyses = []
            for item in minor_article_analysis_results:
                article = item["article"]
                result = item["analysis"]
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
                result = item["analysis"]
                event_hash = article.get("event_hash", "")
                significance = significance_by_hash.get(event_hash, {})
                analysis_source = (
                    result.get("provider", "mirofish") if result else "mirofish"
                )
                if analysis_source == "mirofish":
                    mirofish_used = True
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
                    },
                    dedupe_event_hash=event_hash,
                )
                if created and notifications_enabled and apns_token:
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

            from .position_report_builder import build_position_report

            position_report = await build_position_report(
                position,
                inferred_labels,
                event_analyses,
                macro_context=macro_context,
            )

            mirofish_used = mirofish_used or any(
                e.get("analysis_source") == "mirofish" for e in event_analyses
            )

            position_payload = {
                **position,
                "previous_grade": previous_grades_by_ticker.get(ticker),
                "summary": position_report["summary"],
                "long_report": position_report["long_report"],
                "top_risks": position_report["top_risks"],
                "watch_items": position_report["watch_items"],
                "top_news": top_headlines,
                "inferred_labels": inferred_labels,
                "methodology": position_report["methodology"],
                "mirofish_used": mirofish_used,
                "thesis_verifier": position_report.get("thesis_verifier", []),
            }
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
            from .risk_scorer import score_positions_batch

            batch_risk_scores = await score_positions_batch(position_payloads)
            for i, scores in enumerate(batch_risk_scores):
                if i < len(position_payloads):
                    position_payloads[i].update(scores)

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
                    "factor_breakdown": structural_scores.get("factor_breakdown"),
                    "grade": grade,
                    "reasoning": ai_scores.get("reasoning"),
                    "grade_reason": ai_scores.get("grade_reason"),
                    "evidence_summary": ai_scores.get("evidence_summary"),
                    "dimension_rationale": ai_scores.get("dimension_rationale"),
                    "mirofish_used": ai_scores.get(
                        "mirofish_used", structural_scores.get("mirofish_used", False)
                    ),
                }
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
                    alert_payload = {
                        "user_id": user_id,
                        "position_ticker": ticker,
                        "type": "grade_change",
                        "previous_grade": previous_grade,
                        "new_grade": grade,
                        "message": f"{ticker} grade changed from {previous_grade} to {grade}",
                        "analysis_run_id": analysis_run_id,
                    }
                    supabase.table("alerts").insert(alert_payload).execute()
                    if notifications_enabled and apns_token:
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
                else "Refreshing price history for analyzed holdings."
            ),
            positions_processed=len(position_payloads),
            events_processed=total_event_count,
        )
        await asyncio.to_thread(update_position_prices, positions)

        for position in positions:
            ticker = position["ticker"]
            aggs = await asyncio.to_thread(fetch_aggs, ticker, 30)
            if aggs:
                store_prices(ticker, aggs)

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
        if not target_position_id:
            _set_analysis_stage(
                supabase,
                analysis_run_id,
                "building_digest",
                "Building your morning digest.",
                positions_processed=len(position_payloads),
                events_processed=total_event_count,
            )
            portfolio_score, overall_grade = _compute_portfolio_grade(position_payloads)
            digest = await compile_portfolio_digest(
                position_payloads,
                overall_grade,
                portfolio_risk,
                macro_context=macro_context,
                sector_context=sector_context,
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
                    },
                )
                if created and notifications_enabled and apns_token:
                    await notify_portfolio_grade_change(
                        user_id,
                        apns_token,
                        previous_portfolio_grade,
                        overall_grade,
                    )

            previous_scores_for_alerts = {}
            for p in positions:
                prev_result = (
                    supabase.table("risk_scores")
                    .select("safety_score")
                    .eq("position_id", p["id"])
                    .order("calculated_at", desc=True)
                    .limit(2)
                    .execute()
                    .data
                )
                if len(prev_result) >= 2:
                    previous_scores_for_alerts[p["id"]] = prev_result[1].get(
                        "safety_score"
                    )

            for p in positions:
                ticker = p["ticker"]
                position_id = p["id"]
                current_score = p.get("safety_score")
                if not current_score:
                    continue
                previous_score = previous_scores_for_alerts.get(position_id)
                if previous_score is not None and current_score < previous_score - 10:
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
                        },
                        dedupe_hours=12,
                    )

            if portfolio_risk:
                risk_score = portfolio_risk.get("portfolio_allocation_risk_score", 0)
                concentration = portfolio_risk.get("concentration_risk", 0)
                if concentration > 50:
                    created = await _maybe_create_alert(
                        supabase,
                        {
                            "user_id": user_id,
                            "type": "concentration_danger",
                            "message": f"Portfolio concentration risk elevated at {concentration}/100",
                            "analysis_run_id": analysis_run_id,
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

            if notifications_enabled and apns_token:
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
        if triggered_by == "scheduled":
            _record_scheduled_run_result(supabase, user_id, status="completed")
        return digest_alert_created
    except Exception as exc:
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
        raise
    finally:
        active_runs.pop(analysis_run_id, None)


async def enqueue_analysis_run(
    user_id: str,
    triggered_by: str = "manual",
    target_position_id: str | None = None,
) -> dict:
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    _fail_stale_runs(supabase)
    _fail_orphaned_runs(supabase)

    existing = (
        supabase.table("analysis_runs")
        .select("id, status, started_at, target_position_id")
        .eq("user_id", user_id)
        .in_("status", ["queued", "running"])
        .order("started_at", desc=True)
        .execute()
        .data
    )
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

    run = await create_analysis_run(user_id, triggered_by, target_position_id)
    task = asyncio.create_task(
        asyncio.to_thread(
            _run_analysis_in_thread,
            user_id,
            run["id"],
            triggered_by,
            target_position_id,
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
    return await enqueue_analysis_run(user_id, "scheduled")


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

    for position in positions:
        ticker = position.get("ticker")
        if not ticker:
            continue

        upsert_ticker_metadata(supabase, ticker)

        meta_result = (
            supabase.table("ticker_metadata")
            .select("*")
            .eq("ticker", ticker.upper())
            .limit(1)
            .execute()
        )

        if not meta_result.data:
            continue

        metadata = meta_result.data[0]

        previous_score_result = (
            supabase.table("asset_safety_profiles")
            .select("safety_score")
            .eq("ticker", ticker.upper())
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

        existing = (
            supabase.table("asset_safety_profiles")
            .select("id")
            .eq("ticker", ticker.upper())
            .eq("as_of_date", today.isoformat())
            .limit(1)
            .execute()
            .data
        )

        profile_payload = {
            "ticker": ticker.upper(),
            "as_of_date": today.isoformat(),
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

        if existing:
            supabase.table("asset_safety_profiles").update(profile_payload).eq(
                "id", existing[0]["id"]
            ).execute()
        else:
            supabase.table("asset_safety_profiles").insert(profile_payload).execute()

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
        "runtime_next_run_at": _serialize_datetime(job.next_run_time if job else None),
        "persisted_state": state,
    }


def start_scheduler():
    from ..services.supabase import get_supabase

    supabase = get_supabase()
    _fail_stale_runs(supabase)
    _fail_orphaned_runs(supabase)

    if not scheduler.running:
        scheduler.start()

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
