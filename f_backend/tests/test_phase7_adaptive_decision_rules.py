"""
Tests for Phase 7: Deterministic Adaptive Decision Rules Engine.
Implements 10 unit tests (one per Section 7 rule) verifying before/after states and generated plan diffs:
1. Prereq failure
2. Consistent strong performance
3. Incomplete assignment
4. Recurring mistake tag >= 2
5. Mastered skill near deadline
6. Missed day
7. Interview date moved closer
8. Insufficient evidence
9. Repeated failure (>= 3 attempts)
10. Stale evidence (> 30 days old)
"""

import unittest
from services.adaptive_decision_rules import (
    AdaptiveDecisionRulesEngine,
    RULE_PREREQ_FAILURE,
    RULE_CONSISTENT_STRONG_PERFORMANCE,
    RULE_INCOMPLETE_ASSIGNMENT,
    RULE_RECURRING_MISTAKE,
    RULE_MASTERED_NEAR_DEADLINE,
    RULE_MISSED_DAY,
    RULE_INTERVIEW_DATE_MOVED_CLOSER,
    RULE_INSUFFICIENT_EVIDENCE,
    RULE_REPEATED_FAILURE,
    RULE_STALE_EVIDENCE
)
from services.curriculum_engine import (
    ACTIVITY_LESSON,
    ACTIVITY_ASSIGNMENT,
    ACTIVITY_CODING_DRILL,
    ACTIVITY_REVISION,
    ACTIVITY_MOCK_INTERVIEW,
    ACTIVITY_ASSESSMENT
)


