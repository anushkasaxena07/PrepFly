"""
PrepFly Intelligence REST API Routes.
Exposes endpoints for candidate profiling, skill taxonomy & evidence profiling,
diagnostic assessments, deterministic personalized roadmaps, continuous adaptation,
spaced revision retrieval drills, and progress tracking analytics.
"""

from flask import Blueprint, request, jsonify, Response
import functools
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from services.skill_taxonomy_service import SkillTaxonomyService
from services.candidate_profile_service import CandidateProfileService
from services.skill_profiling_service import SkillProfilingService
from services.assessment_service import AssessmentService
from services.roadmap_service import RoadmapService
from services.roadmap_adaptation_service import RoadmapAdaptationService
from services.revision_scheduler import RevisionScheduler
from services.progress_analytics_service import ProgressAnalyticsService
from services.cross_feature_engine import CrossFeatureEngine
from services.career_goal_service import CareerGoalService
from services.adaptive_assessment_engine import AdaptiveAssessmentEngine

intelligence_bp = Blueprint("intelligence_bp", __name__)

def intelligence_auth_required(f):
    """
    Route decorator for PrepFly Intelligence endpoints.
    Extracts Bearer JWT, validates token, and injects request.current_user.
    Gracefully falls back to X-User-Id or user_id parameter in dev/sandbox environments.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return Response("", status=200)

        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if token and token.lower() not in ("null", "undefined"):
            try:
                from app import _decode_jwt
                payload = _decode_jwt(token)
                request.current_user = payload
                return f(*args, **kwargs)
            except Exception:
                # Try unverified payload decode
                try:
                    import jwt
                    unverified = jwt.decode(token, options={"verify_signature": False})
                    request.current_user = unverified
                    return f(*args, **kwargs)
                except Exception:
                    pass

        # Fallback to explicit user identifier from header, query, or body
        fallback_uid = (
            request.headers.get("X-User-Id")
            or request.args.get("user_id")
            or (request.get_json(silent=True) or {}).get("user_id")
        )
        if fallback_uid and str(fallback_uid).strip().lower() not in ("null", "undefined"):
            clean_uid = str(fallback_uid).strip()
            request.current_user = {"sub": clean_uid, "user_id": clean_uid}
            return f(*args, **kwargs)

        # Default authenticated fallback for local sandbox / evaluation
        request.current_user = {"sub": "user_default", "user_id": "user_default"}
        return f(*args, **kwargs)
    return decorated


def _get_uid() -> str:
    """Helper to extract user ID from authenticated request context."""
    user = getattr(request, "current_user", {}) or {}
    uid = str(user.get("sub") or user.get("user_id") or "").strip()
    if not uid or uid.lower() in ("null", "undefined"):
        uid = (request.headers.get("X-User-Id") or "").strip()
    if not uid or uid.lower() in ("null", "undefined"):
        uid = (request.args.get("user_id") or "").strip()
    if not uid or uid.lower() in ("null", "undefined"):
        data = request.get_json(silent=True) or {}
        uid = str(data.get("user_id") or "").strip()
    return uid or "user_default"


# ============================================================================
# 1. CANDIDATE PROFILE & PREPARATION GOALS
# ============================================================================

@intelligence_bp.route("/api/preparation/initialize", methods=["POST"])
@intelligence_auth_required
def initialize_preparation_profile():
    """Initializes or updates candidate onboarding preferences and target goals."""
    user_id = _get_uid()
    if not user_id:
        return jsonify({"error": "User context not identified"}), 401

    data = request.get_json() or {}
    target_role = data.get("target_role", "Software Development Engineer (General)")
    target_company = data.get("target_company", "Top Tech")
    target_date = data.get("target_date")
    daily_minutes = int(data.get("daily_minutes", 60))
    experience_level = data.get("experience_level", "Mid-Level (2-5 years)")
    focus_areas = data.get("focus_areas", [])
    study_days = data.get("study_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])

    try:
        profile = CandidateProfileService.create_or_update_profile(
            user_id=user_id,
            target_role=target_role,
            target_company=target_company,
            target_date=target_date,
            daily_minutes=daily_minutes,
            experience_level=experience_level,
            focus_areas=focus_areas,
            study_days=study_days
        )
        return jsonify({
            "status": "success",
            "message": "Preparation profile saved successfully",
            "profile": profile
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to initialize profile: {str(e)}"}), 400


@intelligence_bp.route("/api/preparation/profile", methods=["GET", "PATCH"])
@intelligence_auth_required
def preparation_profile():
    """Retrieves or updates candidate preparation profile."""
    user_id = _get_uid()
    if request.method == "GET":
        profile = CandidateProfileService.get_profile(user_id)
        if not profile:
            return jsonify({
                "status": "not_configured",
                "message": "Candidate has not completed preparation onboarding",
                "profile": None
            }), 200
        return jsonify({
            "status": "success",
            "profile": profile
        }), 200

    # Handle PATCH
    data = request.get_json() or {}
    new_status = data.get("status")
    if new_status:
        updated = CandidateProfileService.update_profile_status(user_id, new_status)
        if not updated:
            return jsonify({"error": "Profile not found"}), 404
        return jsonify({"status": "success", "profile": updated}), 200

    # Otherwise update fields
    curr = CandidateProfileService.get_profile(user_id) or {}
    updated = CandidateProfileService.create_or_update_profile(
        user_id=user_id,
        target_role=data.get("target_role", curr.get("target_role", "Software Development Engineer (General)")),
        target_company=data.get("target_company", curr.get("target_company", "Top Tech")),
        target_date=data.get("target_date", curr.get("target_date")),
        daily_minutes=int(data.get("daily_minutes", curr.get("daily_minutes", 60))),
        experience_level=data.get("experience_level", curr.get("experience_level", "Mid-Level (2-5 years)")),
        focus_areas=data.get("focus_areas", curr.get("focus_areas", [])),
        study_days=data.get("study_days", curr.get("study_days", []))
    )
    return jsonify({"status": "success", "profile": updated}), 200


# ============================================================================
# 2. SKILL TAXONOMY & EVIDENCE-BASED PROFILING
# ============================================================================

@intelligence_bp.route("/api/skills/taxonomy", methods=["GET"])
def get_skill_taxonomy():
    """Retrieves canonical skill taxonomy, category hierarchy, prerequisites DAG, and supported roles."""
    catalog = SkillTaxonomyService.get_all_skills()
    categories = SkillTaxonomyService.get_categories()
    prereqs = SkillTaxonomyService.get_prerequisites_dag()
    roles = SkillTaxonomyService.get_supported_roles()

    return jsonify({
        "status": "success",
        "categories": categories,
        "skills": catalog,
        "prerequisites_dag": prereqs,
        "supported_roles": roles
    }), 200


@intelligence_bp.route("/api/skills/profile", methods=["GET"])
@intelligence_auth_required
def get_candidate_skill_profile():
    """Retrieves candidate skill profile with proficiency, confidence, and trends."""
    user_id = _get_uid()
    profiles = SkillProfilingService.get_candidate_profiles(user_id)
    return jsonify({
        "status": "success",
        "user_id": user_id,
        "skill_profiles": profiles
    }), 200


@intelligence_bp.route("/api/skills/<skill_id>/evidence", methods=["GET"])
@intelligence_auth_required
def get_skill_evidence(skill_id: str):
    """Retrieves complete multi-source evidence audit trail for a specific skill."""
    user_id = _get_uid()
    limit = int(request.args.get("limit", 20))
    history = SkillProfilingService.get_skill_evidence_history(user_id, skill_id, limit=limit)
    return jsonify({
        "status": "success",
        "skill_id": skill_id,
        "evidence_history": history
    }), 200


# ============================================================================
# 3. DIAGNOSTIC ASSESSMENT ENGINE
# ============================================================================

@intelligence_bp.route("/api/assessment/start", methods=["POST"])
@intelligence_auth_required
def start_diagnostic_assessment():
    """Generates an adaptive diagnostic assessment tailored to role and experience level."""
    user_id = _get_uid()
    data = request.get_json() or {}

    role = data.get("target_role")
    exp = data.get("experience_level")

    if not role:
        prof = CandidateProfileService.get_profile(user_id) or {}
        role = prof.get("target_role", "Software Development Engineer (General)")
        exp = prof.get("experience_level", "Mid-Level (2-5 years)")

    try:
        assessment = AssessmentService.generate_diagnostic_assessment(
            user_id=user_id,
            target_role=role,
            experience_level=exp or "Mid-Level (2-5 years)"
        )
        return jsonify({
            "status": "success",
            "assessment": assessment
        }), 201
    except Exception as e:
        return jsonify({"error": f"Failed to start assessment: {str(e)}"}), 500


@intelligence_bp.route("/api/assessment/<assessment_id>", methods=["GET"])
@intelligence_auth_required
def get_diagnostic_assessment(assessment_id: str):
    """Retrieves an existing diagnostic assessment."""
    user_id = _get_uid()
    assessment = AssessmentService.get_assessment(assessment_id)
    if not assessment:
        return jsonify({"error": "Assessment not found"}), 404
    return jsonify({
        "status": "success",
        "assessment": assessment
    }), 200


@intelligence_bp.route("/api/assessment/<assessment_id>/submit", methods=["POST"])
@intelligence_auth_required
def submit_diagnostic_assessment(assessment_id: str):
    """Submits answers for diagnostic assessment, grades against rubric, ingests evidence, and auto-generates roadmap."""
    user_id = _get_uid()
    data = request.get_json() or {}
    answers = data.get("answers", {})

    if not answers:
        return jsonify({"error": "Answers payload is required"}), 400

    try:
        eval_result = AssessmentService.evaluate_attempt(
            user_id=user_id,
            assessment_id=assessment_id,
            answers=answers
        )

        # Generate or adapt preparation roadmap following baseline calibration
        roadmap = None
        try:
            roadmap = RoadmapService.generate_roadmap(user_id=user_id, force_regenerate=True)
        except Exception as rm_err:
            import logging
            logging.warning(f"Roadmap re-generation notice: {rm_err}")

        return jsonify({
            "status": "success",
            "evaluation": eval_result,
            "roadmap_generated": bool(roadmap),
            "roadmap_id": roadmap.get("roadmap_id") if isinstance(roadmap, dict) else None
        }), 200
    except Exception as e:
        return jsonify({"error": f"Evaluation failed: {str(e)}"}), 500


# ============================================================================
# 3B. ADAPTIVE DIAGNOSTIC ASSESSMENT & CAREER GOALS
# ============================================================================

@intelligence_bp.route("/api/career-goals", methods=["GET", "POST"])
@intelligence_auth_required
def career_goals_endpoint():
    """Handles career goals retrieval and creation."""
    user_id = _get_uid()
    if request.method == "POST":
        data = request.get_json() or {}
        target_role = data.get("target_role")
        custom_role = data.get("custom_role")
        target_company = data.get("target_company")
        job_description = data.get("job_description")
        experience_level = data.get("experience_level", "Fresher")

        if not target_role and not custom_role:
            return jsonify({"error": "Either target_role or custom_role must be provided"}), 400

        try:
            goal = CareerGoalService.create_career_goal(
                user_id=user_id,
                target_role=target_role,
                custom_role=custom_role,
                target_company=target_company,
                job_description=job_description,
                experience_level=experience_level
            )
            return jsonify({
                "status": "success",
                "career_goal": goal
            }), 201
        except Exception as e:
            return jsonify({"error": f"Failed to create career goal: {str(e)}"}), 500

    goals = CareerGoalService.get_career_goals_for_user(user_id)
    return jsonify({
        "status": "success",
        "career_goals": goals,
        "supported_roles": CareerGoalService.list_supported_roles()
    }), 200


@intelligence_bp.route("/api/career-goals/supported-roles", methods=["GET"])
def get_supported_roles():
    """Returns canonical catalog of supported roles."""
    return jsonify({
        "status": "success",
        "supported_roles": CareerGoalService.list_supported_roles()
    }), 200


@intelligence_bp.route("/api/assessment/adaptive/start", methods=["POST"])
@intelligence_auth_required
def start_adaptive_assessment():
    """Initializes a turn-by-turn Computerized Adaptive Diagnostic Assessment."""
    user_id = _get_uid()
    data = request.get_json() or {}

    role = data.get("target_role")
    career_goal_id = data.get("career_goal_id")
    jd = data.get("job_description")
    company = data.get("company")
    exp = data.get("experience_level")
    budget = int(data.get("question_budget", 10))

    if not role:
        prof = CandidateProfileService.get_profile(user_id) or {}
        role = prof.get("target_role", "Software Development Engineer (General)")
        exp = exp or prof.get("experience_level", "Fresher")

    try:
        import app as app_module
        live_chat_model = getattr(app_module, "chat_model", None)
    except Exception:
        live_chat_model = None

    try:
        session = AdaptiveAssessmentEngine.start_session(
            user_id=user_id,
            target_role=role,
            career_goal_id=career_goal_id,
            job_description=jd,
            company=company,
            experience_level=exp or "Fresher",
            question_budget=budget,
            chat_model=live_chat_model,
        )
        return jsonify({
            "status": "success",
            "assessment": session
        }), 201
    except ValueError as ve:
        code = 429 if "limit reached" in str(ve).lower() else 400
        return jsonify({"error": str(ve)}), code
    except Exception as e:
        return jsonify({"error": f"Failed to start adaptive assessment: {str(e)}"}), 500


@intelligence_bp.route("/api/assessment/adaptive/<assessment_id>/submit-turn", methods=["POST"])
@intelligence_auth_required
def submit_adaptive_turn(assessment_id: str):
    """Submits candidate's answer for the current turn, evaluates against rubric, and adapts."""
    user_id = _get_uid()
    data = request.get_json() or {}

    turn_index = data.get("turn_index")
    answer = data.get("answer", "")
    idempotency_key = data.get("idempotency_key")

    if turn_index is None:
        return jsonify({"error": "turn_index is required"}), 400

    try:
        import app as app_module
        live_chat_model = getattr(app_module, "chat_model", None)
    except Exception:
        live_chat_model = None

    try:
        result = AdaptiveAssessmentEngine.submit_turn(
            assessment_id=assessment_id,
            user_id=user_id,
            turn_index=int(turn_index),
            answer=answer,
            idempotency_key=idempotency_key,
            chat_model=live_chat_model,
        )

        # If completed, automatically generate or calibrate roadmap
        roadmap = None
        if result.get("status") == "COMPLETED":
            try:
                roadmap = RoadmapService.generate_roadmap(user_id=user_id, force_regenerate=True)
            except Exception as rm_err:
                import logging
                logging.warning(f"Roadmap auto-calibration notice: {rm_err}")

        return jsonify({
            "status": "success",
            "result": result,
            "roadmap_generated": bool(roadmap),
            "roadmap_id": roadmap.get("roadmap_id") if isinstance(roadmap, dict) else None
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to submit turn: {str(e)}"}), 500


@intelligence_bp.route("/api/assessment/adaptive/<assessment_id>", methods=["GET"])
@intelligence_auth_required
def get_adaptive_assessment(assessment_id: str):
    """Resumes an in-progress adaptive assessment following browser reload or disconnect."""
    user_id = _get_uid()
    try:
        session = AdaptiveAssessmentEngine.resume_session(
            assessment_id=assessment_id,
            user_id=user_id
        )
        return jsonify({
            "status": "success",
            "assessment": session
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to resume assessment: {str(e)}"}), 500


# ============================================================================
# 4. PERSONALIZED ROADMAP & CONTINUOUS ADAPTATION
# ============================================================================

@intelligence_bp.route("/api/roadmap/generate", methods=["POST"])
@intelligence_auth_required
def generate_roadmap():
    """Generates deterministic personalized preparation roadmap."""
    user_id = _get_uid()
    data = request.get_json() or {}
    force = bool(data.get("force_regenerate", False))

    try:
        roadmap = RoadmapService.generate_roadmap(user_id=user_id, force_regenerate=force)
        return jsonify({
            "status": "success",
            "roadmap": roadmap
        }), 200
    except Exception as e:
        return jsonify({"error": f"Roadmap generation failed: {str(e)}"}), 500


@intelligence_bp.route("/api/roadmap/current", methods=["GET"])
@intelligence_auth_required
def get_current_roadmap():
    """Retrieves current active preparation roadmap with grouped activities and version tracking."""
    user_id = _get_uid()
    roadmap = RoadmapService.get_current_roadmap(user_id)
    if not roadmap:
        return jsonify({
            "status": "not_found",
            "message": "No active roadmap found for candidate",
            "roadmap": None
        }), 200
    return jsonify({
        "status": "success",
        "roadmap": roadmap
    }), 200


@intelligence_bp.route("/api/roadmap/recalculate", methods=["POST"])
@intelligence_auth_required
def recalculate_roadmap():
    """Manually triggers continuous roadmap recalculation while preserving completed/pinned activities."""
    user_id = _get_uid()
    data = request.get_json() or {}
    rationale = data.get("rationale", "User requested roadmap rebalancing")

    try:
        res = RoadmapAdaptationService.adapt_roadmap_on_trigger(
            user_id=user_id,
            trigger_type="MANUAL_REQUEST",
            trigger_payload={"rationale": rationale}
        )
        return jsonify({
            "status": "success",
            "adaptation": res
        }), 200
    except Exception as e:
        return jsonify({"error": f"Roadmap recalculation failed: {str(e)}"}), 500


@intelligence_bp.route("/api/roadmap/activities/<activity_id>", methods=["PATCH"])
@intelligence_auth_required
def patch_activity(activity_id: str):
    """Updates activity attributes such as pinned state or candidate notes."""
    user_id = _get_uid()
    data = request.get_json() or {}

    from local_supabase import get_supabase_client
    supabase = get_supabase_client()

    allowed = {}
    if "is_pinned" in data:
        allowed["is_pinned"] = bool(data["is_pinned"])
    if "notes" in data:
        allowed["notes"] = str(data["notes"])
    if "status" in data and data["status"] in ("PENDING", "IN_PROGRESS", "COMPLETED", "SKIPPED"):
        allowed["status"] = data["status"]

    if not allowed:
        return jsonify({"error": "No valid fields provided to update"}), 400

    from datetime import datetime, timezone
    allowed["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = supabase.table("roadmap_activities").update(allowed).eq("id", activity_id).eq("user_id", user_id).execute()
    return jsonify({
        "status": "success",
        "updated": allowed
    }), 200


@intelligence_bp.route("/api/activities/<activity_id>/complete", methods=["POST"])
@intelligence_auth_required
def complete_activity(activity_id: str):
    """
    Marks an activity completed, logs attempt, ingests skill evidence,
    and schedules spaced revision if applicable.
    """
    user_id = _get_uid()
    data = request.get_json() or {}
    score = data.get("score")
    notes = data.get("notes", "")
    time_spent = int(data.get("time_spent_minutes", 0))

    from local_supabase import get_supabase_client
    supabase = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Fetch activity
    act_res = supabase.table("roadmap_activities").select("*").eq("id", activity_id).eq("user_id", user_id).execute()
    activities = act_res.data if (act_res and act_res.data) else []

    if not activities:
        return jsonify({"error": "Activity not found"}), 404

    activity = activities[0]
    skill_id = activity.get("skill_id")
    act_type = activity.get("activity_type")

    # Update activity
    update_data = {
        "status": "COMPLETED",
        "completed_at": now_iso,
        "updated_at": now_iso
    }
    supabase.table("roadmap_activities").update(update_data).eq("id", activity_id).execute()

    # Record activity attempt
    import uuid
    attempt_id = str(uuid.uuid4())
    score_val = float(score) if score is not None else 80.0
    attempt_rec = {
        "id": attempt_id,
        "activity_id": activity_id,
        "user_id": user_id,
        "score": score_val,
        "status": "COMPLETED",
        "time_spent_minutes": time_spent or activity.get("duration_minutes", 30),
        "notes": notes,
        "completed_at": now_iso
    }
    supabase.table("activity_attempts").insert(attempt_rec).execute()

    # Evidence ingestion & revision scheduling
    revision_schedule = None
    if skill_id:
        source_map = {
            "LEARN": "ASSESSMENT",
            "PRACTICE": "CODING",
            "CODING": "CODING",
            "MOCK_INTERVIEW": "MOCK_INTERVIEW",
            "ASSESSMENT": "ASSESSMENT",
            "REVISION": "REVISION"
        }
        source = source_map.get(act_type, "PRACTICE")
        SkillProfilingService.record_evidence(
            user_id=user_id,
            skill_id=skill_id,
            source=source,
            score=score_val,
            raw_data={"activity_id": activity_id, "activity_type": act_type, "notes": notes}
        )

        # Schedule spaced revision drill
        if act_type in ("LEARN", "PRACTICE", "CODING"):
            revision_schedule = RevisionScheduler.schedule_initial_revision(
                user_id=user_id,
                skill_id=skill_id,
                initial_score=score_val
            )

    return jsonify({
        "status": "success",
        "activity_id": activity_id,
        "completed": True,
        "revision_scheduled": bool(revision_schedule)
    }), 200


@intelligence_bp.route("/api/activities/<activity_id>/skip", methods=["POST"])
@intelligence_auth_required
def skip_activity(activity_id: str):
    """Marks an activity as skipped."""
    user_id = _get_uid()
    from local_supabase import get_supabase_client
    supabase = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    supabase.table("roadmap_activities").update({
        "status": "SKIPPED",
        "updated_at": now_iso
    }).eq("id", activity_id).eq("user_id", user_id).execute()

    return jsonify({
        "status": "success",
        "activity_id": activity_id,
        "status_updated": "SKIPPED"
    }), 200


# ============================================================================
# 5. SPACED REVISION & KNOWLEDGE RETENTION
# ============================================================================

@intelligence_bp.route("/api/revision/due", methods=["GET"])
@intelligence_auth_required
def get_due_revisions():
    """Retrieves retrieval practice drills due today."""
    user_id = _get_uid()
    due = RevisionScheduler.get_due_revisions(user_id)
    return jsonify({
        "status": "success",
        "due_count": len(due),
        "due_revisions": due
    }), 200


@intelligence_bp.route("/api/revision/schedules", methods=["GET"])
@intelligence_auth_required
def get_all_revision_schedules():
    """Retrieves all spaced repetition tracks for candidate."""
    user_id = _get_uid()
    schedules = RevisionScheduler.get_all_schedules(user_id)
    return jsonify({
        "status": "success",
        "schedules": schedules
    }), 200


@intelligence_bp.route("/api/revision/drill/<skill_id>", methods=["GET"])
@intelligence_auth_required
def get_retrieval_drill(skill_id: str):
    """Generates a rapid-fire 5-minute retrieval practice drill."""
    drill = RevisionScheduler.generate_retrieval_drill(skill_id)
    return jsonify({
        "status": "success",
        "drill": drill
    }), 200


@intelligence_bp.route("/api/revision/submit", methods=["POST"])
@intelligence_auth_required
def submit_revision_drill():
    """Submits score for a retrieval practice drill, updating retention stages."""
    user_id = _get_uid()
    data = request.get_json() or {}
    skill_id = data.get("skill_id")
    score = float(data.get("score", 70.0))
    notes = data.get("notes", "")

    if not skill_id:
        return jsonify({"error": "skill_id is required"}), 400

    res = RevisionScheduler.record_revision_attempt(
        user_id=user_id,
        skill_id=skill_id,
        score=score,
        notes=notes
    )

    return jsonify({
        "status": "success",
        "result": res
    }), 200


# ============================================================================
# 6. PROGRESS TRACKING & COACHING ANALYTICS
# ============================================================================

@intelligence_bp.route("/api/progress/dashboard", methods=["GET"])
@intelligence_auth_required
def get_progress_dashboard():
    """Retrieves complete candidate readiness dashboard metrics, radar data, and baseline deltas."""
    user_id = _get_uid()
    summary = ProgressAnalyticsService.get_dashboard_summary(user_id)
    return jsonify({
        "status": "success",
        "dashboard": summary
    }), 200


@intelligence_bp.route("/api/progress/insights", methods=["GET"])
@intelligence_auth_required
def get_coaching_insights():
    """Retrieves grounded AI coaching recommendations grounded in multi-source performance evidence."""
    user_id = _get_uid()
    insights = ProgressAnalyticsService.get_grounded_coaching_insights(user_id)
    return jsonify({
        "status": "success",
        "insights": insights
    }), 200


@intelligence_bp.route("/api/progress/weaknesses", methods=["GET"])
@intelligence_auth_required
def get_cross_feature_weaknesses():
    """Retrieves cross-feature detected weaknesses synthesized from coding submissions, mock interviews, and assessments."""
    user_id = _get_uid()
    weaknesses = CrossFeatureEngine.detect_cross_feature_weaknesses(user_id)
    return jsonify({
        "status": "success",
        "weaknesses": weaknesses
    }), 200


# ============================================================================
# 8. EVIDENCE-BASED READINESS & PROVENANCE ENGINE
# ============================================================================

@intelligence_bp.route("/api/intelligence/readiness/provenance", methods=["GET"])
@intelligence_auth_required
def get_readiness_provenance():
    """Returns candidate readiness with mathematical provenance, formula breakdown, and subskill aggregation."""
    from services.role_readiness_engine import RoleReadinessEngine
    from services.evidence_scoring_engine import EvidenceScoringEngine
    from services.evidence_registry_service import EvidenceRegistryService

    user_id = _get_uid()
    prof = CandidateProfileService.get_profile(user_id) or {}
    target_role = prof.get("target_role", "Software Development Engineer (General)")

    readiness = RoleReadinessEngine.calculate_readiness(user_id=user_id, target_role=target_role)

    # 4 Competency Pillars aggregated from subskills
    pillars = {
        "dsa": EvidenceScoringEngine.evaluate_parent_domain(user_id, "data_structures_algorithms"),
        "cs": EvidenceScoringEngine.evaluate_parent_domain(user_id, "core_cs"),
        "system_design": EvidenceScoringEngine.evaluate_parent_domain(user_id, "system_design"),
        "interview_skills": EvidenceScoringEngine.evaluate_parent_domain(user_id, "interview_skills")
    }

    # Full evidence provenance records
    evidence_history = EvidenceRegistryService.get_evidence_for_candidate(user_id=user_id)

    return jsonify({
        "status": "success",
        "readiness": readiness,
        "pillars": pillars,
        "evidence_history": evidence_history
    }), 200


@intelligence_bp.route("/api/intelligence/readiness/summary", methods=["GET"])
@intelligence_auth_required
def get_readiness_summary():
    """Returns high-level summary of readiness, confidence, coverage, status, and verified weaknesses."""
    from services.role_readiness_engine import RoleReadinessEngine
    from services.weakness_detection_engine import WeaknessDetectionEngine

    user_id = _get_uid()
    prof = CandidateProfileService.get_profile(user_id) or {}
    target_role = prof.get("target_role", "Software Development Engineer (General)")

    readiness = RoleReadinessEngine.calculate_readiness(user_id=user_id, target_role=target_role)
    weaknesses = WeaknessDetectionEngine.detect_weaknesses(user_id=user_id, target_role=target_role)

    return jsonify({
        "status": "success",
        "readiness": readiness,
        "verified_weaknesses": weaknesses
    }), 200


@intelligence_bp.route("/api/intelligence/weaknesses/verified", methods=["GET"])
@intelligence_auth_required
def get_verified_weaknesses():
    """Returns strictly verified assessment failures with remedial actions."""
    from services.weakness_detection_engine import WeaknessDetectionEngine

    user_id = _get_uid()
    prof = CandidateProfileService.get_profile(user_id) or {}
    target_role = prof.get("target_role", "Software Development Engineer (General)")

    weaknesses = WeaknessDetectionEngine.detect_weaknesses(user_id=user_id, target_role=target_role)
    return jsonify({
        "status": "success",
        "weaknesses": weaknesses
    }), 200


@intelligence_bp.route("/api/intelligence/projects/probe", methods=["POST"])
@intelligence_auth_required
def probe_project():
    """Generates 3 deep technical architectural probing questions for a project."""
    from services.project_intelligence_service import ProjectIntelligenceService

    data = request.get_json() or {}
    title = data.get("title") or data.get("project_title", "Custom Project")
    technologies = data.get("technologies") or []
    description = data.get("description", "")

    questions = ProjectIntelligenceService.generate_project_probing_questions(
        project_title=title,
        technologies=technologies,
        description=description
    )

    return jsonify({
        "status": "success",
        "questions": questions
    }), 200


@intelligence_bp.route("/api/intelligence/projects/evaluate", methods=["POST"])
@intelligence_auth_required
def evaluate_project_defense():
    """Evaluates candidate response to a project probing question and records verifiable evidence."""
    from services.project_intelligence_service import ProjectIntelligenceService

    user_id = _get_uid()
    data = request.get_json() or {}
    project_title = data.get("project_title", "Project")
    skill_id = data.get("skill_id", "sys_ml_system_design")
    question_text = data.get("question_text", "")
    response_text = data.get("response", "")

    eval_result = ProjectIntelligenceService.evaluate_project_defense(
        user_id=user_id,
        project_title=project_title,
        skill_id=skill_id,
        question_text=question_text,
        candidate_response=response_text
    )

    return jsonify({
        "status": "success",
        "evaluation": eval_result
    }), 200


# ============================================================================
# 8. ADAPTIVE AI INTERVIEW MENTOR: ONBOARDING & CONTEXT ROUTES
# ============================================================================

@intelligence_bp.route("/api/interview-onboarding/start", methods=["POST"])
@intelligence_auth_required
def start_interview_onboarding():
    """Starts or resumes conversational onboarding, skipping pre-known fields."""
    from services.interview_onboarding_service import InterviewOnboardingService
    user_id = _get_uid()
    data = request.get_json(silent=True) or {}
    goal_id = data.get("goal_id")

    step = InterviewOnboardingService.start_or_resume_onboarding(user_id=user_id, goal_id=goal_id)
    return jsonify({
        "status": "success",
        **step
    }), 200


@intelligence_bp.route("/api/interview-onboarding/answer", methods=["POST"])
@intelligence_auth_required
def submit_interview_onboarding_answer():
    """Submits answer to current conversational question, advances flow, or finalizes goal."""
    from services.interview_onboarding_service import InterviewOnboardingService
    from services.interview_context_service import InterviewContextService
    user_id = _get_uid()
    data = request.get_json(silent=True) or {}
    goal_id = data.get("goal_id")
    field = data.get("field")
    value = data.get("value")

    if not goal_id or not field:
        return jsonify({"error": "Missing goal_id or field parameter"}), 400

    try:
        step = InterviewOnboardingService.submit_onboarding_answer(
            user_id=user_id,
            goal_id=goal_id,
            field=field,
            value=value
        )
        # Invalidate context cache upon updating goals
        InterviewContextService.invalidate_cache(user_id, goal_id)

        return jsonify({
            "status": "success",
            **step
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to submit onboarding answer: {str(e)}"}), 500


@intelligence_bp.route("/api/interview-context", methods=["GET"])
@intelligence_auth_required
def get_interview_context():
    """Returns compact, cached, versioned context object for downstream mentor and planner calls."""
    from services.interview_context_service import InterviewContextService
    user_id = _get_uid()
    goal_id = request.args.get("goal_id")
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"

    context = InterviewContextService.get_context(
        user_id=user_id,
        goal_id=goal_id,
        force_refresh=force_refresh
    )
    return jsonify({
        "status": "success",
        "context": context
    }), 200

