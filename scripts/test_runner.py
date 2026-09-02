#!/usr/bin/env python3
"""Test Execution and Failure Triage Engine for Coding Agents.

Executes tests in an isolated, controlled subshell, parses test metrics, and delegates
failure diagnosis to Antigravity CLI to produce actionable root-cause reports.

Features:
- Auto-detects test runners (pytest, unittest, cargo test, npm/vitest/jest, go test).
- Parses structured test results (passed, failed, skipped, errors, tracebacks).
- AI-driven failure triage: extracts stack traces and pinpoints root causes and fixes.
- Safe execution with strict timeouts and cwd isolation.
- Fast turnaround: zero AI overhead if all tests pass.
- Mock mode for offline testing and verification.
"""

import argparse
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codebase_analyzer import detect_project_stack  # type: ignore
from config_loader import load_config  # type: ignore
from models import find_agy_binary, resolve_model  # type: ignore
from safety import SafetyPolicy, SecurityError  # type: ignore

DIAGNOSIS_PROMPT_TEMPLATE = """You are an expert software QA and debugging agent assisting a Coding Agent (Codex).

Task:
Diagnose the test failures below and provide concise, actionable root-cause analysis and fix recommendations.

Project:
{PROJECT_NAME} ({PROJECT_LANGUAGES})

Failing Tests Summary:
{TEST_METRICS}

Failure Traces:
{FAILURES_TRACE}

{CODE_CONTEXT}

Strict Rules:
1. Focus only on diagnosing the root cause of the failures.
2. Provide concrete, file-specific guidance on how the coding agent should fix the issue.
3. Keep the explanation concise and direct.
4. Do NOT attempt to modify files directly.

Structure your response with these explicit section headings:
ROOT_CAUSE:
<Clear 1-3 sentence explanation of the underlying cause of the failure>

AFFECTED_COMPONENTS:
- <File:line or function name impacted>

SUGGESTED_FIX:
- <Step 1 or code snippet recommendation>
- <Step 2 or edge case to watch for>
"""


def detect_test_command(project_dir: str) -> str:
    """Determine the most appropriate test command for the project directory."""
    stack = detect_project_stack(project_dir)
    langs = stack.get("languages", [])

    if "Python" in langs:
        if shutil.which("pytest"):
            return "pytest -v"
        return "/usr/bin/python3 -m unittest discover tests"

    if "Rust" in langs:
        return "cargo test"

    if "JavaScript/TypeScript" in langs or "JavaScript" in langs:
        if stack.get("test_runner"):
            return stack["test_runner"]
        return "npm test"

    if "Go" in langs:
        return "go test ./..."

    if "C/C++" in langs:
        if os.path.isfile(os.path.join(project_dir, "Makefile")):
            return "make test"
        return "ctest"

    return "python3 -m unittest discover tests"


def parse_pytest_output(output: str) -> Dict[str, Any]:
    """Parse output from pytest."""
    metrics = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "total": 0}
    # Look for pytest summary line (usually the last = ... in ...s line)
    summary_line = ""
    for line in reversed(output.splitlines()):
        if re.search(r"in\s+[0-9\.]+s", line) and any(k in line for k in ["passed", "failed", "error", "skipped"]):
            summary_line = line
            break

    target_text = summary_line or output
    p_m = re.search(r"(\d+)\s+passed", target_text)
    f_m = re.search(r"(\d+)\s+failed", target_text)
    s_m = re.search(r"(\d+)\s+skipped", target_text)
    e_m = re.search(r"(\d+)\s+errors?", target_text)

    if p_m:
        metrics["passed"] = int(p_m.group(1))
    if f_m:
        metrics["failed"] = int(f_m.group(1))
    if s_m:
        metrics["skipped"] = int(s_m.group(1))
    if e_m:
        metrics["errors"] = int(e_m.group(1))
    metrics["total"] = metrics["passed"] + metrics["failed"] + metrics["errors"]

    failures: List[Dict[str, str]] = []
    fail_sections = re.findall(r"_{3,}\s*(.*?)\s*_{3,}\n(.*?)(?=\n_{3,}|\n={3,}|\Z)", output, re.DOTALL)
    for title, body in fail_sections:
        clean_title = title.strip()
        snippet = body.strip()
        if len(snippet) > 1500:
            snippet = snippet[:1500] + "\n... [traceback truncated]"
        failures.append({
            "test_name": clean_title,
            "traceback": snippet,
        })

    return {"metrics": metrics, "failures": failures}


