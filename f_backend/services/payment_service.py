import os
import hmac
import hashlib
import sqlite3
import uuid
from datetime import datetime, timedelta
from local_supabase import DB_FILE, SQLiteSupabaseMock

import secrets

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

def get_supabase_client():
    try:
        from app import supabase
        return supabase
    except Exception:
        return SQLiteSupabaseMock()

SUBSCRIPTION_PLANS = {
    "ENTERPRISE_YEARLY": {
        "id": "ENTERPRISE_YEARLY",
        "name": "Premium",
        "amount": 500.0,
        "currency": "INR",
        "duration_days": 365,
        "description": "1-Year Premium Annual Subscription"
    },
    "PRO_YEARLY": {
        "id": "PRO_YEARLY",
        "name": "Pro Plan",
        "amount": 2500.0,
        "currency": "INR",
        "duration_days": 365,
        "description": "1-Year Pro Annual Subscription"
    },
    "CAMPUS_ENTERPRISE": {
        "id": "CAMPUS_ENTERPRISE",
        "name": "Campus Enterprise Scale",
        "amount": 25000.0,
        "currency": "INR",
        "duration_days": 365,
        "description": "1-Year Campus Enterprise Scale"
    }
}
ALLOWED_PLAN_AMOUNTS = {p["amount"] for p in SUBSCRIPTION_PLANS.values()}

def resolve_plan(plan_id=None, amount_inr=None):
    """Authoritative server-side plan resolver. Maps plan_id or amount to valid plan object."""
    if plan_id and plan_id in SUBSCRIPTION_PLANS:
        plan = SUBSCRIPTION_PLANS[plan_id]
        if amount_inr is not None:
            try:
                amt = float(amount_inr)
                if amt != plan["amount"]:
                    raise ValueError(f"Price mismatch: Plan '{plan_id}' costs INR {plan['amount']}, but INR {amt} was specified.")
            except (TypeError, ValueError) as ex:
                if "Price mismatch" in str(ex):
                    raise
                raise ValueError("Invalid amount specified.")
        return plan

    if plan_id and plan_id not in SUBSCRIPTION_PLANS:
        raise ValueError(f"Unknown subscription plan: '{plan_id}'. Allowed plans: {list(SUBSCRIPTION_PLANS.keys())}")

    if amount_inr is not None:
        try:
            amt = float(amount_inr)
        except (TypeError, ValueError):
            raise ValueError("Invalid amount specified.")
        for p in SUBSCRIPTION_PLANS.values():
            if p["amount"] == amt:
                return p
        raise ValueError(f"Unauthorized payment amount: INR {amt}. Allowed subscription amounts: {sorted(list(ALLOWED_PLAN_AMOUNTS))}")

    return SUBSCRIPTION_PLANS["ENTERPRISE_YEARLY"]

def create_razorpay_order(org_id, plan_id=None, amount_inr=None):
    if plan_id is None and amount_inr is None:
        plan_id = "ENTERPRISE_YEARLY"
    plan = resolve_plan(plan_id=plan_id, amount_inr=amount_inr)
    amount_inr = plan["amount"]
    amount_paise = int(amount_inr * 100) # e.g. ₹500 = 50000 paise
    currency = plan.get("currency", "INR")

    order_id = f"order_{uuid.uuid4().hex[:14]}"

    try:
        import razorpay
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        rzp_order = client.order.create({
            "amount": amount_paise,
            "currency": currency,
            "receipt": f"rcpt_{org_id[:6]}_{plan['id'][:8]}",
            "payment_capture": 1
        })
        order_id = rzp_order.get("id", order_id)
    except Exception as e:
        print("Razorpay client notice (fallback order_id generated):", e)

    return {
        "order_id": order_id,
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "duration_days": plan["duration_days"],
        "amount": amount_paise,
        "amount_inr": amount_inr,
        "currency": currency,
        "key_id": RAZORPAY_KEY_ID
    }

