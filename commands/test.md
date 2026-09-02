# /test

Execute project tests in an isolated runner and receive automated AI failure diagnosis.

## Usage

```text
/test [optional command or target path]
```

## Examples

```text
/test
/test tests/test_models.py
/test pytest -v -k "test_login"
/test cargo test --lib
```

## Description

Triggers `scripts/test_runner.py` to run tests in the target workspace. If all tests pass, returns a clean status report. If any tests fail, automatically packages the failing stack traces and queries Antigravity AI to diagnose the root cause and provide clear fix recommendations for Codex.

## Workflow

1. Detects project stack and test runner (pytest, unittest, cargo test, npm test, etc.).
2. Executes tests in a subprocess with timeout protection.
3. If failures occur, extracts stack traces and requests AI root-cause analysis.
4. Returns structured status, failing test names, and suggested fixes directly to the chat.
