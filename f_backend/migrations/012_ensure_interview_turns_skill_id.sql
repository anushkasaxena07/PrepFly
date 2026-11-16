-- ============================================================================
-- Migration 012: Ensure interview_turns.skill_id and reload PostgREST schema cache
-- Fixes PGRST204: Could not find the 'skill_id' column of 'interview_turns'
-- Safe, non-destructive, and idempotent.
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_turns') THEN
        -- Add skill_id and all Phase 1/2 turn ledger columns if not present
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS skill_id TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS turn_index INTEGER;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS turn_number INTEGER;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS speaker TEXT DEFAULT 'candidate';
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS question_id TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS question_text TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS question_type TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS stage TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS text TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS candidate_response TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS intent TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS decision TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS score REAL;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS accuracy_score INTEGER;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS evaluation_json TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS input_mode TEXT DEFAULT 'typed';
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS stt_engine TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS stt_confidence REAL;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS audio_ref TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS audio_duration_s REAL;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS word_count INTEGER DEFAULT 0;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS turn_status TEXT DEFAULT 'answered';
    END IF;
END $$;

-- Indexes for turn lookups by session and index
CREATE INDEX IF NOT EXISTS idx_interview_turns_session_idx ON public.interview_turns(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_interview_turns_skill_id ON public.interview_turns(skill_id) WHERE skill_id IS NOT NULL;

-- Enable Row Level Security (RLS) safely
ALTER TABLE public.interview_turns ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "service_role_all_interview_turns" ON public.interview_turns;
    CREATE POLICY "service_role_all_interview_turns" ON public.interview_turns
        FOR ALL TO service_role USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "authenticated_read_interview_turns" ON public.interview_turns;
    CREATE POLICY "authenticated_read_interview_turns" ON public.interview_turns
        FOR SELECT TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM public.sessions s
                WHERE s.session_id = interview_turns.session_id
                  AND (s.user_id = auth.uid()::text OR s.user_id IS NULL)
            )
        );
END $$;

-- Reload PostgREST schema cache immediately
NOTIFY pgrst, 'reload schema';
