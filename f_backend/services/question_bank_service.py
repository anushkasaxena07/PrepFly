"""
Question Bank Service: Curated, pre-calibrated repository of interview questions with rubrics,
difficulty ratings, expected concepts, and follow-up paths across technical and behavioral domains.
"""

from typing import Dict, Any, List, Optional
import random

# Canonical Question Bank Catalog
CURATED_QUESTION_BANK: List[Dict[str, Any]] = [
    # ── DSA: Arrays & Hash Maps ──
    {
        "id": "DSA_ARR_001",
        "topic": "DSA",
        "subtopic": "Arrays & Two Pointers",
        "difficulty": "Easy",
        "interview_type": "Technical",
        "question_text": "Given an array of integers, how would you find two numbers that sum up to a specific target in O(N) time?",
        "expected_concepts": ["hash_map", "one_pass", "complement_lookup", "time_complexity"],
        "follow_up_concepts": ["handling_duplicate_elements", "memory_trade_offs_vs_two_pointer_sorting"],
        "rubric": {
            "correctness": "Must use hash map for O(N) time or sorted two-pointers for O(N log N)",
            "edge_cases": "Empty array, no pair exists, duplicate numbers summing to target"
        }
    },
    {
        "id": "DSA_ARR_002",
        "topic": "DSA",
        "subtopic": "Sliding Window",
        "difficulty": "Medium",
        "interview_type": "Technical",
        "question_text": "How does the sliding window technique optimize finding the longest substring without repeating characters compared to a brute-force approach?",
        "expected_concepts": ["sliding_window", "hash_set_or_map", "two_pointers", "o(n)_time"],
        "follow_up_concepts": ["dynamic_window_shrinking", "ascii_array_optimization"],
        "rubric": {
            "correctness": "Maintains window bounds [left, right], contracts window when duplicates appear",
            "edge_cases": "All unique characters, all identical characters, empty string"
        }
    },
    # ── DSA: Trees & Graphs ──
    {
        "id": "DSA_TREE_001",
        "topic": "DSA",
        "subtopic": "Binary Search Trees",
        "difficulty": "Medium",
        "interview_type": "Technical",
        "question_text": "What makes a Binary Search Tree valid, and how would you verify whether an arbitrary binary tree satisfies the BST invariant?",
        "expected_concepts": ["bst_invariant", "inorder_traversal", "range_bounds_min_max", "recursion"],
        "follow_up_concepts": ["handling_duplicate_keys", "balanced_vs_degenerate_trees"],
        "rubric": {
            "correctness": "Must state that all left descendants are strictly less and all right descendants greater; check with bounds (min, max)",
            "edge_cases": "Single node, duplicate values, skewed degenerate tree"
        }
    },
    {
        "id": "DSA_GRAPH_001",
        "topic": "DSA",
        "subtopic": "Graph Traversal",
        "difficulty": "Medium",
        "interview_type": "Technical",
        "question_text": "When traversing a directed graph, how do you distinguish between a cycle and multiple paths converging on the same vertex?",
        "expected_concepts": ["dfs_coloring", "recursion_stack", "visited_vs_visiting_states", "cycle_detection"],
        "follow_up_concepts": ["topological_sort_kahn_algorithm", "strongly_connected_components"],
        "rubric": {
            "correctness": "Uses 3-state tracking (unvisited, currently visiting / on stack, fully visited)",
            "edge_cases": "Disconnected components, self-loops"
        }
    },
    # ── Core CS: Operating Systems ──
    {
        "id": "CS_OS_001",
        "topic": "CS_FUNDAMENTALS",
        "subtopic": "Processes & Threads",
        "difficulty": "Medium",
        "interview_type": "Technical",
        "question_text": "What is the structural difference between a process and a thread, and what happens at the hardware/OS level during a context switch between them?",
        "expected_concepts": ["separate_address_space", "shared_heap_separate_stack", "pcb_vs_tcb", "tlb_flush_overhead"],
        "follow_up_concepts": ["goroutines_vs_kernel_threads", "false_sharing_in_cpu_cache"],
        "rubric": {
            "correctness": "Process has independent virtual memory; thread shares heap/data with peers. Process switch invalidates MMU/TLB cache",
            "edge_cases": "Kernel-level vs user-level threads"
        }
    },
    {
        "id": "CS_OS_002",
        "topic": "CS_FUNDAMENTALS",
        "subtopic": "Concurrency & Deadlocks",
        "difficulty": "Hard",
        "interview_type": "Technical",
        "question_text": "What are the four Coffman conditions required for a deadlock to occur, and how do modern databases prevent or recover from them?",
        "expected_concepts": ["mutual_exclusion", "hold_and_wait", "no_preemption", "circular_wait", "wait_for_graph"],
        "follow_up_concepts": ["two_phase_locking_2pl", "deadlock_detection_timeout"],
        "rubric": {
            "correctness": "Lists all 4 conditions correctly; explains deadlock detection via cycle detection in wait-for graph",
            "edge_cases": "Livelock vs deadlock"
        }
    },
    # ── Core CS: Computer Networks ──
    {
        "id": "CS_NET_001",
        "topic": "CS_FUNDAMENTALS",
        "subtopic": "Transport Layer",
        "difficulty": "Medium",
        "interview_type": "Technical",
        "question_text": "Walk me through the TCP three-way handshake and explain what problem the sequence numbers solve during network packet loss.",
        "expected_concepts": ["syn_syn_ack_ack", "initial_sequence_numbers", "packet_ordering", "duplicate_detection"],
        "follow_up_concepts": ["tcp_time_wait_state", "syn_flood_ddos_mitigation"],
        "rubric": {
            "correctness": "Client sends SYN(x), Server replies SYN(y)+ACK(x+1), Client sends ACK(y+1). Sequence numbers allow in-order reassembly",
            "edge_cases": "Delayed duplicate packets, asymmetric routing"
        }
    },
    # ── Core CS: DBMS ──
    {
        "id": "CS_DBMS_001",
        "topic": "CS_FUNDAMENTALS",
        "subtopic": "Transactions & ACID",
        "difficulty": "Medium",
        "interview_type": "Technical",
        "question_text": "What are database isolation levels, and what anomalies (dirty reads, non-repeatable reads, phantom reads) can occur at Read Committed versus Repeatable Read?",
        "expected_concepts": ["acid_isolation", "dirty_read", "non_repeatable_read", "phantom_read", "mvcc"],
        "follow_up_concepts": ["serializable_snapshot_isolation", "optimistic_concurrency_control"],
        "rubric": {
            "correctness": "Correctly defines anomalies; Read Committed prevents dirty reads; Repeatable Read prevents non-repeatable reads via snapshots/locks",
            "edge_cases": "Snapshot isolation write skew"
        }
    },
    # ── System Design ──
    {
        "id": "SYS_DES_001",
        "topic": "SYSTEM_DESIGN",
        "subtopic": "Caching & High Availability",
        "difficulty": "Medium",
        "interview_type": "System Design",
        "question_text": "When designing a distributed cache using Redis, how do you handle cache invalidation, cache stampede (thundering herd), and cold starts?",
        "expected_concepts": ["cache_aside", "ttl_expiry", "distributed_locks_or_mutex", "probabilistic_early_expiration"],
        "follow_up_concepts": ["consistent_hashing", "write_through_vs_write_back"],
        "rubric": {
            "correctness": "Explains Cache-Aside pattern; mitigates stampede via distributed lock (Redlock) or pre-warming cache",
            "edge_cases": "Redis master crash before replication"
        }
    },
    {
        "id": "SYS_DES_002",
        "topic": "SYSTEM_DESIGN",
        "subtopic": "Database Sharding & Replication",
        "difficulty": "Hard",
        "interview_type": "System Design",
        "question_text": "If a single relational database instance exceeds its storage and I/O capacity, how do you decide between horizontal sharding versus introducing read replicas, and what are the trade-offs?",
        "expected_concepts": ["read_replicas_for_read_heavy", "sharding_for_write_or_storage", "cross_shard_joins", "shard_key_selection"],
        "follow_up_concepts": ["re-sharding_strategies", "two_phase_commit_distributed_transactions"],
        "rubric": {
            "correctness": "Read replicas scale read throughput but not writes or storage; sharding scales writes but introduces cross-shard join complexity",
            "edge_cases": "Hotspot shard key distribution"
        }
    },
    # ── Behavioral: Leadership & Conflict (STAR) ──
    {
        "id": "BEH_STAR_001",
        "topic": "HR_BEHAVIORAL",
        "subtopic": "Conflict Resolution",
        "difficulty": "Medium",
        "interview_type": "Behavioral",
        "question_text": "Tell me about a time when you strongly disagreed with an architectural decision or technical approach proposed by a teammate. How did you handle the discussion, and what was the outcome?",
        "expected_concepts": ["situation", "task", "action", "result", "data_driven_evaluation", "disagree_and_commit"],
        "follow_up_concepts": ["handling_unfavorable_decisions", "maintaining_team_morale"],
        "rubric": {
            "correctness": "Follows STAR structure; demonstrates data-driven reasoning rather than emotional confrontation; commits to final team decision",
            "edge_cases": "Blaming teammate without personal accountability"
        }
    },
    {
        "id": "BEH_STAR_002",
        "topic": "HR_BEHAVIORAL",
        "subtopic": "Production Incident & Ownership",
        "difficulty": "Medium",
        "interview_type": "Behavioral",
        "question_text": "Describe a situation where a production deployment or unexpected outage occurred under your watch. How did you triage the incident, communicate with stakeholders, and prevent recurrence?",
        "expected_concepts": ["incident_triage", "rollback_mitigation", "transparent_communication", "blameless_postmortem"],
        "follow_up_concepts": ["root_cause_analysis_5_whys", "monitoring_alerts_sla"],
        "rubric": {
            "correctness": "Prioritizes immediate user recovery (rollback/feature flag), transparent updates, followed by blameless root cause analysis",
            "edge_cases": "Hiding mistakes or delaying escalation"
        }
    }
]


