import concurrent.futures
import io
import os
import sys
import threading
import time
import unittest
import uuid
from unittest.mock import MagicMock, patch

import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32ch")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_12345")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test_razorpay_secret")
os.environ.setdefault("RESEND_API_KEY", "re_test_12345")

import app as app_module
from app import app, supabase


def create_jwt(sub, email, role, org_id=None):
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "role": role,
        "aud": "authenticated",
    }
    if org_id is not None:
        payload["organization_id"] = org_id
    return jwt.encode(payload, app_module._get_jwt_secret(), algorithm="HS256")


class TestProductionIncidentRemediation(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.org_a = f"org_inc_a_{uuid.uuid4().hex[:6]}"
        self.org_b = f"org_inc_b_{uuid.uuid4().hex[:6]}"
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())
        self.admin_a = str(uuid.uuid4())

        self.token_a = create_jwt(self.user_a, "studenta@test.com", "Student", org_id=self.org_a)
        self.token_b = create_jwt(self.user_b, "studentb@test.com", "Student", org_id=self.org_b)
        self.token_admin_a = create_jwt(self.admin_a, "admina@test.com", "Organization Admin", org_id=self.org_a)
        self.token_sa = create_jwt(str(uuid.uuid4()), "sa@test.com", "SUPER_ADMIN", org_id=None)

    # ── 1. Gemini Resume Parsing ─────────────────────────────────────────────

    def test_01_resume_parse_success_preserves_schema(self):
        from services import resume_service

        mock_model = MagicMock()
        mock_model.model = "gemini-3.8-flash"
        mock_resp = MagicMock()
        mock_resp.content = (
            '```json\n'
            '{"full_name":"Priya Nair","email":"priya@example.com","phone":"9999999999",'
            '"skills":["Python","Flask","PostgreSQL"],'
            '"projects":[{"title":"PrepFly","tech_stack":["React","Flask"],"description":"Interview AI"}],'
            '"experience":[{"role":"Backend Intern","company":"Acme","duration":"6m","key_achievements":["Cut p95 30%"]}],'
            '"education":[{"degree":"B.Tech","institution":"NIT","year":"2026"}],'
            '"ats_score":91,"missing_info":[]}\n'
            '```'
        )
        mock_model.invoke.return_value = mock_resp

        result = resume_service.parse_resume_content(
            f"Unique Success Resume {uuid.uuid4().hex}\nPriya Nair Python Flask PostgreSQL",
            mock_model,
        )
        self.assertEqual(result["ats_score"], 91)
        self.assertEqual(result["model_used"], "gemini-3.8-flash")
        self.assertEqual(result["prompt_id"], resume_service.RESUME_PARSE_PROMPT_ID)
        self.assertEqual(result["structured_data"]["full_name"], "Priya Nair")
        self.assertEqual(result["structured_data"]["skills"], ["Python", "Flask", "PostgreSQL"])
        self.assertEqual(result["missing_info"], [])
        mock_model.invoke.assert_called_once()

    @patch("time.sleep", return_value=None)
    def test_02_resume_parse_timeout_returns_504_retryable(self, _mock_sleep):
        from services import resume_service

        timeout_model = MagicMock()
        timeout_model.model = "gemini-3.8-flash"
        timeout_model.invoke.side_effect = TimeoutError("504 Deadline Exceeded waiting on Gemini")

        with self.assertRaises(resume_service.ResumeParseError) as ctx:
            resume_service.parse_resume_content(
                f"Unique Timeout Resume {uuid.uuid4().hex}\nBackend Engineer",
                timeout_model,
            )
        self.assertEqual(ctx.exception.status_code, 504)
        self.assertTrue(ctx.exception.retryable)

    def test_03_resume_parse_invalid_json_never_silently_returns_fake_data(self):
        from services import resume_service

        bad_model = MagicMock()
        bad_model.model = "gemini-3.8-flash"
        bad_resp = MagicMock()
        bad_resp.content = "Not valid JSON at all"
        bad_model.invoke.return_value = bad_resp

        with self.assertRaises(resume_service.ResumeParseError) as ctx:
            resume_service.parse_resume_content(
                f"Unique Bad JSON Resume {uuid.uuid4().hex}\nSystems Engineer",
                bad_model,
            )
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertTrue(ctx.exception.retryable)
        self.assertEqual(bad_model.invoke.call_count, 3)

    def test_04_resume_parse_deduplicates_concurrent_retries(self):
        from services import resume_service

        started = threading.Event()
        release = threading.Event()
        call_count = {"n": 0}

        class _SlowOnceModel:
            model = "gemini-3.8-flash"

            def invoke(self, _msgs):
                call_count["n"] += 1
                started.set()
                release.wait(timeout=3.0)
                r = MagicMock()
                r.content = '{"full_name":"Same Candidate","skills":["Go","Redis"],"ats_score":84,"missing_info":[]}'
                return r

        resume_txt = f"Concurrent Retry Dedupe {uuid.uuid4().hex}\nGo Redis Engineer"
        model = _SlowOnceModel()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(resume_service.parse_resume_content, resume_txt, model)
            self.assertTrue(started.wait(timeout=2.0))
            f2 = pool.submit(resume_service.parse_resume_content, resume_txt, model)
            time.sleep(0.05)
            release.set()
            r1 = f1.result(timeout=5.0)
            r2 = f2.result(timeout=5.0)

        self.assertEqual(call_count["n"], 1, "Concurrent duplicate parse retries must share one Gemini call")
        self.assertEqual(r1["structured_data"]["skills"], ["Go", "Redis"])
        self.assertEqual(r2["structured_data"]["skills"], ["Go", "Redis"])

    # ── 2. Supabase Notifications & Migration Verification ───────────────────

    def test_05_migration_011_notifications_schema_indexes_and_rls(self):
        mig_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "migrations",
            "011_fix_live_supabase_schema.sql",
        )
        with open(mig_path, "r", encoding="utf-8") as fh:
            sql = fh.read()

        for expected in (
            "CREATE TABLE IF NOT EXISTS public.notifications",
            "organization_id TEXT",
            "user_id TEXT",
            "sender_type TEXT",
            "target_group TEXT",
            "target_dept TEXT",
            "target_sem TEXT",
            "idx_notifications_org_id",
            "idx_notifications_user_id",
            "idx_notifications_sender_type",
            "ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY",
            "service_role_all_notifications",
            "authenticated_read_scoped_notifications",
            "NOTIFY pgrst, 'reload schema';",
        ):
            self.assertIn(expected, sql)

    def test_06_notifications_user_org_and_superadmin_scoping(self):
        orig_in_mem = list(app_module.IN_MEMORY_NOTIFICATIONS)
        app_module._NOTIFICATIONS_TABLE_MISSING_UNTIL = 0.0
        try:
            sa_id = f"sa_{uuid.uuid4().hex[:8]}"
            org_a_id = f"orga_{uuid.uuid4().hex[:8]}"
            org_b_id = f"orgb_{uuid.uuid4().hex[:8]}"
            uid_a_id = f"uida_{uuid.uuid4().hex[:8]}"

            app_module._push_notification({
                "id": sa_id,
                "sender_type": "SUPER_ADMIN",
                "sender_name": "Platform Super Admin",
                "organization_id": None,
                "title": "Platform Broadcast",
                "message": "Scheduled maintenance window",
            })
            app_module._push_notification({
                "id": org_a_id,
                "sender_type": "ADMIN",
                "sender_name": "Org A Admin",
                "organization_id": self.org_a,
                "title": "Org A Update",
                "message": "Drive tomorrow",
            })
            app_module._push_notification({
                "id": org_b_id,
                "sender_type": "ADMIN",
                "sender_name": "Org B Admin",
                "organization_id": self.org_b,
                "title": "Org B Secret Update",
                "message": "Only for Org B",
            })
            app_module._push_notification({
                "id": uid_a_id,
                "sender_type": "ADMIN",
                "sender_name": "Direct Mentor",
                "organization_id": self.org_a,
                "user_id": self.user_a,
                "title": "Direct Message",
                "message": "Private for User A",
            })

            res_a = self.client.get("/notifications", headers={"Authorization": f"Bearer {self.token_a}"})
            self.assertEqual(res_a.status_code, 200)
            ids_a = {item["id"] for item in res_a.get_json()}
            self.assertIn(sa_id, ids_a)
            self.assertIn(org_a_id, ids_a)
            self.assertIn(uid_a_id, ids_a)
            self.assertNotIn(org_b_id, ids_a)

            res_b = self.client.get("/notifications", headers={"Authorization": f"Bearer {self.token_b}"})
            self.assertEqual(res_b.status_code, 200)
            ids_b = {item["id"] for item in res_b.get_json()}
            self.assertIn(sa_id, ids_b)
            self.assertIn(org_b_id, ids_b)
            self.assertNotIn(org_a_id, ids_b)
            self.assertNotIn(uid_a_id, ids_b)
        finally:
            app_module.IN_MEMORY_NOTIFICATIONS[:] = orig_in_mem
            app_module._NOTIFICATIONS_TABLE_MISSING_UNTIL = 0.0

    # ── 3. Auth & AuthZ (/user-stats, /payment/history) ──────────────────────

    def test_07_user_stats_and_payment_history_auth_rbac(self):
        # Seed student A in org_a and student B in org_b for org-admin scope check
        supabase.table("users").insert({
            "id": self.user_a,
            "email": f"sa_{self.user_a[:8]}@test.com",
            "organization_id": self.org_a,
            "role": "Student",
        }).execute()
        supabase.table("users").insert({
            "id": self.user_b,
            "email": f"sb_{self.user_b[:8]}@test.com",
            "organization_id": self.org_b,
            "role": "Student",
        }).execute()

        # /user-stats: unauthenticated -> 401; cross-user -> 403; self & own org admin -> 200; cross-org admin -> 403
        self.assertEqual(self.client.get(f"/user-stats/{self.user_a}").status_code, 401)
        self.assertEqual(
            self.client.get(f"/user-stats/{self.user_a}", headers={"Authorization": f"Bearer {self.token_b}"}).status_code,
            403,
        )
        self.assertEqual(
            self.client.get("/user-stats/me", headers={"Authorization": f"Bearer {self.token_a}"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/user-stats/{self.user_a}", headers={"Authorization": f"Bearer {self.token_admin_a}"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/user-stats/{self.user_b}", headers={"Authorization": f"Bearer {self.token_admin_a}"}).status_code,
            403,
        )

        # /payment/history: unauth -> 401; student -> 403; wrong org -> 403; own org admin -> 200
        self.assertEqual(self.client.get(f"/payment/history?org_id={self.org_a}").status_code, 401)
        self.assertEqual(
            self.client.get(f"/payment/history?org_id={self.org_a}", headers={"Authorization": f"Bearer {self.token_a}"}).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(f"/payment/history?org_id={self.org_b}", headers={"Authorization": f"Bearer {self.token_admin_a}"}).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(f"/payment/history?org_id={self.org_a}", headers={"Authorization": f"Bearer {self.token_admin_a}"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"/payment/history?org_id={self.org_b}", headers={"Authorization": f"Bearer {self.token_sa}"}).status_code,
            200,
        )

    # ── 4. Redis Upstash Normalization, Bounded Retry & Circuit Breaker ──────

    def test_08_redis_tls_bounded_retry_and_l1_fallback(self):
        from services.cache_service import RedisCacheBackend, TieredCacheManager, normalize_redis_url

        self.assertEqual(
            normalize_redis_url("redis://default:pw@example.upstash.io:6379"),
            "rediss://default:pw@example.upstash.io:6379",
        )
        self.assertEqual(normalize_redis_url("redis://localhost:6379/0"), "redis://localhost:6379/0")

        # Simulated transient timeout on attempt 1 followed by success on attempt 2
        mock_client = MagicMock()
        mock_client.ping.side_effect = [TimeoutError("transient blip"), True]
        with patch("redis.from_url", return_value=mock_client), patch("time.sleep", return_value=None):
            backend = RedisCacheBackend("redis://default:pw@host.upstash.io:6379", max_connect_retries=2)
        self.assertTrue(backend.is_connected)
        self.assertEqual(mock_client.ping.call_count, 2)

        # Runtime socket errors open circuit breaker and TieredCacheManager serves L1 cleanly
        mgr = TieredCacheManager()
        mgr.l2 = backend
        mgr.set("k_inc", {"ok": True}, ttl=60)
        mock_client.get.side_effect = ConnectionError("Redis dropped")
        self.assertEqual(mgr.get("k_inc"), {"ok": True})
        mgr.l1.clear()
        self.assertIsNone(mgr.get("k_inc"))
        self.assertIsNone(mgr.get("k_inc"))
        self.assertFalse(backend.is_connected)

    # ── 5. Upload Reliability & Resume AI Extract / Improve ──────────────────

    @patch("app.extract_text_from_pdf", return_value="Candidate Resume\nPython Flask React AWS")
    def test_09_resume_extract_and_upload_validation(self, _mock_extract):
        # Empty file rejected cleanly with 400
        res_empty = self.client.post(
            "/upload",
            headers={"Authorization": f"Bearer {self.token_a}"},
            data={"resume": (io.BytesIO(b""), "empty.pdf"), "consent": "true"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res_empty.status_code, 400)

        # Bad extension rejected cleanly with 400
        res_ext = self.client.post(
            "/upload",
            headers={"Authorization": f"Bearer {self.token_a}"},
            data={"resume": (io.BytesIO(b"hello"), "notes.txt"), "consent": "true"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res_ext.status_code, 400)

        # Resume AI lightweight extract succeeds without calling Gemini or creating sessions
        before_sessions = len(supabase.table("sessions").select("session_id").eq("user_id", self.user_a).execute().data or [])
        res_extract = self.client.post(
            "/api/resume/extract",
            headers={"Authorization": f"Bearer {self.token_a}"},
            data={"resume": (io.BytesIO(b"%PDF-1.4 sample resume"), "resume.pdf"), "consent": "true"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res_extract.status_code, 200)
        body = res_extract.get_json()
        self.assertIn("Python Flask React AWS", body["resume_text"])
        self.assertTrue(body["extract_only"])
        after_sessions = len(supabase.table("sessions").select("session_id").eq("user_id", self.user_a).execute().data or [])
        self.assertEqual(before_sessions, after_sessions)

    @patch("services.ai_service.safe_invoke_llm")
    def test_10_resume_improve_uses_safe_invoke_llm(self, mock_safe_llm):
        mock_safe_llm.return_value = (
            '{"target_role":"Backend Engineer","original_ats_score":72,"projected_ats_score":91,'
            '"tailored_summary":"Strong engineer","key_injected_skills":["Redis","Docker"],'
            '"bullet_point_improvements":[{"original":"Built APIs","improved":"Built 10k RPS APIs","impact_reason":"Metric"}],'
            '"full_improved_resume":"# Improved"}'
        )
        res = self.client.post(
            "/api/resume/improve",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={
                "resume_text": "Built APIs using Python Flask and PostgreSQL",
                "job_description": "Backend Engineer Python Flask Redis Docker",
                "target_role": "Backend Engineer",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["target_role"], "Backend Engineer")
        self.assertGreaterEqual(data["projected_ats_score"], data["original_ats_score"])
        mock_safe_llm.assert_called_once()


if __name__ == "__main__":
    unittest.main()

