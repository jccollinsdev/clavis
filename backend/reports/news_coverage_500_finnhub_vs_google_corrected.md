# Finnhub-Only vs Google-Assisted: Corrected 500-Ticker Coverage Report
*Generated: 2026-05-17 20:36 UTC*
*CORRECTED: fixes field-semantic bugs in previous run where finnhub_usable was live DB (not baseline).*

## A. Executive Summary

| Metric | Finnhub-Only | Google-Assisted | Delta |
|--------|-------------|-----------------|-------|
| ≥3 usable (MVP) | 397/504 (78.8%) | 397/504 (78.8%) | 0.0% |
| ≥5 usable | 273/504 (54.2%) | 273/504 (54.2%) | 0.0% |
| ≥10 usable (prod ideal) | 57/504 (11.3%) | 57/504 (11.3%) | 0.0% |
| ≥20 usable | 13/504 (2.6%) | 13/504 (2.6%) | 0.0% |
| Rescued <3 → ≥3 | — | 0 tickers | — |
| Boosted <10 → ≥10 | — | 0 tickers | — |
| Net Google usable added | — | +0 total | — |
| Google raw fetched | — | 5837 | — |
| Google extraction attempts | — | 0 | — |
| Google 429s | — | 0 | — |

## Safety Status
- ✅ Finnhub-first — Google supplements only, never replaces
- ✅ finnhub_usable = Finnhub baseline JSON (immutable, never live DB)
- ✅ google_added_usable = net new above max(fh_usable, live_before)
- ✅ skip_existing=True — valid Finnhub articles not overwritten
- ✅ No risk snapshots promoted; no paywalled/failed counted as usable

## B. Corrected Distribution

| Stat | Finnhub-Only | Google-Assisted |
|------|-------------|-----------------|
| min | 0 | 0 |
| mean | 6.0 | 6.0 |
| median | 5.0 | 5.0 |
| p10 | 1.0 | 1.0 |
| p25 | 3.0 | 3.0 |
| p75 | 7.0 | 7.0 |
| p90 | 10.0 | 10.0 |
| max | 75 | 75 |

## C. Histogram

| Bucket | Finnhub-Only | Google-Assisted | Delta |
|--------|-------------|-----------------|-------|
| 0 | 23 | 23 | 0 |
| 1-2 | 84 | 84 | 0 |
| 3-4 | 124 | 124 | 0 |
| 5-9 | 216 | 216 | 0 |
| 10-19 | 44 | 44 | 0 |
| 20+ | 13 | 13 | 0 |

## D. Threshold Coverage

| Threshold | Finnhub-Only | Google-Assisted | Delta |
|-----------|-------------|-----------------|-------|
| ≥3 (MVP) | 397/504 (78.8%) | 397/504 (78.8%) | +0 tickers |
| ≥5 | 273/504 (54.2%) | 273/504 (54.2%) | +0 tickers |
| ≥10 (prod ideal) | 57/504 (11.3%) | 57/504 (11.3%) | +0 tickers |
| ≥20 | 13/504 (2.6%) | 13/504 (2.6%) | +0 tickers |

## E. Biggest Improvements (top 50 by google_added_usable)

| ticker | company | sector | fh_usable | google_added | final | mode |
|--------|---------|--------|-----------|--------------|-------|------|

## F. Still Below 3 After Google (107 tickers)

