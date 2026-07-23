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
        return {
            "organization_id": "org_default",
            "subscription_status": "TRIAL",
            "current_plan": "Trial",
            "days_remaining": 10,
            "trial_start": datetime.utcnow().isoformat(),
            "trial_end": (datetime.utcnow() + timedelta(days=10)).isoformat(),
            "subscription_start": None,
            "subscription_expiry": None,
            "is_blocked": False,
            "reminders": []
        }

    supabase = get_supabase()
    res = supabase.table("organization").select("*").eq("id", org_id).execute()
    rows = res.data if res and hasattr(res, "data") and res.data else []
    org = rows[0] if rows else None

    now = datetime.utcnow()

    if not org:
        trial_start = now.isoformat()
        trial_end = (now + timedelta(days=10)).isoformat()
        org_name = f"Organization {org_id[:8]}" if len(org_id) >= 8 else f"Organization {org_id}"
        
        try:
            supabase.table("organization").insert({
                "id": org_id,
                "name": org_name,
                "type": "College",
                "subscription_status": "TRIAL",
                "trial_start": trial_start,
                "trial_end": trial_end,
                "current_plan": "Trial",
                "status": "Active",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }).execute()

            res_new = supabase.table("organization").select("*").eq("id", org_id).execute()
            if res_new and hasattr(res_new, "data") and res_new.data:
                org = res_new.data[0]
        except Exception as e:
            print("Create default org notice:", e)

    org = org or {
        "id": org_id,
        "subscription_status": "TRIAL",
        "current_plan": "Trial",
        "trial_start": now.isoformat(),
        "trial_end": (now + timedelta(days=10)).isoformat()
    }

    sub_status = org.get("subscription_status") or "TRIAL"
    current_plan = org.get("current_plan") or "Trial"
    trial_start_str = org.get("trial_start")
    trial_end_str = org.get("trial_end")
    sub_start_str = org.get("subscription_start")
    sub_expiry_str = org.get("subscription_expiry")

    is_blocked = False
    days_remaining = 0
    reminders = []

    if sub_status == "TRIAL":
        if trial_end_str:
            try:
                t_end = datetime.fromisoformat(trial_end_str.replace("Z", ""))
                days_remaining = max((t_end.date() - now.date()).days, 0)
                if now > t_end:
                    sub_status = "EXPIRED"
                    current_plan = "Expired"
                    is_blocked = True
                    supabase.table("organization").update({"subscription_status": "EXPIRED", "updated_at": now.isoformat()}).eq("id", org_id).execute()
                else:
                    if days_remaining <= 3:
                        reminders.append(f"⏰ Free Trial expires in {days_remaining} day(s). Renew now to maintain uninterrupted access.")
            except Exception as e:
                print("Trial date parse notice:", e)
                days_remaining = 10
        else:
            t_start = now
            t_end = t_start + timedelta(days=10)
            supabase.table("organization").update({
                "trial_start": t_start.isoformat(),
                "trial_end": t_end.isoformat(),
                "subscription_status": "TRIAL",
                "current_plan": "Trial",
                "updated_at": now.isoformat()
            }).eq("id", org_id).execute()
            trial_start_str = t_start.isoformat()
            trial_end_str = t_end.isoformat()
            days_remaining = 10

    elif sub_status == "ACTIVE":
        if sub_expiry_str:
            try:
                s_exp = datetime.fromisoformat(sub_expiry_str.replace("Z", ""))
                days_remaining = max((s_exp.date() - now.date()).days, 0)
                if now > s_exp:
                    sub_status = "EXPIRED"
                    current_plan = "Expired"
                    is_blocked = True
                    supabase.table("organization").update({"subscription_status": "EXPIRED", "updated_at": now.isoformat()}).eq("id", org_id).execute()
                else:
                    if days_remaining == 7:
                        reminders.append("🔔 Subscription Notice: 7 days remaining before your annual plan expires.")
                    elif days_remaining == 3:
                        reminders.append("⚠️ Subscription Notice: 3 days remaining before your annual plan expires.")
                    elif days_remaining == 1:
                        reminders.append("🚨 Final Warning: Your subscription expires tomorrow. Renew immediately.")
                    elif days_remaining == 0:
                        reminders.append("⚠️ Your subscription expires today.")
            except Exception as e:
                print("Sub expiry date parse notice:", e)
                days_remaining = 365
        else:
            days_remaining = 365

    elif sub_status == "EXPIRED":
        is_blocked = True
        days_remaining = 0
        current_plan = "Expired"

    return {
        "organization_id": org_id,
        "subscription_status": sub_status,
        "current_plan": current_plan,
        "days_remaining": days_remaining,
        "trial_start": trial_start_str,
        "trial_end": trial_end_str,
        "subscription_start": sub_start_str,
        "subscription_expiry": sub_expiry_str,
        "is_blocked": is_blocked,
        "reminders": reminders
    }

def block_if_expired(org_id):
    status = get_org_subscription_status(org_id)
    return status.get("is_blocked", False)
