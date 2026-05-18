# Strict 500/504 News-Coverage Report — Post Re-Enrichment

*Generated: 2026-05-18 22:21 UTC  |  Window: trailing 7 days*
*Definition: strict (mirrors ticker_cache_service._row_is_strict_usable)*
*Universe: ticker_universe[index_membership=SP500,is_active=True] — 503 active tickers*
*Events rows in window: 15,453  |  Non-usable candidate rows: 11,756*

## A. Executive Summary — Strict Coverage

| Threshold | Strict baseline (pre-repair) | After re-enrichment | Delta |
|---|---|---|---|
| ≥3 usable (MVP) | 307/504 | 402/503 (79.9%) | **+95** |
| ≥5 usable | — | 330/503 (65.6%) | — |
| ≥10 usable (prod ideal) | 18/504 | 127/503 (25.2%) | **+109** |
| ≥20 usable | — | 13/503 (2.6%) | — |

## B. Per-Ticker Usable-Count Distribution

| Stat | Value |
|---|---|
| min | 0 |
| p10 | 1.0 |
| p25 | 3.0 |
| median | 6.0 |
| mean | 7.35 |
| p75 | 10.0 |
| p90 | 13.0 |
| max | 61 |

### Histogram (usable strict articles / ticker)

| Bucket | Tickers | % |
|---|---|---|
| 0 | 20 | 4.0% |
| 1-2 | 81 | 16.1% |
| 3-4 | 72 | 14.3% |
| 5-9 | 203 | 40.4% |
| 10-19 | 114 | 22.7% |
| 20+ | 13 | 2.6% |

## C. Sector Breakdown

| Sector | Tickers | Mean usable | Median | % ≥3 | % ≥10 |
|---|---|---|---|---|---|
| Communication Services | 23 | 10.87 | 10 | 87.0% | 56.5% |
| Information Technology | 73 | 9.38 | 7 | 89.0% | 34.2% |
| Consumer Discretionary | 48 | 8.46 | 7.0 | 79.2% | 31.2% |
| Utilities | 31 | 8.13 | 8 | 80.6% | 32.3% |
| Health Care | 58 | 6.97 | 6.0 | 74.1% | 19.0% |
| Industrials | 79 | 6.87 | 7 | 87.3% | 22.8% |
| Energy | 22 | 6.5 | 6.5 | 81.8% | 22.7% |
| Materials | 26 | 6.35 | 5.5 | 69.2% | 7.7% |
| Financials | 76 | 6.28 | 6.0 | 78.9% | 23.7% |
| Consumer Staples | 36 | 6.14 | 6.0 | 69.4% | 16.7% |
| Real Estate | 31 | 4.87 | 4 | 67.7% | 12.9% |

## D. Source Breakdown (top 30, by usable articles)

| Source | Usable articles |
|---|---|
| Yahoo | 1663 |
| Yahoo Finance | 260 |
| CNBC | 141 |
| Benzinga | 124 |
| simplywall.st | 114 |
| Stock Titan | 97 |
| Finnhub | 92 |
| MarketBeat | 81 |
| PR Newswire | 47 |
| StockStory | 44 |
| Trefis | 42 |
| ChartMill | 30 |
| Quiver Quantitative | 26 |
| TradingView | 17 |
| SeekingAlpha | 16 |
| Investor's Business Daily | 14 |
| Sahm | 12 |
| BBC | 11 |
| TIKR.com | 10 |
| The Motley Fool | 10 |
| Business Wire | 10 |
| CBS News | 10 |
| Bloomberg Law News | 9 |
| AD HOC NEWS | 9 |
| 24/7 Wall St. | 9 |
| Kavout | 8 |
| The Guardian | 8 |
| Morningstar | 7 |
| ESPN | 7 |
| NBC News | 7 |

## E. Domain Breakdown (top 30, by usable articles)

| Domain | Usable articles |
|---|---|
| finance.yahoo.com | 1556 |
| finnhub.io | 211 |
| cnbc.com | 135 |
| marketbeat.com | 120 |
| simplywall.st | 114 |
| benzinga.com | 102 |
| stocktitan.net | 97 |
| 247wallst.com | 82 |
| barchart.com | 67 |
| fool.com | 61 |
| trefis.com | 50 |
| prnewswire.com | 47 |
| stockstory.org | 44 |
| chartmill.com | 28 |
| quiverquant.com | 26 |
| seekingalpha.com | 21 |
| tradingview.com | 16 |
| investors.com | 14 |
| sahmcapital.com | 12 |
| wwd.com | 11 |
| bbc.com | 11 |
| tikr.com | 10 |
| businesswire.com | 10 |
| cbsnews.com | 10 |
| news.bloomberglaw.com | 9 |
| ad-hoc-news.de | 9 |
| kavout.com | 8 |
| theguardian.com | 8 |
| morningstar.com | 7 |
| espn.com | 7 |

