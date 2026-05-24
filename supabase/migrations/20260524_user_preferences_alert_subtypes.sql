-- User preferences: add alert subtype toggles and trial dates per CLAVIX_TRUTH §15/§16.
--
-- Status: DRAFTED 2026-05-24 during the live S&P 500 refresh run.
--         DO NOT apply until parent analysis_run ddb9b4ed-3eb7-4c6e-b97a-34577aa2c62d
--         completes. user_preferences is not written by the scoring pipeline so the
--         contention risk is low, but defer to the same window for consistency.
--
-- Existing columns (verified live): alerts_major_events, alerts_portfolio_risk,
-- alerts_grade_changes, quiet_hours_enabled, digest_time, summary_length,
-- subscription_tier.

BEGIN;

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS alerts_watchlist          boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS alerts_macro_shock        boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS alerts_digest_ready       boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS alert_severity_threshold  text    NOT NULL DEFAULT 'all',
    ADD COLUMN IF NOT EXISTS trial_started_at          timestamptz,
    ADD COLUMN IF NOT EXISTS trial_ends_at             timestamptz,
    ADD COLUMN IF NOT EXISTS timezone                  text;

ALTER TABLE user_preferences
    ADD CONSTRAINT user_preferences_alert_severity_threshold_check
        CHECK (alert_severity_threshold IN ('all', 'medium', 'high'));

COMMIT;
