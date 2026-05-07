-- ============================================================================
-- Phase 1 / Migration 001 — Reconcile repo schema with live DB
-- Purpose: Add tables, columns, constraints, indexes, and RLS policies that
--          exist on the live Supabase DB but are absent from supabase_schema.sql.
-- Safety:  ALL statements use IF NOT EXISTS / ADD COLUMN IF NOT EXISTS so
--          this migration is idempotent and safe to run against the live DB
--          without any destructive effect.
-- Rollback: No rollback needed. This migration only declares what already
--           exists in production. If we ever need to undo, the live artifacts
--           remain untouched.
-- ============================================================================

-- ════════════════════════════════════════════════════════════════════════
-- 1. asset_safety_profiles — Daily structural safety snapshot per ticker
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.asset_safety_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    structural_base_score NUMERIC,
    macro_adjustment NUMERIC,
    event_adjustment NUMERIC,
    safety_score NUMERIC,
    confidence NUMERIC,
    asset_class TEXT,
    regime_state TEXT,
    market_cap_bucket TEXT,
    liquidity_score NUMERIC,
    volatility_score NUMERIC,
    leverage_score NUMERIC,
    profitability_score NUMERIC,
    macro_sensitivity_score NUMERIC,
    event_risk_score NUMERIC,
    factor_breakdown JSONB,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (ticker, as_of_date)
);

ALTER TABLE public.asset_safety_profiles ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_asset_safety_profiles_ticker
    ON public.asset_safety_profiles(ticker);

CREATE INDEX IF NOT EXISTS idx_asset_safety_profiles_date
    ON public.asset_safety_profiles(as_of_date DESC);

-- ════════════════════════════════════════════════════════════════════════
-- 2. macro_regime_snapshots — Daily shared macro regime state
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.macro_regime_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    as_of_date DATE NOT NULL UNIQUE,
    regime_state TEXT
        CHECK (regime_state IN ('risk_on', 'risk_off', 'rates_up', 'rates_down',
               'credit_tightening', 'credit_easing', 'inflation_shock',
               'commodity_shock', 'recession_pressure', 'expansion_supportive',
               'neutral')),
    rates_signal TEXT  CHECK (rates_signal IN ('rising', 'falling', 'stable')),
    credit_signal TEXT CHECK (credit_signal IN ('tightening', 'easing', 'stable')),
    inflation_signal TEXT CHECK (inflation_signal IN ('spiking', 'moderating', 'stable')),
    growth_signal TEXT CHECK (growth_signal IN ('expanding', 'contracting', 'stable')),
    risk_on_off_signal TEXT CHECK (risk_on_off_signal IN ('risk_on', 'risk_off', 'neutral')),
    vix_level NUMERIC,
    credit_spread_level NUMERIC,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.macro_regime_snapshots ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_macro_regime_snapshots_date
    ON public.macro_regime_snapshots(as_of_date DESC);

-- ════════════════════════════════════════════════════════════════════════
-- 3. portfolio_risk_snapshots — Per-user portfolio risk rollup
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.portfolio_risk_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users NOT NULL,
    as_of_date DATE NOT NULL,
    portfolio_allocation_risk_score NUMERIC,
    confidence NUMERIC,
    concentration_risk NUMERIC,
    cluster_risk NUMERIC,
    correlation_risk NUMERIC,
    liquidity_mismatch NUMERIC,
    macro_stack_risk NUMERIC,
    factor_breakdown JSONB,
    top_risk_drivers JSONB,
    danger_clusters JSONB,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, as_of_date)
);

ALTER TABLE public.portfolio_risk_snapshots ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_portfolio_risk_snapshots_user_date
    ON public.portfolio_risk_snapshots(user_id, as_of_date DESC);

-- ════════════════════════════════════════════════════════════════════════
-- 4. ticker_metadata — Company/fundamentals metadata cache per ticker
-- ════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.ticker_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL UNIQUE,
    company_name TEXT,
    asset_class TEXT
        CHECK (asset_class IN ('treasury', 'large_cap_equity', 'mid_cap_equity',
               'small_cap_equity', 'adr', 'biotech', 'penny_stock', 'etf', 'other')),
    sector TEXT,
    industry TEXT,
    exchange TEXT,
    market_cap NUMERIC,
    market_cap_bucket TEXT
        CHECK (market_cap_bucket IN ('very_high', 'high', 'moderate_high',
               'moderate', 'low_moderate', 'low', 'very_low')),
    float_shares NUMERIC,
    avg_daily_dollar_volume NUMERIC,
    spread_proxy NUMERIC,
    beta NUMERIC,
    volatility_proxy NUMERIC,
    profitability_profile TEXT
        CHECK (profitability_profile IN ('profitable', 'mixed', 'unprofitable')),
    leverage_profile TEXT
        CHECK (leverage_profile IN ('low', 'moderate', 'high', 'very_high')),
    macro_sensitivity TEXT
        CHECK (macro_sensitivity IN ('low', 'moderate', 'high', 'very_high')),
    structural_fragility NUMERIC,
    liquidity_risk NUMERIC,
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    pe_ratio NUMERIC,
    week_52_high NUMERIC,
    week_52_low NUMERIC,
    price NUMERIC,
    price_as_of TIMESTAMPTZ,
    avg_volume NUMERIC,
    previous_close NUMERIC,
    open_price NUMERIC,
    day_high NUMERIC,
    day_low NUMERIC,
    last_price_source TEXT,
    is_supported BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE public.ticker_metadata ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_ticker_metadata_ticker
    ON public.ticker_metadata(ticker);

