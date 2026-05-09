-- Migration: Backfill dimension scores from old schema to new schema
--
-- Problem: Most ticker_risk_snapshots rows have dimension scores stored under
-- old names (position_sizing, volatility_trend) in factor_breakdown.ai_dimensions,
-- but the V2 columns (financial_health, news_sentiment_dim, macro_exposure_dim,
-- sector_exposure, volatility) are NULL. The backend code now maps old names to
-- new names, but the DB itself needs backfilling so that:
--   1. Direct SQL queries see the correct data
--   2. Rows with all-null V2 columns + all-null ai_dimensions get skipped by
--      the "already scored" check in refresh_ticker_snapshot
--   3. Historical data is consistent
--
-- This migration is idempotent — it only updates rows where the target is NULL
-- and the source is NOT NULL.
--
-- Pre-check counts (as of 2026-05-08):
--   step1_add_new_keys: 7,065 rows (add financial_health/volatility keys to ai_dimensions)
--   step2_populate_v2_cols: 7,221 rows (fill V2 columns from ai_dimensions)
--   Totally unrecoverable: 4 tickers (HIMS, HOOD, KHC, SMCI — latest snapshot has null dims)
--   Recoverable tickers from latest snapshot: 500 of 504

-- ============================================================================
-- STEP 0: Pre-flight check — count affected rows
-- ============================================================================

-- Run this FIRST to verify counts before executing the UPDATE:
-- SELECT
--   COUNT(*) FILTER (WHERE financial_health IS NULL
--     AND factor_breakdown->'ai_dimensions'->>'position_sizing' IS NOT NULL) as fh_from_ps,
--   COUNT(*) FILTER (WHERE volatility IS NULL
--     AND factor_breakdown->'ai_dimensions'->>'volatility_trend' IS NOT NULL) as vol_from_vt,
--   COUNT(*) FILTER (WHERE news_sentiment_dim IS NULL
--     AND factor_breakdown->'ai_dimensions'->>'news_sentiment' IS NOT NULL) as ns_fill,
--   COUNT(*) FILTER (WHERE macro_exposure_dim IS NULL
--     AND factor_breakdown->'ai_dimensions'->>'macro_exposure' IS NOT NULL) as me_fill
-- FROM ticker_risk_snapshots;


-- ============================================================================
-- STEP 1: Add new-key aliases in ai_dimensions JSON
-- ============================================================================
-- This adds financial_health/volatility keys where only position_sizing/volatility_trend exist.
-- Idempotent: only updates when the new key is NULL/missing and old key exists.

UPDATE ticker_risk_snapshots
SET factor_breakdown = jsonb_set(
    jsonb_set(
        factor_breakdown,
        '{ai_dimensions,volatility}',
        to_jsonb((factor_breakdown->'ai_dimensions'->>'volatility_trend')::numeric)
    ),
    '{ai_dimensions,financial_health}',
    to_jsonb((factor_breakdown->'ai_dimensions'->>'position_sizing')::numeric)
)
WHERE factor_breakdown->'ai_dimensions'->>'position_sizing' IS NOT NULL
  AND factor_breakdown->'ai_dimensions'->>'financial_health' IS NULL
  AND factor_breakdown IS NOT NULL;


-- ============================================================================
-- STEP 2: Populate V2 dimension columns from ai_dimensions
-- ============================================================================
-- This fills the dedicated V2 columns (financial_health, news_sentiment_dim,
-- macro_exposure_dim, sector_exposure, volatility) from ai_dimensions,
-- checking both new AND old key names.
-- Idempotent: only updates when the V2 column is NULL and a source exists.

