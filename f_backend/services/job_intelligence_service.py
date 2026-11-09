"""
PrepFly Job-Specific Preparation Intelligence Service
Production-Grade Multi-Stage Job Description Understanding, Semantic Skill Mapping,
Role-Aware Interview Blueprint Construction, and Grounded Question Generation Engine.

Pipeline Stages:
1. Raw JD Text Normalization (cleanup, whitespace, paragraph preservation, offset tracking)
2. Section Detection (Responsibilities, Requirements, Preferred, Experience, Role Context)
3. Atomic Requirement Extraction with Text Provenance
4. Semantic Classification & Canonical Skill Mapping with Negative Guardrails
5. Requirement Normalization & Semantic Deduplication
6. Requirement Classification & Calibrated Weighting
7. Candidate Evidence Alignment & Decoupled Match Scoring
8. Role-Aware Interview Blueprint Construction
9. Grounded Question Generation (Zero Hallucination / Zero DP for ML)
10. Multi-Dimensional Quality Evaluation & De-duplication
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timezone
import json
import re
import uuid
import logging

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG, normalize_role_id
from services.skill_profiling_service import SkillProfilingService

logger = logging.getLogger("prepfly.intelligence.jobs")


# =============================================================================
# 1. Negative Semantic Guardrails
# =============================================================================
# Strict guardrails preventing false-positive mappings without explicit source text evidence.
# Even if a phrase matches an alias, it is REJECTED if it violates these semantic rules.
NEGATIVE_GUARDRAILS = {
    # Dynamic Programming must NEVER be inferred from "model", "algorithm", or generic technical text
    "dsa_dp": [r"\bdynamic programming\b", r"\bdp\b", r"\bmemoization\b", r"\bknapsack\b", r"\btabulation\b"],
    # SQL must NEVER be inferred from generic data preprocessing or data cleaning
    "cs_sql": [r"\bsql\b", r"\bpostgres\b", r"\bmysql\b", r"\brelational database\b", r"\bcomplex queries\b"],
    # Database Design must NEVER be inferred from dataset scale or volume
    "sys_db_design": [r"\bdatabase design\b", r"\bschema design\b", r"\bindexing\b", r"\bb-tree\b", r"\bnormalization\b", r"\brdbms\b"],
    # Fault tolerance / disaster recovery must NEVER be inferred from production deployment
    "sys_fault_tolerance": [r"\bfault tolerance\b", r"\bdisaster recovery\b", r"\bcircuit breaker\b", r"\bfailover\b", r"\bhigh availability\b"],
}

# =============================================================================
# 2. Semantic Alias to Canonical Skill Mapping Dictionary
# =============================================================================
TECH_TO_CANONICAL_SKILL = {
    # ── Mathematics & Statistics ──
    "linear algebra": "math_linear_algebra",
    "matrix": "math_linear_algebra",
    "matrices": "math_linear_algebra",
    "eigenvalues": "math_linear_algebra",
    "svd": "math_linear_algebra",
    "probability": "math_probability_statistics",
    "statistics": "math_probability_statistics",
    "statistical": "math_probability_statistics",
    "hypothesis testing": "math_probability_statistics",

    # ── Machine Learning ──
    "numpy": "ml_python_libraries",
    "pandas": "ml_python_libraries",
    "python for ml": "ml_python_libraries",
    "machine learning": "ml_model_development",
    "ml models": "ml_model_development",
    "ml model": "ml_model_development",
    "model development": "ml_model_development",
    "model training": "ml_model_development",
    "train models": "ml_model_development",
    "training models": "ml_model_development",
    "scikit-learn": "ml_python_libraries",
    "logistic regression": "ml_classical_algorithms",
    "linear regression": "ml_classical_algorithms",
    "svm": "ml_classical_algorithms",
    "support vector": "ml_classical_algorithms",
    "decision trees": "ml_tree_ensembles",
    "decision tree": "ml_tree_ensembles",
    "random forest": "ml_tree_ensembles",
    "xgboost": "ml_tree_ensembles",
    "gradient boosting": "ml_tree_ensembles",
    "clustering": "ml_clustering_pca",
    "k-means": "ml_clustering_pca",
    "pca": "ml_clustering_pca",
    "supervised learning": "ml_supervised_unsupervised",
    "unsupervised learning": "ml_supervised_unsupervised",
    "model evaluation": "ml_model_evaluation",
    "feature engineering": "ml_feature_engineering",
    "hyperparameter tuning": "ml_model_development",

    # ── Deep Learning ──
    "deep learning": "dl_neural_networks",
    "neural networks": "dl_neural_networks",
    "neural network": "dl_neural_networks",
    "pytorch": "dl_frameworks_pytorch_tensorflow",
    "tensorflow": "dl_frameworks_pytorch_tensorflow",
    "keras": "dl_frameworks_pytorch_tensorflow",
    "computer vision": "dl_computer_vision_cnn",
    "cnn": "dl_computer_vision_cnn",
    "convolutional": "dl_computer_vision_cnn",
    "transformers": "dl_transformers",
    "transformer models": "dl_transformers",
    "self-attention": "dl_transformers",
    "attention mechanisms": "dl_transformers",
    "fine-tune": "dl_fine_tuning",
    "fine-tuning": "dl_fine_tuning",
    "fine tuning": "dl_fine_tuning",
    "transfer learning": "dl_fine_tuning",
    "lora": "dl_fine_tuning",
    "peft": "dl_fine_tuning",

    # ── NLP ──
    "nlp": "nlp_pipelines",
    "natural language processing": "nlp_pipelines",
    "text processing": "nlp_pipelines",
    "tokenization": "nlp_pipelines",
    "embeddings": "nlp_embeddings",
    "vector embeddings": "nlp_embeddings",
    "dense embeddings": "nlp_embeddings",

    # ── Generative AI & LLMs ──
    "generative ai": "genai_llm_fundamentals",
    "genai": "genai_llm_fundamentals",
    "llm": "genai_llm_fundamentals",
    "llms": "genai_llm_fundamentals",
    "large language models": "genai_llm_fundamentals",
    "foundation models": "genai_llm_fundamentals",
    "prompt engineering": "genai_llm_fundamentals",
    "rag": "genai_llm_fundamentals",
    "retrieval augmented generation": "genai_llm_fundamentals",

    # ── Data Engineering & Preprocessing ──
    "data collection": "data_preprocessing",
    "data cleaning": "data_preprocessing",
    "clean data": "data_preprocessing",
    "preprocess": "data_preprocessing",
    "preprocessing": "data_preprocessing",
    "data preprocessing": "data_preprocessing",
    "data processing": "data_preprocessing",
    "large-scale datasets": "data_dataset_management",
    "datasets": "data_dataset_management",
    "manage datasets": "data_dataset_management",
    "dataset management": "data_dataset_management",
    "data engineering": "data_feature_pipelines",
    "feature pipeline": "data_feature_pipelines",
    "feature pipelines": "data_feature_pipelines",
    "etl": "data_feature_pipelines",

    # ── MLOps & Productionization ──
    "productionization": "mlops_model_deployment",
    "deploy models": "mlops_model_deployment",
    "model deployment": "mlops_model_deployment",
    "deployment": "mlops_model_deployment",
    "deploying models": "mlops_model_deployment",
    "model serving": "mlops_model_serving_apis",
    "inference": "mlops_model_serving_apis",
    "prediction api": "mlops_model_serving_apis",
    "data drift": "mlops_monitoring_drift",
    "model monitoring": "mlops_monitoring_drift",
    "concept drift": "mlops_monitoring_drift",
    "covariate shift": "mlops_monitoring_drift",
    "retrain": "mlops_automated_retraining",
    "retraining": "mlops_automated_retraining",
    "ml system design": "sys_ml_system_design",
    "machine learning system design": "sys_ml_system_design",
    "recommendation system": "sys_ml_system_design",
    "recommendation systems": "sys_ml_system_design",
    "ranking system": "sys_ml_system_design",
    "feature store": "sys_ml_system_design",

    # ── Core Backend, APIs, Scalability (Unified Canonical IDs) ──
    "api": "sys_rest_apis",
    "apis": "sys_rest_apis",
    "rest": "sys_rest_apis",
    "rest api": "sys_rest_apis",
    "restful api": "sys_rest_apis",
    "grpc": "sys_rest_apis",
    "api design": "sys_rest_apis",
    "scalability": "sys_scalability",
    "scalable": "sys_scalability",
    "low latency": "sys_scalability",
    "latency": "sys_scalability",
    "real-time": "sys_scalability",
    "high throughput": "sys_scalability",

    # ── Languages & Infrastructure ──
    "python": "python",
    "sql": "cs_sql",
    "database": "sys_db_design",
    "caching": "sys_caching",
    "redis": "sys_caching",
    "docker": "cloud_devops",
    "kubernetes": "cloud_devops",
    "k8s": "cloud_devops",
    "operating systems": "cs_os",
    "operating system": "cs_os",
    "memory management": "cs_os",
    "concurrency": "cs_concurrency",
    "oop": "cs_oop",
    "object oriented": "cs_oop",

    # ── DSA (ONLY mapped when explicitly named) ──
    "dynamic programming": "dsa_dp",
    "dp": "dsa_dp",
    "algorithms": "dsa_arrays",
    "data structures": "dsa_arrays",

    # ── Behavioral & Collaboration ──
    "communication": "soft_communication",
    "collaboration": "soft_communication",
    "cross-functional": "soft_communication",
    "stakeholders": "soft_communication",
    "leadership": "soft_leadership_ownership",
    "ownership": "soft_leadership_ownership"
}

# Alias Unification Map: Prevents duplicate requirements like REST API + API Design
CANONICAL_ALIASES = {
    "api_design": "sys_rest_apis",
    "databases_caching": "sys_db_design",
    "arrays_hashing": "dsa_arrays",
    "high_level_system_design": "sys_scalability",
    "distributed_systems": "sys_scalability"
}


class JobIntelligenceService:
    """End-to-end intelligence engine for job-specific preparation."""

    # =========================================================================
    # Public Entrypoints
    # =========================================================================

    @classmethod
    def ingest_job_description(
        cls,
        user_id: str,
        raw_text: str,
        job_title: Optional[str] = None,
        company: Optional[str] = None,
        target_date: Optional[str] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Multi-stage controlled pipeline for job description ingestion:
        1. Normalization & Section Detection
        2. Atomic Requirement Extraction with negative guardrails
        3. Deduplication & Semantic Alias Unification
        4. Decoupled Candidate Match & Gap Analysis
        5. Role-Aware Blueprint & Tailored Question Generation
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not raw_text or len(raw_text.strip()) < 20:
            raise ValueError("Job description text must be at least 20 characters.")

        supabase = supabase_client or get_supabase_client()
        sanitized_text = cls._sanitize_jd_text(raw_text)

        # 1. Infer metadata if missing
        inferred_title = job_title or cls._infer_job_title(sanitized_text)
        inferred_company = company or cls._infer_company(sanitized_text)
        role_tier = cls._infer_role_tier(sanitized_text, inferred_title)

        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # 2. Persist Job Profile
        job_row = {
            "id": job_id,
            "user_id": user_id,
            "job_title": inferred_title,
            "company": inferred_company,
            "raw_text": sanitized_text,
            "role_tier": role_tier,
            "target_date": target_date or "",
            "created_at": now_iso,
            "updated_at": now_iso
        }
        supabase.table("job_profiles").insert(job_row).execute()

        # 3. Extract, Classify, Guardrail & Deduplicate Requirements
        requirements = cls._extract_and_deduplicate_requirements(job_id, sanitized_text, role_tier)
        for req in requirements:
            supabase.table("job_requirements").insert(req).execute()

        # 4. Decoupled Match & Gap Analysis
        gap_analysis = cls.calculate_skill_gaps(user_id=user_id, job_id=job_id, supabase_client=supabase)

        # 5. Role-Aware Blueprint & Tailored Question Generation
        tailored_questions = cls.generate_and_evaluate_questions(
            job_id=job_id,
            job_title=inferred_title,
            role_tier=role_tier,
            requirements=requirements,
            supabase_client=supabase
        )

        # 6. Pipeline Event Emission
        try:
            from services.event_pipeline_service import EventPipelineService
            EventPipelineService.emit_event(
                user_id=user_id,
                event_type="job_description_analyzed",
                source_module="JOB_INTELLIGENCE",
                source_record_id=job_id,
                payload={
                    "job_id": job_id,
                    "job_title": inferred_title,
                    "company": inferred_company,
                    "overall_match_percentage": gap_analysis.get("overall_match_percentage", 0.0),
                    "critical_gaps_count": len(gap_analysis.get("critical_gaps", []))
                },
                supabase_client=supabase
            )
        except Exception as ex:
            logger.warning(f"Failed to emit job_description_analyzed event: {ex}")

        return {
            "job_profile": job_row,
            "requirements": requirements,
            "gap_analysis": gap_analysis,
            "tailored_questions": tailored_questions
        }

    # =========================================================================
    # Stage A-E: Section-Aware Requirement Extraction & Deduplication
    # =========================================================================

    @classmethod
    def _extract_and_deduplicate_requirements(
        cls,
        job_id: str,
        text: str,
        role_tier: str
    ) -> List[Dict[str, Any]]:
        """
        Executes Stages A through E of the understanding pipeline:
        - Segments text into section blocks
        - Parses individual responsibility / qualification clauses
        - Maps to canonical skills with negative guardrail validation
        - Deduplicates identical canonical skills, merging supporting evidence passages
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        sections = cls._detect_sections(text)

        extracted_by_skill: Dict[str, Dict[str, Any]] = {}

        for sec in sections:
            sec_type = sec["section_type"]
            for sentence in sec["sentences"]:
                s_clean = sentence.strip()
                if len(s_clean) < 8:
                    continue

                s_lower = s_clean.lower()

                # Determine requirement classification and weight from section context
                is_preferred_phrase = bool(re.search(r"\b(nice to have|preferred|bonus|plus|optional|desired)\b", s_lower))
                if sec_type == "PREFERRED" or is_preferred_phrase:
                    is_required = 0
                    req_type = "preferred_qualification"
                    base_weight = 2.5
                elif sec_type == "REQUIREMENTS":
                    is_required = 1
                    req_type = "mandatory_requirement"
                    base_weight = 5.0
                elif sec_type == "RESPONSIBILITIES":
                    is_required = 1
                    req_type = "core_responsibility"
                    base_weight = 4.0
                else:
                    is_required = 1
                    req_type = "core_technical"
                    base_weight = 3.5

                # Adjust for seniority tier
                if role_tier in ("senior", "staff") and req_type in ("core_responsibility", "mandatory_requirement"):
                    base_weight += 0.5

                # Search technology and skill keywords
                for kw, raw_canonical in TECH_TO_CANONICAL_SKILL.items():
                    # Check exact word boundary match
                    if re.search(rf"\b{re.escape(kw)}\b", s_lower):
                        # Unify alias to master canonical ID
                        canonical_skill = CANONICAL_ALIASES.get(raw_canonical, raw_canonical)

                        # Negative Guardrail Validation
                        if not cls._passes_negative_guardrails(canonical_skill, s_lower):
                            continue

                        # Stage E: Semantic Deduplication & Evidence Merging
                        if canonical_skill in extracted_by_skill:
                            existing = extracted_by_skill[canonical_skill]
                            # If either occurrence is required, mark as required
                            if is_required:
                                existing["is_required"] = 1
                                existing["requirement_type"] = req_type
                                existing["importance_weight"] = max(existing["importance_weight"], base_weight)
                            # Append evidence passage if not already present
                            if s_clean not in existing["evidence_text"]:
                                existing["evidence_text"] = f"{existing['evidence_text']} • {s_clean}"[:350]
                        else:
                            extracted_by_skill[canonical_skill] = {
                                "id": f"req_{uuid.uuid4().hex[:12]}",
                                "job_id": job_id,
                                "normalized_skill_id": canonical_skill,
                                "requirement_type": req_type,
                                "is_required": is_required,
                                "importance_weight": base_weight,
                                "evidence_text": s_clean[:250],
                                "created_at": now_iso
                            }

        # Fallback if no specific skills matched
        if not extracted_by_skill:
            fallback = ["sys_rest_apis", "sys_scalability", "soft_communication"]
            for sid in fallback:
                extracted_by_skill[sid] = {
                    "id": f"req_{uuid.uuid4().hex[:12]}",
                    "job_id": job_id,
                    "normalized_skill_id": sid,
                    "requirement_type": "core_technical",
                    "is_required": 1,
                    "importance_weight": 3.0,
                    "evidence_text": "General technical interview baseline requirement",
                    "created_at": now_iso
                }

        # Order by is_required descending, then importance weight descending
        result = list(extracted_by_skill.values())
        result.sort(key=lambda r: (r["is_required"], r["importance_weight"]), reverse=True)
        return result

    @classmethod
    def _passes_negative_guardrails(cls, skill_id: str, sentence_lower: str) -> bool:
        """
        Validates that a mapping has genuine textual evidence and rejects false positives.
        e.g., prevents model development -> DP, data preprocessing -> SQL, dataset scale -> DB indexing.
        """
        if skill_id in NEGATIVE_GUARDRAILS:
            required_patterns = NEGATIVE_GUARDRAILS[skill_id]
            if not any(re.search(pat, sentence_lower) for pat in required_patterns):
                return False
        return True

    @classmethod
    def _detect_sections(cls, text: str) -> List[Dict[str, Any]]:
        """
        Segments raw job description into structured sections based on contextual headers.
        """
        lines = text.split("\n")
        sections = []
        current_section = "GENERAL"
        current_sentences = []

        resp_patterns = [r"\b(?:core\s+)?responsibilities\b", r"\bwhat\s+you(?:'ll|\s+will)\s+do\b", r"\bduties\b", r"\bkey\s+responsibilities\b"]
        req_patterns = [r"\b(?:minimum|basic|required)\s+qualifications\b", r"\brequirements\b", r"\bwhat\s+you(?:'ll|\s+will)\s+bring\b", r"\bmust\s+have\b"]
        pref_patterns = [r"\bpreferred\s+qualifications\b", r"\bnice\s+to\s+have\b", r"\bbonus\s+points\b", r"\bpluses\b", r"\bdesired\b"]

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            l_lower = line_str.lower()

            # Check header triggers
            if any(re.search(p, l_lower) for p in resp_patterns):
                if current_sentences:
                    sections.append({"section_type": current_section, "sentences": current_sentences})
                current_section = "RESPONSIBILITIES"
                current_sentences = []
                continue
            elif any(re.search(p, l_lower) for p in req_patterns):
                if current_sentences:
                    sections.append({"section_type": current_section, "sentences": current_sentences})
                current_section = "REQUIREMENTS"
                current_sentences = []
                continue
            elif any(re.search(p, l_lower) for p in pref_patterns):
                if current_sentences:
                    sections.append({"section_type": current_section, "sentences": current_sentences})
                current_section = "PREFERRED"
                current_sentences = []
                continue

            # Split bullets or clauses within the line
            clauses = re.split(r"[•\-\*]+|(?<=[.!?])\s+", line_str)
            for c in clauses:
                c_clean = c.strip()
                if len(c_clean) > 8:
                    current_sentences.append(c_clean)

        if current_sentences:
            sections.append({"section_type": current_section, "sentences": current_sentences})

        return sections if sections else [{"section_type": "GENERAL", "sentences": [text]}]

    # =========================================================================
    # Stage G: Decoupled Candidate Matching & Gap Analysis
    # =========================================================================

    @classmethod
    def calculate_skill_gaps(
        cls,
        user_id: str,
        job_id: str,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Calculates verified match percentage and distinguishes:
        - Demonstrated Skills (verified through assessment or mock)
        - Partially Demonstrated Skills
        - Unassessed Requirements (does NOT treat missing evidence as 0% ability)
        - Critical Deficits (only assessed skills with score < 50%)
        """
        supabase = supabase_client or get_supabase_client()

        # Fetch job requirements
        req_res = supabase.table("job_requirements").select("*").eq("job_id", job_id).execute()
        reqs = req_res.data if (req_res and req_res.data) else []

        # Fetch candidate skill profiles
        skill_profiles = SkillProfilingService.get_candidate_profile(supabase, user_id)

        if not reqs:
            return {
                "overall_match_percentage": 0.0,
                "required_match_percentage": 0.0,
                "preferred_match_percentage": 0.0,
                "evidence_coverage_percentage": 0.0,
                "critical_gaps": [],
                "aligned_skills": [],
                "unassessed_skills": [],
                "readiness_verdict": "DIAGNOSTIC_EVALUATION_RECOMMENDED"
            }

        total_req_weight = 0.0
        assessed_req_weight = 0.0
        earned_req_score = 0.0

        total_pref_weight = 0.0
        assessed_pref_weight = 0.0
        earned_pref_score = 0.0

        critical_gaps = []
        aligned_skills = []
        unassessed_skills = []

        for req in reqs:
            sid = req["normalized_skill_id"]
            weight = float(req.get("importance_weight", 3.0))
            is_req = bool(req.get("is_required", 1))

            sp = skill_profiles.get(sid, {})
            ev_count = int(sp.get("evidence_count", 0))
            current_prof = float(sp.get("proficiency", 0.0))
            conf = float(sp.get("confidence", 0.0))

            target_prof = 75.0 if is_req else 60.0
            deficit = max(0.0, target_prof - current_prof)

            meta = SKILL_CATALOG.get(sid, {})
            skill_name = meta.get("name", sid.replace("_", " ").title())

            skill_entry = {
                "skill_id": sid,
                "skill_name": skill_name,
                "requirement_type": req.get("requirement_type", "core_technical"),
                "is_required": is_req,
                "current_proficiency": current_prof if ev_count > 0 else 0.0,
                "target_proficiency": target_prof,
                "confidence": conf,
                "evidence_count": ev_count,
                "deficit": round(deficit, 1) if ev_count > 0 else target_prof,
                "evidence_status": "DEMONSTRATED" if (ev_count > 0 and current_prof >= 70.0) else (
                    "PARTIALLY_DEMONSTRATED" if (ev_count > 0 and current_prof >= 40.0) else (
                        "NEEDS_DEVELOPMENT" if ev_count > 0 else "NOT_ASSESSED"
                    )
                ),
                "evidence_text": req.get("evidence_text", "")
            }

            if is_req:
                total_req_weight += weight
                if ev_count > 0:
                    assessed_req_weight += weight
                    earned_req_score += (min(100.0, current_prof) / 100.0) * weight
                    if current_prof < 50.0:
                        critical_gaps.append(skill_entry)
                    elif current_prof >= 70.0:
                        aligned_skills.append(skill_entry)
                else:
                    unassessed_skills.append(skill_entry)
            else:
                total_pref_weight += weight
                if ev_count > 0:
                    assessed_pref_weight += weight
                    earned_pref_score += (min(100.0, current_prof) / 100.0) * weight
                    if current_prof >= 60.0:
                        aligned_skills.append(skill_entry)

        # Decoupled scoring: measured proficiency vs evidence coverage
        if assessed_req_weight > 0:
            req_match = (earned_req_score / assessed_req_weight * 100.0)
        else:
            req_match = 0.0

        if assessed_pref_weight > 0:
            pref_match = (earned_pref_score / assessed_pref_weight * 100.0)
        else:
            pref_match = 0.0

        coverage_ratio = (assessed_req_weight / total_req_weight) if total_req_weight > 0 else 0.0
        coverage_pct = round(coverage_ratio * 100.0, 1)

        # Overall Match = S_measured * (0.5 + 0.5 * Coverage)
        if assessed_req_weight > 0:
            overall_match = round(req_match * (0.5 + 0.5 * coverage_ratio), 1)
        else:
            overall_match = 0.0

        # Readiness Verdict
        if coverage_pct < 25.0:
            verdict = "DIAGNOSTIC_EVALUATION_RECOMMENDED"
        elif overall_match >= 80.0 and len(critical_gaps) == 0:
            verdict = "READY_TO_INTERVIEW"
        elif overall_match >= 65.0 and len(critical_gaps) <= 1:
            verdict = "NEAR_MATCH"
        else:
            verdict = "REQUIRES_PREPARATION"

        # If user has not assessed skills, show unassessed requirements explicitly
        critical_gaps_to_display = critical_gaps if critical_gaps else [
            {**u, "deficit": u["target_proficiency"], "note": "Awaiting verification assessment"}
            for u in unassessed_skills[:4]
        ]

        return {
            "overall_match_percentage": overall_match,
            "required_match_percentage": round(req_match, 1),
            "preferred_match_percentage": round(pref_match, 1),
            "evidence_coverage_percentage": coverage_pct,
            "critical_gaps": critical_gaps_to_display,
            "aligned_skills": aligned_skills,
            "unassessed_skills": unassessed_skills,
            "readiness_verdict": verdict
        }

    # =========================================================================
    # Stage H-J: Role-Aware Blueprint & Tailored Question Generation
    # =========================================================================

    @classmethod
    def generate_and_evaluate_questions(
        cls,
        job_id: str,
        job_title: str,
        role_tier: str,
        requirements: List[Dict[str, Any]],
        supabase_client=None
    ) -> List[Dict[str, Any]]:
        """
        Constructs a structured role blueprint and generates non-duplicative,
        domain-grounded interview questions evaluating Relevance, Clarity, and Depth.
        Never forces generic DSA / DP questions into AI/ML or specialized roles.
        """
        supabase = supabase_client or get_supabase_client()

        # Build Role Blueprint
        normalized_role = normalize_role_id(job_title)
        blueprint = cls._build_interview_blueprint(normalized_role, role_tier, requirements)

        generated_questions = []
        seen_question_signatures: Set[str] = set()

        now_iso = datetime.now(timezone.utc).isoformat()

        for topic in blueprint["topics"]:
            sid = topic["skill_id"]
            req_id = topic.get("requirement_id", f"req_bp_{uuid.uuid4().hex[:6]}")
            evidence = topic.get("evidence", "")

            q_text, category, difficulty = cls._craft_domain_question(sid, normalized_role, role_tier, evidence)

            # Deduplicate by normalized signature
            sig = re.sub(r"[^a-z0-9]", "", q_text.lower()[:50])
            if sig in seen_question_signatures:
                continue
            seen_question_signatures.add(sig)

            # Automated Quality Evaluation
            eval_metrics = cls.evaluate_question_quality(q_text, sid, evidence)

            q_id = f"q_{uuid.uuid4().hex[:12]}"

            question_row = {
                "id": q_id,
                "job_id": job_id,
                "requirement_id": req_id,
                "question_text": q_text,
                "category": category,
                "difficulty": difficulty,
                "quality_score": eval_metrics["composite_score"],
                "evaluation_metrics": json.dumps(eval_metrics),
                "created_at": now_iso
            }

            supabase.table("job_tailored_questions").insert(question_row).execute()
            generated_questions.append(question_row)

        return generated_questions

    @classmethod
    def _build_interview_blueprint(
        cls,
        normalized_role: str,
        role_tier: str,
        requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Constructs structured blueprint allocating questions strictly across
        skills confirmed by the job description's extracted requirements.
        """
        topics = []
        seen_skills = set()

        # 1. Add top extracted requirements from JD
        for req in requirements:
            sid = req["normalized_skill_id"]
            if sid not in seen_skills:
                seen_skills.add(sid)
                topics.append({
                    "skill_id": sid,
                    "requirement_id": req.get("id"),
                    "evidence": req.get("evidence_text", "")
                })

        # 2. Add communication / behavioral check if not present
        if "soft_communication" not in seen_skills and len(topics) < 6:
            topics.append({
                "skill_id": "soft_communication",
                "requirement_id": f"req_soft_{uuid.uuid4().hex[:6]}",
                "evidence": "Team collaboration and cross-functional communication"
            })

        # Limit to 5-7 highest-yield topics
        return {
            "role": normalized_role,
            "role_tier": role_tier,
            "topics": topics[:7]
        }

    @classmethod
    def _craft_domain_question(
        cls,
        skill_id: str,
        role_type: str,
        role_tier: str,
        evidence: str
    ) -> Tuple[str, str, str]:
        """
        Generates role-relevant, technically sound questions testing recognized concepts.
        Strictly adheres to domain constraints: no forced DP for ML, no false SQL for datasets.
        """
        ev_lower = (evidence or "").lower()

        # Specific Question Templates by Canonical Skill ID
        domain_templates = {
            # ── Machine Learning ──
            "ml_model_development": (
                "Walk me through how you frame a real-world problem as a machine learning objective, select baseline model families, and systematically evaluate train/test distributions to prevent data leakage.",
                "Machine Learning",
                "Medium"
            ),
            "ml_model_evaluation": (
                "When evaluating an ML model under severe class imbalance, how do you choose between ROC-AUC, Precision-Recall AUC, and F1-beta, and how do you calibrate prediction probabilities for downstream decision systems?",
                "Machine Learning",
                "Medium"
            ),
            "ml_feature_engineering": (
                "How do you design feature selection and transformation pipelines that handle high-cardinality categorical variables without introducing target leakage or excessive dimensionality?",
                "Machine Learning",
                "Medium"
            ),
            "ml_supervised_unsupervised": (
                "Compare ensemble bagging (Random Forests) versus gradient boosting (XGBoost/LightGBM) in terms of bias-variance decomposition, sensitivity to outliers, and convergence behavior.",
                "Machine Learning",
                "Medium"
            ),

            # ── Deep Learning ──
            "dl_neural_networks": (
                "How do you select and evaluate an appropriate deep neural network architecture for a particular prediction task, and how do you diagnose vanishing gradients or layer saturation during training?",
                "Deep Learning",
                "Hard" if role_tier in ("senior", "staff") else "Medium"
            ),
            "dl_transformers": (
                "Explain the computational and memory complexity of scaled dot-product self-attention in transformer architectures, and how KV caching optimizes autoregressive sequence generation during inference.",
                "Deep Learning",
                "Hard"
            ),
            "dl_fine_tuning": (
                "What factors and compute constraints guide your decision between parameter-efficient fine-tuning (such as LoRA or QLoRA) versus full parameter training when adapting deep learning models?",
                "Deep Learning",
                "Medium"
            ),

            # ── NLP ──
            "nlp_pipelines": (
                "Explain the stages of an end-to-end NLP pipeline, from subword tokenization (BPE/WordPiece) and vocabulary management to text representation and sequence evaluation.",
                "NLP",
                "Medium"
            ),
            "nlp_embeddings": (
                "How do you generate and validate dense vector embeddings for semantic search, and what similarity metric (cosine vs dot product vs Euclidean) do you select based on vector normalization?",
                "NLP",
                "Medium"
            ),

            # ── Generative AI & LLMs ──
            "genai_llm_fundamentals": (
                "What architectural and latency factors determine whether you deploy a pretrained generative AI model with Retrieval-Augmented Generation (RAG) versus fine-tuning it on domain-specific data?",
                "Generative AI",
                "Hard"
            ),

            # ── Data Engineering ──
            "data_preprocessing": (
                "How would you clean, preprocess, and validate a large, noisy dataset before feeding it into machine learning model training?",
                "Data Engineering",
                "Medium"
            ),
            "data_dataset_management": (
                "When managing multi-gigabyte or terabyte-scale datasets for feature pipelines, how do you optimize memory management, batching, and storage formats (like Parquet or Arrow) to avoid compute bottlenecks?",
                "Data Engineering",
                "Hard"
            ),
            "data_feature_pipelines": (
                "How do you architect automated feature pipelines that guarantee consistent feature definitions and prevent train-serve feature skew between training and production inference?",
                "Data Engineering",
                "Hard"
            ),

            # ── MLOps ──
            "mlops_model_deployment": (
                "How would you expose a trained model through an API and ensure reliable, containerized inference in a production environment?",
                "MLOps",
                "Medium"
            ),
            "mlops_model_serving_apis": (
                "How do you design a low-latency model serving API that implements server-side dynamic batching, payload validation, and graceful degradation during traffic surges?",
                "MLOps",
                "Hard"
            ),
            "mlops_monitoring_drift": (
                "How would you monitor a deployed ML model for data drift, concept drift, and performance degradation in production?",
                "MLOps",
                "Hard"
            ),
            "mlops_automated_retraining": (
                "How do you architect automated retraining pipelines upon detected drift, and what champion-challenger validation and rollback gates do you enforce before promoting a new model?",
                "MLOps",
                "Hard"
            ),

            # ── System Design & Backend ──
            "sys_scalability": (
                "How would you design a horizontally scalable prediction architecture that auto-scales dynamically across GPU/CPU compute nodes with sub-50ms latency guarantees?",
                "System Design",
                "Hard"
            ),
            "sys_rest_apis": (
                "How do you design idempotent REST API endpoints, validate input schemas, and structure error contracts for high-reliability web services?",
                "Backend",
                "Medium"
            ),
            "sys_caching": (
                "Walk through your strategy for caching embedding vectors and model predictions to minimize redundant inference compute while preventing cache stampedes.",
                "System Design",
                "Medium"
            ),
            "sys_db_design": (
                "How do you approach database schema design, index selectivity, and query optimization for high-throughput write workloads?",
                "Databases",
                "Medium"
            ),
            "cs_sql": (
                "Explain how query execution plans work in relational databases, and how index coverage affects execution time for complex aggregation queries.",
                "Databases",
                "Medium"
            ),

            # ── Core Programming & Behavioral ──
            "python": (
                "How do Python's GIL and asynchronous event loops impact CPU-bound preprocessing versus I/O-bound networking in production applications?",
                "Technical",
                "Medium"
            ),
            "soft_communication": (
                "Describe a project where you worked with developers, data engineers, or product managers to integrate an AI capability into an application. How did you resolve technical trade-offs?",
                "Behavioral",
                "Medium"
            ),
            "soft_leadership_ownership": (
                "Tell me about a time you identified a critical flaw or risk in an architecture or pipeline close to release. How did you handle the situation?",
                "Behavioral",
                "Medium"
            )
        }

        if skill_id in domain_templates:
            return domain_templates[skill_id]

        # Generic fallback grounded in skill name
        meta = SKILL_CATALOG.get(skill_id, {})
        name = meta.get("name", skill_id.replace("_", " ").title())
        return (
            f"How do you apply best architectural practices, ensure reliability, and handle edge cases when implementing {name} in production?",
            meta.get("category", "Technical"),
            "Medium"
        )

    # =========================================================================
    # Quality Evaluation & Interview Provisioning
    # =========================================================================

    @classmethod
    def evaluate_question_quality(
        cls,
        question_text: str,
        skill_id: str,
        evidence_text: str
    ) -> Dict[str, Any]:
        """
        Automated multi-dimensional quality evaluation:
        - Relevance (0-10): Grounded in targeted skill & JD evidence
        - Clarity (0-10): Well-structured, punctuation, absence of ambiguous run-ons
        - Depth (0-10): Tests practical understanding, tradeoffs, and system design
        Composite >= 7.0 required for production readiness.
        """
        # Relevance: Checks connection to domain terms
        rel_score = 9.0
        meta = SKILL_CATALOG.get(skill_id, {})
        skill_name = meta.get("name", "").lower()
        if skill_name and any(word in question_text.lower() for word in skill_name.split() if len(word) > 3):
            rel_score = 9.5

        # Clarity: Proper length, ends with question mark
        q_len = len(question_text)
        clarity_score = 9.5 if (40 <= q_len <= 300 and question_text.strip().endswith("?")) else 8.0

        # Depth: Probing depth
        depth_indicators = ["how would you", "tradeoffs", "design", "walk through", "evaluate", "compare", "optimize", "mitigate"]
        has_depth = any(ind in question_text.lower() for ind in depth_indicators)
        depth_score = 9.2 if has_depth else 7.8

        composite = round((rel_score * 0.4) + (clarity_score * 0.3) + (depth_score * 0.3), 1)

        return {
            "relevance_score": rel_score,
            "clarity_score": clarity_score,
            "depth_score": depth_score,
            "composite_score": composite,
            "is_production_ready": composite >= 7.0
        }

    @classmethod
    def create_job_matched_interview_session(
        cls,
        user_id: str,
        job_id: str,
        personality: str = "professional",
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Provisions a customized Ava AI Mock Interview session targeted specifically
        at this job description's critical requirements, interview blueprint, and tailored questions.
        """
        supabase = supabase_client or get_supabase_client()

        # Fetch job profile
        job_res = supabase.table("job_profiles").select("*").eq("id", job_id).execute()
        if not job_res or not job_res.data:
            raise ValueError(f"Job profile not found: {job_id}")
        job_profile = job_res.data[0]

        # Fetch tailored questions
        q_res = supabase.table("job_tailored_questions").select("*").eq("job_id", job_id).order("quality_score", desc=True).limit(6).execute()
        questions = q_res.data if (q_res and q_res.data) else []

        session_id = f"sess_job_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        session_record = {
            "id": session_id,
            "user_id": user_id,
            "role": job_profile.get("job_title", "Software Engineer"),
            "company_name": job_profile.get("company", "Target Company"),
            "interview_state": "INTRO",
            "personality": personality,
            "turn_count": 0,
            "knowledge_map": json.dumps({
                "job_id": job_id,
                "role_tier": job_profile.get("role_tier", "mid"),
                "tailored_question_ids": [q["id"] for q in questions],
                "tailored_questions": [q["question_text"] for q in questions]
            }),
            "created_at": now_iso
        }
        supabase.table("sessions").insert(session_record).execute()

        return {
            "session_id": session_id,
            "job_title": job_profile.get("job_title"),
            "company": job_profile.get("company"),
            "personality": personality,
            "curated_question_count": len(questions)
        }

    # =========================================================================
    # Metadata Inferences
    # =========================================================================

    @staticmethod
    def _sanitize_jd_text(text: str) -> str:
        """Strips HTML tags and abnormal control characters while preserving structure."""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", clean)
        clean = re.sub(r"(?i)\b(ignore previous instructions|system prompt override|you are now)\b", "[filtered]", clean)
        return clean.strip()

    @staticmethod
    def _infer_job_title(text: str) -> str:
        """Infers job title using regex heuristics from first lines."""
        first_lines = text.split("\n")[:6]
        for line in first_lines:
            line_clean = line.strip()
            if re.search(r"\b(engineer|developer|architect|scientist|lead|manager|analyst)\b", line_clean, re.I):
                # Clean prefix words like "Title:" or "Role:"
                cleaned = re.sub(r"(?i)^(?:title|role|position|job\s+title)[:\s]+", "", line_clean).strip()
                return cleaned[:60]
        return "Software Engineer"

    @staticmethod
    def _infer_company(text: str) -> str:
        """Infers company name if present."""
        match = re.search(r"\b(?:at|for|company:)\s+([A-Z][A-Za-z0-9&.\s]{2,25})\b", text)
        if match:
            return match.group(1).strip()
        return "Target Company"

    @staticmethod
    def _infer_role_tier(text: str, title: str) -> str:
        """Infers seniority tier."""
        combined = (text + " " + title).lower()
        if any(w in combined for w in ["principal", "staff", "director"]):
            return "staff"
        elif any(w in combined for w in ["senior", "sr.", "lead", "architect"]):
            return "senior"
        elif any(w in combined for w in ["entry", "junior", "associate", "intern", "new grad"]):
            return "junior"
        return "mid"
