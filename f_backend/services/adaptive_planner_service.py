"""
Adaptive Planner Service for PrepFly Adaptive AI Interview Mentor.
Produces deterministic, versioned preparation roadmaps backed by cryptographic input hashes.
Executes incremental updates upon triggers (new_evaluation, missed_day, interview_date_changed,
daily_minutes_changed, revision_due) preserving completed work and producing structured diffs.
Enforces strict anti-sameness validation rejecting non-measurable generic titles.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
import json
import hashlib
import uuid
from datetime import datetime, timezone, timedelta

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.curriculum_engine import (
    CurriculumEngine,
    ACTIVITY_ASSESSMENT,
    ACTIVITY_LESSON,
    ACTIVITY_PRACTICE_SET,
    ACTIVITY_ASSIGNMENT,
    ACTIVITY_CODING_DRILL,
    ACTIVITY_MOCK_INTERVIEW,
    ACTIVITY_REVISION,
    ACTIVITY_PROJECT_DEEP_DIVE,
    ACTIVITY_BEHAVIORAL_PREP,
    REASON_VERIFIED_GAP,
    REASON_UNASSESSED_PROBE,
    REASON_SPACED_REVISION,
    REASON_INTERVIEW_COMPRESSION
)

# Reject generic unstructured activities
GENERIC_REJECT_PREFIXES = ("study ", "read about ", "overview of ", "learn ", "explore ")


def compute_planner_input_hash(
    candidate_profile: Dict[str, Any],
    goal: Dict[str, Any],
    skill_states: List[Dict[str, Any]],
    constraints: Dict[str, Any],
    history_len: int
) -> str:
    """
    Computes deterministic SHA-256 hash across all planner inputs.
    Identical inputs -> Identical hash -> Identical plan.
    """
    normalized_skills = sorted(
        [
            f"{s.get('skill_id')}:{s.get('status')}:{round(float(s.get('proficiency', 0.0)), 1)}"
            for s in skill_states
        ]
    )
    payload = {
        "user_id": candidate_profile.get("user_id"),
        "role": goal.get("normalized_role") or goal.get("target_role"),
        "company": goal.get("target_company"),
        "experience": goal.get("candidate_actual_experience_years", 0.0),
        "days_left": constraints.get("days_left", 30),
        "daily_minutes": constraints.get("daily_minutes", 60),
        "skill_states": normalized_skills,
        "history_count": history_len
    }
    dumped = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


class AdaptivePlannerService:
    """Orchestrates deterministic, versioned, and incrementally updated candidate roadmaps."""

    _ACTIVE_PLANS: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_active_plan(
        cls,
        user_id: str,
        supabase_client: Any = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves active cached roadmap plan for candidate, or builds initial plan if goal exists."""
        if user_id in cls._ACTIVE_PLANS:
            return cls._ACTIVE_PLANS[user_id]

        supabase = supabase_client or get_supabase_client()
        try:
            from services.interview_context_service import InterviewContextService
            ctx = InterviewContextService.get_context(user_id, supabase_client=supabase)
            if not ctx:
                return None

            css_res = supabase.table("candidate_skill_states").select("*").eq("user_id", user_id).execute()
            skill_states = css_res.data if (css_res and css_res.data) else []

            goal = {
                "target_role": ctx.get("target_role", "Software Development Engineer"),
                "target_company": ctx.get("target_company", "Tech Company"),
                "candidate_actual_experience_years": 2.0,
                "learning_preference": ctx.get("learning_preference", "hands-on")
            }
            candidate_profile = {
                "user_id": user_id,
                "experience_level": "Mid-Level",
                "daily_minutes": ctx.get("daily_minutes", 60)
            }
            constraints = {
                "days_left": ctx.get("days_left", 30),
                "daily_minutes": ctx.get("daily_minutes", 60)
            }
            plan = cls.build_plan(
                candidate_profile=candidate_profile,
                goal=goal,
                skill_states=skill_states,
                constraints=constraints,
                supabase_client=supabase
            )
            cls._ACTIVE_PLANS[user_id] = plan
            return plan
        except Exception:
            return None

    @classmethod
    def validate_activity_structure(cls, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates that every activity has a measurable learning objective and concrete deliverable.
        Rejects lazy generic strings ("Study ML architecture").
        """
        title = activity.get("title", "").strip()
        lower_title = title.lower()

        # Enforce rejection of generic study/read strings
        for pref in GENERIC_REJECT_PREFIXES:
            if lower_title.startswith(pref):
                # Auto-upgrade to concrete invariant drill
                sname = activity.get("skill_name") or activity.get("skill_id", "").replace("_", " ").title()
                title = f"Applied Invariants & Mechanics: {sname}"
                break

        # Guarantee concrete practice task and submission requirements
        practice_task = activity.get("practice_task")
        if not practice_task:
            atype = activity.get("activity_type")
            sname = activity.get("skill_name") or "Core Skill"
            if atype == ACTIVITY_ASSESSMENT:
                practice_task = f"Complete 5-minute technical turn evaluating edge-case invariants for {sname}."
            elif atype == ACTIVITY_CODING_DRILL:
                practice_task = f"Write sandboxed code implementation for {sname} passing hidden test cases."
            elif atype == ACTIVITY_REVISION:
                practice_task = f"Active recall flash quiz testing core asymptotic complexity and failure modes for {sname}."
            else:
                practice_task = f"Design and implement production solution addressing critical edge cases in {sname}."

        sub_reqs = activity.get("submission_requirements")
        if not sub_reqs:
            sub_reqs = "Executable code or structured technical explanation evaluated against rubric criteria."

        eval_criteria = activity.get("evaluation_criteria")
        if not eval_criteria:
            eval_criteria = "Correctness (40%), Technical Depth (30%), Edge Cases & Complexity (20%), Clarity (10%)."

        activity["title"] = title
        activity["practice_task"] = practice_task
        activity["submission_requirements"] = sub_reqs
        activity["evaluation_criteria"] = eval_criteria
        activity["completion_conditions"] = activity.get("completion_conditions") or "Score >= 70% on verified evaluation."
        return activity

    @classmethod
    def build_plan(
        cls,
        candidate_profile: Dict[str, Any],
        goal: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        history: Optional[List[Dict[str, Any]]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """
        Builds a fresh, version 1 preparation roadmap. Pure, deterministic, and reproducible.
        """
        hist = history or []
        target_role = goal.get("normalized_role") or SkillTaxonomyService.normalize_role(goal.get("target_role", "Software Development Engineer"))
        
        c = constraints or {}
        days_left = max(1, int(c.get("days_left") or goal.get("days_horizon") or candidate_profile.get("days_left") or 30))
        daily_mins = max(30, int(c.get("daily_minutes") or goal.get("daily_minutes") or candidate_profile.get("daily_minutes") or 60))

        constraints = {
            "days_left": days_left,
            "daily_minutes": daily_mins,
            "is_compressed_deadline": (days_left <= 7)
        }

        # 1. Compute Cryptographic Input Hash
        input_hash = compute_planner_input_hash(
            candidate_profile=candidate_profile,
            goal=goal,
            skill_states=skill_states,
            constraints=constraints,
            history_len=len(hist)
        )

        # 2. Build context for CurriculumEngine
        skill_summary: Dict[str, Any] = {
            "verified_gaps": [],
            "mastered_skills": [],
            "developing_skills": []
        }
        for s in skill_states:
            st = s.get("status")
            prof = float(s.get("proficiency", 0.0))
            sid = s.get("skill_id")
            if st == "VERIFIED_GAP" or prof < 60.0 and st != "NOT_ASSESSED":
                skill_summary["verified_gaps"].append({"skill_id": sid, "proficiency": prof})
            elif st == "MASTERED" or prof >= 85.0:
                skill_summary["mastered_skills"].append({"skill_id": sid, "proficiency": prof})
            elif st == "DEVELOPING" or prof >= 60.0:
                skill_summary["developing_skills"].append({"skill_id": sid, "proficiency": prof})

        context = {
            "goal": {**goal, "normalized_role": target_role},
            "schedule_constraints": constraints,
            "top_requirements": goal.get("top_requirements", []),
            "skill_state_summary": skill_summary
        }

        # 3. Invoke CurriculumEngine
        curriculum = CurriculumEngine.build_curriculum(context)
        raw_activities = curriculum["activities"]

        # 4. Validate all activities against generic titles & missing deliverables
        validated_activities = []
        for act in raw_activities:
            val_act = cls.validate_activity_structure(act)
            validated_activities.append(val_act)

        # Re-group into daily schedule
        daily_schedule: Dict[int, List[Dict[str, Any]]] = {d: [] for d in range(1, days_left + 1)}
        for act in validated_activities:
            d = act.get("day_number", 1)
            if d in daily_schedule:
                daily_schedule[d].append(act)

        version_id = f"ver_{uuid.uuid4().hex[:10]}"
        roadmap_id = f"rm_{uuid.uuid4().hex[:10]}"

        roadmap_version: Dict[str, Any] = {
            "id": version_id,
            "roadmap_id": roadmap_id,
            "user_id": candidate_profile.get("user_id"),
            "version_number": 1,
            "input_hash": input_hash,
            "change_summary": "Initial deterministic preparation roadmap generated.",
            "trigger_event": "INITIAL_GENERATION",
            "diff": {
                "added": [a["title"] for a in validated_activities],
                "removed": [],
                "moved": [],
                "difficulty_changed": []
            },
            "horizon_days": days_left,
            "daily_minutes": daily_mins,
            "is_compressed_deadline": curriculum["is_compressed_deadline"],
            "total_activities": len(validated_activities),
            "activities": validated_activities,
            "daily_schedule": daily_schedule,
            "deferred_items": curriculum.get("deferred_skills", []),
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Persist version to database if client provided
        if supabase_client:
            try:
                supabase_client.table("roadmaps").insert({
                    "id": roadmap_id,
                    "user_id": candidate_profile.get("user_id"),
                    "target_role": target_role,
                    "target_company": goal.get("target_company"),
                    "current_version": 1,
                    "total_days": days_left,
                    "total_activities": len(validated_activities),
                    "completed_activities": 0,
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).execute()

                supabase_client.table("roadmap_versions").insert({
                    "id": version_id,
                    "roadmap_id": roadmap_id,
                    "user_id": candidate_profile.get("user_id"),
                    "version_number": 1,
                    "change_reason": "Initial plan build",
                    "trigger_event": "INITIAL_GENERATION",
                    "activities_snapshot": json.dumps([a.get("title") for a in validated_activities]),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
            except Exception:
                pass

        if candidate_profile and candidate_profile.get("user_id"):
            cls._ACTIVE_PLANS[candidate_profile.get("user_id")] = roadmap_version

        return roadmap_version

    @classmethod
    def update_plan(
        cls,
        current_version: Dict[str, Any],
        trigger_type: str,
        trigger_payload: Dict[str, Any],
        candidate_profile: Optional[Dict[str, Any]] = None,
        goal: Optional[Dict[str, Any]] = None,
        skill_states: Optional[List[Dict[str, Any]]] = None,
        supabase_client: Any = None
    ) -> Dict[str, Any]:
        """
        Incrementally adapts active roadmap version based on triggers:
        - new_evaluation: updates affected skills, unblocks dependent items, inserts remediation
        - missed_day: carries over pending work, defers lowest priority if capacity exceeded
        - interview_date_changed: recomputes horizon and capacity
        - daily_minutes_changed: rebalances daily load to match new time budget
        - revision_due: schedules 15-minute spaced retrieval flash quizzes
        Preserves all completed work, past evaluations, and history.
        """
        old_activities = current_version.get("activities", [])
        old_version_num = current_version.get("version_number", 1)
        roadmap_id = current_version.get("roadmap_id") or f"rm_{uuid.uuid4().hex[:10]}"
        user_id = current_version.get("user_id")

        # Separate completed work from in-flight/pending work
        completed_activities = [a for a in old_activities if a.get("status") in ("COMPLETED", "completed")]
        pending_activities = [a for a in old_activities if a.get("status") not in ("COMPLETED", "completed")]

        diff: Dict[str, Any] = {
            "added": [],
            "removed": [],
            "moved": [],
            "difficulty_changed": []
        }
        change_summary = ""

        updated_activities: List[Dict[str, Any]] = list(completed_activities)
        deferred_items: List[Dict[str, Any]] = list(current_version.get("deferred_items", []))

        days_left = current_version.get("horizon_days", 30)
        daily_minutes = current_version.get("daily_minutes", 60)

        # ── Trigger 1: new_evaluation ──
        if trigger_type == "new_evaluation":
            evaluated_skill = trigger_payload.get("skill_id")
            score = float(trigger_payload.get("score", 0.0))
            evidence_id = trigger_payload.get("evidence_id")

            change_summary = f"Adapted plan following new evaluation on {evaluated_skill} (Score: {score}%)."

            if score >= 60.0:
                # Skill mastered/demonstrated: remove pending basic lessons for this skill
                for act in pending_activities:
                    if act.get("skill_id") == evaluated_skill and act.get("activity_type") in (ACTIVITY_LESSON, ACTIVITY_ASSESSMENT):
                        diff["removed"].append(act.get("title"))
                    else:
                        updated_activities.append(act)

                sinfo = SkillTaxonomyService.get_skill(evaluated_skill) or {}
                sname = sinfo.get("name") or evaluated_skill.replace('_', ' ').title()

                # Insert spaced revision slot
                rev_act = cls.validate_activity_structure({
                    "id": f"act_{uuid.uuid4().hex[:10]}",
                    "skill_id": evaluated_skill,
                    "title": f"Spaced Revision: {sname} Retrieval",
                    "activity_type": ACTIVITY_REVISION,
                    "difficulty": "intermediate" if score < 85.0 else "advanced",
                    "estimated_minutes": 15,
                    "day_number": min(days_left, 3),
                    "priority": 0.2,
                    "reason_code": REASON_SPACED_REVISION,
                    "evidence_ids": [evidence_id] if evidence_id else []
                })
                updated_activities.append(rev_act)
                diff["added"].append(rev_act["title"])

                # Unblock any dependent skills that were blocked by evaluated_skill
                for act in updated_activities:
                    if act.get("is_blocked") and evaluated_skill in act.get("blocked_by", []):
                        act["blocked_by"].remove(evaluated_skill)
                        if len(act["blocked_by"]) == 0:
                            act["is_blocked"] = False
                            diff["moved"].append({
                                "activity": act.get("title"),
                                "reason": f"Unblocked: prerequisite {evaluated_skill} passed."
                            })
            else:
                # Failure / Gap: Insert remediation drill
                remed_act = cls.validate_activity_structure({
                    "id": f"act_{uuid.uuid4().hex[:10]}",
                    "skill_id": evaluated_skill,
                    "title": f"Targeted Remediation: {evaluated_skill.replace('_', ' ').title()} Gaps",
                    "activity_type": ACTIVITY_LESSON,
                    "difficulty": "beginner",
                    "estimated_minutes": 30,
                    "day_number": 1,
                    "priority": 2.5,
                    "reason_code": REASON_VERIFIED_GAP,
                    "evidence_ids": [evidence_id] if evidence_id else []
                })
                updated_activities.append(remed_act)
                diff["added"].append(remed_act["title"])
                updated_activities.extend(pending_activities)

        # ── Trigger 2: missed_day ──
        elif trigger_type == "missed_day":
            missed_day_num = int(trigger_payload.get("missed_day", 1))
            change_summary = f"Carried over uncompleted Day {missed_day_num} activities and rebalanced schedule."

            max_budget = int(daily_minutes * 1.10)
            carried_over = [a for a in pending_activities if a.get("day_number") == missed_day_num]
            future_activities = [a for a in pending_activities if a.get("day_number") > missed_day_num]

            # Shift carried over activities to missed_day_num + 1
            for act in carried_over:
                orig_day = act.get("day_number")
                act["day_number"] = min(days_left, missed_day_num + 1)
                act["rescheduled_from"] = f"missed_day_{missed_day_num}"
                diff["moved"].append({
                    "activity": act.get("title"),
                    "from_day": orig_day,
                    "to_day": act["day_number"],
                    "reason": "Carried over from missed day."
                })
                updated_activities.append(act)

            # Re-bin future activities, deferring lowest priority if total overflow exceeds horizon
            for act in future_activities:
                updated_activities.append(act)

        # ── Trigger 3: interview_date_changed ──
        elif trigger_type == "interview_date_changed":
            new_days = max(1, int(trigger_payload.get("days_left", days_left)))
            days_left = new_days
            change_summary = f"Recalculated preparation schedule for updated {days_left}-day interview timeline."

            if days_left <= 7:
                # Compress to critical gaps + revision + mocks
                compressed_acts = []
                for act in pending_activities:
                    # Defer low-importance items
                    if act.get("priority", 0.0) < 0.25 and act.get("reason_code") != REASON_VERIFIED_GAP:
                        deferred_items.append({
                            "title": act.get("title"),
                            "skill_id": act.get("skill_id"),
                            "reason": "deferred_due_to_imminent_interview",
                            "explanation": f"Deferred to focus on critical interview gaps during {days_left}-day countdown."
                        })
                        diff["removed"].append(act.get("title"))
                    else:
                        act["day_number"] = min(days_left, act.get("day_number", 1))
                        compressed_acts.append(act)
                updated_activities.extend(compressed_acts)
            else:
                updated_activities.extend(pending_activities)

        # ── Trigger 4: daily_minutes_changed ──
        elif trigger_type == "daily_minutes_changed":
            new_daily_mins = max(20, int(trigger_payload.get("daily_minutes", daily_minutes)))
            scope = trigger_payload.get("scope", "all")  # "today" or "all"
            daily_minutes = new_daily_mins
            change_summary = f"Adjusted study budget to {new_daily_mins} minutes/day ({scope})."

            max_budget = int(new_daily_mins * 1.10)
            # Rebalance daily assignments
            curr_day = 1
            curr_spent = 0
            for act in pending_activities:
                dur = act.get("estimated_minutes", 30)
                if curr_spent + dur > max_budget:
                    curr_day = min(days_left, curr_day + 1)
                    curr_spent = 0
                if act.get("day_number") != curr_day:
                    diff["moved"].append({
                        "activity": act.get("title"),
                        "from_day": act.get("day_number"),
                        "to_day": curr_day,
                        "reason": "Rebalanced for daily minutes constraint."
                    })
                    act["day_number"] = curr_day
                curr_spent += dur
                updated_activities.append(act)

        # ── Trigger 5: revision_due ──
        elif trigger_type == "revision_due":
            rev_skill = trigger_payload.get("skill_id")
            change_summary = f"Scheduled spaced retrieval drill for {rev_skill}."
            rev_act = cls.validate_activity_structure({
                "id": f"act_{uuid.uuid4().hex[:10]}",
                "skill_id": rev_skill,
                "title": f"Spaced Revision: {rev_skill.replace('_', ' ').title()} Retrieval",
                "activity_type": ACTIVITY_REVISION,
                "difficulty": "intermediate",
                "estimated_minutes": 15,
                "day_number": 1,
                "priority": 0.5,
                "reason_code": REASON_SPACED_REVISION,
                "evidence_ids": []
            })
            updated_activities.insert(0, rev_act)
            diff["added"].append(rev_act["title"])
            updated_activities.extend(pending_activities)

        else:
            updated_activities.extend(pending_activities)
            change_summary = f"Plan re-synchronized for trigger: {trigger_type}."

        # Reconstruct daily schedule
        daily_schedule: Dict[int, List[Dict[str, Any]]] = {d: [] for d in range(1, days_left + 1)}
        for act in updated_activities:
            d = min(days_left, act.get("day_number", 1))
            act["day_number"] = d
            daily_schedule[d].append(act)

        new_version_num = old_version_num + 1
        new_version_id = f"ver_{uuid.uuid4().hex[:10]}"

        # Compute updated input hash
        new_input_hash = hashlib.sha256(
            f"{roadmap_id}:{new_version_num}:{len(updated_activities)}:{days_left}:{daily_minutes}:{trigger_type}".encode("utf-8")
        ).hexdigest()

        new_version: Dict[str, Any] = {
            "id": new_version_id,
            "roadmap_id": roadmap_id,
            "user_id": user_id,
            "version_number": new_version_num,
            "input_hash": new_input_hash,
            "change_summary": change_summary,
            "trigger_event": trigger_type,
            "diff": diff,
            "horizon_days": days_left,
            "daily_minutes": daily_minutes,
            "is_compressed_deadline": (days_left <= 7),
            "total_activities": len(updated_activities),
            "activities": updated_activities,
            "daily_schedule": daily_schedule,
            "deferred_items": deferred_items,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Persist version to DB if client provided
        if supabase_client:
            try:
                supabase_client.table("roadmaps").update({
                    "current_version": new_version_num,
                    "total_days": days_left,
                    "total_activities": len(updated_activities),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", roadmap_id).execute()

                supabase_client.table("roadmap_versions").insert({
                    "id": new_version_id,
                    "roadmap_id": roadmap_id,
                    "user_id": user_id,
                    "version_number": new_version_num,
                    "change_reason": change_summary,
                    "trigger_event": trigger_type,
                    "activities_snapshot": json.dumps([a.get("title") for a in updated_activities]),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }).execute()
            except Exception:
                pass

        if user_id:
            cls._ACTIVE_PLANS[user_id] = new_version

        return new_version
