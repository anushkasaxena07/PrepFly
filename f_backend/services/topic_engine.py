"""
Topic Engine: Domain Authority for Topic Classification, Validation, and Question Regeneration
Ensures strict topic compliance for Resume Mode and strict JD alignment for JD Mode.
"""

import re
from typing import List, Tuple, Optional, Dict, Any

TOPIC_DSA = "DSA"
TOPIC_SYSTEM_DESIGN = "SYSTEM_DESIGN"
TOPIC_CS_FUNDAMENTALS = "CS_FUNDAMENTALS"
TOPIC_HR_BEHAVIORAL = "HR_BEHAVIORAL"

TOPIC_NAME_DSA = "DSA & Algorithms"
TOPIC_NAME_SYSTEM_DESIGN = "System Design"
TOPIC_NAME_CS_FUNDAMENTALS = "Computer Science Fundamentals"
TOPIC_NAME_HR_BEHAVIORAL = "HR & Behavioral"

# ── 1. SUPPORTED TOPIC IDENTIFIERS & METADATA ────────────────────────────────
SUPPORTED_TOPICS = {
    "DSA": {
        "id": "DSA",
        "name": "DSA & Algorithms",
        "aliases": ["dsa", "algorithms", "data structures", "coding", "algorithm"],
        "keywords": [
            "array", "string", "linked list", "binary tree", "bst", "graph", "hash map",
            "hash table", "heap", "stack", "queue", "dynamic programming", "dp", "greedy",
            "two pointers", "sliding window", "binary search", "bfs", "dfs", "recursion",
            "backtracking", "time complexity", "space complexity", "big-o", "big o",
            "sorting", "trie", "matrix", "prefix sum"
        ],
        "disallowed_keywords": [
            "acid", "tcp", "udp", "operating system", "context switch", "dns",
            "sharding", "load balancer", "microservices", "kafka", "redis cluster",
            "tell me about a time", "conflict resolution", "leadership", "disagreement",
            "hr operations", "payroll", "posh", "talent acquisition"
        ]
    },
    "SYSTEM_DESIGN": {
        "id": "SYSTEM_DESIGN",
        "name": "System Design",
        "aliases": ["system design", "systemdesign", "architecture", "distributed systems"],
        "keywords": [
            "system design", "architecture", "scalability", "distributed", "microservices",
            "load balancer", "caching", "redis", "memcached", "sharding", "partitioning",
            "replication", "message queue", "kafka", "rabbitmq", "api gateway",
            "database selection", "sql vs nosql", "high availability", "fault tolerance",
            "circuit breaker", "rate limiter", "url shortener", "event driven",
            "consistency", "cap theorem", "throughput", "latency"
        ],
        "disallowed_keywords": [
            "binary search", "longest substring", "invert binary tree", "merge sort",
            "dynamic programming", "bfs", "dfs", "tell me about a time", "conflict",
            "onboarding", "payroll", "employee relations", "posh"
        ]
    },
    "CS_FUNDAMENTALS": {
        "id": "CS_FUNDAMENTALS",
        "name": "Computer Science Fundamentals",
        "aliases": ["fundamentals", "cs fundamentals", "core cs", "core_cs"],
        "keywords": [
            "process", "thread", "concurrency", "deadlock", "mutex", "semaphore",
            "context switch", "virtual memory", "paging", "operating system",
            "tcp", "udp", "http", "https", "dns", "osi model", "socket", "handshake",
            "acid", "database transaction", "b-tree", "indexing", "isolation level",
            "normalization", "solid", "oops", "polymorphism", "inheritance", "encapsulation"
        ],
        "disallowed_keywords": [
            "design twitter", "design uber", "design url shortener", "kafka cluster",
            "longest palindromic substring", "two sum", "tell me about a time you failed",
            "payroll", "talent acquisition", "posh compliance"
        ]
    },
    "HR_BEHAVIORAL": {
        "id": "HR_BEHAVIORAL",
        "name": "HR & Behavioral",
        "aliases": ["hr", "behavioral", "hr & behavioral", "hr_behavioral", "leadership"],
        "keywords": [
            "tell me about a time", "describe a situation", "conflict", "disagreement",
            "difficult teammate", "deadline", "prioritize", "feedback", "constructive",
            "leadership", "initiative", "mistake", "failure", "proudest", "strength",
            "weakness", "star method", "work under pressure", "collaboration",
            "communication", "culture fit", "motivation", "company values"
        ],
        "disallowed_keywords": [
            "binary search", "big-o", "time complexity", "dynamic programming",
            "tcp/ip", "mutex", "b-tree", "database sharding", "microservice architecture"
        ]
    }
}


