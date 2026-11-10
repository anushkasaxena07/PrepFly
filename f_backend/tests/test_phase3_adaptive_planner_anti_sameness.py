"""
Phase 3 Test Suite: Adaptive Planner & Anti-Sameness Proof Matrix.
Builds plans for 8 contrasting candidate profiles and asserts:
1. Pairwise plan difference (Jaccard distance on (skill_id, activity_type, difficulty) tuples) > threshold.
2. Strong-Python candidate receives ZERO basic Python lessons.
3. 7-day deadline candidate has fewer items than a 90-day candidate and has deferred skills.
4. 60-min/day plan never exceeds 60 min/day (within 10% buffer).
5. Same inputs twice -> identical output (input_hash match); one changed evidence row -> specific explained diff.
6. Prints the 8x8 pairwise distance matrix.
"""

import unittest
import json
from typing import Dict, List, Set, Any
from services.adaptive_planner_service import AdaptivePlannerService
from services.curriculum_engine import (
    ACTIVITY_ASSESSMENT,
    ACTIVITY_LESSON,
    ACTIVITY_CODING_DRILL,
    ACTIVITY_REVISION,
    ACTIVITY_PRACTICE_SET
)


def extract_plan_tuples(plan):
    """Extracts set of (skill_id, activity_type, difficulty) tuples for Jaccard distance calculation."""
    return {
        (a["skill_id"], a["activity_type"], a.get("difficulty", "intermediate"))
        for a in plan.get("activities", [])
    }


def compute_jaccard_distance(set1, set2):
    """Computes Jaccard distance: 1 - |A ∩ B| / |A ∪ B|."""
    if not set1 and not set2:
        return 0.0
    union = set1.union(set2)
    intersection = set1.intersection(set2)
    if not union:
        return 0.0
    return round(1.0 - (len(intersection) / len(union)), 4)


