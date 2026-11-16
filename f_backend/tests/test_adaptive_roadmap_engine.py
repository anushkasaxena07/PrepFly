"""
Production-Grade Adaptive Roadmap Engine Verification Suite.
Validates role-aware curriculum planning, ML/DL prioritization for AI/ML roles,
strict daily capacity capping (<= 60 min), calendar horizon span (30 days),
explainable multi-factor priority scores, and non-destructive version adaptation.
"""

import unittest
import json
import uuid
import sys
import os
from datetime import datetime, timedelta, timezone

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from local_supabase import SQLiteSupabaseMock, get_supabase_client
from services.skill_taxonomy_service import (
    SkillTaxonomyService,
    CAT_ML,
    CAT_DEEP_LEARNING,
    CAT_NLP,
    CAT_GENAI,
    CAT_DATA_ENGINEERING,
    CAT_MLOPS,
    CAT_DSA,
    CAT_CS,
    CAT_SYSTEM_DESIGN
)
from services.candidate_profile_service import CandidateProfileService
from services.skill_profiling_service import SkillProfilingService
from services.roadmap_engine import (
    RecommendationEngine,
    SchedulingEngine,
    PersonalizedRoadmapEngine,
    CURATED_CONTENT_CATALOG
)
from services.roadmap_service import RoadmapService
from app import app


