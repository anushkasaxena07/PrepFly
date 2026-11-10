import os
import hashlib
import json
import random
import time
import logging
import docx
from datetime import datetime

logger = logging.getLogger(__name__)

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
    s = str(err).lower()
    return any(tok in s for tok in ("503", "504", "429", "unavailable", "deadline", "timed out", "timeout", "resource exhausted"))


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

    model_used = getattr(chat_model, "model", None) or getattr(chat_model, "model_name", None) or "gemini"
    last_err = None
    prompt_to_send = base_prompt

    # Up to 3 attempts with exponential backoff + jitter on transient 503/504,
    # and validation-error feedback on invalid JSON.
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = chat_model.invoke([HumanMessage(content=prompt_to_send)])
            raw_content = getattr(response, "content", "") if response is not None else ""
            cleaned = _strip_json_fences(raw_content)
            parsed = _validate_parsed_resume(json.loads(cleaned))

            ats_score = parsed.get("ats_score", 70)
            missing_info = parsed.get("missing_info", [])
            save_cached_resume(text_hash, raw_text, parsed, ats_score, missing_info)
            return {
                "structured_data": parsed,
                "ats_score": ats_score,
                "missing_info": missing_info,
                "model_used": str(model_used),
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
            if _is_transient_gemini_error(err) and attempt < max_attempts - 1:
                sleep_s = (0.4 * (2 ** attempt)) + random.uniform(0.0, 0.25)
                time.sleep(sleep_s)
                continue
            if not _is_transient_gemini_error(err):
                break

    # Explicit fallback model attempt only for real live Gemini clients (never for unit-test mocks or test keys)
    from unittest.mock import NonCallableMock
    live_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_INTERVIEW_KEY") or ""
    is_mock_client = isinstance(chat_model, NonCallableMock)
    is_test_key = not live_api_key or live_api_key.startswith("test-") or "dummy" in live_api_key.lower()
    if not is_mock_client and not is_test_key and os.getenv("ENVIRONMENT") != "test":
        for fallback_model in ("gemini-2.0-flash", "gemini-flash-latest"):
            if fallback_model == str(model_used):
                continue
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                fb_chat = ChatGoogleGenerativeAI(
                    api_key=live_api_key,
                    model=fallback_model,
                    temperature=0.3,
                    max_retries=1,
                    timeout=25,
                )
                fb_resp = fb_chat.invoke([HumanMessage(content=base_prompt)])
                fb_raw = getattr(fb_resp, "content", "") if fb_resp is not None else ""
                fb_parsed = _validate_parsed_resume(json.loads(_strip_json_fences(fb_raw)))
                ats_score = fb_parsed.get("ats_score", 70)
                missing_info = fb_parsed.get("missing_info", [])
                save_cached_resume(text_hash, raw_text, fb_parsed, ats_score, missing_info)
                logger.warning("Resume parse succeeded on explicit fallback model '%s' after primary '%s' failed.", fallback_model, model_used)
                return {
                    "structured_data": fb_parsed,
                    "ats_score": ats_score,
                    "missing_info": missing_info,
                    "model_used": fallback_model,
                    "prompt_id": RESUME_PARSE_PROMPT_ID,
                    "prompt_version": RESUME_PARSE_PROMPT_VERSION,
                }
            except Exception as fb_err:
                last_err = fb_err
                logger.warning("Resume parse fallback model '%s' failed: %s", fallback_model, fb_err)

    status_code = 504 if (last_err and ("504" in str(last_err) or "deadline" in str(last_err).lower() or "timed out" in str(last_err).lower())) else 503
    raise ResumeParseError(
        message="AI resume parsing failed after retries. Please retry uploading your resume or continue without a resume.",
        status_code=status_code,
        retryable=True,
        details=type(last_err).__name__ if last_err else "unknown_error",
    )
