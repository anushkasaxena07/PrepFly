import unittest
import json
import os
import sys
import uuid
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, supabase, _get_jwt_secret

class TestSupportAndFeedbackIntegration(unittest.TestCase):
    """End-to-End Integration tests for Candidate Feedback, Super Admin Analytics, and Org Admin Support Tickets."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.org_id = f"org_test_{uuid.uuid4().hex[:8]}"
        self.sa_token = jwt.encode({"sub": "sa_01", "role": "SUPER_ADMIN"}, _get_jwt_secret(), algorithm="HS256")
        self.sa_headers = {"Authorization": f"Bearer {self.sa_token}"}
        self.org_token = jwt.encode({"sub": "admin_01", "role": "Organization Admin", "organization_id": self.org_id}, _get_jwt_secret(), algorithm="HS256")
        self.org_headers = {"Authorization": f"Bearer {self.org_token}"}

    def test_candidate_feedback_and_superadmin_triage_flow(self):
        """Integration: Candidate submits feedback -> Super Admin queries list -> Updates status to Resolved -> Deletes."""
        # 1. Candidate submits feedback
        sub_res = self.client.post("/api/feedback", json={
            "submitted_by": "Candidate Jane",
            "name": "Jane Doe",
            "email": "jane.doe@university.edu",
            "role": "Candidate",
            "organization": "Engineering College",
            "category": "Bug Report",
            "subject": "Audio stutter during technical interview",
            "message": "Encountered brief audio buffer drops while speaking response.",
            "rating": 4
        })
        self.assertEqual(sub_res.status_code, 201)
        sub_data = sub_res.get_json()
        fb_id = sub_data["feedback"]["id"]
        self.assertTrue(fb_id.startswith("FB-"))

        # 2. Super Admin views feedback analytics
        admin_list = self.client.get("/api/admin/feedback", headers=self.sa_headers)
        self.assertEqual(admin_list.status_code, 200)
        list_data = admin_list.get_json()
        self.assertIn("summary", list_data)
        self.assertTrue(any(f["id"] == fb_id for f in list_data["feedback"]))

        # 3. Super Admin changes status to 'In Review' and priority to 'High'
        up_res = self.client.put(f"/api/admin/feedback/{fb_id}", headers=self.sa_headers, json={
            "status": "In Review",
            "priority": "High"
        })
        self.assertEqual(up_res.status_code, 200)

        # 4. Fetch detail
        detail_res = self.client.get(f"/api/admin/feedback/{fb_id}", headers=self.sa_headers)
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.get_json()
        self.assertEqual(detail["status"], "In Review")
        self.assertEqual(detail["priority"], "High")

        # 5. Clean up by deleting
        del_res = self.client.delete(f"/api/admin/feedback/{fb_id}", headers=self.sa_headers)
        self.assertEqual(del_res.status_code, 200)

    def test_org_admin_ticket_and_superadmin_reply_flow(self):
        """Integration: Org Admin opens support ticket -> Super Admin replies -> Org Admin reads history."""
        # 1. Org Admin opens a ticket
        ticket_res = self.client.post(
            "/api/support/conversations",
            headers=self.org_headers,
            json={
                "subject": "Inquiry regarding student batch upload quota",
                "category": "Feature Request",
                "priority": "Normal",
                "message": "We have 400 new batch candidates to upload this semester."
            }
        )
        self.assertEqual(ticket_res.status_code, 201)
        t_data = ticket_res.get_json()
        conv_id = t_data["conversation"]["id"]
        self.assertEqual(t_data["conversation"]["status"], "Open")

        # 2. Super Admin views ticket
        sa_res = self.client.get("/api/support/conversations", headers=self.sa_headers)
        self.assertEqual(sa_res.status_code, 200)
        convs = sa_res.get_json()
        self.assertTrue(any(c["id"] == conv_id for c in convs))

        # 3. Super Admin sends response message
        reply_res = self.client.post(
            f"/api/support/conversations/{conv_id}/messages",
            headers=self.sa_headers,
            json={"message": "Your enterprise batch limit has been upgraded to 1,000 students."}
        )
        self.assertEqual(reply_res.status_code, 201)

        # 4. Org Admin retrieves conversation thread
        thread_res = self.client.get(
            f"/api/support/conversations/{conv_id}",
            headers=self.org_headers
        )
        self.assertEqual(thread_res.status_code, 200)
        thread = thread_res.get_json()
        self.assertEqual(len(thread["messages"]), 2)
        self.assertEqual(thread["messages"][1]["sender_role"], "Super Admin")

        # 5. Verify Student Role is strictly forbidden from support ticket routes
        student_token = jwt.encode(
            {"sub": "student_test_101", "role": "STUDENT"},
            _get_jwt_secret(),
            algorithm="HS256"
        )
        stud_res = self.client.get(
            "/api/support/conversations",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        self.assertEqual(stud_res.status_code, 403)

if __name__ == "__main__":
    unittest.main()
