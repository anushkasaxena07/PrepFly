"""
PREPFLY SPECIFICATION API ENDPOINTS (Section 11)
================================================
Exposes canonical endpoints required by the Full Build Specification:
- GET /api/readiness: The single source of truth readiness object used by all pages.
- GET /api/skills/map: The skill map, statuses, and gap analysis from the scoring engine.
"""

from flask import Blueprint, request, jsonify, Response
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
