import concurrent.futures
import hashlib
import importlib.util
import json
import logging
import os
import random
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import NonCallableMock

import docx

logger = logging.getLogger(__name__)

_IN_FLIGHT_LOCK = threading.Lock()
_IN_FLIGHT_PARSES: Dict[str, Dict[str, Any]] = {}
_GEMINI_PARSE_SEMAPHORE = threading.BoundedSemaphore(value=4)

_RESUME_JOBS_LOCK = threading.Lock()
_RESUME_JOBS: Dict[str, Dict[str, Any]] = {}
_RESUME_JOB_BY_HASH: Dict[tuple, str] = {}
_RESUME_JOB_PAYLOADS: Dict[str, Dict[str, Any]] = {}
_RESUME_JOB_SECRETS: Dict[str, str] = {}
_RESUME_JOB_RETRY_KEYS: Dict[tuple, str] = {}
_RESUME_JOB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="prepfly-resume-job")
MAX_RESUME_JOBS_IN_MEM = 500
RESUME_JOB_TTL_SECONDS = 3600.0

RESUME_PARSE_PROMPT_ID = "resume_parse"
RESUME_PARSE_PROMPT_VERSION = "v1.1"
MAX_GEMINI_RESUME_CHARS = int(os.getenv("RESUME_MAX_GEMINI_CHARS", "4500"))
PRIMARY_ATTEMPT_TIMEOUT_S = float(os.getenv("RESUME_PRIMARY_TIMEOUT_S", "10.0"))
PRIMARY_BUDGET_SECONDS = float(os.getenv("RESUME_PRIMARY_BUDGET_S", "12.0"))
FALLBACK_TIMEOUT_SECONDS = float(os.getenv("RESUME_FALLBACK_TIMEOUT_S", "10.0"))
FALLBACK_BUDGET_SECONDS = float(os.getenv("RESUME_FALLBACK_BUDGET_S", "18.0"))
TOTAL_BUDGET_SECONDS = float(os.getenv("RESUME_TOTAL_BUDGET_S", "32.0"))


class ResumeParseError(Exception):
    """Raised when AI or local resume parsing fails loudly (must never return HTTP 200)."""

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


