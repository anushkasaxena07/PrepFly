import os
import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_supabase import SQLiteSupabaseMock
from services.adaptive_assessment_engine import AdaptiveAssessmentEngine
from services.mentor_service import MentorService
from services.question_generator import QuestionGenerator


class TestAdaptiveDiagnosticRegression(unittest.TestCase):
    def setUp(self):
        self.client = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"diag-reg-{uuid.uuid4().hex[:8]}"

    # 1. Identical & semantically duplicate questions are rejected
    def test_01_identical_and_paraphrased_questions_rejected(self):
        duplicate_text = "Explain how Residual Skip Connections prevent vanishing gradients in deep neural networks."
        v_hash = QuestionGenerator.compute_variation_hash(duplicate_text)

        mock_llm = MagicMock()
        r_dup = MagicMock()
        r_dup.content = (
            '{"question_text": "' + duplicate_text + '",'
            '"question_type":"conceptual","expected_concepts":["Residual connections"],'
            '"rubric":{"core":50,"depth":50}}'
        )
        r_paraphrase = MagicMock()
        r_paraphrase.content = (
            '{"question_text": "Explain how residual skip connections prevent vanishing gradients in deep neural networks?",'
            '"question_type":"conceptual","expected_concepts":["Residual connections"],'
            '"rubric":{"core":50,"depth":50}}'
        )
        r_unique = MagicMock()
        r_unique.content = (
            '{"question_text": "How does Layer Normalization differ mathematically from Batch Normalization inside Transformer decoder blocks?",'
            '"question_type":"conceptual","expected_concepts":["LayerNorm normalizes across feature dimension per token"],'
            '"rubric":{"normalization_axis":50,"inference_behavior":50}}'
        )
        mock_llm.invoke.side_effect = [r_dup, r_paraphrase, r_unique]

        with patch("services.question_generator.safe_invoke_llm", side_effect=[r_dup.content, r_paraphrase.content, r_unique.content]):
            q = QuestionGenerator.generate_question(
                context={"role": "ai_ml_engineer", "skill_id": "dl_neural_networks", "difficulty": "Intermediate", "turn_index": 2},
                chat_model=mock_llm,
                prior_variation_hashes={v_hash},
                prior_question_texts=[duplicate_text],
            )

        self.assertEqual(q["source"], "gemini")
        self.assertIn("Layer Normalization", q["question_text"])
        self.assertNotEqual(q["variation_hash"], v_hash)

    # 2. Different questions can assess the exact same skill without repeating
    def test_02_different_questions_assess_same_skill(self):
        seen_hashes = set()
        seen_texts = []
        seen_qids = set()

        for turn in range(1, 6):
            q = QuestionGenerator.generate_question(
                context={
                    "user_id": self.user_id,
                    "assessment_id": "ass_same_skill",
                    "role": "backend_developer",
                    "skill_id": "sys_caching",
                    "difficulty": "Intermediate",
                    "turn_index": turn,
                },
                chat_model=None,
                prior_variation_hashes=seen_hashes,
                prior_question_texts=seen_texts,
            )
            self.assertEqual(q["skill_id"], "sys_caching")
            self.assertNotIn(q["variation_hash"], seen_hashes)
            self.assertNotIn(q["question_id"], seen_qids)
            self.assertFalse(QuestionGenerator.is_duplicate_question(q["question_text"], seen_hashes, seen_texts))
            seen_hashes.add(q["variation_hash"])
            seen_texts.append(q["question_text"])
            seen_qids.add(q["question_id"])

    # 3. Different skills & roles generate role-relevant questions (not AI/ML for everyone)
    def test_03_different_roles_and_skills_generate_relevant_questions(self):
        fe_session = AdaptiveAssessmentEngine.start_session(
            user_id=f"{self.user_id}_fe",
            target_role="Frontend Developer",
            question_budget=3,
            supabase_client=self.client,
        )
        be_session = AdaptiveAssessmentEngine.start_session(
            user_id=f"{self.user_id}_be",
            target_role="Backend Developer",
            question_budget=3,
            supabase_client=self.client,
        )
        fe_q = fe_session["current_question"]
        be_q = be_session["current_question"]

        self.assertNotIn(fe_q["skill_id"], ("dl_transformers", "genai_llm_fundamentals", "ml_model_evaluation"))
        self.assertNotIn(be_q["skill_id"], ("dl_transformers", "genai_llm_fundamentals", "ml_model_evaluation"))
        self.assertNotEqual(fe_q["question_text"], be_q["question_text"])

    # 4 & 5. Correct vs partial vs incorrect answers produce properly differentiated deterministic scores
    def test_04_05_correct_partial_and_incorrect_answers_differentiated(self):
        expected = [
            "Hash map complement lookup",
            "Single-pass O(N) time complexity",
            "O(N) space complexity",
        ]
        rubric = {"algorithm": 40, "complexity": 35, "edge_cases": 25}
        q_text = "Given an array of integers and a target, find two indices adding up to target in O(N) time."

        strong_res = AdaptiveAssessmentEngine._evaluate_answer(
            question_text=q_text,
            answer="Use a hash map storing each value's index during single-pass traversal to look up target minus current complement in O(1), yielding O(N) time and O(N) space complexity because duplicate values are checked before insert.",
            skill_id="dsa_arrays",
            raw_expected=expected,
            raw_rubric=rubric,
        )
        partial_res = AdaptiveAssessmentEngine._evaluate_answer(
            question_text=q_text,
            answer="A hash map can find complements in linear O(N) time.",
            skill_id="dsa_arrays",
            raw_expected=expected,
            raw_rubric=rubric,
        )
        wrong_res = AdaptiveAssessmentEngine._evaluate_answer(
            question_text=q_text,
            answer="Sort alphabetically and pick the weather forecast.",
            skill_id="dsa_arrays",
            raw_expected=expected,
            raw_rubric=rubric,
        )

        self.assertGreaterEqual(strong_res["score"], 75.0)
        self.assertGreater(partial_res["score"], wrong_res["score"])
        self.assertLess(partial_res["score"], strong_res["score"])
        self.assertLessEqual(wrong_res["score"], 30.0)
        # Re-evaluating same input gives identical deterministic score
        self.assertEqual(
            strong_res["score"],
            AdaptiveAssessmentEngine._evaluate_answer(
                question_text=q_text,
                answer="Use a hash map storing each value's index during single-pass traversal to look up target minus current complement in O(1), yielding O(N) time and O(N) space complexity because duplicate values are checked before insert.",
                skill_id="dsa_arrays",
                raw_expected=expected,
                raw_rubric=rubric,
            )["score"],
        )

    # 6. Numeric zero handling (not treated as missing/empty; correctness depends on expected answer/rubric)
    def test_06_numeric_zero_handled_correctly_not_missing(self):
        res_zero_correct = AdaptiveAssessmentEngine._evaluate_answer(
            question_text="How many comparisons are required to binary search an empty array of length 0?",
            answer="0",
            skill_id="dsa_binary_search",
            raw_expected=["0 comparisons required when array length is 0"],
            raw_rubric={"exact_value": 100},
            expected_answer="0",
        )
        res_zero_int = AdaptiveAssessmentEngine._evaluate_answer(
            question_text="How many comparisons are required to binary search an empty array of length 0?",
            answer=0,
            skill_id="dsa_binary_search",
            raw_expected=["0 comparisons required when array length is 0"],
            raw_rubric={"exact_value": 100},
            expected_answer="0",
        )
        res_zero_wrong = AdaptiveAssessmentEngine._evaluate_answer(
            question_text="Explain how Consistent Hashing prevents hotspot keys using virtual nodes.",
            answer="0",
            skill_id="sys_sharding_replication",
            raw_expected=["Hashing keys and nodes onto a ring", "Virtual nodes balance partitions"],
            raw_rubric={"ring": 50, "vnodes": 50},
        )

        self.assertFalse(res_zero_correct["is_empty"])
        self.assertFalse(res_zero_int["is_empty"])
        self.assertGreaterEqual(res_zero_correct["score"], 85.0)
        self.assertGreaterEqual(res_zero_int["score"], 85.0)
        self.assertFalse(res_zero_wrong["is_empty"])
        self.assertLessEqual(res_zero_wrong["score"], 20.0)

    # 7. Empty answers distinguished cleanly from numeric 0
    def test_07_empty_answers_distinguished_from_numeric_zero(self):
        for blank in ("", "   ", None):
            res = AdaptiveAssessmentEngine._evaluate_answer(
                question_text="How many comparisons?",
                answer=blank,
                skill_id="dsa_arrays",
                raw_expected=["0"],
                raw_rubric={"accuracy": 100},
                expected_answer="0",
            )
            self.assertTrue(res["is_empty"])
            self.assertEqual(res["score"], 0.0)
            self.assertEqual(res["evaluation_status"], "evaluated")

    # 8 & 9. Evaluator failure does NOT silently become 0% incorrect, and valid scores match mean
    def test_08_09_evaluator_failure_excluded_from_score_and_final_matches_evals(self):
        sess = AdaptiveAssessmentEngine.start_session(
            user_id=self.user_id,
            target_role="Backend Developer",
            question_budget=3,
            supabase_client=self.client,
        )
        ass_id = sess["assessment_id"]

        # Turn 1: Valid strong evaluation -> 80.0
        r1 = AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer="Answer 1",
            idempotency_key=f"{ass_id}_t1",
            supabase_client=self.client,
            evaluator_fn=lambda **_kw: {"score": 80.0, "confidence": 0.9},
        )
        self.assertEqual(r1["evaluation"]["score"], 80.0)
        self.assertEqual(r1["evaluation"]["evaluation_status"], "evaluated")

        # Turn 2: Simulated LLM/evaluator outage -> must mark failed & None, NOT 0% incorrect!
        r2 = AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=2,
            answer="Detailed answer whose grader timed out",
            idempotency_key=f"{ass_id}_t2",
            supabase_client=self.client,
            evaluator_fn=lambda **_kw: (_ for _ in ()).throw(TimeoutError("Grader timed out")),
        )
        self.assertIsNone(r2["evaluation"]["score"])
        self.assertEqual(r2["evaluation"]["evaluation_status"], "failed")

        # Turn 3: Valid evaluation -> 60.0
        final = AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=3,
            answer="Answer 3",
            idempotency_key=f"{ass_id}_t3",
            supabase_client=self.client,
            evaluator_fn=lambda **_kw: {"score": 60.0, "confidence": 0.85},
        )
        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["evaluated_count"], 2)
        self.assertEqual(final["pending_or_failed_count"], 1)
        # Mean over ONLY the 2 valid evaluated turns: (80.0 + 60.0) / 2 = 70.0 (NOT dragged down by failed 0!)
        self.assertEqual(final["overall_score"], 70.0)

    # 10 & 11. Low evidence -> low confidence; curriculum coverage reflects distinct assessed skills
    def test_10_11_confidence_and_curriculum_coverage_honesty(self):
        sess = AdaptiveAssessmentEngine.start_session(
            user_id=self.user_id,
            target_role="Software Development Engineer",
            question_budget=1,
            supabase_client=self.client,
        )
        ass_id = sess["assessment_id"]
        final = AdaptiveAssessmentEngine.submit_turn(
            user_id=self.user_id,
            assessment_id=ass_id,
            turn_index=1,
            answer="Hash map lookup checks target minus current complement in single pass O(N) time and O(N) space.",
            idempotency_key=f"{ass_id}_t1",
            supabase_client=self.client,
        )
        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["completion_pct"], 100.0)
        # Single question out of 34 SDE skills must NOT display 100% curriculum coverage or high confidence!
        self.assertLess(final["coverage_pct"], 25.0)
        self.assertLessEqual(final["confidence"], 0.40)

    # 12. Adaptive difficulty adapts upward on strong answers and downward on weak answers
    def test_12_adaptive_difficulty_changes_with_performance(self):
        skill_up, diff_up = AdaptiveAssessmentEngine._select_next_skill_and_difficulty(
            assessment={"target_role": "ai_ml_engineer", "user_id": self.user_id},
            evaluated_items=[{"skill_id": "ml_model_evaluation", "domain": "Machine Learning", "difficulty": "Intermediate"}],
            last_score=88.0,
            last_difficulty="Intermediate",
            client=self.client,
        )
        self.assertEqual(diff_up, "Advanced")
        self.assertNotEqual(skill_up, "ml_model_evaluation")

        _skill_down, diff_down = AdaptiveAssessmentEngine._select_next_skill_and_difficulty(
            assessment={"target_role": "ai_ml_engineer", "user_id": self.user_id},
            evaluated_items=[{"skill_id": "dl_transformers", "domain": "Deep Learning", "difficulty": "Intermediate"}],
            last_score=22.0,
            last_difficulty="Intermediate",
            client=self.client,
        )
        self.assertEqual(diff_down, "Beginner")

    # 13. Full 10-question session has ZERO duplicate questions
    def test_13_full_10_question_assessment_zero_duplicates(self):
        sess = AdaptiveAssessmentEngine.start_session(
            user_id=self.user_id,
            target_role="Backend Developer",
            question_budget=10,
            supabase_client=self.client,
        )
        ass_id = sess["assessment_id"]
        questions = [sess["current_question"]]

        for turn in range(1, 10):
            res = AdaptiveAssessmentEngine.submit_turn(
                user_id=self.user_id,
                assessment_id=ass_id,
                turn_index=turn,
                answer="Idempotency prevents duplicate side effects using distributed locks, B-Tree indexes, and cache-aside TTLs.",
                idempotency_key=f"{ass_id}_t{turn}",
                supabase_client=self.client,
            )
            questions.append(res["next_question"])

        self.assertEqual(len(questions), 10)
        q_texts = [q["question_text"] for q in questions]
        q_hashes = {QuestionGenerator.compute_variation_hash(t) for t in q_texts}
        q_ids = {q["question_id"] for q in questions}
        self.assertEqual(len(q_hashes), 10, "All 10 questions in an assessment must be unique")
        self.assertEqual(len(q_ids), 10, "All 10 question IDs must be unique")

    # 14. AI Mentor general chat invokes safe_invoke_llm with valid signature and clean formatting
    def test_14_mentor_general_chat_formatting_and_llm_call(self):
        conv = MentorService.start_or_resume_conversation(self.user_id, supabase_client=self.client)
        with patch("services.mentor_service.safe_invoke_llm", return_value="### Core Invariant\n\n• **Time**: `O(1)` amortized.") as mock_llm:
            res = MentorService.send_mentor_message(
                user_id=self.user_id,
                conversation_id=conv["id"],
                user_message="How does consistent hashing reduce cache misses?",
                supabase_client=self.client,
            )
        mock_llm.assert_called_once()
        self.assertIn("Core Invariant", res["message"]["content"])
        self.assertNotIn("$p", res["message"]["content"])


if __name__ == "__main__":
    unittest.main()

