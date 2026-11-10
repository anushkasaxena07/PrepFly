"""
Deterministic Curriculum Engine for PrepFly Adaptive AI Interview Mentor.
Calculates skill priority via:
    priority = role_importance * need * prerequisite_urgency * deadline_factor
Performs bin-packing into daily_minutes (with 10% buffer), suppresses mastered skills
from full lessons, blocks dependent skills when prerequisites have verified gaps,
and tags every curriculum row with reason_code + evidence_ids.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
import math
import uuid
from datetime import datetime, timezone

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG


# Activity Types
ACTIVITY_ASSESSMENT = "assessment"
ACTIVITY_LESSON = "lesson"
ACTIVITY_PRACTICE_SET = "practice_set"
ACTIVITY_ASSIGNMENT = "assignment"
ACTIVITY_CODING_DRILL = "coding_drill"
ACTIVITY_MOCK_INTERVIEW = "mock_interview"
ACTIVITY_REVISION = "revision"
ACTIVITY_PROJECT_DEEP_DIVE = "project_deep_dive"
ACTIVITY_BEHAVIORAL_PREP = "behavioral_prep"

VALID_ACTIVITY_TYPES = {
    ACTIVITY_ASSESSMENT,
    ACTIVITY_LESSON,
    ACTIVITY_PRACTICE_SET,
    ACTIVITY_ASSIGNMENT,
    ACTIVITY_CODING_DRILL,
    ACTIVITY_MOCK_INTERVIEW,
    ACTIVITY_REVISION,
    ACTIVITY_PROJECT_DEEP_DIVE,
    ACTIVITY_BEHAVIORAL_PREP
}

# Explicit Reason Codes
REASON_UNASSESSED_PROBE = "unassessed_baseline_calibration"
REASON_VERIFIED_GAP = "verified_performance_gap"
REASON_PREREQUISITE_DEPENDENCY = "prerequisite_knowledge_foundation"
REASON_MANDATORY_JD_REQUIREMENT = "mandatory_job_description_requirement"
REASON_SPACED_REVISION = "spaced_retrieval_refresher"
REASON_INTERVIEW_COMPRESSION = "imminent_interview_drill"
REASON_PROJECT_DEFENSE = "project_experience_defense"
REASON_BEHAVIORAL_ALIGNMENT = "behavioral_competency_alignment"


class CurriculumEngine:
    """Deterministic scheduling and priority engine for interview preparation curricula."""

    @classmethod
    def calculate_skill_priority(
        cls,
        role_importance: float,
        proficiency: Optional[float],
        confidence: float,
        status: str,
        prerequisite_urgency: float,
        deadline_factor: float
    ) -> Tuple[float, str]:
        """
        priority = role_importance * need * prerequisite_urgency * deadline_factor
        """
        norm_imp = max(0.1, min(1.0, role_importance))

        # Calculate need:
        # If assessed: need = 1 - (proficiency / 100.0)
        # If NOT_ASSESSED: assessment is needed first (assessment_needed = 0.75)
        if status == "NOT_ASSESSED" or proficiency is None:
            need = 0.75
            primary_reason = REASON_UNASSESSED_PROBE
        else:
            norm_prof = max(0.0, min(1.0, proficiency / 100.0))
            need = 1.0 - norm_prof
            if status == "VERIFIED_GAP":
                primary_reason = REASON_VERIFIED_GAP
            elif status in ("MASTERED", "DEMONSTRATED"):
                primary_reason = REASON_SPACED_REVISION
            else:
                primary_reason = REASON_MANDATORY_JD_REQUIREMENT

        # Calculate raw priority
        raw_priority = norm_imp * need * prerequisite_urgency * deadline_factor
        priority = round(max(0.01, min(10.0, raw_priority)), 4)
        return priority, primary_reason

    @classmethod
    def build_curriculum(
        cls,
        context: Dict[str, Any],
        skill_evidence_map: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Generates deterministic curriculum based on interview context, verified skill states,
        prerequisite DAG, and calendar horizon.
        """
        goal = context.get("goal", {})
        constraints = context.get("schedule_constraints", {})
        top_reqs = context.get("top_requirements", [])
        skill_summary = context.get("skill_state_summary", {})

        target_role = goal.get("normalized_role") or "software_development_engineer"
        days_left = max(1, int(constraints.get("days_left", 30)))
        daily_minutes = max(30, int(constraints.get("daily_minutes", 60)))
        max_daily_budget = int(daily_minutes * 1.10)  # 10% buffer
        is_compressed = bool(constraints.get("is_compressed_deadline", days_left <= 7))

        # 1. Build lookup tables for candidate skill states
        verified_states: Dict[str, Dict[str, Any]] = {}
        for gap in skill_summary.get("verified_gaps", []):
            verified_states[gap["skill_id"]] = {
                "status": "VERIFIED_GAP",
                "proficiency": float(gap.get("proficiency", 30.0)),
                "confidence": 0.8
            }
        for m in skill_summary.get("mastered_skills", []):
            verified_states[m["skill_id"]] = {
                "status": "MASTERED",
                "proficiency": float(m.get("proficiency", 95.0)),
                "confidence": 0.9
            }
        for d in skill_summary.get("developing_skills", []):
            verified_states[d["skill_id"]] = {
                "status": "DEVELOPING",
                "proficiency": float(d.get("proficiency", 55.0)),
                "confidence": 0.6
            }

        ev_map = skill_evidence_map or {}

        # 2. Extract weights for all candidate skills
        dag = SkillTaxonomyService.get_prerequisites_dag()
        role_weights = SkillTaxonomyService.get_role_weights(target_role)

        # Incorporate JD requirements weights if present
        merged_weights: Dict[str, float] = dict(role_weights)
        for req in top_reqs:
            sid = req.get("skill_id")
            if sid:
                merged_weights[sid] = max(merged_weights.get(sid, 0.1), float(req.get("weight", 0.5)))

        # 3. Identify prerequisite gaps and compute prerequisite urgency
        # If a prerequisite is VERIFIED_GAP or DEVELOPING, it gets an urgency boost (1.5x)
        # and dependent advanced skills are BLOCKED until prerequisite reaches DEVELOPING+.
        blocked_skills: Dict[str, List[str]] = {}
        prereq_boosts: Dict[str, float] = {}

        for sid, prereqs in dag.items():
            for p in prereqs:
                p_state = verified_states.get(p, {})
                p_status = p_state.get("status", "NOT_ASSESSED")
                p_prof = p_state.get("proficiency", 0.0)

                # If prerequisite has verified gap or is unassessed with high importance
                if p_status in ("VERIFIED_GAP", "DEVELOPING") or (p_status == "NOT_ASSESSED" and merged_weights.get(p, 0.0) >= 0.2):
                    prereq_boosts[p] = 1.6  # Boost prerequisite priority
                    if p_prof < 60.0:
                        if sid not in blocked_skills:
                            blocked_skills[sid] = []
                        blocked_skills[sid].append(p)

        # 4. Compute priority score per candidate skill
        candidate_items: List[Dict[str, Any]] = []
        deferred_items: List[Dict[str, Any]] = []

        for sid, skill_info in SKILL_CATALOG.items():
            weight = merged_weights.get(sid, 0.05)
            # Skip completely irrelevant skills for this role if weight is zero
            if weight <= 0.05 and sid not in merged_weights and sid not in verified_states:
                continue

            state = verified_states.get(sid, {})
            status = state.get("status", "NOT_ASSESSED")
            prof = state.get("proficiency")
            conf = state.get("confidence", 0.5)

            prereq_urgency = prereq_boosts.get(sid, 1.0)

            # Deadline factor
            if is_compressed:
                # In compressed mode (<= 7 days), prioritize top mandatory JD skills and verified gaps
                top_req_ids = [r.get("skill_id") for r in top_reqs if float(r.get("weight", 0.0)) >= 0.2]
                is_mandatory = (weight >= 0.85) or (sid in top_req_ids)
                if is_mandatory or status == "VERIFIED_GAP":
                    deadline_factor = 1.7  # Must-have core skills prioritized
                elif status != "VERIFIED_GAP":
                    # Lower-priority or preferred skills deferred
                    deferred_items.append({
                        "skill_id": sid,
                        "skill_name": skill_info.get("name", sid),
                        "weight": weight,
                        "status": status,
                        "reason": "deferred_due_to_imminent_interview",
                        "reason_description": f"Excluded from {days_left}-day sprint to focus exclusively on critical core requirements."
                    })
                    continue
                else:
                    deadline_factor = 1.0
            else:
                deadline_factor = 1.0

            prio, reason_code = cls.calculate_skill_priority(
                role_importance=weight,
                proficiency=prof,
                confidence=conf,
                status=status,
                prerequisite_urgency=prereq_urgency,
                deadline_factor=deadline_factor
            )

            # Check blocking condition
            is_blocked = (sid in blocked_skills)
            blockers = blocked_skills.get(sid, [])

            # Evidence IDs attached to this skill
            evidence_ids = ev_map.get(sid, [])

            # Determine appropriate activity types based on status
            activities = cls._derive_activities_for_skill(
                skill_id=sid,
                skill_info=skill_info,
                status=status,
                proficiency=prof,
                priority=prio,
                reason_code=reason_code,
                evidence_ids=evidence_ids,
                is_blocked=is_blocked,
                blocked_by=blockers,
                is_compressed=is_compressed
            )
            candidate_items.extend(activities)

        # 5. Deterministic Sort: Unblocked first, highest priority first
        candidate_items.sort(key=lambda item: (
            1 if item.get("is_blocked") else 0,
            -item.get("priority", 0.0),
            item.get("skill_id")
        ))

        # 6. Bin-Packing into days (sum of duration <= daily_minutes * 1.10)
        daily_schedule: Dict[int, List[Dict[str, Any]]] = {d: [] for d in range(1, days_left + 1)}
        daily_minutes_spent: Dict[int, int] = {d: 0 for d in range(1, days_left + 1)}
        all_scheduled_activities: List[Dict[str, Any]] = []

        unscheduled_items: List[Dict[str, Any]] = []

        current_day = 1
        for item in candidate_items:
            duration = item.get("estimated_minutes", 30)

            # Find earliest day with capacity that is not blocked
            placed = False
            for d in range(current_day, days_left + 1):
                # If item is blocked by prerequisites, ensure it is placed AFTER prerequisite days
                if item.get("is_blocked"):
                    # Blocked items can only be scheduled in later half of the horizon
                    min_allowed_day = max(2, (days_left // 2) + 1)
                    if d < min_allowed_day:
                        continue

                if daily_minutes_spent[d] + duration <= max_daily_budget:
                    item_copy = dict(item)
                    item_copy["id"] = f"act_{uuid.uuid4().hex[:10]}"
                    item_copy["day_number"] = d
                    item_copy["order_in_day"] = len(daily_schedule[d]) + 1
                    daily_schedule[d].append(item_copy)
                    daily_minutes_spent[d] += duration
                    all_scheduled_activities.append(item_copy)
                    placed = True
                    break

            if not placed:
                # Carry over / overflow
                unscheduled_items.append({
                    **item,
                    "rescheduled_from": "capacity_overflow",
                    "reason": "Exceeded total horizon study capacity."
                })

        return {
            "target_role": target_role,
            "horizon_days": days_left,
            "daily_minutes_budget": daily_minutes,
            "max_daily_budget_with_buffer": max_daily_budget,
            "is_compressed_deadline": is_compressed,
            "total_activities_scheduled": len(all_scheduled_activities),
            "daily_schedule": daily_schedule,
            "activities": all_scheduled_activities,
            "deferred_skills": deferred_items,
            "unscheduled_overflow": unscheduled_items,
            "blocked_skills_count": len(blocked_skills)
        }

    @classmethod
    def _derive_activities_for_skill(
        cls,
        skill_id: str,
        skill_info: Dict[str, Any],
        status: str,
        proficiency: Optional[float],
        priority: float,
        reason_code: str,
        evidence_ids: List[str],
        is_blocked: bool,
        blocked_by: List[str],
        is_compressed: bool
    ) -> List[Dict[str, Any]]:
        """
        Derives concrete, measurable activity items for a given skill based on status.
        Suppression: Mastered/demonstrated skills do not receive full lessons;
        they receive short revision retrieval slots only.
        """
        sname = skill_info.get("name", skill_id.replace("_", " ").title())
        activities: List[Dict[str, Any]] = []

        # Case 1: NOT_ASSESSED -> Assessment scheduled first
        if status == "NOT_ASSESSED" or proficiency is None:
            activities.append({
                "skill_id": skill_id,
                "skill_name": sname,
                "title": f"Diagnostic Assessment: {sname} Calibration",
                "learning_objective": f"Calibrate baseline competency in {sname} via rubric-evaluated technical turn.",
                "activity_type": ACTIVITY_ASSESSMENT,
                "difficulty": "intermediate",
                "estimated_minutes": 25,
                "prerequisites": skill_info.get("prerequisites", []),
                "is_blocked": is_blocked,
                "blocked_by": blocked_by,
                "priority": priority + 0.5,
                "reason_code": REASON_UNASSESSED_PROBE,
                "evidence_ids": evidence_ids
            })
            return activities

        # Case 2: MASTERED or DEMONSTRATED -> SUPPRESS LESSONS; schedule short revision only
        if status in ("MASTERED", "DEMONSTRATED") and (proficiency and proficiency >= 60.0):
            activities.append({
                "skill_id": skill_id,
                "skill_name": sname,
                "title": f"Spaced Revision: {sname} Synthesis",
                "learning_objective": f"Maintain demonstrated retention in {sname} with active retrieval quiz.",
                "activity_type": ACTIVITY_REVISION,
                "difficulty": "advanced" if status == "MASTERED" else "intermediate",
                "estimated_minutes": 15,
                "prerequisites": skill_info.get("prerequisites", []),
                "is_blocked": False,
                "blocked_by": [],
                "priority": max(0.05, priority * 0.4),
                "reason_code": REASON_SPACED_REVISION,
                "evidence_ids": evidence_ids
            })
            return activities

        # Case 3: VERIFIED_GAP -> High priority deep remediation + coding drill
        if status == "VERIFIED_GAP" or (proficiency and proficiency < 60.0):
            # 1. Lesson
            activities.append({
                "skill_id": skill_id,
                "skill_name": sname,
                "title": f"Targeted Remediation: {sname} Core Invariants",
                "learning_objective": f"Address verified gap in {sname} by mastering fundamental invariants and boundary conditions.",
                "activity_type": ACTIVITY_LESSON,
                "difficulty": "beginner" if (proficiency and proficiency < 40.0) else "intermediate",
                "estimated_minutes": 30,
                "prerequisites": skill_info.get("prerequisites", []),
                "is_blocked": is_blocked,
                "blocked_by": blocked_by,
                "priority": priority + 1.0,
                "reason_code": REASON_VERIFIED_GAP,
                "evidence_ids": evidence_ids
            })
            # 2. Coding drill or practice assignment
            activities.append({
                "skill_id": skill_id,
                "skill_name": sname,
                "title": f"Sandboxed Verification Drill: {sname}",
                "learning_objective": f"Implement and pass hidden test suite for {sname} to prove gap closure.",
                "activity_type": ACTIVITY_CODING_DRILL,
                "difficulty": "intermediate",
                "estimated_minutes": 30,
                "prerequisites": skill_info.get("prerequisites", []),
                "is_blocked": is_blocked,
                "blocked_by": blocked_by,
                "priority": priority + 0.8,
                "reason_code": REASON_VERIFIED_GAP,
                "evidence_ids": evidence_ids
            })
            return activities

        # Case 4: DEVELOPING -> Practice set and assignment
        activities.append({
            "skill_id": skill_id,
            "skill_name": sname,
            "title": f"Applied Practice: {sname} Implementation",
            "learning_objective": f"Advance competency in {sname} toward interview readiness with structured practice.",
            "activity_type": ACTIVITY_PRACTICE_SET,
            "difficulty": "intermediate",
            "estimated_minutes": 30,
            "prerequisites": skill_info.get("prerequisites", []),
            "is_blocked": is_blocked,
            "blocked_by": blocked_by,
            "priority": priority,
            "reason_code": reason_code,
            "evidence_ids": evidence_ids
        })
        return activities
