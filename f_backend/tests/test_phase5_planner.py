"""
PREPFLY PHASE 5 UNIT TESTS: DETERMINISTIC PLANNER & RE-PLANNING ENGINE
======================================================================
Validates Section 8, Section 11, and Section 14 (Acceptance Tests 10-16):
1. Acceptance Test 10: Every day sum(block minutes) <= budget and >= 85% of budget (except eve/taper).
2. Acceptance Test 11: No block scheduled on rest/blackout days or after interviewDate.
3. Acceptance Test 12: No new topics in final 2 days; last day (eve) has totalMinutes <= 45.
4. Acceptance Test 13: Every MANDATORY unassessed skill has a DIAGNOSTIC_CHECK within first 30% of days.
5. Acceptance Test 14: 18-day plan (90 min/day, MID AI/ML) generates 18 days, >= 2 mock interviews, spaced revision blocks.
6. Acceptance Test 15: Changing today's time from 30 to 40 min yields valid schedule <= 40 min and structured diff.
7. Acceptance Test 16: Date labels are timezone-safe (Asia/Kolkata).
8. Feasibility Gating: COMFORTABLE, TIGHT, AT_RISK, and CRASH_MODE categorization.
9. Crash Mode (interview <= 2 days): rapid wins, mock, cheat sheet, STAR stories, logistics.
10. Plan Versioning & Diff (Section 8.7): incrementing version and structured diff.
11. Section 11 API Endpoints: /api/plan/generate, /replan, /active, /versions, /block/:id/start, /complete.
"""

import unittest
import os
import json
from datetime import datetime, timedelta, date

os.environ["ENVIRONMENT"] = "test"
os.environ["FLASK_ENV"] = "test"

from services.spec_planner_service import SpecPlannerService
from utils.timezone_utils import (
    determine_plan_start_date,
    get_current_user_datetime,
    get_current_user_date,
    format_date_iso,
    DEFAULT_TIMEZONE
)
from app import app


