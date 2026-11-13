"""
Startup Schema Self-Check Service
Compares required tables and columns to live database metadata cleanly without
confusing temporary connectivity, timeout, permission, or stale PostgREST cache issues
for confirmed schema drift.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

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
    "notifications": [
        "id", "organization_id", "user_id", "sender_type", "sender_name",
        "target_group", "title", "message", "target_dept", "target_sem",
        "read", "created_at"
    ],
}


def _classify_remote_error(err: Exception) -> str:
    """
    Classifies a database/PostgREST error so connectivity, permission, and timeout
    failures are never misreported as missing columns.
    """
    if isinstance(err, TimeoutError):
        return "timeout"
    s = str(err or "").lower()
    if any(tok in s for tok in ("timed out", "timeout", "deadline", "504", "statement timeout")):
        return "timeout"
    if any(tok in s for tok in ("42501", "permission denied", "401", "403", "jwt", "invalid api key", "unauthorized", "row-level security")):
        return "permission_denied"
    if any(
        tok in s
        for tok in (
            "503", "502", "500", "pgrst002", "pgrst003", "service unavailable",
            "getaddrinfo", "name or service not known", "connection refused",
            "connection reset", "unreachable", "dns", "maintenance", "json could not be generated",
        )
    ):
        return "unavailable"
    if any(tok in s for tok in ("pgrst205", "42p01", "could not find the table")):
        return "table_missing"
    if "pgrst204" in s or "42703" in s or ("could not find the" in s and "column" in s) or ("column" in s and "does not exist" in s):
        return "column_missing"
    if "does not exist" in s:
        return "table_missing"
    return "unavailable"


def _fetch_postgres_columns(table: str) -> Optional[List[str]]:
    """
    Optional authoritative PostgreSQL `information_schema.columns` lookup when a direct
    DATABASE_URL + psycopg driver is available. Returns None if direct SQL is unavailable.
    """
    db_url = (os.getenv("DATABASE_URL") or "").strip()
    if not db_url:
        return None
    for mod_name in ("psycopg", "psycopg2"):
        try:
            mod = __import__(mod_name)
            with mod.connect(db_url, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = %s",
                        (table,),
                    )
                    return [str(r[0]) for r in cur.fetchall()]
        except ImportError:
            continue
        except Exception as exc:
            logger.debug("Direct PostgreSQL metadata lookup skipped (%s): %s", mod_name, type(exc).__name__)
            return None
    return None


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


def _inspect_remote_table(
    real_client: Any,
    table: str,
    required_cols: List[str],
    metadata_fetcher: Optional[Callable[[str], Optional[List[str]]]] = None,
) -> Dict[str, Any]:
    """
    Returns {"missing": [...], "stale_cache": [...], "error": Optional[str]}.
    Uses authoritative metadata if provided/available before interpreting PostgREST responses.
    """
    fetcher = metadata_fetcher or _fetch_postgres_columns
    auth_cols = None
    try:
        auth_cols = fetcher(table)
    except Exception as meta_err:
        kind = _classify_remote_error(meta_err)
        return {"missing": [], "stale_cache": [], "error": kind}

    if auth_cols is not None:
        if not auth_cols:
            return {"missing": list(required_cols), "stale_cache": [], "error": None}
        existing_set = set(auth_cols)
        missing_auth = [c for c in required_cols if c not in existing_set]
        if missing_auth:
            return {"missing": missing_auth, "stale_cache": [], "error": None}
        # Confirm PostgREST schema cache is also warm; if PostgREST rejects with PGRST204/205 despite PG metadata,
        # flag stale_cache rather than false schema drift.
        try:
            real_client.table(table).select(",".join(required_cols)).limit(1).execute()
            return {"missing": [], "stale_cache": [], "error": None}
        except Exception as rest_err:
            kind = _classify_remote_error(rest_err)
            if kind in ("column_missing", "table_missing"):
                return {"missing": [], "stale_cache": list(required_cols), "error": None}
            return {"missing": [], "stale_cache": [], "error": kind}

    # REST-only inspection (e.g., standard Supabase API without DATABASE_URL)
    try:
        real_client.table(table).select(",".join(required_cols)).limit(1).execute()
        return {"missing": [], "stale_cache": [], "error": None}
    except Exception as bulk_err:
        bulk_kind = _classify_remote_error(bulk_err)
        if bulk_kind in ("timeout", "permission_denied", "unavailable"):
            return {"missing": [], "stale_cache": [], "error": bulk_kind}
        if bulk_kind == "table_missing":
            return {"missing": list(required_cols), "stale_cache": [], "error": None}

        missing: List[str] = []
        last_col_err: Optional[str] = None
        for col in required_cols:
            try:
                real_client.table(table).select(col).limit(1).execute()
            except Exception as col_err:
                col_kind = _classify_remote_error(col_err)
                if col_kind == "table_missing":
                    return {"missing": list(required_cols), "stale_cache": [], "error": None}
                if col_kind == "column_missing":
                    missing.append(col)
                else:
                    last_col_err = col_kind
        return {"missing": missing, "stale_cache": [], "error": last_col_err if not missing else None}


def verify_database_schema(
    supabase_client: Any,
    metadata_fetcher: Optional[Callable[[str], Optional[List[str]]]] = None,
) -> Dict[str, Any]:
    """
    Verifies required tables and columns against live Supabase or local SQLite mock.
    Separates confirmed schema drift (`drift_detected`) from stale PostgREST cache (`stale_cache`)
    and temporary connectivity/timeout/permission errors (`errors`), never crashing app startup.
    """
    missing_by_table: Dict[str, List[str]] = {}
    stale_by_table: Dict[str, List[str]] = {}
    errors_by_table: Dict[str, str] = {}
    checked_tables: List[str] = []

    real_client = getattr(supabase_client, "_real_client", None)
    local_client = getattr(supabase_client, "_local_client", None)

    for table, cols in REQUIRED_SCHEMA.items():
        checked_tables.append(table)
        if real_client is not None:
            res = _inspect_remote_table(real_client, table, cols, metadata_fetcher=metadata_fetcher)
            if res["missing"]:
                missing_by_table[table] = res["missing"]
            if res["stale_cache"]:
                stale_by_table[table] = res["stale_cache"]
            if res["error"]:
                errors_by_table[table] = res["error"]
        elif local_client is not None:
            missing = _check_sqlite_table_columns(local_client, table, cols)
            if missing:
                missing_by_table[table] = missing
        elif hasattr(supabase_client, "_get_conn"):
            missing = _check_sqlite_table_columns(supabase_client, table, cols)
            if missing:
                missing_by_table[table] = missing

    drift_detected = len(missing_by_table) > 0
    if drift_detected:
        status = "drift_detected"
    elif errors_by_table:
        # Pick highest-specificity operational classification
        priorities = ("permission_denied", "timeout", "unavailable")
        found = set(errors_by_table.values())
        status = next((p for p in priorities if p in found), "unavailable")
    elif stale_by_table:
        status = "stale_cache"
    else:
        status = "ok"

    ok = (not drift_detected) and (not errors_by_table) and (not stale_by_table)

    if drift_detected:
        logger.error(
            "[SCHEMA SELF-CHECK ERROR] Confirmed database schema drift! Missing columns: %s. "
            "Apply missing additive columns cleanly and run \"NOTIFY pgrst, 'reload schema';\".",
            missing_by_table,
        )
    elif stale_by_table:
        logger.warning(
            "[SCHEMA SELF-CHECK NOTICE] PostgreSQL columns exist but PostgREST schema cache appears stale for %s. "
            "Run \"NOTIFY pgrst, 'reload schema';\" in Supabase SQL Editor.",
            list(stale_by_table.keys()),
        )
    elif errors_by_table:
        logger.warning(
            "[SCHEMA SELF-CHECK NOTICE] Metadata check incomplete (%s) across %d tables; NOT treating as schema drift.",
            status,
            len(errors_by_table),
        )
    else:
        logger.info("[SCHEMA SELF-CHECK OK] Verified %d interview & core tables.", len(checked_tables))

    return {
        "ok": ok,
        "status": status,
        "drift_detected": drift_detected,
        "missing": missing_by_table,
        "stale_cache": stale_by_table,
        "errors": errors_by_table,
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
            "interview_evaluations", "interview_reports", "interview_question_rubrics",
            "notifications",
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
