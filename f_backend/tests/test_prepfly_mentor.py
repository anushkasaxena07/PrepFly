"""
Comprehensive Unit Tests for PrepFly AI Mentor.
Tests:
1. Conversational Onboarding and 9-category JD breakdown.
2. 7-Step Dedicated Learning Workspace retrieval and taxonomy fallback.
3. Assignment submission, rubric evaluation, and verified evidence recording.
4. Persistent Contextual Mentor Chat with intent classification and prompt synthesis.
"""

import unittest
import json
import uuid

from local_supabase import get_supabase_client
from services.conversational_onboarding_service import ConversationalOnboardingService
from services.learning_service import LearningService
from services.mentor_service import (
    MentorService,
    INTENT_EXPLAIN_FROM_SCRATCH,
    INTENT_REAL_WORLD_EXAMPLE,
    INTENT_TIME_BUDGET_30MIN
)
from services.candidate_profile_service import CandidateProfileService
from services.skill_profiling_service import SkillProfilingService


class TestPrepFlyMentor(unittest.TestCase):
    def setUp(self):
        self.client = get_supabase_client()
        self.user_id = f"test_mentor_user_{uuid.uuid4().hex[:8]}"

    def test_01_conversational_onboarding_and_jd_parsing(self):
        """Validates that job descriptions are accurately extracted into 9 categories."""
        sample_jd = (
            "We are seeking an AI/ML Engineer to train deep learning models using PyTorch. "
            "Must have solid foundations in Data Structures and Algorithms, Linear Algebra, and Calculus. "
            "Experience building real-time recommendation systems with Kafka and vector databases is preferred. "
            "Requires 2+ years of production experience and strong cross-functional communication."
        )

        breakdown = ConversationalOnboardingService.parse_job_description(
            jd_text=sample_jd,
            target_role="AI/ML Engineer",
            target_company="OpenAI"
        )

        expected_categories = [
            "mandatory_technical", "preferred_qualifications", "programming_languages",
            "core_cs_fundamentals", "frameworks_and_tools", "role_specific_technologies",
            "system_design", "practical_experience", "behavioral_and_culture"
        ]
        for cat in expected_categories:
            self.assertIn(cat, breakdown, f"Missing category {cat}")
            self.assertIsInstance(breakdown[cat], list)

        # Test complete onboarding flow
        onboarding_payload = {
            "target_role": "AI/ML Engineer",
            "target_company": "DeepMind",
            "experience_level": "Senior",
            "candidate_years_experience": 3.0,
            "required_years_experience": 3.0,
            "target_date": "45 days",
            "daily_minutes": 90,
            "job_description": sample_jd
        }
        res = ConversationalOnboardingService.complete_onboarding(
            user_id=self.user_id,
            onboarding_data=onboarding_payload,
            supabase_client=self.client
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("diagnostic_assessment", res)
        self.assertIn("questions", res["diagnostic_assessment"])
        self.assertEqual(len(res["diagnostic_assessment"]["questions"]), 5)

    def test_02_seven_step_learning_workspace(self):
        """Validates that a 7-step learning workspace is generated with curated content."""
        activity_id = f"act_{uuid.uuid4().hex[:8]}"
        workspace = LearningService.get_learning_workspace(
            activity_id=activity_id,
            skill_id="ml_model_development",
            target_role="AI/ML Engineer",
            target_company="Google"
        )

        self.assertIn("why_this_matters", workspace)
        self.assertIn("learn", workspace)
        self.assertIn("practice", workspace)
        self.assertIn("assignment", workspace)

        learn = workspace["learn"]
        self.assertIn("simple_definition", learn)
        self.assertIn("technical_explanation", learn)
        self.assertIn("real_world_example", learn)
        self.assertIn("code_example", learn)

        practice = workspace["practice"]
        self.assertGreaterEqual(len(practice), 2)
        self.assertIn("hint", practice[0])
        self.assertIn("explanation", practice[0])

        assignment = workspace["assignment"]
        self.assertIn("prompt", assignment)
        self.assertIn("rubric", assignment)

    def test_03_assignment_submission_and_rubric_evaluation(self):
        """Validates that candidate solutions are evaluated against rubrics and verified evidence is recorded."""
        activity_id = f"act_{uuid.uuid4().hex[:8]}"
        # Ensure workspace exists in db
        workspace = LearningService.get_learning_workspace(
            activity_id=activity_id,
            skill_id="ml_model_development",
            target_role="AI/ML Engineer"
        )

        submission_text = (
            "We balance bias and variance using L1/L2 regularization. "
            "L1 adds the sum of absolute values which creates sparse zero weights (Lasso), "
            "while L2 adds squared weights (Ridge) which continuously shrinks coefficients. "
            "Complexity is O(N) over feature dimension D."
        )
        code_sub = (
            "import numpy as np\n"
            "def l2_loss(y_true, y_pred, weights, lmbda=0.01):\n"
            "    mse = np.mean((y_true - y_pred) ** 2)\n"
            "    reg = lmbda * np.sum(weights ** 2)\n"
            "    return mse + reg\n"
        )

        evaluation = LearningService.submit_and_evaluate_assignment(
            user_id=self.user_id,
            activity_id=activity_id,
            submission_text=submission_text,
            code_submission=code_sub,
            supabase_client=self.client
        )

        self.assertIn("score", evaluation)
        self.assertGreaterEqual(evaluation["score"], 50.0)
        self.assertIn("identified_strengths", evaluation)
        self.assertIn("actionable_feedback", evaluation)

        # Confirm evidence was recorded in skill profiling store
        proficiencies = SkillProfilingService.get_candidate_proficiencies(self.user_id, self.client)
        self.assertIn("ml_model_development", proficiencies)
        self.assertGreaterEqual(proficiencies["ml_model_development"], 50.0)

    def test_04_contextual_mentor_chat(self):
        """Validates persistent mentor chat, intent recognition, and contextual guidance synthesis."""
        conv = MentorService.start_or_resume_conversation(
            user_id=self.user_id,
            title="AI/ML System Design Coaching",
            supabase_client=self.client
        )
        self.assertIn("id", conv)
        conv_id = conv["id"]

        # Test intent detection
        self.assertEqual(
            MentorService.detect_intent("Can you explain how attention works from scratch?"),
            INTENT_EXPLAIN_FROM_SCRATCH
        )
        self.assertEqual(
            MentorService.detect_intent("Give me a real-world example of caching in production"),
            INTENT_REAL_WORLD_EXAMPLE
        )
        self.assertEqual(
            MentorService.detect_intent("I only have 30 mins today, what should I study?"),
            INTENT_TIME_BUDGET_30MIN
        )

        # Test sending message
        res = MentorService.send_mentor_message(
            user_id=self.user_id,
            conversation_id=conv_id,
            user_message="I only have 30 mins today. Prioritize my daily preparation.",
            supabase_client=self.client
        )
        self.assertIn("message", res)
        self.assertIn("suggested_pills", res)
        self.assertEqual(res["message"]["role"], "assistant")
        self.assertIn("Start 10m concept review", res["suggested_pills"])

        # Confirm messages persist in database
        messages = MentorService.get_conversation_messages(conv_id, supabase_client=self.client)
        self.assertGreaterEqual(len(messages), 3)  # Welcome + User + Assistant


if __name__ == "__main__":
    unittest.main()