def verify_razorpay_payment(org_id, razorpay_order_id, razorpay_payment_id, razorpay_signature, plan_id=None, amount_inr=None):
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        raise ValueError("Missing payment verification fields")

    plan = resolve_plan(plan_id=plan_id, amount_inr=amount_inr)
    amount_inr = plan["amount"]

    supabase = get_supabase_client()

    # 1. Prevent duplicate payments / replay attacks on payment_id
    try:
        res = supabase.table("payment").select("*").eq("razorpay_payment_id", razorpay_payment_id).execute()
        if res and hasattr(res, "data") and isinstance(res.data, list) and len(res.data) > 0:
            raise ValueError("Duplicate payment transaction detected")
    except Exception as e:
        if "Duplicate payment" in str(e):
            raise e

    # 2. Prevent duplicate order fulfillment on order_id
    try:
        res_ord = supabase.table("payment").select("*").eq("razorpay_order_id", razorpay_order_id).execute()
        rows = res_ord.data if (res_ord and hasattr(res_ord, "data") and isinstance(res_ord.data, list)) else []
        if any(r.get("status") == "Success" for r in rows if isinstance(r, dict)):
            raise ValueError("Order already fulfilled")
    except Exception as e:
        if "Order already fulfilled" in str(e):
            raise e

    # 3. Server-side HMAC Signature Verification
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    generated_sig = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    # Constant-time cryptographic HMAC verification
    is_valid = secrets.compare_digest(generated_sig, razorpay_signature)

    if not is_valid:
        raise ValueError("Razorpay signature verification failed! Payment rejected.")

    # 4. DATABASE UPDATE (Payment + Subscription Update + Invoice + Activity Log)
    now = datetime.utcnow()
    duration_days = plan.get("duration_days", 365)
    expiry = now + timedelta(days=duration_days)
    pay_id = f"pay_{uuid.uuid4().hex[:8]}"
    invoice_number = f"INV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    try:
        supabase.table("payment").insert({
            "id": pay_id,
            "organization_id": org_id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
            "plan_id": plan["id"],
            "amount": amount_inr,
            "currency": "INR",
            "invoice_number": invoice_number,
            "status": "Success",
            "payment_method": "Razorpay Standard Checkout",
            "created_at": now.isoformat()
        }).execute()

        supabase.table("organization").update({
            "subscription_status": "ACTIVE",
            "subscription_start": now.isoformat(),
            "subscription_expiry": expiry.isoformat(),
            "current_plan": plan["name"],
            "subscription_plan": plan["id"],
            "updated_at": now.isoformat()
        }).eq("id", org_id).execute()

        inv_id = f"inv_{uuid.uuid4().hex[:8]}"
        gst_amount = round(amount_inr * 0.18, 2)
        supabase.table("invoice").insert({
            "id": inv_id,
            "payment_id": pay_id,
            "organization_id": org_id,
            "invoice_number": invoice_number,
            "amount": amount_inr,
            "gst": gst_amount,
            "created_at": now.isoformat()
        }).execute()

        supabase.table("activity_logs").insert({
            "id": f"log_{uuid.uuid4().hex[:6]}",
            "actor_id": org_id,
            "actor_type": "ORGANIZATION_ADMIN",
            "action": f"Subscription Purchase Successful ({plan['name']} - ₹{amount_inr} / {duration_days} Days)",
            "ip_address": "127.0.0.1",
            "details": f"Razorpay Payment ID: {razorpay_payment_id} | Invoice: {invoice_number} | Plan: {plan['id']}",
            "created_at": now.isoformat()
        }).execute()

        inv_data = {"id": inv_id, "invoice_number": invoice_number}
    except Exception as db_err:
        print("Database insert notice:", db_err)
        inv_data = {"id": f"inv_{uuid.uuid4().hex[:8]}", "invoice_number": invoice_number}

    # 5. Dispatch Email Confirmation
    try:
        org_res = supabase.table("organization").select("email, name").eq("id", org_id).execute()
        org_row = org_res.data[0] if (org_res and hasattr(org_res, "data") and org_res.data) else {}
        target_email = org_row.get("email") if org_row.get("email") else os.getenv("DEFAULT_ALERT_EMAIL", "admin@organization.edu")
        org_name = org_row.get("name") if org_row.get("name") else "Organization Admin"
        
        send_payment_confirmation_email(
            recipient_email=target_email,
            org_name=org_name,
            invoice_number=inv_data["invoice_number"],
            amount=amount_inr,
            payment_id=razorpay_payment_id,
            expiry_date=expiry.strftime("%Y-%m-%d"),
            plan_name=plan["name"]
        )
    except Exception as em_err:
        print("Payment confirmation email notice:", em_err)

    return {
        "status": "SUCCESS",
        "message": f"Payment verified and {plan['name']} activated successfully!",
        "organization_id": org_id,
        "payment_id": razorpay_payment_id,
        "invoice_number": inv_data["invoice_number"],
        "invoice_id": inv_data["id"],
        "subscription_status": "ACTIVE",
        "current_plan": plan["name"],
        "plan_id": plan["id"],
        "amount_inr": amount_inr,
        "days_remaining": duration_days,
        "subscription_expiry": expiry.isoformat()
    }

