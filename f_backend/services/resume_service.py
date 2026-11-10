import concurrent.futures
import os
import hashlib
import json
import random
import re
import threading
import time
import logging
import uuid
import docx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_IN_FLIGHT_LOCK = threading.Lock()
_IN_FLIGHT_PARSES = {}
_GEMINI_PARSE_SEMAPHORE = threading.BoundedSemaphore(value=4)

_RESUME_JOBS_LOCK = threading.Lock()
_RESUME_JOBS = {}
_RESUME_JOB_BY_HASH = {}
_RESUME_JOB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="prepfly-resume-job")

logger = logging.getLogger(__name__)

_IN_FLIGHT_LOCK = threading.Lock()
_IN_FLIGHT_PARSES = {}

RESUME_PARSE_PROMPT_ID = "resume_parse"
RESUME_PARSE_PROMPT_VERSION = "v1.0"


class ResumeParseError(Exception):
    """Raised when AI resume parsing fails after retries (must never return HTTP 200)."""
    def __init__(self, message: str, status_code: int = 503, retryable: bool = True, details: str = ""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details


def get_supabase():
    try:
        import app
        return app.supabase
    except Exception:
        from local_supabase import SQLiteSupabaseMock
        return SQLiteSupabaseMock()

def extract_text_from_pdf(filepath):
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception:
        try:
            import pymupdf
            doc = pymupdf.open(filepath)
            for page in doc:
                text += page.get_text() + "\n"
        except Exception as e2:
            print(f"PDF extraction error: {e2}")
    return text.strip()

def extract_text_from_docx(filepath):
    try:
        doc = docx.Document(filepath)
        text_parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    text_parts.append(" | ".join(row_cells))
        return "\n".join(text_parts).strip()
    except Exception as e:
        print(f"docx extract error: {e}")
        return ""

def compute_text_hash(text):
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def get_cached_resume(text_hash):
    try:
        from services.cache_service import cache_manager
        fast_cached = cache_manager.get(f"resume:{text_hash}")
        if fast_cached:
            return fast_cached
    except Exception:
        pass

    supabase = get_supabase()
    try:
        res = supabase.table("parsed_resumes").select("*").eq("hash", text_hash).execute()
        if res and hasattr(res, "data") and res.data:
            row = res.data[0]
            s_data = row.get("structured_data")
            if isinstance(s_data, str):
                try: s_data = json.loads(s_data)
                except: s_data = {}

            m_info = row.get("missing_info")
            if isinstance(m_info, str):
                try: m_info = json.loads(m_info)
                except: m_info = []

            result = {
                "id": row.get("id"),
                "raw_text": row.get("raw_text"),
                "structured_data": s_data or {},
                "ats_score": row.get("ats_score", 70),
                "missing_info": m_info or []
            }
            # Reject previously poisoned fallback cache entries
            if (
                isinstance(result["structured_data"], dict)
                and result["structured_data"].get("full_name") == "Candidate"
                and result["structured_data"].get("skills") == ["Software Engineering", "Algorithms"]
                and result["ats_score"] == 70
            ):
                return None
            try:
                from services.cache_service import cache_manager
                cache_manager.set(f"resume:{text_hash}", result, ttl=86400)
            except Exception:
                pass
            return result
    except Exception as e:
        print("Get cached resume notice:", e)
    return None

def save_cached_resume(text_hash, raw_text, structured_data, ats_score, missing_info):
    supabase = get_supabase()
    res_id = f"res_{text_hash[:12]}"
    try:
        record = {
            "id": res_id,
            "hash": text_hash,
            "raw_text": raw_text,
            "structured_data": json.dumps(structured_data) if isinstance(structured_data, dict) else structured_data,
            "ats_score": ats_score,
            "missing_info": json.dumps(missing_info) if isinstance(missing_info, list) else missing_info,
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table("parsed_resumes").upsert(record).execute()
        try:
            from services.cache_service import cache_manager
            cache_data = {
                "id": res_id,
                "raw_text": raw_text,
                "structured_data": structured_data if isinstance(structured_data, dict) else json.loads(structured_data),
                "ats_score": ats_score,
                "missing_info": missing_info if isinstance(missing_info, list) else json.loads(missing_info)
            }
            cache_manager.set(f"resume:{text_hash}", cache_data, ttl=86400)
        except Exception:
            pass
    except Exception as e:
        logger.warning("Save resume cache notice: %s", e)


def _strip_json_fences(content: str) -> str:
    txt = (content or "").strip()
    if txt.startswith("```"):
        lines = txt.split("\n")
        if len(lines) >= 3:
            txt = "\n".join(lines[1:-1]).strip()
        else:
            txt = txt.strip("`").strip()
    return txt


def _validate_parsed_resume(parsed: object) -> dict:
    if not isinstance(parsed, dict):
        raise ValueError("Parsed output must be a JSON object")
    if "skills" not in parsed or not isinstance(parsed.get("skills"), list):
        raise ValueError("Missing or non-list 'skills' field in parsed resume JSON")
    return parsed


def _is_transient_gemini_error(err: Exception) -> bool:
    from services.ai_service import is_transient_gemini_error
    return is_transient_gemini_error(err)


def parse_resume_content(raw_text, chat_model):
    if not raw_text or not raw_text.strip():
        return {
            "structured_data": {},
            "ats_score": 50,
            "missing_info": ["Complete Resume Content"]
        }

    text_hash = compute_text_hash(raw_text)
    cached = get_cached_resume(text_hash)
    if cached:
        logger.info("[RESUME CACHE HIT] Reusing cached resume parsing for hash %s", text_hash[:8])
        return cached

    if chat_model is None:
        raise ResumeParseError(
            message="AI resume parser is currently unavailable. Please retry.",
            status_code=503,
            retryable=True,
            details="chat_model is None",
        )

    # Single-flight deduplication across concurrent retries for the identical resume hash
    is_leader = False
    flight_entry = None
    with _IN_FLIGHT_LOCK:
        existing = _IN_FLIGHT_PARSES.get(text_hash)
        if existing is not None:
            flight_entry = existing
        else:
            flight_entry = {"event": threading.Event(), "result": None, "error": None}
            _IN_FLIGHT_PARSES[text_hash] = flight_entry
            is_leader = True

    if not is_leader:
        flight_entry["event"].wait(timeout=22.0)
        if flight_entry["result"] is not None:
            return dict(flight_entry["result"])
        if flight_entry["error"] is not None:
            raise flight_entry["error"]

    try:
        parsed_result = _execute_parse_resume_content(raw_text, text_hash, chat_model)
        if is_leader:
            flight_entry["result"] = parsed_result
        return parsed_result
    except Exception as exc:
        if is_leader:
            flight_entry["error"] = exc
        raise
    finally:
        if is_leader:
            flight_entry["event"].set()
            with _IN_FLIGHT_LOCK:
                if _IN_FLIGHT_PARSES.get(text_hash) is flight_entry:
                    _IN_FLIGHT_PARSES.pop(text_hash, None)


def _execute_parse_resume_content(raw_text, text_hash, chat_model):

    base_prompt = f"""Analyze the following resume text and extract structured candidate profile data.
Return ONLY valid JSON with no markdown formatting or backticks.

Resume Content:
{raw_text[:3500]}

Expected JSON Schema:
{{
  "full_name": "string",
  "email": "string",
  "phone": "string",
  "skills": ["string"],
  "projects": [{{"title": "string", "tech_stack": ["string"], "description": "string"}}],
  "experience": [{{"role": "string", "company": "string", "duration": "string", "key_achievements": ["string"]}}],
  "education": [{{"degree": "string", "institution": "string", "year": "string"}}],
  "ats_score": 75,
  "missing_info": ["string"]
}}"""

    from langchain_core.messages import HumanMessage
    from services.ai_service import (
        get_fallback_gemini_models,
        is_model_not_found_error,
        is_test_gemini_key,
        mark_gemini_model_unavailable,
    )

    model_used = getattr(chat_model, "model", None) or getattr(chat_model, "model_name", None) or "gemini"
    last_err = None
    prompt_to_send = base_prompt
    started_at = time.monotonic()
    total_budget_s = 20.0

    # Up to 3 attempts with bounded exponential backoff + jitter on transient 503/504,
    # and validation-error feedback on invalid JSON.
    max_attempts = 3
    retry_count = 0
    for attempt in range(max_attempts):
        if attempt > 0 and (time.monotonic() - started_at) >= total_budget_s:
            break
        retry_count = attempt
        try:
            with _GEMINI_PARSE_SEMAPHORE:
                response = chat_model.invoke([HumanMessage(content=prompt_to_send)])
            raw_content = getattr(response, "content", "") if response is not None else ""
            cleaned = _strip_json_fences(raw_content)
            parsed = _validate_parsed_resume(json.loads(cleaned))

            ats_score = parsed.get("ats_score", 70)
            missing_info = parsed.get("missing_info", [])
            save_cached_resume(text_hash, raw_text, parsed, ats_score, missing_info)
            latency_ms = round((time.monotonic() - started_at) * 1000.0, 1)
            logger.info(
                "Resume parse success: model=%s latency_ms=%s retry_count=%d hash=%s",
                model_used, latency_ms, retry_count, text_hash[:8],
            )
            return {
                "structured_data": parsed,
                "ats_score": ats_score,
                "missing_info": missing_info,
                "model_used": str(model_used),
                "latency_ms": latency_ms,
                "retry_count": retry_count,
                "prompt_id": RESUME_PARSE_PROMPT_ID,
                "prompt_version": RESUME_PARSE_PROMPT_VERSION,
            }
        except (json.JSONDecodeError, ValueError) as val_err:
            last_err = val_err
            logger.warning("Resume parse JSON validation failed (attempt %d/%d): %s", attempt + 1, max_attempts, val_err)
            prompt_to_send = (
                f"{base_prompt}\n\nPREVIOUS OUTPUT WAS INVALID JSON ({val_err}). "
                "Respond with ONLY a valid JSON object matching the schema."
            )
        except Exception as err:
            last_err = err
            logger.warning("Resume parse Gemini call failed (attempt %d/%d): %s", attempt + 1, max_attempts, err)
            if is_model_not_found_error(err):
                mark_gemini_model_unavailable(str(model_used))
                break
            if _is_transient_gemini_error(err) and attempt < max_attempts - 1:
                if (time.monotonic() - started_at) >= total_budget_s:
                    break
                sleep_s = (0.3 * (2 ** attempt)) + random.uniform(0.0, 0.2)
                time.sleep(sleep_s)
                continue
            if not _is_transient_gemini_error(err):
                break

    # Explicit fallback model attempt only for real live Gemini clients (never for unit-test mocks or test keys)
    from unittest.mock import NonCallableMock
    live_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_INTERVIEW_KEY") or ""
    is_mock_client = isinstance(chat_model, NonCallableMock)
    if not is_mock_client and not is_test_gemini_key(live_api_key):
        discover_live = last_err is not None and is_model_not_found_error(last_err)
        for fallback_model in get_fallback_gemini_models(live_api_key, exclude_model=str(model_used), include_discovery=discover_live):
            if (time.monotonic() - started_at) >= total_budget_s + 2.0:
                break
            retry_count += 1
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                fb_chat = ChatGoogleGenerativeAI(
                    api_key=live_api_key,
                    model=fallback_model,
                    temperature=0.3,
                    max_retries=0,
                    timeout=12,
                )
                with _GEMINI_PARSE_SEMAPHORE:
                    fb_resp = fb_chat.invoke([HumanMessage(content=base_prompt)])
                fb_raw = getattr(fb_resp, "content", "") if fb_resp is not None else ""
                fb_parsed = _validate_parsed_resume(json.loads(_strip_json_fences(fb_raw)))
                ats_score = fb_parsed.get("ats_score", 70)
                missing_info = fb_parsed.get("missing_info", [])
                save_cached_resume(text_hash, raw_text, fb_parsed, ats_score, missing_info)
                latency_ms = round((time.monotonic() - started_at) * 1000.0, 1)
                logger.warning(
                    "Resume parse succeeded on fallback model='%s' after primary='%s' latency_ms=%s retry_count=%d",
                    fallback_model, model_used, latency_ms, retry_count,
                )
                return {
                    "structured_data": fb_parsed,
                    "ats_score": ats_score,
                    "missing_info": missing_info,
                    "model_used": fallback_model,
                    "latency_ms": latency_ms,
                    "retry_count": retry_count,
                    "prompt_id": RESUME_PARSE_PROMPT_ID,
                    "prompt_version": RESUME_PARSE_PROMPT_VERSION,
                }
            except Exception as fb_err:
                last_err = fb_err
                if is_model_not_found_error(fb_err):
                    mark_gemini_model_unavailable(fallback_model)
                logger.warning("Resume parse fallback model '%s' failed: %s", fallback_model, fb_err)

    latency_ms = round((time.monotonic() - started_at) * 1000.0, 1)
    failure_reason = type(last_err).__name__ if last_err else "unknown_error"
    logger.error(
        "Resume parse failed loudly: model=%s latency_ms=%s retry_count=%d failure_reason=%s hash=%s",
        model_used, latency_ms, retry_count, failure_reason, text_hash[:8],
    )
    status_code = 504 if (last_err and ("504" in str(last_err) or "deadline" in str(last_err).lower() or "timed out" in str(last_err).lower())) else 503
    raise ResumeParseError(
        message="AI resume parsing failed after retries. Please retry uploading your resume or continue without a resume.",
        status_code=status_code,
        retryable=True,
        details=failure_reason,
    )


def deterministic_parse_resume(raw_text: str) -> dict:
    """
    Deterministic, zero-LLM resume extraction fallback grounded strictly in input text.
    Never invents fake skills or synthetic names; explicitly tags `is_partial=True`.
    """
    text = (raw_text or "").strip()
    if not text:
        return {
            "structured_data": {
                "full_name": "",
                "email": "",
                "phone": "",
                "skills": [],
                "projects": [],
                "experience": [],
                "education": [],
                "ats_score": 0,
                "missing_info": ["Empty resume text"],
            },
            "ats_score": 0,
            "missing_info": ["Empty resume text"],
            "model_used": "deterministic_fallback",
            "is_partial": True,
            "prompt_id": RESUME_PARSE_PROMPT_ID,
            "prompt_version": RESUME_PARSE_PROMPT_VERSION,
        }

    from services.ats_engine import extract_skills
    skills = extract_skills(text)
    email_m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone_m = re.search(r"(?:\+?\d[\d\s\-().]{8,16}\d)", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    first_line = lines[0][:80] if lines else ""
    inferred_name = first_line if (first_line and "@" not in first_line and len(first_line.split()) <= 5) else ""

    missing = []
    if not skills:
        missing.append("Recognized Technical Skills")
    if not email_m:
        missing.append("Email Address")

    structured = {
        "full_name": inferred_name,
        "email": email_m.group(0) if email_m else "",
        "phone": phone_m.group(0).strip() if phone_m else "",
        "skills": skills,
        "projects": [],
        "experience": [],
        "education": [],
        "ats_score": None,
        "missing_info": missing,
    }
    _validate_parsed_resume(structured)
    return {
        "structured_data": structured,
        "ats_score": None,
        "missing_info": missing,
        "model_used": "deterministic_fallback",
        "is_partial": True,
        "prompt_id": RESUME_PARSE_PROMPT_ID,
        "prompt_version": RESUME_PARSE_PROMPT_VERSION,
    }


def _run_resume_job(job_id: str, raw_text: str, user_id, org_id, chat_model, create_session: bool):
    started = time.monotonic()
    with _RESUME_JOBS_LOCK:
        job = _RESUME_JOBS.get(job_id)
        if not job:
            return
        job["status"] = "processing"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        parse_result = parse_resume_content(raw_text, chat_model)
        structured = parse_result.get("structured_data", {})
        ats_score = parse_result.get("ats_score", 70)
        session_id = None
        display_name = None

        if create_session:
            from services.identity_service import resolve_candidate_display_name
            supabase = get_supabase()
            user_payload = {"sub": user_id, "organization_id": org_id} if user_id else None
            display_name, display_name_source = resolve_candidate_display_name(
                user_payload=user_payload,
                user_id=user_id,
                parsed_resume=structured,
                supabase_client=supabase,
            )
            session_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            session_data = {
                "session_id": session_id,
                "resume_text": raw_text,
                "resume_snapshot_json": json.dumps(structured),
                "question_index": 0,
                "questions": [],
                "responses": [],
                "feedbacks": [],
                "active": True,
                "status": "created",
                "mode": "resume",
                "role": "Resume Based",
                "level": "Mid",
                "interview_mode": "resume",
                "total_questions": 10,
                "ats_score": ats_score,
                "structured_resume": json.dumps(structured),
                "display_name": display_name,
                "display_name_source": display_name_source,
                "report_status": "pending",
                "model_used": parse_result.get("model_used"),
                "prompt_versions_json": json.dumps({"resume_parse": RESUME_PARSE_PROMPT_VERSION}),
                "consent_given": 1,
                "consent_timestamp": now_iso,
                "privacy_policy_version": "DPDP-2023-v1.0",
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            if user_id:
                session_data["user_id"] = user_id
            if org_id:
                session_data["organization_id"] = org_id
            supabase.table("sessions").insert(session_data).execute()

        with _RESUME_JOBS_LOCK:
            job = _RESUME_JOBS.get(job_id)
            if job:
                job["status"] = "completed"
                job["session_id"] = session_id
                job["display_name"] = display_name
                job["ats_score"] = ats_score
                job["structured_data"] = structured
                job["missing_info"] = parse_result.get("missing_info", [])
                job["model_used"] = parse_result.get("model_used")
                job["latency_ms"] = round((time.monotonic() - started) * 1000.0, 1)
                job["updated_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        fb = deterministic_parse_resume(raw_text)
        with _RESUME_JOBS_LOCK:
            job = _RESUME_JOBS.get(job_id)
            if job:
                job["status"] = "failed"
                job["error"] = str(getattr(exc, "message", None) or exc)
                job["retryable"] = bool(getattr(exc, "retryable", True))
                job["status_code"] = int(getattr(exc, "status_code", 503))
                job["fallback_available"] = True
                job["deterministic_fallback"] = fb["structured_data"]
                job["latency_ms"] = round((time.monotonic() - started) * 1000.0, 1)
                job["updated_at"] = datetime.now(timezone.utc).isoformat()


def create_resume_parse_job(
    raw_text: str,
    chat_model,
    user_id=None,
    org_id=None,
    create_session: bool = True,
    run_async: bool = True,
) -> dict:
    """
    Creates (or deduplicates by user_id + content hash) a background resume parsing job.
    """
    text_hash = compute_text_hash(raw_text)
    dedupe_key = (str(user_id or "anon"), text_hash)

    with _RESUME_JOBS_LOCK:
        existing_id = _RESUME_JOB_BY_HASH.get(dedupe_key)
        if existing_id and existing_id in _RESUME_JOBS:
            existing_job = _RESUME_JOBS[existing_id]
            if existing_job["status"] in ("queued", "processing", "completed"):
                copy_job = dict(existing_job)
                copy_job["deduplicated"] = True
                return copy_job

        job_id = f"rjob_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        job = {
            "job_id": job_id,
            "user_id": str(user_id) if user_id else None,
            "organization_id": org_id,
            "text_hash": text_hash,
            "text_length": len(raw_text or ""),
            "status": "queued",
            "retryable": True,
            "deduplicated": False,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        _RESUME_JOBS[job_id] = job
        _RESUME_JOB_BY_HASH[dedupe_key] = job_id

    if run_async:
        _RESUME_JOB_EXECUTOR.submit(_run_resume_job, job_id, raw_text, user_id, org_id, chat_model, create_session)
    else:
        _run_resume_job(job_id, raw_text, user_id, org_id, chat_model, create_session)

    with _RESUME_JOBS_LOCK:
        return dict(_RESUME_JOBS[job_id])


def get_resume_parse_job(job_id: str):
    with _RESUME_JOBS_LOCK:
        job = _RESUME_JOBS.get(job_id)
        return dict(job) if job else None


def clear_resume_jobs_for_tests():
    with _RESUME_JOBS_LOCK:
        _RESUME_JOBS.clear()
        _RESUME_JOB_BY_HASH.clear()
