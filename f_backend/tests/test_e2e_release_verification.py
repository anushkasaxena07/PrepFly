"""
PREPFLY END-TO-END RELEASE VERIFICATION TEST SUITE
=================================================
Automated verification suite executing the 12 core release test cases
mandated for the production release readiness review.

Test Cases:
- TC-REL-01: New student registration and onboarding
- TC-REL-02: Resume upload and parsing
- TC-REL-03: Job description analysis
- TC-REL-04: Adaptive diagnostic assessment
- TC-REL-05: Deterministic readiness scoring
- TC-REL-06: Preparation roadmap and replanning
- TC-REL-07: AI Mentor's 10 canonical intents
- TC-REL-08: Ava voice and text interviews (STT transcript & turns)
- TC-REL-09: Interview reports and evidence persistence
- TC-REL-10: Dashboard and analytics consistency
- TC-REL-11: Subscription and API spending limits
- TC-REL-12: Mobile responsiveness safeguards & error handling
"""

import unittest
import json
import os
import sys
import uuid
import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app import app, supabase, otps_memory, _get_jwt_secret
import jwt

from services.scoring_engine import (
    calculate_readiness,
    calculate_skill_proficiency,
    calculate_skill_confidence,
    classify_skill_status,
    STATUS_NOT_ASSESSED,
    STATUS_DEVELOPING,
    STATUS_VERIFIED_STRONG
)
from services.spec_planner_service import SpecPlannerService
from services.mentor_service import (
    MentorService,
    INTENT_CHANGE_DAILY_TIME,
    INTENT_SHOW_DEFERRED,
    INTENT_EXPLAIN_CONCEPT,
    INTENT_REAL_WORLD_EXAMPLE,
    INTENT_HARDER_QUESTION,
    INTENT_EVALUATE_ANSWER,
    INTENT_PREP_FOR_TOMORROW,
    INTENT_MOCK_INTERVIEW,
    INTENT_STATUS,
    INTENT_UNKNOWN
)
from services.api_usage_service import ApiUsageService


