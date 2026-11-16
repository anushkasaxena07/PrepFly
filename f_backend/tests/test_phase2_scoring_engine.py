"""
PREPFLY PHASE 2 TEST SUITE: SCORING ENGINE & READINESS
======================================================
Validates all Section 5 & Section 6 deliverables:
- Golden Rules: Code computes numbers; One source of truth; No fake mastery; Unassessed != gap.
- Acceptance Test 6: One MEDIUM short-answer at 60% -> P=60, C≈0.23+diversity, status LOW_EVIDENCE (not a gap).
- Acceptance Test 7: Evidence 180 days old has recency weight 0.25 (90-day half-life).
- Acceptance Test 8: Readiness with 0 assessed skills = null with "No evidence yet", not 0%.
- Acceptance Test 9: Skills assessed 3/12 with all mandatory unassessed -> PROVISIONAL badge present.
- Consistency Tests 1-5: Invariants on unassessed skills, mastered skills, and formula breakdown.
- Trend linear regression, slope thresholding, and < 3 days data guard.
- Gap analysis prioritization: W × (100 - P) × importance.
- Endpoints: GET /api/readiness and GET /api/skills/map.
"""

import unittest
from datetime import datetime, date, timedelta, timezone

from services.scoring_engine import (
    RECENCY_HALF_LIFE_DAYS,
    DIFFICULTY_WEIGHTS,
    TYPE_WEIGHTS,
    TIER_WEIGHTS,
    STATUS_NOT_ASSESSED,
    STATUS_LOW_EVIDENCE,
    STATUS_VERIFIED_GAP,
    STATUS_DEVELOPING,
    STATUS_VERIFIED_STRONG,
    PILLAR_NOT_ASSESSED,
    PILLAR_PARTIALLY_ASSESSED,
    PILLAR_ASSESSED,
    TREND_IMPROVING,
    TREND_FLAT,
    TREND_DECLINING,
    TREND_NOT_ENOUGH_DATA,
    calculate_recency_weight,
    get_difficulty_weight,
    get_type_weight,
    calculate_evidence_weight,
    calculate_skill_proficiency,
    calculate_skill_confidence,
    classify_skill_status,
    aggregate_pillar,
    calculate_readiness,
    calculate_trend,
    analyze_skill_gaps,
    build_unified_readiness_object
)
from app import app


