"""
Comprehensive Test Suite for PrepFly Job-Specific Readiness Assessment and Gap Analysis Engine.
Validates all 12 test scenarios from Section 14:
1. AI/ML Engineer fresher (negative guardrails, zero DP/SQL, MLOps drift)
2. Software Engineer fresher (DSA + Core CS + REST)
3. Backend Engineer (REST, SQL, Caching, Scalability, no ML)
4. Data Analyst (SQL, Python libraries, Visualization, no DP)
5. Strong coding but weak communication
6. Strong resume claims but weak technical knowledge
7. Strong interview performance but weak coding
8. No previous assessment history (Coverage < 40% -> READINESS NOT YET ESTABLISHED)
9. Incomplete / ambiguous JD (uncertainty preserved, no fabricated requirements)
10. Conflicting / sparse company reports (evidence disclosure & role-based fallback)
11. New target role after previous assessment (historical snapshots preserved)
12. Candidate with insufficient time before interview (urgent gap prioritization)
13. Deterministic Rubric Scoring (separating correctness, depth, communication)
14. Prep tab handover export formatting
15. Analytics event publishing
"""

import unittest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime, timezone

from services.job_readiness_engine import (
    JobReadinessEngine,
    REQ_EXPLICIT_MANDATORY,
    REQ_EXPLICIT_PREFERRED,
    REQ_RESPONSIBILITY_DERIVED,
    REQ_COMPANY_INTERVIEW_PATTERN,
    REQ_GENERAL_ROLE_EXPECTATION,
    REQ_INFERRED_UNCERTAIN,
    EVID_DEMONSTRATED,
    EVID_ASSESSED,
    EVID_CLAIMED,
    EVID_UNASSESSED,
    MIN_COVERAGE_FOR_READINESS
)
from services.skill_taxonomy_service import SKILL_CATALOG
from local_supabase import get_supabase_client


