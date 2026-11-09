"""
Diagnostic Assessment Engine for PrepFly Intelligence.
Generates role-tailored diagnostic evaluations, evaluates concept coverage using rubrics,
and records verifiable evidence into the skill profiling store.
"""

from typing import Dict, List, Optional, Any
import json
import uuid
from datetime import datetime, timezone
from services.skill_taxonomy_service import SkillTaxonomyService, normalize_role_id
from services.skill_profiling_service import SkillProfilingService
from services.answer_classifier import (
    classify_candidate_response,
    CLASS_CORRECT_COMPLETE,
    CLASS_PARTIALLY_CORRECT,
    CLASS_INCORRECT,
    CLASS_NO_ANSWER
)
from services.ai_service import safe_invoke_llm

# Curated High-Yield Diagnostic Question Bank across Categories
DIAGNOSTIC_BANK = [
    {
        "skill_id": "dsa_arrays",
        "question_text": "Given an array of integers, how would you find two numbers that sum up to a specific target in O(N) time? Explain your approach and space-time complexity.",
        "question_type": "conceptual",
        "difficulty": "Beginner",
        "expected_concepts": ["Hash map lookup", "Target minus current complement", "Single-pass traversal", "O(N) time complexity", "O(N) space complexity"],
        "rubric": {
            "full_credit": "Uses hash map with complement lookup in single pass O(N) time and O(N) space.",
            "partial_credit": "Sorts array and uses two pointers O(N log N) time, or misses duplicate handling.",
            "zero_credit": "Brute force O(N^2) or incorrect logic."
        }
    },
    {
        "skill_id": "dsa_dp",
        "question_text": "In Dynamic Programming, what is the fundamental difference between memoization and tabulation? When would you prefer one over the other?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Top-down vs bottom-up", "Recursion stack overhead", "Call stack overflow risk", "Subproblem state ordering", "Space optimization via rolling variables"],
        "rubric": {
            "full_credit": "Clearly contrasts top-down recursion + cache against iterative table building, mentioning recursion limits and space optimization.",
            "partial_credit": "Defines only one approach or confuses top-down with bottom-up.",
            "zero_credit": "Does not explain caching or overlapping subproblems."
        }
    },
    {
        "skill_id": "dsa_trees",
        "question_text": "How do you determine if a binary tree is a valid Binary Search Tree (BST)? Why is checking left < root and right > root alone insufficient?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Global min and max bounds", "Subtree invariant", "Inorder traversal monotonic increase", "Recursive range propagation"],
        "rubric": {
            "full_credit": "Explains that all nodes in a right subtree must exceed all ancestors, requiring min/max bound propagation or monotonic inorder traversal.",
            "partial_credit": "Recognizes local comparison is flawed but cannot articulate the global bound mechanism.",
            "zero_credit": "Claims checking immediate parent-child nodes is sufficient."
        }
    },
    {
        "skill_id": "cs_os",
        "question_text": "Explain the difference between a process and a thread. What memory is shared between threads in the same process, and what is private?",
        "question_type": "conceptual",
        "difficulty": "Beginner",
        "expected_concepts": ["Isolated address space for processes", "Shared heap and code segment", "Private stack and registers per thread", "Context switch overhead difference"],
        "rubric": {
            "full_credit": "Identifies shared heap/globals and private call stacks/registers, contrasting inter-process isolation with lightweight thread concurrency.",
            "partial_credit": "States processes are heavy and threads are light without specifying memory layout (stack vs heap).",
            "zero_credit": "Claims threads have separate address spaces or processes share stacks."
        }
    },
    {
        "skill_id": "cs_dbms",
        "question_text": "In relational databases, what does the 'I' (Isolation) in ACID guarantee, and what anomaly does the 'Read Committed' isolation level prevent?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Concurrent transaction independence", "Dirty reads prevention", "Uncommitted writes visibility", "Non-repeatable reads possibility"],
        "rubric": {
            "full_credit": "Defines isolation and states Read Committed prevents reading uncommitted changes (dirty reads) while still allowing non-repeatable reads.",
            "partial_credit": "Defines ACID but confuses dirty reads with phantom reads.",
            "zero_credit": "Cannot define transaction isolation."
        }
    },
    {
        "skill_id": "sys_caching",
        "question_text": "Describe the Cache-Aside pattern. What problem occurs during a 'cache stampede' (thundering herd), and how can you mitigate it?",
        "question_type": "system_design",
        "difficulty": "Intermediate",
        "expected_concepts": ["Application reads cache first, fetches DB on miss and writes cache", "Simultaneous cache miss flooding backend", "Mutex / single-flight locking", "Probabilistic early expiration (XFetch) or background refresh"],
        "rubric": {
            "full_credit": "Accurately details cache-aside flow and explains mutex locking, single-flight requests, or jittered TTL to stop stampedes.",
            "partial_credit": "Explains cache-aside but does not know how to mitigate cache stampedes.",
            "zero_credit": "Confuses caching with database indexing."
        }
    },
    {
        "skill_id": "sys_rate_limiting",
        "question_text": "How does the Token Bucket algorithm work for API rate limiting? What are its primary advantages over a simple fixed window counter?",
        "question_type": "system_design",
        "difficulty": "Intermediate",
        "expected_concepts": ["Constant token refill rate", "Burst capacity up to bucket size", "Fixed window boundary spike anomaly", "Memory efficiency"],
        "rubric": {
            "full_credit": "Explains token consumption, refill cadence, and how it absorbs bursts without allowing double-limit spikes at window boundaries.",
            "partial_credit": "Describes token refill but does not contrast with fixed window boundary vulnerabilities.",
            "zero_credit": "Incorrect algorithm description."
        }
    },
    {
        "skill_id": "soft_complexity_analysis",
        "question_text": "What is the amortized time complexity of appending an element to a dynamic array (like Python list or Java ArrayList)? Why is it not simply O(N)?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["O(1) amortized", "Occasional O(N) reallocation and copy", "Geometric capacity doubling (factor of 2 or 1.5)", "Aggregate cost distributed across N insertions"],
        "rubric": {
            "full_credit": "States O(1) amortized, explaining that doubling capacity ensures the sum of copy operations over N inserts is bounded by 2N.",
            "partial_credit": "States O(1) without explaining capacity doubling or geometric progression.",
            "zero_credit": "Claims dynamic array appends are strictly O(N) every time."
        }
    },
    {
        "skill_id": "soft_star_framework",
        "question_text": "Describe a challenging technical bug or production failure you resolved. Structure your answer using the STAR method (Situation, Task, Action, Result).",
        "question_type": "behavioral",
        "difficulty": "Intermediate",
        "expected_concepts": ["Clear initial situation", "Specific assigned task", "Concrete individual action taken", "Quantifiable result or learning"],
        "rubric": {
            "full_credit": "Presents a structured narrative clearly separating Situation, Task, personal Action, and measurable Result.",
            "partial_credit": "Describes a bug fix but lacks clear STAR structure or omits quantifiable outcomes.",
            "zero_credit": "Vague generalization without specific incident or personal contribution."
        }
    }
]

