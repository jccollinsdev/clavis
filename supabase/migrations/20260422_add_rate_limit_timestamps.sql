ALTER TABLE public.user_preferences
  ADD COLUMN IF NOT EXISTS last_manual_refresh_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_analysis_request_at TIMESTAMPTZ;
