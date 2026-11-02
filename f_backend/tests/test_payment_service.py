import unittest
import os
import sys
import hmac
import hashlib
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.payment_service import (
    create_razorpay_order,
    verify_razorpay_payment,
    RAZORPAY_KEY_SECRET,
    RAZORPAY_KEY_ID
)

class TestPaymentService(unittest.TestCase):
    """Unit tests for Razorpay Order Creation and Cryptographic Verification."""

    def test_create_razorpay_order_currency_and_paise(self):
        """Order creation should convert INR to paise correctly and specify INR currency."""
        order = create_razorpay_order("org_test_101", amount_inr=500.0)
        self.assertIn("order_id", order)
        self.assertEqual(order["amount"], 50000)  # 500 INR in paise
        self.assertEqual(order["amount_inr"], 500.0)
        self.assertEqual(order["currency"], "INR")
        self.assertEqual(order["key_id"], RAZORPAY_KEY_ID)

    def test_verify_razorpay_payment_missing_arguments(self):
        """Missing verification parameters must raise ValueError."""
        with self.assertRaises(ValueError):
            verify_razorpay_payment("org_01", None, "pay_123", "sig_123")

        with self.assertRaises(ValueError):
            verify_razorpay_payment("org_01", "order_123", "", "sig_123")

        with self.assertRaises(ValueError):
            verify_razorpay_payment("org_01", "order_123", "pay_123", None)

    @patch("services.payment_service.get_supabase_client")
    def test_verify_razorpay_payment_duplicate_replay_attack(self, mock_sb_client):
        """Replaying an existing payment_id must be rejected as duplicate."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        # Simulate payment already existing
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{"id": "existing_pay"}])

        with self.assertRaises(ValueError) as ctx:
            verify_razorpay_payment("org_01", "order_test", "pay_already_processed", "sig_valid_test")
        self.assertIn("Duplicate payment", str(ctx.exception))

    @patch("services.payment_service.get_supabase_client")
    def test_verify_razorpay_payment_invalid_hmac_rejected(self, mock_sb_client):
        """Invalid cryptographic HMAC signature must be rejected."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])

        with self.assertRaises(ValueError) as ctx:
            verify_razorpay_payment("org_01", "order_100", "pay_200", "invalid_forged_signature_xyz")
        self.assertIn("signature verification failed", str(ctx.exception))

    @patch("services.payment_service.get_supabase_client")
    def test_verify_razorpay_payment_valid_hmac_sha256(self, mock_sb_client):
        """Genuine HMAC SHA256 signature calculated from secret must verify and activate subscription."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[])

        order_id = "order_test_999"
        payment_id = "pay_test_999"
        payload = f"{order_id}|{payment_id}"
        genuine_sig = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        result = verify_razorpay_payment("org_test_999", order_id, payment_id, genuine_sig)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["subscription_status"], "ACTIVE")
        self.assertIn("invoice_number", result)
        self.assertIn("invoice_id", result)

    def test_create_razorpay_order_unauthorized_amount_rejected(self):
        """Arbitrary client amounts (e.g. INR 1.0 or INR 99.0) must be rejected with ValueError."""
        with self.assertRaises(ValueError) as ctx:
            create_razorpay_order("org_test_hack", amount_inr=1.0)
        self.assertIn("Unauthorized payment amount", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            create_razorpay_order("org_test_hack", amount_inr="invalid_amount")
        self.assertIn("Invalid amount specified", str(ctx.exception))

    def test_plan_mapping_price_mismatch_rejected(self):
        """Requesting an expensive plan with a tampered low amount must be rejected."""
        with self.assertRaises(ValueError) as ctx:
            create_razorpay_order("org_tamper", plan_id="CAMPUS_ENTERPRISE", amount_inr=500.0)
        self.assertIn("Price mismatch", str(ctx.exception))

    @patch("services.payment_service.get_supabase_client")
    def test_verify_duplicate_order_fulfillment_rejected(self, mock_sb_client):
        """Fulfilling an order that is already fulfilled must be rejected."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        
        # 1st query (payment_id check): []
        # 2nd query (order_id check): [{"status": "Success"}]
        mock_table.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[]),
            MagicMock(data=[{"id": "existing_pay", "status": "Success"}])
        ]

        with self.assertRaises(ValueError) as ctx:
            verify_razorpay_payment("org_01", "order_already_fulfilled", "pay_new", "sig_dummy")
        self.assertIn("Order already fulfilled", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
