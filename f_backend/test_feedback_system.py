import unittest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from app import app, supabase

class FeedbackSystemTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_complete_feedback_flow(self):
        # 1. Submit Feedback as Student
        fb_payload = {
            "submitted_by": "test_student_101",
            "submitted_by_role": "Student",
            "organization_id": "org_stanford_01",
            "subject": "AI Interview Voice Latency Issue",
            "category": "Bug Report",
            "rating": 4,
            "message": "Encountered 2-second audio latency during System Design question #2.",
            "screenshot_url": "/uploads/feedback/demo_screenshot.png"
        }
        res_submit = self.app.post('/api/feedback', data=json.dumps(fb_payload), content_type='application/json')
        self.assertEqual(res_submit.status_code, 201)
        sub_data = json.loads(res_submit.data)
        self.assertIn("message", sub_data)
        self.assertEqual(sub_data["message"], "Thank you for your feedback. Your response has been submitted successfully.")
        fb_id = sub_data["feedback"]["id"]
        self.assertTrue(fb_id.startswith("fb_"))

        # 2. Fetch My Feedback
        res_my = self.app.get(f'/api/feedback/my?user_id=test_student_101')
        self.assertEqual(res_my.status_code, 200)
        my_list = json.loads(res_my.data)
        self.assertTrue(any(f["id"] == fb_id for f in my_list))

        # 3. Update My Feedback (Before Resolved)
        res_update_my = self.app.put(f'/api/feedback/my/{fb_id}', data=json.dumps({"subject": "Updated Voice Latency Title"}), content_type='application/json')
        self.assertEqual(res_update_my.status_code, 200)

        # 4. Super Admin Fetch All Feedback & Analytics
        headers_sa = {"X-Super-Admin": "true"}
        res_admin_list = self.app.get('/api/admin/feedback', headers=headers_sa)
        self.assertEqual(res_admin_list.status_code, 200)
        admin_data = json.loads(res_admin_list.data)
        self.assertIn("summary", admin_data)
        self.assertIn("analytics", admin_data)
        self.assertIn("feedback", admin_data)
        self.assertGreaterEqual(admin_data["summary"]["total_feedback"], 1)

        # 5. Super Admin Update Status, Priority & Admin Notes
        res_admin_update = self.app.put(f'/api/admin/feedback/{fb_id}', headers=headers_sa, data=json.dumps({
            "status": "In Progress",
            "priority": "High",
            "admin_notes": "Assigned to WebRTC engineering team for investigation."
        }), content_type='application/json')
        self.assertEqual(res_admin_update.status_code, 200)

        # 6. Verify Super Admin Detail
        res_admin_detail = self.app.get(f'/api/admin/feedback/{fb_id}', headers=headers_sa)
        self.assertEqual(res_admin_detail.status_code, 200)
        detail_data = json.loads(res_admin_detail.data)
        self.assertEqual(detail_data["status"], "In Progress")
        self.assertEqual(detail_data["priority"], "High")
        self.assertEqual(detail_data["admin_notes"], "Assigned to WebRTC engineering team for investigation.")

        # 7. Super Admin Delete Feedback
        res_delete = self.app.delete(f'/api/admin/feedback/{fb_id}', headers=headers_sa)
        self.assertEqual(res_delete.status_code, 200)

if __name__ == '__main__':
    unittest.main()
