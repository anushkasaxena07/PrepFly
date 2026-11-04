-- ===========================================================================
-- PrepFly Intelligence Database Migration (001_prepfly_intelligence_schema.sql)
-- Production-Grade Personalized Preparation, Adaptive Roadmaps & Skill Profiling
-- ===========================================================================

-- 1. Candidate Preparation Profiles
CREATE TABLE IF NOT EXISTS candidate_profiles (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    target_company TEXT,
    target_role TEXT NOT NULL,
    experience_level TEXT NOT NULL,
    target_interview_date TEXT,
    preparation_duration_days INTEGER DEFAULT 30,
    daily_study_hours DOUBLE PRECISION DEFAULT 2.0,
    preferred_study_days TEXT,
    current_skills TEXT,
    preferred_language TEXT DEFAULT 'python',
    preparation_goals TEXT,
    strengths TEXT,
    growth_areas TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Master Skill Taxonomy
CREATE TABLE IF NOT EXISTS skills (
    skill_id VARCHAR(255) PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    parent_skill_id TEXT,
    difficulty TEXT NOT NULL,
    description TEXT,
    learning_objectives TEXT,
    assessment_criteria TEXT,
    created_at TEXT NOT NULL
);

-- 3. Normalized Skill Prerequisites DAG
CREATE TABLE IF NOT EXISTS skill_prerequisites (
    id BIGSERIAL PRIMARY KEY,
    skill_id VARCHAR(255) NOT NULL,
    prerequisite_skill_id VARCHAR(255) NOT NULL,
    is_mandatory INTEGER DEFAULT 1,
    UNIQUE(skill_id, prerequisite_skill_id)
);

-- 4. Role Skill Requirement Weights
CREATE TABLE IF NOT EXISTS role_skill_requirements (
    id BIGSERIAL PRIMARY KEY,
    role_id VARCHAR(255) NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    importance_weight DOUBLE PRECISION DEFAULT 1.0,
    minimum_proficiency DOUBLE PRECISION DEFAULT 60.0,
    UNIQUE(role_id, skill_id)
);

-- 5. Candidate Evidence-Based Skill Profiles
CREATE TABLE IF NOT EXISTS candidate_skill_profiles (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    proficiency DOUBLE PRECISION DEFAULT 0.0,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    evidence_count INTEGER DEFAULT 0,
    last_assessed TEXT,
    historical_proficiency TEXT,
    learning_trend TEXT DEFAULT 'stable',
    strong_concepts TEXT,
    growth_concepts TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, skill_id)
);

-- 6. Individual Skill Evidence Rows
CREATE TABLE IF NOT EXISTS skill_evidence (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT,
    score DOUBLE PRECISION NOT NULL,
    weight DOUBLE PRECISION DEFAULT 1.0,
    demonstrated_concepts TEXT,
    missed_concepts TEXT,
    misconceptions TEXT,
    evidence_notes TEXT,
    rubric_version TEXT DEFAULT 'v1',
    created_at TEXT NOT NULL
);

