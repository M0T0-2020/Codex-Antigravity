# /codebase

Inspect and scout the current codebase project status, architecture, and change impact.

## Usage

```text
/codebase [status | impact <module> | audit | <question>]
```

## Examples

```text
/codebase status
/codebase impact scripts/models.py
/codebase audit
/codebase Where is the authentication middleware configured?
```

## Description

Scouts the local project directory using `scripts/antigravity_delegate.py` with `--dir .` and dedicated codebase reconnaissance modes. Safely gathers structural facts, tech stack details, call graphs, or technical debt indicators without making any file modifications.

## Workflow

1. Runs fast pre-flight local scan of project files, manifests, and Git state.
2. Invokes Antigravity subagent with project directory mounted via `--add-dir`.
3. Returns concise architectural summary, module relationships, and citation of relevant files.
