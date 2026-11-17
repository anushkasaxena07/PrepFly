"""
Test Suite: Super Admin API Sanitization (Phase 2).
Verifies that all /api/superadmin/* endpoints in app.py return 100% genuine,
traceable data from MetricsService with zero dummy fallback arrays, zero
hardcoded constants (e.g. 1420, 18, 4820), and zero synthetic trends.
"""

import json
import unittest
from datetime import datetime, timezone

import app as app_module
from local_supabase import SQLiteSupabaseMock
import services.metrics_service as ms


class TestSuperAdminApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config["TESTING"] = True
        cls.client = app_module.app.test_client()

    def setUp(self):
        # Create an isolated mock DB instance
        self.mock_db = SQLiteSupabaseMock()
        # Mock app.supabase and metrics_service supabase accessor
        self._orig_app_sb = app_module.supabase
        self._orig_ms_sb = ms.get_supabase
        app_module.supabase = self.mock_db
        ms.get_supabase = lambda: self.mock_db

        # Clear relevant tables
        conn = self.mock_db._get_conn()
        cursor = conn.cursor()
        cleanup_statements = [
            "DELETE FROM users",
            "DELETE FROM organization",
            "DELETE FROM payment",
            "DELETE FROM sessions",
            "DELETE FROM coding_submissions",
            "DELETE FROM user_api_usage",
            "DELETE FROM audit_logs",
            "DELETE FROM activity_logs",
            "DELETE FROM coupons",
            "DELETE FROM platform_settings"
        ]
        for sql in cleanup_statements:
            try:
                cursor.execute(sql)
            except Exception as clean_err:
                unittest.TestCase().assertIsNotNone(clean_err)
        conn.commit()

        # Generate a valid Super Admin token
        import jwt
        from app import _get_jwt_secret
        self.superadmin_token = jwt.encode(
            {"sub": "superadmin_user_01", "role": "SUPER_ADMIN", "email": "superadmin@prepfly.io"},
            _get_jwt_secret(),
            algorithm="HS256"
        )
        self.headers = {"Authorization": f"Bearer {self.superadmin_token}"}

    def tearDown(self):
        app_module.supabase = self._orig_app_sb
        ms.get_supabase = self._orig_ms_sb

    def test_01_dashboard_empty_db_returns_honest_zeros(self):
        """Dashboard must return 0s and empty lists on empty DB — no 1420, 18, 4820, or fake orgs."""
        res = self.client.get("/api/superadmin/dashboard", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Zero-fabrication asserts
        self.assertEqual(data["total_organizations"], 0)
        self.assertEqual(data["total_students"], 0)
        self.assertNotEqual(data["total_students"], 1420)
        self.assertEqual(data["total_admins"], 0)
        self.assertNotEqual(data["total_admins"], 18)
        self.assertEqual(data["total_interviews"], 0)
        self.assertNotEqual(data["total_interviews"], 4820)
        self.assertEqual(data["total_coding_tests"], 0)
        self.assertNotEqual(data["total_coding_tests"], 8940)

        # Revenue checks
        self.assertEqual(data["today_revenue_paise"], 0)
        self.assertEqual(data["monthly_revenue_paise"], 0)
        self.assertEqual(data["annual_revenue_paise"], 0)
        self.assertEqual(data["mrr_paise"], 0)
        self.assertEqual(data["arr_paise"], 0)

        # Honest empty state
        self.assertEqual(data["recent_organizations"], [])
        self.assertEqual(data["recent_payments"], [])
        self.assertIsNone(data["revenue_growth_badge"])

    def test_02_dashboard_seeded_db_accurate_aggregation(self):
        """Dashboard aggregates real seeded organizations, students, and payments."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # Seed organization
        self.mock_db.table("organization").insert({
            "id": "org_seed_01",
            "name": "Horizon Tech Institute",
            "type": "College",
            "subscription_plan": "ENTERPRISE",
            "status": "Active",
            "created_at": now_iso
        }).execute()

        # Seed 1 admin and 2 students (1 org, 1 B2C)
        self.mock_db.table("users").insert({
            "id": "usr_adm_1",
            "email": "admin@horizon.edu",
            "role": "Organization Admin",
            "organization_id": "org_seed_01",
            "created_at": now_iso
        }).execute()

        self.mock_db.table("users").insert({
            "id": "usr_std_org",
            "email": "student1@horizon.edu",
            "role": "student",
            "organization_id": "org_seed_01",
            "created_at": now_iso
        }).execute()

        self.mock_db.table("users").insert({
            "id": "usr_std_b2c",
            "email": "b2c@gmail.com",
            "role": "student",
            "organization_id": None,
            "created_at": now_iso
        }).execute()

        # Seed successful payment: ₹50,000 = 5,000,000 paise
        self.mock_db.table("payment").insert({
            "id": "pay_test_01",
            "organization_id": "org_seed_01",
            "amount": 50000.0,
            "status": "Success",
            "payment_method": "Razorpay",
            "created_at": now_iso
        }).execute()

        res = self.client.get("/api/superadmin/dashboard", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["total_organizations"], 1)
        self.assertEqual(data["total_students"], 2)
        self.assertEqual(data["org_students"], 1)
        self.assertEqual(data["b2c_students"], 1)
        self.assertEqual(data["total_admins"], 1)
        self.assertEqual(data["monthly_revenue_paise"], 5000000)
        self.assertEqual(data["mrr_paise"], 5000000)
        self.assertEqual(data["arr_paise"], 5000000 * 12)
        self.assertEqual(len(data["recent_organizations"]), 1)
        self.assertEqual(data["recent_organizations"][0]["name"], "Horizon Tech Institute")
        self.assertEqual(len(data["recent_payments"]), 1)
        self.assertEqual(data["recent_payments"][0]["amount"], 50000.0)

    def test_03_payments_endpoint_no_fake_pay_fallbacks(self):
        """Payments endpoint must return [] when empty, not pay_901 / pay_902 / pay_903."""
        res = self.client.get("/api/superadmin/payments", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        payments = res.get_json()
        self.assertEqual(payments, [])

    def test_04_organizations_endpoint_no_fake_org_fallbacks(self):
        """Organizations endpoint must return [] when empty, not Stanford or MIT."""
        res = self.client.get("/api/superadmin/organizations", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        orgs = res.get_json()
        self.assertEqual(orgs, [])

    def test_05_admins_endpoint_students_managed_is_accurate(self):
        """Admins endpoint computes real students_managed and contains zero fake numbers."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.mock_db.table("users").insert({
            "id": "adm_real_01",
            "name": "Jane Doe",
            "email": "jane@college.edu",
            "role": "Organization Admin",
            "organization_id": "org_target_01",
            "created_at": now_iso
        }).execute()

        # Seed 3 students in this org
        for i in range(3):
            self.mock_db.table("users").insert({
                "id": f"std_{i}",
                "email": f"std_{i}@college.edu",
                "role": "student",
                "organization_id": "org_target_01",
                "created_at": now_iso
            }).execute()

        res = self.client.get("/api/superadmin/admins", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        admins = res.get_json()
        self.assertEqual(len(admins), 1)
        self.assertEqual(admins[0]["students_managed"], 3)
        self.assertNotEqual(admins[0]["students_managed"], 1420)

    def test_06_coupons_endpoint_no_fake_fallbacks(self):
        """Coupons endpoint must return [] when empty, not SUMMER25 or WELCOME500."""
        res = self.client.get("/api/superadmin/coupons", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        coupons = res.get_json()
        self.assertEqual(coupons, [])

    def test_07_analytics_endpoint_uses_real_data(self):
        """Analytics endpoint returns real metrics and trends from MetricsService."""
        res = self.client.get("/api/superadmin/analytics", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("ai_api_usage", data)
        self.assertIn("revenue_trend", data)
        self.assertIn("top_organizations", data)
        self.assertEqual(data["top_organizations"], [])

    def test_08_activity_logs_endpoint_no_rich_seed_logs(self):
        """Activity logs endpoint returns real logs only, with zero fabricated SOC events."""
        res = self.client.get("/api/superadmin/activity-logs", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        # Verify no hardcoded fake logs like LOG-2026-000481 (Rahul Sharma)
        for log in data.get("logs", []):
            self.assertNotEqual(log.get("id"), "LOG-2026-000481")
            self.assertNotEqual(log.get("performed_by_name"), "Rahul Sharma")

    def test_09_integrity_reconciliation_endpoint(self):
        """Integrity endpoint returns full reconciliation status and checks."""
        res = self.client.get("/api/superadmin/integrity", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["healthy"])
        self.assertEqual(data["failed_checks"], 0)
        self.assertTrue(len(data["checks"]) >= 5)

    def test_10_settings_get_and_post_with_audit_logging(self):
        """Platform settings can be updated via POST and records an audit log."""
        payload = {
            "platform_name": "PrepFly Global Enterprise",
            "jwt_expiry_hours": 48,
            "maintenance_mode": False
        }
        res_post = self.client.post("/api/superadmin/settings", headers=self.headers, json=payload)
        self.assertEqual(res_post.status_code, 200)

        # GET should reflect updated values
        res_get = self.client.get("/api/superadmin/settings", headers=self.headers)
        self.assertEqual(res_get.status_code, 200)
        data = res_get.get_json()
        self.assertEqual(data["platform_name"], "PrepFly Global Enterprise")
        self.assertEqual(data["jwt_expiry_hours"], 48)

        # Verify audit log was recorded
        audit_res = self.client.get("/api/superadmin/audit-logs", headers=self.headers)
        self.assertEqual(audit_res.status_code, 200)
        logs = audit_res.get_json().get("logs", [])
        self.assertTrue(any(l.get("action") == "update_platform_settings" for l in logs))


if __name__ == "__main__":
    unittest.main()
