"""
Unit and integration tests for the Sandbox Worker HTTP API.
Tests authentication, input validation, per-user quotas, rate limiting, and health reporting.
"""

import unittest
import os
import sys
import time

# Ensure sandbox_worker directory is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app
from config import config
from quota import quota_manager

class TestSandboxWorkerAPI(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.valid_headers = {
            "Content-Type": "application/json",
            "X-Sandbox-Secret": config.SECRET
        }

    def test_01_health_endpoint(self):
        """1. /health reports healthy status, active jobs, toolchains, and quota stats."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "prepfly-sandbox-worker")
        self.assertIn("toolchains", data)
        self.assertIn("limits", data)
        self.assertIn("quotas", data)
        self.assertIn("queue", data)

    def test_02_auth_missing_secret_rejected(self):
        """2. /execute without X-Sandbox-Secret returns 401 Unauthorized."""
        res = self.client.post("/execute", json={
            "language": "python",
            "code": "print('hello')",
            "test_cases": [{"input": "", "expected_output": "hello"}]
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Unauthorized", res.get_json().get("error", ""))

    def test_03_auth_invalid_secret_rejected(self):
        """3. /execute with invalid X-Sandbox-Secret returns 401 Unauthorized."""
        res = self.client.post("/execute", headers={"X-Sandbox-Secret": "wrong-secret-token"}, json={
            "language": "python",
            "code": "print('hello')",
            "test_cases": [{"input": "", "expected_output": "hello"}]
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Unauthorized", res.get_json().get("error", ""))

    def test_04_payload_validation_missing_fields(self):
        """4. /execute rejects payloads missing required fields with 400 Bad Request."""
        # Missing language
        res = self.client.post("/execute", headers=self.valid_headers, json={
            "code": "print(1)",
            "test_cases": [{"input": "", "expected_output": "1"}]
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("language", res.get_json().get("error", ""))

        # Missing code
        res = self.client.post("/execute", headers=self.valid_headers, json={
            "language": "python",
            "test_cases": [{"input": "", "expected_output": "1"}]
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("code", res.get_json().get("error", ""))

        # Missing test_cases
        res = self.client.post("/execute", headers=self.valid_headers, json={
            "language": "python",
            "code": "print(1)"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("test_cases", res.get_json().get("error", ""))

    def test_05_payload_too_large_rejected(self):
        """5. /execute rejects code exceeding MAX_CODE_SIZE_BYTES with 413 Payload Too Large."""
        oversized_code = "x = 1\n" * 15000  # > 64 KB
        res = self.client.post("/execute", headers=self.valid_headers, json={
            "language": "python",
            "code": oversized_code,
            "test_cases": [{"input": "", "expected_output": ""}]
        })
        self.assertEqual(res.status_code, 413)
        self.assertIn("Payload Too Large", res.get_json().get("error", ""))

    def test_06_successful_execution_via_api(self):
        """6. /execute successfully runs valid Python code and returns structured results."""
        payload = {
            "language": "python",
            "code": "import sys\nline = sys.stdin.read().strip()\nprint(f'Echo: {line}')",
            "problem_id": "echo-test",
            "user_id": "user-test-123",
            "test_cases": [
                {"input": "PrepFly", "expected_output": "Echo: PrepFly", "is_hidden": False},
                {"input": "Security", "expected_output": "Echo: Security", "is_hidden": True}
            ]
        }
        res = self.client.post("/execute", headers=self.valid_headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)
        
        # Test case 1
        tc1 = data["results"][0]
        self.assertEqual(tc1["status"], "success")
        self.assertTrue(tc1["passed"])
        self.assertEqual(tc1["output"], "Echo: PrepFly")
        self.assertFalse(tc1["is_hidden"])

        # Test case 2 (Hidden)
        tc2 = data["results"][1]
        self.assertEqual(tc2["status"], "success")
        self.assertTrue(tc2["passed"])
        self.assertEqual(tc2["output"], "Echo: Security")
        self.assertTrue(tc2["is_hidden"])

    def test_07_per_user_quota_limits_enforced(self):
        """7. /execute rejects requests when a user exceeds USER_QUOTA_PER_MINUTE with 429."""
        user_id = "quota-test-user-999"
        # Seed timestamps to fill user quota
        with quota_manager._lock:
            quota_manager._user_requests[user_id] = [time.time()] * config.USER_QUOTA_PER_MINUTE

        payload = {
            "language": "python",
            "code": "print(1)",
            "user_id": user_id,
            "test_cases": [{"input": "", "expected_output": "1"}]
        }
        res = self.client.post("/execute", headers=self.valid_headers, json=payload)
        self.assertEqual(res.status_code, 429)
        self.assertIn("Retry-After", res.headers)
        data = res.get_json()
        self.assertIn("User quota exceeded", data.get("error", ""))
        self.assertGreater(data.get("retry_after", 0), 0)

        # Cleanup test user record
        with quota_manager._lock:
            quota_manager._user_requests.pop(user_id, None)

    def test_08_concurrent_user_limit_enforced(self):
        """8. /execute prevents a user from exceeding USER_MAX_CONCURRENT_JOBS with 429."""
        user_id = "concurrency-test-user-888"
        with quota_manager._lock:
            quota_manager._user_active_jobs[user_id] = config.USER_MAX_CONCURRENT_JOBS

        payload = {
            "language": "python",
            "code": "print(1)",
            "user_id": user_id,
            "test_cases": [{"input": "", "expected_output": "1"}]
        }
        res = self.client.post("/execute", headers=self.valid_headers, json=payload)
        self.assertEqual(res.status_code, 429)
        data = res.get_json()
        self.assertIn("Concurrent execution limit", data.get("error", ""))

        # Cleanup test user record
        with quota_manager._lock:
            quota_manager._user_active_jobs.pop(user_id, None)

    def test_09_metrics_and_audit_endpoints(self):
        """9. /metrics and /audit/recent provide operational telemetry and compliance logs."""
        # /metrics
        metrics_res = self.client.get("/metrics")
        self.assertEqual(metrics_res.status_code, 200)
        metrics_data = metrics_res.get_json()
        self.assertIn("queue", metrics_data)
        self.assertIn("quotas", metrics_data)
        self.assertIn("isolation_mode", metrics_data)

        # /audit/recent without auth -> 401
        self.assertEqual(self.client.get("/audit/recent").status_code, 401)

        # /audit/recent with auth -> 200
        audit_res = self.client.get("/audit/recent?limit=10", headers=self.valid_headers)
        self.assertEqual(audit_res.status_code, 200)
        audit_data = audit_res.get_json()
        self.assertIn("events", audit_data)
        self.assertIsInstance(audit_data["events"], list)

    def test_10_production_mode_refuses_weak_isolation(self):
        """10. In production (ENVIRONMENT=production), worker refuses process mode and auto fallback."""
        from runner import runner
        from server import validate_sandbox_startup
        from unittest.mock import patch

        orig_env = os.environ.get("ENVIRONMENT")
        os.environ["ENVIRONMENT"] = "production"
        try:
            # 1. ISOLATION_MODE='process' must raise RuntimeError in production
            with patch.object(config, "ISOLATION_MODE", "process"):
                with self.assertRaises(RuntimeError) as cm:
                    runner.get_isolation_mode()
                self.assertIn("strictly forbidden in production", str(cm.exception))

                with self.assertRaises(RuntimeError):
                    validate_sandbox_startup()

            # 2. ISOLATION_MODE='auto' must never fall back to process mode in production
            with patch.object(config, "ISOLATION_MODE", "auto"):
                with patch("runner.is_docker_available", return_value=False):
                    with self.assertRaises(RuntimeError) as cm:
                        runner.get_isolation_mode()
                    self.assertIn("strictly forbidden in production", str(cm.exception))

                    with self.assertRaises(RuntimeError):
                        validate_sandbox_startup()

            # 3. ISOLATION_MODE='container' without docker must raise RuntimeError in production
            with patch.object(config, "ISOLATION_MODE", "container"):
                with patch("runner.is_docker_available", return_value=False):
                    with self.assertRaises(RuntimeError) as cm:
                        runner.get_isolation_mode()
                    self.assertIn("Container runtime is not operational", str(cm.exception))

            # 4. Valid container/microvm with operational Docker succeeds in production
            with patch.object(config, "ISOLATION_MODE", "container"):
                with patch("runner.is_docker_available", return_value=True):
                    self.assertEqual(runner.get_isolation_mode(), "container")

            with patch.object(config, "ISOLATION_MODE", "microvm"):
                with patch("runner.is_docker_available", return_value=True):
                    self.assertEqual(runner.get_isolation_mode(), "microvm")

        finally:
            if orig_env is not None:
                os.environ["ENVIRONMENT"] = orig_env
            else:
                os.environ.pop("ENVIRONMENT", None)

    def test_11_metrics_endpoint_privacy(self):
        """11. /metrics exposes only aggregate counts and never reveals user IDs, IPs, or candidate code."""
        # Execute code with sensitive user ID and payload
        sensitive_user = "user-confidential-uuid-987654321"
        sensitive_code = "SECRET_CANARY_STRING_DO_NOT_LEAK = 123456789"
        self.client.post("/execute", headers=self.valid_headers, json={
            "language": "python",
            "code": f"print('ok')\n# {sensitive_code}",
            "user_id": sensitive_user,
            "test_cases": [{"input": "", "expected_output": "ok"}]
        })

        # Fetch /metrics
        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        metrics_text = res.get_data(as_text=True)

        # Assert no user ID, no IP address, and no code string appears in /metrics
        self.assertNotIn(sensitive_user, metrics_text)
        self.assertNotIn(sensitive_code, metrics_text)
        self.assertNotIn("CANARY", metrics_text)

        metrics_json = res.get_json()
        quotas = metrics_json.get("quotas", {})
        # Verify quotas only contains numeric counts
        self.assertIsInstance(quotas.get("active_users_in_flight"), int)
        self.assertIsInstance(quotas.get("total_tracked_users"), int)
        self.assertIsInstance(quotas.get("total_tracked_ips"), int)
        self.assertNotIn("user_ids", quotas)
        self.assertNotIn("ips", quotas)

    def test_12_docker_socket_not_mounted(self):
        """12. Sandbox worker container configuration does NOT mount /var/run/docker.sock."""
        compose_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_file), "docker-compose.yml missing")
        with open(compose_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Must NOT mount docker.sock
        self.assertNotIn("/var/run/docker.sock", content)
        self.assertNotIn("docker.sock", content)

    def test_13_ci_guard_ruff_static_integrity(self):
        """13. CI Guard: ruff check . --select F821,E9,F811 passes on sandbox_worker."""
        import subprocess
        worker_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backend_dir = os.path.join(os.path.dirname(worker_dir), "f_backend")
        venv_py = os.path.join(backend_dir, "venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join(backend_dir, "venv", "bin", "python")
        py_exe = venv_py if os.path.exists(venv_py) else sys.executable

        res = subprocess.run(
            [py_exe, "-m", "ruff", "check", worker_dir, "--select", "F821,E9,F811"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Ruff integrity check failed:\n{res.stdout}\n{res.stderr}")

if __name__ == "__main__":
    unittest.main()

