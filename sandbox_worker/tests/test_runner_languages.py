"""
Multi-language execution correctness tests for the Sandbox Worker runner.
"""

import unittest
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner import runner

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

if __name__ == "__main__":
    unittest.main()
