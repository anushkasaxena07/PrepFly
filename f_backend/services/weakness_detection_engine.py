"""
PREPFLY WEAKNESS DETECTION ENGINE
=================================
Strictly identifies candidate weaknesses and skill gaps.
Guiding Law:
- Unassessed skills, resume mentions, or project claims are NEVER labeled as weaknesses.
- Weakness requires verified, provenance-backed assessment failure (< 60%).
- Categorizes severity into VERIFIED_GAP (< 45%) and DEVELOPING (45-59%).
- Attaches actionable remedial assignments and rubric failure criteria.
"""

from typing import Dict, Any, List, Optional
from services.canonical_skill_taxonomy import CanonicalSkillTaxonomy
from services.evidence_registry_service import EvidenceRegistryService
from services.evidence_scoring_engine import EvidenceScoringEngine
from local_supabase import get_supabase_client


class WeaknessDetectionEngine:
    """Detects verified technical skill gaps without false positives on unassessed claims."""

    @classmethod
    def detect_weaknesses(
        cls,
        user_id: str,
        target_role: Optional[str] = None,
        supabase_client=None
    ) -> List[Dict[str, Any]]:
        """
        Scans all candidate evidence and identifies verified assessment gaps:
        - Filters ONLY assessed skills with demonstrated proficiency < 60%
        - Never flags unassessed skills, resume-only skills, or project-only mentions
        - Attaches specific remedial actions and supporting assessment provenance
        """
        supabase = supabase_client or get_supabase_client()
        all_evidence = EvidenceRegistryService.get_evidence_for_candidate(
            user_id=user_id,
            supabase_client=supabase
        )

        # Collect unique skills from evidence
        unique_skill_ids = set(e.get("skill_id") for e in all_evidence if e.get("skill_id"))

        detected_weaknesses = []

        for sid in unique_skill_ids:
            skill_evs = [e for e in all_evidence if e.get("skill_id") == sid]
            skill_eval = EvidenceScoringEngine.evaluate_skill(
                user_id=user_id,
                skill_id=sid,
                evidence_list=skill_evs,
                supabase_client=supabase
            )

            # Rule 1: Must be explicitly assessed
            if not skill_eval["is_assessed"] or skill_eval["proficiency"] is None:
                continue

            prof = float(skill_eval["proficiency"])

            # Rule 2: Must have demonstrated failure / shortfall below 60%
            if prof < 60.0:
                severity = "VERIFIED_GAP" if prof < 45.0 else "DEVELOPING"
                skill_meta = CanonicalSkillTaxonomy.get_skill(sid) or {}

                # Extract failed rubrics or notes from supporting assessment items
                failed_criteria = []
                for ev in skill_evs:
                    rub = ev.get("evaluation_rubric")
                    if isinstance(rub, dict) and rub.get("missed_concepts"):
                        failed_criteria.extend(rub.get("missed_concepts"))
                    elif isinstance(ev.get("metadata"), dict) and ev["metadata"].get("missed_concepts"):
                        failed_criteria.extend(ev["metadata"]["missed_concepts"])

                remedial_title = f"Mastery Assignment: {skill_meta.get('name', sid)}"
                remedial_action = (
                    f"Complete the targeted {skill_meta.get('name', sid)} practical assignment "
                    f"and submit code addressing {', '.join(failed_criteria[:2]) if failed_criteria else 'core invariants'}."
                )

                detected_weaknesses.append({
                    "skill_id": sid,
                    "skill_name": skill_meta.get("name", sid),
                    "parent_domain_id": skill_meta.get("parent_skill_id"),
                    "proficiency": prof,
                    "confidence": skill_eval["confidence"],
                    "severity": severity,
                    "evidence_count": skill_eval["evidence_count"],
                    "failed_criteria": list(set(failed_criteria))[:4],
                    "remedial_action": remedial_action,
                    "remedial_assignment": {
                        "title": remedial_title,
                        "skill_id": sid,
                        "activity_type": "PRACTICAL_ASSIGNMENT",
                        "estimated_minutes": 35
                    }
                })

        # Sort by severity (VERIFIED_GAP first) and lowest proficiency
        detected_weaknesses.sort(key=lambda w: (0 if w["severity"] == "VERIFIED_GAP" else 1, w["proficiency"]))
        return detected_weaknesses

