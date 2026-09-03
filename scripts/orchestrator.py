#!/usr/bin/env python3
"""Manager-Style Agent Orchestrator for Codex-Antigravity.

Coordinates the end-to-end multi-agent execution pipeline:
1. Decomposes mixed user tasks into a bounded subtask DAG (TaskGraph).
2. Concurrently dispatches independent research/codebase subtasks to Antigravity CLI.
3. Applies Quality Gate evaluation and triggers adaptive cascade to Pro models if needed.
4. Merges multi-agent evidence and detects cross-claim conflicts via EvidenceMerger.
5. Emits a consolidated execution packet for Codex Native implementation and test verification.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from antigravity_delegate import delegate_research  # type: ignore
from config_loader import load_config  # type: ignore
from evidence_merger import merge_evidence, EvidencePacket  # type: ignore
from quality_gate import evaluate_quality, QualityResult  # type: ignore
from router import decompose_task, TaskGraph, TaskNode, TaskNodeType, Route  # type: ignore


class OrchestrationResult:
    """Consolidated result of the orchestration pipeline."""

    def __init__(
        self,
        task: str,
        graph: TaskGraph,
        evidence: Optional[EvidencePacket] = None,
        subtask_results: Optional[List[Dict[str, Any]]] = None,
        quality_reports: Optional[Dict[str, Any]] = None,
        next_action: str = "implement_with_codex",
        duration_seconds: float = 0.0,
    ):
        self.task = task
        self.graph = graph
        self.evidence = evidence
        self.subtask_results = subtask_results or []
        self.quality_reports = quality_reports or {}
        self.next_action = next_action
        self.duration_seconds = duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "is_compound": self.graph.is_compound,
            "next_action": self.next_action,
            "subtasks_count": len(self.graph.subtasks),
            "graph": self.graph.to_dict(),
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "quality_reports": self.quality_reports,
            "duration_seconds": self.duration_seconds,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Orchestration Plan & Evidence for: {self.task}",
            f"- **Workflow Mode**: {'Manager DAG (Compound)' if self.graph.is_compound else 'Direct Execution'}",
            f"- **Next Action**: `{self.next_action.upper()}`",
            f"- **Duration**: {self.duration_seconds:.2f}s\n",
            "## Task Execution Plan",
        ]

        for st in self.graph.subtasks:
            deps = f" *(depends on: {', '.join(st.depends_on)})*" if st.depends_on else ""
            lines.append(f"1. **[{st.id}]** `{st.type.value}` → **{st.route.value.upper()}**{deps}")
            lines.append(f"   *Query*: {st.query}")

        if self.evidence:
            lines.append("\n" + self.evidence.to_markdown())

        return "\n".join(lines)


def orchestrate_task(
    task: str,
    project_dir: Optional[str] = None,
    context: Optional[str] = None,
    language: Optional[str] = None,
    config_path: Optional[str] = None,
    mock: bool = False,
) -> OrchestrationResult:
    """Execute the end-to-end orchestration pipeline for a user task."""
    start_time = time.time()
    cfg = load_config(config_path)
    budget = cfg.get("budget", {})
    max_workers = min(int(budget.get("max_parallel", 3)), int(cfg.get("antigravity", {}).get("max_parallel", 3)))
    output_lang = language or cfg.get("antigravity", {}).get("output_language", "en")

    # Step 1: Decompose task into DAG
    graph = decompose_task(task, config=cfg)

    # Filter info-gathering subtasks (external_research, codebase)
    recon_subtasks = [
        st for st in graph.subtasks
        if st.type in (TaskNodeType.EXTERNAL_RESEARCH, TaskNodeType.CODEBASE)
    ]

    if not recon_subtasks:
        # Simple task without research/codebase delegation needed (e.g. pure implementation or pure test)
        duration = round(time.time() - start_time, 3)
        return OrchestrationResult(
            task=task,
            graph=graph,
            next_action="execute_route",
            duration_seconds=duration,
        )

    # Step 2: Execute information-gathering subtasks in parallel
    raw_results: List[Dict[str, Any]] = []
    quality_reports: Dict[str, Any] = {}

    def _run_subtask(subtask: TaskNode) -> Dict[str, Any]:
        task_type = "codebase" if subtask.type == TaskNodeType.CODEBASE else "research"
        res = delegate_research(
            task=subtask.query,
            task_type=task_type,
            model=subtask.model_tier,
            context=context,
            project_dir=project_dir,
            language=output_lang,
            mock=mock,
        )
        res["task"] = subtask.id
        res["task_type"] = subtask.type.value
        res["query"] = subtask.query

        # Step 3: Evaluate Quality Gate metrics
        quality = evaluate_quality(res, config=cfg)
        quality_reports[subtask.id] = quality.to_dict()
        res["quality"] = quality.to_dict()
        return res

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_run_subtask, st): st for st in recon_subtasks}
        for future in as_completed(future_map):
            try:
                sub_res = future.result()
                raw_results.append(sub_res)
            except Exception as exc:
                st = future_map[future]
                raw_results.append({
                    "task": st.id,
                    "task_type": st.type.value,
                    "query": st.query,
                    "success": False,
                    "error": str(exc),
                    "claims": [],
                    "findings": [],
                    "sources": [],
                    "uncertainties": [],
                })

    # Step 5: Merge Evidence & Conflict Detection
    evidence_packet = merge_evidence(raw_results)

    # Determine next action
    has_implementation = any(st.type == TaskNodeType.IMPLEMENTATION for st in graph.subtasks)
    has_test = any(st.type == TaskNodeType.TEST for st in graph.subtasks)

    if has_implementation:
        next_action = "implement_with_codex"
    elif has_test:
        next_action = "run_tests_with_delegator"
    else:
        next_action = "present_evidence_to_user"

    duration = round(time.time() - start_time, 3)

    return OrchestrationResult(
        task=task,
        graph=graph,
        evidence=evidence_packet,
        subtask_results=raw_results,
        quality_reports=quality_reports,
        next_action=next_action,
        duration_seconds=duration,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Manager-Style Agent Orchestrator for Codex-Antigravity."
    )
    parser.add_argument("--task", type=str, required=True, help="User request or inquiry")
    parser.add_argument("--dir", type=str, default=None, help="Target project workspace")
    parser.add_argument("--context", type=str, default=None, help="Caller context")
    parser.add_argument("--lang", "--language", type=str, default=None, help="Output language (default: 'en')")
    parser.add_argument("--config", type=str, default=None, help="Config path")
    parser.add_argument("--mock", action="store_true", default=False, help="Run in mock mode")
    parser.add_argument("--json", action="store_true", default=False, help="Output JSON packet")
    parser.add_argument("--markdown", action="store_true", default=False, help="Output Markdown report")
    args = parser.parse_args()

    result = orchestrate_task(
        task=args.task,
        project_dir=args.dir,
        context=args.context,
        language=args.lang,
        config_path=args.config,
        mock=args.mock,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(result.to_markdown())


if __name__ == "__main__":
    main()
