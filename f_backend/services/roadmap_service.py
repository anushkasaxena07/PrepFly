"""
Personalized Roadmap Generation Engine for PrepFly Intelligence.
Hybrid deterministic scheduling engine that builds prioritized, dependency-respecting
preparation roadmaps bounded by daily candidate availability and target interview dates.
"""

from typing import Dict, List, Optional, Any, Set
import json
import uuid
import math
from datetime import datetime, timedelta, timezone

from services.skill_taxonomy_service import (
    SkillTaxonomyService,
    SKILL_CATALOG,
    CAT_DSA,
    CAT_CS,
    CAT_SYSTEM_DESIGN,
    CAT_INTERVIEW_SKILLS
)
from services.skill_profiling_service import SkillProfilingService
from services.candidate_profile_service import CandidateProfileService
from services.roadmap_engine import PersonalizedRoadmapEngine, RecommendationEngine, SchedulingEngine
from local_supabase import get_supabase_client


class RoadmapService:
    """Generates and schedules tailored preparation roadmaps."""

    @staticmethod
    def calculate_skill_priority(
        proficiency: float,
        role_importance: float,
        confidence: float
    ) -> float:
        """
        Priority = (1 - (proficiency / 100)) * role_importance * max(0.4, confidence)
        Bounded between 0.05 and 1.0.
        Low confidence caps the priority from prematurely marking something as fully mastered.
        """
        norm_prof = max(0.0, min(1.0, proficiency / 100.0))
        norm_imp = max(0.1, min(1.0, role_importance))
        effective_conf = max(0.4, min(1.0, confidence))
        raw_prio = (1.0 - norm_prof) * norm_imp * effective_conf
        return round(max(0.05, min(1.0, raw_prio)), 3)

    @classmethod
    def generate_roadmap(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generates a personalized daily/weekly preparation plan based on candidate profile,
        current skill proficiencies, and prerequisite DAG.
        Delegates to PersonalizedRoadmapEngine for unified, production-grade scheduling.
        """
        if len(args) == 2 and not isinstance(args[0], str):
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
            raise ValueError("user_id is required")

        force_regenerate = kwargs.get("force_regenerate", False)
        job_id = kwargs.get("job_id")

        # Check existing roadmap unless force_regenerate is requested
        if not force_regenerate:
            existing = PersonalizedRoadmapEngine.get_or_create_roadmap(user_id=user_id, job_id=job_id, supabase_client=supabase_client)
            if existing and existing.get("activities"):
                return existing

        return PersonalizedRoadmapEngine.recalculate_roadmap(
            user_id=user_id,
            job_id=job_id,
            change_reason="Fresh Roadmap Generation" if force_regenerate else "Initial Roadmap Initialization",
            trigger_event="MANUAL_GENERATION",
            supabase_client=supabase_client
        )

    @classmethod
    def get_current_roadmap(cls, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Retrieves candidate's active roadmap, daily breakdown, and progress metrics."""
        if len(args) == 2 and not isinstance(args[0], str):
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

        rm_res = supabase_client.table("roadmaps").select("*").eq("user_id", user_id).execute()
        if not rm_res or not rm_res.data:
            return None

        roadmap = rm_res.data[0]
        rid = roadmap["id"]

        act_res = supabase_client.table("roadmap_activities").select("*").eq("roadmap_id", rid).order("day_number").execute()
        activities = act_res.data if (act_res and act_res.data) else []

        completed_count = sum(1 for a in activities if a.get("status") in ("completed", "COMPLETED"))
        total_count = len(activities)
        completion_pct = round((completed_count / total_count * 100)) if total_count > 0 else 0

        # Group activities by day
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        for a in activities:
            d = a.get("day_number", 1)
            if d not in by_day:
                by_day[d] = []

            res_payload = a.get("resource_payload")
            parsed_payload = {}
            if res_payload:
                try:
                    parsed_payload = json.loads(res_payload) if isinstance(res_payload, str) else res_payload
                except Exception:
                    parsed_payload = {}

            by_day[d].append({
                **a,
                "activity_id": a.get("activity_id") or a.get("id"),
                "id": a.get("id") or a.get("activity_id"),
                "skill_id": a["skill_id"],
                "skill_name": (SkillTaxonomyService.get_skill(a["skill_id"]) or {}).get("name", a["skill_id"]),
                "category": (SkillTaxonomyService.get_skill(a["skill_id"]) or {}).get("category", ""),
                "day_number": d,
                "order_in_day": a.get("order_in_day", 1),
                "title": a["title"],
                "description": a.get("description", ""),
                "activity_type": a["activity_type"],
                "difficulty": a["difficulty"],
                "estimated_minutes": a.get("estimated_minutes", 30),
                "priority": a.get("priority", 1.0),
                "due_date": a.get("due_date"),
                "status": a.get("status", "pending"),
                "is_pinned": bool(a.get("is_pinned", 0)),
                "recommendation_reason": a.get("recommendation_reason", ""),
                "resource_payload": parsed_payload,
                "completed_at": a.get("completed_at")
            })

        return {
            **roadmap,
            "roadmap_id": rid,
            "version": roadmap.get("current_version", 1),
            "current_version": roadmap.get("current_version", 1),
            "activities": activities,
            "schedule": by_day,
            "total_activities": total_count,
            "completed_activities": completed_count,
            "completion_percentage": completion_pct
        }

    @classmethod
    def recalculate_roadmap(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """Triggers adaptive recalculation of remaining activities."""
        if len(args) >= 2 and not isinstance(args[0], str):
            supabase_client, user_id = args[:2]
            change_reason = args[2] if len(args) > 2 else kwargs.get("change_reason", "Candidate requested rebalancing")
        elif len(args) == 1:
            if isinstance(args[0], str):
                user_id = args[0]
                supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            else:
                supabase_client = args[0]
                user_id = kwargs.get("user_id", "")
            change_reason = kwargs.get("change_reason", "Candidate requested rebalancing")
        else:
            user_id = kwargs.get("user_id", "")
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            change_reason = kwargs.get("change_reason", "Candidate requested rebalancing")

        job_id = kwargs.get("job_id")
        return PersonalizedRoadmapEngine.recalculate_roadmap(
            user_id=user_id,
            job_id=job_id,
            change_reason=change_reason,
            trigger_event="MANUAL_RECALCULATION",
            supabase_client=supabase_client
        )
