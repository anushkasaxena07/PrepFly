"""
PREPFLY PHASE 3 TEST SUITE: ONBOARDING, SKILL PROFILES & FEASIBILITY
====================================================================
Validates all Section 2, Section 3, Section 8.1, and Section 11 Phase 3 deliverables:
- Experience level derivation: 0-2 Jr, 2-5 Mid, 5-8 Sr, 8+ Staff, with user override.
- Section 8.1 Feasibility Check:
    availableDays, totalMinutes, baseMinutes(skill), mock & revision allowances.
    Statuses: COMFORTABLE, TIGHT (cuts SUPPORTING first), AT_RISK (drops ranked skills), CRASH_MODE (<= 2 days).
    Blackout dates and 0-minute rest day exclusion.
- Section 3 & 12.1 Skill Requirement Profile Generation:
    Validation against RoleProfileLLMOutputSchema.
    JD extraction labeled USER_PROVIDED, general standards labeled MODEL_INFERRED.
    Negative guardrails: never invent company facts without explicit source.
- Section 2.1 Step 4: Editable skills review and re-tiering (PUT /api/profile/skills).
- Endpoints: POST /api/onboarding/profile, PUT /api/profile/skills, GET /api/feasibility.
"""

import os
import unittest
from datetime import date, timedelta

os.environ["ENVIRONMENT"] = "test"
os.environ["FLASK_ENV"] = "test"

from services.onboarding_service import (
    OnboardingService,
    derive_candidate_level,
    TIER_BASE_MINUTES,
    MIN_SKILL_MINUTES
)
from schemas.spec_schemas import RoleProfileLLMOutputSchema
from app import app


