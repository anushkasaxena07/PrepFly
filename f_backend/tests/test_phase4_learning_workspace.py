"""
Phase 4 Test Suite: Learning Workspace & Content Generation.
Verifies the complete 7-step learning workspace structure, sandbox code execution,
personalization based on candidate recurring mistakes, and 3-tier progressive hint logging.
"""

import unittest
from services.learning_service import LearningService


class TestPhase4LearningWorkspace(unittest.TestCase):
    """Unit and sandbox execution tests for Phase 4 Learning Service."""

    def test_01_seven_step_workspace_structure(self):
        """Verifies workspace contains all 7 steps with complete non-empty schemas."""
        context = {
            "goal": {
                "target_company": "Stripe",
                "target_role": "Backend Engineer",
                "candidate_actual_experience_years": 3.0,
                "learning_preference": "hands-on"
            },
            "top_recurring_mistakes": ["race_condition_deadlock"]
        }

        workspace = LearningService.generate_workspace_content(
            activity_id="act_test_01",
            skill_id="cs_concurrency",
            candidate_context=context,
            difficulty="intermediate"
        )

        # Verify all 7 steps present
        self.assertIn("step_1_why", workspace)
        self.assertIn("step_2_learn", workspace)
        self.assertIn("step_3_practice", workspace)
        self.assertIn("step_4_assignment", workspace)
        self.assertIn("step_5_submit", workspace)
        self.assertIn("step_6_evaluate", workspace)
        self.assertIn("step_7_next_action", workspace)

        # Step 1: Why This Matters
        self.assertIn("personalized_context", workspace["step_1_why"])
        self.assertIn("Stripe", workspace["step_1_why"]["personalized_context"])

        # Step 2: Learn
        learn = workspace["step_2_learn"]
        self.assertIn("simple_definition", learn)
        self.assertIn("technical_explanation", learn)
        self.assertIn("code_example", learn)
        self.assertIn("visual_or_math", learn)
        self.assertIn("common_mistakes", learn)
        self.assertIn("interview_relevance", learn)

        # Step 4: Assignment (No answer key leaked)
        asg = workspace["step_4_assignment"]
        self.assertNotIn("solution", asg)
        self.assertNotIn("answer_key", asg)
        self.assertIn("rubric_weights", asg)

        # Step 5: Submit (3 hint tiers)
        hints = workspace["step_5_submit"]["hints"]
        self.assertIn("level_1_nudge", hints)
        self.assertIn("level_2_structure", hints)
        self.assertIn("level_3_partial", hints)

    def test_02_sandbox_code_execution_verification(self):
        """Verifies sandbox executes code example and logs performance metrics."""
        context = {
            "goal": {"target_company": "Google", "target_role": "AI / ML Engineer", "candidate_actual_experience_years": 2.0},
            "top_recurring_mistakes": []
        }

        workspace = LearningService.generate_workspace_content(
            activity_id="act_test_02",
            skill_id="dl_frameworks_pytorch_tensorflow",
            candidate_context=context,
            difficulty="intermediate"
        )

        sandbox_log = workspace.get("sandbox_verification")
        self.assertIsNotNone(sandbox_log)
        self.assertTrue(sandbox_log["compiled"])
        self.assertTrue(sandbox_log["executed"])
        self.assertEqual(sandbox_log["returncode"], 0)
        self.assertIn("Sandbox execution passed", sandbox_log["stdout"])
        self.assertGreater(sandbox_log["execution_time_ms"], 0.0)

    def test_03_candidate_mistake_personalization_differentiation(self):
        """Verifies two candidates with different mistake histories receive visibly different lessons."""
        cand1_context = {
            "goal": {"target_company": "OpenAI", "target_role": "AI / ML Engineer", "candidate_actual_experience_years": 2.0},
            "top_recurring_mistakes": ["overfitting_data_leakage"]
        }
        cand2_context = {
            "goal": {"target_company": "DeepMind", "target_role": "AI / ML Engineer", "candidate_actual_experience_years": 4.0},
            "top_recurring_mistakes": ["vanishing_gradient_saturation"]
        }

        # Generate on the SAME skill
        ws1 = LearningService.generate_workspace_content(
            activity_id="act_c1",
            skill_id="dl_frameworks_pytorch_tensorflow",
            candidate_context=cand1_context
        )
        ws2 = LearningService.generate_workspace_content(
            activity_id="act_c2",
            skill_id="dl_frameworks_pytorch_tensorflow",
            candidate_context=cand2_context
        )

        c1_mistakes = [m["mistake_title"] for m in ws1["step_2_learn"]["common_mistakes"]]
        c2_mistakes = [m["mistake_title"] for m in ws2["step_2_learn"]["common_mistakes"]]

        # Candidate 1 common mistakes should highlight data leakage
        self.assertIn("Candidate Recurring Blind Spot: Overfitting Data Leakage", c1_mistakes)
        self.assertNotIn("Candidate Recurring Blind Spot: Overfitting Data Leakage", c2_mistakes)

        # Candidate 2 common mistakes should highlight vanishing gradient
        self.assertIn("Candidate Recurring Blind Spot: Vanishing Gradient Saturation", c2_mistakes)
        self.assertNotIn("Candidate Recurring Blind Spot: Vanishing Gradient Saturation", c1_mistakes)

        # Print Side-by-Side Comparison for Gate 4 output
        print("\n" + "=" * 90)
        print("          GATE 4 PERSONALIZED WORKSPACE CONTENT COMPARISON (SAME SKILL)")
        print("=" * 90)
        print(f"{'ATTRIBUTE':<22} | {'CANDIDATE 1 (OpenAI)':<32} | {'CANDIDATE 2 (DeepMind)':<32}")
        print("-" * 90)
        print(f"{'Target Company':<22} | {'OpenAI':<32} | {'DeepMind':<32}")
        print(f"{'Experience Level':<22} | {'2.0 Years':<32} | {'4.0 Years':<32}")
        print(f"{'Top Injected Blindspot':<22} | {'Overfitting Data Leakage':<32} | {'Vanishing Gradient Saturation':<32}")
        print(f"{'Sandbox Verifier':<22} | {ws1['sandbox_verification']['stdout'][:32]:<32} | {ws2['sandbox_verification']['stdout'][:32]:<32}")
        print(f"{'Execution Time (ms)':<22} | {str(ws1['sandbox_verification']['execution_time_ms']) + ' ms':<32} | {str(ws2['sandbox_verification']['execution_time_ms']) + ' ms':<32}")
        print("=" * 90 + "\n")

    def test_04_three_tier_hint_logging_and_modifiers(self):
        """Verifies progressive hints apply correct evidence quality modifiers."""
        # Level 1 Nudge: 5% penalty, modifier = 0.95
        h1 = LearningService.record_hint_usage(activity_id="act_01", user_id="u1", hint_level=1)
        self.assertEqual(h1["penalty_percentage"], 5.0)
        self.assertEqual(h1["evidence_quality_modifier"], 0.95)

        # Level 2 Structure: 10% penalty, modifier = 0.90
        h2 = LearningService.record_hint_usage(activity_id="act_01", user_id="u1", hint_level=2)
        self.assertEqual(h2["penalty_percentage"], 10.0)
        self.assertEqual(h2["evidence_quality_modifier"], 0.90)

        # Level 3 Partial: 15% penalty, modifier = 0.85
        h3 = LearningService.record_hint_usage(activity_id="act_01", user_id="u1", hint_level=3)
        self.assertEqual(h3["penalty_percentage"], 15.0)
        self.assertEqual(h3["evidence_quality_modifier"], 0.85)


if __name__ == "__main__":
    unittest.main()

