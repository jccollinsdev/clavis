ALTER TABLE public.analysis_runs
  ADD COLUMN IF NOT EXISTS current_stage TEXT,
  ADD COLUMN IF NOT EXISTS current_stage_message TEXT;
