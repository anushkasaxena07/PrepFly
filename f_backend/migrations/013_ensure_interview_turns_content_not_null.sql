-- ============================================================================
-- Migration 013: Ensure interview_turns.content and synchronization columns
-- Prevents Postgres 23502 (null value in column "content" violates not-null constraint)
-- Safe, non-destructive, and idempotent.
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_turns') THEN
        -- Add content, transcript, and role columns if not already present
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS content TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS transcript TEXT;
        ALTER TABLE public.interview_turns ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'candidate';

        -- Backfill historical rows to guarantee content is never null
        UPDATE public.interview_turns
        SET content = COALESCE(NULLIF(text, ''), NULLIF(candidate_response, ''), NULLIF(question_text, ''), '[Recorded turn]')
        WHERE content IS NULL;

        UPDATE public.interview_turns
        SET transcript = COALESCE(NULLIF(text, ''), NULLIF(candidate_response, ''), NULLIF(question_text, ''), '')
        WHERE transcript IS NULL;

        UPDATE public.interview_turns
        SET role = COALESCE(NULLIF(speaker, ''), 'candidate')
        WHERE role IS NULL;
    END IF;
END $$;

-- Reload PostgREST schema cache immediately
NOTIFY pgrst, 'reload schema';

