"""
Tests for Phase 5: Track-Specific Question and Conversation Strategies.
Verifies all 8 interview tracks:
- Opening question generation and skill attribution
- Follow-up question generation quoting candidate response
- Strict scope guard rejection of out-of-scope questions across tracks
- Resume grounding guard rejection of hallucinated technologies
"""

import unittest
from services.track_strategy_service import TrackStrategyService
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


class TestPhase5TrackStrategies(unittest.TestCase):
    def setUp(self):
        self.sample_resume_facts = [
            {"fact_id": "fact_project_1", "category": "project", "raw_entity": "Fintech Payment Gateway", "confidence": 0.95},
            {"fact_id": "fact_skill_1", "category": "skill", "raw_entity": "Python", "confidence": 0.98},
            {"fact_id": "fact_skill_2", "category": "skill", "raw_entity": "Flask", "confidence": 0.90},
            {"fact_id": "fact_metric_1", "category": "metric", "raw_entity": "Processed $5M daily transactions", "confidence": 0.88}
        ]

        self.session_context = {
            "candidate": {"first_name": "Alex", "experience_level": "Mid-Level"},
            "personality": {"id": "professional", "name": "Professional"},
            "resume_facts": {"facts": self.sample_resume_facts}
        }

    def test_opening_questions_all_8_tracks(self):
        """Verify opening questions for all 8 tracks conform to track specifications."""
        all_tracks = [
            TRACK_MAANG, TRACK_DSA, TRACK_RESUME_DEEP_DIVE, TRACK_CS_FUNDAMENTALS,
            TRACK_GUESSTIMATE, TRACK_LOGIC_PUZZLES, TRACK_SYSTEM_DESIGN, TRACK_HR_BEHAVIORAL
        ]

        for tid in all_tracks:
            result = TrackStrategyService.generate_opening_question(tid, self.session_context)
            self.assertEqual(result["track_id"], tid)
            self.assertTrue(len(result["question_text"]) > 20)
            self.assertIsNotNone(result["skill_id"])
            self.assertEqual(result["stage"], "Track Main Questioning")

            # Check that generated opening question passes its own track validation
            is_valid, reason = TrackStrategyService.validate_track_question(
                result["question_text"], tid, self.sample_resume_facts
            )
            self.assertTrue(is_valid, f"Opening question for {tid} failed validation: {reason}")

    def test_resume_deep_dive_binds_to_verified_fact(self):
        """Verify Resume Deep-Dive opening question explicitly binds to a verified resume fact."""
        result = TrackStrategyService.generate_opening_question(TRACK_RESUME_DEEP_DIVE, self.session_context)
        self.assertEqual(result["resume_fact_id"], "fact_project_1")
        self.assertIn("Fintech Payment Gateway", result["question_text"])

    def test_followup_quotes_candidate_words_all_8_tracks(self):
        """Verify follow-up questions cite the candidate's words across all 8 tracks."""
        all_tracks = [
            TRACK_MAANG, TRACK_DSA, TRACK_RESUME_DEEP_DIVE, TRACK_CS_FUNDAMENTALS,
            TRACK_GUESSTIMATE, TRACK_LOGIC_PUZZLES, TRACK_SYSTEM_DESIGN, TRACK_HR_BEHAVIORAL
        ]

        candidate_answer = "we partitioned our PostgreSQL database into shards using a hash of the customer UUID"

        for tid in all_tracks:
            res = TrackStrategyService.generate_followup_question(
                track_id=tid,
                previous_question="Tell me about your architecture.",
                candidate_answer=candidate_answer,
                session_context=self.session_context,
                followup_index=1
            )
            self.assertEqual(res["track_id"], tid)
            self.assertTrue(res["is_followup"])
            self.assertIn("partitioned our PostgreSQL database", res["question_text"])
            self.assertIn("partitioned", res["quoted_phrase"])

    def test_scope_guard_rejects_out_of_scope_questions(self):
        """Test scope guard strictly rejects out-of-scope questions for individual tracks."""
        # 1. Guesstimate track rejects LeetCode / DBMS
        valid_g, _ = TrackStrategyService.validate_track_question(
            "Estimate the number of piano tuners in Chicago.", TRACK_GUESSTIMATE
        )
        self.assertTrue(valid_g)

        invalid_g, reason_g = TrackStrategyService.validate_track_question(
            "How would you optimize this Leetcode binary tree traversal?", TRACK_GUESSTIMATE
        )
        self.assertFalse(invalid_g)
        self.assertIn("coding/DBMS concepts", reason_g)

        # 2. Logic Puzzles rejects React / Behavioral
        valid_p, _ = TrackStrategyService.validate_track_question(
            "You have three light bulbs and three switches in another room.", TRACK_LOGIC_PUZZLES
        )
        self.assertTrue(valid_p)

        invalid_p, reason_p = TrackStrategyService.validate_track_question(
            "Tell me about a time you had conflict with your product manager.", TRACK_LOGIC_PUZZLES
        )
        self.assertFalse(invalid_p)
        self.assertIn("framework/behavioral", reason_p)

        # 3. CS Fundamentals rejects Behavioral STAR
        valid_cs, _ = TrackStrategyService.validate_track_question(
            "Explain virtual memory and paging in modern operating systems.", TRACK_CS_FUNDAMENTALS
        )
        self.assertTrue(valid_cs)

        invalid_cs, reason_cs = TrackStrategyService.validate_track_question(
            "Tell me about a time your project was late.", TRACK_CS_FUNDAMENTALS
        )
        self.assertFalse(invalid_cs)
        self.assertIn("behavioral STAR", reason_cs)

        # 4. Pure DSA rejects System Design Sharding / Kafka
        valid_dsa, _ = TrackStrategyService.validate_track_question(
            "Find the median of two sorted arrays in logarithmic time.", TRACK_DSA
        )
        self.assertTrue(valid_dsa)

        invalid_dsa, reason_dsa = TrackStrategyService.validate_track_question(
            "How would you set up a Kafka cluster with database sharding?", TRACK_DSA
        )
        self.assertFalse(invalid_dsa)
        self.assertIn("distributed systems", reason_dsa)

        # 5. HR & Behavioral rejects protected attributes
        valid_hr, _ = TrackStrategyService.validate_track_question(
            "Describe a situation where you had to adapt quickly to changing project priorities.", TRACK_HR_BEHAVIORAL
        )
        self.assertTrue(valid_hr)

        invalid_hr, reason_hr = TrackStrategyService.validate_track_question(
            "Are you married and what religion do you practice?", TRACK_HR_BEHAVIORAL
        )
        self.assertFalse(invalid_hr)
        self.assertIn("protected personal attributes", reason_hr)

    def test_resume_grounding_guard_rejects_hallucinations(self):
        """Verify Resume Grounding Guard rejects questions referring to unverified technologies."""
        # Candidate resume has Python, Flask, Fintech Payment Gateway
        # Question citing unverified "Kubernetes" or "Golang" must be rejected
        hallucinated_q = "In your resume you used Kubernetes and Golang for microservices orchestration. How did you handle ingress?"
        is_valid, reason = TrackStrategyService.validate_track_question(
            hallucinated_q,
            TRACK_RESUME_DEEP_DIVE,
            resume_facts=self.sample_resume_facts
        )
        self.assertFalse(is_valid)
        self.assertIn("hallucinated technology 'kubernetes'", reason.lower())

        # Question citing verified Python must pass
        grounded_q = "In your resume you built the payment gateway in Python. How did you structure your API services?"
        is_valid_g, reason_g = TrackStrategyService.validate_track_question(
            grounded_q,
            TRACK_RESUME_DEEP_DIVE,
            resume_facts=self.sample_resume_facts
        )
        self.assertTrue(is_valid_g, f"Grounded question failed: {reason_g}")


if __name__ == "__main__":
    unittest.main()

