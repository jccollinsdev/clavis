CREATE TABLE IF NOT EXISTS public.analysis_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  status TEXT NOT NULL,
  triggered_by TEXT,
  error_message TEXT,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  overall_portfolio_grade TEXT,
  positions_processed INTEGER DEFAULT 0,
  events_processed INTEGER DEFAULT 0
);

ALTER TABLE public.analysis_runs
  ADD COLUMN IF NOT EXISTS error_message TEXT;

ALTER TABLE public.risk_scores
  ADD COLUMN IF NOT EXISTS analysis_run_id UUID REFERENCES public.analysis_runs,
  ADD COLUMN IF NOT EXISTS grade_reason TEXT,
  ADD COLUMN IF NOT EXISTS evidence_summary TEXT,
  ADD COLUMN IF NOT EXISTS dimension_rationale JSONB;

ALTER TABLE public.news_items
  ADD COLUMN IF NOT EXISTS event_hash TEXT,
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS body TEXT,
  ADD COLUMN IF NOT EXISTS affected_tickers JSONB,
  ADD COLUMN IF NOT EXISTS relevance JSONB;

ALTER TABLE public.digests
  ADD COLUMN IF NOT EXISTS analysis_run_id UUID REFERENCES public.analysis_runs,
  ADD COLUMN IF NOT EXISTS overall_grade TEXT,
  ADD COLUMN IF NOT EXISTS overall_score NUMERIC,
  ADD COLUMN IF NOT EXISTS structured_sections JSONB,
  ADD COLUMN IF NOT EXISTS summary TEXT;

ALTER TABLE public.alerts
  DROP CONSTRAINT IF EXISTS alerts_type_check;

ALTER TABLE public.alerts
  ADD COLUMN IF NOT EXISTS event_hash TEXT,
  ADD COLUMN IF NOT EXISTS analysis_run_id UUID REFERENCES public.analysis_runs;

ALTER TABLE public.alerts
  ADD CONSTRAINT alerts_type_check
  CHECK (type IN ('grade_change','major_event','portfolio_grade_change','digest_ready'));

CREATE TABLE IF NOT EXISTS public.position_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_run_id UUID REFERENCES public.analysis_runs NOT NULL,
  position_id UUID REFERENCES public.positions NOT NULL,
  ticker TEXT NOT NULL,
  inferred_labels JSONB,
  summary TEXT,
  long_report TEXT,
  methodology TEXT,
  top_risks JSONB,
  watch_items JSONB,
  top_news JSONB,
  major_event_count INTEGER DEFAULT 0,
  minor_event_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.event_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_run_id UUID REFERENCES public.analysis_runs NOT NULL,
  position_id UUID REFERENCES public.positions NOT NULL,
  event_hash TEXT NOT NULL,
  external_event_id TEXT,
  title TEXT NOT NULL,
  summary TEXT,
  source TEXT,
  source_url TEXT,
  published_at TIMESTAMPTZ,
  event_type TEXT,
  significance TEXT CHECK (significance IN ('major','minor')),
  classification JSONB,
  classification_evidence JSONB,
  analysis_source TEXT,
  long_analysis TEXT,
  confidence NUMERIC,
  impact_horizon TEXT,
  risk_direction TEXT,
  scenario_summary TEXT,
  key_implications JSONB,
  recommended_followups JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.position_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_analysis_runs" ON public.analysis_runs FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "users_own_position_analyses" ON public.position_analyses FOR ALL USING (EXISTS (SELECT 1 FROM public.positions WHERE positions.id = position_analyses.position_id AND positions.user_id = auth.uid()));
CREATE POLICY "users_own_event_analyses" ON public.event_analyses FOR ALL USING (EXISTS (SELECT 1 FROM public.positions WHERE positions.id = event_analyses.position_id AND positions.user_id = auth.uid()));

CREATE INDEX IF NOT EXISTS idx_analysis_runs_user_id ON public.analysis_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_started_at ON public.analysis_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_position_analyses_run_id ON public.position_analyses(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_position_analyses_position_id ON public.position_analyses(position_id);
CREATE INDEX IF NOT EXISTS idx_event_analyses_run_id ON public.event_analyses(analysis_run_id);
CREATE INDEX IF NOT EXISTS idx_event_analyses_position_id ON public.event_analyses(position_id);
CREATE INDEX IF NOT EXISTS idx_event_analyses_event_hash ON public.event_analyses(event_hash);
