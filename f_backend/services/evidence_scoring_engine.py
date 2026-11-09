"""
PREPFLY EVIDENCE SCORING ENGINE
===============================
Calculates evidence-based skill proficiency, confidence, coverage, recency, and difficulty.
Strictly separates assessed demonstrated proficiency from unverified claimed signals.
Missing evidence is never treated as zero proficiency (returns None).
Aggregates leaf subskills into top-level parent domains with coverage gating.
"""

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from services.canonical_skill_taxonomy import CanonicalSkillTaxonomy, PARENT_DOMAINS
from services.evidence_registry_service import (
    EvidenceRegistryService,
    SOURCE_DIAGNOSTIC_ASSESSMENT,
    SOURCE_PRACTICAL_ASSIGNMENT,
    SOURCE_CODING_SUBMISSION,
    SOURCE_AI_INTERVIEW,
    SOURCE_MOCK_INTERVIEW,
    STATUS_CLAIMED_EXPOSURE,
    STATUS_PROJECT_EXPOSURE,
    STATUS_ASSESSED,
    STATUS_VERIFIED_CODE,
    STATUS_VERIFIED_EXPERIENCE
)

# Standardized evidence source category weights for demonstrated proficiency
SOURCE_WEIGHTS = {
    SOURCE_PRACTICAL_ASSIGNMENT: 0.35,
    SOURCE_DIAGNOSTIC_ASSESSMENT: 0.25,
    "adaptive_diagnostic": 0.25,
    SOURCE_CODING_SUBMISSION: 0.25,
    SOURCE_AI_INTERVIEW: 0.15,
    SOURCE_MOCK_INTERVIEW: 0.15
}

# 90-day half-life for evidence recency decay
RECENCY_HALF_LIFE_DAYS = 90.0


