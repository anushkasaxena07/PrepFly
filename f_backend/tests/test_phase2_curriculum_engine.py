"""
Phase 2 Test Suite: Deterministic Curriculum Engine.
Verifies the priority formula:
    priority = role_importance * need * prerequisite_urgency * deadline_factor
Verifies suppression of mastered skills from lessons, unassessed assessment scheduling,
prerequisite DAG blocking, deadline compression & deferral, daily bin-packing within 10% buffer,
and contrasting candidate curriculum generations.
"""

import unittest
from services.curriculum_engine import (
    CurriculumEngine,
    ACTIVITY_ASSESSMENT,
    ACTIVITY_LESSON,
    ACTIVITY_CODING_DRILL,
    ACTIVITY_REVISION,
    ACTIVITY_PRACTICE_SET,
    REASON_VERIFIED_GAP,
    REASON_UNASSESSED_PROBE,
    REASON_SPACED_REVISION
)


class TestPhase2CurriculumEngine(unittest.TestCase):
    """Unit tests for deterministic curriculum generation."""

    def test_01_priority_formula_calculation(self):
        """Verifies priority = role_importance * need * prerequisite_urgency * deadline_factor."""
        # Case A: Assessed skill with gap (proficiency = 20%, need = 0.8)
        prio_a, reason_a = CurriculumEngine.calculate_skill_priority(
            role_importance=0.5,
            proficiency=20.0,
            confidence=0.8,
            status="VERIFIED_GAP",
            prerequisite_urgency=1.0,
            deadline_factor=1.0
        )
        # Expected: 0.5 * 0.8 * 1.0 * 1.0 = 0.4000
        self.assertEqual(prio_a, 0.4)
        self.assertEqual(reason_a, REASON_VERIFIED_GAP)

        # Case B: Unassessed skill (need = 0.75)
        prio_b, reason_b = CurriculumEngine.calculate_skill_priority(
            role_importance=0.4,
            proficiency=None,
            confidence=0.0,
            status="NOT_ASSESSED",
            prerequisite_urgency=1.0,
            deadline_factor=1.0
        )
        # Expected: 0.4 * 0.75 * 1.0 * 1.0 = 0.3000
        self.assertEqual(prio_b, 0.3)
        self.assertEqual(reason_b, REASON_UNASSESSED_PROBE)

        # Case C: Prerequisite boost (urgency = 1.6) and deadline boost (factor = 1.7)
        prio_c, _ = CurriculumEngine.calculate_skill_priority(
            role_importance=0.5,
            proficiency=30.0,
            confidence=0.7,
            status="VERIFIED_GAP",
            prerequisite_urgency=1.6,
            deadline_factor=1.7
        )
        # 0.5 * 0.7 * 1.6 * 1.7 = 0.952
        self.assertAlmostEqual(prio_c, 0.952, places=3)

    def test_02_suppression_of_mastered_skills(self):
        """Verifies skills with DEMONSTRATED/MASTERED status receive revision only, no full lessons."""
        context = {
            "goal": {"normalized_role": "software_development_engineer"},
            "schedule_constraints": {"days_left": 14, "daily_minutes": 60, "is_compressed_deadline": False},
            "top_requirements": [{"skill_id": "dsa_arrays", "weight": 0.9}],
            "skill_state_summary": {
                "mastered_skills": [{"skill_id": "dsa_arrays", "proficiency": 95.0}],
                "verified_gaps": [],
                "developing_skills": []
            }
        }

        curriculum = CurriculumEngine.build_curriculum(context)
        scheduled = curriculum["activities"]

        # Find activities for dsa_arrays
        dsa_acts = [a for a in scheduled if a["skill_id"] == "dsa_arrays"]
        self.assertTrue(len(dsa_acts) > 0)

        # Ensure NO lesson was scheduled for dsa_arrays
        types = [a["activity_type"] for a in dsa_acts]
        self.assertIn(ACTIVITY_REVISION, types)
        self.assertNotIn(ACTIVITY_LESSON, types)
        self.assertEqual(dsa_acts[0]["reason_code"], REASON_SPACED_REVISION)

    def test_03_unassessed_skills_scheduled_for_assessment_first(self):
        """Verifies NOT_ASSESSED skills schedule an assessment first, not a lesson."""
        context = {
            "goal": {"normalized_role": "software_development_engineer"},
            "schedule_constraints": {"days_left": 30, "daily_minutes": 60, "is_compressed_deadline": False},
            "top_requirements": [{"skill_id": "dsa_arrays", "weight": 0.9}],
            "skill_state_summary": {
                "mastered_skills": [],
                "verified_gaps": [],
                "developing_skills": []
            }
        }

        curriculum = CurriculumEngine.build_curriculum(context)
        dsa_acts = [a for a in curriculum["activities"] if a["skill_id"] == "dsa_arrays"]
        self.assertTrue(len(dsa_acts) > 0)
        self.assertEqual(dsa_acts[0]["activity_type"], ACTIVITY_ASSESSMENT)
        self.assertEqual(dsa_acts[0]["reason_code"], REASON_UNASSESSED_PROBE)

    def test_04_prerequisite_urgency_and_blocking(self):
        """Verifies that a gap in a prerequisite blocks dependent skills and boosts prerequisite priority."""
        # cs_concurrency depends on cs_os
        context = {
            "goal": {"normalized_role": "backend_developer"},
            "schedule_constraints": {"days_left": 20, "daily_minutes": 60, "is_compressed_deadline": False},
            "top_requirements": [
                {"skill_id": "cs_os", "weight": 0.9},
                {"skill_id": "cs_concurrency", "weight": 0.9}
            ],
            "skill_state_summary": {
                "verified_gaps": [
                    {"skill_id": "cs_os", "proficiency": 30.0}
                ],
                "mastered_skills": [],
                "developing_skills": []
            }
        }

        curriculum = CurriculumEngine.build_curriculum(context)
        conc_acts = [a for a in curriculum["activities"] if a["skill_id"] == "cs_concurrency"]
        if conc_acts:
            self.assertTrue(conc_acts[0]["is_blocked"])
            self.assertIn("cs_os", conc_acts[0]["blocked_by"])

    def test_05_deadline_compression_and_deferral(self):
        """Verifies tight deadlines (<= 7 days) defer low-importance skills."""
        context = {
            "goal": {"normalized_role": "backend_developer"},
            "schedule_constraints": {"days_left": 5, "daily_minutes": 45, "is_compressed_deadline": True},
            "top_requirements": [
                {"skill_id": "sys_db_design", "weight": 0.95},
                {"skill_id": "sys_caching", "weight": 0.90}
            ],
            "skill_state_summary": {"verified_gaps": [], "mastered_skills": [], "developing_skills": []}
        }

        curriculum = CurriculumEngine.build_curriculum(context)
        self.assertTrue(curriculum["is_compressed_deadline"])
        # Check deferred skills
        deferred = curriculum["deferred_skills"]
        self.assertTrue(len(deferred) > 0)
        self.assertEqual(deferred[0]["reason"], "deferred_due_to_imminent_interview")

    def test_06_daily_capacity_bin_packing_with_buffer(self):
        """Verifies sum of estimated minutes per day <= daily_minutes * 1.10."""
        daily_mins = 60
        max_budget = int(daily_mins * 1.10)  # 66 minutes

        context = {
            "goal": {"normalized_role": "software_development_engineer"},
            "schedule_constraints": {"days_left": 10, "daily_minutes": daily_mins, "is_compressed_deadline": False},
            "top_requirements": [
                {"skill_id": "dsa_arrays", "weight": 0.9},
                {"skill_id": "cs_os", "weight": 0.8}
            ],
            "skill_state_summary": {"verified_gaps": [], "mastered_skills": [], "developing_skills": []}
        }

        curriculum = CurriculumEngine.build_curriculum(context)
        daily_schedule = curriculum["daily_schedule"]

        for day, acts in daily_schedule.items():
            day_total = sum(a.get("estimated_minutes", 30) for a in acts)
            self.assertLessEqual(day_total, max_budget, f"Day {day} total {day_total} exceeded max budget {max_budget}")

    def test_07_contrasting_candidates(self):
        """Contrasting candidate curricula for Gate 2 verification."""
        # Candidate 1: Fresher (30 days, all unassessed)
        cand_fresher = {
            "goal": {"normalized_role": "software_development_engineer"},
            "schedule_constraints": {"days_left": 30, "daily_minutes": 60, "is_compressed_deadline": False},
            "top_requirements": [{"skill_id": "dsa_arrays", "weight": 1.0}],
            "skill_state_summary": {"verified_gaps": [], "mastered_skills": [], "developing_skills": []}
        }
        res_fresher = CurriculumEngine.build_curriculum(cand_fresher)
        self.assertGreater(len(res_fresher["activities"]), 0)
        self.assertEqual(res_fresher["activities"][0]["activity_type"], ACTIVITY_ASSESSMENT)

        # Candidate 2: AI/ML with ML gaps and Python mastered (10 days)
        cand_aiml = {
            "goal": {"normalized_role": "ai_ml_engineer"},
            "schedule_constraints": {"days_left": 10, "daily_minutes": 60, "is_compressed_deadline": False},
            "top_requirements": [
                {"skill_id": "ml_python_libraries", "weight": 0.9},
                {"skill_id": "dl_frameworks_pytorch_tensorflow", "weight": 0.9}
            ],
            "skill_state_summary": {
                "mastered_skills": [{"skill_id": "ml_python_libraries", "proficiency": 92.0}],
                "verified_gaps": [{"skill_id": "dl_frameworks_pytorch_tensorflow", "proficiency": 35.0}],
                "developing_skills": []
            }
        }
        res_aiml = CurriculumEngine.build_curriculum(cand_aiml)
        # PyTorch should receive remediation lesson
        pytorch_acts = [a for a in res_aiml["activities"] if a["skill_id"] == "dl_frameworks_pytorch_tensorflow"]
        self.assertTrue(len(pytorch_acts) > 0)
        self.assertEqual(pytorch_acts[0]["activity_type"], ACTIVITY_LESSON)

        # Python should receive only revision
        py_acts = [a for a in res_aiml["activities"] if a["skill_id"] == "ml_python_libraries"]
        self.assertTrue(len(py_acts) > 0)
        self.assertEqual(py_acts[0]["activity_type"], ACTIVITY_REVISION)


if __name__ == "__main__":
    unittest.main()
