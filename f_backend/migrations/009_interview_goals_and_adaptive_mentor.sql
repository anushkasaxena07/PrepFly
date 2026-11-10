-- ============================================================================
-- Migration 009: PrepFly Adaptive AI Interview Mentor - Interview Goals & Context
-- ============================================================================

CREATE TABLE IF NOT EXISTS interview_goals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    target_company TEXT,
    target_role TEXT NOT NULL,
    job_description_text TEXT,
    required_experience_years REAL DEFAULT 0.0,
    candidate_actual_experience_years REAL DEFAULT 0.0,
    resume_text TEXT,
    target_interview_date TEXT,
    days_horizon INTEGER DEFAULT 30,
    daily_minutes INTEGER DEFAULT 60,
    self_reported_skills TEXT DEFAULT '[]', -- JSON array of claimed skills
    previous_attempts INTEGER DEFAULT 0,
    learning_preference TEXT DEFAULT 'hands-on', -- 'reading', 'walkthrough', 'hands-on'
    status TEXT DEFAULT 'active', -- 'active', 'completed', 'archived'
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for rapid lookup
CREATE INDEX IF NOT EXISTS idx_interview_goals_user_id ON interview_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_interview_goals_status ON interview_goals(status);

-- Enable Row-Level Security
ALTER TABLE interview_goals ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own interview goals"
    ON interview_goals FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own interview goals"
    ON interview_goals FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own interview goals"
    ON interview_goals FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

