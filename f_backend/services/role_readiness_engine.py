"""
PREPFLY ROLE READINESS ENGINE
=============================
Computes job-specific role readiness relative to a target Job Description or canonical role.
Applies weighted importance:
  - Mandatory Skills: 1.5x
  - Preferred Skills: 1.0x
  - Supporting Skills: 0.7x
Labels readiness as PROVISIONAL whenever critical mandatory requirements lack verified assessments.
Generates full mathematical provenance and formula explanations.
"""

from typing import Dict, Any, List, Optional
from services.canonical_skill_taxonomy import CanonicalSkillTaxonomy
from services.evidence_scoring_engine import EvidenceScoringEngine
from local_supabase import get_supabase_client

# Role Skill Weight Multipliers
WEIGHT_MANDATORY = 1.5
WEIGHT_PREFERRED = 1.0
WEIGHT_SUPPORTING = 0.7

# Default canonical role profiles with tier classification
ROLE_SKILL_REQUIREMENTS: Dict[str, Dict[str, List[str]]] = {
    "ai_ml_engineer": {
        "mandatory": ["ml_model_development", "ml_model_evaluation", "dl_transformers", "sys_ml_system_design", "python_data_structures"],
        "preferred": ["dl_neural_networks", "genai_llm_fundamentals", "ml_tree_ensembles", "python_concurrency"],
        "supporting": ["dsa_arrays_strings", "cs_dbms_internals", "soft_tradeoff_articulation"]
    },
    "data_scientist": {
        "mandatory": ["ml_math_foundations", "ml_model_development", "ml_model_evaluation", "python_data_structures"],
        "preferred": ["ml_tree_ensembles", "dl_neural_networks", "cs_dbms_internals"],
        "supporting": ["dsa_arrays_strings", "soft_problem_decomposition"]
    },
    "software_development_engineer": {
        "mandatory": ["dsa_arrays_strings", "dsa_hashing", "dsa_trees_graphs", "sys_caching", "cs_os_concurrency"],
        "preferred": ["sys_scalability", "sys_rate_limiting", "dsa_dynamic_programming", "cs_dbms_internals"],
        "supporting": ["python_syntax_idioms", "soft_problem_decomposition", "soft_tradeoff_articulation"]
    },
    "backend_developer": {
        "mandatory": ["sys_caching", "sys_scalability", "cs_dbms_internals", "python_data_structures", "cs_os_concurrency"],
        "preferred": ["sys_rate_limiting", "python_concurrency", "dsa_hashing"],
        "supporting": ["dsa_arrays_strings", "soft_tradeoff_articulation"]
    },
    "frontend_developer": {
        "mandatory": ["fe_react_architecture", "fe_web_performance"],
        "preferred": ["dsa_arrays_strings", "dsa_hashing"],
        "supporting": ["soft_problem_decomposition", "soft_tradeoff_articulation"]
    }
}


