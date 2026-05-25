CREATE TABLE IF NOT EXISTS public.etf_holdings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  etf_ticker TEXT NOT NULL,
  holding_ticker TEXT NOT NULL,
  weight_pct NUMERIC,
  rank INTEGER,
  source TEXT NOT NULL DEFAULT 'static_seed',
  as_of DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (etf_ticker, holding_ticker, as_of)
);

CREATE INDEX IF NOT EXISTS idx_etf_holdings_etf_rank
  ON public.etf_holdings(etf_ticker, rank);

ALTER TABLE public.etf_holdings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "authenticated_read_etf_holdings" ON public.etf_holdings;
CREATE POLICY "authenticated_read_etf_holdings"
  ON public.etf_holdings FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_etf_holdings" ON public.etf_holdings;
CREATE POLICY "service_role_manage_etf_holdings"
  ON public.etf_holdings FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
