"""
PREPFLY DIAGNOSTIC ENGINE (Section 4)
=====================================
Adaptive Computerized Testing and Grading Pipeline:
- 4.1 Format: Adaptive, covers MANDATORY skills first, then PREFERRED, then SUPPORTING.
- 4.2 Adaptive algorithm (deterministic):
    Starting difficulty: JUNIOR=EASY, MID=MEDIUM, SENIOR=MEDIUM, STAFF=HARD.
    Score >= 75 -> step up; 40-74 -> stay; < 40 -> step down.
    Stop skill when >= 2 graded answers across >= 2 different subskills.
    Never ask same subskill twice in row. Never repeat question ID.
- 4.3 Grading:
    MCQ: deterministic.
    SHORT_ANSWER/SCENARIO/CODE: temperature 0 rubric evaluation via Prompt 12.3.
    Code computes numbers: Score = Σ(points awarded) / Σ(rubric points) * 100.
    Dual-run variance check: if scores differ by > 15, run third time and take median.
    Blank / < 10 chars: score 0, attempted=false, SKIPPED, never weakness evidence.
- 4.4 Result Screen ("Calibrated Competency & Readiness Profile"):
    Single source of truth scoring via scoring_engine.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone
import json
import uuid
import re
import os
import logging

from schemas.spec_schemas import (
    QuestionLLMOutputSchema,
    QuestionRubricItemSchema,
    GraderLLMOutputSchema,
    GraderItemResultSchema
)
from services.scoring_engine import (
    calculate_skill_proficiency,
    calculate_skill_confidence,
    classify_skill_status,
    calculate_readiness,
    aggregate_pillar,
    analyze_skill_gaps,
    build_unified_readiness_object
)
from services.onboarding_service import OnboardingService
from utils.template_guard import sanitize_user_facing_string
from local_supabase import get_supabase_client

logger = logging.getLogger("prepfly.diagnostic_engine")

STARTING_DIFFICULTY_BY_LEVEL = {
    "JUNIOR": "EASY",
    "MID": "MEDIUM",
    "SENIOR": "MEDIUM",
    "STAFF": "HARD"
}

DIFFICULTY_STEPS = ["EASY", "MEDIUM", "HARD"]

# Curated High-Fidelity Question Bank Covering Core AI/ML Engineering & General SDE Skills
CURATED_DIAGNOSTIC_QUESTIONS = [
    # ── Python for ML ──────────────────────────────────────────────────────────
    {
        "id": "q_py_vec_01",
        "skillId": "python_ml",
        "subskillId": "vectorisation",
        "difficulty": "EASY",
        "type": "SHORT_ANSWER",
        "prompt": "Explain why vectorised operations in NumPy execute substantially faster than standard Python loops when processing numerical arrays.",
        "rubric": [
            {"id": "r1", "criterion": "Mentions execution in compiled C/Fortran code bypassing Python bytecode evaluation", "points": 40},
            {"id": "r2", "criterion": "Mentions contiguous memory layout enabling CPU cache spatial locality", "points": 35},
            {"id": "r3", "criterion": "Mentions SIMD (Single Instruction, Multiple Data) CPU vector hardware registers", "points": 25}
        ],
        "modelAnswer": "NumPy vectorised operations run in pre-compiled C/Fortran routines, eliminating dynamic Python type-checking and bytecode overhead. Arrays are stored in contiguous memory blocks, maximizing CPU cache locality and enabling SIMD parallel instructions.",
        "timeLimitSec": 180
    },
    {
        "id": "q_py_broad_02",
        "skillId": "python_ml",
        "subskillId": "broadcasting",
        "difficulty": "MEDIUM",
        "type": "SHORT_ANSWER",
        "prompt": "State the two conditions required for two NumPy arrays to be broadcast-compatible when performing element-wise operations.",
        "rubric": [
            {"id": "r1", "criterion": "Mentions dimensions are compared element-wise starting from trailing (rightmost) dimensions backward", "points": 40},
            {"id": "r2", "criterion": "States dimensions are compatible if they are equal", "points": 30},
            {"id": "r3", "criterion": "States dimensions are compatible if one of them is equal to 1", "points": 30}
        ],
        "modelAnswer": "When operating on two arrays, NumPy compares their shapes element-wise starting from the trailing (rightmost) dimensions. Two dimensions are compatible when: 1. They are equal, or 2. One of them is 1.",
        "timeLimitSec": 180
    },
    {
        "id": "q_py_mem_03",
        "skillId": "python_ml",
        "subskillId": "memory_management",
        "difficulty": "HARD",
        "type": "SHORT_ANSWER",
        "prompt": "How does NumPy differentiate between array slices that create a 'view' versus those that create an explicit memory 'copy', and how does this impact memory consumption in large-scale dataset preprocessing?",
        "rubric": [
            {"id": "r1", "criterion": "Explains that basic slicing (start:stop:step) creates a view sharing the underlying data buffer with modified strides", "points": 40},
            {"id": "r2", "criterion": "Explains that advanced indexing (boolean masks, integer array indexing) always creates a new memory copy", "points": 35},
            {"id": "r3", "criterion": "Highlights memory impact: large parent arrays cannot be garbage collected if small views remain referenced", "points": 25}
        ],
        "modelAnswer": "Basic slicing creates a view that shares the original data buffer by adjusting metadata (strides, shape, offset) without allocating new memory. Advanced indexing (integer arrays, boolean masks) allocates an independent copy. Retaining a tiny view of a multi-gigabyte array prevents the parent memory buffer from being freed by the garbage collector.",
        "timeLimitSec": 240
    },

    # ── Supervised Learning & Regularization ───────────────────────────────────
    {
        "id": "q_sl_reg_01",
        "skillId": "supervised_learning",
        "subskillId": "bias_variance",
        "difficulty": "EASY",
        "type": "MCQ",
        "prompt": "Which diagnostic observation typically indicates that a supervised machine learning model is suffering from high variance (overfitting)?",
        "options": [
            "High training loss and similarly high validation loss",
            "Near-zero training loss but significantly higher validation loss",
            "Low training loss and low validation loss with simple linear decision boundaries",
            "Constant prediction output across all input samples"
        ],
        "correctOptions": [1],
        "rubric": [
            {"id": "r1", "criterion": "Correctly identifies large divergence between near-zero training loss and high validation loss", "points": 100}
        ],
        "modelAnswer": "Near-zero training loss but significantly higher validation loss indicates the model has memorized training noise and fails to generalize.",
        "timeLimitSec": 120
    },
    {
        "id": "q_sl_reg_02",
        "skillId": "supervised_learning",
        "subskillId": "l1_l2_regularization",
        "difficulty": "MEDIUM",
        "type": "SHORT_ANSWER",
        "prompt": "Why does L1 (Lasso) regularization induce sparse weight vectors (driving coefficients exactly to zero), whereas L2 (Ridge) regularization only shrinks coefficients toward zero without setting them to zero?",
        "rubric": [
            {"id": "r1", "criterion": "Contrasts diamond/rhombus L1 contour geometry having sharp corners on coordinate axes with smooth circular/spherical L2 hypersphere", "points": 50},
            {"id": "r2", "criterion": "Explains that unconstrained loss contours intersect L1 constraints at coordinate corners where parameters equal zero", "points": 50}
        ],
        "modelAnswer": "The L1 penalty constraint boundary is a diamond/hyper-octahedron with sharp corners aligned directly along the coordinate axes. When the elliptical contours of the objective function expand, they are geometrically most likely to first touch the L1 boundary at a corner, driving coordinates exactly to 0. L2 constraints form smooth hyperspheres where tangent intersections rarely occur at exactly 0.",
        "timeLimitSec": 180
    },

    # ── Model Evaluation & Imbalanced Metrics ──────────────────────────────────
    {
        "id": "q_me_eval_01",
        "skillId": "model_eval",
        "subskillId": "precision_recall",
        "difficulty": "MEDIUM",
        "type": "SHORT_ANSWER",
        "prompt": "In a medical diagnostic screening model for a rare life-threatening disease with 99.8% negative patients, why is classification accuracy a misleading metric, and which metric should be prioritized?",
        "rubric": [
            {"id": "r1", "criterion": "Explains accuracy paradox: a trivial dummy classifier predicting negative for all patients achieves 99.8% accuracy but detects zero cases", "points": 50},
            {"id": "r2", "criterion": "Identifies Recall (Sensitivity) as the critical priority to minimize false negatives, along with Precision/PR-AUC", "points": 50}
        ],
        "modelAnswer": "Accuracy is misleading because a trivial model predicting negative for 100% of samples achieves 99.8% accuracy while missing every sick patient. Recall (Sensitivity) must be prioritized to minimize lethal False Negatives, complemented by Precision and PR-AUC.",
        "timeLimitSec": 180
    },
    {
        "id": "q_me_eval_02",
        "skillId": "model_eval",
        "subskillId": "roc_auc",
        "difficulty": "HARD",
        "type": "SHORT_ANSWER",
        "prompt": "Explain the key mathematical difference between ROC-AUC and PR-AUC, and specify under which class distribution PR-AUC provides more diagnostic value.",
        "rubric": [
            {"id": "r1", "criterion": "States ROC plots True Positive Rate vs False Positive Rate (FPR), where FPR denominator includes True Negatives", "points": 40},
            {"id": "r2", "criterion": "States PR plots Precision vs Recall, neither of which includes True Negatives in the denominator", "points": 35},
            {"id": "r3", "criterion": "Concludes PR-AUC is far more informative in severe class imbalance because massive True Negatives artificially deflate FPR in ROC", "points": 25}
        ],
        "modelAnswer": "ROC curves plot True Positive Rate against False Positive Rate (FP / (FP + TN)). Under extreme class imbalance, a vast number of True Negatives dilutes the denominator, keeping FPR deceptively small even with many False Positives. Precision-Recall curves omit True Negatives entirely, making PR-AUC directly sensitive to False Positives and far more informative for imbalanced detection.",
        "timeLimitSec": 240
    },

    # ── Transformer Architecture & Self-Attention ──────────────────────────────
    {
        "id": "q_tr_att_01",
        "skillId": "transformers",
        "subskillId": "multi_head_attention",
        "difficulty": "MEDIUM",
        "type": "SHORT_ANSWER",
        "prompt": "Write the mathematical equation for Scaled Dot-Product Attention as introduced by Vaswani et al., and explain the purpose of dividing by sqrt(d_k).",
        "rubric": [
            {"id": "r1", "criterion": "States Attention(Q, K, V) = softmax(Q * K^T / sqrt(d_k)) * V", "points": 50},
            {"id": "r2", "criterion": "Explains that for large d_k, dot products grow large in magnitude, pushing softmax into regions of vanishingly small gradients", "points": 50}
        ],
        "modelAnswer": "Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V. Scaling by sqrt(d_k) counteracts dot-product variance growth: without scaling, large embedding dimensions cause dot products to grow large, pushing the softmax function into regions with extremely small gradients.",
        "timeLimitSec": 180
    },
    {
        "id": "q_tr_att_02",
        "skillId": "transformers",
        "subskillId": "positional_encoding",
        "difficulty": "HARD",
        "type": "SHORT_ANSWER",
        "prompt": "Why do vanilla Transformer architectures require explicit Positional Encodings, whereas Recurrent Neural Networks (RNNs) do not?",
        "rubric": [
            {"id": "r1", "criterion": "Explains that Self-Attention is permutation invariant with respect to input token order", "points": 50},
            {"id": "r2", "criterion": "Explains that RNNs process sequences iteratively step-by-step, inherently encoding sequential order in their hidden state recurrence", "points": 50}
        ],
        "modelAnswer": "Self-attention operations are entirely permutation-invariant: scrambling input token positions yields identical attention outputs without positional markers. RNNs process input tokens sequentially one step at a time, so token order is naturally encoded through temporal recurrence.",
        "timeLimitSec": 180
    },

    # ── ML System Design & Feature Stores ──────────────────────────────────────
    {
        "id": "q_sys_ml_01",
        "skillId": "ml_system_design",
        "subskillId": "feature_stores",
        "difficulty": "MEDIUM",
        "type": "SCENARIO",
        "prompt": "You are designing an ML system for real-time fraud detection requiring p99 inference latency under 20ms. Describe how a Feature Store prevents training-serving skew between historical training batches and real-time inference.",
        "rubric": [
            {"id": "r1", "criterion": "Explains dual-storage architecture: low-latency key-value store (Redis/DynamoDB) for online serving and warehouse/lakehouse (Parquet/Snowflake) for offline training", "points": 50},
            {"id": "r2", "criterion": "Explains unified feature transformation definitions preventing discrepancy between Python training scripts and online pipeline transformations", "points": 50}
        ],
        "modelAnswer": "A feature store enforces a single unified definition for feature transformations used across both offline training and online serving. It synchronizes an offline store (data warehouse) for point-in-time correct batch training with a low-latency online key-value store (e.g. Redis) for real-time serving, eliminating training-serving skew.",
        "timeLimitSec": 240
    },

    # ── General SDE: Arrays & Strings ──────────────────────────────────────────
    {
        "id": "q_dsa_arr_01",
        "skillId": "dsa_arrays_strings",
        "subskillId": "sliding_window",
        "difficulty": "EASY",
        "type": "SHORT_ANSWER",
        "prompt": "When is the Sliding Window pattern preferred over brute-force O(N^2) nested loops when finding optimal sub-arrays satisfying a monotonic property?",
        "rubric": [
            {"id": "r1", "criterion": "Explains that sliding window expands right and contracts left, achieving O(N) linear time complexity", "points": 50},
            {"id": "r2", "criterion": "Mentions maintaining running window state without recomputing overlapping sub-array sums from scratch", "points": 50}
        ],
        "modelAnswer": "The sliding window pattern avoids re-scanning overlapping elements by maintaining a running state (e.g. sum, frequency map) as the right pointer expands and left pointer contracts, reducing time complexity from O(N^2) to O(N).",
        "timeLimitSec": 180
    }
]


class DiagnosticEngine:
    """
    Manages adaptive diagnostic session progression, deterministic grading,
    variance control, and the Section 4 result summary.
    """

    _ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_curated_questions(cls) -> List[Dict[str, Any]]:
        return CURATED_DIAGNOSTIC_QUESTIONS

    @classmethod
    def start_diagnostic_session(
        cls,
        user_id: str,
        kind: str = "DIAGNOSTIC",
        target_role: str = "AI/ML Engineer",
        target_skills: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Initializes an adaptive diagnostic session (Section 4.1 & 4.2):
        - Starting difficulty based on user level: JUNIOR=EASY, MID=MEDIUM, SENIOR=MEDIUM, STAFF=HARD
        - Prioritizes unassessed MANDATORY skills first, then PREFERRED, then SUPPORTING
        - Returns session state + the first question
        """
        clean_uid = str(user_id or "user_default").strip()
        session_id = f"diag_{uuid.uuid4().hex[:12]}"

        # Resolve candidate role profile skills
        if not target_skills:
            prof = OnboardingService._PROFILE_CACHE.get(clean_uid)
            if prof and prof.get("skills_profile", {}).get("skills"):
                target_skills = prof["skills_profile"]["skills"]
            else:
                target_skills = OnboardingService.generate_skill_requirement_profile(
                    company="Target Company",
                    role=target_role,
                    level="MID"
                ).get("skills", [])

        user_level = "MID"
        prof = OnboardingService._PROFILE_CACHE.get(clean_uid)
        if prof and prof.get("level"):
            user_level = prof["level"]

        start_diff = STARTING_DIFFICULTY_BY_LEVEL.get(user_level, "MEDIUM")

        # Session State
        session_state = {
            "session_id": session_id,
            "user_id": clean_uid,
            "kind": kind,
            "target_role": target_role,
            "user_level": user_level,
            "starting_difficulty": start_diff,
            "skills_profile": target_skills,
            "current_difficulty_by_skill": {sk.get("id") or sk.get("skill_id"): start_diff for sk in target_skills},
            "theta_by_skill": {sk.get("id") or sk.get("skill_id"): 50.0 for sk in target_skills},
            "graded_answers_by_skill": {sk.get("id") or sk.get("skill_id"): [] for sk in target_skills},
            "subskills_tested_by_skill": {sk.get("id") or sk.get("skill_id"): set() for sk in target_skills},
            "asked_question_ids": [],
            "last_subskill_asked": None,
            "answers_history": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_completed": False
        }

        # Select first question
        first_q = cls.select_next_question(session_state)
        if first_q:
            session_state["asked_question_ids"].append(first_q["id"])
            session_state["last_subskill_asked"] = first_q.get("subskillId")

        cls._ACTIVE_SESSIONS[session_id] = session_state

        return {
            "status": "success",
            "session_id": session_id,
            "kind": kind,
            "target_role": target_role,
            "total_questions_cap": 15,
            "current_question_index": 1,
            "first_question": first_q
        }

    @classmethod
    def select_next_question(cls, session_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Deterministic Adaptive Question Selection (Section 4.2):
        1. Stop if global cap reached (15 questions).
        2. Filter skills that have not yet achieved stopping criteria:
           (< 2 graded answers across < 2 different subskills).
        3. Priority order: MANDATORY (highest importance first), then PREFERRED, then SUPPORTING.
        4. Select question matching target skill at its current adaptive difficulty.
        5. Never ask the same subskill twice in a row. Never repeat a question ID.
        """
        asked_ids = set(session_state.get("asked_question_ids", []))
        if len(asked_ids) >= 15:
            return None

        skills = session_state.get("skills_profile", [])
        last_subskill = session_state.get("last_subskill_asked")

        # Sort candidate skills by tier priority, then importance descending
        def _tier_rank(tier: str) -> int:
            t = str(tier).upper()
            if t == "MANDATORY": return 0
            if t == "PREFERRED": return 1
            return 2

        sorted_skills = sorted(
            skills,
            key=lambda x: (
                _tier_rank(x.get("tier", "PREFERRED")),
                -float(x.get("interviewImportance", x.get("importance", 3)) or 3)
            )
        )

        all_curated = cls.get_curated_questions()

        for sk in sorted_skills:
            sk_id = sk.get("id") or sk.get("skill_id")
            tested_subskills = session_state.get("subskills_tested_by_skill", {}).get(sk_id, set())
            graded_count = len(session_state.get("graded_answers_by_skill", {}).get(sk_id, []))

            # Stop asking if >= 2 graded answers across >= 2 different subskills
            if graded_count >= 2 and len(tested_subskills) >= 2:
                continue

            target_diff = session_state.get("current_difficulty_by_skill", {}).get(sk_id, "MEDIUM")

            # Find matching question in pool
            candidates = [
                q for q in all_curated
                if q["skillId"] == sk_id
                and q["id"] not in asked_ids
                and q.get("subskillId") != last_subskill
            ]

            if not candidates:
                # Try relaxed candidate match (ignore subskill repeat constraint if no alternative)
                candidates = [
                    q for q in all_curated
                    if q["skillId"] == sk_id and q["id"] not in asked_ids
                ]

            if not candidates:
                # Allow fallback across all unasked curated questions for this skill
                continue

            # Prioritize matching target difficulty
            best_match = next((q for q in candidates if q.get("difficulty") == target_diff), candidates[0])
            return best_match

        # If all skills satisfy condition or pool exhausted, return first available unasked question
        remaining = [q for q in all_curated if q["id"] not in asked_ids]
        return remaining[0] if remaining else None

    @classmethod
    def grade_answer(
        cls,
        question: Dict[str, Any],
        answer_text: Optional[str] = None,
        selected_options: Optional[List[int]] = None,
        candidate_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministic Grading Pipeline (Section 4.3):
        - Blank or < 10 characters -> score 0, attempted=false, SKIPPED (not weakness evidence).
        - MCQ -> deterministic auto-grade.
        - SHORT_ANSWER / SCENARIO -> temperature 0 rubric evaluation.
          Score = Σ(points awarded) / Σ(points) * 100 computed by code.
        - Dual-run variance check for open-ended answers.
        """
        raw_ans = (answer_text or "").strip()
        q_type = str(question.get("type", "SHORT_ANSWER")).upper()

        # Blank or < 10 characters check
        if q_type != "MCQ" and len(raw_ans) < 10:
            return {
                "score": 0.0,
                "is_attempted": False,
                "status": "SKIPPED",
                "feedback": "Answer was omitted or shorter than 10 characters. Excluded from skill gap evidence.",
                "rubric_results": [],
                "failed_rubrics": []
            }

        rubric_items = question.get("rubric", [])
        total_possible_points = sum(r.get("points", 25) for r in rubric_items)
        if total_possible_points <= 0:
            total_possible_points = 100

        # 1. MCQ Grading
        if q_type == "MCQ":
            correct_opts = set(question.get("correctOptions") or [])
            cand_opts = set(selected_options or [])
            if not cand_opts and raw_ans:
                try:
                    cand_opts = {int(raw_ans)}
                except ValueError:
                    pass

            is_correct = (cand_opts == correct_opts) and len(cand_opts) > 0
            score = 100.0 if is_correct else 0.0
            crit = rubric_items[0].get("criterion", "Selected incorrect option") if rubric_items else "Selected incorrect option"
            return {
                "score": score,
                "is_attempted": True,
                "status": "GRADED",
                "feedback": "Correct option selected." if is_correct else "Incorrect option selected.",
                "rubric_results": [
                    {
                        "rubricId": rubric_items[0]["id"] if rubric_items else "r1",
                        "result": "PASS" if is_correct else "FAIL",
                        "pointsAwarded": int(score),
                        "evidence": f"Selected options {list(cand_opts)}"
                    }
                ],
                "failed_rubrics": [] if is_correct else [crit]
            }

        # 2. SHORT_ANSWER / SCENARIO / CODE Rubric Grading
        grader_run_1 = cls._evaluate_rubric_with_llm(question, raw_ans, rubric_items)
        score_1, failed_1 = cls._compute_rubric_score_and_failures(grader_run_1, rubric_items)

        # Dual-run check: run second time
        grader_run_2 = cls._evaluate_rubric_with_llm(question, raw_ans, rubric_items)
        score_2, failed_2 = cls._compute_rubric_score_and_failures(grader_run_2, rubric_items)

        if abs(score_1 - score_2) > 15.0:
            # Variance exceeds 15 points: run third time and take median
            grader_run_3 = cls._evaluate_rubric_with_llm(question, raw_ans, rubric_items)
            score_3, failed_3 = cls._compute_rubric_score_and_failures(grader_run_3, rubric_items)
            sorted_scores = sorted([score_1, score_2, score_3])
            final_score = sorted_scores[1]  # median
            final_results = grader_run_2 if final_score == score_2 else (grader_run_1 if final_score == score_1 else grader_run_3)
            final_failed = failed_2 if final_score == score_2 else (failed_1 if final_score == score_1 else failed_3)
        else:
            final_score = round((score_1 + score_2) / 2.0, 1)
            final_results = grader_run_1
            final_failed = failed_1

        return {
            "score": float(final_score),
            "is_attempted": True,
            "status": "GRADED",
            "feedback": f"Scored {final_score}% against {len(rubric_items)} structured rubric criteria.",
            "rubric_results": final_results,
            "failed_rubrics": final_failed
        }

    @classmethod
    def _evaluate_rubric_with_llm(
        cls,
        question: Dict[str, Any],
        answer_text: str,
        rubric_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Executes Prompt 12.3 at temperature 0.
        Falls back to deterministic keyword/subsequence heuristic matcher in test mode.
        """
        if os.getenv("ENVIRONMENT") == "test" or os.getenv("FLASK_ENV") == "test":
            return cls._heuristic_rubric_grader(answer_text, rubric_items)

        prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "12_3_grader.txt")
        system_instruction = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_instruction = f.read().strip()

        user_content = (
            f"Question: {question.get('prompt')}\n"
            f"Model Answer: {question.get('modelAnswer')}\n"
            f"Candidate Answer: {answer_text}\n"
            f"Rubric: {json.dumps(rubric_items)}\n"
        )

        try:
            from services.ai_service import safe_invoke_llm, create_gemini_client, GEMINI_DEFAULT_PRIMARY_MODEL
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_INTERVIEW_KEY") or ""
            model = create_gemini_client(GEMINI_DEFAULT_PRIMARY_MODEL, api_key, temperature=0.0) if api_key else None
            if model:
                resp = safe_invoke_llm(model, f"{system_instruction}\n\n{user_content}")
                if resp:
                    raw_text = resp if isinstance(resp, str) else getattr(resp, "content", "")
                    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        validated = GraderLLMOutputSchema(**parsed)
                        return [item.model_dump() for item in validated.items]
        except Exception as e:
            logger.warning(f"LLM Grader fallback notice: {e}")

        return cls._heuristic_rubric_grader(answer_text, rubric_items)

    @classmethod
    def _heuristic_rubric_grader(
        cls,
        answer_text: str,
        rubric_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deterministic, transparent semantic heuristic grader used in tests and offline environments.
        """
        ans_low = answer_text.lower()
        results = []

        for r in rubric_items:
            rid = r.get("id")
            pts = int(r.get("points", 25))
            crit = r.get("criterion", "").lower()
            crit_words = [w for w in re.findall(r"\w+", crit) if len(w) > 3]

            # Match keyword overlap
            matched_words = [w for w in crit_words if w in ans_low]
            match_ratio = (len(matched_words) / len(crit_words)) if crit_words else 1.0

            if match_ratio >= 0.5:
                awarded = pts
                outcome = "PASS"
                ev = f"Matched keywords: {', '.join(matched_words[:3])}"
            elif match_ratio >= 0.25:
                awarded = pts // 2
                outcome = "PARTIAL"
                ev = f"Partial mention: {', '.join(matched_words[:2])}"
            else:
                awarded = 0
                outcome = "FAIL"
                ev = "none"

            results.append({
                "rubricId": rid,
                "result": outcome,
                "pointsAwarded": awarded,
                "evidence": ev
            })

        return results

    @classmethod
    def _compute_rubric_score_and_failures(
        cls,
        grader_items: List[Dict[str, Any]],
        rubric_items: List[Dict[str, Any]]
    ) -> Tuple[float, List[str]]:
        """
        Golden Rule 1: Code computes the score from per-item results.
        Score = Σ(pointsAwarded) / Σ(item.points) * 100.
        """
        rubric_map = {r["id"]: r for r in rubric_items}
        total_possible = sum(r.get("points", 25) for r in rubric_items)
        total_awarded = 0
        failed_rubrics = []

        for item in grader_items:
            rid = item.get("rubricId")
            r_meta = rubric_map.get(rid)
            awarded = int(item.get("pointsAwarded", 0))
            total_awarded += awarded

            if item.get("result") == "FAIL":
                if r_meta and r_meta.get("criterion"):
                    failed_rubrics.append(r_meta["criterion"])
                else:
                    failed_rubrics.append(f"Rubric {rid} criterion failed")

        score = (float(total_awarded) / float(total_possible) * 100.0) if total_possible > 0 else 0.0
        return (round(min(100.0, max(0.0, score)), 1), failed_rubrics)

    @classmethod
    def submit_diagnostic_answer(
        cls,
        session_id: str,
        question_id: str,
        answer_text: str,
        selected_options: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Submits answer, updates adaptive state, adjusts skill difficulty,
        and returns grade + next question.
        """
        session = cls._ACTIVE_SESSIONS.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        # Find question metadata
        all_q = cls.get_curated_questions()
        q_meta = next((q for q in all_q if q["id"] == question_id), None)
        if not q_meta:
            q_meta = {
                "id": question_id,
                "skillId": "python_ml",
                "subskillId": "vectorisation",
                "difficulty": "MEDIUM",
                "type": "SHORT_ANSWER",
                "rubric": [{"id": "r1", "criterion": "Core understanding", "points": 100}],
                "modelAnswer": "Comprehensive technical answer"
            }

        # Grade
        grade_res = cls.grade_answer(q_meta, answer_text, selected_options)
        score = grade_res["score"]
        is_attempted = grade_res["is_attempted"]

        sk_id = q_meta["skillId"]
        sub_id = q_meta.get("subskillId")

        # Update Session Adaptive State if attempted
        if is_attempted:
            if sk_id not in session["graded_answers_by_skill"]:
                session["graded_answers_by_skill"][sk_id] = []
            session["graded_answers_by_skill"][sk_id].append(score)

            if sub_id:
                if sk_id not in session["subskills_tested_by_skill"]:
                    session["subskills_tested_by_skill"][sk_id] = set()
                session["subskills_tested_by_skill"][sk_id].add(sub_id)

            # Dynamic difficulty step for this skill (Section 4.2)
            curr_diff = session["current_difficulty_by_skill"].get(sk_id, "MEDIUM")
            curr_idx = DIFFICULTY_STEPS.index(curr_diff)
            if score >= 75.0 and curr_idx < len(DIFFICULTY_STEPS) - 1:
                session["current_difficulty_by_skill"][sk_id] = DIFFICULTY_STEPS[curr_idx + 1]
            elif score < 40.0 and curr_idx > 0:
                session["current_difficulty_by_skill"][sk_id] = DIFFICULTY_STEPS[curr_idx - 1]

        # Record answer history
        answer_record = {
            "question_id": question_id,
            "skill_id": sk_id,
            "subskill_id": sub_id,
            "difficulty": q_meta.get("difficulty"),
            "score": score,
            "is_attempted": is_attempted,
            "failed_rubrics": grade_res["failed_rubrics"],
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        session["answers_history"].append(answer_record)

        # Select next question
        next_q = cls.select_next_question(session)
        if next_q:
            session["asked_question_ids"].append(next_q["id"])
            session["last_subskill_asked"] = next_q.get("subskillId")
        else:
            session["is_completed"] = True

        return {
            "status": "success",
            "session_id": session_id,
            "question_id": question_id,
            "score": score,
            "grade_result": grade_res,
            "next_question": next_q,
            "is_completed": next_q is None
        }

    @classmethod
    def finish_diagnostic_session(cls, session_id: str) -> Dict[str, Any]:
        """
        Completes diagnostic session and constructs the Calibrated Competency & Readiness Profile
        result screen payload complying with Section 4.4 and Section 5 single source of truth.
        """
        session = cls._ACTIVE_SESSIONS.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        session["is_completed"] = True

        # Assemble skills with attempted evidence
        skills_profile = session.get("skills_profile", [])
        evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        failed_rubrics_by_skill: Dict[str, List[str]] = {}

        for ans in session.get("answers_history", []):
            if not ans.get("is_attempted"):
                continue  # Exclude skipped / < 10 char answers from evidence
            sk_id = ans["skill_id"]
            if sk_id not in evidence_by_skill:
                evidence_by_skill[sk_id] = []
                failed_rubrics_by_skill[sk_id] = []

            evidence_by_skill[sk_id].append({
                "score": ans["score"],
                "age_in_days": 0.0,
                "difficulty": ans["difficulty"],
                "evidence_type": "SHORT_ANSWER",
                "is_attempted": True
            })
            failed_rubrics_by_skill[sk_id].extend(ans.get("failed_rubrics", []))

        skills_data = []
        for sk in skills_profile:
            sk_id = sk.get("id") or sk.get("skill_id")
            ev_list = evidence_by_skill.get(sk_id, [])
            sub_tested = session.get("subskills_tested_by_skill", {}).get(sk_id, set())

            skills_data.append({
                "skill_id": sk_id,
                "name": sk.get("name"),
                "pillar": sk.get("pillar") or "Core Technical",
                "tier": sk.get("tier", "PREFERRED"),
                "importance": sk.get("interviewImportance", sk.get("importance", 3)),
                "total_subskills_count": len(sk.get("subskills", [])) or 3,
                "evidence": ev_list,
                "subskills_tested": sub_tested,
                "failed_rubrics": failed_rubrics_by_skill.get(sk_id, [])
            })

        # Single source of truth calculation via scoring engine
        unified = build_unified_readiness_object(
            skills_data=skills_data,
            target_role=session.get("target_role", "AI/ML Engineer")
        )

        readiness = unified["readiness"]
        assessed_count = readiness["assessed_skills_count"]
        total_skills = readiness["total_skills_count"]
        unassessed_count = total_skills - assessed_count

        total_questions_asked = len(session.get("asked_question_ids", []))
        total_answered = len(session.get("answers_history", []))
        completion_pct = round((total_answered / max(1, total_questions_asked)) * 100.0, 1)

        # Mandatory Section 4.4 summary sentence:
        summary_sentence = (
            f"You were assessed on {assessed_count} of {total_skills} skills. "
            f"{unassessed_count} skills are not yet assessed and are not counted as weaknesses."
        )

        return {
            "status": "success",
            "session_id": session_id,
            "target_role": session.get("target_role"),
            "demonstrated_competency_pct": readiness["verified_score"],
            "measurement_confidence_pct": round(readiness["weighted_coverage"] * 100.0, 1),
            "curriculum_coverage_pct": round(readiness["weighted_coverage"] * 100.0, 1),
            "assessment_completion_pct": completion_pct,
            "summary_sentence": summary_sentence,
            "readiness": readiness,
            "pillars": unified["pillars"],
            "skills_map": unified["skills_map"],
            "gap_analysis": unified["gap_analysis"]
        }