class TestPhase7AdaptiveDecisionRules(unittest.TestCase):
    """Unit tests for the 10 Section 7 deterministic decision rules."""

    def setUp(self):
        self.candidate = {"user_id": "usr_rule_test", "experience_level": "Mid-Level"}

    def test_01_rule_prereq_failure(self):
        """Rule 1: Prereq failure blocks dependent lessons & schedules remediation."""
        skill_states = [
            {"skill_id": "dsa_trees", "status": "VERIFIED_GAP", "proficiency": 40.0},
            {"skill_id": "dsa_graphs", "status": "NOT_ASSESSED", "proficiency": 0.0}
        ]
        plan = {
            "activities": [
                {"id": "act_g1", "skill_id": "dsa_graphs", "title": "Graph BFS/DFS", "activity_type": ACTIVITY_LESSON, "status": "PENDING"},
                {"id": "act_g2", "skill_id": "dsa_graphs", "title": "Dijkstra Drill", "activity_type": ACTIVITY_ASSIGNMENT, "status": "PENDING"}
            ]
        }

        res = AdaptiveDecisionRulesEngine.apply_rule_prereq_failure(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            target_skill="dsa_graphs",
            failed_score=42.0,
            prerequisite_skill="dsa_trees"
        )

        self.assertTrue(res["is_applied"])
        self.assertEqual(res["rule_id"], RULE_PREREQ_FAILURE)

        # Verify dependent lessons blocked
        blocked_acts = [a for a in res["updated_plan"]["activities"] if a.get("status") == "BLOCKED"]
        self.assertEqual(len(blocked_acts), 2)
        self.assertEqual(blocked_acts[0]["blocked_by"], "dsa_trees")

        # Verify remediation scheduled on Day 1
        day_1_act = res["updated_plan"]["activities"][0]
        self.assertEqual(day_1_act["skill_id"], "dsa_trees")
        self.assertEqual(day_1_act["reason_code"], "PREREQUISITE_BOOST")

    def test_02_rule_consistent_strong_performance(self):
        """Rule 2: Consistent scores >= 85% marks MASTERED, removes elementary lessons & adds revision."""
        skill_states = [
            {"skill_id": "ml_model_evaluation", "status": "DEVELOPING", "proficiency": 65.0, "confidence": 0.70}
        ]
        plan = {
            "horizon_days": 30,
            "activities": [
                {"id": "act_m1", "skill_id": "ml_model_evaluation", "title": "Intro to ROC-AUC", "activity_type": ACTIVITY_LESSON, "difficulty": "Beginner"},
                {"id": "act_m2", "skill_id": "ml_model_evaluation", "title": "PR-AUC Practice", "activity_type": ACTIVITY_LESSON, "difficulty": "Intermediate"},
                {"id": "act_o1", "skill_id": "dsa_arrays", "title": "Two Pointer Drill", "activity_type": ACTIVITY_CODING_DRILL, "difficulty": "Intermediate"}
            ]
        }

        res = AdaptiveDecisionRulesEngine.apply_rule_consistent_strong_performance(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            skill_id="ml_model_evaluation",
            consecutive_scores=[88.0, 94.0]
        )

        self.assertTrue(res["is_applied"])
        # Verify skill state upgraded to MASTERED
        self.assertEqual(res["updated_skill_states"][0]["status"], "MASTERED")
        self.assertEqual(res["updated_skill_states"][0]["proficiency"], 94.0)

        # Verify elementary lessons removed
        acts = res["updated_plan"]["activities"]
        elementary_ml = [a for a in acts if a.get("skill_id") == "ml_model_evaluation" and a.get("activity_type") == ACTIVITY_LESSON]
        self.assertEqual(len(elementary_ml), 0)

        # Verify revision slot added near deadline
        rev_acts = [a for a in acts if a.get("activity_type") == ACTIVITY_REVISION and a.get("skill_id") == "ml_model_evaluation"]
        self.assertEqual(len(rev_acts), 1)
        self.assertEqual(rev_acts[0]["day_number"], 29)

    def test_03_rule_incomplete_assignment(self):
        """Rule 3: Incomplete assignment stays NEEDS_REVISION without penalizing skill state."""
        skill_states = [
            {"skill_id": "cs_concurrency", "status": "DEVELOPING", "proficiency": 68.0}
        ]
        plan = {
            "activities": [
                {"id": "act_c1", "skill_id": "cs_concurrency", "title": "Mutex Locks", "status": "PENDING"}
            ]
        }

        res = AdaptiveDecisionRulesEngine.apply_rule_incomplete_assignment(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            activity_id="act_c1",
            missing_requirements=["Deadlock invariant proof", "Runnable unit tests"]
        )

        self.assertTrue(res["is_applied"])
        self.assertFalse(res["diff"]["skill_penalized"])
        self.assertEqual(res["updated_skill_states"][0]["proficiency"], 68.0)

        # Verify activity updated to NEEDS_REVISION
        act = res["updated_plan"]["activities"][0]
        self.assertEqual(act["status"], "NEEDS_REVISION")
        self.assertIn("Deadlock invariant proof", act["missing_requirements"])

    def test_04_rule_recurring_mistake(self):
        """Rule 4: Recurring misconception (>= 2) triggers modality-shifted drill."""
        plan = {"activities": []}
        skill_states = [{"skill_id": "ml_model_evaluation", "status": "DEVELOPING"}]

        res = AdaptiveDecisionRulesEngine.apply_rule_recurring_mistake(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            skill_id="ml_model_evaluation",
            misconception_tag="overfitting_data_leakage",
            occurrences=2,
            initial_modality="coding_drill"
        )

        self.assertTrue(res["is_applied"])
        self.assertEqual(res["diff"]["new_modality"], "visual_walkthrough")

        drill = res["updated_plan"]["activities"][0]
        self.assertEqual(drill["reason_code"], "RECURRING_MISTAKE_INTERVENTION")
        self.assertEqual(drill["learning_modality"], "visual_walkthrough")

    def test_05_rule_mastered_near_deadline(self):
        """Rule 5: Mastered skill with days_left <= 5 retains only 15m retrieval slot, freeing capacity."""
        plan = {
            "activities": [
                {"id": "act_1", "skill_id": "dsa_arrays", "title": "Long Array Lesson", "activity_type": ACTIVITY_LESSON, "estimated_minutes": 45},
                {"id": "act_2", "skill_id": "dsa_arrays", "title": "Array Practice Set", "activity_type": ACTIVITY_ASSIGNMENT, "estimated_minutes": 45},
                {"id": "act_3", "skill_id": "ml_model_evaluation", "title": "Gap Remediation", "estimated_minutes": 30}
            ]
        }
        skill_states = [{"skill_id": "dsa_arrays", "status": "MASTERED"}]

        res = AdaptiveDecisionRulesEngine.apply_rule_mastered_near_deadline(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            mastered_skill_id="dsa_arrays",
            days_left=4
        )

        self.assertTrue(res["is_applied"])
        self.assertEqual(res["diff"]["freed_minutes"], 90)

        # Verify only 15m retrieval slot kept for dsa_arrays
        array_acts = [a for a in res["updated_plan"]["activities"] if a.get("skill_id") == "dsa_arrays"]
        self.assertEqual(len(array_acts), 1)
        self.assertEqual(array_acts[0]["estimated_minutes"], 15)
        self.assertEqual(array_acts[0]["activity_type"], ACTIVITY_REVISION)

    def test_06_rule_missed_day(self):
        """Rule 6: Missed day carries forward and defers lowest priority when capacity exceeded."""
        plan = {
            "horizon_days": 30,
            "activities": [
                {"id": "a1", "title": "Missed High Priority", "day_number": 1, "status": "PENDING", "estimated_minutes": 30, "priority": 0.9},
                {"id": "a2", "title": "Scheduled Today Critical", "day_number": 2, "status": "PENDING", "estimated_minutes": 25, "priority": 0.8},
                {"id": "a3", "title": "Scheduled Today Minor", "day_number": 2, "status": "PENDING", "estimated_minutes": 25, "priority": 0.2}
            ]
        }

        # Daily capacity = 60m. Total needed for Day 2 = 30 + 25 + 25 = 80m. Must defer a3 (25m) to stay <= 60m.
        res = AdaptiveDecisionRulesEngine.apply_rule_missed_day(
            candidate_profile=self.candidate,
            skill_states=[],
            current_plan=plan,
            missed_day_number=1,
            daily_capacity_minutes=60
        )

        self.assertTrue(res["is_applied"])
        self.assertEqual(res["diff"]["carried_forward_count"], 1)
        self.assertEqual(res["diff"]["deferred_count"], 1)
        self.assertIn("Scheduled Today Minor", res["diff"]["deferred_titles"])

    def test_07_rule_interview_date_moved_closer(self):
        """Rule 7: Interview date <= 7 days defers optional skills & focuses 100% on critical gaps."""
        skill_states = [
            {"skill_id": "ml_model_evaluation", "status": "VERIFIED_GAP"},
            {"skill_id": "python_styling", "status": "DEVELOPING"}
        ]
        plan = {
            "activities": [
                {"id": "a1", "skill_id": "ml_model_evaluation", "title": "Imbalanced Metrics", "activity_type": ACTIVITY_CODING_DRILL},
                {"id": "a2", "skill_id": "python_styling", "title": "PEP8 Formatting", "activity_type": ACTIVITY_LESSON},
                {"id": "a3", "skill_id": "general", "title": "Full Mock Simulation", "activity_type": ACTIVITY_MOCK_INTERVIEW}
            ]
        }

        res = AdaptiveDecisionRulesEngine.apply_rule_interview_date_moved_closer(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            new_days_left=5
        )

        self.assertTrue(res["is_applied"])
        self.assertEqual(res["diff"]["deferred_count"], 1)

        # PEP8 Formatting must be deferred
        deferred = res["updated_plan"]["deferred_activities"]
        self.assertEqual(deferred[0]["skill_id"], "python_styling")

        # Critical gap and mock interview must be retained
        retained = res["updated_plan"]["activities"]
        self.assertEqual(len(retained), 2)

    def test_08_rule_insufficient_evidence(self):
        """Rule 8: Claimed skill with 0 evaluations schedules diagnostic assessment before lessons."""
        plan = {
            "activities": [
                {"id": "a1", "skill_id": "cs_concurrency", "title": "Advanced Goroutines", "activity_type": ACTIVITY_ASSIGNMENT}
            ]
        }
        skill_states = [{"skill_id": "cs_concurrency", "status": "NOT_ASSESSED"}]

        res = AdaptiveDecisionRulesEngine.apply_rule_insufficient_evidence(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            claimed_skill_id="cs_concurrency"
        )

        self.assertTrue(res["is_applied"])
        first_act = res["updated_plan"]["activities"][0]
        self.assertEqual(first_act["activity_type"], ACTIVITY_ASSESSMENT)
        self.assertEqual(first_act["reason_code"], "UNASSESSED_PROBE")

    def test_09_rule_repeated_failure(self):
        """Rule 9: Repeated failures (>= 3) shifts modality to visual_walkthrough & demotes difficulty."""
        plan = {
            "activities": [
                {"id": "a1", "skill_id": "dsa_dp", "title": "Hard DP Drill", "difficulty": "Advanced", "activity_type": ACTIVITY_CODING_DRILL}
            ]
        }
        skill_states = [{"skill_id": "dsa_dp", "status": "VERIFIED_GAP"}]

        res = AdaptiveDecisionRulesEngine.apply_rule_repeated_failure(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            skill_id="dsa_dp",
            consecutive_failures=3
        )

        self.assertTrue(res["is_applied"])
        act = res["updated_plan"]["activities"][0]
        self.assertEqual(act["difficulty"], "Beginner")
        self.assertEqual(act["learning_modality"], "visual_walkthrough")
        self.assertTrue(act["mentor_intervention_flag"])

    def test_10_rule_stale_evidence(self):
        """Rule 10: Mastered skill evaluated > 30 days ago decays confidence & schedules re-assessment."""
        skill_states = [
            {"skill_id": "ml_python_libraries", "status": "MASTERED", "confidence": 0.95, "proficiency": 90.0}
        ]
        plan = {"activities": []}

        res = AdaptiveDecisionRulesEngine.apply_rule_stale_evidence(
            candidate_profile=self.candidate,
            skill_states=skill_states,
            current_plan=plan,
            skill_id="ml_python_libraries",
            days_since_assessment=35
        )

        self.assertTrue(res["is_applied"])
        # Confidence must decay
        self.assertLess(res["updated_skill_states"][0]["confidence"], 0.70)
        self.assertTrue(res["updated_skill_states"][0]["is_stale"])

        # Re-assessment scheduled on Day 1
        act = res["updated_plan"]["activities"][0]
        self.assertEqual(act["activity_type"], ACTIVITY_ASSESSMENT)
        self.assertEqual(act["reason_code"], "STALE_EVIDENCE_REASSESSMENT")

        # Print all 10 verified rule transitions for Gate 7
        print("\n" + "=" * 105)
        print("          GATE 7 DETERMINISTIC ADAPTIVE DECISION RULES TABLE & VERIFICATIONS")
        print("=" * 105)
        rules_info = [
            ("RULE 1: Prereq failure", "Candidate fails B, prereq A is weak", "Boost priority of A; block lessons on B; schedule remediation for A"),
            ("RULE 2: Consistent strong", "Scores >= 85% on 2 consecutive evaluations", "Mark MASTERED; prune elementary lessons; insert spaced revision slot"),
            ("RULE 3: Incomplete assignment", "Candidate submits partial work / deliverables", "Status set to NEEDS_REVISION; zero penalty to skill state; schedule nudge"),
            ("RULE 4: Recurring mistake >= 2", "Same misconception committed twice", "Schedule targeted drill with shifted modality (e.g. visual walkthrough)"),
            ("RULE 5: Mastered near deadline", "Skill is MASTERED and days_left <= 5", "Retain 15m retrieval flash only; free capacity for critical gap skills"),
            ("RULE 6: Missed day", "Scheduled activities missed yesterday", "Carry forward; capacity check: defer lowest-priority items to end"),
            ("RULE 7: Interview date closer", "days_left <= 7 days", "Drop optional skills (mark DEFERRED); focus 100% on critical gaps & mocks"),
            ("RULE 8: Insufficient evidence", "Claimed skill on profile with 0 evaluations", "Schedule diagnostic assessment first; block advanced practice"),
            ("RULE 9: Repeated failure >= 3", "Candidate fails 3 consecutive attempts", "Shift modality to visual_walkthrough; demote to Beginner; flag mentor intervention"),
            ("RULE 10: Stale evidence > 30d", "Last evaluated > 30 days ago, was MASTERED", "Decay confidence; schedule 15m freshness re-assessment probe")
        ]
        for r_name, r_cond, r_act in rules_info:
            print(f"• {r_name:<28} | COND: {r_cond:<44} | ACTION: {r_act}")
        print("=" * 105 + "\n")


if __name__ == "__main__":
    unittest.main()

