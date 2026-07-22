import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.subscription_service import get_org_subscription_status, block_if_expired
from services.payment_service import create_razorpay_order, verify_razorpay_payment
from services.invoice_service import get_invoice_html
from services.webhook_service import handle_razorpay_webhook

def run_tests():
    print("--- 1. Testing Free Trial Initialization (10 Days) ---")
    org_id = f"test_org_{int(datetime.utcnow().timestamp())}"
    status = get_org_subscription_status(org_id)
    print("Status Result:", status["subscription_status"])
    print("Days Remaining:", status["days_remaining"])
    assert status["subscription_status"] == "TRIAL"
    assert status["days_remaining"] == 10
    assert status["is_blocked"] == False
    print("[OK] Free trial test passed!")

    print("\n--- 2. Testing Razorpay Order Creation ---")
    order = create_razorpay_order(org_id=org_id, amount_inr=500.0)
    print("Order ID:", order["order_id"])
    print("Amount (paise):", order["amount"])
    assert order["amount"] == 50000
    assert order["currency"] == "INR"
    print("[OK] Order creation test passed!")

    print("\n--- 3. Testing Razorpay Server Verification & Activation ---")
    ver_res = verify_razorpay_payment(
        org_id=org_id,
        razorpay_order_id=order["order_id"],
        razorpay_payment_id=f"pay_test_{int(datetime.utcnow().timestamp())}",
        razorpay_signature="sig_valid_test_verification"
    )
    print("Verification Status:", ver_res["status"])
    print("Invoice Number:", ver_res["invoice_number"])
    assert ver_res["status"] == "SUCCESS"
    assert ver_res["subscription_status"] == "ACTIVE"
    print("[OK] Verification and 1-Year activation test passed!")

    print("\n--- 4. Testing Post-Activation Status ---")
    active_status = get_org_subscription_status(org_id)
    print("New Subscription Status:", active_status["subscription_status"])
    print("New Plan:", active_status["current_plan"])
    assert active_status["subscription_status"] == "ACTIVE"
    assert active_status["current_plan"] == "Premium"
    assert active_status["is_blocked"] == False
    print("[OK] Post-activation status test passed!")

    print("\n--- 5. Testing Invoice HTML Generation ---")
    inv_html, code = get_invoice_html(ver_res["invoice_id"])
    assert code == 200
    assert "Official Invoice" in inv_html or "OFFICIAL INVOICE" in inv_html
    print("[OK] Invoice generation test passed!")

    print("\n[SUCCESS] ALL PAYMENT AND SUBSCRIPTION SYSTEM TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
