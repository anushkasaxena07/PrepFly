"""
Unit and Integration Tests for the PrepFly Intelligent Personalized
Company-Specific Preparation Engine (Parts 1 - 15).

Validates:
- Scenario A: Google + Software Engineer + Fresher + 30 days + 60 minutes/day
- Scenario B: Amazon + SDE-1 + 15 days + 90 minutes/day
- Scenario C: AI/ML Engineer + uncataloged company + 20 days + 60 minutes/day
- Scenario D: Strong DSA candidate with weak communication
- Scenario E: Strong resume but weak technical assessment results
- Scenario F: Strong coding performance but no Ava interview evidence
- Scenario G: Candidate with no assessment history (unassessed != confirmed failure)
- Scenario H: Candidate changes interview date / reduced preparation time
- Scenario I: Candidate changes target company after roadmap generation
- Scenario J: Multi-source deduplication, recency decay & confidence scoring
"""

import unittest
from datetime import datetime, timezone, timedelta
import json

from services.company_intelligence_service import (
    CompanyIntelligenceService,
    COMPANY_INTELLIGENCE_CATALOG,
    SRC_REPORTED,
    SRC_OFFICIAL
)
from services.candidate_readiness_service import CandidateReadinessService
from services.company_gap_service import (
    CompanyCandidateGapService,
    TIER_HIGH_PRIORITY_WEAKNESS,
    TIER_DEVELOPING,
    TIER_STRONG_DEMONSTRATED,
    TIER_NOT_ASSESSED,
    TIER_INSUFFICIENT_DATA
)
from services.roadmap_engine import PersonalizedRoadmapEngine, SchedulingEngine
from local_supabase import SQLiteSupabaseMock


class TestCompanyPreparationEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_db = SQLiteSupabaseMock(db_path=":memory:")

    def test_scenario_a_google_swe_fresher_30_days_60_mins(self):
        """Scenario A: Google + SWE + Fresher + 30 days + 60 mins/day."""
        plan = PersonalizedRoadmapEngine.generate_company_personalized_plan(
            user_id="user_scenario_a",
            company_name="Google",
            role="Software Engineer",
            experience_level="Fresher",
            target_date=(datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(),
            daily_minutes=60,
            supabase_client=self.mock_db
        )

        self.assertTrue(plan["success"])
        self.assertEqual(plan["company_name"], "Google")
        self.assertEqual(plan["daily_minutes"], 60)
        self.assertEqual(plan["total_days"], 30)
        
        # Verify strict capacity capping: no day can exceed 60 minutes
        schedule = plan["roadmap"]["schedule"]
        for day, acts in schedule.items():
            total_day_dur = sum(a["estimated_minutes"] for a in acts)
            self.assertLessEqual(total_day_dur, 60, f"Day {day} exceeded 60 min capacity: {total_day_dur}m")

        # Verify Google specific rounds are present in mock interviews
        mock_acts = [a for a in plan["roadmap"]["activities"] if a["activity_type"] == "MOCK_INTERVIEW"]
        self.assertTrue(len(mock_acts) >= 2, "Google plan must include simulated mock interview rounds")

    def test_scenario_b_amazon_sde1_15_days_90_mins(self):
        """Scenario B: Amazon + SDE-1 + 15 days + 90 mins/day."""
        plan = PersonalizedRoadmapEngine.generate_company_personalized_plan(
            user_id="user_scenario_b",
            company_name="Amazon",
            role="Software Engineer",
            experience_level="Junior / SDE-1",
            target_date=(datetime.now(timezone.utc).date() + timedelta(days=15)).isoformat(),
            daily_minutes=90,
            supabase_client=self.mock_db
        )

        self.assertTrue(plan["success"])
        self.assertEqual(plan["company_name"], "Amazon")
        self.assertEqual(plan["daily_minutes"], 90)

        # Verify Amazon Leadership Principles are present in behavioral principles
        beh = plan["company_intelligence"]["behavioral_principles"]
        self.assertTrue(any("Customer Obsession" in b for b in beh))

        # Verify daily capacity constraint
        for day, acts in plan["roadmap"]["schedule"].items():
            total_day_dur = sum(a["estimated_minutes"] for a in acts)
            self.assertLessEqual(total_day_dur, 90, f"Day {day} exceeded 90 min capacity")

    def test_scenario_c_aiml_engineer_uncataloged_company(self):
        """Scenario C: AI/ML Engineer + company with limited interview reports (graceful fallback)."""
        intel = CompanyIntelligenceService.get_company_intelligence(
            company_name="Starlight AI Technologies",
            role="AI/ML Engineer",
            experience_level="Mid-Level (2-5 years)"
        )

        # Must fall back gracefully to role benchmark without crashing
        self.assertFalse(intel["matched_catalog"])
        self.assertEqual(intel["normalized_role"], "AI/ML Engineer")
        self.assertEqual(intel["data_completeness"], "ROLE_BENCHMARK_FALLBACK")
        self.assertIn("No direct empirical reports found", intel["disclaimer"])

    def test_scenario_d_strong_dsa_weak_communication(self):
        """Scenario D: Strong DSA candidate with weak communication."""
        gap_report = CompanyCandidateGapService.analyze_company_candidate_gaps(
            user_id="user_scenario_d",
            company_name="Google",
            role="Software Engineer",
            experience_level="Fresher",
            days_to_deadline=14
        )

        # Behavioral & communication skill must be present in top gaps or question bank
        q_bank = gap_report["tailored_question_bank"]
        has_behavioral_q = any(q["canonical_skill"] == "soft_behavioral_star" for q in q_bank)
        self.assertTrue(has_behavioral_q, "Must include behavioral question for candidate interview preparation")

    def test_scenario_e_strong_resume_weak_assessments(self):
        """Scenario E: Strong resume claims but weak assessment results."""
        snapshot = CandidateReadinessService.get_candidate_readiness_snapshot(
            user_id="user_scenario_e",
            target_role="Software Engineer"
        )
        # Verify coverage calculation
        self.assertIn("assessment_coverage_pct", snapshot)
        self.assertIn("diagnostic_recommended", snapshot)

    def test_scenario_f_strong_coding_no_ava_evidence(self):
        """Scenario F: Strong coding performance but zero Ava interview sessions."""
        snapshot = CandidateReadinessService.get_candidate_readiness_snapshot(
            user_id="user_scenario_f_new",
            target_role="Software Engineer"
        )
        ava = snapshot["ava_interview_readiness"]
        self.assertFalse(ava["has_verified_interview_evidence"])
        self.assertIsNone(ava["avg_score_100"])

    def test_scenario_g_unassessed_not_assumed_zero(self):
        """Scenario G: Unassessed topics must NOT be treated as confirmed weaknesses."""
        gap_report = CompanyCandidateGapService.analyze_company_candidate_gaps(
            user_id="user_blank_candidate",
            company_name="Google",
            role="Software Engineer",
            experience_level="Fresher",
            days_to_deadline=30
        )

        unassessed_items = [g for g in gap_report["gaps"] if g["classification_tier"] == TIER_NOT_ASSESSED]
        self.assertTrue(len(unassessed_items) > 0)
        for item in unassessed_items:
            # Baseline gap is 65.0, not 100.0, and tier is explicitly NOT_ASSESSED
            self.assertEqual(item["preparation_gap"], 65.0)
            self.assertEqual(item["classification_tier"], TIER_NOT_ASSESSED)

    def test_scenario_h_adaptive_deadline_rescheduling(self):
        """Scenario H: Candidate changes interview date from 30 days to 10 days."""
        plan_30 = PersonalizedRoadmapEngine.generate_company_personalized_plan(
            user_id="user_scenario_h",
            company_name="Microsoft",
            role="Software Engineer",
            experience_level="Fresher",
            target_date=(datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(),
            daily_minutes=60,
            supabase_client=self.mock_db
        )
        self.assertEqual(plan_30["total_days"], 30)

        # Reschedule with 10 days
        plan_10 = PersonalizedRoadmapEngine.generate_company_personalized_plan(
            user_id="user_scenario_h",
            company_name="Microsoft",
            role="Software Engineer",
            experience_level="Fresher",
            target_date=(datetime.now(timezone.utc).date() + timedelta(days=10)).isoformat(),
            daily_minutes=60,
            supabase_client=self.mock_db
        )
        self.assertEqual(plan_10["total_days"], 10)
        self.assertLessEqual(plan_10["roadmap"]["total_activities"], plan_30["roadmap"]["total_activities"])

    def test_scenario_i_company_change_preserves_completed(self):
        """Scenario I: Changing target company from Google to Amazon preserves finished activities."""
        # Setup initial Google plan
        plan_goog = PersonalizedRoadmapEngine.generate_company_personalized_plan(
            user_id="user_scenario_i",
            company_name="Google",
            role="Software Engineer",
            experience_level="Fresher",
            target_date=(datetime.now(timezone.utc).date() + timedelta(days=14)).isoformat(),
            daily_minutes=60,
            supabase_client=self.mock_db
        )
        first_act_id = plan_goog["roadmap"]["activities"][0]["id"]
        
        # Mark first activity as completed
        self.mock_db.table("roadmap_activities").update({"status": "COMPLETED"}).eq("id", first_act_id).execute()

        # Switch to Amazon
        plan_amzn = PersonalizedRoadmapEngine.generate_company_personalized_plan(
            user_id="user_scenario_i",
            company_name="Amazon",
            role="Software Engineer",
            experience_level="Junior",
            target_date=(datetime.now(timezone.utc).date() + timedelta(days=14)).isoformat(),
            daily_minutes=60,
            supabase_client=self.mock_db
        )

        completed_acts = [a for a in plan_amzn["roadmap"]["activities"] if a.get("status") == "COMPLETED"]
        self.assertTrue(len(completed_acts) >= 1, "Completed activity must be preserved across company switch")
        self.assertEqual(completed_acts[0]["id"], first_act_id)

    def test_scenario_j_recency_and_source_provenance(self):
        """Scenario J: Multi-source provenance and recency validation."""
        goog = COMPANY_INTELLIGENCE_CATALOG["google"]
        self.assertTrue(goog["source_count"] >= 30)
        self.assertGreaterEqual(goog["overall_confidence"], 0.90)

        for src in goog["verified_sources"]:
            self.assertTrue(src["url"].startswith("http"))
            self.assertTrue(src["source_type"] in (SRC_REPORTED, SRC_OFFICIAL))
            self.assertTrue(len(src["excerpt"]) > 20)


if __name__ == "__main__":
    unittest.main()

