import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_supabase import SQLiteSupabaseMock
from services.weakness_detection_engine import WeaknessDetectionEngine
from services.evidence_registry_service import (
    EvidenceRegistryService,
    SOURCE_CODING_SUBMISSION,
    SOURCE_DIAGNOSTIC_ASSESSMENT,
    SOURCE_RESUME_MENTION
)

class TestPhase5GroundedWeaknessEngine(unittest.TestCase):
    """
    Validates Phase 5 Grounded Weakness Engine deliverables:
      1. Zero false-positives on unassessed skills or resume mentions
      2. Strict verification requirement: failure (< 60%) backed by evidence
      3. Categorization into VERIFIED_GAP (< 45%) and DEVELOPING (45-59%)
      4. Extraction of failed criteria and root-cause prerequisite gaps
      5. Clear separation between verified weaknesses and unassessed uncertainties
    """

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"test-user-{uuid.uuid4()}"

    def test_01_unassessed_skills_and_resume_claims_never_labeled_as_weakness(self):
        """Verifies skills with zero assessments or resume claims only are NEVER in weaknesses."""
        # 1. Resume mention only
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="cs_dbms_internals",
            source_type=SOURCE_RESUME_MENTION,
            submission_content={"resume": "Proficient in SQL databases and PostgreSQL"},
            supabase_client=self.client
        )

        weaknesses = WeaknessDetectionEngine.detect_weaknesses(
            user_id=self.user_id,
            supabase_client=self.client
        )
        weak_ids = [w["skill_id"] for w in weaknesses]
        self.assertNotIn("cs_dbms_internals", weak_ids)

    def test_02_high_proficiency_skills_never_labeled_as_weakness(self):
        """Verifies skills with score >= 60% are never labeled as weaknesses."""
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="python_syntax_idioms",
            source_type=SOURCE_CODING_SUBMISSION,
            raw_score=95.0,
            difficulty="Intermediate",
            submission_content={"code": "def solution(): pass"},
            supabase_client=self.client
        )

        weaknesses = WeaknessDetectionEngine.detect_weaknesses(
            user_id=self.user_id,
            supabase_client=self.client
        )
        weak_ids = [w["skill_id"] for w in weaknesses]
        self.assertNotIn("python_syntax_idioms", weak_ids)

    def test_03_verified_failure_flags_only_failed_skill_with_provenance(self):
        """Verifies that an assessed score < 60% flags a targeted weakness with remedial assignment."""
        # Verified failure on Model Evaluation (35% score)
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="ml_model_evaluation",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=35.0,
            difficulty="Intermediate",
            submission_content={"answer": "I would just measure raw accuracy."},
            metadata={"missed_concepts": ["PR-AUC under severe class imbalance", "F1 score vs ROC-AUC distortion"]},
            supabase_client=self.client
        )

        weaknesses = WeaknessDetectionEngine.detect_weaknesses(
            user_id=self.user_id,
            supabase_client=self.client
        )
        self.assertEqual(len(weaknesses), 1)
        w = weaknesses[0]
        self.assertEqual(w["skill_id"], "ml_model_evaluation")
        self.assertEqual(w["severity"], "VERIFIED_GAP")
        self.assertEqual(w["proficiency"], 35.0)
        self.assertIn("PR-AUC", str(w["failed_criteria"]))
        self.assertIn("remedial_assignment", w)
        self.assertEqual(w["remedial_assignment"]["activity_type"], "PRACTICAL_ASSIGNMENT")

    def test_04_prerequisite_root_cause_tracing(self):
        """Verifies that a weak skill detects unassessed or weak foundational prerequisites in the DAG."""
        # Candidate failed Transformer Attention
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="dl_transformers",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=40.0,
            difficulty="Advanced",
            metadata={"missed_concepts": ["Scaling factor sqrt(d_k)", "O(N^2) complexity"]},
            supabase_client=self.client
        )

        weaknesses = WeaknessDetectionEngine.detect_weaknesses(
            user_id=self.user_id,
            supabase_client=self.client
        )
        self.assertEqual(len(weaknesses), 1)
        w = weaknesses[0]
        self.assertEqual(w["skill_id"], "dl_transformers")
        # Prerequisite dl_neural_networks was unassessed, should appear in prerequisite_gaps
        prereq_gaps = w.get("prerequisite_gaps", [])
        prereq_ids = [pg["skill_id"] for pg in prereq_gaps]
        self.assertIn("dl_neural_networks", prereq_ids)

    def test_05_detect_weaknesses_and_uncertainties_separation(self):
        """Verifies clean separation between verified weaknesses and unassessed role uncertainties."""
        # 1 verified failure
        EvidenceRegistryService.record_evidence(
            user_id=self.user_id,
            skill_id="cs_concurrency",
            source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
            raw_score=42.0,
            metadata={"missed_concepts": ["Race conditions", "Deadlock Coffman conditions"]},
            supabase_client=self.client
        )

        report = WeaknessDetectionEngine.detect_weaknesses_and_uncertainties(
            user_id=self.user_id,
            target_role="Backend Developer",
            supabase_client=self.client
        )
        self.assertEqual(report["weakness_count"], 1)
        self.assertEqual(report["verified_weaknesses"][0]["skill_id"], "cs_concurrency")
        
        # Untested backend skills (e.g. sys_caching) must be in uncertainties, NOT weaknesses
        uncertainty_ids = [u["skill_id"] for u in report["unassessed_uncertainties"]]
        self.assertIn("sys_caching", uncertainty_ids)
        self.assertNotIn("cs_concurrency", uncertainty_ids)

if __name__ == "__main__":
    unittest.main()

