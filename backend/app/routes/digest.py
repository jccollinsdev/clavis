from typing import Any

from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import datetime, timedelta, timezone
from ..services.supabase import get_supabase
from ..services.digest_selection import select_latest_trading_day_digest
from ..services.ticker_cache_service import (
    enrich_positions_with_ticker_cache,
    get_default_watchlist_detail,
    get_metadata_map,
)
from .analysis_runs import _enrich_run
from ..pipeline.portfolio_compiler import compile_portfolio_digest
from ..pipeline.macro_classifier import classify_overnight_macro
from ..pipeline.rss_ingest import fetch_cnbc_macro_rss, fetch_cnbc_sector_rss
from ..pipeline.macro_classifier import summarize_sector_overview
from ..pipeline.portfolio_risk import calculate_portfolio_risk_score
from ..pipeline.scheduler import (
    _compute_portfolio_grade,
    _maybe_create_alert,
    _set_analysis_stage,
    create_analysis_run,
)

DIGEST_VERSION = 2

router = APIRouter()


def get_user_id(request: Request) -> str:
    return request.state.user_id


def _compute_shared_portfolio_grade(positions: list[dict]) -> tuple[float, str]:
    scores = [
        float(p.get("total_score") or p.get("risk_score") or 50) for p in positions
    ]
    if not scores:
        return 50.0, "C"
    avg = sum(scores) / len(scores)
    if avg >= 80:
        grade = "A"
    elif avg >= 65:
        grade = "B"
    elif avg >= 50:
        grade = "C"
    elif avg >= 35:
        grade = "D"
    else:
        grade = "F"
    return round(avg, 1), grade


