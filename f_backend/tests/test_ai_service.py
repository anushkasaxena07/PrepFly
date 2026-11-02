import unittest
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_service import (
    get_current_stage,
    generate_dynamic_question,
    generate_hint,
    STAGES,
    PHASE_1_GREETINGS
)

class TestAiService(unittest.TestCase):
    """Unit tests for AI Recruiter conversation stages, voice commands, and question progression."""

    def test_get_current_stage_progression(self):
        """Test question index mapping to human-like interview phases."""
        self.assertIn("Phase 1", get_current_stage(1))
        self.assertIn("Phase 2", get_current_stage(2))
        self.assertIn("Phase 3", get_current_stage(3))
        self.assertIn("Phase 4", get_current_stage(4))
        self.assertIn("Phase 5", get_current_stage(5))
        self.assertIn("Wrap-up", get_current_stage(6))
        self.assertIn("Wrap-up", get_current_stage(10))

    def test_repeat_voice_command(self):
        """Candidate saying 'repeat' or 'pardon' should return previous question without invoking LLM."""
        prev_q = "Explain how you handle race conditions in database transactions."
        for phrase in ["repeat", "can you repeat the question", "pardon"]:
            with self.subTest(phrase=phrase):
                question, stage, is_deep_dive = generate_dynamic_question(
                    resume_text="Senior backend developer",
                    previous_questions=[prev_q],
                    question_index=2,
                    last_answer=phrase
                )
                self.assertEqual(question, prev_q)
                self.assertEqual(stage, "Repeat")
                self.assertFalse(is_deep_dive)

    def test_generate_dynamic_question_phase_1_deterministic(self):
        """Phase 1 greeting should return a friendly Ava recruiter greeting without needing LLM."""
        question, stage, is_deep_dive = generate_dynamic_question(
            resume_text="Fresh graduate",
            previous_questions=[],
            question_index=1,
            candidate_name="Alex"
        )
        self.assertTrue(any(g in question for g in ["Ava", "Hey", "Hi"]))
        self.assertIn("Phase 1", stage)
        self.assertFalse(is_deep_dive)

    def test_generate_hint_fallback(self):
        """When LLM is unavailable, generate_hint must return a constructive fallback hint."""
        hint = generate_hint(
            "How would you design a distributed cache?",
            "Senior backend engineer profile",
            None
        )
        self.assertIsInstance(hint, str)
        self.assertGreater(len(hint), 15)

if __name__ == "__main__":
    unittest.main()
