from __future__ import annotations

from datetime import datetime, timezone
import os
import re
from typing import Any

from .minimax import chatcompletion_text


BANNED_VOCABULARY_BLOCK = """## Banned vocabulary

| Word | Why it's banned |
|---|---|
| coverage, monitor, momentum | Reads as analyst-speak |
| analyst, research, thesis | Implies advisory product |
| provisional, current read | Hedging language |
| recommendation, suggest, advise | Advisory |
| predict, forecast | Advisory |
| Clavis, SnapTrade | Prior product names — never surface |
"""

_BANNED_PATTERNS = (
    # From system/00-rules.md "Banned vocabulary" table
    "coverage",
    "monitor",
    "momentum",
    "analyst",
    "research",
    "thesis",
    "provisional",
    "current read",
    "recommendation",
    "suggest",
    "advise",
    "predict",
    "forecast",
    "Clavis",
    "SnapTrade",
    # From "What Clavix is NOT" prose section of system/00-rules.md:
    # "No buy / sell / hold. No price targets. No earnings forecasts."
    "buy",
    "sell",
    "hold",
    "recommend",
)
_BANNED_REGEX = re.compile(
    r"\b(?:"
    + "|".join(re.escape(pattern) for pattern in _BANNED_PATTERNS)
    + r")\b",
    flags=re.IGNORECASE,
)
_NARRATIVE_CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}
_DAILY_BUDGET_SPEND: dict[str, int] = {}
_MAX_NARRATIVE_ARTICLES = 5
_MAX_NARRATIVE_CHARS = 240
_MAX_NARRATIVE_SENTENCES = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today_key(now: datetime | None = None) -> str:
    return (now or _utcnow()).date().isoformat()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value in {None, ""}:
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def _format_shares(value: Any) -> str:
    try:
        shares = float(value)
    except (TypeError, ValueError):
        return "0"
    if shares.is_integer():
        return str(int(shares))
    return f"{shares:.2f}".rstrip("0").rstrip(".")


def _format_percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}"


def _format_score(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}".rstrip("0").rstrip(".")


def _trim_narrative(text: str) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    kept = " ".join(sentences[:_MAX_NARRATIVE_SENTENCES]).strip()
    if len(kept) <= _MAX_NARRATIVE_CHARS:
        return kept
    trimmed = kept[: _MAX_NARRATIVE_CHARS].rstrip(" ,;:")
    if "." in trimmed:
        trimmed = trimmed.rsplit(".", 1)[0].rstrip(" ,;:") + "."
    return trimmed


