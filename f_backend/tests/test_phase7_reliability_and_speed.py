"""
Phase 7 Verification Suite: Reliability, Speed, Cost, Backoff & Security Controls
"""

import json
import logging
import os
import sys
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch

import jwt

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import app as app_module
from app import app, supabase
from services.interview_capture_service import persist_candidate_turn, persist_interviewer_turn
from services.interview_reliability_service import (
    DailyTokenBudgetTracker,
    TokenBudgetExceededError,
    await_background_turn_evals,
    build_concise_resume_summary,
    get_degraded_error_payload,
    log_structured_event,
    sanitize_log_fields,
)
from services.interview_report_service import generate_and_persist_report
from services.interview_rubric_grader import (
    _grade_single_pass,
    evaluate_turns_parallel,
    grade_and_persist_turn,
)
from services.interview_scoring_config import (
    GEMINI_REQUEST_TIMEOUT_S,
    MAX_EVAL_CONCURRENCY,
    RESUME_SUMMARY_MAX_CHARS,
)


class _DummyResp:
    def __init__(self, content: str):
        self.content = content


def _make_fake_model(model_name="gemini-2.5-flash", delay_s=0.05, fail_503_count=0, hang_forever=False):
    state = {"calls": 0}

    class _FakeModel:
        model = model_name

        def bind(self, **kwargs):
            return self

        def invoke(self, messages):
            state["calls"] += 1
            if hang_forever:
                time.sleep(2.5)
            if state["calls"] <= fail_503_count:
                raise RuntimeError("503 UNAVAILABLE: Gemini transient overload")
            if delay_s > 0:
                time.sleep(delay_s)
            prompt_txt = messages[0].content
            # Extract actual candidate answer substring for quote verification
            marker = "Candidate Answer: "
            snippet = "B-tree indexes"
            if marker in prompt_txt:
                ans_part = prompt_txt.split(marker, 1)[1].split("\nCriteria:", 1)[0].strip()
                snippet = ans_part[:22]
            return _DummyResp(json.dumps({
                "criteria": [
                    {"criterion": "technical_accuracy", "weight": 0.25, "score": 0.85, "quoted_justification": snippet},
                    {"criterion": "technical_depth", "weight": 0.25, "score": 0.80, "quoted_justification": snippet},
                    {"criterion": "problem_solving", "weight": 0.25, "score": 0.82, "quoted_justification": snippet},
                    {"criterion": "clarity", "weight": 0.25, "score": 0.88, "quoted_justification": snippet},
                ],
                "missing_concepts": [],
                "technical_mistakes": [],
                "misconception_tags": [],
                "improved_answer": "Strong answer covering core internals.",
            }))

    m = _FakeModel()
    m._state = state
    return m


