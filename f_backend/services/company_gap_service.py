"""
PrepFly Company-Candidate Gap Analysis Service (Part 5)
Compares Company Interview Expectations against Candidate Demonstrated Readiness.
Computes deterministic multi-factor gap scores, 6-tier competency classifications,
prerequisite validation, and prioritized preparation recommendations.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
import math
import logging

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG, ROLE_REQUIREMENTS
from services.company_intelligence_service import (
    CompanyIntelligenceService,
    SRC_REPORTED,
    SRC_OFFICIAL,
    SRC_ADAPTED,
    SRC_AI_PRACTICE,
    SRC_ROLE_BASE
)
from services.candidate_readiness_service import CandidateReadinessService

logger = logging.getLogger("prepfly.gap_analysis")

# 6-Tier Competency Classifications
TIER_STRONG_DEMONSTRATED = "STRONG_AND_DEMONSTRATED"
TIER_STRONG_REVISION = "STRONG_NEEDS_REVISION"
TIER_DEVELOPING = "DEVELOPING"
TIER_HIGH_PRIORITY_WEAKNESS = "HIGH_PRIORITY_WEAKNESS"
TIER_NOT_ASSESSED = "NOT_ASSESSED"
TIER_INSUFFICIENT_DATA = "INSUFFICIENT_COMPANY_EVIDENCE"


class CompanyCandidateGapService:
    """
    Core matching and gap analysis engine joining Dimension A (Candidate Readiness)
    with Dimension B (Company Interview Intelligence).
    """

    @classmethod
    def analyze_company_candidate_gaps(
        cls,
        user_id: str,
        company_name: str,
        role: str = "Software Engineer",
        experience_level: str = "Fresher",
        days_to_deadline: int = 30,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Executes comprehensive two-dimensional gap analysis and generates prioritized
        competency allocations.
        """
        clean_company = (company_name or "Tech Standard").strip()
        clean_role = (role or "Software Engineer").strip()

        # 1. Dimension B: Retrieve Company Interview Intelligence
        company_profile = CompanyIntelligenceService.get_company_intelligence(
            company_name=clean_company,
            role=clean_role,
            experience_level=experience_level
        )

        # 2. Dimension A: Retrieve Candidate Demonstrated Readiness Snapshot
        candidate_snapshot = CandidateReadinessService.get_candidate_readiness_snapshot(
            user_id=user_id,
            target_role=clean_role,
            supabase_client=supabase_client
        )

        # 3. Extract frequent company skills and role requirements
        company_frequent_skills = set(company_profile.get("level_expectations", {}).get("frequent_skills", []))
        normalized_role_reqs = ROLE_REQUIREMENTS.get(company_profile.get("normalized_role", "Software Engineer"), {})

        # Build Candidate Proficiency Map
        skill_dict = {
            s["skill_id"]: s for s in candidate_snapshot.get("skills", {}).get("demonstrated_strengths", [])
        }
        for s in candidate_snapshot.get("skills", {}).get("confirmed_weaknesses", []):
            skill_dict[s["skill_id"]] = s

        gap_items: List[Dict[str, Any]] = []

        # Analyze every relevant canonical skill
        for skill_id, skill_meta in SKILL_CATALOG.items():
            role_weight = normalized_role_reqs.get(skill_id, 0.3)
            is_company_frequent = (skill_id in company_frequent_skills)
            
            # Company relevance score: 0.95 for direct frequent skill, 0.70 for role req, 0.30 baseline
            if is_company_frequent:
                company_relevance = 0.95
            elif role_weight >= 0.7:
                company_relevance = 0.80
            elif role_weight >= 0.4:
                company_relevance = 0.60
            else:
                company_relevance = 0.30

            candidate_record = skill_dict.get(skill_id)
            if candidate_record:
                proficiency = float(candidate_record.get("proficiency", 0.0))
                evidence_count = int(candidate_record.get("evidence_count", 1))
                confidence = candidate_record.get("confidence", "LOW")
                is_assessed = True
            else:
                proficiency = 0.0
                evidence_count = 0
                confidence = "NOT_ASSESSED"
                is_assessed = False

            # Calculate Preparation Gap (0 to 100)
            if is_assessed:
                prep_gap = max(0.0, 100.0 - proficiency)
            else:
                # For unassessed skills, gap is calibrated to 65.0 baseline (NOT assumed 100% failure!)
                prep_gap = 65.0

            # 6-Tier Classification
            if not company_profile.get("matched_catalog") and not is_company_frequent and role_weight < 0.4:
                tier_class = TIER_INSUFFICIENT_DATA
            elif not is_assessed:
                tier_class = TIER_NOT_ASSESSED
            elif proficiency >= 75.0:
                tier_class = TIER_STRONG_DEMONSTRATED
            elif proficiency >= 60.0:
                tier_class = TIER_STRONG_REVISION if days_to_deadline <= 14 else TIER_DEVELOPING
            elif proficiency < 50.0 and company_relevance >= 0.70:
                tier_class = TIER_HIGH_PRIORITY_WEAKNESS
            else:
                tier_class = TIER_DEVELOPING

            # Deterministic Priority Score:
            # Priority = (0.35 * CompanyRelevance) + (0.30 * PrepGap/100) + (0.15 * Urgency) + (0.20 * RoleImportance)
            urgency_factor = 1.0 if days_to_deadline <= 7 else (0.85 if days_to_deadline <= 14 else 0.70)
            
            # Tier multiplier to emphasize confirmed company weaknesses
            tier_mult = 1.25 if tier_class == TIER_HIGH_PRIORITY_WEAKNESS else (
                1.10 if tier_class == TIER_DEVELOPING else (
                    0.90 if tier_class == TIER_NOT_ASSESSED else (
                        0.75 if tier_class == TIER_STRONG_REVISION else 0.50
                    )
                )
            )

            raw_score = (
                (0.35 * company_relevance) +
                (0.30 * (prep_gap / 100.0)) +
                (0.15 * urgency_factor) +
                (0.20 * role_weight)
            ) * tier_mult * 100.0

            final_priority = min(100.0, max(10.0, round(raw_score, 1)))

            # Recommended preparation minutes
            rec_minutes = int(min(180, max(30, round((prep_gap / 100.0) * company_relevance * 120.0))))

            gap_items.append({
                "skill_id": skill_id,
                "name": skill_meta.get("name", skill_id),
                "category": skill_meta.get("category", "General"),
                "company_relevance": round(company_relevance, 2),
                "role_importance": round(role_weight, 2),
                "is_company_frequent": is_company_frequent,
                "candidate_proficiency": round(proficiency, 1),
                "evidence_strength": round(min(1.0, evidence_count * 0.25), 2),
                "assessment_confidence": confidence,
                "preparation_gap": round(prep_gap, 1),
                "classification_tier": tier_class,
                "priority_score": final_priority,
                "recommended_minutes": rec_minutes,
                "prerequisites": skill_meta.get("prerequisites", [])
            })

        # Sort gaps by priority descending
        gap_items.sort(key=lambda x: x["priority_score"], reverse=True)

        # Filter top priorities
        high_priority_gaps = [g for g in gap_items if g["classification_tier"] == TIER_HIGH_PRIORITY_WEAKNESS]
        developing_gaps = [g for g in gap_items if g["classification_tier"] in (TIER_DEVELOPING, TIER_STRONG_REVISION)]
        unassessed_priorities = [g for g in gap_items if g["classification_tier"] == TIER_NOT_ASSESSED and g["company_relevance"] >= 0.70]

        # Generate Company-Specific Grounded Question Bank
        question_bank = cls._generate_company_question_bank(
            company_profile=company_profile,
            top_gaps=gap_items[:6],
            experience_level=experience_level
        )

        return {
            "company_name": company_profile["company_name"],
            "role": clean_role,
            "experience_level": experience_level,
            "days_to_deadline": days_to_deadline,
            "company_confidence": company_profile["confidence_score"],
            "candidate_coverage_pct": candidate_snapshot["assessment_coverage_pct"],
            "total_skills_evaluated": len(gap_items),
            "priority_summary": {
                "high_priority_weakness_count": len(high_priority_gaps),
                "developing_count": len(developing_gaps),
                "unassessed_company_skills_count": len(unassessed_priorities),
                "top_focus_skill_names": [g["name"] for g in gap_items[:5]]
            },
            "gaps": gap_items,
            "tailored_question_bank": question_bank,
            "company_round_breakdown": company_profile.get("round_structure", []),
            "behavioral_focus": company_profile.get("behavioral_principles", [])
        }

    @classmethod
    def _generate_company_question_bank(
        cls,
        company_profile: Dict[str, Any],
        top_gaps: List[Dict[str, Any]],
        experience_level: str
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes a grounded company-specific question bank classified by source type:
        1. Actual Reported Interview Questions
        2. Adapted Question Patterns
        3. AI Practice Variants
        """
        c_name = company_profile.get("company_name", "Target Company")
        questions = []

        # 1. Include verified reported questions from sources
        for s in company_profile.get("verified_sources", [])[:2]:
            for topic in s.get("reported_topics", [])[:2]:
                questions.append({
                    "question_id": f"q_rep_{len(questions)+1}",
                    "question_text": f"In a recent {c_name} {s.get('role')} interview: Solve the problem variant focusing on {topic}. Explain your approach, data structure invariants, and prove worst-case complexity.",
                    "company": c_name,
                    "interview_round": "Technical Coding Round",
                    "canonical_skill": "dsa_graphs_bfs_dfs" if "graph" in topic.lower() else "dsa_trees_traversals",
                    "difficulty": "Medium-to-Hard" if "senior" in experience_level.lower() else "Medium",
                    "source_classification": SRC_REPORTED,
                    "source_reference": s.get("url"),
                    "source_excerpt": s.get("excerpt"),
                    "rubric": {
                        "accuracy_weight": 0.50,
                        "complexity_analysis_weight": 0.30,
                        "code_clarity_weight": 0.20
                    },
                    "suggested_answer_framework": "1. Clarify constraints & null/empty bounds\n2. Propose optimal state machine / traversal\n3. Write modular code\n4. Dry run with edge cases\n5. State Big-O time and space."
                })

        # 2. Include Adapted Pattern Questions for Top Candidate Gaps
        for gap in top_gaps[:3]:
            questions.append({
                "question_id": f"q_adapt_{len(questions)+1}",
                "question_text": f"Design and implement a high-throughput solution demonstrating '{gap['name']}' under real-world {c_name} scale constraints.",
                "company": c_name,
                "interview_round": "Data Structures & Systems",
                "canonical_skill": gap["skill_id"],
                "difficulty": "Medium",
                "source_classification": SRC_ADAPTED,
                "source_reference": f"{c_name} Recurring Interview Curriculum ({company_profile.get('research_period')})",
                "rubric": {
                    "correctness": "Handles duplicates and boundary bounds",
                    "scalability": "Minimizes memory allocations and lock contention"
                },
                "suggested_answer_framework": "Explain space-time trade-off compared to naive brute force."
            })

        # 3. Include Company Behavioral Question
        principles = company_profile.get("behavioral_principles", [])
        principle_sample = principles[0] if principles else "Collaborative problem solving under tight deadlines"
        questions.append({
            "question_id": f"q_beh_{len(questions)+1}",
            "question_text": f"Tell me about a time you had to balance technical perfection with business delivery speed. How did you decide what trade-offs to accept, and how do you reflect the value of '{principle_sample.split(':')[0]}'?",
            "company": c_name,
            "interview_round": "Behavioral / Values Round",
            "canonical_skill": "soft_behavioral_star",
            "difficulty": "Standard",
            "source_classification": SRC_OFFICIAL if company_profile.get("matched_catalog") else SRC_ROLE_BASE,
            "source_reference": f"{c_name} Evaluated Values & Leadership Rubric",
            "rubric": {
                "situation_task_clarity": 0.25,
                "action_specificity": 0.40,
                "quantified_result": 0.35
            },
            "suggested_answer_framework": "Use the STAR method: Situation (context), Task (goal), Action (what YOU did with specifics), Result (measurable metric outcome)."
        })

        return questions
