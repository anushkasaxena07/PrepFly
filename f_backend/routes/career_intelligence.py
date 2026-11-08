"""
PrepFly Career Intelligence REST API Blueprint
Exposes endpoints for:
1. Improvement Tracking & Performance Snapshots
2. Personalized Preparation Roadmaps (Recommendation & Scheduling)
3. Job-Specific Preparation (JD ingestion, skill gap analysis, tailored questions, Ava integration)
4. Server-Validated Achievements and Milestones
5. Shared Event Pipeline
"""

from flask import Blueprint, request, jsonify
import json

from services.event_pipeline_service import EventPipelineService
from services.performance_analytics_engine import PerformanceAnalyticsEngine
from services.roadmap_engine import PersonalizedRoadmapEngine, RecommendationEngine
from services.job_intelligence_service import JobIntelligenceService
from services.achievement_service import AchievementService
from local_supabase import get_supabase_client

career_intelligence_bp = Blueprint("career_intelligence", __name__, url_prefix="/api/intelligence")


def _resolve_user_id(data: dict = None) -> str:
    """
    Robust user identity resolution:
    1. Checks explicit 'user_id' in JSON body.
    2. Checks explicit 'user_id' in query parameters.
    3. Decodes JWT token from 'Authorization: Bearer <token>' header.
    4. Falls back to active candidate / user from headers or 'user_default'.
    """
    if data and data.get("user_id"):
        uid = str(data["user_id"]).strip()
        if uid and uid.lower() not in ("null", "undefined"):
            return uid

    arg_uid = request.args.get("user_id")
    if arg_uid and arg_uid.strip() and arg_uid.strip().lower() not in ("null", "undefined"):
        return arg_uid.strip()

    # Try Authorization Bearer JWT
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token and token.lower() not in ("null", "undefined"):
            try:
                from app import _decode_jwt
                payload = _decode_jwt(token)
                token_uid = payload.get("sub") or payload.get("user_id") or payload.get("id")
                if token_uid:
                    return str(token_uid).strip()
            except Exception:
                pass
            try:
                import jwt
                unverified = jwt.decode(token, options={"verify_signature": False})
                token_uid = unverified.get("sub") or unverified.get("user_id") or unverified.get("id")
                if token_uid:
                    return str(token_uid).strip()
            except Exception:
                pass

    header_uid = request.headers.get("X-User-Id")
    if header_uid and header_uid.strip() and header_uid.strip().lower() not in ("null", "undefined"):
        return header_uid.strip()

    return "user_default"


# =============================================================================
# 1. Event Pipeline Endpoints
# =============================================================================

@career_intelligence_bp.route("/events", methods=["POST"])
def emit_preparation_event():
    """Ingests a preparation event into the idempotent event pipeline."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    event_type = data.get("event_type")
    source_module = data.get("source_module", "CLIENT_APP")
    source_record_id = data.get("source_record_id")
    payload = data.get("payload", {})

    if not event_type:
        return jsonify({"error": "event_type is required"}), 400

    try:
        result = EventPipelineService.emit_event(
            user_id=user_id,
            event_type=event_type,
            source_module=source_module,
            source_record_id=source_record_id,
            payload=payload
        )
        return jsonify({"success": True, "data": result}), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as ex:
        return jsonify({"error": f"Failed to emit event: {str(ex)}"}), 500


# =============================================================================
# 2. Improvement Tracking Endpoints
# =============================================================================

@career_intelligence_bp.route("/improvement/analytics", methods=["GET"])
def get_improvement_analytics():
    """Returns comprehensive improvement tracking metrics, statistical trend, and grounded coaching insights."""
    user_id = _resolve_user_id()

    try:
        report = PerformanceAnalyticsEngine.get_full_improvement_report(user_id)
        return jsonify({"success": True, "data": report}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to compute improvement report: {str(ex)}"}), 500


@career_intelligence_bp.route("/improvement/snapshot", methods=["POST"])
def create_performance_snapshot():
    """Captures an immutable point-in-time performance snapshot."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    snapshot_type = data.get("snapshot_type", "periodic")

    try:
        snap = PerformanceAnalyticsEngine.create_snapshot(user_id=user_id, snapshot_type=snapshot_type)
        return jsonify({"success": True, "data": snap}), 201
    except Exception as ex:
        return jsonify({"error": f"Failed to capture snapshot: {str(ex)}"}), 500


# =============================================================================
# 3. Personalized Preparation Roadmap Endpoints
# =============================================================================

