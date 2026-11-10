"""
Track Configurations for PrepFly AI Interviewer ("Ava").
Governs allowed skills, topic boundaries, forbidden topics, question types,
time budgets, resume weight, and format expectations.
"""

from typing import Dict, Any, List, Optional, Tuple

# Track ID Constants
TRACK_MAANG = "maang_big_tech"
TRACK_DSA = "dsa_algorithms"
TRACK_RESUME_DEEP_DIVE = "resume_deep_dive"
TRACK_CS_FUNDAMENTALS = "cs_fundamentals"
TRACK_GUESSTIMATE = "guesstimate"
TRACK_LOGIC_PUZZLES = "logic_puzzles"
TRACK_SYSTEM_DESIGN = "system_design"
TRACK_HR_BEHAVIORAL = "hr_behavioral"

TRACK_CONFIGS: Dict[str, Dict[str, Any]] = {
    TRACK_MAANG: {
        "track_id": TRACK_MAANG,
        "display_name": "MAANG / Big Tech",
        "aliases": ["maang", "big tech", "faang", "meta", "google", "amazon"],
        "allowed_skills": [
            "dsa_arrays", "dsa_trees", "dsa_graphs", "dsa_dp", "dsa_hashing",
            "sys_caching", "sys_load_balancing", "sys_sharding", "sys_microservices",
            "python_concurrency", "cs_dbms", "cs_networks"
        ],
        "allowed_topics": [
            "algorithmic trade-offs", "distributed system architecture",
            "high-scale capacity estimation", "production reliability", "resume project ownership"
        ],
        "forbidden_topics": [
            "entry-level syntax memorization", "academic theory without scale",
            "generic non-technical small talk", "trivia questions"
        ],
        "question_types": ["project_dive", "scenario", "code_tradeoff", "system_architecture"],
        "default_question_count": 5,
        "time_budget_minutes": 45,
        "resume_weight": 0.40,
        "difficulty_start_level": "Advanced",
        "opening_scope_sentence": (
            "This is a MAANG-style round where we'll explore the architecture and algorithmic "
            "trade-offs in your past work, followed by a high-scale problem-solving discussion."
        )
    },

    TRACK_DSA: {
        "track_id": TRACK_DSA,
        "display_name": "DSA & Algorithms",
        "aliases": ["dsa", "algorithms", "data structures", "coding", "dsa & algorithms"],
        "allowed_skills": [
            "dsa_arrays", "dsa_trees", "dsa_graphs", "dsa_dp", "dsa_hashing",
            "dsa_recursion", "dsa_two_pointers", "dsa_binary_search"
        ],
        "allowed_topics": [
            "data structures", "algorithmic complexity", "time and space Big-O",
            "edge case analysis", "thinking aloud", "optimization strategies"
        ],
        "forbidden_topics": [
            "distributed systems", "database indexing internals", "REST API architecture",
            "behavioral STAR questions", "generic project resume inquiries"
        ],
        "question_types": ["code", "debug", "algorithmic_reasoning", "complexity_analysis"],
        "default_question_count": 5,
        "time_budget_minutes": 35,
        "resume_weight": 0.05,
        "difficulty_start_level": "Intermediate",
        "opening_scope_sentence": (
            "We will focus strictly on algorithmic problem solving, data structures, and computational "
            "complexity. Please talk through your reasoning aloud as you structure your solution."
        )
    },

    TRACK_RESUME_DEEP_DIVE: {
        "track_id": TRACK_RESUME_DEEP_DIVE,
        "display_name": "Resume Deep-Dive",
        "aliases": ["resume", "resume deep-dive", "project round", "experience"],
        "allowed_skills": [
            "python_core", "ml_model_evaluation", "sys_client_server", "sys_rest_apis",
            "cs_dbms", "project_ownership", "architectural_decisions"
        ],
        "allowed_topics": [
            "candidate uploaded projects", "production tech stack", "individual vs team contribution",
            "engineering trade-offs", "operational metrics and business impact", "past failures"
        ],
        "forbidden_topics": [
            "unrelated third-party technologies not on resume", "pure leetcode puzzle algorithms",
            "abstract academic trivia"
        ],
        "question_types": ["project_dive", "scenario", "tradeoff_investigation"],
        "default_question_count": 5,
        "time_budget_minutes": 25,
        "resume_weight": 0.95,
        "difficulty_start_level": "Intermediate",
        "opening_scope_sentence": (
            "Every question in this round comes directly from your uploaded resume. I'll be asking "
            "about the technical decisions, architecture, and ownership in your documented projects."
        )
    },

    TRACK_CS_FUNDAMENTALS: {
        "track_id": TRACK_CS_FUNDAMENTALS,
        "display_name": "CS Fundamentals",
        "aliases": ["fundamentals", "cs fundamentals", "core cs", "os dbms networks"],
        "allowed_skills": [
            "cs_os_processes", "cs_os_memory", "cs_networks", "cs_dbms", "cs_oop"
        ],
        "allowed_topics": [
            "operating systems", "virtual memory and paging", "process vs thread synchronization",
            "computer networks TCP/UDP and DNS", "database ACID and indexing", "OOP & SOLID principles"
        ],
        "forbidden_topics": [
            "large-scale distributed sharding", "deep learning backprop",
            "behavioral STAR questions", "frontend CSS layout"
        ],
        "question_types": ["concept", "scenario", "comparative_analysis"],
        "default_question_count": 5,
        "time_budget_minutes": 25,
        "resume_weight": 0.10,
        "difficulty_start_level": "Intermediate",
        "opening_scope_sentence": (
            "This session assesses foundational Computer Science: Operating Systems, Networking, "
            "DBMS, and Object-Oriented Design. We'll start with core principles and explore real-world scenarios."
        )
    },

    TRACK_GUESSTIMATE: {
        "track_id": TRACK_GUESSTIMATE,
        "display_name": "Guesstimate & Market Sizing",
        "aliases": ["guesstimate", "market sizing", "fermi estimation", "estimation"],
        "allowed_skills": [
            "structured_estimation", "assumption_articulation", "decomposition",
            "sanity_checking", "mental_math_communication"
        ],
        "allowed_topics": [
            "market sizing", "engineering volume sizing", "bandwidth/storage estimation",
            "population and demographic decomposition", "boundary sanity checking"
        ],
        "forbidden_topics": [
            "coding syntax", "database queries", "behavioral conflict resolution",
            "trivia memorization", "exact census facts"
        ],
        "question_types": ["estimation", "decomposition_probe", "assumption_stress_test"],
        "default_question_count": 4,
        "time_budget_minutes": 25,
        "resume_weight": 0.0,
        "difficulty_start_level": "Intermediate",
        "opening_scope_sentence": (
            "We'll explore structured Fermi estimation and market sizing. There is no single exact answer; "
            "I am looking for clear assumptions, top-down or bottom-up decomposition, and sanity checks."
        )
    },

    TRACK_LOGIC_PUZZLES: {
        "track_id": TRACK_LOGIC_PUZZLES,
        "display_name": "Logic Puzzles & Analytical Reasoning",
        "aliases": ["puzzles", "logic puzzles", "analytical reasoning", "brain teasers"],
        "allowed_skills": [
            "logical_deduction", "adversarial_reasoning", "combinatorics",
            "invariance_analysis", "hypothesis_testing"
        ],
        "allowed_topics": [
            "mathematical logic", "probability paradoxes", "weighing & measurement puzzles",
            "graph and game theory logic", "formal verification of invariants"
        ],
        "forbidden_topics": [
            "software frameworks", "cloud providers", "resume experience",
            "cultural fit", "database schemas"
        ],
        "question_types": ["puzzle", "constraint_exploration", "generalization_probe"],
        "default_question_count": 4,
        "time_budget_minutes": 25,
        "resume_weight": 0.0,
        "difficulty_start_level": "Intermediate",
        "opening_scope_sentence": (
            "We will tackle analytical and mathematical logic puzzles. Please talk through your "
            "thought process and any edge cases you test as you work toward a solution."
        )
    },

    TRACK_SYSTEM_DESIGN: {
        "track_id": TRACK_SYSTEM_DESIGN,
        "display_name": "System Design & Architecture",
        "aliases": ["system design", "systemdesign", "architecture", "hld", "distributed systems"],
        "allowed_skills": [
            "sys_caching", "sys_load_balancing", "sys_sharding", "sys_microservices",
            "sys_event_driven", "sys_data_modeling", "sys_resilience"
        ],
        "allowed_topics": [
            "functional and non-functional requirements", "capacity planning", "API contract design",
            "data model and persistence", "caching layers", "partitioning and replication",
            "availability vs consistency trade-offs", "single points of failure"
        ],
        "forbidden_topics": [
            "binary tree traversal algorithms", "CSS layout", "behavioral stories",
            "low-level syntax bugs"
        ],
        "question_types": ["system_architecture", "capacity_estimation", "failure_mode_analysis"],
        "default_question_count": 5,
        "time_budget_minutes": 40,
        "resume_weight": 0.20,
        "difficulty_start_level": "Advanced",
        "opening_scope_sentence": (
            "This is a high-level system design discussion. We'll outline requirements, estimate "
            "traffic and storage, design APIs and data models, and drill into scalability and failure modes."
        )
    },

    TRACK_HR_BEHAVIORAL: {
        "track_id": TRACK_HR_BEHAVIORAL,
        "display_name": "HR & Behavioral",
        "aliases": ["hr", "behavioral", "hr & behavioral", "culture fit", "leadership"],
        "allowed_skills": [
            "star_storytelling", "conflict_resolution", "leadership_ownership",
            "cross_functional_collaboration", "adaptability_under_pressure"
        ],
        "allowed_topics": [
            "past workplace challenges", "conflict with colleagues or managers",
            "leadership and mentoring", "project setbacks and lessons learned",
            "career motivation and company culture fit"
        ],
        "forbidden_topics": [
            "protected attributes (marital status, religion, caste, health, age)",
            "coding syntax", "system design sharding", "salary negotiations during technical interview"
        ],
        "question_types": ["behavioral", "situational", "star_probe"],
        "default_question_count": 5,
        "time_budget_minutes": 25,
        "resume_weight": 0.50,
        "difficulty_start_level": "Intermediate",
        "opening_scope_sentence": (
            "We'll cover behavioral and situational experiences using the STAR method. "
            "I'm interested in hearing about real challenges you faced, your specific actions, and the outcomes."
        )
    }
}


