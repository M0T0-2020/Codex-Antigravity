#!/usr/bin/env python3
"""Safety and Security Policy Layer for Codex-Antigravity.

Enforces execution boundaries, workspace isolation, command whitelisting,
environment sanitization, and read-only constraints.
"""

import os
from pathlib import Path
import re
import shlex
import sys
from typing import Any, Dict, List, Optional, Set, Union


class SecurityError(Exception):
    """Raised when an operation violates security or safety policy."""
    pass


DEFAULT_ALLOWED_RUNNERS: Set[str] = {
    "pytest",
    "python",
    "python3",
    "cargo",
    "npm",
    "pnpm",
    "yarn",
    "vitest",
    "jest",
    "go",
    "ctest",
    "make",
}

# Shell metacharacters and control operators prohibited when disallow_arbitrary_shell is enabled
DANGEROUS_SHELL_CHARS_REGEX = re.compile(r"[;&|><`$\n\r]")

# Sensitive environment variables to scrub from subprocess environments
SENSITIVE_ENV_PATTERNS = [
    re.compile(r".*TOKEN.*", re.IGNORECASE),
    re.compile(r".*SECRET.*", re.IGNORECASE),
    re.compile(r".*PASSWORD.*", re.IGNORECASE),
    re.compile(r".*PRIVATE_KEY.*", re.IGNORECASE),
    re.compile(r"^AWS_", re.IGNORECASE),
    re.compile(r"^GITHUB_", re.IGNORECASE),
    re.compile(r"^GH_", re.IGNORECASE),
    re.compile(r"^OPENAI_", re.IGNORECASE),
    re.compile(r"^ANTHROPIC_", re.IGNORECASE),
    re.compile(r"^SLACK_", re.IGNORECASE),
]

SAFE_ENV_PASSTHROUGH = {
    "PATH",
    "HOME",
    "USER",
    "LOGNAME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "SHELL",
    "TERM",
    "TMPDIR",
    "SYSTEMROOT",
    "COMSPEC",
    "PATHEXT",
    "TZ",
}


