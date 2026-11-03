"""
Security Regression Test Suite
Automated regression tests for confirmed pentest findings #1 to #11.
"""

import unittest
import json
import os
import sys
import io
import uuid
import jwt
from collections import Counter
import re

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ensure default test environment variables if not present
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key-for-unit-testing")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_dummy_id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test_razorpay_secret_for_testing")
os.environ.setdefault("SMTP_EMAIL", "test@prepfly.io")
os.environ.setdefault("SMTP_PASSWORD", "test-smtp-password")

from app import app, supabase, _get_jwt_secret

class TestSecurityRegressions(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_01_master_otps_rejected_across_all_auth_flows(self):
        """1. OTP 123456 and 981103 return 401 for login, signup, and reset."""
        for code in ["123456", "981103"]:
            with self.subTest(otp=code):
                # Signup OTP verification
                res_signup = self.client.post("/auth/verify-signup-otp", json={
                    "email": "victim_user_test@prepfly.io",
                    "otp": code
                })
                self.assertEqual(res_signup.status_code, 401, f"Master OTP {code} was accepted in signup!")

                # Login OTP verification
                res_login = self.client.post("/auth/verify-login-otp", json={
                    "email": "victim_user_test@prepfly.io",
                    "otp": code
                })
                self.assertEqual(res_login.status_code, 401, f"Master OTP {code} was accepted in login!")

                # Reset OTP verification
                res_reset = self.client.post("/auth/verify-reset-otp", json={
                    "email": "victim_user_test@prepfly.io",
                    "otp": code
                })
                self.assertEqual(res_reset.status_code, 401, f"Master OTP {code} was accepted in password reset!")

    def test_02_superadmin_login_rejects_wrong_password(self):
        """2. Superadmin login with a wrong password returns 401, even with no DB row."""
        res = self.client.post("/api/superadmin/login", json={
            "email": "saxenaanushka9645@gmail.com",
            "password": "wrong_attacker_password_xyz"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertNotIn("access_token", data)

    def test_03_token_signed_with_weak_or_hardcoded_keys_rejected(self):
        """3. A token signed with hardcoded keys (e.g. super-secret-key-123) returns 401."""
        for bad_secret in ["super-secret-key-123", "prepfly-super-secret-jwt-signature-key-2026-secure-32byte-min", "secret"]:
            with self.subTest(secret=bad_secret):
                if bad_secret == _get_jwt_secret():
                    continue  # skip if matches current real secret
                forged_token = jwt.encode(
                    {"sub": "attacker_user_1", "role": "SUPER_ADMIN"},
                    bad_secret,
                    algorithm="HS256"
                )
                res = self.client.put(
                    "/update-profile",
                    headers={"Authorization": f"Bearer {forged_token}"},
                    json={"name": "Hacked Profile"}
                )
                self.assertEqual(res.status_code, 401)

    def test_04_header_and_string_admin_spoofing_rejected(self):
        """4. X-Super-Admin: true, X-User-Role: SUPER_ADMIN and Bearer superadmin_x return 401/403."""
        # 1. Header X-Super-Admin: true
        res_h1 = self.client.get("/api/superadmin/dashboard", headers={"X-Super-Admin": "true"})
        self.assertIn(res_h1.status_code, (401, 403))

        # 2. Header X-User-Role: SUPER_ADMIN
        res_h2 = self.client.get("/api/superadmin/dashboard", headers={"X-User-Role": "SUPER_ADMIN"})
        self.assertIn(res_h2.status_code, (401, 403))

        # 3. String-based bearer token containing 'superadmin'
        res_b = self.client.get("/api/superadmin/dashboard", headers={"Authorization": "Bearer superadmin_fake_token"})
        self.assertIn(res_b.status_code, (401, 403))

    def test_05_payment_verify_bad_signature_rejected(self):
        """5. /api/payment/verify with a bad signature returns 400 and activates nothing."""
        res = self.client.post("/api/payment/verify", json={
            "organization_id": "org_victim_test",
            "razorpay_order_id": "order_test_999",
            "razorpay_payment_id": "pay_test_999",
            "razorpay_signature": "invalid_forged_signature_123"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_06_role_escalation_in_update_profile_rejected(self):
        """6. PUT /update-profile with {'role': 'ADMIN'} as a candidate returns 403."""
        candidate_token = jwt.encode(
            {"sub": "cand_user_101", "role": "candidate", "email": "cand@prepfly.test"},
            _get_jwt_secret(),
            algorithm="HS256"
        )
        res = self.client.put(
            "/update-profile",
            headers={"Authorization": f"Bearer {candidate_token}"},
            json={"role": "ADMIN"}
        )
        self.assertEqual(res.status_code, 403)

    def test_07_idor_session_ownership_enforced(self):
        """7. User A requesting User B's session returns 404/401."""
        user_a_token = jwt.encode({"sub": "user_A_123", "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        user_b_token = jwt.encode({"sub": "user_B_456", "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")

        # User A creates a session
        create_res = self.client.post(
            "/create-session-no-resume",
            headers={"Authorization": f"Bearer {user_a_token}"},
            json={"role": "Software Engineer", "consent": True}
        )
        session_id = create_res.get_json().get("session_id")
        self.assertIsNotNone(session_id)

        # User B attempts to access User A's session
        get_res = self.client.get(
            f"/get-session?session_id={session_id}",
            headers={"Authorization": f"Bearer {user_b_token}"}
        )
        self.assertIn(get_res.status_code, (401, 404))

        # Unauthenticated access to User A's session
        unauth_res = self.client.get(f"/get-session?session_id={session_id}")
        self.assertIn(unauth_res.status_code, (401, 404))

    def test_08_admin_tenant_isolation_and_auth_enforced(self):
        """8. /api/admin/students with no token returns 401/403, and org A cannot query org B."""
        # Unauthenticated request
        unauth = self.client.get("/api/admin/students")
        self.assertIn(unauth.status_code, (401, 403))

        # Org A admin token
        org_a_token = jwt.encode(
            {"sub": "admin_a", "role": "Organization Admin", "organization_id": "org_A_unique"},
            _get_jwt_secret(),
            algorithm="HS256"
        )
        # Attempt to spoof X-Organization-Id: org_B_spoof
        res_spoof = self.client.get(
            "/api/admin/students",
            headers={
                "Authorization": f"Bearer {org_a_token}",
                "X-Organization-Id": "org_B_spoof"
            }
        )
        # Should not leak org B data
        self.assertIn(res_spoof.status_code, (200, 403))
        if res_spoof.status_code == 200:
            data = res_spoof.get_json()
            # If any students returned, none must belong to org_B_spoof
            students = data.get("students", data if isinstance(data, list) else [])
            for st in students:
                self.assertNotEqual(st.get("organization_id"), "org_B_spoof")

    def test_09_path_traversal_in_save_recording_blocked(self):
        """9. /save-recording with session_id=../x returns 400."""
        user_token = jwt.encode({"sub": "user_rec", "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        res = self.client.post(
            "/save-recording",
            headers={"Authorization": f"Bearer {user_token}"},
            data={
                "session_id": "../traversal_attack",
                "file": (io.BytesIO(b"dummy video data"), "recording.webm")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)

    def test_10_disallowed_file_types_rejected_on_upload(self):
        """10. Uploading .html or executable scripts is rejected with 400."""
        user_token = jwt.encode({"sub": "user_upload", "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        for bad_filename in ["payload.html", "exploit.htm", "script.svg", "malware.exe"]:
            with self.subTest(filename=bad_filename):
                res = self.client.post(
                    "/api/support/upload",
                    headers={"Authorization": f"Bearer {user_token}"},
                    data={"file": (io.BytesIO(b"<script>alert(1)</script>"), bad_filename)},
                    content_type="multipart/form-data"
                )
                self.assertIn(res.status_code, (400, 403))

    def test_11_no_duplicate_routes_exist_in_url_map(self):
        """11. The URL map contains zero duplicate route registrations."""
        route_counter = Counter((r.rule, m) for r in app.url_map.iter_rules() for m in r.methods)
        duplicates = [k for k, v in route_counter.items() if v > 1]
        self.assertEqual(len(duplicates), 0, f"Found duplicate route definitions: {duplicates}")

    def test_12_no_sensitive_leftover_literals_in_source(self):
        """12. Automated scan: app.py, services/*.py, payment.py contain zero leaked secret or backdoor literals."""
        pattern = re.compile(r"981103|123456|super-secret|admin123|aditya123|X-Super-Admin|X-User-Role|AIzaSy|re_A24|mdpqnpueuhjlgzcd|rzp_test_|sb_publishable")
        f_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        target_files = [os.path.join(f_backend_dir, "app.py"), os.path.join(f_backend_dir, "payment.py")]
        services_dir = os.path.join(f_backend_dir, "services")
        if os.path.isdir(services_dir):
            for fname in os.listdir(services_dir):
                if fname.endswith(".py"):
                    target_files.append(os.path.join(services_dir, fname))

        violations = []
        for fpath in target_files:
            if not os.path.exists(fpath):
                continue
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, 1):
                    match = pattern.search(line)
                    if match:
                        violations.append(f"{os.path.basename(fpath)}:{idx} -> matched '{match.group(0)}': {line.strip()[:80]}")

        self.assertEqual(len(violations), 0, f"Found sensitive leftover literals in code:\n" + "\n".join(violations))

    def test_13_otp_brute_force_lockout_after_five_failed_attempts(self):
        """13. Attempting 5 invalid OTPs locks out the account and immediately invalidates the active OTP."""
        from app import store_otp
        target_email = "bruteforce_victim@test.org"
        valid_otp = "849201"
        store_otp(target_email, valid_otp, purpose="login")

        # 5 failed verification attempts
        for attempt in range(1, 6):
            res = self.client.post("/auth/verify-login-otp", json={
                "email": target_email,
                "otp": f"00000{attempt}"
            })
            self.assertEqual(res.status_code, 401)

        # The 6th attempt (even with the correct OTP) must be rejected due to lockout
        correct_res = self.client.post("/auth/verify-login-otp", json={
            "email": target_email,
            "otp": valid_otp
        })
        self.assertEqual(correct_res.status_code, 401)
        data = correct_res.get_json()
        self.assertIn("Locked", data.get("error", ""))

    def test_14_filter_injection_in_student_coding_tests_blocked(self):
        """14. PostgREST/SQLite filter injection in /api/student/coding-tests is rejected with 400."""
        malicious_org = "org_1,role.eq.admin"
        res = self.client.get(
            "/api/student/coding-tests",
            headers={"X-Organization-Id": malicious_org}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid organization ID format", res.get_json().get("error", ""))

    def test_15_code_execution_entry_points_fail_closed(self):
        """15. /run-code and /api/coding/submit fail closed (401 without auth, 503 without sandbox container)."""
        candidate_token = jwt.encode(
            {"sub": "cand_runner", "role": "candidate"},
            _get_jwt_secret(),
            algorithm="HS256"
        )
        for endpoint in ["/run-code", "/api/run-code", "/api/coding/submit", "/coding/run"]:
            with self.subTest(endpoint=endpoint):
                # 1. Unauthenticated request -> 401
                unauth_res = self.client.post(endpoint, json={"code": "print('hello')", "language": "python"})
                self.assertEqual(unauth_res.status_code, 401)

                # 2. Authenticated request -> 503 (sandbox worker required)
                auth_res = self.client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {candidate_token}"},
                    json={"code": "print('hello')", "language": "python"}
                )
                self.assertEqual(auth_res.status_code, 503)
                self.assertIn("isolated sandbox", auth_res.get_json().get("error", "").lower())

    def test_16_signaling_auth_required_and_impersonation_blocked(self):
        """16. WebRTC and coding room signaling require auth; body sender_id is bound strictly to JWT sub."""
        from app import webrtc_signals, webrtc_signals_memory

        # 1. Unauthenticated signaling rejected with 401
        self.assertEqual(self.client.post("/api/coding/room/signal", json={"signal": "sdp"}).status_code, 401)
        self.assertEqual(self.client.get("/api/coding/room/signals").status_code, 401)
        self.assertEqual(self.client.post("/api/webrtc/signal", json={"signal": "sdp"}).status_code, 401)
        self.assertEqual(self.client.get("/api/webrtc/signals").status_code, 401)

        # 2. User A attempts to spoof User B's identity in sender_id
        attacker_sub = "attacker_uuid_777"
        victim_sub = "victim_uuid_888"
        recipient_sub = "recipient_uuid_999"

        attacker_token = jwt.encode({"sub": attacker_sub, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")
        victim_token = jwt.encode({"sub": victim_sub, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")

        # In /api/coding/room/signal
        self.client.post(
            "/api/coding/room/signal",
            headers={"Authorization": f"Bearer {attacker_token}"},
            json={"sender_id": victim_sub, "recipient_id": recipient_sub, "signal": {"type": "offer"}}
        )
        stored_coding_signals = webrtc_signals.get(recipient_sub, [])
        self.assertTrue(len(stored_coding_signals) > 0)
        self.assertEqual(stored_coding_signals[-1]["sender_id"], attacker_sub, "Impersonation succeeded in coding signal!")

        # In /api/webrtc/signal
        self.client.post(
            "/api/webrtc/signal",
            headers={"Authorization": f"Bearer {attacker_token}"},
            json={"sender_id": victim_sub, "recipient_id": recipient_sub, "signal": {"type": "offer"}}
        )
        stored_webrtc_signals = webrtc_signals_memory.get(recipient_sub, [])
        self.assertTrue(len(stored_webrtc_signals) > 0)
        self.assertEqual(stored_webrtc_signals[-1]["sender_id"], attacker_sub, "Impersonation succeeded in WebRTC signal!")

        # 3. User A attempts to read User B's signals (IDOR)
        idor_coding = self.client.get(
            f"/api/coding/room/signals?user_id={victim_sub}",
            headers={"Authorization": f"Bearer {attacker_token}"}
        )
        self.assertEqual(idor_coding.status_code, 403)

        idor_webrtc = self.client.get(
            f"/api/webrtc/signals?user_id={victim_sub}",
            headers={"Authorization": f"Bearer {attacker_token}"}
        )
        self.assertEqual(idor_webrtc.status_code, 403)

    def test_17_per_user_rate_limiting_enforced_on_ai_endpoints(self):
        """17. Sending >10 requests/minute to AI endpoints triggers HTTP 429 Too Many Requests."""
        rate_user_sub = "rate_limit_candidate_99"
        rate_user_token = jwt.encode({"sub": rate_user_sub, "role": "candidate"}, _get_jwt_secret(), algorithm="HS256")

        # Hit /speech-to-text 10 times (valid quota)
        headers = {"Authorization": f"Bearer {rate_user_token}"}
        for i in range(10):
            res = self.client.post("/speech-to-text", headers=headers, json={"audio_base64": "dummy", "mime_type": "audio/webm"})
            self.assertIn(res.status_code, (200, 400))

        # The 11th request must be rate limited with 429
        rate_limited_res = self.client.post("/speech-to-text", headers=headers, json={"audio_base64": "dummy", "mime_type": "audio/webm"})
        self.assertEqual(rate_limited_res.status_code, 429, "Rate limiter did not block 11th request!")
        self.assertIn("10 per 1 minute", rate_limited_res.get_json().get("error", "").lower())

    def test_18_isolated_sandbox_url_ssrf_validation(self):
        """18. ISOLATED_SANDBOX_URL rejects insecure HTTP, loopback, private networks, and metadata endpoints."""
        from app import _validate_sandbox_url

        # Disallowed schemes and SSRF targets
        bad_urls = [
            "http://worker.external.io",
            "https://localhost:8080",
            "https://127.0.0.1:8080",
            "https://0.0.0.0:8080",
            "https://[::1]:8080",
            "https://169.254.169.254",
            "https://metadata.google.internal",
            "https://10.0.0.5",
            "https://172.16.0.5",
            "https://192.168.1.100"
        ]
        for url in bad_urls:
            with self.subTest(url=url):
                valid, err = _validate_sandbox_url(url)
                self.assertFalse(valid, f"URL was accepted when it should have been blocked: {url}")

        # Allowed public HTTPS endpoint
        valid, err = _validate_sandbox_url("https://sandbox-worker-us-east.runner.prepfly.io")
        self.assertTrue(valid, f"Valid HTTPS worker was rejected: {err}")

    def test_19_ruff_static_code_integrity_clean(self):
        """19. CI Guard: ruff --select F821,E9,F811 passes with 0 syntax errors, undefined names, or redefinitions."""
        import subprocess
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        res = subprocess.run(
            [sys.executable, "-m", "ruff", "check", ".", "--select", "F821,E9,F811"],
            cwd=backend_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Ruff static integrity check failed:\n{res.stdout}\n{res.stderr}")

    def test_20_sql_identifier_validation_and_production_failfast(self):
        """20. SQL identifier validation rejects malicious names and SupabaseFallbackClient fail-fast in production."""
        from local_supabase import _validate_ident, SQLiteSupabaseMock
        import app

        # Test valid identifiers
        valid_idents = ["users", "sessions", "created_at", "col_123", "_private_id"]
        for ident in valid_idents:
            self.assertEqual(_validate_ident(ident), ident)

        # Test malicious/invalid identifiers
        bad_idents = [
            "users; DROP TABLE sessions;--",
            "column with space",
            "123startwithnumber",
            "column$invalid",
            "col' OR '1'='1",
            "col-dash",
            "",
            "   ",
            None
        ]
        for bad in bad_idents:
            with self.assertRaises(ValueError, msg=f"Should reject: {bad}"):
                _validate_ident(bad)

        # Dynamic ALTER TABLE with invalid column in insert must raise ValueError
        local_db = SQLiteSupabaseMock()
        with self.assertRaises(ValueError):
            local_db.table("users").insert({"bad col; DROP TABLE users;--": "val"}).execute()

        # Invalid table name must raise ValueError
        with self.assertRaises(ValueError):
            local_db.table("users; DROP TABLE sessions;--")

        # Invalid column in select must raise ValueError
        with self.assertRaises(ValueError):
            local_db.table("users").select("id, bad col;--")

        # Invalid column in update must raise ValueError
        with self.assertRaises(ValueError):
            local_db.table("users").update({"bad col;--": "val"}).eq("id", "1").execute()

        # Invalid column in eq filter must raise ValueError
        with self.assertRaises(ValueError):
            local_db.table("users").select().eq("bad col;--", "1")

        # Invalid column in order must raise ValueError
        with self.assertRaises(ValueError):
            local_db.table("users").select().order("bad col;--")

        # In production mode, SupabaseFallbackClient with unreachable host must fail startup
        orig_prod = app.is_production
        try:
            app.is_production = True
            with self.assertRaises(RuntimeError):
                app.SupabaseFallbackClient("https://unreachable-mock-supabase-123.supabase.co", "dummy_key")
        finally:
            app.is_production = orig_prod

    def test_21_production_database_query_failure_returns_503(self):
        """21. In production, Supabase query failures return HTTP 503 instead of falling back to SQLite."""
        import app
        from unittest.mock import MagicMock

        orig_prod = app.is_production
        try:
            app.is_production = True
            # Mock failing Supabase client
            mock_real = MagicMock()
            mock_builder = MagicMock()
            mock_real.table.return_value = mock_builder
            mock_builder.select.return_value = mock_builder
            mock_builder.execute.side_effect = RuntimeError("Connection to Supabase timed out")

            fallback_client = app.SupabaseFallbackClient.__new__(app.SupabaseFallbackClient)
            fallback_client._real_client = mock_real
            fallback_client._local_client = None

            # Test execution inside Flask request context -> aborts with 503
            with app.app.test_request_context("/api/test-db"):
                from werkzeug.exceptions import HTTPException
                with self.assertRaises(HTTPException) as cm:
                    fallback_client.table("users").select("*").execute()
                self.assertEqual(cm.exception.code, 503)

            # Test execution outside request context -> raises RuntimeError
            with self.assertRaises(RuntimeError):
                fallback_client.table("users").select("*").execute()

        finally:
            app.is_production = orig_prod

if __name__ == "__main__":
    unittest.main()


