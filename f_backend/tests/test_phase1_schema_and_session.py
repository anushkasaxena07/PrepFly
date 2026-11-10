"""
Phase 1 Verification Suite:
- Migration 010 & rollback verification
- Startup schema self-check (drift detection before/after)
- Removal of silent PGRST204 Supabase execute fallback
- Identity priority resolution (profile -> google -> resume -> fallback)
- Honest /upload failure handling (non-200 + retryable: true, no ghost session)
- Reliable & idempotent /start-interview session auto-creation
- RLS & privilege enforcement proving client role cannot write evaluations/reports or read rubrics
"""

import io
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
from services.identity_service import resolve_candidate_display_name
from services.resume_service import ResumeParseError, parse_resume_content
from services.schema_check_service import inspect_local_tables_ddl, verify_database_schema


class TestPhase1SchemaAndSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.jwt_secret = os.getenv("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
        cls.user_a_id = f"user_{uuid.uuid4().hex[:8]}"
        cls.user_b_id = f"user_{uuid.uuid4().hex[:8]}"
        cls.user_a_token = jwt.encode(
            {
                "sub": cls.user_a_id,
                "user_id": cls.user_a_id,
                "email": "anushka.google@prepfly.io",
                "name": "Anushka Saxena",
                "role": "STUDENT",
            },
            cls.jwt_secret,
            algorithm="HS256",
        )
        cls.user_b_token = jwt.encode(
            {
                "sub": cls.user_b_id,
                "user_id": cls.user_b_id,
                "email": "other@prepfly.io",
                "name": "Other User",
                "role": "STUDENT",
            },
            cls.jwt_secret,
            algorithm="HS256",
        )

    def test_01_migration_010_and_rollback_exist_and_reload_pgrst(self):
        mig_path = os.path.join(backend_dir, "migrations", "010_interview_capture_and_evaluation.sql")
        rb_path = os.path.join(backend_dir, "migrations", "010_interview_capture_and_evaluation_rollback.sql")
        self.assertTrue(os.path.exists(mig_path))
        self.assertTrue(os.path.exists(rb_path))

        with open(mig_path, "r", encoding="utf-8") as f:
            sql = f.read()
        with open(rb_path, "r", encoding="utf-8") as f:
            rb_sql = f.read()

        # Verify schema drift columns fixed
        for stmt in (
            "resume_text",
            "created_at",
            "actor_id",
            "status",
            "interview_turns",
            "interview_speech_metrics",
            "interview_evaluations",
            "interview_reports",
            "interview_question_rubrics",
            "NOTIFY pgrst, 'reload schema';",
        ):
            self.assertIn(stmt, sql)

        # Verify rollback drops added objects cleanly
        for tbl in ("interview_question_rubrics", "interview_reports", "interview_evaluations", "interview_speech_metrics"):
            self.assertIn(f"DROP TABLE IF EXISTS {tbl}", rb_sql)

    def test_02_schema_self_check_detects_drift_and_passes_after_migration(self):
        # Simulated remote client missing sessions.resume_text (PGRST204)
        mock_sb = MagicMock()
        mock_sb._local_client = None
        mock_real = MagicMock()

        def table_side_effect(tbl_name):
            qb = MagicMock()
            def select_side_effect(cols):
                inner = MagicMock()
                def limit_side_effect(n):
                    leaf = MagicMock()
                    if tbl_name == "sessions" and ("resume_text" in cols or "," in cols):
                        leaf.execute.side_effect = Exception("PGRST204: Could not find the 'resume_text' column of 'sessions'")
                    else:
                        leaf.execute.return_value = MagicMock(data=[])
                    return leaf
                inner.limit.side_effect = limit_side_effect
                return inner
            qb.select.side_effect = select_side_effect
            return qb

        mock_real.table.side_effect = table_side_effect
        mock_sb._real_client = mock_real

        drift_report = verify_database_schema(mock_sb)
        self.assertFalse(drift_report["ok"])
        self.assertIn("resume_text", drift_report["missing"].get("sessions", []))

        # Now verify local SQLite schema post-Migration-010 passes completely
        local_mock = SQLiteSupabaseMock(db_path=":memory:")
        ok_report = verify_database_schema(local_mock)
        self.assertTrue(ok_report["ok"], f"Unexpected missing columns: {ok_report['missing']}")

    def test_03_pgrst204_never_silently_falls_back_to_sqlite(self):
        mock_real = MagicMock()
        mock_builder = MagicMock()
        mock_real.table.return_value = mock_builder
        mock_builder.insert.return_value = mock_builder
        mock_builder.execute.side_effect = Exception("PGRST204: Could not find the 'resume_text' column of 'sessions'")

        fallback_client = app_module.SupabaseFallbackClient.__new__(app_module.SupabaseFallbackClient)
        fallback_client._real_client = mock_real
        fallback_client._local_client = SQLiteSupabaseMock(db_path=":memory:")
        fallback_client._use_local = False

        with self.assertRaises(RuntimeError) as cm:
            fallback_client.table("sessions").insert({"session_id": "s1", "resume_text": "hello"}).execute()
        self.assertIn("PGRST204", str(cm.exception))

    def test_04_identity_resolution_priority_and_google_fallback(self):
        local_mock = SQLiteSupabaseMock(db_path=":memory:")
        uid = f"u_{uuid.uuid4().hex[:8]}"
        # Without DB profile -> uses Google claim
        name, src = resolve_candidate_display_name(
            user_payload={"sub": uid, "name": "Anushka Google"},
            user_id=uid,
            parsed_resume={"full_name": "Resume Name"},
            supabase_client=local_mock,
        )
        self.assertEqual((name, src), ("Anushka Google", "google"))

        # With DB profile -> profile takes priority over Google
        local_mock.table("users").insert({"id": uid, "email": "a@b.com", "name": "Anushka Profile"}).execute()
        name2, src2 = resolve_candidate_display_name(
            user_payload={"sub": uid, "name": "Anushka Google"},
            user_id=uid,
            parsed_resume={"full_name": "Resume Name"},
            supabase_client=local_mock,
        )
        self.assertEqual((name2, src2), ("Anushka Profile", "profile"))

        # Existing real name is never overwritten with "Candidate"
        name3, src3 = resolve_candidate_display_name(
            user_payload={},
            existing_name="Anushka Existing",
            existing_source="google",
            supabase_client=local_mock,
        )
        self.assertEqual((name3, src3), ("Anushka Existing", "google"))

    @patch("werkzeug.datastructures.FileStorage.save", return_value=None)
    @patch("time.sleep", return_value=None)
    @patch("app.extract_text_from_pdf", return_value="Anushka Saxena\nSenior Backend Engineer\nPython, Flask, Postgres")
    def test_05_upload_fails_loudly_on_gemini_503_no_ghost_session(self, mock_extract, mock_sleep, mock_save):
        before_count = len((supabase.table("sessions").select("session_id").eq("user_id", self.user_a_id).execute().data) or [])
        failing_model = MagicMock()
        failing_model.model = "gemini-3.8-flash"
        failing_model.invoke.side_effect = Exception("503 UNAVAILABLE: Service overloaded")

        orig_cm = app_module.chat_model
        try:
            app_module.chat_model = failing_model
            res = self.client.post(
                "/upload",
                headers={"Authorization": f"Bearer {self.user_a_token}"},
                data={
                    "resume": (io.BytesIO(b"%PDF-1.4 resume bytes"), "resume.pdf"),
                    "consent": "true",
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(res.status_code, 503)
            body = res.get_json()
            self.assertTrue(body.get("retryable"))
            self.assertIn("failed", body.get("message", "").lower())
            after_count = len((supabase.table("sessions").select("session_id").eq("user_id", self.user_a_id).execute().data) or [])
            self.assertEqual(before_count, after_count, "Failed /upload must not create a ghost session row")
        finally:
            app_module.chat_model = orig_cm

    @patch("app.generate_dynamic_question", return_value=("Walk me through a scalable system you designed.", "Technical", {}))
    def test_06_start_interview_creates_missing_session_and_is_idempotent(self, mock_gen_q):
        new_sid = str(uuid.uuid4())
        idem_key = f"idem_{uuid.uuid4().hex}"

        # Call /start-interview directly without prior /upload -> must create session cleanly
        res1 = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={
                "session_id": new_sid,
                "idempotency_key": idem_key,
                "role": "Backend Engineer",
                "category": "System Design",
                "difficulty": "Medium",
            },
        )
        self.assertEqual(res1.status_code, 200)
        d1 = res1.get_json()
        self.assertEqual(d1["session_id"], new_sid)
        self.assertEqual(d1["display_name"], "Anushka Saxena")
        self.assertEqual(d1["display_name_source"], "google")
        self.assertEqual(d1["question_number"], 1)

        # Retry with same idempotency_key -> idempotent replay, no duplicate question
        res2 = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_a_token}"},
            json={"session_id": new_sid, "idempotency_key": idem_key},
        )
        self.assertEqual(res2.status_code, 200)
        d2 = res2.get_json()
        self.assertTrue(d2.get("idempotent_replay"))
        self.assertEqual(d2["question"], d1["question"])

        # User B still cannot access User A's created session (IDOR -> 404)
        idor_res = self.client.post(
            "/start-interview",
            headers={"Authorization": f"Bearer {self.user_b_token}"},
            json={"session_id": new_sid},
        )
        self.assertEqual(idor_res.status_code, 404)

    def test_07_rls_client_token_cannot_write_evals_reports_or_read_rubrics(self):
        db = SQLiteSupabaseMock(db_path=":memory:")
        sid = str(uuid.uuid4())
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"

        # Backend (service_role) seeds session, turn, rubric, evaluation, and report
        db.table("sessions").insert({"session_id": sid, "user_id": self.user_a_id, "status": "in_progress"}).execute()
        db.table("interview_turns").insert({
            "id": turn_id, "session_id": sid, "turn_index": 1, "speaker": "candidate",
            "text": "I used Redis and indexes.", "created_at": "2026-11-10T00:00:00Z"
        }).execute()
        db.table("interview_question_rubrics").insert({
            "id": "rub_1", "session_id": sid, "question_id": "q1",
            "rubric_json": json.dumps({"criteria": ["caching", "indexing"]}),
            "reference_answer": "Use write-through Redis cache and composite B-tree index.",
            "created_at": "2026-11-10T00:00:00Z",
        }).execute()
        db.table("interview_evaluations").insert({
            "id": "eval_1", "turn_id": turn_id, "session_id": sid, "skill_id": "sys_caching",
            "rubric_scores_json": json.dumps({"caching": 0.9}), "normalized_score": 0.85,
            "status": "ok", "created_at": "2026-11-10T00:00:00Z"
        }).execute()
        db.table("interview_reports").insert({
            "id": "rep_1", "session_id": sid, "candidate_id": self.user_a_id,
            "report_status": "EVALUATED", "overall_score": 0.85, "grade": "A",
            "generated_at": "2026-11-10T00:00:00Z",
        }).execute()

        client_a = db.for_client_role(self.user_a_id, role="authenticated")
        client_b = db.for_client_role(self.user_b_id, role="authenticated")

        # 1. Client token CANNOT insert or update interview_evaluations
        with self.assertRaises(PermissionError):
            client_a.table("interview_evaluations").insert({
                "id": "fake_eval", "turn_id": turn_id, "session_id": sid, "normalized_score": 1.0, "status": "ok"
            }).execute()

        with self.assertRaises(PermissionError):
            client_a.table("interview_evaluations").update({"normalized_score": 1.0}).eq("id", "eval_1").execute()

        # 2. Client token CANNOT insert or update interview_reports or interview_speech_metrics
        with self.assertRaises(PermissionError):
            client_a.table("interview_reports").insert({
                "id": "fake_rep", "session_id": sid, "candidate_id": self.user_a_id, "report_status": "EVALUATED", "grade": "A"
            }).execute()

        with self.assertRaises(PermissionError):
            client_a.table("interview_speech_metrics").insert({
                "turn_id": turn_id, "session_id": sid, "wpm": 145
            }).execute()

        # 3. Client token CANNOT read rubrics table or rubric_scores_json column
        with self.assertRaises(PermissionError):
            client_a.table("interview_question_rubrics").select("*").eq("session_id", sid).execute()

        with self.assertRaises(PermissionError):
            client_a.table("interview_evaluations").select("*").eq("session_id", sid).execute()

        # 4. Client A CAN read safe evaluation fields & own report; Client B reads ZERO rows
        safe_evals_a = client_a.table("interview_evaluations").select("id,turn_id,normalized_score,status").eq("session_id", sid).execute()
        self.assertEqual(len(safe_evals_a.data), 1)
        safe_evals_b = client_b.table("interview_evaluations").select("id,turn_id,normalized_score,status").eq("session_id", sid).execute()
        self.assertEqual(len(safe_evals_b.data), 0)

        rep_b = client_b.table("interview_reports").select("*").eq("session_id", sid).execute()
        self.assertEqual(len(rep_b.data), 0)

    def test_09_resume_404_model_not_found_switches_to_gemini_38_flash(self):
        from services import ai_service, resume_service

        class _Live404Model:
            model = "gemini-2.5-flash"

            def invoke(self, _messages):
                raise RuntimeError("404 NOT_FOUND. This model models/gemini-2.5-flash is no longer available")

        class _FakeResp:
            def __init__(self, content):
                self.content = content

        class _FakeFallbackChat:
            def __init__(self, **kwargs):
                self.model = kwargs["model"]

            def invoke(self, _messages):
                if self.model == "gemini-3.8-flash":
                    return _FakeResp('{"full_name":"Ava Test","skills":["Python"],"ats_score":88,"missing_info":[]}')
                raise RuntimeError(f"Unexpected model {self.model}")

        orig_env = os.environ.get("ENVIRONMENT")
        orig_flask_env = os.environ.get("FLASK_ENV")
        orig_key = os.environ.get("GEMINI_API_KEY")
        ai_service._UNAVAILABLE_GEMINI_MODELS.clear()
        try:
            os.environ["ENVIRONMENT"] = "production"
            os.environ["FLASK_ENV"] = "production"
            os.environ["GEMINI_API_KEY"] = "AIzaLiveMockKeyFor404SwitchTest"
            with patch("langchain_google_genai.ChatGoogleGenerativeAI", side_effect=_FakeFallbackChat), \
                 patch.object(ai_service, "discover_gemini_flash_models", return_value=[]):
                parsed = resume_service.parse_resume_content(
                    f"Unique Resume 404 Switch Test {uuid.uuid4().hex}\nPython Flask React",
                    _Live404Model(),
                )
            self.assertEqual(parsed["model_used"], "gemini-3.8-flash")
            self.assertIn("Python", parsed["structured_data"]["skills"])
            self.assertIn("gemini-2.5-flash", ai_service._UNAVAILABLE_GEMINI_MODELS)
        finally:
            ai_service._UNAVAILABLE_GEMINI_MODELS.clear()
            if orig_env is None:
                os.environ.pop("ENVIRONMENT", None)
            else:
                os.environ["ENVIRONMENT"] = orig_env
            if orig_flask_env is None:
                os.environ.pop("FLASK_ENV", None)
            else:
                os.environ["FLASK_ENV"] = orig_flask_env
            if orig_key is not None:
                os.environ["GEMINI_API_KEY"] = orig_key

    def test_10_notifications_pgrst205_suppresses_poll_spam(self):
        app_module._NOTIFICATIONS_TABLE_MISSING_UNTIL = 0.0
        notif_calls = []

        class _RaisingNotifBuilder:
            def select(self, *_a, **_kw):
                return self

            def eq(self, *_a, **_kw):
                return self

            def neq(self, *_a, **_kw):
                return self

            def execute(self):
                notif_calls.append(1)
                raise RuntimeError(
                    "Database execute failed on 'notifications': "
                    "{'message': \"Could not find the table 'public.notifications' in the schema cache\", 'code': 'PGRST205'}"
                )

        orig_table = supabase.table

        def _fake_table(name, *args, **kwargs):
            if name == "notifications":
                return _RaisingNotifBuilder()
            return orig_table(name, *args, **kwargs)

        try:
            with patch.object(supabase, "table", side_effect=_fake_table):
                r1 = self.client.get("/notifications", headers={"Authorization": f"Bearer {self.user_a_token}"})
                r2 = self.client.get("/notifications", headers={"Authorization": f"Bearer {self.user_a_token}"})
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r2.status_code, 200)
            # Step 1 triggers PGRST205 once, skipping Step 2 and the entire next poll!
            self.assertEqual(len(notif_calls), 1)
        finally:
            app_module._NOTIFICATIONS_TABLE_MISSING_UNTIL = 0.0


if __name__ == "__main__":
    unittest.main()