class EvidenceScoringEngine:
    """Calculates multidimensional proficiency profiles from verified evidence."""

    @classmethod
    def calculate_recency_factor(cls, created_at_iso: str) -> Dict[str, Any]:
        """Calculates exponential recency decay and status based on age in days."""
        try:
            created_dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
            age_days = max(0.0, (datetime.now(timezone.utc) - created_dt).total_seconds() / 86400.0)
        except Exception:
            age_days = 0.0

        # Half-life exponential decay: decay = 0.5^(age_days / 90)
        decay = math.pow(0.5, age_days / RECENCY_HALF_LIFE_DAYS)

        if age_days <= 60:
            status = "CURRENT"
        elif age_days <= 120:
            status = "AGING"
        else:
            status = "STALE_REASSESSMENT_DUE"

        return {
            "age_days": round(age_days, 1),
            "decay_factor": round(decay, 3),
            "status": status
        }

    @classmethod
    def evaluate_skill(
        cls,
        user_id: str,
        skill_id: str,
        evidence_list: Optional[List[Dict[str, Any]]] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Computes the 5 decoupled dimensions for a single skill:
        - proficiency: Assessed score (0-100) or None if unassessed
        - confidence: 0.0 to 1.0 based on evidence count, source variety & recency
        - coverage: Subskill coverage ratio
        - recency: Most recent assessment status
        - difficulty_quality: Average task difficulty level
        """
        if evidence_list is None:
            evidence_list = EvidenceRegistryService.get_evidence_for_candidate(
                user_id=user_id,
                skill_id=skill_id,
                supabase_client=supabase_client
            )

        # 1. Filter assessed evidence vs discovery exposure signals
        assessed_evidence = [
            e for e in evidence_list
            if e.get("validity_status") in (STATUS_ASSESSED, STATUS_VERIFIED_CODE, STATUS_VERIFIED_EXPERIENCE, "VALID")
            and e.get("normalized_score") is not None
        ]

        claimed_signals = [
            e for e in evidence_list
            if e.get("validity_status") in (STATUS_CLAIMED_EXPOSURE, STATUS_PROJECT_EXPOSURE)
        ]

        # 2. Compute Proficiency (Assessed sources only)
        if not assessed_evidence:
            proficiency = None
            evidence_status = "NOT_ASSESSED" if not claimed_signals else (
                "PROJECT_EXPOSURE" if any(c.get("validity_status") == STATUS_PROJECT_EXPOSURE for c in claimed_signals)
                else "CLAIMED_EXPOSURE"
            )
            confidence = 0.0
            recency_info = {"status": "NO_EVIDENCE", "age_days": None, "decay_factor": 1.0}
            avg_difficulty = "None"
        else:
            # Group by source type to prevent single source dominance
            by_source: Dict[str, List[Dict[str, Any]]] = {}
            for ev in assessed_evidence:
                st = ev.get("source_type", SOURCE_DIAGNOSTIC_ASSESSMENT)
                if st not in by_source:
                    by_source[st] = []
                by_source[st].append(ev)

            # Compute weighted source scores
            total_weight = 0.0
            weighted_sum = 0.0

            for st, items in by_source.items():
                w = SOURCE_WEIGHTS.get(st, 0.20)
                # Recent score with difficulty multiplier
                source_scores = []
                for item in items:
                    raw_s = float(item.get("normalized_score", 0.0))
                    diff = str(item.get("difficulty") or "Intermediate").lower()
                    diff_mult = 0.85 if "beg" in diff else (1.15 if "adv" in diff else 1.0)
                    rec = cls.calculate_recency_factor(item.get("created_at") or datetime.now(timezone.utc).isoformat())
                    # Weight score by difficulty and recency decay
                    adjusted_score = min(100.0, raw_s * diff_mult)
                    source_scores.append(adjusted_score)

                # Average across items within this source
                avg_source_score = sum(source_scores) / len(source_scores)
                weighted_sum += avg_source_score * w
                total_weight += w

            # Normalize remaining weights
            proficiency = round(weighted_sum / max(0.01, total_weight), 1) if total_weight > 0 else 0.0

            # 3. Compute Confidence (saturation curve)
            # Factors: count of evaluations (saturation at 4), source variety (up to 3 types), recency
            n_evals = len(assessed_evidence)
            count_factor = 1.0 - math.exp(-0.6 * n_evals)  # 1->0.45, 2->0.70, 3->0.83, 4->0.91
            variety_factor = min(1.0, len(by_source) / 2.5)  # Multi-source boost

            most_recent_ev = max(assessed_evidence, key=lambda x: x.get("created_at") or "")
            recency_info = cls.calculate_recency_factor(most_recent_ev.get("created_at") or "")
            decay = recency_info.get("decay_factor", 1.0)

            confidence = round(min(1.0, count_factor * (0.7 + 0.3 * variety_factor) * decay), 2)
            evidence_status = "VERIFIED_ASSESSED"

            # Determine aggregate difficulty
            adv_count = sum(1 for e in assessed_evidence if "adv" in str(e.get("difficulty", "")).lower())
            beg_count = sum(1 for e in assessed_evidence if "beg" in str(e.get("difficulty", "")).lower())
            avg_difficulty = "Advanced" if adv_count > len(assessed_evidence) / 2 else ("Beginner" if beg_count > len(assessed_evidence) / 2 else "Intermediate")

        skill_meta = CanonicalSkillTaxonomy.get_skill(skill_id) or {}

        return {
            "skill_id": skill_id,
            "skill_name": skill_meta.get("name", skill_id),
            "parent_domain_id": skill_meta.get("parent_skill_id"),
            "proficiency": proficiency,
            "confidence": confidence,
            "evidence_status": evidence_status,
            "evidence_count": len(assessed_evidence),
            "claimed_count": len(claimed_signals),
            "recency": recency_info.get("status"),
            "recency_age_days": recency_info.get("age_days"),
            "difficulty": avg_difficulty,
            "is_assessed": proficiency is not None
        }

    @classmethod
    def evaluate_parent_domain(
        cls,
        user_id: str,
        domain_id: str,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Subskill Aggregation: derives parent domain proficiency, confidence, and coverage
        from its constituent leaf subskills.
        If < 50% of domain subskills have assessed evidence, marked PARTIALLY_ASSESSED.
        """
        domain_meta = PARENT_DOMAINS.get(domain_id) or {}
        subskills = CanonicalSkillTaxonomy.get_subskills_for_domain(domain_id)
        if not subskills:
            return {
                "domain_id": domain_id,
                "domain_name": domain_meta.get("name", domain_id),
                "proficiency": None,
                "confidence": 0.0,
                "coverage": 0.0,
                "status": "NO_SUBSKILLS",
                "subskills": []
            }

        # Fetch candidate evidence for all subskills
        all_user_evidence = EvidenceRegistryService.get_evidence_for_candidate(
            user_id=user_id,
            supabase_client=supabase_client
        )
        evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for ev in all_user_evidence:
            sid = ev.get("skill_id")
            if sid:
                if sid not in evidence_by_skill:
                    evidence_by_skill[sid] = []
                evidence_by_skill[sid].append(ev)

        subskill_evals = []
        assessed_proficiencies = []
        confidences = []

        for s in subskills:
            sid = s["skill_id"]
            ev_list = evidence_by_skill.get(sid, [])
            eval_res = cls.evaluate_skill(
                user_id=user_id,
                skill_id=sid,
                evidence_list=ev_list,
                supabase_client=supabase_client
            )
            subskill_evals.append(eval_res)
            if eval_res["proficiency"] is not None:
                assessed_proficiencies.append(eval_res["proficiency"])
                confidences.append(eval_res["confidence"])

        total_subskills = len(subskills)
        assessed_count = len(assessed_proficiencies)
        coverage_ratio = round(assessed_count / max(1, total_subskills), 2)

        if assessed_count == 0:
            domain_proficiency = None
            domain_confidence = 0.0
            domain_status = "NOT_ASSESSED"
        else:
            domain_proficiency = round(sum(assessed_proficiencies) / assessed_count, 1)
            domain_confidence = round(sum(confidences) / assessed_count * (0.6 + 0.4 * coverage_ratio), 2)
            if coverage_ratio >= 0.50:
                domain_status = "ESTABLISHED"
            else:
                domain_status = "PARTIALLY_ASSESSED"

        return {
            "domain_id": domain_id,
            "domain_name": domain_meta.get("name", domain_id),
            "category": domain_meta.get("category", ""),
            "proficiency": domain_proficiency,
            "confidence": domain_confidence,
            "coverage": coverage_ratio,
            "assessed_count": assessed_count,
            "total_subskills": total_subskills,
            "status": domain_status,
            "subskills": subskill_evals
        }