## F. Failure Breakdown (non-usable candidate rows in window)

| Category | Count | % of non-usable |
|---|---|---|
| headline_only | 8702 | 74.0% |
| analysis_status:partial | 805 | 6.8% |
| missing_key_implications | 707 | 6.0% |
| extraction_status:failed | 491 | 4.2% |
| rejection:forbidden_phrase | 350 | 3.0% |
| missing_sentiment_reason | 172 | 1.5% |
| missing_sentiment_score | 171 | 1.5% |
| missing_tldr | 104 | 0.9% |
| rejection:missing_required_field | 91 | 0.8% |
| rejection:invalid_sentiment_score | 85 | 0.7% |
| analysis_status:headline_only | 29 | 0.2% |
| rejection:blocked | 12 | 0.1% |
| rejection:forbidden_phrase:buy | 12 | 0.1% |
| rejection:forbidden_phrase:sell | 9 | 0.1% |
| missing_what_it_means | 6 | 0.1% |
| rejection:forbidden_phrase:predict | 6 | 0.1% |
| rejection:forbidden_phrase:upside potential | 2 | 0.0% |
| paywalled | 1 | 0.0% |
| rejection:forbidden_phrase:suggest | 1 | 0.0% |

## G. Bottom 50 (lowest strict-usable coverage)

| Ticker | Company | Sector | Usable | Total 7d |
|---|---|---|---|---|
| BAX | Baxter International | Health Care | 0 | 15 |
| BF.B | Brown–Forman | Consumer Staples | 0 | 19 |
| BK | BNY Mellon | Financials | 0 | 14 |
| BKNG | Booking Holdings | Consumer Discretionary | 0 | 14 |
| BMY | Bristol Myers Squibb | Health Care | 0 | 19 |
| BX | Blackstone Inc. | Financials | 0 | 13 |
| CARR | Carrier Global | Industrials | 0 | 12 |
| CASY | Casey's | Consumer Staples | 0 | 13 |
| CEG | Constellation Energy | Utilities | 0 | 9 |
| CNC | Centene Corporation | Health Care | 0 | 19 |
| COHR | Coherent Corp. | Information Technology | 0 | 10 |
| COP | ConocoPhillips | Energy | 0 | 18 |
| CRL | Charles River Laboratories | Health Care | 0 | 14 |
| CSGP | CoStar Group | Real Estate | 0 | 11 |
| DDOG | Datadog | Information Technology | 0 | 14 |
| DECK | Deckers Brands | Consumer Discretionary | 0 | 19 |
| DG | Dollar General | Consumer Staples | 0 | 22 |
| DLR | Digital Realty | Real Estate | 0 | 11 |
| DLTR | Dollar Tree | Consumer Staples | 0 | 13 |
| INVH | Invitation Homes | Real Estate | 0 | 11 |
| BDX | Becton Dickinson | Health Care | 1 | 9 |
| BEN | Franklin Resources | Financials | 1 | 13 |
| BG | Bunge Global | Consumer Staples | 1 | 16 |
| BLDR | Builders FirstSource | Industrials | 1 | 20 |
| BLK | BlackRock | Financials | 1 | 16 |
| BRK.B | Berkshire Hathaway | Financials | 1 | 11 |
| BSX | Boston Scientific | Health Care | 1 | 19 |
| C | Citigroup | Financials | 1 | 15 |
| CAG | Conagra Brands | Consumer Staples | 1 | 15 |
| CAH | Cardinal Health | Health Care | 1 | 19 |
| CBOE | Cboe Global Markets | Financials | 1 | 20 |
| CCI | Crown Castle | Real Estate | 1 | 17 |
| CCL | Carnival | Consumer Discretionary | 1 | 11 |
| CDNS | Cadence Design Systems | Information Technology | 1 | 18 |
| CF | CF Industries | Materials | 1 | 16 |
| CHD | Church & Dwight | Consumer Staples | 1 | 56 |
| CHTR | Charter Communications | Communication Services | 1 | 15 |
| CIEN | Ciena | Information Technology | 1 | 12 |
| CL | Colgate-Palmolive | Consumer Staples | 1 | 14 |
| CLX | Clorox | Consumer Staples | 1 | 8 |
| CMG | Chipotle Mexican Grill | Consumer Discretionary | 1 | 12 |
| CNP | CenterPoint Energy | Utilities | 1 | 17 |
| COIN | Coinbase | Financials | 1 | 23 |
| COO | Cooper Companies (The) | Health Care | 1 | 17 |
| CPB | Campbell's Company (The) | Consumer Staples | 1 | 14 |
| CPRT | Copart | Industrials | 1 | 14 |
| CRH | CRH plc | Materials | 1 | 17 |
| CTVA | Corteva | Materials | 1 | 18 |
| D | Dominion Energy | Utilities | 1 | 13 |
| DRI | Darden Restaurants | Consumer Discretionary | 1 | 15 |

