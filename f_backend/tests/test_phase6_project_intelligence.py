import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_supabase import SQLiteSupabaseMock
from services.project_intelligence_service import ProjectIntelligenceService

class TestPhase6ProjectIntelligence(unittest.TestCase):
    """
    Validates Phase 6 Project Intelligence Engine:
      1. Technology mapping to canonical skill taxonomy
      2. Automated generation of deep technical defense probing questions
      3. Persistence in candidate_project_analyses and project_technical_questions
      4. Defense evaluation with substantive technical verification
    """

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"test-user-{uuid.uuid4()}"

    def test_01_technology_mapping_to_canonical_skills(self):
        """Verifies raw tech strings map to canonical skill IDs in the ontology."""
        techs = ["PyTorch", "Transformers", "Kafka", "Redis", "PostgreSQL"]
        mapped = ProjectIntelligenceService.map_technologies_to_skills(techs)
        
        self.assertIn("dl_frameworks_pytorch_tensorflow", mapped)
        self.assertIn("dl_transformers", mapped)
        self.assertIn("sys_message_queues", mapped)
        self.assertIn("sys_caching", mapped)
        self.assertIn("cs_dbms", mapped)

    def test_02_project_analysis_and_probing_questions_persistence(self):
        """Verifies project analysis and 3 architectural probing questions are generated and stored."""
        title = "Distributed Real-Time Chat Engine"
        description = "A high-concurrency WebSocket messaging service with Redis pub/sub and PostgreSQL message archival."
        techs = ["Redis", "PostgreSQL", "WebSockets", "Go"]

        res = ProjectIntelligenceService.analyze_and_persist_project(
            user_id=self.user_id,
            project_title=title,
            description=description,
            technologies=techs,
            supabase_client=self.client
        )

        project_id = res["project_id"]
        self.assertTrue(project_id)
        self.assertEqual(len(res["probing_questions"]), 3)

        # Verify rows in database
        analysis_db = self.client.table("candidate_project_analyses").select("*").eq("id", project_id).execute()
        self.assertTrue(analysis_db.data)
        self.assertEqual(analysis_db.data[0]["project_title"], title)

        questions_db = self.client.table("project_technical_questions").select("*").eq("project_id", project_id).execute()
        self.assertEqual(len(questions_db.data), 3)
        focus_areas = {q["focus_area"] for q in questions_db.data}
        self.assertIn("Architecture & Data Flow", focus_areas)
        self.assertIn("Trade-offs & Concurrency", focus_areas)

    def test_03_superficial_defense_receives_low_score(self):
        """Verifies short/evasive defenses fail to establish genuine architectural ownership."""
        defense_res = ProjectIntelligenceService.evaluate_project_defense(
            user_id=self.user_id,
            project_title="Recommendation Feed",
            skill_id="sys_ml_system_design",
            question_text="How did you handle 50x traffic scale?",
            candidate_response="I used AWS EC2 and it was fine.",
            supabase_client=self.client
        )
        self.assertEqual(defense_res["score"], 35.0)
        self.assertEqual(defense_res["classification"], "Superficial / Inconclusive Defense")

    def test_04_authoritative_technical_defense_awards_verified_evidence(self):
        """Verifies deep substantive defenses citing trade-offs and mechanisms receive authoritative score and evidence."""
        rigorous_defense = (
            "We encountered a massive bottleneck on the primary PostgreSQL database due to write-lock contention. "
            "To solve this trade-off between consistency and latency, we introduced a Redis write-behind cache buffer with "
            "worker processes batching inserts. We partitioned the event queue by user_id to eliminate race conditions "
            "and implemented connection pool timeouts to prevent connection exhaustion under 50x throughput."
        )
        defense_res = ProjectIntelligenceService.evaluate_project_defense(
            user_id=self.user_id,
            project_title="Distributed Real-Time Chat Engine",
            skill_id="sys_caching",
            question_text="Describe your concurrency and database bottlenecks under 50x scale.",
            candidate_response=rigorous_defense,
            supabase_client=self.client
        )
        self.assertEqual(defense_res["score"], 88.0)
        self.assertEqual(defense_res["classification"], "Demonstrated Authoritative Ownership")
        self.assertTrue(defense_res["evidence_id"])

        # Verify evidence logged in skill_evidence
        ev_db = self.client.table("skill_evidence").select("*").eq("user_id", self.user_id).execute()
        self.assertTrue(ev_db.data)
        self.assertEqual(ev_db.data[0]["score"], 88.0)

if __name__ == "__main__":
    unittest.main()
