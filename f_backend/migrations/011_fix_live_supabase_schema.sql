-- ============================================================================
-- Migration 011: Live Supabase Production Schema Sync
-- Fixes schema drift observed in live Render logs:
--   - users.id default UUID for direct inserts without client UUID
--   - organization.updated_at & organization.status
--   - activity_logs.actor_type & activity_logs.actor_id
--   - public.notifications table creation
-- Safe & idempotent: run once in Supabase SQL Editor alongside 010.
-- ============================================================================

-- 1. Ensure users.id generates a UUID automatically if omitted
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users') THEN
        ALTER TABLE users ALTER COLUMN id SET DEFAULT gen_random_uuid()::text;
    END IF;
END $$;

-- 2. Ensure organization has updated_at, status, and subscription columns
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organization') THEN
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'TRIAL';
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS trial_start TEXT;
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS trial_end TEXT;
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS subscription_start TEXT;
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS subscription_expiry TEXT;
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS current_plan TEXT DEFAULT 'Trial';
    END IF;
END $$;

-- 3. Ensure activity_logs has actor_id and actor_type
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'activity_logs') THEN
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS actor_id TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS actor_type TEXT;
    END IF;
END $$;

-- 4. Create public.notifications table if missing
CREATE TABLE IF NOT EXISTS public.notifications (
    id VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id TEXT,
    sender_type TEXT,
    sender_name TEXT,
    title TEXT,
    message TEXT,
    read INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reload PostgREST schema cache immediately
NOTIFY pgrst, 'reload schema';
