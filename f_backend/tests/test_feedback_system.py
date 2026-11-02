import unittest
import json
import os
import sys
import io
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, _get_jwt_secret

class TestFeedbackSystem(unittest.TestCase):
    """Unit tests for the Student, Org Admin, and Super Admin Feedback lifecycle."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.sa_token = jwt.encode({"sub": "sa_01", "role": "SUPER_ADMIN"}, _get_jwt_secret(), algorithm="HS256")
        self.sa_headers = {"Authorization": f"Bearer {self.sa_token}"}

    def test_complete_feedback_flow(self):
        # 1. Submit Feedback as Candidate / Student
        fb_payload = {
            "submitted_by": "test_student_101",
            "name": "Test Student",
            "email": "student@stanford.edu",
            "role": "Candidate",
            "organization": "Stanford University",
            "subject": "AI Interview Voice Latency Issue",
            "category": "Bug Report",
            "rating": 4,
            "message": "Encountered 2-second audio latency during System Design question #2."
        }
        res_submit = self.app.post('/api/feedback', data=json.dumps(fb_payload), content_type='application/json')
        self.assertEqual(res_submit.status_code, 201)
        sub_data = json.loads(res_submit.data)
        self.assertIn("message", sub_data)
        fb_id = sub_data["feedback"]["id"]
        self.assertTrue(fb_id.startswith("FB-"))

        # 2. Fetch Admin Feedback List & Analytics
        res_admin_list = self.app.get('/api/admin/feedback', headers=self.sa_headers)
        self.assertEqual(res_admin_list.status_code, 200)
        admin_data = json.loads(res_admin_list.data)
        self.assertIn("summary", admin_data)
        self.assertIn("feedback", admin_data)
        self.assertGreaterEqual(admin_data["summary"]["total_feedback"], 1)
        self.assertTrue(any(f["id"] == fb_id for f in admin_data["feedback"]))

        # 3. Update Feedback Status & Priority
        res_update = self.app.put(
            f'/api/admin/feedback/{fb_id}',
            headers=self.sa_headers,
            data=json.dumps({
                "status": "In Progress",
                "priority": "High"
            }),
            content_type='application/json'
        )
        self.assertEqual(res_update.status_code, 200)

        # 4. Fetch Specific Feedback Detail
        res_detail = self.app.get(f'/api/admin/feedback/{fb_id}', headers=self.sa_headers)
        self.assertEqual(res_detail.status_code, 200)
        detail_data = json.loads(res_detail.data)
        self.assertEqual(detail_data["status"], "In Progress")
        self.assertEqual(detail_data["priority"], "High")

        # 5. Delete Feedback Record
        res_delete = self.app.delete(f'/api/admin/feedback/{fb_id}', headers=self.sa_headers)
        self.assertEqual(res_delete.status_code, 200)

        # 6. Verify Deletion
        res_after = self.app.get(f'/api/admin/feedback/{fb_id}', headers=self.sa_headers)
        self.assertEqual(res_after.status_code, 404)

    def test_feedback_upload_endpoint(self):
        """Test screenshot attachment upload endpoint."""
        token = jwt.encode({"sub": "student_1", "role": "STUDENT"}, _get_jwt_secret(), algorithm="HS256")
        data = {"file": (io.BytesIO(b"dummy image data"), "screenshot.png")}
        res = self.app.post(
            '/api/feedback/upload',
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            content_type="multipart/form-data"
        )
        self.assertIn(res.status_code, (200, 201))
        data = json.loads(res.data)
        self.assertIn("url", data)

if __name__ == '__main__':
    unittest.main()
