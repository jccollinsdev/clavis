-- ============================================================================
-- Phase 5B SQL Backfill Package
-- Purpose: Correct ticker_risk_snapshots grades that don't match
--          the canonical score_to_grade() bands.
--
-- CRITICAL: Do NOT run the UPDATE statements on production until reviewed.
--           Run dry-run queries first and share the counts/samples.
-- ============================================================================

-- ── Grade band mapping (mirrors analysis_utils.score_to_grade) ──────────────
-- A >= 80, B >= 65, C >= 50, D >= 35, F < 35


-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. DRY-RUN: Count mismatched rows
-- ============================================================================

SELECT COUNT(*) AS total_mismatches
FROM ticker_risk_snapshots
WHERE grade IS DISTINCT FROM (
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. DRY-RUN: Breakdown by grade mismatch type
-- ============================================================================

SELECT
    grade AS stored_grade,
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END AS expected_grade,
    COUNT(*) AS row_count,
    ROUND(MIN(safety_score), 1) AS min_score,
    ROUND(MAX(safety_score), 1) AS max_score
FROM ticker_risk_snapshots
WHERE grade IS DISTINCT FROM (
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END
)
GROUP BY stored_grade,
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END
ORDER BY row_count DESC;


-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. DRY-RUN: Sample mismatched rows (first 20) for review
-- ============================================================================

SELECT
    ticker,
    snapshot_date,
    snapshot_type,
    grade AS stored_grade,
    ROUND(safety_score, 1) AS safety_score,
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END AS expected_grade,
    methodology_version
FROM ticker_risk_snapshots
WHERE grade IS DISTINCT FROM (
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END
)
ORDER BY snapshot_date DESC, ticker
LIMIT 20;


-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. TOTAL affected row count
-- ============================================================================

SELECT COUNT(*) AS affected_row_count
FROM ticker_risk_snapshots
WHERE grade IS DISTINCT FROM (
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- 5. AFFECTED TABLES
-- ============================================================================
-- Only ticker_risk_snapshots is touched.
-- No other tables are modified by this backfill.


-- ═══════════════════════════════════════════════════════════════════════════════
-- 6. APPLY QUERY — DO NOT RUN YET — approve with user first
-- ============================================================================
/*
UPDATE ticker_risk_snapshots
SET grade = CASE
    WHEN safety_score >= 80 THEN 'A'
    WHEN safety_score >= 65 THEN 'B'
    WHEN safety_score >= 50 THEN 'C'
    WHEN safety_score >= 35 THEN 'D'
    ELSE 'F'
END
WHERE grade IS DISTINCT FROM (
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END
);
*/


-- ═══════════════════════════════════════════════════════════════════════════════
-- 7. VERIFICATION QUERY (run after apply)
-- ============================================================================
-- Should return 0 after apply.
/*
SELECT COUNT(*) AS remaining_mismatches
FROM ticker_risk_snapshots
WHERE grade IS DISTINCT FROM (
    CASE
        WHEN safety_score >= 80 THEN 'A'
        WHEN safety_score >= 65 THEN 'B'
        WHEN safety_score >= 50 THEN 'C'
        WHEN safety_score >= 35 THEN 'D'
        ELSE 'F'
    END
);
*/


-- ═══════════════════════════════════════════════════════════════════════════════
-- 8. ROLLBACK PLAN
-- ============================================================================
-- This is a straightforward UPDATE with no schema changes.
-- Rollback via Supabase Point-in-Time Recovery (PITR) if needed.
-- No DDL, no column drops, no table drops.
-- If PITR is unavailable, restore from a pre-backfill database snapshot.
