#!/usr/bin/env python3
"""Antigravity CLI Delegation Wrapper for Codex.

This script executes a lightweight, read-only research task on Google Antigravity CLI (`agy`)
and returns a clean, structured JSON result to Codex.

Features:
- Prompt isolation and research-only constraints (no file edits, no architecture decisions).
- Timeout enforcement and process lifecycle management.
- Transient failure auto-retry.
- Graceful handling of AGY JSON output and section parsing (SUMMARY, FINDINGS, SOURCES, UNCERTAINTIES).
- Output character limiting to protect Codex context window.
- Parallel delegation of multiple subqueries.
- Mock mode for offline testing and verification.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codebase_analyzer import analyze_codebase, format_codebase_context  # type: ignore
from config_loader import load_config  # type: ignore
from models import find_agy_binary, resolve_model  # type: ignore

RESEARCH_PROMPT_TEMPLATE = """You are a lightweight research subagent assisting a Coding Agent.

Task:
{TASK}

{TYPE_SPECIFIC_INSTRUCTIONS}

{CONTEXT_SECTION}

Strict Rules:
1. Research and fact-gathering only.
2. Do NOT write or modify files.
3. Do NOT make architectural or final implementation decisions.
4. Prefer primary sources (official documentation, GitHub repositories, release notes).
5. Clearly separate verified facts from inference.
6. Keep the answer concise, structured, and factual.
7. Always cite URLs, versions, or source names where possible.

Please structure your response with these explicit section headings:
SUMMARY:
<Concise 1-3 sentence summary of the findings>

FINDINGS:
- <Key finding 1>
- <Key finding 2>

SOURCES:
- <Source URL or primary documentation reference>