def resolve_track(track_identifier: Optional[str]) -> Dict[str, Any]:
    """Resolves track configuration by ID or alias; defaults to TRACK_RESUME_DEEP_DIVE."""
    if not track_identifier:
        return TRACK_CONFIGS[TRACK_RESUME_DEEP_DIVE]

    clean = track_identifier.strip().lower()
    if clean in TRACK_CONFIGS:
        return TRACK_CONFIGS[clean]

    for track in TRACK_CONFIGS.values():
        if clean == track["display_name"].lower():
            return track
        if any(clean == alias or alias in clean for alias in track["aliases"]):
            return track

    return TRACK_CONFIGS[TRACK_RESUME_DEEP_DIVE]


def validate_question_against_track(question_text: str, track_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Deterministic scope guard: Verifies that question_text does not violate track boundaries.
    Returns (is_valid, rejection_reason).
    """
    q_lower = question_text.lower()
    forbidden = track_config.get("forbidden_topics", [])

    # Check track-specific explicit violations
    track_id = track_config.get("track_id")
    if track_id == TRACK_GUESSTIMATE:
        if any(kw in q_lower for kw in ["leetcode", "binary tree", "sql query", "acid properties", "docker container"]):
            return False, "Question introduces technical coding/DBMS concepts into a pure Guesstimate track."
    elif track_id == TRACK_LOGIC_PUZZLES:
        if any(kw in q_lower for kw in ["react component", "rest api", "kubernetes", "tell me about a time you had conflict"]):
            return False, "Question introduces framework/behavioral topics into a pure Logic Puzzles track."
    elif track_id == TRACK_CS_FUNDAMENTALS:
        if any(kw in q_lower for kw in ["tell me about a time", "greatest weakness", "conflict with a peer"]):
            return False, "Question introduces behavioral STAR topics into CS Fundamentals track."
    elif track_id == TRACK_DSA:
        if any(kw in q_lower for kw in ["kafka cluster", "database sharding", "microservices mesh", "star method"]):
            return False, "Question introduces distributed systems or behavioral topics into pure DSA track."
    elif track_id == TRACK_HR_BEHAVIORAL:
        if any(kw in q_lower for kw in ["religion", "married", "caste", "health condition", "how old are you"]):
            return False, "Question inquires about protected personal attributes."

    return True, None
