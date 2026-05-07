# Clavix Methodology

How Clavix rates portfolio risk using observable data, transparent scoring, and a bond-rating-style grade scale.

**Last updated:** May 7, 2026

---

## What Clavix Measures

Clavix rates the risk of each tracked ticker across five dimensions. Each dimension is scored from 0 to 100, where higher means lower observed risk. The composite score is the average of the available dimensions.

Clavix is informational only. It does not recommend buying, selling, or holding any security. It describes risk signals based on public market data, company fundamentals, price behavior, and recent news.

## The Five Risk Dimensions

### 1. Financial Health

Financial Health measures the structural strength of the company. It uses balance-sheet and cash-flow inputs such as debt-to-equity ratio, free cash flow margin, interest coverage, current ratio, revenue growth trend, and profitability trend.

This dimension updates quarterly as new filings and fundamentals become available. For ETFs, Clavix uses the weighted financial health of the ETF's top holdings when enough underlying holdings are available. If there is not enough data, the dimension is shown as limited rather than estimated.

### 2. News Sentiment

News Sentiment measures the tone and severity of news about a ticker over the trailing seven days. Each article receives an individual 0-100 score, a short reason for that score, an impact tag, and source/recency weights.

Recent articles carry more weight than older articles. High-quality sources carry more weight than aggregators or low-confidence sources. A sudden increase in article volume is also treated as a risk signal because unusual attention can matter even before the direction is fully clear.

If fewer than three relevant articles are available in the seven-day window, Clavix shows limited data and excludes this dimension from the composite calculation.

### 3. Macro Exposure

Macro Exposure measures how sensitive a ticker is to broad macro factors. Clavix evaluates historical relationships between the ticker's returns and factors such as 10-year Treasury yields, the U.S. dollar, crude oil, VIX, and S&P 500 returns.

The quantitative score is based on observed sensitivity. The narrative explains what the current macro environment means for that ticker right now.

### 4. Sector Exposure

Sector Exposure measures how vulnerable a ticker is to its sector's current state. It considers sector beta, sector momentum versus the S&P 500, sector breadth, and sector-specific news.

A company in a weak or highly concentrated sector can score lower even if company-specific news is quiet. A defensive sector with broad participation and stable conditions can support a higher score.

### 5. Volatility

Volatility measures price instability and whether it is rising or falling. Inputs include 30-day realized volatility, 90-day realized volatility, the 30-day/90-day volatility ratio, maximum drawdown from the trailing 252-day high, and beta to the S&P 500.

Low volatility and falling volatility support a higher score. High volatility, rising volatility, large drawdowns, or high beta reduce the score.

## Composite Score

Each available dimension is weighted equally.

```text
composite_score = average(available dimension scores)
```

When all five dimensions are available, each contributes 20% of the final score. If a dimension has limited data, Clavix excludes it and averages the remaining dimensions. Clavix does not fabricate a score when the underlying data is missing.

## Grade Scale

Clavix maps the composite score to a bond-rating-style grade.

| Grade | Score | Meaning |
|---|---:|---|
| AAA | 90-100 | Treasury-grade. Major defensive blue chips, broad-market ETFs, ultra-stable names. |
| AA | 80-89 | Investment-grade safe. Strong large caps, defensive sectors, well-capitalized. |
| A | 70-79 | Solid. Healthy balance sheet, reasonable risk profile. |
| BBB | 60-69 | Stable but watch points. Some pressure but no immediate concerns. |
| BB | 50-59 | Mixed signals. Real risks present, weighing them is required. |
| B | 40-49 | Elevated risk. Material concerns across multiple dimensions. |
| CCC | 30-39 | High risk. Pressure compounding. |
| CC | 20-29 | Severe risk. Multiple dimensions in deterioration. |
| C | 10-19 | Distressed. Near-failure signals in fundamentals or news. |
| F | 0-9 | Failure mode. Illiquid, broken, near-zero. |

## Grade Stability

Clavix applies a stability rule so grades do not flicker because of small daily score movement. A grade change requires the score to move at least three points across the boundary and stay there for two consecutive days.

If there is not enough score history, Clavix shows no previous grade or delta. It shows `New` or `--` instead of inventing a prior value.

## Methodology Drill-Down

Every score is auditable. From a ticker rating, users can inspect:

- The five dimension scores
- The inputs behind each dimension
- The source of each input
- When each input was last updated
- The article-level scores that contributed to News Sentiment
- The reason each article received its score

The goal is simple: a user should be able to understand why a ticker is rated AA, BBB, or B without trusting a black box.

## Daily Digest

The daily digest turns these scores into a morning briefing. It is organized in this order:

1. Header with portfolio composite grade
2. Overnight macro
3. Sector heat for sectors the user owns
4. Position-by-position changes, ranked by risk movement
5. Watchlist updates
6. What to watch today

The digest is personalized to the user's holdings and watchlist, but the underlying ticker scores remain ticker-level ratings. Position size, cost basis, and brokerage data affect the explanation of what a change means for the user; they do not change the ticker's rating.

## Data Sources

Clavix uses market data, fundamentals, and news from providers including Polygon, Finnhub, Google News RSS, CNBC RSS, Jina Reader, and MiniMax for structured language analysis.

Brokerage connections are read-only and are used only to sync holdings. Clavix cannot place trades.

## Limitations

Clavix ratings depend on available data. Some events can move faster than scheduled refresh cycles. Some articles are paywalled or incomplete. Some tickers outside the tracked universe have limited fundamentals or limited news.

When data is limited, Clavix labels it as limited. It does not fill gaps with invented scores.
