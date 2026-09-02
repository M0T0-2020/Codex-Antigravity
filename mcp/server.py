#!/usr/bin/env python3
"""Model Context Protocol (MCP) server for Antigravity delegation.

Exposes Antigravity research capabilities as MCP tools over standard JSON-RPC 2.0 stdio:
- antigravity_research: fast fact gathering and documentation lookup.
- antigravity_compare: compare libraries, versions, or frameworks.
- antigravity_inspect_docs: inspect official API docs and signatures.
- antigravity_inspect_repo: inspect repository structure and dependencies.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure scripts directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from antigravity_delegate import delegate_research  # type: ignore
from models import search_models  # type: ignore
from test_runner import delegate_test_run  # type: ignore

SERVER_INFO = {
    "name": "antigravity-mcp-server",
    "version": "1.1.0",
}

TOOLS = [
    {
        "name": "antigravity_research",
        "description": "Delegate a lightweight, read-only research or fact-gathering query to Antigravity CLI.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The specific research question or topic to investigate.",
                },
                "depth": {
                    "type": "string",
                    "enum": ["quick", "normal"],
                    "default": "quick",
                    "description": "Research depth ('quick' for fast scout, 'normal' for deeper check).",
                },
                "model": {
                    "type": "string",
                    "description": "Optional model ID or alias (e.g. 'gemini-3.8-flash-high', 'flash', 'pro'). Defaults to config.",
                },
                "context": {
                    "type": "string",
                    "description": "Optional minimal context snippet to assist investigation.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "antigravity_list_models",
        "description": "List or search available models supported by Antigravity CLI for research tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional search term to filter models (e.g. 'flash', 'pro', 'claude').",
                },
            },
        },
    },
    {
        "name": "antigravity_compare",
        "description": "Compare two technologies, libraries, algorithms, or versions objectively.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_a": {
                    "type": "string",
                    "description": "First item or technology to compare.",
                },
                "item_b": {
                    "type": "string",
                    "description": "Second item or technology to compare.",
                },
                "criteria": {
                    "type": "string",
                    "description": "Specific criteria or aspects to compare (e.g. performance, ease of use, license).",
                },
            },
            "required": ["item_a", "item_b"],
        },
    },
    {
        "name": "antigravity_inspect_docs",
        "description": "Lookup official documentation, method signatures, parameter types, and API changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "library": {
                    "type": "string",
                    "description": "Library or framework name (e.g. onnxruntime, torch, pydantic).",
                },
                "topic": {
                    "type": "string",
                    "description": "API method, class, feature, or version query.",
                },
            },
            "required": ["library", "topic"],
        },
    },
    {
        "name": "antigravity_inspect_repo",
        "description": "Inspect a remote repository's structure, license, and dependency requirements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_or_path": {
                    "type": "string",
                    "description": "GitHub repository (owner/repo) or URL.",
                },
                "question": {
                    "type": "string",
                    "description": "Question regarding dependencies, structure, or setup.",
                },
            },
            "required": ["repo_or_path", "question"],
        },
    },
    {
        "name": "antigravity_inspect_codebase",
        "description": "Inspect local codebase structure, tech stack, architecture, entry points, or change impact.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target project directory (defaults to current directory '.').",
                    "default": ".",
                },
                "focus": {
                    "type": "string",
                    "enum": ["codebase", "impact", "audit"],
                    "default": "codebase",
                    "description": "Inspection focus ('codebase' for structure/stack, 'impact' for change blast radius, 'audit' for code quality/TODOs).",
                },
                "query": {
                    "type": "string",
                    "description": "Specific question or target module to investigate.",
                },
            },
        },
    },
    {
        "name": "antigravity_run_tests",
        "description": "Execute tests in the target project workspace, collect metrics, and auto-diagnose failures with safety constraints.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target project directory within authorized workspace boundary (defaults to current directory '.').",
                    "default": ".",
                },
                "runner": {
                    "type": "string",
                    "enum": ["pytest", "python", "python3", "cargo", "npm", "pnpm", "yarn", "vitest", "jest", "go", "ctest", "make"],
                    "description": "Allowed test runner (e.g. 'pytest', 'cargo', 'npm', 'vitest'). Auto-detected if omitted.",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Arguments passed to runner (e.g. ['-v', 'tests/test_foo.py']).",
                },
                "command": {
                    "type": "string",
                    "description": "Legacy test command string (validated and parsed securely with shell=False).",
                },
                "diagnose": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to perform AI failure diagnosis when tests fail.",
                },
            },
        },
    },
    {
        "name": "antigravity_diagnose_failure",
        "description": "Diagnose an arbitrary test failure, stack trace, or compiler error with root-cause analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_trace": {
                    "type": "string",
                    "description": "The error stack trace or compiler diagnostic message.",
                },
                "context": {
                    "type": "string",
                    "description": "Optional code snippet or file context related to the failure.",
                },
            },
            "required": ["error_trace"],
        },
    },
]


def call_tool(name: str, arguments: Dict[str, Any], mock: bool = False) -> Dict[str, Any]:
    """Dispatch tool call to delegate_research."""
    if name == "antigravity_research":
        query = arguments.get("query", "")
        depth = arguments.get("depth", "quick")
        effort = "low" if depth == "quick" else "medium"
        model = arguments.get("model")
        context = arguments.get("context")
        return delegate_research(
            task=query,
            task_type="research",
            effort=effort,
            model=model,
            context=context,
            mock=mock,
        )

    elif name == "antigravity_list_models":
        q = arguments.get("query")
        models = search_models(q)
        lines = [f"**{m['id']}** ({m['name']})" for m in models]
        summary = f"Found {len(models)} available model(s)" + (f" matching '{q}'" if q else "") + "."
        return {
            "success": True,
            "summary": summary,
            "findings": lines,
            "sources": ["agy models"],
            "uncertainties": [],
            "models": models,
        }

    elif name == "antigravity_compare":
        item_a = arguments.get("item_a", "")
        item_b = arguments.get("item_b", "")
        criteria = arguments.get("criteria", "features and performance")
        task = f"Compare {item_a} vs {item_b} focusing on {criteria}."
        return delegate_research(
            task=task,
            task_type="compare",
            effort="low",
            mock=mock,
        )

    elif name == "antigravity_inspect_docs":
        library = arguments.get("library", "")
        topic = arguments.get("topic", "")
        task = f"Check official {library} documentation for: {topic}."
        return delegate_research(
            task=task,
            task_type="docs",
            effort="low",
            mock=mock,
        )

    elif name == "antigravity_inspect_repo":
        repo = arguments.get("repo_or_path", "")
        question = arguments.get("question", "")
        task = f"Inspect repository {repo}: {question}."
        return delegate_research(
            task=task,
            task_type="repo",
            effort="low",
            mock=mock,
        )

    elif name == "antigravity_inspect_codebase":
        path = arguments.get("path", ".")
        focus = arguments.get("focus", "codebase")
        query = arguments.get("query")
        task = query or (
            "Analyze project architecture, tech stack, and module layout."
            if focus == "codebase"
            else f"Perform {focus} inspection on local project."
        )
        return delegate_research(
            task=task,
            task_type=focus,
            project_dir=path,
            effort="low",
            mock=mock,
        )

    elif name == "antigravity_run_tests":
        path = arguments.get("path", ".")
        runner = arguments.get("runner")
        args = arguments.get("args")
        command = arguments.get("command")
        diagnose = arguments.get("diagnose", True)
        return delegate_test_run(
            project_dir=path,
            runner=runner,
            args=args,
            command=command,
            diagnose=diagnose,
            mock=mock,
        )

    elif name == "antigravity_diagnose_failure":
        error_trace = arguments.get("error_trace", "")
        context = arguments.get("context")
        return delegate_research(
            task=f"Diagnose failure:\n{error_trace}",
            task_type="research",
            context=context,
            effort="low",
            mock=mock,
        )

    else:
        return {
            "success": False,
            "error": f"Unknown tool: {name}",
            "summary": "",
            "claims": [],
            "findings": [],
            "sources": [],
            "uncertainties": [],
        }


def format_tool_response(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Format research or test result into standard MCP tool response content."""
    text_parts = []

    # Check for test execution results
    if "metrics" in raw_result:
        m = raw_result["metrics"]
        text_parts.append(f"### Test Execution Status: {'PASSED' if raw_result.get('success') else 'FAILED'}")
        if raw_result.get("error"):
            text_parts.append(f"- Error: {raw_result['error']}")
        text_parts.append(f"- Command: `{raw_result.get('command')}`")
        text_parts.append(f"- Duration: {raw_result.get('duration_seconds')}s")
        text_parts.append(f"- Results: {m.get('passed', 0)} passed, {m.get('failed', 0)} failed, {m.get('errors', 0)} errors (total {m.get('total', 0)})")
        if raw_result.get("failures"):
            fails = [f"- {f.get('test_name', 'Unknown')}" for f in raw_result["failures"]]
            text_parts.append("### Failing Tests\n" + "\n".join(fails))
        if raw_result.get("diagnosis"):
            d = raw_result["diagnosis"]
            diag_lines = [f"**Root Cause**: {d.get('root_cause', 'Unknown')}"]
            if d.get("affected_components"):
                diag_lines.append("\n**Affected Components**:\n" + "\n".join(f"- {c}" for c in d["affected_components"]))
            if d.get("suggested_fix"):
                diag_lines.append("\n**Suggested Fix**:\n" + "\n".join(f"- {s}" for s in d["suggested_fix"]))
            text_parts.append("### AI Failure Diagnosis\n" + "\n".join(diag_lines))

    elif not raw_result.get("success", False):
        text_parts.append(f"[Error]: {raw_result.get('error', 'Unknown delegation failure')}")
    else:
        if raw_result.get("summary"):
            text_parts.append(f"### Summary\n{raw_result['summary']}")
        if raw_result.get("claims"):
            claims_lines = []
            for c in raw_result["claims"]:
                conf = f" ({c.get('confidence', 'high')} confidence)" if c.get("confidence") else ""
                src = f" [Source: {c.get('source')}]" if c.get("source") else ""
                claims_lines.append(f"- **{c.get('claim')}**{src}{conf}")
            text_parts.append(f"### Claims & Evidence\n" + "\n".join(claims_lines))
        if raw_result.get("findings"):
            findings_text = "\n".join(f"- {f}" for f in raw_result["findings"])
            text_parts.append(f"### Findings\n{findings_text}")
        if raw_result.get("sources"):
            sources_text = "\n".join(f"- {s}" for s in raw_result["sources"])
            text_parts.append(f"### Sources\n{sources_text}")
        if raw_result.get("uncertainties"):
            uncertainties_text = "\n".join(f"- {u}" for u in raw_result["uncertainties"])
            text_parts.append(f"### Uncertainties\n{uncertainties_text}")

    full_text = "\n\n".join(text_parts) if text_parts else "No findings reported."

    return {
        "content": [
            {
                "type": "text",
                "text": full_text,
            }
        ],
        "isError": False if "metrics" in raw_result else not raw_result.get("success", False),
    }


def handle_json_rpc(request: Dict[str, Any], mock: bool = False) -> Optional[Dict[str, Any]]:
    """Process a single JSON-RPC 2.0 request."""
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id") if isinstance(request, dict) else None,
            "error": {"code": -32600, "message": "Invalid Request: must be JSON-RPC 2.0"},
        }

    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": SERVER_INFO,
            },
        }

    elif method == "notifications/initialized":
        # Notification; no response required
        return None

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {},
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS,
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        tool_res = call_tool(tool_name, args, mock=mock)
        formatted = format_tool_response(tool_res)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": formatted,
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def run_stdio_server(mock: bool = False):
    """Run JSON-RPC stdio event loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            response = handle_json_rpc(req, mock=mock)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Antigravity MCP stdio server.")
    parser.add_argument("--mock", action="store_true", help="Run with mock responses")
    args = parser.parse_args()
    run_stdio_server(mock=args.mock)


if __name__ == "__main__":
    main()
