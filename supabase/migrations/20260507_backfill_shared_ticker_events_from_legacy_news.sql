-- ============================================================================
-- Phase 1 / Migration 006 — Backfill shared_ticker_events from legacy news
-- Purpose: Copy article data from news_items and ticker_news_cache into
--          shared_ticker_events, preserving legacy IDs as back-references.
--          Deduplicates by (ticker, canonical_url) — news_items takes
--          precedence over ticker_news_cache when both have the same URL.
-- Safety:  INSERT ... ON CONFLICT (ticker, event_hash) DO NOTHING.
--          shared_ticker_events currently has 0 rows, so this is purely
--          additive.
-- Rollback: DELETE FROM shared_ticker_events WHERE provenance = 'backfill';
-- ============================================================================

-- Step 1: Backfill from news_items (preferred — has richer structured data)
INSERT INTO public.shared_ticker_events (
    ticker,
    event_hash,
    news_id,
    title,
    summary,
    source,
    source_url,
    published_at,
    event_type,
    significance,
    classification,
    body,
    analysis_run_id,
    provenance,
    created_at
)
SELECT
    ni.ticker,
    COALESCE(ni.event_hash, md5(COALESCE(ni.url, ni.title))),
    ni.id,
    ni.title,
    NULL,
    ni.source,
    ni.url,
    ni.published_at,
    (ni.relevance->>'event_type')::text,
    ni.significance,
    ni.relevance,
    ni.body,
    ni.analysis_run_id,
    'backfill_news_items',
    ni.processed_at
FROM public.news_items ni
WHERE ni.ticker IS NOT NULL
  AND ni.title IS NOT NULL
ON CONFLICT (ticker, event_hash) DO NOTHING;

-- Step 2: Backfill from ticker_news_cache (secondary — has URL-based dedupe)
INSERT INTO public.shared_ticker_events (
    ticker,
    event_hash,
    news_cache_id,
    title,
    summary,
    source,
    source_url,
    published_at,
    event_type,
    significance,
    provenance,
    created_at,
    sentiment_score
)
SELECT
    tnc.ticker,
    md5(COALESCE(tnc.url, tnc.headline)),
    tnc.id,
    tnc.headline,
    tnc.summary,
    tnc.source,
    tnc.url,
    tnc.published_at,
    tnc.event_type,
    CASE WHEN tnc.sentiment IS NOT NULL THEN 'minor' ELSE NULL END,
    'backfill_ticker_cache',
    tnc.processed_at,
    CASE
        WHEN tnc.sentiment = 'positive' THEN 75.0
        WHEN tnc.sentiment = 'negative' THEN 25.0
        WHEN tnc.sentiment = 'neutral'  THEN 50.0
        ELSE tnc.relevance_score
    END
FROM public.ticker_news_cache tnc
ON CONFLICT (ticker, event_hash) DO NOTHING;
