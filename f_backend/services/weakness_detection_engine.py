"""
PREPFLY WEAKNESS DETECTION ENGINE
=================================
Strictly identifies candidate weaknesses and skill gaps.
Guiding Law:
- Unassessed skills, resume mentions, or project claims are NEVER labeled as weaknesses.
- Weakness requires verified, provenance-backed assessment failure (< 60%).
- Categorizes severity into VERIFIED_GAP (< 45%) and DEVELOPING (45-59%).
- Attaches actionable remedial assignments, rubric failure criteria, and prerequisite root causes.
"""

from typing import Dict, Any, List, Optional
import json
from services.canonical_skill_taxonomy import CanonicalSkillTaxonomy
from services.skill_taxonomy_service import SkillTaxonomyService
from services.evidence_registry_service import EvidenceRegistryService, STATUS_ASSESSED
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
        
        # 1. Fetch registry evidence (Migration 006)
        all_evidence = EvidenceRegistryService.get_evidence_for_candidate(
            user_id=user_id,
            supabase_client=supabase
        )

        # 2. Also fetch skill_evidence ledger (Migration 001/008)
        try:
            se_res = supabase.table("skill_evidence").select("*").eq("user_id", user_id).execute()
            if se_res and se_res.data:
                for row in se_res.data:
                    # Map to evidence structure
                    all_evidence.append({
                        "id": row.get("id"),
                        "user_id": row.get("user_id"),
                        "skill_id": row.get("skill_id"),
                        "source_type": row.get("source_type"),
                        "source_id": row.get("source_id"),
                        "raw_score": row.get("raw_score") or row.get("score"),
                        "normalized_score": row.get("weighted_score") or row.get("score"),
                        "difficulty": "Intermediate",
                        "evidence_quality": row.get("confidence", 0.9),
                        "validity_status": STATUS_ASSESSED,
                        "evaluator_type": "adaptive_diagnostic",
                        "provenance_hash": f"prov_{row.get('id')}",
                        "metadata": {
                            "demonstrated_concepts": row.get("demonstrated_concepts") or [],
                            "missed_concepts": row.get("missed_concepts") or []
                        }
                    })
        except Exception:
            pass

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
                skill_meta = CanonicalSkillTaxonomy.get_skill(sid) or SkillTaxonomyService.get_skill(sid) or {}

                # Extract failed rubrics or notes from supporting assessment items
                failed_criteria = []
                for ev in skill_evs:
                    rub = ev.get("evaluation_rubric")
                    if isinstance(rub, dict) and rub.get("missed_concepts"):
                        failed_criteria.extend(rub.get("missed_concepts"))
                    elif isinstance(ev.get("metadata"), dict) and ev["metadata"].get("missed_concepts"):
                        raw_missed = ev["metadata"]["missed_concepts"]
                        if isinstance(raw_missed, str):
                            try:
                                raw_missed = json.loads(raw_missed)
                            except Exception:
                                raw_missed = [raw_missed]
                        if isinstance(raw_missed, list):
                            failed_criteria.extend(raw_missed)

                # Check DAG prerequisites for root-cause gaps
                prereqs = SkillTaxonomyService.get_prerequisites(sid)
                prereq_gaps = []
                for p in prereqs:
                    p_evs = [e for e in all_evidence if e.get("skill_id") == p]
                    if not p_evs:
                        prereq_gaps.append({"skill_id": p, "status": "UNASSESSED"})
                    else:
                        p_eval = EvidenceScoringEngine.evaluate_skill(user_id=user_id, skill_id=p, evidence_list=p_evs, supabase_client=supabase)
                        if p_eval["is_assessed"] and (p_eval["proficiency"] or 0) < 60.0:
                            prereq_gaps.append({"skill_id": p, "status": "WEAK", "proficiency": p_eval["proficiency"]})

                remedial_title = f"Mastery Assignment: {skill_meta.get('name', sid)}"
                remedial_action = (
                    f"Complete the targeted {skill_meta.get('name', sid)} practical assignment "
                    f"and submit code addressing {', '.join(failed_criteria[:2]) if failed_criteria else 'core invariants'}."
                )

                detected_weaknesses.append({
                    "skill_id": sid,
                    "skill_name": skill_meta.get("name", sid),
                    "parent_domain_id": skill_meta.get("parent_skill_id") or skill_meta.get("category"),
                    "proficiency": prof,
                    "confidence": skill_eval["confidence"],
                    "severity": severity,
                    "evidence_count": skill_eval["evidence_count"],
                    "failed_criteria": list(dict.fromkeys(failed_criteria))[:4],
                    "prerequisite_gaps": prereq_gaps,
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

    @classmethod
    def detect_weaknesses_and_uncertainties(
        cls,
        user_id: str,
        target_role: Optional[str] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Returns both verified failure weaknesses AND unassessed role uncertainties.
        Prevents conflating lack of testing with actual candidate weakness.
        """
        weaknesses = cls.detect_weaknesses(user_id=user_id, target_role=target_role, supabase_client=supabase_client)
        assessed_sids = {w["skill_id"] for w in weaknesses}

        role_name = target_role or "software_development_engineer"
        role_reqs = SkillTaxonomyService.get_role_requirements(role_name)

        uncertainties = []
        for req in role_reqs:
            sid = req["skill_id"]
            if sid not in assessed_sids:
                meta = SkillTaxonomyService.get_skill(sid) or {}
                uncertainties.append({
                    "skill_id": sid,
                    "skill_name": meta.get("name", sid),
                    "category": meta.get("category", "General"),
                    "importance_weight": req.get("importance_weight", 0.7),
                    "status": "UNASSESSED_UNCERTAINTY",
                    "action": f"Schedule targeted diagnostic drill for {meta.get('name', sid)}."
                })

        return {
            "verified_weaknesses": weaknesses,
            "unassessed_uncertainties": uncertainties,
            "weakness_count": len(weaknesses),
            "uncertainty_count": len(uncertainties)
        }
