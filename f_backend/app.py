import os
import fitz
import uuid
import random
import base64
import threading
import secrets
import smtplib
from io import BytesIO
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from docx import Document
from flask import Flask, request, jsonify, send_file
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from werkzeug.utils import secure_filename
from flask_cors import CORS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from gtts import gTTS
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CORS(app, resources={r"/*": {
    "origins": ["http://localhost:5173", "http://localhost:5174"],
    "supports_credentials": True
}})

# ─── Supabase Setup ────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://atfozkznxxuehyjgqvvm.supabase.co/")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "sb_publishable_B1hsywJt3jKSDdij-3iddw_ZNStwZWY") # service_role key only
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in your .env file.\n"
        "Get the service_role key from: Supabase Dashboard → Settings → API → service_role"
    )
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Email / SMTP ──────────────────────────────────────────────────────────────
SMTP_SERVER   = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL    = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# ─── Google OAuth ──────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# ─── Upload Folder ─────────────────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ─── Gemini / LangChain ────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
chat_model = ChatGoogleGenerativeAI(
    api_key=GEMINI_API_KEY, model="gemini-2.5-flash-lite", temperature=0.6
)


# ══════════════════════════════════════════════════════════════════════════════
#  EMAIL HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def send_email(to_email, subject, html_body):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("SMTP not configured – skipping email")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = SMTP_EMAIL
        msg['To']      = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def _otp_html(otp: str, title: str, subtitle: str) -> str:
    """Shared OTP email template – reused for login, signup, and reset."""
    return f"""<!DOCTYPE html><html><head><style>
        body{{font-family:Arial,sans-serif;background:#080c14;color:#e8edf8;padding:20px}}
        .c{{max-width:600px;margin:0 auto;background:linear-gradient(135deg,rgba(15,22,40,.95),rgba(13,18,32,.95));
            padding:40px;border-radius:24px;border:1px solid rgba(255,255,255,.07)}}
        .hdr{{text-align:center;color:#00e5c3;font-size:26px;font-weight:700;margin-bottom:8px}}
        .sub{{text-align:center;color:#7a8ba8;font-size:14px;margin-bottom:28px}}
        .box{{background:rgba(0,229,195,.12);padding:28px;text-align:center;border-radius:16px;
              margin:24px 0;border:1px solid rgba(0,229,195,.3)}}
        .otp{{font-size:44px;font-weight:700;color:#00e5c3;letter-spacing:14px;font-family:monospace}}
        .info{{color:#7a8ba8;font-size:13px;margin-top:20px;line-height:1.7}}
        .footer{{text-align:center;color:#4a5a72;font-size:11px;margin-top:36px}}
    </style></head><body><div class="c">
        <div class="hdr">🎯 HireAI</div>
        <div class="sub">{subtitle}</div>
        <p style="color:#e8edf8">{title}</p>
        <div class="box"><div class="otp">{otp}</div></div>
        <div class="info">
            ⏰ Expires in <strong style="color:#00e5c3">5 minutes</strong><br>
            🔒 Do not share this code with anyone
        </div>
        <p style="color:#7a8ba8;font-size:13px">If you didn't request this, please ignore this email.</p>
        <div class="footer">© 2026 HireAI · AI-Powered Interview Platform</div>
    </div></body></html>"""


def send_otp_email(email: str, otp: str, purpose: str = "login"):
    titles = {
        "login":   ("Your login verification code:", "Sign in to HireAI"),
        "signup":  ("Verify your new HireAI account:", "Confirm your email address"),
        "reset":   ("Reset your HireAI password:", "Password Reset Request"),
    }
    title, subtitle = titles.get(purpose, titles["login"])
    return send_email(email, f"HireAI – {subtitle}", _otp_html(otp, title, subtitle))


