"""
Comprehensive Object-Level Authorization (BOLA/IDOR) & Tenant Isolation Test Suite.
Validates multi-user and multi-tenant isolation across 5 distinct identities:
1. User A (Candidate, Org Alpha)
2. User B (Candidate, Org Beta)
3. Org Admin A (Organization Admin, Org Alpha)
4. Org Admin B (Organization Admin, Org Beta)
5. Super Admin (Platform Super Administrator)

Verifies:
- Reading, updating, deleting, downloading another user's or organization's resources
- Spoofing user_id, organization_id, session_id, and resource_id in bodies/params
- Ordinary user (Candidate) and Org Admin privilege escalation attempts
- Database & file system state immutability on rejected requests
- Legitimate authorized workflows for each role
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

class TestDataIsolationComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.client.testing = True
        cls.secret = _get_jwt_secret()

        # Deterministic IDs
        cls.user_a_id = f"usr_a_{uuid.uuid4().hex[:8]}"
        cls.user_b_id = f"usr_b_{uuid.uuid4().hex[:8]}"
        cls.org_a_id = f"org_a_{uuid.uuid4().hex[:6]}"
        cls.org_b_id = f"org_b_{uuid.uuid4().hex[:6]}"
        cls.admin_a_id = f"adm_a_{uuid.uuid4().hex[:6]}"
        cls.admin_b_id = f"adm_b_{uuid.uuid4().hex[:6]}"
        cls.super_admin_id = f"sa_{uuid.uuid4().hex[:6]}"

        # 5 Isolated Identities
        cls.token_user_a = jwt.encode({
            "sub": cls.user_a_id,
            "email": "alice@alpha.edu",
            "role": "candidate",
            "organization_id": cls.org_a_id,
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, cls.secret, algorithm="HS256")

        cls.token_user_b = jwt.encode({
            "sub": cls.user_b_id,
            "email": "bob@beta.edu",
            "role": "candidate",
            "organization_id": cls.org_b_id,
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, cls.secret, algorithm="HS256")

        cls.token_admin_org_a = jwt.encode({
            "sub": cls.admin_a_id,
            "email": "admin@alpha.edu",
            "role": "Organization Admin",
            "organization_id": cls.org_a_id,
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, cls.secret, algorithm="HS256")

        cls.token_admin_org_b = jwt.encode({
            "sub": cls.admin_b_id,
            "email": "admin@beta.edu",
            "role": "Organization Admin",
            "organization_id": cls.org_b_id,
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, cls.secret, algorithm="HS256")

        cls.token_super_admin = jwt.encode({
            "sub": cls.super_admin_id,
            "email": "superadmin@prepfly.io",
            "role": "SUPER_ADMIN",
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, cls.secret, algorithm="HS256")

        # Seed sample data for testing
        # 1. User A Session
        cls.session_a_id = str(uuid.uuid4())
        supabase.table("sessions").insert({
            "session_id": cls.session_a_id,
            "user_id": cls.user_a_id,
            "resume_text": "Alice's Private Resume",
            "question_index": 0,
            "active": 1,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # 2. User A Feedback
        cls.feedback_a_id = f"fb_{uuid.uuid4().hex[:8]}"
        supabase.table("feedback").insert({
            "id": cls.feedback_a_id,
            "submitted_by": cls.user_a_id,
            "submitted_by_role": "candidate",
            "organization_id": cls.org_a_id,
            "subject": "Private Student Feedback Alice",
            "message": "Original feedback text by Alice",
            "status": "New",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # 3. Org A Invoice
        cls.invoice_a_id = f"inv_{uuid.uuid4().hex[:8]}"
        supabase.table("invoice").insert({
            "id": cls.invoice_a_id,
            "organization_id": cls.org_a_id,
            "invoice_number": f"INV-{cls.invoice_a_id.upper()}",
            "amount": 1500.0,
            "gst": 270.0,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # 4. Org A Interview Dossier
        cls.interview_a_id = f"intv_{uuid.uuid4().hex[:8]}"
        supabase.table("admin_interviews").insert({
            "id": cls.interview_a_id,
            "organization_id": cls.org_a_id,
            "title": "Software Engineering Campus Placement Round",
            "status": "Completed",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # 5. Org A Student Dossier
        cls.student_a_id = f"std_{uuid.uuid4().hex[:8]}"
        supabase.table("students").insert({
            "id": cls.student_a_id,
            "organization_id": cls.org_a_id,
            "name": "Alice Candidate",
            "email": "alice@alpha.edu",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # 6. Org A Coding Test
        cls.coding_test_a_id = f"test_{uuid.uuid4().hex[:8]}"
        supabase.table("admin_coding").insert({
            "id": cls.coding_test_a_id,
            "organization_id": cls.org_a_id,
            "title": "Algorithms & Data Structures Assessment",
            "duration": 60,
            "language": "Python",
            "status": "Active",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

    # ── CATEGORY 1: RESUME & ATS SCORING ISOLATION ────────────────────────────

    def test_resume_score_spoofing_user_id_rejected(self):
        """User A cannot score a resume on behalf of User B."""
        res = self.client.post(
            "/api/resume/score",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={
                "user_id": self.user_b_id,
                "resume_text": "Attacker trying to write resume score for Bob",
                "job_description": "Data Scientist"
            }
        )
        self.assertEqual(res.status_code, 403)
        # Verify no database entry was created for user B
        r = supabase.table("resume_scores").select("id").eq("user_id", self.user_b_id).execute()
        self.assertEqual(len(r.data or []), 0)

    def test_user_stats_cross_user_reading_rejected(self):
        """User B cannot read User A's statistics."""
        res = self.client.get(
            f"/api/user-stats/{self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_user_stats_own_reading_permitted(self):
        """User A can read their own statistics."""
        res = self.client.get(
            f"/api/user-stats/{self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 200)

    # ── CATEGORY 2: INTERVIEW SESSIONS & LIFECYCLE ISOLATION ─────────────────

    def test_session_read_by_unauthorized_user_rejected(self):
        """User B cannot read User A's interview session details."""
        res = self.client.get(
            f"/get-session?session_id={self.session_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 404)

    def test_session_start_by_unauthorized_user_rejected(self):
        """User B cannot start User A's interview session."""
        res = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            json={"session_id": self.session_a_id}
        )
        self.assertEqual(res.status_code, 404)

    def test_session_end_by_unauthorized_user_rejected(self):
        """User B cannot end User A's interview session."""
        res = self.client.post(
            "/end-interview",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            json={"session_id": self.session_a_id}
        )
        self.assertEqual(res.status_code, 404)

    def test_session_delete_by_unauthorized_user_rejected_and_db_persisted(self):
        """User B cannot delete User A's session; session remains in DB."""
        res = self.client.delete(
            f"/session/{self.session_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 404)
        # Verify DB still contains User A's session
        check = supabase.table("sessions").select("session_id").eq("session_id", self.session_a_id).execute()
        self.assertEqual(len(check.data or []), 1)

    def test_session_bulk_delete_ignores_unowned_sessions(self):
        """User B bulk-deleting User A's session ignores it without deleting."""
        res = self.client.post(
            "/session/bulk-delete",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            json={"session_ids": [self.session_a_id]}
        )
        self.assertEqual(res.status_code, 200)
        # Result should show 0 sessions deleted
        self.assertIn("0 sessions deleted", res.get_json().get("message", ""))
        # Verify User A's session still exists
        check = supabase.table("sessions").select("session_id").eq("session_id", self.session_a_id).execute()
        self.assertEqual(len(check.data or []), 1)

    def test_session_lifecycle_by_owner_permitted(self):
        """User A can read and interact with their own session."""
        res = self.client.get(
            f"/get-session?session_id={self.session_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 200)

    # ── CATEGORY 3: INTERVIEW RECORDINGS & GENERATED REPORTS ─────────────────

    def test_recording_file_download_by_unauthorized_user_rejected(self):
        """User B cannot download User A's interview recording file."""
        res = self.client.get(
            f"/recording/{self.session_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 404)

    def test_session_report_read_by_unauthorized_user_rejected(self):
        """User B cannot view User A's generated interview report."""
        res = self.client.get(
            f"/api/session-report/{self.session_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 404)

    def test_save_recording_cross_user_injection_rejected(self):
        """User B cannot inject video recording data into User A's session."""
        res = self.client.post(
            "/save-recording",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            data={
                "session_id": self.session_a_id,
                "video": (io.BytesIO(b"fake video bytes"), "fake.webm")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 404)
        # Verify recording_path was not updated
        s = supabase.table("sessions").select("recording_path").eq("session_id", self.session_a_id).execute()
        self.assertIsNone(s.data[0].get("recording_path"))

    def test_interview_pdf_cross_tenant_access_rejected(self):
        """Org Admin B cannot download Org Admin A's interview dossier PDF."""
        res = self.client.get(
            f"/api/admin/interview-pdf/{self.interview_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json().get("error", ""))

    def test_interview_pdf_same_tenant_admin_permitted(self):
        """Org Admin A can download their own organization's interview dossier PDF."""
        res = self.client.get(
            f"/api/admin/interview-pdf/{self.interview_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        # Should generate PDF or return 200 attachment
        self.assertEqual(res.status_code, 200)

    def test_interview_pdf_super_admin_permitted(self):
        """Super Admin can access any organization's interview dossier PDF."""
        res = self.client.get(
            f"/api/admin/interview-pdf/{self.interview_a_id}",
            headers={"Authorization": f"Bearer {self.token_super_admin}"}
        )
        self.assertEqual(res.status_code, 200)

    def test_student_dossier_pdf_cross_tenant_access_rejected(self):
        """Org Admin B cannot download Org Admin A's student dossier PDF."""
        res = self.client.get(
            f"/api/admin/reports/student/{self.student_a_id}/pdf",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_student_dossier_pdf_same_tenant_admin_permitted(self):
        """Org Admin A can download their own student's dossier PDF."""
        res = self.client.get(
            f"/api/admin/reports/student/{self.student_a_id}/pdf",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res.status_code, 200)

    # ── CATEGORY 4: CODING SUBMISSIONS & CODING TESTS ────────────────────────

    def test_coding_submission_spoofing_user_id_rejected(self):
        """User A submitting code with user_id = User B is rejected with 403."""
        res = self.client.post(
            "/api/coding/submit",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={
                "user_id": self.user_b_id,
                "problem_id": "two-sum",
                "language": "python",
                "code": "print('exploit')"
            }
        )
        self.assertEqual(res.status_code, 403)
        # Verify no database entry was created for user B
        r = supabase.table("coding_submissions").select("id").eq("user_id", self.user_b_id).execute()
        self.assertEqual(len(r.data or []), 0)

    def test_coding_leaderboard_cross_tenant_access_rejected(self):
        """Org Admin B cannot view Org A's coding assessment leaderboard."""
        res = self.client.get(
            f"/api/admin/coding-test/{self.coding_test_a_id}/leaderboard",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_coding_export_csv_cross_tenant_access_rejected(self):
        """Org Admin B cannot export Org A's coding assessment results."""
        res = self.client.get(
            f"/api/admin/coding-test/{self.coding_test_a_id}/export-csv",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_coding_leaderboard_same_tenant_admin_permitted(self):
        """Org Admin A can view Org A's coding leaderboard."""
        res = self.client.get(
            f"/api/admin/coding-test/{self.coding_test_a_id}/leaderboard",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res.status_code, 200)

    # ── CATEGORY 5: FEEDBACK SUBMISSIONS & UPDATES ────────────────────────────

    def test_feedback_read_cross_user_rejected(self):
        """User B querying User A's feedback returns 403."""
        res = self.client.get(
            f"/api/feedback/my?user_id={self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_feedback_update_cross_user_rejected_and_db_intact(self):
        """User B cannot update Alice's feedback; database remains unchanged."""
        res = self.client.put(
            f"/api/feedback/my/{self.feedback_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            json={"message": "Hacked message by Bob"}
        )
        self.assertEqual(res.status_code, 403)
        # Check database still contains original message
        fb = supabase.table("feedback").select("message").eq("id", self.feedback_a_id).execute()
        self.assertEqual(fb.data[0]["message"], "Original feedback text by Alice")

    def test_feedback_update_by_owner_permitted(self):
        """Alice can update her own feedback."""
        fb_owner_id = f"fb_own_{uuid.uuid4().hex[:8]}"
        supabase.table("feedback").insert({
            "id": fb_owner_id,
            "submitted_by": self.user_a_id,
            "submitted_by_role": "candidate",
            "organization_id": self.org_a_id,
            "subject": "Alice's Feedback for Edit",
            "message": "Initial text before edit",
            "status": "New",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        res = self.client.put(
            f"/api/feedback/my/{fb_owner_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={"message": "Updated legitimate feedback by Alice"}
        )
        self.assertEqual(res.status_code, 200)
        # Verify in DB
        fb = supabase.table("feedback").select("message").eq("id", fb_owner_id).execute()
        self.assertEqual(fb.data[0]["message"], "Updated legitimate feedback by Alice")

    # ── CATEGORY 6: SUBSCRIPTION DETAILS ISOLATION ────────────────────────────

    def test_subscription_read_cross_user_rejected(self):
        """User A querying User B's subscription returns 403."""
        res = self.client.get(
            f"/api/subscription?user_id={self.user_b_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_subscription_read_own_permitted(self):
        """User A querying their own subscription returns 200."""
        res = self.client.get(
            f"/api/subscription?user_id={self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 200)

    # ── CATEGORY 7: PAYMENT HISTORY & INVOICES ISOLATION ─────────────────────

    def test_invoice_download_cross_tenant_rejected(self):
        """Org Admin B downloading Org A's invoice returns 403."""
        res = self.client.get(
            f"/api/invoice/{self.invoice_a_id}?format=pdf",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_invoice_download_candidate_rejected(self):
        """Candidate A attempting to access Org A's invoice returns 403."""
        res = self.client.get(
            f"/api/invoice/{self.invoice_a_id}?format=pdf",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_invoice_download_same_tenant_admin_permitted(self):
        """Org Admin A can download Org A's invoice."""
        res = self.client.get(
            f"/api/invoice/{self.invoice_a_id}?format=pdf",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/pdf")

    def test_invoice_download_super_admin_permitted(self):
        """Super Admin can download any organization's invoice."""
        res = self.client.get(
            f"/api/invoice/{self.invoice_a_id}?format=pdf",
            headers={"Authorization": f"Bearer {self.token_super_admin}"}
        )
        self.assertEqual(res.status_code, 200)

    def test_payment_history_cross_tenant_rejected(self):
        """Org Admin B attempting to read Org A's payment history returns 403."""
        res = self.client.get(
            f"/api/payment/history?org_id={self.org_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_payment_history_candidate_rejected(self):
        """Candidate A attempting to read payment history returns 403."""
        res = self.client.get(
            f"/api/payment/history?org_id={self.org_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_payment_order_cross_tenant_spoofing_rejected(self):
        """Org Admin A creating an order for Org B returns 403."""
        res = self.client.post(
            "/payment/create-order",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"},
            json={"organization_id": self.org_b_id, "amount": 1000}
        )
        self.assertEqual(res.status_code, 403)

    # ── CATEGORY 8: ADMINISTRATIVE & SUPER-ADMINISTRATIVE ISOLATION ──────────

    def test_admin_dashboard_candidate_rejected(self):
        """Candidate cannot access Org Admin dashboard."""
        res = self.client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_analytics_candidate_rejected(self):
        """Candidate cannot access Org Admin analytics."""
        res = self.client.get(
            "/api/admin/analytics",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_superadmin_dashboard_candidate_rejected(self):
        """Candidate cannot access SuperAdmin dashboard."""
        res = self.client.get(
            "/api/superadmin/dashboard",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_superadmin_dashboard_org_admin_rejected(self):
        """Org Admin cannot access SuperAdmin dashboard."""
        res = self.client.get(
            "/api/superadmin/dashboard",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_superadmin_dashboard_super_admin_permitted(self):
        """Super Admin can access SuperAdmin dashboard."""
        res = self.client.get(
            "/api/superadmin/dashboard",
            headers={"Authorization": f"Bearer {self.token_super_admin}"}
        )
        self.assertEqual(res.status_code, 200)

    # ── CATEGORY 9: USER HISTORY & PROFILE COLLISION ISOLATION ───────────────

    def test_user_history_read_cross_user_rejected(self):
        """User B cannot read User A's history."""
        res = self.client.get(
            f"/api/history/{self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_user_history_delete_cross_user_rejected_and_db_persisted(self):
        """User B cannot clear User A's history; history remains in DB."""
        res = self.client.delete(
            f"/api/history/{self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 403)
        # Check sessions still exist for user A
        s = supabase.table("sessions").select("session_id").eq("user_id", self.user_a_id).execute()
        self.assertGreater(len(s.data or []), 0)

    def test_user_history_read_own_permitted(self):
        """User A can read their own history."""
        res = self.client.get(
            f"/api/history/{self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res.status_code, 200)

    def test_update_profile_email_collision_rejected(self):
        """User A updating email to an existing user's email returns 400."""
        # Seed an existing user
        existing_email = f"existing_{uuid.uuid4().hex[:6]}@domain.com"
        supabase.table("users").insert({
            "id": f"usr_exist_{uuid.uuid4().hex[:6]}",
            "email": existing_email,
            "name": "Existing Account",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        res = self.client.put(
            "/update-profile",
            headers={"Authorization": f"Bearer {self.token_user_a}"},
            json={"email": existing_email, "name": "Alice Colliding"}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Email already in use", res.get_json().get("error", ""))

    # ── CATEGORY 10: SUPPORT CONVERSATION OBJECT-LEVEL ISOLATION ─────────────

    def test_support_conversation_unauthenticated_rejected(self):
        """Unauthenticated caller cannot read support conversation or messages."""
        conv_id = f"conv_test_{uuid.uuid4().hex[:8]}"
        supabase.table("support_conversations").insert({
            "id": conv_id,
            "organization_id": self.org_a_id,
            "status": "Open",
            "priority": "Normal",
            "subject": "Confidential Technical Problem",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        res = self.client.get(f"/api/support/conversations/{conv_id}")
        self.assertEqual(res.status_code, 401)
        # Verify no messages or details leaked
        self.assertNotIn("messages", res.get_json())

    def test_support_conversation_read_cross_tenant_rejected_and_no_data_leaked(self):
        """Org Admin B cannot view Org A's support conversation or confidential messages."""
        conv_id = f"conv_priv_{uuid.uuid4().hex[:8]}"
        supabase.table("support_conversations").insert({
            "id": conv_id,
            "organization_id": self.org_a_id,
            "status": "Open",
            "priority": "High",
            "subject": "Confidential Dean Inquiry",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        # Seed confidential message
        supabase.table("support_messages").insert({
            "id": f"msg_priv_{uuid.uuid4().hex[:8]}",
            "conversation_id": conv_id,
            "sender_role": "Organization Admin",
            "sender_id": self.admin_a_id,
            "message": "Sensitive internal incident details for Alpha.",
            "is_read": 0,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        res = self.client.get(
            f"/api/support/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)
        # Verify no private messages or subject in response
        self.assertNotIn("messages", res.get_json())
        self.assertNotIn("Sensitive internal incident details", str(res.get_json()))

    def test_support_conversation_modify_cross_tenant_rejected_and_db_persisted(self):
        """Org Admin B cannot update status or priority of Org A's ticket; DB remains unchanged."""
        conv_id = f"conv_mod_{uuid.uuid4().hex[:8]}"
        supabase.table("support_conversations").insert({
            "id": conv_id,
            "organization_id": self.org_a_id,
            "status": "Open",
            "priority": "High",
            "subject": "Alpha System Ticket",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        res = self.client.put(
            f"/api/support/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"},
            json={"status": "Closed", "priority": "Low"}
        )
        self.assertEqual(res.status_code, 403)

        # Verify DB status remains untampered
        c = supabase.table("support_conversations").select("status, priority").eq("id", conv_id).execute()
        self.assertEqual(c.data[0]["status"], "Open")
        self.assertEqual(c.data[0]["priority"], "High")

    def test_support_message_post_cross_tenant_rejected_and_db_intact(self):
        """Org Admin B cannot inject messages into Org A's support ticket; 0 rows inserted."""
        conv_id = f"conv_post_{uuid.uuid4().hex[:8]}"
        supabase.table("support_conversations").insert({
            "id": conv_id,
            "organization_id": self.org_a_id,
            "status": "Open",
            "priority": "Normal",
            "subject": "Alpha Inquiry",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()

        initial_count = 0
        r_init = supabase.table("support_messages").select("id").eq("conversation_id", conv_id).execute()
        initial_count = len(r_init.data or [])

        res = self.client.post(
            f"/api/support/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"},
            json={"message": "Hacker message injected into Alpha ticket"}
        )
        self.assertEqual(res.status_code, 403)

        # Verify zero messages added to this conversation in DB
        r_post = supabase.table("support_messages").select("id").eq("conversation_id", conv_id).execute()
        self.assertEqual(len(r_post.data or []), initial_count)

    # ── CATEGORY 11: CAMPUS ANNOUNCEMENTS & NOTIFICATIONS TENANT ISOLATION ───

    def test_notifications_campus_announcement_tenant_spoofing_prevented(self):
        """Candidate B and unauthenticated callers cannot read Org A's private announcements via ?org_id spoofing."""
        ann_id = f"ann_priv_{uuid.uuid4().hex[:8]}"
        supabase.table("announcements").insert({
            "id": ann_id,
            "organization_id": self.org_a_id,
            "title": "Confidential Alpha Placement Schedule 2027",
            "message": "Private placement interview date for Alpha campus only.",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # 1. Unauthenticated request attempting ?org_id=<org_a>
        res_unauth = self.client.get(f"/api/notifications?org_id={self.org_a_id}")
        self.assertEqual(res_unauth.status_code, 200)
        notifs_unauth = res_unauth.get_json() or []
        titles_unauth = [n.get("title", "") for n in notifs_unauth]
        self.assertFalse(any("Confidential Alpha Placement" in t for t in titles_unauth))

        # 2. Candidate B (from Org B) attempting ?org_id=<org_a>
        res_cand_b = self.client.get(
            f"/api/notifications?org_id={self.org_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res_cand_b.status_code, 200)
        notifs_b = res_cand_b.get_json() or []
        titles_b = [n.get("title", "") for n in notifs_b]
        self.assertFalse(any("Confidential Alpha Placement" in t for t in titles_b))

        # 3. Candidate A (legitimate member of Org A) receives the announcement
        res_cand_a = self.client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        self.assertEqual(res_cand_a.status_code, 200)
        notifs_a = res_cand_a.get_json() or []
        titles_a = [n.get("title", "") for n in notifs_a]
        self.assertTrue(any("Confidential Alpha Placement" in t for t in titles_a))

    # ── CATEGORY 12: STUDENT ADMINISTRATION ISOLATION ────────────────────────

    def test_student_update_cross_tenant_rejected_and_db_persisted(self):
        """Org Admin B cannot update student belonging to Org A; student name in DB stays untampered."""
        res = self.client.put(
            f"/api/admin/student/{self.student_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"},
            json={"name": "Hacked Student Name", "department": "Malicious Dept"}
        )
        self.assertEqual(res.status_code, 403)

        # Verify DB student name is unchanged
        s = supabase.table("students").select("name, department").eq("id", self.student_a_id).execute()
        self.assertEqual(s.data[0]["name"], "Alice Candidate")

    def test_student_delete_cross_tenant_rejected_and_db_persisted(self):
        """Org Admin B cannot delete student belonging to Org A; student remains in DB."""
        res = self.client.delete(
            f"/api/admin/student/{self.student_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)

        # Verify student still exists in DB
        s = supabase.table("students").select("id").eq("id", self.student_a_id).execute()
        self.assertEqual(len(s.data or []), 1)

    # ── CATEGORY 13: REALTIME & WEBRTC SIGNALS ISOLATION ─────────────────────

    def test_webrtc_signals_cross_user_reading_rejected(self):
        """Candidate B cannot read WebRTC signals directed to Candidate A."""
        res = self.client.get(
            f"/api/webrtc/signals?user_id={self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 403)

    def test_coding_room_signals_cross_user_reading_rejected(self):
        """Candidate B cannot intercept coding room signals directed to Candidate A."""
        res = self.client.get(
            f"/api/coding/room/signals?user_id={self.user_a_id}",
            headers={"Authorization": f"Bearer {self.token_user_b}"}
        )
        self.assertEqual(res.status_code, 403)

    # ── CATEGORY 14: FRONTEND SECRETS LEAK AUDIT ─────────────────────────────

    def test_frontend_source_contains_no_supabase_service_role_secrets(self):
        """Automated code scanner verifying no backend service keys are bundled or present in frontend files."""
        frontend_dir = os.path.join(os.path.dirname(BACKEND_DIR), "f_frontend")
        prohibited_terms = [
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_SERVICE_KEY",
            "RAZORPAY_KEY_SECRET",
            "JWT_SECRET_KEY"
        ]
        scanned_count = 0
        for root, _, files in os.walk(frontend_dir):
            if "node_modules" in root or "dist" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith((".js", ".jsx", ".ts", ".tsx", ".env", ".json")):
                    filepath = os.path.join(root, f)
                    scanned_count += 1
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                        for term in prohibited_terms:
                            self.assertNotIn(term, content, f"Sensitive secret {term} exposed in frontend file: {filepath}")
        self.assertGreater(scanned_count, 20)

if __name__ == "__main__":
    unittest.main()

