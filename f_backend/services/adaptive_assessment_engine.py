"""
AdaptiveAssessmentEngine
========================
Orchestrates Computerized Adaptive Testing (CAT) for technical diagnostics.
Manages turn-by-turn state progression, non-duplicate adaptive question generation,
idempotent submission handling, rubric evidence extraction, and calibrated scoring
that strictly distinguishes:
  1. Demonstrated Competency (overall_score)
  2. Measurement Confidence (confidence)
  3. Curriculum Coverage (coverage_pct)
  4. Assessment Completion (completion_pct)
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Callable
import json
import re
import statistics
import uuid
from datetime import datetime, timezone, timedelta
import logging

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, ROLE_REQUIREMENTS, normalize_role_id
from services.job_requirement_extractor import JobRequirementExtractor
from services.pure_scoring_engine import PureScoringEngine
from services.question_generator import QuestionGenerator
from services.answer_classifier import (
    classify_candidate_response,
    CLASS_CORRECT_COMPLETE,
    CLASS_PARTIALLY_CORRECT,
    CLASS_INCORRECT,
    CLASS_NO_ANSWER,
)

logger = logging.getLogger("prepfly.adaptive_engine")

_DIFFICULTY_ORDER = ["Beginner", "Intermediate", "Advanced"]

_SYNONYM_GROUPS = (
    ("hash map", "hashmap", "hash table", "hashtable", "dictionary", "dict"),
    ("l1", "lasso"),
    ("l2", "ridge"),
    ("pr-auc", "precision-recall", "precision recall", "pr curve"),
    ("roc-auc", "roc curve", "roc"),
    ("o(1)", "constant time"),
    ("o(n)", "linear time"),
    ("o(log n)", "logarithmic time"),
    ("bfs", "breadth-first search", "breadth first"),
    ("dfs", "depth-first search", "depth first"),
    ("cache-aside", "cache aside", "lazy loading"),
    ("thundering herd", "cache stampede", "stampede"),
    ("rag", "retrieval-augmented generation", "retrieval augmented"),
    ("rlhf", "reinforcement learning from human feedback"),
    ("dpo", "direct preference optimization"),
    ("cot", "chain-of-thought", "chain of thought"),
    ("zero", "0", "none", "no comparisons"),
)


def _extract_tech_tokens(text: str) -> Set[str]:
    """Extracts normalized technical tokens including short symbols (0, L1, L2, O(1), PR, SQL)."""
    low = (text or "").lower()
    tokens: Set[str] = set()
    # Preserve Big-O expressions explicitly
    for big_o in re.findall(r"o\([^)]+\)", low):
        tokens.add(re.sub(r"\s+", "", big_o))
    # Alphanumeric words (keep single digit numbers like '0' and 2+ char tech symbols)
    for tok in re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", low):
        if len(tok) >= 2 or tok.isdigit():
            tokens.add(tok)
    return tokens


def _expand_with_synonyms(text: str, tokens: Set[str]) -> Set[str]:
    low = (text or "").lower()
    expanded = set(tokens)
    for group in _SYNONYM_GROUPS:
        if any((g in low) or (g in tokens) for g in group):
            for g in group:
                expanded.add(g)
    return expanded


class AdaptiveAssessmentEngine:
    """Orchestrates multi-turn adaptive technical diagnostic assessments."""

    DEFAULT_QUESTION_BUDGET = 10

    @classmethod
    def _resolve_chat_model(cls, chat_model=None):
        if chat_model is not None:
            return chat_model
        try:
            import os
            if os.getenv("ENVIRONMENT") == "test" or os.getenv("FLASK_ENV") == "test":
                return None
            import app as app_module
            return getattr(app_module, "chat_model", None)
        except Exception:
            return None

    @classmethod
    def _load_role_weights(cls, user_id: str, role_id: str, client) -> Dict[str, float]:
        """Loads user+role JD requirements with fallback to canonical ROLE_REQUIREMENTS."""
        canonical = normalize_role_id(role_id)
        try:
            req_res = (
                client.table("job_skill_requirements")
                .select("*")
                .eq("user_id", user_id)
                .eq("target_role", canonical)
                .execute()
            )
            if req_res and req_res.data:
                weights = req_res.data[-1].get("weight_distribution") or {}
                if isinstance(weights, str):
                    weights = json.loads(weights)
                if isinstance(weights, dict) and weights:
                    return {str(k): float(v) for k, v in weights.items() if float(v) > 0}
        except Exception as exc:
            logger.warning(f"Failed reading job_skill_requirements: {exc}")

        role_defaults = ROLE_REQUIREMENTS.get(canonical) or ROLE_REQUIREMENTS.get("software_development_engineer", {})
        total = sum(role_defaults.values()) or 1.0
        return {k: round(v / total, 4) for k, v in role_defaults.items()}

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
        supabase_client=None,
    ) -> Dict[str, Any]:
        """
        Initializes an adaptive diagnostic session, parses requirements,
        and generates Question 1 dynamically without duplication.
        """
        if not user_id:
            raise ValueError("user_id is required")

        client = supabase_client or get_supabase_client()
        canonical_role = normalize_role_id(target_role)
        now_iso = datetime.now(timezone.utc).isoformat()
        assessment_id = str(uuid.uuid4())
        resolved_model = cls._resolve_chat_model(chat_model)

        # Enforce per-user daily quota (max 5 sessions per 24 hours)
        day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        try:
            recent_res = (
                client.table("assessments").select("id").eq("user_id", user_id).gte("created_at", day_ago).execute()
            )
            if recent_res and recent_res.data and len(recent_res.data) >= 5:
                raise ValueError(
                    "Daily diagnostic assessment limit reached (maximum 5 sessions per 24 hours). "
                    "Please complete or resume your existing assessment."
                )
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
            chat_model=resolved_model,
            supabase_client=client,
        )
        required_skills = reqs.get("required_skills") or ["dsa_arrays"]
        weights = reqs.get("weight_distribution") or {}

        # 2. Select initial skill (highest importance requirement; break weight ties toward curated conceptual core skills)
        from services.question_generator import DOMAIN_FALLBACK_BANKS
        curated_skills = {it["skill_id"] for it in DOMAIN_FALLBACK_BANKS.get(canonical_role, [])}
        sorted_skills = sorted(
            required_skills,
            key=lambda s: (weights.get(s, 0.0), 1 if s in curated_skills else 0),
            reverse=True,
        )
        first_skill_id = sorted_skills[0] if sorted_skills else "dsa_arrays"

        initial_diff = "Beginner" if experience_level == "Fresher" and len(sorted_skills) > 10 else "Intermediate"
        if experience_level in ("Senior",):
            initial_diff = "Intermediate"

        # 3. Generate Question 1
        gen_context = {
            "user_id": user_id,
            "assessment_id": assessment_id,
            "turn_index": 1,
            "role": canonical_role,
            "skill_id": first_skill_id,
            "difficulty": initial_diff,
            "experience_level": experience_level,
            "previous_performance": "Neutral",
        }
        q1 = QuestionGenerator.generate_question(
            gen_context,
            chat_model=resolved_model,
            prior_variation_hashes=set(),
            prior_question_texts=[],
        )

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
            "created_at": now_iso,
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
            "turn_index": 1,
            "created_at": now_iso,
        }
        client.table("assessment_items").insert(item_record).execute()

        return {
            "assessment_id": assessment_id,
            "status": "IN_PROGRESS",
            "turn_index": 1,
            "question_budget": question_budget,
            "current_question": QuestionGenerator.sanitize_for_client(q1),
            "progress": {"answered": 0, "total": question_budget},
        }

    @classmethod
    def submit_turn(
        cls,
        user_id: str,
        assessment_id: str,
        turn_index: int,
        answer: Any,
        idempotency_key: str,
        chat_model=None,
        supabase_client=None,
        evaluator_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates the current question, updates candidate skill state,
        and dynamically generates the next non-duplicate adaptive question or final scorecard.
        """
        client = supabase_client or get_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        resolved_model = cls._resolve_chat_model(chat_model)

        if answer is not None and len(str(answer)) > 10000:
            raise ValueError("Candidate response exceeds maximum allowable size of 10,000 characters.")

        # Preserve numeric 0 explicitly as string "0" rather than treating falsy int/float as empty
        answer_text = "" if answer is None else str(answer)

        # 1. Verify assessment session exists and belongs to user
        ass_res = client.table("assessments").select("*").eq("id", assessment_id).eq("user_id", user_id).execute()
        if not ass_res or not ass_res.data:
            raise ValueError(f"Assessment {assessment_id} not found for user {user_id}")
        assessment = ass_res.data[0]

        # 2. Fetch all questions asked in this assessment so far
        items_res = (
            client.table("assessment_items").select("*").eq("assessment_id", assessment_id).order("created_at", desc=False).execute()
        )
        items = items_res.data or []
        if not items or turn_index < 1 or turn_index > len(items):
            raise ValueError(f"Invalid turn_index {turn_index} for assessment with {len(items)} items")

        current_item = items[turn_index - 1]
        item_id = current_item["id"]

        # 3. Idempotency Check: if evaluation already exists for this item, return cached result
        existing_eval = client.table("evaluations").select("*").eq("assessment_item_id", item_id).execute()
        if existing_eval and existing_eval.data:
            logger.info(f"Idempotency hit for assessment {assessment_id} item {item_id}")
            eval_record = existing_eval.data[0]
            return cls._build_turn_response(assessment, items, turn_index, eval_record, client)

        # 4. Evaluate candidate answer safely (never silently coerce evaluator failures to 0%)
        eval_result = cls._evaluate_answer(
            question_text=current_item["question_text"],
            answer=answer_text,
            skill_id=current_item["skill_id"],
            raw_expected=current_item.get("expected_concepts"),
            raw_rubric=current_item.get("rubric"),
            chat_model=resolved_model,
            evaluator_fn=evaluator_fn,
        )

        eval_status = eval_result.get("evaluation_status", "evaluated")
        raw_score = eval_result.get("score")
        confidence = float(eval_result.get("confidence", 0.0))

        # 5. Persist evaluation record (DB column score is NOT NULL -> -1.0 sentinel on failed/pending)
        db_score = float(raw_score) if (eval_status == "evaluated" and raw_score is not None) else -1.0
        breakdown_payload = dict(eval_result.get("rubric_breakdown") or {})
        breakdown_payload["_meta"] = {
            "evaluation_status": eval_status,
            "is_empty": bool(eval_result.get("is_empty")),
            "error": eval_result.get("error"),
        }

        eval_id = str(uuid.uuid4())
        eval_record = {
            "id": eval_id,
            "assessment_item_id": item_id,
            "user_id": user_id,
            "raw_response": answer_text,
            "matched_concepts": json.dumps(eval_result["matched_concepts"]) if not hasattr(client, "_is_postgres") else eval_result["matched_concepts"],
            "missed_concepts": json.dumps(eval_result["missed_concepts"]) if not hasattr(client, "_is_postgres") else eval_result["missed_concepts"],
            "rubric_breakdown": json.dumps(breakdown_payload) if not hasattr(client, "_is_postgres") else breakdown_payload,
            "score": db_score,
            "confidence": confidence,
            "created_at": now_iso,
        }
        client.table("evaluations").insert(eval_record).execute()

        # 6. Only record skill evidence and update skill state for valid evaluated responses
        if eval_status == "evaluated" and raw_score is not None:
            score_val = float(raw_score)
            ev_id = str(uuid.uuid4())
            client.table("skill_evidence").insert({
                "id": ev_id,
                "user_id": user_id,
                "skill_id": current_item["skill_id"],
                "source_type": "adaptive_diagnostic",
                "source_id": item_id,
                "score": score_val,
                "raw_score": score_val,
                "weighted_score": score_val,
                "confidence": confidence,
                "created_at": now_iso,
            }).execute()

            try:
                from services.evidence_registry_service import EvidenceRegistryService, SOURCE_DIAGNOSTIC_ASSESSMENT
                EvidenceRegistryService.record_evidence(
                    user_id=user_id,
                    skill_id=current_item["skill_id"],
                    source_type=SOURCE_DIAGNOSTIC_ASSESSMENT,
                    raw_score=score_val,
                    difficulty=current_item.get("difficulty", "Intermediate"),
                    submission_content={"answer": answer_text, "question": current_item.get("question_text")},
                    metadata={
                        "matched_concepts": eval_result.get("matched_concepts", []),
                        "missed_concepts": eval_result.get("missed_concepts", []),
                        "assessment_item_id": item_id,
                    },
                    supabase_client=client,
                )
            except Exception as reg_err:
                logger.warning(f"Notice: failed to record in evidence registry: {reg_err}")

            cls._update_candidate_skill_state(user_id, current_item["skill_id"], score_val, confidence, client)

        # Update completed question count on session
        client.table("assessments").update({"completed_questions": turn_index}).eq("id", assessment_id).execute()

        total_budget = int(assessment.get("total_questions", cls.DEFAULT_QUESTION_BUDGET))

        # 8. Check if assessment is completed
        if turn_index >= total_budget:
            return cls._finalize_assessment(assessment_id, user_id, total_budget, client, target_role=assessment.get("target_role"))

        # 9. Adaptive Next-Question Decision (uses score if valid, else neutral)
        adaptive_signal_score = float(raw_score) if (eval_status == "evaluated" and raw_score is not None) else 60.0
        next_skill_id, next_difficulty = cls._select_next_skill_and_difficulty(
            assessment=assessment,
            evaluated_items=items,
            last_score=adaptive_signal_score,
            last_difficulty=current_item.get("difficulty", "Intermediate"),
            client=client,
            item_scores={item_id: adaptive_signal_score},
        )

        # Collect ALL prior hashes and question texts to guarantee zero repeats
        prior_hashes = {it.get("variation_hash") for it in items if it.get("variation_hash")}
        prior_texts = [it.get("question_text") for it in items if it.get("question_text")]

        gen_context = {
            "user_id": user_id,
            "assessment_id": assessment_id,
            "turn_index": turn_index + 1,
            "role": assessment.get("target_role", "software_development_engineer"),
            "skill_id": next_skill_id,
            "difficulty": next_difficulty,
            "previous_performance": "Strong" if adaptive_signal_score >= 75 else ("Weak" if adaptive_signal_score < 50 else "Neutral"),
        }
        next_q = QuestionGenerator.generate_question(
            gen_context,
            chat_model=resolved_model,
            prior_variation_hashes=prior_hashes,
            prior_question_texts=prior_texts,
        )

        # Final uniqueness defense-in-depth
        if QuestionGenerator.is_duplicate_question(next_q.get("question_text", ""), prior_hashes, prior_texts):
            skill_info = SkillTaxonomyService.get_skill(next_skill_id) or {"name": next_skill_id, "category": "General"}
            next_q = QuestionGenerator._synthesize_taxonomy_question(
                skill_id=next_skill_id,
                skill_info=skill_info,
                role_id=normalize_role_id(assessment.get("target_role", "software_development_engineer")),
                difficulty=next_difficulty,
                prior_hashes=prior_hashes,
                prior_texts=prior_texts,
                turn_index=turn_index + 1,
            )

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
            "turn_index": turn_index + 1,
            "created_at": now_iso,
        }
        client.table("assessment_items").insert(next_record).execute()

        return {
            "status": "IN_PROGRESS",
            "turn_index": turn_index + 1,
            "evaluation": {
                "score": raw_score if eval_status == "evaluated" else None,
                "evaluation_status": eval_status,
                "confidence": confidence,
                "feedback": eval_result["feedback"],
            },
            "next_question": QuestionGenerator.sanitize_for_client(next_q),
            "progress": {"answered": turn_index, "total": total_budget},
        }

    @classmethod
    def _evaluate_answer(
        cls,
        question_text: str,
        answer: Any,
        skill_id: str,
        raw_expected,
        raw_rubric,
        expected_answer: Optional[str] = None,
        chat_model=None,
        evaluator_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates candidate response cleanly distinguishing:
          - Empty response ("", None, whitespace) -> score 0.0, is_empty=True, evaluation_status="evaluated"
          - Numeric zero (0, "0", "0.0") -> evaluated strictly against expected answer/rubric (NEVER treated as missing)
          - Evaluator exception -> evaluation_status="failed", score=None (NEVER silently marked incorrect/0)
        """
        expected_concepts = (
            raw_expected if isinstance(raw_expected, list)
            else (json.loads(raw_expected) if isinstance(raw_expected, str) and raw_expected.strip().startswith("[") else [])
        )
        rubric = (
            raw_rubric if isinstance(raw_rubric, dict)
            else (json.loads(raw_rubric) if isinstance(raw_rubric, str) and raw_rubric.strip().startswith("{") else {})
        )

        # Optional pluggable/mocked evaluator hook (failures must propagate to failure handler, never become 0%)
        if evaluator_fn is not None:
            try:
                ext_res = evaluator_fn(
                    question_text=question_text,
                    answer=answer,
                    skill_id=skill_id,
                    expected_concepts=expected_concepts,
                    rubric=rubric,
                )
                if not isinstance(ext_res, dict) or ext_res.get("score") is None:
                    raise ValueError("Evaluator returned incomplete result without score")
                return {
                    "score": round(max(0.0, min(100.0, float(ext_res["score"]))), 1),
                    "confidence": float(ext_res.get("confidence", 0.85)),
                    "matched_concepts": list(ext_res.get("matched_concepts", [])),
                    "missed_concepts": list(ext_res.get("missed_concepts", [])),
                    "rubric_breakdown": dict(ext_res.get("rubric_breakdown", {})),
                    "feedback": ext_res.get("feedback", "Evaluated by rubric grader."),
                    "evaluation_status": "evaluated",
                    "is_empty": False,
                }
            except Exception as eval_exc:
                logger.warning(f"External/LLM evaluator failure on skill {skill_id}: {eval_exc}")
                return {
                    "score": None,
                    "confidence": 0.0,
                    "matched_concepts": [],
                    "missed_concepts": list(expected_concepts),
                    "rubric_breakdown": {},
                    "feedback": "Evaluation temporarily pending due to grader service error.",
                    "evaluation_status": "failed",
                    "error": str(eval_exc),
                    "is_empty": False,
                }

        # Distinguish empty submission vs numeric zero (0 / "0")
        is_empty = (answer is None) or (isinstance(answer, str) and answer.strip() == "")
        if is_empty:
            return {
                "score": 0.0,
                "confidence": 0.5,
                "matched_concepts": [],
                "missed_concepts": list(expected_concepts),
                "rubric_breakdown": {},
                "feedback": "No response submitted for evaluation.",
                "evaluation_status": "evaluated",
                "is_empty": True,
            }

        ans_clean = str(answer).strip()
        ans_lower = ans_clean.lower()
        is_numeric_zero = ans_lower in ("0", "0.0", "-0", "zero")

        # Handle exact numeric zero against question / expected_answer / expected_concepts
        if is_numeric_zero:
            exp_text_all = " ".join(
                [str(expected_answer or ""), *(str(c) for c in expected_concepts)]
            ).lower()
            zero_is_expected = bool(
                (expected_answer is not None and str(expected_answer).strip().lower() in ("0", "0.0", "-0", "zero"))
                or re.search(r"\b(0|zero)\b", exp_text_all)
            )
            if zero_is_expected:
                return {
                    "score": 90.0,
                    "confidence": 0.85,
                    "matched_concepts": [c for c in expected_concepts if re.search(r"\b(0|zero)\b", str(c).lower())] or ["0"],
                    "missed_concepts": [c for c in expected_concepts if not re.search(r"\b(0|zero)\b", str(c).lower())],
                    "rubric_breakdown": {"exact_value": 90.0},
                    "feedback": "Exact numeric value '0' matches the expected boundary/result.",
                    "evaluation_status": "evaluated",
                    "is_empty": False,
                }
            return {
                "score": 10.0,
                "confidence": 0.75,
                "matched_concepts": [],
                "missed_concepts": list(expected_concepts),
                "rubric_breakdown": {"exact_value": 10.0},
                "feedback": "Numeric response '0' does not satisfy the expected solution criteria.",
                "evaluation_status": "evaluated",
                "is_empty": False,
            }

        # Non-empty general response evaluation
        ans_tokens = _expand_with_synonyms(ans_lower, _extract_tech_tokens(ans_lower))

        # 1. Compute fractional concept credit (handles short tokens like L1, L2, PR, ML, O(1))
        demonstrated: List[str] = []
        missed: List[str] = []
        concept_credits: List[float] = []

        for concept in expected_concepts:
            c_str = str(concept).strip()
            c_low = c_str.lower()
            c_tokens = _extract_tech_tokens(c_low)
            if not c_tokens:
                matched_frac = 1.0 if c_low in ans_lower else 0.0
            else:
                hits = 0.0
                for ct in c_tokens:
                    if ct in ans_tokens or (len(ct) >= 3 and ct in ans_lower):
                        hits += 1.0
                    elif any(ct in at and len(ct) >= 4 for at in ans_tokens):
                        hits += 0.75
                matched_frac = min(1.0, hits / max(1, min(len(c_tokens), 4)))

            concept_credits.append(matched_frac)
            if matched_frac >= 0.35:
                demonstrated.append(c_str)
            else:
                missed.append(c_str)

        concept_ratio = (sum(concept_credits) / len(concept_credits)) if concept_credits else 0.0

        # 2. Classifier sanity check (catches "I don't know", off-topic, skips, empty-intent answers)
        skill_meta = SkillTaxonomyService.get_skill(skill_id) or {}
        classification, cls_acc, _dims, _rat = classify_candidate_response(
            question=question_text,
            answer=ans_clean,
            expected_keywords=[str(c) for c in expected_concepts],
            category=skill_meta.get("category", ""),
        )
        if classification == CLASS_NO_ANSWER:
            return {
                "score": 0.0,
                "confidence": 0.8,
                "matched_concepts": [],
                "missed_concepts": list(expected_concepts),
                "rubric_breakdown": {},
                "feedback": "Candidate indicated no answer or skipped the question.",
                "evaluation_status": "evaluated",
                "is_empty": False,
            }

        # 3. Evaluate weighted rubric via PureScoringEngine
        numeric_rubric_weights: Dict[str, float] = {}
        criteria_achievements: Dict[str, float] = {}

        if rubric:
            has_numeric_weights = all(isinstance(v, (int, float)) for v in rubric.values())
            if has_numeric_weights:
                for crit, w in rubric.items():
                    numeric_rubric_weights[str(crit)] = max(1.0, float(w))
                    crit_tokens = _extract_tech_tokens(str(crit).replace("_", " "))
                    crit_overlap = (
                        len(crit_tokens & ans_tokens) / max(1, len(crit_tokens))
                        if crit_tokens
                        else 0.0
                    )
                    # Blend direct criterion terminology match with overall concept attainment
                    achievement = min(1.0, max(concept_ratio, (crit_overlap * 0.45) + (concept_ratio * 0.85)))
                    criteria_achievements[str(crit)] = round(achievement, 3)
            else:
                # Descriptive string rubric (full_credit / partial_credit / zero_credit)
                numeric_rubric_weights = {"technical_accuracy": 60.0, "conceptual_coverage": 40.0}
                criteria_achievements = {
                    "technical_accuracy": min(1.0, cls_acc / 100.0),
                    "conceptual_coverage": concept_ratio,
                }
        else:
            numeric_rubric_weights = {"technical_accuracy": 60.0, "conceptual_coverage": 40.0}
            criteria_achievements = {
                "technical_accuracy": min(1.0, max(concept_ratio, cls_acc / 100.0)),
                "conceptual_coverage": concept_ratio,
            }

        rubric_score = PureScoringEngine.calculate_rubric_score(numeric_rubric_weights, criteria_achievements)

        # Depth & reasoning adjustment so distinct thoroughness levels differentiate cleanly
        has_reasoning = any(
            kw in ans_lower
            for kw in ("because", "therefore", "tradeoff", "trade-off", "whereas", "complexity", "o(", "prevents", "mitigate")
        )
        reasoning_bonus = 6.0 if (has_reasoning and concept_ratio >= 0.35) else 0.0

        combined_score = (rubric_score * 0.55) + (concept_ratio * 100.0 * 0.35) + (cls_acc * 0.10) + reasoning_bonus

        # Enforce wrong/irrelevant upper bound if zero expected concepts were hit and classifier rejected
        if concept_ratio < 0.15 and classification in (CLASS_INCORRECT, "Irrelevant or off-topic", "Unclear or insufficient response"):
            combined_score = min(combined_score, 25.0)
        elif classification == CLASS_INCORRECT and concept_ratio < 0.3:
            combined_score = min(combined_score, 35.0)

        final_score = round(max(0.0, min(100.0, combined_score)), 1)

        # Item-level reliability signal based on response richness & evidence match
        word_count = len(ans_clean.split())
        item_confidence = round(
            min(0.95, 0.45 + min(0.25, word_count / 60.0) + (0.25 if expected_concepts else 0.10) * max(concept_ratio, 0.2)),
            2,
        )

        feedback = (
            f"Demonstrated concepts: {', '.join(demonstrated) if demonstrated else 'None identified'}. "
            f"Growth areas: {', '.join(missed) if missed else 'All core criteria satisfied'}."
        )

        return {
            "score": final_score,
            "confidence": item_confidence,
            "matched_concepts": demonstrated,
            "missed_concepts": missed,
            "rubric_breakdown": criteria_achievements,
            "feedback": feedback,
            "evaluation_status": "evaluated",
            "is_empty": False,
        }

    @classmethod
    def _select_next_skill_and_difficulty(
        cls,
        assessment: Dict[str, Any],
        evaluated_items: List[Dict[str, Any]],
        last_score: float,
        last_difficulty: str = "Intermediate",
        client=None,
        item_scores: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, str]:
        """
        Adaptive Selection Heuristic:
        Prioritizes untested required skills weighted by role importance and category diversity.
        If all required skills have been sampled once, targets the skill with weakest evidence.
        Adapts difficulty upward on strong performance and downward on weak performance.
        """
        role_id = normalize_role_id(assessment.get("target_role", "software_development_engineer"))
        user_id = assessment.get("user_id", "")
        weights = cls._load_role_weights(user_id, role_id, client)

        tested_counts: Dict[str, int] = {}
        tested_domains: Set[str] = set()
        for it in evaluated_items:
            sid = it.get("skill_id")
            if sid:
                tested_counts[sid] = tested_counts.get(sid, 0) + 1
            if it.get("domain"):
                tested_domains.add(it["domain"])

        tested_skill_ids = set(tested_counts.keys())
        untested = [s for s in weights.keys() if s not in tested_skill_ids]

        if untested:
            def _untested_priority(sid: str):
                info = SkillTaxonomyService.get_skill(sid) or {}
                novel_domain_bonus = 0.25 if info.get("category") not in tested_domains else 0.0
                return weights.get(sid, 0.0) + novel_domain_bonus

            untested_sorted = sorted(untested, key=_untested_priority, reverse=True)
            next_skill = untested_sorted[0]
        else:
            # All required skills tested at least once: pick least-sampled / weakest skill
            candidate_skills = list(weights.keys()) or list(tested_skill_ids) or ["dsa_arrays"]
            score_map = item_scores or {}
            next_skill = min(
                candidate_skills,
                key=lambda s: (tested_counts.get(s, 0), score_map.get(s, 50.0), -weights.get(s, 0.0)),
            )

        # Step difficulty smoothly relative to previous turn difficulty & score
        curr_idx = _DIFFICULTY_ORDER.index(last_difficulty) if last_difficulty in _DIFFICULTY_ORDER else 1
        if last_score >= 75.0:
            next_idx = min(2, curr_idx + 1)
        elif last_score < 50.0:
            next_idx = max(0, curr_idx - 1)
        else:
            next_idx = curr_idx

        return next_skill, _DIFFICULTY_ORDER[next_idx]

    @classmethod
    def _update_candidate_skill_state(cls, user_id: str, skill_id: str, score: float, confidence: float, client):
        """Materializes updated candidate skill proficiency state."""
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            curr_res = (
                client.table("candidate_skill_states").select("*").eq("user_id", user_id).eq("skill_id", skill_id).execute()
            )
            if curr_res and curr_res.data:
                curr = curr_res.data[0]
                prev_prof = float(curr.get("proficiency", 0.0))
                samples = int(curr.get("sample_count", 0)) + 1
                new_prof = round((prev_prof * 0.4) + (score * 0.6), 1)
                new_conf = PureScoringEngine.calculate_confidence(samples, concept_diversity=min(4, samples))
                client.table("candidate_skill_states").update({
                    "proficiency": new_prof,
                    "confidence": new_conf,
                    "sample_count": samples,
                    "last_assessed_at": now_iso,
                    "updated_at": now_iso,
                }).eq("user_id", user_id).eq("skill_id", skill_id).execute()
            else:
                init_conf = PureScoringEngine.calculate_confidence(1, concept_diversity=1)
                client.table("candidate_skill_states").insert({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "skill_id": skill_id,
                    "proficiency": score,
                    "confidence": init_conf,
                    "sample_count": 1,
                    "last_assessed_at": now_iso,
                    "updated_at": now_iso,
                }).execute()
        except Exception as e:
            logger.warning(f"Error updating candidate skill state: {e}")

    @classmethod
    def _parse_eval_meta(cls, ev: Dict[str, Any]) -> Tuple[str, Optional[float]]:
        raw_bd = ev.get("rubric_breakdown")
        if isinstance(raw_bd, str):
            try:
                raw_bd = json.loads(raw_bd)
            except Exception:
                raw_bd = {}
        meta = raw_bd.get("_meta", {}) if isinstance(raw_bd, dict) else {}
        status = meta.get("evaluation_status", "evaluated")
        raw_score = ev.get("score")
        if status in ("failed", "pending") or raw_score is None or float(raw_score) < 0.0:
            return status if status in ("failed", "pending") else "failed", None
        return "evaluated", float(raw_score)

    @classmethod
    def _finalize_assessment(
        cls,
        assessment_id: str,
        user_id: str,
        total_budget: int,
        client,
        target_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates deterministic final scorecard strictly separating:
          - overall_score (demonstrated competency over valid evaluated items)
          - confidence (PureScoringEngine statistical confidence)
          - coverage_pct (distinct assessed skills weight / required curriculum weight)
          - completion_pct (valid evaluated items / question_budget)
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        if not target_role:
            try:
                a_res = client.table("assessments").select("target_role").eq("id", assessment_id).execute()
                if a_res and a_res.data:
                    target_role = a_res.data[0].get("target_role")
            except Exception:
                pass
        canonical_role = normalize_role_id(target_role or "software_development_engineer")
        required_weights = cls._load_role_weights(user_id, canonical_role, client)

        items_res = (
            client.table("assessment_items")
            .select("id, skill_id, domain, difficulty, variation_hash, question_text")
            .eq("assessment_id", assessment_id)
            .execute()
        )
        items = items_res.data or []
        item_by_id = {it["id"]: it for it in items}
        item_ids = list(item_by_id.keys())

        evals = []
        if item_ids:
            evals_res = client.table("evaluations").select("*").in_("assessment_item_id", item_ids).execute()
            evals = evals_res.data or []

        valid_evals: List[Dict[str, Any]] = []
        pending_or_failed_count = 0
        valid_scores: List[float] = []
        valid_item_ids: Set[str] = set()

        for ev in evals:
            ev_status, ev_score = cls._parse_eval_meta(ev)
            if ev_status == "evaluated" and ev_score is not None:
                valid_evals.append(ev)
                valid_scores.append(ev_score)
                valid_item_ids.add(ev["assessment_item_id"])
            else:
                pending_or_failed_count += 1

        evaluated_count = len(valid_evals)
        overall_score: Optional[float] = (
            round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else None
        )

        # Distinct questions and skills actually evaluated
        distinct_hashes = {
            (item_by_id[iid].get("variation_hash") or QuestionGenerator.compute_variation_hash(item_by_id[iid].get("question_text", "")))
            for iid in valid_item_ids
            if iid in item_by_id
        }
        distinct_skills = {
            item_by_id[iid]["skill_id"]
            for iid in valid_item_ids
            if iid in item_by_id and item_by_id[iid].get("skill_id")
        }
        distinct_difficulties = {
            item_by_id[iid].get("difficulty")
            for iid in valid_item_ids
            if iid in item_by_id and item_by_id[iid].get("difficulty")
        }

        completion_pct = round((evaluated_count / max(1, total_budget)) * 100.0, 1)
        coverage_pct = PureScoringEngine.calculate_coverage(list(distinct_skills), required_weights)

        # Measurement confidence penalizes low samples, repeated questions, narrow topics, or failed evals
        score_variance = statistics.pvariance(valid_scores) if len(valid_scores) >= 2 else 0.0
        distinct_q_count = len(distinct_hashes)
        uniqueness_ratio = distinct_q_count / max(1, len(items)) if items else 0.0
        reliability_ratio = evaluated_count / max(1, len(evals)) if evals else 0.0
        diff_factor = 0.7 + 0.1 * min(3, len(distinct_difficulties))
        source_quality = max(0.5, min(1.0, diff_factor * uniqueness_ratio * max(0.5, reliability_ratio)))

        measurement_confidence = PureScoringEngine.calculate_confidence(
            sample_count=distinct_q_count,
            concept_diversity=max(1, len(distinct_skills)),
            score_variance=score_variance,
            source_quality=source_quality,
        )

        score_display = f"{overall_score}%" if overall_score is not None else "Pending Evaluation"
        summary_text = (
            f"Adaptive Diagnostic Assessment completed. Demonstrated Competency: {score_display} "
            f"({evaluated_count} evaluated, {pending_or_failed_count} pending). "
            f"Measurement Confidence: {int(round(measurement_confidence * 100))}%. "
            f"Curriculum Coverage: {coverage_pct}% across {len(distinct_skills)} distinct skills."
        )

        client.table("assessments").update({
            "status": "completed" if pending_or_failed_count == 0 else "partial",
            "score": overall_score,
            "completed_questions": evaluated_count,
            "summary": summary_text,
            "completed_at": now_iso,
        }).eq("id", assessment_id).execute()

        try:
            client.table("score_audit_log").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "target_role": canonical_role,
                "calculation_type": "adaptive_diagnostic_final",
                "score_inputs": json.dumps({
                    "evaluated_count": evaluated_count,
                    "pending_or_failed_count": pending_or_failed_count,
                    "distinct_questions": distinct_q_count,
                    "distinct_skills": sorted(distinct_skills),
                    "scores": valid_scores,
                    "completion_pct": completion_pct,
                    "coverage_pct": coverage_pct,
                    "confidence": measurement_confidence,
                }),
                "calculated_score": overall_score if overall_score is not None else 0.0,
                "generated_at": now_iso,
            }).execute()
        except Exception:
            pass

        return {
            "status": "COMPLETED",
            "assessment_id": assessment_id,
            "overall_score": overall_score,
            "confidence": measurement_confidence,
            "coverage_pct": coverage_pct,
            "completion_pct": completion_pct,
            "evaluated_count": evaluated_count,
            "pending_or_failed_count": pending_or_failed_count,
            "distinct_skills_count": len(distinct_skills),
            "distinct_questions_count": distinct_q_count,
            "summary": summary_text,
            "progress": {
                "answered": evaluated_count,
                "total": total_budget,
            },
        }

    @classmethod
    def resume_session(cls, assessment_id: str, user_id: str, supabase_client=None) -> Dict[str, Any]:
        """Resumes an in-progress assessment following page reload."""
        client = supabase_client or get_supabase_client()
        ass_res = client.table("assessments").select("*").eq("id", assessment_id).eq("user_id", user_id).execute()
        if not ass_res or not ass_res.data:
            raise ValueError(f"Assessment {assessment_id} not found")
        assessment = ass_res.data[0]

        items_res = (
            client.table("assessment_items").select("*").eq("assessment_id", assessment_id).order("created_at", desc=False).execute()
        )
        items = items_res.data or []

        answered_count = int(assessment.get("completed_questions", 0))
        total_budget = int(assessment.get("total_questions", cls.DEFAULT_QUESTION_BUDGET))
        current_item = items[answered_count] if answered_count < len(items) else None

        return {
            "assessment_id": assessment_id,
            "status": assessment.get("status", "IN_PROGRESS"),
            "target_role": assessment.get("target_role"),
            "answered": answered_count,
            "total": total_budget,
            "current_question": QuestionGenerator.sanitize_for_client(current_item) if current_item else None,
        }

    @classmethod
    def _build_turn_response(cls, assessment, items, turn_index, eval_record, client):
        total_budget = int(assessment.get("total_questions", cls.DEFAULT_QUESTION_BUDGET))
        ev_status, ev_score = cls._parse_eval_meta(eval_record)
        if turn_index >= total_budget:
            return {
                "status": "COMPLETED",
                "assessment_id": assessment["id"],
                "overall_score": assessment.get("score"),
                "summary": assessment.get("summary"),
            }
        next_item = items[turn_index] if turn_index < len(items) else None
        return {
            "status": "IN_PROGRESS",
            "turn_index": turn_index + 1,
            "evaluation": {
                "score": ev_score,
                "evaluation_status": ev_status,
                "confidence": eval_record.get("confidence"),
                "cached": True,
            },
            "next_question": QuestionGenerator.sanitize_for_client(next_item) if next_item else None,
            "progress": {"answered": turn_index, "total": total_budget},
        }
