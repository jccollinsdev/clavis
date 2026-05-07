-- ============================================================================
-- Phase 1 / Migration 005 — Sector Regime Snapshots
-- Purpose: Create shared per-sector quantitative and narrative state table
--          for digest sector heat, sector exposure audit, and cost sharing
--          per CLAVIX_TRUTH §6.4 and §9.
-- Safety:  CREATE TABLE IF NOT EXISTS. No destructive operations.
-- Rollback: DROP TABLE IF EXISTS public.sector_regime_snapshots;
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.sector_regime_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector TEXT NOT NULL,
    snapshot_date DATE NOT NULL,

    -- Quantitative layer
    sector_beta      NUMERIC,
    sector_momentum  NUMERIC,
    sector_breadth   NUMERIC,
    sector_score     NUMERIC,

    -- Narrative layer
    narrative_text   TEXT,
    narrative_last_refreshed TIMESTAMPTZ,
    regulatory_risk  TEXT,
    supply_chain_risk TEXT,
    demand_cycle_risk TEXT,

    -- Metadata
    source_etf TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (sector, snapshot_date)
);

ALTER TABLE public.sector_regime_snapshots ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'authenticated_read_sector_regime_snapshots'
          AND tablename = 'sector_regime_snapshots'
    ) THEN
        EXECUTE 'CREATE POLICY "authenticated_read_sector_regime_snapshots"
            ON public.sector_regime_snapshots FOR SELECT
            USING (auth.role() = ''authenticated'')';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_sector_regime_snapshots_sector_date
    ON public.sector_regime_snapshots(sector, snapshot_date DESC);

COMMENT ON TABLE public.sector_regime_snapshots IS
    'Daily shared per-sector quantitative scores and narrative text for digest and sector audit.';