class SafetyPolicy:
    """Central safety validation and policy enforcement engine."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("safety", {}) if config else {}
        self.readonly_enforced: bool = cfg.get("readonly_enforced", True)
        self.disallow_file_writes: bool = cfg.get("disallow_file_writes", True)
        self.disallow_git_write: bool = cfg.get("disallow_git_write", True)
        self.disallow_package_install: bool = cfg.get("disallow_package_install", True)
        self.disallow_arbitrary_shell: bool = cfg.get("disallow_arbitrary_shell", True)

        self.allowed_roots: List[str] = cfg.get("allowed_roots", ["."])
        self.allow_parent_paths: bool = cfg.get("allow_parent_paths", False)
        self.allow_absolute_paths: bool = cfg.get("allow_absolute_paths", False)

        custom_runners = cfg.get("allowed_runners")
        self.allowed_runners: Set[str] = (
            set(custom_runners) if custom_runners is not None else set(DEFAULT_ALLOWED_RUNNERS)
        )

    def validate_workspace(
        self,
        path: Union[str, Path],
        workspace_root: Optional[Union[str, Path]] = None,
    ) -> Path:
        """Validate that a path resides strictly within the allowed workspace boundary."""
        root_path = Path(workspace_root or os.getcwd()).resolve()
        target_path = Path(path)

        if not target_path.is_absolute():
            target_path = (root_path / target_path).resolve()
        else:
            target_path = target_path.resolve()

        # Check if target is inside root or equals root
        try:
            target_path.relative_to(root_path)
            is_inside = True
        except ValueError:
            is_inside = False

        if not is_inside:
            # Check secondary allowed roots if configured
            secondary_allowed = False
            for r in self.allowed_roots:
                allowed_r = Path(r).resolve()
                try:
                    target_path.relative_to(allowed_r)
                    secondary_allowed = True
                    break
                except ValueError:
                    continue

            if not secondary_allowed:
                raise SecurityError(
                    f"Workspace boundary violation: '{path}' resolves to '{target_path}', "
                    f"which is outside authorized workspace root '{root_path}'."
                )

        return target_path

    def allow_path(self, path: Union[str, Path], mode: str = "read") -> bool:
        """Verify path authorization for the given mode ('read' or 'write')."""
        self.validate_workspace(path)
        if mode == "write" and self.disallow_file_writes:
            raise SecurityError(
                f"File modification prohibited: write access to '{path}' is disallowed by safety policy."
            )
        return True

    def validate_command(
        self,
        cmd: Union[str, List[str]],
        allowed_runners: Optional[Set[str]] = None,
    ) -> List[str]:
        """Validate and parse a command into a safe argv list.

        Rejects shell metacharacters and unwhitelisted runners.
        """
        if isinstance(cmd, str):
            if self.disallow_arbitrary_shell:
                # Check for chaining, redirection, or command substitution
                match = DANGEROUS_SHELL_CHARS_REGEX.search(cmd)
                if match:
                    char = match.group(0)
                    repr_char = repr(char)
                    raise SecurityError(
                        f"Arbitrary shell execution prohibited: command contains dangerous character {repr_char}."
                    )
            try:
                argv = shlex.split(cmd)
            except Exception as e:
                raise SecurityError(f"Failed to safely parse command string: {e}")
        elif isinstance(cmd, (list, tuple)):
            argv = [str(arg) for arg in cmd]
        else:
            raise SecurityError(f"Unsupported command format: {type(cmd)}")

        if not argv:
            raise SecurityError("Command is empty.")

        runner_name = os.path.basename(argv[0])
        effective_runners = allowed_runners if allowed_runners is not None else self.allowed_runners

        if runner_name not in effective_runners:
            raise SecurityError(
                f"Disallowed test runner '{runner_name}'. Allowed runners: {sorted(list(effective_runners))}"
            )

        # Check for disallowed operations
        cmd_str = " ".join(argv).lower()

        if self.disallow_package_install:
            prohibited_installs = ["pip install", "npm install", "npm i ", "cargo install", "yarn add", "pnpm add"]
            for pi in prohibited_installs:
                if pi in cmd_str:
                    raise SecurityError(f"Package installation is prohibited: '{pi}' detected in command.")

        if self.disallow_git_write:
            prohibited_git = ["git commit", "git push", "git merge", "git rebase", "git checkout -b"]
            for pg in prohibited_git:
                if pg in cmd_str:
                    raise SecurityError(f"Git write operation is prohibited: '{pg}' detected in command.")

        return argv

    def sanitize_environment(
        self,
        base_env: Optional[Dict[str, str]] = None,
        extra_passthrough: Optional[Set[str]] = None,
    ) -> Dict[str, str]:
        """Produce a sanitized copy of the environment with sensitive credentials removed."""
        source = base_env if base_env is not None else os.environ
        passthrough = set(SAFE_ENV_PASSTHROUGH)
        if extra_passthrough:
            passthrough.update(extra_passthrough)

        sanitized: Dict[str, str] = {}

        for k, v in source.items():
            # Check explicit passthrough
            if k in passthrough:
                sanitized[k] = v
                continue

            # Scrub anything matching sensitive patterns
            is_sensitive = any(pattern.match(k) for pattern in SENSITIVE_ENV_PATTERNS)
            if not is_sensitive:
                sanitized[k] = v

        sanitized["PYTHONUNBUFFERED"] = "1"
        return sanitized

    def build_agy_permissions(self, sandbox_requested: Optional[bool] = None) -> Dict[str, Any]:
        """Build permissions and CLI flags for Antigravity subagent invocation."""
        enforce_sandbox = self.readonly_enforced or (sandbox_requested is True)
        return {
            "sandbox": enforce_sandbox,
            "readonly": self.readonly_enforced,
            "allow_file_writes": not self.disallow_file_writes,
            "allow_git_write": not self.disallow_git_write,
        }