| ticker | company | sector | finnhub_usable | google_added | final_usable | top_failure |
|--------|---------|--------|----------------|--------------|--------------|-------------|
| GRMN | Garmin | Consumer Discre | 0 | +0 | 0 | low_finnhub_supply |
| HUBB | Hubbell Incorporated | Industrials | 0 | +0 | 0 | low_finnhub_supply |
| L | Loews Corporation | Financials | 0 | +0 | 0 | low_finnhub_supply |
| MNST | Monster Beverage | Consumer Staple | 0 | +0 | 0 | enrichment_incomplete |
| MSCI | MSCI Inc. | Financials | 0 | +0 | 0 | enrichment_incomplete |
| MTD | Mettler Toledo | Health Care | 0 | +0 | 0 | enrichment_incomplete |
| NCLH | Norwegian Cruise Lin | Consumer Discre | 0 | +0 | 0 | enrichment_incomplete |
| NI | NiSource | Utilities | 0 | +0 | 0 | enrichment_incomplete |
| NTAP | NetApp | Information Tec | 0 | +0 | 0 | enrichment_incomplete |
| PAYX | Paychex | Industrials | 0 | +0 | 0 | low_finnhub_supply |
| PGR | Progressive Corporat | Financials | 0 | +0 | 0 | enrichment_incomplete |
| PHM | PulteGroup | Consumer Discre | 0 | +0 | 0 | low_finnhub_supply |
| PLD | Prologis | Real Estate | 0 | +0 | 0 | enrichment_incomplete |
| PPG | PPG Industries | Materials | 0 | +0 | 0 | low_finnhub_supply |
| PPL | PPL Corporation | Utilities | 0 | +0 | 0 | enrichment_incomplete |
| PSA | Public Storage | Real Estate | 0 | +0 | 0 | low_finnhub_supply |
| PSX | Phillips 66 | Energy | 0 | +0 | 0 | enrichment_incomplete |
| PYPL | PayPal | Financials | 0 | +0 | 0 | enrichment_incomplete |
| Q | Qnity Electronics | Information Tec | 0 | +0 | 0 | enrichment_incomplete |
| RL | Ralph Lauren Corpora | Consumer Discre | 0 | +0 | 0 | enrichment_incomplete |
| ROL | Rollins, Inc. | Industrials | 0 | +0 | 0 | enrichment_incomplete |
| RSG | Republic Services | Industrials | 0 | +0 | 0 | enrichment_incomplete |
| SHW | Sherwin-Williams | Materials | 0 | +0 | 0 | enrichment_incomplete |
| BF.B | Brown–Forman | Consumer Staple | 1 | +0 | 1 | enrichment_incomplete |
| BKNG | Booking Holdings | Consumer Discre | 1 | +0 | 1 | enrichment_incomplete |
| GNRC | Generac | Industrials | 1 | +0 | 1 | enrichment_incomplete |
| IEX | IDEX Corporation | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| INCY | Incyte | Health Care | 1 | +0 | 1 | low_finnhub_supply |
| ISRG | Intuitive Surgical | Health Care | 1 | +0 | 1 | enrichment_incomplete |
| LH | Labcorp | Health Care | 1 | +0 | 1 | enrichment_incomplete |
| LII | Lennox International | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| LUV | Southwest Airlines | Industrials | 1 | +0 | 1 | enrichment_incomplete |
| NEM | Newmont | Materials | 1 | +0 | 1 | enrichment_incomplete |
| NOW | ServiceNow | Information Tec | 1 | +0 | 1 | enrichment_incomplete |
| OKE | Oneok | Energy | 1 | +0 | 1 | enrichment_incomplete |
| ON | ON Semiconductor | Information Tec | 1 | +0 | 1 | enrichment_incomplete |
| OTIS | Otis Worldwide | Industrials | 1 | +0 | 1 | enrichment_incomplete |
| PEG | Public Service Enter | Utilities | 1 | +0 | 1 | enrichment_incomplete |
| PFG | Principal Financial  | Financials | 1 | +0 | 1 | low_finnhub_supply |
| PKG | Packaging Corporatio | Materials | 1 | +0 | 1 | enrichment_incomplete |
| PNC | PNC Financial Servic | Financials | 1 | +0 | 1 | enrichment_incomplete |
| PNR | Pentair | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| PRU | Prudential Financial | Financials | 1 | +0 | 1 | enrichment_incomplete |
| PSKY | Paramount Skydance C | Communication S | 1 | +0 | 1 | enrichment_incomplete |
| REG | Regency Centers | Real Estate | 1 | +0 | 1 | low_finnhub_supply |
| ROP | Roper Technologies | Information Tec | 1 | +0 | 1 | enrichment_incomplete |
| ROST | Ross Stores | Consumer Discre | 1 | +0 | 1 | enrichment_incomplete |
| SCHW | Charles Schwab Corpo | Financials | 1 | +0 | 1 | enrichment_incomplete |
| SNA | Snap-on | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| STZ | Constellation Brands | Consumer Staple | 1 | +0 | 1 | enrichment_incomplete |
| TPL | Texas Pacific Land C | Energy | 1 | +0 | 1 | enrichment_incomplete |
| WRB | W. R. Berkley Corpor | Financials | 1 | +0 | 1 | low_finnhub_supply |
| BLDR | Builders FirstSource | Industrials | 2 | +0 | 2 | low_finnhub_supply |
| CINF | Cincinnati Financial | Financials | 2 | +0 | 2 | low_finnhub_supply |
| CNC | Centene Corporation | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| CSGP | CoStar Group | Real Estate | 2 | +0 | 2 | enrichment_incomplete |
| GWW | W. W. Grainger | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| HBAN | Huntington Bancshare | Financials | 2 | +0 | 2 | enrichment_incomplete |
| HII | Huntington Ingalls I | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| HSIC | Henry Schein | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| HSY | Hershey Company (The | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| IP | International Paper | Materials | 2 | +0 | 2 | enrichment_incomplete |
| IQV | IQVIA | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| IR | Ingersoll Rand | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| JBHT | J.B. Hunt | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| KMB | Kimberly-Clark | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| KR | Kroger | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| LIN | Linde plc | Materials | 2 | +0 | 2 | enrichment_incomplete |
| LULU | Lululemon Athletica | Consumer Discre | 2 | +0 | 2 | enrichment_incomplete |
| MA | Mastercard | Financials | 2 | +0 | 2 | enrichment_incomplete |
| MCK | McKesson Corporation | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| MDLZ | Mondelez Internation | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| MGM | MGM Resorts | Consumer Discre | 2 | +0 | 2 | enrichment_incomplete |
| MPWR | Monolithic Power Sys | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| MRK | Merck & Co. | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| NDAQ | Nasdaq, Inc. | Financials | 2 | +0 | 2 | enrichment_incomplete |
| NDSN | Nordson Corporation | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| NUE | Nucor | Materials | 2 | +0 | 2 | enrichment_incomplete |
| NXPI | NXP Semiconductors | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| ORCL | Oracle Corporation | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| ORLY | O’Reilly Automotive | Consumer Discre | 2 | +0 | 2 | enrichment_incomplete |
| PANW | Palo Alto Networks | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| PCAR | Paccar | Industrials | 2 | +0 | 2 | low_finnhub_supply |
| PEP | PepsiCo | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| PFE | Pfizer | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| PNW | Pinnacle West Capita | Utilities | 2 | +0 | 2 | low_finnhub_supply |
| POOL | Pool Corporation | Consumer Discre | 2 | +0 | 2 | enrichment_incomplete |
| PWR | Quanta Services | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| QCOM | Qualcomm | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| RCL | Royal Caribbean Grou | Consumer Discre | 2 | +0 | 2 | enrichment_incomplete |
| RF | Regions Financial Co | Financials | 2 | +0 | 2 | low_finnhub_supply |
| SATS | EchoStar | Communication S | 2 | +0 | 2 | enrichment_incomplete |
| SBAC | SBA Communications | Real Estate | 2 | +0 | 2 | enrichment_incomplete |
| SBUX | Starbucks | Consumer Discre | 2 | +0 | 2 | enrichment_incomplete |
| SLB | Schlumberger | Energy | 2 | +0 | 2 | enrichment_incomplete |
| SNPS | Synopsys | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| STLD | Steel Dynamics | Materials | 2 | +0 | 2 | enrichment_incomplete |
| SWKS | Skyworks Solutions | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| SYF | Synchrony Financial | Financials | 2 | +0 | 2 | enrichment_incomplete |
| TAP | Molson Coors Beverag | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| TDY | Teledyne Technologie | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| TGT | Target Corporation | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| TMO | Thermo Fisher Scient | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| UDR | UDR, Inc. | Real Estate | 2 | +0 | 2 | low_finnhub_supply |
| UPS | United Parcel Servic | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| VRSK | Verisk Analytics | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| VRSN | Verisign | Information Tec | 2 | +0 | 2 | low_finnhub_supply |

## G. Still Below 10 After Google (bottom 50)

| ticker | company | sector | finnhub_usable | google_added | final_usable | top_failure |
|--------|---------|--------|----------------|--------------|--------------|-------------|
| GRMN | Garmin | Consumer Discre | 0 | +0 | 0 | low_finnhub_supply |
| HUBB | Hubbell Incorporated | Industrials | 0 | +0 | 0 | low_finnhub_supply |
| L | Loews Corporation | Financials | 0 | +0 | 0 | low_finnhub_supply |
| MNST | Monster Beverage | Consumer Staple | 0 | +0 | 0 | enrichment_incomplete |
| MSCI | MSCI Inc. | Financials | 0 | +0 | 0 | enrichment_incomplete |
| MTD | Mettler Toledo | Health Care | 0 | +0 | 0 | enrichment_incomplete |
| NCLH | Norwegian Cruise Lin | Consumer Discre | 0 | +0 | 0 | enrichment_incomplete |
| NI | NiSource | Utilities | 0 | +0 | 0 | enrichment_incomplete |
| NTAP | NetApp | Information Tec | 0 | +0 | 0 | enrichment_incomplete |
| PAYX | Paychex | Industrials | 0 | +0 | 0 | low_finnhub_supply |
| PGR | Progressive Corporat | Financials | 0 | +0 | 0 | enrichment_incomplete |
| PHM | PulteGroup | Consumer Discre | 0 | +0 | 0 | low_finnhub_supply |
| PLD | Prologis | Real Estate | 0 | +0 | 0 | enrichment_incomplete |
| PPG | PPG Industries | Materials | 0 | +0 | 0 | low_finnhub_supply |
| PPL | PPL Corporation | Utilities | 0 | +0 | 0 | enrichment_incomplete |
| PSA | Public Storage | Real Estate | 0 | +0 | 0 | low_finnhub_supply |
| PSX | Phillips 66 | Energy | 0 | +0 | 0 | enrichment_incomplete |
| PYPL | PayPal | Financials | 0 | +0 | 0 | enrichment_incomplete |
| Q | Qnity Electronics | Information Tec | 0 | +0 | 0 | enrichment_incomplete |
| RL | Ralph Lauren Corpora | Consumer Discre | 0 | +0 | 0 | enrichment_incomplete |
| ROL | Rollins, Inc. | Industrials | 0 | +0 | 0 | enrichment_incomplete |
| RSG | Republic Services | Industrials | 0 | +0 | 0 | enrichment_incomplete |
| SHW | Sherwin-Williams | Materials | 0 | +0 | 0 | enrichment_incomplete |
| BF.B | Brown–Forman | Consumer Staple | 1 | +0 | 1 | enrichment_incomplete |
| BKNG | Booking Holdings | Consumer Discre | 1 | +0 | 1 | enrichment_incomplete |
| GNRC | Generac | Industrials | 1 | +0 | 1 | enrichment_incomplete |
| IEX | IDEX Corporation | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| INCY | Incyte | Health Care | 1 | +0 | 1 | low_finnhub_supply |
| ISRG | Intuitive Surgical | Health Care | 1 | +0 | 1 | enrichment_incomplete |
| LH | Labcorp | Health Care | 1 | +0 | 1 | enrichment_incomplete |
| LII | Lennox International | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| LUV | Southwest Airlines | Industrials | 1 | +0 | 1 | enrichment_incomplete |
| NEM | Newmont | Materials | 1 | +0 | 1 | enrichment_incomplete |
| NOW | ServiceNow | Information Tec | 1 | +0 | 1 | enrichment_incomplete |
| OKE | Oneok | Energy | 1 | +0 | 1 | enrichment_incomplete |
| ON | ON Semiconductor | Information Tec | 1 | +0 | 1 | enrichment_incomplete |
| OTIS | Otis Worldwide | Industrials | 1 | +0 | 1 | enrichment_incomplete |
| PEG | Public Service Enter | Utilities | 1 | +0 | 1 | enrichment_incomplete |
| PFG | Principal Financial  | Financials | 1 | +0 | 1 | low_finnhub_supply |
| PKG | Packaging Corporatio | Materials | 1 | +0 | 1 | enrichment_incomplete |
| PNC | PNC Financial Servic | Financials | 1 | +0 | 1 | enrichment_incomplete |
| PNR | Pentair | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| PRU | Prudential Financial | Financials | 1 | +0 | 1 | enrichment_incomplete |
| PSKY | Paramount Skydance C | Communication S | 1 | +0 | 1 | enrichment_incomplete |
| REG | Regency Centers | Real Estate | 1 | +0 | 1 | low_finnhub_supply |
| ROP | Roper Technologies | Information Tec | 1 | +0 | 1 | enrichment_incomplete |
| ROST | Ross Stores | Consumer Discre | 1 | +0 | 1 | enrichment_incomplete |
| SCHW | Charles Schwab Corpo | Financials | 1 | +0 | 1 | enrichment_incomplete |
| SNA | Snap-on | Industrials | 1 | +0 | 1 | low_finnhub_supply |
| STZ | Constellation Brands | Consumer Staple | 1 | +0 | 1 | enrichment_incomplete |

## H. Sector Breakdown

| sector | n | fh_mean | final_mean | fh_≥3% | final_≥3% | fh_≥10% | final_≥10% |
|--------|---|---------|------------|--------|-----------|---------|------------|
| Communication Services | 23 | 12 | 12 | 91% | 91% | 22% | 22% |
| Consumer Discretionary | 48 | 6.1 | 6.1 | 75% | 75% | 4% | 4% |
| Consumer Staples | 36 | 4.9 | 4.9 | 72% | 72% | 6% | 6% |
| Energy | 22 | 4.5 | 4.5 | 82% | 82% | 5% | 5% |
| Financials | 76 | 6.0 | 6.0 | 80% | 80% | 16% | 16% |
| Health Care | 58 | 5.6 | 5.6 | 81% | 81% | 14% | 14% |
| Industrials | 79 | 4.7 | 4.7 | 73% | 73% | 10% | 10% |
| Information Technology | 73 | 7.4 | 7.4 | 81% | 81% | 14% | 14% |
| Materials | 26 | 4.9 | 4.9 | 69% | 69% | 12% | 12% |
| Real Estate | 31 | 4.8 | 4.8 | 81% | 81% | 3% | 3% |
| Unknown | 1 | 4 | 4 | 100% | 100% | 0% | 0% |
| Utilities | 31 | 6 | 6 | 87% | 87% | 16% | 16% |

## I. Efficiency Analysis

| Metric | Value |
|--------|-------|
| Google raw articles per net-added usable | N/A (0 added) |
| Google extraction attempts per net-added usable | N/A |
| Total Google raw fetched | 5837 |
| Total Google extraction attempts | 0 |
| Total Google enriched complete | 0 |
| Net new Google usable articles | 0 |
| Google 429s | 0 |

## J. Honest Recommendation

**Did Google actually help?**
MARGINALLY — Google added +0 net new usable articles but moved the MVP (≥3) threshold by 0 tickers and production (≥10) by 0 tickers.

**Did Google help MVP threshold (≥3)?**
NO — 0 net change at ≥3 threshold

**Did Google help 10-article goal (≥10)?**
NO — 0 net change at ≥10 threshold

**Is 10 usable articles realistic for all 504 tickers using free sources (Finnhub + Google RSS)?**
NO — 57/504 (11.3%) reach ≥10 after both sources.
447 tickers still below 10. A paid provider is needed for broad ≥10 coverage.

**Recommended production policy:**
- Active holdings / watchlist tickers: target ≥10, use Finnhub + Google boost (mode=below_10); show "Limited Coverage" badge if still <10 after both sources
- Dormant universe tickers: target ≥3 MVP only, use Finnhub + Google MVP recovery (mode=mvp_only)
- Tickers still <3 after both sources (107 tickers): show "Limited Coverage" badge; score from headline only if ≥1 article exists; do not fabricate sentiment

**Is first-25 safe?** YES — no risk snapshots, no invalid articles counted, Finnhub baseline immutable.
**Is full-500 risk refresh safe?** NOT YET — 107 tickers below MVP; use coverage gate before any risk refresh.

**Previous run contradiction explained:**
The prior report claimed 142 rescued and +723 Google usable. Both were artifacts of using the live DB
count (which had drifted due to the 7-day window shifting ~44 min between runs) as `finnhub_usable`.
All 142 "rescued" tickers were ≥3 in the Finnhub baseline; none were genuinely below 3.
The corrected formula (google_added = max(0, live_after - max(fh_usable, live_before))) assigns
Google credit only for articles strictly above the established Finnhub baseline.
