import unittest
import os
import sys
import uuid
import jwt
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, supabase

JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")

class TestStudentLinkingFlows(unittest.TestCase):
    """
    Automated test suite validating Phase 3:
      - CSV dry-run preview and commit
      - Institutional seat limit enforcement (409 Conflict)
      - College Join Code preview & student consent onboarding
      - Single Active College Membership enforcement
      - Admin student unlinking & archiving (with 404 on foreign tenant access)
      - Student transparency ('what my college can see')
    """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        self.now_iso = datetime.now(timezone.utc).isoformat()
        self.org_id = f"org_link_{uuid.uuid4().hex[:8]}"
        self.foreign_org_id = f"org_foreign_{uuid.uuid4().hex[:8]}"
        self.join_code = f"S{uuid.uuid4().hex[:5].upper()}"
        self.foreign_join_code = f"F{uuid.uuid4().hex[:5].upper()}"

        # Seed College with 5 seats max
        supabase.table("organization").insert({
            "id": self.org_id,
            "name": "Sunrise Peak Institute",
            "type": "college",
            "join_code": self.join_code,
            "max_seats": 5,
            "created_at": self.now_iso
        }).execute()

        # Seed Foreign College
        supabase.table("organization").insert({
            "id": self.foreign_org_id,
            "name": "Foreign Academy",
            "type": "college",
            "join_code": self.foreign_join_code,
            "max_seats": 5,
            "created_at": self.now_iso
        }).execute()

        # Seed Admin for org_id
        self.admin_id = f"admin_{uuid.uuid4().hex[:8]}"
        self.token_admin = jwt.encode({
            "sub": self.admin_id,
            "role": "Organization Admin",
            "organization_id": self.org_id
        }, JWT_SECRET, algorithm="HS256")

        # Seed Foreign Admin
        self.foreign_admin_id = f"fadmin_{uuid.uuid4().hex[:8]}"
        self.token_foreign_admin = jwt.encode({
            "sub": self.foreign_admin_id,
            "role": "Organization Admin",
            "organization_id": self.foreign_org_id
        }, JWT_SECRET, algorithm="HS256")

        # Seed Candidate User
        self.user_id = f"cand_{uuid.uuid4().hex[:8]}"
        self.user_email = f"student_{uuid.uuid4().hex[:6]}@gmail.com"
        supabase.table("users").insert({
            "id": self.user_id,
            "name": "Test Candidate",
            "email": self.user_email,
            "role": "candidate",
            "organization_id": None,
            "created_at": self.now_iso
        }).execute()

        self.token_student = jwt.encode({
            "sub": self.user_id,
            "role": "candidate",
            "organization_id": None
        }, JWT_SECRET, algorithm="HS256")

    def test_01_csv_import_preview_mode_does_not_mutate_database(self):
        """CSV upload with preview=true validates rows without writing to DB."""
        csv_data = (
            "name,email,roll_number,department,year\n"
            f"Aditi Sen,aditi_{uuid.uuid4().hex[:4]}@sunrise.edu,CS01,CSE,2026\n"
            f"Bikram Roy,bikram_{uuid.uuid4().hex[:4]}@sunrise.edu,CS02,CSE,2026\n"
            "Bad Row,not-an-email,CS03,CSE,2026\n"
        )
        headers = {"Authorization": f"Bearer {self.token_admin}"}
        res = self.client.post("/api/admin/students/import", json={
            "csv_text": csv_data,
            "preview": True
        }, headers=headers)

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("preview"))
        self.assertEqual(data.get("valid_count"), 2)
        self.assertEqual(data.get("invalid_count"), 1)
        self.assertEqual(data.get("seat_limit"), 5)
        self.assertTrue(data.get("can_commit"))

        # Verify no students or invites were actually inserted
        invs = supabase.table("org_invites").select("*").eq("organization_id", self.org_id).execute()
        self.assertEqual(len(invs.data or []), 0)

    def test_02_csv_import_commit_creates_invites_and_roster(self):
        """CSV upload with preview=false commits valid rows and creates pending invites."""
        e1 = f"student1_{uuid.uuid4().hex[:4]}@sunrise.edu"
        e2 = f"student2_{uuid.uuid4().hex[:4]}@sunrise.edu"
        csv_data = (
            "name,email,roll_number,department,year\n"
            f"Student One,{e1},CS01,CSE,2026\n"
            f"Student Two,{e2},CS02,CSE,2026\n"
        )
        headers = {"Authorization": f"Bearer {self.token_admin}"}
        res = self.client.post("/api/admin/students/import", json={
            "csv_text": csv_data,
            "preview": False
        }, headers=headers)

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("count"), 2)
        self.assertEqual(data.get("invites_created"), 2)

        # Verify invites were created with tokens and 7-day expiration
        invs = supabase.table("org_invites").select("*").eq("organization_id", self.org_id).execute()
        self.assertEqual(len(invs.data or []), 2)
        for inv in invs.data:
            self.assertEqual(inv["status"], "pending")
            self.assertTrue(len(inv["token"]) > 20)

    def test_03_csv_import_rejects_exceeding_seat_limit(self):
        """Attempting to import more students than max_seats returns 409 Conflict."""
        # College has max_seats = 5. Attempt to import 6 students.
        rows = ["name,email,roll_number,department,year"]
        for i in range(6):
            rows.append(f"Student {i},student_{uuid.uuid4().hex[:6]}@sunrise.edu,R{i},CSE,2026")
        csv_data = "\n".join(rows)

        headers = {"Authorization": f"Bearer {self.token_admin}"}
        res = self.client.post("/api/admin/students/import", json={
            "csv_text": csv_data,
            "preview": False
        }, headers=headers)

        self.assertEqual(res.status_code, 409)
        self.assertIn("Seat limit reached", res.get_json().get("error", ""))

    def test_04_college_join_code_preview_and_consent(self):
        """Student previews college by join code, checks consent notice."""
        # Valid code
        res_ok = self.client.get(f"/api/student/college-preview?code={self.join_code}")
        self.assertEqual(res_ok.status_code, 200)
        data = res_ok.get_json()
        self.assertEqual(data.get("college_name"), "Sunrise Peak Institute")
        self.assertIn("independent practice history remains strictly private", data.get("consent_notice", ""))

        # Invalid code
        res_bad = self.client.get("/api/student/college-preview?code=WRONG1")
        self.assertEqual(res_bad.status_code, 404)

    def test_05_student_join_college_with_consent(self):
        """Student enters join code with consent; links account to college."""
        headers = {"Authorization": f"Bearer {self.token_student}"}

        # 1. Attempt join without consent -> rejected 400
        res_no_consent = self.client.post("/api/student/join-college", json={
            "join_code": self.join_code,
            "consent": False
        }, headers=headers)
        self.assertEqual(res_no_consent.status_code, 400)

        # 2. Join with consent -> succeeds 200
        res_join = self.client.post("/api/student/join-college", json={
            "join_code": self.join_code,
            "consent": True,
            "roll_number": "CS-2026-99",
            "department": "Computer Science"
        }, headers=headers)
        self.assertEqual(res_join.status_code, 200)

        # 3. Check student's active college
        res_my = self.client.get("/api/student/my-college", headers=headers)
        self.assertEqual(res_my.status_code, 200)
        my_col = res_my.get_json().get("college")
        self.assertIsNotNone(my_col)
        self.assertEqual(my_col.get("id"), self.org_id)
        self.assertEqual(my_col.get("roll_number"), "CS-2026-99")
        self.assertIn("what_my_college_can_see", my_col)
        self.assertIn("what_my_college_cannot_see", my_col)

    def test_06_single_active_college_membership_enforcement(self):
        """Joining a new college automatically archives previous active college membership."""
        headers = {"Authorization": f"Bearer {self.token_student}"}

        # First join Sunrise Peak
        self.client.post("/api/student/join-college", json={"join_code": self.join_code, "consent": True}, headers=headers)

        # Then join Foreign Academy
        res_switch = self.client.post("/api/student/join-college", json={"join_code": self.foreign_join_code, "consent": True}, headers=headers)
        self.assertEqual(res_switch.status_code, 200)

        # Verify old membership for Sunrise Peak is ARCHIVED
        old_mem = supabase.table("org_memberships").select("*").eq("user_id", self.user_id).eq("organization_id", self.org_id).execute()
        self.assertEqual(old_mem.data[0]["status"], "archived")

        # Verify new membership for Foreign Academy is ACTIVE
        new_mem = supabase.table("org_memberships").select("*").eq("user_id", self.user_id).eq("organization_id", self.foreign_org_id).execute()
        self.assertEqual(new_mem.data[0]["status"], "active")

    def test_07_admin_unlink_student_and_404_on_foreign_tenant(self):
        """Admin unlinks student: preserves history, reverts account to independent. Foreign admin gets 404."""
        # Link user to Sunrise Peak
        headers_student = {"Authorization": f"Bearer {self.token_student}"}
        self.client.post("/api/student/join-college", json={"join_code": self.join_code, "consent": True}, headers=headers_student)

        # 1. Foreign Admin attempts to unlink user -> MUST return 404 (Golden Rule 4)
        headers_foreign = {"Authorization": f"Bearer {self.token_foreign_admin}"}
        res_foreign = self.client.delete(f"/api/admin/student/{self.user_id}", headers=headers_foreign)
        self.assertEqual(res_foreign.status_code, 404)

        # 2. Owning Admin unlinks student -> succeeds 200
        headers_owning = {"Authorization": f"Bearer {self.token_admin}"}
        res_del = self.client.delete(f"/api/admin/student/{self.user_id}", headers=headers_owning)
        self.assertEqual(res_del.status_code, 200)

        # 3. Verify user account reverted to independent (organization_id is None)
        u_row = supabase.table("users").select("organization_id").eq("id", self.user_id).execute()
        self.assertIsNone(u_row.data[0]["organization_id"])

        # 4. Verify membership archived
        mem_row = supabase.table("org_memberships").select("status").eq("user_id", self.user_id).eq("organization_id", self.org_id).execute()
        self.assertEqual(mem_row.data[0]["status"], "archived")

if __name__ == "__main__":
    unittest.main()
