# News Failure Access Classification — S&P 500 Below-MVP Investigation

**Generated:** 2026-05-17  
**Scope:** 107 S&P 500 tickers with <3 usable news articles (7-day window)  
**Baseline:** Finnhub canary — 397/504 tickers with ≥3 usable, 57 with ≥10

---

## A. Executive Summary

**All 107 below-MVP tickers fail for the same reason: enrichment_incomplete.**

Every ticker has ≥11 articles in the 7-day DB window. None are victims of low news supply,
hard paywalls, or source selection errors. The pipeline fetches and extracts article bodies
but never calls the LLM enrichment step on them. Articles sit with `extraction_status='success'`
and `body_length ≥ 300` but `sentiment_score IS NULL` — permanently excluded by the `skip_existing`
guard that prevents re-enrichment.

**A single targeted re-enrich pass resolves all 107 tickers:**
- ≥3 usable: 107/107 (100%) with 7-day re-enrich
- ≥10 usable: 18/107 (17%) with 7-day re-enrich; 24/107 with 14-day

No new provider, no paywall bypass, no source changes required.

---

## B. Failure Classification

### B.1 — By Ticker (Primary Failure Mode)

| Category | Tickers | Description |
|---|---|---|
| **enrichment_incomplete** | **107** | Body extracted, LLM never called — `skip_existing` trap |
| hard_paywall | 0 | No ticker's primary failure is paywall |
| soft_block / 403 | 0 | No ticker's primary failure is 403 |
| genuine_low_news | 0 | All have ≥11 DB articles |

### B.2 — By Article (3,230 total articles across 107 tickers)

| Article Status | Count | % of Total |
|---|---|---|
| enrichment_incomplete (success + body≥300, no LLM) | 2,172 | 67.2% |
| extraction_bug (failed extraction, not paywall) | 531 | 16.4% |
| soft_block (403 / anti-scrape) | 250 | 7.7% |
| hard_paywall (paywalled, body inaccessible) | 102 | 3.2% |
| currently usable (success + sentiment) | 138 | 4.3% |
| other | 37 | 1.1% |

**Key finding:** 663 articles have `extraction_status='success'`, `body_length ≥ 300`,
and `sentiment_score IS NULL`. These exist in the DB right now. The LLM enrichment
step was never called on them — not because of any external barrier, but because
`skip_existing=True` prevents re-processing.

---

## C. Domain Access Map (Top 15 Domains by Article Volume)

| Domain | Attempts | Success | Body≥300 | Sentiment | Paywall | 403 | Access Class |
|---|---|---|---|---|---|---|---|
| finance.yahoo.com | 470 | 347 | 89 | 22 | 0 | 0 | open_good |
| finnhub.io | 365 | 199 | 162 | 41 | 0 | 43 | open_good |
| marketwatch.com | 247 | 0 | 0 | 0 | 67 | 5 | hard_paywall |
| stocktitan.net | 191 | 48 | 48 | 12 | 0 | 0 | open_good |
| msn.com | 154 | 1 | 0 | 0 | 0 | 0 | open_no_body |
| marketbeat.com | 131 | 53 | 43 | 12 | 0 | 0 | open_good |
| gurufocus.com | 131 | 0 | 0 | 0 | 0 | 33 | soft_blocked |
| chartmill.com | 113 | 10 | 3 | 1 | 0 | 0 | open_mixed |
| investing.com | 71 | 0 | 0 | 0 | 0 | 30 | soft_blocked |
| simplywall.st | 67 | 55 | 55 | 8 | 0 | 0 | open_good |
| benzinga.com | 67 | 61 | 2 | 2 | 0 | 0 | open_mixed |
| barchart.com | 45 | 30 | 0 | 0 | 0 | 6 | open_no_body |
| ad-hoc-news.de | 44 | 5 | 5 | 1 | 0 | 0 | open_mixed |
| cnbc.com | 41 | 39 | 11 | 6 | 0 | 0 | open_good |
| seekingalpha.com | 38 | 4 | 4 | 0 | 0 | 18 | open_mixed |

**Notable findings:**
- **finance.yahoo.com**: 470 articles, 347 extracted (73%), but only 22 have sentiment (89 bodies
  stuck with no LLM call) — largest enrichment_incomplete sink
- **marketwatch.com**: 247 attempts, 0 bodies, 67 confirmed paywalls — hard wall, skip it
- **gurufocus.com**: 131 attempts, 33 return 403 — soft-blocked
- **investing.com**: 71 attempts, 30 return 403 — soft-blocked
- **simplywall.st**: 82% success, bodies present, only 8 with sentiment — good source, stuck in pipeline
- **benzinga.com**: 91% success rate — working well where sentiment was called