# ── 2. TOPIC NORMALIZATION ───────────────────────────────────────────────────
def normalize_topic_identifier(topic_str: Optional[str]) -> str:
    """Normalizes any category/topic string to canonical topic ID."""
    if not topic_str:
        return "GENERAL"
    t = topic_str.strip().upper().replace("&", "AND").replace("-", "_").replace(" ", "_")
    if "DSA" in t or "ALGORITHM" in t or "DATA_STRUCTURE" in t:
        return "DSA"
    if "SYSTEM" in t or "DESIGN" in t or "ARCHITECTURE" in t:
        return "SYSTEM_DESIGN"
    if "FUNDAMENTAL" in t or "CS" in t or "CORE" in t:
        return "CS_FUNDAMENTALS"
    if "HR" in t or "BEHAVIORAL" in t or "LEADERSHIP" in t or "CULTURE" in t:
        return "HR_BEHAVIORAL"
    return "GENERAL"


# ── 3. STRICT TOPIC QUESTION VALIDATOR (RESUME MODE) ─────────────────────────
def validate_topic_question(question: str, allowed_topic_ids: List[str]) -> Tuple[bool, str, str]:
    """
    Validates whether a generated question strictly belongs to allowed topic(s).
    Returns (is_valid, detected_topic, reason).
    """
    if not question or len(question.strip()) < 10:
        return False, "UNKNOWN", "Question is empty or too short"

    q_lower = question.lower()
    normalized_allowed = [normalize_topic_identifier(t) for t in allowed_topic_ids if t]
    if not normalized_allowed or "GENERAL" in normalized_allowed:
        return True, "GENERAL", "General topic allowed"

    # Score matches across each supported topic
    scores: Dict[str, int] = {}
    violations: Dict[str, int] = {}

    for t_id, meta in SUPPORTED_TOPICS.items():
        kw_hits = sum(1 for kw in meta["keywords"] if kw in q_lower)
        scores[t_id] = kw_hits

        # Disallowed keywords trigger violations if t_id is in allowed list
        disallowed_hits = sum(1 for dkw in meta["disallowed_keywords"] if dkw in q_lower)
        violations[t_id] = disallowed_hits

    # Determine highest matching topic
    best_topic = max(scores, key=lambda k: scores[k])
    best_score = scores[best_topic]

    # Check for direct allowed topic match
    for allowed in normalized_allowed:
        if allowed in SUPPORTED_TOPICS:
            allowed_hits = scores.get(allowed, 0)
            disallowed_in_allowed = violations.get(allowed, 0)

            # If disallowed keywords for the allowed topic are present, question drifted!
            if disallowed_in_allowed > 0 and allowed_hits == 0:
                return False, best_topic, f"Question drifted into disallowed concepts for {allowed}"

            if allowed_hits >= 1:
                return True, allowed, f"Question matches allowed topic {allowed}"

    # If no keywords matched and question contains concepts from other topics
    if best_score >= 1 and best_topic not in normalized_allowed:
        return False, best_topic, f"Question belongs to {best_topic}, which is outside selected topics {normalized_allowed}"

    # If weak/generic question without specific topic terms
    if best_score == 0:
        # Check if question looks like an icebreaker or greeting on Turn 1 (handled separately)
        if any(g in q_lower for g in ["how are you feeling", "how is your day", "welcome", "glad to meet"]):
            return True, "ICEBREAKER", "Turn 1 greeting/icebreaker"
        return False, "OFF_TOPIC", f"Question lacks required concepts for selected topics {normalized_allowed}"

    return True, best_topic, "Topic validated"


