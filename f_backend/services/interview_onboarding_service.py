"""
Interview Onboarding Service for PrepFly Adaptive AI Interview Mentor.
Orchestrates conversational onboarding one question at a time, skipping pre-known
profile/resume/job fields, clearly separating candidate actual experience from job-required
experience, and persisting active goals to interview_goals.
"""

from typing import Dict, List, Optional, Any
import json
import uuid
from datetime import datetime, timezone, date

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService
from services.job_requirement_extractor import JobRequirementExtractor


ONBOARDING_FIELD_SEQUENCE = [
    {
        "field": "target_role",
        "question_text": "What specific engineering or technical role are you targeting for your upcoming interview?",
        "field_type": "choice",
        "options": [
            "Software Development Engineer (General)",
            "AI / ML Engineer",
            "Backend Engineer",
            "Frontend Engineer",
            "Full Stack Engineer",
            "Data Science & Analytics",
            "Data Engineer",
            "DevOps & Cloud Engineer",
            "Custom Role"
        ],
        "default": "Software Development Engineer (General)"
    },
    {
        "field": "target_company",
        "question_text": "Which company or organization are you preparing to interview with?",
        "field_type": "text",
        "default": "Tech Firm"
    },
    {
        "field": "job_description_text",
        "question_text": "Paste the target Job Description (JD) text, or enter 'skip' if you don't have one right now:",
        "field_type": "text_multiline",
        "default": ""
    },
    {
        "field": "required_experience_years",
        "question_text": "How many years of experience does this target job position require (e.g. 0 for new grad, 3 for mid-level, 5 for senior)?",
        "field_type": "number",
        "default": 2.0
    },
    {
        "field": "candidate_actual_experience_years",
        "question_text": "How many actual years of professional engineering experience do you currently have?",
        "field_type": "number",
        "default": 1.0
    },
    {
        "field": "resume_text",
        "question_text": "Paste a summary of your recent technical experience / resume, or enter 'skip':",
        "field_type": "text_multiline",
        "default": ""
    },
    {
        "field": "target_interview_date",
        "question_text": "When is your upcoming interview scheduled (YYYY-MM-DD), or in approximately how many days?",
        "field_type": "date_or_days",
        "default": "30"
    },
    {
        "field": "daily_minutes",
        "question_text": "How many minutes can you realistically commit to focused daily interview preparation?",
        "field_type": "choice",
        "options": ["30", "45", "60", "90", "120"],
        "default": 60
    },
    {
        "field": "self_reported_skills",
        "question_text": "What core technical skills do you feel confident claiming today? (Comma-separated or list):",
        "field_type": "skills_list",
        "default": []
    },
    {
        "field": "previous_attempts",
        "question_text": "How many prior technical interview attempts have you made for this or similar roles?",
        "field_type": "number",
        "default": 0
    },
    {
        "field": "learning_preference",
        "question_text": "What is your primary learning preference for mastering complex topics?",
        "field_type": "choice",
        "options": ["hands-on", "reading", "walkthrough"],
        "default": "hands-on"
    }
]


