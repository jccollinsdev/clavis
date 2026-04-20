from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .ticker_cache_service import (
    get_latest_risk_snapshot_history_map,
    get_latest_risk_snapshot_map,
    get_metadata_map,
    get_or_create_default_watchlist,
)


SEVERE_ALERT_TYPES = {
    "grade_change",
    "portfolio_grade_change",
    "safety_deterioration",
    "concentration_danger",
    "cluster_risk",
    "macro_shock",
    "structural_fragility",
    "portfolio_safety_threshold_breach",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc)

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _clean_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _clean_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [
        item
        for item in (
            _clean_string(value).upper() for value in values if _clean_string(value)
        )
        if item
    ]


def _story_category(
    *,
    ticker: str | None,
    held_tickers: set[str],
    watchlist_tickers: set[str],
    source_type: str | None,
    relevance: dict[str, Any] | None,
    alerts_by_ticker: dict[str, list[dict[str, Any]]],
) -> str:
    normalized_ticker = _clean_string(ticker).upper()
    if normalized_ticker and normalized_ticker in held_tickers:
        if any(
            str(alert.get("type") or "").strip() in SEVERE_ALERT_TYPES
            for alert in alerts_by_ticker.get(normalized_ticker, [])
        ):
            return "major"
        return "portfolio"

    if normalized_ticker and normalized_ticker in watchlist_tickers:
        return "watchlist"

    if source_type in {"market", "macro", "sector"}:
        return "market"

    event_type = _clean_string((relevance or {}).get("event_type")).lower()
    if event_type in {"macro", "sector", "theme"}:
        return "market"

    if any(
        str(alert.get("type") or "").strip() in SEVERE_ALERT_TYPES
        for alert in alerts_by_ticker.get(normalized_ticker, [])
    ):
        return "major"

    return "portfolio" if normalized_ticker else "market"


def _story_priority(category: str) -> int:
    return {
        "major": 4,
        "portfolio": 3,
        "watchlist": 2,
        "market": 1,
    }.get(category, 0)


def _base_story(
    *,
    source_table: str,
    source_id: str,
    title: str,
    summary: str | None,
    body: str | None,
    source: str | None,
    url: str | None,
    published_at: Any,
    ticker: str | None,
    tickers: list[str],
    category: str,
    relevance: str | None,
    grade: str | None,
    previous_grade: str | None,
    current_grade: str | None,
    factored: bool,
    impact: str | None,
    held_shares: float | None,
    position_id: str | None,
    analysis_run_id: str | None,
    image_url: str | None = None,
) -> dict[str, Any]:
    article_id = f"{source_table}:{source_id}"
    return {
        "id": article_id,
        "source_table": source_table,
        "source_id": source_id,
        "ticker": ticker,
        "tickers": tickers,
        "title": _clean_string(title),
        "summary": _clean_string(summary) or None,
        "body": _clean_string(body) or None,
        "source": _clean_string(source) or None,
        "url": _clean_string(url) or None,
        "published_at": _parse_timestamp(published_at).isoformat(),
        "category": category,
        "relevance": relevance,
        "grade": grade,
        "previous_grade": previous_grade,
        "current_grade": current_grade,
        "factored": factored,
        "impact": _clean_string(impact) or None,
        "held_shares": held_shares,
        "position_id": position_id,
        "analysis_run_id": analysis_run_id,
        "image_url": _clean_string(image_url) or None,
    }


