-- ============================================================================
-- Phase 1 / Migration 003 — V2 Dimension Columns for ticker_risk_snapshots
-- Purpose: Add per-dimension score columns and audit metadata fields
--          so ticker_risk_snapshots can store all five CLAVIX_TRUTH §6
--          dimensions: Financial Health, News Sentiment, Macro Exposure,
--          Sector Exposure, and Volatility.
-- Safety:  All columns are nullable and DEFAULT NULL. Existing 9,006 rows
--          retain their legacy fields (safety_score, etc.) unchanged.
--          New columns only affect future writes.
-- Rollback: ALTER TABLE ... DROP COLUMN for each column added.
-- ============================================================================

ALTER TABLE public.ticker_risk_snapshots
    ADD COLUMN IF NOT EXISTS financial_health     NUMERIC,
    ADD COLUMN IF NOT EXISTS news_sentiment_dim   NUMERIC,
    ADD COLUMN IF NOT EXISTS macro_exposure_dim   NUMERIC,
    ADD COLUMN IF NOT EXISTS sector_exposure      NUMERIC,
    ADD COLUMN IF NOT EXISTS volatility           NUMERIC,
    ADD COLUMN IF NOT EXISTS composite_score      NUMERIC,
    ADD COLUMN IF NOT EXISTS dimension_inputs     JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS dimension_last_refreshed JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS limited_data_dimensions   JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.ticker_risk_snapshots.financial_health IS
    'Financial Health dimension score (0-100). CLAVIX_TRUTH §6.1.';
COMMENT ON COLUMN public.ticker_risk_snapshots.news_sentiment_dim IS
    'News Sentiment dimension score (0-100). CLAVIX_TRUTH §6.2.';
COMMENT ON COLUMN public.ticker_risk_snapshots.macro_exposure_dim IS
    'Macro Exposure dimension score (0-100). CLAVIX_TRUTH §6.3.';
COMMENT ON COLUMN public.ticker_risk_snapshots.sector_exposure IS
    'Sector Exposure dimension score (0-100). CLAVIX_TRUTH §6.4.';
COMMENT ON COLUMN public.ticker_risk_snapshots.volatility IS
    'Volatility dimension score (0-100). CLAVIX_TRUTH §6.5.';
COMMENT ON COLUMN public.ticker_risk_snapshots.composite_score IS
    'Equal-weight composite of available dimension scores (0-100). CLAVIX_TRUTH §7.';
COMMENT ON COLUMN public.ticker_risk_snapshots.dimension_inputs IS
    '{dimension: {input_name: value, ...}} — per-dimension input values for audit.';
COMMENT ON COLUMN public.ticker_risk_snapshots.dimension_last_refreshed IS
    '{dimension: "ISO timestamp"} — when each dimension was last computed.';
COMMENT ON COLUMN public.ticker_risk_snapshots.limited_data_dimensions IS
    '["dimension", ...] — dimensions excluded from composite due to limited data.';
