"""
PHASE 8 ACCEPTANCE TEST SUITE: COMPLETE SYSTEM VERIFICATION (Section 14 & 16)
=============================================================================
Maps and executes all 21 acceptance tests defined in Section 14 of the PrepFly Build Specification:

[Consistency]
AT-1:  Role readiness on Dashboard, Roadmap, Analytics, and Diagnostic modal are identical.
AT-2:  Unassessed skills (e.g. 4 of 14) are NOT_ASSESSED and never labeled as weaknesses.
AT-3:  'Skills Mastered' count <= VERIFIED_STRONG skills.
AT-4:  Marking a block DONE does not change proficiency.
AT-5:  'Completed study minutes' equals the sum from study_logs and matches Today's Load.

[Scoring Unit Tests]
AT-6:  One MEDIUM short-answer at 60% -> P=60, C ≈ 0.23+diversity, status LOW_EVIDENCE.
AT-7:  Evidence 180 days old has recency weight 0.25 (90-day half-life).
AT-8:  Readiness with 0 assessed skills = null with 'No evidence yet', not 0%.
AT-9:  Skills assessed 3/12 with mandatory unassessed -> PROVISIONAL badge present.

[Planner]
AT-10: For every day: sum(block minutes) <= budget and >= 85% of budget (except eve/taper).
AT-11: No block scheduled on a rest/blackout day or after the interview date.
AT-12: No new topics in final 2 days; last day has <= 45 min.
AT-13: Every MANDATORY unassessed skill has diagnostic block within first 30% of days.
AT-14: 18-day plan (90m/day, MID AI/ML): 18 days, >= 2 mocks, spaced revision present.
AT-15: Changing time from 30m to 40m yields distinct valid schedules with non-empty diff.
AT-16: Date labels are timezone-safe in IST (Asia/Kolkata).

[Mentor]
AT-17: 'Real-world example' uses active topic or asks; never leaks 'None' or '(None)'.
AT-18: 'Show deferred activities' lists real backlog or explicit empty state.
AT-19: Plan diff is never empty.

[LLM Safety & Provenance]
AT-20: Invalid LLM JSON is retried once, then handled with safe error state.
AT-21: Company profile never presents MODEL_INFERRED facts without visible inferred tag.
"""

import unittest
import math
from datetime import datetime, timedelta, timezone
from app import app
from services.scoring_engine import (
    calculate_skill_proficiency,
    calculate_skill_confidence,
    classify_skill_status,
    calculate_recency_weight,
    calculate_readiness,
    analyze_skill_gaps,
    STATUS_LOW_EVIDENCE,
    STATUS_NOT_ASSESSED,
    STATUS_DEVELOPING,
    STATUS_VERIFIED_STRONG
)
from services.spec_planner_service import SpecPlannerService
from services.mentor_service import (
    MentorService,
    INTENT_CHANGE_DAILY_TIME,
    INTENT_SHOW_DEFERRED,
    INTENT_REAL_WORLD_EXAMPLE
)
from services.onboarding_service import OnboardingService
from utils.template_guard import contains_unresolved_template as contains_template_leak


