-- Daily structural refresh: save asset_safety_profiles and macro_regime_snapshots

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