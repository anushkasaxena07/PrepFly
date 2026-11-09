"""
Mentor API Blueprint for PrepFly Adaptive AI Mentor.
Exposes endpoints for conversational onboarding, 7-step learning workspaces,
rubric-based assignment evaluation, and persistent contextual mentor chat.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import json

from services.mentor_service import MentorService
from services.learning_service import LearningService
from services.conversational_onboarding_service import ConversationalOnboardingService
from local_supabase import get_supabase_client

mentor_bp = Blueprint("mentor_bp", __name__)


def _extract_user_id() -> str:
    """Extracts user ID from request headers or body, defaulting safely for development."""
    user_id = request.headers.get("X-User-Id") or request.headers.get("x-user-id")
    if not user_id:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")
    return user_id or "candidate"


# ─── MENTOR CONVERSATION ROUTES ─────────────────────────────────────────────

@mentor_bp.route("/api/mentor/conversations", methods=["POST"])
def start_or_resume_conversation():
    user_id = _extract_user_id()
    data = request.get_json(silent=True) or {}
    title = data.get("title")

    conv = MentorService.start_or_resume_conversation(user_id, title)
    return jsonify({"conversation": conv}), 200


@mentor_bp.route("/api/mentor/conversations/<conv_id>/messages", methods=["GET", "POST"])
def handle_conversation_messages(conv_id):
    if request.method == "GET":
        messages = MentorService.get_conversation_messages(conv_id)
        return jsonify({"messages": messages}), 200

    user_id = _extract_user_id()
    data = request.get_json(silent=True) or {}
    message_text = data.get("message", "").strip()
    active_activity = data.get("active_activity")

    if not message_text:
        return jsonify({"error": "Message content cannot be empty"}), 400

    result = MentorService.send_mentor_message(
        user_id=user_id,
        conversation_id=conv_id,
        user_message=message_text,
        active_activity=active_activity
    )
    return jsonify(result), 200


# ─── 7-STEP LEARNING WORKSPACE ROUTES ───────────────────────────────────────

@mentor_bp.route("/api/mentor/workspace/<activity_id>", methods=["GET"])
def get_learning_workspace(activity_id):
    user_id = _extract_user_id()
    skill_id = request.args.get("skill_id")
    target_role = request.args.get("target_role")
    target_company = request.args.get("target_company")

    workspace = LearningService.get_learning_workspace(
        activity_id=activity_id,
        skill_id=skill_id,
        target_role=target_role,
        target_company=target_company
    )
    return jsonify({"workspace": workspace}), 200


@mentor_bp.route("/api/mentor/workspace/<activity_id>/submit", methods=["POST"])
def submit_assignment(activity_id):
    user_id = _extract_user_id()
    data = request.get_json(silent=True) or {}
    submission_text = data.get("submission_text", "")
    code_submission = data.get("code_submission", "")

    if not submission_text and not code_submission:
        return jsonify({"error": "Submission must contain code or an explanation"}), 400

    evaluation = LearningService.submit_and_evaluate_assignment(
        user_id=user_id,
        activity_id=activity_id,
        submission_text=submission_text,
        code_submission=code_submission
    )
    return jsonify({"evaluation": evaluation}), 200


# ─── CONVERSATIONAL ONBOARDING ROUTES ───────────────────────────────────────

@mentor_bp.route("/api/mentor/parse-jd", methods=["POST"])
def parse_job_description():
    data = request.get_json(silent=True) or {}
    jd_text = data.get("job_description", "")
    target_role = data.get("target_role")
    target_company = data.get("target_company")

    categorized = ConversationalOnboardingService.parse_job_description(
        jd_text=jd_text,
        target_role=target_role,
        target_company=target_company
    )
    return jsonify({"categorized_requirements": categorized}), 200


@mentor_bp.route("/api/mentor/onboarding/complete", methods=["POST"])
def complete_onboarding():
    user_id = _extract_user_id()
    data = request.get_json(silent=True) or {}

    result = ConversationalOnboardingService.complete_onboarding(
        user_id=user_id,
        onboarding_data=data
    )
    return jsonify(result), 200