---

## D. Safe Recovery Analysis

### D.1 — Re-Enrich Existing Bodies (Recommended Action)

Filter: `extraction_status = 'success' AND body_length >= 300 AND sentiment_score IS NULL AND published_at > NOW() - INTERVAL '7 days'`

| Metric | 7-Day Window | 14-Day Window |
|---|---|---|
| Recoverable articles | 663 | ~900 est. |
| Tickers reaching ≥3 | **107/107** | **107/107** |
| Tickers reaching ≥10 | **18/107** | **24/107** |

**All 107 tickers already have enough extracted bodies to meet the ≥3 MVP threshold.**
Zero additional fetching or extraction required.

### D.2 — Tickers Reaching ≥10 After 7-Day Re-Enrich (18 tickers)

```
HSY, IQV, LH, MA, MCK, MGM, NDSN, NI, PANW, PCAR, PFE, PGR, PPL, PWR, SBUX, SCHW, SLB, SWKS
```

### D.3 — Additional Tickers Reaching ≥10 With 14-Day Re-Enrich (6 additional)

```
CSGP, INCY, MDLZ, MNST, PFG, RCL
```

---

## E. Low-Confidence Headline / Summary Policy Evaluation

**Policy definition:** Count paywalled articles that have title + summary (but no body)
as low-confidence usable, weighted at 0.5 or counted as 1 full article.

| Metric | Value |
|---|---|
| Paywalled articles with title (7d, 107 tickers) | 81 |
| Tickers with paywall headlines | 62 |
| Additional tickers reaching ≥3 via headline policy | **0** |
| Additional tickers reaching ≥10 via re-enrich + headline | **10** |
| Total ≥10 with re-enrich + headline policy | **28** |

**Recommendation: Do not implement headline-only scoring.**

Reasons:
1. Adds 0 tickers to ≥3 coverage — the primary goal is unchanged.
2. Adds 10 tickers to ≥10 coverage — achievable without this policy by using the 14-day window.
3. Headline-only articles have no body, no sentiment direction, and no significance score.
   Counting them as usable weakens the verifier without a proportional coverage gain.
4. If ≥10 breadth is needed, a 14-day re-enrich window is safer and already yields 24 tickers.

---

## F. Per-Ticker Recovery Table

