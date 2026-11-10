"""
Adaptive Decision Rules Engine for PrepFly Adaptive AI Interview Mentor.
Deterministic rule table mapping candidate evidence and trigger events to exact plan mutations.
Enforces Section 7 decision rules with zero ambiguity:
1. Prereq failure
2. Consistent strong performance
3. Incomplete assignment
4. Recurring mistake tag >= 2
5. Mastered skill near deadline
6. Missed day
7. Interview date moved closer
8. Insufficient evidence
9. Repeated failure (>= 3 attempts)
10. Stale evidence (> 30 days)
"""

from typing import Dict, List, Optional, Any, Callable
import copy
from datetime import datetime, timezone, timedelta

from services.skill_taxonomy_service import SkillTaxonomyService
from services.curriculum_engine import (
    ACTIVITY_ASSESSMENT,
    ACTIVITY_LESSON,
    ACTIVITY_PRACTICE_SET,
    ACTIVITY_ASSIGNMENT,
    ACTIVITY_CODING_DRILL,
    ACTIVITY_MOCK_INTERVIEW,
    ACTIVITY_REVISION
)

# Rule Identifiers
RULE_PREREQ_FAILURE = "RULE_PREREQ_FAILURE"
RULE_CONSISTENT_STRONG_PERFORMANCE = "RULE_CONSISTENT_STRONG_PERFORMANCE"
RULE_INCOMPLETE_ASSIGNMENT = "RULE_INCOMPLETE_ASSIGNMENT"
RULE_RECURRING_MISTAKE = "RULE_RECURRING_MISTAKE"
RULE_MASTERED_NEAR_DEADLINE = "RULE_MASTERED_NEAR_DEADLINE"
RULE_MISSED_DAY = "RULE_MISSED_DAY"
RULE_INTERVIEW_DATE_MOVED_CLOSER = "RULE_INTERVIEW_DATE_MOVED_CLOSER"
RULE_INSUFFICIENT_EVIDENCE = "RULE_INSUFFICIENT_EVIDENCE"
RULE_REPEATED_FAILURE = "RULE_REPEATED_FAILURE"
RULE_STALE_EVIDENCE = "RULE_STALE_EVIDENCE"