-- ════════════════════════════════════════════════════════════════════════
-- 5. Additional live indexes not declared in supabase_schema.sql
-- ════════════════════════════════════════════════════════════════════════
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_cache_kind_key
    ON public.analysis_cache(kind, cache_key);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_target_position_id
    ON public.analysis_runs(target_position_id);

CREATE INDEX IF NOT EXISTS idx_position_analyses_updated_at
    ON public.position_analyses(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_user_id
    ON public.scheduler_jobs(user_id);

CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_active
    ON public.scheduler_jobs(active);

CREATE INDEX IF NOT EXISTS idx_ticker_refresh_jobs_ticker_created_at
    ON public.ticker_refresh_jobs(ticker, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ticker_refresh_jobs_status_created_at
    ON public.ticker_refresh_jobs(status, created_at);

CREATE INDEX IF NOT EXISTS idx_ticker_universe_company_name
    ON public.ticker_universe(company_name);

CREATE INDEX IF NOT EXISTS idx_ticker_universe_priority_rank
    ON public.ticker_universe(priority_rank);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id
    ON public.watchlists(user_id);

CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist_id
    ON public.watchlist_items(watchlist_id);

-- ════════════════════════════════════════════════════════════════════════
-- 6. RLS policies for reconciled tables
-- ════════════════════════════════════════════════════════════════════════

-- asset_safety_profiles: authenticated users can read; service_role can manage
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'authenticated_read_asset_safety_profiles'
          AND tablename = 'asset_safety_profiles'
    ) THEN
        EXECUTE 'CREATE POLICY "authenticated_read_asset_safety_profiles"
            ON public.asset_safety_profiles FOR SELECT
            USING (auth.role() = ''authenticated'')';
    END IF;
END $$;

-- macro_regime_snapshots: authenticated can read; service_role can manage
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'authenticated_read_macro_regime_snapshots'
          AND tablename = 'macro_regime_snapshots'
    ) THEN
        EXECUTE 'CREATE POLICY "authenticated_read_macro_regime_snapshots"
            ON public.macro_regime_snapshots FOR SELECT
            USING (auth.role() = ''authenticated'')';
    END IF;
END $$;

-- portfolio_risk_snapshots: users own their own rows
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'users_own_portfolio_risk_snapshots'
          AND tablename = 'portfolio_risk_snapshots'
    ) THEN
        EXECUTE 'CREATE POLICY "users_own_portfolio_risk_snapshots"
            ON public.portfolio_risk_snapshots FOR ALL
            USING (auth.uid() = user_id)';
    END IF;
END $$;

-- ticker_metadata: authenticated can read; service_role can manage
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'authenticated_read_ticker_metadata'
          AND tablename = 'ticker_metadata'
    ) THEN
        EXECUTE 'CREATE POLICY "authenticated_read_ticker_metadata"
            ON public.ticker_metadata FOR SELECT
            USING (auth.role() = ''authenticated'')';
    END IF;
END $$;

-- watchlists: users own their own rows
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'users_own_watchlists'
          AND tablename = 'watchlists'
    ) THEN
        EXECUTE 'CREATE POLICY "users_own_watchlists"
            ON public.watchlists FOR ALL
            USING (auth.uid() = user_id)';
    END IF;
END $$;

-- watchlist_items: users access via their watchlist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'users_own_watchlist_items'
          AND tablename = 'watchlist_items'
    ) THEN
        EXECUTE 'CREATE POLICY "users_own_watchlist_items"
            ON public.watchlist_items FOR ALL
            USING (EXISTS (
                SELECT 1 FROM public.watchlists
                WHERE watchlists.id = watchlist_items.watchlist_id
                  AND watchlists.user_id = auth.uid()
            ))';
    END IF;
END $$;

-- ticker_universe: authenticated can read; service_role can manage
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'authenticated_read_ticker_universe'
          AND tablename = 'ticker_universe'
    ) THEN
        EXECUTE 'CREATE POLICY "authenticated_read_ticker_universe"
            ON public.ticker_universe FOR SELECT
            USING (auth.role() = ''authenticated'')';
    END IF;
END $$;

-- ticker_refresh_jobs: authenticated can read; service_role can manage
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'authenticated_read_ticker_refresh_jobs'
          AND tablename = 'ticker_refresh_jobs'
    ) THEN
        EXECUTE 'CREATE POLICY "authenticated_read_ticker_refresh_jobs"
            ON public.ticker_refresh_jobs FOR SELECT
            USING (auth.role() = ''authenticated'')';
    END IF;
END $$;
