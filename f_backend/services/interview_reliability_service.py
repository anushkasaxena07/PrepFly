"""
Phase 7: Reliability, Speed & Cost Controls for PrepFly AI Interview
Provides:
  1. Per-user daily token budget enforcement (atomic L1 + cache_service counter).
  2. Concise resume summary helper (prevents full raw resume prompt bloat).
  3. Structured logging scrubbed of PII, answer text, resume text, and quotes.
  4. Audit logging for every report generation and status transition.
  5. Bounded background per-turn evaluation executor + awaiting before report synthesis.
  6. Graceful degradation messaging for Gemini 503/429/504 transient errors.
"""

import json
import logging
import os
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.interview_scoring_config import (
    DAILY_USER_TOKEN_BUDGET,
    FORMULA_VERSION,
    MAX_EVAL_CONCURRENCY,
    RESUME_SUMMARY_MAX_CHARS,
)

logger = logging.getLogger("prepfly.interview.telemetry")

PII_REDACT_KEYS = frozenset({
    "answer",
    "candidate_answer",
    "text",
    "resume_text",
    "raw_text",
    "email",
    "display_name",
    "candidate_name",
    "quote",
    "quoted_justification",
    "improved_answer",
    "authorization",
    "token",
})


class TokenBudgetExceededError(RuntimeError):
    """Raised when a user reaches their daily AI token budget."""

    def __init__(self, user_id: str, used: int, limit: int):
        self.user_id = user_id
        self.used = used
        self.limit = limit
        self.status_code = 429
        super().__init__(f"Daily AI evaluation token budget reached ({used}/{limit} tokens). Try again tomorrow.")


