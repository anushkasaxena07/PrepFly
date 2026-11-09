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
from datetime import datetime, timezone
import json
import uuid
import logging

logger = logging.getLogger(__name__)

from services.event_pipeline_service import EventPipelineService
from services.performance_analytics_engine import PerformanceAnalyticsEngine
from services.roadmap_engine import PersonalizedRoadmapEngine, RecommendationEngine
from services.job_intelligence_service import JobIntelligenceService
from services.achievement_service import AchievementService
from services.job_readiness_engine import JobReadinessEngine
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


# =============================================================================
# 6. Intelligent Company-Specific Preparation Engine Endpoints
# =============================================================================

@career_intelligence_bp.route("/company/<company_name>", methods=["GET"])
def get_company_interview_intelligence(company_name):
    """Retrieves company interview intelligence, round structures, verified sources, and topic relevance."""
    role = request.args.get("role", "Software Engineer")
    experience_level = request.args.get("experience_level", "Fresher")

    try:
        from services.company_intelligence_service import CompanyIntelligenceService
        intel = CompanyIntelligenceService.get_company_intelligence(
            company_name=company_name,
            role=role,
            experience_level=experience_level
        )
        return jsonify({"success": True, "data": intel}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to retrieve company intelligence: {str(ex)}"}), 500


@career_intelligence_bp.route("/candidate/readiness", methods=["GET"])
def get_candidate_readiness():
    """Returns candidate readiness snapshot across skills, coding, Ava interviews, and study behavior."""
    user_id = _resolve_user_id()
    role = request.args.get("role", "Software Engineer")

    try:
        from services.candidate_readiness_service import CandidateReadinessService
        snapshot = CandidateReadinessService.get_candidate_readiness_snapshot(
            user_id=user_id,
            target_role=role
        )
        return jsonify({"success": True, "data": snapshot}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to compute candidate readiness: {str(ex)}"}), 500


@career_intelligence_bp.route("/company/gap-analysis", methods=["POST"])
def compute_company_candidate_gaps():
    """Computes Dimension A vs Dimension B gap analysis with 6-tier competency classification."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    company_name = data.get("company_name", "Target Company")
    role = data.get("role", "Software Engineer")
    experience_level = data.get("experience_level", "Fresher")
    days_to_deadline = int(data.get("days_to_deadline", 30))

    try:
        from services.company_gap_service import CompanyCandidateGapService
        gap_report = CompanyCandidateGapService.analyze_company_candidate_gaps(
            user_id=user_id,
            company_name=company_name,
            role=role,
            experience_level=experience_level,
            days_to_deadline=days_to_deadline
        )
        return jsonify({"success": True, "data": gap_report}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to execute gap analysis: {str(ex)}"}), 500


@career_intelligence_bp.route("/company/plan", methods=["POST", "GET"])
def handle_company_preparation_plan():
    """
    POST: Generates or recalculates a personalized company-specific preparation roadmap.
    GET: Retrieves the current active preparation plan with company intelligence and readiness context.
    """
    if request.method == "GET":
        user_id = _resolve_user_id()
        try:
            plan = PersonalizedRoadmapEngine.get_or_create_roadmap(user_id)
            return jsonify({"success": True, "data": plan}), 200
        except Exception as ex:
            return jsonify({"error": f"Failed to fetch plan: {str(ex)}"}), 500

    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    company_name = data.get("company_name", "Target Company")
    role = data.get("role", "Software Engineer")
    experience_level = data.get("experience_level", "Fresher")
    target_date = data.get("target_date") or data.get("target_interview_date")
    daily_minutes = int(data.get("daily_minutes", 60))
    study_days = data.get("study_days")
    prep_style = data.get("prep_style", "mixed")
    job_description = data.get("job_description")

    # Validate inputs
    if target_date:
        try:
            t_dt = datetime.strptime(str(target_date).strip()[:10], "%Y-%m-%d").date()
            if t_dt < datetime.now(timezone.utc).date():
                return jsonify({"error": "Target interview date cannot be in the past. Please select an upcoming date."}), 400
        except ValueError:
            return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    if daily_minutes < 15 or daily_minutes > 480:
        return jsonify({"error": "Daily preparation time must be between 15 and 480 minutes."}), 400

    try:
        plan = PersonalizedRoadmapEngine.generate_company_personalized_plan(
            user_id=user_id,
            company_name=company_name,
            role=role,
            experience_level=experience_level,
            target_date=target_date,
            daily_minutes=daily_minutes,
            study_days=study_days,
            prep_style=prep_style,
            job_description=job_description
        )
        return jsonify({"success": True, "data": plan}), 201
    except Exception as ex:
        return jsonify({"error": f"Failed to generate company preparation plan: {str(ex)}"}), 500


# =============================================================================
# 7. Job-Specific Readiness Assessment & Diagnostic Engine Endpoints
# =============================================================================

@career_intelligence_bp.route("/job-prep/assessments", methods=["POST"])
def create_job_readiness_session():
    """
    Ingests job requirements, aggregates candidate evidence,
    constructs role-specific blueprint, and calculates initial readiness.
    """
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    raw_text = data.get("raw_text") or data.get("job_description") or ""
    company = data.get("company", "Tech Standard").strip()
    role = data.get("role", "Software Engineer").strip()
    experience_level = data.get("experience_level", "Fresher").strip()
    target_date = data.get("target_date")

    if not raw_text or len(raw_text.strip()) < 20:
        return jsonify({"error": "Job description text must contain at least 20 characters."}), 400

    supabase = get_supabase_client()
    session_id = f"job_sess_{uuid.uuid4().hex[:10]}"

    try:
        # 1. Extract and classify requirements (6 canonical types)
        requirements = JobReadinessEngine.extract_and_classify_requirements(
            raw_text=raw_text,
            company=company,
            role=role,
            experience_level=experience_level
        )

        # 2. Persist Session
        supabase.table("job_assessment_sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "company": company,
            "role": role,
            "experience_level": experience_level,
            "target_date": target_date,
            "raw_jd_text": raw_text,
            "status": "IN_PROGRESS",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # 3. Persist Requirements Snapshots
        for req in requirements:
            supabase.table("job_requirement_snapshots").insert({
                "id": f"req_{uuid.uuid4().hex[:10]}",
                "session_id": session_id,
                "job_id": session_id,
                "canonical_skill_id": req["canonical_skill_id"],
                "original_source_text": req["original_source_text"],
                "normalized_description": req["normalized_description"],
                "requirement_type": req["requirement_type"],
                "importance": req["importance"],
                "role_relevance": req["role_relevance"],
                "evidence_source": req["evidence_source"],
                "extraction_confidence": req["extraction_confidence"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()

        # 4. Aggregate Candidate Evidence
        req_ids = [r["canonical_skill_id"] for r in requirements]
        evidence = JobReadinessEngine.aggregate_candidate_evidence(user_id, role, req_ids, supabase)

        # 5. Build Role-Specific Assessment Blueprint
        unassessed_or_weak = [
            u["skill_id"] for u in evidence.get("unassessed_competencies", [])
        ]
        blueprint = JobReadinessEngine.build_role_assessment_blueprint(
            role=role,
            experience_level=experience_level,
            unassessed_or_weak_skills=unassessed_or_weak
        )

        supabase.table("assessment_blueprints").insert({
            "id": f"bp_{uuid.uuid4().hex[:10]}",
            "session_id": session_id,
            "role": role,
            "role_tier": blueprint.get("experience_level", "mid"),
            "planned_components_json": json.dumps(blueprint.get("component_weights", {})),
            "target_skills_json": json.dumps(blueprint.get("target_skills", [])),
            "weights_json": json.dumps(blueprint.get("component_weights", {})),
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # 6. Calculate Initial Readiness (Coverage Gated)
        readiness = JobReadinessEngine.calculate_job_readiness(requirements, evidence)

        # Update Session with readiness metrics
        supabase.table("job_assessment_sessions").update({
            "overall_readiness": readiness.get("overall_readiness"),
            "assessment_coverage": readiness.get("assessment_coverage", 0.0),
            "evidence_confidence": readiness.get("evidence_confidence", 0.0),
            "readiness_status": readiness.get("readiness_status", "READINESS NOT YET ESTABLISHED")
        }).eq("id", session_id).execute()

        # 7. Generate Full 9-Section Report
        report = JobReadinessEngine.generate_readiness_report(session_id, user_id, supabase)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "data": report
        }), 201

    except Exception as ex:
        logger.error(f"Failed to create job readiness assessment: {ex}", exc_info=True)
        return jsonify({"error": f"Failed to initialize job readiness session: {str(ex)}"}), 500


@career_intelligence_bp.route("/job-prep/assessments/<session_id>", methods=["GET"])
def get_job_readiness_report_endpoint(session_id):
    """Retrieves the full 9-section Job Readiness Report for a session."""
    user_id = _resolve_user_id()
    try:
        report = JobReadinessEngine.generate_readiness_report(session_id, user_id)
        return jsonify({"success": True, "data": report}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except Exception as ex:
        return jsonify({"error": f"Failed to fetch readiness report: {str(ex)}"}), 500


@career_intelligence_bp.route("/job-prep/assessments/<session_id>/blueprint", methods=["GET"])
def get_job_assessment_blueprint_endpoint(session_id):
    """Retrieves the assessment blueprint and adaptive questions."""
    user_id = _resolve_user_id()
    supabase = get_supabase_client()

    try:
        s_res = supabase.table("job_assessment_sessions").select("*").eq("id", session_id).execute()
        if not s_res or not s_res.data:
            return jsonify({"error": "Session not found"}), 404
        session = s_res.data[0]

        # Fetch requirements
        r_res = supabase.table("job_requirement_snapshots").select("*").eq("session_id", session_id).execute()
        reqs = r_res.data if (r_res and r_res.data) else []
        req_ids = [r["canonical_skill_id"] for r in reqs]

        # Aggregate evidence
        evidence = JobReadinessEngine.aggregate_candidate_evidence(user_id, session["role"], req_ids, supabase)

        # Build blueprint and select adaptive questions
        unassessed_or_weak = [u["skill_id"] for u in evidence.get("unassessed_competencies", [])]
        blueprint = JobReadinessEngine.build_role_assessment_blueprint(session["role"], session.get("experience_level", "Fresher"), unassessed_or_weak)
        questions = JobReadinessEngine.select_adaptive_questions(blueprint, evidence)

        return jsonify({
            "success": True,
            "data": {
                "blueprint": blueprint,
                "adaptive_questions": questions
            }
        }), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to load assessment blueprint: {str(ex)}"}), 500


@career_intelligence_bp.route("/job-prep/assessments/<session_id>/attempts", methods=["POST"])
def submit_job_assessment_attempt_endpoint(session_id):
    """
    Submits a candidate's response to an assessment question, scores via structured rubrics,
    updates assessment evaluations, and recalculates readiness.
    """
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    component_type = data.get("component_type", "technical_knowledge")
    canonical_skill_id = data.get("canonical_skill_id")
    candidate_response = data.get("candidate_response", "")
    code_submission = data.get("code_submission")
    question_id = data.get("question_id", f"q_{uuid.uuid4().hex[:6]}")
    time_taken = int(data.get("time_taken_seconds", 60))

    if not canonical_skill_id:
        return jsonify({"error": "canonical_skill_id is required."}), 400

    supabase = get_supabase_client()
    attempt_id = f"att_{uuid.uuid4().hex[:10]}"

    try:
        # 1. Score Attempt via deterministic rubric
        scoring_res = JobReadinessEngine.score_assessment_attempt(
            component_type=component_type,
            canonical_skill_id=canonical_skill_id,
            candidate_response=candidate_response,
            code_submission=code_submission
        )

        # 2. Persist Attempt
        supabase.table("assessment_attempts").insert({
            "id": attempt_id,
            "session_id": session_id,
            "user_id": user_id,
            "component_type": component_type,
            "question_id": question_id,
            "canonical_skill_id": canonical_skill_id,
            "candidate_response": candidate_response,
            "code_submission": code_submission,
            "time_taken_seconds": time_taken,
            "status": "COMPLETED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # 3. Persist Evaluation
        eval_id = f"eval_{uuid.uuid4().hex[:10]}"
        supabase.table("assessment_evaluations").insert({
            "id": eval_id,
            "attempt_id": attempt_id,
            "session_id": session_id,
            "canonical_skill_id": canonical_skill_id,
            "correctness_score": scoring_res["correctness_score"],
            "depth_score": scoring_res["depth_score"],
            "communication_score": scoring_res["communication_score"],
            "overall_score": scoring_res["overall_score"],
            "rubric_breakdown_json": json.dumps(scoring_res["rubric_breakdown"]),
            "feedback": scoring_res["feedback"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        # 4. Publish to shared candidate intelligence (verified evidence)
        JobReadinessEngine.publish_to_candidate_analytics(
            session_id=session_id,
            user_id=user_id,
            evaluations=[scoring_res],
            supabase_client=supabase
        )

        # 5. Re-generate Updated 9-Section Readiness Report
        updated_report = JobReadinessEngine.generate_readiness_report(session_id, user_id, supabase)

        # Update Session overall score
        new_score = updated_report["section_b_overall_readiness"]["overall_readiness"]
        new_cov = updated_report["section_b_overall_readiness"]["assessment_coverage_pct"]
        new_stat = updated_report["section_b_overall_readiness"]["readiness_status"]
        supabase.table("job_assessment_sessions").update({
            "overall_readiness": new_score,
            "assessment_coverage": new_cov,
            "readiness_status": new_stat,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", session_id).execute()

        return jsonify({
            "success": True,
            "evaluation": scoring_res,
            "updated_report": updated_report
        }), 201

    except Exception as ex:
        logger.error(f"Failed to score assessment attempt: {ex}", exc_info=True)
        return jsonify({"error": f"Failed to score assessment: {str(ex)}"}), 500


@career_intelligence_bp.route("/job-prep/assessments/<session_id>/recommendations", methods=["GET"])
def get_job_recommendations_endpoint(session_id):
    """Retrieves prioritized improvement recommendations for this job."""
    user_id = _resolve_user_id()
    try:
        report = JobReadinessEngine.generate_readiness_report(session_id, user_id)
        recs = report.get("section_i_improvement_plan", {}).get("all_recommendations", [])
        return jsonify({"success": True, "data": recs}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to fetch recommendations: {str(ex)}"}), 500


@career_intelligence_bp.route("/job-prep/assessments/<session_id>/transfer-to-prep", methods=["POST"])
def transfer_job_readiness_to_prep_endpoint(session_id):
    """Exports readiness gaps directly to Prep Roadmap scheduling."""
    data = request.get_json() or {}
    user_id = _resolve_user_id(data)
    daily_minutes = int(data.get("daily_minutes", 60))

    try:
        handover = JobReadinessEngine.export_to_prep_roadmap(
            session_id=session_id,
            user_id=user_id,
            daily_minutes=daily_minutes
        )
        return jsonify({"success": True, "data": handover}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to transfer readiness to prep: {str(ex)}"}), 500


@career_intelligence_bp.route("/job-prep/sessions", methods=["GET"])
def list_job_assessment_sessions_endpoint():
    """Lists historical job assessment sessions for candidate."""
    user_id = _resolve_user_id()
    supabase = get_supabase_client()

    try:
        res = supabase.table("job_assessment_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        sessions = res.data if (res and res.data) else []
        return jsonify({"success": True, "data": sessions}), 200
    except Exception as ex:
        return jsonify({"error": f"Failed to fetch sessions: {str(ex)}"}), 500


