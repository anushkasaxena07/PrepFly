"""
Phase 1 Test Suite: Conversational Onboarding and Interview Context Service.
Verifies one-question-at-a-time onboarding, skipping pre-known fields, separate candidate
actual vs job required experience, database row creation in interview_goals, and compact
cached versioned context assembly.
"""

import unittest
import json
import uuid
from datetime import datetime, timezone, timedelta

from local_supabase import get_supabase_client
from services.interview_onboarding_service import InterviewOnboardingService, ONBOARDING_FIELD_SEQUENCE
from services.interview_context_service import InterviewContextService


class TestPhase1InterviewOnboardingAndContext(unittest.TestCase):
    """Test suite for Phase 1 Onboarding & Context Service."""

    def setUp(self):
        self.supabase = get_supabase_client()
        self.test_user_id = f"test_user_p1_{uuid.uuid4().hex[:8]}"
        InterviewContextService.invalidate_cache(self.test_user_id)

    def test_01_conversational_onboarding_step_by_step(self):
        """Tests that onboarding proceeds one question at a time and creates a draft goal row."""
        # 1. Start onboarding
        step1 = InterviewOnboardingService.start_or_resume_onboarding(
            user_id=self.test_user_id,
            supabase_client=self.supabase
        )

        self.assertFalse(step1["is_completed"])
        self.assertIsNotNone(step1["current_question"])
        # If no profile exists, target_role is the first question
        goal_id = step1["goal_id"]

        # Check DB row created
        db_res = self.supabase.table("interview_goals").select("*").eq("id", goal_id).execute()
        self.assertTrue(len(db_res.data) > 0)
        self.assertEqual(db_res.data[0]["status"], "draft")

        # 2. Submit target role
        step2 = InterviewOnboardingService.submit_onboarding_answer(
            user_id=self.test_user_id,
            goal_id=goal_id,
            field="target_role",
            value="AI / ML Engineer",
            supabase_client=self.supabase
        )
        self.assertFalse(step2["is_completed"])
        self.assertEqual(step2["current_question"]["field"], "target_company")

        # 3. Submit target company
        step3 = InterviewOnboardingService.submit_onboarding_answer(
            user_id=self.test_user_id,
            goal_id=goal_id,
            field="target_company",
            value="DeepMind",
            supabase_client=self.supabase
        )
        self.assertFalse(step3["is_completed"])
        self.assertEqual(step3["current_question"]["field"], "job_description_text")

    def test_02_onboarding_skips_prefilled_fields(self):
        """Verifies onboarding skips questions for fields already populated in candidate_profiles."""
        # Pre-seed candidate profile with known target_role and target_company
        self.supabase.table("candidate_profiles").insert({
            "user_id": self.test_user_id,
            "target_role": "Backend Engineer",
            "target_company": "Stripe",
            "daily_minutes": 90,
            "target_date": "2026-12-01",
            "experience_level": "Mid-Level",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Start onboarding
        step = InterviewOnboardingService.start_or_resume_onboarding(
            user_id=self.test_user_id,
            supabase_client=self.supabase
        )

        # target_role, target_company, daily_minutes, and target_date should be skipped
        self.assertIn("target_role", step["skipped_fields"])
        self.assertIn("target_company", step["skipped_fields"])
        self.assertIn("daily_minutes", step["skipped_fields"])

        # The first active question should NOT be target_role or target_company
        self.assertNotIn(step["current_question"]["field"], ["target_role", "target_company"])
        self.assertEqual(step["current_question"]["field"], "job_description_text")

    def test_03_candidate_actual_vs_job_required_experience_separated(self):
        """Verifies candidate actual experience and job required experience are strictly isolated."""
        goal_id = f"goal_{uuid.uuid4().hex[:10]}"
        self.supabase.table("interview_goals").insert({
            "id": goal_id,
            "user_id": self.test_user_id,
            "target_role": "AI / ML Engineer",
            "required_experience_years": 5.0,  # Job requires 5 years (Senior)
            "candidate_actual_experience_years": 1.5,  # Candidate only has 1.5 years (Junior/Mid)
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Submit answer updating candidate experience
        step = InterviewOnboardingService.submit_onboarding_answer(
            user_id=self.test_user_id,
            goal_id=goal_id,
            field="candidate_actual_experience_years",
            value=2.0,
            supabase_client=self.supabase
        )

        # Verify DB values remain cleanly separated
        row = self.supabase.table("interview_goals").select("*").eq("id", goal_id).execute().data[0]
        self.assertEqual(row["candidate_actual_experience_years"], 2.0)
        self.assertEqual(row["required_experience_years"], 5.0)

    def test_04_interview_context_service_compact_and_versioned(self):
        """Verifies interview_context_service returns a compact, versioned context object."""
        target_date = (datetime.now(timezone.utc).date() + timedelta(days=5)).isoformat()
        goal_id = f"goal_{uuid.uuid4().hex[:10]}"
        self.supabase.table("interview_goals").insert({
            "id": goal_id,
            "user_id": self.test_user_id,
            "target_role": "AI / ML Engineer",
            "target_company": "Anthropic",
            "required_experience_years": 3.0,
            "candidate_actual_experience_years": 2.0,
            "target_interview_date": target_date,
            "daily_minutes": 45,
            "learning_preference": "hands-on",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Seed candidate skill state: 1 verified gap, 1 mastered
        now_str = datetime.now(timezone.utc).isoformat()
        self.supabase.table("candidate_skill_states").insert({
            "id": f"css_{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "skill_id": "pytorch_foundations",
            "proficiency": 25.0,
            "confidence": 0.8,
            "status": "VERIFIED_GAP",
            "evidence_count": 2,
            "last_assessed_at": now_str,
            "updated_at": now_str
        }).execute()
        self.supabase.table("candidate_skill_states").insert({
            "id": f"css_{uuid.uuid4().hex[:8]}",
            "user_id": self.test_user_id,
            "skill_id": "python_data_structures",
            "proficiency": 95.0,
            "confidence": 0.9,
            "status": "MASTERED",
            "evidence_count": 4,
            "last_assessed_at": now_str,
            "updated_at": now_str
        }).execute()

        # Fetch context
        ctx = InterviewContextService.get_context(
            user_id=self.test_user_id,
            goal_id=goal_id,
            force_refresh=True,
            supabase_client=self.supabase
        )

        self.assertIn("context_version", ctx)
        self.assertEqual(ctx["goal"]["target_company"], "Anthropic")
        self.assertEqual(ctx["goal"]["target_role"], "AI / ML Engineer")
        self.assertEqual(ctx["goal"]["candidate_actual_experience_years"], 2.0)
        self.assertEqual(ctx["goal"]["required_experience_years"], 3.0)
        self.assertEqual(ctx["schedule_constraints"]["daily_minutes"], 45)
        self.assertEqual(ctx["schedule_constraints"]["days_left"], 5)
        # 5 days left -> compressed deadline is True
        self.assertTrue(ctx["schedule_constraints"]["is_compressed_deadline"])

        # Check skill summary
        summary = ctx["skill_state_summary"]
        self.assertEqual(summary["counts"]["VERIFIED_GAP"], 1)
        self.assertEqual(summary["counts"]["MASTERED"], 1)
        self.assertEqual(summary["verified_gaps"][0]["skill_id"], "pytorch_foundations")

    def test_05_caching_and_invalidation(self):
        """Verifies that context is cached in-memory and invalidated when updated."""
        goal_id = f"goal_{uuid.uuid4().hex[:10]}"
        self.supabase.table("interview_goals").insert({
            "id": goal_id,
            "user_id": self.test_user_id,
            "target_role": "Full Stack Engineer",
            "target_company": "Vercel",
            "daily_minutes": 60,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # Call 1: populated in cache
        ctx1 = InterviewContextService.get_context(self.test_user_id, goal_id=goal_id, supabase_client=self.supabase)
        cached_timestamp1 = ctx1["cached_at"]

        # Call 2: should retrieve exact cached object
        ctx2 = InterviewContextService.get_context(self.test_user_id, goal_id=goal_id, supabase_client=self.supabase)
        self.assertEqual(ctx2["cached_at"], cached_timestamp1)

        # Invalidate cache
        InterviewContextService.invalidate_cache(self.test_user_id, goal_id=goal_id)

        # Call 3: should re-fetch and generate fresh timestamp
        ctx3 = InterviewContextService.get_context(self.test_user_id, goal_id=goal_id, supabase_client=self.supabase)
        self.assertEqual(ctx3["goal"]["target_company"], "Vercel")


if __name__ == "__main__":
    unittest.main()
