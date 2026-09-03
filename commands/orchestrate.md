# /orchestrate

Execute full manager-style agent orchestration: decompose compound tasks into a DAG, run parallel research and codebase scouts, evaluate quality gates, merge evidence with conflict detection, and prepare an implementation plan for Codex.

## Usage

```text
/orchestrate <complex task prompt>
```

## Description

Triggers the full Codex-Antigravity v1.2 orchestration pipeline:
1. **Task Decomposer**: Generates a subtask DAG (TaskGraph).
2. **Parallel Scouts**: Dispatches external research and codebase reconnaissance in parallel.
3. **Quality Gate & Cascade**: Automatically evaluates factual coverage and primary sources; cascades from Flash to Pro models if quality is insufficient.
4. **Evidence Merger**: Synthesizes findings and detects contradictions/version discrepancies across subtasks.
5. **Codex Native Handoff**: Produces structured evidence and next actions for immediate code implementation and follow-up testing.

## Workflow

1. Take the user's request.
2. Execute:
   ```bash
   python3 scripts/orchestrator.py --task "<request>" --markdown
   ```
3. Codex ingests the verified claims and findings, proceeds with implementation, and runs tests.
