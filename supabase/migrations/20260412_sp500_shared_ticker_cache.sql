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

DROP POLICY IF EXISTS "authenticated_read_ticker_universe" ON public.ticker_universe;
CREATE POLICY "authenticated_read_ticker_universe" ON public.ticker_universe
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_ticker_universe" ON public.ticker_universe;
CREATE POLICY "service_role_manage_ticker_universe" ON public.ticker_universe
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_ticker_universe_company_name
  ON public.ticker_universe(company_name);

CREATE INDEX IF NOT EXISTS idx_ticker_universe_priority_rank
  ON public.ticker_universe(priority_rank);

ALTER TABLE public.ticker_metadata
  ADD COLUMN IF NOT EXISTS pe_ratio NUMERIC,
  ADD COLUMN IF NOT EXISTS week_52_high NUMERIC,
  ADD COLUMN IF NOT EXISTS week_52_low NUMERIC,
  ADD COLUMN IF NOT EXISTS price NUMERIC,
  ADD COLUMN IF NOT EXISTS price_as_of TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS avg_volume NUMERIC,
  ADD COLUMN IF NOT EXISTS previous_close NUMERIC,
  ADD COLUMN IF NOT EXISTS open_price NUMERIC,
  ADD COLUMN IF NOT EXISTS day_high NUMERIC,
  ADD COLUMN IF NOT EXISTS day_low NUMERIC,
  ADD COLUMN IF NOT EXISTS last_price_source TEXT,
  ADD COLUMN IF NOT EXISTS is_supported BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS public.ticker_risk_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL REFERENCES public.ticker_universe(ticker) ON DELETE CASCADE,
  snapshot_date DATE NOT NULL,
  snapshot_type TEXT NOT NULL CHECK (snapshot_type IN ('daily', 'manual_refresh', 'backfill')),
  grade TEXT,
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
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (ticker, snapshot_date, snapshot_type)
);

ALTER TABLE public.ticker_risk_snapshots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "authenticated_read_ticker_risk_snapshots" ON public.ticker_risk_snapshots;
CREATE POLICY "authenticated_read_ticker_risk_snapshots" ON public.ticker_risk_snapshots
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_ticker_risk_snapshots" ON public.ticker_risk_snapshots;
CREATE POLICY "service_role_manage_ticker_risk_snapshots" ON public.ticker_risk_snapshots
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_ticker_risk_snapshots_ticker_analysis_as_of
  ON public.ticker_risk_snapshots(ticker, analysis_as_of DESC);

CREATE INDEX IF NOT EXISTS idx_ticker_risk_snapshots_snapshot_date
  ON public.ticker_risk_snapshots(snapshot_date DESC);

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

DROP POLICY IF EXISTS "authenticated_read_ticker_news_cache" ON public.ticker_news_cache;
CREATE POLICY "authenticated_read_ticker_news_cache" ON public.ticker_news_cache
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_ticker_news_cache" ON public.ticker_news_cache;
CREATE POLICY "service_role_manage_ticker_news_cache" ON public.ticker_news_cache
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE UNIQUE INDEX IF NOT EXISTS idx_ticker_news_cache_ticker_url
  ON public.ticker_news_cache(ticker, url);

CREATE INDEX IF NOT EXISTS idx_ticker_news_cache_ticker_published_at
  ON public.ticker_news_cache(ticker, published_at DESC);

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

DROP POLICY IF EXISTS "authenticated_read_ticker_refresh_jobs" ON public.ticker_refresh_jobs;
CREATE POLICY "authenticated_read_ticker_refresh_jobs" ON public.ticker_refresh_jobs
  FOR SELECT
  USING (
    auth.role() = 'service_role'
    OR requested_by_user_id = auth.uid()
  );

DROP POLICY IF EXISTS "service_role_manage_ticker_refresh_jobs" ON public.ticker_refresh_jobs;
CREATE POLICY "service_role_manage_ticker_refresh_jobs" ON public.ticker_refresh_jobs
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_ticker_refresh_jobs_ticker_created_at
  ON public.ticker_refresh_jobs(ticker, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ticker_refresh_jobs_status_created_at
  ON public.ticker_refresh_jobs(status, created_at ASC);

CREATE TABLE IF NOT EXISTS public.watchlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  name TEXT NOT NULL DEFAULT 'Watchlist',
  is_default BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_manage_own_watchlists" ON public.watchlists;
CREATE POLICY "users_manage_own_watchlists" ON public.watchlists
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id
  ON public.watchlists(user_id);

CREATE TABLE IF NOT EXISTS public.watchlist_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  watchlist_id UUID NOT NULL REFERENCES public.watchlists(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL REFERENCES public.ticker_universe(ticker) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (watchlist_id, ticker)
);

ALTER TABLE public.watchlist_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_manage_own_watchlist_items" ON public.watchlist_items;
CREATE POLICY "users_manage_own_watchlist_items" ON public.watchlist_items
  FOR ALL
  USING (
    EXISTS (
      SELECT 1
      FROM public.watchlists w
      WHERE w.id = watchlist_items.watchlist_id
        AND w.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.watchlists w
      WHERE w.id = watchlist_items.watchlist_id
        AND w.user_id = auth.uid()
    )
  );

CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist_id
  ON public.watchlist_items(watchlist_id);

ALTER TABLE public.user_preferences
  ADD COLUMN IF NOT EXISTS subscription_tier TEXT DEFAULT 'free';
