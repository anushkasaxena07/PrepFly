import os
import fitz
import uuid
import random
from io import BytesIO

from docx import Document
from flask import Flask, request, jsonify, send_file, redirect
from werkzeug.utils import secure_filename
from flask_cors import CORS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from gtts import gTTS
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ─── Supabase Setup ────────────────────────────────────────────────────────────
# ⚠️  IMPORTANT: SUPABASE_SERVICE_KEY must be the service_role key (starts with "eyJ...").
# Get it from: Supabase Dashboard → Project Settings → API → service_role (secret)
# Add to your .env file — NEVER hardcode or commit it to Git.
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://atfozkznxxuehyjgqvvm.supabase.co/")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "sb_publishable_B1hsywJt3jKSDdij-3iddw_ZNStwZWY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in your .env file.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Upload Folder ─────────────────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ─── Gemini / LangChain Setup ──────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
chat_model = ChatGoogleGenerativeAI(
    api_key=GEMINI_API_KEY, model="gemini-2.5-flash-lite", temperature=0.6
)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    return "\n".join(page.get_text() for page in doc)


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs)


def generate_question(resume_text: str) -> str:
    focus_areas = ["education background", "technical skills", "work experience", "certifications", "projects"]
    focus = random.choice(focus_areas)
    prompt = f"""
    You are a technical interviewer. Based on the candidate's resume, generate a clear
    interview question. Focus on {focus}. Keep it short (1-2 sentences only).
    Resume Content: {resume_text[:3000]}
    """
    try:
        res = chat_model.invoke([HumanMessage(content=prompt)])
        return res.content.strip()
    except Exception as e:
        return f"Error generating question: {e}"


def analyze_response(resume_text: str, question: str, response: str) -> str:
    prompt = f"""
    Evaluate the candidate's response professionally.
    Resume: {resume_text[:1000]}
    Question: {question}
    Answer: {response}
    Give concise feedback (3 bullet points):
    - One strength
    - One improvement area
    - One actionable tip
    """
    try:
        feedback = chat_model.invoke([HumanMessage(content=prompt)])
        return feedback.content.strip()
    except Exception as e:
        return f"Error analyzing response: {e}"


