#!/usr/bin/env python3
"""Tests for Manager-Style Agent Orchestrator."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from orchestrator import orchestrate_task  # type: ignore


class TestOrchestrator(unittest.TestCase):
    def test_orchestrate_compound_task_mock(self):
        task = "ONNX Runtime の最新仕様を調べて、このコードを対応させてテストして"
        result = orchestrate_task(task=task, mock=True)

        self.assertTrue(result.graph.is_compound)
        self.assertEqual(result.next_action, "implement_with_codex")
        self.assertIsNotNone(result.evidence)
        self.assertTrue(len(result.evidence.claims) >= 2)
        self.assertTrue(len(result.subtask_results) >= 2)

        # Check markdown presentation
        md = result.to_markdown()
        self.assertIn("Orchestration Plan & Evidence", md)
        self.assertIn("Manager DAG (Compound)", md)
        self.assertIn("IMPLEMENT_WITH_CODEX", md)
        self.assertIn("research_1", md)
        self.assertIn("repo_1", md)

    def test_orchestrate_simple_task(self):
        task = "What is the capital of France?"
        result = orchestrate_task(task=task, mock=True)
        self.assertFalse(result.graph.is_compound)
    def test_orchestrate_with_language_parameter(self):
        task = "Research Unity portal transition best practices and documentation"
        result = orchestrate_task(task=task, language="en", mock=True)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.evidence)


if __name__ == "__main__":
    unittest.main()