UNCERTAINTIES:
- <Any unverified points, version caveats, or unknowns>
"""

TYPE_INSTRUCTIONS = {
    "research": "Focus on gathering current, accurate facts, documentation, or issue discussions.",
    "docs": "Focus on official API documentation, method signatures, parameter types, and version differences.",
    "compare": "Provide an objective comparison: pros/cons, compatibility, performance, and key trade-offs.",
    "repo": "Inspect repository structure, license, dependencies, and requirements without editing.",
    "issue": "Search for related GitHub issues, workarounds, bug status, and pull request references.",
    "codebase": "Inspect the local codebase structure, architecture, entry points, technology stack, and implementation status without modifying files.",
    "impact": "Trace call graphs, component dependencies, and potential breaking changes/side effects if the specified module or function is modified.",
    "audit": "Review code quality, security patterns, technical debt, deprecations, and TODO items in the codebase.",
}


def build_research_prompt(
    task: str,
    task_type: str = "research",
    context: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> str:
    """Build a constrained research prompt preventing file modifications."""
    type_inst = TYPE_INSTRUCTIONS.get(task_type.lower(), TYPE_INSTRUCTIONS["research"])

    context_parts = []
    if context and context.strip():
        # Truncate context to avoid token bloat
        clean_ctx = context.strip()
        if len(clean_ctx) > 3000:
            clean_ctx = clean_ctx[:3000] + "... [context truncated]"
        context_parts.append(f"Context from caller:\n{clean_ctx}\n")

    # If project_dir is provided or task is codebase-oriented, inject codebase reconnaissance
    if project_dir or task_type.lower() in ("codebase", "impact", "audit"):
        target_p = project_dir or "."
        if os.path.isdir(target_p):
            try:
                analysis = analyze_codebase(target_p)
                cb_summary = format_codebase_context(analysis)
                context_parts.append(f"Target Project Context:\n{cb_summary}\n")
            except Exception:
                pass

    context_sec = "\n".join(context_parts) if context_parts else ""

    return RESEARCH_PROMPT_TEMPLATE.format(
        TASK=task.strip(),
        TYPE_SPECIFIC_INSTRUCTIONS=type_inst,
        CONTEXT_SECTION=context_sec,
    ).strip()


def parse_structured_output(raw_text: str, max_chars: int = 20000) -> Dict[str, Any]:
    """Extract SUMMARY, FINDINGS, SOURCES, and UNCERTAINTIES sections from text."""
    if len(raw_text) > max_chars:
        raw_text = raw_text[:max_chars] + "\n... [Output truncated at max_output_chars limit]"

    # If raw_text is JSON from agy print mode, extract message text
    extracted_text = raw_text
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            # Check standard agy json output structures
            if "response" in data and isinstance(data["response"], str):
                extracted_text = data["response"]
            elif "content" in data and isinstance(data["content"], str):
                extracted_text = data["content"]
            elif "summary" in data and isinstance(data["summary"], str):
                extracted_text = data["summary"]
            elif "output" in data and isinstance(data["output"], str):
                extracted_text = data["output"]
            elif "messages" in data and isinstance(data["messages"], list):
                msgs = [m.get("content", "") for m in data["messages"] if isinstance(m, dict)]
                if msgs:
                    extracted_text = "\n".join(msgs)
    except Exception:
        pass

    summary = ""
    findings: List[str] = []
    sources: List[str] = []
    uncertainties: List[str] = []

    # Regex patterns for section headers
    header_regex = re.compile(
        r"^(?:#{1,4}\s*)?(SUMMARY|FINDINGS|SOURCES|UNCERTAINTIES)[:\s]*$",
        re.MULTILINE | re.IGNORECASE,
    )

    matches = list(header_regex.finditer(extracted_text))

    if matches:
        for i, match in enumerate(matches):
            section_title = match.group(1).upper()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(extracted_text)
            section_content = extracted_text[start_pos:end_pos].strip()

            if section_title == "SUMMARY":
                summary = section_content
            elif section_title == "FINDINGS":
                findings = _extract_bullet_points(section_content)
            elif section_title == "SOURCES":
                sources = _extract_bullet_points(section_content)
            elif section_title == "UNCERTAINTIES":
                uncertainties = _extract_bullet_points(section_content)

    # Fallback if specific section headers were not used by model
    if not summary and not findings:
        lines = extracted_text.strip().splitlines()
        if lines:
            summary = lines[0].strip()
            rest = "\n".join(lines[1:]).strip()
            if rest:
                findings = _extract_bullet_points(rest)

    # Extract URL sources if sources list is empty
    if not sources:
        url_pattern = re.compile(r"https?://[^\s)\]>\"']+")
        found_urls = list(dict.fromkeys(url_pattern.findall(extracted_text)))
        if found_urls:
            sources = found_urls

    return {
        "summary": summary or extracted_text.strip()[:500],
        "findings": findings if findings else ([extracted_text.strip()] if extracted_text.strip() else []),
        "sources": sources,
        "uncertainties": uncertainties,
        "raw_text": extracted_text,
    }


def _extract_bullet_points(content: str) -> List[str]:
    """Parse lines into a list of bullet points."""
    items: List[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove bullet markers like -, *, 1., etc.
        cleaned = re.sub(r"^(?:[-*•]|\d+[\.)])\s+", "", line).strip()
        if cleaned:
            items.append(cleaned)
    return items


def execute_agy_cli(
    prompt: str,
    agy_path: str,
    effort: str = "low",
    model: Optional[str] = None,
    timeout: int = 120,
    sandbox: bool = False,
    project_dir: Optional[str] = None,
) -> Tuple[bool, str, str, int]:
    """Execute the agy command in a subprocess.

    Returns:
      (success, stdout, stderr, returncode)
    """
    cmd = [
        agy_path,
        "-p", prompt,
        "--output-format", "json",
    ]

    if project_dir:
        abs_proj = os.path.abspath(project_dir)
        cmd.extend(["--add-dir", abs_proj])

    # Claude and certain external models in agy do not accept --effort flag
    supports_effort = True
    if model:
        m_lower = model.lower()
        if "claude" in m_lower or "gpt" in m_lower:
            supports_effort = False

    if effort and supports_effort:
        cmd.extend(["--effort", effort])

    if model:
        cmd.extend(["--model", model])

    if sandbox:
        cmd.append("--sandbox")

    # Set up safe execution environment
    env = dict(os.environ)
    cwd = os.path.abspath(project_dir) if project_dir and os.path.isdir(project_dir) else None

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            is_ok = (proc.returncode == 0)
            # If stdout is JSON error response from agy, mark failure and capture message
            if stdout:
                try:
                    data = json.loads(stdout)
                    if isinstance(data, dict) and data.get("status") == "ERROR":
                        is_ok = False
                        stderr = data.get("error") or stderr
                except Exception:
                    pass

            return (is_ok, stdout, stderr, proc.returncode)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return (False, stdout, f"Execution timed out after {timeout} seconds.", -1)
    except Exception as exc:
        return (False, "", str(exc), -1)


def generate_mock_response(task: str, task_type: str, project_dir: Optional[str] = None) -> str:
    """Generate a realistic mock response for testing and dry-runs."""
    if task_type == "codebase":
        p_name = os.path.basename(os.path.abspath(project_dir)) if project_dir else "current project"
        return f"""SUMMARY:
Codebase reconnaissance completed for '{p_name}'. Identified tech stack, module layout, and key entry points.

FINDINGS:
- Project is structured cleanly into modules with separate configuration and test suites.
- Primary entry points and CLI commands are defined and mapped.
- Test runner and test cases detected and operational.

SOURCES:
- Local codebase inspection: {project_dir or '.'}
- Project manifests and directory hierarchy

