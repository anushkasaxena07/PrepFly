"""
Phase 2 Verification Suite: Interview Capture (The Source of Truth)
Tests:
1. Deterministic Python speech metrics (WPM, fillers, pauses, silence ratio)
2. Missing timing -> NULL with explicit missing_reason (NEVER 0)
3. Typed input -> speech metrics NULL / not_applicable
4. Edge cases: very short, "I don't know", explicit skip, off-topic, small talk,
   mic denied / STT failed, low STT confidence review gate before evaluation
5. Non-repeating question stem check for the same candidate
6. Scripted 6-turn interview (mix of spoken w/ timing, spoken w/o timing, typed, skipped, "I don't know", small talk)
   - Prints persisted `interview_turns` rows & `interview_speech_metrics` rows
   - Verifies `GET /interview/<session_id>/state` reload survives refresh with zero data loss
"""

import json
import os
import sys
import unittest
import uuid
from unittest.mock import patch

import jwt

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app, supabase
from local_supabase import SQLiteSupabaseMock
from services.interview_capture_service import (
    classify_turn_status,
    compute_data_sufficiency,
    get_persisted_interview_state,
    is_duplicate_question_stem,
)
from services.interview_speech_service import compute_speech_metrics


class TestPhase2InterviewCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.jwt_secret = os.getenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
        cls.user_id = f"user_{uuid.uuid4().hex[:8]}"
        cls.token = jwt.encode(
            {
                "sub": cls.user_id,
                "user_id": cls.user_id,
                "name": "Anushka Saxena",
                "email": "anushka.p2@prepfly.io",
                "role": "STUDENT",
            },
            cls.jwt_secret,
            algorithm="HS256",
        )

    def test_01_deterministic_speech_metrics_and_null_when_missing(self):
        # Spoken with duration + word timestamps (including a 1.5s pause)
        ts = [
            {"word": "I", "start": 0.0, "end": 0.2},
            {"word": "used", "start": 0.3, "end": 0.6},
            {"word": "um", "start": 0.7, "end": 0.9},
            {"word": "Redis", "start": 2.4, "end": 2.9},  # 1.5s pause before Redis
            {"word": "caching", "start": 3.0, "end": 3.5},
            {"word": "basically", "start": 3.6, "end": 4.1},
            {"word": "for", "start": 4.2, "end": 4.4},
            {"word": "speed", "start": 4.5, "end": 5.0},
        ]
        m = compute_speech_metrics(
            text="I used um Redis caching basically for speed",
            input_mode="speech",
            audio_duration_s=6.0,
            word_timestamps=ts,
        )
        self.assertEqual(m["word_count"], 8)
        self.assertEqual(m["wpm"], 80.0)  # 8 words / 0.1 min = 80.0
        self.assertEqual(m["filler_count"], 2)  # um, basically
        self.assertEqual(m["filler_map_json"], {"um": 1, "basically": 1})
        self.assertEqual(m["pause_count"], 1)
        self.assertEqual(m["longest_pause_s"], 1.5)
        self.assertEqual(m["pauses_status"], "measured")
        self.assertIsNotNone(m["silence_ratio"])

        # Missing timing -> NULL (None), NEVER 0
        m_no_time = compute_speech_metrics(
            text="I implemented consistent hashing across shards",
            input_mode="speech",
            audio_duration_s=None,
        )
        self.assertIsNone(m_no_time["wpm"])
        self.assertIsNone(m_no_time["speaking_time_s"])
        self.assertIsNone(m_no_time["pause_count"])
        self.assertEqual(m_no_time["missing_reason"], "timing_data_unavailable")

        # Typed input -> not applicable (NULL)
        m_typed = compute_speech_metrics(
            text="Consistent hashing reduces key movement during scaling",
            input_mode="typed",
        )
        self.assertIsNone(m_typed["wpm"])
        self.assertEqual(m_typed["missing_reason"], "typed_input_not_applicable")

    def test_02_edge_case_turn_status_classification(self):
        self.assertEqual(classify_turn_status("", input_mode="typed")[0], "empty")
        self.assertEqual(classify_turn_status("skip", input_mode="typed"), ("skipped", "explicit_skip"))
        self.assertEqual(classify_turn_status("I don't know", input_mode="speech", stt_confidence=0.9), ("skipped", "dont_know"))
        self.assertEqual(classify_turn_status("Yes caching", input_mode="typed"), ("answered", "very_short"))
        self.assertEqual(classify_turn_status("asdf", input_mode="typed")[0], "off_topic")
        self.assertEqual(classify_turn_status("How are you doing?", input_mode="speech", stt_confidence=0.95, is_small_talk_turn=True)[0], "small_talk")
        self.assertEqual(classify_turn_status("", input_mode="speech", edge_case="mic_permission_denied"), ("stt_failed", "mic_permission_denied"))
        self.assertEqual(classify_turn_status("unclear mumbling", input_mode="speech", stt_confidence=0.35, confirmed_edit=False), ("stt_low_confidence", "low_stt_confidence"))
        # Once candidate confirms or edits the transcript -> proceeds cleanly to answered
        self.assertEqual(classify_turn_status("I used binary search on the sorted array to achieve O(log n)", input_mode="speech", stt_confidence=0.35, confirmed_edit=True), ("answered", "substantive"))

    def test_03_low_stt_confidence_blocks_evaluation_until_confirmed(self):
        with patch("app.generate_dynamic_question", return_value=("Explain ACID properties in SQL databases.", "Technical", {})):
            s_res = self.client.post(
                "/start-interview",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"role": "Backend Engineer", "category": "Databases"},
            )
        self.assertEqual(s_res.status_code, 200)
        sid = s_res.get_json()["session_id"]

        # Send low-confidence speech transcript without confirmed_edit -> triggers review gate
        r_low = self.client.post(
            "/next",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": sid,
                "answer": "acid means something",
                "input_mode": "speech",
                "stt_engine": "web_speech_api",
                "stt_confidence": 0.30,
                "audio_duration_s": 3.0,
            },
        )
        self.assertEqual(r_low.status_code, 200)
        b_low = r_low.get_json()
        self.assertTrue(b_low.get("requires_review"))
        self.assertEqual(b_low.get("turn_status"), "stt_low_confidence")
        self.assertEqual(b_low.get("question_number"), 1)  # Did NOT advance

    def test_04_duplicate_stem_detection(self):
        db = SQLiteSupabaseMock(db_path=":memory:")
        uid = "cand_stem_1"
        db.table("sessions").insert({
            "session_id": str(uuid.uuid4()),
            "user_id": uid,
            "questions": json.dumps(["Explain how a hash map resolves collisions."]),
        }).execute()
        self.assertTrue(is_duplicate_question_stem(uid, "Explain how a Hash Map resolves collisions?", [], supabase_client=db))
        self.assertFalse(is_duplicate_question_stem(uid, "Design a distributed rate limiter.", [], supabase_client=db))

    @patch("app.evaluate_response_comprehensive", return_value={"score": 8.0, "accuracy_score": 80, "feedback": "Good structured explanation."})
    def test_05_scripted_6_turn_interview_persistence_and_reload(self, mock_eval):
        q_seq = iter([
            ("Explain how database indexes improve read queries and impact writes.", "Technical", False),
            ("How would you design a distributed rate limiter with Redis?", "System Design", False),
            ("What is the CAP theorem and how do you handle network partitions?", "System Design", False),
            ("Explain eventual consistency vs strong consistency.", "System Design", False),
            ("How does consistent hashing minimize key reshuffling?", "System Design", False),
            ("Describe a production incident you debugged end to end.", "Behavioral", False),
            ("Any closing questions for me?", "Wrap-up", False),
        ])

        with patch("app.generate_dynamic_question", side_effect=lambda *args, **kwargs: next(q_seq)):
            start_res = self.client.post(
                "/start-interview",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"role": "Senior Backend Engineer", "category": "System Design", "difficulty": "Medium"},
            )
            self.assertEqual(start_res.status_code, 200)
            sid = start_res.get_json()["session_id"]

            # Turn 0: Small talk greeting -> persisted as small_talk, does NOT advance Q1
            r_sm = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"session_id": sid, "answer": "Hi, I am doing well today!", "input_mode": "speech", "stt_engine": "web_speech_api", "stt_confidence": 0.95, "audio_duration_s": 2.0, "is_small_talk": True},
            )
            self.assertEqual(r_sm.status_code, 200)
            self.assertEqual(r_sm.get_json()["turn_status"], "small_talk")
            self.assertEqual(r_sm.get_json()["question_number"], 1)

            # Turn 1: Spoken answer WITH full timing + word timestamps
            r1 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "session_id": sid,
                    "answer": "Database indexes use B-tree structures so lookups run in logarithmic time, um while write operations pay an update overhead.",
                    "input_mode": "speech",
                    "stt_engine": "web_speech_api",
                    "stt_confidence": 0.94,
                    "audio_duration_s": 9.0,
                    "skill_id": "db_indexing",
                    "word_timestamps": [
                        {"word": "Database", "start": 0.0, "end": 0.5},
                        {"word": "indexes", "start": 0.6, "end": 1.1},
                        {"word": "use", "start": 2.5, "end": 2.8},  # 1.4s pause
                        {"word": "B-tree", "start": 2.9, "end": 3.5},
                    ],
                },
            )
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r1.get_json()["turn_status"], "answered")

            # Turn 2: Spoken answer WITHOUT timing data -> WPM must be NULL (None)
            r2 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "session_id": sid,
                    "answer": "We can implement token bucket rate limiting inside Redis using atomic Lua scripts.",
                    "input_mode": "speech",
                    "stt_engine": "web_speech_api",
                    "stt_confidence": 0.91,
                    "audio_duration_s": None,
                    "skill_id": "sys_rate_limiting",
                },
            )
            self.assertEqual(r2.status_code, 200)
            self.assertIsNone(r2.get_json()["speech_metrics"]["wpm"])
            self.assertEqual(r2.get_json()["speech_metrics"]["missing_reason"], "timing_data_unavailable")

            # Turn 3: Typed substantive answer -> speech metrics N/A (NULL)
            r3 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "session_id": sid,
                    "answer": "Under CAP theorem during a network partition, a distributed datastore must trade off availability against linearizability.",
                    "input_mode": "typed",
                    "skill_id": "sys_distributed_cap",
                },
            )
            self.assertEqual(r3.status_code, 200)
            self.assertEqual(r3.get_json()["speech_metrics"]["missing_reason"], "typed_input_not_applicable")

            # Turn 4: Explicit skip
            r4 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"session_id": sid, "answer": "skip", "input_mode": "typed", "skill_id": "sys_consistency"},
            )
            self.assertEqual(r4.status_code, 200)
            self.assertEqual(r4.get_json()["turn_status"], "skipped")

            # Turn 5: "I don't know"
            r5 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"session_id": sid, "answer": "I don't know", "input_mode": "speech", "stt_engine": "web_speech_api", "stt_confidence": 0.88, "audio_duration_s": 2.0, "skill_id": "sys_hashing"},
            )
            self.assertEqual(r5.status_code, 200)
            self.assertEqual(r5.get_json()["turn_status"], "skipped")

            # Turn 6: Typed substantive behavioral answer
            r6 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "session_id": sid,
                    "answer": "During a Redis connection pool exhaustion incident, I added exponential backoff, bounded connection limits, and circuit breaking to restore p99 latency.",
                    "input_mode": "typed",
                    "skill_id": "ops_incident_response",
                },
            )
            self.assertEqual(r6.status_code, 200)
            self.assertEqual(r6.get_json()["turn_status"], "answered")

        # Simulate page reload via GET /interview/<session_id>/state
        reload_res = self.client.get(
            f"/interview/{sid}/state",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(reload_res.status_code, 200)
        state = reload_res.get_json()

        turns = state["turns"]
        cand_turns = [t for t in turns if t["speaker"] == "candidate"]
        self.assertGreaterEqual(len(cand_turns), 7)  # 6 turns + 1 small_talk

        suff = state["data_sufficiency"]
        self.assertEqual(suff["answered_substantive_turns"], 4)  # Turns 1, 2, 3, 6
        self.assertEqual(suff["status_counts"]["skipped"], 2)  # Turns 4, 5
        self.assertEqual(suff["status_counts"]["small_talk"], 1)  # Turn 0
        self.assertEqual(suff["total_speaking_time_s"], 11.0)  # Turn 1 (9.0s) + Turn 5 (2.0s)
        self.assertIn("db_indexing", suff["skills_touched"])
        self.assertIn("sys_distributed_cap", suff["skills_touched"])


if __name__ == "__main__":
    unittest.main()

