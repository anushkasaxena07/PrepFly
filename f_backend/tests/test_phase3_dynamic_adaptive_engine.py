import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_supabase import SQLiteSupabaseMock
from services.question_generator import QuestionGenerator
from services.adaptive_assessment_engine import AdaptiveAssessmentEngine
from services.career_goal_service import CareerGoalService

class TestPhase3DynamicAdaptiveEngine(unittest.TestCase):
    """
    Validates Phase 3 deliverables:
      1. QuestionGenerator (Role relevance, client sanitization, variation hashes)
      2. AdaptiveAssessmentEngine (Turn-by-turn CAT, idempotency, rubric grading, state calibration)
    """

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"test-user-{uuid.uuid4()}"

    def test_01_question_generator_role_relevance_and_sanitization(self):
        """Verifies AI/ML requests produce ML questions (never generic OS) and rubrics are stripped for client."""
        context = {
            "role": "AI/ML Engineer",
            "skill_id": "dl_transformers",
            "difficulty": "Intermediate",
            "experience_level": "Fresher"
        }
        item = QuestionGenerator.generate_question(context)
        
        # Verify domain relevance
        self.assertEqual(item["skill_id"], "dl_transformers")
        self.assertIn("attention", item["question_text"].lower())
        self.assertTrue(len(item["variation_hash"]) > 0)
        self.assertIn("rubric", item)
        self.assertIn("expected_concepts", item)

        # Verify client sanitization strips internal scoring keys
        client_view = QuestionGenerator.sanitize_for_client(item)
        self.assertNotIn("rubric", client_view)
        self.assertNotIn("expected_concepts", client_view)
        self.assertIn("question_text", client_view)
        self.assertIn("skill_name", client_view)

    def test_02_adaptive_session_start_and_turn_progression(self):
        """Verifies start_session initializes session and turn 1 question."""
        session = AdaptiveAssessmentEngine.start_session(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            job_description="Developing transformer models with PyTorch and attention mechanisms.",
            question_budget=3,
            supabase_client=self.client
        )
        self.assertEqual(session["status"], "IN_PROGRESS")
        self.assertEqual(session["turn_index"], 1)
        self.assertEqual(session["progress"]["total"], 3)
        self.assertIsNotNone(session["current_question"])
        
        # Question 1 must be role-relevant
        q1 = session["current_question"]
        self.assertIn(q1["skill_id"], ["dl_transformers", "genai_llm_fundamentals", "math_probability_statistics", "dl_neural_networks"])

    def test_03_turn_submission_idempotency_and_state_updates(self):
        """Verifies turn evaluation updates candidate states and handles duplicate submissions idempotently."""
        session = AdaptiveAssessmentEngine.start_session(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            job_description="Research in Transformer attention architectures and Large Language Models.",
            question_budget=3,
            supabase_client=self.client
        )
        ass_id = session["assessment_id"]
        idempotency_key = f"key_{uuid.uuid4()}"

        answer = "Scaled dot-product attention projects inputs into Query, Key, and Value vectors and divides by sqrt(d_k) to prevent vanishing gradients."
        
        # Turn 1 Submission
        turn1_res = AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer=answer,
            idempotency_key=idempotency_key,
            supabase_client=self.client
        )
        self.assertEqual(turn1_res["status"], "IN_PROGRESS")
        self.assertEqual(turn1_res["turn_index"], 2)
        self.assertTrue(turn1_res["evaluation"]["score"] >= 60.0)

        # Verify skill state was updated
        state_res = self.client.table("candidate_skill_states").select("*").eq("user_id", self.user_id).execute()
        self.assertTrue(state_res.data)
        self.assertTrue(state_res.data[0]["proficiency"] >= 60.0)

        # Duplicate submission with same turn_index should return cached result without duplicating evidence
        evidence_count_before = len(self.client.table("skill_evidence").select("*").eq("user_id", self.user_id).execute().data or [])
        turn1_dup = AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer=answer,
            idempotency_key=idempotency_key,
            supabase_client=self.client
        )
        evidence_count_after = len(self.client.table("skill_evidence").select("*").eq("user_id", self.user_id).execute().data or [])
        self.assertEqual(evidence_count_before, evidence_count_after)
        self.assertTrue(turn1_dup["evaluation"].get("cached", False))

    def test_04_session_completion_and_scorecard(self):
        """Verifies completing all turns finalizes assessment and records audit log."""
        session = AdaptiveAssessmentEngine.start_session(
            user_id=self.user_id,
            target_role="Backend Developer",
            question_budget=2,
            supabase_client=self.client
        )
        ass_id = session["assessment_id"]

        # Turn 1
        AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer="Idempotence means multiple identical requests have the same side effect as a single request.",
            idempotency_key=str(uuid.uuid4()),
            supabase_client=self.client
        )

        # Turn 2 (Final turn)
        turn2_res = AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=2,
            answer="Cache-Aside queries cache first, then database on miss, and populates the cache.",
            idempotency_key=str(uuid.uuid4()),
            supabase_client=self.client
        )
        self.assertEqual(turn2_res["status"], "COMPLETED")
        self.assertTrue(turn2_res["overall_score"] > 0)
        self.assertTrue(turn2_res["confidence"] > 0)
        self.assertEqual(turn2_res["coverage_pct"], 100.0)

        # Verify assessment record marked as completed in DB
        db_ass = self.client.table("assessments").select("*").eq("id", ass_id).execute().data[0]
        self.assertEqual(db_ass["status"], "completed")
        self.assertIsNotNone(db_ass["score"])

    def test_05_resume_in_progress_session(self):
        """Verifies resume_session restores active uncompleted question."""
        session = AdaptiveAssessmentEngine.start_session(
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            question_budget=3,
            supabase_client=self.client
        )
        ass_id = session["assessment_id"]

        # Turn 1 answered
        AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer="Backpropagation computes gradients of loss with respect to weights using chain rule.",
            idempotency_key=str(uuid.uuid4()),
            supabase_client=self.client
        )

        # Resume call
        resumed = AdaptiveAssessmentEngine.resume_session(ass_id, self.user_id, supabase_client=self.client)
        self.assertEqual(resumed["status"], "in_progress")
        self.assertEqual(resumed["answered"], 1)
        self.assertEqual(resumed["total"], 3)
        self.assertIsNotNone(resumed["current_question"])

if __name__ == "__main__":
    unittest.main()