-- 7. Diagnostic & Checkpoint Assessments
CREATE TABLE IF NOT EXISTS assessments (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    assessment_type TEXT NOT NULL,
    target_role TEXT,
    status TEXT DEFAULT 'pending',
    score DOUBLE PRECISION,
    total_questions INTEGER DEFAULT 0,
    completed_questions INTEGER DEFAULT 0,
    summary TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

-- 8. Assessment Questions
CREATE TABLE IF NOT EXISTS assessment_questions (
    id VARCHAR(255) PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    options TEXT,
    correct_answer TEXT,
    expected_concepts TEXT,
    rubric TEXT,
    order_index INTEGER DEFAULT 0
);

-- 9. Assessment Question Attempts & Evaluations
CREATE TABLE IF NOT EXISTS assessment_attempts (
    id VARCHAR(255) PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    candidate_answer TEXT,
    is_correct INTEGER,
    score DOUBLE PRECISION,
    evaluation_result TEXT,
    identified_concepts TEXT,
    missing_concepts TEXT,
    misconceptions TEXT,
    feedback TEXT,
    evaluated_at TEXT NOT NULL
);

-- 10. Personalized Roadmaps
CREATE TABLE IF NOT EXISTS roadmaps (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    target_role TEXT NOT NULL,
    target_company TEXT,
    current_version INTEGER DEFAULT 1,
    total_days INTEGER DEFAULT 30,
    total_activities INTEGER DEFAULT 0,
    completed_activities INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 11. Roadmap Version History & Change Rationale
CREATE TABLE IF NOT EXISTS roadmap_versions (
    id VARCHAR(255) PRIMARY KEY,
    roadmap_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    change_reason TEXT NOT NULL,
    trigger_event TEXT,
    activities_snapshot TEXT,
    created_at TEXT NOT NULL
);

-- 12. Roadmap Scheduled Activities
CREATE TABLE IF NOT EXISTS roadmap_activities (
    id VARCHAR(255) PRIMARY KEY,
    roadmap_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    day_number INTEGER NOT NULL,
    order_in_day INTEGER DEFAULT 1,
    title TEXT NOT NULL,
    description TEXT,
    activity_type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    estimated_minutes INTEGER DEFAULT 30,
    learning_objective TEXT,
    completion_criteria TEXT,
    priority DOUBLE PRECISION DEFAULT 1.0,
    due_date TEXT,
    status TEXT DEFAULT 'pending',
    is_pinned INTEGER DEFAULT 0,
    recommendation_reason TEXT,
    resource_payload TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 13. Activity Execution Attempts
CREATE TABLE IF NOT EXISTS activity_attempts (
    id VARCHAR(255) PRIMARY KEY,
    activity_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    time_spent_minutes INTEGER DEFAULT 0,
    performance_score DOUBLE PRECISION,
    notes TEXT,
    created_at TEXT NOT NULL
);

-- 14. Spaced Revision Schedules
CREATE TABLE IF NOT EXISTS revision_schedules (
    id VARCHAR(255) PRIMARY KEY,
    user_id TEXT NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    interval_stage INTEGER DEFAULT 1,
    next_revision_date TEXT NOT NULL,
    last_reviewed_at TEXT,
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- ===========================================================================
-- Performance Indexes
-- ===========================================================================
CREATE INDEX IF NOT EXISTS idx_candidate_profiles_user ON candidate_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_profiles_user ON candidate_skill_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_profiles_skill ON candidate_skill_profiles(skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_evidence_user_skill ON skill_evidence(user_id, skill_id);
CREATE INDEX IF NOT EXISTS idx_assessments_user ON assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_assessment_questions_assessment ON assessment_questions(assessment_id);
CREATE INDEX IF NOT EXISTS idx_assessment_attempts_user_assessment ON assessment_attempts(user_id, assessment_id);
CREATE INDEX IF NOT EXISTS idx_roadmaps_user ON roadmaps(user_id);
CREATE INDEX IF NOT EXISTS idx_roadmap_activities_user_day ON roadmap_activities(user_id, day_number);
CREATE INDEX IF NOT EXISTS idx_roadmap_activities_status ON roadmap_activities(user_id, status);
CREATE INDEX IF NOT EXISTS idx_roadmap_versions_roadmap ON roadmap_versions(roadmap_id);
CREATE INDEX IF NOT EXISTS idx_revision_schedules_user_date ON revision_schedules(user_id, next_revision_date);

-- ===========================================================================
-- Supabase Row Level Security (RLS) Policies
-- ===========================================================================
ALTER TABLE candidate_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_skill_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE revision_schedules ENABLE ROW LEVEL SECURITY;

-- Read-only global catalog tables
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_prerequisites ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_skill_requirements ENABLE ROW LEVEL SECURITY;

