# /research-deep

Perform an extensive, in-depth architectural or codebase-wide research task using native Codex reasoning.

## Usage

```text
/research-deep <complex investigation topic>
```

## Description

Executes deep multi-step investigation directly inside Codex. Useful for whole-repository dependency tracing, performance profiling analysis, complex architecture decisions, and deep bug diagnosis.

## Workflow

1. Perform initial structural search and analysis across the repository.
2. If external documentation or specific third-party library details are required, delegate small subquestions to Antigravity:
   ```bash
   python3 scripts/antigravity_delegate.py --task "<specific library subquestion>" --type docs
   ```
3. Synthesize code findings and external documentation into a comprehensive architectural report.
