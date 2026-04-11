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

CREATE OR REPLACE FUNCTION public.touch_scheduler_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

DROP TRIGGER IF EXISTS scheduler_jobs_updated_at ON public.scheduler_jobs;
CREATE TRIGGER scheduler_jobs_updated_at
BEFORE UPDATE ON public.scheduler_jobs
FOR EACH ROW
EXECUTE FUNCTION public.touch_scheduler_jobs_updated_at();

ALTER TABLE public.scheduler_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_own_scheduler_jobs" ON public.scheduler_jobs;
CREATE POLICY "users_own_scheduler_jobs"
ON public.scheduler_jobs
FOR ALL
USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_user_id ON public.scheduler_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_active ON public.scheduler_jobs(active);
