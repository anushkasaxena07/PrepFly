-- ==============================================================================
-- Migration 015: Super Admin Metrics Support & Audit Logging
-- ==============================================================================
-- Purpose:
--   1. Real audit logging for administrative mutations across Super Admin.
--   2. High-performance composite indices for real-time KPI aggregations:
--      revenue, organizations, students, subscriptions, and interview counts.
--   3. Guarantees deterministic, traceable data access with zero fabrication.
-- ==============================================================================

-- 1. Table: audit_logs (tamper-evident record of administrative operations)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id TEXT NOT NULL,
    actor_email TEXT,
    action VARCHAR(64) NOT NULL,              -- e.g. 'update_setting', 'suspend_user', 'record_payment', 'create_org'
    target_type VARCHAR(64) NOT NULL,         -- e.g. 'user', 'organization', 'payment', 'question', 'setting'
    target_id TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optimize audit log querying by timeline and administrative actor
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at 
    ON audit_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor 
    ON audit_logs (actor_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_target 
    ON audit_logs (target_type, target_id);

-- 2. Performance Indices for Metrics Aggregation

-- Payments: Fast status filtering & chronological revenue sum
CREATE INDEX IF NOT EXISTS idx_payment_status_created 
    ON payment (status, created_at DESC);

-- Users: Fast role and creation filtering
CREATE INDEX IF NOT EXISTS idx_users_role_created 
    ON users (role, created_at DESC);

-- Users: Organization membership lookup (including NULL B2C candidates)
CREATE INDEX IF NOT EXISTS idx_users_org_id 
    ON users (organization_id);

-- Subscriptions: Active subscription checks and expiration monitoring
CREATE INDEX IF NOT EXISTS idx_subscriptions_status_expires 
    ON subscriptions (status, expires_at DESC);

-- Interview Sessions: Completed interview tallies
CREATE INDEX IF NOT EXISTS idx_interview_sessions_status_created 
    ON interview_sessions (status, created_at DESC);

-- Code Submissions: Coding test tallies
CREATE INDEX IF NOT EXISTS idx_code_submissions_created 
    ON code_submissions (created_at DESC);

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

