from fastapi import APIRouter, Request, Depends, HTTPException
from datetime import datetime, timedelta, timezone
from ..services.supabase import get_supabase
from ..services.digest_selection import select_latest_trading_day_digest
from ..services.ticker_cache_service import (
    enrich_positions_with_ticker_cache,
    get_default_watchlist_detail,
)
from .analysis_runs import _enrich_run
from ..pipeline.portfolio_compiler import compile_portfolio_digest
from ..pipeline.macro_classifier import classify_overnight_macro
from ..pipeline.rss_ingest import fetch_cnbc_macro_rss, fetch_cnbc_sector_rss
from ..pipeline.macro_classifier import summarize_sector_overview

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

    def build_digest_response(digest: dict | None, message: str = "ok"):
        return {
            "digest": digest,
            "saved_digest": latest_saved_digest,
            "generated_digest": None,
            "analysis_run": _enrich_run(latest_run, latest_run_digest)
            if latest_run
            else None,
            "overall_grade": digest.get("overall_grade") if digest else None,
            "structured_sections": digest.get("structured_sections")
            if digest
            else None,
            "generated_at": digest.get("generated_at") if digest else None,
            "grade_summary": digest.get("grade_summary") if digest else None,
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
        return build_digest_response(selected_digest)

    if not force_refresh:
        if selected_digest:
            return build_digest_response(selected_digest)
        return {
            "digest": None,
            "saved_digest": latest_saved_digest,
            "generated_digest": None,
            "analysis_run": _enrich_run(latest_run, latest_run_digest)
            if latest_run
            else None,
            "message": "No digest saved yet",
        }

    if positions:
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

        overall_score, overall_grade = _compute_shared_portfolio_grade(positions)
        macro_context = None
        sector_context = None
        watchlist_alerts: list[str] = []
        try:
            macro_articles = await fetch_cnbc_macro_rss(limit=12)
            macro_context = await classify_overnight_macro(macro_articles, positions)
        except Exception:
            macro_context = None

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
                        sector_articles_by_name.setdefault(sector_name, []).append(
                            article
                        )
                sector_context = await summarize_sector_overview(
                    sector_articles_by_name
                )
        except Exception:
            sector_context = None

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

        compiled_digest = await compile_portfolio_digest(
            positions,
            overall_grade,
            macro_context=macro_context,
            sector_context=sector_context,
            watchlist_alerts=watchlist_alerts,
        )
        structured_sections = dict(compiled_digest["sections"])
        structured_sections["digest_version"] = DIGEST_VERSION

        digest_payload = {
            "user_id": user_id,
            "analysis_run_id": latest_run["id"] if latest_run else None,
            "content": compiled_digest["content"],
            "grade_summary": {
                p["ticker"]: p.get("risk_grade") or p.get("grade") for p in positions
            },
            "overall_grade": overall_grade,
            "overall_score": overall_score,
            "structured_sections": structured_sections,
            "summary": compiled_digest["overall_summary"],
            "generated_at": now.isoformat(),
        }
        inserted_digest = (
            supabase.table("digests").insert(digest_payload).execute().data
        )
        digest_record = inserted_digest[0] if inserted_digest else digest_payload
        _touch_manual_refresh(supabase, user_id, now)

        return {
            "digest": {
                "user_id": user_id,
                "analysis_run_id": digest_record.get("analysis_run_id"),
                "content": digest_record.get("content", compiled_digest["content"]),
                "grade_summary": {
                    p["ticker"]: p.get("risk_grade") or p.get("grade")
                    for p in positions
                },
                "overall_grade": overall_grade,
                "overall_score": overall_score,
                "structured_sections": digest_record.get(
                    "structured_sections", structured_sections
                ),
                "summary": digest_record.get(
                    "summary", compiled_digest["overall_summary"]
                ),
            },
            "saved_digest": latest_saved_digest,
            "generated_digest": digest_record,
            "analysis_run": None,
            "overall_grade": overall_grade,
            "structured_sections": digest_record.get(
                "structured_sections", structured_sections
            ),
            "generated_at": digest_record.get("generated_at"),
            "grade_summary": {
                p["ticker"]: p.get("risk_grade") or p.get("grade") for p in positions
            },
            "message": "generated from shared ticker cache",
        }

    return build_digest_response(selected_digest, message="No digest generated yet")


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
