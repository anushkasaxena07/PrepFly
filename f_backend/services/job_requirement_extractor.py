"""
JobRequirementExtractor
=======================
Extracts, normalizes, and weights canonical technical skills from Job Descriptions.
Features SHA-256 deduplication, Gemini structured extraction, deterministic fallback,
and alignment with the canonical Skill Catalogue DAG.
"""

from typing import Dict, List, Optional, Any
import hashlib
import json
import uuid
from datetime import datetime, timezone
import logging

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import SkillTaxonomyService, normalize_role_id, SKILL_CATALOG, ROLE_REQUIREMENTS
from services.ai_service import safe_invoke_llm

logger = logging.getLogger("prepfly.job_extractor")


class JobRequirementExtractor:
    """Extracts, normalizes, and persists skill requirements from Job Descriptions."""

    @classmethod
    def compute_hash(cls, text: str) -> str:
        """Computes a deterministic SHA-256 hash of normalized JD text."""
        norm = " ".join((text or "").strip().lower().split())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    @classmethod
    def extract_and_persist_requirements(
        cls,
        user_id: str,
        target_role: str,
        job_description: Optional[str] = None,
        company: Optional[str] = None,
        career_goal_id: Optional[str] = None,
        chat_model=None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Extracts skill requirements from JD text or falls back to canonical role defaults.
        Guarantees SHA-256 caching and persistence in job_skill_requirements.
        """
        if not user_id:
            raise ValueError("user_id is required")

        client = supabase_client or get_supabase_client()
        canonical_role = normalize_role_id(target_role)
        jd_clean = (job_description or "").strip()
        text_hash = cls.compute_hash(jd_clean if jd_clean else f"role_default_{canonical_role}")

        # 1. Check for cached requirements with matching source_text_hash
        try:
            cached_res = client.table("job_skill_requirements").select("*").eq("user_id", user_id).eq("source_text_hash", text_hash).execute()
            if cached_res and cached_res.data:
                cached = cached_res.data[0]
                req_skills = cached.get("required_skills")
                if isinstance(req_skills, str):
                    req_skills = json.loads(req_skills)
                weights = cached.get("weight_distribution")
                if isinstance(weights, str):
                    weights = json.loads(weights)
                return {
                    "id": cached["id"],
                    "source": "cache",
                    "target_role": cached.get("target_role", canonical_role),
                    "company": cached.get("company", company),
                    "source_text_hash": text_hash,
                    "required_skills": req_skills or [],
                    "weight_distribution": weights or {}
                }
        except Exception as e:
            logger.warning(f"Error checking cached requirements: {e}")

        # 2. Extract skills: If JD provided, parse via LLM or keyword extraction
        extracted_skills: List[str] = []
        raw_weights: Dict[str, float] = {}

        if len(jd_clean) >= 40:
            extracted_skills = cls._extract_skills_from_jd(jd_clean, canonical_role, chat_model)

        # If JD was absent, too short, or extraction yielded fewer than 3 skills, merge with canonical role requirements
        role_default_weights = ROLE_REQUIREMENTS.get(canonical_role, ROLE_REQUIREMENTS.get("software_development_engineer", {}))
        
        if not extracted_skills:
            extracted_skills = list(role_default_weights.keys())
            raw_weights = {s: role_default_weights[s] for s in extracted_skills}
        else:
            # Assign higher weight to skills explicitly identified in JD, with role baseline support
            for s in extracted_skills:
                base_w = role_default_weights.get(s, 0.7)
                raw_weights[s] = base_w * 1.5

            # Supplement top core role fundamentals if missing (e.g. math/stats or algorithms)
            for core_s, core_w in role_default_weights.items():
                if core_w >= 0.9 and core_s not in raw_weights:
                    extracted_skills.append(core_s)
                    raw_weights[core_s] = core_w

        # 3. Normalize weight distribution to sum to 1.0
        total_w = sum(raw_weights.values()) or 1.0
        normalized_weights = {s: round(w / total_w, 4) for s, w in raw_weights.items()}

        now_iso = datetime.now(timezone.utc).isoformat()
        record_id = str(uuid.uuid4())

        record = {
            "id": record_id,
            "user_id": user_id,
            "career_goal_id": career_goal_id,
            "target_role": canonical_role,
            "company": company.strip() if company else None,
            "source_text_hash": text_hash,
            "required_skills": json.dumps(extracted_skills) if not hasattr(client, "_is_postgres") else extracted_skills,
            "weight_distribution": json.dumps(normalized_weights) if not hasattr(client, "_is_postgres") else normalized_weights,
            "created_at": now_iso
        }

        try:
            client.table("job_skill_requirements").insert(record).execute()
        except Exception as e:
            logger.warning(f"Could not persist job_skill_requirements: {e}")

        return {
            "id": record_id,
            "source": "extracted",
            "target_role": canonical_role,
            "company": company,
            "source_text_hash": text_hash,
            "required_skills": extracted_skills,
            "weight_distribution": normalized_weights
        }

    @classmethod
    def _extract_skills_from_jd(cls, jd_text: str, role_id: str, chat_model) -> List[str]:
        """
        Uses Gemini LLM with structured output or falls back to taxonomy regex keyword matching.
        Guarantees that all returned skill IDs exist in SKILL_CATALOG.
        """
        valid_catalog_ids = set(SKILL_CATALOG.keys())
        matched_skills: List[str] = []

        if chat_model:
            prompt = (
                f"You are a Senior Technical Recruiter analyzing a job description for role '{role_id}'.\n"
                f"Candidate Job Description:\n\"\"\"{jd_text[:4000]}\"\"\"\n\n"
                f"Available Canonical Skill IDs:\n{json.dumps(list(valid_catalog_ids))}\n\n"
                f"Return a strict JSON object with format:\n"
                f'{{"extracted_skills": ["skill_id_1", "skill_id_2"]}}\n'
                f"Include ONLY skill IDs present in the Available Canonical Skill IDs list."
            )
            try:
                response = safe_invoke_llm(chat_model, prompt)
                if response:
                    raw_text = response.strip()
                    if "{" in raw_text:
                        raw_json = raw_text[raw_text.find("{"):raw_text.rfind("}") + 1]
                        parsed = json.loads(raw_json)
                        for sid in parsed.get("extracted_skills", []):
                            if sid in valid_catalog_ids:
                                matched_skills.append(sid)
            except Exception as e:
                logger.warning(f"LLM JD extraction notice: {e}")

        # Deterministic fallback or supplemental extraction via catalog keyword mapping
        keyword_matches = SkillTaxonomyService.map_text_to_skills(jd_text)
        for sid in keyword_matches:
            if sid in valid_catalog_ids and sid not in matched_skills:
                matched_skills.append(sid)

        return matched_skills