class RoleReadinessEngine:
    """Computes transparent, evidence-calibrated readiness scores relative to a target role."""

    @classmethod
    def get_role_requirements(cls, target_role: str) -> Dict[str, List[str]]:
        """Maps target role string to mandatory, preferred, and supporting skill IDs."""
        r = (target_role or "").lower()
        if "ai" in r or "ml" in r or "machine learning" in r or "deep learning" in r:
            return ROLE_SKILL_REQUIREMENTS["ai_ml_engineer"]
        elif "data sci" in r:
            return ROLE_SKILL_REQUIREMENTS["data_scientist"]
        elif "back" in r:
            return ROLE_SKILL_REQUIREMENTS["backend_developer"]
        elif "front" in r or "ui" in r:
            return ROLE_SKILL_REQUIREMENTS["frontend_developer"]
        return ROLE_SKILL_REQUIREMENTS["software_development_engineer"]

    @classmethod
    def calculate_readiness(
        cls,
        user_id: str,
        target_role: str = "Software Development Engineer (General)",
        job_description: Optional[str] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Calculates role readiness relative to target JD / role:
        - Evaluates candidate on mandatory (1.5x), preferred (1.0x), and supporting (0.7x) skills
        - If any mandatory skill has ZERO assessed evidence, readiness is flagged as PROVISIONAL
        - Missing skills are NOT treated as 0% proficiency; unassessed gap is quantified in coverage
        - Outputs formula breakdown explanation
        """
        requirements = cls.get_role_requirements(target_role)
        mandatory_skills = requirements.get("mandatory", [])
        preferred_skills = requirements.get("preferred", [])
        supporting_skills = requirements.get("supporting", [])

        all_target_skills = [
            *( (s, "mandatory", WEIGHT_MANDATORY) for s in mandatory_skills ),
            *( (s, "preferred", WEIGHT_PREFERRED) for s in preferred_skills ),
            *( (s, "supporting", WEIGHT_SUPPORTING) for s in supporting_skills )
        ]

        evaluated_skills = []
        weighted_score_sum = 0.0
        total_assessed_weights = 0.0
        unassessed_mandatory = []
        unassessed_skills = []

        for skill_id, tier, weight in all_target_skills:
            eval_res = EvidenceScoringEngine.evaluate_skill(
                user_id=user_id,
                skill_id=skill_id,
                supabase_client=supabase_client
            )
            item = {
                **eval_res,
                "tier": tier,
                "weight": weight
            }
            evaluated_skills.append(item)

            if eval_res["is_assessed"]:
                weighted_score_sum += eval_res["proficiency"] * weight
                total_assessed_weights += weight
            else:
                unassessed_skills.append(skill_id)
                if tier == "mandatory":
                    unassessed_mandatory.append({
                        "skill_id": skill_id,
                        "skill_name": eval_res["skill_name"]
                    })

        total_target_count = len(all_target_skills)
        assessed_target_count = total_target_count - len(unassessed_skills)
        coverage_ratio = round(assessed_target_count / max(1, total_target_count), 2)

        if total_assessed_weights > 0:
            measured_proficiency = round(weighted_score_sum / total_assessed_weights, 1)
        else:
            measured_proficiency = None

        # Readiness status & final score calibration
        if measured_proficiency is None:
            overall_score = 0.0
            readiness_status = "PROVISIONAL"
            status_explanation = (
                "Readiness is PROVISIONAL because you have not completed verified technical assessments "
                "for this role. Complete a diagnostic assessment or coding challenge to calibrate your baseline."
            )
        elif len(unassessed_mandatory) > 0:
            # Calibrate provisional score considering unassessed mandatory coverage
            overall_score = round(measured_proficiency * (0.6 + 0.4 * coverage_ratio), 1)
            readiness_status = "PROVISIONAL"
            mandatory_names = ", ".join(m["skill_name"] for m in unassessed_mandatory[:3])
            status_explanation = (
                f"Readiness is PROVISIONAL because {len(unassessed_mandatory)} critical mandatory skill(s) "
                f"({mandatory_names}) have not been assessed through verified testing or coding."
            )
        else:
            overall_score = measured_proficiency
            readiness_status = "ESTABLISHED"
            status_explanation = (
                f"Readiness is ESTABLISHED across all {len(mandatory_skills)} core mandatory requirements "
                f"with {round(coverage_ratio * 100)}% overall evidence coverage."
            )

        # Formula string explanation
        formula_breakdown = (
            f"Readiness Score ({overall_score}%) = [Sum(Assessed Proficiency * Tier Weight) / Total Assessed Weights] "
            f"* Coverage Penalty if Mandatory Unassessed. "
            f"Evaluated {assessed_target_count}/{total_target_count} role requirements "
            f"(Mandatory: {len(mandatory_skills) - len(unassessed_mandatory)}/{len(mandatory_skills)} assessed)."
        )

        return {
            "target_role": target_role,
            "overall_score": overall_score,
            "measured_proficiency": measured_proficiency,
            "readiness_status": readiness_status,
            "status_explanation": status_explanation,
            "formula_breakdown": formula_breakdown,
            "coverage_ratio": coverage_ratio,
            "assessed_skills_count": assessed_target_count,
            "total_required_skills_count": total_target_count,
            "unassessed_mandatory_skills": unassessed_mandatory,
            "skills_matrix": evaluated_skills
        }

