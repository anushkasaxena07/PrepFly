-- ==============================================================================
-- Migration 015 Rollback: Super Admin Metrics Support & Audit Logging
-- ==============================================================================
-- Idempotent rollback script reverting Migration 015.
-- ==============================================================================

-- Drop added aggregation indices
DROP INDEX IF EXISTS idx_code_submissions_created;
DROP INDEX IF EXISTS idx_interview_sessions_status_created;
DROP INDEX IF EXISTS idx_subscriptions_status_expires;
DROP INDEX IF EXISTS idx_users_org_id;
DROP INDEX IF EXISTS idx_users_role_created;
DROP INDEX IF EXISTS idx_payment_status_created;
DROP INDEX IF EXISTS idx_audit_logs_target;
DROP INDEX IF EXISTS idx_audit_logs_actor;
DROP INDEX IF EXISTS idx_audit_logs_created_at;

-- Drop audit_logs table
DROP TABLE IF EXISTS audit_logs;

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

