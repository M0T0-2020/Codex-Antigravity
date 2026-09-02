#!/usr/bin/env python3
"""Tests for SafetyPolicy layer and execution boundaries."""

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from safety import SafetyPolicy, SecurityError  # type: ignore


class TestSafetyPolicy(unittest.TestCase):
    def setUp(self):
        self.policy = SafetyPolicy()

    # --- 1. Shell Injection & Command Validation Tests ---

    def test_allow_valid_runner_command_string(self):
        argv = self.policy.validate_command("pytest -v -k test_auth")
        self.assertEqual(argv, ["pytest", "-v", "-k", "test_auth"])

    def test_allow_valid_runner_argv_list(self):
        argv = self.policy.validate_command(["cargo", "test", "--lib"])
        self.assertEqual(argv, ["cargo", "test", "--lib"])

    def test_reject_semicolon_chaining(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("pytest ; rm -rf /")
        self.assertIn("dangerous character", str(ctx.exception))

    def test_reject_and_chaining(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("pytest && cat /etc/passwd")
        self.assertIn("dangerous character", str(ctx.exception))

    def test_reject_pipe_chaining(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("npm test | bash")
        self.assertIn("dangerous character", str(ctx.exception))

    def test_reject_redirection(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("pytest > /tmp/out.txt")
        self.assertIn("dangerous character", str(ctx.exception))

    def test_reject_command_substitution(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("pytest `whoami`")
        self.assertIn("dangerous character", str(ctx.exception))

    def test_reject_unauthorized_runner(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("bash -c 'echo pwned'")
        self.assertIn("Disallowed test runner 'bash'", str(ctx.exception))

    def test_reject_package_install_in_command(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("python3 -m pip install requests")
        self.assertIn("Package installation is prohibited", str(ctx.exception))

    def test_reject_git_write_in_command(self):
        with self.assertRaises(SecurityError) as ctx:
            self.policy.validate_command("python3 -c 'pass' git commit -m test")
        self.assertIn("Git write operation is prohibited", str(ctx.exception))

    # --- 2. Workspace Boundary Tests ---

    def test_valid_workspace_relative_path(self):
        with tempfile.TemporaryDirectory() as root:
            sub = os.path.join(root, "tests", "unit")
            os.makedirs(sub, exist_ok=True)
            res = self.policy.validate_workspace(path="tests/unit", workspace_root=root)
            self.assertEqual(res, Path(sub).resolve())

    def test_reject_path_traversal_parent(self):
        with tempfile.TemporaryDirectory() as root:
            outside = Path(root).parent
            with self.assertRaises(SecurityError) as ctx:
                self.policy.validate_workspace(path="../", workspace_root=root)
            self.assertIn("Workspace boundary violation", str(ctx.exception))

    def test_reject_root_path_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(SecurityError) as ctx:
                self.policy.validate_workspace(path="/etc/passwd", workspace_root=root)
            self.assertIn("Workspace boundary violation", str(ctx.exception))

    # --- 3. Environment Sanitization Tests ---

    def test_sanitize_environment_scrubs_secrets(self):
        raw_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/user",
            "USER": "user",
            "GITHUB_TOKEN": "ghp_secret_token_123",
            "AWS_SECRET_ACCESS_KEY": "aws_secret_key_456",
            "DATABASE_PASSWORD": "super_secret_db_pass",
            "CUSTOM_VAR": "harmless_value",
        }
        sanitized = self.policy.sanitize_environment(base_env=raw_env)
        self.assertIn("PATH", sanitized)
        self.assertIn("HOME", sanitized)
        self.assertIn("CUSTOM_VAR", sanitized)
        self.assertNotIn("GITHUB_TOKEN", sanitized)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", sanitized)
        self.assertNotIn("DATABASE_PASSWORD", sanitized)
        self.assertEqual(sanitized.get("PYTHONUNBUFFERED"), "1")

    # --- 4. AGY Permissions & Sandbox Tests ---

    def test_build_agy_permissions_readonly(self):
        perms = self.policy.build_agy_permissions()
        self.assertTrue(perms["sandbox"])
        self.assertTrue(perms["readonly"])
        self.assertFalse(perms["allow_file_writes"])


if __name__ == "__main__":
    unittest.main()
