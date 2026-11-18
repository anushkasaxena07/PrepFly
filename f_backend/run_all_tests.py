"""
PrepFly Master Test Runner
Discovers and executes both Unit Tests and End-to-End Integration Tests.
"""

import unittest
import time
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# Set defaults for test runs if not already in environment
os.environ["ENVIRONMENT"] = "test"
os.environ["FLASK_ENV"] = "test"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-chars-long-for-testing-only-12345")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key-for-unit-testing")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_dummy_id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test_razorpay_secret_for_testing")
os.environ.setdefault("SMTP_EMAIL", "test@prepfly.io")
os.environ.setdefault("SMTP_PASSWORD", "test-smtp-password")

def run_suite():
    print("=" * 75)
    print(" " * 22 + "PREPFLY MASTER TEST RUNNER")
    print("=" * 75)
    print(f"Backend Directory: {BACKEND_DIR}")
    print(f"Python Version:    {sys.version.split()[0]}")
    print("=" * 75)

    start_time = time.time()

    # Phase 0: Ruff Static Integrity Checks (Syntax, Undefined Names, Redefinitions)
    print("\n[PHASE 0] Running Static Integrity Checks (ruff check f_backend sandbox_worker --select F821,E9,F811)...")
    import subprocess
    import shutil
    venv_py = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join(BACKEND_DIR, "venv", "bin", "python")
    py_exe = venv_py if os.path.exists(venv_py) else sys.executable
    repo_root = os.path.dirname(BACKEND_DIR)
    check_dir = repo_root if os.path.exists(os.path.join(repo_root, "sandbox_worker")) else BACKEND_DIR
    check_targets = ["f_backend", "sandbox_worker"] if check_dir == repo_root else ["."]

    ruff_bin = shutil.which("ruff")
    if ruff_bin:
        cmd = [ruff_bin, "check"] + check_targets + ["--no-cache", "--select", "F821,E9,F811"]
    else:
        cmd = [py_exe, "-m", "ruff", "check"] + check_targets + ["--no-cache", "--select", "F821,E9,F811"]

    ruff_res = subprocess.run(cmd, cwd=check_dir, capture_output=True, text=True)
    if ruff_res.returncode != 0:
        print(f">>> STATIC INTEGRITY CHECK FAILED (code {ruff_res.returncode})!\n{ruff_res.stdout}\n{ruff_res.stderr}")
        print(f"::error title=Ruff Static Integrity Failed::{ruff_res.stdout.strip() or ruff_res.stderr.strip()}")
        return 1
    print("Static integrity checks passed cleanly!")


    loader = unittest.TestLoader()

    # 1. Discover Unit Tests
    print("\n[PHASE 1] Discovering and Running Unit Tests...")
    unit_suite = loader.discover(
        start_dir=os.path.join(BACKEND_DIR, "tests"),
        pattern="test_*.py",
        top_level_dir=BACKEND_DIR
    )

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unit_suite)

    duration = time.time() - start_time

    print("\n" + "=" * 75)
    print(" " * 24 + "COMPLETE TEST SUITE SUMMARY")
    print("=" * 75)
    print(f"Total Tests Executed: {result.testsRun}")
    print(f"Passed:               {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:             {len(result.failures)}")
    print(f"Errors:               {len(result.errors)}")
    print(f"Total Time Taken:     {duration:.2f} seconds")
    print("=" * 75)

    if result.wasSuccessful():
        print(">>> ALL PREPFLY UNIT & INTEGRATION TESTS PASSED WITH 100% SUCCESS! <<<")
        return 0
    else:
        print("\n" + "!" * 75)
        print(">>> SOME TESTS FAILED! DETAILED REPORT:")
        print("!" * 75)
        summary_lines = ["### PrepFly Backend Test Failures", f"**Failed:** {len(result.failures)} | **Errors:** {len(result.errors)}"]

        for test, err in result.failures:
            print(f"\n[FAILURE] {test}:")
            print(err)
            first_err_line = err.strip().splitlines()[-1] if err else "AssertionError"
            print(f"::error title=Test Failure - {test}::{first_err_line}")
            summary_lines.append(f"- **FAILURE**: `{test}`: `{first_err_line}`")

        for test, err in result.errors:
            print(f"\n[ERROR] {test}:")
            print(err)
            first_err_line = err.strip().splitlines()[-1] if err else "Exception"
            print(f"::error title=Test Error - {test}::{first_err_line}")
            summary_lines.append(f"- **ERROR**: `{test}`: `{first_err_line}`")

        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary:
            try:
                with open(step_summary, "a", encoding="utf-8") as f:
                    f.write("\n\n" + "\n".join(summary_lines) + "\n")
            except Exception:
                pass

        return 1

if __name__ == "__main__":
    sys.exit(run_suite())
