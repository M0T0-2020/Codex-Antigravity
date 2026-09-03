#!/usr/bin/env python3
"""Config loader for Codex-Antigravity delegation system.

Supports tomllib (Python 3.11+), tomli/toml, or a robust built-in fallback parser
for Python 3.9/3.10 standard library environments without extra dependencies.
"""

import os
import re
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "antigravity": {
        "enabled": True,
        "agy_path": "agy",
        "default_effort": "low",
        "timeout_seconds": 120,
        "max_parallel": 3,
        "max_output_chars": 20000,
        "retry_count": 1,
        "output_language": "en",
    },
    "models": {
        "research": "flash",
        "complex_research": "pro",
        "diagnosis": "flash",
    },
    "codebase": {
        "enabled": True,
        "auto_detect_stack": True,
        "max_file_tree_depth": 3,
        "exclude_dirs": [".git", "node_modules", ".venv", "__pycache__", "target", "dist", "build"],
    },
    "testing": {
        "enabled": True,
        "auto_detect_runner": True,
        "default_timeout_seconds": 180,
        "auto_diagnose_on_failure": True,
        "max_failure_lines": 150,
    },
    "routing": {
        "web_research": True,
        "docs_lookup": True,
        "github_research": True,
        "codebase_status": True,
        "codebase_impact": True,
        "test_execution": True,
        "test_failure_diagnosis": True,
        "code_implementation": False,
        "architecture": False,
        "debugging": False,
    },
    "safety": {
        "readonly_enforced": True,
        "disallow_file_writes": True,
        "disallow_git_write": True,
        "disallow_package_install": True,
        "disallow_arbitrary_shell": True,
        "allowed_roots": ["."],
        "allow_parent_paths": False,
        "allow_absolute_paths": False,
    },
    "quality_gate": {
        "enabled": True,
        "pass_threshold": 0.70,
        "review_threshold": 0.40,
    },
    "budget": {
        "max_seconds": 60,
        "max_parallel": 3,
    },
    "source_policy": {
        "mode": "primary_preferred",
    },
}


def _parse_toml_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        try:
            import json
            return json.loads(raw)
        except Exception:
            return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    # Try integer
    try:
        return int(raw)
    except ValueError:
        pass
    # Try float
    try:
        return float(raw)
    except ValueError:
        pass
    # Basic list support [a, b, c]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        items = [s.strip() for s in inner.split(",")]
        return [_parse_toml_value(item) for item in items if item]
    return raw


def _fallback_toml_loads(content: str) -> Dict[str, Any]:
    """Zero-dependency TOML parser for sections and key=value pairs."""
    data: Dict[str, Any] = {}
    current_section = data

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Strip inline comment if not in quotes
        if "#" in line:
            # Simple comment stripping avoiding quoted hash
            in_quote = False
            clean_chars = []
            for char in line:
                if char in ('"', "'"):
                    in_quote = not in_quote
                elif char == "#" and not in_quote:
                    break
                clean_chars.append(char)
            line = "".join(clean_chars).strip()
            if not line:
                continue

        # Section header
        match_section = re.match(r"^\[([A-Za-z0-9_.-]+)\]$", line)
        if match_section:
            section_name = match_section.group(1)
            parts = section_name.split(".")
            curr = data
            for part in parts:
                if part not in curr or not isinstance(curr[part], dict):
                    curr[part] = {}
                curr = curr[part]
            current_section = curr
            continue

        # Key-Value
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            parsed_val = _parse_toml_value(val)
            current_section[key] = parsed_val

    return data


def parse_toml(content: str) -> Dict[str, Any]:
    """Parse TOML string using available parser."""
    try:
        import tomllib  # type: ignore
        return tomllib.loads(content)
    except ImportError:
        pass

    try:
        import tomli  # type: ignore
        return tomli.loads(content)
    except ImportError:
        pass

    try:
        import toml  # type: ignore
        return toml.loads(content)
    except ImportError:
        pass

    return _fallback_toml_loads(content)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override into base."""
    merged = dict(base)
    for k, v in override.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def find_default_config_path() -> str:
    """Locate the default defaults.toml relative to workspace or scripts."""
    candidates = [
        os.path.join(os.getcwd(), "config", "defaults.toml"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "defaults.toml"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from TOML file with fallback to defaults."""
    if not config_path:
        config_path = find_default_config_path()

    if not os.path.exists(config_path):
        return dict(DEFAULT_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
        parsed = parse_toml(raw_content)
        return deep_merge(DEFAULT_CONFIG, parsed)
    except Exception as err:
        # Fallback to defaults if file read/parse fails
        return dict(DEFAULT_CONFIG)


if __name__ == "__main__":
    import json
    cfg = load_config()
    print(json.dumps(cfg, indent=2))