class TestPhase2ScoringEngine(unittest.TestCase):
    """Complete unit tests for Phase 2 Scoring Engine."""

    def test_01_acceptance_test_7_recency_decay_half_life(self):
        """
        Acceptance Test 7: Evidence 180 days old has recency weight 0.25.
        recencyWeight = 0.5 ^ (ageInDays / 90)
        """
        # 180 days -> 0.5 ^ (180/90) = 0.5 ^ 2 = 0.25
        w_180 = calculate_recency_weight(180.0)
        self.assertAlmostEqual(w_180, 0.25, places=5)

        # 0 days -> 1.0
        w_0 = calculate_recency_weight(0.0)
        self.assertAlmostEqual(w_0, 1.0, places=5)

        # 90 days -> 0.5
        w_90 = calculate_recency_weight(90.0)
        self.assertAlmostEqual(w_90, 0.5, places=5)

        # 270 days -> 0.125
        w_270 = calculate_recency_weight(270.0)
        self.assertAlmostEqual(w_270, 0.125, places=5)

    def test_02_difficulty_and_type_weights(self):
        """Verifies difficulty and question type multipliers match Section 5.1."""
        self.assertEqual(get_difficulty_weight("EASY"), 0.8)
        self.assertEqual(get_difficulty_weight("MEDIUM"), 1.0)
        self.assertEqual(get_difficulty_weight("HARD"), 1.3)

        self.assertEqual(get_type_weight("MCQ"), 0.7)
        self.assertEqual(get_type_weight("SHORT_ANSWER"), 1.0)
        self.assertEqual(get_type_weight("SCENARIO"), 1.1)
        self.assertEqual(get_type_weight("CODE"), 1.2)
        self.assertEqual(get_type_weight("MOCK_INTERVIEW"), 1.2)
        self.assertEqual(get_type_weight("PRACTICE_ASSIGNMENT"), 1.0)

        # Composite: 90 days old (0.5), HARD (1.3), CODE (1.2) -> 0.5 * 1.3 * 1.2 = 0.78
        cw = calculate_evidence_weight(age_in_days=90.0, difficulty="HARD", evidence_type="CODE")
        self.assertAlmostEqual(cw, 0.78, places=4)

    def test_03_acceptance_test_6_one_medium_short_answer_at_60(self):
        """
        Acceptance Test 6: One MEDIUM short-answer at 60% ->
        P = 60, C ≈ 0.23 + diversity part, status LOW_EVIDENCE (not a gap).
        """
        ev_items = [
            {
                "score": 60.0,
                "age_in_days": 0.0,
                "difficulty": "MEDIUM",
                "evidence_type": "SHORT_ANSWER",
                "is_attempted": True
            }
        ]
        p_skill, sum_w = calculate_skill_proficiency(ev_items)
        self.assertEqual(p_skill, 60.0)
        self.assertEqual(sum_w, 1.0)

        # 1 subskill tested out of 3
        c_skill = calculate_skill_confidence(sum_weights=sum_w, subskills_tested=1, total_subskills_count=3)
        # evidenceFactor = 1.0 / 3.0 = 0.3333 -> 0.7 * 0.3333 = 0.2333
        # diversityFactor = 1.0 / 3.0 = 0.3333 -> 0.3 * 0.3333 = 0.1000
        # C_skill = 0.3333
        self.assertAlmostEqual(c_skill, 0.3333, places=3)
        self.assertLess(c_skill, 0.40)

        # Status must be LOW_EVIDENCE, not a gap!
        status = classify_skill_status(p_skill, c_skill)
        self.assertEqual(status, STATUS_LOW_EVIDENCE)

    def test_04_acceptance_test_8_readiness_with_zero_assessed_skills(self):
        """
        Acceptance Test 8: Readiness with 0 assessed skills = null with 'No evidence yet', not 0%.
        """
        skills = [
            {"skill_id": "s1", "name": "Python ML", "tier": "MANDATORY", "proficiency": None, "status": STATUS_NOT_ASSESSED},
            {"skill_id": "s2", "name": "Transformers", "tier": "MANDATORY", "proficiency": None, "status": STATUS_NOT_ASSESSED},
            {"skill_id": "s3", "name": "System Design", "tier": "PREFERRED", "proficiency": None, "status": STATUS_NOT_ASSESSED}
        ]
        res = calculate_readiness(skills)
        self.assertIsNone(res["verified_score"])
        self.assertIsNone(res["projected_readiness"])
        self.assertEqual(res["formula_breakdown"], "No evidence yet")
        self.assertTrue(res["is_provisional"])
        self.assertEqual(res["skills_mastered_count"], 0)
        self.assertEqual(res["skills_demonstrated_count"], 0)

    def test_05_acceptance_test_9_provisional_badge_missing_mandatory(self):
        """
        Acceptance Test 9: Skills assessed 3/12 with all mandatory unassessed -> PROVISIONAL badge present.
        """
        skills = [
            # 3 mandatory, all unassessed
            {"skill_id": f"m{i}", "name": f"Mandatory {i}", "tier": "MANDATORY", "proficiency": None, "status": STATUS_NOT_ASSESSED}
            for i in range(1, 4)
        ] + [
            # 3 preferred, assessed
            {"skill_id": f"p{i}", "name": f"Preferred {i}", "tier": "PREFERRED", "proficiency": 80.0, "status": STATUS_DEVELOPING}
            for i in range(1, 4)
        ] + [
            # 6 supporting, unassessed
            {"skill_id": f"s{i}", "name": f"Supporting {i}", "tier": "SUPPORTING", "proficiency": None, "status": STATUS_NOT_ASSESSED}
            for i in range(1, 7)
        ]
        self.assertEqual(len(skills), 12)

        res = calculate_readiness(skills)
        self.assertTrue(res["is_provisional"])
        self.assertEqual(res["mandatory_coverage"], 0.0)
        self.assertEqual(len(res["missing_mandatory_skills"]), 3)
        self.assertIn("Mandatory 1", res["missing_mandatory_skills"])

    def test_06_skill_status_transitions(self):
        """Verifies status transitions across confidence and proficiency thresholds."""
        # Unassessed
        self.assertEqual(classify_skill_status(None, 0.8), STATUS_NOT_ASSESSED)

        # Low evidence: score is low or high, but confidence < 0.4
        self.assertEqual(classify_skill_status(50.0, 0.35), STATUS_LOW_EVIDENCE)
        self.assertEqual(classify_skill_status(95.0, 0.39), STATUS_LOW_EVIDENCE)

        # Verified Gap: score < 60 and confidence >= 0.4
        self.assertEqual(classify_skill_status(59.9, 0.40), STATUS_VERIFIED_GAP)
        self.assertEqual(classify_skill_status(40.0, 0.75), STATUS_VERIFIED_GAP)

        # Developing: 60 <= score < 85 and confidence >= 0.4
        self.assertEqual(classify_skill_status(60.0, 0.40), STATUS_DEVELOPING)
        self.assertEqual(classify_skill_status(84.9, 0.80), STATUS_DEVELOPING)

        # Verified Strong: score >= 85 and confidence >= 0.4
        self.assertEqual(classify_skill_status(85.0, 0.40), STATUS_VERIFIED_STRONG)
        self.assertEqual(classify_skill_status(98.0, 0.95), STATUS_VERIFIED_STRONG)

    def test_07_pillar_aggregation_and_coverage(self):
        """Verifies pillar proficiency, coverage ratio, and status classification."""
        skills = [
            {"skill_id": "s1", "tier": "MANDATORY", "proficiency": 80.0},
            {"skill_id": "s2", "tier": "PREFERRED", "proficiency": 90.0},
            {"skill_id": "s3", "tier": "SUPPORTING", "proficiency": None},
            {"skill_id": "s4", "tier": "SUPPORTING", "proficiency": None}
        ]
        pillar = aggregate_pillar(skills, pillar_name="ML Fundamentals")
        self.assertEqual(pillar["coverage_display"], "2/4")
        self.assertEqual(pillar["coverage_ratio"], 0.5)
        self.assertEqual(pillar["status"], PILLAR_ASSESSED)

        # Tier-weighted proficiency: (80 * 1.5 + 90 * 1.0) / (1.5 + 1.0) = (120 + 90) / 2.5 = 210 / 2.5 = 84.0
        self.assertEqual(pillar["proficiency"], 84.0)

        # 0 assessed skills
        unassessed_pillar = aggregate_pillar([{"proficiency": None}, {"proficiency": None}])
        self.assertIsNone(unassessed_pillar["proficiency"])
        self.assertEqual(unassessed_pillar["status"], PILLAR_NOT_ASSESSED)

        # 1/3 assessed -> partially assessed (< 50%)
        partial_pillar = aggregate_pillar([{"proficiency": 70.0}, {"proficiency": None}, {"proficiency": None}])
        self.assertEqual(partial_pillar["status"], PILLAR_PARTIALLY_ASSESSED)

    def test_08_readiness_exact_mathematical_formula(self):
        """
        Verifies Section 5.6 readiness formula:
        ProjectedReadiness = VerifiedScore × (0.4 + 0.6 × WeightedCoverage)
        """
        # Skill 1 (MANDATORY, weight 1.5): score 80.0
        # Skill 2 (PREFERRED, weight 1.0): score 70.0
        # Skill 3 (SUPPORTING, weight 0.7): unassessed
        skills = [
            {"skill_id": "s1", "tier": "MANDATORY", "proficiency": 80.0, "status": STATUS_DEVELOPING},
            {"skill_id": "s2", "tier": "PREFERRED", "proficiency": 70.0, "status": STATUS_DEVELOPING},
            {"skill_id": "s3", "tier": "SUPPORTING", "proficiency": None, "status": STATUS_NOT_ASSESSED}
        ]
        # Total weights: 1.5 + 1.0 + 0.7 = 3.2
        # Assessed weights: 1.5 + 1.0 = 2.5
        # Weighted coverage = 2.5 / 3.2 = 0.78125
        # Verified score = (80.0 * 1.5 + 70.0 * 1.0) / 2.5 = (120 + 70) / 2.5 = 190 / 2.5 = 76.0
        # Projected readiness = 76.0 * (0.4 + 0.6 * 0.78125) = 76.0 * (0.4 + 0.46875) = 76.0 * 0.86875 = 66.025 -> 66.0
        res = calculate_readiness(skills)
        self.assertAlmostEqual(res["raw_verified_score"], 76.0, places=4)
        self.assertAlmostEqual(res["raw_projected_readiness"], 66.025, places=3)
        self.assertEqual(res["verified_score"], 76.0)
        self.assertEqual(res["projected_readiness"], 66.0)
        self.assertIn("Projected Readiness = Verified Score (76.0)", res["formula_breakdown"])

    def test_09_trend_linear_regression_and_insufficient_data_guard(self):
        """Verifies Section 5.7: ≥ 3 distinct days required, slope per week calculation."""
        # 2 days -> not enough data
        sessions_2 = [
            {"date": "2026-11-01", "projected_readiness": 50.0, "verified_score": 60.0},
            {"date": "2026-11-02", "projected_readiness": 55.0, "verified_score": 65.0}
        ]
        t2 = calculate_trend(sessions_2)
        self.assertFalse(t2["has_enough_data"])
        self.assertEqual(t2["trend_label"], TREND_NOT_ENOUGH_DATA)

        # 3 distinct days with rising scores (10 points over 7 days = ~10 pts/week -> IMPROVING)
        sessions_improving = [
            {"date": "2026-11-01", "projected_readiness": 50.0, "verified_score": 60.0},
            {"date": "2026-11-04", "projected_readiness": 55.0, "verified_score": 65.0},
            {"date": "2026-11-08", "projected_readiness": 60.0, "verified_score": 70.0}
        ]
        t_imp = calculate_trend(sessions_improving)
        self.assertTrue(t_imp["has_enough_data"])
        self.assertEqual(t_imp["trend_label"], TREND_IMPROVING)
        self.assertGreater(t_imp["slope_per_week"], 2.0)
        self.assertEqual(t_imp["baseline_vs_latest"]["baseline_score"], 60.0)
        self.assertEqual(t_imp["baseline_vs_latest"]["latest_score"], 70.0)
        self.assertEqual(t_imp["baseline_vs_latest"]["delta"], 10.0)
        self.assertTrue(t_imp["baseline_vs_latest"]["improved"])

    def test_10_gap_analysis_priority_ordering_and_remediation(self):
        """Verifies Section 6: verified gaps prioritized by W × (100 - P) × importance."""
        skills = [
            # Gap 1: MANDATORY (1.5), score 40 (gap 60), importance 5 -> priority = 1.5 * 60 * 5 = 450
            {
                "skill_id": "transformers",
                "name": "Transformers",
                "tier": "MANDATORY",
                "proficiency": 40.0,
                "confidence": 0.6,
                "importance": 5.0,
                "status": STATUS_VERIFIED_GAP,
                "failed_rubrics": ["Multi-head attention projection dimensions", "KV cache memory scaling"]
            },
            # Gap 2: PREFERRED (1.0), score 50 (gap 50), importance 4 -> priority = 1.0 * 50 * 4 = 200
            {
                "skill_id": "sql_opt",
                "name": "SQL Optimization",
                "tier": "PREFERRED",
                "proficiency": 50.0,
                "confidence": 0.5,
                "importance": 4.0,
                "status": STATUS_VERIFIED_GAP,
                "failed_rubrics": ["B-Tree composite index order"]
            },
            # Unassessed skill: must never be called a weakness
            {
                "skill_id": "unassessed_1",
                "name": "Kubernetes",
                "tier": "SUPPORTING",
                "proficiency": None,
                "status": STATUS_NOT_ASSESSED
            }
        ]
        res = analyze_skill_gaps(skills)
        gaps = res["verified_skill_gaps"]
        self.assertEqual(len(gaps), 2)
        # First priority should be Transformers (450 > 200)
        self.assertEqual(gaps[0]["skill_id"], "transformers")
        self.assertEqual(gaps[0]["priority"], 450.0)
        self.assertIn("KV cache", gaps[0]["remediation_action"])

        # Unassessed section
        not_assessed = res["not_yet_assessed"]
        self.assertEqual(len(not_assessed), 1)
        self.assertFalse(not_assessed[0]["is_weakness"])
        self.assertEqual(not_assessed[0]["action_prompt"], "Take quick assessment")

    def test_11_consistency_invariants(self):
        """Verifies Consistency Tests 2 & 3: Mastered <= strong, unassessed never weaknesses."""
        skills = [
            {"skill_id": f"strong_{i}", "proficiency": 90.0, "status": STATUS_VERIFIED_STRONG, "tier": "MANDATORY"}
            for i in range(3)
        ] + [
            {"skill_id": f"unassessed_{i}", "proficiency": None, "status": STATUS_NOT_ASSESSED, "tier": "SUPPORTING"}
            for i in range(4)
        ]
        readiness = calculate_readiness(skills)
        self.assertEqual(readiness["skills_mastered_count"], 3)
        self.assertLessEqual(readiness["skills_mastered_count"], 3)

        gap_analysis = analyze_skill_gaps(skills)
        for u in gap_analysis["not_yet_assessed"]:
            self.assertFalse(u["is_weakness"])

    def test_12_spec_api_readiness_and_skills_map_endpoints(self):
        """Verifies Section 11 endpoints: GET /api/readiness and GET /api/skills/map."""
        client = app.test_client()

        # 1. GET /api/readiness
        resp1 = client.get("/api/readiness?user_id=test_phase2_user&role=AI/ML+Engineer")
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.get_json()
        self.assertEqual(data1["status"], "success")
        self.assertIn("readiness", data1)
        self.assertIn("verified_score", data1["readiness"])
        self.assertIn("projected_readiness", data1["readiness"])
        self.assertIn("formula_breakdown", data1["readiness"])
        self.assertIn("pillars", data1)

        # 2. GET /api/skills/map
        resp2 = client.get("/api/skills/map?user_id=test_phase2_user&role=AI/ML+Engineer")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertEqual(data2["status"], "success")
        self.assertIn("skills", data2)
        self.assertIn("gap_analysis", data2)
        self.assertIn("verified_skill_gaps", data2["gap_analysis"])
        self.assertIn("not_yet_assessed", data2["gap_analysis"])


if __name__ == "__main__":
    unittest.main()
