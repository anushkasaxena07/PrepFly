import unittest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestSuperAdminAuth(unittest.TestCase):
    """Unit tests for SuperAdmin Authentication, Role Authorization, and Protected Endpoints."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        from app import supabase
        from werkzeug.security import generate_password_hash
        try:
            supabase.table("super_admin").upsert({
                "id": "sa_test_01",
                "name": "Super Admin",
                "email": "saxenaanushka9645@gmail.com",
                "password_hash": generate_password_hash("valid_admin_password"),
                "role": "SUPER_ADMIN"
            }).execute()
        except Exception:
            pass

    def test_superadmin_login_success(self):
        """Authorized superadmin email should log in and receive token and permissions."""
        res = self.client.post("/api/superadmin/login", json={
            "email": "saxenaanushka9645@gmail.com",
            "password": "valid_admin_password"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("access_token", data)
        self.assertEqual(data["superadmin"]["role"], "SUPER_ADMIN")

    def test_superadmin_login_unauthorized_email(self):
        """Unauthorized non-admin email should be rejected."""
        res = self.client.post("/api/superadmin/login", json={
            "email": "intruder@randomdomain.com",
            "password": "password123"
        })
        self.assertIn(res.status_code, [401, 403])
        data = res.get_json()
        self.assertIn("error", data)

    def test_superadmin_dashboard_authorization(self):
        """Superadmin dashboard should reject unauthorized requests and allow authenticated requests."""
        # Unauthorized request
        unauth_res = self.client.get("/api/superadmin/dashboard")
        self.assertIn(unauth_res.status_code, [401, 403])

        # Authorized with genuine JWT bearer token
        login_res = self.client.post("/api/superadmin/login", json={
            "email": "saxenaanushka9645@gmail.com",
            "password": "valid_admin_password"
        })
        token = login_res.get_json()["access_token"]
        auth_res = self.client.get("/api/superadmin/dashboard", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(auth_res.status_code, 200)
        data = auth_res.get_json()
        self.assertIn("total_organizations", data)
        self.assertIn("system_health", data)

if __name__ == "__main__":
    unittest.main()
