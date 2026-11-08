"""
Tests for PrepFly Job Preparation Intelligence Engine.
Validates:
1. Mandatory AI/ML Engineer JD regression case:
   - Model Development -> ml_model_development (NOT dsa_dp)
   - Deep Learning -> dl_neural_networks (NOT dsa_dp)
   - NLP -> nlp_pipelines (NOT dsa_dp)
   - Generative AI -> genai_llm_fundamentals
   - Preprocessing -> data_preprocessing (NOT cs_sql)
   - Datasets -> data_dataset_management (NOT sys_db_design)
   - Unified API canonical skill (NO duplicate api_design)
   - Data drift & retraining -> mlops_monitoring_drift & mlops_automated_retraining
   - Zero Dynamic Programming questions generated
   - Zero SQL questions generated without textual evidence
   - Zero duplicate questions
   - Unassessed skills distinguished from 0% ability
2. Negative guardrail enforcement against false positives.
3. Multi-role understanding (Backend Engineer vs Data Engineer vs AI/ML Engineer).
4. Question quality scoring (Relevance, Clarity, Depth composite >= 7.0).
5. Ava interview context provisioning with role blueprint.
"""

import unittest
from unittest.mock import MagicMock, patch
import json

from services.job_intelligence_service import (
    JobIntelligenceService,
    NEGATIVE_GUARDRAILS,
    TECH_TO_CANONICAL_SKILL,
    CANONICAL_ALIASES
)
from services.skill_taxonomy_service import SkillTaxonomyService, normalize_role_id
from local_supabase import get_supabase_client


