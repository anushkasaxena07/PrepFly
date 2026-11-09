import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_supabase import SQLiteSupabaseMock
from services.pure_scoring_engine import PureScoringEngine

class TestPhase4PureScoringEngine(unittest.TestCase):
    """
    Validates Phase 4 deliverables:
      1. Rubric scoring correctness and bounded invariant [0.0, 100.0]
      2. Statistical confidence bounds and single-question ceiling <= 0.40
      3. Role curriculum coverage calculation
      4. Honest, anti-inflation Role Readiness (Coverage Gate & Confidence Damper)
      5. Full explainability audit logging in score_audit_log
    """

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"test-user-{uuid.uuid4()}"

    def test_01_rubric_scoring_invariants(self):
        """Verifies weighted rubric arithmetic always produces bounded [0, 100] scores."""
        rubric = {"architecture": 40.0, "scaling": 30.0, "edge_cases": 30.0}
        
        # Perfect submission
        score_100 = PureScoringEngine.calculate_rubric_score(rubric, {"architecture": 1.0, "scaling": 1.0, "edge_cases": 1.0})
        self.assertEqual(score_100, 100.0)

        # Zero submission
        score_0 = PureScoringEngine.calculate_rubric_score(rubric, {"architecture": 0.0, "scaling": 0.0, "edge_cases": 0.0})
        self.assertEqual(score_0, 0.0)

        # Partial achievements: 0.5 * 40 + 1.0 * 30 + 0.0 * 30 = 20 + 30 = 50.0
        score_50 = PureScoringEngine.calculate_rubric_score(rubric, {"architecture": 0.5, "scaling": 1.0, "edge_cases": 0.0})
        self.assertEqual(score_50, 50.0)

        # Empty rubric handles gracefully
        self.assertEqual(PureScoringEngine.calculate_rubric_score({}, {}), 0.0)

    def test_02_confidence_monotonicity_and_single_question_ceiling(self):
        """Verifies N=1 yields confidence <= 0.40 and confidence grows monotonically with sample count."""
        conf_n1 = PureScoringEngine.calculate_confidence(sample_count=1, concept_diversity=1)
        self.assertTrue(conf_n1 <= 0.40, f"Expected N=1 confidence <= 0.40, got {conf_n1}")
        self.assertTrue(conf_n1 > 0.0)

        conf_n3 = PureScoringEngine.calculate_confidence(sample_count=3, concept_diversity=2)
        conf_n6 = PureScoringEngine.calculate_confidence(sample_count=6, concept_diversity=4)
        conf_n12 = PureScoringEngine.calculate_confidence(sample_count=12, concept_diversity=4)

        # Monotonic growth
        self.assertTrue(conf_n1 < conf_n3 < conf_n6 < conf_n12)
        self.assertTrue(conf_n12 <= 1.0)

        # Variance penalty: erratic scores reduce confidence
        conf_stable = PureScoringEngine.calculate_confidence(sample_count=5, score_variance=50.0)
        conf_erratic = PureScoringEngine.calculate_confidence(sample_count=5, score_variance=1200.0)
        self.assertTrue(conf_stable > conf_erratic)

    def test_03_coverage_calculation(self):
        """Verifies curriculum coverage correctly measures assessed weight ratio."""
        role_weights = {
            "math_stats": 0.2,
            "classical_ml": 0.3,
            "deep_learning": 0.3,
            "mlops": 0.2
        }
        # 0 assessed
        self.assertEqual(PureScoringEngine.calculate_coverage([], role_weights), 0.0)

        # Half assessed: math_stats (0.2) + classical_ml (0.3) = 0.5 -> 50%
        cov_50 = PureScoringEngine.calculate_coverage(["math_stats", "classical_ml"], role_weights)
        self.assertEqual(cov_50, 50.0)

        # All assessed
        cov_100 = PureScoringEngine.calculate_coverage(list(role_weights.keys()), role_weights)
        self.assertEqual(cov_100, 100.0)

    def test_04_role_readiness_anti_inflation_and_provisional_flag(self):
        """
        Critical Anti-Inflation Test:
        A candidate with 100% score on 1 out of 10 skills (10% coverage) must NOT
        receive an overall readiness score > 35%, and must be flagged as PROVISIONAL.
        """
        role_weights = {f"skill_{i}": 0.1 for i in range(10)}
        mandatory = ["skill_0", "skill_1", "skill_2"]

        # Scenario A: Scored 100% on skill_0, but remaining 9 skills unassessed
        proficiencies_a = {"skill_0": 100.0}
        confidences_a = {"skill_0": 0.35}

        readiness_a = PureScoringEngine.calculate_role_readiness(
            skill_proficiencies=proficiencies_a,
            skill_confidences=confidences_a,
            required_weights=role_weights,
            mandatory_skills=mandatory
        )
        self.assertEqual(readiness_a["assessed_proficiency"], 100.0)
        self.assertEqual(readiness_a["coverage_pct"], 10.0)
        self.assertTrue(readiness_a["provisional"])
        self.assertTrue(readiness_a["overall_readiness"] <= 35.0, f"Expected <= 35.0%, got {readiness_a['overall_readiness']}")
        self.assertIn("skill_1", readiness_a["missing_mandatory_skills"])

        # Scenario B: Comprehensive assessment across all 10 skills with 85% average
        proficiencies_b = {f"skill_{i}": 85.0 for i in range(10)}
        confidences_b = {f"skill_{i}": 0.9 for i in range(10)}

        readiness_b = PureScoringEngine.calculate_role_readiness(
            skill_proficiencies=proficiencies_b,
            skill_confidences=confidences_b,
            required_weights=role_weights,
            mandatory_skills=mandatory
        )
        self.assertEqual(readiness_b["assessed_proficiency"], 85.0)
        self.assertEqual(readiness_b["coverage_pct"], 100.0)
        self.assertFalse(readiness_b["provisional"])
        self.assertTrue(readiness_b["overall_readiness"] >= 75.0)

    def test_05_score_audit_logging_explainability(self):
        """Verifies calculation inputs and outputs are recorded in score_audit_log."""
        inputs = {"rubric": {"c1": 50, "c2": 50}, "achievements": {"c1": 1.0, "c2": 0.8}}
        log_id = PureScoringEngine.audit_and_log_score(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            calculation_type="rubric_evaluation",
            score_inputs=inputs,
            calculated_score=90.0,
            supabase_client=self.client
        )
        self.assertTrue(log_id)
        
        # Verify row in DB
        res = self.client.table("score_audit_log").select("*").eq("id", log_id).execute()
        self.assertTrue(res.data)
        self.assertEqual(res.data[0]["calculated_score"], 90.0)
        self.assertEqual(res.data[0]["calculation_type"], "rubric_evaluation")

if __name__ == "__main__":
    unittest.main()

