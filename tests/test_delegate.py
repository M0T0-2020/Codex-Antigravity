#!/usr/bin/env python3
"""Tests for Antigravity delegation wrapper."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from antigravity_delegate import build_research_prompt, delegate_research, delegate_parallel  # type: ignore


class TestDelegate(unittest.TestCase):
    def test_build_research_prompt_basic(self):
        prompt = build_research_prompt("Check library API", task_type="docs")
        self.assertIn("Check library API", prompt)
        self.assertIn("Strict Rules:", prompt)
        self.assertIn("Do NOT write or modify files.", prompt)
        self.assertIn("SUMMARY:", prompt)
        self.assertIn("FINDINGS:", prompt)
        self.assertIn("SOURCES:", prompt)
        self.assertIn("UNCERTAINTIES:", prompt)

    def test_build_research_prompt_with_context(self):
        prompt = build_research_prompt("Subtask query", context="Important project constraint")
        self.assertIn("Context from caller:", prompt)
        self.assertIn("Important project constraint", prompt)

    def test_build_research_prompt_context_truncation(self):
        long_context = "X" * 4000
        prompt = build_research_prompt("Subtask query", context=long_context)
        self.assertIn("... [context truncated]", prompt)

    def test_delegate_mock_mode(self):
        result = delegate_research(
            task="Test query for mock mode",
            task_type="research",
            effort="low",
            mock=True,
        )
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["summary"])
        self.assertTrue(len(result["findings"]) > 0)
        self.assertTrue(len(result["sources"]) > 0)
        self.assertEqual(result["usage"]["mock"], True)
        self.assertIsNone(result["error"])

    def test_delegate_parallel_mock(self):
        tasks = ["Query 1", "Query 2", "Query 3"]
        result = delegate_parallel(tasks=tasks, mock=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["subtasks_count"], 3)
        self.assertEqual(len(result["subtask_results"]), 3)
        self.assertTrue(len(result["findings"]) >= 3)
        self.assertIn("parallel_workers", result["usage"])


    def test_build_research_prompt_codebase_context(self):
        prompt = build_research_prompt("Analyze project structure", task_type="codebase", project_dir=".")
        self.assertIn("Target Project Context:", prompt)
        self.assertIn("Codebase Overview:", prompt)
        self.assertIn("Python", prompt)

    def test_delegate_codebase_mock(self):
        result = delegate_research(
            task="Reconnaissance query",
            task_type="codebase",
            project_dir=".",
            mock=True,
        )
        self.assertTrue(result["success"])
        self.assertIn("Codebase reconnaissance completed", result["summary"])
        self.assertIsNotNone(result["project_dir"])

    def test_delegate_impact_mock(self):
        result = delegate_research(
            task="Refactor models.py",
            task_type="impact",
            project_dir=".",
            mock=True,
        )
        self.assertTrue(result["success"])
        self.assertIn("Impact analysis", result["summary"])

    def test_delegate_audit_mock(self):
        result = delegate_research(
            task="Audit code quality",
            task_type="audit",
            project_dir=".",
            mock=True,
        )
        self.assertTrue(result["success"])
        self.assertIn("audit completed", result["summary"])


if __name__ == "__main__":
    unittest.main()