def parse_unittest_output(output: str) -> Dict[str, Any]:
    """Parse output from Python unittest."""
    metrics = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "total": 0}
    ran_match = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+([0-9\.]+)s", output)
    if ran_match:
        metrics["total"] = int(ran_match.group(1))

    if "OK" in output:
        metrics["passed"] = metrics["total"]
    else:
        fail_match = re.search(r"failures=(\d+)", output)
        err_match = re.search(r"errors=(\d+)", output)
        skip_match = re.search(r"skipped=(\d+)", output)

        metrics["failed"] = int(fail_match.group(1)) if fail_match else 0
        metrics["errors"] = int(err_match.group(1)) if err_match else 0
        metrics["skipped"] = int(skip_match.group(1)) if skip_match else 0
        metrics["passed"] = max(0, metrics["total"] - metrics["failed"] - metrics["errors"] - metrics["skipped"])

    failures: List[Dict[str, str]] = []
    items = re.findall(r"(?:FAIL|ERROR):\s*(.*?)\n-+\n(.*?)(?=\n(?:FAIL|ERROR):|\n-{5,}|\n={5,}|\Z)", output, re.DOTALL)
    for title, body in items:
        snippet = body.strip()
        if len(snippet) > 1500:
            snippet = snippet[:1500] + "\n... [traceback truncated]"
        failures.append({
            "test_name": title.strip(),
            "traceback": snippet,
        })

    return {"metrics": metrics, "failures": failures}


def parse_generic_test_output(output: str, exit_code: int) -> Dict[str, Any]:
    """Fallback generic test output parser for cargo, npm, etc."""
    metrics = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "total": 0}

    cargo_match = re.search(r"test result:\s*(\w+)\.\s*(\d+)\s+passed;\s*(\d+)\s+failed;\s*(\d+)\s+ignored", output)
    if cargo_match:
        metrics["passed"] = int(cargo_match.group(2))
        metrics["failed"] = int(cargo_match.group(3))
        metrics["skipped"] = int(cargo_match.group(4))
        metrics["total"] = metrics["passed"] + metrics["failed"] + metrics["skipped"]
    else:
        if exit_code == 0:
            metrics["passed"] = 1
            metrics["total"] = 1
        else:
            metrics["failed"] = 1
            metrics["total"] = 1

    failures: List[Dict[str, str]] = []
    if exit_code != 0:
        lines = output.splitlines()
        tail_lines = "\n".join(lines[-40:]) if len(lines) > 40 else output
        failures.append({
            "test_name": "Test Suite Execution",
            "traceback": tail_lines.strip(),
        })

    return {"metrics": metrics, "failures": failures}


