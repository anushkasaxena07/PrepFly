import os
import uuid
import json
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, redirect, Response, g
from middleware.auth import require_auth
from services.ai_service import get_current_stage, generate_dynamic_question, generate_hint
from services.interview_service import analyze_live_response
from services.feedback_service import evaluate_response_comprehensive
from services.pdf_service import generate_pdf_html_report
from services.grading_service import calculate_grade_info
from services.speech import generate_tts_audio_buffer

interview_bp = Blueprint("interview_bp", __name__)

def get_supabase():
    import app
    return app.supabase

def upload_storage(bucket_name, file_input, filename, content_type=None):
    import app
    return app.upload_to_supabase_storage(bucket_name, file_input, filename, content_type)

@interview_bp.route("/create-session-no-resume", methods=["POST"])
@require_auth(allow_optional=True)
def create_session_no_resume():
    data = request.get_json() or {}
    user_id = g.user_id or data.get("user_id")
    category = data.get("category", "General")
    difficulty = data.get("difficulty", "Medium")

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "resume_text": "",
        "question_index": 0,
        "questions": [],
        "responses": [],
        "feedbacks": [],
        "active": True,
        "category": category,
        "difficulty": difficulty
    }
    if user_id:
        session_data["user_id"] = user_id

    try:
        supabase = get_supabase()
        supabase.table("sessions").insert(session_data).execute()
    except Exception as e:
        print("Create session notice:", e)

    return jsonify({"session_id": session_id, "message": "Session created successfully"}), 200

from middleware.limiter import limiter