def _news_item_story(
    row: dict[str, Any],
    *,
    held_tickers: set[str],
    watchlist_tickers: set[str],
    alerts_by_ticker: dict[str, list[dict[str, Any]]],
    positions_by_ticker: dict[str, dict[str, Any]],
    snapshots_by_ticker: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ticker = _clean_string(row.get("ticker")).upper() or None
    relevance = row.get("relevance") if isinstance(row.get("relevance"), dict) else {}
    category = _story_category(
        ticker=ticker,
        held_tickers=held_tickers,
        watchlist_tickers=watchlist_tickers,
        source_type="news_items",
        relevance=relevance,
        alerts_by_ticker=alerts_by_ticker,
    )
    position = positions_by_ticker.get(ticker or "", {})
    snapshot = snapshots_by_ticker.get(ticker or "", {})
    tickers = _clean_string_list(row.get("affected_tickers"))
    if ticker and ticker not in tickers:
        tickers = [ticker, *tickers]
    if not tickers and ticker:
        tickers = [ticker]

    return _base_story(
        source_table="news_item",
        source_id=str(row.get("id") or ""),
        title=row.get("title") or row.get("headline") or "",
        summary=row.get("summary"),
        body=row.get("body"),
        source=row.get("source"),
        url=row.get("url"),
        published_at=row.get("published_at"),
        ticker=ticker,
        tickers=tickers,
        category=category,
        relevance=_clean_string((relevance or {}).get("event_type")) or category,
        grade=(snapshot or {}).get("grade") or position.get("risk_grade"),
        previous_grade=(snapshot or {}).get("previous_grade")
        or position.get("previous_grade"),
        current_grade=(snapshot or {}).get("grade") or position.get("risk_grade"),
        factored=bool(row.get("analysis_run_id")),
        impact=(relevance or {}).get("why_it_matters") or row.get("summary"),
        held_shares=position.get("shares") if position else None,
        position_id=position.get("id") if position else None,
        analysis_run_id=str(row.get("analysis_run_id") or "") or None,
    )


def _ticker_cache_story(
    row: dict[str, Any],
    *,
    held_tickers: set[str],
    watchlist_tickers: set[str],
    alerts_by_ticker: dict[str, list[dict[str, Any]]],
    positions_by_ticker: dict[str, dict[str, Any]],
    snapshots_by_ticker: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ticker = _clean_string(row.get("ticker")).upper() or None
    category = _story_category(
        ticker=ticker,
        held_tickers=held_tickers,
        watchlist_tickers=watchlist_tickers,
        source_type="ticker_news_cache",
        relevance=None,
        alerts_by_ticker=alerts_by_ticker,
    )
    position = positions_by_ticker.get(ticker or "", {})
    snapshot = snapshots_by_ticker.get(ticker or "", {})
    sentiment = _clean_string(row.get("sentiment")).lower() or None
    relevance_label = (
        "high" if category in {"portfolio", "major"} else sentiment or "medium"
    )
    tickers = [ticker] if ticker else []

    title = row.get("headline") or row.get("title") or ""
    summary = row.get("summary")
    impact = (
        summary or (snapshot or {}).get("reasoning") or (position or {}).get("summary")
    )

    return _base_story(
        source_table="ticker_news",
        source_id=str(row.get("id") or ""),
        title=title,
        summary=summary,
        body=summary,
        source=row.get("source"),
        url=row.get("url"),
        published_at=row.get("published_at"),
        ticker=ticker,
        tickers=tickers,
        category=category,
        relevance=relevance_label,
        grade=(snapshot or {}).get("grade") or position.get("risk_grade"),
        previous_grade=(snapshot or {}).get("previous_grade")
        or position.get("previous_grade"),
        current_grade=(snapshot or {}).get("grade") or position.get("risk_grade"),
        factored=bool(snapshot or position),
        impact=impact,
        held_shares=position.get("shares") if position else None,
        position_id=position.get("id") if position else None,
        analysis_run_id=None,
    )


def _dedupe_stories(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for story in stories:
        key = (
            _clean_string(story.get("url"))
            or _clean_string(story.get("title")).lower()
            + "|"
            + _clean_string(story.get("source")).lower()
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(story)
    return deduped


def _story_sort_key(story: dict[str, Any]) -> tuple[int, datetime]:
    return (
        _story_priority(_clean_string(story.get("category"))).__int__(),
        _parse_timestamp(story.get("published_at")),
    )


def _build_feed_state(supabase, user_id: str) -> dict[str, Any]:
    positions = (
        supabase.table("positions")
        .select("id, ticker, shares, purchase_price, current_price, archetype")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    positions_by_ticker = {
        _clean_string(position.get("ticker")).upper(): position
        for position in positions
        if _clean_string(position.get("ticker"))
    }

    watchlist = get_or_create_default_watchlist(supabase, user_id)
    watchlist_items = (
        supabase.table("watchlist_items")
        .select("ticker")
        .eq("watchlist_id", watchlist["id"])
        .execute()
        .data
        or []
    )
    watchlist_tickers = {
        _clean_string(item.get("ticker")).upper()
        for item in watchlist_items
        if _clean_string(item.get("ticker"))
    }

    held_tickers = set(positions_by_ticker.keys())
    tracked_tickers = sorted(held_tickers | watchlist_tickers)

    alerts = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    alerts_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for alert in alerts:
        ticker = _clean_string(alert.get("position_ticker")).upper()
        if ticker:
            alerts_by_ticker[ticker].append(alert)

    news_items = (
        supabase.table("news_items")
        .select("*")
        .eq("user_id", user_id)
        .order("published_at", desc=True)
        .limit(75)
        .execute()
        .data
        or []
    )

    ticker_news: list[dict[str, Any]] = []
    if tracked_tickers:
        ticker_news = (
            supabase.table("ticker_news_cache")
            .select("*")
            .in_("ticker", tracked_tickers)
            .order("published_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )

    snapshot_map = get_latest_risk_snapshot_map(supabase, tracked_tickers)
    history_map = get_latest_risk_snapshot_history_map(
        supabase, tracked_tickers, per_ticker=2
    )
    metadata_map = get_metadata_map(supabase, tracked_tickers)

    stories: list[dict[str, Any]] = []
    for row in news_items:
        stories.append(
            _news_item_story(
                row,
                held_tickers=held_tickers,
                watchlist_tickers=watchlist_tickers,
                alerts_by_ticker=alerts_by_ticker,
                positions_by_ticker=positions_by_ticker,
                snapshots_by_ticker={
                    ticker: {
                        **(history[0] if history else {}),
                        "previous_grade": history[1].get("grade")
                        if len(history) > 1
                        else None,
                    }
                    for ticker, history in history_map.items()
                },
            )
        )

    for row in ticker_news:
        ticker = _clean_string(row.get("ticker")).upper()
        history = history_map.get(ticker, [])
        snapshot = snapshot_map.get(ticker, {})
        if snapshot:
            snapshot = {
                **snapshot,
                "previous_grade": history[1].get("grade") if len(history) > 1 else None,
            }
        stories.append(
            _ticker_cache_story(
                row,
                held_tickers=held_tickers,
                watchlist_tickers=watchlist_tickers,
                alerts_by_ticker=alerts_by_ticker,
                positions_by_ticker=positions_by_ticker,
                snapshots_by_ticker={ticker: snapshot} if ticker else {},
            )
        )

    stories = _dedupe_stories(stories)
    stories.sort(key=_story_sort_key, reverse=True)

    counts = {
        "portfolio": sum(
            1 for story in stories if story.get("category") == "portfolio"
        ),
        "watchlist": sum(
            1 for story in stories if story.get("category") == "watchlist"
        ),
        "market": sum(1 for story in stories if story.get("category") == "market"),
        "major": sum(1 for story in stories if story.get("category") == "major"),
    }

    hero_story = None
    for story in stories:
        if story.get("category") in {"major", "portfolio"}:
            hero_story = story
            break
    if hero_story is None and stories:
        hero_story = stories[0]

    return {
        "hero_story": hero_story,
        "stories": stories,
        "counts": counts,
        "updated_at": _utcnow_iso(),
        "positions": positions,
        "watchlist_tickers": sorted(watchlist_tickers),
        "metadata": metadata_map,
        "snapshot_map": snapshot_map,
        "history_map": history_map,
        "alerts_by_ticker": alerts_by_ticker,
    }


def build_news_feed_bundle(supabase, user_id: str, limit: int = 30) -> dict[str, Any]:
    state = _build_feed_state(supabase, user_id)
    state["stories"] = state["stories"][:limit]
    return {
        "hero_story": state["hero_story"],
        "stories": state["stories"],
        "counts": state["counts"],
        "updated_at": state["updated_at"],
        "message": "ok",
    }


def _find_row_by_id(supabase, table: str, record_id: str) -> dict[str, Any] | None:
    result = (
        supabase.table(table).select("*").eq("id", record_id).limit(1).execute().data
        or []
    )
    return result[0] if result else None


def _resolve_article_record(
    supabase, article_id: str
) -> tuple[str, dict[str, Any] | None]:
    raw_id = _clean_string(article_id)
    if ":" in raw_id:
        prefix, record_id = raw_id.split(":", 1)
        if prefix == "news_item":
            return "news_item", _find_row_by_id(supabase, "news_items", record_id)
        if prefix == "ticker_news":
            return "ticker_news", _find_row_by_id(
                supabase, "ticker_news_cache", record_id
            )

    row = _find_row_by_id(supabase, "news_items", raw_id)
    if row:
        return "news_item", row
    row = _find_row_by_id(supabase, "ticker_news_cache", raw_id)
    if row:
        return "ticker_news", row
    return "", None


def get_news_article_bundle(supabase, user_id: str, article_id: str) -> dict[str, Any]:
    source_table, row = _resolve_article_record(supabase, article_id)
    if not row:
        return {"article": None, "related_alerts": [], "message": "Article not found"}

    state = _build_feed_state(supabase, user_id)
    positions_by_ticker = {
        _clean_string(position.get("ticker")).upper(): position
        for position in state["positions"]
        if _clean_string(position.get("ticker"))
    }
    held_tickers = set(positions_by_ticker.keys())
    watchlist_tickers = set(state["watchlist_tickers"])
    alerts_by_ticker = state["alerts_by_ticker"]
    snapshot_map = state["snapshot_map"]
    history_map = state["history_map"]

    ticker = _clean_string(row.get("ticker")).upper() or None
    position = positions_by_ticker.get(ticker or "", {})
    snapshot = snapshot_map.get(ticker or "", {})
    history = history_map.get(ticker or "", [])
    previous_grade = history[1].get("grade") if len(history) > 1 else None
    current_grade = snapshot.get("grade") or position.get("risk_grade")

    if source_table == "news_item":
        relevance = (
            row.get("relevance") if isinstance(row.get("relevance"), dict) else {}
        )
        article = _base_story(
            source_table="news_item",
            source_id=str(row.get("id") or ""),
            title=row.get("title") or row.get("headline") or "",
            summary=row.get("summary"),
            body=row.get("body"),
            source=row.get("source"),
            url=row.get("url"),
            published_at=row.get("published_at"),
            ticker=ticker,
            tickers=_clean_string_list(row.get("affected_tickers")),
            category=_story_category(
                ticker=ticker,
                held_tickers=held_tickers,
                watchlist_tickers=watchlist_tickers,
                source_type="news_items",
                relevance=relevance,
                alerts_by_ticker=alerts_by_ticker,
            ),
            relevance=_clean_string((relevance or {}).get("event_type")) or "portfolio",
            grade=current_grade,
            previous_grade=previous_grade,
            current_grade=current_grade,
            factored=bool(row.get("analysis_run_id")),
            impact=(relevance or {}).get("why_it_matters") or row.get("summary"),
            held_shares=position.get("shares") if position else None,
            position_id=position.get("id") if position else None,
            analysis_run_id=str(row.get("analysis_run_id") or "") or None,
        )
    else:
        article = _ticker_cache_story(
            row,
            held_tickers=held_tickers,
            watchlist_tickers=watchlist_tickers,
            alerts_by_ticker=alerts_by_ticker,
            positions_by_ticker=positions_by_ticker,
            snapshots_by_ticker={ticker: {**snapshot, "previous_grade": previous_grade}}
            if ticker
            else {},
        )

    related_alerts = (
        state["alerts_by_ticker"].get(ticker or "", [])[:5] if ticker else []
    )
    return {
        "article": article,
        "related_alerts": related_alerts,
        "message": "ok",
    }
