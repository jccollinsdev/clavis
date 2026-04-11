ALTER TABLE public.analysis_runs
  ADD COLUMN IF NOT EXISTS target_position_id UUID REFERENCES public.positions,
  ADD COLUMN IF NOT EXISTS target_ticker TEXT;

CREATE INDEX IF NOT EXISTS idx_analysis_runs_target_position_id
  ON public.analysis_runs(target_position_id);