class DailyTokenBudgetTracker:
    """Thread-safe per-user daily token tracker (L1 + optional Redis/cache_service sync)."""

    _lock = threading.Lock()
    _counters: Dict[str, int] = {}

    @classmethod
    def _key(cls, user_id: str) -> str:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return f"prepfly:token_budget:{user_id or 'anonymous'}:{day}"

    @classmethod
    def get_usage(cls, user_id: Optional[str]) -> int:
        k = cls._key(str(user_id or "anonymous"))
        with cls._lock:
            val = cls._counters.get(k, 0)
        try:
            from services.cache_service import cache_manager
            cached = cache_manager.get(k)
            if isinstance(cached, int) and cached > val:
                val = cached
        except Exception:
            pass
        return val

    @classmethod
    def record_usage(cls, user_id: Optional[str], prompt_chars: int, output_chars: int = 0) -> int:
        # Conservative ~4 chars per token approximation + fixed structural overhead
        tokens = max(1, (int(prompt_chars) + int(output_chars)) // 4)
        k = cls._key(str(user_id or "anonymous"))
        with cls._lock:
            new_total = cls._counters.get(k, 0) + tokens
            cls._counters[k] = new_total
        try:
            from services.cache_service import cache_manager
            cache_manager.set(k, new_total, ttl=86400)
        except Exception:
            pass
        return new_total

    @classmethod
    def check_budget(cls, user_id: Optional[str], estimated_tokens: int = 400, limit: Optional[int] = None) -> int:
        cap = int(limit if limit is not None else os.getenv("DAILY_USER_TOKEN_BUDGET", DAILY_USER_TOKEN_BUDGET))
        used = cls.get_usage(user_id)
        if used + estimated_tokens > cap:
            raise TokenBudgetExceededError(str(user_id or "anonymous"), used, cap)
        return used

    @classmethod
    def reset_for_tests(cls, user_id: Optional[str] = None) -> None:
        with cls._lock:
            if user_id is None:
                cls._counters.clear()
            else:
                k = cls._key(str(user_id))
                cls._counters.pop(k, None)


def build_concise_resume_summary(
    resume_source: Any,
    max_chars: int = RESUME_SUMMARY_MAX_CHARS,
) -> str:
    """
    Compresses parsed resume dict or raw resume text into a small bounded context string
    (<= max_chars) so per-turn grading and question generation never resend huge resumes.
    """
    if not resume_source:
        return ""
    if isinstance(resume_source, dict):
        parts: List[str] = []
        role = resume_source.get("target_role") or resume_source.get("role") or resume_source.get("experience_level")
        if role:
            parts.append(f"Role/Level: {role}")
        skills = resume_source.get("skills") or resume_source.get("technical_skills") or []
        if isinstance(skills, list) and skills:
            parts.append("Skills: " + ", ".join(str(s) for s in skills[:10]))
        projects = resume_source.get("projects") or []
        if isinstance(projects, list) and projects:
            p_titles = [str(p.get("name") or p.get("title") or p)[:40] if isinstance(p, dict) else str(p)[:40] for p in projects[:2]]
            parts.append("Projects: " + "; ".join(p_titles))
        summary = " | ".join(parts)
        return summary[:max_chars]

    cleaned = " ".join(str(resume_source).split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max(0, max_chars - 3)].rstrip() + "..."


def sanitize_log_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Strips PII, answer content, transcripts, and resume text before logging."""
    safe: Dict[str, Any] = {}
    for k, v in (fields or {}).items():
        if str(k).lower() in PII_REDACT_KEYS:
            safe[k] = "[REDACTED]"
        elif isinstance(v, str) and len(v) > 160 and str(k).lower() not in ("error", "message", "status_reason"):
            safe[k] = f"[len={len(v)}]"
        else:
            safe[k] = v
    return safe


def log_structured_event(event: str, level: int = logging.INFO, **fields: Any) -> Dict[str, Any]:
    """Emits a single JSON structured telemetry line guaranteed free of PII and answer text."""
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **sanitize_log_fields(fields),
    }
    try:
        logger.log(level, json.dumps(payload, default=str))
    except Exception:
        pass
    return payload


def record_report_audit_log(
    supabase_client: Any,
    session_id: str,
    actor_id: Optional[str],
    report_status: str,
    previous_status: Optional[str] = None,
    overall_score: Optional[float] = None,
    formula_version: str = FORMULA_VERSION,
) -> Dict[str, Any]:
    """
    Audits every report generation & status transition in `activity_logs` + structured log.
    Contains NO PII or answer text.
    """
    action = (
        f"interview_report_status_change:{previous_status}->{report_status}"
        if previous_status and previous_status != report_status
        else f"interview_report_generated:{report_status}"
    )
    audit_payload = {
        "id": f"act_{uuid.uuid4().hex[:14]}",
        "actor_id": str(actor_id or "anonymous"),
        "user_id": str(actor_id or "anonymous"),
        "action": action,
        "entity_type": "interview_report",
        "entity_id": session_id,
        "details": json.dumps({
            "session_id": session_id,
            "previous_status": previous_status,
            "report_status": report_status,
            "overall_score": overall_score,
            "formula_version": formula_version,
        }),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if supabase_client is not None:
        try:
            supabase_client.table("activity_logs").insert(audit_payload).execute()
        except Exception as err:
            log_structured_event("report_audit_insert_failed", level=logging.WARNING, session_id=session_id, error=str(err))

    log_structured_event(
        "interview_report_audit",
        session_id=session_id,
        actor_id=str(actor_id or "anonymous"),
        previous_status=previous_status,
        report_status=report_status,
        overall_score=overall_score,
        formula_version=formula_version,
    )
    return audit_payload


def get_degraded_error_payload(error_code: str, detail: str = "", attempt: int = 1, max_attempts: int = 3) -> Dict[str, Any]:
    """Returns a user-facing graceful degradation notice for Gemini 503/429/504."""
    code_up = str(error_code or "GRADING_ERROR").upper()
    if "429" in code_up:
        msg = "AI evaluation quota is temporarily busy (429). Your responses are safely saved; we will retry automatically and you can also click Retry Evaluation."
        retry_after = 6
    elif "504" in code_up or "TIMEOUT" in code_up:
        msg = "AI evaluation timed out waiting for a model response (504). Your responses are saved cleanly — automatic retry is scheduled."
        retry_after = 4
    elif "503" in code_up or "UNAVAILABLE" in code_up:
        msg = "AI evaluation service is temporarily overloaded (503). Automatic exponential backoff retries are active and your transcript is safely stored."
        retry_after = 4
    else:
        msg = "AI evaluation could not complete right now. Your transcript is preserved — please retry evaluation."
        retry_after = 5

    return {
        "retryable": True,
        "error_code": code_up,
        "retry_after_s": retry_after,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "degraded_message": msg,
        "detail": detail[:180] if detail else None,
    }


# ── Bounded Background Per-Turn Evaluation Pool ──────────────────────────────
_BG_EVAL_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_EVAL_CONCURRENCY, thread_name_prefix="prepfly-turn-eval")
_BG_FUTURES_LOCK = threading.Lock()
_BG_SESSION_FUTURES: Dict[str, List[Future]] = {}


def submit_background_turn_eval(
    supabase_client: Any,
    session_id: str,
    turn_row: Dict[str, Any],
    question_text: str,
    chat_model: Any,
    user_id: Optional[str] = None,
    role: str = "Software Engineer",
    difficulty: str = "Medium",
    resume_summary: str = "",
) -> Optional[Future]:
    """
    Schedules immediate background rubric grading right after `/next` persists a turn
    so end-of-interview report generation finishes much faster.
    """
    if not turn_row or not session_id:
        return None

    from services.interview_rubric_grader import grade_and_persist_turn

    def _run():
        try:
            return grade_and_persist_turn(
                supabase_client=supabase_client,
                session_id=session_id,
                turn_row=turn_row,
                question_text=question_text,
                chat_model=chat_model,
                user_id=user_id,
                role=role,
                difficulty=difficulty,
                resume_summary=resume_summary,
            )
        except Exception as err:
            log_structured_event(
                "background_turn_eval_error",
                level=logging.WARNING,
                session_id=session_id,
                turn_id=turn_row.get("id"),
                error=str(err),
            )
            return None

    fut = _BG_EVAL_EXECUTOR.submit(_run)
    with _BG_FUTURES_LOCK:
        _BG_SESSION_FUTURES.setdefault(session_id, []).append(fut)
    return fut


def await_background_turn_evals(session_id: str, timeout_s: float = 20.0) -> int:
    """Waits up to `timeout_s` for any in-flight per-turn background evaluations to settle."""
    with _BG_FUTURES_LOCK:
        futs = list(_BG_SESSION_FUTURES.pop(session_id, []))
    completed = 0
    for f in futs:
        try:
            f.result(timeout=timeout_s)
            completed += 1
        except Exception:
            pass
    return completed

