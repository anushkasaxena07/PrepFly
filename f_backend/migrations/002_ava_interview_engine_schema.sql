-- ============================================================================
-- Migration 002: Ava AI Interview Engine Schema & State Machine Architecture
-- ============================================================================

-- 1. Extend existing sessions table with state machine & personality columns
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS interview_state TEXT DEFAULT 'INITIALIZING';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS personality TEXT DEFAULT 'professional';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS knowledge_map TEXT DEFAULT '{}';
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS turn_count INTEGER DEFAULT 0;

-- 2. Interview Turns: Relational Turn Audit & Evidence Ledger
CREATE TABLE IF NOT EXISTS interview_turns (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type TEXT,
    stage TEXT,
    candidate_response TEXT,
    intent TEXT DEFAULT 'ANSWER',
    decision TEXT DEFAULT 'NEXT_QUESTION',
    score REAL DEFAULT 0.0,
    accuracy_score INTEGER DEFAULT 0,
    evaluation_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interview_turns_session ON interview_turns(session_id, turn_number);

-- 3. Interviewer Profiles: Configurable Personalities
CREATE TABLE IF NOT EXISTS interviewer_profiles (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    tone TEXT NOT NULL,
    formality TEXT NOT NULL,
    probing_intensity TEXT NOT NULL,
    encouragement_frequency TEXT NOT NULL,
    hint_policy TEXT NOT NULL,
    system_prompt_modifier TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed default personalities if not present
INSERT INTO interviewer_profiles (id, name, tone, formality, probing_intensity, encouragement_frequency, hint_policy, system_prompt_modifier)
VALUES
    ('friendly', 'Friendly Ava', 'Warm, supportive, encouraging, patient', 'Semi-Formal', 'Moderate', 'High', 'Generous hints with constructive nudges', 'Adopt an empathetic, encouraging tone. Reassure the candidate and offer warm transitional phrases while maintaining evaluation rigor.'),
    ('professional', 'Professional Ava', 'Objective, structured, balanced, polite', 'Formal', 'Standard', 'Moderate', 'Standard hints providing direction without answers', 'Adopt a polished, standard corporate interviewer style. Be courteous, neutral, and direct.'),
    ('challenging', 'Challenging Ava', 'Direct, inquisitive, analytical, probing', 'Formal', 'High', 'Low', 'Minimal hints; encourages candidate self-correction', 'Probe technical statements rigorously. Challenge assumptions and ask for architectural trade-offs, edge cases, and failure modes.'),
    ('strict', 'Strict Ava', 'Concise, rigorous, no-nonsense, concise', 'Very Formal', 'Maximum', 'None', 'Strictly hints on request only, minimal guidance', 'Be very concise and direct. Expect precise definitions and avoid conversational filler or unnecessary pleasantries.'),
    ('senior_engineer', 'Senior Staff Ava', 'Systemic, architectural, practical, production-focused', 'Collaborative Peer', 'High', 'Moderate', 'Pragmatic guidance pointing to system constraints', 'Speak like a seasoned Staff Engineer/Tech Lead. Focus heavily on production trade-offs, scale, latency, consistency, and operational reliability.')
ON CONFLICT (id) DO NOTHING;

-- 4. Candidate Resume Claims: Verified Claim Ledger with Provenance
CREATE TABLE IF NOT EXISTS candidate_resume_claims (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    claim_type TEXT NOT NULL, -- 'SKILL', 'PROJECT', 'ROLE', 'TECHNOLOGY', 'ACHIEVEMENT'
    claim_text TEXT NOT NULL,
    provenance_section TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resume_claims_session ON candidate_resume_claims(session_id);

-- Enable RLS
ALTER TABLE interview_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE interviewer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_resume_claims ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated read turns" ON interview_turns
    FOR SELECT USING (auth.uid() IS NOT NULL);

CREATE POLICY "Allow authenticated read profiles" ON interviewer_profiles
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated read claims" ON candidate_resume_claims
    FOR SELECT USING (auth.uid() IS NOT NULL);

