-- ============================================================================
-- Migration 013: PrepFly Master Specification Schema Alignment (Section 10)
-- Idempotent creation of target_profiles, availability, blackout_dates,
-- pillars, skills, subskills, questions, assessment_sessions, answers,
-- evidence, skill_snapshots, readiness_snapshots, plans, plan_days,
-- plan_blocks, study_logs, chat_messages, and timezone column on users.
-- ============================================================================

-- 1. Ensure timezone column on users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'Asia/Kolkata';

-- 2. Target Profiles
CREATE TABLE IF NOT EXISTS target_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('JUNIOR', 'MID', 'SENIOR', 'STAFF')),
    years_total NUMERIC DEFAULT 0,
    years_domain NUMERIC DEFAULT 0,
    jd_text TEXT,
    user_rules_text TEXT,
    interview_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_target_profiles_user ON target_profiles(user_id);

-- 3. Availability and Blackout Dates
CREATE TABLE IF NOT EXISTS availability (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weekday TEXT NOT NULL CHECK (weekday IN ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')),
    minutes INTEGER NOT NULL DEFAULT 90,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_availability_user_weekday ON availability(user_id, weekday);

CREATE TABLE IF NOT EXISTS blackout_dates (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_blackout_user_date ON blackout_dates(user_id, date);

-- 4. Pillars, Skills & Subskills Taxonomy
CREATE TABLE IF NOT EXISTS pillars (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pillars_profile ON pillars(profile_id);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,
    pillar_id TEXT NOT NULL REFERENCES pillars(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('MANDATORY', 'PREFERRED', 'SUPPORTING')),
    importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
    source TEXT NOT NULL CHECK (source IN ('USER_PROVIDED', 'WEB_SOURCED', 'MODEL_INFERRED')),
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skills_profile ON skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_skills_pillar ON skills(pillar_id);

CREATE TABLE IF NOT EXISTS subskills (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    rubric_json JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subskills_skill ON subskills(skill_id);

-- 5. Questions Bank
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    subskill_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('MCQ', 'SHORT_ANSWER', 'CODE', 'SCENARIO')),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    prompt TEXT NOT NULL,
    rubric_json JSONB NOT NULL DEFAULT '[]',
    model_answer TEXT,
    options_json JSONB,
    tests_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_skill_diff ON questions(skill_id, difficulty);

-- 6. Assessment Sessions and Answers
CREATE TABLE IF NOT EXISTS assessment_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('DIAGNOSTIC', 'ASSIGNMENT', 'MOCK', 'EOD_CHECK')),
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_assessment_sessions_user ON assessment_sessions(user_id);

CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    answer_text TEXT,
    attempted BOOLEAN NOT NULL DEFAULT TRUE,
    time_spent_sec INTEGER DEFAULT 0,
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id);

-- 7. Evidence Engine (The Single Source of Truth for Proficiency)
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id TEXT NOT NULL,
    subskill_id TEXT,
    answer_id TEXT REFERENCES answers(id) ON DELETE SET NULL,
    score NUMERIC NOT NULL CHECK (score BETWEEN 0 AND 100),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    type TEXT NOT NULL CHECK (type IN ('MCQ', 'SHORT_ANSWER', 'SCENARIO', 'CODE', 'MOCK_INTERVIEW', 'PRACTICE_ASSIGNMENT')),
    rubric_results_json JSONB NOT NULL DEFAULT '[]',
    grader_runs_json JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_user_skill ON evidence(user_id, skill_id, created_at DESC);

-- 8. Skill & Readiness Snapshots (Deterministic Historical Audit)
CREATE TABLE IF NOT EXISTS skill_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES assessment_sessions(id) ON DELETE SET NULL,
    skill_id TEXT NOT NULL,
    proficiency NUMERIC,
    confidence NUMERIC NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('NOT_ASSESSED', 'LOW_EVIDENCE', 'VERIFIED_GAP', 'DEVELOPING', 'VERIFIED_STRONG')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_snapshots_user ON skill_snapshots(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS readiness_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES assessment_sessions(id) ON DELETE SET NULL,
    verified_score NUMERIC,
    projected_readiness NUMERIC,
    weighted_coverage NUMERIC NOT NULL,
    mandatory_coverage NUMERIC NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_readiness_snapshots_user ON readiness_snapshots(user_id, created_at DESC);

-- 9. Preparation Plans, Days & Blocks
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    trigger TEXT NOT NULL CHECK (trigger IN ('INITIAL', 'DAILY_MINUTES_CHANGED', 'MISSED_DAY', 'DEADLINE_CHANGED', 'ASSESSMENT_COMPLETED', 'MANUAL_REBALANCE', 'SKILL_PROFILE_EDITED')),
    diff_json JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plans_user_active ON plans(user_id, is_active);

CREATE TABLE IF NOT EXISTS plan_days (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    day_number INTEGER NOT NULL,
    phase TEXT NOT NULL,
    theme TEXT NOT NULL,
    daily_goal TEXT NOT NULL,
    budget_min INTEGER NOT NULL,
    total_min INTEGER NOT NULL,
    notes_json JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plan_days_plan_date ON plan_days(plan_id, date);

CREATE TABLE IF NOT EXISTS plan_blocks (
    id TEXT PRIMARY KEY,
    plan_day_id TEXT NOT NULL REFERENCES plan_days(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('DIAGNOSTIC_CHECK', 'LEARN', 'PRACTICE', 'ASSIGNMENT', 'MOCK_INTERVIEW', 'REVISION', 'REFLECTION')),
    skill_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    content_json JSONB NOT NULL DEFAULT '{}',
    why_here TEXT NOT NULL,
    evidence_id TEXT REFERENCES evidence(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'DONE', 'DEFERRED', 'DROPPED')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plan_blocks_day ON plan_blocks(plan_day_id);

-- 10. Study Logs (The Only Source for Completed Study Minutes)
CREATE TABLE IF NOT EXISTS study_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    block_id TEXT REFERENCES plan_blocks(id) ON DELETE SET NULL,
    minutes INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_study_logs_user ON study_logs(user_id, started_at);

-- 11. Chat Messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    intent TEXT,
    tool_calls_json JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, created_at ASC);

-- 12. Schema cache reload for PostgREST
NOTIFY pgrst, 'reload schema';
