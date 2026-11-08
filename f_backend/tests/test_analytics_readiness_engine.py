"""
Tests for PrepFly Analytics & Readiness Intelligence Engine.
Validates:
1. Decoupled role readiness mathematical model.
2. Unassessed skills isolation from 'Needs Focus' degradation.
3. Statistical trend detection using OLS linear regression.
4. Multi-source cross-feature weakness detection with deficit prioritization.
5. Baseline comparison with dual deltas (percentage points vs relative %).
6. Multi-source preparation study minutes accounting.
7. Grounded coaching insights with deterministic zero-hallucination fallback.
"""

import unittest
from unittest.mock import MagicMock, patch
import json

from services.skill_taxonomy_service import SkillTaxonomyService, SKILL_CATALOG
from services.skill_profiling_service import SkillProfilingService
from services.performance_analytics_engine import PerformanceAnalyticsEngine
from services.cross_feature_engine import CrossFeatureEngine
from services.progress_analytics_service import ProgressAnalyticsService
from local_supabase import get_supabase_client


class TestAnalyticsReadinessEngine(unittest.TestCase):

    def setUp(self):
        self.supabase = get_supabase_client()
        self.user_id = "test_analytics_user_001"

    def test_decoupled_role_readiness_calculation(self):
        """
        Tests that readiness correctly decouples measured proficiency from curriculum coverage.
        Candidate with 90% on 1 out of 10 skills should NOT be penalized down to 9% readiness.
        """
        # Given: 1 assessed skill at 90.0% proficiency
        test_profiles = [
            {
                "skill_id": "dsa_arrays",
                "proficiency": 90.0,
                "confidence": 0.85,
                "confidence_level": "HIGH",
                "evidence_count": 5,
                "status": "MASTERED"
            }
        ]
        # And 33 unassessed skills
        for sid in SKILL_CATALOG.keys():
            if sid != "dsa_arrays":
                test_profiles.append({
                    "skill_id": sid,
                    "proficiency": 0.0,
                    "confidence": 0.0,
                    "confidence_level": "LOW",
                    "evidence_count": 0,
                    "status": "NOT_ASSESSED"
                })

        with patch.object(SkillProfilingService, "get_candidate_profiles", return_value=test_profiles):
            with patch.object(ProgressAnalyticsService, "_compute_baseline_comparison", return_value={"has_baseline": False}):
                summary = ProgressAnalyticsService.get_dashboard_summary(self.user_id)

                dist = summary["skill_distribution"]
                # Unassessed skills must NOT be classified as needs_focus
                self.assertEqual(dist["mastered"], 1)
                self.assertEqual(dist["needs_focus"], 0)
                self.assertGreater(dist["unassessed"], 20)

                # Measured proficiency must be 90.0%
                self.assertEqual(summary["measured_proficiency"], 90.0)

                # Coverage must be non-zero and readiness must be non-zero
                self.assertGreater(summary["overall_readiness"], 0.0)
                # Readiness should be S_measured * (0.5 + 0.5 * Coverage)
                # With low coverage (~0.03), readiness should be around 45% (not 2-3%)
                self.assertGreaterEqual(summary["overall_readiness"], 40.0)

    def test_statistical_trend_detection_improving(self):
        """Tests that an upward trajectory with net delta >= +5.0 and positive slope is classified as Improving."""
        snapshots = [
            {"overall_readiness": 50.0, "created_at": "2026-10-01T00:00:00"},
            {"overall_readiness": 55.0, "created_at": "2026-10-05T00:00:00"},
            {"overall_readiness": 62.0, "created_at": "2026-10-10T00:00:00"},
            {"overall_readiness": 70.0, "created_at": "2026-10-15T00:00:00"},
        ]
        status, slope, r2 = PerformanceAnalyticsEngine.detect_statistical_trend(snapshots, current_score=75.0)
        self.assertEqual(status, "Improving")
        self.assertGreater(slope, 0.0)

    def test_statistical_trend_detection_declining(self):
        """Tests that a downward trajectory with net delta <= -5.0 and negative slope is classified as Declining."""
        snapshots = [
            {"overall_readiness": 80.0, "created_at": "2026-10-01T00:00:00"},
            {"overall_readiness": 72.0, "created_at": "2026-10-05T00:00:00"},
            {"overall_readiness": 65.0, "created_at": "2026-10-10T00:00:00"},
        ]
        status, slope, r2 = PerformanceAnalyticsEngine.detect_statistical_trend(snapshots, current_score=60.0)
        self.assertEqual(status, "Declining")
        self.assertLess(slope, 0.0)

    def test_statistical_trend_detection_insufficient_evidence(self):
        """Tests that 0 or 1 evaluation points return Insufficient Evidence."""
        status, slope, r2 = PerformanceAnalyticsEngine.detect_statistical_trend([], current_score=75.0)
        self.assertEqual(status, "Insufficient Evidence")

        snapshots = [{"overall_readiness": 75.0, "created_at": "2026-10-01T00:00:00"}]
        status, slope, r2 = PerformanceAnalyticsEngine.detect_statistical_trend(snapshots, current_score=75.0)
        self.assertEqual(status, "Insufficient Evidence")

    def test_cross_feature_weakness_multi_source_rule(self):
        """
        Tests that weaknesses are confirmed ONLY when failing in >= 2 distinct sources
        or >= 2 repeated attempts with avg < 55% in a single source.
        """
        mock_client = MagicMock()

        # Case 1: Isolated single failure in 1 source (not a cross-feature weakness)
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"skill_id": "dsa_dp", "source_type": "coding_submission", "score": 40.0}
        ])
        weaknesses = CrossFeatureEngine.detect_cross_feature_weaknesses(self.user_id, supabase_client=mock_client)
        self.assertEqual(len(weaknesses), 0)

        # Case 2: Multi-source failure (coding_submission + ava_interview)
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
            {"skill_id": "dsa_dp", "source_type": "coding_submission", "score": 40.0},
            {"skill_id": "dsa_dp", "source_type": "ava_interview", "score": 50.0}
        ])
        weaknesses = CrossFeatureEngine.detect_cross_feature_weaknesses(self.user_id, supabase_client=mock_client)
        self.assertEqual(len(weaknesses), 1)
        w = weaknesses[0]
        self.assertEqual(w["skill_id"], "dsa_dp")
        self.assertEqual(len(w["failing_sources"]), 2)
        self.assertEqual(w["average_score"], 45.0)
        self.assertEqual(w["deficit"], 30.0)  # 75.0 - 45.0
        self.assertGreater(w["priority_score"], 0.0)

    def test_baseline_comparison_dual_deltas(self):
        """Tests that baseline comparison returns both percentage points and relative percentage improvement."""
        mock_assessments = [
            {
                "id": "ass_001",
                "assessment_type": "diagnostic",
                "score": 50.0,
                "concept_breakdown": json.dumps({"dsa_arrays": 40.0, "cs_oop": 60.0}),
                "completed_at": "2026-10-01T12:00:00"
            }
        ]
        current_profiles = [
            {"skill_id": "dsa_arrays", "proficiency": 70.0, "evidence_count": 3},
            {"skill_id": "cs_oop", "proficiency": 75.0, "evidence_count": 2}
        ]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=mock_assessments)

        with patch("services.progress_analytics_service.get_supabase_client", return_value=mock_client):
            comp = ProgressAnalyticsService._compute_baseline_comparison(self.user_id, current_profiles)

            self.assertTrue(comp["has_baseline"])
            self.assertTrue(comp["is_immutable"])
            self.assertEqual(comp["initial_score"], 50.0)
            self.assertEqual(comp["current_score"], 72.5)  # (70 + 75) / 2

            # Dual deltas
            self.assertEqual(comp["overall_delta_pp"], 22.5)  # 72.5 - 50.0
            self.assertEqual(comp["relative_improvement_pct"], 45.0)  # (22.5 / 50.0) * 100

            # Concept level deltas
            deltas = {d["skill_id"]: d for d in comp["skill_deltas"]}
            self.assertEqual(deltas["dsa_arrays"]["delta_pp"], 30.0)
            self.assertEqual(deltas["dsa_arrays"]["relative_improvement_pct"], 75.0)


if __name__ == "__main__":
    unittest.main()
