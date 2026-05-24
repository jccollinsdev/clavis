-- Alerts v2: read/unread tracking, severity, destination metadata.
-- Applied 2026-05-24 post sp500 backfill run.

BEGIN;

ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS read_at         timestamptz,
    ADD COLUMN IF NOT EXISTS delivered_at    timestamptz,
    ADD COLUMN IF NOT EXISTS severity        text,
    ADD COLUMN IF NOT EXISTS destination_type text,
    ADD COLUMN IF NOT EXISTS destination_id   text;

-- Backfill severity from existing alert type.
-- Live values: cluster_risk, concentration_danger, digest_ready, grade_change,
-- major_event, portfolio_grade_change. Map to CLAVIX_TRUTH §15 severities.
UPDATE alerts
SET severity = CASE
    WHEN type IN ('grade_change', 'portfolio_grade_change')           THEN 'high'
    WHEN type IN ('major_event', 'cluster_risk', 'concentration_danger') THEN 'high'
    WHEN type = 'digest_ready'                                        THEN 'low'
    ELSE 'medium'
END
WHERE severity IS NULL;

ALTER TABLE alerts
    ALTER COLUMN severity SET DEFAULT 'medium';

-- Add severity check constraint (only if not present).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'alerts_severity_check'
    ) THEN
        ALTER TABLE alerts
            ADD CONSTRAINT alerts_severity_check
            CHECK (severity IS NULL OR severity IN ('low', 'medium', 'high'));
    END IF;
END $$;

-- destination_type / destination_id derived from existing columns.
-- position_ticker is the only ticker-identifying column on alerts today.
UPDATE alerts
SET
    destination_type = CASE
        WHEN type IN ('grade_change', 'major_event', 'cluster_risk', 'concentration_danger')
            THEN 'ticker_detail'
        WHEN type = 'portfolio_grade_change' THEN 'today'
        WHEN type = 'digest_ready'            THEN 'today'
        ELSE 'alert_detail'
    END,
    destination_id = COALESCE(destination_id, position_ticker)
WHERE destination_type IS NULL;

-- Indexes to make unread counts cheap.
CREATE INDEX IF NOT EXISTS alerts_user_read_idx
    ON alerts (user_id, read_at);

CREATE INDEX IF NOT EXISTS alerts_user_created_idx
    ON alerts (user_id, created_at DESC);

COMMIT;
