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

-- 3. Ensure activity_logs has actor_id, actor_type, user_id, and entity columns
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'activity_logs') THEN
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS actor_id TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS user_id TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS actor_type TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS entity_type TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS entity_id TEXT;
    END IF;
END $$;

-- 4. Create public.notifications table if missing and ensure all columns/indexes/RLS exist
CREATE TABLE IF NOT EXISTS public.notifications (
    id VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    organization_id TEXT,
    user_id TEXT,
    sender_type TEXT,
    sender_name TEXT,
    target_group TEXT DEFAULT 'All',
    title TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    target_dept TEXT DEFAULT 'All',
    target_sem TEXT DEFAULT 'All',
    read INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'notifications') THEN
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS organization_id TEXT;
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS user_id TEXT;
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS sender_type TEXT;
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS sender_name TEXT;
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS target_group TEXT DEFAULT 'All';
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS title TEXT DEFAULT '';
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS message TEXT DEFAULT '';
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS target_dept TEXT DEFAULT 'All';
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS target_sem TEXT DEFAULT 'All';
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS read INTEGER DEFAULT 0;
        ALTER TABLE public.notifications ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_notifications_read') THEN
        ALTER TABLE public.notifications ADD CONSTRAINT chk_notifications_read CHECK (read IN (0, 1));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_notifications_org_id ON public.notifications(organization_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_sender_type ON public.notifications(sender_type);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON public.notifications(created_at DESC);

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "service_role_all_notifications" ON public.notifications;
    CREATE POLICY "service_role_all_notifications" ON public.notifications
        FOR ALL TO service_role USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "authenticated_read_scoped_notifications" ON public.notifications;
    CREATE POLICY "authenticated_read_scoped_notifications" ON public.notifications
        FOR SELECT TO authenticated
        USING (
            (user_id IS NOT NULL AND user_id = auth.uid()::text)
            OR (
                user_id IS NULL AND (
                    sender_type = 'SUPER_ADMIN'
                    OR organization_id IS NULL
                    OR organization_id = 'All'
                    OR EXISTS (
                        SELECT 1 FROM public.users u
                        WHERE u.id = auth.uid()::text
                          AND u.organization_id = notifications.organization_id
                    )
                )
            )
        );
END $$;

REVOKE INSERT, UPDATE, DELETE ON public.notifications FROM anon, authenticated;

-- 5. Enforce RLS on payment/invoice tables if present
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'payment') THEN
        ALTER TABLE public.payment ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "service_role_all_payment" ON public.payment;
        CREATE POLICY "service_role_all_payment" ON public.payment
            FOR ALL TO service_role USING (true) WITH CHECK (true);
        REVOKE ALL ON public.payment FROM anon;
        REVOKE INSERT, UPDATE, DELETE ON public.payment FROM authenticated;
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'invoice') THEN
        ALTER TABLE public.invoice ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "service_role_all_invoice" ON public.invoice;
        CREATE POLICY "service_role_all_invoice" ON public.invoice
            FOR ALL TO service_role USING (true) WITH CHECK (true);
        REVOKE ALL ON public.invoice FROM anon;
        REVOKE INSERT, UPDATE, DELETE ON public.invoice FROM authenticated;
    END IF;
END $$;

-- 6. Ensure all Phase 1 / Migration 010 tables have complete idempotent columns
--    in case partial tables pre-existed before CREATE TABLE IF NOT EXISTS ran.
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sessions') THEN
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS hiring_recommendation TEXT;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS report_status TEXT;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS final_score REAL;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS final_score_100 REAL;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS final_grade TEXT;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS final_report TEXT;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS report_json TEXT;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS display_name TEXT;
        ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS display_name_source TEXT;
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_turns') THEN
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS turn_number INTEGER;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS turn_index INTEGER;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS speaker TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS question_id TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS question_text TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS question_type TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS skill_id TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS stage TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS text TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS candidate_response TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS intent TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS decision TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS score REAL;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS accuracy_score INTEGER;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS evaluation_json TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS input_mode TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS stt_engine TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS stt_confidence REAL;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS audio_ref TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS audio_duration_s REAL;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS word_count INTEGER;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS turn_status TEXT DEFAULT 'answered';
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_speech_metrics') THEN
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS wpm REAL;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS filler_count INTEGER;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS filler_map_json JSONB DEFAULT '{}'::jsonb;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS pause_count INTEGER;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS longest_pause_s REAL;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS avg_pause_s REAL;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS speaking_time_s REAL;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS silence_ratio REAL;
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS computed_by TEXT DEFAULT 'deterministic_python';
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS formula_version TEXT DEFAULT 'v1';
        ALTER TABLE public.interview_speech_metrics ADD COLUMN IF NOT EXISTS missing_reason TEXT;
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_evaluations') THEN
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS turn_id VARCHAR(255);
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS skill_id TEXT;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS rubric_scores_json JSONB;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS raw_score REAL;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS normalized_score REAL;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS quoted_evidence_json JSONB;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS missing_concepts_json JSONB;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS technical_mistakes_json JSONB;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS improved_answer TEXT;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS misconception_tags TEXT[] DEFAULT ARRAY[]::TEXT[];
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS evaluator_type TEXT DEFAULT 'gemini_rubric';
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS prompt_id TEXT;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS prompt_version TEXT;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS model_used TEXT;
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ok';
        ALTER TABLE public.interview_evaluations ADD COLUMN IF NOT EXISTS error_code TEXT;
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_reports') THEN
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS candidate_id TEXT;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS report_status TEXT DEFAULT 'pending';
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS overall_score REAL;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS grade TEXT;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS recommendation TEXT;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS dimension_scores_json JSONB;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS strengths_json JSONB;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS weaknesses_json JSONB;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS coverage_json JSONB;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS data_sufficiency_json JSONB;
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS formula_version TEXT DEFAULT 'v1';
        ALTER TABLE public.interview_reports ADD COLUMN IF NOT EXISTS generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_question_rubrics') THEN
        ALTER TABLE public.interview_question_rubrics ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);
        ALTER TABLE public.interview_question_rubrics ADD COLUMN IF NOT EXISTS question_id TEXT;
        ALTER TABLE public.interview_question_rubrics ADD COLUMN IF NOT EXISTS skill_id TEXT;
        ALTER TABLE public.interview_question_rubrics ADD COLUMN IF NOT EXISTS rubric_json JSONB;
        ALTER TABLE public.interview_question_rubrics ADD COLUMN IF NOT EXISTS reference_answer TEXT;
        ALTER TABLE public.interview_question_rubrics ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

-- Reload PostgREST schema cache immediately
NOTIFY pgrst, 'reload schema';