def _build_watchlist_alerts(
    alert_rows: list[dict], watchlist_tickers: set[str]
) -> list[str]:
    if not watchlist_tickers:
        return []

    priority_types = {
        "grade_change",
        "major_event",
        "portfolio_grade_change",
        "safety_deterioration",
        "concentration_danger",
        "cluster_risk",
        "macro_shock",
        "structural_fragility",
        "portfolio_safety_threshold_breach",
    }

    seen: set[str] = set()
    alerts: list[str] = []
    for alert in alert_rows:
        ticker = str(alert.get("position_ticker") or "").strip().upper()
        if not ticker or ticker not in watchlist_tickers or ticker in seen:
            continue
        alert_type = str(alert.get("type") or "").strip().lower()
        if alert_type not in priority_types:
            continue
        message = str(alert.get("message") or "").strip()
        if not message:
            continue
        alerts.append(f"{ticker} — {alert_type.replace('_', ' ').title()}: {message}")
        seen.add(ticker)
        if len(alerts) >= 6:
            break
    return alerts


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _manual_refresh_ready(supabase, user_id: str, now: datetime) -> tuple[bool, int]:
    prefs = (
        supabase.table("user_preferences")
        .select("last_manual_refresh_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    last_refresh_at = (
        _parse_iso_datetime(prefs[0].get("last_manual_refresh_at")) if prefs else None
    )
    if not last_refresh_at:
        return True, 0

    cooldown = timedelta(hours=1)
    elapsed = now - last_refresh_at
    if elapsed >= cooldown:
        return True, 0

    remaining = int((cooldown - elapsed).total_seconds() // 60) + 1
    return False, remaining


def _touch_manual_refresh(supabase, user_id: str, now: datetime) -> None:
    payload = {"user_id": user_id, "last_manual_refresh_at": now.isoformat()}
    existing = (
        supabase.table("user_preferences")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        supabase.table("user_preferences").update(payload).eq(
            "user_id", user_id
        ).execute()
    else:
        supabase.table("user_preferences").insert(payload).execute()


def _digest_provenance_fields(digest: dict | None) -> dict[str, Any | None]:
    if not digest:
        return {
            "overall_score": None,
            "overall_grade": None,
            "score_source": None,
            "score_as_of": None,
            "score_version": None,
        }

    return {
        "overall_score": digest.get("overall_score"),
        "overall_grade": digest.get("overall_grade"),
        "score_source": "digest",
        "score_as_of": digest.get("generated_at"),
        "score_version": digest.get("analysis_run_id"),
    }


async def _build_force_refresh_digest(
    supabase,
    *,
    user_id: str,
    positions: list[dict],
    latest_saved_digest: dict | None,
    latest_run: dict | None,
    now: datetime,
) -> dict[str, Any]:
    positions = enrich_positions_with_ticker_cache(positions, supabase)

    position_ids = [position["id"] for position in positions if position.get("id")]
    analysis_rows = []
    if position_ids:
        analysis_rows = (
            supabase.table("position_analyses")
            .select(
                "position_id, summary, methodology, watch_items, top_risks, source_count, major_event_count, minor_event_count, updated_at"
            )
            .in_("position_id", position_ids)
            .order("updated_at", desc=True)
            .execute()
            .data
            or []
        )

    analysis_by_position: dict[str, dict] = {}
    for row in analysis_rows:
        position_id = str(row.get("position_id") or "")
        if position_id and position_id not in analysis_by_position:
            analysis_by_position[position_id] = row

    for position in positions:
        position["grade"] = position.get("risk_grade") or position.get("grade")
        position["safety_score"] = position.get("total_score") or position.get(
            "safety_score"
        )
        position["confidence"] = position.get("confidence") or 0.65
        position["structural_base_score"] = position.get(
            "structural_base_score"
        ) or position.get("total_score")
        analysis = analysis_by_position.get(str(position.get("id") or ""), {})
        position["top_risks"] = (
            position.get("top_risks") or analysis.get("top_risks") or []
        )
        position["watch_items"] = (
            position.get("watch_items") or analysis.get("watch_items") or []
        )
        position["thesis_verifier"] = position.get("thesis_verifier") or []

    prefs = (
        supabase.table("user_preferences")
        .select("summary_length")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    summary_length = (
        (prefs[0].get("summary_length") or "standard") if prefs else "standard"
    )

    ticker_metadata_map = get_metadata_map(
        supabase,
        [position.get("ticker") for position in positions if position.get("ticker")],
    )
    sector_map = {
        ticker: metadata.get("sector", "unknown")
        for ticker, metadata in ticker_metadata_map.items()
    }
    portfolio_risk = calculate_portfolio_risk_score(
        positions=positions,
        sector_map=sector_map,
        ticker_metadata=ticker_metadata_map,
        ticker_correlation_matrix=None,
        regime_state="neutral",
    )

    macro_context = None
    try:
        macro_articles = await fetch_cnbc_macro_rss(limit=12)
        macro_context = await classify_overnight_macro(macro_articles, positions)
    except Exception:
        macro_context = None

    sector_context = None
    try:
        sector_names = sorted(
            {
                str(position.get("sector") or "").strip()
                for position in positions
                if str(position.get("sector") or "").strip()
            }
        )
        if sector_names:
            sector_articles = await fetch_cnbc_sector_rss(
                sector_names, limit_per_sector=8
            )
            sector_articles_by_name: dict[str, list[dict]] = {}
            for article in sector_articles:
                if isinstance(article, dict):
                    sector_name = (
                        str(article.get("sector_hint") or article.get("sector") or "")
                        .strip()
                        .lower()
                    )
                else:
                    sector_name = sector_names[0].strip().lower()
                if sector_name and sector_name not in {
                    "unknown",
                    "none",
                    "null",
                    "n/a",
                }:
                    sector_articles_by_name.setdefault(sector_name, []).append(article)
            if not sector_articles_by_name and sector_articles and sector_names:
                sector_articles_by_name[sector_names[0].strip().lower()] = list(
                    sector_articles
                )
            sector_context = await summarize_sector_overview(sector_articles_by_name)
    except Exception:
        sector_context = None

    watchlist_alerts: list[str] = []
    try:
        watchlist_detail = get_default_watchlist_detail(supabase, user_id)
        watchlist_tickers = {
            str(item.get("ticker") or "").strip().upper()
            for item in watchlist_detail.get("items", [])
            if str(item.get("ticker") or "").strip()
        }
        if watchlist_tickers:
            recent_watchlist_alerts = (
                supabase.table("alerts")
                .select("*")
                .eq("user_id", user_id)
                .in_("position_ticker", list(watchlist_tickers))
                .order("created_at", desc=True)
                .limit(20)
                .execute()
                .data
                or []
            )
            watchlist_alerts = _build_watchlist_alerts(
                recent_watchlist_alerts, watchlist_tickers
            )
    except Exception:
        watchlist_alerts = []

    portfolio_score, overall_grade = _compute_portfolio_grade(positions)
    digest = await compile_portfolio_digest(
        positions,
        overall_grade,
        portfolio_risk=portfolio_risk,
        macro_context=macro_context,
        sector_context=sector_context,
        watchlist_alerts=watchlist_alerts,
        summary_length=summary_length,
    )
    structured_sections = dict(digest["sections"])
    structured_sections["digest_version"] = DIGEST_VERSION

    digest_run = latest_run
    if not digest_run or digest_run.get("status") not in {"queued", "running"}:
        digest_run = await create_analysis_run(user_id, "manual")

    _set_analysis_stage(
        supabase,
        digest_run["id"],
        "building_digest",
        "Building your morning digest.",
        positions_processed=len(positions),
        events_processed=0,
    )

    digest_payload = {
        "user_id": user_id,
        "analysis_run_id": digest_run["id"],
        "content": digest["content"],
        "grade_summary": {
            position["ticker"]: position.get("grade") for position in positions
        },
        "overall_grade": overall_grade,
        "overall_score": portfolio_score,
        "structured_sections": structured_sections,
        "summary": digest["overall_summary"],
        "generated_at": now.isoformat(),
    }
    inserted_digest = supabase.table("digests").insert(digest_payload).execute().data
    digest_record = inserted_digest[0] if inserted_digest else digest_payload

    previous_portfolio_grade = (
        latest_saved_digest.get("overall_grade") if latest_saved_digest else None
    )
    if previous_portfolio_grade and previous_portfolio_grade != overall_grade:
        await _maybe_create_alert(
            supabase,
            {
                "user_id": user_id,
                "type": "portfolio_grade_change",
                "previous_grade": previous_portfolio_grade,
                "new_grade": overall_grade,
                "message": f"Overall portfolio grade changed from {previous_portfolio_grade} to {overall_grade}",
                "analysis_run_id": digest_run["id"],
                "change_reason": "Portfolio-wide score moved after the latest digest refresh.",
                "change_details": {
                    "previous_grade": previous_portfolio_grade,
                    "new_grade": overall_grade,
                    "overall_score": f"{portfolio_score:.1f}",
                },
            },
        )

    await _maybe_create_alert(
        supabase,
        {
            "user_id": user_id,
            "type": "digest_ready",
            "message": "Your latest Clavynx digest is ready.",
            "analysis_run_id": digest_run["id"],
        },
        dedupe_hours=4,
    )

    _set_analysis_stage(
        supabase,
        digest_run["id"],
        "completed",
        "Digest refresh complete.",
        status="completed",
        completed_at=now.isoformat(),
        overall_portfolio_grade=overall_grade,
        positions_processed=len(positions),
        events_processed=0,
    )

    digest_run = {
        **digest_run,
        "current_stage": "completed",
        "current_stage_message": "Digest refresh complete.",
        "status": "completed",
        "completed_at": now.isoformat(),
        "overall_portfolio_grade": overall_grade,
        "positions_processed": len(positions),
        "events_processed": 0,
    }

    digest_record = {
        **digest_record,
        **_digest_provenance_fields(digest_record),
    }
    analysis_run = _enrich_run(
        digest_run,
        [
            {
                "id": digest_record.get("id"),
                "overall_grade": overall_grade,
                "generated_at": digest_record.get("generated_at"),
            }
        ],
    )

    return {
        "digest": digest_record,
        "saved_digest": latest_saved_digest,
        "generated_digest": digest_record,
        "analysis_run": analysis_run,
        **_digest_provenance_fields(digest_record),
        "grade_summary": digest_record.get("grade_summary"),
        "structured_sections": digest_record.get("structured_sections"),
        "generated_at": digest_record.get("generated_at"),
        "message": "generated from shared ticker cache",
    }


@router.get("")
async def get_digest(force_refresh: bool = False, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    now = datetime.now(timezone.utc)

    latest_run_result = (
        supabase.table("analysis_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    latest_run = latest_run_result.data[0] if latest_run_result.data else None
    latest_run_digest = None
    if latest_run:
        latest_run_digest = (
            supabase.table("digests")
            .select("id, overall_grade, generated_at")
            .eq("analysis_run_id", latest_run["id"])
            .limit(1)
            .execute()
            .data
        )

    all_digests_result = (
        supabase.table("digests")
        .select("*")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(12)
        .execute()
    )

    latest_saved_digest = (
        all_digests_result.data[0] if all_digests_result.data else None
    )
    selected_digest = select_latest_trading_day_digest(all_digests_result.data, now)

    def _analysis_run_for_digest(digest: dict | None):
        if not digest or not digest.get("analysis_run_id"):
            return None, None

        run_result = (
            supabase.table("analysis_runs")
            .select("*")
            .eq("id", digest["analysis_run_id"])
            .limit(1)
            .execute()
            .data
        )
        run = run_result[0] if run_result else None
        run_digest = None
        if run:
            run_digest = (
                supabase.table("digests")
                .select("id, overall_grade, generated_at")
                .eq("analysis_run_id", run["id"])
                .limit(1)
                .execute()
                .data
            )
        return run, run_digest

    def build_digest_response(
        digest: dict | None,
        analysis_run: dict | None,
        message: str = "ok",
    ):
        digest_payload = (
            {**digest, **_digest_provenance_fields(digest)} if digest else None
        )
        return {
            "digest": digest_payload,
            "saved_digest": latest_saved_digest,
            "generated_digest": None,
            "analysis_run": analysis_run,
            **_digest_provenance_fields(digest),
            "structured_sections": digest_payload.get("structured_sections")
            if digest_payload
            else None,
            "generated_at": digest_payload.get("generated_at")
            if digest_payload
            else None,
            "grade_summary": digest_payload.get("grade_summary")
            if digest_payload
            else None,
            "message": message,
        }

    positions = (
        supabase.table("positions").select("*").eq("user_id", user_id).execute().data
        or []
    )
    if force_refresh and positions:
        ready, minutes_remaining = _manual_refresh_ready(supabase, user_id, now)
        if not ready:
            raise HTTPException(
                429,
                f"Manual digest refresh is limited to once per hour. Try again in about {minutes_remaining} minutes.",
            )

    if not positions and selected_digest:
        selected_run, selected_run_digest = _analysis_run_for_digest(selected_digest)
        return build_digest_response(
            selected_digest,
            _enrich_run(selected_run, selected_run_digest) if selected_run else None,
        )

    if not force_refresh:
        if selected_digest:
            selected_run, selected_run_digest = _analysis_run_for_digest(
                selected_digest
            )
            return build_digest_response(
                selected_digest,
                _enrich_run(selected_run, selected_run_digest)
                if selected_run
                else None,
            )
        return {
            "digest": None,
            "saved_digest": latest_saved_digest,
            "generated_digest": None,
            "analysis_run": _enrich_run(latest_run, latest_run_digest)
            if latest_run
            else None,
            **_digest_provenance_fields(None),
            "message": "No digest saved yet",
        }

    if positions:
        digest_response = await _build_force_refresh_digest(
            supabase,
            user_id=user_id,
            positions=positions,
            latest_saved_digest=latest_saved_digest,
            latest_run=latest_run,
            now=now,
        )
        _touch_manual_refresh(supabase, user_id, now)
        return digest_response

    return build_digest_response(
        selected_digest,
        _enrich_run(latest_run, latest_run_digest) if latest_run else None,
        message="No digest generated yet",
    )


@router.get("/history")
async def get_digest_history(limit: int = 7, user_id: str = Depends(get_user_id)):
    supabase = get_supabase()
    result = (
        supabase.table("digests")
        .select("*")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