def send_login_confirmation_email(email, name, login_time):
    subject = "Successful Login – HireAI"
    html = f"""<!DOCTYPE html><html><head><style>
        body{{font-family:Arial,sans-serif;background:#080c14;color:#e8edf8;padding:20px}}
        .c{{max-width:600px;margin:0 auto;background:linear-gradient(135deg,rgba(15,22,40,.95),rgba(13,18,32,.95));
            padding:40px;border-radius:24px;border:1px solid rgba(255,255,255,.07)}}
        .hdr{{text-align:center;color:#00d68f;font-size:26px;font-weight:700;margin-bottom:20px}}
        .box{{background:rgba(0,214,143,.12);border-left:4px solid #00d68f;padding:20px;margin:24px 0;border-radius:12px}}
        .lbl{{font-weight:600;color:#00e5c3}}
        .warn{{background:rgba(255,79,106,.12);border-left:4px solid #ff4f6a;padding:20px;
               margin:24px 0;border-radius:12px;color:#ff4f6a}}
        .footer{{text-align:center;color:#4a5a72;font-size:11px;margin-top:36px}}
    </style></head><body><div class="c">
        <div style="text-align:center;font-size:48px">✅</div>
        <div class="hdr">Login Successful</div>
        <p>Hello {name},</p>
        <p style="color:#7a8ba8">You signed in to <strong>HireAI</strong> via Google.</p>
        <div class="box">
            <div><span class="lbl">📧 Email:</span> <span style="color:#7a8ba8">{email}</span></div>
            <div style="margin-top:10px"><span class="lbl">🕐 Time:</span> <span style="color:#7a8ba8">{login_time}</span></div>
            <div style="margin-top:10px"><span class="lbl">🔐 Method:</span> <span style="color:#7a8ba8">Google OAuth 2.0</span></div>
        </div>
        <div class="warn">⚠️ If this wasn't you, secure your Google account immediately.</div>
        <div class="footer">© 2026 HireAI</div>
    </div></body></html>"""
    return send_email(email, subject, html)


# ══════════════════════════════════════════════════════════════════════════════
#  OTP / AUTH HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def generate_otp() -> str:
    return ''.join(str(secrets.randbelow(10)) for _ in range(6))


def check_otp_rate_limit(email: str) -> bool:
    """Max 3 requests per 10 min per email."""
    try:
        since = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
        res   = supabase.table("otp_requests").select("id").eq("email", email).gte("created_at", since).execute()
        return not (res.data and len(res.data) >= 3)
    except Exception as e:
        print(f"Rate limit error: {e}")
        return True


def store_otp(email: str, otp: str, purpose: str = "login") -> bool:
    """Delete old OTPs for this email+purpose and store a fresh one."""
    try:
        expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        supabase.table("otps").delete().eq("email", email).eq("purpose", purpose).execute()
        supabase.table("otps").insert({
            "email": email, "otp": otp,
            "expires_at": expires_at, "is_used": False, "purpose": purpose
        }).execute()
        supabase.table("otp_requests").insert({
            "email": email, "created_at": datetime.utcnow().isoformat()
        }).execute()
        return True
    except Exception as e:
        print(f"Store OTP error: {e}")
        return False


def verify_otp_code(email: str, otp: str, purpose: str = "login") -> dict:
    """Validate OTP, check expiry, mark used."""
    try:
        res = supabase.table("otps").select("*") \
            .eq("email", email).eq("otp", otp) \
            .eq("is_used", False).eq("purpose", purpose) \
            .maybe_single().execute()

        if not res or not res.data:
            return {"valid": False, "error": "Invalid OTP"}

        row        = res.data
        expires_at = datetime.fromisoformat(row["expires_at"].replace('Z', '+00:00'))
        now_aware  = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)

        if now_aware > expires_at:
            return {"valid": False, "error": "OTP has expired"}

        supabase.table("otps").update({"is_used": True}).eq("id", row["id"]).execute()
        return {"valid": True}
    except Exception as e:
        print(f"Verify OTP error: {e}")
        return {"valid": False, "error": "Verification failed"}


def get_or_create_user(email, name=None, avatar=None, google_id=None):
    try:
        res = supabase.table("users").select("*").eq("email", email).maybe_single().execute()
        if res and res.data:
            user    = res.data
            payload = {}
            if google_id and not user.get("google_id"):
                payload["google_id"] = google_id
            if avatar and not user.get("avatar"):
                payload["avatar"] = avatar
            if payload:
                supabase.table("users").update(payload).eq("id", user["id"]).execute()
                user.update(payload)
            return user

        ins = supabase.table("users").insert({
            "email": email,
            "name":  name or email.split("@")[0],
            "avatar": avatar, "google_id": google_id, "role": "candidate"
        }).execute()
        if ins and ins.data:
            return ins.data[0]
        print(f"Insert returned no data for {email}")
        return None
    except Exception as e:
        print(f"get_or_create_user error: {e}")
        return None


