"""
Interview Context Service for PrepFly Adaptive AI Interview Mentor.
Assembles, summarizes, versions, and caches a compact, high-yield context object
for all downstream mentor chat, curriculum scheduling, and assignment generation calls.
Guarantees fast retrieval within token budgets without transmitting bulky raw history.
"""

from typing import Dict, List, Optional, Any
import json
import hashlib
from datetime import datetime, timezone, timedelta

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService


# In-memory context cache: {cache_key: (timestamp, context_dict)}
_CONTEXT_CACHE: Dict[str, tuple[datetime, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


class InterviewContextService:
    """Provides high-density, versioned interview context summaries for LLM & planner consumers."""

    @classmethod
    def get_context(
        cls,
        user_id: str,
        goal_id: Optional[str] = None,
        force_refresh: bool = False,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """
        Retrieves compact, cached context object for the active interview goal.
        """
        cache_key = f"ctx_{user_id}_{goal_id or 'active'}"
        now = datetime.now(timezone.utc)

        if not force_refresh and cache_key in _CONTEXT_CACHE:
            cached_time, cached_val = _CONTEXT_CACHE[cache_key]
            if (now - cached_time).total_seconds() < CACHE_TTL_SECONDS:
                return cached_val

        supabase = supabase_client or get_supabase_client()

        # 1. Fetch active interview goal
        goal = None
        if goal_id:
            res = supabase.table("interview_goals").select("*").eq("id", goal_id).eq("user_id", user_id).execute()
            if res and res.data:
                goal = res.data[0]
        if not goal:
            res = supabase.table("interview_goals").select("*").eq("user_id", user_id).eq("status", "active").order("updated_at", desc=True).limit(1).execute()
            if res and res.data:
                goal = res.data[0]
        if not goal:
            # Fall back to latest draft or profile defaults
            res = supabase.table("interview_goals").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if res and res.data:
                goal = res.data[0]

        target_role = goal.get("target_role") if goal else "Software Development Engineer (General)"
        target_company = goal.get("target_company") if goal else "Tech Firm"
        norm_role = SkillTaxonomyService.normalize_role(target_role)

        # 2. Calculate Days Left to Interview
        days_left = 30
        if goal and goal.get("target_interview_date"):
            try:
                t_date = datetime.strptime(goal["target_interview_date"], "%Y-%m-%d").date()
                diff = (t_date - now.date()).days
                days_left = max(1, diff)
            except Exception:
                days_left = goal.get("days_horizon", 30)
        elif goal and goal.get("days_horizon"):
            days_left = max(1, int(goal["days_horizon"]))

        daily_minutes = int(goal.get("daily_minutes", 60)) if goal else 60
        learning_pref = goal.get("learning_preference", "hands-on") if goal else "hands-on"

        # 3. Retrieve Top Requirements (from job_skill_requirements or taxonomy)
        top_requirements: List[Dict[str, Any]] = []
        try:
            if goal and goal.get("id"):
                req_res = supabase.table("job_skill_requirements").select("skill_id, weight, is_required").eq("job_id", goal["id"]).order("weight", desc=True).limit(8).execute()
                if req_res and req_res.data:
                    for r in req_res.data:
                        sinfo = SkillTaxonomyService.get_skill(r["skill_id"])
                        sname = sinfo.get("name", r["skill_id"]) if sinfo else str(r["skill_id"]).replace("_", " ").title()
                        top_requirements.append({
                            "skill_id": r["skill_id"],
                            "skill_name": sname,
                            "weight": float(r.get("weight", 0.0)),
                            "is_required": bool(r.get("is_required", True))
                        })
        except Exception:
            pass

        if not top_requirements:
            # Sourced from taxonomy role weights
            role_w = SkillTaxonomyService.get_role_weights(norm_role)
            sorted_w = sorted(role_w.items(), key=lambda kv: kv[1], reverse=True)[:8]
            for sid, w in sorted_w:
                sinfo = SkillTaxonomyService.get_skill(sid)
                sname = sinfo.get("name", sid) if sinfo else str(sid).replace("_", " ").title()
                top_requirements.append({
                    "skill_id": sid,
                    "skill_name": sname,
                    "weight": round(w, 3),
                    "is_required": True
                })

        # 4. Summarize Candidate Skill States
        skill_states_summary = cls._summarize_skill_states(supabase, user_id)

        # 5. Extract Top Recurring Mistakes
        top_mistakes = cls._extract_top_mistakes(supabase, user_id)

        # 6. Compact Recent Evaluations (last 5)
        recent_evals = cls._fetch_compact_recent_evaluations(supabase, user_id, limit=5)

        # 7. Formulate Version & Hash
        version_seed = f"{target_role}:{target_company}:{days_left}:{daily_minutes}:{len(recent_evals)}:{skill_states_summary.get('verified_gaps_count', 0)}"
        context_version = int(hashlib.md5(version_seed.encode("utf-8")).hexdigest()[:8], 16) % 100000

        context_obj: Dict[str, Any] = {
            "context_version": context_version,
            "cached_at": now.isoformat(),
            "goal": {
                "goal_id": goal.get("id") if goal else None,
                "target_role": target_role,
                "target_company": target_company,
                "normalized_role": norm_role,
                "learning_preference": learning_pref,
                "required_experience_years": float(goal.get("required_experience_years", 0.0)) if goal else 0.0,
                "candidate_actual_experience_years": float(goal.get("candidate_actual_experience_years", 0.0)) if goal else 0.0,
                "self_reported_skills": json.loads(goal.get("self_reported_skills") or "[]") if goal else [],
                "previous_attempts": int(goal.get("previous_attempts", 0)) if goal else 0
            },
            "schedule_constraints": {
                "days_left": days_left,
                "daily_minutes": daily_minutes,
                "is_compressed_deadline": (days_left <= 7)
            },
            "top_requirements": top_requirements,
            "skill_state_summary": skill_states_summary,
            "top_recurring_mistakes": top_mistakes,
            "recent_evaluations": recent_evals
        }

        # Store in in-memory cache
        _CONTEXT_CACHE[cache_key] = (now, context_obj)
        return context_obj

    @classmethod
    def invalidate_cache(cls, user_id: str, goal_id: Optional[str] = None) -> None:
        """Invalidates context cache entries for a user."""
        keys_to_del = [k for k in _CONTEXT_CACHE if k.startswith(f"ctx_{user_id}")]
        for k in keys_to_del:
            _CONTEXT_CACHE.pop(k, None)

    @classmethod
    def _summarize_skill_states(cls, supabase: Any, user_id: str) -> Dict[str, Any]:
        """Aggregates state counts, verified gaps, and mastered competencies."""
        summary = {
            "counts": {"MASTERED": 0, "DEMONSTRATED": 0, "DEVELOPING": 0, "VERIFIED_GAP": 0, "NOT_ASSESSED": 0},
            "verified_gaps": [],
            "verified_gaps_count": 0,
            "mastered_skills": [],
            "developing_skills": []
        }

        try:
            res = supabase.table("candidate_skill_states").select("*").eq("user_id", user_id).execute()
            if res and res.data:
                for row in res.data:
                    status = row.get("status")
                    prof = float(row.get("proficiency", 0.0))
                    conf = float(row.get("confidence", 0.0))
                    if not status or status == "NOT_ASSESSED":
                        if prof >= 85.0 and conf >= 0.7:
                            status = "MASTERED"
                        elif prof >= 60.0:
                            status = "DEMONSTRATED"
                        elif prof < 60.0 and conf >= 0.4:
                            status = "VERIFIED_GAP"
                        else:
                            status = "DEVELOPING"

                    sid = row.get("skill_id")
                    sinfo = SkillTaxonomyService.get_skill(sid)
                    sname = sinfo.get("name", sid) if sinfo else str(sid).replace("_", " ").title()

                    if status in summary["counts"]:
                        summary["counts"][status] += 1
                    else:
                        summary["counts"]["NOT_ASSESSED"] += 1

                    if status == "VERIFIED_GAP":
                        summary["verified_gaps"].append({"skill_id": sid, "name": sname, "proficiency": prof})
                    elif status == "MASTERED":
                        summary["mastered_skills"].append({"skill_id": sid, "name": sname, "proficiency": prof})
                    elif status == "DEVELOPING":
                        summary["developing_skills"].append({"skill_id": sid, "name": sname, "proficiency": prof})

                summary["verified_gaps_count"] = len(summary["verified_gaps"])
        except Exception:
            pass

        return summary

    @classmethod
    def _extract_top_mistakes(cls, supabase: Any, user_id: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Identifies top recurring misconceptions across evaluations."""
        mistakes: List[Dict[str, Any]] = []
        try:
            res = supabase.table("evaluations").select("missing_concepts, feedback, generated_at").eq("user_id", user_id).order("generated_at", desc=True).limit(20).execute()
            if res and res.data:
                concept_counts: Dict[str, int] = {}
                for ev in res.data:
                    raw_mc = ev.get("missing_concepts")
                    if raw_mc:
                        parsed = []
                        if isinstance(raw_mc, list):
                            parsed = raw_mc
                        elif isinstance(raw_mc, str):
                            try:
                                parsed = json.loads(raw_mc)
                            except Exception:
                                parsed = [raw_mc]
                        for c in parsed:
                            c_str = str(c).strip()
                            if c_str:
                                concept_counts[c_str] = concept_counts.get(c_str, 0) + 1

                sorted_concepts = sorted(concept_counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
                for c, count in sorted_concepts:
                    mistakes.append({"concept": c, "occurrences": count})
        except Exception:
            pass

        return mistakes

    @classmethod
    def _fetch_compact_recent_evaluations(cls, supabase: Any, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Extracts recent evaluations without storing verbose prompt texts."""
        compact_evals: List[Dict[str, Any]] = []
        try:
            res = supabase.table("evaluations").select("id, item_id, score, confidence, evaluated_at, generated_at").eq("user_id", user_id).order("generated_at", desc=True).limit(limit).execute()
            if res and res.data:
                for row in res.data:
                    compact_evals.append({
                        "evaluation_id": row.get("id"),
                        "item_id": row.get("item_id"),
                        "score": round(float(row.get("score", 0.0)), 1),
                        "confidence": round(float(row.get("confidence", 0.5)), 2),
                        "evaluated_at": row.get("evaluated_at") or row.get("generated_at")
                    })
        except Exception:
            pass

        return compact_evals
