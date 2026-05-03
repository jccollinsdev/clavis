ALTER TABLE public.event_analyses
  ADD COLUMN IF NOT EXISTS what_happened TEXT,
  ADD COLUMN IF NOT EXISTS tldr TEXT,
  ADD COLUMN IF NOT EXISTS what_it_means TEXT;