| Ticker | Company | FH Usable | Current | Recoverable | Potential (7d) | ≥3? | ≥10? | EI Count | PW Hl |
|---|---|---|---|---|---|---|---|---|---|
| LH | Labcorp | 1 | 1 | 11 | 12 | ✓ | ✓ | 22 | 0 |
| HSY | Hershey Company (The) | 2 | 2 | 9 | 11 | ✓ | ✓ | 22 | 0 |
| IQV | IQVIA | 2 | 2 | 9 | 11 | ✓ | ✓ | 22 | 0 |
| MA | Mastercard | 2 | 2 | 9 | 11 | ✓ | ✓ | 28 | 0 |
| MCK | McKesson Corporation | 2 | 2 | 9 | 11 | ✓ | ✓ | 23 | 1 |
| MGM | MGM Resorts | 2 | 2 | 9 | 11 | ✓ | ✓ | 24 | 1 |
| PFE | Pfizer | 2 | 2 | 9 | 11 | ✓ | ✓ | 21 | 0 |
| PPL | PPL Corporation | 0 | 0 | 11 | 11 | ✓ | ✓ | 22 | 0 |
| PWR | Quanta Services | 2 | 2 | 9 | 11 | ✓ | ✓ | 24 | 1 |
| SWKS | Skyworks Solutions | 2 | 2 | 9 | 11 | ✓ | ✓ | 28 | 1 |
| NDSN | Nordson Corporation | 2 | 2 | 8 | 10 | ✓ | ✓ | 17 | 1 |
| NI | NiSource | 0 | 0 | 10 | 10 | ✓ | ✓ | 23 | 0 |
| PANW | Palo Alto Networks | 2 | 2 | 8 | 10 | ✓ | ✓ | 29 | 0 |
| PCAR | Paccar | 2 | 2 | 8 | 10 | ✓ | ✓ | 16 | 1 |
| PGR | Progressive Corporation | 0 | 0 | 10 | 10 | ✓ | ✓ | 26 | 1 |
| SBUX | Starbucks | 2 | 2 | 8 | 10 | ✓ | ✓ | 27 | 1 |
| SCHW | Charles Schwab Corporation | 1 | 1 | 9 | 10 | ✓ | ✓ | 27 | 0 |
| SLB | Schlumberger | 2 | 2 | 8 | 10 | ✓ | ✓ | 20 | 0 |
| BKNG | Booking Holdings | 1 | 1 | 8 | 9 | ✓ | ✗ | 22 | 0 |
| CSGP | CoStar Group | 2 | 2 | 7 | 9 | ✓ | ✗ | 17 | 0 |
| GRMN | Garmin | 0 | 0 | 9 | 9 | ✓ | ✗ | 23 | 0 |
| HII | Huntington Ingalls Industries | 2 | 2 | 7 | 9 | ✓ | ✗ | 20 | 0 |
| HSIC | Henry Schein | 2 | 2 | 7 | 9 | ✓ | ✗ | 19 | 1 |
| INCY | Incyte | 1 | 1 | 8 | 9 | ✓ | ✗ | 25 | 1 |
| JBHT | J.B. Hunt | 2 | 2 | 7 | 9 | ✓ | ✗ | 23 | 1 |
| LII | Lennox International | 1 | 1 | 8 | 9 | ✓ | ✗ | 20 | 0 |
| LULU | Lululemon Athletica | 2 | 2 | 7 | 9 | ✓ | ✗ | 19 | 2 |
| MDLZ | Mondelez International | 2 | 2 | 7 | 9 | ✓ | ✗ | 17 | 0 |
| MPWR | Monolithic Power Systems | 2 | 2 | 7 | 9 | ✓ | ✗ | 21 | 3 |
| NDAQ | Nasdaq, Inc. | 2 | 2 | 7 | 9 | ✓ | ✗ | 25 | 0 |
| NOW | ServiceNow | 1 | 1 | 8 | 9 | ✓ | ✗ | 24 | 1 |
| PEP | PepsiCo | 2 | 2 | 7 | 9 | ✓ | ✗ | 21 | 0 |
| Q | Qnity Electronics | 0 | 0 | 9 | 9 | ✓ | ✗ | 21 | 0 |
| RCL | Royal Caribbean Group | 2 | 2 | 7 | 9 | ✓ | ✗ | 20 | 1 |
| RF | Regions Financial Corporation | 2 | 2 | 7 | 9 | ✓ | ✗ | 23 | 1 |
| RSG | Republic Services | 0 | 0 | 9 | 9 | ✓ | ✗ | 22 | 0 |
| GWW | W. W. Grainger | 2 | 1 | 7 | 8 | ✓ | ✗ | 18 | 1 |
| HBAN | Huntington Bancshares | 2 | 2 | 6 | 8 | ✓ | ✗ | 18 | 1 |
| HUBB | Hubbell Incorporated | 0 | 0 | 8 | 8 | ✓ | ✗ | 22 | 0 |
| ISRG | Intuitive Surgical | 1 | 1 | 7 | 8 | ✓ | ✗ | 20 | 1 |
| L | Loews Corporation | 0 | 0 | 8 | 8 | ✓ | ✗ | 20 | 0 |
| LIN | Linde plc | 2 | 2 | 6 | 8 | ✓ | ✗ | 19 | 0 |
| MNST | Monster Beverage | 0 | 0 | 8 | 8 | ✓ | ✗ | 25 | 1 |
| NEM | Newmont | 1 | 1 | 7 | 8 | ✓ | ✗ | 25 | 1 |
| NTAP | NetApp | 0 | 0 | 8 | 8 | ✓ | ✗ | 20 | 0 |
| NXPI | NXP Semiconductors | 2 | 2 | 6 | 8 | ✓ | ✗ | 22 | 1 |
| OKE | Oneok | 1 | 1 | 7 | 8 | ✓ | ✗ | 26 | 1 |
| ORCL | Oracle Corporation | 2 | 2 | 6 | 8 | ✓ | ✗ | 25 | 1 |
| ORLY | O’Reilly Automotive | 2 | 2 | 6 | 8 | ✓ | ✗ | 18 | 0 |
| PEG | Public Service Enterprise Group | 1 | 1 | 7 | 8 | ✓ | ✗ | 19 | 2 |
| PFG | Principal Financial Group | 1 | 1 | 7 | 8 | ✓ | ✗ | 10 | 0 |
| PSX | Phillips 66 | 0 | 0 | 8 | 8 | ✓ | ✗ | 29 | 1 |
| QCOM | Qualcomm | 2 | 2 | 6 | 8 | ✓ | ✗ | 20 | 1 |
| RL | Ralph Lauren Corporation | 0 | 0 | 8 | 8 | ✓ | ✗ | 18 | 0 |
| SNPS | Synopsys | 2 | 2 | 6 | 8 | ✓ | ✗ | 19 | 0 |
| TMO | Thermo Fisher Scientific | 2 | 2 | 6 | 8 | ✓ | ✗ | 23 | 1 |
| CNC | Centene Corporation | 2 | 2 | 5 | 7 | ✓ | ✗ | 22 | 1 |
| GNRC | Generac | 1 | 1 | 6 | 7 | ✓ | ✗ | 21 | 1 |
| IEX | IDEX Corporation | 1 | 1 | 6 | 7 | ✓ | ✗ | 18 | 1 |
| IR | Ingersoll Rand | 2 | 2 | 5 | 7 | ✓ | ✗ | 19 | 1 |
| KMB | Kimberly-Clark | 2 | 2 | 5 | 7 | ✓ | ✗ | 27 | 0 |
| KR | Kroger | 2 | 2 | 5 | 7 | ✓ | ✗ | 19 | 0 |
| LUV | Southwest Airlines | 1 | 1 | 6 | 7 | ✓ | ✗ | 21 | 0 |
| MTD | Mettler Toledo | 0 | 0 | 7 | 7 | ✓ | ✗ | 20 | 3 |
| NUE | Nucor | 2 | 2 | 5 | 7 | ✓ | ✗ | 19 | 2 |
| PSKY | Paramount Skydance Corporation | 1 | 1 | 6 | 7 | ✓ | ✗ | 17 | 0 |
| REG | Regency Centers | 1 | 1 | 6 | 7 | ✓ | ✗ | 19 | 1 |
| ROL | Rollins, Inc. | 0 | 0 | 7 | 7 | ✓ | ✗ | 27 | 0 |
| ROST | Ross Stores | 1 | 1 | 6 | 7 | ✓ | ✗ | 16 | 0 |
| SATS | EchoStar | 2 | 2 | 5 | 7 | ✓ | ✗ | 19 | 0 |
| SNA | Snap-on | 1 | 1 | 6 | 7 | ✓ | ✗ | 21 | 0 |
| UPS | United Parcel Service | 2 | 2 | 5 | 7 | ✓ | ✗ | 21 | 0 |
| VRSK | Verisk Analytics | 2 | 2 | 5 | 7 | ✓ | ✗ | 19 | 1 |
| BF.B | Brown–Forman | 1 | 1 | 5 | 6 | ✓ | ✗ | 22 | 3 |
| BLDR | Builders FirstSource | 2 | 2 | 4 | 6 | ✓ | ✗ | 17 | 1 |
| IP | International Paper | 2 | 2 | 4 | 6 | ✓ | ✗ | 17 | 1 |
| ON | ON Semiconductor | 1 | 1 | 5 | 6 | ✓ | ✗ | 24 | 2 |
| PKG | Packaging Corporation of America | 1 | 1 | 5 | 6 | ✓ | ✗ | 18 | 1 |
| PNC | PNC Financial Services | 1 | 1 | 5 | 6 | ✓ | ✗ | 20 | 1 |
| PSA | Public Storage | 0 | 0 | 6 | 6 | ✓ | ✗ | 18 | 0 |
| SHW | Sherwin-Williams | 0 | 0 | 6 | 6 | ✓ | ✗ | 22 | 0 |
| STLD | Steel Dynamics | 2 | 2 | 4 | 6 | ✓ | ✗ | 16 | 1 |
| TGT | Target Corporation | 2 | 2 | 4 | 6 | ✓ | ✗ | 18 | 1 |
| TPL | Texas Pacific Land Corporation | 1 | 1 | 5 | 6 | ✓ | ✗ | 27 | 0 |
| CINF | Cincinnati Financial | 2 | 2 | 3 | 5 | ✓ | ✗ | 20 | 1 |
| MRK | Merck & Co. | 2 | 2 | 3 | 5 | ✓ | ✗ | 18 | 0 |
| NCLH | Norwegian Cruise Line Holdings | 0 | 0 | 5 | 5 | ✓ | ✗ | 19 | 0 |
| OTIS | Otis Worldwide | 1 | 1 | 4 | 5 | ✓ | ✗ | 16 | 2 |
| PLD | Prologis | 0 | 0 | 5 | 5 | ✓ | ✗ | 18 | 0 |
| PNR | Pentair | 1 | 1 | 4 | 5 | ✓ | ✗ | 14 | 2 |
| POOL | Pool Corporation | 2 | 2 | 3 | 5 | ✓ | ✗ | 12 | 0 |
| PPG | PPG Industries | 0 | 0 | 5 | 5 | ✓ | ✗ | 19 | 3 |
| PYPL | PayPal | 0 | 0 | 5 | 5 | ✓ | ✗ | 18 | 1 |
| ROP | Roper Technologies | 1 | 1 | 4 | 5 | ✓ | ✗ | 20 | 1 |
| SBAC | SBA Communications | 2 | 2 | 3 | 5 | ✓ | ✗ | 25 | 1 |
| STZ | Constellation Brands | 1 | 1 | 4 | 5 | ✓ | ✗ | 18 | 1 |
| SYF | Synchrony Financial | 2 | 2 | 3 | 5 | ✓ | ✗ | 16 | 2 |
| TDY | Teledyne Technologies | 2 | 2 | 3 | 5 | ✓ | ✗ | 14 | 1 |
| UDR | UDR, Inc. | 2 | 2 | 3 | 5 | ✓ | ✗ | 15 | 1 |
| PAYX | Paychex | 0 | 0 | 4 | 4 | ✓ | ✗ | 19 | 2 |
| PHM | PulteGroup | 0 | 0 | 4 | 4 | ✓ | ✗ | 14 | 2 |
| PNW | Pinnacle West Capital | 2 | 2 | 2 | 4 | ✓ | ✗ | 19 | 1 |
| WRB | W. R. Berkley Corporation | 1 | 1 | 3 | 4 | ✓ | ✗ | 13 | 1 |
| MSCI | MSCI Inc. | 0 | 0 | 3 | 3 | ✓ | ✗ | 18 | 2 |
| PRU | Prudential Financial | 1 | 1 | 2 | 3 | ✓ | ✗ | 25 | 0 |
| TAP | Molson Coors Beverage Company | 2 | 2 | 1 | 3 | ✓ | ✗ | 11 | 1 |
| VRSN | Verisign | 2 | 2 | 1 | 3 | ✓ | ✗ | 8 | 2 |

