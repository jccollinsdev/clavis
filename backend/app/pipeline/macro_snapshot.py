"""Daily macro factor snapshot job.

Captures daily levels of the macro factors that CLAVIX_TRUTH §6 uses for the
Macro Exposure dimension and for the digest "Overnight Macro" prose:

- TLT  → 20+ year Treasury bond ETF (10Y rate proxy via inverse)
- UUP  → US dollar index ETF
- USO  → WTI crude ETF
- VIXY → short-term VIX futures ETF (VIX-level proxy)
- SPY  → S&P 500 ETF (beta reference)

Writes one row per (as_of_date) into `macro_regime_snapshots`.

Usage:
    from app.pipeline.macro_snapshot import refresh_macro_snapshot
    refresh_macro_snapshot()
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..services.polygon import fetch_aggs
from ..services.supabase import get_supabase

logger = logging.getLogger(__name__)

# Polygon doesn't surface yields or the raw VIX index on the basic plan; we
# use ETF proxies whose daily aggregates are reliably available.
MACRO_FACTORS: dict[str, str] = {
    "ust10y": "TLT",
    "dxy":    "UUP",
    "wti":    "USO",
    "vix":    "VIXY",
    "spy":    "SPY",
}


def _latest_close_and_change(ticker: str) -> tuple[float | None, float | None, float | None, str | None]:
    """Return (close, day_change_amount, day_change_pct, snapshot_date)."""
    bars = fetch_aggs(ticker, days=7) or []
    if not bars:
        return (None, None, None, None)
    latest = bars[-1]
    prior = bars[-2] if len(bars) >= 2 else bars[-1]
    close = latest.get("c")
    prev_close = prior.get("c")
    try:
        amount = float(close) - float(prev_close)
        pct = (amount / float(prev_close)) * 100.0 if prev_close else None
    except (TypeError, ValueError):
        amount = None
        pct = None

    ts = latest.get("t")
    if isinstance(ts, int):
        snapshot_date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
    else:
        snapshot_date = datetime.now(timezone.utc).date().isoformat()
    return (close, amount, pct, snapshot_date)


def _regime_from_signals(spy_pct: float | None, vix_close: float | None) -> str:
    """Cheap heuristic regime label until a richer classifier ships."""
    if spy_pct is None or vix_close is None:
        return "unknown"
    if vix_close > 25 and spy_pct < -1.0:
        return "risk_off"
    if vix_close < 15 and spy_pct >= 0:
        return "risk_on"
    return "neutral"


def refresh_macro_snapshot() -> bool:
    """Pull macro factor levels and upsert today's `macro_regime_snapshots` row."""
    supabase = get_supabase()

    values: dict[str, tuple[float | None, float | None, float | None, str | None]] = {}
    snapshot_date: str | None = None
    for code, etf in MACRO_FACTORS.items():
        try:
            close, amount, pct, dt = _latest_close_and_change(etf)
            values[code] = (close, amount, pct, dt)
            snapshot_date = snapshot_date or dt
        except Exception:
            logger.exception("Failed to pull %s (%s)", code, etf)
            values[code] = (None, None, None, None)

    if snapshot_date is None:
        logger.warning("No macro data returned by any factor; aborting snapshot")
        return False

    spy_pct = values["spy"][2]
    vix_close = values["vix"][0]
    regime = _regime_from_signals(spy_pct, vix_close)

    row = {
        "as_of_date":         snapshot_date,
        "regime_state":       regime,
        "vix_level":          values["vix"][0],
        "vix_day_change":     values["vix"][1],
        "ust10y_level":       values["ust10y"][0],
        "ust10y_day_change":  values["ust10y"][1],
        "dxy_level":          values["dxy"][0],
        "dxy_day_change":     values["dxy"][1],
        "wti_level":          values["wti"][0],
        "wti_day_change":     values["wti"][1],
        "spy_close":          values["spy"][0],
        "spy_day_change_pct": values["spy"][2],
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "data_status":        "price_only",
    }

    existing = (
        supabase.table("macro_regime_snapshots")
        .select("id")
        .eq("as_of_date", snapshot_date)
        .limit(1)
        .execute()
        .data
    )
    try:
        if existing:
            supabase.table("macro_regime_snapshots") \
                .update(row) \
                .eq("id", existing[0]["id"]) \
                .execute()
        else:
            supabase.table("macro_regime_snapshots").insert(row).execute()
    except Exception:
        logger.exception("Failed to write macro snapshot for %s", snapshot_date)
        return False
    logger.info("refresh_macro_snapshot wrote row for %s (regime=%s)", snapshot_date, regime)
    return True
