ALTER TABLE public.analysis_runs
  ADD COLUMN IF NOT EXISTS target_tickers JSONB;
