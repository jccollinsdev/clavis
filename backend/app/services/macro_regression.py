from __future__ import annotations

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

FACTOR_TICKERS = {
    "tnx": "I:TNX",
    "dxy": "UUP",
    "wti": "USO",
    "vix": "I:VIX",
    "spy": "SPY",
}

_REQUIRED_TRADING_DAYS = 60
_TRAILING_DAYS = 252


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _ols(X: list[list[float]], y: list[float]) -> tuple[list[float], float]:
    """Pure-Python OLS regression via normal equations (X^T X)^(-1) X^T y.

    Returns (coefficients, r_squared).
    Falls back to beta-only if matrix is singular.
    """
    n = len(y)
    if n < 5 or len(X) == 0:
        return [0.0] * len(X[0]) if X else [], 0.0

    p = len(X[0])

    XtX = [[0.0] * p for _ in range(p)]
    Xty = [0.0] * p

    mean_y = _mean(y)
    means_x = [_mean([X[i][j] for i in range(n)]) for j in range(p)]

    for i in range(n):
        for j in range(p):
            x_cent = X[i][j] - means_x[j]
            Xty[j] += x_cent * (y[i] - mean_y)
            for k in range(p):
                XtX[j][k] += x_cent * (X[i][k] - means_x[k])

    beta = _solve_linear(XtX, Xty)

    ss_res = 0.0
    ss_tot = 0.0
    for i in range(n):
        pred = sum(beta[j] * X[i][j] for j in range(p))
        ss_res += (y[i] - pred) ** 2
        ss_tot += (y[i] - mean_y) ** 2

    r_sq = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return beta, max(0.0, min(1.0, r_sq))


