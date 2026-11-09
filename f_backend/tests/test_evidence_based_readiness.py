"""
AUTOMATED TEST SUITE: EVIDENCE-BASED SKILL PROFICIENCY AND ROLE READINESS ENGINE
==============================================================================
Validates all 10 essential scenarios specified in the task requirement:
1. Resume only -> claimed skills, no fabricated proficiency
2. Projects only -> project exposure, no automatic mastery
3. Coding strong, conceptual weak -> separate proficiencies
4. 1 easy question -> low coverage & limited confidence
5. Repeated advanced assessments -> higher proficiency & confidence
6. No Spring Boot assessment -> NOT_ASSESSED, never weakness
7. Strong Python, weak model evaluation -> targeted gap recommendation
8. Different target role -> role-specific readiness weights
9. Duplicate submission -> no score inflation
10. Old assessment -> recency staleness indicator
"""

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from services.canonical_skill_taxonomy import CanonicalSkillTaxonomy
from services.evidence_registry_service import (
    EvidenceRegistryService,
    SOURCE_RESUME_MENTION,
    SOURCE_PROJECT_MENTION,
    SOURCE_DIAGNOSTIC_ASSESSMENT,
    SOURCE_CODING_SUBMISSION,
    SOURCE_PRACTICAL_ASSIGNMENT
)
from services.evidence_scoring_engine import EvidenceScoringEngine
from services.role_readiness_engine import RoleReadinessEngine
from services.weakness_detection_engine import WeaknessDetectionEngine
from local_supabase import SQLiteSupabaseMock