def log_authentication(email, method, success, ip_address=None):
    try:
        supabase.table("auth_logs").insert({
            "email": email, "auth_method": method,
            "success": success, "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print(f"Auth log error (non-fatal): {e}")


def get_client_ip():
    fwd = request.headers.get('X-Forwarded-For')
    return fwd.split(',')[0].strip() if fwd else request.remote_addr


def user_response(user: dict) -> dict:
    """Standardised user payload returned to frontend."""
    return {
        "email":   user["email"],
        "user_id": user["id"],
        "name":    user.get("name", ""),
        "role":    user.get("role", "candidate"),
        "phone":   user.get("phone", ""),
        "avatar":  user.get("avatar", ""),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. Register – sends OTP to verify email ───────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
    """
    Step 1: collect name/email/password, store pending user, send signup OTP.
    Step 2: /auth/verify-signup-otp confirms and activates the account.
    """
    data     = request.get_json() or {}
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    try:
        existing = supabase.table("users").select("id").eq("email", email).maybe_single().execute()
        if existing and existing.data:
            return jsonify({"error": "Email already registered"}), 400

        if not check_otp_rate_limit(email):
            return jsonify({"error": "Too many requests. Try again in 10 minutes."}), 429

        # Store pending registration in a temp table
        supabase.table("pending_users").delete().eq("email", email).execute()
        supabase.table("pending_users").insert({
            "email": email, "name": name, "password": password,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        otp = generate_otp()
        if not store_otp(email, otp, purpose="signup"):
            return jsonify({"error": "Failed to generate OTP"}), 500

        threading.Thread(target=send_otp_email, args=(email, otp, "signup"), daemon=True).start()
        return jsonify({"message": "OTP sent to your email. Please verify to complete signup."}), 200

    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/auth/verify-signup-otp", methods=["POST"])
def verify_signup_otp():
    """Verify OTP from signup flow → create real user account."""
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp   = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    result = verify_otp_code(email, otp, purpose="signup")
    if not result["valid"]:
        log_authentication(email, "signup_otp", False, get_client_ip())
        return jsonify({"error": result["error"]}), 401

    try:
        # Fetch pending registration
        pending = supabase.table("pending_users").select("*").eq("email", email).maybe_single().execute()
        if not pending or not pending.data:
            return jsonify({"error": "Signup session expired. Please register again."}), 400

        p = pending.data

        # Create real user
        ins = supabase.table("users").insert({
            "name": p["name"], "email": email,
            "password": p["password"], "role": "candidate"
        }).execute()

        if not ins or not ins.data:
            return jsonify({"error": "Failed to create account. Please try again."}), 500

        user = ins.data[0]
        # Clean up pending row
        supabase.table("pending_users").delete().eq("email", email).execute()

        log_authentication(email, "signup_otp", True, get_client_ip())
        return jsonify({"message": "Account created successfully!", **user_response(user)}), 201

    except Exception as e:
        print(f"Verify signup OTP error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 2. Login – sends OTP after password check ─────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    """
    Validates password, then sends a login OTP.
    Frontend must call /auth/verify-login-otp to complete sign-in.
    """
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        res = supabase.table("users").select("*").eq("email", email).maybe_single().execute()

        if not res or not res.data:
            log_authentication(email, "email_password", False, get_client_ip())
            return jsonify({"error": "Invalid credentials"}), 401

        user = res.data
        if user.get("password") != password:
            log_authentication(email, "email_password", False, get_client_ip())
            return jsonify({"error": "Invalid credentials"}), 401

        if not check_otp_rate_limit(email):
            return jsonify({"error": "Too many OTP requests. Try again in 10 minutes."}), 429

        otp = generate_otp()
        if not store_otp(email, otp, purpose="login"):
            return jsonify({"error": "Failed to send OTP"}), 500

        threading.Thread(target=send_otp_email, args=(email, otp, "login"), daemon=True).start()

        return jsonify({
            "message": "Password verified. OTP sent to your email.",
            "otp_required": True,
            "email": email
        }), 200

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/auth/verify-login-otp", methods=["POST"])
def verify_login_otp():
    """Final step of login: verify OTP → return user session."""
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp   = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    result = verify_otp_code(email, otp, purpose="login")
    if not result["valid"]:
        log_authentication(email, "email_password_otp", False, get_client_ip())
        return jsonify({"error": result["error"]}), 401

    try:
        res = supabase.table("users").select("*").eq("email", email).maybe_single().execute()
        if not res or not res.data:
            return jsonify({"error": "User not found"}), 404

        user = res.data
        log_authentication(email, "email_password_otp", True, get_client_ip())
        return jsonify({"message": "Login successful", **user_response(user)}), 200

    except Exception as e:
        print(f"Verify login OTP error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 3. OTP-only login (no password) ──────────────────────────────────────────
@app.route("/auth/email/request-otp", methods=["POST"])
def request_otp():
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not check_otp_rate_limit(email):
        return jsonify({"error": "Too many requests. Try again in 10 minutes."}), 429

    otp = generate_otp()
    if not store_otp(email, otp, purpose="login"):
        return jsonify({"error": "Failed to generate OTP"}), 500

    threading.Thread(target=send_otp_email, args=(email, otp, "login"), daemon=True).start()
    return jsonify({"message": "OTP sent to your email"}), 200


@app.route("/auth/email/verify-otp", methods=["POST"])
def verify_otp_route():
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp   = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    result = verify_otp_code(email, otp, purpose="login")
    if not result["valid"]:
        log_authentication(email, "email_otp", False, get_client_ip())
        return jsonify({"error": result["error"]}), 401

    user = get_or_create_user(email)
    if not user:
        return jsonify({"error": "Failed to find or create account"}), 500

    log_authentication(email, "email_otp", True, get_client_ip())
    return jsonify({"message": "Login successful", **user_response(user)}), 200


# ── 4. Google OAuth ───────────────────────────────────────────────────────────
@app.route("/auth/google/verify", methods=["POST"])
def google_verify():
    data       = request.get_json() or {}
    credential = data.get("credential", "").strip()

    if not credential:
        return jsonify({"error": "Google credential is required"}), 400

    try:
        idinfo     = id_token.verify_oauth2_token(credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        google_sub = idinfo["sub"]
        email      = idinfo.get("email", "")
        name       = idinfo.get("name", "")
        avatar     = idinfo.get("picture", "")

        user = get_or_create_user(email, name, avatar, google_sub)
        if not user:
            log_authentication(email, "google_oauth", False, get_client_ip())
            return jsonify({"error": "Failed to create user account"}), 500

        login_time = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")
        threading.Thread(
            target=send_login_confirmation_email, args=(email, name, login_time), daemon=True
        ).start()

        log_authentication(email, "google_oauth", True, get_client_ip())
        return jsonify({
            "message": "Signed in with Google successfully",
            **user_response(user),
            "name":   user.get("name") or name,
            "avatar": user.get("avatar") or avatar,
        }), 200

    except ValueError as e:
        log_authentication("unknown", "google_oauth", False, get_client_ip())
        return jsonify({"error": f"Invalid Google token: {e}"}), 401
    except Exception as e:
        log_authentication("unknown", "google_oauth", False, get_client_ip())
        return jsonify({"error": f"Google sign-in failed: {e}"}), 500


# ── 5. Forgot Password ────────────────────────────────────────────────────────
@app.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    """Send a password-reset OTP. Always returns 200 to avoid email enumeration."""
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        # Check user exists — but don't reveal result to caller
        res = supabase.table("users").select("id").eq("email", email).maybe_single().execute()
        if res and res.data:
            if check_otp_rate_limit(email):
                otp = generate_otp()
                if store_otp(email, otp, purpose="reset"):
                    threading.Thread(
                        target=send_otp_email, args=(email, otp, "reset"), daemon=True
                    ).start()

        # Always return same response (prevents user enumeration)
        return jsonify({"message": "If that email is registered, a reset code has been sent."}), 200

    except Exception as e:
        print(f"Forgot password error: {e}")
        return jsonify({"message": "If that email is registered, a reset code has been sent."}), 200


@app.route("/auth/verify-reset-otp", methods=["POST"])
def verify_reset_otp():
    """Verify the reset OTP — returns a short-lived reset token."""
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp   = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    result = verify_otp_code(email, otp, purpose="reset")
    if not result["valid"]:
        return jsonify({"error": result["error"]}), 401

    # Issue a short-lived reset token (valid 10 min)
    reset_token = secrets.token_urlsafe(32)
    expires_at  = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    try:
        supabase.table("password_reset_tokens").delete().eq("email", email).execute()
        supabase.table("password_reset_tokens").insert({
            "email": email, "token": reset_token,
            "expires_at": expires_at, "is_used": False
        }).execute()
    except Exception as e:
        print(f"Reset token store error: {e}")
        return jsonify({"error": "Failed to issue reset token"}), 500

    return jsonify({"message": "OTP verified", "reset_token": reset_token}), 200


@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    """Set a new password using the reset token from /auth/verify-reset-otp."""
    data         = request.get_json() or {}
    email        = data.get("email", "").strip().lower()
    reset_token  = data.get("reset_token", "").strip()
    new_password = data.get("new_password", "").strip()

    if not email or not reset_token or not new_password:
        return jsonify({"error": "email, reset_token, and new_password are required"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    try:
        res = supabase.table("password_reset_tokens").select("*") \
            .eq("email", email).eq("token", reset_token).eq("is_used", False) \
            .maybe_single().execute()

        if not res or not res.data:
            return jsonify({"error": "Invalid or expired reset token"}), 401

        row        = res.data
        expires_at = datetime.fromisoformat(row["expires_at"].replace('Z', '+00:00'))
        now_aware  = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)

        if now_aware > expires_at:
            return jsonify({"error": "Reset token has expired"}), 401

        # Update password
        supabase.table("users").update({"password": new_password}).eq("email", email).execute()

        # Mark token used
        supabase.table("password_reset_tokens").update({"is_used": True}).eq("id", row["id"]).execute()

        log_authentication(email, "password_reset", True, get_client_ip())
        return jsonify({"message": "Password reset successfully. You can now log in."}), 200

    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  INTERVIEW SYSTEM HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    return "\n".join(page.get_text() for page in doc)


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs)


def generate_question(resume_text: str, previous_questions: list = None) -> str:
    focus_areas = [
        "technical skills and tools", "work experience and achievements",
        "education and learning approach", "problem-solving ability",
        "team collaboration and leadership", "a specific project mentioned in the resume",
        "career goals and motivation",
    ]
    prev_q_text = ""
    if previous_questions:
        prev_q_text = "Already asked (do NOT repeat):\n" + "\n".join(f"- {q}" for q in previous_questions[-5:])

    prompt = f"""You are Hana, a friendly anime-style AI interviewer.
Based on the resume, generate ONE clear interview question.
Focus: {random.choice(focus_areas)}

{prev_q_text}

Rules:
- One question only (1-2 sentences)
- Specific to the resume content
- Conversational tone
- No preamble like "Here is a question:"

Resume:
{resume_text[:3000]}"""
    try:
        return chat_model.invoke([HumanMessage(content=prompt)]).content.strip()
    except Exception:
        return "Tell me about your most impactful project from your resume."


def analyze_response(resume_text: str, question: str, response: str) -> dict:
    prompt = f"""You are Hana, an expert AI interviewer. Evaluate this answer.

Resume: {resume_text[:1000]}
Question: {question}
Answer: {response}

Reply in EXACTLY this format:
SCORE: [1-10]
STRENGTH: [one sentence]
IMPROVEMENT: [one sentence]
TIP: [one sentence]
SUMMARY: [2-3 sentences]"""
    try:
        raw   = chat_model.invoke([HumanMessage(content=prompt)]).content.strip()
        score = 7; strength = improvement = tip = summary = ""
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("SCORE:"):
                try: score = max(1, min(10, int(line.replace("SCORE:", "").strip().split()[0])))
                except: pass
            elif line.startswith("STRENGTH:"):    strength    = line.replace("STRENGTH:", "").strip()
            elif line.startswith("IMPROVEMENT:"): improvement = line.replace("IMPROVEMENT:", "").strip()
            elif line.startswith("TIP:"):         tip         = line.replace("TIP:", "").strip()
            elif line.startswith("SUMMARY:"):     summary     = line.replace("SUMMARY:", "").strip()

        feedback = f"✅ Strength: {strength}\n⚠️ Improve: {improvement}\n💡 Tip: {tip}"
        if summary: feedback += f"\n\n{summary}"
        return {"feedback": feedback, "score": score, "strength": strength,
                "improvement": improvement, "tip": tip, "summary": summary}
    except Exception:
        return {"feedback": "Good attempt. Keep practicing.", "score": 6,
                "strength": "You attempted the question",
                "improvement": "Add more specific details",
                "tip": "Use STAR: Situation, Task, Action, Result",
                "summary": "Keep practicing to improve."}


# ══════════════════════════════════════════════════════════════════════════════
#  INTERVIEW ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"error": "No resume file provided"}), 400

    file = request.files["resume"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    user_id  = request.form.get("user_id")
    filename = secure_filename(file.filename)
    ext      = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "docx"):
        return jsonify({"error": "Only PDF and DOCX files are supported"}), 400

    save_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{uuid.uuid4()}_{filename}")
    file.save(save_path)

    try:
        resume_text = extract_text_from_pdf(save_path) if ext == "pdf" else extract_text_from_docx(save_path)
        if not resume_text.strip():
            return jsonify({"error": "Could not extract text from resume"}), 400

        session_id   = str(uuid.uuid4())
        session_data = {
            "session_id": session_id, "resume_text": resume_text,
            "question_index": 0, "questions": [], "responses": [],
            "feedbacks": [], "active": True,
        }
        if user_id:
            session_data["user_id"] = user_id

        supabase.table("sessions").insert(session_data).execute()
        return jsonify({"message": "Resume uploaded", "session_id": session_id, "text_length": len(resume_text)}), 200

    except Exception as e:
        print(f"Upload resume error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route("/start-interview", methods=["POST"])
def start_interview():
    data       = request.get_json() or {}
    session_id = data.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        res = supabase.table("sessions").select("*").eq("session_id", session_id).eq("active", True).maybe_single().execute()
        if not res or not res.data:
            return jsonify({"error": "Session not found or already completed"}), 404

        session   = res.data
        first_q   = generate_question(session.get("resume_text", ""))
        questions = [first_q]

        supabase.table("sessions").update({"questions": questions, "question_index": 1}).eq("session_id", session_id).execute()
        return jsonify({"message": "Interview started", "question": first_q, "question_number": 1}), 200

    except Exception as e:
        print(f"Start interview error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/next-question", methods=["POST"])
def next_question():
    data       = request.get_json() or {}
    session_id = data.get("session_id", "").strip()
    answer     = data.get("answer", "").strip()

    if not session_id or not answer:
        return jsonify({"error": "session_id and answer are required"}), 400

    try:
        res = supabase.table("sessions").select("*").eq("session_id", session_id).eq("active", True).maybe_single().execute()
        if not res or not res.data:
            return jsonify({"error": "Session not found or already completed"}), 404

        session        = res.data
        resume_text    = session.get("resume_text", "")
        questions      = session.get("questions") or []
        responses      = session.get("responses") or []
        feedbacks      = session.get("feedbacks") or []
        question_index = session.get("question_index", 1)
        current_q      = questions[-1] if questions else "Tell me about yourself."

        feedback = analyze_response(resume_text, current_q, answer)
        responses.append(answer)
        feedbacks.append(feedback)

        MAX_QUESTIONS = 5
        if question_index >= MAX_QUESTIONS:
            avg_score = round(sum(f.get("score", 0) for f in feedbacks) / len(feedbacks), 1) if feedbacks else 0
            supabase.table("sessions").update({"responses": responses, "feedbacks": feedbacks, "active": False}).eq("session_id", session_id).execute()
            return jsonify({"message": "Interview complete", "done": True, "final_feedback": feedback,
                            "average_score": avg_score, "total_questions": len(questions), "all_feedbacks": feedbacks}), 200

        next_q = generate_question(resume_text, previous_questions=questions)
        questions.append(next_q)
        supabase.table("sessions").update({
            "questions": questions, "responses": responses,
            "feedbacks": feedbacks, "question_index": question_index + 1,
        }).eq("session_id", session_id).execute()
        return jsonify({"message": "Answer recorded", "done": False, "feedback": feedback,
                        "next_question": next_q, "question_number": question_index + 1}), 200

    except Exception as e:
        print(f"Next question error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/get-session", methods=["GET"])
def get_session():
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    try:
        res = supabase.table("sessions").select("*").eq("session_id", session_id).maybe_single().execute()
        if not res or not res.data:
            return jsonify({"error": "Session not found"}), 404
        session = res.data
        session.pop("resume_text", None)
        return jsonify(session), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/user-sessions", methods=["GET"])
def user_sessions():
    user_id = request.args.get("user_id", "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    try:
        res = supabase.table("sessions").select("session_id,question_index,active,created_at,updated_at") \
            .eq("user_id", user_id).order("created_at", desc=True).execute()
        return jsonify({"sessions": res.data or []}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        tts = gTTS(text=text, lang="en", slow=False)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg", as_attachment=False, download_name="speech.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)