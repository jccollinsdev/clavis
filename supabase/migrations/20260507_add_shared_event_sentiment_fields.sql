-- ============================================================================
-- Phase 1 / Migration 004 — Article Sentiment & Audit Fields
-- Purpose: Add per-article sentiment scoring, source weighting, content
--          extraction, and audit metadata to shared_ticker_events so it
--          can serve as the single article store for News Sentiment
--          audit pages and methodology drill-downs.
-- Safety:  All columns are nullable. shared_ticker_events currently has
--          0 rows, so no existing data is affected. All additions are
--          ADD COLUMN IF NOT EXISTS.
-- Rollback: ALTER TABLE ... DROP COLUMN for each column.
-- ============================================================================

ALTER TABLE public.shared_ticker_events
    ADD COLUMN IF NOT EXISTS body              TEXT,
    ADD COLUMN IF NOT EXISTS canonical_url     TEXT,
    ADD COLUMN IF NOT EXISTS sentiment_score   NUMERIC
        CHECK (sentiment_score IS NULL OR (sentiment_score >= 0 AND sentiment_score <= 100)),
    ADD COLUMN IF NOT EXISTS sentiment_reason  TEXT,
    ADD COLUMN IF NOT EXISTS source_tier       INTEGER
        CHECK (source_tier IS NULL OR source_tier IN (1, 2, 3)),
    ADD COLUMN IF NOT EXISTS recency_weight    NUMERIC,
    ADD COLUMN IF NOT EXISTS source_weight     NUMERIC,
    ADD COLUMN IF NOT EXISTS impact_tag        TEXT
        CHECK (impact_tag IS NULL OR impact_tag IN (
            'financial-impact', 'regulatory', 'leadership', 'product',
            'macro', 'sector', 'other')),
    ADD COLUMN IF NOT EXISTS extraction_status TEXT,
    ADD COLUMN IF NOT EXISTS paywalled         BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS article_window    TEXT
        CHECK (article_window IS NULL OR article_window IN ('last_24h', '24_72h', '72h_7d'));

COMMENT ON COLUMN public.shared_ticker_events.body IS
    'Extracted article body (clean text from Jina/trafilatura/newspaper).';
COMMENT ON COLUMN public.shared_ticker_events.canonical_url IS
    'Normalized article URL with tracking params stripped.';
COMMENT ON COLUMN public.shared_ticker_events.sentiment_score IS
    '0-100 sentiment score assigned by the LLM.';
COMMENT ON COLUMN public.shared_ticker_events.sentiment_reason IS
    'Short explanation for why this article received its sentiment score.';
COMMENT ON COLUMN public.shared_ticker_events.source_tier IS
    'Source quality: 1=Tier1 (Reuters,WSJ,BBG,FT,AP), 2=Tier2 (MW,YF,SA,CNBC), 3=Tier3 (aggregators,blogs).';
COMMENT ON COLUMN public.shared_ticker_events.recency_weight IS
    'Multiplier for recency: last_24h=3.0, 24_72h=2.0, 72h_7d=1.0.';
COMMENT ON COLUMN public.shared_ticker_events.source_weight IS
    'Multiplier for source quality: T1=1.5, T2=1.0, T3=0.5.';
COMMENT ON COLUMN public.shared_ticker_events.impact_tag IS
    'High-level category of the article impact.';
COMMENT ON COLUMN public.shared_ticker_events.extraction_status IS
    'success, partial, failed, or null (not yet extracted).';
COMMENT ON COLUMN public.shared_ticker_events.paywalled IS
    'True if the source is paywalled and body extraction was not possible.';
COMMENT ON COLUMN public.shared_ticker_events.article_window IS
    'Which recency bucket the article falls into for weight calculation.';
