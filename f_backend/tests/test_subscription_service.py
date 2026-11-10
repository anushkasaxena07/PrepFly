import unittest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.subscription_service import (
    get_org_subscription_status,
    block_if_expired
)

class TestSubscriptionService(unittest.TestCase):
    """Unit tests for Organization Subscription, Free Trial, and Expiration Guard."""

    def test_get_org_subscription_status_none_org(self):
        """When org_id is None or empty, returns default 10-day trial status without error."""
        status = get_org_subscription_status(None)
        self.assertEqual(status["subscription_status"], "TRIAL")
        self.assertEqual(status["days_remaining"], 10)
        self.assertFalse(status["is_blocked"])
        self.assertEqual(status["current_plan"], "Trial")

    @patch("services.subscription_service.get_supabase")
    def test_new_organization_auto_trial_creation(self, mock_get_supabase):
        """A new organization without record should be initialized with 10 days trial."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        # First select returns empty (not found)
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])

        status = get_org_subscription_status("org_new_college_123")
        self.assertEqual(status["subscription_status"], "TRIAL")
        self.assertFalse(status["is_blocked"])

    @patch("services.subscription_service.get_supabase")
    def test_active_enterprise_subscription(self, mock_get_supabase):
        """Active subscription with future expiry should be unblocked with correct days remaining."""
        now = datetime.utcnow()
        expiry = now + timedelta(days=120)

        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{
            "id": "org_active_01",
            "subscription_status": "ACTIVE",
            "current_plan": "Enterprise",
            "subscription_start": (now - timedelta(days=30)).isoformat(),
            "subscription_expiry": expiry.isoformat()
        }])

        status = get_org_subscription_status("org_active_01")
        self.assertEqual(status["subscription_status"], "ACTIVE")
        self.assertFalse(status["is_blocked"])
        self.assertAlmostEqual(status["days_remaining"], 120, delta=2)

    @patch("services.subscription_service.get_supabase")
    def test_active_subscription_expired_triggers_block(self, mock_get_supabase):
        """Active subscription that is past expiry date should transition to EXPIRED and is_blocked=True."""
        now = datetime.utcnow()
        past_expiry = now - timedelta(days=2)

        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{
            "id": "org_expired_01",
            "subscription_status": "ACTIVE",
            "current_plan": "Enterprise",
            "subscription_expiry": past_expiry.isoformat()
        }])

        status = get_org_subscription_status("org_expired_01")
        self.assertEqual(status["subscription_status"], "EXPIRED")
        self.assertTrue(status["is_blocked"])
        self.assertEqual(status["days_remaining"], 0)

        # Test block_if_expired helper
        self.assertTrue(block_if_expired("org_expired_01"))

    @patch("services.subscription_service.get_supabase")
    def test_trial_expiring_soon_generates_reminder(self, mock_get_supabase):
        """Trial expiring in 2 days should include warning reminder message."""
        now = datetime.utcnow()
        soon_end = now + timedelta(days=2)

        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{
            "id": "org_trial_soon",
            "subscription_status": "TRIAL",
            "current_plan": "Trial",
            "trial_end": soon_end.isoformat()
        }])

        status = get_org_subscription_status("org_trial_soon")
        self.assertEqual(status["subscription_status"], "TRIAL")
        self.assertFalse(status["is_blocked"])
        self.assertGreater(len(status["reminders"]), 0)
        self.assertIn("Free Trial expires in", status["reminders"][0])

    def test_expired_org_blocked_from_ai_interview_creation(self):
        """Candidates belonging to an expired organization must receive 403 on session creation and interview endpoints."""
        from app import app, _get_jwt_secret
        import jwt
        import uuid

        client = app.test_client()
        expired_org_id = f"org_exp_{uuid.uuid4().hex[:6]}"
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        
        # Initialize organization as EXPIRED
        from services.subscription_service import get_supabase
        sb = get_supabase()
        sb.table("organization").insert({
            "id": expired_org_id,
            "name": "Expired College",
            "subscription_status": "EXPIRED",
            "current_plan": "Expired"
        }).execute()

        token = jwt.encode({
            "sub": user_id,
            "role": "candidate",
            "organization_id": expired_org_id
        }, _get_jwt_secret(), algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Blocked from create-session-no-resume
        res = client.post("/create-session-no-resume", headers=headers, json={"role": "Engineer"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Subscription Expired", res.get_json().get("error", ""))

        # 2. Blocked from upload
        res_upload = client.post("/upload", headers=headers, data={})
        self.assertEqual(res_upload.status_code, 403)
        self.assertIn("Subscription Expired", res_upload.get_json().get("error", ""))

    def test_next_question_bounded_to_five_questions(self):
        """Calling /next after 5 answers must signal done=True and not spawn unbounded questions."""
        import json
        from app import app, _get_jwt_secret
        import jwt
        import uuid

        client = app.test_client()
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        session_id = str(uuid.uuid4())
        
        token = jwt.encode({"sub": user_id, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        from services.subscription_service import get_supabase
        sb = get_supabase()
        sb.table("sessions").insert({
            "session_id": session_id,
            "user_id": user_id,
            "resume_text": "Experienced software engineer with backend and systems knowledge.",
            "questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "responses": ["A1", "A2", "A3", "A4"],
            "feedbacks": [{"score": 8}, {"score": 7}, {"score": 9}, {"score": 8}],
            "question_index": 5,
            "active": True
        }).execute()

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps({
                "score": 8.5,
                "accuracy_score": 85,
                "feedback": "Solid final answer.",
                "strengths": ["Clear explanation"],
                "improvements": [],
                "concept_match": 85,
                "clarity": 85,
            })
        )

        # Submit 5th and final answer offline with mocked Gemini client
        with patch.dict(os.environ, {"ENVIRONMENT": "", "FLASK_ENV": "", "GEMINI_API_KEY": ""}), \
             patch("app.chat_model", mock_llm):
            res = client.post("/next", headers=headers, json={
                "session_id": session_id,
                "answer": "This is my final comprehensive response to question 5."
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("done"))
            self.assertEqual(data.get("question_number"), 5)
            self.assertIsNone(data.get("next_question"))

            # Subsequent call must immediately return done=True without calling LLM
            res_after = client.post("/next", headers=headers, json={
                "session_id": session_id,
                "answer": "Another redundant response"
            })
            self.assertEqual(res_after.status_code, 200)
            self.assertTrue(res_after.get_json().get("done"))

    def test_affirmative_consent_recording(self):
        """Backend must only record consent_given=1 if the user actively provided consent."""
        from app import app, _get_jwt_secret
        import jwt
        import uuid

        client = app.test_client()
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        token = jwt.encode({"sub": user_id, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        from services.subscription_service import get_supabase
        sb = get_supabase()

        # 1. Without consent: Must be rejected server-side with HTTP 400 Bad Request
        res_no_consent = client.post("/create-session-no-resume", headers=headers, json={
            "role": "Backend Engineer"
        })
        self.assertEqual(res_no_consent.status_code, 400)
        self.assertIn("consent", res_no_consent.get_json().get("error", "").lower())

        # 1b. With false consent: Must be rejected server-side with HTTP 400
        res_false_consent = client.post("/create-session-no-resume", headers=headers, json={
            "role": "Backend Engineer",
            "consent": False
        })
        self.assertEqual(res_false_consent.status_code, 400)
        self.assertIn("consent", res_false_consent.get_json().get("error", "").lower())

        # 2. With affirmative consent: Must succeed with 200 and record consent_given = 1
        res_consent = client.post("/create-session-no-resume", headers=headers, json={
            "role": "Backend Engineer",
            "consent": True
        })
        self.assertEqual(res_consent.status_code, 200)
        sess_id_consent = res_consent.get_json()["session_id"]
        row_consent = sb.table("sessions").select("consent_given,consent_timestamp").eq("session_id", sess_id_consent).execute().data[0]
        self.assertEqual(int(row_consent["consent_given"]), 1)
        self.assertIsNotNone(row_consent["consent_timestamp"])

    def test_concurrent_next_question_rejected(self):
        """Simultaneous /next requests on the same session must return HTTP 429."""
        from app import app, _get_jwt_secret, _SESSION_IN_FLIGHT, _SESSION_IN_FLIGHT_LOCK
        import jwt
        import uuid

        client = app.test_client()
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        session_id = str(uuid.uuid4())
        token = jwt.encode({"sub": user_id, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        from services.subscription_service import get_supabase
        sb = get_supabase()
        sb.table("sessions").insert({
            "session_id": session_id,
            "user_id": user_id,
            "resume_text": "Software engineer",
            "questions": ["Q1"],
            "responses": [],
            "feedbacks": [],
            "question_index": 1,
            "active": True
        }).execute()

        # Simulate in-flight lock active on session_id
        with _SESSION_IN_FLIGHT_LOCK:
            _SESSION_IN_FLIGHT.add(session_id)

        try:
            res = client.post("/next", headers=headers, json={
                "session_id": session_id,
                "answer": "Concurrent attempt"
            })
            self.assertEqual(res.status_code, 429)
            self.assertIn("Concurrent request in progress", res.get_json().get("error", ""))
        finally:
            with _SESSION_IN_FLIGHT_LOCK:
                _SESSION_IN_FLIGHT.discard(session_id)

    def test_hint_caching_avoids_repeated_llm_calls(self):
        """First hint request calls mocked Gemini client once; subsequent identical requests use cache with zero extra calls."""
        from app import app, _get_jwt_secret
        import jwt
        import uuid

        client = app.test_client()
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        session_id = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())
        # Unique question ensures L1/Redis prompt cache starts cold for this run without mocking cache_service
        question_text = f"Explain how Python GIL works in CPython [{uuid.uuid4().hex[:8]}]."
        resume_text = "Experienced Python Engineer"
        expected_hint = "Consider how the Global Interpreter Lock serializes Python bytecode execution across OS threads."

        token = jwt.encode({"sub": user_id, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        from services.subscription_service import get_supabase
        sb = get_supabase()
        for sid in (session_id, session_id_2):
            sb.table("sessions").insert({
                "session_id": sid,
                "user_id": user_id,
                "resume_text": resume_text,
                "questions": [question_text],
                "responses": [],
                "feedbacks": [],
                "question_index": 1,
                "active": True
            }).execute()

        mock_gemini = MagicMock()
        mock_gemini.invoke.return_value = MagicMock(content=expected_hint)

        # Mock Gemini client at app.chat_model boundary; clear env keys so safe_invoke_llm stays offline with no API key
        with patch.dict(os.environ, {"ENVIRONMENT": "", "FLASK_ENV": "", "GEMINI_API_KEY": "", "GEMINI_INTERVIEW_KEY": ""}), \
             patch("app.chat_model", mock_gemini):
            # 1st hint request must invoke Gemini exactly once
            res1 = client.post("/get-hint", headers=headers, json={"session_id": session_id})
            self.assertEqual(res1.status_code, 200)
            body1 = res1.get_json()
            self.assertEqual(body1["hint"], expected_hint)
            self.assertFalse(body1.get("cached", False))
            self.assertEqual(mock_gemini.invoke.call_count, 1)

            # 2nd identical hint request on same session hits session cache without another Gemini call
            res2 = client.post("/get-hint", headers=headers, json={"session_id": session_id})
            self.assertEqual(res2.status_code, 200)
            body2 = res2.get_json()
            self.assertTrue(body2.get("cached"))
            self.assertEqual(body2["hint"], expected_hint)
            self.assertEqual(mock_gemini.invoke.call_count, 1)

            # 3rd identical request on a fresh session with empty cached_hints hits prompt cache without calling Gemini
            res3 = client.post("/get-hint", headers=headers, json={"session_id": session_id_2})
            self.assertEqual(res3.status_code, 200)
            self.assertEqual(res3.get_json()["hint"], expected_hint)
            self.assertEqual(mock_gemini.invoke.call_count, 1)

    def test_exception_in_next_releases_session_lock(self):
        """Even if an internal error occurs during /next, the finally block must release the in-flight lock."""
        from app import app, _get_jwt_secret, _SESSION_IN_FLIGHT, _SESSION_IN_FLIGHT_LOCK
        import jwt
        import uuid

        client = app.test_client()
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        session_id = str(uuid.uuid4())
        token = jwt.encode({"sub": user_id, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        from services.subscription_service import get_supabase
        sb = get_supabase()
        sb.table("sessions").insert({
            "session_id": session_id,
            "user_id": user_id,
            "resume_text": "Experienced Python Engineer",
            "questions": ["Q1"],
            "responses": [],
            "feedbacks": [],
            "question_index": 1,
            "active": True
        }).execute()

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="How would you benchmark latency under load?")

        # Simulate exception during evaluate_response_comprehensive while keeping background/question LLM calls offline
        with patch.dict(os.environ, {"ENVIRONMENT": "", "FLASK_ENV": "", "GEMINI_API_KEY": ""}), \
             patch("app.chat_model", mock_llm), \
             patch("services.interview_reliability_service.submit_background_turn_eval"), \
             patch("app.evaluate_response_comprehensive", side_effect=RuntimeError("Simulated LLM network error")):
            res = client.post("/next", headers=headers, json={
                "session_id": session_id,
                "answer": "My answer that encounters a network error"
            })
            self.assertEqual(res.status_code, 500)

        # Verify that lock is NOT held on session_id after exception
        with _SESSION_IN_FLIGHT_LOCK:
            self.assertNotIn(session_id, _SESSION_IN_FLIGHT)

    def test_hint_invalidated_when_interview_advances(self):
        """When an interview advances to question 2, the hint cache must be invalidated."""
        import json
        from app import app, _get_jwt_secret
        import jwt
        import uuid

        client = app.test_client()
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        session_id = str(uuid.uuid4())
        token = jwt.encode({"sub": user_id, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        from services.subscription_service import get_supabase
        sb = get_supabase()
        sb.table("sessions").insert({
            "session_id": session_id,
            "user_id": user_id,
            "resume_text": "Experienced Python Engineer",
            "questions": [f"Question 1: Explain Python GIL [{uuid.uuid4().hex[:6]}]."],
            "responses": [],
            "feedbacks": [],
            "question_index": 1,
            "active": True
        }).execute()

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=json.dumps({
                "score": 8.0,
                "accuracy_score": 80,
                "feedback": "Good explanation of CPython threading.",
                "strengths": ["Accurate GIL summary"],
                "improvements": [],
                "next_question": "How does multiprocessing differ from multithreading in Python?"
            })
        )

        with patch.dict(os.environ, {"ENVIRONMENT": "", "FLASK_ENV": "", "GEMINI_API_KEY": ""}), \
             patch("app.chat_model", mock_llm), \
             patch("services.interview_reliability_service.submit_background_turn_eval"):
            # 1. Generate hint for Q1
            res_hint = client.post("/get-hint", headers=headers, json={"session_id": session_id})
            self.assertEqual(res_hint.status_code, 200)

            # 2. Advance to Q2 via /next
            res_next = client.post("/next", headers=headers, json={
                "session_id": session_id,
                "answer": "GIL prevents multiple native threads from executing Python bytecodes simultaneously."
            })
            self.assertEqual(res_next.status_code, 200)

        # 3. Check that cached_hints on session is reset
        sess_data = sb.table("sessions").select("cached_hints").eq("session_id", session_id).execute().data[0]
        cached_val = sess_data.get("cached_hints")
        self.assertTrue(cached_val in [{}, "{}", None, ""] or len(cached_val or {}) == 0)

if __name__ == "__main__":
    unittest.main()
