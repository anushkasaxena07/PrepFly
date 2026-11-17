-- ==============================================================================
-- Migration 016 Rollback: Strict Tenant Isolation & College ↔ Student Linking Model
-- ==============================================================================
-- Idempotent rollback script reverting Migration 016.
-- ==============================================================================

-- Drop indices
DROP INDEX IF EXISTS idx_coding_submissions_org;
DROP INDEX IF EXISTS idx_organization_join_code;
DROP INDEX IF EXISTS idx_org_invites_org_email;
DROP INDEX IF EXISTS idx_org_invites_token;
DROP INDEX IF EXISTS idx_org_memberships_org_status;
DROP INDEX IF EXISTS idx_org_memberships_user_status;
DROP INDEX IF EXISTS idx_org_memberships_org_user;

-- Drop tables
DROP TABLE IF EXISTS org_invites;
DROP TABLE IF EXISTS org_memberships;

-- Remove added columns from organization (PostgreSQL supports DROP COLUMN IF EXISTS)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'organization' AND column_name = 'join_code'
    ) THEN
        ALTER TABLE organization DROP COLUMN join_code;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'organization' AND column_name = 'max_seats'
    ) THEN
        ALTER TABLE organization DROP COLUMN max_seats;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'coding_submissions' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE coding_submissions DROP COLUMN organization_id;
    END IF;
END $$;

-- Reload schema notification for PostgREST
NOTIFY pgrst, 'reload schema';