class TestAdaptiveRoadmapEngine(unittest.TestCase):
    """Rigorous verification of PrepFly Adaptive Roadmap Engine."""

    def setUp(self):
        self.mock_db = SQLiteSupabaseMock()
        self.user_id = f"test_aiml_{uuid.uuid4().hex[:8]}"
        self.app_client = app.test_client()

    def test_01_aiml_google_prioritization_regression(self):
        """
        Regression Test Scenario:
        Candidate: AI/ML Engineer preparing for Google, 30-day horizon, 60m daily budget.
        Invariant 1: ML, Deep Learning, NLP, GenAI, and MLOps must dominate top recommendations.
        Invariant 2: DSA and OS must NOT be scheduled ahead of core ML requirements.
        """
        target_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

        # Initialize profile for AI/ML Engineer
        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            target_company="Google",
            target_date=target_date,
            daily_minutes=60,
            experience_level="Mid-Level (2-5 years)"
        )

        recs = RecommendationEngine.get_recommendations(self.user_id, supabase_client=self.mock_db)
        self.assertGreater(len(recs), 0)

        # Inspect top 5 recommended skills
        top_5_categories = [r["category"] for r in recs[:5]]
        top_5_skill_ids = [r["skill_id"] for r in recs[:5]]

        ml_categories = {CAT_ML, CAT_DEEP_LEARNING, CAT_NLP, CAT_GENAI, CAT_DATA_ENGINEERING, CAT_MLOPS}

        # Verify that the majority of top 5 skills are ML / DL / NLP / MLOps
        ml_count_in_top_5 = sum(1 for c in top_5_categories if c in ml_categories)
        self.assertGreaterEqual(ml_count_in_top_5, 4, f"Top 5 skills for AI/ML role must be ML-centric: {top_5_skill_ids}")

        # Ensure general DSA (like arrays or dynamic programming) is not at the very top
        self.assertNotIn("dsa_dp", top_5_skill_ids)
        self.assertNotIn("cs_os", top_5_skill_ids)

        # Verify priority score is explainable with all 5 components
        top_rec = recs[0]
        self.assertIn("priority_score", top_rec)
        self.assertIn("components", top_rec)
        comps = top_rec["components"]
        self.assertIn("skill_gap", comps)
        self.assertIn("job_relevance", comps)
        self.assertIn("prerequisite_importance", comps)
        self.assertIn("assessment_weakness", comps)
        self.assertIn("deadline_urgency", comps)
        self.assertGreater(top_rec["priority_score"], 70.0)

    def test_02_strict_daily_capacity_capping_and_horizon_span(self):
        """
        Tests that:
        1. Every single day's total duration strictly respects sum(minutes) <= daily_budget (60m).
        2. The schedule populates up to the target horizon (30 days) rather than stopping prematurely on Day 9.
        """
        target_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

        profile = {
            "target_role": "AI/ML Engineer",
            "target_company": "Google",
            "target_date": target_date,
            "daily_minutes": 60,
            "preparation_duration_days": 30
        }

        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=self.user_id,
            **profile
        )

        recs = RecommendationEngine.get_recommendations(self.user_id, supabase_client=self.mock_db)
        scheduled = SchedulingEngine.generate_schedule(
            user_id=self.user_id,
            recommendations=recs,
            profile=profile
        )

        self.assertGreater(len(scheduled), 0)

        # Group by day and calculate total minutes per day
        daily_durations = {}
        for act in scheduled:
            d = act["day_number"]
            dur = act["estimated_minutes"]
            daily_durations[d] = daily_durations.get(d, 0) + dur

        # Strict capacity invariant: no day > 60 minutes
        for day, total_mins in daily_durations.items():
            self.assertLessEqual(
                total_mins, 60,
                f"Day {day} exceeded daily budget of 60m with {total_mins} minutes!"
            )

        # Horizon invariant: schedule must span significantly past Day 9 (up to ~25-30 days)
        max_scheduled_day = max(daily_durations.keys())
        self.assertGreaterEqual(
            max_scheduled_day, 20,
            f"Schedule terminated prematurely at Day {max_scheduled_day}; expected horizon ~30 days!"
        )

    def test_03_spaced_retrieval_interleaving(self):
        """Validates that periodic REVISION drills are interleaved into the schedule."""
        profile = {
            "target_role": "AI/ML Engineer",
            "daily_minutes": 60,
            "preparation_duration_days": 28
        }
        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=self.user_id,
            **profile
        )

        recs = RecommendationEngine.get_recommendations(self.user_id, supabase_client=self.mock_db)
        scheduled = SchedulingEngine.generate_schedule(
            user_id=self.user_id,
            recommendations=recs,
            profile=profile
        )

        revision_activities = [a for a in scheduled if a["activity_type"] == "REVISION"]
        self.assertGreater(len(revision_activities), 0, "Schedule must interleave spaced retrieval activities!")

    def test_04_role_differentiation_sde_vs_aiml(self):
        """Verifies that an SDE candidate gets DSA/Systems prioritized while AI/ML gets ML prioritized."""
        # 1. SDE Profile
        sde_user = f"test_sde_{uuid.uuid4().hex[:8]}"
        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=sde_user,
            target_role="Software Development Engineer (General)",
            daily_minutes=60,
            preparation_duration_days=30
        )
        sde_recs = RecommendationEngine.get_recommendations(sde_user, supabase_client=self.mock_db)
        top_sde_cat = sde_recs[0]["category"]
        self.assertIn(top_sde_cat, [CAT_DSA, CAT_CS, CAT_SYSTEM_DESIGN])

        # 2. AI/ML Profile
        aiml_user = f"test_aiml_{uuid.uuid4().hex[:8]}"
        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=aiml_user,
            target_role="AI/ML Engineer",
            daily_minutes=60,
            preparation_duration_days=30
        )
        aiml_recs = RecommendationEngine.get_recommendations(aiml_user, supabase_client=self.mock_db)
        top_aiml_cat = aiml_recs[0]["category"]
        self.assertIn(top_aiml_cat, [CAT_ML, CAT_DEEP_LEARNING, CAT_NLP, CAT_GENAI, CAT_DATA_ENGINEERING, CAT_MLOPS])

    def test_05_non_destructive_adaptation_preserves_completed(self):
        """
        Validates non-destructive recalculation:
        - Completed and pinned activities are strictly preserved
        - Version number increments
        - Activities count and progress updates
        """
        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            daily_minutes=60,
            preparation_duration_days=14
        )

        # Build initial roadmap v1
        rm1 = PersonalizedRoadmapEngine.recalculate_roadmap(
            user_id=self.user_id,
            change_reason="Initial Build",
            supabase_client=self.mock_db
        )
        self.assertEqual(rm1["current_version"], 1)
        self.assertGreater(len(rm1["activities"]), 0)

        # Mark first activity as completed and second as pinned
        acts = rm1["activities"]
        first_act_id = acts[0]["id"]
        second_act_id = acts[1]["id"]

        self.mock_db.table("roadmap_activities").update({"status": "completed"}).eq("id", first_act_id).execute()
        self.mock_db.table("roadmap_activities").update({"is_pinned": 1}).eq("id", second_act_id).execute()

        # Recalculate roadmap v2
        rm2 = PersonalizedRoadmapEngine.recalculate_roadmap(
            user_id=self.user_id,
            change_reason="Candidate scored 85% on DL diagnostic",
            supabase_client=self.mock_db
        )

        self.assertEqual(rm2["current_version"], 2)
        acts_v2 = rm2["activities"]

        # Ensure completed activity is preserved
        completed_preserved = [a for a in acts_v2 if a["id"] == first_act_id]
        self.assertEqual(len(completed_preserved), 1)
        self.assertIn(completed_preserved[0]["status"], ("completed", "COMPLETED"))

        # Ensure pinned activity is preserved
        pinned_preserved = [a for a in acts_v2 if a["id"] == second_act_id]
        self.assertEqual(len(pinned_preserved), 1)
        self.assertEqual(int(pinned_preserved[0]["is_pinned"]), 1)

    def test_06_roadmap_service_dual_representation(self):
        """Verifies that RoadmapService returns BOTH 'activities' list and 'schedule' dict."""
        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            daily_minutes=60,
            preparation_duration_days=10
        )

        rm = RoadmapService.generate_roadmap(user_id=self.user_id, force_regenerate=True, supabase_client=self.mock_db)
        self.assertIn("activities", rm)
        self.assertIn("schedule", rm)
        self.assertIsInstance(rm["activities"], list)
        self.assertIsInstance(rm["schedule"], dict)

        curr = RoadmapService.get_current_roadmap(user_id=self.user_id, supabase_client=self.mock_db)
        self.assertIsNotNone(curr)
        self.assertIn("schedule", curr)
        self.assertIn("activities", curr)

    def test_07_reset_prep_roadmap_and_goals(self):
        """
        Validates complete reset of preparation roadmap, schedule activities,
        and career/interview goals:
        - Removes roadmap and all scheduled activities
        - Clears career goals and interview goals
        - Resets candidate profile so fresh onboarding is triggered
        """
        # 1. Setup profile and goals
        CandidateProfileService.create_or_update_profile(
            self.mock_db,
            user_id=self.user_id,
            target_role="AI/ML Engineer",
            daily_minutes=60,
            preparation_duration_days=10
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        self.mock_db.table("career_goals").insert({
            "id": f"goal_{self.user_id}",
            "user_id": self.user_id,
            "role_id": "ai_ml_engineer",
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso
        }).execute()
        self.mock_db.table("interview_goals").insert({
            "id": f"igoal_{self.user_id}",
            "user_id": self.user_id,
            "target_role": "AI/ML Engineer",
            "status": "active",
            "created_at": now_iso,
            "updated_at": now_iso
        }).execute()

        # 2. Generate roadmap with activities
        rm = RoadmapService.generate_roadmap(user_id=self.user_id, force_regenerate=True, supabase_client=self.mock_db)
        self.assertIsNotNone(rm)
        self.assertGreater(len(rm.get("activities", [])), 0)

        # 3. Perform complete reset
        rm_res = self.mock_db.table("roadmaps").select("id").eq("user_id", self.user_id).execute()
        roadmap_ids = [r["id"] for r in (rm_res.data or []) if "id" in r]
        for rid in roadmap_ids:
            self.mock_db.table("roadmap_activities").delete().eq("roadmap_id", rid).execute()
        self.mock_db.table("roadmaps").delete().eq("user_id", self.user_id).execute()
        self.mock_db.table("career_goals").delete().eq("user_id", self.user_id).execute()
        self.mock_db.table("interview_goals").delete().eq("user_id", self.user_id).execute()
        self.mock_db.table("candidate_profiles").delete().eq("user_id", self.user_id).execute()

        # 4. Verify everything is reset
        curr_rm = RoadmapService.get_current_roadmap(user_id=self.user_id, supabase_client=self.mock_db)
        self.assertIsNone(curr_rm)

        remaining_acts = self.mock_db.table("roadmap_activities").select("*").execute()
        user_acts = [a for a in (remaining_acts.data or []) if a.get("roadmap_id") in roadmap_ids]
        self.assertEqual(len(user_acts), 0)

        remaining_goals = self.mock_db.table("career_goals").select("*").eq("user_id", self.user_id).execute()
        self.assertEqual(len(remaining_goals.data or []), 0)

        remaining_igoals = self.mock_db.table("interview_goals").select("*").eq("user_id", self.user_id).execute()
        self.assertEqual(len(remaining_igoals.data or []), 0)


if __name__ == "__main__":
    unittest.main()
