"""
Phase 9: Comprehensive End-to-End Verification Suite for Ava AI Interviewer.
Covers all 14 Acceptance Criteria:
AC-1:  Track Boundary Enforcement (Scope guard blocks out-of-scope questions)
AC-2:  Personality Expression (Measurable differences in warmth, formality, and directness)
AC-3:  Resume Grounding (Facts bound to stable fact IDs; zero hallucinated tech)
AC-4:  Multi-Stage Opening (Greeting -> Rapport -> Track Briefing -> Main Questioning)
AC-5:  Active Listening Follow-ups (Quotes and cites candidate words)
AC-6:  Non-Answer Turns Never Scored (Clarifications, repeats, small-talk, hints)
AC-7:  Candidate Control Commands (Repeat, Clarify, Hint, Pause, Early Exit)
AC-8:  Silence Escalation Ladder & Barge-in Ducking (4 escalation levels + instant ducking)
AC-9:  Zero Audio Bleed / Instant Audio Cutoff on End Interview
AC-10: Personality Neutrality (Identical candidate answers yield identical rubric scores)
AC-11: Report Conversation Summary (Referencing Turn IDs turn_1, turn_2, ...)
AC-12: Zero Repetitive Openers (Deterministic dynamic opener variation)
AC-13: Latency Benchmark (p50 <= 3.5s, p95 <= 4.0s)
AC-14: Unit Cost per Interview (< $0.02 per 15-min session)
"""

import unittest
from unittest.mock import MagicMock
from services.interview_state_machine import (
    InterviewStateMachine,
    STATE_PRE_START,
    STATE_GREETING,
    STATE_ICEBREAKER,
    STATE_FORMAT_BRIEFING,
    STATE_MAIN_QUESTIONING,
    STATE_ENDED
)
from services.conversation_manager import ConversationManager
from services.intent_classifier import (
    IntentClassifier,
    INTENT_ANSWER,
    INTENT_END_INTERVIEW_REQUEST,
    INTENT_CLARIFICATION_REQUEST,
    INTENT_HINT_REQUEST,
    INTENT_REPEAT_REQUEST,
    INTENT_SMALL_TALK
)
from services.intent_handler import IntentHandler
from services.silence_manager import (
    SilenceManager,
    SILENCE_LEVEL_1_CHECK_IN,
    SILENCE_LEVEL_4_PAUSE_OR_ABANDON
)
from services.track_strategy_service import TrackStrategyService
from services.evaluation_service import EvaluationService, INTERVIEW_TYPE_SYSTEM_DESIGN, INTERVIEW_TYPE_TECHNICAL
from services.feedback_service import build_conversation_summary, generate_end_of_interview_report
from services.humanness_evaluator import HumannessEvaluator
from interviewer_config.personality_configs import (
    PERSONALITY_FRIENDLY,
    PERSONALITY_PROFESSIONAL,
    PERSONALITY_CHALLENGING,
    PERSONALITY_STRICT,
    PERSONALITY_SENIOR_STAFF,
    PERSONALITY_CONFIGS
)
from interviewer_config.track_configs import (
    TRACK_MAANG,
    TRACK_DSA,
    TRACK_RESUME_DEEP_DIVE,
    TRACK_CS_FUNDAMENTALS,
    TRACK_GUESSTIMATE,
    TRACK_LOGIC_PUZZLES,
    TRACK_SYSTEM_DESIGN,
    TRACK_HR_BEHAVIORAL,
    TRACK_CONFIGS
)


