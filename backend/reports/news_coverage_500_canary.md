# Finnhub-First 500-Ticker News Coverage Canary
*Generated: 2026-05-17 19:17 UTC*

## Executive Summary

| Metric | Value |
|--------|-------|
| Tickers processed | 504 |
| SCORED (≥3 usable) | 397 / 504 (78.8%) |
| Production threshold (≥10 usable) | 57 / 504 (11.3%) |
| Finnhub 429s | 0 |
| Extraction success rate | 88.5% |
| Google fallback used | 0 tickers |

## Safety Status
- ✅ News coverage canary only — no risk snapshots promoted
- ✅ skip_existing=True — no valid enriched articles overwritten
- ✅ Finnhub-first: Google used only as fallback for <3 usable

## Distribution Stats

| Statistic | Value |
|-----------|-------|
| Min usable | 0 |
| Max usable | 75 |
| Mean | 6.0 |
| Median | 5.0 |
| Std Dev | 7.1 |
| p10 | 1.0 |
| p25 | 3.0 |
| p75 | 7.0 |
| p90 | 10.0 |

## Histogram

| Bucket | Count | % |
|--------|-------|---|
| 0 usable | 23 | 4.6% |
| 1–2 usable | 84 | 16.7% |
| 3–4 usable | 124 | 24.6% |
| 5–9 usable | 216 | 42.9% |
| 10–19 usable | 44 | 8.7% |
| 20+ usable | 13 | 2.6% |

## Threshold Coverage

| Threshold | Count | % |
|-----------|-------|---|
| ≥3 usable (MVP) | 397 | 78.8% |
| ≥5 usable | 273 | 54.2% |
| ≥10 usable (production ideal) | 57 | 11.3% |
| ≥20 usable | 13 | 2.6% |

## Bottom 50 Tickers (by usable_7d)

