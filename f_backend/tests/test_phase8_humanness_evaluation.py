"""
Tests for Phase 8: Reliability, Cost, Safety and Evaluation of Humanness.
Runs offline evaluation harness across all simulated candidate personas and personalities.
Validates:
1. Follow-up specificity >= 90%
2. Opener repetition rate < 5%
3. Track scope violations == 0
4. Unsupported / hallucinated claims == 0
5. End-request success rate == 100%
6. Turn latency p95 <= 4.0s
7. Unit cost per 15-minute interview <= $0.02
"""

import unittest
from services.humanness_evaluator import HumannessEvaluator


class TestPhase8HumannessEvaluation(unittest.TestCase):
    def test_humanness_metrics_benchmark(self):
        """Execute full evaluation across all 6 candidate personas and 5 personalities."""
        report = HumannessEvaluator.evaluate_all_personas()
        summary = report["aggregate_summary"]
        cost = report["cost_analysis"]
        personas = report["persona_results"]

        # 1. Follow-up Specificity
        self.assertGreaterEqual(
            summary["followup_specificity_pct"], 90.0,
            f"Follow-up specificity fell below 90%: {summary['followup_specificity_pct']}%"
        )

        # 2. Repetition Rate
        self.assertLess(
            summary["repetition_rate_pct"], 5.0,
            f"Consecutive opener repetition rate exceeded 5%: {summary['repetition_rate_pct']}%"
        )

        # 3. Scope Violations
        self.assertEqual(
            summary["scope_violations_count"], 0,
            f"Found {summary['scope_violations_count']} track scope violations!"
        )

        # 4. Unsupported Claims
        self.assertEqual(
            summary["unsupported_claims_count"], 0,
            f"Found {summary['unsupported_claims_count']} unsupported resume claims!"
        )

        # 5. End Request Clean Termination
        self.assertEqual(
            summary["end_request_success_pct"], 100.0,
            f"End request success rate was below 100%: {summary['end_request_success_pct']}%"
        )

        # 6. Latency Target
        self.assertTrue(
            summary["target_latency_met"],
            f"p95 latency exceeded 4.0s target: {summary['p95_latency_s']}s"
        )
        self.assertLessEqual(summary["p50_latency_s"], 3.5)
        self.assertLessEqual(summary["p95_latency_s"], 4.0)

        # 7. Unit Cost
        self.assertLess(
            cost["total_cost_per_interview_usd"], 0.02,
            f"Cost per interview exceeded $0.02: ${cost['total_cost_per_interview_usd']}"
        )
        self.assertGreater(cost["interviews_per_dollar"], 50)


if __name__ == "__main__":
    unittest.main()

