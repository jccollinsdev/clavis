ALTER TABLE public.position_analyses
  ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ready',
  ADD COLUMN IF NOT EXISTS progress_message TEXT,
  ADD COLUMN IF NOT EXISTS source_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE public.news_items
  ADD COLUMN IF NOT EXISTS analysis_run_id UUID REFERENCES public.analysis_runs;

UPDATE public.position_analyses
SET
  status = COALESCE(status, 'ready'),
  source_count = COALESCE(source_count, 0),
  updated_at = COALESCE(updated_at, created_at, now());

CREATE TABLE IF NOT EXISTS public.analysis_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind TEXT NOT NULL,
  cache_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.analysis_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_analysis_cache" ON public.analysis_cache;
CREATE POLICY "service_role_analysis_cache" ON public.analysis_cache
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_cache_kind_key
  ON public.analysis_cache(kind, cache_key);

CREATE INDEX IF NOT EXISTS idx_position_analyses_updated_at
  ON public.position_analyses(updated_at DESC);
