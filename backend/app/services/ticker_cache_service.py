from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from ..pipeline.risk_scorer import score_position_structural, score_to_grade
from ..pipeline.analysis_utils import sanitize_public_analysis_text
from .alert_payloads import enrich_alert_rows
from .ticker_metadata import upsert_ticker_metadata


logger = logging.getLogger(__name__)


SYSTEM_SP500_USER_ID = "00000000-0000-0000-0000-000000000001"


SP500_UNIVERSE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "sp500_universe.txt"
)


@lru_cache(maxsize=1)
def load_sp500_seed_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(SP500_UNIVERSE_PATH.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        ticker, company_name, sector, industry = line.split("|", maxsplit=3)
        rows.append(
            {
                "ticker": ticker.upper(),
                "company_name": company_name,
                "sector": sector,
                "industry": industry,
                "index_membership": "SP500",
                "is_active": True,
                "priority_rank": index,
            }
        )
    return rows


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _chunked(values: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def ensure_sp500_universe_seeded(supabase) -> None:
    existing = (
        supabase.table("ticker_universe")
        .select("ticker")
        .eq("index_membership", "SP500")
        .execute()
        .data
        or []
    )
    existing_tickers = {row["ticker"] for row in existing}
    missing = [
        row for row in load_sp500_seed_rows() if row["ticker"] not in existing_tickers
    ]
    for chunk in _chunked(missing, 100):
        supabase.table("ticker_universe").insert(chunk).execute()


def list_active_sp500_tickers(supabase, limit: int | None = None) -> list[str]:
    ensure_sp500_universe_seeded(supabase)
    result = (
        supabase.table("ticker_universe")
        .select("ticker")
        .eq("index_membership", "SP500")
        .eq("is_active", True)
        .order("priority_rank")
        .execute()
    )
    tickers = [row["ticker"] for row in (result.data or [])]
    if limit is not None:
        return tickers[:limit]
    return tickers


def _universe_sort_key(row: dict[str, Any], term: str) -> tuple:
    ticker = (row.get("ticker") or "").upper()
    company_name = (row.get("company_name") or "").upper()
    membership = (row.get("index_membership") or "").upper()
    priority_rank = row.get("priority_rank")
    return (
        0 if ticker == term else 1,
        0 if ticker.startswith(term) else 1,
        0 if term and term in company_name else 1,
        0 if membership == "SP500" else 1,
        priority_rank if priority_rank is not None else 999999,
        ticker,
    )


def ensure_ticker_in_universe(supabase, ticker: str) -> dict | None:
    normalized = (ticker or "").strip().upper()
    if not normalized:
        return None

    existing = get_supported_ticker(supabase, normalized)
    if existing:
        return existing

    metadata = upsert_ticker_metadata(supabase, normalized)
    if not metadata:
        return None

    payload = {
        "ticker": normalized,
        "company_name": metadata.get("company_name") or normalized,
        "exchange": metadata.get("exchange"),
        "sector": metadata.get("sector"),
        "industry": metadata.get("industry"),
        "index_membership": "USER_SHARED",
        "is_active": True,
        "priority_rank": None,
        "updated_at": _utcnow_iso(),
    }
    supabase.table("ticker_universe").insert(payload).execute()
    return get_supported_ticker(supabase, normalized)


def get_supported_ticker(supabase, ticker: str) -> dict | None:
    ensure_sp500_universe_seeded(supabase)
    result = (
        supabase.table("ticker_universe")
        .select("*")
        .eq("ticker", ticker.upper())
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def require_supported_ticker(supabase, ticker: str) -> dict:
    supported = get_supported_ticker(supabase, ticker)
    if not supported:
        raise HTTPException(400, "Ticker is not available in the shared ticker cache")
    return supported


def search_supported_tickers(
    supabase, query: str | None, limit: int = 20
) -> list[dict[str, Any]]:
    ensure_sp500_universe_seeded(supabase)
    universe = (
        supabase.table("ticker_universe")
        .select("ticker, company_name, exchange, sector, industry, priority_rank")
        .eq("is_active", True)
        .execute()
        .data
        or []
    )

    term = (query or "").strip().upper()
    if term:
        filtered = [
            row
            for row in universe
            if term in (row.get("ticker") or "").upper()
            or term in (row.get("company_name") or "").upper()
        ]
    else:
        filtered = universe

    filtered.sort(key=lambda row: _universe_sort_key(row, term))

    selected = filtered[:limit]
    tickers = [row["ticker"] for row in selected]
    metadata_map = get_metadata_map(supabase, tickers)
    snapshot_map = get_latest_risk_snapshot_map(supabase, tickers)

    results = []
    for row in selected:
        ticker = row["ticker"]
        metadata = metadata_map.get(ticker, {})
        snapshot = snapshot_map.get(ticker, {})
        results.append(
            {
                **row,
                "price": metadata.get("price"),
                "price_as_of": metadata.get("price_as_of"),
                "grade": snapshot.get("grade"),
                "safety_score": snapshot.get("safety_score"),
                "analysis_as_of": snapshot.get("analysis_as_of"),
                "summary": snapshot.get("news_summary") or snapshot.get("reasoning"),
                "is_supported": True,
            }
        )
    return results


def get_metadata_map(supabase, tickers: list[str]) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    result = (
        supabase.table("ticker_metadata")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .execute()
    )
    return {row["ticker"]: row for row in (result.data or [])}


def get_latest_risk_snapshot_history_map(
    supabase, tickers: list[str], per_ticker: int = 2
) -> dict[str, list[dict[str, Any]]]:
    if not tickers:
        return {}
    result = (
        supabase.table("ticker_risk_snapshots")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .order("analysis_as_of", desc=True)
        .execute()
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result.data or []:
        ticker = row["ticker"]
        if len(grouped[ticker]) < per_ticker:
            grouped[ticker].append(row)
    return grouped


def get_latest_risk_snapshot_map(
    supabase, tickers: list[str]
) -> dict[str, dict[str, Any]]:
    history = get_latest_risk_snapshot_history_map(supabase, tickers, per_ticker=1)
    return {ticker: rows[0] for ticker, rows in history.items() if rows}


def enrich_positions_with_ticker_cache(
    positions: list[dict[str, Any]], supabase
) -> list[dict[str, Any]]:
    positions = positions or []
    tickers = [
        position.get("ticker", "").upper()
        for position in positions
        if position.get("ticker")
    ]
    metadata_map = get_metadata_map(supabase, tickers)
    history_map = get_latest_risk_snapshot_history_map(supabase, tickers, per_ticker=2)
    analysis_run_map = get_latest_analysis_run_map_for_ids(
        supabase,
        [position.get("id", "") for position in positions if position.get("id")],
    )
    score_map = _get_latest_position_score_map_for_ids(
        supabase,
        [position.get("id", "") for position in positions if position.get("id")],
    )
    refresh_job_map = get_latest_refresh_job_map(supabase, tickers)
    news_cache_map = get_latest_news_cache_map(supabase, tickers)

    for position in positions:
        ticker = (position.get("ticker") or "").upper()
        metadata = metadata_map.get(ticker, {})
        snapshots = history_map.get(ticker, [])
        latest = snapshots[0] if snapshots else {}
        previous = snapshots[1] if len(snapshots) > 1 else {}
        latest_analysis_run = analysis_run_map.get(position.get("id"), {})
        latest_position_score = score_map.get(position.get("id"), {})
        latest_refresh_job = refresh_job_map.get(ticker, {})
        latest_news_row = news_cache_map.get(ticker, {})
        current_score = build_risk_score_response(
            latest,
            position_id=position.get("id", ""),
            latest_position_score=latest_position_score,
            include_position_sizing=True,
            coverage_context={
                "coverage_state": latest.get("coverage_state"),
                "coverage_note": latest.get("coverage_note"),
            },
        )
        analysis_state = _analysis_state_from_context(
            snapshot=latest,
            latest_position_analysis=None,
            latest_analysis_run=latest_analysis_run,
            latest_refresh_job=latest_refresh_job,
            metadata=metadata,
            current_score=current_score,
            latest_news_row=latest_news_row,
        )

        if position.get("current_price") is None:
            position["current_price"] = metadata.get("price")

        score = current_score or {}
        position["risk_grade"] = score.get("grade") or latest.get("grade")
        position["total_score"] = score.get("total_score") or latest.get("safety_score")
        position["last_analyzed_at"] = score.get("score_as_of") or latest.get(
            "analysis_as_of"
        )
        position["previous_grade"] = previous.get("grade")
        position["inferred_labels"] = None
        position["summary"] = (
            score.get("reasoning")
            or latest.get("news_summary")
            or latest.get("reasoning")
        )
        position["dimension_breakdown"] = (
            score.get("factor_breakdown") or latest.get("dimension_rationale") or {}
        )
        position["analysis_state"] = analysis_state.get("status")
        position["coverage_state"] = analysis_state.get("coverage_state")
        position["coverage_note"] = analysis_state.get("coverage_note")
        position["analysis_run_id"] = analysis_state.get("latest_analysis_run_id")
        position["latest_analysis_run_status"] = latest_analysis_run.get("status")
        position["latest_refresh_job_id"] = latest_refresh_job.get("id")
        position["latest_refresh_job_status"] = latest_refresh_job.get("status")
        position["analysis_as_of"] = analysis_state.get("analysis_as_of")
        position["score_source"] = score.get("score_source")
        position["score_as_of"] = score.get("score_as_of")
        position["score_version"] = score.get("score_version")
        position["last_news_refresh_at"] = analysis_state.get("last_news_refresh_at")
        position["price_as_of"] = analysis_state.get("price_as_of")
        position["news_as_of"] = analysis_state.get("news_as_of")
        position["news_refresh_status"] = analysis_state.get("news_refresh_status")
        position["source"] = analysis_state.get("source")

    return positions


def _news_rows_to_response(
    news_rows: list[dict[str, Any]], *, user_id: str, ticker: str
) -> list[dict[str, Any]]:
    responses = []
    for row in news_rows:
        responses.append(
            {
                "id": row.get("id"),
                "user_id": user_id,
                "ticker": ticker,
                "title": row.get("headline"),
                "summary": row.get("summary"),
                "source": row.get("source"),
                "url": row.get("url"),
                "significance": row.get("sentiment"),
                "published_at": row.get("published_at"),
                "affected_tickers": [ticker],
                "processed_at": row.get("processed_at"),
            }
        )
    return responses


def _news_row_to_cache_payload(row: dict[str, Any], ticker: str) -> dict[str, Any]:
    headline = row.get("headline") or row.get("title") or ""
    summary = row.get("summary") or row.get("body") or row.get("headline") or ""
    sentiment = row.get("sentiment") or row.get("significance")
    return {
        "ticker": ticker,
        "headline": headline,
        "summary": summary,
        "source": row.get("source") or "",
        "url": row.get("url") or "",
        "sentiment": sentiment,
        "published_at": row.get("published_at"),
        "processed_at": row.get("processed_at") or _utcnow_iso(),
    }


def sync_ticker_news_cache(
    supabase,
    *,
    ticker: str,
    news_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_ticker = (ticker or "").strip().upper()
    if not normalized_ticker:
        return {"ticker": normalized_ticker, "status": "skipped", "count": 0}

    deduped_rows: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in news_rows or []:
        key = str(
            row.get("event_hash") or row.get("url") or row.get("headline") or ""
        ).strip()
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_rows.append(row)

    deduped_rows.sort(
        key=lambda row: row.get("published_at") or row.get("processed_at") or "",
        reverse=True,
    )

    cache_rows = [
        _news_row_to_cache_payload(row, normalized_ticker) for row in deduped_rows[:10]
    ]

    delete_query = (
        supabase.table("ticker_news_cache").delete().eq("ticker", normalized_ticker)
    )
    if cache_rows:
        latest_processed_at = max(row.get("processed_at") or "" for row in cache_rows)
        if latest_processed_at:
            delete_query = delete_query.lt("processed_at", latest_processed_at)
    delete_query.execute()
    if cache_rows:
        supabase.table("ticker_news_cache").insert(cache_rows).execute()

    last_news_refresh_at = None
    if cache_rows:
        last_news_refresh_at = max(
            row.get("processed_at") for row in cache_rows if row.get("processed_at")
        )

    if deduped_rows and not cache_rows:
        logger.warning(
            "[NEWS_CACHE] ticker=%s mirrored 0/%s rows from news_items",
            normalized_ticker,
            len(deduped_rows),
        )
    else:
        logger.info(
            "[NEWS_CACHE] ticker=%s mirrored %s/%s rows from news_items",
            normalized_ticker,
            len(cache_rows),
            len(deduped_rows),
        )

    return {
        "ticker": normalized_ticker,
        "status": "completed" if cache_rows else "empty",
        "count": len(cache_rows),
        "last_news_refresh_at": last_news_refresh_at,
    }


def build_position_analysis_from_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    position_id: str,
    ticker: str,
) -> dict[str, Any] | None:
    if not snapshot:
        return None
    summary = snapshot.get("news_summary") or snapshot.get("reasoning")
    watch_items = []
    if snapshot.get("event_adjustment") not in (None, 0, 0.0):
        watch_items.append(
            "Recent events are contributing to the shared ticker risk read."
        )
    if snapshot.get("macro_adjustment") not in (None, 0, 0.0):
        watch_items.append(
            "Macro conditions are affecting the current shared ticker snapshot."
        )
    return sanitize_public_analysis_text(
        {
            "id": None,
            "analysis_run_id": None,
            "position_id": position_id,
            "ticker": ticker,
            "summary": summary,
            "methodology": "Shared S&P ticker cache using canonical structural scoring and the latest cached ticker snapshot.",
            "top_risks": [],
            "watch_items": watch_items,
            "top_news": [],
            "major_event_count": 0,
            "minor_event_count": 0,
            "status": "ready",
            "progress_message": "Shared ticker cache is ready.",
            "source_count": snapshot.get("source_count") or 0,
            "updated_at": snapshot.get("analysis_as_of"),
        }
    )


_LEGACY_DIMENSION_MATH_MARKERS = (
    "adds risk at ",
    "supports a safer read at ",
    "is broadly neutral at ",
    "Those inputs land the score at ",
    "Company-specific news (",
    "Macro/sector exposure (",
    "Near-term volatility (",
    "Portfolio construction (",
    "This summary was assembled from the final dimension scores",
    "Low-confidence coverage: only",
    "analyzed event(s) were available",
    "analyzed event(s) supported this score",
)


def _is_legacy_dimension_math(text: str) -> bool:
    return any(marker in text for marker in _LEGACY_DIMENSION_MATH_MARKERS)


_GENERIC_FALLBACK_MARKERS = (
    "We're still building a full picture for this ticker.",
    "Risk is based on",
    "Risk reflects recent news coverage and sector conditions.",
    "The score reflects underlying fundamentals and sector context",
)


def _is_generic_fallback_reasoning(text: str) -> bool:
    """Detect our own generic fallback template text (not article-specific)."""
    return any(marker in text for marker in _GENERIC_FALLBACK_MARKERS)


def _normalize_headline(title: str) -> str:
    """Normalize a headline for dedup: lowercase, strip source suffixes, remove punctuation."""
    import re

    t = (title or "").lower().strip()
    # Strip trailing source attribution: " - Reuters", " | CNBC", " — Bloomberg"
    t = re.sub(r"\s*[-|—]\s*[A-Za-z][\w\s.,&'-]{1,40}$", "", t).strip()
    # Remove all non-alphanumeric chars except spaces
    t = re.sub(r"[^a-z0-9\s]", "", t).strip()
    # Collapse whitespace
    return re.sub(r"\s+", " ", t)


def _dedup_event_analyses(events: list[dict]) -> list[dict]:
    """
    Deduplicate event_analyses rows.
    Priority: highest confidence first, then most recent.
    Dedup key: event_hash, then normalized headline.
    """
    sorted_events = sorted(
        events,
        key=lambda e: (
            float(e.get("confidence") or 0),
            e.get("created_at") or "",
        ),
        reverse=True,
    )
    seen_hashes: set[str] = set()
    seen_titles: set[str] = set()
    result: list[dict] = []
    for event in sorted_events:
        h = (event.get("event_hash") or "").strip()
        norm = _normalize_headline(event.get("title") or "")
        if h and h in seen_hashes:
            continue
        if norm and norm in seen_titles:
            continue
        if h:
            seen_hashes.add(h)
        if norm:
            seen_titles.add(norm)
        result.append(event)
    return result


def _build_article_aware_reasoning(
    events: list[dict],
    current_score: dict | None,
    ticker: str,
) -> str | None:
    """
    Build investor-facing rationale using actual event analyses.
    Covers: overall tone, downside signals, supportive signals, macro context, watch item.
    Returns None if there are no events to build from.
    """
    if not events:
        return None

    score = current_score or {}
    source_count = int(score.get("source_count") or len(events))
    macro_score = int(score.get("macro_exposure") or 50)
    coverage_state = score.get("coverage_state") or "substantive"

    worsening = [
        e for e in events if (e.get("risk_direction") or "").lower() == "worsening"
    ]
    improving = [
        e for e in events if (e.get("risk_direction") or "").lower() == "improving"
    ]

    # Overall tone
    if len(worsening) > 0 and len(improving) == 0:
        tone = "broadly cautious"
    elif len(improving) > 0 and len(worsening) == 0:
        tone = "broadly positive"
    elif len(worsening) == 0 and len(improving) == 0:
        tone = "broadly neutral"
    elif len(worsening) > len(improving):
        tone = "mixed, leaning cautious"
    elif len(improving) > len(worsening):
        tone = "mixed, leaning positive"
    else:
        tone = "mixed"

    word = "source" if source_count == 1 else "sources"
    lines: list[str] = [f"Recent coverage across {source_count} {word} is {tone}."]

    def _title_clip(event: dict) -> str:
        title = (event.get("title") or ticker).strip()
        for sep in (" - ", " | ", " — ", ": "):
            if sep in title:
                title = title.split(sep)[0].strip()
        return title[:80]  # guard against very long titles

    def _best_detail(event: dict) -> str:
        implications = event.get("key_implications") or []
        if implications and implications[0]:
            return str(implications[0]).strip()
        return (event.get("scenario_summary") or "").strip()

    def _sentence_case(text: str) -> str:
        if not text:
            return text
        return text[0].lower() + text[1:]

    # Downside signals
    if worsening:
        parts = []
        for e in worsening[:2]:
            detail = _best_detail(e)
            clip = _title_clip(e)
            if detail:
                parts.append(f"{clip}: {_sentence_case(detail).rstrip('.')}")
        if parts:
            lines.append("Downside signals: " + "; ".join(parts) + ".")

    # Supportive signals
    if improving:
        parts = []
        for e in improving[:2]:
            detail = _best_detail(e)
            clip = _title_clip(e)
            if detail:
                parts.append(f"{clip}: {_sentence_case(detail).rstrip('.')}")
        if parts:
            lines.append("On the positive side: " + "; ".join(parts) + ".")

    # Macro context
    if macro_score <= 35:
        lines.append(
            "Macro and sector conditions are elevated risk — that weighs on the overall score."
        )
    elif macro_score >= 65:
        lines.append("Macro and sector conditions are broadly supportive.")

    # Watch item: second implication from the most significant worsening or improving event
    watch_text: str | None = None
    candidates = worsening + improving
    for e in candidates:
        implications = e.get("key_implications") or []
        if len(implications) > 1 and implications[1]:
            watch_text = str(implications[1]).strip()
            break
    if watch_text:
        lines.append(f"Watch: {watch_text.rstrip('.')}.")

    # Coverage caveat
    if coverage_state == "provisional":
        lines.append(
            "Score is based mostly on fundamentals — more recent news will sharpen this read."
        )
    elif coverage_state == "thin":
        lines.append(
            "Coverage is still building; watch for new earnings or analyst updates."
        )

    return " ".join(lines)


def _investor_coverage_note(coverage_state: str, source_count: Any) -> str:
    sc = int(source_count or 0)
    word = "source" if sc == 1 else "sources"
    if coverage_state == "provisional":
        return "Score based on fundamentals — limited recent news available."
    if coverage_state == "thin":
        return f"Limited coverage: {sc} recent {word} reviewed."
    return f"{sc} recent {word} reviewed."


def _investor_fallback_reasoning(coverage_state: str, source_count: Any) -> str:
    sc = int(source_count or 0)
    word = "source" if sc == 1 else "sources"
    if coverage_state == "provisional":
        return (
            "We're still building a full picture for this ticker. "
            "The score reflects underlying fundamentals and sector context — "
            "it will sharpen as we collect more recent news."
        )
    if coverage_state == "thin":
        return (
            f"Risk is based on {sc} recent {word} plus ticker fundamentals. "
            "Coverage is limited right now — watch for earnings updates, "
            "analyst notes, or macro shifts that could move the score."
        )
    return (
        "Risk reflects recent news coverage and sector conditions. "
        "Monitor for changes in company guidance, macro data, or portfolio concentration."
    )


def build_risk_score_response(
    snapshot: dict[str, Any] | None,
    *,
    position_id: str,
    latest_position_score: dict[str, Any] | None = None,
    include_position_sizing: bool = True,
    coverage_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not snapshot and not latest_position_score:
        return None
    snapshot = snapshot or {}
    fallback = latest_position_score or {}
    coverage_context = coverage_context or {}
    factor_breakdown = fallback.get("factor_breakdown") or snapshot.get(
        "factor_breakdown"
    )
    if isinstance(factor_breakdown, str):
        import json

        try:
            factor_breakdown = json.loads(factor_breakdown)
        except Exception:
            factor_breakdown = {}
    ai_dims = (factor_breakdown or {}).get("ai_dimensions") or {}
    if not include_position_sizing and isinstance(factor_breakdown, dict):
        factor_breakdown = {
            **factor_breakdown,
            "ai_dimensions": {
                **ai_dims,
                "position_sizing": None,
            },
        }
        ai_dims = factor_breakdown.get("ai_dimensions") or {}

    def _first_present(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    source_count = _first_present(
        fallback.get("source_count"),
        coverage_context.get("source_count"),
        snapshot.get("source_count"),
    )
    major_event_count = _first_present(
        fallback.get("major_event_count"),
        coverage_context.get("major_event_count"),
    )
    minor_event_count = _first_present(
        fallback.get("minor_event_count"),
        coverage_context.get("minor_event_count"),
    )
    coverage_state = (
        fallback.get("coverage_state")
        or coverage_context.get("coverage_state")
        or (
            "provisional"
            if not source_count
            else "thin"
            if int(source_count) <= 2
            else "substantive"
        )
    )
    coverage_note = (
        fallback.get("coverage_note")
        or coverage_context.get("coverage_note")
        or _investor_coverage_note(coverage_state, source_count)
    )
    is_provisional = bool(
        fallback.get("is_provisional")
        or coverage_context.get("is_provisional")
        or coverage_state != "substantive"
    )
    reasoning = fallback.get("reasoning") or snapshot.get("reasoning")
    if reasoning and _is_legacy_dimension_math(reasoning):
        reasoning = None
    if not reasoning:
        reasoning = _investor_fallback_reasoning(coverage_state, source_count)
    return sanitize_public_analysis_text(
        {
            "id": snapshot.get("id"),
            "position_id": position_id,
            "score_source": "user" if fallback else "shared",
            "score_as_of": fallback.get("calculated_at")
            or snapshot.get("analysis_as_of"),
            "score_version": fallback.get("analysis_run_id")
            or snapshot.get("methodology_version")
            or snapshot.get("snapshot_date"),
            "safety_score": fallback.get("safety_score")
            or fallback.get("total_score")
            or snapshot.get("safety_score"),
            "confidence": fallback.get("confidence") or snapshot.get("confidence"),
            "structural_base_score": fallback.get("structural_base_score")
            or snapshot.get("structural_base_score"),
            "macro_adjustment": fallback.get("macro_adjustment")
            or snapshot.get("macro_adjustment"),
            "event_adjustment": fallback.get("event_adjustment")
            or snapshot.get("event_adjustment"),
            "grade": fallback.get("grade") or snapshot.get("grade"),
            "reasoning": reasoning,
            "factor_breakdown": factor_breakdown,
            "mirofish_used": False,
            "calculated_at": fallback.get("calculated_at")
            or snapshot.get("analysis_as_of"),
            "total_score": fallback.get("total_score")
            or fallback.get("safety_score")
            or snapshot.get("safety_score"),
            "news_sentiment": fallback.get("news_sentiment")
            or ai_dims.get("news_sentiment"),
            "macro_exposure": fallback.get("macro_exposure")
            or ai_dims.get("macro_exposure"),
            "position_sizing": (
                fallback.get("position_sizing") or ai_dims.get("position_sizing")
            )
            if include_position_sizing
            else None,
            "volatility_trend": fallback.get("volatility_trend")
            or ai_dims.get("volatility_trend"),
            "source_count": source_count,
            "major_event_count": major_event_count,
            "minor_event_count": minor_event_count,
            "coverage_state": coverage_state,
            "coverage_note": coverage_note,
            "is_provisional": is_provisional,
        }
    )


def _build_virtual_position(
    *,
    user_id: str,
    ticker: str,
    metadata: dict[str, Any],
    snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    now_iso = _utcnow_iso()
    return {
        "id": f"virtual:{ticker}",
        "user_id": user_id,
        "ticker": ticker,
        "shares": 0.0,
        "purchase_price": metadata.get("price") or 0.0,
        "archetype": "growth",
        "created_at": now_iso,
        "updated_at": now_iso,
        "current_price": metadata.get("price"),
        "risk_grade": snapshot.get("grade") if snapshot else None,
        "total_score": snapshot.get("safety_score") if snapshot else None,
        "previous_grade": previous_snapshot.get("grade") if previous_snapshot else None,
        "inferred_labels": None,
        "summary": (snapshot or {}).get("news_summary")
        or (snapshot or {}).get("reasoning"),
        "last_analyzed_at": (snapshot or {}).get("analysis_as_of"),
        "analysis_started_at": None,
    }


def _build_event_analyses_from_news_rows(
    news_rows: list[dict[str, Any]], *, ticker: str, position_id: str
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for row in news_rows[:10]:
        sentiment = (row.get("sentiment") or "neutral").lower()
        if sentiment in {"negative", "bearish"}:
            significance = "major"
            risk_direction = "negative"
        elif sentiment in {"positive", "bullish"}:
            significance = "minor"
            risk_direction = "positive"
        else:
            significance = "minor"
            risk_direction = "neutral"

        summary = row.get("summary") or row.get("headline") or ""
        events.append(
            {
                "id": row.get("id") or str(uuid4()),
                "analysis_run_id": None,
                "position_id": position_id,
                "event_hash": None,
                "title": row.get("headline") or ticker,
                "summary": summary,
                "source": row.get("source"),
                "source_url": row.get("url"),
                "published_at": row.get("published_at"),
                "event_type": row.get("event_type") or "news",
                "significance": significance,
                "analysis_source": "ticker_cache",
                "long_analysis": summary,
                "confidence": 0.45,
                "impact_horizon": "near_term",
                "risk_direction": risk_direction,
                "scenario_summary": summary,
                "key_implications": [],
                "recommended_followups": [],
            }
        )
    return events


def _get_latest_position_score_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    if not position_ids:
        return None
    result = (
        supabase.table("risk_scores")
        .select("*")
        .in_("position_id", position_ids)
        .order("calculated_at", desc=True)
        .limit(10)
        .execute()
    )
    rows = result.data or []
    for row in rows:
        if row.get("position_id") in position_ids:
            return row
    return None


def _get_latest_position_score_map_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not position_ids:
        return {}
    result = (
        supabase.table("risk_scores")
        .select("*")
        .in_("position_id", position_ids)
        .order("calculated_at", desc=True)
        .execute()
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        position_id = row.get("position_id")
        if position_id and position_id not in grouped:
            grouped[position_id] = row
    return grouped


def _get_latest_position_analysis_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    if not position_ids:
        return None
    result = (
        supabase.table("position_analyses")
        .select("*")
        .in_("position_id", position_ids)
        .order("updated_at", desc=True)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    rows = result.data or []
    for row in rows:
        if row.get("position_id") in position_ids:
            return row
    return None


def _get_latest_analysis_run_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    if not position_ids:
        return None

    result = (
        supabase.table("analysis_runs")
        .select("*")
        .in_("target_position_id", position_ids)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None

    active_rows = [
        row for row in rows if row.get("status") in {"queued", "starting", "running"}
    ]
    candidate_rows = active_rows or rows
    return max(
        candidate_rows,
        key=lambda row: (
            row.get("updated_at")
            or row.get("started_at")
            or row.get("created_at")
            or "",
            row.get("id") or "",
        ),
    )


def _get_latest_analysis_run_legacy_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, Any] | None:
    latest_position_analysis = _get_latest_position_analysis_for_ids(
        supabase, position_ids
    )
    if not latest_position_analysis:
        return None

    analysis_run_id = latest_position_analysis.get("analysis_run_id")
    if not analysis_run_id:
        return None

    result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("id", analysis_run_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_latest_analysis_run_map_for_ids(
    supabase, position_ids: list[str]
) -> dict[str, dict[str, Any]]:
    if not position_ids:
        return {}
    result = (
        supabase.table("analysis_runs")
        .select("*")
        .in_("target_position_id", position_ids)
        .order("started_at", desc=True)
        .execute()
    )
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result.data or []:
        position_id = row.get("target_position_id")
        if position_id:
            grouped_rows[position_id].append(row)

    grouped: dict[str, dict[str, Any]] = {}
    for position_id, rows in grouped_rows.items():
        active_rows = [
            row
            for row in rows
            if row.get("status") in {"queued", "starting", "running"}
        ]
        candidate_rows = active_rows or rows
        grouped[position_id] = max(
            candidate_rows,
            key=lambda row: (
                row.get("updated_at")
                or row.get("started_at")
                or row.get("created_at")
                or "",
                row.get("id") or "",
            ),
        )
    for position_id in position_ids:
        if position_id not in grouped:
            legacy_run = _get_latest_analysis_run_legacy_for_ids(
                supabase, [position_id]
            )
            if legacy_run:
                grouped[position_id] = legacy_run
    return grouped


def get_latest_refresh_job_map(
    supabase, tickers: list[str]
) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    result = (
        supabase.table("ticker_refresh_jobs")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .order("created_at", desc=True)
        .execute()
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        ticker = row.get("ticker")
        if ticker and ticker not in grouped:
            grouped[ticker] = row
    return grouped


def get_latest_news_cache_map(
    supabase, tickers: list[str]
) -> dict[str, dict[str, Any]]:
    if not tickers:
        return {}
    result = (
        supabase.table("ticker_news_cache")
        .select("*")
        .in_("ticker", [ticker.upper() for ticker in tickers])
        .order("processed_at", desc=True)
        .order("published_at", desc=True)
        .execute()
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        ticker = row.get("ticker")
        if ticker and ticker not in grouped:
            grouped[ticker] = row
    return grouped


def _analysis_state_from_context(
    *,
    snapshot: dict[str, Any] | None,
    latest_position_analysis: dict[str, Any] | None,
    latest_analysis_run: dict[str, Any] | None,
    latest_refresh_job: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    current_score: dict[str, Any] | None,
    latest_news_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = snapshot or {}
    latest_position_analysis = latest_position_analysis or {}
    latest_analysis_run = latest_analysis_run or {}
    latest_refresh_job = latest_refresh_job or {}
    metadata = metadata or {}
    current_score = current_score or {}

    coverage_state = (
        current_score.get("coverage_state")
        or latest_position_analysis.get("coverage_state")
        or snapshot.get("coverage_state")
        or "provisional"
    )
    coverage_note = (
        current_score.get("coverage_note")
        or latest_position_analysis.get("coverage_note")
        or snapshot.get("coverage_note")
    )

    latest_refresh_status = latest_refresh_job.get("status")
    latest_run_status = latest_analysis_run.get("status")
    last_news_refresh_at = (
        latest_news_row.get("processed_at")
        if latest_news_row and latest_news_row.get("processed_at")
        else latest_refresh_job.get("completed_at")
        if latest_refresh_status in {"completed", "skipped_ai_scored"}
        else None
    )
    news_refresh_status = (
        latest_refresh_status
        if latest_refresh_status
        in {"queued", "running", "failed", "completed", "skipped_ai_scored"}
        else "cached"
        if latest_news_row
        else None
    )

    if latest_refresh_status in {"queued", "running"} or latest_run_status == "queued":
        analysis_state = "queued"
    elif latest_refresh_status == "running" or latest_run_status in {
        "starting",
        "running",
    }:
        analysis_state = "running"
    elif latest_refresh_status == "failed" or latest_run_status == "failed":
        analysis_state = "failed"
    elif snapshot and coverage_state == "substantive":
        news_refresh_dt = _parse_iso_datetime(last_news_refresh_at)
        news_is_recent = bool(
            news_refresh_dt
            and datetime.now(timezone.utc) - news_refresh_dt <= timedelta(days=1)
        )
        analysis_state = "ready" if news_is_recent else "stale"
    elif coverage_state in {"thin", "provisional"}:
        analysis_state = "thin"
    else:
        analysis_state = "stale"

    analysis_as_of = (
        latest_analysis_run.get("completed_at")
        if latest_run_status in {"completed", "partial"}
        else latest_position_analysis.get("updated_at")
        or snapshot.get("analysis_as_of")
    )

    return {
        "status": analysis_state,
        "source": "user"
        if latest_position_analysis or latest_analysis_run
        else "shared",
        "coverage_state": coverage_state,
        "coverage_note": coverage_note,
        "latest_analysis_run_id": latest_analysis_run.get("id") or None,
        "latest_analysis_status": latest_run_status,
        "latest_refresh_job_id": latest_refresh_job.get("id") or None,
        "latest_refresh_status": latest_refresh_status,
        "news_refresh_status": news_refresh_status,
        "last_success_at": latest_refresh_job.get("completed_at")
        if latest_refresh_status in {"completed", "skipped_ai_scored"}
        else latest_analysis_run.get("completed_at")
        if latest_run_status in {"completed", "partial"}
        else None,
        "last_failure_at": latest_refresh_job.get("completed_at")
        if latest_refresh_status == "failed"
        else latest_analysis_run.get("completed_at")
        if latest_run_status == "failed"
        else None,
        "analysis_as_of": analysis_as_of,
        "last_news_refresh_at": last_news_refresh_at,
        "price_as_of": metadata.get("price_as_of"),
        "news_as_of": latest_news_row.get("published_at") if latest_news_row else None,
    }


def build_holding_workflow_response(
    supabase,
    *,
    user_id: str,
    ticker: str,
    position_id: str,
    position: dict[str, Any] | None = None,
    latest_analysis_run: dict[str, Any] | None = None,
    latest_refresh_job: dict[str, Any] | None = None,
    latest_news_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_ticker = (ticker or "").strip().upper()
    position = position or {}
    metadata = get_metadata_map(supabase, [normalized_ticker]).get(
        normalized_ticker, {}
    )
    if latest_news_row is None:
        news_result = (
            supabase.table("ticker_news_cache")
            .select("*")
            .eq("ticker", normalized_ticker)
            .order("processed_at", desc=True)
            .order("published_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_news_row = news_result.data[0] if news_result.data else None
    snapshot_history = get_latest_risk_snapshot_history_map(
        supabase, [normalized_ticker], per_ticker=1
    ).get(normalized_ticker, [])
    snapshot = snapshot_history[0] if snapshot_history else None
    latest_position_analysis = _get_latest_position_analysis_for_ids(
        supabase, [position_id]
    )
    latest_refresh_job = latest_refresh_job or get_latest_refresh_job(supabase, ticker)
    latest_analysis_run = latest_analysis_run or _get_latest_analysis_run_for_ids(
        supabase, [position_id]
    )
    current_score = build_risk_score_response(
        snapshot,
        position_id=position_id,
        latest_position_score=_get_latest_position_score_for_ids(
            supabase, [position_id]
        ),
        include_position_sizing=bool(position_id),
        coverage_context=latest_position_analysis,
    )
    analysis_state = _analysis_state_from_context(
        snapshot=snapshot,
        latest_position_analysis=latest_position_analysis,
        latest_analysis_run=latest_analysis_run,
        latest_refresh_job=latest_refresh_job,
        metadata=metadata,
        current_score=current_score,
        latest_news_row=latest_news_row,
    )
    enriched_position = sanitize_public_analysis_text(
        {
            **position,
            "analysis_state": analysis_state["status"],
            "coverage_state": analysis_state["coverage_state"],
            "coverage_note": analysis_state["coverage_note"],
            "analysis_run_id": analysis_state["latest_analysis_run_id"],
            "latest_analysis_run_status": latest_analysis_run.get("status"),
            "latest_refresh_job_id": analysis_state["latest_refresh_job_id"],
            "latest_refresh_job_status": analysis_state["latest_refresh_status"],
            "analysis_as_of": analysis_state["analysis_as_of"],
            "score_source": current_score.get("score_source"),
            "score_as_of": current_score.get("score_as_of"),
            "score_version": current_score.get("score_version"),
            "last_news_refresh_at": analysis_state["last_news_refresh_at"],
            "news_refresh_status": analysis_state["news_refresh_status"],
            "price_as_of": analysis_state["price_as_of"],
            "news_as_of": analysis_state["news_as_of"],
            "source": analysis_state["source"],
        }
    )
    return {
        "holding_id": position_id,
        "ticker": normalized_ticker,
        "analysis_state": analysis_state["status"],
        "analysis_run_id": analysis_state["latest_analysis_run_id"],
        "latest_refresh_job": latest_refresh_job,
        "coverage_state": analysis_state["coverage_state"],
        "coverage_note": analysis_state["coverage_note"],
        "analysis_as_of": analysis_state["analysis_as_of"],
        "score_source": current_score.get("score_source"),
        "score_as_of": current_score.get("score_as_of"),
        "score_version": current_score.get("score_version"),
        "last_news_refresh_at": analysis_state["last_news_refresh_at"],
        "news_refresh_status": analysis_state["news_refresh_status"],
        "news_as_of": analysis_state["news_as_of"],
        "price_as_of": analysis_state["price_as_of"],
        "position": enriched_position,
        "source": analysis_state["source"],
    }


def get_ticker_detail_bundle(supabase, user_id: str, ticker: str) -> dict[str, Any]:
    supported = require_supported_ticker(supabase, ticker)
    ticker = supported["ticker"]

    metadata = get_metadata_map(supabase, [ticker]).get(ticker, {})
    history = get_latest_risk_snapshot_history_map(
        supabase, [ticker], per_ticker=2
    ).get(ticker, [])
    snapshot = history[0] if history else None
    previous_snapshot = history[1] if len(history) > 1 else None
    news_result = (
        supabase.table("ticker_news_cache")
        .select("*")
        .eq("ticker", ticker)
        .order("processed_at", desc=True)
        .order("published_at", desc=True)
        .limit(10)
        .execute()
    )
    latest_news_row = news_result.data[0] if news_result.data else None
    positions_result = (
        supabase.table("positions")
        .select("*")
        .eq("user_id", user_id)
        .eq("ticker", ticker)
        .execute()
    )
    held_positions = positions_result.data or []
    holding_ids = [row["id"] for row in held_positions]
    reference_position_ids = holding_ids
    if not reference_position_ids:
        system_position_rows = (
            supabase.table("positions")
            .select("id")
            .eq("user_id", SYSTEM_SP500_USER_ID)
            .eq("ticker", ticker)
            .limit(1)
            .execute()
            .data
            or []
        )
        reference_position_ids = (
            [system_position_rows[0]["id"]] if system_position_rows else []
        )
    latest_position_score = _get_latest_position_score_for_ids(
        supabase, reference_position_ids
    )
    latest_position_analysis = _get_latest_position_analysis_for_ids(
        supabase, reference_position_ids
    )
    latest_analysis_run = _get_latest_analysis_run_for_ids(
        supabase, reference_position_ids
    )
    latest_refresh_job = get_latest_refresh_job(supabase, ticker)
    current_analysis = (
        latest_position_analysis
        or build_position_analysis_from_snapshot(
            snapshot,
            position_id=(
                reference_position_ids[0]
                if reference_position_ids
                else f"virtual:{ticker}"
            ),
            ticker=ticker,
        )
    )
    current_score = build_risk_score_response(
        snapshot,
        position_id=(
            reference_position_ids[0] if reference_position_ids else f"virtual:{ticker}"
        ),
        latest_position_score=latest_position_score,
        include_position_sizing=bool(held_positions),
        coverage_context=latest_position_analysis or current_analysis,
    )
    coverage_state = (
        (current_score or {}).get("coverage_state")
        or (latest_position_analysis or {}).get("coverage_state")
        or "provisional"
    )
    latest_refresh_status = (latest_refresh_job or {}).get("status")
    latest_run_status = (latest_analysis_run or {}).get("status")

    if latest_refresh_status in {"queued", "running"} or latest_run_status in {
        "queued",
        "starting",
        "running",
    }:
        analysis_state = "running"
    elif latest_refresh_status == "failed" or latest_run_status == "failed":
        analysis_state = "failed"
    elif latest_refresh_status == "skipped_ai_scored":
        analysis_state = "fresh"
    elif snapshot and coverage_state == "substantive" and latest_news_row:
        analysis_state = "fresh"
    else:
        analysis_state = "stale"

    last_success_at = (
        (latest_refresh_job or {}).get("completed_at")
        if latest_refresh_status in {"completed", "skipped_ai_scored"}
        else (latest_analysis_run or {}).get("completed_at")
        if latest_run_status in {"completed", "partial"}
        else None
    )
    last_failure_at = (
        (latest_refresh_job or {}).get("completed_at")
        if latest_refresh_status == "failed"
        else (latest_analysis_run or {}).get("completed_at")
        if latest_run_status == "failed"
        else None
    )
    last_news_refresh_at = (
        latest_news_row.get("processed_at")
        if latest_news_row and latest_news_row.get("processed_at")
        else (latest_refresh_job or {}).get("completed_at")
        if latest_refresh_status in {"completed", "skipped_ai_scored"}
        else None
    )
    analysis_state_payload = {
        "status": analysis_state,
        "source": "user" if latest_position_analysis else "shared",
        "coverage_state": coverage_state,
        "latest_analysis_run_id": latest_analysis_run.get("id")
        if latest_analysis_run
        else None,
        "latest_analysis_status": latest_run_status,
        "latest_refresh_job_id": latest_refresh_job.get("id")
        if latest_refresh_job
        else None,
        "latest_refresh_status": latest_refresh_status,
        "news_refresh_status": latest_refresh_status
        or ("cached" if latest_news_row else None),
        "score_source": current_score.get("score_source"),
        "score_as_of": current_score.get("score_as_of"),
        "score_version": current_score.get("score_version"),
        "last_success_at": last_success_at,
        "last_failure_at": last_failure_at,
        "analysis_as_of": (snapshot or {}).get("analysis_as_of"),
        "last_news_refresh_at": last_news_refresh_at,
        "price_as_of": metadata.get("price_as_of"),
        "news_as_of": latest_news_row.get("published_at") if latest_news_row else None,
    }

    if held_positions:
        position = held_positions[0]
        position["risk_grade"] = current_score.get("grade") or (
            snapshot.get("grade") if snapshot else None
        )
        position["total_score"] = current_score.get("total_score") or (
            snapshot.get("safety_score") if snapshot else None
        )
        position["previous_grade"] = (
            previous_snapshot.get("grade") if previous_snapshot else None
        )
        position["summary"] = (
            current_score.get("reasoning")
            or (snapshot or {}).get("news_summary")
            or (snapshot or {}).get("reasoning")
        )
        position["last_analyzed_at"] = current_score.get("score_as_of") or (
            snapshot or {}
        ).get("analysis_as_of")
        if position.get("current_price") is None:
            position["current_price"] = metadata.get("price")
    else:
        position = _build_virtual_position(
            user_id=user_id,
            ticker=ticker,
            metadata=metadata,
            snapshot=snapshot,
            previous_snapshot=previous_snapshot,
        )

    position["score_source"] = analysis_state_payload.get("score_source")
    position["score_as_of"] = analysis_state_payload.get("score_as_of")
    position["score_version"] = analysis_state_payload.get("score_version")

    if holding_ids:
        event_rows = (
            supabase.table("event_analyses")
            .select("*")
            .in_("position_id", holding_ids)
            .order("created_at", desc=True)
            .limit(20)  # fetch extra so dedup has room to work
            .execute()
        )
        # Dedup by event_hash then normalized headline; prefer highest-confidence rows
        latest_event_analyses = _dedup_event_analyses(event_rows.data or [])
        # Cap displayed events to source_count so the count matches the risk rationale
        sc = int((current_score or {}).get("source_count") or 0)
        if sc and len(latest_event_analyses) > sc:
            latest_event_analyses = latest_event_analyses[:sc]
    else:
        # Only show news articles that were in the cache when the snapshot was scored,
        # so the displayed list aligns with the source_count in the risk rationale.
        snapshot_as_of = (snapshot or {}).get("analysis_as_of")
        if snapshot_as_of:
            display_news_rows = [
                row
                for row in (news_result.data or [])
                if (row.get("processed_at") or "") <= snapshot_as_of
            ]
        else:
            display_news_rows = news_result.data or []
        latest_event_analyses = _build_event_analyses_from_news_rows(
            display_news_rows,
            ticker=ticker,
            position_id=position["id"],
        )

    # Replace generic/fallback reasoning with article-specific text when we have events.
    # This gives users a specific, article-grounded explanation rather than template prose.
    if latest_event_analyses and current_score:
        existing_reasoning = current_score.get("reasoning") or ""
        if not existing_reasoning or _is_generic_fallback_reasoning(existing_reasoning):
            article_reasoning = _build_article_aware_reasoning(
                latest_event_analyses, current_score, ticker
            )
            if article_reasoning:
                current_score["reasoning"] = article_reasoning

    alerts_result = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .eq("position_ticker", ticker)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    watchlist = get_or_create_default_watchlist(supabase, user_id)
    watchlist_items = (
        supabase.table("watchlist_items")
        .select("id")
        .eq("watchlist_id", watchlist["id"])
        .eq("ticker", ticker)
        .limit(1)
        .execute()
    )

    return sanitize_public_analysis_text(
        {
            "ticker": ticker,
            "profile": {**supported, **metadata},
            "position": position,
            "latest_price": {
                "price": metadata.get("price"),
                "price_as_of": metadata.get("price_as_of"),
                "previous_close": metadata.get("previous_close"),
                "open_price": metadata.get("open_price"),
                "day_high": metadata.get("day_high"),
                "day_low": metadata.get("day_low"),
                "week_52_high": metadata.get("week_52_high"),
                "week_52_low": metadata.get("week_52_low"),
                "avg_volume": metadata.get("avg_volume"),
                "source": metadata.get("last_price_source"),
            },
            "source": analysis_state_payload["source"],
            "analysis_state": analysis_state_payload,
            "latest_analysis_run": latest_analysis_run,
            "latest_refresh_job": latest_refresh_job,
            "coverage_state": coverage_state,
            "latest_risk_snapshot": snapshot,
            "current_score": current_score,
            "current_analysis": current_analysis,
            "methodology": current_analysis.get("methodology")
            if current_analysis
            else None,
            "dimension_breakdown": snapshot.get("dimension_rationale")
            if snapshot
            else None,
            "latest_event_analyses": latest_event_analyses,
            "mirofish_used_this_cycle": False,
            "recent_news": _news_rows_to_response(
                news_result.data or [], user_id=user_id, ticker=ticker
            ),
            "recent_alerts": enrich_alert_rows(alerts_result.data or []),
            "freshness": {
                "price_as_of": metadata.get("price_as_of"),
                "analysis_as_of": snapshot.get("analysis_as_of") if snapshot else None,
                "last_news_refresh_at": analysis_state_payload["last_news_refresh_at"],
                "news_as_of": latest_news_row.get("published_at")
                if latest_news_row
                else None,
                "news_refresh_status": analysis_state_payload["news_refresh_status"],
            },
            "user_context": {
                "is_held": bool(held_positions),
                "holding_ids": holding_ids,
                "is_in_watchlist": bool(watchlist_items.data),
            },
        }
    )


def _upsert_ticker_snapshot(
    supabase,
    *,
    ticker: str,
    snapshot_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    snapshot_date = payload["snapshot_date"]
    existing = (
        supabase.table("ticker_risk_snapshots")
        .select("id")
        .eq("ticker", ticker)
        .eq("snapshot_date", snapshot_date)
        .eq("snapshot_type", snapshot_type)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        (
            supabase.table("ticker_risk_snapshots")
            .update(payload)
            .eq("id", existing[0]["id"])
            .execute()
        )
        payload["id"] = existing[0]["id"]
        return payload

    result = supabase.table("ticker_risk_snapshots").insert(payload).execute()
    return result.data[0] if result.data else payload


def _update_refresh_job(supabase, job_id: str, payload: dict[str, Any]) -> None:
    payload = {**payload, "updated_at": _utcnow_iso()}
    supabase.table("ticker_refresh_jobs").update(payload).eq("id", job_id).execute()


def refresh_ticker_snapshot(
    supabase,
    *,
    ticker: str,
    job_type: str,
    requested_by_user_id: str | None = None,
) -> dict[str, Any]:
    supported = get_supported_ticker(supabase, ticker) or ensure_ticker_in_universe(
        supabase, ticker
    )
    if not supported:
        raise HTTPException(400, "Ticker could not be onboarded into the shared cache")
    ticker = supported["ticker"]

    active_job = (
        supabase.table("ticker_refresh_jobs")
        .select("*")
        .eq("ticker", ticker)
        .in_("status", ["queued", "running"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if active_job:
        return active_job[0]

    shared_news_rows = (
        supabase.table("news_items")
        .select("title, body, source, url, significance, published_at, processed_at, event_hash")
        .eq("ticker", ticker)
        .order("processed_at", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    news_cache_refresh = sync_ticker_news_cache(
        supabase,
        ticker=ticker,
        news_rows=shared_news_rows,
    )

    existing_ai_snapshot = (
        supabase.table("ticker_risk_snapshots")
        .select("id, methodology_version, grade, safety_score")
        .eq("ticker", ticker)
        .eq("snapshot_date", date.today().isoformat())
        .eq("snapshot_type", job_type)
        .ilike("methodology_version", "%ai%")
        .limit(1)
        .execute()
        .data
    )
    if existing_ai_snapshot:
        return {
            "ticker": ticker,
            "job_type": job_type,
            "status": "skipped_ai_scored",
            "methodology_version": existing_ai_snapshot[0].get("methodology_version"),
            "grade": existing_ai_snapshot[0].get("grade"),
            "safety_score": existing_ai_snapshot[0].get("safety_score"),
            "news_cache_status": news_cache_refresh.get("status"),
            "news_cache_count": news_cache_refresh.get("count", 0),
        }

    job_result = (
        supabase.table("ticker_refresh_jobs")
        .insert(
            {
                "ticker": ticker,
                "job_type": job_type,
                "status": "running",
                "requested_by_user_id": requested_by_user_id,
                "started_at": _utcnow_iso(),
                "updated_at": _utcnow_iso(),
            }
        )
        .execute()
    )
    job = job_result.data[0]

    try:
        metadata = upsert_ticker_metadata(supabase, ticker)
        if not metadata:
            raise RuntimeError(f"Unable to refresh ticker metadata for {ticker}")

        previous_snapshot = get_latest_risk_snapshot_map(supabase, [ticker]).get(ticker)
        news_rows = (
            supabase.table("ticker_news_cache")
            .select("*")
            .eq("ticker", ticker)
            .order("processed_at", desc=True)
            .order("published_at", desc=True)
            .limit(10)
            .execute()
            .data
            or []
        )
        recent_events = _build_event_analyses_from_news_rows(
            news_rows, ticker=ticker, position_id=f"virtual:{ticker}"
        )
        score = score_position_structural(
            {},
            ticker_metadata=metadata,
            recent_events=recent_events,
            previous_safety_score=(
                previous_snapshot.get("safety_score") if previous_snapshot else None
            ),
        )
        analysis_as_of = _utcnow_iso()
        snapshot_payload = {
            "ticker": ticker,
            "snapshot_date": date.today().isoformat(),
            "snapshot_type": job_type,
            "grade": score["grade"],
            "safety_score": round(score["safety_score"], 1),
            "structural_base_score": score["structural_base_score"],
            "macro_adjustment": score["macro_adjustment"],
            "event_adjustment": score["event_adjustment"],
            "confidence": score["confidence"],
            "factor_breakdown": score["factor_breakdown"],
            "dimension_rationale": score["dimension_rationale"],
            "reasoning": score["reasoning"],
            "news_summary": (news_rows[0].get("summary") if news_rows else None),
            "source_count": len(news_rows),
            "methodology_version": "sp500-shared-cache-v1",
            "analysis_as_of": analysis_as_of,
            "refresh_triggered_by_user_id": requested_by_user_id,
            "updated_at": analysis_as_of,
            "news_cache_status": news_cache_refresh.get("status"),
            "news_cache_count": news_cache_refresh.get("count", 0),
        }
        snapshot = _upsert_ticker_snapshot(
            supabase,
            ticker=ticker,
            snapshot_type=job_type,
            payload=snapshot_payload,
        )
        _update_refresh_job(
            supabase,
            job["id"],
            {
                "status": "completed",
                "completed_at": analysis_as_of,
                "error_message": None,
            },
        )
        return {
            **job,
            "status": "completed",
            "completed_at": analysis_as_of,
            "snapshot": snapshot,
        }
    except Exception as exc:
        _update_refresh_job(
            supabase,
            job["id"],
            {
                "status": "failed",
                "completed_at": _utcnow_iso(),
                "error_message": str(exc),
            },
        )
        raise


def get_latest_refresh_job(supabase, ticker: str) -> dict[str, Any] | None:
    supported = get_supported_ticker(supabase, ticker)
    if not supported:
        return None
    result = (
        supabase.table("ticker_refresh_jobs")
        .select("*")
        .eq("ticker", supported["ticker"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_or_create_default_watchlist(supabase, user_id: str) -> dict[str, Any]:
    existing = (
        supabase.table("watchlists")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_default", True)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return existing[0]

    try:
        result = (
            supabase.table("watchlists")
            .insert({"user_id": user_id, "name": "Watchlist", "is_default": True})
            .execute()
        )
        return result.data[0]
    except AttributeError:
        return {"id": None, "user_id": user_id, "name": "Watchlist", "is_default": True}


def get_default_watchlist_detail(supabase, user_id: str) -> dict[str, Any]:
    watchlist = get_or_create_default_watchlist(supabase, user_id)
    items = (
        supabase.table("watchlist_items")
        .select("id, ticker, created_at")
        .eq("watchlist_id", watchlist["id"])
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )
    tickers = [item["ticker"] for item in items]
    metadata_map = get_metadata_map(supabase, tickers)
    snapshot_map = get_latest_risk_snapshot_map(supabase, tickers)
    enriched_items = []
    for item in items:
        ticker = item["ticker"]
        metadata = metadata_map.get(ticker, {})
        snapshot = snapshot_map.get(ticker, {})
        enriched_items.append(
            {
                **item,
                "company_name": metadata.get("company_name"),
                "price": metadata.get("price"),
                "price_as_of": metadata.get("price_as_of"),
                "grade": snapshot.get("grade"),
                "safety_score": snapshot.get("safety_score"),
                "analysis_as_of": snapshot.get("analysis_as_of"),
                "summary": snapshot.get("news_summary") or snapshot.get("reasoning"),
            }
        )
    watchlist["items"] = enriched_items
    return watchlist