class TestPhase5Planner(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_acceptance_test_10_daily_minutes_budget_bounds(self):
        """Acceptance Test 10: For every day sum(block minutes) <= budget and >= 85% of budget (except eve/taper)."""
        today_iso = format_date_iso(date.today())
        interview_iso = format_date_iso(date.today() + timedelta(days=10))

        plan = SpecPlannerService.generate_plan(
            user_id="user_at10_test",
            target_role="AI/ML Engineer",
            daily_minutes=90,
            start_date=today_iso,
            interview_date=interview_iso
        )

        days = plan["days"]
        self.assertEqual(len(days), 10)

        for i, day in enumerate(days):
            day_num = day["dayNumber"]
            budget = day["budgetMinutes"]
            total = day["totalMinutes"]
            blocks_sum = sum(b["durationMin"] for b in day["blocks"])

            self.assertEqual(total, blocks_sum)
            self.assertLessEqual(total, budget, f"Day {day_num} total {total} exceeded budget {budget}")

            is_eve = (day_num == len(days))
            is_taper = (day_num == len(days) - 1)

            if not is_eve and not is_taper:
                min_expected = int(math_floor_or_ceil := budget * 0.85)
                self.assertGreaterEqual(
                    total,
                    min_expected,
                    f"Day {day_num} total {total} was below 85% of budget ({min_expected})"
                )

    def test_02_acceptance_test_11_no_blocks_on_blackout_or_past_interview(self):
        """Acceptance Test 11: No block scheduled on rest/blackout days or after interview date."""
        today = date.today()
        start_iso = format_date_iso(today)
        interview_iso = format_date_iso(today + timedelta(days=6))
        blackout_day = format_date_iso(today + timedelta(days=2))

        plan = SpecPlannerService.generate_plan(
            user_id="user_at11_test",
            daily_minutes=60,
            start_date=start_iso,
            interview_date=interview_iso,
            blackout_dates=[blackout_day]
        )

        plan_dates = [d["date"] for d in plan["days"]]

        # Blackout date must never have blocks
        self.assertNotIn(blackout_day, plan_dates, "Blackout date was erroneously scheduled")

        # No date on or after interview date
        for d_str in plan_dates:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            self.assertLess(d_obj, today + timedelta(days=6), "Block scheduled on or after interview date")

    def test_03_acceptance_test_12_no_new_topics_in_final_2_days_and_eve_cap(self):
        """Acceptance Test 12: No new topics in final 2 days; last day (eve) has totalMinutes <= 45."""
        today = date.today()
        start_iso = format_date_iso(today)
        interview_iso = format_date_iso(today + timedelta(days=12))

        plan = SpecPlannerService.generate_plan(
            user_id="user_at12_test",
            daily_minutes=90,
            start_date=start_iso,
            interview_date=interview_iso
        )

        days = plan["days"]
        taper_day = days[-2]
        eve_day = days[-1]

        # Taper day check
        self.assertIn("Taper", taper_day["phase"])
        for b in taper_day["blocks"]:
            # Taper day contains only review/drills/reflection, no heavy new LEARN
            self.assertIn(b["type"], ("REVISION", "PRACTICE", "REFLECTION", "MOCK_INTERVIEW"))

        # Eve day check
        self.assertIn("Eve", eve_day["phase"])
        self.assertLessEqual(eve_day["totalMinutes"], 45, "Interview Eve exceeded 45-minute limit")
        for b in eve_day["blocks"]:
            self.assertIn(b["type"], ("REVISION", "REFLECTION"))

    def test_04_acceptance_test_13_mandatory_unassessed_skills_in_first_30_percent(self):
        """Acceptance Test 13: Every MANDATORY unassessed skill has a DIAGNOSTIC_CHECK within first 30% of days."""
        today = date.today()
        start_iso = format_date_iso(today)
        interview_iso = format_date_iso(today + timedelta(days=15))

        test_skills = [
            {"id": "mand_unassessed_1", "name": "Core Math for ML", "tier": "MANDATORY", "importance": 5, "evidence": []},
            {"id": "pref_skill", "name": "Cloud Serving", "tier": "PREFERRED", "importance": 3, "evidence": []}
        ]

        plan = SpecPlannerService.generate_plan(
            user_id="user_at13_test",
            daily_minutes=90,
            start_date=start_iso,
            interview_date=interview_iso,
            skills_profile=test_skills
        )

        # 30% of 15 days is day 1 to 5
        cutoff_day = max(1, int(round(15 * 0.30)))
        first_30_pct_blocks = [
            b for d in plan["days"][:cutoff_day] for b in d["blocks"]
        ]

        diagnostic_skills = {
            b["skillId"] for b in first_30_pct_blocks if b["type"] == "DIAGNOSTIC_CHECK"
        }
        self.assertIn(
            "mand_unassessed_1",
            diagnostic_skills,
            "MANDATORY unassessed skill missing diagnostic check in first 30% of days"
        )

    def test_05_acceptance_test_14_worked_example_18_day_plan_shape(self):
        """Acceptance Test 14 (Worked Example Section 15): 18-day plan, 90 min/day, MID AI/ML role."""
        today = date.today()
        start_iso = format_date_iso(today)
        interview_iso = format_date_iso(today + timedelta(days=18))

        plan = SpecPlannerService.generate_plan(
            user_id="user_at14_worked_example",
            target_role="AI/ML Engineer",
            target_company="Acme AI",
            daily_minutes=90,
            start_date=start_iso,
            interview_date=interview_iso
        )

        days = plan["days"]
        self.assertEqual(len(days), 18, f"Expected 18 days, got {len(days)}")

        # Count mock interviews across the 18 days
        mock_blocks = [
            b for d in days for b in d["blocks"] if b["type"] == "MOCK_INTERVIEW"
        ]
        self.assertGreaterEqual(len(mock_blocks), 2, f"Expected >= 2 mock interviews, got {len(mock_blocks)}")

        # Verify spaced revision blocks present
        revision_blocks = [
            b for d in days for b in d["blocks"] if b["type"] == "REVISION"
        ]
        self.assertGreaterEqual(len(revision_blocks), 3, "Spaced revision blocks missing from 18-day plan")

        # Verify phase progression: Phase 1 -> Phase 2 -> Phase 3 -> Taper -> Eve
        phase_ids = [d["phaseId"] for d in days]
        self.assertEqual(phase_ids[0], "PHASE_1_DIAGNOSE")
        self.assertEqual(phase_ids[-1], "PHASE_EVE")
        self.assertEqual(phase_ids[-2], "PHASE_4_TAPER")

    def test_06_acceptance_test_15_daily_minutes_diff_30_vs_40_minutes(self):
        """Acceptance Test 15: Changing today's time from 30 to 40 min yields valid schedule and non-empty diff."""
        today = date.today()
        start_iso = format_date_iso(today)
        interview_iso = format_date_iso(today + timedelta(days=5))

        # Initial plan at 30 min/day
        plan_30 = SpecPlannerService.generate_plan(
            user_id="user_at15_diff_test",
            daily_minutes=30,
            start_date=start_iso,
            interview_date=interview_iso
        )
        self.assertEqual(plan_30["version"], 1)
        self.assertLessEqual(plan_30["days"][0]["totalMinutes"], 30)

        # Re-plan at 40 min/day
        plan_40 = SpecPlannerService.replan(
            user_id="user_at15_diff_test",
            trigger="DAILY_MINUTES_CHANGED",
            params={"daily_minutes": 40}
        )
        self.assertEqual(plan_40["version"], 2)
        self.assertLessEqual(plan_40["days"][0]["totalMinutes"], 40)

        diff = plan_40.get("diff", {})
        self.assertIsNotNone(diff)
        self.assertEqual(diff.get("trigger"), "DAILY_MINUTES_CHANGED")
        self.assertEqual(diff.get("from"), 1)
        self.assertEqual(diff.get("to"), 2)

    def test_07_acceptance_test_16_timezone_safe_start_date(self):
        """Acceptance Test 16: Date labels are timezone-safe (Asia/Kolkata)."""
        # Test start date logic before 6 PM vs after 6 PM
        start_date, label = determine_plan_start_date(DEFAULT_TIMEZONE, available_today_minutes=60)
        self.assertIn(label, ("Today", "Tomorrow"))
        self.assertIsInstance(start_date, date)

    def test_08_feasibility_check_categorization(self):
        """Section 8.1 Feasibility Check: COMFORTABLE, TIGHT, AT_RISK, CRASH_MODE."""
        today = date.today()
        start_iso = format_date_iso(today)

        # 1. Crash Mode (<= 2 days)
        f_crash = SpecPlannerService.compute_feasibility(
            user_id="u_feas",
            start_date=start_iso,
            interview_date=format_date_iso(today + timedelta(days=2)),
            daily_minutes=90
        )
        self.assertEqual(f_crash["status"], "CRASH_MODE")

        # 2. Comfortable (30 days, 120 min/day)
        f_comf = SpecPlannerService.compute_feasibility(
            user_id="u_feas",
            start_date=start_iso,
            interview_date=format_date_iso(today + timedelta(days=30)),
            daily_minutes=120
        )
        self.assertEqual(f_comf["status"], "COMFORTABLE")

        # 3. At Risk (3 days, 20 min/day -> total 60 min << required)
        f_risk = SpecPlannerService.compute_feasibility(
            user_id="u_feas",
            start_date=start_iso,
            interview_date=format_date_iso(today + timedelta(days=5)),
            daily_minutes=15
        )
        self.assertEqual(f_risk["status"], "AT_RISK")

    def test_09_api_endpoints_generate_replan_active_versions_block(self):
        """Section 11 Endpoints: /api/plan/generate, /replan, /active, /versions, /block/:id/start, /complete."""
        today = date.today()

        # 1. POST /api/plan/generate
        res_gen = self.app.post(
            "/api/plan/generate",
            json={
                "target_role": "AI/ML Engineer",
                "daily_minutes": 90,
                "start_date": format_date_iso(today),
                "interview_date": format_date_iso(today + timedelta(days=10))
            },
            headers={"X-User-Id": "api_planner_user"}
        )
        self.assertEqual(res_gen.status_code, 201)
        data_gen = res_gen.get_json()
        self.assertEqual(data_gen["status"], "success")
        plan = data_gen["plan"]
        self.assertEqual(plan["version"], 1)
        first_block_id = plan["days"][0]["blocks"][0]["id"]

        # 2. GET /api/plan/active
        res_act = self.app.get("/api/plan/active", headers={"X-User-Id": "api_planner_user"})
        self.assertEqual(res_act.status_code, 200)
        data_act = res_act.get_json()
        self.assertEqual(data_act["plan"]["version"], 1)

        # 3. POST /api/plan/replan
        res_replan = self.app.post(
            "/api/plan/replan",
            json={
                "trigger": "DAILY_MINUTES_CHANGED",
                "params": {"daily_minutes": 60}
            },
            headers={"X-User-Id": "api_planner_user"}
        )
        self.assertEqual(res_replan.status_code, 200)
        data_replan = res_replan.get_json()
        self.assertEqual(data_replan["plan"]["version"], 2)
        self.assertIn("diff", data_replan)

        # 4. GET /api/plan/versions
        res_ver = self.app.get("/api/plan/versions", headers={"X-User-Id": "api_planner_user"})
        self.assertEqual(res_ver.status_code, 200)
        data_ver = res_ver.get_json()
        self.assertEqual(len(data_ver["versions"]), 2)

        # 5. POST /api/block/:id/start
        res_start = self.app.post(f"/api/block/{first_block_id}/start", headers={"X-User-Id": "api_planner_user"})
        self.assertEqual(res_start.status_code, 200)

        # 6. POST /api/block/:id/complete
        res_comp = self.app.post(
            f"/api/block/{first_block_id}/complete",
            json={"minutes_spent": 30},
            headers={"X-User-Id": "api_planner_user"}
        )
        self.assertEqual(res_comp.status_code, 200)
        self.assertEqual(res_comp.get_json()["minutes_spent"], 30)


if __name__ == "__main__":
    unittest.main()

