from __future__ import annotations

from datetime import date, datetime
import io
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
import zipfile

import requests

from app.services.supabase import get_supabase


logger = logging.getLogger(__name__)

ETF_STATIC_SEEDS: dict[str, list[tuple[str, float]]] = {
    "SPY": [("AAPL", 7.1), ("MSFT", 6.8), ("NVDA", 6.2), ("AMZN", 3.8), ("META", 2.9), ("AVGO", 2.2), ("GOOGL", 2.1), ("GOOG", 1.8), ("BRK.B", 1.7), ("TSLA", 1.6)],
    "QQQ": [("NVDA", 9.2), ("MSFT", 8.1), ("AAPL", 7.9), ("AMZN", 5.2), ("AVGO", 4.6), ("META", 4.2), ("NFLX", 2.7), ("COST", 2.6), ("GOOGL", 2.5), ("GOOG", 2.4)],
    "VTI": [("AAPL", 6.2), ("MSFT", 5.8), ("NVDA", 5.4), ("AMZN", 3.2), ("META", 2.5), ("AVGO", 1.9), ("GOOGL", 1.8), ("GOOG", 1.6), ("BRK.B", 1.5), ("TSLA", 1.4)],
}
TOP_HOLDINGS_LIMIT = 10
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
VANGUARD_PORT_IDS = {"VTI": "0970"}
INVESCO_HOLDINGS_URL = (
    "https://dng-api.invesco.com/cache/v1/accounts/en_US/shareclasses/{ticker}/holdings/fund"
    "?idType=ticker&interval=monthly&productType=ETF&loadType=initial"
)
SSGA_SPY_XLSX_URL = (
    "https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx"
)
VANGUARD_HOLDINGS_URL = (
    "https://advisors.vanguard.com/investments/products/holdings/latest/{port_id}"
)


def _active_etfs(supabase) -> list[str]:
    tickers: set[str] = set()
    for table in ("positions", "watchlist_items"):
        for row in supabase.table(table).select("ticker").execute().data or []:
            ticker = str(row.get("ticker") or "").upper()
            if ticker in ETF_STATIC_SEEDS:
                tickers.add(ticker)
    return sorted(tickers)


def _rows_for_holdings(
    ticker: str,
    holdings: list[tuple[str, float]],
    *,
    as_of: str,
    source: str,
) -> list[dict[str, Any]]:
    return [
        {
            "etf_ticker": ticker.upper(),
            "holding_ticker": holding,
            "weight_pct": weight,
            "rank": index + 1,
            "source": source,
            "as_of": as_of,
        }
        for index, (holding, weight) in enumerate(holdings[:TOP_HOLDINGS_LIMIT])
    ]


def _fallback_rows(ticker: str, as_of: str | None = None) -> list[dict[str, Any]]:
    return _rows_for_holdings(
        ticker,
        ETF_STATIC_SEEDS.get(ticker.upper(), []),
        as_of=as_of or date.today().isoformat(),
        source="static_seed",
    )


def _parse_xlsx_rows(content: bytes) -> list[list[str]]:
    workbook = zipfile.ZipFile(io.BytesIO(content))
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared_strings: list[str] = []
    if "xl/sharedStrings.xml" in workbook.namelist():
        root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        for item in root.findall("a:si", ns):
            shared_strings.append("".join(node.text or "" for node in item.findall(".//a:t", ns)))

    sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
    rows: list[list[str]] = []
    for row in sheet.findall(".//a:sheetData/a:row", ns):
        values: list[str] = []
        for cell in row.findall("a:c", ns):
            cell_type = cell.attrib.get("t")
            raw = cell.find("a:v", ns)
            text = raw.text if raw is not None else ""
            if cell_type == "s" and text:
                text = shared_strings[int(text)]
            values.append(text)
        rows.append(values)
    return rows


