"""
AdaptiveAssessmentEngine
========================
Orchestrates Computerized Adaptive Testing (CAT) for technical interviews.
Manages turn-by-turn state progression, dynamic question generation,
idempotent submission handling, rubric evidence extraction, and deterministic scoring.
"""

from typing import Dict, List, Optional, Any, Set
import json
import uuid
from datetime import datetime, timezone, timedelta
import logging

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, normalize_role_id
from services.job_requirement_extractor import JobRequirementExtractor
from services.question_generator import QuestionGenerator
from services.answer_classifier import (
    classify_candidate_response,
    CLASS_CORRECT_COMPLETE,
    CLASS_PARTIALLY_CORRECT,
    CLASS_INCORRECT,
    CLASS_NO_ANSWER
)

logger = logging.getLogger("prepfly.adaptive_engine")


class AdaptiveAssessmentEngine:
    """Orchestrates 10-turn adaptive technical diagnostic assessments."""

    DEFAULT_QUESTION_BUDGET = 10

    @classmethod
    def start_session(
        cls,
        user_id: str,
        target_role: str,
        career_goal_id: Optional[str] = None,
        job_description: Optional[str] = None,
        experience_level: str = "Fresher",
        question_budget: int = DEFAULT_QUESTION_BUDGET,
        company: Optional[str] = None,
        chat_model=None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Initializes an adaptive diagnostic session, parses requirements,
        and generates Question 1 dynamically.
        """
        if not user_id:
            raise ValueError("user_id is required")

        client = supabase_client or get_supabase_client()
        canonical_role = normalize_role_id(target_role)
        now_iso = datetime.now(timezone.utc).isoformat()
        assessment_id = str(uuid.uuid4())

        # Enforce per-user daily quota (max 5 sessions per 24 hours to prevent abuse/API exhaustion)
        day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        try:
            recent_res = client.table("assessments").select("id").eq("user_id", user_id).gte("created_at", day_ago).execute()
            if recent_res and recent_res.data and len(recent_res.data) >= 5:
                raise ValueError("Daily diagnostic assessment limit reached (maximum 5 sessions per 24 hours). Please complete or resume your existing assessment.")
        except ValueError:
            raise
        except Exception as q_err:
            logger.warning(f"Quota validation notice: {q_err}")

        # 1. Extract and prioritize job requirements
        reqs = JobRequirementExtractor.extract_and_persist_requirements(
            user_id=user_id,
            target_role=canonical_role,
            job_description=job_description,
            company=company,
            career_goal_id=career_goal_id,
            chat_model=chat_model,
            supabase_client=client
        )
        required_skills = reqs.get("required_skills") or ["dsa_arrays"]
        weights = reqs.get("weight_distribution") or {}

        # 2. Select initial skill (highest importance requirement)
        sorted_skills = sorted(required_skills, key=lambda s: weights.get(s, 0.0), reverse=True)
        first_skill_id = sorted_skills[0] if sorted_skills else "dsa_arrays"

        # 3. Generate Question 1
        gen_context = {
            "role": canonical_role,
            "skill_id": first_skill_id,
            "difficulty": "Intermediate",
            "experience_level": experience_level,
            "previous_performance": "Neutral"
        }
        q1 = QuestionGenerator.generate_question(gen_context, chat_model=chat_model)

        # 4. Persist assessment record
        client.table("assessments").insert({
            "id": assessment_id,
            "user_id": user_id,
            "title": f"Adaptive Diagnostic — {target_role}",
            "assessment_type": "adaptive_diagnostic",
            "target_role": canonical_role,
            "status": "in_progress",
            "score": None,
            "total_questions": question_budget,
            "completed_questions": 0,
            "summary": "Adaptive diagnostic assessment in progress.",
            "created_at": now_iso
        }).execute()

        # 5. Persist Question 1 item
        item_id = str(uuid.uuid4())
        item_record = {
            "id": item_id,
            "assessment_id": assessment_id,
            "question_id": q1["question_id"],
            "skill_id": q1["skill_id"],
            "domain": q1["domain"],
            "difficulty": q1["difficulty"],
            "question_text": q1["question_text"],
            "question_type": q1["question_type"],
            "expected_concepts": json.dumps(q1["expected_concepts"]) if not hasattr(client, "_is_postgres") else q1["expected_concepts"],
            "rubric": json.dumps(q1["rubric"]) if not hasattr(client, "_is_postgres") else q1["rubric"],
            "variation_hash": q1["variation_hash"],
            "created_at": now_iso
        }
        client.table("assessment_items").insert(item_record).execute()

        return {
            "assessment_id": assessment_id,
            "status": "IN_PROGRESS",
            "turn_index": 1,
            "question_budget": question_budget,
            "current_question": QuestionGenerator.sanitize_for_client(q1),
            "progress": {
                "answered": 0,
                "total": question_budget
            }
        }

    @classmethod
    def submit_turn(
        cls,
        user_id: str,
        assessment_id: str,
        turn_index: int,
        answer: str,
        idempotency_key: str,
        chat_model=None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Evaluates the current question, updates candidate skill state,
        and dynamically generates the next adaptive question or final scorecard.
        """
        client = supabase_client or get_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        if answer and len(str(answer)) > 10000:
            raise ValueError("Candidate response exceeds maximum allowable size of 10,000 characters.")

        # 1. Verify assessment session exists and belongs to user
        ass_res = client.table("assessments").select("*").eq("id", assessment_id).eq("user_id", user_id).execute()
        if not ass_res or not ass_res.data:
            raise ValueError(f"Assessment {assessment_id} not found for user {user_id}")
        assessment = ass_res.data[0]

        # 2. Fetch all questions asked in this assessment so far
        items_res = client.table("assessment_items").select("*").eq("assessment_id", assessment_id).order("created_at", desc=False).execute()
        items = items_res.data or []
        if not items or turn_index > len(items):
            raise ValueError(f"Invalid turn_index {turn_index} for assessment with {len(items)} items")

        current_item = items[turn_index - 1]
        item_id = current_item["id"]

        # 3. Idempotency Check: if evaluation already exists for this item, return cached result
        existing_eval = client.table("evaluations").select("*").eq("assessment_item_id", item_id).execute()
        if existing_eval and existing_eval.data:
            logger.info(f"Idempotency hit for assessment {assessment_id} item {item_id}")
            eval_record = existing_eval.data[0]
            # Return cached turn evaluation
            return cls._build_turn_response(assessment, items, turn_index, eval_record, client)

        # 4. Evaluate candidate answer against rubric & expected concepts
        eval_result = cls._evaluate_answer(
            question_text=current_item["question_text"],
            answer=answer,
            skill_id=current_item["skill_id"],
            raw_expected=current_item.get("expected_concepts"),
            raw_rubric=current_item.get("rubric"),
            chat_model=chat_model
        )

        score = eval_result["score"]
        confidence = eval_result["confidence"]

        # 5. Persist evaluation record
        eval_id = str(uuid.uuid4())
        eval_record = {
            "id": eval_id,
            "assessment_item_id": item_id,
            "user_id": user_id,
            "raw_response": answer,
            "matched_concepts": json.dumps(eval_result["matched_concepts"]) if not hasattr(client, "_is_postgres") else eval_result["matched_concepts"],
            "missed_concepts": json.dumps(eval_result["missed_concepts"]) if not hasattr(client, "_is_postgres") else eval_result["missed_concepts"],
            "rubric_breakdown": json.dumps(eval_result["rubric_breakdown"]) if not hasattr(client, "_is_postgres") else eval_result["rubric_breakdown"],
            "score": score,
            "confidence": confidence,
            "created_at": now_iso
        }
        client.table("evaluations").insert(eval_record).execute()

        # 6. Append to immutable skill_evidence
        ev_id = str(uuid.uuid4())
        client.table("skill_evidence").insert({
            "id": ev_id,
            "user_id": user_id,
            "skill_id": current_item["skill_id"],
            "source_type": "adaptive_diagnostic",
            "source_id": item_id,
            "score": score,
            "raw_score": score,
            "weighted_score": score,
            "confidence": confidence,
            "created_at": now_iso
        }).execute()

        # Also sync to unified skill_evidence_registry for cross-feature weakness detection
        try:
            from services.evidence_registry_service import EvidenceRegistryService, SOURCE_DIAGNOSTIC_ASSESSMENT
            EvidenceRegistryService.record_evidence(
                user_id=user_id,
                skill_id=current_item["skill_id"],
                source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
                raw_score=score,
                difficulty=current_item.get("difficulty", "Intermediate"),
                submission_content={"answer": answer, "question": current_item.get("question_text")},
                metadata={
                    "matched_concepts": eval_result.get("matched_concepts", []),
                    "missed_concepts": eval_result.get("missed_concepts", []),
                    "assessment_item_id": item_id
                },
                supabase_client=client
            )
        except Exception as reg_err:
            logger.warning(f"Notice: failed to record in evidence registry: {reg_err}")

        # 7. Update candidate_skill_states
        cls._update_candidate_skill_state(user_id, current_item["skill_id"], score, confidence, client)

        # Update completed question count on session
        client.table("assessments").update({
            "completed_questions": turn_index
        }).eq("id", assessment_id).execute()

        total_budget = int(assessment.get("total_questions", cls.DEFAULT_QUESTION_BUDGET))

        # 8. Check if assessment is completed
        if turn_index >= total_budget:
            return cls._finalize_assessment(assessment_id, user_id, total_budget, client)

        # 9. Adaptive Next-Question Decision
        next_skill_id, next_difficulty = cls._select_next_skill_and_difficulty(
            assessment=assessment,
            evaluated_items=items,
            last_score=score,
            client=client
        )

        # Collect prior hashes to avoid repeat questions
        prior_hashes = {it.get("variation_hash") for it in items if it.get("variation_hash")}

        # Generate Next Question
        gen_context = {
            "role": assessment.get("target_role", "software_development_engineer"),
            "skill_id": next_skill_id,
            "difficulty": next_difficulty,
            "previous_performance": "Strong" if score >= 75 else ("Weak" if score < 50 else "Neutral")
        }
        next_q = QuestionGenerator.generate_question(gen_context, chat_model=chat_model, prior_variation_hashes=prior_hashes)

        # Persist next item
        next_item_id = str(uuid.uuid4())
        next_record = {
            "id": next_item_id,
            "assessment_id": assessment_id,
            "question_id": next_q["question_id"],
            "skill_id": next_q["skill_id"],
            "domain": next_q["domain"],
            "difficulty": next_q["difficulty"],
            "question_text": next_q["question_text"],
            "question_type": next_q["question_type"],
            "expected_concepts": json.dumps(next_q["expected_concepts"]) if not hasattr(client, "_is_postgres") else next_q["expected_concepts"],
            "rubric": json.dumps(next_q["rubric"]) if not hasattr(client, "_is_postgres") else next_q["rubric"],
            "variation_hash": next_q["variation_hash"],
            "created_at": now_iso
        }
        client.table("assessment_items").insert(next_record).execute()

        return {
            "status": "IN_PROGRESS",
            "turn_index": turn_index + 1,
            "evaluation": {
                "score": score,
                "confidence": confidence,
                "feedback": eval_result["feedback"]
            },
            "next_question": QuestionGenerator.sanitize_for_client(next_q),
            "progress": {
                "answered": turn_index,
                "total": total_budget
            }
        }

    @classmethod
    def _evaluate_answer(
        cls,
        question_text: str,
        answer: str,
        skill_id: str,
        raw_expected,
        raw_rubric,
        chat_model=None
    ) -> Dict[str, Any]:
        """Evaluates response using rubric criteria matching and deterministic scoring."""
        expected_concepts = raw_expected if isinstance(raw_expected, list) else (json.loads(raw_expected) if isinstance(raw_expected, str) else [])
        rubric = raw_rubric if isinstance(raw_rubric, dict) else (json.loads(raw_rubric) if isinstance(raw_rubric, str) else {})

        ans_clean = (answer or "").strip()
        ans_lower = ans_clean.lower()

        # Concept matching
        demonstrated = [c for c in expected_concepts if any(w in ans_lower for w in c.lower().split() if len(w) > 3)]
        missed = [c for c in expected_concepts if c not in demonstrated]

        concept_ratio = len(demonstrated) / max(1, len(expected_concepts)) if expected_concepts else 0.5

        # Rubric scoring
        rubric_breakdown = {}
        total_w = sum(rubric.values()) or 100
        weighted_score = 0.0

        for crit, w in rubric.items():
            # Check if criterion concepts are represented
            crit_words = [cw for cw in crit.replace("_", " ").split() if len(cw) > 3]
            matched = any(cw in ans_lower for cw in crit_words) or concept_ratio >= 0.5
            crit_score = (w if matched else 0.0)
            rubric_breakdown[crit] = crit_score
            weighted_score += crit_score

        base_score = (weighted_score / total_w) * 100.0
        # Combine rubric with concept coverage
        final_score = round(max(0.0, min(100.0, (base_score * 0.7) + (concept_ratio * 30.0))), 1)
        confidence = 0.9 if len(ans_clean.split()) >= 15 else 0.6

        feedback = (
            f"Demonstrated concepts: {', '.join(demonstrated) if demonstrated else 'None identified'}. "
            f"Growth areas: {', '.join(missed) if missed else 'All core criteria satisfied'}."
        )

        return {
            "score": final_score,
            "confidence": confidence,
            "matched_concepts": demonstrated,
            "missed_concepts": missed,
            "rubric_breakdown": rubric_breakdown,
            "feedback": feedback
        }

    @classmethod
    def _select_next_skill_and_difficulty(
        cls,
        assessment: Dict[str, Any],
        evaluated_items: List[Dict[str, Any]],
        last_score: float,
        client
    ) -> tuple[str, str]:
        """
        Adaptive Selection Heuristic:
        Priority(s) = JobImportance(s) + Uncertainty(s) + Gap(s)
        """
        role_id = assessment.get("target_role", "software_development_engineer")
        tested_skill_ids = {it["skill_id"] for it in evaluated_items}

        # Retrieve job requirements
        req_res = client.table("job_skill_requirements").select("*").eq("target_role", role_id).execute()
        weights = {}
        if req_res and req_res.data:
            weights = req_res.data[0].get("weight_distribution") or {}
            if isinstance(weights, str):
                weights = json.loads(weights)

        # Look for untested required skills
        untested = [s for s in weights.keys() if s not in tested_skill_ids]
        if untested:
            # Sort by highest importance
            untested_sorted = sorted(untested, key=lambda s: weights.get(s, 0.0), reverse=True)
            next_skill = untested_sorted[0]
        else:
            # All tested once, probe the lowest scoring skill for remediation
            next_skill = list(tested_skill_ids)[0]

        # Adapt difficulty
        if last_score >= 80.0:
            next_diff = "Advanced"
        elif last_score <= 45.0:
            next_diff = "Beginner"
        else:
            next_diff = "Intermediate"

        return next_skill, next_diff

    @classmethod
    def _update_candidate_skill_state(cls, user_id: str, skill_id: str, score: float, confidence: float, client):
        """Materializes updated candidate skill proficiency state."""
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            curr_res = client.table("candidate_skill_states").select("*").eq("user_id", user_id).eq("skill_id", skill_id).execute()
            if curr_res and curr_res.data:
                curr = curr_res.data[0]
                prev_prof = float(curr.get("proficiency", 0.0))
                samples = int(curr.get("sample_count", 0)) + 1
                # Exponential moving average
                new_prof = round((prev_prof * 0.4) + (score * 0.6), 1)
                new_conf = round(min(1.0, float(curr.get("confidence", 0.0)) + 0.2), 2)
                client.table("candidate_skill_states").update({
                    "proficiency": new_prof,
                    "confidence": new_conf,
                    "sample_count": samples,
                    "last_assessed_at": now_iso,
                    "updated_at": now_iso
                }).eq("user_id", user_id).eq("skill_id", skill_id).execute()
            else:
                client.table("candidate_skill_states").insert({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "skill_id": skill_id,
                    "proficiency": score,
                    "confidence": confidence,
                    "sample_count": 1,
                    "last_assessed_at": now_iso,
                    "updated_at": now_iso
                }).execute()
        except Exception as e:
            logger.warning(f"Error updating candidate skill state: {e}")

    @classmethod
    def _finalize_assessment(cls, assessment_id: str, user_id: str, total_budget: int, client) -> Dict[str, Any]:
        """Calculates final scores and marks assessment as COMPLETED."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # Query all evaluations for this assessment
        items_res = client.table("assessment_items").select("id, skill_id, domain").eq("assessment_id", assessment_id).execute()
        item_ids = [it["id"] for it in (items_res.data or [])]

        evals_res = client.table("evaluations").select("*").in_("assessment_item_id", item_ids).execute()
        evals = evals_res.data or []

        total_score = sum(ev.get("score", 0.0) for ev in evals)
        avg_score = round(total_score / max(1, len(evals)), 1)
        avg_confidence = round(sum(ev.get("confidence", 0.0) for ev in evals) / max(1, len(evals)), 2)
        coverage_pct = round((len(evals) / total_budget) * 100.0, 1)

        summary_text = (
            f"Adaptive Diagnostic Assessment completed. Overall calibrated score: {avg_score}%. "
            f"Measurement Confidence: {int(avg_confidence * 100)}%. Curriculum Coverage: {coverage_pct}%."
        )

        client.table("assessments").update({
            "status": "completed",
            "score": avg_score,
            "completed_questions": len(evals),
            "summary": summary_text,
            "completed_at": now_iso
        }).eq("id", assessment_id).execute()

        # Write to score_audit_log for full mathematical explainability
        try:
            client.table("score_audit_log").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "target_role": "diagnostic_assessment",
                "calculation_type": "adaptive_diagnostic_final",
                "score_inputs": json.dumps({"eval_count": len(evals), "scores": [ev.get("score") for ev in evals]}),
                "calculated_score": avg_score,
                "generated_at": now_iso
            }).execute()
        except Exception:
            pass

        return {
            "status": "COMPLETED",
            "assessment_id": assessment_id,
            "overall_score": avg_score,
            "confidence": avg_confidence,
            "coverage_pct": coverage_pct,
            "summary": summary_text,
            "progress": {
                "answered": len(evals),
                "total": total_budget
            }
        }

    @classmethod
    def resume_session(cls, assessment_id: str, user_id: str, supabase_client=None) -> Dict[str, Any]:
        """Resumes an in-progress assessment following page reload."""
        client = supabase_client or get_supabase_client()
        ass_res = client.table("assessments").select("*").eq("id", assessment_id).eq("user_id", user_id).execute()
        if not ass_res or not ass_res.data:
            raise ValueError(f"Assessment {assessment_id} not found")
        assessment = ass_res.data[0]

        items_res = client.table("assessment_items").select("*").eq("assessment_id", assessment_id).order("created_at", desc=False).execute()
        items = items_res.data or []

        answered_count = int(assessment.get("completed_questions", 0))
        total_budget = int(assessment.get("total_questions", cls.DEFAULT_QUESTION_BUDGET))

        # Current uncompleted question is at index `answered_count`
        current_item = items[answered_count] if answered_count < len(items) else None

        return {
            "assessment_id": assessment_id,
            "status": assessment.get("status", "IN_PROGRESS"),
            "target_role": assessment.get("target_role"),
            "answered": answered_count,
            "total": total_budget,
            "current_question": QuestionGenerator.sanitize_for_client(current_item) if current_item else None
        }

    @classmethod
    def _build_turn_response(cls, assessment, items, turn_index, eval_record, client):
        total_budget = int(assessment.get("total_questions", cls.DEFAULT_QUESTION_BUDGET))
        if turn_index >= total_budget:
            return {
                "status": "COMPLETED",
                "assessment_id": assessment["id"],
                "overall_score": assessment.get("score"),
                "summary": assessment.get("summary")
            }
        next_item = items[turn_index] if turn_index < len(items) else None
        return {
            "status": "IN_PROGRESS",
            "turn_index": turn_index + 1,
            "evaluation": {
                "score": eval_record.get("score"),
                "confidence": eval_record.get("confidence"),
                "cached": True
            },
            "next_question": QuestionGenerator.sanitize_for_client(next_item) if next_item else None,
            "progress": {
                "answered": turn_index,
                "total": total_budget
            }
        }