def record_failed_payment(org_id, razorpay_order_id, razorpay_payment_id=None, reason="Payment Failed"):
    supabase = get_supabase_client()
    pay_id = f"pay_fail_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()
    
    try:
        supabase.table("payment").insert({
            "id": pay_id,
            "organization_id": org_id,
            "razorpay_order_id": razorpay_order_id or "order_failed",
            "razorpay_payment_id": razorpay_payment_id or f"pay_failed_{uuid.uuid4().hex[:6]}",
            "amount": 500.0,
            "currency": "INR",
            "invoice_number": f"FAILED-{now.strftime('%Y%m%d')}",
            "status": "Failed",
            "payment_method": "Razorpay Standard Checkout",
            "created_at": now.isoformat()
        }).execute()

        supabase.table("activity_logs").insert({
            "id": f"log_{uuid.uuid4().hex[:6]}",
            "actor_id": org_id,
            "actor_type": "ORGANIZATION_ADMIN",
            "action": f"Subscription Payment Failed: {reason}",
            "ip_address": "127.0.0.1",
            "details": f"Order ID: {razorpay_order_id} | Payment ID: {razorpay_payment_id}",
            "created_at": now.isoformat()
        }).execute()
    except Exception as e:
        print("Record failed notice:", e)

    return {"status": "FAILED_RECORDED", "reason": reason}

def send_payment_confirmation_email(recipient_email, org_name, invoice_number, amount, payment_id, expiry_date, plan_name="Enterprise Plan"):
    print(f"[EMAIL NOTIFICATION DISPATCHED] To: {recipient_email} | Org: {org_name} | Invoice: {invoice_number} | Amount: INR {amount} | Expiry: {expiry_date}")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_EMAIL")
    sender_pass = os.getenv("SENDER_PASSWORD") or os.getenv("SMTP_PASSWORD")

    if not sender_email or not sender_pass:
        return

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"👑 Payment Receipt & Subscription Activation - {invoice_number}"

    body = f"""
    Dear {org_name},

    Thank you for purchasing the PrepFly {plan_name} Subscription.

    Payment Details:
    ---------------------------------------------
    Invoice Number : {invoice_number}
    Payment ID     : {payment_id}
    Amount Paid    : ₹{amount:.2f} INR
    Plan           : {plan_name}
    Valid Until    : {expiry_date}

    Your organization and all enrolled students now have full access to AI Mock Interviews, Coding Test Environments, Resume ATS Scans, and Executive Reports.

    Regards,
    PrepFly Team
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL(smtp_server, 465, timeout=6) as server:
            server.login(sender_email, sender_pass)
            server.send_message(msg)
    except Exception:
        try:
            with smtplib.SMTP(smtp_server, 587, timeout=6) as server:
                server.starttls()
                server.login(sender_email, sender_pass)
                server.send_message(msg)
        except Exception as e:
            print(f"Receipt email notification notice: {e}")
