import unittest
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_supabase import SQLiteSupabaseMock

class TestMigration008Schema(unittest.TestCase):
    """
    Validates Migration 008 tables, constraints, schema integrity, and local SQLite mock.
    Tables audited:
      - career_goals
      - skill_catalogue
      - job_skill_requirements
      - assessment_items
      - evaluations
      - skill_evidence
      - candidate_skill_states
      - score_audit_log
    """

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"test-user-{uuid.uuid4()}"
        self.now_iso = datetime.now(timezone.utc).isoformat()

    def test_migration_sql_file_exists_and_is_well_formed(self):
        migration_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "migrations",
            "008_evidence_based_diagnostic_and_scoring.sql"
        )
        self.assertTrue(os.path.exists(migration_path))
        with open(migration_path, "r", encoding="utf-8") as f:
            sql = f.read()

        tables = [
            "career_goals",
            "skill_catalogue",
            "job_skill_requirements",
            "assessment_items",
            "evaluations",
            "skill_evidence",
            "candidate_skill_states",
            "score_audit_log"
        ]
        for tbl in tables:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {tbl}", sql)
            self.assertIn(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;", sql)

    def test_career_goals_crud(self):
        goal_id = str(uuid.uuid4())
        self.client.table("career_goals").insert({
            "id": goal_id,
            "user_id": self.user_id,
            "role_id": "ai_ml_engineer",
            "custom_role": None,
            "target_company": "DeepMind",
            "job_description": "Building next-gen LLMs and Transformers",
            "experience_level": "Fresher",
            "status": "active",
            "created_at": self.now_iso,
            "updated_at": self.now_iso
        }).execute()

        res = self.client.table("career_goals").select("*").eq("user_id", self.user_id).execute()
        self.assertTrue(res.data)
        self.assertEqual(res.data[0]["role_id"], "ai_ml_engineer")
        self.assertEqual(res.data[0]["target_company"], "DeepMind")

    def test_skill_catalogue_crud(self):
        skill_id = "dl_transformers"
        self.client.table("skill_catalogue").insert({
            "id": skill_id,
            "canonical_name": "Transformer Architectures",
            "domain": "ai_ml",
            "category": "deep_learning",
            "difficulty_floor": "Intermediate",
            "difficulty_ceiling": "Advanced",
            "prerequisites": ["dl_neural_networks"],
            "created_at": self.now_iso
        }).execute()

        res = self.client.table("skill_catalogue").select("*").eq("id", skill_id).execute()
        self.assertTrue(res.data)
        self.assertEqual(res.data[0]["canonical_name"], "Transformer Architectures")

if __name__ == "__main__":
    unittest.main()

