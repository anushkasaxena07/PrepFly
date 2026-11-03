import unittest
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, supabase

class TestOrgAdminLifecycleIntegration(unittest.TestCase):
    """End-to-End Integration tests for Organization Admin authentication, Question Bank, and Organization Settings."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.org_id = f"org_test_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        try:
            supabase.table("question_bank").delete().eq("organization_id", self.org_id).execute()
        except Exception:
            pass

    def test_org_admin_login_and_qbank_management_lifecycle(self):
        """Integration: Org Admin Login -> Add Question -> Broadcast Notification -> List -> Update -> Delete."""
        # 1. Admin Login
        login_res = self.client.post("/api/admin/login", json={
            "email": "admin@stanford.edu",
            "password": "mock_org_admin_pass_2026"
        })
        self.assertEqual(login_res.status_code, 200)
        auth_data = login_res.get_json()
        self.assertIn("access_token", auth_data)
        admin_token = auth_data["access_token"]
        self.assertIn("role", auth_data["admin"])

        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": self.org_id
        }

        # 2. Add Practice Question to Org Question Bank
        add_res = self.client.post("/api/admin/question-bank", headers=headers, json={
            "title": "Design a Distributed Message Broker (Kafka Clone)",
            "category": "Technical",
            "difficulty": "Hard",
            "description": "Explain partition replication, consumer group rebalancing, and write acks.",
            "solution": "Use append-only commit logs, Raft/KRaft metadata quorum, and zero-copy OS transfers."
        })
        self.assertEqual(add_res.status_code, 201)
        add_data = add_res.get_json()
        self.assertIn("question", add_data)
        q_id = add_data["question"]["id"]
        self.assertIn("notification", add_data)

        # 3. List Question Bank items
        list_res = self.client.get("/api/admin/question-bank", headers=headers)
        self.assertEqual(list_res.status_code, 200)
        questions = list_res.get_json()
        self.assertTrue(any(q["id"] == q_id for q in questions))

        # 4. Update Question (Change Difficulty and Description)
        up_res = self.client.put(
            f"/api/admin/question-bank/{q_id}",
            headers=headers,
            json={"difficulty": "Expert"}
        )
        self.assertEqual(up_res.status_code, 200)

        # 5. Admin Settings Retrieval and Update
        settings_get = self.client.get("/api/admin/settings", headers=headers)
        self.assertEqual(settings_get.status_code, 200)
        s_data = settings_get.get_json()
        self.assertIn("two_factor_enabled", s_data)

        settings_save = self.client.post("/api/admin/settings", headers=headers, json={
            "theme": "Dark Modern",
            "email_notifications": True
        })
        self.assertEqual(settings_save.status_code, 200)

        # 6. Delete Question from Bank
        del_res = self.client.delete(f"/api/admin/question-bank/{q_id}", headers=headers)
        self.assertEqual(del_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