**Column guide:**
- FH Usable: Finnhub baseline (frozen, 7d window)
- Current: articles with sentiment today
- Recoverable: success-body articles with no sentiment (re-enrich candidates)
- Potential (7d): Current + Recoverable (upper bound with 7d re-enrich)
- ≥3? / ≥10?: Reaches threshold after 7d re-enrich
- EI Count: enrichment_incomplete article count
- PW Hl: paywalled articles with title (headline policy candidates)

---

## G. Final Recommendation

### Task 1: What is the failure breakdown?
All 107/107 tickers have **enrichment_incomplete** as their primary failure. Zero tickers
are primarily blocked by hard paywalls, 403 errors, or genuine low news volume.

### Task 2: How many can recover to ≥3 with safe open-source recovery?
**107/107** — all tickers can reach ≥3 by re-enriching bodies already in the DB.

### Task 3: How many can recover to ≥10?
- **18/107** with 7-day window re-enrich
- **24/107** with 14-day window re-enrich

### Task 4: With low-confidence headline/summary policy?
- ≥3: unchanged at 107/107 (policy adds nothing here)
- ≥10: 28/107 (vs 18 without; marginal gain at precision cost — not recommended)

### Task 5: Should headline/summary scoring be implemented?
**No.** The coverage gain (0 tickers for ≥3, 10 tickers for ≥10) doesn't justify the
precision cost of counting bodyless articles. The 14-day window achieves similar ≥10 gains
cleanly.