def normalize_resume_text(raw_text: str) -> str:
    """Normalizes extracted PDF/DOCX text by removing control artifacts, scanner noise, and noisy whitespace."""
    if not raw_text:
        return ""
    txt = raw_text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    # Rejoin soft hyphenated word breaks across line wraps (e.g., "micro-\nservices" -> "microservices")
    txt = re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", txt)
    noise_line_re = re.compile(
        r"^(?:page\s+\d+(?:\s+of\s+\d+)?|scanned\s+(?:with|by)\s+.+|camscanner)$",
        flags=re.IGNORECASE,
    )
    cleaned_lines: List[str] = []
    for line in txt.split("\n"):
        # Strip zero-width characters & collapse internal runs of spaces/tabs
        line = re.sub(r"[\u200b-\u200d\ufeff]", "", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line and noise_line_re.match(line):
            continue
        cleaned_lines.append(line)
    normalized = "\n".join(cleaned_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _try_ocr_pdf_pages(doc) -> str:
    """Optional OCR path only when pytesseract and Pillow are installed in environment."""
    if importlib.util.find_spec("pytesseract") is None or importlib.util.find_spec("PIL") is None:
        return ""
    try:
        import io as _io
        import pytesseract
        from PIL import Image

        ocr_chunks: List[str] = []
        for idx, page in enumerate(doc):
            if idx >= 5:
                break
            pix = page.get_pixmap(dpi=180)
            img = Image.open(_io.BytesIO(pix.tobytes("png")))
            txt = pytesseract.image_to_string(img) or ""
            if txt.strip():
                ocr_chunks.append(txt.strip())
        return normalize_resume_text("\n".join(ocr_chunks))
    except Exception:
        return ""


def extract_resume_text_detailed(filepath: str, ext: str = "") -> Dict[str, Any]:
    """
    Extracts normalized text from PDF or DOCX and classifies empty, encrypted, corrupt,
    and scanned/image-only files cleanly without logging PII or resume text.
    """
    ext_low = (ext or os.path.splitext(filepath)[1].lstrip(".")).lower()
    if ext_low == "docx":
        try:
            document = docx.Document(filepath)
            text_parts = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        text_parts.append(" | ".join(row_cells))
            normalized = normalize_resume_text("\n".join(text_parts))
            return {
                "text": normalized,
                "page_count": None,
                "extraction_method": "python-docx",
                "ocr_used": False,
                "error_code": None if normalized else "empty_text",
            }
        except Exception:
            raise ResumeParseError(
                message="Uploaded DOCX file appears corrupt or unreadable. Please upload a valid PDF or DOCX resume.",
                status_code=400,
                retryable=False,
                details="corrupt_docx",
            )

    if ext_low == "pdf":
        import pymupdf

        doc = None
        try:
            with open(filepath, "rb") as pdf_fh:
                pdf_bytes = pdf_fh.read()
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception:
            raise ResumeParseError(
                message="Uploaded PDF file appears corrupt or unreadable. Please re-export as PDF and try again.",
                status_code=400,
                retryable=False,
                details="corrupt_pdf",
            )

        try:
            if getattr(doc, "needs_pass", False):
                raise ResumeParseError(
                    message="Uploaded PDF is password-protected/encrypted. Please upload an unlocked PDF or DOCX.",
                    status_code=400,
                    retryable=False,
                    details="encrypted_pdf",
                )
            page_count = len(doc)
            if page_count == 0:
                raise ResumeParseError(
                    message="Uploaded PDF contains no pages.",
                    status_code=400,
                    retryable=False,
                    details="empty_pdf",
                )
            raw_chunks = [page.get_text("text") or "" for page in doc]
            normalized = normalize_resume_text("\n".join(raw_chunks))
            # Use local PyMuPDF text when substantial; otherwise treat as scanned/low-text PDF and try OCR
            if normalized and len(normalized) >= 40 and len(normalized.split()) >= 5:
                return {
                    "text": normalized,
                    "page_count": page_count,
                    "extraction_method": "pymupdf",
                    "ocr_used": False,
                    "error_code": None,
                }
            # Scanned / image-only / low-text PDF fallback
            ocr_text = _try_ocr_pdf_pages(doc)
            if ocr_text and (not normalized or len(ocr_text) >= len(normalized)):
                return {
                    "text": ocr_text,
                    "page_count": page_count,
                    "extraction_method": "pymupdf_ocr",
                    "ocr_used": True,
                    "error_code": None,
                }
            if normalized:
                return {
                    "text": normalized,
                    "page_count": page_count,
                    "extraction_method": "pymupdf",
                    "ocr_used": False,
                    "error_code": None,
                }
            raise ResumeParseError(
                message="Uploaded PDF appears to be a scanned image with no selectable text. Please upload a text-based PDF or DOCX.",
                status_code=422,
                retryable=False,
                details="scanned_pdf",
            )
        finally:
            try:
                doc.close()
            except Exception:
                pass

    raise ResumeParseError(
        message="Only PDF and DOCX files are supported.",
        status_code=400,
        retryable=False,
        details="unsupported_extension",
    )


def extract_text_from_pdf(filepath: str) -> str:
    """Legacy helper returning extracted normalized PDF text or empty string on error."""
    try:
        return extract_resume_text_detailed(filepath, ext="pdf")["text"]
    except Exception:
        return ""


def extract_text_from_docx(filepath: str) -> str:
    """Legacy helper returning extracted normalized DOCX text or empty string on error."""
    try:
        return extract_resume_text_detailed(filepath, ext="docx")["text"]
    except Exception:
        return ""


def compute_text_hash(text: str) -> str:
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()


def _is_poisoned_or_failed_cache(structured_data: Any, ats_score: Any) -> bool:
    if not isinstance(structured_data, dict):
        return True
    if structured_data.get("_parse_status") == "failed":
        return True
    if (
        structured_data.get("full_name") == "Candidate"
        and structured_data.get("skills") == ["Software Engineering", "Algorithms"]
        and ats_score == 70
    ):
        return True
    return False


def get_cached_resume(text_hash: str) -> Optional[Dict[str, Any]]:
    try:
        from services.cache_service import cache_manager
        fast_cached = cache_manager.get(f"resume:{text_hash}")
        if fast_cached and not _is_poisoned_or_failed_cache(
            fast_cached.get("structured_data"), fast_cached.get("ats_score")
        ):
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
                try:
                    s_data = json.loads(s_data)
                except Exception:
                    s_data = {}

            m_info = row.get("missing_info")
            if isinstance(m_info, str):
                try:
                    m_info = json.loads(m_info)
                except Exception:
                    m_info = []

            ats_val = row.get("ats_score", 70)
            if _is_poisoned_or_failed_cache(s_data, ats_val):
                return None

            result = {
                "id": row.get("id"),
                "raw_text": row.get("raw_text"),
                "structured_data": s_data or {},
                "ats_score": ats_val,
                "missing_info": m_info or [],
            }
            try:
                from services.cache_service import cache_manager
                cache_manager.set(f"resume:{text_hash}", result, ttl=86400)
            except Exception:
                pass
            return result
    except Exception as e:
        logger.warning("Get cached resume notice: %s", type(e).__name__)
    return None


def save_cached_resume(
    text_hash: str,
    raw_text: str,
    structured_data: Dict[str, Any],
    ats_score: Optional[int],
    missing_info: List[str],
    user_id: Optional[str] = None,
) -> bool:
    """
    Idempotently persists validated resume parsing results to `parsed_resumes` while matching exact column types:
    - structured_data: JSONB (list/dict) / SQLite JSON text
    - missing_info: JSONB / SQLite JSON text
    - parsed_json: TEXT
    - uploaded_at: TEXT
    - created_at: TIMESTAMPTZ / ISO UTC string
    Returns True if DB persistence succeeded (or in SQLite local mode), False otherwise.
    """
    supabase = get_supabase()
    res_id = f"res_{text_hash[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    is_sqlite = getattr(supabase, "_real_client", None) is None
    structured_obj = structured_data if isinstance(structured_data, dict) else {}
    missing_list = missing_info if isinstance(missing_info, list) else []

    record: Dict[str, Any] = {
        "id": res_id,
        "hash": text_hash,
        "raw_text": raw_text,
        "parsed_json": json.dumps(structured_obj),
        "structured_data": json.dumps(structured_obj) if is_sqlite else structured_obj,
        "ats_score": ats_score,
        "missing_info": json.dumps(missing_list) if is_sqlite else missing_list,
        "uploaded_at": now_iso,
        "created_at": now_iso,
    }
    if user_id:
        record["user_id"] = str(user_id)

    try:
        supabase.table("parsed_resumes").upsert(record).execute()
    except Exception as exc:
        logger.warning("Save resume persistence failed: %s", type(exc).__name__)
        return False

    try:
        from services.cache_service import cache_manager
        cache_data = {
            "id": res_id,
            "raw_text": raw_text,
            "structured_data": structured_obj,
            "ats_score": ats_score,
            "missing_info": missing_list,
        }
        cache_manager.set(f"resume:{text_hash}", cache_data, ttl=86400)
    except Exception:
        pass
    return True


def _strip_json_fences(content: str) -> str:
    txt = (content or "").strip()
    if txt.startswith("```"):
        lines = txt.split("\n")
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            txt = "\n".join(lines[1:-1]).strip()
        elif len(lines) >= 2:
            # Fence header with truncated closing or trailing backticks
            body = "\n".join(lines[1:]).strip()
            txt = body[:-3].strip() if body.endswith("```") else body
        else:
            txt = txt.strip("`").strip()
    # Recover leading/trailing prose around a complete JSON object
    if txt and not txt.startswith("{"):
        first = txt.find("{")
        last = txt.rfind("}")
        if first != -1 and last > first:
            txt = txt[first : last + 1]
    return txt


def _clean_str(val: Any) -> str:
    return val.strip() if isinstance(val, str) else ("" if val is None else str(val).strip())


def _clean_str_list(val: Any) -> List[str]:
    if not isinstance(val, list):
        return []
    out: List[str] = []
    seen = set()
    for item in val:
        s = item.strip() if isinstance(item, str) else (str(item).strip() if item is not None else "")
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def _clean_dict_list(val: Any, allowed_keys: tuple) -> List[Dict[str, Any]]:
    if not isinstance(val, list):
        return []
    cleaned: List[Dict[str, Any]] = []
    for entry in val:
        if isinstance(entry, dict):
            item: Dict[str, Any] = {}
            for k in allowed_keys:
                v = entry.get(k)
                if k in ("tech_stack", "key_achievements"):
                    item[k] = _clean_str_list(v)
                else:
                    item[k] = _clean_str(v)
            if any(bool(v) for v in item.values()):
                cleaned.append(item)
    return cleaned


def _validate_parsed_resume(parsed: object) -> dict:
    """
    Validates Gemini JSON strictly against PrepFly's resume contract without fabricating missing details.
    Preserves all expected keys (including certifications and achievements).
    """
    if not isinstance(parsed, dict):
        raise ValueError("Parsed output must be a JSON object")
    if "skills" not in parsed or not isinstance(parsed.get("skills"), list):
        raise ValueError("Missing or non-list 'skills' field in parsed resume JSON")

    skills = _clean_str_list(parsed.get("skills"))
    raw_ats = parsed.get("ats_score", 70)
    if raw_ats is None:
        ats_score = None
    elif isinstance(raw_ats, bool) or not isinstance(raw_ats, (int, float)):
        try:
            ats_score = int(float(str(raw_ats)))
        except Exception:
            raise ValueError("Invalid 'ats_score' field in parsed resume JSON")
        ats_score = max(0, min(100, ats_score))
    else:
        ats_score = max(0, min(100, int(raw_ats)))

    return {
        "full_name": _clean_str(parsed.get("full_name")),
        "email": _clean_str(parsed.get("email")),
        "phone": _clean_str(parsed.get("phone")),
        "skills": skills,
        "projects": _clean_dict_list(parsed.get("projects"), ("title", "tech_stack", "description")),
        "experience": _clean_dict_list(parsed.get("experience"), ("role", "company", "duration", "key_achievements")),
        "education": _clean_dict_list(parsed.get("education"), ("degree", "institution", "year")),
        "certifications": _clean_str_list(parsed.get("certifications")),
        "achievements": _clean_str_list(parsed.get("achievements")),
        "ats_score": ats_score,
        "missing_info": _clean_str_list(parsed.get("missing_info")),
    }


def _is_transient_gemini_error(err: Exception) -> bool:
    from services.ai_service import is_transient_gemini_error
    return is_transient_gemini_error(err)


def parse_resume_content(
    raw_text: str,
    chat_model: Any,
    user_id: Optional[str] = None,
    require_persistence: bool = False,
    fallback_client_factory: Optional[Callable[[str, str], Any]] = None,
) -> Dict[str, Any]:
    if not raw_text or not raw_text.strip():
        return {
            "structured_data": {},
            "ats_score": 50,
            "missing_info": ["Complete Resume Content"],
        }

    normalized_text = normalize_resume_text(raw_text)
    text_hash = compute_text_hash(normalized_text)
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

    # Single-flight deduplication across concurrent retries for identical resume hash
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
        flight_entry["event"].wait(timeout=TOTAL_BUDGET_SECONDS + 2.0)
        if flight_entry["result"] is not None:
            return dict(flight_entry["result"])
        if flight_entry["error"] is not None:
            raise flight_entry["error"]

    try:
        parsed_result = _execute_parse_resume_content(
            normalized_text,
            text_hash,
            chat_model,
            user_id=user_id,
            require_persistence=require_persistence,
            fallback_client_factory=fallback_client_factory,
        )
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


def _extract_gemini_api_key(chat_model: Any) -> str:
    """Safely extracts raw Gemini API key from chat_model or environment without logging it."""
    raw_attr = getattr(chat_model, "google_api_key", None)
    if raw_attr is not None:
        if hasattr(raw_attr, "get_secret_value"):
            try:
                val = raw_attr.get_secret_value()
                if isinstance(val, str) and val.strip():
                    return val.strip()
            except Exception:
                pass
        elif isinstance(raw_attr, str) and raw_attr.strip():
            return raw_attr.strip()
    for env_name in ("GEMINI_API_KEY", "GEMINI_INTERVIEW_KEY", "GEMINI_REPORT_KEY", "BACKUP_GEMINI_API_KEY"):
        val = (os.getenv(env_name) or "").strip()
        if val:
            return val
    return ""


def _bind_resume_runner(client: Any, timeout_s: float) -> Any:
    """Binds bounded timeout and structured JSON mode to real LangChain Gemini clients cleanly."""
    if isinstance(client, NonCallableMock) or not hasattr(client, "bind"):
        return client
    try:
        return client.bind(timeout=float(timeout_s), response_mime_type="application/json")
    except Exception:
        try:
            return client.bind(timeout=float(timeout_s))
        except Exception:
            return client


def _execute_parse_resume_content(
    raw_text: str,
    text_hash: str,
    chat_model: Any,
    user_id: Optional[str] = None,
    require_persistence: bool = False,
    fallback_client_factory: Optional[Callable[[str, str], Any]] = None,
) -> Dict[str, Any]:
    snippet = raw_text[:MAX_GEMINI_RESUME_CHARS]
    base_prompt = f"""Analyze the following resume text and extract ONLY facts explicitly present.
Do NOT invent or fabricate any missing personal information, companies, degrees, or skills.
Return ONLY valid JSON with no markdown formatting or backticks.

Resume Content:
{snippet}

Expected JSON Schema:
{{
  "full_name": "string",
  "email": "string",
  "phone": "string",
  "skills": ["string"],
  "projects": [{{"title": "string", "tech_stack": ["string"], "description": "string"}}],
  "experience": [{{"role": "string", "company": "string", "duration": "string", "key_achievements": ["string"]}}],
  "education": [{{"degree": "string", "institution": "string", "year": "string"}}],
  "certifications": ["string"],
  "achievements": ["string"],
  "ats_score": 75,
  "missing_info": ["string"]
}}"""

    from langchain_core.messages import HumanMessage
    from services.ai_service import (
        create_gemini_client,
        extract_retry_after_seconds,
        get_fallback_gemini_models,
        is_model_not_found_error,
        is_permanent_gemini_error,
        is_test_gemini_key,
        mark_gemini_model_unavailable,
    )

    model_used = getattr(chat_model, "model", None) or getattr(chat_model, "model_name", None) or "gemini"
    last_err: Optional[Exception] = None
    prompt_to_send = base_prompt
    started_at = time.monotonic()

    max_attempts = 3
    retry_count = 0
    saw_permanent_error = False

    def _finalize_success(parsed: Dict[str, Any], chosen_model: str, used_fallback: bool) -> Dict[str, Any]:
        ats_score = parsed.get("ats_score", 70)
        missing_info = parsed.get("missing_info", [])
        persisted = save_cached_resume(
            text_hash,
            raw_text,
            parsed,
            ats_score,
            missing_info,
            user_id=user_id,
        )
        if require_persistence and not persisted:
            raise ResumeParseError(
                message="Parsed resume could not be persisted cleanly. Please retry.",
                status_code=503,
                retryable=True,
                details="persistence_failed",
            )
        latency_ms = round((time.monotonic() - started_at) * 1000.0, 1)
        log_fn = logger.warning if used_fallback else logger.info
        log_fn(
            "Resume parse success: model=%s latency_ms=%s retry_count=%d fallback=%s hash=%s",
            chosen_model,
            latency_ms,
            retry_count,
            used_fallback,
            text_hash[:8],
        )
        return {
            "structured_data": parsed,
            "ats_score": ats_score,
            "missing_info": missing_info,
            "model_used": str(chosen_model),
            "latency_ms": latency_ms,
            "retry_count": retry_count,
            "persisted": persisted,
            "prompt_id": RESUME_PARSE_PROMPT_ID,
            "prompt_version": RESUME_PARSE_PROMPT_VERSION,
        }

    primary_runner = _bind_resume_runner(chat_model, PRIMARY_ATTEMPT_TIMEOUT_S)

    # Phase A: Bounded primary attempts with jittered exponential backoff + Retry-After respect
    for attempt in range(max_attempts):
        elapsed = time.monotonic() - started_at
        if attempt > 0 and elapsed >= PRIMARY_BUDGET_SECONDS:
            break
        retry_count = attempt
        attempt_timeout = PRIMARY_ATTEMPT_TIMEOUT_S if attempt == 0 else max(2.0, min(PRIMARY_ATTEMPT_TIMEOUT_S, PRIMARY_BUDGET_SECONDS - elapsed))
        attempt_runner = _bind_resume_runner(chat_model, attempt_timeout) if attempt > 0 else primary_runner
        try:
            with _GEMINI_PARSE_SEMAPHORE:
                response = attempt_runner.invoke([HumanMessage(content=prompt_to_send)])
            raw_content = getattr(response, "content", "") if response is not None else ""
            cleaned = _strip_json_fences(raw_content)
            parsed = _validate_parsed_resume(json.loads(cleaned))
            return _finalize_success(parsed, str(model_used), used_fallback=False)
        except ResumeParseError:
            raise
        except (json.JSONDecodeError, ValueError) as val_err:
            last_err = val_err
            logger.warning(
                "Resume parse JSON validation failed (phase=primary attempt=%d/%d model=%s error=%s)",
                attempt + 1,
                max_attempts,
                model_used,
                type(val_err).__name__,
            )
            prompt_to_send = (
                f"{base_prompt}\n\nPREVIOUS OUTPUT WAS INVALID OR INCOMPLETE JSON ({val_err}). "
                "Respond with ONLY a valid complete JSON object matching the schema."
            )
        except Exception as err:
            last_err = err
            err_kind = type(err).__name__
            logger.warning(
                "Resume parse Gemini call failed (phase=primary attempt=%d/%d model=%s elapsed_ms=%.1f error=%s): %s",
                attempt + 1,
                max_attempts,
                model_used,
                (time.monotonic() - started_at) * 1000.0,
                err_kind,
                str(err)[:160],
            )
            if is_permanent_gemini_error(err):
                saw_permanent_error = True
                break
            if is_model_not_found_error(err):
                mark_gemini_model_unavailable(str(model_used))
                break
            if _is_transient_gemini_error(err) and attempt < max_attempts - 1:
                remaining = PRIMARY_BUDGET_SECONDS - (time.monotonic() - started_at)
                if remaining <= 0.5:
                    break
                retry_after = extract_retry_after_seconds(err)
                backoff = (0.3 * (2 ** attempt)) + random.uniform(0.0, 0.2)
                sleep_s = min(max(retry_after or 0.0, backoff), 5.0, max(0.0, remaining - 0.1))
                if sleep_s > 0:
                    time.sleep(sleep_s)
                continue
            if not _is_transient_gemini_error(err):
                break

    # Phase B: Guaranteed fallback model rotation with dedicated remaining time budget
    live_api_key = _extract_gemini_api_key(chat_model)
    is_mock_client = isinstance(chat_model, NonCallableMock)
    allow_fallback = (fallback_client_factory is not None) or (
        not is_mock_client and not is_test_gemini_key(live_api_key)
    )
    if not saw_permanent_error and allow_fallback:
        discover_live = True
        fallback_candidates = get_fallback_gemini_models(
            live_api_key,
            exclude_model=str(model_used),
            include_discovery=discover_live,
        )
        fallback_deadline = max(
            started_at + TOTAL_BUDGET_SECONDS,
            time.monotonic() + FALLBACK_BUDGET_SECONDS,
        )
        for fb_idx, fallback_model in enumerate(fallback_candidates, start=1):
            if time.monotonic() >= fallback_deadline:
                break
            retry_count += 1
            fb_prompt = base_prompt
            try:
                fb_chat = (
                    fallback_client_factory(fallback_model, live_api_key)
                    if fallback_client_factory is not None
                    else create_gemini_client(
                        fallback_model,
                        live_api_key,
                        timeout_s=FALLBACK_TIMEOUT_SECONDS,
                        temperature=0.2,
                    )
                )
                fb_runner = _bind_resume_runner(fb_chat, FALLBACK_TIMEOUT_SECONDS)
                for fb_json_try in range(2):
                    with _GEMINI_PARSE_SEMAPHORE:
                        fb_resp = fb_runner.invoke([HumanMessage(content=fb_prompt)])
                    fb_raw = getattr(fb_resp, "content", "") if fb_resp is not None else ""
                    try:
                        fb_parsed = _validate_parsed_resume(json.loads(_strip_json_fences(fb_raw)))
                        return _finalize_success(fb_parsed, fallback_model, used_fallback=True)
                    except (json.JSONDecodeError, ValueError) as fb_val_err:
                        last_err = fb_val_err
                        if fb_json_try == 0:
                            fb_prompt = (
                                f"{base_prompt}\n\nPREVIOUS OUTPUT WAS INVALID OR INCOMPLETE JSON ({fb_val_err}). "
                                "Respond with ONLY a valid complete JSON object matching the schema."
                            )
                            continue
                        raise
            except ResumeParseError:
                raise
            except Exception as fb_err:
                last_err = fb_err
                if is_permanent_gemini_error(fb_err):
                    saw_permanent_error = True
                    logger.error(
                        "Resume parse fallback permanent error (fallback_idx=%d model=%s error=%s)",
                        fb_idx,
                        fallback_model,
                        type(fb_err).__name__,
                    )
                    break
                if is_model_not_found_error(fb_err):
                    mark_gemini_model_unavailable(fallback_model)
                logger.warning(
                    "Resume parse fallback model failed (fallback_idx=%d model=%s elapsed_ms=%.1f error=%s)",
                    fb_idx,
                    fallback_model,
                    (time.monotonic() - started_at) * 1000.0,
                    type(fb_err).__name__,
                )

    latency_ms = round((time.monotonic() - started_at) * 1000.0, 1)
    failure_reason = type(last_err).__name__ if last_err else "unknown_error"
    logger.error(
        "Resume parse failed loudly: model=%s latency_ms=%s retry_count=%d failure_reason=%s hash=%s",
        model_used,
        latency_ms,
        retry_count,
        failure_reason,
        text_hash[:8],
    )
    if saw_permanent_error:
        raise ResumeParseError(
            message="AI resume parsing service rejected the configuration/request. Please contact support or continue without a resume.",
            status_code=502,
            retryable=False,
            details=failure_reason,
        )
    status_code = (
        504
        if (last_err and ("504" in str(last_err) or "deadline" in str(last_err).lower() or "timed out" in str(last_err).lower()))
        else 503
    )
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
    text = normalize_resume_text(raw_text or "")
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
                "certifications": [],
                "achievements": [],
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

    structured = _validate_parsed_resume({
        "full_name": inferred_name,
        "email": email_m.group(0) if email_m else "",
        "phone": phone_m.group(0).strip() if phone_m else "",
        "skills": skills,
        "projects": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "ats_score": None,
        "missing_info": missing,
    })
    return {
        "structured_data": structured,
        "ats_score": None,
        "missing_info": missing,
        "model_used": "deterministic_fallback",
        "is_partial": True,
        "prompt_id": RESUME_PARSE_PROMPT_ID,
        "prompt_version": RESUME_PARSE_PROMPT_VERSION,
    }


def _update_job_stage(job_id: str, status: str, stage: str, progress: Optional[int] = None) -> None:
    with _RESUME_JOBS_LOCK:
        job = _RESUME_JOBS.get(job_id)
        if not job:
            return
        job["status"] = status
        job["stage"] = stage
        if progress is not None:
            job["progress"] = progress
        job["updated_at"] = datetime.now(timezone.utc).isoformat()


def _run_resume_job(job_id: str, raw_text: str, user_id: Any, org_id: Any, chat_model: Any, create_session: bool) -> None:
    started = time.monotonic()
    _update_job_stage(job_id, status="parsing", stage="parsing", progress=40)

    try:
        parse_result = parse_resume_content(raw_text, chat_model, user_id=user_id, require_persistence=True)
        _update_job_stage(job_id, status="validating", stage="validating", progress=70)

        structured = _validate_parsed_resume(parse_result.get("structured_data", {}))
        ats_score = parse_result.get("ats_score", 70)
        session_id = None
        display_name = None

        _update_job_stage(job_id, status="persisting", stage="persisting", progress=88)

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
                job["stage"] = "completed"
                job["progress"] = 100
                job["session_id"] = session_id
                job["display_name"] = display_name
                job["ats_score"] = ats_score
                job["structured_data"] = structured
                job["missing_info"] = parse_result.get("missing_info", [])
                job["model_used"] = parse_result.get("model_used")
                job["error"] = None
                job["latency_ms"] = round((time.monotonic() - started) * 1000.0, 1)
                job["updated_at"] = datetime.now(timezone.utc).isoformat()
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        fb = deterministic_parse_resume(raw_text)
        retryable = bool(getattr(exc, "retryable", True))
        terminal_status = "retryable_failed" if retryable else "permanently_failed"
        safe_err = str(getattr(exc, "message", None) or "Resume parsing failed temporarily. You can retry without re-uploading.")
        with _RESUME_JOBS_LOCK:
            job = _RESUME_JOBS.get(job_id)
            if job:
                job["status"] = terminal_status
                job["stage"] = terminal_status
                job["progress"] = 100
                job["error"] = safe_err
                job["retryable"] = retryable
                job["status_code"] = int(getattr(exc, "status_code", 503))
                job["fallback_available"] = True
                job["deterministic_fallback"] = fb["structured_data"]
                job["latency_ms"] = round((time.monotonic() - started) * 1000.0, 1)
                job["updated_at"] = datetime.now(timezone.utc).isoformat()


def _prune_expired_jobs_locked() -> None:
    """Evicts oldest / expired in-memory resume jobs to keep PII and RAM bounded."""
    now_mono = time.monotonic()
    expired_ids = [
        jid
        for jid, p in _RESUME_JOB_PAYLOADS.items()
        if (now_mono - p.get("created_mono", now_mono)) > RESUME_JOB_TTL_SECONDS
    ]
    for jid in expired_ids:
        job = _RESUME_JOBS.pop(jid, None)
        _RESUME_JOB_PAYLOADS.pop(jid, None)
        _RESUME_JOB_SECRETS.pop(jid, None)
        if job:
            key = (str(job.get("user_id") or "anon"), job.get("text_hash"))
            if _RESUME_JOB_BY_HASH.get(key) == jid:
                _RESUME_JOB_BY_HASH.pop(key, None)

    while len(_RESUME_JOBS) >= MAX_RESUME_JOBS_IN_MEM:
        oldest_id = next(iter(_RESUME_JOBS))
        job = _RESUME_JOBS.pop(oldest_id, None)
        _RESUME_JOB_PAYLOADS.pop(oldest_id, None)
        _RESUME_JOB_SECRETS.pop(oldest_id, None)
        if job:
            key = (str(job.get("user_id") or "anon"), job.get("text_hash"))
            if _RESUME_JOB_BY_HASH.get(key) == oldest_id:
                _RESUME_JOB_BY_HASH.pop(key, None)


def create_resume_parse_job(
    raw_text: str,
    chat_model: Any,
    user_id: Any = None,
    org_id: Any = None,
    create_session: bool = True,
    run_async: bool = True,
) -> dict:
    """
    Creates (or deduplicates by user_id + content hash) a background resume parsing job.
    Preserves normalized extracted text on the job payload so retries never require re-upload.
    For unauthenticated uploads, binds a random creator secret (`job_token`) to prevent public IDOR polling.
    """
    import secrets
    normalized = normalize_resume_text(raw_text or "")
    text_hash = compute_text_hash(normalized)
    dedupe_key = (str(user_id or "anon"), text_hash)

    with _RESUME_JOBS_LOCK:
        _prune_expired_jobs_locked()
        existing_id = _RESUME_JOB_BY_HASH.get(dedupe_key)
        if existing_id and existing_id in _RESUME_JOBS:
            existing_job = _RESUME_JOBS[existing_id]
            if existing_job["status"] in ("queued", "extracting", "parsing", "validating", "persisting", "completed"):
                copy_job = dict(existing_job)
                copy_job["deduplicated"] = True
                if not user_id and existing_id in _RESUME_JOB_SECRETS:
                    copy_job["job_token"] = _RESUME_JOB_SECRETS[existing_id]
                return copy_job

        job_id = f"rjob_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        job = {
            "job_id": job_id,
            "user_id": str(user_id) if user_id else None,
            "organization_id": org_id,
            "text_hash": text_hash,
            "text_length": len(normalized),
            "status": "queued",
            "stage": "queued",
            "progress": 10,
            "retryable": True,
            "deduplicated": False,
            "attempts": 1,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        anon_secret = secrets.token_urlsafe(24) if not user_id else None
        _RESUME_JOBS[job_id] = job
        _RESUME_JOB_BY_HASH[dedupe_key] = job_id
        _RESUME_JOB_PAYLOADS[job_id] = {
            "raw_text": normalized,
            "user_id": user_id,
            "org_id": org_id,
            "create_session": create_session,
            "created_mono": time.monotonic(),
        }
        if anon_secret:
            _RESUME_JOB_SECRETS[job_id] = anon_secret

    if run_async:
        _RESUME_JOB_EXECUTOR.submit(_run_resume_job, job_id, normalized, user_id, org_id, chat_model, create_session)
    else:
        _run_resume_job(job_id, normalized, user_id, org_id, chat_model, create_session)

    with _RESUME_JOBS_LOCK:
        snap = dict(_RESUME_JOBS[job_id])
        if not user_id and job_id in _RESUME_JOB_SECRETS:
            snap["job_token"] = _RESUME_JOB_SECRETS[job_id]
        return snap


def verify_resume_job_token(job_id: str, supplied_token: Optional[str]) -> bool:
    """Constant-time validation of the anonymous job access token."""
    import hmac
    with _RESUME_JOBS_LOCK:
        expected = _RESUME_JOB_SECRETS.get(job_id)
    if not expected or not supplied_token:
        return False
    return hmac.compare_digest(str(supplied_token).strip(), expected)


def retry_resume_parse_job(
    job_id: str,
    chat_model: Any,
    run_async: bool = True,
    idempotency_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Re-queues an existing failed resume job idempotently without requiring file re-upload."""
    with _RESUME_JOBS_LOCK:
        job = _RESUME_JOBS.get(job_id)
        payload = _RESUME_JOB_PAYLOADS.get(job_id)
        if not job or not payload:
            return None
        if idempotency_key and (job_id, idempotency_key) in _RESUME_JOB_RETRY_KEYS:
            copy_job = dict(job)
            copy_job["deduplicated"] = True
            return copy_job
        if job["status"] in ("queued", "extracting", "parsing", "validating", "persisting", "completed"):
            copy_job = dict(job)
            copy_job["deduplicated"] = True
            return copy_job
        if not job.get("retryable", True):
            return dict(job)

        job["status"] = "queued"
        job["stage"] = "queued"
        job["progress"] = 15
        job["error"] = None
        job["attempts"] = int(job.get("attempts", 1)) + 1
        job["deduplicated"] = False
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        if idempotency_key:
            _RESUME_JOB_RETRY_KEYS[(job_id, idempotency_key)] = job["updated_at"]
        raw_text = payload["raw_text"]
        user_id = payload["user_id"]
        org_id = payload["org_id"]
        create_session = payload["create_session"]
        snapshot = dict(job)

    if run_async:
        _RESUME_JOB_EXECUTOR.submit(_run_resume_job, job_id, raw_text, user_id, org_id, chat_model, create_session)
    else:
        _run_resume_job(job_id, raw_text, user_id, org_id, chat_model, create_session)

    return snapshot


def get_resume_parse_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _RESUME_JOBS_LOCK:
        _prune_expired_jobs_locked()
        job = _RESUME_JOBS.get(job_id)
        return dict(job) if job else None


def clear_resume_jobs_for_tests() -> None:
    with _RESUME_JOBS_LOCK:
        _RESUME_JOBS.clear()
        _RESUME_JOB_BY_HASH.clear()
        _RESUME_JOB_PAYLOADS.clear()
        _RESUME_JOB_SECRETS.clear()
        _RESUME_JOB_RETRY_KEYS.clear()