def parse_test_results(stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
    """Route test output to the appropriate parser."""
    combined = stdout + "\n" + stderr

    if "pytest" in combined or "passed" in combined and "in " in combined:
        parsed = parse_pytest_output(combined)
        if parsed["metrics"]["total"] > 0:
            return parsed

    if "Ran " in combined and " tests in " in combined:
        parsed = parse_unittest_output(combined)
        if parsed["metrics"]["total"] > 0:
            return parsed

    return parse_generic_test_output(combined, exit_code)


def run_test_command(
    command: Union[str, List[str]],
    project_dir: str,
    timeout: int = 180,
    safety_policy: Optional[SafetyPolicy] = None,
) -> Tuple[bool, str, str, int, float]:
    """Execute the test command within the project directory with shell=False and process-tree cleanup."""
    policy = safety_policy or SafetyPolicy()
    start_time = time.time()

    # 1. Validate workspace boundary
    try:
        abs_dir = str(policy.validate_workspace(project_dir))
    except SecurityError as exc:
        return (False, "", str(exc), -1, 0.0)

    # 2. Validate and parse command into safe argv list
    try:
        argv = policy.validate_command(command)
    except SecurityError as exc:
        return (False, "", str(exc), -1, 0.0)

    # 3. Sanitize environment
    env = policy.sanitize_environment()

    popen_kwargs: Dict[str, Any] = {
        "cwd": abs_dir,
        "shell": False,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": env,
    }
    if sys.platform != "win32":
        popen_kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen(argv, **popen_kwargs)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            duration = round(time.time() - start_time, 3)
            return (proc.returncode == 0, stdout, stderr, proc.returncode, duration)
        except subprocess.TimeoutExpired:
            # Kill child processes in the process group
            if sys.platform != "win32":
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    proc.kill()
            else:
                proc.kill()
            stdout, stderr = proc.communicate()
            duration = round(time.time() - start_time, 3)
            return (False, stdout, f"Test execution timed out after {timeout} seconds.", -1, duration)
    except Exception as exc:
        duration = round(time.time() - start_time, 3)
        return (False, "", str(exc), -1, duration)


def build_diagnosis_prompt(
    project_name: str,
    project_languages: List[str],
    metrics: Dict[str, int],
    failures: List[Dict[str, str]],
    code_context: Optional[str] = None,
) -> str:
    """Build the prompt for AI failure diagnosis."""
    metrics_str = (
        f"Total: {metrics.get('total', 0)}, "
        f"Passed: {metrics.get('passed', 0)}, "
        f"Failed: {metrics.get('failed', 0)}, "
        f"Errors: {metrics.get('errors', 0)}"
    )

    trace_parts = []
    for idx, f in enumerate(failures[:5], start=1):
        trace_parts.append(f"--- Failure #{idx}: {f.get('test_name', 'Unknown')} ---")
        trace_parts.append(f.get("traceback", "").strip())

    failures_trace = "\n".join(trace_parts)
    ctx_section = f"Code Context:\n{code_context.strip()}\n" if code_context else ""

    return DIAGNOSIS_PROMPT_TEMPLATE.format(
        PROJECT_NAME=project_name,
        PROJECT_LANGUAGES=", ".join(project_languages) if project_languages else "Unknown",
        TEST_METRICS=metrics_str,
        FAILURES_TRACE=failures_trace,
        CODE_CONTEXT=ctx_section,
    ).strip()


def parse_diagnosis_output(raw_text: str) -> Dict[str, Any]:
    """Parse ROOT_CAUSE, AFFECTED_COMPONENTS, and SUGGESTED_FIX from text."""
    root_cause = ""
    affected: List[str] = []
    suggested_fix: List[str] = []

    extracted = raw_text
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            for k in ["response", "content", "summary", "output"]:
                if k in data and isinstance(data[k], str):
                    extracted = data[k]
                    break
    except Exception:
        pass

    header_regex = re.compile(
        r"^(?:#{1,4}\s*)?(ROOT_CAUSE|AFFECTED_COMPONENTS|SUGGESTED_FIX)[:\s]*$",
        re.MULTILINE | re.IGNORECASE,
    )
    matches = list(header_regex.finditer(extracted))

    if matches:
        for i, match in enumerate(matches):
            sec_name = match.group(1).upper()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(extracted)
            content = extracted[start:end].strip()

            if sec_name == "ROOT_CAUSE":
                root_cause = content
            elif sec_name == "AFFECTED_COMPONENTS":
                for line in content.splitlines():
                    cleaned = re.sub(r"^(?:[-*•]|\d+[\.)])\s+", "", line.strip()).strip()
                    if cleaned:
                        affected.append(cleaned)
            elif sec_name == "SUGGESTED_FIX":
                for line in content.splitlines():
                    cleaned = re.sub(r"^(?:[-*•]|\d+[\.)])\s+", "", line.strip()).strip()
                    if cleaned:
                        suggested_fix.append(cleaned)

    if not root_cause:
        lines = extracted.strip().splitlines()
        if lines:
            root_cause = lines[0].strip()
            suggested_fix = [l.strip() for l in lines[1:5] if l.strip()]

    return {
        "root_cause": root_cause,
        "affected_components": affected,
        "suggested_fix": suggested_fix,
        "raw_text": extracted,
    }


def generate_mock_test_run(should_pass: bool = False) -> Tuple[bool, str, str, int, float]:
    """Generate mock test execution output."""
    if should_pass:
        out = "Ran 15 tests in 0.85s\n\nOK"
        return (True, out, "", 0, 0.85)
    else:
        out = """Ran 5 tests in 0.42s

======================================================================
FAIL: test_validate_token_expiry (tests.test_auth.TestAuth)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/workspace/tests/test_auth.py", line 42, in test_validate_token_expiry
    self.assertEqual(response.status_code, 401)
AssertionError: 200 != 401 : Token should have expired

----------------------------------------------------------------------
FAILED (failures=1)"""
        return (False, out, "", 1, 0.42)


def generate_mock_diagnosis() -> Dict[str, Any]:
    """Generate realistic mock diagnosis."""
    return {
        "root_cause": "Token expiration check uses local machine time rather than UTC, causing expired tokens to evaluate as currently valid.",
        "affected_components": [
            "src/auth.py:35 (validate_token)",
            "tests/test_auth.py:42 (test_validate_token_expiry)",
        ],
        "suggested_fix": [
            "Replace datetime.now() with datetime.now(timezone.utc) in src/auth.py line 35.",
            "Verify JWT exp claim comparison uses UTC seconds epoch.",
        ],
        "raw_text": "Mock AI Diagnosis",
    }


def delegate_test_run(
    project_dir: str = ".",
    command: Optional[str] = None,
    runner: Optional[str] = None,
    args: Optional[List[str]] = None,
    diagnose: bool = True,
    effort: str = "low",
    model: Optional[str] = None,
    timeout: Optional[int] = None,
    config_path: Optional[str] = None,
    mock: bool = False,
    mock_should_pass: bool = False,
) -> Dict[str, Any]:
    """Delegate test execution and optional failure diagnosis with security verification."""
    cfg = load_config(config_path)
    test_cfg = cfg.get("testing", {})
    t_out = timeout or test_cfg.get("default_timeout_seconds", 180)
    policy = SafetyPolicy(cfg)

    # Validate workspace boundary
    try:
        abs_dir = str(policy.validate_workspace(project_dir))
    except SecurityError as exc:
        return {
            "success": False,
            "command": command or runner or "unknown",
            "project_dir": project_dir,
            "metrics": {"total": 0, "passed": 0, "failed": 0, "errors": 1, "skipped": 0},
            "failures_count": 0,
            "failures": [],
            "duration_seconds": 0.0,
            "diagnosis": None,
            "error": f"Security boundary violation: {exc}",
        }

    stack = detect_project_stack(abs_dir)
    project_name = os.path.basename(abs_dir)

    if runner:
        test_cmd: Union[str, List[str]] = [runner] + (args or [])
        display_cmd = " ".join(test_cmd)
    elif command:
        test_cmd = command
        display_cmd = command
    else:
        test_cmd = detect_test_command(abs_dir)
        display_cmd = test_cmd

    # 1. Execute tests
    if mock:
        success, stdout, stderr, code, duration = generate_mock_test_run(should_pass=mock_should_pass)
    else:
        success, stdout, stderr, code, duration = run_test_command(
            command=test_cmd,
            project_dir=abs_dir,
            timeout=t_out,
            safety_policy=policy,
        )

    # 2. Parse results
    parsed = parse_test_results(stdout, stderr, code)
    metrics = parsed["metrics"]
    failures = parsed["failures"]

    result: Dict[str, Any] = {
        "success": success and metrics["failed"] == 0 and metrics["errors"] == 0,
        "command": display_cmd,
        "project_dir": abs_dir,
        "metrics": metrics,
        "failures_count": len(failures),
        "failures": failures,
        "duration_seconds": duration,
        "diagnosis": None,
        "error": None if success else (stderr.strip() or f"Tests failed with exit code {code}"),
    }

    # 3. AI Diagnosis if failures exist and diagnose=True
    if not result["success"] and diagnose and failures:
        if mock:
            result["diagnosis"] = generate_mock_diagnosis()
        else:
            binary_path = find_agy_binary(cfg.get("antigravity", {}).get("agy_path", "agy"))
            if binary_path:
                diag_prompt = build_diagnosis_prompt(
                    project_name=project_name,
                    project_languages=stack.get("languages", []),
                    metrics=metrics,
                    failures=failures,
                )
                diag_model = resolve_model(model or cfg.get("models", {}).get("diagnosis", "flash"))

                cmd_args = [
                    binary_path,
                    "-p", diag_prompt,
                    "--output-format", "json",
                    "--effort", effort,
                ]
                if diag_model:
                    cmd_args.extend(["--model", diag_model])

                # Enforce sandbox if configured
                if policy.build_agy_permissions().get("sandbox"):
                    cmd_args.append("--sandbox")

                safe_diag_env = policy.sanitize_environment()

                try:
                    proc = subprocess.run(
                        cmd_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=60,
                        env=safe_diag_env,
                    )
                    if proc.returncode == 0 and proc.stdout:
                        result["diagnosis"] = parse_diagnosis_output(proc.stdout)
                except Exception as exc:
                    result["diagnosis_error"] = str(exc)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Delegate test execution and failure diagnosis for Coding Agents."
    )
    parser.add_argument("--dir", type=str, default=".", help="Project workspace directory")
    parser.add_argument("--cmd", type=str, default=None, help="Explicit test command to execute")
    parser.add_argument("--runner", type=str, default=None, help="Specific test runner (e.g. pytest, cargo, npm)")
    parser.add_argument("--args", nargs="*", default=None, help="Arguments to pass to the test runner")
    parser.add_argument("--timeout", type=int, default=None, help="Test timeout in seconds")
    parser.add_argument("--no-diagnose", action="store_true", help="Skip AI diagnosis on failure")
    parser.add_argument("--effort", type=str, default="low", choices=["low", "medium", "high"])
    parser.add_argument("--model", type=str, default=None, help="Model for failure diagnosis")
    parser.add_argument("--config", type=str, default=None, help="Path to defaults.toml")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode")
    parser.add_argument("--mock-pass", action="store_true", help="In mock mode, simulate passing tests")
    parser.add_argument("--json", action="store_true", default=True, help="Output JSON (default)")
    parser.add_argument("--text", action="store_true", help="Output formatted human-readable summary")

    args = parser.parse_args()

    result = delegate_test_run(
        project_dir=args.dir,
        command=args.cmd,
        runner=args.runner,
        args=args.args,
        diagnose=not args.no_diagnose,
        effort=args.effort,
        model=args.model,
        timeout=args.timeout,
        config_path=args.config,
        mock=args.mock,
        mock_should_pass=args.mock_pass,
    )

    if args.text:
        print("=" * 60)
        print(f"Test Status : {'PASSED' if result['success'] else 'FAILED'}")
        print(f"Command     : {result['command']}")
        print(f"Duration    : {result['duration_seconds']}s")
        print(f"Metrics     : {result['metrics']['passed']} passed, {result['metrics']['failed']} failed, {result['metrics']['errors']} errors (total {result['metrics']['total']})")

        if result.get("failures"):
            print("\nFailing Tests:")
            for f in result["failures"]:
                print(f"  ✖ {f['test_name']}")

        if result.get("diagnosis"):
            diag = result["diagnosis"]
            print("\n" + "=" * 25 + " AI Diagnosis " + "=" * 25)
            print(f"Root Cause:\n{diag.get('root_cause')}\n")
            if diag.get("affected_components"):
                print("Affected Components:")
                for c in diag["affected_components"]:
                    print(f"  - {c}")
            if diag.get("suggested_fix"):
                print("\nSuggested Fix:")
                for fix in diag["suggested_fix"]:
                    print(f"  • {fix}")
        print("=" * 60)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
