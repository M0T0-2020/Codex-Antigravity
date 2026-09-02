#!/usr/bin/env python3
"""Tests for timeout handling."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from antigravity_delegate import execute_agy_cli, delegate_research  # type: ignore


class TestTimeout(unittest.TestCase):
    @patch("subprocess.Popen")
    def test_execute_agy_cli_timeout(self, mock_popen):
        # Setup mock process that raises TimeoutExpired on communicate
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd="agy", timeout=1)
        mock_popen.return_value = mock_proc

        success, stdout, stderr, code = execute_agy_cli(
            prompt="test",
            agy_path="/mock/agy",
            timeout=1,
        )

        self.assertFalse(success)
        self.assertEqual(code, -1)
        self.assertIn("timed out after 1 seconds", stderr)
        mock_proc.kill.assert_called_once()

    @patch("antigravity_delegate.execute_agy_cli")
    def test_delegate_research_timeout_reporting(self, mock_exec):
        # Mock repeated timeouts
        mock_exec.return_value = (False, "", "Execution timed out after 5 seconds.", -1)

        result = delegate_research(
            task="Long task",
            timeout=5,
            config_path=None,
            mock=False,
        )

        self.assertFalse(result["success"])
        self.assertIn("Antigravity delegation failed", result["error"])
        self.assertIn("timed out", result["error"])


if __name__ == "__main__":
    unittest.main()
