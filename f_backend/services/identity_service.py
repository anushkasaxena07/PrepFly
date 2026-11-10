"""
Candidate Identity Resolution Service (Operating Rule R6)
Priority order:
  1. profile  (confirmed users table record)
  2. google   (Google OAuth / JWT user claims)
  3. resume   (parsed resume full_name / name)
  4. fallback ("Candidate", last resort; never overwrites a real name)
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_PLACEHOLDER_NAMES = {
    "", "candidate", "user", "anonymous", "guest", "null", "none", "undefined", "me", "student"
}


def is_valid_display_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.strip()
    return bool(cleaned) and cleaned.lower() not in _PLACEHOLDER_NAMES


def resolve_candidate_display_name(
    user_payload: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    parsed_resume: Optional[Any] = None,
    existing_name: Optional[str] = None,
    existing_source: Optional[str] = None,
    supabase_client: Any = None,
) -> Tuple[str, str]:
    """
    Returns (display_name, display_name_source) where source is one of:
    'profile', 'google', 'resume', 'fallback'.
    """
    # 1. Confirmed user profile in DB
    uid = user_id or (user_payload or {}).get("sub") or (user_payload or {}).get("user_id") or (user_payload or {}).get("id")
    if supabase_client is not None and uid:
        try:
            u_res = supabase_client.table("users").select("name").eq("id", str(uid)).limit(1).execute()
            if u_res and getattr(u_res, "data", None):
                db_name = u_res.data[0].get("name")
                if is_valid_display_name(db_name):
                    return db_name.strip(), "profile"
        except Exception as e:
            logger.debug("Profile lookup skipped during name resolution: %s", e)

    # Also check by email in user_payload if id lookup yielded nothing
    payload_email = (user_payload or {}).get("email")
    if not payload_email and isinstance((user_payload or {}).get("user_metadata"), dict):
        payload_email = user_payload["user_metadata"].get("email")
    if supabase_client is not None and payload_email:
        try:
            u_res = supabase_client.table("users").select("name").eq("email", str(payload_email)).limit(1).execute()
            if u_res and getattr(u_res, "data", None):
                db_name = u_res.data[0].get("name")
                if is_valid_display_name(db_name):
                    return db_name.strip(), "profile"
        except Exception as e:
            logger.debug("Profile email lookup skipped during name resolution: %s", e)

    # 2. Google / JWT account claims
    if isinstance(user_payload, dict):
        meta = user_payload.get("user_metadata") if isinstance(user_payload.get("user_metadata"), dict) else {}
        given_family = f"{user_payload.get('given_name', '')} {user_payload.get('family_name', '')}".strip()
        for cand in (
            user_payload.get("name"),
            user_payload.get("full_name"),
            meta.get("full_name"),
            meta.get("name"),
            given_family,
        ):
            if is_valid_display_name(cand):
                return str(cand).strip(), "google"

    # 3. Parsed resume name
    resume_dict: Dict[str, Any] = {}
    if isinstance(parsed_resume, str) and parsed_resume.strip():
        try:
            loaded = json.loads(parsed_resume)
            if isinstance(loaded, dict):
                resume_dict = loaded
        except Exception:
            pass
    elif isinstance(parsed_resume, dict):
        resume_dict = parsed_resume

    for key in ("full_name", "name", "candidate_name"):
        cand = resume_dict.get(key)
        if is_valid_display_name(cand):
            return str(cand).strip(), "resume"

    # Never overwrite an already resolved non-placeholder name with "Candidate"
    if is_valid_display_name(existing_name):
        src = existing_source if existing_source in ("profile", "google", "resume") else "profile"
        return str(existing_name).strip(), src

    # 4. Last resort fallback
    return "Candidate", "fallback"

