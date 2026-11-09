-- =============================================================================
-- Migration 005: PrepFly Complete Candidate Intelligence & Topic Coverage Engine
-- =============================================================================

CREATE TABLE IF NOT EXISTS topic_assignment_progress (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    topic_id VARCHAR(100) NOT NULL,
    total_required_questions INTEGER NOT NULL DEFAULT 5,
    completed_question_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    completed_count INTEGER NOT NULL DEFAULT 0,
    coverage_percentage DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_fully_covered INTEGER NOT NULL DEFAULT 0,
    average_assignment_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    last_attempted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS candidate_intelligence_snapshots (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    target_role VARCHAR(255) NOT NULL,
    target_company VARCHAR(255),
    overall_readiness DOUBLE PRECISION,
    readiness_status VARCHAR(100) NOT NULL,
    assessment_coverage DOUBLE PRECISION NOT NULL,
    evidence_confidence VARCHAR(50) NOT NULL,
    resume_quality_score DOUBLE PRECISION NOT NULL,
    jd_alignment_score DOUBLE PRECISION NOT NULL,
    ava_interview_score DOUBLE PRECISION NOT NULL,
    coding_score DOUBLE PRECISION NOT NULL,
    project_experience_score DOUBLE PRECISION NOT NULL,
    communication_score DOUBLE PRECISION NOT NULL,
    consistency_score DOUBLE PRECISION NOT NULL,
    major_strengths_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    major_gaps_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    improvement_deltas_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    coaching_recommendations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topic_assign_user_topic ON topic_assignment_progress(user_id, topic_id);
CREATE INDEX IF NOT EXISTS idx_cand_intel_user ON candidate_intelligence_snapshots(user_id, created_at DESC);

