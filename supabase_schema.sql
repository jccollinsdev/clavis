-- Clavis Database Schema
-- Apply via Supabase Dashboard > SQL Editor or via Supabase MCP

-- User preferences
CREATE TABLE IF NOT EXISTS public.user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL UNIQUE,
  digest_time TIME DEFAULT '07:00',
  notifications_enabled BOOLEAN DEFAULT true,
  apns_token TEXT,
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
  overall_portfolio_grade TEXT,
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
  grade TEXT CHECK (grade IN ('A','B','C','D','F')),
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
  overall_grade TEXT,
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
  previous_grade TEXT,
  new_grade TEXT,
  event_hash TEXT,
  analysis_run_id UUID REFERENCES public.analysis_runs,
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
CREATE POLICY "users_own_prices" ON public.prices FOR ALL USING (true);
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
