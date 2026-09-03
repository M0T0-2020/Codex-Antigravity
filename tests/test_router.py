#!/usr/bin/env python3
"""Tests for Policy-as-Code Task Router."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from router import Route, classify_task, decompose_task, extract_task_profile, route_task, validate_delegation_policy  # type: ignore


class TestRouter(unittest.TestCase):
    def test_classify_code_modification_to_codex(self):
        tasks = [
            "Implement a new login endpoint in src/auth.py",
            "Refactor models.py to use Pydantic v2",
            "Fix bug in payment processing handler",
            "Create file tests/test_new_feature.py",
            "git commit -m 'Add new feature'",
            "ファイルを修正してバグを直してください",
        ]
        for t in tasks:
            decision = route_task(t)
            self.assertEqual(decision.route, Route.CODEX, f"Failed for task: {t}")
            self.assertFalse(decision.allowed_for_delegation)
            self.assertIn("SafetyPolicy", decision.reason)

    def test_classify_test_execution_to_test_delegator(self):
        tasks = [
            "run tests for auth module",
            "pytest -v tests/test_login.py",
            "execute cargo test --lib",
            "vitest run tests",
            "単体テストを実行して",
        ]
        for t in tasks:
            decision = route_task(t)
            self.assertEqual(decision.route, Route.TEST, f"Failed for task: {t}")
            self.assertTrue(decision.allowed_for_delegation)

    def test_classify_codebase_recon_to_codebase(self):
        tasks = [
            "What is the tech stack and architecture overview of this repo?",
            "Codebase status and entry points",
            "Perform impact analysis on scripts/models.py",
            "コードベースの構成を調査して",
        ]
        for t in tasks:
            decision = route_task(t)
            self.assertEqual(decision.route, Route.CODEBASE, f"Failed for task: {t}")
            self.assertTrue(decision.allowed_for_delegation)

    def test_classify_research_inquiry(self):
        tasks = [
            "What is the latest release of ONNX Runtime?",
            "Compare FastAPI vs Flask for high-throughput APIs",
            "Check official documentation for asyncio.gather",
            "公式ドキュメントでAPI仕様を調べて",
        ]
        for t in tasks:
            decision = route_task(t)
            self.assertEqual(decision.route, Route.RESEARCH, f"Failed for task: {t}")
            self.assertTrue(decision.allowed_for_delegation)

    def test_task_profile_extraction(self):
        profile = extract_task_profile("ONNX Runtime の最新仕様を調べて、このコードを対応させてテストして")
        self.assertTrue(profile.requires_external_info)
        self.assertTrue(profile.requires_repo_context)
        self.assertTrue(profile.requires_write)
        self.assertTrue(profile.requires_execution)
        self.assertTrue(profile.freshness_required)
        self.assertGreaterEqual(profile.complexity, 0.7)

    def test_decompose_mixed_task(self):
        task = "ONNX Runtime の最新仕様を調べて、このコードを対応させてテストして"
        graph = decompose_task(task)
        self.assertTrue(graph.is_compound)
        self.assertEqual(len(graph.subtasks), 4)

        subtask_types = [st.type.value for st in graph.subtasks]
        self.assertIn("external_research", subtask_types)
        self.assertIn("codebase", subtask_types)
        self.assertIn("implementation", subtask_types)
        self.assertIn("test", subtask_types)

        # Verify dependency chain
        impl_task = next(st for st in graph.subtasks if st.type.value == "implementation")
        self.assertIn("research_1", impl_task.depends_on)
        self.assertIn("repo_1", impl_task.depends_on)

        test_task = next(st for st in graph.subtasks if st.type.value == "test")
        self.assertIn("implement_1", test_task.depends_on)

    def test_decompose_single_task(self):
        task = "What is the latest release of ONNX Runtime?"
        graph = decompose_task(task)
        self.assertFalse(graph.is_compound)
        self.assertEqual(len(graph.subtasks), 1)
        self.assertEqual(graph.subtasks[0].type.value, "external_research")
        self.assertEqual(graph.subtasks[0].route.value, "antigravity_research")


if __name__ == "__main__":
    unittest.main()
