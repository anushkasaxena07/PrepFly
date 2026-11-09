import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_supabase import SQLiteSupabaseMock
from services.career_goal_service import CareerGoalService
from services.job_requirement_extractor import JobRequirementExtractor
from services.skill_taxonomy_service import SkillTaxonomyService, normalize_role_id

class TestPhase2TaxonomyAndJDParser(unittest.TestCase):
    """
    Validates Phase 2 deliverables:
      1. CareerGoalService (Multi-goal lifecycle, role normalization, isolation)
      2. JobRequirementExtractor (SHA-256 deduplication, skill extraction, weight normalization)
      3. SkillTaxonomyService (Prerequisite DAG, cycle detection, canonical seeding)
    """

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"test-user-{uuid.uuid4()}"

    def test_01_career_goal_lifecycle_and_multi_goal_isolation(self):
        """Verifies candidate can create and maintain multiple independent career goals."""
        # Goal 1: AI/ML Engineer
        goal1 = CareerGoalService.create_career_goal(
            user_id=self.user_id,
            target_role="AI / ML Engineer",
            target_company="Google DeepMind",
            job_description="Research in large language models and attention mechanisms.",
            experience_level="Fresher",
            supabase_client=self.client
        )
        self.assertEqual(goal1["role_id"], "ai_ml_engineer")
        self.assertEqual(goal1["target_company"], "Google DeepMind")

        # Goal 2: Backend Developer
        goal2 = CareerGoalService.create_career_goal(
            user_id=self.user_id,
            target_role="Backend Developer",
            target_company="Stripe",
            job_description="High-throughput payment APIs, distributed databases, and Redis caching.",
            experience_level="Experienced",
            supabase_client=self.client
        )
        self.assertEqual(goal2["role_id"], "backend_developer")
        self.assertEqual(goal2["target_company"], "Stripe")

        # Verify goals exist independently and do not overwrite each other
        user_goals = CareerGoalService.get_career_goals_for_user(self.user_id, supabase_client=self.client)
        self.assertEqual(len(user_goals), 2)
        role_ids = {g["role_id"] for g in user_goals}
        self.assertIn("ai_ml_engineer", role_ids)
        self.assertIn("backend_developer", role_ids)

    def test_02_job_requirement_extractor_with_ai_ml_jd(self):
        """Verifies skill extraction from an AI/ML job description and weight normalization."""
        aiml_jd = (
            "We are looking for an AI/ML Engineer proficient in Deep Learning, PyTorch, "
            "Transformers, Large Language Models, and statistical modeling. Experience with "
            "model evaluation, overfitting mitigation, and deployment is a plus."
        )
        res = JobRequirementExtractor.extract_and_persist_requirements(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            job_description=aiml_jd,
            company="Anthropic",
            supabase_client=self.client
        )
        self.assertEqual(res["target_role"], "ai_ml_engineer")
        self.assertTrue(len(res["required_skills"]) >= 3)
        self.assertIn("dl_transformers", res["required_skills"])
        self.assertIn("genai_llm_fundamentals", res["required_skills"])

        # Check weight distribution sums to approximately 1.0
        weights = res["weight_distribution"]
        total_w = sum(weights.values())
        self.assertAlmostEqual(total_w, 1.0, delta=0.01)

    def test_03_job_requirement_extractor_sha256_cache_hit(self):
        """Verifies that duplicate JD text returns cached requirements in O(1)."""
        jd_text = "Backend engineer specializing in distributed caching with Redis, PostgreSQL, and REST APIs."
        
        # 1st extraction: processes and persists
        res1 = JobRequirementExtractor.extract_and_persist_requirements(
            user_id=self.user_id,
            target_role="Backend Developer",
            job_description=jd_text,
            company="Netflix",
            supabase_client=self.client
        )
        self.assertEqual(res1["source"], "extracted")

        # 2nd extraction with same JD: returns from cache
        res2 = JobRequirementExtractor.extract_and_persist_requirements(
            user_id=self.user_id,
            target_role="Backend Developer",
            job_description=jd_text,
            company="Netflix",
            supabase_client=self.client
        )
        self.assertEqual(res2["source"], "cache")
        self.assertEqual(res1["source_text_hash"], res2["source_text_hash"])
        self.assertEqual(res1["required_skills"], res2["required_skills"])

    def test_04_job_requirement_extractor_empty_jd_fallback(self):
        """Verifies that an absent or empty JD cleanly falls back to canonical role requirements."""
        res = JobRequirementExtractor.extract_and_persist_requirements(
            user_id=self.user_id,
            target_role="DevOps Engineer",
            job_description="",
            supabase_client=self.client
        )
        self.assertEqual(res["target_role"], "devops_engineer")
        self.assertTrue(len(res["required_skills"]) > 0)
        total_w = sum(res["weight_distribution"].values())
        self.assertAlmostEqual(total_w, 1.0, delta=0.01)

    def test_05_prerequisite_dag_is_acyclic(self):
        """Verifies that the canonical Skill Taxonomy DAG contains zero cyclic dependencies."""
        cycles = SkillTaxonomyService.detect_cycles()
        self.assertEqual(cycles, [], f"Detected cycle in skill taxonomy: {cycles}")

    def test_06_transitive_prerequisites_traversal(self):
        """Verifies transitive prerequisite closure."""
        # dl_transformers requires dl_neural_networks, which requires math/stats
        transitive = SkillTaxonomyService.get_transitive_prerequisites("dl_transformers")
        self.assertTrue(len(transitive) >= 1)
        self.assertIn("dl_neural_networks", transitive)

    def test_07_seed_skill_catalogue(self):
        """Verifies seeding canonical skills into persistent skill_catalogue table."""
        seeded_count = SkillTaxonomyService.seed_skill_catalogue(supabase_client=self.client)
        self.assertTrue(seeded_count > 30, f"Expected >30 seeded skills, got {seeded_count}")
        res = self.client.table("skill_catalogue").select("*").eq("id", "dl_transformers").execute()
        self.assertTrue(res.data)
        self.assertEqual(res.data[0]["id"], "dl_transformers")

if __name__ == "__main__":
    unittest.main()
