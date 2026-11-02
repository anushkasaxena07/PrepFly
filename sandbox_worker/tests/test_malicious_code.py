"""
Malicious Code Attack Battery for PrepFly Sandbox Worker.
Validates defenses against infinite loops, fork bombs, memory bombs,
filesystem escapes, secret exfiltration, socket connections, reflection exploits,
and disposable directory cleanup.
"""

import unittest
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner import runner
from security import static_code_check

class TestMaliciousCodeDefense(unittest.TestCase):
    def test_01_infinite_loop_timeout_defense(self):
        """1. Infinite loop is terminated cleanly within wall-clock timeout without hanging worker."""
        infinite_code = """
import time
while True:
    time.sleep(0.1)
"""
        test_cases = [{"input": "", "expected_output": "finished"}]
        res = runner.run_submission("python", infinite_code, test_cases, "inf-loop")
        self.assertIn("results", res)
        case_res = res["results"][0]
        self.assertEqual(case_res["status"], "time_limit_exceeded")
        self.assertFalse(case_res["passed"])
        self.assertIn("Time Limit Exceeded", case_res["error"])

    def test_02_memory_bomb_defense(self):
        """2. Memory exhaustion attempt (allocating huge list) is caught and terminated."""
        mem_bomb_code = """
a = []
for _ in range(100):
    a.append('X' * (100 * 1024 * 1024))  # 100MB chunks
print("Allocated")
"""
        test_cases = [{"input": "", "expected_output": "Allocated"}]
        res = runner.run_submission("python", mem_bomb_code, test_cases, "mem-bomb")
        self.assertIn("results", res)
        case_res = res["results"][0]
        self.assertIn(case_res["status"], ("runtime_error", "memory_limit_exceeded", "time_limit_exceeded"))
        self.assertFalse(case_res["passed"])

    def test_03_fork_bomb_mitigation(self):
        """3. Fork bomb attempt is contained by timeouts and process termination."""
        fork_bomb_code = """
import os
import time
for i in range(50):
    try:
        if hasattr(os, 'fork'):
            os.fork()
    except Exception:
        pass
time.sleep(10)
"""
        test_cases = [{"input": "", "expected_output": ""}]
        res = runner.run_submission("python", fork_bomb_code, test_cases, "fork-bomb")
        self.assertIn("results", res)
        case_res = res["results"][0]
        # Must be stopped by time limit or runtime error, and not crash host
        self.assertIn(case_res["status"], ("time_limit_exceeded", "runtime_error", "success"))

    def test_04_scrubbed_environment_secret_isolation(self):
        """4. Child process receives a scrubbed environment with zero production secrets."""
        # Set dummy secrets on test host environment
        os.environ["JWT_SECRET_KEY"] = "super-secret-production-jwt-key"
        os.environ["SUPABASE_SERVICE_KEY"] = "super-secret-supabase-admin-key"
        os.environ["RAZORPAY_KEY_SECRET"] = "super-secret-razorpay-key"

        code = """
import os
secrets = [k for k in os.environ.keys() if 'SECRET' in k or 'KEY' in k or 'SUPABASE' in k]
print(f"Found: {','.join(secrets)}")
"""
        test_cases = [{"input": "", "expected_output": "Found: "}]
        res = runner.run_submission("python", code, test_cases, "secret-test")
        self.assertIn("results", res)
        case_res = res["results"][0]
        # Output should be "Found: " because none of the secrets were leaked into child env
        self.assertEqual(case_res["output"], "Found:")
        self.assertNotIn("JWT_SECRET_KEY", case_res["output"])
        self.assertNotIn("SUPABASE_SERVICE_KEY", case_res["output"])

    def test_05_filesystem_containment(self):
        """5. Candidate code cannot overwrite critical host files outside scratch directory."""
        code = """
try:
    with open('/etc/passwd', 'a') as f:
        f.write('malicious:x:0:0::/root:/bin/bash\\n')
    print('ESCAPED')
except Exception as e:
    print(f'BLOCKED: {type(e).__name__}')
"""
        test_cases = [{"input": "", "expected_output": "BLOCKED"}]
        res = runner.run_submission("python", code, test_cases, "fs-escape")
        self.assertIn("results", res)
        case_res = res["results"][0]
        # Must NOT succeed in escaping
        self.assertNotIn("ESCAPED", case_res["output"])

    def test_06_output_flooding_truncated(self):
        """6. Massive stdout flooding (infinite print) is truncated to MAX_OUTPUT_BYTES."""
        flood_code = """
for i in range(100000):
    print("A" * 100)
"""
        test_cases = [{"input": "", "expected_output": ""}]
        res = runner.run_submission("python", flood_code, test_cases, "flood-test")
        self.assertIn("results", res)
        case_res = res["results"][0]
        # Output must be truncated and limited
        self.assertLessEqual(len(case_res["output"].encode("utf-8")), 128 * 1024)

    def test_07_network_socket_and_metadata_exfiltration_blocked(self):
        """7. Network connections and metadata endpoints are blocked or fail without crashing."""
        code = """
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    s.connect(("169.254.169.254", 80))
    print("CONNECTED")
except Exception as e:
    print("NETWORK_BLOCKED")
"""
        test_cases = [{"input": "", "expected_output": "NETWORK_BLOCKED"}]
        res = runner.run_submission("python", code, test_cases, "net-test")
        self.assertIn("results", res)
        case_res = res["results"][0]
        self.assertNotIn("CONNECTED", case_res["output"])

    def test_08_subclasses_reflection_defense(self):
        """8. Subclasses reflection dunder attributes are detected by static security analysis."""
        code = """
# Attempt to traverse object subclasses to invoke os.system
subclasses = ().__class__.__bases__[0].__subclasses__()
print(len(subclasses))
"""
        is_safe, flags = static_code_check("python", code)
        self.assertFalse(is_safe)
        self.assertTrue(any("FORBIDDEN_ATTRIBUTE" in f for f in flags))

    def test_09_disposable_directory_purged(self):
        """9. Disposable execution directory is completely purged from disk after run completes."""
        code = """
print("clean run")
"""
        test_cases = [{"input": "", "expected_output": "clean run"}]
        res = runner.run_submission("python", code, test_cases, "cleanup-test")
        self.assertIn("results", res)
        self.assertEqual(res["results"][0]["status"], "success")

        # Verify no orphan prepfly_sandbox_* dirs remain in temp directory
        import tempfile
        temp_dir = tempfile.gettempdir()
        # All temp dirs created by this run should have been purged by finally: block
        active_sandboxes = glob.glob(os.path.join(temp_dir, "prepfly_sandbox_*"))
        self.assertEqual(len(active_sandboxes), 0)

    def test_10_unrestricted_network_and_privilege_modules_flagged(self):
        """10. Static AST filter flags dangerous modules: subprocess, ctypes, socket, pty, posix."""
        dangerous_snippets = [
            ("import subprocess", "SUSPICIOUS_MODULE:subprocess"),
            ("import ctypes", "SUSPICIOUS_MODULE:ctypes"),
            ("import socket", "SUSPICIOUS_MODULE:socket"),
            ("import pty", "SUSPICIOUS_MODULE:pty"),
            ("import posix", "SUSPICIOUS_MODULE:posix"),
            ("x = '169.254.169.254'", "METADATA_IP_ATTEMPT")
        ]
        for snippet, expected_flag in dangerous_snippets:
            with self.subTest(snippet=snippet):
                is_safe, flags = static_code_check("python", snippet)
                self.assertFalse(is_safe)
                self.assertIn(expected_flag, flags)

if __name__ == "__main__":
    unittest.main()