class QuestionBankService:
    """Manages question retrieval, filtering by topic/difficulty, and anti-repetition selection."""

    @staticmethod
    def get_candidate_questions(
        topic: str,
        difficulty: str = "Medium",
        exclude_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Filters question bank by topic and difficulty, excluding previously asked questions."""
        exclude = set(exclude_ids or [])
        t_clean = topic.upper()

        matches = []
        for q in CURATED_QUESTION_BANK:
            if q["id"] in exclude:
                continue
            if t_clean in q["topic"].upper() or (t_clean == "DSA" and q["topic"] == "DSA") or (t_clean == "SYSTEM_DESIGN" and q["topic"] == "SYSTEM_DESIGN"):
                matches.append(q)

        return matches

    @staticmethod
    def select_best_question(
        topic: str,
        difficulty: str = "Medium",
        previous_question_texts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Selects a calibrated question from the bank with minimal semantic repetition."""
        prev_texts = set(t.lower().strip() for t in (previous_question_texts or []))
        candidates = QuestionBankService.get_candidate_questions(topic, difficulty)

        # Filter out questions whose text is already asked
        fresh_candidates = [c for c in candidates if c["question_text"].lower().strip() not in prev_texts]
        if fresh_candidates:
            # Prefer matching difficulty
            diff_matches = [c for c in fresh_candidates if c["difficulty"].lower() == difficulty.lower()]
            if diff_matches:
                return random.choice(diff_matches)
            return random.choice(fresh_candidates)

        # If all exhausted, fallback to any question in topic
        all_topic = [q for q in CURATED_QUESTION_BANK if topic.upper() in q["topic"].upper()]
        return random.choice(all_topic) if all_topic else CURATED_QUESTION_BANK[0]