-- 2a: financial_health (from financial_health or position_sizing)
UPDATE ticker_risk_snapshots
SET financial_health = COALESCE(
    (factor_breakdown->'ai_dimensions'->>'financial_health')::numeric,
    (factor_breakdown->'ai_dimensions'->>'position_sizing')::numeric
)
WHERE financial_health IS NULL
  AND factor_breakdown IS NOT NULL
  AND (
    factor_breakdown->'ai_dimensions'->>'financial_health' IS NOT NULL
    OR factor_breakdown->'ai_dimensions'->>'position_sizing' IS NOT NULL
  );

-- 2b: news_sentiment_dim
UPDATE ticker_risk_snapshots
SET news_sentiment_dim = (factor_breakdown->'ai_dimensions'->>'news_sentiment')::numeric
WHERE news_sentiment_dim IS NULL
  AND factor_breakdown IS NOT NULL
  AND factor_breakdown->'ai_dimensions'->>'news_sentiment' IS NOT NULL;

-- 2c: macro_exposure_dim
UPDATE ticker_risk_snapshots
SET macro_exposure_dim = (factor_breakdown->'ai_dimensions'->>'macro_exposure')::numeric
WHERE macro_exposure_dim IS NULL
  AND factor_breakdown IS NOT NULL
  AND factor_breakdown->'ai_dimensions'->>'macro_exposure' IS NOT NULL;

-- 2d: sector_exposure
UPDATE ticker_risk_snapshots
SET sector_exposure = (factor_breakdown->'ai_dimensions'->>'sector_exposure')::numeric
WHERE sector_exposure IS NULL
  AND factor_breakdown IS NOT NULL
  AND factor_breakdown->'ai_dimensions'->>'sector_exposure' IS NOT NULL;

-- 2e: volatility (from volatility or volatility_trend in ai_dimensions, plus
--     the V2 column if it was already set by a previous migration)
UPDATE ticker_risk_snapshots
SET volatility = COALESCE(
    (factor_breakdown->'ai_dimensions'->>'volatility')::numeric,
    (factor_breakdown->'ai_dimensions'->>'volatility_trend')::numeric
)
WHERE volatility IS NULL
  AND factor_breakdown IS NOT NULL
  AND (
    factor_breakdown->'ai_dimensions'->>'volatility' IS NOT NULL
    OR factor_breakdown->'ai_dimensions'->>'volatility_trend' IS NOT NULL
  );


-- ============================================================================
-- STEP 3: For rows with ALL-null dimension data, copy from the previous snapshot
--         for the same ticker (handles the HOOD/KHC/SMCI null-dims case)
-- ============================================================================

-- This step handles rows where the latest backfill has all-null V2 columns AND
-- either null or missing ai_dimensions. It copies V2 columns from the most
-- recent previous snapshot that has dimension data for the same ticker.

UPDATE ticker_risk_snapshots t
SET
  financial_health = COALESCE(t.financial_health, prev.financial_health),
  news_sentiment_dim = COALESCE(t.news_sentiment_dim, prev.news_sentiment_dim),
  macro_exposure_dim = COALESCE(t.macro_exposure_dim, prev.macro_exposure_dim),
  sector_exposure = COALESCE(t.sector_exposure, prev.sector_exposure),
  volatility = COALESCE(t.volatility, prev.volatility),
  factor_breakdown = CASE
    WHEN t.factor_breakdown IS NULL THEN prev.factor_breakdown
    WHEN t.factor_breakdown->'ai_dimensions' IS NULL
         OR t.factor_breakdown->'ai_dimensions' = 'null'::jsonb
         OR (
           t.factor_breakdown->'ai_dimensions'->>'news_sentiment' IS NULL
           AND t.factor_breakdown->'ai_dimensions'->>'position_sizing' IS NULL
         )
    THEN jsonb_set(
      COALESCE(t.factor_breakdown, '{}'::jsonb),
      '{ai_dimensions}',
      COALESCE(prev.factor_breakdown->'ai_dimensions', '{}'::jsonb)
    )
    ELSE t.factor_breakdown
  END
