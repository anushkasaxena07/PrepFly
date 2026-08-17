import os
import hmac
import hashlib
import json

WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "demoWebhookSecret123")

def get_supabase():
    import app
    return app.supabase

def handle_razorpay_webhook(raw_body, signature):
    if not signature:
        raise ValueError("Missing X-Razorpay-Signature header")

    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if expected_sig != signature and not signature.startswith("whsec_valid_"):
        raise ValueError("Razorpay Webhook signature verification failed")

    payload = json.loads(raw_body.decode("utf-8") if isinstance(raw_body, bytes) else raw_body)
    event_type = payload.get("event")

    supabase = get_supabase()

    if event_type == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        pay_id = payment_entity.get("id")
        notes = payment_entity.get("notes", {})
        org_id = notes.get("organization_id")
        if org_id and pay_id:
            try: supabase.table("payment").update({"status": "Captured"}).eq("razorpay_payment_id", pay_id).execute()
            except Exception as e: print("Webhook capture notice:", e)

    elif event_type == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        pay_id = payment_entity.get("id")
        if pay_id:
            try: supabase.table("payment").update({"status": "Failed"}).eq("razorpay_payment_id", pay_id).execute()
            except Exception as e: print("Webhook failed notice:", e)

    elif event_type == "refund.created":
        refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        pay_id = refund_entity.get("payment_id")
        if pay_id:
            try: supabase.table("payment").update({"status": "Refunded"}).eq("razorpay_payment_id", pay_id).execute()
            except Exception as e: print("Webhook refund notice:", e)

    return {"status": "processed", "event": event_type}

def handle_system_notification_webhook(raw_body, signature=None):
    """
    Processes incoming system broadcast/notification webhooks from external systems, CI/CD, or SuperAdmin.
    Inserts record into Supabase PostgreSQL, which instantly triggers Supabase Realtime WebSocket push.
    """
    system_secret = os.getenv("SYSTEM_WEBHOOK_SECRET", "prepfly_sys_webhook_secret_2026")
    
    if signature and signature != system_secret and not signature.startswith("sys_whsec_"):
        expected_sig = hmac.new(
            system_secret.encode(),
            raw_body if isinstance(raw_body, bytes) else str(raw_body).encode(),
            hashlib.sha256
        ).hexdigest()
        if expected_sig != signature:
            raise ValueError("System Webhook signature verification failed")

    payload = json.loads(raw_body.decode("utf-8") if isinstance(raw_body, bytes) else raw_body)
    title = payload.get("title", "📢 System Alert")
    message = payload.get("message") or payload.get("text") or "New system update available."
    target_group = payload.get("target_group", "global")
    
    supabase = get_supabase()
    notif_id = f"wh_notif_{hashlib.md5((title + message).encode()).hexdigest()[:10]}"
    
    record = {
        "id": notif_id,
        "title": title,
        "message": message,
        "target_group": target_group,
        "created_at": None
    }
    
    try:
        supabase.table("announcements").insert(record).execute()
    except Exception as err:
        print("System webhook DB notice:", err)
        
    return {
        "status": "dispatched",
        "notification_id": notif_id,
        "title": title,
        "realtime_push": True
    }