## H. Top 50 (highest strict-usable coverage)

| Ticker | Company | Sector | Usable | Total 7d |
|---|---|---|---|---|
| AMZN | Amazon | Consumer Discretionary | 61 | 167 |
| AMD | Advanced Micro Devices | Information Technology | 59 | 229 |
| ADBE | Adobe Inc. | Information Technology | 49 | 104 |
| ALB | Albemarle Corporation | Materials | 40 | 92 |
| ABNB | Airbnb | Consumer Discretionary | 39 | 81 |
| GOOG | Alphabet Inc. | Communication Services | 39 | 102 |
| ACN | Accenture | Information Technology | 37 | 111 |
| ABT | Abbott Laboratories | Health Care | 35 | 81 |
| AKAM | Akamai Technologies | Information Technology | 33 | 109 |
| GOOGL | Alphabet Inc. | Communication Services | 29 | 75 |
| ABBV | AbbVie | Health Care | 28 | 80 |
| EXC | Exelon | Utilities | 27 | 73 |
| AES | AES Corporation | Utilities | 21 | 62 |
| AAPL | Apple Inc. | Information Technology | 19 | 84 |
| NVDA | Nvidia | Information Technology | 19 | 73 |
| EBAY | eBay Inc. | Consumer Discretionary | 18 | 53 |
| ECL | Ecolab | Materials | 18 | 39 |
| EL | Estée Lauder Companies (The) | Consumer Staples | 18 | 54 |
| MO | Altria | Consumer Staples | 18 | 49 |
| AFL | Aflac | Financials | 17 | 55 |
| DVA | DaVita | Health Care | 17 | 49 |
| EME | Emcor | Industrials | 17 | 63 |
| EQIX | Equinix | Real Estate | 17 | 60 |
| AEE | Ameren | Utilities | 16 | 60 |
| APH | Amphenol | Information Technology | 16 | 49 |
| AWK | American Water Works | Utilities | 16 | 54 |
| TSN | Tyson Foods | Consumer Staples | 16 | 33 |
| ADM | Archer Daniels Midland | Consumer Staples | 15 | 40 |
| ADSK | Autodesk | Information Technology | 15 | 66 |
| ALGN | Align Technology | Health Care | 15 | 65 |
| APTV | Aptiv | Consumer Discretionary | 15 | 47 |
| EMR | Emerson Electric | Industrials | 15 | 45 |
| F | Ford Motor Company | Consumer Discretionary | 15 | 54 |
| T | AT&T | Communication Services | 15 | 122 |
| AEP | American Electric Power | Utilities | 14 | 51 |
| DUK | Duke Energy | Utilities | 14 | 50 |
| EA | Electronic Arts | Communication Services | 14 | 42 |
| EFX | Equifax | Industrials | 14 | 41 |
| FANG | Diamondback Energy | Energy | 14 | 50 |
| MMM | 3M | Industrials | 14 | 47 |
| MSI | Motorola Solutions | Information Technology | 14 | 31 |
| NOC | Northrop Grumman | Industrials | 14 | 31 |
| NTAP | NetApp | Information Technology | 14 | 29 |
| AON | Aon plc | Financials | 13 | 52 |
| BA | Boeing | Industrials | 13 | 58 |
| DXCM | Dexcom | Health Care | 13 | 76 |
| EG | Everest Group | Financials | 13 | 56 |
| ELV | Elevance Health | Health Care | 13 | 54 |
| MAR | Marriott International | Consumer Discretionary | 13 | 31 |
| MET | MetLife | Financials | 13 | 32 |

*Full per-ticker data: news_coverage_500_after_reenrichment.csv*
