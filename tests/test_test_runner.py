#!/usr/bin/env python3
"""Tests for Test Runner and Failure Triage Engine."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from test_runner import (  # type: ignore
    build_diagnosis_prompt,
    delegate_test_run,
    detect_test_command,
    parse_diagnosis_output,
    parse_pytest_output,
    parse_test_results,
    parse_unittest_output,
)


class TestTestRunner(unittest.TestCase):
    def test_detect_test_command_python(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "pyproject.toml"), "w") as f:
                f.write("[project]\nname='app'\n")
            cmd = detect_test_command(tmp_dir)
            self.assertTrue("pytest" in cmd or "unittest" in cmd)

    def test_detect_test_command_rust(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "Cargo.toml"), "w") as f:
                f.write("[package]\nname='app'\n")
            cmd = detect_test_command(tmp_dir)
            self.assertEqual(cmd, "cargo test")

    def test_parse_pytest_output(self):
        sample = """============================= test session starts ==============================
rootdir: /workspace
collected 10 items

tests/test_api.py ....F....                                              [100%]

=================================== FAILURES ===================================
_________________________________ test_endpoint _________________________________
    def test_endpoint():
>       assert resp.status_code == 200
E       assert 404 == 200

tests/test_api.py:24: AssertionError
=========================== 1 failed, 9 passed in 0.42s ===========================
"""
        parsed = parse_pytest_output(sample)
        metrics = parsed["metrics"]
        self.assertEqual(metrics["passed"], 9)
        self.assertEqual(metrics["failed"], 1)
        self.assertEqual(metrics["total"], 10)
        self.assertEqual(len(parsed["failures"]), 1)
        self.assertEqual(parsed["failures"][0]["test_name"], "test_endpoint")
        self.assertIn("AssertionError", parsed["failures"][0]["traceback"])

    def test_parse_unittest_output_pass(self):
        sample = "Ran 20 tests in 0.15s\n\nOK\n"
        parsed = parse_unittest_output(sample)
        self.assertEqual(parsed["metrics"]["total"], 20)
        self.assertEqual(parsed["metrics"]["passed"], 20)
        self.assertEqual(parsed["metrics"]["failed"], 0)
        self.assertEqual(len(parsed["failures"]), 0)

    def test_parse_unittest_output_fail(self):
        sample = """Ran 5 tests in 0.20s

======================================================================
FAIL: test_addition (tests.test_math.TestMath)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "tests/test_math.py", line 12, in test_addition
    self.assertEqual(1 + 1, 3)
AssertionError: 2 != 3

----------------------------------------------------------------------
FAILED (failures=1)
"""
        parsed = parse_unittest_output(sample)
        self.assertEqual(parsed["metrics"]["total"], 5)
        self.assertEqual(parsed["metrics"]["passed"], 4)
        self.assertEqual(parsed["metrics"]["failed"], 1)
        self.assertEqual(len(parsed["failures"]), 1)
        self.assertIn("test_addition", parsed["failures"][0]["test_name"])

    def test_parse_diagnosis_output(self):
        sample = """ROOT_CAUSE:
The authentication middleware does not parse Bearer prefix properly when token contains underscores.

AFFECTED_COMPONENTS:
- src/auth/middleware.py:42
- tests/test_auth.py:15

SUGGESTED_FIX:
- Strip 'Bearer ' with slice [7:] instead of split.
- Add test case with underscore-separated tokens.
"""
        diag = parse_diagnosis_output(sample)
        self.assertIn("authentication middleware does not parse Bearer", diag["root_cause"])
        self.assertEqual(len(diag["affected_components"]), 2)
        self.assertEqual(len(diag["suggested_fix"]), 2)

    def test_delegate_test_run_mock_pass(self):
        result = delegate_test_run(
            project_dir=".",
            mock=True,
            mock_should_pass=True,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["metrics"]["failed"], 0)
        self.assertEqual(result["metrics"]["passed"], 15)
        self.assertIsNone(result["diagnosis"])

    def test_delegate_test_run_mock_fail_with_diagnosis(self):
        result = delegate_test_run(
            project_dir=".",
            mock=True,
            mock_should_pass=False,
            diagnose=True,
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["metrics"]["failed"], 1)
        self.assertIsNotNone(result["diagnosis"])
        self.assertIn("root_cause", result["diagnosis"])
        self.assertIn("suggested_fix", result["diagnosis"])


if __name__ == "__main__":
    unittest.main()
