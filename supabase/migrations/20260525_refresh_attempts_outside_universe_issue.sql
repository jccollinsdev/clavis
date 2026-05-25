CREATE TABLE IF NOT EXISTS public.refresh_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  result TEXT NOT NULL DEFAULT 'attempted',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_refresh_attempts_user_attempted_at
  ON public.refresh_attempts(user_id, attempted_at DESC);

ALTER TABLE public.refresh_attempts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_read_own_refresh_attempts" ON public.refresh_attempts;
CREATE POLICY "users_read_own_refresh_attempts"
  ON public.refresh_attempts FOR SELECT
  USING (auth.uid() = user_id OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_refresh_attempts" ON public.refresh_attempts;
CREATE POLICY "service_role_manage_refresh_attempts"
  ON public.refresh_attempts FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.positions
  ADD COLUMN IF NOT EXISTS outside_universe BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.digests
  ADD COLUMN IF NOT EXISTS issue_number INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS idx_digests_user_issue_number
  ON public.digests(user_id, issue_number)
  WHERE issue_number IS NOT NULL;
