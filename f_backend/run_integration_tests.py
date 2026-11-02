"""
PrepFly Dedicated Integration Test Runner
Executes all end-to-end integration tests in tests/integration/
"""

import unittest
import time
import sys
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

def run_integration_suite():
    print("=" * 70)
    print(" " * 18 + "PREPFLY INTEGRATION TEST RUNNER")
    print("=" * 70)
    print(f"Backend Directory: {BACKEND_DIR}")
    print(f"Python Version:    {sys.version.split()[0]}")
    print("=" * 70)

    start_time = time.time()

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.join(BACKEND_DIR, "tests", "integration"),
        pattern="test_*.py",
        top_level_dir=BACKEND_DIR
    )

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    duration = time.time() - start_time

    print("\n" + "=" * 70)
    print(" " * 20 + "INTEGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Integration Tests Run: {result.testsRun}")
    print(f"Passed:                {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:              {len(result.failures)}")
    print(f"Errors:                {len(result.errors)}")
    print(f"Time Taken:            {duration:.2f} seconds")
    print("=" * 70)

    if result.wasSuccessful():
        print(">>> ALL PREPFLY INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
        return 0
    else:
        print(">>> INTEGRATION TESTS ENCOUNTERED FAILURES! <<<")
        return 1

if __name__ == "__main__":
    sys.exit(run_integration_suite())