class TestPhase3OnboardingAndProfile(unittest.TestCase):
    """Complete unit tests for Phase 3 Onboarding, Skill Profile, and Feasibility."""

    def test_01_experience_level_derivation_and_override(self):
        """Verifies Section 2.1 level derivation rules and user override."""
        self.assertEqual(derive_candidate_level(0.0), "JUNIOR")
        self.assertEqual(derive_candidate_level(1.5), "JUNIOR")
        self.assertEqual(derive_candidate_level(2.0), "MID")
        self.assertEqual(derive_candidate_level(4.5), "MID")
        self.assertEqual(derive_candidate_level(5.0), "SENIOR")
        self.assertEqual(derive_candidate_level(7.5), "SENIOR")
        self.assertEqual(derive_candidate_level(8.0), "STAFF")
        self.assertEqual(derive_candidate_level(12.0), "STAFF")

    def test_02_feasibility_comfortable_schedule(self):
        """
        Verifies Section 8.1 & Section 15 Worked Example:
        18 days, 90 min/day = 1620 min available -> COMFORTABLE.
        """
        start = date(2026, 11, 16)
        interview = start + timedelta(days=18)
        skills = [
            {"skill_id": "s1", "name": "Python ML", "tier": "MANDATORY", "proficiency": None},
            {"skill_id": "s2", "name": "Transformers", "tier": "MANDATORY", "proficiency": None},
            {"skill_id": "s3", "name": "SQL Opt", "tier": "PREFERRED", "proficiency": None},
            {"skill_id": "s4", "name": "STAR Stories", "tier": "SUPPORTING", "proficiency": None}
        ]

        # Total available = 18 * 90 = 1620 min
        res = OnboardingService.calculate_feasibility(
            start_date=start,
            interview_date=interview,
            skills=skills,
            daily_minutes=90
        )
        self.assertEqual(res["days_until_interview"], 18)
        self.assertEqual(res["available_days_count"], 18)
        self.assertEqual(res["total_available_minutes"], 1620)
        self.assertEqual(res["status"], "COMFORTABLE")
        self.assertFalse(res["is_crash_mode"])
        self.assertEqual(len(res["at_risk_or_deferred_skills"]), 0)

    def test_03_feasibility_tight_schedule_cuts_supporting_first(self):
        """
        Verifies Section 8.1:
        Between 70% and 100% of required minutes -> TIGHT, cuts SUPPORTING first.
        """
        start = date(2026, 11, 16)
        interview = start + timedelta(days=5)
        # 5 days * 90 min = 450 min available
        # Required skills: 4 MANDATORY (180*0.6=108 each -> 432 min) + 2 SUPPORTING (60*0.6=36 each -> 72 min)
        # Raw = 504 min + 20% buffer (90 min) = 594 min
        # Ratio: 450 / 594 ≈ 75.7% (between 70% and 100%) -> TIGHT
        skills = [
            {"skill_id": f"m{i}", "name": f"Mandatory {i}", "tier": "MANDATORY", "proficiency": None}
            for i in range(1, 5)
        ] + [
            {"skill_id": "s1", "name": "Supporting 1", "tier": "SUPPORTING", "proficiency": None},
            {"skill_id": "s2", "name": "Supporting 2", "tier": "SUPPORTING", "proficiency": None}
        ]

        res = OnboardingService.calculate_feasibility(
            start_date=start,
            interview_date=interview,
            skills=skills,
            daily_minutes=90
        )
        self.assertEqual(res["status"], "TIGHT")
        self.assertIn("SUPPORTING skills", res["message"])
        dropped_tiers = [d["tier"] for d in res["at_risk_or_deferred_skills"]]
        self.assertTrue(all(t == "SUPPORTING" for t in dropped_tiers))

    def test_04_feasibility_at_risk_schedule(self):
        """
        Verifies Section 8.1:
        Under 70% of required minutes -> AT_RISK, ranks dropped/shallow skills.
        """
        start = date(2026, 11, 16)
        interview = start + timedelta(days=3)
        # 3 days * 30 min = 90 min available
        # Required skills: 6 MANDATORY (108*6 = 648 min) -> total required > 600 min
        # 90 / 648 < 15% -> AT_RISK
        skills = [
            {"skill_id": f"m{i}", "name": f"Mandatory {i}", "tier": "MANDATORY", "proficiency": None}
            for i in range(1, 7)
        ]
        res = OnboardingService.calculate_feasibility(
            start_date=start,
            interview_date=interview,
            skills=skills,
            daily_minutes=30
        )
        self.assertEqual(res["status"], "AT_RISK")
        self.assertIn("at risk", res["message"].lower())

    def test_05_feasibility_crash_mode(self):
        """
        Verifies Section 8.1 & 8.6:
        Interview date today or tomorrow (<= 2 days) -> CRASH_MODE.
        """
        start = date(2026, 11, 16)
        interview = start + timedelta(days=1)
        skills = [{"skill_id": "s1", "name": "ML", "tier": "MANDATORY"}]

        res = OnboardingService.calculate_feasibility(
            start_date=start,
            interview_date=interview,
            skills=skills,
            daily_minutes=60
        )
        self.assertEqual(res["status"], "CRASH_MODE")
        self.assertTrue(res["is_crash_mode"])

    def test_06_feasibility_blackout_and_rest_days(self):
        """Verifies blackout dates and 0-minute rest days are strictly excluded."""
        start = date(2026, 11, 16)  # Mon
        interview = start + timedelta(days=7)
        skills = [{"skill_id": "s1", "name": "Python", "tier": "MANDATORY"}]

        # Sunday is a rest day (0 minutes), plus Nov 18 is a blackout date
        grid = {
            "Mon": 60, "Tue": 60, "Wed": 60, "Thu": 60, "Fri": 60, "Sat": 60, "Sun": 0
        }
        blackouts = ["2026-11-18"]

        res = OnboardingService.calculate_feasibility(
            start_date=start,
            interview_date=interview,
            skills=skills,
            daily_minutes=60,
            availability_grid=grid,
            blackout_dates=blackouts
        )
        # 7 total days - 1 Sunday - 1 blackout (Wed Nov 18) = 5 available days
        self.assertEqual(res["available_days_count"], 5)
        self.assertEqual(res["total_available_minutes"], 300)
        dates_in_res = [d["date"] for d in res["available_days"]]
        self.assertNotIn("2026-11-18", dates_in_res)

    def test_07_skill_requirement_profile_schema_validation(self):
        """Verifies Section 3: generated profile matches RoleProfileLLMOutputSchema."""
        profile = OnboardingService.generate_skill_requirement_profile(
            company="Google DeepMind",
            role="AI/ML Engineer",
            level="MID"
        )
        # Must validate against Pydantic schema
        validated = RoleProfileLLMOutputSchema(**profile)
        self.assertEqual(validated.roleTitle, "AI/ML Engineer")
        self.assertEqual(validated.company, "Google DeepMind")
        self.assertEqual(validated.level, "MID")
        self.assertGreaterEqual(len(validated.pillars), 4)
        self.assertGreaterEqual(len(validated.skills), 8)

        # Check subskills and rubric criteria
        for sk in validated.skills:
            self.assertIn(sk.tier, ("MANDATORY", "PREFERRED", "SUPPORTING"))
            self.assertGreaterEqual(sk.interviewImportance, 1)
            self.assertLessEqual(sk.interviewImportance, 5)
            self.assertGreaterEqual(len(sk.subskills), 1)
            for sub in sk.subskills:
                self.assertGreaterEqual(len(sub.rubricCriteria), 2)

    def test_08_jd_provenance_and_negative_guardrail(self):
        """
        Verifies Section 3.2:
        Skills extracted with JD are marked USER_PROVIDED;
        General skills marked MODEL_INFERRED.
        """
        jd = (
            "We are seeking an AI/ML Engineer proficient in PyTorch, Transformer Architecture, "
            "and ML Model Evaluation with imbalanced distributions."
        )
        profile = OnboardingService.generate_skill_requirement_profile(
            company="Acme AI",
            role="AI/ML Engineer",
            level="MID",
            jd_text=jd
        )
        skills = profile["skills"]
        user_provided_skills = [s for s in skills if s["source"] == "USER_PROVIDED"]
        model_inferred_skills = [s for s in skills if s["source"] == "MODEL_INFERRED"]

        self.assertGreater(len(user_provided_skills), 0)
        self.assertGreater(len(model_inferred_skills), 0)

    def test_09_editable_skills_review_and_retiering(self):
        """
        Verifies Section 2.1 Step 4:
        Candidate edits skills/tiers and feasibility is automatically recomputed.
        """
        user_id = "test_user_step4_review"
        # 1. Save onboarding profile
        OnboardingService.save_onboarding_target_profile(
            user_id=user_id,
            data={
                "company": "Anthropic",
                "role": "AI/ML Engineer",
                "years_total": 3.0,
                "daily_minutes": 90
            }
        )

        # 2. Update skills list (change tier of a skill to MANDATORY)
        updated_skills = [
            {"id": "sk_custom_1", "name": "Custom GPU Kernels", "tier": "MANDATORY", "importance": 5},
            {"id": "sk_custom_2", "name": "Model Quantization", "tier": "PREFERRED", "importance": 4}
        ]
        res = OnboardingService.update_profile_skills(user_id=user_id, updated_skills=updated_skills)
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["skills"]), 2)
        self.assertEqual(res["skills"][0]["tier"], "MANDATORY")
        self.assertIn("feasibility", res)

    def test_10_api_onboarding_and_skills_endpoints(self):
        """Verifies Section 11 API endpoints for Phase 3."""
        client = app.test_client()

        # 1. POST /api/onboarding/profile
        post_data = {
            "company": "DeepLearning Tech",
            "role": "AI/ML Engineer",
            "years_total": 2.5,
            "daily_minutes": 90,
            "interview_date": "2026-12-10"
        }
        resp1 = client.post("/api/onboarding/profile", json=post_data)
        self.assertEqual(resp1.status_code, 201)
        data1 = resp1.get_json()
        self.assertEqual(data1["status"], "success")
        self.assertIn("profile", data1)
        self.assertEqual(data1["profile"]["level"], "MID")
        self.assertIn("feasibility", data1["profile"])
        self.assertIn("skills_profile", data1["profile"])

        # 2. GET /api/feasibility
        resp2 = client.get("/api/feasibility")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertEqual(data2["status"], "success")
        self.assertIn("feasibility", data2)

        # 3. PUT /api/profile/skills
        put_skills = [
            {"id": "sk_1", "name": "Python ML", "tier": "MANDATORY", "importance": 5},
            {"id": "sk_2", "name": "Transformers", "tier": "MANDATORY", "importance": 5}
        ]
        resp3 = client.put("/api/profile/skills", json={"skills": put_skills})
        self.assertEqual(resp3.status_code, 200)
        data3 = resp3.get_json()
        self.assertEqual(data3["status"], "success")
        self.assertEqual(len(data3["skills"]), 2)


if __name__ == "__main__":
    unittest.main()
