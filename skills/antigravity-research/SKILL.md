---
name: antigravity-research
description: Delegate lightweight, read-only research and documentation tasks to Google Antigravity CLI (agy).
---

# Antigravity Research

Delegate lightweight, read-only research questions, API lookups, library comparisons, and GitHub issue investigations to the Antigravity CLI (`agy`) subagent.

## When to Delegate

Use Antigravity delegation for:
- Official documentation lookup and API signatures.
- Web research on recent releases and breaking changes.
- GitHub issue investigation and bug workarounds.
- Library and framework comparison (pros/cons, compatibility).
- Checking current dependency versions and requirements.
- Searching for papers, references, and related implementations.
- **Codebase status & architecture reconnaissance**: Project layout, tech stack, entry points.
- **Change impact analysis**: Finding callers, dependencies, and blast radius before edits.
- **Codebase audits**: Static identification of tech debt, deprecated APIs, and TODOs.

## When NOT to Delegate

Do NOT use Antigravity delegation for:
- Writing or modifying code in the repository.
- Editing files or creating commits.
- Architectural decisions (Codex determines architecture).
- Security-sensitive decisions.
- Final engineering judgments (Codex always makes the final decision).

## Workflow

1. **Extract minimal subtask**:
   Isolate the specific question or reconnaissance target (e.g., "Find current ONNX Runtime CUDA requirements" or "Map module architecture of this repo").
2. **Invoke delegate script**:
   ```bash
   # External documentation lookup
   python3 scripts/antigravity_delegate.py \
     --task "Check ONNX Runtime 1.24 CUDA compatibility" \
     --type docs \
     --effort low

   # Local codebase reconnaissance
   python3 scripts/antigravity_delegate.py \
     --dir . \
     --type codebase \
     --task "Map project entry points and module dependencies"

   # Impact analysis before refactoring
   python3 scripts/antigravity_delegate.py \
     --dir . \
     --type impact \
     --task "Impact of modifying execute_agy_cli signature"
   ```
3. **Parse structured JSON**:
   Read `summary`, `findings`, `sources`, and `uncertainties`.
4. **Verify critical claims**:
   Cross-reference findings with primary sources cited in `sources`.
5. **Continue engineering in Codex**:
   Use the verified findings to inform your implementation, refactoring, or bug fix.

## Command Options

| Argument | Description | Default |
| --- | --- | --- |
| `--task "..."` | The research query to investigate | Required |
| `--dir <path>` | Target project directory for local codebase reconnaissance | None |
| `--type` | `research`, `docs`, `compare`, `repo`, `issue`, `codebase`, `impact`, `audit` | `research` |
| `--effort` | `low`, `medium`, `high` | `low` |
| `--model` | Model tier (`flash`, `pro`) or specific model name | config default |
| `--timeout` | Execution timeout in seconds | `120` |
| `--context` | Minimal background context snippet | None |
| `--subtasks` | List of subqueries for parallel execution | None |

## Example Outputs

The script returns clean JSON:

```json
{
  "success": true,
  "summary": "ONNX Runtime 1.20+ supports CUDA 11.8 and 12.x.",
  "findings": [
    "CUDA 12.x builds require cuDNN 9.x.",
    "TensorRT execution provider is compatible with TensorRT 10.x."
  ],
  "sources": [
    "https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html"
  ],
  "uncertainties": [],
  "usage": {
    "duration_seconds": 6.4,
    "model": "gemini-2.5-flash",
    "effort": "low"
  }
}
```
