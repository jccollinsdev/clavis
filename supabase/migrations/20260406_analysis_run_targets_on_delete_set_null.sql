ALTER TABLE public.analysis_runs
  DROP CONSTRAINT IF EXISTS analysis_runs_target_position_id_fkey;

ALTER TABLE public.analysis_runs
  ADD CONSTRAINT analysis_runs_target_position_id_fkey
  FOREIGN KEY (target_position_id)
  REFERENCES public.positions(id)
  ON DELETE SET NULL;
