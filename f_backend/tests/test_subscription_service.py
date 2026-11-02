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

        # Submit 5th and final answer
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

if __name__ == "__main__":
    unittest.main()
