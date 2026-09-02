---
name: test-delegation
description: Delegate test execution and AI-powered failure triage to the Antigravity test runner.
---

# Test Delegation & Failure Triage

Delegate running test suites, capturing test metrics, and diagnosing test failures to the isolated Antigravity test runner (`scripts/test_runner.py`).

## When to Delegate Tests

Use Test Delegation when:
- Verifying an implementation or bug fix after writing code.
- Running full or partial test suites without bloating the coding agent context window with hundreds of lines of stack traces.
- Diagnosing why a test failed: obtaining the root cause and concrete fix recommendations rather than raw tracebacks.
- Running smoke tests or regression checks across the project.

## When NOT to Delegate Tests

Do NOT delegate test execution when:
- Writing or refactoring production test code (Codex writes the code).
- Interactive debugging requiring stepping with pdb/lldb.
- Environment configuration changes requiring manual user input.

## Workflow

1. **Invoke Test Delegation**:
   Run the test runner script on the project workspace:
   ```bash
   # Auto-detect test runner and run tests with AI failure diagnosis
   python3 scripts/test_runner.py --dir .

   # Run a specific test command
   python3 scripts/test_runner.py --dir . --cmd "pytest tests/test_auth.py -v"
   ```

2. **Ingest Structured JSON Result**:
   - If tests passed (`"success": true`), proceed immediately without AI diagnosis overhead:
     ```json
     {
       "success": true,
       "metrics": { "passed": 15, "failed": 0, "errors": 0, "total": 15 },
       "duration_seconds": 0.85
     }
     ```
   - If tests failed (`"success": false`), inspect `"failures"` and `"diagnosis"`:
     ```json
     {
       "success": false,
       "metrics": { "passed": 4, "failed": 1, "errors": 0, "total": 5 },
       "failures": [
         {
           "test_name": "test_validate_token_expiry",
           "traceback": "..."
         }
       ],
       "diagnosis": {
         "root_cause": "Token expiration check uses local time instead of UTC.",
         "affected_components": ["src/auth.py:35"],
         "suggested_fix": [
           "Replace datetime.now() with datetime.now(timezone.utc) in src/auth.py."
         ]
       }
     }
     ```

3. **Apply Fix in Codex**:
   Use the concise `diagnosis` to pinpoint and fix the bug in your codebase, then rerun the delegated test to verify.

## Command Options

| Option | Description | Default |
| --- | --- | --- |
| `--dir <path>` | Project workspace directory | `.` |
| `--cmd "<cmd>"` | Explicit test command | Auto-detected (`pytest`, `cargo test`, `npm test`, etc.) |
| `--timeout <sec>` | Test execution timeout in seconds | `180` |
| `--no-diagnose` | Skip AI diagnosis on failure | False |
| `--effort <level>` | AI diagnosis reasoning effort (`low`, `medium`, `high`) | `low` |
| `--text` | Format output for terminal display | False (default JSON) |
| `--mock` | Dry-run mock mode for testing | False |
