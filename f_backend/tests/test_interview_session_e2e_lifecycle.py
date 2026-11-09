"""
E2E Verification Test Suite for PrepFly AI Interview Session Lifecycle
Covers:
1. Resume upload / non-resume session creation
2. Immediate session persistence in Supabase
3. POST /start-interview retrieval, authorization and AI interviewer initialization
4. Question generation and progression
5. Candidate turn response and evidence ingestion
6. Unauthorized user IDOR rejection (404)
7. Invalid session ID rejection (404)
8. Completed session rejection on replay (404)
"""

import unittest
import json
import uuid
import sys
import os
import io
from unittest.mock import patch, MagicMock

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app, supabase
from local_supabase import SQLiteSupabaseMock
import jwt
from werkzeug.datastructures import FileStorage

class TestInterviewSessionE2ELifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.jwt_secret = os.getenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
        
        cls.user_a_id = str(uuid.uuid4())
        cls.user_b_id = str(uuid.uuid4())

        cls.user_a_token = jwt.encode(
            {"sub": cls.user_a_id, "user_id": cls.user_a_id, "email": "candidate_a@prepfly.io", "role": "STUDENT"},
            cls.jwt_secret,
            algorithm="HS256"
        )
        cls.user_b_token = jwt.encode(
            {"sub": cls.user_b_id, "user_id": cls.user_b_id, "email": "candidate_b@prepfly.io", "role": "STUDENT"},
            cls.jwt_secret,
            algorithm="HS256"
        )

    @patch("app.evaluate_response_comprehensive", return_value={
        "feedback": "Solid answer on model inference decoupling.",
        "score": 8.5,
        "accuracy_score": 85,
        "strengths": ["Clear explanation"],
        "weaknesses": [],
        "correctness": "Correct"
    })
    @patch("app.generate_dynamic_question", return_value=("Explain the difference between a process and a thread.", "technical", {}))
    @patch("app.analyze_live_response", return_value={
        "feedback": "Clear explanation of thread vs process memory sharing.",
        "score": 88,
        "score_10": 8.8,
        "strengths": ["Good explanation of heap sharing"],
        "weaknesses": [],
        "filler_count": 0,
        "pacing_wpm": 125,
        "clarity": 90,
        "relevance": 85
    })
    def test_01_full_interview_lifecycle_create_start_turn_end(self, mock_analyze, mock_gen_q, mock_eval):
        """Tests complete end-to-end flow: Upload -> Create -> Start -> Answer -> End."""
        # 1. Create session via non-resume endpoint
        create_res = self.client.post(
            "/create-session-no-resume",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={
                "user_id": self.user_a_id,
                "role": "AI/ML Engineer",
                "tools": "PyTorch, Transformers, Python, System Design",
                "experience": "2-4 Years",
                "category": "Machine Learning & AI",
                "difficulty": "Intermediate",
                "job_description": "Building large-scale deep learning models and RAG pipelines.",
                "consent": True
            }
        )
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.get_json()["session_id"]
        self.assertTrue(session_id)

        # 2. Verify session exists in database
        db_res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        self.assertTrue(db_res and db_res.data and len(db_res.data) > 0)
        sess_record = db_res.data[0]
        self.assertEqual(sess_record.get("role"), "AI/ML Engineer")
        self.assertTrue(sess_record.get("active", True))

        # 3. Start Interview as User A
        start_res = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={
                "session_id": session_id,
                "role": "AI/ML Engineer",
                "category": "Machine Learning & AI",
                "difficulty": "Intermediate",
                "personality": "professional"
            }
        )
        self.assertEqual(start_res.status_code, 200)
        start_data = start_res.get_json()
        self.assertTrue(start_data.get("question"))
        self.assertEqual(start_data.get("question_number"), 1)

        # 4. Submit Answer to Question 1
        next_res = self.client.post(
            "/next",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={
                "session_id": session_id,
                "answer": "To scale model inference under strict latency budgets, we decouple lightweight vector retrieval using an ANN index from deep cross-encoder reranking.",
                "current_question": start_data.get("question"),
                "question_index": 1
            }
        )
        self.assertEqual(next_res.status_code, 200)
        next_data = next_res.get_json()
        self.assertTrue(next_data.get("question") or next_data.get("next_question"))
        self.assertEqual(next_data.get("question_number"), 2)

        # 5. End Interview
        end_res = self.client.post(
            "/end-interview",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={"session_id": session_id}
        )
        self.assertEqual(end_res.status_code, 200)
        end_data = end_res.get_json()
        self.assertTrue("report" in end_data or "overall_score" in end_data)

        # 6. Verify Session is marked completed and cannot be restarted
        replay_res = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={"session_id": session_id}
        )
        self.assertEqual(replay_res.status_code, 404)

    def test_02_idor_unauthorized_user_cannot_start_session(self):
        """User B cannot start User A's session."""
        create_res = self.client.post(
            "/create-session-no-resume",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={
                "user_id": self.user_a_id,
                "role": "Software Engineer",
                "tools": "Java, Spring, PostgreSQL",
                "consent": True
            }
        )
        session_id = create_res.get_json()["session_id"]

        # User B attempts to start User A's session
        b_res = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_b_token}"},
            json={"session_id": session_id}
        )
        self.assertEqual(b_res.status_code, 404)

    def test_03_non_existent_session_id_returns_404(self):
        """Non-existent UUID returns clean 404."""
        bogus_id = str(uuid.uuid4())
        res = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={"session_id": bogus_id}
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.get_json()["error"].lower())

    @patch("werkzeug.datastructures.FileStorage.save", return_value=None)
    @patch("app.generate_dynamic_question", return_value=("Tell me about a challenging project from your resume.", "resume", {}))
    @patch("app.extract_text_from_pdf", return_value="John Doe\nSenior Machine Learning Engineer\nSkills: Python, PyTorch, LLMs")
    @patch("app.parse_resume_content", return_value={"ats_score": 85, "structured_data": {"name": "John Doe", "skills": ["Python", "PyTorch"]}, "missing_info": []})
    def test_04_resume_upload_creates_persisted_session(self, mock_parse, mock_extract, mock_gen_q, mock_save):
        """Resume upload successfully creates and persists session with ATS score."""
        dummy_resume = b"dummy pdf content"
        upload_res = self.client.post(
            "/upload",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            data={
                "resume": (io.BytesIO(dummy_resume), "resume.pdf"),
                "consent": "true",
                "user_id": self.user_a_id
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(upload_res.status_code, 200)
        data = upload_res.get_json()
        session_id = data["session_id"]
        self.assertTrue(session_id)
        self.assertEqual(data.get("ats_score"), 85)

        # Verify session can immediately be retrieved and started
        start_res = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={"session_id": session_id, "category": "Resume", "difficulty": "Medium"}
        )
        self.assertEqual(start_res.status_code, 200)
        self.assertTrue(start_res.get_json().get("question"))

if __name__ == "__main__":
    unittest.main()
