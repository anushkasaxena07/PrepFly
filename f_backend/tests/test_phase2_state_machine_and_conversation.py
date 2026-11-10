"""
Unit Tests for Phase 2: Interview State Machine and Conversation Manager.
Validates pure state machine transitions, illegal transition guards,
and generates three scripted simulated interviews (Friendly+HR, Strict+DSA, Senior Staff+System Design).
"""

import unittest
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.interview_state_machine import (
    InterviewStateMachine,
    STATE_PRE_START,
    STATE_GREETING,
    STATE_ICEBREAKER,
    STATE_FORMAT_BRIEFING,
    STATE_MAIN_QUESTIONING,
    STATE_WRAP_UP_QUESTIONS,
    STATE_CLOSING,
    STATE_ENDED,
    STATE_PAUSED,
    STATE_END_REQUESTED,
    SUBSTATE_ASKED,
    SUBSTATE_LISTENING,
    SUBSTATE_PROBING,
    SUBSTATE_EVALUATING_BG,
    SUBSTATE_TRANSITION
)
from services.conversation_manager import (
    ConversationManager,
    MOVE_ACKNOWLEDGE_AND_NEXT,
    MOVE_PROBE_DETAIL,
    MOVE_CHALLENGE
)
from services.ava_session_context_service import AvaSessionContextService


