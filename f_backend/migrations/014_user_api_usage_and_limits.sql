-- ==============================================================================
-- Migration 014: Per-User API Usage Tracking & Spending Limits
-- ==============================================================================
-- Operating Goals:
--   1. Real-time audit trail of all LLM/API calls per user, feature, and model.
--   2. Enforces hard/soft monthly spending caps ($USD) per student.
--   3. Provides aggregated monthly usage analytics to prevent runaway API costs.
-- ==============================================================================

-- 1. Table: user_api_usage (immutable log of all AI/API invocations)
CREATE TABLE IF NOT EXISTS user_api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    feature VARCHAR(64) NOT NULL,            -- e.g. 'interview_turn', 'interview_grading', 'interview_report', 'resume_parse', 'mentor_chat'
    model VARCHAR(64) NOT NULL,              -- e.g. 'gemini-2.5-flash', 'gemini-3.8-flash', 'gemini-3.5-flash-lite'
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    session_id TEXT,                         -- linked interview_session or mentor_conversation if applicable
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optimize user querying and monthly spend rollups
CREATE INDEX IF NOT EXISTS idx_user_api_usage_user_created 
    ON user_api_usage (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_api_usage_feature 
    ON user_api_usage (feature);

CREATE INDEX IF NOT EXISTS idx_user_api_usage_session 
    ON user_api_usage (session_id) WHERE session_id IS NOT NULL;

-- 2. Table: user_api_spending_limits (budget and threshold settings per user)
CREATE TABLE IF NOT EXISTS user_api_spending_limits (
    user_id TEXT PRIMARY KEY,
    monthly_budget_usd NUMERIC(8, 2) NOT NULL DEFAULT 5.00,  -- Default $5.00/mo included with paid student subscription
    daily_token_limit INT NOT NULL DEFAULT 120000,           -- 120,000 tokens/day burst guard
    is_hard_limit BOOLEAN NOT NULL DEFAULT true,             -- If true, rejects AI calls when budget exhausted
    alert_threshold_pct INT NOT NULL DEFAULT 80,             -- Alert when 80% of budget reached
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. View: v_user_monthly_api_spend (real-time calendar month aggregation)
CREATE OR REPLACE VIEW v_user_monthly_api_spend AS
SELECT 
    user_id,
    DATE_TRUNC('month', created_at) AS billing_month,
    COUNT(*) AS total_calls,
    SUM(prompt_tokens) AS total_prompt_tokens,
    SUM(completion_tokens) AS total_completion_tokens,
    SUM(total_tokens) AS total_tokens,
    COALESCE(SUM(cost_usd), 0.0) AS total_spend_usd
FROM user_api_usage
GROUP BY user_id, DATE_TRUNC('month', created_at);

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

