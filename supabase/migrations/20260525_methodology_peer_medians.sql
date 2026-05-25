CREATE TABLE IF NOT EXISTS public.peer_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  peer_ticker TEXT NOT NULL,
  similarity NUMERIC NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (ticker <> peer_ticker),
  UNIQUE (ticker, peer_ticker)
);

CREATE INDEX IF NOT EXISTS idx_peer_groups_ticker_similarity
  ON public.peer_groups(ticker, similarity DESC);

ALTER TABLE public.peer_groups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "authenticated_read_peer_groups" ON public.peer_groups;
CREATE POLICY "authenticated_read_peer_groups"
  ON public.peer_groups FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_peer_groups" ON public.peer_groups;
CREATE POLICY "service_role_manage_peer_groups"
  ON public.peer_groups FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE TABLE IF NOT EXISTS public.sector_medians (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sector TEXT NOT NULL,
  metric TEXT NOT NULL,
  median NUMERIC,
  p25 NUMERIC,
  p75 NUMERIC,
  n_tickers INTEGER NOT NULL DEFAULT 0,
  as_of DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (sector, metric, as_of)
);

CREATE INDEX IF NOT EXISTS idx_sector_medians_sector_metric_as_of
  ON public.sector_medians(sector, metric, as_of DESC);

ALTER TABLE public.sector_medians ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "authenticated_read_sector_medians" ON public.sector_medians;
CREATE POLICY "authenticated_read_sector_medians"
  ON public.sector_medians FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_sector_medians" ON public.sector_medians;
CREATE POLICY "service_role_manage_sector_medians"
  ON public.sector_medians FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