| ticker | company | sector | fh_raw | relevant | extracted | usable_7d | status | top_failure |
|--------|---------|--------|--------|----------|-----------|-----------|--------|-------------|
| GRMN | Garmin | Consumer Discre | 2 | 2 | 2 | 0 | limited_data | low_finnhub_supply |
| HUBB | Hubbell Incorporated | Industrials | 2 | 2 | 2 | 0 | limited_data | low_finnhub_supply |
| L | Loews Corporation | Financials | 1 | 1 | 1 | 0 | limited_data | low_finnhub_supply |
| MNST | Monster Beverage | Consumer Staple | 15 | 9 | 8 | 0 | limited_data | enrichment_incomplete |
| MSCI | MSCI Inc. | Financials | 7 | 7 | 6 | 0 | limited_data | enrichment_incomplete |
| MTD | Mettler Toledo | Health Care | 9 | 9 | 8 | 0 | limited_data | enrichment_incomplete |
| NCLH | Norwegian Cruise Lin | Consumer Discre | 32 | 10 | 10 | 0 | limited_data | enrichment_incomplete |
| NI | NiSource | Utilities | 7 | 7 | 7 | 0 | limited_data | enrichment_incomplete |
| NTAP | NetApp | Information Tec | 10 | 10 | 10 | 0 | limited_data | enrichment_incomplete |
| PAYX | Paychex | Industrials | 4 | 4 | 3 | 0 | limited_data | low_finnhub_supply |
| PGR | Progressive Corporat | Financials | 16 | 10 | 10 | 0 | limited_data | enrichment_incomplete |
| PHM | PulteGroup | Consumer Discre | 2 | 2 | 2 | 0 | limited_data | low_finnhub_supply |
| PLD | Prologis | Real Estate | 15 | 10 | 8 | 0 | limited_data | enrichment_incomplete |
| PPG | PPG Industries | Materials | 1 | 1 | 1 | 0 | limited_data | low_finnhub_supply |
| PPL | PPL Corporation | Utilities | 9 | 9 | 8 | 0 | limited_data | enrichment_incomplete |
| PSA | Public Storage | Real Estate | 2 | 2 | 1 | 0 | limited_data | low_finnhub_supply |
| PSX | Phillips 66 | Energy | 17 | 10 | 9 | 0 | limited_data | enrichment_incomplete |
| PYPL | PayPal | Financials | 55 | 10 | 8 | 0 | limited_data | enrichment_incomplete |
| Q | Qnity Electronics | Information Tec | 38 | 10 | 9 | 0 | limited_data | enrichment_incomplete |
| RL | Ralph Lauren Corpora | Consumer Discre | 14 | 10 | 10 | 0 | limited_data | enrichment_incomplete |
| ROL | Rollins, Inc. | Industrials | 14 | 10 | 8 | 0 | limited_data | enrichment_incomplete |
| RSG | Republic Services | Industrials | 11 | 10 | 8 | 0 | limited_data | enrichment_incomplete |
| SHW | Sherwin-Williams | Materials | 8 | 8 | 7 | 0 | limited_data | enrichment_incomplete |
| BF.B | Brown–Forman | Consumer Staple | 5 | 5 | 5 | 1 | limited_data | enrichment_incomplete |
| BKNG | Booking Holdings | Consumer Discre | 23 | 10 | 9 | 1 | limited_data | enrichment_incomplete |
| GNRC | Generac | Industrials | 7 | 7 | 5 | 1 | limited_data | enrichment_incomplete |
| IEX | IDEX Corporation | Industrials | 4 | 4 | 2 | 1 | limited_data | low_finnhub_supply |
| INCY | Incyte | Health Care | 4 | 4 | 3 | 1 | limited_data | low_finnhub_supply |
| ISRG | Intuitive Surgical | Health Care | 24 | 10 | 10 | 1 | limited_data | enrichment_incomplete |
| LH | Labcorp | Health Care | 10 | 10 | 9 | 1 | limited_data | enrichment_incomplete |
| LII | Lennox International | Industrials | 4 | 4 | 3 | 1 | limited_data | low_finnhub_supply |
| LUV | Southwest Airlines | Industrials | 27 | 10 | 10 | 1 | limited_data | enrichment_incomplete |
| NEM | Newmont | Materials | 39 | 10 | 9 | 1 | limited_data | enrichment_incomplete |
| NOW | ServiceNow | Information Tec | 58 | 10 | 10 | 1 | limited_data | enrichment_incomplete |
| OKE | Oneok | Energy | 7 | 7 | 4 | 1 | limited_data | enrichment_incomplete |
| ON | ON Semiconductor | Information Tec | 39 | 10 | 10 | 1 | limited_data | enrichment_incomplete |
| OTIS | Otis Worldwide | Industrials | 6 | 6 | 5 | 1 | limited_data | enrichment_incomplete |
| PEG | Public Service Enter | Utilities | 5 | 5 | 5 | 1 | limited_data | enrichment_incomplete |
| PFG | Principal Financial  | Financials | 2 | 2 | 2 | 1 | limited_data | low_finnhub_supply |
| PKG | Packaging Corporatio | Materials | 5 | 5 | 5 | 1 | limited_data | enrichment_incomplete |
| PNC | PNC Financial Servic | Financials | 12 | 10 | 9 | 1 | limited_data | enrichment_incomplete |
| PNR | Pentair | Industrials | 1 | 1 | 1 | 1 | limited_data | low_finnhub_supply |
| PRU | Prudential Financial | Financials | 18 | 10 | 8 | 1 | limited_data | enrichment_incomplete |
| PSKY | Paramount Skydance C | Communication S | 29 | 10 | 8 | 1 | limited_data | enrichment_incomplete |
| REG | Regency Centers | Real Estate | 2 | 2 | 1 | 1 | limited_data | low_finnhub_supply |
| ROP | Roper Technologies | Information Tec | 13 | 9 | 6 | 1 | limited_data | enrichment_incomplete |
| ROST | Ross Stores | Consumer Discre | 16 | 10 | 9 | 1 | limited_data | enrichment_incomplete |
| SCHW | Charles Schwab Corpo | Financials | 50 | 10 | 8 | 1 | limited_data | enrichment_incomplete |
| SNA | Snap-on | Industrials | 2 | 2 | 1 | 1 | limited_data | low_finnhub_supply |
| STZ | Constellation Brands | Consumer Staple | 8 | 7 | 5 | 1 | limited_data | enrichment_incomplete |

## Top 50 Tickers (by usable_7d)