UNCERTAINTIES:
- Upstream external service configurations require environment variables at runtime.
"""
    elif task_type == "impact":
        return f"""SUMMARY:
Impact analysis for '{task}': modifications are isolated with localized regression risk.

FINDINGS:
- Callers are constrained to internal module boundaries.
- Public CLI interface flags remain backward-compatible.
- Existing unit tests cover the affected interface.

SOURCES:
- Local call graph and dependency inspection

UNCERTAINTIES:
- Verify third-party plugin integrations if applicable.
"""
    elif task_type == "audit":
        return f"""SUMMARY:
Codebase audit completed. No critical security vulnerabilities or architectural anti-patterns found.

FINDINGS:
- Read-only constraints are enforced for inspection subtasks.
- Process execution includes robust timeout and error status checks.
- Code style conforms to standard conventions.

SOURCES:
- Static analysis of project workspace

UNCERTAINTIES:
- None
"""

    return f"""SUMMARY:
Mock research completed for task: '{task}'. Primary sources verified compatibility and documentation.

FINDINGS:
- Requirement and version constraints are verified and up-to-date.
- No breaking changes detected for the requested feature or API.
- Implementation pattern is standard and recommended by official guides.

SOURCES:
- https://example.com/docs/api-reference
- https://github.com/example/project/releases/tag/v1.0.0

UNCERTAINTIES:
- Upstream minor version release may change experimental flags.
"""


def delegate_research(
    task: str,
    task_type: str = "research",
    effort: Optional[str] = None,
    model: Optional[str] = None,
    context: Optional[str] = None,
    project_dir: Optional[str] = None,
    timeout: Optional[int] = None,
    max_chars: Optional[int] = None,
    config_path: Optional[str] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Delegate a lightweight research task to Antigravity CLI."""
    start_time = time.time()
    cfg = load_config(config_path)
    antigravity_cfg = cfg.get("antigravity", {})
    safety_cfg = cfg.get("safety", {})

    if not antigravity_cfg.get("enabled", True):
        return {
            "success": False,
            "error": "Antigravity delegation is disabled in configuration.",
            "summary": "",
            "findings": [],
            "sources": [],
            "uncertainties": [],
            "usage": {"duration_seconds": 0.0},
        }

    # Parameter resolution
    eff = effort or antigravity_cfg.get("default_effort", "low")
    t_out = timeout if timeout is not None else antigravity_cfg.get("timeout_seconds", 120)
    max_c = max_chars if max_chars is not None else antigravity_cfg.get("max_output_chars", 20000)
    retry_limit = antigravity_cfg.get("retry_count", 1)

    resolved_model = resolve_model(model, config_models=cfg.get("models", {}))

    prompt = build_research_prompt(task, task_type=task_type, context=context, project_dir=project_dir)

    # Handle mock mode
    if mock:
        mock_text = generate_mock_response(task, task_type, project_dir=project_dir)
        parsed = parse_structured_output(mock_text, max_chars=max_c)
        duration = round(time.time() - start_time, 3)
        return {
            "success": True,
            "summary": parsed["summary"],
            "findings": parsed["findings"],
            "sources": parsed["sources"],
            "uncertainties": parsed["uncertainties"],
            "usage": {
                "duration_seconds": duration,
                "model": resolved_model or "mock-gemini",
                "effort": eff,
                "retries": 0,
                "mock": True,
            },
            "project_dir": os.path.abspath(project_dir) if project_dir else None,
            "error": None,
        }

    # Locate binary
    custom_agy = antigravity_cfg.get("agy_path", "agy")
    binary_path = find_agy_binary(custom_agy)
    if not binary_path:
        return {
            "success": False,
            "error": "Antigravity CLI executable ('agy') not found. Ensure it is installed and on PATH (~/.local/bin/agy).",
            "summary": "",
            "findings": [],
            "sources": [],
            "uncertainties": [],
            "usage": {"duration_seconds": round(time.time() - start_time, 3)},
        }

    retries_used = 0
    last_error = ""
    stdout_result = ""

    for attempt in range(retry_limit + 1):
        success, stdout, stderr, code = execute_agy_cli(
            prompt=prompt,
            agy_path=binary_path,
            effort=eff,
            model=resolved_model,
            timeout=t_out,
            sandbox=False,
            project_dir=project_dir,
        )

        if success and stdout.strip():
            stdout_result = stdout
            break

        retries_used = attempt
        last_error = stderr.strip() or f"Process exited with status code {code}"
        if attempt < retry_limit:
            time.sleep(1.0)  # Brief pause before retry

    duration = round(time.time() - start_time, 3)

    if not stdout_result:
        return {
            "success": False,
            "error": f"Antigravity delegation failed after {retries_used + 1} attempt(s): {last_error}",
            "summary": "",
            "findings": [],
            "sources": [],
            "uncertainties": [],
            "usage": {
                "duration_seconds": duration,
                "model": resolved_model or "default",
                "effort": eff,
                "retries": retries_used,
            },
        }

    parsed = parse_structured_output(stdout_result, max_chars=max_c)
    return {
        "success": True,
        "summary": parsed["summary"],
        "findings": parsed["findings"],
        "sources": parsed["sources"],
        "uncertainties": parsed["uncertainties"],
        "usage": {
            "duration_seconds": duration,
            "model": resolved_model or "default",
            "effort": eff,
            "retries": retries_used,
        },
        "error": None,
    }