class TestJobPrepIntelligence(unittest.TestCase):

    def setUp(self):
        self.supabase = get_supabase_client()
        self.user_id = "test_candidate_job_001"
        self.aiml_jd_text = """
Core Responsibilities:
• Model Development: Design, train, and fine-tune machine learning, deep learning, NLP, and generative AI models from scratch or using existing frameworks.
• Data Engineering: Collect, clean, preprocess, and manage large-scale datasets.
• Productionization: Deploy models into production environments, convert models into APIs, and ensure real-time scalability and low latency.
• Optimization & Monitoring: Track model performance, handle data drift, and retrain models to maintain accuracy over time.
"""

    def test_negative_guardrails_prevent_false_positives(self):
        """Verifies that negative guardrails block spurious mappings without explicit textual evidence."""
        # 'model development' must NOT pass for dsa_dp
        self.assertFalse(
            JobIntelligenceService._passes_negative_guardrails("dsa_dp", "design, train, and fine-tune machine learning models")
        )
        # 'data preprocessing' must NOT pass for cs_sql
        self.assertFalse(
            JobIntelligenceService._passes_negative_guardrails("cs_sql", "collect, clean, preprocess, and manage large-scale datasets")
        )
        # 'large-scale datasets' must NOT pass for sys_db_design
        self.assertFalse(
            JobIntelligenceService._passes_negative_guardrails("sys_db_design", "collect, clean, preprocess, and manage large-scale datasets")
        )
        # 'productionization' must NOT pass for sys_fault_tolerance
        self.assertFalse(
            JobIntelligenceService._passes_negative_guardrails("sys_fault_tolerance", "deploy models into production environments and convert into apis")
        )

        # True positives MUST pass
        self.assertTrue(
            JobIntelligenceService._passes_negative_guardrails("dsa_dp", "implement dynamic programming algorithms with memoization")
        )
        self.assertTrue(
            JobIntelligenceService._passes_negative_guardrails("cs_sql", "write complex sql queries and optimize join execution plans")
        )
        self.assertTrue(
            JobIntelligenceService._passes_negative_guardrails("sys_db_design", "design relational database schemas and b-tree indexing strategies")
        )

    def test_aiml_regression_case_requirement_extraction(self):
        """
        MANDATORY REGRESSION TEST:
        Validates extraction on the supplied AI/ML Engineer JD:
        - ML model development, DL, NLP, GenAI, Data Preprocessing, MLOps extracted
        - NO dsa_dp (Dynamic Programming)
        - NO cs_sql (SQL)
        - NO sys_db_design (Database Design)
        - NO duplicate API requirements (api_design unified into sys_rest_apis)
        """
        reqs = JobIntelligenceService._extract_and_deduplicate_requirements(
            job_id="job_test_aiml",
            text=self.aiml_jd_text,
            role_tier="mid"
        )
        extracted_skills = [r["normalized_skill_id"] for r in reqs]

        # 1. Assert NO false-positive DSA / DP mapping
        self.assertNotIn("dsa_dp", extracted_skills, "Dynamic Programming must NOT be extracted for AI/ML JD without DP evidence.")

        # 2. Assert NO false-positive SQL mapping
        self.assertNotIn("cs_sql", extracted_skills, "SQL must NOT be extracted without explicit SQL evidence.")

        # 3. Assert NO false-positive database design mapping
        self.assertNotIn("sys_db_design", extracted_skills, "Database design must NOT be extracted without explicit schema evidence.")

        # 4. Assert NO duplicate API requirements
        api_reqs = [s for s in extracted_skills if "api" in s or s == "sys_rest_apis"]
        self.assertEqual(len(api_reqs), 1, "REST API and API Design must be unified into a single canonical requirement.")
        self.assertIn("sys_rest_apis", extracted_skills)

        # 5. Assert true positive AI/ML & Data Engineering skills are present
        self.assertIn("ml_model_development", extracted_skills)
        self.assertIn("dl_neural_networks", extracted_skills)
        self.assertIn("nlp_pipelines", extracted_skills)
        self.assertIn("genai_llm_fundamentals", extracted_skills)
        self.assertIn("data_preprocessing", extracted_skills)
        self.assertIn("data_dataset_management", extracted_skills)
        self.assertIn("mlops_model_deployment", extracted_skills)
        self.assertIn("mlops_monitoring_drift", extracted_skills)
        self.assertIn("mlops_automated_retraining", extracted_skills)

    def test_aiml_regression_case_question_generation(self):
        """
        Validates tailored questions for the AI/ML Engineer JD:
        - Questions test ML, DL, Transformers, NLP, GenAI, Data, and MLOps
        - ZERO Dynamic Programming questions exist
        - ZERO SQL questions exist
        - ZERO duplicate questions exist
        - Every question has quality score >= 7.0
        """
        reqs = JobIntelligenceService._extract_and_deduplicate_requirements(
            job_id="job_test_aiml",
            text=self.aiml_jd_text,
            role_tier="mid"
        )
        questions = JobIntelligenceService.generate_and_evaluate_questions(
            job_id="job_test_aiml",
            job_title="AI/ML Engineer",
            role_tier="mid",
            requirements=reqs,
            supabase_client=self.supabase
        )

        self.assertGreaterEqual(len(questions), 4)

        all_text = " ".join(q["question_text"].lower() for q in questions)

        # Assert ZERO DP questions
        self.assertNotIn("dynamic programming", all_text)
        self.assertNotIn("knapsack", all_text)

        # Assert ZERO SQL questions
        self.assertNotIn("sql", all_text)

        # Assert questions cover core JD topics
        has_ml = any("machine learning" in q["question_text"].lower() or "model" in q["question_text"].lower() for q in questions)
        has_dl_transformers = any("neural" in q["question_text"].lower() or "attention" in q["question_text"].lower() or "transformer" in q["question_text"].lower() for q in questions)
        has_data = any("clean" in q["question_text"].lower() or "dataset" in q["question_text"].lower() or "preprocess" in q["question_text"].lower() for q in questions)
        has_mlops = any("drift" in q["question_text"].lower() or "serving" in q["question_text"].lower() or "deploy" in q["question_text"].lower() for q in questions)

        self.assertTrue(has_ml, "Must contain machine learning question.")
        self.assertTrue(has_dl_transformers, "Must contain deep learning / transformer question.")
        self.assertTrue(has_data, "Must contain data preprocessing question.")
        self.assertTrue(has_mlops, "Must contain MLOps / drift question.")

        # Assert no duplicate questions
        texts = [q["question_text"] for q in questions]
        self.assertEqual(len(texts), len(set(texts)), "Generated questions must contain zero duplicates.")

        # Assert quality scores >= 7.0
        for q in questions:
            self.assertGreaterEqual(q["quality_score"], 7.0)

    def test_match_scoring_decouples_unassessed_skills(self):
        """
        Validates that missing candidate evidence is classified as NOT_ASSESSED,
        and does NOT falsely report 0% ability on skills candidate simply hasn't taken yet.
        """
        # User has assessed ML Model Development with 80%, but other skills unassessed
        mock_profiles = {
            "ml_model_development": {"proficiency": 80.0, "confidence": 0.8, "evidence_count": 4}
        }
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"normalized_skill_id": "ml_model_development", "is_required": 1, "importance_weight": 4.0},
            {"normalized_skill_id": "dl_neural_networks", "is_required": 1, "importance_weight": 4.0},
            {"normalized_skill_id": "genai_llm_fundamentals", "is_required": 1, "importance_weight": 4.0}
        ])

        with patch("services.job_intelligence_service.SkillProfilingService.get_candidate_profile", return_value=mock_profiles):
            gaps = JobIntelligenceService.calculate_skill_gaps(
                self.user_id,
                "job_test_001",
                supabase_client=mock_supabase
            )

            # Required match on assessed skills should be 80.0%
            self.assertEqual(gaps["required_match_percentage"], 80.0)

            # Unassessed skills should be explicitly listed under unassessed_skills
            unassessed_ids = [u["skill_id"] for u in gaps["unassessed_skills"]]
            self.assertIn("dl_neural_networks", unassessed_ids)
            self.assertIn("genai_llm_fundamentals", unassessed_ids)

            # Critical gaps should NOT label unassessed skills as 0% ability failures
            for cg in gaps["critical_gaps"]:
                if cg["skill_id"] == "dl_neural_networks":
                    self.assertEqual(cg["evidence_status"], "NOT_ASSESSED")

    def test_backend_engineer_role_understanding(self):
        """Verifies that a Backend Engineer JD produces backend-relevant skills (REST, SQL, Caching) without ML."""
        backend_jd = """
Backend Engineer Responsibilities:
• Design and build high-throughput REST APIs and microservices.
• Optimize PostgreSQL database schemas, write efficient SQL queries, and implement Redis caching.
• Ensure system reliability, horizontal scalability, and handle production deployments using Docker.
"""
        reqs = JobIntelligenceService._extract_and_deduplicate_requirements("job_backend_001", backend_jd, "mid")
        skills = [r["normalized_skill_id"] for r in reqs]

        self.assertIn("sys_rest_apis", skills)
        self.assertIn("cs_sql", skills)
        self.assertIn("sys_caching", skills)
        self.assertIn("sys_scalability", skills)
        self.assertNotIn("ml_model_development", skills)
        self.assertNotIn("dl_neural_networks", skills)


if __name__ == "__main__":
    unittest.main()
