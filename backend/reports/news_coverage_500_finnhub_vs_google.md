# Finnhub-First vs Google-Assisted: 500-Ticker Coverage Comparison
*Generated: 2026-05-17 20:01 UTC*

## Executive Summary

| Metric | Finnhub-Only | Google-Assisted | Delta |
|--------|-------------|-----------------|-------|
| ≥3 usable (MVP) | 397/504 (78.8%) | 396/504 (78.6%) | -0.2% |
| ≥5 usable | 273/504 (54.2%) | 275/504 (54.6%) | +0.4% |
| ≥10 usable (prod ideal) | 57/504 (11.3%) | 59/504 (11.7%) | +0.4% |
| ≥20 usable | 13/504 (2.6%) | 13/504 (2.6%) | +0.0% |
| Mean usable | 6.0 | 6.0 | +0.0 |
| Median usable | 5.0 | 5.0 | +0.0 |

## Safety Status
- ✅ Finnhub-first — Google supplements only, never replaces
- ✅ skip_existing=True — no valid articles overwritten
- ✅ No risk snapshots promoted
- ✅ Finnhub-only and Google-assisted counts tracked separately

## Google Usage Summary

| Metric | Value |
|--------|-------|
| Tickers targeted (<10 usable) | 447 |
| Tickers that used Google | 447 |
| MVP recovery (usable < 3) | 249 |
| Production boost (usable 3–9) | 198 |
| Rescued to ≥3 | 142 |
| Boosted to ≥10 | 0 |
| Still below 3 after Google | 108 |
| Still below 10 after Google | 445 |
| Total Google raw articles | 5822 |
| Total Google added usable | 723 |
| Google 429s | 0 |

## Distribution Shift

| Stat | Finnhub-Only | Google-Assisted |
|------|-------------|-----------------|
| p10 | 1.0 | 1.0 |
| p25 | 3.0 | 3.0 |
| p75 | 7.0 | 7.0 |
| p90 | 10.0 | 10.0 |

## Histogram (Full Universe After Google)

| Bucket | Finnhub-Only | Google-Assisted | Delta |
|--------|-------------|-----------------|-------|
| 0 | 23 | 23 | 0 |
| 1-2 | 84 | 85 | +1 |
| 3-4 | 124 | 121 | -3 |
| 5-9 | 216 | 216 | 0 |
| 10-19 | 44 | 46 | +2 |
| 20+ | 13 | 13 | 0 |

## Tickers Rescued from <3 → ≥3 (142)

| ticker | company | sector | fh_usable | google_added | final |
|--------|---------|--------|-----------|--------------|-------|
| AXP | American Express | Financials | 2 | +8 | 10 |
| EXPE | Expedia Group | Consumer Discre | 2 | +8 | 10 |
| AVGO | Broadcom | Information Tec | 1 | +8 | 9 |
| AWK | American Water Works | Utilities | 2 | +7 | 9 |
| COST | Costco | Consumer Staple | 1 | +8 | 9 |
| ED | Consolidated Edison | Utilities | 1 | +8 | 9 |
| EXC | Exelon | Utilities | 2 | +7 | 9 |
| F | Ford Motor Company | Consumer Discre | 2 | +7 | 9 |
| INTC | Intel | Information Tec | 2 | +7 | 9 |
| MRSH | Marsh McLennan | Financials | 2 | +7 | 9 |
| AMP | Ameriprise Financial | Financials | 1 | +7 | 8 |
| AXON | Axon Enterprise | Industrials | 1 | +7 | 8 |
| BDX | Becton Dickinson | Health Care | 1 | +7 | 8 |
| CAT | Caterpillar Inc. | Industrials | 1 | +7 | 8 |
| CRL | Charles River Labora | Health Care | 2 | +6 | 8 |
| DE | Deere & Company | Industrials | 2 | +6 | 8 |
| DG | Dollar General | Consumer Staple | 1 | +7 | 8 |
| FDS | FactSet | Financials | 1 | +7 | 8 |
| GD | General Dynamics | Industrials | 2 | +6 | 8 |
| IRM | Iron Mountain | Real Estate | 2 | +6 | 8 |
| META | Meta Platforms | Communication S | 1 | +7 | 8 |
| MU | Micron Technology | Information Tec | 1 | +7 | 8 |
| TTD | Trade Desk (The) | Communication S | 1 | +7 | 8 |
| VRT | Vertiv | Industrials | 2 | +6 | 8 |
| VST | Vistra Corp | Utilities | 2 | +6 | 8 |
| AEP | American Electric Po | Utilities | 1 | +6 | 7 |
| BRK.B | Berkshire Hathaway | Financials | 1 | +6 | 7 |
| BX | Blackstone Inc. | Financials | 2 | +5 | 7 |
| CCI | Crown Castle | Real Estate | 1 | +6 | 7 |
| CHRW | C.H. Robinson | Industrials | 1 | +6 | 7 |