# ── 4. STRICT JOB DESCRIPTION QUESTION VALIDATOR (JD MODE) ───────────────────
def is_hr_or_non_technical_role(role: str, job_description: str) -> bool:
    """Identifies if the role/JD is non-technical (HR, Recruiter, Marketing, Sales, Operations)."""
    text = f"{role} {job_description}".lower()
    hr_signals = [
        "human resources", "hr manager", "hr specialist", "hr generalist", "recruiter",
        "talent acquisition", "people operations", "people partner", "employee relations",
        "payroll", "posh", "onboarding", "performance appraisal", "hr business partner",
        "hrbp", "talent management", "staffing"
    ]
    technical_dev_signals = [
        "software engineer", "developer", "backend engineer", "frontend engineer",
        "full stack", "devops", "cloud architect", "data engineer", "machine learning engineer"
    ]
    is_hr = any(sig in text for sig in hr_signals)
    has_dev_title = any(sig in role.lower() for sig in technical_dev_signals)
    return is_hr and not has_dev_title


def validate_jd_question(question: str, role: str, job_description: str) -> Tuple[bool, str]:
    """
    Validates whether a generated question strictly assesses the provided Job Description.
    Ensures HR/non-technical roles NEVER receive coding/DSA/system design questions,
    and technical roles are bounded by their actual stack.
    """
    if not question or len(question.strip()) < 10:
        return False, "Question is empty or too short"

    q_lower = question.lower()
    role_lower = (role or "").lower()
    jd_lower = (job_description or "").lower()

    # Rule 1: HR & Non-Technical Roles must NEVER receive technical coding or systems architecture questions!
    if is_hr_or_non_technical_role(role, job_description):
        tech_violating_keywords = [
            "binary search", "big-o", "time complexity", "space complexity", "linked list",
            "binary tree", "graph", "dynamic programming", "sql query", "nosql", "sharding",
            "redis", "load balancer", "microservices", "kafka", "rest api", "python script",
            "react component", "docker container", "kubernetes", "compiler", "pointer",
            "tcp/ip", "socket", "mutex", "concurrency", "thread"
        ]
        found_tech = [k for k in tech_violating_keywords if k in q_lower]
        if found_tech:
            return False, f"Question asked technical concepts ({', '.join(found_tech)}) for an HR/Non-Technical role ({role})"

        # Check for HR relevance
        hr_relevant_keywords = [
            "talent", "recruit", "candidate", "employee", "conflict", "retention", "onboarding",
            "performance", "appraisal", "compliance", "policy", "posh", "payroll", "interview",
            "culture", "engagement", "grievance", "leadership", "feedback", "hr", "workplace"
        ]
        has_hr_relevance = any(k in q_lower for k in hr_relevant_keywords)
        # Turn 1 icebreakers are permitted
        is_greeting = any(g in q_lower for g in ["how are you", "day going", "welcome", "pleasure"])
        if not has_hr_relevance and not is_greeting:
            return False, "Question is not relevant to HR responsibilities or human resources workflows"

        return True, "Valid HR JD Question"

    # Rule 2: Technical Roles without ML in JD must NOT be asked Machine Learning / AI research questions
    if "machine learning" not in jd_lower and "ai engineer" not in role_lower and "data scientist" not in role_lower:
        ml_violations = [
            "convolutional neural network", "cnn", "yolo", "object detection", "backpropagation",
            "transformer attention", "gradient descent", "fine-tuning llm", "langchain agent",
            "reinforcement learning", "hyperparameter tuning"
        ]
        found_ml = [k for k in ml_violations if k in q_lower]
        if found_ml:
            return False, f"Rejected: Question asked ML concepts ({', '.join(found_ml)}) which are not present in the Job Description"

    # Rule 3: Python Backend Roles must NOT randomly be asked unrelated frontend framework internals (e.g. React component lifecycle)
    if "python" in role_lower and "backend" in role_lower and "react" not in jd_lower and "frontend" not in jd_lower:
        frontend_violations = [
            "react component lifecycle", "useeffect dependency array", "virtual dom reconciliation",
            "redux reducer", "css flexbox vs grid", "vuex store"
        ]
        found_fe = [k for k in frontend_violations if k in q_lower]
        if found_fe:
            return False, f"Rejected: Question asked frontend framework internals ({', '.join(found_fe)}) for a Python Backend role"

    # Rule 4: Frontend Web Roles must NOT randomly be asked low-level OS/Kernel memory paging
    if ("frontend" in role_lower or "react" in role_lower) and "kernel" not in jd_lower and "os" not in jd_lower:
        os_violations = [
            "linux kernel", "memory paging", "page replacement", "device driver", "interrupt vector",
            "assembly language", "virtual memory management"
        ]
        found_os = [k for k in os_violations if k in q_lower]
        if found_os:
            return False, f"Rejected: Question asked low-level OS/Kernel concepts ({', '.join(found_os)}) for a Frontend role"

    return True, "Valid JD Question"