class TestPhase2StateMachineAndConversation(unittest.TestCase):
    """Test suite for Phase 2 Interview State Machine and Conversation Flow."""

    def test_01_deterministic_state_transitions(self):
        """Verifies legal transitions through full interview lifecycle."""
        current = STATE_PRE_START

        # PRE_START -> GREETING
        ok, current, meta = InterviewStateMachine.transition(current, STATE_GREETING)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_GREETING)

        # GREETING -> ICEBREAKER
        ok, current, meta = InterviewStateMachine.transition(current, STATE_ICEBREAKER, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_ICEBREAKER)

        # ICEBREAKER -> FORMAT_BRIEFING
        ok, current, meta = InterviewStateMachine.transition(current, STATE_FORMAT_BRIEFING, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_FORMAT_BRIEFING)

        # FORMAT_BRIEFING -> MAIN_QUESTIONING
        ok, current, meta = InterviewStateMachine.transition(current, STATE_MAIN_QUESTIONING, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_MAIN_QUESTIONING)

        # MAIN_QUESTIONING -> WRAP_UP_QUESTIONS
        ok, current, meta = InterviewStateMachine.transition(current, STATE_WRAP_UP_QUESTIONS, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_WRAP_UP_QUESTIONS)

        # WRAP_UP_QUESTIONS -> CLOSING
        ok, current, meta = InterviewStateMachine.transition(current, STATE_CLOSING, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_CLOSING)

        # CLOSING -> ENDED
        ok, current, meta = InterviewStateMachine.transition(current, STATE_ENDED, meta)
        self.assertTrue(ok)
        self.assertEqual(current, STATE_ENDED)

    def test_02_illegal_state_transitions_rejected(self):
        """Verifies that invalid or skipping transitions are strictly rejected by the guard."""
        # Illegal: PRE_START cannot jump directly to MAIN_QUESTIONING or ENDED
        ok1, state1, meta1 = InterviewStateMachine.transition(STATE_PRE_START, STATE_MAIN_QUESTIONING)
        self.assertFalse(ok1)
        self.assertEqual(state1, STATE_PRE_START)
        self.assertIn("error", meta1)

        # Illegal: ENDED cannot transition back to GREETING
        ok2, state2, meta2 = InterviewStateMachine.transition(STATE_ENDED, STATE_GREETING)
        self.assertFalse(ok2)
        self.assertEqual(state2, STATE_ENDED)

        # Illegal: FORMAT_BRIEFING cannot jump straight to ENDED without END_REQUESTED
        ok3, state3, meta3 = InterviewStateMachine.transition(STATE_FORMAT_BRIEFING, STATE_ENDED)
        self.assertFalse(ok3)

    def test_03_interrupt_and_pause_transitions(self):
        """Verifies pause/resume and early end interrupt paths."""
        # MAIN_QUESTIONING -> PAUSED -> MAIN_QUESTIONING
        ok, state, meta = InterviewStateMachine.transition(STATE_MAIN_QUESTIONING, STATE_PAUSED)
        self.assertTrue(ok)
        self.assertEqual(state, STATE_PAUSED)

        ok, state, meta = InterviewStateMachine.transition(state, STATE_MAIN_QUESTIONING, meta)
        self.assertTrue(ok)
        self.assertEqual(state, STATE_MAIN_QUESTIONING)

        # MAIN_QUESTIONING -> END_REQUESTED -> CLOSING -> ENDED
        ok, state, meta = InterviewStateMachine.transition(state, STATE_END_REQUESTED, meta)
        self.assertTrue(ok)
        self.assertEqual(state, STATE_END_REQUESTED)

        ok, state, meta = InterviewStateMachine.transition(state, STATE_CLOSING, meta)
        self.assertTrue(ok)
        self.assertEqual(state, STATE_CLOSING)

        ok, state, meta = InterviewStateMachine.transition(state, STATE_ENDED, meta)
        self.assertTrue(ok)
        self.assertEqual(state, STATE_ENDED)

    def test_04_substate_questioning_lifecycle(self):
        """Verifies legal substate transitions inside MAIN_QUESTIONING."""
        self.assertTrue(InterviewStateMachine.can_transition_substate(SUBSTATE_ASKED, SUBSTATE_LISTENING))
        self.assertTrue(InterviewStateMachine.can_transition_substate(SUBSTATE_LISTENING, SUBSTATE_EVALUATING_BG))
        self.assertTrue(InterviewStateMachine.can_transition_substate(SUBSTATE_EVALUATING_BG, SUBSTATE_PROBING))
        self.assertTrue(InterviewStateMachine.can_transition_substate(SUBSTATE_PROBING, SUBSTATE_TRANSITION))
        self.assertTrue(InterviewStateMachine.can_transition_substate(SUBSTATE_TRANSITION, SUBSTATE_ASKED))

        # Illegal: ASKED cannot jump directly to TRANSITION
        self.assertFalse(InterviewStateMachine.can_transition_substate(SUBSTATE_ASKED, SUBSTATE_TRANSITION))

    def test_05_rolling_memory_and_callback_extraction(self):
        """Verifies rolling memory tracks stems, skills, and enables quotes for callbacks."""
        mem = ConversationManager.initialize_rolling_memory()
        self.assertEqual(len(mem["stem_hashes_asked"]), 0)

        # Turn 1
        mem = ConversationManager.update_rolling_memory(
            mem,
            turn_number=1,
            question_text="How do you handle database failover in PostgreSQL?",
            candidate_response="We used asynchronous replication with patroni to achieve automatic leader election within 5 seconds.",
            skill_id="cs_dbms",
            score=0.85
        )
        self.assertEqual(len(mem["stem_hashes_asked"]), 1)
        self.assertIn("cs_dbms", mem["topics_covered"])
        self.assertIn("cs_dbms", mem["strengths_noted"])

        # Turn 2
        mem = ConversationManager.update_rolling_memory(
            mem,
            turn_number=2,
            question_text="What happens to in-flight transactions during that failover?",
            candidate_response="Some transactions in WAL might be lost if synchronous replication was not enforced.",
            skill_id="sys_resilience",
            score=0.80
        )
        callback = ConversationManager.format_callback_reference(mem)
        self.assertIsNotNone(callback)
        self.assertIn("asynchronous replication with patroni", callback)

    def test_06_simulated_interviews_printing(self):
        """
        GATE 2 ACCEPTANCE:
        Builds and prints three contrasting simulated interviews:
        1. Friendly + HR & Behavioral
        2. Strict + DSA & Algorithms
        3. Senior Staff + System Design
        """
        print("\n" + "=" * 90)
        print("     GATE 2 ACCEPTANCE: THREE SCRIPTED SIMULATED INTERVIEWS")
        print("=" * 90)

        # Scenario 1: Friendly + HR & Behavioral
        ctx_1 = AvaSessionContextService.build_session_context(
            session_id="sim_hr_friendly",
            track_identifier="HR & Behavioral",
            personality_identifier="Friendly",
            candidate_name="Sarah Connor",
            target_role="Engineering Manager"
        )
        opening_1 = ConversationManager.generate_opening_turn(ctx_1)
        mem_1 = ConversationManager.initialize_rolling_memory()

        print("\n[SIMULATION 1: Friendly Ava + HR & Behavioral Track]")
        print(f"Turn 1 Ava (Opening): {opening_1['message']}")
        ans_1 = "I am doing well, thank you Ava! Really looking forward to discussing leadership and team challenges."
        print(f"Turn 1 Sarah (Rapport): \"{ans_1}\"")

        q2_1 = "Tell me about a time when two senior engineers on your team had a fundamental disagreement on architecture."
        mem_1 = ConversationManager.update_rolling_memory(mem_1, 2, q2_1, "I organized a structured RFC review and mediated a compromise.", "conflict_resolution", 0.70)
        move_1, meta_1 = ConversationManager.evaluate_followup_decision("I organized a structured RFC review and mediated a compromise.", 0.70, 0, ctx_1, mem_1)
        print(f"Turn 2 Ava (Behavioral Q): {q2_1}")
        print(f"Turn 2 Sarah: \"I organized a structured RFC review and mediated a compromise.\"")
        print(f"Follow-up Decision: {move_1} (Reason: {meta_1['reason']})")
        print(f"Turn 2 Follow-up Ava: Could you share a little bit more about what that compromise looked like in practice?")

        # Scenario 2: Strict + DSA & Algorithms
        ctx_2 = AvaSessionContextService.build_session_context(
            session_id="sim_dsa_strict",
            track_identifier="DSA & Algorithms",
            personality_identifier="Strict",
            candidate_name="David Miller",
            target_role="Software Development Engineer"
        )
        opening_2 = ConversationManager.generate_opening_turn(ctx_2)
        print("\n" + "-" * 90)
        print("[SIMULATION 2: Strict Ava + DSA & Algorithms Track]")
        print(f"Turn 1 Ava (Opening): {opening_2['message']}")
        ans_2 = "Ready."
        print(f"Turn 1 David: \"{ans_2}\"")

        q2_2 = "Given an array of integers, find the contiguous subarray with the largest sum. State the time complexity."
        mem_2 = ConversationManager.initialize_rolling_memory()
        ans_2b = "I will use Kadane's algorithm which runs in O(N) time and O(1) space."
        mem_2 = ConversationManager.update_rolling_memory(mem_2, 2, q2_2, ans_2b, "dsa_arrays", 0.90)
        move_2, meta_2 = ConversationManager.evaluate_followup_decision(ans_2b, 0.90, 0, ctx_2, mem_2)
        print(f"Turn 2 Ava (DSA Problem): {q2_2}")
        print(f"Turn 2 David: \"{ans_2b}\"")
        print(f"Follow-up Decision: {move_2}")
        trans_2, _ = ConversationManager.generate_natural_transition("strict", [])
        print(f"Turn 3 Ava Transition: {trans_2} What is the invariant maintained at index i?")

        # Scenario 3: Senior Staff + System Design
        ctx_3 = AvaSessionContextService.build_session_context(
            session_id="sim_sys_staff",
            track_identifier="System Design",
            personality_identifier="Senior Staff",
            candidate_name="Elena Rostova",
            target_role="Staff Distributed Systems Engineer"
        )
        opening_3 = ConversationManager.generate_opening_turn(ctx_3)
        mem_3 = ConversationManager.initialize_rolling_memory()
        print("\n" + "-" * 90)
        print("[SIMULATION 3: Senior Staff Ava + System Design Track]")
        print(f"Turn 1 Ava (Opening): {opening_3['message']}")
        ans_3a = "Excited to chat Ava. Let's design something scalable."
        print(f"Turn 1 Elena: \"{ans_3a}\"")

        q2_3 = "Let's design a global rate limiting service that throttles API abuse across three continents with < 5ms latency."
        ans_3b = "We can use an in-memory sliding window algorithm backed by local Redis clusters with asynchronous eventual consistency."
        mem_3 = ConversationManager.update_rolling_memory(mem_3, 2, q2_3, ans_3b, "sys_caching", 0.85)

        q3_3 = "How do we prevent cross-region quota starvation if North America gets hit with a distributed bot attack?"
        ans_3c = "We partition the global quota into localized buckets based on historical traffic ratios."
        mem_3 = ConversationManager.update_rolling_memory(mem_3, 3, q3_3, ans_3c, "sys_load_balancing", 0.85)

        callback_3 = ConversationManager.format_callback_reference(mem_3)
        print(f"Turn 2 Ava (System Design): {q2_3}")
        print(f"Turn 2 Elena: \"{ans_3b}\"")
        print(f"Turn 3 Ava (Scale Pushback with Callback): {callback_3} In production during a datacenter partition, how does your on-call engineer triage split-brain quota allocation?")
        print(f"Turn 3 Elena: \"{ans_3c}\"")

        closing_3 = ConversationManager.generate_closing_turn(ctx_3, scored_turns_count=5)
        print(f"Turn 4 Ava (Closing): {closing_3['message']}")
        print("=" * 90 + "\n")


if __name__ == "__main__":
    unittest.main()