## Tickers Boosted from 3–9 → ≥10 (0)

| ticker | company | sector | fh_usable | google_added | final |
|--------|---------|--------|-----------|--------------|-------|

## Still Below 3 After Google (108)

| ticker | company | sector | fh_usable | google_added | final | top_failure |
|--------|---------|--------|-----------|--------------|-------|-------------|
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
| GWW | W. W. Grainger | Industrials | 2 | +0 | 1 | enrichment_incomplete |
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
| HBAN | Huntington Bancshare | Financials | 2 | +0 | 2 | enrichment_incomplete |
| HII | Huntington Ingalls I | Industrials | 1 | +1 | 2 | enrichment_incomplete |
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
| MA | Mastercard | Financials | 1 | +1 | 2 | enrichment_incomplete |
| MCK | McKesson Corporation | Health Care | 1 | +1 | 2 | enrichment_incomplete |
| MDLZ | Mondelez Internation | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| MGM | MGM Resorts | Consumer Discre | 1 | +1 | 2 | enrichment_incomplete |
| MPWR | Monolithic Power Sys | Information Tec | 1 | +1 | 2 | enrichment_incomplete |
| MRK | Merck & Co. | Health Care | 1 | +1 | 2 | enrichment_incomplete |
| NDAQ | Nasdaq, Inc. | Financials | 2 | +0 | 2 | enrichment_incomplete |
| NDSN | Nordson Corporation | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| NUE | Nucor | Materials | 2 | +0 | 2 | enrichment_incomplete |
| NXPI | NXP Semiconductors | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| ORCL | Oracle Corporation | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| ORLY | O’Reilly Automotive | Consumer Discre | 1 | +1 | 2 | enrichment_incomplete |
| PANW | Palo Alto Networks | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| PCAR | Paccar | Industrials | 2 | +0 | 2 | low_finnhub_supply |
| PEP | PepsiCo | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| PFE | Pfizer | Health Care | 1 | +1 | 2 | enrichment_incomplete |
| PNW | Pinnacle West Capita | Utilities | 1 | +1 | 2 | low_finnhub_supply |
| POOL | Pool Corporation | Consumer Discre | 1 | +1 | 2 | enrichment_incomplete |
| PWR | Quanta Services | Industrials | 1 | +1 | 2 | enrichment_incomplete |
| QCOM | Qualcomm | Information Tec | 1 | +1 | 2 | enrichment_incomplete |
| RCL | Royal Caribbean Grou | Consumer Discre | 2 | +0 | 2 | enrichment_incomplete |
| RF | Regions Financial Co | Financials | 2 | +0 | 2 | low_finnhub_supply |
| SATS | EchoStar | Communication S | 2 | +0 | 2 | enrichment_incomplete |
| SBAC | SBA Communications | Real Estate | 2 | +0 | 2 | enrichment_incomplete |
| SBUX | Starbucks | Consumer Discre | 1 | +1 | 2 | enrichment_incomplete |
| SLB | Schlumberger | Energy | 2 | +0 | 2 | enrichment_incomplete |
| SNPS | Synopsys | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| STLD | Steel Dynamics | Materials | 2 | +0 | 2 | enrichment_incomplete |
| SWKS | Skyworks Solutions | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| SYF | Synchrony Financial | Financials | 2 | +0 | 2 | enrichment_incomplete |
| TAP | Molson Coors Beverag | Consumer Staple | 1 | +1 | 2 | enrichment_incomplete |
| TDY | Teledyne Technologie | Information Tec | 2 | +0 | 2 | enrichment_incomplete |
| TGT | Target Corporation | Consumer Staple | 2 | +0 | 2 | enrichment_incomplete |
| TMO | Thermo Fisher Scient | Health Care | 2 | +0 | 2 | enrichment_incomplete |
| UDR | UDR, Inc. | Real Estate | 2 | +0 | 2 | low_finnhub_supply |
| UPS | United Parcel Servic | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| VRSK | Verisk Analytics | Industrials | 2 | +0 | 2 | enrichment_incomplete |
| VRSN | Verisign | Information Tec | 2 | +0 | 2 | low_finnhub_supply |
| EIX | Edison International | Utilities | 3 | +0 | 2 | none |

## Still Below 10 After Google (sample — worst 30)

