#!/usr/bin/env python3
"""Codebase Analyzer for Coding Agent Reconnaissance.

Performs fast (<100ms), pure standard-library inspection of a local project directory:
- Detects languages, package managers, and frameworks.
- Summarizes directory structure and entry points.
- Checks Git status (current branch, modified files, recent commits).
- Identifies test setup and recommended test runners.
"""

import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Set

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    "coverage",
    ".tox",
}


def detect_project_stack(project_dir: str) -> Dict[str, Any]:
    """Detect programming languages, build tools, and frameworks in project_dir."""
    abs_path = os.path.abspath(project_dir)
    stack: Dict[str, Any] = {
        "languages": [],
        "manifests": [],
        "frameworks": [],
        "test_runner": None,
    }

    if not os.path.isdir(abs_path):
        return stack

    try:
        root_files = set(os.listdir(abs_path))
    except Exception:
        return stack

    # Python
    py_manifests = ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"]
    found_py = [f for f in py_manifests if f in root_files]
    if found_py:
        stack["languages"].append("Python")
        stack["manifests"].extend(found_py)
        stack["test_runner"] = "pytest"

        # Check framework hints in pyproject.toml or requirements.txt
        for mf in found_py:
            try:
                with open(os.path.join(abs_path, mf), "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                for fw in ["fastapi", "flask", "django", "pydantic", "torch", "onnxruntime"]:
                    if fw in content and fw not in stack["frameworks"]:
                        stack["frameworks"].append(fw)
            except Exception:
                pass

    # Node / TypeScript / JavaScript
    if "package.json" in root_files:
        stack["manifests"].append("package.json")
        stack["languages"].append("JavaScript/TypeScript" if "tsconfig.json" in root_files else "JavaScript")
        stack["test_runner"] = "npm test"

        try:
            with open(os.path.join(abs_path, "package.json"), "r", encoding="utf-8") as f:
                pkg_data = json.loads(f.read())
            deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
            for fw in ["react", "vue", "next", "svelte", "express", "vitest", "jest", "tauri"]:
                if any(fw in k.lower() for k in deps):
                    if fw not in stack["frameworks"]:
                        stack["frameworks"].append(fw)
            if "vitest" in deps:
                stack["test_runner"] = "npx vitest run"
            elif "jest" in deps:
                stack["test_runner"] = "npm test"
        except Exception:
            pass

    # Rust
    if "Cargo.toml" in root_files:
        stack["languages"].append("Rust")
        stack["manifests"].append("Cargo.toml")
        stack["test_runner"] = "cargo test"

        try:
            with open(os.path.join(abs_path, "Cargo.toml"), "r", encoding="utf-8", errors="ignore") as f:
                cargo_content = f.read().lower()
            for fw in ["actix", "axum", "tauri", "tokio", "serde"]:
                if fw in cargo_content and fw not in stack["frameworks"]:
                    stack["frameworks"].append(fw)
        except Exception:
            pass

    # Go
    if "go.mod" in root_files:
        stack["languages"].append("Go")
        stack["manifests"].append("go.mod")
        stack["test_runner"] = "go test ./..."

    # C / C++
    if "CMakeLists.txt" in root_files or "Makefile" in root_files:
        stack["languages"].append("C/C++")
        if "CMakeLists.txt" in root_files:
            stack["manifests"].append("CMakeLists.txt")
        if "Makefile" in root_files:
            stack["manifests"].append("Makefile")

    return stack


def get_git_status_summary(project_dir: str) -> Dict[str, Any]:
    """Retrieve current Git branch, uncommitted changes, and recent commits."""
    abs_path = os.path.abspath(project_dir)
    git_info: Dict[str, Any] = {
        "is_git": False,
        "branch": None,
        "dirty": False,
        "modified_files": [],
        "recent_commits": [],
    }

    if not os.path.isdir(os.path.join(abs_path, ".git")):
        return git_info

    git_info["is_git"] = True

    try:
        # Branch
        b_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=abs_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if b_res.returncode == 0:
            git_info["branch"] = b_res.stdout.strip()

        # Status
        s_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=abs_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if s_res.returncode == 0:
            lines = [line.strip() for line in s_res.stdout.splitlines() if line.strip()]
            git_info["dirty"] = len(lines) > 0
            git_info["modified_files"] = lines[:15]  # Cap at 15 files

        # Recent commits
        c_res = subprocess.run(
            ["git", "log", "-n", "3", "--oneline"],
            cwd=abs_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if c_res.returncode == 0:
            git_info["recent_commits"] = [c.strip() for c in c_res.stdout.splitlines() if c.strip()]
    except Exception:
        pass

    return git_info


def get_directory_tree(
    project_dir: str,
    max_depth: int = 3,
    exclude_dirs: Optional[Set[str]] = None,
) -> List[str]:
    """Return an indented directory tree summary up to max_depth."""
    abs_path = os.path.abspath(project_dir)
    excludes = exclude_dirs or DEFAULT_EXCLUDE_DIRS
    tree_lines: List[str] = []

    def _walk(current_dir: str, depth: int, prefix: str = ""):
        if depth > max_depth:
            return

        try:
            entries = sorted(os.listdir(current_dir))
        except Exception:
            return

        dirs = []
        files = []
        for e in entries:
            if e.startswith(".") and e not in [".env", ".gitignore", ".env.example"]:
                continue
            full_p = os.path.join(current_dir, e)
            if os.path.isdir(full_p):
                if e not in excludes:
                    dirs.append(e)
            else:
                files.append(e)

        # Show directories first, then key files
        for d in dirs:
            tree_lines.append(f"{prefix}├── {d}/")
            _walk(os.path.join(current_dir, d), depth + 1, prefix + "│   ")

        # Show up to 10 files per directory
        for i, f in enumerate(files[:10]):
            tree_lines.append(f"{prefix}└── {f}")
        if len(files) > 10:
            tree_lines.append(f"{prefix}└── ... ({len(files) - 10} more files)")

    _walk(abs_path, depth=1)
    return tree_lines[:60]  # Cap lines to prevent token explosion


def detect_test_setup(project_dir: str) -> Dict[str, Any]:
    """Find test directories and test files in project_dir."""
    abs_path = os.path.abspath(project_dir)
    test_info: Dict[str, Any] = {
        "has_tests": False,
        "test_dirs": [],
        "sample_test_files": [],
        "test_count": 0,
    }

    if not os.path.isdir(abs_path):
        return test_info

    candidate_test_dirs = ["tests", "test", "__tests__", "spec"]
    found_dirs = []
    test_files: List[str] = []

    for d in candidate_test_dirs:
        full_d = os.path.join(abs_path, d)
        if os.path.isdir(full_d):
            found_dirs.append(d)
            try:
                for root, _, files in os.walk(full_d):
                    for f in files:
                        if f.startswith("test_") or f.endswith(("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js")):
                            rel = os.path.relpath(os.path.join(root, f), abs_path)
                            test_files.append(rel)
            except Exception:
                pass

    test_info["test_dirs"] = found_dirs
    test_info["sample_test_files"] = test_files[:10]
    test_info["test_count"] = len(test_files)
    test_info["has_tests"] = len(test_files) > 0 or len(found_dirs) > 0

    return test_info


def analyze_codebase(
    project_dir: str,
    max_depth: int = 3,
    exclude_dirs: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Comprehensive single-call analysis of a codebase."""
    abs_path = os.path.abspath(project_dir)
    stack = detect_project_stack(abs_path)
    git = get_git_status_summary(abs_path)
    tests = detect_test_setup(abs_path)
    tree = get_directory_tree(abs_path, max_depth=max_depth, exclude_dirs=exclude_dirs)

    return {
        "project_dir": abs_path,
        "project_name": os.path.basename(abs_path),
        "stack": stack,
        "git": git,
        "tests": tests,
        "tree": tree,
    }


def format_codebase_context(analysis: Dict[str, Any]) -> str:
    """Render a compact, high-signal markdown context block for Antigravity prompts."""
    stack = analysis.get("stack", {})
    git = analysis.get("git", {})
    tests = analysis.get("tests", {})
    tree = analysis.get("tree", [])

    lines = [
        f"### Codebase Overview: `{analysis.get('project_name')}`",
        f"- Path: `{analysis.get('project_dir')}`",
    ]

    if stack.get("languages"):
        lines.append(f"- Languages: {', '.join(stack['languages'])}")
    if stack.get("frameworks"):
        lines.append(f"- Frameworks: {', '.join(stack['frameworks'])}")
    if stack.get("manifests"):
        lines.append(f"- Manifests: {', '.join(stack['manifests'])}")

    if git.get("is_git"):
        branch = git.get("branch") or "unknown"
        dirty_str = f"dirty ({len(git.get('modified_files', []))} changed files)" if git.get("dirty") else "clean"
        lines.append(f"- Git: branch `{branch}`, working tree is {dirty_str}")
        if git.get("modified_files"):
            lines.append(f"  Modified files: {', '.join(git['modified_files'][:5])}")

    if tests.get("has_tests"):
        runner = stack.get("test_runner") or "auto"
        lines.append(f"- Tests: {tests.get('test_count', 0)} test files detected (runner: `{runner}`)")

    if tree:
        lines.append("\nDirectory Tree:")
        lines.append("```text")
        lines.extend(tree[:25])
        if len(tree) > 25:
            lines.append(f"... ({len(tree) - 25} more paths)")
        lines.append("```")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    result = analyze_codebase(target)
    print(format_codebase_context(result))
