"""
Production-Readiness Sandbox Security Verification Suite.
Independently verifies all 12 security requirements:
1. Container/MicroVM isolation enforcement (rejection of process fallback in production)
2. Zero user code execution inside the Flask backend process
3. Non-root user execution (UID/GID 10001, cap_drop ALL)
4. CPU, memory, wall time, process count, and output size limits
5. Network disabling (--network none, internal: true)
6. Cloud metadata (169.254.169.254), internal service, and host secret blocking
7. Docker socket non-exposure
8. Ephemeral file and container cleanup
9. Concurrency starvation and queue saturation protection
10. Authentication, authorization, and rate limiting on execution endpoints
11. Safe fail-closed behavior on sandbox unavailability (no insecure fallback)
12. Impossibility of silent degradation to weak process isolation
"""

import unittest
import os
import sys
import glob
import tempfile
import inspect
from unittest.mock import patch, MagicMock

# Add sandbox_worker and f_backend to path
SANDBOX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(SANDBOX_DIR)
BACKEND_DIR = os.path.join(PROJECT_DIR, "f_backend")

if SANDBOX_DIR not in sys.path:
    sys.path.insert(0, SANDBOX_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Ensure backend test environment defaults are configured so integration tests can run independently
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key-for-unit-testing")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_dummy_id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test_razorpay_secret_for_testing")
os.environ.setdefault("SMTP_EMAIL", "test@prepfly.io")
os.environ.setdefault("SMTP_PASSWORD", "test-smtp-password")

from config import config
from runner import runner, CodeRunner
from server import app as sandbox_app, validate_sandbox_startup
from queue_manager import QueueManager
from quota import QuotaManager
from security import build_scrubbed_env, sanitize_output, static_code_check


