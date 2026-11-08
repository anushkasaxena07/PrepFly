"""
Interview Blueprint: Production REST API endpoints for Ava AI Interview Engine.
Provides personality profiles, session lifecycle, turn execution, pause/resume,
session recovery, resume claim inspection, and interview history.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone

from services.interviewer_personality_service import InterviewerPersonalityService
from services.interview_state_service import InterviewStateService, STATE_PAUSED, STATE_WAITING_FOR_RESPONSE
from services.interview_orchestrator import InterviewOrchestrator
from services.resume_intelligence_service import ResumeIntelligenceService

interview_bp = Blueprint("interview", __name__, url_prefix="/api/interview")

def _get_supabase():
    try:
        import app
        return app.supabase
    except Exception:
        from local_supabase import SQLiteSupabaseMock
        return SQLiteSupabaseMock()

def _get_user_id():
    try:
        import app
        user = app._get_optional_user()
        if user:
            return user.get("sub") or user.get("user_id") or user.get("id")
    except Exception:
        pass
    return request.headers.get("X-User-Id") or "anonymous_candidate"


@interview_bp.route("/personalities", methods=["GET"])
def get_personalities():
    """Returns available interviewer personalities with tone, formality, and probing metadata."""
    personalities = InterviewerPersonalityService.get_supported_personalities()
    return jsonify({
        "status": "success",
        "personalities": list(personalities.values()),
        "default": "professional"
    }), 200


@interview_bp.route("/session/<session_id>/recover", methods=["GET"])
def recover_session_endpoint(session_id: str):
    """Restores full session state after network disconnect, failure, or page reload."""
    supabase = _get_supabase()
    recovery_data = InterviewStateService.recover_session(supabase, session_id)
    if not recovery_data.get("recovered"):
        return jsonify(recovery_data), 404
    return jsonify({
        "status": "success",
        "session": recovery_data
    }), 200


@interview_bp.route("/session/<session_id>/pause", methods=["POST"])
def pause_session(session_id: str):
    """Pauses an active interview session."""
    supabase = _get_supabase()
    success = InterviewStateService.transition_state(supabase, session_id, STATE_PAUSED)
    if not success:
        return jsonify({"error": "Failed to pause session or invalid state transition"}), 400
    return jsonify({
        "status": "success",
        "message": "Interview session paused",
        "session_id": session_id,
        "interview_state": STATE_PAUSED
    }), 200


@interview_bp.route("/session/<session_id>/resume", methods=["POST"])
def resume_session(session_id: str):
    """Resumes a paused interview session."""
    supabase = _get_supabase()
    success = InterviewStateService.transition_state(supabase, session_id, STATE_WAITING_FOR_RESPONSE)
    if not success:
        return jsonify({"error": "Failed to resume session"}), 400
    return jsonify({
        "status": "success",
        "message": "Interview session resumed",
        "session_id": session_id,
        "interview_state": STATE_WAITING_FOR_RESPONSE
    }), 200


@interview_bp.route("/session/<session_id>/turns", methods=["GET"])
def get_session_turns(session_id: str):
    """Fetches relational turn audit records with questions, responses, intents, decisions, and scores."""
    supabase = _get_supabase()
    try:
        res = supabase.table("interview_turns").select("*").eq("session_id", session_id).order("turn_number").execute()
        turns = res.data if res and hasattr(res, "data") else []
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "turns": turns,
            "count": len(turns)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@interview_bp.route("/resume/profile", methods=["POST"])
def get_resume_profile():
    """Extracts structured candidate profile and verified claims from uploaded resume text."""
    data = request.get_json() or {}
    resume_text = data.get("resume_text", "")
    if not resume_text:
        return jsonify({"error": "resume_text is required"}), 400

    profile = ResumeIntelligenceService.extract_structured_candidate_profile(resume_text)
    return jsonify({
        "status": "success",
        "profile": profile
    }), 200


@interview_bp.route("/history", methods=["GET"])
def get_interview_history():
    """Returns paginated past interview history for the authenticated user."""
    supabase = _get_supabase()
    user_id = _get_user_id()
    limit = min(50, max(1, int(request.args.get("limit", 10))))
    offset = max(0, int(request.args.get("offset", 0)))

    try:
        query = supabase.table("sessions").select("session_id, role, category, difficulty, personality, final_score, final_grade, active, created_at, updated_at")
        if user_id and user_id != "anonymous_candidate":
            query = query.eq("user_id", user_id)
        res = query.order("created_at", desc=True).limit(limit).execute()
        history = res.data if res and hasattr(res, "data") else []
        return jsonify({
            "status": "success",
            "history": history,
            "count": len(history),
            "limit": limit,
            "offset": offset
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

