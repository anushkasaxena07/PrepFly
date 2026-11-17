"""
PrepFly Super Admin User Visibility & Question Bank Regression Test Suite.
Validates:
1. Candidate roster includes B2C learners (organization_id IS NULL) mapped to "Direct / B2C Learner".
2. Case-insensitive role filtering excludes admins and includes all candidate roles.
3. Genuine resume and coding scores populate from real tables.
4. Question Bank CRUD operations work against real database without in-memory mocks.
"""

import unittest
from unittest.mock import MagicMock, patch
import app as app_module
from app import app


class TestSuperAdminUserVisibilityAndQBank(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.mock_db = MagicMock()
        self.orig_supabase = app_module.supabase
        app_module.supabase = self.mock_db

    def tearDown(self):
        app_module.supabase = self.orig_supabase

    @patch("app.verify_super_admin", return_value=True)
    def test_b2c_students_visible_with_direct_learner_label(self, mock_auth):
        """B2C candidates with organization_id=None must be returned with 'Direct / B2C Learner'."""
        mock_users = MagicMock()
        mock_users.execute.return_value.data = [
            {
                "id": "b2c_user_1",
                "name": "Jane Doe",
                "email": "jane@example.com",
                "role": "student",
                "subscription": "FREE",
                "created_at": "2026-11-01T10:00:00Z",
                "organization_id": None,
                "department": None,
                "roll_number": None
            },
            {
                "id": "org_user_2",
                "name": "John Smith",
                "email": "john@campus.edu",
                "role": "Student",
                "subscription": "PREMIUM",
                "created_at": "2026-11-02T10:00:00Z",
                "organization_id": "org_univ_01",
                "department": "Computer Science",
                "roll_number": "CS-101"
            },
            {
                "id": "admin_user_3",
                "name": "Admin User",
                "email": "admin@campus.edu",
                "role": "ADMIN",
                "organization_id": "org_univ_01"
            }
        ]

        mock_orgs = MagicMock()
        mock_orgs.execute.return_value.data = [
            {"id": "org_univ_01", "name": "Apex University"}
        ]

        mock_sessions = MagicMock()
        mock_sessions.execute.return_value.data = [
            {"user_id": "b2c_user_1", "created_at": "2026-11-15T12:00:00Z", "final_score": 85.0}
        ]

        mock_resumes = MagicMock()
        mock_resumes.execute.return_value.data = [
            {"user_id": "b2c_user_1", "score": 78.5, "created_at": "2026-11-15T12:00:00Z"}
        ]

        mock_coding = MagicMock()
        mock_coding.execute.return_value.data = [
            {"user_id": "b2c_user_1", "passed": 3, "total": 3}
        ]

        def table_router(table_name):
            builder = MagicMock()
            builder.select.return_value = builder
            if table_name == "users":
                mock_users.select.return_value = mock_users
                return mock_users
            elif table_name == "organization":
                mock_orgs.select.return_value = mock_orgs
                return mock_orgs
            elif table_name == "sessions":
                mock_sessions.select.return_value = mock_sessions
                return mock_sessions
            elif table_name == "resume_scores":
                mock_resumes.select.return_value = mock_resumes
                return mock_resumes
            elif table_name == "coding_submissions":
                mock_coding.select.return_value = mock_coding
                return mock_coding
            return builder

        self.mock_db.table.side_effect = table_router

        resp = self.client.get("/api/superadmin/students")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        # Admin must be filtered out
        self.assertEqual(len(data), 2)

        # Check B2C Candidate
        b2c_candidate = next((s for s in data if s["id"] == "b2c_user_1"), None)
        self.assertIsNotNone(b2c_candidate)
        self.assertEqual(b2c_candidate["organization_name"], "Direct / B2C Learner")
        self.assertEqual(b2c_candidate["college"], "Direct / B2C Learner")
        self.assertIsNone(b2c_candidate["organization_id"])
        self.assertEqual(b2c_candidate["resume_score"], 78.5)
        self.assertTrue(b2c_candidate["resume_uploaded"])
        self.assertEqual(b2c_candidate["total_coding_tests"], 1)
        self.assertEqual(b2c_candidate["coding_score"], 100.0)

        # Check Org Candidate
        org_candidate = next((s for s in data if s["id"] == "org_user_2"), None)
        self.assertIsNotNone(org_candidate)
        self.assertEqual(org_candidate["organization_name"], "Apex University")
        self.assertEqual(org_candidate["roll_number"], "CS-101")

    @patch("app.verify_super_admin", return_value=True)
    def test_qbank_empty_database_returns_empty_array(self, mock_auth):
        """When question_bank table is empty, GET /api/superadmin/qbank returns [] without fake questions."""
        mock_builder = MagicMock()
        mock_builder.select.return_value = mock_builder
        mock_builder.execute.return_value.data = []
        self.mock_db.table.return_value = mock_builder

        resp = self.client.get("/api/superadmin/qbank")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    @patch("app.verify_super_admin", return_value=True)
    def test_qbank_crud_lifecycle(self, mock_auth):
        """Question Bank POST, PUT, DELETE write directly to database."""
        # 1. POST
        mock_insert_builder = MagicMock()
        self.mock_db.table.return_value = mock_insert_builder

        payload = {
            "title": "Explain MVCC in PostgreSQL",
            "category": "Technical",
            "difficulty": "Medium",
            "solution": "Multi-Version Concurrency Control keeps row versions via xmin/xmax."
        }
        post_resp = self.client.post("/api/superadmin/qbank", json=payload)
        self.assertEqual(post_resp.status_code, 201)
        q = post_resp.get_json()["question"]
        self.assertEqual(q["title"], payload["title"])
        self.mock_db.table.assert_called_with("question_bank")

        # 2. PUT
        mock_update_builder = MagicMock()
        mock_update_builder.update.return_value = mock_update_builder
        mock_update_builder.eq.return_value = mock_update_builder
        self.mock_db.table.return_value = mock_update_builder

        put_resp = self.client.put(f"/api/superadmin/qbank/{q['id']}", json={"difficulty": "Hard"})
        self.assertEqual(put_resp.status_code, 200)

        # 3. DELETE
        mock_delete_builder = MagicMock()
        mock_delete_builder.delete.return_value = mock_delete_builder
        mock_delete_builder.eq.return_value = mock_delete_builder
        self.mock_db.table.return_value = mock_delete_builder

        del_resp = self.client.delete(f"/api/superadmin/qbank/{q['id']}")
        self.assertEqual(del_resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
