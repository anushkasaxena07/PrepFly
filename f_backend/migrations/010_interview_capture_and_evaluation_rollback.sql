-- ============================================================================
-- Rollback for Migration 010: Interview Capture, Evaluation & Report Schema
-- Reverses all new tables, indexes, constraints, and policies added in 010.
-- ============================================================================

DROP TABLE IF EXISTS interview_question_rubrics CASCADE;
DROP TABLE IF EXISTS interview_reports CASCADE;
DROP TABLE IF EXISTS interview_evaluations CASCADE;
DROP TABLE IF EXISTS interview_speech_metrics CASCADE;

DROP INDEX IF EXISTS uq_interview_turns_session_idx_speaker;
DROP INDEX IF EXISTS idx_interview_turns_session_idx;
DROP INDEX IF EXISTS idx_sessions_idempotency_key;

ALTER TABLE sessions DROP CONSTRAINT IF EXISTS chk_sessions_status;
ALTER TABLE sessions DROP CONSTRAINT IF EXISTS chk_sessions_display_name_source;
ALTER TABLE sessions DROP CONSTRAINT IF EXISTS chk_sessions_report_status;

ALTER TABLE sessions DROP COLUMN IF EXISTS job_target_id;
ALTER TABLE sessions DROP COLUMN IF EXISTS level;
ALTER TABLE sessions DROP COLUMN IF EXISTS mode;
ALTER TABLE sessions DROP COLUMN IF EXISTS status;
ALTER TABLE sessions DROP COLUMN IF EXISTS started_at;
ALTER TABLE sessions DROP COLUMN IF EXISTS ended_at;
ALTER TABLE sessions DROP COLUMN IF EXISTS resume_snapshot_json;
ALTER TABLE sessions DROP COLUMN IF EXISTS display_name;
ALTER TABLE sessions DROP COLUMN IF EXISTS display_name_source;
ALTER TABLE sessions DROP COLUMN IF EXISTS blueprint_json;
ALTER TABLE sessions DROP COLUMN IF EXISTS adaptive_state_json;
ALTER TABLE sessions DROP COLUMN IF EXISTS report_status;
ALTER TABLE sessions DROP COLUMN IF EXISTS model_used;
ALTER TABLE sessions DROP COLUMN IF EXISTS prompt_versions_json;

NOTIFY pgrst, 'reload schema';

