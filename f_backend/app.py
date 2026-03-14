import os
import fitz
import uuid
import random
import base64
import threading
from io import BytesIO

from docx import Document
from flask import Flask, request, jsonify, send_file, redirect
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

# To this:
CORS(app, resources={r"/*": {
    "origins": ["http://localhost:5173", "http://localhost:5174"],
    "supports_credentials": True
}})

# ─── Supabase Setup ────────────────────────────────────────────────────────────
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


def generate_question(resume_text: str, previous_questions: list = None) -> str:
    """Generate a Gemini-powered interview question based on the resume."""
    focus_areas = [
        "technical skills and tools",
        "work experience and achievements",
        "education and learning approach",
        "problem-solving ability",
        "team collaboration and leadership",
        "a specific project mentioned in the resume",
        "career goals and motivation",
    ]
    focus = random.choice(focus_areas)
    prev_q_text = ""
    if previous_questions:
        prev_q_text = "Already asked questions (do NOT repeat these):\n" + "\n".join(
            f"- {q}" for q in previous_questions[-5:]
        )

    prompt = f"""You are Hana, a friendly but thorough anime-style AI interviewer conducting a real technical job interview.
Based on the candidate's resume, generate ONE clear, specific interview question.
Focus area this time: {focus}

{prev_q_text}

Rules:
- Ask only ONE question (1-2 sentences max)
- Be specific to what's actually in their resume
- Sound natural and conversational, like a real interviewer
- Do NOT include any preamble like "Here is a question:" — just ask the question directly

Resume Content:
{resume_text[:3000]}
"""
    try:
        res = chat_model.invoke([HumanMessage(content=prompt)])
        return res.content.strip()
    except Exception as e:
        return f"Tell me about your most impactful project from your resume."


def analyze_response(resume_text: str, question: str, response: str) -> dict:
    """
    Analyze candidate response and return structured feedback with a score.
    Returns: { feedback: str, score: int (0-10), strengths: [], improvements: [] }
    """
    prompt = f"""You are Hana, an expert AI interviewer. Evaluate this candidate's interview answer professionally.

Resume (context): {resume_text[:1000]}
Interview Question: {question}
Candidate's Answer: {response}

Provide your evaluation in this EXACT format (keep each section brief):

SCORE: [number 1-10]
STRENGTH: [one specific strength of this answer in 1 sentence]
IMPROVEMENT: [one specific area to improve in 1 sentence]
TIP: [one concrete actionable tip in 1 sentence]
SUMMARY: [2-3 sentence overall assessment]
"""
    try:
        result = chat_model.invoke([HumanMessage(content=prompt)])
        raw = result.content.strip()

        # Parse structured response
        lines = raw.split("\n")
        score = 7  # default
        strength = ""
        improvement = ""
        tip = ""
        summary = ""

        for line in lines:
            line = line.strip()
            if line.startswith("SCORE:"):
                try:
                    score = int(line.replace("SCORE:", "").strip().split()[0])
                    score = max(1, min(10, score))
                except:
                    score = 7
            elif line.startswith("STRENGTH:"):
                strength = line.replace("STRENGTH:", "").strip()
            elif line.startswith("IMPROVEMENT:"):
                improvement = line.replace("IMPROVEMENT:", "").strip()
            elif line.startswith("TIP:"):
                tip = line.replace("TIP:", "").strip()
            elif line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()

        feedback_text = f"✅ Strength: {strength}\n⚠️ Improve: {improvement}\n💡 Tip: {tip}"
        if summary:
            feedback_text += f"\n\n{summary}"

        return {
            "feedback": feedback_text,
            "score": score,
            "strength": strength,
            "improvement": improvement,
            "tip": tip,
            "summary": summary,
        }
    except Exception as e:
        return {
            "feedback": f"Good attempt. Keep practicing to give more structured and detailed answers.",
            "score": 6,
            "strength": "You attempted to answer the question",
            "improvement": "Add more specific details and examples",
            "tip": "Use the STAR method: Situation, Task, Action, Result",
            "summary": "Keep practicing to improve your interview skills.",
        }


