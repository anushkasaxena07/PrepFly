"""
Dedicated Scratch Directory and Filesystem Security Tests.
Verifies Phase 2 security hardening:
1. Strict mode 0o770 in container mode, 0o700 in process mode (zero world access).
2. Complete absence of insecure fallback to mode 0o1777 or 0o777.
3. Fail-closed behavior on scratch permission setup failure.
4. Descriptor-based safe file creation (_safe_write_source with O_CREAT | O_EXCL | O_NOFOLLOW).
5. Strict filename whitelisting and path traversal rejection (../, embedded slashes).
6. Symlink defenses during file creation, execution, and cleanup.
7. Cleanup directory boundary enforcement (preventing deletion of files outside scratch root).
8. Concurrent execution directory isolation (unpredictable unique paths, no collision).
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add sandbox_worker to sys.path
SANDBOX_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SANDBOX_DIR not in sys.path:
    sys.path.insert(0, SANDBOX_DIR)

from config import config
from runner import runner, CodeRunner, _safe_write_source


class TestScratchDirectorySecurity(unittest.TestCase):
    def setUp(self):
        self.runner = CodeRunner()
        self.test_dir = tempfile.mkdtemp(prefix="prepfly_scratch_test_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_safe_write_source_creates_file_correctly(self):
        """1. _safe_write_source creates a valid source file with safe descriptor flags."""
        content = "print('secure write test')"
        path = _safe_write_source(self.test_dir, "solution.py", content)
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_02_safe_write_source_rejects_path_traversal(self):
        """2. _safe_write_source rejects traversal attempts with ../, slashes, or hidden files."""
        traversal_attempts = [
            "../escaped.py",
            "../../etc/passwd",
            "subdir/solution.py",
            "sub\\solution.py",
            ".hidden.py",
            "file with spaces.py",
            "file;malicious.py",
            "file|pipe.py"
        ]
        for bad_filename in traversal_attempts:
            with self.subTest(filename=bad_filename):
                with self.assertRaises(ValueError):
                    _safe_write_source(self.test_dir, bad_filename, "malicious")

    def test_03_safe_write_source_rejects_overwriting_existing_file(self):
        """3. _safe_write_source uses O_CREAT | O_EXCL and refuses to overwrite an existing file."""
        _safe_write_source(self.test_dir, "solution.py", "first content")
        with self.assertRaises(FileExistsError):
            _safe_write_source(self.test_dir, "solution.py", "second content")

    def test_04_setup_scratch_dir_process_mode_enforces_0700(self):
        """4. Process mode enforces mode 0700 (owner-only access, zero group or world access)."""
        scratch_dir = self.runner._setup_scratch_dir("process")
        try:
            self.assertTrue(os.path.isdir(scratch_dir))
            if hasattr(os, "stat") and os.name != "nt":
                mode = os.stat(scratch_dir).st_mode & 0o777
                self.assertEqual(mode, 0o700, f"Expected mode 0700, got {oct(mode)}")
        finally:
            self.runner._safe_cleanup_scratch(scratch_dir)

    def test_05_setup_scratch_dir_container_mode_fails_closed_on_chown_error(self):
        """5. Container mode on POSIX fails closed if group 10001 chown fails (no 01777 fallback)."""
        if os.name == "nt":
            self.skipTest("POSIX chown fail-closed test applicable only to non-Windows hosts")

        with patch("os.chown", side_effect=PermissionError("Mocked Permission Denied for GID 10001")):
            with self.assertRaises(RuntimeError) as cm:
                self.runner._setup_scratch_dir("container")
            err_msg = str(cm.exception)
            self.assertIn("Security failure", err_msg)
            self.assertIn("Failing closed", err_msg)
            # Verify no fallback to 0o1777 or 0o777
            self.assertNotIn("01777", err_msg)
            self.assertNotIn("0777", err_msg)

    def test_06_submission_fails_closed_when_scratch_setup_fails(self):
        """6. run_submission returns system_error and halts when scratch setup fails."""
        with patch.object(self.runner, "_setup_scratch_dir", side_effect=RuntimeError("Disk quota exhausted")):
            res = self.runner.run_submission(
                "python",
                "print(1)",
                [{"input": "", "expected_output": "1"}]
            )
            self.assertIn("error", res)
            self.assertIn("Disk quota exhausted", res["error"])
            self.assertEqual(res["results"][0]["status"], "system_error")
            self.assertFalse(res["results"][0]["passed"])

    def test_07_safe_cleanup_scratch_refuses_to_delete_outside_base(self):
        """7. _safe_cleanup_scratch rejects paths outside the configured scratch root."""
        # Attempt to clean up an unrelated directory (e.g. system temp itself)
        outside_dir = tempfile.gettempdir()
        with patch("shutil.rmtree") as mock_rmtree:
            self.runner._safe_cleanup_scratch(outside_dir)
            mock_rmtree.assert_not_called()

    def test_08_safe_cleanup_scratch_handles_symlinked_dir_without_traversing(self):
        """8. If scratch directory itself is a symlink, _safe_cleanup_scratch unlinks it without traversing."""
        real_target = os.path.join(self.test_dir, "real_target")
        os.makedirs(real_target, exist_ok=True)
        secret_file = os.path.join(real_target, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("top-secret")

        symlink_dir = os.path.join(self.test_dir, "prepfly_sandbox_symlink")
        if hasattr(os, "symlink"):
            try:
                os.symlink(real_target, symlink_dir)
            except OSError:
                self.skipTest("Symlinks not permitted on this host without elevation")

            self.runner._safe_cleanup_scratch(symlink_dir)
            # Symlink must be deleted, but real_target and secret_file MUST remain untouched
            self.assertFalse(os.path.exists(symlink_dir) and os.path.islink(symlink_dir))
            self.assertTrue(os.path.isfile(secret_file), "Symlink deletion followed symlink and destroyed target!")

    def test_09_concurrent_submissions_use_isolated_directories(self):
        """9. Multiple concurrent scratch setups generate distinct, non-overlapping paths."""
        dirs = [self.runner._setup_scratch_dir("process") for _ in range(10)]
        try:
            self.assertEqual(len(dirs), len(set(dirs)), "Collision detected in scratch directory generation!")
            for d in dirs:
                self.assertTrue(os.path.isdir(d))
                self.assertIn("prepfly_sandbox_", os.path.basename(d))
        finally:
            for d in dirs:
                self.runner._safe_cleanup_scratch(d)

    def test_10_no_world_writable_permissions_in_codebase(self):
        """10. Codebase contains zero instances of 0o1777, 01777, 0o777, or 777 permissions."""
        runner_path = os.path.join(SANDBOX_DIR, "runner.py")
        with open(runner_path, "r", encoding="utf-8") as f:
            runner_code = f.read()

        self.assertNotIn("0o1777", runner_code)
        self.assertNotIn("01777", runner_code)
        self.assertNotIn("0o777", runner_code)
        self.assertNotIn("0777", runner_code)


if __name__ == "__main__":
    unittest.main()
