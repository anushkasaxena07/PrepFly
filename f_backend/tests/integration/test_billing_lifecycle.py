import unittest
import json
import os
import sys
import uuid
import hmac
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import jwt
from app import app, supabase, _get_jwt_secret
from services.subscription_service import get_org_subscription_status
from services.payment_service import create_razorpay_order, verify_razorpay_payment, RAZORPAY_KEY_SECRET

class TestBillingLifecycleIntegration(unittest.TestCase):
    """End-to-End Integration tests for Razorpay Order Creation, Verification, Subscription Activation, and Invoicing."""

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.org_id = f"test_college_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        try:
            supabase.table("organization").delete().eq("id", self.org_id).execute()
            supabase.table("payment").delete().eq("organization_id", self.org_id).execute()
            supabase.table("invoice").delete().eq("organization_id", self.org_id).execute()
        except Exception:
            pass

    def test_full_subscription_payment_and_invoice_workflow(self):
        """Integration flow: Initial Trial -> Razorpay Order -> HMAC Verification -> 365-Day Plan -> Invoice Retrieval."""
        # 1. Verify Initial Status is Free Trial
        init_status = get_org_subscription_status(self.org_id)
        self.assertEqual(init_status["subscription_status"], "TRIAL")
        self.assertEqual(init_status["days_remaining"], 10)
        self.assertFalse(init_status["is_blocked"])

        # 2. Org Admin initiates order creation
        order = create_razorpay_order(self.org_id, amount_inr=500.0)
        self.assertIn("order_id", order)
        self.assertEqual(order["amount"], 50000)
        order_id = order["order_id"]

        # 3. Simulate payment completion and HMAC cryptographic signature
        payment_id = f"pay_{uuid.uuid4().hex[:10]}"
        body = f"{order_id}|{payment_id}"
        genuine_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        # 4. Process payment verification & activation
        ver_res = verify_razorpay_payment(
            org_id=self.org_id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=genuine_signature
        )
        self.assertEqual(ver_res["status"], "SUCCESS")
        self.assertEqual(ver_res["subscription_status"], "ACTIVE")
        invoice_id = ver_res["invoice_id"]
        invoice_num = ver_res["invoice_number"]

        # 5. Check post-payment organization state
        active_status = get_org_subscription_status(self.org_id)
        self.assertEqual(active_status["subscription_status"], "ACTIVE")
        self.assertEqual(active_status["current_plan"], "Premium")
        self.assertFalse(active_status["is_blocked"])
        self.assertGreaterEqual(active_status["days_remaining"], 360)

        # 6. Fetch official generated invoice HTML
        admin_token = jwt.encode({"sub": "admin_test", "role": "Organization Admin", "organization_id": self.org_id}, _get_jwt_secret(), algorithm="HS256")
        inv_res = self.client.get(f"/api/invoice/{invoice_id}", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(inv_res.status_code, 200)
        self.assertIn("text/html", inv_res.content_type)
        html_str = inv_res.get_data(as_text=True)
        self.assertIn("PrepFly Enterprise", html_str)
        self.assertIn(invoice_num, html_str)
        self.assertIn("500", html_str)
        self.assertIn("90", html_str)  # 18% GST

        # 7. Replay attack rejection test: verifying same payment_id a second time must fail
        with self.assertRaises(ValueError) as ctx:
            verify_razorpay_payment(
                org_id=self.org_id,
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                razorpay_signature=genuine_signature
            )
        self.assertIn("Duplicate payment", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
