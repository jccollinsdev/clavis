-- ============================================================================
-- Phase 1 / Migration 008 — Enforce summary_length constraint
-- Purpose: Normalize existing rows and add CHECK constraint so only
--          'brief', 'standard', and 'verbose' are allowed per
--          CLAVIX_TRUTH §9 (brief/standard/verbose).
-- Safety:  Normalizes the 1 legacy 'full' row to 'standard' before
--          adding the constraint. Uses NOT VALID as safety.
-- Rollback: ALTER TABLE DROP CONSTRAINT, revert normalization manually.
-- ============================================================================

UPDATE public.user_preferences
SET summary_length = 'standard'
WHERE summary_length IS NOT NULL
  AND summary_length NOT IN ('brief', 'standard', 'verbose');

ALTER TABLE public.user_preferences
    ADD CONSTRAINT user_preferences_summary_length_check
    CHECK (summary_length IS NULL OR summary_length IN ('brief', 'standard', 'verbose'))
    NOT VALID;
