"""
Startup Schema Self-Check Service
Compares required tables and columns to the live database schema at startup
and logs a clear, actionable error when schema drift is detected.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

REQUIRED_SCHEMA: Dict[str, List[str]] = {
    "sessions": [
        "session_id", "user_id", "resume_text", "role", "level", "mode", "status",
        "started_at", "ended_at", "resume_snapshot_json", "display_name",
        "display_name_source", "blueprint_json", "adaptive_state_json",
        "report_status", "model_used", "prompt_versions_json", "report_json",
        "consent_given", "consent_timestamp", "privacy_policy_version",
        "knowledge_map", "turn_count", "interview_state", "idempotency_key"
    ],
    "parsed_resumes": [
        "id", "hash", "raw_text", "structured_data", "ats_score", "missing_info", "created_at"
    ],
    "activity_logs": [
        "id", "actor_id", "actor_type", "action", "ip_address", "details", "created_at"
    ],
    "organization": [
        "id", "name", "status"
    ],
    "interview_turns": [
        "id", "session_id", "turn_index", "speaker", "question_id", "skill_id",
        "text", "input_mode", "stt_engine", "stt_confidence", "audio_ref",
        "audio_duration_s", "started_at", "ended_at", "word_count", "turn_status", "created_at"
    ],
    "interview_speech_metrics": [
        "turn_id", "session_id", "wpm", "filler_count", "filler_map_json",
        "pause_count", "longest_pause_s", "avg_pause_s", "speaking_time_s",
        "silence_ratio", "computed_by", "formula_version"
    ],
    "interview_evaluations": [
        "id", "turn_id", "session_id", "skill_id", "rubric_scores_json",
        "raw_score", "normalized_score", "quoted_evidence_json",
        "missing_concepts_json", "technical_mistakes_json", "improved_answer",
        "misconception_tags", "evaluator_type", "prompt_id", "prompt_version",
        "model_used", "status"
    ],
    "interview_reports": [
        "id", "session_id", "candidate_id", "report_status", "overall_score",
        "grade", "recommendation", "dimension_scores_json", "strengths_json",
        "weaknesses_json", "coverage_json", "data_sufficiency_json",
        "formula_version", "generated_at"
    ],
    "interview_question_rubrics": [
        "id", "session_id", "question_id", "skill_id", "rubric_json",
        "reference_answer", "created_at"
    ],
}


def _check_sqlite_table_columns(local_client, table: str, required_cols: List[str]) -> List[str]:
    conn = local_client._get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        rows = cur.fetchall()
        if not rows:
            return list(required_cols)
        existing = {row[1] for row in rows}
        return [c for c in required_cols if c not in existing]
    finally:
        conn.close()


def _check_remote_table_columns(real_client, table: str, required_cols: List[str]) -> List[str]:
    missing: List[str] = []
    # First check all columns together (fast single PostgREST query)
    try:
        real_client.table(table).select(",".join(required_cols)).limit(1).execute()
        return []
    except Exception:
        # Check column-by-column to pinpoint exact drift
        for col in required_cols:
            try:
                real_client.table(table).select(col).limit(1).execute()
            except Exception as col_err:
                err_s = str(col_err)
                if "PGRST205" in err_s or "Could not find the table" in err_s:
                    return list(required_cols)
                missing.append(col)
    return missing


def verify_database_schema(supabase_client) -> Dict[str, Any]:
    """
    Verifies required tables and columns against live Supabase or local SQLite mock.
    Returns status dictionary and logs CRITICAL errors on any missing columns/tables.
    """
    missing_by_table: Dict[str, List[str]] = {}
    checked_tables: List[str] = []

    real_client = getattr(supabase_client, "_real_client", None)
    local_client = getattr(supabase_client, "_local_client", None)

    for table, cols in REQUIRED_SCHEMA.items():
        checked_tables.append(table)
        missing: List[str] = []
        if real_client is not None:
            missing = _check_remote_table_columns(real_client, table, cols)
        elif local_client is not None:
            missing = _check_sqlite_table_columns(local_client, table, cols)
        elif hasattr(supabase_client, "_get_conn"):
            missing = _check_sqlite_table_columns(supabase_client, table, cols)

        if missing:
            missing_by_table[table] = missing

    ok = len(missing_by_table) == 0
    if not ok:
        logger.error(
            "[SCHEMA SELF-CHECK ERROR] Database schema drift detected! Missing columns: %s. "
            "Run migrations/010_interview_capture_and_evaluation.sql and execute "
            "\"NOTIFY pgrst, 'reload schema';\" in Supabase SQL Editor.",
            missing_by_table,
        )
    else:
        logger.info("[SCHEMA SELF-CHECK OK] Verified %d interview & core tables.", len(checked_tables))

    return {
        "ok": ok,
        "missing": missing_by_table,
        "checked_tables": checked_tables,
        "backend": "supabase" if real_client is not None else "sqlite_mock",
    }


def inspect_local_tables_ddl(sqlite_client) -> Dict[str, List[Dict[str, Any]]]:
    """Returns table column definitions (`PRAGMA table_info`) for verification output."""
    conn = sqlite_client._get_conn()
    out: Dict[str, List[Dict[str, Any]]] = {}
    try:
        cur = conn.cursor()
        for table in [
            "sessions", "parsed_resumes", "activity_logs", "organization",
            "interview_turns", "interview_speech_metrics",
            "interview_evaluations", "interview_reports", "interview_question_rubrics"
        ]:
            cur.execute(f"PRAGMA table_info({table})")
            rows = cur.fetchall()
            out[table] = [
                {"name": r[1], "type": r[2], "notnull": bool(r[3]), "default": r[4], "pk": bool(r[5])}
                for r in rows
            ]
        return out
    finally:
        conn.close()

