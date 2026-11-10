"""
QuestionGenerator
=================
Generates constrained, high-yield, non-duplicate technical assessment items tailored to
target role, skill domain, difficulty tier, and candidate performance history.
Supports:
  - User/assignment/skill/difficulty-scoped generation and caching
  - Normalized text + semantic token-overlap deduplication
  - Up to 3 Gemini retry attempts on duplicate detections
  - Multi-role, multi-skill fallback banks + dynamic taxonomy-grounded synthesis
    so repeated assessments or multi-question probes of the same skill never repeat questions.
"""

from typing import Dict, List, Optional, Any, Set, Sequence
import hashlib
import json
import re
import uuid
import logging

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG, ROLE_REQUIREMENTS, normalize_role_id
from services.ai_service import safe_invoke_llm

logger = logging.getLogger("prepfly.question_generator")


# High-Yield Curated Fallback Banks per Engineering Domain (multiple skills & variants)
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
            "skill_id": "ml_model_development",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain the Bias-Variance tradeoff in supervised machine learning. How do L1 (Lasso) and L2 (Ridge) regularization differ geometrically and in feature weight sparsity?",
            "expected_concepts": ["Underfitting high bias vs overfitting high variance", "L1 absolute value penalty produces sparse zero weights", "L2 squared penalty shrinks weights smoothly"],
            "rubric": {"bias_variance": 35, "l1_sparsity": 35, "l2_shrinkage": 30},
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
            "skill_id": "ml_tree_ensembles",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Contrast Bagging (Random Forests) against Boosting (XGBoost / LightGBM) across bias reduction, variance reduction, tree independence, and sensitivity to noisy outliers.",
            "expected_concepts": ["Random Forest reduces variance via bootstrap aggregating independent trees", "Gradient Boosting reduces bias sequentially by fitting residuals", "Boosting uses shrinkage learning rate and is sensitive to outliers"],
            "rubric": {"bagging_mechanics": 35, "boosting_mechanics": 35, "bias_variance_tradeoff": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "ml_feature_engineering",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "How does data leakage occur during normalization, target encoding, or imputation before cross-validation? Explain the exact pipeline structure needed to guarantee leakage-free evaluation.",
            "expected_concepts": ["Fitting scalers or encoders on full dataset leaks validation statistics", "Compute statistics strictly inside each training fold", "Apply fitted transform only to validation/test fold"],
            "rubric": {"leakage_mechanism": 40, "cv_fold_isolation": 35, "encoding_handling": 25},
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
            "skill_id": "nlp_embeddings",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Compare bi-encoder dense retrieval against cross-encoder reranking for semantic search. What are their latency vs accuracy trade-offs, and how does cosine similarity behave on unnormalized embeddings?",
            "expected_concepts": ["Bi-encoder embeds query and document separately for ANN search", "Cross-encoder scores concatenated pairs with full self-attention for higher accuracy", "Cosine normalizes vector magnitude avoiding norm bias"],
            "rubric": {"bi_vs_cross_encoder": 45, "latency_tradeoff": 30, "cosine_geometry": 25},
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
        },
        {
            "skill_id": "mlops_monitoring_drift",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Distinguish covariate shift (data drift) from concept drift in production ML systems. How do metrics like Population Stability Index (PSI) or KS test alert before ground-truth labels arrive?",
            "expected_concepts": ["Data drift shifts P(X) input distribution", "Concept drift shifts P(Y|X) label relationship", "PSI and Kolmogorov-Smirnov detect input distribution shifts without labels"],
            "rubric": {"drift_distinction": 40, "statistical_detectors": 35, "retraining_triggers": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "ml_python_libraries",
            "difficulty": "Beginner",
            "question_type": "conceptual",
            "question_text": "Why are vectorized NumPy operations orders of magnitude faster than Python for-loops on large arrays? Explain broadcasting rules and contiguous memory stride implications.",
            "expected_concepts": ["Contiguous C-typed memory avoids boxed PyObject overhead", "SIMD vectorized loops run in compiled C", "Broadcasting aligns trailing tensor dimensions without copying"],
            "rubric": {"vectorization_internals": 40, "broadcasting_rules": 30, "memory_layout": 30},
            "time_limit_seconds": 180
        },
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
        },
        {
            "skill_id": "cs_sql",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "How does a B-Tree index accelerate range queries in PostgreSQL, and what is the leftmost prefix rule for composite indexes (a, b, c)? When can an index degrade write throughput?",
            "expected_concepts": ["Balanced sorted tree enables O(log N) lookup and sequential leaf scans", "Composite index (a,b,c) supports filtering on a or (a,b) without leading wildcard", "Each INSERT/UPDATE maintains extra index B-tree pages increasing write amplification"],
            "rubric": {"btree_mechanics": 35, "leftmost_prefix": 35, "write_tradeoff": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_rate_limiting",
            "difficulty": "Intermediate",
            "question_type": "system_design",
            "question_text": "Compare Token Bucket, Leaky Bucket, and Sliding Window Log algorithms for distributed API rate limiting in Redis. Why does a Fixed Window Counter suffer from boundary traffic bursts?",
            "expected_concepts": ["Fixed window allows 2x burst across boundary timestamp", "Token bucket allows controlled bursts up to capacity with steady refill", "Atomic Redis Lua script prevents race conditions across workers"],
            "rubric": {"algorithm_tradeoffs": 40, "boundary_burst": 30, "distributed_atomicity": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_message_queues",
            "difficulty": "Intermediate",
            "question_type": "system_design",
            "question_text": "How do you guarantee at-least-once delivery and idempotent message processing in an event-driven architecture (e.g., Kafka/RabbitMQ) with dead-letter queues?",
            "expected_concepts": ["Manual offset commit after processing avoids message loss", "Transactional Outbox pattern ensures atomic DB + event emission", "Idempotent consumer deduplicates by message ID; DLQ isolates poison pills"],
            "rubric": {"delivery_semantics": 35, "outbox_idempotency": 40, "dlq_handling": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_db_design",
            "difficulty": "Advanced",
            "question_type": "system_design",
            "question_text": "When scaling a write-heavy multi-tenant SQL database beyond a single node, compare vertical partitioning, read replicas, and horizontal sharding by tenant_id. What breaks with cross-shard joins?",
            "expected_concepts": ["Read replicas scale reads with replication lag caveats", "Sharding partitions rows by shard key routing queries", "Cross-shard joins and distributed 2PC transactions add high tail latency"],
            "rubric": {"scaling_strategies": 40, "shard_key_design": 30, "distributed_tradeoffs": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dsa_hashing",
            "difficulty": "Beginner",
            "question_type": "conceptual",
            "question_text": "How do Hash Tables resolve key collisions via chaining vs open addressing, and what happens to amortized O(1) lookup performance if load factor exceeds 0.75 without resizing?",
            "expected_concepts": ["Chaining links colliding entries in buckets; open addressing probes slots", "High load factor causes clustering and O(N) worst-case lookup", "Dynamic resizing rehashes entries at threshold to preserve O(1) amortized lookup"],
            "rubric": {"collision_resolution": 40, "load_factor": 30, "complexity": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_fault_tolerance",
            "difficulty": "Advanced",
            "question_type": "system_design",
            "question_text": "Explain how Circuit Breakers (Closed, Open, Half-Open states) and exponential backoff with jitter prevent cascading failures across downstream microservices.",
            "expected_concepts": ["Circuit breaker fast-fails when error rate crosses threshold", "Half-open probes recovery with bounded test traffic", "Exponential backoff with random jitter spreads retry storms"],
            "rubric": {"state_machine": 40, "cascading_prevention": 30, "backoff_jitter": 30},
            "time_limit_seconds": 180
        },
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
        },
        {
            "skill_id": "cs_networks",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Detail the browser Critical Rendering Path from HTML parsing to compositing. What distinguishes layout (reflow) from paint, and why do CSS transform and opacity avoid reflow?",
            "expected_concepts": ["DOM and CSSOM build Render Tree", "Layout computes box geometry; Paint rasterizes pixels", "Transform and opacity run directly on GPU compositor layer skipping layout and paint"],
            "rubric": {"rendering_stages": 40, "reflow_vs_repaint": 30, "gpu_compositing": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_caching",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain HTTP Cache-Control directives (max-age, stale-while-revalidate, no-store) and ETag / 304 Not Modified revalidation for SPA assets vs dynamic API responses.",
            "expected_concepts": ["Hashed static bundles use long immutable max-age", "ETag validates resource freshness returning 304 with empty body", "no-store prevents persisting sensitive user responses"],
            "rubric": {"cache_directives": 40, "etag_revalidation": 35, "security_boundaries": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dsa_arrays",
            "difficulty": "Beginner",
            "question_type": "coding",
            "question_text": "Given a flat list of UI navigation nodes with parentId references, how do you build a nested tree structure in O(N) time without nested quadratic scans?",
            "expected_concepts": ["Two-pass or single-pass hash map lookup by node id", "Attach each child to parent.children list in O(1)", "O(N) time and O(N) space complexity"],
            "rubric": {"hashmap_indexing": 40, "tree_assembly": 35, "complexity": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "cs_oop",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain JavaScript closures, lexical scoping, and the Event Loop microtask queue (Promises) vs macrotask queue (setTimeout) execution order.",
            "expected_concepts": ["Closures capture lexical outer scope references after parent returns", "Call stack empties before draining entire microtask queue", "Promises run before next macrotask or paint frame"],
            "rubric": {"closures_scope": 35, "event_loop_order": 40, "microtask_starvation": 25},
            "time_limit_seconds": 180
        },
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
            "skill_id": "dsa_hashing",
            "difficulty": "Intermediate",
            "question_type": "coding",
            "question_text": "How would you design an LRU (Least Recently Used) Cache supporting get(key) and put(key, value) both in O(1) worst-case time complexity?",
            "expected_concepts": ["Hash map for O(1) key lookup to node pointer", "Doubly linked list for O(1) move-to-head and tail eviction", "Evict tail node when capacity reached"],
            "rubric": {"data_structures": 40, "o1_operations": 35, "edge_cases": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dsa_trees",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "How do you validate whether a binary tree is a valid Binary Search Tree (BST)? Why is only comparing node.val > node.left.val and node.val < node.right.val insufficient?",
            "expected_concepts": ["Pass recursive min and max range bounds down subtrees", "All descendants in right subtree must exceed ancestors", "Inorder DFS produces strictly increasing sequence in O(N) time"],
            "rubric": {"subtree_invariant": 40, "bound_propagation": 35, "complexity": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dsa_dp",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Contrast Top-Down Memoization against Bottom-Up Tabulation in Dynamic Programming. What two problem properties must hold for DP to apply?",
            "expected_concepts": ["Overlapping subproblems and optimal substructure", "Top-down uses recursion + memo cache; bottom-up iterates dependency order", "Tabulation avoids call stack overflow and enables O(1) rolling space optimization"],
            "rubric": {"dp_properties": 35, "memo_vs_tabulation": 35, "space_optimization": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dsa_graphs",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Compare Breadth-First Search (BFS) and Depth-First Search (DFS) on graphs. How do you detect a cycle in a directed graph vs an undirected graph?",
            "expected_concepts": ["BFS uses queue for shortest unweighted paths; DFS uses stack/recursion", "Directed cycle detection tracks 3 states (unvisited, visiting/on-stack, visited)", "Undirected cycle checks visited neighbor != immediate parent"],
            "rubric": {"bfs_vs_dfs": 35, "directed_cycle": 35, "undirected_cycle": 30},
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
        },
        {
            "skill_id": "cs_dbms",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Explain ACID properties in relational databases and compare B-Tree indexing with full table scans for high-selectivity vs low-selectivity columns.",
            "expected_concepts": ["Atomicity, Consistency, Isolation, Durability via WAL logs", "B-Tree speeds selective queries to O(log N)", "Low-cardinality indexes hurt writes without speeding full scans"],
            "rubric": {"acid_guarantees": 40, "index_selectivity": 35, "write_cost": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "dsa_binary_search",
            "difficulty": "Beginner",
            "question_type": "coding",
            "question_text": "What is the worst-case time complexity of binary search on a sorted array of N elements, and how many comparisons at minimum are needed to find a missing target in an empty array of length 0?",
            "expected_concepts": ["O(log N) time and O(1) iterative space", "Empty array of length 0 requires 0 comparisons (low > high immediately)", "Midpoint overflow safe formula low + (high - low) // 2"],
            "rubric": {"complexity": 40, "empty_zero_boundary": 35, "midpoint_safety": 25},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "sys_caching",
            "difficulty": "Intermediate",
            "question_type": "system_design",
            "question_text": "How does Cache-Aside differ from Write-Through caching, and what causes a cache stampede (thundering herd) on hot key expiration?",
            "expected_concepts": ["Cache-Aside loads lazily on cache miss", "Write-Through updates cache and DB synchronously", "Single-flight locks and jittered TTLs mitigate thundering herd"],
            "rubric": {"caching_patterns": 40, "stampede_cause": 30, "mitigation": 30},
            "time_limit_seconds": 180
        },
        {
            "skill_id": "soft_complexity_analysis",
            "difficulty": "Intermediate",
            "question_type": "conceptual",
            "question_text": "Why is appending to a dynamic array O(1) amortized time complexity rather than O(N), and what happens to amortized cost if capacity grows by a constant +10 instead of doubling?",
            "expected_concepts": ["Geometric doubling bounds total copy work across N appends to O(N)", "Amortized O(1) per append", "Constant linear growth triggers O(N) copies giving O(N^2) total and O(N) amortized"],
            "rubric": {"geometric_growth": 40, "amortized_proof": 35, "linear_growth_pitfall": 25},
            "time_limit_seconds": 180
        },
    ],
}

# Alias compatible roles cleanly
DOMAIN_FALLBACK_BANKS["data_scientist"] = DOMAIN_FALLBACK_BANKS["ai_ml_engineer"]
DOMAIN_FALLBACK_BANKS["full_stack_developer"] = (
    DOMAIN_FALLBACK_BANKS["backend_developer"][:5] + DOMAIN_FALLBACK_BANKS["frontend_developer"][:5]
)
DOMAIN_FALLBACK_BANKS["data_engineer"] = DOMAIN_FALLBACK_BANKS["backend_developer"]
DOMAIN_FALLBACK_BANKS["devops_engineer"] = DOMAIN_FALLBACK_BANKS["backend_developer"]


def _tokenize_for_similarity(text: str) -> Set[str]:
    clean = re.sub(r"[^a-z0-9_]+", " ", (text or "").lower())
    stop = {
        "the", "a", "an", "and", "or", "is", "are", "was", "were", "in", "on", "to",
        "for", "of", "with", "how", "what", "why", "when", "where", "which", "you", "your",
        "do", "does", "would", "can", "explain", "describe", "compare", "contrast",
    }
    words = [w for w in clean.split() if len(w) > 1 and w not in stop]
    bigrams = {f"{words[i]}_{words[i+1]}" for i in range(len(words) - 1)} if len(words) > 1 else set()
    return set(words) | bigrams


class QuestionGenerator:
    """Generates and validates non-duplicate, adaptive diagnostic questions."""

    SIMILARITY_THRESHOLD = 0.72

    @classmethod
    def compute_variation_hash(cls, question_text: str) -> str:
        """Computes a 16-character SHA-256 hash of normalized question text."""
        norm = " ".join(re.sub(r"\s+", " ", (question_text or "").strip().lower()).split())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def compute_context_cache_key(cls, context: Dict[str, Any]) -> str:
        """Unique context signature scoped by user, assignment, skill, difficulty, and turn."""
        sig = (
            f"u={context.get('user_id', '')}|"
            f"a={context.get('assessment_id', '')}|"
            f"r={normalize_role_id(context.get('role', ''))}|"
            f"s={context.get('skill_id', '')}|"
            f"d={context.get('difficulty', 'Intermediate')}|"
            f"t={context.get('turn_index', 1)}|"
            f"p={context.get('previous_performance', 'Neutral')}"
        )
        return hashlib.sha256(sig.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def is_duplicate_question(
        cls,
        question_text: str,
        prior_variation_hashes: Optional[Set[str]] = None,
        prior_question_texts: Optional[Sequence[str]] = None,
    ) -> bool:
        """Detects exact normalized matches and high semantic-overlap paraphrases."""
        q_clean = (question_text or "").strip()
        if not q_clean:
            return True
        v_hash = cls.compute_variation_hash(q_clean)
        if prior_variation_hashes and v_hash in prior_variation_hashes:
            return True
        if prior_question_texts:
            q_tokens = _tokenize_for_similarity(q_clean)
            if not q_tokens:
                return False
            for prev_text in prior_question_texts:
                prev_hash = cls.compute_variation_hash(prev_text)
                if prev_hash == v_hash:
                    return True
                p_tokens = _tokenize_for_similarity(prev_text)
                if not p_tokens:
                    continue
                union = q_tokens | p_tokens
                if union:
                    jaccard = len(q_tokens & p_tokens) / len(union)
                    if jaccard >= cls.SIMILARITY_THRESHOLD:
                        return True
        return False

    @classmethod
    def _normalize_rubric(cls, rubric: Any) -> Dict[str, int]:
        if isinstance(rubric, dict) and rubric:
            numeric_items = {}
            for k, v in rubric.items():
                try:
                    numeric_items[str(k)] = max(1, int(round(float(v))))
                except (TypeError, ValueError):
                    numeric_items[str(k)] = 33
            total = sum(numeric_items.values()) or 100
            normalized = {k: max(1, int(round((w / total) * 100))) for k, w in numeric_items.items()}
            diff = 100 - sum(normalized.values())
            if diff != 0 and normalized:
                first_k = next(iter(normalized))
                normalized[first_k] = max(1, normalized[first_k] + diff)
            return normalized
        return {"technical_accuracy": 50, "conceptual_depth": 30, "tradeoffs_and_edge_cases": 20}

    @classmethod
    def _synthesize_taxonomy_question(
        cls,
        skill_id: str,
        skill_info: Dict[str, Any],
        role_id: str,
        difficulty: str,
        prior_hashes: Set[str],
        prior_texts: Sequence[str],
        turn_index: int = 1,
    ) -> Dict[str, Any]:
        """
        Deterministically synthesizes a unique, domain-authentic technical question anchored
        in SKILL_CATALOG metadata when curated bank variants for a skill are exhausted.
        """
        skill_name = skill_info.get("name") or skill_id.replace("_", " ").title()
        category = skill_info.get("category") or "Engineering Fundamentals"
        desc = (skill_info.get("description") or skill_name).rstrip(".")
        objectives = list(skill_info.get("learning_objectives") or [f"Core principles of {skill_name}"])
        criteria = list(skill_info.get("assessment_criteria") or ["Correctness", "Edge cases", "Complexity"])

        scenario_angles = [
            ("Production Bottleneck", "production traffic or scale constraints"),
            ("Architectural Trade-Off", "comparing competing design choices and failure modes"),
            ("Edge-Case & Complexity Audit", "zero/empty boundary inputs, invariants, and time/space complexity"),
            ("Debugging & Root Cause", "diagnosing subtle faults or silent degradation"),
            ("Design Walkthrough", "end-to-end execution guarantees and observability"),
        ]

        start_idx = max(0, turn_index - 1)
        for offset in range(len(scenario_angles) + 4):
            angle_idx = (start_idx + offset) % len(scenario_angles)
            angle_title, angle_focus = scenario_angles[angle_idx]
            obj = objectives[(turn_index + offset) % len(objectives)]
            crit = criteria[(turn_index + offset) % len(criteria)]

            if difficulty == "Beginner":
                prompt_text = (
                    f"[{angle_title} — {skill_name}] Focusing on {obj.lower()}, explain how {skill_name} works "
                    f"({desc.lower()}) and how you handle {crit.lower()} in {role_id.replace('_', ' ')} tasks?"
                )
            elif difficulty == "Advanced":
                prompt_text = (
                    f"[{angle_title} — {skill_name}] Under {angle_focus}, how would you architect a solution leveraging "
                    f"{skill_name} ({desc.lower()}) to satisfy {obj.lower()} while guarding against {crit.lower()}?"
                )
            else:
                prompt_text = (
                    f"[{angle_title} — {skill_name}] In a {role_id.replace('_', ' ')} system requiring {angle_focus}, "
                    f"how do you apply {skill_name} to achieve {obj.lower()} and validate {crit.lower()}?"
                )
            if offset >= len(scenario_angles):
                prompt_text += f" (Probe variant #{offset + 1})"

            if not cls.is_duplicate_question(prompt_text, prior_hashes, prior_texts):
                v_hash = cls.compute_variation_hash(prompt_text)
                expected = list(dict.fromkeys([*objectives[:3], *criteria[:2], skill_name]))
                return {
                    "id": str(uuid.uuid4()),
                    "question_id": f"q_{skill_id}_{v_hash}_{uuid.uuid4().hex[:6]}",
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "domain": category,
                    "difficulty": difficulty,
                    "question_text": prompt_text,
                    "question_type": "system_design" if "sys_" in skill_id else "conceptual",
                    "expected_concepts": expected,
                    "rubric": {"core_mechanism": 40, "edge_cases_and_criteria": 35, "tradeoffs": 25},
                    "variation_hash": v_hash,
                    "time_limit_seconds": 180,
                    "source": "taxonomy_synthesized",
                }

        # Guaranteed distinct fallback with nonce
        unique_nonce = uuid.uuid4().hex[:6]
        prompt_text = f"[{skill_name} Deep Dive #{unique_nonce}] Explain {desc}, specifically {objectives[0]} and {criteria[0]}."
        v_hash = cls.compute_variation_hash(prompt_text)
        return {
            "id": str(uuid.uuid4()),
            "question_id": f"q_{skill_id}_{v_hash}_{unique_nonce}",
            "skill_id": skill_id,
            "skill_name": skill_name,
            "domain": category,
            "difficulty": difficulty,
            "question_text": prompt_text,
            "question_type": "conceptual",
            "expected_concepts": list(dict.fromkeys([*objectives[:2], *criteria[:2], skill_name])),
            "rubric": {"core_mechanism": 40, "edge_cases_and_criteria": 35, "tradeoffs": 25},
            "variation_hash": v_hash,
            "time_limit_seconds": 180,
            "source": "taxonomy_synthesized",
        }

    @classmethod
    def generate_question(
        cls,
        context: Dict[str, Any],
        chat_model=None,
        prior_variation_hashes: Optional[Set[str]] = None,
        prior_question_texts: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generates one validated, non-duplicate question for given context:
        Context keys: role, skill_id, difficulty, experience_level, previous_performance,
        user_id, assessment_id, turn_index, job_requirements.
        """
        prior_hashes = set(prior_variation_hashes or ())
        prior_texts = list(prior_question_texts or ())
        role_id = normalize_role_id(context.get("role", "software_development_engineer"))
        skill_id = context.get("skill_id", "dsa_arrays")
        difficulty = context.get("difficulty", "Intermediate")
        turn_index = int(context.get("turn_index") or (len(prior_hashes) + 1))
        skill_info = SkillTaxonomyService.get_skill(skill_id) or {}
        skill_name = skill_info.get("name", skill_id.replace("_", " ").title())
        cache_sig = cls.compute_context_cache_key(context)

        # 1. Attempt Gemini Generation with duplicate retry loop if chat_model is available
        if chat_model:
            avoid_block = ""
            if prior_texts:
                recent_snips = "\n".join(f"- {t[:140]}" for t in prior_texts[-6:])
                avoid_block = f"\nPreviously Asked Questions (DO NOT repeat or paraphrase any of these):\n{recent_snips}\n"

            for attempt in range(3):
                retry_hint = (
                    f"\nRetry #{attempt + 1}: Generate a completely different angle/scenario than earlier attempts."
                    if attempt > 0
                    else ""
                )
                prompt = (
                    f"You are a Principal Engineer creating diagnostic question #{turn_index} (context={cache_sig[:10]}).\n"
                    f"Role: {role_id}\n"
                    f"Experience: {context.get('experience_level', 'Fresher')}\n"
                    f"Target Skill: {skill_name} ({skill_id})\n"
                    f"Difficulty Tier: {difficulty}\n"
                    f"Candidate Prior Performance: {context.get('previous_performance', 'Neutral')}\n"
                    f"{avoid_block}{retry_hint}\n"
                    f"Requirements:\n"
                    f"1. Generate ONE precise, answerable technical question specifically assessing '{skill_name}' at '{difficulty}' level.\n"
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
                            q_text = (parsed.get("question_text") or "").strip()
                            if q_text and len(q_text) >= 20 and not cls.is_duplicate_question(q_text, prior_hashes, prior_texts):
                                v_hash = cls.compute_variation_hash(q_text)
                                return {
                                    "id": str(uuid.uuid4()),
                                    "question_id": f"q_{skill_id}_{v_hash}_{uuid.uuid4().hex[:6]}",
                                    "skill_id": skill_id,
                                    "skill_name": skill_name,
                                    "domain": skill_info.get("category", "General"),
                                    "difficulty": difficulty,
                                    "question_text": q_text,
                                    "question_type": parsed.get("question_type", "conceptual"),
                                    "expected_concepts": parsed.get("expected_concepts") or [],
                                    "rubric": cls._normalize_rubric(parsed.get("rubric")),
                                    "variation_hash": v_hash,
                                    "context_cache_key": cache_sig,
                                    "time_limit_seconds": parsed.get("time_limit_seconds", 180),
                                    "source": "gemini",
                                }
                except Exception as e:
                    logger.warning(f"Gemini question generation error (attempt {attempt + 1}/3): {e}")
                    break

        # 2. Curated Role/Cross-Bank Lookup filtered strictly by target skill & non-duplication
        role_bank = list(DOMAIN_FALLBACK_BANKS.get(role_id) or DOMAIN_FALLBACK_BANKS.get("software_development_engineer", []))
        all_banks = list(role_bank)
        for other_role, items in DOMAIN_FALLBACK_BANKS.items():
            if other_role != role_id:
                all_banks.extend(items)

        skill_matched = [item for item in role_bank if item["skill_id"] == skill_id]
        if not skill_matched:
            skill_matched = [item for item in all_banks if item["skill_id"] == skill_id]

        # Prefer matching difficulty first, then non-duplicate within same skill
        diff_matched = [item for item in skill_matched if item.get("difficulty") == difficulty]
        ordered_skill_candidates = diff_matched + [item for item in skill_matched if item not in diff_matched]
        available_for_skill = [
            item for item in ordered_skill_candidates
            if not cls.is_duplicate_question(item["question_text"], prior_hashes, prior_texts)
        ]

        if available_for_skill:
            chosen = available_for_skill[0]
            q_text = chosen["question_text"]
            v_hash = cls.compute_variation_hash(q_text)
            c_info = SkillTaxonomyService.get_skill(chosen["skill_id"]) or skill_info
            return {
                "id": str(uuid.uuid4()),
                "question_id": f"q_{chosen['skill_id']}_{v_hash}_{uuid.uuid4().hex[:6]}",
                "skill_id": chosen["skill_id"],
                "skill_name": c_info.get("name", chosen["skill_id"]),
                "domain": c_info.get("category", "General"),
                "difficulty": chosen.get("difficulty", difficulty),
                "question_text": q_text,
                "question_type": chosen.get("question_type", "conceptual"),
                "expected_concepts": list(chosen.get("expected_concepts", [])),
                "rubric": cls._normalize_rubric(chosen.get("rubric")),
                "variation_hash": v_hash,
                "context_cache_key": cache_sig,
                "time_limit_seconds": chosen.get("time_limit_seconds", 180),
                "source": "curated_fallback",
            }

        # 3. Synthesize unique skill-specific question if skill exists in catalog (supports probing same skill repeatedly without duplicates!)
        if skill_info:
            synthesized = cls._synthesize_taxonomy_question(
                skill_id=skill_id,
                skill_info=skill_info,
                role_id=role_id,
                difficulty=difficulty,
                prior_hashes=prior_hashes,
                prior_texts=prior_texts,
                turn_index=turn_index,
            )
            synthesized["context_cache_key"] = cache_sig
            return synthesized

        # 4. Last-resort unused role bank item before synthesized generic
        unused_role = [
            item for item in role_bank
            if not cls.is_duplicate_question(item["question_text"], prior_hashes, prior_texts)
        ]
        if unused_role:
            chosen = unused_role[0]
            q_text = chosen["question_text"]
            v_hash = cls.compute_variation_hash(q_text)
            c_info = SkillTaxonomyService.get_skill(chosen["skill_id"]) or {}
            return {
                "id": str(uuid.uuid4()),
                "question_id": f"q_{chosen['skill_id']}_{v_hash}_{uuid.uuid4().hex[:6]}",
                "skill_id": chosen["skill_id"],
                "skill_name": c_info.get("name", chosen["skill_id"]),
                "domain": c_info.get("category", "General"),
                "difficulty": chosen.get("difficulty", difficulty),
                "question_text": q_text,
                "question_type": chosen.get("question_type", "conceptual"),
                "expected_concepts": list(chosen.get("expected_concepts", [])),
                "rubric": cls._normalize_rubric(chosen.get("rubric")),
                "variation_hash": v_hash,
                "context_cache_key": cache_sig,
                "time_limit_seconds": chosen.get("time_limit_seconds", 180),
                "source": "curated_fallback",
            }

        return cls._synthesize_taxonomy_question(
            skill_id=skill_id,
            skill_info=skill_info or {"name": skill_id, "category": "General"},
            role_id=role_id,
            difficulty=difficulty,
            prior_hashes=prior_hashes,
            prior_texts=prior_texts,
            turn_index=turn_index,
        )

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
