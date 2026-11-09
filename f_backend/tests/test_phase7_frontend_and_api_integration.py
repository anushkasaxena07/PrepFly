"""
Test Suite for Phase 7: Frontend & API Integration
Validates REST API endpoints for Career Goals and Adaptive Diagnostic Assessment.
"""

import unittest
import json
import uuid
import os
import sys
from datetime import datetime, timezone, timedelta

os.environ.setdefault("ENV", "test")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key-mock")
os.environ.setdefault("JWT_SECRET", "test-secret-key-12345678901234567890123456789012")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, _get_jwt_secret
import jwt
from local_supabase import get_supabase_client


class TestPhase7FrontendAndAPIIntegration(unittest.TestCase):
    """Verifies Career Goals endpoints and Turn-by-Turn Adaptive Assessment API."""

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self.email = f"user-{uuid.uuid4().hex[:6]}@example.com"

        # Sign JWT
        secret = _get_jwt_secret()
        self.token = jwt.encode({
            "sub": self.user_id,
            "email": self.email,
            "role": "candidate",
            "exp": datetime.now(timezone.utc) + timedelta(days=2)
        }, secret, algorithm="HS256")

        self.auth_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def test_01_supported_roles_endpoint(self):
        """Verifies GET /api/career-goals/supported-roles returns 8 canonical engineering tracks."""
        resp = self.client.get("/api/career-goals/supported-roles")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        roles = data["supported_roles"]
        role_ids = [r["role_id"] for r in roles]
        self.assertIn("ai_ml_engineer", role_ids)
        self.assertIn("software_development_engineer", role_ids)
        self.assertIn("backend_developer", role_ids)
        self.assertIn("frontend_developer", role_ids)
        self.assertIn("data_scientist", role_ids)

    def test_02_career_goal_crud_endpoints(self):
        """Verifies POST /api/career-goals creates a goal and GET /api/career-goals lists it."""
        payload = {
            "target_role": "AI/ML Engineer",
            "target_company": "DeepMind",
            "job_description": "Experience training transformer architectures and diffusion models.",
            "experience_level": "Fresher"
        }
        create_resp = self.client.post("/api/career-goals", headers=self.auth_headers, data=json.dumps(payload))
        self.assertEqual(create_resp.status_code, 201)
        created_data = create_resp.get_json()
        self.assertEqual(created_data["status"], "success")
        goal = created_data["career_goal"]
        self.assertEqual(goal["role_id"], "ai_ml_engineer")
        self.assertEqual(goal["target_company"], "DeepMind")

        # List goals
        list_resp = self.client.get("/api/career-goals", headers=self.auth_headers)
        self.assertEqual(list_resp.status_code, 200)
        list_data = list_resp.get_json()
        self.assertEqual(list_data["status"], "success")
        user_goals = [g for g in list_data["career_goals"] if g["user_id"] == self.user_id]
        self.assertGreaterEqual(len(user_goals), 1)

    def test_03_adaptive_assessment_start_endpoint(self):
        """Verifies POST /api/assessment/adaptive/start starts a 10-question adaptive assessment."""
        payload = {
            "target_role": "AI/ML Engineer",
            "job_description": "Deep Learning with attention transformers and PyTorch.",
            "experience_level": "Fresher",
            "question_budget": 10
        }
        start_resp = self.client.post("/api/assessment/adaptive/start", headers=self.auth_headers, data=json.dumps(payload))
        self.assertEqual(start_resp.status_code, 201)
        data = start_resp.get_json()
        self.assertEqual(data["status"], "success")
        ass = data["assessment"]
        self.assertIn("assessment_id", ass)
        total = ass.get("total_questions") or ass.get("question_budget") or ass.get("progress", {}).get("total")
        self.assertEqual(total, 10)
        first_q = ass.get("current_question") or ass.get("first_question")
        self.assertIsNotNone(first_q)
        self.assertIn("question_text", first_q)
        # Ensure client view is sanitized (no rubric or expected concepts leaked)
        self.assertNotIn("rubric", first_q)
        self.assertNotIn("expected_concepts", first_q)

    def test_04_adaptive_assessment_resume_endpoint(self):
        """Verifies GET /api/assessment/adaptive/<id> resumes active session on refresh."""
        # Start session
        start_resp = self.client.post("/api/assessment/adaptive/start", headers=self.auth_headers, data=json.dumps({
            "target_role": "AI/ML Engineer",
            "experience_level": "Fresher"
        }))
        ass_id = start_resp.get_json()["assessment"]["assessment_id"]

        # Resume session
        resume_resp = self.client.get(f"/api/assessment/adaptive/{ass_id}", headers=self.auth_headers)
        self.assertEqual(resume_resp.status_code, 200)
        data = resume_resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["assessment"]["assessment_id"], ass_id)
        self.assertEqual(data["assessment"]["answered"], 0)
        self.assertIsNotNone(data["assessment"]["current_question"])

    def test_05_adaptive_assessment_submit_turn_and_adaptation(self):
        """Verifies POST /api/assessment/adaptive/<id>/submit-turn evaluates turn and adapts."""
        start_resp = self.client.post("/api/assessment/adaptive/start", headers=self.auth_headers, data=json.dumps({
            "target_role": "AI/ML Engineer",
            "job_description": "Transformer self-attention query key value mechanisms.",
            "question_budget": 3  # short budget for test speed
        }))
        ass_id = start_resp.get_json()["assessment"]["assessment_id"]

        # Submit Turn 1
        turn1_payload = {
            "turn_index": 1,
            "answer": "Self-attention computes scaled dot-product attention using Query, Key, and Value matrices where attention weights are softmax(Q K^T / sqrt(d_k)) * V.",
            "idempotency_key": f"{ass_id}_turn_1"
        }
        turn1_resp = self.client.post(f"/api/assessment/adaptive/{ass_id}/submit-turn", headers=self.auth_headers, data=json.dumps(turn1_payload))
        self.assertEqual(turn1_resp.status_code, 200)
        turn1_data = turn1_resp.get_json()["result"]
        self.assertEqual(turn1_data["status"], "IN_PROGRESS")
        self.assertEqual(turn1_data["turn_index"], 2)
        self.assertGreaterEqual(turn1_data["evaluation"]["score"], 60.0)
        self.assertIsNotNone(turn1_data["next_question"])

        # Test idempotency: re-submitting turn 1 does not generate a duplicate turn
        idemp_resp = self.client.post(f"/api/assessment/adaptive/{ass_id}/submit-turn", headers=self.auth_headers, data=json.dumps(turn1_payload))
        self.assertEqual(idemp_resp.status_code, 200)
        idemp_data = idemp_resp.get_json()["result"]
        self.assertTrue(idemp_data["evaluation"]["cached"])


if __name__ == "__main__":
    unittest.main()
