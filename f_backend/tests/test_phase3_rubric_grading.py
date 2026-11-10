"""
Phase 3 Verification Suite: Evidence-Based Rubric Grading & Prompt 1 Skill Mapping
Tests:
1. Strong vs Weak answer grading with verbatim quoted evidence verification
2. Rejection of fabricated quotes (substring check in code)
3. Critical skill double-grading & disagreement flag (> 0.25)
4. Gemini 503 failure -> status='failed' (normalized_score=None, NEVER 0) -> recovery on retry
5. Prompt 1 `skill_evidence` & `candidate_skill_states` sync (with dedupe_key idempotency)
6. Delivery dimensions: combined with speech metrics when present; 'Not evaluated' (None) when speech metrics NULL
7. Skipped / empty / off-topic turns -> status='skipped' (never scored as 0)
"""

import json
import os
import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

import jwt

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import app as app_module
from app import app, supabase
from local_supabase import SQLiteSupabaseMock
from services.interview_capture_service import persist_candidate_turn
from services.interview_rubric_grader import (
    compute_dimension_scores,
    grade_and_persist_turn,
    retry_failed_evaluations,
    verify_quote_in_answer,
)


def _make_mock_gemini(payload_dict):
    m = MagicMock()
    m.model = "gemini-2.5-flash"
    resp = MagicMock()
    resp.content = json.dumps(payload_dict)
    m.invoke.return_value = resp
    m.bind.return_value = m
    return m


