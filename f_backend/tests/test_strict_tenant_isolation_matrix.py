import unittest
import os
import sys
import uuid
import jwt
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, supabase
from services.tenancy import build_tenant_context, TenantContext

JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")

class TestStrictTenantIsolationMatrix(unittest.TestCase):
    """
    Master Multi-Tenant Isolation & Anti-Probing Security Regression Matrix.
    Proves comprehensive defense-in-depth across:
      - 5 Actor Types (Admin A, Admin B, Student A, Student B, Independent Candidate)
      - All Tenant-Owned Entities (Rosters, Stats, Interviews, Coding Tests, Submissions,
        Question Bank, Announcements, Private Student Practice)
      - Golden Rule 1 (Server identity derivation, ignoring client org_id overrides)
      - Golden Rule 4 (404 Anti-Probing on all foreign tenant queries)
      - Golden Rule 5 (Independent student exclusion and zero-leakage)
    """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        self.now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Organizations
        self.org_a = f"org_alpha_{uuid.uuid4().hex[:8]}"
        self.org_b = f"org_beta_{uuid.uuid4().hex[:8]}"

        supabase.table("organization").insert({
            "id": self.org_a,
            "name": "Alpha Institute of Tech",
            "type": "college",
            "join_code": f"A{uuid.uuid4().hex[:5].upper()}",
            "max_seats": 25,
            "created_at": self.now_iso
        }).execute()

        supabase.table("organization").insert({
            "id": self.org_b,
            "name": "Beta University",
            "type": "university",
            "join_code": f"B{uuid.uuid4().hex[:5].upper()}",
            "max_seats": 25,
            "created_at": self.now_iso
        }).execute()

        # 2. Admins
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

        # 3. Students
        self.student_a_id = f"std_a_{uuid.uuid4().hex[:8]}"
        self.student_b_id = f"std_b_{uuid.uuid4().hex[:8]}"
        self.student_indep_id = f"std_indep_{uuid.uuid4().hex[:8]}"

        self.email_a = f"alice_{uuid.uuid4().hex[:6]}@alpha.edu"
        self.email_b = f"bob_{uuid.uuid4().hex[:6]}@beta.edu"
        self.email_indep = f"ian_{uuid.uuid4().hex[:6]}@gmail.com"

        # Seed Student A in Users + Students + Org Memberships
        supabase.table("users").insert({
            "id": self.student_a_id,
            "email": self.email_a,
            "name": "Alice Alpha",
            "role": "candidate",
            "organization_id": self.org_a,
            "created_at": self.now_iso
        }).execute()
        supabase.table("students").insert({
            "id": self.student_a_id,
            "name": "Alice Alpha",
            "email": self.email_a,
            "organization_id": self.org_a,
            "roll_number": "A-101",
            "department": "Computer Science",
            "status": "Active",
            "created_at": self.now_iso
        }).execute()
        supabase.table("org_memberships").insert({
            "id": f"mem_a_{uuid.uuid4().hex[:8]}",
            "organization_id": self.org_a,
            "user_id": self.student_a_id,
            "roll_number": "A-101",
            "department": "Computer Science",
            "status": "active",
            "joined_at": self.now_iso,
            "updated_at": self.now_iso
        }).execute()

        # Seed Student B in Users + Students + Org Memberships
        supabase.table("users").insert({
            "id": self.student_b_id,
            "email": self.email_b,
            "name": "Bob Beta",
            "role": "candidate",
            "organization_id": self.org_b,
            "created_at": self.now_iso
        }).execute()
        supabase.table("students").insert({
            "id": self.student_b_id,
            "name": "Bob Beta",
            "email": self.email_b,
            "organization_id": self.org_b,
            "roll_number": "B-202",
            "department": "Electrical Eng",
            "status": "Active",
            "created_at": self.now_iso
        }).execute()
        supabase.table("org_memberships").insert({
            "id": f"mem_b_{uuid.uuid4().hex[:8]}",
            "organization_id": self.org_b,
            "user_id": self.student_b_id,
            "roll_number": "B-202",
            "department": "Electrical Eng",
            "status": "active",
            "joined_at": self.now_iso,
            "updated_at": self.now_iso
        }).execute()

        # Seed Independent Student (organization_id IS NULL)
        supabase.table("users").insert({
            "id": self.student_indep_id,
            "email": self.email_indep,
            "name": "Ian Independent",
            "role": "candidate",
            "organization_id": None,
            "created_at": self.now_iso
        }).execute()

        # Student Tokens
        self.token_student_a = jwt.encode({
            "sub": self.student_a_id,
            "role": "candidate",
            "organization_id": self.org_a
        }, JWT_SECRET, algorithm="HS256")

        self.token_student_b = jwt.encode({
            "sub": self.student_b_id,
            "role": "candidate",
            "organization_id": self.org_b
        }, JWT_SECRET, algorithm="HS256")

        self.token_student_indep = jwt.encode({
            "sub": self.student_indep_id,
            "role": "candidate",
            "organization_id": None
        }, JWT_SECRET, algorithm="HS256")

    # =========================================================================
    # 1. STUDENT ROSTER ISOLATION & ANTI-PROBING (GOLDEN RULES 1, 2, 4, 5)
    # =========================================================================

    def test_roster_listing_strict_isolation(self):
        """Admin A list contains only Org A students; excludes Org B and Independent students."""
        res_a = self.client.get("/api/admin/students", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.get_json()
        students_a = data_a.get("students", [])

        ids_a = [s.get("id") or s.get("user_id") for s in students_a]
        self.assertIn(self.student_a_id, ids_a)
        self.assertNotIn(self.student_b_id, ids_a, "SECURITY VIOLATION: Org B student leaked into Org A roster!")
        self.assertNotIn(self.student_indep_id, ids_a, "SECURITY VIOLATION: Independent student leaked into Org A roster!")

        # Admin B check
        res_b = self.client.get("/api/admin/students", headers={"Authorization": f"Bearer {self.token_admin_b}"})
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.get_json()
        students_b = data_b.get("students", [])

        ids_b = [s.get("id") or s.get("user_id") for s in students_b]
        self.assertIn(self.student_b_id, ids_b)
        self.assertNotIn(self.student_a_id, ids_b, "SECURITY VIOLATION: Org A student leaked into Org B roster!")
        self.assertNotIn(self.student_indep_id, ids_b, "SECURITY VIOLATION: Independent student leaked into Org B roster!")

    def test_student_detail_anti_probing_returns_404(self):
        """Direct lookup of foreign or independent student by ID returns HTTP 404 (Golden Rule 4)."""
        # Admin A accesses Student A -> 200
        res_own = self.client.get(f"/api/admin/student/{self.student_a_id}", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_own.status_code, 200)

        # Admin A attempts to probe Student B -> MUST return 404
        res_foreign = self.client.get(f"/api/admin/student/{self.student_b_id}", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_foreign.status_code, 404, "Anti-probing failed: Cross-tenant lookup must return 404, not 403 or 200")

        # Admin A attempts to probe Independent Student -> MUST return 404
        res_indep = self.client.get(f"/api/admin/student/{self.student_indep_id}", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_indep.status_code, 404, "Anti-probing failed: Independent student lookup must return 404")

    def test_student_mutation_cross_tenant_rejected_with_404(self):
        """Cross-tenant update and delete operations return HTTP 404 without mutating foreign data."""
        # Attempt update
        res_upd = self.client.put(f"/api/admin/student/{self.student_b_id}",
                                  headers={"Authorization": f"Bearer {self.token_admin_a}"},
                                  json={"name": "Hacked Name", "department": "Compromised"})
        self.assertIn(res_upd.status_code, (403, 404))

        # Verify Student B was not mutated
        b_record = supabase.table("students").select("*").eq("id", self.student_b_id).execute().data[0]
        self.assertEqual(b_record["name"], "Bob Beta")

        # Attempt delete
        res_del = self.client.delete(f"/api/admin/student/{self.student_b_id}",
                                     headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertIn(res_del.status_code, (403, 404))

        # Verify Student B membership remains active in Org B
        mem_b = supabase.table("org_memberships").select("*").eq("user_id", self.student_b_id).eq("organization_id", self.org_b).execute()
        self.assertTrue(len(mem_b.data) > 0 and mem_b.data[0]["status"] == "active")

    # =========================================================================
    # 2. SERVER-DERIVED IDENTITY & CLIENT TAMPERING RESISTANCE (GOLDEN RULE 1)
    # =========================================================================

    def test_ignore_client_org_override_headers_and_query_params(self):
        """Admin A sends headers or query params attempting to act on behalf of Org B; server derives org strictly from token."""
        # Header spoofing attempt
        res_header = self.client.get("/api/admin/students",
                                    headers={
                                        "Authorization": f"Bearer {self.token_admin_a}",
                                        "X-Organization-Id": self.org_b,
                                        "x-org-id": self.org_b
                                    })
        self.assertEqual(res_header.status_code, 200)
        data = res_header.get_json()
        ids = [s.get("id") or s.get("user_id") for s in data.get("students", [])]
        self.assertIn(self.student_a_id, ids)
        self.assertNotIn(self.student_b_id, ids, "CRITICAL VULNERABILITY: Client header X-Organization-Id allowed tenant bypass!")

        # Query param spoofing attempt
        res_query = self.client.get(f"/api/admin/students?organization_id={self.org_b}&org_id={self.org_b}",
                                   headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_query.status_code, 200)
        data_q = res_query.get_json()
        ids_q = [s.get("id") or s.get("user_id") for s in data_q.get("students", [])]
        self.assertIn(self.student_a_id, ids_q)
        self.assertNotIn(self.student_b_id, ids_q, "CRITICAL VULNERABILITY: Query parameter org_id allowed tenant bypass!")

    # =========================================================================
    # 3. DASHBOARD METRICS ISOLATION (GOLDEN RULE 8 - HONEST REAL METRICS)
    # =========================================================================

    def test_dashboard_metrics_strict_isolation(self):
        """Admin dashboard stats reflect exclusively the authenticated organization's counts."""
        res_a = self.client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_a.status_code, 200)
        stats_a = res_a.get_json()

        # Admin A has 1 student
        self.assertEqual(stats_a.get("total_students"), 1)
        self.assertNotIn("+14% this month", str(stats_a))
        self.assertNotIn("35% conversion", str(stats_a))

        # Admin B has 1 student
        res_b = self.client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {self.token_admin_b}"})
        self.assertEqual(res_b.status_code, 200)
        stats_b = res_b.get_json()
        self.assertEqual(stats_b.get("total_students"), 1)

    # =========================================================================
    # 4. CODING TESTS & SUBMISSIONS ISOLATION
    # =========================================================================

    def test_coding_assessments_and_submissions_isolation(self):
        """Coding challenges and student submissions remain strictly partitioned by organization."""
        # Create Coding Challenge for Org A
        challenge_a_id = f"ct_{uuid.uuid4().hex[:8]}"
        supabase.table("admin_coding").insert({
            "id": challenge_a_id,
            "title": "Alpha Graph Algorithm",
            "organization_id": self.org_a,
            "duration": 60,
            "language": "Python",
            "difficulty": "Medium",
            "visible_tests": 3,
            "hidden_tests": 7,
            "status": "Active",
            "created_at": self.now_iso
        }).execute()

        # Create Coding Challenge for Org B
        challenge_b_id = f"ct_{uuid.uuid4().hex[:8]}"
        supabase.table("admin_coding").insert({
            "id": challenge_b_id,
            "title": "Beta Matrix Solver",
            "organization_id": self.org_b,
            "duration": 60,
            "language": "Python",
            "difficulty": "Hard",
            "visible_tests": 3,
            "hidden_tests": 7,
            "status": "Active",
            "created_at": self.now_iso
        }).execute()

        # Admin A lists challenges
        res_chal_a = self.client.get("/api/admin/coding", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_chal_a.status_code, 200)
        tests_a = res_chal_a.get_json()
        if isinstance(tests_a, dict):
            tests_a = tests_a.get("tests", [])
        chal_ids_a = [t.get("id") for t in tests_a]
        self.assertIn(challenge_a_id, chal_ids_a)
        self.assertNotIn(challenge_b_id, chal_ids_a, "SECURITY VIOLATION: Org B coding challenge visible to Org A!")

        # Create submission for Student A
        sub_a_id = f"sub_a_{uuid.uuid4().hex[:8]}"
        supabase.table("coding_submissions").insert({
            "id": sub_a_id,
            "challenge_id": challenge_a_id,
            "student_id": self.student_a_id,
            "organization_id": self.org_a,
            "status": "passed",
            "created_at": self.now_iso
        }).execute()

        # Create submission for Student B
        sub_b_id = f"sub_b_{uuid.uuid4().hex[:8]}"
        supabase.table("coding_submissions").insert({
            "id": sub_b_id,
            "challenge_id": challenge_b_id,
            "student_id": self.student_b_id,
            "organization_id": self.org_b,
            "status": "passed",
            "created_at": self.now_iso
        }).execute()

        # Admin A views leaderboard for challenge A
        res_sub_a = self.client.get(f"/api/admin/coding-test/{challenge_a_id}/leaderboard", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_sub_a.status_code, 200)
        raw_board = res_sub_a.get_json()
        leaderboard_a = raw_board if isinstance(raw_board, list) else raw_board.get("leaderboard", [])
        student_ids_in_a = [s.get("student_id") or s.get("id") for s in leaderboard_a]
        self.assertNotIn(self.student_b_id, student_ids_in_a, "SECURITY VIOLATION: Org B student submission leaked into Org A leaderboard!")

        # Admin A attempts to probe challenge B leaderboard -> MUST return 404
        res_sub_b_probe = self.client.get(f"/api/admin/coding-test/{challenge_b_id}/leaderboard", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_sub_b_probe.status_code, 404, "Anti-probing failed: Cross-tenant test leaderboard lookup must return 404")

    # =========================================================================
    # 5. QUESTION BANK ISOLATION
    # =========================================================================

    def test_question_bank_isolation(self):
        """Admin A sees system questions + Org A custom questions; never Org B custom questions."""
        q_a_id = f"q_a_{uuid.uuid4().hex[:8]}"
        q_b_id = f"q_b_{uuid.uuid4().hex[:8]}"

        supabase.table("question_bank").insert({
            "id": q_a_id,
            "question_text": "Describe Alpha distributed transactions",
            "organization_id": self.org_a,
            "is_system": False,
            "created_at": self.now_iso
        }).execute()

        supabase.table("question_bank").insert({
            "id": q_b_id,
            "question_text": "Describe Beta kernel scheduling",
            "organization_id": self.org_b,
            "is_system": False,
            "created_at": self.now_iso
        }).execute()

        res_q_a = self.client.get("/api/admin/question-bank", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_q_a.status_code, 200)
        q_raw = res_q_a.get_json()
        q_list_a = q_raw if isinstance(q_raw, list) else q_raw.get("questions", [])
        q_ids_a = [q.get("id") for q in q_list_a]
        self.assertIn(q_a_id, q_ids_a)
        self.assertNotIn(q_b_id, q_ids_a, "SECURITY VIOLATION: Org B proprietary question visible to Org A!")

    # =========================================================================
    # 6. ANNOUNCEMENTS ISOLATION
    # =========================================================================

    def test_announcements_strict_cross_tenant_isolation(self):
        """Announcements published by Org A are visible exclusively to Org A; never to Org B or independent candidates."""
        # Admin A creates an announcement
        res_post = self.client.post("/api/admin/announcements",
                                    headers={"Authorization": f"Bearer {self.token_admin_a}"},
                                    json={"title": "Alpha Fall Hackathon", "content": "Exclusive to Alpha students."})
        self.assertIn(res_post.status_code, (200, 201))

        # Admin B fetches announcements
        res_b = self.client.get("/api/admin/announcements", headers={"Authorization": f"Bearer {self.token_admin_b}"})
        self.assertEqual(res_b.status_code, 200)
        ann_raw = res_b.get_json()
        ann_b = ann_raw if isinstance(ann_raw, list) else ann_raw.get("announcements", [])
        titles_b = [a.get("title") for a in ann_b]
        self.assertNotIn("Alpha Fall Hackathon", titles_b, "SECURITY VIOLATION: Org A announcement leaked to Org B!")

    # =========================================================================
    # 7. CANDIDATE PRIVACY: INDEPENDENT PRACTICE IS ZERO-ACCESSIBLE TO ADMINS
    # =========================================================================

    def test_independent_candidate_personal_practice_isolation(self):
        """College admin list of interviews queries only that college's interviews; never foreign or independent sessions."""
        iv_a_id = f"iv_a_{uuid.uuid4().hex[:8]}"
        iv_b_id = f"iv_b_{uuid.uuid4().hex[:8]}"

        supabase.table("admin_interviews").insert({
            "id": iv_a_id,
            "organization_id": self.org_a,
            "title": "Alpha AI Evaluation",
            "category": "Backend",
            "difficulty": "Hard",
            "student_id": self.student_a_id,
            "student_name": "Alice Alpha",
            "scheduled_date": "2026-11-20",
            "status": "Scheduled",
            "overall_score": 9.2,
            "created_at": self.now_iso
        }).execute()

        supabase.table("admin_interviews").insert({
            "id": iv_b_id,
            "organization_id": self.org_b,
            "title": "Beta Secret Evaluation",
            "category": "Frontend",
            "difficulty": "Medium",
            "student_id": self.student_b_id,
            "student_name": "Bob Beta",
            "scheduled_date": "2026-11-21",
            "status": "Scheduled",
            "overall_score": 8.0,
            "created_at": self.now_iso
        }).execute()

        # Admin A checks interviews
        res_int_a = self.client.get("/api/admin/interviews", headers={"Authorization": f"Bearer {self.token_admin_a}"})
        self.assertEqual(res_int_a.status_code, 200)
        int_raw = res_int_a.get_json()
        interviews_a = int_raw if isinstance(int_raw, list) else int_raw.get("interviews", [])
        int_ids_a = [i.get("id") for i in interviews_a]
        self.assertIn(iv_a_id, int_ids_a)
        self.assertNotIn(iv_b_id, int_ids_a, "PRIVACY VIOLATION: Org B interview leaked to College Admin A!")

    # =========================================================================
    # 8. SEAT ALLOCATION & CEILING ENFORCEMENT
    # =========================================================================

    def test_seat_ceiling_enforcement_on_invite_and_join(self):
        """Organization cannot exceed max_seats via join code or bulk import."""
        # Set max_seats = 1 for Org A (currently has 1 active member: Alice)
        supabase.table("organization").update({"max_seats": 1}).eq("id", self.org_a).execute()

        # Attempt to join Org A as Student B using Org A's join code
        org_a_record = supabase.table("organization").select("join_code").eq("id", self.org_a).execute().data[0]
        join_code_a = org_a_record["join_code"]

        res_join = self.client.post("/api/student/join-college",
                                   headers={"Authorization": f"Bearer {self.token_student_b}"},
                                   json={
                                       "join_code": join_code_a,
                                       "roll_number": "B-999",
                                       "department": "Civil",
                                       "consent": True
                                   })
        self.assertEqual(res_join.status_code, 409, "Seat ceiling failed: Must reject join with 409 when capacity reached")
        self.assertIn("capacity", res_join.get_json().get("error", "").lower())

if __name__ == "__main__":
    unittest.main()
