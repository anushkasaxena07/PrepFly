import io
import os
import smtplib
import ssl
import sys
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

import docx
import jwt
import pymupdf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key-for-unit-testing")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

import app as app_module
from app import app, supabase


def _make_jwt(sub, email, role="Student", org_id="org_remed"):
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "role": role,
        "aud": "authenticated",
        "organization_id": org_id,
    }
    return jwt.encode(payload, app_module._get_jwt_secret(), algorithm="HS256")


class TestProductionRemediationComprehensive(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.user_uuid = str(uuid.uuid4())
        self.token = _make_jwt(self.user_uuid, "candidate@prepfly.test", "Student")
        from services.resume_service import clear_resume_jobs_for_tests
        clear_resume_jobs_for_tests()

    # ── 1. Local Resume Extraction (PDF, DOCX, Empty, Corrupt, Encrypted, Scanned) ──

    def test_01_extract_valid_pdf_and_docx_and_normalize_whitespace(self):
        from services.resume_service import extract_resume_text_detailed

        with tempfile.TemporaryDirectory() as tmp:
            # Valid PDF
            pdf_path = os.path.join(tmp, "valid.pdf")
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Ananya   Rao\nSenior  Python\x00  Developer\nFlask   PostgreSQL   Redis")
            doc.save(pdf_path)
            doc.close()

            pdf_res = extract_resume_text_detailed(pdf_path, ext="pdf")
            self.assertEqual(pdf_res["extraction_method"], "pymupdf")
            self.assertEqual(pdf_res["page_count"], 1)
            self.assertIn("Ananya Rao", pdf_res["text"])
            self.assertNotIn("\x00", pdf_res["text"])

            # Valid DOCX
            docx_path = os.path.join(tmp, "valid.docx")
            d = docx.Document()
            d.add_paragraph("Rohan Mehta")
            d.add_paragraph("Built microservices in Python and FastAPI")
            d.save(docx_path)

            docx_res = extract_resume_text_detailed(docx_path, ext="docx")
            self.assertEqual(docx_res["extraction_method"], "python-docx")
            self.assertIn("Rohan Mehta", docx_res["text"])

    def test_02_extract_empty_corrupt_encrypted_and_scanned_pdfs(self):
        from services.resume_service import ResumeParseError, extract_resume_text_detailed

        # Empty file via upload route -> 400 non-retryable
        res_empty = self.client.post(
            "/api/resume/jobs",
            headers={"Authorization": f"Bearer {self.token}"},
            data={"resume": (io.BytesIO(b""), "empty.pdf"), "consent": "true"},
            content_type="multipart/form-data",
        )
        self.assertEqual(res_empty.status_code, 400)
        self.assertFalse(res_empty.get_json().get("retryable", True))

        with tempfile.TemporaryDirectory() as tmp:
            # Corrupt PDF
            corrupt_path = os.path.join(tmp, "corrupt.pdf")
            with open(corrupt_path, "wb") as fh:
                fh.write(b"%PDF-1.4\nnot valid pdf stream @@@")
            with self.assertRaises(ResumeParseError) as ctx_corrupt:
                extract_resume_text_detailed(corrupt_path, ext="pdf")
            self.assertEqual(ctx_corrupt.exception.details, "corrupt_pdf")
            self.assertFalse(ctx_corrupt.exception.retryable)

            # Encrypted PDF
            enc_path = os.path.join(tmp, "encrypted.pdf")
            enc_doc = pymupdf.open()
            enc_doc.new_page().insert_text((72, 72), "Secret Resume")
            enc_doc.save(enc_path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret123", owner_pw="owner123")
            enc_doc.close()
            with self.assertRaises(ResumeParseError) as ctx_enc:
                extract_resume_text_detailed(enc_path, ext="pdf")
            self.assertEqual(ctx_enc.exception.details, "encrypted_pdf")
            self.assertFalse(ctx_enc.exception.retryable)

            # Image-only / blank scanned PDF
            scan_path = os.path.join(tmp, "scanned.pdf")
            scan_doc = pymupdf.open()
            scan_doc.new_page()
            scan_doc.save(scan_path)
            scan_doc.close()
            with patch("services.resume_service._try_ocr_pdf_pages", return_value=""):
                with self.assertRaises(ResumeParseError) as ctx_scan:
                    extract_resume_text_detailed(scan_path, ext="pdf")
            self.assertEqual(ctx_scan.exception.details, "scanned_pdf")
            self.assertEqual(ctx_scan.exception.status_code, 422)
            self.assertFalse(ctx_scan.exception.retryable)

    # ── 2. Gemini Retry, Fallback, Permanent Errors & Validation ──

    @patch("time.sleep", return_value=None)
    def test_03_gemini_429_retry_after_503_504_and_permanent_error(self, mock_sleep):
        from services.resume_service import ResumeParseError, parse_resume_content

        # 429 with Retry-After succeeds on second attempt
        rate_err = RuntimeError("429 RESOURCE_EXHAUSTED: Quota exceeded. retry after 0.25s")
        ok_resp = MagicMock()
        ok_resp.content = '{"full_name":"Kavya","email":"","phone":"","skills":["Python","SQL"],"projects":[],"experience":[],"education":[],"certifications":[],"achievements":[],"ats_score":81,"missing_info":[]}'

        m_429 = MagicMock()
        m_429.model = "gemini-2.5-flash"
        m_429.invoke.side_effect = [rate_err, ok_resp]
        parsed = parse_resume_content(f"Kavya Resume {uuid.uuid4().hex}\nPython SQL", m_429)
        self.assertEqual(parsed["structured_data"]["skills"], ["Python", "SQL"])
        self.assertEqual(m_429.invoke.call_count, 2)
        self.assertTrue(mock_sleep.called)

        # Permanent API key error fails fast on 1st attempt without retrying
        perm_err = RuntimeError("401 API_KEY_INVALID: API key not valid")
        m_perm = MagicMock()
        m_perm.model = "gemini-2.5-flash"
        m_perm.invoke.side_effect = perm_err
        with self.assertRaises(ResumeParseError) as ctx_perm:
            parse_resume_content(f"Perm Error {uuid.uuid4().hex}\nJava", m_perm)
        self.assertFalse(ctx_perm.exception.retryable)
        self.assertEqual(m_perm.invoke.call_count, 1)

    @patch("time.sleep", return_value=None)
    def test_04_primary_transient_failure_falls_back_to_secondary_model(self, _mock_sleep):
        from services.resume_service import parse_resume_content

        primary = MagicMock()
        primary.model = "gemini-2.5-flash"
        primary.invoke.side_effect = TimeoutError("504 DEADLINE_EXCEEDED")

        fallback_ok = MagicMock()
        fb_resp = MagicMock()
        fb_resp.content = '{"full_name":"Arjun","skills":["Go","Kubernetes"],"ats_score":87,"missing_info":[]}'
        fallback_ok.invoke.return_value = fb_resp

        factory = MagicMock(return_value=fallback_ok)
        with patch("services.ai_service.get_fallback_gemini_models", return_value=["gemini-3.5-flash-lite"]):
            result = parse_resume_content(
                f"Fallback Test {uuid.uuid4().hex}\nArjun Go Kubernetes",
                primary,
                fallback_client_factory=factory,
            )

        self.assertEqual(result["model_used"], "gemini-3.5-flash-lite")
        self.assertEqual(result["structured_data"]["skills"], ["Go", "Kubernetes"])
        self.assertEqual(primary.invoke.call_count, 3)
        factory.assert_called_once()

        # Verify default primary/fallback list contains no shut-down gemini-2.0-flash
        from services.ai_service import get_configured_gemini_candidates
        self.assertNotIn("gemini-2.0-flash", get_configured_gemini_candidates())

    @patch("time.sleep", return_value=None)
    def test_05_truncated_json_schema_validation_and_persistence_failure(self, _mock_sleep):
        from services.resume_service import ResumeParseError, parse_resume_content

        # Truncated JSON fails loudly cleanly
        m_trunc = MagicMock()
        m_trunc.model = "gemini-2.5-flash"
        trunc_resp = MagicMock()
        trunc_resp.content = '```json\n{"full_name":"Truncated","skills":["Python"'
        m_trunc.invoke.return_value = trunc_resp
        with self.assertRaises(ResumeParseError):
            parse_resume_content(f"Truncated {uuid.uuid4().hex}\nPython", m_trunc)

        # DB persistence failure blocks completed when require_persistence=True
        m_ok = MagicMock()
        m_ok.model = "gemini-2.5-flash"
        ok_resp = MagicMock()
        ok_resp.content = '{"full_name":"Persist Fail","skills":["React"],"ats_score":80,"missing_info":[]}'
        m_ok.invoke.return_value = ok_resp
        with patch("services.resume_service.save_cached_resume", return_value=False):
            with self.assertRaises(ResumeParseError) as ctx_db:
                parse_resume_content(f"Persist {uuid.uuid4().hex}\nReact", m_ok, require_persistence=True)
        self.assertEqual(ctx_db.exception.details, "persistence_failed")

    def test_06_async_job_retry_without_reupload_and_worker_crash_recovery(self):
        from services.resume_service import (
            create_resume_parse_job,
            get_resume_parse_job,
            retry_resume_parse_job,
        )

        # Transient failure preserves extracted payload -> retry_resume_parse_job succeeds without reupload
        bad_model = MagicMock()
        bad_model.model = "gemini-2.5-flash"
        bad_model.invoke.side_effect = RuntimeError("503 UNAVAILABLE")
        raw_txt = f"Retry Without Reupload {uuid.uuid4().hex}\nPriya Python Docker"

        job = create_resume_parse_job(raw_txt, bad_model, user_id=self.user_uuid, create_session=False, run_async=False)
        self.assertEqual(job["status"], "retryable_failed")
        self.assertTrue(job["retryable"])

        good_model = MagicMock()
        good_model.model = "gemini-2.5-flash"
        good_resp = MagicMock()
        good_resp.content = '{"full_name":"Priya","skills":["Python","Docker"],"ats_score":85,"missing_info":[]}'
        good_model.invoke.return_value = good_resp

        orig_cm = app_module.chat_model
        try:
            app_module.chat_model = good_model
            res_retry = self.client.post(
                f"/api/resume/jobs/{job['job_id']}/retry",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.assertEqual(res_retry.status_code, 202)
            # Poll until completed
            final_state = None
            for _ in range(40):
                final_state = get_resume_parse_job(job["job_id"])
                if final_state["status"] in ("completed", "retryable_failed", "permanently_failed"):
                    break
                import time as _t
                _t.sleep(0.03)
            self.assertEqual(final_state["status"], "completed")
            self.assertEqual(final_state["attempts"], 2)
        finally:
            app_module.chat_model = orig_cm

        # Anonymous job requires creator X-Job-Token (blocks unauthenticated IDOR)
        from services.resume_service import create_resume_parse_job
        anon_job = create_resume_parse_job(
            f"Anon Resume {uuid.uuid4().hex}\nPython Flask",
            bad_model,
            user_id=None,
            create_session=False,
            run_async=False,
        )
        self.assertTrue(anon_job.get("job_token"))
        self.assertEqual(self.client.get(f"/api/resume/jobs/{anon_job['job_id']}").status_code, 401)
        self.assertEqual(
            self.client.get(
                f"/api/resume/jobs/{anon_job['job_id']}",
                headers={"X-Job-Token": anon_job["job_token"]},
            ).status_code,
            200,
        )

        # Payment activation succeeds cleanly even if optional activity_logs write fails
        import services.payment_service as payment_svc
        import hmac, hashlib
        org_p = f"org_paylog_{uuid.uuid4().hex[:6]}"
        supabase.table("organization").insert({"id": org_p, "name": "Pay Log Org", "subscription_status": "TRIAL"}).execute()
        order_id = f"order_{uuid.uuid4().hex[:8]}"
        pay_id = f"pay_{uuid.uuid4().hex[:8]}"
        secret = "test_razorpay_secret_for_testing"
        sig = hmac.new(secret.encode(), f"{order_id}|{pay_id}".encode(), hashlib.sha256).hexdigest()
        orig_tbl_p = supabase.table
        def _boom_act_pay(name):
            if name == "activity_logs":
                raise RuntimeError("Simulated activity_logs error during payment")
            return orig_tbl_p(name)
        with patch.object(payment_svc, "RAZORPAY_KEY_SECRET", secret), \
             patch.object(supabase, "table", side_effect=_boom_act_pay):
            pay_res = payment_svc.verify_razorpay_payment(org_p, order_id, pay_id, sig, plan_id="ENTERPRISE_YEARLY")
        self.assertEqual(pay_res["status"], "SUCCESS")

        # Worker crash recovery (unexpected BaseException/RuntimeError in parse_resume_content)
        with patch("services.resume_service.parse_resume_content", side_effect=RuntimeError("Worker OOM simulation")):
            crashed = create_resume_parse_job(
                f"Worker Crash {uuid.uuid4().hex}\nJava",
                good_model,
                user_id=self.user_uuid,
                create_session=False,
                run_async=False,
            )
        self.assertEqual(crashed["status"], "retryable_failed")

    # ── 3. Activity Log UUID Type Safety ──

    def test_07_activity_logs_never_put_email_or_anonymous_in_uuid_actor_id(self):
        from services.identity_service import parse_valid_uuid
        from services.interview_reliability_service import record_report_audit_log

        self.assertEqual(parse_valid_uuid(self.user_uuid), self.user_uuid)
        self.assertIsNone(parse_valid_uuid("anushka.gghs@gmail.com"))
        self.assertIsNone(parse_valid_uuid("anonymous"))
        self.assertIsNone(parse_valid_uuid(""))
        self.assertIsNone(parse_valid_uuid(None))

        # Seed user with UUID id and email
        test_email = f"uuidtest_{uuid.uuid4().hex[:6]}@prepfly.test"
        supabase.table("users").insert({
            "id": self.user_uuid,
            "name": "UUID Test User",
            "email": test_email,
            "password": "hashed_password",
            "role": "Student",
        }).execute()

        # Case A: Known user UUID resolved cleanly from email lookup
        app_module.log_authentication(test_email, "email_password", True, "127.0.0.1")
        logs_a = supabase.table("activity_logs").select("*").eq("user_id", test_email).execute().data or []
        self.assertGreaterEqual(len(logs_a), 1)
        self.assertEqual(logs_a[-1]["actor_id"], self.user_uuid)

        # Case B: Unknown email -> actor_id MUST be None (not email!), user_id stores text email
        unknown_email = "unregistered.user@gmail.com"
        app_module.log_authentication(unknown_email, "email_password", False, "127.0.0.1")
        logs_b = supabase.table("activity_logs").select("*").eq("user_id", unknown_email).execute().data or []
        self.assertGreaterEqual(len(logs_b), 1)
        self.assertIsNone(logs_b[-1]["actor_id"])

        # Case C: record_report_audit_log with "anonymous" -> actor_id None
        audit = record_report_audit_log(None, f"sess_{uuid.uuid4().hex[:6]}", actor_id="anonymous", report_status="complete")
        self.assertIsNone(audit["actor_id"])
        self.assertEqual(audit["user_id"], "anonymous")

        # Case D: Login continues even if activity_logs write raises inside logger
        with patch.object(supabase, "table", wraps=supabase.table) as wrapped_tbl:
            orig_table = supabase.table
            def _boom_on_activity(name):
                if name == "activity_logs":
                    raise RuntimeError("Simulated 503 activity_logs failure")
                return orig_table(name)
            wrapped_tbl.side_effect = _boom_on_activity
            # Must not raise!
            app_module.log_authentication(unknown_email, "email_password", True, "127.0.0.1")

    # ── 4. Schema Self-Check Classification (Drift vs Stale Cache vs Connectivity) ──

    def test_08_schema_self_check_classifies_unavailable_timeout_permission_and_stale_cache(self):
        from services.schema_check_service import REQUIRED_SCHEMA, verify_database_schema

        def _make_mock_sb(side_effect_fn):
            sb = MagicMock()
            sb._local_client = None
            real = MagicMock()
            def tbl(name):
                qb = MagicMock()
                def sel(cols):
                    inner = MagicMock()
                    def lim(n):
                        leaf = MagicMock()
                        leaf.execute.side_effect = lambda: side_effect_fn(name, cols)
                        return leaf
                    inner.limit.side_effect = lim
                    return inner
                qb.select.side_effect = sel
                return qb
            real.table.side_effect = tbl
            sb._real_client = real
            return sb

        # 1. Timeout must NOT falsely report missing columns
        sb_timeout = _make_mock_sb(lambda _n, _c: (_ for _ in ()).throw(TimeoutError("statement timeout")))
        rep_to = verify_database_schema(sb_timeout)
        self.assertFalse(rep_to["ok"])
        self.assertEqual(rep_to["status"], "timeout")
        self.assertFalse(rep_to["drift_detected"])
        self.assertEqual(rep_to["missing"], {})

        # 2. Permission denied (401/42501) must NOT report missing columns
        sb_perm = _make_mock_sb(lambda _n, _c: (_ for _ in ()).throw(RuntimeError("42501 permission denied for table sessions")))
        rep_perm = verify_database_schema(sb_perm)
        self.assertEqual(rep_perm["status"], "permission_denied")
        self.assertFalse(rep_perm["drift_detected"])
        self.assertEqual(rep_perm["missing"], {})

        # 3. Supabase unavailable (503) must NOT report missing columns
        sb_down = _make_mock_sb(lambda _n, _c: (_ for _ in ()).throw(RuntimeError("503 Service Unavailable")))
        rep_down = verify_database_schema(sb_down)
        self.assertEqual(rep_down["status"], "unavailable")
        self.assertFalse(rep_down["drift_detected"])
        self.assertEqual(rep_down["missing"], {})

        # 4. Stale PostgREST cache: PG metadata confirms all columns exist while PostgREST returns PGRST204
        sb_stale = _make_mock_sb(lambda t, c: (_ for _ in ()).throw(RuntimeError("PGRST204: Could not find column")) if t == "interview_turns" else MagicMock(data=[]))
        rep_stale = verify_database_schema(sb_stale, metadata_fetcher=lambda t: list(REQUIRED_SCHEMA.get(t, [])))
        self.assertEqual(rep_stale["status"], "stale_cache")
        self.assertFalse(rep_stale["drift_detected"])
        self.assertIn("interview_turns", rep_stale["stale_cache"])

    # ── 5. Redis TLS, DNS, Timeout, TLS Error, Fallback & Rate Limiter ──

    def test_09_redis_dns_timeout_tls_errors_and_secret_redaction(self):
        from services.cache_service import RedisCacheBackend, validate_redis_config

        cfg = validate_redis_config("redis://default:SuperSecret@good.upstash.io:6379")
        self.assertTrue(cfg["valid"])
        self.assertTrue(cfg["tls_enabled"])
        self.assertNotIn("SuperSecret", cfg["target"])

        # DNS failure fails fast on first attempt cleanly
        with patch("redis.from_url", side_effect=OSError("[Errno -2] Name or service not known")) as m_from:
            b_dns = RedisCacheBackend("rediss://default:SecretPw@dead.upstash.io:6379", max_connect_retries=2)
        self.assertFalse(b_dns.is_connected)
        self.assertEqual(b_dns.last_error_type, "dns_error")
        self.assertEqual(m_from.call_count, 1)

        # TLS error classifies as tls_error without looping retries
        with patch("redis.from_url", side_effect=ssl.SSLError("TLS handshake failed")) as m_tls:
            b_tls = RedisCacheBackend("rediss://default:SecretPw@tls.upstash.io:6379", max_connect_retries=2)
        self.assertFalse(b_tls.is_connected)
        self.assertEqual(b_tls.last_error_type, "tls_error")
        self.assertEqual(m_tls.call_count, 1)

        # Health endpoint and rate-limited endpoint stay responsive even when Redis is unreachable
        self.assertEqual(self.client.get("/health").status_code, 200)

    # ── 6. Email Auth Failure, Retryable Transient Error & Secret Protection ──

    def test_10_email_auth_permanent_vs_transient_retry(self):
        from services.email_service import send_email_with_status

        orig = {k: os.environ.get(k) for k in ("RESEND_API_KEY", "SMTP_EMAIL", "SMTP_PASSWORD", "SMTP_HOST", "SMTP_SERVER", "SMTP_PORT")}
        try:
            os.environ["RESEND_API_KEY"] = "re_prepfly_rotated_disabled"
            os.environ["SMTP_EMAIL"] = "noreply@prepfly.test"
            os.environ["SMTP_PASSWORD"] = "TopSecretSmtp99!"
            os.environ["SMTP_HOST"] = "mail.example.test"
            os.environ["SMTP_PORT"] = "587"

            # Permanent SMTP authentication failure must NOT retry multiple attempts
            with patch("services.email_service._resolve_ipv4_targets", return_value=["127.0.0.1"]), \
                 patch("services.email_service.smtplib.SMTP") as mock_smtp:
                inst = MagicMock()
                inst.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed")
                mock_smtp.return_value.__enter__.return_value = inst
                with self.assertLogs("prepfly.email", level="INFO") as caplog:
                    res_auth = send_email_with_status("user@example.com", "Login OTP", "<p>112233</p>", max_retries=3)
            self.assertFalse(res_auth["ok"])
            self.assertFalse(res_auth["retryable"])
            self.assertEqual(res_auth["attempts"], 1)
            self.assertNotIn("TopSecretSmtp99!", "\n".join(caplog.output))
            self.assertNotIn("112233", "\n".join(caplog.output))

            # Transient 421 error retries and succeeds cleanly on attempt 2
            with patch("services.email_service._resolve_ipv4_targets", return_value=["127.0.0.1"]), \
                 patch("services.email_service.time.sleep", return_value=None), \
                 patch("services.email_service.smtplib.SMTP") as mock_smtp:
                inst2 = MagicMock()
                inst2.send_message.side_effect = [smtplib.SMTPResponseException(421, b"Try again later"), None]
                mock_smtp.return_value.__enter__.return_value = inst2
                res_ok = send_email_with_status("user@example.com", "Login OTP", "<p>998877</p>", max_retries=2)
            self.assertTrue(res_ok["ok"])
            self.assertEqual(res_ok["attempts"], 2)
        finally:
            for k, v in orig.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    # ── 7. End-to-End Production Fallback Proof (503 / 504 -> Fallback -> Completed) ──

    def test_11_resume_jobs_503_and_504_invoke_fallback_and_complete_without_poll_retrigger(self):
        import time as _t
        from services.resume_service import clear_resume_jobs_for_tests

        class FakeProdPrimaryClient:
            def __init__(self, fail_err):
                self.model = "gemini-3.8-flash"
                self.google_api_key = "fake-prod-key-for-offline-test"
                self.calls = 0
                self._fail_err = fail_err

            def invoke(self, _messages):
                self.calls += 1
                raise self._fail_err

        class FakeFallbackClient:
            def __init__(self, model_name):
                self.model = model_name
                self.calls = 0

            def invoke(self, _messages):
                self.calls += 1
                resp = MagicMock()
                resp.content = '{"full_name":"Meera Nair","email":"meera@ex.com","skills":["Python","FastAPI","PostgreSQL"],"projects":[],"experience":[],"education":[],"certifications":[],"achievements":[],"ats_score":89,"missing_info":[]}'
                return resp

        for case_label, err_obj in (
            ("503", RuntimeError("503 UNAVAILABLE")),
            ("504", TimeoutError("504 DEADLINE_EXCEEDED")),
        ):
            pdf_buf = io.BytesIO()
            doc = pymupdf.open()
            doc.new_page().insert_text((72, 72), f"Meera Nair ({case_label} {uuid.uuid4().hex[:6]})\nSenior Backend Engineer\nPython FastAPI PostgreSQL Redis Docker")
            doc.save(pdf_buf)
            raw_pdf_bytes = pdf_buf.getvalue()

            clear_resume_jobs_for_tests()
            primary = FakeProdPrimaryClient(err_obj)
            fallback_instances = []

            def _make_fb(model_name, _api_key, **_kwargs):
                c = FakeFallbackClient(model_name)
                fallback_instances.append(c)
                return c

            orig_cm = app_module.chat_model
            orig_key = os.environ.get("GEMINI_API_KEY")
            try:
                app_module.chat_model = primary
                os.environ["GEMINI_API_KEY"] = "fake-prod-key-for-offline-test"
                with patch("services.ai_service.is_test_gemini_key", return_value=False), \
                     patch("services.ai_service.discover_gemini_flash_models", return_value=[]), \
                     patch("services.ai_service.create_gemini_client", side_effect=_make_fb):
                    res_post = self.client.post(
                        "/api/resume/jobs",
                        headers={"Authorization": f"Bearer {self.token}"},
                        data={"resume": (io.BytesIO(raw_pdf_bytes), f"meera_{case_label}.pdf"), "consent": "true"},
                        content_type="multipart/form-data",
                    )
                    self.assertEqual(res_post.status_code, 202)
                    job_id = res_post.get_json()["job_id"]

                    # Repeated polling waits for completion and never triggers additional Gemini calls
                    job_state = None
                    for _ in range(80):
                        poll = self.client.get(
                            f"/api/resume/jobs/{job_id}",
                            headers={"Authorization": f"Bearer {self.token}"},
                        )
                        self.assertEqual(poll.status_code, 200)
                        job_state = poll.get_json()
                        if job_state["status"] in ("completed", "retryable_failed", "permanently_failed"):
                            break
                        _t.sleep(0.05)

                    self.assertEqual(job_state["status"], "completed", f"Expected completed on {case_label}, got {job_state}")
                    self.assertEqual(job_state["model_used"], "gemini-3.5-flash-lite")
                    self.assertTrue(job_state.get("session_id"))

                    # 5 extra polls on completed job must trigger zero additional primary/fallback Gemini calls
                    calls_before_polls = (primary.calls, sum(c.calls for c in fallback_instances))
                    for _ in range(5):
                        extra = self.client.get(
                            f"/api/resume/jobs/{job_id}",
                            headers={"Authorization": f"Bearer {self.token}"},
                        )
                        self.assertEqual(extra.status_code, 200)
                    calls_after_polls = (primary.calls, sum(c.calls for c in fallback_instances))
                    self.assertEqual(calls_before_polls, calls_after_polls)
                    self.assertGreaterEqual(len(fallback_instances), 1)
                    self.assertEqual(fallback_instances[0].calls, 1)
            finally:
                app_module.chat_model = orig_cm
                if orig_key is None:
                    os.environ.pop("GEMINI_API_KEY", None)
                else:
                    os.environ["GEMINI_API_KEY"] = orig_key

    def test_12_resume_job_persistence_failure_blocks_completed_ocr_and_tenant_isolation(self):
        from services.resume_service import (
            clear_resume_jobs_for_tests,
            create_resume_parse_job,
            extract_resume_text_detailed,
            parse_resume_content,
        )

        # Persistence failure inside _run_resume_job must mark job retryable_failed, NEVER completed
        clear_resume_jobs_for_tests()
        ok_model = MagicMock()
        ok_model.model = "gemini-3.8-flash"
        ok_resp = MagicMock()
        ok_resp.content = '{"full_name":"Dev","skills":["Python","SQL"],"ats_score":82,"missing_info":[]}'
        ok_model.invoke.return_value = ok_resp

        with patch("services.resume_service.save_cached_resume", return_value=False):
            failed_job = create_resume_parse_job(
                f"Persist Fail Job {uuid.uuid4().hex}\nPython SQL",
                ok_model,
                user_id=self.user_uuid,
                org_id="org_remed",
                create_session=False,
                run_async=False,
            )
        self.assertEqual(failed_job["status"], "retryable_failed")
        self.assertTrue(failed_job["retryable"])

        # Cross-user and cross-org ADMIN cannot retry or view another user's job
        other_user_tok = _make_jwt(str(uuid.uuid4()), "other@prepfly.test", "Student", org_id="org_remed")
        other_org_admin_tok = _make_jwt(str(uuid.uuid4()), "admin@other.test", "ADMIN", org_id="org_other")
        self.assertEqual(
            self.client.post(f"/api/resume/jobs/{failed_job['job_id']}/retry", headers={"Authorization": f"Bearer {other_user_tok}"}).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(f"/api/resume/jobs/{failed_job['job_id']}/retry", headers={"Authorization": f"Bearer {other_org_admin_tok}"}).status_code,
            403,
        )

        # Controlled JSON repair prompt recovers malformed 1st response cleanly
        bad_then_good = MagicMock()
        bad_then_good.model = "gemini-3.8-flash"
        bad_r = MagicMock()
        bad_r.content = '{"full_name":"Broken'
        good_r = MagicMock()
        good_r.content = '{"full_name":"Repaired Dev","skills":["Go"],"ats_score":80,"missing_info":[]}'
        bad_then_good.invoke.side_effect = [bad_r, good_r]
        repaired = parse_resume_content(f"JSON Repair {uuid.uuid4().hex}\nGo developer", bad_then_good)
        self.assertEqual(repaired["structured_data"]["full_name"], "Repaired Dev")
        self.assertEqual(bad_then_good.invoke.call_count, 2)

        # Low-text scanned PDF (< 40 chars scanner watermark) invokes OCR fallback
        with tempfile.TemporaryDirectory() as tmp:
            low_pdf = os.path.join(tmp, "low_text_scan.pdf")
            d = pymupdf.open()
            d.new_page().insert_text((72, 72), "Img01")
            d.save(low_pdf)
            d.close()
            with patch("services.resume_service._try_ocr_pdf_pages", return_value="Anita Sharma Python Docker PostgreSQL Senior Engineer"):
                ocr_res = extract_resume_text_detailed(low_pdf, ext="pdf")
            self.assertTrue(ocr_res["ocr_used"])
            self.assertEqual(ocr_res["extraction_method"], "pymupdf_ocr")
            self.assertIn("Anita Sharma", ocr_res["text"])

        # Migration 011 includes idempotent interview_turns.skill_id column repair
        mig011_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations", "011_fix_live_supabase_schema.sql")
        with open(mig011_path, "r", encoding="utf-8") as mf:
            mig011_sql = mf.read()
        self.assertIn("interview_turns ADD COLUMN IF NOT EXISTS skill_id TEXT", mig011_sql)


if __name__ == "__main__":
    unittest.main()

