"""
Phase 8 End-to-End Verification Suite (All 14 Required Acceptance Scenarios, Fixtures Only)
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

import app as app_module
from app import app, supabase
from services.interview_capture_service import persist_candidate_turn, persist_interviewer_turn
from services.interview_scoring_config import DIMENSION_CONFIG, WEAKNESS_THRESHOLD

ALL_CRIT = [c for cfg in DIMENSION_CONFIG.values() for c in cfg["criteria"]]


class _DummyResp:
    def __init__(self, content: str):
        self.content = content


def _make_quality_model(score_map=None, fail_503=False):
    """Deterministic fake Gemini rubric grader echoing exact answer substrings."""
    score_map = score_map or {}

    class _M:
        model = "gemini-2.5-flash"

        def bind(self, **kwargs):
            return self

        def invoke(self, messages):
            if fail_503:
                raise RuntimeError("503 UNAVAILABLE: simulated outage")
            prompt_txt = messages[0].content
            ans = ""
            if "Candidate Answer: " in prompt_txt:
                ans = prompt_txt.split("Candidate Answer: ", 1)[1].split("\nCriteria:", 1)[0].strip()
            q = ans[:24] if len(ans) >= 8 else ans
            sc = 0.88
            for k, v in score_map.items():
                if k.lower() in ans.lower():
                    sc = v
                    break
            return _DummyResp(json.dumps({
                "criteria": [
                    {"criterion": c, "weight": 0.2, "score": sc, "quoted_justification": q}
                    for c in ALL_CRIT
                ],
                "missing_concepts": ["Replication lag handling"] if sc < WEAKNESS_THRESHOLD else [],
                "technical_mistakes": ["Unsynchronized shared state"] if sc < WEAKNESS_THRESHOLD else [],
                "misconception_tags": ["state_isolation_gap"] if sc < WEAKNESS_THRESHOLD else [],
                "improved_answer": "Elaborate on trade-offs, invariants, and failure recovery.",
            }))

    return _M()


class TestPhase8InterviewE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.jwt_secret = os.getenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")

    def _new_user(self, name="Anushka Saxena", email=None):
        uid = f"u_p8_{uuid.uuid4().hex[:8]}"
        tok = jwt.encode(
            {"sub": uid, "user_id": uid, "name": name, "email": email or f"{uid}@prepfly.io", "role": "STUDENT"},
            self.jwt_secret,
            algorithm="HS256",
        )
        return uid, tok

    def _headers(self, tok, extra=None):
        h = {"Authorization": f"Bearer {tok}"}
        if extra:
            h.update(extra)
        return h

    def _create_session(self, uid, tok, role="Senior Backend Engineer", name="Anushka Saxena", source="google", total_questions=6, status="completed"):
        sid = str(uuid.uuid4())
        supabase.table("sessions").insert({
            "session_id": sid, "user_id": uid, "role": role,
            "level": "Senior", "mode": "resume", "status": status,
            "questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "responses": [], "feedbacks": [],
            "question_index": 1, "total_questions": total_questions,
            "display_name": name, "display_name_source": source,
            "active": status == "in_progress", "consent_given": 1,
        }).execute()
        return sid

    def _insert_eval(self, sid, t_row, sc, skill_id, mistakes=None, tags=None):
        txt = t_row.get("text") or ""
        snippet = txt[:26] if len(txt) >= 8 else txt
        supabase.table("interview_evaluations").upsert({
            "id": f"eval_{t_row['id']}", "turn_id": t_row["id"], "session_id": sid, "skill_id": skill_id,
            "rubric_scores_json": {
                "criteria": [
                    {"criterion": c, "weight": 0.25, "score": sc, "quoted_justification": snippet}
                    for c in ALL_CRIT
                ]
            },
            "raw_score": sc * 100.0, "normalized_score": sc, "status": "ok",
            "technical_mistakes_json": mistakes or [],
            "misconception_tags": tags or [],
            "evaluator_type": "gemini_rubric", "prompt_id": "interview_rubric_grader", "prompt_version": "v1.0",
            "model_used": "gemini-2.5-flash",
        }, on_conflict="id").execute()

    def test_01_complete_interview_good_answers_evaluated_grade_name_strengths(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            for i, (sk, txt) in enumerate([
                ("db_indexing", "B-tree indexes balance depth logarithmically for selective range predicates cleanly."),
                ("sys_caching", "Redis cluster with Lua atomic counters maintains distributed rate limits smoothly."),
                ("sys_distributed_cap", "Network partitions require explicitly choosing consistency vs availability per endpoint."),
                ("sys_scalability", "Consistent hashing minimizes key rebalancing overhead when scaling stateless shards."),
            ], start=1):
                t, _ = persist_candidate_turn(supabase, sid, i, text=txt, question_text=f"Explain {sk}", skill_id=sk, input_mode="speech", stt_confidence=0.96, audio_duration_s=6.0)
                self._insert_eval(sid, t, 0.90, sk)
            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep["report_status"], "EVALUATED")
            self.assertIn(rep["grade"], ("A", "B"))
            self.assertEqual(rep["header"]["candidate_name"], "Anushka Saxena")
            self.assertTrue(len(rep["strengths"]) > 0)
            self.assertTrue(all(s.get("quote") and s.get("turn_id") for s in rep["strengths"]))
        finally:
            app_module.chat_model = orig_cm

    def test_02_original_bug_spoken_answers_present_empty_evals_never_fake_reject(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            for i in range(1, 5):
                persist_candidate_turn(
                    supabase, sid, i,
                    text="I designed resilient microservices using Flask, PostgreSQL pooling, and Redis pub/sub.",
                    question_text=f"Q{i}", skill_id="sys_api",
                    input_mode="speech", stt_engine="web_speech_api", stt_confidence=0.95, audio_duration_s=5.0,
                )
            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep["header"]["candidate_name"], "Anushka Saxena")
            self.assertEqual(rep["report_status"], "EVALUATION_FAILED")
            self.assertIsNone(rep["grade"])
            self.assertIsNone(rep["recommendation"])
            self.assertGreater(rep["speech_metrics"]["wpm"], 100.0)
            rep_dump = json.dumps(rep)
            self.assertNotIn("No Responses", rep_dump)
            self.assertNotIn("Strong Reject", rep_dump)
        finally:
            app_module.chat_model = orig_cm

    def test_03_zero_candidate_turns_incomplete_no_grade_no_recommendation(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep["report_status"], "INCOMPLETE_INSUFFICIENT_DATA")
            self.assertIsNone(rep["grade"])
            self.assertIsNone(rep["recommendation"])
            self.assertEqual(rep["next_action"], "continue_interview")
        finally:
            app_module.chat_model = orig_cm

    def test_04_all_evaluations_fail_503_then_retry_recovers(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        t_ids = []
        for i in range(1, 5):
            txt = "Consistent hashing maps nodes onto a ring so node joins move O(K/N) keys."
            t, _ = persist_candidate_turn(supabase, sid, i, text=txt, question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
            t_ids.append(t["id"])
            supabase.table("interview_evaluations").upsert({
                "id": f"eval_{t['id']}", "turn_id": t["id"], "session_id": sid, "skill_id": f"sk_{i}",
                "status": "failed", "error_code": "GEMINI_503", "normalized_score": None,
            }, on_conflict="id").execute()

        orig_cm = app_module.chat_model
        try:
            app_module.chat_model = _make_quality_model(fail_503=True)
            rep_fail = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep_fail["report_status"], "EVALUATION_FAILED")
            self.assertIsNone(rep_fail["grade"])
            self.assertIsNone(rep_fail["recommendation"])

            # Now Gemini recovers -> retry succeeds
            app_module.chat_model = _make_quality_model(fail_503=False)
            retry_res = self.client.post(f"/interview/{sid}/retry-evaluations", headers=self._headers(tok))
            self.assertEqual(retry_res.status_code, 200)
            self.assertEqual(retry_res.get_json()["still_failed"], 0)

            rep_ok = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep_ok["report_status"], "EVALUATED")
            self.assertIsNotNone(rep_ok["grade"])
        finally:
            app_module.chat_model = orig_cm

    def test_05_speech_timing_missing_null_delivery_not_evaluated_overall_unaffected(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            # 4 turns with speech input_mode=speech but NO audio_duration_s / word_timestamps
            for i in range(1, 5):
                txt = "Distributed locks use fencing tokens to prevent stale lease writes safely."
                t, sm = persist_candidate_turn(supabase, sid, i, text=txt, question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=None)
                self.assertIsNone(sm["wpm"])
                self._insert_eval(sid, t, 0.85, f"sk_{i}")

            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep["speech_metrics"]["wpm_display"], "Not measurable")
            delivery_dims = [d for d in rep["dimensions"] if d.get("is_delivery")]
            self.assertTrue(len(delivery_dims) >= 1)
            self.assertTrue(all(d["status"] == "Not evaluated" and d["score"] is None for d in delivery_dims))
            # Overall score still reflects content dimensions (~85), never pulled down by missing delivery dims
            self.assertAlmostEqual(rep["overall_score_100"], 85.0, delta=0.5)
        finally:
            app_module.chat_model = orig_cm

    def test_06_typed_only_answers_score_content_dimensions(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            for i in range(1, 5):
                txt = "Typed architectural response covering write-ahead logging and durability guarantees."
                t, _ = persist_candidate_turn(supabase, sid, i, text=txt, question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="typed")
                self._insert_eval(sid, t, 0.88, f"sk_{i}")

            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep["speech_metrics"]["wpm_display"], "Not measurable")
            content_dims = [d for d in rep["dimensions"] if not d.get("is_delivery")]
            self.assertTrue(all(d["score"] is not None for d in content_dims))
            delivery_dims = [d for d in rep["dimensions"] if d.get("is_delivery")]
            self.assertTrue(all(d["status"] == "Not evaluated" for d in delivery_dims))
            self.assertAlmostEqual(rep["coverage"], 0.78, places=2)
            self.assertEqual(rep["report_status"], "EVALUATED")  # 0.78 >= MIN_COVERAGE_FOR_ESTABLISHED (0.75)
        finally:
            app_module.chat_model = orig_cm

    def test_07_mix_strong_weak_answers_only_weak_cited_as_weakness(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            t1, _ = persist_candidate_turn(supabase, sid, 1, text="Strong answer on MVCC snapshots and serializable isolation.", question_text="Q1", skill_id="db_tx", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
            self._insert_eval(sid, t1, 0.92, "db_tx")
            t2, _ = persist_candidate_turn(supabase, sid, 2, text="Strong answer on write-through Redis caching and TTL jitter.", question_text="Q2", skill_id="sys_cache", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
            self._insert_eval(sid, t2, 0.90, "sys_cache")
            t3, _ = persist_candidate_turn(supabase, sid, 3, text="Weak explanation storing locks in local module variable.", question_text="Q3", skill_id="sys_locks", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
            self._insert_eval(sid, t3, 0.30, "sys_locks", mistakes=["Process-local mutex does not synchronize across hosts"], tags=["local_state_only"])

            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertTrue(len(rep["weaknesses"]) > 0)
            self.assertTrue(all(w["turn_id"] == t3["id"] for w in rep["weaknesses"]))
            self.assertTrue(all("Weak explanation storing" in w["quote"] for w in rep["weaknesses"]))
        finally:
            app_module.chat_model = orig_cm

    def test_08_dont_know_answer_low_score_alone_never_strong_reject(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            for i in range(1, 4):
                txt = "Strong architectural reasoning on sharding, replication, and idempotent retries."
                t, _ = persist_candidate_turn(supabase, sid, i, text=txt, question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
                self._insert_eval(sid, t, 0.90, f"sk_{i}")
            # Turn 4: explicit "I don't know"
            t4, _ = persist_candidate_turn(supabase, sid, 4, text="I don't know", question_text="Explain Paxos Synod phase 2b.", skill_id="sys_paxos", input_mode="speech", stt_confidence=0.95, audio_duration_s=2.0)
            from services.interview_rubric_grader import grade_and_persist_turn
            ev4 = grade_and_persist_turn(supabase, sid, t4, t4["question_text"], None, user_id=uid)
            self.assertEqual(ev4["normalized_score"], 0.10)
            self.assertEqual(ev4["evaluator_type"], "deterministic_dont_know")

            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertNotEqual(rep["recommendation"], "Strong Reject")
            self.assertNotEqual(rep["grade"], "F")
        finally:
            app_module.chat_model = orig_cm

    def test_09_small_talk_turns_excluded_from_scoring(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            for i in range(1, 4):
                txt = "Strong explanation of PostgreSQL vacuuming, visibility maps, and heap tuples."
                t, _ = persist_candidate_turn(supabase, sid, i, text=txt, question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
                self._insert_eval(sid, t, 0.90, f"sk_{i}")
            persist_candidate_turn(supabase, sid, 99, text="Hi Ava doing great today!", question_text="How are you doing?", is_small_talk_turn=True, input_mode="speech", stt_confidence=0.99, audio_duration_s=2.0)

            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            st = [q for q in rep["question_reviews"] if q["is_small_talk"]]
            self.assertEqual(len(st), 1)
            self.assertTrue(st[0]["excluded_from_scoring"])
            self.assertEqual(rep["answered_questions_count"], 3)
        finally:
            app_module.chat_model = orig_cm

    def test_10_google_name_no_resume_uses_google_display_name(self):
        uid, tok = self._new_user("Priya Kulkarni")
        create_res = self.client.post(
            "/create-session-no-resume",
            headers=self._headers(tok),
            json={"role": "Platform Engineer", "category": "SystemDesign", "consent": True},
        )
        self.assertEqual(create_res.status_code, 200)
        sid = create_res.get_json()["session_id"]

        with patch("app.generate_dynamic_question", return_value=("Explain consistent hashing.", "technical", False)):
            start_res = self.client.post("/start-interview", headers=self._headers(tok), json={"session_id": sid, "role": "Platform Engineer"})
            self.assertEqual(start_res.status_code, 200)

        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            rep = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(rep["header"]["candidate_name"], "Priya Kulkarni")
            self.assertEqual(rep["header"]["display_name_source"], "google")
        finally:
            app_module.chat_model = orig_cm

    def test_11_duplicate_submit_idempotent_no_double_evidence_or_score_inflation(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok, status="in_progress")
        supabase.table("sessions").update({"active": True}).eq("session_id", sid).execute()

        fake_eval = {"score": 8.5, "accuracy_score": 85, "feedback": "Clear reasoning."}
        mock_model = _make_quality_model()
        with patch.object(app_module, "chat_model", mock_model), \
             patch("app.evaluate_response_comprehensive", return_value=fake_eval), \
             patch("app.generate_dynamic_question", return_value=("Describe index cardinality.", "technical", False)):
            payload = {
                "session_id": sid,
                "answer": "B-tree indexes keep sorted leaf pointers for fast range lookups cleanly.",
                "skill_id": "db_indexing_p8",
                "input_mode": "speech",
                "audio_duration_s": 5.0,
                "stt_confidence": 0.95,
            }
            r1 = self.client.post("/next", headers=self._headers(tok, {"X-Idempotency-Key": "dup-click-1"}), json=payload)
            self.assertEqual(r1.status_code, 200)
            from services.interview_reliability_service import await_background_turn_evals
            await_background_turn_evals(sid, timeout_s=5.0)

            r2 = self.client.post("/next", headers=self._headers(tok, {"X-Idempotency-Key": "dup-click-1"}), json=payload)
            self.assertEqual(r2.status_code, 200)
            self.assertTrue(r2.get_json().get("idempotent_replay"))

            turns_res = supabase.table("interview_turns").select("*").eq("session_id", sid).eq("speaker", "candidate").execute()
            self.assertEqual(len(turns_res.data or []), 1)
            ev_res = supabase.table("skill_evidence").select("*").eq("user_id", uid).eq("skill_id", "db_indexing_p8").execute()
            self.assertEqual(len(ev_res.data or []), 1)

    def test_12_two_candidates_same_role_different_quality_different_reports(self):
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            u1, t1_tok = self._new_user("Rohan Verma")
            s1 = self._create_session(u1, t1_tok)
            for i in range(1, 5):
                t, _ = persist_candidate_turn(supabase, s1, i, text="Strong answer covering idempotency keys, WAL durability, and backpressure queues.", question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
                self._insert_eval(supabase_sid := s1, t, 0.92, f"sk_{i}")

            u2, t2_tok = self._new_user("Kabir Mehta")
            s2 = self._create_session(u2, t2_tok)
            for i in range(1, 5):
                t, _ = persist_candidate_turn(supabase, s2, i, text="Weak answer mixing up thread locking with multi-host distributed queues.", question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
                self._insert_eval(s2, t, 0.34, f"sk_{i}", mistakes=["Confused thread locks with distributed locks"], tags=["concurrency_gap"])

            r1 = self.client.get(f"/interview/{s1}/report", headers=self._headers(t1_tok)).get_json()
            r2 = self.client.get(f"/interview/{s2}/report", headers=self._headers(t2_tok)).get_json()
            self.assertGreater(r1["overall_score_100"], r2["overall_score_100"] + 35)
            self.assertNotEqual(r1["grade"], r2["grade"])
            self.assertTrue(len(r1["strengths"]) > 0 and len(r2["strengths"]) == 0)
            self.assertTrue(len(r2["weaknesses"]) > 0)
        finally:
            app_module.chat_model = orig_cm

    def test_13_page_reload_after_report_identical_persisted_output(self):
        uid, tok = self._new_user("Anushka Saxena")
        sid = self._create_session(uid, tok)
        orig_cm = app_module.chat_model
        app_module.chat_model = None
        try:
            for i in range(1, 4):
                t, _ = persist_candidate_turn(supabase, sid, i, text="Distributed consensus uses quorum replication and term fencing cleanly.", question_text=f"Q{i}", skill_id=f"sk_{i}", input_mode="speech", stt_confidence=0.95, audio_duration_s=5.0)
                self._insert_eval(sid, t, 0.86, f"sk_{i}")

            r1 = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            r2 = self.client.get(f"/interview/{sid}/report", headers=self._headers(tok)).get_json()
            self.assertEqual(r1["overall_score_100"], r2["overall_score_100"])
            self.assertEqual(r1["grade"], r2["grade"])
            self.assertEqual(r1["report_status"], r2["report_status"])
            self.assertEqual(r1["dimension_scores_json"] if "dimension_scores_json" in r1 else r1["dimensions"], r2["dimensions"])
        finally:
            app_module.chat_model = orig_cm

    def test_14_interview_evidence_updates_prep_roadmap_mapped_skills_only(self):
        uid, tok = self._new_user("Anushka Saxena")
        # Seed an unrelated unassessed skill state
        untouched_id = f"css_untouched_{uuid.uuid4().hex[:8]}"
        supabase.table("candidate_skill_states").insert({
            "id": untouched_id, "user_id": uid, "skill_id": "unrelated_css_skill",
            "proficiency": 42.0, "confidence": 0.40, "sample_count": 1,
            "updated_at": "2026-11-10T00:00:00",
        }).execute()

        sid = self._create_session(uid, tok)
        from services.interview_rubric_grader import grade_and_persist_turn
        mock_model = _make_quality_model()
        t, _ = persist_candidate_turn(
            supabase, sid, 1,
            text="PostgreSQL B-tree indexes use balanced tree pages so range queries scan leaf doubly linked lists.",
            question_text="Explain PostgreSQL B-tree indexing.",
            skill_id="db_indexing_roadmap", input_mode="speech", stt_confidence=0.96, audio_duration_s=6.0,
        )
        ev = grade_and_persist_turn(supabase, sid, t, t["question_text"], mock_model, user_id=uid, is_critical=False)
        self.assertEqual(ev["status"], "ok")

        mapped_state = supabase.table("candidate_skill_states").select("*").eq("user_id", uid).eq("skill_id", "db_indexing_roadmap").execute().data
        self.assertEqual(len(mapped_state), 1)
        self.assertGreater(float(mapped_state[0]["proficiency"]), 80.0)

        untouched_after = supabase.table("candidate_skill_states").select("*").eq("id", untouched_id).execute().data
        self.assertEqual(len(untouched_after), 1)
        self.assertEqual(float(untouched_after[0]["proficiency"]), 42.0)
        self.assertEqual(int(untouched_after[0]["sample_count"]), 1)


if __name__ == "__main__":
    unittest.main()