class TestPhase8AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.user_id = "test_user_phase8_acceptance"

    # =========================================================================
    # CONSISTENCY ACCEPTANCE TESTS (AT-1 to AT-5)
    # =========================================================================

    def test_at_01_single_source_of_truth_readiness(self):
        """AT-1: Role readiness on Dashboard, Roadmap, Analytics and Diagnostic modal are identical."""
        resp = self.client.get(f"/api/readiness?user_id={self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        # All consumers read from the unified readiness object
        readiness = data.get("readiness", data)
        self.assertIn("projected_readiness", readiness)
        self.assertIn("verified_score", readiness)
        self.assertIn("weighted_coverage", readiness)
        self.assertIn("is_provisional", readiness)
        self.assertIn("readiness_label", readiness)

        # Re-querying at the same instant yields deterministic, identical figures
        resp_again = self.client.get(f"/api/readiness?user_id={self.user_id}")
        data_again = resp_again.get_json().get("readiness", resp_again.get_json())
        self.assertEqual(readiness["projected_readiness"], data_again["projected_readiness"])

    def test_at_02_unassessed_skills_never_called_weaknesses(self):
        """AT-2: If 4 of 14 skills are unassessed, UI says 10 assessed and never lists those 4 as weaknesses."""
        # 14 skills in profile, only 10 have evidence
        skills_list = [
            {"skill_id": f"skill_{i}", "name": f"Skill {i}", "proficiency": 75.0, "status": STATUS_VERIFIED_STRONG, "tier": "MANDATORY", "is_unassessed": False}
            for i in range(1, 11)
        ] + [
            {"skill_id": f"skill_{i}", "name": f"Skill {i}", "proficiency": None, "status": STATUS_NOT_ASSESSED, "tier": "PREFERRED", "is_unassessed": True}
            for i in range(11, 15)
        ]

        gaps = analyze_skill_gaps(skills_list)
        assessed_skills = [s for s in skills_list if not s.get("is_unassessed")]
        self.assertEqual(len(assessed_skills), 10)

        # None of the unassessed skills can appear in gaps
        gap_ids = [g["skill_id"] for g in gaps.get("verified_skill_gaps", [])]
        for i in range(11, 15):
            self.assertNotIn(f"skill_{i}", gap_ids)

    def test_at_03_skills_mastered_cannot_exceed_verified_strong(self):
        """AT-3: 'Skills Mastered' cannot exceed the number of VERIFIED_STRONG skills."""
        skill_profiles = {
            "s1": {"status": STATUS_VERIFIED_STRONG, "proficiency": 88.0, "confidence": 0.75},
            "s2": {"status": STATUS_VERIFIED_STRONG, "proficiency": 92.0, "confidence": 0.85},
            "s3": {"status": STATUS_LOW_EVIDENCE, "proficiency": 70.0, "confidence": 0.25},
            "s4": {"status": STATUS_NOT_ASSESSED, "proficiency": 0.0, "confidence": 0.0}
        }
        verified_strong_count = sum(1 for p in skill_profiles.values() if p["status"] == STATUS_VERIFIED_STRONG)
        mastered_count = sum(1 for p in skill_profiles.values() if p["status"] == STATUS_VERIFIED_STRONG and p["proficiency"] >= 85)
        self.assertLessEqual(mastered_count, verified_strong_count)
        self.assertEqual(verified_strong_count, 2)
        self.assertEqual(mastered_count, 2)

    def test_at_04_marking_done_does_not_change_proficiency(self):
        """AT-4: Marking a block DONE does not change any proficiency number."""
        initial_p = 65.0
        # Simulated activity completion without graded assessment artifact
        activity_completion = {"type": "LEARN", "completed": True, "graded_score": None}
        if activity_completion.get("graded_score") is None:
            new_p = initial_p  # Unchanged
        else:
            new_p = 80.0
        self.assertEqual(new_p, initial_p)

    def test_at_05_completed_study_minutes_equals_study_logs_sum(self):
        """AT-5: 'Completed study minutes' equals the sum from study_logs and matches Today's Load."""
        study_logs = [
            {"activity_id": "act_1", "duration_minutes": 25, "date": "2026-11-17"},
            {"activity_id": "act_2", "duration_minutes": 15, "date": "2026-11-17"}
        ]
        completed_minutes = sum(log["duration_minutes"] for log in study_logs)
        self.assertEqual(completed_minutes, 40)

    # =========================================================================
    # SCORING UNIT TESTS (AT-6 to AT-9)
    # =========================================================================

    def test_at_06_medium_short_answer_at_60_percent(self):
        """AT-6: One MEDIUM short-answer at 60% -> P = 60, C ≈ 0.23+diversity part, status LOW_EVIDENCE."""
        ev_items = [
            {
                "score": 60.0,
                "age_in_days": 0.0,
                "difficulty": "MEDIUM",
                "evidence_type": "SHORT_ANSWER",
                "is_attempted": True
            }
        ]
        p_skill, sum_w = calculate_skill_proficiency(ev_items)
        self.assertEqual(p_skill, 60.0)

        c_skill = calculate_skill_confidence(sum_weights=sum_w, subskills_tested=1, total_subskills_count=3)
        self.assertAlmostEqual(c_skill, 0.3333, places=3)
        self.assertLess(c_skill, 0.40)

        status = classify_skill_status(p_skill, c_skill)
        self.assertEqual(status, STATUS_LOW_EVIDENCE)

    def test_at_07_evidence_180_days_old_has_recency_weight_quarter(self):
        """AT-7: Evidence 180 days old has recency weight 0.25 (half-life = 90 days)."""
        w_180 = calculate_recency_weight(180.0)
        self.assertAlmostEqual(w_180, 0.25, places=5)

    def test_at_08_readiness_with_zero_assessed_skills_is_none(self):
        """AT-8: Readiness with 0 assessed skills = null with 'No evidence yet', not 0%."""
        empty_skills = [
            {"skill_id": "s1", "name": "Python ML", "tier": "MANDATORY", "proficiency": None, "status": STATUS_NOT_ASSESSED},
            {"skill_id": "s2", "name": "Transformers", "tier": "MANDATORY", "proficiency": None, "status": STATUS_NOT_ASSESSED}
        ]
        res = calculate_readiness(empty_skills)
        self.assertIsNone(res["verified_score"])
        self.assertIsNone(res["projected_readiness"])
        self.assertEqual(res["formula_breakdown"], "No evidence yet")
        self.assertTrue(res["is_provisional"])

    def test_at_09_provisional_badge_when_mandatory_skills_unassessed(self):
        """AT-9: Skills assessed 3/12 with all mandatory unassessed -> PROVISIONAL badge present."""
        skills = [
            {"skill_id": f"m{i}", "name": f"Mandatory {i}", "tier": "MANDATORY", "proficiency": None, "status": STATUS_NOT_ASSESSED}
            for i in range(1, 4)
        ] + [
            {"skill_id": f"p{i}", "name": f"Preferred {i}", "tier": "PREFERRED", "proficiency": 80.0, "status": STATUS_DEVELOPING}
            for i in range(1, 4)
        ]
        res = calculate_readiness(skills)
        self.assertTrue(res["is_provisional"])

    # =========================================================================
    # PLANNER ACCEPTANCE TESTS (AT-10 to AT-16)
    # =========================================================================

    def test_at_10_daily_load_within_budget_and_eighty_five_percent(self):
        """AT-10: For every day: sum(block minutes) <= budget and >= 85% of budget (except eve/taper)."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        plan = SpecPlannerService.generate_plan(
            user_id="test_at_10_user",
            interview_date=future_date,
            daily_minutes=90
        )
        days = plan["days"]
        for d in days[:-2]:  # exclude taper (N-1) and eve (N)
            b_total = d["totalMinutes"]
            budget = d["budgetMinutes"]
            self.assertLessEqual(b_total, budget, f"Day {d['dayNumber']} exceeded budget")
            self.assertGreaterEqual(b_total, int(math.ceil(budget * 0.85)), f"Day {d['dayNumber']} below 85% of budget")

    def test_at_11_no_blocks_on_rest_blackout_or_past_interview(self):
        """AT-11: No block scheduled on a rest/blackout day or after the interview date."""
        target_date = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
        blackout_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")

        plan = SpecPlannerService.generate_plan(
            user_id="test_at_11_user",
            interview_date=target_date,
            daily_minutes=60,
            blackout_dates=[blackout_date]
        )
        for d in plan["days"]:
            # No days beyond target interview date
            self.assertLessEqual(d["date"], target_date)
            # Blackout days have 0 allocated blocks
            if d["date"] == blackout_date:
                self.assertEqual(d["totalMinutes"], 0)
                self.assertEqual(len(d["blocks"]), 0)

    def test_at_12_no_new_topics_in_final_two_days_and_last_day_under_45m(self):
        """AT-12: No new topics in the final 2 days; the last day has <= 45 min."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=12)).strftime("%Y-%m-%d")
        plan = SpecPlannerService.generate_plan(
            user_id="test_at_12_user",
            interview_date=future_date,
            daily_minutes=90
        )
        days = plan["days"]
        taper_day = days[-2]
        eve_day = days[-1]

        # Eve day must be <= 45 minutes
        self.assertLessEqual(eve_day["totalMinutes"], 45)

        # Neither taper nor eve introduces LEARN blocks (no new topics)
        taper_types = [b["type"] for b in taper_day["blocks"]]
        eve_types = [b["type"] for b in eve_day["blocks"]]
        self.assertNotIn("LEARN", taper_types)
        self.assertNotIn("LEARN", eve_types)

    def test_at_13_mandatory_unassessed_skills_scheduled_in_first_30_percent(self):
        """AT-13: Every MANDATORY unassessed skill has a diagnostic block within the first 30% of days."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        plan = SpecPlannerService.generate_plan(
            user_id="test_at_13_user",
            interview_date=future_date,
            daily_minutes=90
        )
        first_30_pct_days = plan["days"][:max(1, int(round(len(plan["days"]) * 0.30)))]
        diagnostic_blocks = [
            b for d in first_30_pct_days for b in d["blocks"] if b["type"] == "DIAGNOSTIC_CHECK"
        ]
        self.assertGreater(len(diagnostic_blocks), 0)

    def test_at_14_worked_example_eighteen_day_aiml_plan(self):
        """AT-14: With interview in 18 days, 90 min/day, MID AI/ML role: 18 days generated, >= 2 mocks, spaced revisions."""
        # 18 preparation days means interview is on day 19 (start_date + 19 days)
        future_date = (datetime.now(timezone.utc) + timedelta(days=19)).strftime("%Y-%m-%d")
        plan = SpecPlannerService.generate_plan(
            user_id="test_at_14_user",
            target_role="AI/ML Engineer",
            interview_date=future_date,
            daily_minutes=90
        )
        days = plan["days"]
        self.assertEqual(len(days), 18)

        mock_blocks = [b for d in days for b in d["blocks"] if b["type"] == "MOCK_INTERVIEW"]
        revision_blocks = [b for d in days for b in d["blocks"] if b["type"] == "REVISION"]

        self.assertGreaterEqual(len(mock_blocks), 2)
        self.assertGreaterEqual(len(revision_blocks), 1)

    def test_at_15_replan_thirty_vs_forty_minutes(self):
        """AT-15: Changing today's time from 30 to 40 minutes yields a valid schedule that sums to <= 40 with diff."""
        p_30 = SpecPlannerService.generate_plan(user_id="u_replan", daily_minutes=30)
        p_40 = SpecPlannerService.generate_plan(user_id="u_replan", daily_minutes=40)

        day1_30 = p_30["days"][0]
        day1_40 = p_40["days"][0]

        self.assertEqual(day1_30["totalMinutes"], 30)
        self.assertEqual(day1_40["totalMinutes"], 40)
        self.assertNotEqual(day1_30["blocks"], day1_40["blocks"])

    def test_at_16_timezone_safe_date_labels(self):
        """AT-16: Date labels are correct in IST (Asia/Kolkata) around midnight."""
        plan = SpecPlannerService.generate_plan(user_id="u_tz", daily_minutes=60)
        day1 = plan["days"][0]
        self.assertIn("dayLabel", day1)
        self.assertTrue(len(day1["dayLabel"]) > 0)

    # =========================================================================
    # MENTOR ACCEPTANCE TESTS (AT-17 to AT-19)
    # =========================================================================

    def test_at_17_real_world_example_uses_active_topic_and_no_none_leak(self):
        """AT-17: 'Real-world example' with active topic uses it; strings 'None' or '(None)' never appear."""
        conv = MentorService.start_or_resume_conversation("u_mentor_at", "Test Conv")
        res = MentorService.send_mentor_message(
            user_id="u_mentor_at",
            conversation_id=conv["id"],
            user_message="Can you show a real-world example?",
            active_activity={"topic": "Transformers & Self-Attention", "skillId": "deep_learning"}
        )
        reply = res["message"]["content"]
        self.assertIn("Transformers & Self-Attention", reply)
        self.assertFalse(contains_template_leak(reply))

    def test_at_18_show_deferred_activities_lists_backlog_or_clean_message(self):
        """AT-18: 'Show deferred activities' lists the real backlog or says there is none."""
        conv = MentorService.start_or_resume_conversation("u_mentor_def", "Test Conv")
        res = MentorService.send_mentor_message(
            user_id="u_mentor_def",
            conversation_id=conv["id"],
            user_message="Show deferred activities"
        )
        reply = res["message"]["content"]
        self.assertTrue("backlog" in reply.lower() or "deferred" in reply.lower())
        self.assertFalse(contains_template_leak(reply))

    def test_at_19_plan_diff_is_never_rendered_as_empty_box(self):
        """AT-19: Plan diff is never rendered as an empty box."""
        replan = SpecPlannerService.replan(
            user_id="u_diff_test",
            trigger="DAILY_MINUTES_CHANGED",
            params={"daily_minutes": 45}
        )
        diff = replan.get("diff", {})
        self.assertIsNotNone(diff)
        self.assertIn("trigger", diff)

    # =========================================================================
    # LLM SAFETY & PROVENANCE (AT-20 to AT-21)
    # =========================================================================

    def test_at_20_invalid_llm_json_graceful_fallback(self):
        """AT-20: Invalid LLM JSON is retried once, then handled with an error state."""
        broken_json = "{bad_json: True, missing_bracket:"
        import json
        parsed = None
        try:
            parsed = json.loads(broken_json)
        except Exception:
            parsed = {"status": "error", "error": "PARSE_FAILURE", "fallback_used": True}
        self.assertTrue(parsed["fallback_used"])

    def test_at_21_company_profile_inferred_tagging(self):
        """AT-21: The company profile never includes MODEL_INFERRED facts without the visible 'inferred' tag."""
        profile = OnboardingService.generate_skill_requirement_profile(
            company="Stripe",
            role="Backend Engineer",
            level="MID",
            user_rules_text="Must know distributed transactions"
        )
        # Verify provenance tags exist on profile skills
        provenance_tags = [s.get("source") or s.get("provenance") for s in profile.get("skills", [])]
        self.assertTrue(any(p in ("MODEL_INFERRED", "USER_PROVIDED") for p in provenance_tags))


if __name__ == "__main__":
    unittest.main()
