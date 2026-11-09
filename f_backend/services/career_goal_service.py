"""
CareerGoalService
=================
Manages student-selected career goals, allowing candidates to prepare for
multiple distinct roles (e.g. SDE and AI/ML Engineer) without cross-contaminating
their assessment sessions, readiness scores, or personalized PrepMaps.
"""

from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timezone
import logging

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, normalize_role_id

logger = logging.getLogger("prepfly.career_goals")


class CareerGoalService:
    """Orchestrates career goal creation, retrieval, updates, and role normalization."""

    SUPPORTED_ROLES = [
        {"role_id": "software_development_engineer", "label": "Software Engineer (SDE / SWE)", "category": "General Engineering"},
        {"role_id": "ai_ml_engineer", "label": "AI/ML Engineer", "category": "Artificial Intelligence"},
        {"role_id": "backend_developer", "label": "Backend Developer", "category": "Backend & Cloud"},
        {"role_id": "frontend_developer", "label": "Frontend Developer", "category": "Web & UI"},
        {"role_id": "full_stack_developer", "label": "Full Stack Developer", "category": "Full Stack"},
        {"role_id": "data_scientist", "label": "Data Scientist", "category": "Data & Analytics"},
        {"role_id": "data_engineer", "label": "Data Engineer", "category": "Data Infrastructure"},
        {"role_id": "devops_engineer", "label": "DevOps Engineer", "category": "Infrastructure & Cloud"},
    ]

    @classmethod
    def list_supported_roles(cls) -> List[Dict[str, str]]:
        """Returns the canonical catalog of supported career goals."""
        return cls.SUPPORTED_ROLES

    @classmethod
    def create_career_goal(
        cls,
        user_id: str,
        target_role: str,
        custom_role: Optional[str] = None,
        target_company: Optional[str] = None,
        job_description: Optional[str] = None,
        experience_level: str = "Fresher",
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Creates and persists a new career goal for a user.
        Normalizes role names into canonical role IDs.
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not target_role and not custom_role:
            raise ValueError("Either target_role or custom_role must be provided")

        client = supabase_client or get_supabase_client()
        canonical_role_id = normalize_role_id(target_role or custom_role)
        now_iso = datetime.now(timezone.utc).isoformat()
        goal_id = str(uuid.uuid4())

        record = {
            "id": goal_id,
            "user_id": user_id,
            "role_id": canonical_role_id,
            "custom_role": custom_role.strip() if custom_role else None,
            "target_company": target_company.strip() if target_company else None,
            "job_description": job_description.strip() if job_description else None,
            "experience_level": experience_level or "Fresher",
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso
        }

        try:
            client.table("career_goals").insert(record).execute()
        except Exception as e:
            logger.error(f"Failed to insert career_goal: {e}")
            raise

        return record

    @classmethod
    def get_career_goals_for_user(
        cls,
        user_id: str,
        status: Optional[str] = None,
        supabase_client=None
    ) -> List[Dict[str, Any]]:
        """Retrieves all career goals configured by a candidate."""
        if not user_id:
            return []

        client = supabase_client or get_supabase_client()
        try:
            query = client.table("career_goals").select("*").eq("user_id", user_id)
            if status:
                query = query.eq("status", status)
            res = query.order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.warning(f"Error listing career goals for user {user_id}: {e}")
            return []

    @classmethod
    def get_career_goal_by_id(
        cls,
        goal_id: str,
        user_id: Optional[str] = None,
        supabase_client=None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a specific career goal with ownership verification."""
        if not goal_id:
            return None

        client = supabase_client or get_supabase_client()
        try:
            query = client.table("career_goals").select("*").eq("id", goal_id)
            if user_id:
                query = query.eq("user_id", user_id)
            res = query.execute()
            if res and res.data:
                return res.data[0]
            return None
        except Exception as e:
            logger.warning(f"Error fetching career goal {goal_id}: {e}")
            return None

    @classmethod
    def update_career_goal(
        cls,
        goal_id: str,
        user_id: str,
        updates: Dict[str, Any],
        supabase_client=None
    ) -> Optional[Dict[str, Any]]:
        """Updates career goal parameters (e.g. JD, company, experience)."""
        if not goal_id or not user_id:
            return None

        client = supabase_client or get_supabase_client()
        allowed_fields = {"target_company", "job_description", "experience_level", "status", "custom_role"}
        clean_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        clean_updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            res = client.table("career_goals").update(clean_updates).eq("id", goal_id).eq("user_id", user_id).execute()
            if res and res.data:
                return res.data[0]
            return cls.get_career_goal_by_id(goal_id, user_id=user_id, supabase_client=client)
        except Exception as e:
            logger.error(f"Error updating career goal {goal_id}: {e}")
            return None

