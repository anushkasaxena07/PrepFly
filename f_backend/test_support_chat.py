import unittest
import json
from app import app

class TestSupportChat(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_student_blocked(self):
        # Simulate student JWT or student role call
        import jwt, os
        token = jwt.encode({"sub": "student_1", "role": "STUDENT"}, app.config.get("JWT_SECRET_KEY", "super-secret-key-123"), algorithm="HS256")
        res = self.client.get("/api/support/conversations", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 403)

    def test_org_admin_create_and_reply_flow(self):
        # 1. Org Admin creates conversation
        res = self.client.post("/api/support/conversations", 
            headers={"X-Organization-Id": "org_stanford_01"},
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
        sa_res = self.client.get("/api/support/conversations", headers={"X-Super-Admin": "true"})
        self.assertEqual(sa_res.status_code, 200)
        sa_convs = sa_res.get_json()
        self.assertTrue(any(c["id"] == conv_id for c in sa_convs))

        # 3. Super Admin replies
        reply_res = self.client.post(f"/api/support/conversations/{conv_id}/messages",
            headers={"X-Super-Admin": "true"},
            json={"message": "Thanks for reporting! We are increasing WebRTC buffer size."}
        )
        self.assertEqual(reply_res.status_code, 201)

        # 4. Super Admin updates status to In Progress & priority to Urgent
        status_res = self.client.put(f"/api/support/conversations/{conv_id}",
            headers={"X-Super-Admin": "true"},
            json={"status": "In Progress", "priority": "Urgent"}
        )
        self.assertEqual(status_res.status_code, 200)

        # 5. Org Admin fetches detail & checks read status
        detail_res = self.client.get(f"/api/support/conversations/{conv_id}", headers={"X-Organization-Id": "org_stanford_01"})
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.get_json()
        self.assertEqual(len(detail["messages"]), 2)
        self.assertEqual(detail["conversation"]["status"], "In Progress")
        self.assertEqual(detail["conversation"]["priority"], "Urgent")

        # 6. Check unread count
        unread_res = self.client.get("/api/support/unread-count", headers={"X-Organization-Id": "org_stanford_01"})
        self.assertEqual(unread_res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
