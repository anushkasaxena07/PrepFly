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

        # Select 5 representative questions from the bank
        selected_questions = DIAGNOSTIC_BANK[:5]
        if role_key in ("frontend_developer", "frontend_engineer"):
            selected_questions = [DIAGNOSTIC_BANK[0], DIAGNOSTIC_BANK[3], DIAGNOSTIC_BANK[5], DIAGNOSTIC_BANK[6], DIAGNOSTIC_BANK[8]]
        elif role_key in ("backend_developer", "backend_engineer"):
            selected_questions = [DIAGNOSTIC_BANK[1], DIAGNOSTIC_BANK[3], DIAGNOSTIC_BANK[4], DIAGNOSTIC_BANK[5], DIAGNOSTIC_BANK[7]]

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
            "results": evaluated_results
        }

    evaluate_attempt = evaluate_and_submit_answers
