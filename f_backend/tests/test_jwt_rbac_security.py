"""
Comprehensive Security Test Suite: JWT Validation, RBAC Boundaries, and Multi-Tenant Isolation
Exercises real authorization logic across:
1. Token signature, expiration, algorithm, audience, and claims validation.
2. Candidate attempting Admin and SuperAdmin operations.
3. Organization Admin attempting other Organizations' data and SuperAdmin operations.
4. Role escalation attempts via registration, profile update, and user-editable metadata.
5. Cross-organization access prevention.
6. Identity derivation from cryptographically validated token rather than client input.
"""

import unittest
import json
import os
import sys
import uuid
import jwt
from datetime import datetime, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app import app, _get_jwt_secret, supabase, _decode_jwt


class TestJWTRBACSecurity(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        self.secret = _get_jwt_secret()

        self.cand_a_id = f"cand_a_{uuid.uuid4().hex[:8]}"
        self.cand_b_id = f"cand_b_{uuid.uuid4().hex[:8]}"
        self.org_a_id = f"org_alpha_{uuid.uuid4().hex[:6]}"
        self.org_b_id = f"org_beta_{uuid.uuid4().hex[:6]}"

        # Standard Candidate Token (Flask-issued format, no aud)
        self.token_cand_a = jwt.encode({
            "sub": self.cand_a_id,
            "email": "cand_a@alpha.edu",
            "role": "candidate",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() + timedelta(days=7)
        }, self.secret, algorithm="HS256")

        # Supabase Auth Candidate Token (with aud: "authenticated")
        self.token_supabase_cand = jwt.encode({
            "aud": "authenticated",
            "sub": self.cand_b_id,
            "email": "cand_b@beta.edu",
            "role": "authenticated",
            "app_metadata": {"role": "candidate", "organization_id": self.org_b_id},
            "user_metadata": {"role": "SUPER_ADMIN"},  # Attempted escalation in user-editable metadata!
            "exp": datetime.utcnow() + timedelta(days=7)
        }, self.secret, algorithm="HS256")

        # Org Admin A Token
        self.token_admin_org_a = jwt.encode({
            "sub": f"admin_a_{uuid.uuid4().hex[:6]}",
            "email": "admin@alpha.edu",
            "role": "Organization Admin",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() + timedelta(days=7)
        }, self.secret, algorithm="HS256")

        # Org Admin B Token
        self.token_admin_org_b = jwt.encode({
            "sub": f"admin_b_{uuid.uuid4().hex[:6]}",
            "email": "admin@beta.edu",
            "role": "Organization Admin",
            "organization_id": self.org_b_id,
            "exp": datetime.utcnow() + timedelta(days=7)
        }, self.secret, algorithm="HS256")

        # Super Admin Token
        self.token_super_admin = jwt.encode({
            "sub": f"super_{uuid.uuid4().hex[:6]}",
            "email": "superadmin@prepfly.io",
            "role": "SUPER_ADMIN",
            "exp": datetime.utcnow() + timedelta(days=7)
        }, self.secret, algorithm="HS256")

        # Seeds for cross-tenant testing
        self.iv_a_id = f"iv_alpha_{uuid.uuid4().hex[:8]}"
        self.iv_b_id = f"iv_beta_{uuid.uuid4().hex[:8]}"
        self.student_b_id = f"std_b_{uuid.uuid4().hex[:8]}"
        self.test_b_id = f"ct_b_{uuid.uuid4().hex[:8]}"

        try:
            supabase.table("admin_interviews").upsert([
                {
                    "id": self.iv_a_id,
                    "organization_id": self.org_a_id,
                    "title": "Alpha Technical Interview",
                    "student_name": "Alice Candidate",
                    "overall_score": 8.5
                },
                {
                    "id": self.iv_b_id,
                    "organization_id": self.org_b_id,
                    "title": "Beta Secret Interview",
                    "student_name": "Bob Candidate",
                    "overall_score": 9.2
                }
            ]).execute()

            supabase.table("students").upsert([
                {
                    "id": self.student_b_id,
                    "organization_id": self.org_b_id,
                    "name": "Beta Student",
                    "email": "student@beta.edu",
                    "department": "Computer Science",
                    "interview_score": 8.9,
                    "coding_score": 92.0
                }
            ]).execute()

            supabase.table("admin_coding").upsert([
                {
                    "id": self.test_b_id,
                    "organization_id": self.org_b_id,
                    "title": "Beta Proprietary Algorithm Assessment",
                    "status": "Active"
                }
            ]).execute()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # 1. JWT VALIDATION TESTS
    # ══════════════════════════════════════════════════════════════════════════

    def test_jwt_valid_flask_token_accepted(self):
        """Standard Flask-issued token without aud claim is accepted and decoded."""
        res = self.client.get("/user-sessions", headers={"Authorization": f"Bearer {self.token_cand_a}"})
        self.assertEqual(res.status_code, 200)

    def test_jwt_valid_supabase_token_accepted(self):
        """Supabase Auth token with aud='authenticated' is accepted."""
        res = self.client.get("/user-sessions", headers={"Authorization": f"Bearer {self.token_supabase_cand}"})
        self.assertEqual(res.status_code, 200)

    def test_jwt_user_metadata_role_escalation_ignored(self):
        """User-editable Supabase user_metadata containing role='SUPER_ADMIN' is ignored."""
        decoded = _decode_jwt(self.token_supabase_cand)
        self.assertEqual(decoded["role"], "candidate")
        self.assertEqual(decoded["sub"], self.cand_b_id)

    def test_jwt_invalid_signature_rejected(self):
        """Token signed with forged/untrusted secret is rejected with 401."""
        forged_token = jwt.encode({
            "sub": self.cand_a_id,
            "role": "SUPER_ADMIN",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, "untrusted_secret_key_123456789012", algorithm="HS256")

        res = self.client.get("/api/admin/interviews", headers={"Authorization": f"Bearer {forged_token}"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("error", data)

    def test_jwt_expired_token_rejected(self):
        """Expired token is rejected with 401 and TOKEN_EXPIRED code."""
        expired = jwt.encode({
            "sub": self.cand_a_id,
            "role": "Organization Admin",
            "exp": datetime.utcnow() - timedelta(minutes=5)
        }, self.secret, algorithm="HS256")

        res = self.client.get("/api/admin/interviews", headers={"Authorization": f"Bearer {expired}"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data.get("code"), "TOKEN_EXPIRED")

    def test_jwt_malformed_token_rejected(self):
        """Malformed and garbage tokens are rejected with 401."""
        bad_tokens = [
            "not.a.token",
            "Bearer invalid_base64_payload",
            "eyJhbGciOiJIUzI1NiJ9.invalid.signature",
            "null",
            "undefined"
        ]
        for bad in bad_tokens:
            with self.subTest(token=bad):
                res = self.client.get("/api/admin/interviews", headers={"Authorization": f"Bearer {bad}"})
                self.assertEqual(res.status_code, 401)

    def test_jwt_untrusted_audience_rejected(self):
        """Token with an unauthorized audience (foreign service) is rejected."""
        foreign_token = jwt.encode({
            "aud": "foreign_unknown_application",
            "sub": self.cand_a_id,
            "role": "SUPER_ADMIN",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        res = self.client.get("/api/admin/interviews", headers={"Authorization": f"Bearer {foreign_token}"})
        self.assertEqual(res.status_code, 401)

    def test_jwt_missing_sub_claim_rejected(self):
        """Token missing the subject ('sub') claim cannot be decoded."""
        no_sub_token = jwt.encode({
            "email": "nosub@example.com",
            "role": "candidate",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        res = self.client.get("/user-sessions", headers={"Authorization": f"Bearer {no_sub_token}"})
        self.assertEqual(res.status_code, 401)

    # ══════════════════════════════════════════════════════════════════════════
    # 2. RBAC: CANDIDATES CANNOT ACCESS ADMIN / SUPERADMIN APIS
    # ══════════════════════════════════════════════════════════════════════════

    def test_candidate_cannot_access_org_admin_apis(self):
        """Candidate tokens are strictly rejected with 403 Forbidden across all Admin endpoints."""
        admin_endpoints = [
            ("GET", "/api/admin/interviews"),
            ("POST", "/api/admin/interviews"),
            ("GET", f"/api/admin/interview-pdf/{self.iv_a_id}"),
            ("GET", "/api/admin/coding"),
            ("POST", "/api/admin/coding"),
            ("GET", "/api/admin/question-bank"),
            ("POST", "/api/admin/question-bank"),
            ("GET", "/api/admin/reports"),
            ("POST", "/api/admin/reports/generate"),
            ("GET", f"/api/admin/reports/student/{self.student_b_id}/pdf"),
            ("GET", "/api/admin/analytics"),
            ("GET", "/api/admin/announcements"),
            ("POST", "/api/admin/announcements"),
            ("POST", "/api/admin/feedback-to-superadmin"),
            ("GET", "/api/admin/subscription"),
            ("GET", "/api/subscription/status"),
            ("GET", "/api/admin/settings"),
            ("POST", "/api/admin/settings"),
            ("GET", "/api/admin/students"),
            ("POST", "/api/admin/students/import")
        ]
        headers = {"Authorization": f"Bearer {self.token_cand_a}"}
        for method, ep in admin_endpoints:
            with self.subTest(endpoint=ep, method=method):
                if method == "GET":
                    res = self.client.get(ep, headers=headers)
                elif method == "POST":
                    res = self.client.post(ep, headers=headers, json={"title": "Unauthorized attempt"})
                self.assertEqual(res.status_code, 403)

    def test_unauthenticated_cannot_access_org_admin_apis(self):
        """Unauthenticated requests to Admin endpoints are strictly rejected with 401 Unauthorized."""
        admin_endpoints = [
            ("GET", "/api/admin/interviews"),
            ("GET", f"/api/admin/interview-pdf/{self.iv_a_id}"),
            ("GET", "/api/admin/coding"),
            ("GET", "/api/admin/question-bank"),
            ("GET", "/api/admin/reports"),
            ("GET", "/api/admin/analytics"),
            ("GET", "/api/admin/subscription"),
            ("GET", "/api/subscription/status"),
            ("GET", "/api/admin/settings")
        ]
        for method, ep in admin_endpoints:
            with self.subTest(endpoint=ep):
                res = self.client.get(ep)
                self.assertEqual(res.status_code, 401)

    def test_candidate_cannot_access_super_admin_apis(self):
        """Candidate tokens are strictly rejected with 403 Forbidden across SuperAdmin endpoints."""
        superadmin_endpoints = [
            "/api/superadmin/dashboard",
            "/api/superadmin/organizations",
            "/api/superadmin/ai-config",
            "/api/superadmin/feedback",
            "/api/superadmin/admins",
            "/api/superadmin/payments",
            "/api/superadmin/activity-logs",
            "/api/superadmin/settings"
        ]
        headers = {"Authorization": f"Bearer {self.token_cand_a}"}
        for ep in superadmin_endpoints:
            with self.subTest(endpoint=ep):
                res = self.client.get(ep, headers=headers)
                self.assertEqual(res.status_code, 403)

    def test_org_admin_cannot_access_super_admin_apis(self):
        """Organization Admin tokens are strictly rejected with 403 Forbidden on SuperAdmin endpoints."""
        superadmin_endpoints = [
            "/api/superadmin/dashboard",
            "/api/superadmin/organizations",
            "/api/superadmin/ai-config",
            "/api/superadmin/feedback",
            "/api/superadmin/admins"
        ]
        headers = {"Authorization": f"Bearer {self.token_admin_org_a}"}
        for ep in superadmin_endpoints:
            with self.subTest(endpoint=ep):
                res = self.client.get(ep, headers=headers)
                self.assertEqual(res.status_code, 403)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. ROLE ESCALATION RESISTANCE
    # ══════════════════════════════════════════════════════════════════════════

    def test_role_escalation_via_update_profile_rejected(self):
        """Candidates cannot escalate their role to ADMIN or SUPER_ADMIN via /update-profile."""
        res = self.client.put(
            "/update-profile",
            headers={"Authorization": f"Bearer {self.token_cand_a}"},
            json={"role": "SUPER_ADMIN"}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Only Super Admin can assign roles", res.get_json().get("error", ""))

    def test_role_escalation_via_register_prevented(self):
        """Registration always provisions pending account with role 'candidate' regardless of input."""
        test_email = f"escalate_{uuid.uuid4().hex[:6]}@example.com"
        res = self.client.post("/register", json={
            "name": "Attacker",
            "email": test_email,
            "password": "ValidPassword123!",
            "role": "SUPER_ADMIN"  # Malicious attempted payload
        })
        self.assertEqual(res.status_code, 200)

        # Pending user check
        from app import pending_users_memory
        self.assertIn(test_email, pending_users_memory)
        # Verify role is not elevated in memory or db
        self.assertNotIn("SUPER_ADMIN", str(pending_users_memory[test_email].get("role", "")))

    # ══════════════════════════════════════════════════════════════════════════
    # 4. CROSS-ORGANIZATION TENANT ISOLATION
    # ══════════════════════════════════════════════════════════════════════════

    def test_org_admin_cannot_access_other_org_interview_pdf(self):
        """Organization Admin A cannot access Organization B's interview dossier PDF."""
        headers_a = {"Authorization": f"Bearer {self.token_admin_org_a}"}
        res = self.client.get(f"/api/admin/interview-pdf/{self.iv_b_id}", headers=headers_a)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json().get("error", ""))

    def test_org_admin_cannot_access_other_org_student_dossier(self):
        """Organization Admin A cannot access Organization B's student dossier PDF."""
        headers_a = {"Authorization": f"Bearer {self.token_admin_org_a}"}
        res = self.client.get(f"/api/admin/reports/student/{self.student_b_id}/pdf", headers=headers_a)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json().get("error", ""))

    def test_org_admin_cannot_access_other_org_coding_leaderboard(self):
        """Organization Admin A cannot access Organization B's coding test leaderboard."""
        headers_a = {"Authorization": f"Bearer {self.token_admin_org_a}"}
        res = self.client.get(f"/api/admin/coding-test/{self.test_b_id}/leaderboard", headers=headers_a)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json().get("error", ""))

    def test_superadmin_can_access_cross_org_resources(self):
        """Super Admin legitimately has global oversight across organizations."""
        headers_sa = {"Authorization": f"Bearer {self.token_super_admin}"}
        res = self.client.get(f"/api/admin/interview-pdf/{self.iv_b_id}", headers=headers_sa)
        self.assertEqual(res.status_code, 200)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. TRUSTED IDENTITY DERIVATION & IDOR RESISTANCE
    # ══════════════════════════════════════════════════════════════════════════

    def test_candidate_cannot_update_another_user_profile(self):
        """Candidate A cannot modify Candidate B's profile by supplying B's user_id in the body."""
        res = self.client.put(
            "/update-profile",
            headers={"Authorization": f"Bearer {self.token_cand_a}"},
            json={
                "user_id": self.cand_b_id,
                "name": "Tampered Name"
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden: cannot update another user's profile", res.get_json().get("error", ""))

    def test_user_cannot_collide_or_takeover_existing_email(self):
        """User cannot update their profile email to an existing account's email."""
        # Create user B in DB
        try:
            supabase.table("users").upsert({
                "id": self.cand_b_id,
                "email": "victim_bob@alpha.edu",
                "name": "Bob Victim",
                "role": "candidate"
            }).execute()

            supabase.table("users").upsert({
                "id": self.cand_a_id,
                "email": "cand_a@alpha.edu",
                "name": "Alice Attacker",
                "role": "candidate"
            }).execute()
        except Exception:
            pass

        res = self.client.put(
            "/update-profile",
            headers={"Authorization": f"Bearer {self.token_cand_a}"},
            json={"email": "victim_bob@alpha.edu"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Email already in use", res.get_json().get("error", ""))


if __name__ == "__main__":
    unittest.main()
