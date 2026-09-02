#!/usr/bin/env python3
"""Policy-as-Code Task Router for Codex-Antigravity.

Classifies incoming tasks and validates routing decisions through strict
security policies, preventing file modifications or git operations from being
delegated away from Codex Native.
"""

from enum import Enum
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config  # type: ignore


class Route(str, Enum):
    CODEX = "codex"
    RESEARCH = "antigravity_research"
    CODEBASE = "antigravity_codebase"
    TEST = "test_delegator"


class RouteDecision:
    """Represents a validated routing decision."""

    def __init__(
        self,
        route: Route,
        proposed_route: Route,
        allowed_for_delegation: bool,
        reason: str,
        task: str,
    ):
        self.route = route
        self.proposed_route = proposed_route
        self.allowed_for_delegation = allowed_for_delegation
        self.reason = reason
        self.task = task

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route.value,
            "proposed_route": self.proposed_route.value,
            "allowed_for_delegation": self.allowed_for_delegation,
            "reason": self.reason,
            "task": self.task,
        }


# Keywords that require direct coding agent implementation and cannot be delegated to read-only tools
CODE_MODIFICATION_PATTERNS = [
    re.compile(r"\b(?:implement|write|edit|modify|refactor|delete|create\s+file|patch|fix\s+bug)\b", re.IGNORECASE),
    re.compile(r"\b(?:git\s+(?:commit|push|merge|rebase|checkout\s+-b))\b", re.IGNORECASE),
    re.compile(r"\b(?:pip\s+install|npm\s+i(?:nstall)?|cargo\s+add)\b", re.IGNORECASE),
    re.compile(r"(?:ファイルを(?:作成|変更|編集|削除|修正)|実装して|リファクタリングして|コミットして)", re.IGNORECASE),
]

# Patterns indicating test execution
TEST_PATTERNS = [
    re.compile(r"\b(?:run\s+tests?|execute\s+tests?|pytest|unittest|cargo\s+test|npm\s+test|vitest|jest|ctest)\b", re.IGNORECASE),
    re.compile(r"(?:テストを実行|テストを走らせ|単体テスト|結合テスト)", re.IGNORECASE),
]

# Patterns indicating codebase reconnaissance
CODEBASE_PATTERNS = [
    re.compile(r"\b(?:codebase\s+status|tech\s+stack|architecture\s+overview|call\s+graph|impact\s+analysis|audit\s+code)\b", re.IGNORECASE),
    re.compile(r"(?:コードベースの構成|アーキテクチャ|依存関係の調査|影響範囲)", re.IGNORECASE),
]

# Patterns indicating research / documentation
RESEARCH_PATTERNS = [
    re.compile(r"\b(?:how\s+to|what\s+is|documentation|docs|api\s+signature|compare\s+.*vs|github\s+issue|version\s+compatibilit)\b", re.IGNORECASE),
    re.compile(r"(?:ドキュメントを調べて|API仕様|バージョン比較|公式情報|最新情報)", re.IGNORECASE),
]


def classify_task(task: str, metadata: Optional[Dict[str, Any]] = None) -> Route:
    """Classify the most appropriate agent route for a given task prompt."""
    text = task.strip()

    # 1. If explicit modification intent is present, route immediately to Codex
    for p in CODE_MODIFICATION_PATTERNS:
        if p.search(text):
            return Route.CODEX

    # 2. Check for test execution
    for p in TEST_PATTERNS:
        if p.search(text):
            return Route.TEST

    # 3. Check for codebase reconnaissance
    for p in CODEBASE_PATTERNS:
        if p.search(text):
            return Route.CODEBASE

    # 4. Check for external research
    for p in RESEARCH_PATTERNS:
        if p.search(text):
            return Route.RESEARCH

    # Default to research if it looks like an inquiry, else Codex
    if "?" in text or text.lower().startswith(("how", "what", "why", "where", "can", "is")):
        return Route.RESEARCH

    return Route.CODEX


def validate_delegation_policy(proposed_route: Route, task: str) -> Tuple[bool, str]:
    """Policy-as-code validator: verify whether a task is permitted to be delegated.

    Rejects Antigravity delegation if task requires mutating codebase or system state.
    """
    if proposed_route == Route.CODEX:
        return (
            False,
            "Delegation rejected by SafetyPolicy: file modifications, package installations, and git commits must be performed by Codex Native.",
        )

    # Verify task does not contain destructive or file modification directives
    for p in CODE_MODIFICATION_PATTERNS:
        match = p.search(task)
        if match:
            forbidden = match.group(0)
            return (
                False,
                f"Delegation rejected by SafetyPolicy: task contains mutation directive '{forbidden}'. "
                f"File modifications, package installations, and git commits must be performed by Codex Native.",
            )

    return True, f"Delegation to {proposed_route.value} approved by SafetyPolicy."


def route_task(
    task: str,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> RouteDecision:
    """Route a task through intent classification and policy validation."""
    cfg = config or load_config()
    routing_cfg = cfg.get("routing", {})

    proposed = classify_task(task, metadata)

    # Check routing feature flags in configuration
    if proposed == Route.TEST and not routing_cfg.get("test_execution", True):
        proposed = Route.CODEX
    elif proposed == Route.CODEBASE and not routing_cfg.get("codebase_status", True):
        proposed = Route.CODEX
    elif proposed == Route.RESEARCH and not routing_cfg.get("web_research", True):
        proposed = Route.CODEX

    allowed, reason = validate_delegation_policy(proposed, task)

    effective_route = proposed if allowed else Route.CODEX

    return RouteDecision(
        route=effective_route,
        proposed_route=proposed,
        allowed_for_delegation=allowed,
        reason=reason,
        task=task,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Policy-as-Code Task Router for Codex-Antigravity.")
    parser.add_argument("--task", type=str, required=True, help="Task prompt or user query to route")
    parser.add_argument("--json", action="store_true", default=False, help="Output JSON result")
    args = parser.parse_args()

    decision = route_task(args.task)
    if args.json:
        print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
    else:
        print("=" * 50)
        print(f"Task       : {decision.task}")
        print(f"Final Route: {decision.route.value.upper()}")
        print(f"Proposed   : {decision.proposed_route.value}")
        print(f"Delegation : {'APPROVED' if decision.allowed_for_delegation else 'BLOCKED'}")
        print(f"Policy Note: {decision.reason}")
        print("=" * 50)


if __name__ == "__main__":
    main()