# ── 5. CURATED DETERMINISTIC FALLBACK QUESTION BANKS ─────────────────────────
TOPIC_QUESTION_BANKS = {
    "DSA": [
        "Explain how you would implement a data structure that supports insert, delete, and getRandom in O(1) time complexity.",
        "Given a sorted array that has been rotated at an unknown pivot, explain how binary search can be adapted to find an element in O(log N) time.",
        "Compare Depth-First Search (DFS) and Breadth-First Search (BFS) for graph traversal: in what scenarios would one be preferred over the other regarding memory usage?",
        "Explain the core principle of Dynamic Programming: how do overlapping subproblems and optimal substructure differentiate it from a Greedy approach?",
        "How would you find the longest substring without repeating characters in O(N) time complexity using a sliding window and hash map?",
        "Explain how a Trie (Prefix Tree) is structured and why it outperforms a Hash Table for prefix search operations.",
        "What are the edge cases and time complexity trade-offs when implementing QuickSort versus MergeSort on nearly-sorted data?"
    ],
    "SYSTEM_DESIGN": [
        "How would you design a distributed, high-throughput rate limiting service for an API handling 100,000 requests per second?",
        "Explain database sharding vs horizontal partitioning. How do you select an effective shard key to avoid hot spots in distributed storage?",
        "When designing a URL shortener service (like bit.ly), how would you structure the unique ID generation to guarantee collision-free IDs across multiple nodes?",
        "How do distributed caching strategies (such as Redis Write-Through vs Write-Back vs Cache-Aside) handle cache stampedes and stale data?",
        "Explain how message queues like Apache Kafka guarantee message ordering and fault tolerance across distributed consumer groups.",
        "How would you design an idempotency mechanism for payment processing APIs to prevent duplicate charges upon network retries?",
        "Compare SQL and NoSQL database trade-offs for an e-commerce order management system requiring ACID transactional guarantees."
    ],
    "CS_FUNDAMENTALS": [
        "What is the difference between a process and a thread, and how does the operating system manage CPU context switching overhead?",
        "Explain the TCP three-way handshake and connection teardown. In what scenarios would an application choose UDP over TCP?",
        "What are the ACID properties in database management systems, and how does the Isolation level prevent dirty reads and phantom reads?",
        "Explain how virtual memory and paging work in modern operating systems, including what happens during a page fault.",
        "What is a B-Tree index in relational databases, and why is it preferred over a Binary Search Tree for disk-based storage?",
        "Explain the SOLID principles in Object-Oriented Design, with a concrete example of the Dependency Inversion Principle.",
        "What is the difference between a mutex and a counting semaphore, and how do you prevent priority inversion in multithreaded systems?"
    ],
    "HR_BEHAVIORAL": [
        "Tell me about a situation where you had a significant technical or project disagreement with a teammate or lead. How did you resolve it?",
        "Describe a time when a critical project deadline was moved up unexpectedly. How did you prioritize tasks and deliver under pressure?",
        "Can you share an experience where you received critical constructive feedback on your work? What specific actions did you take to improve?",
        "Tell me about a project where you took leadership or initiative beyond your assigned responsibilities to solve an unaddressed problem.",
        "Describe a situation where a production release or deliverable failed or had severe issues. How did you take ownership and recover?",
        "How do you handle collaborating with cross-functional stakeholders who have competing priorities or non-technical expectations?",
        "Tell me about a time when you had to make a high-impact decision with incomplete information. What was your thought process?"
    ],
    "HR_JOB_DESCRIPTION": [
        "As an HR Specialist/Manager, walk me through your end-to-end talent acquisition workflow: how do you source, screen, and maintain candidate pipelines for high-demand roles?",
        "How do you handle a sensitive employee relations dispute involving workplace harassment or policy non-compliance while ensuring confidentiality and statutory compliance?",
        "Describe your strategy for building and executing a structured employee onboarding program that reduces early-stage attrition and drives cultural integration.",
        "How do you design and administer a performance appraisal framework that objectively evaluates employee performance, career milestones, and merit-based compensation?",
        "What statutory labor law compliance frameworks (e.g. POSH, provident fund, employee state insurance, separation compliance) do you monitor to mitigate legal liability?",
        "Tell me about a time when employee turnover was rising in a business unit. How did you diagnose the root causes and implement retention interventions?",
        "How do you partner with departmental leadership to conduct effective workforce planning and succession management for critical business positions?"
    ],
    "PYTHON_BACKEND_JD": [
        "How would you structure a scalable RESTful API service using Flask or FastAPI, including clean request validation and centralized error handling?",
        "Walk me through how you would optimize a slow-running PostgreSQL database query that involves multiple table joins and millions of rows.",
        "Explain how you would implement secure user authentication and authorization using JWT tokens, refresh tokens, and role-based access control (RBAC).",
        "How would you integrate Redis caching into a Python backend application to reduce database load while preventing cache invalidation race conditions?",
        "Describe your approach to designing automated unit and integration test suites in Python (using pytest/unittest) for critical business logic and API endpoints.",
        "How do you handle asynchronous background processing and task scheduling in a Python architecture using tools like Celery or asyncio?",
        "What strategies do you use in PostgreSQL to manage concurrent write operations, database transactions, and database migration versioning?"
    ]
}


