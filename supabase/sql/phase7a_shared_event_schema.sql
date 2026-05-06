-- ============================================================================
-- Phase 7A — Shared Ticker Event Architecture Proposal
-- Purpose: Add a shared_ticker_events table as the canonical source for
--          analyzed event data per ticker, eliminating position-level
--          duplication while keeping legacy event_analyses for history.
--
-- CRITICAL: DO NOT RUN on production. This is a design proposal.
--           All DDL below requires review, dry-run SQL, and explicit approval.
-- ============================================================================

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. NEW TABLE: shared_ticker_events
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.shared_ticker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    external_event_id TEXT,
    news_id UUID REFERENCES public.news_items(id),
    news_cache_id UUID REFERENCES public.ticker_news_cache(id),

    -- Event content
    title TEXT NOT NULL,
    summary TEXT,
    source TEXT,
    source_url TEXT,
    published_at TIMESTAMPTZ,

    -- Classification
    event_type TEXT,
    significance TEXT CHECK (significance IN ('major', 'minor')),
    classification JSONB,

    -- Analysis (LLM-generated)
    analysis_source TEXT,
    what_happened TEXT,
    tldr TEXT,
    what_it_means TEXT,
    long_analysis TEXT,
    confidence NUMERIC CHECK (confidence >= 0 AND confidence <= 1),
    impact_horizon TEXT CHECK (impact_horizon IN ('immediate', 'near_term', 'long_term')),
    risk_direction TEXT CHECK (risk_direction IN ('improving', 'neutral', 'worsening')),
    scenario_summary TEXT,
    key_implications JSONB,
    follow_up_notes JSONB,
    tags JSONB DEFAULT '[]'::jsonb,

    -- Provenance
    analysis_run_id UUID REFERENCES public.analysis_runs(id),
    factored_into_score BOOLEAN DEFAULT false,
    provenance TEXT DEFAULT 'shared',
    methodology_version TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_shared_ticker_events_ticker
    ON public.shared_ticker_events(ticker);
CREATE INDEX IF NOT EXISTS idx_shared_ticker_events_event_hash
    ON public.shared_ticker_events(event_hash);
CREATE INDEX IF NOT EXISTS idx_shared_ticker_events_ticker_date
    ON public.shared_ticker_events(ticker, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_shared_ticker_events_run_id
    ON public.shared_ticker_events(analysis_run_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_shared_ticker_events_hash
    ON public.shared_ticker_events(ticker, event_hash);

-- RLS: Users can read any shared ticker event (it's public data)
ALTER TABLE public.shared_ticker_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anyone_can_read_shared_ticker_events"
    ON public.shared_ticker_events
    FOR SELECT
    USING (true);


-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. ADD COLUMN to event_analyses: shared_event_id (nullable back-reference)
-- ============================================================================

ALTER TABLE public.event_analyses
    ADD COLUMN IF NOT EXISTS shared_event_id UUID
    REFERENCES public.shared_ticker_events(id)
    ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_event_analyses_shared_event_id
    ON public.event_analyses(shared_event_id);


-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. BACKFILL MAPPING QUERY (dry-run: group duplicates by event_hash)
-- ============================================================================

-- This query shows the mapping from existing duplicate event_analyses rows
-- to the proposed shared_ticker_events rows for a specific ticker.
-- Run this FIRST as a dry-run before any backfill.

/*
WITH ticker_events AS (
    SELECT
        ea.event_hash,
        ea.title,
        ea.source,
        ea.source_url,
        ea.published_at,
        ea.event_type,
        ea.significance,
        ea.classification,
        ea.analysis_source,
        ea.what_happened,
        ea.tldr,
        ea.what_it_means,
        ea.long_analysis,
        ea.confidence,
        ea.impact_horizon,
        ea.risk_direction,
        ea.scenario_summary,
        ea.key_implications,
        ea.recommended_followups AS follow_up_notes,
        ea.analysis_run_id,
        ea.created_at,
        COUNT(*) OVER (PARTITION BY ea.event_hash) AS duplicate_count,
        ROW_NUMBER() OVER (
            PARTITION BY ea.event_hash
            ORDER BY ea.confidence DESC NULLS LAST, ea.created_at DESC
        ) AS rn
    FROM event_analyses ea
    JOIN positions p ON p.id = ea.position_id
    WHERE p.ticker = 'AMD'  -- replace with any ticker
)
SELECT
    event_hash,
    title,
    duplicate_count,
    -- Pick the best (highest confidence, most recent) row for each hash
    MAX(source) FILTER (WHERE rn = 1) AS best_source,
    MAX(confidence) FILTER (WHERE rn = 1) AS best_confidence,
    MAX(what_happened) FILTER (WHERE rn = 1) AS best_what_happened,
    MAX(tldr) FILTER (WHERE rn = 1) AS best_tldr,
    MAX(what_it_means) FILTER (WHERE rn = 1) AS best_what_it_means
FROM ticker_events
GROUP BY event_hash, title, duplicate_count
ORDER BY duplicate_count DESC;
*/


-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. BACKFILL COUNT QUERY (how many shared events would be created?)
-- ============================================================================

/*
WITH event_tickers AS (
    SELECT DISTINCT
        ea.event_hash,
        p.ticker
    FROM event_analyses ea
    JOIN positions p ON p.id = ea.position_id
    WHERE p.ticker IS NOT NULL
)
SELECT
    COUNT(DISTINCT CONCAT(ticker, ':', event_hash)) AS shared_event_rows_needed,
    COUNT(DISTINCT ticker) AS unique_tickers,
    COUNT(DISTINCT event_hash) AS unique_event_hashes
FROM event_tickers;
*/


-- ═══════════════════════════════════════════════════════════════════════════════
-- 5. ROLLBACK PLAN
-- ============================================================================
-- Since shared_ticker_events is a NEW table (no existing data depends on it):
--   1. Drop the shared_event_id column from event_analyses
--   2. Drop the shared_ticker_events table
--   3. Both are reversible with zero data loss to existing event_analyses rows.
--
-- If backfill is applied and needs reversal:
--   1. Restore event_analyses from Supabase PITR to pre-backfill state
--   2. Drop shared_ticker_events table
--   3. Drop shared_event_id column from event_analyses


-- ═══════════════════════════════════════════════════════════════════════════════
-- 6. TABLE AFFECTED SUMMARY
-- ============================================================================
-- NEW: public.shared_ticker_events (canonical shared event repository)
-- MODIFIED: public.event_analyses (add shared_event_id column, nullable FK)
-- UNCHANGED: positions, news_items, ticker_news_cache, position_analyses,
--            analysis_runs, ticker_risk_snapshots, digests, alerts
