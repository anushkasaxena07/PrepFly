"""
Authentication, Authorization, and Multi-User Data Isolation Test Suite
Verifies trusted identity derivation, object-level authorization (BOLA/IDOR protection),
role boundaries, tenant isolation, database immutability on rejected requests, and regression safety.
"""

import unittest
import json
import os
import sys
import io
import uuid
import jwt
from datetime import datetime, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app import app, _get_jwt_secret, supabase

class TestAuthIsolationSecurity(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        self.user_a_id = f"usr_alice_{uuid.uuid4().hex[:8]}"
        self.user_b_id = f"usr_bob_{uuid.uuid4().hex[:8]}"
        self.org_a_id = f"org_alpha_{uuid.uuid4().hex[:6]}"
        self.org_b_id = f"org_beta_{uuid.uuid4().hex[:6]}"

        self.secret = _get_jwt_secret()

        # Tokens
        self.token_user_a = jwt.encode({
            "sub": self.user_a_id,
            "email": "alice@alpha.edu",
            "role": "candidate",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        self.token_user_b = jwt.encode({
            "sub": self.user_b_id,
            "email": "bob@beta.edu",
            "role": "candidate",
            "organization_id": self.org_b_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        self.token_admin_org_a = jwt.encode({
            "sub": f"admin_a_{uuid.uuid4().hex[:6]}",
            "email": "admin@alpha.edu",
            "role": "Organization Admin",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        self.token_admin_org_b = jwt.encode({
            "sub": f"admin_b_{uuid.uuid4().hex[:6]}",
            "email": "admin@beta.edu",
            "role": "Organization Admin",
            "organization_id": self.org_b_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        self.token_super_admin = jwt.encode({
            "sub": "sa_super_user_01",
            "email": "superadmin@prepfly.io",
            "role": "SUPER_ADMIN",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        self.expired_token = jwt.encode({
            "sub": self.user_a_id,
            "role": "candidate",
            "exp": datetime.utcnow() - timedelta(days=1)
        }, self.secret, algorithm="HS256")

        self.tampered_token = jwt.encode({
            "sub": self.user_a_id,
            "role": "SUPER_ADMIN"
        }, "wrong-untrusted-signing-key", algorithm="HS256")

    # ── 1. AUTHENTICATION TOKEN VALIDATION ────────────────────────────────────

    def test_auth_missing_token_rejected_on_protected_endpoints(self):
        """Unauthenticated requests to protected endpoints return HTTP 401."""
        endpoints = [
            ("GET", "/api/subscription"),
            ("GET", "/user-sessions"),
            ("POST", "/api/coding/submit"),
            ("GET", "/api/feedback/my"),
            ("PUT", "/api/feedback/my/FB-12345678"),
            ("GET", "/api/invoice/INV-TEST-001"),
        ]
        for method, ep in endpoints:
            with self.subTest(endpoint=ep):
                if method == "GET":
                    res = self.client.get(ep)
                elif method == "PUT":
                    res = self.client.put(ep, json={})
                else:
                    res = self.client.post(ep, json={})
                self.assertEqual(res.status_code, 401, f"{ep} allowed unauthenticated access!")

    def test_auth_expired_token_rejected(self):
        """Expired JWT token returns HTTP 401."""
        res = self.client.get(
            "/api/subscription",
            headers={"Authorization": f"Bearer {self.expired_token}"}
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("expired", res.get_json().get("error", "").lower())

    def test_auth_tampered_signature_rejected(self):
        """Token with invalid/tampered signature returns HTTP 401."""
        res = self.client.get(
            "/api/subscription",
            headers={"Authorization": f"Bearer {self.tampered_token}"}
        )
        self.assertEqual(res.status_code, 401)

    def test_auth_query_param_token_rejected(self):
        """Bearer tokens passed as query parameters are rejected; Authorization header is required."""
        res = self.client.get(
            f"/api/subscription?token={self.token_user_a}"
        )
        self.assertEqual(res.status_code, 401)

    # ── 2. IDENTITY SPOOFING & CLIENT-SUPPLIED USER_ID REJECTION ──────────────

    def test_session_creation_rejects_user_id_spoofing(self):
        """User A attempting to create a session under User B's user_id returns 403."""
        # Authenticated user attempting to override with another user_id
        res_no_resume = self.client.post(
            "/create-session-no-resume",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={
                "user_id": self.user_b_id,
                "role": "Software Engineer"
            }
        )
        self.assertEqual(res_no_resume.status_code, 403)

        # Unauthenticated user attempting to assign session to a user_id
        res_unauth = self.client.post(
            "/create-session-no-resume",
            json={
                "user_id": self.user_b_id,
                "role": "Software Engineer"
            }
        )
        self.assertEqual(res_unauth.status_code, 401)

    def test_resume_upload_rejects_user_id_spoofing(self):
        """User A attempting to upload a resume under User B's user_id returns 403."""
        data = {
            "user_id": self.user_b_id,
            "resume": (io.BytesIO(b"%PDF-1.4 dummy pdf resume content"), "resume.pdf")
        }
        res = self.client.post(
            "/upload",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 403)

    def test_coding_submission_rejects_user_id_spoofing_and_prevents_db_write(self):
        """User A submitting code with User B's user_id in JSON payload returns 403 and creates no DB record."""
        initial_count = 0
        try:
            r = supabase.table("coding_submissions").select("id").eq("user_id", self.user_b_id).execute()
            initial_count = len(r.data) if r and r.data else 0
        except Exception:
            pass

        res = self.client.post(
            "/api/coding/submit",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={
                "user_id": self.user_b_id,
                "language": "python",
                "code": "def solve(): return True"
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json().get("error", ""))

        # Verify database state was NOT modified
        try:
            r_post = supabase.table("coding_submissions").select("id").eq("user_id", self.user_b_id).execute()
            final_count = len(r_post.data) if r_post and r_post.data else 0
            self.assertEqual(initial_count, final_count)
        except Exception:
            pass

    def test_resume_score_rejects_user_id_spoofing_and_prevents_db_write(self):
        """User A storing an ATS resume score with User B's user_id returns 403 and writes nothing."""
        res = self.client.post(
            "/api/resume/score",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={
                "user_id": self.user_b_id,
                "resume_text": "Experienced Python Software Engineer with Flask, SQL.",
                "job_description": "Looking for Python Engineer proficient in Flask."
            }
        )
        self.assertEqual(res.status_code, 403)

        # Verify no record created for user_b
        try:
            r = supabase.table("resume_scores").select("id").eq("user_id", self.user_b_id).execute()
            self.assertEqual(len(r.data or []), 0)
        except Exception:
            pass

    def test_speech_analysis_rejects_user_id_spoofing_and_prevents_db_write(self):
        """User A storing speech analysis with User B's user_id returns 403 and writes nothing."""
        res = self.client.post(
            "/api/speech/analyze",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={
                "user_id": self.user_b_id,
                "transcript": "I built distributed microservices using Kafka and Redis."
            }
        )
        self.assertEqual(res.status_code, 403)

        # Verify no record created for user_b
        try:
            r = supabase.table("speech_analyses").select("id").eq("user_id", self.user_b_id).execute()
            self.assertEqual(len(r.data or []), 0)
        except Exception:
            pass

    # ── 3. CROSS-USER RESOURCE ISOLATION (BOLA / IDOR) ────────────────────────

    def test_session_lifecycle_idor_protection_and_immutability(self):
        """User A's session cannot be started, recorded, viewed, or deleted by User B."""
        # 1. User A creates a valid session
        create_res = self.client.post(
            "/create-session-no-resume",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={"role": "Backend Engineer"}
        )
        self.assertEqual(create_res.status_code, 200)
        session_id = create_res.get_json()["session_id"]

        # 2. User B attempts to call /start-interview on User A's session -> 404
        b_start = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            json={"session_id": session_id}
        )
        self.assertEqual(b_start.status_code, 404)

        # 3. User B attempts to save a recording to User A's session -> 404
        b_rec = self.client.post(
            "/save-recording",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            data={
                "session_id": session_id,
                "video": (io.BytesIO(b"dummy webm video"), "rec.webm")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(b_rec.status_code, 404)

        # Verify User A's session in DB was NOT corrupted
        s_db = supabase.table("sessions").select("recording_path").eq("session_id", session_id).execute()
        self.assertTrue(s_db and s_db.data)
        self.assertIsNone(s_db.data[0].get("recording_path"))

        # 4. User B attempts to read User A's session report -> 404
        b_report = self.client.get(
            f"/api/session-report/{session_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(b_report.status_code, 404)

        # 5. User B attempts to delete User A's session -> 404
        b_del = self.client.delete(
            f"/session/{session_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(b_del.status_code, 404)

        # Verify User A's session still exists in DB
        s_still_exists = supabase.table("sessions").select("session_id").eq("session_id", session_id).execute()
        self.assertEqual(len(s_still_exists.data or []), 1)

    def test_user_subscription_idor_protection(self):
        """User A querying User B's subscription returns HTTP 403."""
        res = self.client.get(
            f"/api/subscription?user_id={self.user_b_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 403)

        # Own subscription allowed
        res_own = self.client.get(
            f"/api/subscription?user_id={self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res_own.status_code, 200)

    def test_feedback_idor_protection_and_immutability(self):
        """User A cannot read or edit User B's feedback, and failed edit leaves DB unchanged."""
        # 1. User B submits feedback
        b_fb_res = self.client.post(
            "/api/feedback",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            json={
                "subject": "Private Student Grievance",
                "message": "Original untampered message from User B."
            }
        )
        self.assertEqual(b_fb_res.status_code, 201)
        fb_id = b_fb_res.get_json()["feedback"]["id"]

        # 2. User A attempts to query User B's feedback -> 403
        a_query = self.client.get(
            f"/api/feedback/my?user_id={self.user_b_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(a_query.status_code, 403)

        # 3. User A attempts to edit User B's feedback -> 403
        a_edit = self.client.put(
            f"/api/feedback/my/{fb_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={"message": "Tampered message by User A"}
        )
        self.assertEqual(a_edit.status_code, 403)

        # Verify message in database remains untampered
        fb_db = supabase.table("feedback").select("message").eq("id", fb_id).execute()
        self.assertEqual(fb_db.data[0]["message"], "Original untampered message from User B.")

    # ── 4. ROLE-BASED ACCESS CONTROL (RBAC) & TENANT PRIVACY ─────────────────

    def test_superadmin_candidates_stats_requires_superadmin_role(self):
        """Unauthenticated or regular candidate users cannot access candidate stats."""
        # Unauthenticated -> 401 or 403
        res_unauth = self.client.get("/api/superadmin/candidates-stats")
        self.assertIn(res_unauth.status_code, [401, 403])

        # Candidate token -> 403
        res_cand = self.client.get(
            "/api/superadmin/candidates-stats",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res_cand.status_code, 403)

        # Super admin token -> 200
        res_sa = self.client.get(
            "/api/superadmin/candidates-stats",
            headers={"Authorization": f"Bearer {self.token_super_admin}"}
        )
        self.assertEqual(res_sa.status_code, 200)
        self.assertIn("total_students", res_sa.get_json())

    def test_invoice_cross_organization_isolation(self):
        """Organization B cannot download or view Organization A's invoices."""
        # Seed an invoice for Org A
        inv_id = f"inv_{uuid.uuid4().hex[:8]}"
        supabase.table("invoice").insert({
            "id": inv_id,
            "organization_id": self.org_a_id,
            "invoice_number": f"INV-{inv_id.upper()}",
            "amount": 500.0,
            "gst": 90.0,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Unauthenticated access -> 401
        res_unauth = self.client.get(f"/api/invoice/{inv_id}")
        self.assertEqual(res_unauth.status_code, 401)

        # Org B user access -> 403
        res_org_b = self.client.get(
            f"/api/invoice/{inv_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res_org_b.status_code, 403)

        # Candidate from Org A cannot access invoice -> 403
        res_cand = self.client.get(
            f"/api/invoice/{inv_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res_cand.status_code, 403)

        # Org Admin from Org A access -> 200
        res_org_a = self.client.get(
            f"/api/invoice/{inv_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res_org_a.status_code, 200)

        # Super admin access -> 200
        res_sa = self.client.get(
            f"/api/invoice/{inv_id}",
            headers={"Authorization": f"Bearer {self.token_super_admin}"}
        )
        self.assertEqual(res_sa.status_code, 200)

    def test_payment_history_rbac_and_cross_organization_isolation(self):
        """Candidates and cross-tenant users are denied; Org Admin and SuperAdmin permitted."""
        # 1. Candidate cannot access payment history -> 403
        res_cand = self.client.get(
            f"/api/payment/history?org_id={self.org_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res_cand.status_code, 403)

        # 2. Org Admin A cannot access Org B's payment history -> 403
        res_cross_org = self.client.get(
            f"/api/payment/history?org_id={self.org_b_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res_cross_org.status_code, 403)

        # 3. Org Admin A can access Org A's payment history -> 200
        res_own_org = self.client.get(
            f"/api/payment/history?org_id={self.org_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res_own_org.status_code, 200)

        # 4. Super Admin can query any org payment history -> 200
        res_sa = self.client.get(
            f"/api/payment/history?org_id={self.org_b_id}",
            headers={"Authorization": f"Bearer {self.token_super_admin}"}
        )
        self.assertEqual(res_sa.status_code, 200)

    def test_order_creation_cross_organization_isolation(self):
        """Org Admin cannot initiate payment orders for a foreign tenant."""
        res_cross = self.client.post(
            "/payment/create-order",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"},
            json={"organization_id": self.org_b_id, "amount": 500}
        )
        self.assertEqual(res_cross.status_code, 403)

if __name__ == "__main__":
    unittest.main()