# Curated High-Yield Diagnostic Question Bank for AI/ML Engineer & Data Scientist
AIML_DIAGNOSTIC_BANK = [
    {
        "skill_id": "ml_model_development",
        "question_text": "In supervised machine learning, explain the Bias-Variance tradeoff. How do L1 (Lasso) and L2 (Ridge) regularization mathematically prevent overfitting, and how do their weight sparsity outcomes differ?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Underfitting vs overfitting", "Model complexity vs generalization error", "L1 L1-norm absolute sum penalty vs L2 squared Euclidean norm", "L1 yields sparse feature selection corner solutions", "L2 shrinks weights continuously without setting exactly to zero"],
        "rubric": {
            "full_credit": "Accurately details bias vs variance trade-off, formulates the loss penalty terms (absolute vs squared weights), and explains geometric diamond vs circle constraint boundaries leading to sparse zero weights in L1.",
            "partial_credit": "Explains bias vs variance but confuses L1 and L2 weight shrinkage dynamics.",
            "zero_credit": "Incorrect definitions or claims regularization increases overfitting."
        }
    },
    {
        "skill_id": "ml_model_evaluation",
        "question_text": "You are building a fraud detection model where only 0.1% of transactions are fraudulent (999:1 imbalance). Why is raw accuracy a misleading metric? Which evaluation metrics would you prioritize, and how do Precision-Recall (PR) curves compare to ROC curves in this scenario?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Accuracy paradox under severe class imbalance", "Precision, Recall, and F1/F-beta score", "ROC-AUC false positive rate distortion by large true negative pool", "PR-AUC focuses directly on minority positive class performance", "Cost-sensitive threshold tuning"],
        "rubric": {
            "full_credit": "Explains accuracy paradox (predicting all negative gives 99.9% accuracy), articulates why PR-AUC is superior to ROC-AUC when true negatives dominate, and discusses F-beta/recall trade-offs.",
            "partial_credit": "Identifies precision and recall but fails to contrast PR-AUC with ROC-AUC curve behavior under imbalance.",
            "zero_credit": "Suggests relying solely on raw accuracy or confusion matrix diagonal."
        }
    },
    {
        "skill_id": "dl_transformers",
        "question_text": "Describe the Scaled Dot-Product Attention mechanism in Transformer architectures: Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V. Why is the scaling factor sqrt(d_k) essential, and what is the computational time and space complexity with respect to sequence length N?",
        "question_type": "conceptual",
        "difficulty": "Advanced",
        "expected_concepts": ["Query, Key, Value vector projections", "Large d_k pushes dot product magnitudes into softmax vanishing gradient regions", "Scaling preserves unit variance", "O(N^2) time complexity for pairwise token attention", "O(N^2) memory footprint for attention matrix"],
        "rubric": {
            "full_credit": "Correctly states formula and explains that without sqrt(d_k), large inner products saturate softmax resulting in vanishing gradients; states O(N^2 * d) time and O(N^2) space complexity.",
            "partial_credit": "Explains QKV dot product but cannot explain why the variance scales or why gradients vanish.",
            "zero_credit": "Claims attention is O(N) or cannot explain what Q, K, and V represent."
        }
    },
    {
        "skill_id": "genai_llm_fundamentals",
        "question_text": "What causes hallucinations in Large Language Models (LLMs)? Detail three distinct architectural or post-training strategies (such as RAG, Chain-of-Thought prompting, or RLHF/DPO) to reduce hallucination rates in enterprise applications.",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Next-token probability sampling without grounded world model", "Knowledge cutoff and out-of-distribution prompts", "Retrieval-Augmented Generation (RAG) with vector databases", "Chain-of-Thought / reasoning self-consistency", "Alignment via RLHF/DPO reward models and citation verification"],
        "rubric": {
            "full_credit": "Analyzes probabilistic token prediction roots of hallucinations, contrasts parametric vs non-parametric memory, and thoroughly details RAG grounding, CoT decomposition, and RLHF/DPO preference alignment.",
            "partial_credit": "Mentions RAG or prompting but gives superficial or inaccurate explanations of LLM generation dynamics.",
            "zero_credit": "Claims LLMs have deterministic fact databases or fails to describe mitigations."
        }
    },
    {
        "skill_id": "sys_ml_system_design",
        "question_text": "Design an end-to-end Machine Learning inference architecture for a real-time recommendation feed serving 50,000 queries per second (QPS). How do you separate candidate retrieval (first stage) from heavy ranking (second stage), and how do you monitor for data and concept drift?",
        "question_type": "system_design",
        "difficulty": "Advanced",
        "expected_concepts": ["Two-stage architecture: lightweight retrieval (ANN / vector search / collaborative filtering) from millions to hundreds", "Heavy cross-encoder / GBDT / deep ranking on candidate pool", "Low-latency caching (Redis) for precomputed user/item embeddings", "Data drift (Kolmogorov-Smirnov / PSI on feature distribution) vs Concept drift (P(Y|X) performance decay)", "Online shadow deployment / canary testing"],
        "rubric": {
            "full_credit": "Articulates two-stage funnel (retrieval vs ranking) meeting sub-50ms SLA at 50k QPS, features store design, and distinguishes input covariate shift (data drift) from target relationship decay (concept drift).",
            "partial_credit": "Describes a basic ML model deployment without addressing two-stage candidate retrieval or drift monitoring.",
            "zero_credit": "Suggests running a heavy deep neural network over millions of candidate items per real-time request."
        }
    },
    {
        "skill_id": "dl_neural_networks",
        "question_text": "Explain the vanishing and exploding gradient problems encountered when training deep neural networks with backpropagation. What causes them mathematically, and how do residual skip connections (ResNets) and modern initializations (He/Xavier) mitigate them?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Chain rule repeated Jacobian matrix multiplication", "Sigmoid/tanh derivative saturation (< 0.25)", "Weight matrices with eigenvalues > 1 or < 1", "Skip connections create identity gradient highways F(x) + x", "He/Xavier variance preservation based on fan-in/fan-out"],
        "rubric": {
            "full_credit": "Clearly breaks down repeated derivative multiplication in backprop, activation saturation, how identity skip connections allow gradients to flow directly without attenuation (d(F(x)+x)/dx = dF/dx + 1), and variance-preserving initialization.",
            "partial_credit": "Understands gradients become small or huge but cannot explain the role of activation saturation or skip connections.",
            "zero_credit": "Confuses gradients with learning rate or loss value."
        }
    },
    {
        "skill_id": "ml_tree_ensembles",
        "question_text": "Compare and contrast Random Forests and Gradient Boosted Decision Trees (GBDT like XGBoost, LightGBM). How do Bagging and Boosting differ in terms of bias and variance reduction, tree independence, and parallelizability?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Bagging (Bootstrap Aggregating) vs Boosting sequential residual fitting", "Random Forest reduces variance of deep low-bias trees", "Boosting reduces bias by iteratively training shallow trees on pseudo-residuals", "Random Forest trees trained independently in parallel", "Gradient boosting is sequential though node splitting can be parallelized"],
        "rubric": {
            "full_credit": "Clearly contrasts bagging (variance reduction, parallel independent trees) with boosting (bias reduction, sequential residual minimization with gradient descent in function space), noting shrinkage/learning rate and regularization.",
            "partial_credit": "Knows both use decision trees but confuses bias vs variance reduction or claims boosting is parallelizable across trees.",
            "zero_credit": "Cannot differentiate Random Forest from individual decision trees."
        }
    },
    {
        "skill_id": "math_probability_statistics",
        "question_text": "What is the foundational difference between Maximum Likelihood Estimation (MLE) and Maximum A Posteriori (MAP) estimation in probabilistic modeling? How does placing a Gaussian prior over model parameters relate to Ridge (L2) regression?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["MLE maximizes P(Data | Theta)", "MAP maximizes posterior P(Theta | Data) proportional to P(Data | Theta) * P(Theta)", "Incorporation of explicit prior belief P(Theta)", "Zero-mean Gaussian prior log-probability produces squared weight penalty (Ridge L2)", "Laplace prior produces absolute weight penalty (Lasso L1)"],
        "rubric": {
            "full_credit": "Formulates Bayes rule showing MAP = argmax [log P(D|Theta) + log P(Theta)], and demonstrates that assuming Theta ~ N(0, sigma^2) directly yields the L2 squared penalty term lambda * ||Theta||^2.",
            "partial_credit": "Explains that MAP includes a prior while MLE does not, but cannot link Gaussian prior to L2 regularization.",
            "zero_credit": "Confuses likelihood with probability or claims MLE and MAP are identical."
        }
    }
]