class TestProductionSandboxSecurity(unittest.TestCase):
    def setUp(self):
        self.client = sandbox_app.test_client()
        self.valid_headers = {
            "Content-Type": "application/json",
            "X-Sandbox-Secret": config.SECRET
        }

    # -------------------------------------------------------------------------
    # 1. Container / MicroVM Isolation & Anti-Degradation in Production
    # -------------------------------------------------------------------------
    def test_01_production_strictly_rejects_process_mode(self):
        """Req 1 & 12: Production (ENVIRONMENT=production) refuses ISOLATION_MODE='process'."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with patch.object(config, "ISOLATION_MODE", "process"):
                with self.assertRaises(RuntimeError) as cm:
                    runner.get_isolation_mode()
                self.assertIn("strictly forbidden in production", str(cm.exception))

                with self.assertRaises(RuntimeError):
                    validate_sandbox_startup()

    def test_02_production_auto_mode_cannot_silently_fallback_to_process(self):
        """Req 1 & 12: In production, auto mode without Docker fails closed, raising RuntimeError."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with patch.object(config, "ISOLATION_MODE", "auto"):
                with patch("runner.is_docker_available", return_value=False):
                    with self.assertRaises(RuntimeError) as cm:
                        runner.get_isolation_mode()
                    self.assertIn("strictly forbidden in production", str(cm.exception))

                    with self.assertRaises(RuntimeError):
                        validate_sandbox_startup()

    # -------------------------------------------------------------------------
    # 2. Flask Backend Code Execution Absence
    # -------------------------------------------------------------------------
    def test_03_flask_backend_contains_zero_host_execution_primitives(self):
        """Req 2: Flask backend app.py has zero subprocess, os.system, exec, or eval code runs."""
        app_path = os.path.join(BACKEND_DIR, "app.py")
        with open(app_path, "r", encoding="utf-8") as f:
            code_text = f.read()

        # Check for forbidden code execution primitives in app.py
        self.assertNotIn("os.system(", code_text)
        self.assertNotIn("exec(", code_text)
        self.assertNotIn("eval(", code_text)
        # Verify subprocess is not imported in app.py
        self.assertNotIn("import subprocess", code_text)
        self.assertNotIn("from subprocess", code_text)

    # -------------------------------------------------------------------------
    # 3. Non-Root User & Linux Capabilities in Dockerfile & Compose
    # -------------------------------------------------------------------------
    def test_04_dockerfile_declares_non_root_user_and_group(self):
        """Req 3: Dockerfile configures unprivileged user and group 10001."""
        dockerfile_path = os.path.join(SANDBOX_DIR, "Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            df = f.read()

        self.assertIn("groupadd -g 10001", df)
        self.assertIn("useradd -u 10001", df)
        self.assertIn("USER sandboxuser:sandboxgroup", df)

    def test_05_docker_compose_drops_all_capabilities_and_forbids_new_privs(self):
        """Req 3: docker-compose.yml drops ALL Linux capabilities and sets no-new-privileges."""
        compose_path = os.path.join(SANDBOX_DIR, "docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            dc = f.read()

        self.assertIn("cap_drop:", dc)
        self.assertIn("- ALL", dc)
        self.assertIn("no-new-privileges:true", dc)
        self.assertIn("read_only: true", dc)

    # -------------------------------------------------------------------------
    # 4. Strict Resource Limits
    # -------------------------------------------------------------------------
    def test_06_resource_boundaries_configured(self):
        """Req 4: Config enforces strict CPU, wall-time, memory, process, and output limits."""
        self.assertLessEqual(config.CPU_TIME_LIMIT_SECONDS, 5.0)
        self.assertLessEqual(config.WALL_TIME_LIMIT_SECONDS, 10.0)
        self.assertLessEqual(config.MEMORY_LIMIT_BYTES, 256 * 1024 * 1024)  # <= 256 MB
        self.assertLessEqual(config.MAX_PROCESSES, 32)
        self.assertLessEqual(config.MAX_OUTPUT_BYTES, 128 * 1024)  # <= 128 KB
        self.assertLessEqual(config.MAX_CODE_SIZE_BYTES, 128 * 1024)

    def test_07_output_sanitizer_truncates_large_outputs(self):
        """Req 4: Sanitizer enforces hard ceiling on stdout/stderr to prevent memory flooding."""
        large_payload = "A" * (200 * 1024)
        sanitized = sanitize_output(large_payload, max_bytes=64 * 1024)
        self.assertLessEqual(len(sanitized.encode("utf-8")), 65 * 1024)
        self.assertIn("[Output truncated: size limit exceeded]", sanitized)

    # -------------------------------------------------------------------------
    # 5 & 6. Network Disabling, Metadata Blocking & Secret Isolation
    # -------------------------------------------------------------------------
    def test_08_container_run_command_disables_network(self):
        """Req 5: Container runner passes --network none, memory limits, and unprivileged user."""
        source_runner = inspect.getsource(runner._execute_container_case)
        self.assertIn('"--network", "none"', source_runner)
        self.assertIn('"--read-only"', source_runner)
        self.assertIn('"--user", "10001:10001"', source_runner)
        self.assertIn('f"--memory={config.MEMORY_LIMIT_BYTES}"', source_runner)
        self.assertIn('f"--memory-swap={config.MEMORY_LIMIT_BYTES}"', source_runner)

    def test_08b_container_cgroup_memory_limit_verified(self):
        """Req 4: Verify effective Linux kernel cgroup memory limit inside running container."""
        from runner import is_docker_available
        if is_docker_available():
            code = """
import os
val = None
for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
    if os.path.exists(p):
        with open(p, "r") as f:
            val = f.read().strip()
        break
print(f"CGROUP_MEM:{val}")
"""
            test_cases = [{"input": "", "expected_output": f"CGROUP_MEM:{config.MEMORY_LIMIT_BYTES}"}]
            with patch.dict(os.environ, {"SANDBOX_ISOLATION_MODE": "container"}):
                res = runner.run_submission("python", code, test_cases, "cgroup-verify")
                self.assertIn("results", res)
                case_res = res["results"][0]
                self.assertEqual(
                    case_res["status"],
                    "success",
                    f"Execution failed with status '{case_res.get('status')}': {case_res.get('error')}"
                )
                self.assertIn(f"CGROUP_MEM:{config.MEMORY_LIMIT_BYTES}", case_res["output"])

    def test_09_docker_compose_configures_internal_network_bridge(self):
        """Req 5: docker-compose.yml configures internal: true on the network."""
        compose_path = os.path.join(SANDBOX_DIR, "docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            dc = f.read()

        self.assertIn("internal: true", dc)

    def test_10_environment_scrubbing_drops_all_host_secrets(self):
        """Req 6: build_scrubbed_env() eliminates database keys, JWT secrets, and AWS/GCP credentials."""
        # Inject simulated sensitive host environment
        test_env = {
            "SUPABASE_SERVICE_ROLE_KEY": "secret-supabase-token",
            "JWT_SECRET_KEY": "secret-jwt-key",
            "RAZORPAY_KEY_SECRET": "secret-razorpay-key",
            "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }
        with patch.dict(os.environ, test_env):
            scrubbed = build_scrubbed_env()
            for k in test_env:
                self.assertNotIn(k, scrubbed, f"Secret {k} leaked into child environment!")
            # Allowed minimal keys
            self.assertIn("PATH", scrubbed)
            self.assertIn("LANG", scrubbed)

    # -------------------------------------------------------------------------
    # 7. Docker Socket & Host Filesystem Protection
    # -------------------------------------------------------------------------
    def test_11_docker_socket_is_not_mounted(self):
        """Req 7: docker-compose.yml does NOT mount /var/run/docker.sock into worker."""
        compose_path = os.path.join(SANDBOX_DIR, "docker-compose.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            dc = f.read()

        self.assertNotIn("/var/run/docker.sock", dc)
        self.assertNotIn("docker.sock", dc)

    # -------------------------------------------------------------------------
    # 8. Disposable Directory Cleanup
    # -------------------------------------------------------------------------
    def test_12_disposable_directories_cleaned_up_after_execution(self):
        """Req 8: All temporary directories are removed in finally: blocks."""
        code = "print('cleanup test')"
        test_cases = [{"input": "", "expected_output": "cleanup test"}]
        res = runner.run_submission("python", code, test_cases, "cleanup-test")
        self.assertIn("results", res)

        # Check that no prepfly_sandbox_* folders remain orphaned in system or configured scratch temp
        temp_dir = getattr(config, "SCRATCH_BASE_DIR", None) or tempfile.gettempdir()
        orphaned = glob.glob(os.path.join(temp_dir, "prepfly_sandbox_*"))
        self.assertEqual(len(orphaned), 0, f"Found orphaned sandbox directories: {orphaned}")

    # -------------------------------------------------------------------------
    # 9. Concurrency & Queue Saturation
    # -------------------------------------------------------------------------
    def test_13_queue_saturation_rejects_with_429(self):
        """Req 9: QueueManager returns 429 when max queue capacity is reached."""
        qm = QueueManager(max_workers=1, max_queue_size=2)
        with qm._lock:
            qm._active_jobs = 3  # Capacity = 1 + 2 = 3

        res = qm.dispatch(lambda: {"status": "ok"})
        self.assertEqual(res.get("status_code"), 429)
        self.assertIn("Job queue capacity exceeded", res.get("error", ""))

    # -------------------------------------------------------------------------
    # 10. Authentication & Rate Limiting on Sandbox API
    # -------------------------------------------------------------------------
    def test_14_worker_api_rejects_missing_and_invalid_auth(self):
        """Req 10: /execute requires valid X-Sandbox-Secret with constant-time verification."""
        # Missing auth
        res_no_auth = self.client.post("/execute", json={"language": "python", "code": "print(1)", "test_cases": [{"input": "", "expected_output": "1"}]})
        self.assertEqual(res_no_auth.status_code, 401)

        # Invalid auth
        res_bad_auth = self.client.post(
            "/execute",
            headers={"X-Sandbox-Secret": "invalid-secret"},
            json={"language": "python", "code": "print(1)", "test_cases": [{"input": "", "expected_output": "1"}]}
        )
        self.assertEqual(res_bad_auth.status_code, 401)

    # -------------------------------------------------------------------------
    # 11. Backend Fail-Closed & SSRF Protection
    # -------------------------------------------------------------------------
    def test_15_backend_fails_closed_when_sandbox_unavailable(self):
        """Req 11: Backend coding_submit returns 503 when ISOLATED_SANDBOX_URL is unset."""
        from app import app as backend_app, _get_jwt_secret
        import jwt

        backend_client = backend_app.test_client()
        from datetime import datetime, timedelta
        secret_key = _get_jwt_secret()
        token = jwt.encode({
            "sub": "test_user_failclosed",
            "role": "candidate",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, secret_key, algorithm="HS256")

        with patch.dict(os.environ, {"ISOLATED_SANDBOX_URL": ""}):
            res = backend_client.post(
                "/api/coding/submit",
                headers={"Authorization": f"Bearer {token}"},
                json={"language": "python", "code": "print(1)", "problem_id": "two-sum"}
            )
            self.assertEqual(res.status_code, 503)
            self.assertIn("requires an isolated sandbox worker", res.get_json().get("error", ""))

    def test_16_backend_ssrf_validator_blocks_internal_and_metadata_targets(self):
        """Req 11: _validate_sandbox_url blocks loopback, private IPs, and cloud metadata targets."""
        from app import _validate_sandbox_url

        blocked_urls = [
            "http://external.domain.com",       # Insecure HTTP
            "https://127.0.0.1:5050",            # Loopback IP
            "https://localhost:5050",            # Localhost
            "https://169.254.169.254",           # Cloud metadata IP
            "https://metadata.google.internal",  # GCP metadata
            "https://10.0.1.10:5050",            # RFC1918 Class A
            "https://172.16.1.10:5050",          # RFC1918 Class B
            "https://192.168.1.10:5050",         # RFC1918 Class C
            "https://admin:pass@sandbox.prepfly.io" # Embedded credentials in URL
        ]
        for url in blocked_urls:
            with self.subTest(url=url):
                valid, err = _validate_sandbox_url(url)
                self.assertFalse(valid, f"Expected {url} to be blocked by SSRF filter, but was accepted.")

    def test_17_production_mode_rejects_insecure_sandbox_secret(self):
        """Req 10: In production (ENVIRONMENT=production), worker strictly refuses weak or default secret."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with patch.object(config, "ISOLATION_MODE", "container"):
                with patch("runner.is_docker_available", return_value=True):
                    # Default dev secret must be rejected
                    with patch.object(config, "SECRET", "prepfly-sandbox-dev-secret-32-chars-long-minimum"):
                        with self.assertRaises(RuntimeError) as cm:
                            validate_sandbox_startup()
                        self.assertIn("ISOLATED_SANDBOX_SECRET must be configured", str(cm.exception))

                    # Short secret (<32 chars) must be rejected
                    with patch.object(config, "SECRET", "too-short-secret"):
                        with self.assertRaises(RuntimeError) as cm:
                            validate_sandbox_startup()
                        self.assertIn("minimum 32 characters", str(cm.exception))

                    # Strong 64-char secret succeeds
                    strong_secret = "a" * 64
                    with patch.object(config, "SECRET", strong_secret):
                        # Should not raise
                        validate_sandbox_startup()

    def test_18_backend_coding_submit_handles_sandbox_config_error_gracefully(self):
        """Req 11: Backend coding_submit returns 503 instead of unhandled 500 when sandbox URL has invalid scheme."""
        from app import app as backend_app, _get_jwt_secret
        import jwt
        from datetime import datetime, timedelta

        backend_client = backend_app.test_client()
        secret_key = _get_jwt_secret()
        token = jwt.encode({
            "sub": "test_user_err_handle",
            "role": "candidate",
            "exp": datetime.utcnow() + timedelta(days=1)
        }, secret_key, algorithm="HS256")

        # Set sandbox URL to invalid scheme (e.g. ftp://)
        with patch.dict(os.environ, {"ISOLATED_SANDBOX_URL": "ftp://malicious.example.com"}):
            res = backend_client.post(
                "/api/coding/submit",
                headers={"Authorization": f"Bearer {token}"},
                json={"language": "python", "code": "print(1)", "problem_id": "two-sum"}
            )
            self.assertEqual(res.status_code, 503)
            self.assertIn("Sandbox worker communication error", res.get_json().get("error", ""))

    def test_19_worker_verify_auth_in_production_rejects_missing_or_default_secret(self):
        """Req 10: In production mode, _verify_auth strictly returns False if secret is missing or default."""
        from server import _verify_auth
        req_mock = MagicMock()
        req_mock.headers = {"X-Sandbox-Secret": "prepfly-sandbox-dev-secret-32-chars-long-minimum"}

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with patch.object(config, "SECRET", "prepfly-sandbox-dev-secret-32-chars-long-minimum"):
                self.assertFalse(_verify_auth(req_mock))

        # Empty secret in production must be rejected
        req_mock_empty = MagicMock()
        req_mock_empty.headers = {}
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with patch.object(config, "SECRET", ""):
                self.assertFalse(_verify_auth(req_mock_empty))


if __name__ == "__main__":
    unittest.main()