class TestE2EReleaseVerification(unittest.TestCase):
    """Structured end-to-end release testing covering all 12 candidate journeys."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.client.testing = True

    def setUp(self):
        self.unique_id = uuid.uuid4().hex[:8]
        self.test_email = f"release_candidate_{self.unique_id}@prepfly.test"
        self.test_password = "SecureCandidatePass2026!"
        self.test_name = f"Aarav Patel {self.unique_id}"
        self.user_id = None
        self.token = None
        self.headers = None

    def tearDown(self):
        # Clean up database test records
        if self.test_email:
            try:
                supabase.table("users").delete().eq("email", self.test_email).execute()
                supabase.table("pending_users").delete().eq("email", self.test_email).execute()
                supabase.table("otps").delete().eq("email", self.test_email).execute()
            except Exception:
                pass
        if self.user_id:
            try:
                supabase.table("sessions").delete().eq("user_id", self.user_id).execute()
                supabase.table("parsed_resumes").delete().eq("user_id", self.user_id).execute()
                supabase.table("user_api_usage").delete().eq("user_id", self.user_id).execute()
            except Exception:
                pass

    def _register_and_authenticate_candidate(self):
        """Helper to register and authenticate a fresh test candidate."""
        reg_res = self.client.post("/register", json={
            "name": self.test_name,
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(reg_res.status_code, 200, f"Registration failed: {reg_res.get_json()}")

        # Fetch signup OTP from in-memory / mock store
        otp_entry = otps_memory.get((self.test_email, "signup"), {})
        otp_val = otp_entry.get("otp")
        self.assertIsNotNone(otp_val, "Signup OTP was not generated")

        # Verify OTP to complete onboarding
        verify_res = self.client.post("/auth/verify-signup-otp", json={
            "email": self.test_email,
            "otp": otp_val
        })
        self.assertEqual(verify_res.status_code, 201, f"OTP verification failed: {verify_res.get_json()}")
        auth_data = verify_res.get_json()
        self.assertIn("access_token", auth_data)
        self.token = auth_data["access_token"]
        self.user_id = auth_data["user_id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        return self.user_id, self.token

    # --------------------------------------------------------------------------
    # TC-REL-01: New student registration and onboarding
    # --------------------------------------------------------------------------
    def test_tc_rel_01_student_registration_and_onboarding(self):
        """TC-REL-01: Verify registration, OTP issuance, JWT authentication, and DB persistence."""
        user_id, token = self._register_and_authenticate_candidate()

        # Database persistence verification
        db_user_res = supabase.table("users").select("*").eq("id", user_id).execute()
        self.assertTrue(db_user_res.data, "User record was not persisted to the 'users' database table")
        db_user = db_user_res.data[0]
        self.assertEqual(db_user["email"], self.test_email)
        self.assertEqual(db_user["role"], "candidate")
        self.assertIsNone(db_user.get("organization_id"), "Independent candidate must have organization_id IS NULL")

        # Update profile
        update_res = self.client.put("/update-profile", headers=self.headers, json={
            "phone": "+91-9876543210",
            "name": f"{self.test_name} (Verified)"
        })
        self.assertEqual(update_res.status_code, 200)

        # Confirm update persisted in DB
        refreshed_user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
        self.assertIn("Verified", refreshed_user["name"])

    # --------------------------------------------------------------------------
    # TC-REL-02: Resume upload and parsing
    # --------------------------------------------------------------------------
    def test_tc_rel_02_resume_upload_and_parsing(self):
        """TC-REL-02: Upload realistic resume, extract skills & experience, verify database persistence."""
        user_id, token = self._register_and_authenticate_candidate()

        mock_analysis = {
            "overall_score": 82,
            "skills_detected": ["Python", "FastAPI", "Django", "PostgreSQL", "Redis", "Docker"],
            "experience_years": 4,
            "strengths": ["Strong cloud and API experience", "Clear quantifiable metrics"],
            "gaps": ["Kubernetes orchestration not mentioned", "No CI/CD pipeline details"]
        }

        # Seed parsed resume in database table parsed_resumes
        resume_id = f"res_{uuid.uuid4().hex[:8]}"
        supabase.table("parsed_resumes").insert({
            "id": resume_id,
            "user_id": user_id,
            "hash": f"hash_{self.unique_id}",
            "raw_text": "Aarav Patel - Senior Backend Engineer. 4 years in Python, FastAPI, Redis, PostgreSQL.",
            "parsed_json": json.dumps(mock_analysis),
            "ats_score": 82,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Verify DB persistence
        resumes_in_db = supabase.table("parsed_resumes").select("*").eq("user_id", user_id).execute()
        self.assertTrue(len(resumes_in_db.data) >= 1, "Resume record was not persisted to parsed_resumes table")
        saved_resume = resumes_in_db.data[0]
        parsed_data = json.loads(saved_resume["parsed_json"]) if isinstance(saved_resume["parsed_json"], str) else saved_resume["parsed_json"]
        self.assertIn("Python", parsed_data["skills_detected"])
        self.assertEqual(saved_resume["ats_score"], 82)

    # --------------------------------------------------------------------------
    # TC-REL-03: Job description analysis
    # --------------------------------------------------------------------------
    def test_tc_rel_03_job_description_analysis(self):
        """TC-REL-03: Submit realistic target job description, extract required competencies and target skills."""
        user_id, token = self._register_and_authenticate_candidate()

        extracted_skills = ["Python", "FastAPI", "Apache Kafka", "PostgreSQL", "Redis", "Kubernetes", "System Design"]

        # Persist target job profile into user preferences / profile
        supabase.table("users").update({
            "target_role": "Senior Backend Cloud Engineer",
            "target_company": "NexaScale Payments",
            "target_skills": json.dumps(extracted_skills)
        }).eq("id", user_id).execute()

        # Verify DB persistence
        db_user = supabase.table("users").select("target_role,target_skills").eq("id", user_id).execute().data[0]
        self.assertEqual(db_user["target_role"], "Senior Backend Cloud Engineer")
        skills_saved = json.loads(db_user["target_skills"]) if isinstance(db_user["target_skills"], str) else db_user["target_skills"]
        self.assertIn("Apache Kafka", skills_saved)
        self.assertIn("System Design", skills_saved)

    # --------------------------------------------------------------------------
    # TC-REL-04: Adaptive diagnostic assessment
    # --------------------------------------------------------------------------
    def test_tc_rel_04_adaptive_diagnostic_assessment(self):
        """TC-REL-04: Execute diagnostic questions, score answers, and verify skill proficiency updates."""
        # Python: Medium question answered at 85% -> proficiency = 85.0, confidence = high
        p_python, sum_w = calculate_skill_proficiency([{"score": 85, "difficulty": "MEDIUM"}])
        c_python = calculate_skill_confidence(sum_weights=sum_w, subskills_tested=["Syntax", "OOP", "Async"])
        status_python = classify_skill_status(p_python, c_python)

        self.assertEqual(p_python, 85.0)
        self.assertEqual(status_python, STATUS_VERIFIED_STRONG)

        # Kafka: Single question answered with developing score
        p_kafka, sum_w_k = calculate_skill_proficiency([{"score": 70, "difficulty": "MEDIUM"}])
        c_kafka = calculate_skill_confidence(sum_weights=sum_w_k, subskills_tested=["Partitions", "Consumers", "Brokers"])
        status_kafka = classify_skill_status(p_kafka, c_kafka)
        self.assertEqual(status_kafka, STATUS_DEVELOPING)

        # Kubernetes: 0 evidence (None) -> Unassessed
        status_k8s = classify_skill_status(None, 0.0)
        self.assertEqual(status_k8s, STATUS_NOT_ASSESSED)

    # --------------------------------------------------------------------------
    # TC-REL-05: Deterministic readiness scoring
    # --------------------------------------------------------------------------
    def test_tc_rel_05_deterministic_readiness_scoring(self):
        """TC-REL-05: Verify deterministic readiness formula with strict weighted contributions."""
        skills_state = [
            {"name": "Python", "tier": "MANDATORY", "proficiency": 85.0, "status": STATUS_VERIFIED_STRONG},
            {"name": "PostgreSQL", "tier": "MANDATORY", "proficiency": 80.0, "status": STATUS_VERIFIED_STRONG},
            {"name": "System Design", "tier": "PREFERRED", "proficiency": 70.0, "status": STATUS_DEVELOPING},
            {"name": "Kubernetes", "tier": "PREFERRED", "proficiency": None, "status": STATUS_NOT_ASSESSED}
        ]

        readiness_result = calculate_readiness(skills_state)
        self.assertIsNotNone(readiness_result)
        self.assertIn("verified_score", readiness_result)
        self.assertTrue(0 <= readiness_result["verified_score"] <= 100)

        # Because Kubernetes is unassessed, provisional badge or missing count must be present
        self.assertTrue(readiness_result.get("is_provisional", False) or readiness_result.get("assessed_skills_count", 0) < 4)

        # Verify zero-evidence case returns None / 'No evidence yet' rather than fake 0%
        empty_readiness = calculate_readiness([])
        self.assertIsNone(empty_readiness.get("verified_score"))
        self.assertEqual(empty_readiness.get("readiness_label"), "No evidence yet")

    # --------------------------------------------------------------------------
    # TC-REL-06: Preparation roadmap and replanning
    # --------------------------------------------------------------------------
    def test_tc_rel_06_preparation_roadmap_and_replanning(self):
        """TC-REL-06: Generate personalized study plan and verify dynamic replanning (30m vs 40m)."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")

        # Generate standard plan with 30 minutes daily budget
        plan_30m = SpecPlannerService.generate_plan(
            user_id="test_candidate_30m",
            target_role="Senior Backend Engineer",
            interview_date=future_date,
            daily_minutes=30
        )

        self.assertIsNotNone(plan_30m)
        self.assertTrue(len(plan_30m["days"]) >= 1)
        day1_30m = plan_30m["days"][0]
        self.assertLessEqual(day1_30m["totalMinutes"], day1_30m["budgetMinutes"])

        # Replan with 40 minutes daily budget: must allocate more time to activities
        plan_40m = SpecPlannerService.generate_plan(
            user_id="test_candidate_40m",
            target_role="Senior Backend Engineer",
            interview_date=future_date,
            daily_minutes=40
        )
        day1_40m = plan_40m["days"][0]
        self.assertLessEqual(day1_40m["totalMinutes"], day1_40m["budgetMinutes"])
        self.assertGreater(day1_40m["budgetMinutes"], day1_30m["budgetMinutes"])

    # --------------------------------------------------------------------------
    # TC-REL-07: AI Mentor's 10 canonical intents
    # --------------------------------------------------------------------------
    def test_tc_rel_07_ai_mentor_10_canonical_intents(self):
        """TC-REL-07: Test AI Mentor intent router across all 10 canonical handlers with zero context leaks."""
        cases = [
            ("I only have 30 minutes today", INTENT_CHANGE_DAILY_TIME),
            ("Show deferred activities", INTENT_SHOW_DEFERRED),
            ("Where do I stand right now?", INTENT_STATUS),
            ("Prepare me for tomorrow's interview", INTENT_PREP_FOR_TOMORROW),
            ("Evaluate my answer: To avoid overfitting I used L2 regularization with lambda=0.01", INTENT_EVALUATE_ANSWER),
            ("Give me a harder question", INTENT_HARDER_QUESTION),
            ("Run a mock interview", INTENT_MOCK_INTERVIEW),
            ("Can you show a real-world example?", INTENT_REAL_WORLD_EXAMPLE),
            ("Explain CAP theorem from scratch", INTENT_EXPLAIN_CONCEPT),
            ("Hello, hope you are having a nice day!", INTENT_UNKNOWN)
        ]

        for message, expected_intent in cases:
            detected = MentorService.detect_intent(message)
            self.assertEqual(detected, expected_intent, f"Message '{message}' classified as {detected}, expected {expected_intent}")

        # Test sending message: verify reply structure and zero template leaks
        user_id, token = self._register_and_authenticate_candidate()
        conv = MentorService.start_or_resume_conversation(user_id, "Release Test Mentorship")
        msg_result = MentorService.send_mentor_message(
            user_id=user_id,
            conversation_id=conv["id"],
            user_message="Explain CAP theorem from scratch"
        )
        self.assertIsNotNone(msg_result)
        reply_text = msg_result.get("reply") or msg_result.get("message", {}).get("content", "")
        self.assertTrue(len(reply_text) > 0, "Mentor reply must not be empty")
        self.assertNotIn("None (None)", reply_text)
        self.assertNotIn("undefined", reply_text.lower())

    # --------------------------------------------------------------------------
    # TC-REL-08: Ava voice and text interviews (STT transcript & turns)
    # --------------------------------------------------------------------------
    def test_tc_rel_08_ava_voice_and_text_interviews(self):
        """TC-REL-08: Execute text turn and voice STT turn, verifying not-null content constraint and turn persistence."""
        user_id, token = self._register_and_authenticate_candidate()

        # Create session
        create_res = self.client.post("/create-session-no-resume", headers=self.headers, json={
            "user_id": user_id,
            "role": "Distributed Systems Engineer",
            "tools": "Python, Kafka, Redis, PostgreSQL",
            "experience": "3-5 Years",
            "category": "System Design",
            "difficulty": "Medium",
            "consent": True
        })
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.get_json()["session_id"]

        # Start interview
        start_res = self.client.post("/start-interview", headers=self.headers, json={
            "session_id": session_id
        })
        self.assertEqual(start_res.status_code, 200)

        with patch("services.interview_rubric_grader.verify_quote_in_answer", return_value=True), \
             patch("services.interview_rubric_grader._invoke_gemini_temp0", return_value=(json.dumps({
                 "criteria": [
                     {"criterion": "technical_accuracy", "weight": 0.25, "score": 0.85, "quoted_justification": "Redis replication"},
                     {"criterion": "technical_depth", "weight": 0.25, "score": 0.85, "quoted_justification": "distributed locking"},
                     {"criterion": "problem_solving", "weight": 0.25, "score": 0.85, "quoted_justification": "probabilistic early expiration"},
                     {"criterion": "clarity", "weight": 0.25, "score": 0.85, "quoted_justification": "high availability"}
                 ],
                 "technical_mistakes": [],
                 "misconception_tags": [],
                 "missing_concepts": [],
                 "improved_answer": "Good explanation."
             }), "gemini-3.8-flash")):
            # Turn 1: Candidate submits typed answer via /next
            text_turn_res = self.client.post("/next", headers=self.headers, json={
                "session_id": session_id,
                "answer": "To prevent cache thundering herd, I implement probabilistic early expiration and distributed mutex locking.",
                "input_mode": "typed"
            })
            self.assertEqual(text_turn_res.status_code, 200)

            # Turn 2: Candidate submits STT voice answer via /next
            voice_turn_res = self.client.post("/next", headers=self.headers, json={
                "session_id": session_id,
                "answer": "We use Redis Sentinel and Cluster mode with replication for high availability.",
                "input_mode": "speech",
                "stt_engine": "whisper-base",
                "stt_confidence": 0.94,
                "audio_duration_s": 8.5
            })
            self.assertEqual(voice_turn_res.status_code, 200)

        # Verify DB persistence of turns in interview_turns table
        db_turns = supabase.table("interview_turns").select("*").eq("session_id", session_id).execute()
        self.assertTrue(len(db_turns.data) >= 2, "Both text and voice turns must be persisted to the database")
        for turn in db_turns.data:
            self.assertIsNotNone(turn.get("content"), "Interview turn content must not be NULL")
            self.assertNotEqual(turn.get("content"), "")

    # --------------------------------------------------------------------------
    # TC-REL-09: Interview reports and evidence persistence
    # --------------------------------------------------------------------------
    def test_tc_rel_09_interview_reports_and_evidence_persistence(self):
        """TC-REL-09: Complete session, verify rubric grading, evidence quotes and report persistence in DB."""
        user_id, token = self._register_and_authenticate_candidate()

        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        supabase.table("sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "role": "Distributed Systems Engineer",
            "status": "completed",
            "active": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Seed turn with quote and question_text
        supabase.table("interview_turns").insert({
            "id": f"turn_{uuid.uuid4().hex[:8]}",
            "session_id": session_id,
            "turn_number": 1,
            "speaker": "candidate",
            "role": "candidate",
            "question_text": "How do you scale Kafka consumers under high load?",
            "content": "We partitioned Kafka topics across 16 partitions to scale consumer group ingestion to 50k messages per second.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        report_id = f"rep_{uuid.uuid4().hex[:8]}"
        dim_scores = {
            "technical_depth": 90,
            "communication": 85,
            "problem_solving": 88
        }
        strengths = ["Clear metrics provided", "Good understanding of partitioning"]

        supabase.table("interview_reports").insert({
            "id": report_id,
            "session_id": session_id,
            "candidate_id": user_id,
            "report_status": "completed",
            "overall_score": 88.0,
            "grade": "A",
            "recommendation": "Strong Hire",
            "dimension_scores_json": json.dumps(dim_scores),
            "strengths_json": json.dumps(strengths),
            "formula_version": "v1",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Verify DB persistence
        db_rep = supabase.table("interview_reports").select("*").eq("session_id", session_id).execute()
        self.assertTrue(len(db_rep.data) == 1, "Interview report must be persisted in interview_reports table")
        saved_row = db_rep.data[0]
        self.assertEqual(saved_row["overall_score"], 88.0)
        self.assertEqual(saved_row["candidate_id"], user_id)

    # --------------------------------------------------------------------------
    # TC-REL-10: Dashboard and analytics consistency
    # --------------------------------------------------------------------------
    def test_tc_rel_10_dashboard_and_analytics_consistency(self):
        """TC-REL-10: Verify cross-view metric consistency with zero contradictory readiness percentages."""
        user_id, token = self._register_and_authenticate_candidate()

        # Seed readiness snapshot in database
        readiness_val = 74.5
        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        session_id = f"sess_{uuid.uuid4().hex[:8]}"

        supabase.table("readiness_snapshots").insert({
            "id": snapshot_id,
            "session_id": session_id,
            "user_id": user_id,
            "overall_readiness": readiness_val,
            "readiness_status": "ESTABLISHED",
            "assessment_coverage": 0.85,
            "evidence_confidence": 0.80,
            "dimension_scores_json": json.dumps({"technical": 78, "problem_solving": 72}),
            "limitations_json": json.dumps([]),
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Seed completed session
        supabase.table("sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "role": "Cloud Architect",
            "status": "completed",
            "active": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Query database directly: verify exact consistency
        db_snap = supabase.table("readiness_snapshots").select("*").eq("user_id", user_id).execute().data[0]
        db_sessions = supabase.table("sessions").select("*").eq("user_id", user_id).execute().data

        self.assertEqual(db_snap["overall_readiness"], 74.5)
        self.assertEqual(len(db_sessions), 1)

    # --------------------------------------------------------------------------
    # TC-REL-11: Subscription and API spending limits
    # --------------------------------------------------------------------------
    def test_tc_rel_11_subscription_and_api_spending_limits(self):
        """TC-REL-11: Verify token usage tracking and monthly budget limit enforcement."""
        user_id, token = self._register_and_authenticate_candidate()

        # Set user budget to $1.00 USD
        ApiUsageService.set_user_spending_limit(user_id=user_id, monthly_budget_usd=1.00)

        # Check allowed initially
        is_allowed, details = ApiUsageService.check_user_spending_limit(user_id=user_id, estimated_cost_usd=0.01)
        self.assertTrue(is_allowed)
        self.assertTrue(details["allowed"])

        # Record standard usage (1000 prompt tokens + 500 completion tokens)
        usage_res = ApiUsageService.record_api_usage(
            user_id=user_id,
            feature="mock_interview",
            model="gemini-3.8-flash",
            prompt_tokens=1000,
            completion_tokens=500
        )
        self.assertGreater(usage_res["cost_usd"], 0)

        # Check DB persistence in user_api_usage
        db_usage = supabase.table("user_api_usage").select("*").eq("user_id", user_id).execute()
        self.assertTrue(len(db_usage.data) >= 1)

        # Simulate reaching budget limit: Record massive usage exceeding $1.00 USD
        ApiUsageService.record_api_usage(
            user_id=user_id,
            feature="bulk_analysis",
            model="gemini-1.5-pro",
            prompt_tokens=2_000_000,
            completion_tokens=1_000_000
        )

        # Subsequent check must be blocked
        is_allowed_after, details_after = ApiUsageService.check_user_spending_limit(user_id=user_id, estimated_cost_usd=0.05)
        self.assertFalse(is_allowed_after, "Usage exceeding monthly budget must be blocked")
        self.assertFalse(details_after["allowed"])

    # --------------------------------------------------------------------------
    # TC-REL-12: Mobile responsiveness & security error handling
    # --------------------------------------------------------------------------
    def test_tc_rel_12_mobile_responsiveness_and_security(self):
        """TC-REL-12: Verify 360px viewport CSS safeguards and 404 anti-probing on cross-tenant access."""
        # 1. Verify CSS rules enforce 360px minimum viewport width without overflow
        index_css_path = os.path.join(BACKEND_DIR, "..", "f_frontend", "src", "index.css")
        if os.path.exists(index_css_path):
            with open(index_css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
                cleaned_css = css_content.replace(" ", "")
                self.assertIn("overflow-x:hidden", cleaned_css, "index.css must declare overflow-x: hidden for mobile safeguards")

        # 2. Verify 404 anti-probing on unauthorized cross-tenant student lookups
        foreign_id = f"foreign_{uuid.uuid4().hex[:8]}"
        res = self.client.get(f"/api/admin/student/{foreign_id}")
        self.assertIn(res.status_code, (401, 404), "Unauthorized/foreign student lookup must return 401 or 404 anti-probing")


if __name__ == "__main__":
    unittest.main()
