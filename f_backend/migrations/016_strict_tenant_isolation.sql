-- ==============================================================================
-- Migration 016: Strict Tenant Isolation & College ↔ Student Linking Model
-- ==============================================================================
-- Purpose:
--   1. Unify student identity via explicit `org_memberships` (links users to colleges).
--   2. Introduce `org_invites` for verifiable CSV invite and join code onboarding.
--   3. Add `join_code` and `max_seats` to `organization` for institutional access control.
--   4. Add `organization_id` to `coding_submissions` to guarantee code test scoping.
--   5. Backfill existing linked users safely without data loss.
-- ==============================================================================

-- 1. Table: org_memberships
CREATE TABLE IF NOT EXISTS org_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'student',
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- 'active', 'pending', 'revoked', 'archived'
    roll_number VARCHAR(64),
    department VARCHAR(128),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_user UNIQUE (organization_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_memberships_org_user 
    ON org_memberships (organization_id, user_id);

CREATE INDEX IF NOT EXISTS idx_org_memberships_user_status 
    ON org_memberships (user_id, status);

CREATE INDEX IF NOT EXISTS idx_org_memberships_org_status 
    ON org_memberships (organization_id, status);

-- 2. Table: org_invites
CREATE TABLE IF NOT EXISTS org_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'student',
    token VARCHAR(128) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- 'pending', 'accepted', 'expired', 'revoked'
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_email_pending UNIQUE (organization_id, email, status)
);

CREATE INDEX IF NOT EXISTS idx_org_invites_token 
    ON org_invites (token);

CREATE INDEX IF NOT EXISTS idx_org_invites_org_email 
    ON org_invites (organization_id, email);

-- 3. Alter Table: organization (Add join_code and max_seats)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'organization' AND column_name = 'join_code'
    ) THEN
        ALTER TABLE organization ADD COLUMN join_code VARCHAR(16) UNIQUE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'organization' AND column_name = 'max_seats'
    ) THEN
        ALTER TABLE organization ADD COLUMN max_seats INTEGER NOT NULL DEFAULT 100;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_organization_join_code 
    ON organization (join_code);

-- 4. Alter Table: coding_submissions (Add organization_id)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'coding_submissions' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE coding_submissions ADD COLUMN organization_id TEXT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_coding_submissions_org 
    ON coding_submissions (organization_id);

-- 5. Backfill Existing Linked Users to org_memberships
INSERT INTO org_memberships (organization_id, user_id, role, status, joined_at, updated_at)
SELECT 
    u.organization_id,
    u.id AS user_id,
    CASE 
        WHEN LOWER(COALESCE(u.role, '')) = 'admin' THEN 'admin'
        ELSE 'student'
    END AS role,
    'active' AS status,
    NOW(),
    NOW()
FROM users u
WHERE u.organization_id IS NOT NULL 
  AND TRIM(u.organization_id) != ''
ON CONFLICT (organization_id, user_id) DO NOTHING;

-- 6. Seed Default Join Codes for Known Organizations
UPDATE organization 
SET join_code = UPPER(SUBSTRING(MD5(id::text || name::text) FROM 1 FOR 6))
WHERE join_code IS NULL;

-- 7. Row Level Security Policies
ALTER TABLE org_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_invites ENABLE ROW LEVEL SECURITY;

-- Reload schema notification for PostgREST
NOTIFY pgrst, 'reload schema';
