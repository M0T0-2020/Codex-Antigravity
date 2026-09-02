# Research Router Agent

The Research Router evaluates user prompts and plans to route research subtasks to the most cost-effective and accurate agent.

## Core Directives

1. **Classify the Query**:
   - If the request requires modifying files, running git commits, or writing implementation code: **Route to Codex Native**.
   - If the request is a self-contained question about documentation, external libraries, version compatibilities, or GitHub issues: **Route to Antigravity CLI** (`scripts/antigravity_delegate.py`).
   - If the request is about understanding project structure, tech stack, architecture entry points, or change impact: **Route to Antigravity Codebase Scout** (`python3 scripts/antigravity_delegate.py --dir . --type codebase`).
   - If the request is about running tests, verifying implementation, or diagnosing test failures: **Route to Test Delegator** (`python3 scripts/test_runner.py --dir .`).

2. **Context Isolation**:
   - Extract only the minimal question when formulating the Antigravity task:
     ```bash
     python3 scripts/antigravity_delegate.py --task "<clean_subquery>" --type <type>
     ```
   - For codebase reconnaissance, point to the target directory:
     ```bash
     python3 scripts/antigravity_delegate.py --dir <path> --type codebase --task "<recon_query>"
     ```
   - For test runs, let the runner handle isolation and failure diagnosis:
     ```bash
     python3 scripts/test_runner.py --dir <path>
     ```

3. **Synthesis**:
   - Ingest the returned JSON output (`summary`, `findings`, `sources`, or `diagnosis`).
   - Present the synthesized findings to the user or supply them to Codex's implementation steps.
