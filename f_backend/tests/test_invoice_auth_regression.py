"""
Invoice Download Authentication & Authorization Security Regression Tests.

Verifies:
1. Missing token returns 401.
2. Invalid token signature returns 401.
3. Expired token returns 401.
4. Token passed via query string (?token=...) is rejected with 401 (reusable token exposure prevention).
5. Authorized Organization Administrator can download own invoice (HTML & PDF blob).
6. Candidate attempting to download an invoice is rejected with 403 Forbidden.
7. Administrator from Organization A attempting to download Organization B's invoice is rejected with 403.
8. Super Administrator can download any organization's invoice.
9. Nonexistent invoice returns 404 Not Found.
10. Failed authorization attempts leave invoice data completely unchanged in the database.
"""

import unittest
import os
import sys
import uuid
import jwt
from datetime import datetime, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app import app, _get_jwt_secret, supabase
from services.invoice_service import generate_invoice

class TestInvoiceAuthRegression(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        self.secret = _get_jwt_secret()

        # Generate isolated tenant and user IDs for this test run
        self.org_a_id = f"org_test_a_{uuid.uuid4().hex[:6]}"
        self.org_b_id = f"org_test_b_{uuid.uuid4().hex[:6]}"
        self.admin_a_id = f"usr_admin_a_{uuid.uuid4().hex[:6]}"
        self.admin_b_id = f"usr_admin_b_{uuid.uuid4().hex[:6]}"
        self.candidate_id = f"usr_cand_{uuid.uuid4().hex[:6]}"

        # Seed test invoice for Organization A
        self.inv_a = generate_invoice(
            org_id=self.org_a_id,
            payment_id=f"pay_seed_{uuid.uuid4().hex[:8]}",
            amount=500.0
        )
        self.inv_a_id = self.inv_a["id"]
        self.inv_a_number = self.inv_a["invoice_number"]

        # 1. Valid Org Admin A token
        self.token_admin_org_a = jwt.encode({
            "sub": self.admin_a_id,
            "email": "admin@orga.edu",
            "role": "Organization Admin",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        # 2. Valid Org Admin B token (foreign tenant)
        self.token_admin_org_b = jwt.encode({
            "sub": self.admin_b_id,
            "email": "admin@orgb.edu",
            "role": "Organization Admin",
            "organization_id": self.org_b_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        # 3. Valid Candidate token (same organization A, but candidate role)
        self.token_candidate_org_a = jwt.encode({
            "sub": self.candidate_id,
            "email": "student@orga.edu",
            "role": "candidate",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        # 4. Super Admin token
        self.token_super_admin = jwt.encode({
            "sub": "sa_system_admin",
            "email": "superadmin@prepfly.io",
            "role": "SUPER_ADMIN",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, self.secret, algorithm="HS256")

        # 5. Expired token
        self.token_expired = jwt.encode({
            "sub": self.admin_a_id,
            "role": "Organization Admin",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() - timedelta(days=1)
        }, self.secret, algorithm="HS256")

        # 6. Tampered / invalid signature token
        self.token_invalid_signature = jwt.encode({
            "sub": self.admin_a_id,
            "role": "Organization Admin",
            "organization_id": self.org_a_id,
            "exp": datetime.utcnow() + timedelta(days=1)
        }, "untrusted_wrong_signing_key_999", algorithm="HS256")

    # ── TESTS ─────────────────────────────────────────────────────────────────

    def test_missing_token_rejected_with_401(self):
        """A request without an Authorization header returns HTTP 401."""
        res = self.client.get(f"/api/invoice/{self.inv_a_id}")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertIn("Authentication required", data.get("error", ""))

    def test_invalid_token_signature_rejected_with_401(self):
        """A token signed with an invalid or untrusted key returns HTTP 401."""
        res = self.client.get(
            f"/api/invoice/{self.inv_a_id}",
            headers={"Authorization": f"Bearer {self.token_invalid_signature}"}
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("error", data)

    def test_expired_token_rejected_with_401(self):
        """An expired token returns HTTP 401."""
        res = self.client.get(
            f"/api/invoice/{self.inv_a_id}",
            headers={"Authorization": f"Bearer {self.token_expired}"}
        )
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("error", data)

    def test_query_string_token_rejected_with_401(self):
        """Passing the access token in a URL query parameter (?token=...) is rejected."""
        res = self.client.get(f"/api/invoice/{self.inv_a_id}?token={self.token_admin_org_a}")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIn("Authentication required", data.get("error", ""))

    def test_authorized_org_admin_downloads_invoice_pdf(self):
        """Authorized Organization Administrator downloads official PDF blob with valid Authorization header."""
        res = self.client.get(
            f"/api/invoice/{self.inv_a_id}?format=pdf",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "application/pdf")
        # PDF binary starts with %PDF-
        self.assertTrue(res.data.startswith(b"%PDF-"))
        self.assertIn(f'attachment; filename="Invoice-{self.inv_a_number}.pdf"', res.headers.get("Content-Disposition", ""))

    def test_authorized_org_admin_downloads_invoice_html(self):
        """Authorized Organization Administrator can view standard invoice HTML with Authorization header."""
        res = self.client.get(
            f"/api/invoice/{self.inv_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.content_type)
        html = res.get_data(as_text=True)
        self.assertIn("PrepFly Enterprise", html)
        self.assertIn(self.inv_a_number, html)
        self.assertIn("500", html)

    def test_candidate_attempting_to_download_invoice_rejected_with_403(self):
        """A candidate user attempting to download an invoice is rejected with HTTP 403 Forbidden."""
        res = self.client.get(
            f"/api/invoice/{self.inv_a_id}",
            headers={"Authorization": f"Bearer {self.token_candidate_org_a}"}
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn("Forbidden", data.get("error", ""))
        self.assertNotIn("PrepFly Enterprise", str(res.data))

    def test_cross_org_admin_attempting_to_download_invoice_rejected_with_403(self):
        """Administrator from Organization B cannot download Organization A's invoice."""
        res = self.client.get(
            f"/api/invoice/{self.inv_a_id}",
            headers={"Authorization": f"Bearer {self.token_admin_org_b}"}
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn("Forbidden", data.get("error", ""))
        # Verify invoice body is NOT leaked
        self.assertNotIn("PrepFly Enterprise", str(res.data))
        self.assertNotIn(self.inv_a_number, str(res.data))

    def test_super_admin_can_download_any_org_invoice(self):
        """Super Administrator can download invoices belonging to any organization."""
        res = self.client.get(
            f"/api/invoice/{self.inv_a_id}?format=pdf",
            headers={"Authorization": f"Bearer {self.token_super_admin}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "application/pdf")
        self.assertTrue(res.data.startswith(b"%PDF-"))

    def test_nonexistent_invoice_returns_404(self):
        """Querying a non-existent invoice returns HTTP 404 Not Found."""
        res = self.client.get(
            "/api/invoice/inv_nonexistent_99999",
            headers={"Authorization": f"Bearer {self.token_admin_org_a}"}
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIn("Invoice not found", data.get("error", ""))

    def test_failed_authorization_leaves_invoice_data_unchanged(self):
        """Failed authorization attempts do not modify or corrupt the invoice in the database."""
        # 1. Fetch baseline record
        res_pre = supabase.table("invoice").select("*").eq("id", self.inv_a_id).execute()
        self.assertTrue(res_pre and res_pre.data)
        baseline = dict(res_pre.data[0])

        # 2. Trigger various unauthorized requests
        self.client.get(f"/api/invoice/{self.inv_a_id}")  # Missing token
        self.client.get(f"/api/invoice/{self.inv_a_id}", headers={"Authorization": f"Bearer {self.token_expired}"})
        self.client.get(f"/api/invoice/{self.inv_a_id}", headers={"Authorization": f"Bearer {self.token_invalid_signature}"})
        self.client.get(f"/api/invoice/{self.inv_a_id}", headers={"Authorization": f"Bearer {self.token_candidate_org_a}"})
        self.client.get(f"/api/invoice/{self.inv_a_id}", headers={"Authorization": f"Bearer {self.token_admin_org_b}"})

        # 3. Fetch record after attacks
        res_post = supabase.table("invoice").select("*").eq("id", self.inv_a_id).execute()
        self.assertTrue(res_post and res_post.data)
        post = dict(res_post.data[0])

        # 4. Assert full data immutability
        self.assertEqual(baseline["id"], post["id"])
        self.assertEqual(baseline["organization_id"], post["organization_id"])
        self.assertEqual(baseline["amount"], post["amount"])
        self.assertEqual(baseline["gst"], post["gst"])
        self.assertEqual(baseline["payment_id"], post["payment_id"])
        self.assertEqual(baseline["invoice_number"], post["invoice_number"])

if __name__ == "__main__":
    unittest.main()
