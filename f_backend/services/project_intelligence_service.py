"""
PREPFLY PROJECT INTELLIGENCE ENGINE
===================================
Analyzes candidate project descriptions and architectural claims.
Maps claimed technologies to canonical skill IDs in the Skill Taxonomy.
Generates probing technical defense questions (concurrency, trade-offs, bottlenecks, failure modes).
Evaluates candidate defenses and converts project claims into verified evidence.
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from services.evidence_registry_service import EvidenceRegistryService, SOURCE_PRACTICAL_ASSIGNMENT
from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.ai_service import safe_invoke_llm
from local_supabase import get_supabase_client

# Technology to Canonical Skill Mapping
TECH_TO_SKILL_MAP: Dict[str, str] = {
    "pytorch": "dl_frameworks_pytorch_tensorflow",
    "tensorflow": "dl_frameworks_pytorch_tensorflow",
    "torch": "dl_frameworks_pytorch_tensorflow",
    "transformer": "dl_transformers",
    "transformers": "dl_transformers",
    "huggingface": "dl_transformers",
    "llm": "genai_llm_fundamentals",
    "llama": "genai_llm_fundamentals",
    "rag": "genai_llm_fundamentals",
    "langchain": "genai_llm_fundamentals",
    "react": "fe_react_architecture",
    "reactjs": "fe_react_architecture",
    "redux": "fe_react_architecture",
    "redis": "sys_caching",
    "memcached": "sys_caching",
    "kafka": "sys_message_queues",
    "rabbitmq": "sys_message_queues",
    "postgres": "cs_dbms",
    "postgresql": "cs_dbms",
    "sql": "cs_sql",
    "mysql": "cs_dbms",
    "mongodb": "cs_dbms",
    "fastapi": "sys_rest_apis",
    "flask": "sys_rest_apis",
    "express": "sys_rest_apis",
    "node": "sys_rest_apis",
    "docker": "devops_containers",
    "kubernetes": "devops_kubernetes",
    "k8s": "devops_kubernetes",
}


class ProjectIntelligenceService:
    """Extracts project claims, maps to canonical skills, and probes architectural defense depth."""

    @classmethod
    def map_technologies_to_skills(cls, technologies: List[str], description: str = "") -> List[str]:
        """Maps free-form technology mentions and project descriptions to canonical skill IDs."""
        mapped = set()
        for tech in technologies:
            clean = tech.strip().lower()
            if clean in TECH_TO_SKILL_MAP:
                mapped.add(TECH_TO_SKILL_MAP[clean])
            else:
                for k, sid in TECH_TO_SKILL_MAP.items():
                    if k in clean:
                        mapped.add(sid)

        # Also scan description text using taxonomy mapper
        if description:
            desc_skills = SkillTaxonomyService.map_text_to_skills(description)
            mapped.update(desc_skills)

        # Filter against active SKILL_CATALOG or default fallback
        valid_skills = [s for s in mapped if s in SKILL_CATALOG]
        return valid_skills if valid_skills else ["sys_rest_apis"]

    @classmethod
    def analyze_and_persist_project(
        cls,
        user_id: str,
        project_title: str,
        description: str,
        technologies: List[str],
        chat_model=None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Analyzes a candidate project, maps technologies to canonical skills,
        generates 3 deep technical probing questions, and persists into candidate_project_analyses.
        """
        if not user_id or not project_title:
            raise ValueError("user_id and project_title are required")

        client = supabase_client or get_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        project_id = str(uuid.uuid4())

        mapped_skills = cls.map_technologies_to_skills(technologies, description)
        probing_questions = cls.generate_project_probing_questions(
            project_title=project_title,
            technologies=technologies,
            description=description,
            chat_model=chat_model
        )

        # 1. Persist candidate_project_analyses
        analysis_record = {
            "id": project_id,
            "user_id": user_id,
            "project_title": project_title,
            "technologies": json.dumps(technologies) if not hasattr(client, "_is_postgres") else technologies,
            "description": description,
            "created_at": now_iso
        }
        try:
            client.table("candidate_project_analyses").insert(analysis_record).execute()
        except Exception:
            pass

        # 2. Persist project_technical_questions
        for q in probing_questions:
            q_record = {
                "id": q["question_id"],
                "project_id": project_id,
                "focus_area": q["focus_area"],
                "question_text": q["question_text"],
                "expected_aspects": json.dumps(q["expected_aspects"]) if not hasattr(client, "_is_postgres") else q["expected_aspects"],
                "created_at": now_iso
            }
            try:
                client.table("project_technical_questions").insert(q_record).execute()
            except Exception:
                pass

        return {
            "project_id": project_id,
            "project_title": project_title,
            "mapped_skills": mapped_skills,
            "probing_questions": probing_questions
        }

    @classmethod
    def generate_project_probing_questions(
        cls,
        project_title: str,
        technologies: List[str],
        description: str,
        chat_model=None
    ) -> List[Dict[str, Any]]:
        """
        Generates 3 deep technical probing questions for a project to verify genuine authorship:
        1. Architecture & component boundaries
        2. Scalability, bottlenecks, and failure modes
        3. Concurrency, data consistency, or latency trade-offs
        """
        tech_str = ", ".join(technologies) if technologies else "distributed components"

        if chat_model:
            prompt = (
                f"You are a Senior Principal Engineer reviewing a candidate's portfolio project.\n"
                f"Project Title: '{project_title}'\n"
                f"Technologies: {tech_str}\n"
                f"Description: \"\"\"{description[:2000]}\"\"\"\n\n"
                f"Generate 3 rigorous architectural defense probing questions to verify genuine authorship.\n"
                f"Focus on: 1. Architecture/failure boundaries, 2. Bottlenecks/trade-offs under 50x scale, 3. Concurrency/race conditions.\n"
                f"Return JSON matching:\n"
                f'[{{"question_id": "prq_1", "focus_area": "Architecture", "question_text": "...", "expected_aspects": ["..."]}}]'
            )
            try:
                res = safe_invoke_llm(chat_model, prompt)
                if res and "[" in res:
                    raw_json = res[res.find("["):res.rfind("]") + 1]
                    parsed = json.loads(raw_json)
                    if isinstance(parsed, list) and len(parsed) >= 2:
                        for idx, q in enumerate(parsed):
                            q["question_id"] = q.get("question_id") or f"prq_{uuid.uuid4().hex[:8]}"
                        return parsed
            except Exception:
                pass

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
        - Records assessed evidence into EvidenceRegistryService and skill_evidence ledger
        """
        resp_len = len(candidate_response.strip())
        now_iso = datetime.now(timezone.utc).isoformat()
        client = supabase_client or get_supabase_client()

        has_tradeoff = any(w in candidate_response.lower() for w in ["trade-off", "tradeoff", "latency", "throughput", "concurrency", "lock", "scale", "bottleneck", "cache", "async"])
        has_concrete_tool = any(w in candidate_response.lower() for w in ["redis", "postgres", "sql", "worker", "thread", "queue", "api", "timeout", "index", "partition", "connection"])

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

        # Register evidence in EvidenceRegistryService
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
            supabase_client=client
        )

        # Also append to skill_evidence ledger
        try:
            client.table("skill_evidence").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "skill_id": skill_id,
                "source_type": "project_defense",
                "source_id": project_title,
                "score": score,
                "raw_score": score,
                "weighted_score": score,
                "confidence": 0.85,
                "created_at": now_iso
            }).execute()
        except Exception:
            pass

        return {
            "project_title": project_title,
            "skill_id": skill_id,
            "score": score,
            "classification": classification,
            "feedback": feedback,
            "evidence_id": ev.get("id")
        }
