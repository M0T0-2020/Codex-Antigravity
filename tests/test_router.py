#!/usr/bin/env python3
"""Tests for Policy-as-Code Task Router."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from router import Route, classify_task, route_task, validate_delegation_policy  # type: ignore


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

    def test_policy_validator_blocks_delegation_with_mutation(self):
        # Even if proposed route was RESEARCH, if task says "modify", it is blocked
        allowed, reason = validate_delegation_policy(Route.RESEARCH, "Research how to edit and write file src/main.py")
        self.assertFalse(allowed)
        self.assertIn("Delegation rejected by SafetyPolicy", reason)


if __name__ == "__main__":
    unittest.main()
