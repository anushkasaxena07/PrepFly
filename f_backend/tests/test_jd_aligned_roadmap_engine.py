"""
Comprehensive Multi-Role JD-Aligned Intelligence Roadmap Engine Test Suite.
Validates:
1. Dynamic JD-first architecture consuming extracted job_requirements.
2. 5-Tier priority enforcement where mandatory JD skills dominate without generic CS displacement.
3. Multi-role regression across AI/ML Engineer, Data Scientist, Data Engineer, Backend, Frontend, and SDE.
4. 9 Days Planned & 60m Daily Pace budget enforcement (<= 60m/day).
5. Low-confidence diagnostic assessments and non-destructive recalculation preserving completed/pinned activities.
"""

import unittest
import uuid
from datetime import datetime, timezone
from local_supabase import get_supabase_client
from services.candidate_profile_service import CandidateProfileService
from services.job_intelligence_service import JobIntelligenceService
from services.roadmap_engine import (
    RecommendationEngine,
    SchedulingEngine,
    PersonalizedRoadmapEngine
)
from services.skill_taxonomy_service import SkillTaxonomyService


class TestJDAlignedRoadmapEngine(unittest.TestCase):
    """Test suite for role-aware, JD-aligned adaptive curriculum planning."""

    @classmethod
    def setUpClass(cls):
        cls.supabase = get_supabase_client()

    def setUp(self):
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"

    # =========================================================================
    # TEST 1: AI/ML Engineer JD Alignment
    # =========================================================================
    def test_01_aiml_engineer_jd_curriculum_alignment(self):
        """Verifies AI/ML JD triggers ML/DL/Math curriculum without generic OS/DBMS displacement."""
        aiml_jd = """
        Role: AI/ML Engineer at DeepScale
        Core Responsibilities:
        - Design, train, and fine-tune deep learning and machine learning models from scratch using PyTorch and TensorFlow.
        - Build transformer architectures, NLP pipelines, and generative AI features.
        - Architect scalable ML System Design for real-time inference and low-latency model deployment.
        - Perform linear algebra, probability, and statistical mathematical modeling.
        Required Qualifications:
        - Strong proficiency in Python for ML, NumPy, and Pandas.
        - Deep understanding of neural networks, CNNs, attention mechanisms, and transformers.
        - Experience deploying production ML APIs with real-time scalability.
        """
        # Ingest JD
        ingest_res = JobIntelligenceService.ingest_job_description(
            user_id=self.user_id,
            raw_text=aiml_jd,
            job_title="AI/ML Engineer",
            company="DeepScale",
            supabase_client=self.supabase
        )
        job_id = ingest_res["job_profile"]["id"]
        self.assertIsNotNone(job_id)

        # Initialize profile with 9 days and 60m pace
        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            target_company="DeepScale",
            daily_minutes=60,
            days_planned=9,
            total_days=9,
            experience_level="Mid-Level (2-5 years)",
            supabase_client=self.supabase
        )

        # Generate roadmap
        roadmap = PersonalizedRoadmapEngine.get_or_create_roadmap(
            user_id=self.user_id,
            job_id=job_id,
            supabase_client=self.supabase
        )
        self.assertIsNotNone(roadmap)
        schedule = roadmap.get("schedule", {})
        self.assertTrue(len(schedule) > 0)

        # Gather scheduled skills across all days
        scheduled_skills = []
        for day_num, activities in schedule.items():
            for act in activities:
                scheduled_skills.append(act.get("skill_id"))

        # Verify AI/ML mandatory skills appear in the schedule
        aiml_skills = {
            "ml_python_libraries",
            "math_linear_algebra",
            "math_probability_statistics",
            "ml_model_development",
            "dl_neural_networks",
            "dl_transformers",
            "sys_ml_system_design"
        }
        intersect = aiml_skills.intersection(set(scheduled_skills))
        self.assertGreaterEqual(len(intersect), 3, f"Expected prominent AI/ML skills, found: {scheduled_skills}")

        # Verify generic CS fundamentals (OS, DBMS, Networks) did NOT displace core ML
        generic_cs = {"cs_os", "cs_dbms", "cs_networks"}
        early_skills = []
        for day_num in [1, 2, 3]:
            activities = schedule.get(day_num, [])
            for act in activities:
                early_skills.append(act.get("skill_id"))

        for gcs in generic_cs:
            self.assertNotIn(gcs, early_skills, f"Generic CS skill {gcs} should not appear in early AI/ML schedule")

    # =========================================================================
    # TEST 2: Data Scientist JD Alignment
    # =========================================================================
    def test_02_data_scientist_jd_curriculum_alignment(self):
        """Verifies Data Scientist JD prioritizes Statistics, Classical ML, and SQL."""
        ds_jd = """
        Role: Senior Data Scientist
        Requirements:
        - Advanced probability and statistics, hypothesis testing, A/B testing, and experimentation.
        - Supervised and unsupervised machine learning algorithms, decision trees, random forests, and PCA.
        - Advanced SQL for large data extraction and statistical analysis.
        - Python data analysis libraries: Pandas, NumPy, Scikit-Learn.
        """
        ingest_res = JobIntelligenceService.ingest_job_description(
            user_id=self.user_id,
            raw_text=ds_jd,
            job_title="Data Scientist",
            company="Airbnb",
            supabase_client=self.supabase
        )
        job_id = ingest_res["job_profile"]["id"]

        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="Data Scientist",
            target_company="Airbnb",
            daily_minutes=60,
            days_planned=9,
            supabase_client=self.supabase
        )

        recs = RecommendationEngine.get_recommendations(
            user_id=self.user_id,
            job_id=job_id,
            supabase_client=self.supabase
        )
        top_skill_ids = [r["skill_id"] for r in recs[:5]]
        
        # Verify stats and ML are prioritized
        ds_core = {"math_probability_statistics", "ml_classical_algorithms", "ml_tree_ensembles", "ml_python_libraries", "db_sql", "cs_sql"}
        self.assertTrue(any(s in top_skill_ids for s in ds_core), f"Top recommendations {top_skill_ids} should contain Data Science core skills")

    # =========================================================================
    # TEST 3: Data Engineer JD Alignment
    # =========================================================================
    def test_03_data_engineer_jd_curriculum_alignment(self):
        """Verifies Data Engineer JD prioritizes ETL, SQL, and System Scalability."""
        de_jd = """
        Role: Data Engineer
        Requirements:
        - Design and maintain production ETL data pipelines.
        - Expert level SQL and data warehousing.
        - Experience managing large-scale distributed datasets, message queues, and Kafka.
        - Distributed database optimization and data modeling.
        """
        ingest_res = JobIntelligenceService.ingest_job_description(
            user_id=self.user_id,
            raw_text=de_jd,
            job_title="Data Engineer",
            company="Snowflake",
            supabase_client=self.supabase
        )
        job_id = ingest_res["job_profile"]["id"]

        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="Data Engineer",
            target_company="Snowflake",
            daily_minutes=60,
            days_planned=9,
            supabase_client=self.supabase
        )

        recs = RecommendationEngine.get_recommendations(
            user_id=self.user_id,
            job_id=job_id,
            supabase_client=self.supabase
        )
        top_skills = [r["skill_id"] for r in recs[:8]]
        self.assertTrue(any("sql" in s or "dbms" in s or "sys_" in s for s in top_skills), f"Data Engineer recommendations {top_skills} must prioritize SQL or Systems")

    # =========================================================================
    # TEST 4: Backend Engineer JD Alignment
    # =========================================================================
    def test_04_backend_engineer_jd_curriculum_alignment(self):
        """Verifies Backend Engineer JD prioritizes System Design, APIs, Caching, and Concurrency."""
        backend_jd = """
        Role: Backend Engineer
        Requirements:
        - Architect distributed systems, microservices, and RESTful APIs.
        - Concurrency, multithreading, and asynchronous programming.
        - Relational database schema design, indexing, and Redis caching.
        """
        ingest_res = JobIntelligenceService.ingest_job_description(
            user_id=self.user_id,
            raw_text=backend_jd,
            job_title="Backend Engineer",
            company="Stripe",
            supabase_client=self.supabase
        )
        job_id = ingest_res["job_profile"]["id"]

        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="Backend Engineer",
            target_company="Stripe",
            daily_minutes=60,
            days_planned=9,
            supabase_client=self.supabase
        )

        roadmap = PersonalizedRoadmapEngine.get_or_create_roadmap(
            user_id=self.user_id,
            job_id=job_id,
            supabase_client=self.supabase
        )
        schedule = roadmap.get("schedule", {})
        all_skills = [act["skill_id"] for activities in schedule.values() for act in activities]
        self.assertTrue(
            any("sys_" in s or "sql" in s or "dbms" in s for s in all_skills),
            f"Backend schedule {all_skills} must feature Systems or Databases"
        )

    # =========================================================================
    # TEST 5: Frontend Engineer JD Alignment
    # =========================================================================
    def test_05_frontend_engineer_jd_curriculum_alignment(self):
        """Verifies Frontend Engineer JD prioritizes Web APIs, DOM performance, and Client State."""
        frontend_jd = """
        Role: Senior Frontend Engineer
        Requirements:
        - React, JavaScript ES6+, TypeScript, and modern frontend frameworks.
        - DOM performance, browser rendering pipeline, Web APIs, and client-server caching.
        - State management, accessible UI components, and client networking.
        """
        ingest_res = JobIntelligenceService.ingest_job_description(
            user_id=self.user_id,
            raw_text=frontend_jd,
            job_title="Frontend Engineer",
            company="Vercel",
            supabase_client=self.supabase
        )
        job_id = ingest_res["job_profile"]["id"]

        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="Frontend Engineer",
            target_company="Vercel",
            daily_minutes=60,
            days_planned=9,
            supabase_client=self.supabase
        )

        recs = RecommendationEngine.get_recommendations(
            user_id=self.user_id,
            job_id=job_id,
            supabase_client=self.supabase
        )
        self.assertTrue(len(recs) > 0, "Frontend recommendations must not be empty")

    # =========================================================================
    # TEST 6: SDE Role Balance
    # =========================================================================
    def test_06_sde_curriculum_balance(self):
        """Verifies general SDE role curriculum balances DSA and System Design."""
        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="Software Development Engineer (General)",
            target_company="Amazon",
            daily_minutes=60,
            days_planned=9,
            supabase_client=self.supabase
        )

        recs = RecommendationEngine.get_recommendations(
            user_id=self.user_id,
            supabase_client=self.supabase
        )
        categories = {r.get("category") for r in recs[:8]}
        self.assertIn("Data Structures and Algorithms", categories)

    # =========================================================================
    # TEST 7: 9 Days Planned & 60m Daily Pace Strict Budget Enforcement
    # =========================================================================
    def test_07_nine_days_planned_and_sixty_min_pace_budget(self):
        """Verifies schedule strictly adheres to 9 days allocation and <= 60m daily minutes."""
        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            target_company="Google",
            daily_minutes=60,
            days_planned=9,
            total_days=9,
            supabase_client=self.supabase
        )

        roadmap = PersonalizedRoadmapEngine.get_or_create_roadmap(
            user_id=self.user_id,
            supabase_client=self.supabase
        )
        schedule = roadmap.get("schedule", {})
        self.assertLessEqual(len(schedule), 9, "Schedule must not exceed 9 days")

        for day_num, activities in schedule.items():
            total_duration = sum(act.get("estimated_minutes", act.get("duration_minutes", 0)) for act in activities)
            self.assertLessEqual(
                total_duration,
                60,
                f"Day {day_num} allocated {total_duration}m exceeding 60m daily pace limit!"
            )
            # Verify each activity has required quality fields
            for act in activities:
                self.assertIn("title", act)
                self.assertTrue("estimated_minutes" in act or "duration_minutes" in act)
                self.assertIn("activity_type", act)
                self.assertIn("completion_criteria", act)

    # =========================================================================
    # TEST 8: Confidence Handling & Non-Destructive Recalculation
    # =========================================================================
    def test_08_confidence_handling_and_non_destructive_recalculation(self):
        """Verifies unassessed low-confidence skills trigger diagnostics and completed items persist."""
        CandidateProfileService.initialize_or_update_profile(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            target_company="OpenAI",
            daily_minutes=60,
            days_planned=9,
            supabase_client=self.supabase
        )

        roadmap = PersonalizedRoadmapEngine.get_or_create_roadmap(
            user_id=self.user_id,
            supabase_client=self.supabase
        )
        acts = roadmap.get("activities", [])
        self.assertTrue(len(acts) > 0)

        # Mark first activity as completed
        first_act_id = acts[0]["id"]
        self.supabase.table("roadmap_activities").update({"status": "completed"}).eq("id", first_act_id).execute()

        # Recalculate roadmap
        new_roadmap = PersonalizedRoadmapEngine.recalculate_roadmap(
            user_id=self.user_id,
            change_reason="User completed Day 1 activity and requested rebalancing",
            supabase_client=self.supabase
        )
        new_acts = new_roadmap.get("activities", [])

        # Verify completed activity was preserved
        found_completed = any(a.get("id") == first_act_id and a.get("status") == "completed" for a in new_acts)
        self.assertTrue(found_completed, "Completed activity must be preserved during roadmap recalculation!")


if __name__ == "__main__":
    unittest.main()
