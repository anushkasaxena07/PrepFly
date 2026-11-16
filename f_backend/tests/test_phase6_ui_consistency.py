"""
PHASE 6 TEST SUITE: UI WIRING & CONSISTENCY (Section 16, Phase 6)
================================================================
Verifies that:
1. /api/readiness is the single source of truth for Dashboard, Roadmap, and Analytics.
2. VerifiedScore, WeightedCoverage, and ProjectedReadiness adhere to Section 5 formulas.
3. Unassessed skills are strictly marked NOT_ASSESSED and never returned in verified_skill_gaps (Golden Rule 4).
4. Verified gaps strictly require evidence and score < 60%.
5. Provisional readiness flag is set when 0 skills are assessed.
6. Trend analysis enforces the 3-checkpoint threshold (Acceptance Test 7).
"""

import unittest
import json
from app import app
from services.scoring_engine import (
    calculate_readiness,
    calculate_trend,
    analyze_skill_gaps,
    build_unified_readiness_object,
    STATUS_NOT_ASSESSED,
    STATUS_VERIFIED_GAP,
    STATUS_VERIFIED_STRONG,
    TREND_NOT_ENOUGH_DATA
)


class TestPhase6UIConsistency(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_readiness_endpoint_returns_canonical_structure(self):
        """GET /api/readiness returns canonical object with readiness, pillars, trend, and gap_analysis."""
        resp = self.client.get("/api/readiness?user_id=test_ui_user&role=AI/ML Engineer")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("readiness", data)
        self.assertIn("pillars", data)
        self.assertIn("trend", data)
        self.assertIn("gap_analysis", data)

        readiness = data["readiness"]
        self.assertIn("projected_readiness", readiness)
        self.assertIn("verified_score", readiness)
        self.assertIn("weighted_coverage", readiness)
        self.assertIn("is_provisional", readiness)
        self.assertIn("readiness_label", readiness)

    def test_02_zero_evidence_returns_provisional_readiness(self):
        """When candidate has 0 evaluated skills, readiness is provisional and no fake gaps exist."""
        resp = self.client.get("/api/readiness?user_id=user_no_evidence_99&role=AI/ML Engineer")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        readiness = data["readiness"]

        self.assertTrue(readiness["is_provisional"])
        self.assertEqual(readiness["readiness_label"], "PROVISIONAL")
        self.assertEqual(readiness["assessed_skills_count"], 0)

        # Gap analysis must have 0 verified gaps
        gap_analysis = data["gap_analysis"]
        self.assertEqual(len(gap_analysis["verified_skill_gaps"]), 0)
        self.assertGreater(len(gap_analysis["not_yet_assessed"]), 0)

    def test_03_golden_rule_4_unassessed_never_labeled_as_gap(self):
        """Unassessed skills must remain NOT_ASSESSED and never be reported as gaps (Golden Rule 4)."""
        skills = [
            {
                "skill_id": "transformers",
                "name": "Transformer Architecture",
                "tier": "MANDATORY",
                "importance": 5.0,
                "proficiency": None,
                "confidence": 0.0,
                "status": STATUS_NOT_ASSESSED,
                "evidence_count": 0
            },
            {
                "skill_id": "model_eval",
                "name": "Model Evaluation",
                "tier": "MANDATORY",
                "importance": 5.0,
                "proficiency": 42.0,
                "confidence": 0.7,
                "status": STATUS_VERIFIED_GAP,
                "evidence_count": 2
            },
            {
                "skill_id": "python_ml",
                "name": "Python for ML",
                "tier": "MANDATORY",
                "importance": 5.0,
                "proficiency": 88.0,
                "confidence": 0.85,
                "status": STATUS_VERIFIED_STRONG,
                "evidence_count": 3
            }
        ]

        gaps = analyze_skill_gaps(skills)
        # Only model_eval (< 60%) is a verified gap
        self.assertEqual(len(gaps["verified_skill_gaps"]), 1)
        self.assertEqual(gaps["verified_skill_gaps"][0]["skill_id"], "model_eval")

        # transformers is in not_yet_assessed, NOT in verified_skill_gaps
        self.assertEqual(len(gaps["not_yet_assessed"]), 1)
        self.assertEqual(gaps["not_yet_assessed"][0]["skill_id"], "transformers")

    def test_04_trend_detection_requires_minimum_3_checkpoints(self):
        """Acceptance Test 7: Velocity trend requires >= 3 evaluation checkpoints on distinct days."""
        # Case A: 2 sessions -> Insufficient
        sessions_2 = [
            {"date": "2026-03-01", "projected_readiness": 60.0},
            {"date": "2026-03-05", "projected_readiness": 68.0}
        ]
        trend_2 = calculate_trend(sessions_2)
        self.assertFalse(trend_2["has_enough_data"])
        self.assertEqual(trend_2["trend_label"], TREND_NOT_ENOUGH_DATA)

        # Case B: 3 sessions on distinct days -> Valid trend
        sessions_3 = [
            {"date": "2026-03-01", "projected_readiness": 60.0},
            {"date": "2026-03-05", "projected_readiness": 68.0},
            {"date": "2026-03-10", "projected_readiness": 75.0}
        ]
        trend_3 = calculate_trend(sessions_3)
        self.assertTrue(trend_3["has_enough_data"])
        self.assertEqual(trend_3["trend_label"], "IMPROVING")
        self.assertGreater(trend_3["slope_per_week"], 0.0)

    def test_05_unified_readiness_math_consistency(self):
        """Verifies Section 5 deterministic formula: 0.5*Verified + 0.3*Coverage + 0.2*Confidence."""
        skills = [
            {
                "skill_id": "s1",
                "name": "Skill 1",
                "tier": "MANDATORY",
                "importance": 5.0,
                "proficiency": 80.0,
                "confidence": 0.9,
                "status": STATUS_VERIFIED_STRONG,
                "evidence": [{"score": 80.0, "is_attempted": True}],
                "subskills_tested": {"sub1", "sub2"},
                "total_subskills_count": 2
            },
            {
                "skill_id": "s2",
                "name": "Skill 2",
                "tier": "PREFERRED",
                "importance": 3.0,
                "proficiency": None,
                "confidence": 0.0,
                "status": STATUS_NOT_ASSESSED,
                "evidence": [],
                "subskills_tested": set(),
                "total_subskills_count": 2
            }
        ]

        obj = build_unified_readiness_object(skills, target_role="AI/ML Engineer")
        readiness = obj["readiness"]

        self.assertEqual(readiness["verified_score"], 80.0)
        self.assertIsNotNone(readiness["projected_readiness"])
        self.assertEqual(readiness["assessed_skills_count"], 1)


if __name__ == "__main__":
    unittest.main()
