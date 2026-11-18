-- ============================================================================
-- PREPFLY: COMPREHENSIVE ROW LEVEL SECURITY (RLS) LOCKDOWN MIGRATION
-- Migration: 20261118161500_enable_rls_lockdown.sql
-- Description: Enables RLS across all public tables, revokes all privileges
--              from anon and authenticated roles, and locks default privileges
--              to resolve Supabase Security Advisor lints 0013 and 0023.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. EXPLICITLY ENABLE RLS ON ALL KNOWN PUBLIC SCHEMA TABLES
-- ----------------------------------------------------------------------------
ALTER TABLE IF EXISTS public.pending_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.otps ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.otp_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.auth_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.coding_problems ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.parsed_resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.coding_rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.question_sheets ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.webrtc_rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.resume_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.subscription ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.platform_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.admin ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.organization ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.question_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.admin_interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.admin_coding ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.super_admin ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.ai_configuration ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.support_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.support_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.platform_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.candidate_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.skill_prerequisites ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.role_skill_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.assessment_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.assessment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.roadmap_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.roadmap_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.skill_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.candidate_skill_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.activity_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.revision_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.preparation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.job_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.interviewer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.candidate_resume_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.job_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.job_tailored_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.achievement_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.performance_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.coding_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.speech_analyses ENABLE ROW LEVEL SECURITY;

-- Additional application tables
ALTER TABLE IF EXISTS public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.interview_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.interview_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.org_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.org_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_api_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_api_spending_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.career_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.mentor_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.mentor_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.study_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.jobs ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 2. DYNAMICALLY ENABLE RLS ON ANY EXISTING OR FUTURE TABLES IN SCHEMA public
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    ) LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', r.tablename);
    END LOOP;
END $$;

-- ----------------------------------------------------------------------------
-- 3. REVOKE ALL PRIVILEGES FROM anon AND authenticated ROLES
-- ----------------------------------------------------------------------------
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- 4. LOCK DEFAULT PRIVILEGES FOR FUTURE OBJECTS IN SCHEMA public
-- ----------------------------------------------------------------------------
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON ROUTINES FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- 5. REMOVE ANY LEGACY PERMISSIVE POLICIES FOR anon OR public
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN (
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public'
          AND ('anon' = ANY(roles) OR roles = '{public}')
    ) LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I;', pol.policyname, pol.schemaname, pol.tablename);
    END LOOP;
END $$;