### Task 6: Are there ≥3 non-blocked open sources for most tickers?
Yes — across the universe, benzinga.com (91% success), cnbc.com (95% success),
prnewswire.com, stocktitan.net, and simplywall.st all provide accessible bodies.
The pipeline already fetches from these sources; it just doesn't finish enriching them.

### Task 7: What is the exact next engineering task?

**Add a re-enrich pass to the news pipeline:**

```sql
-- Articles eligible for re-enrichment
SELECT id, ticker, url, body, published_at
FROM news_articles
WHERE extraction_status = 'success'
  AND body_length >= 300
  AND sentiment_score IS NULL
  AND published_at > NOW() - INTERVAL '7 days'
ORDER BY published_at DESC;
-- Expected: ~663 articles across 107 tickers
```

Implementation steps:
1. Add `reenrich_pass.py` (or equivalent job) that queries the filter above
2. Pipe each article through the existing LLM enrichment step (no extraction needed)
3. Set `skip_existing = False` for articles matching the filter (or call enrichment directly)
4. Run daily or after each Finnhub fetch
5. Optionally: backfill with 14-day window to bring 24 tickers to ≥10

This is a **pipeline wiring fix**, not a new feature. The LLM enrichment infrastructure
already exists — it's just not being called on previously extracted bodies.

---

*Analysis run: 2026-05-17 | Finnhub baseline: 397/504 ≥3 usable | Google boost: +0 net (corrected)*
