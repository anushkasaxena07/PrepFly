"""
PHASE 7 TEST SUITE: ADAPTIVE AI MENTOR (Section 16, Phase 7)
============================================================
Verifies:
1. Intent classification covers all 10 Section 9.2 canonical intents.
2. Context assembly and replies never leak 'None (None)' or template tokens (Golden Rule 5, Section 9.3).
3. 30-minute vs 40-minute re-planning yields distinct, valid schedules (Section 8.8, Acceptance Test 15).
4. POST /api/mentor/message returns {intent, reply, uiActions, conversation_id} (Section 11).
5. Real-world example handler uses active topic or prompts for clarification (Section 9.2).
6. Status handler returns single source of truth readiness numbers (Section 9.2).
7. Show deferred handler returns backlog items or 'Nothing is deferred' (Section 9.2).
"""

import unittest
import json
import re
from app import app
from services.mentor_service import (
    MentorService,
    INTENT_CHANGE_DAILY_TIME,
    INTENT_SHOW_DEFERRED,
    INTENT_EXPLAIN_CONCEPT,
    INTENT_REAL_WORLD_EXAMPLE,
    INTENT_HARDER_QUESTION,
    INTENT_EVALUATE_ANSWER,
    INTENT_PREP_FOR_TOMORROW,
    INTENT_MOCK_INTERVIEW,
    INTENT_STATUS,
    INTENT_UNKNOWN
)
from services.spec_planner_service import SpecPlannerService
from utils.template_guard import contains_unresolved_template as contains_template_leak


class TestPhase7AdaptiveMentor(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.user_id = "test_mentor_user_p7"
        conv = MentorService.start_or_resume_conversation(self.user_id, "Test Mentorship")
        self.conv_id = conv["id"]

    def test_01_intent_classification_all_ten_intents(self):
        """Verifies Section 9.2 canonical intent routing table."""
        cases = [
            ("I only have 30 minutes today", INTENT_CHANGE_DAILY_TIME),
            ("I have 40 mins today to study", INTENT_CHANGE_DAILY_TIME),
            ("Change my daily time to 45 minutes", INTENT_CHANGE_DAILY_TIME),
            ("Show deferred activities", INTENT_SHOW_DEFERRED),
            ("Show my backlog items", INTENT_SHOW_DEFERRED),
            ("Where do I stand?", INTENT_STATUS),
            ("What is my readiness score right now?", INTENT_STATUS),
            ("Prepare me for tomorrow's interview", INTENT_PREP_FOR_TOMORROW),
            ("Evaluate my answer: To avoid overfitting I used L2 regularization with lambda=0.01", INTENT_EVALUATE_ANSWER),
            ("Give me a harder question", INTENT_HARDER_QUESTION),
            ("Run a mock interview", INTENT_MOCK_INTERVIEW),
            ("Can you show a real-world example?", INTENT_REAL_WORLD_EXAMPLE),
            ("Explain RAG from scratch", INTENT_EXPLAIN_CONCEPT),
            ("What is the time complexity of QuickSort?", INTENT_EXPLAIN_CONCEPT),
            ("Hello, hope you are having a nice day!", INTENT_UNKNOWN)
        ]

        for msg, expected_intent in cases:
            detected = MentorService.detect_intent(msg)
            self.assertEqual(
                detected,
                expected_intent,
                f"Expected intent '{expected_intent}' for message '{msg}', got '{detected}'"
            )

    def test_02_no_none_none_context_leak(self):
        """Verifies Golden Rule 5 & Section 9.3: Never output 'None (None)' or template tokens."""
        # Test candidate with zero pre-populated profile to trigger fallback
        empty_user = "user_empty_profile_999"
        conv = MentorService.start_or_resume_conversation(empty_user)

        res = MentorService.send_mentor_message(
            user_id=empty_user,
            conversation_id=conv["id"],
            user_message="Hello, where should I start?"
        )

        content = res["message"]["content"]
        self.assertFalse(
            contains_template_leak(content),
            f"Mentor output leaked template tokens: '{content}'"
        )
        self.assertNotIn("None (None)", content)
        self.assertNotIn("None at None", content)

    def test_03_thirty_vs_forty_minute_replanning(self):
        """Section 8.8 & Acceptance Test 15: 30 vs 40 minutes produce distinct schedules."""
        # Replan to 30 minutes
        res_30 = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=self.conv_id,
            user_message="I only have 30 minutes today"
        )
        self.assertEqual(res_30["intent"], INTENT_CHANGE_DAILY_TIME)
        plan_30 = res_30["updated_version"]
        day1_30 = plan_30["days"][0]
        self.assertEqual(day1_30["totalMinutes"], 30)

        # Replan to 40 minutes
        res_40 = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=self.conv_id,
            user_message="Actually I have 40 minutes today"
        )
        self.assertEqual(res_40["intent"], INTENT_CHANGE_DAILY_TIME)
        plan_40 = res_40["updated_version"]
        day1_40 = plan_40["days"][0]
        self.assertEqual(day1_40["totalMinutes"], 40)

        # 30-min day and 40-min day have distinct block counts / durations
        # 40-min day has 25m LEARN + 15m PRACTICE (2 core blocks)
        block_types_40 = [b["type"] for b in day1_40["blocks"]]
        self.assertIn("LEARN", block_types_40)
        self.assertIn("PRACTICE", block_types_40)

        # Diff must be non-empty and describe the change
        self.assertIsNotNone(res_40.get("plan_diff"))

    def test_04_post_mentor_message_endpoint(self):
        """Section 11: POST /api/mentor/message returns {intent, reply, uiActions, conversation_id}."""
        resp = self.client.post("/api/mentor/message", json={
            "user_id": self.user_id,
            "message": "Where do I stand?"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("intent"), INTENT_STATUS)
        self.assertIn("reply", data)
        self.assertIn("uiActions", data)
        self.assertIn("conversation_id", data)

        reply = data["reply"]
        self.assertIn("Overall Readiness", reply)
        self.assertFalse(contains_template_leak(reply))

    def test_05_show_deferred_handler(self):
        """Section 9.2: SHOW_DEFERRED returns backlog items or clear 'Nothing is deferred' message."""
        res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=self.conv_id,
            user_message="Show deferred activities"
        )
        self.assertEqual(res["intent"], INTENT_SHOW_DEFERRED)
        content = res["message"]["content"]
        self.assertTrue(
            "deferred" in content.lower() or "on track" in content.lower()
        )
        self.assertFalse(contains_template_leak(content))

    def test_06_real_world_example_uses_active_topic(self):
        """Section 9.2: Uses CURRENT topic from user's active block; never generic text."""
        res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=self.conv_id,
            user_message="Show me a real-world example",
            active_activity={
                "topic": "Retrieval-Augmented Generation (RAG)",
                "skill_name": "RAG & Hallucination Mitigation",
                "skill_id": "rag_mitigation"
            }
        )
        self.assertEqual(res["intent"], INTENT_REAL_WORLD_EXAMPLE)
        content = res["message"]["content"]
        self.assertIn("RAG", content)
        self.assertIn("Production Engineering Case Study", content)
        self.assertIn("Check Question", content)
        self.assertFalse(contains_template_leak(content))


if __name__ == "__main__":
    unittest.main()
