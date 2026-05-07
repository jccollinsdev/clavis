-- ============================================================================
-- Phase 1 / Migration 007 — Backfill ticker_risk_snapshots from risk_scores
-- Purpose: Copy the latest score per ticker from risk_scores into
--          ticker_risk_snapshots, grouped by ticker and snapshot_date.
--          Maps old grades (A-F) to new grades where possible using the
--          score value for grade recalculation (not the legacy string).
-- Safety:  INSERT ... ON CONFLICT (ticker, snapshot_date, snapshot_type)
--          DO UPDATE only if existing safety_score is NULL. Existing
--          9,006 snapshot rows are never overwritten.
-- Rollback: DELETE FROM ticker_risk_snapshots WHERE snapshot_type = 'backfill';
-- ============================================================================

INSERT INTO public.ticker_risk_snapshots (
    ticker,
    snapshot_date,
    snapshot_type,
    grade,
    safety_score,
    source_count,
    reasoning,
    methodology_version,
    analysis_as_of,
    created_at,
    updated_at
)
SELECT
    p.ticker,
    rs.calculated_at::date,
    'backfill',
    CASE
        WHEN rs.total_score >= 90 THEN 'AAA'
        WHEN rs.total_score >= 80 THEN 'AA'
        WHEN rs.total_score >= 70 THEN 'A'
        WHEN rs.total_score >= 60 THEN 'BBB'
        WHEN rs.total_score >= 50 THEN 'BB'
        WHEN rs.total_score >= 40 THEN 'B'
        WHEN rs.total_score >= 30 THEN 'CCC'
        WHEN rs.total_score >= 20 THEN 'CC'
        WHEN rs.total_score >= 10 THEN 'C'
        ELSE 'F'
    END,
    rs.total_score,
    NULL,
    rs.reasoning,
    'v1-backfill',
    rs.calculated_at,
    rs.calculated_at,
    rs.calculated_at
FROM public.risk_scores rs
JOIN public.positions p ON p.id = rs.position_id
WHERE rs.total_score IS NOT NULL
  AND p.ticker IS NOT NULL
  AND rs.calculated_at IS NOT NULL
  AND rs.id = (
      SELECT rs2.id
      FROM public.risk_scores rs2
      JOIN public.positions p2 ON p2.id = rs2.position_id
      WHERE p2.ticker = p.ticker
        AND rs2.total_score IS NOT NULL
        AND rs2.calculated_at IS NOT NULL
      ORDER BY rs2.calculated_at DESC
      LIMIT 1
  )
ON CONFLICT (ticker, snapshot_date, snapshot_type) DO NOTHING;
