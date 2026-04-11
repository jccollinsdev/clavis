-- Phase 1 + 2: Risk Calibration Build
-- Adds new safety scoring fields, ticker_metadata, and asset_safety_profiles tables

-- 1. Add new safety fields to risk_scores (backward compat - nullable first)
ALTER TABLE public.risk_scores
ADD COLUMN IF NOT EXISTS confidence NUMERIC,
ADD COLUMN IF NOT EXISTS structural_base_score NUMERIC,
ADD COLUMN IF NOT EXISTS macro_adjustment NUMERIC,
ADD COLUMN IF NOT EXISTS event_adjustment NUMERIC,
ADD COLUMN IF NOT EXISTS safety_score NUMERIC,
ADD COLUMN IF NOT EXISTS factor_breakdown JSONB;

-- 2. Create ticker_metadata table (slowly changing per-ticker data)
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
  spread_proxy NUMERIC,
  beta NUMERIC,
  volatility_proxy NUMERIC,
  profitability_profile TEXT CHECK (profitability_profile IN ('profitable', 'mixed', 'unprofitable')),
  leverage_profile TEXT CHECK (leverage_profile IN ('low', 'moderate', 'high', 'very_high')),
  macro_sensitivity TEXT CHECK (macro_sensitivity IN ('low', 'moderate', 'high', 'very_high')),
  structural_fragility NUMERIC,
  liquidity_risk NUMERIC,
  updated_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Create asset_safety_profiles table (daily structural safety snapshot)
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
  UNIQUE(ticker, as_of_date)
);

-- 4. Create macro_regime_snapshots table
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

-- 5. Create portfolio_risk_snapshots table
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
  UNIQUE(user_id, as_of_date)
);

-- Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_ticker_metadata_ticker ON public.ticker_metadata(ticker);
CREATE INDEX IF NOT EXISTS idx_asset_safety_profiles_ticker ON public.asset_safety_profiles(ticker);
CREATE INDEX IF NOT EXISTS idx_asset_safety_profiles_date ON public.asset_safety_profiles(as_of_date DESC);
CREATE INDEX IF NOT EXISTS idx_macro_regime_snapshots_date ON public.macro_regime_snapshots(as_of_date DESC);
CREATE INDEX IF NOT EXISTS idx_portfolio_risk_snapshots_user_date ON public.portfolio_risk_snapshots(user_id, as_of_date DESC);

-- RLS policies for new tables
ALTER TABLE public.ticker_metadata ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_ticker_metadata" ON public.ticker_metadata FOR SELECT USING (true);

ALTER TABLE public.asset_safety_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_asset_safety_profiles" ON public.asset_safety_profiles FOR ALL USING (
  EXISTS (SELECT 1 FROM public.positions WHERE positions.ticker = asset_safety_profiles.ticker AND positions.user_id = auth.uid())
);

ALTER TABLE public.macro_regime_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_macro_regime_snapshots" ON public.macro_regime_snapshots FOR SELECT USING (true);

ALTER TABLE public.portfolio_risk_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_portfolio_risk_snapshots" ON public.portfolio_risk_snapshots FOR ALL USING (auth.uid() = user_id);