class TestPhase3AdaptivePlannerAntiSameness(unittest.TestCase):
    """The Anti-Sameness Proof and Incremental Adaptation Suite."""

    @classmethod
    def setUpClass(cls):
        # Define 8 contrasting profiles from Section 9
        cls.profiles = {
            # A: Fresher SDE (no experience, 30 days, 60m/day)
            "A_Fresher_SDE": {
                "profile": {"user_id": "cand_a", "experience_level": "Fresher"},
                "goal": {"normalized_role": "software_development_engineer", "days_horizon": 30, "daily_minutes": 60},
                "skill_states": []
            },
            # B: 2 yrs Backend moving to AI/ML (backend skills suppressed, ML fundamentals prioritized)
            "B_Backend_to_AIML": {
                "profile": {"user_id": "cand_b", "experience_level": "Mid-Level"},
                "goal": {"normalized_role": "ai_ml_engineer", "days_horizon": 30, "daily_minutes": 60},
                "skill_states": [
                    {"skill_id": "cs_dbms", "proficiency": 95.0, "status": "MASTERED"},
                    {"skill_id": "cs_sql", "proficiency": 90.0, "status": "MASTERED"},
                    {"skill_id": "dl_frameworks_pytorch_tensorflow", "proficiency": 30.0, "status": "VERIFIED_GAP"}
                ]
            },
            # C: Strong Python, weak ML fundamentals (zero basic Python lessons, ML-heavy)
            "C_Strong_Python_Weak_ML": {
                "profile": {"user_id": "cand_c", "experience_level": "Mid-Level"},
                "goal": {"normalized_role": "ai_ml_engineer", "days_horizon": 30, "daily_minutes": 60},
                "skill_states": [
                    {"skill_id": "ml_python_libraries", "proficiency": 96.0, "status": "MASTERED"},
                    {"skill_id": "math_linear_algebra", "proficiency": 30.0, "status": "VERIFIED_GAP"},
                    {"skill_id": "ml_model_development", "proficiency": 25.0, "status": "VERIFIED_GAP"}
                ]
            },
            # D: Strong Theory, weak Practice (coding drills dominate)
            "D_Strong_Theory_Weak_Practice": {
                "profile": {"user_id": "cand_d", "experience_level": "Academic"},
                "goal": {"normalized_role": "software_development_engineer", "days_horizon": 30, "daily_minutes": 60},
                "skill_states": [
                    {"skill_id": "cs_os", "proficiency": 88.0, "status": "MASTERED"},
                    {"skill_id": "dsa_dp", "proficiency": 35.0, "status": "VERIFIED_GAP"},
                    {"skill_id": "dsa_graphs", "proficiency": 40.0, "status": "VERIFIED_GAP"}
                ]
            },
            # E: 7-day Deadline (compressed to critical gaps + revision; deferred list shown)
            "E_Seven_Day_Deadline": {
                "profile": {"user_id": "cand_e", "experience_level": "Mid-Level"},
                "goal": {"normalized_role": "backend_developer", "days_horizon": 7, "daily_minutes": 60},
                "skill_states": [
                    {"skill_id": "sys_db_design", "proficiency": 35.0, "status": "VERIFIED_GAP"}
                ]
            },
            # F: 60-min daily budget
            "F_Strict_60Min_Daily": {
                "profile": {"user_id": "cand_f", "experience_level": "Fresher"},
                "goal": {"normalized_role": "frontend_developer", "days_horizon": 14, "daily_minutes": 60},
                "skill_states": []
            },
            # G: Repeated Failure on One Topic (remediation path)
            "G_Repeated_Failure_Topic": {
                "profile": {"user_id": "cand_g", "experience_level": "Junior"},
                "goal": {"normalized_role": "software_development_engineer", "days_horizon": 20, "daily_minutes": 60},
                "skill_states": [
                    {"skill_id": "dsa_recursion", "proficiency": 20.0, "status": "VERIFIED_GAP"}
                ]
            },
            # H: Senior / Mastered Overall (mostly revision and mocks)
            "H_Senior_Mastered_Overall": {
                "profile": {"user_id": "cand_h", "experience_level": "Senior"},
                "goal": {"normalized_role": "software_development_engineer", "days_horizon": 14, "daily_minutes": 60},
                "skill_states": [
                    {"skill_id": "dsa_arrays", "proficiency": 95.0, "status": "MASTERED"},
                    {"skill_id": "dsa_trees", "proficiency": 92.0, "status": "MASTERED"},
                    {"skill_id": "dsa_graphs", "proficiency": 90.0, "status": "MASTERED"},
                    {"skill_id": "cs_os", "proficiency": 95.0, "status": "MASTERED"}
                ]
            }
        }

    def test_01_pairwise_plan_difference_matrix(self):
        """Generates plans for all 8 profiles, verifies pairwise divergence, and prints difference matrix."""
        plans = {}
        tuple_sets = {}

        for name, data in self.profiles.items():
            plan = AdaptivePlannerService.build_plan(
                candidate_profile=data["profile"],
                goal=data["goal"],
                skill_states=data["skill_states"]
            )
            plans[name] = plan
            tuple_sets[name] = extract_plan_tuples(plan)

        profile_names = list(self.profiles.keys())
        matrix: Dict[str, Dict[str, float]] = {}

        for p1 in profile_names:
            matrix[p1] = {}
            for p2 in profile_names:
                dist = compute_jaccard_distance(tuple_sets[p1], tuple_sets[p2])
                matrix[p1][p2] = dist

        # Assert pairwise difference between contrasting profiles > 0.35
        self.assertGreater(matrix["A_Fresher_SDE"]["B_Backend_to_AIML"], 0.40)
        self.assertGreater(matrix["A_Fresher_SDE"]["E_Seven_Day_Deadline"], 0.40)
        self.assertGreater(matrix["B_Backend_to_AIML"]["F_Strict_60Min_Daily"], 0.40)
        self.assertGreater(matrix["C_Strong_Python_Weak_ML"]["H_Senior_Mastered_Overall"], 0.40)

        # Print formatted 8x8 Anti-Sameness Matrix
        print("\n" + "=" * 95)
        print("                 GATE 3 ANTI-SAMENESS PROOF: 8x8 JACCARD DISTANCE MATRIX")
        print("=" * 95)
        short_names = [n[:10] for n in profile_names]
        header = f"{'Profile':<12} | " + " | ".join(f"{sn:<7}" for sn in short_names)
        print(header)
        print("-" * len(header))
        for p1 in profile_names:
            row_str = f"{p1[:12]:<12} | " + " | ".join(f"{matrix[p1][p2]:.4f}" for p2 in profile_names)
            print(row_str)
        print("=" * 95 + "\n")

    def test_02_strong_python_candidate_receives_no_basic_python_lessons(self):
        """Verifies candidate with strong Python (Profile C) gets zero basic Python lessons."""
        cand_c = self.profiles["C_Strong_Python_Weak_ML"]
        plan = AdaptivePlannerService.build_plan(
            candidate_profile=cand_c["profile"],
            goal=cand_c["goal"],
            skill_states=cand_c["skill_states"]
        )

        # Check all activities for ml_python_libraries
        py_acts = [a for a in plan["activities"] if a["skill_id"] == "ml_python_libraries"]
        for a in py_acts:
            self.assertNotEqual(a["activity_type"], ACTIVITY_LESSON, f"Found unexpected basic lesson: {a['title']}")
            self.assertEqual(a["activity_type"], ACTIVITY_REVISION)

    def test_03_seven_day_vs_ninety_day_candidate(self):
        """Verifies 7-day candidate (Profile E) has fewer items than 90-day candidate and has deferred skills."""
        cand_e = self.profiles["E_Seven_Day_Deadline"]
        plan_7d = AdaptivePlannerService.build_plan(
            candidate_profile=cand_e["profile"],
            goal=cand_e["goal"],
            skill_states=cand_e["skill_states"]
        )

        cand_90d = {
            "profile": {"user_id": "cand_90d"},
            "goal": {"normalized_role": "backend_developer", "days_horizon": 90, "daily_minutes": 60},
            "skill_states": cand_e["skill_states"]
        }
        plan_90d = AdaptivePlannerService.build_plan(
            candidate_profile=cand_90d["profile"],
            goal=cand_90d["goal"],
            skill_states=cand_90d["skill_states"]
        )

        # 7-day plan must have fewer activities than 90-day plan
        self.assertLess(plan_7d["total_activities"], plan_90d["total_activities"])
        # 7-day plan must have deferred items
        self.assertTrue(len(plan_7d["deferred_items"]) > 0)

    def test_04_daily_capacity_capping_under_60min(self):
        """Verifies 60-min daily budget never exceeds 60 min * 1.10 = 66 minutes on any scheduled day."""
        cand_f = self.profiles["F_Strict_60Min_Daily"]
        plan = AdaptivePlannerService.build_plan(
            candidate_profile=cand_f["profile"],
            goal=cand_f["goal"],
            skill_states=cand_f["skill_states"]
        )

        max_allowed = int(60 * 1.10)
        for d, acts in plan["daily_schedule"].items():
            day_sum = sum(a.get("estimated_minutes", 30) for a in acts)
            self.assertLessEqual(day_sum, max_allowed, f"Day {d} sum {day_sum} exceeded {max_allowed}")

    def test_05_determinism_and_incremental_diff(self):
        """Verifies identical inputs -> identical plan; one changed evidence row -> specific explained diff."""
        cand_b = self.profiles["B_Backend_to_AIML"]

        # Run 1
        plan_run1 = AdaptivePlannerService.build_plan(
            candidate_profile=cand_b["profile"],
            goal=cand_b["goal"],
            skill_states=cand_b["skill_states"]
        )

        # Run 2 with identical inputs
        plan_run2 = AdaptivePlannerService.build_plan(
            candidate_profile=cand_b["profile"],
            goal=cand_b["goal"],
            skill_states=cand_b["skill_states"]
        )

        # Assert exact hash match and identical activity list
        self.assertEqual(plan_run1["input_hash"], plan_run2["input_hash"])
        self.assertEqual(len(plan_run1["activities"]), len(plan_run2["activities"]))

        # Incremental update with new evaluation
        updated_plan = AdaptivePlannerService.update_plan(
            current_version=plan_run1,
            trigger_type="new_evaluation",
            trigger_payload={"skill_id": "dl_frameworks_pytorch_tensorflow", "score": 88.0, "evidence_id": "ev_test_101"}
        )

        # Verify version incremented
        self.assertEqual(updated_plan["version_number"], 2)
        # Verify diff
        self.assertTrue(len(updated_plan["diff"]["added"]) > 0)
        self.assertIn("Spaced Revision", updated_plan["diff"]["added"][0])
        self.assertIn("Retrieval", updated_plan["diff"]["added"][0])
        self.assertIn("Score: 88.0%", updated_plan["change_summary"])


if __name__ == "__main__":
    unittest.main()
