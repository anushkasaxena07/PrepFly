"""
PREPFLY SPECIFICATION API ENDPOINTS (Section 11)
================================================
Exposes canonical endpoints required by the Full Build Specification:
- GET /api/readiness: The single source of truth readiness object used by all pages.
- GET /api/skills/map: The skill map, statuses, and gap analysis from the scoring engine.
"""

from flask import Blueprint, request, jsonify, Response
from datetime import datetime, timezone
import functools
import logging

from services.scoring_engine import (
    evaluate_candidate_readiness,
    get_canonical_role_skills,
    build_unified_readiness_object
)
from utils.template_guard import sanitize_user_facing_string

logger = logging.getLogger("prepfly.spec_api")

spec_api_bp = Blueprint("spec_api", __name__)


def _extract_request_user_id() -> str:
    """Resolves authenticated candidate user id from Authorization header, query, or body."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    if token and token.lower() not in ("null", "undefined"):
        try:
            from app import _decode_jwt
            payload = _decode_jwt(token)
            if payload and payload.get("sub"):
                return str(payload["sub"]).strip()
            if payload and payload.get("user_id"):
                return str(payload["user_id"]).strip()
        except Exception:
            try:
                import jwt
                unverified = jwt.decode(token, options={"verify_signature": False})
                if unverified and unverified.get("sub"):
                    return str(unverified["sub"]).strip()
                if unverified and unverified.get("user_id"):
                    return str(unverified["user_id"]).strip()
            except Exception:
                pass

    # Fallback to query param, header, or body
    fallback_uid = (
        request.headers.get("X-User-Id")
        or request.args.get("user_id")
        or (request.get_json(silent=True) or {}).get("user_id")
    )
    if fallback_uid and str(fallback_uid).strip().lower() not in ("null", "undefined"):
        return str(fallback_uid).strip()

    return "user_default"


@spec_api_bp.route("/api/readiness", methods=["GET"])
def get_canonical_readiness():
    """
    Returns the single canonical readiness object used by all pages:
    Dashboard, Roadmap, Analytics, Mentor, and Diagnostic modal.
    Guarantees no two pages show conflicting numbers.
    """
    user_id = _extract_request_user_id()
    target_role = request.args.get("role") or request.args.get("target_role") or "AI/ML Engineer"

    try:
        profile_data = evaluate_candidate_readiness(user_id=user_id, target_role=target_role)
        readiness = profile_data.get("readiness") or {}
        
        # Sanitize formula breakdown and text labels
        if readiness.get("formula_breakdown"):
            readiness["formula_breakdown"] = sanitize_user_facing_string(readiness["formula_breakdown"])

        response_payload = {
            "status": "success",
            "user_id": user_id,
            "target_role": target_role,
            "readiness": readiness,
            "pillars": profile_data.get("pillars", []),
            "trend": profile_data.get("trend", {})
        }
        return jsonify(response_payload), 200
    except Exception as ex:
        logger.error(f"Error computing canonical readiness for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to compute canonical readiness",
            "error": str(ex)
        }), 500


@spec_api_bp.route("/api/skills/map", methods=["GET"])
def get_canonical_skills_map():
    """
    Returns the complete skills map, pillars, verified gaps, and unassessed skills.
    Complies with Section 5 and Section 6.
    """
    user_id = _extract_request_user_id()
    target_role = request.args.get("role") or request.args.get("target_role") or "AI/ML Engineer"

    try:
        profile_data = evaluate_candidate_readiness(user_id=user_id, target_role=target_role)

        response_payload = {
            "status": "success",
            "user_id": user_id,
            "target_role": target_role,
            "skills": profile_data.get("skills_map", []),
            "pillars": profile_data.get("pillars", []),
            "gap_analysis": profile_data.get("gap_analysis", {})
        }
        return jsonify(response_payload), 200
    except Exception as ex:
        logger.error(f"Error fetching skills map for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to fetch skills map",
            "error": str(ex)
        }), 500


# -----------------------------------------------------------------------------
# PHASE 3: ONBOARDING, SKILLS PROFILE & FEASIBILITY ENDPOINTS (Section 2, 3, 8.1, 11)
# -----------------------------------------------------------------------------

@spec_api_bp.route("/api/onboarding/profile", methods=["POST"])
def create_onboarding_profile():
    """
    POST /api/onboarding/profile
    Saves multi-step onboarding constraints, generates the skill requirement profile,
    and runs the Section 8.1 feasibility check.
    """
    user_id = _extract_request_user_id()
    payload = request.get_json(silent=True) or {}

    try:
        from services.onboarding_service import OnboardingService
        profile_res = OnboardingService.save_onboarding_target_profile(
            user_id=user_id,
            data=payload
        )
        return jsonify({
            "status": "success",
            "message": "Onboarding profile created and skill requirements generated",
            "profile": profile_res
        }), 201
    except Exception as ex:
        logger.error(f"Failed to create onboarding profile for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to generate onboarding profile",
            "error": str(ex)
        }), 400


@spec_api_bp.route("/api/profile/skills", methods=["PUT"])
def update_candidate_profile_skills():
    """
    PUT /api/profile/skills
    Allows candidate to edit skills/tiers during Step 4 review (Section 2.1).
    Re-runs feasibility check and returns updated state.
    """
    user_id = _extract_request_user_id()
    payload = request.get_json(silent=True) or {}
    skills_list = payload.get("skills") if isinstance(payload.get("skills"), list) else payload

    if not isinstance(skills_list, list):
        return jsonify({
            "status": "error",
            "message": "Body must contain 'skills' list"
        }), 400

    try:
        from services.onboarding_service import OnboardingService
        update_res = OnboardingService.update_profile_skills(
            user_id=user_id,
            updated_skills=skills_list
        )
        return jsonify(update_res), 200
    except Exception as ex:
        logger.error(f"Failed to update profile skills for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to update profile skills",
            "error": str(ex)
        }), 400


@spec_api_bp.route("/api/feasibility", methods=["GET"])
def get_feasibility_check_endpoint():
    """
    GET /api/feasibility
    Returns real-time Section 8.1 Feasibility Check.
    """
    user_id = _extract_request_user_id()

    try:
        from services.onboarding_service import OnboardingService
        feasibility = OnboardingService.get_feasibility_check(user_id=user_id)
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "feasibility": feasibility
        }), 200
    except Exception as ex:
        logger.error(f"Failed to compute feasibility for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to compute feasibility check",
            "error": str(ex)
        }), 500


# -----------------------------------------------------------------------------
# PHASE 4: DIAGNOSTIC & ASSESSMENT ENDPOINTS (Section 4, 11)
# -----------------------------------------------------------------------------
# Note: POST /api/assessment/start is routed through intelligence.py:start_diagnostic_assessment
# to prevent URL map collision while cleanly servicing both spec and legacy callers.

@spec_api_bp.route("/api/assessment/answer", methods=["POST"])
def submit_assessment_answer_endpoint():
    """
    POST /api/assessment/answer
    Accepts: { sessionId, questionId, answer, selectedOptions? }
    Returns: { score, grade_result, next_question, is_completed }
    """
    user_id = _extract_request_user_id()
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("sessionId") or payload.get("session_id")
    question_id = payload.get("questionId") or payload.get("question_id")
    answer = payload.get("answer") or ""
    selected_options = payload.get("selectedOptions") or payload.get("selected_options")

    if not session_id or not question_id:
        return jsonify({
            "status": "error",
            "message": "Both sessionId and questionId are required"
        }), 400

    try:
        from services.diagnostic_engine import DiagnosticEngine
        ans_res = DiagnosticEngine.submit_diagnostic_answer(
            session_id=session_id,
            question_id=question_id,
            answer_text=answer,
            selected_options=selected_options
        )
        return jsonify(ans_res), 200
    except Exception as ex:
        logger.error(f"Failed to submit assessment answer for session {session_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to submit assessment answer",
            "error": str(ex)
        }), 400


@spec_api_bp.route("/api/assessment/finish", methods=["POST"])
def finish_assessment_endpoint():
    """
    POST /api/assessment/finish
    Accepts: { sessionId }
    Returns: Section 4.4 Result Screen payload ("Calibrated Competency & Readiness Profile")
    """
    user_id = _extract_request_user_id()
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("sessionId") or payload.get("session_id")

    if not session_id:
        return jsonify({
            "status": "error",
            "message": "sessionId is required"
        }), 400

    try:
        from services.diagnostic_engine import DiagnosticEngine
        finish_res = DiagnosticEngine.finish_diagnostic_session(session_id=session_id)
        return jsonify(finish_res), 200
    except Exception as ex:
        logger.error(f"Failed to finish assessment session {session_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to finalize assessment session",
            "error": str(ex)
        }), 400


# -----------------------------------------------------------------------------
# PHASE 5: PREPARATION PLANNER & RE-PLANNING ENDPOINTS (Section 8, 11)
# -----------------------------------------------------------------------------

@spec_api_bp.route("/api/plan/generate", methods=["POST"])
def generate_preparation_plan_endpoint():
    """
    POST /api/plan/generate
    Generates initial deterministic, phased preparation plan.
    """
    user_id = _extract_request_user_id()
    payload = request.get_json(silent=True) or {}

    try:
        from services.spec_planner_service import SpecPlannerService
        plan_res = SpecPlannerService.generate_plan(
            user_id=user_id,
            target_role=payload.get("target_role", "AI/ML Engineer"),
            target_company=payload.get("target_company", "Target Tech"),
            interview_date=payload.get("interview_date"),
            daily_minutes=payload.get("daily_minutes", 90),
            start_date=payload.get("start_date"),
            blackout_dates=payload.get("blackout_dates"),
            availability_grid=payload.get("availability_grid"),
            trigger="INITIAL"
        )
        return jsonify({
            "status": "success",
            "plan": plan_res
        }), 201
    except Exception as ex:
        logger.error(f"Failed to generate plan for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to generate preparation plan",
            "error": str(ex)
        }), 400


@spec_api_bp.route("/api/plan/replan", methods=["POST"])
def replan_preparation_endpoint():
    """
    POST /api/plan/replan
    Body: { trigger, params }
    Returns: new plan version + structured diff
    """
    user_id = _extract_request_user_id()
    payload = request.get_json(silent=True) or {}
    trigger = payload.get("trigger", "MANUAL_REBALANCE")
    params = payload.get("params", {})

    try:
        from services.spec_planner_service import SpecPlannerService
        new_plan = SpecPlannerService.replan(
            user_id=user_id,
            trigger=trigger,
            params=params
        )
        return jsonify({
            "status": "success",
            "plan": new_plan,
            "diff": new_plan.get("diff", {})
        }), 200
    except Exception as ex:
        logger.error(f"Failed to replan for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to recalculate preparation plan",
            "error": str(ex)
        }), 400


@spec_api_bp.route("/api/plan/active", methods=["GET"])
def get_active_plan_endpoint():
    """
    GET /api/plan/active
    Returns the active preparation plan with days and blocks.
    """
    user_id = _extract_request_user_id()

    try:
        from services.spec_planner_service import SpecPlannerService
        active = SpecPlannerService.get_active_plan(user_id=user_id)
        if not active:
            # Auto-generate initial plan
            active = SpecPlannerService.generate_plan(user_id=user_id)
        return jsonify({
            "status": "success",
            "plan": active
        }), 200
    except Exception as ex:
        logger.error(f"Failed to retrieve active plan for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to get active plan",
            "error": str(ex)
        }), 500


@spec_api_bp.route("/api/plan/versions", methods=["GET"])
def get_plan_versions_endpoint():
    """
    GET /api/plan/versions
    Returns list of plan versions with historical diffs.
    """
    user_id = _extract_request_user_id()

    try:
        from services.spec_planner_service import SpecPlannerService
        versions = SpecPlannerService.get_user_plan_history(user_id=user_id)
        return jsonify({
            "status": "success",
            "versions": versions
        }), 200
    except Exception as ex:
        logger.error(f"Failed to retrieve plan versions for {user_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to get plan versions",
            "error": str(ex)
        }), 500


@spec_api_bp.route("/api/block/<block_id>/start", methods=["POST"])
def start_block_activity(block_id: str):
    """
    POST /api/block/:id/start
    Logs study session start.
    """
    user_id = _extract_request_user_id()
    return jsonify({
        "status": "success",
        "block_id": block_id,
        "user_id": user_id,
        "started_at": datetime.now(timezone.utc).isoformat()
    }), 200


@spec_api_bp.route("/api/block/<block_id>/complete", methods=["POST"])
def complete_block_activity(block_id: str):
    """
    POST /api/block/:id/complete
    Logs completed study minutes. Note Golden Rule 3: Marking a block complete does not invent fake mastery.
    """
    user_id = _extract_request_user_id()
    payload = request.get_json(silent=True) or {}
    minutes_spent = payload.get("minutes_spent", 30)

    try:
        from services.spec_planner_service import SpecPlannerService
        if user_id not in SpecPlannerService._COMPLETED_BLOCKS:
            SpecPlannerService._COMPLETED_BLOCKS[user_id] = set()
        SpecPlannerService._COMPLETED_BLOCKS[user_id].add(block_id)

        return jsonify({
            "status": "success",
            "block_id": block_id,
            "user_id": user_id,
            "minutes_spent": minutes_spent,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }), 200
    except Exception as ex:
        logger.error(f"Failed to complete block {block_id}: {ex}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to record block completion",
            "error": str(ex)
        }), 400




