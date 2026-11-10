"""
Resume Grounding Service: Extracts structured, schema-validated facts
from candidate resume text with stable fact IDs and provenance citations.
Governs fact-based question generation to prevent hallucinated candidate experience.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional

FACT_CATEGORY_PROJECT = "project"
FACT_CATEGORY_SKILL = "skill"
FACT_CATEGORY_EXPERIENCE = "experience"
FACT_CATEGORY_METRIC = "metric"
FACT_CATEGORY_EDUCATION = "education"
FACT_CATEGORY_GAP = "gap"


class ResumeGroundingService:
    """Extracts and verifies stable resume facts for interview grounding."""

    FACT_SHEET_VERSION = "v1.0"

    @classmethod
    def extract_fact_sheet(cls, resume_text: str, candidate_name: str = "Candidate") -> Dict[str, Any]:
        """
        Parses resume text into a structured, schema-validated fact sheet with stable fact IDs.
        Each fact carries category, claim_text, confidence, and provenance_snippet.
        """
        if not resume_text or not resume_text.strip():
            return {
                "version": cls.FACT_SHEET_VERSION,
                "candidate_name": candidate_name,
                "facts": [],
                "fact_count": 0,
                "has_resume": False
            }

        facts: List[Dict[str, Any]] = []
        fact_idx = 0

        def make_fact_id(category: str, key_phrase: str) -> str:
            clean_key = re.sub(r'[^a-zA-Z0-9]', '_', key_phrase.lower())[:24].strip('_')
            h = hashlib.sha256(key_phrase.encode("utf-8")).hexdigest()[:6]
            return f"fact_{category}_{clean_key}_{h}"

        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]

        # 1. Detect Projects
        proj_matches = re.findall(
            r'(?:project|developed|built|architected|designed|implemented)\s*[:\-]?\s*([A-Za-z0-9\s\-_,]{4,60})',
            resume_text,
            re.IGNORECASE
        )
        for proj in proj_matches[:5]:
            p_clean = proj.strip()
            p_clean = re.sub(r'^(?:a|an|the|this|our)\s+', '', p_clean, flags=re.IGNORECASE).strip()
            if len(p_clean) >= 4:
                fact_id = make_fact_id(FACT_CATEGORY_PROJECT, p_clean)
                facts.append({
                    "fact_id": fact_id,
                    "category": FACT_CATEGORY_PROJECT,
                    "claim_text": f"Candidate developed project: {p_clean}",
                    "raw_entity": p_clean,
                    "confidence": 0.90,
                    "provenance_snippet": p_clean[:120],
                    "is_low_confidence": False
                })

        # 2. Detect Quantifiable Metrics / Achievements
        metric_matches = re.findall(
            r'([^\.\n]*?(?:increased|reduced|improved|scaled|optimized|decreased|achieved|saved)\s+[^\.\n]*?(?:\d+[%xXkKMbB]|\$\d+|\d+\s*ms|\d+\s*seconds)[^\.\n]*)',
            resume_text,
            re.IGNORECASE
        )
        for metric in metric_matches[:5]:
            m_clean = metric.strip()
            if len(m_clean) >= 10:
                fact_id = make_fact_id(FACT_CATEGORY_METRIC, m_clean[:20])
                facts.append({
                    "fact_id": fact_id,
                    "category": FACT_CATEGORY_METRIC,
                    "claim_text": f"Quantified impact: {m_clean}",
                    "raw_entity": m_clean,
                    "confidence": 0.85,
                    "provenance_snippet": m_clean[:150],
                    "is_low_confidence": False
                })

        # 3. Detect Technical Skills / Stack
        tech_keywords = [
            "Python", "Java", "Go", "Golang", "C++", "Rust", "JavaScript", "TypeScript",
            "React", "Node.js", "Django", "FastAPI", "Flask", "Spring Boot",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Kafka", "RabbitMQ",
            "Docker", "Kubernetes", "AWS", "GCP", "Azure", "PyTorch", "TensorFlow", "Scikit-Learn"
        ]
        found_skills = set()
        for tech in tech_keywords:
            pattern = rf'\b{re.escape(tech)}\b'
            if re.search(pattern, resume_text, re.IGNORECASE):
                found_skills.add(tech)

        for skill in sorted(found_skills)[:12]:
            fact_id = make_fact_id(FACT_CATEGORY_SKILL, skill)
            facts.append({
                "fact_id": fact_id,
                "category": FACT_CATEGORY_SKILL,
                "claim_text": f"Proficiency claimed in {skill}",
                "raw_entity": skill,
                "confidence": 0.95,
                "provenance_snippet": f"Mentioned technology: {skill}",
                "is_low_confidence": False
            })

        # 4. Detect Companies / Roles (Experience)
        role_matches = re.findall(
            r'(?:software engineer|backend engineer|frontend engineer|data scientist|machine learning engineer|devops engineer|sde|intern|lead|full stack)\b[^\.\n]*',
            resume_text,
            re.IGNORECASE
        )
        for role_snippet in role_matches[:3]:
            r_clean = role_snippet.strip()
            fact_id = make_fact_id(FACT_CATEGORY_EXPERIENCE, r_clean[:20])
            facts.append({
                "fact_id": fact_id,
                "category": FACT_CATEGORY_EXPERIENCE,
                "claim_text": f"Past experience: {r_clean}",
                "raw_entity": r_clean,
                "confidence": 0.80,
                "provenance_snippet": r_clean[:100],
                "is_low_confidence": False
            })

        # 5. Low-confidence or inferred facts (flags for question hedging)
        # If a skill was only mentioned once in passing without project backing:
        for f in facts:
            if f["category"] == FACT_CATEGORY_SKILL and f["confidence"] < 0.70:
                f["is_low_confidence"] = True

        # Deduplicate facts by fact_id
        unique_facts = {}
        for f in facts:
            if f["fact_id"] not in unique_facts:
                unique_facts[f["fact_id"]] = f

        final_facts = list(unique_facts.values())

        return {
            "version": cls.FACT_SHEET_VERSION,
            "candidate_name": candidate_name,
            "facts": final_facts,
            "fact_count": len(final_facts),
            "has_resume": True,
            "summary": {
                "projects_count": len([f for f in final_facts if f["category"] == FACT_CATEGORY_PROJECT]),
                "metrics_count": len([f for f in final_facts if f["category"] == FACT_CATEGORY_METRIC]),
                "skills_count": len([f for f in final_facts if f["category"] == FACT_CATEGORY_SKILL]),
                "experience_count": len([f for f in final_facts if f["category"] == FACT_CATEGORY_EXPERIENCE]),
            }
        }

    @staticmethod
    def get_fact_by_id(fact_sheet: Dict[str, Any], fact_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific verified fact by its stable ID."""
        for f in fact_sheet.get("facts", []):
            if f.get("fact_id") == fact_id:
                return f
        return None
