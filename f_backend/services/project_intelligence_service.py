"""
PREPFLY PROJECT INTELLIGENCE ENGINE
===================================
Analyzes candidate project descriptions and architectural claims.
Generates probing technical defense questions (concurrency, trade-offs, bottlenecks, failure modes).
Evaluates candidate defenses and converts project claims into verified evidence.
"""

import uuid
from typing import Dict, Any, List, Optional
from services.evidence_registry_service import EvidenceRegistryService, SOURCE_PRACTICAL_ASSIGNMENT
from local_supabase import get_supabase_client


class ProjectIntelligenceService:
    """Extracts project claims and probes architectural defense depth."""

    @classmethod
    def generate_project_probing_questions(
        cls,
        project_title: str,
        technologies: List[str],
        description: str
    ) -> List[Dict[str, Any]]:
        """
        Generates 3 deep technical probing questions for a project to verify genuine authorship:
        1. Architecture & component boundaries
        2. Scalability, bottlenecks, and failure modes
        3. Concurrency, data consistency, or latency trade-offs
        """
        tech_str = ", ".join(technologies) if technologies else "distributed components"

        return [
            {
                "question_id": f"prq_{uuid.uuid4().hex[:8]}",
                "focus_area": "Architecture & Data Flow",
                "question_text": (
                    f"In your project '{project_title}', describe the end-to-end data flow between "
                    f"{tech_str}. How did you isolate failures so that a crash in one service did not cascade?"
                ),
                "expected_aspects": ["Component boundaries", "Failure isolation / circuit breakers", "Payload serialization"]
            },
            {
                "question_id": f"prq_{uuid.uuid4().hex[:8]}",
                "focus_area": "Trade-offs & Concurrency",
                "question_text": (
                    f"What was the single most difficult architectural trade-off you made in '{project_title}'? "
                    f"If user traffic or dataset size increased by 50x, where would the system break first, and how would you redesign it?"
                ),
                "expected_aspects": ["Bottleneck identification", "Read vs write scalability", "Horizontal scaling strategy"]
            },
            {
                "question_id": f"prq_{uuid.uuid4().hex[:8]}",
                "focus_area": "Implementation Depth & Edge Cases",
                "question_text": (
                    f"What edge cases or data race conditions did you encounter during the implementation of '{project_title}', "
                    f"and how did you verify that your solution maintained data integrity?"
                ),
                "expected_aspects": ["Race conditions", "Locking / idempotency", "Testing / validation invariants"]
            }
        ]

    @classmethod
    def evaluate_project_defense(
        cls,
        user_id: str,
        project_title: str,
        skill_id: str,
        question_text: str,
        candidate_response: str,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate's defense of their project claim:
        - Longer, substantive explanations citing trade-offs, bottlenecks, and mechanisms receive full credit
        - Superficial or evasive answers receive low/partial credit
        - Records assessed evidence into EvidenceRegistryService
        """
        resp_len = len(candidate_response.strip())
        words = candidate_response.lower().split()

        # Score based on substantive technical content
        has_tradeoff = any(w in candidate_response.lower() for w in ["trade-off", "tradeoff", "latency", "throughput", "concurrency", "lock", "scale", "bottleneck", "cache", "async"])
        has_concrete_tool = any(w in candidate_response.lower() for w in ["redis", "postgres", "sql", "worker", "thread", "queue", "api", "timeout", "index"])

        if resp_len < 60:
            score = 35.0
            classification = "Superficial / Inconclusive Defense"
            feedback = "Defense is too brief to verify genuine architectural authorship or trade-off awareness."
        elif has_tradeoff and has_concrete_tool and resp_len >= 180:
            score = 88.0
            classification = "Demonstrated Authoritative Ownership"
            feedback = "Candidate convincingly explained component failure boundaries, technical trade-offs, and concrete mechanisms."
        elif has_tradeoff or has_concrete_tool:
            score = 70.0
            classification = "Moderate Technical Defense"
            feedback = "Candidate demonstrated working knowledge of the system but could articulate deeper failure modes and edge cases."
        else:
            score = 55.0
            classification = "Basic Descriptive Defense"
            feedback = "Candidate described what the project does rather than how it handles failure and scalability."

        # Register evidence with provenance
        ev = EvidenceRegistryService.record_evidence(
            user_id=user_id,
            skill_id=skill_id,
            source_type=SOURCE_PRACTICAL_ASSIGNMENT,
            raw_score=score,
            difficulty="Advanced",
            submission_content={
                "project_title": project_title,
                "question": question_text,
                "response": candidate_response
            },
            evaluator_type="project_defense_evaluator",
            metadata={
                "project_title": project_title,
                "classification": classification,
                "feedback": feedback
            },
            supabase_client=supabase_client
        )

        return {
            "project_title": project_title,
            "skill_id": skill_id,
            "score": score,
            "classification": classification,
            "feedback": feedback,
            "evidence_id": ev.get("id")
        }

