import os
from datetime import datetime, timedelta

def get_supabase():
    try:
        import app
        return app.supabase
    except Exception:
        from local_supabase import SQLiteSupabaseMock
        return SQLiteSupabaseMock()

def get_org_subscription_status(org_id):
    if not org_id:
        org_id = "org_default"

    supabase = get_supabase()
    org = None
    try:
        res = supabase.table("organization").select("*").eq("id", org_id).execute()
        rows = res.data if res and hasattr(res, "data") and res.data else []
        org = rows[0] if rows else None
    except Exception as e:
        print("Subscription service fetch notice:", e)

    now = datetime.utcnow()
    default_expiry = (now + timedelta(days=365)).strftime("%Y-%m-%d")

    if not org:
        org = {
            "id": org_id,
            "name": f"Organization {org_id[:8]}" if len(org_id) >= 8 else f"Organization {org_id}",
            "type": "College",
            "subscription_status": "ACTIVE",
            "current_plan": "ENTERPRISE SCALE",
            "subscription_start": now.strftime("%Y-%m-%d"),
            "subscription_expiry": default_expiry,
            "status": "Active"
        }

    sub_status = org.get("subscription_status") or "ACTIVE"
    current_plan = org.get("current_plan") or org.get("subscription_plan") or "ENTERPRISE SCALE"
    sub_expiry_str = org.get("subscription_expiry") or org.get("expiry_date") or default_expiry
    trial_end_str = org.get("trial_end")

    is_blocked = False
    days_remaining = 365
    reminders = []

    if sub_status.upper() in ["ACTIVE", "ENTERPRISE", "ENTERPRISE SCALE", "BUSINESS GROWTH", "PREMIUM"]:
        sub_status = "ACTIVE"
        try:
            exp_date = datetime.strptime(str(sub_expiry_str)[:10], "%Y-%m-%d")
            days_remaining = max(0, (exp_date.date() - now.date()).days)
            if now.date() > exp_date.date():
                sub_status = "EXPIRED"
                is_blocked = True
                reminders.append("⚠️ Enterprise Subscription has expired. Please renew your annual contract.")
            else:
                reminders.append(f"🟢 Active Subscription verified. {days_remaining} days remaining in billing cycle.")
        except Exception as e:
            days_remaining = 365
    elif sub_status.upper() == "TRIAL":
        if trial_end_str:
            try:
                t_end = datetime.fromisoformat(str(trial_end_str).replace("Z", ""))
                days_remaining = max((t_end.date() - now.date()).days, 0)
                if now > t_end:
                    sub_status = "EXPIRED"
                    current_plan = "Expired"
                    is_blocked = True
                else:
                    reminders.append(f"⏰ Free Trial expires in {days_remaining} day(s). Upgrade to Enterprise to unlock full access.")
            except Exception as e:
                days_remaining = 14
        else:
            days_remaining = 14

    return {
        "organization_id": org_id,
        "subscription_status": sub_status,
        "current_plan": current_plan,
        "days_remaining": days_remaining,
        "subscription_start": org.get("subscription_start") or now.strftime("%Y-%m-%d"),
        "subscription_expiry": sub_expiry_str,
        "is_blocked": is_blocked,
        "reminders": reminders
    }

def block_if_expired(org_id):
    status = get_org_subscription_status(org_id)
    return status.get("is_blocked", False)