class TestPhase3RubricGrading(unittest.TestCase):
    def setUp(self):
        self.db = SQLiteSupabaseMock(db_path=":memory:")
        self.user_id = f"u_p3_{uuid.uuid4().hex[:8]}"
        self.session_id = str(uuid.uuid4())
        self.db.table("sessions").insert({
            "session_id": self.session_id,
            "user_id": self.user_id,
            "role": "Senior Backend Engineer",
            "status": "in_progress",
            "active": True,
        }).execute()

    def test_01_strong_and_weak_answers_with_verified_quotes_and_skill_evidence(self):
        strong_answer = (
            "We implemented a sliding window log rate limiter using Redis sorted sets and Lua scripts "
            "for atomic check-and-increment, keeping p99 overhead under 2ms across 50k QPS while trading off higher memory per key."
        )
        t_strong, sm_strong = persist_candidate_turn(
            self.db,
            self.session_id,
            turn_index=1,
            text=strong_answer,
            question_text="Design a distributed rate limiter in Redis.",
            skill_id="sys_caching",
            input_mode="speech",
            stt_engine="web_speech_api",
            stt_confidence=0.95,
            audio_duration_s=10.0,
        )
        strong_mock = _make_mock_gemini({
            "criteria": [
                {"criterion": "technical_accuracy", "weight": 0.25, "score": 0.92, "quoted_justification": "sliding window log rate limiter using Redis sorted sets and Lua scripts"},
                {"criterion": "technical_depth", "weight": 0.20, "score": 0.90, "quoted_justification": "trading off higher memory per key"},
                {"criterion": "problem_solving", "weight": 0.20, "score": 0.88, "quoted_justification": "atomic check-and-increment"},
                {"criterion": "role_relevance", "weight": 0.15, "score": 0.90, "quoted_justification": "keeping p99 overhead under 2ms across 50k QPS"},
                {"criterion": "examples", "weight": 0.10, "score": 0.85, "quoted_justification": "under 2ms across 50k QPS"},
                {"criterion": "clarity", "weight": 0.10, "score": 0.90, "quoted_justification": "Redis sorted sets and Lua scripts"},
            ],
            "missing_concepts": ["Clock skew mitigation across nodes"],
            "technical_mistakes": [],
            "misconception_tags": [],
            "improved_answer": "Mention Redis Cluster slot pinning and NTP clock synchronization.",
        })

        ev_strong = grade_and_persist_turn(
            self.db, self.session_id, t_strong,
            "Design a distributed rate limiter in Redis.",
            chat_model=strong_mock, user_id=self.user_id, role="Backend Engineer", difficulty="Hard", is_critical=False,
        )
        self.assertEqual(ev_strong["status"], "ok")
        self.assertGreater(ev_strong["normalized_score"], 0.85)
        self.assertEqual(ev_strong["prompt_id"], "interview_rubric_grader")
        self.assertEqual(ev_strong["prompt_version"], "v1.0")

        # Weak answer
        weak_answer = "We can just store a counter in a single Python variable inside memory to count requests."
        t_weak, _ = persist_candidate_turn(
            self.db,
            self.session_id,
            turn_index=2,
            text=weak_answer,
            question_text="How do you scale counters across multiple API servers?",
            skill_id="sys_scalability",
            input_mode="speech",
            stt_engine="web_speech_api",
            stt_confidence=0.92,
            audio_duration_s=5.0,
        )
        weak_mock = _make_mock_gemini({
            "criteria": [
                {"criterion": "technical_accuracy", "weight": 0.25, "score": 0.25, "quoted_justification": "store a counter in a single Python variable inside memory"},
                {"criterion": "technical_depth", "weight": 0.20, "score": 0.20, "quoted_justification": "single Python variable inside memory"},
                {"criterion": "problem_solving", "weight": 0.20, "score": 0.30, "quoted_justification": "count requests"},
                {"criterion": "clarity", "weight": 0.10, "score": 0.60, "quoted_justification": "store a counter"},
            ],
            "missing_concepts": ["Shared distributed store", "Atomic increments", "Multi-worker synchronization"],
            "technical_mistakes": ["Process-local memory is not shared across distributed servers"],
            "misconception_tags": ["single_node_memory_assumption"],
            "improved_answer": "Use a centralized store like Redis INCR with TTL or partitioned token buckets.",
        })
        ev_weak = grade_and_persist_turn(
            self.db, self.session_id, t_weak,
            "How do you scale counters across multiple API servers?",
            chat_model=weak_mock, user_id=self.user_id, role="Backend Engineer", difficulty="Medium", is_critical=False,
        )
        self.assertEqual(ev_weak["status"], "ok")
        self.assertLess(ev_weak["normalized_score"], 0.35)
        self.assertIn("single_node_memory_assumption", ev_weak["misconception_tags"])

        # Verify skill_evidence & candidate_skill_states written for ONLY affected skills
        se_rows = self.db.table("skill_evidence").select("*").eq("user_id", self.user_id).execute().data
        self.assertEqual(len(se_rows), 2)
        self.assertTrue(all(r["source_type"] == "ai_interview" for r in se_rows))
        self.assertEqual({r["skill_id"] for r in se_rows}, {"sys_caching", "sys_scalability"})

        # Dedupe check: re-grading same turn MUST NOT insert duplicate skill_evidence
        grade_and_persist_turn(
            self.db, self.session_id, t_strong,
            "Design a distributed rate limiter in Redis.",
            chat_model=strong_mock, user_id=self.user_id, role="Backend Engineer", difficulty="Hard", is_critical=False,
        )
        se_after = self.db.table("skill_evidence").select("*").eq("user_id", self.user_id).execute().data
        self.assertEqual(len(se_after), 2)

        css_rows = self.db.table("candidate_skill_states").select("*").eq("user_id", self.user_id).execute().data
        self.assertEqual({r["skill_id"] for r in css_rows}, {"sys_caching", "sys_scalability"})

    def test_02_fabricated_quote_is_rejected(self):
        ans = "I use composite B-tree indexes on high-cardinality filter columns."
        self.assertTrue(verify_quote_in_answer("composite B-tree indexes", ans))
        self.assertFalse(verify_quote_in_answer("hash partitioning with Kafka streams", ans))

        t_row, _ = persist_candidate_turn(
            self.db, self.session_id, 1, text=ans, question_text="Explain SQL indexing.", skill_id="db_indexing"
        )
        # LLM fabricates quote that does not appear in answer
        fab_mock = _make_mock_gemini({
            "criteria": [
                {"criterion": "technical_accuracy", "weight": 0.5, "score": 0.95, "quoted_justification": "Candidate discussed hash partitioning and Kafka consumer lag cleanly"}
            ],
            "missing_concepts": [],
            "technical_mistakes": [],
            "misconception_tags": [],
            "improved_answer": "Good.",
        })

        ev = grade_and_persist_turn(
            self.db, self.session_id, t_row, "Explain SQL indexing.",
            chat_model=fab_mock, user_id=self.user_id, is_critical=False,
        )
        self.assertEqual(ev["status"], "failed")
        self.assertEqual(ev["error_code"], "QUOTE_VERIFICATION_FAILED")
        self.assertIsNone(ev["normalized_score"])
        self.assertEqual(fab_mock.invoke.call_count, 3)  # Retried 3 times rejecting fabricated quote

    def test_03_critical_skill_double_grading_and_disagreement_flag(self):
        ans = "Consistent hashing uses a hash ring with virtual nodes to minimize key movement."
        t_row, _ = persist_candidate_turn(
            self.db, self.session_id, 1, text=ans, question_text="Explain consistent hashing.", skill_id="sys_distributed_cap"
        )
        r1 = MagicMock(content=json.dumps({
            "criteria": [{"criterion": "technical_accuracy", "weight": 1.0, "score": 0.90, "quoted_justification": "hash ring with virtual nodes"}],
            "missing_concepts": [], "technical_mistakes": [], "misconception_tags": [], "improved_answer": "Good"
        }))
        r2 = MagicMock(content=json.dumps({
            "criteria": [{"criterion": "technical_accuracy", "weight": 1.0, "score": 0.50, "quoted_justification": "minimize key movement"}],
            "missing_concepts": ["Replication factor"], "technical_mistakes": [], "misconception_tags": [], "improved_answer": "Mention replication"
        }))
        m = MagicMock()
        m.model = "gemini-2.5-flash"
        m.bind.return_value = m
        m.invoke.side_effect = [r1, r2]

        ev = grade_and_persist_turn(
            self.db, self.session_id, t_row, "Explain consistent hashing.",
            chat_model=m, user_id=self.user_id, is_critical=True,
        )
        self.assertEqual(ev["status"], "ok")
        self.assertAlmostEqual(ev["normalized_score"], 0.70, places=3)  # avg(0.90, 0.50)
        self.assertTrue(ev["rubric_scores_json"]["double_graded"])
        self.assertTrue(ev["rubric_scores_json"]["disagreement_flagged"])  # 0.40 > 0.25

    @patch("time.sleep", return_value=None)
    def test_04_gemini_503_becomes_failed_not_zero_and_recovers_on_retry(self, mock_sleep):
        ans = "Connection pooling reuses open TCP sockets to avoid handshake overhead."
        t_row, _ = persist_candidate_turn(
            self.db, self.session_id, 1, text=ans, question_text="Why use connection pooling?", skill_id="db_pooling"
        )
        m_503 = MagicMock()
        m_503.model = "gemini-2.5-flash"
        m_503.bind.return_value = m_503
        m_503.invoke.side_effect = Exception("503 UNAVAILABLE: Backend timeout")

        ev_fail = grade_and_persist_turn(
            self.db, self.session_id, t_row, "Why use connection pooling?",
            chat_model=m_503, user_id=self.user_id, is_critical=False,
        )
        self.assertEqual(ev_fail["status"], "failed")
        self.assertEqual(ev_fail["error_code"], "GEMINI_503")
        self.assertIsNone(ev_fail["normalized_score"])  # NEVER 0

        # Recover on retry with working Gemini mock
        m_ok = _make_mock_gemini({
            "criteria": [
                {"criterion": "technical_accuracy", "weight": 1.0, "score": 0.88, "quoted_justification": "reuses open TCP sockets to avoid handshake overhead"}
            ],
            "missing_concepts": ["Max pool size tuning"],
            "technical_mistakes": [],
            "misconception_tags": [],
            "improved_answer": "Discuss PgBouncer transaction pooling.",
        })
        recovered = retry_failed_evaluations(self.db, self.session_id, chat_model=m_ok, user_id=self.user_id)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0]["status"], "ok")
        self.assertEqual(recovered[0]["normalized_score"], 0.88)

        # skill_evidence now written on recovery
        se = self.db.table("skill_evidence").select("*").eq("user_id", self.user_id).execute().data
        self.assertEqual(len(se), 1)
        self.assertEqual(se[0]["source_type"], "ai_interview")

    def test_05_delivery_dimensions_not_evaluated_when_speech_null(self):
        ev = {
            "turn_id": "t1",
            "status": "ok",
            "normalized_score": 0.85,
            "rubric_scores_json": {
                "criteria": [
                    {"criterion": "technical_accuracy", "weight": 0.5, "score": 0.90, "quoted_justification": "foo bar baz"},
                    {"criterion": "clarity", "weight": 0.5, "score": 0.85, "quoted_justification": "foo bar baz"},
                ]
            },
        }
        # Timing missing (wpm is None) -> delivery dimensions MUST be None / Not evaluated, NEVER 0
        dims_no_speech = compute_dimension_scores([ev], [{"turn_id": "t1", "wpm": None}])
        by_name = {d["name"]: d for d in dims_no_speech}
        self.assertEqual(by_name["Technical Accuracy"]["score"], 90.0)
        self.assertIsNone(by_name["Communication Clarity"]["score"])
        self.assertEqual(by_name["Communication Clarity"]["status"], "Not evaluated")
        self.assertIsNone(by_name["Confidence & Delivery"]["score"])
        self.assertIsNone(by_name["Conciseness"]["score"])

        # Timing present (wpm=135, 0 fillers) -> delivery dimensions scored cleanly
        dims_with_speech = compute_dimension_scores([ev], [{"turn_id": "t1", "wpm": 135.0, "word_count": 30, "filler_count": 0}])
        by_name_sp = {d["name"]: d for d in dims_with_speech}
        self.assertIsNotNone(by_name_sp["Communication Clarity"]["score"])
        self.assertGreater(by_name_sp["Communication Clarity"]["score"], 85.0)
        self.assertEqual(by_name_sp["Confidence & Delivery"]["score"], 100.0)

    def test_06_skipped_turn_never_scored_as_zero(self):
        t_skip, _ = persist_candidate_turn(self.db, self.session_id, 1, text="skip", question_text="Q?", input_mode="typed")
        ev = grade_and_persist_turn(self.db, self.session_id, t_skip, "Q?", chat_model=None, user_id=self.user_id)
        self.assertEqual(ev["status"], "skipped")
        self.assertIsNone(ev["normalized_score"])


if __name__ == "__main__":
    unittest.main()

