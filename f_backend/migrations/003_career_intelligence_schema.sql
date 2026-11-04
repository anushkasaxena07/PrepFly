-- ===========================================================================
-- PrepFly Career Intelligence Database Migration (003_career_intelligence_schema.sql)
-- Improvement Tracking, Personalized Roadmaps, Job Preparation & Achievements
-- ===========================================================================

-- 1. Preparation Event Stream (Idempotent Event Ledger)
CREATE TABLE IF NOT EXISTS preparation_events (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_module TEXT NOT NULL,
    source_record_id TEXT,
    payload_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Ingested Job Target Profiles
CREATE TABLE IF NOT EXISTS job_profiles (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_title TEXT NOT NULL,
    company TEXT,
    raw_text TEXT NOT NULL,
    role_tier TEXT DEFAULT 'mid',
    target_date TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Structured Job Requirements
CREATE TABLE IF NOT EXISTS job_requirements (
    id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    normalized_skill_id VARCHAR(255) NOT NULL,
    requirement_type TEXT NOT NULL,
    is_required INTEGER DEFAULT 1,
    importance_weight DOUBLE PRECISION DEFAULT 3.0,
    evidence_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Job Tailored Questions with Automated Quality Metrics
CREATE TABLE IF NOT EXISTS job_tailored_questions (
    id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    requirement_id VARCHAR(255),
    question_text TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    quality_score DOUBLE PRECISION DEFAULT 8.0,
    evaluation_metrics TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Configurable Milestone and Achievement Definitions
CREATE TABLE IF NOT EXISTS achievement_definitions (
    id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    trigger_event TEXT NOT NULL,
    condition_type TEXT NOT NULL,
    threshold_value DOUBLE PRECISION NOT NULL,
    badge_icon TEXT NOT NULL,
    reward_points INTEGER DEFAULT 50,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Server-Validated Unlocked User Achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    achievement_id VARCHAR(255) NOT NULL,
    triggering_event_id TEXT,
    unlocked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reward_claimed INTEGER DEFAULT 0,
    metadata_json TEXT,
    UNIQUE(user_id, achievement_id)
);

-- 7. Comparable Performance Snapshots
CREATE TABLE IF NOT EXISTS performance_snapshots (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    overall_readiness DOUBLE PRECISION NOT NULL,
    category_scores_json TEXT NOT NULL,
    sample_counts_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for Fast Query Performance
CREATE INDEX IF NOT EXISTS idx_prep_events_user ON preparation_events(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_job_profiles_user ON job_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_job_reqs_job ON job_requirements(job_id);
CREATE INDEX IF NOT EXISTS idx_job_questions_job ON job_tailored_questions(job_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_perf_snapshots_user ON performance_snapshots(user_id, created_at);

