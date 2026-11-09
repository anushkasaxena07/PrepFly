-- ============================================================================
-- Migration 007: Fix Production Schema Missing Columns & Backward Compatibility
-- ============================================================================
-- Resolves reported production schema drift on Render & Supabase PostgreSQL:
-- 1. sessions.active & metadata fields
-- 2. parsed_resumes.hash & ats_score
-- 3. coding_submissions.user_id
-- 4. speech_analyses.user_id
-- 5. candidate_skill_profiles.proficiency & tracking columns
-- 6. organization(s).current_plan & subscription tracking
-- ============================================================================

-- 1. SESSIONS TABLE EXTENSIONS
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sessions') THEN
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS storage_path TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'General Technical';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS difficulty TEXT DEFAULT 'Medium';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS stage TEXT DEFAULT 'GREETING';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ats_score REAL DEFAULT 70.0;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS structured_resume TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS final_score_100 REAL;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS grade_color TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS grade_label TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS performance_level TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS hiring_recommendation TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'Software Engineer';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS interview_mode TEXT DEFAULT 'resume';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS total_questions INTEGER DEFAULT 10;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS consent_given INTEGER DEFAULT 1;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS privacy_policy_version TEXT DEFAULT 'DPDP-2023-v1.0';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS job_description TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS organization_id TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cached_hints TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS interview_state TEXT DEFAULT 'INITIALIZING';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS personality TEXT DEFAULT 'professional';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS knowledge_map TEXT DEFAULT '{}';
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS turn_count INTEGER DEFAULT 0;
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(active);

-- 2. PARSED_RESUMES TABLE
CREATE TABLE IF NOT EXISTS parsed_resumes (
    id VARCHAR(255) PRIMARY KEY,
    hash VARCHAR(255),
    raw_text TEXT,
    structured_data TEXT,
    ats_score REAL DEFAULT 70.0,
    missing_info TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'parsed_resumes') THEN
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS hash VARCHAR(255);
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS ats_score REAL DEFAULT 70.0;
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS raw_text TEXT;
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS structured_data TEXT;
        ALTER TABLE parsed_resumes ADD COLUMN IF NOT EXISTS missing_info TEXT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_parsed_resumes_hash ON parsed_resumes(hash);

-- 3. CODING_SUBMISSIONS TABLE
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'coding_submissions') THEN
        ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS user_id TEXT;
        ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS candidate_id TEXT;
        ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'PENDING';
        ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS execution_time_ms REAL;
        ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS memory_kb REAL;
    ELSE
        CREATE TABLE coding_submissions (
            id VARCHAR(255) PRIMARY KEY,
            user_id TEXT,
            challenge_id TEXT,
            language TEXT,
            code TEXT,
            status TEXT DEFAULT 'PENDING',
            score REAL DEFAULT 0.0,
            execution_time_ms REAL,
            memory_kb REAL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_coding_submissions_user_id ON coding_submissions(user_id);

-- 4. SPEECH_ANALYSES TABLE
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'speech_analyses') THEN
        ALTER TABLE speech_analyses ADD COLUMN IF NOT EXISTS user_id TEXT;
        ALTER TABLE speech_analyses ADD COLUMN IF NOT EXISTS session_id TEXT;
        ALTER TABLE speech_analyses ADD COLUMN IF NOT EXISTS pace_wpm REAL;
        ALTER TABLE speech_analyses ADD COLUMN IF NOT EXISTS clarity_score REAL;
    ELSE
        CREATE TABLE speech_analyses (
            id VARCHAR(255) PRIMARY KEY,
            user_id TEXT,
            session_id TEXT,
            pace_wpm REAL,
            clarity_score REAL,
            filler_words_count INTEGER DEFAULT 0,
            analysis_json TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_speech_analyses_user_id ON speech_analyses(user_id);

-- 5. CANDIDATE_SKILL_PROFILES TABLE
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'candidate_skill_profiles') THEN
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS proficiency REAL DEFAULT 0.0;
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS confidence REAL DEFAULT 0.0;
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS evidence_count INTEGER DEFAULT 0;
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS learning_trend TEXT DEFAULT 'STABLE';
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS last_assessed TEXT;
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS historical_proficiency TEXT;
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS strong_concepts TEXT;
        ALTER TABLE candidate_skill_profiles ADD COLUMN IF NOT EXISTS growth_concepts TEXT;
    ELSE
        CREATE TABLE candidate_skill_profiles (
            id VARCHAR(255) PRIMARY KEY,
            user_id TEXT NOT NULL,
            skill_id VARCHAR(255) NOT NULL,
            proficiency REAL DEFAULT 0.0,
            confidence REAL DEFAULT 0.0,
            evidence_count INTEGER DEFAULT 0,
            last_assessed TEXT,
            historical_proficiency TEXT,
            learning_trend TEXT DEFAULT 'STABLE',
            strong_concepts TEXT,
            growth_concepts TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, skill_id)
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_candidate_skill_profiles_user ON candidate_skill_profiles(user_id);

-- 6. ORGANIZATION / ORGANIZATIONS TABLE
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'organization') THEN
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS current_plan TEXT DEFAULT 'Trial';
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS subscription_plan TEXT;
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'TRIAL';
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS trial_start TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS trial_end TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '10 days');
        ALTER TABLE organization ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'organizations') THEN
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS current_plan TEXT DEFAULT 'Trial';
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_plan TEXT;
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'TRIAL';
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS trial_start TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS trial_end TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '10 days');
        ALTER TABLE organizations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

