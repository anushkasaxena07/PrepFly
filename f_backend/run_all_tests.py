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
    print("\n[PHASE 0] Running Static Integrity Checks (ruff check . --select F821,E9,F811)...")
    import subprocess
    venv_py = os.path.join(BACKEND_DIR, "venv", "Scripts", "python.exe") if os.name == "nt" else os.path.join(BACKEND_DIR, "venv", "bin", "python")
    py_exe = venv_py if os.path.exists(venv_py) else sys.executable
    repo_root = os.path.dirname(BACKEND_DIR)
    check_dir = repo_root if os.path.exists(os.path.join(repo_root, "sandbox_worker")) else BACKEND_DIR
    ruff_res = subprocess.run([py_exe, "-m", "ruff", "check", ".", "--no-cache", "--select", "F821,E9,F811"], cwd=check_dir)
    if ruff_res.returncode != 0:
        print(">>> STATIC INTEGRITY CHECK FAILED! Fix syntax errors, undefined names, or redefinitions.")
        return 1


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
        print(">>> SOME TESTS FAILED! PLEASE REVIEW THE LOGS ABOVE. <<<")
        return 1

if __name__ == "__main__":
    sys.exit(run_suite())
