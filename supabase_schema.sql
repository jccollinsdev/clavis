-- Clavis Database Schema
-- Apply via Supabase Dashboard > SQL Editor or via Supabase MCP

-- User preferences
CREATE TABLE IF NOT EXISTS public.user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL UNIQUE,
  digest_time TIME DEFAULT '07:00',
  notifications_enabled BOOLEAN DEFAULT true,
  last_manual_refresh_at TIMESTAMPTZ,
  last_analysis_request_at TIMESTAMPTZ,
  apns_token TEXT,
  snaptrade_user_id TEXT,
  snaptrade_user_secret TEXT,
  snaptrade_last_sync_at TIMESTAMPTZ,
  brokerage_auto_sync_enabled BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Holdings/positions
CREATE TABLE IF NOT EXISTS public.positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  ticker TEXT NOT NULL,
  shares NUMERIC NOT NULL,
  purchase_price NUMERIC NOT NULL,
  current_price NUMERIC,
  synced_from_brokerage BOOLEAN NOT NULL DEFAULT false,
  brokerage_authorization_id TEXT,
  brokerage_account_id TEXT,
  brokerage_last_synced_at TIMESTAMPTZ,
  archetype TEXT CHECK (archetype IN ('growth', 'value', 'cyclical', 'defensive', 'small_cap')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Analysis run tracking
CREATE TABLE IF NOT EXISTS public.analysis_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  status TEXT NOT NULL,
  triggered_by TEXT,
  error_message TEXT,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  overall_portfolio_grade TEXT
    CHECK (overall_portfolio_grade IS NULL OR overall_portfolio_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F')),
  positions_processed INTEGER DEFAULT 0,
  events_processed INTEGER DEFAULT 0
);

-- Risk scores per position (history)
CREATE TABLE IF NOT EXISTS public.risk_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  position_id UUID REFERENCES public.positions NOT NULL,
  analysis_run_id UUID REFERENCES public.analysis_runs,
  news_sentiment NUMERIC,
  macro_exposure NUMERIC,
  position_sizing NUMERIC,
  volatility_trend NUMERIC,
  thesis_integrity NUMERIC,
  total_score NUMERIC,
  grade TEXT CHECK (grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F')),
  reasoning TEXT,
  grade_reason TEXT,
  evidence_summary TEXT,
  dimension_rationale JSONB,
  mirofish_used BOOLEAN DEFAULT false,
  calculated_at TIMESTAMPTZ DEFAULT now()
);

-- Filtered news items per position (auto-cleanup after 30 days)
CREATE TABLE IF NOT EXISTS public.news_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  ticker TEXT,
  title TEXT NOT NULL,
  source TEXT,
  url TEXT,
  event_hash TEXT,
  published_at TIMESTAMPTZ,
  body TEXT,
  affected_tickers JSONB,
  relevance JSONB,
  significance TEXT CHECK (significance IN ('major','minor')),
  processed_at TIMESTAMPTZ DEFAULT now()
);

-- Compiled morning digests
CREATE TABLE IF NOT EXISTS public.digests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  analysis_run_id UUID REFERENCES public.analysis_runs,
  content TEXT NOT NULL,
  grade_summary JSONB,
  overall_grade TEXT
    CHECK (overall_grade IS NULL OR overall_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F')),
  overall_score NUMERIC,
  structured_sections JSONB,
  summary TEXT,
  generated_at TIMESTAMPTZ DEFAULT now()
);

-- Price history for charts
CREATE TABLE IF NOT EXISTS public.prices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  price NUMERIC NOT NULL,
  recorded_at TIMESTAMPTZ DEFAULT now()
);

