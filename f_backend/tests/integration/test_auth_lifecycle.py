import unittest
import json
import os
import sys
import uuid

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, supabase, otps_memory

class TestAuthLifecycleIntegration(unittest.TestCase):
    """End-to-End Integration tests for User Registration, OTP Verification, Login, and Profile Management."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.unique_id = uuid.uuid4().hex[:8]
        self.test_email = f"candidate_{self.unique_id}@prepfly.test"
        self.test_password = "SecurePassword@2026"
        self.test_name = f"Test Candidate {self.unique_id}"

    def tearDown(self):
        # Clean up database test records
        try:
            supabase.table("users").delete().eq("email", self.test_email).execute()
            supabase.table("pending_users").delete().eq("email", self.test_email).execute()
            supabase.table("otps").delete().eq("email", self.test_email).execute()
        except Exception:
            pass

    def test_full_signup_profile_and_login_lifecycle(self):
        """End-to-End integration: Register -> Verify Signup OTP -> Access Protected Profile -> Login -> Verify Login OTP."""
        # Step 1: Register new user
        reg_res = self.client.post("/register", json={
            "name": self.test_name,
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(reg_res.status_code, 200)
        reg_data = reg_res.get_json()
        self.assertIn("message", reg_data)

        # Step 2: Verify Signup OTP with generated OTP
        otp_val = otps_memory.get((self.test_email, "signup"), {}).get("otp")
        verify_res = self.client.post("/auth/verify-signup-otp", json={
            "email": self.test_email,
            "otp": otp_val
        })
        self.assertEqual(verify_res.status_code, 201)
        auth_data = verify_res.get_json()
        self.assertIn("access_token", auth_data)
        token = auth_data["access_token"]
        user_id = auth_data["user_id"]

        # Step 3: Access protected /update-profile endpoint with issued JWT
        headers = {"Authorization": f"Bearer {token}"}
        update_res = self.client.put("/update-profile", headers=headers, json={
            "phone": "+1-555-0199",
            "name": f"{self.test_name} (Updated)"
        })
        self.assertEqual(update_res.status_code, 200)

        # Verify profile was actually updated in the database
        db_user = supabase.table("users").select("*").eq("id", user_id).execute()
        self.assertTrue(len(db_user.data) > 0)
        self.assertEqual(db_user.data[0]["phone"], "+1-555-0199")

        # Step 4: Login flow with password
        login_res = self.client.post("/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data.get("otp_required", False))

        # Step 5: Complete login with OTP
        login_otp_val = otps_memory.get((self.test_email, "login"), {}).get("otp")
        login_otp_res = self.client.post("/auth/verify-login-otp", json={
            "email": self.test_email,
            "otp": login_otp_val
        })
        self.assertEqual(login_otp_res.status_code, 200)
        final_auth = login_otp_res.get_json()
        self.assertIn("access_token", final_auth)
        self.assertEqual(final_auth["user_id"], user_id)

    def test_duplicate_registration_rejected(self):
        """Registering an already existing email address should return 400 Bad Request."""
        # First registration
        self.client.post("/register", json={
            "name": self.test_name,
            "email": self.test_email,
            "password": self.test_password
        })
        otp_val = otps_memory.get((self.test_email, "signup"), {}).get("otp")
        self.client.post("/auth/verify-signup-otp", json={
            "email": self.test_email,
            "otp": otp_val
        })

        # Second registration attempt with identical email
        dup_res = self.client.post("/register", json={
            "name": "Intruder Copy",
            "email": self.test_email,
            "password": "AnotherPassword"
        })
        self.assertEqual(dup_res.status_code, 400)
        data = dup_res.get_json()
        self.assertIn("already registered", data.get("error", "").lower())

    def test_unauthorized_profile_access_blocked(self):
        """Accessing protected endpoints without a token or with a bogus token must return 401."""
        # No header
        res_none = self.client.put("/update-profile", json={"phone": "+1-000-0000"})
        self.assertEqual(res_none.status_code, 401)

        # Forged token
        res_bad = self.client.put(
            "/update-profile",
            headers={"Authorization": "Bearer forged_invalid_jwt_signature"},
            json={"phone": "+1-000-0000"}
        )
        self.assertEqual(res_bad.status_code, 401)

if __name__ == "__main__":
    unittest.main()
