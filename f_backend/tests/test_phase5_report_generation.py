"""
Phase 5 Verification Suite: Evidence-Grounded Report Generation (No Templates)
Tests:
  (a) Complete EVALUATED interview report (real name, dimension grades, speech dashboard,
      cited strengths, severity-ranked weaknesses + recurring tags, narrative grounding, roadmap links, idempotence)
  (b) Interview with 1 substantive answer -> INCOMPLETE_INSUFFICIENT_DATA (no grade, no verdict)
  (c) Interview where Gemini failed -> EVALUATION_FAILED (no grade, no verdict, retry action)
  (d) Original bug reproduction (spoken answers present, evaluation empty, Google login) ->
      real name, real WPM, EVALUATION_FAILED, never F / Strong Reject / No Responses
  (e) Narrative number hallucination guard & HTTP email error surfacing
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
from services.interview_capture_service import persist_candidate_turn, persist_interviewer_turn
from services.interview_report_service import _validate_narrative_numbers, generate_and_persist_report
from services.interview_scoring_config import DIMENSION_CONFIG

ALL_CRITERIA = [c for cfg in DIMENSION_CONFIG.values() for c in cfg["criteria"]]


class TestPhase5ReportGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.jwt_secret = os.getenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
        cls.user_id = f"u_p5_{uuid.uuid4().hex[:8]}"
        cls.token = jwt.encode(
            {
                "sub": cls.user_id,
                "user_id": cls.user_id,
                "name": "Anushka Saxena",
                "email": "anushka.p5@prepfly.io",
                "role": "STUDENT",
            },
            cls.jwt_secret,
            algorithm="HS256",
        )

    def _create_session(self, role="Senior Backend Engineer"):
        sid = str(uuid.uuid4())
        supabase.table("sessions").insert({
            "session_id": sid,
            "user_id": self.user_id,
            "role": role,
            "level": "Senior",
            "mode": "resume",
            "status": "completed",
            "display_name": "Anushka Saxena",
            "display_name_source": "google",
            "active": False,
            "consent_given": 1,
        }).execute()
        return sid

    def test_01_complete_interview_report_grounded_no_templates_and_idempotent(self):
        sid = self._create_session()
        answers = [
            ("db_indexing", "B-tree indexes speed up lookups in O(log N) time while paying write overhead."),
            ("sys_caching", "Redis sorted sets with Lua scripts enforce rate limits atomically under 2ms."),
            ("sys_distributed_cap", "Network partitions require trading consistency vs availability cleanly."),
            ("sys_scalability", "A single Python dict in memory loses shared state across processes."),
            ("ops_incident_response", "We used Python dict in memory initially and hit cross-worker cache drift."),
        ]

        for idx, (sk, txt) in enumerate(answers, start=1):
            persist_interviewer_turn(supabase, sid, idx - 1, f"Question {idx}?", skill_id=sk)
            t_row, _ = persist_candidate_turn(
                supabase, sid, idx, text=txt, question_text=f"Question {idx}?", skill_id=sk,
                input_mode="speech", stt_engine="web_speech_api", stt_confidence=0.95, audio_duration_s=6.0,
            )
            # First 3 strong, turns 4 & 5 share recurring misconception 'single_node_memory_assumption'
            is_weak = idx >= 4
            sc = 0.35 if is_weak else 0.90
            crit_payload = [
                {"criterion": cname, "weight": 0.25, "score": sc, "quoted_justification": txt[:30]}
                for cname in ALL_CRITERIA
            ]
            supabase.table("interview_evaluations").upsert({
                "id": f"eval_{t_row['id']}",
                "turn_id": t_row["id"],
                "session_id": sid,
                "skill_id": sk,
                "rubric_scores_json": {"criteria": crit_payload},
                "raw_score": sc * 100,
                "normalized_score": sc,
                "missing_concepts_json": ["Distributed shared state"] if is_weak else [],
                "technical_mistakes_json": ["Single-process memory does not scale across workers"] if is_weak else [],
                "misconception_tags": ["single_node_memory_assumption"] if is_weak else [],
                "improved_answer": "Use distributed Redis state." if is_weak else "Strong response.",
                "status": "ok",
            }, on_conflict="id").execute()

        # Also add a small_talk turn that MUST be labelled and excluded from scoring
        persist_candidate_turn(
            supabase, sid, 901, text="Hi Ava doing great!", question_text="How are you?",
            is_small_talk_turn=True, input_mode="speech", stt_confidence=0.98, audio_duration_s=2.0
        )

        orig_cm = app_module.chat_model
        try:
            app_module.chat_model = None
            res = self.client.get(f"/interview/{sid}/report", headers={"Authorization": f"Bearer {self.token}"})
            self.assertEqual(res.status_code, 200)
            rep = res.get_json()

            self.assertEqual(rep["candidate_name"], "Anushka Saxena")
            self.assertEqual(rep["report_status"], "EVALUATED")
            self.assertIsNotNone(rep["grade"])
            self.assertIsNotNone(rep["recommendation"])
            self.assertEqual(len(rep["dimensions"]), 10)
            self.assertIsNotNone(rep["speech_metrics"]["wpm"])

            # Zero generic template text
            rep_str = json.dumps(rep)
            self.assertNotIn("Depth Gap", rep_str)
            self.assertNotIn("Review the core domain definitions", rep_str)
            self.assertNotIn("No tangible strengths", rep_str)

            # Recurring misconception flagged across turns 4 & 5
            self.assertEqual(len(rep["recurring_misconceptions"]), 1)
            self.assertEqual(rep["recurring_misconceptions"][0]["tag"], "single_node_memory_assumption")
            self.assertEqual(rep["recurring_misconceptions"][0]["count"], 2)

            # Strengths cite exact turn_id + verbatim quote
            self.assertTrue(len(rep["strengths"]) > 0)
            self.assertTrue(all("quote" in s and "turn_id" in s for s in rep["strengths"]))

            # Small talk turn flagged as excluded
            st_reviews = [q for q in rep["question_reviews"] if q["is_small_talk"]]
            self.assertEqual(len(st_reviews), 1)
            self.assertTrue(st_reviews[0]["excluded_from_scoring"])

            # Roadmap evidence links generated
            self.assertTrue(len(rep["roadmap_evidence_links"]) > 0)

            # Idempotent reload yields matching score/grade/status
            res2 = self.client.get(f"/interview/{sid}/report", headers={"Authorization": f"Bearer {self.token}"})
            self.assertEqual(res2.status_code, 200)
            rep2 = res2.get_json()
            self.assertEqual(rep["overall_score"], rep2["overall_score"])
            self.assertEqual(rep["grade"], rep2["grade"])
            self.assertEqual(rep["report_status"], rep2["report_status"])
        finally:
            app_module.chat_model = orig_cm

    def test_02_incomplete_1_substantive_answer_no_grade_no_verdict(self):
        sid = self._create_session()
        txt = "We partition Kafka topics by customer ID for ordered per-tenant processing."
        t_row, _ = persist_candidate_turn(supabase, sid, 1, text=txt, question_text="Explain Kafka partitioning.", skill_id="sys_kafka", input_mode="typed")
        supabase.table("interview_evaluations").upsert({
            "id": f"eval_{t_row['id']}",
            "turn_id": t_row["id"],
            "session_id": sid,
            "skill_id": "sys_kafka",
            "rubric_scores_json": {"criteria": [{"criterion": "technical_accuracy", "weight": 1.0, "score": 0.90, "quoted_justification": "partition Kafka topics"}]},
            "normalized_score": 0.90,
            "status": "ok",
        }, on_conflict="id").execute()

        rep = generate_and_persist_report(supabase, sid)
        self.assertEqual(rep["report_status"], "INCOMPLETE_INSUFFICIENT_DATA")
        self.assertIsNone(rep["grade"])
        self.assertIsNone(rep["recommendation"])
        self.assertEqual(rep["next_action"], "continue_interview")
        self.assertEqual(rep["speech_metrics"]["wpm_display"], "Not measurable")

    def test_03_evaluation_failed_no_grade_and_retry_action(self):
        sid = self._create_session()
        for i in range(1, 4):
            txt = f"Technical answer number {i} detailing distributed locking and consensus algorithms."
            t_row, _ = persist_candidate_turn(supabase, sid, i, text=txt, question_text=f"Q{i}?", skill_id="sys_consensus", input_mode="speech", stt_confidence=0.9, audio_duration_s=5.0)
            supabase.table("interview_evaluations").upsert({
                "id": f"eval_{t_row['id']}",
                "turn_id": t_row["id"],
                "session_id": sid,
                "skill_id": "sys_consensus",
                "status": "failed",
                "error_code": "GEMINI_503",
                "normalized_score": None,
            }, on_conflict="id").execute()

        rep = generate_and_persist_report(supabase, sid)
        self.assertEqual(rep["report_status"], "EVALUATION_FAILED")
        self.assertIsNone(rep["overall_score"])
        self.assertIsNone(rep["grade"])
        self.assertIsNone(rep["recommendation"])
        self.assertEqual(rep["next_action"], "retry_evaluation")

    def test_04_original_bug_reproduction_google_name_real_wpm_not_strong_reject(self):
        sid = self._create_session()
        for i in range(1, 5):
            txt = "I designed high-throughput microservices in Python and Flask backed by PostgreSQL read replicas."
            persist_candidate_turn(
                supabase, sid, i, text=txt, question_text=f"Q{i}?", skill_id="sys_architecture",
                input_mode="speech", stt_engine="web_speech_api", stt_confidence=0.95, audio_duration_s=5.5,
            )
        # No evaluations present (the production bug)
        orig_cm = app_module.chat_model
        try:
            app_module.chat_model = None
            res = self.client.get(f"/interview/{sid}/report", headers={"Authorization": f"Bearer {self.token}"})
            rep = res.get_json()
            self.assertEqual(rep["candidate_name"], "Anushka Saxena")
            self.assertNotEqual(rep["candidate_name"], "Candidate")
            self.assertEqual(rep["report_status"], "EVALUATION_FAILED")
            self.assertIsNone(rep["grade"])
            self.assertIsNone(rep["recommendation"])
            self.assertIsNotNone(rep["speech_metrics"]["wpm"])
            self.assertGreater(rep["speech_metrics"]["wpm"], 100.0)
            self.assertNotIn("No Responses", json.dumps(rep))
        finally:
            app_module.chat_model = orig_cm

    def test_05_narrative_number_validator_and_http_email_surface_failure(self):
        self.assertTrue(_validate_narrative_numbers("Candidate answered 5 turns with 88.0% overall.", {5.0, 88.0}))
        self.assertFalse(_validate_narrative_numbers("Candidate achieved 99.5% mastery.", {5.0, 88.0}))

        sid = self._create_session()
        with patch.dict(os.environ, {"RESEND_API_KEY": "", "SENDGRID_API_KEY": ""}):
            email_res = self.client.post(
                f"/interview/{sid}/email-report",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"email": "anushka.p5@prepfly.io"},
            )
            self.assertEqual(email_res.status_code, 502)
            self.assertFalse(email_res.get_json()["ok"])


if __name__ == "__main__":
    unittest.main()