class AdaptiveDecisionRulesEngine:
    """Deterministic, pure execution engine evaluating Section 7 adaptive decision rules."""

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 1: PREREQUISITE FAILURE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_prereq_failure(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        target_skill: str,
        failed_score: float,
        prerequisite_skill: str
    ) -> Dict[str, Any]:
        """
        Condition: Candidate fails evaluation on skill B, but prerequisite A is weak (VERIFIED_GAP / DEVELOPING).
        Action: Boost priority of A; block lessons on B until A reaches DEVELOPING+; schedule remediation drill for A.
        """
        updated_states = copy.deepcopy(skill_states)
        plan = copy.deepcopy(current_plan)
        activities = plan.get("activities", [])

        # 1. Block lessons on target_skill (B)
        blocked_count = 0
        for act in activities:
            if act.get("skill_id") == target_skill and act.get("activity_type") in (ACTIVITY_LESSON, ACTIVITY_PRACTICE_SET, ACTIVITY_ASSIGNMENT):
                act["status"] = "BLOCKED"
                act["blocked_by"] = prerequisite_skill
                act["blocking_reason"] = f"Prerequisite {prerequisite_skill} requires mastery before advancing."
                blocked_count += 1

        # 2. Add remediation drill for prerequisite_skill (A) to Day 1
        remediation_activity = {
            "id": f"act_remed_{prerequisite_skill}",
            "title": f"Targeted Prerequisite Remediation: {prerequisite_skill.replace('_', ' ').title()}",
            "skill_id": prerequisite_skill,
            "skill_name": prerequisite_skill.replace("_", " ").title(),
            "activity_type": ACTIVITY_CODING_DRILL,
            "difficulty": "Intermediate",
            "estimated_minutes": 25,
            "day_number": 1,
            "status": "PENDING",
            "reason_code": "PREREQUISITE_BOOST",
            "deliverable": "Passing hidden test assertions for core prerequisite invariants."
        }
        activities.insert(0, remediation_activity)
        plan["activities"] = activities

        diff = {
            "rule_id": RULE_PREREQ_FAILURE,
            "added": [remediation_activity["title"]],
            "blocked": [f"{target_skill} (blocked by {prerequisite_skill})"],
            "remediation_scheduled": prerequisite_skill
        }

        return {
            "rule_id": RULE_PREREQ_FAILURE,
            "is_applied": True,
            "updated_skill_states": updated_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Blocked {blocked_count} dependent lessons on {target_skill}; scheduled remediation for {prerequisite_skill}."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 2: CONSISTENT STRONG PERFORMANCE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_consistent_strong_performance(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        skill_id: str,
        consecutive_scores: List[float]
    ) -> Dict[str, Any]:
        """
        Condition: Candidate scores >= 85% on 2 consecutive evaluations of skill X.
        Action: Mark X as MASTERED; remove remaining beginner/intermediate lessons on X; insert one advanced revision slot near interview.
        """
        updated_states = copy.deepcopy(skill_states)
        plan = copy.deepcopy(current_plan)
        old_activities = plan.get("activities", [])

        # 1. Update candidate skill state to MASTERED
        for s in updated_states:
            if s.get("skill_id") == skill_id:
                s["status"] = "MASTERED"
                s["proficiency"] = max([s.get("proficiency", 0.0)] + consecutive_scores)
                s["confidence"] = 0.95

        # 2. Remove remaining beginner / intermediate lessons on X
        removed_titles = []
        filtered_activities = []
        for act in old_activities:
            if act.get("skill_id") == skill_id and act.get("difficulty", "").lower() in ("beginner", "intermediate") and act.get("activity_type") in (ACTIVITY_LESSON, ACTIVITY_PRACTICE_SET):
                removed_titles.append(act.get("title"))
            else:
                filtered_activities.append(act)

        # 3. Insert one 15-min advanced revision slot near the interview (final day)
        horizon = plan.get("horizon_days", 30)
        revision_activity = {
            "id": f"act_rev_{skill_id}",
            "title": f"Spaced Retrieval Sprint: {skill_id.replace('_', ' ').title()}",
            "skill_id": skill_id,
            "activity_type": ACTIVITY_REVISION,
            "difficulty": "Advanced",
            "estimated_minutes": 15,
            "day_number": max(1, horizon - 1),
            "status": "PENDING",
            "reason_code": "SPACED_REVISION",
            "deliverable": "Rapid active recall quiz testing core failure modes."
        }
        filtered_activities.append(revision_activity)
        plan["activities"] = filtered_activities

        diff = {
            "rule_id": RULE_CONSISTENT_STRONG_PERFORMANCE,
            "status_change": {skill_id: "MASTERED"},
            "removed": removed_titles,
            "added": [revision_activity["title"]]
        }

        return {
            "rule_id": RULE_CONSISTENT_STRONG_PERFORMANCE,
            "is_applied": True,
            "updated_skill_states": updated_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Marked {skill_id} as MASTERED; pruned {len(removed_titles)} elementary lessons; scheduled spaced revision."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 3: INCOMPLETE ASSIGNMENT
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_incomplete_assignment(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        activity_id: str,
        missing_requirements: List[str]
    ) -> Dict[str, Any]:
        """
        Condition: Candidate submits partial work (missed requirements).
        Action: Activity remains in progress with status 'needs_revision'; do not fail the skill; schedule a targeted nudge.
        """
        updated_states = copy.deepcopy(skill_states)
        plan = copy.deepcopy(current_plan)

        # Verify no skill state changed or failed
        for act in plan.get("activities", []):
            if act.get("id") == activity_id:
                act["status"] = "NEEDS_REVISION"
                act["missing_requirements"] = missing_requirements
                act["nudge_message"] = "Your submission is missing required deliverables. Revise and resubmit without penalty."

        diff = {
            "rule_id": RULE_INCOMPLETE_ASSIGNMENT,
            "activity_id": activity_id,
            "new_status": "NEEDS_REVISION",
            "skill_penalized": False,
            "nudge_scheduled": True
        }

        return {
            "rule_id": RULE_INCOMPLETE_ASSIGNMENT,
            "is_applied": True,
            "updated_skill_states": updated_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Activity {activity_id} preserved in progress as NEEDS_REVISION; zero penalty to skill state."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 4: RECURRING MISTAKE (COUNT >= 2)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_recurring_mistake(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        skill_id: str,
        misconception_tag: str,
        occurrences: int,
        initial_modality: str = "coding_drill"
    ) -> Dict[str, Any]:
        """
        Condition: Candidate makes same misconception twice across any activities.
        Action: Schedule a targeted conceptual drill specifically addressing that misconception with a different modality than first used.
        """
        plan = copy.deepcopy(current_plan)
        new_modality = "visual_walkthrough" if initial_modality in ("coding_drill", "assignment") else "interactive_coding"

        drill_activity = {
            "id": f"act_miscon_{misconception_tag}",
            "title": f"Targeted Blindspot Drill: {misconception_tag.replace('_', ' ').title()}",
            "skill_id": skill_id,
            "activity_type": ACTIVITY_LESSON,
            "learning_modality": new_modality,
            "difficulty": "Intermediate",
            "estimated_minutes": 20,
            "day_number": 1,
            "status": "PENDING",
            "reason_code": "RECURRING_MISTAKE_INTERVENTION",
            "deliverable": f"Step-by-step walkthrough analyzing invariant violation in {misconception_tag}."
        }
        plan.get("activities", []).insert(0, drill_activity)

        diff = {
            "rule_id": RULE_RECURRING_MISTAKE,
            "misconception_tag": misconception_tag,
            "occurrences": occurrences,
            "added": [drill_activity["title"]],
            "new_modality": new_modality
        }

        return {
            "rule_id": RULE_RECURRING_MISTAKE,
            "is_applied": True,
            "updated_skill_states": skill_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Scheduled modality-shifted drill ({new_modality}) addressing recurring blindspot '{misconception_tag}'."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 5: MASTERED SKILL NEAR DEADLINE (DAYS_LEFT <= 5)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_mastered_near_deadline(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        mastered_skill_id: str,
        days_left: int
    ) -> Dict[str, Any]:
        """
        Condition: Skill is MASTERED and days_left <= 5.
        Action: Keep only a 15-min retrieval practice session; free capacity for VERIFIED_GAP skills.
        """
        plan = copy.deepcopy(current_plan)
        activities = plan.get("activities", [])
        freed_minutes = 0
        retained_activities = []
        retrieval_slot = None

        for act in activities:
            if act.get("skill_id") == mastered_skill_id:
                if act.get("activity_type") == ACTIVITY_REVISION:
                    retrieval_slot = act
                    retrieval_slot["estimated_minutes"] = 15
                    retained_activities.append(retrieval_slot)
                else:
                    freed_minutes += int(act.get("estimated_minutes", 30))
            else:
                retained_activities.append(act)

        # If no revision slot existed, insert a 15-minute slot
        if not retrieval_slot:
            retrieval_slot = {
                "id": f"act_quick_rev_{mastered_skill_id}",
                "title": f"15-Minute Retrieval Flush: {mastered_skill_id.replace('_', ' ').title()}",
                "skill_id": mastered_skill_id,
                "activity_type": ACTIVITY_REVISION,
                "estimated_minutes": 15,
                "day_number": max(1, days_left),
                "status": "PENDING"
            }
            retained_activities.append(retrieval_slot)

        plan["activities"] = retained_activities

        diff = {
            "rule_id": RULE_MASTERED_NEAR_DEADLINE,
            "skill_id": mastered_skill_id,
            "days_left": days_left,
            "freed_minutes": freed_minutes,
            "retrieval_slot": retrieval_slot["title"]
        }

        return {
            "rule_id": RULE_MASTERED_NEAR_DEADLINE,
            "is_applied": True,
            "updated_skill_states": skill_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Suppressed extensive lessons for {mastered_skill_id}; freed {freed_minutes}m capacity for critical gaps."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 6: MISSED DAY
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_missed_day(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        missed_day_number: int,
        daily_capacity_minutes: int
    ) -> Dict[str, Any]:
        """
        Condition: Candidate did not complete scheduled activities yesterday.
        Action: Carry forward to today; if today's capacity is exceeded, defer lowest-priority activities to the end of the roadmap; notify user.
        """
        plan = copy.deepcopy(current_plan)
        activities = plan.get("activities", [])

        # Find incomplete activities from missed day
        carried_forward = []
        remaining = []
        for act in activities:
            if act.get("day_number") == missed_day_number and act.get("status") not in ("COMPLETED", "completed"):
                act["day_number"] = missed_day_number + 1
                act["rescheduled_from"] = f"Day {missed_day_number}"
                carried_forward.append(act)
            else:
                remaining.append(act)

        # Capacity check for Day missed_day_number + 1
        today_number = missed_day_number + 1
        today_items = [a for a in remaining if a.get("day_number") == today_number] + carried_forward
        total_minutes = sum(int(a.get("estimated_minutes", 30)) for a in today_items)

        deferred_items = []
        if total_minutes > daily_capacity_minutes:
            # Sort by priority ascending (lowest priority deferred first)
            today_items.sort(key=lambda a: float(a.get("priority", 0.5)))
            while total_minutes > daily_capacity_minutes and len(today_items) > 1:
                deferred = today_items.pop(0)
                deferred["day_number"] = plan.get("horizon_days", 30)
                deferred["deferral_reason"] = "Capacity exceeded due to carry-forward from missed day."
                deferred_items.append(deferred)
                total_minutes -= int(deferred.get("estimated_minutes", 30))

        # Reconstruct activities
        other_items = [a for a in remaining if a.get("day_number") != today_number]
        plan["activities"] = today_items + other_items + deferred_items

        diff = {
            "rule_id": RULE_MISSED_DAY,
            "carried_forward_count": len(carried_forward),
            "deferred_count": len(deferred_items),
            "deferred_titles": [d["title"] for d in deferred_items]
        }

        return {
            "rule_id": RULE_MISSED_DAY,
            "is_applied": True,
            "updated_skill_states": skill_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Carried forward {len(carried_forward)} activities; deferred {len(deferred_items)} low-priority activities to end of roadmap."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 7: INTERVIEW DATE MOVED CLOSER
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_interview_date_moved_closer(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        new_days_left: int
    ) -> Dict[str, Any]:
        """
        Condition: days_left shrinks significantly (e.g. <= 7 days).
        Action: Drop non-critical skills; mark them 'deferred due to time constraints'; focus 100% on high-importance gaps + mock interviews.
        """
        plan = copy.deepcopy(current_plan)
        activities = plan.get("activities", [])
        plan["horizon_days"] = new_days_left
        plan["is_compressed_deadline"] = True

        critical_skills = {
            s["skill_id"] for s in skill_states if s.get("status") == "VERIFIED_GAP"
        }

        active_activities = []
        deferred_activities = []
        for act in activities:
            sid = act.get("skill_id")
            atype = act.get("activity_type")
            is_critical = (sid in critical_skills) or (atype in (ACTIVITY_MOCK_INTERVIEW, ACTIVITY_REVISION))
            if is_critical:
                act["day_number"] = min(act.get("day_number", 1), new_days_left)
                active_activities.append(act)
            else:
                act["status"] = "DEFERRED"
                act["deferral_reason"] = "Deferred due to acute time constraints before interview."
                deferred_activities.append(act)

        plan["activities"] = active_activities
        plan["deferred_activities"] = deferred_activities

        diff = {
            "rule_id": RULE_INTERVIEW_DATE_MOVED_CLOSER,
            "new_days_left": new_days_left,
            "retained_count": len(active_activities),
            "deferred_count": len(deferred_activities)
        }

        return {
            "rule_id": RULE_INTERVIEW_DATE_MOVED_CLOSER,
            "is_applied": True,
            "updated_skill_states": skill_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Compressed horizon to {new_days_left} days; deferred {len(deferred_activities)} optional skills to focus on critical gaps."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 8: INSUFFICIENT EVIDENCE (CLAIMED WITH 0 EVALUATIONS)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_insufficient_evidence(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        claimed_skill_id: str
    ) -> Dict[str, Any]:
        """
        Condition: User claims skill on profile but has 0 evaluations / 0 samples.
        Action: Schedule diagnostic assessment first; do not schedule advanced practice until baseline is established.
        """
        plan = copy.deepcopy(current_plan)
        activities = plan.get("activities", [])

        # Remove any advanced drills/lessons on claimed_skill_id
        filtered = [a for a in activities if not (a.get("skill_id") == claimed_skill_id and a.get("activity_type") != ACTIVITY_ASSESSMENT)]

        # Insert mandatory 5-minute diagnostic assessment as Step 1
        diagnostic_activity = {
            "id": f"act_diag_{claimed_skill_id}",
            "title": f"Diagnostic Baseline Assessment: {claimed_skill_id.replace('_', ' ').title()}",
            "skill_id": claimed_skill_id,
            "activity_type": ACTIVITY_ASSESSMENT,
            "difficulty": "Intermediate",
            "estimated_minutes": 15,
            "day_number": 1,
            "status": "PENDING",
            "reason_code": "UNASSESSED_PROBE",
            "deliverable": "Baseline calibration turn testing core invariants."
        }
        filtered.insert(0, diagnostic_activity)
        plan["activities"] = filtered

        diff = {
            "rule_id": RULE_INSUFFICIENT_EVIDENCE,
            "claimed_skill": claimed_skill_id,
            "diagnostic_scheduled": diagnostic_activity["title"],
            "advanced_lessons_blocked": True
        }

        return {
            "rule_id": RULE_INSUFFICIENT_EVIDENCE,
            "is_applied": True,
            "updated_skill_states": skill_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Scheduled mandatory diagnostic probe for claimed unverified skill {claimed_skill_id}."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 9: REPEATED FAILURE (CONSECUTIVE FAILURES >= 3)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_repeated_failure(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        skill_id: str,
        consecutive_failures: int
    ) -> Dict[str, Any]:
        """
        Condition: Candidate fails 3 consecutive attempts on skill X.
        Action: Shift modality (e.g. from coding drill to visual/step-by-step walkthrough); lower initial difficulty; schedule human-style mentor intervention.
        """
        plan = copy.deepcopy(current_plan)
        activities = plan.get("activities", [])

        interventions = []
        for act in activities:
            if act.get("skill_id") == skill_id:
                act["difficulty"] = "Beginner"
                act["learning_modality"] = "visual_walkthrough"
                act["mentor_intervention_flag"] = True
                act["title"] = f"Visual Conceptual Walkthrough: {skill_id.replace('_', ' ').title()} (Foundations)"
                interventions.append(act["title"])

        diff = {
            "rule_id": RULE_REPEATED_FAILURE,
            "skill_id": skill_id,
            "consecutive_failures": consecutive_failures,
            "new_modality": "visual_walkthrough",
            "new_difficulty": "Beginner",
            "interventions": interventions
        }

        return {
            "rule_id": RULE_REPEATED_FAILURE,
            "is_applied": True,
            "updated_skill_states": skill_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Demoted difficulty to Beginner; shifted modality to visual_walkthrough with active mentor intervention for {skill_id}."
        }

    # ──────────────────────────────────────────────────────────────────────────
    # RULE 10: STALE EVIDENCE (> 30 DAYS OLD)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def apply_rule_stale_evidence(
        cls,
        candidate_profile: Dict[str, Any],
        skill_states: List[Dict[str, Any]],
        current_plan: Dict[str, Any],
        skill_id: str,
        days_since_assessment: int
    ) -> Dict[str, Any]:
        """
        Condition: Skill last evaluated > 30 days ago, was MASTERED.
        Action: Decay confidence; schedule a short re-assessment; do not silently assume mastery is retained.
        """
        updated_states = copy.deepcopy(skill_states)
        plan = copy.deepcopy(current_plan)

        # 1. Decay confidence in skill state
        old_conf = 0.95
        new_conf = 0.50
        for s in updated_states:
            if s.get("skill_id") == skill_id:
                old_conf = float(s.get("confidence", 0.95))
                new_conf = round(max(0.40, old_conf - 0.45), 2)
                s["confidence"] = new_conf
                s["is_stale"] = True

        # 2. Schedule short re-assessment
        reassessment_activity = {
            "id": f"act_reassess_{skill_id}",
            "title": f"Freshness Re-assessment: {skill_id.replace('_', ' ').title()}",
            "skill_id": skill_id,
            "activity_type": ACTIVITY_ASSESSMENT,
            "difficulty": "Intermediate",
            "estimated_minutes": 15,
            "day_number": 1,
            "status": "PENDING",
            "reason_code": "STALE_EVIDENCE_REASSESSMENT",
            "deliverable": "10-minute diagnostic verifying retention of invariants after 30+ days."
        }
        plan.get("activities", []).insert(0, reassessment_activity)

        diff = {
            "rule_id": RULE_STALE_EVIDENCE,
            "skill_id": skill_id,
            "days_elapsed": days_since_assessment,
            "confidence_decay": f"{old_conf} -> {new_conf}",
            "scheduled_reassessment": reassessment_activity["title"]
        }

        return {
            "rule_id": RULE_STALE_EVIDENCE,
            "is_applied": True,
            "updated_skill_states": updated_states,
            "updated_plan": plan,
            "diff": diff,
            "action_summary": f"Decayed confidence for stale skill {skill_id} ({old_conf} -> {new_conf}); scheduled freshness re-assessment."
        }

