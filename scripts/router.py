#!/usr/bin/env python3
"""Policy-as-Code Task Router and Task Decomposer for Codex-Antigravity.

Classifies incoming tasks into multi-dimensional TaskProfiles, decomposes
mixed/compound tasks into DAGs (Task Graphs), and validates routing decisions
through strict security policies, ensuring file modifications and git operations
remain strictly with Codex Native.
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


class TaskNodeType(str, Enum):
    EXTERNAL_RESEARCH = "external_research"
    CODEBASE = "codebase"
    IMPLEMENTATION = "implementation"
    TEST = "test"


class RouteDecision:
    """Represents a validated routing decision."""

    def __init__(
        self,
        route: Route,
        proposed_route: Route,
        allowed_for_delegation: bool,
        reason: str,
        task: str,
        profile: Optional["TaskProfile"] = None,
    ):
        self.route = route
        self.proposed_route = proposed_route
        self.allowed_for_delegation = allowed_for_delegation
        self.reason = reason
        self.task = task
        self.profile = profile

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "route": self.route.value,
            "proposed_route": self.proposed_route.value,
            "allowed_for_delegation": self.allowed_for_delegation,
            "reason": self.reason,
            "task": self.task,
        }
        if self.profile:
            data["profile"] = self.profile.to_dict()
        return data


class TaskProfile:
    """Multi-dimensional characteristics profile for an incoming user task."""

    def __init__(
        self,
        requires_external_info: bool = False,
        requires_repo_context: bool = False,
        requires_write: bool = False,
        requires_execution: bool = False,
        complexity: float = 0.5,
        uncertainty: float = 0.0,
        freshness_required: bool = False,
        parallelizable: bool = False,
    ):
        self.requires_external_info = requires_external_info
        self.requires_repo_context = requires_repo_context
        self.requires_write = requires_write
        self.requires_execution = requires_execution
        self.complexity = complexity
        self.uncertainty = uncertainty
        self.freshness_required = freshness_required
        self.parallelizable = parallelizable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requires_external_info": self.requires_external_info,
            "requires_repo_context": self.requires_repo_context,
            "requires_write": self.requires_write,
            "requires_execution": self.requires_execution,
            "complexity": round(self.complexity, 2),
            "uncertainty": round(self.uncertainty, 2),
            "freshness_required": self.freshness_required,
            "parallelizable": self.parallelizable,
        }


class TaskNode:
    """Individual bounded subtask node in a task DAG."""

    def __init__(
        self,
        id: str,
        type: TaskNodeType,
        query: str,
        route: Route,
        depends_on: Optional[List[str]] = None,
        parallelizable: bool = False,
        model_tier: str = "flash",
    ):
        self.id = id
        self.type = type
        self.query = query
        self.route = route
        self.depends_on = depends_on or []
        self.parallelizable = parallelizable
        self.model_tier = model_tier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "query": self.query,
            "route": self.route.value,
            "depends_on": self.depends_on,
            "parallelizable": self.parallelizable,
            "model_tier": self.model_tier,
        }


class TaskGraph:
    """Directed Acyclic Graph (DAG) of subtasks decomposed from a user prompt."""

    def __init__(
        self,
        goal: str,
        profile: TaskProfile,
        subtasks: List[TaskNode],
        is_compound: bool = False,
    ):
        self.goal = goal
        self.profile = profile
        self.subtasks = subtasks
        self.is_compound = is_compound

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "is_compound": self.is_compound,
            "profile": self.profile.to_dict(),
            "subtasks": [st.to_dict() for st in self.subtasks],
        }


# Keywords that require direct coding agent implementation and cannot be delegated to read-only tools
CODE_MODIFICATION_PATTERNS = [
    re.compile(r"\b(?:implement|write|edit|modify|refactor|delete|create\s+file|patch|fix\s+bug|update|integrate)\b", re.IGNORECASE),
    re.compile(r"\b(?:git\s+(?:commit|push|merge|rebase|checkout\s+-b))\b", re.IGNORECASE),
    re.compile(r"\b(?:pip\s+install|npm\s+i(?:nstall)?|cargo\s+add)\b", re.IGNORECASE),
    re.compile(r"(?:ファイルを(?:作成|変更|編集|削除|修正)|実装して|リファクタリングして|コミットして|対応させて|書き換えて|修正して)", re.IGNORECASE),
]

# Patterns indicating test execution
TEST_PATTERNS = [
    re.compile(r"\b(?:run\s+tests?|execute\s+tests?|pytest|unittest|cargo\s+test|npm\s+test|vitest|jest|ctest)\b", re.IGNORECASE),
    re.compile(r"(?:テストを実行|テストを走らせ|単体テスト|結合テスト|テストして)", re.IGNORECASE),
]

# Patterns indicating codebase reconnaissance
CODEBASE_PATTERNS = [
    re.compile(r"\b(?:codebase\s+status|tech\s+stack|architecture\s+overview|call\s+graph|impact\s+analysis|audit\s+code|in\s+this\s+repo|current\s+usage)\b", re.IGNORECASE),
    re.compile(r"(?:コードベースの構成|アーキテクチャ|依存関係の調査|影響範囲|このコード|現在の.*使用箇所|リポジトリ内)", re.IGNORECASE),
]

# Patterns indicating research / documentation
RESEARCH_PATTERNS = [
    re.compile(r"\b(?:how\s+to|what\s+is|documentation|docs|api\s+signature|compare\s+.*vs|github\s+issue|version\s+compatibilit|latest\s+spec|requirements)\b", re.IGNORECASE),
    re.compile(r"(?:ドキュメントを調べて|API仕様|バージョン比較|公式情報|最新情報|仕様を調べて|調べて)", re.IGNORECASE),
]

# Freshness patterns
FRESHNESS_PATTERNS = [
    re.compile(r"\b(?:latest|recent|newest|current\s+version|changelog|breaking\s+changes|202[4-9])\b", re.IGNORECASE),
    re.compile(r"(?:最新|最近|変更点|新機能|リリースノート)", re.IGNORECASE),
]


def extract_task_profile(task: str, metadata: Optional[Dict[str, Any]] = None) -> TaskProfile:
    """Extract multi-dimensional task profile attributes from a user prompt."""
    text = task.strip()

    has_write = any(p.search(text) for p in CODE_MODIFICATION_PATTERNS)
    has_test = any(p.search(text) for p in TEST_PATTERNS)
    has_codebase = any(p.search(text) for p in CODEBASE_PATTERNS)
    has_research = any(p.search(text) for p in RESEARCH_PATTERNS)
    has_freshness = any(p.search(text) for p in FRESHNESS_PATTERNS)

    # Local code reasoning check: "Why is this slow?" without external library lookup
    is_local_inquiry = bool(re.search(r"(?:why\s+is\s+this|遅い理由|なぜ.*動かない|この関数の問題)", text, re.IGNORECASE))
    if is_local_inquiry and not has_research:
        has_codebase = True

    # Questions that aren't modifications or tests lean towards research
    if not has_write and not has_test and not has_codebase:
        if "?" in text or text.lower().startswith(("how", "what", "why", "where", "can", "is")):
            has_research = True

    # Complexity estimation: number of distinct intents + text length
    intents_count = sum([1 for x in [has_write, has_test, has_codebase, has_research] if x])
    complexity = min(1.0, 0.2 + (intents_count * 0.25) + (len(text) / 500.0) * 0.2)

    # Uncertainty estimation: question markers or ambiguous wording
    uncertainty = 0.5 if ("?" in text or "理由" in text or "原因" in text) else 0.1

    # Parallelizable when both external research and codebase reconnaissance can run concurrently
    parallelizable = (has_research and has_codebase) or (has_research and has_test)

    return TaskProfile(
        requires_external_info=has_research,
        requires_repo_context=has_codebase,
        requires_write=has_write,
        requires_execution=has_test,
        complexity=complexity,
        uncertainty=uncertainty,
        freshness_required=has_freshness,
        parallelizable=parallelizable,
    )


def decompose_task(
    task: str,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> TaskGraph:
    """Decompose a user task into a structured TaskGraph (DAG) of bounded subtasks."""
    cfg = config or load_config()
    profile = extract_task_profile(task, metadata)

    subtasks: List[TaskNode] = []
    goal = task.strip()

    # Determine if this is a compound/mixed task requiring orchestration
    active_intents = sum([
        1 for x in [
            profile.requires_external_info,
            profile.requires_repo_context,
            profile.requires_write,
            profile.requires_execution,
        ] if x
    ])
    is_compound = (active_intents >= 2 and (profile.requires_write or profile.requires_execution))

    if is_compound:
        # Phase 1: Information Gathering Subtasks (Can run in parallel)
        gather_deps: List[str] = []

        if profile.requires_external_info:
            subtasks.append(
                TaskNode(
                    id="research_1",
                    type=TaskNodeType.EXTERNAL_RESEARCH,
                    query=f"Investigate external documentation, APIs, and latest specifications for: {goal}",
                    route=Route.RESEARCH,
                    depends_on=[],
                    parallelizable=True,
                    model_tier="flash",
                )
            )
            gather_deps.append("research_1")

        if profile.requires_repo_context:
            subtasks.append(
                TaskNode(
                    id="repo_1",
                    type=TaskNodeType.CODEBASE,
                    query=f"Inspect local codebase usage, integration points, and dependencies relevant to: {goal}",
                    route=Route.CODEBASE,
                    depends_on=[],
                    parallelizable=True,
                    model_tier="flash",
                )
            )
            gather_deps.append("repo_1")

        # Phase 2: Implementation Subtask (Codex Native, depends on gathered evidence)
        if profile.requires_write:
            subtasks.append(
                TaskNode(
                    id="implement_1",
                    type=TaskNodeType.IMPLEMENTATION,
                    query=f"Implement and update source code based on gathered evidence for: {goal}",
                    route=Route.CODEX,
                    depends_on=list(gather_deps),
                    parallelizable=False,
                    model_tier="codex",
                )
            )
            last_impl_id = "implement_1"
        else:
            last_impl_id = gather_deps[-1] if gather_deps else ""

        # Phase 3: Test Subtask (Test Delegator, depends on implementation)
        if profile.requires_execution:
            subtasks.append(
                TaskNode(
                    id="test_1",
                    type=TaskNodeType.TEST,
                    query=f"Execute test suite to verify changes and validate stability for: {goal}",
                    route=Route.TEST,
                    depends_on=[last_impl_id] if last_impl_id else [],
                    parallelizable=False,
                    model_tier="test",
                )
            )

        return TaskGraph(goal=goal, profile=profile, subtasks=subtasks, is_compound=True)

    # Single-intent task: generate a 1-node TaskGraph
    if profile.requires_write:
        node = TaskNode(
            id="implement_1",
            type=TaskNodeType.IMPLEMENTATION,
            query=goal,
            route=Route.CODEX,
            depends_on=[],
            parallelizable=False,
            model_tier="codex",
        )
    elif profile.requires_execution:
        node = TaskNode(
            id="test_1",
            type=TaskNodeType.TEST,
            query=goal,
            route=Route.TEST,
            depends_on=[],
            parallelizable=False,
            model_tier="test",
        )
    elif profile.requires_repo_context:
        node = TaskNode(
            id="repo_1",
            type=TaskNodeType.CODEBASE,
            query=goal,
            route=Route.CODEBASE,
            depends_on=[],
            parallelizable=False,
            model_tier="flash",
        )
    elif profile.requires_external_info:
        node = TaskNode(
            id="research_1",
            type=TaskNodeType.EXTERNAL_RESEARCH,
            query=goal,
            route=Route.RESEARCH,
            depends_on=[],
            parallelizable=False,
            model_tier="flash",
        )
    else:
        # Default fallback
        node = TaskNode(
            id="task_1",
            type=TaskNodeType.IMPLEMENTATION,
            query=goal,
            route=Route.CODEX,
            depends_on=[],
            parallelizable=False,
            model_tier="codex",
        )

    return TaskGraph(goal=goal, profile=profile, subtasks=[node], is_compound=False)


def classify_task(task: str, metadata: Optional[Dict[str, Any]] = None) -> Route:
    """Classify the most appropriate agent route for a given single task prompt."""
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
    """Route a task through TaskProfile analysis and policy validation."""
    cfg = config or load_config()
    routing_cfg = cfg.get("routing", {})

    profile = extract_task_profile(task, metadata)
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
        profile=profile,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Policy-as-Code Task Router & Decomposer for Codex-Antigravity.")
    parser.add_argument("--task", type=str, required=True, help="Task prompt or user query to route or decompose")
    parser.add_argument("--decompose", action="store_true", default=False, help="Decompose mixed task into TaskGraph DAG")
    parser.add_argument("--json", action="store_true", default=False, help="Output JSON result")
    args = parser.parse_args()

    if args.decompose:
        graph = decompose_task(args.task)
        if args.json:
            print(json.dumps(graph.to_dict(), indent=2, ensure_ascii=False))
        else:
            print("=" * 60)
            print(f"Goal       : {graph.goal}")
            print(f"Compound   : {'YES' if graph.is_compound else 'NO'}")
            print(f"Subtasks   : {len(graph.subtasks)}")
            print("-" * 60)
            for st in graph.subtasks:
                deps = f" (depends on: {', '.join(st.depends_on)})" if st.depends_on else ""
                parallel = " [parallel]" if st.parallelizable else ""
                print(f"  [{st.id}] ({st.type.value}) -> {st.route.value.upper()}{parallel}{deps}")
                print(f"    Query: {st.query}")
            print("=" * 60)
    else:
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
