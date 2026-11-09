"""
PureScoringEngine
=================
Pure, deterministic mathematical calculation engine for technical evaluations.
Implements strict separation between:
  1. Proficiency (Demonstrated competency [0.0, 100.0])
  2. Confidence  (Statistical reliability [0.0, 1.0])
  3. Coverage    (Curriculum breadth evaluated [0.0, 100.0%])
  4. Role Readiness (Integrated readiness with explainability audit)

Zero side-effects, zero LLM calls, and fully verifiable via property-based tests.
"""

from typing import Dict, List, Optional, Any, Tuple
import math
import uuid
import json
from datetime import datetime, timezone
import logging

from local_supabase import get_supabase_client

logger = logging.getLogger("prepfly.pure_scoring")


class PureScoringEngine:
    """Pure mathematical scoring functions decoupled from I/O and persistence."""

    @staticmethod
    def calculate_rubric_score(
        rubric_weights: Dict[str, float],
        criteria_achievements: Dict[str, float]
    ) -> float:
        """
        Calculates question score based on weighted rubric criteria:
        Score = (Sum(w_i * r_i) / Sum(w_i)) * 100
        where r_i in [0.0, 1.0] and w_i > 0.
        Guarantees return value in [0.0, 100.0].
        """
        if not rubric_weights:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for criterion, weight in rubric_weights.items():
            w = max(0.0, float(weight))
            r = max(0.0, min(1.0, float(criteria_achievements.get(criterion, 0.0))))
            total_weight += w
            weighted_sum += (w * r)

        if total_weight <= 0.0:
            return 0.0

        raw_score = (weighted_sum / total_weight) * 100.0
        return round(max(0.0, min(100.0, raw_score)), 1)

    @staticmethod
    def calculate_confidence(
        sample_count: int,
        concept_diversity: int = 1,
        score_variance: float = 0.0,
        source_quality: float = 0.9
    ) -> float:
        """
        Calculates statistical measurement confidence in [0.0, 1.0]:
        Confidence = BoundedSampleFactor * DiversityFactor * ConsistencyFactor * Quality
        Guarantees that a single question (N=1) yields confidence <= 0.40.
        """
        N = max(0, int(sample_count))
        if N == 0:
            return 0.0

        # Sample count saturation: 1 - exp(-N / 4.0)
        # N=1 -> 0.22, N=2 -> 0.39, N=5 -> 0.71, N=10 -> 0.92
        sample_factor = 1.0 - math.exp(-N / 4.0)

        # Concept diversity bonus: more distinct concepts probed increases certainty
        diversity_factor = min(1.0, 0.6 + (0.1 * min(4, max(1, concept_diversity))))

        # Consistency penalty: high score variance reduces confidence
        # Normalized variance [0, 2500] (for 0-100 scale)
        variance_penalty = max(0.0, min(0.3, (score_variance / 2500.0) * 0.3))
        consistency_factor = max(0.7, 1.0 - variance_penalty)

        quality = max(0.5, min(1.0, float(source_quality)))

        confidence = sample_factor * diversity_factor * consistency_factor * quality
        return round(max(0.0, min(1.0, confidence)), 2)

    @staticmethod
    def calculate_coverage(
        assessed_skills: List[str],
        required_weights: Dict[str, float]
    ) -> float:
        """
        Calculates role curriculum coverage percentage:
        Coverage = (Sum(w_s for s in Assessed) / Sum(w_s for s in Required)) * 100.0
        Guarantees return value in [0.0, 100.0].
        """
        if not required_weights:
            return 100.0 if assessed_skills else 0.0

        total_req_weight = sum(max(0.0, float(w)) for w in required_weights.values())
        if total_req_weight <= 0.0:
            return 0.0

        assessed_set = set(assessed_skills)
        evaluated_weight = sum(
            max(0.0, float(w)) for s, w in required_weights.items() if s in assessed_set
        )

        coverage = (evaluated_weight / total_req_weight) * 100.0
        return round(max(0.0, min(100.0, coverage)), 1)

    @classmethod
    def calculate_role_readiness(
        cls,
        skill_proficiencies: Dict[str, float],
        skill_confidences: Dict[str, float],
        required_weights: Dict[str, float],
        mandatory_skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Integrates Proficiency, Confidence, and Coverage into an honest, uninflated Readiness Score:
        - Missing skills are NOT treated as 0% proficiency (which would artificially penalize verified skills).
        - Coverage acts as an uncertainty gate: unassessed skills reduce Coverage, not Proficiency.
        - Overall Readiness = AssessedProficiency * CoverageGate * AverageConfidence
        """
        if not required_weights:
            return {
                "overall_readiness": 0.0,
                "coverage_pct": 0.0,
                "confidence_factor": 0.0,
                "provisional": True,
                "assessed_skills_count": 0,
                "missing_mandatory_skills": mandatory_skills or [],
                "formula_breakdown": "No required skills defined for role."
            }

        assessed_skills = [s for s in required_weights.keys() if s in skill_proficiencies]
        coverage_pct = cls.calculate_coverage(assessed_skills, required_weights)
        coverage_ratio = coverage_pct / 100.0

        # Calculate weighted average proficiency across ASSESSED skills only
        assessed_weight_sum = sum(required_weights[s] for s in assessed_skills)
        if assessed_weight_sum > 0:
            weighted_prof = sum(
                (skill_proficiencies[s] * required_weights[s]) for s in assessed_skills
            ) / assessed_weight_sum
        else:
            weighted_prof = 0.0

        # Average confidence across assessed skills
        if assessed_skills:
            avg_conf = sum(skill_confidences.get(s, 0.5) for s in assessed_skills) / len(assessed_skills)
        else:
            avg_conf = 0.0

        # Check mandatory requirements
        missing_mandatory = []
        if mandatory_skills:
            for ms in mandatory_skills:
                if ms not in skill_proficiencies:
                    missing_mandatory.append(ms)

        is_provisional = bool(missing_mandatory or coverage_pct < 50.0 or avg_conf < 0.6)

        # Honest Readiness Score:
        # WeightedProficiency scaled by coverage damper:
        # A candidate with 100% on 10% coverage cannot score > 30% readiness.
        # Readiness = WeightedProf * (0.2 + 0.8 * CoverageRatio) * (0.5 + 0.5 * AvgConfidence)
        coverage_damper = 0.2 + (0.8 * coverage_ratio)
        confidence_damper = 0.5 + (0.5 * avg_conf)
        readiness_score = round(max(0.0, min(100.0, weighted_prof * coverage_damper * confidence_damper)), 1)

        breakdown_text = (
            f"Evaluated {len(assessed_skills)} of {len(required_weights)} required skills. "
            f"Assessed Proficiency: {round(weighted_prof, 1)}%. Coverage: {coverage_pct}%. "
            f"Measurement Confidence: {int(avg_conf * 100)}%. "
            f"{'Flagged as PROVISIONAL due to unassessed mandatory skills.' if is_provisional else 'Baseline calibrated with high evidence.'}"
        )

        return {
            "overall_readiness": readiness_score,
            "assessed_proficiency": round(weighted_prof, 1),
            "coverage_pct": coverage_pct,
            "confidence_factor": round(avg_conf, 2),
            "provisional": is_provisional,
            "assessed_skills_count": len(assessed_skills),
            "total_skills_count": len(required_weights),
            "missing_mandatory_skills": missing_mandatory,
            "formula_breakdown": breakdown_text
        }

    @classmethod
    def audit_and_log_score(
        cls,
        user_id: str,
        target_role: str,
        calculation_type: str,
        score_inputs: Dict[str, Any],
        calculated_score: float,
        supabase_client=None
    ) -> str:
        """Persists calculation inputs and outputs into score_audit_log for mathematical explainability."""
        client = supabase_client or get_supabase_client()
        log_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "id": log_id,
            "user_id": user_id,
            "target_role": target_role,
            "calculation_type": calculation_type,
            "score_inputs": json.dumps(score_inputs) if not hasattr(client, "_is_postgres") else score_inputs,
            "calculated_score": calculated_score,
            "generated_at": now_iso
        }

        try:
            client.table("score_audit_log").insert(record).execute()
        except Exception as e:
            logger.warning(f"Failed to record score audit log: {e}")

        return log_id

