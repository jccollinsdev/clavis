-- ============================================================================
-- Phase P4 — Portfolio rollup snapshots
-- Purpose: Add v2 portfolio composite fields used by Today/Holdings envelopes.
-- Safety:  Additive only.
-- ============================================================================

ALTER TABLE public.portfolio_risk_snapshots
    ADD COLUMN IF NOT EXISTS portfolio_value NUMERIC,
    ADD COLUMN IF NOT EXISTS composite_score NUMERIC,
    ADD COLUMN IF NOT EXISTS grade TEXT
        CHECK (grade IS NULL OR grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F')),
    ADD COLUMN IF NOT EXISTS previous_score NUMERIC,
    ADD COLUMN IF NOT EXISTS score_delta NUMERIC,
    ADD COLUMN IF NOT EXISTS dimensions JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS sector_breakdown JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_portfolio_risk_snapshots_user_as_of
    ON public.portfolio_risk_snapshots(user_id, as_of_date DESC);
