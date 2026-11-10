import io
import json
import logging
import os
import smtplib
import sys
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone
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
from services.resume_service import (
    clear_resume_jobs_for_tests,
    create_resume_parse_job,
    deterministic_parse_resume,
    get_resume_parse_job,
)
from services.subscription_service import (
    get_org_subscription_status,
    parse_utc_datetime,
    utc_now,
)


def _issue_jwt(sub, email, role, org_id=None):
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


class TestStabilizationAcceptance(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        clear_resume_jobs_for_tests()
        self.org_a = f"org_stab_a_{uuid.uuid4().hex[:6]}"
        self.org_b = f"org_stab_b_{uuid.uuid4().hex[:6]}"
        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())
        self.admin_a = str(uuid.uuid4())
        self.token_a = _issue_jwt(self.user_a, "studa@stab.test", "Student", org_id=self.org_a)
        self.token_b = _issue_jwt(self.user_b, "studb@stab.test", "Student", org_id=self.org_b)
        self.token_admin_a = _issue_jwt(self.admin_a, "admina@stab.test", "Organization Admin", org_id=self.org_a)

    # ── Phase 1: Database Migrations & Production Config ──────────────────────

    def test_01_migrations_010_and_011_complete_and_no_sqlite_in_render(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        m010 = os.path.join(repo_root, "f_backend", "migrations", "010_interview_capture_and_evaluation.sql")
        m011 = os.path.join(repo_root, "f_backend", "migrations", "011_fix_live_supabase_schema.sql")
        render_yml = os.path.join(repo_root, "render.yaml")

        with open(m010, "r", encoding="utf-8") as fh:
            sql_010 = fh.read()
        with open(m011, "r", encoding="utf-8") as fh:
            sql_011 = fh.read()
        with open(render_yml, "r", encoding="utf-8") as fh:
            render_txt = fh.read()

        # Verify migration 010 itself does NOT create public.notifications (managed explicitly in 011)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS public.notifications", sql_010)
        self.assertIn("CREATE TABLE IF NOT EXISTS public.notifications", sql_011)

        # Verify 011 idempotently alters pre-existing partial tables checked by schema_check_service
        for tbl in (
            "interview_speech_metrics",
            "interview_evaluations",
            "interview_reports",
            "interview_question_rubrics",
            "notifications",
            "organization",
            "activity_logs",
        ):
            self.assertIn(tbl, sql_011)
        self.assertIn("NOTIFY pgrst, 'reload schema';", sql_011)
        self.assertIn('value: "false"', render_txt)

    # ── Phase 2: Async Resume Job Architecture & Deterministic Fallback ───────

    def test_02_deterministic_resume_fallback_grounded_no_fake_skills(self):
        fb = deterministic_parse_resume("Priya Sharma\npriya@example.com\nBuilt microservices in Python, Flask, PostgreSQL and Redis.")
        self.assertTrue(fb["is_partial"])
        self.assertEqual(fb["model_used"], "deterministic_fallback")
        skills = [s.lower() for s in fb["structured_data"]["skills"]]
        self.assertIn("python", skills)
        self.assertIn("flask", skills)
        self.assertEqual(fb["structured_data"]["email"], "priya@example.com")

        empty_fb = deterministic_parse_resume("")
        self.assertEqual(empty_fb["structured_data"]["skills"], [])

    @patch("app.extract_text_from_pdf", return_value="Rohan Verma\nSenior Backend Engineer\nPython PostgreSQL Redis Docker")
    def test_03_async_resume_job_lifecycle_dedup_and_isolation(self, _mock_extract):
        mock_model = MagicMock()
        mock_model.model = "gemini-3.8-flash"
        mock_resp = MagicMock()
        mock_resp.content = '{"full_name":"Rohan Verma","email":"rohan@ex.com","skills":["Python","PostgreSQL"],"ats_score":86,"missing_info":[]}'
        mock_model.invoke.return_value = mock_resp

        orig_cm = app_module.chat_model
        try:
            app_module.chat_model = mock_model
            res1 = self.client.post(
                "/api/resume/jobs",
                headers={"Authorization": f"Bearer {self.token_a}"},
                data={"resume": (io.BytesIO(b"%PDF-1.4 resume bytes"), "rohan.pdf"), "consent": "true"},
                content_type="multipart/form-data",
            )
            self.assertEqual(res1.status_code, 202)
            d1 = res1.get_json()
            job_id = d1["job_id"]
            self.assertFalse(d1["deduplicated"])

            # Wait briefly for background thread completion
            job_state = None
            for _ in range(40):
                poll = self.client.get(f"/api/resume/jobs/{job_id}", headers={"Authorization": f"Bearer {self.token_a}"})
                self.assertEqual(poll.status_code, 200)
                job_state = poll.get_json()
                if job_state["status"] in ("completed", "failed"):
                    break
                time.sleep(0.05)

            self.assertIsNotNone(job_state)
            self.assertEqual(job_state["status"], "completed")
            self.assertEqual(job_state["ats_score"], 86)
            self.assertTrue(job_state.get("session_id"))

            # Duplicate upload for same user & content deduplicates to same job_id
            res2 = self.client.post(
                "/api/resume/jobs",
                headers={"Authorization": f"Bearer {self.token_a}"},
                data={"resume": (io.BytesIO(b"%PDF-1.4 resume bytes"), "rohan.pdf"), "consent": "true"},
                content_type="multipart/form-data",
            )
            self.assertEqual(res2.status_code, 202)
            d2 = res2.get_json()
            self.assertTrue(d2["deduplicated"])
            self.assertEqual(d2["job_id"], job_id)

            # Ownership checks: unauth -> 401; User B -> 403
            self.assertEqual(self.client.get(f"/api/resume/jobs/{job_id}").status_code, 401)
            self.assertEqual(
                self.client.get(f"/api/resume/jobs/{job_id}", headers={"Authorization": f"Bearer {self.token_b}"}).status_code,
                403,
            )
        finally:
            app_module.chat_model = orig_cm

    # ── Phase 3: Subscription Datetime Timezone Regression ────────────────────

    def test_04_subscription_datetimes_handle_z_offset_and_naive_timestamps(self):
        # Verify parse_utc_datetime handles Z, +00:00, +05:30, and naive timestamps cleanly
        dt_z = parse_utc_datetime("2026-11-10T18:00:00Z")
        dt_plus = parse_utc_datetime("2026-11-10T23:30:00+05:30")
        dt_naive = parse_utc_datetime("2026-11-10T18:00:00")
        self.assertEqual(dt_z, dt_plus)
        self.assertEqual(dt_z, dt_naive)
        self.assertIsNotNone(dt_z.tzinfo)

        # Boundary test: org with Z-suffixed trial_end in the past vs future offset-aware timestamp
        org_past = f"org_tz_past_{uuid.uuid4().hex[:6]}"
        org_fut = f"org_tz_fut_{uuid.uuid4().hex[:6]}"
        past_ts = (utc_now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        fut_ts = (utc_now() + timedelta(days=5)).astimezone(timezone(timedelta(hours=5, minutes=30))).isoformat()

        supabase.table("organization").insert({
            "id": org_past,
            "name": "Past Trial Org",
            "subscription_status": "TRIAL",
            "trial_start": (utc_now() - timedelta(days=11)).isoformat(),
            "trial_end": past_ts,
            "current_plan": "Trial",
        }).execute()
        supabase.table("organization").insert({
            "id": org_fut,
            "name": "Active Offset Org",
            "subscription_status": "ACTIVE",
            "subscription_start": (utc_now() - timedelta(days=10)).isoformat(),
            "subscription_expiry": fut_ts,
            "current_plan": "Pro Plan",
        }).execute()

        st_past = get_org_subscription_status(org_past)
        self.assertEqual(st_past["subscription_status"], "EXPIRED")
        self.assertTrue(st_past["is_blocked"])
        self.assertEqual(st_past["days_remaining"], 0)

        st_fut = get_org_subscription_status(org_fut)
        self.assertEqual(st_fut["subscription_status"], "ACTIVE")
        self.assertFalse(st_fut["is_blocked"])
        self.assertGreaterEqual(st_fut["days_remaining"], 4)

    # ── Phase 4: Email Delivery (465/587, Retries, Safe Logs, Queue) ──────────

    def test_05_email_delivery_465_fallback_to_587_and_no_secret_leak(self):
        from services.email_service import enqueue_email, get_email_queue_stats, send_email_sync

        smtp_secret = "SuperSecretSmtpPass_98765"
        orig_env = {k: os.environ.get(k) for k in ("RESEND_API_KEY", "SMTP_EMAIL", "SMTP_PASSWORD", "SMTP_PORT")}
        try:
            os.environ["RESEND_API_KEY"] = "re_prepfly_rotated_disabled"
            os.environ["SMTP_EMAIL"] = "noreply@prepfly.test"
            os.environ["SMTP_PASSWORD"] = smtp_secret
            os.environ["SMTP_PORT"] = "465"

            mock_tls_server = MagicMock()
            with patch("services.email_service.smtplib.SMTP_SSL", side_effect=TimeoutError("SSL 465 timeout")), \
                 patch("services.email_service.smtplib.SMTP") as mock_smtp, \
                 patch("services.email_service._resolve_ipv4_targets", return_value=["127.0.0.1"]):
                mock_smtp.return_value.__enter__.return_value = mock_tls_server

                with self.assertLogs("prepfly.email", level="INFO") as caplog:
                    ok = send_email_sync("user@example.com", "OTP Code", "<p>123456</p>", max_retries=1)

            self.assertTrue(ok)
            mock_tls_server.starttls.assert_called_once()
            mock_tls_server.send_message.assert_called_once()
            joined_logs = "\n".join(caplog.output)
            self.assertNotIn(smtp_secret, joined_logs)

            # Enqueue should return immediately without blocking caller even if SMTP unreachable
            with patch("services.email_service.send_email_sync", return_value=False):
                queued = enqueue_email("user@example.com", "Async Notice", "<p>Hi</p>")
            self.assertTrue(queued)
            self.assertGreaterEqual(get_email_queue_stats()["queued"], 1)
        finally:
            for k, v in orig_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    # ── Phase 5: Redis Health Check & Honest Local Memory Reporting ───────────

    def test_06_redis_health_check_never_claims_l1_is_distributed(self):
        from services.cache_service import RedisCacheBackend, TieredCacheManager

        mgr = TieredCacheManager()
        mgr.l2 = None
        stats_local = mgr.stats()
        self.assertFalse(stats_local["is_distributed"])
        self.assertEqual(stats_local["mode"], "l1_local_memory_fallback")

        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        h_body = res_health.get_json()
        self.assertIn("cache", h_body)
        self.assertIn("is_distributed", h_body["cache"])
        self.assertIn("rate_limiter_storage", h_body)

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        with patch("redis.from_url", return_value=mock_client):
            backend = RedisCacheBackend("rediss://default:secret@active.upstash.io:6379")
            hc = backend.health_check()
        self.assertTrue(hc["connected"])
        self.assertTrue(hc["is_distributed"])
        self.assertTrue(hc["tls_enabled"])
        self.assertNotIn("secret", hc["target"])

    # ── Phase 7: Cross-Endpoint Auth & Ownership Regression ───────────────────

    def test_07_core_routes_enforce_auth_and_tenant_isolation(self):
        self.assertEqual(self.client.get(f"/user-stats/{self.user_a}").status_code, 401)
        self.assertEqual(
            self.client.get(f"/user-stats/{self.user_a}", headers={"Authorization": f"Bearer {self.token_b}"}).status_code,
            403,
        )
        self.assertEqual(
            self.client.get("/user-stats/me", headers={"Authorization": f"Bearer {self.token_a}"}).status_code,
            200,
        )
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
            self.client.get(f"/subscription/status?org_id={self.org_a}", headers={"Authorization": f"Bearer {self.token_a}"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/notifications", headers={"Authorization": f"Bearer {self.token_a}"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/api/progress/weaknesses", headers={"Authorization": f"Bearer {self.token_a}"}).status_code,
            200,
        )
        self.assertEqual(
            self.client.post("/api/mentor/conversations", headers={"X-User-Id": self.user_a}, json={"title": "Check"}).status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()

