"""
Candidate Preparation Profile Service for PrepFly Intelligence.
Manages candidate goals, target companies, roles, daily availability, and study schedules.
Supports flexible signatures with optional Supabase client injection and automated fallback.
"""

from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime, timezone, timedelta
from local_supabase import get_supabase_client

class CandidateProfileService:
    """Handles CRUD and lifecycle for candidate preparation profiles."""

    SUPPORTED_ROLES = [
        "Software Development Engineer",
        "Software Development Engineer (General)",
        "Frontend Developer",
        "Frontend Engineer",
        "Backend Developer",
        "Backend Engineer",
        "Full Stack Developer",
        "Full Stack Engineer",
        "AI/ML Engineer",
        "Data Analyst"
    ]

    SUPPORTED_EXPERIENCE = [
        "Fresher",
        "1-3 Years",
        "3-5 Years",
        "5+ Years",
        "Mid-Level (2-5 years)",
        "Senior (5+ years)"
    ]

    @classmethod
    def initialize_or_update_profile(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Creates or updates a candidate preparation profile with strict boundary checks."""
        # Signature resolution:
        # Style A: (supabase_client, user_id, data_dict)
        # Style B: (user_id, data_dict)
        # Style C: (user_id=..., target_role=..., ...)
        if len(args) == 3:
            if isinstance(args[0], str) and isinstance(args[1], dict):
                user_id, data, supabase_client = args
            else:
                supabase_client, user_id, data = args
        elif len(args) == 2:
            if isinstance(args[0], str):
                user_id, data = args
                supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            else:
                supabase_client, user_id = args
                data = kwargs
        elif len(args) == 1:
            if isinstance(args[0], str):
                user_id = args[0]
                supabase_client = kwargs.pop("supabase_client", None) or get_supabase_client()
                data = kwargs
            else:
                supabase_client = args[0]
                user_id = kwargs.pop("user_id", "")
                data = kwargs
        else:
            user_id = kwargs.pop("user_id", "")
            supabase_client = kwargs.pop("supabase_client", None) or get_supabase_client()
            data = kwargs.pop("data", kwargs)

        if not user_id:
            raise ValueError("user_id is required")

        now_iso = datetime.now(timezone.utc).isoformat()
        
        target_role = (data.get("target_role") or "Software Development Engineer (General)").strip()
        experience_level = (data.get("experience_level") or "Fresher").strip()
        target_company = (data.get("target_company") or "General Tech").strip()
        target_interview_date = data.get("target_interview_date") or data.get("target_date")
        
        # Bounded duration & daily study hours
        raw_days = data.get("days_planned") or data.get("total_days") or data.get("preparation_duration_days") or data.get("duration_days")
        if raw_days:
            duration_days = max(1, min(365, int(raw_days)))
        elif target_interview_date:
            try:
                t_date = datetime.strptime(target_interview_date, "%Y-%m-%d").date()
                diff_d = (t_date - datetime.now(timezone.utc).date()).days
                duration_days = max(1, min(365, diff_d)) if diff_d > 0 else 30
            except Exception:
                duration_days = 30
        else:
            duration_days = 30

        if not target_interview_date:
            target_interview_date = (datetime.now(timezone.utc) + timedelta(days=duration_days)).strftime("%Y-%m-%d")
        
        # Support daily_minutes or daily_study_hours
        if "daily_minutes" in data:
            daily_hours = max(0.5, min(12.0, float(data["daily_minutes"]) / 60.0))
        elif "daily_pace" in data:
            daily_hours = max(0.5, min(12.0, float(data["daily_pace"]) / 60.0))
        else:
            daily_hours = max(0.5, min(12.0, float(data.get("daily_study_hours", 1.0))))
        
        preferred_days = data.get("preferred_study_days") or data.get("study_days") or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        if isinstance(preferred_days, list):
            preferred_days_json = json.dumps(preferred_days)
        else:
            preferred_days_json = str(preferred_days)

        current_skills = data.get("current_skills") or []
        current_skills_json = json.dumps(current_skills) if isinstance(current_skills, list) else str(current_skills)

        preferred_language = (data.get("preferred_language") or "python").lower().strip()
        
        preparation_goals = data.get("preparation_goals") or data.get("focus_areas") or ["DSA", "System Design", "Core CS", "Interview Skills"]
        goals_json = json.dumps(preparation_goals) if isinstance(preparation_goals, list) else str(preparation_goals)

        strengths = data.get("strengths") or []
        strengths_json = json.dumps(strengths) if isinstance(strengths, list) else str(strengths)

        growth_areas = data.get("growth_areas") or []
        growth_json = json.dumps(growth_areas) if isinstance(growth_areas, list) else str(growth_areas)

        status = str(data.get("status", "ACTIVE")).upper()

        # Check existing profile
        existing_res = supabase_client.table("candidate_profiles").select("*").eq("user_id", user_id).execute()
        existing = existing_res.data[0] if (existing_res and existing_res.data) else None

        profile_payload = {
            "user_id": user_id,
            "target_company": target_company,
            "target_role": target_role,
            "experience_level": experience_level,
            "target_interview_date": target_interview_date,
            "preparation_duration_days": duration_days,
            "daily_study_hours": round(daily_hours, 2),
            "preferred_study_days": preferred_days_json,
            "current_skills": current_skills_json,
            "preferred_language": preferred_language,
            "preparation_goals": goals_json,
            "strengths": strengths_json,
            "growth_areas": growth_json,
            "status": status,
            "updated_at": now_iso
        }

        if existing:
            profile_payload["id"] = existing["id"]
            supabase_client.table("candidate_profiles").update(profile_payload).eq("id", existing["id"]).execute()
        else:
            profile_payload["id"] = str(uuid.uuid4())
            profile_payload["created_at"] = now_iso
            supabase_client.table("candidate_profiles").insert(profile_payload).execute()

        return cls.get_profile(user_id, supabase_client=supabase_client)

    # Alias for convenience
    create_or_update_profile = initialize_or_update_profile

    @classmethod
    def get_profile(cls, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetches and parses a candidate profile."""
        if len(args) == 2:
            if isinstance(args[0], str):
                user_id, supabase_client = args
            else:
                supabase_client, user_id = args
        elif len(args) == 1:
            if isinstance(args[0], str):
                user_id = args[0]
                supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            else:
                supabase_client = args[0]
                user_id = kwargs.get("user_id", "")
        else:
            user_id = kwargs.get("user_id", "")
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()

        if not user_id:
            return None

        res = supabase_client.table("candidate_profiles").select("*").eq("user_id", user_id).execute()
        if not res or not res.data:
            return None
        
        raw = res.data[0]
        # Parse JSON fields safely
        def _parse(val, default):
            if not val:
                return default
            if isinstance(val, (list, dict)):
                return val
            try:
                return json.loads(val)
            except Exception:
                return default

        daily_hours = float(raw.get("daily_study_hours", 2.0))
        return {
            "id": raw["id"],
            "user_id": raw["user_id"],
            "target_company": raw.get("target_company") or "General Tech",
            "target_role": raw.get("target_role") or "Software Development Engineer (General)",
            "experience_level": raw.get("experience_level") or "Fresher",
            "target_interview_date": raw.get("target_interview_date"),
            "target_date": raw.get("target_interview_date"),
            "preparation_duration_days": raw.get("preparation_duration_days", 30),
            "total_days": raw.get("preparation_duration_days", 30),
            "days_planned": raw.get("preparation_duration_days", 30),
            "daily_study_hours": daily_hours,
            "daily_minutes": int(round(daily_hours * 60)),
            "preferred_study_days": _parse(raw.get("preferred_study_days"), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]),
            "study_days": _parse(raw.get("preferred_study_days"), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]),
            "current_skills": _parse(raw.get("current_skills"), []),
            "preferred_language": raw.get("preferred_language", "python"),
            "preparation_goals": _parse(raw.get("preparation_goals"), ["DSA", "System Design", "Core CS"]),
            "focus_areas": _parse(raw.get("preparation_goals"), ["DSA", "System Design", "Core CS"]),
            "strengths": _parse(raw.get("strengths"), []),
            "growth_areas": _parse(raw.get("growth_areas"), []),
            "status": str(raw.get("status", "ACTIVE")).upper(),
            "created_at": raw.get("created_at"),
            "updated_at": raw.get("updated_at")
        }

    @classmethod
    def update_status(cls, *args, **kwargs) -> Any:
        """Updates preparation lifecycle status ('ACTIVE', 'PAUSED', 'COMPLETED')."""
        if len(args) == 3:
            supabase_client, user_id, new_status = args
        elif len(args) == 2:
            if isinstance(args[0], str):
                user_id, new_status = args
                supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            else:
                supabase_client, user_id = args
                new_status = kwargs.get("new_status") or kwargs.get("status")
        else:
            user_id = kwargs.get("user_id")
            new_status = kwargs.get("new_status") or kwargs.get("status")
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()

        norm_status = str(new_status).upper()
        if norm_status not in ("ACTIVE", "PAUSED", "COMPLETED", "EXTENDED"):
            raise ValueError(f"Invalid status: {new_status}")

        now_iso = datetime.now(timezone.utc).isoformat()
        supabase_client.table("candidate_profiles").update({
            "status": norm_status,
            "updated_at": now_iso
        }).eq("user_id", user_id).execute()
        return cls.get_profile(user_id, supabase_client=supabase_client)

    update_profile_status = update_status
