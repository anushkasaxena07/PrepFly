"""
Spaced Revision & Knowledge Retention Engine for PrepFly Intelligence.
Implements adaptive retrieval practice with exponential interval spacing (Day 1, 3, 7, 14),
forgetting curve mitigation, performance-adapted interval adjustments, and drill generation.
"""

from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timezone, timedelta

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.skill_profiling_service import SkillProfilingService

class RevisionScheduler:
    """Manages spaced repetition schedules, retrieval drill evaluations, and retention tracking."""

    # Ebbinghaus-adapted spacing intervals in days
    STAGE_INTERVALS = {
        1: 1,   # 24 hours (immediate consolidation)
        2: 3,   # 3 days
        3: 7,   # 1 week
        4: 14   # 2 weeks (long-term retention gate)
    }

    @classmethod
    def schedule_initial_revision(
        cls,
        user_id: str,
        skill_id: str,
        initial_score: float = 75.0
    ) -> Dict[str, Any]:
        """
        Schedules a skill for spaced revision following learning or assessment.
        Initializes at Stage 1 (due in 24 hours).
        """
        supabase = get_supabase_client()
        now = datetime.now(timezone.utc)
        next_due = now + timedelta(days=cls.STAGE_INTERVALS[1])

        # Check if schedule already exists
        existing_res = supabase.table("revision_schedules").select("*").eq("user_id", user_id).eq("skill_id", skill_id).execute()
        existing = existing_res.data if (existing_res and existing_res.data) else []

        if existing:
            rec_id = existing[0]["id"]
            update_payload = {
                "interval_stage": 1,
                "next_due_at": next_due.isoformat(),
                "next_revision_date": next_due.isoformat(),
                "last_reviewed_at": now.isoformat(),
                "last_score": round(float(initial_score), 1),
                "status": "ACTIVE",
                "updated_at": now.isoformat()
            }
            supabase.table("revision_schedules").update(update_payload).eq("id", rec_id).execute()
            return {**existing[0], **update_payload}

        schedule_id = str(uuid.uuid4())
        record = {
            "id": schedule_id,
            "user_id": user_id,
            "skill_id": skill_id,
            "interval_stage": 1,
            "last_reviewed_at": now.isoformat(),
            "next_due_at": next_due.isoformat(),
            "next_revision_date": next_due.isoformat(),
            "consecutive_successes": 0,
            "last_score": round(float(initial_score), 1),
            "status": "ACTIVE",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        supabase.table("revision_schedules").insert(record).execute()
        return record

    @classmethod
    def record_revision_attempt(
        cls,
        user_id: str,
        skill_id: str,
        score: float,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Records the outcome of a spaced revision drill.
        - score >= 70%: advances to next interval stage (or completes if stage 4 passed).
        - 50% <= score < 70%: maintains current stage.
        - score < 50%: contracts interval to Stage 1 (remedial drill).
        Also registers evidence to the skill profiling engine.
        """
        supabase = get_supabase_client()
        now = datetime.now(timezone.utc)
        score_f = round(max(0.0, min(100.0, float(score))), 1)

        res = supabase.table("revision_schedules").select("*").eq("user_id", user_id).eq("skill_id", skill_id).execute()
        schedules = res.data if (res and res.data) else []

        if not schedules:
            # Create fresh
            sched = cls.schedule_initial_revision(user_id, skill_id, initial_score=score_f)
            stage = sched["interval_stage"]
            consecutive = 0
            rec_id = sched["id"]
        else:
            sched = schedules[0]
            stage = int(sched.get("interval_stage", 1))
            consecutive = int(sched.get("consecutive_successes", 0))
            rec_id = sched["id"]

        status = "ACTIVE"

        if score_f >= 70.0:
            consecutive += 1
            if stage < 4:
                stage += 1
            elif consecutive >= 4:
                status = "COMPLETED"
            days = cls.STAGE_INTERVALS.get(stage, 14)
            next_due = now + timedelta(days=days)
            outcome = "ADVANCED"
        elif score_f >= 50.0:
            # Maintained
            days = cls.STAGE_INTERVALS.get(stage, 1)
            next_due = now + timedelta(days=days)
            outcome = "MAINTAINED"
        else:
            # Regressed to stage 1 remedial
            stage = 1
            consecutive = 0
            next_due = now + timedelta(days=cls.STAGE_INTERVALS[1])
            outcome = "REGRESSED_REMEDIAL"

        update_payload = {
            "interval_stage": stage,
            "last_reviewed_at": now.isoformat(),
            "next_due_at": next_due.isoformat(),
            "next_revision_date": next_due.isoformat(),
            "consecutive_successes": consecutive,
            "last_score": score_f,
            "status": status,
            "updated_at": now.isoformat()
        }
        supabase.table("revision_schedules").update(update_payload).eq("id", rec_id).execute()

        # Ingest evidence into SkillProfilingService
        SkillProfilingService.record_evidence(
            user_id=user_id,
            skill_id=skill_id,
            source="REVISION",
            score=score_f,
            raw_data={
                "revision_stage": stage,
                "outcome": outcome,
                "consecutive_successes": consecutive,
                "notes": notes
            }
        )

        return {
            "schedule_id": rec_id,
            "skill_id": skill_id,
            "score": score_f,
            "outcome": outcome,
            "new_stage": stage,
            "next_due_at": next_due.isoformat(),
            "status": status,
            "consecutive_successes": consecutive
        }

    @classmethod
    def get_due_revisions(cls, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves active revision schedules where next_due_at is now or in the past."""
        supabase = get_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()

        res = supabase.table("revision_schedules").select("*").eq("user_id", user_id).eq("status", "ACTIVE").lte("next_due_at", now_iso).limit(limit).execute()
        items = res.data if (res and res.data) else []

        enriched = []
        for it in items:
            skill_id = it.get("skill_id", "")
            cat_entry = SKILL_CATALOG.get(skill_id, {})
            enriched.append({
                **it,
                "skill_name": cat_entry.get("name", skill_id.replace("_", " ").title()),
                "category": cat_entry.get("category", "General"),
                "interval_days": cls.STAGE_INTERVALS.get(int(it.get("interval_stage", 1)), 1)
            })
        return enriched

    @classmethod
    def get_all_schedules(cls, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves all revision schedules for a user."""
        supabase = get_supabase_client()
        res = supabase.table("revision_schedules").select("*").eq("user_id", user_id).order("next_due_at", desc=False).execute()
        items = res.data if (res and res.data) else []

        enriched = []
        for it in items:
            skill_id = it.get("skill_id", "")
            cat_entry = SKILL_CATALOG.get(skill_id, {})
            enriched.append({
                **it,
                "skill_name": cat_entry.get("name", skill_id.replace("_", " ").title()),
                "category": cat_entry.get("category", "General"),
                "interval_days": cls.STAGE_INTERVALS.get(int(it.get("interval_stage", 1)), 1)
            })
        return enriched

    @classmethod
    def generate_retrieval_drill(cls, skill_id: str) -> Dict[str, Any]:
        """
        Produces a concise 5-minute retrieval drill for the given skill,
        featuring targeted conceptual and diagnostic validation questions.
        """
        cat_entry = SKILL_CATALOG.get(skill_id, {})
        skill_name = cat_entry.get("name", skill_id.replace("_", " ").title())
        category = cat_entry.get("category", "General")

        drills = {
            "dsa_arrays": {
                "question": "Explain how hash collisions are resolved in HashMap implementations and why worst-case lookup can degrade to O(N).",
                "rubric": "Mentions chaining (linked lists / balanced trees) or open addressing (linear/quadratic probing), load factor rehashing, and worst-case hash clustering.",
                "duration_minutes": 5
            },
            "dsa_hashing": {
                "question": "Explain how hash collisions are resolved in HashMap implementations and why worst-case lookup can degrade to O(N).",
                "rubric": "Mentions chaining (linked lists / balanced trees) or open addressing (linear/quadratic probing), load factor rehashing, and worst-case hash clustering.",
                "duration_minutes": 5
            },
            "arrays_hashing": {
                "question": "Explain how hash collisions are resolved in HashMap implementations and why worst-case lookup can degrade to O(N).",
                "rubric": "Mentions chaining (linked lists / balanced trees) or open addressing (linear/quadratic probing), load factor rehashing, and worst-case hash clustering.",
                "duration_minutes": 5
            },
            "dsa_trees": {
                "question": "What is the key invariant of a Binary Search Tree (BST) versus a Binary Heap, and what traversal outputs elements in sorted order?",
                "rubric": "BST left < root < right; in-order traversal yields sorted sequence; Heap only enforces parent-child order.",
                "duration_minutes": 5
            },
            "trees": {
                "question": "What is the key invariant of a Binary Search Tree (BST) versus a Binary Heap, and what traversal outputs elements in sorted order?",
                "rubric": "BST left < root < right; in-order traversal yields sorted sequence; Heap only enforces parent-child order.",
                "duration_minutes": 5
            },
            "dsa_dp": {
                "question": "What two core properties must an optimization problem exhibit to be solvable via Dynamic Programming, and how does memoization differ from tabulation?",
                "rubric": "Optimal substructure and overlapping subproblems. Memoization is top-down recursion with cache; tabulation is bottom-up iterative table filling.",
                "duration_minutes": 5
            },
            "dynamic_programming": {
                "question": "What two core properties must an optimization problem exhibit to be solvable via Dynamic Programming, and how does memoization differ from tabulation?",
                "rubric": "Optimal substructure and overlapping subproblems. Memoization is top-down recursion with cache; tabulation is bottom-up iterative table filling.",
                "duration_minutes": 5
            },
            "sys_caching": {
                "question": "Compare Cache-Aside (Lazy Loading) with Write-Through caching in terms of read/write latency and data freshness.",
                "rubric": "Cache-aside: app loads on miss, potential stale data. Write-through: writes to cache and DB simultaneously, higher write latency but immediate read freshness.",
                "duration_minutes": 5
            },
            "caching_strategies": {
                "question": "Compare Cache-Aside (Lazy Loading) with Write-Through caching in terms of read/write latency and data freshness.",
                "rubric": "Cache-aside: app loads on miss, potential stale data. Write-through: writes to cache and DB simultaneously, higher write latency but immediate read freshness.",
                "duration_minutes": 5
            }
        }

        default_drill = {
            "question": f"Summarize the core invariants, trade-offs, and best practices for {skill_name}.",
            "rubric": f"Accurate technical explanation of {skill_name} semantics, time/space complexity, and practical application patterns.",
            "duration_minutes": 5
        }

        selected = drills.get(skill_id, default_drill)
        return {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "category": category,
            "question": selected["question"],
            "rubric": selected["rubric"],
            "suggested_duration_minutes": selected["duration_minutes"]
        }
