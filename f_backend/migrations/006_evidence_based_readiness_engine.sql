-- PREPFLY MIGRATION 006: EVIDENCE-BASED SKILL PROFICIENCY AND ROLE READINESS ENGINE
-- Creates canonical_skills, skill_evidence_registry, candidate_project_analyses, and project_technical_questions tables.

CREATE TABLE IF NOT EXISTS canonical_skills (
    skill_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_skill_id VARCHAR(255),
    description TEXT,
    prerequisites JSONB DEFAULT '[]'::jsonb,
    difficulty VARCHAR(50) DEFAULT 'Intermediate',
    applicable_roles JSONB DEFAULT '[]'::jsonb,
    assessment_methods JSONB DEFAULT '[]'::jsonb,
    evaluation_rubric JSONB DEFAULT '{}'::jsonb,
    is_leaf BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skill_evidence_registry (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    source_id VARCHAR(255),
    raw_score DOUBLE PRECISION,
    normalized_score DOUBLE PRECISION,
    difficulty VARCHAR(50) DEFAULT 'Intermediate',
    evidence_quality DOUBLE PRECISION DEFAULT 0.8,
    validity_status VARCHAR(50) NOT NULL,
    evaluator_type VARCHAR(100) NOT NULL,
    evaluation_rubric JSONB DEFAULT '{}'::jsonb,
    provenance_hash VARCHAR(255) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_user_skill ON skill_evidence_registry (user_id, skill_id);
CREATE INDEX IF NOT EXISTS idx_evidence_provenance ON skill_evidence_registry (user_id, provenance_hash);

CREATE TABLE IF NOT EXISTS candidate_project_analyses (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_title VARCHAR(255) NOT NULL,
    technologies JSONB DEFAULT '[]'::jsonb,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_technical_questions (
    id VARCHAR(255) PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    focus_area VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    expected_aspects JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
