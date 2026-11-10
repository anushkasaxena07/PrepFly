"""
Unit Tests for Phase 1: Interview Configuration Model (Tracks, Personalities, Session Context).
Validates track definitions, personality configs, resume grounding, and prompt integration.
"""

import unittest
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from interviewer_config.track_configs import (
    TRACK_CONFIGS,
    TRACK_MAANG,
    TRACK_DSA,
    TRACK_RESUME_DEEP_DIVE,
    TRACK_CS_FUNDAMENTALS,
    TRACK_GUESSTIMATE,
    TRACK_LOGIC_PUZZLES,
    TRACK_SYSTEM_DESIGN,
    TRACK_HR_BEHAVIORAL,
    resolve_track,
    validate_question_against_track
)
from interviewer_config.personality_configs import (
    PERSONALITY_CONFIGS,
    PERSONALITY_FRIENDLY,
    PERSONALITY_PROFESSIONAL,
    PERSONALITY_CHALLENGING,
    PERSONALITY_STRICT,
    PERSONALITY_SENIOR_STAFF,
    resolve_personality
)
from services.resume_grounding_service import ResumeGroundingService
from services.ava_session_context_service import AvaSessionContextService


class TestPhase1AvaInterviewConfig(unittest.TestCase):
    """Test suite for Phase 1 Interview Configuration Model."""

    def test_01_all_eight_tracks_defined_with_required_schema(self):
        """Verifies that all 8 tracks exist and conform to the full track schema."""
        expected_tracks = [
            TRACK_MAANG, TRACK_DSA, TRACK_RESUME_DEEP_DIVE, TRACK_CS_FUNDAMENTALS,
            TRACK_GUESSTIMATE, TRACK_LOGIC_PUZZLES, TRACK_SYSTEM_DESIGN, TRACK_HR_BEHAVIORAL
        ]
        self.assertEqual(len(TRACK_CONFIGS), 8)
        for t_id in expected_tracks:
            self.assertIn(t_id, TRACK_CONFIGS)
            cfg = TRACK_CONFIGS[t_id]
            self.assertEqual(cfg["track_id"], t_id)
            self.assertTrue(len(cfg["display_name"]) > 0)
            self.assertTrue(len(cfg["allowed_topics"]) > 0)
            self.assertTrue(len(cfg["forbidden_topics"]) > 0)
            self.assertTrue(len(cfg["question_types"]) > 0)
            self.assertIsInstance(cfg["default_question_count"], int)
            self.assertIsInstance(cfg["time_budget_minutes"], int)
            self.assertIsInstance(cfg["resume_weight"], float)
            self.assertTrue(len(cfg["opening_scope_sentence"]) > 20)

    def test_02_all_five_personalities_defined_with_measurable_parameters(self):
        """Verifies all 5 personalities define measurable tone, depth, and pacing parameters."""
        expected_personalities = [
            PERSONALITY_FRIENDLY, PERSONALITY_PROFESSIONAL, PERSONALITY_CHALLENGING,
            PERSONALITY_STRICT, PERSONALITY_SENIOR_STAFF
        ]
        self.assertEqual(len(PERSONALITY_CONFIGS), 5)
        for p_id in expected_personalities:
            self.assertIn(p_id, PERSONALITY_CONFIGS)
            p = PERSONALITY_CONFIGS[p_id]
            self.assertEqual(p["id"], p_id)
            self.assertTrue(0.0 <= p["warmth"] <= 1.0)
            self.assertTrue(0.0 <= p["formality"] <= 1.0)
            self.assertTrue(0.0 <= p["directness"] <= 1.0)
            self.assertIn(p["praise_policy"], ["frequent_supportive", "balanced_neutral", "minimal_critical", "none_strict", "peer_pragmatic"])
            self.assertTrue(p["followup_depth"] >= 1)
            self.assertTrue(0.0 <= p["challenge_rate"] <= 1.0)
            self.assertTrue(p["silence_patience_s"] > 0)
            self.assertTrue(p["pacing"] > 0)
            self.assertIn("greeting", p["sample_lines"])
            self.assertIn("acknowledging", p["sample_lines"])
            self.assertIn("probing", p["sample_lines"])
            self.assertIn("pushback", p["sample_lines"])
            self.assertIn("hinting", p["sample_lines"])
            self.assertIn("silence_nudge", p["sample_lines"])
            self.assertIn("closing", p["sample_lines"])
            self.assertTrue(len(p["sample_lines"]["greeting"]) >= 3)

    def test_03_track_and_personality_resolution_and_aliases(self):
        """Verifies robust resolution by slug, display name, and aliases."""
        self.assertEqual(resolve_track("MAANG")["track_id"], TRACK_MAANG)
        self.assertEqual(resolve_track("Guesstimate")["track_id"], TRACK_GUESSTIMATE)
        self.assertEqual(resolve_track("System Design")["track_id"], TRACK_SYSTEM_DESIGN)
        self.assertEqual(resolve_track("dsa & algorithms")["track_id"], TRACK_DSA)

        self.assertEqual(resolve_personality("Friendly")["id"], PERSONALITY_FRIENDLY)
        self.assertEqual(resolve_personality("Staff")["id"], PERSONALITY_SENIOR_STAFF)
        self.assertEqual(resolve_personality("strict")["id"], PERSONALITY_STRICT)

    def test_04_resume_grounding_fact_sheet_extraction(self):
        """Verifies structured resume fact sheet generation with stable fact IDs and confidence."""
        sample_resume = """
        John Doe - Senior Backend Engineer
        Skills: Python, FastAPI, Docker, PostgreSQL, Redis, Kubernetes
        Experience:
        Senior Software Engineer at Fintech Corp
        - Architected Realtime Payments Engine handling 25,000 transactions per second.
        - Reduced API p99 latency from 180ms to 24ms by introducing Redis caching.
        Projects:
        - Developed Distributed Task Orchestrator in Python using Celery and Redis.
        """
        fact_sheet = ResumeGroundingService.extract_fact_sheet(sample_resume, "John Doe")
        self.assertEqual(fact_sheet["version"], "v1.0")
        self.assertTrue(fact_sheet["has_resume"])
        self.assertTrue(fact_sheet["fact_count"] >= 5)

        facts = fact_sheet["facts"]
        fact_ids = [f["fact_id"] for f in facts]
        # IDs must be stable and prefixed by category
        self.assertTrue(any(fid.startswith("fact_project_") for fid in fact_ids))
        self.assertTrue(any(fid.startswith("fact_metric_") for fid in fact_ids))
        self.assertTrue(any(fid.startswith("fact_skill_") for fid in fact_ids))

        # Check metric fact
        metric_fact = next(f for f in facts if f["category"] == "metric")
        self.assertTrue("reduced" in metric_fact["claim_text"].lower() or "latency" in metric_fact["claim_text"].lower())
        self.assertTrue(metric_fact["confidence"] >= 0.8)

    def test_05_session_context_and_prompt_directives_integration(self):
        """Verifies that session context object binds track, personality, and resume facts into prompt directives."""
        resume = "Software Engineer with 3 years experience in Python, AWS, and PostgreSQL. Built Search Indexer."

        # Candidate A: Guesstimate Track + Friendly Personality
        ctx_a = AvaSessionContextService.build_session_context(
            session_id="sess_candidate_a",
            track_identifier="Guesstimate",
            personality_identifier="Friendly",
            candidate_name="Alice Smith",
            resume_text=resume
        )
        self.assertEqual(ctx_a["track"]["track_id"], TRACK_GUESSTIMATE)
        self.assertEqual(ctx_a["personality"]["id"], PERSONALITY_FRIENDLY)
        self.assertEqual(ctx_a["candidate"]["first_name"], "Alice")

        directives_a = AvaSessionContextService.generate_prompt_directives(ctx_a)
        self.assertIn("Guesstimate & Market Sizing", directives_a)
        self.assertIn("Friendly Ava", directives_a)
        self.assertIn("Alice", directives_a)
        self.assertIn("WARMTH: 0.95", directives_a)
        self.assertIn("FORBIDDEN TOPICS", directives_a)

        # Candidate B: DSA Track + Strict Personality
        ctx_b = AvaSessionContextService.build_session_context(
            session_id="sess_candidate_b",
            track_identifier="DSA & Algorithms",
            personality_identifier="Strict",
            candidate_name="Bob Jones",
            resume_text=resume
        )
        self.assertEqual(ctx_b["track"]["track_id"], TRACK_DSA)
        self.assertEqual(ctx_b["personality"]["id"], PERSONALITY_STRICT)
        self.assertEqual(ctx_b["candidate"]["first_name"], "Bob")

        directives_b = AvaSessionContextService.generate_prompt_directives(ctx_b)
        self.assertIn("DSA & Algorithms", directives_b)
        self.assertIn("Strict Ava", directives_b)
        self.assertIn("Bob", directives_b)
        self.assertIn("WARMTH: 0.15", directives_b)
        self.assertIn("DIRECTNESS: 0.98", directives_b)

    def test_06_scope_guard_catches_out_of_track_questions(self):
        """Verifies that validate_question_against_track rejects off-track questions."""
        guesstimate_track = TRACK_CONFIGS[TRACK_GUESSTIMATE]
        # In Guesstimate, asking about binary trees or SQL ACID must be rejected
        is_valid_1, reason_1 = validate_question_against_track(
            "Write a Python function to invert a binary tree in O(N) time.",
            guesstimate_track
        )
        self.assertFalse(is_valid_1)
        self.assertIn("Guesstimate", reason_1)

        # In DSA, asking about kafka or microservices must be rejected
        dsa_track = TRACK_CONFIGS[TRACK_DSA]
        is_valid_2, reason_2 = validate_question_against_track(
            "How would you configure a Kafka cluster for cross-datacenter replication?",
            dsa_track
        )
        self.assertFalse(is_valid_2)
        self.assertIn("DSA", reason_2)

        # Valid question passes
        is_valid_3, reason_3 = validate_question_against_track(
            "How would you estimate the daily consumption of coffee in New York City?",
            guesstimate_track
        )
        self.assertTrue(is_valid_3)
        self.assertIsNone(reason_3)


if __name__ == "__main__":
    unittest.main()