def _solve_linear(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting."""
    n = len(A)
    aug = [A[i][:] + [b[i]] for i in range(n)]

    for col in range(n):
        max_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[max_row][col]) < 1e-12:
            continue
        aug[col], aug[max_row] = aug[max_row], aug[col]
        pivot = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= pivot
        for row in range(n):
            if row != col:
                factor = aug[row][col]
                for j in range(col, n + 1):
                    aug[row][j] -= factor * aug[col][j]

    return [aug[i][n] for i in range(n)]


def _daily_returns(prices: list[float]) -> list[float]:
    if len(prices) < 2:
        return []
    return [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]


def _price_to_change(prices: list[float]) -> list[float]:
    if len(prices) < 2:
        return []
    return [prices[i] - prices[i - 1] for i in range(1, len(prices))]


def _parse_polygon_close(bars: list[dict]) -> list[tuple[str, float]]:
    result: list[tuple[str, float]] = []
    for bar in bars or []:
        date = str(bar.get("t") or "")
        close = bar.get("c")
        if date and close is not None:
            try:
                result.append((date, float(close)))
            except (ValueError, TypeError):
                continue
    result.sort(key=lambda x: x[0])
    return result


def _dates_from_bars(bars: list[dict]) -> list[str]:
    dates: list[str] = []
    for bar in bars or []:
        date = str(bar.get("t") or "")
        if date:
            dates.append(date)
    return sorted(set(dates))


def _align_series(
    ticker_returns: list[tuple[str, float]],
    factor_returns: dict[str, list[tuple[str, float]]],
) -> tuple[list[list[float]], list[float]]:
    all_dates = sorted(set(ticker_returns.keys() if isinstance(ticker_returns, dict) else [d for d, _ in ticker_returns]) & {
        d for f in factor_returns.get("spy", []) for d, _ in [f]
    })

    _ticker_map = {d: v for d, v in ticker_returns} if not isinstance(ticker_returns, dict) else ticker_returns
    _factor_maps = {}
    for name, series in factor_returns.items():
        _factor_maps[name] = {d: v for d, v in series}

    X: list[list[float]] = []
    y: list[float] = []
    factor_order = ["tnx", "dxy", "wti", "vix", "spy"]

    common_dates = sorted(all_dates)
    for date in common_dates:
        row = []
        for factor in factor_order:
            fm = _factor_maps.get(factor, {})
            row.append(fm.get(date, 0.0))
        if all(v == 0.0 for v in row):
            continue
        tk_val = _ticker_map.get(date, 0.0)
        y.append(tk_val)
        X.append(row)

    return X, y


def _sensitivity_score(
    coefficients: dict[str, float],
    r_squared: float,
) -> float:
    """Convert regression coefficients to a 0-100 score using sqrt normalization.

    sensitivity = sqrt(sum(coef_i^2 for all factors))
    Score = 100 * (1 - sensitivity / observed_max)
    where observed_max = 5.0 (calibrated; covers typical S&P 500 stock range)

    100 = zero macro sensitivity (best)
    0 = maximum macro sensitivity (worst)
    """
    OBSERVED_MAX = 5.0
    sensitivity = math.sqrt(sum(v ** 2 for v in coefficients.values()))
    normalized = sensitivity / OBSERVED_MAX
    score = 100.0 * (1.0 - min(1.0, normalized))
    return round(max(0.0, min(100.0, score)), 1)


def run_macro_regression(
    ticker: str,
    ticker_bars: list[dict],
    factor_bars_map: dict[str, list[dict]],
    *,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    if as_of_date is None:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ticker_prices = _parse_polygon_close(ticker_bars)
    if len(ticker_prices) < _REQUIRED_TRADING_DAYS:
        return {
            "limited_data": True,
            "trading_days_available": len(ticker_prices),
            "as_of_date": as_of_date,
            "message": "Insufficient trading days for regression",
        }

    ticker_price_list = [p for _, p in ticker_prices[-_TRAILING_DAYS:]]
    ticker_returns = _daily_returns(ticker_price_list)

    factor_returns: dict[str, list[tuple[str, float]]] = {}
    for factor_key, factor_ticker in FACTOR_TICKERS.items():
        factor_bars = factor_bars_map.get(factor_key, [])
        factor_prices = _parse_polygon_close(factor_bars)
        if factor_key in ("tnx", "dxy", "vix"):
            factor_changes = _price_to_change([p for _, p in factor_prices[-_TRAILING_DAYS:]])
            factor_returns[factor_key] = [
                (factor_prices[i + 1][0], factor_changes[i])
                for i in range(min(len(factor_changes), len(ticker_returns)))
            ]
        else:
            factor_price_list = [p for _, p in factor_prices[-_TRAILING_DAYS:]]
            factor_ret = _daily_returns(factor_price_list)
            factor_returns[factor_key] = [
                (factor_prices[i + 1][0], factor_ret[i])
                for i in range(min(len(factor_ret), len(ticker_returns)))
            ]

    n = min(len(ticker_returns), *(len(fr) for fr in factor_returns.values()))
    if n < _REQUIRED_TRADING_DAYS:
        return {
            "limited_data": True,
            "trading_days_available": n,
            "as_of_date": as_of_date,
            "message": "Insufficient aligned trading days across factors",
        }

    y = ticker_returns[:n]
    factor_order = ["tnx", "dxy", "wti", "vix", "spy"]
    X = [[factor_returns[fk][i][1] for fk in factor_order] for i in range(n)]

    beta, r_sq = _ols(X, y)
    coefficients = {factor_order[i]: round(beta[i], 6) for i in range(len(factor_order))}

    sensitivity = _sensitivity_score(coefficients, r_sq)

    return {
        "limited_data": False,
        "coefficients": coefficients,
        "r_squared": round(r_sq, 4),
        "sensitivity_score": sensitivity,
        "trading_days_used": n,
        "as_of_date": as_of_date,
        "factor_tickers": FACTOR_TICKERS,
    }


def macro_regression_to_audit_jsonb(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "macro_regression": {
            "coefficients": result.get("coefficients", {}),
            "r_squared": result.get("r_squared"),
            "as_of_date": result.get("as_of_date"),
            "trading_days_used": result.get("trading_days_used", 0),
            "limited_data": result.get("limited_data", False),
            "factor_tickers": FACTOR_TICKERS,
        }
    }
