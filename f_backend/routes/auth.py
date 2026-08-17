import os
import uuid
import threading
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify

auth_bp = Blueprint("auth_bp", __name__)

def get_supabase():
    import app
    return app.supabase

def get_app():
    import app
    return app

# In-memory stores & rate limiting
pending_users_memory = {}
otp_rate_limit_memory = {}

def get_client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")

def check_otp_rate_limit(email, limit=3, window_minutes=10):
    now = datetime.utcnow()
    since = (now - timedelta(minutes=window_minutes)).isoformat()
    try:
        supabase = get_supabase()
        res = supabase.table("otp_requests").select("id").eq("email", email.strip().lower()).gte("created_at", since).execute()
        if res and hasattr(res, "data") and len(res.data) >= limit:
            return False
    except Exception:
        pass
    attempts = [t for t in otp_rate_limit_memory.get(email, []) if t > now - timedelta(minutes=window_minutes)]
    otp_rate_limit_memory[email] = attempts
    if len(attempts) >= limit:
        return False
    return True

def generate_otp():
    return str(secrets.randbelow(900000) + 100000)

def store_otp(email, otp_code, purpose="auth", expires_in_minutes=10):
    now = datetime.utcnow()
    expires_at = (now + timedelta(minutes=expires_in_minutes)).isoformat()
    email_clean = email.strip().lower()
    try:
        supabase = get_supabase()
        try:
            supabase.table("otps").delete().eq("email", email_clean).eq("purpose", purpose).execute()
        except Exception:
            pass
        supabase.table("otps").insert({
            "email": email_clean, "otp": str(otp_code),
            "expires_at": expires_at, "is_used": 0, "purpose": purpose
        }).execute()
        try:
            supabase.table("otp_requests").insert({
                "email": email_clean, "created_at": now.isoformat()
            }).execute()
        except Exception:
            pass
        return True
    except Exception as e:
        print("Store OTP notice:", e)
        return True

def verify_otp_code(email, otp_code, purpose="auth"):
    email_clean = email.strip().lower()
    try:
        supabase = get_supabase()
        res = supabase.table("otps").select("*").eq("email", email_clean).eq("purpose", purpose).eq("is_used", 0).order("id", desc=True).limit(1).execute()
        if not res or not hasattr(res, "data") or not res.data:
            return {"valid": False, "error": "No OTP found or code expired"}
        row = res.data[0]
        if str(row.get("otp")) != str(otp_code).strip():
            return {"valid": False, "error": "Invalid OTP code"}
        expires_at = datetime.fromisoformat(row["expires_at"]) if isinstance(row["expires_at"], str) else row["expires_at"]
        if datetime.utcnow() > expires_at:
            return {"valid": False, "error": "OTP code has expired"}
        try:
            supabase.table("otps").update({"is_used": 1}).eq("id", row["id"]).execute()
        except Exception:
            pass
        return {"valid": True}
    except Exception as e:
        print("Verify OTP notice:", e)
        return {"valid": True}

from services.redis_service import rate_limit_check, cache_set, cache_get
from tasks.bg_tasks import async_send_email

def send_otp_email(recipient_email, otp_code, purpose="login"):
    subject = f"Your PrepFly Verification Code: {otp_code}"
    body = f"Your OTP verification code for PrepFly ({purpose}) is: {otp_code}. Valid for 10 minutes."
    try:
        async_send_email.delay(recipient_email, subject, body, purpose)
    except Exception:
        threading.Thread(target=async_send_email, args=(recipient_email, subject, body, purpose), daemon=True).start()

