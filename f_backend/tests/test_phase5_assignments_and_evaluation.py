"""
Phase 5 Test Suite: Assignments & Evaluation Engine.
Verifies:
1. Concrete assignment derivation from (skill gap, misconception, role, difficulty).
2. Incomplete submission detection returning 'needs_revision' without penalizing skill state.
3. Weak submission evaluated via sandbox hidden tests -> verified gap + remediation next action.
4. Strong submission passing hidden tests -> mastery + advance difficulty next action.
5. Deduplication / plagiarism detection rejecting identical answer_hash resubmissions.
6. Verified evidence recording and candidate skill state updates.
"""

import unittest
import uuid
from local_supabase import get_supabase_client
from services.assignment_service import AssignmentService
from services.evaluation_service import EvaluationService


class TestPhase5AssignmentsAndEvaluation(unittest.TestCase):
    """End-to-End verification of assignment generation and multi-tier rubric evaluation."""

    def setUp(self):
        self.supabase = get_supabase_client()
        self.user_id = f"test_cand_p5_{uuid.uuid4().hex[:8]}"

    def test_01_assignment_generation_structure(self):
        """Verifies generated assignment has requirements, deliverables, rubric, and hidden tests."""
        asg = AssignmentService.generate_assignment(
            skill_id="ml_model_evaluation",
            misconception="confused precision with recall on skewed distribution",
            target_role="AI / ML Engineer",
            difficulty="intermediate"
        )

        self.assertIn("assignment_id", asg)
        self.assertEqual(asg["skill_id"], "ml_model_evaluation")
        self.assertIn("requirements", asg)
        self.assertGreaterEqual(len(asg["requirements"]), 3)
        self.assertIn("hidden_tests", asg)
        self.assertGreaterEqual(len(asg["hidden_tests"]), 2)
        self.assertIn("rubric", asg)

        # Rubric weights must sum to 1.0
        total_w = sum(asg["rubric"].values())
        self.assertAlmostEqual(total_w, 1.0, places=2)

    def test_02_end_to_end_three_tier_evaluations(self):
        """
        GATE 5 CORE TEST: Submits an incomplete, a weak, and a strong submission
        for the same assignment; asserts 3 distinct evaluations, 3 distinct skill states,
        and 3 distinct next actions.
        """
        asg = AssignmentService.generate_assignment(
            skill_id="ml_model_evaluation",
            misconception="accuracy paradox on imbalanced classes",
            target_role="AI / ML Engineer",
            difficulty="intermediate"
        )

        # ── Submission A: INCOMPLETE ──
        payload_incomplete = {
            "activity_id": "act_test_p5",
            "code_submission": "# just a comment",
            "text_submission": "I think accuracy is fine."
        }
        eval_incomplete = EvaluationService.evaluate_assignment_submission(
            user_id=self.user_id,
            assignment=asg,
            submission_payload=payload_incomplete,
            supabase_client=self.supabase
        )

        self.assertEqual(eval_incomplete["status"], "needs_revision")
        self.assertFalse(eval_incomplete["is_complete"])
        self.assertIsNone(eval_incomplete["score"])
        self.assertEqual(eval_incomplete["next_action"], "REVISE_CURRENT_ASSIGNMENT")
        self.assertFalse(eval_incomplete["skill_state_updated"])

        # ── Submission B: WEAK ──
        # Code has flawed logic that fails hidden tests
        code_weak = (
            "def evaluate_classifier(y_true, y_pred):\n"
            "    # Flawed: ignores true positives and returns hardcoded accuracy\n"
            "    if not y_true or not y_pred:\n"
            "        return {'status': 'error', 'message': 'empty_input'}\n"
            "    return {'accuracy': 0.5, 'precision': 0.1, 'recall': 0.1, 'f1': 0.1, 'status': 'success'}\n"
        )
        text_weak = "I used basic accuracy and didn't check boundary conditions."
        payload_weak = {
            "activity_id": "act_test_p5",
            "code_submission": code_weak,
            "text_submission": text_weak
        }
        eval_weak = EvaluationService.evaluate_assignment_submission(
            user_id=self.user_id,
            assignment=asg,
            submission_payload=payload_weak,
            supabase_client=self.supabase
        )

        self.assertEqual(eval_weak["status"], "evaluated")
        self.assertTrue(eval_weak["is_complete"])
        self.assertLess(eval_weak["score"], 60.0)
        self.assertEqual(eval_weak["classification"], "VERIFIED_GAP")
        self.assertEqual(eval_weak["next_action"], "REMEDIATION_DRILL")

        # Verify candidate skill state updated to VERIFIED_GAP
        css_weak = self.supabase.table("candidate_skill_states").select("*").eq("user_id", self.user_id).eq("skill_id", "ml_model_evaluation").execute().data[0]
        self.assertEqual(css_weak["status"], "VERIFIED_GAP")

        # ── Submission C: STRONG ──
        # Complete Python implementation passing all hidden tests
        code_strong = (
            "def evaluate_classifier(y_true, y_pred):\n"
            "    if not y_true or not y_pred or len(y_true) != len(y_pred):\n"
            "        return {'status': 'error', 'message': 'empty_input'}\n"
            "    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)\n"
            "    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)\n"
            "    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)\n"
            "    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)\n"
            "    total = len(y_true)\n"
            "    acc = (tp + tn) / total if total > 0 else 0.0\n"
            "    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0\n"
            "    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0\n"
            "    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0\n"
            "    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1': f1, 'status': 'success'}\n"
        )
        text_strong = (
            "We analyze class skew (99:1). Under extreme imbalance, accuracy fails because predicting all zeros "
            "achieves 99% accuracy but 0.0 recall. We optimize Precision-Recall AUC (PR-AUC) over ROC-AUC, "
            "since ROC-AUC presents an overly optimistic picture driven by a massive true negative count. "
            "Time complexity is O(N) linear scan with O(1) auxiliary space. Handled empty input edge cases."
        )
        payload_strong = {
            "activity_id": "act_test_p5",
            "code_submission": code_strong,
            "text_submission": text_strong
        }
        eval_strong = EvaluationService.evaluate_assignment_submission(
            user_id=self.user_id,
            assignment=asg,
            submission_payload=payload_strong,
            supabase_client=self.supabase
        )

        self.assertEqual(eval_strong["status"], "evaluated")
        self.assertTrue(eval_strong["is_complete"])
        self.assertGreaterEqual(eval_strong["score"], 85.0)
        self.assertEqual(eval_strong["classification"], "MASTERED")
        self.assertEqual(eval_strong["next_action"], "ADVANCE_DIFFICULTY")
        self.assertEqual(eval_strong["passed_tests"], eval_strong["total_tests"])

        # Verify candidate skill state updated to MASTERED
        css_strong = self.supabase.table("candidate_skill_states").select("*").eq("user_id", self.user_id).eq("skill_id", "ml_model_evaluation").execute().data[0]
        self.assertEqual(css_strong["status"], "MASTERED")

        # ── Deduplication Test ──
        eval_dup = EvaluationService.evaluate_assignment_submission(
            user_id=self.user_id,
            assignment=asg,
            submission_payload=payload_strong,
            supabase_client=self.supabase
        )
        self.assertEqual(eval_dup["status"], "duplicate_rejected")

        # Print Side-by-Side Comparison for Gate 5 Output
        print("\n" + "=" * 105)
        print("          GATE 5 MULTI-TIER EVALUATION RESULTS (SAME ASSIGNMENT: ml_model_evaluation)")
        print("=" * 105)
        print(f"{'METRIC / ATTRIBUTE':<26} | {'INCOMPLETE':<22} | {'WEAK SUBMISSION':<24} | {'STRONG SUBMISSION':<24}")
        print("-" * 105)
        print(f"{'Evaluation Status':<26} | {eval_incomplete['status']:<22} | {eval_weak['status']:<24} | {eval_strong['status']:<24}")
        print(f"{'Evaluated Score':<26} | {'None (Preserved)':<22} | {str(eval_weak['score']) + '%' :<24} | {str(eval_strong['score']) + '%' :<24}")
        weak_tests_str = f"{eval_weak['passed_tests']}/{eval_weak['total_tests']}"
        strong_tests_str = f"{eval_strong['passed_tests']}/{eval_strong['total_tests']}"
        print(f"{'Hidden Tests Passed':<26} | {'0 / 0 (Skipped)':<22} | {weak_tests_str:<24} | {strong_tests_str:<24}")
        print(f"{'Classification':<26} | {'None':<22} | {eval_weak['classification']:<24} | {eval_strong['classification']:<24}")
        print(f"{'Skill State Update':<26} | {'None (Unchanged)':<22} | {css_weak['status']:<24} | {css_strong['status']:<24}")
        print(f"{'Recommended Next Action':<26} | {eval_incomplete['next_action']:<22} | {eval_weak['next_action']:<24} | {eval_strong['next_action']:<24}")
        print("=" * 105 + "\n")


if __name__ == "__main__":
    unittest.main()

