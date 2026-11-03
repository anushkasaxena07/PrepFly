"""
Multi-language execution correctness tests for the Sandbox Worker runner.
"""

import unittest
import os
import sys
import shutil
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner import runner, is_docker_available

class TestRunnerLanguages(unittest.TestCase):
    def test_01_python_algorithm_execution(self):
        """1. Python: Two Sum algorithm runs and passes sample and hidden cases."""
        code = """
import sys

def two_sum():
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        return
    import json
    nums = json.loads(lines[0])
    target = int(lines[1])
    seen = {}
    for idx, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            print(f"[{seen[diff]}, {idx}]")
            return
        seen[num] = idx

two_sum()
"""
        test_cases = [
            {"input": "[2, 7, 11, 15]\n9", "expected_output": "[0, 1]", "is_hidden": False},
            {"input": "[3, 2, 4]\n6", "expected_output": "[1, 2]", "is_hidden": False},
            {"input": "[3, 3]\n6", "expected_output": "[0, 1]", "is_hidden": True}
        ]
        res = runner.run_submission("python", code, test_cases, "two-sum")
        self.assertIn("results", res)
        results = res["results"]
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertEqual(r["status"], "success")
            self.assertTrue(r["passed"])
            self.assertGreaterEqual(r["time_ms"], 0.0)

    def test_02_python_syntax_compilation_error(self):
        """2. Python: Syntax error returns runtime_error / error details without crashing host."""
        bad_code = "def broken(\n  print('unclosed parenthesis')"
        test_cases = [{"input": "", "expected_output": "1"}]
        res = runner.run_submission("python", bad_code, test_cases, "syntax-err")
        self.assertIn("results", res)
        self.assertEqual(res["results"][0]["status"], "runtime_error")
        self.assertFalse(res["results"][0]["passed"])
        self.assertIn("SyntaxError", res["results"][0]["error"])

    @unittest.skipUnless(shutil.which("node") is not None, "Node.js not installed on test host")
    def test_03_javascript_execution(self):
        """3. JavaScript: Node.js runner executes JS solutions correctly."""
        code = """
const fs = require('fs');
const input = fs.readFileSync(0, 'utf-8').trim();
const num = parseInt(input);
console.log(num * 2);
"""
        test_cases = [
            {"input": "5", "expected_output": "10", "is_hidden": False},
            {"input": "21", "expected_output": "42", "is_hidden": True}
        ]
        res = runner.run_submission("javascript", code, test_cases, "double-js")
        self.assertIn("results", res)
        self.assertTrue(res["results"][0]["passed"])
        self.assertTrue(res["results"][1]["passed"])

    def test_04_unsupported_language_rejection(self):
        """4. Unsupported language returns clean compilation_error."""
        test_cases = [{"input": "", "expected_output": ""}]
        res = runner.run_submission("cobol", "IDENTIFICATION DIVISION.", test_cases)
        self.assertIn("results", res)
        self.assertEqual(res["results"][0]["status"], "compilation_error")
        self.assertIn("Unsupported language", res["results"][0]["error"])

    @unittest.skipUnless(shutil.which("node") is not None, "Node.js not installed on test host")
    def test_05_javascript_memory_exhaustion_defense(self):
        """
        5. JavaScript heap-exhaustion defense:
        Verifies that attempting unbounded memory allocation triggers V8 heap exhaustion
        under --max-old-space-size=128 and is terminated cleanly without crashing the worker host.
        Under Docker container isolation, also verifies kernel-enforced cgroup termination.
        Note: This verifies V8 heap limit enforcement, not total process virtual memory limit in process mode.
        """
        # Allocates objects in a tight loop to rapidly hit V8 heap ceiling without destabilizing the host
        exhaustion_code = """
const chunks = [];
while (true) {
    chunks.push(new Array(100000).fill("memory_bomb_data_string"));
}
"""
        test_cases = [{"input": "", "expected_output": "success"}]
        res = runner.run_submission("javascript", exhaustion_code, test_cases, "js-mem-exhaustion")
        self.assertIn("results", res)
        case_res = res["results"][0]
        self.assertFalse(case_res["passed"], "Memory exhaustion code must not be reported as passed")
        self.assertIn(
            case_res["status"],
            ("runtime_error", "memory_limit_exceeded", "time_limit_exceeded"),
            f"Expected termination status for memory bomb, got {case_res['status']}"
        )

        # When Docker container isolation is operational, verify under container cgroup boundary
        if is_docker_available():
            with patch.dict(os.environ, {"SANDBOX_ISOLATION_MODE": "container"}):
                c_res = runner.run_submission("javascript", exhaustion_code, test_cases, "js-cgroup-mem")
                self.assertIn("results", c_res)
                self.assertEqual(c_res.get("isolation_mode"), "container")
                c_case = c_res["results"][0]
                self.assertFalse(c_case["passed"])
                self.assertIn(
                    c_case["status"],
                    ("runtime_error", "memory_limit_exceeded", "time_limit_exceeded")
                )

if __name__ == "__main__":
    unittest.main()
