"""
Unit & Integration Tests for PrepFly Per-User API Usage Tracking & Spending Limits.
"""

import json
import unittest
from datetime import datetime, timezone

from services.api_usage_service import (
    ApiUsageService,
    SpendingLimitExceededError,
    calculate_call_cost,
    estimate_token_count,
)


class TestApiUsageAndSpendingLimits(unittest.TestCase):
    def setUp(self):
        ApiUsageService.reset_for_tests()

    def tearDown(self):
        ApiUsageService.reset_for_tests()

    def test_calculate_call_cost_flash(self):
        # 1,000,000 prompt tokens = $0.075, 1,000,000 completion tokens = $0.300
        cost = calculate_call_cost("gemini-2.5-flash", 1_000_000, 1_000_000)
        self.assertAlmostEqual(cost, 0.375, places=5)

        # Realistic interview turn: 1,600 prompt, 200 completion
        turn_cost = calculate_call_cost("gemini-2.5-flash", 1600, 200)
        expected = (1600 / 1e6 * 0.075) + (200 / 1e6 * 0.300)
        self.assertAlmostEqual(turn_cost, expected, places=6)

    def test_calculate_call_cost_flash_lite(self):
        cost = calculate_call_cost("gemini-3.5-flash-lite", 1_000_000, 1_000_000)
        self.assertAlmostEqual(cost, 0.1875, places=5)

    def test_estimate_token_count(self):
        text = "Hello world! This is a test of the token estimator."
        self.assertGreater(estimate_token_count(text), 5)
        self.assertEqual(estimate_token_count(""), 0)

    def test_record_and_get_user_monthly_spend(self):
        user_id = "test_student_user_1"
        rec1 = ApiUsageService.record_api_usage(
            user_id=user_id,
            feature="interview_turn",
            model="gemini-2.5-flash",
            prompt_tokens=1500,
            completion_tokens=250,
        )
        self.assertEqual(rec1["user_id"], user_id)
        self.assertEqual(rec1["total_tokens"], 1750)
        self.assertGreater(rec1["cost_usd"], 0.0)

        rec2 = ApiUsageService.record_api_usage(
            user_id=user_id,
            feature="mentor_chat",
            model="gemini-2.5-flash",
            prompt_tokens=1000,
            completion_tokens=200,
        )

        spend = ApiUsageService.get_user_monthly_spend(user_id)
        self.assertEqual(spend["total_calls"], 2)
        self.assertEqual(spend["total_tokens"], 2950)
        self.assertAlmostEqual(spend["total_spend_usd"], rec1["cost_usd"] + rec2["cost_usd"], places=5)
        self.assertIn("interview_turn", spend["by_feature_spend_usd"])
        self.assertIn("mentor_chat", spend["by_feature_spend_usd"])

    def test_spending_limit_allowed_and_breach(self):
        user_id = "test_budget_student"
        # Set a small test budget of $0.001
        ApiUsageService.set_user_spending_limit(user_id, monthly_budget_usd=0.001, is_hard_limit=True)

        allowed, info = ApiUsageService.check_user_spending_limit(user_id, estimated_cost_usd=0.0001)
        self.assertTrue(allowed)
        self.assertEqual(info["budget_usd"], 0.001)

        # Simulate heavy usage exceeding budget
        ApiUsageService.record_api_usage(
            user_id=user_id,
            feature="interview_report",
            model="gemini-2.5-pro",
            prompt_tokens=5000,
            completion_tokens=2000,  # cost = (5000*1.25/1e6) + (2000*5.00/1e6) = 0.00625 + 0.010 = 0.01625 > 0.001
        )

        allowed_after, info_after = ApiUsageService.check_user_spending_limit(user_id, estimated_cost_usd=0.0001)
        self.assertFalse(allowed_after)
        self.assertIn("exceeded", info_after.get("reason", ""))

        with self.assertRaises(SpendingLimitExceededError):
            ApiUsageService.check_user_spending_limit(user_id, estimated_cost_usd=0.0001, raise_on_exceeded=True)


class TestApiUsageEndpoints(unittest.TestCase):
    def setUp(self):
        from app import app
        self.app = app.test_client()
        self.app.testing = True
        ApiUsageService.reset_for_tests()

    def tearDown(self):
        ApiUsageService.reset_for_tests()

    def test_get_user_api_usage_endpoint(self):
        user_id = "endpoint_test_user"
        ApiUsageService.record_api_usage(
            user_id=user_id,
            feature="interview_turn",
            model="gemini-2.5-flash",
            prompt_tokens=1200,
            completion_tokens=150,
        )

        resp = self.app.get(f"/api/user/api-usage?user_id={user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["user_id"], user_id)
        self.assertEqual(data["data"]["total_calls"], 1)
        self.assertGreater(data["data"]["monthly_budget_usd"], 0.0)

    def test_update_spending_limit_endpoint(self):
        payload = {
            "user_id": "vip_student",
            "monthly_budget_usd": 15.00,
            "is_hard_limit": True,
        }
        resp = self.app.post(
            "/api/admin/api-spending-limits",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["monthly_budget_usd"], 15.0)


if __name__ == "__main__":
    unittest.main()
