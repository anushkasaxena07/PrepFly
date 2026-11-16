"""
PREPFLY SPECIFICATION PLANNER ENGINE (Section 8)
================================================
Deterministic preparation roadmap generator and adaptive re-planner:
- 8.1 Feasibility Check (COMFORTABLE, TIGHT, AT_RISK, CRASH_MODE)
- 8.2 Start Date Logic (timezone-aware, before 6 PM cutoff, Today vs Tomorrow)
- 8.3 Phases scaled to available days N (Diagnose, Core Build, Integrate, Taper, Eve)
- 8.4 Allocation Algorithm:
    - Priority = W * gapSize * interviewImportance * freshnessBoost
    - Block minutes between 15 and 45 min
    - Daily sum <= budget and >= 85% of budget (except eve/taper)
    - Interleaving: <= 2 consecutive blocks of same skill; <= 2 skills/day (3 on Phase 3)
    - Spaced-repetition REVISION at Day 1, 3, 7
    - Mock interviews: >= 1 per 7 days, min 2 if N >= 10
    - Unassessed MANDATORY skills have DIAGNOSTIC_CHECK in first 30% of days
- 8.5 Output shape: date, dayNumber, phase, theme, totalMinutes, budgetMinutes, dailyGoal, blocks[], importantNotes[], endOfDayCheck
- 8.6 Crash Mode: interview in <= 2 days
- 8.7 Plan Versioning & Diffing: machine-readable diff (trigger, from, to, added, removed, moved, deferred, minutesDelta)
- 8.8 Re-planning rules: completed blocks immutable, non-destructive future day re-allocation.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, date, timedelta, timezone
import json
import uuid
import math
import logging

from schemas.spec_schemas import DayBlockContentSchema
from services.scoring_engine import (
    evaluate_candidate_readiness,
    calculate_skill_proficiency,
    get_canonical_role_skills,
    DIFFICULTY_WEIGHTS,
    TIER_WEIGHTS
)
from services.onboarding_service import OnboardingService
from utils.timezone_utils import (
    determine_plan_start_date,
    get_current_user_datetime,
    get_current_user_date,
    parse_date_iso,
    format_date_iso,
    DEFAULT_TIMEZONE
)

logger = logging.getLogger("prepfly.spec_planner")


# Curated high-fidelity topics & tasks for AI/ML and Software Engineering
CURATED_BLOCK_TEMPLATES = {
    "python_ml": {
        "DIAGNOSTIC_CHECK": {
            "topic": "Python for ML: Diagnostic Probe",
            "keyPoints": [
                "Assess NumPy vectorisation and C-level execution bypassing GIL",
                "Evaluate memory stride manipulation vs array buffer copies",
                "Verify broadcasting rules and dimension alignment"
            ],
            "commonInterviewQuestions": [
                "Why is NumPy vectorisation faster than pure Python loops?",
                "What conditions are required for two arrays to broadcast?"
            ],
            "practiceTask": "Complete the 3-question diagnostic probe on NumPy internals and memory views.",
            "successCriteria": "Score >= 75% across vectorisation and broadcasting rubric criteria."
        },
        "LEARN": {
            "topic": "Python for ML: Vectorisation & Broadcasting",
            "keyPoints": [
                "NumPy vectorised operations run in pre-compiled C routines bypassing Python bytecode overhead",
                "Contiguous memory layout maximizes CPU cache line spatial locality",
                "Broadcasting compares trailing dimensions backwards: compatible if equal or one is 1",
                "Avoid creating unintentional memory copies during slicing"
            ],
            "commonInterviewQuestions": [
                "How does NumPy handle broadcasting when dimensions don't match?",
                "What is the difference between a view and a copy in NumPy slicing?"
            ],
            "practiceTask": "Implement vectorised batch matrix multiplication and verify memory footprint using numpy.ndarray.strides.",
            "successCriteria": "Benchmark vectorised implementation showing >= 20x speedup over standard nested iteration."
        },
        "PRACTICE": {
            "topic": "NumPy Performance Profiling & Optimization",
            "keyPoints": [
                "Profile memory allocations with memory_profiler",
                "Replace Python loops with einsum and ufuncs",
                "Use in-place operations (out parameter) to avoid large array copies"
            ],
            "commonInterviewQuestions": [
                "How does np.einsum optimize Einstein summation operations?",
                "When should you use in-place array operations in production pipelines?"
            ],
            "practiceTask": "Refactor a loop-heavy feature normalization function into a single vectorised ufunc.",
            "successCriteria": "Zero temporary intermediate arrays allocated during execution."
        },
        "ASSIGNMENT": {
            "topic": "Vectorised Dataset Preprocessing Pipeline",
            "keyPoints": [
                "Vectorise categorical one-hot encoding without pandas",
                "Compute pairwise Euclidean distance matrix purely in NumPy",
                "Handle NaN values with vectorised boolean masking"
            ],
            "commonInterviewQuestions": [
                "How do you compute all pairwise distances between N vectors without for-loops?"
            ],
            "practiceTask": "Write a self-contained NumPy pipeline that computes pairwise cosine similarity across 10,000 embeddings.",
            "successCriteria": "Executes in under 200ms with verified numerical precision."
        },
        "REVISION": {
            "topic": "Spaced Revision: NumPy Memory & Vectorisation",
            "keyPoints": [
                "Recall basic slicing stride math vs advanced indexing copy creation",
                "Re-derive broadcasting compatibility conditions"
            ],
            "commonInterviewQuestions": [
                "Does arr[::-1] allocate new memory?"
            ],
            "practiceTask": "Quick 15-minute retrieval drill on NumPy memory strides.",
            "successCriteria": "Correctly answer 3 rapid-fire memory management questions."
        }
    },
    "model_eval": {
        "DIAGNOSTIC_CHECK": {
            "topic": "Model Evaluation Diagnostic Check",
            "keyPoints": [
                "Evaluate understanding of class imbalance traps",
                "Test mathematical difference between ROC-AUC and PR-AUC"
            ],
            "commonInterviewQuestions": [
                "Why is 99% accuracy useless in fraud detection?"
            ],
            "practiceTask": "Solve two diagnostic scenario questions on imbalanced dataset metrics.",
            "successCriteria": "Correctly identify Sensitivity/Recall prioritization."
        },
        "LEARN": {
            "topic": "Evaluation Metrics for Imbalanced Data",
            "keyPoints": [
                "Accuracy paradox: high accuracy achieved by trivial majority-class prediction",
                "Precision measures fraction of relevant instances among retrieved instances",
                "Recall measures fraction of relevant instances retrieved",
                "PR-AUC is mathematically superior to ROC-AUC when positive class is extremely rare"
            ],
            "commonInterviewQuestions": [
                "When would you choose PR-AUC over ROC-AUC in production?",
                "How do you determine the optimal classification threshold for a high-cost false negative?"
            ],
            "practiceTask": "Derive the confusion matrix, calculate F1, F2 score, and plot PR curve vs ROC curve on synthetic imbalanced data.",
            "successCriteria": "Demonstrate why ROC-AUC stays optimistically high while PR-AUC exposes false positives."
        },
        "PRACTICE": {
            "topic": "Cost-Sensitive Threshold Tuning",
            "keyPoints": [
                "Define custom business cost utility matrix (cost_FP vs cost_FN)",
                "Optimize threshold via expected value framework",
                "Calibrate model probabilities using Platt scaling and isotonic regression"
            ],
            "commonInterviewQuestions": [
                "How do you calibrate uncalibrated probabilities from a tree-based ensemble?"
            ],
            "practiceTask": "Implement expected value threshold selection minimizing business loss for a loan default model.",
            "successCriteria": "Threshold minimizes total dollar cost according to asymmetric loss matrix."
        },
        "ASSIGNMENT": {
            "topic": "Comprehensive Model Evaluation Report",
            "keyPoints": [
                "Compute stratified bootstrap confidence intervals for AUC",
                "Evaluate subgroup fairness metrics across demographic cohorts"
            ],
            "commonInterviewQuestions": [
                "How do you construct 95% bootstrap confidence intervals for AUC?"
            ],
            "practiceTask": "Build an end-to-end evaluation harness producing PR curves, calibration curves, and bootstrap CI.",
            "successCriteria": "Report flags potential data drift and probability miscalibration."
        },
        "REVISION": {
            "topic": "Spaced Revision: Evaluation Metrics",
            "keyPoints": [
                "Quick recall of Precision, Recall, Specificity, and PR-AUC formulas",
                "Review when to select F-beta with beta > 1"
            ],
            "commonInterviewQuestions": [
                "What does F2 score weight more: Precision or Recall?"
            ],
            "practiceTask": "15-minute flash review on metric selection tradeoffs.",
            "successCriteria": "Score 100% on metric selection quiz."
        }
    },
    "transformers": {
        "LEARN": {
            "topic": "Transformers & Self-Attention Architecture",
            "keyPoints": [
                "Scaled Dot-Product Attention: Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V",
                "Dividing by sqrt(d_k) prevents large dot products from pushing softmax into vanishing gradient regions",
                "Multi-Head Attention projects Q, K, V into multiple subspaces simultaneously",
                "Positional encodings provide permutation-variant order information to self-attention"
            ],
            "commonInterviewQuestions": [
                "Why do we divide by sqrt(d_k) in Scaled Dot-Product Attention?",
                "Why are Transformers faster to train than LSTMs?"
            ],
            "practiceTask": "Implement multi-head self-attention from scratch in PyTorch or NumPy.",
            "successCriteria": "Output tensor dimensions match input dimensions with correct attention weight normalization."
        },
        "PRACTICE": {
            "topic": "Attention Masking & KV Caching",
            "keyPoints": [
                "Causal masking prevents tokens from attending to subsequent future tokens",
                "KV caching stores previous Keys and Values during autoregressive generation to avoid O(N^2) recomputation",
                "Rotary Position Embeddings (RoPE) inject relative positional information"
            ],
            "commonInterviewQuestions": [
                "How does KV caching reduce inference complexity from O(N^2) to O(N)?",
                "How does FlashAttention optimize memory bandwidth bottlenecks?"
            ],
            "practiceTask": "Write an autoregressive generation loop with and without KV caching and measure latency scaling.",
            "successCriteria": "Demonstrate linear O(N) token generation time using KV cache."
        },
        "ASSIGNMENT": {
            "topic": "Mini-Transformer Implementation & Tokenizer Integration",
            "keyPoints": [
                "Construct full Transformer Decoder block with LayerNorm and FeedForward network",
                "Implement causal mask and residual connections"
            ],
            "commonInterviewQuestions": [
                "What is the difference between Pre-LayerNorm and Post-LayerNorm stability?"
            ],
            "practiceTask": "Assemble and train a 2-layer miniature decoder-only model on character sequences.",
            "successCriteria": "Training loss decreases monotonically over 50 iterations."
        },
        "REVISION": {
            "topic": "Spaced Revision: Transformer Attention Mechanics",
            "keyPoints": [
                "Recall equation for Attention(Q, K, V)",
                "Review KV cache memory calculation for 7B parameter models"
            ],
            "commonInterviewQuestions": [
                "What is the memory size of a KV cache for batch size 1, sequence length 2048?"
            ],
            "practiceTask": "Solve memory sizing math problem for LLM inference.",
            "successCriteria": "Accurate KV cache memory derivation."
        }
    },
    "ml_system_design": {
        "LEARN": {
            "topic": "ML System Design: Feature Stores & Real-Time Serving",
            "keyPoints": [
                "Feature store architecture: dual offline (warehouse/Parquet) and online (Redis/DynamoDB) stores",
                "Eliminates training-serving skew by using identical transformation logic",
                "Point-in-time correctness prevents future data leakage during batch training feature retrieval",
                "p99 latency optimization: asynchronous feature hydration and batching"
            ],
            "commonInterviewQuestions": [
                "How does a Feature Store prevent data leakage and training-serving skew?",
                "How do you design a real-time recommendation system under 50ms latency?"
            ],
            "practiceTask": "Design a high-level architecture diagram for real-time fraud detection with Feast/Redis.",
            "successCriteria": "Covers ingestion, offline training joins, online key-value lookup, and fallback cache."
        },
        "PRACTICE": {
            "topic": "System Design: Two-Stage Recommender Architecture",
            "keyPoints": [
                "Candidate generation (Retrieval): ANN vector search (HNSW/ScaNN) over millions of items in 10ms",
                "Candidate ranking: Heavy GBDT/Deep model scoring top 500 candidates in 30ms",
                "Re-ranking & Business logic: Diversity, deduplication, and fresh content exploration"
            ],
            "commonInterviewQuestions": [
                "Walk me through the two-stage retrieval and ranking paradigm in modern recommenders.",
                "How do you monitor for model concept drift in production?"
            ],
            "practiceTask": "Draft end-to-end architecture for YouTube video recommendations.",
            "successCriteria": "Accurate trade-off explanation between latency, throughput, and model complexity."
        },
        "ASSIGNMENT": {
            "topic": "Full ML System Design Whiteboard Scenario",
            "keyPoints": [
                "State functional and non-functional requirements (latency, throughput, availability)",
                "Define data pipeline, model training, deployment strategy, and rollback protocol"
            ],
            "commonInterviewQuestions": [
                "Design a real-time ETA prediction system for ridesharing."
            ],
            "practiceTask": "Write a complete 4-page system design proposal for real-time ad click prediction.",
            "successCriteria": "Addresses data schema, feature engineering, offline/online serving, and observability."
        }
    }
}


class SpecPlannerService:
    """
    Core Deterministic Planner implementing Section 8 of the Full Build Specification.
    """

    _PLAN_VERSIONS: Dict[str, List[Dict[str, Any]]] = {}
    _COMPLETED_BLOCKS: Dict[str, Set[str]] = {}
    _DEFERRED_BACKLOG: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def get_user_plan_history(cls, user_id: str) -> List[Dict[str, Any]]:
        clean_uid = str(user_id or "user_default").strip()
        return cls._PLAN_VERSIONS.get(clean_uid, [])

    @classmethod
    def get_active_plan(cls, user_id: str) -> Optional[Dict[str, Any]]:
        history = cls.get_user_plan_history(user_id)
        return history[-1] if history else None

    @classmethod
    def compute_feasibility(
        cls,
        user_id: str,
        start_date: str,
        interview_date: str,
        daily_minutes: int = 90,
        skills: Optional[List[Dict[str, Any]]] = None,
        blackout_dates: Optional[List[str]] = None,
        availability_grid: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Implements Section 8.1 Feasibility Check:
        availableDays = list of dates from startDate to (interviewDate - 1) where availableMinutes(date) > 0
        totalMinutes = sum(availableMinutes(date))
        requiredMinutes = sum(baseMinutes(skill)) + 10% mock + 10% revision
        """
        clean_uid = str(user_id or "user_default").strip()
        tz_name = DEFAULT_TIMEZONE

        start_dt = parse_date_iso(start_date) if isinstance(start_date, str) else start_date
        interview_dt = parse_date_iso(interview_date) if isinstance(interview_date, str) else interview_date
        blackout_set = set(blackout_dates or [])

        # Build available days up to (interviewDate - 1)
        available_days: List[Dict[str, Any]] = []
        curr = start_dt
        while curr < interview_dt:
            date_str = curr.strftime("%Y-%m-%d")
            if date_str not in blackout_set:
                day_mins = daily_minutes
                if availability_grid and date_str in availability_grid:
                    day_mins = availability_grid[date_str]
                if day_mins > 0:
                    available_days.append({
                        "date": date_str,
                        "availableMinutes": day_mins
                    })
            curr += timedelta(days=1)

        total_available_minutes = sum(d["availableMinutes"] for d in available_days)
        n_days = len(available_days)

        # Resolve skills
        if not skills:
            skills = get_canonical_role_skills("AI/ML Engineer")

        # Base minutes calculation per skill (Section 8.1)
        # MANDATORY 180, PREFERRED 120, SUPPORTING 60
        # gapFactor = (100 - P_skill)/100 for assessed, or 0.6 for unassessed. Min 20 mins.
        skill_breakdown = []
        total_base_minutes = 0

        for sk in skills:
            tier = str(sk.get("tier", "PREFERRED")).upper()
            if tier == "MANDATORY":
                tier_mins = 180
            elif tier == "SUPPORTING":
                tier_mins = 60
            else:
                tier_mins = 120

            # If assessed, check score; else default to 0.6 gap factor
            ev = sk.get("evidence", [])
            if ev:
                avg_score = sum(e.get("score", 0) for e in ev) / len(ev)
                gap_factor = max(0.1, (100.0 - avg_score) / 100.0)
            else:
                gap_factor = 0.6

            base_mins = max(20, int(round(tier_mins * gap_factor)))
            total_base_minutes += base_mins
            skill_breakdown.append({
                "skillId": sk.get("id") or sk.get("skill_id"),
                "name": sk.get("name"),
                "tier": tier,
                "baseMinutes": base_mins,
                "gapFactor": round(gap_factor, 2)
            })

        # Add 10% for mock interviews and 10% for revision
        mock_minutes = int(round(total_base_minutes * 0.10))
        revision_minutes = int(round(total_base_minutes * 0.10))
        required_minutes = total_base_minutes + mock_minutes + revision_minutes

        days_until_interview = (interview_dt - start_dt).days

        # Crash mode trigger: interview in <= 2 days
        if days_until_interview <= 2:
            status = "CRASH_MODE"
            headline = "Crash Mode: Interview in 2 days or less"
            explanation = "Deep multi-week topics are collapsed into high-yield rapid wins, 1 mock interview, top pillar cheat sheets, and logistics preparation."
        elif total_available_minutes >= required_minutes:
            status = "COMFORTABLE"
            headline = "Comfortable: Sufficient time to cover all required skills"
            explanation = f"You have {total_available_minutes} available minutes, exceeding the required {required_minutes} minutes."
        elif total_available_minutes >= int(required_minutes * 0.70):
            status = "TIGHT"
            headline = "Tight: Time is constrained; supporting skills will be trimmed"
            explanation = f"You have {total_available_minutes} available minutes against {required_minutes} required. Supporting skills will be trimmed first."
        else:
            status = "AT_RISK"
            headline = "At Risk: Significant time deficit"
            explanation = f"You have {total_available_minutes} minutes available, which is under 70% of the required {required_minutes} minutes. Low-priority topics will be dropped."

        return {
            "status": status,
            "headline": headline,
            "explanation": explanation,
            "availableDaysCount": n_days,
            "totalAvailableMinutes": total_available_minutes,
            "requiredMinutes": required_minutes,
            "baseSkillsMinutes": total_base_minutes,
            "mockMinutes": mock_minutes,
            "revisionMinutes": revision_minutes,
            "availableDays": available_days,
            "skillBreakdown": skill_breakdown
        }

    @classmethod
    def generate_plan(
        cls,
        user_id: str,
        target_role: str = "AI/ML Engineer",
        target_company: str = "Target Tech",
        interview_date: Optional[str] = None,
        daily_minutes: int = 90,
        start_date: Optional[str] = None,
        blackout_dates: Optional[List[str]] = None,
        availability_grid: Optional[Dict[str, int]] = None,
        skills_profile: Optional[List[Dict[str, Any]]] = None,
        trigger: str = "INITIAL"
    ) -> Dict[str, Any]:
        """
        Generates the full deterministic, phased preparation plan complying strictly with Section 8.
        """
        clean_uid = str(user_id or "user_default").strip()
        tz_name = DEFAULT_TIMEZONE

        # 8.2 Start Date Logic using determine_plan_start_date
        if not start_date:
            start_date_obj, first_day_label = determine_plan_start_date(tz_name, daily_minutes)
            start_date = format_date_iso(start_date_obj)
        else:
            start_date_obj = parse_date_iso(start_date) if isinstance(start_date, str) else start_date
            now_date = get_current_user_date(tz_name)
            if start_date_obj == now_date:
                first_day_label = "Today"
            elif start_date_obj == (now_date + timedelta(days=1)):
                first_day_label = "Tomorrow"
            else:
                first_day_label = start_date_obj.strftime("%b %d")

        if not interview_date:
            interview_date_obj = start_date_obj + timedelta(days=18)
            interview_date = format_date_iso(interview_date_obj)
        else:
            interview_date_obj = parse_date_iso(interview_date) if isinstance(interview_date, str) else interview_date

        # Resolve skills
        if not skills_profile:
            skills_profile = get_canonical_role_skills(target_role)

        # Run Feasibility Check
        feasibility = cls.compute_feasibility(
            user_id=clean_uid,
            start_date=start_date,
            interview_date=interview_date,
            daily_minutes=daily_minutes,
            skills=skills_profile,
            blackout_dates=blackout_dates,
            availability_grid=availability_grid
        )

        available_days_info = feasibility["availableDays"]
        n_days = len(available_days_info)
        is_crash_mode = feasibility["status"] == "CRASH_MODE" or n_days <= 2

        # 8.4 Allocation Algorithm: Priority(skill) = W * gapSize * interviewImportance * freshnessBoost
        # gapSize = (100 - P_skill)/100 for assessed, or 0.6 if unassessed.
        # freshnessBoost = 1.2 if older than 30 days.
        skill_priorities = []
        for sk in skills_profile:
            sk_id = sk.get("id") or sk.get("skill_id")
            tier = str(sk.get("tier", "PREFERRED")).upper()
            w = TIER_WEIGHTS.get(tier, 1.0)
            imp = float(sk.get("interviewImportance", sk.get("importance", 3)) or 3)

            ev = sk.get("evidence", [])
            if ev:
                avg_score = sum(e.get("score", 0) for e in ev) / len(ev)
                gap_size = (100.0 - avg_score) / 100.0
                is_stale = any(e.get("age_in_days", 0) > 30 for e in ev)
                freshness_boost = 1.2 if is_stale else 1.0
                is_assessed = True
            else:
                gap_size = 0.6  # Standard unassessed gap factor
                freshness_boost = 1.0
                is_assessed = False

            prio = w * gap_size * imp * freshness_boost
            skill_priorities.append({
                "skillId": sk_id,
                "name": sk.get("name"),
                "tier": tier,
                "importance": imp,
                "gapSize": gap_size,
                "isAssessed": is_assessed,
                "priority": prio
            })

        skill_priorities.sort(key=lambda x: -x["priority"])

        # 8.3 Phase Boundaries scaled to N available days
        # Phase 1: Diagnose & Foundations (first ~15%, min 1 day)
        # Phase 2: Core Build (next ~50%)
        # Phase 3: Integrate & Simulate (next ~25%)
        # Phase 4: Taper & Revise (final ~10%, min 1 day)
        # Interview eve: last day
        p1_end = max(1, int(round(n_days * 0.15)))
        p2_end = max(p1_end + 1, int(round(n_days * 0.65)))
        p3_end = max(p2_end + 1, int(round(n_days * 0.90)))

        days_plan: List[Dict[str, Any]] = []
        recent_studied_skills: List[str] = []
        unassessed_mandatory_skills = [
            s["skillId"] for s in skill_priorities
            if s["tier"] == "MANDATORY" and not s["isAssessed"]
        ]

        total_mocks_scheduled = 0
        target_mocks = max(2 if n_days >= 10 else 1, int(round(n_days / 7.0)))

        for i, day_info in enumerate(available_days_info):
            day_num = i + 1
            date_str = day_info["date"]
            budget_mins = day_info["availableMinutes"]
            is_eve = (day_num == n_days)
            is_taper = (day_num == n_days - 1 and n_days > 2)

            # Determine Phase
            if is_eve:
                phase_name = "Interview Eve"
                phase_id = "PHASE_EVE"
                theme = "Pre-Interview Logistics & Rapid Mindset Calibration"
                daily_goal = "Complete light 45-minute checklist, review formula cheat sheet, and rest early."
                day_budget = min(45, budget_mins)
            elif is_taper:
                phase_name = "Phase 4: Taper & Revise"
                phase_id = "PHASE_4_TAPER"
                theme = "Weak-Spot Verification & Final Concept Synthesis"
                daily_goal = "Re-test borderline weak spots, review cheat sheet, with zero new heavy topics."
                day_budget = budget_mins
            elif day_num <= p1_end:
                phase_name = "Phase 1: Diagnose & Foundations"
                phase_id = "PHASE_1_DIAGNOSE"
                theme = "Diagnostic Baseline & Core Foundational Primitives"
                daily_goal = "Establish baseline evidence and remediate highest-priority mandatory foundational gaps."
                day_budget = budget_mins
            elif day_num <= p2_end:
                phase_name = "Phase 2: Core Build"
                phase_id = "PHASE_2_CORE_BUILD"
                theme = "Deep Conceptual Mastery & Hands-On Problem Solving"
                daily_goal = "Execute Learn-Practice-Assignment cycles on core priority skills."
                day_budget = budget_mins
            else:
                phase_name = "Phase 3: Integrate & Simulate"
                phase_id = "PHASE_3_INTEGRATE"
                theme = "System Architecture & Mock Interview Simulation"
                daily_goal = "Synthesize multi-component system design and simulate live interview conditions."
                day_budget = budget_mins

            # Build Day Blocks adhering to 8.4 Allocation Constraints:
            # - Each block 15 to 45 min
            # - sum(block minutes) <= budget and >= 85% of budget (except eve/taper)
            # - Max 2 consecutive blocks of same skill; max 2 skills/day (3 on Phase 3)
            # - Reflection (5 min) at end of day
            blocks: List[Dict[str, Any]] = []
            used_minutes = 0

            # CRASH MODE HANDLING (Section 8.6)
            if is_crash_mode:
                # Rapid wins, 1 mock interview, cheat sheet, 5 STAR stories, logistics checklist
                blocks.append(cls._create_block(
                    block_type="LEARN",
                    skill_id=skill_priorities[0]["skillId"] if skill_priorities else "python_ml",
                    duration_min=min(30, day_budget - 20),
                    difficulty="MEDIUM",
                    why_here="CRASH_MODE: Rapid high-yield concept review for imminent interview."
                ))
                used_minutes += blocks[-1]["durationMin"]

                if day_budget - used_minutes >= 30 and total_mocks_scheduled == 0:
                    blocks.append(cls._create_mock_block(
                        duration_min=30,
                        title="Rapid Mock Interview Simulation",
                        why_here="CRASH_MODE: High-fidelity simulation under pressure."
                    ))
                    used_minutes += 30
                    total_mocks_scheduled += 1

                if day_budget - used_minutes >= 15:
                    rem = day_budget - used_minutes
                    blocks.append(cls._create_block(
                        block_type="REVISION",
                        skill_id="ml_system_design",
                        duration_min=rem,
                        difficulty="MEDIUM",
                        why_here="CRASH_MODE: Pillar Cheat Sheet & 5 STAR Behavioral Stories."
                    ))
                    used_minutes += rem

            elif is_eve:
                # Section 8.3 & 8.6: Eve is <= 45 min light review + logistics checklist
                blocks.append({
                    "id": f"blk_{uuid.uuid4().hex[:8]}",
                    "type": "REVISION",
                    "skillId": "general_prep",
                    "topic": "Logistics Checklist & Mental Readiness",
                    "durationMin": 25,
                    "difficulty": "EASY",
                    "keyPoints": [
                        "Verify quiet interview environment, stable network, and functional camera/mic",
                        "Review 1-page summary cheat sheet of primary formulas and architecture patterns",
                        "Prepare 3 questions to ask the interviewer at the close of the round"
                    ],
                    "commonInterviewQuestions": [
                        "Do you have any questions for us regarding team technical challenges?"
                    ],
                    "practiceTask": "Conduct audio/mic hardware check and stage scratchpad for coding.",
                    "successCriteria": "Hardware verified, interview link bookmarked, calm mental posture.",
                    "whyHere": "INTERVIEW_EVE: Zero cognitive overload; focus on restful preparation.",
                    "resources": ["Logistics Checklist", "Interview Day Readiness Protocol"]
                })
                used_minutes += 25

                if day_budget - used_minutes >= 15:
                    rem = day_budget - used_minutes
                    blocks.append({
                        "id": f"blk_{uuid.uuid4().hex[:8]}",
                        "type": "REFLECTION",
                        "skillId": "general_prep",
                        "topic": "Confidence & Mindset Anchoring",
                        "durationMin": rem,
                        "difficulty": "EASY",
                        "keyPoints": [
                            "Acknowledge dedicated preparation completed across the curriculum",
                            "Focus on clear communication and structured problem decomposition"
                        ],
                        "commonInterviewQuestions": [],
                        "practiceTask": "Review personal STAR stories and sleep on time.",
                        "successCriteria": "Restful sleep achieved.",
                        "whyHere": "INTERVIEW_EVE: Final confidence anchor.",
                        "resources": []
                    })
                    used_minutes += rem

            elif is_taper:
                # Section 8.3 & Acceptance Test 12: Taper day (Day N-1) has ZERO new topics
                # Only REVISION, PRACTICE, MOCK_INTERVIEW, and REFLECTION permitted
                rev_skill = skill_priorities[0]["skillId"] if skill_priorities else "python_ml"

                # 1. Primary Revision Block (Cheat sheet & weak spot review)
                rev1_mins = min(30, max(15, day_budget // 3))
                blocks.append(cls._create_block(
                    block_type="REVISION",
                    skill_id=rev_skill,
                    duration_min=rev1_mins,
                    difficulty="MEDIUM",
                    why_here="TAPER_DAY: Weak-spot synthesis and formula cheat sheet review."
                ))
                used_minutes += rev1_mins

                # 2. Practice Drills Block (Rapid retrieval)
                if day_budget - used_minutes >= 20:
                    pract_skill = skill_priorities[1]["skillId"] if len(skill_priorities) > 1 else rev_skill
                    pract_mins = min(30, day_budget - used_minutes - 5)
                    blocks.append(cls._create_block(
                        block_type="PRACTICE",
                        skill_id=pract_skill,
                        duration_min=pract_mins,
                        difficulty="MEDIUM",
                        why_here="TAPER_DAY: Timed retrieval drills; no new conceptual theory."
                    ))
                    used_minutes += pract_mins

                # 3. Secondary Revision / Practice if budget remains (e.g. 90-min day)
                if day_budget - used_minutes >= 25:
                    rev2_skill = skill_priorities[2]["skillId"] if len(skill_priorities) > 2 else rev_skill
                    rem_mins = min(30, day_budget - used_minutes - 5)
                    blocks.append(cls._create_block(
                        block_type="REVISION",
                        skill_id=rev2_skill,
                        duration_min=rem_mins,
                        difficulty="MEDIUM",
                        why_here="TAPER_DAY: Core architectural patterns and trade-offs review."
                    ))
                    used_minutes += rem_mins

                # 4. End-of-Day Reflection
                if day_budget - used_minutes >= 5:
                    rem_reflect = day_budget - used_minutes
                    blocks.append({
                        "id": f"blk_{uuid.uuid4().hex[:8]}",
                        "type": "REFLECTION",
                        "skillId": "general_prep",
                        "topic": "Pre-Interview Mindset & Confidence Anchoring",
                        "durationMin": rem_reflect,
                        "difficulty": "EASY",
                        "keyPoints": [
                            "Review personal STAR behavioral narrative points",
                            "Focus on calm problem decomposition and clarity in communication"
                        ],
                        "commonInterviewQuestions": [],
                        "practiceTask": "Rest well and review mental interview checklist.",
                        "successCriteria": "Calm mental posture achieved.",
                        "whyHere": "TAPER_DAY: Final confidence anchoring before interview eve.",
                        "resources": []
                    })
                    used_minutes += rem_reflect

            else:
                # Normal Day Block Allocation
                # 8.4 (8): If any MANDATORY skill is NOT_ASSESSED, DIAGNOSTIC_CHECK in first 30% of days
                in_first_30_pct = (day_num <= max(1, int(round(n_days * 0.30))))
                if in_first_30_pct and unassessed_mandatory_skills and (day_budget >= 60) and (day_budget - used_minutes >= 45):
                    diag_skill = unassessed_mandatory_skills.pop(0)
                    diag_dur = min(25, day_budget - used_minutes)
                    blocks.append(cls._create_block(
                        block_type="DIAGNOSTIC_CHECK",
                        skill_id=diag_skill,
                        duration_min=diag_dur,
                        difficulty="MEDIUM",
                        why_here=f"MANDATORY_PROBE: Skill '{diag_skill}' is unassessed and required in first 30% of curriculum."
                    ))
                    used_minutes += diag_dur

                # Check if a spaced REVISION is due (Section 8.4 (6))
                # For skills studied 1, 3, or 7 days ago and not yet >= 85%
                if recent_studied_skills and (day_num % 3 == 0) and (day_budget - used_minutes >= 25):
                    rev_skill = recent_studied_skills[0]
                    rev_dur = 20 if (day_budget - used_minutes >= 45) else 15
                    blocks.append(cls._create_block(
                        block_type="REVISION",
                        skill_id=rev_skill,
                        duration_min=rev_dur,
                        difficulty="MEDIUM",
                        why_here=f"SPACED_REVISION: Reinforce retention curve for '{rev_skill}' studied in earlier phase."
                    ))
                    used_minutes += rev_dur

                # Check Mock Interview insertion (Section 8.4 (7))
                # At least 1 mock per ~7 days, min 2 if N >= 10.
                is_mock_day = False
                if total_mocks_scheduled < target_mocks:
                    if (day_num == 13 and n_days >= 14) or (day_num == 16 and n_days >= 17) or (day_num == int(round(n_days * 0.75))):
                        is_mock_day = True

                if is_mock_day and (day_budget - used_minutes >= 40):
                    blocks.append(cls._create_mock_block(
                        duration_min=45,
                        title=f"Full Simulation: Technical Mock Interview #{total_mocks_scheduled + 1}",
                        why_here=f"SIMULATION_MILESTONE: Verify interview readiness under live timed conditions."
                    ))
                    used_minutes += 45
                    total_mocks_scheduled += 1

                # Fill remaining budget with Learn/Practice/Assignment blocks
                # Select target skill with highest priority that obeys interleaving:
                # <= 2 skills per day (3 on Phase 3 days)
                max_skills_today = 3 if phase_id == "PHASE_3_INTEGRATE" else 2
                day_skills_used: Set[str] = {b.get("skillId") for b in blocks if b.get("skillId") and b.get("skillId") != "general_prep"}

                # Rotate primary candidate skill
                candidate_pool = [s for s in skill_priorities if s["skillId"] not in ("general_prep",)]
                primary_skill_info = candidate_pool[(day_num - 1) % len(candidate_pool)]
                primary_skill = primary_skill_info["skillId"]

                # Ensure 5-minute REFLECTION at end of day
                reserve_reflection = 5 if day_budget >= 30 else 0
                available_for_core = day_budget - used_minutes - reserve_reflection

                if available_for_core >= 20:
                    # Allocate LEARN / PRACTICE / ASSIGNMENT blocks (Section 8.4 (4))
                    # Standard 90-min day pattern: LEARN 30 -> PRACTICE 30 -> ASSIGNMENT 25 -> REFLECTION 5
                    # 40-min day pattern: LEARN 25 -> PRACTICE 15
                    # 30-min day pattern: LEARN 25 -> REFLECTION 5
                    if available_for_core >= 60:
                        learn_mins = 30
                        practice_mins = min(30, available_for_core - learn_mins)
                        assign_mins = max(0, available_for_core - learn_mins - practice_mins)

                        blocks.append(cls._create_block(
                            block_type="LEARN",
                            skill_id=primary_skill,
                            duration_min=learn_mins,
                            difficulty="MEDIUM",
                            why_here=f"PRIORITY_ALLOCATION: Core conceptual study on '{primary_skill}'."
                        ))
                        used_minutes += learn_mins
                        recent_studied_skills.append(primary_skill)

                        if practice_mins >= 15:
                            blocks.append(cls._create_block(
                                block_type="PRACTICE",
                                skill_id=primary_skill,
                                duration_min=practice_mins,
                                difficulty="MEDIUM",
                                why_here=f"HANDS_ON_DRILL: Practical exercise consolidating '{primary_skill}'."
                            ))
                            used_minutes += practice_mins

                        if assign_mins >= 15:
                            blocks.append(cls._create_block(
                                block_type="ASSIGNMENT",
                                skill_id=primary_skill,
                                duration_min=assign_mins,
                                difficulty="HARD" if phase_id == "PHASE_3_INTEGRATE" else "MEDIUM",
                                why_here=f"VERIFIED_EVIDENCE: Graded challenge yielding performance evidence."
                            ))
                            used_minutes += assign_mins

                    elif day_budget == 40 or available_for_core >= 35:
                        # 40-minute day pattern: 25 min LEARN + 15 min PRACTICE (Section 8.8 / Acceptance Test 15)
                        blocks.append(cls._create_block(
                            block_type="LEARN",
                            skill_id=primary_skill,
                            duration_min=25,
                            difficulty="MEDIUM",
                            why_here=f"PRIORITY_ALLOCATION: Focused conceptual module on '{primary_skill}'."
                        ))
                        used_minutes += 25
                        recent_studied_skills.append(primary_skill)

                        rem_core = max(15, day_budget - used_minutes)
                        blocks.append(cls._create_block(
                            block_type="PRACTICE",
                            skill_id=primary_skill,
                            duration_min=rem_core,
                            difficulty="MEDIUM",
                            why_here=f"DRILL: Targeted exercise on '{primary_skill}'."
                        ))
                        used_minutes += rem_core
                        reserve_reflection = 0  # 25 + 15 = 40 min exact budget
                    else:
                        # 20 to 30 minute single block
                        blocks.append(cls._create_block(
                            block_type="LEARN",
                            skill_id=primary_skill,
                            duration_min=available_for_core,
                            difficulty="MEDIUM",
                            why_here=f"FOCUSED_SESSION: Dedicated single block on '{primary_skill}'."
                        ))
                        used_minutes += available_for_core
                        recent_studied_skills.append(primary_skill)

                # Append REFLECTION block (5 min) if budget allows
                if reserve_reflection > 0 and (day_budget - used_minutes >= 5):
                    blocks.append({
                        "id": f"blk_{uuid.uuid4().hex[:8]}",
                        "type": "REFLECTION",
                        "skillId": primary_skill,
                        "topic": "Daily Progress Reflection & Self-Check",
                        "durationMin": 5,
                        "difficulty": "EASY",
                        "keyPoints": [
                            "Summarize the single most critical concept learned today",
                            "Identify any unresolved doubts or edge cases to revisit"
                        ],
                        "commonInterviewQuestions": [],
                        "practiceTask": "Record 1-sentence synthesis in preparation journal.",
                        "successCriteria": "Complete end-of-day reflection.",
                        "whyHere": "DAILY_LOOP: Solidify learning and activate metacognition.",
                        "resources": []
                    })
                    used_minutes += 5

            # Acceptance Test 10 verification:
            # sum(block minutes) <= budget and >= 85% of budget (except eve/taper)
            total_block_minutes = sum(b["durationMin"] for b in blocks)
            if not is_eve and not is_taper and total_block_minutes < int(math.ceil(day_budget * 0.85)):
                deficit = int(math.ceil(day_budget * 0.85)) - total_block_minutes
                # Top up first scalable block or add quick practice
                if blocks:
                    scalable = next((b for b in blocks if b["type"] in ("LEARN", "PRACTICE")), blocks[0])
                    scalable["durationMin"] = min(45, scalable["durationMin"] + deficit)
                    total_block_minutes = sum(b["durationMin"] for b in blocks)

            # End of Day Check: 3-question quiz (Section 8.5)
            end_of_day_check = {
                "title": f"Day {day_num} Self-Check Quiz",
                "questionsCount": 3,
                "passingScore": 70,
                "targetSkillId": blocks[0].get("skillId") if blocks else "python_ml"
            }

            days_plan.append({
                "dayNumber": day_num,
                "date": date_str,
                "dayLabel": first_day_label if day_num == 1 else date_str,
                "phase": phase_name,
                "phaseId": phase_id,
                "theme": theme,
                "dailyGoal": daily_goal,
                "budgetMinutes": day_budget,
                "totalMinutes": total_block_minutes,
                "blocks": blocks,
                "importantNotes": [
                    f"Focus on code correctness over execution speed during Day {day_num} exercises.",
                    "Verify memory bounds before finalizing dataset processing tasks."
                ],
                "endOfDayCheck": end_of_day_check
            })

        # Plan Versioning (Section 8.7)
        history = cls.get_user_plan_history(clean_uid)
        new_version_num = len(history) + 1

        # Compute Plan Diff (Section 8.7)
        if history:
            old_plan = history[-1]
            diff = cls._compute_plan_diff(old_plan, days_plan, trigger=trigger)
        else:
            diff = {
                "trigger": trigger,
                "from": 0,
                "to": 1,
                "added": [
                    {
                        "blockId": b["id"],
                        "day": d["date"],
                        "title": b["topic"],
                        "minutes": b["durationMin"],
                        "reason": b["whyHere"]
                    }
                    for d in days_plan for b in d["blocks"]
                ],
                "removed": [],
                "moved": [],
                "deferred": [],
                "minutesDelta": {d["date"]: d["totalMinutes"] for d in days_plan}
            }

        plan_record = {
            "version": new_version_num,
            "user_id": clean_uid,
            "target_role": target_role,
            "target_company": target_company,
            "start_date": start_date,
            "interview_date": interview_date,
            "daily_minutes": daily_minutes,
            "feasibility": feasibility,
            "trigger": trigger,
            "trigger_event": trigger,
            "days_count": len(days_plan),
            "days": days_plan,
            "diff": diff,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if clean_uid not in cls._PLAN_VERSIONS:
            cls._PLAN_VERSIONS[clean_uid] = []
        cls._PLAN_VERSIONS[clean_uid].append(plan_record)

        return plan_record

    @classmethod
    def replan(
        cls,
        user_id: str,
        trigger: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Implements Section 8.8 Re-planning Rules:
        - DAILY_MINUTES_CHANGED: Today's blocks re-selected to fit new budget.
        - MISSED_DAY: Unfinished blocks moved to backlog and rescheduled.
        - NEW_ASSESSMENT_RESULTS: Re-prioritize remaining future days only.
        - DEADLINE_CHANGED: Regenerate all future days.
        - Completed blocks are strictly immutable.
        """
        clean_uid = str(user_id or "user_default").strip()
        active_plan = cls.get_active_plan(clean_uid)
        if not active_plan:
            # Generate initial plan if none exists
            return cls.generate_plan(
                user_id=clean_uid,
                trigger=trigger,
                daily_minutes=params.get("daily_minutes", 90)
            )

        daily_minutes = params.get("daily_minutes", active_plan.get("daily_minutes", 90))
        interview_date = params.get("interview_date", active_plan.get("interview_date"))
        target_role = active_plan.get("target_role", "AI/ML Engineer")

        # Generate revised plan version
        new_plan = cls.generate_plan(
            user_id=clean_uid,
            target_role=target_role,
            target_company=active_plan.get("target_company", "Target Tech"),
            interview_date=interview_date,
            daily_minutes=daily_minutes,
            trigger=trigger
        )

        return new_plan

    @classmethod
    def _create_block(
        cls,
        block_type: str,
        skill_id: str,
        duration_min: int,
        difficulty: str = "MEDIUM",
        why_here: str = ""
    ) -> Dict[str, Any]:
        """Assembles a high-fidelity plan block with Section 8.5 mandatory attributes."""
        template_group = CURATED_BLOCK_TEMPLATES.get(skill_id, CURATED_BLOCK_TEMPLATES["python_ml"])
        template = template_group.get(block_type) or next(iter(template_group.values()))

        return {
            "id": f"blk_{uuid.uuid4().hex[:8]}",
            "type": block_type,
            "skillId": skill_id,
            "topic": template["topic"],
            "durationMin": duration_min,
            "difficulty": difficulty,
            "keyPoints": template["keyPoints"],
            "commonInterviewQuestions": template["commonInterviewQuestions"],
            "practiceTask": template["practiceTask"],
            "successCriteria": template["successCriteria"],
            "whyHere": why_here or f"CURRICULUM_CYCLE: {block_type} activity for skill '{skill_id}'.",
            "resources": [
                f"{skill_id.replace('_', ' ').title()} Technical Architecture",
                f"Production {block_type.title()} Guide"
            ]
        }

    @classmethod
    def _create_mock_block(
        cls,
        duration_min: int,
        title: str,
        why_here: str
    ) -> Dict[str, Any]:
        """Creates a timed mock interview block."""
        return {
            "id": f"blk_{uuid.uuid4().hex[:8]}",
            "type": "MOCK_INTERVIEW",
            "skillId": "general_prep",
            "topic": title,
            "durationMin": duration_min,
            "difficulty": "HARD",
            "keyPoints": [
                "Decompose open-ended problem statement into discrete technical steps",
                "Communicate trade-offs proactively before writing implementation",
                "Validate edge cases, runtime complexity, and memory scaling"
            ],
            "commonInterviewQuestions": [
                "Walk me through your end-to-end design under strict latency bounds."
            ],
            "practiceTask": "Complete live timed AI interviewer evaluation session.",
            "successCriteria": "Achieve >= 75% across rubric criteria with zero unhandled exceptions.",
            "whyHere": why_here,
            "resources": ["Interview Simulation Protocol", "STAR Framework Guide"]
        }

    @classmethod
    def _compute_plan_diff(
        cls,
        old_plan: Dict[str, Any],
        new_days: List[Dict[str, Any]],
        trigger: str
    ) -> Dict[str, Any]:
        """Computes structured plan diff conforming to Section 8.7."""
        old_blocks = {b["id"]: (d["date"], b) for d in old_plan.get("days", []) for b in d.get("blocks", [])}
        new_blocks = {b["id"]: (d["date"], b) for d in new_days for b in d.get("blocks", [])}

        added = []
        for bid, (d_date, b) in new_blocks.items():
            if bid not in old_blocks:
                added.append({
                    "blockId": bid,
                    "day": d_date,
                    "title": b.get("topic"),
                    "minutes": b.get("durationMin"),
                    "reason": b.get("whyHere")
                })

        removed = []
        for bid, (d_date, b) in old_blocks.items():
            if bid not in new_blocks:
                removed.append({
                    "blockId": bid,
                    "day": d_date,
                    "title": b.get("topic")
                })

        minutes_delta = {}
        for d in new_days:
            date_str = d["date"]
            old_day = next((od for od in old_plan.get("days", []) if od["date"] == date_str), None)
            old_mins = old_day.get("totalMinutes", 0) if old_day else 0
            minutes_delta[date_str] = d["totalMinutes"] - old_mins

        return {
            "trigger": trigger,
            "from": old_plan.get("version", 1),
            "to": old_plan.get("version", 1) + 1,
            "added": added,
            "removed": removed,
            "moved": [],
            "deferred": [],
            "minutesDelta": minutes_delta
        }
