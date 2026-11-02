import unittest
import json
import os
import sys

import uuid
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, supabase, _get_jwt_secret

class TestInterviewLifecycleIntegration(unittest.TestCase):
    """End-to-End Integration tests for AI Recruiter Mock Interview lifecycle and reporting."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"
        self.token = jwt.encode({"sub": self.user_id, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_complete_recruiter_interview_flow(self):
        """Full interview lifecycle: Create Session -> Start -> Hint -> Repeat -> Next Question -> End Interview."""
        # 1. Create session without resume
        create_res = self.client.post("/create-session-no-resume", headers=self.headers, json={
            "user_id": self.user_id,
            "role": "Cloud Solutions Architect",
            "tools": "AWS, Kubernetes, Terraform, Docker, Python",
            "experience": "3-5 Years",
            "category": "System Design",
            "difficulty": "Hard"
        })
        self.assertEqual(create_res.status_code, 200)
        c_data = create_res.get_json()
        session_id = c_data["session_id"]
        self.assertIsNotNone(session_id)

        # 2. Start Interview
        start_res = self.client.post("/start-interview", headers=self.headers, json={"session_id": session_id})
        self.assertEqual(start_res.status_code, 200)
        start_data = start_res.get_json()
        self.assertIn("question", start_data)
        self.assertEqual(start_data["question_number"], 1)
        self.assertIn("Phase 1", start_data["stage"])
        first_question = start_data["question"]

        # 3. Request Hint
        hint_res = self.client.post("/get-hint", headers=self.headers, json={"session_id": session_id})
        self.assertEqual(hint_res.status_code, 200)
        hint_data = hint_res.get_json()
        self.assertIn("hint", hint_data)
        self.assertTrue(len(hint_data["hint"]) > 10)

        # 4. Request Question Repetition (simulating candidate asking 'repeat')
        repeat_res = self.client.post("/next", headers=self.headers, json={
            "session_id": session_id,
            "answer": "Pardon, could you repeat the question?"
        })
        self.assertEqual(repeat_res.status_code, 200)
        repeat_data = repeat_res.get_json()
        self.assertEqual(repeat_data["next_question"], first_question)
        self.assertEqual(repeat_data["question_number"], 1)

        # 5. Submit real technical answer for Question 1
        answer_q1 = "In my previous project, we deployed microservices on AWS EKS using Terraform. We used Redis for caching to reduce database read load and implemented horizontal pod autoscalers."
        next_res = self.client.post("/next", headers=self.headers, json={
            "session_id": session_id,
            "answer": answer_q1
        })
        self.assertEqual(next_res.status_code, 200)
        next_data = next_res.get_json()
        self.assertIn("feedback", next_data)
        self.assertIn("score", next_data["feedback"])
        self.assertEqual(next_data["question_number"], 2)
        self.assertIn("next_question", next_data)

        # 6. Query /get-session state (allow async daemon thread to persist responses)
        import time
        session_data = {}
        for _ in range(10):
            time.sleep(0.15)
            session_res = self.client.get(f"/get-session?session_id={session_id}", headers=self.headers)
            self.assertEqual(session_res.status_code, 200)
            session_data = session_res.get_json()
            if len(session_data.get("responses", [])) >= 1:
                break

        self.assertEqual(session_data["session_id"], session_id)
        self.assertTrue(session_data["active"])
        self.assertEqual(len(session_data["responses"]), 1)

        # 7. End Interview and generate comprehensive evaluation
        end_res = self.client.post("/end-interview", headers=self.headers, json={"session_id": session_id})
        self.assertEqual(end_res.status_code, 200)
        end_data = end_res.get_json()
        self.assertIn("overall_score", end_data)
        self.assertIn("grade", end_data)
        self.assertIn(end_data["grade"], ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"])

        # 8. Verify session is now closed (active = False)
        db_session = supabase.table("sessions").select("active,final_grade").eq("session_id", session_id).execute()
        self.assertTrue(len(db_session.data) > 0)
        self.assertFalse(db_session.data[0]["active"])

if __name__ == "__main__":
    unittest.main()
