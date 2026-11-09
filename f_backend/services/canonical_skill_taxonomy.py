"""
CANONICAL HIERARCHICAL SKILL TAXONOMY
======================================
Defines the authoritative, standardized skill catalog for PrepFly.
Organized into top-level parent domains and leaf child subskills with
stable IDs, prerequisites, applicable roles, assessment methods, and evaluation rubrics.
"""

from typing import Dict, Any, List, Optional

# Top-Level Parent Skill Domains
PARENT_DOMAINS: Dict[str, Dict[str, Any]] = {
    "python": {
        "domain_id": "python",
        "name": "Python Engineering",
        "description": "Core Python language, idioms, data structures, concurrency, and ecosystem tooling.",
        "category": "Programming Languages",
    },
    "machine_learning": {
        "domain_id": "machine_learning",
        "name": "Machine Learning",
        "description": "Classical ML models, mathematical foundations, model evaluation, and feature engineering.",
        "category": "AI / ML",
    },
    "deep_learning": {
        "domain_id": "deep_learning",
        "name": "Deep Learning & Generative AI",
        "description": "Neural networks, Transformer architectures, LLM fundamentals, and fine-tuning.",
        "category": "AI / ML",
    },
    "system_design": {
        "domain_id": "system_design",
        "name": "System Design & Architecture",
        "description": "Scalable distributed systems, caching, messaging, databases, and microservices.",
        "category": "System Design",
    },
    "data_structures_algorithms": {
        "domain_id": "data_structures_algorithms",
        "name": "Data Structures & Algorithms",
        "description": "Arrays, trees, graphs, dynamic programming, and complexity analysis.",
        "category": "DSA",
    },
    "core_cs": {
        "domain_id": "core_cs",
        "name": "Computer Science Fundamentals",
        "description": "Operating systems, concurrency, computer networks, and relational database internals.",
        "category": "Core CS",
    },
    "frontend_web": {
        "domain_id": "frontend_web",
        "name": "Frontend & Web Engineering",
        "description": "Modern JavaScript/TypeScript, React state architecture, rendering optimization, and web APIs.",
        "category": "Frontend",
    },
    "data_engineering": {
        "domain_id": "data_engineering",
        "name": "Data Engineering & Pipelines",
        "description": "ETL/ELT pipelines, distributed processing, stream processing, and data warehousing.",
        "category": "Data Engineering",
    },
    "devops_cloud": {
        "domain_id": "devops_cloud",
        "name": "Cloud & MLOps",
        "description": "Containerization, CI/CD, cloud infrastructure, model deployment, and observability.",
        "category": "DevOps & Cloud",
    },
    "interview_skills": {
        "domain_id": "interview_skills",
        "name": "Interview Execution & Behavioral",
        "description": "STAR methodology, technical communication, trade-off explanation, and requirements clarification.",
        "category": "Interview Skills",
    }
}