# Curated High-Yield Diagnostic Question Bank for Data Engineer
DATA_ENGINEER_DIAGNOSTIC_BANK = [
    {
        "skill_id": "cs_sql",
        "question_text": "Explain the behavioral difference between the SQL window functions ROW_NUMBER(), RANK(), and DENSE_RANK() when ordering over duplicate values. How does PARTITION BY differ from a standard GROUP BY clause?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["ROW_NUMBER strictly assigns sequential integers", "RANK assigns duplicate ranks and skips subsequent numbers", "DENSE_RANK assigns duplicate ranks without skipping numbers", "PARTITION BY retains individual input rows", "GROUP BY collapses multiple rows into a single aggregated row"],
        "rubric": {
            "full_credit": "Clearly demonstrates tie-handling differences with concrete numeric examples (e.g., 1, 2, 2, 4 vs 1, 2, 2, 3), and contrasts row preservation of window partitions against row collapsing of GROUP BY.",
            "partial_credit": "Explains ROW_NUMBER and RANK but confuses DENSE_RANK or misses the GROUP BY distinction.",
            "zero_credit": "Cannot differentiate SQL ranking functions."
        }
    },
    {
        "skill_id": "sys_db_design",
        "question_text": "In data warehousing, contrast a Star Schema with a Snowflake Schema. When would you prefer columnar storage (like Parquet or ClickHouse) over row-oriented storage (like Postgres) for analytics queries?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Star schema has denormalized dimension tables with single join to fact table", "Snowflake schema normalizes dimensions into sub-dimensions reducing redundancy at cost of joins", "Columnar storage reads only queried columns avoiding I/O for unused fields", "High compression ratio on similar column data types", "OLAP analytical aggregations (SUM, AVG) vs OLTP single-row transactional writes"],
        "rubric": {
            "full_credit": "Thoroughly articulates denormalization trade-offs between Star and Snowflake, and explains vector/column-oriented storage I/O reduction and compression benefits on analytical workloads.",
            "partial_credit": "Defines Star and Snowflake schemas but gives vague or incorrect explanations of columnar storage benefits.",
            "zero_credit": "Confuses fact tables with dimension tables or claims row storage is faster for large analytical aggregations."
        }
    },
    {
        "skill_id": "data_feature_pipelines",
        "question_text": "Compare Batch ETL pipelines with Streaming pipelines (e.g. Lambda vs Kappa architecture). How do streaming systems handle late-arriving or out-of-order data using event-time processing and watermarks?",
        "question_type": "system_design",
        "difficulty": "Intermediate",
        "expected_concepts": ["Event-time vs processing-time semantics", "Watermarks as temporal progress metrics asserting no older data will arrive", "Allowed lateness and side outputs for dead-letter processing", "Lambda architecture dual batch + speed layers", "Kappa architecture single stream processing engine with immutable event replay"],
        "rubric": {
            "full_credit": "Details event-time vs processing-time, explains watermarks as monotonic timestamps signaling window closure, and contrasts Lambda dual-codebase maintenance against Kappa stream-first unification.",
            "partial_credit": "Understands batch vs streaming but cannot articulate how watermarks or windowing operate.",
            "zero_credit": "Confuses streaming with simple polling or cannot explain event-time."
        }
    },
    {
        "skill_id": "sys_message_queues",
        "question_text": "In distributed message streaming (e.g., Apache Kafka), how do topic partitions guarantee message ordering? What causes consumer group rebalancing, and how do you achieve at-least-once vs exactly-once processing semantics?",
        "question_type": "system_design",
        "difficulty": "Intermediate",
        "expected_concepts": ["Strict total order only within a single partition via partition key hashing", "Consumer group partition assignment and heartbeat failure timeouts", "Idempotent producers with sequence IDs and transactional commits", "At-least-once via manual offset commit after processing", "Rebalance stop-the-world vs cooperative sticky assignor"],
        "rubric": {
            "full_credit": "Explains key-based partitioning for per-key ordering, consumer rebalance triggers (heartbeat timeout, consumer scale-up/down), and contrasts manual offset commits with 2-phase transactional exactly-once semantics.",
            "partial_credit": "Understands partitions provide parallelism but claims Kafka guarantees global order across all partitions.",
            "zero_credit": "Confuses Kafka message brokers with relational database tables."
        }
    },
    {
        "skill_id": "sys_sharding_replication",
        "question_text": "Explain the concept of Consistent Hashing in distributed data stores. How does it minimize key remapping when nodes are added or removed, and how do virtual nodes prevent hot-spot imbalances?",
        "question_type": "system_design",
        "difficulty": "Intermediate",
        "expected_concepts": ["Hashing both keys and cache nodes onto a cyclic 0 to 2^32-1 ring", "Key is assigned to the next clockwise node", "Adding/removing a node only remaps K/N keys rather than all keys (mod N reshuffle)", "Virtual nodes (vnodes) assign multiple ring points to each physical server", "Elimination of non-uniform hash ring clustering and hot spots"],
        "rubric": {
            "full_credit": "Accurately details hash ring geometry, demonstrates that adding/removing a node only affects adjacent keys (K/N), and explains how virtual nodes ensure uniform distribution across heterogeneous hardware.",
            "partial_credit": "Describes hash ring but does not explain why standard hash(k) % N fails or how virtual nodes resolve imbalance.",
            "zero_credit": "Cannot explain how keys are mapped to nodes."
        }
    }
]

