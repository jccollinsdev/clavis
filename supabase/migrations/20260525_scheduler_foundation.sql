-- ============================================================================
-- Phase P3 — Scheduler foundation
-- Purpose: Add auditable job runs, advisory-lock RPC helpers, and additive
--          macro/sector snapshot columns needed by cron-launched jobs.
-- Safety:  All changes are additive and idempotent.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'cron',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (
        status IN ('running', 'completed', 'failed', 'skipped', 'skipped_lock')
    ),
    items_processed INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    items_failed INTEGER NOT NULL DEFAULT 0,
    error_json JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.job_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_manage_job_runs" ON public.job_runs;
CREATE POLICY "service_role_manage_job_runs"
    ON public.job_runs
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_job_runs_job_started
    ON public.job_runs(job_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_job_runs_status_started
    ON public.job_runs(status, started_at DESC);

COMMENT ON TABLE public.job_runs IS
    'One row per scheduled or cron-launched job invocation.';

CREATE OR REPLACE FUNCTION public.clavix_try_advisory_lock(lock_name TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
AS $$
    SELECT pg_try_advisory_lock(hashtextextended(lock_name, 0));
$$;

CREATE OR REPLACE FUNCTION public.clavix_advisory_unlock(lock_name TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
AS $$
    SELECT pg_advisory_unlock(hashtextextended(lock_name, 0));
$$;

REVOKE ALL ON FUNCTION public.clavix_try_advisory_lock(TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.clavix_advisory_unlock(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.clavix_try_advisory_lock(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.clavix_advisory_unlock(TEXT) TO service_role;

ALTER TABLE public.macro_regime_snapshots
    ADD COLUMN IF NOT EXISTS vix_day_change NUMERIC,
    ADD COLUMN IF NOT EXISTS ust10y_level NUMERIC,
    ADD COLUMN IF NOT EXISTS ust10y_day_change NUMERIC,
    ADD COLUMN IF NOT EXISTS dxy_level NUMERIC,
    ADD COLUMN IF NOT EXISTS dxy_day_change NUMERIC,
    ADD COLUMN IF NOT EXISTS wti_level NUMERIC,
    ADD COLUMN IF NOT EXISTS wti_day_change NUMERIC,
    ADD COLUMN IF NOT EXISTS spy_close NUMERIC,
    ADD COLUMN IF NOT EXISTS spy_day_change_pct NUMERIC,
    ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS data_status TEXT;

ALTER TABLE public.sector_regime_snapshots
    ADD COLUMN IF NOT EXISTS etf_day_change_pct NUMERIC,
    ADD COLUMN IF NOT EXISTS breadth NUMERIC,
    ADD COLUMN IF NOT EXISTS momentum NUMERIC,
    ADD COLUMN IF NOT EXISTS data_status TEXT;