@interview_bp.route("/start-interview", methods=["POST"])
@limiter.limit("5 per day")
def start_interview():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        if not res or not hasattr(res, "data") or not res.data:
            return jsonify({"error": "Session not found"}), 404

        row = res.data[0]
        category = row.get("category", "DSA")
        difficulty = row.get("difficulty", "Medium")

        import app
        flash_model = getattr(app, "flash_model", app.chat_model)
        q_res = generate_dynamic_question(
            stage="Phase 1: Greeting & Icebreaker",
            resume_text=row.get("resume_text", ""),
            previous_questions=[],
            previous_responses=[],
            chat_model=flash_model,
            category=category,
            difficulty=difficulty
        )
        q1 = q_res[0] if isinstance(q_res, (list, tuple)) else q_res

        questions = [q1]
        supabase.table("sessions").update({
            "questions": json.dumps(questions),
            "question_index": 1,
            "stage": "Phase 1: Greeting & Icebreaker"
        }).eq("session_id", session_id).execute()

        return jsonify({
            "session_id": session_id,
            "question": q1,
            "stage": "Phase 1: Greeting & Icebreaker",
            "question_index": 1
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/next", methods=["POST"])
def next_question():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    answer = data.get("answer", "").strip()

    if not session_id or not answer:
        return jsonify({"error": "session_id and answer are required"}), 400

    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        if not res or not hasattr(res, "data") or not res.data:
            return jsonify({"error": "Session not found"}), 404

        row = res.data[0]
        raw_q = row.get("questions", "[]")
        raw_r = row.get("responses", "[]")
        raw_f = row.get("feedbacks", "[]")

        questions = json.loads(raw_q) if isinstance(raw_q, str) else (raw_q or [])
        responses = json.loads(raw_r) if isinstance(raw_r, str) else (raw_r or [])
        feedbacks = json.loads(raw_f) if isinstance(raw_f, str) else (raw_f or [])

        responses.append(answer)
        curr_index = len(responses)
        curr_stage = get_current_stage(curr_index)

        import app
        flash_model = getattr(app, "flash_model", app.chat_model)
        curr_q = questions[-1] if questions else "Tell me about yourself."
        if isinstance(curr_q, (list, tuple)):
            curr_q = curr_q[0] if curr_q else "Tell me about yourself."

        eval_res = evaluate_response_comprehensive(
            resume_text=row.get("resume_text", ""),
            question=curr_q,
            answer=answer,
            chat_model=flash_model,
            question_index=curr_index,
            category=row.get("category", "DSA")
        )
        if not isinstance(eval_res, dict):
            eval_res = {
                "score": 7.5,
                "feedback": "Good response provided.",
                "strength": "Attempted technical prompt",
                "improvement": "Elaborate with specific details"
            }
        elif "score" not in eval_res:
            eval_res["score"] = 7.5

        feedbacks.append(eval_res)

        # ── 3-Warning RAG Vector Recall & Escalation Engine ────────────────────────
        from services.warning_service import detect_warning, record_warning, recall_and_evaluate_warnings

        is_warning, warning_reason = detect_warning(curr_q, answer, eval_res)
        warning_count = int(row.get("warning_count", 0))
        raw_w_records = row.get("warning_records", "[]")
        warning_records = json.loads(raw_w_records) if isinstance(raw_w_records, str) else (raw_w_records or [])

        warning_info = None
        if is_warning:
            warning_count += 1
            w_record = record_warning(session_id, curr_q, answer, warning_reason, warning_count)
            warning_records.append(w_record)
            warning_info = {
                "warning_count": warning_count,
                "reason": warning_reason
            }

            # 🔌 On Warning #3: Perform Vector Embedding Recall & AI Decision Evaluation
            if warning_count >= 3:
                recall_decision = recall_and_evaluate_warnings(session_id, warning_records, w_record)
                
                if recall_decision.get("action") == "terminate":
                    supabase.table("sessions").update({
                        "questions": json.dumps(questions),
                        "responses": json.dumps(responses),
                        "feedbacks": json.dumps(feedbacks),
                        "warning_count": warning_count,
                        "warning_records": json.dumps(warning_records),
                        "active": False,
                        "stage": "Terminated"
                    }).eq("session_id", session_id).execute()

                    return jsonify({
                        "session_id": session_id,
                        "terminated": True,
                        "action": "terminate",
                        "warning_count": warning_count,
                        "reason": recall_decision.get("reason"),
                        "message": recall_decision.get("message_to_candidate"),
                        "next_question": recall_decision.get("message_to_candidate"),
                        "stage": "Terminated",
                        "feedback": eval_res
                    }), 200

        next_q_res = generate_dynamic_question(
            stage=curr_stage,
            resume_text=row.get("resume_text", ""),
            previous_questions=questions,
            previous_responses=responses,
            chat_model=flash_model,
            category=row.get("category", "DSA"),
            difficulty=row.get("difficulty", "Medium")
        )
        next_q = next_q_res[0] if isinstance(next_q_res, (list, tuple)) else next_q_res
        questions.append(next_q)

        supabase.table("sessions").update({
            "questions": json.dumps(questions),
            "responses": json.dumps(responses),
            "feedbacks": json.dumps(feedbacks),
            "warning_count": warning_count,
            "warning_records": json.dumps(warning_records),
            "question_index": curr_index + 1,
            "stage": curr_stage
        }).eq("session_id", session_id).execute()

        return jsonify({
            "session_id": session_id,
            "feedback": eval_res,
            "next_question": next_q,
            "stage": curr_stage,
            "question_index": curr_index + 1,
            "warning_info": warning_info
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/get-hint", methods=["POST"])
def get_hint_route():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        if not res or not hasattr(res, "data") or not res.data:
            return jsonify({"error": "Session not found"}), 404

        row = res.data[0]
        raw_q = row.get("questions", "[]")
        questions = json.loads(raw_q) if isinstance(raw_q, str) else (raw_q or [])
        curr_q = questions[-1] if questions else "General Question"

        import app
        flash_model = getattr(app, "flash_model", app.chat_model)
        hint = generate_hint(curr_q, flash_model)
        return jsonify({"hint": hint}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/get-session", methods=["GET"])
def get_session():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        if not res or not hasattr(res, "data") or not res.data:
            return jsonify({"error": "Session not found"}), 404

        row = res.data[0]
        for fld in ("questions", "responses", "feedbacks"):
            if isinstance(row.get(fld), str):
                try: row[fld] = json.loads(row[fld])
                except: pass

        return jsonify(row), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/user-sessions", methods=["GET"])
def get_user_sessions():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify([]), 200
    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("user_id", user_id).execute()
        data = res.data if (res and hasattr(res, "data") and res.data) else []
        return jsonify(data), 200
    except Exception as e:
        return jsonify([]), 200

@interview_bp.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        buf = generate_tts_audio_buffer(text)
        return send_file(buf, mimetype="audio/mpeg", as_attachment=False, download_name="speech.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/end-interview", methods=["POST"])
def end_interview():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        if not res or not hasattr(res, "data") or not res.data:
            return jsonify({"error": "Session not found"}), 404

        row = res.data[0]
        raw_q = row.get("questions", "[]")
        raw_r = row.get("responses", "[]")
        raw_f = row.get("feedbacks", "[]")

        questions = json.loads(raw_q) if isinstance(raw_q, str) else (raw_q or [])
        responses = json.loads(raw_r) if isinstance(raw_r, str) else (raw_r or [])
        feedbacks = json.loads(raw_f) if isinstance(raw_f, str) else (raw_f or [])

        scores = [f.get("score", 7) for f in feedbacks if isinstance(f, dict)]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 7.5
        g_info = calculate_grade_info(avg_score * 10)

        report_md = f"### Overall Score: {avg_score}/10\nGrade: {g_info['grade']}\nPerformance Summary: Good candidate demonstration."

        supabase.table("sessions").update({
            "active": False,
            "final_score": avg_score,
            "final_grade": g_info["grade"],
            "final_report": report_md,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("session_id", session_id).execute()

        return jsonify({
            "session_id": session_id,
            "overall_score": avg_score,
            "grade": g_info["grade"],
            "report": report_md
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/save-recording", methods=["POST"])
def save_recording():
    try:
        if "video" in request.files:
            file = request.files["video"]
            session_id = request.form.get("session_id")
            if not session_id:
                return jsonify({"error": "session_id is required"}), 400
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "webm"
            filename = f"recording_{session_id}.{ext}"
            file_bytes = file.read()
        else:
            data = request.get_json() or {}
            session_id = data.get("session_id")
            video_b64 = data.get("video_base64")
            mime_type = data.get("mime_type", "video/webm")

            if not session_id or not video_b64:
                return jsonify({"error": "session_id and video_base64/file are required"}), 400

            file_bytes = base64.b64decode(video_b64)
            ext = mime_type.split("/")[-1] if "/" in mime_type else "webm"
            if ";" in ext: ext = ext.split(";")[0]
            filename = f"recording_{session_id}.{ext}"

        mime = f"video/{ext}" if ext in ("webm", "mp4") else f"audio/{ext}"
        recording_url = upload_storage("recordings", file_bytes, filename, mime)

        supabase = get_supabase()
        supabase.table("sessions").update({"recording_path": recording_url}).eq("session_id", session_id).execute()

        return jsonify({"message": "Recording saved successfully", "path": recording_url, "recording_url": recording_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/recording/<session_id>", methods=["GET"])
def get_recording_file(session_id):
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("recording_path").eq("session_id", session_id).execute()
        if res and hasattr(res, "data") and res.data:
            rec_path = res.data[0].get("recording_path")
            if rec_path and rec_path.startswith("http"):
                return redirect(rec_path)
        return jsonify({"error": "Recording not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@interview_bp.route("/session-report/<session_id>", methods=["GET"])
@interview_bp.route("/api/session-report/<session_id>", methods=["GET"])
def get_session_report(session_id):
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()
        if not res or not hasattr(res, "data") or not res.data:
            return jsonify({"error": "Session not found"}), 404
        return jsonify(res.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def resolve_target_user_id(user_id_param):
    if not user_id_param or user_id_param in ["me", "user_default", "undefined", "null"]:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                import jwt
                secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "c8fa4668d31b53d0b5dd4786fe27e2946a527436f95869970a5118bf48c6f342"
                payload = jwt.decode(token, secret, algorithms=["HS256"])
                return payload.get("sub") or payload.get("email") or "user_default"
            except Exception:
                pass
        return "user_default"
    return user_id_param

@interview_bp.route("/history", methods=["GET", "OPTIONS"])
@interview_bp.route("/history/me", methods=["GET", "OPTIONS"])
@interview_bp.route("/history/<user_id>", methods=["GET", "OPTIONS"])
@interview_bp.route("/api/history", methods=["GET", "OPTIONS"])
@interview_bp.route("/api/history/me", methods=["GET", "OPTIONS"])
@interview_bp.route("/api/history/<user_id>", methods=["GET", "OPTIONS"])
def get_user_history(user_id="me"):
    if request.method == "OPTIONS":
        return jsonify([]), 200
    target_id = resolve_target_user_id(user_id)
    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("user_id", target_id).execute()
        data = res.data if (res and hasattr(res, "data") and res.data) else []
        return jsonify(data), 200
    except Exception as e:
        print("User history notice:", e)
        return jsonify([]), 200

@interview_bp.route("/user-stats", methods=["GET", "OPTIONS"])
@interview_bp.route("/user-stats/me", methods=["GET", "OPTIONS"])
@interview_bp.route("/user-stats/<user_id>", methods=["GET", "OPTIONS"])
@interview_bp.route("/api/user-stats", methods=["GET", "OPTIONS"])
@interview_bp.route("/api/user-stats/me", methods=["GET", "OPTIONS"])
@interview_bp.route("/api/user-stats/<user_id>", methods=["GET", "OPTIONS"])
def get_user_stats(user_id="me"):
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    target_id = resolve_target_user_id(user_id)
    try:
        supabase = get_supabase()
        res = supabase.table("sessions").select("*").eq("user_id", target_id).execute()
        rows = res.data if (res and hasattr(res, "data") and res.data) else []
        
        count = len(rows)
        scores = [float(r.get("overall_score") or r.get("final_score") or 7.5) for r in rows if r.get("overall_score") or r.get("final_score")]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        return jsonify({
            "user_id": target_id,
            "streak_days": 1 if count > 0 else 0,
            "has_data": count > 0,
            "interviews": {
                "count": count,
                "avg_score": avg_score
            },
            "stats": {
                "total_interviews": count,
                "avg_score": avg_score,
                "streak": 1 if count > 0 else 0
            }
        }), 200
    except Exception as e:
        print("User stats notice:", e)
        return jsonify({
            "user_id": target_id,
            "streak_days": 0,
            "has_data": False,
            "interviews": {"count": 0, "avg_score": 0.0},
            "stats": {"total_interviews": 0, "avg_score": 0.0, "streak": 0}
        }), 200

@interview_bp.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    try:
        supabase = get_supabase()
        supabase.table("sessions").delete().eq("session_id", session_id).execute()
        return jsonify({"message": "Session deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