def delegate_parallel(
    tasks: List[str],
    task_type: str = "research",
    max_workers: int = 3,
    project_dir: Optional[str] = None,
    config_path: Optional[str] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Execute multiple subtasks concurrently and aggregate findings."""
    start_time = time.time()
    cfg = load_config(config_path)
    limit = min(max_workers, cfg.get("antigravity", {}).get("max_parallel", 3))

    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=limit) as executor:
        future_to_task = {
            executor.submit(
                delegate_research,
                task=t,
                task_type=task_type,
                project_dir=project_dir,
                config_path=config_path,
                mock=mock,
            ): t
            for t in tasks
        }
        for future in as_completed(future_to_task):
            task_name = future_to_task[future]
            try:
                res = future.result()
                res["task"] = task_name
                results.append(res)
            except Exception as exc:
                results.append({
                    "task": task_name,
                    "success": False,
                    "error": str(exc),
                    "summary": "",
                    "findings": [],
                    "sources": [],
                    "uncertainties": [],
                })

    all_success = any(r.get("success", False) for r in results)
    merged_findings = []
    merged_sources = []
    merged_summaries = []

    for r in results:
        if r.get("summary"):
            merged_summaries.append(f"[{r.get('task')}] {r['summary']}")
        for f in r.get("findings", []):
            merged_findings.append(f"[{r.get('task')}] {f}")
        for s in r.get("sources", []):
            if s not in merged_sources:
                merged_sources.append(s)

    duration = round(time.time() - start_time, 3)

    return {
        "success": all_success,
        "summary": "\n".join(merged_summaries),
        "findings": merged_findings,
        "sources": merged_sources,
        "subtasks_count": len(tasks),
        "subtask_results": results,
        "project_dir": os.path.abspath(project_dir) if project_dir else None,
        "usage": {
            "duration_seconds": duration,
            "parallel_workers": limit,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Delegate lightweight research to Google Antigravity CLI (agy)."
    )
    parser.add_argument("--task", type=str, help="Research task query")
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Target project workspace directory for codebase reconnaissance",
    )
    parser.add_argument(
        "--type",
        type=str,
        default="research",
        choices=["research", "docs", "compare", "repo", "issue", "codebase", "impact", "audit"],
        help="Type of investigation",
    )
    parser.add_argument(
        "--effort",
        type=str,
        choices=["low", "medium", "high"],
        default=None,
        help="Reasoning effort level (default: from config, usually 'low')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model tier or name (flash, pro, etc.)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout in seconds",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Max output length in characters",
    )
    parser.add_argument(
        "--context",
        type=str,
        default=None,
        help="Optional minimal background context",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to defaults.toml configuration",
    )
    parser.add_argument(
        "--subtasks",
        type=str,
        nargs="+",
        help="Run multiple subtasks in parallel",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode without invoking live CLI",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="Output in JSON format (default: True)",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Output in human-readable text format instead of JSON",
    )

    args = parser.parse_args()

    if not args.task and not args.subtasks:
        parser.error("Either --task or --subtasks must be specified.")

    if args.subtasks:
        result = delegate_parallel(
            tasks=args.subtasks,
            task_type=args.type,
            project_dir=args.dir,
            config_path=args.config,
            mock=args.mock,
        )
    else:
        result = delegate_research(
            task=args.task,
            task_type=args.type,
            effort=args.effort,
            model=args.model,
            context=args.context,
            project_dir=args.dir,
            timeout=args.timeout,
            max_chars=args.max_chars,
            config_path=args.config,
            mock=args.mock,
        )

    if args.text:
        print("=" * 60)
        print(f"Status   : {'SUCCESS' if result.get('success') else 'FAILED'}")
        if result.get("error"):
            print(f"Error    : {result['error']}")
        print(f"Summary  : {result.get('summary')}")
        print("\nFindings :")
        for f in result.get("findings", []):
            print(f"  • {f}")
        if result.get("sources"):
            print("\nSources  :")
            for s in result.get("sources", []):
                print(f"  - {s}")
        if result.get("uncertainties"):
            print("\nUncertainties:")
            for u in result.get("uncertainties", []):
                print(f"  ? {u}")
        print("=" * 60)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