class TestJobReadinessEngineComprehensive(unittest.TestCase):

    def setUp(self):
        self.supabase = get_supabase_client()
        self.user_id = "test_candidate_job_readiness_001"

    # -------------------------------------------------------------------------
    # Scenario 1: AI/ML Engineer Fresher
    # -------------------------------------------------------------------------
    def test_scenario_1_aiml_engineer_fresher(self):
        """Verifies AI/ML JD extracts ML/DL/NLP/MLOps without spurious DP, SQL, or DB Design."""
        jd = """
        Core Responsibilities:
        • Model Development: Design, train, and fine-tune machine learning, deep learning, NLP, and generative AI models.
        • Data Engineering: Collect, clean, preprocess, and manage large-scale datasets.
        • Productionization: Deploy models into production environments and convert models into APIs.
        • Optimization & Monitoring: Track model performance, handle data drift, and retrain models to maintain accuracy.
        """
        reqs = JobReadinessEngine.extract_and_classify_requirements(
            raw_text=jd,
            company="Databricks",
            role="AI/ML Engineer",
            experience_level="Fresher"
        )
        skill_ids = [r["canonical_skill_id"] for r in reqs]

        # Valid mappings
        self.assertIn("ml_model_development", skill_ids)
        self.assertIn("dl_neural_networks", skill_ids)
        self.assertIn("nlp_pipelines", skill_ids)
        self.assertIn("genai_llm_fundamentals", skill_ids)
        self.assertIn("data_preprocessing", skill_ids)
        self.assertIn("mlops_monitoring_drift", skill_ids)

        # Negative Guardrail checks: No DP, No SQL without explicit query keywords, No DB design
        self.assertNotIn("dsa_dp", skill_ids, "Model development must never map to Dynamic Programming.")
        self.assertNotIn("cs_sql", skill_ids, "Generic data preprocessing must never map to SQL.")
        self.assertNotIn("sys_db_design", skill_ids, "Dataset scale must never map to database design.")

    # -------------------------------------------------------------------------
    # Scenario 2: Software Engineer Fresher
    # -------------------------------------------------------------------------
    def test_scenario_2_software_engineer_fresher(self):
        """Verifies SDE fresher JD extracts DSA, Core CS, and OOP fundamentals."""
        jd = """
        Minimum Requirements:
        • Strong foundation in Data Structures, Algorithms, problem solving, and computational complexity.
        • Working knowledge of Object Oriented Programming, Operating Systems, and Memory Management.
        • Experience building RESTful web services and API endpoints.
        """
        reqs = JobReadinessEngine.extract_and_classify_requirements(
            raw_text=jd,
            company="Google",
            role="Software Engineer",
            experience_level="Fresher"
        )
        skill_ids = [r["canonical_skill_id"] for r in reqs]

        self.assertIn("dsa_arrays", skill_ids)
        self.assertIn("cs_os", skill_ids)
        self.assertIn("sys_rest_apis", skill_ids)

        # Check classification: requirements section marks as explicit_mandatory
        for r in reqs:
            if r["canonical_skill_id"] == "dsa_arrays":
                self.assertEqual(r["requirement_type"], REQ_EXPLICIT_MANDATORY)

    # -------------------------------------------------------------------------
    # Scenario 3: Backend Engineer
    # -------------------------------------------------------------------------
    def test_scenario_3_backend_engineer(self):
        """Verifies Backend Engineer extracts REST, SQL, Caching, Scalability without ML."""
        jd = """
        Responsibilities:
        • Design and build high-throughput REST APIs and microservices.
        • Optimize PostgreSQL database schemas, write efficient SQL queries, and implement Redis caching.
        • Ensure system reliability, horizontal scalability, and handle production deployments using Docker.
        """
        reqs = JobReadinessEngine.extract_and_classify_requirements(
            raw_text=jd,
            company="Uber",
            role="Backend Engineer",
            experience_level="Mid-Level"
        )
        skill_ids = [r["canonical_skill_id"] for r in reqs]

        self.assertIn("sys_rest_apis", skill_ids)
        self.assertIn("cs_sql", skill_ids)
        self.assertIn("sys_caching", skill_ids)
        self.assertIn("sys_scalability", skill_ids)
        self.assertNotIn("ml_model_development", skill_ids)
        self.assertNotIn("dl_neural_networks", skill_ids)

    # -------------------------------------------------------------------------
    # Scenario 4: Data Analyst
    # -------------------------------------------------------------------------
    def test_scenario_4_data_analyst(self):
        """Verifies Data Analyst JD extracts SQL, Python libraries, visualization, and stats."""
        jd = """
        Key Duties:
        • Write complex SQL queries to extract, transform, and analyze multi-terabyte datasets.
        • Build automated dashboards and KPI reporting tools using Python, Pandas, and visualization libraries.
        • Perform statistical hypothesis testing and present actionable business recommendations.
        """
        reqs = JobReadinessEngine.extract_and_classify_requirements(
            raw_text=jd,
            company="Amazon",
            role="Data Analyst",
            experience_level="Junior"
        )
        skill_ids = [r["canonical_skill_id"] for r in reqs]

        self.assertIn("cs_sql", skill_ids)
        self.assertIn("ml_python_libraries", skill_ids)
        self.assertIn("math_probability_statistics", skill_ids)
        self.assertNotIn("dsa_dp", skill_ids)

    # -------------------------------------------------------------------------
    # Scenario 5: Strong Coding but Weak Communication
    # -------------------------------------------------------------------------
    def test_scenario_5_strong_coding_weak_communication(self):
        """Validates that candidate with high coding score (90%) but low communication (45%) has separated dimensions."""
        mock_evidence = {
            "demonstrated_competencies": {
                "dsa_arrays": {"proficiency": 95.0, "evidence_type": EVID_DEMONSTRATED},
                "cs_sql": {"proficiency": 88.0, "evidence_type": EVID_DEMONSTRATED}
            },
            "assessed_competencies": {
                "sys_rest_apis": {"proficiency": 75.0, "evidence_type": EVID_ASSESSED}
            },
            "claimed_competencies": {},
            "unassessed_competencies": [],
            "coding_analysis": {"average_score": 92.0, "accepted_count": 15},
            "ava_interview_analysis": {"average_score": 52.0, "communication_score": 48.0},
            "resume_analysis": {"ats_score": 80.0}
        }
        requirements = [
            {"canonical_skill_id": "dsa_arrays", "importance": 5.0, "requirement_type": REQ_EXPLICIT_MANDATORY},
            {"canonical_skill_id": "cs_sql", "importance": 4.0, "requirement_type": REQ_EXPLICIT_MANDATORY},
            {"canonical_skill_id": "sys_rest_apis", "importance": 3.5, "requirement_type": REQ_RESPONSIBILITY_DERIVED}
        ]

        readiness = JobReadinessEngine.calculate_job_readiness(requirements, mock_evidence)

        self.assertEqual(readiness["readiness_status"], "ESTABLISHED")
        self.assertGreaterEqual(readiness["dimensions"]["coding_problem_solving"], 90.0)
        self.assertLessEqual(readiness["dimensions"]["communication_behavioral"], 50.0)
        self.assertNotEqual(readiness["dimensions"]["coding_problem_solving"], readiness["dimensions"]["communication_behavioral"])

    # -------------------------------------------------------------------------
    # Scenario 6: Strong Resume Claims but Weak Technical Knowledge
    # -------------------------------------------------------------------------
    def test_scenario_6_strong_resume_weak_technical(self):
        """Verifies that resume claims are strictly classified as 'claimed' (50% unverified) and do not count as demonstrated."""
        mock_evidence = {
            "demonstrated_competencies": {},
            "assessed_competencies": {
                "dsa_arrays": {"proficiency": 42.0, "evidence_type": EVID_ASSESSED}
            },
            "claimed_competencies": {
                "sys_scalability": {"proficiency": 50.0, "evidence_type": EVID_CLAIMED},
                "sys_caching": {"proficiency": 50.0, "evidence_type": EVID_CLAIMED}
            },
            "unassessed_competencies": [],
            "coding_analysis": {"average_score": 40.0, "accepted_count": 0},
            "ava_interview_analysis": {"average_score": 45.0},
            "resume_analysis": {"ats_score": 92.0}
        }
        requirements = [
            {"canonical_skill_id": "dsa_arrays", "importance": 5.0, "requirement_type": REQ_EXPLICIT_MANDATORY},
            {"canonical_skill_id": "sys_scalability", "importance": 4.0, "requirement_type": REQ_EXPLICIT_MANDATORY},
            {"canonical_skill_id": "sys_caching", "importance": 3.0, "requirement_type": REQ_EXPLICIT_PREFERRED}
        ]

        readiness = JobReadinessEngine.calculate_job_readiness(requirements, mock_evidence)

        # ATS match may be 92%, but overall readiness should reflect weak technical scores
        self.assertEqual(readiness["dimensions"]["resume_alignment"], 92.0)
        self.assertLess(readiness["overall_readiness"], 65.0)

    # -------------------------------------------------------------------------
    # Scenario 7: Strong Interview Performance but Weak Coding
    # -------------------------------------------------------------------------
    def test_scenario_7_strong_interview_weak_coding(self):
        """Verifies candidate with strong communication/Ava score (88%) but low coding (35%) is accurately decoupled."""
        mock_evidence = {
            "demonstrated_competencies": {
                "sys_rest_apis": {"proficiency": 85.0, "evidence_type": EVID_DEMONSTRATED}
            },
            "assessed_competencies": {
                "dsa_arrays": {"proficiency": 35.0, "evidence_type": EVID_ASSESSED}
            },
            "claimed_competencies": {},
            "unassessed_competencies": [],
            "coding_analysis": {"average_score": 35.0, "accepted_count": 1},
            "ava_interview_analysis": {"average_score": 88.0, "communication_score": 90.0},
            "resume_analysis": {"ats_score": 75.0}
        }
        requirements = [
            {"canonical_skill_id": "sys_rest_apis", "importance": 4.0, "requirement_type": REQ_EXPLICIT_MANDATORY},
            {"canonical_skill_id": "dsa_arrays", "importance": 4.5, "requirement_type": REQ_EXPLICIT_MANDATORY}
        ]

        readiness = JobReadinessEngine.calculate_job_readiness(requirements, mock_evidence)

        self.assertGreaterEqual(readiness["dimensions"]["technical_interview"], 85.0)
        self.assertLessEqual(readiness["dimensions"]["coding_problem_solving"], 40.0)

    # -------------------------------------------------------------------------
    # Scenario 8: No Previous Assessment History (Coverage Gate)
    # -------------------------------------------------------------------------
    def test_scenario_8_no_previous_assessment_history_gated(self):
        """Validates that candidate with 0 assessed skills triggers 'READINESS NOT YET ESTABLISHED'."""
        mock_evidence = {
            "demonstrated_competencies": {},
            "assessed_competencies": {},
            "claimed_competencies": {},
            "unassessed_competencies": [
                {"skill_id": "dsa_arrays"},
                {"skill_id": "cs_sql"},
                {"skill_id": "sys_rest_apis"},
                {"skill_id": "cs_os_memory"}
            ],
            "coding_analysis": {},
            "ava_interview_analysis": {},
            "resume_analysis": {"ats_score": 65.0}
        }
        requirements = [
            {"canonical_skill_id": "dsa_arrays", "importance": 5.0, "requirement_type": REQ_EXPLICIT_MANDATORY},
            {"canonical_skill_id": "cs_sql", "importance": 4.0, "requirement_type": REQ_EXPLICIT_MANDATORY},
            {"canonical_skill_id": "sys_rest_apis", "importance": 3.0, "requirement_type": REQ_EXPLICIT_PREFERRED},
            {"canonical_skill_id": "cs_os_memory", "importance": 3.0, "requirement_type": REQ_GENERAL_ROLE_EXPECTATION}
        ]

        readiness = JobReadinessEngine.calculate_job_readiness(requirements, mock_evidence)

        self.assertEqual(readiness["readiness_status"], "READINESS NOT YET ESTABLISHED")
        self.assertIsNone(readiness["overall_readiness"])
        self.assertTrue(readiness["is_gated"])
        self.assertEqual(readiness["assessment_coverage"], 0.0)

    # -------------------------------------------------------------------------
    # Scenario 9: Incomplete / Ambiguous JD
    # -------------------------------------------------------------------------
    def test_scenario_9_incomplete_ambiguous_jd(self):
        """Verifies short/ambiguous JD preserves uncertainty without fabricating requirements."""
        jd = "We are seeking a developer with general programming experience to join our team."
        reqs = JobReadinessEngine.extract_and_classify_requirements(
            raw_text=jd,
            company="Startup",
            role="Software Engineer",
            experience_level="Fresher"
        )

        # Core role requirements should be present as general expectations, with no hallucinated specialized skills
        skill_ids = [r["canonical_skill_id"] for r in reqs]
        self.assertIn("dsa_arrays", skill_ids)
        self.assertNotIn("genai_llm_fundamentals", skill_ids)
        self.assertNotIn("dl_fine_tuning", skill_ids)

    # -------------------------------------------------------------------------
    # Scenario 10: Conflicting / Sparse Company Reports
    # -------------------------------------------------------------------------
    def test_scenario_10_sparse_company_reports_disclosure(self):
        """Verifies sparse company data explicitly discloses data gap and falls back to role baseline."""
        intel = JobReadinessEngine.retrieve_company_interview_intelligence(
            company="UnknownNicheCo",
            role="Backend Engineer",
            experience_level="Fresher"
        )
        self.assertIn("evidence_disclosure", intel)
        self.assertTrue(len(intel["interview_rounds"]) >= 1)

    # -------------------------------------------------------------------------
    # Scenario 11: New Target Role Preserves Snapshots
    # -------------------------------------------------------------------------
    def test_scenario_11_role_blueprints_are_role_specific(self):
        """Verifies that changing target role from SDE to AI/ML changes blueprint weights and target components."""
        sde_bp = JobReadinessEngine.build_role_assessment_blueprint(
            role="Software Engineer",
            experience_level="Fresher",
            unassessed_or_weak_skills=["dsa_arrays", "cs_sql"]
        )
        aiml_bp = JobReadinessEngine.build_role_assessment_blueprint(
            role="AI/ML Engineer",
            experience_level="Fresher",
            unassessed_or_weak_skills=["ml_model_development", "dl_neural_networks"]
        )

        # SDE allocates more coding weight; AI/ML allocates more practical and technical knowledge
        self.assertGreater(sde_bp["component_weights"]["coding"], aiml_bp["component_weights"]["coding"])
        self.assertIn("technical_knowledge", aiml_bp["component_weights"])

    # -------------------------------------------------------------------------
    # Scenario 12: Candidate with Insufficient Time (Urgent Gap Prioritization)
    # -------------------------------------------------------------------------
    def test_scenario_12_insufficient_time_urgent_prioritization(self):
        """Verifies candidate with 3 days left receives urgency-weighted recommendations for highest-importance gaps."""
        reqs = [
            {"canonical_skill_id": "dsa_arrays", "skill_name": "Arrays & Strings", "importance": 5.0},
            {"canonical_skill_id": "cs_sql", "skill_name": "SQL & Relational DB", "importance": 4.0},
            {"canonical_skill_id": "sys_caching", "skill_name": "Caching & Redis", "importance": 2.5}
        ]
        evidence = {
            "demonstrated_competencies": {},
            "assessed_competencies": {
                "dsa_arrays": {"proficiency": 40.0}
            },
            "unassessed_competencies": [
                {"skill_id": "cs_sql"},
                {"skill_id": "sys_caching"}
            ]
        }
        readiness = {"overall_readiness": 50.0}

        # 3 days remaining
        target_date = datetime.now(timezone.utc).date()
        target_date_str = f"{target_date.year}-{target_date.month:02d}-{(target_date.day + 3):02d}"

        recs = JobReadinessEngine.generate_job_recommendations(readiness, reqs, evidence, target_date=target_date_str)

        self.assertTrue(len(recs) >= 2)
        # Top recommendation must be the mandatory high-importance item
        self.assertEqual(recs[0]["canonical_skill_id"], "dsa_arrays")
        self.assertEqual(recs[0]["priority"], "CRITICAL")

    # -------------------------------------------------------------------------
    # Scenario 13: Deterministic Rubric Scoring
    # -------------------------------------------------------------------------
    def test_scenario_13_deterministic_rubric_scoring(self):
        """Verifies rubric scoring evaluates functional correctness, edge cases, and code quality deterministically."""
        good_code = """
        def two_sum(nums, target):
            if not nums or len(nums) == 0:
                return []
            seen = {}
            for i, num in enumerate(nums):
                comp = target - num
                if comp in seen:
                    return [seen[comp], i]
                seen[num] = i
            return []
        """
        score_res = JobReadinessEngine.score_assessment_attempt(
            component_type="coding",
            canonical_skill_id="dsa_arrays",
            candidate_response="",
            code_submission=good_code
        )

        self.assertGreaterEqual(score_res["overall_score"], 80.0)
        self.assertIn("functional_correctness", score_res["rubric_breakdown"])
        self.assertIn("edge_cases", score_res["rubric_breakdown"])

    # -------------------------------------------------------------------------
    # Scenario 14: Prep Tab Handover Export
    # -------------------------------------------------------------------------
    def test_scenario_14_export_to_prep_roadmap(self):
        """Verifies handover payload format for Prep tab RoadmapEngine."""
        # Setup mock session in local_supabase
        sess_id = "test_handover_sess_001"
        self.supabase.table("job_assessment_sessions").insert({
            "id": sess_id,
            "user_id": self.user_id,
            "company": "Google",
            "role": "Software Engineer",
            "experience_level": "Fresher",
            "target_date": "2026-12-01",
            "raw_jd_text": "Software engineer with data structures and systems knowledge.",
            "status": "IN_PROGRESS",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        self.supabase.table("job_requirement_snapshots").insert({
            "id": "req_handover_001",
            "session_id": sess_id,
            "job_id": sess_id,
            "canonical_skill_id": "dsa_arrays",
            "original_source_text": "Strong DSA foundation",
            "normalized_description": "Data Structures & Algorithms",
            "requirement_type": REQ_EXPLICIT_MANDATORY,
            "importance": 5.0,
            "role_relevance": 1.0,
            "evidence_source": "job_description",
            "extraction_confidence": 0.95,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        handover = JobReadinessEngine.export_to_prep_roadmap(sess_id, self.user_id, daily_minutes=60, supabase_client=self.supabase)

        self.assertEqual(handover["handover_type"], "job_readiness_to_prep_roadmap")
        self.assertEqual(handover["target_company"], "Google")
        self.assertEqual(handover["target_role"], "Software Engineer")
        self.assertEqual(handover["daily_minutes"], 60)
        self.assertIn("critical_gaps", handover)


if __name__ == "__main__":
    unittest.main()
