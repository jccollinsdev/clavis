-- ============================================================================
-- Phase 1 / Migration 009 — Drop Legacy Backup Tables
-- Purpose: Remove the two April 2026 backup tables that have no primary
--          key, no RLS policies, and no production use. Verified with
--          codebase grep: zero backend code reads from either table.
--          Row counts at drop time: event_analyses_backup=10,363,
--          position_analyses_backup=11,312.
-- Rollback: Not applicable (data already migrated and tables were
--           snapshots, not live stores). Restore from earlier dump if
--           needed.
-- ============================================================================

DROP TABLE IF EXISTS public.event_analyses_backup_20260504;
DROP TABLE IF EXISTS public.position_analyses_backup_20260504;