def _get_session(session_id: str):
    """Fetch a session row from Supabase. Returns None if not found."""
    try:
        res = (
            supabase.table("sessions")
            .select("*")
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/register", methods=["POST"])
def register():
    """
    Body: { email, password, name? }

    FIX: Removed direct upsert into public.users — was blocked by RLS (no INSERT
    policy), causing 500 errors. The on_auth_user_created trigger now handles
    the row creation automatically. Name is passed via options.data so the
    trigger picks it up from raw_user_meta_data. A safe .update() (not upsert)
    is used afterwards with the service-role key to set the name.
    """
    data     = request.json or {}
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    name     = data.get("name", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        auth_res = supabase.auth.sign_up({
            "email":    email,
            "password": password,
            "options":  {"data": {"name": name}}  # picked up by trigger via raw_user_meta_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if auth_res.user is None:
        return jsonify({"error": "Registration failed – check email/password requirements"}), 400

    user_id = auth_res.user.id

    # Update name using service-role key (bypasses RLS safely — server-side only)
    if name:
        try:
            supabase.table("users").update({"name": name}).eq("id", user_id).execute()
        except Exception:
            pass  # Non-fatal; trigger already created the row

    return jsonify({"message": "Registration successful. Please verify your email."}), 201


@app.route("/login", methods=["POST"])
def login():
    """
    Body: { email, password }

    FIX 1: Better error message when email is unverified ("email not confirmed").
    FIX 2: Null-safe profile.data access — maybe_single() returns None when no
            row exists, which was crashing with AttributeError.
    FIX 3: Fallback upsert creates profile row if trigger hadn't fired yet.
    """
    data     = request.json or {}
    email    = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        err_msg = str(e).lower()
        if "email not confirmed" in err_msg or "not confirmed" in err_msg:
            return jsonify({"error": "Please verify your email before signing in. Check your inbox."}), 401
        return jsonify({"error": "Invalid email or password"}), 401

    if auth_res.user is None:
        return jsonify({"error": "Invalid credentials"}), 401

    user_id = auth_res.user.id

    # Null-safe profile fetch
    profile_data = {}
    try:
        profile = (
            supabase.table("users")
            .select("name, role, phone, avatar")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        if profile and profile.data:
            profile_data = profile.data
    except Exception:
        pass  # Non-fatal; login still succeeds

    # Fallback: create profile row if trigger hadn't fired yet
    if not profile_data:
        try:
            supabase.table("users").upsert({"id": user_id, "email": email}).execute()
        except Exception:
            pass

    return jsonify({
        "message": "Login successful",
        "email":   email,
        "user_id": user_id,
        "name":    profile_data.get("name", ""),
        "role":    profile_data.get("role", ""),
        "phone":   profile_data.get("phone", ""),
        "avatar":  profile_data.get("avatar", ""),
    }), 200


# ─── Google OAuth ──────────────────────────────────────────────────────────────

@app.route("/auth/google")
def google_login():
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    try:
        res = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options":  {"redirect_to": f"{frontend_url}/auth/callback"},
        })
        return redirect(res.url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/auth/callback")
def auth_callback():
    return redirect(os.getenv("FRONTEND_URL", "http://localhost:5173") + "/dashboard")


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/update-profile", methods=["PUT"])
def update_profile():
    """Body: { user_id, name?, email?, phone?, role?, avatar? }"""
    data    = request.json or {}
    user_id = data.get("user_id", "").strip()

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    allowed     = ["name", "email", "phone", "role", "avatar"]
    update_data = {k: data[k] for k in allowed if data.get(k) is not None}

    if not update_data:
        return jsonify({"error": "No fields to update"}), 400

    res = supabase.table("users").update(update_data).eq("id", user_id).execute()

    if not res.data:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": "Profile updated successfully", "user": res.data[0]})


@app.route("/profile/<user_id>", methods=["GET"])
def get_profile(user_id: str):
    res = (
        supabase.table("users")
        .select("id, email, name, phone, role, avatar, created_at")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if not res or not res.data:
        return jsonify({"error": "User not found"}), 404
    return jsonify(res.data)


# ══════════════════════════════════════════════════════════════════════════════
#  RESUME / SESSION ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/upload", methods=["POST"])
def upload_resume():
    """
    Form-data: { resume (file), session_id (string), user_id? (string) }

    FIX: Changed .insert() to .upsert(on_conflict="session_id") to prevent
    the 'duplicate key violates unique constraint' 500 error that occurred
    when the frontend retried an upload with the same session_id.
    """
    file = request.files.get("resume")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        text = extract_text_from_pdf(filepath)
    elif ext in ("docx", "doc"):
        text = extract_text_from_docx(filepath)
    else:
        return jsonify({"error": "Unsupported file type. Upload PDF or DOCX."}), 400

    # Upload raw file to Supabase Storage (best-effort)
    storage_path = None
    try:
        with open(filepath, "rb") as f:
            content = f.read()
        storage_res = supabase.storage.from_("resumes").upload(
            path=f"{uuid.uuid4()}_{filename}",
            file=content,
            file_options={"content-type": "application/octet-stream"},
        )
        storage_path = storage_res.path
    except Exception:
        pass

    session_id = request.form.get("session_id") or str(uuid.uuid4())
    user_id    = request.form.get("user_id") or None

    session_row = {
        "session_id":     session_id,
        "user_id":        user_id,
        "resume_text":    text,
        "storage_path":   storage_path,
        "question_index": 0,
        "questions":      ["Introduce yourself."],
        "responses":      [],
        "feedbacks":      [],
        "active":         True,
    }

    # upsert prevents duplicate key crash on retry
    supabase.table("sessions").upsert(session_row, on_conflict="session_id").execute()

    return jsonify({"message": "Resume processed", "session_id": session_id})


@app.route("/next", methods=["POST"])
def next_question():
    session_id = (request.json or {}).get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Invalid session"}), 404

    if not session.get("active"):
        return jsonify({"message": "Interview complete"}), 200

    question          = generate_question(session["resume_text"])
    updated_questions = session.get("questions", []) + [question]

    supabase.table("sessions").update({
        "questions":      updated_questions,
        "question_index": len(updated_questions) - 1,
    }).eq("session_id", session_id).execute()

    return jsonify({"question": question})


@app.route("/response", methods=["POST"])
def submit_response():
    data          = request.json or {}
    session_id    = data.get("session_id")
    response_text = data.get("response", "").strip()

    if not session_id or not response_text:
        return jsonify({"error": "session_id and response are required"}), 400

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Invalid session"}), 404

    questions        = session.get("questions", [])
    current_question = questions[-1] if questions else "General interview question"
    feedback         = analyze_response(session["resume_text"], current_question, response_text)

    supabase.table("sessions").update({
        "responses": session.get("responses", []) + [response_text],
        "feedbacks": session.get("feedbacks", []) + [feedback],
    }).eq("session_id", session_id).execute()

    return jsonify({"feedback": feedback})


@app.route("/end-interview", methods=["POST"])
def end_interview():
    session_id = (request.json or {}).get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Invalid session"}), 404

    supabase.table("sessions").update({"active": False}).eq("session_id", session_id).execute()

    return jsonify({
        "message":   "Interview ended",
        "questions": session.get("questions", []),
        "responses": session.get("responses", []),
        "feedbacks": session.get("feedbacks", []),
    })


@app.route("/history/<user_id>", methods=["GET"])
def interview_history(user_id: str):
    res = (
        supabase.table("sessions")
        .select("session_id, question_index, active, created_at, questions, feedbacks")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(res.data or [])


# ══════════════════════════════════════════════════════════════════════════════
#  TEXT-TO-SPEECH ROUTE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        tts = gTTS(text)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg", download_name="speech.mp3")
    except Exception as e:
        return jsonify({"error": f"TTS failed: {e}"}), 500


@app.route("/")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)