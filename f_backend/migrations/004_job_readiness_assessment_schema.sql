-- =============================================================================
-- Migration 004: PrepFly Job-Specific Readiness Assessment and Gap Engine
-- =============================================================================

CREATE TABLE IF NOT EXISTS job_assessment_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    job_id VARCHAR(255),
    company VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    experience_level VARCHAR(100) DEFAULT 'Fresher',
    target_date VARCHAR(50),
    raw_jd_text TEXT,
    status VARCHAR(50) DEFAULT 'IN_PROGRESS',
    overall_readiness DOUBLE PRECISION,
    assessment_coverage DOUBLE PRECISION DEFAULT 0.0,
    evidence_confidence DOUBLE PRECISION DEFAULT 0.0,
    readiness_status VARCHAR(100) DEFAULT 'READINESS NOT YET ESTABLISHED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_requirement_snapshots (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES job_assessment_sessions(id) ON DELETE CASCADE,
    job_id VARCHAR(255),
    canonical_skill_id VARCHAR(100) NOT NULL,
    original_source_text TEXT,
    normalized_description TEXT NOT NULL,
    requirement_type VARCHAR(100) NOT NULL,
    importance DOUBLE PRECISION DEFAULT 3.0,
    role_relevance DOUBLE PRECISION DEFAULT 1.0,
    evidence_source VARCHAR(100) DEFAULT 'job_description',
    extraction_confidence DOUBLE PRECISION DEFAULT 0.9,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment_blueprints (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES job_assessment_sessions(id) ON DELETE CASCADE,
    role VARCHAR(255) NOT NULL,
    role_tier VARCHAR(50) DEFAULT 'mid',
    planned_components_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_skills_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    weights_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment_attempts (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES job_assessment_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    component_type VARCHAR(100) NOT NULL,
    question_id VARCHAR(255) NOT NULL,
    canonical_skill_id VARCHAR(100) NOT NULL,
    candidate_response TEXT,
    code_submission TEXT,
    time_taken_seconds INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'COMPLETED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assessment_evaluations (
    id VARCHAR(255) PRIMARY KEY,
    attempt_id VARCHAR(255) NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL REFERENCES job_assessment_sessions(id) ON DELETE CASCADE,
    canonical_skill_id VARCHAR(100) NOT NULL,
    correctness_score DOUBLE PRECISION NOT NULL,
    depth_score DOUBLE PRECISION NOT NULL,
    communication_score DOUBLE PRECISION NOT NULL,
    overall_score DOUBLE PRECISION NOT NULL,
    rubric_breakdown_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS readiness_snapshots (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES job_assessment_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    overall_readiness DOUBLE PRECISION,
    readiness_status VARCHAR(100) NOT NULL,
    assessment_coverage DOUBLE PRECISION NOT NULL,
    evidence_confidence DOUBLE PRECISION NOT NULL,
    mandatory_readiness DOUBLE PRECISION DEFAULT 0.0,
    preferred_readiness DOUBLE PRECISION DEFAULT 0.0,
    coding_readiness DOUBLE PRECISION DEFAULT 0.0,
    interview_readiness DOUBLE PRECISION DEFAULT 0.0,
    practical_readiness DOUBLE PRECISION DEFAULT 0.0,
    resume_alignment DOUBLE PRECISION DEFAULT 0.0,
    project_relevance DOUBLE PRECISION DEFAULT 0.0,
    comm_behavioral DOUBLE PRECISION DEFAULT 0.0,
    dimension_scores_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_recommendations (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES job_assessment_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    canonical_skill_id VARCHAR(100) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    problem_identified TEXT NOT NULL,
    supporting_evidence TEXT NOT NULL,
    target_competency TEXT NOT NULL,
    priority VARCHAR(50) NOT NULL,
    recommended_practice TEXT NOT NULL,
    relevant_activity TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_assessment_user ON job_assessment_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_job_req_session ON job_requirement_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_readiness_snapshot_user ON readiness_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_job_rec_session ON job_recommendations(session_id);

