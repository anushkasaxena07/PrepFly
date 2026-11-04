"""
Continuous Roadmap Adaptation Engine for PrepFly Intelligence.
Adapts preparation plans dynamically upon performance triggers (coding submissions,
mock interviews, diagnostic tests, schedule changes) with non-destructive versioning.
"""

from typing import Dict, List, Optional, Any, Set
import json
import uuid
from datetime import datetime, timezone, timedelta

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.skill_profiling_service import SkillProfilingService
from services.candidate_profile_service import CandidateProfileService
from services.roadmap_service import RoadmapService

class RoadmapAdaptationService:
    """Manages trigger-based continuous adaptation and non-destructive roadmap versioning."""

    ADAPTATION_THRESHOLD = 8.0  # Minimum proficiency delta to trigger automatic reordering

    @classmethod
    def adapt_roadmap_on_trigger(cls, *args, **kwargs) -> Dict[str, Any]:
        from local_supabase import get_supabase_client
        if len(args) >= 3 and not isinstance(args[0], str):
            supabase_client = args[0]
            user_id = args[1]
            trigger_event = args[2]
            context_notes = args[3] if len(args) > 3 else kwargs.get("context_notes", "")
        else:
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            user_id = args[0] if args else kwargs.get("user_id", "")
            trigger_event = args[1] if len(args) > 1 else kwargs.get("trigger_type", "PERFORMANCE_TRIGGER")
            trigger_payload = kwargs.get("trigger_payload") or {}
            context_notes = json.dumps(trigger_payload) if isinstance(trigger_payload, dict) else str(trigger_payload)
        return cls.evaluate_and_adapt(supabase_client, user_id, trigger_event, context_notes)

    @staticmethod
    def evaluate_and_adapt(
        supabase_client,
        user_id: str,
        trigger_event: str,
        context_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluates whether recent performance changes warrant a roadmap adaptation.
        If meaningful changes are detected, produces a new roadmap version while
        strictly preserving all completed and pinned activities.
        """
        if not user_id:
            raise ValueError("user_id is required")

        # 1. Fetch current roadmap
        curr_rm = RoadmapService.get_current_roadmap(supabase_client, user_id)
        if not curr_rm:
            # No existing roadmap: generate initial roadmap
            return RoadmapService.generate_roadmap(supabase_client, user_id)

        roadmap_id = curr_rm["roadmap_id"]
        current_version = curr_rm["current_version"]

        # 2. Fetch skill profiles and profile settings
        skill_profiles = SkillProfilingService.get_candidate_profile(supabase_client, user_id)
        profile = CandidateProfileService.get_profile(supabase_client, user_id) or {}
        role_weights = SkillTaxonomyService.get_role_weights(profile.get("target_role", "Software Development Engineer"))

        # 3. Inspect existing activities: preserve completed & pinned
        act_res = supabase_client.table("roadmap_activities").select("*").eq("roadmap_id", roadmap_id).execute()
        existing_activities = act_res.data if (act_res and act_res.data) else []

        preserved_activities = [a for a in existing_activities if a.get("status") == "completed" or a.get("is_pinned") == 1]
        pending_activities = [a for a in existing_activities if a.get("status") == "pending" and a.get("is_pinned") == 0]

        # 4. Check for meaningful changes in pending skill priorities
        meaningful_changes = []
        skills_needing_remedy = []
        skills_mastered = []

        payload = {}
        if context_notes:
            try:
                payload = json.loads(context_notes) if isinstance(context_notes, str) else context_notes
            except Exception:
                payload = {}

        if isinstance(payload, dict) and "skill_id" in payload:
            sk_id = payload["skill_id"]
            sk_score = float(payload.get("score", 70.0))
            if sk_score < 50.0 and sk_id not in skills_needing_remedy:
                skills_needing_remedy.append(sk_id)
            elif sk_score >= 80.0 and sk_id not in skills_mastered:
                skills_mastered.append(sk_id)

        for sid, sp in skill_profiles.items():
            prof = sp.get("proficiency", 0.0)
            trend = sp.get("learning_trend", "stable")
            
            # Check if candidate is struggling (proficiency < 45 or declining)
            if prof < 45.0 and sp.get("evidence_count", 0) >= 1 and sid not in skills_needing_remedy:
                skills_needing_remedy.append(sid)
            # Check if candidate has demonstrated mastery (proficiency >= 75)
            elif prof >= 75.0 and sp.get("evidence_count", 0) >= 1 and sid not in skills_mastered:
                skills_mastered.append(sid)

        # 5. Formulate adaptation actions
        change_reasons = []
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        if skills_needing_remedy:
            remedy_names = [(SkillTaxonomyService.get_skill(s) or {}).get("name", s) for s in skills_needing_remedy[:2]]
            change_reasons.append(f"Identified foundation gaps in {', '.join(remedy_names)}; introduced prerequisite reinforcement exercises.")

        if skills_mastered:
            mastered_names = [(SkillTaxonomyService.get_skill(s) or {}).get("name", s) for s in skills_mastered[:2]]
            change_reasons.append(f"Demonstrated competence in {', '.join(mastered_names)}; accelerated to advanced interview simulations and scheduled spaced revision.")

        ev_lower = str(trigger_event).lower()
        if not change_reasons and ev_lower not in ("schedule_change", "manual_recalculate", "manual_request", "coding_submission", "performance_trigger"):
            # Fluctuations below threshold; no adaptation needed
            return {
                "adapted": False,
                "message": "Performance reviewed. No schedule changes required; current plan is on track.",
                "roadmap": curr_rm
            }

        if ev_lower == "schedule_change":
            change_reasons.append(f"Recalculated available study hours and deadline window: {context_notes}")
        elif ev_lower in ("manual_recalculate", "manual_request"):
            change_reasons.append(f"Manual plan recalculation requested: {context_notes or 'Refreshed priorities'}")
        elif not change_reasons:
            change_reasons.append(f"Triggered rebalancing following {trigger_event}: {context_notes}")

        # 6. Rebuild Pending Activities with New Priorities while preserving completed days
        completed_days = {a.get("day_number", 1) for a in preserved_activities}
        max_completed_day = max(completed_days) if completed_days else 0

        # Calculate new skill priorities
        scored_skills = []
        for sid, skill in SKILL_CATALOG.items():
            sp = skill_profiles.get(sid, {})
            prof = sp.get("proficiency", 0.0)
            conf = sp.get("confidence", 0.0)
            weight = role_weights.get(sid, 0.6)
            prio = RoadmapService.calculate_skill_priority(prof, weight, conf)
            scored_skills.append({
                "skill_id": sid,
                "name": skill["name"],
                "category": skill["category"],
                "difficulty": skill["difficulty"],
                "proficiency": prof,
                "confidence": conf,
                "priority": prio,
                "prerequisites": skill.get("prerequisites", [])
            })

        scored_skills.sort(key=lambda s: s["priority"], reverse=True)

        # Delete pending unpinned activities
        supabase_client.table("roadmap_activities").delete().eq("roadmap_id", roadmap_id).eq("status", "pending").eq("is_pinned", 0).execute()

        # Re-schedule pending activities starting from next available day
        duration_days = profile.get("preparation_duration_days", 30)
        daily_hours = profile.get("daily_study_hours", 2.0)
        daily_minutes_budget = int(daily_hours * 60)

        start_date = now_dt.date()
        next_day = max_completed_day + 1
        new_activities = []

        for s in scored_skills:
            if next_day > duration_days:
                break
            sid = s["skill_id"]
            prof = s["proficiency"]
            conf = s["confidence"]

            if sid in skills_mastered:
                # Add revision instead of introductory tasks
                act_type = "REVISION"
                title = f"Spaced Practice: {s['name']}"
                desc = f"Maintain fluency and verify retention in {s['name']}."
                est_min = min(30, daily_minutes_budget)
            elif sid in skills_needing_remedy:
                # Priority reinforcement
                act_type = "LEARN" if conf < 0.4 else "CODING"
                title = f"Focused Recovery: {s['name']}"
                desc = f"Reinforce core subproblem patterns and edge cases in {s['name']}."
                est_min = min(60, daily_minutes_budget)
            else:
                act_type = "PRACTICE"
                title = f"Skill Advancement: {s['name']}"
                desc = f"Solve interview-standard problems in {s['name']}."
                est_min = min(45, daily_minutes_budget)

            act_id = str(uuid.uuid4())
            due_iso = (start_date + timedelta(days=next_day - 1)).isoformat()
            new_act = {
                "id": act_id,
                "roadmap_id": roadmap_id,
                "user_id": user_id,
                "skill_id": sid,
                "day_number": next_day,
                "order_in_day": 1,
                "title": title,
                "description": desc,
                "activity_type": act_type,
                "difficulty": s["difficulty"],
                "estimated_minutes": est_min,
                "learning_objective": f"Solidify {s['name']} under timed conditions.",
                "completion_criteria": "Score >= 70% on task.",
                "priority": s["priority"],
                "due_date": due_iso,
                "status": "pending",
                "is_pinned": 0,
                "recommendation_reason": f"Adapted based on recent performance: {change_reasons[0]}",
                "resource_payload": json.dumps({"skill_id": sid}),
                "completed_at": None,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            new_activities.append(new_act)
            supabase_client.table("roadmap_activities").insert(new_act).execute()
            next_day += 1

        # 7. Record New Roadmap Version
        new_version_num = current_version + 1
        full_change_summary = " | ".join(change_reasons)
        snapshot = [
            {"day": a["day_number"], "title": a["title"], "skill_id": a["skill_id"], "type": a["activity_type"]}
            for a in (preserved_activities + new_activities)[:20]
        ]

        supabase_client.table("roadmap_versions").insert({
            "id": str(uuid.uuid4()),
            "roadmap_id": roadmap_id,
            "user_id": user_id,
            "version_number": new_version_num,
            "change_reason": full_change_summary,
            "trigger_event": trigger_event,
            "activities_snapshot": json.dumps(snapshot),
            "created_at": now_iso
        }).execute()

        # Update roadmap header
        supabase_client.table("roadmaps").update({
            "current_version": new_version_num,
            "total_activities": len(preserved_activities) + len(new_activities),
            "updated_at": now_iso
        }).eq("id", roadmap_id).execute()

        return {
            "adapted": True,
            "previous_version": current_version,
            "new_version": new_version_num,
            "change_reason": full_change_summary,
            "preserved_activities_count": len(preserved_activities),
            "recalculated_activities_count": len(new_activities),
            "roadmap": RoadmapService.get_current_roadmap(supabase_client, user_id)
        }
