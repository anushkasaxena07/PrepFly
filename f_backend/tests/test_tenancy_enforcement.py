import unittest
import os
import sys
import uuid
import jwt
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, supabase
from services.tenancy import build_tenant_context, TenantContext

JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")

class TestTenancyEnforcement(unittest.TestCase):
    """
    Automated regression and security suite proving strict multi-tenant isolation,
    server-derived scoping, and compliance with Golden Rules 1, 2, and 4.
    """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        self.now_iso = datetime.now(timezone.utc).isoformat()
        self.org_a = f"org_alpha_{uuid.uuid4().hex[:8]}"
        self.org_b = f"org_beta_{uuid.uuid4().hex[:8]}"

        # Seed Organizations
        supabase.table("organization").insert({
            "id": self.org_a,
            "name": "Alpha Institute",
            "type": "college",
            "join_code": "ALP001",
            "max_seats": 50,
            "created_at": self.now_iso
        }).execute()

        supabase.table("organization").insert({
            "id": self.org_b,
            "name": "Beta University",
            "type": "university",
            "join_code": "BET002",
            "max_seats": 50,
            "created_at": self.now_iso
        }).execute()

        # Seed Admins
        self.admin_a_id = f"admin_a_{uuid.uuid4().hex[:8]}"
        self.admin_b_id = f"admin_b_{uuid.uuid4().hex[:8]}"

        self.token_admin_a = jwt.encode({
            "sub": self.admin_a_id,
            "role": "Organization Admin",
            "organization_id": self.org_a
        }, JWT_SECRET, algorithm="HS256")

        self.token_admin_b = jwt.encode({
            "sub": self.admin_b_id,
            "role": "Organization Admin",
            "organization_id": self.org_b
        }, JWT_SECRET, algorithm="HS256")

        # Seed Students
        self.student_a_id = f"std_a_{uuid.uuid4().hex[:8]}"
        self.student_b_id = f"std_b_{uuid.uuid4().hex[:8]}"
        self.student_indep_id = f"std_indep_{uuid.uuid4().hex[:8]}"
        self.email_a = f"alice_{uuid.uuid4().hex[:6]}@alpha.edu"
        self.email_b = f"bob_{uuid.uuid4().hex[:6]}@beta.edu"
        self.email_indep = f"charlie_{uuid.uuid4().hex[:6]}@gmail.com"

        self.token_student_a = jwt.encode({
            "sub": self.student_a_id,
            "role": "candidate",
            "organization_id": self.org_a
        }, JWT_SECRET, algorithm="HS256")

        self.token_student_indep = jwt.encode({
            "sub": self.student_indep_id,
            "role": "candidate",
            "organization_id": None
        }, JWT_SECRET, algorithm="HS256")

        # Insert Org A Student record
        supabase.table("students").insert({
            "id": self.student_a_id,
            "organization_id": self.org_a,
            "name": "Alice Alpha",
            "email": self.email_a,
            "roll_number": "ALP-001",
            "department": "Computer Science",
            "status": "Active",
            "interview_score": 9.0,
            "coding_score": 95.0,
            "created_at": self.now_iso
        }).execute()

        # Insert Org B Student record
        supabase.table("students").insert({
            "id": self.student_b_id,
            "organization_id": self.org_b,
            "name": "Bob Beta",
            "email": self.email_b,
            "roll_number": "BET-001",
            "department": "Electronics",
            "status": "Active",
            "interview_score": 7.5,
            "coding_score": 80.0,
            "created_at": self.now_iso
        }).execute()

        # Insert Independent User (no organization)
        supabase.table("users").insert({
            "id": self.student_indep_id,
            "name": "Charlie Independent",
            "email": self.email_indep,
            "role": "candidate",
            "organization_id": None,
            "created_at": self.now_iso
        }).execute()

    def test_golden_rule_1_header_spoofing_rejected(self):
        """Admin A supplies X-Organization-Id: org_b. Server MUST ignore it and scope to org_a."""
        headers = {
            "Authorization": f"Bearer {self.token_admin_a}",
            "X-Organization-Id": self.org_b  # Malicious attempt to spoof tenant
        }
        res = self.client.get("/api/admin/students", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        students = data.get("students", [])
        
        # Verify student list contains ONLY Alpha students, zero Beta students
        self.assertTrue(any(s["email"] == self.email_a for s in students))
        self.assertFalse(any(s["email"] == self.email_b for s in students))

    def test_golden_rule_2_independent_users_never_leak_into_empty_org(self):
        """Empty Org B queries dashboard; must return 0 students, NOT leak global/independent users."""
        empty_org = f"org_empty_{uuid.uuid4().hex[:8]}"
        supabase.table("organization").insert({
            "id": empty_org,
            "name": "Empty College",
            "type": "college",
            "join_code": "EMP001",
            "max_seats": 50,
            "created_at": self.now_iso
        }).execute()

        token_empty_admin = jwt.encode({
            "sub": f"admin_emp_{uuid.uuid4().hex[:8]}",
            "role": "Organization Admin",
            "organization_id": empty_org
        }, JWT_SECRET, algorithm="HS256")

        headers = {"Authorization": f"Bearer {token_empty_admin}"}
        res = self.client.get("/api/admin/dashboard", headers=headers)
        self.assertEqual(res.status_code, 200)
        stats = res.get_json()

        # Strict assertion: total_students MUST be 0, never fallback to independent users or 48
        self.assertEqual(stats.get("total_students"), 0)
        self.assertEqual(stats.get("ai_interviews_conducted"), 0)
        self.assertEqual(stats.get("coding_tests_completed"), 0)

    def test_golden_rule_4_cross_tenant_interview_pdf_returns_404_not_403(self):
        """Admin A querying an interview belonging to Org B MUST receive HTTP 404 Not Found."""
        iv_b_id = f"iv_beta_{uuid.uuid4().hex[:8]}"
        supabase.table("admin_interviews").insert({
            "id": iv_b_id,
            "organization_id": self.org_b,
            "title": "Beta System Design Interview",
            "role": "Backend Engineer",
            "difficulty": "Hard",
            "status": "Active",
            "created_at": self.now_iso
        }).execute()

        # Admin A requests Org B's interview PDF
        headers_a = {"Authorization": f"Bearer {self.token_admin_a}"}
        res_a = self.client.get(f"/api/admin/interview-pdf/{iv_b_id}", headers=headers_a)
        
        # Invariant: Must return 404 (never 403) to prevent resource enumeration
        self.assertEqual(res_a.status_code, 404)
        self.assertIn("not found", res_a.get_json().get("error", "").lower())

    def test_golden_rule_4_cross_tenant_coding_leaderboard_returns_404_not_403(self):
        """Admin A querying coding leaderboard of Org B MUST receive HTTP 404 Not Found."""
        code_b_id = f"code_beta_{uuid.uuid4().hex[:8]}"
        supabase.table("admin_coding").insert({
            "id": code_b_id,
            "organization_id": self.org_b,
            "title": "Beta Tree Inversion Challenge",
            "duration": 60,
            "language": "Python",
            "status": "Active",
            "created_at": self.now_iso
        }).execute()

        # Admin A requests Org B's coding leaderboard
        headers_a = {"Authorization": f"Bearer {self.token_admin_a}"}
        res_a = self.client.get(f"/api/admin/coding-test/{code_b_id}/leaderboard", headers=headers_a)
        
        # Invariant: Must return 404 (never 403)
        self.assertEqual(res_a.status_code, 404)

    def test_student_announcements_isolated_from_independent_users(self):
        """College announcements must NEVER be delivered to independent students."""
        ann_a_id = f"ann_a_{uuid.uuid4().hex[:8]}"
        supabase.table("announcements").insert({
            "id": ann_a_id,
            "organization_id": self.org_a,
            "title": "Alpha College Placement Drive Tomorrow",
            "message": "Only Alpha College students are eligible to attend.",
            "created_at": self.now_iso
        }).execute()

        # 1. Org A student queries notifications -> MUST receive announcement
        headers_a = {"Authorization": f"Bearer {self.token_student_a}"}
        res_a = self.client.get("/api/notifications", headers=headers_a)
        self.assertEqual(res_a.status_code, 200)
        notifs_a = res_a.get_json() if isinstance(res_a.get_json(), list) else res_a.get_json().get("notifications", [])
        self.assertTrue(any("Placement Drive" in n.get("title", "") for n in notifs_a))

        # 2. Independent student queries notifications -> MUST NEVER receive Org A announcement
        headers_indep = {"Authorization": f"Bearer {self.token_student_indep}"}
        res_indep = self.client.get("/api/notifications", headers=headers_indep)
        self.assertEqual(res_indep.status_code, 200)
        notifs_indep = res_indep.get_json() if isinstance(res_indep.get_json(), list) else res_indep.get_json().get("notifications", [])
        self.assertFalse(any("Placement Drive" in n.get("title", "") for n in notifs_indep))

if __name__ == "__main__":
    unittest.main()