class InterviewOnboardingService:
    """Conversational onboarding controller for candidate interview context."""

    @classmethod
    def get_prefilled_candidate_data(cls, user_id: str, supabase_client: Any = None) -> Dict[str, Any]:
        """
        Inspects existing profile, resumes, and job targets to pre-populate known fields,
        allowing onboarding to skip redundant questions.
        """
        supabase = supabase_client or get_supabase_client()
        prefilled: Dict[str, Any] = {}

        # 1. Candidate Profile
        try:
            p_res = supabase.table("candidate_profiles").select("*").eq("user_id", user_id).execute()
            if p_res and p_res.data:
                prof = p_res.data[0]
                if prof.get("target_role"):
                    prefilled["target_role"] = prof["target_role"]
                if prof.get("target_company"):
                    prefilled["target_company"] = prof["target_company"]
                if prof.get("daily_minutes"):
                    prefilled["daily_minutes"] = int(prof["daily_minutes"])
                elif prof.get("daily_study_hours"):
                    prefilled["daily_minutes"] = int(float(prof["daily_study_hours"]) * 60)
                if prof.get("target_date"):
                    prefilled["target_interview_date"] = prof["target_date"]
                if prof.get("experience_level"):
                    exp_str = str(prof["experience_level"]).lower()
                    if "entry" in exp_str or "fresher" in exp_str:
                        prefilled["candidate_actual_experience_years"] = 0.0
                    elif "mid" in exp_str:
                        prefilled["candidate_actual_experience_years"] = 3.0
                    elif "senior" in exp_str:
                        prefilled["candidate_actual_experience_years"] = 6.0
        except Exception:
            pass

        # 2. Resumes
        try:
            r_res = supabase.table("resumes").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if r_res and r_res.data:
                resume = r_res.data[0]
                if resume.get("parsed_text") or resume.get("raw_text"):
                    prefilled["resume_text"] = resume.get("parsed_text") or resume.get("raw_text")
        except Exception:
            pass

        # 3. Job Profiles / Target JD
        try:
            j_res = supabase.table("job_profiles").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if j_res and j_res.data:
                job = j_res.data[0]
                if job.get("job_title") and not prefilled.get("target_role"):
                    prefilled["target_role"] = job["job_title"]
                if job.get("company_name") and not prefilled.get("target_company"):
                    prefilled["target_company"] = job["company_name"]
                if job.get("raw_jd_text") or job.get("description"):
                    prefilled["job_description_text"] = job.get("raw_jd_text") or job.get("description")
                if job.get("min_years_experience") is not None:
                    prefilled["required_experience_years"] = float(job["min_years_experience"])
        except Exception:
            pass

        return prefilled

    @classmethod
    def start_or_resume_onboarding(
        cls,
        user_id: str,
        goal_id: Optional[str] = None,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """
        Starts a new conversational onboarding flow or resumes an in-progress draft.
        Skips anything already known from existing candidate records.
        """
        supabase = supabase_client or get_supabase_client()
        prefilled = cls.get_prefilled_candidate_data(user_id, supabase)

        # 1. Locate active draft or existing goal
        goal_record = None
        if goal_id:
            res = supabase.table("interview_goals").select("*").eq("id", goal_id).eq("user_id", user_id).execute()
            if res and res.data:
                goal_record = res.data[0]
        else:
            res = supabase.table("interview_goals").select("*").eq("user_id", user_id).eq("status", "draft").order("created_at", desc=True).limit(1).execute()
            if res and res.data:
                goal_record = res.data[0]

        now_iso = datetime.now(timezone.utc).isoformat()
        if not goal_record:
            goal_id = f"goal_{uuid.uuid4().hex[:12]}"
            goal_record = {
                "id": goal_id,
                "user_id": user_id,
                "target_company": prefilled.get("target_company"),
                "target_role": prefilled.get("target_role") or "Software Development Engineer (General)",
                "job_description_text": prefilled.get("job_description_text"),
                "required_experience_years": prefilled.get("required_experience_years", 0.0),
                "candidate_actual_experience_years": prefilled.get("candidate_actual_experience_years", 0.0),
                "resume_text": prefilled.get("resume_text"),
                "target_interview_date": prefilled.get("target_interview_date"),
                "days_horizon": 30,
                "daily_minutes": prefilled.get("daily_minutes", 60),
                "self_reported_skills": json.dumps(prefilled.get("self_reported_skills", [])),
                "previous_attempts": 0,
                "learning_preference": "hands-on",
                "status": "draft",
                "version": 1,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            supabase.table("interview_goals").insert(goal_record).execute()
        else:
            goal_id = goal_record["id"]

        return cls._determine_next_step(goal_record, prefilled)

    @classmethod
    def submit_onboarding_answer(
        cls,
        user_id: str,
        goal_id: str,
        field: str,
        value: Any,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """
        Receives candidate's response to the current question, updates interview_goals,
        and advances to the next unanswered question.
        """
        supabase = supabase_client or get_supabase_client()
        res = supabase.table("interview_goals").select("*").eq("id", goal_id).eq("user_id", user_id).execute()
        if not res or not res.data:
            raise ValueError(f"Interview goal {goal_id} not found for candidate.")

        goal = res.data[0]
        cleaned_value = cls._clean_field_value(field, value)

        update_payload: Dict[str, Any] = {
            field: cleaned_value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # If date or horizon field was submitted, sync both target_interview_date and days_horizon
        if field == "target_interview_date":
            days, target_date_str = cls._parse_date_or_horizon(cleaned_value)
            update_payload["days_horizon"] = days
            update_payload["target_interview_date"] = target_date_str

        supabase.table("interview_goals").update(update_payload).eq("id", goal_id).execute()
        goal.update(update_payload)

        prefilled = cls.get_prefilled_candidate_data(user_id, supabase)
        next_step = cls._determine_next_step(goal, prefilled)

        # If all fields completed, finalize goal status to 'active'
        if next_step.get("is_completed"):
            supabase.table("interview_goals").update({
                "status": "active",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", goal_id).execute()
            goal["status"] = "active"

            # Parse and cache JD requirements if text is provided
            jd_text = goal.get("job_description_text")
            if jd_text and len(jd_text.strip()) > 30 and jd_text.strip().lower() != "skip":
                try:
                    extractor = JobRequirementExtractor(supabase)
                    extractor.extract_and_persist_requirements(
                        job_id=goal_id,
                        user_id=user_id,
                        target_role=goal.get("target_role", "Software Development Engineer (General)"),
                        jd_text=jd_text
                    )
                except Exception:
                    pass

        return next_step

    @classmethod
    def _determine_next_step(cls, goal: Dict[str, Any], prefilled: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates remaining questions, skipping anything prefilled from candidate profile/resume/job target.
        """
        skipped_fields: List[str] = []
        next_question: Optional[Dict[str, Any]] = None

        completed_count = 0
        total_questions = len(ONBOARDING_FIELD_SEQUENCE)

        for q in ONBOARDING_FIELD_SEQUENCE:
            f = q["field"]
            current_val = goal.get(f)

            # Check if value is already filled with meaningful data
            is_filled = False
            if current_val is not None:
                if isinstance(current_val, str) and current_val.strip() and current_val != "[]":
                    is_filled = True
                elif isinstance(current_val, (int, float)):
                    # 0.0 or 0 can be a valid answer if explicitly set or prefilled
                    is_filled = True
                elif isinstance(current_val, list) and len(current_val) > 0:
                    is_filled = True

            if is_filled:
                completed_count += 1
                if f in prefilled and goal.get("status") == "draft":
                    skipped_fields.append(f)
            else:
                if next_question is None:
                    next_question = q

        is_completed = (next_question is None)

        return {
            "goal_id": goal["id"],
            "status": "active" if is_completed else "in_progress",
            "is_completed": is_completed,
            "current_question": next_question,
            "skipped_fields": skipped_fields,
            "progress": {
                "completed": completed_count,
                "total": total_questions,
                "percent": int((completed_count / total_questions) * 100)
            },
            "goal_snapshot": goal
        }

    @classmethod
    def _clean_field_value(cls, field: str, value: Any) -> Any:
        """Sanitizes and normalizes incoming answers."""
        if value is None:
            return None

        if field in ("required_experience_years", "candidate_actual_experience_years"):
            try:
                return max(0.0, float(value))
            except (ValueError, TypeError):
                return 0.0

        if field in ("daily_minutes", "previous_attempts", "days_horizon"):
            try:
                return max(0, int(value))
            except (ValueError, TypeError):
                return 0

        if field == "self_reported_skills":
            if isinstance(value, list):
                return json.dumps(value)
            elif isinstance(value, str):
                parts = [p.strip() for p in value.split(",") if p.strip()]
                return json.dumps(parts)
            return "[]"

        if field == "target_role":
            # Normalize role to canonical taxonomy where possible
            return str(value).strip()

        if field == "learning_preference":
            val_str = str(value).strip().lower()
            if "read" in val_str:
                return "reading"
            elif "video" in val_str or "walk" in val_str:
                return "walkthrough"
            return "hands-on"

        return str(value).strip()

    @classmethod
    def _parse_date_or_horizon(cls, val: Any) -> tuple[int, Optional[str]]:
        """Parses either a calendar date string (YYYY-MM-DD) or an integer days count."""
        val_str = str(val).strip()
        now_date = datetime.now(timezone.utc).date()

        # Try parsing as ISO date YYYY-MM-DD
        try:
            target_d = datetime.strptime(val_str, "%Y-%m-%d").date()
            diff = (target_d - now_date).days
            days = max(1, diff)
            return days, val_str
        except Exception:
            pass

        # Try parsing as integer days (e.g. "30", "14")
        try:
            days = max(1, int(val_str))
            target_d = now_date + (date.today() - date.today() + datetime.timedelta(days=days) if hasattr(datetime, "timedelta") else __import__("datetime").timedelta(days=days))
            return days, target_d.isoformat()
        except Exception:
            return 30, (now_date + __import__("datetime").timedelta(days=30)).isoformat()

