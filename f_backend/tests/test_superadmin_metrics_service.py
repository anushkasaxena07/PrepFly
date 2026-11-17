"""
Unit tests for Super Admin MetricsService & Audit Logging (Phase 1).
Validates zero data fabrication, integer paise arithmetic, period-over-period formulas,
audit logging, and data integrity reconciliation checks.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone

from local_supabase import SQLiteSupabaseMock
import services.metrics_service as ms


class TestSuperadminMetricsService(unittest.TestCase):
    def setUp(self):
        # Initialize an isolated SQLite memory database for deterministic tests
        self.mock_db = SQLiteSupabaseMock()
        # Point metrics_service to this mock
        self._orig_get_supabase = ms.get_supabase
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
            "DELETE FROM audit_logs"
        ]
        for sql in cleanup_statements:
            try:
                cursor.execute(sql)
            except Exception as clean_err:
                unittest.TestCase().assertIsNotNone(clean_err)
        conn.commit()

    def tearDown(self):
        ms.get_supabase = self._orig_get_supabase

    def test_percentage_change_formula(self):
        """Verifies Golden Rule 4: Accurate period-over-period percentage calculation."""
        # Baseline growth
        self.assertEqual(ms.compute_percentage_change(150.0, 100.0), "+50.0%")
        # Baseline decline
        self.assertEqual(ms.compute_percentage_change(75.0, 100.0), "-25.0%")
        # When previous was 0 and current > 0 -> 'New'
        self.assertEqual(ms.compute_percentage_change(500.0, 0.0), "New")
        # When both are 0 -> None (hide badge)
        self.assertIsNone(ms.compute_percentage_change(0.0, 0.0))

    def test_currency_formatting_and_paise(self):
        """Verifies integer paise conversions and currency formatting."""
        self.assertEqual(ms._to_paise(500.0), 50000)
        self.assertEqual(ms._to_paise("1420.50"), 142050)
        self.assertEqual(ms._to_paise(None), 0)
        self.assertEqual(ms._to_paise(-10), 0)

        self.assertEqual(ms.format_currency(50000, "INR"), "₹500.00")
        self.assertEqual(ms.format_currency(4285000, "INR"), "₹42,850.00")

    def test_empty_database_returns_honest_zeros(self):
        """Verifies Golden Rule 1 & 2: An empty database returns 0s, never fabricated numbers."""
        overview = ms.get_dashboard_overview()

        # Zero fabrication checks
        self.assertEqual(overview["total_organizations"], 0)
        self.assertEqual(overview["total_students"], 0)
        self.assertNotEqual(overview["total_students"], 1420)  # Never clamped to 1420!
        self.assertEqual(overview["total_admins"], 0)
        self.assertNotEqual(overview["total_admins"], 18)      # Never clamped to 18!
        self.assertEqual(overview["total_interviews"], 0)
        self.assertNotEqual(overview["total_interviews"], 4820)
        self.assertEqual(overview["total_coding_tests"], 0)
        self.assertNotEqual(overview["total_coding_tests"], 8940)

        # Revenue checks
        self.assertEqual(overview["today_revenue_paise"], 0)
        self.assertEqual(overview["monthly_revenue_paise"], 0)
        self.assertEqual(overview["total_revenue_paise"], 0)
        self.assertEqual(overview["mrr_paise"], 0)
        self.assertEqual(overview["arr_paise"], 0)

        # Honest empty lists
        self.assertEqual(overview["recent_organizations"], [])
        self.assertEqual(overview["recent_payments"], [])

        # Growth badge when both current and previous are 0
        self.assertIsNone(overview["revenue_growth_badge"])

    def test_seeded_data_metrics_and_reconciliation(self):
        """Verifies accurate metric aggregation and population breakdown with real seeded data."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Seed 2 Organizations
        self.mock_db.table("organization").insert({
            "id": "org_real_01",
            "name": "Apex Engineering Institute",
            "type": "College",
            "subscription_plan": "ENTERPRISE",
            "status": "Active",
            "created_at": now_iso
        }).execute()

        self.mock_db.table("organization").insert({
            "id": "org_real_02",
            "name": "CloudScale Technologies",
            "type": "Company",
            "subscription_plan": "BUSINESS",
            "status": "Active",
            "created_at": now_iso
        }).execute()

        # 2. Seed Users: 1 Superadmin, 1 Org Admin, 3 Org Students, 2 B2C Students
        self.mock_db.table("users").insert({
            "id": "usr_sa",
            "email": "sa@prepfly.com",
            "role": "SUPER_ADMIN",
            "created_at": now_iso
        }).execute()

        self.mock_db.table("users").insert({
            "id": "usr_admin",
            "email": "admin@apex.edu",
            "role": "Organization Admin",
            "organization_id": "org_real_01",
            "created_at": now_iso
        }).execute()

        # 3 Org Students
        for i in range(1, 4):
            self.mock_db.table("users").insert({
                "id": f"usr_stud_org_{i}",
                "email": f"stud{i}@apex.edu",
                "role": "student",
                "organization_id": "org_real_01",
                "created_at": now_iso
            }).execute()

        # 2 Direct B2C Students (organization_id is None / NULL)
        for i in range(1, 3):
            self.mock_db.table("users").insert({
                "id": f"usr_stud_b2c_{i}",
                "email": f"b2c{i}@gmail.com",
                "role": "student",
                "organization_id": None,
                "created_at": now_iso
            }).execute()

        # 3. Seed Payments: 2 Successful, 1 Failed
        self.mock_db.table("payment").insert({
            "id": "pay_01",
            "organization_id": "org_real_01",
            "amount": 50000.0,
            "status": "Success",
            "created_at": now_iso
        }).execute()

        self.mock_db.table("payment").insert({
            "id": "pay_02",
            "organization_id": "org_real_02",
            "amount": 25000.0,
            "status": "Success",
            "created_at": now_iso
        }).execute()

        self.mock_db.table("payment").insert({
            "id": "pay_03",
            "organization_id": "org_real_01",
            "amount": 10000.0,
            "status": "Failed",
            "created_at": now_iso
        }).execute()

        # 4. Verify Dashboard Overview
        overview = ms.get_dashboard_overview()
        self.assertEqual(overview["total_organizations"], 2)
        self.assertEqual(overview["colleges_count"], 1)
        self.assertEqual(overview["companies_count"], 1)
        self.assertEqual(overview["total_admins"], 2)
        self.assertEqual(overview["total_students"], 5)
        self.assertEqual(overview["org_students"], 3)
        self.assertEqual(overview["b2c_students"], 2)

        # Revenue: 50,000 + 25,000 = 75,000 rupees = 7,500,000 paise (failed payment excluded)
        self.assertEqual(overview["monthly_revenue_paise"], 7500000)
        self.assertEqual(overview["monthly_revenue"], 75000.0)
        self.assertEqual(overview["total_revenue_paise"], 7500000)
        self.assertEqual(overview["mrr_paise"], 7500000)
        self.assertEqual(overview["arr_paise"], 7500000 * 12)

        # 5. Verify Student Metrics
        stud_metrics = ms.get_student_metrics()
        self.assertEqual(stud_metrics["total_students"], 5)
        self.assertEqual(stud_metrics["org_students"], 3)
        self.assertEqual(stud_metrics["b2c_students"], 2)

        # 6. Verify Payment Metrics
        pay_metrics = ms.get_payment_metrics()
        self.assertEqual(pay_metrics["total_transactions"], 3)
        self.assertEqual(pay_metrics["successful_transactions"], 2)
        self.assertEqual(pay_metrics["failed_transactions"], 1)
        self.assertEqual(pay_metrics["total_gross_revenue_paise"], 7500000)
        # GST at 18% of 75,000 = 13,500 rupees = 1,350,000 paise
        self.assertEqual(pay_metrics["total_gst_paise"], 1350000)
        self.assertEqual(pay_metrics["net_revenue_paise"], 7500000 - 1350000)

        # 7. Verify Data Integrity Audit
        audit = ms.get_data_integrity_audit()
        self.assertTrue(audit["healthy"])
        self.assertEqual(audit["failed_checks"], 0)
        self.assertEqual(audit["passed_checks"], audit["total_checks"])

    def test_orphan_student_detection_in_integrity_audit(self):
        """Verifies that an orphan student with non-existent organization_id triggers an audit failure."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # Seed valid organization
        self.mock_db.table("organization").insert({
            "id": "org_valid",
            "name": "Valid University",
            "created_at": now_iso
        }).execute()

        # Seed student pointing to non-existent organization
        self.mock_db.table("users").insert({
            "id": "usr_orphan",
            "email": "orphan@unknown.edu",
            "role": "student",
            "organization_id": "org_ghost_999",
            "created_at": now_iso
        }).execute()

        audit = ms.get_data_integrity_audit()
        self.assertFalse(audit["healthy"])
        orphan_check = next(c for c in audit["checks"] if c["check"] == "orphan_organization_memberships")
        self.assertFalse(orphan_check["passed"])
        self.assertEqual(orphan_check["discrepancy"], 1)

    def test_audit_logging_and_retrieval(self):
        """Verifies tamper-evident administrative action logging and query retrieval."""
        entry = ms.record_audit_log(
            actor_id="usr_superadmin_01",
            actor_email="superadmin@prepfly.com",
            action="update_platform_setting",
            target_type="platform_setting",
            target_id="setting_jwt_expiry",
            details={"old_hours": 24, "new_hours": 48},
            ip_address="192.168.1.50"
        )

        self.assertIsNotNone(entry.get("id"))
        self.assertEqual(entry["actor_id"], "usr_superadmin_01")
        self.assertEqual(entry["action"], "update_platform_setting")

        # Query back
        logs = ms.get_audit_logs(limit=10, action="update_platform_setting")
        self.assertTrue(len(logs) >= 1)
        match = next((l for l in logs if l["id"] == entry["id"]), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["actor_email"], "superadmin@prepfly.com")
        self.assertEqual(match["details"]["new_hours"], 48)


if __name__ == "__main__":
    unittest.main()

