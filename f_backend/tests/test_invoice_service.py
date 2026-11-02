import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.invoice_service import (
    generate_invoice,
    get_invoice_html
)

class TestInvoiceService(unittest.TestCase):
    """Unit tests for Invoice generation, GST calculation, and HTML rendering."""

    @patch("services.invoice_service.get_supabase")
    def test_generate_invoice_calculations(self, mock_get_supabase):
        """Test invoice creation, 18% GST computation, and total amount summing."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        base_amount = 500.0
        expected_gst = round(500.0 * 0.18, 2)  # 90.0
        expected_total = round(base_amount + expected_gst, 2)  # 590.0

        inv = generate_invoice(org_id="org_test_01", payment_id="pay_test_01", amount=base_amount)
        self.assertIn("id", inv)
        self.assertIn("invoice_number", inv)
        self.assertEqual(inv["amount"], base_amount)
        self.assertEqual(inv["gst"], expected_gst)
        self.assertEqual(inv["total_amount"], expected_total)
        self.assertEqual(inv["organization_id"], "org_test_01")
        self.assertEqual(inv["payment_id"], "pay_test_01")

    @patch("services.invoice_service.get_supabase")
    def test_get_invoice_html_not_found_returns_404(self, mock_get_supabase):
        """Non-existent invoice ID should return 404 status."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb
        mock_sb.table().select().or_().execute.return_value = MagicMock(data=[])

        html, status_code = get_invoice_html("non_existent_invoice_999")
        self.assertEqual(status_code, 404)
        self.assertIn("Invoice Not Found", html)

    @patch("services.invoice_service.get_supabase")
    def test_get_invoice_html_renders_branding_and_details(self, mock_get_supabase):
        """Existing invoice renders official HTML with organization name, invoice number, and PrepFly branding."""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        # Mock invoice query
        mock_sb.table().select().or_().execute.return_value = MagicMock(data=[{
            "id": "inv_12345",
            "invoice_number": "INV-20261024-TEST",
            "organization_id": "org_harvard_01",
            "payment_id": "pay_98765",
            "amount": 500.0,
            "gst": 90.0,
            "created_at": "2026-10-24T00:00:00"
        }])

        # Mock org query
        mock_sb.table().select().eq().execute.return_value = MagicMock(data=[{
            "name": "Harvard Placement Cell",
            "email": "placement@harvard.edu"
        }])

        html, status_code = get_invoice_html("inv_12345")
        self.assertEqual(status_code, 200)
        self.assertIn("PrepFly Enterprise", html)
        self.assertIn("INV-20261024-TEST", html)
        self.assertIn("Harvard Placement Cell", html)

if __name__ == "__main__":
    unittest.main()