# Curated High-Yield Diagnostic Question Bank for Frontend Developer & Engineer
FRONTEND_DIAGNOSTIC_BANK = [
    {
        "skill_id": "sys_client_server",
        "question_text": "Explain how the Virtual DOM reconciliation algorithm works in modern UI frameworks (like React). Why is assigning stable, unique 'key' props essential when rendering dynamic lists?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["In-memory representation of real DOM tree", "Heuristic O(N) diffing algorithm comparing element types and props", "Avoids expensive browser layout reflows and repaints", "Keys provide persistent element identity across renders", "Index as key anti-pattern causing state corruption in dynamic reordering"],
        "rubric": {
            "full_credit": "Explains tree diffing heuristics (type comparison, component boundary), batch DOM updates, and demonstrates how unstable/index keys corrupt component state during deletion or reordering.",
            "partial_credit": "Understands Virtual DOM is faster than direct DOM manipulation but cannot explain reconciliation heuristics or key identity.",
            "zero_credit": "Claims Virtual DOM is an actual browser Web API or that keys have no functional purpose."
        }
    },
    {
        "skill_id": "sys_rest_apis",
        "question_text": "Contrast Debouncing and Throttling in client-side JavaScript. Provide a concrete scenario for each (such as a search typeahead vs infinite scroll), and explain how memory leaks are avoided during component unmounting.",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["Debounce delays execution until N milliseconds of silence after last invocation", "Throttle limits execution to at most once per fixed time interval", "Search autocomplete (debounce) vs scroll/resize listener (throttle)", "ClearTimeout / removeEventListener in cleanup / useEffect return function", "Closure memory retention of timer IDs"],
        "rubric": {
            "full_credit": "Clearly contrasts debounce (burst reset) vs throttle (rate limiting), specifies correct production use cases, and details timer clearance in lifecycle unmount hooks to prevent memory leaks.",
            "partial_credit": "Confuses debounce and throttle definitions but recognizes both rate-limit events.",
            "zero_credit": "Cannot differentiate debounce and throttle."
        }
    },
    {
        "skill_id": "cs_networks",
        "question_text": "Detail the Critical Rendering Path of a web browser: from receiving raw HTML bytes to painting pixels on screen. What causes layout (reflow) versus repaint, and how can CSS properties like transform and opacity optimize rendering?",
        "question_type": "conceptual",
        "difficulty": "Intermediate",
        "expected_concepts": ["HTML parsing -> DOM tree construction; CSS parsing -> CSSOM tree construction", "Render Tree combining DOM and CSSOM", "Layout (reflow) computing geometry and coordinates", "Paint filling in pixels, colors, borders", "Compositing on GPU layers avoiding CPU layout/paint for transform and opacity"],
        "rubric": {
            "full_credit": "Outlines DOM -> CSSOM -> Render Tree -> Layout -> Paint -> Composite, distinguishes geometry changes (reflow) from visual changes (repaint), and explains GPU compositor layer isolation.",
            "partial_credit": "Lists steps of rendering path but fails to explain difference between reflow and repaint or GPU acceleration.",
            "zero_credit": "Confuses browser network requests with rendering pipeline."
        }
    },
    {
        "skill_id": "dsa_arrays",
        "question_text": "Given an array of integers, how would you find two numbers that sum up to a specific target in O(N) time? Explain your approach and space-time complexity.",
        "question_type": "conceptual",
        "difficulty": "Beginner",
        "expected_concepts": ["Hash map lookup", "Target minus current complement", "Single-pass traversal", "O(N) time complexity", "O(N) space complexity"],
        "rubric": {
            "full_credit": "Uses hash map with complement lookup in single pass O(N) time and O(N) space.",
            "partial_credit": "Sorts array and uses two pointers O(N log N) time, or misses duplicate handling.",
            "zero_credit": "Brute force O(N^2) or incorrect logic."
        }
    },
    {
        "skill_id": "soft_star_framework",
        "question_text": "Describe a challenging technical bug or production failure you resolved. Structure your answer using the STAR method (Situation, Task, Action, Result).",
        "question_type": "behavioral",
        "difficulty": "Intermediate",
        "expected_concepts": ["Clear initial situation", "Specific assigned task", "Concrete individual action taken", "Quantifiable result or learning"],
        "rubric": {
            "full_credit": "Presents a structured narrative clearly separating Situation, Task, personal Action, and measurable Result.",
            "partial_credit": "Describes a bug fix but lacks clear STAR structure or omits quantifiable outcomes.",
            "zero_credit": "Vague generalization without specific incident or personal contribution."
        }
    }
]

