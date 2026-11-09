"""
Skill Taxonomy & Knowledge Map Service for PrepFly Intelligence.
Provides a normalized, extensible DAG of technical and interview skills,
prerequisites, and role requirement matrices.
"""

from typing import Dict, List, Optional, Any
import json
import logging

logger = logging.getLogger("prepfly.intelligence.taxonomy")

# Standardized Categories
CAT_DSA = "Data Structures and Algorithms"
CAT_CS = "Computer Science Fundamentals"
CAT_SYSTEM_DESIGN = "System Design"
CAT_INTERVIEW_SKILLS = "Interview Skills"
CAT_ML = "Machine Learning"
CAT_DEEP_LEARNING = "Deep Learning"
CAT_NLP = "Natural Language Processing"
CAT_GENAI = "Generative AI & LLMs"
CAT_DATA_ENGINEERING = "Data Engineering"
CAT_MLOPS = "MLOps & Model Deployment"
CAT_MATH_STATS = "Mathematics & Statistics"

# Comprehensive Master Skill Catalog
SKILL_CATALOG: Dict[str, Dict[str, Any]] = {
    # ── DSA ──
    "dsa_arrays": {
        "skill_id": "dsa_arrays",
        "name": "Arrays & Dynamic Arrays",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "Contiguous memory structures, index-based access, and amortized insertions.",
        "learning_objectives": ["Understand memory layout", "Perform in-place operations", "Analyze O(1) random access vs O(N) search"],
        "assessment_criteria": ["Boundary conditions", "Index arithmetic", "Array mutation vs copying"],
        "prerequisites": []
    },
    "dsa_strings": {
        "skill_id": "dsa_strings",
        "name": "Strings & Pattern Matching",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "String immutability, character encoding, and anagram / palindrome detection.",
        "learning_objectives": ["Manipulate string pointers", "Handle ASCII vs Unicode edge cases", "Perform frequency counts"],
        "assessment_criteria": ["Case sensitivity", "Special characters", "Substrings vs subsequences"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_hashing": {
        "skill_id": "dsa_hashing",
        "name": "Hashing & Hash Tables",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "Key-value indexing, hash functions, collision handling, and frequency maps.",
        "learning_objectives": ["Identify O(1) average lookup trade-offs", "Implement frequency maps", "Detect duplicates in single passes"],
        "assessment_criteria": ["Collision understanding", "Load factor implications", "Space-time trade-offs"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_two_pointers": {
        "skill_id": "dsa_two_pointers",
        "name": "Two Pointers Technique",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Converging and parallel pointer traversal for sorted arrays and subarrays.",
        "learning_objectives": ["Optimize O(N^2) searches to O(N)", "Solve meeting-in-the-middle problems", "Detect palindromes"],
        "assessment_criteria": ["Pointer boundary checks", "Sortedness invariants", "Off-by-one errors"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_sliding_window": {
        "skill_id": "dsa_sliding_window",
        "name": "Sliding Window",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Dynamic and fixed-size range tracking over sequential data.",
        "learning_objectives": ["Track window expansion and contraction", "Maintain running state with hash maps", "Solve longest/shortest subarray problems"],
        "assessment_criteria": ["Window contraction conditions", "Running window invariant maintenance", "Zero/empty array edge cases"],
        "prerequisites": ["dsa_arrays", "dsa_hashing"]
    },
    "dsa_binary_search": {
        "skill_id": "dsa_binary_search",
        "name": "Binary Search",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Logarithmic search space reduction over monotonic functions and sorted sequences.",
        "learning_objectives": ["Formulate loop invariants", "Avoid integer overflow in midpoint calculation", "Apply binary search on answer spaces"],
        "assessment_criteria": ["Termination condition (low <= high vs low < high)", "Rotated sorted array handling", "Off-by-one boundary cases"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_linked_lists": {
        "skill_id": "dsa_linked_lists",
        "name": "Linked Lists",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "Singly and doubly linked nodes, pointer manipulation, and cycle detection.",
        "learning_objectives": ["Traverse nodes safely", "Reverse linked lists in-place", "Detect cycles using Floyd's algorithm"],
        "assessment_criteria": ["Null pointer references", "Head and tail manipulation", "Dummy node technique"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_stacks": {
        "skill_id": "dsa_stacks",
        "name": "Stacks & Monotonic Stacks",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "LIFO structures, parentheses parsing, and monotonic next-greater element searches.",
        "learning_objectives": ["Implement LIFO operations", "Apply monotonic stack pattern", "Evaluate nested expressions"],
        "assessment_criteria": ["Empty stack pops", "Monotonicity invariants", "Linear amortized complexity"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_queues": {
        "skill_id": "dsa_queues",
        "name": "Queues & Deques",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "FIFO structures, circular buffers, and sliding window maximums.",
        "learning_objectives": ["Implement FIFO buffering", "Use double-ended queues", "Support BFS exploration"],
        "assessment_criteria": ["Queue underflow/overflow", "Amortized enqueue/dequeue", "Deque ordering"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_trees": {
        "skill_id": "dsa_trees",
        "name": "Binary Trees",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Hierarchical node structures, preorder/inorder/postorder traversals, and maximum depth.",
        "learning_objectives": ["Implement recursive tree traversals", "Calculate tree height and diameter", "Serialize and deserialize trees"],
        "assessment_criteria": ["Base case on null root", "Leaf vs non-leaf handling", "Stack overflow on skewed trees"],
        "prerequisites": ["dsa_recursion"]
    },
    "dsa_bst": {
        "skill_id": "dsa_bst",
        "name": "Binary Search Trees",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Ordered binary trees, insertion, deletion, and validation.",
        "learning_objectives": ["Maintain BST ordering invariant", "Perform O(log N) average searches", "Find lowest common ancestor"],
        "assessment_criteria": ["Range validation (min/max bounds)", "Handling duplicates", "Inorder traversal yielding sorted order"],
        "prerequisites": ["dsa_trees"]
    },
    "dsa_heaps": {
        "skill_id": "dsa_heaps",
        "name": "Heaps & Priority Queues",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Binary min/max heaps, top-K elements, and continuous median tracking.",
        "learning_objectives": ["Understand heapify operations", "Find top-K frequent/largest items", "Coordinate two heaps for streaming medians"],
        "assessment_criteria": ["Heap property maintenance", "O(N log K) bounded heap memory", "Custom comparator functions"],
        "prerequisites": ["dsa_arrays", "dsa_trees"]
    },
    "dsa_graphs": {
        "skill_id": "dsa_graphs",
        "name": "Graphs & Representations",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Adjacency lists, adjacency matrices, directed/undirected graphs, and connected components.",
        "learning_objectives": ["Construct adjacency lists", "Detect cycles in graphs", "Find strongly connected components"],
        "assessment_criteria": ["Visited set tracking", "Handling disconnected graphs", "Directed vs undirected cycle detection"],
        "prerequisites": ["dsa_hashing", "dsa_queues", "dsa_stacks"]
    },
    "dsa_bfs": {
        "skill_id": "dsa_bfs",
        "name": "Breadth-First Search (BFS)",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Level-order traversal and shortest path in unweighted graphs.",
        "learning_objectives": ["Implement queue-driven level traversal", "Calculate minimum steps/transformations", "Conduct multi-source BFS"],
        "assessment_criteria": ["Level boundary separation", "Visited set timing (upon enqueue)", "Infinite loop prevention"],
        "prerequisites": ["dsa_queues", "dsa_graphs"]
    },
    "dsa_dfs": {
        "skill_id": "dsa_dfs",
        "name": "Depth-First Search (DFS)",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Exhaustive exploration, path finding, and topological sorting.",
        "learning_objectives": ["Implement recursive and iterative DFS", "Detect back-edges and cycles", "Perform topological sort via Kahn or DFS"],
        "assessment_criteria": ["Recursion stack depth", "Cycle state (unvisited/visiting/visited)", "Path backtracking cleanup"],
        "prerequisites": ["dsa_recursion", "dsa_graphs"]
    },
    "dsa_recursion": {
        "skill_id": "dsa_recursion",
        "name": "Recursion",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "Recursive decomposition, base cases, and call stack mechanics.",
        "learning_objectives": ["Formulate base cases", "Identify subproblems", "Trace call stack execution"],
        "assessment_criteria": ["Stack overflow prevention", "Correct return bubbling", "Auxiliary stack space analysis"],
        "prerequisites": []
    },
    "dsa_backtracking": {
        "skill_id": "dsa_backtracking",
        "name": "Backtracking",
        "category": CAT_DSA,
        "difficulty": "Advanced",
        "description": "Combinatorial generation, permutations, subsets, and pruning search trees.",
        "learning_objectives": ["Formulate choose-explore-unchoose pattern", "Prune invalid branches early", "Generate valid combinations and permutations"],
        "assessment_criteria": ["State restoration (undo step)", "Duplicate combination handling", "Complexity bounding"],
        "prerequisites": ["dsa_recursion"]
    },
    "dsa_greedy": {
        "skill_id": "dsa_greedy",
        "name": "Greedy Algorithms",
        "category": CAT_DSA,
        "difficulty": "Intermediate",
        "description": "Locally optimal choices leading to global solutions, interval scheduling, and fractional knapsack.",
        "learning_objectives": ["Identify optimal substructure", "Prove greedy choice property", "Solve interval overlapping problems"],
        "assessment_criteria": ["Greedy counter-example awareness", "Sorting prerequisite", "Tie-breaking criteria"],
        "prerequisites": ["dsa_arrays", "dsa_sorting"]
    },
    "dsa_dp": {
        "skill_id": "dsa_dp",
        "name": "Dynamic Programming",
        "category": CAT_DSA,
        "difficulty": "Advanced",
        "description": "Overlapping subproblems, state definition, recurrence relations, memoization, and tabulation.",
        "learning_objectives": [
            "Define minimal state representation",
            "Formulate mathematical recurrence relation",
            "Transform top-down memoization to bottom-up tabulation",
            "Optimize space complexity"
        ],
        "assessment_criteria": [
            "Base case correctness",
            "State transitions without missing variables",
            "Time and space complexity derivation",
            "Tabulation table dimensioning"
        ],
        "prerequisites": ["dsa_recursion", "dsa_arrays", "dsa_hashing"]
    },
    "dsa_sorting": {
        "skill_id": "dsa_sorting",
        "name": "Sorting Algorithms",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "Comparison sorts (QuickSort, MergeSort) and linear sorts (Counting, Radix).",
        "learning_objectives": ["Understand stable vs unstable sorting", "Derive worst and average complexities", "Apply custom sort keys"],
        "assessment_criteria": ["Pivot selection edge cases", "In-place vs auxiliary memory", "Adaptive sorting behavior"],
        "prerequisites": ["dsa_arrays"]
    },
    "dsa_searching": {
        "skill_id": "dsa_searching",
        "name": "Searching Techniques",
        "category": CAT_DSA,
        "difficulty": "Beginner",
        "description": "Linear search, binary search, and hash-based search patterns.",
        "learning_objectives": ["Select appropriate search mechanism for data layout", "Analyze time-space trade-offs"],
        "assessment_criteria": ["Unsorted vs sorted assumptions", "Early termination logic"],
        "prerequisites": ["dsa_arrays"]
    },

    # ── Computer Science Fundamentals ──
    "cs_oop": {
        "skill_id": "cs_oop",
        "name": "Object-Oriented Programming (OOP)",
        "category": CAT_CS,
        "difficulty": "Beginner",
        "description": "Encapsulation, inheritance, polymorphism, abstraction, and SOLID principles.",
        "learning_objectives": ["Apply SOLID design principles", "Distinguish composition over inheritance", "Design clean class interfaces"],
        "assessment_criteria": ["Coupling and cohesion", "Interface segregation", "Liskov substitution understanding"],
        "prerequisites": []
    },
    "cs_os": {
        "skill_id": "cs_os",
        "name": "Operating Systems & Concurrency",
        "category": CAT_CS,
        "difficulty": "Intermediate",
        "description": "Processes vs threads, virtual memory, paging, CPU scheduling, deadlocks, and synchronization.",
        "learning_objectives": ["Explain race conditions and mutexes", "Analyze deadlock necessary conditions", "Describe context switching and paging"],
        "assessment_criteria": ["Locking primitives (mutex vs semaphore)", "Memory virtualization and TLB", "Deadlock detection/prevention"],
        "prerequisites": []
    },
    "cs_dbms": {
        "skill_id": "cs_dbms",
        "name": "Database Management Systems (DBMS)",
        "category": CAT_CS,
        "difficulty": "Intermediate",
        "description": "ACID properties, relational schemas, normal forms, and transaction isolation levels.",
        "learning_objectives": ["Explain ACID guarantees", "Normalize schemas to 3NF/BCNF", "Evaluate dirty reads, non-repeatable reads, phantom reads"],
        "assessment_criteria": ["Isolation levels (Read Committed to Serializable)", "Foreign key cascade rules", "Write-ahead logging (WAL)"],
        "prerequisites": []
    },
    "cs_networks": {
        "skill_id": "cs_networks",
        "name": "Computer Networks",
        "category": CAT_CS,
        "difficulty": "Intermediate",
        "description": "OSI and TCP/IP models, TCP vs UDP, HTTP/HTTPS, DNS resolution, and TLS handshakes.",
        "learning_objectives": ["Trace HTTP request lifecycle", "Explain TCP 3-way handshake and congestion control", "Describe DNS hierarchy"],
        "assessment_criteria": ["TCP flow vs congestion control", "TLS encryption exchange", "WebSocket vs HTTP/2/3"],
        "prerequisites": []
    },
    "cs_sql": {
        "skill_id": "cs_sql",
        "name": "SQL & Query Optimization",
        "category": CAT_CS,
        "difficulty": "Intermediate",
        "description": "Complex joins, aggregations, window functions, and EXPLAIN query plan analysis.",
        "learning_objectives": ["Write multi-table joins and subqueries", "Use window functions (ROW_NUMBER, RANK)", "Diagnose sequential scans"],
        "assessment_criteria": ["JOIN correctness (INNER vs LEFT vs FULL)", "GROUP BY aggregation rules", "INDEX selectivity"],
        "prerequisites": ["cs_dbms"]
    },
    "cs_concurrency": {
        "skill_id": "cs_concurrency",
        "name": "Concurrency & Multithreading",
        "category": CAT_CS,
        "difficulty": "Advanced",
        "description": "Thread pools, locks, atomics, futures, async event loops, and producer-consumer queues.",
        "learning_objectives": ["Implement thread-safe producer-consumer patterns", "Explain memory visibility and volatile", "Contrast async I/O with threads"],
        "assessment_criteria": ["Deadlock avoidance", "Thread starvation", "Lock granularity"],
        "prerequisites": ["cs_os"]
    },

    # ── System Design ──
    "sys_client_server": {
        "skill_id": "sys_client_server",
        "name": "Client-Server Architecture",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Beginner",
        "description": "Stateless servers, separation of concerns, and network protocols.",
        "learning_objectives": ["Design decoupled client-server boundaries", "Manage session state", "Understand latency overhead"],
        "assessment_criteria": ["State management", "Client-side vs server-side rendering trade-offs"],
        "prerequisites": ["cs_networks"]
    },
    "sys_rest_apis": {
        "skill_id": "sys_rest_apis",
        "name": "REST API & Interface Design",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Beginner",
        "description": "HTTP verbs, status codes, idempotency, pagination, and versioning.",
        "learning_objectives": ["Design RESTful resource paths", "Enforce idempotency on mutations", "Structure error payloads"],
        "assessment_criteria": ["Correct HTTP status code selection", "Idempotency-Key implementation", "Cursor vs offset pagination"],
        "prerequisites": ["sys_client_server"]
    },
    "sys_db_design": {
        "skill_id": "sys_db_design",
        "name": "Database Design & Indexing",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Intermediate",
        "description": "B-Tree vs Hash indexes, composite indexes, primary keys, and query optimization.",
        "learning_objectives": ["Select appropriate index columns", "Explain leftmost prefix rule", "Evaluate read vs write overhead"],
        "assessment_criteria": ["Index selectivity", "Covering indexes", "Write amplification"],
        "prerequisites": ["cs_dbms", "cs_sql"]
    },
    "sys_caching": {
        "skill_id": "sys_caching",
        "name": "Caching & Invalidation",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Intermediate",
        "description": "Redis/Memcached, Cache-Aside, Write-Through, Write-Behind, TTL, and eviction policies.",
        "learning_objectives": ["Implement Cache-Aside pattern", "Prevent cache stampede / dogpiling", "Select LRU/LFU eviction"],
        "assessment_criteria": ["Cache invalidation consistency", "Handling cache penetration/breakdown", "TTL sizing"],
        "prerequisites": ["dsa_hashing", "sys_client_server"]
    },
    "sys_load_balancing": {
        "skill_id": "sys_load_balancing",
        "name": "Load Balancing & Reverse Proxies",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Intermediate",
        "description": "L4 vs L7 load balancing, Round Robin, Least Connections, Consistent Hashing, and Health Checks.",
        "learning_objectives": ["Configure L7 reverse proxy routes", "Apply consistent hashing for stateful nodes", "Handle SSL termination"],
        "assessment_criteria": ["Single point of failure mitigation", "Sticky sessions vs statelessness", "Health check timeouts"],
        "prerequisites": ["cs_networks", "sys_client_server"]
    },
    "sys_sharding_replication": {
        "skill_id": "sys_sharding_replication",
        "name": "Database Replication & Sharding",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Advanced",
        "description": "Primary-replica replication, read replicas, horizontal partitioning, shard keys, and rebalancing.",
        "learning_objectives": ["Design shard keys to avoid hotspots", "Handle cross-shard joins and transactions", "Manage replication lag"],
        "assessment_criteria": ["Hotspot shard mitigation", "Consistent hashing topology changes", "Split-brain defense"],
        "prerequisites": ["cs_dbms", "sys_db_design"]
    },
    "sys_scalability": {
        "skill_id": "sys_scalability",
        "name": "High Availability & Scalability",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Advanced",
        "description": "Vertical vs horizontal scaling, CAP theorem, PACELC, and graceful degradation.",
        "learning_objectives": ["Evaluate CAP theorem trade-offs", "Formulate SLOs and SLAs", "Design active-passive vs active-active systems"],
        "assessment_criteria": ["Consistency vs Availability trade-offs", "Circuit breaker implementation", "Bulkhead pattern"],
        "prerequisites": ["sys_load_balancing", "sys_caching"]
    },
    "sys_message_queues": {
        "skill_id": "sys_message_queues",
        "name": "Asynchronous Message Queues",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Intermediate",
        "description": "RabbitMQ, Kafka, Pub/Sub, at-least-once delivery, dead letter queues, and consumer groups.",
        "learning_objectives": ["Decouple synchronous requests via message brokers", "Design idempotent consumers", "Handle backpressure"],
        "assessment_criteria": ["Exactly-once vs at-least-once trade-offs", "Consumer lag monitoring", "Poison message containment"],
        "prerequisites": ["sys_client_server", "cs_concurrency"]
    },
    "sys_rate_limiting": {
        "skill_id": "sys_rate_limiting",
        "name": "Rate Limiting & Throttling",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Intermediate",
        "description": "Token bucket, leaky bucket, fixed window, sliding window log, and distributed counters.",
        "learning_objectives": ["Implement sliding window rate limiting with Redis", "Return standard 429 Retry-After headers", "Protect backend from DDoS"],
        "assessment_criteria": ["Distributed race conditions in counter increments", "Memory footprint of sliding logs", "Tiered IP/user limits"],
        "prerequisites": ["sys_caching", "sys_rest_apis"]
    },
    "sys_fault_tolerance": {
        "skill_id": "sys_fault_tolerance",
        "name": "Fault Tolerance & Disaster Recovery",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Advanced",
        "description": "Retry mechanisms with exponential backoff, circuit breakers, fallbacks, and multi-region failover.",
        "learning_objectives": ["Implement circuit breaker states (Closed, Open, Half-Open)", "Add exponential backoff with jitter", "Plan RTO and RPO"],
        "assessment_criteria": ["Thundering herd prevention via jitter", "Fail-safe defaults", "Cascading failure mitigation"],
        "prerequisites": ["sys_scalability"]
    },
    "sys_ml_system_design": {
        "skill_id": "sys_ml_system_design",
        "name": "Machine Learning System Design & Architecture",
        "category": CAT_SYSTEM_DESIGN,
        "difficulty": "Advanced",
        "description": "End-to-end ML architectures: two-stage recommendation (retrieval + ranking), feature stores, real-time inference vs batch scoring, embeddings vector databases, and feedback loops.",
        "learning_objectives": ["Architect scalable two-stage recommendation systems", "Design online feature stores with low-latency key-value lookups", "Handle cold-start problem and distribution shifts"],
        "assessment_criteria": ["End-to-end latency and throughput budgeting", "Offline-to-online feature consistency", "Vector search scaling"],
        "prerequisites": ["ml_model_development", "sys_scalability"]
    },

    # ── Interview Skills ──
    "soft_problem_understanding": {
        "skill_id": "soft_problem_understanding",
        "name": "Problem Clarification & Scoping",
        "category": CAT_INTERVIEW_SKILLS,
        "difficulty": "Beginner",
        "description": "Clarifying assumptions, verifying input constraints, asking targeted questions before coding.",
        "learning_objectives": ["Ask clarifying questions on input bounds", "Confirm edge conditions before writing code", "State implicit assumptions"],
        "assessment_criteria": ["Inquiring about empty/null inputs", "Checking data scale", "Verifying return format"],
        "prerequisites": []
    },
    "soft_communication": {
        "skill_id": "soft_communication",
        "name": "Technical Communication & Thinking Aloud",
        "category": CAT_INTERVIEW_SKILLS,
        "difficulty": "Beginner",
        "description": "Articulating thought process, active listening, and structuring verbal technical explanations.",
        "learning_objectives": ["Think aloud while designing solutions", "Explain trade-offs clearly", "Incorporate interviewer hints"],
        "assessment_criteria": ["Clear reasoning articulation", "Receptive to feedback", "Concise verbal summaries"],
        "prerequisites": []
    },
    "soft_complexity_analysis": {
        "skill_id": "soft_complexity_analysis",
        "name": "Complexity Analysis (Big-O)",
        "category": CAT_INTERVIEW_SKILLS,
        "difficulty": "Intermediate",
        "description": "Deriving exact time and space complexity, best/worst/average cases, and auxiliary memory.",
        "learning_objectives": ["Derive Big-O time and space mathematically", "Distinguish auxiliary vs total space", "Analyze recursion stack memory"],
        "assessment_criteria": ["Accurate Big-O notation", "Justification of tight upper bounds", "Accounting for hidden framework allocations"],
        "prerequisites": ["dsa_arrays"]
    },
    "soft_edge_cases": {
        "skill_id": "soft_edge_cases",
        "name": "Edge-Case & Boundary Identification",
        "category": CAT_INTERVIEW_SKILLS,
        "difficulty": "Intermediate",
        "description": "Proactively testing solutions against empty inputs, duplicates, single elements, and integer overflows.",
        "learning_objectives": ["Enumerate edge cases before coding", "Dry-run code with boundary inputs", "Handle off-by-one errors"],
        "assessment_criteria": ["Empty collections", "Negative values", "Overflow/underflow considerations"],
        "prerequisites": ["soft_problem_understanding"]
    },
    "soft_star_framework": {
        "skill_id": "soft_star_framework",
        "name": "Behavioral STAR Methodology",
        "category": CAT_INTERVIEW_SKILLS,
        "difficulty": "Intermediate",
        "description": "Structuring behavioral responses using Situation, Task, Action, and Result with quantifiable impact.",
        "learning_objectives": ["Structure stories into crisp STAR phases", "Emphasize personal Action over team generalizations", "Highlight measurable Result"],
        "assessment_criteria": ["Clear situation context", "Specific individual action", "Quantifiable positive outcome"],
        "prerequisites": []
    },
    "soft_leadership_ownership": {
        "skill_id": "soft_leadership_ownership",
        "name": "Ownership, Conflict & Leadership",
        "category": CAT_INTERVIEW_SKILLS,
        "difficulty": "Advanced",
        "description": "Demonstrating customer obsession, bias for action, handling technical disagreements, and ownership.",
        "learning_objectives": ["Discuss technical disagreements constructively", "Show proactive accountability for mistakes", "Demonstrate end-to-end ownership"],
        "assessment_criteria": ["Focus on resolution over blame", "Learning from failures", "Long-term architectural thinking"],
        "prerequisites": ["soft_star_framework"]
    },

    # ── Mathematics & Statistics ──
    "math_linear_algebra": {
        "skill_id": "math_linear_algebra",
        "name": "Linear Algebra for Machine Learning",
        "category": CAT_MATH_STATS,
        "difficulty": "Intermediate",
        "description": "Vector spaces, dot products, matrix decompositions (Eigenvalues, SVD), projections, and tensor operations.",
        "learning_objectives": ["Derive matrix transformations and vector projections", "Understand SVD and spectral decomposition", "Apply linear algebra to dimensionality reduction"],
        "assessment_criteria": ["Eigenvalue/eigenvector derivation", "SVD formulation", "Orthogonality and matrix ranks"],
        "prerequisites": []
    },
    "math_probability_statistics": {
        "skill_id": "math_probability_statistics",
        "name": "Probability & Mathematical Statistics",
        "category": CAT_MATH_STATS,
        "difficulty": "Intermediate",
        "description": "Probability distributions, Bayes' theorem, expectation, variance, Maximum Likelihood Estimation (MLE), hypothesis testing, and confidence intervals.",
        "learning_objectives": ["Derive MLE for common probability distributions", "Design hypothesis tests and compute p-values", "Formulate Bayesian inference models"],
        "assessment_criteria": ["Bayes' theorem applications", "Statistical significance and Type I/II errors", "Central Limit Theorem assumptions"],
        "prerequisites": []
    },

    # ── Machine Learning ──
    "ml_python_libraries": {
        "skill_id": "ml_python_libraries",
        "name": "Python for ML: NumPy & Pandas",
        "category": CAT_ML,
        "difficulty": "Beginner",
        "description": "Vectorized operations with NumPy, Pandas Series and DataFrames, indexing, group-by, broadcasting, and memory efficiency.",
        "learning_objectives": ["Master NumPy vectorization and eliminate slow Python loops", "Perform complex aggregations and joins in Pandas", "Optimize dataframe memory footprints"],
        "assessment_criteria": ["Vectorized operations", "Handling missing values and outliers", "Broadcasting rules"],
        "prerequisites": []
    },
    "ml_model_development": {
        "skill_id": "ml_model_development",
        "name": "Machine Learning Model Development",
        "category": CAT_ML,
        "difficulty": "Intermediate",
        "description": "Designing, training, and iterating on classical and modern ML models from problem framing to baseline.",
        "learning_objectives": ["Formulate ML objectives and loss functions", "Train baseline models", "Prevent overfitting and leakage"],
        "assessment_criteria": ["Feature selection logic", "Train/test split integrity", "Hyperparameter tuning approach"],
        "prerequisites": ["ml_python_libraries"]
    },
    "ml_classical_algorithms": {
        "skill_id": "ml_classical_algorithms",
        "name": "Classical ML: Regression, Classification & SVM",
        "category": CAT_ML,
        "difficulty": "Intermediate",
        "description": "Linear and Logistic Regression, Support Vector Machines (SVM), k-Nearest Neighbors, Naive Bayes, and margin optimization.",
        "learning_objectives": ["Derive gradient descent updates for linear and logistic regression", "Formulate SVM dual margin optimization and kernel trick", "Balance regularization (L1/L2)"],
        "assessment_criteria": ["Mathematical loss derivation", "Kernel functions and hyperplanes", "Regularization shrinkage effects"],
        "prerequisites": ["math_linear_algebra", "math_probability_statistics"]
    },
    "ml_tree_ensembles": {
        "skill_id": "ml_tree_ensembles",
        "name": "Decision Trees, Random Forest & Gradient Boosting",
        "category": CAT_ML,
        "difficulty": "Intermediate",
        "description": "Information gain, Gini impurity, CART, Bagging, Random Forests, AdaBoost, Gradient Boosting, XGBoost, and LightGBM.",
        "learning_objectives": ["Calculate splitting criteria (Gini, Entropy)", "Understand bagging variance reduction vs boosting bias reduction", "Tune hyperparameters in XGBoost/LightGBM"],
        "assessment_criteria": ["Tree splitting mathematics", "Handling missing values and regularization in trees", "Feature importance metrics"],
        "prerequisites": ["ml_classical_algorithms"]
    },
    "ml_clustering_pca": {
        "skill_id": "ml_clustering_pca",
        "name": "Unsupervised Learning: K-Means, DBSCAN & PCA",
        "category": CAT_ML,
        "difficulty": "Intermediate",
        "description": "Centroid-based clustering (K-Means), density-based clustering (DBSCAN), hierarchical clustering, PCA, and t-SNE.",
        "learning_objectives": ["Derive K-Means convergence invariants", "Understand DBSCAN core/border/noise points", "Implement PCA via SVD / Covariance Eigendecomposition"],
        "assessment_criteria": ["Silhouette scores and inertia", "DBSCAN epsilon and min_samples tuning", "Variance explained ratio"],
        "prerequisites": ["math_linear_algebra"]
    },
    "ml_supervised_unsupervised": {
        "skill_id": "ml_supervised_unsupervised",
        "name": "Supervised & Unsupervised Learning",
        "category": CAT_ML,
        "difficulty": "Intermediate",
        "description": "Core algorithms including regression, classification, clustering, dimensionality reduction, and ensemble trees.",
        "learning_objectives": ["Select appropriate model family for data distributions", "Understand bias-variance tradeoffs", "Interpret feature importances"],
        "assessment_criteria": ["Model selection justification", "Clustering metrics", "Ensemble bagging vs boosting"],
        "prerequisites": ["ml_model_development"]
    },
    "ml_model_evaluation": {
        "skill_id": "ml_model_evaluation",
        "name": "Model Evaluation & Validation",
        "category": CAT_ML,
        "difficulty": "Intermediate",
        "description": "Rigorous offline evaluation using ROC-AUC, precision-recall curves, F1-score, calibration, and cross-validation.",
        "learning_objectives": ["Choose metrics aligned with business objectives", "Detect label imbalances and false discovery rates", "Design k-fold strategies"],
        "assessment_criteria": ["Class imbalance handling", "Metric trade-offs", "Statistical significance of validation splits"],
        "prerequisites": ["ml_model_development"]
    },
    "ml_feature_engineering": {
        "skill_id": "ml_feature_engineering",
        "name": "Feature Engineering & Selection",
        "category": CAT_ML,
        "difficulty": "Intermediate",
        "description": "Feature scaling, categorical encoding, polynomial interactions, embeddings, and mutual information selection.",
        "learning_objectives": ["Engineer domain-relevant features", "Prevent data leakage during scaling/encoding", "Select parsimonious feature sets"],
        "assessment_criteria": ["Encoding strategies for high cardinality", "Outlier handling", "Leakage prevention in transformations"],
        "prerequisites": ["ml_model_development"]
    },

    # ── Deep Learning ──
    "dl_neural_networks": {
        "skill_id": "dl_neural_networks",
        "name": "Deep Learning & Neural Architectures",
        "category": CAT_DEEP_LEARNING,
        "difficulty": "Intermediate",
        "description": "Multi-layer perceptrons, backpropagation, activation functions, regularizations (dropout, batchnorm), and optimizers.",
        "learning_objectives": ["Understand backpropagation mathematics", "Mitigate vanishing/exploding gradients", "Select optimizers like Adam/AdamW"],
        "assessment_criteria": ["Gradient flow analysis", "Normalization layer placement", "Learning rate scheduling"],
        "prerequisites": ["ml_model_development"]
    },
    "dl_transformers": {
        "skill_id": "dl_transformers",
        "name": "Transformers & Attention Mechanisms",
        "category": CAT_DEEP_LEARNING,
        "difficulty": "Advanced",
        "description": "Scaled dot-product self-attention, multi-head attention, positional encodings, encoder-decoder architectures, and compute complexity.",
        "learning_objectives": ["Derive self-attention O(N^2) memory and compute complexity", "Explain KV caching during autoregressive decoding", "Compare encoder vs decoder models"],
        "assessment_criteria": ["Attention matrix mechanics", "Positional embeddings", "Decoder causal masking"],
        "prerequisites": ["dl_neural_networks"]
    },
    "dl_fine_tuning": {
        "skill_id": "dl_fine_tuning",
        "name": "Model Training & Fine-Tuning",
        "category": CAT_DEEP_LEARNING,
        "difficulty": "Advanced",
        "description": "Supervised fine-tuning, parameter-efficient fine-tuning (LoRA, QLoRA), transfer learning, and gradient checkpointing.",
        "learning_objectives": ["Implement parameter-efficient adaptation", "Manage GPU memory with gradient accumulation", "Prevent catastrophic forgetting"],
        "assessment_criteria": ["LoRA rank and alpha tuning", "Frozen vs trainable parameter ratios", "Mixed-precision training (FP16/BF16)"],
        "prerequisites": ["dl_neural_networks"]
    },
    "dl_frameworks_pytorch_tensorflow": {
        "skill_id": "dl_frameworks_pytorch_tensorflow",
        "name": "Deep Learning Frameworks: PyTorch & TensorFlow",
        "category": CAT_DEEP_LEARNING,
        "difficulty": "Intermediate",
        "description": "PyTorch tensors, autograd engine, custom nn.Module architectures, dataloaders, GPU tensor memory, and mixed precision.",
        "learning_objectives": ["Build modular PyTorch architectures with custom forward passes", "Implement custom training/eval loops with torch.cuda.amp", "Debug tensor shapes and GPU out-of-memory errors"],
        "assessment_criteria": ["Zero memory leaks in GPU tensors", "Gradient clipping and accumulation", "Autograd graph detachment"],
        "prerequisites": ["dl_neural_networks", "ml_python_libraries"]
    },
    "dl_computer_vision_cnn": {
        "skill_id": "dl_computer_vision_cnn",
        "name": "Computer Vision: CNNs & Spatial Architectures",
        "category": CAT_DEEP_LEARNING,
        "difficulty": "Advanced",
        "description": "2D/3D Convolutions, pooling, receptive fields, residual connections (ResNet), object detection backbones, and vision transformers.",
        "learning_objectives": ["Calculate receptive fields and spatial output dimensions", "Understand skip/residual connections in deep CNNs", "Implement data augmentation pipelines for vision"],
        "assessment_criteria": ["Convolution arithmetic", "Transfer learning with pretrained backbones", "Feature map interpretability"],
        "prerequisites": ["dl_neural_networks"]
    },

    # ── NLP ──
    "nlp_pipelines": {
        "skill_id": "nlp_pipelines",
        "name": "NLP & Text Processing Pipelines",
        "category": CAT_NLP,
        "difficulty": "Intermediate",
        "description": "End-to-end NLP pipelines including tokenization (BPE/WordPiece), normalization, vocabulary construction, and text classification.",
        "learning_objectives": ["Design robust tokenization pipelines", "Handle out-of-vocabulary tokens", "Evaluate NLP sequence models"],
        "assessment_criteria": ["Subword tokenization understanding", "Sequence padding & truncation trade-offs", "Text classification evaluation"],
        "prerequisites": ["ml_model_development"]
    },
    "nlp_embeddings": {
        "skill_id": "nlp_embeddings",
        "name": "Embeddings & Vector Representations",
        "category": CAT_NLP,
        "difficulty": "Intermediate",
        "description": "Dense vector representations, semantic similarity, cosine distance, contrastive learning, and embedding indexing.",
        "learning_objectives": ["Generate dense semantic embeddings", "Evaluate vector similarity metrics", "Optimize embedding retrieval"],
        "assessment_criteria": ["Embedding dimensionality trade-offs", "Cosine similarity vs dot product", "Vector search indexing concepts"],
        "prerequisites": ["nlp_pipelines"]
    },

    # ── Generative AI & LLMs ──
    "genai_llm_fundamentals": {
        "skill_id": "genai_llm_fundamentals",
        "name": "Generative AI & LLM Systems",
        "category": CAT_GENAI,
        "difficulty": "Advanced",
        "description": "Pretrained foundation models, prompting paradigms, retrieval-augmented generation (RAG), and evaluation of generative outputs.",
        "learning_objectives": ["Evaluate pretrained models vs domain fine-tuning", "Design grounded RAG architectures", "Evaluate hallucination and groundedness"],
        "assessment_criteria": ["RAG chunking and re-ranking", "Prompt structure and system instructions", "Generative evaluation benchmarks"],
        "prerequisites": ["dl_transformers"]
    },

    # ── Data Engineering & Preprocessing ──
    "data_preprocessing": {
        "skill_id": "data_preprocessing",
        "name": "Data Cleaning & Preprocessing",
        "category": CAT_DATA_ENGINEERING,
        "difficulty": "Intermediate",
        "description": "Cleaning noisy data, imputing missing values, deduplication, schema validation, and normalization for downstream consumption.",
        "learning_objectives": ["Design reproducible preprocessing pipelines", "Handle missing data without introduction of bias", "Validate distribution shifts"],
        "assessment_criteria": ["Imputation trade-offs", "Data cleaning efficiency", "Pipeline modularity"],
        "prerequisites": []
    },
    "data_dataset_management": {
        "skill_id": "data_dataset_management",
        "name": "Large-Scale Dataset Management",
        "category": CAT_DATA_ENGINEERING,
        "difficulty": "Intermediate",
        "description": "Managing high-volume datasets, partitioning, batch vs streaming ingestion, storage formats (Parquet/Arrow), and dataset versioning.",
        "learning_objectives": ["Manage multi-gigabyte/terabyte datasets in memory and disk", "Optimize storage using columnar formats", "Implement dataset versioning"],
        "assessment_criteria": ["Columnar vs row storage trade-offs", "Memory-efficient data batching", "Data versioning strategies"],
        "prerequisites": ["data_preprocessing"]
    },
    "data_feature_pipelines": {
        "skill_id": "data_feature_pipelines",
        "name": "Feature Pipelines & Quality Validation",
        "category": CAT_DATA_ENGINEERING,
        "difficulty": "Advanced",
        "description": "Building automated ETL and feature engineering pipelines, ensuring training-serving skew prevention and data consistency.",
        "learning_objectives": ["Prevent train-serve feature skew", "Implement data quality assertions", "Automate feature transformation pipelines"],
        "assessment_criteria": ["Feature consistency guarantees", "Automated pipeline orchestration", "Data schema contract testing"],
        "prerequisites": ["data_dataset_management"]
    },

    # ── MLOps & Productionization ──
    "mlops_model_deployment": {
        "skill_id": "mlops_model_deployment",
        "name": "Model Deployment & Productionization",
        "category": CAT_MLOPS,
        "difficulty": "Intermediate",
        "description": "Containerizing ML models, model export formats (ONNX, TorchScript), API encapsulation, and deployment into production environments.",
        "learning_objectives": ["Package models into production containers", "Optimize model inference runtimes", "Expose model predictions via APIs"],
        "assessment_criteria": ["Serialization format trade-offs", "Containerization best practices", "Inference dependencies isolation"],
        "prerequisites": ["ml_model_development"]
    },
    "mlops_model_serving_apis": {
        "skill_id": "mlops_model_serving_apis",
        "name": "Low-Latency Model Serving APIs",
        "category": CAT_MLOPS,
        "difficulty": "Advanced",
        "description": "Exposing models via high-throughput REST/gRPC endpoints, dynamic batching, concurrency handling, and meeting p99 latency SLOs.",
        "learning_objectives": ["Design low-latency prediction endpoints", "Implement server-side dynamic batching", "Handle backpressure and traffic spikes"],
        "assessment_criteria": ["Batching trade-offs vs latency", "REST vs gRPC protocol selection", "GPU resource allocation during inference"],
        "prerequisites": ["mlops_model_deployment", "sys_rest_apis"]
    },
    "mlops_monitoring_drift": {
        "skill_id": "mlops_monitoring_drift",
        "name": "Model Monitoring & Data Drift Detection",
        "category": CAT_MLOPS,
        "difficulty": "Advanced",
        "description": "Tracking live model performance, concept drift, covariate shift, prediction distribution monitoring, and alerting.",
        "learning_objectives": ["Detect covariate shift and concept drift using statistical tests", "Monitor prediction latency and error rates", "Design alerting thresholds for ML systems"],
        "assessment_criteria": ["Statistical drift detection methods (KS-test, PSI)", "Ground-truth delay handling", "Actionable alerting design"],
        "prerequisites": ["mlops_model_deployment"]
    },
    "mlops_automated_retraining": {
        "skill_id": "mlops_automated_retraining",
        "name": "Automated Model Retraining & Rollback",
        "category": CAT_MLOPS,
        "difficulty": "Advanced",
        "description": "Triggering automated model retraining pipelines upon detected drift, champion-challenger validation, canary deployments, and safe rollback.",
        "learning_objectives": ["Orchestrate automated retraining triggers", "Validate shadow/canary models against production champions", "Execute safe automated rollbacks"],
        "assessment_criteria": ["Champion-challenger gating criteria", "Canary traffic splitting", "Safe rollback protocols"],
        "prerequisites": ["mlops_monitoring_drift"]
    }
}

# Role Requirements Matrices
# Supported Roles:
# 1. Software Development Engineer (SDE 1 / SDE 2)
# 2. Frontend Developer
# 3. Backend Developer
# 4. Full Stack Developer
# 5. AI/ML Engineer
# 6. Data Engineer
# 7. Data Analyst

ROLE_REQUIREMENTS: Dict[str, Dict[str, float]] = {
    "software_development_engineer": {
        "dsa_arrays": 1.0, "dsa_strings": 0.9, "dsa_hashing": 1.0, "dsa_two_pointers": 0.9,
        "dsa_sliding_window": 0.9, "dsa_binary_search": 0.9, "dsa_linked_lists": 0.8,
        "dsa_stacks": 0.8, "dsa_queues": 0.8, "dsa_trees": 1.0, "dsa_bst": 0.9,
        "dsa_heaps": 0.8, "dsa_graphs": 0.9, "dsa_bfs": 0.9, "dsa_dfs": 0.9,
        "dsa_recursion": 0.9, "dsa_backtracking": 0.8, "dsa_dp": 1.0, "dsa_sorting": 0.8,
        "cs_oop": 0.8, "cs_os": 0.8, "cs_dbms": 0.8, "cs_networks": 0.7, "cs_sql": 0.8,
        "sys_client_server": 0.7, "sys_rest_apis": 0.7, "sys_caching": 0.8, "sys_load_balancing": 0.7,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_complexity_analysis": 1.0,
        "soft_edge_cases": 1.0, "soft_star_framework": 0.9, "soft_leadership_ownership": 0.8
    },
    "frontend_developer": {
        "dsa_arrays": 0.9, "dsa_strings": 0.9, "dsa_hashing": 0.9, "dsa_two_pointers": 0.7,
        "dsa_trees": 0.7, "dsa_recursion": 0.7, "dsa_sorting": 0.7,
        "cs_oop": 0.8, "cs_networks": 0.9,
        "sys_client_server": 1.0, "sys_rest_apis": 1.0, "sys_caching": 0.9, "sys_rate_limiting": 0.7,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_complexity_analysis": 0.8,
        "soft_edge_cases": 0.9, "soft_star_framework": 0.9, "soft_leadership_ownership": 0.8
    },
    "backend_developer": {
        "dsa_arrays": 0.9, "dsa_hashing": 1.0, "dsa_binary_search": 0.8, "dsa_trees": 0.8,
        "dsa_graphs": 0.8, "dsa_bfs": 0.8, "dsa_dfs": 0.8, "dsa_recursion": 0.8, "dsa_dp": 0.8,
        "cs_oop": 0.9, "cs_os": 0.9, "cs_dbms": 1.0, "cs_networks": 0.9, "cs_sql": 1.0, "cs_concurrency": 0.9,
        "sys_client_server": 1.0, "sys_rest_apis": 1.0, "sys_db_design": 1.0, "sys_caching": 1.0,
        "sys_load_balancing": 0.9, "sys_sharding_replication": 0.9, "sys_scalability": 0.9,
        "sys_message_queues": 0.9, "sys_rate_limiting": 0.9, "sys_fault_tolerance": 0.9,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_complexity_analysis": 0.9,
        "soft_edge_cases": 1.0, "soft_star_framework": 0.9, "soft_leadership_ownership": 0.8
    },
    "full_stack_developer": {
        "dsa_arrays": 0.9, "dsa_strings": 0.8, "dsa_hashing": 0.9, "dsa_trees": 0.8, "dsa_graphs": 0.7,
        "cs_oop": 0.9, "cs_dbms": 0.9, "cs_networks": 0.9, "cs_sql": 0.9,
        "sys_client_server": 1.0, "sys_rest_apis": 1.0, "sys_db_design": 0.9, "sys_caching": 0.9,
        "sys_load_balancing": 0.8, "sys_message_queues": 0.8,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_complexity_analysis": 0.9,
        "soft_edge_cases": 0.9, "soft_star_framework": 0.9, "soft_leadership_ownership": 0.8
    },
    "ai_ml_engineer": {
        "ml_python_libraries": 1.0, "math_linear_algebra": 0.9, "math_probability_statistics": 0.9,
        "ml_model_development": 1.0, "ml_classical_algorithms": 0.9, "ml_tree_ensembles": 0.9,
        "ml_clustering_pca": 0.8, "ml_model_evaluation": 0.9, "ml_feature_engineering": 0.9,
        "dl_neural_networks": 1.0, "dl_frameworks_pytorch_tensorflow": 0.9, "dl_transformers": 0.9,
        "dl_fine_tuning": 0.9, "dl_computer_vision_cnn": 0.7, "nlp_pipelines": 0.8, "nlp_embeddings": 0.8,
        "genai_llm_fundamentals": 0.9, "data_preprocessing": 0.9, "data_dataset_management": 0.8,
        "sys_ml_system_design": 1.0, "mlops_model_deployment": 0.9, "mlops_model_serving_apis": 0.8,
        "mlops_monitoring_drift": 0.8, "mlops_automated_retraining": 0.8,
        "cs_sql": 0.7, "dsa_arrays": 0.35, "dsa_hashing": 0.35,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_complexity_analysis": 0.8,
        "soft_star_framework": 0.8
    },
    "data_scientist": {
        "ml_python_libraries": 1.0, "math_probability_statistics": 1.0, "math_linear_algebra": 0.9,
        "ml_classical_algorithms": 1.0, "ml_tree_ensembles": 1.0, "ml_model_evaluation": 1.0,
        "ml_feature_engineering": 1.0, "ml_clustering_pca": 0.9, "ml_model_development": 0.9,
        "cs_sql": 1.0, "data_preprocessing": 1.0, "data_dataset_management": 0.8, "cs_dbms": 0.8,
        "dl_neural_networks": 0.7, "nlp_pipelines": 0.7, "sys_ml_system_design": 0.7,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_star_framework": 0.9
    },
    "data_engineer": {
        "data_collection_cleaning": 1.0, "data_preprocessing": 1.0,
        "data_dataset_management": 1.0, "data_feature_pipelines": 1.0,
        "cs_sql": 1.0, "cs_dbms": 1.0, "sys_db_design": 1.0,
        "sys_message_queues": 1.0, "sys_sharding_replication": 0.9, "sys_scalability": 0.9,
        "cs_concurrency": 0.9, "cs_os": 0.8, "ml_python_libraries": 0.8,
        "dsa_arrays": 0.7, "dsa_hashing": 0.8, "dsa_trees": 0.6,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0
    },
    "devops_engineer": {
        "cs_os": 1.0, "cs_networks": 1.0, "sys_scalability": 1.0, "sys_load_balancing": 1.0,
        "sys_fault_tolerance": 1.0, "sys_rate_limiting": 0.8, "sys_caching": 0.8, "sys_message_queues": 0.8,
        "mlops_model_deployment": 0.8, "mlops_monitoring_drift": 0.8, "cs_concurrency": 0.8,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_star_framework": 0.8
    },
    "data_analyst": {
        "cs_sql": 1.0, "cs_dbms": 1.0, "math_probability_statistics": 1.0,
        "ml_python_libraries": 0.9, "data_preprocessing": 0.9,
        "dsa_arrays": 0.7, "dsa_strings": 0.7, "dsa_hashing": 0.8, "dsa_sorting": 0.7,
        "sys_client_server": 0.6, "sys_rest_apis": 0.7,
        "soft_problem_understanding": 1.0, "soft_communication": 1.0, "soft_complexity_analysis": 0.7,
        "soft_edge_cases": 0.8, "soft_star_framework": 0.9, "soft_leadership_ownership": 0.7
    }
}


def normalize_role_id(role_name: str) -> str:
    """Maps human role names to normalized catalog keys."""
    r = (role_name or "").lower().strip()
    if any(k in r for k in ("ai", "ml", "aiml", "artificial intelligence", "machine learning", "deep learning", "nlp", "computer vision", "llm")):
        return "ai_ml_engineer"
    elif "devops" in r or "sre" in r or "site reliability" in r or "infrastructure" in r:
        return "devops_engineer"
    elif "data sci" in r:
        return "data_scientist"
    elif "data eng" in r or "pipeline" in r or "etl" in r:
        return "data_engineer"
    elif "front" in r or "ui" in r:
        return "frontend_developer"
    elif "back" in r or "api" in r or "server" in r:
        return "backend_developer"
    elif "full" in r or "stack" in r:
        return "full_stack_developer"
    elif "analyst" in r or "analytics" in r or "bi" in r:
        return "data_analyst"
    # Default to SDE
    return "software_development_engineer"


class SkillTaxonomyService:
    """Encapsulates skill catalog lookups, prerequisites validation, and role weighting."""

    CAT_DSA = CAT_DSA
    CAT_CS = CAT_CS
    CAT_SYSTEM_DESIGN = CAT_SYSTEM_DESIGN
    CAT_INTERVIEW_SKILLS = CAT_INTERVIEW_SKILLS
    CAT_ML = CAT_ML
    CAT_DEEP_LEARNING = CAT_DEEP_LEARNING
    CAT_NLP = CAT_NLP
    CAT_GENAI = CAT_GENAI
    CAT_DATA_ENGINEERING = CAT_DATA_ENGINEERING
    CAT_MLOPS = CAT_MLOPS
    CAT_MATH_STATS = CAT_MATH_STATS

    normalize_role = staticmethod(normalize_role_id)
    normalize_role_id = staticmethod(normalize_role_id)

    @staticmethod
    def get_skill(skill_id: str) -> Optional[Dict[str, Any]]:
        return SKILL_CATALOG.get(skill_id)

    @staticmethod
    def get_all_skills() -> List[Dict[str, Any]]:
        return list(SKILL_CATALOG.values())

    @staticmethod
    def get_skills_by_category(category: str) -> List[Dict[str, Any]]:
        return [s for s in SKILL_CATALOG.values() if s.get("category") == category]

    @staticmethod
    def get_prerequisites(skill_id: str) -> List[str]:
        skill = SKILL_CATALOG.get(skill_id)
        if not skill:
            return []
        return skill.get("prerequisites", [])

    @staticmethod
    def are_prerequisites_satisfied(skill_id: str, candidate_skill_proficiencies: Dict[str, float], threshold: float = 50.0) -> bool:
        """Returns True if all prerequisites meet the minimum proficiency threshold."""
        prereqs = SkillTaxonomyService.get_prerequisites(skill_id)
        for p in prereqs:
            prof = candidate_skill_proficiencies.get(p, 0.0)
            if prof < threshold:
                return False
        return True

    @staticmethod
    def get_role_weights(role_name: str) -> Dict[str, float]:
        role_key = normalize_role_id(role_name)
        return ROLE_REQUIREMENTS.get(role_key, ROLE_REQUIREMENTS["software_development_engineer"])

    @staticmethod
    def map_text_to_skills(text: str) -> List[str]:
        """Identifies skills from question, problem, or feedback text."""
        txt = (text or "").lower()
        matched = []
        keywords = {
            "dsa_dp": ["dynamic programming", "dp", "memoization", "tabulation", "knapsack", "subproblems"],
            "dsa_trees": ["tree", "binary tree", "traversal", "inorder", "postorder", "preorder"],
            "dsa_bst": ["bst", "binary search tree"],
            "dsa_graphs": ["graph", "adjacency list", "cycle detection"],
            "dsa_bfs": ["bfs", "breadth first", "level order"],
            "dsa_dfs": ["dfs", "depth first", "back-edge"],
            "dsa_arrays": ["array", "subarray", "matrix"],
            "dsa_strings": ["string", "anagram", "palindrome", "substring"],
            "dsa_hashing": ["hash", "hashmap", "frequency map", "dictionary"],
            "dsa_two_pointers": ["two pointer", "two-pointer", "meeting in the middle"],
            "dsa_sliding_window": ["sliding window"],
            "dsa_binary_search": ["binary search", "logarithmic search"],
            "dsa_recursion": ["recursion", "recursive"],
            "dsa_backtracking": ["backtracking", "permutations", "combinations"],
            "dsa_heaps": ["heap", "priority queue", "top-k"],
            "dsa_linked_lists": ["linked list", "linkedlist", "node pointer"],
            "dsa_stacks": ["stack", "lifo", "parentheses"],
            "dsa_queues": ["queue", "fifo"],
            "cs_oop": ["oop", "object oriented", "encapsulation", "polymorphism", "inheritance", "solid"],
            "cs_os": ["operating system", "process", "thread", "virtual memory", "deadlock", "paging"],
            "cs_dbms": ["acid", "database", "rdbms", "transaction", "3nf", "isolation"],
            "cs_sql": ["sql", "join", "query optimization", "explain", "group by"],
            "cs_networks": ["network", "tcp", "udp", "http", "https", "dns", "tls"],
            "cs_concurrency": ["concurrency", "multithreading", "race condition", "mutex", "lock"],
            "sys_caching": ["cache", "caching", "redis", "memcached", "cache-aside", "eviction"],
            "sys_load_balancing": ["load balancer", "load balancing", "reverse proxy", "nginx", "consistent hashing"],
            "sys_rest_apis": ["rest api", "endpoint", "http verb", "idempotency"],
            "sys_db_design": ["database design", "indexing", "b-tree", "composite index"],
            "sys_sharding_replication": ["sharding", "replication", "shard key", "replica"],
            "sys_scalability": ["scalability", "horizontal scaling", "cap theorem", "high availability"],
            "sys_message_queues": ["message queue", "kafka", "rabbitmq", "pub/sub", "async queue"],
            "sys_rate_limiting": ["rate limit", "token bucket", "throttling", "429"],
            "sys_fault_tolerance": ["fault tolerance", "circuit breaker", "retry", "backoff"],
            "soft_complexity_analysis": ["time complexity", "space complexity", "big-o", "big o", "o(n)"],
            "soft_problem_understanding": ["clarifying question", "problem understanding", "constraints"],
            "soft_communication": ["communication", "explanation", "think aloud", "articulation"],
            "soft_edge_cases": ["edge case", "boundary condition", "empty input", "overflow"],
            "soft_star_framework": ["star framework", "behavioral", "tell me about a time"],
            "soft_leadership_ownership": ["ownership", "leadership", "conflict", "disagreement"],

            # ── Mathematics & Statistics ──
            "math_linear_algebra": ["linear algebra", "matrix decomposition", "matrices", "eigenvalue", "eigenvector", "svd", "singular value decomposition"],
            "math_probability_statistics": ["probability", "statistics", "statistical", "bayes", "hypothesis testing", "p-value", "confidence interval", "mle"],

            # ── AI / ML / DL / NLP / GenAI ──
            "ml_python_libraries": ["numpy", "pandas", "scipy", "scikit-learn", "sklearn", "python for ml"],
            "ml_model_development": ["machine learning", "model development", "model training", "supervised learning", "unsupervised learning"],
            "ml_classical_algorithms": ["logistic regression", "linear regression", "svm", "support vector", "naive bayes", "k-nearest", "knn"],
            "ml_tree_ensembles": ["decision tree", "random forest", "xgboost", "gradient boosting", "lightgbm", "catboost"],
            "ml_clustering_pca": ["clustering", "k-means", "dbscan", "pca", "dimensionality reduction", "t-sne"],
            "ml_model_evaluation": ["model evaluation", "cross-validation", "roc-auc", "f1-score", "precision recall"],
            "ml_feature_engineering": ["feature engineering", "feature selection", "feature scaling"],
            "dl_neural_networks": ["deep learning", "neural network", "backpropagation", "activation function"],
            "dl_frameworks_pytorch_tensorflow": ["pytorch", "tensorflow", "keras", "autograd", "tensor"],
            "dl_computer_vision_cnn": ["computer vision", "cnn", "convolutional", "resnet", "object detection", "vision transformer"],
            "dl_transformers": ["transformer", "self-attention", "multi-head attention", "kv cache"],
            "dl_fine_tuning": ["fine-tune", "fine-tuning", "lora", "qlora", "peft", "transfer learning"],
            "nlp_pipelines": ["nlp", "natural language processing", "text processing", "tokenization", "bpe"],
            "nlp_embeddings": ["embedding", "embeddings", "vector representation", "cosine similarity"],
            "genai_llm_fundamentals": ["generative ai", "genai", "llm", "large language model", "prompt engineering", "rag"],
            "sys_ml_system_design": ["ml system design", "machine learning system design", "recommendation system", "ranking system", "feature store", "vector search"],

            # ── Data Engineering ──
            "data_preprocessing": ["data preprocessing", "data cleaning", "preprocess", "imputation"],
            "data_dataset_management": ["large-scale dataset", "dataset management", "parquet", "dataset versioning", "data scale"],
            "data_feature_pipelines": ["data engineering", "feature pipeline", "etl", "feature store"],

            # ── MLOps ──
            "mlops_model_deployment": ["model deployment", "model packaging", "onnx", "torchscript", "productionization"],
            "mlops_model_serving_apis": ["model serving", "inference api", "prediction api", "low latency inference"],
            "mlops_monitoring_drift": ["model monitoring", "data drift", "concept drift", "covariate shift"],
            "mlops_automated_retraining": ["automated retraining", "model retraining", "champion challenger", "model rollback"]
        }
        for skill_id, kws in keywords.items():
            if any(kw in txt for kw in kws):
                matched.append(skill_id)
        return matched

    @staticmethod
    def get_categories() -> List[str]:
        return [
            CAT_DSA, CAT_CS, CAT_SYSTEM_DESIGN, CAT_INTERVIEW_SKILLS,
            CAT_MATH_STATS, CAT_ML, CAT_DEEP_LEARNING, CAT_NLP, CAT_GENAI,
            CAT_DATA_ENGINEERING, CAT_MLOPS
        ]

    @staticmethod
    def get_prerequisites_dag() -> Dict[str, List[str]]:
        return {s_id: s.get("prerequisites", []) for s_id, s in SKILL_CATALOG.items()}

    @staticmethod
    def get_supported_roles() -> List[str]:
        return [
            "AI/ML Engineer",
            "Data Scientist",
            "Data Engineer",
            "Backend Engineer",
            "Frontend Engineer",
            "Full Stack Engineer",
            "Software Development Engineer (General)",
            "DevOps Engineer",
            "Data Analyst"
        ]

    @staticmethod
    def get_transitive_prerequisites(skill_id: str) -> List[str]:
        """Returns all transitive ancestors of a skill in topological order."""
        visited = set()
        order = []

        def dfs(curr: str):
            for p in SkillTaxonomyService.get_prerequisites(curr):
                if p not in visited:
                    visited.add(p)
                    dfs(p)
                    order.append(p)

        dfs(skill_id)
        return order

    @staticmethod
    def detect_cycles() -> List[str]:
        """
        Validates that the prerequisite graph is a valid DAG.
        Returns a list of skill IDs involved in a cycle, or empty list if valid.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {s_id: WHITE for s_id in SKILL_CATALOG}
        cycle_nodes = []

        def dfs(u: str) -> bool:
            color[u] = GRAY
            for v in SkillTaxonomyService.get_prerequisites(u):
                if color.get(v) == GRAY:
                    cycle_nodes.append(u)
                    cycle_nodes.append(v)
                    return True
                if color.get(v) == WHITE and dfs(v):
                    cycle_nodes.append(u)
                    return True
            color[u] = BLACK
            return False

        for node in SKILL_CATALOG:
            if color[node] == WHITE:
                if dfs(node):
                    return list(dict.fromkeys(cycle_nodes))
        return []

    @staticmethod
    def seed_skill_catalogue(supabase_client=None) -> int:
        """
        Populates the persistent skill_catalogue table with all canonical skills.
        Returns the count of seeded skills.
        """
        from local_supabase import get_supabase_client
        client = supabase_client or get_supabase_client()
        seeded = 0
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()

        for s_id, s in SKILL_CATALOG.items():
            record = {
                "id": s_id,
                "canonical_name": s.get("name", s_id),
                "domain": s.get("category", "General"),
                "category": s.get("category", "General"),
                "difficulty_floor": s.get("difficulty", "Beginner"),
                "difficulty_ceiling": "Advanced" if s.get("difficulty") == "Advanced" else "Intermediate",
                "prerequisites": json.dumps(s.get("prerequisites", [])) if not hasattr(client, "_is_postgres") else s.get("prerequisites", []),
                "created_at": now_iso
            }
            try:
                client.table("skill_catalogue").insert(record).execute()
                seeded += 1
            except Exception:
                pass
        return seeded

    @staticmethod
    def get_role_requirements(role_name: str) -> List[Dict[str, Any]]:
        weights = SkillTaxonomyService.get_role_weights(role_name)
        reqs = []
        for s_id, w in weights.items():
            reqs.append({
                "skill_id": s_id,
                "importance_weight": float(w),
                "target_proficiency": 75.0
            })
        return reqs