class TestEvidenceBasedReadinessEngine(unittest.TestCase):

    def setUp(self):
        self.client = SQLiteSupabaseMock()
        self.user_id = f"test_cand_{uuid.uuid4().hex[:8]}"

    def test_scenario_01_resume_only_no_fabricated_proficiency(self):
        """Scenario 1: Candidate with only resume mentions has CLAIMED_EXPOSURE and NO fabricated proficiency."""
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="python_syntax_idioms",
            source_type=SOURCE_RESUME_MENTION,
            submission_content={"resume_section": "Skills: Python, Django"},
            supabase_client=self.client
        )

        res = EvidenceScoringEngine.evaluate_skill(
            user_id=self.user_id,
            skill_id="python_syntax_idioms",
            supabase_client=self.client
        )

        # Proficiency MUST BE None (never fabricated to 0 or 70)
        self.assertIsNone(res["proficiency"])
        self.assertEqual(res["evidence_status"], "CLAIMED_EXPOSURE")
        self.assertEqual(res["confidence"], 0.0)
        self.assertFalse(res["is_assessed"])

    def test_scenario_02_projects_only_exposure_without_mastery(self):
        """Scenario 2: Project descriptions record PROJECT_EXPOSURE but no automatic mastery score."""
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="sys_caching",
            source_type=SOURCE_PROJECT_MENTION,
            submission_content={"project_title": "E-Commerce Redis Cache"},
            supabase_client=self.client
        )

        res = EvidenceScoringEngine.evaluate_skill(
            user_id=self.user_id,
            skill_id="sys_caching",
            supabase_client=self.client
        )

        self.assertIsNone(res["proficiency"])
        self.assertEqual(res["evidence_status"], "PROJECT_EXPOSURE")
        self.assertEqual(res["confidence"], 0.0)

    def test_scenario_03_coding_strong_conceptual_weak_separation(self):
        """Scenario 3: Strong coding performance does not conflate with weak conceptual understanding."""
        # 1. Strong coding submission on arrays (score 95%)
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dsa_arrays_strings",
            source_type=SOURCE_CODING_SUBMISSION,
            raw_score=95.0,
            difficulty="Intermediate",
            submission_content={"code": "def two_sum(): pass"},
            supabase_client=self.client
        )

        # 2. Weak conceptual assessment on OS concurrency (score 35%)
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="cs_os_concurrency",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=35.0,
            difficulty="Intermediate",
            submission_content={"answer": "threads are light"},
            supabase_client=self.client
        )

        res_coding = EvidenceScoringEngine.evaluate_skill(
            user_id=self.user_id,
            skill_id="dsa_arrays_strings",
            supabase_client=self.client
        )
        res_concept = EvidenceScoringEngine.evaluate_skill(
            user_id=self.user_id,
            skill_id="cs_os_concurrency",
            supabase_client=self.client
        )

        self.assertGreaterEqual(res_coding["proficiency"], 90.0)
        self.assertLess(res_concept["proficiency"], 40.0)
        # Separately tracked
        self.assertNotEqual(res_coding["proficiency"], res_concept["proficiency"])

    def test_scenario_04_one_easy_question_low_confidence(self):
        """Scenario 4: Answering 1 single easy question yields low confidence (< 0.50)."""
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="python_syntax_idioms",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=80.0,
            difficulty="Beginner",
            submission_content={"answer": "list comprehensions syntax"},
            supabase_client=self.client
        )

        res = EvidenceScoringEngine.evaluate_skill(
            user_id=self.user_id,
            skill_id="python_syntax_idioms",
            supabase_client=self.client
        )

        self.assertIsNotNone(res["proficiency"])
        self.assertLess(res["confidence"], 0.50)

    def test_scenario_05_repeated_advanced_assessments_high_confidence(self):
        """Scenario 5: Repeated advanced multi-source assessments yield higher confidence (> 0.70)."""
        # 1. Advanced diagnostic assessment
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dl_transformers",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=90.0,
            difficulty="Advanced",
            submission_content={"answer": "attention scaled dot product formula"},
            supabase_client=self.client
        )
        # 2. Practical assignment
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dl_transformers",
            source_type=SOURCE_PRACTICAL_ASSIGNMENT,
            raw_score=92.0,
            difficulty="Advanced",
            submission_content={"code": "class MultiHeadAttention(): pass"},
            supabase_client=self.client
        )
        # 3. Coding submission
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dl_transformers",
            source_type=SOURCE_CODING_SUBMISSION,
            raw_score=88.0,
            difficulty="Advanced",
            submission_content={"code": "def scaled_dot_product(): pass"},
            supabase_client=self.client
        )

        res = EvidenceScoringEngine.evaluate_skill(
            user_id=self.user_id,
            skill_id="dl_transformers",
            supabase_client=self.client
        )

        self.assertGreater(res["proficiency"], 85.0)
        self.assertGreater(res["confidence"], 0.70)

    def test_scenario_06_unassessed_skill_never_weakness(self):
        """Scenario 6: Unassessed skills are NEVER labeled as weaknesses."""
        # Record only a resume mention for cs_dbms_internals
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="cs_dbms_internals",
            source_type=SOURCE_RESUME_MENTION,
            submission_content={"resume": "Experienced in Spring Boot & PostgreSQL"},
            supabase_client=self.client
        )

        weaknesses = WeaknessDetectionEngine.detect_weaknesses(
            user_id=self.user_id,
            supabase_client=self.client
        )

        # Unassessed skill MUST NOT appear in weaknesses
        weak_ids = [w["skill_id"] for w in weaknesses]
        self.assertNotIn("cs_dbms_internals", weak_ids)

    def test_scenario_07_strong_python_weak_model_eval_targeted_gap(self):
        """Scenario 7: Strong Python but verified failure on Model Evaluation flags ONLY the failed skill."""
        # Python strong (92%)
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="python_syntax_idioms",
            source_type=SOURCE_CODING_SUBMISSION,
            raw_score=92.0,
            difficulty="Intermediate",
            submission_content={"code": "comprehensions"},
            supabase_client=self.client
        )

        # Model evaluation weak (38%)
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="ml_model_evaluation",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=38.0,
            difficulty="Intermediate",
            submission_content={"answer": "I would just use raw accuracy"},
            metadata={"missed_concepts": ["PR-AUC under severe class imbalance", "F1 trade-offs"]},
            supabase_client=self.client
        )

        weaknesses = WeaknessDetectionEngine.detect_weaknesses(
            user_id=self.user_id,
            supabase_client=self.client
        )

        weak_ids = [w["skill_id"] for w in weaknesses]
        self.assertIn("ml_model_evaluation", weak_ids)
        self.assertNotIn("python_syntax_idioms", weak_ids)

        gap_item = next(w for w in weaknesses if w["skill_id"] == "ml_model_evaluation")
        self.assertEqual(gap_item["severity"], "VERIFIED_GAP")
        self.assertIn("PR-AUC", str(gap_item["failed_criteria"]))

    def test_scenario_08_different_target_roles_calibrated_weights(self):
        """Scenario 8: Role readiness engine applies role-specific weights."""
        # Record identical evidence across Python and ML
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="ml_model_development",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=90.0,
            difficulty="Intermediate",
            submission_content={"ans": "regularization"},
            supabase_client=self.client
        )
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dsa_arrays_strings",
            source_type=SOURCE_CODING_SUBMISSION,
            raw_score=50.0,
            difficulty="Intermediate",
            submission_content={"code": "arrays"},
            supabase_client=self.client
        )

        res_aiml = RoleReadinessEngine.calculate_readiness(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            supabase_client=self.client
        )
        res_sde = RoleReadinessEngine.calculate_readiness(
            user_id=self.user_id,
            target_role="Software Development Engineer (General)",
            supabase_client=self.client
        )

        # AI/ML considers ml_model_development Mandatory (1.5x) while SDE does not
        self.assertNotEqual(res_aiml["overall_score"], res_sde["overall_score"])

    def test_scenario_09_duplicate_submission_no_score_inflation(self):
        """Scenario 9: Submitting the identical submission does not duplicate evidence or inflate scores."""
        content = {"code": "def solve(): return True"}

        # First submission
        rec1 = EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dsa_hashing",
            source_type=SOURCE_CODING_SUBMISSION,
            raw_score=85.0,
            submission_content=content,
            supabase_client=self.client
        )
        self.assertFalse(rec1["is_duplicate"])

        # Identical second submission
        rec2 = EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dsa_hashing",
            source_type=SOURCE_CODING_SUBMISSION,
            raw_score=85.0,
            submission_content=content,
            supabase_client=self.client
        )
        self.assertTrue(rec2["is_duplicate"])

        evs = EvidenceRegistryService.get_evidence_for_candidate(
            user_id=self.user_id,
            skill_id="dsa_hashing",
            supabase_client=self.client
        )
        # Should only have 1 unique record stored
        self.assertEqual(len(evs), 1)

    def test_scenario_10_old_assessment_recency_staleness(self):
        """Scenario 10: Assessments older than 120 days are flagged as STALE_REASSESSMENT_DUE."""
        old_time = (datetime.now(timezone.utc) - timedelta(days=140)).isoformat()
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="sys_scalability",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=80.0,
            created_at=old_time,
            submission_content={"ans": "stateless services"},
            supabase_client=self.client
        )

        res = EvidenceScoringEngine.evaluate_skill(
            user_id=self.user_id,
            skill_id="sys_scalability",
            supabase_client=self.client
        )

        self.assertEqual(res["recency"], "STALE_REASSESSMENT_DUE")
        self.assertGreater(res["recency_age_days"], 120)


if __name__ == "__main__":
    unittest.main()
