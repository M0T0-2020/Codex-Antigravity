#!/usr/bin/env python3
"""Diagnostics tool to check Antigravity CLI installation and readiness.

Usage:
  python scripts/check_antigravity.py [--json]
"""

import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict

# Support relative import when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import find_agy_binary, get_available_models  # type: ignore
from config_loader import load_config  # type: ignore


def check_antigravity(config_path: str = None) -> Dict[str, Any]:
    """Inspect environment for Antigravity CLI readiness."""
    cfg = load_config(config_path)
    custom_path = cfg.get("antigravity", {}).get("agy_path")

    binary_path = find_agy_binary(custom_path)
    result: Dict[str, Any] = {
        "installed": False,
        "binary_path": binary_path,
        "version": None,
        "executable": False,
        "models_available": [],
        "config": cfg.get("antigravity", {}),
        "issues": [],
    }

    if not binary_path:
        result["issues"].append(
            "Antigravity CLI ('agy') not found in PATH or standard locations (~/.local/bin/agy, /usr/local/bin/agy)."
        )
        return result

    result["installed"] = True
    result["executable"] = os.access(binary_path, os.X_OK)

    # Check version
    try:
        ver_proc = subprocess.run(
            [binary_path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if ver_proc.returncode == 0:
            result["version"] = ver_proc.stdout.strip()
        else:
            # Try running with no args or help to extract version info
            result["version"] = "installed (version flag returned non-zero)"
    except Exception as err:
        result["issues"].append(f"Failed to check version: {err}")

    # Check models
    try:
        models = get_available_models(binary_path, timeout=3)
        result["models_available"] = models
    except Exception as err:
        result["issues"].append(f"Failed to query models: {err}")

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Check Antigravity CLI installation and configuration.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--config", type=str, default=None, help="Path to custom defaults.toml")
    args = parser.parse_args()

    status = check_antigravity(args.config)

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print("=" * 50)
        print(" Codex-Antigravity Environment Diagnostics")
        print("=" * 50)
        print(f"Installed    : {'YES' if status['installed'] else 'NO'}")
        print(f"Binary Path  : {status['binary_path'] or 'Not found'}")
        print(f"Executable   : {'YES' if status['executable'] else 'NO'}")
        print(f"Version      : {status['version'] or 'Unknown'}")
        print(f"Models       : {', '.join(status['models_available']) if status['models_available'] else 'None'}")
        if status["issues"]:
            print("\nIssues:")
            for issue in status["issues"]:
                print(f"  [!] {issue}")
        else:
            print("\nStatus       : OK (Ready to delegate)")
        print("=" * 50)

    if not status["installed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
