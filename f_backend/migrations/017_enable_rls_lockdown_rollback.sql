-- ============================================================================
-- PREPFLY: RLS LOCKDOWN ROLLBACK MIGRATION
-- Migration: 017_enable_rls_lockdown_rollback.sql (and 20261118161500_rollback)
-- Description: Reverts RLS lockdown by restoring default schema grants.
-- ============================================================================

-- Grant standard usage back to authenticated and anon if rollback is needed
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON ROUTINES TO anon, authenticated;