def compute_final_score(scores: list, feedbacks: list, resume_text: str) -> dict:
    """Compute final interview score and generate an overall report using Gemini."""
    if not scores:
        return {"overall_score": 0, "grade": "N/A", "report": "No answers recorded."}

    avg = round(sum(scores) / len(scores), 1)

    # Grade mapping
    if avg >= 9:
        grade = "S"
    elif avg >= 8:
        grade = "A"
    elif avg >= 7:
        grade = "B"
    elif avg >= 6:
        grade = "C"
    elif avg >= 5:
        grade = "D"
    else:
        grade = "F"

    # Ask Gemini for a final holistic report
    feedback_summary = "\n".join(
        f"Q{i+1} (Score {scores[i]}/10): {fb}" for i, fb in enumerate(feedbacks)
    )
    prompt = f"""You are Hana, an AI interviewer. The candidate just completed their interview.
Here is their performance summary:

Average Score: {avg}/10
Individual Feedback:
{feedback_summary[:2000]}

Write a 3-4 sentence final performance report. Be honest but encouraging.
Mention their top strength and the single most important area to work on.
End with an encouraging closing line. Keep it warm and professional.
"""
    try:
        res = chat_model.invoke([HumanMessage(content=prompt)])
        report = res.content.strip()
    except:
        report = f"You completed the interview with an average score of {avg}/10. Keep practicing!"

    return {
        "overall_score": avg,
        "grade": grade,
        "report": report,
        "total_questions": len(scores),
    }


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
            "options":  {"data": {"name": name}}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if auth_res.user is None:
        return jsonify({"error": "Registration failed – check email/password requirements"}), 400

    user_id = auth_res.user.id
    if name:
        try:
            supabase.table("users").update({"name": name}).eq("id", user_id).execute()
        except Exception:
            pass

    return jsonify({"message": "Registration successful. Please verify your email."}), 201


@app.route("/login", methods=["POST"])
def login():
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
        pass

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


@app.route("/auth/google/verify", methods=["POST"])
def google_verify():
    """
    Verifies the Google ID token directly with Google (no Supabase Auth).
    Upserts the user into your own `users` table — zero rate-limit exposure.
    """
    data       = request.json or {}
    credential = data.get("credential", "").strip()

    if not credential:
        return jsonify({"error": "Google credential is required"}), 400

    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not google_client_id:
        return jsonify({"error": "GOOGLE_CLIENT_ID is not set in .env"}), 500

    try:
        # 1. Verify token directly with Google -- no Supabase Auth call
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            google_client_id,
        )

        google_sub = idinfo["sub"]          # unique stable Google user ID
        email      = idinfo.get("email", "")
        name       = idinfo.get("name", "")
        avatar     = idinfo.get("picture", "")

        # 2. Look up by google_id first (returning user)
        existing = (
            supabase.table("users")
            .select("id, name, role, phone, avatar")
            .eq("google_id", google_sub)
            .maybe_single()
            .execute()
        )

        # ADD NULL CHECK HERE
        if existing and existing.data:
            user    = existing.data
            user_id = user["id"]

        else:
            # Check if email already exists (link accounts)
            by_email = (
                supabase.table("users")
                .select("id, name, role, phone, avatar")
                .eq("email", email)
                .maybe_single()
                .execute()
            )
            
            # ADD NULL CHECK HERE
            if by_email and by_email.data:
                user_id = by_email.data["id"]
                supabase.table("users").update({
                    "google_id": google_sub,
                    "avatar":    by_email.data.get("avatar") or avatar,
                }).eq("id", user_id).execute()
                user = by_email.data
            else:
                # Brand new user
                new_row = supabase.table("users").insert({
                    "email":     email,
                    "name":      name,
                    "avatar":    avatar,
                    "google_id": google_sub,
                }).execute()
                
                # ADD NULL CHECK HERE
                if not new_row or not new_row.data or len(new_row.data) == 0:
                    return jsonify({"error": "Failed to create user in database"}), 500
                    
                user    = new_row.data[0]
                user_id = user["id"]

        return jsonify({
            "message": "Signed in with Google successfully",
            "email":   email,
            "user_id": user_id,
            "name":    user.get("name") or name,
            "role":    user.get("role", ""),
            "phone":   user.get("phone", ""),
            "avatar":  user.get("avatar") or avatar,
        }), 200

    except ValueError as e:
        return jsonify({"error": f"Invalid Google token: {str(e)}"}), 401
    except Exception as e:
        # Add more detailed error logging
        print(f"Google verify error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Google sign-in failed: {str(e)}"}), 500

