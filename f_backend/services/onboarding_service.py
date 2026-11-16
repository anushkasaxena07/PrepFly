"""
PREPFLY ONBOARDING & SKILL PROFILE SERVICE (Sections 2, 3, 8.1)
==============================================================
Manages multi-step onboarding, deterministic experience level derivation,
role skill profile generation with schema validation, negative guardrails,
editable skill review, and the Section 8.1 feasibility check.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union
from datetime import datetime, date, timedelta, timezone
import json
import uuid
import logging
import re
import os

from schemas.spec_schemas import (
    RoleProfileLLMOutputSchema,
    PillarSchema,
    SkillSchema,
    SubskillSchema,
    RubricCriterionSchema
)
from utils.timezone_utils import (
    get_timezone,
    get_current_user_date,
    determine_plan_start_date,
    parse_date_iso,
    format_date_iso
)
from utils.template_guard import sanitize_user_facing_string
from local_supabase import get_supabase_client

logger = logging.getLogger("prepfly.onboarding_service")

# Tier Minute Allocations from Section 8.1
TIER_BASE_MINUTES = {
    "MANDATORY": 180,
    "PREFERRED": 120,
    "SUPPORTING": 60
}

MIN_SKILL_MINUTES = 20


def derive_candidate_level(years_total: float) -> str:
    """
    Derives standard role seniority level from total experience (Section 2.1):
    0-2 yrs -> JUNIOR
    2-5 yrs -> MID
    5-8 yrs -> SENIOR
    8+  yrs -> STAFF
    """
    try:
        y = float(years_total if years_total is not None else 0.0)
    except (ValueError, TypeError):
        y = 0.0

    if y < 2.0:
        return "JUNIOR"
    elif y < 5.0:
        return "MID"
    elif y < 8.0:
        return "SENIOR"
    else:
        return "STAFF"


class OnboardingService:
    """
    Orchestrates candidate onboarding, skill profile generation,
    user skill customization, and feasibility assessment.
    """

    @classmethod
    def calculate_feasibility(
        cls,
        start_date: Union[date, str],
        interview_date: Union[date, str],
        skills: List[Dict[str, Any]],
        daily_minutes: int = 90,
        availability_grid: Optional[Dict[str, int]] = None,
        blackout_dates: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes the exact Section 8.1 Feasibility Check algorithm:
        availableDays   = list of dates from startDate to (interviewDate − 1) where availableMinutes(date) > 0
        totalMinutes    = Σ availableMinutes(date)
        baseMinutes(skill) = tierMinutes × gapFactor (min 20 min)
        requiredMinutes = Σ baseMinutes(skill) + 10% mock interviews + 10% revision
        
        Statuses:
        - COMFORTABLE: totalMinutes >= requiredMinutes
        - TIGHT: 70% <= totalMinutes < 100% (cuts SUPPORTING first)
        - AT_RISK: totalMinutes < 70% (drops/shallows skills ranked)
        - CRASH_MODE: interviewDate is today or tomorrow (<= 2 days)
        """
        s_date = start_date if isinstance(start_date, date) else parse_date_iso(str(start_date))
        i_date = interview_date if isinstance(interview_date, date) else parse_date_iso(str(interview_date))

        if not s_date or not i_date:
            raise ValueError("Valid start_date and interview_date are required.")

        days_until_interview = (i_date - s_date).days
        if days_until_interview < 0:
            raise ValueError(f"Interview date ({i_date}) cannot be before start date ({s_date}).")

        # Check Crash Mode (interview is today or tomorrow, <= 2 days)
        is_crash_mode = (days_until_interview <= 2)

        blackouts_set = set(str(b).strip() for b in (blackout_dates or []))

        # Default weekday mapping if grid not provided
        # availability_grid format: {"Mon": 90, "Tue": 90, ...}
        default_grid = {
            "Mon": daily_minutes, "Tue": daily_minutes, "Wed": daily_minutes,
            "Thu": daily_minutes, "Fri": daily_minutes, "Sat": daily_minutes, "Sun": daily_minutes
        }
        grid = {**default_grid, **(availability_grid or {})}

        available_days = []
        total_minutes = 0

        curr = s_date
        # available days from startDate to (interviewDate - 1)
        while curr < i_date:
            c_iso = format_date_iso(curr)
            if c_iso not in blackouts_set:
                weekday_name = curr.strftime("%a")  # Mon, Tue...
                mins = int(grid.get(weekday_name, daily_minutes))
                if mins > 0:
                    available_days.append({
                        "date": c_iso,
                        "weekday": weekday_name,
                        "minutes": mins
                    })
                    total_minutes += mins
            curr += timedelta(days=1)

        # Compute requiredMinutes over skills
        skill_breakdown = []
        raw_skills_required = 0

        for sk in skills:
            t_key = str(sk.get("tier", "PREFERRED")).upper().strip()
            tier_mins = TIER_BASE_MINUTES.get(t_key, 120)

            # gapFactor = (100 - P_skill)/100 for assessed skills, or 0.6 for unassessed
            prof = sk.get("proficiency")
            if prof is not None:
                gap_factor = max(0.0, (100.0 - float(prof)) / 100.0)
            else:
                gap_factor = 0.6  # assume moderate gap until measured

            base_mins = max(MIN_SKILL_MINUTES, int(round(tier_mins * gap_factor)))
            raw_skills_required += base_mins

            skill_breakdown.append({
                "skill_id": sk.get("id") or sk.get("skill_id"),
                "name": sk.get("name"),
                "tier": t_key,
                "importance": sk.get("importance", 3),
                "base_minutes": base_mins,
                "gap_factor": round(gap_factor, 2)
            })

        # Add 10% of totalMinutes for mock interviews and 10% for revision
        mock_allowance = int(round(0.10 * total_minutes))
        revision_allowance = int(round(0.10 * total_minutes))
        total_required_minutes = raw_skills_required + mock_allowance + revision_allowance

        # Determine Feasibility Status
        if is_crash_mode:
            status = "CRASH_MODE"
            message = "Interview is within 2 days. PrepFly has switched to High-Impact Crash Mode."
            dropped_skills = []
        elif total_minutes >= total_required_minutes:
            status = "COMFORTABLE"
            message = "Schedule is comfortable with sufficient capacity for core learning, revision, and mock interviews."
            dropped_skills = []
        elif total_minutes >= int(0.70 * total_required_minutes):
            status = "TIGHT"
            # Cut SUPPORTING skills first
            dropped_skills = [s for s in skill_breakdown if s["tier"] == "SUPPORTING"]
            message = (
                f"Schedule is tight ({total_minutes}m available vs {total_required_minutes}m required). "
                f"SUPPORTING skills ({len(dropped_skills)}) will be compressed or deferred to protect mandatory skills."
            )
        else:
            status = "AT_RISK"
            # Rank skills to drop: all SUPPORTING first, then PREFERRED by lowest importance
            supporting = [s for s in skill_breakdown if s["tier"] == "SUPPORTING"]
            preferred = sorted([s for s in skill_breakdown if s["tier"] == "PREFERRED"], key=lambda x: x["importance"])
            dropped_skills = supporting + preferred
            message = (
                f"Schedule is at risk (only {total_minutes}m available for {total_required_minutes}m required). "
                f"Consider adding 15-30 daily study minutes or adjusting rest days to avoid dropping critical skills."
            )

        return {
            "status": status,
            "message": message,
            "is_crash_mode": is_crash_mode,
            "days_until_interview": days_until_interview,
            "available_days_count": len(available_days),
            "total_available_minutes": total_minutes,
            "total_required_minutes": total_required_minutes,
            "skills_minutes_required": raw_skills_required,
            "mock_allowance_minutes": mock_allowance,
            "revision_allowance_minutes": revision_allowance,
            "available_days": available_days,
            "skills_breakdown": skill_breakdown,
            "at_risk_or_deferred_skills": dropped_skills[:5]
        }

    @classmethod
    def generate_skill_requirement_profile(
        cls,
        company: str,
        role: str,
        level: str,
        jd_text: Optional[str] = None,
        user_rules_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates role skill requirement profile complying with Section 3:
        1. Calls LLM with prompt in Section 12.1.
        2. Validates against RoleProfileLLMOutputSchema.
        3. If JD is provided, extracted items are USER_PROVIDED.
        4. General industry expectations are MODEL_INFERRED.
        5. Never invents facts about company rounds or internal tools unless provided.
        6. Falls back safely to structured canonical profile if LLM is offline or invalid.
        """
        comp_clean = sanitize_user_facing_string(company or "Target Company")
        role_clean = sanitize_user_facing_string(role or "AI/ML Engineer")
        lvl_clean = str(level or "MID").upper()
        if lvl_clean not in ("JUNIOR", "MID", "SENIOR", "STAFF"):
            lvl_clean = "MID"

        # Check prompt template
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "12_1_role_profile_generator.txt")
        system_instruction = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_instruction = f.read().strip()

        user_content = (
            f"Company: {comp_clean}\n"
            f"Role: {role_clean}\n"
            f"Seniority Level: {lvl_clean}\n"
        )
        if jd_text and len(jd_text.strip()) > 10:
            user_content += f"\nJob Description:\n{jd_text.strip()}\n"
        if user_rules_text and len(user_rules_text.strip()) > 5:
            user_content += f"\nUser Rules / Interview Notes:\n{user_rules_text.strip()}\n"

        # Attempt structured generation with safe invoke
        if os.getenv("ENVIRONMENT") == "test" or os.getenv("FLASK_ENV") == "test":
            model = None
        else:
            try:
                from services.ai_service import safe_invoke_llm, create_gemini_client, GEMINI_DEFAULT_PRIMARY_MODEL
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_INTERVIEW_KEY") or ""
                model = create_gemini_client(GEMINI_DEFAULT_PRIMARY_MODEL, api_key, temperature=0.1) if api_key else None
            except Exception:
                model = None
        raw_output = None

        if model:
            full_prompt = f"{system_instruction}\n\nCandidate Request:\n{user_content}"
            try:
                resp = safe_invoke_llm(model, full_prompt)
                if resp:
                    raw_text = resp if isinstance(resp, str) else getattr(resp, "content", "")
                    # Extract JSON
                    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        validated = RoleProfileLLMOutputSchema(**parsed)
                        return validated.model_dump()
            except Exception as e:
                logger.warning(f"LLM Role Profile generation error, invoking safe fallback: {e}")

        # Safe deterministic profile generator (Section 3.4 template)
        return cls._generate_canonical_fallback_profile(
            company=comp_clean,
            role=role_clean,
            level=lvl_clean,
            has_jd=bool(jd_text and len(jd_text.strip()) > 20)
        )

    @classmethod
    def _generate_canonical_fallback_profile(
        cls,
        company: str,
        role: str,
        level: str,
        has_jd: bool = False
    ) -> Dict[str, Any]:
        """
        Deterministic, validated fallback role profile following Section 3.3 and 3.4.
        Guarantees 100% compliance with RoleProfileLLMOutputSchema.
        """
        r_lower = role.lower()
        src_jd = "USER_PROVIDED" if has_jd else "MODEL_INFERRED"

        if "ai" in r_lower or "ml" in r_lower or "machine learning" in r_lower or "deep learning" in r_lower:
            pillars = [
                {"id": "p1", "name": "Programming & Data", "order": 1, "skills": []},
                {"id": "p2", "name": "ML Fundamentals", "order": 2, "skills": []},
                {"id": "p3", "name": "Deep Learning", "order": 3, "skills": []},
                {"id": "p4", "name": "GenAI", "order": 4, "skills": []},
                {"id": "p5", "name": "Production ML", "order": 5, "skills": []},
                {"id": "p6", "name": "Interview Execution", "order": 6, "skills": []}
            ]
            skills_data = [
                # Pillar 1
                {
                    "id": "sk_python_ml",
                    "name": "Python for ML (NumPy/Pandas)",
                    "pillarId": "p1",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_numpy_vector",
                            "name": "Vectorised Operations & Broadcasting",
                            "rubricCriteria": [
                                {"id": "c1", "criterion": "Eliminates Python loops using vectorised operations", "points": 35},
                                {"id": "c2", "criterion": "Applies broadcasting rules across multidimensional tensors", "points": 35},
                                {"id": "c3", "criterion": "Avoids unnecessary memory allocations in memory-constrained arrays", "points": 30}
                            ]
                        },
                        {
                            "id": "sub_pandas_indexing",
                            "name": "DataFrame Transformations & Aggregation",
                            "rubricCriteria": [
                                {"id": "c4", "criterion": "Correctly applies groupby, merge, and transform operations", "points": 50},
                                {"id": "c5", "criterion": "Handles missing data and categorical encodings cleanly", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_sql_opt",
                    "name": "SQL & Query Optimization",
                    "pillarId": "p1",
                    "tier": "PREFERRED",
                    "interviewImportance": 4,
                    "source": "MODEL_INFERRED",
                    "subskills": [
                        {
                            "id": "sub_sql_window",
                            "name": "Window Functions & Joins",
                            "rubricCriteria": [
                                {"id": "c6", "criterion": "Uses ROW_NUMBER, RANK, and partition windows correctly", "points": 50},
                                {"id": "c7", "criterion": "Optimizes join ordering and index utilization", "points": 50}
                            ]
                        }
                    ]
                },
                # Pillar 2
                {
                    "id": "sk_supervised",
                    "name": "Supervised Learning & Regularization",
                    "pillarId": "p2",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_regularization",
                            "name": "L1/L2 Regularization & Bias-Variance",
                            "rubricCriteria": [
                                {"id": "c8", "criterion": "Articulates bias-variance trade-off mathematically", "points": 50},
                                {"id": "c9", "criterion": "Explains difference between Lasso and Ridge sparsity", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_model_eval",
                    "name": "Model Evaluation & Imbalanced Metrics",
                    "pillarId": "p2",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_imbalanced_eval",
                            "name": "Precision/Recall & ROC-AUC",
                            "rubricCriteria": [
                                {"id": "c10", "criterion": "Selects appropriate metric for highly imbalanced distributions", "points": 50},
                                {"id": "c11", "criterion": "Interprets Precision-Recall curve trade-offs correctly", "points": 50}
                            ]
                        }
                    ]
                },
                # Pillar 3
                {
                    "id": "sk_transformers",
                    "name": "Transformer Architecture & Self-Attention",
                    "pillarId": "p3",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_self_attention",
                            "name": "Multi-Head Self-Attention Mechanics",
                            "rubricCriteria": [
                                {"id": "c12", "criterion": "Derives Scaled Dot-Product Attention equation", "points": 50},
                                {"id": "c13", "criterion": "Explains query, key, value matrix projection dimensions", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_neural_networks",
                    "name": "Neural Networks & Backpropagation",
                    "pillarId": "p3",
                    "tier": "PREFERRED",
                    "interviewImportance": 4,
                    "source": "MODEL_INFERRED",
                    "subskills": [
                        {
                            "id": "sub_backprop",
                            "name": "Gradient Calculation & Chain Rule",
                            "rubricCriteria": [
                                {"id": "c14", "criterion": "Applies chain rule across multilayer perceptron nodes", "points": 50},
                                {"id": "c15", "criterion": "Identifies exploding/vanishing gradient causes and remedies", "points": 50}
                            ]
                        }
                    ]
                },
                # Pillar 4
                {
                    "id": "sk_rag_mitigation",
                    "name": "RAG & Hallucination Mitigation",
                    "pillarId": "p4",
                    "tier": "PREFERRED",
                    "interviewImportance": 4,
                    "source": "MODEL_INFERRED",
                    "subskills": [
                        {
                            "id": "sub_rag_eval",
                            "name": "Dense Retrieval & Chunking Strategies",
                            "rubricCriteria": [
                                {"id": "c16", "criterion": "Designs vector embedding chunking and overlap parameters", "points": 50},
                                {"id": "c17", "criterion": "Evaluates context groundedness and citation faithfulness", "points": 50}
                            ]
                        }
                    ]
                },
                # Pillar 5
                {
                    "id": "sk_ml_design",
                    "name": "ML System Design & Feature Stores",
                    "pillarId": "p5",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_feature_store",
                            "name": "Offline/Online Feature Stores & Drift",
                            "rubricCriteria": [
                                {"id": "c18", "criterion": "Designs dual-storage architecture for low-latency inference", "points": 50},
                                {"id": "c19", "criterion": "Defines data drift and concept drift monitoring alerts", "points": 50}
                            ]
                        }
                    ]
                },
                # Pillar 6
                {
                    "id": "sk_star_stories",
                    "name": "Behavioral/STAR Stories",
                    "pillarId": "p6",
                    "tier": "SUPPORTING",
                    "interviewImportance": 3,
                    "source": "MODEL_INFERRED",
                    "subskills": [
                        {
                            "id": "sub_star_comm",
                            "name": "Conflict Resolution & Technical Ownership",
                            "rubricCriteria": [
                                {"id": "c20", "criterion": "Structures answer in Situation, Task, Action, Result format", "points": 50},
                                {"id": "c21", "criterion": "Articulates measurable business and engineering impact", "points": 50}
                            ]
                        }
                    ]
                }
            ]
        else:
            # Default General Software Engineering Profile
            pillars = [
                {"id": "p1", "name": "Data Structures & Algorithms", "order": 1, "skills": []},
                {"id": "p2", "name": "System Design", "order": 2, "skills": []},
                {"id": "p3", "name": "Core Computer Science", "order": 3, "skills": []},
                {"id": "p4", "name": "Interview Execution", "order": 4, "skills": []}
            ]
            skills_data = [
                {
                    "id": "sk_arrays_strings",
                    "name": "Arrays & Strings",
                    "pillarId": "p1",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_two_pointers",
                            "name": "Two Pointers & Sliding Window",
                            "rubricCriteria": [
                                {"id": "c1", "criterion": "Identifies optimal sub-array window expansion and contraction", "points": 50},
                                {"id": "c2", "criterion": "Achieves O(N) time and O(1) auxiliary space bounds", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_trees_graphs",
                    "name": "Trees & Graphs",
                    "pillarId": "p1",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_graph_traversal",
                            "name": "DFS, BFS & Topological Sort",
                            "rubricCriteria": [
                                {"id": "c3", "criterion": "Implements cycle detection and shortest path search", "points": 50},
                                {"id": "c4", "criterion": "Maintains visited set and handles disconnected components", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_caching",
                    "name": "Caching & Memory Hierarchy",
                    "pillarId": "p2",
                    "tier": "MANDATORY",
                    "interviewImportance": 5,
                    "source": src_jd,
                    "subskills": [
                        {
                            "id": "sub_cache_eviction",
                            "name": "LRU/LFU Eviction & Consistency",
                            "rubricCriteria": [
                                {"id": "c5", "criterion": "Explains write-through vs write-back caching trade-offs", "points": 50},
                                {"id": "c6", "criterion": "Formulates cache invalidation and stampede protections", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_dbms",
                    "name": "DBMS Internals & Indexing",
                    "pillarId": "p3",
                    "tier": "PREFERRED",
                    "interviewImportance": 4,
                    "source": "MODEL_INFERRED",
                    "subskills": [
                        {
                            "id": "sub_b_trees",
                            "name": "B-Tree Indexing & ACID Isolation",
                            "rubricCriteria": [
                                {"id": "c7", "criterion": "Explains clustered vs non-clustered index lookup mechanics", "points": 50},
                                {"id": "c8", "criterion": "Contrasts read-committed and serializable isolation anomalies", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_concurrency",
                    "name": "Concurrency & Distributed Primitives",
                    "pillarId": "p3",
                    "tier": "PREFERRED",
                    "interviewImportance": 4,
                    "source": "MODEL_INFERRED",
                    "subskills": [
                        {
                            "id": "sub_locks_consensus",
                            "name": "Mutex Locks & Consensus Basics",
                            "rubricCriteria": [
                                {"id": "c11", "criterion": "Contrasts optimistic and pessimistic locking", "points": 50},
                                {"id": "c12", "criterion": "Formulates deadlock avoidance strategies", "points": 50}
                            ]
                        }
                    ]
                },
                {
                    "id": "sk_tradeoffs",
                    "name": "Technical Trade-off Articulation",
                    "pillarId": "p4",
                    "tier": "SUPPORTING",
                    "interviewImportance": 3,
                    "source": "MODEL_INFERRED",
                    "subskills": [
                        {
                            "id": "sub_tradeoff_defense",
                            "name": "Architecture Justification & Communication",
                            "rubricCriteria": [
                                {"id": "c9", "criterion": "Clearly defends architectural choices with bottleneck awareness", "points": 50},
                                {"id": "c10", "criterion": "Speaks concisely with structured trade-off comparisons", "points": 50}
                            ]
                        }
                    ]
                }
            ]

        # Assemble and validate with Pydantic
        payload = {
            "roleTitle": role,
            "company": company,
            "level": level,
            "pillars": pillars,
            "skills": skills_data
        }
        validated = RoleProfileLLMOutputSchema(**payload)
        return validated.model_dump()

    # In-memory storage cache for active candidate onboarding state
    _PROFILE_CACHE: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def save_onboarding_target_profile(
        cls,
        user_id: str,
        data: Dict[str, Any],
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Processes multi-step onboarding payload (Section 2.1):
        Step 1 (Target): company, role, optional jd_text, optional user_rules
        Step 2 (Experience): years_total, years_domain, current_role, technologies, self_ratings (self_claim only)
        Step 3 (Constraints): interview_date, daily_minutes, availability_grid, blackout_dates
        Step 4 (Review): Generates skill profile via LLM/schema and computes feasibility
        """
        clean_uid = str(user_id or "user_default").strip()

        company = sanitize_user_facing_string(data.get("company") or "Target Tech")
        role = sanitize_user_facing_string(data.get("role") or data.get("role_title") or "AI/ML Engineer")

        # Step 2: Experience & level derivation
        years_total = float(data.get("years_total", 0.0) or 0.0)
        years_domain = float(data.get("years_domain", 0.0) or 0.0)
        derived_lvl = derive_candidate_level(years_total)
        # User override takes precedence
        level = str(data.get("level") or derived_lvl).upper()
        if level not in ("JUNIOR", "MID", "SENIOR", "STAFF"):
            level = derived_lvl

        # Step 3: Constraints
        user_tz = data.get("timezone", "Asia/Kolkata")
        today_user_date = get_current_user_date(user_tz)

        raw_i_date = data.get("interview_date")
        if not raw_i_date:
            # Default to 18 days in future (matching Worked Example Section 15)
            interview_d = today_user_date + timedelta(days=18)
            interview_date_str = format_date_iso(interview_d)
        else:
            interview_date_str = str(raw_i_date)[:10]
            interview_d = parse_date_iso(interview_date_str)

        daily_minutes = int(data.get("daily_minutes", 90) or 90)
        daily_minutes = max(15, min(480, daily_minutes))

        availability_grid = data.get("availability_grid") or {
            "Mon": daily_minutes, "Tue": daily_minutes, "Wed": daily_minutes,
            "Thu": daily_minutes, "Fri": daily_minutes, "Sat": daily_minutes, "Sun": daily_minutes
        }
        blackout_dates = data.get("blackout_dates") or []

        # Generate Skill Requirement Profile
        skill_profile = cls.generate_skill_requirement_profile(
            company=company,
            role=role,
            level=level,
            jd_text=data.get("jd_text"),
            user_rules_text=data.get("user_rules_text") or data.get("user_rules")
        )

        # Compute initial Feasibility Check
        feasibility = cls.calculate_feasibility(
            start_date=today_user_date,
            interview_date=interview_d,
            skills=skill_profile.get("skills", []),
            daily_minutes=daily_minutes,
            availability_grid=availability_grid,
            blackout_dates=blackout_dates
        )

        target_profile_id = f"tp_{uuid.uuid4().hex[:12]}"
        profile_record = {
            "id": target_profile_id,
            "user_id": clean_uid,
            "company": company,
            "role": role,
            "level": level,
            "derived_level": derived_lvl,
            "years_total": years_total,
            "years_domain": years_domain,
            "current_role": data.get("current_role"),
            "technologies": data.get("technologies") or [],
            "self_ratings": data.get("self_ratings") or {},
            "interview_date": interview_date_str,
            "daily_minutes": daily_minutes,
            "availability_grid": availability_grid,
            "blackout_dates": blackout_dates,
            "study_time_preference": data.get("study_time_preference", "evening"),
            "learning_preference": data.get("learning_preference", "balanced"),
            "skills_profile": skill_profile,
            "feasibility": feasibility,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Cache in memory
        cls._PROFILE_CACHE[clean_uid] = profile_record

        # Best-effort persist to DB
        try:
            supabase = supabase_client or get_supabase_client()
            supabase.table("target_profiles").upsert({
                "id": target_profile_id,
                "user_id": clean_uid,
                "company": company,
                "role": role,
                "level": level,
                "years_total": years_total,
                "years_domain": years_domain,
                "jd_text": data.get("jd_text"),
                "user_rules_text": data.get("user_rules_text"),
                "interview_date": interview_date_str
            }).execute()
        except Exception as e:
            logger.debug(f"Target profile DB persist notice: {e}")

        return profile_record

    @classmethod
    def update_profile_skills(
        cls,
        user_id: str,
        updated_skills: List[Dict[str, Any]],
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Allows candidate to edit, re-tier, add or remove skills during Step 4 review (Section 2.1 & 11).
        Recomputes feasibility check with updated skill list.
        """
        clean_uid = str(user_id or "user_default").strip()
        prof = cls._PROFILE_CACHE.get(clean_uid) or {}

        # Normalize skill structure
        clean_skills = []
        for sk in updated_skills:
            t_key = str(sk.get("tier", "PREFERRED")).upper().strip()
            if t_key not in ("MANDATORY", "PREFERRED", "SUPPORTING"):
                t_key = "PREFERRED"
            clean_skills.append({
                "id": sk.get("id") or sk.get("skill_id") or f"sk_{uuid.uuid4().hex[:8]}",
                "name": sanitize_user_facing_string(sk.get("name") or "Custom Skill"),
                "pillarId": sk.get("pillarId") or sk.get("pillar_id") or "p1",
                "tier": t_key,
                "interviewImportance": int(sk.get("interviewImportance", sk.get("importance", 3)) or 3),
                "source": sk.get("source", "USER_PROVIDED"),
                "subskills": sk.get("subskills") or [
                    {
                        "id": f"sub_{uuid.uuid4().hex[:6]}",
                        "name": "Practical Applications & Trade-offs",
                        "rubricCriteria": [
                            {"id": "c1", "criterion": "Demonstrates practical technical fluency", "points": 50},
                            {"id": "c2", "criterion": "Defends engineering trade-offs cleanly", "points": 50}
                        ]
                    }
                ]
            })

        # Update skills profile
        existing_profile = prof.get("skills_profile") or {}
        existing_profile["skills"] = clean_skills
        prof["skills_profile"] = existing_profile

        # Re-run Feasibility Check
        today_date = get_current_user_date("Asia/Kolkata")
        raw_i_date = prof.get("interview_date") or format_date_iso(today_date + timedelta(days=18))
        interview_d = parse_date_iso(raw_i_date)

        feasibility = cls.calculate_feasibility(
            start_date=today_date,
            interview_date=interview_d,
            skills=clean_skills,
            daily_minutes=prof.get("daily_minutes", 90),
            availability_grid=prof.get("availability_grid"),
            blackout_dates=prof.get("blackout_dates")
        )
        prof["feasibility"] = feasibility
        prof["updated_at"] = datetime.now(timezone.utc).isoformat()
        cls._PROFILE_CACHE[clean_uid] = prof

        return {
            "status": "success",
            "message": "Skill profile updated successfully",
            "skills": clean_skills,
            "feasibility": feasibility
        }

    @classmethod
    def get_feasibility_check(
        cls,
        user_id: str,
        supabase_client=None
    ) -> Dict[str, Any]:
        """Fetches active user constraints and computes real-time feasibility."""
        clean_uid = str(user_id or "user_default").strip()
        prof = cls._PROFILE_CACHE.get(clean_uid)

        if prof and prof.get("feasibility"):
            return prof["feasibility"]

        today_date = get_current_user_date("Asia/Kolkata")
        interview_d = today_date + timedelta(days=18)
        default_skills = cls.generate_skill_requirement_profile("Target Company", "AI/ML Engineer", "MID").get("skills", [])

        return cls.calculate_feasibility(
            start_date=today_date,
            interview_date=interview_d,
            skills=default_skills,
            daily_minutes=90
        )

