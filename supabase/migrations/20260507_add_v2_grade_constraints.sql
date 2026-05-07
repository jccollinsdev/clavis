-- ============================================================================
-- Phase 1 / Migration 002 — V2 Grade Constraint Migration
-- Purpose: Replace A/B/C/D/F grade checks with the bond-rating scale
--          AAA, AA, A, BBB, BB, B, CCC, CC, C, F per CLAVIX_TRUTH §7.
-- Safety:  risk_scores uses NOT VALID so existing rows with old grades
--          are not rejected. All other tables currently have no grade
--          CHECK at all, so the new constraint has zero existing-violation
--          risk.
-- Rollback: ALTER TABLE ... DROP CONSTRAINT for each new constraint,
--           plus restore the old risk_scores constraint if needed.
-- ============================================================================

-- 1. risk_scores — currently has CHECK (grade IN ('A','B','C','D','F'))
-- Drop old constraint, add v2 constraint NOT VALID to avoid rejecting
-- existing rows that still carry old legacy grades.
ALTER TABLE public.risk_scores
    DROP CONSTRAINT IF EXISTS risk_scores_grade_check;

ALTER TABLE public.risk_scores
    ADD CONSTRAINT risk_scores_grade_check
    CHECK (grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F'))
    NOT VALID;

-- 2. ticker_risk_snapshots — currently has NO grade check constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.ticker_risk_snapshots'::regclass
          AND conname = 'ticker_risk_snapshots_grade_check'
    ) THEN
        ALTER TABLE public.ticker_risk_snapshots
            ADD CONSTRAINT ticker_risk_snapshots_grade_check
            CHECK (grade IS NULL OR grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F'))
            NOT VALID;
    END IF;
END $$;

-- 3. alerts.previous_grade and alerts.new_grade — currently no check
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.alerts'::regclass
          AND conname = 'alerts_previous_grade_check'
    ) THEN
        ALTER TABLE public.alerts
            ADD CONSTRAINT alerts_previous_grade_check
            CHECK (previous_grade IS NULL OR previous_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.alerts'::regclass
          AND conname = 'alerts_new_grade_check'
    ) THEN
        ALTER TABLE public.alerts
            ADD CONSTRAINT alerts_new_grade_check
            CHECK (new_grade IS NULL OR new_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F'));
    END IF;
END $$;

-- 4. analysis_runs.overall_portfolio_grade — currently no check
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.analysis_runs'::regclass
          AND conname = 'analysis_runs_overall_portfolio_grade_check'
    ) THEN
        ALTER TABLE public.analysis_runs
            ADD CONSTRAINT analysis_runs_overall_portfolio_grade_check
            CHECK (overall_portfolio_grade IS NULL OR overall_portfolio_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F'));
    END IF;
END $$;

-- 5. digests.overall_grade — currently no check
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.digests'::regclass
          AND conname = 'digests_overall_grade_check'
    ) THEN
        ALTER TABLE public.digests
            ADD CONSTRAINT digests_overall_grade_check
            CHECK (overall_grade IS NULL OR overall_grade IN ('AAA','AA','A','BBB','BB','B','CCC','CC','C','F'));
    END IF;
END $$;