@app.route("/update-profile", methods=["PUT"])
def update_profile():
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
        "questions":      [],
        "responses":      [],
        "feedbacks":      [],
        "scores":         [],
        "active":         True,
    }

    supabase.table("sessions").upsert(session_row, on_conflict="session_id").execute()

    return jsonify({"message": "Resume processed", "session_id": session_id})


@app.route("/next", methods=["POST"])
def next_question():
    """Generate and return the next interview question via Gemini."""
    session_id = (request.json or {}).get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Invalid session"}), 404

    if not session.get("active"):
        return jsonify({"message": "Interview complete"}), 200

    previous_questions = session.get("questions", [])
    question           = generate_question(session["resume_text"], previous_questions)
    updated_questions  = previous_questions + [question]

    supabase.table("sessions").update({
        "questions":      updated_questions,
        "question_index": len(updated_questions) - 1,
    }).eq("session_id", session_id).execute()

    return jsonify({
        "question":        question,
        "question_number": len(updated_questions),
    })


@app.route("/response", methods=["POST"])
def submit_response():
    """Submit a candidate answer. Accepts text OR base64 audio (transcribed via Gemini)."""
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

    # Analyze and score the response
    analysis = analyze_response(session["resume_text"], current_question, response_text)

    supabase.table("sessions").update({
        "responses": session.get("responses", []) + [response_text],
        "feedbacks": session.get("feedbacks", []) + [analysis["feedback"]],
        "scores":    session.get("scores", []) + [analysis["score"]],
    }).eq("session_id", session_id).execute()

    return jsonify({
        "feedback":    analysis["feedback"],
        "score":       analysis["score"],
        "strength":    analysis["strength"],
        "improvement": analysis["improvement"],
        "tip":         analysis["tip"],
    })


def _grade_from_avg(avg: float) -> str:
    if avg >= 9: return "S"
    if avg >= 8: return "A"
    if avg >= 7: return "B"
    if avg >= 6: return "C"
    if avg >= 5: return "D"
    return "F"


def _generate_report_async(session_id: str, scores: list, feedbacks: list, resume_text: str, avg: float, grade: str):
    """Runs in background thread — generates Gemini report and saves it."""
    feedback_summary = "\n".join(
        f"Q{i+1} (Score {scores[i]}/10): {fb}" for i, fb in enumerate(feedbacks)
    )
    prompt = f"""You are Hana, an AI interviewer. The candidate just completed their interview.
Here is their performance summary:

Average Score: {avg}/10  Grade: {grade}
Individual Feedback:
{feedback_summary[:2000]}

Write a 3-4 sentence final performance report. Be honest but encouraging.
Mention their top strength and the single most important area to work on.
End with an encouraging closing line. Keep it warm and professional.
"""
    try:
        res    = chat_model.invoke([HumanMessage(content=prompt)])
        report = res.content.strip()
    except Exception:
        report = f"You completed the interview with an average score of {avg}/10. Keep practising!"

    try:
        supabase.table("sessions").update({"final_report": report}).eq("session_id", session_id).execute()
    except Exception:
        pass