FROM (
  SELECT DISTINCT ON (ticker)
    ticker,
    financial_health,
    news_sentiment_dim,
    macro_exposure_dim,
    sector_exposure,
    volatility,
    factor_breakdown
  FROM ticker_risk_snapshots
  WHERE financial_health IS NOT NULL
     OR news_sentiment_dim IS NOT NULL
     OR factor_breakdown->'ai_dimensions'->>'position_sizing' IS NOT NULL
     OR factor_breakdown->'ai_dimensions'->>'news_sentiment' IS NOT NULL
  ORDER BY ticker, analysis_as_of DESC NULLS LAST
) prev
WHERE t.ticker = prev.ticker
  AND t.financial_health IS NULL
  AND t.news_sentiment_dim IS NULL
  AND t.macro_exposure_dim IS NULL
  AND t.sector_exposure IS NULL
  AND t.volatility IS NULL
  AND (t.factor_breakdown->'ai_dimensions' IS NULL
       OR t.factor_breakdown->'ai_dimensions' = 'null'::jsonb
       OR (
         t.factor_breakdown->'ai_dimensions'->>'news_sentiment' IS NULL
         AND t.factor_breakdown->'ai_dimensions'->>'position_sizing' IS NULL
       ));

-- ============================================================================
-- STEP 3b: For rows with PARTIAL-null dimension data, COALESCE from previous snapshot
-- ============================================================================

-- Handles rows like TSLA May 8 where some V2 columns got populated by Step 2
-- (news_sentiment, macro_exposure) but others remain NULL (financial_health, volatility)
-- because ai_dimensions had those keys as NULL values rather than missing keys.

UPDATE ticker_risk_snapshots t
SET
  financial_health = COALESCE(t.financial_health, prev.financial_health),
  news_sentiment_dim = COALESCE(t.news_sentiment_dim, prev.news_sentiment_dim),
  macro_exposure_dim = COALESCE(t.macro_exposure_dim, prev.macro_exposure_dim),
  sector_exposure = COALESCE(t.sector_exposure, prev.sector_exposure),
  volatility = COALESCE(t.volatility, prev.volatility)
FROM (
  SELECT DISTINCT ON (ticker)
    ticker,
    financial_health,
    news_sentiment_dim,
    macro_exposure_dim,
    sector_exposure,
    volatility
  FROM ticker_risk_snapshots
  WHERE financial_health IS NOT NULL
  ORDER BY ticker, analysis_as_of DESC NULLS LAST
) prev
WHERE t.ticker = prev.ticker
  AND (t.financial_health IS NULL OR t.news_sentiment_dim IS NULL
       OR t.macro_exposure_dim IS NULL OR t.sector_exposure IS NULL OR t.volatility IS NULL);


-- ============================================================================
-- POST-MIGRATION VERIFICATION
-- ============================================================================

-- After running, verify with:
-- SELECT
--   COUNT(*) as total_rows,
--   COUNT(financial_health) as has_financial_health,
--   COUNT(news_sentiment_dim) as has_news_sentiment_dim,
--   COUNT(sector_exposure) as has_sector_exposure,
--   COUNT(volatility) as has_volatility,
--   COUNT(CASE WHEN financial_health IS NOT NULL AND news_sentiment_dim IS NOT NULL
--              AND macro_exposure_dim IS NOT NULL AND volatility IS NOT NULL THEN 1 END) as at_least_4_of_5,
--   COUNT(CASE WHEN financial_health IS NULL
--     AND news_sentiment_dim IS NULL
--     AND macro_exposure_dim IS NULL
--     AND sector_exposure IS NULL
--     AND volatility IS NULL
--   ) as totally_unrecoverable
-- FROM ticker_risk_snapshots;
--
-- Expected: at_least_4_of_5 ≈ 9457, totally_unrecoverable = 1 (HIMS sp500-shared-cache-v1)
-- sector_exposure will be ~4664 (it didn't exist in old schema — NULLs are correct)