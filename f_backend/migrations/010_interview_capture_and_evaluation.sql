-- ============================================================================
-- Migration 010: Interview Capture, Evidence-Based Evaluation & Report Schema
-- Fixes schema drift identified in AUDIT_INTERVIEW.md Phase 0:
--   - sessions.resume_text (and report/lifecycle/identity columns)
--   - parsed_resumes.created_at
--   - activity_logs.actor_id
--   - organization.status
-- Creates/extends normalized interview entities with FKs, constraints, & RLS:
--   - interview_sessions (mapped to extended `sessions` table)
--   - interview_turns
--   - interview_speech_metrics
--   - interview_evaluations
--   - interview_reports
--   - interview_question_rubrics (service-role-only rubric/reference store)
-- ============================================================================

-- 1. FIX SCHEMA DRIFT ON EXISTING TABLES

-- 1a. sessions (mapped entity: interview_sessions)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sessions') THEN
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS resume_text TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS report_json JSONB;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS consent_given INTEGER DEFAULT 1;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS privacy_policy_version TEXT DEFAULT 'DPDP-2023-v1.0';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS knowledge_map TEXT DEFAULT '{}';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS turn_count INTEGER DEFAULT 0;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS interview_state TEXT DEFAULT 'INITIALIZING';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS personality TEXT DEFAULT 'professional';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS organization_id TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cached_hints TEXT DEFAULT '{}';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS job_description TEXT;

        -- Logical interview_sessions columns required by Prompt 2 Phase 1
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS job_target_id TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS level TEXT DEFAULT 'Mid';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'resume';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'created';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS resume_snapshot_json JSONB;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS display_name TEXT DEFAULT 'Candidate';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS display_name_source TEXT DEFAULT 'fallback';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS blueprint_json JSONB;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS adaptive_state_json JSONB;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS report_status TEXT DEFAULT 'pending';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS model_used TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS prompt_versions_json JSONB;
    END IF;
END $$;

