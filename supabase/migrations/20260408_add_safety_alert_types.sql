-- Add new safety-focused alert types to the alerts table

ALTER TABLE public.alerts DROP CONSTRAINT IF EXISTS alerts_type_check;

ALTER TABLE public.alerts ADD CONSTRAINT alerts_type_check 
CHECK (type IN (
  'grade_change',
  'major_event',
  'portfolio_grade_change',
  'digest_ready',
  'safety_deterioration',
  'concentration_danger',
  'cluster_risk',
  'macro_shock',
  'structural_fragility',
  'portfolio_safety_threshold_breach'
));

COMMENT ON COLUMN public.alerts.type IS 'Alert type: grade_change, major_event, portfolio_grade_change, digest_ready, safety_deterioration, concentration_danger, cluster_risk, macro_shock, structural_fragility, portfolio_safety_threshold_breach';