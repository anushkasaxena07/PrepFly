"""
PREPFLY EVIDENCE REGISTRY SERVICE
=================================
Records and manages immutable, provenance-backed evidence of candidate skills.
Distinguishes between unverified discovery signals (claimed exposure, project mentions)
and verified demonstrated proficiency (assessments, coding execution, interview rubrics).
Enforces deduplication to prevent score inflation from identical submissions.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from local_supabase import get_supabase_client

# Valid Evidence Source Types
SOURCE_RESUME_MENTION = "resume_mention"
SOURCE_PROJECT_MENTION = "project_mention"
SOURCE_REPOSITORY_SCAN = "repository_scan"
SOURCE_DIAGNOSTIC_ASSESSMENT = "diagnostic_assessment"
SOURCE_CODING_SUBMISSION = "coding_submission"
SOURCE_PRACTICAL_ASSIGNMENT = "practical_assignment"
SOURCE_AI_INTERVIEW = "ai_interview"
SOURCE_MOCK_INTERVIEW = "mock_interview"
SOURCE_VERIFIED_EXPERIENCE = "verified_experience"

# Status Classifications
STATUS_CLAIMED_EXPOSURE = "CLAIMED_EXPOSURE"
STATUS_PROJECT_EXPOSURE = "PROJECT_EXPOSURE"
STATUS_ASSESSED = "ASSESSED"
STATUS_VERIFIED_CODE = "VERIFIED_CODE"
STATUS_VERIFIED_EXPERIENCE = "VERIFIED_EXPERIENCE"

# Mapping from source type to default validity classification
SOURCE_STATUS_MAP = {
    SOURCE_RESUME_MENTION: STATUS_CLAIMED_EXPOSURE,
    SOURCE_PROJECT_MENTION: STATUS_PROJECT_EXPOSURE,
    SOURCE_REPOSITORY_SCAN: STATUS_VERIFIED_CODE,
    SOURCE_DIAGNOSTIC_ASSESSMENT: STATUS_ASSESSED,
    SOURCE_CODING_SUBMISSION: STATUS_VERIFIED_CODE,
    SOURCE_PRACTICAL_ASSIGNMENT: STATUS_ASSESSED,
    SOURCE_AI_INTERVIEW: STATUS_ASSESSED,
    SOURCE_MOCK_INTERVIEW: STATUS_ASSESSED,
    SOURCE_VERIFIED_EXPERIENCE: STATUS_VERIFIED_EXPERIENCE
}


class EvidenceRegistryService:
    """Manages the registration, retrieval, and deduplication of skill evidence."""

    @classmethod
    def compute_provenance_hash(
        cls,
        user_id: str,
        skill_id: str,
        source_type: str,
        content_payload: Any
    ) -> str:
        """Generates a deterministic SHA-256 fingerprint for submission deduplication."""
        serialized = json.dumps(content_payload, sort_keys=True, default=str) if content_payload else ""
        raw = f"{user_id}:{skill_id}:{source_type}:{serialized}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def record_evidence(
        cls,
        user_id: str,
        skill_id: str,
        source_type: str,
        raw_score: Optional[float] = None,
        difficulty: str = "Intermediate",
        source_id: Optional[str] = None,
        submission_content: Any = None,
        evaluation_rubric: Optional[Dict[str, Any]] = None,
        evaluator_type: str = "automated_engine",
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Records a new verifiable skill evidence item with deduplication.
        If an identical submission hash exists for this user and skill,
        it returns the existing record without score inflation.
        """
        supabase = supabase_client or get_supabase_client()
        now_iso = created_at or datetime.now(timezone.utc).isoformat()

        validity_status = SOURCE_STATUS_MAP.get(source_type, STATUS_ASSESSED)

        # Quality weights by difficulty and source
        diff_lower = (difficulty or "Intermediate").lower()
        diff_multiplier = 0.8 if "beg" in diff_lower else (1.2 if "adv" in diff_lower else 1.0)

        # Non-assessed discovery signals must have raw_score = None
        if validity_status in (STATUS_CLAIMED_EXPOSURE, STATUS_PROJECT_EXPOSURE):
            normalized_score = None
            evidence_quality = 0.25
        else:
            normalized_score = float(raw_score) if raw_score is not None else 0.0
            evidence_quality = min(1.0, round(diff_multiplier * 0.85, 2))

        provenance_hash = cls.compute_provenance_hash(user_id, skill_id, source_type, submission_content or raw_score)

        # Check for existing duplicate submission
        try:
            dup_res = supabase.table("skill_evidence_registry").select("*") \
                .eq("user_id", user_id) \
                .eq("provenance_hash", provenance_hash) \
                .execute()
            if dup_res and dup_res.data:
                # Return existing record to prevent duplicate score inflation
                return {
                    **dup_res.data[0],
                    "is_duplicate": True
                }
        except Exception:
            pass

        evidence_id = f"ev_{uuid.uuid4().hex[:16]}"
        record = {
            "id": evidence_id,
            "user_id": user_id,
            "skill_id": skill_id,
            "source_type": source_type,
            "source_id": source_id or evidence_id,
            "raw_score": raw_score,
            "normalized_score": normalized_score,
            "difficulty": difficulty,
            "evidence_quality": evidence_quality,
            "validity_status": validity_status,
            "evaluator_type": evaluator_type,
            "evaluation_rubric": json.dumps(evaluation_rubric or {}),
            "provenance_hash": provenance_hash,
            "metadata": json.dumps(metadata or {}),
            "created_at": now_iso
        }

        try:
            supabase.table("skill_evidence_registry").insert(record).execute()
        except Exception as e:
            # Table might be missing in older environments; save to fallback or local
            try:
                from local_supabase import local_supabase
                local_supabase.table("skill_evidence_registry").insert(record).execute()
            except Exception as loc_err:
                print("Evidence insertion fallback notice:", loc_err)

        return {
            **record,
            "is_duplicate": False
        }

    @classmethod
    def get_evidence_for_candidate(
        cls,
        user_id: str,
        skill_id: Optional[str] = None,
        source_type: Optional[str] = None,
        supabase_client=None
    ) -> List[Dict[str, Any]]:
        """Retrieves verified evidence records for a candidate with optional filtering."""
        supabase = supabase_client or get_supabase_client()
        query = supabase.table("skill_evidence_registry").select("*").eq("user_id", user_id)
        if skill_id:
            query = query.eq("skill_id", skill_id)
        if source_type:
            query = query.eq("source_type", source_type)

        res = query.order("created_at", desc=True).execute()
        rows = res.data if (res and res.data) else []

        # Parse JSON fields
        for r in rows:
            for field in ("evaluation_rubric", "metadata"):
                if isinstance(r.get(field), str):
                    try:
                        r[field] = json.loads(r[field])
                    except Exception:
                        r[field] = {}
        return rows