@app.route("/end-interview", methods=["POST"])
def end_interview():
    """End the interview — returns instantly with score/grade, generates Gemini report in background."""
    session_id = (request.json or {}).get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    session = _get_session(session_id)
    if not session:
        return jsonify({"error": "Invalid session"}), 404

    scores    = session.get("scores", [])
    feedbacks = session.get("feedbacks", [])

    # Instant math — no Gemini needed
    avg   = round(sum(scores) / len(scores), 1) if scores else 0.0
    grade = _grade_from_avg(avg)

    # Mark session done immediately
    supabase.table("sessions").update({
        "active":      False,
        "final_score": avg,
        "final_grade": grade,
    }).eq("session_id", session_id).execute()

    # Fire-and-forget background report generation
    threading.Thread(
        target=_generate_report_async,
        args=(session_id, scores, feedbacks, session.get("resume_text", ""), avg, grade),
        daemon=True,
    ).start()

    return jsonify({
        "message":         "Interview ended",
        "questions":       session.get("questions", []),
        "responses":       session.get("responses", []),
        "feedbacks":       feedbacks,
        "scores":          scores,
        "overall_score":   avg,
        "grade":           grade,
        "report":          "Generating your personalised report… check back in a moment.",
        "total_questions": len(scores),
    })


@app.route("/session-report/<session_id>", methods=["GET"])
def session_report(session_id: str):
    """Poll for the async Gemini final report once it is ready."""
    try:
        res = (
            supabase.table("sessions")
            .select("final_report, final_score, final_grade")
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        return jsonify(res.data or {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history/<user_id>", methods=["GET"])
def interview_history(user_id: str):
    res = (
        supabase.table("sessions")
        .select("session_id, question_index, active, created_at, questions, feedbacks, scores, final_score, final_grade")
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
    """Convert text to speech audio (MP3). Used by the anime interviewer."""
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        # Use a friendly, slightly higher-pitched voice for the anime character
        tts = gTTS(text=text, lang="en", slow=False)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg", download_name="speech.mp3")
    except Exception as e:
        return jsonify({"error": f"TTS failed: {e}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT ROUTE (via Gemini multimodal)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/speech-to-text", methods=["POST"])
def speech_to_text():
    """
    Accepts base64-encoded audio (WebM/OGG from browser MediaRecorder).
    Uses Gemini's multimodal capability to transcribe it.
    Body: { audio_base64: "...", mime_type: "audio/webm" }
    """
    data         = request.json or {}
    audio_b64    = data.get("audio_base64", "").strip()
    mime_type    = data.get("mime_type", "audio/webm")

    if not audio_b64:
        return jsonify({"error": "audio_base64 is required"}), 400

    try:
        # Use Gemini multimodal to transcribe audio
        gemini_vision = ChatGoogleGenerativeAI(
            api_key=GEMINI_API_KEY, model="gemini-2.5-flash-lite", temperature=0.0
        )

        message = HumanMessage(
            content=[
                {
                    "type": "media",
                    "data": audio_b64,
                    "mime_type": mime_type,
                },
                {
                    "type": "text",
                    "text": "Please transcribe this audio recording accurately. Return ONLY the transcribed text, nothing else.",
                },
            ]
        )
        res = gemini_vision.invoke([message])
        transcript = res.content.strip()
        return jsonify({"transcript": transcript})
    except Exception as e:
        return jsonify({"error": f"Transcription failed: {e}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  SAVE RECORDING ROUTE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/save-recording", methods=["POST"])
def save_recording():
    """
    Save the session video recording to Supabase storage (best-effort).
    Body: { session_id: str, video_base64: str, mime_type: str }
    """
    data        = request.json or {}
    session_id  = data.get("session_id", "")
    video_b64   = data.get("video_base64", "")
    mime_type   = data.get("mime_type", "video/webm")

    if not session_id or not video_b64:
        return jsonify({"error": "session_id and video_base64 are required"}), 400

    try:
        video_bytes  = base64.b64decode(video_b64)
        storage_path = f"recordings/{session_id}.webm"
        supabase.storage.from_("recordings").upload(
            path=storage_path,
            file=video_bytes,
            file_options={"content-type": mime_type},
        )
        supabase.table("sessions").update(
            {"recording_path": storage_path}
        ).eq("session_id", session_id).execute()
        return jsonify({"message": "Recording saved", "path": storage_path})
    except Exception as e:
        return jsonify({"error": f"Failed to save recording: {e}"}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def health():
    return jsonify({"status": "ok", "service": "InterviewAI Backend"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)