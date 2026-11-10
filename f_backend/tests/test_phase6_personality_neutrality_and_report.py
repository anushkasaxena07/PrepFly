"""
Tests for Phase 6: Scoring Integration and Report Consistency.
Verifies:
1. Personality Neutrality: Identical candidate answer evaluated across all 5 personalities yields identical rubric scores.
2. Non-Answer Turns (rapport, repeat, clarification, silence, hints) are NEVER scored.
3. Conversation summary section in report generation referencing turn IDs.
"""

import unittest
from unittest.mock import MagicMock
from services.evaluation_service import (
    EvaluationService,
    INTERVIEW_TYPE_SYSTEM_DESIGN,
    INTERVIEW_TYPE_TECHNICAL
)
from services.feedback_service import (
    evaluate_response_comprehensive,
    generate_end_of_interview_report,
    build_conversation_summary
)
from interviewer_config.personality_configs import (
    PERSONALITY_FRIENDLY,
    PERSONALITY_PROFESSIONAL,
    PERSONALITY_CHALLENGING,
    PERSONALITY_STRICT,
    PERSONALITY_SENIOR_STAFF,
    PERSONALITY_CONFIGS
)


class TestPhase6PersonalityNeutralityAndReport(unittest.TestCase):
    def setUp(self):
        self.mock_chat_model = MagicMock()
        # Mock structured LLM rubric response
        mock_response = MagicMock()
        mock_response.content = """
        {
          "accuracy_score": 85,
          "overall_score": 8.5,
          "classification": "Correct and complete",
          "criteria": [
            {"name": "Technical Correctness", "score": 36, "max_score": 40, "supporting_evidence": "Accurate token bucket mechanism"},
            {"name": "Conceptual Depth", "score": 26, "max_score": 30, "supporting_evidence": "Described Lua atomic scripts in Redis"},
            {"name": "Trade-offs & Edge Cases", "score": 15, "max_score": 20, "supporting_evidence": "Noted Redis failover fallback"},
            {"name": "Clarity & Structure", "score": 8, "max_score": 10, "supporting_evidence": "Concise structured articulation"}
          ],
          "correct_points": ["Token bucket in Redis", "Atomic Lua scripts"],
          "missing_concepts": ["Cross-region clock drift"],
          "misconceptions": [],
          "improvement_suggestions": ["Mention NTP clock drift compensation."],
          "evaluation_confidence": "high"
        }
        """
        self.mock_chat_model.invoke.return_value = mock_response

        self.candidate_answer = (
            "We implemented a distributed rate limiter using the Token Bucket algorithm in Redis. "
            "To guarantee atomicity across concurrent workers, we executed the token check and refill "
            "using Lua scripts on the Redis primary cluster, falling back to local memory if Redis was unavailable."
        )
        self.question = "How would you design a distributed rate limiter for high-traffic API gateways?"

    def test_personality_neutrality_across_all_5_personalities(self):
        """
        Operating Rule R3: The rubric score remains OBJECTIVE and identical
        across personalities for the exact same answer.
        """
        personalities = [
            PERSONALITY_FRIENDLY,
            PERSONALITY_PROFESSIONAL,
            PERSONALITY_CHALLENGING,
            PERSONALITY_STRICT,
            PERSONALITY_SENIOR_STAFF
        ]

        scores = []
        accuracy_scores = []
        criteria_scores = []

        for p_id in personalities:
            eval_res = EvaluationService.evaluate_response_with_rubric(
                interview_type=INTERVIEW_TYPE_SYSTEM_DESIGN,
                question=self.question,
                answer=self.candidate_answer,
                chat_model=self.mock_chat_model,
                role="Software Engineer",
                personality=p_id
            )

            scores.append(eval_res["overall_score"])
            accuracy_scores.append(eval_res["accuracy_score"])
            total_crit = sum(c["score"] for c in eval_res.get("criteria", []))
            criteria_scores.append(total_crit)

        # Assert all 5 evaluated personalities yielded exactly identical scores
        self.assertEqual(len(set(scores)), 1, f"Rubric overall scores differed across personalities: {scores}")
        self.assertEqual(len(set(accuracy_scores)), 1, f"Accuracy scores differed across personalities: {accuracy_scores}")
        self.assertEqual(len(set(criteria_scores)), 1, f"Criteria scores differed across personalities: {criteria_scores}")
        self.assertEqual(scores[0], 8.5)
        self.assertEqual(accuracy_scores[0], 85)

    def test_non_answer_turns_never_scored_in_evaluation_service(self):
        """Verify non-answer turns (rapport, repeat, clarification, hints, pause) return is_scored=False."""
        non_answers = [
            ("can you repeat the question please?", "repeat_question"),
            ("could you clarify what throughput scale is required?", "clarification_request"),
            ("can i get a hint on which data structure to use?", "hint_request"),
            ("how are you doing today ava?", "small_talk"),
            ("please give me a moment to think", "pause_request"),
            ("i'm a bit overwhelmed right now", "distress")
        ]

        for utterance, expected_intent in non_answers:
            res = EvaluationService.evaluate_response_with_rubric(
                interview_type=INTERVIEW_TYPE_TECHNICAL,
                question=self.question,
                answer=utterance,
                chat_model=self.mock_chat_model
            )
            self.assertFalse(res.get("is_scored", True), f"Utterance '{utterance}' was marked as scored!")
            self.assertIsNone(res.get("score"), f"Utterance '{utterance}' received a non-None score: {res.get('score')}")
            self.assertTrue(res.get("is_conversational_turn"), f"Utterance '{utterance}' not marked as conversational")

    def test_non_answer_turns_never_scored_in_feedback_service(self):
        """Verify evaluate_response_comprehensive returns is_scored=False and score=None for conversational turns."""
        res = evaluate_response_comprehensive(
            resume_text="Python engineer with 3 years experience",
            question="What is eventual consistency?",
            answer="Could you give me a small hint on how DynamoDB handles this?",
            chat_model=self.mock_chat_model,
            question_index=2
        )
        self.assertFalse(res.get("is_scored", True))
        self.assertIsNone(res.get("score"))
        self.assertIsNone(res.get("accuracy_score"))
        self.assertTrue(res.get("is_conversational_turn"))

    def test_conversation_summary_section_referencing_turn_ids(self):
        """Verify report generation produces structured conversation_summary with turn IDs."""
        questions = [
            "Hi, welcome! How are you doing today?",
            "Can you explain how distributed caching works in Redis?",
            "Can you give a hint?",
            "Walk me through your database sharding strategy."
        ]
        responses = [
            "I am doing great, excited to interview!",
            "Redis caches hot keys in memory with LRU eviction and asynchronous write-back to Postgres.",
            "Can you provide a small hint on sharding keys?",
            "We used consistent hashing based on tenant UUID to partition orders across 16 database shards."
        ]
        feedbacks = [
            {"score": None, "is_conversational_turn": True, "feedback": "Icebreaker rapport", "summary": "Rapport exchange"},
            {"score": 8.0, "accuracy_score": 80, "strength": "Good explanation of Redis LRU", "summary": "Clear caching answer"},
            {"score": None, "is_conversational_turn": True, "feedback": "Hint request", "summary": "Clarification"},
            {"score": 9.0, "accuracy_score": 90, "strength": "Consistent hashing UUID design", "summary": "Excellent sharding design"}
        ]

        summary = build_conversation_summary(questions, responses, feedbacks)

        self.assertEqual(summary["total_turns"], 4)
        self.assertEqual(summary["substantive_answers_count"], 2)
        self.assertEqual(summary["conversational_turns_count"], 2)

        turn_summaries = summary["turn_summaries"]
        self.assertEqual(len(turn_summaries), 4)

        # Turn 1: Conversational (icebreaker / rapport)
        self.assertEqual(turn_summaries[0]["turn_id"], "turn_1")
        self.assertEqual(turn_summaries[0]["turn_number"], 1)
        self.assertFalse(turn_summaries[0]["is_scored"])
        self.assertIsNone(turn_summaries[0]["score"])

        # Turn 2: Substantive technical
        self.assertEqual(turn_summaries[1]["turn_id"], "turn_2")
        self.assertEqual(turn_summaries[1]["turn_number"], 2)
        self.assertTrue(turn_summaries[1]["is_scored"])
        self.assertEqual(turn_summaries[1]["score"], 80)

        # Turn 3: Conversational (hint request)
        self.assertEqual(turn_summaries[2]["turn_id"], "turn_3")
        self.assertFalse(turn_summaries[2]["is_scored"])
        self.assertIsNone(turn_summaries[2]["score"])

        # Turn 4: Substantive technical
        self.assertEqual(turn_summaries[3]["turn_id"], "turn_4")
        self.assertTrue(turn_summaries[3]["is_scored"])
        self.assertEqual(turn_summaries[3]["score"], 90)

        # Chronological narrative must explicitly reference Turn IDs
        narrative = summary["chronological_narrative"]
        self.assertIn("Turn_1", narrative)
        self.assertIn("Turn_2", narrative)
        self.assertIn("Turn_3", narrative)
        self.assertIn("Turn_4", narrative)

    def test_full_report_enrichment_contains_conversation_summary(self):
        """Verify generate_end_of_interview_report includes conversation_summary in final report structure."""
        report = generate_end_of_interview_report(
            role="Software Engineer",
            track="system_design",
            difficulty="Senior",
            experience_level="5+ Years",
            questions=["Question 1", "Question 2"],
            responses=["Answer 1 for system design", "Answer 2 for sharding"],
            chat_model=self.mock_chat_model,
            feedbacks=[{"score": 8.0, "accuracy_score": 80}, {"score": 8.5, "accuracy_score": 85}]
        )

        self.assertIn("conversation_summary", report)
        conv_summary = report["conversation_summary"]
        self.assertEqual(conv_summary["total_turns"], 2)
        self.assertEqual(conv_summary["turn_summaries"][0]["turn_id"], "turn_1")
        self.assertEqual(conv_summary["turn_summaries"][1]["turn_id"], "turn_2")


if __name__ == "__main__":
    unittest.main()

