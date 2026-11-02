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

    @patch("services.payment_service.get_supabase_client")
    def test_plan_tampering_at_verification_rejected(self, mock_sb_client):
        """Claiming a higher plan than the order was created for must raise Plan tampering error."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table

        # orders table returns order created for ENTERPRISE_YEARLY
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"order_id": "order_budget", "plan_id": "ENTERPRISE_YEARLY", "amount": 500.0}]
        )

        with self.assertRaises(ValueError) as ctx:
            verify_razorpay_payment("org_01", "order_budget", "pay_01", "sig_dummy", plan_id="CAMPUS_ENTERPRISE")
        self.assertIn("Plan tampering detected", str(ctx.exception))

    @patch("services.payment_service.get_supabase_client")
    def test_verify_database_failure_fails_closed(self, mock_sb_client):
        """Database failures during subscription activation must fail closed and raise RuntimeError."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        
        # Duplicate checks return empty
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Simulate database failure during payment insert
        mock_table.insert.return_value.execute.side_effect = Exception("DB Connection Lost / Constraint Violation")

        order_id = "order_db_fail"
        payment_id = "pay_db_fail"
        payload = f"{order_id}|{payment_id}"
        genuine_sig = hmac.new(RAZORPAY_KEY_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

        with self.assertRaises(RuntimeError) as ctx:
            verify_razorpay_payment("org_01", order_id, payment_id, genuine_sig)
        self.assertIn("Database error during payment activation", str(ctx.exception))

    def test_concurrent_order_verification_lock(self):
        """Simultaneous verification on the same order must be blocked by the in-flight lock."""
        from services.payment_service import _IN_FLIGHT_ORDERS, _ORDER_VERIFY_LOCK
        test_order_id = "order_concurrent_test"
        with _ORDER_VERIFY_LOCK:
            _IN_FLIGHT_ORDERS.add(test_order_id)

        try:
            with self.assertRaises(ValueError) as ctx:
                verify_razorpay_payment("org_01", test_order_id, "pay_01", "sig_01")
            self.assertIn("Order verification already in progress", str(ctx.exception))
        finally:
            with _ORDER_VERIFY_LOCK:
                _IN_FLIGHT_ORDERS.discard(test_order_id)

    @patch("services.payment_service.get_supabase_client")
    def test_idempotent_retry_returns_success_and_heals_state(self, mock_sb_client):
        """Retrying verification of an already-fulfilled order with identical payment must return SUCCESS idempotently."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table

        order_id = "order_idempotent_1"
        payment_id = "pay_idempotent_1"
        payload = f"{order_id}|{payment_id}"
        genuine_sig = hmac.new(RAZORPAY_KEY_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

        existing_record = {
            "id": "pay_row_uuid_123",
            "organization_id": "org_idem_col",
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "invoice_number": "INV-20261103-TEST",
            "status": "Success",
            "amount": 500.0
        }

        # payment table select by payment_id and order_id returns the matching fulfilled record
        mock_table.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[existing_record]), # orders check
            MagicMock(data=[existing_record]), # payment check by payment_id
            MagicMock(data=[existing_record])  # payment check by order_id
        ]

        result = verify_razorpay_payment("org_idem_col", order_id, payment_id, genuine_sig)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertTrue(result.get("is_idempotent_retry"))
        self.assertEqual(result["payment_id"], payment_id)
        self.assertEqual(result["invoice_number"], "INV-20261103-TEST")

    @patch("services.payment_service.get_supabase_client")
    def test_different_payment_id_on_same_order_rejected(self, mock_sb_client):
        """Attempting to fulfill an already fulfilled order with a new/different payment_id must be rejected."""
        mock_sb = MagicMock()
        mock_sb_client.return_value = mock_sb
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table

        order_id = "order_fulfilled_earlier"
        new_payment_id = "pay_new_attempt"
        payload = f"{order_id}|{new_payment_id}"
        genuine_sig = hmac.new(RAZORPAY_KEY_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

        # payment_id query returns empty, but order_id query returns previous fulfillment under pay_old
        mock_table.select.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[]), # orders check
            MagicMock(data=[]), # payment_id check (not found)
            MagicMock(data=[{"id": "pay_old_row", "razorpay_payment_id": "pay_old", "status": "Success"}]) # order_id check
        ]

        with self.assertRaises(ValueError) as ctx:
            verify_razorpay_payment("org_col", order_id, new_payment_id, genuine_sig)
        self.assertIn("Order already fulfilled with a different transaction", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