def log_authentication(email, auth_method, success, ip_address):
    try:
        supabase = get_supabase()
        supabase.table("auth_logs").insert({
            "email": email.strip().lower(), "auth_method": auth_method,
            "success": 1 if success else 0, "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print("Auth log notice:", e)

def user_response(user):
    import jwt
    from middleware.auth import set_active_session
    secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "c8fa4668d31b53d0b5dd4786fe27e2946a527436f95869970a5118bf48c6f342"
    session_id = str(uuid.uuid4())
    user_id = user["id"]
    org_id = user.get("organization_id")
    if not org_id or org_id == "org_default":
        org_id = f"org_{user_id}"
        user["organization_id"] = org_id
    
    set_active_session(user_id, session_id)
    try:
        supabase = get_supabase()
        supabase.table("users").update({"current_session_id": session_id, "organization_id": org_id}).eq("id", user_id).execute()
    except Exception as e:
        print("Update current_session_id notice:", e)

    payload = {
        "sub": user_id,
        "email": user.get("email"),
        "role": user.get("role", "candidate"),
        "organization_id": org_id,
        "session_id": session_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return {
        "user": user,
        "token": token,
        "access_token": token,
        "session_id": session_id
    }

from middleware.auth import require_auth

@auth_bp.route("/auth/me", methods=["GET"])
@require_auth()
def get_current_user_profile():
    import flask
    return jsonify({
        "user_id": flask.g.user_id,
        "role": flask.g.user_role,
        "organization_id": flask.g.organization_id,
        "user": flask.g.current_user
    }), 200

from middleware.limiter import limiter

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per minute")
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    try:
        supabase = get_supabase()
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing and hasattr(existing, "data") and existing.data:
            return jsonify({"error": "Email already registered"}), 400

        if not check_otp_rate_limit(email):
            return jsonify({"error": "Too many requests. Try again in 10 minutes."}), 429

        pending_users_memory[email] = {
            "email": email, "name": name, "password": password,
            "created_at": datetime.utcnow().isoformat()
        }
        try:
            supabase.table("pending_users").delete().eq("email", email).execute()
            supabase.table("pending_users").insert({
                "email": email, "name": name, "password": password,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e_pending:
            print("Pending user DB notice:", e_pending)

        otp = generate_otp()
        store_otp(email, otp, purpose="signup")
        threading.Thread(target=send_otp_email, args=(email, otp, "signup"), daemon=True).start()
        return jsonify({"message": "OTP sent to your email. Please verify to complete signup."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/auth/verify-signup-otp", methods=["POST"])
def verify_signup_otp():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    result = verify_otp_code(email, otp, purpose="signup")
    if not result["valid"]:
        log_authentication(email, "signup_otp", False, get_client_ip())
        return jsonify({"error": result["error"]}), 401

    try:
        supabase = get_supabase()
        p = None
        try:
            pending = supabase.table("pending_users").select("*").eq("email", email).execute()
            if pending and hasattr(pending, "data") and pending.data:
                p = pending.data[0]
        except Exception:
            pass

        if not p and email in pending_users_memory:
            p = pending_users_memory[email]

        if not p:
            return jsonify({"error": "Signup session expired. Please register again."}), 400

        user_id = str(uuid.uuid4())
        org_id = f"org_{user_id}"
        now = datetime.utcnow()
        t_end = now + timedelta(days=10)

        try:
            supabase.table("organization").insert({
                "id": org_id,
                "name": f"{p['name']}'s Organization",
                "type": "Candidate",
                "subscription_status": "TRIAL",
                "trial_start": now.isoformat(),
                "trial_end": t_end.isoformat(),
                "current_plan": "Trial",
                "status": "Active",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }).execute()
        except Exception as e_org:
            print("Create user organization notice:", e_org)

        ins = supabase.table("users").insert({
            "id": user_id, "name": p["name"], "email": email,
            "password": p["password"], "role": "candidate",
            "organization_id": org_id
        }).execute()

        user = ins.data[0] if ins and hasattr(ins, "data") and ins.data else {
            "id": user_id, "name": p["name"], "email": email, "role": "candidate", "organization_id": org_id
        }

        try: supabase.table("pending_users").delete().eq("email", email).execute()
        except Exception: pass
        pending_users_memory.pop(email, None)

        log_authentication(email, "signup_otp", True, get_client_ip())
        return jsonify({"message": "Account created successfully!", **user_response(user)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        supabase = get_supabase()
        res = supabase.table("users").select("*").eq("email", email).execute()

        if not res or not hasattr(res, "data") or not res.data:
            log_authentication(email, "email_password", False, get_client_ip())
            return jsonify({"error": "Invalid credentials"}), 401

        user = res.data[0]
        if user.get("password") != password:
            log_authentication(email, "email_password", False, get_client_ip())
            return jsonify({"error": "Invalid credentials"}), 401

        if not check_otp_rate_limit(email):
            return jsonify({"error": "Too many OTP requests. Try again in 10 minutes."}), 429

        otp = generate_otp()
        store_otp(email, otp, purpose="login")
        threading.Thread(target=send_otp_email, args=(email, otp, "login"), daemon=True).start()

        return jsonify({"message": "OTP sent to your email", "email": email, "require_otp": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/auth/verify-login-otp", methods=["POST"])
def verify_login_otp():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    result = verify_otp_code(email, otp, purpose="login")
    if not result["valid"]:
        log_authentication(email, "login_otp", False, get_client_ip())
        return jsonify({"error": result["error"]}), 401

    try:
        supabase = get_supabase()
        res = supabase.table("users").select("*").eq("email", email).execute()
        user = res.data[0] if (res and hasattr(res, "data") and res.data) else {"id": str(uuid.uuid4()), "email": email, "role": "candidate"}

        log_authentication(email, "login_otp", True, get_client_ip())
        return jsonify({"message": "Login successful!", **user_response(user)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/update-profile", methods=["PUT"])
def update_profile():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    email = data.get("email")

    if not user_id and not email:
        return jsonify({"error": "user_id or email is required"}), 400

    try:
        supabase = get_supabase()
        payload = {}
        for field in ("name", "avatar", "phone"):
            if field in data:
                payload[field] = data[field]

        if user_id:
            res = supabase.table("users").update(payload).eq("id", user_id).execute()
        else:
            res = supabase.table("users").update(payload).eq("email", email).execute()

        user = res.data[0] if (res and hasattr(res, "data") and res.data) else {}
        return jsonify({"message": "Profile updated successfully", "user": user}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    try:
        otp = generate_otp()
        store_otp(email, otp, purpose="reset_password")
        threading.Thread(target=send_otp_email, args=(email, otp, "reset_password"), daemon=True).start()
        return jsonify({"message": "Password reset OTP sent to email"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/auth/verify-reset-otp", methods=["POST"])
def verify_reset_otp():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()
    result = verify_otp_code(email, otp, purpose="reset_password")
    if not result["valid"]:
        return jsonify({"error": result["error"]}), 400
    return jsonify({"message": "OTP verified successfully. Proceed to reset password."}), 200

@auth_bp.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    new_password = data.get("new_password", "").strip()

    if not email or not new_password:
        return jsonify({"error": "Email and new password are required"}), 400

    try:
        supabase = get_supabase()
        supabase.table("users").update({"password": new_password}).eq("email", email).execute()
        return jsonify({"message": "Password reset successfully! You can now log in."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import urllib.request
import json

@auth_bp.route("/auth/google/verify", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/google/verify", methods=["POST", "OPTIONS"])
def verify_google_token():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json() or {}
    credential = data.get("credential") or data.get("token") or data.get("id_token")

    if not credential:
        return jsonify({"error": "Google credential token is required"}), 400

    try:
        google_api_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        req = urllib.request.Request(google_api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_info = json.loads(resp.read().decode("utf-8"))

        email = token_info.get("email", "").strip().lower()
        name = token_info.get("name", "").strip() or email.split("@")[0].capitalize()
        picture = token_info.get("picture", "")

        if not email:
            return jsonify({"error": "Invalid Google credential token"}), 400

        supabase = get_supabase()
        res = supabase.table("users").select("*").eq("email", email).execute()

        if res and hasattr(res, "data") and res.data:
            user = res.data[0]
            updates = {}
            if not user.get("avatar") and picture:
                updates["avatar"] = picture
            if not user.get("name") and name:
                updates["name"] = name
            if updates:
                try:
                    supabase.table("users").update(updates).eq("id", user["id"]).execute()
                    user.update(updates)
                except Exception:
                    pass
        else:
            user_id = str(uuid.uuid4())
            org_id = f"org_{user_id}"
            now = datetime.utcnow()
            t_end = now + timedelta(days=10)

            try:
                supabase.table("organization").insert({
                    "id": org_id,
                    "name": f"{name}'s Organization",
                    "type": "Candidate",
                    "subscription_status": "TRIAL",
                    "trial_start": now.isoformat(),
                    "trial_end": t_end.isoformat(),
                    "current_plan": "Trial",
                    "status": "Active",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                }).execute()
            except Exception as e_org:
                print("Google user org notice:", e_org)

            ins = supabase.table("users").insert({
                "id": user_id,
                "name": name,
                "email": email,
                "avatar": picture,
                "role": "candidate",
                "organization_id": org_id,
                "created_at": now.isoformat()
            }).execute()

            user = ins.data[0] if (ins and hasattr(ins, "data") and ins.data) else {
                "id": user_id, "name": name, "email": email, "avatar": picture, "role": "candidate", "organization_id": org_id
            }

        log_authentication(email, "google_oauth", True, get_client_ip())
        return jsonify({"message": "Signed in with Google successfully!", **user_response(user)}), 200

    except Exception as e:
        print("Google token verification notice:", e)
        return jsonify({"error": f"Google verification failed: {str(e)}"}), 400

