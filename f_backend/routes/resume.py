import os
import uuid
import json
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from services.ats import extract_text_from_pdf, extract_text_from_docx, parse_resume_content, calculate_ats_match

resume_bp = Blueprint("resume_bp", __name__)

def get_supabase():
    import app
    return app.supabase

def upload_storage(bucket_name, file_input, filename, content_type=None):
    import app
    return app.upload_to_supabase_storage(bucket_name, file_input, filename, content_type)

from middleware.limiter import limiter

@resume_bp.route("/upload", methods=["POST"])
@limiter.limit("10 per hour")
def upload_resume():
    file = None
    if "resume" in request.files:
        file = request.files["resume"]
    elif "file" in request.files:
        file = request.files["file"]

    if not file or not file.filename:
        return jsonify({"error": "No resume file provided"}), 400

    user_id = request.form.get("user_id")
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "docx"):
        return jsonify({"error": "Only PDF and DOCX files are supported"}), 400

    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_bytes = file.read()

    try:
        # Upload resume directly to Supabase Storage bucket 'resumes'
        content_type = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        resume_url = upload_storage("resumes", file_bytes, unique_filename, content_type)

        # Temp extraction
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            resume_text = extract_text_from_pdf(tmp_path) if ext == "pdf" else extract_text_from_docx(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not resume_text.strip():
            return jsonify({"error": "Could not extract text from resume"}), 400

        import app
        parse_result = parse_resume_content(resume_text, app.chat_model)

        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "resume_text": resume_text,
            "storage_path": resume_url,
            "question_index": 0,
            "questions": [],
            "responses": [],
            "feedbacks": [],
            "active": True,
            "ats_score": parse_result.get("ats_score", 70),
            "structured_resume": json.dumps(parse_result.get("structured_data", {}))
        }
        if user_id:
            session_data["user_id"] = user_id

        try:
            supabase = get_supabase()
            supabase.table("sessions").insert(session_data).execute()
        except Exception as db_err:
            print("Session DB insert notice:", db_err)

        return jsonify({
            "message": "Resume uploaded successfully",
            "session_id": session_id,
            "resume_url": resume_url,
            "storage_path": resume_url,
            "text_length": len(resume_text),
            "resume_text": resume_text,
            "ats_score": parse_result.get("ats_score", 70),
            "structured_data": parse_result.get("structured_data", {}),
            "missing_info": parse_result.get("missing_info", [])
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from services.redis_service import cache_get, cache_set

@resume_bp.route("/api/resume/analyze-ats", methods=["POST"])
def analyze_ats():
    data = request.get_json() or {}
    resume_text = data.get("resume_text", "")
    job_description = data.get("job_description", "")

    if not resume_text:
        return jsonify({"error": "resume_text is required"}), 400

    import hashlib
    cache_key = f"ats_cache:{hashlib.md5((resume_text + job_description).encode()).hexdigest()}"
    cached_res = cache_get(cache_key)
    if cached_res:
        return jsonify(cached_res), 200

    import app
    parse_res = parse_resume_content(resume_text, app.chat_model)
    ats_score = parse_res.get("ats_score", 70)

    result = {
        "ats_score": ats_score,
        "structured_data": parse_res.get("structured_data", {}),
        "missing_info": parse_res.get("missing_info", []),
        "suggestions": ["Include quantified metrics", "Add relevant tech stack keywords"]
    }
    cache_set(cache_key, result, ttl_seconds=7200)
    return jsonify(result), 200

@resume_bp.route("/api/resume/parse-cached", methods=["GET"])
def parse_cached():
    text_hash = request.args.get("hash")
    if not text_hash:
        return jsonify({"error": "hash is required"}), 400

    try:
        supabase = get_supabase()
        res = supabase.table("parsed_resumes").select("*").eq("hash", text_hash).execute()
        if res and hasattr(res, "data") and res.data:
            return jsonify(res.data[0]), 200
        return jsonify({"message": "Not found in cache"}), 444
    except Exception as e:
        return jsonify({"error": str(e)}), 500