class TestPhase7ReliabilityAndSpeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.jwt_secret = os.getenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
        cls.user_id = f"u_p7_{uuid.uuid4().hex[:8]}"
        cls.token = jwt.encode(
            {"sub": cls.user_id, "user_id": cls.user_id, "name": "Anushka Saxena", "role": "STUDENT"},
            cls.jwt_secret,
            algorithm="HS256",
        )

    def tearDown(self):
        DailyTokenBudgetTracker.reset_for_tests(self.user_id)

    def _create_session(self):
        sid = str(uuid.uuid4())
        supabase.table("sessions").insert({
            "session_id": sid, "user_id": self.user_id, "role": "Backend Engineer",
            "level": "Senior", "mode": "resume", "status": "in_progress",
            "questions": ["Explain B-tree indexes."], "responses": [], "feedbacks": [],
            "question_index": 1, "total_questions": 6,
            "display_name": "Anushka Saxena", "display_name_source": "google",
            "active": True, "consent_given": 1,
        }).execute()
        return sid

    def test_01_token_budget_and_concise_resume_and_pii_scrubbing(self):
        # 1. Resume summary bounds prompt size even for large multi-page resumes
        huge_resume = "Experienced Python Distributed Systems Engineer " * 200
        compact = build_concise_resume_summary(huge_resume)
        self.assertLessEqual(len(compact), RESUME_SUMMARY_MAX_CHARS)

        # 2. Structured logs scrub PII & candidate answer text
        clean_fields = sanitize_log_fields({
            "session_id": "sess-123",
            "answer": "Secret salary or personal experience string",
            "resume_text": "Private PII phone 555-1234",
            "email": "private@example.com",
            "display_name": "Anushka Saxena",
            "latency_ms": 42.1,
        })
        self.assertEqual(clean_fields["answer"], "[REDACTED]")
        self.assertEqual(clean_fields["resume_text"], "[REDACTED]")
        self.assertEqual(clean_fields["email"], "[REDACTED]")
        self.assertEqual(clean_fields["display_name"], "[REDACTED]")
        self.assertEqual(clean_fields["latency_ms"], 42.1)

        # 3. Daily user token budget enforcement
        DailyTokenBudgetTracker.reset_for_tests(self.user_id)
        DailyTokenBudgetTracker.record_usage(self.user_id, prompt_chars=4000, output_chars=800)
        self.assertGreaterEqual(DailyTokenBudgetTracker.get_usage(self.user_id), 1200)
        with self.assertRaises(TokenBudgetExceededError):
            DailyTokenBudgetTracker.check_budget(self.user_id, estimated_tokens=500, limit=1300)

    def test_02_simulated_503_backoff_and_fallback_model_recorded(self):
        # Primary fails 503 all 3 attempts -> fallback succeeds and records '(fallback)'
        flaky_primary = _make_fake_model(model_name="gemini-2.5-flash", delay_s=0.0, fail_503_count=10)
        healthy_fallback = _make_fake_model(model_name="gemini-2.0-flash", delay_s=0.0, fail_503_count=0)
        ans = "B-tree indexes keep balanced height so lookups run in logarithmic time cleanly."

        with self.assertLogs("prepfly.interview.telemetry", level="WARNING") as captured:
            cleaned, norm, model_used = _grade_single_pass(
                question="Explain B-tree indexes.",
                answer=ans,
                role="Backend Engineer",
                skill_id="db_indexing",
                difficulty="Medium",
                chat_model=flaky_primary,
                max_attempts=3,
                user_id=self.user_id,
                fallback_model=healthy_fallback,
            )
        self.assertGreater(norm, 0.7)
        self.assertIn("fallback", model_used)
        joined_logs = "\n".join(captured.output)
        self.assertIn("rubric_grade_backoff_retry", joined_logs)
        self.assertIn("GEMINI_503", joined_logs)
        self.assertNotIn("B-tree indexes keep balanced height", joined_logs)

        degraded = get_degraded_error_payload("GEMINI_503", attempt=1, max_attempts=3)
        self.assertTrue(degraded["retryable"])
        self.assertIn("503", degraded["degraded_message"])

    def test_03_parallel_evaluation_faster_than_sequential_6_turn_benchmark(self):
        sid_seq = self._create_session()
        sid_par = self._create_session()
        ans = "Consistent hashing partitions keys across a hash ring minimizing key redistribution during node scaling."

        seq_turns = []
        par_turns = []
        for i in range(1, 7):
            t1, _ = persist_candidate_turn(supabase, sid_seq, i, text=ans, question_text=f"Q{i}?", skill_id=f"skill_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
            t2, _ = persist_candidate_turn(supabase, sid_par, i, text=ans, question_text=f"Q{i}?", skill_id=f"skill_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
            seq_turns.append(t1)
            par_turns.append(t2)

        model_seq = _make_fake_model(delay_s=0.15)
        t0 = time.perf_counter()
        seq_results = [
            grade_and_persist_turn(supabase, sid_seq, t, t["question_text"], model_seq, user_id=self.user_id, is_critical=False)
            for t in seq_turns
        ]
        seq_elapsed = time.perf_counter() - t0
        self.assertTrue(all(r["status"] == "ok" for r in seq_results))

        model_par = _make_fake_model(delay_s=0.15)
        t1 = time.perf_counter()
        par_results = evaluate_turns_parallel(supabase, sid_par, par_turns, model_par, user_id=self.user_id, max_concurrency=MAX_EVAL_CONCURRENCY)
        par_elapsed = time.perf_counter() - t1
        self.assertTrue(all(r["status"] == "ok" for r in par_results))

        # 6 turns * 0.15s sequentially (~0.90s+) vs parallel concurrency 4 (~0.30s)
        self.assertLess(par_elapsed, seq_elapsed * 0.65)

    def test_04_audit_log_on_report_and_requirements_and_pymupdf_and_health(self):
        sid = self._create_session()
        persist_candidate_turn(supabase, sid, 1, text="Kafka guarantees per-partition ordering cleanly.", question_text="Explain Kafka.", skill_id="sys_kafka", input_mode="typed")
        rep = generate_and_persist_report(supabase, sid, chat_model=None)
        self.assertEqual(rep["report_status"], "EVALUATION_FAILED")

        # Verify activity_logs recorded the audit entry with actor_id and without PII/answers
        logs_res = supabase.table("activity_logs").select("*").eq("entity_id", sid).execute()
        self.assertTrue(len(logs_res.data or []) >= 1)
        last_log = logs_res.data[-1]
        self.assertIn("interview_report", last_log["action"])
        self.assertNotIn("Kafka guarantees", json.dumps(last_log))

        # Verify health endpoint works cleanly
        h_res = self.client.get("/health")
        self.assertEqual(h_res.status_code, 200)

        # Verify requirements.txt includes redis & resume_service no longer imports bare fitz
        req_path = os.path.join(backend_dir, "requirements.txt")
        with open(req_path, "r", encoding="utf-8") as f:
            self.assertIn("redis", f.read().lower())

        rs_path = os.path.join(backend_dir, "services", "resume_service.py")
        with open(rs_path, "r", encoding="utf-8") as f:
            rs_src = f.read()
        self.assertNotIn("import fitz", rs_src)
        self.assertIn("import pymupdf", rs_src)

    def test_05_next_idempotency_key_prevents_duplicate_turns(self):
        sid = self._create_session()
        fake_eval = {"score": 8.0, "accuracy_score": 80, "feedback": "Good explanation."}
        fake_bg_model = _make_fake_model(delay_s=0.01)
        with patch.object(app_module, "chat_model", fake_bg_model), \
             patch("app.evaluate_response_comprehensive", return_value=fake_eval), \
             patch("app.generate_dynamic_question", return_value=("What about B+ trees?", "technical", False)):
            r1 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}", "X-Idempotency-Key": "idem-q1-click"},
                json={"session_id": sid, "answer": "B-trees store sorted keys in balanced multi-way nodes for O(log N) lookups.", "input_mode": "typed"},
            )
            self.assertEqual(r1.status_code, 200)
            await_background_turn_evals(sid, timeout_s=5.0)

            r2 = self.client.post(
                "/next",
                headers={"Authorization": f"Bearer {self.token}", "X-Idempotency-Key": "idem-q1-click"},
                json={"session_id": sid, "answer": "B-trees store sorted keys in balanced multi-way nodes for O(log N) lookups.", "input_mode": "typed"},
            )
            self.assertEqual(r2.status_code, 200)
            self.assertTrue(r2.get_json().get("idempotent_replay"))


if __name__ == "__main__":
    unittest.main()