def _fetch_ssga_holdings(ticker: str) -> list[dict[str, Any]]:
    if ticker.upper() != "SPY":
        return []
    response = requests.get(SSGA_SPY_XLSX_URL, timeout=20, headers=REQUEST_HEADERS)
    if response.status_code != 200:
        return []

    rows = _parse_xlsx_rows(response.content)
    as_of = date.today().isoformat()
    holdings_started = False
    holdings: list[tuple[str, float]] = []
    for row in rows:
        if len(row) >= 2 and row[0] == "Holdings:":
            match = re.search(r"As of (\d{1,2}-[A-Za-z]{3}-\d{4})", row[1] or "")
            if match:
                as_of = datetime.strptime(match.group(1), "%d-%b-%Y").date().isoformat()
        elif row[:5] == ["Name", "Ticker", "Identifier", "SEDOL", "Weight"]:
            holdings_started = True
        elif holdings_started:
            if len(row) < 5 or not row[1]:
                break
            try:
                holdings.append((str(row[1]).upper(), float(row[4])))
            except (TypeError, ValueError):
                continue
            if len(holdings) >= TOP_HOLDINGS_LIMIT:
                break

    return _rows_for_holdings(ticker, holdings, as_of=as_of, source="ssga")


def _fetch_invesco_holdings(ticker: str) -> list[dict[str, Any]]:
    if ticker.upper() != "QQQ":
        return []
    response = requests.get(
        INVESCO_HOLDINGS_URL.format(ticker=ticker.upper()),
        timeout=20,
        headers=REQUEST_HEADERS,
    )
    if response.status_code != 200:
        return []
    payload = response.json() or {}
    as_of = payload.get("effectiveDate") or payload.get("effectiveBusinessDate") or date.today().isoformat()
    holdings = []
    for item in payload.get("holdings") or []:
        holding_ticker = str(item.get("ticker") or "").upper()
        try:
            weight = float(item.get("percentageOfTotalNetAssets"))
        except (TypeError, ValueError):
            continue
        if holding_ticker:
            holdings.append((holding_ticker, weight))
        if len(holdings) >= TOP_HOLDINGS_LIMIT:
            break
    return _rows_for_holdings(ticker, holdings, as_of=as_of, source="invesco")


def _fetch_vanguard_holdings(ticker: str) -> list[dict[str, Any]]:
    port_id = VANGUARD_PORT_IDS.get(ticker.upper())
    if not port_id:
        return []
    response = requests.get(
        VANGUARD_HOLDINGS_URL.format(port_id=port_id),
        timeout=20,
        headers={**REQUEST_HEADERS, "X-Consumer-ID": "FPP"},
    )
    if response.status_code != 200:
        return []
    payload = response.json() or {}
    as_of = payload.get("latestEffectiveDate") or date.today().isoformat()
    daily_payload = payload.get(as_of) or {}
    holdings = []
    for item in daily_payload.get("equity") or []:
        holding_ticker = str(item.get("ticker") or "").upper()
        try:
            weight = float(item.get("percentOfFunds"))
        except (TypeError, ValueError):
            continue
        if holding_ticker:
            holdings.append((holding_ticker, weight))
        if len(holdings) >= TOP_HOLDINGS_LIMIT:
            break
    return _rows_for_holdings(ticker, holdings, as_of=as_of, source="vanguard")


def _fetch_live_rows(ticker: str) -> list[dict[str, Any]]:
    upper = ticker.upper()
    if upper == "SPY":
        return _fetch_ssga_holdings(upper)
    if upper == "QQQ":
        return _fetch_invesco_holdings(upper)
    if upper == "VTI":
        return _fetch_vanguard_holdings(upper)
    return []


def run() -> dict[str, Any]:
    supabase = get_supabase()
    all_rows: list[dict[str, Any]] = []
    for ticker in _active_etfs(supabase):
        rows = _fetch_live_rows(ticker)
        if not rows:
            logger.warning("ETF holdings fetch returned empty for %s; using static seed fallback", ticker)
            rows = _fallback_rows(ticker)
        all_rows.extend(rows)

    if all_rows:
        supabase.table("etf_holdings").upsert(
            all_rows,
            on_conflict="etf_ticker,holding_ticker,as_of",
        ).execute()
    return {
        "status": "completed",
        "items_processed": len(all_rows),
        "metadata": {"etfs": sorted({row["etf_ticker"] for row in all_rows})},
    }


def run_from_env() -> dict[str, Any]:
    return run()