| ticker | company | sector | fh_usable | google_added | final |
|--------|---------|--------|-----------|--------------|-------|
| GRMN | Garmin | Consumer Discre | 0 | +0 | 0 |
| HUBB | Hubbell Incorporated | Industrials | 0 | +0 | 0 |
| L | Loews Corporation | Financials | 0 | +0 | 0 |
| MNST | Monster Beverage | Consumer Staple | 0 | +0 | 0 |
| MSCI | MSCI Inc. | Financials | 0 | +0 | 0 |
| MTD | Mettler Toledo | Health Care | 0 | +0 | 0 |
| NCLH | Norwegian Cruise Lin | Consumer Discre | 0 | +0 | 0 |
| NI | NiSource | Utilities | 0 | +0 | 0 |
| NTAP | NetApp | Information Tec | 0 | +0 | 0 |
| PAYX | Paychex | Industrials | 0 | +0 | 0 |
| PGR | Progressive Corporat | Financials | 0 | +0 | 0 |
| PHM | PulteGroup | Consumer Discre | 0 | +0 | 0 |
| PLD | Prologis | Real Estate | 0 | +0 | 0 |
| PPG | PPG Industries | Materials | 0 | +0 | 0 |
| PPL | PPL Corporation | Utilities | 0 | +0 | 0 |
| PSA | Public Storage | Real Estate | 0 | +0 | 0 |
| PSX | Phillips 66 | Energy | 0 | +0 | 0 |
| PYPL | PayPal | Financials | 0 | +0 | 0 |
| Q | Qnity Electronics | Information Tec | 0 | +0 | 0 |
| RL | Ralph Lauren Corpora | Consumer Discre | 0 | +0 | 0 |
| ROL | Rollins, Inc. | Industrials | 0 | +0 | 0 |
| RSG | Republic Services | Industrials | 0 | +0 | 0 |
| SHW | Sherwin-Williams | Materials | 0 | +0 | 0 |
| BF.B | Brown–Forman | Consumer Staple | 1 | +0 | 1 |
| BKNG | Booking Holdings | Consumer Discre | 1 | +0 | 1 |
| GNRC | Generac | Industrials | 1 | +0 | 1 |
| GWW | W. W. Grainger | Industrials | 2 | +0 | 1 |
| IEX | IDEX Corporation | Industrials | 1 | +0 | 1 |
| INCY | Incyte | Health Care | 1 | +0 | 1 |
| ISRG | Intuitive Surgical | Health Care | 1 | +0 | 1 |

## By Sector

| sector | n | fh_mean | ga_mean | fh_≥3% | ga_≥3% | fh_≥10% | ga_≥10% |
|--------|---|---------|---------|--------|--------|---------|--------|
| Communication Services | 23 | 12 | 12 | 91% | 91% | 22% | 22% |
| Consumer Discretionary | 48 | 6.1 | 6.1 | 75% | 75% | 4% | 6% |
| Consumer Staples | 36 | 4.9 | 5 | 72% | 72% | 6% | 6% |
| Energy | 22 | 4.5 | 4.5 | 82% | 82% | 5% | 5% |
| Financials | 76 | 6.0 | 6.2 | 80% | 80% | 16% | 17% |
| Health Care | 58 | 5.6 | 5.6 | 81% | 81% | 14% | 14% |
| Industrials | 79 | 4.7 | 4.7 | 73% | 73% | 10% | 10% |
| Information Technology | 73 | 7.4 | 7.5 | 81% | 81% | 14% | 14% |
| Materials | 26 | 4.9 | 5 | 69% | 69% | 12% | 12% |
| Real Estate | 31 | 4.8 | 4.8 | 81% | 81% | 3% | 3% |
| Unknown | 1 | 4 | 4 | 100% | 100% | 0% | 0% |
| Utilities | 31 | 6 | 6 | 87% | 84% | 16% | 16% |

## Efficiency Analysis

| Metric | Value |
|--------|-------|
| Google raw articles per added usable | 8.1 |
| Total Google raw fetched | 5822 |
| Total usable added | 723 |
| Google 429s | 0 |

## Recommendations

**Can Finnhub-first support the full universe at MVP (≥3)?**
PARTIALLY — 396/504 (78.6%) after Google

**Can Finnhub+Google reach production ideal (≥10) for most tickers?**
NO — paid provider needed for remaining gap — 59/504 (11.7%) after Google

**Recommended production policy:**
- Active holdings/watchlist: target ≥10, use Finnhub + Google boost (mode=below_10)
- Dormant universe: target ≥3 MVP only, use Finnhub + Google MVP recovery (mode=mvp_only)
- Tickers still below 3 after Google: show "Limited Coverage" badge, score from headline if ≥1 article
- Never count failed/paywalled/headline-only as usable; never fabricate bodies or scores