@career_intelligence_bp.route("/roadmap/recommendations", methods=["GET"])
def get_roadmap_recommendations():
    """Returns ordered recommendations of what to learn with priority scoring rationale."""
    user_id = _resolve_user_id()
    job_id = request.args.get("job_id")

    try:
        recommendations = RecommendationEngine.get_recommendations(user_id, job_id=job_id)
        return jsonify({"success": True, "data": recommendations}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to fetch recommendations: {str(ex)}"}), 500


@career_intelligence_bp.route("/roadmap/schedule", methods=["GET"])
def get_roadmap_schedule():
    """Returns active preparation roadmap with scheduled daily activities."""
    user_id = _resolve_user_id()
    job_id = request.args.get("job_id")

    try:
        roadmap = PersonalizedRoadmapEngine.get_or_create_roadmap(user_id, job_id=job_id)
        return jsonify({"success": True, "data": roadmap}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to fetch roadmap schedule: {str(ex)}"}), 500


@career_intelligence_bp.route("/roadmap/recalculate", methods=["POST"])
def recalculate_roadmap():
    """Triggers non-destructive adaptive recalculation while preserving completed/pinned tasks."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    job_id = data.get("job_id") or request.args.get("job_id")
    change_reason = data.get("change_reason", "Candidate requested recalculation")

    try:
        roadmap = PersonalizedRoadmapEngine.recalculate_roadmap(
            user_id=user_id,
            job_id=job_id,
            change_reason=change_reason,
            trigger_event="manual_request"
        )
        return jsonify({"success": True, "data": roadmap}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to recalculate roadmap: {str(ex)}"}), 500


# =============================================================================
# 4. Job-Specific Preparation Endpoints
# =============================================================================

@career_intelligence_bp.route("/jobs/ingest", methods=["POST"])
def ingest_job_description():
    """Ingests raw JD, extracts structured requirements, calculates gaps, and generates questions."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    raw_text = data.get("raw_text", "")
    job_title = data.get("job_title")
    company = data.get("company")
    target_date = data.get("target_date")

    if not raw_text or len(raw_text.strip()) < 20:
        return jsonify({"error": "Please provide a job description of at least 20 characters."}), 400

    try:
        result = JobIntelligenceService.ingest_job_description(
            user_id=user_id,
            raw_text=raw_text,
            job_title=job_title,
            company=company,
            target_date=target_date
        )
        return jsonify({"success": True, "data": result}), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as ex:
        return jsonify({"error": f"Failed to ingest job description: {str(ex)}"}), 500


@career_intelligence_bp.route("/jobs/<job_id>/gaps", methods=["GET"])
def get_job_skill_gaps(job_id):
    """Calculates skill gaps between candidate profile and a specific job requirement set."""
    user_id = _resolve_user_id()

    try:
        gaps = JobIntelligenceService.calculate_skill_gaps(user_id=user_id, job_id=job_id)
        return jsonify({"success": True, "data": gaps}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to calculate skill gaps: {str(ex)}"}), 500


@career_intelligence_bp.route("/jobs/<job_id>/questions", methods=["GET"])
def get_job_tailored_questions(job_id):
    """Retrieves quality-evaluated questions tailored to a specific job."""
    supabase = get_supabase_client()
    res = supabase.table("job_tailored_questions").select("*").eq("job_id", job_id).execute()
    questions = res.data if (res and res.data) else []
    return jsonify({"success": True, "data": questions}), 200


@career_intelligence_bp.route("/jobs/<job_id>/start-interview", methods=["POST"])
def start_job_matched_interview(job_id):
    """Configures an Ava mock interview session pre-seeded with this job's requirements and questions."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    personality = data.get("personality", "professional")

    try:
        session = JobIntelligenceService.create_job_matched_interview_session(
            user_id=user_id,
            job_id=job_id,
            personality=personality
        )
        return jsonify({"success": True, "data": session}), 201
    except Exception as ex:
        return jsonify({"error": f"Failed to launch job interview: {str(ex)}"}), 500


# =============================================================================
# 5. Achievements and Milestones Endpoints
# =============================================================================

@career_intelligence_bp.route("/achievements", methods=["GET"])
def get_user_achievements():
    """Retrieves all milestone definitions with candidate unlock status and progress."""
    user_id = _resolve_user_id()

    try:
        achievements_data = AchievementService.get_user_achievements_with_progress(user_id)
        return jsonify({"success": True, "data": achievements_data}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to fetch achievements: {str(ex)}"}), 500


@career_intelligence_bp.route("/achievements/<achievement_id>/claim", methods=["POST"])
def claim_achievement_reward(achievement_id):
    """Claims reward points for an unlocked achievement."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)

    try:
        claim_result = AchievementService.claim_achievement_reward(user_id=user_id, achievement_id=achievement_id)
        return jsonify({"success": True, "data": claim_result}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as ex:
        return jsonify({"error": f"Failed to claim reward: {str(ex)}"}), 500