| ticker | company | sector | fh_raw | extracted | usable_7d |
|--------|---------|--------|--------|-----------|-----------|
| AMD | Advanced Micro Devic | Information Tec | 243 | 9 | 75 |
| GOOG | Alphabet Inc. | Communication S | 246 | 10 | 74 |
| GOOGL | Alphabet Inc. | Communication S | 245 | 10 | 61 |
| AMZN | Amazon | Consumer Discre | 243 | 10 | 57 |
| ADBE | Adobe Inc. | Information Tec | 38 | 8 | 39 |
| AKAM | Akamai Technologies | Information Tec | 51 | 9 | 34 |
| ABNB | Airbnb | Consumer Discre | 32 | 10 | 33 |
| ABT | Abbott Laboratories | Health Care | 27 | 9 | 28 |
| ACN | Accenture | Information Tec | 40 | 8 | 27 |
| ALB | Albemarle Corporatio | Materials | 24 | 9 | 24 |
| ABBV | AbbVie | Health Care | 35 | 10 | 23 |
| AAPL | Apple Inc. | Information Tec | 238 | 10 | 22 |
| NVDA | Nvidia | Information Tec | 249 | 9 | 21 |
| BRO | Brown & Brown | Financials | 6 | 4 | 18 |
| FOX | Fox Corporation | Communication S | 37 | 7 | 17 |
| MO | Altria | Consumer Staple | 18 | 7 | 17 |
| AES | AES Corporation | Utilities | 8 | 7 | 16 |
| CHD | Church & Dwight | Consumer Staple | 5 | 5 | 16 |
| T | AT&T | Communication S | 51 | 10 | 16 |
| ALLE | Allegion | Industrials | 13 | 8 | 15 |
| MTB | M&T Bank | Financials | 4 | 3 | 15 |
| PCG | PG&E Corporation | Utilities | 9 | 9 | 15 |
| ALL | Allstate | Financials | 11 | 7 | 14 |
| ALGN | Align Technology | Health Care | 5 | 5 | 13 |
| C | Citigroup | Financials | 98 | 10 | 13 |
| MMM | 3M | Industrials | 12 | 7 | 13 |
| AMCR | Amcor | Materials | 8 | 6 | 12 |
| AOS | A. O. Smith | Industrials | 10 | 8 | 12 |
| BR | Broadridge Financial | Industrials | 19 | 9 | 12 |
| FOXA | Fox Corporation | Communication S | 43 | 8 | 12 |
| JNJ | Johnson & Johnson | Health Care | 59 | 9 | 12 |
| KKR | KKR & Co. | Financials | 35 | 10 | 12 |
| AEE | Ameren | Utilities | 6 | 5 | 11 |
| AFL | Aflac | Financials | 9 | 8 | 11 |
| APH | Amphenol | Information Tec | 25 | 10 | 11 |
| BLK | BlackRock | Financials | 84 | 10 | 11 |
| CARR | Carrier Global | Industrials | 11 | 9 | 11 |
| CRM | Salesforce | Information Tec | 91 | 10 | 11 |
| CTSH | Cognizant | Information Tec | 12 | 10 | 11 |
| EG | Everest Group | Financials | 7 | 7 | 11 |
| A | Agilent Technologies | Health Care | 7 | 7 | 10 |
| AIG | American Internation | Financials | 7 | 6 | 10 |
| AON | Aon plc | Financials | 15 | 8 | 10 |
| BK | BNY Mellon | Financials | 9 | 8 | 10 |
| CI | Cigna | Health Care | 11 | 9 | 10 |
| COR | Cencora | Health Care | 10 | 8 | 10 |
| CVS | CVS Health | Health Care | 43 | 9 | 10 |
| DELL | Dell Technologies | Information Tec | 80 | 10 | 10 |
| DOW | Dow Inc. | Materials | 13 | 7 | 10 |
| DUK | Duke Energy | Utilities | 18 | 10 | 10 |

## By Sector

| sector | tickers | mean_usable | median | ≥3% | ≥10% | common_failure |
|--------|---------|-------------|--------|-----|------|----------------|
| Communication Services | 23 | 12 | 7 | 91.3% | 21.7% | blocked_domains |
| Consumer Discretionary | 48 | 6.1 | 4.5 | 75.0% | 4.2% | blocked_domains |
| Consumer Staples | 36 | 4.9 | 4.5 | 72.2% | 5.6% | blocked_domains |
| Energy | 22 | 4.5 | 5.0 | 81.8% | 4.5% | blocked_domains |
| Financials | 76 | 6.0 | 6.0 | 80.3% | 15.8% | blocked_domains |
| Health Care | 58 | 5.6 | 4.0 | 81.0% | 13.8% | blocked_domains |
| Industrials | 79 | 4.7 | 4 | 73.4% | 10.1% | blocked_domains |
| Information Technology | 73 | 7.4 | 5 | 80.8% | 13.7% | blocked_domains |
| Materials | 26 | 4.9 | 4.0 | 69.2% | 11.5% | blocked_domains |
| Real Estate | 31 | 4.8 | 5 | 80.6% | 3.2% | blocked_domains |
| Unknown | 1 | 4 | 4 | 100.0% | 0.0% | low_finnhub_supply |
| Utilities | 31 | 6 | 5 | 87.1% | 16.1% | blocked_domains |

## Failure Analysis

| failure_reason | ticker_count |
|----------------|--------------|
| blocked_domains | 237 |
| none | 157 |
| enrichment_incomplete | 85 |
| low_finnhub_supply | 25 |

## Recommendations

**Can Finnhub-first support the full universe (MVP ≥3)?** PARTIALLY
- 397/504 tickers (78.8%) meet the MVP threshold

**Is 10 usable articles per ticker realistic?** NO
- 57/504 tickers (11.3%) meet the production ideal threshold

**Is first25 safe?** CAUTION — check limited tickers first

**Is full 500 risk refresh safe?** WAIT — 107 tickers are limited
