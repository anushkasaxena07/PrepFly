import unittest
import json
import os
import sys
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, _get_jwt_secret

class TestSupportChat(unittest.TestCase):
    """Unit tests for Support Chat RBAC, Org Admin ticket creation, and Super Admin messaging."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_student_blocked_from_org_support(self):
        """Students should be blocked with 403 Forbidden from accessing org admin support tickets."""
        token = jwt.encode(
            {"sub": "student_1", "role": "STUDENT"},
            _get_jwt_secret(),
            algorithm="HS256"
        )
        res = self.client.get("/api/support/conversations", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 403)

    def test_org_admin_create_and_superadmin_reply_flow(self):
        """Org Admin opens conversation, Super Admin replies and updates status."""
        org_token = jwt.encode(
            {"sub": "admin_01", "role": "Organization Admin", "organization_id": "org_stanford_01"},
            _get_jwt_secret(),
            algorithm="HS256"
        )
        sa_token = jwt.encode(
            {"sub": "sa_01", "role": "SUPER_ADMIN"},
            _get_jwt_secret(),
            algorithm="HS256"
        )

        # 1. Org Admin creates conversation
        res = self.client.post(
            "/api/support/conversations",
            headers={"Authorization": f"Bearer {org_token}"},
            json={
                "subject": "Audio lag during AI Interview",
                "category": "Report Bug",
                "priority": "High",
                "message": "We experienced 3s delay during live candidate evaluation."
            }
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        conv_id = data["conversation"]["id"]
        self.assertIsNotNone(conv_id)
        self.assertEqual(data["conversation"]["status"], "Open")

        # 2. Super Admin views all conversations
        sa_res = self.client.get("/api/support/conversations", headers={"Authorization": f"Bearer {sa_token}"})
        self.assertEqual(sa_res.status_code, 200)
        sa_convs = sa_res.get_json()
        self.assertTrue(any(c["id"] == conv_id for c in sa_convs))

        # 3. Super Admin replies
        reply_res = self.client.post(
            f"/api/support/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {sa_token}"},
            json={"message": "Thanks for reporting! We are increasing WebRTC buffer size."}
        )
        self.assertEqual(reply_res.status_code, 201)

        # 4. Super Admin updates status to In Progress & priority to Urgent
        status_res = self.client.put(
            f"/api/support/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {sa_token}"},
            json={"status": "In Progress", "priority": "Urgent"}
        )
        self.assertEqual(status_res.status_code, 200)

        # 5. Org Admin fetches detail & checks updated values
        detail_res = self.client.get(
            f"/api/support/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {org_token}"}
        )
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.get_json()
        self.assertEqual(len(detail["messages"]), 2)
        self.assertEqual(detail["conversation"]["status"], "In Progress")
        self.assertEqual(detail["conversation"]["priority"], "Urgent")

        # 6. Check unread count endpoint
        unread_res = self.client.get(
            "/api/support/unread-count",
            headers={"Authorization": f"Bearer {org_token}"}
        )
        self.assertEqual(unread_res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