-- Check constraints for sessions enums (idempotent via pg_constraint check)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_sessions_status') THEN
        ALTER TABLE sessions ADD CONSTRAINT chk_sessions_status
            CHECK (status IS NULL OR status IN ('created', 'in_progress', 'completed', 'abandoned'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_sessions_display_name_source') THEN
        ALTER TABLE sessions ADD CONSTRAINT chk_sessions_display_name_source
            CHECK (display_name_source IS NULL OR display_name_source IN ('profile', 'google', 'resume', 'fallback'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_sessions_report_status') THEN
        ALTER TABLE sessions ADD CONSTRAINT chk_sessions_report_status
            CHECK (report_status IS NULL OR report_status IN ('pending', 'EVALUATED', 'PARTIAL', 'INCOMPLETE_INSUFFICIENT_DATA', 'EVALUATION_FAILED'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_idempotency_key ON sessions(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- 1b. parsed_resumes
CREATE TABLE IF NOT EXISTS parsed_resumes (
    id VARCHAR(255) PRIMARY KEY,
    hash VARCHAR(255) UNIQUE,
    raw_text TEXT,
    structured_data TEXT,
    ats_score REAL DEFAULT 70.0,
    missing_info TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'parsed_resumes') THEN
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS hash VARCHAR(255);
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS raw_text TEXT;
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS structured_data TEXT;
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS ats_score REAL DEFAULT 70.0;
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS missing_info TEXT;
    END IF;
END $$;

-- 1c. activity_logs
CREATE TABLE IF NOT EXISTS activity_logs (
    id VARCHAR(255) PRIMARY KEY,
    actor_id TEXT,
    actor_type TEXT,
    action TEXT,
    ip_address TEXT,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'activity_logs') THEN
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS actor_id TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS actor_type TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS action TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS ip_address TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS details TEXT;
        ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

-- 1d. organization (and organizations if aliased)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organization') THEN
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organizations') THEN
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
    END IF;
END $$;

-- ============================================================================
-- 2. INTERVIEW TURNS (EXTEND FROM 002 FOR NORMALIZED SPEAKER-LEVEL CAPTURE)
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_turns (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER,
    turn_index INTEGER,
    speaker TEXT CHECK (speaker IN ('interviewer', 'candidate')),
    question_id TEXT,
    skill_id TEXT,
    question_text TEXT,
    text TEXT,
    question_type TEXT,
    stage TEXT,
    candidate_response TEXT,
    input_mode TEXT CHECK (input_mode IS NULL OR input_mode IN ('typed', 'speech')),
    stt_engine TEXT,
    stt_confidence REAL,
    audio_ref TEXT,
    audio_duration_s REAL,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    word_count INTEGER,
    turn_status TEXT DEFAULT 'answered',
    intent TEXT DEFAULT 'ANSWER',
    decision TEXT DEFAULT 'NEXT_QUESTION',
    score REAL,
    accuracy_score INTEGER,
    evaluation_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'interview_turns') THEN
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS turn_index INTEGER;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS speaker TEXT;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS question_id TEXT;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS skill_id TEXT;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS text TEXT;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS input_mode TEXT;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS stt_engine TEXT;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS stt_confidence REAL;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS audio_ref TEXT;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS audio_duration_s REAL;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS word_count INTEGER;
        ALTER TABLE interview_turns ADD COLUMN IF NOT EXISTS turn_status TEXT DEFAULT 'answered';
    END IF;
    -- Allow question_text to be nullable for candidate speaker turns
    ALTER TABLE interview_turns ALTER COLUMN question_text DROP NOT NULL;
    ALTER TABLE interview_turns ALTER COLUMN turn_number DROP NOT NULL;
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_interview_turns_speaker') THEN
        ALTER TABLE interview_turns ADD CONSTRAINT chk_interview_turns_speaker
            CHECK (speaker IS NULL OR speaker IN ('interviewer', 'candidate'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_interview_turns_input_mode') THEN
        ALTER TABLE interview_turns ADD CONSTRAINT chk_interview_turns_input_mode
            CHECK (input_mode IS NULL OR input_mode IN ('typed', 'speech'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_interview_turns_session_idx ON interview_turns(session_id, turn_index);
CREATE UNIQUE INDEX IF NOT EXISTS uq_interview_turns_session_idx_speaker
    ON interview_turns(session_id, turn_index, speaker)
    WHERE turn_index IS NOT NULL AND speaker IS NOT NULL;

-- ============================================================================
-- 3. INTERVIEW SPEECH METRICS
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_speech_metrics (
    turn_id VARCHAR(255) PRIMARY KEY REFERENCES interview_turns(id) ON DELETE CASCADE,
    session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
    wpm REAL,
    filler_count INTEGER,
    filler_map_json JSONB DEFAULT '{}'::jsonb,
    pause_count INTEGER,
    longest_pause_s REAL,
    avg_pause_s REAL,
    speaking_time_s REAL,
    silence_ratio REAL,
    computed_by TEXT NOT NULL DEFAULT 'deterministic_python',
    formula_version TEXT NOT NULL DEFAULT 'v1',
    missing_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_speech_metrics_session ON interview_speech_metrics(session_id);

-- ============================================================================
-- 4. INTERVIEW EVALUATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_evaluations (
    id VARCHAR(255) PRIMARY KEY,
    turn_id VARCHAR(255) NOT NULL REFERENCES interview_turns(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    skill_id TEXT,
    rubric_scores_json JSONB,
    raw_score REAL,
    normalized_score REAL CHECK (normalized_score IS NULL OR (normalized_score >= 0.0 AND normalized_score <= 1.0)),
    quoted_evidence_json JSONB,
    missing_concepts_json JSONB,
    technical_mistakes_json JSONB,
    improved_answer TEXT,
    misconception_tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    evaluator_type TEXT NOT NULL DEFAULT 'gemini_rubric',
    prompt_id TEXT,
    prompt_version TEXT,
    model_used TEXT,
    status TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'skipped')),
    error_code TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interview_evals_turn ON interview_evaluations(turn_id);
CREATE INDEX IF NOT EXISTS idx_interview_evals_session ON interview_evaluations(session_id);

-- ============================================================================
-- 5. INTERVIEW REPORTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_reports (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL,
    report_status TEXT NOT NULL CHECK (report_status IN ('pending', 'EVALUATED', 'PARTIAL', 'INCOMPLETE_INSUFFICIENT_DATA', 'EVALUATION_FAILED')),
    overall_score REAL,
    grade TEXT,
    recommendation TEXT,
    dimension_scores_json JSONB,
    strengths_json JSONB,
    weaknesses_json JSONB,
    coverage_json JSONB,
    data_sufficiency_json JSONB,
    formula_version TEXT NOT NULL DEFAULT 'v1',
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interview_reports_candidate ON interview_reports(candidate_id);

-- ============================================================================
-- 6. PRIVATE RUBRICS & REFERENCE ANSWERS (NEVER READABLE BY CLIENT ROLE)
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_question_rubrics (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    question_id TEXT,
    skill_id TEXT,
    rubric_json JSONB NOT NULL,
    reference_answer TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 7. ROW LEVEL SECURITY (RLS) & COLUMN/TABLE PRIVILEGES
-- ============================================================================

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_speech_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_question_rubrics ENABLE ROW LEVEL SECURITY;

-- Service role bypass policies (backend Flask uses service role)
DO $$
BEGIN
    DROP POLICY IF EXISTS "service_role_all_sessions" ON sessions;
    CREATE POLICY "service_role_all_sessions" ON sessions FOR ALL TO service_role USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "service_role_all_turns" ON interview_turns;
    CREATE POLICY "service_role_all_turns" ON interview_turns FOR ALL TO service_role USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "service_role_all_speech_metrics" ON interview_speech_metrics;
    CREATE POLICY "service_role_all_speech_metrics" ON interview_speech_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "service_role_all_evaluations" ON interview_evaluations;
    CREATE POLICY "service_role_all_evaluations" ON interview_evaluations FOR ALL TO service_role USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "service_role_all_reports" ON interview_reports;
    CREATE POLICY "service_role_all_reports" ON interview_reports FOR ALL TO service_role USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "service_role_all_rubrics" ON interview_question_rubrics;
    CREATE POLICY "service_role_all_rubrics" ON interview_question_rubrics FOR ALL TO service_role USING (true) WITH CHECK (true);
END $$;

-- Candidate read-only policies (authenticated user can SELECT ONLY their own rows)
DO $$
BEGIN
    DROP POLICY IF EXISTS "candidate_select_own_sessions" ON sessions;
    CREATE POLICY "candidate_select_own_sessions" ON sessions
        FOR SELECT TO authenticated
        USING (auth.uid()::text = user_id);

    DROP POLICY IF EXISTS "Allow authenticated read turns" ON interview_turns;
    DROP POLICY IF EXISTS "candidate_select_own_turns" ON interview_turns;
    CREATE POLICY "candidate_select_own_turns" ON interview_turns
        FOR SELECT TO authenticated
        USING (EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.session_id = interview_turns.session_id
              AND s.user_id = auth.uid()::text
        ));

    DROP POLICY IF EXISTS "candidate_select_own_speech_metrics" ON interview_speech_metrics;
    CREATE POLICY "candidate_select_own_speech_metrics" ON interview_speech_metrics
        FOR SELECT TO authenticated
        USING (EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.session_id = interview_speech_metrics.session_id
              AND s.user_id = auth.uid()::text
        ));

    DROP POLICY IF EXISTS "candidate_select_own_evaluations" ON interview_evaluations;
    CREATE POLICY "candidate_select_own_evaluations" ON interview_evaluations
        FOR SELECT TO authenticated
        USING (EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.session_id = interview_evaluations.session_id
              AND s.user_id = auth.uid()::text
        ));

    DROP POLICY IF EXISTS "candidate_select_own_reports" ON interview_reports;
    CREATE POLICY "candidate_select_own_reports" ON interview_reports
        FOR SELECT TO authenticated
        USING (auth.uid()::text = candidate_id);
END $$;

-- Strictly revoke write privileges from anon/authenticated on backend-owned tables
REVOKE INSERT, UPDATE, DELETE ON interview_speech_metrics FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON interview_evaluations FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON interview_reports FROM anon, authenticated;

-- Strictly revoke ALL access to private rubrics/reference answers from client roles
REVOKE ALL ON interview_question_rubrics FROM anon, authenticated;

-- Column-level restriction: client role cannot select raw rubric_scores_json directly
REVOKE SELECT ON interview_evaluations FROM anon, authenticated;
GRANT SELECT (
    id, turn_id, session_id, skill_id, raw_score, normalized_score,
    quoted_evidence_json, missing_concepts_json, technical_mistakes_json,
    improved_answer, misconception_tags, evaluator_type,
    prompt_id, prompt_version, model_used, status, error_code, created_at
) ON interview_evaluations TO authenticated;

-- Extend Prompt 1 skill_evidence with interview deduplication & versioning fields
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'skill_evidence') THEN
        ALTER TABLE skill_evidence ADD COLUMN IF NOT EXISTS difficulty TEXT DEFAULT 'Medium';
        ALTER TABLE skill_evidence ADD COLUMN IF NOT EXISTS evaluator_version TEXT DEFAULT 'v1';
        ALTER TABLE skill_evidence ADD COLUMN IF NOT EXISTS dedupe_key TEXT;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_skill_evidence_dedupe_key
            ON skill_evidence(dedupe_key) WHERE dedupe_key IS NOT NULL;
    END IF;
END $$;

-- Reload PostgREST schema cache so PGRST204 errors clear immediately
NOTIFY pgrst, 'reload schema';

