-- PREPFLY MIGRATION 008: EVIDENCE-BASED DIAGNOSTIC, SCORING AND CAREER GOALS ENGINE
-- Adds student-selected career goals, canonical skill catalogue, job skill requirements,
-- dynamic assessment items with variation hashes, rubric evaluations, and calibrated skill states.

-- 1. Student Career Goals (Multi-goal support)
CREATE TABLE IF NOT EXISTS career_goals (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    role_id VARCHAR(100) NOT NULL,
    custom_role VARCHAR(255),
    target_company VARCHAR(255),
    job_description TEXT,
    experience_level VARCHAR(50) DEFAULT 'Fresher',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_career_goals_user ON career_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_career_goals_role ON career_goals(user_id, role_id);

-- 2. Canonical Skill Catalogue
CREATE TABLE IF NOT EXISTS skill_catalogue (
    id VARCHAR(255) PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    difficulty_floor VARCHAR(50) DEFAULT 'Beginner',
    difficulty_ceiling VARCHAR(50) DEFAULT 'Advanced',
    prerequisites JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_catalogue_domain ON skill_catalogue(domain);
CREATE INDEX IF NOT EXISTS idx_skill_catalogue_category ON skill_catalogue(category);

-- 3. Job Skill Requirements (Extracted from JDs or Role Profiles)
CREATE TABLE IF NOT EXISTS job_skill_requirements (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    career_goal_id VARCHAR(255),
    target_role VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    source_text_hash VARCHAR(64) NOT NULL,
    required_skills JSONB DEFAULT '[]'::jsonb,
    weight_distribution JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_skill_reqs_user_role ON job_skill_requirements(user_id, target_role);
CREATE INDEX IF NOT EXISTS idx_job_skill_reqs_goal ON job_skill_requirements(user_id, career_goal_id);

-- 4. Dynamic Assessment Items (Per-turn generated questions with variation hashes)
CREATE TABLE IF NOT EXISTS assessment_items (
    id VARCHAR(255) PRIMARY KEY,
    assessment_id VARCHAR(255) NOT NULL,
    question_id VARCHAR(255) NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    difficulty VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    expected_concepts JSONB DEFAULT '[]'::jsonb,
    rubric JSONB DEFAULT '{}'::jsonb,
    variation_hash VARCHAR(64),
    turn_index INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessment_items_assessment ON assessment_items(assessment_id);
CREATE INDEX IF NOT EXISTS idx_assessment_items_skill ON assessment_items(skill_id);
CREATE INDEX IF NOT EXISTS idx_assessment_items_variation ON assessment_items(variation_hash);

-- 5. Rubric Evaluations (Concept matching and deterministic score breakdown)
CREATE TABLE IF NOT EXISTS evaluations (
    id VARCHAR(255) PRIMARY KEY,
    assessment_item_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    raw_response TEXT,
    matched_concepts JSONB DEFAULT '[]'::jsonb,
    missed_concepts JSONB DEFAULT '[]'::jsonb,
    rubric_breakdown JSONB DEFAULT '{}'::jsonb,
    score DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluations_user ON evaluations(user_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_item ON evaluations(assessment_item_id);

-- 6. Immutable Skill Evidence (Append-only signal ledger)
CREATE TABLE IF NOT EXISTS skill_evidence (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    source_id VARCHAR(255),
    score DOUBLE PRECISION DEFAULT 0.0,
    raw_score DOUBLE PRECISION,
    weighted_score DOUBLE PRECISION,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    weight DOUBLE PRECISION DEFAULT 1.0,
    demonstrated_concepts JSONB DEFAULT '[]'::jsonb,
    missed_concepts JSONB DEFAULT '[]'::jsonb,
    misconceptions JSONB DEFAULT '[]'::jsonb,
    evidence_notes TEXT,
    rubric_version VARCHAR(50) DEFAULT 'v1',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE skill_evidence ADD COLUMN IF NOT EXISTS raw_score DOUBLE PRECISION;
ALTER TABLE skill_evidence ADD COLUMN IF NOT EXISTS weighted_score DOUBLE PRECISION;
ALTER TABLE skill_evidence ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION DEFAULT 1.0;
ALTER TABLE skill_evidence ADD COLUMN IF NOT EXISTS rubric_version VARCHAR(50) DEFAULT 'v1';

CREATE INDEX IF NOT EXISTS idx_skill_evidence_user_skill ON skill_evidence(user_id, skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_evidence_source ON skill_evidence(source_type, source_id);

-- 7. Candidate Skill States (Calibrated proficiency and confidence)
CREATE TABLE IF NOT EXISTS candidate_skill_states (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    skill_id VARCHAR(255) NOT NULL,
    proficiency DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    sample_count INTEGER NOT NULL DEFAULT 0,
    last_assessed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_candidate_skill UNIQUE(user_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_candidate_skill_states_user ON candidate_skill_states(user_id);
CREATE INDEX IF NOT EXISTS idx_candidate_skill_states_lookup ON candidate_skill_states(user_id, skill_id);

-- 8. Score Audit Log (Reproducibility & Explainability Ledger)
CREATE TABLE IF NOT EXISTS score_audit_log (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    target_role VARCHAR(255) NOT NULL,
    calculation_type VARCHAR(100) NOT NULL,
    score_inputs JSONB DEFAULT '{}'::jsonb,
    calculated_score DOUBLE PRECISION NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_score_audit_user ON score_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_score_audit_type ON score_audit_log(user_id, calculation_type);

-- Enable Row-Level Security
ALTER TABLE career_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_catalogue ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_skill_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_skill_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE score_audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS p_career_goals_all ON career_goals;
CREATE POLICY p_career_goals_all ON career_goals FOR ALL USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS p_skill_catalogue_read ON skill_catalogue;
CREATE POLICY p_skill_catalogue_read ON skill_catalogue FOR SELECT USING (true);

DROP POLICY IF EXISTS p_job_skill_reqs_all ON job_skill_requirements;
CREATE POLICY p_job_skill_reqs_all ON job_skill_requirements FOR ALL USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS p_assessment_items_read ON assessment_items;
CREATE POLICY p_assessment_items_read ON assessment_items FOR SELECT USING (true);

DROP POLICY IF EXISTS p_evaluations_all ON evaluations;
CREATE POLICY p_evaluations_all ON evaluations FOR ALL USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS p_skill_evidence_all ON skill_evidence;
CREATE POLICY p_skill_evidence_all ON skill_evidence FOR ALL USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS p_candidate_skill_states_all ON candidate_skill_states;
CREATE POLICY p_candidate_skill_states_all ON candidate_skill_states FOR ALL USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS p_score_audit_log_all ON score_audit_log;
CREATE POLICY p_score_audit_log_all ON score_audit_log FOR ALL USING (auth.uid()::text = user_id);

