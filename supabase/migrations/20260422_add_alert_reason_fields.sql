alter table public.alerts
  add column if not exists change_reason text,
  add column if not exists change_details jsonb;

comment on column public.alerts.change_reason is 'Human-readable explanation for why the alert fired.';
comment on column public.alerts.change_details is 'Structured alert metadata such as score deltas, top risks, and supporting evidence.';