# Role-to-Diagnostic-Bank Mapping
ROLE_DIAGNOSTIC_MAP = {
    "ai_ml_engineer": AIML_DIAGNOSTIC_BANK,
    "data_scientist": AIML_DIAGNOSTIC_BANK,
    "data_engineer": DATA_ENGINEER_DIAGNOSTIC_BANK,
    "frontend_developer": FRONTEND_DIAGNOSTIC_BANK,
    "frontend_engineer": FRONTEND_DIAGNOSTIC_BANK,
    "backend_developer": DIAGNOSTIC_BANK,
    "backend_engineer": DIAGNOSTIC_BANK,
    "software_development_engineer": DIAGNOSTIC_BANK,
}



from local_supabase import get_supabase_client

class AssessmentService:
    """Orchestrates diagnostic assessments, scoring, and skill profiling integration."""

    @classmethod
    def start_diagnostic_assessment(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Creates a new diagnostic assessment session with 5 balanced questions
        covering DSA, CS Fundamentals, System Design, and Interview Skills.
        Supports both (supabase_client, user_id, target_role) and (user_id=..., target_role=...)
        """
        if len(args) >= 2 and not isinstance(args[0], str):
            supabase_client = args[0]
            user_id = args[1]
            target_role = args[2] if len(args) > 2 else kwargs.get("target_role", "Software Development Engineer (General)")
        else:
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            user_id = args[0] if args else kwargs.get("user_id", "")
            target_role = args[1] if len(args) > 1 else kwargs.get("target_role", "Software Development Engineer (General)")

        if not user_id:
            raise ValueError("user_id is required")

        now_iso = datetime.now(timezone.utc).isoformat()
        assessment_id = str(uuid.uuid4())
        role_key = normalize_role_id(target_role)

        # Retrieve prior completed or in-progress assessments for this role to rotate questions across attempts
        attempt_count = 0
        try:
            prev_res = supabase_client.table("assessments").select("id").eq("user_id", user_id).eq("target_role", target_role).execute()
            if prev_res and prev_res.data:
                attempt_count = len(prev_res.data)
        except Exception:
            pass

        question_bank = ROLE_DIAGNOSTIC_MAP.get(role_key, DIAGNOSTIC_BANK)
        n_q = min(5, len(question_bank))
        # Rotate questions deterministically per attempt so retakes present fresh questions
        offset = (attempt_count * 2) % len(question_bank)
        selected_questions = [question_bank[(offset + i) % len(question_bank)] for i in range(n_q)]

        # 1. Insert assessment record
        supabase_client.table("assessments").insert({
            "id": assessment_id,
            "user_id": user_id,
            "title": f"Diagnostic Assessment — {target_role}",
            "assessment_type": "diagnostic",
            "target_role": target_role,
            "status": "in_progress",
            "score": None,
            "total_questions": len(selected_questions),
            "completed_questions": 0,
            "summary": "Diagnostic baseline assessment in progress.",
            "created_at": now_iso
        }).execute()

        # 2. Insert questions
        inserted_questions = []
        for idx, q in enumerate(selected_questions):
            q_id = str(uuid.uuid4())
            q_record = {
                "id": q_id,
                "assessment_id": assessment_id,
                "skill_id": q["skill_id"],
                "question_text": q["question_text"],
                "question_type": q["question_type"],
                "difficulty": q["difficulty"],
                "options": json.dumps(q.get("options") or []),
                "correct_answer": q.get("correct_answer") or "",
                "expected_concepts": json.dumps(q["expected_concepts"]),
                "rubric": json.dumps(q["rubric"]),
                "order_index": idx + 1
            }
            supabase_client.table("assessment_questions").insert(q_record).execute()
            inserted_questions.append({
                "id": q_id,
                "question_id": q_id,
                "skill_id": q["skill_id"],
                "skill_name": (SkillTaxonomyService.get_skill(q["skill_id"]) or {}).get("name", q["skill_id"]),
                "question_text": q["question_text"],
                "question_type": q["question_type"],
                "difficulty": q["difficulty"],
                "options": q.get("options") or [],
                "order_index": idx + 1
            })

        return {
            "id": assessment_id,
            "assessment_id": assessment_id,
            "title": f"Diagnostic Assessment — {target_role}",
            "total_questions": len(selected_questions),
            "questions": inserted_questions,
            "status": "in_progress",
            "created_at": now_iso
        }

    generate_diagnostic_assessment = start_diagnostic_assessment

    @classmethod
    def get_assessment(cls, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Retrieves assessment metadata, questions, and already submitted attempts."""
        if len(args) == 3:
            supabase_client, user_id, assessment_id = args
        elif len(args) == 2:
            if isinstance(args[0], str):
                user_id, assessment_id = args
                supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            else:
                supabase_client, assessment_id = args
                user_id = kwargs.get("user_id")
        elif len(args) == 1:
            assessment_id = args[0]
            user_id = kwargs.get("user_id")
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
        else:
            assessment_id = kwargs.get("assessment_id")
            user_id = kwargs.get("user_id")
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()

        query = supabase_client.table("assessments").select("*").eq("id", assessment_id)
        if user_id:
            query = query.eq("user_id", user_id)
        res = query.execute()
        if not res or not res.data:
            return None
        assessment = res.data[0]

        q_res = supabase_client.table("assessment_questions").select("*").eq("assessment_id", assessment_id).order("order_index").execute()
        questions = q_res.data if (q_res and q_res.data) else []

        attempts_query = supabase_client.table("assessment_attempts").select("*").eq("assessment_id", assessment_id)
        if user_id:
            attempts_query = attempts_query.eq("user_id", user_id)
        att_res = attempts_query.execute()
        attempts = {a["question_id"]: a for a in (att_res.data or [])}

        parsed_questions = []
        for q in questions:
            qid = q["id"]
            meta = SkillTaxonomyService.get_skill(q["skill_id"]) or {}
            parsed_questions.append({
                "id": qid,
                "question_id": qid,
                "skill_id": q["skill_id"],
                "skill_name": meta.get("name", q["skill_id"]),
                "question_text": q["question_text"],
                "question_type": q["question_type"],
                "difficulty": q["difficulty"],
                "options": json.loads(q.get("options") or "[]"),
                "order_index": q.get("order_index", 0),
                "attempt": attempts.get(qid)
            })

        return {
            "id": assessment["id"],
            "assessment_id": assessment["id"],
            "title": assessment["title"],
            "status": assessment["status"],
            "score": assessment.get("score"),
            "total_questions": assessment.get("total_questions", len(parsed_questions)),
            "completed_questions": assessment.get("completed_questions", len(attempts)),
            "summary": assessment.get("summary"),
            "created_at": assessment.get("created_at"),
            "completed_at": assessment.get("completed_at"),
            "questions": parsed_questions
        }

    @classmethod
    def evaluate_and_submit_answers(
        cls,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Evaluates submitted candidate responses against questions & rubrics,
        records verifiable skill evidence, and computes the diagnostic baseline.
        """
        if len(args) >= 4 and not isinstance(args[0], str):
            supabase_client = args[0]
            user_id = args[1]
            assessment_id = args[2]
            submissions = args[3]
        else:
            supabase_client = kwargs.get("supabase_client") or get_supabase_client()
            user_id = args[0] if args else kwargs.get("user_id", "")
            assessment_id = args[1] if len(args) > 1 else kwargs.get("assessment_id", "")
            submissions = args[2] if len(args) > 2 else kwargs.get("submissions") or kwargs.get("answers", [])

        if not user_id or not assessment_id:
            raise ValueError("user_id and assessment_id are required")

        # Convert dict format {qid: answer} to list
        if isinstance(submissions, dict):
            submissions = [{"question_id": qid, "answer": ans} for qid, ans in submissions.items()]

        ass_res = supabase_client.table("assessments").select("*").eq("id", assessment_id).eq("user_id", user_id).execute()
        if not ass_res or not ass_res.data:
            # Try without user_id if mock data
            ass_res = supabase_client.table("assessments").select("*").eq("id", assessment_id).execute()
            if not ass_res or not ass_res.data:
                raise ValueError(f"Assessment {assessment_id} not found")
        assessment = ass_res.data[0]

        q_res = supabase_client.table("assessment_questions").select("*").eq("assessment_id", assessment_id).execute()
        q_map = {q["id"]: q for q in (q_res.data or [])}

        total_score = 0.0
        evaluated_count = 0
        evaluated_results = []
        concept_breakdown = {}
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in submissions:
            qid = item.get("question_id") or item.get("id")
            answer = (item.get("answer") or "").strip()
            q_data = q_map.get(qid)
            if not q_data:
                continue

            skill_id = q_data["skill_id"]
            raw_exp = q_data.get("expected_concepts") or []
            expected_concepts = raw_exp if isinstance(raw_exp, list) else (json.loads(raw_exp) if isinstance(raw_exp, str) else [])
            raw_rub = q_data.get("rubric") or {}
            rubric = raw_rub if isinstance(raw_rub, dict) else (json.loads(raw_rub) if isinstance(raw_rub, str) else {})

            classification, acc_score, dims, rationale = classify_candidate_response(
                question=q_data["question_text"],
                answer=answer,
                category=SkillTaxonomyService.get_skill(skill_id).get("category", "")
            )

            ans_lower = answer.lower()
            demonstrated = [c for c in expected_concepts if any(w in ans_lower for w in c.lower().split() if len(w) > 3)]
            missed = [c for c in expected_concepts if c not in demonstrated]

            concept_ratio = len(demonstrated) / max(1, len(expected_concepts))
            final_score = round(max(0.0, min(100.0, (acc_score * 0.6) + (concept_ratio * 40.0))), 1)
            is_correct = 1 if final_score >= 60.0 else 0

            feedback_text = (
                f"{classification}. Identified concepts: {', '.join(demonstrated) if demonstrated else 'None'}. "
                f"Needs focus on: {', '.join(missed) if missed else 'All core criteria satisfied'}."
            )

            att_id = str(uuid.uuid4())
            att_record = {
                "id": att_id,
                "assessment_id": assessment_id,
                "question_id": qid,
                "user_id": user_id,
                "candidate_answer": answer,
                "is_correct": is_correct,
                "score": final_score,
                "evaluation_result": json.dumps({"classification": classification, "rationale": rationale}),
                "identified_concepts": json.dumps(demonstrated),
                "missing_concepts": json.dumps(missed),
                "misconceptions": json.dumps([classification] if classification in (CLASS_INCORRECT, CLASS_NO_ANSWER) else []),
                "feedback": feedback_text,
                "evaluated_at": now_iso
            }
            supabase_client.table("assessment_attempts").insert(att_record).execute()

            # Record verifiable evidence into SkillProfilingService
            SkillProfilingService.record_evidence(
                supabase_client=supabase_client,
                user_id=user_id,
                skill_id=skill_id,
                source_type="diagnostic_assessment",
                source_id=assessment_id,
                score=final_score,
                demonstrated_concepts=demonstrated,
                missed_concepts=missed,
                misconceptions=[classification] if classification == CLASS_INCORRECT else [],
                notes=f"Diagnostic assessment answer evaluation: {classification}",
                rubric_version="v1"
            )

            total_score += final_score
            evaluated_count += 1
            evaluated_results.append({
                "question_id": qid,
                "skill_id": skill_id,
                "score": final_score,
                "classification": classification,
                "demonstrated_concepts": demonstrated,
                "missed_concepts": missed,
                "feedback": feedback_text
            })
            concept_breakdown[skill_id] = final_score

        avg_score = round(total_score / max(1, evaluated_count), 1)

        summary_text = (
            f"Diagnostic baseline complete. Overall score: {avg_score}/100 across {evaluated_count} questions. "
            f"Demonstrated competence in {sum(1 for r in evaluated_results if r['score'] >= 70)} areas; "
            f"foundational gaps identified in {sum(1 for r in evaluated_results if r['score'] < 50)} areas."
        )

        supabase_client.table("assessments").update({
            "status": "completed",
            "score": avg_score,
            "completed_questions": evaluated_count,
            "summary": summary_text,
            "completed_at": now_iso
        }).eq("id", assessment_id).execute()

        return {
            "id": assessment_id,
            "assessment_id": assessment_id,
            "status": "completed",
            "overall_score": avg_score,
            "concept_breakdown": concept_breakdown,
            "summary": summary_text,
            "results": evaluated_results,
            "evaluated_questions": evaluated_results
        }

    evaluate_attempt = evaluate_and_submit_answers