-- Alert history
CREATE TABLE IF NOT EXISTS public.alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  position_ticker TEXT,
  type TEXT CHECK (type IN ('grade_change','major_event','portfolio_grade_change','digest_ready','safety_deterioration','concentration_danger','cluster_risk','macro_shock','structural_fragility','portfolio_safety_threshold_breach')),
  previous_grade TEXT
    CHECK (previous_grade IS NULL OR previous_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F')),
  new_grade TEXT
    CHECK (new_grade IS NULL OR new_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F')),
  event_hash TEXT,
  analysis_run_id UUID REFERENCES public.analysis_runs,
  change_reason TEXT,
  change_details JSONB,
  message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Long-form position analysis artifacts
CREATE TABLE IF NOT EXISTS public.position_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_run_id UUID REFERENCES public.analysis_runs NOT NULL,
  position_id UUID REFERENCES public.positions NOT NULL,
  ticker TEXT NOT NULL,
  inferred_labels JSONB,
  summary TEXT,
  long_report TEXT,
  methodology TEXT,
  top_risks JSONB,
  watch_items JSONB,
  top_news JSONB,
  major_event_count INTEGER DEFAULT 0,
  minor_event_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Per-event analysis artifacts
CREATE TABLE IF NOT EXISTS public.event_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_run_id UUID REFERENCES public.analysis_runs NOT NULL,
  position_id UUID REFERENCES public.positions NOT NULL,
  event_hash TEXT NOT NULL,
  external_event_id TEXT,
  title TEXT NOT NULL,
  summary TEXT,
  source TEXT,
  source_url TEXT,
  published_at TIMESTAMPTZ,
  event_type TEXT,
  significance TEXT CHECK (significance IN ('major','minor')),
  classification JSONB,
  classification_evidence JSONB,
  analysis_source TEXT,
  long_analysis TEXT,
  confidence NUMERIC,
  impact_horizon TEXT,
  risk_direction TEXT,
  scenario_summary TEXT,
  key_implications JSONB,
  recommended_followups JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS on all tables
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.position_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_analyses ENABLE ROW LEVEL SECURITY;

-- RLS policies (unique names per table)
CREATE POLICY "users_own_preferences" ON public.user_preferences FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users_own_positions" ON public.positions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users_own_risk_scores" ON public.risk_scores FOR ALL USING (EXISTS (SELECT 1 FROM public.positions WHERE positions.id = risk_scores.position_id AND positions.user_id = auth.uid()));
CREATE POLICY "users_own_news" ON public.news_items FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users_own_digests" ON public.digests FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users_own_alerts" ON public.alerts FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users_own_prices" ON public.prices FOR SELECT USING (true);
CREATE POLICY "users_own_analysis_runs" ON public.analysis_runs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users_own_position_analyses" ON public.position_analyses FOR ALL USING (EXISTS (SELECT 1 FROM public.positions WHERE positions.id = position_analyses.position_id AND positions.user_id = auth.uid()));
CREATE POLICY "users_own_event_analyses" ON public.event_analyses FOR ALL USING (EXISTS (SELECT 1 FROM public.positions WHERE positions.id = event_analyses.position_id AND positions.user_id = auth.uid()));

-- Auto-cleanup news_items older than 30 days (daily)
CREATE OR REPLACE FUNCTION delete_old_news_items()
RETURNS void AS $$
BEGIN
  DELETE FROM public.news_items WHERE processed_at < now() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a cron job to cleanup old news (requires pg_cron extension)
-- Note: This requires pg_cron to be enabled on your Supabase project
-- ALTER DATABASE postgres SET cron.schedule = '0 3 * * *';
-- SELECT cron.schedule('cleanup-old-news', '0 3 * * *', 'SELECT delete_old_news_items()');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_positions_user_id ON public.positions(user_id);
CREATE INDEX IF NOT EXISTS idx_positions_ticker ON public.positions(ticker);
CREATE INDEX IF NOT EXISTS idx_positions_user_brokerage_account ON public.positions(user_id, brokerage_account_id);
CREATE INDEX IF NOT EXISTS idx_risk_scores_position_id ON public.risk_scores(position_id);
CREATE INDEX IF NOT EXISTS idx_risk_scores_calculated_at ON public.risk_scores(calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_items_user_id ON public.news_items(user_id);
CREATE INDEX IF NOT EXISTS idx_news_items_ticker ON public.news_items(ticker);
CREATE INDEX IF NOT EXISTS idx_news_items_processed_at ON public.news_items(processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_digests_user_id ON public.digests(user_id);
CREATE INDEX IF NOT EXISTS idx_digests_generated_at ON public.digests(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON public.alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON public.alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_prices_ticker ON public.prices(ticker);
CREATE INDEX IF NOT EXISTS idx_prices_recorded_at ON public.prices(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_user_id ON public.analysis_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_started_at ON public.analysis_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_position_analyses_run_id ON public.position_analyses(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_position_analyses_position_id ON public.position_analyses(position_id);
CREATE INDEX IF NOT EXISTS idx_event_analyses_run_id ON public.event_analyses(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_event_analyses_position_id ON public.event_analyses(position_id);
CREATE INDEX IF NOT EXISTS idx_event_analyses_event_hash ON public.event_analyses(event_hash);

-- Current production extensions from later migrations
ALTER TABLE public.user_preferences
  ADD COLUMN IF NOT EXISTS summary_length TEXT DEFAULT 'standard' CHECK (summary_length IS NULL OR summary_length IN ('brief', 'standard', 'verbose')),
  ADD COLUMN IF NOT EXISTS weekday_only BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS alerts_grade_changes BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS alerts_major_events BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS alerts_portfolio_risk BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS alerts_large_price_moves BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS quiet_hours_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS quiet_hours_start TIME DEFAULT '22:00',
  ADD COLUMN IF NOT EXISTS quiet_hours_end TIME DEFAULT '07:00',
  ADD COLUMN IF NOT EXISTS has_completed_onboarding BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS onboarding_acknowledged_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS name TEXT,
  ADD COLUMN IF NOT EXISTS birth_year INTEGER,
  ADD COLUMN IF NOT EXISTS subscription_tier TEXT DEFAULT 'free',
  ADD COLUMN IF NOT EXISTS snaptrade_user_id TEXT,
  ADD COLUMN IF NOT EXISTS snaptrade_user_secret TEXT,
  ADD COLUMN IF NOT EXISTS snaptrade_last_sync_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS brokerage_auto_sync_enabled BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE public.positions
  ADD COLUMN IF NOT EXISTS synced_from_brokerage BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS brokerage_authorization_id TEXT,
  ADD COLUMN IF NOT EXISTS brokerage_account_id TEXT,
  ADD COLUMN IF NOT EXISTS brokerage_last_synced_at TIMESTAMPTZ;

ALTER TABLE public.analysis_runs
  ADD COLUMN IF NOT EXISTS current_stage TEXT,
  ADD COLUMN IF NOT EXISTS current_stage_message TEXT,
  ADD COLUMN IF NOT EXISTS target_position_id UUID REFERENCES public.positions,
  ADD COLUMN IF NOT EXISTS target_ticker TEXT,
  ADD COLUMN IF NOT EXISTS target_tickers JSONB;

ALTER TABLE public.risk_scores
  ADD COLUMN IF NOT EXISTS analysis_run_id UUID REFERENCES public.analysis_runs,
  ADD COLUMN IF NOT EXISTS grade_reason TEXT,
  ADD COLUMN IF NOT EXISTS evidence_summary TEXT,
  ADD COLUMN IF NOT EXISTS dimension_rationale JSONB;

ALTER TABLE public.news_items
  ADD COLUMN IF NOT EXISTS analysis_run_id UUID REFERENCES public.analysis_runs,
  ADD COLUMN IF NOT EXISTS event_hash TEXT,
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS body TEXT,
  ADD COLUMN IF NOT EXISTS affected_tickers JSONB,
  ADD COLUMN IF NOT EXISTS relevance JSONB;

ALTER TABLE public.digests
  ADD COLUMN IF NOT EXISTS analysis_run_id UUID REFERENCES public.analysis_runs,
  ADD COLUMN IF NOT EXISTS overall_grade TEXT,
  ADD COLUMN IF NOT EXISTS overall_score NUMERIC,
  ADD COLUMN IF NOT EXISTS structured_sections JSONB,
  ADD COLUMN IF NOT EXISTS summary TEXT;

ALTER TABLE public.position_analyses
  ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ready',
  ADD COLUMN IF NOT EXISTS progress_message TEXT,
  ADD COLUMN IF NOT EXISTS source_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

CREATE TABLE IF NOT EXISTS public.scheduler_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL UNIQUE,
  job_id TEXT NOT NULL,
  digest_time TIME DEFAULT '07:00',
  notifications_enabled BOOLEAN DEFAULT FALSE,
  active BOOLEAN DEFAULT FALSE,
  last_scheduled_at TIMESTAMPTZ,
  next_run_at TIMESTAMPTZ,
  last_run_at TIMESTAMPTZ,
  last_run_status TEXT,
  last_error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.scheduler_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_scheduler_jobs" ON public.scheduler_jobs FOR ALL USING (auth.uid() = user_id);

CREATE TABLE IF NOT EXISTS public.analysis_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind TEXT NOT NULL,
  cache_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.analysis_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_analysis_cache" ON public.analysis_cache
  FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

CREATE TABLE IF NOT EXISTS public.ticker_universe (
  ticker TEXT PRIMARY KEY,
  company_name TEXT NOT NULL,
  exchange TEXT,
  sector TEXT,
  industry TEXT,
  index_membership TEXT NOT NULL DEFAULT 'SP500',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  priority_rank INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.ticker_universe ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.ticker_risk_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL REFERENCES public.ticker_universe(ticker) ON DELETE CASCADE,
  snapshot_date DATE NOT NULL,
  snapshot_type TEXT NOT NULL CHECK (snapshot_type IN ('daily', 'manual_refresh', 'backfill')),
  grade TEXT
    CHECK (grade IS NULL OR grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F')),
  safety_score NUMERIC,
  structural_base_score NUMERIC,
  macro_adjustment NUMERIC,
  event_adjustment NUMERIC,
  confidence NUMERIC,
  factor_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
  dimension_rationale JSONB,
  reasoning TEXT,
  news_summary TEXT,
  source_count INTEGER,
  methodology_version TEXT,
  analysis_as_of TIMESTAMPTZ NOT NULL,
  refresh_triggered_by_user_id UUID,

  -- V2 dimension columns (Phase 1 / migration 003)
  financial_health     NUMERIC,
  news_sentiment_dim   NUMERIC,
  macro_exposure_dim   NUMERIC,
  sector_exposure      NUMERIC,
  volatility           NUMERIC,
  composite_score      NUMERIC,
  dimension_inputs     JSONB DEFAULT '{}'::jsonb,
  dimension_last_refreshed JSONB DEFAULT '{}'::jsonb,
  limited_data_dimensions   JSONB DEFAULT '[]'::jsonb,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (ticker, snapshot_date, snapshot_type)
);

ALTER TABLE public.ticker_risk_snapshots ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.ticker_news_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL REFERENCES public.ticker_universe(ticker) ON DELETE CASCADE,
  headline TEXT NOT NULL,
  summary TEXT,
  url TEXT NOT NULL,
  source TEXT,
  published_at TIMESTAMPTZ,
  sentiment TEXT,
  relevance_score NUMERIC,
  event_type TEXT,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.ticker_news_cache ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.ticker_refresh_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL REFERENCES public.ticker_universe(ticker) ON DELETE CASCADE,
  job_type TEXT NOT NULL CHECK (job_type IN ('daily', 'manual_refresh', 'backfill')),
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),
  requested_by_user_id UUID,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.ticker_refresh_jobs ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.watchlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  name TEXT NOT NULL DEFAULT 'Watchlist',
  is_default BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.watchlist_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  watchlist_id UUID NOT NULL REFERENCES public.watchlists(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL REFERENCES public.ticker_universe(ticker) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (watchlist_id, ticker)
);

ALTER TABLE public.watchlist_items ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- V2 / Phase 1 reconciled tables
-- ============================================================================

-- ticker_metadata — Company fundamentals metadata cache
CREATE TABLE IF NOT EXISTS public.ticker_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL UNIQUE,
    company_name TEXT,
    asset_class TEXT CHECK (asset_class IN ('treasury', 'large_cap_equity', 'mid_cap_equity', 'small_cap_equity', 'adr', 'biotech', 'penny_stock', 'etf', 'other')),
    sector TEXT,
    industry TEXT,
    exchange TEXT,
    market_cap NUMERIC,
    market_cap_bucket TEXT CHECK (market_cap_bucket IN ('very_high', 'high', 'moderate_high', 'moderate', 'low_moderate', 'low', 'very_low')),
    float_shares NUMERIC,
    avg_daily_dollar_volume NUMERIC,
    beta NUMERIC,
    volatility_proxy NUMERIC,
    profitability_profile TEXT CHECK (profitability_profile IN ('profitable', 'mixed', 'unprofitable')),
    leverage_profile TEXT CHECK (leverage_profile IN ('low', 'moderate', 'high', 'very_high')),
    macro_sensitivity TEXT CHECK (macro_sensitivity IN ('low', 'moderate', 'high', 'very_high')),
    structural_fragility NUMERIC,
    liquidity_risk NUMERIC,
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
    is_supported BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.ticker_metadata ENABLE ROW LEVEL SECURITY;

-- asset_safety_profiles — Daily structural safety snapshot
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

-- macro_regime_snapshots — Daily shared macro state
CREATE TABLE IF NOT EXISTS public.macro_regime_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    as_of_date DATE NOT NULL UNIQUE,
    regime_state TEXT CHECK (regime_state IN ('risk_on', 'risk_off', 'rates_up', 'rates_down', 'credit_tightening', 'credit_easing', 'inflation_shock', 'commodity_shock', 'recession_pressure', 'expansion_supportive', 'neutral')),
    rates_signal TEXT CHECK (rates_signal IN ('rising', 'falling', 'stable')),
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

-- portfolio_risk_snapshots — Per-user portfolio risk rollup
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

-- shared_ticker_events — Canonical event/article store (v2 consolidated news store)
CREATE TABLE IF NOT EXISTS public.shared_ticker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    external_event_id TEXT,
    news_id UUID REFERENCES public.news_items(id),
    news_cache_id UUID REFERENCES public.ticker_news_cache(id),
    title TEXT NOT NULL,
    summary TEXT,
    source TEXT,
    source_url TEXT,
    published_at TIMESTAMPTZ,
    event_type TEXT,
    significance TEXT CHECK (significance IN ('major', 'minor')),
    classification JSONB,
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
    analysis_run_id UUID REFERENCES public.analysis_runs(id),
    factored_into_score BOOLEAN DEFAULT false,
    provenance TEXT DEFAULT 'shared',
    methodology_version TEXT,

    -- V2 sentiment & audit fields (Phase 1 / migration 004)
    body              TEXT,
    canonical_url     TEXT,
    sentiment_score   NUMERIC CHECK (sentiment_score IS NULL OR (sentiment_score >= 0 AND sentiment_score <= 100)),
    sentiment_reason  TEXT,
    source_tier       INTEGER CHECK (source_tier IS NULL OR source_tier IN (1, 2, 3)),
    recency_weight    NUMERIC,
    source_weight     NUMERIC,
    impact_tag        TEXT CHECK (impact_tag IS NULL OR impact_tag IN ('financial-impact', 'regulatory', 'leadership', 'product', 'macro', 'sector', 'other')),
    extraction_status TEXT,
    paywalled         BOOLEAN DEFAULT false,
    article_window    TEXT CHECK (article_window IS NULL OR article_window IN ('last_24h', '24_72h', '72h_7d')),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (ticker, event_hash)
);

ALTER TABLE public.shared_ticker_events ENABLE ROW LEVEL SECURITY;

-- sector_regime_snapshots — Daily per-sector quantitative and narrative state
CREATE TABLE IF NOT EXISTS public.sector_regime_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    sector_beta      NUMERIC,
    sector_momentum  NUMERIC,
    sector_breadth   NUMERIC,
    sector_score     NUMERIC,
    narrative_text   TEXT,
    narrative_last_refreshed TIMESTAMPTZ,
    regulatory_risk  TEXT,
    supply_chain_risk TEXT,
    demand_cycle_risk TEXT,
    source_etf TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (sector, snapshot_date)
);

ALTER TABLE public.sector_regime_snapshots ENABLE ROW LEVEL SECURITY;
