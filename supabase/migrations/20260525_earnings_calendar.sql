CREATE TABLE IF NOT EXISTS public.earnings_calendar (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker TEXT NOT NULL,
  report_date DATE NOT NULL,
  est_eps NUMERIC,
  est_revenue NUMERIC,
  time_of_day TEXT,
  fiscal_period TEXT,
  source TEXT NOT NULL DEFAULT 'finnhub',
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (ticker, report_date)
);

CREATE INDEX IF NOT EXISTS idx_earnings_calendar_report_date
  ON public.earnings_calendar(report_date);

CREATE INDEX IF NOT EXISTS idx_earnings_calendar_ticker_report_date
  ON public.earnings_calendar(ticker, report_date);

ALTER TABLE public.earnings_calendar ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "authenticated_read_earnings_calendar" ON public.earnings_calendar;
CREATE POLICY "authenticated_read_earnings_calendar"
  ON public.earnings_calendar FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_role_manage_earnings_calendar" ON public.earnings_calendar;
CREATE POLICY "service_role_manage_earnings_calendar"
  ON public.earnings_calendar FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