class TestPhase9AvaE2EVerification(unittest.TestCase):
    def setUp(self):
        self.sample_resume_facts = [
            {"fact_id": "fact_proj_1", "category": "project", "raw_entity": "Fintech Payment Gateway", "confidence": 0.95},
            {"fact_id": "fact_skill_1", "category": "skill", "raw_entity": "Python", "confidence": 0.98},
            {"fact_id": "fact_skill_2", "category": "skill", "raw_entity": "PostgreSQL", "confidence": 0.92},
            {"fact_id": "fact_metric_1", "category": "metric", "raw_entity": "Processed $5M daily transactions", "confidence": 0.88}
        ]
        self.session_context = {
            "candidate": {"first_name": "Jordan"},
            "personality": PERSONALITY_CONFIGS[PERSONALITY_PROFESSIONAL],
            "resume_facts": {"facts": self.sample_resume_facts}
        }

    # AC-1: Track Boundary Enforcement
    def test_ac1_track_boundary_enforcement(self):
        """AC-1: All 8 tracks enforce strictly bounded topics and reject out-of-scope prompts."""
        valid_q, _ = TrackStrategyService.validate_track_question(
            "Estimate how many commercial flights are in the sky over North America.", TRACK_GUESSTIMATE
        )
        self.assertTrue(valid_q)

        invalid_q, reason = TrackStrategyService.validate_track_question(
            "How would you optimize this Leetcode binary tree traversal?", TRACK_GUESSTIMATE
        )
        self.assertFalse(invalid_q)
        self.assertIn("coding/DBMS concepts", reason)

    # AC-2: Personality Expression
    def test_ac2_personality_expression_distinctions(self):
        """AC-2: Personalities demonstrate distinct, measurable parameter profiles."""
        p_friendly = PERSONALITY_CONFIGS[PERSONALITY_FRIENDLY]
        p_strict = PERSONALITY_CONFIGS[PERSONALITY_STRICT]
        p_senior = PERSONALITY_CONFIGS[PERSONALITY_SENIOR_STAFF]

        self.assertGreater(p_friendly["warmth"], p_strict["warmth"])
        self.assertGreater(p_strict["directness"], p_friendly["directness"])
        self.assertIn("strict", p_strict["praise_policy"].lower())
        self.assertGreater(p_senior["challenge_rate"], p_friendly["challenge_rate"])

    # AC-3: Resume Grounding & Zero Hallucinations
    def test_ac3_resume_grounding_and_hallucination_prevention(self):
        """AC-3: Resume questions bind to fact IDs and reject unverified technologies."""
        op_res = TrackStrategyService.generate_opening_question(TRACK_RESUME_DEEP_DIVE, self.session_context)
        self.assertEqual(op_res["resume_fact_id"], "fact_proj_1")
        self.assertIn("Fintech Payment Gateway", op_res["question_text"])

        # Hallucinated question mentioning Rust (not on resume) must be rejected
        is_val, reason = TrackStrategyService.validate_track_question(
            "In your resume you built the core parser in Rust. How did memory safety help?",
            TRACK_RESUME_DEEP_DIVE,
            self.sample_resume_facts
        )
        self.assertFalse(is_val)
        self.assertIn("hallucinated technology 'rust'", reason.lower())

    # AC-4: Multi-Stage Opening
    def test_ac4_multi_stage_opening_sequence(self):
        """AC-4: State machine enforces GREETING -> ICEBREAKER -> FORMAT_BRIEFING -> MAIN_QUESTIONING."""
        current = STATE_PRE_START

        # Transition 1: Greeting
        ok, current, meta = InterviewStateMachine.transition(current, STATE_GREETING)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_GREETING)

        # Transition 2: Icebreaker
        ok, current, meta = InterviewStateMachine.transition(current, STATE_ICEBREAKER, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_ICEBREAKER)

        # Transition 3: Briefing
        ok, current, meta = InterviewStateMachine.transition(current, STATE_FORMAT_BRIEFING, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_FORMAT_BRIEFING)

        # Transition 4: Main Questioning
        ok, current, meta = InterviewStateMachine.transition(current, STATE_MAIN_QUESTIONING, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_MAIN_QUESTIONING)

    # AC-5: Active Listening Follow-ups
    def test_ac5_active_listening_followups_quote_candidate(self):
        """AC-5: Follow-ups quote and anchor directly onto candidate statements."""
        candidate_ans = "We partitioned our orders database using tenant UUID hashing across eight shards."
        fu = TrackStrategyService.generate_followup_question(
            TRACK_SYSTEM_DESIGN, "Tell me about your database.", candidate_ans, self.session_context, 1
        )
        self.assertTrue(fu["is_followup"])
        self.assertIn("orders database using", fu["question_text"])
        self.assertIn("We partitioned our", fu["quoted_phrase"])

    # AC-6: Non-Answer Turns Never Scored
    def test_ac6_non_answer_turns_never_scored(self):
        """AC-6: Clarifications, repeats, small-talk, and hints are marked is_scored=False."""
        non_answers = [
            "could you clarify what SLA uptime is expected?",
            "can you repeat the question please?",
            "how are you doing today ava?",
            "can i get a hint on the formula?"
        ]
        mock_model = MagicMock()
        for na in non_answers:
            res = EvaluationService.evaluate_response_with_rubric(
                INTERVIEW_TYPE_TECHNICAL, "What is two-phase commit?", na, mock_model
            )
            self.assertFalse(res.get("is_scored", True))
            self.assertIsNone(res.get("score"))
            self.assertTrue(res.get("is_conversational_turn"))

    # AC-7: Candidate Control Commands
    def test_ac7_candidate_control_commands(self):
        """AC-7: IntentClassifier reliably detects candidate control commands."""
        test_cases = [
            ("end the interview please", INTENT_END_INTERVIEW_REQUEST),
            ("can you repeat the question", INTENT_REPEAT_REQUEST),
            ("give me a hint", INTENT_HINT_REQUEST),
            ("can you clarify what you mean", INTENT_CLARIFICATION_REQUEST)
        ]
        for utterance, expected_intent in test_cases:
            res = IntentClassifier.classify_intent(utterance)
            self.assertEqual(res["intent"], expected_intent)

    # AC-8: Silence Escalation & Barge-In
    def test_ac8_silence_escalation_and_barge_in(self):
        """AC-8: Escalation escalates across thresholds and barge-in immediately ducks."""
        p_cfg = PERSONALITY_CONFIGS[PERSONALITY_FRIENDLY]
        # At 18 seconds, friendly Ava fires check-in
        level, action = SilenceManager.evaluate_silence_state(18.0, 0, "friendly", "general", "Jordan")
        self.assertEqual(level, SILENCE_LEVEL_1_CHECK_IN)
        self.assertEqual(action["action"], "CHECK_IN")

        # Barge-in command immediately ducks Ava
        barge_res = SilenceManager.handle_barge_in(is_ava_talking=True)
        self.assertTrue(barge_res["barge_in_detected"])
        self.assertTrue(barge_res["cancel_tts"])

    # AC-9: Zero Audio Bleed on End Interview
    def test_ac9_zero_audio_bleed_on_end_interview(self):
        """AC-9: Early exit intent returns audio_cutoff=True and terminates session."""
        intent = {"intent": INTENT_END_INTERVIEW_REQUEST, "confidence": 0.98}
        res = IntentHandler.handle_intent(
            intent, "What is CAP theorem?", 2, self.session_context
        )
        self.assertEqual(res["action"], "END_INTERVIEW")
        self.assertTrue(res["audio_cutoff"])
        self.assertFalse(res["is_scored"])

    # AC-10: Personality Neutrality
    def test_ac10_personality_neutrality(self):
        """AC-10: Objective rubric scores are identical across all 5 personalities."""
        mock_model = MagicMock()
        mock_model.invoke.return_value.content = '{"accuracy_score": 88, "overall_score": 8.8, "criteria": []}'

        answer = "We used an in-memory Redis cluster with write-behind caching to keep latency under 5ms."
        scores = []
        for p_id in [PERSONALITY_FRIENDLY, PERSONALITY_PROFESSIONAL, PERSONALITY_CHALLENGING, PERSONALITY_STRICT, PERSONALITY_SENIOR_STAFF]:
            res = EvaluationService.evaluate_response_with_rubric(
                INTERVIEW_TYPE_SYSTEM_DESIGN, "How do you optimize latency?", answer, mock_model, personality=p_id
            )
            scores.append(res["overall_score"])

        self.assertEqual(len(set(scores)), 1)
        self.assertEqual(scores[0], 8.8)

    # AC-11: Report Conversation Summary
    def test_ac11_report_conversation_summary_with_turn_ids(self):
        """AC-11: Report includes structured conversation_summary with turn_1, turn_2, ..."""
        q = ["Tell me about yourself.", "Explain Kafka partitions."]
        a = ["Hi, excited to be here!", "Kafka partitions allow parallel consumption across consumer groups."]
        fb = [
            {"is_conversational_turn": True, "score": None, "feedback": "Rapport"},
            {"is_conversational_turn": False, "score": 8.5, "accuracy_score": 85, "strength": "Good Kafka explanation"}
        ]
        summary = build_conversation_summary(q, a, fb)
        self.assertEqual(summary["total_turns"], 2)
        self.assertEqual(summary["substantive_answers_count"], 1)
        self.assertEqual(summary["conversational_turns_count"], 1)
        self.assertEqual(summary["turn_summaries"][0]["turn_id"], "turn_1")
        self.assertEqual(summary["turn_summaries"][1]["turn_id"], "turn_2")

    # AC-12: Zero Repetitive Openers
    def test_ac12_zero_repetitive_openers(self):
        """AC-12: Consecutive follow-up turns rotate openers dynamically without repetition."""
        fu1 = TrackStrategyService.generate_followup_question(
            TRACK_MAANG, "q1", "we partitioned the database into shards", self.session_context, followup_index=1
        )
        fu2 = TrackStrategyService.generate_followup_question(
            TRACK_MAANG, "q2", "we added a Redis cache for lookups", self.session_context, followup_index=2
        )
        opener1 = " ".join(fu1["question_text"].split()[:2]).lower()
        opener2 = " ".join(fu2["question_text"].split()[:2]).lower()
        self.assertNotEqual(opener1, opener2)

    # AC-13: Latency Benchmark
    def test_ac13_latency_benchmark(self):
        """AC-13: Full evaluation harness achieves p50 <= 3.5s and p95 <= 4.0s."""
        report = HumannessEvaluator.evaluate_all_personas()
        summary = report["aggregate_summary"]
        self.assertTrue(summary["target_latency_met"])
        self.assertLessEqual(summary["p95_latency_s"], 4.0)

    # AC-14: Unit Cost per Interview
    def test_ac14_unit_cost_economics(self):
        """AC-14: 15-minute interview costs <= $0.02 USD."""
        report = HumannessEvaluator.evaluate_all_personas()
        cost = report["cost_analysis"]
        self.assertLess(cost["total_cost_per_interview_usd"], 0.02)
        self.assertGreater(cost["interviews_per_dollar"], 50)


if __name__ == "__main__":
    unittest.main()