def get_curated_fallback_question(*args, **kwargs) -> str:
    """
    Selects a deterministic, non-repeating, topic-compliant question from the curated banks.
    Guarantees that HR roles receive HR questions, DSA receives DSA, etc.
    """
    question_index = kwargs.get("question_index", 2)
    category = kwargs.get("category", "")
    role = kwargs.get("role", "")
    job_description = kwargs.get("job_description", "")
    previous_questions = kwargs.get("previous_questions") or []

    for arg in args:
        if isinstance(arg, int):
            question_index = arg
        elif isinstance(arg, (list, tuple)):
            if not category or category == "DSA":
                category = arg[0] if arg else "DSA"
            elif not previous_questions:
                previous_questions = list(arg)
        elif isinstance(arg, str):
            if not category:
                category = arg
            elif not role:
                role = arg
            elif not job_description:
                job_description = arg

    category = str(category or "DSA")
    role = str(role or "")
    job_description = str(job_description or "")
    previous_questions = previous_questions or []
    prev_clean = [q.lower().strip() for q in previous_questions]

    # Select target bank
    if is_hr_or_non_technical_role(role, job_description):
        bank = TOPIC_QUESTION_BANKS["HR_JOB_DESCRIPTION"]
    elif role and "python" in role.lower() and "backend" in role.lower():
        bank = TOPIC_QUESTION_BANKS["PYTHON_BACKEND_JD"]
    else:
        norm_topic = normalize_topic_identifier(category)
        if norm_topic in TOPIC_QUESTION_BANKS:
            bank = TOPIC_QUESTION_BANKS[norm_topic]
        elif "HR" in norm_topic or "BEHAVIORAL" in norm_topic:
            bank = TOPIC_QUESTION_BANKS["HR_BEHAVIORAL"]
        elif "DESIGN" in norm_topic:
            bank = TOPIC_QUESTION_BANKS["SYSTEM_DESIGN"]
        elif "FUNDAMENTAL" in norm_topic:
            bank = TOPIC_QUESTION_BANKS["CS_FUNDAMENTALS"]
        else:
            bank = TOPIC_QUESTION_BANKS["DSA"]

    # Pick first non-repeating question from the bank
    for q in bank:
        if not any(q.lower() in p or p in q.lower() for p in prev_clean):
            return q

    # Fallback to indexed wrap
    return bank[(question_index - 2) % len(bank)]