def _latest_portfolio_snapshot_pair(
    supabase,
    user_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    rows = (
        supabase.table("portfolio_risk_snapshots")
        .select("as_of_date,composite_score")
        .eq("user_id", user_id)
        .order("as_of_date", desc=True)
        .limit(2)
        .execute()
        .data
        or []
    )
    latest = rows[0] if rows else None
    previous = rows[1] if len(rows) > 1 else None
    return latest, previous


def _position_map(supabase, user_id: str) -> dict[str, dict[str, Any]]:
    rows = (
        supabase.table("positions")
        .select("ticker,shares,current_price")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    tickers = [str(row.get("ticker") or "").upper() for row in rows if row.get("ticker")]
    metadata_rows = (
        supabase.table("ticker_metadata")
        .select("ticker,price")
        .in_("ticker", tickers)
        .execute()
        .data
        or []
    ) if tickers else []
    metadata_prices = {
        str(row.get("ticker") or "").upper(): row.get("price")
        for row in metadata_rows
        if row.get("ticker")
    }

    positions: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").upper()
        if not ticker:
            continue
        current_price = row.get("current_price")
        if current_price in {None, ""}:
            current_price = metadata_prices.get(ticker)
        positions[ticker] = {
            "ticker": ticker,
            "shares": row.get("shares"),
            "current_price": current_price,
        }
    return positions


def _event_rows(supabase, event_ids: list[str]) -> list[dict[str, Any]]:
    if not event_ids:
        return []
    rows = (
        supabase.table("shared_ticker_events")
        .select("id,ticker,title,summary,tldr,what_it_means,key_implications")
        .in_("id", event_ids)
        .execute()
        .data
        or []
    )
    order = {event_id: index for index, event_id in enumerate(event_ids)}
    return sorted(rows, key=lambda row: order.get(str(row.get("id") or ""), 10_000))


def recent_event_ids_for_tickers(
    supabase,
    tickers: list[str],
    *,
    limit: int = _MAX_NARRATIVE_ARTICLES,
) -> list[str]:
    normalized = [str(ticker or "").upper() for ticker in tickers if str(ticker or "").strip()]
    if not normalized:
        return []
    rows = (
        supabase.table("shared_ticker_events")
        .select("id,ticker,published_at")
        .in_("ticker", normalized)
        .order("published_at", desc=True)
        .limit(max(limit * 5, limit))
        .execute()
        .data
        or []
    )
    seen: set[str] = set()
    event_ids: list[str] = []
    for row in rows:
        event_id = str(row.get("id") or "")
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        event_ids.append(event_id)
        if len(event_ids) >= limit:
            break
    return event_ids


def _structural_line(
    event_row: dict[str, Any],
    *,
    position_map: dict[str, dict[str, Any]],
    latest_snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None,
) -> tuple[str, str]:
    ticker = str(event_row.get("ticker") or "").upper()
    position = position_map.get(ticker) or {}
    total_value = 0.0
    for row in position_map.values():
        try:
            shares = float(row.get("shares") or 0)
            current_price = float(row.get("current_price") or 0)
        except (TypeError, ValueError):
            continue
        total_value += shares * current_price

    weight_pct: float | None = None
    try:
        if total_value > 0 and position:
            weight_pct = (
                float(position.get("shares") or 0)
                * float(position.get("current_price") or 0)
                / total_value
                * 100.0
            )
    except (TypeError, ValueError):
        weight_pct = None

    latest_composite = latest_snapshot.get("composite_score") if latest_snapshot else None
    previous_composite = previous_snapshot.get("composite_score") if previous_snapshot else None
    structural = (
        f"You hold {_format_shares(position.get('shares'))} sh of {ticker} "
        f"({_format_percent(weight_pct)}% of book). This change moves your portfolio composite "
        f"from {_format_score(previous_composite)} → {_format_score(latest_composite)}."
    )
    composite_key = _format_score(latest_composite)
    return structural, composite_key


def _budget_available(now: datetime | None = None) -> bool:
    daily_budget = _env_int("MINIMAX_DAILY_BUDGET", 0)
    if daily_budget <= 0:
        return False
    return _DAILY_BUDGET_SPEND.get(_today_key(now), 0) < daily_budget


def _consume_budget(now: datetime | None = None) -> None:
    key = _today_key(now)
    _DAILY_BUDGET_SPEND[key] = _DAILY_BUDGET_SPEND.get(key, 0) + 1


def _generate_narrative(
    *,
    event_row: dict[str, Any],
    structural: str,
) -> str | None:
    if not _env_flag("MINIMAX_PERSONALISATION_ENABLED", default=False):
        return None
    if not _budget_available():
        return None

    prompt = "\n".join(
        [
            "Write one short Clavix personalised article note.",
            BANNED_VOCABULARY_BLOCK,
            "Rules:",
            "- Informational only. No advice, no forecasts, no recommendations.",
            "- Rating-agency tone. Calm, direct, observational.",
            "- Maximum 3 sentences and 240 characters.",
            "- Start from the structural portfolio context below, then add only article-specific context.",
            f"Structural context: {structural}",
            f"Headline: {event_row.get('title') or 'Unknown headline'}",
            f"Summary: {event_row.get('summary') or ''}",
            f"TLDR: {event_row.get('tldr') or ''}",
            f"What it means: {event_row.get('what_it_means') or ''}",
            f"Key implications: {', '.join(event_row.get('key_implications') or [])}",
        ]
    )
    try:
        narrative = chatcompletion_text(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write concise Clavix article personalisation blurbs. "
                        "Stay informational and portfolio-specific.\n\n"
                        + BANNED_VOCABULARY_BLOCK
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=180,
        )
    except Exception:
        return None

    narrative = _trim_narrative(narrative)
    if not narrative or _BANNED_REGEX.search(narrative):
        return None
    _consume_budget()
    return narrative


def personalise_articles_for_user(
    user_id: str,
    event_ids: list[str],
    *,
    supabase,
) -> dict[str, dict[str, str | None]]:
    latest_snapshot, previous_snapshot = _latest_portfolio_snapshot_pair(supabase, user_id)
    position_map = _position_map(supabase, user_id)
    generated_at = _utcnow().isoformat()
    results: dict[str, dict[str, str | None]] = {}

    llm_eligible_ids = set(event_ids[:_MAX_NARRATIVE_ARTICLES])
    for event_row in _event_rows(supabase, event_ids):
        event_id = str(event_row.get("id") or "")
        if not event_id:
            continue
        structural, composite_key = _structural_line(
            event_row,
            position_map=position_map,
            latest_snapshot=latest_snapshot,
            previous_snapshot=previous_snapshot,
        )
        cache_key = (user_id, event_id, composite_key)
        cached = _NARRATIVE_CACHE.get(cache_key)
        if cached is not None:
            results[event_id] = cached
            continue

        narrative = None
        if event_id in llm_eligible_ids:
            narrative = _generate_narrative(
                event_row=event_row,
                structural=structural,
            )
        payload = {
            "structural": structural,
            "narrative": narrative,
            "generated_at": generated_at,
        }
        _NARRATIVE_CACHE[cache_key] = payload
        results[event_id] = payload

    return results


def latest_personalised_articles_for_user(
    supabase,
    user_id: str,
) -> dict[str, dict[str, Any]]:
    rows = (
        supabase.table("digests")
        .select("structured_sections,generated_at")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    sections = ((rows[0] if rows else {}).get("structured_sections") or {}) if rows else {}
    personalisation = sections.get("personalised_articles") if isinstance(sections, dict) else {}
    return personalisation if isinstance(personalisation, dict) else {}


def attach_latest_personalisation(
    supabase,
    *,
    user_id: str,
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    personalisation = latest_personalised_articles_for_user(supabase, user_id)
    attached: list[dict[str, Any]] = []
    for article in articles:
        event_id = str(article.get("id") or "")
        payload = personalisation.get(event_id) if event_id else None
        if isinstance(payload, dict):
            attached.append(
                {
                    **article,
                    "personalised_structural": payload.get("structural"),
                    "personalised_narrative": payload.get("narrative"),
                    "personalised_generated_at": payload.get("generated_at"),
                }
            )
        else:
            attached.append(article)
    return attached
