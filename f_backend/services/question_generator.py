"""
QuestionGenerator
=================
Generates constrained, high-yield technical assessment items tailored to target role,
skill domain, and candidate difficulty tier.
Uses Gemini AI with strict JSON schema validation, variation hashes for deduplication,
and domain-specific curated fallback banks for offline and test resilience.
"""

from typing import Dict, List, Optional, Any, Set
import hashlib
import json
import uuid
import logging

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG, normalize_role_id
from services.ai_service import safe_invoke_llm

logger = logging.getLogger("prepfly.question_generator")


# High-Yield Curated Fallback Banks per Engineering Domain
DOMAIN_FALLBACK_BANKS: Dict[str, List[Dict[str, Any]]] = {
    "ai_ml_engineer": [
        {
            "skill_id": "math_probability_statistics",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "What is the foundational difference between Maximum Likelihood Estimation (MLE) and Maximum A Posteriori (MAP) estimation? How does placing a zero-mean Gaussian prior over model parameters mathematically yield Ridge (L2) regularization?",
            "expected_concepts": ["MLE maximizes likelihood P(D|Theta)", "MAP incorporates prior P(Theta) via Bayes rule", "Gaussian prior log-probability produces squared L2 penalty lambda * ||Theta||^2"],
            "rubric": {"likelihood_vs_posterior": 40, "prior_formulation": 30, "l2_derivation": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "ml_model_evaluation",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "You are building a fraud detection model where only 0.1% of transactions are fraudulent (999:1 imbalance). Why is raw accuracy a misleading metric? Which evaluation metrics would you prioritize, and how do Precision-Recall (PR) curves compare to ROC curves in this scenario?",
            "expected_concepts": ["Accuracy paradox under severe class imbalance", "Precision, Recall, and F1/F-beta score", "PR-AUC focuses directly on minority positive class performance", "ROC-AUC distortion by true negative pool"],
            "rubric": {"accuracy_paradox": 30, "pr_vs_roc_auc": 40, "cost_sensitive_metrics": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dl_neural_networks",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain the vanishing and exploding gradient problems encountered when training deep neural networks with backpropagation. What causes them mathematically, and how do residual skip connections (ResNets) mitigate vanishing gradients?",
            "expected_concepts": ["Chain rule repeated Jacobian multiplication", "Activation saturation (sigmoid/tanh derivative < 0.25)", "Residual skip connections create identity gradient highways d(F(x)+x)/dx = dF/dx + 1"],
            "rubric": {"mathematical_cause": 40, "saturation_dynamics": 30, "residual_highway": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dl_transformers",
            "difficulty": "Advanced",
            "question_type": "conceptual",
            "question_text": "Describe the Scaled Dot-Product Attention mechanism in Transformer architectures: Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V. Why is the scaling factor sqrt(d_k) essential, and what is the computational time and space complexity with respect to sequence length N?",
            "expected_concepts": ["Query, Key, Value projections", "Large d_k pushes inner products into softmax vanishing gradient regions", "Scaling preserves unit variance", "O(N^2) pairwise attention time and space complexity"],
            "rubric": {"formula_components": 30, "scaling_factor_rationale": 40, "complexity_analysis": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "genai_llm_fundamentals",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "What causes hallucinations in Large Language Models (LLMs)? Detail three distinct architectural or post-training strategies (such as RAG, Chain-of-Thought prompting, or RLHF/DPO) to reduce hallucination rates in enterprise applications.",
            "expected_concepts": ["Next-token probability sampling without grounded world model", "Retrieval-Augmented Generation (RAG) with vector databases", "Chain-of-Thought reasoning self-consistency", "Alignment via RLHF/DPO preference optimization"],
            "rubric": {"hallucination_root_causes": 30, "rag_grounding": 35, "alignment_and_cot": 35},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_ml_system_design",
            "difficulty": "Advanced",
            "question_type": "system_design",
            "question_text": "Design an end-to-end Machine Learning inference architecture for a real-time recommendation feed serving 50,000 queries per second (QPS). How do you separate candidate retrieval (first stage) from heavy ranking (second stage), and how do you monitor for data and concept drift?",
            "expected_concepts": ["Two-stage funnel: lightweight ANN vector retrieval to heavy cross-encoder ranking", "Sub-50ms latency SLA with caching", "Data drift (covariate shift) vs Concept drift (target relationship decay)"],
            "rubric": {"two_stage_funnel": 40, "caching_and_latency": 30, "drift_monitoring": 30},
            "time_limit_seconds": 240
        }
    ],
    "backend_developer": [
        {
            "skill_id": "sys_rest_apis",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain the concept of Idempotency in REST APIs. Which HTTP methods are inherently idempotent, which are not, and how would you implement idempotency keys for payment processing POST endpoints?",
            "expected_concepts": ["Idempotence: multiple identical requests have same side effects as single request", "GET, PUT, DELETE are idempotent; POST is not", "Unique client-generated idempotency key stored in Redis/DB with atomic conditional lock"],
            "rubric": {"idempotency_definition": 30, "http_method_distinction": 35, "payment_implementation": 35},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "cs_concurrency",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Contrast Optimistic Concurrency Control (OCC) and Pessimistic Concurrency Control (PCC) in relational databases. Under what read/write workload characteristics would you prefer OCC, and how is it typically implemented?",
            "expected_concepts": ["Pessimistic locking (SELECT FOR UPDATE) blocks concurrent writes", "Optimistic concurrency uses version/timestamp checking without blocking reads", "OCC preferred under high read, low write contention", "UPDATE ... WHERE id = :id AND version = :v fails if row modified"],
            "rubric": {"locking_vs_versioning": 40, "workload_tradeoffs": 30, "implementation_details": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_caching",
            "difficulty": "Intermediate",
            "question_type": "system_design",
            "question_text": "Compare the Cache-Aside, Write-Through, and Write-Behind caching patterns. What is a Cache Stampede (Thundering Herd), and how do probabilistic early expiration or mutex locks mitigate it?",
            "expected_concepts": ["Cache-Aside: app queries cache then DB", "Write-Through: synchronous dual write", "Write-Behind: async deferred DB write", "Cache Stampede: multiple concurrent misses hammer DB on key expiration", "Mitigation via distributed locks or probabilistic early renewal"],
            "rubric": {"pattern_comparison": 40, "cache_stampede_cause": 30, "mitigation_strategies": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "cs_dbms",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Break down the four ANSI SQL Transaction Isolation Levels: Read Uncommitted, Read Committed, Repeatable Read, and Serializable. What concurrency anomalies (Dirty Read, Non-Repeatable Read, Phantom Read) does each prevent?",
            "expected_concepts": ["Read Uncommitted permits dirty reads", "Read Committed prevents dirty reads using read locks/MVCC", "Repeatable Read prevents non-repeatable reads", "Serializable prevents phantom reads using range/predicate locks"],
            "rubric": {"isolation_levels": 40, "anomaly_definitions": 30, "mvcc_tradeoffs": 30},
            "time_limit_seconds": 180
        }
    ],
    "frontend_developer": [
        {
            "skill_id": "sys_client_server",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain how the Virtual DOM reconciliation algorithm works in modern UI frameworks (like React). Why is assigning stable, unique 'key' props essential when rendering dynamic lists?",
            "expected_concepts": ["In-memory representation of real DOM tree", "Heuristic O(N) diffing algorithm comparing element types and props", "Avoids expensive browser layout reflows and repaints", "Keys provide persistent element identity across renders"],
            "rubric": {"tree_diffing": 40, "browser_rendering_pipeline": 30, "key_identity_invariants": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_rest_apis",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Contrast Debouncing and Throttling in client-side JavaScript. Provide a concrete production scenario for each, and explain how memory leaks are avoided during component unmounting.",
            "expected_concepts": ["Debounce delays execution until silence period", "Throttle limits execution to fixed rate interval", "Search autocomplete (debounce) vs scroll/resize listener (throttle)", "ClearTimeout / removeEventListener in cleanup hook"],
            "rubric": {"concept_distinction": 40, "production_use_cases": 30, "cleanup_memory_safety": 30},
            "time_limit_seconds": 180
        }
    ],
    "software_development_engineer": [
        {
            "skill_id": "dsa_arrays",
            "difficulty": "Beginner",
            "question_type": "coding",
            "question_text": "Given an array of integers and a target integer, explain how to find two indices that add up to the target in O(N) time and O(N) space. What are the edge cases?",
            "expected_concepts": ["Hash map complement lookup", "Single-pass traversal", "O(N) time and O(N) space complexity", "Duplicate values and no-solution handling"],
            "rubric": {"hash_map_approach": 40, "complexity_analysis": 30, "edge_case_considerations": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "cs_os",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain the four necessary conditions for Deadlock to occur in an operating system (Coffman conditions). Detail how Deadlock Prevention differs from Deadlock Detection and Recovery.",
            "expected_concepts": ["Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait", "Deadlock Prevention invalidates at least one Coffman condition", "Detection uses resource allocation graphs and resolves via preemption/termination"],
            "rubric": {"coffman_conditions": 40, "prevention_strategies": 30, "detection_recovery": 30},
            "time_limit_seconds": 180
        }
    ]
}


class QuestionGenerator:
    """Generates and validates constrained, adaptive diagnostic questions."""

    @classmethod
    def compute_variation_hash(cls, question_text: str) -> str:
        """Computes a 16-character SHA-256 hash of normalized question text."""
        norm = " ".join((question_text or "").strip().lower().split())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def generate_question(
        cls,
        context: Dict[str, Any],
        chat_model=None,
        prior_variation_hashes: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Generates one validated question for given context:
        Context keys: role, skill_id, difficulty, experience_level, previous_performance, job_requirements.
        """
        prior_hashes = prior_variation_hashes or set()
        role_id = normalize_role_id(context.get("role", "software_development_engineer"))
        skill_id = context.get("skill_id", "dsa_arrays")
        difficulty = context.get("difficulty", "Intermediate")
        skill_info = SkillTaxonomyService.get_skill(skill_id) or {}
        skill_name = skill_info.get("name", skill_id)

        # 1. Attempt Gemini Generation if chat_model is available
        if chat_model:
            prompt = (
                f"You are a Principal Engineer creating a diagnostic interview question for a candidate.\n"
                f"Role: {role_id}\n"
                f"Experience: {context.get('experience_level', 'Fresher')}\n"
                f"Target Skill: {skill_name} ({skill_id})\n"
                f"Difficulty Tier: {difficulty}\n"
                f"Candidate Prior Performance: {context.get('previous_performance', 'Neutral')}\n\n"
                f"Requirements:\n"
                f"1. Generate ONE precise, answerable technical question testing deep understanding.\n"
                f"2. Return strict JSON matching this schema:\n"
                f'{{\n'
                f'  "question_text": "Question prompt here...",\n'
                f'  "question_type": "conceptual",\n'
                f'  "expected_concepts": ["concept 1", "concept 2", "concept 3"],\n'
                f'  "rubric": {{"criterion_1": 40, "criterion_2": 30, "criterion_3": 30}},\n'
                f'  "time_limit_seconds": 180\n'
                f'}}\n'
                f"3. Rubric weights MUST sum to 100. Do NOT reveal the full answer in the question."
            )
            try:
                response = safe_invoke_llm(chat_model, prompt)
                if response:
                    raw_text = response.strip()
                    if "{" in raw_text:
                        raw_json = raw_text[raw_text.find("{"):raw_text.rfind("}") + 1]
                        parsed = json.loads(raw_json)
                        q_text = parsed.get("question_text", "").strip()
                        v_hash = cls.compute_variation_hash(q_text)

                        # Validate schema and deduplication
                        if q_text and len(q_text) >= 20 and v_hash not in prior_hashes:
                            rubric = parsed.get("rubric") or {"correctness": 60, "understanding": 40}
                            # Normalize rubric weights to sum to 100
                            total_rub = sum(rubric.values()) or 100
                            normalized_rubric = {k: int(round((w / total_rub) * 100)) for k, w in rubric.items()}
                            
                            return {
                                "id": str(uuid.uuid4()),
                                "question_id": f"q_{skill_id}_{v_hash}",
                                "skill_id": skill_id,
                                "skill_name": skill_name,
                                "domain": skill_info.get("category", "General"),
                                "difficulty": difficulty,
                                "question_text": q_text,
                                "question_type": parsed.get("question_type", "conceptual"),
                                "expected_concepts": parsed.get("expected_concepts") or [],
                                "rubric": normalized_rubric,
                                "variation_hash": v_hash,
                                "time_limit_seconds": parsed.get("time_limit_seconds", 180),
                                "source": "gemini"
                            }
            except Exception as e:
                logger.warning(f"Gemini question generation error, falling back to reviewed bank: {e}")

        # 2. Curated Fallback Selection
        bank = DOMAIN_FALLBACK_BANKS.get(role_id) or DOMAIN_FALLBACK_BANKS.get("software_development_engineer", [])
        # Find item matching skill_id
        matched = [item for item in bank if item["skill_id"] == skill_id]
        if not matched:
            matched = bank

        # Filter out prior hashes if possible
        available = [item for item in matched if cls.compute_variation_hash(item["question_text"]) not in prior_hashes]
        chosen = available[0] if available else matched[0]

        q_text = chosen["question_text"]
        v_hash = cls.compute_variation_hash(q_text)

        return {
            "id": str(uuid.uuid4()),
            "question_id": f"q_{chosen['skill_id']}_{v_hash}",
            "skill_id": chosen["skill_id"],
            "skill_name": (SkillTaxonomyService.get_skill(chosen["skill_id"]) or {}).get("name", chosen["skill_id"]),
            "domain": (SkillTaxonomyService.get_skill(chosen["skill_id"]) or {}).get("category", "General"),
            "difficulty": chosen.get("difficulty", difficulty),
            "question_text": q_text,
            "question_type": chosen.get("question_type", "conceptual"),
            "expected_concepts": chosen.get("expected_concepts", []),
            "rubric": chosen.get("rubric", {"core_concept": 50, "explanation": 50}),
            "variation_hash": v_hash,
            "time_limit_seconds": chosen.get("time_limit_seconds", 180),
            "source": "curated_fallback"
        }

    @classmethod
    def sanitize_for_client(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        """Strips internal scoring rubrics and expected concepts before returning to client."""
        return {
            "id": item.get("id"),
            "question_id": item.get("question_id"),
            "skill_id": item.get("skill_id"),
            "skill_name": item.get("skill_name"),
            "domain": item.get("domain"),
            "difficulty": item.get("difficulty"),
            "question_text": item.get("question_text"),
            "question_type": item.get("question_type"),
            "time_limit_seconds": item.get("time_limit_seconds", 180)
        }

