-- Security fixes — 2026-05-30
-- Closes three Supabase advisor findings:
--   1. ERROR: gnews_wrapper_resolution RLS disabled (anon-readable)
--   2. WARN: save_daily_asset_safety_profile anon EXECUTE (SECURITY DEFINER)
--   3. WARN: save_daily_macro_regime anon EXECUTE (SECURITY DEFINER)
-- Also enables leaked-password protection in Supabase Auth (must also toggle via dashboard).

-- ─── 1. Enable RLS on gnews_wrapper_resolution ──────────────────────────────
ALTER TABLE public.gnews_wrapper_resolution ENABLE ROW LEVEL SECURITY;

-- Only authenticated service-role callers (backend) should read/write this table.
-- The iOS app never reads gnews_wrapper_resolution directly.
-- No anon or authenticated user SELECT is granted — backend uses service-role key.
-- (If a select policy for authenticated users is ever needed, add it here.)

-- ─── 2. Revoke anon EXECUTE on SECURITY DEFINER RPCs ────────────────────────
-- These functions write into asset_safety_profiles and macro_regime_snapshots.
-- They are called only by the backend service-role; anon should never call them.
REVOKE EXECUTE ON FUNCTION public.save_daily_asset_safety_profile(
    TEXT, NUMERIC, NUMERIC, NUMERIC, NUMERIC, NUMERIC, JSONB, TEXT
) FROM anon;

REVOKE EXECUTE ON FUNCTION public.save_daily_macro_regime(
    TEXT, TEXT, TEXT, TEXT, TEXT, TEXT, NUMERIC, NUMERIC, TEXT
) FROM anon;

-- Add an auth check inside each function so even if EXECUTE is somehow granted
-- later, unauthenticated callers are rejected at the SQL level.
CREATE OR REPLACE FUNCTION save_daily_asset_safety_profile(
  p_ticker TEXT,
  p_structural_base_score NUMERIC,
  p_macro_adjustment NUMERIC,
  p_event_adjustment NUMERIC,
  p_safety_score NUMERIC,
  p_confidence NUMERIC,
  p_factor_breakdown JSONB,
  p_regime_state TEXT DEFAULT 'neutral'
) RETURNS void AS $$
DECLARE
  v_date DATE := CURRENT_DATE;
BEGIN
  -- Only service-role (no JWT) or authenticated users may call this function.
  IF auth.role() = 'anon' THEN
    RAISE EXCEPTION 'Unauthorized: service-role required';
  END IF;

  INSERT INTO public.asset_safety_profiles (
    ticker, as_of_date, structural_base_score, macro_adjustment,
    event_adjustment, safety_score, confidence, factor_breakdown, regime_state, updated_at
  ) VALUES (
    p_ticker, v_date, p_structural_base_score, p_macro_adjustment,
    p_event_adjustment, p_safety_score, p_confidence, p_factor_breakdown, p_regime_state, now()
  )
  ON CONFLICT (ticker, as_of_date)
  DO UPDATE SET
    structural_base_score = EXCLUDED.structural_base_score,
    macro_adjustment = EXCLUDED.macro_adjustment,
    event_adjustment = EXCLUDED.event_adjustment,
    safety_score = EXCLUDED.safety_score,
    confidence = EXCLUDED.confidence,
    factor_breakdown = EXCLUDED.factor_breakdown,
    regime_state = EXCLUDED.regime_state,
    updated_at = now();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION save_daily_macro_regime(
  p_regime_state TEXT,
  p_rates_signal TEXT DEFAULT 'stable',
  p_credit_signal TEXT DEFAULT 'stable',
  p_inflation_signal TEXT DEFAULT 'stable',
  p_growth_signal TEXT DEFAULT 'stable',
  p_risk_on_off_signal TEXT DEFAULT 'neutral',
  p_vix_level NUMERIC DEFAULT NULL,
  p_credit_spread_level NUMERIC DEFAULT NULL,
  p_notes TEXT DEFAULT NULL
) RETURNS void AS $$
BEGIN
  -- Only service-role (no JWT) or authenticated users may call this function.
  IF auth.role() = 'anon' THEN
    RAISE EXCEPTION 'Unauthorized: service-role required';
  END IF;

  INSERT INTO public.macro_regime_snapshots (
    as_of_date, regime_state, rates_signal, credit_signal,
    inflation_signal, growth_signal, risk_on_off_signal, vix_level,
    credit_spread_level, notes, created_at
  ) VALUES (
    CURRENT_DATE, p_regime_state, p_rates_signal, p_credit_signal,
    p_inflation_signal, p_growth_signal, p_risk_on_off_signal,
    p_vix_level, p_credit_spread_level, p_notes, now()
  )
  ON CONFLICT (as_of_date)
  DO UPDATE SET
    regime_state = EXCLUDED.regime_state,
    rates_signal = EXCLUDED.rates_signal,
    credit_signal = EXCLUDED.credit_signal,
    inflation_signal = EXCLUDED.inflation_signal,
    growth_signal = EXCLUDED.growth_signal,
    risk_on_off_signal = EXCLUDED.risk_on_off_signal,
    vix_level = EXCLUDED.vix_level,
    credit_spread_level = EXCLUDED.credit_spread_level,
    notes = EXCLUDED.notes;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ─── 3. Leaked-password protection ──────────────────────────────────────────
-- This must ALSO be toggled in the Supabase Dashboard:
-- Authentication → Providers → Email → "Enable leaked password protection" → ON
-- The SQL below is advisory; the actual feature is toggled in Dashboard config.
-- No SQL command is needed — it is a dashboard-level auth setting.

-- ─── Verification queries ────────────────────────────────────────────────────
-- After running this migration, verify:
--
-- SELECT relrowsecurity FROM pg_class WHERE relname = 'gnews_wrapper_resolution';
-- -- Expected: true
--
-- SELECT grantee, privilege_type FROM information_schema.role_routine_grants
-- WHERE routine_name = 'save_daily_asset_safety_profile' AND grantee = 'anon';
-- -- Expected: 0 rows
--
-- SELECT grantee, privilege_type FROM information_schema.role_routine_grants
-- WHERE routine_name = 'save_daily_macro_regime' AND grantee = 'anon';
-- -- Expected: 0 rows