# Granular Child Subskills with Canonical IDs
CANONICAL_SKILLS: Dict[str, Dict[str, Any]] = {
    # ── Python Subskills ──────────────────────────────────────────────────────────
    "python_syntax_idioms": {
        "skill_id": "python_syntax_idioms",
        "name": "Python Idiomatic Syntax & Comprehensions",
        "parent_skill_id": "python",
        "description": "List/dict comprehensions, generators, context managers, and PEP 8 best practices.",
        "prerequisites": [],
        "difficulty": "Beginner",
        "applicable_roles": ["software_development_engineer", "ai_ml_engineer", "data_scientist", "backend_developer"],
        "assessment_methods": ["coding_submission", "practical_assignment"],
        "is_leaf": True
    },
    "python_data_structures": {
        "skill_id": "python_data_structures",
        "name": "Python Built-in Data Structures & Collections",
        "parent_skill_id": "python",
        "description": "Deep understanding of list, dict, set, deque, heapq, and their asymptotic operations.",
        "prerequisites": ["python_syntax_idioms"],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "ai_ml_engineer", "data_scientist", "backend_developer"],
        "assessment_methods": ["coding_submission", "diagnostic_assessment"],
        "is_leaf": True
    },
    "python_oop": {
        "skill_id": "python_oop",
        "name": "Object-Oriented Python & Dunder Methods",
        "parent_skill_id": "python",
        "description": "Classes, inheritance, polymorphism, abstract base classes, and magic dunder methods.",
        "prerequisites": ["python_syntax_idioms"],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "ai_ml_engineer", "backend_developer"],
        "assessment_methods": ["coding_submission", "practical_assignment"],
        "is_leaf": True
    },
    "python_concurrency": {
        "skill_id": "python_concurrency",
        "name": "Python Concurrency & GIL Internals",
        "parent_skill_id": "python",
        "description": "Global Interpreter Lock (GIL), threading vs multiprocessing, asyncio, and event loops.",
        "prerequisites": ["python_data_structures"],
        "difficulty": "Advanced",
        "applicable_roles": ["backend_developer", "ai_ml_engineer", "software_development_engineer"],
        "assessment_methods": ["diagnostic_assessment", "ai_interview"],
        "is_leaf": True
    },

    # ── Machine Learning Subskills ────────────────────────────────────────────────
    "ml_math_foundations": {
        "skill_id": "ml_math_foundations",
        "name": "ML Mathematics (Linear Algebra & Statistics)",
        "parent_skill_id": "machine_learning",
        "description": "Vector norms, eigenvalues/eigenvectors, probability distributions, Bayes rule, and hypothesis testing.",
        "prerequisites": [],
        "difficulty": "Intermediate",
        "applicable_roles": ["ai_ml_engineer", "data_scientist"],
        "assessment_methods": ["diagnostic_assessment"],
        "is_leaf": True
    },
    "ml_model_development": {
        "skill_id": "ml_model_development",
        "name": "Supervised Learning & Regularization",
        "parent_skill_id": "machine_learning",
        "description": "Linear/Logistic regression, cost functions, gradient descent, L1/L2 regularization, and bias-variance tradeoff.",
        "prerequisites": ["ml_math_foundations"],
        "difficulty": "Intermediate",
        "applicable_roles": ["ai_ml_engineer", "data_scientist"],
        "assessment_methods": ["diagnostic_assessment", "practical_assignment"],
        "is_leaf": True
    },
    "ml_tree_ensembles": {
        "skill_id": "ml_tree_ensembles",
        "name": "Tree Ensembles (Random Forests & GBDT)",
        "parent_skill_id": "machine_learning",
        "description": "Decision trees, bagging, Random Forests, boosting, XGBoost, and LightGBM.",
        "prerequisites": ["ml_model_development"],
        "difficulty": "Intermediate",
        "applicable_roles": ["ai_ml_engineer", "data_scientist"],
        "assessment_methods": ["practical_assignment", "diagnostic_assessment"],
        "is_leaf": True
    },
    "ml_model_evaluation": {
        "skill_id": "ml_model_evaluation",
        "name": "Model Evaluation & Imbalanced Metrics",
        "parent_skill_id": "machine_learning",
        "description": "Precision, recall, F1, ROC-AUC vs PR-AUC, confusion matrices, and cross-validation strategies.",
        "prerequisites": ["ml_model_development"],
        "difficulty": "Intermediate",
        "applicable_roles": ["ai_ml_engineer", "data_scientist"],
        "assessment_methods": ["diagnostic_assessment", "practical_assignment"],
        "is_leaf": True
    },

    # ── Deep Learning & GenAI Subskills ───────────────────────────────────────────
    "dl_neural_networks": {
        "skill_id": "dl_neural_networks",
        "name": "Neural Networks & Backpropagation",
        "parent_skill_id": "deep_learning",
        "description": "Feedforward architectures, activation functions, loss gradients, backpropagation, and optimization (Adam).",
        "prerequisites": ["ml_model_development"],
        "difficulty": "Intermediate",
        "applicable_roles": ["ai_ml_engineer", "data_scientist"],
        "assessment_methods": ["diagnostic_assessment", "coding_submission"],
        "is_leaf": True
    },
    "dl_transformers": {
        "skill_id": "dl_transformers",
        "name": "Transformer Architecture & Self-Attention",
        "parent_skill_id": "deep_learning",
        "description": "Scaled dot-product attention, multi-head attention, positional encodings, and encoder-decoder topologies.",
        "prerequisites": ["dl_neural_networks"],
        "difficulty": "Advanced",
        "applicable_roles": ["ai_ml_engineer"],
        "assessment_methods": ["diagnostic_assessment", "ai_interview"],
        "is_leaf": True
    },
    "genai_llm_fundamentals": {
        "skill_id": "genai_llm_fundamentals",
        "name": "LLM Fundamentals, RAG & Hallucination Mitigation",
        "parent_skill_id": "deep_learning",
        "description": "Auto-regressive token sampling, vector search, Retrieval-Augmented Generation, and alignment.",
        "prerequisites": ["dl_transformers"],
        "difficulty": "Advanced",
        "applicable_roles": ["ai_ml_engineer"],
        "assessment_methods": ["diagnostic_assessment", "ai_interview", "practical_assignment"],
        "is_leaf": True
    },

    # ── System Design Subskills ───────────────────────────────────────────────────
    "sys_caching": {
        "skill_id": "sys_caching",
        "name": "Distributed Caching & Eviction Strategies",
        "parent_skill_id": "system_design",
        "description": "Redis/Memcached, Cache-Aside, Write-Through, Write-Back, cache invalidation, and thundering herd mitigation.",
        "prerequisites": [],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "backend_developer", "ai_ml_engineer"],
        "assessment_methods": ["diagnostic_assessment", "ai_interview"],
        "is_leaf": True
    },
    "sys_scalability": {
        "skill_id": "sys_scalability",
        "name": "Horizontal Scaling & Load Balancing",
        "parent_skill_id": "system_design",
        "description": "Stateless services, round-robin, consistent hashing, reverse proxies, and autoscaling.",
        "prerequisites": [],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "backend_developer", "devops_engineer"],
        "assessment_methods": ["diagnostic_assessment", "ai_interview"],
        "is_leaf": True
    },
    "sys_rate_limiting": {
        "skill_id": "sys_rate_limiting",
        "name": "API Rate Limiting & Traffic Shaping",
        "parent_skill_id": "system_design",
        "description": "Token bucket, leaky bucket, fixed/sliding window counters, distributed Redis rate limiters.",
        "prerequisites": ["sys_caching"],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "backend_developer"],
        "assessment_methods": ["diagnostic_assessment", "practical_assignment"],
        "is_leaf": True
    },
    "sys_ml_system_design": {
        "skill_id": "sys_ml_system_design",
        "name": "ML System Design & Feature Stores",
        "parent_skill_id": "system_design",
        "description": "High-throughput inference, candidate retrieval vs ranking, feature stores, drift monitoring, and canary deployments.",
        "prerequisites": ["ml_model_evaluation", "sys_caching"],
        "difficulty": "Advanced",
        "applicable_roles": ["ai_ml_engineer"],
        "assessment_methods": ["diagnostic_assessment", "ai_interview"],
        "is_leaf": True
    },

    # ── DSA Subskills ─────────────────────────────────────────────────────────────
    "dsa_arrays_strings": {
        "skill_id": "dsa_arrays_strings",
        "name": "Arrays, Two-Pointers & Sliding Window",
        "parent_skill_id": "data_structures_algorithms",
        "description": "In-place modifications, two-pointer convergence, sliding window bounds, and prefix sums.",
        "prerequisites": [],
        "difficulty": "Beginner",
        "applicable_roles": ["software_development_engineer", "backend_developer", "ai_ml_engineer"],
        "assessment_methods": ["coding_submission"],
        "is_leaf": True
    },
    "dsa_hashing": {
        "skill_id": "dsa_hashing",
        "name": "Hash Tables & Fast Lookup",
        "parent_skill_id": "data_structures_algorithms",
        "description": "Hash collision resolution, constant time lookups, frequency counting, and amortized bounds.",
        "prerequisites": ["dsa_arrays_strings"],
        "difficulty": "Beginner",
        "applicable_roles": ["software_development_engineer", "backend_developer", "ai_ml_engineer"],
        "assessment_methods": ["coding_submission"],
        "is_leaf": True
    },
    "dsa_trees_graphs": {
        "skill_id": "dsa_trees_graphs",
        "name": "Trees, BSTs, BFS/DFS & Graph Traversals",
        "parent_skill_id": "data_structures_algorithms",
        "description": "Binary search tree invariants, level-order traversal, cycle detection, topological sort, Dijkstra.",
        "prerequisites": ["dsa_hashing"],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "backend_developer"],
        "assessment_methods": ["coding_submission", "diagnostic_assessment"],
        "is_leaf": True
    },
    "dsa_dynamic_programming": {
        "skill_id": "dsa_dynamic_programming",
        "name": "Dynamic Programming & Memoization",
        "parent_skill_id": "data_structures_algorithms",
        "description": "Overlapping subproblems, optimal substructure, top-down memoization, bottom-up tabulation.",
        "prerequisites": ["dsa_trees_graphs"],
        "difficulty": "Advanced",
        "applicable_roles": ["software_development_engineer"],
        "assessment_methods": ["coding_submission", "diagnostic_assessment"],
        "is_leaf": True
    },

    # ── Core CS Subskills ─────────────────────────────────────────────────────────
    "cs_os_concurrency": {
        "skill_id": "cs_os_concurrency",
        "name": "Processes, Threads & Memory Isolation",
        "parent_skill_id": "core_cs",
        "description": "Process vs thread memory spaces, stack vs heap, context switching, mutexes, semaphores, and deadlocks.",
        "prerequisites": [],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "backend_developer", "devops_engineer"],
        "assessment_methods": ["diagnostic_assessment"],
        "is_leaf": True
    },
    "cs_dbms_internals": {
        "skill_id": "cs_dbms_internals",
        "name": "Database Internals, ACID & Transactions",
        "parent_skill_id": "core_cs",
        "description": "B-Tree vs LSM indexing, transaction isolation levels (Dirty Read, Non-repeatable, Phantom), and WAL.",
        "prerequisites": [],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "backend_developer", "data_engineer"],
        "assessment_methods": ["diagnostic_assessment", "ai_interview"],
        "is_leaf": True
    },

    # ── Frontend Subskills ────────────────────────────────────────────────────────
    "fe_react_architecture": {
        "skill_id": "fe_react_architecture",
        "name": "React Hooks, State & Component Architecture",
        "parent_skill_id": "frontend_web",
        "description": "useState, useEffect, useMemo, useCallback, reconciliation algorithm, and custom hooks.",
        "prerequisites": [],
        "difficulty": "Intermediate",
        "applicable_roles": ["frontend_developer", "full_stack_developer"],
        "assessment_methods": ["coding_submission", "practical_assignment"],
        "is_leaf": True
    },
    "fe_web_performance": {
        "skill_id": "fe_web_performance",
        "name": "Critical Rendering Path & Browser Performance",
        "parent_skill_id": "frontend_web",
        "description": "DOM/CSSOM creation, reflow vs repaint, GPU compositing, code splitting, and web vitals.",
        "prerequisites": ["fe_react_architecture"],
        "difficulty": "Intermediate",
        "applicable_roles": ["frontend_developer", "full_stack_developer"],
        "assessment_methods": ["diagnostic_assessment", "practical_assignment"],
        "is_leaf": True
    },

    # ── Interview Skills ──────────────────────────────────────────────────────────
    "soft_problem_decomposition": {
        "skill_id": "soft_problem_decomposition",
        "name": "Requirements Clarification & Edge Case Identification",
        "parent_skill_id": "interview_skills",
        "description": "Asking clarifying questions, probing inputs/outputs, and proactively defining boundary edge cases.",
        "prerequisites": [],
        "difficulty": "Beginner",
        "applicable_roles": ["software_development_engineer", "ai_ml_engineer", "backend_developer", "frontend_developer"],
        "assessment_methods": ["ai_interview", "mock_interview"],
        "is_leaf": True
    },
    "soft_tradeoff_articulation": {
        "skill_id": "soft_tradeoff_articulation",
        "name": "Technical Trade-Off Articulation",
        "parent_skill_id": "interview_skills",
        "description": "Verbalizing pros and cons of alternative approaches (e.g. time vs space, latency vs consistency).",
        "prerequisites": ["soft_problem_decomposition"],
        "difficulty": "Intermediate",
        "applicable_roles": ["software_development_engineer", "ai_ml_engineer", "backend_developer", "frontend_developer"],
        "assessment_methods": ["ai_interview", "mock_interview"],
        "is_leaf": True
    }
}


class CanonicalSkillTaxonomy:
    """Helper service providing hierarchical catalog queries and relationship navigation."""

    @classmethod
    def get_skill(cls, skill_id: str) -> Optional[Dict[str, Any]]:
        return CANONICAL_SKILLS.get(skill_id)

    @classmethod
    def get_parent_domain(cls, domain_id: str) -> Optional[Dict[str, Any]]:
        return PARENT_DOMAINS.get(domain_id)

    @classmethod
    def get_subskills_for_domain(cls, domain_id: str) -> List[Dict[str, Any]]:
        return [s for s in CANONICAL_SKILLS.values() if s.get("parent_skill_id") == domain_id]

    @classmethod
    def get_all_skills(cls) -> Dict[str, Dict[str, Any]]:
        return CANONICAL_SKILLS

    @classmethod
    def get_all_domains(cls) -> Dict[str, Dict[str, Any]]:
        return PARENT_DOMAINS
