import unittest
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_supabase import SQLiteSupabaseMock

class TestMigration016Tenancy(unittest.TestCase):
    """
    Validates Migration 016 schema, tables, constraints, indices, and local SQLite mock.
    Tables & Columns audited:
      - org_memberships
      - org_invites
      - organization (join_code, max_seats)
      - coding_submissions (organization_id)
    """

    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.org_a_id = f"org_test_a_{uuid.uuid4().hex[:8]}"
        self.org_b_id = f"org_test_b_{uuid.uuid4().hex[:8]}"
        self.user_a_id = f"user_a_{uuid.uuid4().hex[:8]}"
        self.user_b_id = f"user_b_{uuid.uuid4().hex[:8]}"
        self.independent_user_id = f"user_indep_{uuid.uuid4().hex[:8]}"
        self.now_iso = datetime.now(timezone.utc).isoformat()

        # Seed Organizations
        self.client.table("organization").insert({
            "id": self.org_a_id,
            "name": "Sunrise Peak College",
            "type": "college",
            "join_code": "SUN001",
            "max_seats": 100,
            "created_at": self.now_iso
        }).execute()

        self.client.table("organization").insert({
            "id": self.org_b_id,
            "name": "Evergreen University",
            "type": "university",
            "join_code": "EVG002",
            "max_seats": 50,
            "created_at": self.now_iso
        }).execute()

    def test_migration_sql_files_exist_and_are_well_formed(self):
        migrations_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "migrations"
        )
        up_path = os.path.join(migrations_dir, "016_strict_tenant_isolation.sql")
        down_path = os.path.join(migrations_dir, "016_strict_tenant_isolation_rollback.sql")

        self.assertTrue(os.path.exists(up_path), f"Missing {up_path}")
        self.assertTrue(os.path.exists(down_path), f"Missing {down_path}")

        with open(up_path, "r", encoding="utf-8") as f:
            up_sql = f.read()

        self.assertIn("CREATE TABLE IF NOT EXISTS org_memberships", up_sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS org_invites", up_sql)
        self.assertIn("ALTER TABLE organization ADD COLUMN join_code", up_sql)
        self.assertIn("ALTER TABLE organization ADD COLUMN max_seats", up_sql)
        self.assertIn("ALTER TABLE coding_submissions ADD COLUMN organization_id", up_sql)
        self.assertIn("idx_org_memberships_org_user", up_sql)

        with open(down_path, "r", encoding="utf-8") as f:
            down_sql = f.read()

        self.assertIn("DROP TABLE IF EXISTS org_invites", down_sql)
        self.assertIn("DROP TABLE IF EXISTS org_memberships", down_sql)

    def test_org_memberships_crud_and_status(self):
        mem_id = f"mem_{uuid.uuid4().hex}"
        # Insert active membership for Org A
        res = self.client.table("org_memberships").insert({
            "id": mem_id,
            "organization_id": self.org_a_id,
            "user_id": self.user_a_id,
            "role": "student",
            "status": "active",
            "roll_number": "CS-2026-001",
            "department": "Computer Science",
            "joined_at": self.now_iso,
            "updated_at": self.now_iso
        }).execute()
        self.assertTrue(res.data)

        # Query membership by org_id
        org_a_members = self.client.table("org_memberships").select("*").eq("organization_id", self.org_a_id).execute()
        self.assertEqual(len(org_a_members.data), 1)
        self.assertEqual(org_a_members.data[0]["user_id"], self.user_a_id)
        self.assertEqual(org_a_members.data[0]["status"], "active")

        # Query membership by Org B (MUST BE EMPTY - ISOLATION)
        org_b_members = self.client.table("org_memberships").select("*").eq("organization_id", self.org_b_id).execute()
        self.assertEqual(len(org_b_members.data), 0)

        # Update status to archived (unlinking)
        self.client.table("org_memberships").update({"status": "archived"}).eq("id", mem_id).execute()
        archived_members = self.client.table("org_memberships").select("*").eq("id", mem_id).execute()
        self.assertEqual(archived_members.data[0]["status"], "archived")

    def test_org_invites_lifecycle(self):
        invite_id = f"inv_{uuid.uuid4().hex}"
        token = f"tok_{uuid.uuid4().hex}"
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

        # Create invite
        self.client.table("org_invites").insert({
            "id": invite_id,
            "organization_id": self.org_a_id,
            "email": "student@sunrise.edu",
            "role": "student",
            "token": token,
            "status": "pending",
            "expires_at": expires_at,
            "created_at": self.now_iso
        }).execute()

        # Lookup invite by token
        inv = self.client.table("org_invites").select("*").eq("token", token).execute()
        self.assertEqual(len(inv.data), 1)
        self.assertEqual(inv.data[0]["status"], "pending")
        self.assertEqual(inv.data[0]["organization_id"], self.org_a_id)

        # Accept invite
        self.client.table("org_invites").update({"status": "accepted"}).eq("token", token).execute()
        accepted_inv = self.client.table("org_invites").select("*").eq("token", token).execute()
        self.assertEqual(accepted_inv.data[0]["status"], "accepted")

    def test_coding_submissions_organization_scoping(self):
        sub_a_id = f"sub_a_{uuid.uuid4().hex}"
        sub_b_id = f"sub_b_{uuid.uuid4().hex}"
        sub_indep_id = f"sub_indep_{uuid.uuid4().hex}"

        # Insert submission for Org A student
        self.client.table("coding_submissions").insert({
            "id": sub_a_id,
            "user_id": self.user_a_id,
            "organization_id": self.org_a_id,
            "problem_id": "two_sum",
            "language": "python",
            "code": "print('hello')",
            "passed": 5,
            "total": 5,
            "created_at": self.now_iso
        }).execute()

        # Insert submission for Org B student
        self.client.table("coding_submissions").insert({
            "id": sub_b_id,
            "user_id": self.user_b_id,
            "organization_id": self.org_b_id,
            "problem_id": "two_sum",
            "language": "python",
            "code": "print('world')",
            "passed": 4,
            "total": 5,
            "created_at": self.now_iso
        }).execute()

        # Insert submission for Independent student (no org)
        self.client.table("coding_submissions").insert({
            "id": sub_indep_id,
            "user_id": self.independent_user_id,
            "organization_id": None,
            "problem_id": "two_sum",
            "language": "python",
            "code": "print('indep')",
            "passed": 5,
            "total": 5,
            "created_at": self.now_iso
        }).execute()

        # Org A scoped query ONLY returns Org A submission
        org_a_subs = self.client.table("coding_submissions").select("*").eq("organization_id", self.org_a_id).execute()
        self.assertEqual(len(org_a_subs.data), 1)
        self.assertEqual(org_a_subs.data[0]["id"], sub_a_id)

        # Org B scoped query ONLY returns Org B submission
        org_b_subs = self.client.table("coding_submissions").select("*").eq("organization_id", self.org_b_id).execute()
        self.assertEqual(len(org_b_subs.data), 1)
        self.assertEqual(org_b_subs.data[0]["id"], sub_b_id)

    def test_organization_join_code_and_seats(self):
        org = self.client.table("organization").select("*").eq("id", self.org_a_id).execute()
        self.assertEqual(len(org.data), 1)
        self.assertEqual(org.data[0]["join_code"], "SUN001")
        self.assertEqual(org.data[0]["max_seats"], 100)

if __name__ == "__main__":
    unittest.main()
